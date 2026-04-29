# MP2.0 Open Questions

This file is the agent-facing planning subset of Part 15 in
`MP2.0_Working_Canon.md` v2.3. The canon remains authoritative if this summary
falls behind.

## Phase B / Real-PII Blockers

Secure-local browser upload now exists for controlled local review, but these
remain blockers for any broader pilot, staging deployment, or sharing of
real-derived outputs.

| Question | Owner | Phase Impact |
| --- | --- | --- |
| Written authorization basis for using real Steadyhand client documents in product development | Lori + Amitha | REAL-PII BLOCKER before any real file is copied |
| Bedrock ca-central-1 enablement on Purpose AWS account | Saranyaraj + Purpose IT | REAL-PII BLOCKER before real-derived extraction |
| Purpose data-classification tier for client PII | Purpose IT | REAL-PII BLOCKER; validates or tightens storage/logging defaults |
| Per-persona pseudonym mapping storage mechanism | Raj | Must be chosen before first real file |
| Quasi-identifier handling during pseudonymization | Lori + Raj | Affects extraction quality and privacy risk |
| Real-PII retention/disposal trigger | Team | Local version-bump disposal/report command exists; legal/IT policy trigger still open |
| Som/IS demo audience handling for quasi-identifiers | Lori | Confirm before any real-derived persona is shown |
| Lori backup for the Croesus/file-drop data path | Lori + team | Needed before offsite kickoff / Phase A execution |

## Engine / Portfolio Questions

| Question | Owner | Phase Impact |
| --- | --- | --- |
| Specific weighting for household x goal risk composite | Team | Blocks final risk methodology; code should parameterize |
| Compliance risk-rating thresholds | Lori + Saranyaraj | Phase B exit criterion |
| Capital market assumptions source | Saranyaraj + Fraser | Blocks real-client pilot recommendations |
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
| CMA admin permissions model | Saranyaraj + Lori | Admin-only flag is v1 minimum |
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
