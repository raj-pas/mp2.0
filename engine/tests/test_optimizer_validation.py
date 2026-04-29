from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from engine.frontier import compute_frontier
from engine.validation_pack import build_validation_pack
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from scipy.optimize import minimize


def test_default_frontier_matches_scipy_oracle_target_points() -> None:
    data = _default_fixture()
    returns = [fund["expected_return"] for fund in data["funds"]]
    volatilities = [fund["volatility"] for fund in data["funds"]]
    frontier = compute_frontier(returns, volatilities, data["correlation_matrix"])

    for index in [0, 5, 20, 45, 70]:
        point = frontier.all_points[index]
        oracle = _oracle_min_variance(
            returns,
            volatilities,
            data["correlation_matrix"],
            target_return=point.expected_return,
        )
        assert point.expected_return == pytest.approx(oracle["expected_return"], abs=1e-4)
        assert point.volatility == pytest.approx(oracle["volatility"], abs=1e-4)
        assert point.weights == pytest.approx(oracle["weights"], abs=1e-4)


@settings(max_examples=25, deadline=None)
@given(
    returns=st.lists(
        st.floats(min_value=0.01, max_value=0.12, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=3,
        unique=True,
    ),
    volatilities=st.lists(
        st.floats(min_value=0.01, max_value=0.35, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=3,
    ),
    rho=st.floats(min_value=-0.2, max_value=0.85, allow_nan=False, allow_infinity=False),
)
def test_generated_valid_frontiers_keep_core_invariants(
    returns: list[float], volatilities: list[float], rho: float
) -> None:
    assume(max(returns) - min(returns) > 0.005)
    matrix = [[1.0 if row == col else rho for col in range(3)] for row in range(3)]

    frontier = compute_frontier(returns, volatilities, matrix, steps=10)

    assert frontier.efficient
    for point in frontier.all_points:
        assert sum(point.weights) == pytest.approx(1.0)
        assert all(weight >= -1e-8 for weight in point.weights)
        assert np.isfinite(point.expected_return)
        assert np.isfinite(point.volatility)
    for candidate in frontier.efficient:
        assert not any(
            other.expected_return >= candidate.expected_return
            and other.volatility < candidate.volatility - 1e-8
            for other in frontier.efficient
        )


@pytest.mark.parametrize(
    "correlation_matrix, message",
    [
        ([[1.0, 0.5], [0.2, 1.0]], "symmetric"),
        ([[0.9, 0.2], [0.2, 1.0]], "diagonal"),
        ([[1.0, 1.0], [1.0, 1.0]], "positive definite"),
    ],
)
def test_invalid_correlation_matrices_fail_loudly(
    correlation_matrix: list[list[float]], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        compute_frontier([0.04, 0.07], [0.05, 0.12], correlation_matrix)


def test_frontier_rejects_too_few_assets() -> None:
    with pytest.raises(ValueError, match="at least two assets"):
        compute_frontier([0.04], [0.05], [[1.0]])


def test_validation_pack_matches_committed_baseline() -> None:
    baseline_path = Path("docs/validation/optimizer_validation.json")
    expected = json.loads(baseline_path.read_text())

    assert build_validation_pack() == expected


def _oracle_min_variance(
    returns: list[float],
    volatilities: list[float],
    correlation_matrix: list[list[float]],
    *,
    target_return: float,
) -> dict:
    covariance = np.array(
        [
            [
                correlation_matrix[row][col] * volatilities[row] * volatilities[col]
                for col in range(len(volatilities))
            ]
            for row in range(len(volatilities))
        ]
    )
    returns_array = np.array(returns)
    size = len(returns)
    result = minimize(
        lambda weights: float(weights.T @ covariance @ weights),
        x0=np.full(size, 1 / size),
        method="SLSQP",
        bounds=[(0.0, 1.0) for _ in range(size)],
        constraints=[
            {"type": "eq", "fun": lambda weights: np.sum(weights) - 1.0},
            {"type": "eq", "fun": lambda weights: weights @ returns_array - target_return},
        ],
        options={"ftol": 1e-12, "maxiter": 1000},
    )
    assert result.success, result.message
    weights = result.x
    variance = float(weights.T @ covariance @ weights)
    return {
        "weights": list(weights),
        "expected_return": float(weights @ returns_array),
        "volatility": float(np.sqrt(max(variance, 0.0))),
    }


def _default_fixture() -> dict:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures/default_cma_v1.json"
    return json.loads(fixture_path.read_text())
