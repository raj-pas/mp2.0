"""Pure MP2.0 portfolio engine package."""

from engine.collapse import CollapseSuggestion, collapse_suggestion, match_score
from engine.goal_scoring import (
    GoalRiskOverride,
    ResolvedGoalScore,
    effective_score_and_descriptor,
)
from engine.moves import Move, MovesResult, compute_rebalance_moves
from engine.optimizer import optimize
from engine.projections import (
    ProjectionBands,
    ProjectionPoint,
    equity_from_score,
    lognormal_mean,
    lognormal_quantile,
    mu_current,
    mu_ideal,
    prob_above_target,
    projection_bands,
    projection_path,
    sigma_current,
    sigma_ideal,
    tier_band_pcts,
)
from engine.risk_profile import (
    RiskProfileInput,
    RiskProfileResult,
    compute_risk_profile,
)
from engine.schemas import (
    Account,
    Allocation,
    AllocationDelta,
    CMASnapshot,
    Constraints,
    EngineOutput,
    FundAssumption,
    Goal,
    GoalAccountLink,
    Holding,
    Household,
    LinkRecommendation,
    Person,
    RiskInput,
    Rollup,
    Sleeve,
)
from engine.sleeves import (
    FUND_NAMES,
    SLEEVE_COLOR_HEX,
    SLEEVE_REF_POINTS,
    STEADYHAND_PURE_SLEEVES,
)

__all__ = [
    # Schemas
    "Account",
    "Allocation",
    "AllocationDelta",
    "CMASnapshot",
    "Constraints",
    "EngineOutput",
    "FundAssumption",
    "Goal",
    "GoalAccountLink",
    "Holding",
    "Household",
    "LinkRecommendation",
    "Person",
    "RiskInput",
    "Rollup",
    "Sleeve",
    # Universe
    "STEADYHAND_PURE_SLEEVES",
    "SLEEVE_REF_POINTS",
    "SLEEVE_COLOR_HEX",
    "FUND_NAMES",
    # Risk profile (R0)
    "RiskProfileInput",
    "RiskProfileResult",
    "compute_risk_profile",
    # Goal scoring (R0)
    "GoalRiskOverride",
    "ResolvedGoalScore",
    "effective_score_and_descriptor",
    # Projections (R0)
    "ProjectionBands",
    "ProjectionPoint",
    "equity_from_score",
    "lognormal_mean",
    "lognormal_quantile",
    "mu_current",
    "mu_ideal",
    "prob_above_target",
    "projection_bands",
    "projection_path",
    "sigma_current",
    "sigma_ideal",
    "tier_band_pcts",
    # Moves (R0)
    "Move",
    "MovesResult",
    "compute_rebalance_moves",
    # Collapse (R0)
    "CollapseSuggestion",
    "collapse_suggestion",
    "match_score",
    # Optimizer
    "optimize",
]
