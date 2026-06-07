"""
pricing_engine.py
-----------------
Daily group displacement logic for the Group Pricing Intelligence Tool.

Each stay night is evaluated independently, then totals are summed.
"""

from __future__ import annotations

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


def run_pricing_engine(
    sales_data: dict[str, Any],
    market_data: dict[str, Any],
) -> dict[str, Any]:
    daily_inputs = market_data["daily_inputs"]
    total_rooms = int(market_data["total_rooms"])
    adr_growth = market_data["adr_growth_pct"] / 100
    proposed_rate = float(market_data["proposed_rate"])

    daily_results = []
    for row in daily_inputs:
        group_rooms = int(row["group_rooms"])
        hist_occ = [float(value) for value in row["hist_occ"]]
        hist_adr = [float(value) for value in row["hist_adr"]]
        forecasted_transient_rooms = int(round(row["forecasted_transient_rooms"]))

        avg_hist_adr = _avg(hist_adr)
        avg_hist_occ = _avg(hist_occ)
        yoy_trend = _yoy_trend(hist_adr)
        projected_transient_adr = avg_hist_adr * (1 + yoy_trend) * (1 + adr_growth)

        total_demand_after_group = forecasted_transient_rooms + group_rooms
        displaced_rooms = max(total_demand_after_group - total_rooms, 0)
        group_revenue = group_rooms * proposed_rate
        displaced_revenue = displaced_rooms * projected_transient_adr

        daily_results.append({
            "stay_date": row["stay_date"],
            "group_rooms": group_rooms,
            "forecasted_transient_rooms": forecasted_transient_rooms,
            "total_demand_after_group": total_demand_after_group,
            "hotel_capacity": total_rooms,
            "displaced_rooms": int(displaced_rooms),
            "avg_hist_adr": round(avg_hist_adr, 2),
            "avg_hist_occ": round(avg_hist_occ, 2),
            "yoy_trend": round(yoy_trend * 100, 2),
            "projected_transient_adr": round(projected_transient_adr, 2),
            "group_revenue": round(group_revenue, 2),
            "displaced_revenue": round(displaced_revenue, 2),
            "net_revenue_position": round(group_revenue - displaced_revenue, 2),
        })

    total_group_room_nights = sum(row["group_rooms"] for row in daily_results)
    total_group_revenue = sum(row["group_revenue"] for row in daily_results)
    total_displaced_room_nights = sum(row["displaced_rooms"] for row in daily_results)
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
        proposed_rate / weighted_transient_adr * 100 if weighted_transient_adr else 0.0
    )
    rate_vs_transient_gap = proposed_rate - weighted_transient_adr

    return {
        "daily_results": daily_results,
        "avg_hist_adr": round(_avg([row["avg_hist_adr"] for row in daily_results]), 2),
        "avg_hist_occ": round(_avg([row["avg_hist_occ"] for row in daily_results]), 2),
        "yoy_trend": round(_avg([row["yoy_trend"] for row in daily_results]), 2),
        "proj_transient_adr": round(weighted_transient_adr, 2),
        "proposed_rate": proposed_rate,
        "rate_vs_transient_pct": round(rate_vs_transient_pct, 1),
        "rate_vs_transient_gap": round(rate_vs_transient_gap, 2),
        "displaced_room_nights": int(total_displaced_room_nights),
        "displaced_revenue": round(total_displaced_revenue, 2),
        "displacement_risk": _displacement_risk_label(
            int(total_displaced_room_nights),
            int(total_group_room_nights),
        ),
        "displacement_cost": round(max(total_displaced_revenue - total_group_revenue, 0), 2),
        "group_rev_proposed": round(total_group_revenue, 2),
        "net_revenue_position": round(net_revenue_position, 2),
        "total_room_nights": int(total_group_room_nights),
        "pace_variance": market_data["pace_otb"] - market_data["pace_stly"],
    }
