# MP2.0 Implementation Decisions

This file distills implementation decisions for coding sessions. The canon is
authoritative when more detail is needed.

## Locked for the Current Scaffold

- Work directly on `main`.
- Make local commits after checks pass; do not push unless explicitly asked.
- Use repo files as project memory.
- Treat `CLAUDE.md` as the primary Claude Code entrypoint.
- Use Python 3.12, Node 22, `uv`, `npm`, and Docker Compose first.
- Build a runnable thin slice, not structure-only scaffolding.
- Use a DB-backed synthetic Sandra/Mike Chen persona.
- Keep Django persistence models separate from engine Pydantic schemas.
- Translate web DB state into engine inputs at the web/engine boundary.
- Add audit logging in Phase 1 and keep audit rows immutable through model
  guards plus backend-specific DB triggers.
- Real-upload features require `MP20_SECURE_DATA_ROOT` outside the repo and hard
  fail if it is missing or repo-local.
- Runtime and Python tests are Postgres-only. `DATABASE_URL` is required and
  non-Postgres URLs fail loudly; SQLite fallback is out of scope.
- Use Postgres rows as the local processing queue for now. Backend enqueues;
  worker claims with row locking and processes through
  `process_review_queue`.
- Real-derived extraction requires Bedrock env and ca-central-1 routing. Missing
  Bedrock configuration is a fail-closed worker error.
- Full raw extracted text remains transient. Persist structured facts,
  provenance/run metadata, and minimally redacted evidence quotes only.
- Sensitive identifiers are stored as hash plus redacted display, not plaintext.
- Household uniqueness for review commits is internal generated ID; matching is
  advisory and commit must be link-or-create.
- Default DRF access is authenticated. Session/login endpoints opt out
  explicitly. Advisors use one shared team scope for clients and review
  workspaces; financial analysts cannot access real-client PII surfaces.
- Commit requires `engine_ready`, `construction_ready`, and plain approved
  status on all required review sections.
- Household and goal risk use the same 1-5 contract. Legacy 1-10 household and
  goal values are remapped with `ceil(old / 2)` during migration; new values
  above 5 fail validation at the model/API/engine boundary.
- `MP20_ENGINE_ENABLED=false` blocks portfolio generation while leaving intake
  and review available.
- Failed documents do not block review. Manual retry queues another processing
  job.
- Fraser/CMA portfolio generation starts from committed household state only.
- `PortfolioRun` plus append-only `PortfolioRunEvent` rows are the source of
  truth for generated recommendations and lifecycle. Legacy
  `Household.last_engine_output` and mutable `PortfolioRun.status/stale_reason`
  are removed in v2.
- CMA data is versioned globally through snapshot/fund/correlation rows.
  Financial analysts can draft/edit/publish and view the frontier; advisors
  cannot edit CMA.
- PortfolioRun input snapshots include committed construction data only. Do not
  store review evidence quotes, extracted facts, raw notes/documents, or source
  provenance payloads in PortfolioRun.
- V2 portfolio output is `engine_output.link_first.v2` only. Do not add a v1
  compatibility path.
- The engine id for a goal-account recommendation is durable
  `GoalAccountLink.external_id`.
- Whole-portfolio funds are optimizer eligible and may mix with building-block
  funds; no allocation cap is applied in Phase A.
- New/onboarding cash is represented explicitly by `Account.cash_state`.
- Present-but-unmapped non-cash holdings are warnings with structured mapping
  diagnostics, not generation blockers.
- Reuse a stored PortfolioRun only after input/output/CMA/run-signature hash
  verification succeeds. A mismatch records an event and permits fresh
  regeneration.
- Advisor audit export must be sanitized: hashes, manifest, diagnostics, and
  lifecycle events are allowed; raw evidence quotes, document text, and source
  provenance payloads are not.

## Canon v2.3 Decisions to Implement Next

- Delivery is Phase A/B/C: Som-demo-grade scaffold, pilot hardening with IS
  validation, then controlled advisor pilot.
- Phase A is not pilot-grade. Phase B exit criteria gate any advisor login.
- Steadyhand remains v1 launch context; Sandra/Mike Chen remains the synthetic
  backup persona.
- Engine optimization unit is goal x account (`GoalAccountLink`), then
  account-level and household-level rollups. This is now implemented for the
  Fraser v1 engine path.
- Recommended portfolio always comes from the efficient frontier. Whole-portfolio
  funds such as Founders/Builders are eligible funds in the frontier and are
  labeled distinctly from building-block funds in explanations.
- Risk scale is 5-point, snap-to-grid, mapped to optimizer percentiles:
  cautious=5th, conservative-balanced=15th, balanced=25th,
  balanced-growth=35th, growth-oriented=45th.
- Advisor-visible risk exposes three components: household, goal, and combined.
- Future-dollar targets are optional secondary inputs, not mandatory primary
  flow requirements.
- Tax drag is architecturally in scope with schema and versioning; zero drag is
  an acceptable v1 default until real values are available.
- External holdings are an optional household-risk dampener, not a full external
  portfolio simulation in v1.
- CMA assumptions and efficient-frontier visualization are financial-analyst-only.
- The advisor UX centers on a three-tab household/account/goal view with fund vs
  asset-class look-through and a click-through goal-account assignment workflow.
- Current vs ideal allocation must be visible together on recommendation screens,
  with account-first diagnostics and alias-mapping warnings.
- Reporting supports Tier 1/2/3 sophistication from the same deterministic
  engine numbers. AI may style the narrative but cannot invent numbers.
- Pre-recommendation overrides adjust inputs and rerun the engine; post-
  recommendation overrides require an inline rationale note.
- Boundary pseudonymization is retired for the current tranche. Real-derived
  extraction uses the canon defense-in-depth regime: authenticated ingress,
  Bedrock ca-central-1 fail-closed routing, transient raw text, structured-only
  persistence, hashed sensitive identifiers, redacted evidence quotes, immutable
  audit, RBAC, secure-root retention/disposal, and bounded pilot population.
  If legal/IT later requires pre-LLM pseudonymization, that is a Phase B
  re-engineering project, not a partial runtime toggle.

## Architecture Defaults

- Django + DRF backend.
- React + Vite frontend.
- Pydantic v2 for engine schemas.
- Postgres for local persistence.
- TanStack Query for frontend data fetching.
- Ruff and pytest for Python checks.
- Vite build/typecheck for frontend smoke checks.

## Known Scaffold Mismatches

- Fund-of-funds collapse suggestions, real tax-drag math, compliance ratings,
  and richer report-grade fan charts are still missing from the Fraser path.
- Household and goal risk now use the 1-5 optimizer mapping. Remaining work is
  the documented household x goal composite weighting, not scale migration.
- Visible household/goal risk score labels should stay numeric 1-5. Qualitative
  low/medium/high vocabulary is reserved for source facts or compliance/internal
  mapping and should not be used as the advisor-facing construction score.
- Current extraction/review is being moved into `extraction/` as the canonical
  Layer 1-5 package. Remaining Phase B hardening is richer IS validation,
  temporal reconciliation, retention/disposal policy sign-off, and CI PII
  checks. Boundary pseudonymization is not part of this tranche.
- Current audit log has append-only protection, sanitized timeline events, and
  an advisor audit drawer/export for portfolio runs. Full compliance audit
  browser UI remains deferred.
- Current RBAC has authenticated-by-default access, advisor team scope, and
  financial-analyst PII denial, but Phase B still needs MFA/session policy,
  lockout, password reset, and admin-only CMA boundaries.

## Deferred

- Staging deployment.
- CI PII scanners and encryption-posture validation.
- Real Croesus, Conquest, custodian, or LLM integrations.
- Audit browser UI.
- External-holdings risk-tolerance dampener (canon §4.6a) — deferred to
  Phase B per 2026-04-30 plan locked decision #11. The v36 mockup itself
  does not implement the dampener; it applies a projection-time penalty
  (μ × 0.85, σ × 1.15 for external) which is implemented in
  `engine/projections.py`. Awaits team-confirmed dampener formula.

## R7 (UI/UX rewrite, 2026-04-30)

- Doc-drop + review-screen shipped at `/review` (canon §6.7 primary
  onboarding entry per locked decision #7). DocDropOverlay
  (multi-file dropzone + workspace label + data-origin selector),
  ReviewScreen (processing panel + readiness chips + section-
  approval list + commit gate), ReviewRoute (host with in-flight
  queue).
- `frontend/src/lib/review.ts` exports typed hooks for the 11
  R1 review endpoints + `useReviewWorkspace` with optional 3s
  polling while ProcessingJobs are queued/running. Wire shapes
  match the canonical contracts captured during the pre-R7 smoke.
- Three real bugs caught + fixed during R7 build:
  - DocDropOverlay two-mutation closure race (workspace id was
    stale at upload time); fixed by changing useUploadDocuments
    to take the workspace id per-call.
  - Readiness wire-shape drift (fresh workspaces return
    `readiness: {}`, type expected full shape); fixed by making
    Readiness fields optional + defensive `?? false`/`?? []`
    accessors.
  - Hidden file input wasn't interactable by Playwright
    (`hidden` class = display:none); switched to `sr-only`.
- Real-PII discipline (canon §11.8.3): workspace timeline
  serializer's sanitized projection drives the audit-visible
  event list; raw text never persists in the UI.
- Source-priority hierarchy (canon §11.4): cross-class mismatches
  resolve silently to higher-priority source server-side; the
  `state.conflicts[]` field surfaces same-class disagreements
  for the conflict UI (R10 polish layers in cards).
- Vocab CI green — UI strings honor canon §6.7 + §11.4.
- e2e foundation spec extended: doc-drop synthetic flow → workspace
  appears in queue → review screen renders. 10/10 e2e in 9.1s.

## R6 (UI/UX rewrite, 2026-04-30)

- Realignment + Compare + History shipped. RealignModal (per-account
  leg editor with sum=account_value validation), CompareScreen
  (full-screen Dialog with side-by-side before/after summary +
  per-goal delta badges), HouseholdHistoryTab (snapshots list with
  Compare/Restore actions).
- `frontend/src/lib/realignment.ts` exports typed hooks for the
  R1 endpoints: `useRealignment`, `useSnapshots`, `useSnapshot`,
  `useRestoreSnapshot`, `useBlendedAccountRisk`. Wire shapes match
  the canonical contracts captured during the pre-R6 smoke.
- `frontend/src/components/ui/dialog.tsx` adds the Radix Dialog
  wrapper with `fullScreen` variant for CompareScreen takeovers.
- HouseholdRoute wires "Re-goal across accounts" CTA into the
  AUM strip; manages closed → modal → compare → confirm/revert
  state machine.
- HouseholdContext history tab replaces R3 placeholder with the
  full snapshot list; restore action invalidates household +
  snapshots queries.
- Vocab CI green — UI strings honor canon §6.3a ("re-goaling",
  "realignment"; never "transfer"/"reallocation"/"move money").
- Drift item #13 (BIG_SHIFT threshold) is acknowledged in the
  RealignModal docstring; frontend is correct, backend fix is a
  one-line follow-up tracked.
- e2e foundation spec extended with R6 realignment + history
  flow (9/9 in 10.7s).

## R5 (UI/UX rewrite, 2026-04-30)

- 5-step household wizard shipped at `/wizard/new` (locked decision #7
  — fallback path; doc-drop is primary). Steps: identity, risk
  profile, accounts+goals, external holdings, review+commit.
- `frontend/src/wizard/schema.ts` mirrors `WizardCommitSerializer`
  exactly (verified during the pre-R5 smoke). superRefine validates
  cross-field rules (joint_consent for couple, leg account_index
  bounds).
- State recovery (locked decision #35): per-tab session id keys a
  localStorage draft saved on every step transition + 30s heartbeat;
  recovery banner offers Resume/Discard on mount.
- Step 2 live recompute calls `/api/preview/risk-profile/` with
  `useDebouncedValue(250ms)`; the preview panel is the ONE approved
  surface where T/C/anchor numbers are visible (locked decision #6).
- Commit success → invalidate clients query, set
  rememberedClientId to the new UUID, toast, navigate to `/`.
  AuditEvent `household_wizard_committed` fires (locked decision
  #37 verified live).
- "Add new household" affordance added to ClientPicker; closes the
  popover and navigates to `/wizard/new`.
- e2e foundation spec extended with the full wizard flow
  (8/8 in 7.1s).

## R4 (UI/UX rewrite, 2026-04-30)

- Goal allocation surfaces shipped: hero KPI strip + interactive
  RiskSlider with 5-band override flow (canon 1-5 only; locked
  decision #6) + GoalAllocationSection (current vs ideal vs Δ) +
  OptimizerOutputWidget + MovesPanel + GoalProjectionsSection
  (FanChart + side panel).
- `frontend/src/lib/preview.ts` exports typed query hooks for every
  R1 endpoint (riskProfile/goalScore/sleeveMix/projection/
  projectionPaths/probability/optimizerOutput/moves) plus
  `useOverrideHistory` + `useCreateOverride`. Wire shapes match
  the canonical contracts captured live during the deeper smoke.
- `RiskSlider` saves overrides via POST `/api/goals/{id}/override/`;
  rationale captured via react-hook-form + zod (locked decision #29);
  permission gate via `canEdit`; analyst sees `RiskSliderLocked`
  with a Lock icon + tooltip.
- `FanChart` registers Chart.js v4 line + filler + axis controllers;
  P10–P90 + P25–P75 fills + dotted P50 + amber dashed target line.
  Static probability-at-target badge; hover-debounced per-year
  probability fetch is a follow-up.
- Side-fix: Hypothesis surfaced a pre-existing optimizer frontier
  Pareto-violation edge case during the R4 gate run. Fixed in
  `engine/frontier.py` with `_pareto_filter()` that drops
  dominated points (1e-9 tolerance). 313 pytest passing. Drift
  item #12 marked resolved.
- e2e foundation spec extended with two R4 tests covering the
  goal-page reading surface and the override save → history
  round-trip flow. 7/7 e2e in 6.6s.

## R3 (UI/UX rewrite, 2026-04-30)

- Three-view stage shipped: HouseholdRoute (AUM split strip +
  d3-hierarchy squarified treemap), AccountRoute (KPI strip + Chart.js
  doughnut + AllocationBars + goals-in-account list), GoalRoute (4 KPI
  tiles + reusable `RiskBandTrack` + linked accounts). Click-to-drill
  navigation flows household → account → goal.
- Treemap: SVG render path (not canvas) — accessible (each cell is a
  keyboard-navigable button, role="button" + aria-label with $ value),
  ResizeObserver-driven, paper-2 background to match the v36 aesthetic.
  Click + Enter/Space drill into target.
- Per-kind ContextPanel: extracted into `HouseholdContext.tsx` /
  `AccountContext.tsx` / `GoalContext.tsx` matching the plan's
  filename guidance. ContextPanel layout owns header + collapse +
  Tabs.List; per-kind components own their `<Tabs.Content>` panes.
- `lib/risk.ts` canon-aligned helper: `RISK_DESCRIPTOR_KEYS` +
  `BUCKET_COLORS` + `descriptorFor()` route every risk display
  through canon 1-5 ↔ Cautious / Conservative-balanced / Balanced /
  Balanced-growth / Growth-oriented (locked decision #5). Mockup
  labels not used.
- `RiskBandTrack` is a read-only canon-1-5 marker (locked decision #6
  enforces 5-band picker, never 0-50). role="meter" with
  aria-valuemin/max/now/text. R4 will wrap this in the interactive
  RiskSlider with override rationale.
- `lib/household.ts` mirrors `HouseholdDetailSerializer` exactly
  (Holding / Account / Goal / GoalAccountLink / Member /
  LinkRecommendation / PortfolioRun) plus pure helpers
  (`findGoal`, `findAccount`, `householdInternalAum`,
  `findLinkRecommendation`).
- `lib/treemap.ts` exposes `useTreemap(householdId, mode)` and
  `colorForNode()` palette mapper. `noUncheckedIndexedAccess`-safe
  fallbacks; no non-null assertions.
- `lib/clients.ts` `ClientSummary` shape corrected to match
  `HouseholdListSerializer` (`id`, `display_name`, `total_assets`)
  — the previous R2 sketch used `external_id`/`name`/`total_aum`
  which never existed on the wire.
- `e2e/foundation.spec.ts` extended: client picker → AUM strip +
  treemap render → drill into account → KPI strip → drill into
  goal → risk meter visible.
- Bundle size grew to 586 kB (gzip 188 kB) due to Chart.js +
  d3-hierarchy + lucide-react. Bundle budget deferred to R10
  polish per locked decision #25.

## R2 (UI/UX rewrite, 2026-04-30)

- Frontend chrome shipped: TopBar (BrandMark + ClientPicker + ModeToggle
  + Report + Methodology + UserChip with logout), ContextPanel (Radix
  Tabs with per-kind tab definitions, collapse-to-rail mode persisted
  to localStorage), six empty route placeholders, LoginRoute.
- BrowserRouter + role-based routing: advisors land at `/` (HouseholdRoute),
  financial_analysts auto-redirect to `/cma`. Per-route ErrorBoundary
  via RouteFrame component (locked decision #31a).
- shadcn-pattern primitives in `frontend/src/components/ui/`: Button
  (cva variants: default/outline/ghost/toggle/link/destructive),
  Skeleton (paper-2 shimmer), Toaster wrapping Sonner with paper/ink
  toast classNames (locked decision #21).
- Lucide icons replace decorative unicode glyphs (⌂ ⚡ ∑ ▼ ‹ ›) to
  satisfy `eslint-plugin-i18next/no-literal-string` (locked decision
  #28a) without polluting i18n catalogs.
- Lib helpers added: `api.ts` (CSRF-aware fetch wrapper),
  `auth.ts` (useSession/useLogin/useLogout), `clients.ts` (useClients),
  `debounce.ts` (useDebouncedValue), `format.ts` (CAD currency +
  compact + percent), `local-storage.ts` (typed prefs hook — strict
  no-PII discipline per locked decision #32b), `toast.ts`,
  `api-error.ts`.
- New `e2e/foundation.spec.ts` covers chrome smoke (login → topbar →
  household stage → methodology nav → analyst-to-CMA bounce). Replaces
  the deleted legacy `synthetic-review.spec.ts` /
  `portfolio-cma.spec.ts` which targeted the old App.tsx shell
  (rebuilt at R7 / R9 per the plan); `package.json` `e2e:synthetic`
  script repointed.
- i18n keys added under `topbar.*`, `ctx.*`, `routes.*`, plus
  `auth.role_unsupported` and `scaffold.phase_label_r2`. fr.json
  remains placeholder (locked decision #12).
- Locked decision #20 honored: no feature flag — old App.tsx
  is fully replaced, no two-shell coexistence.
- Locked decision #2 honored: chrome triggers all data via
  TanStack Query; no client-side computation duplication.

## R1 (UI/UX rewrite, 2026-04-30)

- 4 new Django models added (`web/api/models.py` + `0008_v36_ui_models.py`):
  `RiskProfile` (one-to-one with Household), `GoalRiskOverride`
  (append-only, latest-row-wins per goal, DB CHECK constraint enforces
  rationale min length 10), `ExternalHolding` (sum=100 validation),
  `HouseholdSnapshot` (append-only with trigger taxonomy per locked
  decision #36).
- 18 new DRF endpoints under `/api/preview/`, `/api/households/`,
  `/api/goals/` (10 read-only preview + 8 state-changing).
- Engine adapter extensions in `web/api/engine_adapter.py`:
  `to_engine_risk_profile`, `active_goal_override`,
  `current_holdings_to_pct`, `household_aum`.
- Concurrency safety per locked decision #30:
  `_resolve_household_for_write` does scope-check first then
  `select_for_update()` to avoid Postgres outer-join lock rejection.
- Audit-event regression suite (`test_r1_audit_emission.py`, locked
  decision #37): `_assert_audit_event(action, count, scope)` helper
  asserts every state-changing endpoint fires exactly the expected
  count of AuditEvent rows. Read-only preview endpoints emit ZERO
  events.
- 30 new tests (16 endpoint behavior + 14 audit-emission). Full pytest:
  313 passed in 31.33s.
- Locked decision #6 enforced at the API layer: serializer + endpoint
  responses NEVER include the internal Goal_50 / 0-100 T/C numbers;
  surface is canon 1-5 + descriptor + flags + derivation.
- Locked decision #14 vocabulary CI guard remains green; new endpoint
  bodies + audit detail strings respect re-goaling discipline.

## R0 (UI/UX rewrite, 2026-04-30)

- Cut `feature/ux-rebuild` from `main` for the rewrite.
- Five new pure engine modules added: `risk_profile.py`, `goal_scoring.py`,
  `projections.py`, `moves.py`, `collapse.py`. All pure Pydantic; canon
  §9.4.2 boundary preserved (`engine/tests/test_engine_purity.py` enforces).
- v36 8-fund universe (locked decision #3): `engine/sleeves.py` updated to
  include Founders + Builders + `SLEEVE_REF_POINTS` calibration table +
  display colors and names. Fixture already 8-fund.
- Locked decision #6: Goal_50 is internal engine intermediate only; API
  surface returns canon 1-5 + descriptor + flags.
- Locked decision #5: canon-aligned client-facing labels
  (Cautious / Conservative-balanced / Balanced / Balanced-growth /
  Growth-oriented) used everywhere; mockup labels retired.
- 216 engine parity + property + purity tests passing.

## Phase 4.0 — Bedrock tool-use SDK probe (2026-05-02)

Probed forward-compat across active + future model classes via
`AnthropicBedrock.messages.create(..., tools=[...])` with explicit
long-term `AKIA*` creds (account `865045593529`, region `ca-central-1`).

| Model | Short id | Inference-profile ARN | Result |
|---|---|---|---|
| Sonnet 4.6 (active) | `global.anthropic.claude-sonnet-4-6` | `arn:aws:bedrock:ca-central-1:865045593529:inference-profile/global.anthropic.claude-sonnet-4-6` | tool_use OK; stop_reason=tool_use |
| Opus 4.6 | `global.anthropic.claude-opus-4-6` | (ARN form) | `BadRequestError 400 — model identifier is invalid` (not provisioned in this Bedrock subscription) |
| Opus 4.7 | `global.anthropic.claude-opus-4-7` | (ARN form) | tool_use OK; stop_reason=tool_use |

Decision: **proceed Phase 4.1+** with tool-use migration. Active model
(Sonnet 4.6) supports tool-use end-to-end; forward-compat to Opus 4.7
verified. Opus 4.6 is an availability gap (AWS account config) not a
capability gap; `BEDROCK_MODEL` env can be bumped to either Sonnet 4.6
or Opus 4.7 without code change post-migration.

Auth gotcha worth recording: a stale `AWS_SESSION_TOKEN` set in a
local shell env will be picked up by the boto3 credential chain and
silently override explicit `aws_access_key`/`aws_secret_key` passed
to `AnthropicBedrock(...)`, surfacing as `PermissionDeniedError 403
"security token expired"`. Local validation runs that touch Bedrock
should prefix with `unset AWS_SESSION_TOKEN` (or run in a Docker
container with no inherited STS context). Worker-via-docker-compose
isn't affected.


---

## Engine→UI Display Integration (2026-05-03/04)

Sub-sessions #1-#5 closed the gap between the engine's `PortfolioRun`
output and the advisor's eyes. 111 locked decisions distilled from
`~/.claude/plans/i-want-you-to-jolly-beacon.md` (deleted at A6.16
close-out per locked #11+#42 lifecycle). Tag `v0.1.2-engine-display`
at HEAD `e5cd859`.

### Architecture (8 entries)
- **#1** Phased delivery: A1-A5 demo-bar; A6 pilot-bar via 3-round sub-agent orchestration (#20).
- **#9** Failure surfacing: typed-skip silent + audit; unexpected → catch-all + audit + `latest_portfolio_failure` SerializerMethodField + Banner inline + Sonner toast.
- **#14** 8 trigger points: review_commit + wizard_commit + override + realignment + 4 workspace-level (conflict_resolve / defer_conflict / fact_override / section_approve).
- **#27** Workspace-level triggers gate on `linked_household_id is None` (silent-skip + observability audit).
- **#56** Strict P99 ≤ 1000ms threshold; sync vs threading decision locked at A0.2.
- **#74** Auto-trigger SYNCHRONOUS inside `transaction.atomic`; response IS truth (not `transaction.on_commit`).
- **#80** PostgreSQL pool to 150 + max_connections to 200 supports 100-parallel commits.
- **#81** Helper-managed atomic (Django nested-atomic via savepoints); reusable check OUTSIDE atomic so audit emits persist on raise.

### UX (12 entries)
- **#5** Goal "ideal mix" source: `EngineOutput.goal_rollups[].allocations` (engine pre-computed; honors locked #2 server roundtrip).
- **#6** Moves: modify `/api/preview/moves/` in place; reads `ideal_pct` from `goal_rollups` when run exists; SLEEVE_REF_POINTS calibration fallback. Response includes `source: "portfolio_run" | "calibration"`.
- **#10** HouseholdRoute portfolio rollup panel placement: between AUM strip and treemap.
- **#18** Stale state UX: muted run-data + accent-bordered overlay with Regenerate CTA.
- **#19** HouseholdPortfolioPanel mirrors RecommendationBanner failure pattern.
- **#24** Dual-line FanChart: engine canonical solid + calibration what-if dotted (DEFERRED to post-pilot).
- **#28** State precedence: failure > stale > success.
- **#29** Multi-link goal: dollar-weighted P50 single line.
- **#75** i18n keys distribute under existing feature namespaces (`routes.goal.*`, `routes.household.*`).
- **#78** AdvisorSummaryPanel multi-link: default-collapsed Radix Accordion (first link expanded). NOTE: shipped as inline render with border-t-hairline separators (simpler; equivalent UX).
- **#90** Dual-line FanChart includes explicit Legend + axe + Vitest tests (DEFERRED with #24).
- **#109** `aria-live="polite"` on RecommendationBanner + HouseholdPortfolioPanel (WCAG 4.1.3 Status Messages).

### Operational (10 entries)
- **#7** Sandra/Mike PortfolioRun seeded at end of `load_synthetic_personas`. Demo-ready DB via `reset-v2-dev.sh --yes`.
- **#8** Auto-trigger fires on every committed household (synthetic + real-PII).
- **#13** Demo-prep `scripts/demo-prep/upload_and_drain.py` extended (auto-seed PortfolioRun for committed real-PII households).
- **#22** A6.11 real-PII auto-trigger smoke (Niesner) — DEFERRED to authorized session.
- **#23** Cross-browser scope: A6 manual gate (webkit + firefox); not CI-integrated.
- **#34** `bash scripts/reset-v2-dev.sh --yes` is the only pre-authorized real-PII path; specific Bedrock uploads require per-target authorization.
- **#69** session-state.md update enforcement at every sub-session boundary.
- **#79+#86** A6.11 Niesner uses delete-then-upload (preserves Seltzer/Weryha demo state).
- **#88** Demo dress rehearsal: 10s threshold for trigger steps; 8s for non-trigger.
- **#89** OTEL spans wrap `_trigger_portfolio_generation`; no-op locally; backend-ready.

### Testing (15 entries)
- **#17** Comprehensive Vitest scope: ~60-80 unit tests across new components.
- **#20** A6 sub-agent orchestration: 3 sequential rounds, 2 parallel agents per round + 1 in round 3.
- **#46** Sub-session #1 must-pass gate before #2.
- **#55** mockHousehold byte-for-byte production payload shape (cost-key bug at `2bd77d3` was fixture/payload drift).
- **#60** §Y comprehensive testing & regression matrix (14 layers).
- **#61** 85% line coverage gate on touched modules.
- **#63** Visual regression baseline maintenance (per-PR workflow + intentional-diff handling).
- **#64** StrictMode double-invoke tests for every new component (DocDropOverlay regression at `bca0112`).
- **#71** Test selectors must match accessible-name resolution (aria-label > visible text in Playwright role-name; lesson from `b14a199` visual-verification gap closure).
- **#82** Visual-verification spec is single source of truth; A6 Round 3 EXTENDS rather than replaces.
- **#84** mockHousehold factory at `frontend/src/__tests__/__fixtures__/household.ts`.
- **#85** Bundle size gate < 290 kB gzipped (measured 267.22 kB).
- **#96** Full advisor lifecycle integration test (catches sequential cross-trigger interactions).
- **#99** Audit-trail integrity Hypothesis property test (catches `str(exc)` regression class explicitly).
- **#102** Pool capacity regression at 120 concurrent connections.
- **#103** Rollback smoke test (kill-switch + verify graceful degradation; helper-level + HTTP-level).
- **#104** A3.1 expectTypeOf type-safety regression tests.
- **#106** Vitest cache-invalidation tests for useGeneratePortfolio.
- **#X.10** Sub-agent verification protocol — Read every file the agent edited; re-run tests; spot-check citations; verify locked-decision compliance. Caught 4 real bugs across sub-sessions (1 i18n at sub-session #4 + 1 BLOCKING + 2 CRITICAL via code-reviewer at A6.14).

### Documentation (8 entries)
- **#11** Tag bump v0.1.2-engine-display + design-system.md update at end of A6.
- **#21** CHANGELOG.md + `docs/agent/ops-runbook.md` entries at A6.13.
- **#42** Dedicated starter prompt for multi-sub-session execution (deleted at A6.16 close-out).
- **#83** CHANGELOG entry version-stamped at A6.13.
- **#91** A6.16 migrates 111+ decisions to `docs/agent/decisions.md` (this entry).

### Continuity (12 entries)
- **#43** Within-sub-session compaction discipline (halt at next natural breakpoint).
- **#44** Per-phase commit message format (citing locked-decision numbers).
- **#45** Per-phase verbose ~400-word handoff-log entry.
- **§X.1** Sub-session boundary protocol (commit + handoff + dossier + memory update before suggesting compact).
- **§X.2** Sub-session boot protocol (read MEMORY → starter → dossier → handoff-log → plan).
- **§X.7** Starter-prompt lifecycle (created in A0.0; deleted in A6.16).

### Meta (6 entries)
- Communication style: cite specific evidence (commit hash, regression test ids, gate output tail); never "looks good".
- Anti-patterns: tests pass ≠ ship-ready; subagent says it's done ≠ verified; mock fixtures must mirror production payload byte-for-byte.
- Code-reviewer subagent pattern: dispatch on cumulative diff at A6.14; expect findings; fix before tag.

### Reference

- Plan file (deleted at A6.16 close-out): `~/.claude/plans/i-want-you-to-jolly-beacon.md`
- Starter prompt (deleted at A6.16 close-out): `docs/agent/engine-ui-display-starter-prompt.md`
- Architecture detail: `docs/agent/design-system.md` "Engine output consumption" section
- Operational detail: `docs/agent/ops-runbook.md` §1
- Rollback procedure: `docs/agent/pilot-rollback.md` "Engine→UI Display Rollback (v0.1.2-engine-display)" section
