---
title: MP2.0 — product brief
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
status: living
audience: Internal Purpose — Som, Fraser, Lori, leadership, new hires
update_when: The four locked project goals shift, the AUM/business
  case figures change, the pilot status changes materially (new tag,
  cohort expansion, off-ramp), the 8 success metrics get re-locked,
  or the Mission-Aligned Team composition changes.
---

# MP2.0 — product brief

**MP2.0 is Purpose Investments' bet that the next decade of advisor
value will come from integrated planning, not from picking model
portfolios — and the system that makes that bet executable.**

## The thesis

For a generation, the Canadian wealth industry has organized portfolios
around a one-dimensional risk score and a handful of model portfolios.
We're betting that as AI matures, portfolio construction commoditizes;
firms that use AI to elevate insight and outcomes will pull ahead.
MP2.0 takes a client's financial plan as input and produces a
portfolio that is mathematically tied to the plan's goals, continuously
updated as the plan and the world change. Som's framing: every client
meeting today opens with returns; in the MP2.0 world, every meeting
opens with goal progress.

## Four locked goals

1. **Re-imagine planning-first wealth.** Lead the industry shift.
2. **Connect the experience** — "One Purpose" across Steadyhand,
   Harness, Link, Partnership Program.
3. **Accelerate fund sales** — fund pages link to portfolios; portfolio
   pages link to funds.
4. **Access new distribution channels** — DIY, Group RRSPs, DC
   pensions, future retirement robo.

## Business case

- **Target:** ~$5B AUM toward Purpose's $50B-by-2028.
- **Threshold (Som):** 100–1,000 deeply partnered advisors. Depth
  wins.
- **Fee argument:** of a 1% advisor fee, ~30–50 bps is market access
  (commoditizing); the remaining 50–70 bps must come from planning
  value. MP2.0 makes those bps defensible.
- **Catalyst:** the **Longevity Pension Fund (LPF)** — strong product,
  weak sales because it doesn't fit a risk-bucket portfolio. Needs a
  planning-aware allocation engine.

## Pilot status

**Pilot live since 2026-05-08.** 3–5 Investment Specialists at
Steadyhand, real client PII flowing under the canon §11.8.3
defense-in-depth regime (Bedrock ca-central-1 fail-closed, immutable
audit, hashed sensitive identifiers, redacted evidence quotes, RBAC,
secure-root storage). Current tag: **`v0.1.3-pilot-quality-closure`**
(cut 2026-05-05). Pre-pilot Bedrock spend: $0.36 cumulative.

## The 8 success metrics (weekly review)

1. Advisors completing ≥1 onboarding by 2026-05-15 — target 3/5.
2. Sev-1 incidents week 1–2 — target <2.
3. Real-PII docs reconciled per advisor — target ≥90%.
4. Advisor NPS — target ≥7/10.
5. Bedrock $ per advisor / week — target <$25.
6. Manual-entry rate per workspace — target <25%.
7. Time-to-first-portfolio (median) — target <30 min.
8. Conflict-resolve rate — target ≥80%.

GA gate: all of the above plus NPS ≥8 and ≥50% of advisors completing
≥3 onboardings, for two consecutive weeks. (See
`docs/agent/pilot-success-metrics.md` for live queries.)

## Platform position

MP2.0 is a **goal-based lens that layers on top of foundational
platforms — not a parallel rebuild.** The differentiator is the
goal × account engine; the scaffolding (login, client list, document
storage) is minimal and intended to snap into Advisor Center primitives
as they mature.

## Team

**Fraser Stark** (project lead) · **Nafal Butt** · **Lori Norman**
(IS + compliance lead) · **Saranyaraj Rajendran** (engineering
lead). Executive sponsor: **Som Seif**. Hiring in progress.

## Not in pilot scope

Automated execution (Stage 4 of the 6-stage journey, Phase 2+);
real tax-drag math; fund-of-funds collapse execution suggestions;
external-holdings risk-tolerance dampener; federation / SSO (Phase
B+).

## See also

- [`README.md`](README.md) · [`glossary.md`](glossary.md)
  (start here if new to wealth-management) ·
  [`architecture-diagrams.md`](architecture-diagrams.md)
- [`../../MP2.0_Working_Canon.md`](../../MP2.0_Working_Canon.md)
  — authoritative canon
- [`../agent/pilot-success-metrics.md`](../agent/pilot-success-metrics.md)
  · [`../agent/pilot-readiness-2026-05-04.md`](../agent/pilot-readiness-2026-05-04.md)
- [`../../CHANGELOG.md`](../../CHANGELOG.md) — what shipped each tag
