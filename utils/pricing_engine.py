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


def run_pricing_engine(
    sales_data: dict[str, Any],
    market_data: dict[str, Any],
) -> dict[str, Any]:
    daily_inputs = market_data["daily_inputs"]
    total_rooms = int(market_data["total_rooms"])
    group_adr_growth = market_data["adr_growth_pct"] / 100
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
        pms_forecast_rooms = int(round(row["pms_forecast_rooms"]))
        pms_forecast_adr = float(row.get("pms_forecast_adr", 0.0))

        hist_group_adr_baseline = _avg(hist_adr)
        hist_group_occ_baseline = _avg(hist_occ)
        group_adr_yoy_trend = _yoy_trend(hist_adr)
        after_group_yoy_trend_adr = hist_group_adr_baseline * (1 + group_adr_yoy_trend)
        daily_indicated_group_rate = after_group_yoy_trend_adr * (1 + group_adr_growth)
        yoy_1 = ((hist_adr[1] - hist_adr[0]) / hist_adr[0]) if hist_adr[0] else 0.0
        yoy_2 = ((hist_adr[2] - hist_adr[1]) / hist_adr[1]) if hist_adr[1] else 0.0

        total_demand_after_group = pms_forecast_rooms + group_rooms
        displaced_rooms = max(total_demand_after_group - total_rooms, 0)

        daily_results.append({
            "stay_date": row["stay_date"],
            "group_rooms": group_rooms,
            "pms_forecast_rooms": pms_forecast_rooms,
            "total_demand_after_group": total_demand_after_group,
            "hotel_capacity": total_rooms,
            "displaced_rooms": int(displaced_rooms),
            "pace_adjustment": round(pace_adj, 3),
            "str_adjustment": round(str_adj, 3),
            "hist_occ": hist_occ,
            "hist_adr": hist_adr,
            "pms_forecast_adr": round(pms_forecast_adr, 2),
            "avg_hist_adr": round(hist_group_adr_baseline, 2),
            "avg_hist_occ": round(hist_group_occ_baseline, 2),
            "hist_group_adr_baseline": round(hist_group_adr_baseline, 2),
            "hist_group_occ_baseline": round(hist_group_occ_baseline, 2),
            "yoy_1": round(yoy_1 * 100, 2),
            "yoy_2": round(yoy_2 * 100, 2),
            "yoy_trend": round(group_adr_yoy_trend * 100, 2),
            "group_adr_yoy_trend": round(group_adr_yoy_trend * 100, 2),
            "after_group_yoy_trend_adr": round(after_group_yoy_trend_adr, 2),
            "daily_indicated_group_rate": round(daily_indicated_group_rate, 2),
            "daily_recommended_rate": round(daily_indicated_group_rate, 2),
        })

    total_group_room_nights = sum(row["group_rooms"] for row in daily_results)
    total_displaced_room_nights = sum(row["displaced_rooms"] for row in daily_results)
    recommended_rate = _round_up_5(
        sum(row["daily_indicated_group_rate"] * row["group_rooms"] for row in daily_results) / total_group_room_nights
        if total_group_room_nights
        else 0
    )

    for row in daily_results:
        group_revenue = row["group_rooms"] * recommended_rate
        displaced_revenue = row["displaced_rooms"] * row["pms_forecast_adr"]
        row["group_revenue"] = round(group_revenue, 2)
        row["displaced_revenue"] = round(displaced_revenue, 2)
        row["net_revenue_position"] = round(group_revenue - displaced_revenue, 2)

    total_group_revenue = sum(row["group_revenue"] for row in daily_results)
    total_displaced_revenue = sum(row["displaced_revenue"] for row in daily_results)
    net_revenue_position = total_group_revenue - total_displaced_revenue

    if total_group_room_nights:
        weighted_pms_forecast_adr = (
            sum(row["pms_forecast_adr"] * row["group_rooms"] for row in daily_results)
            / total_group_room_nights
        )
    else:
        weighted_pms_forecast_adr = _avg([row["pms_forecast_adr"] for row in daily_results])

    rate_vs_forecast_adr_pct = (
        recommended_rate / weighted_pms_forecast_adr * 100 if weighted_pms_forecast_adr else 0.0
    )
    rate_vs_forecast_adr_gap = recommended_rate - weighted_pms_forecast_adr

    return {
        "daily_results": daily_results,
        "avg_hist_adr": round(_avg([row["avg_hist_adr"] for row in daily_results]), 2),
        "avg_hist_occ": round(_avg([row["avg_hist_occ"] for row in daily_results]), 2),
        "yoy_trend": round(_avg([row["yoy_trend"] for row in daily_results]), 2),
        "weighted_pms_forecast_adr": round(weighted_pms_forecast_adr, 2),
        "recommended_rate": recommended_rate,
        "rate_vs_forecast_adr_pct": round(rate_vs_forecast_adr_pct, 1),
        "rate_vs_forecast_adr_gap": round(rate_vs_forecast_adr_gap, 2),
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
