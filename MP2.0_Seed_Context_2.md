# MP2.0 — Seed Context File

**Purpose Investments | Model Portfolios 2.0**
*Canonical reference for application & platform development*

> **How to use this file.** This is the single source of truth for anyone — human or AI agent — being onboarded to build, extend, or test the MP2.0 platform. It compresses the original Sep 2024 Purpose Memo, the Apr 2026 offsite decisions, the Steadyhand client-data framework, the CSM nudge framework, and the team's working architecture into one document. Read top-to-bottom for orientation; use the section anchors as reference once oriented. Where the offsite resolved or evolved a position from the original memo, the offsite position governs and is flagged inline.

---

## 0. Quick orientation (one page)

**What we're building.** A wealth-management platform that turns a client's financial plan into a personalized investment portfolio, demonstrates how that portfolio supports the plan under uncertainty, and continuously updates both as the client's life evolves. Initial deployment context: Steadyhand (MFDA dealer, in-house mutual funds). Subsequent rollouts: Harness, 3rd-party IIROC/CIRO advisors, Group RRSP / DC pensions, DIY.

**The core question MP2.0 helps answer.** *"How should I structure my portfolio today to best support my financial plan and goals?"*

**The shift we're driving.** From *"How did your portfolio perform vs. benchmark?"* to *"Am I going to achieve my goals?"* — Som Seif's framing.

**Architecture, in one sentence.** A small set of standardized "sleeve" funds (the building blocks) are blended in personalized ratios driven by the client's living financial plan, with sleeve internals updated independently by a Macro Insight Layer. Fraser's analogy: *paint mixing*. Sleeves are molecules made of atoms (underlying holdings); blends are alloys.

**The 6-stage loop.**
1. **Onboarding** — KYC/AML, risk profiling, goals, life context.
2. **Living Financial Plan** — goals, cash flow, projections, Monte Carlo. Trust is made or broken here.
3. **Portfolio Construction** — hybrid sleeve-blend engine. Plan drives blend ratios.
4. **Automated Execution** — drift detection, tax-aware rebalancing, custodian APIs. Phase 2+.
5. **Outcomes Reporting** — *"Am I going to be okay?"* Plan progress + portfolio + market context.
6. **Continuous Loop** — life events and observed behaviour feed Stage 2. This is where MP2.0 becomes sticky.

**MVP demo scope (offsite outcome).** Stages 1 → 2 → 3 → 5. Execution is Phase 2+. The April/May 2026 Purpose offsite demo must be a working application — not slides — that mechanically traverses: client intake → personalized portfolio → progress against plan.

**Stack (offsite decision).** Python + Django, modular engine, mock APIs / mock data where real integrations aren't available, audit log on every input → output decision for explainability.

**Three stakeholders, every screen.** Client, Advisor, Purpose (the firm). Every UI and report needs to resolve all three.

---

## 1. Strategic context

### 1.1 Why this initiative exists
Purpose Unlimited's top-level OKRs that this initiative directly serves:
- Lead in the Market — industry-leading and transforming products and services.
- Make Purpose THE partner to financial advisors in Canada.
- Spark Innovation — strategic experimentation.
- WOW our Clients by delivering ONE Purpose.

The founding mission is to help investors achieve their ultimate life outcomes. The MP2.0 objective is to *directly connect financial planning with portfolio construction*, so investors hold optimal portfolios whether they self-direct or work with an advisor.

### 1.2 Som's "planning-first" thesis (Aug 2024 Future of Wealth interview)
Four points that frame the strategic environment for MP2.0:

- **Planning-first is the winning model.** Advisors who lead with portfolio management as their core value proposition will lose ground over the next decade. The future belongs to those who lead with integrated financial planning and treat investment management as essential but secondary. Reference firms: Investors Group, Creative Planning, Vanguard Personal Advisor Service. Fee-justification reframe: of a 1% advisor fee, perhaps 30–50 bps is for market access; 50–70 bps must come from genuine planning value.
- **Deeper service & advisor enablement are the differentiators.** Purpose's vision is to be more than a product manufacturer — a services organization that helps advisors modernize their practices. Even 100–1,000 deeply partnered advisors would constitute a winning business.
- **Being the "black sheep" matters.** No firm holds more than 5–10% market share in Canada. The strategy is to differentiate by being bold and forward-looking, leading from the front.
- **AI accelerates commoditization and raises the bar.** Basic portfolio construction, planning tools, and admin will become free or near-free. Firms packaging commodity services as high-value will be exposed. Firms using AI to elevate insight and service quality will pull ahead.

### 1.3 Industry evolution (Horizon 1 → Horizon 2)
What's getting commoditized in the next 3–5 years: beta/index strategies, basic accumulation planning (60/40), market intelligence, simple model portfolios, non-human-driven innovation.

What wins as differentiation moves to: customer experience and fluidity, expertise in the service model (PM, practice management, marketing), deep client understanding and holistic relationship, helping advisors differentiate themselves, and a true planning-first approach where the plan is the benchmark, not the portfolio.

What "planning-first" means in Horizon 2: plan is the main guiding benchmark; portfolio/investments/spending follow it; life-milestone breakdowns; outcome-focus rather than return-target %; "end-in-mind" cash-flow projection.

### 1.4 The 4 project goals
| Goal | Detail |
|---|---|
| **Reimagine planning-first wealth** | Bring Purpose forcefully into the planning-first world and shape it with a bold offering. Do for portfolios what Purpose did for funds. |
| **Connect the experience** | A delightful, integrated end-client experience — the One Purpose vision. Capstone for Harness's offering; potential foundation for a "retirement robo." |
| **Accelerate fund sales** | Demonstrate clearly the role of each Purpose fund inside a portfolio. Wholesalers become better challengers. Pre-clear path for new fund launches by incorporating them into models on day one. |
| **Access new distribution channels** | DIY consumer brand on-ramp; Group RRSP / DC pensions (~$260B channel where Purpose has little adoption, including LPF). |

### 1.5 OKRs (from the original memo — to be re-baselined post-MVP)
| Key result | Timing | Approximate target |
|---|---|---|
| Use of online tools published | 6 mo. after launch | 10–15K total users, rising monthly |
| Press / earned media | 6 mo. after launch | 15–20 mentions or guest articles |
| AUM in building-block (sleeve) funds | 12 mo. after launch | +$250M |
| AUM into LPF | 12 mo. after launch | +$75M |
| Advisor NPS ("aNPS") | 18 mo. after launch | +20 points from baseline |

### 1.6 Where MP2.0 fits in Purpose's targets
- ~$5B contribution toward the $50B AUM target by 2028.
- Relevant existing products: Longevity Pension Fund (LPF), Purpose Active ETF suite (~$280M AUM today), the 16 "whole portfolio" models across MF/ETFs (PACF, PABF, PAGF) and SMAs (Harness, Link, PIMP).
- Distribution channels in scope (rolled out in this order): Steadyhand Investment Specialists → 3rd-party IIROC/CIRO advisors → Partnership Program teams → DIY → Group RRSP / DC pensions.

### 1.7 Brand / call-to-action positioning (memo concepts, not yet finalized)
Working candidates:
- *"Build a portfolio as unique as your goals are."*
- *"Your goals are unique. Build a portfolio to match."*
- *"Plans shape portfolios. Then portfolios enable plans."*

Positioning metaphors that pair well with the "Purpose" brand: Voiceprint; D.N.A.; Fingerprint; Path; Tattoo; Journey. Naming patterns: Portfolios with Purpose; Planning with Purpose; Journey by Purpose.

---

## 2. The 6-stage customer journey (system architecture)

Each stage has three lenses that must be resolved at every design step: **Client**, **Advisor**, **Purpose (the firm)**.

### 2.1 Stage 1 — Onboarding
- Digital intake; KYC/AML; risk profiling; goals & life-context capture.
- Adaptable input source: Conquest, Adviice, Planworth output → ingestible; meeting notes (unstructured) → ingestible via AI extraction with human review; direct client questionnaire when no plan exists.
- Initial use case is **advisor-for-client**, not direct DIY. Steadyhand specialists drive the first deployment.
- This stage produces the structured client record that feeds every downstream stage.

### 2.2 Stage 2 — Living Financial Plan
- Goals-based planning engine: scenario modelling, cash-flow projections, Monte Carlo simulation.
- Produces the inputs that drive blend ratios in Stage 3.
- Trust is made or broken here. The plan must feel like the client's plan, not a templated output.
- "Living" is the operative word: the plan is updated continuously; it is not a static PDF. The continuous-loop in Stage 6 feeds back here.

### 2.3 Stage 3 — Portfolio Construction
- **Hybrid sleeve-blend model** (the team-confirmed Option C; Fraser's "paint mixing" analogy).
- 8–12 standardized sleeve funds = building blocks.
- Personalized blend ratios are driven by the financial plan output (time horizon, risk tolerance percentile, goal necessity, household risk capacity, behavioural risk).
- **Macro Insight Layer** (CIO/strategist-driven) updates sleeve internals on its own cadence, independent of individual client plans. Two update cycles run in parallel: (a) blend ratios for a client (driven by plan changes / life events); (b) sleeve internals (driven by macro/strategist views).
- Engine outputs are subject to Steadyhand investment-specialist review and explicit client approval before execution.
- See §3 for the full engine spec.

### 2.4 Stage 4 — Automated Execution
- Drift detection, tax-aware rebalancing, custodian API integration, compliance guardrails.
- Ideally invisible to the client.
- **Phase 2+.** Not in MVP scope. Today at Steadyhand, all transactions require explicit verbal or DocuSign client approval, with no discretionary management permitted under MFDA.

### 2.5 Stage 5 — Outcomes Reporting
- The "Am I going to be okay?" report. Combines plan progress, portfolio performance, and market context.
- AI/LLM-generated meeting prep for advisors (pre-meeting summaries, suggested questions, on/off-track flags).
- **Goal-centric, not benchmark-centric.** The team explicitly resolved at the offsite that the primary client view shifts from performance-vs-benchmark to progress-vs-goals. Regulatory statements remain (MFDA-mandated), but the client-facing portal/one-pager leads with goal pathing.
- Open design issue: "phantom reporting" — when one account contains funds servicing two goals (e.g., a TFSA with 70% retirement, 30% cabin), how do we attribute returns at the goal level without showing regulator-confusing per-goal returns? Working position: report dollars-toward-goal, not per-goal returns.

### 2.6 Stage 6 — Continuous Loop
- Event-driven triggers feed back to Stage 2.
- **Sources of triggers**: life events (marriage, divorce, birth, inheritance, job change, retirement), money-in-motion events (PAC change, large deposit/withdrawal, address change, account opening/closing, SWP start), regulatory cycle (3-yr KYC under MFDA / annual under IIROC/CIRO), advisor observations, market dislocations.
- **This is where MP2.0 becomes sticky.** A static plan + portfolio is a one-time deliverable. A living one is a relationship.
- The CSM Nudge Framework (§7) is the operational expression of this stage at MVP — human-judgment-triggered, manual outreach, pre-approved language.

---

## 3. The portfolio engine — technical specification

### 3.1 Engine inputs
**Per-goal inputs** (one row per goal):
- `goal_id`, `goal_name`
- `target_amount` (today's dollars; inflation handled in projection layer)
- `target_date` / `time_horizon_years`
- `goal_necessity` ("essential" / "important" / "aspirational" — feeds the percentile we optimize for)
- `current_assets_allocated` ($ assigned to this goal today)
- `monthly_contribution` (savings flowing to this goal)

**Per-household inputs:**
- `household_risk_capacity` (financial — derived from balance sheet, income stability, fixed obligations)
- `household_risk_tolerance` (psychological — KYC questionnaire + observed behaviour)
- `behavioural_risk_signals` (PAC pauses during volatility, large emotional withdrawals, follow-through on past advice)

**Sleeve universe inputs:**
- For each sleeve: `expected_return`, `expected_volatility`, `pairwise_correlations`, `compliance_risk_rating` (low/medium/high), `mandate_constraints` (max weights, sector caps, etc.)
- Sleeve capital-market assumptions are sourced from a defined provider (TBD: Goldman, JP Morgan, Purpose CIO Craig Basinger, or composite). Document the source on every model run for explainability.
- Cash sleeve treated as risk-free (volatility ~0); efficient frontier extends as a tangent line from the cash sleeve to the curved frontier of risky sleeves.

### 3.2 Engine math (working v1.0)
The v1.0 engine uses Modern Portfolio Theory with percentile-optimization rather than mean-variance utility. The selection logic at the offsite walked through this end-to-end:

1. **Build the frontier.** Given N sleeves with expected returns, volatilities, and the correlation matrix, compute the efficient frontier — the set of (volatility, return) points that are Pareto-optimal.
2. **Translate "risk tolerance" into a target percentile.** Risk tolerance is expressed as the percentile of the outcome distribution the client wants to optimize for:
   - Risk-tolerant client → 50th percentile (median expected outcome).
   - Moderate → 30th percentile.
   - Risk-averse → 10th percentile.
   - Very conservative → 5th or 1st percentile.
   The engine maximizes portfolio value at the chosen percentile, given the time horizon.
3. **Walk the equity-weight axis.** The engine evaluates expected outcomes at each percentile across 0%–100% equity weight (1% increments). For median percentile, optimum often pushes to 100% equity at long horizons. As the target percentile drops, the optimum pulls toward lower-volatility blends.
4. **Apply time horizon.** Shorter horizons compress the value of equity exposure; the engine allocates more to cash/short-duration sleeves as the goal approaches.
5. **Output blend ratios.** Per goal: a vector of sleeve weights summing to 100%. Per household: aggregated blend across all goals weighted by goal $ size.

**Alternative formulations to evaluate post-MVP:**
- Maximize-probability-of-reaching-target (vs. percentile optimization).
- Utility-function-based (diminishing marginal utility, prospect theory loss aversion) — better captures human psychology but harder to explain.
- Behavioural-overlay: if the client has paused PACs during past drawdowns, the engine recommends a slightly more conservative blend than the plan strictly requires.

**Open methodology question (offsite):** Combining household-level risk and goal-level risk into a single risk input. Working approach: weight goal risk by goal $, blend with household risk capacity, but the team is explicit this is an MVP simplification and needs more rigour.

### 3.3 Glide pathing
- Rebalance is **event-driven**, not calendar-driven, in v1.0.
- Triggers: significant deviation from optimal blend; goal date approaching (the "cash takeover" effect — as the goal gets close, the cash sleeve dominates the blend); major life event; meaningful change in circumstances.
- Define "meaningful" deliberately conservatively — the operating principle is *"don't trigger trades for negligible benefit."* Steadyhand currently rebalances only when ≥3–5% off household target; that intuition carries over.
- The day before a goal liquidates (e.g., wire-out for a house purchase), the allocation should be effectively cash. The model already prescribes this; the practical question is whether to expose the full glide path to the client or smooth it through advisor judgment.

### 3.4 Goal → account → fund mapping
This is one of the more conceptually complex pieces; the offsite worked through it explicitly.

**Relationship cardinality:**
- One goal ↔ one account (simple case: an RRSP entirely for retirement).
- One goal ↔ many accounts (retirement spread across RRSP + spousal RRSP + TFSA + non-reg).
- Many goals ↔ one account (a TFSA holding 70% retirement + 30% cabin down-payment).
- Many goals ↔ many accounts (the realistic case for most households).

**Working model:**
- The household is the primary planning unit.
- Goals exist at the household level; accounts and funds are the execution layer.
- Within an account that supports multiple goals, the engine produces a logical sub-account ("sleeve of the sleeve") allocation per goal.
- For reporting, the account-level return is what regulators see. Goal-level progress is computed by attributing the account's blended return to each goal's $ slice — but the team flagged this is *exactly* the "phantom reporting" risk and the agreed working approach is: *report goal progress in dollars-toward-target, not as per-goal returns*.

**Regulatory constraint to design around:** Steadyhand cannot formally label or nickname an account by goal. The mapping lives in the planning/portfolio layer; the account itself stays generically labelled per regulation.

### 3.5 Engine outputs
Per-client-run, the engine produces:
- A vector of sleeve weights per goal.
- An aggregated household blend.
- An expected-outcome fan chart (e.g., 10th/50th/90th percentile portfolio value over the time horizon).
- A **classical compliance risk rating** (low / medium / high) translated from the optimized portfolio for MFDA/IIROC compliance reporting.
- An **audit log** of every input and decision: client inputs, sleeve assumptions, percentile chosen, frontier coordinates, output weights, timestamp, model version. Required from day one — explainability is non-negotiable for regulated deployment.

### 3.6 What the engine is NOT (explicit scope boundaries)
- Not a discretionary trading system. Output is a *recommendation* that requires advisor review and explicit client approval at Steadyhand under MFDA.
- Not a comprehensive financial planner. Steadyhand investment specialists are limited to investment advice; only CFP/QAFP-designated professionals provide comprehensive financial plans. The engine ingests plan output; it does not replace a planner.
- Not a tax engine in v1.0. Tax-aware rebalancing is Phase 2+.
- Not multi-currency or non-Canadian asset-aware in v1.0.

---

## 4. Sleeves — the building blocks

### 4.1 Why sleeves matter (and why they're non-negotiable)
From the original memo and reinforced at the offsite: launching the building-block sleeves as proper funds is a *table-stakes* requirement for the system to function. The reasons:

- **Trust requires demonstration over a modelled investor lifetime.** The full system can only be validated end-to-end if the building blocks exist as real, investable, papered products with track records.
- **Consistency across Purpose's two portfolio offerings.** MP2.0 doesn't replace the Partnership Program / "Model Portfolios 1.0" — it builds on top of it. The sleeves embody Purpose's best portfolio-construction-1.0 thinking and ensure both offerings draw from the same well.
- **The Harness Investment Committee specifically required formal launch.** Deploying for retired Harness clients required PMs attached, papering complete, full-fund treatment.
- **Operational efficiency.** A 3- or 4-ticket portfolio of real funds is dramatically simpler to execute and sustain than ad-hoc allocations across underlying securities.

### 4.2 Wrapper choice
- **Preferred: ETF.** Maximum accessibility, lowest cost on smaller accounts, modern feel, available on every platform.
- **Acceptable: mutual fund.** Same effect for Steadyhand-style execution; less universal access than ETFs.
- **Limited use: SMA.** Works for Harness and 3rd-party SMA relationships, but unfamiliar and high-cost on small accounts; major distribution gaps.

### 4.3 Working sleeve count and shape
- 8–12 sleeves total (the practical envelope).
- Walking through the offsite efficient-frontier exercise, the team tested with 5–6 illustrative sleeves (broad equity, fixed income / IG, high-yield, international, commodities, cash). The Steadyhand existing fund roster (Builders, Founders, Income, Cash, etc.) was being mapped onto this framework as a parallel exercise.
- A **cash sleeve** is essential — it's the risk-free anchor that lets the engine extend the frontier as a tangent line and lets goals near their target date glide into cash.
- Each sleeve has a clear, narrow mandate so the engine can reason about its expected return, volatility, and correlation to the others without ambiguity.

### 4.4 Sleeve maintenance
The Macro Insight Layer (CIO/strategist) updates sleeve *internals* (the underlying holdings) on its own cadence. The blend layer (which sleeves a given client holds, in what ratios) updates on a *separate* cadence driven by the client's plan and life events. These two cycles must not be conflated in the system architecture or the client communication.

---

## 5. Client data framework

The data the system needs is more comprehensive than the regulatory KYC minimum but less prescriptive than a full CFP planning intake. Steadyhand's working framework (from the Lori Norman document) is the v1.0 input schema for MP2.0.

### 5.1 Six data categories
1. **Profile & household** — names, DOBs, household type, marital status, blended-family status, children/grandchildren, parent health & longevity, dependants with disabilities, trusted contact person, POA, beneficiary designations, will status.
2. **Income & cash flow** — employment income (gross/net), DB/DC pension entitlements, business/self-employment income, rental income, PAC/savings rate, monthly spending estimate, expense-tracking discipline, expected income changes.
3. **Assets, liabilities & registered-account room** — outside (non-Steadyhand) assets, RRSP/TFSA/FHSA/RESP/RDSP room and balances, mortgage/debt, real-estate, business interests, registered-plan setup, major-purchase plans, charitable giving intentions, business-succession timeline.
4. **Goals** — short / medium / long-term goals with $ target and time frame; goal necessity (essential / important / aspirational); goal-to-account conceptual mapping.
5. **Risk profile & investor behaviour** — risk tolerance (SAM / questionnaire), prior investment experience, reaction to past market declines, return expectations, delegation preference (DIY vs. advised), attitude to debt, money mindset (saver vs. spender), tax sensitivity, life/disability/critical-illness coverage in place.
6. **Relationship & engagement data** — meeting type/channel, last contact/review dates, client sentiment, questions raised, goals on/off track, plan-last-updated date, scenarios modelled, professional referrals, AUM/loyalty tier.

### 5.2 Known gaps in current Steadyhand data collection (highest-priority fixes)
- **Outside assets** — frequently referenced, rarely documented consistently. Recommendation: standardize an "outside assets" field.
- **Monthly spending** — one of the most impactful inputs for retirement modelling, one of the most inconsistently captured. FP Canada framework recommends client-tracked spending pre-meeting.
- **Business owner data** — income, succession timeline, corporate structure.
- **Insurance coverage detail** — life, disability, critical illness.
- **Will & POA currency** — tracked on review checklists but rarely synced to CRM.
- **Charitable intentions** — surfaced in discovery, rarely formalized.

### 5.3 Data ingestion strategy
The system must ingest from three input shapes:
- **Structured plan output** — Conquest, Adviice, Planworth. Highest fidelity. When available, parse directly into the schema.
- **Semi-structured CRM notes** — Croesus meeting notes against templates. Parse via LLM extraction with human-in-the-loop validation.
- **Unstructured / conversational** — recordings or free-form notes. Same LLM extraction pattern; lowest fidelity, requires more validation.

The system should also support **interactive clarification**: when ingestion finds gaps or ambiguity, it generates targeted clarifying questions for the advisor or client rather than failing silently. This is not a failure mode — it's a feature, and it's why batch-processing 600 clients is not feasible (and not desired) at MVP.

### 5.4 Data freshness and re-trigger
- MFDA: 3-year KYC refresh cycle.
- IIROC/CIRO: annual refresh cycle.
- MP2.0 supplement: any "money-in-motion" event or disclosed life event triggers a data re-validation, regardless of where in the regulatory cycle the household sits.

### 5.5 Discovery framework (FP Canada 5W-1H)
Steadyhand's discovery uses the FP Canada model across six planning areas. Condensed starter questions live in the framework document; the platform should treat these as the gold-standard intake set for advisor-led conversations and as the source for any DIY questionnaire equivalents.

---

## 6. Regulatory & compliance framework

### 6.1 Where Steadyhand sits (initial deployment)
- **MFDA dealer.** Investment advice is limited to Steadyhand/Purpose's own products.
- **No discretionary management.** Every transaction requires explicit client approval — recorded verbal consent or DocuSign.
- **Documentation is mandatory.** All client interactions, recommendations, and suitability assessments are documented; calls are recorded.
- **Limited financial planning.** Investment specialists provide investment advice only. Comprehensive financial planning requires a CFP or QAFP designation.
- **KYC suitability is a baseline, not the ceiling.** A small set of mandatory questions; everything beyond is open-ended and discretionary to the specialist.
- **Account labels are constrained.** Accounts cannot be formally nicknamed or labelled by goal. Goal mapping lives in the planning/portfolio layer, not in the account record.

### 6.2 What MP2.0 must do to be compliant
- Translate the engine's optimized portfolio into a classical compliance risk rating (low/medium/high) at both account and household level.
- Provide explainability: an audit log of every input and decision, retrievable by compliance, the advisor, the client, and any regulator review.
- Preserve the human-in-the-loop: advisor review and explicit client approval before any execution. This is a feature, not friction.
- Avoid "phantom" per-goal return reporting in regulator-visible artifacts. Goal progress reports in $-toward-target form.
- Allow the recommended risk level to differ from the client's stated overall risk profile *only* with clear documentation and disclosure (e.g., a goal-specific aggressive allocation inside a generally conservative household).

### 6.3 Channel constraints to design around
- **Steadyhand** — MFDA, in-house funds only, no discretion. Governs MVP design.
- **Harness** — IIROC/CIRO, broader product universe, retirement focus, Investment Committee approval required on funds. Phase 2.
- **Partnership Program / 3rd-party advisors** — varied; the engine output is a recommendation; execution sits on the advisor's platform.
- **DIY** — long-term ambition; raises a different compliance and suitability question that the team is explicit is *not* in MVP scope.
- **Group RRSP / DC pensions** — large channel (~$260B), low Purpose adoption today. LPF is the lead product. MP2.0's track record in retail will be instrumental in unlocking this channel later.

### 6.4 Compliance posture in design choices
- **Deterministic workflows.** Even where AI is used (intake parsing, meeting prep, summarization), the workflow boundaries, the data attributes captured, and the output structure must be deterministic. AI creativity is bounded inside well-defined slots.
- **Static or configurable intake forms.** Required-data attributes are non-negotiable; the form may evolve, but the schema must be enforced.
- **Skills/prompts as guardrails** for any LLM-driven step; outputs validated against the schema; human review where outputs influence advice.

---

## 7. The CSM nudge framework — MP2.0's behavioural layer

### 7.1 Governing principle
*At MVP, nudges are a behaviour standard, not a system. Human judgment is the trigger. Manual execution is acceptable. Consistency beats cleverness.*

This is intentional. The MP2.0 engine and the CSM nudge framework are designed to work together — the engine gives the nudge framework its intelligence (a *reason* to reach out grounded in the plan, not just an event); the nudge framework gives the engine its behavioural layer (when to reach out, what to say, what *not* to automate yet).

### 7.2 Nudge categories at MVP
**Section 1 — Transaction-based** (highest-priority lever; observable, timely, money-in-motion):
- Address change → check-in for life-transition signal; flag inter-provincial moves for plan review.
- Large/unusual contribution → reach out within 5 business days; possible engine re-run.
- PAC started / increased / paused / stopped → engine validates against plan trajectory; pauses get priority outreach.
- Account opening / closing / structure change → triggers re-allocation review.
- SWP started → major nudge event; full review conversation; introduces sequence-of-returns risk context. **This is core MP2.0 — decumulation initiation.**
- Large withdrawal → outreach to understand purpose; behavioural reassurance language if market-driven.

**Section 2 — Life stage & life event** (manual, conservative; human-reviewed):
- Age 60 / 65 / 71 milestones (RRIF conversion, OAS/CPP timing).
- Beneficiary / estate gap surfaced in KYC review.
- New relationship / marriage; divorce / separation (priority, sensitive).
- Birth of child or grandchild.
- Job change / job loss / retirement.
- Inheritance / windfall.
- Health / longevity event.

**Section 3 — Seasonal & market** (formalizing what already happens):
- RRSP season (Jan–Mar) — targeted outreach to clients with room.
- Year-end planning (Nov–Dec) — tax-loss harvesting, charitable giving, TFSA top-up, RESP year-end.
- Annual budget / plan review.
- Market-volatility events — pre-approved language, human-sent.

### 7.3 What is explicitly NOT MVP (parked for Phase 2+)
- Predictive / advisory nudges (TFSA-room alerts, OAS-timing warnings, RIF-conversion warnings) — precision-timing risk.
- Any fully automated nudges — tooling and governance not ready.
- Real-time market-triggered automation — reputational downside, governance not ready.
- Personal / non-financial milestones (birthdays, family events) — privacy and unwind risk.
- Automated rewards / gifting — budget and tooling.
- A/B optimization on nudge performance — premature.

### 7.4 How the nudge thinking shapes portfolio design (six design principles)
1. **Pre-arm the nudge in the report.** Reports include pre-built behavioural-reassurance scenarios — *"if markets drop 15%, here's what that means for your plan"* — embedded in the portfolio output.
2. **Transaction signals are portfolio-aware.** PAC pauses, large withdrawals, contribution changes are both nudge triggers and portfolio events — flag when they create material plan/allocation deviation.
3. **Review cadence = nudge cadence.** The iterative loop (check-in → updated plan → engine) maps to time-boxed nudge windows. The portfolio review cycle *is* the nudge cycle.
4. **The Not-MVP list is the MP2.0 roadmap.** Parked nudges become Phase 2 engine features once the foundation is solid.
5. **Behavioural risk ≠ stated risk tolerance.** A client who consistently pauses PACs in volatility has a behavioural risk profile separate from the questionnaire score. Future engine should weight observed behaviour into the blend.
6. **Decumulation is the highest-stakes nudge zone.** SWP initiation triggers a full review conversation, not a mechanical re-allocation. Wealth-therapist and portfolio-engineer converge here.

---

## 8. Personas & test data

### 8.1 The MVP persona set (offsite commitment)
- **Five client personas** sourced from real Steadyhand client situations (Lori provides), allowing manual extraction and validation of every input the engine needs. These drive the demo path.
- **10–50+ synthetic personas** generated programmatically (Claude or equivalent), spanning Canadian client situations from straightforward to deliberately strange/edge-case. These pressure-test the engine and the ingestion pipeline.

### 8.2 Why both real and synthetic
- **Real personas** test the realistic shape of the input (incomplete notes, ambiguous goals, conflicting signals between KYC and conversation, outside assets, etc.).
- **Synthetic personas** let us scale tests to edge cases (very high net worth, ultra-conservative behaviour, recently divorced with split assets, business owner mid-succession, immigrant client with pre-Canadian assets, etc.).
- **The "translation back to source" test:** generate a structured persona → run it through the ingestion pipeline → does the engine produce the same structured profile back out? This catches regressions in the extraction and parsing layer.

### 8.3 Engine-test scenarios that must pass MVP
- One person, one goal, one account (the simplest case — retirement RRSP).
- One person, multiple goals, multiple accounts (RRSP for retirement + TFSA mixed retirement/cabin + non-reg general savings).
- Couple, joint goals + individual goals + asymmetric assets.
- Pre-retiree (age 60, accumulation tail, transition scenarios).
- Newly retired (SWP initiation, decumulation engine).
- Inheritance event (engine re-run with new asset base).
- Goal target date in <12 months (cash sleeve dominates the blend).

---

## 9. MVP build plan

### 9.1 What the offsite committed to ship
The April/May 2026 Purpose offsite demo is a *working application*, not a slide deck. It must mechanically traverse the happy path:

1. Ingest a client persona (one of the five real or a synthetic one).
2. Render a financial plan view with goals, time horizons, and projected trajectories.
3. Run the engine → produce blend ratios per goal and aggregated household allocation.
4. Render a goals-progress view showing dollar progress against target, with a fan chart of expected outcomes.
5. Show the recommended allocation, the compliance risk rating, and the audit-log entry behind it.

### 9.2 Stack and architecture decisions (offsite)
- **Backend:** Python + Django. Modular engine. Mock APIs / mock data wherever real integrations aren't yet available.
- **Frontend:** demo-grade. UI fidelity is secondary to the demo path working.
- **AI tooling:** Claude / Codex for code; LLM extraction for ingestion; deterministic workflow boundaries; human review at every step that influences advice.
- **Audit log from day one.** Every input → output decision is traced. Non-negotiable.
- **Mock data / mock APIs for ingestion.** Real Steadyhand fund data is being merged in; client ingestion will use synthetic data for the demo, with a clear plan to swap in real CRM extracts post-MVP.

### 9.3 Working scope boundary for MVP
- Stages 1, 2, 3, 5 of the customer journey.
- Stage 4 (automated execution) is *out of scope* for MVP. Today's manual execution flow stays.
- Stage 6 (continuous loop) is represented by the *capability* to ingest a triggered re-run, not by the full event-detection pipeline.
- Single-client mode. Couples mode is a fast-follow.
- Steadyhand fund universe only at first; sleeve productization runs in parallel.

### 9.4 Roadmap immediately after MVP demo
The offsite explicitly noted that day 3 of the offsite shifts from "build" to "roadmap" — *"if this is what we have for each section, what are the eight things we need to do to make this robust?"*

The post-MVP roadmap includes:
- Real fund data integration (Steadyhand + Purpose fund universe).
- Couple-mode planning.
- The Macro Insight Layer plumbing (separating sleeve-internal updates from blend-ratio updates).
- Decumulation engine (SWP-driven, sequence-of-returns-aware).
- Tax-aware rebalancing.
- The portal / one-pager client view (Andrew's team is owner; coordinate).
- Predictive nudges and event-detection pipelines.
- DIY-mode flow (much later — different compliance regime).

### 9.5 Follow-up tasks from offsite Day 1
| Owner | Task |
|---|---|
| Lori | Provide 5 sample client personas in a format that allows manual extraction and validation for engine testing |
| Saranyaraj, Raj | Integrate the client situation optimizer with the Steadyhand fund-blending model; test with real fund data and sample personas |
| Team | Define and document the process for combining household-level and goal-level risk scores into a single risk input |
| Team | Establish a method to translate optimizer output into a compliance risk rating (low/medium/high) for client and account level |
| Raj | Implement the audit log in the engine for input-output traceability |
| Saranyaraj, Raj | Build the MVP demo application that mechanically traverses the journey |
| Raj | Create mock data and API placeholders for client ingestion and portfolio construction |

### 9.6 Hire / squad context
- A product leader for MP2.0 was hired the day of the offsite (offer accepted) — the "model portfolio 2.0 squad" picks up post-offsite for prototype iteration, client testing, and roadmap execution.

---

## 10. Open questions and decisions pending

These are the unresolved items from the offsite. They are *not* blockers to the MVP demo, but they need named owners and resolution before broader deployment.

1. **Capital-market-assumptions source.** Which set of expected returns / volatilities / correlations does the engine canonicalize on? Goldman, JP Morgan, RP, Purpose CIO Craig Basinger, or a composite. Document on every model run.
2. **Risk-tolerance → percentile mapping.** The percentile-based formulation is acknowledged as somewhat arbitrary in how it maps human psychology to a number. Alternatives (probability-of-target, utility-function, behavioural-overlay) need a structured comparison.
3. **Household + goal risk blending.** Working approach is goal-$-weighted; needs a more rigorous derivation.
4. **Goal-level reporting.** "Phantom return" reporting is rejected. Working alternative is dollars-toward-target. Final UX needs validation with compliance and with clients.
5. **Sleeve count.** 8–12 is the working envelope; the actual count and shape of the production sleeves must be decided alongside the productization workstream.
6. **Sleeve wrapper.** ETF preferred; mutual fund acceptable; SMA situational. Decision needs to land for production launch.
7. **DIY compliance regime.** Out of MVP scope, but the long-term path needs an explicit position before DIY rollout.
8. **Fund-size mandate constraints.** The "what's too big" question (capacity ceilings on actively managed sleeves) needs an institutional-lens answer before scaling AUM.
9. **Conquest/Adviice/Planworth integration depth.** Read-only ingestion at MVP. Two-way sync (writing engine output back into the planning tool) is desirable but unscoped.
10. **The portal vs. the report.** Andrew's team owns the portal; this team owns the engine and the one-pager. The boundary between them — and the data contract — needs to be drawn.

---

## 11. Reference materials

### 11.1 Source documents (in this project)
- **The Purpose Memo — MP2.0** (Sep 2024, Fraser Stark) — the founding strategic memo. Opinionated, not set in stone; thinking has evolved. Still authoritative on goals, brand positioning, sleeves rationale, OKRs.
- **MP2.0 MAT Invitation Extract** — the offsite framing document; objective statement; key design principles.
- **MP2.0 Offsite Prep** — agenda and offsite objectives.
- **MP2.0 Day 1 Morning** — AI-generated meeting notes (regulatory framing, client onboarding, account/goal mapping, engagement cadence).
- **MP2.0 Day 1 Afternoon** — engine architecture, efficient frontier walkthrough, fund-to-goal mapping, reporting design, MVP scoping. Authoritative on engine design choices.
- **MP2.0 Day 1.docx / MP2_0_-_Day_1_-_Afternoon.docx** — full transcripts.
- **Client Data & Conversations Framework** (Lori Norman, Steadyhand) — the canonical data schema; gaps; FP Canada discovery framework.
- **Client Nudges & MP2.0** (Lori Norman, Apr 2026) — the CSM behavioural framework and its design implications for the engine.
- **Summary of Som's Future of Wealth interview** (Aug 2024) — strategic thesis from the executive sponsor.
- **Sample financial plans** (Burnham, Kneteman, Moore, Schlotfeldt, Lee/Nigel) — real examples of plan output the system must ingest.
- **Client checklists** (birth of child, post-secondary, house purchase, inheritance, end-of-life, divorce, job loss, retirement) — life-event triggers and their associated information needs.
- **Client Meeting OnePager — Dominique Paris** — example of the kind of client-facing one-page output MP2.0 should produce.
- **Action Plan Nov 2024** — earlier planning artifact.

### 11.2 External references
- **Hackathon prototype output (Q4 2024):** https://purpose-portfolio2-0.lovable.app/ (early UI exploration; not the architecture being built).
- **Mermaid project flowcharts:**
  - Option A (sleeves): https://mermaid.ai/d/4814577d-5367-4dde-9ef6-3f01143fe630
  - Option B: https://mermaid.ai/d/9bfdc432-ff41-4a3d-9aa0-8186e7842c07
- **US comparable:** Vanguard Personal Advisor (planning-first, goals-based, advisor-supported).
- **Canadian planning tools tested:** Conquest, Adviice, Planworth.

---

## 12. Glossary

| Term | Meaning |
|---|---|
| **Sleeve / sleeve fund** | A standardized building-block fund. ~8–12 of these total. The "molecule" in Fraser's analogy. |
| **Blend / blend ratio** | The personalized mix of sleeves that a given client holds, driven by their financial plan. The "alloy." |
| **Macro Insight Layer** | The CIO/strategist-driven layer that updates sleeve internals (the underlying holdings). Operates on its own cadence, independent of individual client plans. |
| **Living Financial Plan** | Continuously updated, not a static PDF. Drives blend ratios. |
| **Paint mixing** | Fraser's analogy for how sleeves combine into a portfolio — fixed pigments (sleeves), endless personalized colours (blends). |
| **The 6-stage loop** | Onboarding → Plan → Construction → Execution → Reporting → Continuous Loop → back to Plan. |
| **Phantom reporting** | Showing per-goal returns inside an account that holds multiple goals. The team's working position is to *not* do this; report dollars-toward-target instead. |
| **Goal necessity** | "Essential" / "important" / "aspirational" — informs the percentile the engine optimizes for. |
| **Glide path** | The trajectory of allocations as a goal approaches its target date — typically a steady increase in cash-sleeve weight in the final ~24 months. |
| **Money-in-motion event** | Any client transaction or balance change that signals something — PAC change, large deposit, address change, account opening. A primary nudge trigger. |
| **MAT** | Mission-Aligned Team — the 5-person offsite team. |
| **CSM** | Client Service Model — Steadyhand's behavioural framework for advisor-client interactions. |
| **PAC** | Pre-Authorized Contribution — recurring deposit. A leading indicator of client commitment and behaviour. |
| **SWP** | Systematic Withdrawal Plan — the start of decumulation. Highest-stakes nudge zone. |
| **LPF** | Longevity Pension Fund — Purpose's mortality-pooled retirement product; central to the decumulation thesis. |
| **PP** | Partnership Program — Purpose's IA-consulting program; "Model Portfolios 1.0" sits inside this. |
| **Steadyhand** | Purpose's MFDA dealer; first MP2.0 deployment context. |
| **Harness** | Purpose's advisor solutions platform; second deployment context (IIROC/CIRO). |
| **Link** | Purpose's direct/group plan platform. |
| **MFDA** | Mutual Fund Dealers Association — the regulatory body governing Steadyhand. Defines suitability, KYC cadence, no-discretionary-management constraints. |
| **IIROC / CIRO** | The IIROC, now CIRO, regulatory regime for Harness and 3rd-party advisors. Annual KYC refresh. |
| **One Purpose** | Purpose's strategic ambition for an integrated wealth experience across all platforms and products. |

---

*Last updated: April 28, 2026.*
*Owners: Fraser Stark (project lead), Nafal Butt, Lori Norman, Saranyaraj Rajendran. Executive sponsor: Som Seif.*
