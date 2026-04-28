"""Illustrative Steadyhand v1 sleeve universe.

These values are placeholders for Phase 1. `docs/agent/open-questions.md`
tracks the need for real CMA and sleeve numerical inputs.
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
        role="Fixed income sleeve, impure for v1 because it carries equity exposure.",
        asset_class="fixed_income",
        expected_return=0.039,
        volatility=0.065,
        equity_weight=0.25,
    ),
    Sleeve(
        id="equity_fund",
        name="Equity Fund",
        mandate="Canadian and global mid/large-cap equity core.",
        role="Primary equity sleeve.",
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
]
