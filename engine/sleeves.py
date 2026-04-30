"""Illustrative Steadyhand v1 fund universe (canon §5.1).

Updated to the v36 mockup 8-fund universe per locked decision #3 (hybrid):
all 8 funds are optimizer-eligible in the CMA snapshot; whole-portfolio
funds (Founders, Builders) carry ``is_whole_portfolio`` metadata in the
CMA fixture. The collapse-suggestion logic in engine/collapse.py runs on
top of the optimizer output to surface FoF replacement opportunities per
canon §4.3b.

These ``Sleeve`` values are placeholders for Phase 1 (canon §15 Q15 / Q56).
Real CMA values come from the published `CMASnapshot` (which the engine
actually consumes via `optimize()`); this list is a legacy reference kept
under its original identifier per canon Part 10 ("code identifiers don't
need to track product vocabulary changes"). `docs/agent/open-questions.md`
tracks the need for real CMA values.
"""

from engine.schemas import Sleeve

STEADYHAND_PURE_SLEEVES: list[Sleeve] = [
    Sleeve(
        id="cash_savings",
        name="Cash / Savings",
        mandate="Money market and high-interest savings exposure.",
        role="Risk-free corner and glide-path endpoint.",
        asset_class="cash",
        expected_return=0.021,
        volatility=0.005,
        equity_weight=0.0,
    ),
    Sleeve(
        id="income_fund",
        name="Income Fund",
        mandate="Canadian bonds with a minority Canadian equity allocation.",
        role="Fixed income building block, impure for v1 because it carries equity exposure.",
        asset_class="fixed_income",
        expected_return=0.039,
        volatility=0.065,
        equity_weight=0.25,
    ),
    Sleeve(
        id="equity_fund",
        name="Equity Fund",
        mandate="Canadian and global mid/large-cap equity core.",
        role="Primary equity building block.",
        asset_class="equity",
        expected_return=0.071,
        volatility=0.155,
        equity_weight=1.0,
    ),
    Sleeve(
        id="global_equity_fund",
        name="Global Equity Fund",
        mandate="International equity exposure.",
        role="Global diversification.",
        asset_class="equity",
        expected_return=0.073,
        volatility=0.17,
        equity_weight=1.0,
    ),
    Sleeve(
        id="canadian_small_cap",
        name="Canadian Small-Cap Equity Fund",
        mandate="Canadian small-cap exposure.",
        role="Equity satellite.",
        asset_class="equity",
        expected_return=0.079,
        volatility=0.22,
        equity_weight=1.0,
    ),
    Sleeve(
        id="global_small_cap",
        name="Global Small-Cap Equity Fund",
        mandate="Global small-cap exposure.",
        role="Equity satellite.",
        asset_class="equity",
        expected_return=0.081,
        volatility=0.225,
        equity_weight=1.0,
    ),
    # Whole-portfolio funds added per v36 8-fund universe (locked decision #3).
    # In code these stay as Sleeve entries (canon Part 10 — code identifiers
    # legacy); the CMA fixture flags them ``is_whole_portfolio=true`` on the
    # FundAssumption schema, which is what the optimizer actually consumes.
    Sleeve(
        id="founders_fund",
        name="Founders Fund",
        mandate="Tactical balanced fund-of-funds; ~60/40 long-term target.",
        role="Whole-portfolio fund; collapse target for Balanced blends.",
        asset_class="equity",
        expected_return=0.060,
        volatility=0.074,
        equity_weight=0.60,
    ),
    Sleeve(
        id="builders_fund",
        name="Builders Fund",
        mandate="All-equity fund-of-funds composed of the four equity building blocks.",
        role="Whole-portfolio fund; collapse target for Growth-oriented blends.",
        asset_class="equity",
        expected_return=0.073,
        volatility=0.133,
        equity_weight=0.90,
    ),
]


# ---------------------------------------------------------------------------
# v36 SLEEVE_REF_POINTS — calibration reference for parity tests + advisor
# explainability. These are the recommended sleeve mixes at canonical risk
# score points per the v36 mockup.
#
# Locked decision #3 (Hybrid): the optimizer uses efficient-frontier
# optimization (canon §4.1, engine/frontier.py); these reference points are
# NOT used at runtime to compute mixes. They exist as:
#   - a calibration anchor (the optimizer's outputs at the score points
#     should land near these mixes for the Default CMA),
#   - a parity-test fixture (`engine/tests/test_parity_v36.py` can pin the
#     expected shape), and
#   - explainability material for the methodology page.
#
# Source: v36 mockup `SLEEVE_REF_POINTS` (~line 10339) per the context
# pack at `/Users/saranyaraj/Downloads/MP2_Context_Pack_dense.md`. The
# product/engine teams may revise these values; single-line edits update
# everything.
# ---------------------------------------------------------------------------

#: Sleeve mix at score points 5/15/25/35/45/50 — values in percent (sum ~100).
SLEEVE_REF_POINTS: dict[int, dict[str, int]] = {
    5: {  # Cautious (canon)
        "SH-Sav": 55,
        "SH-Inc": 30,
        "SH-Eq": 5,
        "SH-Glb": 5,
        "SH-SC": 0,
        "SH-GSC": 0,
        "SH-Fnd": 5,
        "SH-Bld": 0,
    },
    15: {  # Conservative-balanced (canon)
        "SH-Sav": 22,
        "SH-Inc": 38,
        "SH-Eq": 8,
        "SH-Glb": 10,
        "SH-SC": 2,
        "SH-GSC": 2,
        "SH-Fnd": 15,
        "SH-Bld": 3,
    },
    25: {  # Balanced (canon) — Founders peaks here.
        "SH-Sav": 8,
        "SH-Inc": 28,
        "SH-Eq": 12,
        "SH-Glb": 14,
        "SH-SC": 5,
        "SH-GSC": 5,
        "SH-Fnd": 22,
        "SH-Bld": 6,
    },
    35: {  # Balanced-growth (canon)
        "SH-Sav": 2,
        "SH-Inc": 16,
        "SH-Eq": 16,
        "SH-Glb": 20,
        "SH-SC": 8,
        "SH-GSC": 8,
        "SH-Fnd": 18,
        "SH-Bld": 12,
    },
    45: {  # Growth-oriented (canon) — Builders peaks here.
        "SH-Sav": 0,
        "SH-Inc": 5,
        "SH-Eq": 20,
        "SH-Glb": 24,
        "SH-SC": 12,
        "SH-GSC": 12,
        "SH-Fnd": 8,
        "SH-Bld": 19,
    },
    50: {  # Aggressive bound (Goal_50 max — internal only, locked #6)
        "SH-Sav": 0,
        "SH-Inc": 2,
        "SH-Eq": 22,
        "SH-Glb": 26,
        "SH-SC": 13,
        "SH-GSC": 13,
        "SH-Fnd": 0,
        "SH-Bld": 24,
    },
}

#: Display colors for v36 fund universe (advisor UI ↔ design tokens).
SLEEVE_COLOR_HEX: dict[str, str] = {
    "SH-Sav": "#5D7A8C",  # slate
    "SH-Inc": "#2E4A6B",  # navy
    "SH-Eq": "#0E1116",  # ink
    "SH-Glb": "#8B5E3C",  # copper
    "SH-SC": "#B87333",  # orange
    "SH-GSC": "#2E5D3A",  # green
    "SH-Fnd": "#6B5876",  # plum
    "SH-Bld": "#8B8C5E",  # olive
}

#: Display names for v36 fund universe.
FUND_NAMES: dict[str, str] = {
    "SH-Sav": "Steadyhand Savings Fund",
    "SH-Inc": "Steadyhand Income Fund",
    "SH-Eq": "Steadyhand Equity Fund",
    "SH-Glb": "Steadyhand Global Equity Fund",
    "SH-SC": "Steadyhand Small-Cap Equity Fund",
    "SH-GSC": "Steadyhand Global Small-Cap Equity Fund",
    "SH-Fnd": "Steadyhand Founders Fund",
    "SH-Bld": "Steadyhand Builders Fund",
}
