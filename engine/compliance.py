"""Deterministic placeholder compliance mapping for Phase 1."""

from __future__ import annotations

from engine.schemas import Allocation, RiskRating, Sleeve


def risk_rating(
    blend: list[Allocation],
    sleeve_universe: list[Sleeve],
    time_horizon_years: float | None = None,
) -> RiskRating:
    """Map an allocation to a low/medium/high placeholder risk bucket.

    The canon keeps exact thresholds open. This function is intentionally simple,
    deterministic, and easy to replace once Lori + Saranyaraj lock the policy.
    """

    sleeves_by_id = {sleeve.id: sleeve for sleeve in sleeve_universe}
    equity_pct = sum(
        allocation.weight * sleeves_by_id[allocation.sleeve_id].equity_weight
        for allocation in blend
        if allocation.sleeve_id in sleeves_by_id
    )
    volatility = sum(
        allocation.weight * sleeves_by_id[allocation.sleeve_id].volatility
        for allocation in blend
        if allocation.sleeve_id in sleeves_by_id
    )

    if equity_pct <= 0.25 and volatility <= 0.06:
        return "low"
    if equity_pct <= 0.7 and volatility <= 0.14:
        if time_horizon_years is not None and time_horizon_years < 3 and equity_pct > 0.45:
            return "high"
        return "medium"
    return "high"
