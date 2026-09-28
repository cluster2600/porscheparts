"""Fuel path: combustion energy balance + BSFC grid (0D).

Fuel power comes from the air-path charge flow at an assumed WOT air-fuel
ratio. Brake efficiency is taken from a documented BSFC-shape grid
(HYPOTHESIS, typical turbocharged spark-ignition shape) scaled by ONE
global calibration constant anchored to the public 408 PS / 540 Nm case
(peak-power point only; the torque anchor is left as a blind prediction).
"""
from __future__ import annotations

from .common import (
    AFR_STOICH, DISPLACEMENT_M3, LHV_FUEL_J_KG, PUBLIC_CASE, interp,
)
from .air_path import air_flow

# WOT air-fuel ratio (ASSUMPTION: rich-of-stoich charge-cooling/boost margin;
# no repo fuel-calibration card exists).
AFR_WOT = 12.0

# BSFC shape grid at WOT, g/kWh (HYPOTHESIS: generic turbocharged SI shape;
# minimum near the torque plateau, rising at low rpm and to the limiter).
BSFC_RPM = [1000.0, 2000.0, 3000.0, 4050.0, 4750.0, 5750.0, 6400.0, 6800.0]
BSFC_SHAPE = [340.0, 290.0, 262.0, 250.0, 252.0, 285.0, 302.0, 318.0]

# One global calibration factor, solved from the public peak-power anchor.
def _bsfc_shape_to_eff(bsfc_g_kwh: float) -> float:
    """Brake thermal efficiency from BSFC (g/kWh) and fuel LHV (J/kg)."""
    return 3.6e9 / (bsfc_g_kwh * LHV_FUEL_J_KG)


def _calibration() -> tuple[float, float]:
    """Solve global efficiency multiplier on the 300 kW @ 5750 rpm anchor."""
    a = air_flow(PUBLIC_CASE["peak_power_rpm"], DISPLACEMENT_M3)
    p_chem = a["m_dot_air_kg_s"] / AFR_WOT * LHV_FUEL_J_KG
    eta_shape = _bsfc_shape_to_eff(interp(PUBLIC_CASE["peak_power_rpm"],
                                          BSFC_RPM, BSFC_SHAPE))
    calib = PUBLIC_CASE["peak_power_kw"] * 1e3 / (p_chem * eta_shape)
    return calib, p_chem


CALIB, P_CHEM_ANCHOR = _calibration()


def point(rpm: float) -> dict:
    """Brake power/torque/fuel at WOT for one engine speed."""
    a = air_flow(rpm, DISPLACEMENT_M3)
    m_fuel = a["m_dot_air_kg_s"] / AFR_WOT
    p_chem = m_fuel * LHV_FUEL_J_KG
    eta_b = CALIB * _bsfc_shape_to_eff(interp(rpm, BSFC_RPM, BSFC_SHAPE))
    p_kw = p_chem * eta_b / 1e3
    omega = 2.0 * 3.141592653589793 * rpm / 60.0
    torque = p_kw * 1e3 / omega
    bsfc = 3.6e9 / (eta_b * LHV_FUEL_J_KG)
    bmep_bar = torque * 4.0 * 2.0 * 3.141592653589793 / (2.0 * DISPLACEMENT_M3) / 1e5
    return {**a, "afr": AFR_WOT, "m_dot_fuel_kg_s": m_fuel,
            "p_chem_kw": p_chem / 1e3, "eta_brake": eta_b,
            "power_kw": p_kw, "torque_nm": torque, "bsfc_g_kwh": bsfc,
            "bmep_bar": bmep_bar}
