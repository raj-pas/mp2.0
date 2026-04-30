"""Lognormal projection math (canon §4 + v36 mockup methodology §7).

Computes mu/sigma curves from a continuous risk score, lognormal quantiles
and means, probability-above-target, and tier-aware percentile bands.

**External holdings** (locked decision #11): the only effect external
holdings have on projections is the *drift penalty* (mu * 0.85, sigma *
1.15) — there is NO household risk-tolerance dampener implemented.
See engine/risk_profile.py docstring for the deferral rationale.

**Score convention**: this module accepts a continuous ``score`` float in
[1.0, 50.0] (the same internal scale ``Goal_50`` uses). Callers that have
only a canon 1-5 score should feed the bucket-midpoint
(``BUCKET_REPRESENTATIVE_SCORE`` below) to get a reasonable projection.

Canon §9.4.2 boundary: stdlib + pydantic + engine.* only.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Configurable constants (locked decision #10).
# Sources: v36 mockup methodology §7 + JS reference functions.
# ---------------------------------------------------------------------------

#: Equity weight curve. score=1 → 5%, score=50 → ~95% equity.
EQUITY_INTERCEPT = 0.05
EQUITY_SLOPE = 0.90
EQUITY_MIN = 0.05
EQUITY_MAX = 0.95

#: Drift / volatility curves keyed off equity weight.
MU_IDEAL_INTERCEPT = 0.030
MU_IDEAL_SLOPE = 0.045
SIGMA_IDEAL_INTERCEPT = 0.030
SIGMA_IDEAL_SLOPE = 0.190

#: Drift penalty when actual sleeve mix is off-target.
MU_CURRENT_PENALTY_INTERNAL = 0.92
MU_CURRENT_PENALTY_EXTERNAL = 0.85
SIGMA_CURRENT_PENALTY_INTERNAL = 1.08
SIGMA_CURRENT_PENALTY_EXTERNAL = 1.15

#: Tier-aware percentile bands (mockup §7).
TIER_BAND_PCTS: dict[str, tuple[float, float]] = {
    "need": (0.10, 0.90),
    "want": (0.05, 0.95),
    "wish": (0.025, 0.975),
    "unsure": (0.05, 0.95),  # Default to Want band for Unsure goals.
}

#: Canon 1-5 → representative continuous score for projection input.
#: Matches the mockup's ``bucketToScore`` mapping used by
#: ``effectiveScoreForGoal`` when an override or horizon-cap is binding.
BUCKET_REPRESENTATIVE_SCORE: dict[int, float] = {1: 5.0, 2: 15.0, 3: 25.0, 4: 35.0, 5: 45.0}

#: Score range guards.
SCORE_MIN = 1.0
SCORE_MAX = 50.0

Mode = Literal["ideal", "current"]
Tier = Literal["need", "want", "wish", "unsure"]


class ProjectionBands(BaseModel):
    """Distribution snapshot at a single horizon."""

    model_config = ConfigDict(extra="forbid")

    p2_5: float
    p5: float
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    p95: float
    p97_5: float
    mean: float
    mu: float
    sigma: float
    tier_low_pct: float
    tier_high_pct: float


class ProjectionPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    year: float
    value: float
    percentile: float


# ---------------------------------------------------------------------------
# Math primitives
# ---------------------------------------------------------------------------


def equity_from_score(score: float) -> float:
    """Equity weight curve. ``equity = clamp(0.05 + (score - 1) / 49 * 0.90, 0.05, 0.95)``."""

    _validate_score(score)
    raw = EQUITY_INTERCEPT + (score - 1.0) / 49.0 * EQUITY_SLOPE
    return max(EQUITY_MIN, min(EQUITY_MAX, raw))


def mu_ideal(score: float) -> float:
    """``mu_ideal = 0.030 + equity * 0.045`` (annual log-drift)."""

    return MU_IDEAL_INTERCEPT + equity_from_score(score) * MU_IDEAL_SLOPE


def sigma_ideal(score: float) -> float:
    """``sigma_ideal = 0.030 + equity * 0.190`` (annual log-vol)."""

    return SIGMA_IDEAL_INTERCEPT + equity_from_score(score) * SIGMA_IDEAL_SLOPE


def mu_current(score: float, *, is_external: bool) -> float:
    """``mu_current = mu_ideal * penalty`` (penalty accounts for off-target drag)."""

    penalty = MU_CURRENT_PENALTY_EXTERNAL if is_external else MU_CURRENT_PENALTY_INTERNAL
    return mu_ideal(score) * penalty


def sigma_current(score: float, *, is_external: bool) -> float:
    """``sigma_current = sigma_ideal * penalty`` (slight inflation when off-target)."""

    penalty = SIGMA_CURRENT_PENALTY_EXTERNAL if is_external else SIGMA_CURRENT_PENALTY_INTERNAL
    return sigma_ideal(score) * penalty


def _resolve_mu_sigma(score: float, *, mode: Mode, is_external: bool) -> tuple[float, float]:
    if mode == "ideal":
        return mu_ideal(score), sigma_ideal(score)
    return mu_current(score, is_external=is_external), sigma_current(score, is_external=is_external)


def lognormal_quantile(
    *,
    start: float,
    score: float,
    horizon_years: float,
    percentile: float,
    mode: Mode = "ideal",
    is_external: bool = False,
) -> float:
    """Lognormal quantile: S_T = S_0 * exp(mu*T + z*sigma*sqrt(T))."""

    _validate_inputs(start, score, horizon_years)
    if not 0 < percentile < 1:
        raise ValueError(f"percentile must be in (0, 1), got {percentile}")
    mu, sigma = _resolve_mu_sigma(score, mode=mode, is_external=is_external)
    z = _inverse_standard_normal(percentile)
    return start * math.exp(mu * horizon_years + z * sigma * math.sqrt(horizon_years))


def lognormal_mean(
    *,
    start: float,
    score: float,
    horizon_years: float,
    mode: Mode = "ideal",
    is_external: bool = False,
) -> float:
    """E[S_T] = S_0 * exp(mu*T + sigma^2*T/2)."""

    _validate_inputs(start, score, horizon_years)
    mu, sigma = _resolve_mu_sigma(score, mode=mode, is_external=is_external)
    return start * math.exp(mu * horizon_years + (sigma**2) * horizon_years / 2.0)


def prob_above_target(
    *,
    start: float,
    score: float,
    horizon_years: float,
    target: float,
    mode: Mode = "ideal",
    is_external: bool = False,
) -> float:
    """P(S_T >= target) under lognormal model."""

    _validate_inputs(start, score, horizon_years)
    if target <= 0:
        raise ValueError(f"target must be > 0, got {target}")
    mu, sigma = _resolve_mu_sigma(score, mode=mode, is_external=is_external)
    if sigma <= 0 or horizon_years <= 0:
        return 1.0 if start >= target else 0.0
    d = (math.log(target / start) - mu * horizon_years) / (sigma * math.sqrt(horizon_years))
    return 1.0 - _standard_normal_cdf(d)


def tier_band_pcts(tier: Tier) -> tuple[float, float]:
    """Return (low_pct, high_pct) for the tier's projection band."""

    if tier not in TIER_BAND_PCTS:
        raise ValueError(f"tier must be one of {sorted(TIER_BAND_PCTS)}, got {tier}")
    return TIER_BAND_PCTS[tier]


def projection_bands(
    *,
    start: float,
    score: float,
    horizon_years: float,
    tier: Tier = "want",
    mode: Mode = "ideal",
    is_external: bool = False,
) -> ProjectionBands:
    """Distribution at horizon: every standard percentile + mean + mu/sigma."""

    _validate_inputs(start, score, horizon_years)
    mu, sigma = _resolve_mu_sigma(score, mode=mode, is_external=is_external)
    low, high = tier_band_pcts(tier)

    def q(p: float) -> float:
        return lognormal_quantile(
            start=start,
            score=score,
            horizon_years=horizon_years,
            percentile=p,
            mode=mode,
            is_external=is_external,
        )

    return ProjectionBands(
        p2_5=q(0.025),
        p5=q(0.05),
        p10=q(0.10),
        p25=q(0.25),
        p50=q(0.50),
        p75=q(0.75),
        p90=q(0.90),
        p95=q(0.95),
        p97_5=q(0.975),
        mean=lognormal_mean(
            start=start,
            score=score,
            horizon_years=horizon_years,
            mode=mode,
            is_external=is_external,
        ),
        mu=mu,
        sigma=sigma,
        tier_low_pct=low,
        tier_high_pct=high,
    )


def projection_path(
    *,
    start: float,
    score: float,
    horizon_years: float,
    percentile: float,
    n_steps: int = 50,
    mode: Mode = "ideal",
    is_external: bool = False,
) -> list[ProjectionPoint]:
    """Sequence of ``(year, value)`` points along a constant-percentile path."""

    if n_steps < 2:
        raise ValueError(f"n_steps must be >= 2, got {n_steps}")
    points: list[ProjectionPoint] = []
    for i in range(n_steps + 1):
        year = horizon_years * i / n_steps
        if year == 0:
            value = start
        else:
            value = lognormal_quantile(
                start=start,
                score=score,
                horizon_years=year,
                percentile=percentile,
                mode=mode,
                is_external=is_external,
            )
        points.append(ProjectionPoint(year=year, value=value, percentile=percentile))
    return points


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_score(score: float) -> None:
    if not SCORE_MIN <= score <= SCORE_MAX:
        raise ValueError(f"score must be in [{SCORE_MIN}, {SCORE_MAX}], got {score}")


def _validate_inputs(start: float, score: float, horizon_years: float) -> None:
    if start <= 0:
        raise ValueError(f"start must be > 0, got {start}")
    _validate_score(score)
    if horizon_years < 0:
        raise ValueError(f"horizon_years must be >= 0, got {horizon_years}")


def _standard_normal_cdf(x: float) -> float:
    """Standard normal CDF via math.erf."""

    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _inverse_standard_normal(p: float) -> float:
    """Acklam's inverse standard normal CDF (matches engine/frontier.py)."""

    if not 0 < p < 1:
        raise ValueError(f"p must be in (0, 1), got {p}")

    # Coefficients from Peter J. Acklam.
    a = [
        -3.969683028665376e1,
        2.209460984245205e2,
        -2.759285104469687e2,
        1.383577518672690e2,
        -3.066479806614716e1,
        2.506628277459239e0,
    ]
    b = [
        -5.447609879822406e1,
        1.615858368580409e2,
        -1.556989798598866e2,
        6.680131188771972e1,
        -1.328068155288572e1,
    ]
    c = [
        -7.784894002430293e-3,
        -3.223964580411365e-1,
        -2.400758277161838e0,
        -2.549732539343734e0,
        4.374664141464968e0,
        2.938163982698783e0,
    ]
    d = [
        7.784695709041462e-3,
        3.224671290700398e-1,
        2.445134137142996e0,
        3.754408661907416e0,
    ]

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q) / (
            ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
        )
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
        (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
    )
