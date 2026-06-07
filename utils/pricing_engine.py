"""
pricing_engine.py
─────────────────
Core group pricing logic for the Group Pricing Intelligence Tool.

The manager enters their own proposed rate directly. The engine computes the
projected transient ADR for context, runs displacement math against the
proposed rate, and returns market signals for decision support.
"""

from __future__ import annotations

import math
from typing import Any

__all__ = [
    "run_pricing_engine",
    "_round_up_10",
]


def _round_up_10(value: float) -> int:
    """
    Round up to the nearest $10.
    """
    return math.ceil(value / 10) * 10


def _displacement_risk_label(displaced_rn: int, room_block_rn: int) -> str:
    """
    Single source of truth for displacement risk label.

    LOW    = 0 rooms displaced
    MEDIUM = 1-49% of group block displaced
    HIGH   = 50%+ of group block displaced
    """
    if displaced_rn == 0:
        return "LOW"
    if displaced_rn < room_block_rn * 0.50:
        return "MEDIUM"
    return "HIGH"


def _forecasted_transient_rooms_by_date(
    market_data: dict[str, Any],
    nights: int,
    total_rooms: int,
) -> list[int]:
    """
    Return forecasted transient rooms for each stay date.

    The current UI captures one forecasted occupancy value for the stay period.
    If a future UI supplies per-date transient room forecasts, the engine will
    use those directly.
    """
    if "forecasted_transient_rooms" in market_data:
        forecasts = list(market_data["forecasted_transient_rooms"])
        if len(forecasts) != nights:
            raise ValueError("forecasted_transient_rooms must match number of stay nights")
        return [max(int(round(value)), 0) for value in forecasts]

    curr_occ = market_data["curr_occ"]
    forecasted_rooms = round((curr_occ / 100) * total_rooms)
    return [forecasted_rooms] * nights


def run_pricing_engine(
    sales_data: dict[str, Any],
    market_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate a manager-proposed group rate against market context and
    displacement math.
    """
    nights = sales_data["nights"]
    room_block = sales_data["room_block"]

    hist_adr = market_data["hist_adr"]
    hist_occ = market_data["hist_occ"]
    total_rooms = market_data["total_rooms"]
    pace_otb = market_data["pace_otb"]
    pace_stly = market_data["pace_stly"]
    adr_growth = market_data["adr_growth_pct"]
    proposed_rate = market_data["proposed_rate"]

    avg_hist_adr = sum(hist_adr) / len(hist_adr) if hist_adr else 0.0
    avg_hist_occ = sum(hist_occ) / len(hist_occ) if hist_occ else 0.0

    changes = []
    for idx in range(1, len(hist_adr)):
        prior = hist_adr[idx - 1]
        if prior:
            changes.append((hist_adr[idx] - prior) / prior * 100)
    yoy_trend = sum(changes) / len(changes) if changes else 0.0

    after_hist_trend = avg_hist_adr * (1 + yoy_trend / 100)
    proj_transient_adr = after_hist_trend * (1 + adr_growth / 100)

    rate_vs_transient_pct = (
        proposed_rate / proj_transient_adr * 100 if proj_transient_adr else 0.0
    )
    rate_vs_transient_gap = proposed_rate - proj_transient_adr

    group_rn = room_block * nights
    forecasted_transient_rooms = _forecasted_transient_rooms_by_date(
        market_data,
        nights,
        total_rooms,
    )
    available_inventory_by_date = [
        max(total_rooms - forecast_rooms, 0)
        for forecast_rooms in forecasted_transient_rooms
    ]
    displaced_rooms_by_date = [
        max((forecast_rooms + room_block) - total_rooms, 0)
        for forecast_rooms in forecasted_transient_rooms
    ]
    displaced_rn = sum(displaced_rooms_by_date)
    displaced_revenue = displaced_rn * proj_transient_adr
    displacement_risk = _displacement_risk_label(displaced_rn, group_rn)

    group_rev_proposed = group_rn * proposed_rate
    net_revenue_position = group_rev_proposed - displaced_revenue
    displacement_cost = max(displaced_revenue - group_rev_proposed, 0)

    return {
        "avg_hist_adr": round(avg_hist_adr, 2),
        "avg_hist_occ": avg_hist_occ,
        "yoy_trend": round(yoy_trend, 2),
        "proj_transient_adr": round(proj_transient_adr, 2),
        "proposed_rate": proposed_rate,
        "rate_vs_transient_pct": round(rate_vs_transient_pct, 1),
        "rate_vs_transient_gap": round(rate_vs_transient_gap, 2),
        "displaced_room_nights": int(displaced_rn),
        "forecasted_transient_rooms_by_date": forecasted_transient_rooms,
        "available_inventory_by_date": available_inventory_by_date,
        "displaced_rooms_by_date": displaced_rooms_by_date,
        "displaced_revenue": round(displaced_revenue, 2),
        "displacement_risk": displacement_risk,
        "displacement_cost": round(displacement_cost, 2),
        "group_rev_proposed": round(group_rev_proposed, 2),
        "net_revenue_position": round(net_revenue_position, 2),
        "total_room_nights": group_rn,
        "pace_variance": pace_otb - pace_stly,
    }
