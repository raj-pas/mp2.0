from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


def normalize_fact_value(field: str, value: Any) -> Any:
    lowered = field.lower()
    if any(
        token in lowered
        for token in (
            "current_value",
            "account_value",
            "balance",
            "balance_cad",
            "market_value",
            "market_value_cad",
            "target_amount",
            "funded_amount",
            "allocated_amount",
            "allocation_value",
            "contribution_room",
        )
    ):
        return json_number(value)
    if any(token in lowered for token in ("household_score", "risk_score", "goal_risk_score")):
        return risk_score(value, default=3)
    if any(token in lowered for token in ("horizon", "age", "necessity_score")):
        return int_or_default(value, 0)
    if any(token in lowered for token in ("missing_holdings_confirmed", "is_held_at_purpose")):
        return bool_value(value)
    if isinstance(value, str) and re.fullmatch(r"\d{1,2}/\d{1,2}/\d{2,4}", value.strip()):
        month, day, year = value.strip().split("/")
        year_number = int(year)
        if year_number < 100:
            year_number += 1900 if year_number > 30 else 2000
        return f"{year_number:04d}-{int(month):02d}-{int(day):02d}"
    if isinstance(value, str):
        return value.strip()
    return value


def number(value: Any) -> Decimal:
    try:
        if value in {None, ""}:
            return Decimal("0")
        if isinstance(value, str):
            cleaned = value.replace(",", "")
            cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
            if not cleaned or cleaned in {"-", ".", "-."}:
                return Decimal("0")
            return Decimal(cleaned)
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def json_number(value: Any) -> int | float:
    parsed = number(value)
    if parsed == parsed.to_integral_value():
        return int(parsed)
    return float(parsed)


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return normalize_key(value) in {
            "yes",
            "true",
            "confirmed",
            "missing",
            "not_available",
            "na",
        }
    return bool(value)


def int_or_default(value: Any, default: int) -> int:
    try:
        if value in {None, ""}:
            return default
        if isinstance(value, str):
            match = re.search(r"-?\d+", value)
            if match:
                return int(match.group(0))
        return int(value)
    except (TypeError, ValueError):
        return default


def risk_score(value: Any, *, default: int) -> int:
    if isinstance(value, str):
        normalized = normalize_key(value)
        qualitative_scores = {
            "very_low": 1,
            "cautious": 1,
            "low": 2,
            "conservative": 2,
            "conservative_balanced": 2,
            "medium": 3,
            "moderate": 3,
            "balanced": 3,
            "medium_risk": 3,
            "high": 4,
            "growth": 4,
            "balanced_growth": 4,
            "growth_oriented": 5,
            "very_high": 5,
        }
        if normalized in qualitative_scores:
            return qualitative_scores[normalized]
    score = int_or_default(value, default)
    if score > 5:
        score = ((score + 1) // 2) if score <= 10 else 5
    return max(1, min(score, 5))


def risk_value_is_contract_score(value: Any) -> bool:
    try:
        parsed = Decimal(str(value))
    except Exception:
        return False
    if parsed != parsed.to_integral_value():
        return False
    return Decimal("1") <= parsed <= Decimal("5")


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", " ".join(value.lower().split())).strip("_")
