"""993 flat (horizontal) fan rotor, concept F0, drawn inside the envelope of
the scanned 935 flat-fan rotor.

Design choice: a flat fan on top of a 993 engine, in the spirit of the
Gunther Werks cars, using the one flat-fan rotor this repository has
actually measured (the 935 twin, twins/935-horizontal-fan-cad-twin) as the
envelope and interface: same hub and drum (r 89.3 mm), same tip radius
(135.25 mm), same drive dogs and fastener pattern, same axial span. Inside
that envelope the blades are redrawn with the F1 velocity-triangle method
(parts/993-eng-cooling-impeller-we43-f1-0001), and the hub's unobserved
interior is designed as a hollow shell.

Both rotors are judged by the same one-dimensional blade-element model on
the same system curve: the 993 duty that the F1 study inferred from the
Turbo rotor rebuild (2.34 m3/s at 2,155 Pa). The 935 rotor enters the model
through its fitted sections (chord, stagger and camber-line metal angles).
These are model estimates on an inferred duty, not measurements, not CFD,
and not a statement about the performance of any real 935 or 993.

Usage: flat_fan_993_f0.py study OUT.json       (aero comparison, no CAD)
       flat_fan_993_f0.py sections OUT.json    (blade sections for the CAD)
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
F1_SCRIPT = ROOT / "parts/993-eng-cooling-impeller-we43-f1-0001/source/cooling_impeller_f1.py"
TWIN = ROOT / "twins/935-horizontal-fan-cad-twin/params"

HUB_RADIUS_MM = 89.3          # fitted drum radius, upper band (frame.json: 89.289)
TIP_GAP_MM = 2.0              # hypothesis H-TIP-GAP, same for both rotors
MAX_TIP_SPEED_M_S = 128.0     # F1's tip-speed cap (noise and stress)
MIN_DE_HALLER = 0.65
DUTY_FLOW_M3_S = 2.34         # F1-inferred 993 duty, flow
BLADE_COUNTS = (9, 11, 13)
DESIGN_SPEEDS_RPM = tuple(range(6000, 9001, 250))
DESIGN_GAINS = tuple(round(1.0 + 0.05 * i, 2) for i in range(7))
CONFIGS = {"rotor_only": {"shrouded": False, "stator": False, "bellmouth": True},
           "rotor_and_stator": {"shrouded": False, "stator": True, "bellmouth": True}}


def load_model(tip_mm: float):
    spec = importlib.util.spec_from_file_location("cooling_impeller_f1_flat993", F1_SCRIPT)
    m = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(m)
    m.SHROUDED = False
    m.SHROUD_THICKNESS_MM = 0.0
    m.OUTER_DIAMETER_MM = 2.0 * tip_mm
    m.SHROUD_OUTER_RADIUS_MM = tip_mm
    m.HOUSING_SYNTHETIC_THROAT_MM = 2.0 * (tip_mm + TIP_GAP_MM)
    m.REFERENCE_TIP_GAP_MM = TIP_GAP_MM
    m.HUB_OUTER_DIAMETER_MM = 2.0 * HUB_RADIUS_MM
    m.MAX_BLADE_AXIAL_PROJECTION_MM = 50.0
    return m


# ---------------------------------------------------------------- 935 baseline

def camber_metal_angles(sec: dict, x_tab: np.ndarray) -> tuple[float, float, float]:
    """Stagger and metal angles, from the axial direction, of a fitted 935
    section. The camber line is the mean of the fitted upper and lower
    surfaces; its slope is taken over x 0.05-0.15 and 0.85-0.95, clear of the
    rounded ends."""
    up, lo = np.asarray(sec["upper_mm"]), np.asarray(sec["lower_mm"])
    chord = sec["chord_mm"]
    yc = 0.5 * (up + lo)
    def slope(a, b):
        sel = (x_tab >= a) & (x_tab <= b)
        return float(np.polyfit(x_tab[sel] * chord, yc[sel], 1)[0])
    gamma = sec["stagger_from_tangential_deg"]
    theta_le = gamma + math.degrees(math.atan(slope(0.05, 0.15)))
    theta_te = gamma + math.degrees(math.atan(slope(0.85, 0.95)))
    return 90.0 - gamma, 90.0 - theta_le, 90.0 - theta_te


def rotor_935(m, loss_note: str = "airfoil-like") -> dict:
    blade = json.loads((TWIN / "blade.json").read_text())
    x_tab = np.asarray(blade["chord_stations_x"])
    secs = blade["sections"]
    rr = np.array([s["r_mm"] for s in secs])
    rows = []
    for s in secs:
        stg, k1, k2 = camber_metal_angles(s, x_tab)
        rows.append((s["chord_mm"], stg, k1, k2, s["max_thickness_mm"]))
    rows = np.array(rows)
    tip = blade["tip_radius_mm"]
    out = []
    for r in m.stations(HUB_RADIUS_MM, tip):
        r_mm = r * 1000.0
        chord, stg, k1, k2, t = (float(np.interp(r_mm, rr, rows[:, j])) for j in range(5))
        out.append({"radius_mm": r_mm, "chord_mm": chord, "solidity": chord * blade["blade_count"] / (2 * math.pi * r_mm),
                    "camber_deg": k1 - k2, "stagger_deg": stg, "inlet_metal_deg": k1, "outlet_metal_deg": k2,
                    "thickness_mm": t})
    return {"source": "twins/935-horizontal-fan-cad-twin/params/blade.json", "hub_radius_mm": HUB_RADIUS_MM,
            "tip_radius_mm": tip, "annulus_area_m2": math.pi * ((tip / 1000) ** 2 - (HUB_RADIUS_MM / 1000) ** 2),
            "blade_count": blade["blade_count"], "sections": out}


# ---------------------------------------------------------------- duty solve

def speed_for_duty(m, rotor: dict, config: dict, flow: float = DUTY_FLOW_M3_S, loss_factor: float = 1.0):
    """Fan speed at which the rotor delivers `flow` on the system curve."""
    need = m.system_coefficient() * flow ** 2
    def surplus(n):
        return m.rotor_performance(rotor, flow, n, loss_factor=loss_factor, **config)["useful_pressure_pa"] - need
    lo, hi = 1500.0, 20000.0
    if surplus(hi) < 0:
        return None
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if surplus(mid) < 0:
            lo = mid
        else:
            hi = mid
    perf = m.rotor_performance(rotor, flow, hi, loss_factor=loss_factor, **config)
    perf["speed_rpm"] = hi
    perf["tip_speed_m_s"] = m.angular_speed(hi) * rotor["tip_radius_mm"] / 1000.0
    return perf


def summary(perf: dict) -> dict:
    keys = ("speed_rpm", "tip_speed_m_s", "flow_m3_s", "useful_pressure_pa", "shaft_power_w", "efficiency",
            "stalled_station_count", "rotor_profile_loss_pa", "exit_swirl_loss_pa", "tip_gap_loss_pa")
    return {k: (round(perf[k], 4) if isinstance(perf[k], float) else perf[k]) for k in keys}


# ---------------------------------------------------------------- new design

def design(m, blades: int, speed: float, gain: float) -> dict | None:
    m.BLADE_COUNT = blades
    m.SYNTHETIC_NOMINAL_SPEED_RPM = speed
    m.DESIGN_FLOW_GAIN = gain
    d = m.design_f1_rotor()
    if min(s["de_haller_ratio"] for s in d["sections"]) < MIN_DE_HALLER:
        return None
    return d


def study() -> dict:
    blade = json.loads((TWIN / "blade.json").read_text())
    tip = blade["tip_radius_mm"]
    m = load_model(tip)
    base = rotor_935(m)
    report = {"duty": {"flow_m3_s": DUTY_FLOW_M3_S, "pressure_pa": round(m.system_coefficient() * DUTY_FLOW_M3_S ** 2, 1),
                       "basis": "F1-inferred 993 duty, quadratic system curve; a flat-fan plenum may have a different resistance"},
              "envelope": {"hub_radius_mm": HUB_RADIUS_MM, "tip_radius_mm": tip, "tip_gap_mm": TIP_GAP_MM,
                           "max_tip_speed_m_s": MAX_TIP_SPEED_M_S}}
    for name, cfg in CONFIGS.items():
        b = speed_for_duty(m, base, cfg)
        b15 = speed_for_duty(m, base, cfg, loss_factor=1.5)
        best = None
        for z in BLADE_COUNTS:
            for n in DESIGN_SPEEDS_RPM:
                if m.angular_speed(n) * tip / 1000.0 > MAX_TIP_SPEED_M_S:
                    continue
                for g in DESIGN_GAINS:
                    d = design(m, z, n, g)
                    if d is None:
                        continue
                    p = speed_for_duty(m, d, cfg)
                    if p is None or p["stalled_station_count"] or p["tip_speed_m_s"] > MAX_TIP_SPEED_M_S:
                        continue
                    if best is None or p["shaft_power_w"] < best[0]["shaft_power_w"]:
                        best = (p, z, n, g, d)
        p, z, n, g, d = best
        entry = {"935_fitted_rotor": summary(b) if b else None,
                 "935_fitted_rotor_loss_x1.5": summary(b15) if b15 else None,
                 "new_rotor": {"blade_count": z, "design_speed_rpm": n, "design_flow_gain": g, **summary(p)}}
        if b:
            ratio = b["shaft_power_w"] / p["shaft_power_w"]
            entry["comparison"] = {"power_saving_at_duty": round(1 - 1 / ratio, 4),
                                   "flow_gain_at_equal_power_fan_laws": round(ratio ** (1 / 3) - 1, 4),
                                   "speed_ratio_new_to_935": round(p["speed_rpm"] / b["speed_rpm"], 4)}
        report[name] = entry
        if name == "rotor_and_stator":
            report["chosen_design"] = {"config": name, "blade_count": z, "design_speed_rpm": n, "design_flow_gain": g,
                                       "sections": d["sections"]}
    return report


def main(mode: str, out: str) -> int:
    rep = study()
    if mode == "sections":
        rep = {"chosen_design": rep["chosen_design"], "envelope": rep["envelope"]}
    Path(out).write_text(json.dumps(rep, indent=1) + "\n")
    for k in ("rotor_only", "rotor_and_stator"):
        if k in rep:
            print(k, json.dumps(rep[k]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
