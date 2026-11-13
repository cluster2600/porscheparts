"""CAD of the 993 flat-fan rotor F0 (build123d / OCCT).

Hub and interfaces: the fitted 935 hub (twins/935-horizontal-fan-cad-twin)
with its drive dogs and fastener bosses, so the rotor fits a 935-type
right-angle drive. The hub section that the scanner could not see inside
(between the inner cone, the rolled lip and the outer drum) is designed as a
shell of WALL_MM, a design choice rather than a copy.

Blades: the velocity-triangle design chosen by flat_fan_993_f0.py (read from
evidence/flat-fan-993-f0.json): circular-arc camber line between the inlet
and outlet metal angles, NACA 4-digit thickness, stacked on the 935 blade's
mid-chord line so the new blades occupy the same axial band. The leading
edge is at low z and the rotor turns towards -s, as in the twin.

Usage: build_flat_fan_993.py OUT_DIR   (writes private STEP/STL + a JSON summary)
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "twins/935-horizontal-fan-cad-twin/source"))
import build_cad as twin  # noqa: E402
from build123d import Axis, Cylinder, Face, Location, Polyline, Shell, Solid, Spline, Wire, export_step, export_stl, revolve  # noqa: E402
from OCP.ShapeFix import ShapeFix_Solid  # noqa: E402

PART = Path(__file__).resolve().parents[1]
EVIDENCE = PART / "evidence/flat-fan-993-f0.json"
WALL_MM = 2.5
HOLLOW_FROM_R_MM = 62.0
WE43_DENSITY = 1840.0
TE_THICKNESS_MM = 0.5
SIDE_POINTS = 48


def design_sections() -> tuple[list[dict], dict]:
    ev = json.loads(EVIDENCE.read_text())
    return ev["chosen_design"]["sections"], ev["envelope"]


def interp(rr, vals, r):
    return float(np.interp(r, rr, vals))


def stacking(blade935: dict, r: float) -> np.ndarray:
    poly = blade935["radial_polynomials"]
    le = np.array([np.polyval(poly["le_sz"][j], r) for j in range(2)])
    te = np.array([np.polyval(poly["te_sz"][j], r) for j in range(2)])
    return 0.5 * (le + te)


def section_sz(sec: dict, centre: np.ndarray) -> np.ndarray:
    c, t = sec["chord_mm"], sec["thickness_mm"]
    th1 = math.radians(90.0 - sec["inlet_metal_deg"])
    th2 = math.radians(90.0 - sec["outlet_metal_deg"])
    n = 400
    u = np.linspace(0, 1, n)
    ang = th1 + (th2 - th1) * u
    pts = np.c_[np.cumsum(np.cos(ang)), np.cumsum(np.sin(ang))]
    pts -= pts[0]
    pts *= c / np.linalg.norm(pts[-1])
    tang = np.gradient(pts, axis=0)
    tang /= np.linalg.norm(tang, axis=1)[:, None]
    nrm = np.c_[-tang[:, 1], tang[:, 0]]
    xs = 0.5 * (1 - np.cos(np.linspace(0, math.pi, SIDE_POINTS)))
    idx = np.clip((xs * (n - 1)).round().astype(int), 0, n - 1)
    tc = t / c
    yt = 5 * tc * c * (0.2969 * np.sqrt(xs) - 0.1260 * xs - 0.3516 * xs ** 2 + 0.2843 * xs ** 3 - 0.1015 * xs ** 4) + 0.5 * TE_THICKNESS_MM * xs
    top = pts[idx] + nrm[idx] * yt[:, None]
    bot = pts[idx] - nrm[idx] * yt[:, None]
    ring = np.r_[top, bot[::-1][1:-1]]
    return ring - pts[n // 2] + centre


def blade_solid(sections: list[dict], blade935: dict, tip: float):
    rr = np.array([s["radius_mm"] for s in sections])
    radii = np.arange(twin.ROOT_R, tip + twin.TIP_OVERSHOOT + 1e-6, twin.SECTION_STEP_MM)
    wires = []
    for r in radii:
        sec = {k: interp(rr, [s[k] for s in sections], r) for k in ("chord_mm", "thickness_mm", "inlet_metal_deg", "outlet_metal_deg")}
        ring = section_sz(sec, stacking(blade935, r))
        pts = [(float(r * math.cos(a / r)), float(r * math.sin(a / r)), float(z)) for a, z in ring]
        wires.append(Wire([Spline(*pts, periodic=True)]))
    side = Solid.make_loft(wires, ruled=False).faces()[0]
    fix = ShapeFix_Solid(Solid(Shell([side, Face.make_surface(wires[0]), Face.make_surface(wires[-1])])).wrapped)
    fix.Perform()
    body = Solid(fix.Solid())
    return body & Cylinder(tip, 400, align=None).moved(Location((0, 0, -200)))


def hollow_core():
    prof = json.loads((twin.PARAMS / "hub-profile.json").read_text())["profile_rz_mm"]
    poly = Polygon(prof).buffer(0)
    inner = poly.buffer(-WALL_MM, join_style=2)
    cut = Polygon([(HOLLOW_FROM_R_MM, -100), (200, -100), (200, 100), (HOLLOW_FROM_R_MM, 100)])
    core = inner.intersection(cut)
    if core.geom_type != "Polygon":
        core = max(core.geoms, key=lambda g: g.area)
    core = core.simplify(0.02)
    pts = [(float(r), 0.0, float(z)) for r, z in list(core.exterior.coords)[:-1]]
    return revolve(Face(Polyline(*pts, close=True)), Axis.Z, 360), float(core.area)


def main(out_dir: str) -> int:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sections, env = design_sections()
    blade935 = json.loads((twin.PARAMS / "blade.json").read_text())
    tip = env["tip_radius_mm"]
    hub = twin.hub_solid()
    core, core_area = hollow_core()
    adds, cuts = twin.feature_solids()
    one = blade_solid(sections, blade935, tip)
    blades = [one.rotate(Axis.Z, k * 360.0 / len(blade935["blade_angular_offsets_deg"])) for k in range(9)]
    rotor = twin.union_all(hub, adds, blades)
    rotor = rotor.cut(core, *cuts)
    if len(rotor.solids()) == 1:
        rotor = Solid(rotor.solids()[0].wrapped)
    rotor = twin.heal(rotor)
    step, stl = out / "flat-fan-993-f0.step", out / "flat-fan-993-f0.stl"
    export_step(rotor, str(step))
    export_stl(rotor, str(stl), tolerance=0.02, angular_tolerance=0.1)
    vol, open_edges = twin.mesh_volume(stl)
    bb = rotor.bounding_box()
    summary = {"valid": bool(rotor.is_valid), "solids": len(rotor.solids()), "volume_mm3": round(vol, 1),
               "volume_basis": "tessellation (0.02 mm)", "tessellation_open_edges": open_edges,
               "mass_we43_kg": round(vol * 1e-9 * WE43_DENSITY, 3),
               "mass_alsi10mg_kg": round(vol * 1e-9 * 2670.0, 3),
               "hollow_core_section_mm2": round(core_area, 1), "wall_mm": WALL_MM,
               "bbox_mm": [round(x, 2) for x in tuple(bb.min) + tuple(bb.max)]}
    (out / "flat-fan-993-f0.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
