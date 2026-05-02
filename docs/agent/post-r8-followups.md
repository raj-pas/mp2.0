# Post-R8 Followups — Demo-Critical Testing Items

**Compiled:** 2026-05-01 at HEAD `cfe941c`, before context compaction.

The 2026-05-01 session shipped R8 (methodology overlay) + demo lock-
down. Subsequent honest testing review surfaced 4 verifiable evidence
gaps for what just shipped. None are demo-blockers individually; all
are bounded; doing them BEFORE the Mon 2026-05-04 demo materially
reduces credibility risk on stage.

The user authorized the work but had to step away before it ran. The
next session should pick these up first if there's bandwidth before
the demo.

## Item 1 — Extend real-browser-smoke to include /methodology

**Risk:** Demo step 8 opens the methodology page. The
`real-browser-smoke.spec.ts` covers login → /review → Seltzer but
does NOT navigate to /methodology. So we don't know whether the new
R8 page renders cleanly in real Chromium with no console errors —
only that the foundation e2e (which uses the same harness but
different selectors) passes.

**Fix:** add a step to `frontend/e2e/real-browser-smoke.spec.ts`
that, after the existing review-screen assertions:

```ts
collector.setStep("methodology-page");
await page.getByRole("button", { name: /Methodology/i }).click();
await expect(page).toHaveURL(/\/methodology$/);
await expect(
  page.getByRole("heading", { level: 1, name: /^Methodology$/ }),
).toBeVisible();
// All 10 section headings should render
for (const sectionTitle of [
  /Household risk profile/i, /^Anchor$/i, /Goal-level risk score/i,
  /Horizon cap per goal/i, /Effective bucket/i, /Sleeve mix/i,
  /Lognormal projections/i, /Rebalancing moves/i,
  /Goal realignment/i, /Archive snapshots/i,
]) {
  await expect(page.getByRole("heading", { level: 2, name: sectionTitle })).toBeVisible();
}
// TOC click → scroll
await page.getByRole("button", { name: /Sleeve mix/i }).click();
await expect(page.getByRole("heading", { level: 2, name: /Sleeve mix/i })).toBeInViewport();
```

Run with `MP20_LOCAL_ADMIN_PASSWORD` env set. Time: 10 min.

## Item 2 — Cross-verify R8 worked-example numbers against engine code

**Risk:** I wrote each section's worked example from the master plan
summary; the master plan got them from the v36 mockup (Lori-
footnoted). I did NOT independently run the engine functions with
the documented inputs and confirm the outputs match. If the CEO asks
"can you show me how this is calculated?" and the on-screen formula
+ numbers don't match what the engine actually returns, that's a
credibility hit on stage.

**Fix:** new pytest at `engine/tests/test_r8_worked_examples_match_engine.py`:

```python
"""Regression guard: every worked-example number quoted in the R8
methodology page (frontend/src/i18n/en.json `methodology.s*.worked`)
must match what the engine actually computes. If any constant in
engine/risk_profile.py / projections.py / moves.py / goal_scoring.py
shifts, this test fails before the methodology page silently lies.
"""

from engine.risk_profile import compute_tolerance, compute_capacity, bucket_for_score, compute_anchor
from engine.goal_scoring import effective_score_and_bucket, score_to_descriptor
from engine.projections import equity_from_score, mu_ideal, mu_current, sigma_ideal, sigma_current
from engine.moves import compute_rebalance_moves


def test_s1_hayes_household_risk_profile():
    # Hayes: Q1=5, Q2=B, Q3=1, Q4=B  → T=45, C=50 → Balanced (canon 3)
    t = compute_tolerance(q1=5, q2="B", q3=["career"])
    c = compute_capacity(q4="B")
    assert t == 45, f"T expected 45, got {t}"
    assert c == 50, f"C expected 50, got {c}"
    assert bucket_for_score(min(t, c), scale="profile") == "Balanced"


def test_s2_hayes_anchor():
    anchor = compute_anchor(t=45, c=50)
    assert anchor == 22.5


def test_s3_hayes_retirement_goal_score():
    # anchor 22.5, Need-tier (-10 imp_shift), 47% of AUM (size_shift)
    # → resolves to canon Cautious (score 1)
    result = effective_score_and_bucket(
        anchor=22.5,
        tier="need",
        goal_amount_share=0.47,
        horizon_years=32,
        override=None,
    )
    assert result.score_1_5 == 1
    assert score_to_descriptor(1) == "Cautious"


def test_s7_thompson_retirement_projections():
    # Thompson Retirement at score 4 (Balanced-growth)
    # μ_ideal ≈ 5.8% (0.030 + equity_pct(4) * 0.045)
    # μ_current external ≈ 5.34% (μ_ideal × 0.85... actually × 0.92 for SH)
    eq = equity_from_score(4)
    mu_id = mu_ideal(4)
    assert abs(mu_id - (0.030 + eq * 0.045)) < 1e-6
    # Worked example says μ_current ≈ 5.34%; verify the SH branch
    mu_cur_sh = mu_current(4, is_external=False)
    assert abs(mu_cur_sh - mu_id * 0.92) < 1e-6


def test_s8_choi_education_moves():
    # Choi Education $80,000 goal, 4-pp shortfall in SH-Eq, 4-pp surplus
    # in SH-Sav → Δ = ±$3,200, $0 residual, sells == buys
    moves = compute_rebalance_moves(
        current_pct={"SH-Eq": 0.46, "SH-Sav": 0.54},
        ideal_pct={"SH-Eq": 0.50, "SH-Sav": 0.50},
        goal_total_dollars=80_000,
    )
    total_buy = sum(m.amount for m in moves if m.action == "buy")
    total_sell = sum(m.amount for m in moves if m.action == "sell")
    assert total_buy == total_sell  # invariant
    assert total_buy == 3200, f"expected 3200, got {total_buy}"
```

If any test fails, EITHER the engine constants drifted from canon (engine bug), OR the methodology copy is wrong (i18n bug). Fix the wrong side. Time: 30-45 min.

## Item 3 — Pre-upload Weryha as backup

**Risk:** The demo script names Weryha as the backup folder if
Seltzer fails on stage. Right now Weryha would require ~5 min of
live Bedrock processing if invoked — visible dead-air for the
audience.

**Fix:** run `demo-prep-seltzer.py` again with `Weryha` substituted
for `Seltzer`. The script template is at `/tmp/demo-prep-seltzer.py`
(not committed; recreate from Item 4 of demo-script-2026-05-04.md if
missing).

```python
# Changes to make:
SELTZER_ROOT = Path("/Users/saranyaraj/Documents/MP2.0_Clients/Weryha")
# label = f"Weryha review (demo prep)"
```

Time: 5 min driver + ~5 min Bedrock processing.

## Item 4 — Add /methodology cache-warm to demo pre-checklist

**Risk:** Bundle is 820KB. First-cold-load on the methodology page
might be slow if browser cache is cleared.

**Fix:** trivial. Update the pre-demo checklist in
`docs/agent/demo-script-2026-05-04.md` to add:

```markdown
- [ ] Open Chrome to `http://localhost:5173/methodology` once to warm the bundle (1-second click; closes the cold-load risk on stage)
```

Time: 30 seconds.

## Item 5 (yours) — Demo dry-run with the presenter

Already noted in `demo-script-2026-05-04.md`. Pending user
availability. Cannot be done by an agent alone. ~45 min when
scheduled.

## Sequencing recommendation

If next-session has the bandwidth before Mon 2026-05-04 demo:

1. **Item 4** (~30s, trivial doc edit) — does not need a deep session
2. **Item 1** (~10 min) — extends existing real-browser-smoke spec
3. **Item 2** (~30-45 min) — new pytest; surfaces math drift if any
4. **Item 3** (~10 min wall-clock) — safety net for stage backup

Total: ~1 hour of productive work.

If bandwidth is tight, do Item 2 first (highest credibility risk if a
worked example is wrong on stage) followed by Item 1.

## Items NOT in scope for next session

These are post-demo / post-pilot work, deferred per user direction:

- P0 #2 — Conflict-resolution UI cards (~1-1.5 days)
- P0 #5 — OpenAPI-typescript codegen (~0.5 day, kills FE/BE drift class)
- P0 #6 — Auth/RBAC hardening (Phase B)
- P0 #7 — Audit-immutability validation (Phase B)
- The 2 catalogued bugs (workspace status flip + zero-value accounts)
  — scheduled agent on Wed 2026-05-06 09:00 Winnipeg will land a
  proposal at `docs/agent/post-pilot-bugfix-proposal.md`
- R9 — CMA Workbench rebuild (analyst-only visual rewrite)
- R10 — Full mockup-parity checklist + DB state diff (sweep already
  done at 55/55)

## How to apply this in the next session

1. Read the master dossier (`post-r7-handoff-2026-05-01.md`) §3 first
   to understand current state
2. Run the gates from §8 of the dossier to verify the env at HEAD
   `cfe941c` is healthy before any code change
3. Pick from the items above per the sequencing recommendation
4. Each item has a self-contained fix; no cross-dependencies
5. After each item, run gates + commit
