---
title: ADR-0003 — Bedrock ca-central-1 for real-PII extraction
status: Accepted
decision_date: 2026-04-30
deciders: [Saranyaraj Rajendran, Lori Norman, Fraser Stark]
supersedes: []
superseded_by: []
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
update_when: This ADR's supersession-path conditions trigger an update; otherwise revise when the cited canon section, code symbols, or referenced sibling ADRs change.
---

# ADR-0003 — Bedrock ca-central-1 for real-PII extraction

**Status:** Accepted
**Decision date:** 2026-04-30
**Deciders:** Saranyaraj Rajendran (engineering lead); Lori Norman
(compliance + IS lead); Fraser Stark (project lead).

## Context

Layer 3 of the extraction pipeline (canon §11.3) uses a large language
model to extract structured facts from advisor-uploaded documents
(KYC forms, statements, meeting notes, planning docs). The LLM is
necessary because document shapes are heterogeneous and structured
parsers can't cover the long tail.

Real client documents contain Canadian PII: names, SINs, dates of
birth, account numbers, addresses, employment history. Canadian
privacy regulation (PIPEDA + provincial equivalents) and Purpose's
internal data-classification policies prefer in-Canada processing
when feasible. MP2.0's defense-in-depth regime (canon §11.8.3)
formalizes this preference.

Two LLM access routes are available:

- Anthropic API direct (us-east-1) — used during early development.
- AWS Bedrock in ca-central-1 — Canadian region, IAM-scoped.

A mixed routing pattern is also possible (real data → Bedrock,
synthetic → Anthropic direct).

## Decision

For documents with `data_origin = real_derived`, the extraction
pipeline routes **only** through AWS Bedrock in **ca-central-1**.
Anthropic-direct routing is permitted only for `data_origin =
synthetic` (Sandra & Mike Chen + R5 wizard smoke fixtures).

The routing is enforced server-side in the extraction client
(`extraction/llm.py`). A misconfigured environment (e.g., missing
`AWS_REGION` or `BEDROCK_MODEL`) fails the worker run rather than
silently falling back.

When Bedrock ca-central-1 is unreachable for a real-derived document,
the document is marked `failed`. There is **no fallback** to
us-east-1, no fallback to local extraction. The advisor uses the
manual-entry escape hatch (`ReviewDocumentManualEntryView`).

## Consequences

### Positive

- Real client PII never leaves Canadian AWS infrastructure during
  LLM inference. Defensible posture under PIPEDA + provincial
  regulations.
- The routing rule is enforced in code (not just policy), so a
  contributor cannot accidentally route real data through us-east-1.
- The fail-closed behavior means a temporary regional outage produces
  a clear "extraction failed, use manual entry" UX rather than a
  silent compliance violation.
- The structured `failure_code` on a Bedrock failure (e.g.,
  `bedrock_non_json`, `bedrock_token_limit`) flows into
  advisor-facing copy via `friendly_message_for_code`.

### Negative

- ca-central-1 has historically had slightly higher Bedrock latency
  + slightly lower model availability than us-east-1. Acceptable for
  pilot scale (3–5 advisors); revisit if it becomes a scaling
  bottleneck.
- Cross-region failover is unavailable. If ca-central-1 is down,
  real-PII extraction halts. The kill-switch (ADR-0009) does not
  apply to extraction — only to portfolio generation.
- The cost-and-throughput envelope is constrained by ca-central-1's
  Bedrock quotas. The pilot's $25/advisor/week budget assumed
  ca-central-1 pricing.

## Alternatives considered

### Alternative A: Anthropic API direct (us-east-1) for everything

Rejected. Violates the Canadian-data-residency preference + would
require a separate compliance posture (data-processing agreement
with Anthropic, US legal review).

### Alternative B: Mixed routing with us-east-1 fallback for outages

Rejected. The fail-closed posture is preferable: a temporary outage
that routes real data through us-east-1 would be a silent compliance
violation. Manual entry is a known, advisor-visible degraded path.

### Alternative C: On-prem LLM (private LLM hosted by Purpose)

Rejected for pilot scope. Operationally heavier (model serving,
GPU provisioning, ops on-call); we don't have the team for it yet.
Revisit in Phase C+ if Purpose builds the platform.

## Supersession path

If Bedrock ca-central-1 quotas become a sustained bottleneck (e.g.,
pilot expansion hits rate limits), supersede this ADR with one
that specifies either:

- A different in-Canada region (if AWS launches one).
- A bi-region setup with a documented fail-closed routing rule.
- A self-hosted LLM with its own privacy posture.

Sign-off required from Lori Norman (compliance), Saranyaraj
Rajendran, and Amitha (Engineering Director liaison) for the
broader rollout review.

## References

- Canon §11.3 — Layer 3 LLM extraction
- Canon §11.8.3 — privacy regime / defense-in-depth
- `extraction/llm.py` — the Bedrock client + typed exceptions
- `web/api/error_codes.py` — `friendly_message_for_code` advisor copy
- `.env.example` — `AWS_REGION=ca-central-1`, `BEDROCK_MODEL`
- `docs/agent/bedrock-spend-2026-05-03.md` — append-only spend ledger
- Sibling ADRs:
  - ADR-0004 (real-PII defense-in-depth) — ca-central-1 routing is
    one layer of the regime.
  - ADR-0008 (Postgres-only) — same "fail-loud not fall-back"
    posture.
