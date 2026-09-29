#!/usr/bin/env python3
"""M64/60 virtual test bench — end-to-end runner (deterministic, 0D).

Usage:  python3 simulation/m64-virtual-bench/source/run_bench.py

Runs the WOT sweep and a WOT x part-load throttle sweep
(air -> charge-air -> fuel -> cooling-air/oil -> electrical -> driveline)
and writes:

    results/bench_results.json    all panels, calibration, versions
    results/sweep_wot.csv         flat WOT grid
    results/sweep_partload.csv    flat WOT + throttle-fraction grid
    results/deviation_table.csv   model vs public anchors
    results/report.md             solver/BC/convergence documentation

No wall-clock timestamps are written: byte-identical reruns are the
determinism contract asserted by tests/test_bench_smoke.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bench import (  # noqa: E402
    charge_air, cooling_air, driveline, dyno, electrical, fuel, oil,
)
from bench.air_path import PR_LIMITER_LABEL, PR_RPM, PR_VALS, VE_RPM, VE_VALS  # noqa: E402
from bench.common import (  # noqa: E402
    PUBLIC_CASE, REPO_ROOT, versions, write_csv, write_json,
)

RESULTS = REPO_ROOT / "simulation" / "m64-virtual-bench" / "results"

CSV_COLUMNS = [
    "rpm", "thr", "pr", "p_man_pa", "t_man_k", "rho_man_kg_m3", "ve",
    "m_dot_air_kg_s", "m_dot_air_per_turbo_kg_s", "flow_anchor_check",
    "m_dot_fuel_kg_s", "p_chem_kw", "eta_brake", "power_kw", "torque_nm",
    "bsfc_g_kwh", "bmep_bar",
    "t2_actual_k", "w_comp_shaft_total_kw", "q_intercooler_kw_per_turbo",
    "intercooler_effectiveness",
    "q_cooling_air_kw", "q_oil_kw", "q_exhaust_kw",
    "fan_mass_flow_kg_s", "fan_flow_l_s", "cooling_air_dt_k",
    "cooling_air_dt_implied_k", "cooling_air_exergy_destroyed_kw",
    "bank_metal_rise_k",
    "oil_flow_required_l_min", "oil_flow_available_assumed_l_min",
    "oil_flow_headroom_l_min", "oil_pump_shaft_w_assumed",
    "ignition_w", "injection_w", "starter_w", "total_electrical_w",
    "p_accessory_kw", "p_trans_loss_kw", "p_wheel_kw", "driveline_efficiency",
]

DEV_COLUMNS = ["label", "rpm", "thr", "public_value", "model_value", "unit",
               "rel_error_percent", "note"]


def build() -> tuple[list[dict], list[dict], dict]:
    rows = dyno.sweep()
    part = dyno.partload_sweep()
    dev = dyno.deviation_table(rows, part)
    v = dyno.verdicts(rows, part, dev, cooling_air.SPLIT_SUM)
    return rows, part, dev, v


def _model_hypotheses() -> dict:
    return {
        "compressor_pr_curve": {"rpm": PR_RPM, "pr": PR_VALS,
                                "tag": "HYPOTHESIS (K16 map not public, M64-ACQ-0003)",
                                "note": PR_LIMITER_LABEL},
        "ve_curve": {"rpm": VE_RPM, "ve": VE_VALS,
                     "tag": "HYPOTHESIS, plateau inside REPO 0.85-1.0 envelope"},
        "calibration": {**fuel.CAL_DIAG,
                        "form": "eta_b = (C0 + C1*4050/rpm) * eta_BSFC_shape(rpm)"},
        "bsfc_shape_g_kwh": {"rpm": fuel.BSFC_RPM, "shape": fuel.BSFC_SHAPE,
                             "tag": "HYPOTHESIS generic turbo-SI shape"},
        "part_load": {"throttle_fractions": dyno.PARTLOAD_FRACTIONS,
                      "law": "rho_man = 1 - thr*(1 - rho_man_WOT), VE unchanged (assumed)",
                      "tag": "ASSUMPTION (M64-ACQ-BENCH-10)"},
        "fan_airflow": {"law": "linear affinity from FACT_public 1.010 m3/s @ 6100 rpm engine",
                        "effective_fin_fraction": cooling_air.FIN_EFFECTIVE_FRACTION,
                        "tag": "HYPOTHESIS/ASSUMPTION (M64-ACQ-BENCH-06)"},
        "fin_stack_dt": {"rpm": cooling_air.DT_AIR_RPM_GRID,
                         "dt_k": cooling_air.DT_AIR_K,
                         "tag": "HYPOTHESIS shape through 35 K anchor (ASSUMPTION)"},
        "compressor": {"eta_ad": charge_air.ETA_COMP_AD,
                       "tag": "ASSUMPTION (K16 map not public, M64-ACQ-0003)"},
        "oil_circuit": {"pump_flow_l_min_at": dict(zip(oil.PUMP_FLOW_RPM, oil.PUMP_FLOW_L_MIN)),
                        "supply_pressure_bar": oil.OIL_SUPPLY_PRESSURE_BAR,
                        "film_floor_l_min": oil.FILM_FLOW_PER_BEARING_L_MIN * oil.N_BEARINGS,
                        "tag": "ASSUMPTION set, no pump curve in repo (M64-ACQ-BENCH-02)"},
        "driveline": {"accessory_w_grid": {"rpm": driveline.ACC_RPM, "w": driveline.ACC_W},
                      "trans_loss_frac": driveline.TRANS_LOSS_FRAC,
                      "tag": "ASSUMPTION set (M64-ACQ-BENCH-09)"},
        "electrical": {"tag": "all constants ASSUMPTION (M64-ACQ-BENCH-07)",
                       "starter_w": electrical.STARTER_INPUT_W},
    }


def write_outputs(rows: list[dict], part: list[dict], dev: list[dict],
                  v: dict) -> list[Path]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    written = []

    cranking = dyno.cranking_row()
    results = {
        "$comment": ("Deterministic 0D quasi-steady M64/60 virtual bench. "
                     "Not a measured part: hypothesis-grade simulation, see "
                     "inputs-gap.md for every missing input."),
        "schema_version": "1.1.0",
        "dataset_id": "M64-VIRTUAL-BENCH-0002",
        "status": "exploratory_reference",
        "solver": {
            "name": "closed-form 0D quasi-steady evaluation",
            "iterations": "none (no iterative solve; linear 2x2 calibration solve only)",
            "convergence": "N/A by construction; determinism = byte-identical reruns",
            "versions": versions(),
        },
        "boundary_conditions": {
            "ambient": {"p_pa": 101325.0, "t_k": 303.15, "tag": "ASSUMPTION"},
            "manifold_plateau": {"p_pa": 181300.0, "t_k": 323.15,
                                 "tag": "REPO simulation/993-turbo-dyno/dyno-reference.json airflow_envelope"},
            "calibration_anchors": {
                "peak_power": f"{PUBLIC_CASE['peak_power_kw']} kW @ {PUBLIC_CASE['peak_power_rpm']} rpm (rpm position ASSUMPTION)",
                "peak_torque": f"{PUBLIC_CASE['peak_torque_nm']} Nm @ {PUBLIC_CASE['peak_torque_rpm']} rpm (rpm position ASSUMPTION)",
                "source": PUBLIC_CASE["source"],
            },
            "heat_rejection_split_of_chemical_power": {
                "cooling_air": cooling_air.SPLIT_COOLING_AIR,
                "oil": cooling_air.SPLIT_OIL,
                "exhaust": cooling_air.SPLIT_EXHAUST,
                "radiated_accessories": cooling_air.SPLIT_RADIATED,
                "sum": cooling_air.SPLIT_SUM,
                "tag": "ASSUMPTION set (M64-ACQ-BENCH-04)",
            },
        },
        "model_hypotheses": _model_hypotheses(),
        "wot_sweep": rows,
        "partload_sweep": part,
        "cranking_electrical": cranking,
        "deviation_table": dev,
        "verdicts": v,
    }
    p = RESULTS / "bench_results.json"
    write_json(p, results)
    written.append(p)

    p = RESULTS / "sweep_wot.csv"
    write_csv(p, CSV_COLUMNS, [[r.get(c, "") for c in CSV_COLUMNS] for r in rows])
    written.append(p)

    p = RESULTS / "sweep_partload.csv"
    write_csv(p, CSV_COLUMNS, [[r.get(c, "") for c in CSV_COLUMNS] for r in part])
    written.append(p)

    dev_rows = [[d.get(c, "") for c in DEV_COLUMNS] for d in dev]
    p = RESULTS / "deviation_table.csv"
    write_csv(p, DEV_COLUMNS, dev_rows)
    written.append(p)

    p = RESULTS / "report.md"
    p.write_text(render_report(rows, part, dev, v), encoding="utf-8")
    written.append(p)
    return written


def render_report(rows: list[dict], part: list[dict], dev: list[dict],
                  v: dict) -> str:
    def fmt_dev():
        lines = ["| label | rpm | thr | public | model | unit | rel. err. % | note |",
                 "|---|---|---|---|---|---|---|---|"]
        for d in dev:
            lines.append(
                f"| {d['label']} | {d['rpm']:.0f} | {d['thr']:.2f} | "
                f"{d['public_value']:.1f} | {d['model_value']:.1f} | "
                f"{d['unit']} | {d['rel_error_percent']:+.2f} | {d['note']} |")
        return "\n".join(lines)

    peak_p = max(rows, key=lambda r: r["power_kw"])
    peak_t = max(rows, key=lambda r: r["torque_nm"])
    hot = peak_p
    mid = next(r for r in rows if r["rpm"] == 4050.0)
    best_pl = min((r for r in part if r["thr"] < 1.0),
                  key=lambda r: r["bsfc_g_kwh"])
    lines = [
        "# M64/60 Virtual Test Bench — 0D Quasi-Steady Report",
        "",
        "Dataset `M64-VIRTUAL-BENCH-0002`, status `exploratory_reference`.",
        "Hypothesis-grade simulation: nothing here is a measured, fitted,",
        "tested, released, or manufacturing-ready part or engine. Inputs and",
        "provenance tags: see every module docstring and",
        "[`inputs-gap.md`](../inputs-gap.md).",
        "",
        "## Solver, boundary conditions, convergence",
        "",
        "- **Solver:** closed-form 0D quasi-steady evaluation (stdlib + numpy).",
        "  No iterative solver; the only numeric solve is a linear 2x2 system",
        "  for the two-point efficiency calibration (`numpy.linalg.solve`).",
        "- **Convergence:** N/A by construction. Determinism contract:",
        "  byte-identical outputs on rerun (asserted in `tests/`).",
        "- **Boundary conditions:** ambient 101 325 Pa / 303.15 K (ASSUMPTION);",
        "  manifold plateau 181.3 kPa abs / 323.15 K (REPO",
        "  `simulation/993-turbo-dyno/dyno-reference.json` airflow envelope);",
        "  heat split 30 % cooling air / 10 % oil / 55 % exhaust / 5 % other",
        "  (ASSUMPTION set, M64-ACQ-BENCH-04).",
        "- **Upstream CFD inputs consumed:** fan-zone OpenFOAM deck",
        "  `simulation/993-fan-baseline` (caseB_corrected: 200 iterations,",
        "  final outer residual 3.6e-3, mass-flow match <0.01 % against the",
        "  prescribed 1.457 kg/s target — used as an order-of-magnitude check",
        "  only, its pressure rise is an input not a prediction); variants",
        "  anchor 0.156 kg/s per turbo from `simulation/993-turbo-variants`.",
        f"- **Grid:** WOT 1000–6800 rpm at 250 rpm plus both anchor speeds",
        f"  and the limiter ({len(rows)} points); part-load overlay at",
        f"  throttle fractions {dyno.PARTLOAD_FRACTIONS} on a coarser rpm grid",
        f"  ({len(part)} rows incl. WOT). All fixed.",
        "",
        "## Dyno result vs public case (408 PS / 540 Nm / 1.0 bar / 1010 l/s)",
        "",
        fmt_dev(),
        "",
        f"Model peak power {peak_p['power_kw']:.1f} kW @ {peak_p['rpm']:.0f} rpm;",
        f"model peak torque {peak_t['torque_nm']:.0f} Nm @ {peak_t['rpm']:.0f} rpm.",
        f"WOT fuel consumption at peak: {hot['m_dot_fuel_kg_s']:.4f} kg/s "
        f"({hot['m_dot_fuel_kg_s'] * 3600 / 0.740:.0f} l/h at 740 kg/m3 assumed);",
        f"min BSFC on WOT grid {min(r['bsfc_g_kwh'] for r in rows):.0f} g/kWh;",
        f"min BSFC on part-load grid {best_pl['bsfc_g_kwh']:.0f} g/kWh at",
        f"{best_pl['rpm']:.0f} rpm / thr {best_pl['thr']:.2f}.",
        "",
        "## Panel verdicts",
        "",
        f"- **Air / charge air:** {v['air']}",
        f"- **Fuel:** {v['fuel']}",
        f"- **Cooling / oil:** {v['oil_thermal']}",
        f"- **Driveline:** {v['driveline']}",
        "",
        "## Known contradictions (flagged, not corrected)",
        "",
        f"- At peak power the cooling-air share ({hot['q_cooling_air_kw']:.0f} kW)",
        f"  over the model effective fin flow ({hot['effective_fin_flow_kg_s']:.2f} kg/s)",
        f"  implies a free-stream dT of {hot['cooling_air_dt_implied_k']:.0f} K, far above",
        "  the 35 K fin-stack anchor: the published 1010 l/s fan figure and",
        "  a 30 % cooling-air split cannot both describe effective fin flow",
        "  (M64-ACQ-BENCH-04/-06).",
        "- Brochure boost setpoint is 1.0 bar gauge (FACT_public) but the",
        "  model plateau is the 0.8 bar effective reading from the repo dyno",
        f"  envelope: {hot['boost_gauge_pa_brochure'] / 1e5:.1f} vs "
        f"{hot['boost_gauge_pa_model'] / 1e5:.1f} bar kept as deviation",
        "  M64-ACQ-BENCH-08, uncorrected.",
        "- Public brochure gives 408 PS / 540 Nm but the repo survey carries no",
        "  rpm positions; 5750 / 4050 rpm are ASSUMPTIONs taken as anchors",
        "  (M64-ACQ-BENCH-01b).",
        "- Starter draw (4.5 kW) exceeds every other running electrical load",
        "  by an order of magnitude; battery/alternator sizing is out of scope.",
        "- Part-load rows use a throttled-density law with unchanged VE and",
        "  unchanged WOT efficiency calibration: the resulting BSFC is a",
        "  weakly-bounded estimate, not a fuel-consumption prediction",
        "  (M64-ACQ-BENCH-10).",
        "",
        "## Not proven by this bench",
        "",
        "Torque-curve shape between anchors, transient behaviour, drive-cycle",
        "fuel figures, turbo shaft speeds, oil pressure, metal temperatures,",
        "fan static pressure, wheel-side power validity (driveline constants",
        "are ASSUMPTIONs), part release of any kind, dimensional correctness,",
        "fitment, safety, or manufacturing readiness of any part.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    rows, part, dev, v = build()
    # cross-module consistency: oil cooler dT target must agree
    assert oil.OIL_DT_TARGET_K == 25.0
    for p in write_outputs(rows, part, dev, v):
        print(f"wrote {p.relative_to(REPO_ROOT)}")
    for d in dev:
        print(f"{d['label']:36s} {d['rpm']:6.0f} {d['thr']:4.2f} "
              f"{d['model_value']:9.1f} vs public {d['public_value']:8.1f} "
              f"{d['unit']}  ({d['rel_error_percent']:+.2f} %)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
