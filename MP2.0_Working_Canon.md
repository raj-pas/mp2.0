# MP2.0 — Working Canon (v2.3)

**Merged seed context + engineering addendum + real-PII handling + MVP/pilot framing + Day 2 design decisions**
**Compiled:** April 2026, post Day-2 of MAT offsite (architectural lock-ins, three-tab view, risk methodology, tax drag, override patterns, schedule correction)
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
5. Sleeve universe
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
- After Steadyhand, the next deployment is **Harness** (advisor platform, especially retired clients — Harness Investment Committee has confirmed interest, conditional on sleeves being formally launched as funds with a Purpose PM attached). Eventually: 3rd-party IIROC/CIRO advisors, Partnership Program, Link group plans, and DIY.

### 1.6 The deliverable — MVP for advisor pilot, not a demo **[LOCKED]**

> **MP2.0 is a working MVP that 3–5 Steadyhand Investment Specialists will use with real clients in a controlled pilot. It is not a demo.** The Wednesday end-of-day Som demo and the IS team validation sessions the following Mon/Tue are the start of pilot use — not one-time presentations. Everything in this canon should be read with that bar in mind.

This distinction matters because it changes what "done" means at every layer:

| Concern | Demo bar | MVP-for-advisor-pilot bar (the actual bar) |
|---|---|---|
| **Audience posture** | Passive — watching a screen | Active — clicking around, doing their job, exploring edge cases |
| **Path coverage** | Storyboard happy path works | Most reasonable advisor actions produce sensible output or graceful failure |
| **Personas** | One hero persona | Whatever real client files an advisor loads |
| **Auth** | One hardcoded login | Per-advisor accounts, password reset, session timeout, lockout |
| **Output trust** | "Looks impressive" | Every recommendation is clearly marked as pilot output requiring advisor judgment |
| **Failure mode** | Awkward silence in the room | An advisor takes pilot output to a real client conversation |
| **Success metric** | "They liked it" | Advisors keep using it after week one |
| **Feedback loop** | Post-demo survey optional | Structured channel from day one — advisors flag bugs, surface bad output, ask questions |
| **PII volume** | 1–2 validation personas | Real client books, at routine pilot volume |

The **honest implication** is that the offsite 2-day build produces the *foundation*, not the finished MVP. There's a defined window between offsite end and first advisor onboarding (the **pilot hardening window**, see Part 13.0) where the gap between "demo-shaped" and "advisor-usable" gets closed. That window is part of the project, not an afterthought.

Naming this here so that no decision downstream — auth phase, error handling, edge-case coverage, support model — can quietly slip back to demo-grade just because something said "demo" in an earlier draft.

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
         - accounts contain SLEEVES (sleeve funds = the building blocks)
```

**Critical insight from the offsite:** goals and accounts have a **many-to-many** relationship.
- One goal can be funded by money across multiple accounts (retirement spans RRSP + TFSA + non-reg).
- One account can serve multiple goals (a TFSA holding both cabin-purchase money and retirement money).
- The system must support this without forcing 1:1 mapping.

Regulatory reality: at Steadyhand (MFDA), accounts cannot be formally "nicknamed" or labeled with goals. The mapping is a logical/system layer above the regulatory account.

### 2.2 The sleeve-blend architecture (Option C) **[LOCKED]**

**The foundational architectural decision is Option C: the hybrid sleeve-blend model.**

The analogy is **paint mixing** (Fraser's):
- **Sleeves** = building-block funds (the paints). 8–12 sleeves total. Each sleeve has a clear mandate (e.g., "Canadian large-cap equity," "investment-grade bonds," "cash"). Each sleeve is itself a real, papered fund with a Purpose PM attached.
- **Blend ratios** = personalized mix of sleeves driven by the financial plan (the painting). Every household–goal–account combination produces a unique blend.
- **Atoms-and-molecules**: sleeves are molecules; the underlying holdings (individual securities) are the atoms. Clients/advisors operate at the molecule level. The Macro Insight Layer (see 2.3) operates at the atom level inside each sleeve.

Why this architecture:
- Standardized sleeves give us manageability, consistency across client books, and operational tractability (rebalancing 12 sleeves vs. 1,000 unique portfolios).
- Personalized blends give us the planning-driven personalization that defines MP2.0.
- Sleeves earn trust over time because they have track records, mandates, and PMs — they're real funds, not synthetic constructs.

### 2.3 The Macro Insight Layer **[LOCKED]**

The CIO/strategist function does **not** touch individual client portfolios. It updates the **internals of sleeves** (the underlying holdings) based on macro views — duration calls, sector tilts, currency hedging decisions, factor exposures.

This means there are **two independent update cycles**:
1. **Sleeve internals** — driven by the Macro Insight Layer (probably monthly). Affects every client who holds that sleeve.
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
| 3 | **Portfolio Construction** | The MP2.0 engine itself. Sleeve-blend optimization driven by plan. Two independent update cycles (sleeve internals via Macro Insight Layer; blend via plan). | Purpose: "Are sleeves consistent across clients?" Advisor: "Why this blend?" Client: "Why these funds?" |
| 4 | **Automated Execution** | Drift detection, tax-aware rebalancing, custodian API, compliance guardrails. **Phase 2+ — explicitly out of MVP scope.** Should be invisible to the client when it works. | All: invisible until it isn't. |
| 5 | **Outcomes Reporting** | "Am I going to be okay?" reports. Goal progress visualization, plan-vs-actual, market context. AI/LLM-generated meeting prep for advisors. Periodic personalized updates. | Client: "Am I on track?" Advisor: "What do I tell them?" Purpose: regulatory reporting layered on top. |
| 6 | **Continuous Loop** | Event-driven triggers feed back into Stage 2: life changes, market shifts, advisor observations, plan-progress signals. **This is where MP2.0 becomes sticky.** | All: the system gets smarter with every interaction. |

**Phase A demonstration target: Stage 1 → 2 → 3 → 5.** **[LOCKED]** Stage 4 is mocked. Stage 6 is implied via "what happens when X changes" branches in the storyboard.

---

## PART 4 — INVESTMENT THEORY & ENGINE MECHANICS

This is the math the offsite locked in for v1. Like the race-car-engine analogy: it's a working engine for v1. We may swap from "gasoline to diesel" later — but it must run now.

### 4.1 Foundation: efficient frontier optimization **[LOCKED]**

For a given universe of sleeve funds, with each sleeve characterized by:
- Expected return (after-fee, net)
- Volatility (annualized standard deviation)
- A correlation matrix across all sleeves

…we compute the **efficient frontier** — the set of portfolios that maximize expected return for each level of volatility (and equivalently, minimize volatility for each level of expected return).

This is Modern Portfolio Theory, applied at the sleeve level. The frontier is a curve in (volatility, return) space. Any blend of sleeves that lands **on** the curve is optimal in the mean-variance sense; anything below is dominated.

**Key mechanic observed in the offsite:** as we vary correlations between sleeves, the *shape* of the frontier changes meaningfully — strongly negatively-correlated sleeves push the frontier up and to the left (more return for less risk). This is why launching a true **bond-only sleeve** matters: today the Steadyhand bond fund (Income Fund) is 75% bonds / 25% equities, which "couples" the bond axis to the equity axis and limits how far we can extend the frontier.

### 4.2 Risk modeling — composite, 5-point, three components exposed **[LOCKED — Day 2]**

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

**The risk input is composed of three named components, all exposed to the advisor:**

1. **Household risk rating** — derived from the holistic view of the household: income, net worth, investment knowledge, behavioral signals (loss aversion, follow-through, sentiment under volatility), tax sensitivity, attitude to debt.
2. **Goal-level risk rating** — specific to *this* goal: how essential is it (need / want / wish), what's the time horizon, how much variability can the client tolerate on this specific outcome.
3. **Combined / "goal-adjusted" risk** — what the optimizer actually uses.

**Showing all three avoids the black-box feel** (Day 2). An info icon / drill-down is preferred over hiding. The advisor chooses whether to walk the client through it.

Both component scores can start very simple: the goal-level score can be **a single 4- or 5-point question per goal** ("If you missed this target by 30%, what would that mean to you?"). The household-level can be a 3-question composite + behavioral data from notes.

**Vocabulary** **[LOCKED — Day 2 §6.2]**: client-facing copy uses *cautious / balanced / growth-oriented* (and intermediates), not *low / medium / high*. The technical labels are held internally for the engine and for compliance mapping; the friendly descriptors surface in any client-visible copy. *"Low / medium / high" reads as a verdict; advisors and clients should not see those words in the client experience layer.*

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
- Optimize as usual; produce a sleeve-level blend
- Compare blend composition against existing whole-portfolio funds (PACF, PABF, PAGF, Founders, Builders, etc.)
- Where the optimization output closely matches an existing fund-of-funds, **recommend executing via that fund-of-funds** for tax efficiency (no client-level rebalancing on the underlying)
- Where it doesn't, recommend the sleeve-level blend directly

**Same composition, fewer trade events.** This is also how Steadyhand existing portfolios (the "1.0" models) coexist with MP2.0 outputs — when MP2.0 lands on the same allocation as an existing model, it recommends the existing model.

### 4.3c Future-dollar targets are secondary input **[LOCKED — Day 2 §3.3]**

Leading with future-dollar projections is dangerous: clients latch onto the number, real-vs-nominal confusion is common, and naming a specific future amount raises the legal bar. The system's primary framing is risk × time-horizon, not target-dollar.

Future targets are **optional secondary input**, used when the client volunteers a specific number. They enable goal-attainment probability framing (Method 2 in 4.3) as a tab, not the primary view. The core flow does not require a dollar target.

This is also why Lori's caution prevailed at Day 2: the candidate one-sentence justification (Part 8.5) leads with "this allocation gives you the maximum portfolio value at a level of confidence aligned to your risk tolerance" — no future number unless one is explicitly provided.

### 4.4 Glide path & the cash sleeve as risk-reducer **[LOCKED]**

As a goal nears its target date, the optimal blend should glide toward lower-volatility sleeves — and ultimately toward **cash**. The cash sleeve (currently approximated by Steadyhand Savings/MMF, with ~2.1% expected return and ~0.5% modeled volatility) functions as the "risk-free corner" of the frontier.

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

- **Currency / hedging decisions** (hedge ratios, FX overlays). Today buried inside sleeve internals.
- **Factor tilts** (value, growth, momentum, quality). Today emergent from sleeve mandates. *Behavioral risk* of factor concentration (clients bailing in a crisis on funds they don't emotionally connect with) is real and material — handled in v1 via CMA tuning that prevents extreme concentrations (Part 4.7) and via investment-specialist discretion, not by adding factor-tilt math to the optimizer (Day 2 §6.3).
- **Geographic / sector concentration look-through.** A future feature: re-aggregate the underlying atoms across all sleeves the blend holds, and flag concentration risks.
- **Full external-portfolio simulation.** v1 treats external holdings as a **simple risk-tolerance dampener** (Part 4.6a), not a full position model.

The offsite consensus: build v1 with these gaps explicit, then evaluate which to close based on what we observe with real personas.

### 4.6a External holdings as household-risk dampener **[LOCKED — Day 2 §6.4]**

External holdings (other-firm investments, real estate, business equity, private investments) are **optional input** in v1 and act as a simple **dampener** on the household risk score used for Purpose accounts:

- Higher external risk or larger external holdings push the household risk score *down* (more conservative) for the Purpose-managed portion
- This is a single-number adjustment, not a full external-portfolio simulation
- Disclosure is optional; the system needs to articulate the value to the client of disclosing (Day 2 §6.4 — open work)
- When external holdings aren't disclosed, the dampener is simply absent (no penalty, no warning)

The math is intentionally simple. Full external-portfolio modeling (joint optimization across Purpose + external assets) is v2+.

### 4.7 Capital market assumptions are an admin lever **[LOCKED — Day 2 §4]**

Purpose owns the CMA inputs (expected return, std dev, correlation matrix per sleeve, asset-class composition per fund, per-asset-class tax drag). These are not user-editable parameters; they are the firm's investment views.

**Important guardrail:** the optimizer will not concentrate to a single fund **as long as no fund is Pareto-dominant and all pairwise correlations are sub-1**. Tuning CMAs is therefore a legitimate guardrail to keep recommendations within the range of "fundable" allocations the firm is comfortable with. This is a feature, not a bug — extreme concentrations (e.g., 100% global small-cap equity) are prevented by the same CMA inputs that drive optimization.

**The CMA editor and the efficient frontier visualization are admin-only.** They live in the application but behind a permissions gate:
- Advisors do not see the frontier, do not edit CMAs
- Designated administrators (initially: the CIO/strategist function — the "Macro Insight Layer" of Part 2.3) edit CMAs and view the frontier
- All CMA edits write to the audit log with operator + timestamp + before/after values
- This is the first real distinction in the permissions model beyond admin/non-admin (cf. Part 9.2 RBAC scaffolding)

This sharpens what was previously the abstract "Macro Insight Layer" of Part 2.3 into something with a real UI surface and a real permission boundary.

---

## PART 5 — SLEEVE UNIVERSE

### 5.1 Initial sleeve universe (Steadyhand v1) **[LOCKED]**

The Steadyhand fund lineup is the v1 sleeve universe. Eight funds total; six are pure building blocks, two are funds-of-funds.

| Sleeve | Mandate | Role | Notes |
|--------|---------|------|-------|
| **Equity Fund** (a.k.a. Builders Fund) | ~160 companies, Canadian + global, mid/large cap, style-agnostic | Equity core | Primary equity sleeve |
| **Global Equity Fund** | International equities | Global diversification | Underperformed historically — flagged for review |
| **Small-Cap Equity Fund** (×2: Canadian + Global) | Small-cap exposure | Equity satellite | Two sub-sleeves |
| **Income Fund** | 75% Canadian bonds, 25% Canadian equities | Fixed income (impure) | **Identified as a constraint** — we need a true bond-only sleeve |
| **Cash / Savings (MMF)** | Money market | Risk-free corner of the frontier | Used for glide-path-to-goal |
| **Founders Fund** | Tactical balanced; ~60/40 long-term target, can flex 50–70% equity | Fund-of-funds, tactical | Currently ~55% cash. Hard to model quantitatively because of active tactical layer |
| **Builders Fund** (whole-portfolio equity) | All-equity fund-of-funds | Aggressive whole-portfolio | Comprised of the four equity sleeves above |

For the v1 engine: **operate on the six pure sleeves.** Founders and Builders are funds-of-funds and add modeling complexity (their active layer is hard to capture quantitatively). They can be re-introduced as toggle-able shortcuts later.

### 5.2 Sleeve gaps to close (priority order)

1. **A pure bond-only sleeve.** This is the single highest-leverage addition to the v1 universe — it would meaningfully improve the shape of the efficient frontier. Already under discussion (Salman / Tom).
2. **A true cash / MMF sleeve** with zero modeled volatility (currently approximated by the Savings Fund at ~0.5% modeled vol).
3. **All-weather diversifier** — alternatives, hybrid, or inflation-protected exposure. Open question whether this comes from existing Purpose products (Hybrid, etc.).

### 5.3 Future sleeve strategy (post-Steadyhand)

When MP2.0 expands beyond Steadyhand, the sleeve universe grows. Key principles:

- **Sleeves are real, papered funds with a PM attached** (the Harness Investment Committee made this a table-stakes requirement).
- **Sleeves are launched ideally as ETFs** (universal accessibility, lowest cost), with mutual fund and SMA structures available where channel needs require.
- **Sleeves use the same rigor as Purpose's existing whole-portfolio funds (PACF/PABF/PAGF).** No "quickly whipped together" allocations.
- Purpose's existing 16 whole-portfolio models (PACF, PABF, PAGF, Harness, Link, PIMP) coexist with MP2.0 — they don't get replaced; they sit alongside as the "1.0" option.

### 5.4 Capital market assumptions source **[OPEN]**

Sleeve return / vol / correlation inputs need a defensible source: Goldman, JPM, Basinger (Purpose CIO) views, or composite. This is more consequential than its position implies — placeholder CMAs produce placeholder portfolios, which becomes critical when advisors begin using output to inform real client conversations. **Owner: Saranyaraj + Fraser.** Resolution required before Phase B exit; pilot use cannot begin without defensible CMAs in place. If unresolved at the Wednesday Som demo, the demo narrative must explicitly say "illustrative numbers" upfront.

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
  created_at, updated_at
}
```

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
  name                                  // e.g., "Buy cabin", "Retirement"
  target_amount, target_date            // OPTIONAL — secondary input only when client volunteers (Part 4.3c)
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

### 6.4 Account entity

```
Account {
  id, household_id, owner_person_id
  type: RRSP | TFSA | RESP | RDSP | FHSA | Non-Registered | LIRA | RRIF | Corporate
  regulatory_objective: income | growth_and_income | growth   // Steadyhand 3-bucket
  regulatory_time_horizon: <3y | 3-10y | >10y
  regulatory_risk_rating: low | medium | high                 // mapped from blend
  current_holdings: Holding[]                                  // sleeve allocations
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
  goals: { goal_id -> goal_risk_score }  // 1..5, single question per goal
}

// Engine-derived per (goal, account) pair:
ResolvedRisk {
  goal_id, account_id
  household_component: 1..5     // surfaced to advisor (Part 4.2)
  goal_component: 1..5          // surfaced to advisor
  combined_score: 1..5          // surfaced to advisor; what the optimizer uses
  combined_percentile: int      // 5 | 15 | 25 | 35 | 45 (Part 4.3)
}
```

The engine's risk input for a given (goal, account) is `combine(household_score, goal_risk_score)`. Default combination function for v1: a documented weighted blend; the weights are a tunable parameter we expect to refine.

The three components (`household_component`, `goal_component`, `combined_score`) are exposed to the advisor in the UI via an info icon / drill-down (Day 2 §1.3). All three are visible — the system does not hide the math.

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

### 6.7 The "5 atomic data points" question

Fraser pushed during the offsite: what are the **fewest** data points required to run MP2.0?

The answer landed at: more than 5, but the team should keep asking. Working draft of the **minimum viable inputs**:

1. Household composition (1 or 2 people, ages)
2. Total investable assets at Purpose
3. At least one named goal with a target amount and target date
4. Household risk score (composite of 3–4 questions)
5. Goal necessity (1 question per goal)
6. Account types and holdings
7. Time horizon per goal

If the system has these, it can produce a v1 portfolio. More data → better personalization. Less data → MP2.0 is still possible but degraded.

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

### 8.7 The three-tab household / account / goal view **[LOCKED — Day 2 §2, the "wow" of the session]**

This is the front-end paradigm Day 2 identified as genuinely novel — *"nobody is doing this. I haven't seen a visual of an account that holds two different goals."* (Lori) Fraser's framing: *"We're redesigning how advisors view their client's book."*

The total client AUM (e.g., $1.28M) should be **sliceable three ways**, each viewable by **funds** or **look-through to asset classes**:

| Tab | What it shows |
|---|---|
| **Household** | Total AUM, no partitioning. Holistic view. "Here's everything we manage." |
| **Account** | Same total, split across accounts proportionally. The advisor's traditional view. |
| **Goal** | Same total, split across goals (current allocated dollars, not future targets). Novel view. |

**Pivot-table principle:** the grand total in the bottom-right corner is always $1.28M; only the slices change. Every view reconciles to the same household total — no "money goes missing" between views.

**Fund / asset-class toggle:** within each tab, the advisor toggles between (a) a fund-level view (showing the actual sleeves/funds held) and (b) a look-through-to-asset-classes view (re-aggregating sleeve internals to show overall equity / fixed income / cash exposure). The latter is the natural lens for the "is the household risk profile aligned?" conversation.

**Why this is the wow:** clients don't typically map goals to accounts mentally; advisors do, from meeting notes. The goal-view tab makes that mapping visual for the first time. Steadyhand notes already implicitly contain this mapping ("the $25k in the TFSA is for Emma's school"); MP2.0 surfaces it.

### 8.8 Click-through workflow for setting a portfolio **[LOCKED — Day 2 §2.3]**

The advisor sets up a portfolio for an account through a structured click-through, not a free-form form fill:

1. **Click into an account** (e.g., $80k non-reg)
2. **Identify which goals it serves** (click, click — pick from the household's goals, or create a new goal inline)
3. **Assign proportions** (e.g., 50% to education, 50% to emergency fund)
4. **For each goal-account combo, the system pulls the duration + risk inputs and recommends a portfolio.** The advisor sees *"we recommend this"* — **the efficient frontier and apex curves are NOT shown** (those live behind the admin-only view, Part 4.7). Just the recommendation, with the one-sentence justification (Part 8.5).
5. **Repeat for each goal in that account.**
6. **System merges the per-goal-account recommendations into the consolidated account portfolio**, possibly collapsing to a single fund-of-funds if optimal (Part 4.3b).
7. **Client consents at the account level** (verbal or DocuSign per Part 7.5).

**Current vs. ideal allocation — both must be visible** (Day 2 §2.4). The view shows what the account currently holds **and** the recommended allocation, side-by-side. Don't only show the optimized output; that strips the context the advisor needs to have a conversation about why anything should change.

### 8.9 The fan chart as longitudinal reporting primitive **[LOCKED — Day 2 §3.4]**

The fan chart isn't only a "what might happen" projection at recommendation time — it's an ongoing reporting artifact:

1. **Lock the fan at time zero** when the portfolio is set. The fan represents the engine's projection at that moment.
2. **Place a dot on the chart at the goal date** (only when a dollar target is known — see Part 4.3c).
3. **Over time, plot the actual portfolio value** moving through the fan.
4. **Conversation trigger:** when actual value drops outside the bottom of the fan, the system flags this as a Stage-6 event prompting a plan review.

This turns the fan from a one-time recommendation visual into a continuous "are we on track?" instrument — and gives the advisor a structured trigger for when to call the client, replacing today's reactive practice.

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

### 9.2 Auth phasing **[LOCKED — tightened for advisor pilot]**

Three phases, OIDC throughout so transitions are config swaps, not rewrites.

| Phase | Mechanism | Trigger to advance |
|---|---|---|
| **0 — Offsite scaffold** | Django built-in auth, single hardcoded admin | Internal team Day 1–2 only; never touches real advisor work |
| **1 — Pilot (advisor-usable MVP)** | Django built-in auth with per-advisor accounts: forced password change on first login, password reset via email, session timeout (30 min), account lockout after 5 failed attempts, MFA via TOTP | First real advisor users beyond core team |
| **2 — Internal scale** | Microsoft Entra SSO via OIDC | Broader Purpose advisor rollout |
| **3 — Broader platform** | Auth0-backed user pool (OIDC) | DIY investors, third-party advisors, Advisor Center |

**Phase 0 → Phase 1 is the offsite-end-to-pilot-start transition.** A single hardcoded admin is acceptable for internal scaffolding during the offsite. It is *not* acceptable for advisor pilot use. The pilot hardening window (Part 13.0) closes this gap before any Steadyhand IS logs in.

**Permission framework (RBAC) is built in Phase 0, even if all checks pass.** Retrofitting authorization across every endpoint is the most error-prone refactor in any web app. Build the structure now; tighten the rules per phase. By Phase 1, RBAC enforces the actual roles in Part 7.2 — IS can recommend within Steadyhand fund set, cannot manage discretionarily, cannot give comprehensive financial planning advice.

**Roles for v1 RBAC:**

- **IS / Advisor** — sees only their assigned client book; cannot view other advisors' clients; cannot edit CMAs or view the efficient frontier; can override engine inputs (pre-recommendation) or annotate non-execution (post-recommendation) per Part 7.5
- **IS Manager** — sees their team's books, plus override on assignments
- **CMA Admin (Macro Insight Layer)** — restricted role for the CIO/strategist function; edits CMAs and views the efficient frontier per Part 4.7. Initially: 1–2 named individuals. All edits write to the audit log.
- **Compliance** — read-only across all clients within Steadyhand; audit log visibility
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
- Field overridden by advisor (before/after, who, when)
- Engine run (inputs, sleeve assumptions used, method + params, output, model version)
- Recommendation approved by client (when, by whom, via what channel)

Schema is append-only Postgres with row-level immutability via trigger. UI for browsing the audit log is post-MVP; the writes happen now.

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
│   ├── sleeves.py                    # Sleeve universe constant
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

The extraction layer is **in MVP scope and load-bearing for the pilot**. **Owner: Raj.** Source data: real Croesus exports manually copied by Lori (and pilot advisors, during Phase C) into `personas/<name>/raw/` — no API integration in MVP.

> **Real client PII is in scope for MP2.0 from day one.** The extraction pipeline processes real Steadyhand client documents — meeting notes accumulated over years, financial plans, account statements, transaction history — containing real names, real account numbers, real life details. This is not a synthetic-data build with a thin layer of redaction. Section 11.8 governs how real PII is handled operationally. **Section 11.8 is a hard prerequisite for the build, not an addendum to it. It must be read and signed off by Lori + Amitha (Purpose legal) before real client files land on any team machine.**

> **Operational dependency:** during Phase A the Croesus → file-drop pipeline depends on Lori as a person. Identify a backup who can copy files in her absence; have at least one fully synthetic persona that works without any real-data dependency, so the Wednesday Som demo is viable even if real data isn't available. During Phase C, pilot advisors copy files for their own clients; Lori's role shifts to triage and quality oversight.

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

Per canonical field, sort Facts by `asserted_at` desc:
- Most recent + highest confidence becomes the "current value"
- All prior facts retained as history
- Conflicts where recent values disagree with older ones are signal, not noise — surfaced in the review UI

Naive most-recent-wins is sufficient for v1. Sophisticated reconciliation (confidence-weighted, conflict-resolution heuristics) is post-MVP.

### 11.5 Layer 5 — Advisor review and approval

The most important screen in the system. Side-by-side:

- **Left:** source documents, clickable
- **Right:** consolidated client state, organized by Part 6 schema (Household / Person / Goals / Accounts / Risk)
- Each field shows source quote + originating document; click jumps to source
- Each field shows derivation method (extracted / inferred / defaulted) — extracted facts get visual priority; inferred facts get a "please confirm" marker
- Conflicts shown inline ("retirement_age: 67 (Aug 2024 note) — older value 65 in Mar 2023 note")
- All fields editable; edits logged with user + timestamp into audit log
- "Approve" button writes the canonical `ClientState` consumed by the engine

**Trust is earned or lost here.** Fields without provenance get re-done by the advisor — defeating the system's purpose.

### 11.6 Document classification

Filename convention preferred: `{date}_{doctype}_{description}.{ext}`. When absent or non-conforming, Claude classifier reads the first page and tags `meeting_note | kyc | statement | plan | other`. One extra Claude call per file. Both paths logged.

### 11.7 Privacy posture for raw files **[LOCKED]**

Original Croesus exports contain real client PII: names, dates of birth, addresses, SINs (sometimes), account numbers, employer names, beneficiaries, family details, health information, financial situation. The repository is structured on the assumption that **real PII never enters version control and never leaves authorized environments.**

- Raw files in `personas/<name>/raw/` for any real-derived persona are gitignored at the repo root with explicit `**/raw/**` patterns. CI fails if files matching common PII signatures appear in a commit.
- A scrub-pass utility flags potential PII (emails, SIN patterns, account numbers, phone numbers, full names) before any file enters a committed location. Files that fail the scrub pass cannot be committed.
- Synthetic personas may have raw files committed (the Sandra & Mike Chen demo persona is one of these); real-derived personas may not.
- A pre-commit hook on every team machine runs the scrub-pass utility automatically. The hook is part of the repo bootstrap (`make setup`), not an optional install.

### 11.8 Real client PII handling **[LOCKED — hard prerequisite]**

This section governs the operational use of real Steadyhand client PII in the MP2.0 build. **Lori + Amitha (Purpose legal) must review and approve this section before any real client file is copied onto a team machine.** Operating outside this section is a compliance failure, not a process slip.

#### 11.8.1 Authorization basis

Before real client data is used:

1. **Confirm the consent / authorization basis** under which Steadyhand can use real client documents for internal product development. Most likely covered under existing client agreements that permit internal use for service improvement, but this needs explicit confirmation in writing from Amitha.
2. **Document the scope** — which clients, which document types, for what purpose, for how long. Narrow is better than broad.
3. **Retain the authorization record** in a known location (project shared drive) with version, date, and signatories. Referenced by ID in the audit log.

If this confirmation has not happened, **no real client files are copied onto any team machine.** The build proceeds on synthetic personas only until authorization is in place.

#### 11.8.2 Data minimization

Use the smallest amount of real PII that proves the use case. Operating principle:

- **During offsite build (before pilot):** 1–2 real-derived personas (from Lori's tier-2 client base) exercise the extraction pipeline against real document shape, accumulated-history meeting notes, and the complexity that synthetic personas can't realistically simulate. Synthetic personas (5) exercise breadth; real-derived (1–2) exercise depth. The Wednesday Som demo runs the synthetic backup persona alongside one real-derived tier-2 example (pseudonymized).
- **During advisor pilot:** each pilot advisor loads files for their own client subset (not their full book). Pilot scope: **3–5 advisors, ~5–10 clients per advisor, total ~15–50 real-derived personas**. Pilot scope is bounded, documented, and reviewed at Week 2 of pilot use. The bound exists to limit blast radius if anything goes wrong, not to limit the system's usefulness.
- For each real-derived persona, advisors copy only the document types needed: meeting notes file, most recent KYC, recent statement. Not the full client file.
- The pseudonymization regime in 11.8.3 applies to all real-derived personas — both validation personas and advisor-pilot personas. Volume scales; controls don't change.

#### 11.8.3 Pseudonymization at the boundary

Real PII enters the pipeline at Layer 1 (raw ingestion). Real names, addresses, account numbers and other directly-identifying fields are **pseudonymized at the Layer 2 → Layer 3 boundary** before structured fact extraction:

- A per-persona pseudonym mapping is generated once and stored locally (encrypted, gitignored). Real "Marla Burnham" → "Persona_001" → display name "Sarah Lewis" (Daffy-Duck-style synthetic name).
- Layer 3 (Claude extraction) sees pseudonymized text. Source quotes stored with extracted facts contain pseudonymized strings, not real names.
- The reverse mapping exists only on authorized machines, encrypted at rest, never committed, never sent over the wire. It is used only in the Layer 5 advisor review UI when an authorized user toggles "show real identity."
- During Phase A and Phase C, audiences see pseudonymized data only. The Wednesday Som demo runs primarily on the synthetic backup persona, with optional pseudonymized real-derived persona display only after pseudonymization is verified. Pilot advisors see their own pseudonymized real-derived personas. No real client name appears on any shared screen.

This protects against three failure modes simultaneously: PII leaking into git, PII transiting to the LLM provider, and PII being shoulder-surfed during launch events or pilot use.

#### 11.8.4 LLM provider posture under real PII **[LOCKED]**

The v2.0 default of "Anthropic API direct in dev, Bedrock in prod" was set under synthetic-data assumptions. Real PII changes the calculus:

- **Even with pseudonymization at the Layer 2 → Layer 3 boundary, residual identifying detail remains.** Meeting notes contain employer names, neighborhood references, family member relationships, health details, and other quasi-identifiers that pseudonymization of names alone does not catch.
- **Dev LLM provider for real-PII extraction: Bedrock in ca-central-1, not Anthropic API direct.** This keeps real Canadian client data inside Canadian-resident infrastructure under Purpose's AWS account from the moment the build begins handling real data — not deferred to "production." Bedrock enablement (Part 14 item 3) becomes a Day 1 blocking item the moment real PII is in scope, not a post-MVP item.
- **Anthropic API direct remains acceptable for synthetic-persona work** (Sandra & Mike Chen, the four other synthetic personas). The LLM client wrapper (Part 9.5) routes per-persona based on a `data_origin` flag: `synthetic → anthropic_direct`, `real_derived → bedrock_ca_central_1`. Misconfiguration (real persona routed to direct API) is a deployment-blocker check, not a runtime warning.
- **Document the position in writing** so the team can defend it under audit: "real Canadian client PII is processed only via AWS Bedrock in ca-central-1, under Purpose's AWS account, from the start of the build."

#### 11.8.5 Storage and machine posture

Machines that touch real PII files (the offsite laptops, the staging server) must:

- Have full-disk encryption enabled and verified (`fdesetup status` / `lsblk -f` checks documented before files land).
- Have screen-lock timeout ≤5 minutes.
- Not sync the project directory to personal cloud storage (Dropbox, iCloud, personal Drive, OneDrive). The repo is on a known-clean working directory; personal sync clients excluded by path.
- Store the per-persona pseudonym mapping in an encrypted vault (1Password, age-encrypted file, or equivalent), not in the repo and not in plain text on disk.
- Run the pre-commit scrub-pass hook (from 11.7) without exception.

The staging server (Part 9.6.2) is in Purpose's AWS account, ca-central-1, from the moment real PII is in scope. **Render.com free tier and other US-resident hosts are not acceptable for real PII**, even for staging. If the staging URL is needed before AWS staging is ready, it serves only synthetic personas.

#### 11.8.6 Retention and disposal

Real PII files have a defined lifespan in the build environment:

- Raw files copied for the offsite are retained for the duration of MP2.0 active development against that data, then deleted from local machines and staging storage.
- "Active development against that data" is reviewed at each version milestone (v2.x → v3.x). Default disposition at version-bump is deletion unless explicitly retained with a documented reason.
- Disposal is logged in the audit log: file ID, sha256, deletion timestamp, machine, operator. The audit trail outlives the file.
- The pseudonym mapping is retained as long as the structured extracted facts are retained, so the audit chain remains queryable.
- **Lori is responsible for ensuring the original Steadyhand-side records are unaffected.** MP2.0 disposes of its working copies; the system of record remains in Croesus.

#### 11.8.7 Demo audiences and pilot use

The Wednesday Som demo, the Mon/Tue IS validation sessions, and the ongoing advisor pilot all involve people seeing the running system, with different stakes:

- **Wednesday Som demo** — primary persona is the synthetic Sandra & Mike Chen; one optional pseudonymized real-derived tier-2 persona may be shown if pseudonymization has been verified. No real names appear during the presentation.
- **Mon/Tue IS validation sessions** — each IS runs the system on their own real tier-2 clients (pseudonymized). Each IS sees only their own clients, RBAC-enforced.
- **Pilot use (Phase C onward)** — each advisor sees their own pseudonymized real-derived personas. The Layer 5 review UI's "show real identity" toggle is enabled for the advisor on their own personas only, not on others'. RBAC enforces this at the API layer, not just the UI.
- Screen recordings, screenshots, and slides made during the offsite or pilot retrospectives use pseudonymized data. Pre-rolled media reviewed for incidental PII leakage (window titles, file paths, browser tabs) before circulation.
- If an advisor recognizes another advisor's client from quasi-identifiers (employer, neighborhood, family situation), that's a finding to log and tighten — not a "well, they figured it out" shrug. The pseudonym scheme exists because *quasi-identifiers leak*, and 11.8.3 should be revisited if this happens.

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
    sleeve_universe: list[Sleeve],
    method: OptimizationMethod = "percentile",  # Part 4.3
    constraints: Constraints | None = None,
) -> EngineOutput:
    ...
```

`EngineOutput` contains:

- **Per-link blends**: one optimized sleeve-weight vector per `GoalAccountLink` (Part 4.3a — the optimization unit is the goal × account cross). The `link_id` keys back to the household's `GoalAccountLink` set.
- **Per-account roll-up**: each account's consolidated holdings, weighted across the per-link blends within that account (Part 4.3a step 2).
- **Per-account fund-of-funds collapse suggestion** (Part 4.3b): if the per-account roll-up closely matches an existing whole-portfolio fund (Founders, Builders, PACF, etc.), the engine recommends that fund instead of the sleeve list. Includes a "match score" so the UI can show why.
- **Household roll-up**: aggregated weighted blend across all accounts.
- **Resolved risk per link**: `household_component`, `goal_component`, `combined_score`, `combined_percentile` — all surfaced to the UI per Part 4.2.
- **Fan chart data per link**: 10th / 50th / 90th percentile portfolio value over the goal's time horizon. Fan locks at t=0 for longitudinal plotting (Part 8.9).
- **Compliance risk rating** per account + household (low/med/high) per Part 7.4.
- **Audit trace**: sleeve assumptions used (CMA snapshot ID, asset-class composition, tax-drag table version), frontier coordinates, method + params, prompt + model version where AI was involved, optimization timestamp.

The shape is per-link first, account second, household third. The UI consumes whichever level matches its current view (Part 8.7 three-tab toggle).

### 12.2 Schemas live in engine/

Pydantic models for `Household`, `Person`, `Goal`, `GoalAccountLink` (many-to-many — central to the goal × account optimization unit, Part 4.3a), `Account`, `Holding`, `RiskInput`, `ResolvedRisk` (per-link three-component exposure, Part 6.5), `Sleeve`, `CMASnapshot` (sleeve return/vol/correlation/asset-class composition, versioned), `TaxDragTable` (per-fund / per-asset-class drag factors), `Allocation`, `LinkBlend` (per-link optimization output), `AccountRollup`, `EngineOutput`, `EngineRun`. Web layer imports from `engine.schemas`; engine never imports from web.

### 12.3 The Claude artifact handoff process

Engine code arriving from Fraser/Nafal's Claude artifacts gets:

1. Wrapped in the I/O contract (Pydantic in, Pydantic out)
2. Test suite written against the persona fixtures
3. Reviewed for things prototypes skip: input validation, edge cases, numerical stability, empty-input behavior

Artifact code is treated as reference implementation, not production code. Re-implemented inside the engine package's conventions. Few hours per module; saves the class of bug where the prototype worked on three test cases and breaks on the fourth.

### 12.4 Pilot posture: live vs. cached

In actual pilot use, what's interactive vs. what's pre-computed?

- **Interactive (live engine call):** advisor-initiated portfolio computation, what-if sliders, Layer 5 fact review and approval, "regenerate" actions on plain-language explanations.
- **Pre-computed and cached:** initial engine outputs after a fresh persona load (computed once on persona ingestion, cached until a material change), fan charts (computed alongside engine output), baseline goal probabilities. Cache invalidates on plan change, persona reload, or sleeve-universe update.

Engine + extraction calls are LLM-bound and slow — interactive sub-second response requires caching. For Phase A (Wednesday Som demo), the synthetic backup persona's outputs are pre-baked entirely. For Phase C (pilot use), the cache layer is real and tested. Build the cache abstraction in Phase A so Phase B doesn't need a refactor.

Async work: a Celery worker (Part 9.6.4) handles engine runs that exceed an interactive budget (~5 seconds). The advisor sees a "computing your portfolio…" state, with a clear ETA, rather than a hung browser tab.

---

## PART 13 — MVP SCOPE, BUILD SEQUENCE, PILOT LAUNCH

### 13.0 Three-phase delivery: scaffold → harden → pilot **[LOCKED — schedule per Day 2]**

The deliverable is a working MVP that 3–5 Steadyhand advisors will use with real clients (Part 1.6). The actual delivery has three phases:

| Phase | Timing | Output | Bar |
|---|---|---|---|
| **Phase A — Offsite scaffold** | Mon–Wed at offsite (3 days), with Thursday extension at offsite location and Friday cleanup at Purpose office available as buffer | Foundation: extraction pipeline, engine integration, end-to-end flow, Wednesday end-of-day demo to Som | Som-demo-grade. Stage-managed paths work. The Wednesday demo runs cleanly. |
| **Phase B — Pilot hardening + IS validation** | Following Mon–Tue (IS team demos with real client data) plus ~1–2 weeks afterward | Auth Phase 1 (per-advisor accounts), error handling, edge-case coverage, feedback channel, pilot-mode disclaimer in UI, IS training, kill-switch | Advisor-usable. An IS can load a real tier-2 client, get sensible output, and know what to do if something looks wrong. |
| **Phase C — Pilot launch + iteration** | Week 3 onward | 3–5 advisors actively using the system with their real clients. Weekly retros. Structured feedback intake. Defects triaged and fixed in batches. | Pilot-grade. Most reasonable advisor actions produce usable output or graceful failure. |

**The Wednesday Som demo is the close of Phase A.** Phase B begins the following week, opening with IS team validation Monday/Tuesday using their own tier-2 client data. **Saranyaraj has an engineering hackathon Mon/Tue that week with partial availability** — Phase B day-1 capacity is reduced and that's a known constraint, not a surprise.

Phase C begins when Phase B exit criteria (Section 13.0.1) are met.

#### 13.0.1 Phase B exit criteria — the gate to pilot launch

Pilot use cannot begin until **all** of the following are true:

- Auth Phase 1 in production: per-advisor accounts, password reset, MFA, session timeout, lockout (Part 9.2)
- Real-PII regime fully operational: Bedrock ca-central-1 routing for real-derived personas, pre-commit scrub-pass hook, Lori + Amitha written authorization (Part 11.8)
- Compliance risk-rating mapping function deployed and reviewed (Part 7.4)
- Pilot-mode disclaimer visible in UI on every recommendation: "Pilot output — review before sharing with clients. Not for use as standalone investment advice."
- Audit log writes confirmed on every meaningful action including pre/post-recommendation overrides (Part 9.4.6, Part 7.5)
- Feedback channel operational (Part 13.0.2) with at least one team member triaging
- IS onboarding documentation written, reviewed by Lori, walked through with at least one pilot advisor
- Kill-switch tested: a single config change can disable engine output platform-wide if a critical issue is discovered
- Admin-only CMA + efficient frontier view exists and is properly access-restricted (Part 4.7)
- IS team Mon/Tue demo session completed with structured findings logged
- One full pilot-quality run on a real tier-2 client persona reviewed end-to-end by Lori, with no blocking findings

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

### 13.1 The Wednesday Som demo and the IS validation week **[LOCKED]**

By the end of the offsite Wednesday, the team produces a **working MVP foundation** demonstrating the loop:

**Stage 1 → Stage 2 → Stage 3 → Stage 5**

The Wednesday end-of-day **demo to Som** is the close of Phase A. The audience is Som and any executive sponsors he brings. Thursday at the offsite location and Friday at Purpose office serve as buffer/cleanup if Phase A slipped.

The following **Monday and Tuesday** are the IS team validation sessions — Lori's investment specialists run the system end-to-end on **their own real tier-2 client data** (notes, accounts, goals). This is the structural beginning of Phase B and the most consequential testing event in the project: the first time the system meets real Steadyhand advisor practice on real Steadyhand client work. Findings are logged, prioritized, and feed Phase B hardening.

**Saranyaraj has an engineering hackathon Mon/Tue that week** with partial availability; Phase B day-1 engineering capacity is reduced. Plan around it.

Pilot use (Phase C) begins after Phase B exit criteria (Section 13.0.1) are met — typically ~1–2 weeks after the IS validation sessions, depending on what they surface.

### 13.2 Phase A build sequence — offsite scaffold (3 days, Mon–Wed) **[LOCKED]**

Phase A produces the foundation organized around **three pillars** (Day 2 framing, Saranyaraj):

1. **Ingestion layer** — robust extraction of client risk, goals, account mapping, time horizons from notes
2. **Portfolio engine** — Fraser's optimizer plugged into the application, tested with real fund data
3. **Reporting / dashboard** — *"Am I going to be okay?"* — the part nobody else has integrated

**UI polish, branding, and Purpose visual identity are explicitly deferred.** Usability for an advisor like Evan is the bar, not visual finish.

**Phase A is not advisor-usable on its own** — that's the work of Phase B (Section 13.0.1). The day-1-morning list is aggressive. **If the schedule slips on Day 1, the Wednesday Som demo is at risk because every subsequent day depends on it.** Buffer is built into the structure below: *critical path* items must land before lunch; *important but deferrable* items can move to Day 1 evening or Day 2 morning if needed. Thursday at offsite + Friday at Purpose office are available as additional buffer.

#### Day 1 morning — scaffold and contract

**Critical path (must land before lunch):**
- Repo with engine/extraction/integrations/web/frontend package boundaries
- Django + DRF + Postgres skeleton; Docker Compose for local dev
- React + Vite + Tailwind + shadcn/ui frontend skeleton talking to DRF
- Pydantic schemas for Household / Person / Goal / Account / RiskInput / Sleeve / EngineOutput
- Sleeve universe constant (six Steadyhand pure sleeves; placeholder return/vol/correlation)
- Engine `optimize()` stub returning realistic-shaped output
- One end-to-end "hello world": login → client list → client detail (empty)
- LLM client wrapper (Anthropic provider for now)

**Important but deferrable to Day 1 evening:**
- Auth Phase 1 (single hardcoded admin) with OIDC-ready user model
- Permission decorator on every view (all checks return true for now)
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
- Sleeve universe with real numbers (or best-available placeholders — see Part 5.4)
- Wire engine to web app: approved client → "Generate portfolio" → engine call → result display
- Result display: stacked bar / donut for blend, sleeve-level breakdown, explainability trace, risk-rating mapping
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
- Walk-through end-to-end on the demo persona (synthetic hero + at least one tier-2 real-client example, pseudonymized)
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

- **Real-PII handling discipline slips under offsite pressure.** Highest-consequence operational risk. The pre-commit scrub-pass hook, the Bedrock-only routing for real personas, the encrypted disk requirement, and the gitignore patterns must be in place *before* any real file is copied. If they aren't, the build proceeds on synthetic personas only. Section 11.8 is not optional.
- **Pilot retention risk.** If pilot software is bad, advisors don't come back. There's no second pitch. Phase B exit criteria exist for this reason; an under-baked pilot launch is worse than no pilot launch.
- **The "false euphoria" risk** (Day 2, Fraser): *"the school play is three weeks away and like, guys, we're ready. I don't know my lines."* Phase A produces stage-managed paths that work for the Som demo. Phase B is when those paths break and need fixing for real IS use. Resist the urge to declare victory at Wednesday close.
- **Saranyaraj hackathon Mon/Tue reduces Phase B day-1 capacity.** Known constraint; not a surprise. Front-load Phase B planning during Day 3 (Wednesday) so partial-availability days are productive.
- **Mon/Tue IS validation finds large gaps.** This is the most consequential testing event in the project and almost certainly will surface real gaps. Plan for Phase B to extend if needed; do not pre-commit to a Phase C launch date until Mon/Tue findings are triaged.
- **Support load underestimated.** 3–5 advisors using the system can generate more support traffic than 4 engineers can absorb mid-build. Phase B includes establishing the feedback channel + triage owner explicitly so this doesn't degrade into Slack DMs to Lori.
- **Authorization basis for real-PII use unconfirmed.** If Lori + Amitha haven't signed off in writing before the offsite, real client files do not get copied. Build runs synthetic until cleared. This is a Day 0 blocking item.
- **Bedrock enablement on Purpose's AWS account is unconfirmed.** Required before real PII is processed. If not enabled by Day 1, real-derived personas cannot be added to the pipeline that day. Treat as a standing item until confirmed (Part 14 item 3).
- **Croesus export format unknown until Lori provides one.** Get one real meeting note before writing extraction prompts. 30 minutes of reading saves hours of building against assumptions.
- **Engine code cleanliness unknown.** If Fraser/Nafal hand a clean function, integration is 30 minutes. If a Jupyter notebook with execution-order dependencies, half a day of refactoring. Read the code Day 1 evening.
- **Auth Phase 0 → Phase 1 transition skipped.** Hardcoded admin works for offsite scaffold; cannot ship to advisors. Phase B exit criteria gate this.
- **Lori-as-single-point-of-failure for data pipeline.** Identify a backup; ensure at least one fully synthetic persona is end-to-end functional without real-data dependency.
- **CMA placeholder masquerading as real numbers.** If Part 5.4 unresolved by Wednesday Som demo, demo narrative must explicitly say "illustrative numbers." Pilot output (Phase C) cannot have placeholder math sitting under real-client recommendations.
- **Three-tab view scope creep.** Day 2 identified the household/account/goal toggle as the single biggest "wow." It's also a nontrivial UI build. If running tight, the goal tab is the must-have novelty; account-tab and household-tab can launch with simpler cuts and iterate.
- **Override note friction.** Steadyhand IS already note every interaction. Adding mandatory override notes risks fatigue. Inline the note capture; don't create a separate workflow.
- **Bad-output incident in early pilot.** An advisor takes a wrong recommendation to a real client conversation. Mitigations: pilot-mode disclaimer, weekly retros, kill-switch, audit log enabling root-cause reconstruction. Cannot be eliminated; can be contained.

### 13.4 Parallel work split — owners per Day 2 follow-ups

| Person | Owns (Day 2 task assignments) |
|---|---|
| **Saranyaraj** | Repo scaffold, Django + DRF, in-app AI ingestion layer (replacing the external Claude proxy), Fraser's optimizer plugged into the application, per-fund/per-asset-class tax drag stub, advisor override functionality with audit log, dynamic three-tier reporting with generative copy, restricted admin view for CMAs and frontier, Figma mockups (with team) for client report + account view at three sophistication levels, end-to-end demo run with Lori's team using real client data |
| **Fraser** | Optimizer engine code (integration-ready before Day 3), fan chart visualization for outcome projection, household → account → goal view structure (with Lori, Nafal) |
| **Nafal** | Finalize 5-point risk questionnaire and integrate with engine; sketch on household/account/goal view structure with Fraser, Lori |
| **Lori** | Provide tier-2 client sample data (notes-based) for ingestion testing; sketch on household/account/goal view structure with Fraser, Nafal; persona selection; IS pilot training; "what good looks like" |

Roughly halves wall-clock if handoffs are clean. The team is small enough that "parallel" is partial; pairing on big interfaces (e.g., the three-tab view) is preferred over strict ownership.

### 13.5 Wednesday Som demo flow **[LOCKED — Day 2 framing]**

The demo flow is the path Phase A optimizes for. Every screen serves a specific minute. Everything else is Phase B+.

```
1. INGESTION — drop a .docx of consolidated meeting notes
   → AI ingestion populates the structured client object
   → advisor reviews/validates the extraction (Layer 5 review UI)

2. HOUSEHOLD VIEW — "here's everything we manage for them"
   → total AUM (e.g., $1.28M), no partitioning
   → toggle between funds / look-through-to-asset-classes (Part 8.7)

3. DRILL INTO ACCOUNTS — same total, sliced by the four accounts
   → click into one account ($80k non-reg)
   → see its current holdings

4. DRILL INTO GOALS — same total, sliced by goals
   → see the M:N goal-account mapping
   → "the $25k in the TFSA is for Emma's school"

5. CLICK-THROUGH PORTFOLIO ASSIGNMENT — for the $80k non-reg account
   → identify which goals it serves (click, click)
   → assign proportions (50% education, 50% emergency)
   → for each goal-account combo, system recommends a portfolio
   → no efficient frontier shown to advisor (admin-only)
   → just "we recommend this" with the one-sentence justification (Part 8.5)
   → system merges the two into the consolidated account portfolio
   → may collapse to a single fund-of-funds (Founders, Builders) if optimal

6. PORTFOLIO RECOMMENDATION VIEW
   → current vs. ideal allocation, side-by-side
   → tier-appropriate explanation copy (Tier 1 / 2 / 3)
   → fan chart locked at t=0, dot at goal date

7. RETURN TO DASHBOARD — "am I going to be okay?"
   → integrated outcome view across all goals
   → the part nobody else has done
```

For the Som demo this runs on a tier-2 client persona (real client documents, pseudonymized per Part 11.8.3) **and** on a fully synthetic backup persona. Pseudonymization is verified before any screen is shared.

For the IS Mon/Tue session this runs on the IS's own real tier-2 clients (each IS sees only their own clients, RBAC-enforced).

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

Before production deployment, get explicit answers. **If any item blocks Day 1, the build proceeds in a personal AWS sandbox with a clear migration path documented — except items marked [REAL-PII BLOCKER], which block real-PII use until resolved (build proceeds on synthetic personas only).**

1. ECS namespace / IAM boundary / tagging convention for MP2.0 inside the existing AWS account
2. Federation pattern: Entra → AWS SSO via SAML, or OIDC, or other
3. **[REAL-PII BLOCKER]** Bedrock enablement in ca-central-1: turned on in the org, or requires Service Control Policy change. Required before real client PII enters the extraction pipeline (Part 11.8.4).
4. **[REAL-PII BLOCKER]** Data classification tier for client PII; storage and encryption requirements that flow from it. Confirms whether Part 9.3 / Part 11.8 defaults are sufficient or need tightening.
5. Existing logging/observability stack: Elastic only, or also Datadog/Splunk; where audit logs need to be queryable
6. Maintenance windows on the shared ECS-EC2 cluster (avoid Wednesday Som demo + Mon/Tue IS session + pilot-active-time node drains)
7. Whether MP2.0 CI/CD can deploy autonomously or needs platform team approval per change
8. **[REAL-PII BLOCKER]** Confirmation from Amitha (Purpose legal) of the authorization basis for using real Steadyhand client documents in product development (Part 11.8.1). If unwritten, get it in writing before any real file is copied.

---

## PART 15 — OPEN QUESTIONS & DECISIONS PENDING

| # | Open question | Owner | Status |
|--:|--------------|-------|--------|
| 1 | Final method for risk-on-frontier (percentile / probability / utility) — Method 1 with 5/15/25/35/45 percentile mapping locked Day 2 | Saranyaraj + Fraser | LOCKED for v1 |
| 2 | Specific weighting in the household × goal risk composite | Team | OPEN — document the function, parameterize for tuning |
| 3 | Compliance risk-rating mapping function — exact thresholds | Lori + Saranyaraj | OPEN |
| 4 | Bond-only sleeve launch path | Salman + Tom | OPEN — highest-leverage product-side gap |
| 5 | Whether and how to model Founders Fund / Builders Fund (active layer) | Saranyaraj | LOCKED — leave as fund-of-funds collapse target (Part 4.3b), not modeled as sleeve |
| 6 | Household-level risk handling when accounts blend differently | Team | RESOLVED Day 2 — optimization unit is goal × account (Part 4.3a); per-link risk uses combined score |
| 7 | API integration with Conquest — feasibility for v2 | Saranyaraj | OPEN — v1 uses file/manual entry |
| 8 | Goal-decomposition model — turning narrative goal ("retire well") into fungible $ targets | Team | DEFAULT — wants/needs/wishes split is the v1 approach; future-dollar targets are secondary input only (Part 4.3c) |
| 9 | Reporting / portal scope — what does Andrew's team build first | Andrew + team | OPEN — out of MAT scope but blocking for full pilot experience |
| 10 | Behavioral-bucket schema — how many buckets, how to assign | Lori + Saranyaraj | PARTIALLY RESOLVED — three sophistication tiers locked (Part 8.4); behavioral-bucket emphasis composes within tiers |
| 11 | When does drift trigger rebalance — exact thresholds | Team | DEFAULT — 3–5% off, or material event, or actual breaches bottom of fan (Part 8.9) |
| 12 | Whether goal-level questionnaire is one question or three | Lori + Fraser | RESOLVED Day 2 — single 5-point question per goal, with 5-point household composite |
| 13 | How external (non-Purpose) assets enter the household view | Team | RESOLVED Day 2 — optional risk-tolerance dampener (Part 4.6a); not full simulation |
| 14 | Testing protocol — internal IS feedback (Mon/Tue post-offsite) + Som demo Wednesday + advisor pilot | Lori + Saranyaraj | LOCKED |
| 15 | Capital market assumptions source for sleeve return/vol/correlation inputs | Saranyaraj + Fraser | OPEN — required before Phase B exit. Now also tied to admin-only CMA editor (Part 4.7) |
| 16 | Real meeting note shape (templated vs freeform, length, structure, date conventions) | Lori → Raj | OPEN — get one real note before finalizing extraction prompts |
| 17 | Sleeve numerical inputs (real vs placeholder) for v1 | Saranyaraj + Nafal | OPEN — engine can stub initially; tax drag default 0 acceptable for v1 |
| 18 | Optimizer code handoff timing from Fraser/Nafal artifacts | Fraser, Nafal → Raj | LOCKED — integration-ready before Day 3 morning |
| 19 | PDF rendering library for client outputs (WeasyPrint, ReportLab, headless Chrome) | Raj | DEFAULT — defer to week 2 |
| 20 | Fast-forward simulator: pre-baked future states or live re-projection | Team | DEFAULT — pre-baked acceptable for Som demo; revisit for pilot iteration |
| 21 | Reconciliation strategy beyond most-recent-wins | Team | OPEN — post-MVP refinement |
| 22 | Frontend-comfortable person assignment for parallel build | Team | RESOLVED — small team, partial-parallel pairing on big interfaces (see Part 13.4) |
| 23 | Lori's backup for file-pipeline operational dependency | Lori + team | OPEN — name before offsite kickoff |
| 24 | Authorization basis for real-client-PII use in product development — written confirmation from Amitha | Lori + Amitha | OPEN — REAL-PII BLOCKER, must resolve before Day 0 |
| 25 | Bedrock ca-central-1 enablement on Purpose's AWS account | Saranyaraj + Purpose IT | OPEN — REAL-PII BLOCKER, must resolve before real-derived personas enter pipeline |
| 26 | Per-persona pseudonym mapping storage mechanism (1Password vs age-encrypted file vs other) | Raj | OPEN — pick before first real file is copied |
| 27 | Quasi-identifier handling in pseudonymization (employer, neighborhood, family situation) — leave in or strip | Lori + Raj | OPEN — affects extraction quality; default is leave-in for v1 with explicit acknowledgment |
| 28 | Real-PII retention period and disposal trigger | Team | DEFAULT — version-bump default, with explicit retain-with-reason exceptions |
| 29 | Som demo audience and any quasi-identifier risk if real-client persona is shown | Lori | OPEN — confirm before Wednesday |
| 30 | Identity of the 3–5 pilot advisors and their commitment to Phase C participation | Lori | OPEN — name and confirm before Som demo |
| 31 | Phase B exit criteria — who signs off, how disagreements get resolved | Fraser + Lori + Raj | OPEN — agree at Day 3 close so Phase B runs cleanly |
| 32 | Pilot-mode disclaimer wording — exact text on every recommendation screen | Lori + Amitha | OPEN — review before Phase B exit |
| 33 | Feedback channel and triage owner | Team | OPEN — choose before Phase B exit |
| 34 | IS pilot training material — written guide, walkthrough format | Lori | OPEN — drafted in Phase B |
| 35 | Pilot success metrics — finalize the targets in Section 13.0.3 | Fraser + Lori | DEFAULT — current targets are working defaults |
| 36 | Pilot duration and exit decision — when does Phase C end, what's the next phase | Fraser + Som | OPEN — 6-week working assumption |
| 37 | True Plan ↔ Portfolio iterative recursion (Conquest Monte Carlo round-trip with optimizer) | Team | OPEN — mathematically attractive but expensive; v1 is single-pass, revisit later (Day 2 §9) |
| 38 | Real vs. nominal dollars in long-duration projections | Team | OPEN — acknowledged Day 2, unresolved |
| 39 | Whether the client (vs. only the advisor) sees the goal-account three-tab view | Lori vs. Fraser | OPEN — Lori leans client-sees-only-the-report; Fraser leans client-sees-trimmed-version-of-dashboard. Resolve before Phase C |
| 40 | User testing proxy strategy — non-engaged spouses as testers? | Team | OPEN — floated Day 2; needs concrete plan |
| 41 | Articulating to clients the value of disclosing external holdings | Lori | OPEN — needed before pilot to drive disclosure rate |
| 42 | The exact CMA admin permissions model (single role vs. tiered) | Saranyaraj + Lori | OPEN — Phase B work; admin-only flag is the v1 minimum |
| 43 | Override note inline UX — how to capture without creating workflow fatigue | Saranyaraj + Lori | OPEN — Phase B design |
| 44 | Match-score threshold for fund-of-funds collapse recommendation (Part 4.3b) | Saranyaraj + Fraser | OPEN — what % composition match triggers "use Founders instead" |

---

## PART 16 — GLOSSARY & VOCABULARY

Use these terms precisely. Inconsistency confuses the team and the build.

### 16.1 Strategic & investment vocabulary

| Term | Definition |
|------|------------|
| **MP2.0** | Model Portfolios 2.0 — this initiative |
| **Sleeve fund (or Sleeve)** | A standardized, single-mandate building-block fund. Sleeves are the molecules. 8–12 in the universe. |
| **Atom** | Underlying security held inside a sleeve (an individual stock or bond). Clients/advisors don't operate at this level. |
| **Blend** | The personalized mix of sleeves driven by a client's plan. The painting. |
| **Blend ratios** | The specific percentages of each sleeve in a client's blend. |
| **Macro Insight Layer** | The CIO/strategist function that updates sleeve internals (atoms) based on macro views. Independent of client blends. |
| **Living Financial Plan** | The continuously-updated model of the household's situation. Source of truth for blends. Not a document. |
| **Paint mixing** | Fraser's analogy: sleeves are paints, blend is the painting, atoms are the pigments. |
| **Frontier** | The efficient frontier — set of optimal portfolios in (volatility, return) space. |
| **Glide path** | The trajectory of a blend toward lower-risk (cash) as a goal nears its target date. |
| **Necessity score** | Per-goal: 1=wish, 3=want, 5=need. Drives goal-level risk score. |
| **Risk descriptor (client-facing)** | "Cautious / Conservative-balanced / Balanced / Balanced-growth / Growth-oriented." Use this vocabulary in any client-visible copy. *"Low / medium / high"* is held internally for engine math and compliance, not surfaced to clients. See Part 4.2 / Day 2 §6.2. |
| **Household risk score** | Composite score capturing investment knowledge, behavior, capacity. |
| **Goal risk score** | Per-goal: how essential is this specific goal? |
| **Wants and needs (and wishes)** | Goal categorization. Some constructs use 3 levels; we currently merge to 2. |
| **Whole-portfolio fund** | A multi-asset fund-of-funds, like Founders or PACF. Distinct from a sleeve. |
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

- **v2.3 (Apr 28, 2026)** — **Day 2 afternoon design lock-ins integrated.** Major architectural decisions captured: optimization unit is goal × account cross (Part 4.3a), 5-point risk scale mapped to 5/15/25/35/45 percentile range with snap-to-grid output (Part 4.2/4.3), three-component risk exposure surfaced to advisor (Part 4.2), tax-drag schema with per-fund/per-asset-class factors (Part 4.5), recommended portfolio always sits on the frontier with fund-of-funds collapse for execution (Part 4.3b), future-dollar targets are secondary input only (Part 4.3c), external holdings as risk-tolerance dampener moves in-scope (Part 4.6a), CMA admin layer with restricted access sharpens the Macro Insight Layer (Part 4.7). Added two major new UX sections: three-tab household/account/goal view (Part 8.7) and click-through portfolio assignment workflow (Part 8.8) — the "single biggest wow" of the session. Added longitudinal fan chart mechanic (Part 8.9). Restructured Part 8.4 as three sophistication tiers (Tier 1/2/3) with behavioral bucketing composing within tiers. Added concrete sentence templates for "why this portfolio?" (Part 8.5). Added pre-recommendation vs. post-recommendation override patterns (Part 7.5). Added CMA Admin role to RBAC (Part 9.2). Schedule corrected: **Wednesday Som demo** (not Friday); IS team validation Mon/Tue following week (Saranyaraj hackathon partial-availability called out). Refactored Part 13 build sequence to add Day 3 (Wednesday) close-out and revise Phase B sketch. Replaced 8-segment Sandra & Mike storyboard with Day-2 demo flow (drop notes → ingestion → household/account/goal drill → portfolio recommendation → "am I going to be okay?" output). Updated EngineOutput contract to be per-link first (Part 12.1). Vocabulary update: client-facing copy uses cautious / balanced / growth-oriented, not low/medium/high (Day 2 §6.2). Resolved 5 open questions (composite risk, goal-questionnaire, external assets, frontend assignment, demo-grade-vs-pilot-grade); added 8 new ones from Day 2 (recursion, real/nominal, client-vs-advisor view, external disclosure, CMA admin permissions, override UX, fund-of-funds match threshold, user-testing proxy). Added 17 new vocabulary terms covering Day 2 design.

- **v2.2 (Apr 2026)** — **Reframed deliverable from "demo" to "MVP for advisor pilot."** 3–5 Steadyhand Investment Specialists will use the system with real clients in a controlled pilot starting after the offsite. Added Part 1.6 explicitly redefining the deliverable and the demo-vs-MVP bar table. Restructured Part 13 as three phases: Phase A (offsite scaffold, 2 days, demo-grade foundation), Phase B (pilot hardening window, ~2 weeks, advisor-usable), Phase C (pilot launch + iteration, 3–5 advisors). Added Part 13.0.1 with explicit Phase B exit criteria gating advisor onboarding. Added Part 13.0.2 with pilot operations (feedback channel, office hours, weekly retros, bad-output escalation, pilot-mode disclaimer, IS training, kill-switch). Added Part 13.0.3 with pilot success metrics. Tightened Part 9.2 auth: Phase 0 (hardcoded admin, offsite only) → Phase 1 (per-advisor accounts with MFA, password reset, session timeout, lockout) → Phase 2 → Phase 3. Updated Part 11.8.2 data minimization to scale across phases (1–2 personas Phase A → ~15–50 Phase C). Updated Part 11.8.7 from "demo audience" to pilot-audience framing with RBAC enforcement. Updated Part 12.4 from demo-posture to pilot-posture. Updated Part 13.7 out-of-scope from demo bar to pilot bar. Added 4 pilot-related compression risks (retention, support load, demo-grade-mistaken-for-pilot-grade, bad-output incident). Added 7 new open questions covering pilot logistics. Added 6 new vocabulary terms.

- **v2.1 (Apr 2026)** — **Real client PII brought in scope.** Added Part 11.8 governing operational use of real Steadyhand client PII (authorization basis, data minimization, pseudonymization at Layer 2→3 boundary, LLM provider posture, machine posture, retention/disposal, demo audience considerations, incident response). Tightened Part 9.3 data classification defaults to assume client-PII tier as floor. Updated Part 11 preamble flagging Section 11.8 as hard prerequisite requiring Lori + Amitha sign-off. Sharpened Part 11.7 on git/repo posture with mandatory pre-commit scrub-pass hook. Updated Part 13.6 to clarify hero demo persona is synthetic; real-derived personas exercise extraction depth. Sharpened Part 13.7 demo PII rule. Added 4 PII-related compression risks to Part 13.3. Tagged 3 items in Part 14 (IT confirmations) as REAL-PII BLOCKER — Bedrock enablement, data classification, authorization basis. Added open questions #24–29 covering PII workstream. Added 5 new vocabulary terms.

- **v2.0 (Apr 2026)** — Merged seed context + engineering addendum into single working canon. Replaced original Part 9 (Technical Architecture) with full engineering content. Added engineering parts: Stack/Architecture/Infrastructure (Part 9), Repo Layout (Part 10), Extraction Layer (Part 11), Engine I/O Contract (Part 12). Merged build sequence and demo storyboard into Part 13. Unified glossaries (Part 16). Unified open-questions table (Part 15). Applied LOCKED/DEFAULT/OPEN tagging consistently throughout. Tightened Day 1 morning into critical-path + deferrable lists. Named operational dependency on Lori as a compression risk. Promoted CMA placeholder issue (Part 5.4) to its own section. Added live-vs-cached demo posture (Part 12.4). Added `derivation_method` field to `Fact[T]` schema. Added explicit IT-blocking fallback (Part 14 preamble). Resolved several items from prior open-questions list.

- **v1.0 (Apr 2026)** — Initial seed context. Architecture confirmed Option C (sleeve-blend hybrid). Method 1 (percentile) selected for v1 risk optimization. Steadyhand confirmed as v1 launch context. Six pure Steadyhand sleeves selected as initial universe. MVP demo target: Stages 1→2→3→5.

- **Engineering Addendum v1.0 (Apr 2026)** — Now superseded by this merged document. Stack locked: Django+DRF / React+Vite / Postgres+pgvector / AWS ECS-on-EC2 ca-central-1 / Bedrock for prod LLM / OpenTelemetry+Elastic. Five-layer extraction pipeline architected with temporal Fact[T] schema. Auth phasing locked. RBAC scaffolded Phase 1.

---

*This is the working canon. When this document and the codebase disagree, fix the disagreement the same day — by updating one or the other.*
