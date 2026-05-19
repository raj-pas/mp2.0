---
title: ADR-0004 — Real-PII defense-in-depth regime
status: Accepted
decision_date: 2026-04-30
deciders: [Saranyaraj Rajendran, Lori Norman, Fraser Stark]
supersedes: []
superseded_by: []
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
update_when: This ADR's supersession-path conditions trigger an update; otherwise revise when the cited canon section, code symbols, or referenced sibling ADRs change.
---

# ADR-0004 — Real-PII defense-in-depth regime

**Status:** Accepted
**Decision date:** 2026-04-30 (canon §11.8.3 reframe)
**Deciders:** Saranyaraj Rajendran (engineering lead); Lori Norman
(compliance + IS lead); Fraser Stark (project lead).

## Context

Earlier versions of the canon proposed **pre-LLM pseudonymization**:
substitute every real PII value with a synthetic placeholder before
sending to the LLM, then re-substitute on the way back. The idea was
to prevent any real PII from reaching the LLM at all.

In practice, pseudonymization had two fatal weaknesses:

1. **Coverage is hard.** Real client documents contain PII in many
   shapes (names in headers, account numbers in tables, dates of
   birth in long-form text). Pseudonymizing all of them reliably
   requires its own NER-grade extractor — which would itself need
   the LLM.
2. **Round-trip drift.** Substituting `[NAME_1]` back into the
   structured output reliably is brittle. Real outputs sometimes
   referenced names not in the substitution map (the LLM noticing
   the spouse's name appears in two formats and "correcting" one).

The canon §11.8.3 reframe (locked 2026-04-30) retires pre-LLM
pseudonymization in favor of a **defense-in-depth** regime: many
imperfect layers that together provide the assurance pseudonymization
was supposed to provide alone.

## Decision

Real-PII handling for MP2.0 uses the following 12 layers, each
independently enforced. The companion operational guide
[`real-pii-handling.md`](../real-pii-handling.md) §2 expands these
into 13 numbered points (it splits "vocabulary discipline" from
"bounded pilot population"); the layer count is approximate and the
two documents describe the same regime.

1. **Authenticated ingress only.** Real client documents enter the
   system only via the authenticated browser upload path
   (`ReviewWorkspaceUploadView`). There is no CLI / script path for
   real PII ingest.

2. **Secure storage root.** Raw uploaded files live under
   `MP20_SECURE_DATA_ROOT`, a path **outside** the repo. Path
   validation rejects repo-local paths at startup. The path is
   gitignored.

3. **Bedrock ca-central-1 fail-closed.** Real-derived extraction
   routes through Bedrock in ca-central-1. ADR-0003 covers this.

4. **Transient raw text.** Extracted text lives in worker memory only
   during processing. The DB stores **structured facts**, **run
   metadata**, **provenance**, and **minimally redacted evidence
   quotes** — never the full raw text.

5. **Sensitive identifier hashing.** Account numbers, SINs, and
   similar are hashed (SHA-256 truncated to 16 hex) before being
   stored or used as matcher features. The hash is stable across
   reconcile cycles (deterministic input → deterministic output) but
   non-reversible.

6. **Evidence quote redaction.** When the system stores an evidence
   quote for advisor display, it runs server-side redaction
   (`extraction/normalization.py` + the redaction patterns in
   `web/api/error_codes.py`) to mask routing numbers, phone numbers,
   addresses, and similar.

7. **Immutable audit via DB triggers.** Every consequential action
   produces an append-only `AuditEvent`. The Postgres trigger blocks
   UPDATE/DELETE. See ADR-0002 + ADR-0013.

8. **RBAC.** Two roles — `advisor` and `financial_analyst`. Financial
   analysts cannot access real-client PII surfaces; they edit CMA
   but never see client review workspaces or household detail. The
   gatekeeper is `web/api/access.py:can_access_real_pii`.

9. **Retention / disposal tooling.** `web/api/management/commands/
   dispose_review_artifacts.py` reports + deletes local raw artifacts
   whose version metadata is no longer current. Formal IT policy
   trigger is pending (Phase B).

10. **Bounded pilot population.** 3–5 advisors, all from Steadyhand,
    all in a controlled local-production-like deployment. Broader
    rollout requires Lori + Amitha review (next checkpoint: 2026-05-21).

11. **PII grep CI guard** (`scripts/check-pii-leaks.sh`). Forbids
    `str(exc)` in DB columns / response bodies / audit metadata, plus
    routing-number / phone / address patterns in code paths.

12. **Vocabulary discipline.** Real client surnames stay inside
    `MP20_SECURE_DATA_ROOT`. Documents under `docs/`, `docs/agent/`,
    and `docs/team/` use placeholders or descriptors. The vocab CI
    guard helps but doesn't replace human discipline.

Each layer is imperfect alone. Together they provide the defensible
posture that pre-LLM pseudonymization was meant to provide.

## Consequences

### Positive

- The system supports real Canadian client PII from day one of the
  pilot without each contributor having to internalize a single
  monolithic "PII rule." The layers are concrete and testable.
- A failure of any single layer doesn't compromise the regime —
  the other layers contain the blast radius.
- The CI guard catches the most common leak vector (`str(exc)`).
- Compliance review (Lori) can verify the regime by walking the 12
  layers, not by auditing a regex-based redaction implementation
  for completeness.

### Negative

- The 12 layers are more surface area than a single pseudonymization
  pass. Each layer needs to be maintained, tested, and re-verified
  when contributors change the relevant code.
- The "real-PII only via authenticated browser" rule prevents
  scripted bulk ingest, which some operators find frustrating. The
  manual-entry escape hatch + the demo-prep upload scripts are the
  approved bypasses for synthetic data.
- New contributors sometimes try to log `str(exc)` for debugging
  convenience. The CI guard catches it, but the friction is real.

## Alternatives considered

### Alternative A: Pre-LLM pseudonymization (original canon proposal)

Rejected for the reasons in Context. Could be revisited if a future
Bedrock posture review demands it.

### Alternative B: Single-layer redaction (regex-based content
filtering at every output point)

Rejected. Regex-based redaction is fragile; gaps are easy to introduce.
A defense-in-depth posture is more robust because it doesn't depend on
any single regex being complete.

### Alternative C: On-prem LLM (eliminate cross-border data flow
entirely)

Rejected for pilot scope. See ADR-0003 Alternative C.

## Supersession path

If broader rollout (Phase C scale, additional firms beyond Steadyhand,
production deployment outside the local-prod-like model) demands a
re-framing of the regime, supersede this ADR with one that specifies
the new layers + the rationale. Sign-off required from Lori Norman
(compliance), Saranyaraj Rajendran, Fraser Stark, and Amitha
(Engineering Director liaison).

The 2026-05-21 broader-rollout review is the natural trigger for this.

## References

- Canon §11.8.3 — privacy regime / defense-in-depth (the canonical
  source)
- `extraction/llm.py` — Bedrock client + typed exceptions
- `extraction/normalization.py` — sensitive-ID hashing + redaction
- `web/api/error_codes.py` — `safe_audit_metadata`,
  `safe_response_payload`, `_REDACTION_PATTERNS`
- `web/api/access.py` — `can_access_real_pii`
- `scripts/check-pii-leaks.sh` — CI guard
- `web/api/management/commands/dispose_review_artifacts.py` — local
  artifact retention/disposal
- `docs/team/real-pii-handling.md` — the procedural guide derived
  from this ADR
- `docs/agent/open-questions.md` "Real-PII Authorization Status" —
  the 2026-05-21 broader-rollout review trigger
- Sibling ADRs:
  - ADR-0002 (append-only audit) — layer 7
  - ADR-0003 (Bedrock ca-central-1) — layer 3
  - ADR-0011 (vocabulary discipline) — layer 12
  - ADR-0013 (immutable audit via DB triggers) — layer 7 backstop
