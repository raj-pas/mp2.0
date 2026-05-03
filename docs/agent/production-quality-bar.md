# Production-Quality Bar — MP2.0 Limited-Beta Pilot

**Status:** living doc; load-bearing for sub-sessions #2–#7
**Last updated:** 2026-05-03
**Audience:** the next sub-session(s); referenced by the starter
prompt; honored at every per-phase ping

This doc captures what "production-grade for a limited user set"
means for MP2.0 — concretely, exhaustively, and with explicit
inspiration sources. The pilot is 3–5 Steadyhand advisors on real
client data; the user set is small but the quality bar is high.
We optimize for fidelity + audit-trail integrity + advisor
productivity, not for scaling to 10K users.

The starter prompt at `docs/agent/next-session-starter-prompt.md`
references this doc. Phases 5b polish + 6 + 6.9 + 7 + final-prep
all gate on the items below.

---

## 1. UX nuances per surface (Steadyhand advisor bar)

For each surface, the polish checklist below MUST be green before
the surface is considered release-ready. Items missing today are
flagged with `[gap]`.

### 1.1 Top bar (`frontend/src/chrome/TopBar.tsx`)

- [x] Brand mark + role-aware controls (advisor vs analyst).
- [x] PilotBanner above (server-side ack).
- [x] FeedbackButton (chrome-level).
- [ ] `[gap]` Keyboard navigation: Tab order rational; Cmd+K to
      open ClientPicker (deferred; nice-to-have).
- [ ] `[gap]` Self-hosted fonts (locked decision; verify
      `frontend/src/index.css` `@font-face` actually points at
      local `.woff2`, not Google CDN).

### 1.2 Client picker (`frontend/src/chrome/ClientPicker.tsx`)

- [ ] `[gap, 5b.7-pag]` Pagination — slice to 20 + "Load more"
      (filter applies to full set, not the slice).
- [ ] `[gap]` Debounced search input (250ms) — prevents
      re-render on every keystroke.
- [ ] `[gap]` Empty state — "No clients yet. Create one via the
      wizard." + link.
- [ ] `[gap]` Loading skeleton when households-list is in flight.
- [ ] `[gap]` Recent-client memory shown at top (already remembered
      via `useRememberedClientId`; surface visually).

### 1.3 Treemap + drill (`frontend/src/charts/Treemap.tsx`)

- [x] d3-hierarchy squarified treemap; click-to-drill into
      account/goal.
- [ ] `[gap]` Smooth fade transition on drill (≤200ms; respects
      prefers-reduced-motion).
- [ ] `[gap]` Breadcrumb at top: Household → Account → (back arrow).
- [ ] `[gap]` Empty-state when household has 0 accounts ("Add an
      account via the wizard").
- [ ] `[gap]` Tooltip on hover with delay (~300ms) showing
      account/goal value + percentage of total.

### 1.4 Account / Goal route (`frontend/src/routes/AccountRoute.tsx` + `GoalRoute.tsx`)

- [x] 4-tile KPI strip + Chart.js fund-composition + AllocationBars.
- [x] Source-attribution per value (via field_sources).
- [ ] `[gap]` Loading skeleton on initial load.
- [ ] `[gap]` Error state with Retry button if data fetch fails.
- [ ] `[gap]` Number formatting consistent: `$1,234,567.89` (en-CA),
      not `1234567`. Use `Intl.NumberFormat`.
- [ ] `[gap]` Date formatting consistent: `2026-05-03` ISO short-form
      OR "May 3, 2026"; pick one + apply everywhere.

### 1.5 Review screen (`frontend/src/modals/ReviewScreen.tsx`)

- [x] ProcessingPanel + ReadinessPanel + ConflictPanel +
      WorkerHealthBanner + SectionApprovalPanel + StatePeekPanel.
- [ ] `[gap, 5b.3]` Inline retry + manual-entry buttons per failed
      doc row (currently in a separate area).
- [ ] `[gap, 5b.5]` DocDetailPanel slide-out from right edge for
      per-doc fact contributions.
- [ ] `[gap]` Progress bar / ETA indicator on processing — Bedrock
      takes 5–30s per doc; advisor needs feedback that work is
      happening.
- [ ] `[gap]` Empty state when 0 documents uploaded (currently
      shows a stub).

### 1.6 Conflict resolution (`frontend/src/modals/ConflictPanel.tsx`)

- [x] Per-conflict card with multi-source candidates.
- [x] Redacted evidence quote per candidate.
- [x] ConfidenceChip (Phase 5b.9) wired into CandidateRow.
- [x] Rationale capture + evidence-ack checkbox.
- [ ] `[gap, 5b.12]` Bulk select across conflicts on the same
      field; submit applies same chosen value to all selected.
- [ ] `[gap, 5b.13]` Defer button + auto-re-surface visual badge
      ("New evidence — reconsider") when reconciliation finds
      a fresh fact for a deferred field.
- [ ] `[gap]` Visual progression: card transitions from
      "unresolved" (border-danger) → "resolving" (loading state
      after submit) → "resolved" (border-accent). Currently
      submit jumps directly to resolved without an intermediate
      state.
- [ ] `[gap]` Resolved cards collapse / move to bottom of panel
      so unresolved stays in focus.

### 1.7 Doc-drop overlay (`frontend/src/modals/DocDropOverlay.tsx`)

- [x] Drag-drop + file-list preview + upload mutation.
- [x] FileList race fix from R7 (snapshots `Array.from(picked)`).
- [ ] `[gap, 5b.4]` Pre-upload size-limit copy ("Max 50MB / file;
      larger files may time out").
- [ ] `[gap, 5b.4]` Failed-file retry button when partial-upload
      response includes ignored files.
- [ ] `[gap, 5b.4]` Client-side duplicate detection: compare
      sha256 (or filename + size) against current workspace
      `documents`; show "This file appears to already be
      uploaded — replace?" dialog.
- [ ] `[gap]` Drop-zone visual feedback: highlight on dragenter,
      restore on dragleave (currently subtle; advisors miss it).

### 1.8 Wizard (`frontend/src/wizard/HouseholdWizard.tsx`)

- [x] 5-step react-hook-form architecture.
- [x] sessionStorage + localStorage draft recovery.
- [x] Per-step trigger() validation.
- [ ] `[gap]` Step-progress indicator at top showing 1/5, 2/5...
      currently relies on labels alone.
- [ ] `[gap]` Save-as-draft button (advisor steps away mid-wizard).

### 1.9 Realignment / Compare / History (`frontend/src/modals/RealignModal.tsx` + `CompareScreen.tsx`)

- [x] Balance-preserving leg-shift modal.
- [x] Before/after compare with snapshot diff.
- [ ] `[gap]` "What's about to change" preview before user clicks
      Apply (currently shows the result, not the projected change).
- [ ] `[gap]` Undo affordance (revert to previous version) —
      advisor catches a mistake post-apply.

### 1.10 Cross-cutting polish (every surface)

- [ ] `[gap]` **Loading skeletons** — Linear-style; replace
      spinners on async surfaces. The Skeleton component exists
      (`frontend/src/components/ui/skeleton.tsx`); apply
      consistently.
- [ ] `[gap]` **Empty states with CTAs** — every list/table
      should have an empty-state copy + a clear next action.
- [ ] `[gap]` **Error recovery affordances** — every async
      surface that can fail should have a Retry button + a
      "Contact ops" link (`mailto:` or Feedback modal trigger).
- [ ] `[gap]` **Focus management** — modal/slide-out close
      restores focus to the trigger element. Radix Dialog does
      this by default; verify the manual modal in
      `FeedbackButton.tsx` does too.
- [ ] `[gap]` **Keyboard navigation** — Tab order rational across
      all forms; Esc closes modals; Enter submits forms; arrow
      keys navigate option lists where applicable.
- [ ] `[gap]` **prefers-reduced-motion** — every CSS transition
      / Chart.js animation respects the media query. Add a
      Tailwind utility or a global CSS rule.
- [ ] `[gap]` **Color-blind palette spot-check** — verify the
      paper/ink/copper/gold/buckets/funds palette doesn't rely
      on red-green discrimination for critical info. Manual
      review with a color-blind simulator (e.g. Sim Daltonism).
- [ ] `[gap]` **Toast deduplication** — `sonner` supports it
      via `dedupe`; verify our `toastError` / `toastSuccess`
      wrappers don't pile 5 identical toasts.
- [ ] `[gap]` **Number formatting** — `$1,234,567.89` (en-CA)
      everywhere. Helper `frontend/src/lib/format.ts` exists;
      audit usage.
- [ ] `[gap]` **Date formatting** — pick ONE format (ISO
      `2026-05-03` for tables; "May 3, 2026" for narrative)
      and apply consistently. Helper available; audit usage.
- [ ] `[gap]` **Long-text truncation** — `text-ellipsis` +
      tooltip on hover. `Tooltip` component or Radix Popover
      already in deps.
- [ ] `[gap]` **Hover delay** — tooltips show after ~300ms,
      not instant. Radix Tooltip has `delayDuration`; apply.

---

## 2. UX inspiration (concrete, not vague)

The "production-grade" bar is calibrated against products our
pilot advisors already use professionally. When in doubt about
a polish item, mirror the pattern from the inspirations below.

### 2.1 Linear (linear.app)

- **Keyboard-first navigation:** Cmd+K palette; J/K to scroll;
  Tab through controls. We don't need full keyboard parity but
  the Tab order should be deliberate.
- **Loading skeletons not spinners:** when fetching a list,
  show grey rectangles in the shape of the eventual rows, not a
  centered spinner.
- **Optimistic UI:** mutations update the UI immediately; revert
  on failure with a toast. Our `useResolveConflict` hook already
  does this; verify the others (state PATCH, approve-section).
- **Inline editing** (Phase 5b.10): click value → input
  appears in place; Enter saves, Esc cancels.

### 2.2 Notion (notion.so)

- **Slide-outs** (Phase 5b.5 DocDetailPanel) — context panel
  from the right edge; doesn't replace the parent view; advisor
  can scan multiple by clicking each.
- **Inline document hover preview** — hovering a doc-link in
  the workspace document list previews the doc card without a
  full navigation. Defer to post-pilot if heavy lift.

### 2.3 Stripe (stripe.com / dashboard.stripe.com)

- **Data tables:** dense, sortable, filterable, exportable. The
  feedback report (`/api/feedback/report/?export=csv`) already
  ships CSV export; verify the analyst UI (deferred to post-pilot)
  matches Stripe's table density when it lands.
- **Source attribution:** every value shows where it came from
  (event ID + timestamp). Our `field_sources` mirrors this; the
  source-attribution chips in ConflictCard are inspired by this.

### 2.4 GitHub PR review

- **Multi-source resolution:** the way GitHub shows conflict
  diffs side-by-side with "Use this side" buttons is exactly
  the conceptual model for ConflictCard. We've shipped this in
  Phase 5a.
- **Suggestion mode:** an inline-edit affordance that creates
  a suggested change rather than overwriting. Our FactOverride
  append-only pattern is the Phase 5b.10/11 analog.

### 2.5 Asana (asana.com)

- **Multi-select bulk actions** (Phase 5b.12 bulk conflict
  resolve) — shift-click to select range; toolbar appears with
  bulk-action buttons.
- **Filter chips:** active filters show as removable pills above
  the list. Useful for the analyst feedback-report UI
  (deferred).

### 2.6 macOS / Apple Human Interface

- **Modal vs sheet vs popover discipline:** modals for blocking
  decisions; sheets for in-context tasks; popovers for hovers
  and small selections. Our slide-outs are sheet-equivalent;
  RealignModal is a true modal; Tooltip is popover. Codify in
  `docs/agent/design-system.md` (Phase 5c).

---

## 3. End-to-end test coverage map (gating Phase 7)

Every surface + flow gets explicit coverage at one or more of
these levels. The matrix below is the source of truth for what
ships in Phase 6 + Phase 7.

### 3.1 Unit (Phase 6.6 Vitest + RTL + jest-dom)

Every new pure component from this session needs a unit test:

- `frontend/src/components/__tests__/ConfidenceChip.test.tsx` —
  level prop → rendering + ARIA label.
- `frontend/src/chrome/__tests__/PilotBanner.test.tsx` —
  version-mismatch handling, dismiss flow with mocked mutation.
- `frontend/src/chrome/__tests__/FeedbackButton.test.tsx` —
  modal open/close + form validation.
- `frontend/src/chrome/__tests__/WelcomeTour.test.tsx` — step
  navigation + complete/skip semantics.
- `frontend/src/components/__tests__/ConflictCard.test.tsx` —
  candidate selection + rationale validation + evidence-ack
  required.
- `frontend/src/modals/__tests__/DocDetailPanel.test.tsx` —
  slide-out open/close + facts grouped by section (after 5b.5).
- `frontend/src/modals/__tests__/WorkerHealthBanner.test.tsx` —
  visibility gating (only shows when stale/offline AND active
  jobs).

### 3.2 Hook unit (also Phase 6.6)

- `frontend/src/lib/__tests__/review.test.ts` — polling backoff
  semantics (3s base → 30s exponential; resets on user action).
- `frontend/src/lib/__tests__/auth.test.ts` —
  useAcknowledgeDisclaimer / useCompleteTour / useSubmitFeedback
  invalidation behavior.

### 3.3 Backend integration (existing patterns)

- Endpoint tests in `web/api/tests/test_*.py` — mirror the
  pattern from `test_phase5a_conflict_resolve.py` +
  `test_phase5b_chrome.py` + `test_provision_pilot_advisors.py`.
- Every new endpoint gets: happy-path, validation-failure,
  auth/RBAC, audit-event-emission, atomicity-pin (when
  state-changing), invalidated_approvals contract (when relevant).

### 3.4 Property-based (Phase 6.3 Hypothesis)

Three suites + a fourth recommended addition:

- `web/api/tests/test_fact_override_properties.py` —
  append-only invariants; latest-row-wins; audit count == row
  count.
- `extraction/tests/test_reconciliation_properties.py` —
  source-priority hierarchy invariants; cross-class silent;
  same-class surfaces conflict; deterministic.
- `web/api/tests/test_conflict_state_machine_properties.py` —
  active → deferred → resurfaced → resolved transitions; no
  resolved → deferred; one audit per transition.
- **NEW (recommended):**
  `web/api/tests/test_audit_invariant_properties.py` — for any
  random-shaped sequence of API calls against any state-changing
  endpoint, exactly one audit event per successful call;
  rollback emits zero events; metadata never carries `str(exc)`
  text.

### 3.5 Concurrency stress (Phase 6.5)

`web/api/tests/test_concurrency_stress.py` — 100 parallel
requests per state-changing endpoint via
`concurrent.futures.ThreadPoolExecutor`. Endpoints (matched
against the codebase as of HEAD `d8a6976`):

- `POST /api/review-workspaces/<wsid>/conflicts/resolve/` (5a)
- `POST /api/review-workspaces/<wsid>/documents/<did>/manual-entry/`
  (3.1)
- `PATCH /api/review-workspaces/<wsid>/state/`
- `POST /api/feedback/` (5b.1)
- `POST /api/disclaimer/acknowledge/` (5b.1)
- `POST /api/tour/complete/` (5b.1)
- `POST /api/clients/<hh>/generate-portfolio/`
- `POST /api/review-workspaces/<wsid>/commit/`
- After Phase 5b.10/11/12/13 ships:
  - `PATCH /api/review-workspaces/<wsid>/state/` with
    `fact_overrides[]` payload
  - `POST /api/review-workspaces/<wsid>/conflicts/bulk-resolve/`
  - `POST /api/review-workspaces/<wsid>/conflicts/<field>/defer/`

For each: assert no IntegrityError, audit count == success count,
final DB state consistent (no orphan rows; invariants hold),
`select_for_update` gaps surface as serialized.

### 3.6 Edge cases (Phase 6.7)

`web/api/tests/test_edge_cases.py` — 4 scenarios:

1. Empty / completely illegible doc (0 facts extracted) —
   `reconcile_workspace` graceful; manual-entry hatch reachable;
   section approvals correctly gated.
2. 1000+ facts overflow — query count bounded;
   `assertNumQueries`; UI doesn't lock up (Playwright load test
   on `/review/<id>/`).
3. Empty fields everywhere — Bedrock returns schema-irrelevant
   facts; surface "no extractable facts" message; failure code
   surfaced (`failure_code = no_canonical_facts`).
4. Non-English content (French-Canadian) — Bedrock routes
   ca-central-1; extraction is value-shape-agnostic;
   no UI rejection.

### 3.7 Migration rollback (Phase 6.8)

Per migration in `web/api/migrations/0010_*` (and any added
in 5b.10/11 if a new migration lands):

- `test_migration_<n>_rolls_back_cleanly` — apply forward, then
  reverse, assert tables/columns gone, no orphan FKs.
- One round-trip test applying all session-added migrations
  forward then all backward.

### 3.8 PII leak adversarial fuzzing (NEW — recommended)

`web/api/tests/test_pii_adversarial.py`:

- For each state-changing endpoint, mock the underlying handler
  to raise an exception whose `str()` contains the PII patterns
  in `web/api/review_redaction.py:_REDACTION_PATTERNS` (SIN,
  routing, phone, email, address) plus a synthetic SSN-shape
  + EIN-shape + credit-card-shape + DOB-shape.
- Assert the response body, audit-event metadata, and DB-stored
  failure_reason / last_error contain ZERO occurrences of the
  raw PII string. Use byte-comparison + regex search.
- Hypothesis-generate variations of PII patterns + assert the
  invariant holds across the search space.

### 3.9 Auth + RBAC matrix (NEW — recommended)

`web/api/tests/test_auth_rbac_matrix.py`:

- For every API endpoint × every role (anonymous, advisor,
  analyst, advisor-not-in-team, advisor-no-access-to-this-
  workspace), assert the expected status (200 / 401 / 403).
- Generate the matrix programmatically via URL introspection:
  iterate `urlpatterns`, hit each endpoint with a representative
  payload (or skip-with-XFAIL for endpoints that need a
  workspace setup), assert against an expected-codes table.
- Currently `test_auth_boundaries.py` covers some of this;
  expand to a comprehensive matrix.

### 3.10 Database invariants (existing 9/9; expand)

`web/api/tests/test_db_state_integrity.py` already enforces 9
invariants. Add (Phase 6+):

- `AuditEvent` row count grows monotonically (no deletes).
- `HouseholdSnapshot` + `FactOverride` + `PortfolioRun` enforce
  append-only via `save()` raising on existing pk.
- For every committed `Household`, the `field_sources` mapping
  in the parent `ReviewWorkspace.reviewed_state` references
  valid `ExtractedFact` rows.
- For every `PortfolioRun`, the linked `CMASnapshot` is in
  ACTIVE state at run time.

### 3.11 Performance budgets (Phase 6.9)

`web/api/tests/test_perf_budgets.py` — pytest-benchmark with
`--benchmark-min-rounds=20`. Locked decision #18: P50 < 250ms,
P99 < 1000ms. Endpoints to benchmark:

- All state-changing endpoints from §3.5.
- Read endpoints under realistic load:
  - `GET /api/review-workspaces/<wsid>/` with workspace having
    1000+ extracted facts.
  - `GET /api/feedback/report/?export=csv` with 1000 feedback
    rows.
  - `GET /api/clients/<hh>/portfolio-runs/` with 50+ runs.
  - `GET /api/clients/` with 50+ households.

### 3.12 Real-browser smoke (Phase 7.4 — NOT optional)

`frontend/e2e/real-browser-smoke.spec.ts` (existing) +
`frontend/e2e/pilot-features-smoke.spec.ts` (Phase 5b.smoke).

Run against the live host-mode stack with actual Chrome (NOT
headless). Coverage:

- **Existing demo flow** (the 8-step demo path):
  login → pick client → drill account/goal → /review →
  upload → reconcile → approve → commit → portfolio-gen.
- **Pilot features** (Phase 5b additions):
  PilotBanner show + dismiss + persist; FeedbackButton +
  modal + submit; WelcomeTour first-login + click-through +
  no-re-show; ConflictPanel render + resolve + bulk + defer
  (after 5b.12/13); DocDetailPanel slide-out + facts (after
  5b.5); inline failed-doc CTAs (after 5b.3);
  WorkerHealthBanner (synthetic stale-job trigger).
- **Network tab inspection**: open during a deliberately
  failing extraction → verify HTTP 4xx response body has
  `{detail, code}` only, NO raw exception strings (Phase 2
  PII verification).

### 3.13 axe-core a11y (Phase 5b.14 + Phase 7)

Currently `pilot-features-smoke.spec.ts` runs axe on `/` +
`/review`. Phase 7 expands to **every route + every modal +
every slide-out**:

- `/`, `/account/:id`, `/goal/:id`, `/review`, `/review/:id`,
  `/cma`, `/methodology`, `/wizard/new`
- All modals: DocDropOverlay, FeedbackModal, RealignModal,
  CompareScreen
- All slide-outs: DocDetailPanel (after 5b.5)
- All banners: PilotBanner, WorkerHealthBanner
- Tags: `wcag2a`, `wcag2aa`. Zero violations.

### 3.14 Cross-browser spot-check (NEW — Phase 7)

Pilot uses Chrome but advisors may fall back to Safari (macOS
default) or Firefox. Phase 7.5 (NEW):

- `npx playwright test --project=webkit e2e/real-browser-smoke.spec.ts`
- `npx playwright test --project=firefox e2e/real-browser-smoke.spec.ts`
- These discover CSS / layout regressions Chrome doesn't.
- Spot-check (not full suite) — verify login + treemap +
  review-screen render correctly + don't throw console errors.

### 3.15 Visual regression (NEW — Phase 7, optional)

If time permits, add Playwright screenshot diffs on key pages:

- `await page.screenshot({path: 'snapshots/review-screen.png'})`
- Compare against committed baseline; threshold ~1% pixel diff.
- Catches CSS regressions that functional tests miss.
- Defer if scope-bound; document the gap.

### 3.16 Demo dress rehearsal (Phase 7.2 — NOT optional)

`docs/agent/demo-script-2026-05-04.md` (verify exists; create if
not) walks the 8-step demo flow. Phase 7.2 task:

1. Reset demo state via `scripts/reset-v2-dev.sh --yes`.
2. Pre-acknowledge disclaimer + tour for the demo advisor user
   (so banner + tour don't disrupt step 1).
3. Re-pre-upload Sandra/Mike + Seltzer + Weryha via
   `scripts/demo-prep/upload_and_drain.py`.
4. Run the 8-step flow end-to-end IN ACTUAL CHROME:
   - login → pick Sandra/Mike → treemap drill →
     account/goal context-panel → /methodology overlay →
     pivot to Seltzer review screen → ConflictPanel resolve →
     commit → portfolio-gen → realign-and-compare → history.
5. Capture wall-clock time per step; flag any > 5s pause
   (advisor-perceived friction).
6. Re-run after any fix; demo state must be reproducibly clean.

---

## 4. Production-grade infrastructure (Phase 6.5 + 6.9 + 8 expansion)

### 4.1 Logging (Phase 6.5 expansion)

- Configure Django `LOGGING` to emit JSON-structured logs to
  stdout (Docker logs / journalctl visible).
- Use `python-json-logger` (already installed via Phase 0).
- Per-request middleware adds `request_id` UUID to every log
  line.
- Sensitive fields (Bedrock prompts, exception messages)
  redacted before log emission.
- Frontend: configure OpenTelemetry exporter (already in
  deps) to send anonymous performance events to an ops-chosen
  collector OR disable cleanly.

### 4.2 Monitoring + alerting hooks

- Define which log signals trigger ops attention:
  - `review_processing_failed` audit count > 5 in 1 hour
  - Bedrock 5xx error rate > 10% over 15 min
  - Worker heartbeat stale > 5 min (already surfaced via
    `WorkerHealthBanner`)
- Document the queries in `docs/agent/ops-runbook.md` (NEW;
  Phase 8 expansion).
- Integration with Datadog / Grafana / CloudWatch is
  out-of-scope for the pilot; ops monitors via `docker compose
  logs -f` for now.

### 4.3 Audit log retention

Currently audit-event rows are kept indefinitely. Document:

- Retention policy: indefinite (compliance + locked decision
  #37); audit log size will grow ~100KB/advisor/week
  (estimated based on event-emission rates).
- Backup: included in the standard pg_dump backup procedure
  (verify ops has this; document in `docs/agent/ops-runbook.md`).
- Right-to-delete (GDPR) handling: the audit log is excluded
  from individual deletion requests because it's a regulated
  record. Document in
  `docs/agent/pii-data-classification.md` (NEW).

### 4.4 PII data classification matrix

`docs/agent/pii-data-classification.md` (NEW) — per-table
classification:

| Table | PII level | Retention | Deletion policy |
|---|---|---|---|
| Household, Person, Account, Goal | High (real-PII) | Per advisor decision | Cascade on advisor request |
| ExtractedFact | High (raw evidence_quote) | Until advisor commits or 90 days | Cascade on workspace deletion |
| ReviewWorkspace, ReviewDocument | High (filenames; raw bytes in MP20_SECURE_DATA_ROOT) | 90 days post-commit | Cascade |
| AuditEvent | Medium (advisor IDs + structural metadata; no raw PII per Phase 2 scrub) | Indefinite | NEVER (compliance) |
| Feedback | Low-medium (advisor narrative; no client values per spec) | Indefinite | NEVER (compliance) |
| AdvisorProfile | Low (advisor email + ack timestamps) | Indefinite | NEVER (compliance) |
| FactOverride | High (advisor-typed values) | Indefinite | Cascade on workspace deletion |
| PortfolioRun | High (engine output references real households) | Indefinite | NEVER (regulated record) |
| CMASnapshot | None (engine inputs; no client data) | Indefinite | NEVER |

### 4.5 Secrets rotation (Phase 8 expansion)

`docs/agent/secrets-rotation.md` (NEW; ~1 page):

- Advisor passwords: ops generates via `make_password()` +
  pastes into the YAML config; advisor receives via secure
  channel (NOT Slack; 1Password sharing).
- Bedrock IAM: short-lived STS tokens preferred; if long-term
  AKIA in use, rotate every 90 days.
- AWS SSM Parameter Store stores all production secrets.

### 4.6 Disaster recovery beyond reset-v2-dev

Document in `docs/agent/pilot-rollback.md` §4 expansion:

- Full DB loss recovery from pg_dump backup (verify ops has a
  backup procedure + tested restore path).
- `MP20_SECURE_DATA_ROOT` raw bytes are gold; back up
  separately via S3 sync (ops decision; not in scope here).

---

## 5. Anti-patterns specific to production-grade

In addition to the anti-patterns in the master plan + starter
prompt:

1. **Don't paper over loading states with "instant" placeholders.**
   If the data isn't ready, show a skeleton; don't render
   stale or zero values that the advisor might mistake for
   real data.
2. **Don't show internal IDs to advisors.** `external_id` UUIDs
   are not advisor-facing; show display names + filenames
   instead.
3. **Don't show error stack traces to advisors.** Phase 2 PII
   discipline + advisor-facing copy must mediate.
4. **Don't use red as the only signal for "danger".** Add an
   icon + text label; color-blind users + screen-reader users
   need both channels.
5. **Don't truncate evidence_quote without a tooltip.** The
   advisor needs to see the full source quote on demand; a
   silent truncation hides decision-relevant context.
6. **Don't auto-save advisor input without a visual acknowledge.**
   "Saved at 2:34 PM" toast or label after auto-save.
7. **Don't use `setTimeout` for state transitions.** Use the
   actual mutation lifecycle (TanStack Query's
   `mutation.isPending`) so the UI reflects real state.
8. **Don't leak Bedrock latency into the advisor's wait.**
   Polling backoff + skeletons + progress indicators bridge
   the perceived gap.

---

## 6. Sub-session #2 (UX-polish pass scope)

The starter prompt's sub-session #2 was "5b.4 + 5b.5 +
5b.7-pag + 5b.10/11 + 5b.12/13" — feature work. Add to that
sub-session a UX-polish pass touching the gaps in §1.10:

- Loading skeletons across §1.2, §1.4, §1.5, §1.6
- Empty states + CTAs across §1.2, §1.4, §1.5
- Error recovery affordances across §1.4, §1.5
- Focus management on FeedbackModal + RealignModal
- prefers-reduced-motion via global CSS
- Number/date formatting audit (`grep -r "\\$" frontend/src/` +
  ensure all currency uses `Intl.NumberFormat`)
- Toast deduplication audit
- Hover delay on tooltips

This is ~200-400 additional lines spread across many files but
each change is small + low-risk.

---

## 7. Sub-session #6 (Phase 7 — full end-to-end validation)

This is the discrete Phase 7 sub-session that ties everything
together.

### 7.1 Full gate suite

Run the complete suite documented in §4 of
`docs/agent/next-session-starter-prompt.md`. Plus benchmark
suite + axe-core full-route coverage + cross-browser smoke.

### 7.2 Demo dress rehearsal

Per §3.16. Document timings + any friction findings.

### 7.3 R10 7-folder sweep (full)

The Phase 7 R10 sweep this session was partial (3 of 7 folders
in DB). Phase 7.3 either:

- (a) Re-uploads the missing 4 folders (Gumprich, Herman,
  McPhalen, Niesner, Schlotfeldt) if raw files are available,
  OR
- (b) Documents the partial sweep + per-folder structural
  comparison + Phase 9 follow-up commitment.

For each folder: per-doc reconciled count + structural fact
counts + per-doc-type confidence distribution. Compare against
pre-Phase-4 baseline (where available; Niesner had a 2026-05-01
baseline in handoff-log).

### 7.4 Real-browser smoke

Per §3.12. Both `real-browser-smoke.spec.ts` +
`pilot-features-smoke.spec.ts` against the live stack, with
network-tab PII verification. Plus the cross-browser spot-check
per §3.14.

### 7.5 axe-core full route + every modal + every slide-out

Per §3.13. Zero violations.

### 7.6 PII adversarial fuzzing live

Run `test_pii_adversarial.py` (per §3.8) against the live stack
to catch any PII leak the unit tests don't.

### 7.7 Demo state restore

After Phase 7 validates clean, restore demo state for Monday's
demo:
- `scripts/reset-v2-dev.sh --yes`
- `scripts/demo-prep/upload_and_drain.py Sandra/Mike +
  Seltzer + Weryha`
- Pre-acknowledge disclaimer + tour for the demo advisor
- Verify the 8-step demo flow renders cleanly one final time

---

## 8. Sub-session #7 (Monday push prep)

- Final per-phase ping summarizing the entire pilot release.
- Update `docs/agent/handoff-log.md` with the release tally.
- Verify CI workflow has all the new gates wired
  (`scripts/check-pii-leaks.sh`,
  `scripts/check-openapi-codegen.sh`, perf benchmark, axe-core,
  Vitest).
- Update CLAUDE.md "Useful Project Memory" with any final new
  pointers (production-quality-bar.md among them).
- Verify `git tag v0.1.0-pilot` is intact.
- Stage the push command for the user but DO NOT execute:
  `git push origin feature/ux-rebuild --tags`.
- Final verbose ping with: cumulative diff stats, test count
  delta, deferred items list, push-readiness checklist.

User pushes Monday morning. Ops deploys Monday-Wednesday. Pilot
launches 2026-05-08.

---

## 9. Quality bar at every per-phase ping

Every per-phase ping must explicitly answer:

1. **What changed** (HEAD + diff highlights + audit-finding closure refs).
2. **What was tested** (new tests + invariants pinned + manual smoke).
3. **What didn't ship** (open items + reason + path forward).
4. **What's next** (sub-session continuation + estimated scope).
5. **What's the risk** (regression possibilities + how the gates
   would catch them).

If any of those is missing, the ping is incomplete and the
sub-session isn't ready to hand off.
