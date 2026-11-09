"""Build the 935 rotor CAD from the fitted parameters (build123d / OCCT).

Hub: revolve of params/hub-profile.json (closed outer loop; interior per
hypothesis H-HUB-INTERIOR), plus the local features of params/features.json
as simple solids: cylindrical bosses (heads, tails, step bosses) and the two
drive dogs extruded from their traced outlines, with their observed holes
cut through the dog only (depth not observed). Blades: one blade from params/blade.json,
section parameters smoothed across radius by their fitted polynomials, each
section mapped back from (s, z) onto its cylinder, lofted from just inside
the drum to beyond the tip, then cut by the fitted tip cylinder. Nine copies
are placed either at the nominal 40 degree pitch ("nominal", design intent)
or at the specimen's measured angular offsets ("specimen", for scoring).

Usage: build_cad.py {nominal|specimen} OUT_DIR
Writes OUT_DIR/rotor-<variant>.step and .stl (private) and prints a JSON
summary (volume, area, bounding box).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from OCP.ShapeFix import ShapeFix_Shape, ShapeFix_Solid
from build123d import (Axis, Cylinder, Face, Location, Polyline, Shell, Solid, Spline, Wire,
                       export_step, export_stl, extrude, revolve)

from fan_common import BLADE_COUNT, PARAMS

ROOT_R = 86.5          # inside the drum (r 88.4-89.3): the root cap is buried in the hub
TIP_OVERSHOOT = 6.0    # the tip cap lies well outside the kept region before the tip cut
SECTION_STEP_MM = 2.5  # uniform spacing: a global spline loft oscillates between uneven sections
SIDE_POINTS = 48
FUZZY_MM = 1e-3


def hub_solid():
    prof = json.loads((PARAMS / "hub-profile.json").read_text())["profile_rz_mm"]
    pts = [(float(r), 0.0, float(z)) for r, z in prof]
    wire = Polyline(*pts, close=True)
    face = Face(Wire(wire.edges()) if hasattr(wire, "edges") else wire)
    return revolve(face, Axis.Z, 360)


def smoothed_section(blade: dict, r: float) -> dict:
    poly = blade["radial_polynomials"]
    le = np.array([np.polyval(poly["le_sz"][j], r) for j in range(2)])
    te = np.array([np.polyval(poly["te_sz"][j], r) for j in range(2)])
    up = np.array([np.polyval(c, r) for c in poly["upper"]])
    lo = np.array([np.polyval(c, r) for c in poly["lower"]])
    mid = 0.5 * (up + lo)
    up, lo = np.maximum(up, mid + 0.05), np.minimum(lo, mid - 0.05)
    return {"le": le, "te": te, "upper": up, "lower": lo}


def section_points_3d(blade: dict, r: float) -> list[tuple[float, float, float]]:
    x_tab = np.asarray(blade["chord_stations_x"])
    s = smoothed_section(blade, r)
    le, te = s["le"], s["te"]
    chord = float(np.linalg.norm(te - le))
    cd = (te - le) / chord
    cn = np.array([-cd[1], cd[0]])
    # Round nose and tail: half-thickness circles near each end.
    xs = 0.5 * (1 - np.cos(np.linspace(0, math.pi, SIDE_POINTS)))
    up = np.interp(xs, x_tab, s["upper"])
    lo = np.interp(xs, x_tab, s["lower"])
    for end, xe in ((0, 0.0), (1, 1.0)):
        k = 3 if end == 0 else -4
        half = 0.5 * (s["upper"][k] - s["lower"][k])
        cen = 0.5 * (s["upper"][k] + s["lower"][k])
        span = abs(x_tab[k] - xe) * chord
        dx = np.abs(xs - xe) * chord
        near = dx < span
        shape = np.sqrt(np.clip(1 - ((span - dx[near]) / span) ** 2, 0, 1))
        up[near] = cen + half * shape
        lo[near] = cen - half * shape
    top = le + np.outer(xs * chord, cd) + np.outer(up, cn)
    bot = le + np.outer(xs * chord, cd) + np.outer(lo, cn)
    ring = np.r_[top, bot[::-1][1:-1]]
    th = ring[:, 0] / r
    return [(float(r * math.cos(t)), float(r * math.sin(t)), float(zz)) for t, zz in zip(th, ring[:, 1])]


def blade_solid(blade: dict):
    tip = blade["tip_radius_mm"]
    radii = np.arange(ROOT_R, tip + TIP_OVERSHOOT + 1e-6, SECTION_STEP_MM)
    wires = [Wire([Spline(*section_points_3d(blade, float(r)), periodic=True)]) for r in radii]
    # OCC cannot cap a loft whose end sections lie on cylinders (non-planar),
    # so the side is lofted alone and capped with filled surfaces.
    side = Solid.make_loft(wires, ruled=False).faces()[0]
    fix = ShapeFix_Solid(Solid(Shell([side, Face.make_surface(wires[0]), Face.make_surface(wires[-1])])).wrapped)
    fix.Perform()
    body = Solid(fix.Solid())
    keep = Cylinder(tip, 400, align=None).moved(Location((0, 0, -200)))
    return body & keep


def boss(x: float, y: float, z0: float, d: float, h: float, up: bool):
    cyl = Cylinder(d / 2, h, align=None)
    zb = z0 - 0.3 if up else z0 - h + 0.3
    return cyl.moved(Location((x, y, zb))) if up else cyl.moved(Location((x, y, zb)))


def feature_solids():
    feats = json.loads((PARAMS / "features.json").read_text())["features"]
    adds, cuts = [], []
    for key, up in (("front_heads", True), ("back_tails", False), ("step_bosses", True)):
        grp = feats[key]
        for it in grp["items"]:
            h = min(it["height_mm"], 8.0) + 0.3
            x, y = it["centre_xy_mm"]
            adds.append(boss(x, y, grp["base_z_mm"], it["diameter_mm"], h, up))
    dogs = feats["drive_dogs"]
    for dog in dogs["items"]:
        pts = [(float(a), float(b), 0.0) for a, b in dog["outline_xy_mm"]]
        face = Face(Polyline(*pts, close=True))
        height = dogs["base_z_mm"] - dog["face_z_mm"] + 0.3
        body = extrude(face, amount=height, dir=(0, 0, 1)).moved(Location((0, 0, dog["face_z_mm"])))
        adds.append(body)
        for hole in dog["holes"]:
            x, y = hole["centre_xy_mm"]
            cuts.append(Cylinder(hole["diameter_mm"] / 2, height + 0.2, align=None).moved(Location((x, y, dog["face_z_mm"] - 0.1))))
    return adds, cuts


def stage(msg: str) -> None:
    import resource
    import time
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
    print(f"[{time.strftime('%H:%M:%S')}] {msg} (peak RSS {rss:.1f} GB)", file=sys.stderr, flush=True)


def mesh_volume(stl: Path) -> tuple[float, int]:
    """Volume of the tessellation and its count of open edges. Open edges
    appear only as T-junction cracks between adjacent tessellated faces (seen
    on the cylindrical tip faces); they do not bias the enclosed volume."""
    import trimesh
    m = trimesh.load(str(stl))
    open_edges = len(trimesh.grouping.group_rows(m.edges_sorted, require_count=1))
    if open_edges > 0.01 * len(m.edges_unique):
        raise SystemExit(f"{stl}: {open_edges} open edges, too many for a volume")
    return float(m.volume), open_edges


def union_all(hub, adds, blades):
    """Features in one fuse, then the blades one at a time. A single fuse of
    everything needs more than 9 GB with 22-section blades; sequential unions
    stay near 1-2 GB. Each step must stay valid and must not lose volume
    (the failure seen with the earlier self-intersecting hub profile)."""
    rotor = hub.fuse(*adds)
    for k, blade in enumerate(blades):
        before = rotor.volume
        nxt = rotor.fuse(blade)
        if not nxt.is_valid or nxt.volume < before:
            nxt = rotor.fuse(blade, tol=FUZZY_MM)
        if not nxt.is_valid or nxt.volume < before:
            raise SystemExit(f"union with blade {k} failed (valid={nxt.is_valid})")
        rotor = nxt
        stage(f"blade {k} united")
    return rotor


def heal(shape):
    """Run OCCT's shape healer when the boolean result is flagged invalid."""
    if shape.is_valid:
        return shape
    fixer = ShapeFix_Shape(shape.wrapped)
    fixer.Perform()
    fixed = fixer.Shape()
    solids = Solid(fixed) if fixed.ShapeType().name == "TopAbs_SOLID" else None
    return solids if solids is not None and solids.is_valid else shape


def main(variant: str, out_dir: str) -> int:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    blade = json.loads((PARAMS / "blade.json").read_text())
    offsets = blade["blade_angular_offsets_deg"] if variant == "specimen" else [0.0] * BLADE_COUNT
    hub = hub_solid()
    one = blade_solid(blade)
    stage("hub and blade built")
    adds, cuts = feature_solids()
    blades = [one.rotate(Axis.Z, k * 360.0 / BLADE_COUNT + offsets[k]) for k in range(BLADE_COUNT)]
    rotor = union_all(hub, adds, blades)
    stage("fused")
    if cuts:
        rotor = rotor.cut(*cuts)
    rotor = Solid(rotor.solids()[0].wrapped) if len(rotor.solids()) == 1 else rotor
    rotor = heal(rotor)
    stage(f"cut and healed, valid={rotor.is_valid}")
    step = out / f"rotor-{variant}.step"
    stl = out / f"rotor-{variant}.stl"
    export_step(rotor, str(step))
    stage("STEP written")
    export_stl(rotor, str(stl), tolerance=0.02, angular_tolerance=0.1)
    stage("STL written")
    bb = rotor.bounding_box()
    summary = {"variant": variant, "valid": bool(rotor.is_valid), "solids": len(rotor.solids()),
               "volume_mm3": round(mesh_volume(stl)[0], 1), "tessellation_open_edges": mesh_volume(stl)[1],
               "volume_basis": "tessellation (0.02 mm); OCCT's volume property reads about 3 % high on the lofted blades",
               "area_mm2": round(rotor.area, 1),
               "bbox_min": [round(x, 3) for x in tuple(bb.min)], "bbox_max": [round(x, 3) for x in tuple(bb.max)]}
    (out / f"rotor-{variant}.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
