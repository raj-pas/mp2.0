# R10 Sweep Results — Phase 4 Tool-Use Migration (2026-05-02)

**Trigger:** Phase 7 R10 sweep against the new tool-use extraction
path (HEAD `6b0ea9b`) following two canary fixes for the Seltzer
KYC regression (confidence-floor cap loosened + `multi_schema_sweep`
classification routes to `generic` builder).

**Scope:** 12 documents across 3 real-PII workspaces in DB
(Seltzer + Weryha + Wurya). Original 7-folder R10 set
(Gumprich, Herman, McPhalen, Niesner, Schlotfeldt, Seltzer,
Weryha) is partial — only 2 of those + Wurya present in DB.
Re-uploading the other 4 needs original raw files which live
outside this session's reach.

**Bedrock cost:** ~$3 across all 12 docs (estimated).

---

## Per-doc structural diff

Real-PII discipline (canon §11.8.3): structural counts only;
no values, no quotes.

| Doc | Type | Pre facts | Post facts | Δ | Pre conf | Post conf | Pre deriv | Post deriv |
|---|---|---|---|---|---|---|---|---|
| CS Address.pdf | identity | 12 | 8 | −33% | 12 high | 7 high + 1 medium | 12 extracted | 7 extracted + 1 inferred |
| CS DOB.pdf | identity | 23 | 5 | −78% | 21 high + 1 medium + 1 low | 5 high | 22 extracted + 1 inferred | 5 extracted |
| CS KYC.pdf | kyc | 74 | 27 | −64% | 58 high + 16 medium | 27 medium | 57 extracted + 17 inferred | 27 extracted |
| CS Profile.pdf | kyc | 28 | 16 | −43% | 20 high + 8 medium | 11 high + 4 medium + 1 low | 22 extracted + 6 inferred | 12 extracted + 4 inferred |
| Client notes Seltzer | meeting_note | 78 | 38 | −51% | 70 high + 7 medium + 1 low | 31 medium + 6 low + 1 high | 68 extracted + 10 inferred | 33 extracted + 5 inferred |
| AW Address.pdf | identity | 12 | 2 | **−83%** | 12 high | 1 high + 1 medium | 12 extracted | 1 extracted + 1 inferred |
| AW Client Notes | meeting_note | 56 | 30 | −46% | 39 high + 16 medium + 1 low | 27 medium + 2 low + 1 high | 47 extracted + 7 inferred + **2 defaulted** | 29 extracted + 1 inferred |
| AW DOB.pdf | identity | 24 | 7 | −71% | 19 high + 5 medium | 5 high + 2 medium | 22 extracted + 2 inferred | 5 extracted + 2 inferred |
| AW KYC.pdf | kyc | 41 | 21 | −49% | 37 high + 4 medium | 20 high + 1 medium | 34 extracted + 7 inferred | 20 extracted + 1 inferred |
| AW Profile.pdf | kyc | 24 | 21 | −13% | 23 high + 1 medium | 19 high + 2 low | 23 extracted + 1 inferred | 21 extracted |
| MN Client Notes | meeting_note | (n/a; 1st extraction post-fix) | 34 | n/a | n/a | 32 medium + 2 low | n/a | 33 extracted + 1 inferred |
| MN DOB.pdf | identity | (n/a; 1st extraction post-fix) | 6 | n/a | n/a | 6 medium | n/a | 6 extracted |

## Per-workspace totals

| Workspace | Pre | Post | Δ |
|---|---|---|---|
| Seltzer | 168 | 94 | −44% |
| Weryha | 157 | 81 | −48% |
| Wurya | (0; failed pre-Phase-4) | 40 | n/a (NET WIN) |
| **Total** | 365 | **215** | **−41%** |

## Quality signals (canon §9.4.5 + §11.4)

**Wins:**
- **Hallucinated section paths eliminated.** Pre-sweep had
  facts at `identification.*`, `kyc.*`, `next_steps.*`,
  `promotions.*`, `real_estate.*`, `advisor.*`,
  `external_assets.*`, `liabilities.*` — none are in the
  canonical schema; the engine never reads them. Post-sweep:
  all facts on canonical paths only.
- **Defaulted facts gone.** Pre-sweep AW Client Notes had 2
  facts with `derivation_method="defaulted"` (canon §9.4.5
  prohibits default-to-make-it-fit). Post-sweep: 0 defaulted
  facts across all 12 docs.
- **Inferred-fact count cut sharply.** Pre: ~52 inferred across
  the 10 docs. Post: ~16 inferred. The remaining inferred facts
  appear in identity + KYC docs where structural inference is
  reasonable (e.g., people[0] inferred from account-holder block).
- **Confidence calibration honest.** Pre had a lot of "high"
  facts that were actually inferred (high-confidence inferred
  is a contradiction). Post: high-confidence facts cluster on
  truly-explicit data; medium clusters on inferred / capped
  by classification.
- **Wurya net win.** Pre-Phase-4 the Wurya workspace had 0 facts
  (failed extraction). Post: 40 facts cleanly extracted.

**Losses:**
- **AW Address.pdf 12 → 2 facts (−83%)** is too aggressive. An
  address doc should produce >2 facts (name + DOB + address parts).
  The new prompt is over-conservative on narrow single-page
  docs. Phase 9.2 (Permissive base + strict per-type) targets
  this.
- **CS DOB.pdf 23 → 5** lost most of the spread. The pre-extraction
  pulled household + accounts + behavioral_notes from a DOB doc —
  some legitimate (people[0].dob, household.display_name from
  account-holder block), some spurious. Post-fix kept only 5
  people facts. Phase 9.2 + 9.3 should recover legitimate
  spread without re-introducing spurious.
- **Client notes -51%, AW Client Notes -46%** is large for
  meeting-note docs. Meeting notes are dense free-form narrative
  with lots of legitimate inference signal. Phase 9 should
  consider per-doc-type policies (J) — meeting_notes get more
  permissive inference + behavioral_notes capture.

## Decision (per user direction 2026-05-02)

> "Accept new path; commit fixes; expand to full 7-folder R10
> sweep ... and write probably a last phase to once all the work
> is done to iterate over this issue and see if we can improve
> facts all the while maintaining fidelity and total accuracy."

Decision: **ship Phase 4 as the pilot's extraction path** despite
the −41% fact-count regression, because:
1. Eliminating ~40 hallucinated section paths is a cleanliness win
   the engine + advisor surface inherits.
2. Eliminating 2 `defaulted` facts is a canon §9.4.5-correctness
   win.
3. Cutting inferred-fact count from ~52 to ~16 is a hallucination
   reduction win.
4. The remaining fact volume (215 across 12 docs = ~18 facts/doc
   average) is sufficient for advisor review pre-pilot. The
   advisor commit-rate + manual-entry-rate during pilot week 1
   will validate this.

Phase 9 (`docs/agent/phase9-fact-quality-iteration.md`) plans the
post-pilot iteration to recover legitimate signal in the −41%
without re-introducing hallucinations.

## Phase 9 inputs from this sweep

The sweep gives Phase 9 a precise diagnostic baseline:
- Per-doc-type recall regressions (Address PDFs hit hardest;
  meeting notes need richer behavioral_notes channel; KYC does
  OK).
- Per-section recall: `goals[*]` + `goal_account_links[*]` +
  `household.*` need targeted improvement; `people.*` +
  `accounts.*` are tracking close to baseline.
- Confidence calibration: post-fix confidence distribution is
  honest (no high-confidence on inferred); the cap-at-rank+1
  semantics is working as designed.
