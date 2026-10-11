#!/usr/bin/env python3
"""Writes source/bionic.json for the bionic (load-path) turbo oil return line.

Centreline, bore, flanges, bolt holes and the mid-span mount come from the
turbo_oil_return_line generator (parts/picogk-catalog/exhaust/TurboOilReturnLine.cs)
and source/picogk.json: the same Catmull-Rom centreline, the bore as the same
round-capped beams (= capsules, exact). The legacy flat support tab is not
used: shaping.base_stl is the legacy tube + flanges regenerated with
clip_tab_thickness_mm = 0 (out/<ID>-notab.stl); the mount is an exact boss at
the legacy tab hole and the bracket to it is grown by the optimizer.
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
P = {k: v["value"] for k, v in json.loads((HERE / "picogk.json").read_text(encoding="utf-8"))["parameters"].items()}
ro = P["tube_outer_diameter_mm"] / 2
ri = ro - P["tube_wall_mm"]
fR, fT = P["flange_diameter_mm"] / 2, P["flange_thickness_mm"]
bc, bR, lobeR = P["flange_bolt_centres_mm"] / 2, P["flange_bore_diameter_mm"] / 2, P["flange_lobe_radius_mm"]
tabT, tabL, tabTh, tabHole = P["clip_tab_t"], P["clip_tab_length_mm"], P["clip_tab_thickness_mm"], P["clip_tab_hole_diameter_mm"] / 2


def r3(v):
    return [round(float(x), 3) for x in v]


def catmull_rom(p, t0, t1, per_span):
    q = [p[0] - t0, *p, p[-1] + t1]
    pts = []
    for s in range(1, len(q) - 2):
        n = per_span + (1 if s + 3 == len(q) else 0)
        for i in range(n):
            t = i / per_span
            t2, t3 = t * t, t * t * t
            pts.append(0.5 * (2 * q[s] + (q[s + 1] - q[s - 1]) * t + (2 * q[s - 1] - 5 * q[s] + 4 * q[s + 1] - q[s + 2]) * t2
                              + (-q[s - 1] + 3 * q[s] - 3 * q[s + 1] + q[s + 2]) * t3))
    return np.array(pts)


cps = [np.array([P[f"cp{i}_x_mm"], P[f"cp{i}_y_mm"], P[f"cp{i}_z_mm"]], float) for i in range(6)]
up = np.array([0, 0, 24.0])
path = catmull_rom(cps, up, up, 16)
a, b = path[0], path[-1]
k = int(round(tabT * (len(path) - 1)))
pc = path[k]
d = path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)]
d /= np.linalg.norm(d)
side = np.cross(d, [0, 0, 1.0])
side /= np.linalg.norm(side)
if side[1] < 0:
    side = -side
tab_end = pc + side * tabL
nrm = np.cross(d, side)
nrm /= np.linalg.norm(nrm)


def dist_to_path(p):
    return float(np.min(np.linalg.norm(path - p, axis=1)))


void = []
bore = np.vstack([a - [0, 0, fT], path, b + [0, 0, fT]])
void += [{"type": "capsule", "a": r3(bore[i]), "b": r3(bore[i + 1]), "r": round(ri, 3), "basis": "assumption",
          "note": "oil bore, same beams as TurboOilReturnLine.cs"} for i in range(len(bore) - 1)]
solid = []
for c, sgn, name in ((a, 1, "turbo-side"), (b, -1, "engine-side")):
    solid.append({"type": "cyl", "a": r3(c - [0, 0, fT / 2]), "b": r3(c + [0, 0, fT / 2]), "r": fR, "basis": "assumption", "note": f"{name} flange disc"})
    for dx in (-bc, bc):
        hole = c + [dx, 0, 0]
        solid.append({"type": "cyl", "a": r3(hole - [0, 0, fT / 2]), "b": r3(hole + [0, 0, fT / 2]), "r": lobeR, "basis": "assumption", "note": f"{name} flange bolt lobe"})
        void.append({"type": "cyl", "a": r3(hole - [0, 0, fT]), "b": r3(hole + [0, 0, fT]), "r": bR, "basis": "assumption", "note": f"{name} flange bolt hole"})
        # bolt-head seat and socket path, as tall as the tube allows (seat must not touch the tube)
        top = fT / 2 + 6
        while top < 25 and min(dist_to_path(hole + [0, 0, sgn * z]) for z in np.linspace(fT / 2, top + 1, 8)) - ro > bR + 1.5 + 0.3:
            top += 1
        void.append({"type": "cyl", "a": r3(hole + [0, 0, sgn * fT / 2]), "b": r3(hole + [0, 0, sgn * top]), "r": bR + 1.5, "basis": "assumption",
                     "note": f"{name} bolt-head seat and socket path ({top:g} mm from the flange mid-plane, clear of the tube)"})
solid.append({"type": "cyl", "a": r3(tab_end - nrm * tabTh / 2), "b": r3(tab_end + nrm * tabTh / 2), "r": 6.0, "basis": "assumption",
              "note": "mid-span mount boss at the legacy tab hole (clip_tab_t, clip_tab_length_mm, thickness clip_tab_thickness_mm)"})
void.append({"type": "cyl", "a": r3(tab_end - nrm * (tabTh + 1)), "b": r3(tab_end + nrm * (tabTh + 1)), "r": tabHole, "basis": "assumption", "note": "mount hole (M5 clearance assumed)"})
void.append({"type": "cyl", "a": r3(tab_end + nrm * tabTh / 2), "b": r3(tab_end + nrm * (tabTh / 2 + 10)), "r": 5.0, "basis": "assumption", "note": "screw-head side of the mount kept free"})

ctl = path[::8] if (len(path) - 1) % 8 == 0 else np.vstack([path[::8], path[-1]])
design = [{"type": "capsule", "a": r3(ctl[i]), "b": r3(ctl[i + 1]), "r": ro + 8, "basis": "assumption", "note": "8 mm zone around the tube"} for i in range(len(ctl) - 1)]
design += [
    {"type": "cyl", "a": r3(a - [0, 0, fT / 2]), "b": r3(a + [0, 0, 22]), "r": fR + 2, "basis": "assumption", "note": "turbo-side flange gusset zone"},
    {"type": "cyl", "a": r3(b - [0, 0, 22]), "b": r3(b + [0, 0, fT / 2]), "r": fR + 2, "basis": "assumption", "note": "engine-side flange gusset zone"},
    {"type": "capsule", "a": r3(pc), "b": r3(tab_end), "r": 9.0, "basis": "assumption", "note": "mount bracket zone"},
]
supports = []
for c, name in ((a, "turbo-side"), (b, "engine-side")):
    for dx in (-bc, bc):
        hole = c + [dx, 0, 0]
        supports.append({"type": "cyl", "a": r3(hole - [0, 0, fT / 2 + 0.5]), "b": r3(hole + [0, 0, fT / 2 + 0.5]), "r": lobeR, "basis": "assumption", "note": f"{name} flange bolted"})
supports.append({"type": "cyl", "a": r3(tab_end - nrm * (tabTh / 2 + 0.5)), "b": r3(tab_end + nrm * (tabTh / 2 + 0.5)), "r": 6.0, "basis": "assumption", "note": "mid-span mount screwed to the engine"})
q1, q3 = path[int(0.25 * (len(path) - 1))], path[int(0.75 * (len(path) - 1))]
spots = [{"type": "sphere", "c": r3(q1), "r": ro + 1}, {"type": "sphere", "c": r3(q3), "r": ro + 1}]
spec = {
    "part_id": "993-ENG-TURBO-OIL-RETURN-LINE-IN625-F0-0001",
    "method": "3D SIMP topology optimization (parts/picogk-catalog/bionic/topopt.py) of flange gussets and the mid-span mount bracket around the exact oil bore, then PicoGK smoothing; legacy tube + flanges without the flat tab (out/<ID>-notab.stl) fused as shaping.base_stl, bore and holes cut last",
    "basis_note": "Interfaces and loads are NOT measured. Centreline, flanges and mount position are F0 hypotheses of source/picogk.json; the 100 N transverse force is the engineering screen's synthetic transverse_center_force_n, applied split over the two quarter spans because the mount sits at mid-span. Thermal growth between turbo and engine (the screen's failing case) is not a SIMP load and is not addressed by this layout.",
    "generator": "bionic_regions.py (this folder) writes this file from source/picogk.json",
    "optimization": {
        "element_mm": 1.8,
        "grid_min": r3(np.floor(np.min(path, 0) - [fR + 3, fR + 3, fT + 1])),
        "grid_max": r3(np.ceil(np.max(path, 0) + [fR + 3, fR + 3, fT + 1])),
        "design": design,
        "solid": solid,
        "void": void,
        "supports": supports,
        "load_cases": [
            {"name": "transverse_y", "basis": "assumption", "note": "screen transverse_center_force_n 100 N (evidence/engineering-screen.json), 50 N at each quarter span, along y",
             "loads": [{"region": [s], "force_N": [0, 50, 0]} for s in spots]},
            {"name": "transverse_z", "basis": "assumption", "note": "same 100 N along z (vertical vibration)",
             "loads": [{"region": [s], "force_N": [0, 0, -50]} for s in spots]},
            {"name": "along_x", "basis": "assumption", "note": "same 100 N along x (no published value)",
             "loads": [{"region": [s], "force_N": [50, 0, 0]} for s in spots]},
        ],
        "volume_fraction": 0.15,
        "filter_radius_mm": 4.5,
        "iterations": 45,
    },
    "shaping": {
        "smooth_mm": 1.8,
        "blend_mm": 0.35,
        "blend_note": "PicoGK Smoothen offsets inward first: the blend stays below half the 1.2 mm tube wall",
        "base_stl": "parts/picogk-catalog/out/993-ENG-TURBO-OIL-RETURN-LINE-IN625-F0-0001-notab.stl",
        "lattice_grey": False,
    },
}
(HERE / "bionic.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8", newline="\n")
print(f"path {len(path)} pts, tab {r3(pc)} -> {r3(tab_end)} nrm {r3(nrm)}; {len(void)} voids, {len(solid)} solids")
