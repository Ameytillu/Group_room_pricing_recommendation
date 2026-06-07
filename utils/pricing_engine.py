"""
pricing_engine.py
─────────────────
Core group pricing logic for the Group Pricing Intelligence Tool.

Formula chain:
  1. 3-year historical avg ADR & occupancy (same dates)
  2. YoY ADR trend derived from historical data
  3. Manager's growth % layered on top  →  Projected Transient ADR
  4. Strategy + occupancy + STR signals  →  Rate multipliers
  5. Multipliers × Projected Transient ADR  →  Min / Rec / Stretch rates
  6. Displacement math  →  Revenue impact comparison
"""

from __future__ import annotations
import statistics
from typing import Any

__all__ = [
    "run_pricing_engine",
    "_STRATEGY_MULTIPLIERS",
    "_occupancy_multiplier_adjustment",
    "_pace_adjustment",
    "_str_adjustment",
]


# ── Strategy multiplier table ────────────────────────────────────────────────
# (min, recommended, stretch) as fraction of projected transient ADR
_STRATEGY_MULTIPLIERS = {
    "Balanced (default)":  (0.80, 0.88, 0.95),
    "Protect Occupancy":   (0.75, 0.83, 0.90),
    "Maximize Rate":       (0.85, 0.92, 0.98),
}

# Occupancy thresholds
_OCC_HIGH  = 75.0   # above → High displacement risk
_OCC_MED   = 55.0   # above → moderate; below → low risk


def _yoy_trend(adr_list: list[float]) -> float:
    """
    Compute average YoY ADR growth % from a list of 3 historical ADRs.
    Returns percentage e.g. 3.5 for 3.5%.
    """
    if len(adr_list) < 2:
        return 0.0
    changes = []
    for i in range(1, len(adr_list)):
        if adr_list[i - 1] > 0:
            changes.append((adr_list[i] - adr_list[i - 1]) / adr_list[i - 1] * 100)
    return statistics.mean(changes) if changes else 0.0


def _occupancy_multiplier_adjustment(curr_occ: float) -> float:
    """
    Returns a small additive bump (+0 to +0.04) to rate multipliers
    when occupancy is high, rewarding scarcity pricing.
    """
    if curr_occ >= 85:
        return 0.04
    elif curr_occ >= _OCC_HIGH:
        return 0.02
    elif curr_occ >= _OCC_MED:
        return 0.01
    return 0.0


def _pace_adjustment(pace_otb: int, pace_stly: int) -> float:
    """
    Returns a small additive bump based on pace vs STLY.
    Ahead of pace → slight rate premium; behind → slight softening.
    """
    if pace_stly == 0:
        return 0.0
    variance_pct = (pace_otb - pace_stly) / pace_stly * 100
    if variance_pct >= 10:
        return 0.02
    elif variance_pct >= 5:
        return 0.01
    elif variance_pct <= -10:
        return -0.02
    elif variance_pct <= -5:
        return -0.01
    return 0.0


def _str_adjustment(mpi: float, ari: float) -> float:
    """
    Market signal: if we're outperforming on both MPI & ARI, we can push rates.
    Returns additive adjustment to multipliers.
    """
    adj = 0.0
    if mpi >= 110:
        adj += 0.015
    elif mpi >= 100:
        adj += 0.005
    if ari >= 110:
        adj += 0.015
    elif ari >= 100:
        adj += 0.005
    return adj


def run_pricing_engine(
    sales_data: dict[str, Any],
    market_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Main entry point. Takes sales_data and market_data dicts,
    returns a results dict consumed by app.py.
    """

    # ── Unpack ────────────────────────────────────────────────────────────
    hist_adr        = market_data["hist_adr"]          # list of 3 floats
    hist_occ        = market_data["hist_occ"]          # list of 3 floats
    curr_occ        = market_data["curr_occ"]
    curr_adr        = market_data["curr_adr"]
    total_rooms     = market_data["total_rooms"]
    str_mpi         = market_data["str_mpi"]
    str_ari         = market_data["str_ari"]
    str_comp_occ    = market_data["str_comp_occ"]
    pace_otb        = market_data["pace_otb"]
    pace_stly       = market_data["pace_stly"]
    adr_growth_pct  = market_data["adr_growth_pct"]
    strategy        = market_data["strategy"]

    room_block      = sales_data["room_block"]
    nights          = sales_data["nights"]

    # ── Step 1: Historical averages ───────────────────────────────────────
    avg_hist_occ = statistics.mean(hist_occ)
    avg_hist_adr = statistics.mean(hist_adr)

    # ── Step 2: YoY trend ─────────────────────────────────────────────────
    yoy_trend = _yoy_trend(hist_adr)   # e.g. 3.2

    # ── Step 3: Projected Transient ADR ───────────────────────────────────
    # Apply historical trend first, then manager's growth assumption
    proj_transient_adr = avg_hist_adr * (1 + yoy_trend / 100) * (1 + adr_growth_pct / 100)

    # ── Step 4: Base multipliers from strategy ────────────────────────────
    mult_min_base, mult_rec_base, mult_str_base = _STRATEGY_MULTIPLIERS[strategy]

    # Adjustments
    occ_adj   = _occupancy_multiplier_adjustment(curr_occ)
    pace_adj  = _pace_adjustment(pace_otb, pace_stly)
    str_adj   = _str_adjustment(str_mpi, str_ari)
    total_adj = occ_adj + pace_adj + str_adj

    mult_min    = min(mult_min_base + total_adj, 0.98)
    mult_rec    = min(mult_rec_base + total_adj, 0.99)
    mult_str    = min(mult_str_base + total_adj, 1.00)

    # ── Step 5: Rate suggestions ──────────────────────────────────────────
    rate_min    = round(proj_transient_adr * mult_min,    -1)   # round to $10
    rate_rec    = round(proj_transient_adr * mult_rec,    -1)
    rate_stretch = round(proj_transient_adr * mult_str,   -1)

    # ── Step 6: Displacement & revenue math ──────────────────────────────
    total_room_nights = room_block * nights

    # Rooms available on those dates (simplified: total_rooms × nights)
    available_room_nights = total_rooms * nights

    # Forecasted transient room-nights already on books
    otb_room_nights = round((curr_occ / 100) * total_rooms) * nights

    # How much headroom exists before the hotel fills (threshold = 95% occ)
    fill_threshold  = round(0.95 * total_rooms) * nights
    headroom        = max(fill_threshold - otb_room_nights, 0)

    # Displaced room-nights = block that exceeds headroom
    displaced_room_nights = max(total_room_nights - headroom, 0)

    # Revenue estimates
    displaced_revenue  = displaced_room_nights * proj_transient_adr
    group_rev_min      = total_room_nights * rate_min
    group_rev_rec      = total_room_nights * rate_rec
    group_rev_str      = total_room_nights * rate_stretch
    displacement_cost  = max(displaced_revenue - group_rev_min, 0)

    # Risk label
    if curr_occ >= _OCC_HIGH or displaced_room_nights > 0:
        displacement_risk = "HIGH"
    elif curr_occ >= _OCC_MED:
        displacement_risk = "MEDIUM"
    else:
        displacement_risk = "LOW"

    # Pace variance
    pace_variance = pace_otb - pace_stly

    return {
        # Rates
        "rate_min":            rate_min,
        "rate_rec":            rate_rec,
        "rate_stretch":        rate_stretch,
        # Multipliers (for display in logic expander)
        "mult_min":            mult_min,
        "mult_rec":            mult_rec,
        "mult_str":            mult_str,
        # Anchors
        "proj_transient_adr":  round(proj_transient_adr, 2),
        "avg_hist_occ":        avg_hist_occ,
        "avg_hist_adr":        round(avg_hist_adr, 2),
        "yoy_trend":           round(yoy_trend, 2),
        # Displacement
        "displaced_room_nights": int(displaced_room_nights),
        "displaced_revenue":   round(displaced_revenue, 2),
        "displacement_risk":   displacement_risk,
        "displacement_cost":   round(displacement_cost, 2),
        # Revenue
        "group_rev_min":       round(group_rev_min, 2),
        "group_rev_rec":       round(group_rev_rec, 2),
        "group_rev_str":       round(group_rev_str, 2),
        "total_room_nights":   total_room_nights,
        # Pace
        "pace_variance":       pace_variance,
    }
