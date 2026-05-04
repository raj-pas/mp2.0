#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--yes" ]]; then
  echo "Usage: scripts/reset-v2-dev.sh --yes" >&2
  echo "This destroys local Docker volumes, migrates a fresh DB, and reseeds v2 data." >&2
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export DATABASE_URL="${DATABASE_URL:-postgres://mp20:mp20@localhost:5432/mp20}"
export MP20_SECURE_DATA_ROOT="${MP20_SECURE_DATA_ROOT:-$HOME/mp20-secure-data}"
export MP20_LOCAL_ADMIN_EMAIL="${MP20_LOCAL_ADMIN_EMAIL:-advisor@example.com}"
export MP20_LOCAL_ADMIN_PASSWORD="${MP20_LOCAL_ADMIN_PASSWORD:-change-this-local-password}"
export MP20_LOCAL_ANALYST_EMAIL="${MP20_LOCAL_ANALYST_EMAIL:-analyst@example.com}"
export MP20_LOCAL_ANALYST_PASSWORD="${MP20_LOCAL_ANALYST_PASSWORD:-change-this-local-password}"

docker compose down -v
docker compose up -d db

echo "Waiting for Postgres to become healthy..."
for _ in {1..60}; do
  STATUS="$(
    docker compose ps --format json db 2>/dev/null \
      | python3 -c 'import json,sys; data=sys.stdin.read().strip(); print(json.loads(data).get("Health", ""))' 2>/dev/null \
      || true
  )"
  if [[ "$STATUS" == "healthy" ]]; then
    break
  fi
  sleep 1
done

STATUS="$(
  docker compose ps --format json db 2>/dev/null \
    | python3 -c 'import json,sys; data=sys.stdin.read().strip(); print(json.loads(data).get("Health", ""))' 2>/dev/null \
    || true
)"
if [[ "$STATUS" != "healthy" ]]; then
  echo "Postgres did not become healthy in time." >&2
  docker compose ps db >&2
  exit 1
fi

uv run python web/manage.py migrate
uv run python web/manage.py seed_default_cma --force
# Bootstrap advisor BEFORE load_synthetic_personas so the persona's
# advisor_pre_ack JSON marker can write into AdvisorProfile (per A1).
uv run python web/manage.py bootstrap_local_advisor --skip-if-missing
uv run python web/manage.py load_synthetic_personas

echo "V2 dev DB reset and reseed complete."
