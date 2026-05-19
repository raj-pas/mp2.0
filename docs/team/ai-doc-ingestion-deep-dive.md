---
title: AI document ingestion + engine-ready data creation — deep dive
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
status: living
audience: engineers, technical PMs, anyone owning a piece of the ingestion or commit pipeline
update_when: A layer boundary shifts (e.g., extraction prompt schema bump, new
  Tier classification, additional readiness gate), a new document type is
  added, a new typed exception is added, the auto-trigger source list
  changes, the audit-action vocabulary changes materially, or a state-machine
  transition is added/removed/renamed.
---

# AI document ingestion + engine-ready data creation — deep dive

This document is the definitive technical reference for how a real Steadyhand
client document — uploaded by an advisor through the browser — becomes a
committed household plus a generated portfolio recommendation. It traces the
full Layer 1 → Layer 5 extraction pipeline, the commit boundary, the
synchronous engine auto-trigger, and the audit emission that follows every
state change.

Read this when you need to understand any of:

- Why a specific document is stuck in a specific status
- What an extracted fact actually represents and where it lives
- How conflicts surface to the advisor for adjudication
- Why the engine produced (or didn't produce) a recommendation after a commit
- Where to add a new document type, fact field, or audit action
- What "real-PII discipline" means in operational terms at each layer

Companion documents (load with this):

- [`architecture-diagrams.md`](architecture-diagrams.md)
  — visual flow at 30,000 ft
- [`real-pii-handling.md`](real-pii-handling.md) — defense-in-depth regime
- [`glossary.md`](glossary.md) — vocabulary for every concept used below
- [`adr/0007-three-tier-entity-matcher.md`](adr/0007-three-tier-entity-matcher.md)
  — Tier-2 rationale
- [`adr/0009-sync-auto-trigger.md`](adr/0009-sync-auto-trigger.md)
  — sync-in-transaction rationale
- [`adr/0003-bedrock-ca-central-1.md`](adr/0003-bedrock-ca-central-1.md)
  — fail-closed routing
- [`adr/0012-source-priority-hierarchy.md`](adr/0012-source-priority-hierarchy.md)
  — conflict resolution
- [`../../MP2.0_Working_Canon.md`](../../MP2.0_Working_Canon.md)
  — canon §11 is the authoritative spec

---

## Part 1 — The 30,000-foot view

### 1.1 What the pipeline does, in one sentence

A Steadyhand advisor drops one or more real client documents (KYC, custodial
statement, planning narrative, meeting note) into the secure browser upload;
within a few minutes the system has parsed them, extracted structured facts
via an AI model, reconciled the facts across documents into a single
canonical state, surfaced conflicts and missing fields for advisor
adjudication, and — once the advisor commits — produced a goal-by-account
portfolio recommendation that respects the household's risk tolerance, the
regulatory profile of each account, and the live Capital Market
Assumptions (CMA).

### 1.2 The five layers + the commit boundary + the engine handoff

```
ADVISOR BROWSER                                        OUTSIDE THE WEB REQUEST
─────────────────                                      ────────────────────────
                                                                │
[DocDropOverlay]                                                │
   │  POST /api/review-workspaces/                              │
   │  POST /api/review-workspaces/<id>/upload/                  │
   ▼                                                            │
┌─────────────────────────────────────────────────────────────┐ │
│ LAYER 1 — INGESTION                                          │ │
│   - Secure-root validation (MP20_SECURE_DATA_ROOT)           │ │
│   - SHA-256 dedup                                            │ │
│   - ReviewDocument + ProcessingJob rows created              │ │
└─────────────────────────────────────────────────────────────┘ │
                              │ enqueued                        │
                              ▼                                 │
                                                  ┌─────────────┴───────────────┐
                                                  │ WORKER PROCESS              │
                                                  │ (process_review_queue cmd)  │
                                                  │                             │
                                                  │ ┌─────────────────────────┐ │
                                                  │ │ LAYER 2 — PARSING       │ │
                                                  │ │   pymupdf, python-docx, │ │
                                                  │ │   openpyxl, csv, OCR    │ │
                                                  │ └─────────────────────────┘ │
                                                  │             │               │
                                                  │             ▼               │
                                                  │ ┌─────────────────────────┐ │
                                                  │ │ LAYER 2.5 — CLASSIFY    │ │
                                                  │ │   kyc / statement /     │ │
                                                  │ │   planning / note /     │ │
                                                  │ │   identity / generic    │ │
                                                  │ └─────────────────────────┘ │
                                                  │             │               │
                                                  │             ▼               │
                                                  │ ┌─────────────────────────┐ │
                                                  │ │ LAYER 3 — LLM EXTRACT   │ │
                                                  │ │   Bedrock ca-central-1  │ │
                                                  │ │   Tool-use JSON schema  │ │
                                                  │ │   FactCandidate emit    │ │
                                                  │ └─────────────────────────┘ │
                                                  │             │               │
                                                  │             ▼               │
                                                  │ ┌─────────────────────────┐ │
                                                  │ │ LAYER 4 — RECONCILE     │ │
                                                  │ │   3-tier entity match   │ │
                                                  │ │   Source-priority pick  │ │
                                                  │ │   Conflict surface      │ │
                                                  │ └─────────────────────────┘ │
                                                  └─────────────┬───────────────┘
                                                                │ reconciled
                                                                ▼
                                                        (workspace polled by FE)
                              ┌─────────────────────────────────────────────────┐
[ReviewScreen]                │ LAYER 5 — REVIEW                                │
   │                          │   reviewed_state JSON projection                │
   │   ConflictPanel          │   Readiness (engine + construction + KYC)       │
   │   MissingPanel           │   Section approvals (6 required)                │
   │   FactOverride           │   Tier-2 merge candidates (advisor adjudicate)  │
   │   SectionApproval        │                                                 │
   │   Commit                 │                                                 │
   ▼                          └─────────────────────────────────────────────────┘
                                                  │ commit gate passes
                                                  ▼
                              ┌─────────────────────────────────────────────────┐
                              │ COMMIT BOUNDARY (review_state.py)               │
                              │   commit_reviewed_state                         │
                              │     → _create_household_from_state              │
                              │       or _merge_household_state                 │
                              │   Account-type case normalization HERE          │
                              │   Cascade-delete + re-create entities           │
                              │   AuditEvent: review_state_committed            │
                              └─────────────────────────────────────────────────┘
                                                  │ fires (synchronous,
                                                  ▼ inside transaction)
                              ┌─────────────────────────────────────────────────┐
                              │ AUTO-TRIGGER (views.py)                         │
                              │   _trigger_and_audit(source="review_commit")    │
                              │     → _trigger_portfolio_generation             │
                              │       → engine.optimize(...)                    │
                              │   PortfolioRun row created (append-only)        │
                              │   PortfolioRunEvent: portfolio_run_generated    │
                              └─────────────────────────────────────────────────┘
                                                  │
                                                  ▼
                                            (response 200 +
                                             PortfolioRun inline)
```

The five layers all live in `extraction/` plus `web/api/review_state.py` for
Layer 5. The commit boundary is `commit_reviewed_state` in `review_state.py`.
The auto-trigger is the helper trio in `web/api/views.py`. The engine is a
pure-Python library in `engine/` invoked via `web/api/engine_adapter.py`.

### 1.3 What "engine-ready" means

A household is **engine-ready** when:

1. All six required review sections (`household`, `people`, `accounts`,
   `goals`, `goal_account_mapping`, `risk`) have an approved status row.
2. The `readiness.engine_ready` flag is `true`. This means every required
   field has at least one extracted (or advisor-overridden) value.
3. The `readiness.construction_ready` flag is `true`. This means committed
   household data passes the engine's optimization preconditions: every
   account type is in `ALLOWED_ENGINE_ACCOUNT_TYPES`, every risk score is in
   1–5, no more than 2 people, and Purpose accounts are fully assigned to
   goals (summing to either current_value within ¢, or to 100%).

The commit endpoint refuses to seal the household unless all three hold. The
auto-trigger then runs the engine synchronously in the same transaction; if
the engine raises one of the five typed exceptions, the commit still
succeeds and the failure is captured as an audit event + a
`latest_portfolio_failure` field on the household serializer.

### 1.4 Why this design exists

A few non-obvious choices govern the entire pipeline:

- **Two AI surfaces with different trust models.** Layer 3 is the *only*
  place AI is allowed to interpret and emit structured facts. Layer 4 is a
  deterministic pure-Python reconciler. This split bounds non-determinism to
  a small, audited layer. (See [ADR-0001](adr/0001-engine-as-library.md) for
  the engine's purity invariant, which is the same idea taken to its
  conclusion.)

- **Synchronous engine call in the mutation transaction.** The advisor sees
  the new PortfolioRun *inline* in the commit response — no polling, no
  "click commit, wait for recommendation, refresh." This is feasible only
  because the engine is a pure-Python library, not a service hop. See
  [ADR-0009](adr/0009-sync-auto-trigger.md).

- **AI never invents financial numbers.** Canon §9.4.5. The LLM emits only
  what's in the document. If a value isn't there, the system surfaces a
  blocker; it never defaults, guesses, or interpolates. The pipeline has
  zero "make-it-reconcile" fallbacks.

- **Real-PII flows from day one under defense-in-depth.** Real Steadyhand
  client data has been in the system since the secure-local review tranche
  landed. Every layer enforces a control: secure-root validation,
  ca-central-1 fail-closed Bedrock routing, transient raw text, hashed
  identifiers, redacted evidence quotes, immutable audit, RBAC. See
  [`real-pii-handling.md`](real-pii-handling.md) and
  [ADR-0004](adr/0004-real-pii-defense-in-depth.md).

---

## Part 2 — Layer 1: Ingestion

### 2.1 The frontend upload entry point

The advisor lands on `/review`, sees an existing workspace queue plus the
`DocDropOverlay` at the top of the route. The overlay is the *only* path
through which real PII enters the system; there is no CLI ingestion route
for real data.

**Component:** `frontend/src/modals/DocDropOverlay.tsx`.

**User-facing controls:**

- Workspace label (free-text, no validation)
- Data origin selector: `synthetic` (development persona) or `real_derived`
  (real Steadyhand client). The selector gates server-side Bedrock routing
  and secure-root enforcement.
- Drag-and-drop zone with motion-safe visual feedback
- Hidden `sr-only` file input (keyboard-accessible)
- File list display with per-file dedup + 50 MB rejection toast

### 2.2 The two-mutation closure pattern

Upload is a two-step API sequence that must always run in order:

1. `POST /api/review-workspaces/` — creates the workspace, returns
   `external_id`.
2. `POST /api/review-workspaces/<id>/upload/` — multipart file upload, one
   `ProcessingJob` enqueued per file.

The frontend never parallelizes these. The create-mutation's `onSuccess`
handler fires the upload-mutation. Between the two, the workspace_id is
stashed back to `sessionStorage` so a 401 mid-upload doesn't leak orphans.

### 2.3 The FileList ref race + StrictMode double-update bugs (R7 history)

Two now-fixed bug classes are worth understanding because they govern how
the upload code is written today:

**Bug 1: FileList ref race.** `event.target.files` is a *live* reference to
the input's selected files. Clearing `event.target.value = ""` (to reset the
input) clears the live reference too. If the handler later reads the
reference asynchronously (inside a deferred React state setter), it gets an
empty list.

**The fix:** snapshot to a static `Array.from(picked)` *before* clearing
the input. Same fix applies to `event.dataTransfer.files` in the drop
handler.

**Bug 2: StrictMode double-update.** React 18 StrictMode invokes state
updaters twice in dev. If the updater mutates a closure-captured array
(e.g., `accepted.push(file)` inside the updater), each file gets pushed
twice — visible as "2 files ready to upload" for one dropped file.

**The fix:** classify against an at-call-time snapshot *outside* the
updater; produce an immutable `accepted` list; pass it into the updater as
a pure spread (`prev => [...prev, ...accepted]`). The updater becomes a
pure function and is safe under double-invocation.

Both fixes are in `DocDropOverlay.tsx`. They're worth memorizing because the
same patterns will recur in any future drag-and-drop surface.

### 2.4 Session-storage upload recovery

Upload is the most failure-prone moment in the entire workflow: the user is
new, the network is unpredictable, real PII is in flight. The system
defends against three classes of interruption:

- **401 mid-upload** (auth session expired). The workspace exists; some
  files uploaded, some didn't.
- **Browser crash / tab close**. State lost.
- **User clicks away pre-upload**. Files selected but not started.

The recovery flow:

1. On "Start review" click, the overlay stashes the current draft —
   `{label, data_origin, files: [{name, size}, ...]}` — to `sessionStorage`
   under `"mp20.upload-draft.v1"`.
2. After workspace create, the stash is updated with the workspace_id.
3. On 401 during retry, the failed-files context is stashed.
4. On overlay mount, `consumeUploadDraft()` reads + clears the stash. If
   present, a "Resume" banner appears with the previous label, data origin,
   and file list. The advisor re-picks the actual files (browser security
   doesn't let JavaScript replay a FileList) and submits.
5. TTL: 30 minutes. Expired drafts are silently dropped.

### 2.5 Backend acceptance + secure-root validation

The endpoint is `ReviewWorkspaceUploadView` in `web/api/views.py`. Two
gates run before any file lands on disk:

**Gate 1: secure-root validation.** `MP20_SECURE_DATA_ROOT` must be set in
the environment and must point to a directory *outside* the repository. If
either is false, the view returns 503 with code `secure_root_missing`. The
emitted audit event is `real_upload_blocked` with the reason; no file
content touches the disk.

**Gate 2: per-file SHA-256 dedup.** Each file's bytes are hashed; if a
matching SHA-256 already exists in the workspace's documents, the upload is
recorded as a duplicate (status `duplicate`) rather than re-creating a
`ProcessingJob`. This is idempotent — re-uploading the same file is a no-op
beyond the audit event.

### 2.6 Disk layout under secure-root

Successful uploads land under:

```
$MP20_SECURE_DATA_ROOT/
└── <workspace_external_id>/
    ├── <document_id>__<safe_filename>.<ext>
    └── _debug/                               ← debug-only Bedrock dumps
        └── <extraction_run_id>-<stage>-<timestamp>.txt
```

Filenames are sanitized; the original filename is preserved in
`ReviewDocument.original_filename`. The path validation logic refuses any
path that doesn't resolve cleanly under the secure root (defense against
directory traversal).

### 2.7 What gets persisted in Layer 1

| Table | Row | Carries |
| --- | --- | --- |
| `ReviewWorkspace` | one per intake session | label, data_origin, status (DRAFT), owner, secure-root subpath |
| `ReviewDocument` | one per accepted file | original_filename, content_type, extension, file_size, sha256, status (UPLOADED), storage_path, processing_metadata (empty dict initially) |
| `ProcessingJob` | one per ReviewDocument | job_type=`process_document`, status (QUEUED), attempts=0, max_attempts (default 3) |
| `AuditEvent` | per state transition | `review_workspace_created`, `review_documents_uploaded`, `review_workspace_deleted` (on DELETE), `real_upload_blocked` (on gate failure) |

### 2.8 File size + format limits

- Per-file size cap: 50 MB (client-side check; mirrored server-side)
- Per-upload count: not capped, but practical worker throughput is ~12 docs
  in ~3–5 minutes for a typical Steadyhand client folder
- Accepted formats: PDF, DOCX, XLSX, CSV, MD, TXT, PNG, JPG. Anything else
  is accepted into Layer 1 but Layer 2 will route it to `unsupported`.

---

## Part 3 — Layer 2: Parsing

### 3.1 The entry point

Layer 2 lives in `extraction/parsers.py`. The function
`parse_document_path(path)` returns a `ParsedDocument` dataclass:

```
@dataclass(frozen=True)
class ParsedDocument:
    text: str                        # concatenated extracted text
    method: str                      # how it was parsed
    metadata: dict[str, Any]         # per-format metadata
    structured_fragments: list[Any]  # optional per-row / per-page structures
```

The `method` field is one of: `pdf_native`, `docx`, `xlsx`, `csv`, `plain`,
`ocr_required`, `unsupported`.

### 3.2 PDF — the most complicated path

PDFs route through `_parse_pdf()` using `pymupdf` (a.k.a. `fitz`). The
result depends on whether the PDF has extractable text:

- **Text PDF.** Concatenates per-page text as `[page N]\n{text}` joined by
  `\n\n`. `method="pdf_native"`. Metadata: `page_count`, `text_page_count`
  (pages with ≥1 character).
- **Image PDF (scanned).** `pymupdf` returns empty strings on every page;
  `method="ocr_required"`. Metadata includes `page_count` and zero
  `text_page_count`.

The function `is_likely_image_pdf()` decides whether to route to OCR even
when *some* text is present, using three heuristics:

1. `method == "ocr_required"` → True.
2. Average characters per page < `IMAGE_PDF_AVG_CHARS_THRESHOLD` (50) → True.
3. `text_page_count / page_count < IMAGE_PDF_TEXT_PAGE_RATIO_THRESHOLD` (0.5)
   → True. (Catches printscreens with a single text page of metadata.)

If any heuristic fires, the document is routed to the **vision path**
(Layer 3 with image blocks) rather than the text path.

### 3.3 The native-PDF vision path

`extraction/llm.py::extract_pdf_facts_with_bedrock_native()` sends the
entire PDF as a single `{"type": "document"}` Bedrock content block — no
OCR, no rasterization. This is the cheapest + highest-quality vision path
for image PDFs under the size cap.

- Soft cap: `MAX_NATIVE_PDF_BYTES = 32_000_000` (32 MB). PDFs above this
  fall back to the rasterized image-block path.
- Pages over `MP20_OCR_MAX_PAGES` are tracked in `processing_metadata.overflow`
  for advisor visibility.

The rasterized fallback splits the PDF into per-page images and sends each
as a separate Bedrock content block with a 4.5 MB per-block cap
(`MAX_IMAGE_BLOCK_BYTES`).

### 3.4 DOCX, XLSX, CSV

| Format | Library | Text representation | Metadata |
| --- | --- | --- | --- |
| DOCX | `python-docx` | Paragraphs + table rows (cells joined by `\|`) with `[table N row M]` labels | `paragraph_count`, `table_rows` |
| XLSX | `openpyxl` (read-only mode) | Per-sheet blocks `[sheet NAME]`, then per-row `[NAME!row]` with `\|`-joined cells; empty cells skipped | `sheet_count`, `sheet_names` |
| CSV | stdlib `csv.reader` | Per-row `[row N]` with `\|`-joined values | `row_count` |

XLSX also emits `structured_fragments` (per-row metadata
`{kind: "sheet_row", sheet: str, row: int}`) so Layer 3 can request specific
rows back if the prompt needs a focused view.

### 3.5 Plain text, Markdown, images

- TXT / MD: direct `path.read_text(errors="ignore")`. `method="plain"`.
- Images (PNG / JPG): returns empty text + `method="ocr_required"`. They go
  straight to the visual extraction path.
- TIFF: explicitly raises `ValueError`. Bedrock vision doesn't handle TIFF
  after rasterization attempts; advisors must convert pre-upload.

### 3.6 Classification

After parsing, `extraction/classification.py::classify_document()` decides
the doc type:

```
kyc | statement | planning | meeting_note | identity | spreadsheet |
image | generic_financial | unknown
```

The classifier uses *heuristics* on the filename + first ~12K characters of
text. It looks for signature patterns:

- KYC: presence of "Know Your Client", "regulatory risk", "objective",
  account-application headers.
- Statement: holding tables, "market value", "as of", custodian header
  patterns.
- Planning: "retirement", "goal", target-amount patterns, advisor narrative
  signals.
- Meeting note: free-form prose, dated entries, "Met with…".
- Identity: passport / DOB / SIN patterns.

If classification confidence is low (no signal fires above threshold),
routing produces `route="multi_schema_sweep"` — Layer 3 then runs a
multi-schema extraction against all the canonical schemas in one pass. The
classifier is intentionally not LLM-driven; it's heuristic so it can run
fast and deterministically before Bedrock is invoked.

### 3.7 What gets persisted in Layer 2

- `ReviewDocument.status` transitions:
  `UPLOADED → CLASSIFIED → TEXT_EXTRACTED` (text path)
  or `UPLOADED → CLASSIFIED → OCR_REQUIRED` (image path).
- `ReviewDocument.document_type` is set to the classifier output.
- `ReviewDocument.processing_metadata` accumulates: `parser_method`,
  `page_count`, `text_page_count`, `sheet_count`, `sheet_names`,
  `route` (if `multi_schema_sweep`), `parser_version`.
- `ProcessingJob.metadata.stage` updates as the worker progresses.

No `AuditEvent` is emitted for parser-only transitions; they're worker-local
state. Audit fires only at the layer boundaries (extraction outcome,
reconcile outcome, advisor action).

---

## Part 4 — Layer 3: LLM extraction (the AI core)

This is the heart of the pipeline. Layer 3 is the only layer where AI is
allowed to *interpret* document content and emit structured facts.

### 4.1 Provider routing

The system supports two LLM providers:

- **AWS Bedrock in ca-central-1** — required for any `data_origin =
  real_derived` document (real Steadyhand client data). Canadian
  data-residency requirement per the canon §11.8.3 defense-in-depth regime.
- **Anthropic-direct** — synthetic-only path. Cheaper, no
  Canadian-residency requirement; used in dev iteration. **Today, the
  Anthropic-direct path infrastructure exists (`integrations/llm/` shells)
  but is not wired.** All real extraction goes through Bedrock. The
  synthetic path uses a small heuristic extractor (`heuristic_facts()` in
  `extraction/pipeline.py`) rather than Anthropic-direct.

Routing is enforced server-side. The view that produces the worker job
captures `data_origin` from the workspace; the worker selects the LLM path
based on it.

### 4.2 Bedrock client wrapper

`extraction/llm.py` exposes:

```
@dataclass(frozen=True)
class BedrockConfig:
    access_key: str
    secret_key: str
    aws_region: str
    model: str

def _bedrock_client(config: BedrockConfig) -> anthropic.AnthropicBedrock:
    return anthropic.AnthropicBedrock(
        aws_access_key=config.access_key,
        aws_secret_key=config.secret_key,
        aws_region=config.aws_region,
    )
```

Config sources (env):

- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` — credentials.
- `AWS_REGION` — defaults to `ca-central-1`.
- `BEDROCK_MODEL` — the model ID (e.g.,
  `anthropic.claude-sonnet-4-6-20251201`).

If any of these are missing for a `real_derived` extraction, the worker
raises `BedrockExtractionError` with `failure_code = "bedrock_unconfigured"`
— fail-closed; nothing leaks to a fallback provider.

### 4.3 The tool-use protocol

Bedrock is invoked in **tool-use mode** with a JSON Schema-constrained
output. This is a critical control: the model can only emit a structured
`{"facts": [...]}` payload — it cannot produce free-form narrative that
might be persisted.

```
response = client.messages.create(
    model=config.model,
    max_tokens=_bedrock_max_tokens(),       # 16384 default
    tools=[FACT_EXTRACTION_TOOL],
    tool_choice={"type": "tool", "name": "fact_extraction"},
    messages=[{"role": "user", "content": prompt}],
)
```

The `tool_choice` clause *forces* the model to emit a tool_use block. If
the model fails to do so (e.g., token-limit exceeded mid-emission), the
response is treated as a schema mismatch and the document goes to FAILED
with a typed error code.

### 4.4 The tool schema

Defined in `extraction/prompts/base.py::FACT_EXTRACTION_TOOL`. The schema
constrains every emitted fact to:

```
{
  "field": str,                       # canonical field path
  "value": Any,                       # JSON-serializable
  "confidence": "high" | "medium" | "low",
  "derivation_method": "extracted" | "inferred" | "defaulted",
  "source_location": str,             # textual label inside the doc
  "source_page": int | null,
  "evidence_quote": str,              # ≤240-char verbatim snippet
  "asserted_at": ISO8601 | null,      # document-asserted date
}
```

Required fields: `field`, `value`, `confidence`, `derivation_method`,
`evidence_quote`.

The `derivation_method` enum is load-bearing:

- `extracted` — directly read from the doc. Default. Always preferred.
- `inferred` — derived from doc content with explicit reasoning. Allowed,
  but evidence-quote validation (§4.10) catches drift from the doc.
- `defaulted` — **banned** per canon §9.4.5. Prompts forbid it explicitly;
  if the model emits it, Phase 9 validation drops the fact.

### 4.5 `max_tokens` — the 4096 → 16384 bump

The default `max_tokens` was originally 4096. During Phase 3 hardening
(2026-05-01), a real XLSX document with many holdings tables exceeded the
budget mid-emission, producing truncated tool-use responses that registered
as `BedrockSchemaMismatchError`. The fix bumped the default to 16384,
configurable via `MP20_BEDROCK_MAX_TOKENS`.

```
DEFAULT_BEDROCK_MAX_TOKENS = 16384
```

The bump is documented in [ADR-0003](adr/0003-bedrock-ca-central-1.md) and
in the canon §11.

### 4.6 Per-document-type prompts

Each doc type gets a tailored prompt that emphasizes the fields most likely
to be present in that document type. Located in `extraction/prompts/`:

| File | Doc type | Focus |
| --- | --- | --- |
| `kyc.py` | `kyc` | Named fields, regulatory disclosures, account holders, "Know Your Client" form structure. Includes the checkbox-omission rule (don't emit a field for an unchecked checkbox). |
| `statement.py` | `statement` | Custodian holdings tables, account numbers, current values, position dates. |
| `planning.py` | `planning` | Goals, time horizons, target amounts, cash-flow projections, advisor narrative. |
| `meeting_note.py` | `meeting_note` | Narrative-grounded facts, behavioral context, temporal assertions ("Mike mentioned he wants to retire by…"). |
| `generic.py` | `unknown` / `multi_schema_sweep` | Falls back to all-schemas extraction when the classifier is uncertain. |
| `classify.py` | (classifier prompt) | Used by `classification.py` when heuristics are inconclusive. |

Every prompt is composed of three shared guardrail blocks plus a doc-type
body:

- `NO_FABRICATION_BLOCK` — canon §9.4.5 verbatim instructions.
- `CONFIDENCE_GUIDANCE_BLOCK` — when to use high / medium / low.
- `ENTITY_ALIGNMENT_BLOCK` — how to handle multi-doc entities (refer to
  prior canonical_index when possible).

### 4.7 `PROMPT_VERSION_BY_TYPE`

Every prompt has a version string:

```
PROMPT_VERSION_BY_TYPE = {
    "kyc": "kyc_review_facts_v4_tooluse_entity_aligned",
    "statement": "statement_facts_v3_tooluse",
    ...
}
```

The worker stores the prompt version in
`ReviewDocument.processing_metadata.prompt_version`. When a prompt body
changes, the version bumps; the worker can then identify which docs need
re-extraction. Re-extraction is not automatic — it's an operator decision.

### 4.8 The four typed extraction exceptions

```
class BedrockExtractionError(ValueError):
    failure_code: str = "bedrock_unknown"

class BedrockNonJsonError(BedrockExtractionError):
    failure_code = "bedrock_non_json"

class BedrockTokenLimitError(BedrockExtractionError):
    failure_code = "bedrock_token_limit"

class BedrockSchemaMismatchError(BedrockExtractionError):
    failure_code = "bedrock_schema_mismatch"
```

`BedrockNonJsonError` is retained for backwards compatibility but is no
longer raised in the tool-use path (the new contract is that any non-tool
response is a schema mismatch).

Failure-code lifecycle:

1. Raised in `extraction/llm.py`.
2. Caught by the worker (`web/api/review_processing.py`).
3. Stored in `ReviewDocument.processing_metadata.failure_code` +
   `failure_reason` (typed message, not raw exception text — see real-PII
   discipline below).
4. Rendered in the UI via i18n key `review.failure_code.<code>` (defined in
   `frontend/src/i18n/en.json`).
5. Per-code, the UI surfaces the manual-entry escape hatch if the code is
   in the "ambiguous extraction failure" set
   (`bedrock_token_limit`, `bedrock_non_json`, `bedrock_schema_mismatch`).

### 4.9 Three extraction entry points

The worker selects one of three based on `parser_method` + `is_likely_image_pdf()`:

| Function | Used for | Input | Output |
| --- | --- | --- | --- |
| `extract_text_facts_with_bedrock()` | text PDFs, DOCX, XLSX, CSV, MD, TXT | filename, doc_type, classification, text (capped), extraction_run_id, config | `list[FactCandidate]` |
| `extract_visual_facts_with_bedrock()` | OCR-required documents (image-only PDFs broken into pages, plus images) | file path, filename, doc_type, classification, extraction_run_id, max_pages, config | `(list[FactCandidate], dict[overflow_metadata])` |
| `extract_pdf_facts_with_bedrock_native()` | Native PDF vision (image PDFs under 32 MB) | file path, filename, doc_type, classification, extraction_run_id, config | `(list[FactCandidate], dict[cost_metadata])` |

All three eventually call into the same `_facts_from_tool_use_response()`
helper which parses the Bedrock response, runs Pydantic validation, and
filters facts via `_is_missing_fact_value()` (drops empty strings, nulls,
zero-length arrays).

### 4.10 Phase 9 evidence validation

Per `extraction/validation.py`, every emitted fact with
`derivation_method = "inferred"` runs through a longest-common-subsequence
(LCS) check: the `evidence_quote` must overlap with the document text by
≥`EVIDENCE_OVERLAP_THRESHOLD` (60%). If overlap is below threshold, the
fact is dropped before persistence.

This catches a subtle hallucination mode: the model emits a plausible
"inferred" fact but with a fabricated evidence quote. The overlap check
ties the quote back to text the model actually saw.

`extracted` and `defaulted` facts don't run through this validator —
`extracted` because the value should already be in the text; `defaulted`
because it's banned and should never emit (if it does, it's dropped at
emission).

### 4.11 Bedrock cost ledger

Every Bedrock call records a structural-only entry to
`docs/agent/bedrock-spend-2026-05-03.md` (append-only). The entry captures:

- Document type
- Input tokens, output tokens, cached tokens
- Cost (computed from a hardcoded pricing table for Sonnet 4.6 / Opus 4.7 /
  Opus 4.6 / Haiku 4.5)
- The `extraction_run_id` for cross-reference to the ProcessingJob

The ledger never carries client content — just numbers. Total pre-pilot
spend was $0.36 cumulative; the pilot success metrics (Part 11.5) cap at
$25/advisor/week.

### 4.12 Debug logging

`MP20_DEBUG_BEDROCK_RESPONSES=1` enables raw response dumps to
`$MP20_SECURE_DATA_ROOT/_debug/`. This is a development aid only — never
enabled in production. The dump filename pattern is
`{safe_extraction_run_id}-{stage}-{timestamp_ms}.txt`. Stages: `tool_input`
(raw tool_use input), `no_tool_use` (raw text when tool block missing),
`bad_tool_input` (non-dict input).

Real-PII discipline: debug dumps are written *only* under
`MP20_SECURE_DATA_ROOT`, never the repo, never stdout, never chat. The PII
grep guard (`scripts/check-pii-leaks.sh`) forbids `str(exc)` in
last_error / failure_reason / response bodies / audit metadata; debug-only
escape via the secure root is allowed.

### 4.13 What gets persisted in Layer 3

| Table | Row | Carries |
| --- | --- | --- |
| `ReviewDocument` | updated | status (`FACTS_EXTRACTED` or `FAILED`), processing_metadata (failure_code, prompt_version, extraction_run_id, bedrock_cost_estimate_usd, token counts), failure_reason (typed advisor copy, never raw exception text) |
| `ExtractedFact` | one per `FactCandidate` | field, value, confidence, derivation_method, source_location, source_page, evidence_quote (redacted on serialization), extraction_run_id, asserted_at, document FK, is_current=True |
| `AuditEvent` | per outcome | `review_document_processed` (success) or `extraction_failed` (with structured failure_code via `safe_audit_metadata`) |

---

## Part 5 — Layer 4: Reconciliation

Layer 4 is **pure-Python deterministic.** It takes the collection of
`ExtractedFact` rows produced by Layer 3 across all the workspace's
documents and produces:

1. A canonical entity index per fact (`canonical_index`) — which person /
   account / goal does this fact describe?
2. A list of Tier-2 merge candidates — pairs of canonicals that *might* be
   the same entity but require advisor judgment.
3. A list of field-level conflicts — fields where multiple facts disagree.

The entry point is `extraction/entity_alignment.py::align_facts()`.

### 5.1 The three-tier matcher

The matcher decides "is this fact about the same Mike Chen as that other
fact?" It operates in three tiers per [ADR-0007](adr/0007-three-tier-entity-matcher.md).

**Tier 1 — Auto-merge** (high-confidence; silent):

- People: `name + DOB → 100` OR
  `name + last_name + last-4 of account_number → ≥115`.
- Accounts: `account_number_hash exact (+100)` OR
  `(type, institution) both match AND single candidate (+80)` OR
  `type + current_value within 5% → 80`.
- Goals: `normalize_key(name) → 80`.

Thresholds (locked Round 13 #2):

```
PEOPLE_THRESHOLD = 100
ACCOUNTS_THRESHOLD = 80
GOALS_THRESHOLD = 80
```

Tier-1 matches are merged silently with no advisor surface.

**Tier 2 — Merge candidate** (medium-confidence; advisor adjudicates):

Bands (locked Round 18 #1, shipped 2026-05-05):

```
PEOPLE_TIER2_FLOOR = 60,  CEILING = 99
ACCOUNTS_TIER2_FLOOR = 50, CEILING = 79
GOALS_TIER2_FLOOR = 50,    CEILING = 79
```

Emitted when the score lands in band *and* no contradicting identity field
exists on either canonical.

The **contradicting-field rule** is the key invariant: if canonical A has
`DOB = X` and canonical B has `DOB = Y` where `X ≠ Y`, they are *never* a
Tier-2 candidate — they're clearly different people. Same for `last_name`,
`account_number_hash` (accounts), `institution` (accounts), and target
amount (goals: same horizon but >5% delta in target_amount → contradicting).

This is why the matcher is safe under sparse real-PII data: a single-field
name match becomes a Tier-2 candidate (advisor decides); but a name match
where DOBs differ becomes Tier-3 (separate canonicals automatically). The
father+son same-surname false-merge stays prevented.

**Tier 3 — New canonical** (low-confidence or contradicted):

Below all bands OR at least one contradicting identity field present. A
new canonical entity is created.

### 5.2 The matcher algorithm

`align_facts()` runs in three phases:

**Phase 1: Feature extraction.** Per `(document, prefix, local_index)`
triple, accumulate a feature dict:

- People: `{name_tokens: set[str], last_name: str|None, dob: str|None,
  account_last4: set[str]}`
- Accounts: `{account_number_hash: str|None, account_type: str|None,
  institution: str|None, current_value: float|None}`
- Goals: `{name_key: str|None, target_amount: float|None,
  time_horizon_years: int|None}`

Account numbers are hashed at this stage: `SHA-256(digits).hexdigest()[:16]`
(16 hex chars). Last-4 digits are extracted (`digits[-4:]`) for cross-doc
people matching but are *not persisted* — they're side-channel features.

**Phase 2: Greedy clustering (Tier-1).** Process triples in deterministic
order: `sorted(key=(str(document_key), prefix_rank, local_index))`. For
each triple:

1. Compute score against every existing canonical for the same prefix.
2. Find the highest score ≥ Tier-1 threshold.
3. If found → merge (union `contributing_docs`, fold in new feature keys
   without overwriting existing values).
4. Else → allocate a new canonical (next available `canonical_index`).

**Tie-breaking** (locked):

1. Highest score wins.
2. Equal score → canonical with more `contributing_docs` wins.
3. Still tied → lowest `canonical_index` wins (deterministic).

This determinism is critical: the matcher must produce the same alignment
for the same input on every run. Hypothesis property tests in
`extraction/tests/test_entity_alignment_properties.py` enforce this.

**Phase 3: Tier-2 surfacing.** After Tier-1 clustering, scan all
same-prefix canonical pairs `(a, b)` where `a.canonical_index <
b.canonical_index`:

1. Compute an **ungated** score (no single-field rejection).
2. Check for contradicting identity fields.
3. If score ∈ band AND no contradictions → emit a `MergeCandidate`.

The result is sorted by `(-score, canonical_a_index, canonical_b_index)`
for stable display ranking.

### 5.3 The `MergeCandidate` dataclass

```
@dataclass(frozen=True)
class MergeCandidate:
    prefix: Literal["people", "accounts", "goals"]
    canonical_a_index: int
    canonical_b_index: int
    score: int
    matched_fields: tuple[str, ...]    # which signals matched
    contradicting_fields: tuple[str, ...]  # always () for emitted candidates
    confidence: Literal["medium"] = "medium"
```

Phase B1 (shipped 2026-05-05) added the backend endpoints
`MergeCandidateResolveView` and `MergeCandidateBulkKeepSeparateView` for
advisor adjudication. **Phase B2** (the frontend `MergeCandidateGroup`
component in `ConflictPanel`) is queued but not shipped at time of
writing — workspaces created today store `merge_candidates` in
`reviewed_state` but show no UI for resolution.

### 5.4 Source-priority hierarchy

Once entity alignment groups facts by canonical entity, conflicts within a
single field (e.g., "what is Mike Chen's DOB?") get resolved per the
source-priority hierarchy in `extraction/reconciliation.py`.

The hierarchy is **per-section** (different sections weight sources
differently). The authority matrix:

```
authority_matrix = {
    "household": {"crm_export": 5, "kyc": 10, "identity": 12, "intake": 15, ...},
    "people":    {"crm_export": 5, "kyc": 8,  "identity": 10, "intake": 18, ...},
    "accounts":  {"statement": 5,  "crm_export": 8, "spreadsheet": 10, ...},
    "goals":     {"planning": 5,   "meeting_note": 8, ...},
    ...
}
```

Lower numbers = higher authority. The function `source_authority()` looks
up the priority; `current_facts_by_field()` sorts conflicting facts by
`(source_authority, confidence_priority, -asserted_date)` and picks the
first (highest authority).

**Cross-class vs same-class disagreements:**

- **Cross-class disagreement** (KYC says X, planning note says Y): the
  source-priority hierarchy resolves silently. KYC wins; no advisor
  surface. This is canon §11.4 — the system is allowed to make this
  decision because the hierarchy is explicit.
- **Same-class disagreement** (two notes disagree on a value): surfaces
  to the advisor as a conflict card in the ConflictPanel. The advisor must
  pick a value with a written rationale + an evidence-acknowledgement
  checkbox.

Advisor `FactOverride` rows trump everything — they're written by a human
with full context.

### 5.5 Conflict surfacing

After source-priority resolution, `conflicts_for_facts()` produces a list
of `ReviewConflict` rows for the same-class disagreements:

```
{
  "field": "people[0].marital_status",
  "label": "Marital status",
  "section": "people",
  "values": ["married", "common_law"],
  "count": 2,
  "fact_ids": [12345, 12350],
  "resolved": false,
  "required": true,                 # is this field needed for engine_ready?
  "same_authority": true,           # both facts from same source class
  "source_types": ["note", "note"],
  "candidates": [
    {
      "fact_id": 12345,
      "value": "married",
      "source": "note",
      "derivation_method": "extracted",
      "confidence": "medium",
      "source_page": 2,
      "evidence_quote": "<redacted snippet>"
    },
    ...
  ]
}
```

The frontend reads this shape via `useReviewedState(workspaceId)` and
renders it in the ConflictPanel.

### 5.6 Per-field normalization

Before conflict detection, fact values run through
`extraction/normalization.py::normalize_fact_value(field, value)`:

- `*_value`, `*_balance`, `target_amount`: parsed as decimal, emitted as int
  if whole or float.
- `*_score`, `risk_score`: qualitative-to-numeric map (cautious→1,
  conservative→2, balanced→3, growth→4, very_high→5); or clamp 1–10 → 1–5.
- `*_horizon`, `age`: integer extraction via regex.
- Date strings (M/D/YYYY format): normalize to ISO YYYY-MM-DD.
- Boolean-like fields: yes/true/confirmed/missing/na → True.

Normalization happens before conflict detection so "5,000" and "5000" don't
surface as a conflict.

### 5.7 What gets persisted in Layer 4

Layer 4 is *purely projection over already-persisted facts*. It writes very
little:

- `EntityAlignment` is computed on every read of `reviewed_state` from the
  workspace; it's a derived value, not a persisted table.
- `ExtractedFact.canonical_index` *is* persisted — set when reconcile
  completes, used to skip re-alignment for unchanged facts.
- `ReviewWorkspace.reviewed_state` is a JSON column carrying the full
  projection including alignment results, conflicts, and merge candidates.
- `AuditEvent`: `entities_reconciled` (auto, on Layer 4 completion);
  `entities_reconciled_via_button` (advisor-initiated re-reconcile via
  Phase P2.5).

---

## Part 6 — Layer 5: Review

Layer 5 is the advisor surface. The reviewed extraction facts become a
single canonical JSON state (`reviewed_state`), and the advisor adjudicates
conflicts, resolves missing fields, approves sections, and (when all gates
pass) commits.

### 6.1 The `reviewed_state` JSON contract

This is the canonical shape the frontend reads. Both `ReviewScreen` and
`StatePeekPanel` consume it. Full annotated shape:

```jsonc
{
  "schema_version": "reviewed_client_state.v1",

  "household": {
    "display_name": "Mike & Sandra Chen",
    "household_type": "couple",           // single | couple
    "household_risk_score": 3,            // canon 1-5
    "notes": ""
  },

  "people": [
    {
      "id": "person_mike_chen",           // workspace-canonical (semantic_entity_key)
      "name": "Mike Chen",
      "dob": "1964-02-12",
      "age": 62,
      "marital_status": "married",
      "employment": { "status": "retired", "occupation": "engineer" },
      "investment_knowledge": "medium",   // low | medium | high
      "longevity": { "assumption_age": 90 }
    }
  ],

  "accounts": [
    {
      "id": "acct_mike_rrsp",
      "type": "RRSP",                     // canonical case (post-normalization)
      "current_value": 620000.0,
      "holdings": [
        {
          "sleeve_id": "SH-Eq",           // building-block fund id
          "sleeve_name": "Steadyhand Equity",
          "weight": 0.60,
          "market_value": 372000.0
        }
      ],
      "missing_holdings_confirmed": false,
      "is_held_at_purpose": true,
      "cash_state": "invested",           // invested | onboarding_cash | pending
      "regulatory_objective": "growth_and_income",
      "regulatory_time_horizon": "3-10y"
    }
  ],

  "goals": [
    {
      "id": "goal_retirement_income",
      "name": "Retirement income",
      "target_amount": 1500000.0,
      "target_date": "2030-06-01",
      "time_horizon_years": 4,
      "necessity_score": 5,               // need (5) → wish (1)
      "goal_risk_score": 3,               // canon 1-5; system OR override-resolved
      "notes": ""
    }
  ],

  "goal_account_links": [
    {
      "goal_id": "goal_retirement_income",
      "account_id": "acct_mike_rrsp",
      "allocated_amount": 620000.0,       // OR allocated_pct (mutually exclusive)
      "allocated_pct": null,
      "advisor_confirmation_required": false
    }
  ],

  "external_holdings": [],

  "risk": {
    "household_score": 3                  // canon 1-5
  },

  "conflicts": [
    {
      "field": "people[0].marital_status",
      "resolved": false,
      "resolution": null,
      "deferred": false,
      "re_surfaced_at": null,
      "candidates": [
        {
          "fact_id": 12345,
          "value": "married",
          "source": "note",
          "derivation_method": "extracted",
          "confidence": "medium",
          "source_page": 2,
          "evidence_quote": "<redacted snippet>"
        }
      ]
    }
  ],

  "merge_candidates": [                   // Phase B1 backend; B2 UI pending
    {
      "key": "people:0:2",                // stable key for resolve endpoint
      "prefix": "people",
      "canonical_a_index": 0,
      "canonical_b_index": 2,
      "score": 75,
      "matched_fields": ["name_token"],
      "confidence": "medium",
      "canonical_a_features": {
        "display_name": "Mike Chen",
        "contributing_doc_count": 3,
        "available_fields": ["display_name", "marital_status"]
      },
      "canonical_b_features": {
        "display_name": "Mike Chen",
        "contributing_doc_count": 1,
        "available_fields": ["display_name"]
      }
    }
  ],

  "merge_decisions": {                    // append-only; applied on re-reconcile
    "people:0:2": "merge"                 // merge | keep_separate | defer
  },

  "readiness": {
    "engine_ready": true,
    "construction_ready": true,
    "kyc_compliance_ready": true,
    "missing": [
      {
        "section": "people",
        "label": "Sandra's date of birth",
        "field_path": "people[1].dob"     // deep-link target for AddBlockerInlineButton
      }
    ],
    "construction_missing": []
  },

  "source_summary": [
    {
      "document_id": 87,
      "filename": "MikeChen_KYC.pdf",
      "document_type": "kyc",
      "status": "reconciled",
      "failure_reason": ""
    }
  ],

  "field_sources": {
    "household.display_name": [
      {
        "fact_id": 12000,
        "field": "household.display_name",
        "value": "Mike & Sandra Chen",
        "confidence": "high",
        "derivation_method": "extracted",
        "source_location": "Account Holders / Household Name",
        "source_page": 1,
        "evidence_quote": "<redacted snippet>"
      }
    ]
  }
}
```

The frontend never hard-codes this shape — it imports the type from
`frontend/src/lib/review.ts`, which mirrors the DRF serializer. The OpenAPI
codegen gate (`scripts/check-openapi-codegen.sh`) catches any drift.

### 6.2 `reviewed_state_from_workspace(workspace)`

`web/api/review_state.py:135` is the canonical projection. Three phases:

1. **Fact collection + alignment** (lines 135–138):

   ```python
   facts = list(workspace.extracted_facts.select_related("document"))
   alignment = compute_entity_alignment(facts)
   current_facts = _current_facts(workspace, alignment=alignment, facts=facts)
   ```

   `_current_facts` calls the Layer 4 reconciler
   (`current_facts_by_field()`) to pick the highest-authority fact per
   field after alignment.

2. **Override application** (`_apply_fact_overrides`, lines 1008–1015):
   Fetches the latest `FactOverride` per field (order by `-created_at`,
   first wins). Each override is wrapped as a fake `ExtractedFact`
   (`_FactOverrideAsFact`) so the downstream projection logic stays
   agnostic. **Overrides always win** — they shadow any competing
   extracted fact (canon §11.4).

3. **State projection** (lines 139–197): For each top-level key, calls
   `_indexed_items()` which regex-matches field paths like `people[0].name`,
   groups by index, and returns a list of dicts keyed by canonical field
   names.

4. **Late enrichment** (lines 198–217): adds `source_summary`,
   `field_sources`, `conflicts`, `merge_candidates`, `readiness`.

### 6.3 The readiness contract

`readiness_for_state(state)` computes three booleans and two missing lists.

| Section | Engine-ready blocker if… |
| --- | --- |
| household | No display_name OR household_type not in {single, couple} |
| people | 0 members OR no member has dob or age |
| accounts | 0 accounts OR all accounts have current_value ≤ 0 OR 0 accounts have holdings (or missing_holdings_confirmed=True) |
| goals | 0 goals OR 0 goals have target_date or time_horizon_years |
| goal_account_mapping | Accounts + goals exist but 0 links; OR any link has neither allocated_amount nor allocated_pct; OR a Purpose account is unassigned or partially assigned |
| risk | No household_risk_score |

**Construction-ready** is the stricter gate on top:

- Household risk in 1–5
- ≤ 2 household members
- Every account type in `ALLOWED_ENGINE_ACCOUNT_TYPES`
- Every goal risk score in 1–5

`ALLOWED_ENGINE_ACCOUNT_TYPES` is the canonical mixed-case set: `RRSP`,
`TFSA`, `RESP`, `RDSP`, `FHSA`, `Non-Registered`, `LIRA`, `RRIF`,
`Corporate`. This list lives in `web/api/review_state.py:61`.

**KYC-compliance-ready** is the weakest gate: `bool(people and accounts)`.
Used for read-only views.

### 6.4 The six required sections

```python
ENGINE_REQUIRED_SECTIONS = [
    "household",
    "people",
    "accounts",
    "goals",
    "goal_account_mapping",
    "risk",
]
```

Every workspace creates one `SectionApproval` row per section at intake
(status `not_ready_for_recommendation`). The advisor approves each via
`POST /api/review-workspaces/<id>/approve-section/`. Commit refuses to
proceed unless every required section has status `approved` or
`approved_with_unknowns`.

Approval statuses:

```
not_ready_for_recommendation    # initial; default for new sections
needs_attention                 # something needs advisor action
approved_with_unknowns          # advisor approved despite missing optional fields
approved                        # ready
```

The frontend never hard-codes the section list — it reads
`workspace.required_sections` from the payload. This is one of the cleanest
examples of single-source-of-truth in the codebase.

### 6.5 Structured readiness blockers (Plan v20 §A1.27)

The bare `readiness.missing[]` list is what the LegacyMissingPanel renders.
A parallel structured blocker list is also emitted for `BlockerBanner`:

```
PortfolioGenerationBlocker = {
  "code": str,                # e.g., "no_holdings", "no_risk_profile"
  "ui_action": str,           # e.g., "open_assign_account_modal"
  "account_label": str | None,
  "field_path": str | None,   # deep-link target
  "severity": "high" | "medium",
  "advisor_message": str,
}
```

There are 12 codes and 5 ui_actions in current code; each maps to a
specific frontend CTA. This is what lets the frontend render
"per-blocker fix buttons" instead of a generic "incomplete" warning.

### 6.6 The advisor adjudication surfaces

| Frontend surface | Backend endpoint | Audit event |
| --- | --- | --- |
| ConflictPanel — resolve | `POST /api/review-workspaces/<id>/conflicts/resolve/` | `review_conflict_resolved` |
| ConflictPanel — bulk resolve | `POST .../conflicts/bulk-resolve/` | `review_conflict_resolved` ×N |
| ConflictPanel — defer | `POST .../conflicts/defer/` | `review_conflict_deferred` |
| MissingPanel inline / ResolveAllMissingWizard | `POST .../facts/override/` (is_added=true) | `review_fact_override_applied` |
| DocDetailPanel — fact edit | same endpoint (is_added=false) | same |
| MergeCandidate (Phase B2 pending) | `POST .../merge-candidates/<key>/resolve/` | `entity_merge_candidate_resolved` |
| SectionApprovalPanel | `POST .../approve-section/` | `review_section_approved` |
| Commit | `POST .../commit/` | `review_state_committed` |
| Uncommit (soft-undo) | `POST .../uncommit/` | `review_workspace_uncommitted` |

Each endpoint:

1. Acquires `select_for_update()` on the workspace row.
2. Mutates `reviewed_state` (or creates `FactOverride` / `SectionApproval`
   rows).
3. Re-runs `readiness_for_state` and writes the updated state back.
4. Emits the audit event (counts + UUIDs only via `safe_audit_metadata`).
5. Fires the auto-trigger (post-commit only).
6. Returns the updated state to the frontend, which invalidates the
   workspace cache.

### 6.7 Defer affordance + re-surfacing

The `ConflictPanel` defer flow is Phase 5b.13. Advisor clicks "Defer",
provides a rationale, and the conflict gets `deferred=true`,
`deferred_at`, `deferred_by`, `deferred_rationale` set.

If a subsequent re-reconcile produces the same conflict (e.g., new
document uploaded), the conflict gets `re_surfaced_at` set and the UI
shows a "Re-surfaced" badge with the message "This conflict reappeared
after additional document upload."

The defer mechanism never blocks commit; it's an advisor-visibility
control.

### 6.8 Manual-entry escape hatch

If extraction fails irrecoverably (e.g., `bedrock_token_limit` after
retry), the advisor can mark the document as `manual_entry` via
`POST /api/review-workspaces/<id>/documents/<doc_id>/manual-entry/`. The
document status becomes `MANUAL_ENTRY`; the worker no longer reprocesses
it. The advisor then uses `FactOverride` (via DocDetailPanel
`AddFactSection`) to add facts manually from the document content.

This is the canon-compliant gap path: extraction failed, so the AI did
not invent; the advisor enters facts explicitly with full audit trail.

---

## Part 7 — The commit boundary

`commit_reviewed_state(workspace, user, household=None)` is the most
important single function in the pipeline. It's the seam between
extraction state (mutable, advisor-editable) and committed state
(append-only, engine-feedable).

### 7.1 The commit sequence

```python
def commit_reviewed_state(workspace, *, user, household=None):
    # 1. Idempotency gate
    if workspace.status == COMMITTED:
        if not workspace.linked_household:
            raise ValueError("...no linked household")
        if household and household.pk != workspace.linked_household_id:
            raise ValueError("...already committed to another household")
        return workspace.linked_household

    # 2. Compute readiness
    state = workspace.reviewed_state or reviewed_state_from_workspace(workspace)
    readiness = readiness_for_state(state)
    if not readiness.engine_ready:
        raise ValueError("Reviewed state is not engine-ready.")
    if not readiness.construction_ready:
        raise ValueError("...not construction-ready.")
    if not required_sections_approved(workspace):
        raise ValueError("Required review sections are not approved.")

    # 3. Select target household
    if household is None and workspace.source_household_id is not None:
        # Re-open path (Phase P2.1): UPSERT onto existing household
        household = workspace.source_household
    household = household or _create_household_from_state(workspace, state, user=user)

    # 4. Merge state into household
    _merge_household_state(household, state)

    # 5. Re-validate construction readiness post-merge
    if blocker := portfolio_generation_blocker_for_household(household):
        raise ValueError(f"...not construction-ready: {blocker}")

    # 6. Create state version + mark as committed
    version = create_state_version(workspace, user=user, state=state)
    version.is_committed = True
    version.committed_household = household
    version.save(update_fields=["is_committed", "committed_household"])

    # 7. Update workspace status
    workspace.linked_household = household
    workspace.status = COMMITTED
    workspace.match_candidates = []
    workspace.save(update_fields=[...])

    # 8. Emit audit event
    record_event(
        action="review_state_committed",
        entity_type="review_workspace",
        entity_id=workspace.external_id,
        actor=user.get_username() if user.is_authenticated else "system",
        metadata={"household_id": household.external_id, "version": version.version}
    )
    return household
```

The function runs **outside** `transaction.atomic()` at the call site
(`ReviewWorkspaceCommitView.post()`). The view wraps the whole thing
including the auto-trigger in `transaction.atomic`, so any failure rolls
back the household creation + merge.

### 7.2 The two write paths

**Fresh-create path** (`_create_household_from_state`): the workspace has no
`source_household_id`. A new `Household` row is created with
`external_id = f"review_{workspace.external_id}"` and seeded fields from
the state. Members / accounts / goals / links are created from scratch.

**Re-open / re-edit path** (`_merge_household_state`): the workspace has
`source_household_id != None` (Phase P2.1 re-open). The existing
`Household` row's `external_id` is preserved; members / accounts / goals
are cascade-deleted and recreated. **The household identity is preserved
across edit cycles.**

### 7.3 `_merge_household_state` — the critical mutation point

This function lives at `web/api/review_state.py:1505`. Read it in full
before making any change that touches the commit path; the invariants are
subtle.

**Step 1: Household record update** (lines 1507–1514):

- Preserves `external_id` (critical for re-open).
- Updates `display_name`, `household_type`, `household_risk_score`.
- Saves with `update_fields=[...]` (no unrelated mutations).

**Step 2: Cascade deletes** (lines 1516–1518):

```python
household.members.all().delete()
household.accounts.all().delete()
household.goals.all().delete()
```

This is **complete flush** of related entities — no partial merge.
`GoalAccountLink` rows cascade-delete via FK constraints. `Holding` rows
likewise.

**Why cascade-delete instead of upsert?** Because the alternative is
N-way diff logic (which fields changed on which person?), which is much
more error-prone for a once-per-commit operation. The trade-off: external
IDs for entities (`Person.external_id`, `Account.external_id`,
`Goal.external_id`) are NOT preserved across re-merges — they get fresh
fallback IDs like `{household_id}_account_{index}`. Anything downstream
that pins to those IDs across commits will break. (Today, nothing pins
to them across commits.)

**Step 3: Account-type case normalization** (line 1541):

```python
account_type=_normalize_account_type(account_state.get("type")) or "Non-Registered",
```

This is the **single point** in the entire pipeline where lowercase /
snake_case extracted account types ("rrsp", "non_registered") become
canonical mixed-case ("RRSP", "Non-Registered"). The mapping is in
`ACCOUNT_TYPE_NORMALIZATION` (lines 82–94):

```
"rrsp" → "RRSP", "tfsa" → "TFSA", "rrif" → "RRIF",
"lira" → "LIRA", "lrif" → "LRIF", "resp" → "RESP",
"rdsp" → "RDSP", "fhsa" → "FHSA",
"non_registered" → "Non-Registered",
"non-registered" → "Non-Registered",
"corporate" → "Corporate"
```

Unknown inputs **pass through unchanged**. This is deliberate: the
downstream `ALLOWED_ENGINE_ACCOUNT_TYPES` validation in
`portfolio_generation_blocker_for_household` will flag them as advisor
blockers (`unsupported_engine_account_type`). The normalizer fixes the
known case-drift cases; it doesn't try to interpret arbitrary free-text
inputs.

**Step 4: People creation** (lines 1521–1531):

- External ID derives from `person_state.get("id")` (the semantic key
  from alignment) or falls back to `f"{household.external_id}_person_{index}"`.
- DOB resolved via `_dob()`: if `dob` present, parse ISO; else use `age`
  to back-compute (defaults 60 if missing). This produces a Date object
  the engine can use; the original "we only have age" detail is captured
  in the audit metadata, not lost.

**Step 5: Account creation** (lines 1534–1560):

- Creates the Account row, then nested Holding rows.
- Holding weights are clamped: `weight if weight <= 1 else Decimal("0")`
  — silently clips percentages > 1.0 to 0. (This is defensive against
  bad extraction; it should never fire on a valid statement.)

**Step 6: Goal creation** (lines 1563–1581):

- External ID derived similarly.
- Target date resolved via `_target_date()`: if ISO present, parse; else
  compute from `time_horizon_years` (defaults 5yr).
- `goal_risk_score` defaults to 3 if missing.

**Step 7: Goal-account link creation** (lines 1583–1598):

- Looks up goal + account by their state IDs.
- Skips links where either is missing (defensive — shouldn't happen
  post-validation).
- Sets `allocated_amount` or `allocated_pct` (mutually exclusive; both
  can be null for validation-deferred links).

### 7.4 Why no `select_for_update` on reads

The commit boundary doesn't acquire row locks on the entities it
deletes/creates. The `select_for_update` happens on the *workspace* row at
the view layer; the entities are derived from the state in the workspace
JSON. No concurrent commit on the same workspace can race because the
workspace lock serializes them.

### 7.5 The auto-trigger fires next

After `commit_reviewed_state` returns, the view fires the auto-trigger:

```python
_trigger_and_audit(committed_household, request.user, source="review_commit")
```

This is Part 8.

---

## Part 8 — The engine handoff

### 8.1 The five typed engine exceptions

Defined in `web/api/views.py:94-113`:

| Exception | When raised | Advisor copy |
| --- | --- | --- |
| `EngineKillSwitchBlocked` | `MP20_ENGINE_ENABLED=False` | "Recommendation generation is temporarily disabled. Engineering has been notified." |
| `NoActiveCMASnapshot` | No `CMASnapshot.status=ACTIVE` row | "An analyst needs to publish the latest CMA before recommendations can be generated." |
| `InvalidCMAUniverse` | `_validate_cma_snapshot()` failed (a held fund ID isn't in the universe; correlation matrix degenerate; etc.) | "Recommendation can't be generated. Engineering has been notified." |
| `ReviewedStateNotConstructionReady` | `portfolio_generation_blocker_for_household()` returned blockers | rendered from the structured `failure_code` (e.g., `no_holdings`, `no_risk_profile`) |
| `MissingProvenance` | Real-derived household lacks Bedrock extraction provenance hashes | "Recommendation can't be generated. Engineering has been notified." |

Any other `ValueError` raised by the engine is classified by
`_map_engine_value_error(exc)` (lines 115–130) using pattern matching on
the message text:

```python
msg = str(exc).lower()
if "active cma" in msg or "no cma" in msg:
    return NoActiveCMASnapshot(str(exc))
if "kill switch" in msg or "engine_enabled" in msg:
    return EngineKillSwitchBlocked(str(exc))
if "construction" in msg or "engine_ready" in msg or "blocker" in msg:
    return ReviewedStateNotConstructionReady(str(exc))
if "provenance" in msg:
    return MissingProvenance(str(exc))
return InvalidCMAUniverse(str(exc))  # catch-all
```

Any non-`ValueError` exception propagates up as "unexpected" and audits as
`portfolio_generation_post_<source>_failed`.

### 8.2 `_trigger_portfolio_generation` — the synchronous engine call

`web/api/views.py:679`. The function:

```python
def _trigger_portfolio_generation(
    household: models.Household,
    user,
    *,
    source: str,
) -> models.PortfolioRun:
```

Returns a `PortfolioRun` row. Runs synchronously, inline, inside
`transaction.atomic` with savepoints (locked decision #81).

**Source values** (line 705-708 docstring — authoritative):

```
"manual"            # explicit Generate / Regenerate CTA
"review_commit"     # post-commit auto-trigger
"wizard_commit"     # post-wizard auto-trigger
"override"          # goal-risk override
"realignment"       # realignment apply
"conflict_resolve"  # conflict resolution
"defer_conflict"    # conflict deferral
"fact_override"     # fact override
"section_approve"   # section approval
"goal_assignment"   # account-to-goals assignment (P13)
"synthetic_load"    # dev path
```

**Sequence:**

1. **Kill-switch check** (lines 711-712): if `MP20_ENGINE_ENABLED=False`,
   raise `EngineKillSwitchBlocked`.
2. **CMA snapshot fetch** (lines 714-720): `CMASnapshot.objects.filter(
   status=ACTIVE).first()`. If None, raise `NoActiveCMASnapshot`.
3. **CMA validation** (lines 722-725): `_validate_cma_snapshot` checks fund
   universe, correlation matrix shape, etc. Raises `InvalidCMAUniverse` on
   failure.
4. **Household readiness check** (lines 727-729):
   `portfolio_generation_blocker_for_household(household)`. Non-empty list
   → raise `ReviewedStateNotConstructionReady`.
5. **Input hashing** (lines 732-740, OUTSIDE atomic — reads only):
   - `input_snapshot = committed_construction_snapshot(household)` →
     `input_hash`
   - `cma_hash = _cma_input_hash(cma_snapshot)`
   - `reviewed_state_hash`, `approval_snapshot_hash`,
     `provenance_warnings = _portfolio_provenance_hashes(household)`.
     Raises wrap as `MissingProvenance`.
6. **Reusability check** (lines 761-770, also OUTSIDE atomic): if a
   PortfolioRun with matching `run_signature` exists with status
   `current`, return it (emit `portfolio_run_reused` audit, skip the
   engine call).
7. **Write-atomic block** (lines 772-853):
   - If reusable, emit REUSED event, return cached run.
   - Else, call `engine.optimize(to_engine_household(household),
     to_engine_cma(cma_snapshot))`.
   - Validate output manifest.
   - Create fresh `PortfolioRun` row + `PortfolioRunLinkRecommendation`
     rows.
   - Emit `portfolio_run_generated` audit.

### 8.3 `_trigger_and_audit` — wrap with failure audit

`web/api/views.py:937`. Wraps `_trigger_portfolio_generation` and emits
audit on any failure:

```python
def _trigger_and_audit(household, user, *, source) -> PortfolioRun | None:
    actor = _actor_for_user(user)
    try:
        return _trigger_portfolio_generation(household, user, source=source)
    except (EngineKillSwitchBlocked, NoActiveCMASnapshot, InvalidCMAUniverse,
            ReviewedStateNotConstructionReady, MissingProvenance) as exc:
        # TYPED skip — emit skipped_post_<source> audit
        record_event(
            action=f"portfolio_generation_skipped_post_{source}",
            entity_type="household",
            entity_id=household.external_id,
            actor=actor,
            metadata=safe_audit_metadata(
                exc,
                source=source,
                household_id=household.external_id,
                reason_code=type(exc).__name__,
            ),
        )
        return None
    except Exception as exc:  # Unexpected
        record_event(
            action=f"portfolio_generation_post_{source}_failed",
            entity_type="household",
            entity_id=household.external_id,
            actor=actor,
            metadata=safe_audit_metadata(exc, source=source,
                                         household_id=household.external_id),
        )
        return None
```

**Critical properties:**

- **Never re-raises.** The commit / wizard / override / realignment
  always returns 200; engine failure is captured as audit + a
  `latest_portfolio_failure` field on the household serializer.
- **Typed exceptions audit as `_skipped_`** — the advisor sees a
  "Recommendation generation paused" message (rendered from
  `friendly_message_for_code`), no toast or banner alert.
- **Unexpected exceptions audit as `_failed_`** — the advisor sees a
  toast + inline banner via `latest_portfolio_failure`.

### 8.4 `_trigger_and_audit_for_workspace` — workspace-scoped variant

`web/api/views.py:996`. Used for endpoints that mutate a workspace before
commit (conflict resolve, defer, fact override, section approve). If the
workspace has `linked_household_id is None` (pre-commit case), the
function silently skips and emits a `skipped_no_household` audit. Else, it
delegates to `_trigger_and_audit`.

This is per locked decision #27 — the auto-trigger gates on
`linked_household_id` to handle the pre-commit case where the workspace
hasn't yet produced a household.

### 8.5 The engine adapter

`web/api/engine_adapter.py:22-42` exposes `to_engine_household(household)`.
This is the **only** place Django models become `engine.schemas` Pydantic
models. Key field translations:

- Person.investment_knowledge → engine `Literal["low", "medium", "high"]`
  (via `_normalize_lowercase_enum`).
- Account regulatory enums (`regulatory_objective`,
  `regulatory_time_horizon`, `regulatory_risk_rating`) → canonical
  underscored forms via `_normalize_regulatory_enum`. Unknown non-empty
  inputs raise `ValueError` so advisor diagnoses; empty inputs pass
  through (Pydantic surfaces required-field error).
- Goal.goal_risk_score → uses `effective_goal_risk_score(goal)` (next
  section).
- Account.cash_state → engine `Literal["invested", "onboarding_cash",
  "pending_investment"]`.
- Account.holdings → engine `list[Holding]` with fund_id canonized via
  the 4-naming-convention normalizer.

### 8.6 `effective_goal_risk_score` — locked decision #100

`engine_adapter.py:374-399`. This helper resolves the "true" goal risk
score:

```python
def effective_goal_risk_score(goal: models.Goal) -> int | None:
    """Latest GoalRiskOverride.score_1_5 if one exists, else
    Goal.goal_risk_score. Single source of truth for what the engine
    optimizes against — used by both `_goal_to_engine` (engine input)
    and `committed_construction_snapshot` (input_hash computation)
    so REUSED-path detection and engine output stay consistent.
    """
    latest = goal.risk_overrides.order_by("-created_at", "-id").first()
    if latest is None:
        return goal.goal_risk_score
    return latest.score_1_5
```

**Why this matters:** an earlier code path read `goal.goal_risk_score`
directly in `_goal_to_engine` and `committed_construction_snapshot`,
bypassing overrides entirely. Result: advisor saved an override, the
audit row + DB row were correct, but the engine input never saw the
override. The `input_hash` matched the no-override seeded run, the REUSED
path returned the seed, and the override mechanism became audit-only
theatre.

The bug was surfaced in real-Chrome smoke on 2026-05-04 (locked
decision #100). The fix consolidates resolution to a single helper used
by both read sites. Any future code path that reads `goal.goal_risk_score`
directly to feed the engine breaks the override.

### 8.7 `committed_construction_snapshot` — the input-hash base

`engine_adapter.py:260-338`. Produces a deterministic dict used to compute
`input_hash`. The dict carries every field the engine depends on:
household, members, accounts (with holdings, cash_state,
is_held_at_purpose), goals (with `effective_goal_risk_score`),
goal_account_links, external_holdings.

The `input_hash` is the SHA-256 of `json.dumps(snapshot, sort_keys=True)`.
Two runs with the same input_hash + cma_hash + reviewed_state_hash +
approval_snapshot_hash are considered identical; the second one returns
the cached PortfolioRun (REUSED) instead of re-running the engine.

This is what makes the auto-trigger cheap on no-op commits: if the
advisor approves a section that doesn't change any engine-relevant data,
the hash matches and the engine doesn't re-run.

### 8.8 PortfolioRun + PortfolioRunEvent

A successful `engine.optimize()` produces:

- One `PortfolioRun` row: input_snapshot, output (engine_output.link_first.v2
  shape), input_hash, output_hash, cma_hash, reviewed_state_hash,
  approval_snapshot_hash, run_signature, engine_version,
  advisor_summary, technical_trace, status (current).
- One `PortfolioRunLinkRecommendation` row per goal-account link.
- One `PortfolioRunEvent` row: action=`portfolio_run_generated`,
  metadata including source ("review_commit" etc.), household_id,
  run_signature.

Both `PortfolioRun` and `PortfolioRunEvent` are append-only (the model's
`save()` method raises if pk exists). Future state changes (CMA
invalidation, advisor decline, hash mismatch detection) create new
`PortfolioRunEvent` rows without modifying the run.

The household serializer reads
`household.portfolio_runs.filter(status=CURRENT).order_by('-created_at').first()`
to surface the latest run as `latest_portfolio_run`. The frontend
`RecommendationBanner` renders it.

---

## Part 9 — The Postgres-backed worker queue

The worker is a separate Docker service (or a long-running management
command) that processes `ProcessingJob` rows. It's the engine of the
extraction pipeline.

### 9.1 The worker entry point

`web/api/management/commands/process_review_queue.py`. Run via:

```bash
DATABASE_URL=postgres://... uv run python web/manage.py process_review_queue
```

The Docker compose stack runs one worker container; you can run more for
parallelism but the typical pilot load (3–5 advisors × ~12 docs each)
fits comfortably in one.

### 9.2 The job-claim loop

```python
def claim_next_job() -> ProcessingJob | None:
    requeue_stale_jobs()
    with transaction.atomic():
        job = (
            ProcessingJob.objects
            .select_for_update(skip_locked=True)
            .filter(status=Status.QUEUED)
            .order_by("created_at")
            .first()
        )
        if job:
            job.status = Status.PROCESSING
            job.attempts += 1
            job.locked_at = timezone.now()
            job.metadata["stage"] = "claimed"
            job.save(...)
        return job
```

**Key invariants:**

- `select_for_update(skip_locked=True)` ensures multiple workers can run
  concurrently without contention. A worker that finds a locked row skips
  to the next one rather than blocking.
- `attempts` increments on claim, not on completion. A worker that crashes
  mid-job has its attempts already counted.
- `locked_at` is the stale-detection key (Part 9.4).

### 9.3 The heartbeat

`WorkerHeartbeat` rows track worker liveness:

```python
record_worker_heartbeat(current_job=job, metadata={"stage": "..."})
```

Called on:

- Job claim
- Each stage transition within a job (parse / classify / extract /
  reconcile)
- Idle polling (every few seconds when no job available)

The frontend reads heartbeat freshness via `workspace.worker_health` in
the workspace payload. If the most recent heartbeat is older than a
threshold, the `WorkerHealthBanner` warns advisors.

### 9.4 Stale-job detection

`requeue_stale_jobs()` runs at the top of every `claim_next_job()` call.
It finds jobs in `PROCESSING` status with `locked_at` older than
`MP20_WORKER_STALE_SECONDS` (default 60s):

- If `attempts < max_attempts`: requeue to `QUEUED`, reset `locked_at`.
- Else: mark `FAILED` with `last_error="stale_after_max_attempts"`.

This recovers from worker crashes, SIGTERM mid-job, OOM kills, etc. The
worst case is one stale job's delay (60s) before recovery.

### 9.5 Retry semantics

Each `ProcessingJob` has `max_attempts` (default 3). When a job fails,
`_fail_or_retry(job, exc)`:

1. Increments `attempts`.
2. Records `failure_code` + `last_error` (typed message via
   `safe_exception_summary`) in `metadata`.
3. If `attempts < max_attempts`, sets status back to `QUEUED` for
   retry on next claim.
4. Else, sets status to `FAILED` permanently.

The advisor sees the retry count via `ProcessingJob.attempts` in the
workspace payload; the UI surfaces a "Retry" button if
`document.retry_eligible` is true (which is set when the job is in a
retryable failure state).

### 9.6 Duplicate suppression

`enqueue_reconcile()` is the entry point that creates a
`reconcile_workspace` job after document extraction. It checks for an
existing `reconcile_workspace` job for the same workspace that's
`QUEUED` or `PROCESSING` — if one exists, it doesn't enqueue another.
This prevents thundering-herd reconciliation when 12 documents land
simultaneously.

### 9.7 OCR overflow metadata

For large image PDFs, `extract_visual_facts_with_bedrock()` returns
`(facts, overflow_metadata)`. The `overflow_metadata` carries pages that
were skipped due to size or count limits. The worker stores this in
`ProcessingJob.metadata.overflow` and `ReviewDocument.processing_metadata.ocr_overflow=true`,
so the advisor sees a "Some pages were not processed" indicator on the
document row.

---

## Part 10 — State machines

### 10.1 `ReviewWorkspace.status`

```
DRAFT
  │  (documents uploaded, jobs enqueued)
  ▼
PROCESSING
  │  (worker reconcile completed; readiness computed)
  ▼
REVIEW_READY              (advisor edits, approves sections)
  │
  ▼
ENGINE_READY              (informational; same as REVIEW_READY + engine_ready)
  │
  │  (advisor commits)
  ▼
COMMITTED                 (linked_household set; auto-trigger fired)
```

A workspace can also go to:

- `ARCHIVED` (advisor deletes via DELETE endpoint).

### 10.2 `ReviewDocument.status`

```
UPLOADED                  (Layer 1 just persisted the file)
  │  (worker claims job; Layer 2 parses)
  ▼
CLASSIFIED                (doc type determined)
  │
  ├──(text extracted)─→ TEXT_EXTRACTED
  │                       │  (Layer 3 LLM call)
  │                       ▼
  │                     FACTS_EXTRACTED
  │                       │  (reconcile_workspace job runs)
  │                       ▼
  │                     RECONCILED
  │
  ├──(no text)──────→ OCR_REQUIRED
  │                       │  (Layer 3 visual extraction)
  │                       ▼
  │                     FACTS_EXTRACTED → RECONCILED
  │
  ├──(unsupported)──→ UNSUPPORTED      (no Layer 3 call)
  ├──(LLM failed)───→ FAILED            (retry-eligible per attempts)
  ├──(advisor flag)─→ MANUAL_ENTRY      (escape hatch)
  └──(SHA-256 dup)──→ DUPLICATE         (no Layer 3 call)
```

### 10.3 `ProcessingJob.status`

```
QUEUED
  │  (worker: claim_next_job)
  ▼
PROCESSING
  │
  ├──(success)────→ COMPLETED
  └──(failure)
     │  (attempts < max_attempts)
     │
     ├──→ QUEUED   (retry)
     │
     │  (attempts >= max_attempts OR stale)
     │
     └──→ FAILED
```

### 10.4 `SectionApproval.status`

```
NOT_READY_FOR_RECOMMENDATION    (initial; section has open blockers)
  │
  ▼
NEEDS_ATTENTION                  (advisor opened but didn't approve)
  │
  ├──→ APPROVED                  (clean approval)
  └──→ APPROVED_WITH_UNKNOWNS    (advisor approved despite optional gaps)
```

### 10.5 `PortfolioRun` lifecycle (via `PortfolioRunEvent`)

```
portfolio_run_generated         (first run for a household)
  │
  ├──→ portfolio_run_reused              (REUSED path; hash match)
  ├──→ invalidated_by_cma                (CMA publish)
  ├──→ invalidated_by_household_change   (household state mutation)
  ├──→ portfolio_run_declined            (advisor decline)
  ├──→ portfolio_run_integrity_alert     (hash_mismatch detected)
  ├──→ regenerated_after_decline         (advisor re-generate after decline)
  ├──→ audit_exported                    (sanitized audit export)
  └──→ generation_failed                 (engine raised; new attempt audited)
```

The run itself is immutable; only events get appended. The `current`
flag on the run is the latest in time per household; older runs become
`superseded` in display logic (not via DB column change).

---

## Part 11 — Audit emission across the pipeline

### 11.1 The `AuditEvent` model

`web/audit/models.py`:

```python
class AuditEvent(models.Model):
    actor = models.CharField(max_length=255, default="system")
    action = models.CharField(max_length=120)
    entity_type = models.CharField(max_length=120)
    entity_id = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk and AuditEvent.objects.filter(pk=self.pk).exists():
            raise ValidationError("Audit events are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit events are immutable.")
```

Append-only at the ORM layer; double-locked by the DB trigger (Part 11.2).

### 11.2 The DB trigger

`web/audit/migrations/0002_audit_immutability.py`:

```sql
CREATE OR REPLACE FUNCTION audit_event_immutable()
RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'Audit events are immutable';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_event_no_update
BEFORE UPDATE ON audit_auditevent
FOR EACH ROW EXECUTE FUNCTION audit_event_immutable();

CREATE TRIGGER audit_event_no_delete
BEFORE DELETE ON audit_auditevent
FOR EACH ROW EXECUTE FUNCTION audit_event_immutable();
```

This means even a privileged operator running raw SQL cannot modify audit
rows (without first dropping the trigger, which is itself a tracked
operation). See [ADR-0013](adr/0013-immutable-audit-via-db-triggers.md)
for the full rationale.

### 11.3 `record_event`

`web/audit/writer.py`:

```python
def record_event(*, action, entity_type, entity_id="", actor="system",
                 metadata=None) -> AuditEvent:
    return AuditEvent.objects.create(
        actor=actor, action=action,
        entity_type=entity_type, entity_id=entity_id,
        metadata=metadata or {},
    )
```

Every audit emission in the codebase goes through this helper. No
direct `AuditEvent.objects.create()` calls — the canon discipline is to
use the writer so future PII-sanitization wrappers can hook in.

### 11.4 `safe_audit_metadata` — PII scrubbing

`web/api/error_codes.py`:

```python
def safe_audit_metadata(exc: Exception, **extra) -> dict[str, object]:
    """Return a PII-safe audit-event metadata dict for an exception.
    Replaces the legacy `metadata={"detail": str(exc), ...}` pattern.
    """
    payload = {"failure_code": failure_code_for_exc(exc)}
    payload.update(extra)
    return payload
```

The function carries a `failure_code` (stable enum string like
`"NoActiveCMASnapshot"`) plus caller-provided extras. **Never** carries
the raw exception text.

The PII grep guard (`scripts/check-pii-leaks.sh`) forbids `str(exc)` in
audit metadata, response bodies, last_error columns, failure_reason
columns. The only legitimate path for exception content is the
secure-root debug dump (Part 4.12).

### 11.5 The audit action vocabulary

Across the codebase, ~50 distinct `record_event(action=...)` strings fire.
Grouped by subsystem:

**Session / auth:**
`local_login`, `local_logout`, `session_viewed`, `advisor_provisioned`,
`disclaimer_acknowledged`

**Read-only views (compliance trail):**
`client_list_viewed`, `client_detail_viewed`, `feedback_report_viewed`,
`review_evidence_viewed`

**Workspace lifecycle:**
`review_workspace_created`, `review_workspace_deleted`,
`review_workspace_uncommitted`, `review_workspace_reopened`,
`review_documents_uploaded`, `review_document_processed`,
`review_document_retry_queued`, `review_document_manual_entry_marked`,
`review_document_unsupported`, `review_document_upload_failed`,
`extraction_failed`, `real_upload_blocked`

**Review state changes:**
`review_conflict_resolved`, `review_conflict_deferred`,
`review_section_approved`, `review_fact_override_applied`,
`entities_reconciled`, `entities_reconciled_via_button`,
`entity_merge_candidate_resolved`

**Commit:**
`review_state_committed`, `household_wizard_committed`,
`planning_version_created`

**Engine + portfolio:**
`engine_run`, `engine_kill_switch_blocked`, `portfolio_run_generated`,
`portfolio_run_reused`, `portfolio_run_declined`,
`portfolio_run_integrity_alert`, `portfolio_run_audit_exported`,
`portfolio_generation_skipped_post_<source>`,
`portfolio_generation_post_<source>_failed`,
`portfolio_generation_blocker_surfaced`

**Household / goal mutations:**
`account_assigned_to_goals`, `assign_to_goal`, `edit_account_value`,
`external_holdings_updated`, `goal_risk_override_created`,
`household_snapshot_created`, `household_snapshot_restored`,
`realignment_applied`, `open_review_workspace`

**CMA:**
`cma_snapshot_seeded`, `cma_snapshot_draft_created`,
`cma_snapshot_updated`, `cma_snapshot_published`

**Feedback:**
`feedback_submitted`, `feedback_triaged`

**Disposal / cleanup:**
`review_artifact_disposal_delete`

This breadth is unusual and load-bearing for compliance: a regulator can
reconstruct an advisor's full session, not just the writes. Every event
carries structured metadata (counts, UUIDs, codes) and never carries
client content.

### 11.6 `failure_code_for_exc` + `friendly_message_for_code`

`web/api/error_codes.py` exposes:

- `failure_code_for_exc(exc)` — maps typed exceptions to stable codes
  (e.g., `EngineKillSwitchBlocked` → `"engine_disabled"`).
- `safe_exception_summary(exc)` — `"ClassName:code"` only.
- `safe_response_payload(data)` — redacts PII from HTTP response bodies.
- `friendly_message_for_code(code)` — advisor-facing copy (i18n-keyed).

Every typed exception has a known code and a known advisor message. The
frontend renders the message via i18n key `review.failure_code.<code>`
(for extraction) or `recommendation.failure.<code>` (for engine).

---

## Part 12 — Real-PII discipline at every layer

The defense-in-depth regime per canon §11.8.3 enforces specific controls
at each layer. The companion doc
[`real-pii-handling.md`](real-pii-handling.md) is the procedural reference;
this section maps each control to the layer that enforces it.

### Layer 1 — Ingestion

**Persists:** file bytes (under `MP20_SECURE_DATA_ROOT`, never repo),
SHA-256 hash, original filename, content_type.

**Enforces:**

- Secure-root validation (no CLI path for real PII)
- Path traversal protection
- Real-derived uploads gated by RBAC (`advisor` role only)

**Transient:** the in-memory file object after the worker reads bytes.

### Layer 2 — Parsing

**Persists:** parsed text in `ReviewDocument.processing_metadata.text`
(temporarily, until reconcile) + classifier output.

**Enforces:**

- Raw text never written outside the secure root
- Worker process runs inside the same container as the backend; no IPC
  channel for parsed text

**Transient:** parsed text after Layer 3 completes (cleared from
`processing_metadata` via post-extraction cleanup).

### Layer 3 — LLM extraction

**Persists:**

- `ExtractedFact` rows with `value`, redacted `evidence_quote`
- `processing_metadata.failure_code`, `prompt_version`,
  `extraction_run_id`, token counts
- (Debug only) raw Bedrock responses under
  `$MP20_SECURE_DATA_ROOT/_debug/`

**Enforces:**

- Bedrock ca-central-1 only for real-derived (fail-closed)
- Anthropic-direct never invoked for real_derived (route check
  server-side)
- Tool-use schema prevents free-form narrative emission
- Debug logging gated by `MP20_DEBUG_BEDROCK_RESPONSES=1`; default off
- PII grep guard forbids `str(exc)` in failure_reason / last_error /
  response bodies / audit metadata

**Transient:** the in-process Bedrock response object after fact emission.
Raw text is not retained outside the fact's `evidence_quote` (which gets
redacted at serialization).

### Layer 4 — Reconciliation

**Persists:**

- `ExtractedFact.canonical_index` (set after alignment)
- `MergeCandidate` data in `reviewed_state['merge_candidates']`
  (structural only: indices, scores, field names; never raw values)
- Account numbers in alignment features are SHA-256 truncated;
  last-4 digits used for matching but not persisted

**Enforces:**

- Hashed identifiers for sensitive numeric fields
- Merge candidates carry only structural metadata
- Cross-class silent resolution doesn't persist the losing fact's value
  in a "conflict-resolved" log; the loser's `is_current` flag flips
  (winner is the new current)

**Transient:** the in-process alignment dataclass.

### Layer 5 — Review

**Persists:**

- `reviewed_state` JSON with full advisor-facing shape
- `FactOverride` rows with `value`, `rationale` (advisor-scoped, not
  PII-redacted; advisors are trusted with their own clients' data)
- `SectionApproval` rows with `notes` (advisor-scoped)
- `AuditEvent` rows with structural metadata only

**Enforces:**

- Evidence quotes pre-redacted server-side
  (`web/api/review_redaction.py`) before they reach the response
- Advisors see only their own team's workspaces
- Financial analysts denied access to real-PII surfaces
  (`can_access_real_pii` gate)

**Audit emission discipline:** every audit event carries counts, UUIDs,
codes — never names, DOBs, account numbers, or rationale text. The
`rationale_length` field is logged but not the rationale itself.

### Across layers: the PII grep guard

`scripts/check-pii-leaks.sh` scans for:

- `last_error\s*=\s*str(exc` — DB column persistence
- `failure_reason\s*=\s*str(exc`
- `Response\(\{"detail":\s*str\(exc` — HTTP response body leak
- `metadata=\{"detail":\s*str\(exc` — audit metadata leak

Allowed:

- `safe_response_payload(exc)` / `safe_audit_metadata(exc)`
- Test files (fixtures)
- `# noqa: PII-safe-classifier` comment for specific allowed cases

The guard runs in the gate suite (`scripts/test-python-postgres.sh`).

---

## Part 13 — Error handling matrix

| Failure mode | Layer | Status produced | Advisor sees | Retryable? |
| --- | --- | --- | --- | --- |
| Bedrock 503 / timeout (ca-central-1) | LLM | `FAILED` initially; auto-retry until `attempts ≥ max_attempts` | "Document failed — retrying" → "Manual entry" CTA | Yes (auto via worker) |
| Tool-use response missing required field | LLM | `FAILED` with `bedrock_schema_mismatch` | "Extraction format error" + manual-entry CTA | Yes (once); usually doesn't help |
| Tool-use response exceeded max_tokens | LLM | `FAILED` with `bedrock_token_limit` | "Document too large for extraction" + manual-entry CTA | Yes (once); usually doesn't help |
| PDF 0 text + 0 image-PDFs + > MP20_OCR_MAX_PAGES | Parse → LLM | `OCR_REQUIRED` but Layer 3 vision path skips | "Document needs manual entry" | Manual only |
| XLSX with unsupported macros | Parse | Loads as zero rows; classifier sees generic_financial; LLM returns 0 facts | "0 facts extracted" + manual-entry CTA | No (structural) |
| DOCX with embedded images | Parse | Images skipped; text-only extracted | Normal flow; lower confidence | No (by design) |
| LLM returns valid JSON but `derivation_method=defaulted` | Validate | Fact dropped silently by Phase 9 validation | Fact doesn't appear (no surface) | No (correct behavior) |
| Worker dies mid-extraction | Worker | `PROCESSING → QUEUED` via stale-job detection | Brief delay; auto-recovered | Yes (auto) |
| Account number hash collision | Alignment | Two accounts merged as one | (No surface; rare) | No (silent) |
| Real-PII upload missing secure root | Layer 1 | 503 `secure_root_missing` | "Upload temporarily disabled" | No (operator) |
| Engine kill-switch on | Commit → Auto-trigger | Commit succeeds; engine raises `EngineKillSwitchBlocked` | "Recommendation generation paused" inline | Yes (when re-enabled) |
| No active CMA snapshot | Auto-trigger | Same — typed skip audited | "Analyst needs to publish CMA" inline | Yes (when CMA published) |
| Construction-ready blocker survives commit | Auto-trigger | Typed skip; commit still persists | Per-blocker CTAs in BlockerBanner | Yes (when advisor resolves) |
| Engine math error (unexpected) | Auto-trigger | `portfolio_generation_post_review_commit_failed` audit | Inline banner + Sonner toast | No (engineering investigates) |

---

## Part 14 — Performance characteristics

### 14.1 Per-document Bedrock latency

Empirical from pre-pilot canaries (2026-05-03 R10 sweep across 7 client
folders):

- KYC PDF (text path, ~5 pages): ~8–15s
- Statement PDF (text path, holdings tables): ~10–20s
- Native vision PDF (5 image pages): ~30–50s
- Meeting note DOCX: ~6–10s
- XLSX (3 sheets, mixed): ~12–25s

Per-doc Bedrock cost (Sonnet 4.6 pricing):

- Text path: $0.01–$0.05
- Vision path: $0.05–$0.20 depending on page count
- Mean across the R10 sweep: ~$0.04/doc

Pilot budget: $25/advisor/week (off-ramp at $50; pause at $500 cumulative).
Pre-pilot total: $0.36 cumulative.

### 14.2 Engine.optimize() latency

Per A0.2 perf benchmark on Sandra/Mike Chen synthetic:

- Typed-skip path: 311 μs (e.g., kill-switch on)
- REUSED path: 266 ms (hash match, return cached run)
- Cold first-run: 530 ms (full optimization)

Locked perf budget: P50 < 250 ms, P99 < 1 s strict (locked
decisions #18 and #56). The 530 ms cold first-run sits just below
the strict P99; sustained drift would supersede the sync-trigger
design per [ADR-0009](adr/0009-sync-auto-trigger.md) supersession path.

### 14.3 Worker throughput

A single worker processes one document at a time. Typical pipeline for a
real Steadyhand client folder (~12 documents):

- Upload (frontend): ~30s (advisor activity)
- Layer 1 (per file): < 1s
- Layer 2 (per file): < 5s
- Layer 3 (per file): 8–50s
- Layer 4 (workspace reconcile): < 2s

Total: ~3–5 minutes for 12 documents. Scales linearly with document count
since the worker is single-threaded.

### 14.4 End-to-end timing budget (locked)

- Time-to-first-portfolio (median): < 30 min per workspace
  (pilot-success-metric #7)
- Per-doc reconciliation success rate: ≥ 90% (metric #3)
- Manual-entry rate: < 25% (metric #6)

### 14.5 Bundle size + backend test count

- Frontend bundle: 278.94 kB gzipped (locked cap 290 kB)
- Backend pytest: 1,198+ tests (post Phase B1)
- Frontend Vitest: 391+
- Playwright cross-browser: 21
- Playwright visual-verification: 34 baselines

---

## Part 15 — Extension points

### 15.1 Adding a new document type

1. Add the type to the classifier enumeration in
   `extraction/classification.py`.
2. Add classifier heuristics in the same file (filename patterns,
   content signatures).
3. Create a new prompt file in `extraction/prompts/<doctype>.py` with:
   - A `PROMPT_VERSION` string
   - A `build_prompt()` function that composes the three shared
     guardrail blocks plus your doc-specific body
4. Register the new doc type in `PROMPT_VERSION_BY_TYPE` and
   `BUILD_PROMPT_BY_TYPE` in `extraction/prompts/__init__.py`.
5. Add tests in `extraction/tests/test_prompts_interpolation.py` for the
   new prompt's compose output.
6. Consider whether new fact fields are needed (Part 15.2).

### 15.2 Adding a new fact schema field

1. If it's a new section: add to `ENGINE_REQUIRED_SECTIONS` in
   `review_state.py:52`. The frontend will read it from
   `workspace.required_sections` automatically.
2. Add a Django model field if the data persists in committed state.
3. Update `to_engine_household` in `engine_adapter.py` to translate the
   new field to engine schemas.
4. Update `engine/schemas.py` to add the field to the engine input
   Pydantic model.
5. Update the relevant prompt(s) in `extraction/prompts/` to instruct the
   model on the new field.
6. Update `reviewed_state_from_workspace` projection in
   `review_state.py` if the field needs to land in the JSON.
7. Update the frontend `ReviewedState` type in `lib/review.ts`. The
   OpenAPI codegen gate will catch drift.
8. Add a new readiness blocker in `readiness_for_state` if the field is
   required.
9. Add a new structured blocker code if a per-blocker CTA is needed.

### 15.3 Adding a new source-priority rule

1. Update the `authority_matrix` in `extraction/reconciliation.py` with
   the new doc-type-to-priority mapping for the relevant section.
2. Add the new source type to the Hypothesis property tests in
   `extraction/tests/test_reconciliation_properties.py` so the new
   priority is validated.
3. Update the canon §11.4 hierarchy table.
4. Update [ADR-0012](adr/0012-source-priority-hierarchy.md) if the rule
   changes the broader policy.

### 15.4 Adding a new Tier-2 candidate matcher (e.g., for external_holdings)

1. Add a new prefix to the matcher in `extraction/entity_alignment.py`:
   - Define threshold + band constants
   - Add feature-extraction logic for the new prefix
   - Add contradicting-field rules for the new prefix
2. Update the `EntityAlignment` dataclass if a new feature shape is
   needed.
3. Add Hypothesis property tests for the new prefix in
   `extraction/tests/test_entity_alignment_properties.py`.
4. Update the backend `MergeCandidateResolveView` to handle the new
   prefix.
5. Update the frontend `MergeCandidateGroup` (when Phase B2 lands) to
   render the new prefix.
6. Update [ADR-0007](adr/0007-three-tier-entity-matcher.md) if the
   matcher contract changes.

### 15.5 Adding a new audit action

1. Use `record_event(action="new_action_name", entity_type="...", ...)`
   at the call site.
2. Construct metadata via `safe_audit_metadata(exc=None, **kwargs)` even
   for success events (it's the consistent pattern; kwargs become the
   metadata dict).
3. Ensure metadata carries only counts, UUIDs, codes — never client
   content.
4. Add an entry to the docs/team/ai-doc-ingestion-deep-dive.md (this
   file) Part 11.5 catalog.
5. Consider whether the frontend audit timeline needs an i18n label
   (search for `audit_timeline.action_label` keys in `en.json`).

---

## Part 16 — Surprises and non-obvious patterns

### 16.1 Cascade-delete on `_merge_household_state`

The commit boundary deletes all members / accounts / goals and recreates
them. Anything that depends on stable `Person.external_id`,
`Account.external_id`, or `Goal.external_id` across re-commits will
break. Today nothing does, but it's a footgun for future work.

### 16.2 Account-type normalization is one-way

`_normalize_account_type` maps lowercase to canonical UPPERCASE but has
no reverse map. Unknown inputs pass through. If extraction starts
returning "Registered Retirement Savings Plan" (full name) instead of
"rrsp", the normalizer won't fix it — and the downstream
`ALLOWED_ENGINE_ACCOUNT_TYPES` check will surface
`unsupported_engine_account_type` as a construction blocker. The advisor
overrides the account type via FactOverride. The prompt should be
updated to constrain emission, not the normalizer.

### 16.3 Risk score resolution is split across layers

`Goal.goal_risk_score` (system-derived) vs `GoalRiskOverride.score_1_5`
(advisor override). The only correct way to read the effective score for
engine input is `effective_goal_risk_score(goal)`. Any new code path
that reads `goal.goal_risk_score` directly silently breaks the override
mechanism. This was a real bug surfaced in locked decision #100. The
fix consolidates resolution to a single helper.

### 16.4 The reusability check is OUTSIDE the write-atomic

`_trigger_portfolio_generation`'s reusability check runs in a separate
mini-atomic before the main write-atomic. This is per locked
decision #81 — it means an "ambiguous current lifecycle" audit event
can persist even when the main atomic rolls back. The reason: ensures
audit emits on raise rather than silently rolling back with the engine
call.

### 16.5 Phase B2 frontend not yet shipped

Workspaces created today store `merge_candidates` in `reviewed_state`
(Phase B1 backend, shipped 2026-05-05) but show no UI for adjudication
(Phase B2 frontend, queued in the active plan). The MergeCandidateGroup
component, MergeCandidateBulkBar, and the mutation hook
(`useResolveMergeCandidate`) are not yet built. Workspace data is
persistent and will surface in the UI once B2 lands.

### 16.6 `reviewed_state.readiness` can go stale

`reviewed_state.readiness` is computed at reconcile time and stored on
the workspace JSON. Subsequent mutations (fact override, conflict
resolve, section approve) update the state but **do not always update
the readiness JSON in place**. The frontend re-computes readiness via
`reviewed_state_from_workspace()` → `readiness_for_state()`. If new code
reads `workspace.readiness` directly, it could see stale data. Use the
endpoint payload, not the column.

### 16.7 `merge_decisions` is index-fragile under re-reconcile

The keys `"people:0:2"` reference canonical indices. If a re-reconcile
introduces a new entity that shifts indices (e.g., a new statement adds
a new person at canonical 1, pushing old canonicals 1+ to indices 2+),
the prior decision keys become stale. Phase B2 + Round 18 #36 address
this by re-executing prior `merge` decisions by canonical-pair-string
matching against the new alignment, but the implementation is not yet
fully proven against real-PII data.

### 16.8 Regulatory enum normalization can surface PII via error messages

`_normalize_regulatory_enum` raises `ValueError` with the original
value included in the message: `"engine_adapter: regulatory_objective='X'
normalizes to 'x' which is not in allowed values [...]."` If the
advisor pasted a free-text value (e.g., a real client's name into the
wrong field by mistake), the value could surface in the error message.
The current PII grep guard catches `str(exc)` patterns but the
underlying value is still in the exception object. A future hardening
would scrub before raising.

### 16.9 `safe_audit_metadata` is permissive on extra kwargs

The helper concatenates `**extra` into the metadata dict without
validation. If a caller passes `account_label=full_account_number`, that
value lands in audit metadata. Discipline relies on code review +
canon §11.8.3 awareness; the helper doesn't enforce. A future
hardening would add structured-only metadata accepters per action.

### 16.10 `integrations/llm/` is orphaned

The `integrations/llm/` directory exists with `anthropic_provider.py`,
`bedrock_provider.py`, and `client.py` shells, but `client.py` raises
`NotImplementedError`. All real LLM access goes through
`extraction/llm.py`. This is documented as code drift #1 in
`docs/agent/open-questions.md`. Decision pending: delete the orphan
directory or rewire it as a thin façade over `extraction/llm.py`.

### 16.11 The "honest meta-call" pattern

Subagent gate suites pass against the fixtures the subagent itself
writes. They don't catch regressions in existing higher-level tests or
shape drifts in production payloads. After any subagent-completed work,
re-run the FULL foundation e2e and verify Vitest mocks mirror
production payload shapes. This is documented in
`docs/agent/handoff-log.md` (the "honest meta-call" section at the
sub-session #11 deferred-work verification pass) and is captured as an
anti-pattern in the master onboarding dossier.

---

## Part 17 — In-flight work as of 2026-05-12

### 17.1 Phase B1 — matcher Tier-2 backend (shipped)

Commit `7274485` (2026-05-05): `feat(p1.1.fix): matcher Tier-2 merge
candidates + endpoint + audit + account_type normalize`. Shipped:

- `MergeCandidate` dataclass + Tier-2 emission in
  `extraction/entity_alignment.py`
- `MergeCandidateResolveView` and `MergeCandidateBulkKeepSeparateView`
  endpoints
- `_normalize_account_type` + `ACCOUNT_TYPE_NORMALIZATION` at the commit
  boundary
- `reviewed_state['merge_candidates']` + `reviewed_state['merge_decisions']`
  persistence
- `entity_merge_candidate_resolved` audit event
- +102 test cases

### 17.2 Phase B2–B7 — UX friction reduction (queued)

Active plan: `~/.claude/plans/you-are-continuing-a-playful-hammock.md`
(1547 lines, 37 lock-ins across 7 interview rounds).

- B2: MergeCandidate UI components (MergeCandidateGroup,
  MergeCandidateCard, MergeCandidateBulkBar)
- B3: ConflictCard authoritative input + N/A + sequence + undo (gaps
  A, G, E, I)
- B4: SectionApprovalAccordion + compound CTAs + human labels + state
  preview accordion (gaps C, D, F, H)
- B5: 7-client real-PII verification matrix
- B5.5: Playwright e2e automation
- B6: final gate + mutation testing + 3-pass code-reviewer
- B7: commit + CHANGELOG + tag `v0.1.4-pilot-ux-friction-reduction`

### 17.3 Phase P2.1 + P2.5 — re-open + re-reconcile (shipped)

`ClientReopenView` (create a workspace seeded from a committed
household) and `ClientReconcileView` (re-run alignment + reconcile on a
workspace) shipped in Pair 7a. Used when advisors need to edit a
committed household post-commit (e.g., new statement arrived,
correction needed).

### 17.4 Phase 9 — fact-quality recovery (post-pilot)

`docs/agent/phase9-fact-quality-iteration.md` plans a recall-recovery
sweep after the Phase 4 tool-use migration's −41% recall regression.
Approach: layered prompt iteration (permissive base + strict per-type +
inferred-with-evidence-validation + empirical advisor-productivity
measurement). Not currently in flight; queued for post-pilot.

---

## Part 18 — Reference + pointers

### 18.1 Files to read for each layer

| Layer | Primary file | Related |
| --- | --- | --- |
| 1 — Ingestion | `web/api/views.py` (ReviewWorkspaceUploadView) | `frontend/src/modals/DocDropOverlay.tsx`, `frontend/src/lib/upload-recovery.ts` |
| 2 — Parsing | `extraction/parsers.py` | `extraction/classification.py`, `extraction/schemas.py` |
| 3 — LLM extraction | `extraction/llm.py` | `extraction/prompts/`, `extraction/validation.py`, `extraction/pipeline.py` |
| 4 — Reconciliation | `extraction/entity_alignment.py` | `extraction/reconciliation.py`, `extraction/normalization.py` |
| 5 — Review | `web/api/review_state.py` | `frontend/src/modals/ReviewScreen.tsx`, `frontend/src/lib/review.ts`, `frontend/src/modals/ConflictPanel.tsx` |
| Commit boundary | `web/api/review_state.py` (`_merge_household_state`, `commit_reviewed_state`) | `web/api/views.py` (`ReviewWorkspaceCommitView`) |
| Auto-trigger | `web/api/views.py` (`_trigger_portfolio_generation`, `_trigger_and_audit`, `_trigger_and_audit_for_workspace`) | `web/api/error_codes.py`, `web/api/engine_adapter.py` |
| Engine | `engine/optimizer.py` | `engine/schemas.py`, `engine/frontier.py`, `engine/projections.py` |
| Worker | `web/api/management/commands/process_review_queue.py` | `web/api/review_processing.py` |
| Audit | `web/audit/models.py`, `web/audit/writer.py` | `web/audit/migrations/0002_audit_immutability.py`, `web/api/error_codes.py` |

### 18.2 Tests to run for verification

```bash
# Full pipeline integration
scripts/test-python-postgres.sh

# Engine purity (no Django imports allowed)
uv run pytest engine/tests/test_engine_purity.py -v

# Entity alignment correctness
uv run pytest extraction/tests/test_entity_alignment.py extraction/tests/test_entity_alignment_merge_candidates.py extraction/tests/test_entity_alignment_properties.py -v

# Reconciliation + conflict surfacing
uv run pytest extraction/tests/test_reconciliation_baseline.py extraction/tests/test_reconciliation_properties.py -v

# Commit boundary + auto-trigger
uv run pytest web/api/tests/test_review_state.py web/api/tests/test_portfolio_run.py web/api/tests/test_trigger_audit.py -v

# Audit append-only invariants
uv run pytest web/api/tests/test_audit_metadata_invariants.py -v

# PII grep guard
bash scripts/check-pii-leaks.sh

# Vocabulary CI
bash scripts/check-vocab.sh

# Frontend type contract
cd frontend && npm run codegen && npm run typecheck

# End-to-end synthetic
cd frontend && PLAYWRIGHT_BASE_URL=http://localhost:5173 npm run e2e:synthetic
```

### 18.3 Diagrams

For visual flow, see:

- [`architecture-diagrams.md`](architecture-diagrams.md) — the four-layer
  view, the upload-to-portfolio sequence, the three-tier matcher decision
  tree, the workspace state machine, the auto-trigger flow, the
  deployment topology.

### 18.4 Glossary

For vocabulary, see [`glossary.md`](glossary.md). Key terms used in this
document: building-block fund, canonical entity, canonical index,
construction-ready, derivation method, engine adapter, engine-ready,
ExtractedFact, FactOverride, goal-account link, kill-switch,
manual-entry escape hatch, reviewed_state, source-priority hierarchy,
Tier-1 / Tier-2 / Tier-3 matcher, tool-use mode.

---

## Appendix A — The engine output shape (link_first.v2)

The engine produces a single `EngineOutput` Pydantic model serialized
into `PortfolioRun.output`:

```jsonc
{
  "schema_version": "engine_output.link_first.v2",
  "link_recommendations": [
    {
      "goal_id": "goal_retirement_income",
      "account_id": "acct_mike_rrsp",
      "goal_account_link_external_id": "link_mike_rrsp_retirement",
      "allocated_amount": 620000.0,
      "ideal_pct": 0.62,                    // ideal % of goal
      "blend": [
        { "fund_id": "SH-Eq", "weight": 0.45 },
        { "fund_id": "SH-Inc", "weight": 0.30 },
        { "fund_id": "SH-Sav", "weight": 0.25 }
      ],
      "expected_return": 0.062,             // annualized
      "volatility": 0.115,                  // annualized stdev
      "advisor_summary": "Balanced blend driven by 4-year retirement horizon...",
      "projection": [                       // P10/P50/P90 by year
        { "year": 1, "p10": 580000, "p50": 658000, "p90": 745000 },
        ...
      ],
      "current_comparison": {
        "current_blend": [...],
        "current_expected_return": 0.054,
        "current_volatility": 0.135
      }
    }
  ],
  "account_rollups": [
    {
      "account_id": "acct_mike_rrsp",
      "expected_return": 0.062,
      "volatility": 0.115,
      "ideal_blend": [...],
      "current_blend": [...]
    }
  ],
  "household_rollup": {
    "expected_return": 0.058,
    "volatility": 0.108,
    "top_funds": [
      { "fund_id": "SH-Eq", "weight": 0.42 },
      { "fund_id": "SH-Inc", "weight": 0.31 },
      ...
    ]
  },
  "run_signature": "<sha256 of inputs>",
  "engine_version": "v2.7",
  "technical_trace": {
    "frontier_points": 50,
    "pareto_filtered": 47,
    "optimization_iterations": 12,
    "cma_snapshot_id": 5,
    ...
  }
}
```

The frontend `RecommendationBanner`, `AdvisorSummaryPanel`,
`OptimizerOutputWidget`, `MovesPanel`, and `HouseholdPortfolioPanel` all
consume this shape via the 4 navigation helpers in `lib/household.ts`.

---

## Appendix B — Recommended reading order for a new contributor

If you've never touched this code before, read in this order:

1. **This document** — Parts 1–8 to establish mental model.
2. **`architecture-diagrams.md`** — visual reinforcement.
3. **`adr/0001-engine-as-library.md`** — the most foundational ADR.
4. **`adr/0007-three-tier-entity-matcher.md`** — to understand the
   current in-flight Tier-2 work.
5. **`adr/0009-sync-auto-trigger.md`** — to understand the commit-time
   engine call.
6. **`adr/0004-real-pii-defense-in-depth.md`** — to understand the
   discipline regime.
7. **`real-pii-handling.md`** — to understand operational rules.
8. **Live code:** open `web/api/review_state.py` and read
   `_merge_household_state` plus `commit_reviewed_state`. They're the
   single most important pair of functions in the codebase.
9. **Live code:** open `extraction/entity_alignment.py` and read
   `align_facts`, `_compute_merge_candidates`, and `_score_tier2`.
10. **Live code:** open `web/api/views.py` and read the helper trio
    (`_trigger_portfolio_generation`, `_trigger_and_audit`,
    `_trigger_and_audit_for_workspace`).

Once you've done all of the above, you can navigate any new ingestion
question in the codebase.

---

**Last verified:** 2026-05-12 against HEAD `0a5de93` (one commit past
tag `v0.1.3-pilot-quality-closure`).
