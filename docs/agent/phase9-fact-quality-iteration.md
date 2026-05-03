# Phase 9 — Fact-Quality Iteration (post-pilot)

**Status:** design (post-pilot scope; not in 2026-05-08 release)
**Owners:** Saranyaraj + Fraser (product)
**Trigger:** Phase 7 R10 sweep (this session, 2026-05-02) revealed
that Phase 4's tool-use migration eliminated hallucinations
(zero inferred-from-context facts; canon §9.4.5-correct) at the
cost of total fact count (Seltzer CS KYC.pdf 74 → 27 after fixes;
similar drops across other docs to be measured by the full sweep).
The pre-fix path's 17 inferred facts per KYC included probable
hallucinations (e.g., 4 goals + 9 goal_account_links on a 3-page
KYC doc that has none of those things) plus invented field paths
(`identification.*`, `kyc.*`, `next_steps.*`, `promotions.*`,
`real_estate.*`, `advisor.*`, `external_assets.*`) that aren't in
the canonical schema and feed only the noise channel.

**Core principle (load-bearing):** improve recall on the canonical
schema without sacrificing fidelity, no-fabrication discipline
(canon §9.4.5), or source attribution. Fact COUNT is a secondary
metric; ADVISOR PRODUCTIVITY (commit rate, manual-entry rate,
conflict-resolve time, time-to-first-portfolio) is primary.

---

## Deep diagnosis: why fact count dropped

Three concurrent causes after Phase 4:

1. **Tool-use schema as strict allowlist.** The
   `FACT_EXTRACTION_TOOL.input_schema` constrains the response
   shape but the model interprets the schema's `properties.field`
   description ("canonical MP2.0 field path") as a strict allowlist
   even though it is technically a string. Bedrock cannot emit
   `identification.*` etc. anymore — and rightfully so, those
   weren't engine-readable. Reduction here is a quality WIN.

2. **No-fabrication block is too strict + lacks per-class
   calibration.** `extraction/prompts/base.py:NO_FABRICATION_BLOCK`
   has 5 worked examples telling Bedrock to OMIT when uncertain.
   Bedrock generalizes "default to omission." Some legitimate
   cases (a goal name explicitly stated in narrative; a household
   `display_name` derived from the account-holder block) get
   omitted because the prompt nudges hard toward conservatism.
   Reduction here is partly a WIN (no hallucinations) and partly
   a LOSS (legitimate signal omitted).

3. **Per-doc-type prompts narrow extraction scope.** A KYC body
   tells Bedrock which fields to focus on. The pre-Phase-4
   unified prompt mentioned every canonical path inline so
   Bedrock would extract opportunistically. After Fix #2
   (`build_prompt_for` routes to generic for `multi_schema_sweep`
   classification), this is partly addressed for low-confidence
   classifications but the per-type bodies remain narrow for
   medium/high confidence classifications. Reduction here is a
   LOSS for cross-section facts that legitimately appear in
   per-type docs (e.g., a KYC that mentions a goal in passing).

---

## Alternatives considered (deep canvas)

### A. Permissive base + strict per-type
Loosen `NO_FABRICATION_BLOCK` to "extract any canonical field present;
be conservative only for inferred-from-prose values." Per-type
bodies stay strict for type-specific fields (KYC enums must be
lowercase; statement holdings must follow shape). Net: comprehensive
sweep across all sections + accurate per-type extraction. Risk:
Bedrock may swing back to over-extraction.

**Cost:** ~30 lines of prompt copy edits + canary re-run.
**Recall ↑** (legitimate goals/household/links return).
**Precision risk:** moderate; needs canary validation per
doc-type.

### B. Two-pass extraction with cross-validation
Pass 1: Permissive sweep (mirrors pre-Phase-4 scope). Pass 2:
Strict validation per fact via second Bedrock call: "for this
exact value/quote, is the extraction faithful to the source?"
Each fact gets verified; failed verification = drop the fact.
Net: high recall (Pass 1) + high precision (Pass 2). Cost: 2×
Bedrock calls per doc.

**Cost:** ~$0.50/doc instead of $0.25 (still under budget).
**Latency:** doubles (~10s → ~20s).
**Architecture:** new `verify_fact_against_quote` Bedrock tool
call; new `_verified_facts_from_extraction` pipeline step.

### C. Document-specific schema priming
Two-step: (1) Visual scan of section headers to detect what's in
the doc; (2) Tell Bedrock specifically "this doc has a goals
section starting at page 2 — extract goals[0..N].name +
target_amount + time_horizon_years." Net: targeted extraction;
high recall + precision. Cost: 2× calls.

**Implementation:** new `extraction/scout.py` runs first, returns
a per-doc inventory of detected sections; per-section extraction
calls follow.

### D. Multi-tool approach (Bedrock self-orchestrates)
Define multiple tool-use tools, one per canonical schema:
- `extract_household_facts`
- `extract_people_facts`
- `extract_accounts_facts`
- `extract_goals_facts`
- `extract_risk_facts`
- `extract_behavioral_notes_facts`

Bedrock can call any/all tools as needed. Each tool has strict
schema for its domain. Net: structured + comprehensive; Bedrock
decides scope. Cost: 1 call (Bedrock can invoke multiple tools
in one response).

**Risk:** Bedrock may not invoke all tools that should be called
(under-coverage if Bedrock's "internal scope" is too narrow).
**Win:** schema-per-section makes input_schema definition
clearer; behavioral_notes tool has a free-form schema (no
canonical-field allowlist).

### E. Inferred-with-evidence flag
Restore inferred-derivation-method facts BUT require explicit
evidence_quote that supports the inference. The OLD prompt allowed
inferred facts without enforcing quote-fidelity; many "inferred"
facts in pre-Phase-4 had thin or absent evidence_quote text.

**Implementation:** modify `derivation_method` enum to require
`source_text_match` validation when method is "inferred" — Bedrock
must include evidence_quote that's a verbatim substring of the
parsed doc. Validate with a quick character-overlap check
post-extraction.

### F. Adversarial validation
Separate "fact-checker" Bedrock call after extraction verifies
each fact against the source. Fails strict; passes ship. Net:
reduces hallucinations to near-zero. Cost: 2× calls (similar to B
but adversarial framing).

### G. Hybrid retrieval (RAG)
Use embeddings to find relevant text chunks per canonical field.
Extract only from relevant chunks. Net: precision ↑ via grounding;
recall depends on chunk retrieval quality.

**Cost:** new embedding model + embedding store (Pinecone /
pgvector). Higher infrastructure cost; longer setup; questionable
ROI for the per-doc volume the pilot operates at.

### H. Empirical end-to-end measurement
Run the new path in pilot. Measure advisor productivity:
- Commit-to-portfolio rate (within first 5 days of advisor pilot)
- Manual-entry rate (advisor uses /manual-entry escape hatch)
- Conflict-resolution time per workspace
- Time-to-first-portfolio per workspace
- Advisor NPS (5b.1 Feedback model rows tagged "suggestion")

If these match or exceed pre-Phase-4 baselines, the quality is
sufficient. Net: data-driven, low engineering cost, but slow
feedback (1-2 weeks of pilot data).

### I. Refined no-fabrication semantics
Modify `NO_FABRICATION_BLOCK` to distinguish:
- "Strong document signal" (named field labels, table cells,
  explicit values): extract eagerly.
- "Soft inference" (synthesized from prose): be conservative.

Net: clear signal to Bedrock about WHEN to be eager vs conservative.

### J. Per-field confidence-aware extraction
Each canonical field has its own "extraction policy":
- `people.display_name`: permissive (high recall; this is non-PII
  OK to err toward extracting); confidence based on context.
- `risk.household_score`: strict (only extract if explicit 1-5
  number; never infer).
- `goals[N].target_amount`: strict (no extraction from ranges).
- `behavioral_notes.*`: permissive (advisor narrative; volume is
  good).

Per-field policies guide Bedrock. Net: per-field calibration.

**Cost:** ~80 lines of policy table + prompt body update + per-
policy unit tests.

---

## Phase 9 plan (recommendation)

**Layered approach combining A + E + H:**

**9.1 — Empirical baseline (Week 1 of pilot)**
- Capture per-folder structural counts pre-pilot (already done by
  this session's R10 sweep).
- Capture per-doc fact counts + sections + confidence + derivation
  via existing `extraction.processing_metadata`.
- Measure advisor productivity:
  - Commit-to-portfolio rate
  - Manual-entry rate
  - Conflict-resolve time per workspace
  - Time-to-first-portfolio
- Triage any blocking-severity feedback (5b.1 Feedback model).

**9.2 — Permissive base + strict per-type (Week 2-3, if needed)**
- Modify `extraction/prompts/base.py:NO_FABRICATION_BLOCK`:
  - Soften the worked-examples block; replace "OMIT when uncertain"
    with "extract when document explicitly mentions; for
    range/aspirational language, emit with confidence='low' + the
    exact source quote."
  - Add a "STRONG signal" block listing the patterns that should
    always extract (named field labels, dollar amounts in cells,
    ISO dates, etc.).
- Per-type bodies (kyc.py, statement.py, etc.):
  - Add explicit "this doc may also contain X" guidance for
    cross-section facts (e.g., a KYC may mention a goal target
    amount in the regulatory_objective discussion).
- Re-run canary on Seltzer CS KYC.pdf; compare to current 27
  facts. Target: 35-50 medium-conf all-extracted.

**9.3 — Inferred-with-evidence-quote validation (Week 3-4)**
- Add `validate_fact_evidence_quote(fact, parsed_doc) -> bool`
  helper in `extraction/validation.py` (new file). Performs a
  character-overlap check: at least 60% of evidence_quote
  characters appear contiguous in `parsed_doc.text`.
- Modify `_facts_from_tool_use_response` to validate inferred
  facts; drop facts that fail validation; log dropped facts to
  `MP20_SECURE_DATA_ROOT/_debug/` for audit.
- Re-canary; target: zero dropped facts per legitimate doc; small
  drops (<5%) per noisy doc with hallucinations.

**9.4 — Multi-tool architecture exploration (Week 5-6, if 9.2+9.3
insufficient)**
- Define 6 tools (one per canonical section).
- Modify `extract_text_facts_with_bedrock` to pass `tools=[...]`
  with all 6; let Bedrock pick which to invoke.
- Behavioral_notes tool has free-form schema (no canonical-field
  allowlist) — captures the "advisor narrative" channel cleanly.
- Re-canary; measure recall by section.

**9.5 — End-to-end advisor productivity validation (Week 6+)**
- Compare advisor metrics (9.1 baseline) to post-9.x metrics.
- If improvement, ship. If regression, roll back to prior step.
- Document per-iteration outcomes in
  `docs/agent/phase9-experiments.md` (new file; per-iteration
  before/after tables).

---

## Stop conditions (load-bearing)

Phase 9 work HALTS + asks user via AskUserQuestion when:
- Any iteration regresses advisor commit rate by >5%.
- Any iteration introduces a new hallucination class detected via
  validation (9.3+).
- Bedrock spend > $50 for the iteration (per-iteration budget).
- An iteration's exit criteria not met after 2 attempts.

---

## Success criteria

Phase 9 is done when:
- Per-folder fact counts on the 7 R10 folders within ±10% of the
  pre-Phase-4 baseline (recall recovered).
- Zero `inferred` facts on `kyc` + `identity` + `statement` doc
  types (per canon §9.4.5; only EXTRACTED facts in structured
  docs).
- Some `inferred` facts allowed on `meeting_note` doc type when
  evidence_quote validation passes (advisor narrative reasonably
  produces inferred-from-quote claims).
- Hallucinated section paths (`identification.*`, `next_steps.*`,
  etc.) remain at 0 (Phase 4 win preserved).
- Advisor productivity metrics (9.1) match or exceed pre-Phase-4.

---

## Anti-patterns (DO NOT)

1. Re-introduce free-form JSON parsing.
2. Allow `derivation_method="defaulted"` (canon §9.4.5 prohibits
   default-to-make-it-fit).
3. Generate hallucinated section paths (the
   `identification.*`/`next_steps.*`/etc. class).
4. Accept high-confidence facts on a low-confidence
   classification (Phase 4 PROMPT-5 still holds).
5. Skip canary validation per iteration.
6. Push to origin during iteration without explicit user OK.

---

## Open questions for the pilot retrospective

1. Should `behavioral_notes.*` have its own free-form tool (Option D
   sub-feature)? The advisor narrative is structurally different
   from canonical engine input.
2. Should `derivation_method` enum gain a `behavioral_synthesis`
   value to distinguish "extracted advisor opinion from narrative"
   from "lifted explicit statement from structured doc"?
3. Should classification confidence cap apply only to
   engine-bound canonical fields, leaving `behavioral_notes.*`
   uncapped (since they're advisor narrative, not engine input)?
