#!/usr/bin/env python3
"""Flat-fan (horizontal, on top of the engine) sizing study F2.

A flat fan, as on the 917, the 935 and Gunther Werks' 911s, frees the fan
diameter from the upright 993 housing throat. This study asks which
diameter moves a given engine's cooling air most efficiently.

For each duty case (how much air the engine needs, and how hard its fins
resist) it redesigns the F1 rotor family at every diameter: same method,
hub/tip ratio, shroud, generic stator and bellmouth. It sweeps design speed
and blade loading, and keeps the most efficient design that delivers at
least 15 % more than the duty flow on that engine's resistance curve. Flow at
equal shaft power scales as efficiency^(1/3), so efficiency is the figure
of merit.

Tip speed is capped at the F1 value, so no candidate is louder than F1.
All duties are synthetic; this is a one-dimensional model, not CFD.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path


ROTOR_SCRIPT = Path(__file__).resolve().parent / "cooling_impeller_f1.py"

# (flow scale, pressure scale) against the synthetic F0 point 1.01 m3/s at 800 Pa.
DUTY_CASES = (
    {"flow_scale": 1.0, "pressure_scale": 1.0, "label": "synthetic F0 duty"},
    {"flow_scale": 1.0, "pressure_scale": 0.6, "label": "same air, 40 % less resistance"},
    {"flow_scale": 1.0, "pressure_scale": 1.6, "label": "same air, 60 % more resistance"},
    {"flow_scale": 2.0, "pressure_scale": 1.0, "label": "twice the air"},
    {"flow_scale": 4.0, "pressure_scale": 1.0, "label": "four times the air"},
)
DIAMETERS_MM = tuple(range(220, 521, 20))
SPEEDS_RPM = tuple(range(2000, 12001, 500))
DESIGN_GAINS = tuple(round(1.15 + 0.05 * i, 2) for i in range(9))
TARGET_FLOW_MARGIN = 1.15
HUB_TO_TIP_RATIO = 60.0 / 119.5          # flat-fan family choice: the alternator moves off the fan shaft
SHROUD_TO_TIP_MM = 2.5
TOOTH_HEIGHT_MM = 2.0
LABYRINTH_GAP_MM = 2.0
MINIMUM_DE_HALLER = 0.65
EOS_M400_PLATE_MM = 400.0
CONFIG = {"shrouded": True, "stator": True, "bellmouth": True}


def load_rotor_module():
    """A private instance of the F1 module whose constants this study
    overrides; the committed F1 part is never touched."""
    spec = importlib.util.spec_from_file_location("cooling_impeller_f1_sizing", ROTOR_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


# The flat-fan family is a shrouded axial rotor drawn with the F1 method.
# Its own blade rules are pinned here, so changes to the upright F1 rotor
# (which follows the original's cup and has no shroud) do not move this study.
FAMILY_CONSTANTS = {
    "SHROUDED": True,
    "SHROUD_THICKNESS_MM": 2.5,
    "MAX_BLADE_AXIAL_PROJECTION_MM": 25.0,
    "TARGET_DIFFUSION_FACTOR": 0.45,
    "MAXIMUM_SOLIDITY": 1.6,
    "VORTEX_EXPONENT": 1.0,
    "DESIGN_EFFICIENCY_GUESS": 0.80,
    "BLADE_COUNT": 11,
}


def configure(m, diameter_mm: float, speed_rpm: float, design_gain: float, duty: dict[str, float]) -> None:
    for name, value in FAMILY_CONSTANTS.items():
        setattr(m, name, value)
    tip_mm = diameter_mm / 2.0 - TOOTH_HEIGHT_MM - SHROUD_TO_TIP_MM
    m.OUTER_DIAMETER_MM = diameter_mm
    m.SHROUD_OUTER_RADIUS_MM = diameter_mm / 2.0 - TOOTH_HEIGHT_MM
    m.HOUSING_SYNTHETIC_THROAT_MM = diameter_mm + 2.0 * LABYRINTH_GAP_MM
    m.HUB_OUTER_DIAMETER_MM = 2.0 * HUB_TO_TIP_RATIO * tip_mm
    m.SYNTHETIC_NOMINAL_SPEED_RPM = speed_rpm
    m.DESIGN_FLOW_GAIN = design_gain
    m.SYNTHETIC_AIRFLOW_M3_S = 1.01 * duty["flow_scale"]
    m.SYNTHETIC_PRESSURE_RISE_PA = 800.0 * duty["pressure_scale"]


def operating_point(m, design, speed_rpm: float) -> dict[str, float]:
    """Flow where useful pressure = K Q^2, with an upper bound wide enough
    for the scaled duties (the F1 module's false-position solver)."""
    k = m.system_coefficient()
    flow = m._root(
        lambda q: k * q**2 - m.rotor_performance(design, q, speed_rpm, **CONFIG)["useful_pressure_pa"],
        0.05, 4.0 * m.SYNTHETIC_AIRFLOW_M3_S, 1.0e-9,
        guess=design["design_flow_m3_s"],
    )
    return m.rotor_performance(design, flow, speed_rpm, **CONFIG)


def evaluate(m, diameter_mm: float, speed_rpm: float, design_gain: float,
             duty: dict[str, float]) -> dict[str, float] | None:
    configure(m, diameter_mm, speed_rpm, design_gain, duty)
    design = m.design_f1_rotor()
    de_haller = min(s["de_haller_ratio"] for s in design["sections"])
    if de_haller < MINIMUM_DE_HALLER:
        return None
    point = operating_point(m, design, speed_rpm)
    if point["stalled_station_count"]:
        return None
    return {
        "diameter_mm": diameter_mm,
        "speed_rpm": speed_rpm,
        "design_gain": design_gain,
        "flow_m3_s": point["flow_m3_s"],
        "shaft_power_w": point["shaft_power_w"],
        "efficiency": point["efficiency"],
        "tip_speed_m_s": m.angular_speed(speed_rpm) * diameter_mm / 2000.0,
        "min_de_haller": de_haller,
    }


def study(cases=DUTY_CASES, diameters=DIAMETERS_MM, speeds=SPEEDS_RPM, gains=DESIGN_GAINS) -> dict[str, object]:
    m = load_rotor_module()
    reference = load_rotor_module()
    tip_cap = reference.angular_speed(reference.SYNTHETIC_NOMINAL_SPEED_RPM) * reference.OUTER_DIAMETER_MM / 2000.0
    out_cases = []
    for duty in cases:
        target = TARGET_FLOW_MARGIN * 1.01 * duty["flow_scale"]
        rows = []
        for d in diameters:
            best = None
            for rpm in speeds:
                if m.angular_speed(rpm) * d / 2000.0 > tip_cap + 1e-9:
                    continue
                for g in gains:
                    c = evaluate(m, d, rpm, g, duty)
                    if c is None or c["flow_m3_s"] < target:
                        continue
                    if best is None or c["efficiency"] > best["efficiency"]:
                        best = c
            rows.append({"diameter_mm": d, "best": best})
        valid = [r for r in rows if r["best"]]
        optimum = max(valid, key=lambda r: r["best"]["efficiency"]) if valid else None
        at_248 = next((r["best"] for r in rows if r["diameter_mm"] == 240 and r["best"]), None)
        out_cases.append({
            **duty,
            "target_flow_m3_s": target,
            "system_pressure_at_target_pa": 800.0 * duty["pressure_scale"] * (target / (1.01 * duty["flow_scale"])) ** 2,
            "rows": rows,
            "smallest_feasible_diameter_mm": min((r["diameter_mm"] for r in valid), default=None),
            "optimum_diameter_mm": optimum["diameter_mm"] if optimum else None,
            "optimum": optimum["best"] if optimum else None,
            "flow_gain_at_equal_power_vs_240_mm": (
                (optimum["best"]["efficiency"] / at_248["efficiency"]) ** (1.0 / 3.0) - 1.0
                if optimum and at_248 else None
            ),
        })
    by_label = {c["label"]: c for c in out_cases}
    nominal = by_label["synthetic F0 duty"]
    return {
        "schema_version": "1.0.0",
        "study_id": "993-FLAT-FAN-SIZING-F2",
        "rotor_family": "993-ENG-COOLING-IMPELLER-WE43-F1-0001 method, shroud, designed-for-point blades, generic stator and bellmouth",
        "sweep": {
            "diameters_mm": list(diameters),
            "speeds_rpm": list(speeds),
            "design_gains": list(gains),
            "target": f"deliver at least {TARGET_FLOW_MARGIN} x the duty flow on the duty's K Q^2 curve",
            "figure_of_merit": "fan efficiency; at equal shaft power flow scales as efficiency^(1/3)",
            "hub_to_tip_ratio": HUB_TO_TIP_RATIO,
            "tip_speed_cap_m_s": tip_cap,
            "minimum_de_haller": MINIMUM_DE_HALLER,
        },
        "measured_context": {
            "source": "Ferdinand magazine on EB Motorsport's 935-derived flat fan kit",
            "url": "https://ferdinandmagazine.com/porsche-flat-fan-kit",
            "fan_power_hp": {"4000_fan_rpm": 1.5, "12000_fan_rpm": 32.0},
            "note": "about ten times this study's synthetic power at the same fan speed: real flat-fan duties are far larger than the synthetic F0 case, which pushes the optimum toward the big-flow cases below",
            "authority": "magazine report of a builder's dyno measurement; not used as model input",
        },
        "cases": out_cases,
        "results": {
            "optimum_diameter_mm_by_case": {c["label"]: c["optimum_diameter_mm"] for c in out_cases},
            "smallest_feasible_diameter_mm_by_case": {c["label"]: c["smallest_feasible_diameter_mm"] for c in out_cases},
            "optimum_efficiency_by_case": {c["label"]: c["optimum"]["efficiency"] if c["optimum"] else None for c in out_cases},
            "bigger_is_better_at_synthetic_duty": nominal["optimum_diameter_mm"] == max(diameters),
            "eos_m400_plate_mm": EOS_M400_PLATE_MM,
        },
        "interpretation": {
            "sizing": "the best diameter follows the duty: a small-air, high-resistance duty wants a small fast fan; more air at the same pressure wants a bigger fan, which only a flat layout can package",
            "synthetic_duty": "at the synthetic F0 duty the upright F1 size is already near optimum, so a flat fan would not help by size alone",
            "resistance": "at fixed efficiency and power, Q scales as K^(-1/3): 40 % less path resistance gives about 19 % more air, the other lever a flat plenum offers",
            "limits": "one-dimensional model, synthetic duties, generic stator, no plenum, distribution, drive or packaging model",
        },
        "manufacturing_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


def plot(report: dict[str, object], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = ["#1f6fb2", "#2e8b57", "#b03a2e", "#8e44ad", "#d68910"]
    fig, ax = plt.subplots(figsize=(8, 5), dpi=120)
    for color, case in zip(colors, report["cases"]):
        rows = [r for r in case["rows"] if r["best"]]
        ax.plot([r["diameter_mm"] for r in rows], [r["best"]["efficiency"] for r in rows],
                "o-", color=color, lw=2, ms=3,
                label=f"{case['label']} ({case['target_flow_m3_s']:.2f} m³/s)")
        if case["optimum"]:
            ax.plot(case["optimum_diameter_mm"], case["optimum"]["efficiency"], "*", color=color, ms=12)
    ax.axvline(248.0, color="#777777", ls="--", lw=1)
    ax.axvline(EOS_M400_PLATE_MM, color="#777777", ls=":", lw=1)
    ax.text(250, 0.02, " F1 upright size", fontsize=8, color="#555555", transform=ax.get_xaxis_transform())
    ax.text(402, 0.02, " EOS M 400 plate", fontsize=8, color="#555555", transform=ax.get_xaxis_transform())
    ax.set_xlabel("fan diameter over the shroud (mm)")
    ax.set_ylabel("best fan efficiency meeting the duty")
    ax.set_title("Flat-fan sizing by duty, 1D model — synthetic duties, ★ = optimum", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    parser.add_argument("--plot", type=Path)
    args = parser.parse_args()
    report = study()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.plot:
        plot(report, args.plot)
    print(json.dumps(report["results"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
