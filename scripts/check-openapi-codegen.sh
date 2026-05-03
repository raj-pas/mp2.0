#!/usr/bin/env bash
# OpenAPI codegen drift CI gate (Phase 4.5, locked 2026-05-02).
#
# Generates the OpenAPI schema from drf-spectacular (offline; no
# running server needed via `manage.py spectacular`), runs
# `openapi-typescript` against the fresh schema, and compares the
# output to the committed `frontend/src/lib/api-types.ts`. Fails on
# any drift.
#
# This guard catches the FE/BE enum-drift bug class that produced the
# 4 hand-synchronized fixes in commit `4643bb5`. Whenever a serializer
# enum changes on the backend, the generated FE types must be
# regenerated and committed; CI fails until they are.
#
# Caveat: the gate only covers schemas that drf-spectacular can
# introspect. Review-pipeline serializers (ReviewWorkspace etc.)
# currently produce 203 spectacular warnings/errors and are not in
# the generated file; their FE shapes in `lib/review.ts` remain
# hand-synchronized until review serializers get @extend_schema
# decorators (post-pilot scope).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TMP_SCHEMA="${TMPDIR:-/tmp}/mp20-api-schema-fresh.json"
TMP_TYPES="${TMPDIR:-/tmp}/mp20-api-types-fresh.ts"

trap 'rm -f "$TMP_SCHEMA" "$TMP_TYPES"' EXIT

# Generate fresh schema. Spectacular emits 200+ warnings/errors to
# stderr; we suppress those (the generated JSON is well-formed
# regardless) but bubble any non-zero exit as a real failure.
DATABASE_URL="${DATABASE_URL:-postgres://mp20:mp20@localhost:5432/mp20}" \
  uv run python web/manage.py spectacular \
    --format openapi-json \
    --file "$TMP_SCHEMA" \
    >/dev/null 2>&1

if [[ ! -s "$TMP_SCHEMA" ]]; then
  echo "OpenAPI codegen gate: spectacular failed to produce schema"
  exit 1
fi

# Generate fresh TS types from the fresh schema.
(
  cd frontend
  npx --no-install openapi-typescript "$TMP_SCHEMA" --output "$TMP_TYPES" >/dev/null 2>&1
)

if [[ ! -s "$TMP_TYPES" ]]; then
  echo "OpenAPI codegen gate: openapi-typescript failed to produce types"
  exit 1
fi

# Compare to committed file.
if ! diff -q "$TMP_TYPES" frontend/src/lib/api-types.ts >/dev/null 2>&1; then
  echo "OpenAPI codegen gate: drift detected in frontend/src/lib/api-types.ts"
  echo "Run: cd frontend && uv run python ../web/manage.py spectacular \\"
  echo "       --format openapi-json --file /tmp/api-schema.json && \\"
  echo "     npx openapi-typescript /tmp/api-schema.json --output src/lib/api-types.ts"
  echo "and commit the regenerated file."
  echo ""
  echo "Diff (first 40 lines):"
  diff -u frontend/src/lib/api-types.ts "$TMP_TYPES" | head -40 || true
  exit 1
fi

echo "OpenAPI codegen gate: OK"
