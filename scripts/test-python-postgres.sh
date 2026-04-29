#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

docker compose up -d db

echo "Waiting for Postgres to become healthy..."
for _ in {1..60}; do
  STATUS="$(docker compose ps --format json db 2>/dev/null | python3 -c 'import json,sys; data=sys.stdin.read().strip(); print(json.loads(data).get("Health", ""))' 2>/dev/null || true)"
  if [[ "$STATUS" == "healthy" ]]; then
    break
  fi
  sleep 1
done

STATUS="$(docker compose ps --format json db 2>/dev/null | python3 -c 'import json,sys; data=sys.stdin.read().strip(); print(json.loads(data).get("Health", ""))' 2>/dev/null || true)"
if [[ "$STATUS" != "healthy" ]]; then
  echo "Postgres did not become healthy in time." >&2
  docker compose ps db >&2
  exit 1
fi

export DATABASE_URL="${DATABASE_URL:-postgres://mp20:mp20@localhost:5432/mp20}"
uv run pytest "$@"
