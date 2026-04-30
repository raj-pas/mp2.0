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

## 2026-04-30 — Phase R2 frontend chrome COMPLETE

**Branch:** `feature/ux-rebuild` (commit pending)
**Phase:** R2 — Frontend chrome (TopBar + ContextPanel + BrowserRouter + auth)
**Status:** ✅ All R2 gates green; ready for R3

### Scope landed

- `frontend/src/chrome/` — TopBar, BrandMark, ClientPicker (Radix
  Popover + searchable list), ModeToggle (group-by-account|goal),
  UserChip (with logout mutation), EmptyStage placeholder.
- `frontend/src/ctx-panel/ContextPanel.tsx` — Radix Tabs panel with
  per-kind tab definitions (household: overview/allocation/projections/
  history; account: overview/allocation/goals; goal: overview/
  allocation/projections), collapse-to-rail mode persisted in
  localStorage, breadcrumb header with Lucide ChevronRight separators.
- `frontend/src/routes/` — six empty route placeholders
  (HouseholdRoute, AccountRoute, GoalRoute, ReviewRoute, CmaRoute,
  MethodologyRoute) + LoginRoute (react-hook-form-free for now —
  simple controlled inputs since wizard's full RHF stack lands R5).
- `frontend/src/components/ui/` — shadcn-pattern primitives (Button
  via cva variants, Skeleton, Toaster wrapping Sonner). Tailwind
  + Radix + cva stack matches locked decision #12 / #21 / #22.
- `frontend/src/lib/` — api.ts (CSRF-aware fetch wrapper),
  auth.ts (useSession/useLogin/useLogout TanStack Query hooks),
  clients.ts (useClients), debounce.ts (useDebouncedValue),
  format.ts (CAD currency + compact + percent), local-storage.ts
  (typed prefs hook — no PII), toast.ts (Sonner wrapper),
  api-error.ts (normalize ApiError → {status,message,code}).
- `frontend/src/App.tsx` — full rewrite. BrowserRouter +
  SessionGate + AuthenticatedShell + RouteHost. Role-based routing:
  advisors land at `/` (HouseholdRoute), financial_analysts auto-
  redirected to `/cma`. Per-route ErrorBoundary scoping per locked
  decision #31a.
- `frontend/src/main.tsx` — added `<Toaster />` next to `<App />`
  inside QueryClientProvider for app-wide Sonner toasts.
- `frontend/src/i18n/en.json` — added `topbar.*`, `ctx.*`, `routes.*`,
  `auth.role_unsupported`, `scaffold.phase_label_r2` keys. fr.json
  remains the placeholder per locked decision #12.
- `frontend/e2e/foundation.spec.ts` — new R2 chrome smoke spec:
  advisor lands on household stage; methodology nav works; analyst
  routes to /cma. Replaces the deleted `synthetic-review.spec.ts`
  and `portfolio-cma.spec.ts` (which targeted the old shell deleted
  in R0; both get rewritten in R7 / R9 per the plan).
- `frontend/package.json` — `e2e:synthetic` script repointed to
  `e2e/foundation.spec.ts`.

### Locked decisions honored in R2

- #2 server roundtrip on every interaction — every chrome interaction
  routes through TanStack Query → /api/* (no client-side state
  duplication).
- #5 canon-aligned client-facing labels — TopBar renders advisor
  role + canon descriptors only; no retired mockup vocabulary.
- #12 a11y baseline + i18n scaffolding + shadcn/ui — every component
  uses semantic HTML, ARIA, focus-visible rings; every user-visible
  string flows through `t()` (eslint-plugin-i18next enforces).
- #14 vocab CI guard — green; chrome strings respect re-goaling
  discipline.
- #17 pilot disclaimer deferred — TopBar.tsx top-of-file TODO comment
  references canon §13.0.1.
- #18 latency budget + caching — TanStack Query staleTime 5min /
  gcTime 30min already from R0; debounce hook ready for R3 sliders.
- #20 no feature flag — old App.tsx is fully replaced; no
  coexistence shell.
- #21 maximalist UX state patterns — Skeleton primitive + Sonner
  toasts + ConfirmDialog (deferred to R6 — no destructive actions
  in R2 chrome) + i18n empty-state strings. ClientPicker has
  skeleton-on-pending.
- #22 type/lint/security discipline — TS strict + zero `any` (eslint
  enforces); Python mypy strict on R0 modules; CSP headers active;
  self-hosted fonts (download still manual per font README).
- #28a i18n CI guard — eslint-plugin-i18next/no-literal-string
  enforces; Lucide icons replace decorative unicode glyphs (⌂ ⚡ ∑ ▼
  ‹ › / ) so they don't trigger the rule.
- #31a per-route ErrorBoundary — RouteFrame wraps every route with
  `<ErrorBoundary scope="…">`; broken Goal view leaves Household
  + Account routes working.
- #32a/b URL state + localStorage — selections via react-router
  params; group-by + last-client-id + ctx-collapsed in localStorage
  via typed `useLocalStorage` hook; no PII stored.

### R2 gate verification

- `uv run ruff check .` — All checks passed
- `uv run ruff format --check .` — 106 files already formatted
- `uv run mypy engine/risk_profile.py engine/goal_scoring.py engine/projections.py engine/moves.py engine/collapse.py engine/sleeves.py`
  — Success: no issues found in 6 source files
- `DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 uv run pytest`
  — 313 passed in 31.35s (R2 adds no new Python tests; full R0+R1
  suite remains green)
- `python web/manage.py makemigrations --check --dry-run` — No changes
- `python web/manage.py spectacular --validate --file /tmp/schema.yaml` — exit 0 (graceful APIView fallbacks per R0/R1 baseline)
- `bash scripts/check-vocab.sh` — vocab CI: OK
- `npm run typecheck` — clean (TS strict + noUncheckedIndexedAccess
  + zero any)
- `npm run lint` — clean (eslint-plugin-i18next + jsx-a11y +
  react-hooks; no-explicit-any error)
- `npm run format` — All matched files use Prettier code style
- `npm run build` — 411.80 kB JS / 14.94 kB CSS, gzip 130.64 kB /
  3.66 kB. Font .woff2 paths warn at build time (manual download
  documented in `frontend/public/fonts/README.md`); browser falls
  back to system fonts gracefully until R10 polish.

### Notes for R3

- `useClients()` returns `ClientSummary[]` from `/api/clients/` —
  R3 should add a `useHousehold(id)` query for the detail surface
  and feed treemap data via `/api/preview/treemap/` (R1-shipped).
- ContextPanel kinds (`household`/`account`/`goal`) and tab keys
  are defined; R3 fills the placeholders with real content panels.
- BrandMark uses react-router-dom `Link` to "/" — works for advisors;
  analyst auto-bounces from "/" to "/cma" via SessionGate's effect.
- `useRememberedClientId()` already wired through TopBar →
  ClientPicker; R3 uses it as the default `householdId` for queries
  on first paint.
- Debounce + format + toast helpers ready for R3 stage panels.

## 2026-04-30 — Phase R3 three-view stage COMPLETE

**Branch:** `feature/ux-rebuild` (commit pending)
**Phase:** R3 — Three-view stage (treemap + KPI surfaces + ring charts + populated ctx panel)
**Status:** ✅ All R3 gates green; ready for R4

### Scope landed

- `frontend/src/lib/household.ts` — full type surface mirroring
  `HouseholdDetailSerializer` + helpers (`useHousehold`, `findGoal`,
  `findAccount`, `householdInternalAum`, `findLinkRecommendation`).
- `frontend/src/lib/treemap.ts` — `useTreemap(householdId, mode)` query
  hook + `colorForNode()` palette mapper for fund/asset/account/goal
  modes, with safe `noUncheckedIndexedAccess`-friendly fallbacks.
- `frontend/src/lib/risk.ts` — canon 1-5 risk helpers
  (`RISK_DESCRIPTOR_KEYS`, `BUCKET_COLORS`, `isCanonRisk`,
  `descriptorFor`). Locked decision #5 vocabulary enforced.
- `frontend/src/lib/clients.ts` — `ClientSummary` shape corrected
  to match the existing `HouseholdListSerializer` payload (`id`,
  `display_name`, `total_assets`, `goal_count`,
  `household_risk_score`, `household_type`).
- `frontend/src/treemap/Treemap.tsx` — squarified d3-hierarchy layout
  rendered via SVG. ResizeObserver-driven; accessible (each cell is a
  button when `onSelect` is wired; aria-labels with $ value); paper-2
  background; Inter Tight + Fraunces text inside cells; truncation
  proportional to cell width. Click + Enter/Space drill into target.
- `frontend/src/charts/RingChart.tsx` — Chart.js doughnut wrapper
  with paper-cream cutout + center-label slot for AUM.
- `frontend/src/charts/AllocationBars.tsx` — pure-CSS horizontal bars
  for top-funds breakdowns (no Chart.js needed; tighter bundle).
- `frontend/src/charts/RiskBandTrack.tsx` — read-only 5-band canon
  marker (locked decision #6). Active band highlighted, inactive
  bands at 40% opacity, optional dashed `baselineScore` ghost
  marker. role="meter" + aria-valuemin/max/now/text. R4 will wrap
  this in the interactive RiskSlider with override rationale.
- `frontend/src/routes/HouseholdRoute.tsx` — AUM split strip (Total /
  internal Steadyhand / external) + canon descriptor stat + goal
  count + treemap stage. Treemap mode driven by topbar group-by
  ("by-account" | "by-goal") via `topbarToTreemapMode()` shim.
  Click-to-drill navigates to `/account/:id` or `/goal/:id`.
- `frontend/src/routes/AccountRoute.tsx` — 4-tile KPI strip (value /
  type / goals-in-account count / cash state) + RingChart of
  fund composition + top-funds AllocationBars + goals-in-account
  list with clickable navigation to goal route. ChevronLeft "back
  to household" affordance.
- `frontend/src/routes/GoalRoute.tsx` — header with goal name + tier
  pill (Need / Want / Wish / Unsure derived from
  `necessity_score`); 4 KPI tiles (target / funded / horizon /
  goal-risk-with-RiskBandTrack); linked-accounts list (account_id +
  $); blended-view placeholder noting R4 scope.
- `frontend/src/ctx-panel/HouseholdContext.tsx` — populates
  household ctx-panel tabs: overview (display_name + type + total
  AUM + risk descriptor + members), allocation (FundMixStack with
  stacked bar + top-8 fund table), projections (R4 deferred
  placeholder), history (R6 deferred placeholder).
- `frontend/src/ctx-panel/AccountContext.tsx` — overview (type +
  current_value + reg objective/horizon if set), allocation (top-8
  funds), goals (goals-in-this-account list).
- `frontend/src/ctx-panel/GoalContext.tsx` — overview (name + target
  + funded + canon descriptor + RiskBandTrack), allocation (linked
  accounts), projections (R4 placeholder).
- `frontend/src/ctx-panel/ContextPanel.tsx` — refactored: layout
  stays (collapse-to-rail + tabs); body delegates to per-kind
  component which owns its own `<Tabs.Content>` panes. Cleaner
  separation of concerns and matches the plan's filename guidance.
- `frontend/src/i18n/en.json` — large additions: `routes.household.*`,
  `routes.account.*`, `routes.goal.*`, `treemap.*`,
  `risk_descriptors.*`, `ctx.section.*`, `ctx.deferred.*`. Goal
  horizon uses i18next plural keys (`horizon_years_one` /
  `horizon_years_other`).
- `frontend/e2e/foundation.spec.ts` — extended with R3 assertions:
  client picker → AUM strip + treemap render → click into account
  → KPI strip → click goal-in-account → goal hero with risk meter.

### Locked decisions honored in R3

- #2 server roundtrip — every read-only surface fetches via
  TanStack Query; no client-side computation duplication. Treemap
  is pre-computed by `/api/treemap/`; frontend only does layout.
- #3 8-fund universe — fund palette in `treemap.ts` + `AccountRoute`
  + `HouseholdContext` matches engine `SLEEVE_COLOR_HEX` (sh-sav,
  sh-inc, sh-eq, sh-glb, sh-sc, sh-gsc, sh-fnd, sh-bld).
- #5 canon-aligned descriptors — every risk display routes through
  `descriptorFor()` → `risk_descriptors.*` i18n key. Mockup labels
  not present.
- #6 Goal_50 hidden — risk surfaces show canon 1-5 + descriptor;
  `RiskBandTrack` is a 5-band picker, never a 0-50 slider.
- #12 a11y — treemap cells are buttons with keyboard nav, all
  charts have role="img" + aria-labels, KPI sections have aria-
  labels, `RiskBandTrack` is a proper meter with valuemin/max/now/
  text. Lucide icons remain aria-hidden when an adjacent text
  carries the label.
- #14 vocab CI — green; UI strings honor re-goaling discipline.
- #18 latency budget — TanStack Query staleTime 5min still in
  effect from R2; no per-call cache layer.
- #21 maximalist UX state — every panel has skeleton-on-pending +
  graceful empty states (no clients selected, no holdings, no
  goals, missing client, missing account, missing goal). Toast
  + ConfirmDialog still pending for state-changing actions
  (R4 onward).
- #28a i18n CI — every user-visible string flows through `t()`;
  decorative chevrons all use Lucide icons.
- #31a per-route ErrorBoundary — already wired by R2 RouteFrame;
  unchanged.
- #32 URL state — `/account/:accountId` + `/goal/:goalId` carry
  selection; chrome group-by + remembered client persist via
  localStorage. No PII stored.

### R3 gate verification

- `uv run ruff check .` — All checks passed
- `uv run ruff format --check .` — 106 files already formatted
- `uv run mypy <R0 modules>` — Success: no issues found in 6 source files
- `DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 uv run pytest`
  — 313 passed in 38.76s (no Python test changes in R3; R0+R1
  suite remains green)
- `python web/manage.py makemigrations --check --dry-run` — No changes
- `bash scripts/check-vocab.sh` — vocab CI: OK
- `npm run typecheck` — clean
- `npm run lint` — clean (after replacing `tabs[0]!` non-null
  assertions with safer `??` fallbacks; Promise.reject path for
  guarded queryFns instead of `id!`)
- `npm run format` — All matched files use Prettier code style
- `npm run build` — 586 kB JS / 17.20 kB CSS, gzip 188 kB / 4.25 kB
  (Chart.js + d3-hierarchy + lucide additions; bundle budget
  deferred to R10 polish per locked decision #25). Font .woff2
  warnings are the documented manual-download step.

### Notes for R4

- `findLinkRecommendation(household, goalId, accountId)` already
  exists in `lib/household.ts` for R4 to surface per-link
  recommendations on GoalRoute.
- `RiskBandTrack` accepts `score` and optional `baselineScore` for
  the plan-baseline ghost marker R4 will need on the override
  flow. R4 will compose this into a permission-gated interactive
  `RiskSlider` with `react-hook-form` rationale capture.
- Treemap modes `by_fund` and `by_asset` are wired in the lib/
  endpoint but not yet surfaced in the topbar group-by toggle
  (locked decision #15 says HH+Goal views get group-by; R4 can
  decide whether to expand to 4 modes or keep at 2).
- HouseholdContext.allocation currently uses a stacked bar +
  top-8 list. R4 may want to swap this for the same RingChart
  pattern used on AccountRoute for visual consistency.
- The `tab` prop on `HouseholdContext` is a defensive hook that's
  not currently used by Radix Tabs (the Root manages active tab
  state). It's there for future programmatic tab switching.
- AccountRoute portfolio statistics currently shows fund
  composition only (no asset-class / geographic rings). R4 should
  extend this when CMA fund metadata is available client-side
  (or add a backend helper that returns per-account asset
  breakdown using `_treemap_by_asset` logic).

## 2026-04-30 — R0–R3 live smoke + foundation fixes

**Branch:** `feature/ux-rebuild` (commit pending)
**Status:** ✅ Stack runnable end-to-end; 5/5 e2e + 313 pytest + all gates green

### Smoke session

Brought up the stack (Postgres in Docker; Django + Vite on host because the
existing backend container image was baked before R0 added `django-csp` to
deps and Docker pypi was timing out — host venv has it). Walked through
login → household → account → goal → methodology routes. Caught and
fixed four real foundation bugs that all R-phase unit/type/lint gates
missed because they only fire on integration:

### Fixes

1. **Vite missing `/api` + `/static` proxy** (frontend/vite.config.ts)
   - `apiFetch` uses relative URLs + `credentials: "same-origin"`. Without
     a proxy, fetches from the Vite dev server (port 5173) never reach
     Django (port 8000); same-origin cookies wouldn't flow even if they
     did. Added proxy with `VITE_BACKEND_TARGET` env override; compose
     frontend service env updated to `http://backend:8000` (was the
     legacy `VITE_API_BASE_URL` that the new `apiFetch` doesn't read).

2. **`HouseholdDetail.external_assets` typed as `number`, actually an array**
   (frontend/src/lib/household.ts, routes/HouseholdRoute.tsx,
   ctx-panel/HouseholdContext.tsx)
   - Backend `Household.external_assets` is a JSONField list of
     `{type?, value, description?}` rows seeded by
     `load_synthetic_personas`. Coercing the array via `Number()`
     yields `NaN`, breaking the household total AUM. Added
     `ExternalAssetRow` type + `householdExternalAum()` helper that
     reduces values defensively. (R1's `ExternalHolding` model is
     the canonical going-forward shape but the legacy JSONField is
     still surfaced by `HouseholdDetailSerializer`; R7 doc-drop will
     migrate.)

3. **`useLocalStorage` had per-consumer `useState` copies**
   (frontend/src/lib/local-storage.ts)
   - The most subtle bug. `useLocalStorage("mp20_last_client_id")`
     was called from BOTH `TopBar` (writer via `useRememberedClientId`)
     and the routes (`HouseholdRoute`, `AccountRoute`, `GoalRoute`,
     `HouseholdContext`, `AccountContext`, `GoalContext` — readers).
     Each call site held its own `useState`, so when the topbar wrote,
     localStorage updated but the routes' state stayed stale. The UI
     showed the topbar with "Sandra & Mike Chen / $1.31M" while the
     household stage said "Select a client from the topbar..." — a
     tell-tale split-brain symptom.
   - Rewrote with `useSyncExternalStore` against a per-key listener set
     + `cache` Map for snapshot stability + window `storage` event
     listener for cross-tab sync. Every consumer of the same key now
     stays coherent. `mp20_group_by` and `mp20_ctx_panel_collapsed`
     also benefit.

4. **Chart.js `RingChart`: canvas reuse + missing `DoughnutController`**
   (frontend/src/charts/RingChart.tsx)
   - React StrictMode double-mounts effects in dev. Chart.js's per-canvas
     internal registry survived the cleanup-then-mount sequence, throwing
     `"Canvas is already in use"`. Fixed with
     `ChartJS.getChart(canvas)?.destroy()` before construction.
   - Chart.js v4 requires per-controller registration; we registered
     `ArcElement` but not `DoughnutController`. Added it. (Chart.js error
     was `"\"doughnut\" is not a registered controller"`.)

### Test selector touch-ups (not bugs, just brittle assertions)

- `e2e/foundation.spec.ts`: methodology button matched on
  `/Methodology/i` (the long tooltip text contains "Methodology" too,
  but the original `/Methodology overlay/i` regex was wrong).
- `getByRole("meter")` returns 2 results on goal page (KPI tile +
  ctx-panel), so `.first()` to satisfy strict-mode locator.

### Verification (post-fix)

- 5/5 Playwright e2e passing in 7.1s on the live stack (Sandra/Mike Chen)
- 313/313 pytest
- `npm run typecheck / lint / format / build` all clean
- ruff + ruff-format + mypy + vocab CI all green
- Live curl confirms Vite proxy serves `/api/*` through to Django

### Docker note

The stale backend container image (`mp20-backend-1`) was built before R0
added `django-csp` to `pyproject.toml` and so its baked venv at
`/opt/mp20-venv` is missing the module. A clean `docker compose build
backend` would fix it; right now Docker pypi is timing out (network /
firewall flake on this machine). Host-mode dev works perfectly via the
new Vite proxy. Before CI / pilot a clean image rebuild is needed; this
is now in `docs/agent/open-questions.md` as a follow-up.

## 2026-04-30 — Deeper smoke: R1 endpoint live integration + audit flow + Docker rebuild

**Branch:** `feature/ux-rebuild` (commit pending)
**Status:** ✅ All R1 endpoints validated live; audit flow validated; Docker image clean

Following the first smoke session that fixed 4 foundation bugs, ran a
deeper round to de-risk R4 specifically. Found a real foundation issue
(fund-id naming chaos) that would have silently cascaded; fixed it.

### R1 endpoint live integration matrix

Every R1 preview + state-changing endpoint curl-probed against the
Sandra/Mike Chen synthetic. Canonical contracts captured below for
R4 wire-shape reference:

| Endpoint | Request shape (verified) | Response shape (verified) |
|---|---|---|
| `POST /api/preview/risk-profile/` | `{q1, q2, q3[], q4}` | `{tolerance_score, capacity_score, tolerance_descriptor, capacity_descriptor, household_descriptor, score_1_5, anchor, flags[]}` |
| `POST /api/preview/goal-score/` | `{anchor, necessity_score?, goal_amount, household_aum, horizon_years, override?}` | `{score_1_5, descriptor, system_descriptor, horizon_cap_descriptor, uncapped_descriptor, is_horizon_cap_binding, is_overridden, derivation: {anchor, imp_shift, size_shift}}` (Goal_50 NEVER returned per locked decision #6) |
| `POST /api/preview/sleeve-mix/` | `{score_1_5}` | `{score_1_5, reference_score, mix: {fund_id: pct}, fund_names: {fund_id: name}}` |
| `POST /api/preview/projection/` | `{start, score_1_5, horizon_years, mode?, is_external?, tier?}` | `{p2_5, p5, p10, p25, p50, p75, p90, p95, p97_5, mean, mu, sigma, tier_low_pct, tier_high_pct}` |
| `POST /api/preview/projection-paths/` | `{start, score_1_5, horizon_years, percentiles[], n_steps?, mode?, is_external?}` | `{paths: [{percentile, points: [{year, value, percentile}]}]}` |
| `POST /api/preview/probability/` | `{start, score_1_5, horizon_years, target, mode?, is_external?}` | `{probability}` |
| `POST /api/preview/optimizer-output/` | `{household_id, goal_id}` | `{ideal_low, current_low, improvement_pct, effective_score_1_5, effective_descriptor, p_used, tier}` |
| `POST /api/preview/moves/` | `{household_id, goal_id}` | `{moves: [{action: "buy"\|"sell", fund_id, fund_name, amount}], total_buy?, total_sell?}` |
| `POST /api/preview/blended-account-risk/` | `{household_id, account_id, candidate_goal_amounts: {goal_id: amount}}` | `{before_score, after_score, delta, would_trigger_banner, banner_threshold}` |
| `POST /api/preview/collapse-suggestion/` | `{blend: {fund_id: weight}, threshold?}` | `{suggested_fund_id\|null, best_score, best_candidate_id, threshold}` |
| `POST /api/goals/{id}/override/` | `{score_1_5, descriptor, rationale}` (rationale min 10 chars) | `{override_id, goal_id, score_1_5, descriptor, created_at}` |

### Real-bug found: fund-id naming chaos

Curl-probing surfaced FOUR coexisting fund-id naming conventions:

| Source | Format | Examples |
|---|---|---|
| `engine/sleeves.py` v36 universe canon | `SH-Sav` mixed-case | `SH-Sav`, `SH-Inc`, `SH-Eq`, `SH-Glb`, `SH-SC`, `SH-GSC`, `SH-Fnd`, `SH-Bld` |
| Default CMA seed `fund_assumptions` | `sh_savings` snake | `sh_savings`, `sh_income`, `sh_equity`, `sh_global_equity`, `sh_small_cap_equity`, `sh_global_small_cap_eq`, `sh_founders`, `sh_builders` |
| Synthetic persona `Holding.sleeve_id` | legacy product names | `cash_savings`, `income_fund`, `equity_fund`, `global_equity_fund` |
| (deprecated) my treemap.ts palette | dashed lowercase | `sh-sav`, `sh-inc`, etc. |

R4 will render sleeve-mix output (`SH-Sav` style) alongside current
holdings (`income_fund` style); without normalization every fund
renders the gray fallback. Fixed with new `frontend/src/lib/funds.ts`
exporting:

- `canonizeFundId(rawId)` — maps any variant → canon `SH-X` form
- `fundColor(rawId, fallbackIndex)` — returns hex via canon color map
- `fundDisplayName(rawId, fallback)` — returns canon Steadyhand name

All four call sites (`treemap.ts`, `AccountRoute.tsx`,
`HouseholdContext.tsx`, `AccountContext.tsx`) now use the helper.
Inline `FUND_COLORS` Records deleted. Drift item #11 added to
open-questions; the underlying fix (fixture regeneration to canon
8-fund universe) is locked decision #19, deferred to R7.

### Audit flow validated live

- `POST /api/goals/goal_retirement_income/override/` with
  `{score_1_5: 2, descriptor: "Conservative-balanced", rationale: ...}`
- AuditEvent count 0 → 1 of action `goal_risk_override_created`
- Audit row: `actor=advisor@example.com`, `entity_type=goal`,
  `entity_id=goal_retirement_income`, `metadata={rationale,
  descriptor, override_id, new_score_1_5, previous_score_1_5}`
- Locked decision #6 honored: surface is canon 1-5 + descriptor only,
  no Goal_50 in payload
- Locked decision #30 honored: Postgres `select_for_update()` path
  (split scope-check + lock) wraps the mutation transaction
- Locked decision #37 honored: exactly one audit event per
  state-changing endpoint

### Docker compose backend rebuild

- Previous image had been built before R0 added `django-csp` to
  `pyproject.toml`; `docker compose up backend` fails with
  `ModuleNotFoundError: No module named 'csp'`. Open question #10
  flagged this.
- Today `docker compose build backend` succeeded cleanly (78s).
  pypi connectivity was healthy. The rebuilt image starts cleanly,
  applies migrations, seeds the persona, bootstraps advisor +
  analyst users, and serves `/api/session/` 200.
- Open question #10 resolved: the documented `docker compose up
  --build` entry point works for fresh-clone setup.

### Security headers verified live

`curl -I http://localhost:8000/api/session/` returns:

- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Cross-Origin-Opener-Policy: same-origin`
- `Content-Security-Policy: default-src 'self'; base-uri 'self';
  script-src 'self' 'strict-dynamic'; object-src 'none'; img-src 'self'
  data: blob:; style-src 'self' 'unsafe-inline'; font-src 'self' data:;
  connect-src 'self' http://localhost:5173 http://127.0.0.1:5173
  ws://localhost:5173; frame-ancestors 'none'; form-action 'self'`

Locked decision #22c (django-csp + DENY + nosniff + strict-origin)
verified live, not just configured.

### Final regression — all gates green on rebuilt stack

- `npm run typecheck / lint / format / build` — clean
- `uv run ruff check / ruff format --check` — clean
- `bash scripts/check-vocab.sh` — vocab CI: OK
- `uv run mypy <R0 modules>` — Success
- `uv run python web/manage.py makemigrations --check --dry-run` — No changes
- `uv run pytest` — **313 passed in 40.62s**
- `npx playwright test e2e/foundation.spec.ts` — **5/5 in 6.5s**

Foundation is solid. Ready for R4.

## 2026-04-30 — Phase R4 goal allocation + RiskSlider override flow COMPLETE

**Branch:** `feature/ux-rebuild` (commit pending)
**Status:** ✅ All R4 gates green; override save round-trips live; 7/7 e2e

### Scope landed

- `frontend/src/lib/preview.ts` — typed hooks for every R1 preview
  endpoint plus the override mutation + history list:
  `useRiskProfilePreview`, `useGoalScorePreview`, `useSleeveMix`,
  `useProjection`, `useProjectionPaths`, `useProbability`,
  `useOptimizerOutput`, `useMoves`, `useOverrideHistory`,
  `useCreateOverride`. Wire shapes match the canonical contracts
  captured in the deeper-smoke handoff entry; the `GoalRiskOverride`
  list shape (`created_by`, no `goal_id`) was corrected from a
  pre-build assumption (`created_by_email`, `goal_id`).
- `frontend/src/components/ui/RiskSlider.tsx` — interactive 5-band
  picker. Locked decision #6 surface (canon 1-5 + descriptor only,
  never Goal_50/0-50). Override draft state shows the warning banner
  + zod-validated rationale textarea (min 10 chars, both client and
  server enforce). `react-hook-form` + `zod` per locked decision #29.
  Permission gate (`canEdit`) shows `RiskSliderLocked` for analysts
  with a `Lock` icon + tooltip. Save → `useCreateOverride` mutation
  → invalidates household + override-history queries.
- `frontend/src/charts/FanChart.tsx` — Chart.js line fan with two
  band fills (P10–P90 outer, P25–P75 inner) + dotted P50 median +
  amber dashed target line. Tier label chip in the corner;
  probability-at-target badge in the lower-left when target +
  pre-computed probability are passed. The hover-debounced
  per-year probability fetch the plan describes is queued for a
  follow-up commit (locked decision #18 latency budget; the static
  badge already conveys the headline number). Registers
  `LineController` + `Filler` + `LinearScale` + `CategoryScale` +
  tooltip plugin (Chart.js v4 requires explicit registration).
- `frontend/src/charts/RiskBandTrack.tsx` — already shipped in R3
  as the read-only meter. R4 reuses it inside the RiskSlider and
  the goal hero KPI tile (with optional `baselineScore` for the
  ghost tick when an override is active).
- `frontend/src/goal/GoalAllocationSection.tsx` — current vs ideal
  vs Δ table. Pulls ideal from `/api/preview/sleeve-mix/`
  (canon score → fund pcts) and aggregates current from goal-leg
  shares of each linked account's holdings. Both sides flow
  through `canonizeFundId()` so the four-way fund-id chaos
  (engine `SH-Sav` vs CMA `sh_savings` vs persona `income_fund`
  vs lowercase) is normalized before comparison.
- `frontend/src/goal/OptimizerOutputWidget.tsx` — improvement %
  + effective-score + ideal/current P-percentile values.
- `frontend/src/goal/MovesPanel.tsx` — buys + sells split into
  two columns; uses `fundColor()` + `fundDisplayName()` so the
  legacy persona fund names map to canon Steadyhand display.
- `frontend/src/goal/GoalProjectionsSection.tsx` — wraps FanChart
  with side panel of P50/P90/P10 from `/api/preview/projection/`.
  Calls `/api/preview/probability/` once with goal target +
  horizon for the badge.
- `frontend/src/routes/GoalRoute.tsx` — full rewrite. Hero KPI
  strip (target / funded / horizon / canon descriptor with
  RiskBandTrack ghost), then RiskSlider, then GoalAllocationSection,
  then 2-column row(OptimizerOutputWidget, MovesPanel), then
  GoalProjectionsSection, then linked-accounts list. Resolves
  effective score = latest override (if any) ?? system score from
  `goal.goal_risk_score`.
- `frontend/src/ctx-panel/GoalContext.tsx` — projections tab now
  hosts the override history list (locked decision #37 audit
  immutability — read-only display of every prior override with
  rationale + actor + timestamp).
- `frontend/src/i18n/en.json` — added `risk_slider.*` (~30 keys),
  `fan_chart.*` (~12), `goal_allocation.*` (8), `optimizer_output.*`
  (6), `moves.*` (8). All user-visible strings flow through `t()`.
- `frontend/e2e/foundation.spec.ts` — extended with two R4 tests:
  (1) goal page renders RiskSlider radiogroup + Allocation table
  + Optimizer output + Moves + Projection fan; (2) advisor selects
  a different band → override banner appears → fills rationale →
  saves → ctx-panel projections tab shows the new history row with
  the rationale text.

### Side-fix: optimizer frontier Pareto filter

Hypothesis property test
`engine/tests/test_optimizer_validation.py::test_generated_valid_frontiers_keep_core_invariants`
surfaced a falsifying example during the R4 gate run:
`returns=[0.0625, 0.01, 0.01]`, `volatilities=[0.25, 0.125, 0.03125]`,
`rho=0.0`. The optimizer's `frontier.efficient` slice was including
dominated points (same/higher return at lower vol). Added
`_pareto_filter()` to `engine/frontier.py` that drops any candidate
dominated by another within a 1e-9 numerical tolerance. Pre-existing
edge case (R3 commit fails the same way); not R4-introduced. Drift
item #12 marked resolved.

### Locked decisions honored in R4

- #2 server roundtrip — every panel reads from `/api/preview/*`
  via TanStack Query; no client-side math duplication.
- #6 Goal_50 hidden — RiskSlider surface is canon 1-5 + descriptor
  only; the goal-score `derivation.anchor` field IS exposed as an
  advisor-transparent intermediate via the methodology-overlay
  context (R8), but the slider itself never displays it as a
  primary readout. Override POST payload is canon 1-5 + descriptor +
  rationale.
- #14 vocab CI — green; UI strings honor re-goaling discipline.
- #18 latency budget — staleTime 5min stays in effect; debounce
  helper available for slider drag in R5.
- #21 maximalist UX state — Skeleton + Sonner toasts + ConfirmDialog
  pattern continued; ConfirmDialog still pending for hard-destructive
  ops in R6.
- #28a i18n CI — every string flows through `t()`; no decorative
  unicode glyphs (Lucide icons throughout).
- #29 react-hook-form + zod — RiskSlider override form uses both
  for the rationale capture, verified via the e2e save flow.
- #30 Postgres concurrency — verified live during the deeper smoke;
  R4 frontend triggers the same `select_for_update()` path on every
  override save.
- #31a per-route ErrorBoundary — RouteFrame still wraps GoalRoute
  with `scope="goal"`; broken FanChart leaves the rest of the
  console working (verified during the Chart.js fixes earlier).
- #32 URL state + localStorage — selection in URL params,
  `mp20_last_client_id` survives across goal navigation.
- #37 audit emission — verified live (R3 deeper smoke + R4 e2e):
  POST override creates exactly one `goal_risk_override_created`
  AuditEvent with rationale + descriptor + previous/new score in
  metadata.

### R4 gate verification

- `uv run ruff check / ruff format --check` — clean
- `uv run mypy <R0 modules>` — Success: no issues found in 6 files
- `uv run pytest` — **313 passed in 32.46s** (after Pareto filter)
- `python web/manage.py makemigrations --check --dry-run` — No changes
- `bash scripts/check-vocab.sh` — vocab CI: OK
- `npm run typecheck / lint / format / build` — clean
- `npm run e2e:synthetic` (foundation.spec.ts) — **7/7 in 6.6s**
- Bundle: 728 kB JS / 18 kB CSS (gzip 230 kB / 4.45 kB) — Chart.js
  controllers + react-hook-form + zod + lucide additions; bundle
  budget deferred to R10 polish per locked decision #25.

### Known scope-trims for R4 (deferred follow-ups)

1. **Goal-score endpoint not yet wired in RiskSlider derivation
   panel.** The household-level anchor (Q1-Q4 → T/C → anchor 0-50)
   isn't exposed by `HouseholdDetailSerializer`. The slider saves
   overrides correctly without it; locked decision #19 fixture
   regeneration in R7 unblocks the live derivation breakdown.
2. **Hover-debounced probability fetch** on the FanChart is queued.
   The static probability-at-target badge ships now; per-year hover
   wiring to `/api/preview/probability/` follows.
3. **Plan-baseline + what-if dual overlay** (locked decision plan
   description) — the FanChart accepts a single set of paths today.
   When R5 wizard ships, planners will compute both a plan-baseline
   set and a what-if set; FanChart will accept two and stack them.
4. **Goal-allocation Compare toggle** (Current/Ideal/Compare) —
   shipped as a single 3-column table for now; the toggle that
   collapses to one view at a time is R10 polish.
