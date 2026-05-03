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
