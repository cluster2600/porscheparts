"""Driveline + accessory parasitic losses (0D).

The fuel path reports *crank* brake power (matching the public brochure
power-puller figure). This module estimates the external parasitic cost
downstream of the crank before the wheels. Engine friction and pumping
losses already sit inside the BSFC-shape calibration, so only external
items are modelled here:

  - oil pump drive (taken as an input from the oil module; not
    double-counted),
  - accessory drive (fan belt via the FACT_public 1.6:1 ratio, generator):
    assumed grid linear in rpm from 0.3 kW at 1000 rpm to 4.5 kW at the
    limiter (ASSUMPTION; the fan belt absorbs the bulk),
  - transmission mechanical loss: fixed fraction of transmitted power
    (ASSUMPTION; no gearbox data in repo).

Everything is a documented ASSUMPTION (M64-ACQ-BENCH-09). The module
outputs wheel-side power so the deviation table can state the crank-vs-
wheel convention explicitly instead of silently mixing them.
"""
from __future__ import annotations

from .common import interp

# Accessory drive loss grid (ASSUMPTION; dominated by the fan belt).
ACC_RPM = [1000.0, 4000.0, 6800.0]
ACC_W = [300.0, 1800.0, 4500.0]

# Transmission mechanical loss fraction of transmitted power (ASSUMPTION).
TRANS_LOSS_FRAC = 0.03


def accessory_w(rpm: float) -> float:
    return interp(rpm, ACC_RPM, ACC_W)


def point(rpm: float, p_brake_kw: float, oil_pump_w: float) -> dict:
    """Parasitic and wheel-side power at one engine speed."""
    acc_w = accessory_w(rpm)
    p_after_acc_kw = p_brake_kw - (acc_w + oil_pump_w) / 1e3
    trans_loss_kw = max(p_after_acc_kw, 0.0) * TRANS_LOSS_FRAC
    p_wheel_kw = max(p_after_acc_kw, 0.0) - trans_loss_kw
    return {
        "rpm": rpm,
        "p_brake_crank_kw": p_brake_kw,
        "p_accessory_kw": acc_w / 1e3,
        "p_oilpump_kw": oil_pump_w / 1e3,
        "p_trans_loss_kw": trans_loss_kw,
        "p_wheel_kw": p_wheel_kw,
        "driveline_loss_total_kw": (acc_w + oil_pump_w) / 1e3 + trans_loss_kw,
        "driveline_efficiency": (p_wheel_kw / p_brake_kw if p_brake_kw > 0 else 0.0),
        "provenance": "all constants ASSUMPTION (M64-ACQ-BENCH-09)",
    }
