---
title: ADR-0010 — Production-grade-MVP reframe (retire "demo-grade")
status: Accepted
decision_date: 2026-04-30
deciders: [Fraser Stark, Saranyaraj Rajendran, Lori Norman, Som Seif]
supersedes: []
superseded_by: []
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
update_when: This ADR's supersession-path conditions trigger an update; otherwise revise when the cited canon section, code symbols, or referenced sibling ADRs change.
---

# ADR-0010 — Production-grade-MVP reframe

**Status:** Accepted
**Decision date:** 2026-04-30 (canon v2.8 reframe; §1.6)
**Deciders:** Fraser Stark (project lead); Saranyaraj Rajendran
(engineering lead); Lori Norman (compliance + IS lead); Som Seif
(executive sponsor).

## Context

Earlier framings of MP2.0 used the vocabulary "Som demo," "Friday
launch event," "Phase A scaffold-grade," and "demo-grade" to describe
the early implementation. The intent was charitable: signal that the
first cut wouldn't be feature-complete and would prioritize narrative
flow over edge-case handling.

In practice this vocabulary created a **false comfort that some
controls could be deferred**. Real client PII arrived in the system by
Day 2 evening when the secure-local review tranche landed. Real PII
doesn't wait for Phase B; the engineering bar had to adjust the
moment real PII flowed through the system — which, in hindsight, was
from the start.

The team realized the gap between the language ("demo-grade") and the
reality (real PII flowing through real auth, real audit, real
extraction) was itself a risk: a contributor reading "demo-grade"
might reasonably defer adding an audit event, defer hardening a
failure mode, or defer a PII-leak check.

## Decision

The canon's §1.6 reframe is in force:

> **MP2.0 is production-grade software with a deliberately small user
> set.** The word "MVP" describes scope (small, focused, controlled
> pilot population), not engineering bar (it is not "demo-grade,"
> "scaffolding," or "throwaway"). Three to five Steadyhand Investment
> Specialists will use the system with their real clients. Real
> Canadian client PII flows through the system from day one.

The implications:

| Concern | The actual bar |
|---|---|
| Audience posture | Active — real advisors using the system to inform real client conversations |
| PII handling | Real PII flows from day one; controls are production-grade or the system doesn't ship |
| Auth | Authenticated-by-default DRF, advisor team scope, financial-analyst PII denial, kill-switch on engine generation. MFA / lockout / password reset are Phase B *additions* to a production foundation, not introductions |
| Audit | Append-only via model guards plus DB triggers, sanitized timeline events, edit hashes, kill-switch as audit event. Browser UI is deferred; **the writes are not.** |
| Output trust | Every recommendation marked as pilot-mode requiring advisor judgment; engine never invents numbers |
| Failure mode | An advisor takes pilot output to a real client conversation. Kill-switch, audit trail, and bounded blast radius (3–5 advisors) are how this is contained, not avoided |
| Success metric | Advisors keep using it after week one; no Sev-1 incidents |

The earlier vocabulary ("Phase A is demo-grade," "stage-managed paths,"
"scaffold-grade," "Som-demo-grade") is retired and removed from the
canon. The Phase A → B → C structure remains useful **as a rollout
sequence** (offsite foundation → IS validation → pilot expansion), but
each phase is **production-grade for its scope**. The gates between
phases are about *coverage* (more advisors, more clients, more
controls layered in), not about *quality* (which is production-grade
throughout).

## Consequences

### Positive

- Every contributor (engineer, PM, leadership) has a single
  unambiguous bar. "Is this production-grade?" is the question,
  even if the user set is small.
- The kill-switch, audit, RBAC, PII discipline, and fail-closed
  Bedrock routing are not deferrable. They are present from
  v0.1.0-pilot onward.
- Compliance review (Lori) has a defensible posture: the controls
  exist at pilot launch, not "soon, in Phase B."
- The vocabulary CI (ADR-0011) prevents reintroduction of the retired
  framing.

### Negative

- The engineering pace is sometimes slower than a "demo-grade"
  framing would allow. Adding an audit event takes time; running
  the gate suite before a commit takes time. The trade-off is
  intentional.
- Some Phase B items (MFA, password reset, full RBAC governance,
  CI PII scanners) are correctly framed as "Phase B *additions* to
  a production foundation" — but the line between "Phase A production
  foundation" and "Phase B addition" is sometimes ambiguous. The
  canon's open-questions list tracks the ambiguities.

## Alternatives considered

### Alternative A: Keep the "demo-grade" framing for Phase A

Rejected. The framing produced concrete bugs (real PII flowing
through unauthenticated demo paths in early code) before the reframe.
The reframe is the lesson.

### Alternative B: Use "MVP" alone (without the "production-grade" qualifier)

Rejected. "MVP" alone is industry-ambiguous; some readers interpret
it as throwaway. The qualifier is the load-bearing word.

## Supersession path

If a future business decision moves to a genuinely-throwaway demo
context (e.g., a public marketing demo with no real users), an ADR
could specify a "demo profile" feature flag that disables the
production controls. But the current canon §1.6 framing does not
anticipate this.

Sign-off would require Fraser Stark, Saranyaraj Rajendran, Lori
Norman, and Som Seif (the original Deciders).

## References

- Canon §1.6 — "The deliverable — production-grade MVP for advisor
  pilot" (the canonical reframe)
- Canon §1.7 — "Platform alignment" (the snap-in-on-Advisor-Center
  posture that complements the production-grade bar)
- `docs/agent/handoff-log.md` 2026-04-30 — original canon v2.8 land
- All other ADRs in this folder — each is a concrete instantiation
  of the production-grade bar.
- Sibling ADRs:
  - ADR-0011 (vocabulary discipline) — the CI enforcement that
    prevents reintroduction of retired framings.
  - ADR-0004 (real-PII defense-in-depth) — the controls that the
    production-grade bar requires from day one.
