"""Fuel path: combustion energy balance + BSFC grid (0D).

Fuel power comes from the air-path charge flow at an assumed WOT air-fuel
ratio. Brake efficiency is taken from a documented BSFC-shape grid
(HYPOTHESIS, typical turbocharged spark-ignition shape) multiplied by a
two-parameter calibration:

    eta_b(rpm) = (C0 + C1 * (4050 / rpm)) * eta_shape(rpm)

C0/C1 are solved on the two public FACT_public anchors
(300 kW @ 5750 rpm and 540 Nm @ 4050 rpm). The 1/rpm tilt is a HYPOTHESIS
reflecting the normal BSFC optimum near the torque plateau; with a single
global scalar (one anchor) the blind torque prediction overshot the public
540 Nm anchor by ~20%, which the two-anchor solve removes. Nothing else in
the curve between/beyond the anchors is calibrated: intermediate rows and
the peak-location remain predictions, and no torque-plateau SHAPE is
claimed (no measured BSFC map in repo -> M64-ACQ-BENCH-05).
"""
from __future__ import annotations

import math

import numpy as np

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


def _bsfc_shape_to_eff(bsfc_g_kwh: float) -> float:
    """Brake thermal efficiency from BSFC (g/kWh) and fuel LHV (J/kg)."""
    return 3.6e9 / (bsfc_g_kwh * LHV_FUEL_J_KG)


def _tilt(rpm: float) -> float:
    """Efficiency-tilt basis, 1.0 at the torque-plateau anchor rpm."""
    return PUBLIC_CASE["peak_torque_rpm"] / rpm


def _calibration() -> tuple[float, float, dict]:
    """Solve (C0, C1) on the two public anchors. Linear 2x2, deterministic."""
    rpm_p = PUBLIC_CASE["peak_power_rpm"]
    rpm_t = PUBLIC_CASE["peak_torque_rpm"]

    a_p = air_flow(rpm_p, DISPLACEMENT_M3)
    p_chem_p = a_p["m_dot_air_kg_s"] / AFR_WOT * LHV_FUEL_J_KG
    e_p = PUBLIC_CASE["peak_power_kw"] * 1e3 / p_chem_p           # required eta

    a_t = air_flow(rpm_t, DISPLACEMENT_M3)
    p_chem_t = a_t["m_dot_air_kg_s"] / AFR_WOT * LHV_FUEL_J_KG
    omega_t = 2.0 * math.pi * rpm_t / 60.0
    e_t = PUBLIC_CASE["peak_torque_nm"] * omega_t / p_chem_t       # required eta

    s_p = _bsfc_shape_to_eff(interp(rpm_p, BSFC_RPM, BSFC_SHAPE))
    s_t = _bsfc_shape_to_eff(interp(rpm_t, BSFC_RPM, BSFC_SHAPE))
    # Rows: C0*s_i + C1*(rpm_t/rpm_i)*s_i = e_i  (shape eta differs per row)
    A = np.array([[s_p, _tilt(rpm_p) * s_p],
                  [s_t, _tilt(rpm_t) * s_t]])
    rhs = np.array([e_p, e_t])
    c0, c1 = np.linalg.solve(A, rhs)
    diag = {
        "c0": float(c0), "c1": float(c1),
        "required_eta_at_power_anchor": float(e_p),
        "required_eta_at_torque_anchor": float(e_t),
        "shape_eta_at_power_anchor": float(s_p),
        "shape_eta_at_torque_anchor": float(s_t),
        "p_chem_at_power_anchor_kw": float(p_chem_p / 1e3),
        "p_chem_at_torque_anchor_kw": float(p_chem_t / 1e3),
    }
    return float(c0), float(c1), diag


C0, C1, CAL_DIAG = _calibration()


def eff_calib(rpm: float) -> float:
    return (C0 + C1 * _tilt(rpm))


def point(rpm: float) -> dict:
    """Brake power/torque/fuel at WOT for one engine speed."""
    a = air_flow(rpm, DISPLACEMENT_M3)
    m_fuel = a["m_dot_air_kg_s"] / AFR_WOT
    p_chem = m_fuel * LHV_FUEL_J_KG
    eta_b = eff_calib(rpm) * _bsfc_shape_to_eff(interp(rpm, BSFC_RPM, BSFC_SHAPE))
    p_kw = p_chem * eta_b / 1e3
    omega = 2.0 * math.pi * rpm / 60.0
    torque = p_kw * 1e3 / omega
    bsfc = 3.6e9 / (eta_b * LHV_FUEL_J_KG)
    bmep_bar = torque * 4.0 * 2.0 * math.pi / (2.0 * DISPLACEMENT_M3) / 1e5
    return {**a, "afr": AFR_WOT, "m_dot_fuel_kg_s": m_fuel,
            "p_chem_kw": p_chem / 1e3, "eta_brake": eta_b,
            "power_kw": p_kw, "torque_nm": torque, "bsfc_g_kwh": bsfc,
            "bmep_bar": bmep_bar}
