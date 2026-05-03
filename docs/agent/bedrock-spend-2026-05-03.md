# Bedrock Spend Ledger — 2026-05-03 onwards

**Authorized:** No hard cap (user 2026-05-03)
**Soft escalation triggers:** $200 per sub-session OR $500 cumulative
**Region:** ca-central-1 (real-PII data residency)
**Default model:** `global.anthropic.claude-sonnet-4-6` ($3 / $15 per 1M)
**Vision-canary alt model:** `global.anthropic.claude-opus-4-7` ($5 / $25 per 1M) — escalate to if Sonnet 4.6 vision quality lacks

Append entries as Bedrock canaries run. Real-PII discipline (canon
§11.8.3): structural counts only — no values, no quotes, no
client-identifying text.

---

## Pre-sub-session #8 baseline

**HEAD:** `9d03013`
**Cumulative spend prior to sub-session #8:** ~$3 (per
`docs/agent/r10-sweep-results-2026-05-02.md`).

---

## 2026-05-03 — Sub-session #8.5 — Niesner native-PDF canary

**Phase:** #8.5 vision-path canary against image-likely Croesus
printscreen PDFs that previously returned 0 facts via the text path.
**HEAD before:** `2d61cc0` (#8.1-#8.4 foundation)
**HEAD after:** (this commit)
**Duration:** 53.3s wall-clock for 5 sequential calls
**Calls:** 5
**Total input tokens:** 22,858
**Total output tokens:** 4,701
**Estimated cost:** $0.1391

Per-doc / per-call breakdown (real-PII discipline: redacted
positional labels; doc_type from `extraction.classification`):

| Doc / call | Path | Input tok | Output tok | Cost | Facts | Notes |
|---|---|---|---|---|---|---|
| niesner-02-identity | vision_native_pdf | 4,531 | 630 | $0.0230 | 6 | 1 page; previously 0 facts |
| niesner-03-kyc | vision_native_pdf | 4,633 | 1,178 | $0.0316 | 11 | 1 page; previously 0 facts |
| niesner-04-identity | vision_native_pdf | 4,530 | 1,080 | $0.0298 | 10 | 1 page; previously 0 facts |
| niesner-05-identity | vision_native_pdf | 4,531 | 441 | $0.0202 | 4 | 1 page; previously 0 facts |
| niesner-07-kyc | vision_native_pdf | 4,633 | 1,372 | $0.0345 | 13 | 1 page; previously 0 facts |

Total: $0.1391
Cumulative across sub-session: $0.1391
Cumulative all sub-sessions: ~$3.14

---

## 2026-05-03 — Sub-session #9 — Phase 9 prompt-recovery canary

**Phase:** #9.4 — re-canary against Seltzer + Niesner spot-check
under the new permissive-base + evidence-validator prompts
(`v3_tooluse` per type).
**HEAD before:** `735ecae` (#8 close-out)
**HEAD after:** (this commit)
**Duration:** Seltzer 142s + Niesner 320s = 462s wall-clock
**Calls:** 14 (5 Seltzer + 9 Niesner)
**Total input tokens:** 40,349
**Total output tokens:** 6,468
**Estimated cost:** $0.2181

| Doc / call | Path | Input tok | Output tok | Cost | Facts | Notes |
|---|---|---|---|---|---|---|
| seltzer-01-identity | vision_native_pdf | 5,004 | 288 | $0.0193 | 2 | Phase 4 baseline 8; -75% (single-page Croesus) |
| seltzer-02-identity | vision_native_pdf | 5,005 | 629 | $0.0245 | 6 | Phase 4 baseline 5; +20% |
| seltzer-03-kyc | text | (text path) | (text path) | (text path) | 29 | Phase 4 baseline 27; +7% |
| seltzer-04-kyc | vision_native_pdf | 5,107 | 1,747 | $0.0415 | 18 | Phase 4 baseline 16; +13% |
| seltzer-05-meeting_note | text | (text path) | (text path) | (text path) | 40 | Phase 4 baseline 38; +5% |
| niesner-03-planning | text | (text path) | (text path) | (text path) | 111 | new doc class; Phase 4 hadn't extracted |
| niesner-05-identity | vision_native_pdf | 5,006 | 629 | $0.0245 | 6 | spot-check vs #8.5 |
| niesner-06-kyc | vision_native_pdf | 5,108 | 1,162 | $0.0328 | 12 | new (post-Phase-4) |
| niesner-07-identity | vision_native_pdf | 5,005 | 284 | $0.0193 | 2 | spot-check vs #8.5 |
| niesner-08-meeting_note | text | (text path) | (text path) | (text path) | 38 | Phase 4 baseline 34; +12% |
| niesner-09-identity | vision_native_pdf | 5,006 | 630 | $0.0245 | 6 | new (post-Phase-4) |
| niesner-10-kyc | text | (text path) | (text path) | (text path) | 42 | new (post-Phase-4) |
| niesner-11-kyc | vision_native_pdf | 5,108 | 1,099 | $0.0318 | 10 | new (post-Phase-4) |
| niesner-12-planning | text | (text path) | (text path) | (text path) | 52 | new (post-Phase-4) |

Total: $0.2181
Cumulative across sub-session: $0.2181
Cumulative all sub-sessions: ~$3.36

Stop-condition checks (Phase 9 design doc §9.4):
- [x] Per-call cost under $0.50/doc — max $0.0415 ✓
- [x] No anomalous structure — every doc returned ≥2 facts ✓
- [x] Real-PII discipline maintained — structural counts only ✓
- [x] Zero `defaulted` facts ✓
- [x] Zero hallucinated section paths ✓
- [ ] Recall recovery ≥20pp — actual +1pp on Seltzer total. See
  `r10-sweep-results-2026-05-03.md` for the honest reading;
  documented as expected single-wave-iteration outcome and
  forwarded to post-pilot multi-tool-architecture (Phase 9.4
  design doc).

Stop-condition checks:
- [x] Per-call cost under $0.50/doc — max $0.0345 ✓
- [x] No anomalous structure — every image-PDF returned ≥4 facts ✓
- [x] Real-PII discipline maintained — structural counts only;
  redacted labels; no values, no quotes ✓

Detection helper: classified 5 of 8 Niesner PDFs as image-likely
(`ocr_required` from pymupdf). All 5 routed to the new native-PDF
path; all 5 produced facts. The 3 text-rich PDFs (financial plan
+ projections) routed to the text path (unchanged behavior).

Result vs the friction this sub-session targets: advisor previously
manually entered 30+ facts/doc via the 5b.10/11 forms for Croesus
printscreens because the text path returned 0. Now those same docs
extract 4-13 facts each — manual-entry burden drops to review +
adjust. Cost is well within the per-doc <$0.50 budget.

Forward implications for sub-session #11 R10 sweep:
- Estimated incremental Bedrock spend for vision-path coverage of
  the remaining 6 client folders: ~$0.15 × 6 ≈ ~$1 if image-PDF
  density is similar; could be 5-10x higher for folders with more
  scanned KYC docs. Well within budget.
- Per-doc latency 6-14s; Niesner at 5 docs took 53s. A 7-folder
  sweep of all image-PDFs is likely 5-15 min wall-clock total for
  the new path alone.

---

## Entry template

```
## YYYY-MM-DD — Sub-session #N — <activity>

**Phase:** #N.M (e.g., #8.1 vision-path canary)
**HEAD before:** <sha>
**HEAD after:** <sha>
**Duration:** Xm
**Calls:** N
**Total input tokens:** N
**Total output tokens:** N
**Estimated cost:** $X.XX

Per-doc / per-call breakdown:
| Doc / call | Path | Input tok | Output tok | Cost | Facts | Notes |
|---|---|---|---|---|---|---|
| <id> | text/vision | N | N | $X.XX | N | … |

Total: $X.XX
Cumulative across sub-session: $X.XX
Cumulative all sub-sessions: $X.XX

Stop-condition checks:
- [ ] Per-call cost under $0.50/doc
- [ ] No anomalous structure (e.g., 0 facts unexpectedly)
- [ ] Real-PII discipline maintained (no values in metadata)
```

---

## Automated R10 7-folder sweep (2026-05-03 22:37 UTC) — Sub-session #11 deferred

**Phase:** sub-session #11 deferred-work follow-up; full 7-folder
real-PII sweep against the live demo stack via
``scripts/demo-prep/r10_sweep.py --anonymize-folders``.
**Duration:** ~63 min wall-clock for 56 docs across 7 folders.
**Calls:** 56 (1 Bedrock call per doc; mix of text + vision_native_pdf).
**Total input tokens:** 151,342
**Total output tokens:** 27,325
**Estimated cost:** $0.8639

Per-folder structural breakdown (folder names anonymized as
``client_<sha256-prefix>``; surname-to-id map only inside
``MP20_SECURE_DATA_ROOT/_debug/``):

| Folder (anon) | Docs | Input tok | Output tok | Cost | DB facts | Path mix |
|---|---|---|---|---|---|---|
| client_95acac6d | 9 | 25,233 | 4,823 | $0.1480 | 109 | text=4, vision=5 |
| client_48bb4b33 | 7 | 20,179 | 3,460 | $0.1124 | 114 | text=3, vision=4 |
| client_4a6ecae4 | 7 | 25,230 | 4,850 | $0.1484 | 126 | vision=5, text=2 |
| client_3c5f07a1 | 13 | 25,233 | 3,804 | $0.1328 | 382 | text=8, vision=5 |
| client_e8f7e5fa | 10 | 25,232 | 4,772 | $0.1473 | 223 | text=5, vision=5 |
| client_2076f34d | 5 | 15,116 | 2,968 | $0.0899 | 89 | vision=3, text=2 |
| client_10edfe80 | 5 | 15,119 | 2,648 | $0.0851 | 79 | vision=3, text=2 |

**Sweep total:** $0.8639
**Sweep input tokens:** 151,342
**Sweep output tokens:** 27,325
**Cumulative across sub-session #11 follow-up:** $0.8639
**Cumulative all sub-sessions:** ~$4.22 ($3.36 prior + $0.86 sweep)

Stop-condition checks (all clean):
- [x] Per-doc cost under $0.50 — max single-doc cost ~$0.04 ✓
- [x] Per-folder cost under $10 — max folder cost $0.1484 ✓
- [x] Per-folder wall-clock under 30 min — max ~14 min (Niesner) ✓
- [x] No anomalous structure — every folder 100% reconciled ✓
- [x] Real-PII discipline maintained — anonymized labels;
  structural counts only; no values, no quotes ✓
- [x] Zero evidence-quote drops across all 56 docs (Phase 9.3
  validator clean)

### Note on the recompute

The first append from the sweep script reported $0.0000 in every
row due to a key-path bug (`processing_metadata.bedrock_cost_*`
instead of the nested `processing_metadata.extraction.bedrock_cost_*`).
The values above were recomputed from the stored metadata after
the bug was fixed (`_doc_extraction_meta` helper +
`scripts/demo-prep/test_r10_sweep.py` regression coverage). The
DB workspaces remain in `review_ready` so the recompute is
non-destructive.
