"""Cooling air path: engine-driven fan, shroud, fin-stack heat rejection (0D).

Covers the air-cooled side only (the charge-air side lives in air_path):

  - fan volumetric flow anchored to FACT_public 1010 l/s at 6100 rpm
    (OBD-1996 supplement via repo public-data survey), scaled with a
    linear affinity HYPOTHESIS;
  - effective fin-flow fraction: only part of the fan flow passes the
    fin stacks; the rest bypasses the shroud. A fixed effective fraction
    (ASSUMPTION) is applied;
  - heat rejection split of chemical power (ASSUMPTION set);
  - fin-stack entropy-generation check: the rejected heat over a finite
    air temperature rise destroys exergy, reported so the split
    assumption can be audited against the 35 K fin-stack anchor.

All values are model predictions, never measurements.
"""
from __future__ import annotations

from .common import (
    CP_AIR, FAN_DRIVE_RATIO, FAN_FLOW_REF_M3_S, FAN_REF_RPM, P_AMB_PA,
    RHO_AMB, T_AMB_K, interp,
)

# --- heat rejection split of chemical power at WOT (ASSUMPTION set) --------
# Typical turbocharged spark-ignition ranges; sums to 1.0 by construction.
SPLIT_COOLING_AIR = 0.30    # fins + fan duct + intercooler face
SPLIT_OIL = 0.10            # oil-cooler circuit (incl. CHRA + bearings)
SPLIT_EXHAUST = 0.55        # enthalpy leaving via turbines/exhaust
SPLIT_RADIATED = 0.05       # external radiation, accessories
SPLIT_SUM = (SPLIT_COOLING_AIR + SPLIT_OIL
             + SPLIT_EXHAUST + SPLIT_RADIATED)

# Only a fraction of fan flow actually crosses the fin stacks (ASSUMPTION:
# typical shrouded air-cooled box 60 % effective; no measured flow split).
FIN_EFFECTIVE_FRACTION = 0.60           # ASSUMPTION

# Fin-stack temperature-rise anchor at the public peak-power point
# (ASSUMPTION: plausible air-cooled fin-stack rise; no measured fin data).
DT_AIR_ANCHOR_K = 35.0
DT_AIR_RPM_GRID = [1000.0, 4050.0, 5750.0, 6800.0]
DT_AIR_K = [22.0, 32.0, 35.0, 36.0]     # HYPOTHESIS shape through the anchor


def fan_flow(rpm: float) -> dict:
    """Fan volumetric/mass flow, scaled from FACT_public 1.010 m3/s @ 6100 rpm.

    Scaling law: flow proportional to shaft speed (standard fan affinity for
    a fixed duct duty point). HYPOTHESIS — repo OpenFOAM decks fix mass flow
    per case, so no measured slope exists (M64-ACQ-BENCH-06)."""
    q = FAN_FLOW_REF_M3_S * (rpm / FAN_REF_RPM)
    return {
        "rpm": rpm,
        "fan_flow_m3_s": q,
        "fan_flow_l_s": q * 1e3,
        "fan_mass_flow_kg_s": q * RHO_AMB,
        "fan_shaft_rpm": rpm * FAN_DRIVE_RATIO,
        "effective_fin_flow_kg_s": q * RHO_AMB * FIN_EFFECTIVE_FRACTION,
        "basis": ("linear affinity scaling of FACT_public 1.010 m3/s @ 6100 "
                  "rpm; effective fraction ASSUMPTION (M64-ACQ-BENCH-06)"),
    }


def dt_air(rpm: float) -> float:
    """Fin-stack air temperature rise (K) — HYPOTHESIS shape through the
    documented 35 K anchor at the 5750 rpm peak-power point."""
    return interp(rpm, DT_AIR_RPM_GRID, DT_AIR_K)


def point(p_chem_kw: float, rpm: float) -> dict:
    """Cooling-air panel at one engine speed."""
    fan = fan_flow(rpm)
    q_air_kw = p_chem_kw * SPLIT_COOLING_AIR
    q_oil_kw = p_chem_kw * SPLIT_OIL
    m_eff = fan["effective_fin_flow_kg_s"]
    # temperature rise implied by the ACTUAL effective flow (audits the split):
    dt_implied_k = (q_air_kw * 1e3 / (m_eff * CP_AIR)) if m_eff > 0 else float("inf")
    dT = dt_air(rpm)
    # entropy generation of the finite-DT heat rejection (W/K), ambient ref:
    t_hot = T_AMB_K + dT
    s_gen_w_k = q_air_kw * 1e3 * (1.0 / T_AMB_K - 1.0 / t_hot)
    exrg_dest_kw = T_AMB_K * s_gen_w_k / 1e3
    return {
        "rpm": rpm,
        **fan,
        "q_cooling_air_kw": q_air_kw,
        "q_oil_kw": q_oil_kw,
        "q_exhaust_kw": p_chem_kw * SPLIT_EXHAUST,
        "cooling_air_dt_k": dT,
        "cooling_air_dt_implied_k": dt_implied_k,
        "cooling_air_exergy_destroyed_kw": exrg_dest_kw,
        "anchor_consistency_flag": (
            "implied rise vs 35 K anchor: "
            + ("consistent within 20 %"
               if abs(dt_implied_k - DT_AIR_ANCHOR_K) / DT_AIR_ANCHOR_K <= 0.20
               else "MISMATCH — fan flow and assumed split disagree")),
        "provenance": ("fan anchor FACT_public; scaling + effective fraction "
                       "+ split ASSUMPTION/HYPOTHESIS (M64-ACQ-BENCH-04/-06)"),
    }
