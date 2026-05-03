# Changelog

All notable changes to MP2.0 are documented here. The format
adheres to [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow `vMAJOR.MINOR.PATCH-pre`. The current pilot is
tagged `v0.1.0-pilot`.

## v0.1.0-pilot — 2026-05-08

Limited-beta pilot release for 3-5 advisors at Steadyhand on
real-PII workflows.

### Added

- **Bedrock tool-use extraction** (Phase 4) — replaces the
  free-form-JSON path with Anthropic's tool-use API.
  Eliminates the JSON-repair surface (REPAIR-1 + REPAIR-2)
  entirely; structurally impossible failure shapes
  (markdown tables, prose preambles, alternate-key drift) are
  removed at the API layer. SDK probe verifies forward-compat
  on Sonnet 4.6 + Opus 4.7. Per-doc-type prompt modules in
  `extraction/prompts/{base,kyc,statement,meeting_note,planning,generic}.py`
  with shared no-fabrication guidance + canonical-vocabulary
  + canonical-field-inventory. Confidence floor caps fact
  confidence to one tier above classification confidence
  (PROMPT-5 semantics); `multi_schema_sweep` classification
  routes to the generic builder.
- **OpenAPI-typescript codegen + drift CI gate** (Phase 4.5)
  — `frontend/src/lib/api-types.ts` generated from
  drf-spectacular's `/api/schema/`; `scripts/check-openapi-codegen.sh`
  fails CI on drift. Closes the FE/BE enum-drift bug class.
- **Conflict-resolution card UI + endpoint** (Phase 5a) —
  `POST /api/review-workspaces/<wsid>/conflicts/resolve/` with
  atomic + select_for_update, structured failure codes,
  rationale capture, evidence-ack checkbox. Per-conflict
  candidate enrichment with redacted evidence quotes. New
  frontend `ConflictPanel` + `ConflictCard` components wired
  into the Review screen.
- **Pilot disclaimer banner with server-side audit-tracked
  acknowledgement** (Phase 5b.1) — `AdvisorProfile` model
  (1:1 with `auth.User`) holds `disclaimer_acknowledged_at`
  + `disclaimer_acknowledged_version`. Endpoint
  `POST /api/disclaimer/acknowledge/` emits
  `disclaimer_acknowledged` audit event with metadata
  `{version, advisor_id, ip, user_agent, acknowledged_at}`.
  Bumping `DISCLAIMER_VERSION` triggers re-ack.
- **In-app feedback infrastructure** (Phase 5b.1) — `Feedback`
  model with Linear-mirroring schema; `POST /api/feedback/`
  for advisor submit, `GET /api/feedback/report/`
  (analyst-only with status/severity/since/advisor filters
  + CSV export), `PATCH /api/feedback/<id>/` for ops triage.
  Django admin registered.
- **First-login welcome tour** (Phase 5b.6) — 3-step
  coachmark with server-side ack via `tour_completed_at`
  User-profile field; `POST /api/tour/complete/` is
  idempotent + audit-event-emitting.
- **Worker health banner** (Phase 5b.2) — renders only when
  `worker_health.status` is stale/offline AND active jobs > 0.
- **Polling backoff** (Phase 5b.7) — `useReviewWorkspace`
  exponential backoff with jitter once stillProcessing
  (3s base → 30s max).
- **Confidence chip component** (Phase 5b.9) — color + text +
  ARIA label single-source rendering; not color-only per
  WCAG 2.1 AA. Wired into `ConflictPanel.CandidateRow`.
- **axe-core a11y testing in Playwright** (Phase 5b.14) +
  `pilot-features-smoke.spec.ts` covering banner + feedback +
  axe scans on `/` + `/review`.
- **Append-only `FactOverride` model** (Phase 5b.10/11
  foundation) — append-only via the `HouseholdSnapshot`
  pattern; latest-row-wins per `(workspace, field)`.
- **Pilot rollback procedure** (`docs/agent/pilot-rollback.md`)
  — severity classification, kill-switch, code revert,
  DB recovery, on-call list, post-incident audit.
- **Pilot success metrics + end-criteria**
  (`docs/agent/pilot-success-metrics.md`) — quantitative bars,
  weekly cadence, GA criteria, off-ramp conditions.
- **Pilot advisor provisioning command** (Phase 8.5) —
  `python web/manage.py provision_pilot_advisors --config-file=...`
  reads YAML from `MP20_SECURE_DATA_ROOT`, idempotent, audit-
  event-emitting per advisor. Refuses plain-text passwords.

### Fixed

- **ENUM-CASE engine-adapter normalization** (Phase 1) —
  `regulatory_objective`, `regulatory_time_horizon`,
  `regulatory_risk_rating`, `marital_status` now case-normalize
  before engine consumption. Real-PII Bedrock outputs
  capitalized values; the engine `Literal` validators were
  rejecting silently before this fix.
- **PII leak class** (Phase 2) — 11+ sites scrubbed across
  `views.py`, `preview_views.py`, `review_processing.py`.
  New `web/api/error_codes.py` is the single source of truth
  for exception → structured `failure_code` mapping. Audit
  metadata records structured codes only; raw exception text
  never reaches DB columns / API response bodies / audit rows.
  CI gate `scripts/check-pii-leaks.sh` prevents regression.
  `_REDACTION_PATTERNS` extended with routing numbers, phone
  numbers, addresses.
- **Manual-entry concurrency** (Phase 3 / BUG-1) —
  `ReviewDocumentManualEntryView.post` decorated
  `@transaction.atomic` + document fetched via
  `select_for_update()`. Concurrent advisor calls now
  serialize cleanly.
- **Reconcile-enqueue ordering** (Phase 3 / REC-1) —
  `process_document` wraps fact bulk_create + FACTS_EXTRACTED
  state save + enqueue_reconcile in one atomic block.
  Eliminates the "advisor sees stuck state forever if enqueue
  fails after job COMPLETED" friction class.
- **Confidence floor over-aggressive cap** (Phase 4
  hardening) — refined `_cap_fact_confidence` to
  `min(rank+1, 3)` semantics. Low classification floors HIGH
  to MEDIUM but doesn't collapse medium to low.
- **Per-doc-type prompt narrowed extraction under
  multi_schema_sweep** (Phase 4 hardening) — dispatcher now
  routes to `generic.build_prompt` when classification route
  is `multi_schema_sweep`, regardless of `document_type`.

### Audit

- 50+ user-locked decisions documented in
  `docs/agent/decisions.md`.
- 8+ commits past `f5f2519` baseline this pilot wave.
- Tests: 362 baseline → **422** (+60 net new) with full gate
  green per phase. Phase 9 will add Hypothesis property suites
  + concurrency stress + edge cases + migration rollback +
  100% coverage gate.
- Phase 7 R10 partial sweep against 12 real-PII docs: total
  365 → 215 facts (−41% recall) with canon §9.4.5
  quality wins (eliminated ~40 hallucinated section paths +
  2 defaulted facts; cut inferred-fact count from ~52 to ~16).
  Trade-off accepted by user; Phase 9 plans the post-pilot
  recovery iteration.

### Deferred to Phase 9 (post-pilot)

- Fact-quality iteration to recover legitimate recall in the
  −41% without re-introducing hallucinations.
  See `docs/agent/phase9-fact-quality-iteration.md`.

### Deferred to a later release

- Phase 5b polish (5b.3 inline failed-doc CTAs,
  5b.4 DocDropOverlay improvements, 5b.5 DocDetailPanel
  slide-out, 5b.7 ClientPicker pagination, 5b.8
  session-interruption recovery, 5b.10/11 FactOverride
  end-to-end UI, 5b.12/13 bulk + defer conflict UI).
- Phase 5c UX spec docs.
- Phase 6 Hypothesis + concurrency stress + factory_boy +
  Vitest unit tests + edge-case scenarios + per-migration
  rollback tests + 100% coverage gate.
- Phase 6.9 perf budget gate (P50 < 250ms / P99 < 1000ms).

These ship in subsequent sub-sessions before the 2026-05-08
release.
