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
