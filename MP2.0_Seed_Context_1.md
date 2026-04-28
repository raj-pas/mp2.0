# MP2.0 — Core Context & Build Specification (v1.0)

**Seed file for application + platform development**
**Compiled:** April 2026, post Day-1 of MAT offsite
**Owner:** Fraser Stark (Project Lead) | Mission-Aligned Team: Nafal Butt, Lori Norman, Saranyaraj Rajendran
**Executive Sponsor:** Som Seif, CEO Purpose Investments

---

## How to use this document

This is the single seed file an engineer or AI coding agent should be able to read and understand the MP2.0 product end-to-end: what we're building, why, for whom, with what data, on what theory, under which constraints, and what the MVP must demonstrate.

It is opinionated where the offsite reached alignment, and explicit about what is still open. It is not the memo, not the meeting notes, and not the regulatory bible — it is the working canon that should remain in sync with the codebase.

When this document and the codebase disagree, update one of them the same day.

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

### 1.3 The 4 project goals

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

### 1.5 Initial launch context — Steadyhand

- **Steadyhand** is the launch context for the MVP. It's a Purpose subsidiary, MFDA-registered, with ~3,500–4,000 clients and a small Investment Specialist (IS) team led by Lori Norman.
- Steadyhand has a constrained, well-understood fund lineup, a high-trust client base, and a culture that already over-delivers on advice relative to its regulatory mandate. Ideal for a v1.0.
- After Steadyhand, the next deployment is **Harness** (advisor platform, especially retired clients — Harness Investment Committee has confirmed interest, conditional on sleeves being formally launched as funds with a Purpose PM attached). Eventually: 3rd-party IIROC/CIRO advisors, Partnership Program, Link group plans, and DIY.

---

## PART 2 — THE CONCEPTUAL MODEL

### 2.1 The atomic hierarchy

This was the framing Fraser landed during the offsite morning — call it the "atomic building blocks" model. The system reasons about wealth at four nested levels:

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

### 2.2 The sleeve-blend architecture (Option C — confirmed)

**The foundational architectural decision is Option C: the hybrid sleeve-blend model.**

The analogy is **paint mixing** (Fraser's):
- **Sleeves** = building-block funds (the paints). 8–12 sleeves total. Each sleeve has a clear mandate (e.g., "Canadian large-cap equity," "investment-grade bonds," "cash"). Each sleeve is itself a real, papered fund with a Purpose PM attached.
- **Blend ratios** = personalized mix of sleeves driven by the financial plan (the painting). Every household–goal–account combination produces a unique blend.
- **Atoms-and-molecules**: sleeves are molecules; the underlying holdings (individual securities) are the atoms. Clients/advisors operate at the molecule level. The Macro Insight Layer (see 2.3) operates at the atom level inside each sleeve.

Why this architecture:
- Standardized sleeves give us manageability, consistency across client books, and operational tractability (rebalancing 12 sleeves vs. 1,000 unique portfolios).
- Personalized blends give us the planning-driven personalization that defines MP2.0.
- Sleeves earn trust over time because they have track records, mandates, and PMs — they're real funds, not synthetic constructs.

### 2.3 The Macro Insight Layer

The CIO/strategist function does **not** touch individual client portfolios. It updates the **internals of sleeves** (the underlying holdings) based on macro views — duration calls, sector tilts, currency hedging decisions, factor exposures.

This means there are **two independent update cycles**:
1. **Sleeve internals** — driven by the Macro Insight Layer (probably monthly). Affects every client who holds that sleeve.
2. **Client blend ratios** — driven by changes to the client's plan, life events, or material drift. Affects only that client.

Clients see one allocation. The two cycles run silently underneath.

### 2.4 The Living Financial Plan

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

**MVP demo flow target: Stage 1 → 2 → 3 → 5.** Stage 4 is mocked. Stage 6 is implied via "what happens when X changes" demo branches.

---

## PART 4 — INVESTMENT THEORY & ENGINE MECHANICS

This is the math the offsite locked in for v1. Like the race-car-engine analogy: it's a working engine for v1. We may swap from "gasoline to diesel" later — but it must run now.

### 4.1 Foundation: efficient frontier optimization

For a given universe of sleeve funds, with each sleeve characterized by:
- Expected return (after-fee, net)
- Volatility (annualized standard deviation)
- A correlation matrix across all sleeves

…we compute the **efficient frontier** — the set of portfolios that maximize expected return for each level of volatility (and equivalently, minimize volatility for each level of expected return).

This is Modern Portfolio Theory, applied at the sleeve level. The frontier is a curve in (volatility, return) space. Any blend of sleeves that lands **on** the curve is optimal in the mean-variance sense; anything below is dominated.

**Key mechanic observed in the offsite:** as we vary correlations between sleeves, the *shape* of the frontier changes meaningfully — strongly negatively-correlated sleeves push the frontier up and to the left (more return for less risk). This is why launching a true **bond-only sleeve** matters: today the Steadyhand bond fund (Income Fund) is 75% bonds / 25% equities, which "couples" the bond axis to the equity axis and limits how far we can extend the frontier.

### 4.2 Risk modeling — the composite approach

Where on the frontier should a given client's blend sit?

The risk input is **a composite of two scores**:

1. **Household-level risk score** — derived from the holistic view of the household: income, net worth, investment knowledge, behavioral signals (loss aversion, follow-through, sentiment under volatility), tax sensitivity, attitude to debt, etc.

2. **Goal-level risk score** — specific to *this* goal: how essential is it? (need / want / wish) What's the time horizon? How much variability can the client tolerate on this specific outcome?

Both can start very simple: the goal-level score can be **a single 4- or 5-point question per goal** ("If you missed this target by 30%, what would that mean to you?"). The household-level can be a 3-question composite + behavioral data from notes.

The engine combines these into a single risk number used for portfolio selection on the frontier.

> Worth noting: this is **not** the same as the regulatory KYC risk rating. The KYC score (low / medium / high investment knowledge × time horizon × objective) is a parallel artifact we still maintain because regulators require it. Our optimized portfolio is then **mapped back** to a regulatory risk bucket for compliance reporting (Section 7.4).

### 4.3 Three methods for "where on the frontier" — pick one for v1

The offsite enumerated three valid mathematical approaches. All three were demonstrated; the team should pick one for v1, and the engine should be modular enough to swap.

| Method | What it optimizes | Use it when |
|--------|-------------------|-------------|
| **Percentile maximization** | "Maximize my expected portfolio value at the Nth percentile outcome." E.g., risk-tolerant = 50th, conservative = 5th, ultra-conservative = 1st. | Easiest to explain. Likely v1 default. |
| **Probability of target** | "Maximize the probability that I hit my target $ amount by my target date." | Most goal-native; ties directly to the plan. |
| **Utility function (risk aversion coefficient)** | Evaluates the full distribution of future outcomes, weighting downside more heavily based on a risk-aversion parameter. Most theoretically complete; hardest to explain. | Best long-term answer. Probably v2. |

**Recommendation locked at offsite: start with Method 1 (percentile maximization) for explainability, with Method 2 as a parallel display ("you have an 87% chance of hitting your $200,000 target"). Move to Method 3 in a later iteration.**

### 4.4 Glide path & the cash sleeve as risk-reducer

As a goal nears its target date, the optimal blend should glide toward lower-volatility sleeves — and ultimately toward **cash**. The cash sleeve (currently approximated by Steadyhand Savings/MMF, with ~2.1% expected return and ~0.5% modeled volatility) functions as the "risk-free corner" of the frontier.

In the model, as time-to-goal approaches zero, the optimizer naturally allocates more to cash. The engine should:
- Compute the optimal blend under current time-to-goal
- Compare to current blend
- Trigger rebalancing **only on material drift** (e.g., 3–5% absolute, or on significant client events) — not on every tiny shift. We don't want to trade for the sake of trading, especially given client communication overhead.

### 4.5 Tax-aware optimization (light layer)

A "light tax overlay" is in scope for v1.

- All return inputs are **net of fund fees** (we use the highest fee series as a conservative proxy).
- Account-type awareness: an RRSP and a non-registered account have different after-tax effective returns for the same sleeve. The engine should prefer placing tax-inefficient sleeves (e.g., bonds throwing off interest income) in registered accounts where possible.
- Full tax optimization (capital gains harvesting, attribution rules, in-kind transfers) is **out of MVP scope.**

### 4.6 What the engine does NOT model in v1 — explicit gaps

These are knowingly missing from v1; flag them as v2+ work:

- **Currency / hedging decisions** (hedge ratios, FX overlays). Today buried inside sleeve internals.
- **Factor tilts** (value, growth, momentum, quality). Today emergent from sleeve mandates.
- **Geographic / sector concentration look-through.** A future feature: re-aggregate the underlying atoms across all sleeves the blend holds, and flag concentration risks.
- **External assets** (other-firm holdings, real estate, business equity, private investments). The household reality includes these; the v1 engine treats only what Purpose holds.

The offsite consensus: build v1 with these gaps explicit, then evaluate which to close based on what we observe with real personas.

---

## PART 5 — SLEEVE UNIVERSE

### 5.1 Initial sleeve universe (Steadyhand v1)

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

---

## PART 6 — DATA MODEL & REQUIRED INPUTS

This section is the contract between the intake layer and the engine.

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
  target_amount, target_date
  necessity_score: 1..5                 // wish → want → need
  current_funded_amount
  contribution_plan: { monthly, annual, lump_sum_dates }
  account_allocations: GoalAccountLink[]  // many-to-many
  goal_risk_score: int                   // see 4.2
  status: on_track | watch | off_track
  notes
}

GoalAccountLink {
  goal_id, account_id
  allocated_amount   // dollars of this account earmarked for this goal
  allocated_pct      // alternative representation
}
```

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
  household_score: int                  // 1-10, composite of:
    - investment_knowledge
    - income_net_worth_band
    - behavioral_loss_aversion
    - behavioral_follow_through
    - sentiment_under_volatility
    - tax_sensitivity

  goals: { goal_id -> goal_risk_score }  // 1-5, single question per goal
}
```

The engine's risk input for a given goal is `combine(household_score, goal_risk_score)`. Default combination function for v1: a documented weighted blend; the weights are a tunable parameter we expect to refine.

### 6.6 Behavioral / soft data — captured from meeting notes

This is where the AI extraction layer earns its keep. From unstructured notes, extract:

- Communication style preferences (numbers-driven, visual, narrative, goal-focused)
- Reaction history (panicked in 2020? steady through 2022? called frequently?)
- Follow-through pattern (acts on advice / doesn't)
- Topics they care about (legacy, lifestyle, security, optionality)
- Sensitive topics to handle carefully (recent loss, family conflict, etc.)

These feed two systems:
1. The household risk score (some of these are inputs).
2. The reporting layer — to personalize tone and emphasis (see Section 8).

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

### 7.4 Translating MP2.0 portfolios back to a compliance risk rating

The optimizer outputs a continuous, multivariate blend. Compliance wants a discrete bucket (low / medium / high) at both the **account** and **client** level.

The system must include a deterministic mapping function:

```
risk_rating(blend) -> {low, medium, high}
```

Likely based on the blend's modeled volatility band, equity %, and time horizon. This function must be explainable, auditable, and consistent across clients. Lori + team's offsite action item.

### 7.5 Client approval & documentation

For any portfolio recommendation MP2.0 generates:

- Must be **validated by an advisor / IS** before presentation.
- Must be **approved by the client** before execution (recorded verbally or via DocuSign).
- Must be **documented in CRM** with disclosure of risk level and any deviation from the household profile.
- Audit log must capture inputs → engine output for regulatory review.

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

The novel insight Fraser pushed: report **retrospectively** as well as prospectively. Plans are usually only forward-looking. Showing a client "you set this goal in January, you were 90% likely; after market moves and contributions, you're now 91% likely" is psychologically empowering and builds trust.

### 8.3 AI-personalized updates

The reporting layer should generate **personalized** updates — not generic newsletters.

- Tone and format adapt to the client's communication preferences (numbers / visual / narrative — captured in Section 6.6).
- Content is grounded in the client's actual plan and portfolio, not generic market commentary.
- Determinism in the workflow is critical: AI generates *within* a structured template, not from scratch. Static-or-configurable intake → deterministic engine → AI-styled output. The output should never include numbers that didn't come from the engine.
- Frequency: quarterly automated, plus event-triggered (large move, life event, goal milestone hit/missed).

### 8.4 Behavioral bucketing for tone

Cluster clients by their captured behavioral profile — examples:

- **Numbers-driven** → lead with the math, charts, probabilities.
- **Visual** → lead with the goal-progress dashboard.
- **Reassurance-seeking** → lead with "you're on track" framing, then optional detail.
- **Curious / explorer** → expose the scenario tools and let them play.

The same underlying truth is presented in different shapes.

### 8.5 The "discussion of how the portfolio supports the goal"

A specific artifact the offsite called out: at the moment the IS proposes a blend, the system should produce a **plain-language narrative** explaining *why this blend supports this goal* — at the goal, account, and household level.

It's not really a report. It's the language the IS uses to talk to the client. Pyramidal: short version → expand if asked → expand again. The IS picks the level of depth.

### 8.6 Money-in-motion / event detection

The portal should detect significant events — address change, large deposit, large withdrawal — and proactively prompt a goal/plan review. Today this is reactive. In MP2.0 it's a Stage-6 trigger.

---

## PART 9 — TECHNICAL ARCHITECTURE

### 9.1 Stack

- **Backend:** Python + Django, modular service architecture.
- **Frontend (MVP):** simple web UI; iterate from the Q4 hackathon prototype (https://purpose-portfolio2-0.lovable.app/) where useful.
- **Data:** local DB for v1 (a few personas), with mock APIs and clear interface boundaries to swap to production data sources later.
- **AI/LLM:** Anthropic (Claude) for extraction and natural-language generation, with deterministic guardrails.
- **No production-scale infra in MVP.** Explicitly out of scope: AWS deployment, access control, Croesus integration, custodian APIs, Conquest API integration.

### 9.2 Engine layers

```
┌─────────────────────────────────────────────────────────┐
│ INTAKE LAYER                                             │
│  - Static/configurable intake forms (deterministic)      │
│  - AI extraction from notes (LLM, with human review)     │
│  - Output: structured data per Part 6 schema             │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ PLAN LAYER                                               │
│  - Goal modeling, cash flow, scenario, Monte Carlo       │
│  - Output: per-goal target $, time horizon, prob curves  │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ RISK LAYER                                               │
│  - Household composite                                    │
│  - Goal-level scoring                                     │
│  - Combined risk per goal                                 │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ OPTIMIZATION ENGINE                                      │
│  - Sleeve universe in (return, vol, correlation)         │
│  - Efficient frontier computation                         │
│  - Selection on frontier per chosen method (4.3)         │
│  - Account-level constraints (regulatory caps)            │
│  - Tax-light overlay                                      │
│  - Output: blend per (household, goal, account)          │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ COMPLIANCE LAYER                                         │
│  - Map blend → regulatory risk rating (low/med/high)     │
│  - Validate against KYC + account objective + horizon    │
│  - Flag drift / required client approvals                │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ EXPLANATION / REPORTING LAYER                            │
│  - Generate plain-language rationale (LLM, templated)    │
│  - Goal-progress visualizations                          │
│  - Account/household roll-up                             │
│  - Behavioral-bucketed tone                              │
└─────────────────────────────────────────────────────────┘

           ┌────────────────────────────────────────┐
           │ AUDIT LOG (cross-cutting)              │
           │  Every decision is traceable:          │
           │   inputs → engine state → output       │
           └────────────────────────────────────────┘
```

### 9.3 Explainability & audit logging — non-negotiable

Every output must be traceable. The audit log captures:
- Input data state at the time of optimization
- Sleeve assumptions (return, vol, correlation) used
- Method selected and parameters
- Output blend and the path through the frontier
- Compliance mapping result

This serves three purposes:
1. **Regulatory defense** — when a client or compliance asks "why this allocation?" we have the trace.
2. **Debugging** — when the engine produces something weird, we can audit why.
3. **Learning** — patterns in the audit log feed the v2 engine improvements.

### 9.4 The determinism / AI-creativity balance

A core insight from the offsite:

- **Workflows must be deterministic.** Don't dynamically generate intake forms. Don't let the LLM "decide" what to ask. The required attribute set must always be captured, every time.
- **Inputs (intelligence) is where AI shines.** Routing between determined steps; extracting structure from unstructured notes; rephrasing for the client.
- Different LLMs behave differently — Claude tends to follow nuanced instructions; some other models follow them more rigidly. Build for the variability.

This principle applies throughout: deterministic skeleton, AI-powered flesh.

### 9.5 Modularity & scalability

For v1, we run a few personas in a local DB. We do not solve scale.

But the architecture must allow:
- Plug in a different planning tool (Conquest, Adviice, Planworth, direct intake) at the Plan Layer boundary
- Plug in different sleeve universes (Steadyhand → Harness → Partnership) at the Optimization Engine boundary
- Plug in different optimization methods (Section 4.3) without rewriting the layer
- Replace mock APIs with production APIs cleanly

Avoid the "Trucon problem" — a single rigid integration point that brings the whole platform down when it fails.

### 9.6 Out of scope for MVP — explicit list

These are not v1. Don't build them; mock them or skip.

- Custodian / brokerage API integration (Stage 4 execution)
- Conquest deep API integration (file-based or manual entry is fine)
- Croesus integration (manually populate test data)
- Production deployment, access control, multi-tenant infra
- Real-time market data
- Mobile native apps
- ChatGPT/Claude app-store distribution
- DIY direct-to-investor flow (Steadyhand-IS-mediated only)
- Full tax optimization (capital gains harvesting, attribution)

### 9.7 The race-car-engine analogy

Fraser's framing for the team: **we're building a working race car. The first engine runs on gasoline. We may swap to diesel later. That's fine — but the car must run now.** Don't let perfection or future-proofing stall the v1 demo.

---

## PART 10 — MVP SCOPE & DEMO FLOW

### 10.1 The demo target

By the end of the offsite (3 days), the team produces a **working application** that mechanically demonstrates the loop:

**Stage 1 → Stage 2 → Stage 3 → Stage 5**

…for at least one persona, and ideally three to five, including a "happy path" and edge cases.

Live customer demo on Friday after the offsite. (Som's design: tying the team to a live demo creates urgency.)

### 10.2 The demo narrative (storyboard)

```
1. INTAKE (2 minutes)
   "Meet Sandra and Mike Chen. Mike is 62, Sandra is 58.
    They have $1.2M with us across RRSPs, TFSAs, and a non-reg.
    They want to retire in 4 years, and their daughter Emma is going
    to university next year — they need ~$80K for that."
   → Show structured intake or extraction from notes.

2. THE PLAN (3 minutes)
   → Show the goals laid out: Retirement (need), Emma's education (need),
     and their stretch goal: a ski cabin (wish).
   → Show necessity scoring per goal.
   → Show household risk profile derived from inputs.

3. THE BLEND (5 minutes)
   → Click "compute portfolio."
   → Show the efficient frontier with the chosen point.
   → Show the resulting blend across the six Steadyhand sleeves.
   → Show how it varies by goal — Emma's education is short-horizon
     (mostly cash + Income); Retirement is medium-term (balanced);
     Ski cabin is small + 5+ years (more equity).
   → Show how it rolls up to account-level allocations.
   → Show the compliance risk rating mapping.

4. THE EXPLANATION (3 minutes)
   → "Here's how to talk to Sandra and Mike about why this blend
     supports their goals." Plain language, three depth levels.

5. THE OUTCOME (3 minutes)
   → Goal progress dashboard.
   → "Sandra and Mike have a 91% chance of retiring at their target
     spending. Emma's education is fully funded. Ski cabin is at 64%
     probability — let's discuss."
   → Show "what if" — drag the retirement date forward 1 year,
     watch the probabilities update.

6. THE LOOP (2 minutes)
   → "Mike just got a $40K bonus. Update plan. Watch the blend adjust
     and the goal probabilities improve."
```

### 10.3 Test personas — five synthetic clients for v1

Lori will provide redacted real-client examples; in parallel, generate Claude-authored synthetic personas for breadth and for testing edge cases. The five v1 personas should span:

| Persona | Profile sketch | What it tests |
|---------|---------------|---------------|
| **1. Pre-retiree couple** | 60s, ~$1.5M, retiring in 5 years, multiple goals (retirement income, leave estate to kids, one big trip) | Multi-goal household, glide path, income vs. growth blend |
| **2. Young professional, single** | 32, ~$120K, single goal (house in 4 years), high savings rate | Single goal, short horizon, growth-leaning client with conservative goal |
| **3. Mid-career family** | 45 + 43, two kids, ~$400K, retirement + RESPs + paying down mortgage | Many goals, RESP tax mechanics, balanced blend |
| **4. Recently retired** | 68, ~$2M, drawdown phase, leaves a legacy goal | Decumulation, LPF natural fit, tax-efficient withdrawal |
| **5. Post-windfall** | 50, just inherited $500K, no formal plan, anxious | Money-in-motion, behavioral cautious, plan-from-scratch flow |

The Birth-of-Child / Job-Loss / Inheritance / Retirement / Divorce / End-of-Life / House-Purchase / Post-Secondary checklists already in the project provide event-trigger scenarios for testing the Stage-6 loop.

### 10.4 Out-of-scope-for-demo (explicit)

- No real custodian connection.
- No real-time prices; use snapshot data.
- No real client PII — Daffy Duck names where needed.
- No mobile UI.
- No actual order placement.

---

## PART 11 — OPEN QUESTIONS & DECISIONS PENDING

The offsite locked many things; these remain open. Owner column reflects offsite assignments.

| # | Open question | Owner | Notes |
|--:|--------------|-------|-------|
| 1 | Final method for risk-on-frontier (percentile / probability / utility) — confirm Method 1 for v1 | Saranyaraj + Fraser | Recommendation: percentile, with probability as a parallel display |
| 2 | Specific weighting in the household × goal risk composite | Team | Document the function, parameterize for tuning |
| 3 | Compliance risk-rating mapping function — exact thresholds | Lori + Saranyaraj | Translate continuous blend → low/med/high |
| 4 | Bond-only sleeve launch path | Salman + Tom | Highest-leverage product-side gap |
| 5 | Whether and how to model Founders Fund / Builders Fund (active layer) | Saranyaraj | v1: leave out; toggle later |
| 6 | Household-level risk handling when accounts blend differently | Team | The "shade of gray" averaging problem — currently sketched, not solved |
| 7 | API integration with Conquest — feasibility for v2 | Saranyaraj | v1: file/manual entry |
| 8 | Goal-decomposition model — turning narrative goal ("retire well") into fungible $ targets | Team | Wants/needs/wishes split is the v1 approach |
| 9 | Reporting / portal scope — what does Andrew's team build first | Andrew + team | Out of MAT scope but blocking for full demo |
| 10 | Behavioral-bucket schema — how many buckets, how to assign | Lori + Saranyaraj | AI agent prototype already running on meeting notes |
| 11 | When does drift trigger rebalance — exact thresholds | Team | Today: 3–5% off, or material event |
| 12 | Whether goal-level questionnaire is one question or three | Lori + Fraser | Lean toward one for v1 |
| 13 | How external (non-Purpose) assets enter the household view | Team | v1: capture, don't optimize |
| 14 | Testing protocol — internal IS feedback Wednesday + live customer Friday | Lori + Saranyaraj | Confirmed |

---

## PART 12 — GLOSSARY & VOCABULARY

Use these terms precisely. Inconsistency confuses the team and the build.

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
| **Household risk score** | Composite score capturing investment knowledge, behavior, capacity. |
| **Goal risk score** | Per-goal: how essential is this specific goal? |
| **Wants and needs (and wishes)** | Goal categorization. Some constructs use 3 levels; we currently merge to 2. |
| **Whole-portfolio fund** | A multi-asset fund-of-funds, like Founders or PACF. Distinct from a sleeve. |
| **MAT** | Mission-Aligned Team — the 5-person offsite group. |
| **One Purpose** | Internal vision: integrated wealth experience across Purpose's businesses. |
| **CRM 3** | Canadian fee/disclosure regulation requiring full FER + advisor fee disclosure. |
| **KYC** | Know-Your-Client; mandatory regulatory data set. |
| **MFDA / CIRO** | Canadian regulator (MFDA terminology still used operationally). |
| **CFP / QAFP** | Designations required to provide comprehensive financial planning. Steadyhand IS team does not (currently) hold these. |
| **IS** | Investment Specialist — Steadyhand's client-facing role. |
| **LPF** | Longevity Pension Fund — Purpose's flagship retirement income product. |
| **Steadyhand** | Purpose subsidiary; MP2.0 v1 launch context. |
| **Harness** | Purpose advisor platform; v2 deployment target. |
| **Link** | Purpose direct/group plans platform. |
| **Partnership Program** | Purpose's IA consulting program. |

---

## PART 13 — REFERENCE MATERIALS

Source documents available in the project:

| Document | Use |
|----------|-----|
| **The Purpose Memo — MP2.0 (Sep 2024)** | Fraser's foundational memo. Opinionated; thinking has evolved. |
| **MP2.0 Offsite prep deck** | Logistics, objectives, prep |
| **MP2.0 MAT Invitation Extract** | Original mandate and design principles |
| **Day 1 morning + afternoon transcripts and AI notes** | Source of most of this seed file |
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

## DOCUMENT VERSIONING

This file should be revised whenever a material decision changes. Track changes inline; archive prior versions.

- **v1.0 (Apr 2026)** — Initial seed, post Day-1 of MAT offsite. Architecture confirmed Option C (sleeve-blend hybrid). Method 1 (percentile) selected for v1 risk optimization. Steadyhand confirmed as v1 launch context. Six pure Steadyhand sleeves selected as initial universe. MVP demo target: Stages 1→2→3→5.

---

*This is the working canon. When this document and the codebase disagree, fix the disagreement the same day — by updating one or the other.*
