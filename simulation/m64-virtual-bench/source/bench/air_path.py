"""Air path: K16 twin-turbo charge model + volumetric efficiency (0D).

Boost build-up is modelled with a documented compressor-map HYPOTHESIS:
the K16 compressor pressure ratio is ramped from 1.0 at the wastegate
cracking engine speed to the published 0.8 bar gauge plateau, with the
public K16 compressor envelope (inducer 40.6 mm / exducer 60.5 mm,
SINGLE_SOURCE) used only to sanity-check reduced mass flow against the
REPO variants anchor (0.156 kg/s per turbo at mid-range).

Everything here is a HYPOTHESIS map hypothesis — the real K16 map is not
public (blocking acquisition M64-ACQ-0003).
"""
from __future__ import annotations

import math

from .common import (
    P_AMB_PA, R_AIR, RHO_AMB, T_AMB_K,
    TURBOS, VARIANTS_FLOW_ANCHOR_KG_S, interp,
)

# Intercooler + duct temperature rise at the published 0.8 bar plateau:
# REPO dyno-envelope T_man = 323.15 K over 303.15 K ambient => +20 K.
T_RISE_K = 20.0

# --- documented map hypothesis -------------------------------------------
# Compressor PR vs engine speed (HYPOTHESIS, shaped to reach the published
# 0.8 bar plateau at mid range; shape is a hypothesis, the plateau value is
# FACT_public from the repo public-data survey).
PR_RPM = [1000.0, 2000.0, 2800.0, 3600.0, 4050.0, 5750.0, 6800.0]
PR_VALS = [1.00, 1.15, 1.35, 1.55, 1.65, 1.79, 1.79]   # 1.79 = 181.3 kPa abs / 101.325
PR_LIMITER_LABEL = "PR=1.0 below spool; plateau = published 0.8 bar gauge"

# (Intercooler + duct total temperature rise is the documented constant
#  T_RISE_K defined above; it scales with PR-1 below the plateau.)

# Volumetric efficiency (REPO envelope 0.85..1.0 from dyno-reference.json).
# HYPOTHESIS shape: VE rises to ~1.0 near the torque plateau and decays.
VE_RPM = [1000.0, 2000.0, 3000.0, 4050.0, 5000.0, 6000.0, 6800.0]
VE_VALS = [0.78, 0.88, 0.95, 1.00, 0.99, 0.94, 0.88]
VE_BAND = (0.85, 1.0)  # only the plateau region stays inside REPO envelope


def pressure_ratio(rpm: float) -> float:
    return interp(rpm, PR_RPM, PR_VALS)


def manifold_state(rpm: float) -> dict:
    """Manifold abs pressure / temperature / density at WOT for given engine rpm.

    Temperature model (documented constant, REPO envelope): at the published
    0.8 bar plateau the manifold temperature is the REPO dyno-envelope value
    323.15 K (30 degC post-intercooler/duct rise of +20 K over ambient);
    below the plateau the rise scales linearly with (PR - 1). HYPOTHESIS for
    the below-plateau shape; the plateau point is REPO-sourced.
    """
    pr = pressure_ratio(rpm)
    p_man = P_AMB_PA * pr
    dt = T_RISE_K * (pr - 1.0) / max(PR_VALS[-1] - 1.0, 1e-9)
    t_man = T_AMB_K + dt
    rho_man = p_man / (R_AIR * t_man)
    return {"rpm": rpm, "pr": pr, "p_man_pa": p_man, "t_man_k": t_man,
            "rho_man_kg_m3": rho_man}


def ve(rpm: float) -> float:
    return interp(rpm, VE_RPM, VE_VALS)


def air_flow(rpm: float, displacement_m3: float) -> dict:
    """Charge mass flow (kg/s) through the engine at WOT."""
    st = manifold_state(rpm)
    # 4-stroke: one intake event per two revolutions -> displacement * rpm/2
    m_dot = ve(rpm) * st["rho_man_kg_m3"] * displacement_m3 * (rpm / 60.0) / 2.0
    per_turbo = m_dot / TURBOS
    return {"rpm": rpm, **st, "ve": ve(rpm),
            "m_dot_air_kg_s": m_dot,
            "m_dot_air_per_turbo_kg_s": per_turbo,
            "flow_anchor_check": per_turbo / VARIANTS_FLOW_ANCHOR_KG_S}


def fan_airflow(rpm: float) -> dict:
    """Cooling fan airflow scaling from the FACT_public anchor 1010 l/s @ 6100 rpm
    (OBD-1996 supplement, via repo public-data survey). Scaling law: fan flow is
    proportional to shaft speed (HYPOTHESIS, standard fan-law affinity for a
    fixed-duty-point duct; the repo OpenFOAM decks fix mass flow per case, so
    no measured slope exists — flagged)."""
    q = FAN_FLOW_REF_M3_S * (rpm / FAN_REF_RPM)
    return {
        "rpm": rpm,
        "fan_flow_m3_s": q,
        "fan_mass_flow_kg_s": q * RHO_AMB,
        "fan_shaft_rpm": rpm * FAN_DRIVE_RATIO,
        "basis": "linear affinity scaling of FACT_public 1.010 m3/s @ 6100 rpm",
    }
