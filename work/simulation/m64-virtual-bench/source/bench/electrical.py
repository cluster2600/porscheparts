"""Electrical parasitic loads on the rpm grid (0D).

Three consumers are modelled: starter (cranking only), ignition, and
fuel injection + management. The repo has NO electrical specification for
the M64/60 wiring loads -> every constant here is an ASSUMPTION flagged in
inputs-gap.md (M64-ACQ-BENCH-07). Values are typical 12 V automotive
orders of magnitude, not measured.

Power convention: all values are electrical power drawn from the 12 V
system (W). The dyno treats them as a parasitic load alongside driveline
losses; the brake power reported by the fuel path is unaffected (the
public brochure figure is a crank/power-puller figure).
"""
from __future__ import annotations

from .common import interp

# --- starter (ASSUMPTION) --------------------------------------------------
# 993 starter: rating not in repo. ASSUMPTION: 1.4 kW mechanical output,
# ~1.0 s cranking, electrical input ~4.5 kW at ~300 rpm cranking speed.
STARTER_INPUT_W = 4500.0
CRANK_RPM_MAX = 500.0            # below this, starter is considered engaged

# --- ignition (ASSUMPTION) -------------------------------------------------
# 6-coil static + speed-proportional component (dwell losses scale with
# spark events). ASSUMPTION: 60 W at idle-equivalent 1000 rpm,
# 130 W at limiter 6800 rpm. Linear in rpm.
IGNITION_W_GRID_RPM = [1000.0, 6800.0]
IGNITION_W_GRID = [60.0, 130.0]

# --- injection + engine management (ASSUMPTION) -----------------------------
# Electric fuel pump work scales with fuel mass flow at a 3.8 bar rail
# (ASSUMPTION, no fuel card in repo) and 60% pump efficiency; injectors +
# DME take a roughly constant 90 W.
FUEL_RAIL_DP_PA = 3.8e5          # ASSUMPTION
FUEL_PUMP_EFF = 0.60             # ASSUMPTION
FUEL_RHO_KG_M3 = 740.0           # ASSUMPTION (pump petrol density)
INJECTOR_DME_W = 90.0            # ASSUMPTION


def ignition_w(rpm: float) -> float:
    return interp(rpm, IGNITION_W_GRID_RPM, IGNITION_W_GRID)


def injection_w(m_dot_fuel_kg_s: float) -> float:
    pump = m_dot_fuel_kg_s / FUEL_RHO_KG_M3 * FUEL_RAIL_DP_PA / FUEL_PUMP_EFF
    return pump + INJECTOR_DME_W


def starter_w(rpm: float) -> float:
    return STARTER_INPUT_W if rpm <= CRANK_RPM_MAX else 0.0


def point(rpm: float, m_dot_fuel_kg_s: float) -> dict:
    """Parasitic electrical load for one engine speed."""
    w_ign = ignition_w(rpm)
    w_inj = injection_w(m_dot_fuel_kg_s)
    w_str = starter_w(rpm)
    total = w_ign + w_inj + w_str
    return {
        "rpm": rpm,
        "ignition_w": w_ign,
        "injection_w": w_inj,
        "starter_w": w_str,
        "total_electrical_w": total,
        "equivalent_12v_current_a": total / 12.0,
        "provenance": "all constants ASSUMPTION (M64-ACQ-BENCH-07)",
    }
