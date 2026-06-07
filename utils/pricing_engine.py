"""
pricing_engine.py
─────────────────
Core group pricing logic for the Group Pricing Intelligence Tool.

All rate rounding uses ceiling rounding to the nearest $10, so suggested rates
do not round down below the calculated revenue-management rate.
"""

from __future__ import annotations

import math
from typing import Any

__all__ = [
    "run_pricing_engine",
    "_STRATEGY_MULTIPLIERS",
    "_occupancy_multiplier_adjustment",
    "_pace_adjustment",
    "_str_adjustment",
]


# Each tuple: (minimum, recommended, stretch) as a fraction of projected
# transient ADR.
_STRATEGY_MULTIPLIERS = {
    "Balanced (default)": (0.80, 0.88, 0.95),
    "Protect Occupancy": (0.75, 0.83, 0.90),
    "Maximize Rate": (0.85, 0.92, 0.98),
}


def _occupancy_multiplier_adjustment(curr_occ: float) -> float:
    """
    Adjust multipliers based on current forecasted occupancy.

    < 55%  -> -0.020
    55-64% -> -0.010
    65-74% -> +0.010
    75-84% -> +0.020
    >= 85% -> +0.030
    """
    if curr_occ < 55:
        return -0.020
    if curr_occ < 65:
        return -0.010
    if curr_occ < 75:
        return 0.010
    if curr_occ < 85:
        return 0.020
    return 0.030


def _pace_adjustment(pace_otb: int, pace_stly: int) -> float:
    """
    Adjust based on pace versus same time last year.

    < -20 rooms -> -0.015
    -20 to -6   -> -0.010
    -5 to +5    ->  0.000
    +6 to +20   -> +0.010
    > +20       -> +0.015
    """
    delta = pace_otb - pace_stly
    if delta < -20:
        return -0.015
    if delta < -5:
        return -0.010
    if delta <= 5:
        return 0.000
    if delta <= 20:
        return 0.010
    return 0.015


def _str_adjustment(mpi: float, ari: float) -> float:
    """
    Adjust based on STR competitive index signals.

    Both above 100                 -> +0.010
    MPI above, ARI below 100       -> +0.005
    MPI below, ARI above 100       -> -0.005
    Both below 100                 -> -0.010
    """
    if mpi >= 100 and ari >= 100:
        return 0.010
    if mpi >= 100 and ari < 100:
        return 0.005
    if mpi < 100 and ari >= 100:
        return -0.005
    return -0.010


def _round_up_10(value: float) -> int:
    """Round up to the nearest $10."""
    return math.ceil(value / 10) * 10


def _displacement_risk_label(displaced_rn: int, group_rn: int) -> str:
    """
    Single source of truth for displacement risk.

    0 displaced room-nights        -> LOW
    1-49% of group block displaced -> MEDIUM
    50%+ of group block displaced  -> HIGH
    """
    if displaced_rn == 0:
        return "LOW"
    if displaced_rn < group_rn * 0.50:
        return "MEDIUM"
    return "HIGH"


def run_pricing_engine(
    sales_data: dict[str, Any],
    market_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Compute pricing outputs from sales request and market data.
    """
    nights = sales_data["nights"]
    room_block = sales_data["room_block"]

    hist_adr = market_data["hist_adr"]
    hist_occ = market_data["hist_occ"]
    curr_occ = market_data["curr_occ"]
    total_rooms = market_data["total_rooms"]
    str_mpi = market_data["str_mpi"]
    str_ari = market_data["str_ari"]
    pace_otb = market_data["pace_otb"]
    pace_stly = market_data["pace_stly"]
    adr_growth_pct = market_data["adr_growth_pct"]
    strategy = market_data["strategy"]

    avg_hist_adr = sum(hist_adr) / len(hist_adr) if hist_adr else 0.0
    avg_hist_occ = sum(hist_occ) / len(hist_occ) if hist_occ else 0.0

    changes = []
    for idx in range(1, len(hist_adr)):
        prior = hist_adr[idx - 1]
        if prior:
            changes.append((hist_adr[idx] - prior) / prior * 100)
    yoy_trend = sum(changes) / len(changes) if changes else 0.0

    after_hist_trend = avg_hist_adr * (1 + yoy_trend / 100)
    proj_transient_adr = after_hist_trend * (1 + adr_growth_pct / 100)

    base_min, base_rec, base_str = _STRATEGY_MULTIPLIERS[strategy]
    occ_adj = _occupancy_multiplier_adjustment(curr_occ)
    pace_adj = _pace_adjustment(pace_otb, pace_stly)
    str_adj = _str_adjustment(str_mpi, str_ari)
    total_adj = occ_adj + pace_adj + str_adj

    mult_min = max(0.60, min(1.00, base_min + total_adj))
    mult_rec = max(0.60, min(1.00, base_rec + total_adj))
    mult_str = max(0.60, min(1.00, base_str + total_adj))

    rate_min = _round_up_10(proj_transient_adr * mult_min)
    rate_rec = _round_up_10(proj_transient_adr * mult_rec)
    rate_stretch = _round_up_10(proj_transient_adr * mult_str)

    group_rn = room_block * nights
    fill_threshold_rooms = round(0.95 * total_rooms)
    fill_threshold_rn = fill_threshold_rooms * nights
    otb_rooms = round((curr_occ / 100) * total_rooms)
    otb_rn = otb_rooms * nights
    headroom_rn = max(fill_threshold_rn - otb_rn, 0)
    displaced_rn = max(group_rn - headroom_rn, 0)

    displaced_revenue = displaced_rn * proj_transient_adr
    displacement_risk = _displacement_risk_label(displaced_rn, group_rn)

    group_rev_min = group_rn * rate_min
    group_rev_rec = group_rn * rate_rec
    group_rev_str = group_rn * rate_stretch
    displacement_cost = max(displaced_revenue - group_rev_min, 0)

    return {
        "rate_min": rate_min,
        "rate_rec": rate_rec,
        "rate_stretch": rate_stretch,
        "mult_min": mult_min,
        "mult_rec": mult_rec,
        "mult_str": mult_str,
        "proj_transient_adr": round(proj_transient_adr, 2),
        "avg_hist_occ": avg_hist_occ,
        "avg_hist_adr": round(avg_hist_adr, 2),
        "yoy_trend": round(yoy_trend, 2),
        "displaced_room_nights": int(displaced_rn),
        "displaced_revenue": round(displaced_revenue, 2),
        "displacement_risk": displacement_risk,
        "displacement_cost": round(displacement_cost, 2),
        "group_rev_min": round(group_rev_min, 2),
        "group_rev_rec": round(group_rev_rec, 2),
        "group_rev_str": round(group_rev_str, 2),
        "total_room_nights": group_rn,
        "pace_variance": pace_otb - pace_stly,
    }
