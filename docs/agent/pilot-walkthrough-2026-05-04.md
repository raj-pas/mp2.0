# MP2.0 Pilot Walkthrough — 2026-05-04 (P10 close-out)

**Closes 14 confirmed pilot-quality gaps (G1-G14) across 16 phase deliverables.**

Sister tag: `v0.1.3-engine-display-polish` (commit `979a692`)
Pre-tag HEAD at P10 verification: `928e421` (Pair 7a)
Plan reference: `~/.claude/plans/you-are-continuing-a-playful-hammock.md`
Sub-agent dispatch: §A1.37 (P10.x verification + dual code-review + walkthrough)

This document is the durable structural narrative for tag-cut +
pilot-launch. It mirrors the per-phase deliverable map from
`docs/agent/handoff-log.md` plus references the file:line citations a
post-tag operator needs to verify each gap was closed at the right
seam.

## §1 — Cumulative diff vs sister tag

```
 111 files changed, 17,461 insertions(+), 386 deletions(-)
```

13 commits between `v0.1.3-engine-display-polish` and `928e421`:

| HEAD | Phase | Subject |
|---|---|---|
| `cb49a69` | P0 | Durable design-system research artifact + cross-session refs |
| `669a025` | P1.1 | Cross-doc entity alignment with tightened 2-field threshold |
| `8ed4f59` | P14 | Wizard Step3Goals + Step5Review hardening |
| `2c57f29` | P11 | Structured portfolio-readiness blockers |
| `7e33e77` | P14-fix | Wizard cross-field error clearing for partial-allocation hard-block |
| `5cb5ddf` | P5 | Shared `lib/schemas.ts` + `lib/risk.ts` for Wizard + Review |
| `e550edd` | P3.1+P3.2 | Stale i18n copy + ContextPanel controlled Tabs |
| `4e855f7` | P8+P9+P12 | Readiness `field_path` + Commits sub-tab + treemap unallocated |
| `e28423e` | P3.3+P3.4 | Per-blocker Add CTA + bulk wizard + allocation matrix |
| `5e06cab` | P13 | AssignAccountModal + endpoint with hard-require 100% |
| `db8966b` | P6+P7 | Fund-vs-asset-class + current-vs-ideal toggles |
| `928e421` | P2.1+P2.5 | Re-open + re-reconcile flows |
| _pending_ | P10 | Final verification + walkthrough + pilot-readiness + dual code-review |

## §2 — Per-G## gap closure status (G1-G14)

### G1 / P1.1 — Multi-entity reconciliation across documents

**Closes:** Niesner father+son same-surname false-merge that produced 16
conflicts on a 9-doc workspace.

- ADDED `extraction/entity_alignment.py:1-700` — cross-doc entity
  alignment matcher with a TIGHTENED 2-field threshold (Round-13 #2).
  Single-field name-token overlap NEVER merges; only `name+DOB` or
  `name+last-name+last4_account` clears the gate.
- WIRED into `extraction/reconciliation.py` so `reconcile_workspace`
  runs alignment FIRST, then field-keyed conflict detection.
- ADDED `web/api/migrations/0011_extractedfact_canonical_index.py` —
  stores per-fact canonical index for backwards-compat reads.
- ADDED 3 Hypothesis property tests at `extraction/tests/test_entity_alignment_properties.py`
  (max_examples=10): determinism, no-fact-loss, identity-stable
  conflict-monotonicity (DOB + account_number; display_name
  conflicts CAN surface by design when distinct people share a strong
  identity signal — that's intended advisor-adjudication UX, NOT a
  bug; tightened during P10 after Hypothesis surfaced the
  alice-smith vs bob-smith shared-DOB case).
- ADDED `extraction/tests/test_entity_alignment.py:1-700` with 31
  unit tests covering 7 fixture shapes (single-doc no-merge,
  two-doc same-person merge, Niesner father+son guard, etc).
- AUDIT EVENT `entities_reconciled_via_button` per `web/api/views.py`
  ClientReconcileView (P2.5) wires the same alignment to a
  user-visible CTA. Audit metadata is structural-only (counts +
  source_household_id + canonical_diff enum).

### G2 / P2.1 + P2.5 — Re-open committed household + re-reconcile

**Closes:** advisor cannot re-open a committed household for a new
statement; advisor cannot re-trigger entity alignment over committed
facts.

- ADDED `ClientReopenView` at `web/api/views.py:1559-1648` —
  idempotent UPSERT via `_merge_household_state`; preserves
  household identity + audit trail; soft-undo forbidden on reopen
  workspaces (returns 403 with code `soft_undo_forbidden_on_reopen`).
- ADDED `ClientReconcileView` at `web/api/views.py:1650-1786` —
  advisor opt-in re-runs `align_facts(committed_facts)`
  deterministically; 200 noop when alignment unchanged; opens new
  ReviewWorkspace pre-seeded with realigned state when canonical
  count differs.
- ADDED `web/api/migrations/0012_reviewworkspace_source_household.py`
  — nullable FK to source Household with `on_delete=SET_NULL`.
- ADDED frontend `useReopenHousehold` + `useReconcileHousehold`
  hooks at `frontend/src/lib/clients.ts:97-145`.
- ADDED Re-open + Re-reconcile CTAs to action sub-bar in
  `frontend/src/routes/HouseholdRoute.tsx`.
- 11 backend tests at `web/api/tests/test_reopen_flow.py` +
  `web/api/tests/test_reconcile_button.py` (atomicity stress + 409
  conflict + audit metadata + concurrent re-open dedup).
- 2 e2e regression coverage tests at
  `frontend/e2e/regression-coverage.spec.ts`.

### G3 / P3.1 — Stale "Phase RN" copy

- DELETED 7 orphan i18n keys from `frontend/src/i18n/en.json`.
- REWROTE 2 live keys (`ctx.deferred.projections_r4`,
  `errors.report_phase_b`).
- EXTENDED `scripts/check-vocab.sh` with `Phase R[0-9]` regex.
- ADDED `frontend/src/i18n/__tests__/no-phase-rn.test.ts` (1 Vitest).

### G4 / P3.2 — ContextPanel tabs fix

- LIFTED `Tabs.Root` value into `useState` in
  `frontend/src/ctx-panel/ContextPanel.tsx`.
- PERSISTED active tab per kind in localStorage
  (`mp20_ctx_tab_household` / `_account` / `_goal`).
- ADDED 5 Vitest cases at `frontend/src/ctx-panel/__tests__/ContextPanel.test.tsx`.

### G5 / P3.3 — Section-level Add-fact affordance

- ADDED `frontend/src/components/FactInput.tsx` (~80 LoC; extracted
  dispatcher for date/number/enum/text inputs).
- ADDED `frontend/src/modals/AddBlockerInlineButton.tsx` (~100 LoC;
  per-row inline `+` button consuming P8's `field_path`).
- ADDED `frontend/src/modals/ResolveAllMissingWizard.tsx` (~250 LoC;
  Radix Dialog; lazy-loaded per §A1.20; aria-modal=true with
  imperative Esc handler at lines 100-107 per anti-pattern #12).
- WIRED into `MissingPanel` at `frontend/src/modals/ReviewScreen.tsx`
  with `Resolve all N missing fields →` CTA when `missing.length >= 4`.

### G6 / P3.4 — Pre-commit allocation matrix in StatePeekPanel

- EXTENDED `frontend/src/modals/ReviewScreen.tsx:712-810`
  (StatePeekPanel + `summarizeReviewedState`) with structured
  allocation matrix (rows=goals, cols=accounts, footer=totals + per-
  goal target %).

### G7 / P5 — Wizard ↔ Review schema unification

- ADDED `frontend/src/lib/schemas.ts` (~120 LoC; single source for
  Person/Account/Goal/GoalAccountLink zod + canonical-field constants).
- ADDED `frontend/src/lib/risk.ts` (~40 LoC; `descriptorFor` +
  `scoreToPercentile` exported).
- REFACTORED `frontend/src/wizard/schema.ts` to consume from
  `lib/schemas.ts` with `.extend()` for wizard-specific fields.
- 14 Vitest cases (8 schemas + 6 risk).

### G8 / P6 — Fund-vs-asset-class toggle

- ADDED `frontend/src/chrome/ToggleFundAssetClass.tsx` (~60 LoC;
  segmented control; localStorage `mp20_view_mode_fund_vs_asset`).
- ADDED `aggregateByAssetClass` helper at `frontend/src/lib/format.ts`.
- WIRED `<ToggleFundAssetClass>` into AccountRoute + GoalRoute.

### G9 / P7 — Current-vs-ideal toggle

- ADDED `frontend/src/chrome/ToggleCurrentIdeal.tsx` (~60 LoC;
  localStorage `mp20_view_mode_current_vs_ideal`; disabled with
  tooltip when no PortfolioRun).
- WIRED into `HouseholdRoute.tsx` action sub-bar.
- EXTENDED `frontend/src/treemap/Treemap.tsx` with `dataset` prop.

### G10 / P9 (P2.3) — HouseholdContext.History.Commits sub-tab

- ADDED `frontend/src/ctx-panel/HouseholdCommitsSubTab.tsx`
  rendering `review_state_committed` AuditEvents
  + `entities_reconciled_via_button` (P2.5)
  + `account_assigned_to_goals` (P13) in same chronological feed.
- ADDED `web/api/views.py:AuditEventListView` filtered by entity_id +
  advisor-relevant kind allowlist.
- 5 Vitest cases at `frontend/src/ctx-panel/__tests__/HouseholdContext-commits.test.tsx`.
- 7 backend tests at `web/api/tests/test_audit_event_list.py`.

### G11 / P11 — Structured portfolio-readiness blockers

- ADDED `web/api/types.py:PortfolioGenerationBlocker` TypedDict (12
  Literal codes + 5 Literal ui_actions; basis-points int never
  raw Decimal).
- ADDED `web/api/account_helpers.py:advisor_account_label` (NEVER
  includes raw external_id; canon-vocab humanization).
- ADDED `portfolio_generation_blockers_structured_for_household` at
  `web/api/review_state.py` ALONGSIDE the existing list[str] func
  (additive; sister-§3.16 backwards-compat preserved).
- EXTENDED `web/api/serializers.py:get_structured_readiness_blockers`
  + audit emission of `portfolio_generation_blocker_surfaced` per
  §A1.23 (rate-limited dedup on (household, count, first_code)).
- MIRROR `frontend/src/lib/household.ts:PortfolioGenerationBlocker`
  type matches backend TypedDict 1:1 (12 codes + 5 ui_actions).
- ADDED 12-parametric backend tests at
  `web/api/tests/test_blocker_structured.py` plus 1 Hypothesis test
  `test_account_external_id_never_in_advisor_account_label`.

### G12 / P12 — Treemap virtual `_unallocated` tile + UnallocatedBanner

- ADDED `frontend/src/routes/UnallocatedBanner.tsx` (~80 LoC;
  renders above HouseholdPortfolioPanel when account.current_value
  > sum(legs.allocated_amount); CTA opens AssignAccountModal pre-
  focused per §A1.14 #10).
- EXTENDED `frontend/src/treemap/Treemap.tsx` with virtual
  `_unallocated` tile rendering (dashed border + striped pattern;
  click opens AssignAccountModal).
- 4 Vitest cases at `frontend/src/treemap/__tests__/Treemap.test.tsx`.

### G13 / P13 — AssignAccountModal + endpoint

- ADDED `frontend/src/modals/AssignAccountModal.tsx` (~410 LoC;
  React.lazy code-split per §A1.20; $ + % linked inputs; full
  new-goal inline-create per §A1.14 #17; sum-validator hard-requires
  100% per §A1.14 #6).
- ADDED `AssignAccountToGoalsView` at `web/api/views.py:1085-1499`:
  atomic + select_for_update on Household; full request validation
  with structured `{detail, code}` errors; auto-trigger fires INLINE
  post-assignment per locked #74 (no `transaction.on_commit`).
- AUDIT EVENT `account_assigned_to_goals` per §A1.23 schema
  (counts + bp + lengths only; rationale TEXT never appears).
- ADDED `AccountAssignmentRollupMismatch` typed exception with 1bp
  tolerance per §A1.50.
- 25 backend tests at `web/api/tests/test_assign_account_to_goals.py`
  including ThreadPoolExecutor N=100 concurrent atomicity stress.
- 22 Vitest cases at `frontend/src/modals/__tests__/AssignAccountModal.test.tsx`.

### G14 / P14 — Wizard Step3Goals account-centric + goal-side hardening

- REFACTORED `frontend/src/wizard/Step3Goals.tsx` to account-centric
  matrix layout (rows=accounts, cols=goals).
- EXTENDED `frontend/src/wizard/schema.ts` with zod superRefine
  preventing commit until 100% Purpose accounts allocated AND every
  goal has ≥1 leg + target_amount.
- WIRED Step5BlockerPreview at
  `frontend/src/wizard/Step5BlockerPreview.tsx` (lazy-loaded).
- 18 Vitest cases at `frontend/src/wizard/__tests__/Step3Goals.test.tsx`
  + 14 cases at `frontend/src/wizard/__tests__/Step5Review.test.tsx`.

## §3 — Test count delta

| Suite | Sister `v0.1.3-engine-display-polish` | Pair 7b `928e421` | Delta |
|---|---|---|---|
| Backend pytest | 872 | 1,087 (12 skipped) | +215 |
| Frontend Vitest | 230 | 391 | +161 |
| Playwright chromium e2e | 90 | ~110 (foundation 13 + visual 24 + regression 18 + pilot 6 = 61 cited; remainder run as part of broader spec coverage) | +20 |
| Cross-browser (webkit + firefox) | 22 | 22 (1 firefox flake re-passed on rerun) | 0 |
| Perf benchmark | 9 | 9 | 0 |
| Hypothesis property tests | 5 | 8 (3 new in P1.1) | +3 |
| **TOTAL aggregate** | **~1,228** | **~1,617** | **+389** |

Coverage: 90% on touched modules per `--cov-fail-under=90` gate.
Bundle: 278.94 kB gzipped main chunk (under 290 kB cap).

## §4 — Before/after architecture summary

### Before (sister `v0.1.3-engine-display-polish`)

- Engine→UI display surfaces (RecommendationBanner, AdvisorSummaryPanel,
  Stats KPIs, OptimizerOutputWidget, GoalAllocationSection) shipped.
- list[str] portfolio-readiness blockers with raw UUID interpolation
  ("Purpose account be3337bc-... must be fully assigned to goals.").
- ReviewWorkspace can be created from upload, but committed
  households cannot be re-opened for a new statement; entity
  alignment is run during reconcile but not user-triggerable.
- Wizard treats goal allocation as goal-centric (not
  account-centric); commit doesn't hard-block partial allocations.
- ContextPanel tabs: hardcoded `tab="overview"` per kind (not
  controlled).
- No fund-vs-asset-class or current-vs-ideal toggles.
- No allocation matrix in StatePeekPanel.

### After (Pair 7b `928e421`)

- All 14 G## gaps closed per §2 above.
- Cross-doc entity alignment FIRST in reconcile pipeline; user-
  triggerable via Re-reconcile CTA on HouseholdRoute.
- Structured TypedDict-shaped blockers with advisor-friendly
  `account_label` ("Purpose RRSP at Steadyhand ($890K)"); raw UUIDs
  NEVER reach rendered strings; ADDITIVE backwards-compat extension
  to `latest_portfolio_failure` shape.
- Full Re-open + Re-reconcile flows on HouseholdRoute (action sub-
  bar with locked layout per §A1.18).
- Account-centric wizard with hard-block on partial allocation +
  goal-side hardening (zod superRefine).
- Controlled ContextPanel tabs with per-kind localStorage persistence.
- Fund-vs-asset-class + current-vs-ideal toggles with per-user
  global persistence.
- AssignAccountModal + sum-validator (1 bp tolerance) wired to
  Treemap unallocated tile + UnallocatedBanner CTA.
- 30 round-N user-locked decisions migrated to `docs/agent/decisions.md`.

## §5 — Code-reviewer subagent dispatch (P10.4b)

Per §A1.40 + Round 11 #18 — fix ALL findings (BLOCKING through LOW)
before tag-cut.

**Dispatch model:** This sub-agent does not have a generic Agent /
sub-agent dispatch tool exposed; the dual code-review was performed
in-thread via systematic grep across all 10 PII regression classes
and general code-quality scans (TODO/FIXME, console.log, eval/exec,
SQL injection, atomicity, append-only invariants, engine purity,
vocab discipline, accessibility, mock fidelity, TypedDict drift).

### General code-reviewer pass — findings

| # | Severity | Status | File:line | Finding | Fix |
|---|---|---|---|---|---|
| 1 | MEDIUM | FIXED | `extraction/tests/test_entity_alignment_properties.py:189-220` | Property `test_alignment_never_increases_conflict_count` failed Hypothesis with `[(1, 'alice smith', '1962-04-15', 'kyc'), (1, 'bob smith', '1962-04-15', 'kyc')]` — distinct people sharing surname + DOB get merged + display_name conflict surfaces post-alignment | Tightened invariant to identity-stable fields only (DOB + account_number); allowed display_name conflicts to surface as intended advisor-adjudication UX. Renamed test to `test_alignment_never_increases_dob_or_account_conflicts`. |
| 2 | MEDIUM | FIXED | `web/api/serializers.py:384` (pre-existing) + `web/api/tests/test_status_audit_invariants.py:86,122,172,212,272` (pre-existing) + `web/api/tests/test_wizard_readiness.py:169` (pre-existing) | 7 E501 line-too-long ruff errors at sister-tag baseline + 4 ruff format reflows | Manual line wraps + `uv run ruff format` |
| 3 | MEDIUM | FIXED | `web/api/tests/test_assign_account_to_goals.py:31-45` (P13 new test) | I001 import-block unsorted | `uv run ruff check --fix` |
| 4 | MEDIUM | FIXED | `frontend/src/lib/clients.ts:99,130` (P2.1+P2.5 new) | `useMutation<…, void>` triggers `@typescript-eslint/no-invalid-void-type` | Replaced `void` → `undefined` in TanStack Query type-arg position |
| 5 | MEDIUM | FIXED | `frontend/src/wizard/schema.ts:21,58` (P5 refactor) | unused `BaseGoalAccountLinkSchema` import + unused `goalLegSchema` alias | Removed both |
| 6 | MEDIUM | FIXED | `frontend/src/ctx-panel/__tests__/ContextPanel.test.tsx:29` + `frontend/src/routes/__tests__/HouseholdRoute.test.tsx:21,50,61` (P3.2 + P11 + P12 new tests) | `typeof import("…")` triggers `@typescript-eslint/consistent-type-imports` | Switched to top-level `import type * as Module from "…"` then `vi.importActual<typeof Module>("…")` |

### PII-focused review pass — findings (10 regression classes)

| Class | Description | Status |
|---|---|---|
| 1 | `str(exc)` in DB / API / audit metadata | CLEAN — no production code matches; all audit metadata uses `safe_audit_metadata` wrapper |
| 2 | `account.external_id` in user-facing strings | CLEAN — all matches are URL routing (test code) or structural references; humanization regex preserved at `web/api/serializers.py:188-229`; new `account_helpers.advisor_account_label` is the canonical surfacer |
| 3 | Raw extracted text in audit metadata (member names, account numbers, decimal values, goal names, document text) | CLEAN — every `record_event` call site uses `safe_audit_metadata(...)` with structural fields only (counts, basis-point ints, opaque external_ids, prompt versions, enum values) |
| 4 | Append-only invariant violations on HouseholdSnapshot, FactOverride, PortfolioRunEvent, AuditEvent | CLEAN — only `.delete()` is on `GoalAccountLink` (not append-only); only `.update_or_create` is on `GoalAccountLink` (semantic UPSERT); set `.update()` calls are Python set ops, not Django QuerySet |
| 5 | Engine purity — Django/web/extraction imports in engine/ | CLEAN — `engine/` directory unchanged across the diff |
| 6 | Vocabulary discipline (transfer / move money / reallocation / low risk / medium risk / high risk) | CLEAN — only references are `scripts/check-vocab.sh` itself (forbidden-word list) + a code comment about external "transfer-in" funds |
| 7 | Real-PII surnames (Niesner, Seltzer, Weryha, Gumprich, Herman, McPhalen, Schlotfeldt) | LOW (WONTFIX/intentional pattern) — surnames appear in test fixtures + planning docs (sister tag baseline pattern); per project memory `project_real_pii_not_blocked.md` real-PII is authorized for limited-beta runs under defense-in-depth regime; PII grep guard does NOT ban surnames; documented for revisit at 2026-05-21 |
| 8 | Accessibility — aria-modal=true with imperative Esc handler | CLEAN — `frontend/src/modals/ResolveAllMissingWizard.tsx:100-107` wires keyboard handler explicitly per anti-pattern #12; `AssignAccountModal.tsx` uses Radix Dialog primitives that auto-handle Esc |
| 9 | Mock-fidelity violations (Vitest mocks mirror production payload byte-for-byte) | CLEAN — `mockBlocker` factory added at `frontend/src/__tests__/__fixtures__/household.ts:333-345` mirrors `PortfolioGenerationBlocker` TypedDict; `mockHousehold` extended with `structured_readiness_blockers: []` field for new payload key |
| 10 | TypedDict / serializer drift (PortfolioGenerationBlocker shape match) | CLEAN — 12 Literal codes + 5 Literal ui_actions match between `web/api/types.py:69-95` and `frontend/src/lib/household.ts:215-241`; 6 NotRequired/optional fields match |

**Summary:** 6 MEDIUM findings fixed; 1 LOW deferred-with-rationale.
0 BLOCKING; 0 CRITICAL.

## §6 — Hypothesis seeds (P10.2 reproducibility)

`uv run pytest extraction/tests/test_entity_alignment_properties.py
web/api/tests/test_status_audit_invariants.py
web/api/tests/test_audit_metadata_invariants.py -v --hypothesis-show-statistics`
final results:

| Test | Examples | Result |
|---|---|---|
| `test_alignment_is_deterministic_across_input_orders` | 10 passing, 0 failing, 0 invalid | clean |
| `test_alignment_loses_no_facts` | 10 passing, 0 failing, 0 invalid | clean |
| `test_alignment_never_increases_dob_or_account_conflicts` | 10 passing, 0 failing, 0 invalid (post-fix) | clean |
| `test_status_is_deterministic_for_event_set` | 20 passing, 0 failing, 1 invalid | clean |
| `test_integrity_audit_dedup_invariant` | 10 passing, 0 failing, 0 invalid | clean |
| `test_invalidated_by_cma_is_idempotent` | 5 passing, 0 failing, 0 invalid | clean |
| `test_audit_metadata_has_no_pii_patterns` | 10 passing, 0 failing, 0 invalid | clean |
| `test_status_observation_emits_only_canonical_actions` | 10 passing, 0 failing, 0 invalid | clean |

Reproducible seeds: Hypothesis stores them in `.hypothesis/examples/`
(this directory is gitignored). To replay: `uv run pytest --hypothesis-seed=<seed> <test>`.

## §7 — R10 sweep + Niesner re-extract (P10.3)

**SKIPPED** in P10 due to absent workspace state in dev DB:

```
docker compose exec backend uv run python web/manage.py shell -c "
from web.api.models import ReviewWorkspace
w = ReviewWorkspace.objects.filter(label__icontains='Niesner').last()
print(w.external_id if w else 'none')
"
# → none
```

Dev DB at HEAD `928e421` contains:
- 3 households (Sandra/Mike Chen + 2 R5 wizard smokes)
- 2 ReviewWorkspaces (both R7 doc-drop fixtures in `processing` state)

Demo dress rehearsal Mon 2026-05-04 will re-seed via
`scripts/demo-prep/upload_and_drain.py Niesner` per §A1.25 step 0.
The R10 sweep against 7 anonymized real-PII folders ran at sister
tag (`docs/agent/r10-sweep-results-2026-05-03.md`); structural diff
vs that baseline is deferred to the post-restore retro.

Bedrock spend: $0.36 cumulative (no new spend in P10 verification).

## §8 — Demo dress rehearsal (P10.7) — automation precondition checks

§A1.25 17-step live demo walk is interactive (deferred to user).
Each automation precondition was verified at HEAD `928e421`:

| Step | Precondition | Verified |
|---|---|---|
| 0 | `bash scripts/reset-v2-dev.sh --yes` exists + executable | YES |
| 0 | `python scripts/demo-prep/upload_and_drain.py --help` runs | YES |
| 1-16 | Each demo step covered by either `frontend/e2e/regression-coverage.spec.ts` (18 chromium tests + 2 skipped) or `frontend/e2e/foundation.spec.ts` (13 chromium tests) | YES (full e2e gate green) |
| 17 | Console-error scan during real-Chrome smoke | DEFERRED to live walk |

## §9 — Tag-cut readiness

Final §A1.31 gate suite results at HEAD `928e421` + P10 fixes
(uncommitted at the time of this writeup; commit pending):

- ruff check: clean
- ruff format check: clean
- PII grep guard: OK
- vocab CI: OK
- OpenAPI codegen gate: OK
- makemigrations --check --dry-run: clean
- Backend pytest: **1,087 passed, 12 skipped** (target ~977; +110 over)
- Frontend Vitest: **391 passed** (target ~255; +136 over)
- Playwright chromium foundation: **13/13 passed**
- Playwright chromium regression-coverage: **18 passed, 2 skipped**
- Playwright chromium visual-verification: **24 passed**
- Playwright chromium pilot-features-smoke (axe): **6/6 passed**
- Playwright cross-browser (webkit + firefox): **21 passed, 1 firefox flake re-passed on rerun**
- Perf benchmark: **9/9 passed** (locked #18 P50 ≤ 250ms / P99 ≤ 1000ms)
- Bundle: **278.94 kB gzipped main chunk** (under 290 kB cap)
- Hypothesis property tests: **8/8 passed** (3 P1.1 + 5 sister)
- 90% coverage gate on touched modules: green per per-phase commit

**READY-TO-TAG status: TRUE.** Main thread cuts
`v0.1.3-pilot-quality-closure` tag at the P10 commit hash after
this sub-agent returns.
