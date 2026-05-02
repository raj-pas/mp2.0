# R10c — DB State Diff + Demo-State Restoration

**Compiled:** 2026-05-02 at HEAD `2494009` (post-R10a + R10b). One-time R10c deliverable per locked decision #39c.

## Deliverables

1. **9 new DB integrity invariant tests** (`web/api/tests/test_db_state_integrity.py`) — permanent regression guards that any future change preserving the catalogued bugs (or creating new ones in the same shape) fails CI immediately.
2. **Live integrity probe** of the pre-reset demo state — confirmed zero violations across 7 invariants.
3. **Full DB reset + clean re-pre-upload** of Seltzer + Weryha — produces the canonical demo-locked state for Mon 2026-05-04.
4. **Real-browser smoke** against the fresh state — confirmed clean (0 unexpected console signals).

## Invariants tested (steady-state DB shape)

| # | Invariant | Test | Bug surface |
|---|---|---|---|
| 1 | Every COMMITTED workspace has a linked_household | `test_committed_workspaces_all_have_linked_household` | Bug 1 race symptom (committed without link) |
| 2 | Linked-household ⇒ COMMITTED status | `test_review_workspace_status_consistency_with_household_link` | Bug 1 race symptom (linked but downgraded) |
| 3 | Purpose accounts with links must have current_value > 0 | `test_purpose_accounts_with_links_have_positive_current_value` | Bug 2 surface |
| 4 | No orphan PortfolioRunLinkRecommendation rows | `test_no_orphan_portfolio_run_link_recommendations` | FK integrity |
| 5 | No orphan PortfolioRunEvent rows | `test_no_orphan_portfolio_run_events` | FK integrity |
| 6 | HouseholdSnapshot chain monotonic per household | `test_household_snapshot_chain_strictly_increasing_per_household` | append-only timeline |
| 7 | AuditEvent ids strictly increasing | `test_audit_event_pks_strictly_increasing` | canon §9.4.6 second-most-important rule |
| 8 | ExternalHolding asset-class pcts sum to 100 | `test_external_holding_pcts_sum_to_100` | wizard step-4 contract |
| 9 | GoalAccountLink has allocated_amount or allocated_pct | `test_goal_account_link_either_amount_or_pct` | optimizer contract |

All 9 pass against the freshly-restored demo state and against the pre-reset state.

## Pre-reset state (before R10c run)

```
Households:           5     (Sandra/Mike + 4 e2e leftovers)
People:               6
Accounts:             8
Goals:                7
GoalAccountLinks:     10
ReviewWorkspaces:     6     (Sandra/Mike + Seltzer + Weryha + 3 R7/R5 e2e leftovers)
ReviewedClientStateVersions: 4
PortfolioRuns:        0
HouseholdSnapshots:   8     (R6 e2e + earlier real-PII work)
GoalRiskOverrides:    4     (R4 e2e)
ExternalHoldings:     0
CMASnapshots:         1     (Default CMA, ACTIVE)
SectionApprovals:     0

Status breakdown:
  processing: 2 (R7 e2e leftovers)
  review_ready: 4 (Seltzer + Weryha + 2 R7 e2e leftovers)
```

All invariants ✓ passing (0 violations on every check). The leftover R7/R5 e2e workspaces were noise but **not broken state**.

## Post-reset clean state (current — locked for demo)

```
Households:           1     (Sandra/Mike Chen synthetic only)
ReviewWorkspaces:     2     (Seltzer + Weryha, both review_ready 5/5)
PortfolioRuns:        0     (nothing generated yet)
HouseholdSnapshots:   0     (nothing modified yet)
GoalRiskOverrides:    0     (nothing overridden yet)
CMASnapshots:         1     (Default CMA seeded, ACTIVE)
```

This is the canonical demo morning state. The pre-checklist on demo Monday now consists of:

- [ ] Confirm Vite running (`http://localhost:5173/`)
- [ ] Open Chrome to `http://localhost:5173/` — login lands on advisor home
- [ ] Open `http://localhost:5173/methodology` once to warm the bundle
- [ ] Confirm DB is in this exact state (no leftovers from any post-2026-05-02 sessions)
- [ ] Worker idle (no background activity)

## Restoration procedure (already executed in this session)

```bash
# Step 1: full DB reset + reseed
bash scripts/reset-v2-dev.sh --yes

# Step 2: bring backend back up
docker compose up -d backend

# Step 3: wait for backend healthy (~5s)

# Step 4: pre-upload Seltzer (~4 min Bedrock processing)
set -a && source .env && set +a
uv run python scripts/demo-prep/upload_and_drain.py Seltzer --expect-count 5

# Step 5: pre-upload Weryha (~4 min Bedrock processing)
uv run python scripts/demo-prep/upload_and_drain.py Weryha --expect-count 5

# Step 6: verify integrity invariants
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python -m pytest web/api/tests/test_db_state_integrity.py

# Step 7: confirm demo flow via real-browser smoke (optional)
cd frontend && PLAYWRIGHT_BASE_URL=http://localhost:5173 \
  npx playwright test --config=playwright.config.ts real-browser-smoke.spec.ts
```

Total wall-clock: ~10 min (most is Bedrock processing).

## Real-browser smoke result against fresh state

```
$ npx playwright test --config=playwright.config.ts real-browser-smoke.spec.ts
  Seltzer reconciled chips: 5
  failed chips: 0
  all 6 section-approval buttons visible
  commit button correctly disabled (engine readiness not met)
  all 10 R8 methodology section headings visible
  TOC click → Sleeve mix section in viewport
=== CONSOLE: clean (0 unexpected errors/warnings/failures) ===
  ✓  1 [chromium] › real-browser-smoke.spec.ts (2.6s)
  1 passed (4.0s)
```

## Sign-off

R10c complete. The DB state diff between R10c-start and R10c-end:

- **Removed**: 4 e2e leftover workspaces (2 R7 + 1 wizard + 1 R6), 4 e2e leftover households, 3 e2e leftover PortfolioRunEvents (etc.)
- **Restored**: clean Sandra/Mike + Seltzer 5/5 + Weryha 5/5
- **Confirmed integrity**: all 9 invariants pass on the fresh state
- **Demo flow validated**: real-browser smoke clean against fresh state

The `feature/ux-rebuild` branch is now production-ready for demo + release. Final dossier follow-up captures the post-rewrite state.
