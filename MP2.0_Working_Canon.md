# MP2.0 — Working Canon (v2.8)

**Merged seed + engineering + real-PII + MVP/pilot + Day 2 design + production-grade reframe + Day 3 lock-ins + internal consistency pass + 2026-04-30 authorization-basis clarification**
**Compiled:** April 30, 2026, post-clarification pass
**Owners:** Fraser Stark (project lead) | Saranyaraj Rajendran (engineering lead)
**Mission-Aligned Team:** Fraser Stark, Nafal Butt, Lori Norman, Saranyaraj Rajendran
**Executive Sponsor:** Som Seif, CEO Purpose Investments

---

## How to use this document

This is the single working canon for MP2.0 — the document an engineer, product person, or AI coding agent should be able to read top-to-bottom and have everything needed to build the platform: what we're building, why, for whom, with what data, on what investment theory, under which regulatory and engineering constraints, and on what sequence.

It is opinionated where the team has aligned. It is explicit about what is still open. It is not the original memo, the meeting notes, or the regulatory bible — it is the working canon that should remain in sync with the codebase.

**Decision tags** appear throughout:
- **[LOCKED]** — settled at the offsite or working session; change only with explicit team agreement
- **[DEFAULT]** — best-judgment default; revisit when grounded by real data or constraint
- **[OPEN]** — unresolved; needs an owner and a date

**When this document and the codebase disagree, fix the disagreement the same day — by updating one or the other.**

---

## TABLE OF CONTENTS

1. Strategic foundation
2. The conceptual model
3. The 6-stage customer journey
4. Investment theory & engine mechanics
5. Fund universe
6. Data model & required inputs
7. Regulatory & compliance constraints
8. Reporting & client communication
9. Engineering — stack, architecture, infrastructure
10. Engineering — repo layout
11. Engineering — extraction layer (5-layer pipeline)
12. Engineering — engine I/O contract
13. MVP scope, build sequence, pilot launch
14. Items to confirm with Purpose IT
15. Open questions & decisions pending
16. Glossary & vocabulary
17. Reference materials
18. Document versioning

---

## PART 1 — STRATEGIC FOUNDATION

### 1.1 The shift we are leading

The Canadian wealth industry has, for a generation, organized portfolios around a one-dimensional risk score and a small set of model portfolios (Conservative, Balanced, Growth, etc.). MP2.0 rejects that as the long-run answer.

The bet: over the next decade, the value advisors deliver will increasingly come from **integrated planning** — not portfolio selection. Portfolio construction, basic planning, and admin will commoditize as AI matures. Firms that package commodity services as premium will be exposed. Firms that use AI to elevate insight, personalization, and outcomes will pull ahead.

MP2.0 is Purpose's expression of this thesis: **a system that takes a client's financial plan as input and produces a portfolio that is mathematically tied to the plan's goals, and continuously updated as the plan and the world change.**

### 1.2 The core question MP2.0 answers

For every client, every year, we want to credibly answer:

> **"How should I structure my portfolio today to best support my financial plan and goals?"**

And, downstream of that:

> **"Am I going to achieve my goals?"** — *not* "How did the portfolio perform vs. benchmark?"

Som's framing for the offsite: every client meeting today opens with returns. In the MP2.0 world, every client meeting opens with goal progress. Returns are a means; goal attainment is the end.

### 1.3 The 4 project goals **[LOCKED]**

| # | Goal | Plain-language meaning |
|---|------|------------------------|
| 1 | **Re-imagine planning-first wealth** | Lead the industry shift from portfolio-first to planning-first. Be a "black sheep." |
| 2 | **Connect the experience** | Realize "One Purpose" — a single integrated journey across Steadyhand, Harness, Link, and Partnership Program. |
| 3 | **Accelerate fund sales** | Use the system to demonstrate what role each Purpose fund plays in a real portfolio. Each fund page links to portfolios that hold it; each portfolio page links to its underlying funds. |
| 4 | **Access new distribution channels** | Build a foundation that can later serve DIY investors, Group RRSPs, DC pensions, and a future "retirement robo." |

### 1.4 The business case

- Target contribution: **~$5B AUM toward Purpose's $50B-by-2028 target.**
- Som's success threshold: **100–1,000 deeply partnered advisors** is a winning business — depth, not breadth, wins.
- Fee architecture argument: of a typical 1% advisor fee, ~30–50 bps is for market access (commoditizing). The remaining 50–70 bps must increasingly come from genuine planning value. MP2.0 is the engine that makes those bps defensible.
- Catalyst product: **Longevity Pension Fund (LPF)**. Strong product, weak sales — because it doesn't fit a traditional risk-bucket portfolio. It needs a planning-aware allocation engine, which is exactly MP2.0.

### 1.5 Initial launch context — Steadyhand **[LOCKED]**

- **Steadyhand** is the launch context for the MVP. It's a Purpose subsidiary, MFDA-registered, with ~3,500–4,000 clients and a small Investment Specialist (IS) team led by Lori Norman.
- Steadyhand has a constrained, well-understood fund lineup, a high-trust client base, and a culture that already over-delivers on advice relative to its regulatory mandate. Ideal for a v1.0.
- After Steadyhand, the next deployment is **Harness** (advisor platform, especially retired clients — Harness Investment Committee has confirmed interest, conditional on the building-block funds being formally launched as funds with a Purpose PM attached). Eventually: 3rd-party IIROC/CIRO advisors, Partnership Program, Link group plans, and DIY.

### 1.6 The deliverable — production-grade MVP for advisor pilot **[LOCKED]**

> **MP2.0 is production-grade software with a limited user set.** The word "MVP" describes scope (small, focused, controlled pilot population), not engineering bar (it is not "demo-grade", "scaffolding", or "throwaway"). 3–5 Steadyhand Investment Specialists will use the system with their real clients. Real Canadian client PII flows through the system from day one.

This distinction matters because earlier framings of this project ("Som demo," "Friday launch event," "Phase A scaffold-grade") created a false comfort that some controls could be deferred. **They cannot.** Real PII does not wait for Phase B; it has been flowing through the system since the secure-local review tranche landed. The auth, audit, RBAC, kill-switch, fail-closed Bedrock routing, sensitive-identifier handling, and immutable-audit-via-DB-triggers controls are production controls, built in from the start, not Phase-B aspirations.

The implications:

| Concern | Production-grade-MVP bar (the actual bar) |
|---|---|
| **Audience posture** | Active — real advisors using the system to inform real client conversations |
| **PII handling** | Real PII flows from day one; controls are production-grade or the system doesn't ship |
| **Auth** | Authenticated-by-default DRF, advisor team scope, financial-analyst PII denial, kill-switch on engine generation. MFA / lockout / password reset are Phase B *additions* to a production foundation, not introductions |
| **Audit** | Append-only via model guards plus DB triggers, sanitized timeline events, edit hashes, kill-switch as audit event. Browser UI is deferred; *the writes are not.* |
| **Output trust** | Every recommendation marked as pilot-mode requiring advisor judgment; engine never invents numbers |
| **Failure mode** | An advisor takes pilot output to a real client conversation. Kill-switch, audit trail, and bounded blast radius (3–5 advisors) are how this is contained, not avoided |
| **Success metric** | Advisors keep using it after week one; no Sev-1 incidents |

**What this retires from earlier versions of this canon:** the language "Phase A is demo-grade," "stage-managed paths," "scaffold-grade," and "Som-demo-grade" are misleading and have been removed from this version. They were inherited from an earlier era when the team imagined synthetic-only data on stage Friday and real PII deferred behind a hardening window. Reality: real PII landed in the system by Day 2 evening; the engineering bar adjusted accordingly. The canon now reflects that.

**The Phase A → B → C structure remains useful** as a rollout sequence (offsite foundation → IS validation → pilot expansion), but each phase is production-grade for its scope, and the gates between phases are about *coverage* (more advisors, more clients, more controls layered in) not about *quality* (which is production-grade throughout).

### 1.7 Platform alignment — goal-based lens layered on foundations **[LOCKED — Day 3 morning]**

> **MP2.0 is a goal-based lens that layers on top of foundational platforms — not a parallel rebuild of them.**

The Purpose Engineering Director is rebuilding Advisor Center components in React (moving away from OutSystems). The risk Fraser flagged at Day 3 morning is real: if MP2.0 inadvertently rebuilds what Advisor Center already does, *some elements will be better, some worse, and both outcomes create organizational friction.* Better-than-Advisor-Center invites political conflict; worse-than-Advisor-Center invites comparison the team will lose. Neither serves the project.

The resolution is positional clarity:

- **The differentiator is the goal-based lens and portfolio construction engine.** The goal × account cross-reference (Part 4.3a), the household/account/goal three-view UX (Part 8.7), and the optimization engine itself are MP2.0's secret sauce.
- **The scaffolding (advisor login, client list, document storage, contact management, account dashboards) is not the differentiator.** Where Advisor Center provides this, MP2.0 should consume it — eventually — rather than rebuild it.
- **Build for snap-in.** The Phase A and B implementations build minimal scaffolding to hold the goal-based views together. The goal-based features are designed to be modular enough to plug into the Advisor Center React foundation as it matures.
- **For demo: minimum viable scaffolding.** Polish, branding, and Purpose visual identity are deferred. Usability for an advisor like Evan is the bar, not visual finish.

**The strategic implication:** if the goal-based lens is powerful enough on Steadyhand, it expands beyond Steadyhand to Harness and other Purpose channels via the same snap-in pattern (Goal #2 in Part 1.3, "One Purpose"). The platform decisions made now should keep that path open.

> *"That goal-based lens becomes the glasses we look at things through... we could build it on top of what [the engineering team is] doing as the foundational platform."* — Fraser, Day 3 morning

---

## PART 2 — THE CONCEPTUAL MODEL

### 2.1 The atomic hierarchy **[LOCKED]**

The "atomic building blocks" model from the offsite morning. The system reasons about wealth at four nested levels:

```
HOUSEHOLD  (1 or 2 people; never more — 3+ becomes dependents-as-goals)
   │
   ├── PERSON(s)
   │
   ├── GOALS (the things the household actually cares about)
   │     - each goal has: target $, time horizon, necessity (need vs. want vs. wish), inherent risk capacity
   │
   └── ACCOUNTS (the regulatory-required containers where money is held & risk is set)
         - each account has: type (RRSP/TFSA/RESP/Non-reg/...), regulatory IPS constraints, holdings
         - accounts contain FUNDS (building-block funds = the constituent paints; whole-portfolio funds = collapsed mixes)
```

**Critical insight from the offsite:** goals and accounts have a **many-to-many** relationship.
- One goal can be funded by money across multiple accounts (retirement spans RRSP + TFSA + non-reg).
- One account can serve multiple goals (a TFSA holding both cabin-purchase money and retirement money).
- The system must support this without forcing 1:1 mapping.

Regulatory reality: at Steadyhand (MFDA), accounts cannot be formally "nicknamed" or labeled with goals. The mapping is a logical/system layer above the regulatory account.

### 2.2 The fund-blend architecture (Option C) **[LOCKED — terminology updated Day 3 afternoon]**

**The foundational architectural decision is Option C: the hybrid fund-blend model.**

> **Terminology note (Day 3 afternoon):** earlier versions of this canon used "sleeve" / "sleeve fund" for the building-block category. **The team has retired that term** because (a) "sleeves" originally meant *purpose-built funds designed specifically for MP2.0*, and no purpose-built funds are being created — the system uses the existing Purpose fund universe; and (b) "sleeve" is industry-ambiguous (it can mean in-kind transfers, sub-portfolio components, or other things depending on context). **The replacement term is "fund."** Where the building-block-vs-whole-portfolio distinction matters, the canon uses "**building-block fund**" for the former and "**whole-portfolio fund**" for the latter (Founders, Builders, PACF, etc.). The conceptual distinction persists; the vocabulary tightened.

The analogy is **paint mixing** (Fraser's):
- **Building-block funds** = the paints. 8–12 building blocks total. Each has a clear mandate (e.g., "Canadian large-cap equity," "investment-grade bonds," "cash"). Each is a real, papered fund with a Purpose PM attached.
- **Blend ratios** = personalized mix of building-block funds driven by the financial plan (the painting). Every household–goal–account combination produces a unique blend.
- **Atoms-and-molecules**: building-block funds are molecules; the underlying holdings (individual securities) are the atoms. Clients/advisors operate at the molecule level. The Macro Insight Layer (see 2.3) operates at the atom level inside each building-block fund.

Why this architecture:
- Standardized building-block funds give us manageability, consistency across client books, and operational tractability (rebalancing ~12 funds vs. 1,000 unique portfolios).
- Personalized blends give us the planning-driven personalization that defines MP2.0.
- Building-block funds earn trust over time because they have track records, mandates, and PMs — they're real funds, not synthetic constructs.

### 2.3 The Macro Insight Layer **[LOCKED]**

The CIO/strategist function does **not** touch individual client portfolios. It updates the **internals of building-block funds** (the underlying holdings) based on macro views — duration calls, sector tilts, currency hedging decisions, factor exposures.

This means there are **two independent update cycles**:
1. **Fund internals** — driven by the Macro Insight Layer (probably monthly). Affects every client who holds that fund.
2. **Client blend ratios** — driven by changes to the client's plan, life events, or material drift. Affects only that client.

Clients see one allocation. The two cycles run silently underneath.

### 2.4 The Living Financial Plan **[LOCKED]**

The plan is **not a document**. It is a continuously-updated model of the household's situation. Specifically:

- It is updated by **events** (life changes, advisor observations, material market moves), not by a calendar tickler alone.
- It is **the source of truth for the blend** — when the plan changes, the blend changes (subject to common-sense thresholds; we don't trade on every plan tweak).
- It must accept inputs from any source: Conquest, Adviice, Planworth, direct client questionnaire, AI extraction from meeting notes. **MP2.0 must not be locked to one planning tool.** Conquest API integration is desirable but not in the MVP critical path.

This is where trust is made or broken. The plan is the product.

---

## PART 3 — THE 6-STAGE CUSTOMER JOURNEY

The system is a **continuous loop**, not a linear funnel.

| Stage | Name | What happens | Stakeholder POV |
|------:|------|--------------|-----------------|
| 1 | **Client Onboarding** | Digital intake, KYC/AML, risk profiling, goals & life context capture. AI helps extract from meeting notes. Static/configurable intake form ensures required attributes are always captured (deterministic). | Client: "Tell me about myself, easily." Advisor: "Let me capture everything I'd ask anyway, faster." |
| 2 | **Living Financial Plan** | Goals-based engine. Cash flow projections, scenario modeling, Monte Carlo, success probabilities by goal. Plan outputs feed Stage 3. **Trust is built or lost here.** | Client: "Will I be okay?" Advisor: "What scenarios do we need to test?" |
| 3 | **Portfolio Construction** | The MP2.0 engine itself. Fund-blend optimization driven by plan. Two independent update cycles (fund internals via Macro Insight Layer; blend via plan). | Purpose: "Are the building-block funds consistent across clients?" Advisor: "Why this blend?" Client: "Why these funds?" |
| 4 | **Automated Execution** | Drift detection, tax-aware rebalancing, custodian API, compliance guardrails. **Phase 2+ — explicitly out of MVP scope.** Should be invisible to the client when it works. | All: invisible until it isn't. |
| 5 | **Outcomes Reporting** | "Am I going to be okay?" reports. Goal progress visualization, plan-vs-actual, market context. AI/LLM-generated meeting prep for advisors. Periodic personalized updates. | Client: "Am I on track?" Advisor: "What do I tell them?" Purpose: regulatory reporting layered on top. |
| 6 | **Continuous Loop** | Event-driven triggers feed back into Stage 2: life changes, market shifts, advisor observations, plan-progress signals. **This is where MP2.0 becomes sticky.** | All: the system gets smarter with every interaction. |

**Phase A demonstration target: Stage 1 → 2 → 3 → 5.** **[LOCKED]** Stage 4 is mocked. Stage 6 is implied via "what happens when X changes" branches in the storyboard.

---

## PART 4 — INVESTMENT THEORY & ENGINE MECHANICS

This is the math the offsite locked in for v1. Like the race-car-engine analogy: it's a working engine for v1. We may swap from "gasoline to diesel" later — but it must run now.

### 4.1 Foundation: efficient frontier optimization **[LOCKED]**

For a given universe of building-block funds, with each fund characterized by:
- Expected return (after-fee, net)
- Volatility (annualized standard deviation)
- A correlation matrix across all funds in the universe

…we compute the **efficient frontier** — the set of portfolios that maximize expected return for each level of volatility (and equivalently, minimize volatility for each level of expected return).

This is Modern Portfolio Theory, applied at the building-block-fund level. The frontier is a curve in (volatility, return) space. Any blend of funds that lands **on** the curve is optimal in the mean-variance sense; anything below is dominated.

**Key mechanic observed in the offsite:** as we vary correlations between funds, the *shape* of the frontier changes meaningfully — strongly negatively-correlated funds push the frontier up and to the left (more return for less risk). This is why launching a true **bond-only building-block fund** matters: today the Steadyhand bond fund (Income Fund) is 75% bonds / 25% equities, which "couples" the bond axis to the equity axis and limits how far we can extend the frontier.

### 4.2 Risk modeling — composite, 5-point, three components exposed **[LOCKED — Day 2 + Day 3 afternoon refinements]**

Where on the frontier should a given client's blend sit?

**The risk scale is 5-point**, mapped to specific optimizer percentiles:

| Risk descriptor (client-facing) | Internal label | Optimizer percentile | Confidence floor |
|---|---|---|---|
| Cautious | Low | 5th | ~95% |
| Conservative-balanced | Low-Medium | 15th | ~85% |
| Balanced | Medium | 25th | ~75% |
| Balanced-growth | Medium-High | 35th | ~65% |
| Growth-oriented | High | 45th | ~55% |

The 5–45 range (intentionally below the median) prevents 100%-global-equity outcomes even for the most risk-tolerant clients. The 1st-percentile extreme produced absurd outcomes (all-cash too early); 50th felt too aggressive. **5–45 keeps a margin of conservatism even for "high-risk" clients.** Output is **snap-to-grid** — the blended risk score rounds to the nearest five-point step.

**Lexical distinction (Day 3 afternoon §2.3):**
- At the **client/household level**, the term is **"risk tolerance"** — a property of the person/household.
- At the **goal/account level**, the term is **"riskiness"** of the allocation — a property of the position/portfolio.

These describe related but distinct things; the canon uses both terms with this discipline.

**The risk input is composed of three named components, all exposed to the advisor:**

1. **Household risk tolerance** — derived from the holistic view of the household: income, net worth, investment knowledge, behavioral signals (loss aversion, follow-through, sentiment under volatility), tax sensitivity, attitude to debt.
2. **Goal-level risk tolerance** — specific to *this* goal, derived from: goal classification (need / want / wish per Part 6.3 necessity_score), and the **portion of total household AUM allocated to this goal** (Day 3 afternoon §5.4 — a goal that holds 90% of the household's wealth carries different riskiness considerations than one holding 5%).
3. **Combined / "goal-adjusted" risk** — what the optimizer actually uses.

**Time horizon is NOT a component of the risk score [LOCKED — Day 3 afternoon §5.4].** Time horizon is a separate input that drives where on the efficient frontier the portfolio targets (via the duration framework in Part 4.3d). Including time horizon in the risk score would **double-count** it: the same year-of-maturity would push the blend conservative once via the risk score and a second time via the frontier selection. Risk score and time horizon are orthogonal inputs to the optimizer.

**Showing all three components avoids the black-box feel** (Day 2). An info icon / drill-down is preferred over hiding. The advisor chooses whether to walk the client through it.

Both component scores can start very simple: the goal-level score can be **a single 4- or 5-point question per goal** ("If you missed this target by 30%, what would that mean to you?"). The household-level can be a 3-question composite + behavioral data from notes.

**Vocabulary [LOCKED — Day 2 §6.2; Day 3 afternoon §2.3]:** client-facing copy uses *cautious / conservative-balanced / balanced / balanced-growth / growth-oriented*. The internal labels (low / low-medium / medium / medium-high / high) are held for engine math and compliance mapping. Day 3 afternoon discussed both vocabularies; the team agreed both internal-numeric and named bands are useful. **The pilot UI should default to the descriptor vocabulary; "low / medium / high" reads as a verdict and stays out of client-facing surfaces.** (Open question #54: final UI string discipline; subset of the broader low-vs-named-band tension flagged Day 3.)

> **Note:** this is **not** the same as the regulatory KYC risk rating. The KYC score (low / medium / high investment knowledge × time horizon × objective) is a parallel artifact we still maintain because regulators require it. Our optimized portfolio is then **mapped back** to a regulatory risk bucket for compliance reporting (Section 7.4).

### 4.3 Three methods for "where on the frontier" **[LOCKED — Method 1 with 5/15/25/35/45 mapping]**

The offsite enumerated three valid mathematical approaches. Method 1 is the v1 default with a specific percentile mapping locked Day 2. The engine is modular enough to swap.

| Method | What it optimizes | Use it when |
|--------|-------------------|-------------|
| **1. Percentile maximization** *(v1 default — LOCKED)* | "Maximize my expected portfolio value at the Nth percentile outcome." Locked mapping: cautious=5th, conservative-balanced=15th, balanced=25th, balanced-growth=35th, growth-oriented=45th (Part 4.2). | Easiest to explain. v1 default. Snap-to-grid output. |
| **2. Probability of target** *(parallel display)* | "Maximize the probability that I hit my target $ amount by my target date." | Most goal-native; ties directly to the plan. Show alongside Method 1 *only when the client has volunteered a specific dollar target* (Part 4.4 / Day 2 §3.3). |
| **3. Utility function (risk aversion coefficient)** | Evaluates the full distribution of future outcomes, weighting downside more heavily based on a risk-aversion parameter. Most theoretically complete; hardest to explain. | Best long-term answer. v2. |

**Concrete confidence-floor framing:** because the optimizer maximizes at the Nth percentile, the natural confidence floor for the recommendation is `100% − N`. A 15th-percentile optimization gives an 85% confidence floor; a 25th gives 75%. This is the math behind the two-sentence outcome description in Part 8.5.

### 4.3a The optimization unit is goal × account **[LOCKED — Day 2 §1.1]**

The unit of optimization is the **goal-account cross**, not goal-alone or account-alone. If a single goal (e.g., Emma's $80k education) is funded across two accounts (TFSA + non-reg), those are **two separate optimizations** that get blended back into a single account-level portfolio.

Rationale: tax treatment differs by account type, so the same goal/duration/risk inputs can produce different optimal allocations depending on the account wrapper.

The engine consumes an **M-accounts × N-goals matrix** of `GoalAccountLink` entries (Part 6.3); each link is a separate optimization. Two-stage roll-up:

1. **Per-link optimization** — for each (goal, account) pair where allocated dollars > 0, compute the optimal blend using:
   - Time horizon (from the goal)
   - Combined risk score (from goal-level + household, per Part 4.2)
   - Tax drag adjusted to the account's tax treatment (Part 4.5)
2. **Account roll-up** — within each account, weight the per-link blends by their allocated dollars to produce one account-level holdings recommendation. If that recommendation closely matches an existing whole-portfolio fund (Founders, Builders), the system can recommend executing via that fund-of-funds for tax efficiency (Section 4.3b).

This is why the data model treats `GoalAccountLink` as a first-class entity (Part 6.3) and why the engine I/O contract returns per-link blends in `EngineOutput` (Part 12.1).

### 4.3b Recommended portfolio always sits on the frontier **[LOCKED — Day 2 §1.5]**

Even when the recommendation collapses to a single fund (Founders, Builders), the back end is solving the **same optimization** on the same efficient frontier. The collapse is an execution-level decision, not a recommendation-level shortcut.

The rule:
- Optimize as usual; produce a building-block-fund-level blend
- Compare blend composition against existing whole-portfolio funds (PACF, PABF, PAGF, Founders, Builders, etc.)
- Where the optimization output closely matches an existing fund-of-funds, **recommend executing via that fund-of-funds** for tax efficiency (no client-level rebalancing on the underlying)
- Where it doesn't, recommend the building-block-fund-level blend directly

**Same composition, fewer trade events.** This is also how Steadyhand existing portfolios (the "1.0" models) coexist with MP2.0 outputs — when MP2.0 lands on the same allocation as an existing model, it recommends the existing model.

### 4.3c Future-dollar targets are secondary input **[LOCKED — Day 2 §3.3]**

Leading with future-dollar projections is dangerous: clients latch onto the number, real-vs-nominal confusion is common, and naming a specific future amount raises the legal bar. The system's primary framing is risk × time-horizon, not target-dollar.

Future targets are **optional secondary input**, used when the client volunteers a specific number. They enable goal-attainment probability framing (Method 2 in 4.3) as a tab, not the primary view. The core flow does not require a dollar target.

This is also why Lori's caution prevailed at Day 2: the candidate one-sentence justification (Part 8.5) leads with "this allocation gives you the maximum portfolio value at a level of confidence aligned to your risk tolerance" — no future number unless one is explicitly provided.

### 4.3d Goal duration computation **[LOCKED — Day 3 morning, Fraser's framework]**

Duration is the time-horizon input the optimizer consumes for each `GoalAccountLink`. How it's computed depends on the *shape* of the goal — three patterns cover the v1 cases:

| Goal shape | Duration formula | Example |
|---|---|---|
| **Lump-sum goal** (buy a car, pay tuition, down payment) | `years_until_needed` | Car in 5 years → duration = 5 years |
| **Retirement estate goal** | `years_to_retirement + expected_years_in_retirement` | Age 51, retire at 65, life expectancy 95 → 14 + 30 = **44 years** |
| **Retirement income goal** | `years_to_retirement + (expected_years_in_retirement / 2)` | Same client → 14 + 15 = **29 years** at the planning moment, decaying to **15 years** at retirement |

**Rationales:**

- *Lump-sum* is straightforward — money is needed on a date; the engine glides toward cash as that date approaches (Part 4.4).
- *Retirement estate* uses the *full* expected retirement years because there is no lump-sum payout at retirement. The estate keeps running (and growing) through retirement; you don't move it to cash at age 65.
- *Retirement income* uses *half* the expected retirement years — the bond-duration analogy. Retirement income is paid out over many years; the midpoint/weighted-average horizon captures when the average dollar of that stream is needed. At the planning moment this is "years to retirement + half of post-retirement years"; at retirement itself it reduces to "half of remaining retirement years."

**Engine consequences:**

- The same household with a single retirement context typically produces **two `GoalAccountLink` optimizations** — one for the retirement income goal and one for the retirement estate goal — with different durations and therefore different optimal blends. That's expected, not a duplication problem.
- The duration is **recomputed on every optimization run**, not stored once. This matters because `years_to_retirement` decreases over calendar time, and the retirement-income duration formula is age-dependent.
- Edge cases (couples with different retirement dates, phased retirements, goals that span generations) are handled by goal decomposition: split into multiple goals with their own durations rather than overloading a single goal.

This framework belongs in `engine/duration.py` and is called once per `GoalAccountLink` before optimization.

### 4.4 Glide path & the cash building-block as risk-reducer **[LOCKED]**

As a goal nears its target date, the optimal blend should glide toward lower-volatility funds — and ultimately toward **cash**. The cash building-block fund (currently approximated by Steadyhand Savings/MMF, with ~2.1% expected return and ~0.5% modeled volatility) functions as the "risk-free corner" of the frontier.

In the model, as time-to-goal approaches zero, the optimizer naturally allocates more to cash. The engine should:
- Compute the optimal blend under current time-to-goal
- Compare to current blend
- Trigger rebalancing **only on material drift** (e.g., 3–5% absolute, or on significant client events) — not on every tiny shift. We don't want to trade for the sake of trading, especially given client communication overhead.

### 4.5 Tax drag — architecturally in scope, placeholder values for v1 **[LOCKED — Day 2 §1.4]**

A "light tax overlay" is in scope for v1 with concrete schema; numerical refinement is a May/June project.

**Schema:**

- Maintain a **per-fund** drag factor (or per-asset-class within a fund, where the fund composition is known)
- The CMA table holds the **asset-class composition per fund**, so drag rolls up correctly (e.g., a fund that's 75% bonds and 25% equity gets weighted drag from both asset classes)
- Apply drag to expected return when the fund sits in a non-registered (or otherwise taxable) account; do not apply when the fund sits in a registered account
- Default drag = 0 effectively disables the feature; the v1 MVP can ship with all drags at zero and still produce sensible recommendations
- Account-type awareness is the engine input: the optimizer asks the CMA layer for "expected return for fund X in account type Y" and gets the post-drag value

**Rationale (per Day 2):** *"When we demo it, I don't want someone screaming, you can't ignore taxes." Acknowledging tax exists is as important as solving for it perfectly.* The structure must exist before the values are right.

**Out of scope for the prototype** (Day 2 §Appendix):
- Province-by-province tax modeling
- Corporate account handling
- External income / total income level optimization
- Full capital gains harvesting, attribution, or in-kind transfer logic

These return as v2+ refinements once the v1 framework is running.

### 4.6 What the engine does NOT model in v1 — explicit gaps

These are knowingly missing from v1; flag them as v2+ work:

- **Currency / hedging decisions** (hedge ratios, FX overlays). Today buried inside fund internals.
- **Factor tilts** (value, growth, momentum, quality). Today emergent from fund mandates. *Behavioral risk* of factor concentration (clients bailing in a crisis on funds they don't emotionally connect with) is real and material — handled in v1 via CMA tuning that prevents extreme concentrations (Part 4.7) and via investment-specialist discretion, not by adding factor-tilt math to the optimizer (Day 2 §6.3).
- **Geographic / sector concentration look-through.** A future feature: re-aggregate the underlying atoms across all funds the blend holds, and flag concentration risks.
- **Full external-portfolio simulation.** v1 treats external holdings as a **simple risk-tolerance dampener** (Part 4.6a), not a full position model.

The offsite consensus: build v1 with these gaps explicit, then evaluate which to close based on what we observe with real personas.

### 4.6a External holdings — risk-tolerance dampener + collection methodology **[LOCKED — Day 2 §6.4 + Day 3 afternoon §8]**

External holdings (other-firm investments, real estate, business equity, private investments) are **optional input** in v1 and act as a simple **dampener** on the household risk score used for Purpose accounts:

- Higher external risk or larger external holdings push the household risk score *down* (more conservative) for the Purpose-managed portion
- This is a single-number adjustment, not a full external-portfolio simulation
- When external holdings aren't disclosed, the dampener is simply absent (no penalty, no warning)
- Full external-portfolio modeling (joint optimization across Purpose + external assets) is v2+

**Data collection methodology (Day 3 afternoon §8) — fallback hierarchy:**

1. **Statement upload** (preferred) — advisors push hard for external statements; most clients comply. AI ingestion (Part 11) detects external-statement documents (foreign institution headers) and auto-classifies; structured extraction populates approximate holdings.
2. **Conversational fallback** — if no statement available, the advisor asks for an approximate asset mix in conversation (e.g., "70% equity, 20% bonds, 10% cash") and approximate geographic split. Captured as note-derived facts with low confidence indicator (Part 6.5.1).
3. **Default fallback** — if the client won't disclose at all, **assume balanced allocation** as default. The dampener uses this default but the UI flags that external holdings are presumed, not disclosed.

**Data sources for the holdings-detail view:**
- **Steadyhand-internal funds:** Morningstar data drives asset class, geography, and fund-level breakdowns (Day 3 afternoon §8)
- **External funds:** client-provided data only; system does not look up external securities against Morningstar or any third-party reference. External holdings show at asset-class granularity only, never fund-level (see Part 8.7 holdings views).

**Future vision** (Day 3 afternoon §8): AI ingestion auto-classifies external statements as their own document type and routes them through a specialized extraction prompt — distinct from how Steadyhand statements are processed. v2+ work.

### 4.7 Capital market assumptions are an admin lever **[LOCKED — Day 2 §4 + Day 3 morning + Day 3 afternoon refinements]**

Purpose owns the CMA inputs (expected return, std dev, correlation matrix per fund, asset-class composition per fund, per-asset-class tax drag). These are not user-editable parameters; they are the firm's investment views.

**Important guardrail:** the optimizer will not concentrate to a single fund **as long as no fund is Pareto-dominant and all pairwise correlations are sub-1**. Tuning CMAs is therefore a legitimate guardrail to keep recommendations within the range of "fundable" allocations the firm is comfortable with. This is a feature, not a bug — extreme concentrations (e.g., 100% global small-cap equity) are prevented by the same CMA inputs that drive optimization.

**The CMA editor and the efficient frontier visualization are admin-only.** They live in the application but behind a permissions gate:
- **Financial Analyst** role: create/edit/save-draft/publish CMAs and view the efficient frontier (Day 3 afternoon §1.1)
- **Advisor / IS** role: separate read-only view (no edit, no frontier)
- All CMA edits write to the audit log with operator + timestamp + before/after values
- Note: this re-uses the Financial Analyst role from Part 9.2; Day 3 afternoon clarified that the role's authorized scope is CMA editing (not real-client PII surfaces, which it remains denied)

#### 4.7.1 Admin portal flow — draft / publish state model **[Day 3 afternoon §1.1]**

The CMA admin portal is a back-end surface where CIO/strategists enter:

1. **Expected return** per fund
2. **Volatility** (annualized standard deviation) per fund
3. **Correlation matrix** across the fund universe — stored as decomposed linear arrays / vectors (not as a full matrix structure) for efficient data mapping in the database

The state model is **create draft → edit → save draft → publish**:

- *Draft state* — visible only to the editing Financial Analyst. Multiple drafts can coexist without affecting client portfolios.
- *Save draft* — persists work-in-progress; no propagation, no advisor alerts.
- *Publish* — atomically writes a new `CMASnapshot` row, triggers an audit log entry recording who published which values when, and triggers the propagation flow (4.7.3).

Output: the **efficient frontier** of achievable portfolios, visualized on the admin page **and on a chart visualization that ships with the v1 CMA UI** (Day 3 afternoon §1.4 follow-up). Admins see the curve before publishing; the curve they see is the curve client portfolios will be drawn from. Publication writes a new `CMASnapshot` row that becomes the optimizer's input until the next publication.

#### 4.7.2 Update cadence and event handling **[Day 3 morning]**

- **Cadence:** approximately monthly, or triggered by major events (rate-cycle inflection, significant downgrades). Not real-time. CMA changes are expected to be **marginal most of the time** — meaningful but not whiplash.
- **Major market events** (bank run, broad downgrades) trigger broader portfolio reviews led by the **investment committee**, not by automated rebalances. The system provides the data backbone (which portfolios are affected, by how much) so the committee can decide; the system does not auto-execute.
- **Decision authority:** Steadyhand CIO / head of investment makes the final call on CMA changes. Purpose CIO provides input; Steadyhand leadership has decision authority. (This boundary may evolve as MP2.0 expands beyond Steadyhand.)

#### 4.7.3 Propagation, stale-portfolio state, and advisor alerts **[Day 3 morning + Day 3 afternoon §1.3]**

When a `CMASnapshot` is published, the system **does not auto-regenerate client portfolios.** Instead, every previously-generated portfolio that was optimized against the prior snapshot is marked **`is_stale = true`**.

- **Stale state** — the portfolio still displays correctly to the advisor with its previous numbers, but is visually marked as stale; the advisor must click **"regenerate"** to compute the new optimal blend against the published snapshot.
- **Why manual, not automatic:** Day 3 afternoon §1.3 — auto-update can confuse advisors who have mentally anchored to specific numbers in a recent client conversation. Manual regeneration gives advisors control and a clean before/after view to walk the client through.
- **Audit trail** — every regeneration event records the previous parameters and the new parameters; nothing is silently overwritten.
- **Future refinement (open question #59):** auto-update with a "delta from last dated portfolio" panel showing what changed, or a hover-over presentation of the same. Both options viable; team finalizes after UI integration.

In parallel with the stale-marking, the system identifies accounts whose newly-optimal allocation (under the new snapshot) has **drifted significantly** from current holdings:

- **Drift threshold for alert:** default >5% absolute deviation, or material event (configurable; aligns with Part 4.4 rebalancing logic). Compliance burden raises this threshold further — see Part 7.5a.
- **Advisor-facing summary:** "17 accounts are now >5% off their optimal allocation" appears in the advisor's client list / dashboard view
- **Alert routing:** alerts flow **to advisors**, never to CMA admins. The admins push the change; the advisors handle the consequences with their clients. CMA admins receive a publication confirmation, not a portfolio-impact list.
- **No auto-rebalance.** Drift detection generates a flag for advisor review, not an automated trade. The advisor decides whether to recommend rebalancing per Part 7.5.

#### 4.7.4 Math validation as a Phase B blocker **[Day 3 afternoon §1.4]**

The optimization engine is **the core compliance layer** — risk rating, efficient-frontier accuracy, and portfolio construction all flow from it. The team agreed to **pressure-test the math** thoroughly once the correlation matrix is integrated (Part 5.4). This includes:

- Validating Raj's backend-engine outputs against Fraser's reference model (both should produce equivalent efficient frontiers given the same inputs)
- Standard mean-variance optimization with matrix operations (inverse matrix, correlation, covariance) — the theory is settled; differences arise from iteration decisions or specific algorithm variants
- Pressure testing happens *after* correlation-matrix integration, not before; without correlations the math cannot be meaningfully validated

This validation is a **Phase B exit blocker**. The engine cannot drive real-client portfolio recommendations under pilot conditions until its outputs are reconciled with the reference model.

This sharpens what was previously the abstract "Macro Insight Layer" of Part 2.3 into something with a real UI surface, real permission boundary, real operational rhythm, and a concrete validation gate.

---

## PART 5 — FUND UNIVERSE

### 5.1 Initial fund universe (Steadyhand v1) **[LOCKED]**

The Steadyhand fund lineup is the v1 fund universe. Eight funds total; six are pure building blocks, two are whole-portfolio funds.

| Fund | Mandate | Role | Notes |
|--------|---------|------|-------|
| **Equity Fund** | ~160 companies, Canadian + global, mid/large cap, style-agnostic | Equity core | Primary equity building block |
| **Global Equity Fund** | International equities | Global diversification | Underperformed historically — flagged for review |
| **Small-Cap Equity Fund** (×2: Canadian + Global) | Small-cap exposure | Equity satellite | Two sub-funds |
| **Income Fund** | 75% Canadian bonds, 25% Canadian equities | Fixed income (impure) | **Identified as a constraint** — we need a true bond-only building block |
| **Cash / Savings (MMF)** | Money market | Risk-free corner of the frontier | Used for glide-path-to-goal |
| **Founders Fund** | Tactical balanced; ~60/40 long-term target, can flex 50–70% equity | Whole-portfolio fund, tactical | Currently ~55% cash. Hard to model quantitatively because of active tactical layer. Available as fund-of-funds collapse target (Part 4.3b). |
| **Builders Fund** | All-equity fund-of-funds | Aggressive whole-portfolio | Comprised of the four equity building blocks above. Available as fund-of-funds collapse target. |

For the v1 engine: **operate on the six building-block funds.** Founders and Builders are whole-portfolio funds and add modeling complexity (their active layer is hard to capture quantitatively). They are reintroduced via the **fund-of-funds collapse** suggestion in the optimizer (Part 4.3b) — when the optimal blend closely matches one of these whole-portfolio funds, the engine recommends executing via that fund for tax efficiency rather than holding the building blocks separately.

### 5.2 Building-block gaps to close (priority order)

1. **A pure bond-only building block.** This is the single highest-leverage addition to the v1 universe — it would meaningfully improve the shape of the efficient frontier. Already under discussion (Salman / Tom).
2. **A true cash / MMF building block** with zero modeled volatility (currently approximated by the Savings Fund at ~0.5% modeled vol).
3. **All-weather diversifier** — alternatives, hybrid, or inflation-protected exposure. Open question whether this comes from existing Purpose products (Hybrid, etc.).

### 5.3 Future fund strategy (post-Steadyhand)

When MP2.0 expands beyond Steadyhand, the fund universe grows. Key principles:

- **Building-block funds are real, papered funds with a PM attached** (the Harness Investment Committee made this a table-stakes requirement).
- **Building-block funds are launched ideally as ETFs** (universal accessibility, lowest cost), with mutual fund and SMA structures available where channel needs require.
- **Building-block funds use the same rigor as Purpose's existing whole-portfolio funds (PACF/PABF/PAGF).** No "quickly whipped together" allocations.
- Purpose's existing 16 whole-portfolio models (PACF, PABF, PAGF, Harness, Link, PIMP) coexist with MP2.0 — they don't get replaced; they sit alongside as the "1.0" option.

### 5.4 Capital market assumptions source **[OPEN]**

Fund return / vol / correlation inputs need a defensible source: Goldman, JPM, Basinger (Purpose CIO) views, or composite. This is more consequential than its position implies — placeholder CMAs produce placeholder portfolios, which becomes critical when advisors begin using output to inform real client conversations. **Owner: Saranyaraj + Fraser.** Resolution required before Phase B exit; pilot use cannot begin without defensible CMAs in place. If unresolved at the Wednesday Som demo, the demo narrative must explicitly say "illustrative numbers" upfront.

**Correlation matrix is a blocking dependency for efficient-frontier validation** (Day 3 afternoon §1.2): without a real correlation table, the engine has to assume zero correlation or arbitrary values, and the math cannot be pressure-tested against Fraser's reference model. Integrating the correlation matrix into the optimization engine is a Phase B prerequisite to any pilot use.

The CMA values themselves live behind the admin-only editor (Part 4.7) — that's the *where they're managed* question. This section is the *where they come from* question. Both must be answered before pilot launch.

---

## PART 6 — DATA MODEL & REQUIRED INPUTS

This section is the contract between the intake layer and the engine. Schemas live in `engine/schemas.py` (see Part 10).

### 6.1 Household entity

```
Household {
  id
  type: single | couple
  members: Person[1..2]
  external_assets: ExternalAsset[]   // optional, where known
  household_risk_score: int           // composite, see 4.2
  householding_consent: {             // see Day 3 afternoon §7.2
    consented: bool                   // true only when each member has signed
    consent_form_ids: list[str]       // signed-form references per person
    consented_at: datetime
  }
  created_at, updated_at
}
```

**Householding consent (Day 3 afternoon §7.2):** clients must sign a consent form to be viewed under the same household. **Privacy among couples is real** — one partner may not want the other to see their full financial situation. The system enforces:

- A single person is always a valid household (household of one) — no consent required for their own data
- Two-person households require both consents on file; if either is missing, the system shows the persons' accounts separately and does not roll up
- The consent form is a Steadyhand-provided document (paper or DocuSign per Part 7.5); MP2.0 stores the reference (form ID, signed date) but does not host the signing flow itself
- Withdrawing consent (e.g., after separation) is supported but flagged for advisor review — re-householding is a non-trivial change with downstream effects on every household-level report

### 6.2 Person entity

```
Person {
  id, household_id
  name, dob
  marital_status, blended_family_flag
  citizenship, residency
  health_indicators, longevity_assumption
  employment: { type, income_gross, income_net, expected_changes }
  pensions: Pension[]                 // DB / DC / CPP / OAS eligibility
  investment_knowledge: low | medium | high
  trusted_contact_person
  poa_status, will_status
  beneficiary_designations
}
```

### 6.3 Goal entity — central to MP2.0

```
Goal {
  id, household_id
  name                                  // e.g., "Buy cabin", "Retirement income", "Retirement estate"
  goal_shape: lump_sum                  // drives duration formula per Part 4.3d
            | retirement_estate
            | retirement_income
            | other                     // fallback; explicit duration must be set
  target_amount, target_date            // OPTIONAL — secondary input only when client volunteers (Part 4.3c)
                                        //   For lump_sum, target_date drives duration
                                        //   For retirement_*, retirement_date + life_expectancy drive duration
  retirement_date                       // person reference; required for retirement_* goal_shapes
  life_expectancy                       // person reference; required for retirement_* goal_shapes
  necessity_score: 1..5                 // wish → want → need
  current_funded_amount
  contribution_plan: { monthly, annual, lump_sum_dates }
  account_allocations: GoalAccountLink[]  // many-to-many
  goal_risk_score: 1..5                  // 5-point scale per Part 4.2; snap-to-grid
  status: on_track | watch | off_track
  notes
}

GoalAccountLink {
  goal_id, account_id
  allocated_amount   // dollars of this account earmarked for this goal
  allocated_pct      // alternative representation
  // The (goal, account) pair is the unit of optimization — see Part 4.3a
  // Each link runs through its own optimization with the link's combined risk score
  // Per-account roll-up weights link blends by allocated_amount
}
```

The advisor sets `account_allocations` via the click-through workflow (Part 8.8). AI ingestion attempts to extract these mappings from notes (Day 2 §2.2 — *"the $25k in the TFSA is for Emma's school"*) but the advisor validates / overrides.

Duration is **derived per optimization run** from `goal_shape` + the relevant date inputs, not stored on the Goal entity. See Part 4.3d.

### 6.3a Re-goaling — conceptual, not money-movement **[LOCKED — Day 3 afternoon §5.2]**

Clients' goals evolve over time. The system needs a mechanism for advisors to **re-label or re-apportion dollars between goals within an account** without implying any actual asset reallocation.

This is a **conceptual overlay**, not a money-movement operation. **Vocabulary discipline matters and is locked:**

| Use | Avoid |
|---|---|
| ✅ "re-goaling" | ❌ "reallocation" (implies asset reallocation; compliance issue) |
| ✅ "goal realignment" | ❌ "transfer" (implies wire transfer; client confusion) |
| ✅ "re-label dollars between goals" | ❌ "move money" (implies actual movement) |

**Why the discipline matters:** if a client (or regulator, or another advisor reading the audit log) reads "$25k reallocated from cabin goal to retirement goal," that reasonably reads as a transaction. It isn't — no shares were sold, no cash moved, no fund position changed. The same dollars are now labeled with a different goal. Calling that "reallocation" creates a documentation problem when reconciling against actual trade history.

**Engine effect:** when the goal mix on an account changes (re-goaling), the account's blended risk/horizon profile changes, which **triggers a new portfolio recommendation** at the account level. The recommendation may suggest actual trades — but those are the *consequence* of the conceptual change, not the change itself.

### 6.3b Default goal classification when client goals are undefined **[LOCKED — Day 3 afternoon §5.3]**

When a client says "I just want to save" with no defined goals, the system needs a default rather than blocking on intake.

**MP2.0 v1 default:** in the absence of defined goals, classify the funds as a split between:

- **Emergency fund** (short-term, conservative, lump-sum shape with 0–3 year horizon)
- **Retirement** (long-term, retirement-income shape using Part 4.3d duration formula)

Fraser's framing: *"If someone won't tell us, we assume retirement + emergency fund, because in the absence of other information, that's what you're saving for."*

**Regulatory wording constraint:** "savings" implies cash to regulators. Don't use bare "savings" as a goal name; use **"long-term savings"** or **"undefined goal"** with internal sub-categorization, or split into the explicit emergency/retirement defaults above. Owner: Lori + Fraser will determine the final regulator-friendly wording (open question #61).

The advisor can override or refine the defaults at any time; this is a *starting point* when intake produces no goal signal, not a permanent assignment.

### 6.4 Account entity

```
Account {
  id, household_id, owner_person_id
  type: RRSP | TFSA | RESP | RDSP | FHSA | Non-Registered | LIRA | RRIF | Corporate
  regulatory_objective: income | growth_and_income | growth   // Steadyhand 3-bucket
  regulatory_time_horizon: <3y | 3-10y | >10y
  regulatory_risk_rating: low | medium | high                 // mapped from blend
  current_holdings: Holding[]                                  // building-block-fund allocations
  contribution_room, contribution_history
  is_held_at_purpose: bool
}
```

### 6.5 Risk inputs

```
RiskInput {
  household_score: 1..5                  // 5-point scale, snap-to-grid; composite of:
    - investment_knowledge
    - income_net_worth_band
    - behavioral_loss_aversion
    - behavioral_follow_through
    - sentiment_under_volatility
    - tax_sensitivity
    - external_holdings_dampener         // Part 4.6a; reduces score if disclosed
  household_confidence: 0.0..1.0         // confidence in the household score (Part 6.5.1)
  goals: { goal_id -> {
      score: 1..5,                       // single question per goal
      confidence: 0.0..1.0
  } }
  rationale: { field -> str }            // per-field "why this score" — required for compliance
}

// Engine-derived per (goal, account) pair:
ResolvedRisk {
  goal_id, account_id
  household_component: 1..5     // surfaced to advisor (Part 4.2)
  goal_component: 1..5          // surfaced to advisor
  combined_score: 1..5          // surfaced to advisor; what the optimizer uses
  combined_percentile: int      // 5 | 15 | 25 | 35 | 45 (Part 4.3)
  combined_confidence: 0.0..1.0 // worst of household + goal component confidences
  needs_advisor_input: bool     // true when combined_confidence < threshold (default 0.7)
}
```

The engine's risk input for a given (goal, account) is `combine(household_score, goal_risk_score)`. Default combination function for v1: a documented weighted blend; the weights are a tunable parameter we expect to refine.

The three components (`household_component`, `goal_component`, `combined_score`) are exposed to the advisor in the UI via an info icon / drill-down (Day 2 §1.3). All three are visible — the system does not hide the math.

#### 6.5.1 Confidence indicators **[LOCKED — Day 3 morning]**

Risk scores carry confidence values (0.0–1.0) reflecting the strength of evidence behind them — modeled on the Ike agent pattern. Below a configurable threshold (default **0.7**), the system flags the score as **needing advisor input** rather than presenting the score as if it were settled.

Sources of confidence signal:

- **Document evidence depth** — were multiple notes consistent? Did one note contradict three? Did the source explicitly mention risk tolerance or did the model infer from context?
- **Recency** — recent observations weight higher than five-year-old notes
- **Specificity** — "she's anxious about market drops" is higher-confidence than "she seems careful"
- **Cross-source agreement** — KYC + meeting notes + statement behavior aligning is high-confidence; one source disagreeing flags lower

Behavior:

- `combined_confidence` is the worst (lowest) of `household_confidence` and the active goal's `confidence`
- When `combined_confidence < 0.7`, the UI surfaces a "please confirm" prompt at the moment the advisor opens the goal-account view; the engine still produces output but visually marks it as low-confidence
- Confidence does not affect the engine math itself — it affects the UX framing and the advisor's review priority

**Compliance angle (Day 3 morning):** the score alone is insufficient — *"3 out of 10"* with no rationale fails both compliance and practical correction. Every risk score must come with a documented rationale (`rationale` field) that the advisor can read, verify, and override.

### 6.6 Behavioral / soft data — captured from meeting notes

This is where the AI extraction layer earns its keep. From unstructured notes, extract:

- Communication style preferences (numbers-driven, visual, narrative, goal-focused)
- Reaction history (panicked in 2020? steady through 2022? called frequently?)
- Follow-through pattern (acts on advice / doesn't)
- Topics they care about (legacy, lifestyle, security, optionality)
- Sensitive topics to handle carefully (recent loss, family conflict, etc.)

These feed two systems:
1. The household risk score (some of these are inputs).
2. The reporting layer — to personalize tone and emphasis (see Part 8).

### 6.7 Onboarding inputs — document drop is primary, structured questionnaire is fallback **[LOCKED — Day 3 afternoon §4.1]**

**The primary onboarding path is the document drop zone:** advisors upload all available client documents (meeting notes, statements, KYC, plans) and AI extracts structured data (Part 11). The **structured questionnaire** is the **secondary/fallback path** for edge cases where document extraction misses required fields.

This reflects real-world advisor workflow: open-ended initial conversations come first; documents arrive afterward. **The structured intake form is not typically completed face-to-face** — making the structured form the primary path would be building for an advisor reality that doesn't exist.

The system still defines a **minimum viable input set** that the engine requires to produce a portfolio recommendation. Whether these come from document extraction or structured fallback questions, the same set must be populated by Phase B exit:

1. Household composition (1 or 2 people, ages)
2. Total investable assets at Purpose
3. At least one named goal — `goal_shape` (lump-sum / retirement-income / retirement-estate / other) drives duration; target dollar amount is **optional secondary input** per Part 4.3c
4. Household risk tolerance (composite, with confidence indicator per Part 6.5.1)
5. Goal necessity (1 question per goal — need / want / wish)
6. Account types and holdings (Steadyhand-internal via CAT/Resource integration; external via document or conversational fallback per Part 4.6a)
7. Time horizon per goal (derived from `goal_shape` + dates per Part 4.3d, not asked directly)
8. Goal-to-account mapping for each `GoalAccountLink` with non-zero allocated amount

If the system has these, it can produce a v1 portfolio. More data → better personalization. Less data → MP2.0 is still possible but degraded.

The fallback questionnaire (open question #62) has not yet been finalized; Lori will share an HTML version for the team to revise before Phase B.

---

## PART 7 — REGULATORY & COMPLIANCE CONSTRAINTS

These are not aspirational; they are hard rails. Build them in, don't bolt them on.

### 7.1 Regulatory frame at Steadyhand (v1)

- Steadyhand operates under **MFDA** (now CIRO, but operational practice still references MFDA terms).
- KYC + suitability is a **defined, mandatory question set** at account opening; refresh every 3 years (annual under IIROC where applicable).
- All client interactions are **documented in CRM (Croesus)**: meeting notes, calls (recorded audio), DocuSign for transactions.
- **No discretionary management.** Every transaction requires explicit client approval (verbal or DocuSign).

### 7.2 What Steadyhand Investment Specialists CAN and CANNOT do

CAN:
- Provide **investment advice** on Steadyhand products.
- Recommend portfolio allocations within the Steadyhand fund set.
- Have rich, holistic client conversations (and routinely do — Steadyhand "over-serves" relative to its mandate).
- Reference outside products in **general** terms.

CANNOT:
- Provide **comprehensive financial planning** (only CFP / QAFP-designated planners can).
- Give prescriptive advice on outside products.
- Manage discretionarily.
- Nickname accounts with goal labels in the regulatory system.

**Implication for MP2.0:** the system can present rich planning views to the client and the IS, but must clearly delineate between "investment recommendation" (which an IS can make) and "financial plan" (which requires a CFP/QAFP). For Steadyhand v1, the system supports the IS workflow; it does not pretend the IS is doing comprehensive planning.

Lori's offsite action: **compile the explicit list of can/cannot for the team.**

### 7.3 Account-level regulatory caps (Steadyhand)

Each account has a regulatory **investment objective**:

| Objective | Equity cap | Use |
|-----------|-----------|-----|
| Income | ≤10% equity | Short-term savings, income-only |
| Growth and Income | ≤60% equity | Most clients sit here |
| Growth | Up to 100% equity | Long-term growth |

The engine must respect these caps when producing an account-level blend. If the math wants 75% equity in a Growth-and-Income account, the engine must either (a) shift the objective with client consent, (b) cap at 60% and explain the trade-off, or (c) move money to a Growth account where space exists.

### 7.4 Translating MP2.0 portfolios back to a compliance risk rating **[OPEN]**

The optimizer outputs a continuous, multivariate blend. Compliance wants a discrete bucket (low / medium / high) at both the **account** and **client** level.

The system must include a deterministic mapping function:

```
risk_rating(blend) -> {low, medium, high}
```

Likely based on the blend's modeled volatility band, equity %, and time horizon. This function must be explainable, auditable, and consistent across clients. **Owner: Lori + Saranyaraj.**

### 7.5 Client approval, advisor override, and documentation **[LOCKED — Day 2 §7]**

For any portfolio recommendation MP2.0 generates:

- Must be **validated by an advisor / IS** before presentation.
- Must be **approved by the client** before execution (recorded verbally or via DocuSign).
- Must be **documented in CRM** with disclosure of risk level and any deviation from the household profile.
- Audit log must capture inputs → engine output for regulatory review.

**Two override mechanisms** are supported, and they are not equivalent:

1. **Pre-recommendation override (preferred).** The advisor adjusts an *input* — most commonly the goal-level risk slider — and the engine regenerates a different optimal portfolio. This changes a parameter rather than overriding an output, so the resulting recommendation is fully reasoned by the engine. Audit log records: which input changed, who changed it, why (free-text note), before / after values, the resulting recommendation.

2. **Post-recommendation override (when needed).** The advisor sees the engine's recommendation and chooses not to execute it. No mechanical override is required — the portfolio simply remains unchanged — but a **mandatory note** explaining why must be captured. Audit log records: the recommendation that was not executed, the advisor, the reason note, the timestamp.

**Why the distinction matters:** if the system recommends X and the advisor executes Y, the firm needs documented rationale. Pre-recommendation override produces a clean trail (the advisor changed an input, the engine reasoned to Y, the advisor approved Y). Post-recommendation override produces a different trail (the engine reasoned to X, the advisor declined, here's why). Both are legitimate; both must be captured.

**Friction tension flagged at Day 2:** Steadyhand advisors already note every interaction (change of address, password reset, tax slip questions). Adding another mandatory note category is real friction. The override note should be inline in the recommendation review screen, not a separate workflow.

### 7.5a Compliance burden raises the rebalancing threshold **[LOCKED — Day 3 afternoon §7.1]**

Every new fund purchase under Steadyhand's MFDA/CIRO operating model triggers a fixed compliance burden:

- **Fee disclosure** must be presented before purchase
- **Fund fact sheet** must be delivered to the client
- **Suitability documentation** must be captured

This is per-trade, not per-rebalance — buying three new funds at once means three sets of disclosures. Combined with the trade-level consent rule (Part 8.10), the cost of any rebalance is a non-trivial advisor + client time investment.

**Implication for the rebalancing trigger:** small drift may not be worth the operational cost. The system must define a **minimum rebalancing threshold** that combines:

- **Percentage minimum** (default 5% absolute drift per fund or per asset class — refined from Part 4.4's "3–5%" default)
- **Dollar minimum** (TBD — Fraser's follow-up; small accounts may have a different threshold than large ones)

Drift below either threshold is logged but does not generate a "rebalance recommended" alert. **Owner: Fraser** (Day 3 afternoon §10 task list — define rebalancing trigger thresholds, % + $ minimums).

**Future relief:** Day 3 afternoon discussed the possibility of MP2.0 becoming **fully discretionary** in some future state, which would dramatically reduce the per-trade compliance burden (advisor doesn't need explicit per-trade consent on a discretionary mandate). Out of v1 scope; flagged as a strategic option for v2+.

**Every new fund purchase still requires fee disclosure and fund fact sheet delivery** even when the system is discretionary in future — that's a CRM 3 / regulatory requirement (Part 7.6), not an MFDA operational rule. The fund-fact-sheet flow ships with the trade-list UI in Part 8.10.

### 7.6 CRM 3 fee transparency

CRM 3 requires full disclosure of fund expense ratios (FER) plus advisor fees. Steadyhand has been ahead of this. MP2.0 reporting must include total expense view as standard.

### 7.7 The evolving digital-advice frontier

The OSC and CSA are actively working on digital advice frameworks. Amitha (Purpose legal) is on the digital asset management working group. Direction: regulators want **structured, human-in-the-loop digital advice** — they recognize the alternative is consumers taking advice from ChatGPT. MP2.0 can be on the right side of this if we build with the right guardrails: deterministic intake, explainable outputs, audit logs, validated outputs, client approval steps.

---

## PART 8 — REPORTING & CLIENT COMMUNICATION

This is where MP2.0's "outcomes-first, not returns-first" philosophy becomes visible to the client.

### 8.1 The reporting philosophy shift

Old world: "Your portfolio returned 6.2% YTD vs. the benchmark's 5.8%."

MP2.0 world: "You started the year with an 87% chance of hitting your retirement goal. After this year's market and contributions, you're now at 91%. Here's why."

Two reporting tracks coexist:

1. **Regulatory reporting** — quarterly statement, fees, holdings, performance. Compliance-mandated. Doesn't go away.
2. **Goal-progress reporting** — the new thing. Lives in the portal. Shows goal-by-goal progress, probability of attainment, what changed and why.

### 8.2 Three levels of reporting

Reports must be available at three levels and explain the connection between them:

| Level | Question it answers |
|-------|---------------------|
| **Goal** | "Am I on track for *this* goal? What's my probability of hitting it?" |
| **Account** | "What's in this account, and how does it support the goals it serves?" |
| **Household** | "Are we, as a family, going to be okay?" |

Novel insight Fraser pushed: report **retrospectively** as well as prospectively. Plans are usually only forward-looking. Showing a client "you set this goal in January, you were 90% likely; after market moves and contributions, you're now 91% likely" is psychologically empowering and builds trust.

### 8.3 AI-personalized updates

The reporting layer should generate **personalized** updates — not generic newsletters.

- Tone and format adapt to the client's communication preferences (numbers / visual / narrative — captured in Section 6.6).
- Content is grounded in the client's actual plan and portfolio, not generic market commentary.
- Determinism in the workflow is critical: AI generates *within* a structured template, not from scratch. Static-or-configurable intake → deterministic engine → AI-styled output. **The output should never include numbers that didn't come from the engine.**
- Frequency: quarterly automated, plus event-triggered (large move, life event, goal milestone hit/missed).

### 8.4 Three-tier dynamic reporting **[LOCKED — Day 2 §6.1]**

Every report and recommendation surface supports **three sophistication tiers** ("choose-your-own-adventure"):

| Tier | Content style | Use for |
|---|---|---|
| **Tier 1** | High-level / non-numeric / outcome-language only | Less financially-engaged clients; "are we okay?" framing |
| **Tier 2** | Moderate detail with averages and ranges | Most clients; default starting point for many |
| **Tier 3** | Full sophistication, percentiles, fan charts, drill-down math | Sophisticated clients, advisors reviewing internally |

**Default tier is inferred from client sophistication signals in notes** (e.g., references to specific investment vehicles, tax planning, options, performance attribution → higher tier). The client (or advisor on their behalf) can manually click up or down a tier at any time. Generative AI produces tier-appropriate copy from the **same underlying engine output** — different wrappers around the same deterministic numbers.

**Principle (Day 2):** *Do not lowest-common-denominator the UI.* Financial literacy is a positive externality of well-designed reporting; clients who choose Tier 2 or 3 should be served at that level, not protected from it.

**Behavioral bucketing within tiers.** Within a tier, the orientation can still vary by behavioral profile (numbers-driven, visual, reassurance-seeking, curious/explorer per Section 6.6). Tier governs *depth*; behavioral bucket governs *emphasis* and *opening framing*. They compose, not conflict.

### 8.5 "Why this portfolio?" — sentence templates **[LOCKED — Day 2 §3.1, §3.2]**

The system produces concrete plain-language narrative at the moment of recommendation. Templates are **deterministic** (no AI invention of numbers) and tier-appropriate:

**One-sentence justification** (advisor-facing, also usable client-facing for most clients):

> *"Based on your time horizon of [X years] and your [risk descriptor] risk profile, this allocation gives you the maximum portfolio value at a level of confidence aligned to your risk tolerance."*

Simplified for less-sophisticated clients (Tier 1):

> *"This allocation gives you the maximum amount of money for someone of your risk tolerance."*

**Two-sentence outcome description** (Tier 2 / 3, when an outcome view is being shown):

> *"Your portfolio is $[current] today. We expect that in [N] years your average balance would be $[expected]."*
> *"You would have an [confidence]% chance of having at least $[floor]."*

The confidence figure is `100% − optimization percentile` (Part 4.3). Optimizing at the 15th percentile produces 85% confidence; at the 25th, 75%; etc.

**By client risk profile:**

- **Cautious / Conservative-balanced** clients — emphasize the confidence floor (the second sentence is the one they'll latch onto).
- **Balanced** clients — show both sentences equally.
- **Growth-oriented** clients — drop the second sentence; replace with the median outcome.

**Pyramidal expansion.** The advisor (or client at higher tiers) can expand from the one-sentence to the two-sentence to a full breakdown — same content, deeper layers. The IS picks the depth in the moment.

### 8.6 Money-in-motion / event detection

The portal should detect significant events — address change, large deposit, large withdrawal — and proactively prompt a goal/plan review. Today this is reactive. In MP2.0 it's a Stage-6 trigger.

### 8.6a Two distinct alert categories — "needs attention" lexical split **[LOCKED — Day 3 morning]**

The team identified that *"needs attention"* was being used in the UI for two materially different concepts. They get distinct labels because they require distinct advisor responses:

| Category | Source | Example | UI label (working) |
|---|---|---|---|
| **Data ingestion alerts** | Layer 1–4 of the extraction pipeline (Part 11) | Conflicting facts across documents; missing required fields; failed extraction; low-confidence risk score | *"Review needed"* — sits on the review workspace, blocks `engine_ready` until resolved |
| **Portfolio / planning alerts** | Engine + monitoring layers post-commit | Goal off-track; significant drift after CMA update; fan-chart breach (Part 8.9); life event detected (Part 8.6) | *"Action recommended"* — sits on the dashboard / client list, prompts an advisor conversation |

**Why the distinction matters.** A "review needed" alert means the system can't produce reliable output yet — the input is incomplete or inconsistent. An "action recommended" alert means the system has produced output and is signalling that the client's situation may have changed. Different urgency, different workflow, different audit trail.

The exact UI strings are TBD with Lori (open question). The lexical separation is locked.

### 8.7 The three-tab household / account / goal view **[LOCKED — Day 2 §2, sharpened Day 3 morning + Day 3 afternoon]**

This is the front-end paradigm Day 2 identified as genuinely novel — *"nobody is doing this. I haven't seen a visual of an account that holds two different goals."* (Lori) Fraser's framing: *"We're redesigning how advisors view their client's book."*

The total client AUM (e.g., $1.28M) should be **sliceable three ways**, each viewable by **funds** or **look-through to asset classes**:

| Tab | What it shows |
|---|---|
| **Household** | Total AUM, no partitioning. Holistic view. "Here's everything we manage." |
| **Account** | Same total, split across accounts proportionally. The advisor's traditional view. |
| **Goal** | Same total, split across goals (current allocated dollars, not future targets). Novel view. |

**Pivot-table principle:** the grand total in the bottom-right corner is always $1.28M; only the slices change. Every view reconciles to the same household total — no "money goes missing" between views.

**Fund / asset-class toggle:** within each tab, the advisor toggles between (a) a fund-level view (showing the actual building-block funds held) and (b) a look-through-to-asset-classes view (re-aggregating fund internals to show overall equity / fixed income / cash exposure). The latter is the natural lens for the "is the household risk profile aligned?" conversation.

**Visual specifics (Day 3 morning):**

- *Vertical slices = accounts; color-coded goal allocations within each account.* Goals are color-coded **consistently across the entire UI** so the advisor can instantly see "~90% earmarked for retirement" without arithmetic.
- *Hover for detail.* Hovering over a goal slice or account slice reveals the detailed portfolio allocation (fund-level blend, current vs. ideal — Part 8.8).
- *Pivot.* The view flips between "accounts sliced by goals" and "goals sliced by accounts" — the same data, two readings. This *is* the visual pivot table the canon names; both directions are first-class.
- *Composite at the account level.* The blended portfolio allocation visible at the account level is the composite of per-goal-account-link blends within that account (Part 4.3a roll-up).

**Holdings views — Steadyhand internal vs. external [Day 3 afternoon §6.2]:**

The view distinguishes Steadyhand-managed holdings from external holdings at every level of detail:

| Source | Detail available | Notes |
|---|---|---|
| **Steadyhand internal** | Full detail: asset class, geography, fund-level breakdown | Morningstar data drives the breakdown (per Part 4.6a). This is the data the advisor can act on. |
| **External holdings** | Asset-class view only (geography if available) | Sourced from client-provided statements or conversational fallback (per Part 4.6a). Fund-level detail is *not* shown — the system doesn't have it and shouldn't pretend to. |
| **Combined view** | Total household AUM showing internal + external combined asset-class breakdown | Important for ensuring the overall household isn't overconcentrated. The combined view never shows fund-level detail (because external is asset-class only). |

**Click-to-reveal pattern for external holdings (Day 3 afternoon §6.2).** External holdings are hidden by default behind a click-to-reveal control. This protects against the case where an advisor turns the screen toward a client and the screen shows the client's external (other-firm) holdings — a plausible privacy concern. The advisor explicitly opts in to revealing the external section.

**Why this is the wow:** clients don't typically map goals to accounts mentally; advisors do, from meeting notes. The goal-view tab makes that mapping visual for the first time. Steadyhand notes already implicitly contain this mapping ("the $25k in the TFSA is for Emma's school"); MP2.0 surfaces it.

### 8.8 Click-through workflow for setting a portfolio **[LOCKED — Day 2 §2.3 + Day 3 afternoon §6.3]**

The advisor sets up a portfolio for an account through a structured click-through, not a free-form form fill:

1. **Click into an account** (e.g., $80k non-reg)
2. **Identify which goals it serves** (click, click — pick from the household's goals, or create a new goal inline)
3. **Assign proportions** (e.g., 50% to education, 50% to emergency fund)
4. **For each goal-account combo, the system pulls the duration + risk inputs and recommends a portfolio.** The advisor sees *"we recommend this"* — **the efficient frontier and apex curves are NOT shown** (those live behind the admin-only view, Part 4.7). Just the recommendation, with the one-sentence justification (Part 8.5).
5. **Repeat for each goal in that account.**
6. **System merges the per-goal-account recommendations into the consolidated account portfolio**, possibly collapsing to a single fund-of-funds if optimal (Part 4.3b).
7. **Client consents at the trade level** (Part 7.5 + Part 7.5a) — not just the end-state level. See Part 8.10.

**Current vs. ideal — comparison rules differ by client situation [Day 3 afternoon §6.3]:**

| Client situation | Comparison view shown? | Rationale |
|---|---|---|
| **Existing client with current holdings** | Yes — current vs. ideal side-by-side, by asset class, by fund, by geography | The advisor needs context to discuss what changes and why. |
| **New client (cash coming in)** | No — show only the ideal portfolio and allocate directly | There are no current holdings to compare against; a comparison view would be misleading. |

This is a UX-mode decision, not a permission rule: the same advisor uses both modes for different clients on the same day. The system detects "no current holdings" and switches modes automatically.

### 8.9 The fan chart as longitudinal reporting primitive **[LOCKED — Day 2 §3.4 + Day 3 afternoon §6.4 sharpening]**

The fan chart isn't only a "what might happen" projection at recommendation time — it's an ongoing reporting artifact and a household-level visualization in its own right.

**Recommendation-time behavior (Day 2):**

1. **Lock the fan at time zero** when the portfolio is set. The fan represents the engine's projection at that moment.
2. **Place a dot on the chart at the goal date** (only when a dollar target is known — see Part 4.3c).
3. **Over time, plot the actual portfolio value** moving through the fan.
4. **Conversation trigger:** when actual value drops outside the bottom of the fan, the system flags this as a Stage-6 event prompting a plan review.

**Household-level fan chart (Day 3 afternoon §6.4):**

- Shows **current portfolio vs. optimized portfolio** projections *overlaid* on the same chart — two fans, one current, one optimized, with overlap regions visible. This makes "what would change if we rebalanced" a visual question, not a numeric one.
- **Interactive on hover** — hovering at any year reveals the dollar values at each percentile band (P5, P25, P50, P75, P95) for both the current and optimized fans.
- **Do not hard-anchor to a specific time horizon at the household level.** At the goal level, time horizons make sense (each goal has its own duration per Part 4.3d). At the household level they don't, because different goals have different horizons. The household chart shows a generic projection window, not a single goal's duration.
- **Cap at life expectancy.** The chart can extend ~30 years but should cap at the client's life expectancy to avoid projecting beyond plausible timeframes for older clients.

**Sophistication tiers map to fan chart presentation [Day 3 afternoon §6.4]:**

| Tier (Part 8.4) | Fan chart shown |
|---|---|
| **Tier 1 (101-level)** | Just the median line. No bands, no percentiles. |
| **Tier 2 (201-level)** | Median + outer bands (P5 / P95). |
| **Tier 3 (301-level)** | Full percentile detail with hover values at all bands. |

**Core principle:** even Tier 1 clients should see *some* concept of uncertainty. **Deterministic "you'll get 7%" projections are what MP2.0 is designed to replace** — single-line projections without uncertainty are not acceptable at any tier. The Tier 1 simplification reduces detail, not honesty.

### 8.10 "Express as moves" — trade-level rebalancing UX **[LOCKED — Day 3 afternoon §6.3 + §7.1]**

The recommendation engine produces an *end-state* portfolio (current → ideal). Compliance requires that **client consent be captured at the move level** — sell X shares of Fund A, buy Y shares of Fund B — not just at the end-state level (Part 7.5a).

The **"Express as moves"** control on the comparison view (Part 8.8) generates the trade list:

1. The advisor shows the client current vs. ideal side-by-side.
2. On agreement to proceed (in principle), the advisor clicks **"Express as moves"**.
3. The system computes the specific trades required to transition current → ideal: a sequence of sells and buys, with quantities and approximate values.
4. The trade list appears below the comparison; the client consents per-trade or to the batch.
5. Each consent is captured (verbal or DocuSign per Part 7.5) and feeds the audit trail.

The trade list is the operational artifact that hits Stage 4 (execution — mocked in MVP per Part 3). For new-client cash-coming-in flows (Part 8.8), this control is replaced by an "Allocate" action that produces an initial-buy trade list directly from the ideal portfolio.

---

## PART 9 — ENGINEERING: STACK, ARCHITECTURE, INFRASTRUCTURE

### 9.1 The full stack **[LOCKED unless tagged otherwise]**

| Layer | Choice | Status | Rationale |
|---|---|---|---|
| **Backend framework** | Django + Django REST Framework | LOCKED | Python ecosystem (matches engine + quant tooling); admin panel + auth + ORM out of box; DRF gives clean React-ready APIs |
| **Frontend framework** | React + Vite | LOCKED | Industry standard; Claude generates React natively |
| **Component library** | shadcn/ui + Tailwind | LOCKED | What Claude generates in artifacts; team owns the component code; professional aesthetic for advisor tools |
| **Frontend data layer** | TanStack Query | LOCKED | Caching, mutations, optimistic updates; no need for Redux |
| **Charts** | Recharts (primary), Visx/D3 (escape hatch) | DEFAULT | Recharts is what Claude generates; Visx for what Recharts can't do |
| **Database (operational)** | Postgres + pgvector extension | LOCKED | Boring + correct; JSONB for semi-structured; pgvector handles RAG without a separate system |
| **Object storage** | S3 (ca-central-1) | LOCKED | Raw documents, generated PDFs, statements |
| **Secrets** | AWS Secrets Manager | LOCKED | No env files in source; rotation-ready |
| **Cloud** | AWS, ca-central-1 (Montreal) | LOCKED | Purpose's existing posture; data residency for Canadian PII |
| **AWS account** | Existing Purpose account, MP2.0 namespace inside | LOCKED | Confirm IAM boundary + tagging convention with Purpose IT |
| **Compute** | ECS on EC2 (Purpose house style) | LOCKED | Other AWS abstractions selected as needed |
| **CI/CD** | GitHub Actions → ECR → ECS | DEFAULT | Adapt to Purpose IT's existing pattern if different |
| **LLM (development)** | Anthropic API direct | DEFAULT | Latest models, full feature surface, fastest iteration |
| **LLM (production)** | AWS Bedrock (Claude) | DEFAULT | Data residency in trust boundary, IAM-native, billing through existing AWS |
| **Observability** | OpenTelemetry SDK → Elastic APM | LOCKED | Vendor-neutral instrumentation; Elastic accepts OTLP natively |
| **Logging** | Structured JSON to stdout → Elastic via Filebeat/Fluent Bit | LOCKED | Whichever shipper Purpose's pattern uses |
| **Audit log** | Separate Postgres table, append-only | LOCKED | Different system from observability — different retention, access, consumers |
| **Local dev** | Docker Compose (Django + Postgres + Vite) | DEFAULT | Same container as deployment for consistency |

### 9.2 Auth phasing **[LOCKED — production-grade foundation throughout]**

Four phases (0 retired), OIDC-ready throughout so transitions are config swaps, not rewrites. **There is no "throwaway hardcoded admin" stage.** The implementation foundation is production-grade from the start; later phases layer on stronger controls without rebuilding the foundation.

| Phase | Mechanism | Trigger to advance |
|---|---|---|
| **A — Offsite foundation (current)** | Django built-in auth, per-advisor local accounts, **authenticated-by-default DRF**, advisor team scope, financial-analyst PII denial, kill-switch on engine generation | Phase A is current state |
| **B — Pilot hardening** | Phase A foundation + **MFA (TOTP), password reset via email, session timeout (30 min), account lockout after 5 failed attempts**. Audit browser UI shipped. CMA admin boundary live. | First real advisor pilot users |
| **C — Internal scale** | Microsoft Entra SSO via OIDC | Broader Purpose advisor rollout beyond pilot |
| **D — Broader platform** | Auth0-backed user pool (OIDC) | DIY investors, third-party advisors, Advisor Center |

**The Phase A → B transition is the critical pre-pilot gate.** Phase A is production-grade for internal team use (no shared accounts, no plaintext credentials, audit immutability via DB triggers, RBAC scoping enforced). Phase B layers on the controls that move it from "internal team" to "advisor pilot" — MFA, lockout, password reset, session policy, audit browser UI.

**Permission framework (RBAC) is in place from Phase A.** Authenticated-by-default DRF, advisor team scope (single shared scope for clients and review workspaces), and financial-analyst PII denial are built in. The structure is in place; Phase B tightens rules and adds roles.

**Roles for v1 RBAC:**

- **IS / Advisor** — sees clients in shared advisor team scope; cannot view financial-analyst surfaces with PII; cannot edit CMAs or view the efficient frontier; can override engine inputs (pre-recommendation) or annotate non-execution (post-recommendation) per Part 7.5
- **IS Manager** — sees team's books plus override on assignments (Phase B)
- **CMA Admin (Macro Insight Layer)** — restricted role for the CIO/strategist function; edits CMAs and views the efficient frontier per Part 4.7. Initially: 1–2 named individuals. All edits write to the audit log. (Phase B)
- **Financial Analyst** — denied access to real-client PII surfaces; sees synthetic personas and aggregate metrics only
- **Compliance** — read-only across all clients within Steadyhand; audit log visibility (Phase B)
- **Engineering / Admin** — break-glass access, heavily logged

User model is minimal and OIDC-ready: email-as-identity, no auth-method-specific fields. SSO transitions don't touch the user model.

### 9.3 Data classification defaults **[LOCKED — tightened for real PII]**

> **MP2.0 processes real Canadian client PII from day one.** This is not a sandbox build with synthetic data; the extraction pipeline ingests real Steadyhand client documents (meeting notes, plans, statements). The full PII handling regime in Part 11.8 governs operational use; this section governs platform defaults.

Purpose has no published data classification policy yet. The build proceeds with conservative defaults that assume the highest sensitivity tier (client PII) and treats them as floors, not ceilings:

- **Encryption at rest:** RDS with customer-managed KMS key; S3 SSE-KMS; EBS encrypted. Local dev DBs encrypted at the disk level (FileVault / LUKS) — non-negotiable on any machine touching real data.
- **TLS 1.2+ in transit everywhere:** ALB to client, app to RDS, app to external APIs. No HTTP fallback paths.
- **Resource tagging:** every resource tagged `mp20-data-sensitivity={pii|internal|public}`. When IT publishes formal classification, inventory is ready.
- **Logging discipline:** PII never logged. Custom logger wraps stdlib with auto-redaction for SIN, SIN-shaped strings, account numbers, email addresses, phone numbers, full names against a known-name dictionary. Auto-redaction is *enforced and tested*, not aspirational — every log writer has a unit test asserting that PII inputs do not appear in output. Painful to retrofit because old logs persist.
- **LLM provider boundary:** real PII does not transit to a US-based LLM endpoint without explicit authorization. See Part 11.8 for the dev/prod LLM provider posture under real-PII conditions.
- **Architecture doc note:** "Data classification policy TBD with Purpose IT — current defaults assume client PII tier and apply as floors; revisit when Purpose IT publishes formal classification."

### 9.4 Architecture principles — the non-negotiables

These are the constraints that make the codebase extensible. Violations here are the bugs that compound.

#### 9.4.1 Modular monolith **[LOCKED]**

Single deployment, single repo, structured into modules with explicit boundaries. Microservices are premature for MVP scale and would burn ops capacity the team doesn't have. The discipline is module boundaries, not deployment boundaries.

#### 9.4.2 The engine boundary **[LOCKED — most important rule]**

> **The engine is a library, not a service. Web layer imports the engine; engine never imports the web layer.**

- Engine takes plain Python objects (Pydantic models) and returns plain Python objects
- Engine never touches Django ORM
- Web layer translates DB models ↔ engine inputs at the boundary
- Engine has its own test suite that runs without Django

This single rule is what makes the engine extractable into a Lambda, a Snowflake stored proc, or a packaged distribution later. It also lets Fraser/Nafal develop the engine in isolation. **Violating this rule once costs a week to unwind later.**

#### 9.4.3 Adapter pattern for integrations **[LOCKED]**

Every external system gets an interface defined now, with a mock implementation that returns realistic fake data. The button in the UI says "Pull from Croesus" — under the hood it calls `croesus_client.get_holdings(client_id)` which returns hardcoded JSON today and real API responses later. UI and engine never change.

Discipline: mock data lives in `integrations/<system>/mocks/`. Never leaks into engine code. This is the avoidance pattern for **the Trucon problem** — the single rigid integration whose failure cascades platform-wide.

**Named external integrations for v1 — adapters to define now, mock for MVP, integrate later:**

| System | Purpose | Status | Notes |
|---|---|---|---|
| **Croesus** | CRM source of meeting notes, KYC, household records | File-drop in MVP; API future | The system of record for client interactions. Manual file drop today; API integration is post-MVP. |
| **CAT** | Trade execution and account-value source | **Named Day 3 morning; mock for MVP** | Real-time account values trump document-derived numbers (Day 3 §1: "facts trump notes"). When CAT says $32K and a meeting note says $30K, that's not a conflict — it's hierarchy. |
| **Resource** | CRM system (Steadyhand) | **Named Day 3 morning; mock for MVP** | Provides factual household / account / contact data. Reconciliation layer prefers Resource facts over note-derived facts. |
| **Custodian APIs** | Order placement, holdings sync | Out of MVP scope | Stage 4 (automated execution) is Phase 2+. |
| **Conquest / Adviice / Planworth** | Planning tool exports | File-drop in MVP; API future | The system must accept inputs from any planning tool — adapters per source, mocked today. |
| **Bedrock / Anthropic** | LLM extraction and styling | Real (Bedrock for real-PII; Anthropic synthetic-only) | Behind LLM client wrapper (Part 9.5). |
| **PDF rendering** | Client-output PDFs | Deferred to week 2+ | WeasyPrint or similar (open question). |

**The reconciliation hierarchy (Day 3 morning):** when document-derived facts conflict with system-of-record facts, **system-of-record wins**. The reconciliation layer (Part 11.4) treats this as priority resolution, not as a "needs review" conflict. Account values from CAT trump statement-extracted values; CRM-resident contact info trumps notes.

#### 9.4.4 Three-layer data pipeline **[LOCKED]**

For every data ingress (Croesus extracts now, APIs later), three stages with stored intermediate state:

1. **Raw layer** — original artifact untouched, sha256 + source metadata recorded
2. **Parsed layer** — Claude's structured extraction with prompt + model version stamp
3. **Engine input layer** — validated, typed Pydantic models the engine consumes; deterministic mapping from parsed; advisor overrides logged

The reason for separation: Claude is great at extraction but non-deterministic; the engine needs deterministic inputs. This pattern lets us re-run extraction when prompts improve, override Claude errors without re-running, and produce a clean audit trail of how raw documents became engine inputs.

(See Part 11 for the full five-layer extraction pipeline that lives within these three.)

#### 9.4.5 Determinism / AI-creativity balance **[LOCKED]**

- **Workflows are deterministic.** Don't dynamically generate intake forms. Don't let the LLM "decide" what to ask. Required attribute set is always captured.
- **Inputs are where AI shines.** Extracting structure from unstructured notes; routing between deterministic steps; rephrasing for the client.
- **Output never includes numbers that didn't come from the engine.** AI styles the deterministic output; AI does not produce financial figures.

#### 9.4.6 Audit log from day one **[LOCKED — second most important rule]**

> **Audit log is separate from observability logs. Different system, different retention, different consumers.**

Captures every meaningful action:
- Document ingested (who, when, what, sha256)
- Field extracted (run ID, prompt version, model version, source quote)
- Field overridden by advisor (before/after, who, when, edit hash)
- Engine run (inputs, fund assumptions used, method + params, output, model version)
- Recommendation approved by client (when, by whom, via what channel)
- Section approval and review-state commit (workspace ID, sections, advisor)
- Kill-switch toggles (operator, before/after state, reason)
- Disposal of real-PII artifacts (file ID, sha256, deletion timestamp, machine, operator)

**Schema is append-only Postgres with row-level immutability** via Django model guards plus backend-specific DB triggers (the protection survives an ORM bypass). The workspace timeline serializer redacts sensitive before/after values for UI consumers; the audit row preserves the full record for compliance review.

**UI for browsing the audit log is a Phase B exit criterion**, not post-MVP — the writes happen now and the browser ships before pilot launch.

### 9.5 LLM client abstraction **[LOCKED]**

Single thin module wraps the LLM provider. App code never imports the Anthropic or Bedrock SDK directly — only the wrapper. Swap is a config change.

```python
# integrations/llm/client.py
def extract(prompt: str, schema: type[BaseModel]) -> BaseModel:
    """Returns validated Pydantic instance. Provider selected from env."""
```

Provider, model, prompt version, and call duration logged with every invocation into the audit log.

### 9.6 Infrastructure (local → staging → production)

#### 9.6.1 Local dev

Docker Compose: Django + Postgres + Vite dev server. Postgres (not SQLite) from the start for consistent query semantics, since extraction stores JSONB and uses pgvector.

#### 9.6.2 Staging (week 1) **[LOCKED]**

EC2 single instance with Caddy reverse proxy + Docker Compose, or Render.com free tier (synthetic-only, see Part 11.8.5). Public URL with HTTPS. Used for the Wednesday Som demo and Phase B/C pilot use. **Demoable from any browser within first week — laptop demos fail at offsite venues (wifi, sleep, battery, stale fixtures).**

#### 9.6.3 Production (post-MVP)

- VPC ca-central-1, private subnets for app + RDS, public subnets for ALB
- ALB with WAF, terminating TLS, routing to ECS service on existing EC2 cluster
- Two tasks for HA; gunicorn + nginx sidecar (match Purpose pattern)
- RDS Postgres encrypted, automated backups, pgvector enabled
- S3 with SSE-KMS, versioning, lifecycle policies
- Secrets Manager for keys
- Bedrock for Claude calls (swap from direct API)
- OpenTelemetry → Elastic APM
- Audit log table in Postgres with row-level immutability trigger
- GitHub Actions → ECR → ECS deploys

#### 9.6.4 Async work (when needed)

Celery worker as separate ECS service backed by SQS. For long optimization runs, scheduled drift checks, batch nudge generation. Engine functions designed to be callable both sync (request) and async (worker) by remaining pure.

### 9.7 Items confirmed out of scope for MVP

- Microservices (premature; modular monolith)
- Custodian / brokerage API integrations (Stage 4)
- Conquest / Adviice / Planworth API integrations
- Croesus *API* integration (manual file drop instead — see Part 11)
- Production access control infra beyond Phase 1 auth
- Real-time market data
- Mobile native apps
- DIY direct-to-investor flow
- Multi-tenant infrastructure
- Full tax optimization
- ChatGPT/Claude app-store distribution

---

## PART 10 — REPO LAYOUT

```
mp20/
├── pyproject.toml                    # Workspace root; defines package boundaries
├── docker-compose.yml                # Local dev: Django + Postgres + Frontend
├── Dockerfile                        # Multi-stage build for production image
├── .github/workflows/                # CI/CD
│
├── engine/                           # Pure Python, no Django imports. Pip-installable.
│   ├── pyproject.toml
│   ├── schemas.py                    # Pydantic: Household, Person, Goal, Account, etc.
│   ├── sleeves.py                    # Fund universe constant (file kept under legacy name; conceptually the building-block fund universe per Part 5 — the codebase identifier intentionally lags the product vocabulary to avoid churn)
│   ├── frontier.py                   # Efficient frontier computation
│   ├── optimizer.py                  # optimize() entrypoint
│   ├── compliance.py                 # risk_rating(blend) → low|med|high
│   └── tests/                        # Persona-driven regression tests
│
├── extraction/                       # AI-powered ingestion pipeline (Part 11)
│   ├── layer1_ingestion.py           # File watcher / upload handler
│   ├── layer2_text.py                # Format dispatch (PDF/DOCX/CSV/XML/MD)
│   ├── layer3_facts.py               # Claude extraction with Fact[T] schemas
│   ├── layer4_reconcile.py           # Group facts → current state + history
│   ├── layer5_review.py              # Backend for advisor review UI
│   └── prompts/
│       ├── meeting_note.py
│       ├── kyc.py
│       ├── statement.py
│       └── classify.py               # Document classifier (fallback)
│
├── integrations/                     # Adapter pattern for all external systems
│   ├── llm/
│   │   ├── client.py                 # Provider-agnostic wrapper
│   │   ├── anthropic_provider.py
│   │   └── bedrock_provider.py
│   ├── croesus/                      # Stub today; real API later
│   ├── conquest/                     # Stub
│   ├── custodian/                    # Stub; Phase 2+
│   └── pdf_render/                   # WeasyPrint or similar
│
├── personas/                         # Test fixtures (real-redacted + synthetic)
│   ├── sandra_mike_chen/             # Demo persona
│   │   ├── raw/                      # Original Croesus exports (gitignored if real)
│   │   ├── extracted/                # Layer 3 output
│   │   └── client_state.yaml         # Approved Layer 5 output
│   ├── young_professional/
│   ├── mid_career_family/
│   ├── recently_retired/
│   └── post_windfall/
│
├── web/                              # Django + DRF
│   ├── settings/                     # base, dev, prod
│   ├── api/
│   ├── auth/                         # Auth phase 1, OIDC-ready
│   ├── audit/                        # Audit log model + writers
│   ├── permissions/                  # RBAC framework
│   ├── models.py                     # Django ORM (DB persistence only)
│   └── management/commands/load_personas.py
│
└── frontend/                         # React + Vite + Tailwind + shadcn/ui
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── routes/                   # React Router
        ├── components/               # shadcn/ui + custom
        ├── lib/api.ts                # TanStack Query hooks
        └── features/
            ├── intake/
            ├── review/               # Layer 5 review UI
            ├── plan/
            ├── portfolio/
            └── outcomes/
```

---

## PART 11 — EXTRACTION LAYER (FIVE-LAYER PIPELINE)

The extraction layer is **production-grade software handling real client PII** as of 2026-04-29. Source data: real Croesus exports manually copied by Lori (and pilot advisors during Phase C) into `MP20_SECURE_DATA_ROOT` outside the repo, ingested via authenticated browser upload — no API integration in MVP.

> **Real client PII flows through this system from day one.** Section 11.8 documents the privacy regime that protects it. The regime is *defense-in-depth* (authenticated ingress, Bedrock ca-central-1 fail-closed routing, transient raw text, structured-only persistence with redacted evidence, hashed sensitive identifiers, immutable audit, RBAC scoping, bounded pilot population) — not pre-LLM pseudonymization, which was earlier specified but not implemented. Section 11.8.3 explains the substitution honestly. Lori + Amitha must confirm the authorization basis in writing if not already done.

> **Operational dependency:** during Phase A the file-drop pipeline depends on Lori as a person. Identify a backup who can copy files in her absence; have at least one fully synthetic persona that works without any real-data dependency, so the Wednesday Som demo is viable even if real data isn't available. During Phase C, pilot advisors copy files for their own clients; Lori's role shifts to triage and quality oversight.

### 11.1 Layer 1 — Raw ingestion (immutable)

Files dropped into a per-persona folder. Stored as-is, sha256 recorded, never modified.

Format heterogeneity expected: PDF (native + scanned), DOCX, CSV, XML, plain text. Documents that may or may not be present per client: planning output, account statements, transaction history. **Meeting notes are the always-present, most consequential source.**

No manifest required from Lori. Filename convention preferred (`{date}_{doctype}_{description}.{ext}`); when absent, document classification handled by Layer 3 fallback.

### 11.2 Layer 2 — Text extraction (deterministic)

Format dispatch returns a uniform shape regardless of source:

```python
class ExtractedText:
    raw_text: str
    structured_fragments: list[Table | KeyValueBlock]
    page_or_section_markers: list[Marker]
    source_file_id: str
    extraction_method: Literal["pdf_native", "pdf_ocr", "docx", "csv", "xml", "plain"]
```

Tooling: `pdfplumber` (native PDF), Tesseract or Claude vision (scanned PDF), `python-docx` (Word), `pandas` (CSV), `lxml` (XML). Layer 3 sees only `ExtractedText`, never the original file. New formats are one more dispatch arm; nothing downstream changes.

For structured formats (CSV, XML, well-formed tables), parse deterministically into structured records. **Do not use Claude on tabular data** — paying tokens for a regex.

### 11.3 Layer 3 — Structured fact extraction (Claude)

This is the consequential layer. Two principles dominate:

**One Claude call per document, not per field.** Document gets parsed once into all the fields it contains. Lower cost, full context, fewer race conditions in reconciliation.

**Per-document-type Pydantic schema as structured output.** Different schemas for `MeetingNoteExtraction`, `KYCExtraction`, `StatementExtraction`. No universal schema.

#### 11.3.1 Temporal extraction (the "accumulated history" pattern)

Steadyhand meeting notes contain years of accumulated client history compounded into single documents. A note may say:

> *"Originally targeting retirement at 65 with $2M nest egg. After 2022 market drop, pushed to 67 and revised target to $1.6M. Recent conversation (Aug 2024): now thinking 66 if Sandra's part-time consulting works out — wants to revisit in spring."*

Asking Claude for "the retirement age" returns one of three numbers and you don't know which. The unit of extraction is therefore a `Fact`, not a current value:

```python
class Fact[T]:
    field: str                     # canonical name, e.g., "retirement_age"
    value: T
    asserted_at: date | None       # when this became true; null if unknowable
    superseded_by: str | None      # ID of fact that replaces this one
    confidence: Literal["high", "medium", "low"]
    derivation_method: Literal["extracted", "inferred", "defaulted"]
    source_quote: str              # exact sentence Claude grounded in (empty if inferred)
    source_doc_id: str
    source_location: str           # page or section
    extraction_run_id: str         # prompt version + model version
```

Claude's instruction: *"Extract every assertion of every field as a Fact, with inferred date and source quote. Multiple facts of the same field are expected and desired."*

The `derivation_method` field lets the review UI distinguish between facts grounded in a specific quote vs. facts the model inferred from context vs. system defaults.

#### 11.3.2 Two-prompt structure per meeting note

1. **Fact extraction** — temporal Facts as above.
2. **Behavioral synthesis** — communication style, reaction patterns, sensitive topics, follow-through. Inherently summative; Claude's read across the note. Lower stakes for "wrongness" because these inform tone, not engine inputs.

#### 11.3.3 Provenance is non-negotiable

Every field carries its source quote (or, for inferred facts, an explicit marker that no quote exists). The advisor review UI (Layer 5) cannot exist without it. The audit story for "why did the engine recommend this" cannot exist without it. No exceptions.

### 11.4 Layer 4 — Field reconciliation

Per canonical field, sort Facts by `asserted_at` desc, then resolve:

- Most recent + highest confidence becomes the "current value"
- All prior facts retained as history
- Conflicts where recent values disagree with older ones are signal, not noise — surfaced in the review UI

**Source-priority hierarchy (Day 3 morning) — facts trump notes.** When facts come from different source classes, source class beats recency:

1. **System-of-record facts** (CAT account values, Resource CRM data) — highest priority. Real-time, authoritative.
2. **Structured documents** (KYC, statements) — medium priority. Authoritative for the moment they were generated.
3. **Note-derived facts** (meeting notes, advisor observations) — lowest priority. Subjective and time-varying.

When a CAT account value reads $32,400 and a four-week-old meeting note says $30,000, **the system silently uses $32,400** and does *not* surface this as a conflict. The note-derived value is logged in fact history but is not a competing claim — it's a stale snapshot. Reconciliation conflicts surface only when same-class sources disagree (e.g., two meeting notes giving different retirement ages, or two statements giving different account types).

Naive most-recent-wins within a source class is sufficient for v1. Sophisticated reconciliation (confidence-weighted, conflict-resolution heuristics across classes) is post-MVP.

### 11.5 Layer 5 — Advisor review, section approval, and the `engine_ready` gate

The most important screen in the system. Side-by-side:

- **Left:** source documents, clickable
- **Right:** consolidated client state, organized into review sections (Household, People, Accounts, Goals, Goal-Account Mapping, Risk)
- Each field shows source quote + originating document; click jumps to source
- Each field shows derivation method (extracted / inferred / defaulted) — extracted facts get visual priority; inferred facts get a "please confirm" marker
- Conflicts shown inline ("retirement_age: 67 (Aug 2024 note) — older value 65 in Mar 2023 note")
- All fields editable; edits logged with user + timestamp + edit hash into audit log
- Approval is **per-section**, not whole-state — each section moves through `pending → approved` once its required fields are populated and resolved

**Explicit advisor confirmation is a compliance requirement [Day 3 afternoon §4.2]:** even when AI extraction succeeds cleanly, advisors **always want to review** before commit, and **must explicitly confirm/agree** that the data is correct. The section-approval action is that confirmation; it is logged with operator + timestamp into the audit trail. Skipping the confirmation step is not an option, even when zero conflicts exist.

**Three mockup states needed for the data-review screen [Day 3 afternoon §4.2]:**

1. **Clean data** — extraction succeeded, no conflicts, no missing required fields. The screen reads as a "review and approve" pass-through; sections approve quickly.
2. **Moderate conflicts** — a handful of fields have conflicts (DOB discrepancy, duplicate account entries, fat-finger errors in source documents). The advisor resolves each, captures override reasons, and approves.
3. **Heavy conflicts** — extraction returned low-confidence results across many fields, multiple unresolved conflicts, missing critical inputs. The screen needs to remain navigable and not feel hopeless; the advisor works through systematically and the system tracks progress.

All three are owed before pilot launch. **Owner: Nafal** (Day 3 afternoon §10 task list — build data review / conflict resolution screen).

#### 11.5.1 The `engine_ready` gate **[LOCKED]**

The reviewed client state has a derived `engine_ready` flag that is **true only when**:

- All required fields are populated (no missing values in fields that block engine input)
- All flagged conflicts are resolved (no field has competing values that the advisor hasn't picked between)
- All required "unknowns" are addressed (no goal without a horizon, no account without a value, no goal-account mapping for a goal that has dollars allocated)

`engine_ready` does *not* require all sections to be approved — an advisor can run the engine to preview output before final approval. But a **commit** of reviewed state into the canonical client tables (the act that creates a real `Household` record the engine queries against) requires both:

1. `engine_ready == true`, **and**
2. All required review sections in `approved` status

This two-gate pattern (ready-to-run vs. ready-to-commit) means advisors can iterate on engine output during review without prematurely creating client records.

**Trust is earned or lost here.** Fields without provenance get re-done by the advisor — defeating the system's purpose. The `engine_ready` gate exists to make sure the system never quietly produces output on incomplete inputs.

### 11.6 Document classification

Filename convention preferred: `{date}_{doctype}_{description}.{ext}`. When absent or non-conforming, Claude classifier reads the first page and tags `meeting_note | kyc | statement | plan | other`. One extra Claude call per file. Both paths logged.

### 11.7 Privacy posture for raw files **[LOCKED]**

Original Croesus exports contain real client PII. The repository is structured on the assumption that **real PII never enters version control and never leaves authorized environments.**

- Real PII enters only through the authenticated browser upload to `MP20_SECURE_DATA_ROOT` outside the repository (Part 11.8.3). Repo-local upload paths are explicitly rejected.
- The `.gitignore` at the repo root excludes `**/raw/**` patterns and the secure data root path; CI fails if files matching common PII signatures appear in a commit.
- A scrub-pass utility flags potential PII (emails, SIN patterns, account numbers, phone numbers, full names) before any file enters a committed location. Files that fail the scrub pass cannot be committed.
- Synthetic personas may have raw files committed (the Sandra & Mike Chen demo persona is one of these); real-derived personas may not.
- A pre-commit hook on every team machine runs the scrub-pass utility automatically. The hook is part of the repo bootstrap (`make setup`), not an optional install.

### 11.8 Real client PII handling **[LOCKED — hard prerequisite]**

This section governs the operational use of real Steadyhand client PII in the MP2.0 build. **Lori + Amitha (Purpose legal) must review and approve this section before any real client file is copied onto a team machine.** Operating outside this section is a compliance failure, not a process slip.

#### 11.8.1 Authorization basis **[LOCKED for limited-beta scope — 2026-04-30]**

As of 2026-04-30, real Steadyhand client PII is **authorized for limited-beta, local-production-like operation** under the §11.8.3 defense-in-depth regime. Current authorized scope:

- Two roles in the running system: `advisor` and `financial_analyst` (Django groups defined in `web/api/access.py`)
- Current local-production-like deployment (the running secure-local pipeline, not a broader staged or production deployment)
- Limited-beta user population

**Broader rollout** beyond this scope (more advisors, broader user population, staging/production deployment, sharing of real-derived outputs outside the team) requires Lori + Amitha review. Working revisit date: 2026-05-21.

For audit and operational hygiene, the team still maintains:

1. **A documented authorization record** in a known location (project shared drive) with version, date, and signatories. Referenced by ID in the audit log when broader-rollout sign-offs land.
2. **A documented scope** — which clients, which document types, for what purpose, for how long. Narrow is better than broad; the limited-beta scope above is the current operating envelope.

The defense-in-depth regime in §11.8.3 is what makes limited-beta operation defensible. Pre-LLM pseudonymization remains retired; if Amitha later requires it for broader rollout, that is a Phase B re-engineering project, not a runtime toggle.

#### 11.8.2 Data minimization

Use the smallest amount of real PII that proves the use case. Operating principle:

- **During offsite build (Phase A):** 1–2 real-derived personas (from Lori's tier-2 client base) exercise the extraction pipeline against real document shape, accumulated-history meeting notes, and the complexity that synthetic personas can't realistically simulate. The Wednesday Som demo defaults to the synthetic Sandra & Mike Chen persona; real-derived personas appear at that demo only with audience composition confirmed in advance.
- **During IS validation (Phase B):** each IS works through their own real tier-2 clients — bounded by their own book and the team-scope RBAC.
- **During advisor pilot (Phase C):** each pilot advisor loads files for their own client subset (not their full book). Pilot scope: **3–5 advisors, ~5–10 clients per advisor, total ~15–50 real-derived personas**. Pilot scope is bounded, documented, and reviewed at Week 2 of pilot use. The bound exists to limit blast radius if anything goes wrong, not to limit the system's usefulness.
- For each real-derived persona, advisors copy only the document types needed: meeting notes file, most recent KYC, recent statement. Not the full client file.
- The privacy regime in 11.8.3 applies to all real-derived personas regardless of phase. Volume scales; controls don't change.

#### 11.8.3 Privacy regime — defense-in-depth, not boundary pseudonymization **[LOCKED — supersedes earlier v2.3 boundary-pseudonymization design]**

> **Important honesty note.** Earlier versions of this canon (v2.1–v2.3) specified pseudonymization at the Layer 2 → Layer 3 boundary so that Bedrock would only ever see pseudonymized text. **That regime was not implemented.** Real client names and content currently transit to Bedrock. The implementation chose a different, defensible regime — defense-in-depth around real text — and the canon now reflects what is built. The substitution is acknowledged here so that no one operating from this canon believes a boundary-pseudonymization protection exists when it does not.

The privacy regime that **is** in place:

1. **Authenticated-only ingress.** Real PII enters only through the authenticated browser upload workflow with `MP20_SECURE_DATA_ROOT` set outside the repository. Hard-fail if the secure root is missing or repo-local. Hard-fail if Postgres is not the persistence layer.
2. **Bedrock ca-central-1 fail-closed routing.** Real-derived extraction requires Bedrock environment configuration; missing Bedrock config is a fail-closed worker error. Real client text does transit to Bedrock — but only Bedrock in ca-central-1, under Purpose's AWS account, never to a US-resident endpoint, and never to Anthropic API direct. The LLM client wrapper routes by persona origin: `synthetic → Anthropic direct` or `Bedrock` per available config; `real_derived → Bedrock ca-central-1 only`. Misconfiguration is a deployment-blocker check.
3. **Transient raw text.** The full raw extracted text from documents is held only long enough to extract structured facts; it is not persisted as a queryable column. The system of record after extraction is the structured fact table, not the raw text.
4. **Structured-only persistence with minimally-redacted evidence.** Only structured facts, provenance/run metadata, and **minimally-redacted evidence quotes** are persisted. An evidence quote retains enough source phrasing to support advisor review and audit but redacts the most directly-identifying tokens.
5. **Sensitive identifiers stored as hash + redacted display.** SIN, account numbers, and similar high-sensitivity identifiers are stored as a hash plus a redacted display string. The plaintext value does not enter the persisted database.
6. **Workspace timeline sanitization.** The audit-visible workspace timeline serializer redacts sensitive before/after values from edit events; the audit row itself preserves the immutable record, but UI consumers see a sanitized projection.
7. **Outside-repo storage with hard-fail validation.** `MP20_SECURE_DATA_ROOT` validation enforces that the directory exists, is outside the repo, and is reachable; failure mode is hard-fail at upload, not graceful degradation.
8. **Bounded blast radius.** Pilot scope (3–5 advisors, ~5–10 clients per advisor, total ~15–50 real-derived personas) bounds exposure; a single team-scope grants advisors visibility to one another's review work but blocks financial-analyst access entirely.

**What this regime protects against:**

- PII committed to git (authenticated upload to outside-repo location; gitignore at repo root; hard-fail validation)
- PII reaching a US-resident LLM endpoint (Bedrock ca-central-1 fail-closed routing)
- PII persisted indefinitely in queryable form (transient raw text; structured-only persistence; redacted evidence)
- High-sensitivity identifier exposure in DB or logs (hash + redacted display)
- Audit log tampering (model guards plus DB triggers; append-only)
- Unauthenticated read of any client surface (authenticated-by-default DRF; advisor team scope; financial-analyst denial)

**What this regime does *not* protect against, and the team accepts:**

- *Real names visible in Bedrock prompt logs (within Purpose AWS, ca-central-1).* Bedrock sees real text. The protection is the trust boundary (Purpose AWS, Canadian-resident, Bedrock service-level controls) rather than pre-LLM redaction. This is a deliberate trade-off: pre-LLM pseudonymization would have degraded extraction quality (quasi-identifiers leak; pseudonyms confuse the model on temporal references), and Bedrock under Purpose's AWS posture is judged a sufficient trust boundary by the team. **This judgment must be reviewed with Amitha (Purpose legal) before pilot expansion** (open question #24).
- *Real names in advisor screen displays during demos and pilot use.* The Layer 5 review UI shows real client identity to the authorized advisor. RBAC enforces same-advisor visibility; financial analysts are denied. The Som demo posture is to use the synthetic backup persona; if a real-derived persona is shown, the audience composition is confirmed in advance (open question #29).
- *Quasi-identifier leakage in extracted facts.* Employer, neighborhood, family situation, health detail are stored in structured facts and visible in the review UI. The structured shape limits casual exposure; access control limits authorized exposure. Active stripping is not implemented.

**The team's standing position to defend this regime under audit:** *"Real Canadian client PII is processed only within Purpose's AWS account in ca-central-1, via Bedrock with fail-closed routing, with structured-only persistence, hashed sensitive identifiers, redacted evidence quotes, immutable audit, authenticated-and-RBAC-scoped access, and bounded pilot population. Pre-LLM pseudonymization was considered and not adopted because the residual quasi-identifier leakage made it security theater rather than meaningful protection; the Bedrock-under-Purpose-AWS trust boundary is the protection."*

If Amitha or Purpose IT subsequently determines pre-LLM pseudonymization is required, that's a Phase B re-engineering item, not a runtime adjustment.

#### 11.8.4 LLM provider posture under real PII **[LOCKED]**

- **Real-derived extraction: Bedrock in ca-central-1, fail-closed.** Missing Bedrock configuration is a worker error, not a fallback to Anthropic direct. Anthropic API direct is **not** a permitted destination for real client content.
- **Synthetic-persona work: Anthropic API direct or Bedrock, by available config.** The synthetic Sandra & Mike Chen persona has no real-PII routing dependencies and can use either provider.
- **The LLM client wrapper routes by `data_origin` flag.** `synthetic → Anthropic direct or Bedrock`; `real_derived → Bedrock ca-central-1 only`. Misconfiguration (real persona routed to direct API) is a deployment-blocker check.
- **Bedrock fact extraction is JSON-validated with controlled repair.** Bedrock output is parsed against typed Pydantic schemas; controlled JSON repair attempts a small set of canonical fixes before failure; failures persist as failed-document state for retry. The repair logic is bounded and auditable; it does not silently rewrite output to make extraction "succeed."

#### 11.8.5 Storage and machine posture **[LOCKED]**

Machines and infrastructure that touch real PII must:

- Validate `MP20_SECURE_DATA_ROOT` exists, is outside the repo, and is writable; hard-fail otherwise. Synthetic upload paths may use SQLite for tests; real-upload paths require Postgres.
- Encrypt at rest (RDS with customer-managed KMS key in production; full-disk encryption on local machines).
- Prevent project-directory sync to personal cloud storage (Dropbox, iCloud, personal Drive, OneDrive); the working directory is excluded from personal sync clients.
- Run the pre-commit scrub-pass hook (Part 11.7) without exception. CI PII scanners are deferred but tracked (open question).
- Use Purpose AWS ca-central-1 for any deployment touching real PII. **Render.com free tier and other US-resident hosts are not acceptable** even for staging. If a staging URL is needed before AWS staging is ready, it serves only synthetic personas.

#### 11.8.6 Retention and disposal **[LOCKED — local tooling exists]**

- Raw files in `MP20_SECURE_DATA_ROOT` and structured facts have a defined lifespan tied to MP2.0 active development against that data.
- Local artifact disposal is supported via `uv run python web/manage.py dispose_review_artifacts`, which also produces a disposal report.
- Disposal is logged in the audit log: file ID, sha256, deletion timestamp, machine, operator. The audit trail outlives the file.
- The team-level retention/disposal policy trigger (when does disposal run, by whom, on what cadence) is open and pending Lori + Amitha confirmation (open question #28).
- **Lori is responsible for ensuring the original Steadyhand-side records are unaffected.** MP2.0 disposes of its working copies; the system of record remains in Croesus.

#### 11.8.7 Demo audiences and pilot use

The Wednesday Som demo, the Mon/Tue IS validation sessions, and the ongoing advisor pilot all involve people seeing the running system, with different stakes:

- **Wednesday Som demo** — primary persona is the synthetic Sandra & Mike Chen. Real-derived personas are **not** shown in this demo unless the audience composition is confirmed and the persona's own client (or that client's advisor) is comfortable. Defaults to synthetic-only.
- **Mon/Tue IS validation sessions** — each IS runs the system on their own real tier-2 clients. Each IS sees only their own clients, RBAC-enforced via advisor team scope. Other IS's clients are not visible.
- **Pilot use (Phase C onward)** — each advisor sees their own real-derived personas. The Layer 5 review UI shows real client identity to the authorized advisor. RBAC enforces same-team-scope visibility; financial analysts are denied.
- Screen recordings, screenshots, and slides made during the offsite or pilot retrospectives use synthetic personas. Pre-rolled media reviewed for incidental PII leakage (window titles, file paths, browser tabs) before circulation.
- If an advisor recognizes another advisor's client from quasi-identifiers (employer, neighborhood, family situation), that's a finding to log and tighten — not a "well, they figured it out" shrug. Quasi-identifier handling is an open question (#27).

#### 11.8.8 Incident response

If real PII is exposed (committed to git, sent to a non-authorized LLM endpoint, leaked in a log, shown at a launch event or in pilot use):

1. Stop the activity. Do not attempt to "fix forward."
2. Notify Lori + Amitha within the hour.
3. Document what was exposed, to whom, when, for how long.
4. Follow Purpose's existing incident-response process (defer to Amitha for the regulatory question of whether OPC notification is required under PIPEDA).
5. Post-incident review with a written remediation that goes into this section as a tightening.

This is a small team on a tight timeline. The way this team avoids incidents is by building the pipeline so most exposure paths are structurally prevented — gitignore patterns, pre-commit hooks, the `data_origin` LLM router, encrypted-at-rest defaults — not by trusting individuals to remember the rules under offsite pressure.

---

## PART 12 — ENGINE I/O CONTRACT

### 12.1 Locked entry point **[LOCKED — refined Day 2]**

```python
def optimize(
    household: Household,
    sleeve_universe: list[Sleeve],     # legacy identifiers per Part 5 / Part 10 — conceptually the building-block fund universe
    method: OptimizationMethod = "percentile",  # Part 4.3
    constraints: Constraints | None = None,
) -> EngineOutput:
    ...
```

`EngineOutput` contains:

- **Per-link blends**: one optimized fund-weight vector per `GoalAccountLink` (Part 4.3a — the optimization unit is the goal × account cross). The `link_id` keys back to the household's `GoalAccountLink` set.
- **Per-account roll-up**: each account's consolidated holdings, weighted across the per-link blends within that account (Part 4.3a step 2).
- **Per-account fund-of-funds collapse suggestion** (Part 4.3b): if the per-account roll-up closely matches an existing whole-portfolio fund (Founders, Builders, PACF, etc.), the engine recommends that fund instead of the building-block-fund list. Includes a "match score" so the UI can show why.
- **Household roll-up**: aggregated weighted blend across all accounts.
- **Resolved risk per link**: `household_component`, `goal_component`, `combined_score`, `combined_percentile` — all surfaced to the UI per Part 4.2.
- **Fan chart data per link**: 10th / 50th / 90th percentile portfolio value over the goal's time horizon. Fan locks at t=0 for longitudinal plotting (Part 8.9).
- **Compliance risk rating** per account + household (low/med/high) per Part 7.4.
- **Audit trace**: fund assumptions used (CMA snapshot ID, asset-class composition, tax-drag table version), frontier coordinates, method + params, prompt + model version where AI was involved, optimization timestamp.

The shape is per-link first, account second, household third. The UI consumes whichever level matches its current view (Part 8.7 three-tab toggle).

### 12.2 Schemas live in engine/

Pydantic models for `Household`, `Person`, `Goal`, `GoalAccountLink` (many-to-many — central to the goal × account optimization unit, Part 4.3a), `Account`, `Holding`, `RiskInput`, `ResolvedRisk` (per-link three-component exposure, Part 6.5), `Sleeve` (legacy identifier; conceptually a building-block fund per Part 5), `CMASnapshot` (per-fund return/vol/correlation/asset-class composition, versioned), `TaxDragTable` (per-fund / per-asset-class drag factors), `Allocation`, `LinkBlend` (per-link optimization output), `AccountRollup`, `EngineOutput`, `EngineRun`. Web layer imports from `engine.schemas`; engine never imports from web.

### 12.3 The Claude artifact handoff process

Engine code arriving from Fraser/Nafal's Claude artifacts gets:

1. Wrapped in the I/O contract (Pydantic in, Pydantic out)
2. Test suite written against the persona fixtures
3. Reviewed for things prototypes skip: input validation, edge cases, numerical stability, empty-input behavior

Artifact code is treated as reference implementation, not production code. Re-implemented inside the engine package's conventions. Few hours per module; saves the class of bug where the prototype worked on three test cases and breaks on the fourth.

### 12.4 Pilot posture: live vs. cached

In actual pilot use, what's interactive vs. what's pre-computed?

- **Interactive (live engine call):** advisor-initiated portfolio computation, what-if sliders, Layer 5 fact review and approval, "regenerate" actions on plain-language explanations.
- **Pre-computed and cached:** initial engine outputs after a fresh persona load (computed once on persona ingestion, cached until a material change), fan charts (computed alongside engine output), baseline goal probabilities. Cache invalidates on plan change, persona reload, or fund-universe update.

Engine + extraction calls are LLM-bound and slow — interactive sub-second response requires caching. For Phase A (Wednesday Som demo), the synthetic backup persona's outputs are pre-baked entirely. For Phase C (pilot use), the cache layer is real and tested. Build the cache abstraction in Phase A so Phase B doesn't need a refactor.

Async work: a Celery worker (Part 9.6.4) handles engine runs that exceed an interactive budget (~5 seconds). The advisor sees a "computing your portfolio…" state, with a clear ETA, rather than a hung browser tab.

---

## PART 13 — MVP SCOPE, BUILD SEQUENCE, PILOT LAUNCH

### 13.0 Three-phase delivery: scaffold → harden → pilot **[LOCKED — production-grade throughout]**

The deliverable is production-grade software for a controlled pilot population (Part 1.6). The actual delivery has three phases, all production-grade for their respective scope:

| Phase | Timing | Output | Bar |
|---|---|---|---|
| **Phase A — Offsite foundation** | Mon–Wed at offsite (3 days), with Thursday extension at offsite location and Friday cleanup at Purpose office available as buffer | Extraction pipeline, engine integration, end-to-end flow, secure-local review tranche, Wednesday end-of-day demo to Som | Production-grade for internal use. Real PII flows through authenticated upload + Bedrock ca-central-1 + structured-only persistence. Three pillars (ingestion, engine, reporting) functional. |
| **Phase B — Pilot hardening + IS validation** | Following Mon–Tue (IS team validation with real client data) plus ~1–2 weeks afterward | MFA / lockout / password reset / session timeout layered onto the existing auth foundation. Compliance risk-rating mapping. CMA admin boundary. Pilot disclaimer. Feedback channel. Kill-switch tested. IS training. | Production-grade for advisor use. 3–5 advisors can log in, work with their own real clients, and produce defensible recommendations. |
| **Phase C — Pilot launch + iteration** | Week 3 onward | 3–5 advisors actively using the system with their real clients. Weekly retros. Structured feedback intake. Defects triaged and fixed in batches. | Production-grade in active operation. Most reasonable advisor actions produce usable output or graceful failure. Output trustworthy enough that an advisor can use it to inform — not replace — their judgment. |

**The Wednesday Som demo is the close of Phase A.** Phase B begins the following week, opening with IS team validation Monday/Tuesday using their own tier-2 client data. **Saranyaraj has an engineering hackathon Mon/Tue that week with partial availability** — Phase B day-1 capacity is reduced and that's a known constraint, not a surprise.

Phase C begins when Phase B exit criteria (Section 13.0.1) are met.

**What is *production-grade* about each phase, and what is added between phases:**

| Concern | Phase A | Phase B addition | Phase C addition |
|---|---|---|---|
| Auth | Authenticated DRF, advisor team scope, financial-analyst PII denial, kill-switch | MFA, lockout, password reset, session timeout, audit browser UI | (steady state) |
| PII handling | Authenticated upload, Bedrock ca-central-1 fail-closed, transient raw text, structured-only persistence, hashed sensitive IDs, redacted evidence quotes | Pseudonymization decision finalized with Amitha; CI PII scanners; encryption posture validation | Routine pilot disposal cadence |
| Engine output | Goal-level placeholder | Per-link blends, account roll-up, fund-of-funds collapse, fan chart, compliance ratings | (refined per pilot feedback) |
| UI | Phase 1 advisor shell + secure-local review workflow | Three-tab household/account/goal view, click-through assignment, current-vs-ideal allocation, fan chart, pilot disclaimer | Three-tier sophistication reporting refinements |
| Audit | Append-only via DB triggers, sanitized timeline, edit hashes | Audit browser UI, full input-to-output trace UI | (steady state) |
| RBAC | Advisor team scope, financial-analyst denial | CMA admin boundary, IS manager role | (steady state) |

#### 13.0.1 Phase B exit criteria — the gate to pilot launch

Pilot use cannot begin until **all** of the following are true:

- Auth Phase 1 in production: per-advisor accounts with **MFA, password reset, session timeout, lockout** layered onto the Phase A authenticated foundation
- Compliance risk-rating mapping function deployed and reviewed (Part 7.4)
- Pilot-mode disclaimer visible in UI on every recommendation: "Pilot output — review before sharing with clients. Not for use as standalone investment advice."
- Audit log writes confirmed on every meaningful action including pre/post-recommendation overrides; **audit browser UI shipped** (Part 9.4.6, Part 7.5)
- Feedback channel operational (Part 13.0.2) with at least one team member triaging
- IS onboarding documentation written, reviewed by Lori, walked through with at least one pilot advisor
- Kill-switch tested end-to-end: a single config change disables engine output platform-wide
- **Admin-only CMA + efficient frontier view shipped and properly access-restricted** (Part 4.7)
- IS team Mon/Tue demo session completed with structured findings logged and triaged
- One full pilot-quality run on a real tier-2 client persona reviewed end-to-end by Lori, with no blocking findings
- **Authorization basis from Lori + Amitha confirmed in writing** (Part 11.8.1) — including retrospective coverage of Phase A real-PII use
- Engine output contract migrated from goal-level to per-link (Part 12.1)
- **Correlation matrix integrated** into the optimization engine (Part 5.4 + Part 4.7.1). Without correlations the math cannot be meaningfully validated.
- **Math validation completed** — Raj's backend optimizer pressure-tested against Fraser's reference model; equivalent efficient frontiers confirmed for matched inputs (Part 4.7.4).
- **Frontend-backend integration completed** — Nafal's frontend wired to Raj's backend per Part 13.4 integration direction.

**No advisor logs in until all of these are checked.** The list is the gate; no individual item is optional in the interest of moving faster.

#### 13.0.2 Pilot operations

Once advisors begin using the system, several support structures must exist:

- **Feedback channel** — a structured intake (Slack channel, dedicated email, or in-app "report this" button feeding a ticket queue) where advisors flag bugs, surface bad output, ask questions. Slack DMs to Lori don't count; signals get lost. One person on the team owns triage.
- **Office hours** — a standing 30-minute weekly session (or async equivalent) where advisors can ask the team about the tool. Low-cost, high-trust.
- **Weekly pilot retro** — Lori + at least one engineer + at least one advisor representative. What worked, what didn't, what changed in the system this week. Notes captured; action items tracked.
- **Bad-output escalation** — when an advisor flags output that looks wrong (a recommendation that doesn't fit the client, a narrative that gets the goal wrong), the team treats it as a Sev-2 by default until proven trivial. The audit log makes it possible to reconstruct: extraction inputs → engine state → output. Document the root cause; tighten the system; close the loop with the advisor.
- **Disclaimer in UI** — every recommendation screen carries pilot-mode language. Advisors see it, clients (if shown anything) see it. Removing the disclaimer is a Phase D concern, after pilot exit.
- **Training material** — written guide for IS users covering: what the tool does, what it doesn't do, how to interpret output, how to flag issues, what's still pilot-quality. Two pages, not a binder. Lori writes the first draft; team reviews.
- **Kill-switch and rollback** — a single config flag (`pilot_engine_enabled=False`) returns engine output endpoints to a maintenance message instantly. Tested before pilot start. Used without ceremony if needed.

#### 13.0.3 Pilot success metric

Success of the pilot is **not** "advisors said they liked the demo." It is **advisors continue to use the system with real clients after week one, and produce structured feedback that improves the system.** Specifically:

- ≥3 of the 3–5 pilot advisors are actively loading clients and reviewing output by end of pilot Week 2
- ≥1 piece of structured feedback per advisor per week (volume signals engagement; silence signals abandonment)
- No Sev-1 incidents (PII exposure, regulator-relevant misstatement, system unavailable for >1 day)
- A defensible answer to "would you recommend a colleague try this?" from at least 2 advisors at the end of the 6-week pilot window

If these aren't met, the pilot ends or extends with explicit revision; it doesn't quietly drift. Owner of the success-metric review: Fraser + Lori.

### 13.1 The Wednesday Som demo, IS validation, and senior stakeholder demos **[LOCKED — refined Day 3 morning]**

By the end of the offsite Wednesday, the team produces a **working MVP foundation** demonstrating the loop:

**Stage 1 → Stage 2 → Stage 3 → Stage 5**

The offsite produces three sequential demonstration events, each with a different audience and purpose:

| Event | Audience | Timing | Purpose |
|---|---|---|---|
| **Wednesday Som demo** | Som + executive sponsors | End of Day 3 (offsite) | Close of Phase A. Validates the foundation. Synthetic Sandra & Mike Chen as primary persona; real-derived persona only if audience composition supports it. |
| **Mon/Tue IS validation** | Lori's investment specialists | Following week, Mon–Tue | Structural beginning of Phase B. IS team runs the system end-to-end on **their own real tier-2 client data**. Most consequential testing event in the project. |
| **Senior Steadyhand stakeholder demo** | Senior Steadyhand leadership | Target 1–2 weeks after offsite | Phase B mid-window. Broader audience; runs on production-grade Phase B build with pilot disclaimer; gathers feedback that informs Phase C scoping. *"Notes on rough edges + product vision"* — Day 3 morning. |

Thursday at the offsite location and Friday at Purpose office serve as buffer/cleanup if Phase A slipped during the offsite week.

**Saranyaraj has an engineering hackathon Mon/Tue** that following week with partial availability; Phase B day-1 engineering capacity is reduced. Plan around it.

Pilot use (Phase C) begins after Phase B exit criteria (Section 13.0.1) are met — typically ~1–2 weeks after the senior stakeholder demo, depending on what Mon/Tue + senior-stakeholder findings surface.

### 13.2 Phase A build sequence — offsite scaffold (3 days, Mon–Wed) **[LOCKED]**

Phase A produces the foundation organized around **three pillars** (Day 2 framing, Saranyaraj):

1. **Ingestion layer** — robust extraction of client risk, goals, account mapping, time horizons from notes
2. **Portfolio engine** — Fraser's optimizer plugged into the application, tested with real fund data
3. **Reporting / dashboard** — *"Am I going to be okay?"* — the part nobody else has integrated

**Demo prioritization principle (Day 3 morning, Fraser):** *"You could demo if we just had the middle one [portfolio construction] and we could mock the ingestion. But if we nail the ingestion but haven't done how it constructs it, there's nothing to demo."* If time slips and a tradeoff is forced, **the engine is the must-have; ingestion can be mocked; reporting can be cut to essentials.** A Som demo without a working engine is no demo at all.

**UI polish, branding, and Purpose visual identity are explicitly deferred.** Usability for an advisor like Evan is the bar, not visual finish.

**Phase A is not advisor-usable on its own** — that's the work of Phase B (Section 13.0.1). The day-1-morning list is aggressive. **If the schedule slips on Day 1, the Wednesday Som demo is at risk because every subsequent day depends on it.** Buffer is built into the structure below: *critical path* items must land before lunch; *important but deferrable* items can move to Day 1 evening or Day 2 morning if needed. Thursday at offsite + Friday at Purpose office are available as additional buffer.

#### Day 1 morning — scaffold and contract

**Critical path (must land before lunch):**
- Repo with engine/extraction/integrations/web/frontend package boundaries
- Django + DRF + Postgres skeleton; Docker Compose for local dev
- React + Vite + Tailwind + shadcn/ui frontend skeleton talking to DRF
- Pydantic schemas for Household / Person / Goal / Account / RiskInput / Sleeve (legacy identifier; conceptually building-block fund) / EngineOutput
- Fund universe constant (six Steadyhand building-block funds; placeholder return/vol/correlation)
- Engine `optimize()` stub returning realistic-shaped output
- One end-to-end "hello world": login → client list → client detail (empty)
- LLM client wrapper (Anthropic provider for now)

**Important but deferrable to Day 1 evening:**
- Authenticated DRF foundation (Phase A per Part 9.2) with OIDC-ready user model
- Permission decorator on every view (advisor team scope; financial-analyst PII denial)
- Audit log table with append-only trigger

#### Day 1 afternoon — extraction Layers 1–3, one document type

- File upload UI; raw files land in `personas/<name>/raw/`
- Layer 2 text extraction for PDF + DOCX (CSV/XML deferred)
- Layer 3 `MeetingNoteExtraction` prompt + schema, populating Fact[T] rows
- Simple list view showing extracted facts with source quotes (bones of Layer 5)
- Validate against one real meeting note from Lori (or against existing project plan PDFs as placeholder if no real notes yet)

Principle: get one document type flowing end-to-end before adding breadth.

#### Day 1 evening — staging deployment + auth/audit catch-up

- Deploy to public URL (Render or simple EC2 + Caddy + Docker Compose)
- Catch up on Day-1-morning deferrables (auth, RBAC scaffolding, audit log)
- Read engine code from Fraser/Nafal artifacts; assess integration cleanliness

#### Day 2 morning — engine + full review UI

- Drop Fraser/Nafal optimizer code into `engine/optimizer.py`; wrap in I/O contract
- Fund universe with real numbers (or best-available placeholders — see Part 5.4)
- Wire engine to web app: approved client → "Generate portfolio" → engine call → result display
- Result display: stacked bar / donut for blend, building-block-fund-level breakdown, explainability trace, risk-rating mapping
- Layer 5 review UI: side-by-side documents + consolidated state
- KYC + statement extraction added (Layer 2-3 expanded)
- Layer 4 reconciliation (most-recent-wins, conflicts surfaced)
- Audit log writes on every engine run

#### Day 2 afternoon — design lock-ins + integration (this session, today)

This session locked the architectural decisions captured throughout this canon (goal × account optimization unit, 5/15/25/35/45 percentile mapping, three-component risk exposure, three-tab household/account/goal view, tax drag schema, admin-only CMA layer, override patterns, three-tier reporting). Engineering work continues into Day 3:

- Outcomes view: plan-progress visualization (Recharts), fan chart locked at t=0, dot at goal date, longitudinal "actual moves through fan" plotting
- Three-tab household / account / goal toggle in the dashboard (see Part 8.7)
- Click-through workflow for goal-account portfolio assignment (see Part 8.8)
- LLM-generated meeting prep + tier-appropriate copy (Tier 1 / 2 / 3 — see Part 8.4)
- Pre-recommendation override slider on the goal risk score; post-recommendation override note pattern (Part 7.5)

#### Day 3 (Wednesday) — Som demo close-out

- Final integration polish on the three pillars (ingestion → engine → reporting)
- Walk-through end-to-end on the demo persona (synthetic Sandra & Mike Chen as primary; real-derived persona only with audience composition confirmed in advance per Part 11.8.7)
- Final rehearsal on staging URL for the Som demo
- **Phase B kickoff scoping** — concrete list of pilot-hardening items, owners, target dates; calendar the IS Mon/Tue session

#### Phase B sketch — pilot hardening window (Mon/Tue IS demos + ~1–2 weeks)

Not built at the offsite, but scoped during Day 3 so Phase B work begins the following Monday with the IS demo session. Items here are necessary conditions for Phase B exit (Section 13.0.1):

- **Mon/Tue IS validation sessions** with Lori's team running the system on their own tier-2 client data; structured findings logged
- Auth Phase 1: per-advisor accounts, password reset, MFA, session timeout, lockout
- Error handling: empty states, network failures, malformed uploads, partial extraction, engine timeout
- Edge-case coverage on extraction: documents Claude can't classify, meeting notes with no extractable goals, conflicting facts the reviewer can't easily resolve
- Pilot-mode disclaimer surfaced on every recommendation screen
- Override audit trail per Part 7.5
- Admin-only CMA + frontier view (Part 4.7)
- Feedback channel operational; triage owner identified
- IS onboarding documentation written and reviewed
- Kill-switch tested
- Mon/Tue findings closed; one real tier-2 persona walked end-to-end with Lori with no blocking findings

Phase B owner: Raj + Fraser. Daily standup until Phase B exit. **Saranyaraj hackathon Mon/Tue the following week reduces day-1 engineering capacity** — front-load decisions, defer execution.

### 13.3 Compression risks (named) **[LOCKED — refreshed Day 2]**

- **Real-PII handling discipline slips under offsite pressure.** Highest-consequence operational risk. The pre-commit scrub-pass hook, the Bedrock-only routing for real-derived personas, the `MP20_SECURE_DATA_ROOT` outside-repo validation, the encrypted disk requirement, and the gitignore patterns must be in place *before* any real file is copied. The defense-in-depth regime (Part 11.8.3) is what protects this build; if any link weakens, real client material does not enter the system.
- **Pilot retention risk.** If pilot software is bad, advisors don't come back. There's no second pitch. Phase B exit criteria exist for this reason; an under-baked pilot launch is worse than no pilot launch.
- **The "false euphoria" risk** (Day 2, Fraser): *"the school play is three weeks away and like, guys, we're ready. I don't know my lines."* Phase A produces a production-grade foundation that works for the Som demo on the synthetic persona. Phase B is when broader paths break and need fixing for real IS use across many client variants. Resist the urge to declare victory at Wednesday close.
- **Saranyaraj hackathon Mon/Tue reduces Phase B day-1 capacity.** Known constraint; not a surprise. Front-load Phase B planning during Day 3 (Wednesday) so partial-availability days are productive.
- **Mon/Tue IS validation finds large gaps.** This is the most consequential testing event in the project and almost certainly will surface real gaps. Plan for Phase B to extend if needed; do not pre-commit to a Phase C launch date until Mon/Tue findings are triaged.
- **Support load underestimated.** 3–5 advisors using the system can generate more support traffic than 4 engineers can absorb mid-build. Phase B includes establishing the feedback channel + triage owner explicitly so this doesn't degrade into Slack DMs to Lori.
- **Authorization basis for real-PII use unconfirmed in writing.** Real PII has been flowing through the system since Day 2 evening under implicit "internal use for service improvement" basis. Retrospective written confirmation from Lori + Amitha is now a Phase B exit blocker (Part 11.8.1, open question #24). Until the basis is documented, no expansion of real-PII volume beyond current pilot scope.
- **Bedrock enablement on Purpose's AWS account formally unconfirmed.** Real-derived extraction has been routing through Bedrock ca-central-1 (compose runs verified through 2026-04-29). Formal IT confirmation that this is sanctioned org policy is still owed (Part 14 item 3, open question #25).
- **Croesus export format unknown until Lori provides one.** Get one real meeting note before writing extraction prompts. 30 minutes of reading saves hours of building against assumptions.
- **Engine code cleanliness unknown.** If Fraser/Nafal hand a clean function, integration is 30 minutes. If a Jupyter notebook with execution-order dependencies, half a day of refactoring. Read the code Day 1 evening.
- **Phase A → B auth controls layered, not bolted on.** Phase A's authenticated-by-default DRF + advisor team scope + financial-analyst PII denial are the production-grade foundation; Phase B layers MFA / lockout / password reset / session timeout / audit browser UI on top (Part 9.2). If any of these layers regress to "we'll add it later," that's a Phase B exit failure, not a soft target.
- **Lori-as-single-point-of-failure for data pipeline.** Identify a backup; ensure at least one fully synthetic persona is end-to-end functional without real-data dependency.
- **CMA placeholder masquerading as real numbers.** If Part 5.4 unresolved by Wednesday Som demo, demo narrative must explicitly say "illustrative numbers." Pilot output (Phase C) cannot have placeholder math sitting under real-client recommendations.
- **Three-tab view scope creep.** Day 2 identified the household/account/goal toggle as the single biggest "wow." It's also a nontrivial UI build. If running tight, the goal tab is the must-have novelty; account-tab and household-tab can launch with simpler cuts and iterate.
- **Override note friction.** Steadyhand IS already note every interaction. Adding mandatory override notes risks fatigue. Inline the note capture; don't create a separate workflow.
- **Bad-output incident in early pilot.** An advisor takes a wrong recommendation to a real client conversation. Mitigations: pilot-mode disclaimer, weekly retros, kill-switch, audit log enabling root-cause reconstruction. Cannot be eliminated; can be contained.

### 13.4 Parallel work split — owners per Day 3 afternoon task allocation

**Integration direction [LOCKED — Day 3 afternoon §3]:** Raj's backend plugs into Nafal's frontend, **not** the other way around. Nafal's UI design elements are strong and become the presentation layer; Raj's heavy-backend (optimization engine, CMA management, document ingestion, audit trails, data reconciliation) wires in behind it. The Day 3 afternoon decision direction is *do not rebuild the frontend in Raj's backend*.

When goal-to-account mapping completes in Nafal's frontend, it calls Raj's backend optimization engine to generate the ideal portfolio. The frontend renders current holdings, ideal portfolio, the comparison view (Part 8.8), and (eventually) the trade moves required to rebalance (Part 8.10). Client sophistication level (per Part 8.4) flows through to the reporting layer and defaults the level of detail shown.

| Person | Owns (current) |
|---|---|
| **Saranyaraj** | Integrate correlation matrix into optimization engine. Validate / pressure-test optimization math against Fraser's reference model (Part 4.7.4). Add chart visualizations to efficient-frontier output. Polish CMA UI and add correlation-matrix management (Part 4.7.1 draft/publish). Connect backend engine to frontend goal/account mapping (per integration direction above). Build reporting output layer (fan charts, comparison views per Part 8.9). Continue: CAT/Resource integration points mocked for MVP, tax drag schema, advisor override + audit. |
| **Nafal** | Build data review / conflict resolution screen with three mockup states (Part 11.5). Enable goal-level risk-tolerance override with reason capture. Add goal-to-account mapping in onboarding UI. Implement re-goaling concept (Part 6.3a) — realign funds between goals, conceptual not money-movement. Configure reporting by client sophistication level (Part 8.4). Duplicate document/record detection mechanism. Share HTML questionnaire with team; revise ingestion questions. Prepare guided-walkthrough demo for stakeholder sessions (Part 13.5). |
| **Fraser** | *Done:* client visualization concepts (account × goal views, pivot views). *In progress:* fan chart / success tracking visualization concepts; feeding sample investment-review data into prototype. **Define rebalancing trigger thresholds (% + $ minimums)** per Part 7.5a. **Produce 3-month roadmap alongside demo deliverable.** |
| **Lori** | Upload all client documents (including external statements) to system. **Determine default goal classification wording for regulators** (Part 6.3b open question #61) with Fraser. User validation for UX mockups. Persona selection. IS pilot training material. Authorization-basis confirmation with Amitha (Part 11.8.1). |
| **Team** | Record Teams transcripts for all collaborative sessions (this canon is downstream of those). Prepare guided-walkthrough demo for senior Steadyhand stakeholders — target 1–2 weeks (separate event from Wednesday Som demo, see Part 13.1). |

Roughly halves wall-clock if handoffs are clean. The team is small enough that "parallel" is partial; pairing on big interfaces (e.g., the three-tab view, the goal-level risk logic, the integration boundary) is preferred over strict ownership.

### 13.5 Demo flow **[LOCKED — Day 2 framing + Day 3 afternoon format/persona refinements]**

**Format — guided walkthrough, not hands-on test [Day 3 afternoon §9.1]:** the team demos the system to stakeholders (showing real-life use cases, narrating the workflow, answering questions) rather than putting the prototype in untrained users' hands. The system is complex enough that without training, users would struggle, and a guided demo communicates the vision more effectively at this stage. Hands-on testing is reserved for the IS Mon/Tue validation session (where the audience *is* the trained user).

The demo flow is the path Phase A optimizes for. Every screen serves a specific minute. Everything else is Phase B+.

```
1. INGESTION — drop a .docx of consolidated meeting notes
   → AI ingestion populates the structured client object
   → advisor reviews/validates the extraction (Layer 5 review UI)
   → ingestion can be mocked / pre-loaded for the demo (Day 3 morning prioritization)

2. HOUSEHOLD VIEW — "here's everything we manage for them"
   → total AUM, no partitioning
   → toggle between funds / look-through-to-asset-classes (Part 8.7)

3. DRILL INTO ACCOUNTS — same total, sliced by accounts
   → click into the dual-purpose RSP account
   → see its current holdings (Steadyhand-internal funds, full detail)

4. DRILL INTO GOALS — same total, sliced by goals
   → see the M:N goal-account mapping
   → demo case: RSP serving BOTH retirement AND first-home-buyers' plan
     (~$60K of the RSP earmarked under FHBP for home purchase)
     — most common dual-purpose Steadyhand scenario per Day 3 afternoon §5.1

5. CLICK-THROUGH PORTFOLIO ASSIGNMENT — for the dual-purpose RSP
   → identify the two goals it serves (retirement + FHBP home)
   → assign proportions (e.g., $60K to home, remainder to retirement)
   → for each goal-account combo, system recommends a portfolio
   → retirement goal: long horizon, balanced/growth blend
   → FHBP goal: short horizon, conservative blend (cash-heavy as horizon nears)
   → no efficient frontier shown to advisor (admin-only)
   → just "we recommend this" with the one-sentence justification (Part 8.5)
   → system merges into the consolidated RSP portfolio
   → may collapse to a single whole-portfolio fund (Founders, Builders) if optimal

6. PORTFOLIO RECOMMENDATION VIEW
   → current vs. ideal allocation, side-by-side (existing-client mode)
   → "Express as moves" — trade list per Part 8.10
   → tier-appropriate explanation copy (Tier 1 / 2 / 3)
   → fan chart at the household level — current vs. optimized overlaid (Part 8.9)

7. RETURN TO DASHBOARD — "am I going to be okay?"
   → integrated outcome view across all goals
   → the part nobody else has done
```

**Demo persona [Day 3 afternoon §9.2]:** a hypothetical couple with an **RSP that has both retirement and first-home goals** (the dual-purpose account scenario — most common real-world Steadyhand case). This is the demo case for senior Steadyhand stakeholder demos and is the hero scenario for the Wednesday Som demo. Sandra & Mike Chen (Part 13.6) remains the synthetic backup if a different persona is needed.

**What's mocked vs. real for demos [Day 3 afternoon §9.2]:**

- *Mocked / pre-loaded acceptable:* document ingestion (use personas with pre-loaded data), personalized after-fee returns (complex math, not essential to MP2.0 core)
- *Must be real:* portfolio construction engine (Day 3 morning prioritization — *"if we nail the ingestion but haven't done how it constructs it, there's nothing to demo"*), goal-account mapping flow, recommendation output, comparison view, fan chart

For the IS Mon/Tue session this runs on the IS's own real tier-2 clients (each IS sees only their own clients, RBAC-enforced via advisor team scope per Part 9.2). For the senior stakeholder demo (~1–2 weeks out), use the dual-purpose RSP persona with synthetic data unless the audience composition has been confirmed in advance.

### 13.6 Test personas — five synthetic clients for v1

Lori will provide redacted real-client examples; in parallel, generate Claude-authored synthetic personas for breadth and for testing edge cases. The five v1 personas should span:

| Persona | Profile sketch | What it tests |
|---------|---------------|---------------|
| **1. Pre-retiree couple (Sandra & Mike Chen)** | 60s, ~$1.5M, retiring in 5 years, multiple goals (retirement income, leave estate to kids, one big trip) | Multi-goal household, glide path, income vs. growth blend. **Synthetic backup persona for the Som demo — used if real-client demo path encounters issues. Remains useful through Phase B/C as a stable test fixture without real-PII routing dependencies.** |
| **2. Young professional, single** | 32, ~$120K, single goal (house in 4 years), high savings rate | Single goal, short horizon, growth-leaning client with conservative goal |
| **3. Mid-career family** | 45 + 43, two kids, ~$400K, retirement + RESPs + paying down mortgage | Many goals, RESP tax mechanics, balanced blend |
| **4. Recently retired** | 68, ~$2M, drawdown phase, leaves a legacy goal | Decumulation, LPF natural fit, tax-efficient withdrawal |
| **5. Post-windfall** | 50, just inherited $500K, no formal plan, anxious | Money-in-motion, behavioral cautious, plan-from-scratch flow |

The Birth-of-Child / Job-Loss / Inheritance / Retirement / Divorce / End-of-Life / House-Purchase / Post-Secondary checklists already in the project provide event-trigger scenarios for testing the Stage-6 loop.

In addition to the five synthetic personas above, **the build uses real-derived personas at increasing volume across phases**: 1–2 during Phase A from Lori's tier-2 client base (validate extraction against real document shape; tier-2 clients are the natural test bed — small enough to be tractable, real enough to be credible per Day 2 §8.3), the IS team's own tier-2 clients during the Mon/Tue Phase B sessions, and ~15–50 during Phase C (3–5 pilot advisors, 5–10 clients each — see Part 11.8.2). All real-derived personas are pseudonymized per Part 11.8.3. Sandra & Mike Chen remains the synthetic backup persona.

### 13.7 Out-of-scope-for-pilot (explicit)

Items below are out of scope for Phase A and Phase B. Some may move into scope during Phase C iteration based on advisor feedback; some are post-pilot work.

- **No real custodian connection.** Recommendations are informational; no order placement, no holdings update against real accounts.
- **No real-time prices.** Snapshot data acceptable for pilot. Advisors are informed.
- **No real client PII visible to anyone but the advisor whose client it is.** Real-derived personas are pseudonymized per Part 11.8.3 before any rendering. Real PII never reaches committed code (Part 11.7); real PII never reaches a US-resident LLM endpoint (Part 11.8.4). RBAC enforces per-advisor visibility.
- **No mobile native UI.** Web on desktop browser only for the pilot. If pilot advisors strongly request iPad use in client meetings, this becomes a Phase C scope question — not auto-scoped in.
- **No actual order placement or trade execution.** Stage 4 is mocked. The system produces recommendations; advisors execute via existing Steadyhand processes.
- **No automated client-facing communication.** AI-personalized updates (Part 8.3) are advisor-reviewable drafts during pilot, not auto-sent.
- **No external (non-Steadyhand) advisor onboarding.** Pilot is Steadyhand IS only. Harness/3rd-party advisor scope is Phase D+.

---

## PART 14 — ITEMS TO CONFIRM WITH PURPOSE IT

Before broader pilot expansion, get explicit answers. **REAL-PII BLOCKER items must be confirmed before pilot launch (Phase B exit); current implementation has been operating under implicit "internal use for service improvement" basis.**

1. ECS namespace / IAM boundary / tagging convention for MP2.0 inside the existing AWS account
2. Federation pattern: Entra → AWS SSO via SAML, or OIDC, or other
3. **[REAL-PII BLOCKER — apparently resolved for ca-central-1; confirm formally]** Bedrock enablement in ca-central-1: implementation has been routing real-derived extraction through Bedrock; confirm this is sanctioned org policy and document the AWS account, IAM role, and service control posture.
4. **[REAL-PII BLOCKER]** Data classification tier for client PII; storage and encryption requirements that flow from it. Confirms whether Part 9.3 / Part 11.8 defaults are sufficient or need tightening.
5. Existing logging/observability stack: Elastic only, or also Datadog/Splunk; where audit logs need to be queryable
6. Maintenance windows on the shared ECS-EC2 cluster (avoid Wednesday Som demo + Mon/Tue IS session + pilot-active-time node drains)
7. Whether MP2.0 CI/CD can deploy autonomously or needs platform team approval per change
8. **[REAL-PII BLOCKER]** Confirmation from Amitha (Purpose legal) of the authorization basis for using real Steadyhand client documents in product development (Part 11.8.1). Real PII is currently flowing under implicit basis; **retrospective written confirmation is needed before broader pilot expansion**.
9. **[REAL-PII BLOCKER]** Amitha sign-off on the defense-in-depth privacy regime in Part 11.8.3 in lieu of pre-LLM pseudonymization, or instruction to implement pseudonymization as a pre-pilot fix.

---

## PART 15 — OPEN QUESTIONS & DECISIONS PENDING

### 15.0 Top priorities right now **[Living shortlist — 7 items]**

The full open-questions table below has 68 entries spanning multiple horizons. This shortlist surfaces the items that are highest-leverage *as of this canon revision* — items where unblocking them unblocks substantial downstream work, or where leaving them open creates real risk. This list is meant to be re-read at each canon revision and rotated as items resolve.

| Priority | Item | Why now | Owner | Refers to |
|--:|---|---|---|---|
| 1 | **Written authorization basis from Lori + Amitha** for real-PII use in product development | **RESOLVED for limited-beta scope (2026-04-30).** Real PII is authorized for limited-beta, local-production-like operation (two roles, current deployment) under §11.8.3 defense-in-depth. Broader rollout requires Lori + Amitha review; revisit 2026-05-21. | Lori + Amitha | #24, Part 11.8.1 |
| 2 | **Bedrock ca-central-1 enablement formally confirmed** with Purpose IT | Real-derived extraction is already routing through Bedrock ca-central-1 in the running implementation; formal IT confirmation that this is sanctioned org policy is still owed. Same Phase B exit blocker. | Saranyaraj + Purpose IT | #25, Part 14 item 3 |
| 3 | **Correlation matrix integrated** into the optimization engine | Blocking dependency for math validation (Part 4.7.4). Without correlations, the engine output cannot be pressure-tested against Fraser's reference model, and no engine-driven pilot recommendations are defensible. | Saranyaraj | #56, Part 5.4 |
| 4 | **Engine output contract migrated** from goal-level to per-link (`LinkBlend`, account roll-ups, fund-of-funds collapse, fan chart per link) | Current scaffold returns goal-level placeholders; canon Part 12.1 requires per-link first. Phase B exit blocker; upstream of UI work on the three-tab view. | Saranyaraj | #47, Part 12.1 |
| 5 | **CAT and Resource API specifications** (mocked for MVP, integration later) | Without the real specs, the source-priority hierarchy in Part 11.4 (system-of-record > documents > notes) can't ship its real implementation; only its mocked behavior. Decisions about what the mock returns shape the production wire. | Saranyaraj + Steadyhand | #51, #52, Part 9.4.3 |
| 6 | **Default goal classification regulator wording** — "savings" implies cash; alternatives like "long-term savings" or "undefined goal" | Required before real-client onboarding via Part 6.3b; affects every client whose intake produces no explicit goal. Small wording question, real downstream effect. | Lori + Fraser | #61, Part 6.3b |
| 7 | **3-month roadmap** alongside the demo deliverable | Currently the canon documents Phase A → B → C without a calendar. Senior stakeholder demo (target ~1–2 weeks) is the venue for setting realistic expectations; the canon shouldn't be the source of date commitments without a roadmap to align against. | Fraser | #64, Part 13.1 |

The numbered references (#NN) point into the 68-item table that follows. As items resolve, this shortlist rotates. Items that move from #1–7 into "RESOLVED" status are not silently removed from the table below — the audit trail of which items mattered when matters.

### 15.1 Full open-questions table

| # | Open question | Owner | Status |
|--:|--------------|-------|--------|
| 1 | Final method for risk-on-frontier (percentile / probability / utility) — Method 1 with 5/15/25/35/45 percentile mapping locked Day 2 | Saranyaraj + Fraser | LOCKED for v1 |
| 2 | Specific weighting in the household × goal risk composite | Team | OPEN — document the function, parameterize for tuning |
| 3 | Compliance risk-rating mapping function — exact thresholds | Lori + Saranyaraj | OPEN |
| 4 | Bond-only building-block fund launch path | Salman + Tom | OPEN — highest-leverage product-side gap |
| 5 | Whether and how to model Founders Fund / Builders Fund (active layer) | Saranyaraj | LOCKED — leave as fund-of-funds collapse target (Part 4.3b), not modeled as a separate building-block fund |
| 6 | Household-level risk handling when accounts blend differently | Team | RESOLVED Day 2 — optimization unit is goal × account (Part 4.3a); per-link risk uses combined score |
| 7 | API integration with Conquest — feasibility for v2 | Saranyaraj | OPEN — v1 uses file/manual entry |
| 8 | Goal-decomposition model — turning narrative goal ("retire well") into fungible $ targets | Team | DEFAULT — wants/needs/wishes split is the v1 approach; future-dollar targets are secondary input only (Part 4.3c) |
| 9 | Reporting / portal scope — what does Andrew's team build first | Andrew + team | OPEN — out of MAT scope but blocking for full pilot experience |
| 10 | Behavioral-bucket schema — how many buckets, how to assign | Lori + Saranyaraj | PARTIALLY RESOLVED — three sophistication tiers locked (Part 8.4); behavioral-bucket emphasis composes within tiers |
| 11 | When does drift trigger rebalance — exact thresholds | Team | DEFAULT — 3–5% off, or material event, or actual breaches bottom of fan (Part 8.9) |
| 12 | Whether goal-level questionnaire is one question or three | Lori + Fraser | RESOLVED Day 2 — single 5-point question per goal, with 5-point household composite |
| 13 | How external (non-Purpose) assets enter the household view | Team | RESOLVED Day 2 — optional risk-tolerance dampener (Part 4.6a); not full simulation |
| 14 | Testing protocol — internal IS feedback (Mon/Tue post-offsite) + Som demo Wednesday + advisor pilot | Lori + Saranyaraj | LOCKED |
| 15 | Capital market assumptions source for fund return/vol/correlation inputs | Saranyaraj + Fraser | OPEN — required before Phase B exit. Now also tied to admin-only CMA editor (Part 4.7) |
| 16 | Real meeting note shape (templated vs freeform, length, structure, date conventions) | Lori → Raj | OPEN — get one real note before finalizing extraction prompts |
| 17 | Building-block-fund numerical inputs (real vs placeholder) for v1 | Saranyaraj + Nafal | OPEN — engine can stub initially; tax drag default 0 acceptable for v1 |
| 18 | Optimizer code handoff timing from Fraser/Nafal artifacts | Fraser, Nafal → Raj | LOCKED — integration-ready before Day 3 morning |
| 19 | PDF rendering library for client outputs (WeasyPrint, ReportLab, headless Chrome) | Raj | DEFAULT — defer to week 2 |
| 20 | Fast-forward simulator: pre-baked future states or live re-projection | Team | DEFAULT — pre-baked acceptable for Som demo; revisit for pilot iteration |
| 21 | Reconciliation strategy beyond most-recent-wins | Team | OPEN — post-MVP refinement |
| 22 | Frontend-comfortable person assignment for parallel build | Team | RESOLVED — small team, partial-parallel pairing on big interfaces (see Part 13.4) |
| 23 | Lori's backup for file-pipeline operational dependency | Lori + team | OPEN — name before broader pilot expansion |
| 24 | Authorization basis for real-client-PII use in product development — written confirmation from Amitha | Lori + Amitha | **RESOLVED for limited-beta scope (2026-04-30).** Real PII is authorized for limited-beta operation (two roles, current local-production-like deployment) under §11.8.3 defense-in-depth. Broader rollout requires Lori + Amitha review; revisit 2026-05-21. |
| 25 | Bedrock ca-central-1 enablement on Purpose's AWS account | Saranyaraj + Purpose IT | PARTIALLY RESOLVED — implementation has been routing real-derived extraction through Bedrock; formal IT confirmation that this is sanctioned org policy is still required. |
| 26 | Per-persona pseudonym mapping storage mechanism | Raj | RETIRED — boundary pseudonymization regime not implemented; superseded by defense-in-depth in Part 11.8.3 |
| 27 | Quasi-identifier handling — leave in or strip | Lori + Raj | OPEN — current implementation leaves quasi-identifiers in structured facts; access control limits exposure. Strip-or-leave decision is part of the Amitha review (Q24). |
| 28 | Real-PII retention period and disposal trigger | Team | PARTIALLY RESOLVED — local disposal command exists (`dispose_review_artifacts`); team-level cadence and trigger policy still open |
| 29 | Som demo audience — show synthetic only or include a real-derived persona | Lori | OPEN — synthetic-only is the default; revisit before Wednesday only if a real-derived demo would meaningfully advance the conversation |
| 30 | Identity of the 3–5 pilot advisors and their commitment to Phase C participation | Lori | OPEN — name and confirm before Phase B exit |
| 31 | Phase B exit criteria sign-off — who signs and how disagreements resolve | Fraser + Lori + Raj | OPEN — agree before Phase B work begins in earnest |
| 32 | Pilot-mode disclaimer wording — exact text on every recommendation screen | Lori + Amitha | OPEN — review before Phase B exit |
| 33 | Feedback channel and triage owner | Team | OPEN — choose before Phase B exit |
| 34 | IS pilot training material — written guide, walkthrough format | Lori | OPEN — drafted in Phase B |
| 35 | Pilot success metrics — finalize the targets in Section 13.0.3 | Fraser + Lori | DEFAULT — current targets are working defaults |
| 36 | Pilot duration and exit decision — when does Phase C end, what's the next phase | Fraser + Som | OPEN — 6-week working assumption |
| 37 | True Plan ↔ Portfolio iterative recursion (Conquest Monte Carlo round-trip with optimizer) | Team | OPEN — mathematically attractive but expensive; v1 is single-pass, revisit later |
| 38 | Real vs. nominal dollars in long-duration projections | Team | OPEN — acknowledged Day 2, unresolved |
| 39 | Whether the client (vs. only the advisor) sees the goal-account three-tab view | Lori vs. Fraser | OPEN — Lori leans client-sees-only-the-report; Fraser leans client-sees-trimmed-version-of-dashboard. Resolve before Phase C |
| 40 | User testing proxy strategy — non-engaged spouses as testers? | Team | OPEN — floated Day 2; needs concrete plan |
| 41 | Articulating to clients the value of disclosing external holdings | Lori | OPEN — needed before pilot to drive disclosure rate |
| 42 | CMA admin permissions model (single role vs. tiered) | Saranyaraj + Lori | OPEN — Phase B work; admin-only flag is the v1 minimum |
| 43 | Override note inline UX — how to capture without creating workflow fatigue | Saranyaraj + Lori | PARTIALLY RESOLVED — section approval with notes is implemented; pre/post-recommendation override UX is Phase B |
| 44 | Match-score threshold for fund-of-funds collapse recommendation (Part 4.3b) | Saranyaraj + Fraser | OPEN — what % composition match triggers "use Founders instead" |
| 45 | CI Playwright synthetic E2E execution — local Chromium install hung; CI installs before run | Raj | OPEN — verify CI runs synthetic E2E green before Phase B exit |
| 46 | CI PII scanners (commit-time pattern detection) | Raj + Lori | OPEN — Phase B work; pre-commit scrub-pass exists locally |
| 47 | Engine output contract migration from goal-level to per-link (`LinkBlend`, account roll-ups, fund-of-funds collapse, fan chart per link, compliance ratings) | Raj | OPEN — Phase B blocker. Current scaffold returns goal-level placeholders; canon Part 12.1 requires per-link first |
| 48 | Risk scale code migration from 1-10 placeholder to 5-point snap-to-grid with 5/15/25/35/45 mapping | Raj | OPEN — Phase B work to align code with canon Part 4.2 |
| 49 | Goal target_amount migration from required to optional secondary input | Raj | OPEN — Phase B; current Goal model requires it. Canon Part 4.3c says optional. |
| 50 | UI vocabulary migration from low/med/high to cautious / balanced / growth-oriented in client-facing surfaces | Raj | OPEN — Phase B; current UI surfaces low/med/high in risk badges. Internal labels stay; client-facing copy changes. |
| 51 | CAT API specification (trade execution / account values) | Saranyaraj + Steadyhand | OPEN — mock for MVP per Day 3; integration spec needed for post-MVP. |
| 52 | Resource API specification (CRM / Steadyhand) | Saranyaraj + Steadyhand | OPEN — mock for MVP per Day 3; integration spec needed for post-MVP. |
| 53 | Confidence-threshold value for risk-score "needs advisor input" flag | Saranyaraj + Lori | DEFAULT — 0.7 working default per Day 3 §2; tune in Phase B based on observed false-positive rate. |
| 54 | "Needs attention" UI string final wording — separating data-ingestion alerts from portfolio/planning alerts | Lori + Nafal | OPEN — lexical split locked Part 8.6a; exact strings TBD. |
| 55 | Goal duration formula for edge cases — couples with different retirement dates, phased retirements, multi-generational goals | Fraser + Nafal | DEFAULT — split into multiple goals per Part 4.3d; revisit when edge cases hit real client data. |
| 56 | CMA correlation matrix storage format (decomposed linear arrays per Day 3 — confirm DB schema) | Saranyaraj | OPEN — Phase B work alongside CMA admin portal. |
| 57 | Demo-vs-mock split for senior Steadyhand stakeholder demo (target 1–2 weeks) — what runs real, what runs mocked | Fraser + Saranyaraj | OPEN — engine real, ingestion may still be mocked per Day 3 prioritization. |
| 58 | Alignment with Purpose Engineering Director on React-based Advisor Center foundation — when do MP2.0 modules snap into that platform | Fraser + Engineering Director | OPEN — Phase B/C strategic conversation per Part 1.7. |
| 59 | Stale-portfolio UX — auto-update with delta panel vs. hover-over delta vs. pure stale flag | Saranyaraj + Nafal | OPEN — Day 3 afternoon §1.3 left this for post-UI-integration finalization; current default is pure stale flag with manual regenerate. |
| 60 | Trade-level consent UX (per-trade vs. batch confirmation in the "Express as moves" flow) | Saranyaraj + Lori | OPEN — Phase B; the audit trail must capture consent at the move level per Part 7.5a, but UI affordance is open. |
| 61 | Default goal classification wording for regulators — "savings" implies cash; alternatives like "long-term savings" or "undefined goal" | Lori + Fraser | OPEN — Day 3 afternoon §5.3 task list item. Resolution before pilot use. |
| 62 | Fallback structured questionnaire — final HTML form for missing-fields fallback path (Part 6.7) | Nafal | OPEN — Day 3 afternoon §10 task list item; will share with team for revision. |
| 63 | Rebalancing trigger thresholds (% + $ minimums) per Part 7.5a | Fraser | OPEN — Day 3 afternoon §10 task list item. Compliance burden raises threshold above naive 5% drift. |
| 64 | 3-month roadmap deliverable alongside demo | Fraser | OPEN — Day 3 afternoon §10 task list item. |
| 65 | Risk band labels — final discipline on "low / low-medium / medium / medium-high / high" vs. "cautious / conservative-balanced / balanced / balanced-growth / growth-oriented" in client-facing UI | Lori + Nafal | OPEN — Day 3 afternoon §2.3 surfaced ambiguity; v2.5 supersedes (#54) but Day 3 afternoon noted both vocabularies were discussed; finalize before pilot. |
| 66 | Personalized after-fee returns — when to add (deferred per Day 3 afternoon §2.2; Steadyhand fee-reduction program makes per-client computation complex) | Saranyaraj + Lori | OPEN — not v1 scope; revisit before broader pilot expansion. |
| 67 | Duplicate / phantom record prevention — backend logic to detect and link duplicate household records when documents are dropped | Nafal | OPEN — Day 3 afternoon §4.3 task list item. Near-term: persona-based demo; future: require uploads against existing client/household ID. |
| 68 | Householding consent withdrawal flow — UX when one partner of a couple withdraws consent post-pilot | Lori + Saranyaraj | OPEN — Part 6.1 covers the data model; UX flow is Phase B. |

---

## PART 16 — GLOSSARY & VOCABULARY

Use these terms precisely. Inconsistency confuses the team and the build.

### 16.1 Strategic & investment vocabulary

| Term | Definition |
|------|------------|
| **MP2.0** | Model Portfolios 2.0 — this initiative |
| **Building-block fund** | A standardized, single-mandate fund used as a constituent of personalized blends. The "molecules" of the system. 8–12 in the universe. Replaces the retired "sleeve" / "sleeve fund" terminology (Day 3 afternoon §2.1). See Part 2.2. |
| **Atom** | Underlying security held inside a building-block fund (an individual stock or bond). Clients/advisors don't operate at this level; the Macro Insight Layer does. |
| **Blend** | The personalized mix of building-block funds driven by a client's plan. The painting. |
| **Blend ratios** | The specific percentages of each building-block fund in a client's blend. |
| **Macro Insight Layer** | The CIO/strategist function that updates the internals of building-block funds (atoms) based on macro views. Independent of client blends. |
| **Living Financial Plan** | The continuously-updated model of the household's situation. Source of truth for blends. Not a document. |
| **Paint mixing** | Fraser's analogy: building-block funds are paints, blend is the painting, atoms are the pigments. |
| **Frontier** | The efficient frontier — set of optimal portfolios in (volatility, return) space. |
| **Glide path** | The trajectory of a blend toward lower-risk (cash) as a goal nears its target date. |
| **Necessity score** | Per-goal: 1=wish, 3=want, 5=need. Drives goal-level risk score. |
| **Risk descriptor (client-facing)** | "Cautious / Conservative-balanced / Balanced / Balanced-growth / Growth-oriented." Pilot UI defaults to this vocabulary in client-visible copy. *"Low / medium / high"* is held internally for engine math and compliance; client-facing exposure is open (Day 3 afternoon §2.3 surfaced ambiguity, open question #65). See Part 4.2. |
| **Household risk tolerance** | Composite score capturing investment knowledge, behavior, capacity. Property of the household (Day 3 afternoon §2.3 lexical discipline). |
| **Goal-level riskiness** | Per-goal: how essential is this goal, plus portion of household AUM allocated. Property of the position/portfolio (Day 3 afternoon §2.3). |
| **Wants and needs (and wishes)** | Goal categorization. Some constructs use 3 levels; we currently merge to 2. |
| **Whole-portfolio fund** | A multi-asset fund-of-funds (Founders, Builders, PACF, etc.) that may serve as a fund-of-funds collapse target when an optimization output closely matches its composition. Distinct from a building-block fund. |
| **MAT** | Mission-Aligned Team — the 5-person offsite group. |
| **One Purpose** | Internal vision: integrated wealth experience across Purpose's businesses. |
| **CRM 3** | Canadian fee/disclosure regulation requiring full FER + advisor fee disclosure. |
| **KYC** | Know-Your-Client; mandatory regulatory data set. |
| **MFDA / CIRO** | Canadian regulator (MFDA terminology still used operationally). |
| **CFP / QAFP** | Designations required to provide comprehensive financial planning. |
| **IS** | Investment Specialist — Steadyhand's client-facing role. |
| **LPF** | Longevity Pension Fund — Purpose's flagship retirement income product. |
| **Steadyhand** | Purpose subsidiary; MP2.0 v1 launch context. |
| **Harness** | Purpose advisor platform; v2 deployment target. |
| **Link** | Purpose direct/group plans platform. |
| **Partnership Program** | Purpose's IA consulting program. |

### 16.2 Engineering vocabulary

| Term | Definition |
|------|------------|
| **Engine boundary** | The rule that engine code never imports from web/, integrations/, or extraction/. Engine takes Pydantic in, returns Pydantic out. |
| **Adapter pattern** | Each external system has an interface + mock + future-real implementation. Mock today, real later, no UI/engine change. |
| **Layer 1–5** | Stages of the extraction pipeline: raw → text → facts → reconciled state → reviewed state. |
| **Fact[T]** | The temporal extraction unit. `field`, `value`, `asserted_at`, `confidence`, `derivation_method`, `source_quote`, `source_doc_id`, `extraction_run_id`. |
| **ClientState** | The Pydantic object the advisor approves in Layer 5; the canonical engine input. |
| **EngineOutput** | The Pydantic object the engine returns: blends, roll-up, fan chart, risk rating, audit trace. |
| **Audit log** | Append-only Postgres table separate from observability logs. Different system, different retention. |
| **OIDC-ready user model** | Minimal user model (email-as-identity) so swapping auth providers is config not migration. |
| **Provenance** | The source quote + document reference attached to every extracted fact. Non-negotiable. |
| **The Trucon problem** | The anti-pattern of a single rigid integration causing platform-wide failures. Modularity exists to avoid this. |
| **Three-layer pipeline** | Raw → Parsed → Engine Input. Each stage stored, each stage independently inspectable. |
| **Determinism / AI-creativity balance** | Workflows deterministic; AI extracts and styles, never produces financial figures. |
| **Pseudonymization boundary** | The Layer 2→Layer 3 step where real names, addresses, and account numbers are replaced with stable pseudonyms. Reverse mapping kept locally and encrypted; never committed, never sent over the wire. |
| **Quasi-identifier** | A field that doesn't directly identify a person but combined with others can — employer, neighborhood, family situation, health detail. Pseudonymizing names alone does not handle these. |
| **`data_origin` flag** | Per-persona attribute (`synthetic` or `real_derived`) routing LLM calls — synthetic to Anthropic API direct, real-derived to Bedrock ca-central-1. Misconfiguration is a deployment-blocker check. |
| **REAL-PII BLOCKER** | Tag on items that must be resolved before any real client PII enters the build environment. Build proceeds on synthetic personas only until cleared. |
| **Phase A / Phase B / Phase C** | The three delivery phases. A = offsite scaffold (2 days, demo-grade foundation). B = pilot hardening window (~2 weeks, advisor-usable). C = pilot launch and iteration (3–5 Steadyhand advisors using the system with real clients). See Part 13.0. |
| **Phase B exit criteria** | The gate items that must be true before any advisor logs in. See Section 13.0.1. No item is optional in the interest of moving faster. |
| **Pilot hardening window** | Phase B. The deliberate runway between offsite end and first advisor onboarding where the gap between demo-grade and advisor-usable gets closed. |
| **Pilot-mode disclaimer** | Visible UI text on every recommendation screen during pilot, making clear that output is informational and requires advisor judgment, not standalone advice. |
| **Hero / synthetic backup persona** | Sandra & Mike Chen. Synthetic. Used as the primary safe persona for the Wednesday Som demo, and as a stable test fixture throughout Phase B/C with no real-PII routing dependencies. |
| **Real-derived persona** | A persona built from real Steadyhand client documents, pseudonymized at the Layer 2→3 boundary. Used to validate extraction depth and (in Phase C) for actual pilot advisor work. Distinct from synthetic personas. |
| **Kill-switch** | A single config flag (`pilot_engine_enabled=False`) that disables engine output endpoints platform-wide. Tested before Phase B exit. Used without ceremony if needed. |
| **Goal × account optimization unit** | The unit on which the engine optimizes — each `GoalAccountLink` runs through its own optimization, then per-link blends roll up to the account level. See Part 4.3a. |
| **Snap-to-grid (risk)** | The output of the risk composite is rounded to the nearest 5-point step (1, 2, 3, 4, or 5), each mapped to a specific optimizer percentile (5/15/25/35/45). See Part 4.2. |
| **5/15/25/35/45 mapping** | The optimizer percentiles corresponding to the 5-point risk scale. Cautious=5th, growth-oriented=45th. Range is intentionally below the median to prevent extreme allocations. |
| **Three-component risk exposure** | The household component, goal component, and combined score — all surfaced to the advisor in the UI rather than hidden behind a single "your risk score is X." See Part 4.2. |
| **Three-tab view** | Household / Account / Goal toggle on the dashboard, each viewable by funds or look-through to asset classes; pivot-table principle ensures every tab reconciles to the same total. See Part 8.7. |
| **Click-through workflow** | The structured 7-step interaction for setting an account's portfolio: account → goals served → proportions → per-link recommendations → consolidated account view → fund-of-funds collapse if applicable → client consent. See Part 8.8. |
| **Fund-of-funds collapse** | When a per-account roll-up closely matches an existing whole-portfolio fund (Founders, Builders, etc.), the engine recommends executing via that fund-of-funds for tax efficiency. Same composition, fewer trade events. See Part 4.3b. |
| **Fan-chart longitudinal plotting** | The fan locks at t=0 when the portfolio is set; actual portfolio value is plotted over time within the fan; breach of the bottom of the fan is a Stage-6 conversation trigger. See Part 8.9. |
| **Tier 1 / Tier 2 / Tier 3 (reporting)** | The three sophistication tiers of the dynamic reporting layer: outcome-language only, moderate detail with averages and ranges, full sophistication with percentiles and fan charts. Default inferred from notes; manually toggleable. See Part 8.4. |
| **Pre-recommendation override** | Advisor adjusts an *input* (typically a goal-level risk slider); the engine regenerates a different optimal portfolio. Preferred over post-recommendation override. See Part 7.5. |
| **Post-recommendation override** | Advisor declines to execute the engine's recommendation; the portfolio remains unchanged but a mandatory note explaining why is captured. See Part 7.5. |
| **CMA admin layer** | The admin-only UI for editing capital market assumptions and viewing the efficient frontier. Restricted to designated administrators (the Macro Insight Layer). See Part 4.7. |
| **Macro Insight Layer (CMA admin)** | The CIO/strategist function — a small group with the CMA Admin role per Part 9.2 RBAC. Edits are audited. |
| **Tax-drag table** | Per-fund (or per-asset-class within fund) drag factors, applied to expected return only when the fund sits in a taxable account. Default 0 = feature disabled. See Part 4.5. |
| **External-holdings dampener** | Optional input that reduces the household risk score when external (non-Purpose) holdings are disclosed and skew higher-risk. Simple modifier, not full simulation. See Part 4.6a. |
| **The "false euphoria" risk** | Fraser's Day 2 framing: the offsite team feels closer to done than it is — *"the school play is three weeks away and like, guys, we're ready. I don't know my lines."* The Phase A → Phase B transition exists to correct for this. |
| **`engine_ready`** | Derived flag on the reviewed client state. True when all required fields are populated, all flagged conflicts are resolved, and all required unknowns are addressed. Required for engine output, but not sufficient for committing reviewed state to client tables (which also requires section approval). See Part 11.5.1. |
| **Section approval** | Per-section status (Household / People / Accounts / Goals / Mapping / Risk) on the reviewed state. `engine_ready + all required sections approved` is the gate to committing reviewed state into the client tables. |
| **Defense-in-depth privacy regime** | The privacy approach actually implemented (Part 11.8.3): authenticated ingress + Bedrock ca-central-1 fail-closed routing + transient raw text + structured-only persistence + redacted evidence quotes + hashed sensitive identifiers + immutable audit + RBAC + bounded population. *Replaces* the boundary-pseudonymization approach earlier specified but not implemented. |
| **Boundary pseudonymization (retired)** | The v2.1–v2.3 design where real names would be replaced with pseudonyms before Bedrock saw the text. Not implemented; superseded by defense-in-depth (Part 11.8.3). The substitution is acknowledged so no one operates from a false assumption that pre-LLM redaction exists. |
| **Structured-only persistence** | After extraction, only structured facts, run metadata, and minimally-redacted evidence quotes are persisted. The full raw extracted text is transient. Sensitive identifiers are stored as hash + redacted display, not plaintext. |
| **Hashed sensitive identifier** | High-sensitivity identifier (SIN, account number) stored as a hash plus a redacted display string; plaintext does not enter the persisted DB. |
| **Workspace timeline sanitization** | The audit-visible workspace timeline serializer redacts sensitive before/after values for UI consumers. The audit row itself preserves the full immutable record. |
| **`MP20_SECURE_DATA_ROOT`** | Environment variable that must point to a directory outside the repository where real-PII upload artifacts land. Hard-fail if missing or repo-local. |
| **`MP20_ENGINE_ENABLED`** | Kill-switch environment variable. When false, blocks portfolio generation while leaving intake and review available. Toggling generates an audit event. |
| **`data_origin` flag** | Per-persona attribute (`synthetic` or `real_derived`) routing LLM calls — synthetic to Anthropic API direct or Bedrock per available config; real-derived to Bedrock ca-central-1 only. Misconfiguration is a deployment-blocker check. |
| **Advisor team scope** | RBAC model where advisors share a single team scope for clients and review workspaces. Financial analysts are denied real-client PII surfaces. Implemented in Phase A. |
| **Link-or-create commit** | The reviewed-state commit pattern: either link to an existing household (matching is advisory; commit can pick or override) or create a new household. The internal generated household ID is the unique key; matching is suggestion-grade. |
| **Goal shape** | The category of a goal that drives its duration formula: `lump_sum`, `retirement_estate`, `retirement_income`, or `other`. See Part 4.3d. |
| **Goal duration framework** | Fraser's three-pattern framework for computing optimization time horizon from goal shape: lump-sum = years until needed; retirement estate = years to retirement + full retirement years; retirement income = years to retirement + half of retirement years. See Part 4.3d. |
| **Confidence indicator (risk)** | A 0.0–1.0 value attached to risk scores reflecting evidence strength. Below threshold (default 0.7), the system flags `needs_advisor_input`. Modeled on the Ike agent pattern. See Part 6.5.1. |
| **CAT** | External integration: trade execution and account-value source. Mocked for MVP per Day 3. Real account values trump document-derived values in reconciliation. |
| **Resource** | External integration: Steadyhand CRM. Mocked for MVP per Day 3. CRM-resident facts trump note-derived facts. |
| **Source-priority hierarchy** | Reconciliation rule: system-of-record facts (CAT, Resource) > structured documents (KYC, statements) > note-derived facts. Cross-class mismatches resolve silently to the higher-priority source, not as conflicts. See Part 11.4. |
| **"Needs attention" lexical split** | UI rule separating *"Review needed"* alerts (data-ingestion: conflicts, missing fields, low confidence) from *"Action recommended"* alerts (portfolio/planning: drift, off-track goals, life events). Different urgency, different workflow. See Part 8.6a. |
| **Goal-based lens** | MP2.0's strategic positioning per Part 1.7 — the system is a goal-based overlay on top of foundational platforms (Advisor Center), not a parallel rebuild. The differentiator is the goal × account cross-reference and portfolio construction engine. |
| **Senior Steadyhand stakeholder demo** | Target ~1–2 weeks after offsite. Distinct from the Wednesday Som demo (executive sponsor) and the Mon/Tue IS validation (working session). Audience is broader Steadyhand leadership; runs on Phase B build. See Part 13.1. |
| **Building-block fund** | See strategic glossary entry (16.1) — the standardized constituent of personalized blends. Code-side identifiers (`Sleeve` Pydantic class, `sleeves.py`) are intentionally left under their legacy names per Part 10 to avoid churn; the *concept* is "building-block fund." |
| **Whole-portfolio fund** | A multi-mandate fund-of-funds (Founders, Builders, PACF, etc.) that may serve as a fund-of-funds collapse target when an optimization output closely matches its composition. Distinct from a building-block fund. See Part 2.2 and Part 4.3b. |
| **Re-goaling / goal realignment** | The conceptual relabel-or-reapportion of dollars between goals within an account. **Not money movement.** Vocabulary discipline locked: never use "reallocation," "transfer," or "move money" for this operation. Triggers a new portfolio recommendation because the account's blended risk/horizon profile changes. See Part 6.3a. |
| **Stale portfolio** | A previously-generated portfolio whose underlying CMA snapshot is no longer current. Marked `is_stale = true` rather than auto-regenerated; advisor must click "regenerate" to compute against the published snapshot. See Part 4.7.3. |
| **Draft / publish CMA workflow** | The state model for CMA edits: create draft → edit → save draft → publish. Drafts are private to the editing Financial Analyst; publish atomically writes a `CMASnapshot`, triggers audit, triggers propagation. See Part 4.7.1. |
| **"Express as moves"** | UI control on the comparison view that generates the specific trade list (sells/buys with quantities) required to transition current → ideal allocation. Required because client consent is captured at the trade level, not the end-state level. See Part 8.10. |
| **Householding consent** | Signed consent from each household member required before the system rolls up their accounts under a single household view. Privacy among couples is real; consent can be withdrawn. See Part 6.1. |
| **Financial Analyst (CMA editor)** | The role with create/edit/save-draft/publish access to CMAs and view access to the efficient frontier. Distinct from the financial-analyst role's denial of real-client PII surfaces — same role name, two scopes. Day 3 afternoon §1.1. |
| **Trailing returns vs. portfolio returns** | "Portfolio returns" is the demo-friendly term per Day 3 afternoon §2.2; "trailing returns" is more technical. Trailing returns are not strictly required for MP2.0's forward-looking construction but matter for advisor / client conversations. Personalized after-fee returns are deferred (Steadyhand fee-reduction program makes per-client computation complex). |
| **Risk tolerance vs. riskiness** | Lexical discipline per Day 3 afternoon §2.3 — *"risk tolerance"* applies to a person/household; *"riskiness"* applies to a position/portfolio. Both terms used in canon with this discipline. See Part 4.2. |
| **Time horizon is not a risk-score component** | Anti-double-counting rule per Day 3 afternoon §5.4. Time horizon and risk score are orthogonal optimizer inputs. Including time horizon in the risk score would push the blend conservative twice for the same maturity. See Part 4.2. |

---

## PART 17 — REFERENCE MATERIALS

Source documents available in the project:

| Document | Use |
|----------|-----|
| **The Purpose Memo — MP2.0 (Sep 2024)** | Fraser's foundational memo. Opinionated; thinking has evolved. |
| **MP2.0 Offsite prep deck** | Logistics, objectives, prep |
| **MP2.0 MAT Invitation Extract** | Original mandate and design principles |
| **Day 1 morning + afternoon transcripts and AI notes** | Source of most of the conceptual content here |
| **Summary of Som "Future of Wealth" interview (Aug 2024)** | Strategic thesis |
| **Client Data Framework** | Steadyhand intake/review templates and FP Canada mapping |
| **Client Nudges — MP2.0** | Behavioral nudge concepts |
| **Birth-of-Child / Retirement / Divorce / Job-Loss / Inheritance / End-of-Life / House-Purchase / Post-Secondary checklists** | Stage-6 loop trigger scenarios |
| **Sample financial plans** (Burnham, Kneteman, Moore, Schlotfeldt, Lee/Nigel + Feb 2025 plan) | Real-world plan structure for engine input modeling |
| **Investment review (Terry, 2025)** | Sample portfolio review |
| **Hackathon output (Q4)** | https://purpose-portfolio2-0.lovable.app/ — earlier prototype |
| **Vanguard Personal Advisor** | US comparable |
| **Mermaid project flowcharts** | Option A (sleeves): https://mermaid.ai/d/4814577d-5367-4dde-9ef6-3f01143fe630 ; Option B: https://mermaid.ai/d/9bfdc432-ff41-4a3d-9aa0-8186e7842c07 |

---

## PART 18 — DOCUMENT VERSIONING

This file should be revised whenever a material decision changes. Track changes inline; archive prior versions.

- **v2.8 (Apr 30, 2026)** — **Authorization-basis clarification.** Saranyaraj clarified on 2026-04-30 that real Steadyhand client PII is authorized for limited-beta, local-production-like operation (current scope: two roles — `advisor` and `financial_analyst` per `web/api/access.py` — and the current local-production-like deployment); use is not blocked. Surgical updates to §11.8.1 (replaced the "OPEN — must be resolved retrospectively" framing and the "stop adding new real-client material" hard-stop with an explicit "LOCKED for limited-beta scope" lock and a documented operating envelope), §15.0 priority #1 (status updated to "RESOLVED for limited-beta scope; broader rollout requires Lori + Amitha review; revisit 2026-05-21"), and §15.1 OQ#24 (same status update). The §11.8.3 defense-in-depth regime stands unchanged as the operational privacy floor; boundary pseudonymization stays retired (former Q26). Other places that reference the authorization basis in supporting context (Part 1.6, §11.8 preamble, §11.8.7, §13.0.1, §13.3, Part 14 items 8–9) are intentionally left as-is — they remain accurate as supporting context and rewriting them risks new internal inconsistencies for marginal gain. Working revisit date: 2026-05-21.

- **v2.7 (Apr 30, 2026)** — **Internal consistency pass.** No new external session input; this revision is a self-review against v2.6 finding and fixing internal inconsistencies that the rapid v2.5 → v2.6 cadence had introduced. **Sleeves → funds rename completed cleanly:** the v2.6 rename had left ~20 leftover references that contradicted the new vocabulary. Surgical fixes to Part 1 TOC entry, Part 1.3 Harness IC reference, Part 3 customer journey Stage 3 row, Part 4.1 efficient frontier core math, Part 4.3b fund-of-funds collapse rule, Part 4.4 cash building-block header, Part 4.6 v2+ gaps, Part 6.4 Account schema comment, Part 9.4.6 audit-log line, Part 12.1 engine I/O contract prose (code identifiers `Sleeve` Pydantic class and `sleeves.py` deliberately kept under their legacy names per a new explanatory note in Part 10 — code identifiers don't need to track product vocabulary changes; the canon now says so), Part 12.2 schema list, Part 12.4 cache invalidation, Part 13.2 Day 1 morning + Day 2 morning build sequence, open questions #4 / #5 / #15 / #17. **Strategic glossary reconciled with engineering glossary:** the strategic glossary at 16.1 still defined "Sleeve fund / Atom / Blend / Blend ratios / Macro Insight Layer / Paint mixing / Whole-portfolio fund" using sleeve vocabulary, while the engineering glossary at 16.2 had already been updated — the two glossaries were actively contradicting each other (the most serious internal inconsistency). The strategic glossary now uses building-block-fund vocabulary throughout; the engineering glossary's redundant "Building-block fund" entry was simplified to a cross-reference. **Phase 0 / hardcoded-admin residue cleared:** v2.4 had retired Phase 0 entirely, but the Day 1 morning build sequence still said "Auth Phase 1 (single hardcoded admin)" and the compression-risks list still flagged "Auth Phase 0 → Phase 1 transition skipped" as a risk. Both fixed. **Pseudonymization residue cleared from Day 3 (Wednesday) Som demo close-out:** v2.4 retired boundary pseudonymization in favor of defense-in-depth, but the demo close-out line still said "real-client example, pseudonymized." Replaced with the actual Part 11.8.7 audience-composition rule. **Authorization-basis and Bedrock compression-risk items updated** to reflect post-Day-2 reality (real PII has been flowing since Day 2 evening; retrospective written confirmation needed) rather than the pre-offsite framing. **Added one structural improvement: Part 15.0 "Top priorities right now"** — a 7-item shortlist surfacing the highest-leverage items from the 68-question table (written authorization basis #24, Bedrock formal confirmation #25, correlation matrix integration #56, engine output contract migration #47, CAT/Resource API specs #51-52, default goal regulator wording #61, 3-month roadmap #64). The shortlist rotates as items resolve; the full table is preserved unchanged at 15.1 for audit-trail continuity.

- **v2.6 (Apr 29, 2026)** — **Day 3 afternoon lock-ins integrated.** Major terminology change: **"sleeves" retired in favor of "funds"** (Day 3 afternoon §2.1) — Part 2.2 (architecture), Part 5 (was "Sleeve Universe", now "Fund Universe"), Part 4.7, and engineering-glossary references updated. The conceptual distinction between *building-block funds* (the standardized constituents) and *whole-portfolio funds* (Founders, Builders, fund-of-funds collapse targets) is preserved with new vocabulary; the paint-mixing analogy stays as a teaching device. Added 5 architectural sharpenings to Part 4.7 CMA admin section: draft/publish state model (4.7.1), Financial Analyst as the authorized CMA editor role, **stale-portfolio state pattern** (`is_stale=true`, advisor must click "regenerate" — does not auto-regenerate; per Day 3 afternoon §1.3), chart visualization in v1 CMA UI, and a new Part 4.7.4 establishing math validation against Fraser's reference model as a Phase B blocker (correlation matrix integration is its prerequisite). Sharpened Part 4.2 risk modeling with three Day 3 afternoon refinements: lexical distinction between household-level "risk tolerance" and goal-level "riskiness" (§2.3); goal-level risk now includes portion-of-AUM allocated to the goal (§5.4); explicit lock that **time horizon is NOT a component of the risk score** (§5.4) — anti-double-counting, since time horizon is a separate orthogonal optimizer input via the duration framework (Part 4.3d). Softened the v2.5 "low/med/high never to clients" rule to reflect Day 3 afternoon's open discussion: both internal-numeric and named-band vocabularies acceptable; pilot UI defaults to descriptors but the discipline is open (#65). Added Part 6.1 householding consent fields and consent-form requirement (Day 3 afternoon §7.2). Added Part 6.3a on **re-goaling as conceptual overlay** — vocabulary discipline locked: use "re-goaling"/"goal realignment", **never** "reallocation"/"transfer"/"move money". Added Part 6.3b on default goal classification when client goals are undefined: emergency fund + retirement split per Fraser; "savings" wording avoided per regulator constraint. Re-anchored Part 6.7 onboarding around document-drop primary, structured questionnaire fallback (Day 3 afternoon §4.1) — reflects real advisor workflow where conversations precede documents. Sharpened Part 4.6a external-holdings methodology: statement upload (preferred) → conversational fallback → balanced-allocation default; Morningstar drives Steadyhand-internal breakdowns; AI auto-classification of external statements is v2+ vision. Sharpened Part 8.7 with Steadyhand-internal vs. external holdings detail rules: full detail for Steadyhand, asset-class-only for external, click-to-reveal pattern for external (privacy when advisor turns screen toward client). Added Part 8.8 current-vs-ideal comparison rules: existing clients see comparison; new clients with cash skip comparison. Refined Part 8.9 fan chart: household-level current-vs-optimized overlay; interactive hover at P5/25/50/75/95; **no household-level time horizon hard-anchor** (different goals have different horizons); cap at life expectancy; Tier 1/2/3 sophistication mapping (101 = median only / 201 = median + outer bands / 301 = full detail). Added new Part 8.10 **"Express as moves"** — trade-level rebalancing UX required because client consent must be captured at the trade level (Part 7.5a), not the end-state level. Added Part 7.5a: compliance burden raises rebalancing trigger threshold; fee disclosure + fund fact sheet on every new fund purchase; future-state full-discretionary option flagged as v2+. Added explicit advisor confirmation requirement and three-mockup-state framing (clean / moderate conflicts / heavy conflicts) to Part 11.5 data review screen. Updated Part 13: demo format = guided walkthrough (not hands-on test) per §9.1; demo persona refined to RSP+FHBP dual-purpose (most common Steadyhand scenario per §5.1). Added correlation-matrix integration, math validation, and frontend-backend integration as Phase B exit criteria (Part 13.0.1). Locked integration direction in Part 13.4: **Raj's backend plugs into Nafal's frontend**, not vice versa (§3). Updated Part 13.4 task allocation per Day 3 afternoon assignments. Added 10 new open questions (#59–68) and 12 new vocabulary terms.

- **v2.5 (Apr 29, 2026)** — **Day 3 morning lock-ins integrated.** Added Part 1.7 on platform alignment: MP2.0 is the goal-based lens layered on the Advisor Center foundation (which the Purpose Engineering Director is rebuilding in React), not a parallel rebuild. Added Part 4.3d on goal duration computation per Fraser's framework — three patterns (lump-sum / retirement-estate / retirement-income), with concrete formulas and the bond-duration analogy for retirement income. Added `goal_shape` to Goal entity (Part 6.3); duration is derived per optimization run, not stored. Sharpened Part 4.7 CMA admin section with operational detail: monthly-or-event update cadence, propagation across all portfolios with drift detection, advisor-routed alerts ("17 accounts >5% off optimal"), Steadyhand CIO decision authority, no auto-rebalance, correlation matrices stored as decomposed linear arrays. Added confidence indicators to risk schemas (Part 6.5.1): 0.0–1.0 confidence on household and goal scores, with default 0.7 threshold below which the system flags `needs_advisor_input`; rationale field required for compliance. Added Part 8.6a on the "needs attention" lexical split — *Review needed* (data ingestion) vs. *Action recommended* (portfolio/planning); different urgency, different workflow. Sharpened Part 8.7 with Day 3 visualization details: vertical-slice accounts with color-coded goal allocations consistently used across the UI; hover for detail; bidirectional pivot. Added named external integrations to Part 9.4.3: **CAT** (trade execution / account values) and **Resource** (Steadyhand CRM); both mocked for MVP, both with adapter interfaces defined now. Added source-priority hierarchy to Part 11.4: system-of-record > structured documents > note-derived facts; cross-class mismatches resolve silently rather than surfacing as conflicts. Sharpened Phase A demo prioritization in Part 13.2: engine is the must-have, ingestion can be mocked, reporting can be cut to essentials — *"if we nail the ingestion but haven't done how it constructs it, there's nothing to demo."* Refined Part 13.1 to distinguish three demo events: Wednesday Som demo, Mon/Tue IS validation, and senior Steadyhand stakeholder demo (target 1–2 weeks). Updated Part 13.4 task allocation per Day 3 morning. Added 9 new open questions and 9 new vocabulary terms covering CAT, Resource, goal shape, duration framework, confidence indicators, source-priority, "needs attention" split, goal-based lens, senior stakeholder demo. The boundary-pseudonymization correction from v2.4 stands; Day 3 morning §8 recap referenced older "demo-grade" language but v2.4's production-grade reframe is preserved deliberately.

- **v2.4 (Apr 29, 2026)** — **Reframed as production-grade software with limited users; reconciled canon with implementation reality.** The "MVP / demo-grade scaffold" framing in v2.2/2.3 produced the wrong mental model — the implementation has been production-grade from day one because real PII has been flowing since Day 2 evening. Part 1.6 retires the "demo-grade" language; Phase A is now production-grade for internal use, with Phase B layering on additional controls (MFA, lockout, password reset, audit browser, CMA admin boundary) for advisor-pilot use. **Major honesty correction in Part 11.8.3:** the boundary-pseudonymization regime specified in v2.1–v2.3 was not implemented; the actual privacy regime is defense-in-depth (authenticated ingress + Bedrock ca-central-1 fail-closed + transient raw text + structured-only persistence + redacted evidence + hashed sensitive identifiers + immutable audit + RBAC + bounded population). Real names do transit to Bedrock; the protection is the trust boundary (Purpose AWS, Canadian-resident, Bedrock service-level controls). The substitution is documented so no one operates from a false assumption. Part 11.8.1 updated to reflect that real PII has already been in use since Day 2 (under implicit "internal use" basis); retrospective written confirmation from Amitha is now a Phase B exit blocker. Auth phasing (Part 9.2) restructured: Phase 0 (hardcoded admin) retired; Phase A current state is authenticated DRF + advisor team scope + financial-analyst PII denial + kill-switch (production-grade for internal team). Phase B adds MFA / lockout / password reset / session timeout / audit browser UI / CMA admin boundary. Phase B exit criteria (Part 13.0.1) tightened to require retrospective Amitha sign-off, audit browser UI shipped, CMA admin boundary live, engine output contract migrated to per-link. Added `engine_ready` gate concept (Part 11.5.1) — a derived flag on reviewed state, separate from section approval; together they gate committing reviewed state into client tables. Updated Part 9.4.6 audit log with the additional events the implementation captures (section approval, kill-switch toggles, disposal, edit hashes); audit browser UI moves from "post-MVP" to Phase B exit criterion. Part 14 (IT confirmations) sharpened: Bedrock ca-central-1 partially resolved (in active use, formal IT confirmation still owed); two new REAL-PII BLOCKER items added covering Amitha's defense-in-depth review. Open questions: 26 retired (boundary pseudonymization), 25 / 28 / 43 partially resolved, 6 new added covering Phase B engineering migrations (engine output, risk scale code, target_amount optionality, vocabulary, CI E2E, CI PII scanners). Added 12 new vocabulary terms.

- **v2.3 (Apr 28, 2026)** — **Day 2 afternoon design lock-ins integrated.** Major architectural decisions captured: optimization unit is goal × account cross (Part 4.3a), 5-point risk scale mapped to 5/15/25/35/45 percentile range with snap-to-grid output (Part 4.2/4.3), three-component risk exposure surfaced to advisor (Part 4.2), tax-drag schema with per-fund/per-asset-class factors (Part 4.5), recommended portfolio always sits on the frontier with fund-of-funds collapse for execution (Part 4.3b), future-dollar targets are secondary input only (Part 4.3c), external holdings as risk-tolerance dampener moves in-scope (Part 4.6a), CMA admin layer with restricted access sharpens the Macro Insight Layer (Part 4.7). Added two major new UX sections: three-tab household/account/goal view (Part 8.7) and click-through portfolio assignment workflow (Part 8.8) — the "single biggest wow" of the session. Added longitudinal fan chart mechanic (Part 8.9). Restructured Part 8.4 as three sophistication tiers (Tier 1/2/3) with behavioral bucketing composing within tiers. Added concrete sentence templates for "why this portfolio?" (Part 8.5). Added pre-recommendation vs. post-recommendation override patterns (Part 7.5). Added CMA Admin role to RBAC (Part 9.2). Schedule corrected: **Wednesday Som demo** (not Friday); IS team validation Mon/Tue following week (Saranyaraj hackathon partial-availability called out). Refactored Part 13 build sequence to add Day 3 (Wednesday) close-out and revise Phase B sketch. Replaced 8-segment Sandra & Mike storyboard with Day-2 demo flow (drop notes → ingestion → household/account/goal drill → portfolio recommendation → "am I going to be okay?" output). Updated EngineOutput contract to be per-link first (Part 12.1). Vocabulary update: client-facing copy uses cautious / balanced / growth-oriented, not low/medium/high (Day 2 §6.2). Resolved 5 open questions (composite risk, goal-questionnaire, external assets, frontend assignment, demo-grade-vs-pilot-grade); added 8 new ones from Day 2 (recursion, real/nominal, client-vs-advisor view, external disclosure, CMA admin permissions, override UX, fund-of-funds match threshold, user-testing proxy). Added 17 new vocabulary terms covering Day 2 design.

- **v2.2 (Apr 2026)** — **Reframed deliverable from "demo" to "MVP for advisor pilot."** 3–5 Steadyhand Investment Specialists will use the system with real clients in a controlled pilot starting after the offsite. Added Part 1.6 explicitly redefining the deliverable and the demo-vs-MVP bar table. Restructured Part 13 as three phases: Phase A (offsite scaffold, 2 days, demo-grade foundation), Phase B (pilot hardening window, ~2 weeks, advisor-usable), Phase C (pilot launch + iteration, 3–5 advisors). Added Part 13.0.1 with explicit Phase B exit criteria gating advisor onboarding. Added Part 13.0.2 with pilot operations (feedback channel, office hours, weekly retros, bad-output escalation, pilot-mode disclaimer, IS training, kill-switch). Added Part 13.0.3 with pilot success metrics. Tightened Part 9.2 auth: Phase 0 (hardcoded admin, offsite only) → Phase 1 (per-advisor accounts with MFA, password reset, session timeout, lockout) → Phase 2 → Phase 3. Updated Part 11.8.2 data minimization to scale across phases (1–2 personas Phase A → ~15–50 Phase C). Updated Part 11.8.7 from "demo audience" to pilot-audience framing with RBAC enforcement. Updated Part 12.4 from demo-posture to pilot-posture. Updated Part 13.7 out-of-scope from demo bar to pilot bar. Added 4 pilot-related compression risks (retention, support load, demo-grade-mistaken-for-pilot-grade, bad-output incident). Added 7 new open questions covering pilot logistics. Added 6 new vocabulary terms.

- **v2.1 (Apr 2026)** — **Real client PII brought in scope.** Added Part 11.8 governing operational use of real Steadyhand client PII (authorization basis, data minimization, pseudonymization at Layer 2→3 boundary, LLM provider posture, machine posture, retention/disposal, demo audience considerations, incident response). Tightened Part 9.3 data classification defaults to assume client-PII tier as floor. Updated Part 11 preamble flagging Section 11.8 as hard prerequisite requiring Lori + Amitha sign-off. Sharpened Part 11.7 on git/repo posture with mandatory pre-commit scrub-pass hook. Updated Part 13.6 to clarify hero demo persona is synthetic; real-derived personas exercise extraction depth. Sharpened Part 13.7 demo PII rule. Added 4 PII-related compression risks to Part 13.3. Tagged 3 items in Part 14 (IT confirmations) as REAL-PII BLOCKER — Bedrock enablement, data classification, authorization basis. Added open questions #24–29 covering PII workstream. Added 5 new vocabulary terms.

- **v2.0 (Apr 2026)** — Merged seed context + engineering addendum into single working canon. Replaced original Part 9 (Technical Architecture) with full engineering content. Added engineering parts: Stack/Architecture/Infrastructure (Part 9), Repo Layout (Part 10), Extraction Layer (Part 11), Engine I/O Contract (Part 12). Merged build sequence and demo storyboard into Part 13. Unified glossaries (Part 16). Unified open-questions table (Part 15). Applied LOCKED/DEFAULT/OPEN tagging consistently throughout. Tightened Day 1 morning into critical-path + deferrable lists. Named operational dependency on Lori as a compression risk. Promoted CMA placeholder issue (Part 5.4) to its own section. Added live-vs-cached demo posture (Part 12.4). Added `derivation_method` field to `Fact[T]` schema. Added explicit IT-blocking fallback (Part 14 preamble). Resolved several items from prior open-questions list.

- **v1.0 (Apr 2026)** — Initial seed context. Architecture confirmed Option C (sleeve-blend hybrid). Method 1 (percentile) selected for v1 risk optimization. Steadyhand confirmed as v1 launch context. Six pure Steadyhand sleeves selected as initial universe. MVP demo target: Stages 1→2→3→5.

- **Engineering Addendum v1.0 (Apr 2026)** — Now superseded by this merged document. Stack locked: Django+DRF / React+Vite / Postgres+pgvector / AWS ECS-on-EC2 ca-central-1 / Bedrock for prod LLM / OpenTelemetry+Elastic. Five-layer extraction pipeline architected with temporal Fact[T] schema. Auth phasing locked. RBAC scaffolded Phase 1.

---

*This is the working canon. When this document and the codebase disagree, fix the disagreement the same day — by updating one or the other.*
