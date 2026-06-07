"""
pricing_engine.py
-----------------
Daily group displacement logic for the Group Pricing Intelligence Tool.

Each stay night is evaluated independently, then totals are summed.
"""

from __future__ import annotations

import math
from typing import Any

__all__ = ["run_pricing_engine"]


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _yoy_trend(adr_values: list[float]) -> float:
    changes = []
    for idx in range(1, len(adr_values)):
        prior = adr_values[idx - 1]
        if prior:
            changes.append((adr_values[idx] - prior) / prior)
    return _avg(changes)


def _displacement_risk_label(displaced_rn: int, total_group_rn: int) -> str:
    if displaced_rn == 0:
        return "LOW"
    if total_group_rn and displaced_rn < total_group_rn * 0.50:
        return "MEDIUM"
    return "HIGH"


def _round_up_5(value: float) -> int:
    return int(math.ceil(value / 5) * 5)


def _pace_adjustment(pace_otb: int, pace_stly: int) -> float:
    delta = pace_otb - pace_stly
    if delta >= 30:
        return 0.03
    if delta >= 10:
        return 0.015
    if delta <= -30:
        return -0.03
    if delta <= -10:
        return -0.015
    return 0.0


def _str_adjustment(mpi: float, ari: float, comp_occ: float) -> float:
    adjustment = 0.0
    if mpi >= 105:
        adjustment += 0.015
    elif mpi < 95:
        adjustment -= 0.015
    if ari >= 105:
        adjustment += 0.015
    elif ari < 95:
        adjustment -= 0.015
    if comp_occ >= 85:
        adjustment += 0.015
    elif comp_occ >= 75:
        adjustment += 0.0075
    elif comp_occ < 55:
        adjustment -= 0.015
    return adjustment


def _occupancy_adjustment(occupancy_pct: float) -> float:
    if occupancy_pct >= 95:
        return 0.10
    if occupancy_pct >= 85:
        return 0.07
    if occupancy_pct >= 75:
        return 0.04
    if occupancy_pct >= 60:
        return 0.00
    return -0.04


def run_pricing_engine(
    sales_data: dict[str, Any],
    market_data: dict[str, Any],
) -> dict[str, Any]:
    daily_inputs = market_data["daily_inputs"]
    total_rooms = int(market_data["total_rooms"])
    adr_growth = market_data["adr_growth_pct"] / 100
    pace_adj = _pace_adjustment(market_data["pace_otb"], market_data["pace_stly"])
    str_adj = _str_adjustment(
        market_data["str_mpi"],
        market_data["str_ari"],
        market_data.get("str_comp_occ", 0.0),
    )

    daily_results = []
    for row in daily_inputs:
        group_rooms = int(row["group_rooms"])
        hist_occ = [float(value) for value in row["hist_occ"]]
        hist_adr = [float(value) for value in row["hist_adr"]]
        forecasted_transient_rooms = int(round(row["forecasted_transient_rooms"]))
        current_adr_on_books = float(row.get("curr_adr", 0.0))

        avg_hist_adr = _avg(hist_adr)
        avg_hist_occ = _avg(hist_occ)
        yoy_trend = _yoy_trend(hist_adr)
        after_yoy_trend_adr = avg_hist_adr * (1 + yoy_trend)
        historical_projected_adr = after_yoy_trend_adr * (1 + adr_growth)
        projected_transient_adr = max(historical_projected_adr, current_adr_on_books)
        yoy_1 = ((hist_adr[1] - hist_adr[0]) / hist_adr[0]) if hist_adr[0] else 0.0
        yoy_2 = ((hist_adr[2] - hist_adr[1]) / hist_adr[1]) if hist_adr[1] else 0.0

        total_demand_after_group = forecasted_transient_rooms + group_rooms
        displaced_rooms = max(total_demand_after_group - total_rooms, 0)
        forecast_occ_pct = (forecasted_transient_rooms / total_rooms * 100) if total_rooms else 0.0
        displaced_share = (displaced_rooms / group_rooms) if group_rooms else 0.0
        occupancy_adj = _occupancy_adjustment(forecast_occ_pct)
        displacement_adj = min(displaced_share * 0.12, 0.12)
        rate_multiplier = min(
            max(
                0.84
                + occupancy_adj
                + displacement_adj
                + pace_adj
                + str_adj,
                0.72,
            ),
            1.05,
        )
        daily_recommended_rate = projected_transient_adr * rate_multiplier

        daily_results.append({
            "stay_date": row["stay_date"],
            "group_rooms": group_rooms,
            "forecasted_transient_rooms": forecasted_transient_rooms,
            "total_demand_after_group": total_demand_after_group,
            "hotel_capacity": total_rooms,
            "displaced_rooms": int(displaced_rooms),
            "forecast_occ_pct": round(forecast_occ_pct, 1),
            "displaced_share": round(displaced_share * 100, 1),
            "base_group_multiplier": 0.84,
            "occupancy_adjustment": round(occupancy_adj, 3),
            "displacement_adjustment": round(displacement_adj, 3),
            "pace_adjustment": round(pace_adj, 3),
            "str_adjustment": round(str_adj, 3),
            "hist_occ": hist_occ,
            "hist_adr": hist_adr,
            "current_adr_on_books": round(current_adr_on_books, 2),
            "avg_hist_adr": round(avg_hist_adr, 2),
            "avg_hist_occ": round(avg_hist_occ, 2),
            "yoy_1": round(yoy_1 * 100, 2),
            "yoy_2": round(yoy_2 * 100, 2),
            "yoy_trend": round(yoy_trend * 100, 2),
            "after_yoy_trend_adr": round(after_yoy_trend_adr, 2),
            "historical_projected_adr": round(historical_projected_adr, 2),
            "projected_transient_adr": round(projected_transient_adr, 2),
            "rate_multiplier": round(rate_multiplier, 3),
            "daily_recommended_rate": round(daily_recommended_rate, 2),
        })

    total_group_room_nights = sum(row["group_rooms"] for row in daily_results)
    total_displaced_room_nights = sum(row["displaced_rooms"] for row in daily_results)
    recommended_rate = _round_up_5(
        sum(row["daily_recommended_rate"] * row["group_rooms"] for row in daily_results) / total_group_room_nights
        if total_group_room_nights
        else 0
    )

    for row in daily_results:
        group_revenue = row["group_rooms"] * recommended_rate
        displaced_revenue = row["displaced_rooms"] * row["projected_transient_adr"]
        row["group_revenue"] = round(group_revenue, 2)
        row["displaced_revenue"] = round(displaced_revenue, 2)
        row["net_revenue_position"] = round(group_revenue - displaced_revenue, 2)

    total_group_revenue = sum(row["group_revenue"] for row in daily_results)
    total_displaced_revenue = sum(row["displaced_revenue"] for row in daily_results)
    net_revenue_position = total_group_revenue - total_displaced_revenue

    if total_group_room_nights:
        weighted_transient_adr = (
            sum(row["projected_transient_adr"] * row["group_rooms"] for row in daily_results)
            / total_group_room_nights
        )
    else:
        weighted_transient_adr = _avg([row["projected_transient_adr"] for row in daily_results])

    rate_vs_transient_pct = (
        recommended_rate / weighted_transient_adr * 100 if weighted_transient_adr else 0.0
    )
    rate_vs_transient_gap = recommended_rate - weighted_transient_adr

    return {
        "daily_results": daily_results,
        "avg_hist_adr": round(_avg([row["avg_hist_adr"] for row in daily_results]), 2),
        "avg_hist_occ": round(_avg([row["avg_hist_occ"] for row in daily_results]), 2),
        "yoy_trend": round(_avg([row["yoy_trend"] for row in daily_results]), 2),
        "proj_transient_adr": round(weighted_transient_adr, 2),
        "recommended_rate": recommended_rate,
        "rate_vs_transient_pct": round(rate_vs_transient_pct, 1),
        "rate_vs_transient_gap": round(rate_vs_transient_gap, 2),
        "displaced_room_nights": int(total_displaced_room_nights),
        "displaced_revenue": round(total_displaced_revenue, 2),
        "displacement_risk": _displacement_risk_label(
            int(total_displaced_room_nights),
            int(total_group_room_nights),
        ),
        "displacement_cost": round(max(total_displaced_revenue - total_group_revenue, 0), 2),
        "group_rev_recommended": round(total_group_revenue, 2),
        "net_revenue_position": round(net_revenue_position, 2),
        "total_room_nights": int(total_group_room_nights),
        "pace_variance": market_data["pace_otb"] - market_data["pace_stly"],
        "pace_adjustment": pace_adj,
        "str_adjustment": str_adj,
    }
