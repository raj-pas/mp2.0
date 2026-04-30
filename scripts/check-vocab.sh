#!/usr/bin/env bash
# Vocabulary CI guard (locked decision #14, broad scope).
#
# Scans frontend/src + selected backend artifacts for canon-violating
# strings. Catches:
#   - Re-goaling tripwires (canon §6.3a): "reallocation", "transfer",
#     "move money" in goal-realignment context
#   - Retired risk labels: "Conservative" used as a stand-alone bucket
#     name (canon vocab uses "Cautious" for the lowest band; the longer
#     "Conservative-balanced" is allowed)
#   - Retired "Sleeve " capitalization in user-visible strings (the
#     code-identifier `Sleeve` class is allowed; the user-visible word
#     is "fund" or "building-block fund" per canon Part 16)
#
# Returns non-zero exit on first match. CI gate.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Paths to scan. Backend serializer + management commands + migrations +
# fixtures are user-visible-string surfaces. Frontend src is everything
# the user can read.
SCAN_PATHS=(
  "frontend/src"
  "frontend/index.html"
  "web/api/serializers.py"
  "web/api/management/commands"
  "web/api/migrations"
  "engine/fixtures"
)

# Forbidden patterns. Each pattern is a Perl-compatible regex.
# Note: we use word boundaries to avoid catching legitimate substrings
# like "transferable" or "reallocation_audit_log_field".
declare -a FORBIDDEN=(
  '\breallocation\b'
  '\breallocate\b'
  '\bmove money\b'
  # Retired bare "Conservative " label (canon uses "Cautious" or
  # "Conservative-balanced"). Word boundary avoids "Conservative-balanced".
  '\bConservative\b(?!-balanced)'
  # "Sleeve " capitalized as user-visible product term. Code identifier
  # `Sleeve` (the Pydantic class) is fine; the canonical product term
  # is "building-block fund" or "fund".
  # We deliberately allow `Sleeve` immediately followed by a closing
  # paren (function-arg) or a dot (member access) so code references
  # don't trip the guard.
  '\bSleeve [a-z]'
)

# Allow-listed contexts where forbidden words are LEGITIMATE (e.g., this
# script itself, the canon doc, the migration plan, decisions doc, the
# vocab CI rule definitions, comments documenting forbidden words).
ALLOW_PATTERNS=(
  'check-vocab.sh'
  'eslint.config.js'
  'docs/agent/'
  '\.test\.'
  '/__tests__/'
  '# canon-vocab-allow:'
  '// canon-vocab-allow:'
)

found_any=0

for path in "${SCAN_PATHS[@]}"; do
  if [[ ! -e "$path" ]]; then
    continue
  fi
  for pattern in "${FORBIDDEN[@]}"; do
    matches=$(grep -rnP --include='*.{ts,tsx,js,py,html,json,md}' --exclude-dir=node_modules --exclude-dir=__pycache__ "$pattern" "$path" 2>/dev/null || true)
    if [[ -z "$matches" ]]; then
      continue
    fi
    while IFS= read -r line; do
      keep=1
      for allow in "${ALLOW_PATTERNS[@]}"; do
        if [[ "$line" =~ $allow ]]; then
          keep=0
          break
        fi
      done
      if [[ $keep -eq 1 ]]; then
        if [[ $found_any -eq 0 ]]; then
          echo "VOCABULARY VIOLATIONS (canon §6.3a + §4.2 + §16.1):"
          echo ""
        fi
        echo "  pattern: $pattern"
        echo "  $line"
        echo ""
        found_any=1
      fi
    done <<< "$matches"
  done
done

if [[ $found_any -eq 1 ]]; then
  echo "Resolution: use canon-aligned vocabulary."
  echo "  - Re-goaling, goal realignment, re-label dollars between goals"
  echo "    (NOT reallocation / transfer / move money — canon §6.3a)"
  echo "  - Cautious / Conservative-balanced / Balanced /"
  echo "    Balanced-growth / Growth-oriented (NOT bare 'Conservative')"
  echo "  - building-block fund / whole-portfolio fund / fund"
  echo "    (NOT user-visible 'Sleeve ' — class identifier OK)"
  exit 1
fi

echo "vocab CI: OK"
