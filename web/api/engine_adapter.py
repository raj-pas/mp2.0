from __future__ import annotations

from decimal import Decimal

from engine.goal_scoring import GoalRiskOverride as EngineGoalRiskOverride
from engine.risk_profile import RiskProfileInput, RiskProfileResult, compute_risk_profile
from engine.schemas import (
    Account,
    CMASnapshot,
    FundAssumption,
    Goal,
    GoalAccountLink,
    Holding,
    Household,
    Person,
    RiskInput,
)

from web.api import models


def to_engine_household(household: models.Household) -> Household:
    members = [_person_to_engine(person) for person in household.members.all()]
    accounts = [_account_to_engine(account) for account in household.accounts.all()]
    goals = [_goal_to_engine(goal) for goal in household.goals.all()]
    risk_input = RiskInput(
        household_score=household.household_risk_score,
        goals={goal.id: goal.goal_risk_score for goal in goals},
    )

    return Household(
        id=household.external_id,
        type=household.household_type,
        members=members,
        goals=goals,
        accounts=accounts,
        external_assets=household.external_assets,
        household_risk_score=household.household_risk_score,
        risk_input=risk_input,
        created_at=household.created_at,
        updated_at=household.updated_at,
    )


def _person_to_engine(person: models.Person) -> Person:
    return Person(
        id=person.external_id,
        household_id=person.household.external_id,
        name=person.name,
        dob=person.dob,
        # marital_status is `str` (not Literal) on the engine side — case
        # normalization is cosmetic but consistent with the rest of the
        # boundary. Empty stays empty.
        marital_status=_normalize_lowercase_enum(person.marital_status, ""),
        blended_family_flag=person.blended_family_flag,
        citizenship=person.citizenship,
        residency=person.residency,
        health_indicators=person.health_indicators,
        longevity_assumption=person.longevity_assumption,
        employment=person.employment,
        pensions=person.pensions,
        # Normalize case at the engine boundary — Bedrock-extracted real-
        # PII values come back capitalized ("Medium") but the engine
        # schema is `Literal["low", "medium", "high"]`. Lowercase here so
        # we don't have to plumb every extraction prompt to enforce
        # canonical case (canon §9.4.2: web layer translates DB models
        # to engine schemas at the boundary; the engine stays strict).
        investment_knowledge=_normalize_lowercase_enum(person.investment_knowledge, "medium"),
        trusted_contact_person=person.trusted_contact_person,
        poa_status=person.poa_status,
        will_status=person.will_status,
        beneficiary_designations=person.beneficiary_designations,
    )


def _account_to_engine(account: models.Account) -> Account:
    return Account(
        id=account.external_id,
        household_id=account.household.external_id,
        owner_person_id=account.owner_person.external_id if account.owner_person else None,
        type=account.account_type,
        # Normalize at engine boundary — same rationale as
        # `investment_knowledge` (canon §9.4.2: web layer translates DB
        # to engine schemas; engine stays strict). Bedrock-extracted
        # real-PII values arrive capitalized + spaced ("Growth and
        # Income"); the engine schema is `Literal["growth_and_income",
        # ...]`. Lowercase + strip + replace spaces with underscores,
        # then validate against allowed values. Per canon §9.4.5: never
        # silently default to a value the AI didn't extract — pass
        # empty through; raise on unknown non-empty.
        # Normalized strings flow into Pydantic Literal fields; the
        # runtime check is in `_normalize_regulatory_enum` (raises on
        # unknown). mypy can't see through the runtime tuple → Literal
        # narrowing, so `# type: ignore[arg-type]` is honest about
        # where the type-narrow happens (caller-side cast would be
        # equally untyped).
        regulatory_objective=_normalize_regulatory_enum(  # type: ignore[arg-type]
            account.regulatory_objective,
            ("income", "growth_and_income", "growth"),
            "regulatory_objective",
        ),
        regulatory_time_horizon=_normalize_regulatory_enum(  # type: ignore[arg-type]
            account.regulatory_time_horizon,
            ("<3y", "3-10y", ">10y"),
            "regulatory_time_horizon",
        ),
        regulatory_risk_rating=_normalize_regulatory_enum(  # type: ignore[arg-type]
            account.regulatory_risk_rating,
            ("low", "medium", "high"),
            "regulatory_risk_rating",
        ),
        current_value=_float(account.current_value),
        current_holdings=[
            Holding(
                sleeve_id=holding.sleeve_id,
                sleeve_name=holding.sleeve_name,
                weight=_float(holding.weight),
                market_value=_float(holding.market_value),
            )
            for holding in account.holdings.all()
        ],
        contribution_room=_float(account.contribution_room)
        if account.contribution_room is not None
        else None,
        contribution_history=account.contribution_history,
        is_held_at_purpose=account.is_held_at_purpose,
        missing_holdings_confirmed=account.missing_holdings_confirmed,
        cash_state=account.cash_state,
    )


def _goal_to_engine(goal: models.Goal) -> Goal:
    return Goal(
        id=goal.external_id,
        household_id=goal.household.external_id,
        name=goal.name,
        target_amount=_float(goal.target_amount) if goal.target_amount is not None else None,
        target_date=goal.target_date,
        necessity_score=goal.necessity_score,
        current_funded_amount=_float(goal.current_funded_amount),
        contribution_plan=goal.contribution_plan,
        account_allocations=[
            GoalAccountLink(
                id=link.external_id,
                goal_id=link.goal.external_id,
                account_id=link.account.external_id,
                allocated_amount=_float(link.allocated_amount)
                if link.allocated_amount is not None
                else None,
                allocated_pct=_float(link.allocated_pct)
                if link.allocated_pct is not None
                else None,
            )
            for link in goal.account_allocations.all()
        ],
        goal_risk_score=effective_goal_risk_score(goal),
        status=goal.status,
        notes=goal.notes,
    )


def _float(value: Decimal) -> float:
    return float(value)


def _normalize_lowercase_enum(value: str | None, default: str) -> str:
    """Lowercase + strip a string-enum value at the engine boundary.

    Bedrock-extracted real-PII values often come back capitalized
    ("Medium" instead of "medium") because client docs use English
    sentence case. The engine schemas are strict `Literal[...]` values
    in lowercase. Normalize here rather than push case-discipline
    upstream into every extraction prompt.

    Returns `default` for missing/empty input. Trusts that the
    lowercased result is one of the engine's allowed values; if not,
    Pydantic validation downstream will surface the structural error
    cleanly with the actual unexpected value.
    """
    if not value:
        return default
    return str(value).strip().lower() or default


def _normalize_regulatory_enum(
    value: str | None,
    allowed: tuple[str, ...],
    field_name: str,
) -> str:
    """Normalize a regulatory ``Literal`` value extracted from real-PII docs.

    Same rationale as ``_normalize_lowercase_enum`` — Bedrock returns
    capitalized + spaced versions like ``"Growth and Income"``; the
    engine schema is ``Literal["growth_and_income", ...]``. Lowercase
    + strip + replace spaces with underscores; validate against
    ``allowed``.

    Per canon §9.4.5: never silently default to a value the AI didn't
    extract. Empty/missing input passes through (downstream Pydantic
    surfaces the missing-required-field error cleanly). Unknown
    non-empty input raises ``ValueError`` with field name + actual
    value so an advisor or operator can diagnose the extraction
    mismatch.

    Phase 1 close-out 2026-05-02 — closes ENUM-CASE audit finding.
    Previously only ``investment_knowledge`` was normalized; the three
    ``regulatory_*`` fields were passed raw and silently failed engine
    validation when Bedrock returned capitalized values from
    real-PII KYC docs.
    """
    if not value:
        return ""  # downstream Pydantic surfaces the missing-required error
    normalized = str(value).strip().lower().replace(" ", "_")
    if normalized in allowed:
        return normalized
    raise ValueError(
        f"engine_adapter: {field_name}={value!r} normalizes to {normalized!r} "
        f"which is not in allowed values {allowed}. Real-PII extraction "
        "may need an advisor manual override or a prompt fix."
    )


def to_engine_cma(snapshot: models.CMASnapshot) -> CMASnapshot:
    funds = list(snapshot.fund_assumptions.all())
    fund_ids = [fund.fund_id for fund in funds]
    correlations = {
        (item.row_fund_id, item.col_fund_id): _float(item.correlation)
        for item in snapshot.correlations.all()
    }
    matrix = [
        [
            correlations.get((row_fund_id, col_fund_id), 1.0 if row_index == col_index else 0.0)
            for col_index, col_fund_id in enumerate(fund_ids)
        ]
        for row_index, row_fund_id in enumerate(fund_ids)
    ]
    return CMASnapshot(
        id=snapshot.external_id,
        version=snapshot.version,
        source=snapshot.source,
        funds=[
            FundAssumption(
                id=fund.fund_id,
                name=fund.name,
                expected_return=_float(fund.expected_return),
                volatility=_float(fund.volatility),
                optimizer_eligible=fund.optimizer_eligible,
                is_whole_portfolio=fund.is_whole_portfolio,
                aliases=fund.aliases,
                asset_class_weights=fund.asset_class_weights,
                geography_weights=fund.geography_weights,
                tax_drag=fund.tax_drag,
            )
            for fund in funds
        ],
        correlation_matrix=matrix,
    )


def committed_construction_snapshot(household: models.Household) -> dict:
    return {
        "household": {
            "id": household.external_id,
            "display_name": household.display_name,
            "household_type": household.household_type,
            "household_risk_score": household.household_risk_score,
            "external_assets": household.external_assets,
        },
        "members": [
            {
                "id": person.external_id,
                "name": person.name,
                "dob": person.dob.isoformat(),
                "investment_knowledge": person.investment_knowledge,
            }
            for person in household.members.all()
        ],
        "accounts": [
            {
                "id": account.external_id,
                "type": account.account_type,
                "current_value": str(account.current_value),
                "regulatory_objective": account.regulatory_objective,
                "regulatory_time_horizon": account.regulatory_time_horizon,
                "regulatory_risk_rating": account.regulatory_risk_rating,
                "is_held_at_purpose": account.is_held_at_purpose,
                "missing_holdings_confirmed": account.missing_holdings_confirmed,
                "cash_state": account.cash_state,
                "holdings": [
                    {
                        "sleeve_id": holding.sleeve_id,
                        "sleeve_name": holding.sleeve_name,
                        "weight": str(holding.weight),
                        "market_value": str(holding.market_value),
                    }
                    for holding in account.holdings.all()
                ],
            }
            for account in household.accounts.all()
        ],
        "goals": [
            {
                "id": goal.external_id,
                "name": goal.name,
                "target_amount": str(goal.target_amount)
                if goal.target_amount is not None
                else None,
                "target_date": goal.target_date.isoformat(),
                "necessity_score": goal.necessity_score,
                "current_funded_amount": str(goal.current_funded_amount),
                "goal_risk_score": effective_goal_risk_score(goal),
                "account_allocations": [
                    {
                        "id": link.external_id,
                        "goal_id": link.goal.external_id,
                        "account_id": link.account.external_id,
                        "allocated_amount": (
                            str(link.allocated_amount)
                            if link.allocated_amount is not None
                            else None
                        ),
                        "allocated_pct": (
                            str(link.allocated_pct) if link.allocated_pct is not None else None
                        ),
                    }
                    for link in goal.account_allocations.all()
                ],
            }
            for goal in household.goals.all()
        ],
    }


# ---------------------------------------------------------------------------
# Phase R1 v36 UI/UX rewrite adapter helpers (locked decisions #6, #11, #29).
# ---------------------------------------------------------------------------


def to_engine_risk_profile(profile: models.RiskProfile) -> RiskProfileResult:
    """Re-compute the household risk profile from persisted Q1-Q4 inputs.

    The persisted ``tolerance_score`` / ``capacity_score`` / etc. mirror the
    return shape; recomputing here keeps the engine the source of truth and
    catches drift if anyone hand-edits the persisted derived columns.
    """

    return compute_risk_profile(
        RiskProfileInput(
            q1=profile.q1,
            q2=profile.q2,
            q3=list(profile.q3 or []),
            q4=profile.q4,
        )
    )


def active_goal_override(goal: models.Goal) -> EngineGoalRiskOverride | None:
    """Return the latest GoalRiskOverride as an engine-shape struct.

    Latest-row-wins per locked decision #6. Append-only at the model
    level (no soft-delete); the most recent row is authoritative.
    """

    latest = goal.risk_overrides.order_by("-created_at", "-id").first()
    if latest is None:
        return None
    return EngineGoalRiskOverride(
        score_1_5=latest.score_1_5,
        descriptor=latest.descriptor,  # type: ignore[arg-type]
        rationale=latest.rationale,
    )


def effective_goal_risk_score(goal: models.Goal) -> int | None:
    """Return the effective goal_risk_score for engine optimization.

    The effective score is the latest GoalRiskOverride.score_1_5 if one
    exists, else the system-derived Goal.goal_risk_score. This is the
    single source of truth for what the engine optimizes against — used
    by both `_goal_to_engine` (engine input mapping) and
    `committed_construction_snapshot` (input_hash computation) so the
    REUSED-path detection and the engine output stay consistent.

    Without this resolution, saved overrides round-trip through the
    audit log + DB but never reach the engine: the input_hash matches
    the no-override seeded run, the REUSED path returns the seed, and
    the override mechanism becomes audit-only theatre. Surfaced in
    real-Chrome smoke 2026-05-04 (locked #100) on Sandra/Mike's
    `goal_ski_cabin` (8yr horizon, no horizon-cap collapse) — the
    advisor saved Cautious=1, the engine continued returning the
    Balanced-growth=4 (system) blend.

    Latest-row-wins per locked decision #6. Append-only override table.
    """

    latest = goal.risk_overrides.order_by("-created_at", "-id").first()
    if latest is None:
        return goal.goal_risk_score
    return latest.score_1_5


def current_holdings_to_pct(account: models.Account) -> dict[str, float]:
    """Convert an account's current_holdings rows to a {fund_id: pct} map.

    Used by `/api/preview/moves/` and `/api/preview/optimizer-output/` to
    feed `engine.moves.compute_rebalance_moves` and the comparison helpers.
    Weights from the model are stored as Decimal in [0, 1]; we cast to
    float for engine consumption (locked decision #6 / canon §9.4.2 — the
    engine takes plain Python types, not ORM rows).
    """

    holdings = list(account.holdings.all())
    if not holdings:
        return {}
    return {holding.sleeve_id: float(holding.weight) for holding in holdings}


def household_aum(household: models.Household) -> float:
    """Sum of committed account values + external holdings (locked #11).

    Used by `/api/preview/goal-score/` to compute the size shift on the
    fly. External holdings are included because the size shift reflects
    the goal's portion of *household* wealth, not just Steadyhand-managed.
    """

    sh_total = sum(float(account.current_value) for account in household.accounts.all())
    ext_total = sum(float(h.value) for h in household.external_holdings.all())
    return sh_total + ext_total
