# MP2.0 — Working Canon (v2.0)

**Merged seed context + engineering addendum**
**Compiled:** April 2026, post Day-1 of MAT offsite + tech-stack working session
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
13. MVP scope, build sequence, demo flow
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

**MVP demo flow target: Stage 1 → 2 → 3 → 5.** **[LOCKED]** Stage 4 is mocked. Stage 6 is implied via "what happens when X changes" demo branches.

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

### 4.2 Risk modeling — the composite approach **[LOCKED]**

Where on the frontier should a given client's blend sit?

The risk input is **a composite of two scores**:

1. **Household-level risk score** — derived from the holistic view of the household: income, net worth, investment knowledge, behavioral signals (loss aversion, follow-through, sentiment under volatility), tax sensitivity, attitude to debt, etc.

2. **Goal-level risk score** — specific to *this* goal: how essential is it? (need / want / wish) What's the time horizon? How much variability can the client tolerate on this specific outcome?

Both can start very simple: the goal-level score can be **a single 4- or 5-point question per goal** ("If you missed this target by 30%, what would that mean to you?"). The household-level can be a 3-question composite + behavioral data from notes.

The engine combines these into a single risk number used for portfolio selection on the frontier.

> **Note:** this is **not** the same as the regulatory KYC risk rating. The KYC score (low / medium / high investment knowledge × time horizon × objective) is a parallel artifact we still maintain because regulators require it. Our optimized portfolio is then **mapped back** to a regulatory risk bucket for compliance reporting (Section 7.4).

### 4.3 Three methods for "where on the frontier" **[LOCKED — Method 1 for v1]**

The offsite enumerated three valid mathematical approaches. All three were demonstrated. Method 1 is the v1 default; the engine is modular enough to swap.

| Method | What it optimizes | Use it when |
|--------|-------------------|-------------|
| **1. Percentile maximization** *(v1 default)* | "Maximize my expected portfolio value at the Nth percentile outcome." E.g., risk-tolerant = 50th, conservative = 5th, ultra-conservative = 1st. | Easiest to explain. v1 default. |
| **2. Probability of target** *(parallel display)* | "Maximize the probability that I hit my target $ amount by my target date." | Most goal-native; ties directly to the plan. Show alongside Method 1 for v1. |
| **3. Utility function (risk aversion coefficient)** | Evaluates the full distribution of future outcomes, weighting downside more heavily based on a risk-aversion parameter. Most theoretically complete; hardest to explain. | Best long-term answer. v2. |

### 4.4 Glide path & the cash sleeve as risk-reducer **[LOCKED]**

As a goal nears its target date, the optimal blend should glide toward lower-volatility sleeves — and ultimately toward **cash**. The cash sleeve (currently approximated by Steadyhand Savings/MMF, with ~2.1% expected return and ~0.5% modeled volatility) functions as the "risk-free corner" of the frontier.

In the model, as time-to-goal approaches zero, the optimizer naturally allocates more to cash. The engine should:
- Compute the optimal blend under current time-to-goal
- Compare to current blend
- Trigger rebalancing **only on material drift** (e.g., 3–5% absolute, or on significant client events) — not on every tiny shift. We don't want to trade for the sake of trading, especially given client communication overhead.

### 4.5 Tax-aware optimization (light layer) **[DEFAULT]**

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

Sleeve return / vol / correlation inputs need a defensible source: Goldman, JPM, Basinger (Purpose CIO) views, or composite. This is more consequential than its position implies — placeholder CMAs produce placeholder portfolios, which means the demo shows placeholder math. **Owner: Saranyaraj + Fraser. Resolution required before Day 2 morning of the build.** If unresolved, the demo must explicitly say "illustrative numbers" upfront.

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

Novel insight Fraser pushed: report **retrospectively** as well as prospectively. Plans are usually only forward-looking. Showing a client "you set this goal in January, you were 90% likely; after market moves and contributions, you're now 91% likely" is psychologically empowering and builds trust.

### 8.3 AI-personalized updates

The reporting layer should generate **personalized** updates — not generic newsletters.

- Tone and format adapt to the client's communication preferences (numbers / visual / narrative — captured in Section 6.6).
- Content is grounded in the client's actual plan and portfolio, not generic market commentary.
- Determinism in the workflow is critical: AI generates *within* a structured template, not from scratch. Static-or-configurable intake → deterministic engine → AI-styled output. **The output should never include numbers that didn't come from the engine.**
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

### 9.2 Auth phasing **[LOCKED]**

Three phases, OIDC throughout so transitions are config swaps, not rewrites.

| Phase | Mechanism | Trigger to advance |
|---|---|---|
| **1 — MVP / pilot** | Django built-in auth, username + password, single hardcoded admin to start | First real advisor users beyond core team |
| **2 — Internal scale** | Microsoft Entra SSO via OIDC | Broader Purpose advisor rollout |
| **3 — Broader platform** | Auth0-backed user pool (OIDC) | DIY investors, third-party advisors, Advisor Center |

**Permission framework (RBAC) is built in Phase 1, even if all checks pass.** Retrofitting authorization across every endpoint is the most error-prone refactor in any web app. Build the structure now; tighten the rules per phase.

User model is minimal and OIDC-ready: email-as-identity, no auth-method-specific fields. SSO transitions don't touch the user model.

### 9.3 Data classification defaults **[DEFAULT]**

Purpose has no published data classification policy yet. The build proceeds with safe defaults and documents the implicit classification:

- **Encryption at rest:** RDS with customer-managed KMS key; S3 SSE-KMS; EBS encrypted.
- **TLS 1.2+ in transit everywhere:** ALB to client, app to RDS, app to external APIs.
- **Resource tagging:** every resource tagged `mp20-data-sensitivity={pii|internal|public}`. When IT publishes formal classification, inventory is ready.
- **Logging discipline:** PII never logged. Custom logger wraps stdlib with auto-redaction for SIN, account numbers, emails. Painful to retrofit because old logs persist.
- **Architecture doc note:** "Data classification policy TBD — current defaults assume client PII tier; revisit when Purpose IT publishes formal classification."

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

EC2 single instance with Caddy reverse proxy + Docker Compose, or Render.com free tier. Public URL with HTTPS. For demo + advisor testing on Wednesday and beyond. **Demoable from any browser within first week — laptop demos fail at offsite venues (wifi, sleep, battery, stale fixtures).**

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

The extraction layer is **in MVP scope and load-bearing for the demo**. **Owner: Raj.** Source data: real Croesus exports manually copied by Lori into `personas/<name>/raw/` — no API integration in MVP.

> **Operational dependency:** the Croesus → file-drop pipeline depends on Lori as a person. Identify a backup who can copy files in her absence; have at least one fully synthetic persona that works without any real-data dependency, so the demo is viable even if real data isn't available the morning of.

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

The most important screen in the demo. Side-by-side:

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

Even with redacted/Daffy-Duck-named clients, original Croesus exports may contain real PII Lori hasn't scrubbed. Rules:

- Raw files in `personas/<name>/raw/` are gitignored when sourced from real client material
- Scrub-pass utility flags potential PII (emails, SIN patterns, account numbers) before files touch any committed location
- Synthetic personas may have raw files committed; real-derived personas may not

---

## PART 12 — ENGINE I/O CONTRACT

### 12.1 Locked entry point **[LOCKED]**

```python
def optimize(
    household: Household,
    sleeve_universe: list[Sleeve],
    method: OptimizationMethod = "percentile",
    constraints: Constraints | None = None,
) -> EngineOutput:
    ...
```

`EngineOutput` contains:
- Per-goal blends (sleeve weight vector)
- Household roll-up (aggregated weighted blend)
- Fan chart data (10th / 50th / 90th percentile portfolio value over horizon)
- Compliance risk rating per account + household (low/med/high)
- Audit trace (sleeve assumptions used, frontier coordinates, method + params, model version)

### 12.2 Schemas live in engine/

Pydantic models for `Household`, `Person`, `Goal`, `GoalAccountLink` (many-to-many — critical), `Account`, `Holding`, `RiskInput`, `Sleeve`, `Allocation`, `EngineOutput`, `EngineRun`. Web layer imports from `engine.schemas`; engine never imports from web.

### 12.3 The Claude artifact handoff process

Engine code arriving from Fraser/Nafal's Claude artifacts gets:

1. Wrapped in the I/O contract (Pydantic in, Pydantic out)
2. Test suite written against the persona fixtures
3. Reviewed for things prototypes skip: input validation, edge cases, numerical stability, empty-input behavior

Artifact code is treated as reference implementation, not production code. Re-implemented inside the engine package's conventions. Few hours per module; saves the class of bug where the prototype worked on three test cases and breaks on the fourth.

### 12.4 Demo posture: live vs. cached

When advisors poke at the staging URL on Wednesday, what's interactive vs. what's pre-computed?

- **Interactive (live engine call):** intake review, what-if sliders for the demo persona, "Generate portfolio" button on a fresh run.
- **Pre-computed (cached for the five personas):** initial engine outputs, fan charts, baseline goal probabilities, fast-forward future states.

Engine + extraction calls are LLM-bound and slow. Sub-second response when clicking around requires caching. Build with this in mind from Day 1; don't surprise yourselves on Wednesday.

---

## PART 13 — MVP SCOPE, BUILD SEQUENCE, DEMO FLOW

### 13.1 The demo target **[LOCKED]**

By the end of the offsite (3 days), the team produces a **working application** that mechanically demonstrates the loop:

**Stage 1 → Stage 2 → Stage 3 → Stage 5**

…for at least one persona, and ideally three to five, including a "happy path" and edge cases.

Live customer demo on Friday after the offsite. (Som's design: tying the team to a live demo creates urgency.)

### 13.2 Build sequence (compressed 2-day MVP) **[LOCKED]**

The day-1-morning list is aggressive. **If the schedule slips on Day 1, the demo is at risk because every subsequent day depends on it.** Buffer is built into the structure below: *critical path* items must land before lunch; *important but deferrable* items can move to Day 1 evening or Day 2 morning if needed.

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

#### Day 2 afternoon — demo loop

- Outcomes view: plan-progress visualization (Recharts)
- Fast-forward button: loads pre-baked future state, shows drift, triggers rebalance recommendation view
- LLM-generated meeting prep: client state → prose paragraph for advisor
- Polish three demo paths end-to-end
- Final rehearsal on staging URL

### 13.3 Compression risks (named) **[LOCKED]**

- **Croesus export format unknown until Lori provides one.** Get one real meeting note before writing extraction prompts. 30 minutes of reading saves hours of building against assumptions.
- **Engine code cleanliness unknown.** If Fraser/Nafal hand a clean function, integration is 30 minutes. If a Jupyter notebook with execution-order dependencies, half a day of refactoring. Read the code Day 1 evening.
- **Auth shortcuts leak.** Calendar reminder for Monday after MVP: "real auth or this thing doesn't get more users." The longer hardcoded auth lives, the more code gets written assuming it.
- **Lori-as-single-point-of-failure for data pipeline.** Identify a backup; ensure at least one fully synthetic persona is end-to-end functional without real-data dependency.
- **CMA placeholder masquerading as real numbers.** If Part 5.4 unresolved by Day 2 morning, demo narrative must explicitly say "illustrative numbers."
- **Staging URL flakiness.** Half a day of deploy setup pays back ten-fold; laptop demos at offsite venues fail.

### 13.4 Parallel work split

| Person | Owns |
|---|---|
| **Raj** | Repo scaffold, Django + DRF, extraction pipeline, engine integration |
| **[OPEN — frontend-comfortable person, named before offsite kickoff]** | React app, screens, Recharts visualizations |
| **Lori** | Persona selection, sleeve universe data, demo narrative, "what good looks like" |
| **Fraser / Nafal** | Optimizer code is integration-ready before Day 2 morning |

Roughly halves wall-clock if handoffs are clean.

### 13.5 Demo narrative — Sandra & Mike Chen storyboard

The eight-segment storyboard drives what gets built. Every screen serves a specific minute. Everything else is post-MVP.

```
1. INTAKE (2 minutes)
   "Meet Sandra and Mike Chen. Mike is 62, Sandra is 58.
    They have $1.2M with us across RRSPs, TFSAs, and a non-reg.
    They want to retire in 4 years, and their daughter Emma is going
    to university next year — they need ~$80K for that."
   → Upload Croesus folder → extraction renders facts with sources.

2. REVIEW + APPROVE (2 minutes)
   → Advisor reviews extracted facts in Layer 5 review UI.
   → Approves. Writes consolidated ClientState.

3. THE PLAN (3 minutes)
   → Goals laid out: Retirement (need), Emma's education (need),
     stretch goal: a ski cabin (wish).
   → Necessity scoring per goal. Household risk profile.

4. THE BLEND (5 minutes)
   → Click "compute portfolio."
   → Efficient frontier with the chosen point.
   → Resulting blend across the six Steadyhand sleeves.
   → How it varies by goal — Emma's education is short-horizon
     (mostly cash + Income); Retirement is medium-term (balanced);
     Ski cabin is small + 5+ years (more equity).
   → Roll-up to account-level allocations.
   → Compliance risk rating mapping.

5. THE EXPLANATION (3 minutes)
   → "Here's how to talk to Sandra and Mike about why this blend
     supports their goals." Plain language, three depth levels.

6. THE OUTCOME (3 minutes)
   → Goal progress dashboard.
   → "Sandra and Mike have a 91% chance of retiring at their target
     spending. Emma's education is fully funded. Ski cabin is at 64%
     probability — let's discuss."
   → Fan chart visualization.

7. WHAT-IF (2 minutes)
   → Drag the retirement date forward 1 year, watch probabilities update.

8. THE LOOP (2 minutes)
   → "Mike just got a $40K bonus. Update plan. Watch the blend adjust
     and the goal probabilities improve."
```

### 13.6 Test personas — five synthetic clients for v1

Lori will provide redacted real-client examples; in parallel, generate Claude-authored synthetic personas for breadth and for testing edge cases. The five v1 personas should span:

| Persona | Profile sketch | What it tests |
|---------|---------------|---------------|
| **1. Pre-retiree couple (Sandra & Mike Chen)** | 60s, ~$1.5M, retiring in 5 years, multiple goals (retirement income, leave estate to kids, one big trip) | Multi-goal household, glide path, income vs. growth blend. **Demo persona — fully synthetic, no real-data dependency.** |
| **2. Young professional, single** | 32, ~$120K, single goal (house in 4 years), high savings rate | Single goal, short horizon, growth-leaning client with conservative goal |
| **3. Mid-career family** | 45 + 43, two kids, ~$400K, retirement + RESPs + paying down mortgage | Many goals, RESP tax mechanics, balanced blend |
| **4. Recently retired** | 68, ~$2M, drawdown phase, leaves a legacy goal | Decumulation, LPF natural fit, tax-efficient withdrawal |
| **5. Post-windfall** | 50, just inherited $500K, no formal plan, anxious | Money-in-motion, behavioral cautious, plan-from-scratch flow |

The Birth-of-Child / Job-Loss / Inheritance / Retirement / Divorce / End-of-Life / House-Purchase / Post-Secondary checklists already in the project provide event-trigger scenarios for testing the Stage-6 loop.

### 13.7 Out-of-scope-for-demo (explicit)

- No real custodian connection.
- No real-time prices; use snapshot data.
- No real client PII in committed code — Daffy Duck names where needed.
- No mobile UI.
- No actual order placement.

---

## PART 14 — ITEMS TO CONFIRM WITH PURPOSE IT

Before production deployment, get explicit answers. **If any item blocks Day 1, the build proceeds in a personal AWS sandbox with a clear migration path documented.**

1. ECS namespace / IAM boundary / tagging convention for MP2.0 inside the existing AWS account
2. Federation pattern: Entra → AWS SSO via SAML, or OIDC, or other
3. Bedrock enablement: turned on in the org, or requires Service Control Policy change
4. Data classification tier for client PII; storage and encryption requirements that flow from it
5. Existing logging/observability stack: Elastic only, or also Datadog/Splunk; where audit logs need to be queryable
6. Maintenance windows on the shared ECS-EC2 cluster (avoid demo-time node drains)
7. Whether MP2.0 CI/CD can deploy autonomously or needs platform team approval per change

---

## PART 15 — OPEN QUESTIONS & DECISIONS PENDING

| # | Open question | Owner | Status |
|--:|--------------|-------|--------|
| 1 | Final method for risk-on-frontier (percentile / probability / utility) — confirmed Method 1 for v1, Method 2 as parallel display | Saranyaraj + Fraser | LOCKED for v1 |
| 2 | Specific weighting in the household × goal risk composite | Team | OPEN — document the function, parameterize for tuning |
| 3 | Compliance risk-rating mapping function — exact thresholds | Lori + Saranyaraj | OPEN |
| 4 | Bond-only sleeve launch path | Salman + Tom | OPEN — highest-leverage product-side gap |
| 5 | Whether and how to model Founders Fund / Builders Fund (active layer) | Saranyaraj | LOCKED — leave out for v1; toggle later |
| 6 | Household-level risk handling when accounts blend differently | Team | OPEN — the "shade of gray" averaging problem |
| 7 | API integration with Conquest — feasibility for v2 | Saranyaraj | OPEN — v1 uses file/manual entry |
| 8 | Goal-decomposition model — turning narrative goal ("retire well") into fungible $ targets | Team | DEFAULT — wants/needs/wishes split is the v1 approach |
| 9 | Reporting / portal scope — what does Andrew's team build first | Andrew + team | OPEN — out of MAT scope but blocking for full demo |
| 10 | Behavioral-bucket schema — how many buckets, how to assign | Lori + Saranyaraj | OPEN — AI agent prototype already running on meeting notes |
| 11 | When does drift trigger rebalance — exact thresholds | Team | DEFAULT — 3–5% off, or material event |
| 12 | Whether goal-level questionnaire is one question or three | Lori + Fraser | DEFAULT — lean toward one for v1 |
| 13 | How external (non-Purpose) assets enter the household view | Team | DEFAULT — v1 captures, doesn't optimize |
| 14 | Testing protocol — internal IS feedback Wednesday + live customer Friday | Lori + Saranyaraj | LOCKED |
| 15 | Capital market assumptions source for sleeve return/vol/correlation inputs | Saranyaraj + Fraser | OPEN — required before Day 2 morning |
| 16 | Real meeting note shape (templated vs freeform, length, structure, date conventions) | Lori → Raj | OPEN — get one real note before finalizing extraction prompts |
| 17 | Sleeve numerical inputs (real vs placeholder) for v1 | Saranyaraj + Nafal | OPEN — engine can stub initially |
| 18 | Optimizer code handoff timing from Fraser/Nafal artifacts | Fraser, Nafal → Raj | OPEN — read Day 1 evening |
| 19 | PDF rendering library for client outputs (WeasyPrint, ReportLab, headless Chrome) | Raj | DEFAULT — defer to week 2 |
| 20 | Fast-forward simulator: pre-baked future states or live re-projection | Team | DEFAULT — pre-baked acceptable for demo |
| 21 | Reconciliation strategy beyond most-recent-wins | Team | OPEN — post-MVP refinement |
| 22 | Frontend-comfortable person assignment for parallel build | Team | OPEN — name before offsite kickoff |
| 23 | Lori's backup for file-pipeline operational dependency | Lori + team | OPEN — name before offsite kickoff |

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

- **v2.0 (Apr 2026)** — **Merged seed context + engineering addendum into single working canon.** Replaced original Part 9 (Technical Architecture) with full engineering content. Added engineering parts: Stack/Architecture/Infrastructure (Part 9), Repo Layout (Part 10), Extraction Layer (Part 11), Engine I/O Contract (Part 12). Merged build sequence and demo storyboard into Part 13. Unified glossaries (Part 16). Unified open-questions table (Part 15). Applied LOCKED/DEFAULT/OPEN tagging consistently throughout. Tightened Day 1 morning into critical-path + deferrable lists. Named operational dependency on Lori as a compression risk. Promoted CMA placeholder issue (Part 5.4) to its own section. Added live-vs-cached demo posture (Part 12.4). Added `derivation_method` field to `Fact[T]` schema. Added explicit IT-blocking fallback (Part 14 preamble). Resolved several items from prior open-questions list.

- **v1.0 (Apr 2026)** — Initial seed context. Architecture confirmed Option C (sleeve-blend hybrid). Method 1 (percentile) selected for v1 risk optimization. Steadyhand confirmed as v1 launch context. Six pure Steadyhand sleeves selected as initial universe. MVP demo target: Stages 1→2→3→5.

- **Engineering Addendum v1.0 (Apr 2026)** — Now superseded by this merged document. Stack locked: Django+DRF / React+Vite / Postgres+pgvector / AWS ECS-on-EC2 ca-central-1 / Bedrock for prod LLM / OpenTelemetry+Elastic. Five-layer extraction pipeline architected with temporal Fact[T] schema. Auth phasing locked. RBAC scaffolded Phase 1.

---

*This is the working canon. When this document and the codebase disagree, fix the disagreement the same day — by updating one or the other.*
