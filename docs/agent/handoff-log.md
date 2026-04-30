# MP2.0 Handoff Log

## 2026-04-28 — Phase 1 Scaffold Started

- User approved implementation of the Phase 1 runnable MVP scaffold.
- Chosen defaults: main-direct work, local commits only, repo-file memory,
  Claude-first instructions, Docker Compose first, Python 3.12, Node 22,
  `uv + npm`, Ruff/pytest/frontend build smoke checks.
- Non-blockers remain tracked in `open-questions.md`.

## 2026-04-28 — Phase 1 Scaffold Implemented

- Added root tooling: `pyproject.toml`, `uv.lock`, `.python-version`,
  Dockerfile, Docker Compose, README, `.env.example`, `.gitignore`, and smoke CI.
- Added `CLAUDE.md` plus agent memory docs under `docs/agent/`.
- Added pure `engine/` package with Pydantic schemas, illustrative Steadyhand
  sleeves, optimizer stub, compliance stub, and tests.
- Added Django/DRF backend with DB models, migrations, synthetic persona loader,
  web-to-engine adapter, light audit table/writer, and API tests.
- Added React/Vite/Tailwind advisor shell wired to client list/detail and
  generate-portfolio API calls.
- Added extraction/integration adapter placeholders for future phases.
- Verification passed: Ruff check, Ruff format check, pytest, frontend build,
  Docker Compose config validation, Django check, migrations, and synthetic
  persona load.
- Docker Compose is running after a restart; backend logs show successful 200
  responses for client list, client detail, and generate-portfolio calls.
- `npm install` reported 2 moderate dependency audit findings; no automatic fix
  was applied during scaffold implementation.

## 2026-04-28 — Detail Financial Summary Fix

- Fixed `$NaN` in the advisor shell by adding `goal_count` and `total_assets`
  to the household detail API response, matching the list API shape.
- Added a backend regression test that asserts the Sandra/Mike detail payload
  includes `goal_count = 3` and `total_assets = 1280000`.
- Also moved the Docker backend virtualenv to `/opt/mp20-venv` so local `uv run`
  commands do not break the bind-mounted container runtime.

## 2026-04-28 — Canon v2.3 Review and Memory Sync

- Reviewed `MP2.0_Working_Canon.md` v2.3, `CLAUDE.md`, `docs/agent/*`, README,
  engine, web, frontend, extraction, integration, Docker, CI, and persona files.
- Synced agent memory to the Day-2 lock-ins: Phase A/B/C delivery, goal-account
  optimization unit, 5-point risk mapping, three-tab advisor view, tax-drag
  schema, CMA admin boundary, real-PII blockers, pilot gates, and override
  patterns.
- Recorded key scaffold drift for future sessions: engine still returns
  goal-level Phase 1 output, extraction is stubbed, auth/RBAC is Phase 0, PII
  controls are incomplete, audit is light, and the UI lacks the three-tab /
  click-through recommendation workflow.

## 2026-04-28 — Secure-Local Review Tranche Implemented

- Added secure-root validation for `MP20_SECURE_DATA_ROOT`; upload/review hard
  fails if the root is missing or inside the repository.
- Added local advisor bootstrap, review workspace/document/job/fact/state/
  approval models, migration, serializers, APIs, and tests.
- Added Postgres-backed worker command `process_review_queue` with transactional
  claim, retry policy, local parsers, Bedrock fail-closed routing, structured
  fact storage, and reviewed-state reconciliation.
- Added sensitive identifier hash/redacted-display handling and minimally
  redacted evidence quotes.
- Added React review workflow: login, workspace creation, upload/status, active
  jobs, facts, quick-fill edits, section approvals, readiness, retry, matches,
  and link-or-create commit.
- Updated Docker Compose with a `worker` service sharing Postgres and the secure
  data-root mount.
- Updated README, `.env.example`, `CLAUDE.md`, and agent memory for the new
  secure-local workflow and safety rules.
- Verification passed: `uv run ruff check .`, `uv run pytest`, `npm run build`.

## 2026-04-28 — Browser E2E Review Flow Verified

- Ran a complete Chrome-headless browser E2E using synthetic upload content and
  AWS/Bedrock credentials loaded from `ike-agent/.env` without printing secrets.
- Flow covered: local login, review workspace creation, browser upload, worker
  processing, Bedrock extraction, visible extracted facts, `engine_ready`,
  section approval, match step, create-household commit, and client detail.
- Final E2E evidence showed committed workspace
  `review_58042dfd-b4a7-456f-a384-85f35c147c6e` with one account and one goal;
  screenshot saved at `/tmp/mp20-e2e-final.png`.
- E2E uncovered and fixed: session endpoint not reporting authenticated sessions,
  strict Bedrock JSON parsing, inability to reconcile indexed fact paths like
  `accounts[0].current_value`, and scalar sensitive identifier values not being
  hashed/redacted.
- Verification after fixes passed: `uv run ruff check .`, `uv run ruff format
  --check .`, `uv run pytest`, and `npm run build`.

## 2026-04-28 — Client/Auth Boundary Hardened

- Tightened the default DRF permission hook from allow-all to authenticated-by-
  default. Login/session remain explicit public endpoints.
- Added explicit login requirements for client list, client detail, and
  generate-portfolio APIs.
- Added nullable `Household.owner`; shared synthetic households can remain
  ownerless, while reviewed-state commits create advisor-owned households.
- Scoped client list/detail/generate access to shared synthetic plus the
  authenticated advisor's households; commit link targets must be owned by the
  current advisor.
- Updated the frontend so client queries and visible client data are gated by
  session auth.
- Added regression tests for unauthenticated denial, household visibility
  scoping, owner-scoped commits, and cross-advisor link rejection.
- Verification passed: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run pytest`, `npm run build`, and a Chrome-headless UI check confirming
  no client data before login and visible client/review UI after login.

## 2026-04-29 — Review Self-Link Candidate Fixed

- Fixed a committed-workspace UX/API regression where the already-linked
  household could appear as a link candidate through backend matching or the
  frontend fallback matcher.
- Backend matching now returns no candidates for linked/committed workspaces,
  commit clears stale match candidates, repeated commit is idempotent for the
  linked household, and relinking a committed workspace to another household is
  rejected.
- Frontend link/create controls are hidden once the workspace is linked, and
  fallback matches exclude the linked household.
- Added regression tests for match scoring, self-link suppression, idempotent
  commit, and relink rejection.
- Verification passed: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run pytest`, and `npm run build`.

## 2026-04-29 — Docker Compose Worker Real-Bundle Run

- Stopped the old local Django/Vite processes and created a gitignored `.env`
  for Docker Compose using ike-agent AWS credentials without printing secrets.
- Set the secure data root to `/private/tmp/mp20-secure-data`, matching the
  previously uploaded files, and started the full Compose stack.
- Transferred the queued review workspace metadata from the prior local SQLite
  run into Compose Postgres via the secure data root so the worker could process
  the already-uploaded bundle.
- Read the Compose log stream through worker processing. The worker stored
  structured facts for the successfully extracted documents; some documents
  failed after retries because Bedrock output did not parse as valid JSON.
- Fixed reconciliation for qualitative risk facts such as `Low`, which had been
  crashing state reconciliation when coerced directly to `int`.
- Final Compose state for that bundle: workspace is `review_ready`; successful
  documents reconciled and failed documents remain visible for retry/manual
  handling; `engine_ready` remains blocked by missing account values/holdings
  marker, goal horizon, and advisor-confirmed goal-account mapping.
- Verification passed: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run pytest`, and `npm run build`.

## 2026-04-29 — Secure Ingest Hardening + Advisor Review Implemented

- Hardened real-upload safety: real-derived upload now requires an outside-repo
  `MP20_SECURE_DATA_ROOT` and Postgres by default; synthetic upload remains
  testable on SQLite.
- Added advisor team access semantics plus financial-analyst PII denial.
- Added immutable audit protections with model guards and DB triggers, sanitized
  workspace timeline serialization, edit audit hashes, and kill-switch audit
  events.
- Added worker heartbeat/stale-job visibility, retry/failure metadata, duplicate
  reconcile suppression, manual reconcile endpoint, typed Bedrock fact schema
  validation, JSON repair, OCR overflow metadata, and artifact disposal/report
  command.
- Replaced Quick Fill with advisor-grade editable review sections for household,
  people, accounts, goals, goal-account mapping, and risk, including provenance
  snippets, override reasons, conflict/unknown hooks, approval statuses/notes,
  and strict `engine_ready + required approvals` commit gating.
- Improved committed client display with defensive financial formatting and
  clearer account/goal/mapping/holdings empty states.
- Added Playwright synthetic E2E config/spec, local real-bundle regression
  scaffold, CI Docker Compose E2E job, and ignored Playwright artifact folders.
- Verification passed: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run pytest`, `npm run build`, and Playwright test discovery for synthetic
  and real-regression specs.
- Full local synthetic Playwright execution was attempted against Docker Compose
  but could not launch because local Chromium was missing; the browser install
  command hung and was terminated. CI is configured to install Chromium before
  running the synthetic browser E2E.

## 2026-04-29 — Postgres Foundation + Fraser PortfolioRun Implemented

- Removed SQLite fallback from active settings; `DATABASE_URL` is now required
  and must be Postgres.
- Added `scripts/test-python-postgres.sh` and updated docs/CI expectations
  around Postgres-backed pytest.
- Extended local bootstrap to create advisor and financial analyst users from
  env vars.
- Extracted tracked Fraser v1 fixtures from the reference HTML without
  committing the source HTML, then ported covariance/frontier/percentile/
  projection math into pure `engine/`.
- Replaced the legacy goal-blend engine path with goal-account-link
  recommendations, goal/account/household rollups, current-vs-optimal
  comparison, projection points, warnings, and Fraser audit trace.
- Added CMA snapshot/fund/correlation models, seed command, analyst-only
  draft/update/publish APIs, efficient frontier API, and frontend CMA modal.
- Added immutable `PortfolioRun` plus link recommendation rows, run hashes,
  committed construction input snapshots, output JSON, advisor summary,
  technical trace, stale/current state, and frontend run history.
- Added PlanningVersion snapshots for advisor planning edits and stale marking.
- Tightened review-state versioning under Postgres row locks after browser E2E
  exposed fast-edit collisions/stale merges.
- Updated browser E2E to cover synthetic review commit, advisor portfolio
  generation/history, and financial analyst CMA/frontier workflow.
- Verification passed: `uv run ruff check .`, `uv run ruff format --check .`,
  `scripts/test-python-postgres.sh`, `npm run build`, and Docker Compose
  `PLAYWRIGHT_BASE_URL=http://localhost:5173 npm run e2e:synthetic`.

## 2026-04-29 — CMA Workbench + Optimizer Validation Implemented

- Renamed runtime CMA surfaces to Default CMA and replaced the seed command with
  `seed_default_cma`.
- Rebuilt the analyst CMA surface as CMA Workbench with tabs for snapshots,
  assumptions, correlations, frontier, and audit.
- Added one-open-draft behavior, full valid assumption/correlation saves,
  editable eligibility, publish notes, analyst-visible audit summaries, and
  Chart.js frontier rendering with fund points.
- Tightened CMA API access so raw CMA assumption/frontier/audit surfaces are
  financial-analyst-only.
- Added SciPy oracle checks, Hypothesis property tests, invalid matrix tests,
  and a committed synthetic validation pack under `docs/validation/`.
- Added CI upload of Playwright report/test-results on browser E2E failure.

## 2026-04-29 — Secure Review Portfolio-Ready Handoff Implemented

- Added `construction_ready` beside `engine_ready`; review commit now requires
  both readiness gates plus required section approvals, while portfolio
  generation remains an explicit post-commit advisor action.
- Migrated household and goal risk to the canon 1-5 contract. Legacy 1-10 values
  are remapped with `ceil(old / 2)` during migration, API/model/engine
  validation rejects new values above 5, and stale `/10` UI labeling was removed.
- Reused portfolio generation blockers for both construction readiness and
  post-commit generation so unsupported account types or missing construction
  facts fail consistently before a PortfolioRun is created.
- Removed the unused Quick Fill path from the review UI and extended the
  synthetic browser flow to commit, open the client, explicitly generate a
  portfolio, and check run history. The CMA Workbench E2E publish-note locator
  was tightened to avoid ambiguous matches.
- Tightened the real-bundle local Playwright harness so it filters empty bundle
  directories, uses generic bundle-number labels, avoids broad text locators,
  and keeps logs/screenshots/traces under `MP20_SECURE_DATA_ROOT`.
- Added regression coverage for stale 1-10 risk values, construction-readiness
  blocking, post-commit PortfolioRun creation, no `$NaN`, no self-link
  candidates, and analyst PII denial.
- Verification passed: `uv run ruff check .`,
  `uv run ruff format --check .`,
  `DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 uv run pytest`,
  `npm run build`, Docker Compose `npm run e2e:synthetic`, and local
  secure-root `npm run e2e:real -- --reporter=list --workers=1`.

## 2026-04-30 — Portfolio V2 Contract, Audit, Advisor Console Implemented

- Cut portfolio output over to `engine_output.link_first.v2` only.
- Removed legacy `Household.last_engine_output` and mutable
  `PortfolioRun.status/stale_reason`; lifecycle is now append-only
  `PortfolioRunEvent`.
- Added durable goal-account link ids, account cash state, CMA aliases,
  geography metadata, whole-fund metadata, current-vs-ideal diagnostics,
  mapping diagnostics, run manifests, and sanitized portfolio audit export.
- Implemented same-input run reuse with input/output/CMA/run-signature
  verification. Hash mismatch records an event and generates a fresh run.
- Added advisor decline/regeneration lifecycle and CMA/planning invalidation
  events.
- Rebuilt the advisor portfolio surface into Household, Account, and Goal
  console tabs with account-first recommendations, blended/by-account goal
  views, fund-type labels, diagnostics, and an audit drawer.
- Added `scripts/reset-v2-dev.sh --yes` for full local DB reset/reseed.
- Verification passed:
  `uv run ruff check .`,
  `uv run ruff format --check .`,
  `DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 uv run python -m pytest engine/tests/test_engine.py -q`,
  `DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 uv run python -m pytest web/api/tests/test_api.py -q`,
  `DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 uv run python web/manage.py makemigrations --check --dry-run`,
  `scripts/test-python-postgres.sh`,
  `npm run build`, and
  `npm run e2e:synthetic`.

## 2026-04-30 — Extraction Package + Advisor Review Hardening Implemented

- Moved live extraction responsibilities out of `web/api/review_processing.py`
  into the canonical `extraction/` package: adaptive classification,
  deterministic parsers, Bedrock prompt routing/JSON repair, typed fact
  candidates, normalization, and field-specific reconciliation helpers.
- Rewired the review worker so Django owns orchestration, persistence, retry,
  audit, and queue state while `extraction/` owns parsing/classification/fact
  generation behavior.
- Added classifier/parser/extraction metadata to document processing state,
  ignored system files such as `.DS_Store` before job creation, and made fact
  replacement atomic after successful extraction so failed retries preserve
  prior good facts.
- Added advisor-readable fact labels/sections, field-source metadata, an audited
  redacted evidence endpoint, and goal-risk explainability metadata in
  PortfolioRun recommendation explanations.
- Cleaned agent memory to retire stale boundary-pseudonymization instructions
  and added `docs/agent/extraction-coverage.md` as the PII-free coverage matrix.
- Verification passed:
  `uv run ruff check .`,
  `uv run ruff format --check .`,
  `DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 uv run pytest`,
  `DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 uv run python web/manage.py makemigrations --check --dry-run`,
  `npm run build`, and
  `PLAYWRIGHT_BASE_URL=http://localhost:5173 npm run e2e:synthetic`.

## 2026-04-30 — UI/UX Rewrite Phase R0 (engine layer) Started

- Plan approved at `~/.claude/plans/i-want-you-to-rosy-mccarthy.md` after 9
  rounds of focused interviewing (39 locked decisions). Branch
  `feature/ux-rebuild` cut from `main`.
- Five new pure engine modules added (canon §9.4.2 boundary preserved —
  `engine/tests/test_engine_purity.py` AST-scans every engine .py and
  enforces no imports of web/extraction/integrations/django/rest_framework):
  - `engine/risk_profile.py` — household profile composition (T/C/anchor)
    with configurable Q1-Q4 score constants. Maps to canon-aligned 5-band
    descriptors (locked decision #5: Cautious / Conservative-balanced /
    Balanced / Balanced-growth / Growth-oriented). Hayes worked-example
    parity test: Q1=5, Q2=B, Q3=1, Q4=B → T=45, C=50, profile=Balanced,
    anchor=22.5.
  - `engine/goal_scoring.py` — Goal_50 derivation (anchor + impShift +
    sizeShift), horizon cap, override-aware effective resolution.
    **Goal_50 is internal only per locked decision #6**; API surface
    returns canon 1-5 + descriptor + flags. Configurable IMP_SHIFT,
    SIZE_SHIFT_TABLE, NECESSITY_TO_TIER constants per locked decision #10.
    GoalRiskOverride model operates at canon 1-5 + descriptor with
    required min-10-char rationale. Hayes Retirement worked-example
    parity (Goal_50=6 → canon Cautious) + Choi Travel (Goal_50=28 →
    Balanced).
  - `engine/projections.py` — equity/mu/sigma curves, lognormal quantiles +
    means + probability-above-target, tier-aware percentile bands (Need
    P10/P90, Want P5/P95, Wish P2.5/P97.5). External holdings drift
    penalty (mu × 0.85, sigma × 1.15). Acklam inverse-normal for
    quantiles; math.erf for CDF.
  - `engine/moves.py` — rebalance moves with $100 rounding + residual
    absorbed into largest deficit-side move so total_buy == total_sell
    exactly. Skip threshold $50. Choi Education worked-example parity.
  - `engine/collapse.py` — FoF match scorer per canon §4.3b. Computes
    asset-class composition of a building-block blend; matches against
    whole-portfolio funds via 1 - L1/2; threshold default 0.92.
- `engine/sleeves.py` updated to v36 8-fund universe (locked decision #3 —
  hybrid): added Founders + Builders Sleeve entries; added
  SLEEVE_REF_POINTS calibration table at scores 5/15/25/35/45/50 (sums to
  100 each); added SLEEVE_COLOR_HEX (paper/ink/gold/copper/etc per
  mockup) and FUND_NAMES.
- `engine/__init__.py` re-exports new modules.
- External-holdings risk-tolerance dampener (canon §4.6a) deferral
  documented in 4 places per locked decision #11: docstring TODO at top
  of `engine/risk_profile.py`; row #9 in `docs/agent/open-questions.md`
  "Code Drift vs Canon"; entry in `docs/agent/decisions.md` Deferred
  section; item #9 in memory `project_codebase_drift_signals.md`.
  Projection-time penalty IS implemented (mu × 0.85 / sigma × 1.15 for
  external); the risk-score dampener stays a Phase B work item awaiting
  team-confirmed formula.
- Engine purity CI grep-check (canon drift item #8) RESOLVED — added
  `engine/tests/test_engine_purity.py` enforcing the boundary at every
  engine .py file via AST import scan. Replaces the prior
  enforced-by-convention posture.
- Engine R0 verification passed:
  - `uv run ruff check .` — All checks passed
  - `uv run ruff format --check .` — 100 files already formatted
  - `DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 uv run python -m pytest engine/tests/ -q`
    — **216 passed** (parity tests for Hayes risk profile + Hayes
    Retirement + Choi Travel + Choi Education + Thompson Retirement; 8-fund
    universe sums; engine purity boundary).
- **R0 still pending**: frontend foundation (design tokens, self-hosted
  fonts, shadcn CLI scaffold, TS strict, ESLint, Prettier, i18n, a11y),
  backend plumbing (drf-spectacular, django-csp, mypy strict, security
  headers), `scripts/check-vocab.sh`, CI workflow updates, full
  per-phase gate suite green, R0 final commit + memory cadence.
- DB reset (`scripts/reset-v2-dev.sh --yes`) deferred until migrations +
  new fixture exist; will run before backend plumbing requires it.
- Branch state: `feature/ux-rebuild`, all engine work uncommitted.
  Working tree clean from a Python tests perspective; ready for either
  (a) commit-as-checkpoint and continue, or (b) keep going to final R0
  commit.

## 2026-04-30 — R0 engine layer committed (6f60694)

Engine R0 chunk landed as `6f60694` on `feature/ux-rebuild`:
"Phase R0: engine foundation for v36 UI/UX rewrite". 17 files, +2878 / -7.

## 2026-04-30 — R0 backend plumbing + frontend foundation Implemented

Round 2 of R0 lands the backend plumbing + frontend foundation:

**Backend plumbing**
- `pyproject.toml`: added drf-spectacular, django-csp 4.x, mypy, OpenTelemetry
  (api + sdk + django + psycopg2 + otlp-http exporter). `uv sync --all-groups`
  installed cleanly.
- `web/mp20_web/settings.py`: drf-spectacular config (`SPECTACULAR_SETTINGS`
  with TAGS for auth/clients/portfolio/preview/cma/review/snapshots);
  django-csp 4.x dict-based `CONTENT_SECURITY_POLICY` (strict-dynamic
  scripts via nonce, self-only fonts/images/connect, frame-ancestors 'none',
  Vite HMR allowed in dev); SECURE_* headers (X-Frame-Options DENY,
  Referrer-Policy strict-origin-when-cross-origin, content-type-nosniff,
  XSS filter); MP20_OTEL_ENABLED env flag.
- `web/mp20_web/otel.py`: env-toggled OpenTelemetry initializer (Django +
  psycopg2 instrumentation, OTLP/HTTP exporter to Elastic APM in
  production per canon §9.1). No-op in dev.
- `web/mp20_web/{wsgi,asgi}.py`: invoke `configure_opentelemetry()` before
  Django's app loader so auto-instrumentation hooks at import time.
- `web/mp20_web/urls.py`: added `/api/schema/`, `/api/docs/` (Swagger UI),
  `/api/redoc/` (ReDoc).
- `engine/schemas.py` + `engine/optimizer.py`: bare `dict` annotations
  converted to `dict[str, Any]`; `MappingStatus` import added; `status:
  MappingStatus` annotation typed. Required for mypy strict to type-check
  the new R0 modules end-to-end through their imports.
- mypy strict config: per-module overrides — strict for the 6 new R0
  modules (risk_profile, goal_scoring, projections, moves, collapse,
  sleeves); typed-but-not-strict for legacy schemas/optimizer/frontier/
  compliance; ignored for tests.

**Frontend foundation (full rewrite per locked decision #1)**
- `package.json` v0.2.0 with new deps: react-router-dom 6, react-hook-form
  + zod + @hookform/resolvers (locked decision #29), d3-hierarchy,
  react-i18next + i18next, sonner, class-variance-authority + clsx +
  tailwind-merge, all required @radix-ui/* primitives, @opentelemetry/*
  web SDK + instrumentation (locked decision #31b), openapi-typescript
  (locked decision #26b), eslint 9 + typescript-eslint 8 +
  eslint-plugin-jsx-a11y + eslint-plugin-i18next + eslint-config-prettier,
  prettier 3, globals. `npm install` succeeded (359 packages).
- `frontend/tailwind.config.ts`: v36 design tokens (locked decision #5):
  paper/ink/accent (gold/copper)/hairlines/muted; `buckets.*` for canon-aligned
  risk descriptors; `funds.*` matching `engine/sleeves.py SLEEVE_COLOR_HEX`;
  Fraunces/Inter Tight/JetBrains Mono font stacks; mockup-aligned shadows;
  `letterSpacing.{wider,widest,ultrawide}` for JetBrains Mono uppercase
  labels; `borderRadius.none = 0` (mockup uses square corners).
- `frontend/src/index.css`: `@font-face` declarations for Fraunces variable
  + Inter Tight 300/400/500/600/700 + JetBrains Mono 400/500/600. Browser
  falls back gracefully to system fonts when `.woff2` files are missing.
  `frontend/public/fonts/README.md` documents the manual download step
  (Google Fonts CDN download was blocked at execution time per safety
  controls; gracefully degrades to system fonts).
- `frontend/src/i18n/{index.ts, en.json, fr.json}`: react-i18next with
  English + French placeholder per locked decision #12. All user-visible
  strings flow through `t()`; fr.json is a placeholder until translations
  land later.
- `frontend/src/App.tsx`: stripped to a holding shell with topbar
  placeholder + scaffolding-ready empty stage. Includes the v36 brand
  mark + canon-aligned scaffolding copy through `t()`. TODO comment
  for the deferred pilot disclaimer (locked decision #17).
- `frontend/src/components/ErrorBoundary.tsx`: top-level + per-route
  React ErrorBoundary (locked decision #31a). Paper/ink fallback UI with
  Retry + "Report this" CTAs. i18n via the singleton `i18n.t()` since
  class components can't use the hook.
- `frontend/src/main.tsx`: ErrorBoundary wraps everything; TanStack Query
  configured with locked decision #18 cache settings (staleTime 5min /
  gcTime 30min); I18nextProvider + QueryClientProvider in place.
- `frontend/src/lib/cn.ts`: shadcn `cn()` helper (clsx + tailwind-merge).
- `frontend/tsconfig.app.json`: strict + noUncheckedIndexedAccess +
  noImplicitOverride + noFallthroughCasesInSwitch + verbatimModuleSyntax
  per locked decision #22a.
- `frontend/eslint.config.js`: ESLint 9 flat config (locked decision #22e
  + #28a) with typescript-eslint strict + react-hooks + jsx-a11y
  recommended + i18next/no-literal-string (markupOnly mode) + zero `any` +
  prettier-compat. Test files relax i18n rule.
- `frontend/.prettierrc.json` + `.prettierignore`: 100-char width, double
  quotes, trailing commas, tabWidth 2.
- Old surfaces deleted: `ReviewShell.tsx`, `CmaWorkbench.tsx`, `api.ts`,
  `types.ts`, `components/ui/button.tsx`, `styles.css`. Per locked
  decision #20 (no feature flag); rebuilt incrementally R2-R9.
- shadcn/ui CLI scaffold deferred to R2 when components are needed; the
  R0 chrome (App.tsx + ErrorBoundary) doesn't need a full kit yet.

**Vocabulary CI guard (locked decision #14)**
- `scripts/check-vocab.sh`: scans `frontend/src/`, `frontend/index.html`,
  `web/api/serializers.py`, `web/api/management/commands/`,
  `web/api/migrations/`, `engine/fixtures/` for re-goaling tripwires
  (`reallocation`, `reallocate`, `move money` per canon §6.3a), retired
  bare `Conservative` label (canon vocab uses `Cautious` for low-end and
  `Conservative-balanced` for low-medium per §4.2 + locked decision #5),
  and retired user-visible `Sleeve ` capitalization (the `Sleeve`
  Pydantic class identifier is allowed). Allow-listed contexts include
  this script, eslint config, docs, and inline `canon-vocab-allow:`
  comments. Currently green.

**CI workflow (`.github/workflows/smoke.yml`)**
- Python job: ruff check + ruff format + **mypy strict on R0 engine
  modules** (locked decision #22b) + pytest + makemigrations check +
  **drf-spectacular --validate** (locked decision #24b) + **vocab CI
  guard**.
- Frontend job: **typecheck (TS strict + noUncheckedIndexedAccess + zero
  `any`)** + **ESLint (jsx-a11y + i18next + react-hooks)** +
  **Prettier --check** + build.
- Browser-e2e job unchanged (still synthetic Playwright over Docker
  Compose). R7 will rewrite the synthetic spec to match the new shell.

**R0 verification — all gates green**
- `uv run ruff check .` — All checks passed
- `uv run ruff format --check .` — 101 files already formatted
- `uv run mypy engine/risk_profile.py engine/goal_scoring.py
  engine/projections.py engine/moves.py engine/collapse.py
  engine/sleeves.py` — Success: no issues found in 6 source files
- `DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 uv run python
  -m pytest engine/tests/ -q` — 216 passed in 2.39s
- `DATABASE_URL=... uv run python web/manage.py check` — System check
  identified no issues (0 silenced)
- `DATABASE_URL=... uv run python web/manage.py spectacular --validate
  --file /tmp/schema.yaml` — schema generates (legacy-view fallback
  warnings; R1 will add @extend_schema decorators)
- `bash scripts/check-vocab.sh` — vocab CI: OK
- `npm run typecheck` (TS strict) — clean
- `npm run lint` (ESLint flat config) — clean
- `npm run format` — All matched files use Prettier code style
- `npm run build` — successful (250KB JS / 79KB gzipped; expected font
  404s for un-downloaded woff2 files)

**R0 still pending (next phase)**
- DB reset (`scripts/reset-v2-dev.sh --yes`) — deferred to R1 when new
  schema migrations + new richer Sandra/Mike fixture (locked decision #19)
  exist.
- Synthetic Playwright spec rewrite — covered by R7 when the doc-drop +
  review-screen surfaces ship.
- Self-hosted font `.woff2` files — manual download per
  `frontend/public/fonts/README.md`; system fonts fall back gracefully
  until then.
- Phase B work (MFA, lockout, password reset, audit browser UI, real
  PII testing harness, full real-bundle E2E, mockup-parity audit) per
  locked decisions and parking lot.

## 2026-04-30 — R1 backend extensions Implemented

R1 lands the backend surface the v36 advisor console will call. 18 new
endpoints (10 read-only preview + 8 state-changing), 4 new models with
append-only contracts, audit-event regression suite enforcing locked
decision #37.

**New models (`web/api/models.py` + `0008_v36_ui_models.py`)**
- `RiskProfile` (one-to-one with Household): Q1-Q4 inputs + persisted
  derived T/C/anchor/descriptor/score_1_5. Per locked decision #6, the
  derived columns mirror what `engine.risk_profile.compute_risk_profile`
  returns; engine remains source of truth.
- `GoalRiskOverride` (append-only via save() override per locked
  decision #6): score_1_5 + descriptor + rationale (CHECK constraint
  enforces min 10 chars at DB level). Latest-row-wins per goal.
- `ExternalHolding` (canon §4.6a): structured rows replacing the legacy
  `Household.external_assets` JSONField. clean() validates pct sum=100.
- `HouseholdSnapshot` (append-only via save() override): trigger
  taxonomy from locked decision #36 — realignment / cash_in / cash_out
  / re_link / override / re_goal / restore. snapshot + summary JSONFields
  feed the History tab + Compare view.

**Engine adapter extensions (`web/api/engine_adapter.py`)**
- `to_engine_risk_profile(profile)` — rebuilds the engine `RiskProfileResult`
  from persisted Q1-Q4 (engine remains source of truth).
- `active_goal_override(goal)` — latest GoalRiskOverride as engine struct.
- `current_holdings_to_pct(account)` — `{fund_id: pct}` map.
- `household_aum(household)` — sum of committed accounts + external holdings.

**Preview DRF views (`web/api/preview_views.py`, all auth-required)**
- `POST /api/preview/risk-profile/` — Q1-Q4 → canon 1-5 + descriptor +
  anchor + flags. Per locked decision #6, no Goal_50 in response.
- `POST /api/preview/goal-score/` — anchor + tier + size + horizon
  (+ optional override) → canon 1-5 + descriptor + horizon-cap-binding +
  derivation. Per locked decision #6, no Goal_50 in response.
- `POST /api/preview/sleeve-mix/` — canon 1-5 → SLEEVE_REF_POINTS mix
  for the bucket midpoint. Calibration-only (frontier optimization is
  what production runs).
- `POST /api/preview/projection/` — lognormal bands at horizon
  (P2.5/P5/P10/P25/P50/P75/P90/P95/P97.5 + mean + mu + sigma + tier
  band lo/hi). Tier-aware per locked decision #21.
- `POST /api/preview/projection-paths/` — sequence of points along
  constant-percentile curves for fan-chart paths.
- `POST /api/preview/probability/` — P(S_T ≥ target). Drives fan-chart
  hover crosshair callout per v36 mockup §35.
- `POST /api/preview/optimizer-output/` — improvement_pct = (ideal_low
  − current_low) / current_low × 100 at P_score downside (mockup v34).
- `POST /api/preview/moves/` — rebalance moves with $100 rounding +
  residual absorbed into largest deficit-side move (canon §8.10).
- `POST /api/preview/blended-account-risk/` — before/after blended
  account risk with >5pt banner trigger (canon §6.3a).
- `POST /api/preview/collapse-suggestion/` — FoF collapse-match scorer
  per canon §4.3b. Surfaces best-effort match score even below threshold.
- `GET /api/treemap/?household_id=...&mode=by_account|by_goal|by_fund|by_asset`
  — hierarchical data for the v36 main canvas. Frontend (d3-hierarchy)
  computes the squarified layout per locked decision #15.

**State-changing DRF views (`web/api/wizard_views.py`, with row locks +
audit per locked decisions #30 + #37)**
- `POST /api/households/wizard/` — full wizard commit creates Household
  + Persons + Accounts + Goals + GoalAccountLinks + RiskProfile +
  ExternalHoldings atomically inside `transaction.atomic()`. Audit event
  `household_wizard_committed`.
- `POST /api/households/<id>/realignment/` — re-goaling label-only per
  canon §6.3a. Creates before+after HouseholdSnapshots; computes
  blended-account-risk delta; flags >5pt shifts. Audit events
  `realignment_applied` + 2× `household_snapshot_created`.
- `GET /api/households/<id>/snapshots/` — list (history tab).
- `GET /api/households/<id>/snapshots/<sid>/` — detail.
- `POST /api/households/<id>/snapshots/<sid>/restore/` — replays
  allocation amounts; creates new snapshot tagged `restore` per locked
  decision #36 (chain stays linear). Audit events
  `household_snapshot_restored` + 1× `household_snapshot_created`.
- `POST /api/goals/<id>/override/` + `GET /api/goals/<id>/overrides/`
  — append-only override creation + read-only history. Audit event
  `goal_risk_override_created` captures before/after canon score +
  descriptor + rationale per canon §9.4.6.
- `GET/POST /api/households/<id>/external-holdings/` +
  `PATCH/DELETE /api/households/<id>/external-holdings/<hid>/` —
  CRUD with sum-validates-to-100. Each mutation fires
  `external_holdings_updated` audit event.

**Concurrency safety (locked decision #30)**
- `_resolve_household_for_write` performs a non-locking team-scope
  check first, then `Household.objects.select_for_update().get(...)`
  to actually lock the row. (Necessary because `team_households`
  returns a LEFT OUTER JOIN — Postgres rejects SELECT FOR UPDATE on
  the nullable side.)

**OpenAPI (`@extend_schema` decorators)**
- Every R1 view tagged into the right group (auth/clients/portfolio/
  preview/cma/review/snapshots) per `SPECTACULAR_SETTINGS`.

**Tests**
- `web/api/tests/test_r1_preview_endpoints.py` (16 tests) — happy path
  + auth + scoping + state changes + Goal_50-not-in-response assertion
  per locked decision #6.
- `web/api/tests/test_r1_audit_emission.py` (14 tests) — centralized
  regression suite (locked decision #37) with `_assert_audit_event(action,
  count, scope)` helper. Asserts every state-changing endpoint fires
  exactly the expected count of `AuditEvent` rows with the expected
  `action`. Also asserts read-only preview endpoints emit ZERO events.

**R1 verification — all gates green**
- `uv run ruff check .` — All checks passed
- `uv run ruff format --check .` — 106 files already formatted
- `uv run mypy <R0 modules>` — Success: no issues found in 6 source files
- `DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 uv run pytest`
  — **313 passed in 31.33s** (216 engine + 97 web, including 30 new
  R1 tests)
- `python web/manage.py makemigrations --check --dry-run` — No changes
- `python web/manage.py spectacular --validate` — schema generates (R1
  views carry @extend_schema; legacy views carry pre-existing fallback
  warnings)
- `bash scripts/check-vocab.sh` — vocab CI: OK

**R1 still pending (next phase)**
- Frontend wiring of the new endpoints (R2+). The endpoints are tested
  in isolation; the React UI consumes them across R2-R10.
- DB reset + new richer Sandra/Mike fixture (locked decision #19) —
  deferred to R7 when real-PII testing checkpoint requires it; R1
  tests use ad-hoc fixtures within pytest-django transactions.
- Phase B work (MFA, lockout, password reset, audit browser UI) per
  locked decisions and parking lot.
