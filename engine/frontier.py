"""Pure-Python efficient frontier math used by the portfolio optimizer."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class FrontierPoint:
    weights: list[float]
    variance: float
    volatility: float
    expected_return: float
    value: float | None = None


@dataclass(frozen=True)
class Frontier:
    efficient: list[FrontierPoint]
    inefficient: list[FrontierPoint]
    minimum_variance: FrontierPoint | None
    all_points: list[FrontierPoint]


def norm_s_inv(p: float) -> float:
    """Inverse standard-normal CDF approximation used by the reference calculator."""

    if p <= 0:
        return -math.inf
    if p >= 1:
        return math.inf
    if p == 0.5:
        return 0.0

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
    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    if p <= 1 - p_low:
        q = p - 0.5
        r = q * q
        return ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q) / (
            ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1
        )

    q = math.sqrt(-2 * math.log(1 - p))
    return -(
        (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
        / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    )


def build_covariance(
    volatilities: list[float], correlation_matrix: list[list[float]]
) -> list[list[float]]:
    _validate_covariance_inputs(volatilities, correlation_matrix)
    return [
        [
            correlation_matrix[i][j] * volatilities[i] * volatilities[j]
            for j in range(len(volatilities))
        ]
        for i in range(len(volatilities))
    ]


def compute_frontier(
    expected_returns: list[float],
    volatilities: list[float],
    correlation_matrix: list[list[float]],
    *,
    steps: int = 70,
) -> Frontier:
    if len(expected_returns) != len(volatilities):
        raise ValueError("expected_returns and volatilities must have the same length")
    if len(expected_returns) < 2:
        raise ValueError("at least two assets are required to compute a frontier")
    if any(not math.isfinite(value) for value in expected_returns):
        raise ValueError("expected_returns must be finite")
    covariance = build_covariance(volatilities, correlation_matrix)
    min_return = min(expected_returns)
    max_return = max(expected_returns)
    points: list[FrontierPoint] = []

    for step in range(steps + 1):
        target = min_return + ((max_return - min_return) * step) / steps
        best: FrontierPoint | None = None
        for subset in _subsets(len(expected_returns)):
            solution = solve_subset(covariance, expected_returns, target, subset)
            if solution and (best is None or solution.variance < best.variance):
                best = solution
        if best:
            points.append(best)

    if not points:
        return Frontier(efficient=[], inefficient=[], minimum_variance=None, all_points=[])

    min_variance_index = min(range(len(points)), key=lambda index: points[index].variance)
    return Frontier(
        efficient=_pareto_filter(points[min_variance_index:]),
        inefficient=points[: min_variance_index + 1],
        minimum_variance=points[min_variance_index],
        all_points=points,
    )


def _pareto_filter(candidates: list[FrontierPoint]) -> list[FrontierPoint]:
    """Drop dominated points (same-or-higher return at lower vol).

    The candidate set is the slice of computed points from
    ``minimum_variance_index`` onwards; numerical noise around equal-
    return regions (degenerate subsets, near-singular covariance) can
    leave a dominated point in the slice. The Pareto filter restores
    the frontier's monotonic invariant: for every kept point there is
    no other kept point with ≥ return AND < volatility (within a
    1e-9 numerical tolerance).
    """

    EPSILON = 1e-9
    survivors: list[FrontierPoint] = []
    for i, p in enumerate(candidates):
        dominated = False
        for j, q in enumerate(candidates):
            if i == j:
                continue
            return_no_worse = q.expected_return >= p.expected_return - EPSILON
            vol_strictly_better = q.volatility < p.volatility - EPSILON
            return_strictly_better = q.expected_return > p.expected_return + EPSILON
            vol_no_worse = q.volatility <= p.volatility + EPSILON
            if (return_no_worse and vol_strictly_better) or (
                return_strictly_better and vol_no_worse
            ):
                dominated = True
                break
        if not dominated:
            survivors.append(p)
    return survivors


def solve_subset(
    covariance: list[list[float]],
    expected_returns: list[float],
    target_return: float,
    subset: list[int],
) -> FrontierPoint | None:
    sigma = [[covariance[i][j] for j in subset] for i in subset]
    subset_returns = [expected_returns[i] for i in subset]
    sigma_inverse = _matrix_inverse(sigma)
    if sigma_inverse is None:
        return None

    sigma_inverse_ones = [sum(row) for row in sigma_inverse]
    sigma_inverse_returns = [
        sum(value * subset_returns[j] for j, value in enumerate(row)) for row in sigma_inverse
    ]
    a = sum(sigma_inverse_ones)
    b = sum(sigma_inverse_returns)
    d = sum(value * sigma_inverse_returns[index] for index, value in enumerate(subset_returns))
    determinant = a * d - b * b
    if abs(determinant) < 1e-14:
        return None

    subset_weights = [
        ((d - b * target_return) * value + (a * target_return - b) * sigma_inverse_returns[index])
        / determinant
        for index, value in enumerate(sigma_inverse_ones)
    ]
    if any(weight < -1e-7 for weight in subset_weights):
        return None

    weights = [0.0 for _ in expected_returns]
    for subset_index, asset_index in enumerate(subset):
        weights[asset_index] = max(0.0, subset_weights[subset_index])

    weight_sum = sum(weights)
    if weight_sum < 1e-9:
        return None
    weights = [weight / weight_sum for weight in weights]
    variance = _portfolio_variance(weights, covariance)
    expected_return = sum(weight * expected_returns[index] for index, weight in enumerate(weights))
    return FrontierPoint(
        weights=weights,
        variance=variance,
        volatility=math.sqrt(max(0.0, variance)),
        expected_return=expected_return,
    )


def optimal_on_frontier(
    efficient_frontier: list[FrontierPoint],
    *,
    periods: float,
    percentile: int,
    starting_value: float,
) -> FrontierPoint | None:
    if not efficient_frontier:
        return None
    z_score = norm_s_inv(percentile / 100)
    best: FrontierPoint | None = None
    best_value = -math.inf
    for point in efficient_frontier:
        value = projected_value(
            starting_value=starting_value,
            expected_return=point.expected_return,
            volatility=point.volatility,
            periods=periods,
            z_score=z_score,
        )
        if value > best_value:
            best_value = value
            best = point
    if best is None:
        return None
    return FrontierPoint(
        weights=best.weights,
        variance=best.variance,
        volatility=best.volatility,
        expected_return=best.expected_return,
        value=best_value,
    )


def evaluate_portfolio(
    weights: list[float],
    expected_returns: list[float],
    volatilities: list[float],
    correlation_matrix: list[list[float]],
    *,
    periods: float,
    percentile: int,
    starting_value: float,
) -> FrontierPoint:
    covariance = build_covariance(volatilities, correlation_matrix)
    expected_return = sum(weight * expected_returns[index] for index, weight in enumerate(weights))
    variance = _portfolio_variance(weights, covariance)
    volatility = math.sqrt(max(0.0, variance))
    value = projected_value(
        starting_value=starting_value,
        expected_return=expected_return,
        volatility=volatility,
        periods=periods,
        z_score=norm_s_inv(percentile / 100),
    )
    return FrontierPoint(
        weights=list(weights),
        variance=variance,
        volatility=volatility,
        expected_return=expected_return,
        value=value,
    )


def projected_value(
    *,
    starting_value: float,
    expected_return: float,
    volatility: float,
    periods: float,
    z_score: float,
) -> float:
    return starting_value * math.exp(
        (expected_return - volatility * volatility / 2) * periods
        + volatility * math.sqrt(periods) * z_score
    )


def percentile_projection(
    *,
    starting_value: float,
    expected_return: float,
    volatility: float,
    periods: float,
    percentile: int,
) -> float:
    return projected_value(
        starting_value=starting_value,
        expected_return=expected_return,
        volatility=volatility,
        periods=periods,
        z_score=norm_s_inv(percentile / 100),
    )


def _subsets(size: int) -> list[list[int]]:
    subsets: list[list[int]] = []
    for length in range(2, size + 1):
        subsets.extend([list(subset) for subset in combinations(range(size), length)])
    return subsets


def _portfolio_variance(weights: list[float], covariance: list[list[float]]) -> float:
    variance = 0.0
    for i, weight_i in enumerate(weights):
        for j, weight_j in enumerate(weights):
            variance += weight_i * weight_j * covariance[i][j]
    return variance


def _validate_covariance_inputs(
    volatilities: list[float], correlation_matrix: list[list[float]]
) -> None:
    size = len(volatilities)
    if size < 2:
        raise ValueError("at least two volatilities are required")
    if any(value < 0 or not math.isfinite(value) for value in volatilities):
        raise ValueError("volatilities must be finite non-negative values")
    if len(correlation_matrix) != size or any(len(row) != size for row in correlation_matrix):
        raise ValueError("correlation matrix dimensions must match volatilities")
    for row_index, row in enumerate(correlation_matrix):
        for column_index, value in enumerate(row):
            if not math.isfinite(value) or value < -1 or value > 1:
                raise ValueError("correlations must be finite values between -1 and 1")
            if row_index == column_index and abs(value - 1.0) > 1e-8:
                raise ValueError("correlation matrix diagonal must be 1")
            if abs(value - correlation_matrix[column_index][row_index]) > 1e-8:
                raise ValueError("correlation matrix must be symmetric")
    if not _is_positive_definite(correlation_matrix):
        raise ValueError("correlation matrix must be positive definite")


def _is_positive_definite(matrix: list[list[float]]) -> bool:
    size = len(matrix)
    lower = [[0.0 for _ in range(size)] for _ in range(size)]
    for row in range(size):
        for column in range(row + 1):
            subtotal = sum(lower[row][k] * lower[column][k] for k in range(column))
            if row == column:
                value = matrix[row][row] - subtotal
                if value <= 1e-10:
                    return False
                lower[row][column] = math.sqrt(value)
            else:
                lower[row][column] = (matrix[row][column] - subtotal) / lower[column][column]
    return True


def _matrix_inverse(matrix: list[list[float]]) -> list[list[float]] | None:
    size = len(matrix)
    augmented = [
        [*row, *[1.0 if row_index == column_index else 0.0 for column_index in range(size)]]
        for row_index, row in enumerate(matrix)
    ]

    for index in range(size):
        pivot = max(range(index, size), key=lambda row_index: abs(augmented[row_index][index]))
        if abs(augmented[pivot][index]) < 1e-14:
            return None
        augmented[index], augmented[pivot] = augmented[pivot], augmented[index]

        divisor = augmented[index][index]
        augmented[index] = [value / divisor for value in augmented[index]]
        for row_index in range(size):
            if row_index == index:
                continue
            factor = augmented[row_index][index]
            augmented[row_index] = [
                value - factor * augmented[index][column_index]
                for column_index, value in enumerate(augmented[row_index])
            ]

    return [row[size:] for row in augmented]
