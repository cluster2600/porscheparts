#!/usr/bin/env python3
"""Writes source/bionic.json for the bionic (load-path) three-runner intake.

Bores, bellmouths, bolt holes and boss positions come from the
three_runner_intake generator (parts/picogk-catalog/exhaust/ThreeRunnerIntake.cs)
and source/picogk.json. A runner bore is a stack of horizontal circles whose
centre moves along the splayed axis: it is cut as a stack of short vertical
cylinders, each inscribed in the true bore (step 2 mm, 0.25 mm in the
bellmouth), so the cut never enlarges the legacy passage.
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
P = {k: v["value"] for k, v in json.loads((HERE / "picogk.json").read_text(encoding="utf-8"))["parameters"].items()}
rt, rb, Hh = P["top_bore_diameter_mm"] / 2, P["bottom_bore_diameter_mm"] / 2, P["height_mm"]
w, pl, pu, oy = P["runner_wall_mm"], P["lower_pitch_mm"], P["upper_pitch_mm"], P["upper_offset_y_mm"]
fx, fy, fT = P["flange_x_mm"] / 2, P["flange_y_mm"] / 2, P["flange_thickness_mm"]
bmR, bmA = P["bellmouth_radial_mm"], P["bellmouth_axial_mm"]
boltR, bossR, bossH = P["bolt_hole_diameter_mm"] / 2, P["bolt_boss_radius_mm"], P["bolt_boss_height_mm"]


def r3(v):
    return [round(float(x), 3) for x in v]


def ctr(i, z):
    t, k = z / Hh, i - 1
    return np.array([k * (pl + (pu - pl) * t), oy * t])


def rbore(z):
    r = rb + (rt - rb) * min(max(z / Hh, 0), 1)
    z0 = Hh - bmA
    if z > z0:
        u = min(max((z - z0) / bmA, 0), 1)
        r += bmR * (1 - np.sqrt(1 - u * u))
    return r


zs = list(np.arange(-2, Hh - bmA, 2.0)) + list(np.arange(Hh - bmA, Hh + 2.001, 0.25))
void = []
for i in range(3):
    for z0, z1 in zip(zs[:-1], zs[1:]):
        c0, c1 = ctr(i, z0), ctr(i, z1)
        r = min(rbore(z0), rbore(z1)) - np.linalg.norm(c1 - c0) / 2
        c = (c0 + c1) / 2
        void.append({"type": "cyl", "a": r3([*c, z0]), "b": r3([*c, z1]), "r": round(float(r), 3), "basis": "catalogue",
                     "note": f"runner {i + 1} bore (46/42 mm read from the catalogue), inscribed step"})

lowB = [np.array([-pl / 2, -fy + 8]), np.array([pl / 2, -fy + 8]), np.array([0, fy - 7])]
upB = [np.array([-pu / 2, fy - 6]), np.array([pu / 2, fy - 6]), np.array([0, -fy + 8])]


def runner_gap(p, z):
    """Free radius around a bolt axis before a runner outer wall."""
    return min(np.linalg.norm(p - ctr(i, z)) - rbore(z) - w for i in range(3))


solid = []
for b in lowB:
    void.append({"type": "cyl", "a": r3([*b, -1]), "b": r3([*b, fT + bossH + 15]), "r": boltR, "basis": "assumption", "note": "lower bolt hole (M6 clearance assumed) and stud path"})
    g = min(runner_gap(b, z) for z in np.linspace(fT + bossH, fT + bossH + 15, 7)) - 0.3
    if g > boltR + 1:
        void.append({"type": "cyl", "a": r3([*b, fT + bossH + 0.5]), "b": r3([*b, fT + bossH + 15]), "r": round(min(5.5, g), 2), "basis": "assumption", "note": "nut / socket clearance above the lower boss (limited by the runner wall)"})
    solid.append({"type": "cyl", "a": r3([*b, 0]), "b": r3([*b, fT + bossH]), "r": bossR, "basis": "assumption", "note": "lower bolt boss"})
for b in upB:
    void.append({"type": "cyl", "a": r3([*b, Hh - fT - bossH - 15]), "b": r3([*b, Hh + 1]), "r": boltR, "basis": "assumption", "note": "upper bolt hole (M6 clearance assumed) and stud path"})
    g = min(runner_gap(b, z) for z in np.linspace(Hh - fT - bossH - 15, Hh - fT - bossH, 7)) - 0.3
    if g > boltR + 1:
        void.append({"type": "cyl", "a": r3([*b, Hh - fT - bossH - 15]), "b": r3([*b, Hh - fT - bossH - 0.5]), "r": round(min(5.5, g), 2), "basis": "assumption", "note": "nut / socket clearance under the upper boss (limited by the runner wall)"})
    solid.append({"type": "cyl", "a": r3([*b, Hh - fT - bossH]), "b": r3([*b, Hh]), "r": bossR, "basis": "assumption", "note": "upper bolt boss"})
solid += [
    {"type": "box", "min": [-fx + 3, -fy + 3, 0], "max": [fx - 3, fy - 3, fT], "basis": "assumption", "note": "head flange plate, inset 3 mm inside the legacy rounded outline"},
    {"type": "box", "min": [-fx + 3, -fy + 3, Hh - fT], "max": [fx - 3, fy - 3, Hh], "basis": "assumption", "note": "throttle flange plate, inset 3 mm inside the legacy rounded outline"},
]
top = [{"type": "box", "min": [-fx + 3, -fy + 3, Hh - 1], "max": [fx - 3, fy - 3, Hh + 1]}]
spec = {
    "part_id": "993-ENG-THREE-RUNNER-INTAKE-ALSI10MG-F0-0001",
    "method": "3D SIMP topology optimization (parts/picogk-catalog/bionic/topopt.py) of the bracing between the exact runners, then PicoGK smoothing; legacy runner body (out/<ID>-functional.stl) fused as shaping.base_stl, bores and bolt holes cut last",
    "basis_note": "Interfaces and loads are NOT measured. Bore sizes and height are the catalogue reading of the F0, pitches, flange and bolts are F0 assumptions; the throttle-side loads are assumptions. The shape is a load-path concept.",
    "generator": "bionic_regions.py (this folder) writes this file from source/picogk.json",
    "optimization": {
        "element_mm": 3.3,
        "grid_min": [-95.7, -36.3, 0],
        "grid_max": [95.7, 36.3, 99],
        "design": [{"type": "box", "min": [-fx, -fy, 0], "max": [fx, fy, Hh], "basis": "assumption", "note": "legacy flange footprint 188 x 70 mm x catalogue height 100 mm"}],
        "solid": solid,
        "void": void,
        "supports": [{"type": "box", "min": [-fx, -fy, -1], "max": [fx, fy, 1], "basis": "assumption", "note": "head flange face clamped to the cylinder head"}],
        "load_cases": [
            {"name": "lateral", "basis": "assumption", "note": "throttle body / plenum share 1.5 kg x 20 g on the throttle flange, along the runner row (no published value)",
             "loads": [{"region": top, "force_N": [300, 0, 0]}]},
            {"name": "fore_aft", "basis": "assumption", "note": "same 300 N across the runner row",
             "loads": [{"region": top, "force_N": [0, 300, 0]}]},
            {"name": "vertical", "basis": "assumption", "note": "same 300 N toward the head; the 10 kPa screen pressure adds about 50 N on the three bores",
             "loads": [{"region": top, "force_N": [0, 0, -350]}]},
        ],
        "volume_fraction": 0.25,
        "filter_radius_mm": 8.25,
        "iterations": 45,
    },
    "shaping": {
        "smooth_mm": 3.3,
        "blend_mm": 0.6,
        "blend_note": "PicoGK Smoothen offsets inward first: the blend stays below half the 2 mm runner wall",
        "base_stl": "parts/picogk-catalog/out/993-ENG-THREE-RUNNER-INTAKE-ALSI10MG-F0-0001-functional.stl",
        "lattice_grey": False,
    },
}
(HERE / "bionic.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8", newline="\n")
print(f"{len(void)} voids, {len(solid)} solids")
