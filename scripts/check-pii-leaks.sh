#!/usr/bin/env bash
# PII grep guard (Phase 2 — 2026-05-02).
#
# Forbids known leak patterns where raw `str(exc)` flows to a serializer
# surface, DB column, audit metadata, or HTTP response body. Real-PII
# Bedrock errors can carry extracted client text in the message body;
# structured failure_codes (per `web/api/error_codes.py`) are PII-safe.
#
# Wires into the gate suite alongside `scripts/check-vocab.sh`. Failing
# this guard means a future commit has re-introduced a leak vector that
# Phase 2 closed.
#
# Allowed (does NOT trigger the guard):
#   - `str(exc)` with `# noqa: PII-safe-classifier` comment (string-search)
#   - `if "..." in str(exc):` (membership tests, not persistence)
#   - `safe_response_payload(exc)` / `safe_audit_metadata(exc)` (sanctioned)
#   - The `_REDACTED_` constants in `web/api/error_codes.py` (intentional)
#   - test files matching `test_*.py` (pytest fixtures may construct
#     exception messages for testing the guard itself)
#
# Forbidden (triggers the guard):
#   - `last_error\s*=\s*str(exc` — DB column persistence
#   - `failure_reason\s*=\s*str(exc` — DB column persistence
#   - `Response({"detail": str(exc)` — HTTP response body
#   - `metadata={"detail": str(exc)` — audit-event metadata leak

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

forbidden=(
    'last_error\s*=\s*str(exc'
    'failure_reason\s*=\s*str(exc'
    'Response\(\{"detail":\s*str\(exc'
    'metadata=\{"detail":\s*str\(exc'
    'metadata=\{"reason":\s*str\(exc'
)

failed=0
for pattern in "${forbidden[@]}"; do
    # Search web/ + extraction/ + integrations/. Exclude test files +
    # this script + the error_codes.py module itself (it documents the
    # patterns it replaces).
    if grep -rEn \
        --include='*.py' \
        --exclude-dir=tests \
        --exclude='*_test.py' \
        --exclude='test_*.py' \
        --exclude='error_codes.py' \
        --exclude='check-pii-leaks.sh' \
        "$pattern" \
        web/ extraction/ integrations/ 2>/dev/null; then
        echo "PII grep guard FAILED: forbidden pattern matched: $pattern" >&2
        failed=1
    fi
done

if [[ $failed -ne 0 ]]; then
    echo "" >&2
    echo "Replace forbidden str(exc) patterns with the structured helpers:" >&2
    echo "  Response(safe_response_payload(exc), status=...)" >&2
    echo "  metadata=safe_audit_metadata(exc, **extra)" >&2
    echo "  job.last_error = safe_exception_summary(exc)" >&2
    echo "" >&2
    echo "All helpers live in web/api/error_codes.py." >&2
    echo "See docs/agent/extraction-audit.md (PII-1 through PII-SER)." >&2
    exit 1
fi

echo "PII grep guard: OK"
