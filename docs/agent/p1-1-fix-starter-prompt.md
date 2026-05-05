# Starter Prompt — P1.1 Multi-Entity Matcher Fix + UI Audit

**Authored:** 2026-05-05 (this artifact written at end-of-session before compact, post-`v0.1.3-pilot-quality-closure` tag).
**HEAD on entry:** `0d72e92` (worker-fix on `feature/ux-rebuild`; tag at `78cc997` is one commit behind).
**Branch:** `feature/ux-rebuild`, +16 commits past origin.
**User:** Saranyaraj Rajendran, technical lead at Purpose Inc., MP2.0 advisor console for Steadyhand.
**Mode:** auto-mode is ACTIVE per session contract; user says "I trust you fully to run through it all end to end." But user explicitly requested **plan mode** for THIS task (P1.1 fix + UI audit) because of scope + locked-decision-revision needed.
**Boot protocol:** Read this prompt → run pre-flight (§Pre-flight gate below) → `EnterPlanMode` → research per §Research checklist → `AskUserQuestion` for the 4-5 lock-in decisions in §Locked-decision revisions → `ExitPlanMode` for plan approval → execute.

---

## §1 — Mission in one paragraph

Just-shipped tag `v0.1.3-pilot-quality-closure` (78cc997) closed 14 gaps G1-G14 across 16 phase deliverables — **but real-PII end-to-end testing was deferred during the build phase and only run at end-of-session**. That late verification surfaced a HIGH-severity bug in G1 (multi-entity reconciliation): the Round 13 #2 LOCKED tightened-threshold matcher in `extraction/entity_alignment.py` over-fragments real Niesner data into **11 people / 30 accounts / 18 goals** when canon expects **2 people / ~5-7 accounts / ~3-4 goals** for the household. The plan's claim ("Niesner 16→≤6 conflicts + 2 distinct people") was correct as the goal but the implementation only achieves it on synthetic Hypothesis-generated facts, not on real LLM extraction. **Your job: design + ship a two-tier matcher (auto-merge high-confidence + merge-candidate medium-confidence + new-canonical low-confidence) + extend `ConflictPanel` for advisor-adjudicated entity merge candidates + walk every advisor-facing surface in real Chrome against real Niesner to surface any other gaps.** This is plan-mode work; user wants thorough deep research first.

---

## §2 — Why the matcher fails on real-PII (root cause analysis already done this session)

Round 13 #2 LOCKED requires for people merges: `name (≥60) AND DOB (+40) → 100 → MERGE` OR `name (≥60) AND last-name (+30) AND last4_account_number (+25) → ≥115 → MERGE` OR single-field → NEW canonical.

**On real Niesner extraction (517 facts, 13 docs):**
- Only **6 of 17** `people[*].date_of_birth` facts present (LLM only emits when document explicitly states DOB).
- Only **8 of 29** `accounts[*].account_number` facts present.
- Result: 11 of 17 person-facts have only `display_name`. Single-field → NEW canonical → 11 distinct people canonicals where there should be 2.

**Hypothesis property tests passed because they generate facts with all identity fields populated**; real LLM extraction obeys canon §9.4.5 ("only emit what's in the doc") — fundamentally different distribution. This is the synthetic-vs-real gap that end-to-end testing exists to catch.

**Sandra/Mike fixture works** because the seed loader writes canonical UPPERCASE `account_type` values directly; the wizard schema's `ACCOUNT_TYPES` enum forces uppercase via dropdown. So Sandra/Mike NEVER hit the real-extraction code path that produces lowercase strings. **Synthetic test fixtures are systematically different from real extraction output.**

---

## §3 — The proposed two-tier matcher (your starting point; refine in plan mode)

Three tiers replacing the current binary auto-merge / new-canonical:

### Tier 1: Auto-merge (high confidence)
Same as Round 13 #2 LOCKED:
- people: name+DOB OR name+last-name+last4_account_number
- accounts: account_number hash exact OR (type+institution+single-candidate)
- goals: name match (normalize_key) ≥80

### Tier 2: Merge-candidate (medium confidence; advisor adjudicates)
NEW. Emit entity-level merge candidates when:
- people: single-field name token match (≥60) WITHOUT contradicting field across both candidates
- accounts: type matches AND institution matches but multiple candidates (ambiguity)
- accounts: type matches AND |current_value| within 5% but multiple candidates
- goals: normalize_key(name) match ≥60 OR target+horizon close but neither high-confidence

"Contradicting field" rule: if candidate A has DOB=X and candidate B has DOB=Y where X≠Y → not a merge candidate (clearly different people). Same for `last_name`, `account_number_hash`, etc.

### Tier 3: New canonical (low confidence)
Below all thresholds OR at least one contradicting field.

### Persistence shape
`EntityAlignment` returns:
```python
@dataclass
class EntityAlignment:
    canonicals_by_prefix: dict[str, list[CanonicalEntity]]
    merge_candidates: list[MergeCandidate]  # NEW

@dataclass
class MergeCandidate:
    prefix: str  # "people" / "accounts" / "goals"
    canonical_a_index: int
    canonical_b_index: int
    score: int
    matched_fields: list[str]  # ["display_name"]
    contradicting_fields: list[str]  # [] or ["dob"] etc.
    confidence: Literal["medium"]  # "high" never reaches Tier 2
```

`reconcile_workspace` persists `merge_candidates` into `reviewed_state.merge_candidates` (NEW key). Backwards-compat: if absent in older states, frontend renders nothing.

---

## §4 — UI audit scope (the user explicitly asked for "very very deeply" thinking here)

User's exact words: "Also the UI does offer the intended experience from advisor level view to look into details, resolve and all that discussed in the plan and design doc (think very very deeply). We need to resolve all those."

**ConflictPanel extension (PRIMARY new UX):**
- Currently handles `reviewed_state.conflicts` = multi-source field disagreement (e.g., document A says DOB=1980, document B says DOB=1985 → advisor picks).
- NEW shape: `reviewed_state.merge_candidates` = entity-level alignment ambiguity (e.g., person A and person B might be the same; advisor picks "merge them" or "they're different").
- Render as separate group above existing field-conflict cards (priority: merge candidates first since they affect the count baseline of conflicts).
- Card states: unresolved → resolving → resolved (mirror existing ConflictCard pattern at `frontend/src/modals/ConflictPanel.tsx:388`).
- Actions per merge candidate: **Merge** (collapse to single canonical; re-emit all field facts under canonical_a_index) | **Keep separate** (record decision; never re-surface) | **Defer** (advisory; resurface at next reconcile).
- Bulk-action: "Merge all high-confidence candidates" button at top.
- Audit emission: `entity_merge_candidate_resolved` AuditEvent per advisor decision (counts + canonical_indices only; no PII).

**Other surfaces to walk against real Niesner (verify they handle real-data shape):**
1. **MissingPanel + AddBlockerInlineButton + ResolveAllMissingWizard (P3.3):** does field_path pre-fill correctly with real Readiness output? Does the wizard step-list actually surface real missing fields?
2. **StatePeekPanel allocation matrix (P3.4):** real Niesner has 30 accounts × 18 goals — does cap-8x8 + "+N more" overflow render legibly? Does the matrix gracefully handle pre-merge-candidate state?
3. **HouseholdPortfolioPanel + structured BlockerBanner (P11):** does `advisor_account_label` render with real Purpose RRSP / TFSA / LIRA accounts (NOT lowercase)? Real values show "$X.XK" or "$X.XM" correctly?
4. **UnallocatedBanner + Treemap unallocated tile (P12):** Niesner's 30 accounts include many held-away (non-Purpose); does banner only surface Purpose unallocated balance? Does treemap virtual `_unallocated` tile rendering scale with many accounts?
5. **AssignAccountModal (P13):** open from BlockerBanner CTA AND UnallocatedBanner AND treemap tile click — verify pre-focus on correct account_id; verify $+% live conversion works with real-account-value precision; verify new-goal inline-create round-trips.
6. **Wizard Step3Goals + Step5Review + Step5BlockerPreview (P14):** these never get used post-pilot since real intake is via doc-drop. But during demo, advisor walks Wizard for synthetic intake — verify allocation matrix preview + per-account % indicator work with real account_type values.
7. **Toggles (P6+P7):** ToggleFundAssetClass on AccountRoute/GoalRoute — verify asset_class_breakdown fallback when fund metadata missing. ToggleCurrentIdeal on HouseholdRoute — verify "ideal" treemap dataset reads `latest_portfolio_run.recommended_allocation` correctly when run exists.
8. **ContextPanel tabs (P3.2):** Right-rail History/Commits sub-tabs render against real audit-event timeline; pagination works at 50 events.
9. **Re-open + Re-reconcile flows (P2.1+P2.5):** click both buttons on a real committed Niesner household; verify atomic + 409 + workspace lifecycle.
10. **Pre-existing extraction bug surfaced this session:** every account has `Unsupported engine account type: tfsa/rrsp/lira/non_registered` blocker because LLM emits lowercase but engine canon expects uppercase. THIS IS NOT P1.1 SCOPE but **must be triaged separately**: either fix in extraction prompts (`extraction/prompts/statement.py:33-37`) OR add normalize step in `_merge_household_state`. Document as discovered + propose fix scope; coordinate with user before touching.

---

## §5 — Locked-decision revisions (use AskUserQuestion in plan mode)

These are the ones where you need explicit user lock-in BEFORE coding (cite as "Round 18 #N" when committing):

### Round 18 #1 — Two-tier matcher confirmation
Tier 1 auto-merge (Round 13 #2 unchanged) + Tier 2 merge-candidate (NEW; advisor adjudicates) + Tier 3 new-canonical. User picks: this design / different design / loosen Tier 1 (revert Round 13 #2).

### Round 18 #2 — Tier 2 thresholds
Should single-field name match (≥60) WITHOUT contradicting field always emit a merge_candidate? Or only when ≥2 prior contributing docs back the canonical? Trade-off: more candidates = more advisor work; fewer candidates = miss some real merges.

### Round 18 #3 — Account merge-candidate criteria
Real Niesner has 8/29 accounts with account_number, 21/29 with only (type, institution, value). Should Tier 2 surface every (type, institution) pair as a candidate? Or require value-within-5%? Or both as separate candidate types?

### Round 18 #4 — ConflictPanel UX placement
Merge candidates render: (a) above field-conflict cards as separate group "Possible duplicates"; (b) inline with field conflicts as a different card variant; (c) in a new sub-tab on right-rail Conflict view. Pick one (recommend (a) for visual hierarchy).

### Round 18 #5 — Bulk-action for high-confidence merge candidates
Should there be a "Merge all" button that auto-merges Tier 2 candidates with score ≥90 (just below Tier 1)? Trade-off: speed vs explicit-advisor-action discipline. Recommendation: NO bulk auto-merge for medium-confidence; only "Keep separate all" for cases advisor knows are clear (e.g., father+son household).

### Round 18 #6 — Account_type case mismatch (out-of-P1.1 scope)
Pre-existing bug: extraction emits lowercase, engine canon expects uppercase. Fix in (a) extraction prompt; (b) `_merge_household_state` normalize step; (c) defer to post-pilot improvements doc. Recommendation: (a) — root cause; one-prompt edit per file; cheaper than (b).

---

## §6 — Pre-flight gate (run before plan-mode entry)

Per plan v20 §A1.42 — 15 commands, ~3-5 min. Catches env drift.

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0

# 1. Git state
git status -sb
git log --oneline -5
git describe --tags HEAD  # expect "v0.1.3-pilot-quality-closure-2-g0d72e92" or similar

# 2. Sister + my tags verified
git tag -l | grep "v0.1.3"  # expect: v0.1.3-engine-display-polish + v0.1.3-pilot-quality-closure

# 3. Docker stack health
docker compose ps  # expect db + backend + worker UP
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/session/  # expect 200

# 4. Backend pytest pre-flight subset (fast)
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 docker compose exec -T backend bash -c "cd /app && uv run pytest --tb=no -q web/api/tests/test_audit_metadata_invariants.py extraction/tests/test_entity_alignment.py 2>&1 | tail -3"
# expect: ~30+ passing

# 5. Frontend gates
cd frontend && npm run typecheck && npm run lint && npm run test:unit -- --run 2>&1 | tail -3
# expect: 391+ Vitest passing

# 6. Static gates
bash scripts/check-pii-leaks.sh
bash scripts/check-vocab.sh
bash scripts/check-openapi-codegen.sh

# 7. Bedrock canary
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 docker compose exec -T backend bash -c "cd /app && uv run python -c 'from extraction.llm import bedrock_config_from_env, _bedrock_client; c = bedrock_config_from_env(); cli = _bedrock_client(c); r = cli.messages.create(model=c.model, max_tokens=10, messages=[{\"role\":\"user\",\"content\":\"ping\"}]); print(f\"OK {r.usage.output_tokens} tokens\")'" 2>&1 | tail -2
# expect: "OK 10 tokens"

# 8. Niesner workspace state (already uploaded last session)
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 docker compose exec -T backend bash -c "cd /app && uv run python -c \"
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.mp20_web.settings')
django.setup()
from web.api.models import ReviewWorkspace, ExtractedFact
w = ReviewWorkspace.objects.filter(label__icontains='Niesner').order_by('-created_at').first()
if not w: print('NIESNER NOT PRESENT — re-upload via upload_and_drain.py')
else:
    rs = w.reviewed_state or {}
    print(f'Niesner: status={w.status} people={len(rs.get(\\\"people\\\", []))} accounts={len(rs.get(\\\"accounts\\\", []))} goals={len(rs.get(\\\"goals\\\", []))}')
    print(f'  facts={ExtractedFact.objects.filter(workspace=w).count()} canonical_indexed={ExtractedFact.objects.filter(workspace=w).exclude(canonical_index=None).count()}')
\""
# expect: Niesner: status=review_ready people=11 accounts=30 goals=18 (the bug)
# Persistent baseline; the over-fragmentation should reproduce on re-reconcile UNTIL fix lands.
```

---

## §7 — Research checklist (in plan mode, before coding)

Phase 1 (Initial Understanding) — read these in order:

1. **`~/.claude/plans/you-are-continuing-a-playful-hammock.md`** — full plan, especially:
   - §A1.14 (22 user lock-ins rounds 7-12)
   - §A1.18 + §A1.19 (sister §3 awareness)
   - §A1.22 (P1.1 sub-agent prompt — this is where the matcher spec lives)
   - §A1.27 (P11 structured blockers; cross-phase contract)
   - §A1.50 (boundary edge cases; especially P1.1 row)
   - §A1.51 (cross-phase interaction matrix)

2. **`extraction/entity_alignment.py`** (687 LoC) — current matcher; understand:
   - `EntityAlignment` class at line 122 (return shape)
   - `align_facts()` at line 200 (entry point)
   - `_score_people()` at line 451 (where Round 13 #2 thresholds live)
   - `_score_accounts()` at line 489
   - `_score_goals()` at line 519
   - `_threshold_for()` at line 535

3. **`web/api/review_state.py`** — reviewed_state shape:
   - line 159: `state["conflicts"] = _conflicts(workspace)` (entry point for conflict surface)
   - line 1085: `raw_conflicts = conflicts_for_facts(facts, alignment=alignment)` (where alignment threads through)
   - line 1044: `"conflicts": []` default empty

4. **`frontend/src/modals/ConflictPanel.tsx`** (776 LoC) — UX extension target:
   - `ConflictPanel` at line 68 (entry component)
   - `ConflictCard` at line 388 (per-conflict card pattern; mirror for merge-candidate cards)
   - `CandidateRow` at line 694 (multi-source candidate row)
   - `BulkResolveBar` at line 317 (extend with merge-candidate bulk action if Round 18 #5 says yes)

5. **`docs/agent/design-system-research.md`** (918 lines, P0 deliverable) — UX patterns + counter-patterns + decision log; CITE before adding new visual treatment for merge candidates

6. **`docs/agent/design-system.md`** — design tokens + component inventory; reuse `--warning` for medium-confidence chip + existing card affordances

7. **`docs/agent/decisions.md`** — 111 prior locked decisions; especially #37 (audit metadata sanitization), #74 (sync auto-trigger), §3.5 (record_event canonical helper), §3.10 (theme-token grep gate), §3.13 (PII-focused review), §3.14 (90% coverage)

Phase 2 (Design) — propose:
- Two-tier matcher delta to `entity_alignment.py` (estimated +150-200 LoC)
- New `MergeCandidate` dataclass + persistence in `reviewed_state.merge_candidates`
- `ConflictPanel` extension: new `MergeCandidateCard` component + `MergeCandidateGroup` wrapper (mirrors `ActiveGroup` at line 211)
- New backend endpoint: `POST /api/review-workspaces/<id>/merge-candidates/<key>/resolve/` with body `{action: "merge" | "keep_separate" | "defer", rationale: str}`
- Audit event: `entity_merge_candidate_resolved` per §A1.23 schema
- Tests: extend `test_entity_alignment.py` with ~10 tier-2 cases (single-field match without contradicting → emit; with contradicting → don't emit; etc.)
- Frontend: extend `ConflictPanel.test.tsx` with ~6 cases for merge-candidate render + resolve

Phase 3 (Review) — verify proposal against:
- All 22+ locked decisions (Round 13 #2 specifically)
- Sister contract (§3 patterns)
- P11 cross-phase (BlockerBanner shouldn't render any blocker that depends on merge-candidate resolution)

Phase 4 (Final Plan) — write to plan file (only writable in plan mode); use ExitPlanMode for approval.

Phase 5 (Execute, post-approval) — implement + test + commit.

---

## §8 — Verification protocol (mandatory; this session's discovery: synthetic ≠ real)

**Tier 1 — synthetic (cheap, fast):**
- `pytest extraction/tests/test_entity_alignment.py` — must pass new tier-2 cases
- `pytest extraction/tests/test_entity_alignment_properties.py` — Hypothesis 3 properties at max_examples=10 must still pass
- `npm run test:unit` — frontend Vitest including new ConflictPanel cases

**Tier 2 — backend integration (medium):**
- `pytest web/api/tests/` full suite — backwards-compat must hold
- Coverage gate ≥90% on `extraction.entity_alignment` per sister §3.14
- Backend regression: 1,096+ pytest passing post-fix

**Tier 3 — REAL-PII Niesner (CRITICAL; this is where the bug lives):**
```bash
# Re-reconcile existing Niesner workspace (alignment re-runs):
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 docker compose exec -T backend bash -c "cd /app && uv run python -c \"
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.mp20_web.settings')
django.setup()
from web.api.models import ReviewWorkspace
from web.api.review_processing import reconcile_workspace
w = ReviewWorkspace.objects.filter(label__icontains='Niesner').order_by('-created_at').first()
reconcile_workspace(w, with_alignment=True)
rs = w.reviewed_state or {}
print(f'people={len(rs.get(\\\"people\\\", []))} accounts={len(rs.get(\\\"accounts\\\", []))} goals={len(rs.get(\\\"goals\\\", []))} merge_candidates={len(rs.get(\\\"merge_candidates\\\", []))}')
\""
```

**Acceptance criteria for Niesner post-fix:**
- people: ≤2 (auto-aligned at Tier 1) OR ≤2 with merge_candidates surfacing the rest as advisor-adjudicable
- accounts: ≤8 distinct canonicals (Niesner couple has ~3-5 Purpose + ~3-5 held-away) OR merge_candidates surface duplicates
- goals: ≤6 (couple has retirement + maybe house + emergency + maybe estate) OR merge_candidates
- merge_candidates: nonzero (proves Tier 2 fired)
- All decisions surfaced to advisor; nothing silently dropped

**Tier 4 — real-Chrome demo walk (UI audit):**
Run vite dev server (`cd frontend && npm run dev`), open `http://localhost:5173` in actual Chrome, walk:
1. Login → ClientPicker → Niesner reopen workspace
2. ConflictPanel renders: merge candidates above field conflicts; advisor clicks Merge on each pair → people count drops to 2
3. After merge resolution: re-check accounts, goals — confirm no over-fragmentation remains
4. MissingPanel + StatePeekPanel allocation matrix render legibly with post-merge data
5. Approve sections → commit → land on Niesner household
6. HouseholdRoute renders BlockerBanner with structured blockers + UnallocatedBanner if any
7. Click each BlockerBanner CTA → AssignAccountModal opens pre-focused
8. Walk full §A1.45 pilot day-1 journey

**Tier 5 — R10 7-folder sweep (per §A1.45 P10.3 — was skipped last session):**
```bash
uv run python scripts/demo-prep/r10_sweep.py --folders Niesner,Seltzer,Sandra/Mike,Gumprich,Herman,McPhalen,Schlotfeldt,Weryha --anonymize-folders
```
Bedrock spend cap $500 cumulative; halt at $400. Append spend ledger entry to `docs/agent/bedrock-spend-2026-05-03.md`.

**Halt-and-ask if:**
- Niesner post-fix still produces >4 people canonicals → matcher design needs revision
- Account_type case mismatch surfaces other blockers (extraction emits "non_registered" but engine wants "Non-Registered")
- Bedrock spend approaches $400
- ConflictPanel UX surfaces a contradicting LOCKED decision

---

## §9 — Critical files (organized by phase scope)

### Backend (matcher + persistence + endpoint)
- `extraction/entity_alignment.py` (687 LoC) — extend with Tier 2 + MergeCandidate dataclass
- `extraction/tests/test_entity_alignment.py` (24 tests) — extend with tier-2 cases
- `extraction/tests/test_entity_alignment_properties.py` (3 properties) — verify backwards-compat
- `web/api/review_state.py:159` — add `state["merge_candidates"]` population
- `web/api/review_state.py:1085` — `conflicts_for_facts(...)` already accepts alignment; extend to surface merge_candidates from alignment
- `web/api/review_processing.py` — `reconcile_workspace` already calls `align_facts(...)`; persists alignment via `canonical_index` on facts; extend to persist merge_candidates in reviewed_state
- `web/api/views.py` — new endpoint `POST /api/review-workspaces/<id>/merge-candidates/<key>/resolve/` with audit emission
- `web/api/serializers.py` — extend ReviewWorkspace serializer to include merge_candidates in output
- `web/audit/writer.py` — `record_event(action="entity_merge_candidate_resolved", ...)` per §A1.23

### Frontend (ConflictPanel extension)
- `frontend/src/modals/ConflictPanel.tsx` (776 LoC) — add `MergeCandidateGroup` + `MergeCandidateCard` components, mirroring `ActiveGroup` + `ConflictCard` patterns
- `frontend/src/modals/__tests__/ConflictPanel.test.tsx` — extend with 6+ cases for merge-candidate render/resolve/dismiss
- `frontend/src/lib/review.ts` — new `useResolveMergeCandidate` mutation hook + cache invalidation
- `frontend/src/lib/api-types.ts` — auto-regenerate via `npm run codegen` after backend serializer change
- `frontend/src/i18n/en.json` — new keys `review.merge_candidate.*` (title, copy, action labels)

### Tests
- Hypothesis property at `extraction/tests/test_entity_alignment_properties.py`: extend with `test_tier_2_emits_when_single_field_match_without_contradiction` + `test_tier_2_does_not_emit_when_contradicting_field_present`
- Backend integration: extend `web/api/tests/test_review_ingestion.py` with merge-candidate flow

### Docs (post-fix)
- `docs/agent/decisions.md` — add Round 18 #1-#6 lock-ins
- `docs/agent/handoff-log.md` — append-only entry covering this fix
- `docs/agent/post-pilot-improvements.md` — document account_type case fix scope IF deferred
- `CHANGELOG.md` — append `[v0.1.3.1-matcher-tier-2]` entry OR amend `[v0.1.3-pilot-quality-closure]` (user picks)

---

## §10 — Locked decisions still in force (don't violate)

22 from rounds 7-12 + 4 from round 13 + 4 from round 14 + 4 from round 15 + 4 from round 16 + 4 from round 17 = 38 user lock-ins. Highest-impact for this fix:

- **Round 8 #5** wizard hard-block — STAYS (P14 unchanged)
- **Round 8 #6** AssignAccountModal hard-require 100% — STAYS (P13 unchanged)
- **Round 8 #7** max 2 sub-agents in parallel — STAYS (use for tier-2 implementation if dispatching)
- **Round 9 #11** P11 structured blockers no bypass — STAYS
- **Round 13 #2** matcher tightened threshold — **REVISE** (this is the round-18 lock-in question; Tier 1 = current behavior; Tier 2 NEW)
- **Round 14 #3** TypedDict + DRF + ts-codegen — APPLIES to MergeCandidate shape
- **§A1.23** audit metadata schema (counts + UUIDs only; no PII) — APPLIES to `entity_merge_candidate_resolved`
- **§A1.40** PII-focused review at A7-equivalent — APPLIES post-fix
- **§3.5** `record_event` from `web/audit/writer.py` — APPLIES
- **§3.10** theme-token grep gate — APPLIES (use existing `--warning` for medium-confidence chip)
- **§3.14** 90% coverage gate — APPLIES

---

## §11 — Auto-mode session protocol (per user direction earlier this session)

User said:
> "I trust you fully to run through it all end to end with best course of action that should be backed by strong reasoning, thinking and judgement"

But also:
> "Let's do it in plan mode."

Resolution: **plan mode for design + research + lock-in questions**, then **auto-mode for execution post-approval**. ExitPlanMode triggers transition.

**Within plan mode:**
- Use Read + Grep + Bash (read-only) freely
- Use AskUserQuestion 1-3 times max for the round-18 lock-ins
- Don't ask plan-approval question via AskUserQuestion (use ExitPlanMode for that)
- Edit the plan file (`~/.claude/plans/...`) directly

**Within auto-mode (post-ExitPlanMode):**
- Dispatch sub-agents via Agent tool for parallel work where independent
- Commit per-phase per sister §X.10 protocol with `subagent: <name>` attribution
- Run §A1.47 cadence per commit (regression-coverage spec + perf budget + static gates)
- Halt + AskUserQuestion only on: locked-decision-revision attempts; Bedrock spend approaching $400; matcher post-fix still over-fragments
- Update CHANGELOG.md when ready to tag/push

---

## §12 — Anti-patterns burned in this session (don't repeat)

1. **Unit-test pass count ≠ feature works.** Sub-agents reported clean tests but the matcher over-fragments on real data because Hypothesis-generated facts have all fields populated; real LLM extraction doesn't. **VERIFY against real-PII before claiming a phase complete.**

2. **Worker container off after `docker compose up -d backend`.** The `up -d` with explicit service names doesn't bring up dependencies. Either always use `docker compose up -d` (no service arg) OR rely on the post-fix `scripts/reset-v2-dev.sh` which now brings up all three.

3. **Permission system blocks raw real-PII reads correctly.** Don't try to bypass — use `scripts/demo-prep/upload_and_drain.py` which is the canon-compliant path. Real client folder is at `/Users/saranyaraj/Documents/MP2.0_Clients/<surname>/`; the script reads + uploads via authenticated API.

4. **`Readiness` is a dataclass, not a dict.** Use `readiness.engine_ready` not `readiness["engine_ready"]`.

5. **Pre-existing bugs surface alongside your fix.** `account_type` lowercase case is a sister-tag baseline issue, not P1.1 regression. Triage separately; don't bundle the fix unless explicitly authorized.

6. **`tail -1` always returns 0 in shell pipes.** Don't write `until <cmd> | tail; do ...; done` loops — use `until <cmd>; do ...; done` for proper exit-code propagation.

7. **`tests pass` ≠ `feature shipped`. `bundle <290 kB` ≠ `bundle headroom for next phase`.** Verify each invariant against full state, not delta from prior commit.

---

## §13 — First concrete actions (in order)

1. **Read this prompt fully** (you're here).
2. **Read `~/.claude/plans/you-are-continuing-a-playful-hammock.md`** §A1.14, §A1.22, §A1.50 (P1.1 row), §A1.51 (P11×P14 cross-phase reference).
3. **Run pre-flight gate** (§6 above; 15 commands).
4. **Verify Niesner workspace exists with the bug** (last sub-step of §6 pre-flight).
5. **`EnterPlanMode`** — the user explicitly requested plan mode for this work.
6. **Phase 1 (Initial Understanding):** Read 7 files in §7 research checklist.
7. **Phase 2 (Design):** Draft two-tier matcher proposal.
8. **Phase 3 (Review):** Cross-check against 38 locked decisions.
9. **Phase 4 (AskUserQuestion):** 4-6 round-18 lock-ins per §5.
10. **Phase 5 (Final Plan):** Write to plan file; section §A1.60+ with new round-18 decisions.
11. **`ExitPlanMode`** for user approval.
12. **(Auto-mode post-approval) Implement:** matcher Tier 2 + persistence + ConflictPanel extension + endpoint + audit + tests.
13. **Verify on real Niesner** (Tier 3 acceptance criteria above).
14. **Walk advisor-facing surfaces in real Chrome** (§4 UI audit).
15. **Commit + update CHANGELOG.md.**
16. **Optional tag bump:** `git tag -a v0.1.3.1-matcher-tier-2 -m "..."` if user authorizes; otherwise leave on branch.

---

## §14 — What "done" looks like

Niesner workspace re-reconciled produces:
```
people=2 accounts=5 goals=4 merge_candidates=N (where N varies; advisor-adjudicable)
```

Real-Chrome walk:
- Advisor opens Niesner → ConflictPanel shows `Possible duplicates (N)` group at top
- Advisor clicks Merge on each high-confidence candidate → count drops to 2 people
- Field conflicts (existing P1.1 baseline) render below
- Approve all sections → commit → land on Niesner household with 2 distinct people
- HouseholdPortfolioPanel renders structured BlockerBanner (P11)
- UnallocatedBanner above sub-bar if any unallocated balance (P12)
- Sub-bar action CTAs visible: Realign + Re-open + Re-reconcile + ToggleCurrentIdeal (P2.1+P2.5+P7+sister)
- Treemap renders (P12 unallocated tile if applicable)
- AssignAccountModal opens from any CTA (P13)
- All audit events emit per §A1.23 (counts + UUIDs only)
- All static gates clean (vocab + PII + OpenAPI + ruff)
- All 1,096+ backend pytest pass
- All 391+ Vitest pass + ~16 new tests for tier-2 + ConflictPanel extension
- Bundle ≤290 kB gzipped
- Hypothesis 3+ properties pass at max_examples=10
- §A1.40 PII-focused review post-fix: 0 BLOCKING + 0 CRITICAL

If all the above hold: cut tag `v0.1.3.1-matcher-tier-2` (or amend `v0.1.3-pilot-quality-closure`; user picks). Pilot launch ready.

---

## §15 — Tone and discipline

User has been burned by overconfident "ship-ready" claims. Pattern: every "Is everything done?" challenge has caught a real bug. Be candid about uncertainty. Do not overclaim test coverage. When asked "is this ready?", answer with evidence (gate results, regression test ids, screenshot artefacts, real-PII verification counts), not opinions.

If a sub-phase looks like it'll force a corner cut: that's an `AskUserQuestion` trigger, not a unilateral decision. Quality > speed; honest audit > confident restatement; real-PII discipline > all.

The user's exact words at start of execution this session: "Take all the time, resource and energy to make sure this is done right". That stance still holds.

---

## §16 — One final reminder

**The matcher passed every test in this session except the one that mattered: real Niesner.** That happened because the test pyramid was synthetic-only at the unit + property + integration layers; real-PII verification was deferred to "demo dress rehearsal" and ultimately skipped. Don't repeat. **Real-PII verification is mandatory pre-merge for any matcher / extraction / reconciliation change.** Bedrock cost is small (~$0.13 per Niesner re-extract); the cost of NOT verifying is much higher (bugged tag, advisor demo failure, lost trust).

End of starter prompt. Read `~/.claude/plans/you-are-continuing-a-playful-hammock.md` next, then run pre-flight gate, then `EnterPlanMode`.
