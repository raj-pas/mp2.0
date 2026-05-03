# Design System — MP2.0 (Living)

**Last updated:** 2026-05-03 (sub-session #3 — Phase 5c)
**Companion to:** `docs/agent/ux-spec.md` (UX dimensions + flows +
decision log)

This doc captures the design substrate: tokens, component inventory,
patterns, copy conventions, iconography, accessibility conventions,
and architectural patterns (ErrorBoundary, focus management).

---

## Token Reference

### Colors (`frontend/tailwind.config.ts`)

#### Brand palette
- **ink** `#0E1116` (DEFAULT), `#1A1F26` (`ink-2`) — primary text
- **paper** `#FAF8F4` (DEFAULT), `#F1EDE5` (`paper-2`) — surfaces
- **accent** `#C5A572` gold (DEFAULT), `#8B5E3C` copper (`accent-2`)
- **hairline** `rgba(14,17,22,0.10)` (DEFAULT), `rgba(14,17,22,0.18)`
  (`hairline-2`) — borders + dividers
- **muted** `#6B7280` (DEFAULT), `#9CA3AF` (`muted-2`) — secondary text

#### Risk-band colors (canon-aligned descriptors)
- `buckets.cautious` `#5D7A8C` (Cautious / low)
- `buckets.conservative-balanced` `#6B8E8E`
- `buckets.balanced` `#C5A572`
- `buckets.balanced-growth` `#B87333`
- `buckets.growth-oriented` `#8B2E2E`

#### Semantic
- **success** `#2E5D3A`
- **danger** `#8B2E2E`
- **info** `#2E4A6B`

#### Fund palette (matches `engine/sleeves.py` SLEEVE_COLOR_HEX)
- `funds.sh-sav`, `sh-inc`, `sh-eq`, `sh-glb`, `sh-sc`, `sh-gsc`,
  `sh-fnd`, `sh-bld` — see config for hex values

### Typography
- **Serif** (brand): Fraunces variable axis 9–144
- **Sans** (body): Inter Tight 300–700
- **Mono** (metadata + uppercase labels): JetBrains Mono 400–600
- Self-hosted via @font-face in `frontend/src/index.css` (locked
  decision #22d). Falls back to system fonts gracefully.

### Spacing
- Tailwind default scale.
- Custom letter-spacing tokens for mono uppercase:
  - `tracking-wider` = 0.06em
  - `tracking-widest` = 0.14em
  - `tracking-ultrawide` = 0.18em

### Radius
- `rounded-none` (default — square corners per mockup).
- `rounded-sm` for chips + small UI marks.
- `rounded-md` for inputs.
- `rounded-2xl` for large cards (rare — used in R7 era; phasing
  out for square mockup parity).

### Shadows
- `shadow-sm` `0 1px 2px rgba(14,17,22,0.04)`
- `shadow` `0 4px 12px rgba(14,17,22,0.06)` (DEFAULT)
- `shadow-lg` `0 16px 48px rgba(14,17,22,0.08)`
- `shadow-xl` `0 24px 64px rgba(14,17,22,0.12)` — slide-outs

### Animation keyframes
- `slideInFromRight` 100% → 0% translate (180ms ease-out)
- `slideInFromLeft` -100% → 0% translate
- `fadeIn` opacity 0 → 1
- All gated by `motion-safe:` prefix; global @media reduced-motion
  rule caps to 1ms.

---

## Risk Vocabulary

`frontend/src/lib/risk.ts` — canon-aligned descriptors. Goal_50 is
engine-internal only; never surfaces in advisor copy. The 1-5
risk-score scale maps to descriptors via `riskDescriptorFor(score)`.

---

## Fund Vocabulary

- **Building-block fund** (NOT "sleeve"). Whole-portfolio fund
  metadata surfaces via SLEEVE_REF_POINTS calibration in
  `engine/sleeves.py`.
- Direct fund weights first; asset/geography look-through metadata
  available as drilldown.

---

## Component Inventory

### Chrome (`frontend/src/chrome/`)
- **TopBar** — global navigation + ClientPicker + GroupBy toggle +
  user chip + FeedbackButton.
- **PilotBanner** — disclaimer ribbon with server-side ack.
- **ClientPicker** — Radix Popover with search + paginated list
  (Phase 5b.7) + Add-new-household CTA.
- **ModeToggle** — group-by-account / group-by-goal segmented control.
- **WelcomeTour** — 3-step coachmark for first-login (5b.6).
- **FeedbackButton** — opens FeedbackModal; submits to backend.
- **BrandMark** — Steadyhand wordmark + accent.

### Components (`frontend/src/components/`)
- **ConfidenceChip** — color + text label per fact confidence
  (Phase 5b.9). Reuses `accent` / `muted` / `danger` tokens.
- **ErrorBoundary** — top-level + per-route. Catches uncaught
  render errors with structured fallback UI.
- **Skeleton** — `animate-pulse bg-paper-2` rectangle for loading
  states.
- **ui/button** — `Button` variants: default / outline / ghost /
  destructive / link. Sizes: sm / icon / default / lg.
- **ui/dialog** — Radix-based modal with backdrop + focus trap.
- **ui/RiskSlider** — 5-band canon-aligned risk picker with override
  flow (R4).
- **ui/skeleton** — see above.

### Routes (`frontend/src/routes/`)
- **HouseholdRoute** — three-tab stage: AUM strip + treemap.
- **AccountRoute** — KPI strip + Chart.js fund-composition ring +
  AllocationBars.
- **GoalRoute** — KPI tiles + RiskBandTrack + linked accounts.
- **CmaRoute** — analyst-only CMA Workbench + frontier chart.
- **MethodologyRoute** — overlay with R8 sections + TOC.
- **ReviewRoute** — workspace list + pick OR DocDropOverlay.
- **LoginRoute** — auth gate.

### Modals (`frontend/src/modals/`)
- **DocDropOverlay** — multi-file drop + workspace create + upload
  flow. Includes 5b.4 (size limit + dup detect + retry-failed) +
  5b.8 (session-recovery).
- **DocDetailPanel** — slide-out per-doc detail (5b.5) + inline
  fact edit (5b.10) + add-missing-fact (5b.11).
- **ReviewScreen** — workspace detail with ProcessingPanel +
  ReadinessPanel + ConflictPanel + SectionApprovalPanel +
  StatePeekPanel.
- **ConflictPanel** — conflict cards (Phase 5a) + bulk-resolve bar
  (5b.12) + defer affordance (5b.13).
- **CompareScreen** — side-by-side current/proposed allocations.
- **RealignModal** — re-allocate flow (R6).

### Charts (`frontend/src/charts/`)
- **Treemap** — d3-hierarchy squarified treemap with click-to-drill.
- **AllocationBars** — horizontal bars per fund weight.
- **RingChart** — Chart.js doughnut for fund composition.
- **RiskBandTrack** — 5-band marker for goal risk.
- **EfficientFrontier** — analyst-only Chart.js scatter.

### Lib (`frontend/src/lib/`)
- **api.ts** — `apiFetch` wrapper; ApiError class.
- **api-error.ts** — `normalizeApiError` + `isAuthError` helpers.
- **api-types.ts** — generated by openapi-typescript (CI gate).
- **auth.ts** — useSession + useLogin + DISCLAIMER_VERSION.
- **review.ts** — all review-pipeline TanStack hooks.
- **clients.ts** — useClients hook.
- **household.ts** — useHousehold + useHouseholdState.
- **toast.ts** — Sonner wrapper with dedup (UX-polish).
- **upload-recovery.ts** — sessionStorage helpers (5b.8).
- **risk.ts** — canon risk-descriptor helper.
- **format.ts** — `formatCadCompact`, `formatCadFull`, etc.
- **cn.ts** — `clsx` wrapper.

### i18n (`frontend/src/i18n/`)
- `en.json` — full namespace per surface
- `fr.json` — placeholder for French-Canadian (locked decision #12;
  populated post-pilot)

---

## Patterns: When To Use What

### Card vs Banner vs Modal vs Slide-out vs Toast vs Coachmark

| Pattern | Persistent? | Blocking? | Loses parent context? | Examples |
|---|---|---|---|---|
| Card | ✓ | ✗ | ✗ | KPIStrip, RecommendationCard |
| Banner | ✓ | ✗ | ✗ | PilotBanner, WorkerHealthBanner |
| Modal | ✗ | ✓ | ✓ | DocDropOverlay, RealignModal |
| Slide-out (right) | ✗ | ✗ | ✗ (semi-transparent backdrop) | DocDetailPanel |
| Toast | ✗ | ✗ | ✗ | toastSuccess/Error/Info |
| Coachmark | ✗ (one-time) | ✓ (until dismissed) | ✗ (overlays) | WelcomeTour |
| Inline form | depends | ✗ | ✗ | FactEditForm |

Rules of thumb:
- Block the user only when the action MUST complete or be cancelled
  (Modal). For deep-dive without blocking, use Slide-out.
- Toast for transient confirmations (≤ 5s). For persistent state
  changes, use a Banner.
- Inline forms (in-place edit) preserve scroll position + don't
  require navigation back.

---

## Copy Conventions

### Re-goaling vocabulary (vocab CI enforced)
- ✓ Re-goaling, re-balance, re-allocate
- ✗ Reallocation, transfer, move money

### Error copy structure
- `code` — stable advisor-safe code (e.g., `bedrock_token_limit`)
- `friendly_message` — i18n key (e.g.,
  `review.failure_code.bedrock_token_limit`)
- `next_step_cta` — what to click next (e.g., "Mark as manual entry")

### i18n namespace
- `<surface>.<element>.<state>`
- Examples:
  - `review.failure_code.bedrock_token_limit`
  - `doc_detail.add_save`
  - `chrome.feedback.submit_pending`
  - `topbar.client_picker_load_more_one`

### Pluralization
- `..._one` / `..._other` — react-i18next handles via `count` param.
- Fall back via `defaultValue`.

---

## Iconography

- **lucide-react** only. No unicode glyphs.
- `aria-hidden` on decorative icons.
- `aria-label` or accompanying text for semantic icons.
- Common icons:
  - `Upload` — dropzone
  - `Plus` — add
  - `Pencil` — edit
  - `X` — close / remove
  - `ChevronDown` — expand
  - `Check` — confirm

---

## Accessibility Conventions

- **Semantic HTML first**: `<button>` for actions, `<a>` for navigation,
  `<form>` for grouped inputs, `<dl>` for definition lists.
- **ARIA only when semantic insufficient**: `role="dialog"` +
  `aria-modal` + `aria-labelledby` for modals.
- **Focus-visible required** on all interactive elements (focus-visible
  ring class in `button.tsx`).
- **Modals trap focus + return on close** (Radix Dialog default).
- **Slide-outs** auto-focus close button on open + bind Escape.
- **Forms**: `<label>` wraps each input; `<legend>` for fieldset
  groups; `aria-describedby` for error/help text.
- **No autoFocus attr** (jsx-a11y/no-autofocus); use useEffect + ref
  pattern.
- **Color + text label** (NEVER color-only).
- **prefers-reduced-motion** honored globally.

---

## ErrorBoundary Architecture

- **Top-level ErrorBoundary** in `frontend/src/App.tsx` catches uncaught
  render errors before they surface to white-screen.
- **Per-route ErrorBoundary** inside `RouteFrame` catches route-scoped
  errors (caught the R9 frontier bug — see `r10-mockup-parity.md` §10).
- New routes MUST wrap in `RouteFrame`.
- Fallback UI: structured "Something went wrong" with reload + report
  CTAs.

---

## Focus Management Patterns

- **Modal opens** → Radix Dialog auto-focuses first focusable.
- **Slide-out opens** → useEffect + ref to focus close button.
- **Inline edit form opens** → useEffect + ref to focus first input
  (NOT autoFocus attr; jsx-a11y/no-autofocus).
- **Modal closes** → focus returns to trigger.
- **Slide-out closes** → focus returns to triggering doc row (not
  always; backdrop-click closes don't auto-restore).

---

## Mutation Hook Patterns

All mutation hooks follow this shape:

```ts
export function useFooMutation(workspaceId: string | null) {
  const qc = useQueryClient();
  return useMutation<Response, Error, Payload>({
    mutationFn: (payload) => {
      if (workspaceId === null) {
        return Promise.reject(new Error("workspace id required"));
      }
      return apiFetch<Response>(
        `/api/.../${encodeURIComponent(workspaceId)}/...`,
        { method: "POST", body: payload },
      );
    },
    onSuccess: () => {
      if (workspaceId === null) return;
      qc.invalidateQueries({ queryKey: <relevantKey> });
    },
  });
}
```

Why:
- Consistent error type (`Error`).
- Defensive `null` check to avoid throwing in render.
- Invalidation on success (TanStack pattern) so refetches reflect
  the new state.

---

## Slash Commands the Frontend Relies On

- `npm run codegen` — regenerate `frontend/src/lib/api-types.ts`
  from drf-spectacular schema. Run after any backend serializer
  change. CI gate `scripts/check-openapi-codegen.sh` fails on
  drift.
- `npm run e2e:synthetic` — Playwright e2e against the synthetic
  Sandra/Mike persona.

---
