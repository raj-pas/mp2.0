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
- Add light real audit logging in Phase 1; defer immutability triggers.
- Real-upload features require `MP20_SECURE_DATA_ROOT` outside the repo and hard
  fail if it is missing or repo-local.
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
- Failed documents do not block review. Manual retry queues another processing
  job.

## Canon v2.3 Decisions to Implement Next

- Delivery is Phase A/B/C: Som-demo-grade scaffold, pilot hardening with IS
  validation, then controlled advisor pilot.
- Phase A is not pilot-grade. Phase B exit criteria gate any advisor login.
- Steadyhand remains v1 launch context; Sandra/Mike Chen remains the synthetic
  backup persona.
- Engine optimization unit is goal x account (`GoalAccountLink`), then
  account-level and household-level rollups.
- Recommended portfolio always comes from the efficient frontier. Whole-portfolio
  funds such as Founders/Builders are execution collapse suggestions, not
  separate optimizer shortcuts.
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
- CMA assumptions and efficient-frontier visualization are admin-only.
- The advisor UX centers on a three-tab household/account/goal view with fund vs
  asset-class look-through and a click-through goal-account assignment workflow.
- Current vs ideal allocation must be visible together on recommendation screens.
- Reporting supports Tier 1/2/3 sophistication from the same deterministic
  engine numbers. AI may style the narrative but cannot invent numbers.
- Pre-recommendation overrides adjust inputs and rerun the engine; post-
  recommendation overrides require an inline rationale note.
- Real-derived personas require pseudonymization, Bedrock ca-central-1 routing,
  and legal/IT authorization before any real PII enters the build environment.

## Architecture Defaults

- Django + DRF backend.
- React + Vite frontend.
- Pydantic v2 for engine schemas.
- Postgres for local persistence.
- TanStack Query for frontend data fetching.
- Ruff and pytest for Python checks.
- Vite build/typecheck for frontend smoke checks.

## Known Scaffold Mismatches

- Engine output currently has `goal_blends`; canon v2.3 requires `LinkBlend`,
  account rollups, fund-of-funds collapse suggestions, resolved risk per link,
  fan chart data per link, compliance ratings, and richer audit trace.
- Current risk code uses a 1-10 placeholder and can emit non-grid percentiles.
- Current `Goal.target_amount` is required; canon treats target dollars as
  optional unless volunteered.
- Current UI surfaces low/medium/high in visible risk badges; canon reserves that
  vocabulary for internal/compliance mapping.
- Current extraction/review is a secure-local scaffold, not full canon Layer 1-5:
  richer source review, temporal reconciliation, IS validation, pseudonymization,
  retention/disposal, and CI PII checks are still needed.
- Current audit log has writes but not immutability trigger, browse UI, or full
  input-to-output trace.
- Current RBAC hook allows all access; Phase B needs real role enforcement.

## Deferred

- Staging deployment.
- Strict extraction/PII workflow.
- Real Croesus, Conquest, custodian, or LLM integrations.
- Full audit immutability triggers and audit browser UI.
