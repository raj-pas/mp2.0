from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from engine.frontier import compute_frontier, optimal_on_frontier

RISK_TO_PERCENTILE = {1: 5, 2: 15, 3: 25, 4: 35, 5: 45}


def build_validation_pack() -> dict[str, Any]:
    data = _default_fixture()
    returns = [fund["expected_return"] for fund in data["funds"]]
    volatilities = [fund["volatility"] for fund in data["funds"]]
    frontier = compute_frontier(returns, volatilities, data["correlation_matrix"])
    if frontier.minimum_variance is None:
        raise ValueError("Default CMA fixture did not produce a minimum variance point.")

    risk_score_points = {}
    for risk_score, percentile in RISK_TO_PERCENTILE.items():
        point = optimal_on_frontier(
            frontier.efficient,
            periods=5,
            percentile=percentile,
            starting_value=100_000,
        )
        if point is None:
            raise ValueError(f"No frontier point for risk score {risk_score}.")
        risk_score_points[str(risk_score)] = _point_summary(point, percentile=percentile)

    representative_outputs = [
        {
            "goal_id": "synthetic_retirement",
            "account_id": "synthetic_rrsp",
            "allocated_amount": 250_000,
            "horizon_years": 5,
            "goal_risk_score": 3,
            "selected_point": risk_score_points["3"],
        },
        {
            "goal_id": "synthetic_education",
            "account_id": "synthetic_resp",
            "allocated_amount": 60_000,
            "horizon_years": 3,
            "goal_risk_score": 1,
            "selected_point": risk_score_points["1"],
        },
    ]
    assumptions_hash = _hash_json(
        {
            "funds": data["funds"],
            "correlation_matrix": data["correlation_matrix"],
        }
    )
    frontier_summary = {
        "efficient_point_count": len(frontier.efficient),
        "all_point_count": len(frontier.all_points),
        "minimum_variance": _point_summary(frontier.minimum_variance),
        "highest_return": _point_summary(
            max(frontier.efficient, key=lambda point: point.expected_return)
        ),
    }
    return {
        "schema_version": "optimizer_validation_pack.v1",
        "status": "internal_validation_evidence_only",
        "source": data["source_note"],
        "assumptions": {
            "fund_count": len(data["funds"]),
            "eligible_fund_count": sum(1 for fund in data["funds"] if fund["optimizer_eligible"]),
            "whole_portfolio_fund_count": sum(
                1 for fund in data["funds"] if fund["is_whole_portfolio"]
            ),
            "funds": data["funds"],
            "assumptions_hash": assumptions_hash,
        },
        "frontier_summary": frontier_summary,
        "risk_score_selected_points": risk_score_points,
        "representative_goal_account_outputs": representative_outputs,
        "edge_case_outcomes": [
            {
                "case": "too_few_eligible_funds",
                "expected": "clear failure before optimization",
            },
            {
                "case": "singular_correlation_matrix",
                "expected": "correlation matrix validation failure",
            },
            {
                "case": "low_volatility_cash",
                "expected": "accepted when the matrix remains positive definite",
            },
            {
                "case": "all_risk_scores",
                "expected": "risk scores 1-5 map to percentiles 5/15/25/35/45",
            },
        ],
        "warnings": [
            "Synthetic validation only.",
            "Requires human review before real-client pilot use.",
        ],
        "hashes": {
            "assumptions_hash": assumptions_hash,
            "frontier_summary_hash": _hash_json(frontier_summary),
            "risk_score_points_hash": _hash_json(risk_score_points),
        },
        "audit_references": [
            {
                "action": "cma_snapshot_seeded",
                "metadata": ["version", "source", "fund_count", "snapshot_name"],
            },
            {
                "action": "cma_snapshot_updated",
                "metadata": [
                    "before_hash",
                    "after_hash",
                    "fund_diffs",
                    "correlation_pair_diffs",
                ],
            },
            {
                "action": "cma_snapshot_published",
                "metadata": ["publish_note", "snapshot_hash", "stale_portfolio_run_count"],
            },
        ],
    }


def markdown_for_validation_pack(pack: dict[str, Any]) -> str:
    risk_rows = "\n".join(
        f"| {risk} | {point['frontier_percentile']} | {point['expected_return']:.6f} | "
        f"{point['volatility']:.6f} |"
        for risk, point in pack["risk_score_selected_points"].items()
    )
    return f"""# Optimizer Validation Pack

Status: internal validation evidence only.

Source: {pack["source"]}

## Frontier Summary

- Efficient points: {pack["frontier_summary"]["efficient_point_count"]}
- Funds: {pack["assumptions"]["fund_count"]}
- Assumptions hash: `{pack["hashes"]["assumptions_hash"]}`

## Risk Score Selected Points

| Risk score | Percentile | Expected return | Volatility |
| --- | ---: | ---: | ---: |
{risk_rows}

## Warnings

- Synthetic data only.
- This evidence does not by itself authorize real-client pilot use.
"""


def _default_fixture() -> dict[str, Any]:
    fixture_path = Path(__file__).resolve().parent / "fixtures/default_cma_v1.json"
    return json.loads(fixture_path.read_text())


def _point_summary(point, *, percentile: int | None = None) -> dict[str, Any]:  # noqa: ANN001
    payload: dict[str, Any] = {
        "expected_return": round(point.expected_return, 10),
        "volatility": round(point.volatility, 10),
        "weights": [round(weight, 10) for weight in point.weights],
    }
    if percentile is not None:
        payload["frontier_percentile"] = percentile
    if point.value is not None:
        payload["projected_value"] = round(point.value, 2)
    return payload


def _hash_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
