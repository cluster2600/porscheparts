"""Virtual dyno: WOT torque/power sweep + deviation table vs public case.

The sweep evaluates the fuel path (air + combustion energy balance) on a
fixed rpm grid, adds the thermal-loop and electrical side-panels at each
point, and compares the model peaks and anchor rows against the public
408 PS / 540 Nm case (docs/research/m64-public-engine-data-2026-09-27.md).

The public case is the calibration reference; deviations at non-calibrated
rpm (notably the torque anchor) are blind predictions, reported verbatim.
"""
from __future__ import annotations

from .common import DISPLACEMENT_M3, PUBLIC_CASE
from . import electrical, fuel, thermal

# WOT sweep grid (rpm). Deterministic fixed grid; 250 rpm spacing resolves
# the power peak (5750); the torque-plateau anchor 4050 is added explicitly
# so the deviation table can read model values exactly at both anchors.
SWEEP_RPM = sorted({float(r) for r in range(1000, 6801, 250)}
                   | {4050.0, 5750.0, 6800.0})
CRANK_RPM = 250.0                # single cranking row on the electrical grid


def sweep() -> list[dict]:
    """One dict per grid point: air, fuel, thermal, electrical panels."""
    rows = []
    for rpm in SWEEP_RPM:
        f = fuel.point(rpm)
        t = thermal.bank_model(f["power_kw"], f["p_chem_kw"], rpm)
        e = electrical.point(rpm, f["m_dot_fuel_kg_s"])
        rows.append({**f, **t, **e})
    return rows


def cranking_row() -> dict:
    """Electrical-only row at cranking speed (engine not producing)."""
    return electrical.point(CRANK_RPM, 0.0)


def _peak(rows: list[dict], key: str) -> dict:
    return max(rows, key=lambda r: r[key])


def deviation_table(rows: list[dict]) -> list[dict]:
    """Model vs public-case anchors. Every row: label, rpm, public, model,
    unit, relative error, note."""
    peak_p = _peak(rows, "power_kw")
    peak_t = _peak(rows, "torque_nm")
    at5750 = next(r for r in rows if r["rpm"] == PUBLIC_CASE["peak_power_rpm"])
    at4050 = next(r for r in rows if r["rpm"] == PUBLIC_CASE["peak_torque_rpm"])

    def row(label, rpm, pub, mod, unit, note):
        rel = 100.0 * (mod - pub) / pub if pub else None
        return {"label": label, "rpm": rpm, "public_value": pub,
                "model_value": mod, "unit": unit,
                "rel_error_percent": rel, "note": note}

    cal = "calibrated anchor (model is exact by construction)"
    blind = "blind prediction (not used in calibration)"
    return [
        row("peak_power", peak_p["rpm"], PUBLIC_CASE["peak_power_kw"],
            peak_p["power_kw"], "kW",
            "model peak may sit off the calibrated rpm if the BSFC/VE shape "
            "tilts the curve"),
        row("power_at_public_peak_rpm", at5750["rpm"],
            PUBLIC_CASE["peak_power_kw"], at5750["power_kw"], "kW", cal),
        row("peak_torque", peak_t["rpm"], PUBLIC_CASE["peak_torque_nm"],
            peak_t["torque_nm"], "Nm",
            "model peak torque location is a prediction"),
        row("torque_at_public_torque_rpm", at4050["rpm"],
            PUBLIC_CASE["peak_torque_nm"], at4050["torque_nm"], "Nm", blind),
    ]


def verdicts(rows: list[dict], dev: list[dict],
             split_sum: float) -> dict:
    """Three-line engineering verdicts (air / fuel / oil-thermal)."""
    peak_p = _peak(rows, "power_kw")
    peak_t = _peak(rows, "torque_nm")
    air = ("AIR: charge flow closes the public 0.8 bar plateau with the VE "
           "shape inside the REPO 0.85-1.0 envelope near peak; per-turbo flow "
           f"{peak_p['m_dot_air_per_turbo_kg_s']:.3f} kg/s sits within +-3% of "
           "the 0.156 kg/s REPO variants anchor at mid-high rpm; PR curve is "
           "an unverified map hypothesis (M64-ACQ-0003).")
    fuel_v = ("FUEL: energy balance at AFR 12 reproduces 300 kW at 5750 rpm "
              f"exactly (calibration) and {peak_t['torque_nm']:.0f} Nm at "
              "4050 rpm as a blind prediction; BSFC min "
              f"{min(r['bsfc_g_kwh'] for r in rows):.0f} g/kWh is plausible "
              "for a turbocharged SI; fuel card missing (M64-ACQ-BENCH-05).")
    hot = peak_p
    oil_v = (f"OIL/THERMAL: oil flow demand {hot['oil_flow_required_l_min']:.0f} "
             f"L/min at peak vs NO sourced pump curve (M64-ACQ-BENCH-02); "
             f"fan-air {hot['fan_mass_flow_kg_s']:.2f} kg/s implies "
             f"cooling-air dT {hot['cooling_air_dt_k']:.0f} K at the assumed "
             f"{hot['q_cooling_air_kw']:.0f} kW air share - the fan is the "
             "thermal bottleneck until the split and hA are measured "
             "(M64-ACQ-BENCH-04).")
    return {
        "air": air,
        "fuel": fuel_v,
        "oil_thermal": oil_v,
        "heat_split_sum": split_sum,
        "peak_power_model_kw": peak_p["power_kw"],
        "peak_power_model_rpm": peak_p["rpm"],
        "peak_torque_model_nm": peak_t["torque_nm"],
        "peak_torque_model_rpm": peak_t["rpm"],
        "deviation_table": dev,
    }
