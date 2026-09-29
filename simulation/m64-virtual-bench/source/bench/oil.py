"""Oil circuit: flow demand vs assumed pump capability (0D, air-cooled).

cooling_air.py owns the *heat* side of the oil loop (oil share of
chemical power). This module owns the *hydraulic* side: required supply
flow, the journal-bearing film-flow floor, and an assumed pump capability
used only to flag headroom — the repo carries oil CAPACITY (12 L,
FACT_public) and a synthetic return-line point (2 L/min, 120 degC) but NO
pump curve or pressure map (M64-ACQ-BENCH-02), so every capability number
here is an ASSUMPTION.

Consumption (make-up) is reported as a documented rate band, not a
prediction: no oil-consumption card exists in the repo.
"""
from __future__ import annotations

from .common import OIL_CAPACITY_L, OIL_CP, OIL_RHO, interp

# Cooler delta-T target (ASSUMPTION). Must match cooling_air.OIL_DT_TARGET_K;
# duplicated locally to keep module imports one-directional (no cycles).
OIL_DT_TARGET_K = 25.0

# --- assumed pump capability (ASSUMPTION set, M64-ACQ-BENCH-02) ------------
# Typical air-cooled turbo dry-sump pressure-fed flat-six: useful flow
# assumed linear from 60 L/min at idle to 250 L/min at redline.
# NOT a measured curve.
PUMP_FLOW_RPM = [800.0, 6800.0]
PUMP_FLOW_L_MIN = [60.0, 250.0]
OIL_SUPPLY_PRESSURE_BAR = 2.0         # hot target, ASSUMPTION
PUMP_EFF = 0.45                       # ASSUMPTION (gear-pump order of magnitude)

# Journal-bearing minimum film flow per main/big-end (ASSUMPTION):
# 1.2 L/min per bearing, 6 mains + 6 rods = 12 bearings.
FILM_FLOW_PER_BEARING_L_MIN = 1.2
N_BEARINGS = 12

# Oil make-up band (ASSUMPTION band, air-cooled turbo dry sump),
# percent of the 12 L sump capacity per 1000 km.
OIL_MAKEUP_PCT_PER_1000KM = (0.3, 0.6)


def pump_flow_available_l_min(rpm: float) -> float:
    return interp(rpm, PUMP_FLOW_RPM, PUMP_FLOW_L_MIN)


def point(rpm: float, q_oil_kw: float) -> dict:
    """Hydraulic panel for one engine speed.

    q_oil_kw: oil-circuit heat load (kW) from cooling_air.py. Required
    flow is the max of the thermal duty flow and the bearing film floor
    (film floor dominates at low load, thermal duty at high load).
    """
    q_flow_kg_s = q_oil_kw * 1e3 / (OIL_CP * OIL_DT_TARGET_K)
    q_flow_l_min = q_flow_kg_s / OIL_RHO * 1e3
    film_floor_l_min = FILM_FLOW_PER_BEARING_L_MIN * N_BEARINGS
    required_l_min = max(q_flow_l_min, film_floor_l_min)
    available_l_min = pump_flow_available_l_min(rpm)
    headroom_l_min = available_l_min - required_l_min
    pump_shaft_w = ((required_l_min / 60000.0) * OIL_SUPPLY_PRESSURE_BAR
                    * 1e5 / PUMP_EFF)
    return {
        "rpm": rpm,
        "oil_flow_thermal_l_min": q_flow_l_min,
        "oil_flow_film_floor_l_min": film_floor_l_min,
        "oil_flow_required_l_min": required_l_min,
        "oil_flow_available_assumed_l_min": available_l_min,
        "oil_flow_headroom_l_min": headroom_l_min,
        "oil_pump_shaft_w_assumed": pump_shaft_w,
        "oil_makeup_band_pct_per_1000km": list(OIL_MAKEUP_PCT_PER_1000KM),
        "sump_capacity_l": OIL_CAPACITY_L,
        "provenance": ("all capability constants ASSUMPTION "
                       "(M64-ACQ-BENCH-02); heat load from cooling_air split "
                       "ASSUMPTION (M64-ACQ-BENCH-04)"),
    }
