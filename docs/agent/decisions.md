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

- Fund-of-funds collapse suggestions, real tax-drag math, compliance ratings,
  and richer report-grade fan charts are still missing from the Fraser path.
- Household and goal risk now use the 1-5 optimizer mapping. Remaining work is
  the documented household x goal composite weighting, not scale migration.
- Visible household/goal risk score labels should stay numeric 1-5. Qualitative
  low/medium/high vocabulary is reserved for source facts or compliance/internal
  mapping and should not be used as the advisor-facing construction score.
- Current extraction/review is a secure-local scaffold, not full canon Layer 1-5:
  richer source review, temporal reconciliation, IS validation, pseudonymization,
  retention/disposal, and CI PII checks are still needed.
- Current audit log has append-only protection, sanitized timeline events, and
  an advisor audit drawer/export for portfolio runs. Full compliance audit
  browser UI remains deferred.
- Current RBAC has authenticated-by-default access, advisor team scope, and
  financial-analyst PII denial, but Phase B still needs MFA/session policy,
  lockout, password reset, and admin-only CMA boundaries.

## Deferred

- Staging deployment.
- Full pseudonymization workflow and CI PII scanners.
- Real Croesus, Conquest, custodian, or LLM integrations.
- Audit browser UI.
