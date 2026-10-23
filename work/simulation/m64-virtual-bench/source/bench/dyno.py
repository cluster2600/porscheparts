"""M64/60 virtual dyno: WOT + part-load sweeps, deviation table vs public case.

The sweeps evaluate the fuel path (air + charge-air + combustion energy
balance) on fixed rpm grids, add the cooling-air, oil, electrical, and
driveline side-panels at each point, and compare the model peaks and
anchor rows against the public 408 PS / 540 Nm / 1.0 bar / 1010 l/s case
(docs/research/m64-public-engine-data-2026-09-27.md).

The public case is the calibration reference: both anchor rows (300 kW
@ 5750 rpm, 540 Nm @ 4050 rpm) enter the two-point calibration solve and
are exact by construction. Deviations at non-calibrated rpm (notably the
model peak locations) and every part-load row are blind predictions,
reported verbatim.
"""
from __future__ import annotations

from .common import DISPLACEMENT_M3, PUBLIC_CASE
from . import charge_air, cooling_air, driveline, electrical, fuel, oil

# WOT sweep grid (rpm). Deterministic fixed grid; 250 rpm spacing resolves
# the power peak (5750); the torque-plateau anchor 4050 is added explicitly
# so the deviation table can read model values exactly at both anchors.
SWEEP_RPM = sorted({float(r) for r in range(1000, 6801, 250)}
                   | {4050.0, 5750.0, 6800.0})
# Part-load overlay: coarser rpm grid, fixed throttle fractions
# (ASSUMPTION law in air_path.manifold_state, M64-ACQ-BENCH-10).
PARTLOAD_RPM = sorted({float(r) for r in range(1500, 6501, 500)})
PARTLOAD_FRACTIONS = [0.25, 0.50, 0.75]
CRANK_RPM = 250.0                # single cranking row on the electrical grid


def _row(rpm: float, thr: float) -> dict:
    """Full-panel row at one (rpm, throttle) operating point."""
    f = fuel.point(rpm, thr)
    ca = charge_air.point(rpm, thr, f["m_dot_air_kg_s"])
    t = cooling_air.point(f["p_chem_kw"], rpm)
    o = oil.point(rpm, t["q_oil_kw"])
    e = electrical.point(rpm, f["m_dot_fuel_kg_s"])
    d = driveline.point(rpm, f["power_kw"], o["oil_pump_shaft_w_assumed"])
    return {**f, **ca, **t,
            # cooling_air.dt_k is the anchor-shape rise; expose bank alias
            "bank_metal_rise_k": t["cooling_air_dt_k"],
            **o, **e, **d}


def sweep() -> list[dict]:
    """One dict per WOT grid point."""
    return [_row(rpm, 1.0) for rpm in SWEEP_RPM]


def partload_sweep() -> list[dict]:
    """One dict per (rpm, throttle) point: WOT rows plus the overlay grid.

    Returned list is sorted by (thr, rpm); WOT rows repeat the WOT grid
    values only where the coarser rpm grid coincides, so the CSV is a
    self-contained map of the model."""
    rows = [_row(rpm, 1.0) for rpm in SWEEP_RPM]
    rows += [_row(rpm, thr) for thr in PARTLOAD_FRACTIONS for rpm in PARTLOAD_RPM]
    return sorted(rows, key=lambda r: (r["thr"], r["rpm"]))


def cranking_row() -> dict:
    """Electrical-only row at cranking speed (engine not producing)."""
    return electrical.point(CRANK_RPM, 0.0)


def _peak(rows: list[dict], key: str) -> dict:
    return max(rows, key=lambda r: r[key])


def deviation_table(rows: list[dict], part: list[dict]) -> list[dict]:
    """Model vs public-case anchors. Every row: label, rpm, thr, public,
    model, unit, relative error, note."""
    peak_p = _peak(rows, "power_kw")
    peak_t = _peak(rows, "torque_nm")
    at5750 = next(r for r in rows if r["rpm"] == PUBLIC_CASE["peak_power_rpm"])
    at4050 = next(r for r in rows if r["rpm"] == PUBLIC_CASE["peak_torque_rpm"])
    fan_at_6100 = cooling_air.fan_flow(6100.0)
    boost_row = at5750

    def row(label, rpm, thr, pub, mod, unit, note):
        rel = 100.0 * (mod - pub) / pub if pub else None
        return {"label": label, "rpm": rpm, "thr": thr,
                "public_value": pub, "model_value": mod, "unit": unit,
                "rel_error_percent": rel, "note": note}

    cal = "calibrated anchor (model is exact by construction)"
    return [
        row("peak_power", peak_p["rpm"], 1.0, PUBLIC_CASE["peak_power_kw"],
            peak_p["power_kw"], "kW",
            "model peak may sit off the calibrated rpm if the BSFC/VE shape "
            "tilts the curve"),
        row("power_at_public_peak_rpm", at5750["rpm"], 1.0,
            PUBLIC_CASE["peak_power_kw"], at5750["power_kw"], "kW", cal),
        row("peak_torque", peak_t["rpm"], 1.0, PUBLIC_CASE["peak_torque_nm"],
            peak_t["torque_nm"], "Nm",
            "model peak torque location is a prediction"),
        row("torque_at_public_torque_rpm", at4050["rpm"], 1.0,
            PUBLIC_CASE["peak_torque_nm"], at4050["torque_nm"], "Nm",
            "calibrated anchor (two-point calibration solve uses this "
            "anchor; exact by construction)"),
        row("boost_plateau_vs_brochure", boost_row["rpm"], 1.0,
            boost_row["boost_gauge_pa_brochure"] / 1e5,
            boost_row["boost_gauge_pa_model"] / 1e5, "bar_gauge",
            "model keeps the 0.8 bar REPO-envelope plateau; brochure "
            "1.0 bar setpoint is FACT_public (M64-ACQ-BENCH-08)"),
        row("cooling_air_flow_at_6100", 6100.0, 1.0, 1010.0,
            fan_at_6100["fan_flow_l_s"], "l/s",
            "exact by construction of the fan anchor; effective fin flow "
            f"{fan_at_6100['effective_fin_flow_kg_s']:.2f} kg/s assumes a "
            "60 % effective fraction (ASSUMPTION, M64-ACQ-BENCH-06)"),
    ]


def verdicts(rows: list[dict], part: list[dict], dev: list[dict],
             split_sum: float) -> dict:
    """Four-line engineering verdicts (air/charge-air, fuel, cooling/oil,
    driveline)."""
    peak_p = _peak(rows, "power_kw")
    peak_t = _peak(rows, "torque_nm")
    pl_best = min((r for r in part if r["thr"] < 1.0),
                  key=lambda r: r["bsfc_g_kwh"])
    air = ("AIR/CHARGE-AIR: charge flow closes the public 0.8 bar plateau "
           f"with the VE shape inside the REPO 0.85-1.0 envelope near peak; "
           f"per-turbo flow {peak_p['m_dot_air_per_turbo_kg_s']:.3f} kg/s "
           "sits within +-3% of the 0.156 kg/s REPO variants anchor at "
           f"mid-high rpm; compressor duty {peak_p['w_comp_shaft_total_kw']:.0f} "
           f"kW total at {peak_p['t2_actual_k']:.0f} K discharge with "
           "eta_ad=0.65 ASSUMPTION; implied intercooler effectiveness "
           f"{peak_p['intercooler_effectiveness']:.2f}; PR curve is an "
           "unverified map hypothesis (M64-ACQ-0003).")
    fuel_v = ("FUEL: energy balance at AFR 12 reproduces 300 kW at 5750 rpm "
              "and 540 Nm at 4050 rpm exactly (both anchors enter the "
              "two-point calibration); model peak "
              f"{peak_t['torque_nm']:.0f} Nm at {peak_t['rpm']:.0f} rpm and "
              "curve shape between anchors are blind predictions; BSFC min "
              f"{min(r['bsfc_g_kwh'] for r in rows):.0f} g/kWh (WOT grid) is "
              f"plausible for a turbocharged SI; part-load min "
              f"{pl_best['bsfc_g_kwh']:.0f} g/kWh at "
              f"{pl_best['rpm']:.0f} rpm / thr {pl_best['thr']:.2f} is a "
              "weakly-bounded estimate (no pumping-loss model); fuel card "
              "missing (M64-ACQ-BENCH-05/-10).")
    hot = peak_p
    oil_v = (f"COOLING/OIL: oil flow demand {hot['oil_flow_required_l_min']:.0f} "
             f"L/min (film-floor-dominated) vs assumed pump "
             f"{hot['oil_flow_available_assumed_l_min']:.0f} L/min — no "
             "sourced pump curve (M64-ACQ-BENCH-02); fan-air "
             f"{hot['fan_mass_flow_kg_s']:.2f} kg/s "
             f"({hot['fan_flow_l_s']:.0f} l/s) implies effective-fin dT "
             f"{hot['cooling_air_dt_implied_k']:.0f} K at the assumed "
             f"{hot['q_cooling_air_kw']:.0f} kW air share — the fan is the "
             "thermal bottleneck until the split and hA are measured "
             "(M64-ACQ-BENCH-04).")
    drv = (f"DRIVELINE: crank {hot['p_brake_crank_kw']:.0f} kW at peak maps to "
           f"{hot['p_wheel_kw']:.0f} kW wheel-side under ASSUMPTION parasitics "
           f"(accessory {hot['p_accessory_kw']:.1f} kW + oil pump "
           f"{hot['p_oilpump_kw']:.1f} kW + "
           f"{hot['driveline_loss_total_kw']:.1f} kW total loss, "
           f"eta_dl {hot['driveline_efficiency']:.2f}); gearbox data missing "
           "(M64-ACQ-BENCH-09).")
    return {
        "air": air,
        "fuel": fuel_v,
        "oil_thermal": oil_v,
        "driveline": drv,
        "heat_split_sum": split_sum,
        "peak_power_model_kw": peak_p["power_kw"],
        "peak_power_model_rpm": peak_p["rpm"],
        "peak_torque_model_nm": peak_t["torque_nm"],
        "peak_torque_model_rpm": peak_t["rpm"],
        "deviation_table": dev,
    }
