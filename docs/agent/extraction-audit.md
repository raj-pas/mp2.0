# Extraction-Subsystem Audit (Living)

**Last full audit:** 2026-05-02 (HEAD `f5f2519`)
**Last update:** 2026-05-02 (HEAD `f5f2519`)
**Author:** Claude Code session 2026-05-02 (post-overnight re-audit)

This is a **living doc** — future audits update rows in place + append
to the audit-history log; do not delete rows. Each row carries a
status timeline.

---

## How To Use This Doc

1. Re-read before any extraction-pipeline work (per CLAUDE.md
   "Start Every Session" block).
2. When closing a finding, update its row's status + add the closing
   commit / phase reference to the timeline column.
3. When a new audit runs, append findings under the appropriate
   severity heading and add an entry to the audit-history log.
4. Severity legend:
   - **DEMO** = blocks 2026-05-04 demo
   - **PILOT** = blocks 2026-05-08 limited-beta release
   - **PHASE B** = post-pilot debt

---

## Already Addressed (verified at HEAD `f5f2519`)

These are findings the prior audit (HEAD `03ce247`) flagged as open;
verified addressed by reading current file:line. **Do not re-do.**

| ID | Where | How addressed | Status timeline |
|---|---|---|---|
| CONC-1 | `web/api/views.py:1130-1152` | `select_for_update()` on workspace held across approval-status flip loop | open at `03ce247`; closed by HEAD baseline |
| CONC-2 | `web/api/review_processing.py:287-298`; `web/api/review_state.py:472-480` | Commit `0701d33` — `reconcile_workspace` short-circuits on COMMITTED; `create_state_version` excludes status from update_fields when COMMITTED | open at `03ce247`; closed by `0701d33` |
| CONC-4 | `web/api/review_processing.py:128-151` | `dequeue_next_job` uses `select_for_update(skip_locked=True)` inside `transaction.atomic()` | open at `03ce247`; closed by HEAD baseline |
| TYPE-1 | `extraction/llm.py:83-108`; `web/api/review_processing.py:407-413` | Commit `826cdb1` — typed `BedrockNonJsonError`/`TokenLimitError`/`SchemaMismatchError`; `_fail_or_retry` reads `.failure_code` | open at `03ce247`; closed by `826cdb1` |
| REGION-1 | `extraction/pipeline.py:34-36` | `extract_facts_for_document` raises if `real_derived` and `bedrock_config` is None | open at `03ce247`; closed by HEAD baseline |
| REGION-2 | `extraction/llm.py:243-278` | `extract_visual_facts_with_bedrock` routes through `_bedrock_client(config)`; region flows from config dataclass | open at `03ce247`; closed by HEAD baseline |
| RBAC-1 | `web/api/views.py:1074-1075` | `ReviewFactEvidenceView` scopes via `_workspace_for_user`; team-scoped query | open at `03ce247`; closed by HEAD baseline |
| CONF-1 | `extraction/schemas.py:79-83` | `@field_validator` returns `"medium"` on invalid input; no silent default-on-validation-failure | open at `03ce247`; closed by HEAD baseline |
| Bug 1 (workspace COMMITTED race) | `0701d33` | 2 regression tests pin the race-fix | open pre-`0701d33`; closed by `0701d33` |
| Bug 2 (zero-value Purpose accounts) | `e528fb5` | three-layer defense (state, household, optimizer) + DB integrity test | open pre-`e528fb5`; closed by `e528fb5` |

---

## Open — Pilot-Blocking (must close for 2026-05-08)

| ID | Severity | Location | Gap | Phase owner |
|---|---|---|---|---|
| PII-1 | PILOT | `web/api/views.py:237, 259, 326, 584, 827, 1138` | `Response({"detail": str(exc)}, ...)` returns raw exception in HTTP body | Phase 2 |
| PII-2 | PILOT | `web/api/review_processing.py:414` | `job.last_error = str(exc)` persists raw exception | Phase 2 |
| PII-3 | PILOT | `web/api/review_processing.py:427`; `review_serializers.py:31` | `ReviewDocument.failure_reason = str(exc)` exposed via API | Phase 2 |
| PII-4 | PILOT | `web/api/views.py:235, 257, 324, 825` | Audit metadata `{"detail": str(exc)}` writes raw exception to immutable trail | Phase 2 |
| PII-SER | PILOT | `web/api/review_serializers.py:71` | `ProcessingJobSerializer.last_error` field exposes raw text | Phase 2 |
| REDACT-1 | PILOT | `web/api/review_redaction.py:29-33` | `_REDACTION_PATTERNS` missing routing numbers, phone numbers, addresses | Phase 2 |
| ENUM-CASE | DEMO | `web/api/engine_adapter.py:65` (only `investment_knowledge`) | `_normalize_lowercase_enum` not applied to `regulatory_objective`, `regulatory_time_horizon`, `regulatory_risk_rating`, `marital_status`. Real-PII Bedrock often returns capitalized values → engine rejects silently | Phase 1 |
| BUG-1 | PILOT | `web/api/views.py:970-1054` (`ReviewDocumentManualEntryView.post`) | No `transaction.atomic() + select_for_update()` on document. Lost-update race possible; audit interleave risk | Phase 3.1 |
| REC-1 | PILOT | `web/api/review_processing.py:154-176` | `process_job` marks COMPLETED before `enqueue_reconcile` succeeds. If enqueue fails, workspace stuck in "processing" forever | Phase 3.2 |

---

## Open — Production-Grade (high ROI for first-week advisor trust)

| ID | Severity | Location | Gap | Phase owner |
|---|---|---|---|---|
| PROMPT-1 | PILOT | `extraction/llm.py:281-320`; `extraction/prompts/*` | Per-doc-type prompt modules exist but body is unified — `PROMPT_VERSION_BY_TYPE` only routes a version string | Phase 4 |
| PROMPT-2 | PILOT | `extraction/llm.py:308` | One-line "do not invent missing financial numbers"; no examples block | Phase 4 |
| PROMPT-3 | PILOT | `extraction/llm.py:297-320` | No few-shot examples for the JSON schema | Phase 4 |
| PROMPT-4 | PILOT | `extraction/llm.py:297-320` | No explicit forbid of markdown tables / prose preambles / code fences | Phase 4 |
| PROMPT-5 | PILOT | `extraction/llm.py:297-320` | Confidence not tied to source class | Phase 4 |
| REPAIR-1 | PILOT | `extraction/llm.py:175, 202, 542` | `_repair_json_text` only strips trailing commas; no markdown-table or prose-preamble handling. Tool-use migration eliminates this surface entirely | Phase 4 (eliminated) |
| REPAIR-2 | PILOT | `extraction/llm.py:405-422` | `_normalize_bedrock_payload` silently accepts alternate keys (`extracted_facts`, `fields`, `results`, `data`). Tool-use migration eliminates this surface | Phase 4 (eliminated) |
| CONFLICT-CARD | PILOT | `frontend/src/modals/ReviewScreen.tsx` + backend | r10-mockup-parity §7 marks ✓ via generic PATCH /state/; full mockup-parity card UI deferred — user authorized full scope 2026-05-01 | Phase 5a |
| TEST-GAP-1 | PILOT | `engine/tests/` or `web/api/tests/` | No pytest validating `generate_portfolio` tolerates zero-value Purpose account end-to-end (Bug 2 has invariant test only) | Phase 6.1 |
| TEST-GAP-2 | PILOT | `web/api/tests/test_review_ingestion.py` | No worker-crash-and-recovery test exercising the full `requeue_stale_jobs` cycle | Phase 6.2 |

---

## Phase B (post-pilot, deferred)

These are real gaps but not week-1 blockers for the 3-5 advisor pilot.

- **CONC-3:** `_merge_household_state` direct atomicity — currently
  mitigated by caller's `@transaction.atomic` decorator. Phase B
  rewrite as upsert + explicit deletion audit events
  (dossier §13.5).
- **Auth/RBAC hardening:** MFA, session timeout, lockout, password
  reset, real role governance, pilot disclaimer surface (now
  shipping in Phase 5b.1 as scope adjustment).
- **Audit browser UI:** advisor sees timeline in workspace context;
  full browser UI deferred.
- **Self-hosted fonts:** `frontend/public/fonts/*.woff2` empty;
  cosmetic OTS warnings; UX fine via fallback.
- **fr-CA i18n population:** `fr.json` empty; translation pass
  post-pilot per locked #12.

**Pulled into this session's scope 2026-05-02:**
- OpenAPI-typescript codegen (P0 #5) → Phase 4.5
- REC-1 (process_job COMPLETED ordering) → Phase 3.2

---

## Real-PII Leak Vectors (cross-reference for PII grep guard)

Five distinct sites where `str(exc)` flows to storage / audit / API
and could leak real client content:

1. **HTTP error response body:** `views.py:237, 259, 326, 584, 827, 1138`
2. **`ProcessingJob.last_error` field:** `review_processing.py:414`
3. **`ReviewDocument.failure_reason` field:** `review_processing.py:427`
4. **Audit event metadata `detail` key:** `views.py:235, 257, 324, 825`
5. **Serializer surface:** `review_serializers.py:71`

Phase 2 closes all five sites + adds `scripts/check-pii-leaks.sh` CI
guard to prevent regression.

---

## Audit History (append-only)

- **2026-05-02** — Triple-Explore audit at HEAD `f5f2519`. Verified
  8 prior findings closed (CONC-1, CONC-2, CONC-4, TYPE-1, REGION-1,
  REGION-2, RBAC-1, CONF-1). Identified 8 open + 2 new findings:
  ENUM-CASE (DEMO-blocker), BUG-1 (PILOT-blocker manual-entry race).
  Plan re-scoped to surgical close-out;
  see `~/.claude/plans/you-are-continuing-a-playful-hammock.md`
  (~50 user-locked decisions across 12 interview rounds).
- **2026-05-01** — Triple-Explore audit at HEAD `03ce247` produced
  ~30 findings spanning prompts, JSON repair, exception PII leaks,
  concurrency races, and atomic-merge gaps. Most findings later
  closed by the 2026-05-01 → 2026-05-02 overnight implementation
  pass.

---

## Pointers

- Working canon: `MP2.0_Working_Canon.md` (canon v2.8) — §11
  extraction, §9.4 architecture invariants, §11.8.3 real-PII
  discipline, §11.4 source-priority hierarchy, §9.4.5 AI-numbers rule.
- Master plan: `~/.claude/plans/i-want-you-to-rosy-mccarthy.md` —
  39 locked decisions across R0-R10.
- Session plan: `~/.claude/plans/you-are-continuing-a-playful-hammock.md`
  — current session's scope.
- Memory: `~/.claude/projects/-Users-saranyaraj-Projects-github-repo-mp2-0/memory/project_extraction_pipeline_map.md`.
- Live state: `docs/agent/session-state.md`.
- Append-only log: `docs/agent/handoff-log.md`.
