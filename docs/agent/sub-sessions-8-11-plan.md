# Sub-sessions #8 → #11 Plan — Pilot-quality close-out

**Created:** 2026-05-03
**Authorized by user:** "Tier 1 + Tier 2 + Tier 3 right now; OCR via
Claude PDF/vision; no spend cap; automate everything."
**Estimated wall-clock:** ~8-10 days at full throttle.
**Estimated Bedrock spend:** $30-80 (no cap).

This doc is the single roadmap for the four sub-sessions that close
the gaps surfaced in the 2026-05-03 audit (`docs/agent/handoff-log.md`
near the end). Status updates land here as commits happen.

---

## Sub-session #8 — OCR/vision ingestion foundation

**Status:** complete (2026-05-03)
**Estimated:** 2 days, ~1500-2000 lines, ~$5-15 Bedrock canary
**Actual:** ~3h wall-clock, 715 lines diff, $0.14 Bedrock canary
**Outcome:** 5 Niesner image-PDFs that previously returned 0 facts
now extract 4-13 facts each via the new native-PDF path. Total
canary cost $0.1391 / 22.8K input + 4.7K output tokens / 53.3s
elapsed across 5 sequential calls. Per-doc cost $0.020-0.034 —
well under the $0.50 stop-condition. See
`docs/agent/bedrock-spend-2026-05-03.md` for the structural-only
breakdown.

### Why first

Croesus CRM exports many real-PII docs as image-only PDFs (KYC,
DOB, address printscreens). Current text-only pipeline returns 0
facts on those → advisor manually adds 30+ facts/doc via 5b.10/11
forms. Hours of friction per client.

Phase 9 fact-quality recovery + R10 7-folder sweep both depend on
having a working vision path.

### Approach

Native PDF document blocks via Bedrock InvokeModel API (which the
`AnthropicBedrock` SDK uses by default, NOT Converse):

```python
{
  "type": "document",
  "source": {
    "type": "base64",
    "media_type": "application/pdf",
    "data": <b64-encoded PDF bytes>,
  },
}
```

Per Anthropic docs (verified 2026-05-03): "PDF support is now
available on Amazon Bedrock... InvokeModel API: Provides full
control over PDF processing without forced citations." Bedrock
processes each page as both text + image for comprehensive
understanding.

### Detection

- `extraction/parsers.py:extract_text` already extracts text via
  pdfplumber/pypdf
- New: per-page extractability check. If `<50 chars per page` after
  text extraction → trigger vision path
- Hybrid case: mixed text+image PDFs run vision path (catches
  scanned regions; text path facts are subset of vision path)

### Implementation

1. **`extraction/llm.py`**:
   - New helper `extract_pdf_facts_with_bedrock_native` that sends
     the PDF as a `document` content block (NOT pre-rendered images)
   - Existing `extract_visual_facts_with_bedrock` (per-page image
     rasterization) becomes the fallback for non-PDF images
   - Audit metadata captures `extraction_path: "text" | "vision_native_pdf" | "vision_image_blocks"`
2. **`extraction/pipeline.py`**:
   - `extract_facts_for_document` dispatches based on text-extractability
   - Cost-tracking metadata: `bedrock_input_tokens`, `bedrock_output_tokens`,
     `bedrock_cost_estimate` written to `processing_metadata`
3. **Tests** (`extraction/tests/test_vision_pdf_path.py`):
   - Synthetic image-PDF fixture (rendered text → PDF → no extractable text)
   - Mock Bedrock vision response → assert facts extracted via vision path
   - Real Niesner image-PDF integration test (gated on real-PII flag)
   - Cost-tracking metadata test
4. **Audit + spend ledger**:
   - Each Bedrock call writes to `docs/agent/bedrock-spend-2026-05-03.md`

### Stop conditions

- Detection false-positive rate >10% (text-extractable PDF wrongly routed to vision) → tune threshold
- Vision path costs exceed $0.50/doc on canary → halt + ask
- Real-PII Niesner canary regresses fact count vs prior text path → halt + diagnose

### Exit criteria

- [ ] Native PDF path implemented + dispatched
- [ ] Detection helper with bounded false-positive rate
- [ ] 5+ unit tests passing; integration test against synthetic image-PDF
- [ ] Audit metadata includes per-call token + cost estimate
- [ ] Spend ledger updated with sub-session #8 canary results
- [ ] Real-PII Niesner canary: ≥1 doc that previously failed now extracts facts
- [ ] Full backend gate suite green
- [ ] Per-phase ping ~400 words

---

## Sub-session #9 — Phase 9 fact-quality recovery

**Status:** pending
**Estimated:** 1.5 days, ~1000 lines, ~$15-30 Bedrock canary

### Approach

Layered per the plan in `phase9-fact-quality-iteration.md`:
- **9.1 Permissive base prompt** — relax the strict no-fabrication
  copy + add explicit "extract every distinct field you can support
  with the document text" language
- **9.2 Per-type strict guards** — KYC must extract DOB; statement
  must extract balances; meeting note may infer aspirational facts
  with confidence cap
- **9.3 Inferred-with-evidence-quote validation** — every inferred
  fact MUST cite a verbatim evidence quote that supports it; missing
  quote → drop the fact
- **9.4 Re-canary against Seltzer + Weryha** — capture pre-Phase-9
  baseline (HEAD `9d03013`) + post-9.3 totals; compute recall delta
  per doc

### Stop conditions

- Recall recovery < 20% pp (Phase 4 lost 41 pp; want ≥20 pp recovery
  → ≥80% of pre-Phase-4) → halt + escalate
- Hallucinated section paths return → halt + tighten prompts
- Defaulted facts > 0 → halt + canon §9.4.5 violation

### Exit criteria

- [ ] 9.1 + 9.2 + 9.3 implemented
- [ ] Pre/post canary captured in `docs/agent/r10-sweep-results-2026-05-03.md`
- [ ] Recall delta ≥ 20 pp (target: match or exceed pre-Phase-4)
- [ ] Zero defaulted facts (canon §9.4.5)
- [ ] Zero hallucinated section paths (per `extraction.reconciliation.field_section`)
- [ ] All Phase 4 tool-use tests still pass
- [ ] Per-phase ping with structural per-doc diff

---

## Sub-session #10 — Tier 1 advisor friction close-out

**Status:** pending
**Estimated:** 2 days, ~2000 lines

### Items

1. **Inline edit polish** — date-picker (HTML5 `<input type="date">`),
   number input with min/max validation, dropdown for known-enum
   fields (risk_score 1-5, marital_status, regulatory_*), schema
   driven via canonical-field-shape map
2. **Field-path autocomplete** — full canonical-field listing in
   datalist (~50 fields); `goals[N]` index discovery from existing
   reviewed_state
3. **Progress indicator + ETA** — "Doc 3 of 12 — extracting (12-30s
   typical)" via existing polling state + per-doc ETA from
   worker_health timestamps
4. **Holistic commit-preview** — replace StatePeekPanel JSON with
   structured "About to commit" summary (people/accounts/goals/risk)
5. **Demo-state restore validated end-to-end** — actually run
   `scripts/reset-v2-dev.sh --yes` + Sandra/Mike + Seltzer/Weryha
   pre-upload, capture wall-clock + structural counts
6. **Undo on commit** — ASK USER for semantics first (soft-undo via
   audit event vs re-edit flow); design + implement chosen path

### Exit criteria

- [ ] All 6 items shipped
- [ ] AskUserQuestion answered before undo work begins
- [ ] Vitest unit tests for new components
- [ ] Backend tests for any new endpoints (e.g., undo endpoint)
- [ ] Per-phase ping

---

## Sub-session #11 — Tier 2 + Tier 3 + automated R10 sweep + close-out

**Status:** complete (deferred work closed in follow-up sub-session 2026-05-03 PM)
**Estimated:** 3 days, subagent-parallel where independent
**Actual (#11 first pass):** Tier 2 #11.1/#11.2/#11.3 shipped (audit
timeline + synthetic badge + verified existing missing-field
guidance). R10 sweep automation + cross-browser + Tier 3 polish
deferred.
**Actual (#11 follow-up):** All deferred items closed:
- R10 7-folder Playwright sweep automation (`scripts/demo-prep/r10_sweep.py`,
  ~570 lines) with worker-cleanup, cost-ceiling enforcement,
  idempotency guard, anonymize-folders flag, cleanup-on-failure;
  workspace DELETE endpoint added (5 backend tests).
- Cross-browser smoke (`frontend/e2e/cross-browser-smoke.spec.ts`)
  with webkit + firefox projects in playwright.config; 5/5 pass on
  both browsers.
- Tier 3 polish bundles A/B/C/D shipped via 4 parallel subagents;
  20 frontend Vitest cases added (Truncated, format helpers, wizard
  draft store).
- Code-reviewer subagent surfaced 1 BLOCKING + 5 critical findings;
  all fixed before sweep ran.

### Tier 2 items (~1.5 days)

- **R10 7-folder sweep automation**: Playwright drives upload of
  Gumprich/Herman/McPhalen/Niesner/Schlotfeldt/Seltzer/Weryha via
  the live UI; captures per-folder reconciled count, conflict count,
  failure count + structural metadata; writes to
  `docs/agent/r10-sweep-results-2026-05-03.md`
- **Missing-field guidance** — per-section blocker UI surfaces
  specific field names (not just "kyc not ready")
- **Audit timeline visible to advisor** — `useAuditTimeline()` hook
  + AuditTimelinePanel inside ReviewScreen
- **Conflict-rule heuristics** — saved-rule support: "for Person 0
  always prefer most-recent KYC" → applied automatically next time
- **Size cap revisited** — vision path can handle larger PDFs (no
  text-parser memory limits); raise cap to 100MB or chunk
- **Test-mode visual cue** — visible badge when `data_origin: synthetic`
- **Cross-browser smoke** — Safari + Firefox spec via Playwright;
  spot-check demo path

### Tier 3 polish (~1 day, subagent-parallel for ~6 agents)

Per `production-quality-bar.md` §1.10 — items still `[gap]`:
- Empty states with CTAs everywhere
- Error recovery affordances on every async surface
- Color-blind palette spot-check
- Number/date formatting audit (en-CA `$1,234,567.89` consistent)
- Long-text truncation + tooltip on hover
- Hover delay (300ms) on tooltips via Radix `delayDuration`
- Wizard step-progress indicator
- Save-as-draft on wizard
- "What's about to change" preview on Realign (before Apply)
- Drop-zone visual feedback strengthening
- Conflict card visual progression (intermediate "resolving" state)
- Resolved cards collapse/move to bottom

### Final close-out (~0.5 days)

- Cumulative ping covering #8-#11
- Tag verification (`v0.1.0-pilot` + decision on bumping to `v0.1.1-pilot`)
- Monday push staged but NOT executed (user pushes morning of)
- Update CLAUDE.md "Useful Project Memory" with new docs

---

## Project tracking discipline

Per user direction "think and reason deeply about project tracking":

1. **Per-sub-session ping** with: HEAD commit, diff highlights, audit
   findings closed, tests added, **full gate suite results**,
   **Bedrock $ delta vs estimate**, failures encountered + resolutions,
   reasoning, open items, next phase. ~400 words.
2. **This doc** updated as items complete (status timeline per row).
3. **`docs/agent/bedrock-spend-2026-05-03.md`** (new) — append-only
   ledger of every Bedrock canary run with per-call token counts +
   cost estimate.
4. **`docs/agent/post-pilot-improvements.md`** (new) — append-only
   capture of ideas surfaced during this work but deferred.
5. **Mid-sub-session checkpoints** (~50 words) at major milestones:
   "OCR detection working", "vision path producing facts",
   "Phase 9.1 prompts deployed", "R10 sweep folder N complete".

---

## Stop-and-ask points (locked, advance noticed)

| Sub-session | When | Question |
|---|---|---|
| #10 | Before undo implementation | Soft-undo via audit event OR re-edit flow? |
| #11 | After R10 sweep results | If a folder regresses, gate pilot launch on Phase 9 close-out OR ship with documented gap? |

Anything else surfaces via `AskUserQuestion` only if a fix grows
beyond ~150 lines OR Bedrock spend approaches $200/sub-session OR
a real-PII anomaly surfaces.
