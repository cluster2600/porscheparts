"""Oil + cooling-air thermal loop (lumped, 0D, air-cooled).

Heat rejection: chemical power in minus brake power out splits into
cooling air (cylinder fins + fan duct), oil circuit, exhaust enthalpy
and radiated/store. Fixed split fractions are ASSUMPTIONS (documented
below); the cooling-air side is closed against the fan airflow model
(FACT_public anchor 1010 l/s @ 6100 rpm, linear affinity HYPOTHESIS).

Per-bank lumped model: 3 cylinders/bank, equal split. Steady-state bank
metal temperature rise is solved from Q_bank = hA_eff * dT with a single
lumped hA_eff per bank, itself anchored so that the cooling-air temperature
rise at the public peak-power point equals a documented 35 K (ASSUMPTION:
plausible air-cooled fin-stack rise; no measured fin data in repo).

Oil: flow demand vs pump data. The repo publishes oil CAPACITY (12 L) and
a synthetic return-line point (2 L/min, 120 degC) but NO pump flow curve
or pressure -> flagged in inputs-gap.md (M64-ACQ-BENCH-02).
"""
from __future__ import annotations

from .common import (
    OIL_CP, OIL_RHO, P_AMB_PA, RHO_AMB,
)
from .air_path import fan_airflow

# Heat rejection split of chemical power at WOT (ASSUMPTION set; typical
# turbocharged spark range; sums to 1.0):
SPLIT_COOLING_AIR = 0.30    # fins + fan duct + intercooler face
SPLIT_OIL = 0.10            # oil-cooler circuit (incl. CHRA + bearings)
SPLIT_EXHAUST = 0.55        # enthalpy leaving via turbines/exhaust
SPLIT_RADIATED = 0.05       # external radiation, accessories
SPLIT_SUM = SPLIT_COOLING_AIR + SPLIT_OIL + SPLIT_EXHAUST + SPLIT_RADIATED

# Cooling-air temperature rise anchor at the public peak-power point (ASSUMPTION).
DT_AIR_ANCHOR_K = 35.0
ANCHOR_RPM = 5750.0

# Oil circuit design intent (ASSUMPTION: typical air-cooled turbo dry-sump
# supply target 1.5-2 bar hot idle, 10-15 L/s peak; no pump curve in repo).
OIL_SUPPLY_TARGET_LPS = 0.25          # ASSUMPTION
OIL_DT_TARGET_K = 25.0                # oil-cooler delta-T target (ASSUMPTION)


def bank_model(power_kw: float, p_chem_kw: float, rpm: float) -> dict:
    fan = fan_airflow(rpm)
    q_air_w = p_chem_kw * 1e3 * SPLIT_COOLING_AIR
    q_oil_w = p_chem_kw * 1e3 * SPLIT_OIL
    m_air = fan["fan_mass_flow_kg_s"]
    # cooling air temperature rise implied by the actual flow:
    cp_air = 1005.0
    dt_air = q_air_w / (m_air * cp_air) if m_air > 0 else float("inf")
    # lumped hA anchored so bank rise = DT_AIR_ANCHOR_K at ANCHOR_RPM
    fan_anchor = fan_airflow(ANCHOR_RPM)
    q_anchor = _p_chem_at_anchor() * 1e3 * SPLIT_COOLING_AIR
    hA = q_anchor / DT_AIR_ANCHOR_K
    # Each bank holds half of q_air and half of hA -> both banks show the same
    # rise; steady rise scales linearly with heat load around the anchor.
    dt_bank = DT_AIR_ANCHOR_K * q_air_w / q_anchor
    oil_flow_required_kg_s = q_oil_w / (OIL_CP * OIL_DT_TARGET_K)
    return {
        "rpm": rpm,
        "q_cooling_air_kw": q_air_w / 1e3,
        "q_oil_kw": q_oil_w / 1e3,
        "q_exhaust_kw": p_chem_kw * SPLIT_EXHAUST,
        "fan_mass_flow_kg_s": m_air,
        "cooling_air_dt_k": dt_air,
        "bank_metal_rise_k": dt_bank * 1.0,
        "per_bank": {
            "q_bank_air_kw": q_air_w / 2e3,
            "dt_bank_k": dt_bank,
        },
        "oil_flow_required_kg_s": oil_flow_required_kg_s,
        "oil_flow_required_l_min": oil_flow_required_kg_s / OIL_RHO * 1e3,
        "fan_basis": fan["basis"],
    }


_ANCHOR_CACHE: dict = {}


def _p_chem_at_anchor() -> float:
    if "p" not in _ANCHOR_CACHE:
        from .fuel import point
        _ANCHOR_CACHE["p"] = point(ANCHOR_RPM)["p_chem_kw"]
    return _ANCHOR_CACHE["p"]
