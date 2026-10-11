#!/usr/bin/env python3
"""Writes source/bionic.json for the bionic (load-path) manifold.

The flow passages are copied from the exhaust_manifold_3into1 generator
(parts/picogk-catalog/exhaust/ExhaustManifold.cs) as the same lattice beams:
round-capped beams of constant radius are exactly capsules, so the "void"
list cuts the passages, bolt holes and nut clearances at their exact size.
The tapered collector entry beam is approximated by inscribed capsules.
Parameters are read from source/picogk.json (legacy values kept there).
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
P = {k: v["value"] for k, v in json.loads((HERE / "picogk.json").read_text(encoding="utf-8"))["parameters"].items()}


def r3(v):
    return [round(float(x), 3) for x in v]


def bezier(a, b, c, n):
    t = np.linspace(0, 1, n + 1)[:, None]
    return (1 - t) ** 2 * a + 2 * (1 - t) * t * b + t ** 2 * c


def chain(pts, r, note):
    return [{"type": "capsule", "a": r3(pts[i]), "b": r3(pts[i + 1]), "r": r, "basis": "assumption", "note": note}
            for i in range(len(pts) - 1)]


rpi, rci, w = P["primary_inner_diameter_mm"] / 2, P["collector_inner_diameter_mm"] / 2, P["wall_mm"]
sx, sy, ex, ey = P["port_spacing_x_mm"], P["port_offset_y_mm"], P["merge_spacing_x_mm"], P["merge_offset_y_mm"]
zm, zc, Lt, zb = P["merge_z_mm"], P["collector_start_z_mm"], P["total_length_mm"], P["bend_control_z_mm"]
fT, fRim = P["head_flange_thickness_mm"], P["head_flange_rim_mm"]
boltR, bossR, nutR = P["bolt_hole_diameter_mm"] / 2, P["bolt_boss_radius_mm"], P["nut_clearance_radius_mm"]
oT, oR, oB = P["outlet_flange_thickness_mm"], P["outlet_flange_radius_mm"], P["outlet_bolt_offset_mm"]
rpo = rpi + w
ports = np.array([[-sx, -sy], [0, 0], [sx, sy]])
ends = np.array([[-ex, -ey], [0, 0], [ex, ey]])
bolts = [(ports[0] + ports[1]) / 2, (ports[1] + ports[2]) / 2]

void = []
for i in range(3):
    a, b, c = np.r_[ports[i], 0], np.r_[ports[i], zb], np.r_[ends[i], zm]
    path = np.vstack([np.r_[ports[i], -3.0], bezier(a, b, c, 48)])
    void += chain(path, rpi, f"primary {i + 1} passage, {2 * rpi:g} mm, same beams as ExhaustManifold.cs")
# collector entry cone (zc+5 -> zm, r 0.7 rpi -> rci): inscribed capsule steps
zs = np.linspace(zc + 5, zm, 11)
for k in range(10):
    r = 0.7 * rpi + (rci - 0.7 * rpi) * (zs[k] - zs[0]) / (zs[-1] - zs[0])
    void.append({"type": "capsule", "a": [0, 0, round(zs[k], 3)], "b": [0, 0, round(zs[k + 1], 3)], "r": round(r, 3),
                 "basis": "assumption", "note": "collector entry cone, inscribed step"})
void.append({"type": "capsule", "a": [0, 0, zm], "b": [0, 0, Lt + 3], "r": rci, "basis": "assumption",
             "note": f"collector passage {2 * rci:g} mm"})
for p in bolts:
    void.append({"type": "cyl", "a": r3([*p, -2]), "b": r3([*p, fT + 1]), "r": boltR, "basis": "assumption", "note": "head flange bolt hole (M8 clearance assumed)"})
    void.append({"type": "capsule", "a": r3([*p, fT]), "b": r3([*p, fT + 18]), "r": nutR, "basis": "assumption", "note": "nut / socket clearance above the head flange bolt"})
for x in (-oB, oB):
    void.append({"type": "cyl", "a": [x, 0, Lt - oT - 1], "b": [x, 0, Lt + 2], "r": boltR, "basis": "assumption", "note": "outlet flange bolt hole"})
    void.append({"type": "capsule", "a": [x, 0, Lt - oT - 30], "b": [x, 0, Lt - oT], "r": nutR, "basis": "assumption", "note": "nut / socket clearance under the outlet flange bolt"})

rf = rpo + fRim
solid = [{"type": "cyl", "a": r3([*p, 0]), "b": r3([*p, fT]), "r": round(rf, 3), "basis": "assumption", "note": "head flange ring around the port (inside the legacy flange outline)"} for p in ports]
solid += [{"type": "cyl", "a": r3([*p, 0]), "b": r3([*p, fT]), "r": bossR + 3, "basis": "assumption", "note": "head flange bolt boss"} for p in bolts]
solid.append({"type": "cyl", "a": [0, 0, Lt - oT], "b": [0, 0, Lt], "r": oR, "basis": "assumption", "note": "outlet (turbine) flange disc"})
solid += [{"type": "cyl", "a": [x, 0, Lt - oT], "b": [x, 0, Lt], "r": bossR + 1, "basis": "assumption", "note": "outlet flange bolt boss"} for x in (-oB, oB)]

# Design zone hugs the flow body: a 10 mm sleeve around every primary and the
# collector (members along and between the pipes), the crotch / head-flange
# web zone between the primaries and the outlet flange gusset zone.
design = []
for i in range(3):
    a, b, c = np.r_[ports[i], 0], np.r_[ports[i], zb], np.r_[ends[i], zm]
    pts = bezier(a, b, c, 8)
    design += [{"type": "capsule", "a": r3(pts[k]), "b": r3(pts[k + 1]), "r": rpi + 10} for k in range(8)]
design[0].update({"basis": "assumption", "note": "10 mm sleeve around each primary (wall + 8.8 mm)"})
design += [
    {"type": "capsule", "a": [0, 0, zc - 10], "b": [0, 0, Lt - oT], "r": rci + 10, "basis": "assumption", "note": "10 mm sleeve around the collector"},
    {"type": "box", "min": [-70, -22, 0], "max": [70, 22, 70], "basis": "assumption", "note": "web zone between the primaries above the head flange"},
    {"type": "box", "min": [-52, -20, 170], "max": [52, 20, Lt], "basis": "assumption", "note": "outlet flange gusset zone (between the two outlet bolts)"},
]
supports = [{"type": "cyl", "a": r3([*p, -1]), "b": r3([*p, 1.5]), "r": round(rf, 3), "basis": "assumption", "note": "head flange face clamped to the cylinder head"} for p in ports]
supports += [{"type": "cyl", "a": r3([*p, -1]), "b": r3([*p, 1.5]), "r": bossR + 3, "basis": "assumption", "note": "head flange bolt"} for p in bolts]
outlet_face = [{"type": "cyl", "a": [0, 0, Lt - 3.5], "b": [0, 0, Lt + 1.5], "r": oR}]

spec = {
    "part_id": "993-ENG-EXHAUST-MANIFOLD-IN625-F0-0001",
    "method": "3D SIMP topology optimization (parts/picogk-catalog/bionic/topopt.py) of the structure around the exact flow passages, then PicoGK smoothing; legacy flow body (out/<ID>-functional.stl) fused as shaping.base_stl, passages / bolt holes / nut clearances cut last at exact size",
    "basis_note": "Interfaces and loads are NOT measured. Port, merge and flange positions are the F0 hypotheses of source/picogk.json; the turbo load share is an assumption, the axial case uses the engineering screen's collector pressure force. Thermal expansion is not a SIMP load: it is addressed only by keeping the single support at the head flange (outlet free). The shape is a load-path concept.",
    "generator": "bionic_regions.py (this folder) writes this file from source/picogk.json",
    "optimization": {
        "element_mm": 3.0,
        "grid_min": [-75, -36, 0],
        "grid_max": [75, 36, 216],
        "design": design,
        "solid": solid,
        "void": void,
        "supports": supports,
        "load_cases": [
            {"name": "turbo_x", "basis": "assumption", "note": "turbocharger mass share 4 kg x 10 g on the outlet flange, along the port row (no published value)",
             "loads": [{"region": outlet_face, "force_N": [400, 0, 0]}]},
            {"name": "turbo_y", "basis": "assumption", "note": "same 400 N across the port row",
             "loads": [{"region": outlet_face, "force_N": [0, 400, 0]}]},
            {"name": "axial", "basis": "assumption", "note": "collector_pressure_force_n 123 N of evidence/engineering-screen.json (50 kPa screen) plus turbo inertia, rounded to 250 N along the collector axis",
             "loads": [{"region": outlet_face, "force_N": [0, 0, 250]}]},
        ],
        "volume_fraction": 0.16,
        "filter_radius_mm": 7.5,
        "iterations": 45,
    },
    "shaping": {
        "smooth_mm": 1.5,
        "blend_mm": 0.3,
        "blend_note": "PicoGK Smoothen offsets inward first: the blend must stay below half the 1.2 mm legacy tube wall",
        "base_stl": "parts/picogk-catalog/out/993-ENG-EXHAUST-MANIFOLD-IN625-F0-0001-functional.stl",
        "lattice_grey": False,
    },
}
(HERE / "bionic.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8", newline="\n")
print(f"{len(void)} voids, {len(solid)} solids")
