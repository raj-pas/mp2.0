"""Pydantic contracts for the pure MP2.0 engine.

The engine boundary is intentionally independent of Django. Web code translates
database rows into these models before calling `engine.optimize()`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

HouseholdType = Literal["single", "couple"]
AccountType = Literal[
    "RRSP",
    "TFSA",
    "RESP",
    "RDSP",
    "FHSA",
    "Non-Registered",
    "LIRA",
    "RRIF",
    "Corporate",
]
RegulatoryObjective = Literal["income", "growth_and_income", "growth"]
RegulatoryTimeHorizon = Literal["<3y", "3-10y", ">10y"]
RiskRating = Literal["low", "medium", "high"]
GoalStatus = Literal["on_track", "watch", "off_track"]
OptimizationMethod = Literal["percentile", "probability", "utility"]
AssetClass = Literal["cash", "fixed_income", "equity"]
CashState = Literal["invested", "onboarding_cash", "pending_investment"]
FundType = Literal["building_block", "whole_portfolio"]
MappingStatus = Literal[
    "mapped",
    "partially_mapped",
    "unmapped",
    "no_holdings",
    "cash_or_pending",
]


class EngineModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Holding(EngineModel):
    sleeve_id: str
    sleeve_name: str
    weight: float = Field(ge=0, le=1)
    market_value: float = Field(ge=0)


class GoalAccountLink(EngineModel):
    id: str
    goal_id: str
    account_id: str
    allocated_amount: float | None = Field(default=None, ge=0)
    allocated_pct: float | None = Field(default=None, ge=0, le=1)


class Account(EngineModel):
    id: str
    household_id: str
    owner_person_id: str | None = None
    type: AccountType
    regulatory_objective: RegulatoryObjective
    regulatory_time_horizon: RegulatoryTimeHorizon
    regulatory_risk_rating: RiskRating
    current_value: float = Field(default=0, ge=0)
    current_holdings: list[Holding] = Field(default_factory=list)
    contribution_room: float | None = Field(default=None, ge=0)
    contribution_history: list[dict] = Field(default_factory=list)
    is_held_at_purpose: bool = True
    missing_holdings_confirmed: bool = False
    cash_state: CashState = "invested"


class Goal(EngineModel):
    id: str
    household_id: str
    name: str
    target_amount: float | None = Field(default=None, gt=0)
    target_date: date
    necessity_score: int = Field(ge=1, le=5)
    current_funded_amount: float = Field(default=0, ge=0)
    contribution_plan: dict = Field(default_factory=dict)
    account_allocations: list[GoalAccountLink] = Field(default_factory=list)
    goal_risk_score: int = Field(ge=1, le=5)
    status: GoalStatus = "watch"
    notes: str = ""


class Person(EngineModel):
    id: str
    household_id: str
    name: str
    dob: date
    marital_status: str = ""
    blended_family_flag: bool = False
    citizenship: str = "Canada"
    residency: str = "Canada"
    health_indicators: dict = Field(default_factory=dict)
    longevity_assumption: int | None = Field(default=None, ge=0)
    employment: dict = Field(default_factory=dict)
    pensions: list[dict] = Field(default_factory=list)
    investment_knowledge: Literal["low", "medium", "high"] = "medium"
    trusted_contact_person: str = ""
    poa_status: str = ""
    will_status: str = ""
    beneficiary_designations: list[dict] = Field(default_factory=list)


class RiskInput(EngineModel):
    household_score: int = Field(ge=1, le=5)
    goals: dict[str, int] = Field(default_factory=dict)


class Household(EngineModel):
    id: str
    type: HouseholdType
    members: list[Person] = Field(min_length=1, max_length=2)
    goals: list[Goal] = Field(default_factory=list)
    accounts: list[Account] = Field(default_factory=list)
    external_assets: list[dict] = Field(default_factory=list)
    household_risk_score: int = Field(ge=1, le=5)
    risk_input: RiskInput
    created_at: datetime
    updated_at: datetime


class Sleeve(EngineModel):
    id: str
    name: str
    mandate: str
    role: str
    asset_class: AssetClass
    expected_return: float
    volatility: float = Field(ge=0)
    equity_weight: float = Field(ge=0, le=1)
    fee_series: str = "highest_fee_series_proxy"
    assumptions_source: str = "illustrative_phase_1_placeholder"


class Allocation(EngineModel):
    sleeve_id: str
    sleeve_name: str
    weight: float = Field(ge=0, le=1)
    fund_type: FundType = "building_block"
    asset_class_weights: dict[str, float] = Field(default_factory=dict)
    geography_weights: dict[str, float] = Field(default_factory=dict)


class AllocationDelta(EngineModel):
    sleeve_id: str
    sleeve_name: str
    weight_delta: float


class FundAssumption(EngineModel):
    id: str
    name: str
    expected_return: float
    volatility: float = Field(ge=0)
    optimizer_eligible: bool = True
    is_whole_portfolio: bool = False
    aliases: list[str] = Field(default_factory=list)
    asset_class_weights: dict[str, float] = Field(default_factory=dict)
    geography_weights: dict[str, float] = Field(default_factory=dict)
    tax_drag: dict[str, float] = Field(default_factory=dict)


class CMASnapshot(EngineModel):
    id: str
    version: int
    source: str
    funds: list[FundAssumption] = Field(min_length=2)
    correlation_matrix: list[list[float]]
    tax_drag_version: str = "neutral_tax_drag.v1"


class ProjectionPoint(EngineModel):
    year: int
    p10: float
    p50: float
    p90: float
    optimized_percentile_value: float


class CurrentPortfolioComparison(EngineModel):
    missing_holdings: bool
    status: MappingStatus = "no_holdings"
    reason: str = ""
    expected_return: float | None = None
    volatility: float | None = None
    allocations: list[Allocation] = Field(default_factory=list)
    deltas: list[AllocationDelta] = Field(default_factory=list)
    holdings_diagnostics: list[dict] = Field(default_factory=list)
    unmapped_holdings: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class LinkRecommendation(EngineModel):
    link_id: str
    goal_id: str
    goal_name: str
    account_id: str
    account_type: AccountType
    allocated_amount: float = Field(gt=0)
    horizon_years: float = Field(gt=0)
    goal_risk_score: int = Field(ge=1, le=5)
    frontier_percentile: int
    allocations: list[Allocation]
    expected_return: float
    volatility: float
    projected_value: float
    projection: list[ProjectionPoint]
    current_comparison: CurrentPortfolioComparison
    drift_flags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    explanation: dict = Field(default_factory=dict)
    advisor_summary: str
    technical_trace: dict


class Rollup(EngineModel):
    id: str
    name: str
    allocated_amount: float = Field(ge=0)
    allocations: list[Allocation]
    expected_return: float
    volatility: float


class FanChartPoint(EngineModel):
    link_id: str
    goal_id: str
    year: int
    p10: float
    p50: float
    p90: float


class Constraints(EngineModel):
    account_equity_caps: dict[str, float] = Field(default_factory=dict)


class EngineRun(EngineModel):
    model_version: str
    method: OptimizationMethod
    params: dict
    cma_snapshot_id: str
    cma_version: int
    fund_assumptions: list[dict]
    constraints: dict = Field(default_factory=dict)


class EngineOutput(EngineModel):
    schema_version: str = "engine_output.link_first.v2"
    household_id: str
    link_recommendations: list[LinkRecommendation]
    goal_rollups: list[Rollup]
    account_rollups: list[Rollup]
    household_rollup: Rollup
    fan_chart: list[FanChartPoint]
    audit_trace: EngineRun
    advisor_summary: str
    technical_trace: dict
    run_manifest: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
