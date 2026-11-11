#!/usr/bin/env python3
"""Derive a print body from the CAD body, on its occupancy lattice.

The v2 CAD body is the twin. A body sent to a slicer needs three more things,
none of which belongs in the twin itself:

1. **no stud residue**: everything above a stud's seat inside the stud's own
   cluster radius is removed (the twin's rule stops 6 mm above the face);
2. **no enclosed void**: air that no path connects to the outside would trap
   powder, so it is filled;
3. **machining stock** on the faces and bores a machinist would finish: the
   deck and the register floor grow downward, the valve seats grow inward,
   and the guide and plug bores are printed solid.

Every amount is declared in ``params/print-body-case.json`` and is a
hypothesis: no drawing of this head exists. The result is a study object. It
is not a build file, it carries no support, and it qualifies nothing.

Usage: print_body.py BODY_OCC_DIR PARAMS_DIR OUT_OCC_DIR
       sim_surface_mc.py OUT_OCC_DIR SURFACE.stl REPORT.json 2 0.4375      (0.5 mm surface)
       print_body.py check SURFACE.stl OUT_OCC_DIR/print-body-occupancy.json SUMMARY.json
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assembly_thermal import axis_coordinates, unit  # noqa: E402

SCHEMA = "935-cad-twin-print-body/1"


def stud_envelopes(frame: dict, occupancy_summary: dict) -> list:
    """Axis, seat station and cluster radius of every accepted stud."""

    rods = [r for group in frame["rods"].values() for r in group]
    out = []
    for stud in occupancy_summary["studs"]:
        if not stud["accepted"]:
            continue
        rod = min(rods, key=lambda r: float(np.linalg.norm(np.subtract(r["point_on_axis"], stud["point_on_axis"]))))
        out.append({"origin": stud["point_on_axis"], "direction": unit(stud["axis"]).tolist(),
                    "t_seat": stud["seat_level_along_axis"],
                    "radius": stud["radius_mm"] + rod["radial_residual"]["max_mm"]})
    return out


def enclosed_air(solid: np.ndarray) -> np.ndarray:
    """Air voxels that no face-connected path joins to the boundary of the grid."""

    from scipy import ndimage

    labels, count = ndimage.label(~solid)
    outside = np.unique(np.concatenate([labels[0].ravel(), labels[-1].ravel(), labels[:, 0].ravel(),
                                        labels[:, -1].ravel(), labels[:, :, 0].ravel(), labels[:, :, -1].ravel()]))
    keep = np.ones(count + 1, dtype=bool)
    keep[outside] = False
    keep[0] = False
    return keep[labels]


def stock_below(solid: np.ndarray, z: np.ndarray, z_max: float, stock: float, pitch: float) -> np.ndarray:
    """Voxels to add under every column whose lowest solid voxel lies below ``z_max``."""

    lowest = np.argmax(solid, axis=2)
    has = solid.any(axis=2) & (z[lowest] < z_max)
    layers = int(round(stock / pitch))
    add = np.zeros_like(solid)
    k = np.arange(solid.shape[2])[None, None, :]
    add[(k >= (lowest - layers)[:, :, None]) & (k < lowest[:, :, None]) & has[:, :, None]] = True
    return add


def main(body_dir, params, out_dir) -> None:
    body_dir, params, out_dir = Path(body_dir), Path(params), Path(out_dir)
    case = json.loads((params / "print-body-case.json").read_text())
    fits = json.loads((params / "feature-fits.json").read_text())
    frame = json.loads((params / "frame.json").read_text())
    occupancy = json.loads((params / "occupancy-summary.json").read_text())
    regions = {r["id"]: r for r in fits["regions"]}
    datums = fits["group_datums"]
    grid = json.loads((body_dir / "occupancy-grid.json").read_text())
    h = grid["pitch_mm"]
    solid = np.asarray(np.load(body_dir / grid["array"], mmap_mode="r")) > 0.5
    x = grid["x0"] + h * np.arange(solid.shape[0])
    y = grid["y0"] + h * np.arange(solid.shape[1])
    z = grid["z0"] + h * np.arange(solid.shape[2])
    cell = h ** 3
    steps = []

    def apply(name, mask_of_points, add: bool, z_range=None):
        """Evaluate an analytic region slab by slab and add it to, or remove it from, the solid."""

        changed = 0
        k0 = 0 if z_range is None else max(0, int((z_range[0] - grid["z0"]) / h) - 1)
        k1 = solid.shape[2] if z_range is None else min(solid.shape[2], int((z_range[1] - grid["z0"]) / h) + 2)
        for a in range(k0, k1, 8):
            b = min(a + 8, k1)
            points = np.stack(np.meshgrid(x, y, z[a:b], indexing="ij"), axis=-1).reshape(-1, 3)
            mask = mask_of_points(points).reshape(len(x), len(y), b - a)
            slab = solid[:, :, a:b]
            before = int(slab.sum())
            slab[mask] = add
            changed += abs(int(slab.sum()) - before)
        steps.append({"step": name, "action": "added" if add else "removed", "volume_mm3": round(changed * cell, 1)})

    volume_twin = float(solid.sum()) * cell

    # 1. stud residue above each seat
    for index, stud in enumerate(stud_envelopes(frame, occupancy)):
        direction = np.asarray(stud["direction"])

        def above_seat(points, stud=stud, direction=direction):
            t, rho = axis_coordinates(points, stud["origin"], direction)
            return (t > stud["t_seat"] + case["stud_clearance_above_seat_mm"]) & (rho < stud["radius"])

        apply(f"stud residue {index:02d}", above_seat, add=False)
    stud_total = round(sum(s["volume_mm3"] for s in steps), 1)

    # 2. enclosed voids
    voids = enclosed_air(solid)
    steps.append({"step": "enclosed voids filled", "action": "added", "volume_mm3": round(float(voids.sum()) * cell, 1)})
    solid |= voids

    # 3. machining stock
    stock = case["stock"]
    add = stock_below(solid, z, stock["deck_zone_z_max_mm"], stock["deck_and_register_mm"], h)
    steps.append({"step": "stock under the deck and the register floor", "action": "added",
                  "volume_mm3": round(float((add & ~solid).sum()) * cell, 1)})
    solid |= add
    for name, datum in datums.items():
        direction = unit(datum["axis_direction"])
        if name.startswith("valve"):
            seat = regions[f"{name}_seat"]["to_group_datum"]
            cone = seat["about_datum_axis"]
            tan_a = math.tan(math.radians(abs(cone["half_angle_deg"])))
            grow = stock["valve_seat_mm"] / math.cos(math.radians(abs(cone["half_angle_deg"])))
            t_seat, r_seat = seat["station_on_datum_axis_mm"], 0.5 * cone["diameter_mm"]
            half = stock["valve_seat_band_half_length_mm"]

            def seat_stock(points, datum=datum, direction=direction, t_seat=t_seat, r_seat=r_seat, tan_a=tan_a, grow=grow, half=half):
                t, rho = axis_coordinates(points, datum["axis_point"], direction)
                surface = r_seat - tan_a * (t - t_seat)
                return (np.abs(t - t_seat) < half) & (rho <= surface) & (rho >= surface - grow)

            apply(f"stock on the seat of {name}", seat_stock, add=True)
            bore = case["guides"][name]
            radius = 0.5 * regions[bore["bore_from"]]["to_group_datum"]["about_datum_axis"]["diameter_mm"] + stock["bore_fill_margin_mm"]

            def guide_bore(points, datum=datum, direction=direction, bore=bore, radius=radius):
                t, rho = axis_coordinates(points, datum["axis_point"], direction)
                return (t >= bore["stations_mm"][0]) & (t <= bore["stations_mm"][1]) & (rho <= radius)

            apply(f"guide bore of {name} printed solid", guide_bore, add=True)
        elif name.startswith("plug"):
            fit = regions[f"{name}_thread_bore"]["fit"]
            radius = 0.5 * fit["diameter_mm"] + stock["bore_fill_margin_mm"]
            lo, hi = fit["station_range_mm"]

            def plug_bore(points, datum=datum, direction=direction, radius=radius, lo=lo, hi=hi):
                t, rho = axis_coordinates(points, datum["axis_point"], direction)
                return (t >= lo) & (t <= hi) & (rho <= radius)

            apply(f"thread bore of {name} printed solid", plug_bore, add=True)

    # A filled bore can close a pocket behind it: look again.
    voids = enclosed_air(solid)
    steps.append({"step": "voids enclosed by the stock, filled", "action": "added", "volume_mm3": round(float(voids.sum()) * cell, 1)})
    solid |= voids

    out_dir.mkdir(parents=True, exist_ok=False)
    np.save(out_dir / "occupancy-wn.npy", solid.astype(np.uint8))
    (out_dir / "occupancy-grid.json").write_text(json.dumps({**grid, "array": "occupancy-wn.npy"}, indent=2) + "\n")
    report = {
        "schema": SCHEMA,
        "case_file": "params/print-body-case.json",
        "pitch_mm": h,
        "twin_body_volume_mm3": round(volume_twin, 1),
        "print_body_volume_mm3": round(float(solid.sum()) * cell, 1),
        "stud_residue_removed_mm3": stud_total,
        "enclosed_voids_remaining": int(enclosed_air(solid).sum()),
        "top_of_the_body_mm": round(float(z[np.flatnonzero(solid.any(axis=(0, 1)))[-1]]) + 0.5 * h, 2),
        "steps": steps,
        "claims": "a study object derived from the twin with declared stock and fills; not a build file, no support, "
                  "no machining drawing, and no dimension of the specimen",
    }
    (out_dir / "print-body-occupancy.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("twin_body_volume_mm3", "print_body_volume_mm3", "stud_residue_removed_mm3",
                                             "enclosed_voids_remaining", "top_of_the_body_mm")}))


def check(surface, occupancy_report, summary) -> None:
    """Checks a slicer would make on the extracted surface, joined to the occupancy report."""

    import trimesh

    raw = trimesh.load(surface, process=False, force="mesh")
    raw.merge_vertices()                       # an STL is a triangle soup: weld it, as any consumer will
    edges = np.sort(raw.edges, axis=1)
    _, count = np.unique(edges, axis=0, return_counts=True)
    report = json.loads(Path(occupancy_report).read_text())
    extent = raw.bounds[1] - raw.bounds[0]
    report["surface"] = {
        "file": Path(surface).name, "triangles": int(len(raw.faces)),
        "watertight_after_welding": bool(raw.is_watertight), "winding_consistent": bool(raw.is_winding_consistent),
        "edges_used_once": int((count == 1).sum()), "edges_used_by_more_than_two_faces": int((count > 2).sum()),
        "genus": int(round(1 - raw.euler_number / 2)), "volume_mm3": round(float(raw.volume), 1),
        "bounding_box_mm": [round(float(v), 2) for v in extent],
        "triangles_with_area_below_1e-8_mm2": int((raw.area_faces < 1.0e-8).sum()),
    }
    previous = json.loads(Path(summary).read_text()) if Path(summary).exists() else {}
    if "strict_gate" in previous:
        # The gate is run by hand with the renderer; keep its record only for the same surface.
        same = previous.get("surface", {}).get("triangles") == report["surface"]["triangles"] \
            and previous.get("surface", {}).get("volume_mm3") == report["surface"]["volume_mm3"]
        report["strict_gate"] = previous["strict_gate"] if same else {
            "passed": None, "recorded": "the surface changed since the gate was run: run it again"}
    Path(summary).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["surface"]))


if __name__ == "__main__":
    if sys.argv[1] == "check":
        check(*sys.argv[2:5])
    else:
        main(*sys.argv[1:4])
