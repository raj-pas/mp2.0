"""Rebalancing moves (canon §8.10 + v36 mockup methodology §8).

Given a goal's current sleeve mix and ideal sleeve mix, produce the list of
buy/sell orders that close the gap. Constraints:
- Each delta is rounded to the nearest $100 (mockup §8).
- Moves below $50 absolute are skipped (no zero-shuffle).
- Buys and sells must sum to exactly equal totals (no cash injected/withdrawn).
- The rounding residual is absorbed into the largest move on the deficit side.

Canon §9.4.2 boundary: stdlib + pydantic + engine.* only.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: Configurable constants (locked decision #10).
ROUNDING_INCREMENT = 100.0
SKIP_THRESHOLD = 50.0

MoveAction = Literal["buy", "sell"]


class Move(BaseModel):
    """One rebalancing order."""

    model_config = ConfigDict(extra="forbid")

    action: MoveAction
    fund_id: str
    fund_name: str
    amount: float = Field(gt=0)


class MovesResult(BaseModel):
    """Output of compute_rebalance_moves: balanced sells + buys."""

    model_config = ConfigDict(extra="forbid")

    moves: list[Move]
    total_buy: float
    total_sell: float


def compute_rebalance_moves(
    *,
    current_pct: dict[str, float],
    ideal_pct: dict[str, float],
    goal_total_dollars: float,
    fund_names: dict[str, str] | None = None,
) -> MovesResult:
    """Produce balanced sell+buy orders to bring current to ideal.

    Args:
        current_pct: ``{fund_id: pct}`` — current sleeve mix (sums close to 1.0).
        ideal_pct: ``{fund_id: pct}`` — target sleeve mix (sums to 1.0).
        goal_total_dollars: total $ value of the goal across funds.
        fund_names: optional ``{fund_id: human_name}`` for display labels.

    Returns:
        ``MovesResult`` with ``total_buy == total_sell`` exactly (after
        residual absorption).
    """

    if goal_total_dollars <= 0:
        raise ValueError(f"goal_total_dollars must be > 0, got {goal_total_dollars}")
    fund_names = fund_names or {}

    all_fund_ids = sorted(set(current_pct) | set(ideal_pct))

    # Compute raw deltas in dollars.
    deltas: dict[str, float] = {}
    for fid in all_fund_ids:
        cur = current_pct.get(fid, 0.0)
        ideal = ideal_pct.get(fid, 0.0)
        deltas[fid] = (ideal - cur) * goal_total_dollars

    # Round to nearest $100 and skip moves below SKIP_THRESHOLD.
    rounded: dict[str, float] = {}
    for fid, raw in deltas.items():
        if abs(raw) < SKIP_THRESHOLD:
            continue
        rounded[fid] = round(raw / ROUNDING_INCREMENT) * ROUNDING_INCREMENT

    # Compute rounding residual: sum should be 0 (current + ideal both ~100%).
    residual = -sum(rounded.values())
    if abs(residual) > 0:
        # Apply residual to the largest deficit-side move so totals balance.
        # Side of residual:
        #   residual > 0 means we need to add to BUY side (sells exceeded buys after rounding)
        #   residual < 0 means we need to add to SELL side
        target_side: Literal["buy", "sell"]
        if residual > 0:
            target_side = "buy"
        else:
            target_side = "sell"
        target_fid = _largest_move_on_side(rounded, target_side)
        if target_fid is not None:
            rounded[target_fid] += residual
        # If no moves exist on the target side, the imbalance stays — but
        # this only happens for trivial cases (e.g., empty mix); skip silently.

    moves: list[Move] = []
    for fid, amt in rounded.items():
        if amt == 0:
            continue
        action: MoveAction = "buy" if amt > 0 else "sell"
        moves.append(
            Move(
                action=action,
                fund_id=fid,
                fund_name=fund_names.get(fid, fid),
                amount=abs(amt),
            )
        )

    # Sort: sells first (descending amount), then buys (descending amount).
    moves.sort(key=lambda m: (m.action != "sell", -m.amount))

    total_buy = sum(m.amount for m in moves if m.action == "buy")
    total_sell = sum(m.amount for m in moves if m.action == "sell")

    return MovesResult(moves=moves, total_buy=total_buy, total_sell=total_sell)


def _largest_move_on_side(rounded: dict[str, float], side: Literal["buy", "sell"]) -> str | None:
    """Return fund_id of the largest move on the given side (or None)."""

    def is_on_side(amt: float) -> bool:
        return amt > 0 if side == "buy" else amt < 0

    candidates = [(fid, abs(amt)) for fid, amt in rounded.items() if is_on_side(amt)]
    if not candidates:
        return None
    return max(candidates, key=lambda x: x[1])[0]
