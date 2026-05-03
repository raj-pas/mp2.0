# UX Spec — MP2.0 Limited-Beta + Forward (Living)

**Last updated:** 2026-05-03 (sub-session #3 — Phase 5c)
**Authoritative entry-points alongside this doc:**
- `MP2.0_Working_Canon.md` — product/strategy/regulatory/architecture
- `~/.claude/plans/i-want-you-to-rosy-mccarthy.md` — v36 master plan
- `~/.claude/plans/you-are-continuing-a-playful-hammock.md` — pilot
  hardening master plan with 50+ locked decisions
- `docs/agent/design-system.md` — design tokens + component taxonomy
- `docs/agent/extraction-audit.md` — extraction subsystem audit
- `docs/agent/post-pilot-ux-backlog.md` — Tier-3 deferred items

This document is the durable cross-session UX canon for MP2.0
advisor-facing surfaces. It captures *what's shipped*, *what's
deferred*, and *the principles that should govern future work*.
Update in place; never delete; append to **Decision Log** at the
bottom when a non-obvious design choice lands.

---

## Purpose

Stop UX drift across sessions. Earlier in this project, sessions
shipped features that locally made sense but globally diverged
(FileList race, prompt-versioning-without-prompt-body-divergence,
Goal_50 leakage to advisor surfaces). The fix: a single
authoritative spec that future Claude Code sessions read on
startup before touching any advisor-facing surface.

---

## UX Dimensions (A through M)

Captured from the 2026-05-02 UX-dimensions audit + sub-session #2
shipping work. Each row carries a **status** (✓ SHIPPED / ⚠ PARTIAL
/ ✗ MISSING / 🚫 OUT-OF-SCOPE), file:line evidence where applicable,
and severity tier.

### A. Onboarding ergonomics

| ID | Dimension | Status | Evidence | Tier |
|---|---|---|---|---|
| A.1 | Login → first-paint < 2s | ✓ SHIPPED | `session.staleTime=60s` + auth gate first | PILOT |
| A.2 | Welcome tour for first-time advisors | ✓ SHIPPED | `WelcomeTour.tsx`; server-side ack via `tour_completed_at` | PILOT |
| A.3 | Inline retry / manual-entry CTAs per failed doc row | ✓ SHIPPED | `ReviewScreen.tsx:303-388` | PILOT |
| A.4 | Failure-reason tooltip + a11y describedby | ✓ SHIPPED | `ReviewScreen.tsx:330-340` (Phase 5b.3) | PILOT |
| A.5 | Attempt counter on retry | ✓ SHIPPED | `ReviewScreen.tsx:319-326` (Phase 5b.3) | PILOT |
| A.6 | Loading affordance on retry button | ✓ SHIPPED | `Retrying…` while `retry.isPending` | PILOT |
| A.7 | Failed-file retry without re-pick | ✓ SHIPPED | `DocDropOverlay.tsx` (Phase 5b.4) | PILOT |
| A.8 | Pre-upload size limit copy | ✓ SHIPPED | dropzone empty-state "Max 50MB per file" | PILOT |
| A.9 | Pre-upload duplicate detection | ✓ SHIPPED | `admitFiles` filter (Phase 5b.4) | PILOT |

### B. Fact extraction visibility

| ID | Dimension | Status | Evidence | Tier |
|---|---|---|---|---|
| B.1 | Per-doc detail panel showing this doc's facts | ✓ SHIPPED | `DocDetailPanel.tsx` slide-out (Phase 5b.5) | PILOT |
| B.2 | Confidence chip per fact | ✓ SHIPPED | `ConfidenceChip.tsx` (Phase 5b.9) | PILOT |
| B.3 | Confidence indicator visual | ✓ SHIPPED | color + text label (WCAG 2.1 AA) | PILOT |
| B.4 | Source attribution chip per fact | ✓ SHIPPED | `ConflictPanel.CandidateRow` | PILOT |
| B.5 | Inline fact edit | ✓ SHIPPED | `FactEditForm` in DocDetailPanel (5b.10) | PILOT |
| B.6 | Edit history per fact | ⚠ PARTIAL | `FactOverride` model is append-only; UI surface deferred | NICE-TO-HAVE |
| B.7 | Add-missing-fact affordance | ✓ SHIPPED | `AddFactSection` in DocDetailPanel (5b.11) | PILOT |
| B.8 | Redacted evidence quote per candidate | ✓ SHIPPED | `redact_evidence_quote` pipeline | PILOT |

### C. Conflict resolution

| ID | Dimension | Status | Evidence | Tier |
|---|---|---|---|---|
| C.1 | Multi-source candidate cards | ✓ SHIPPED | `ConflictCard` (Phase 5a) | PILOT |
| C.2 | Required-section conflict blocker | ✓ SHIPPED | `section_blockers` | PILOT |
| C.3 | Rationale capture per resolution | ✓ SHIPPED | textarea + `rationale_required` validation | PILOT |
| C.4 | Evidence acknowledgement gate | ✓ SHIPPED | checkbox + `evidence_ack_required` validation | PILOT |
| C.5 | Bulk conflict resolve | ✓ SHIPPED | `BulkResolveBar` + `useBulkResolveConflicts` (5b.12) | PILOT |
| C.6 | Defer-a-conflict + auto-resurface | ✓ SHIPPED | `useDeferConflict` + `_conflicts` rebuild (5b.13) | PILOT |
| C.7 | Visual hierarchy: required vs nice-to-have | ✓ SHIPPED | red border for required, hairline for nice | PILOT |

### D. Workspace + household management

| ID | Dimension | Status | Evidence | Tier |
|---|---|---|---|---|
| D.1 | Client picker with full search | ✓ SHIPPED | `ClientPicker.tsx` | PILOT |
| D.2 | Pagination on large rosters | ✓ SHIPPED | PAGE_SIZE=20 + Load more (5b.7) | PILOT |
| D.3 | Favorites/pinning | 🚫 OUT-OF-SCOPE | post-pilot UX backlog | — |
| D.4 | Archived-workspace filter | 🚫 OUT-OF-SCOPE | post-pilot | — |
| D.5 | Workspace label search | ✓ SHIPPED | client-side filter on full set | PILOT |
| D.6 | Last-client memory across navigation | ✓ SHIPPED | `useRememberedClientId` localStorage | PILOT |
| D.7 | Workspace rename | 🚫 OUT-OF-SCOPE | needs PATCH endpoint | — |
| D.8 | Workspace sharing | 🚫 OUT-OF-SCOPE | team-shared by default | — |
| D.9 | Workspace handoff between advisors | 🚫 OUT-OF-SCOPE | post-pilot | — |

### E. Document management

| ID | Dimension | Status | Evidence | Tier |
|---|---|---|---|---|
| E.1 | Per-doc status visibility | ✓ SHIPPED | status chip + filename + size | PILOT |
| E.2 | Replace-vs-add semantics (statement supersedes) | 🚫 OUT-OF-SCOPE | post-pilot | — |
| E.3 | Bulk doc upload | ✓ SHIPPED | DocDropOverlay multi-file | PILOT |
| E.4 | Per-doc retry | ✓ SHIPPED | inline button (R7 + 5b.3 polish) | PILOT |
| E.5 | Manual-entry escape hatch | ✓ SHIPPED | retry-resistant `failure_code` set | PILOT |
| E.6 | OCR overflow visibility | ✓ SHIPPED | `processing_metadata.ocr_overflow` | PILOT |

### F. Onboarding wizard

| ID | Dimension | Status | Evidence | Tier |
|---|---|---|---|---|
| F.1 | Multi-step wizard with draft recovery | ✓ SHIPPED | `HouseholdWizard.tsx` + sessionStorage | PILOT |
| F.2 | Per-step validation | ✓ SHIPPED | react-hook-form + zod | PILOT |
| F.3 | Risk-slider with override flow | ✓ SHIPPED | `RiskSlider.tsx` (R4) | PILOT |
| F.4 | CSV bulk import | 🚫 OUT-OF-SCOPE | post-pilot | — |
| F.5 | Grid editor | 🚫 OUT-OF-SCOPE | post-pilot | — |

### G. Worker + system health

| ID | Dimension | Status | Evidence | Tier |
|---|---|---|---|---|
| G.1 | Session-interruption recovery | ✓ SHIPPED | upload-recovery + draft restore (5b.8) | PILOT |
| G.2 | Worker health banner | ✓ SHIPPED | `WorkerHealthBanner` (5b.2) | PILOT |
| G.3 | Polling backoff under load | ✓ SHIPPED | exponential 3s→30s (5b.7) | PILOT |
| G.4 | Auto-recovery from worker stalls | ✓ SHIPPED | `requeue_stale_jobs` cron | PILOT |
| G.5 | Concurrent-edit detection | 🚫 OUT-OF-SCOPE | locked decision; team-shared | — |

### H. Recommendation surfaces

| ID | Dimension | Status | Evidence | Tier |
|---|---|---|---|---|
| H.1 | Three-tab household/account/goal pivot | ✓ SHIPPED | R3 stage routes | PILOT |
| H.2 | Per-recommendation explainability tooltip | ✓ SHIPPED | "why this recommendation" summary | PILOT |
| H.3 | Compare modal | ✓ SHIPPED | `CompareScreen` (R6) | PILOT |
| H.4 | Realignment + revert flow | ✓ SHIPPED | `RealignModal` (R6) | PILOT |
| H.5 | Audit drawer with run hash + trace | ✓ SHIPPED | append-only PortfolioRunEvent | PILOT |
| H.6 | Export / PDF report | 🚫 OUT-OF-SCOPE | post-pilot | — |

### I. Accessibility

| ID | Dimension | Status | Evidence | Tier |
|---|---|---|---|---|
| I.1 | WCAG 2.1 AA semantic HTML | ✓ SHIPPED | semantic + ARIA where needed | PILOT |
| I.2 | Focus-visible on interactive elements | ✓ SHIPPED | `focus-visible:` Tailwind utility | PILOT |
| I.3 | axe-core e2e on every route | ⚠ PARTIAL | `pilot-features-smoke.spec.ts` covers some routes; full coverage in sub-session #6 | PILOT |
| I.4 | Color-blind palette audit | 🚫 OUT-OF-SCOPE | post-pilot | — |
| I.5 | Font scaling > 200% | 🚫 OUT-OF-SCOPE | post-pilot | — |
| I.6 | Skip-link | 🚫 OUT-OF-SCOPE | post-pilot | — |
| I.7 | prefers-reduced-motion | ✓ SHIPPED | global @media rule (UX-polish) | PILOT |

### J. Performance ergonomics

| ID | Dimension | Status | Evidence | Tier |
|---|---|---|---|---|
| J.1 | Loading skeletons everywhere | ✓ SHIPPED | `Skeleton` component used in all queries | PILOT |
| J.2 | Empty states with helpful copy | ✓ SHIPPED | per-route empty-state copy | PILOT |
| J.3 | Polling with backoff | ✓ SHIPPED | (G.3 above) | PILOT |
| J.4 | Pagination on long lists | ✓ SHIPPED | (D.2 above) | PILOT |
| J.5 | Toast dedup under rapid mutations | ✓ SHIPPED | `lib/toast.ts` 1.5s window (UX-polish) | PILOT |

### K. First-run advisor experience

| ID | Dimension | Status | Evidence | Tier |
|---|---|---|---|---|
| K.1 | Welcome tour with 3 coachmark steps | ✓ SHIPPED | `WelcomeTour` (5b.6) | PILOT |
| K.2 | Server-side ack so tour doesn't re-show on other devices | ✓ SHIPPED | `tour_completed_at` | PILOT |

### L. Notes + collaboration

| ID | Dimension | Status | Evidence | Tier |
|---|---|---|---|---|
| L.1 | Notes per household | 🚫 OUT-OF-SCOPE | post-pilot | — |
| L.2 | Notes per goal | 🚫 OUT-OF-SCOPE | post-pilot | — |
| L.3 | Free-text feedback channel | ✓ SHIPPED | `FeedbackButton` + Feedback model (5b.1) | PILOT |

### M. Governance + compliance

| ID | Dimension | Status | Evidence | Tier |
|---|---|---|---|---|
| M.1 | Pilot disclaimer ribbon | ✓ SHIPPED | `PilotBanner` + server ack (5b.1) | PILOT |
| M.2 | Real-PII redaction in evidence quotes | ✓ SHIPPED | `redact_evidence_quote` (REDACT-1) | PILOT |
| M.3 | Audit export | 🚫 OUT-OF-SCOPE | post-pilot | — |
| M.4 | PII visibility dashboard | 🚫 OUT-OF-SCOPE | post-pilot | — |
| M.5 | Append-only audit + advisor traceability | ✓ SHIPPED | `record_event` + DB triggers | PILOT |

---

## Top-level Design Principles

### Vocabulary discipline (canon §6.3a + §16, vocab CI enforced)

- **Risk descriptors**: Cautious / Conservative-balanced / Balanced
  / Balanced-growth / Growth-oriented (NEVER low/medium/high).
- **Fund vocabulary**: building-block fund (NOT sleeve), whole-portfolio
  fund.
- **Re-goaling vocabulary**: re-goaling, re-allocate, re-balance
  (NEVER "transfer", "move money", "reallocation" without hyphen).
- **Engineer-internal**: Goal_50 is engine-internal; never surfaces
  to advisor copy.

### Real-PII discipline (canon §11.8.3)

- Server-side redaction in evidence quotes (account numbers, SINs,
  routing, phones, addresses).
- Bedrock ca-central-1 only for `data_origin: real_derived`.
- Structural counts in handoffs / docs / chat ("12 docs, 285 facts");
  never raw client values.
- `MP20_SECURE_DATA_ROOT` outside repo for raw artifacts.
- `str(exc)` NEVER in DB columns / API response bodies / audit
  metadata. PII grep guard enforces.

### AI-numbers rule (canon §9.4.5)

- LLM never invents financial numbers, names, dates, or any field.
- Surface gaps as advisor blockers, not silent defaults.
- `derivation_method = "defaulted"` is a code-smell; Phase 7 R10
  sweep eliminated 2 of these and the post-pilot Phase 9 plan
  explicitly forbids re-introducing them.

### Source-priority hierarchy (canon §11.4)

- SoR > structured > note-derived (cross-class silent resolution).
- Same-class disagreements surface as conflict cards.
- Advisor override (FactOverride, Phase 5b.10) is highest priority.

### Engine-is-library boundary (canon §9.4.2)

- `engine/` never imports framework code.
- Web translates DB models → `engine.schemas` Pydantic at boundary.
- Advisor surfaces never speak engine internals (no Goal_50, no
  raw 0-50 risk score, no internal `schema_version`).

---

## Component Taxonomy

When to use what:

| Pattern | When to use | Examples |
|---|---|---|
| **Card** | Persistent UI for facts + KPIs | KPIStrip, RecommendationCard |
| **Banner** | Top-of-page system state | PilotBanner, WorkerHealthBanner |
| **Modal** | Blocking task with clear cancel | DocDropOverlay, RealignModal, CompareScreen |
| **Slide-out (right edge)** | Contextual deep-dive without losing parent | DocDetailPanel (5b.5) |
| **Toast** | Transient confirmation/error | toastSuccess/Error/Info |
| **Coachmark** | First-time-only orientation | WelcomeTour (5b.6) |
| **Inline form** | In-place edit/add per row | FactEditForm, AddFactSection (5b.10/11) |
| **Inline action bar** | Multi-select bulk operation | BulkResolveBar (5b.12) |

### Density rules

- Compact for tables / lists (px-3 py-2, text-[12px]).
- Generous for context panels + slide-outs (p-4, text-[13px]).
- Mono uppercase tracking-widest for muted/uppercase metadata (font-mono text-[10px]).

### Loading states

- `<Skeleton />` rectangles for content > 1 line.
- Spinner only for very-short ops (< 500ms expected).
- Progress bar for multi-step (e.g., upload progress).

---

## Copy Tone

- **Advisor-facing**: direct, action-oriented, vocab-CI-compliant.
  ("Approve required sections: ...", "Re-pick the 12 files you
  dropped before for 'Niesner onboarding' to continue.")
- **Analyst-facing**: precise, technical, audit-trail-aware.
- **Error copy**: structured (code + friendly message + next-step
  CTA). NEVER `str(exc)`.
- **i18n namespace**: `<surface>.<element>.<state>` (e.g.,
  `review.failure_code.bedrock_token_limit`,
  `doc_detail.add_save`).

---

## Motion + Animation

- Subtle, fast (≤ 200ms), no decorative animation.
- `motion-safe:` Tailwind prefix for any `animate-*` utility.
- Global `@media (prefers-reduced-motion: reduce)` (UX-polish pass)
  caps animation/transition duration to 1ms.
- Treemap drill-down + CompareScreen are the only "narrative"
  animations.

---

## Iconography

- `lucide-react` only. No unicode glyphs in advisor-facing surfaces
  (locked decision; R2 patterns).
- `aria-hidden` on every decorative icon; aria-label or text content
  carries the semantic intent.

---

## Accessibility Commitments (WCAG 2.1 AA target)

- Semantic HTML first; ARIA only when semantic insufficient.
- `focus-visible:` required on all interactive elements.
- Modals trap focus + return on close (Radix Dialog default).
- Slide-outs auto-focus close button on open + bind Escape (DocDetailPanel).
- Color + text label (NEVER color-only).
- Tooltip + aria-describedby on chips that carry actionable info.

---

## Canonical Flows

### 1. 8-step demo flow (per `demo-script-2026-05-04.md`)

Login → ClientPicker → Treemap drill → Review → DocDrop →
Reconcile → Conflict resolution → Section approval → Commit →
Portfolio generation.

### 2. Advisor week-1 onboarding flow

PilotBanner ack → WelcomeTour (3 steps) → ClientPicker (or "Add
new household") → Wizard or /review with DocDrop → Watch reconcile
→ Section approvals → Commit.

### 3. Multi-conflict resolution flow

ConflictPanel renders cards → advisor picks candidate per card →
EITHER single-resolve per card OR add-to-bulk → BulkResolveBar
shared rationale + evidence_ack → Submit → audit emitted per
conflict.

### 4. Annual-update flow (post-commit doc addition)

New workspace + link to existing household → upload new docs →
reconcile → review changes (delta highlighted) → commit creates
new HouseholdSnapshot.

### 5. Realignment + compare + revert flow (R6)

PortfolioRun draft → CompareScreen side-by-side current/proposed →
optional revert via append-only `PortfolioRunEvent`.

---

## Decision Log

Append-only. Each entry: date + decision + justification.

- **2026-05-02** — Per-doc-type prompt modules (Phase 4): single
  body unified prompts ignored doc-type-specific extraction patterns;
  user flagged "prompts are lacking" — per-type modules with shared
  guardrails restore canon §11.3 schema differentiation.

- **2026-05-02** — Coordinated PII scrub (Phase 2): five distinct
  sites carried `str(exc)`; a single typed-error-to-code mapper
  applied at every site is the bounded fix; CI grep guard prevents
  regression.

- **2026-05-02** — Pilot disclaimer ships at limited-beta (Phase 5b.1):
  locked decision #17 deferred for "iterative scope" but a 3-5
  advisor pilot launching 2026-05-08 needs the disclaimer as a
  governance/consent surface, not a polish item.

- **2026-05-02** — Tier-3 UX items defer to post-pilot (Phase 5b.Tier-3):
  a 3-5 advisor pilot with daily triage absorbs friction; a public
  launch wouldn't. Mobile, advanced collab, full a11y audit,
  export/PDF are not week-1 blockers.

- **2026-05-02** — Slide-out from the right edge for DocDetailPanel:
  non-blocking, parent context preserved; sets the design-system
  pattern for "contextual deep-dive without losing parent context."
  Codified for future contextual surfaces.

- **2026-05-03** — FactOverride mechanism reuses one append-only
  model for both override (Phase 5b.10) and add-missing-fact
  (Phase 5b.11): `is_added: bool` is the only distinction. Source
  priority: advisor override > extracted fact (canon §11.4 advisor
  wins).

- **2026-05-03** — Bulk conflict resolve emits one audit event
  per conflict (locked #37) with `bulk: True` + `bulk_count: N`
  metadata for ops correlation. Audit emitted AFTER atomic block
  commits to avoid orphan rows on rollback.

- **2026-05-03** — Defer-conflict auto-resurface compares prior
  fact_ids vs fresh fact_ids; if the set GREW, mark
  `re_surfaced_at`. Stable when no new evidence (no spurious
  flapping). Preserves resolution state across reconcile (resolved
  conflicts keep chosen_fact_id + rationale + resolved_by).

- **2026-05-03** — Toast dedup as a 1.5s memory window in
  `lib/toast.ts`. Same `(kind, message, description)` triple
  within window suppressed. Prevents stacking under rapid
  mutation chains.

- **2026-05-03** — Global prefers-reduced-motion via @media rule
  in `index.css`. animation-duration + transition-duration capped
  to 1ms. Single rule covers Tailwind + Radix + Sonner without
  per-component edits.

- **2026-05-03** — Upload session-interruption recovery (Phase
  5b.8): preserve label + data_origin + workspace_id + file
  metadata in sessionStorage. File bytes can't be serialized;
  advisor re-picks. Option D (workspace_id reuse + 404 fallback)
  + Option E (stash before any API call) over literal Option C
  for production-grade robustness.

---
