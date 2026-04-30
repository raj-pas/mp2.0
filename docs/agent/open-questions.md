# MP2.0 Open Questions

This file is the agent-facing planning subset of Part 15 in
`MP2.0_Working_Canon.md` v2.3. The canon remains authoritative if this summary
falls behind.

## Real-PII Authorization Status

**Resolved for limited-beta scope (revisit 2026-05-21):** as of 2026-04-30,
real Steadyhand client PII is **authorized for limited-beta, local-production-like
operation** under the canon §11.8.3 defense-in-depth regime. Current scope:
two roles (`advisor`, `financial_analyst` per `web/api/access.py:8-9`) and the
current local-production-like deployment. Broader rollout (more advisors,
broader user population, staging/production deployment) requires Lori + Amitha
review; revisit 2026-05-21.

| Item | Status |
| --- | --- |
| Authorization basis for real-PII use (Q24) | **RESOLVED for limited-beta scope.** Broader rollout requires Lori + Amitha review. |
| Bedrock ca-central-1 enablement (Q25) | **In active operational use;** formal Purpose IT sign-off owed but not gating limited-beta operation. |
| Defense-in-depth privacy regime (canon §11.8.3) | **In operation;** formal Amitha review pending broader rollout. |
| Pre-LLM pseudonymization (former Q26) | **RETIRED** by canon §11.8.3 substitution. Not reintroduced unless Amitha specifically requires. |

## Phase B / Real-PII Items Still Pending

These remain on the radar as loose ends or as gates for broader rollout, but
none gate limited-beta operation under the current scope.

| Question | Owner | Phase Impact |
| --- | --- | --- |
| Purpose data-classification tier for client PII | Purpose IT | Validates or tightens storage/logging defaults; revisit at broader rollout |
| Real-PII retention/disposal trigger | Team | Local version-bump disposal/report command exists; legal/IT policy trigger still open |
| Som/IS demo audience handling for quasi-identifiers | Lori | Confirm before any real-derived persona is shown to a non-advisor audience |
| Lori backup for the Croesus/file-drop data path | Lori + team | Operational continuity; needed before broader rollout |

## Engine / Portfolio Questions

| Question | Owner | Phase Impact |
| --- | --- | --- |
| Specific weighting for household x goal risk composite | Team | Blocks final risk methodology; code should parameterize |
| Compliance risk-rating thresholds | Lori + Saranyaraj | Phase B exit criterion |
| Capital market assumptions source | Saranyaraj + Fraser | Fraser v1 fixture is seeded for scaffold; defensible pilot source still blocks real-client recommendations |
| Real sleeve numerical inputs | Saranyaraj + Nafal | Placeholder acceptable for scaffold; not pilot |
| Bond-only sleeve launch path | Salman + Tom | Product-side gap; improves frontier materially |
| Fund-of-funds collapse match-score threshold | Saranyaraj + Fraser | Needed for Founders/Builders execution suggestion |
| Drift/rebalance exact thresholds | Team | Default 3-5% or material event; refine before pilot |
| Real vs nominal dollars in projections | Team | Open for long-duration goal reporting |
| Plan-to-portfolio iterative recursion with Conquest Monte Carlo | Team | V2 candidate; v1 remains single-pass |

## Extraction / Review Questions

| Question | Owner | Phase Impact |
| --- | --- | --- |
| Real meeting-note shape and conventions | Lori -> Raj | Get one real note before finalizing prompts |
| Reconciliation strategy beyond most-recent-wins | Team | Post-MVP refinement unless IS validation exposes issues |
| KYC/statement extraction schema details | Raj + Lori | Needed after meeting-note path works |
| Source-document review UX details | Raj + Lori | Layer 5 trust surface; Phase A/B load-bearing |

## Advisor Workflow / UI Questions

| Question | Owner | Phase Impact |
| --- | --- | --- |
| Whether clients see the three-tab view or only advisor/report slices | Lori vs Fraser | Resolve before Phase C |
| Exact pilot-mode disclaimer wording | Lori + Amitha | Phase B exit criterion |
| Inline override-note UX | Saranyaraj + Lori | Needed to avoid workflow fatigue |
| CMA admin permissions model | Saranyaraj + Lori | V1 uses `financial_analyst`; confirm production named users/governance before pilot |
| Reporting/portal scope and Andrew team handoff | Andrew + team | Blocks full pilot experience beyond MAT app |
| Behavioral-bucket schema within Tier 1/2/3 reporting | Lori + Saranyaraj | Partially resolved; needs concrete assignment rules |
| Client value proposition for disclosing external holdings | Lori | Needed to drive useful disclosure rates |
| User testing proxy strategy | Team | Open; non-engaged spouses floated as possible testers |

## Pilot Operations Questions

| Question | Owner | Phase Impact |
| --- | --- | --- |
| Identity and commitment of the 3-5 pilot advisors | Lori | Confirm before Som demo / Phase C planning |
| Phase B sign-off owner and disagreement process | Fraser + Lori + Raj | Needed so pilot gate is real |
| Feedback channel and triage owner | Team | Phase B exit criterion |
| IS pilot training material format and walkthrough | Lori | Phase B exit criterion |
| Pilot success metrics final targets | Fraser + Lori | Current Section 13.0.3 targets are defaults |
| Pilot duration and exit decision | Fraser + Som | Working assumption is 6 weeks |

## Integration / Infrastructure Questions

| Question | Owner | Phase Impact |
| --- | --- | --- |
| Conquest API feasibility for v2 | Saranyaraj | V1 uses file/manual entry |
| PDF rendering library for client outputs | Raj | Default defer to week 2 |
| Fast-forward simulator strategy | Team | Pre-baked acceptable for Som demo; revisit for pilot |
| ECS namespace, IAM boundary, tagging convention | Purpose IT | Production deployment |
| Federation pattern and future OIDC provider choices | Purpose IT + Raj | Auth Phase 2+ |
| Logging/observability destination and audit query requirements | Purpose IT | Production readiness |
| CI/CD approval path into ECR/ECS | Purpose IT | Production readiness |

## Code Drift vs Canon

Observations from the 2026-04-30 codebase walk where current code differs from
canon spec or canon-expected behavior. None are critical-path; tracked here so
a future implementation session can address.

| # | Item | File / location | Disposition |
| --- | --- | --- | --- |
| 1 | `integrations/llm/` directory orphaned — `client.py` raises `NotImplementedError`, providers are stubs; working Bedrock client lives at `extraction/llm.py` | `integrations/llm/{client,anthropic_provider,bedrock_provider}.py` | Delete or rewire as thin re-exports. Confirm with Saranyaraj before either. |
| 2 | Fund-vs-asset-class look-through toggle missing in UI (canon §8.7) — `fund_type` exists in payload, no UI control | `frontend/src/App.tsx` | Phase B work item. |
| 3 | Engine universe placeholder CMA values | `engine/sleeves.py:1-5` (`assumptions_source="illustrative_phase_1_placeholder"`) | Tied to canon Q15 (CMA source); upstream of Phase C pilot recommendations. |
| 4 | `engine/compliance.py` Phase-1 stub maps `equity_weight ≤ 0.25 + vol ≤ 0.06 → "low"` else medium/high (hardcoded) | `engine/compliance.py` | Tied to canon Q3 (compliance risk-rating thresholds); Phase B exit blocker. |
| 5 | `integrations/croesus/client.py` returns mock 40/60 holdings | `integrations/croesus/client.py:4-22` | Canon-aligned for now (canon §9.4.3 file-drop in MVP); replace when canon Q9 advances. |
| 6 | `integrations/{conquest,custodian,pdf_render}/` are empty `__init__.py` | `integrations/{conquest,custodian,pdf_render}/` | Canon Part 10 placeholders; not blocking. |
| 7 | `tax_drag_version="neutral_tax_drag.v1"` stub on CMASnapshot | `engine/schemas.py:179` | Canon §4.5 says zero drags acceptable for v1; canon-aligned. |
| 8 | Engine boundary purity has no CI grep-check | engine/* | **Resolved 2026-04-30 R0** — `engine/tests/test_engine_purity.py` enforces; runs in pytest. |
| 9 | External-holdings risk-tolerance dampener (canon §4.6a) not implemented | `engine/risk_profile.py` (docstring TODO) | **Deferred to Phase B per 2026-04-30 plan locked decision #11.** v36 mockup itself does not implement the dampener; it applies a projection-time penalty (μ × 0.85, σ × 1.15 for external) which is implemented in `engine/projections.py`. Awaits team-confirmed dampener formula. |
| 10 | Backend Docker image stale w.r.t. R0 deps (`django-csp`) | `Dockerfile` baked venv at `/opt/mp20-venv` | **Resolved 2026-04-30 deeper smoke** — `docker compose build backend` succeeded cleanly (78s); rebuilt container starts, runs migrations + seed + bootstrap, serves `/api/session/` 200. `docker compose up --build` is the validated fresh-clone entry point. |
| 11 | Fund-id naming chaos: 4 coexisting conventions across engine / CMA / persona / frontend | `engine/sleeves.py` (`SH-Sav`), `web/api/management/commands/seed_default_cma.py` (`sh_savings`), persona seed (`income_fund`), frontend `lib/funds.ts` normalizer | **Workaround in place 2026-04-30**: `frontend/src/lib/funds.ts` `canonizeFundId()` maps every variant to canon `SH-X` so palettes work regardless of source. **Underlying fix**: locked decision #19 calls for Sandra/Mike fixture regeneration + fund-id unification; deferred to R7. Backend should also be unified — `engine/sleeves.SLEEVE_REF_POINTS` keys (`SH-Sav`) don't match seeded `fund_assumptions.fund_id` (`sh_savings`); the `sleeve-mix` preview returns `SH-Sav` while `treemap` mode `by_fund` returns `cash_savings` etc. from holdings. Tracker for the backend unification; R3 frontend is unblocked via the normalizer. |
| 12 | Optimizer frontier-efficiency invariant violation (Hypothesis) | `engine/frontier.py` — `compute_frontier` | **Resolved 2026-04-30 R4 commit.** Hypothesis falsifying example (`returns=[0.0625, 0.01, 0.01]`, `volatilities=[0.25, 0.125, 0.03125]`, `rho=0.0`) showed the `efficient` slice could include dominated points when degenerate subsets produced near-equal-return solutions with non-monotone variance. Added a Pareto filter (`_pareto_filter`) to `compute_frontier` that drops any point dominated by another (≥ return AND < vol, within 1e-9 tolerance). 313 pytest passing. |
| 13 | Realignment BIG_SHIFT threshold left over from pre-canon-1-5 scale | `web/api/wizard_views.py` — `RealignmentView` line ~542 (`if abs(after - before) > 5.0`) | **Surfaced 2026-04-30 pre-R6 smoke.** The BIG_SHIFT detector compares `_blended_score(account)` before vs after realignment, but `_blended_score` is canon-1-5 weighted (max value 5), so the absolute delta can never exceed `5.0` — meaning `big_shifts` will always be empty in practice. Locked decision #15 calls for the BIG_SHIFT banner in the realignment compare screen, but with the current threshold the banner will never trigger. **Fix options**: (a) lower threshold to e.g. `> 1.0` for canon 1-5 (one full descriptor band shift); (b) scale `_blended_score` to 0-100 internally and keep 5.0 threshold. Either way it's a one-line backend change. R6 frontend can ship the banner UI; backend threshold fix is a small follow-up that R6 can include if scope allows, otherwise tracked as a Phase B exit item. |
