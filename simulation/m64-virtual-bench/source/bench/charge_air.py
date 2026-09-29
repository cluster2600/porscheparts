"""Charge-air path: boost target, compressor duty, intercooler (0D).

This module owns the *thermodynamic* charge-air picture that the air-path
volume model consumes:

  - boost setpoint: FACT_PUBLIC brochure plateau 1.0 bar gauge vs the
    retained dyno reading 0.8 bar gauge (the repo public-data survey
    carries both; the model keeps 0.8 bar as the operating plateau and
    reports the 1.0 bar brochure value as an open deviation
    M64-ACQ-BENCH-08).
  - compressor duty: isentropic temperature rise and shaft-power estimate
    per turbo from the PR hypothesis in air_path, with an assumed
    adiabatic efficiency (ASSUMPTION, K16 map not public, M64-ACQ-0003).
  - intercooler: the air_path model already fixes the *net* charge
    temperature; here the gross aftercooler rise and the implied
    intercooler duty/effectiveness are reported so the +20 K plateau
    assumption can be audited rather than buried.

All values are model predictions, HYPOTHESIS/ASSUMPTION tagged.
"""
from __future__ import annotations

from .air_path import manifold_state
from .common import (
    CP_AIR, GAMMA_AIR, P_AMB_PA, T_AMB_K, TURBOS,
)

# --- documented constants --------------------------------------------------
BOOST_PLATEAU_GAUGE_PA = 80000.0     # REPO dyno-envelope plateau (=1.79 abs PR)
BOOST_BROCHURE_GAUGE_PA = 100000.0   # FACT_public brochure setpoint (deviation row)
BOOST_PLATEAU_PR = 1.0 + BOOST_PLATEAU_GAUGE_PA / P_AMB_PA  # documented plateau PR

# Compressor adiabatic efficiency at the plateau duty point (ASSUMPTION:
# typical small-turbo peak ~0.65; no K16 map in repo, M64-ACQ-0003).
ETA_COMP_AD = 0.65                    # ASSUMPTION

# Charge temperature actually delivered to the manifold is owned by
# air_path (T_RISE_K). Gross isentropic rise at the plateau (ASSUMPTION
# path losses neglected): intercooler duty = gross rise - net rise.
NET_CHARGE_RISE_K = 20.0              # REPO envelope (air_path T_RISE_K)


def isentropic_temperature_ratio(pr: float) -> float:
    return pr ** ((GAMMA_AIR - 1.0) / GAMMA_AIR)


def point(rpm: float, thr: float = 1.0, m_dot_air_kg_s: float = 0.0) -> dict:
    """Compressor estimate at given throttle for one engine speed.

    m_dot_air_kg_s is the TOTAL engine charge flow (from the fuel/air
    panel); it is divided by the number of turbos (equal-split
    ASSUMPTION). Duty scales with the throttle-scaled manifold state from
    air_path. At part load (thr<1) the compressor work vanishes with the
    pressure ratio; the intercooler hot side is throttled toward ambient
    the same way so effectiveness stays a bounded audit number
    (ASSUMPTION, M64-ACQ-BENCH-10)."""
    st = manifold_state(rpm, thr)
    pr = st["pr"]
    m_per_turbo = m_dot_air_kg_s / TURBOS
    tau = isentropic_temperature_ratio(pr)
    t2s_k = T_AMB_K * tau
    dt_act_k = (t2s_k - T_AMB_K) / ETA_COMP_AD
    t2_act_k = T_AMB_K + dt_act_k
    w_shaft_w = m_per_turbo * CP_AIR * dt_act_k
    # Throttling lowers compressor discharge temperature toward ambient in
    # the same proportion as the pressure ratio (ASSUMPTION). The hot-side
    # approach is what the intercooler must remove; the cold-side target
    # is the manifold temperature the engine actually sees (owned by
    # air_path).
    t_hot_k = T_AMB_K + thr * max(t2_act_k - T_AMB_K, 0.0)
    t_man_target_k = st["t_man_k"]
    q_ic_w = m_per_turbo * CP_AIR * max(t_hot_k - t_man_target_k, 0.0)
    denom = m_per_turbo * CP_AIR * max(t_hot_k - T_AMB_K, 1e-9)
    eff_ic = (q_ic_w / denom) if denom > 1e-9 else 0.0
    return {
        "rpm": rpm, "thr": thr, "pr": pr,
        "m_dot_per_turbo_kg_s": m_per_turbo,
        "t2s_k": t2s_k, "t2_actual_k": t2_act_k,
        "w_comp_shaft_kw_per_turbo": w_shaft_w / 1e3,
        "w_comp_shaft_total_kw": w_shaft_w * TURBOS / 1e3,
        "q_intercooler_kw_per_turbo": q_ic_w / 1e3,
        "intercooler_effectiveness": eff_ic,
        "boost_gauge_pa_model": P_AMB_PA * (pr - 1.0),
        "boost_gauge_pa_brochure": BOOST_BROCHURE_GAUGE_PA,
        "boost_gap_note": ("model plateau 0.8 bar gauge (REPO dyno envelope) "
                           "vs brochure 1.0 bar (FACT_public): deviation "
                           "M64-ACQ-BENCH-08, kept uncorrected"),
        "provenance": "PR curve HYPOTHESIS; eta_comp ASSUMPTION (M64-ACQ-0003)",
    }
