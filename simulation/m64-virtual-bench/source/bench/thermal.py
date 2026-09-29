"""Oil + cooling-air thermal loop (lumped, 0D, air-cooled) — compatibility shim.

The physics moved to dedicated modules:

  - bench/cooling_air.py: fan flow (FACT_public anchor 1010 l/s @ 6100 rpm,
    linear affinity HYPOTHESIS), heat-rejection split (ASSUMPTION set),
    fin-stack rise and entropy-generation audit,
  - bench/oil.py: hydraulic side (flow demand vs assumed pump capability,
    bearing film floor, assumed pump drive power, M64-ACQ-BENCH-02),
  - bench/charge_air.py: compressor duty and intercooler audit.

This shim keeps the historical interface (bank_model, SPLIT_*,
DT_AIR_ANCHOR_K, ANCHOR_RPM) working so the wave-2 tests and any external
callers keep running while run_bench.py migrates to the new modules.
"""
from __future__ import annotations

from . import cooling_air
from .air_path import fan_airflow
from .cooling_air import (  # noqa: F401  (re-exported for compatibility)
    DT_AIR_ANCHOR_K, SPLIT_COOLING_AIR, SPLIT_EXHAUST, SPLIT_OIL,
    SPLIT_RADIATED, SPLIT_SUM,
)

ANCHOR_RPM = 5750.0   # public peak-power point (ASSUMPTION rpm position)

# Kept for callers that import them (documented in oil.py as ASSUMPTIONs).
OIL_SUPPLY_TARGET_LPS = 0.25          # ASSUMPTION
OIL_DT_TARGET_K = 25.0                # ASSUMPTION


def bank_model(power_kw: float, p_chem_kw: float, rpm: float) -> dict:
    """Historical interface: cooling_air panel + lumped per-bank rise.

    Bank metal rise is modelled as the cooling-air rise itself (single
    lumped resistance; linear scaling around the 35 K anchor is inherited
    from the cooling_air DT shape)."""
    ca = cooling_air.point(p_chem_kw, rpm)
    dt_bank = ca["cooling_air_dt_k"]
    return {
        "rpm": rpm,
        "q_cooling_air_kw": ca["q_cooling_air_kw"],
        "q_oil_kw": ca["q_oil_kw"],
        "q_exhaust_kw": ca["q_exhaust_kw"],
        "fan_mass_flow_kg_s": ca["fan_mass_flow_kg_s"],
        "cooling_air_dt_k": ca["cooling_air_dt_implied_k"],
        "bank_metal_rise_k": dt_bank,
        "per_bank": {
            "q_bank_air_kw": ca["q_cooling_air_kw"] / 2.0,
            "dt_bank_k": dt_bank,
        },
        "oil_flow_required_kg_s": ca["q_oil_kw"] * 1e3 / (2100.0 * OIL_DT_TARGET_K),
        "oil_flow_required_l_min": (ca["q_oil_kw"] * 1e3
                                    / (2100.0 * OIL_DT_TARGET_K) / 850.0 * 1e3),
        "fan_basis": ca["basis"],
        "anchor_consistency_flag": ca["anchor_consistency_flag"],
    }
