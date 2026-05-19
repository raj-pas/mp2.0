---
title: Real-PII handling — procedural and reference
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
status: living
update_when: Canon §11.8.3 changes, the defense-in-depth layer set
  changes (e.g., adding/removing a layer), access-grant workflow
  changes (new IT step, new IAM role, different sign-off), a new
  "frequently violated" pattern emerges from incident review, or the
  broader rollout (Phase B/C) shifts the scope of who may access
  real PII.
---

# Real-PII handling

This document is the operational guide for handling real Canadian
client PII in MP2.0. It is **mandatory reading** before being granted
access to any real-PII workflow, and **mandatory recurring reference**
for ongoing day-to-day work.

The voice is imperative ("never paste real client values into Slack")
because every word matters. Soft framing has historically been a
source of leak risk.

## See also

- [`README.md`](README.md) — folder index + conventions
- [`onboarding-engineer.md`](onboarding-engineer.md) — Day 1 + Week 1
  context (the "How we work" section overlaps with this doc)
- [`adr/0003-bedrock-ca-central-1.md`](adr/0003-bedrock-ca-central-1.md)
  — Bedrock routing decision
- [`adr/0004-real-pii-defense-in-depth.md`](adr/0004-real-pii-defense-in-depth.md)
  — the architectural decision this doc operationalizes
- [`../agent/pilot-rollback.md`](../agent/pilot-rollback.md) — Sev-1
  procedure (where a PII leak is escalated)
- [`../../MP2.0_Working_Canon.md`](../../MP2.0_Working_Canon.md) §11.8.3
  — the canonical authoritative source

## 1. What real PII means here

In the MP2.0 pilot context, "real PII" is any data that originated
from a real Steadyhand client. Examples include:

- A client's full name (when paired with any other identifier).
- Date of birth, SIN, Social Insurance Number references.
- Account numbers (Steadyhand, custodian, or third-party).
- Address, phone number, email address.
- Employment details, employer name, income figures.
- Beneficiary names, trusted contact names.
- Client-authored notes from meetings.
- Document content that pertains to a specific client.

Note that **client surnames alone** (e.g., a workspace label) sit in
a gray zone. They aren't sensitive identifiers in the regulatory
sense, but the team's discipline is to avoid carrying them into
artifacts that leave `MP20_SECURE_DATA_ROOT`. Synthetic Sandra & Mike
Chen are exempt; the placeholder discipline applies to actual clients.

Synthetic data (the Sandra & Mike Chen persona at
`personas/sandra_mike_chen/client_state.json`, plus other test fixtures)
is **not** real PII. The same handling rules don't apply.

## 2. The defense-in-depth regime (plain language)

Canon §11.8.3 enumerates the regime. In plain language:

1. **Real client data enters the system only through the authenticated
   browser upload.** There is no CLI / script path. The advisor logs
   in, drops files in the `/review` UI, and the system handles the
   rest.

2. **Raw files live outside the repo.** `MP20_SECURE_DATA_ROOT` is
   the configured filesystem path. The path must be **outside** the
   git working copy. Validation rejects repo-local paths at startup.

3. **Extraction routes through Bedrock in ca-central-1.** Real-derived
   documents (`data_origin = real_derived`) route only through the
   Canadian Bedrock region. Anthropic-direct routing is used only for
   synthetic data.

4. **Bedrock failure is fail-closed.** If ca-central-1 is unreachable,
   the document is marked `failed`. There is no fallback to
   us-east-1 or to local extraction. The advisor uses the manual-entry
   escape hatch (`ReviewDocumentManualEntryView`).

5. **Raw text is transient.** Extracted text lives in worker memory
   during processing only. The database stores **structured facts**,
   **run metadata**, **provenance**, and **minimally redacted
   evidence quotes**. The full raw text never persists.

6. **Sensitive identifiers are hashed.** Account numbers, SINs, and
   similar are SHA-256-hashed (truncated to 16 hex) before being
   used as matcher features or stored. The hash is deterministic
   (same input → same hash) but non-reversible.

7. **Evidence quotes are redacted server-side.** Account numbers,
   routing numbers, phone numbers, addresses, and similar are masked
   before the quote is stored or shown to the advisor.

8. **Audit is immutable.** `AuditEvent` rows can't be modified or
   deleted (model guard + Postgres trigger). The audit log survives
   even a destructive dev reset.

9. **RBAC.** Only the `advisor` role can access real-PII surfaces
   (client list, review workspaces, household detail). The
   `financial_analyst` role can edit CMA but cannot reach real PII.

10. **Retention / disposal.** The
    `web/api/management/commands/dispose_review_artifacts.py` command
    reports and deletes local raw artifacts whose version metadata is
    no longer current. Formal IT-policy trigger pending Phase B.

11. **PII grep CI guard.** `scripts/check-pii-leaks.sh` forbids
    `str(exc)` in DB columns / response bodies / audit metadata, plus
    routing-number / phone / address patterns in code.

12. **Vocabulary discipline.** Real client surnames stay inside
    `MP20_SECURE_DATA_ROOT`. Code, docs, commits, and chat use
    placeholders.

13. **Bounded pilot population.** Three to five advisors, all from
    Steadyhand, all in a local-production-like deployment. Broader
    rollout requires Lori (compliance + IS lead) and Amitha
    (Engineering Director liaison) review.

## 3. Real-PII access workflow

Real-PII access is granted by **Saranyaraj Rajendran** (engineering
lead) in coordination with **Lori Norman** (compliance + IS lead).
The granting process:

1. **Trigger:** A new contributor needs to operate against real
   client workspaces (debug a real-PII bug, run the R10 sweep, etc.).
2. **Prerequisites — signed handling policy.** The contributor reads
   this document end-to-end + the canon §11.8.3 section + ADR-0004.
   They sign a "I understand and accept the regime" acknowledgement
   (form maintained by Lori).
3. **Prerequisites — IT confirmation.** Purpose IT confirms the
   contributor's account access + AWS IAM membership.
4. **AWS IAM role assignment.** The contributor is added to the
   Bedrock IAM role that grants `ca-central-1` Bedrock access.
   Saranyaraj + the IAM admin perform this.
5. **1Password vault entry.** The contributor is granted access to
   the `mp20-pilot-secrets` shared vault. Contains the Bedrock
   credentials + pilot advisor provisioning YAML location.
6. **Local environment configured.** `.env` populated with
   `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
   `AWS_REGION=ca-central-1`, `BEDROCK_MODEL`.
7. **Smoke test.** The contributor runs a Bedrock canary against a
   synthetic fixture to confirm the credentials work.
8. **Audit-log entry.** Saranyaraj records the access grant in the
   handoff log with a structural-only entry (advisor name + date +
   IAM role added; never quote real data).

**Until all eight steps complete, the contributor operates against
synthetic data only.** Synthetic Sandra & Mike Chen is sufficient
for 90% of feature development.

## 4. Day-to-day operating discipline

These are the daily-recurring rules for anyone with real-PII access.

### Synthetic vs real default

- **Default to synthetic.** New features, new tests, new fixtures
  use Sandra & Mike Chen (or other synthetic personas) unless a real
  workspace is explicitly necessary.
- **Real-PII work requires a specific reason.** "I want to see how
  this looks with real data" is **not** a sufficient reason. "I'm
  reproducing a Sev-2 reported by an advisor on workspace X" is.
- **Synthetic + real never co-mingle in tests.** Tests use synthetic
  fixtures; real workspaces are tested via the upload-and-drain
  scripts in `scripts/demo-prep/`, not via `pytest` fixtures.

### Debug logging

- **Never log raw client values to stdout, stderr, or repo files.**
  If you need to log a structural summary (e.g., "extracted N facts,
  M reconciled"), use counts and structural shapes, not values.
- **Bedrock debug logging** (`MP20_DEBUG_BEDROCK_RESPONSES=1`)
  writes responses to `MP20_SECURE_DATA_ROOT/_debug/` only. Never
  pipe these logs to stdout or commit them.
- **Django logs** are configured (in `web/mp20_web/json_logging.py`)
  to not log request bodies. If you find a code path that does,
  fix it.

### Communication

When discussing real-PII work in Slack / Linear / email / commit
messages / handoff-log entries:

- **Use structural counts, never values.** "12 docs uploaded, 285
  facts extracted across 10 reconciled docs" is fine. "Client X has
  $620K in RRSP" is not.
- **Use placeholders.** "the 28-merge-candidate real-PII workspace,"
  "client_a's KYC form," "a real-PII couple workspace" — never the
  actual surname.
- **Reference UUIDs, never names.** `workspace bfb6027c-...` is OK.
  `<RealSurname> workspace` is not (in artifacts that leave the
  secure root; internal Slack between Mission-Aligned Team can be
  more permissive).

### Commits and PRs

- **Never commit real client data.** The `.gitignore` blocks the
  obvious paths (`MP20_SECURE_DATA_ROOT` is outside the repo). But
  test outputs, debug logs, and copy-pasted error messages can
  leak in via PR diffs.
- **Review every PR diff for placeholder discipline.** If a real
  surname snuck into a doc string or a comment, fix it before
  merging.
- **Commit messages don't quote real data.** "Fix entity alignment
  for over-fragmented workspaces" is fine. Specific examples go
  through structural summary only.

### Manual entry

- **The manual-entry escape hatch** is the right answer when
  extraction fails on a real document. Don't try to coerce the
  extractor; mark the doc `manual_entry` and have the advisor
  type the facts in directly.
- **Manual entries are audit-tracked** like any other fact.

## 5. The "never" list

Hard prohibitions:

- **Never paste real client values into Slack** (any channel,
  including DMs). Even a single account number or a single quote
  from a doc.
- **Never paste real client values into Linear** (ticket
  descriptions, comments, attachments).
- **Never paste real client values into commit messages** — these
  are version-controlled and replicate to GitHub.
- **Never paste real client values into project memory**
  (`~/.claude/projects/.../memory/`). Memory persists across
  sessions; a leak there propagates indefinitely.
- **Never copy real raw bytes into the repo** (test fixtures,
  doc folders, debug outputs). The secure root is the only
  permitted location.
- **Never log real client values to stdout** — Docker collects
  stdout into log files that may be retained.
- **Never use `str(exc)` in DB columns, response bodies, or
  audit metadata.** Use `safe_audit_metadata`,
  `safe_response_payload`, and `failure_code_for_exc` from
  `web/api/error_codes.py`. The CI guard
  (`scripts/check-pii-leaks.sh`) enforces this; if you find
  yourself fighting the guard, you're doing it wrong.
- **Never share Bedrock responses outside `MP20_SECURE_DATA_ROOT/_debug/`.**
  The debug logs contain raw LLM outputs which may carry real PII.
- **Never share screenshots of real client workspaces** in chat /
  Linear / email. Synthetic screenshots are OK.

## 6. Incident procedure

A PII leak is a **Sev-1** incident regardless of size.

If you discover a leak:

1. **Stop.** Don't continue working in the affected area.
2. **Don't commit** any in-flight work that may have additional
   leaks.
3. **Don't share** the leak in public channels. DM Saranyaraj
   (tech lead) directly.
4. **Document** what you found, where, and when. Structural
   summary only.
5. **Wait for direction.** Saranyaraj + Lori coordinate the
   response.

The response procedure follows
[`../agent/pilot-rollback.md`](../agent/pilot-rollback.md) §1
(severity classification) + §8 (post-incident audit).

If the leak is in the audit log (the most consequential class —
audit immutability means it can't be redacted): the response is
canon-significant. Lori and Amitha lead the compliance review.

## 7. Frequently violated patterns (from handoff-log lessons)

Patterns the team has paid to learn. If you find yourself doing
any of these, stop and reset:

| Pattern | What goes wrong | What to do instead |
|---|---|---|
| `last_error = str(exc)` on a model field | Exception text may carry account numbers, addresses, SINs from the underlying data | Use `safe_exception_summary(exc)` → returns `"ClassName:code"` only |
| `return Response({"detail": str(exc)})` in a DRF view | Same risk in HTTP response bodies | Use `safe_response_payload(exc)` |
| `metadata={"error": str(exc)}` in `record_event` | Same risk in audit metadata | Use `safe_audit_metadata(exc)` |
| `print(extracted_text[:200])` for debug | Stdout captured by Docker logs; persists | Use structural counts; or write to `MP20_SECURE_DATA_ROOT/_debug/` |
| `git add MP2.0_Clients/` accidentally | Real raw files committed | `.gitignore` blocks the obvious paths; `MP20_SECURE_DATA_ROOT` must be outside the repo |
| Slack screenshot of a real workspace | Image-format real PII in chat | Use synthetic Sandra & Mike Chen for screenshots |
| Pasting a Bedrock failure traceback into Linear | Traceback may contain extracted text | Reproduce against synthetic, then paste the synthetic traceback |
| Naming a feature branch after a real client | Branch names visible in CI logs / GitHub | Use a synthetic name or a UUID prefix |
| A test fixture that copies a real document | Real PII in version control | Synthesize a structurally-similar test fixture |

## 8. CI guards (your safety net)

The following CI checks run on every push to `main` and every PR.
They catch the most common reintroductions of forbidden patterns:

- **`scripts/check-pii-leaks.sh`** scans `web/`, `extraction/`,
  `integrations/` for `str(exc)` in DB columns / response bodies /
  audit metadata, plus routing-number / phone / address patterns.
  Test files are exempted.
- **`scripts/check-vocab.sh`** scans for banned vocabulary
  (sleeve, reallocation, low/medium/high risk, etc.) — vocabulary
  discipline overlaps with PII because real client surnames carry
  a vocabulary risk too.
- **`scripts/check-openapi-codegen.sh`** isn't PII-specific but
  catches a related class of bug: silent backend ↔ frontend type
  drift that can produce serializer-level PII leaks.

If a CI guard fails on your PR, **don't bypass it.** Fix the
underlying issue. The guards exist because regressions in their
domains were costly historically.

## 9. Quarterly review

This document and the broader regime are reviewed quarterly. The
next review is **2026-08-12** (three months after this revision).

The review checks:

- Are the 13 layers of the regime still in force?
- Have any patterns been added to the "frequently violated" list
  that should be promoted to CI guards?
- Have the team's working norms shifted in a way that affects this
  doc?
- Is the pilot rollout broader (Phase C, additional firms)? If so,
  does the regime need updating?

Updates land via PR with sign-off from Saranyaraj Rajendran,
Lori Norman, and Fraser Stark.
