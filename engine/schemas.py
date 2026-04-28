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


class EngineModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Holding(EngineModel):
    sleeve_id: str
    sleeve_name: str
    weight: float = Field(ge=0, le=1)
    market_value: float = Field(ge=0)


class GoalAccountLink(EngineModel):
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
    current_holdings: list[Holding] = Field(default_factory=list)
    contribution_room: float | None = Field(default=None, ge=0)
    contribution_history: list[dict] = Field(default_factory=list)
    is_held_at_purpose: bool = True


class Goal(EngineModel):
    id: str
    household_id: str
    name: str
    target_amount: float = Field(gt=0)
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
    household_score: int = Field(ge=1, le=10)
    goals: dict[str, int] = Field(default_factory=dict)


class Household(EngineModel):
    id: str
    type: HouseholdType
    members: list[Person] = Field(min_length=1, max_length=2)
    goals: list[Goal] = Field(default_factory=list)
    accounts: list[Account] = Field(default_factory=list)
    external_assets: list[dict] = Field(default_factory=list)
    household_risk_score: int = Field(ge=1, le=10)
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


class GoalBlend(EngineModel):
    goal_id: str
    goal_name: str
    allocations: list[Allocation]
    expected_return: float
    volatility: float
    risk_rating: RiskRating
    frontier_percentile: int


class FanChartPoint(EngineModel):
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
    sleeve_assumptions: list[dict]
    constraints: dict = Field(default_factory=dict)


class EngineOutput(EngineModel):
    household_id: str
    goal_blends: list[GoalBlend]
    household_blend: list[Allocation]
    fan_chart: list[FanChartPoint]
    account_risk_ratings: dict[str, RiskRating]
    household_risk_rating: RiskRating
    audit_trace: EngineRun
    narrative_summary: str
