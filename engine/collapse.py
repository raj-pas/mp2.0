"""Fund-of-funds collapse suggestion (canon §4.3b).

When a building-block blend closely matches an existing whole-portfolio fund
(Founders, Builders, PACF), the optimizer can recommend executing via that
FoF instead of holding the constituent building blocks separately. The match
is computed at the asset-class level (the blend's asset-class composition
vs. the whole-portfolio fund's published asset-class composition).

**Hybrid 8-fund universe** (locked decision #3): all 8 v36 funds are
optimizer-eligible inputs to the frontier (engine/sleeves.py). The
collapse-suggestion logic runs *on top* of the optimizer output: if the
recommended building-block blend closely resembles Founders or Builders, we
suggest the FoF; otherwise we suggest the building-block blend directly.

Canon §9.4.2 boundary: stdlib + pydantic + engine.* only.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from engine.schemas import FundAssumption

#: Default match-score threshold for FoF collapse suggestion. Tunable per
#: locked decision #10. Threshold of 0.92 is the mockup's implicit default
#: per canon §15 Q (fund-of-funds collapse match-score threshold).
DEFAULT_COLLAPSE_THRESHOLD = 0.92


class CollapseSuggestion(BaseModel):
    """A FoF replacement recommendation for a building-block blend."""

    model_config = ConfigDict(extra="forbid")

    suggested_fund_id: str
    suggested_fund_name: str
    match_score: float = Field(ge=0.0, le=1.0)
    replaces: list[str]
    """Fund IDs whose combined exposure is replaced by the suggested FoF."""


def blend_asset_class_composition(
    *,
    blend: dict[str, float],
    eligible_funds: list[FundAssumption],
) -> dict[str, float]:
    """Compute the asset-class composition of a building-block blend.

    Args:
        blend: ``{fund_id: weight}`` (weights should sum to ~1.0).
        eligible_funds: full universe — used to look up each fund's
            ``asset_class_weights``.

    Returns:
        ``{asset_class: weight}`` weighted by blend allocation.
    """

    fund_index = {f.id: f for f in eligible_funds}
    composition: dict[str, float] = {}
    for fund_id, weight in blend.items():
        fund = fund_index.get(fund_id)
        if fund is None or weight <= 0:
            continue
        for asset_class, ac_weight in fund.asset_class_weights.items():
            composition[asset_class] = composition.get(asset_class, 0.0) + weight * ac_weight
    return composition


def match_score(
    *,
    blend: dict[str, float],
    whole_portfolio_fund: FundAssumption,
    eligible_funds: list[FundAssumption],
) -> float:
    """Match score in [0, 1] between a blend and a whole-portfolio fund.

    Uses 1 - (L1 distance / 2) over the asset-class composition vector.
    1.0 = identical asset-class breakdown; 0.0 = completely disjoint.
    """

    if not whole_portfolio_fund.is_whole_portfolio:
        raise ValueError(
            f"{whole_portfolio_fund.id} is not a whole_portfolio fund; "
            "collapse suggestions only target whole-portfolio funds."
        )

    blend_comp = blend_asset_class_composition(blend=blend, eligible_funds=eligible_funds)
    fund_comp = whole_portfolio_fund.asset_class_weights

    all_classes = set(blend_comp) | set(fund_comp)
    if not all_classes:
        return 0.0

    l1_distance = sum(abs(blend_comp.get(ac, 0.0) - fund_comp.get(ac, 0.0)) for ac in all_classes)
    # Normalize: max L1 between two probability distributions on the same
    # support is 2 (entirely disjoint), so divide by 2 for [0, 1].
    return max(0.0, 1.0 - l1_distance / 2.0)


def collapse_suggestion(
    *,
    blend: dict[str, float],
    eligible_funds: list[FundAssumption],
    threshold: float = DEFAULT_COLLAPSE_THRESHOLD,
) -> CollapseSuggestion | None:
    """Suggest a whole-portfolio fund replacement if blend closely matches one.

    Returns the highest-scoring whole-portfolio fund whose match score
    exceeds the threshold; ``None`` if no fund clears the bar.
    """

    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"threshold must be in [0, 1], got {threshold}")

    whole_portfolio_funds = [f for f in eligible_funds if f.is_whole_portfolio]
    if not whole_portfolio_funds:
        return None

    best: tuple[float, FundAssumption] | None = None
    for fund in whole_portfolio_funds:
        score = match_score(
            blend=blend,
            whole_portfolio_fund=fund,
            eligible_funds=eligible_funds,
        )
        if best is None or score > best[0]:
            best = (score, fund)

    if best is None or best[0] < threshold:
        return None

    score, fund = best
    # The "replaces" list is every blend fund_id with non-trivial allocation
    # whose asset class is also present in the FoF — i.e., the funds that
    # would be replaced by the FoF position.
    replaces = sorted(fund_id for fund_id, weight in blend.items() if weight > 0.001)
    return CollapseSuggestion(
        suggested_fund_id=fund.id,
        suggested_fund_name=fund.name,
        match_score=score,
        replaces=replaces,
    )
