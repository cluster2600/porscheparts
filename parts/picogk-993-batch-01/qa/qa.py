#!/usr/bin/env python3
"""Independent mesh QA for picogk-993-batch-01.

Reads out/<id>.stl and params/<id>.json; it does not trust the generator's
own report. For each part: watertightness, connected bodies, volume, size,
and comparison of the bounding box with every *published* envelope value.
Renders media/<id>.png (shaded view + half section).

Usage: python qa/qa.py [part-id ...]
Requires: numpy, trimesh, pyvista (containers/m64-leap71/geometry-qa-requirements.txt)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pyvista as pv
import trimesh

ROOT = Path(__file__).resolve().parents[1]
ENVELOPE_KEYS = {
    "length_mm", "width_mm", "height_mm", "outlet_width_mm", "outlet_height_mm", "face_diameter_mm",
    "overall_height_mm", "inlet_width_mm", "depth_mm", "knob_diameter_mm", "face_width_mm", "face_height_mm",
}
TOL_MM = 1.5   # envelope tolerance: voxel quantization + fillets


def check(part_id: str) -> dict:
    spec = json.loads((ROOT / "params" / f"{part_id.lower()}.json").read_text(encoding="utf-8"))
    stl = ROOT / "out" / f"{spec['part_id']}.stl"
    mesh = trimesh.load_mesh(stl, process=True)
    # Marching cubes leaves zero-area triangles where vertices coincide; they
    # make a few hundred non-manifold edges. Remove them (volume unchanged)
    # and write the cleaned STL back.
    degenerate = int((mesh.area_faces <= 1e-12).sum())
    if degenerate:
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        mesh.merge_vertices()
        mesh.export(stl)
    # Each closed shell is a body (positive signed volume) or a sealed void
    # (negative signed volume, i.e. an inward-facing cavity that would trap powder).
    shells = mesh.split(only_watertight=False)
    # Shells smaller than two voxels across are marching-cubes slivers, not
    # printable features or cavities: drop them from the STL, but count them.
    artefact_mm3 = (2.0 * spec["voxel_mm"]) ** 3
    kept = [sh for sh in shells if abs(float(sh.volume)) >= artefact_mm3]
    artefacts = len(shells) - len(kept)
    if artefacts:
        mesh = trimesh.util.concatenate(kept)
        mesh.export(stl)
        shells = kept
    signed = [float(sh.volume) for sh in shells]
    solids = sum(1 for v in signed if v > 1e-3)
    voids = sum(1 for v in signed if v < -1e-3)
    size = sorted((mesh.bounds[1] - mesh.bounds[0]).tolist(), reverse=True)

    envelope = []
    for key, p in spec["parameters"].items():
        if key in ENVELOPE_KEYS and p["basis"] in {"published", "catalogue", "community"}:
            nearest = min(size, key=lambda s: abs(s - p["value"]))
            envelope.append({"parameter": key, "published_mm": p["value"], "model_extent_mm": round(nearest, 2),
                             "ok": abs(nearest - p["value"]) <= TOL_MM})
    basis = {}
    for p in spec["parameters"].values():
        basis[p["basis"]] = basis.get(p["basis"], 0) + 1
    result = {
        "part_id": spec["part_id"],
        "watertight": bool(mesh.is_watertight),
        "bodies": solids,
        "sealed_voids": voids,
        "sub_voxel_artefact_shells_removed": artefacts,
        "triangles": int(len(mesh.faces)),
        "degenerate_faces_removed": degenerate,
        "volume_cm3": round(float(abs(mesh.volume)) / 1000.0, 2),
        "mass_estimate_g": round(float(abs(mesh.volume)) / 1000.0 * spec["density_g_cm3"], 1),
        "size_mm_sorted": [round(s, 2) for s in size],
        "envelope_checks": envelope,
        "parameter_basis": basis,
        "open_interfaces": spec["open_interfaces"],
    }
    render(mesh, spec)
    return result


def render(mesh: trimesh.Trimesh, spec: dict) -> None:
    media = ROOT / "media"
    media.mkdir(exist_ok=True)
    faces = np.hstack([np.full((len(mesh.faces), 1), 3), mesh.faces]).astype(np.int64)
    poly = pv.PolyData(mesh.vertices, faces)
    # Section through the plane (x or y, several offsets) that cuts the most
    # material, so internal structure is visible even on open frames.
    best = (0.0, "y", poly.center)
    lo, hi = mesh.bounds
    for axis, n in (("x", [1, 0, 0]), ("y", [0, 1, 0])):
        i = 0 if axis == "x" else 1
        for f in (0.5, 0.35, 0.65, 0.2, 0.8, 0.1, 0.9):
            origin = list(poly.center)
            origin[i] = lo[i] + f * (hi[i] - lo[i])
            area = float(poly.slice(normal=n, origin=origin).n_points)  # proxy: cut length
            if area > best[0]:
                best = (area, axis, origin)
    half = poly.clip(normal=best[1], origin=best[2], invert=False)
    pl = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1600, 800))
    pl.set_background("white")
    pl.subplot(0, 0)
    pl.add_mesh(poly, color="#b8bcc4", smooth_shading=True, specular=0.3)
    pl.add_text(spec["name"], font_size=10, color="black")
    pl.view_isometric()
    pl.subplot(0, 1)
    pl.add_mesh(half, color="#c9a46b", smooth_shading=False)
    pl.add_text("half section (internal structure)", font_size=10, color="black")
    # Look at the cut face, from the removed side, slightly from above.
    n = np.array([1.0, 0.0, 0.0]) if best[1] == "x" else np.array([0.0, 1.0, 0.0])
    c = np.array(half.center)
    dist = 2.6 * float(np.linalg.norm(np.array(mesh.bounds[1]) - np.array(mesh.bounds[0])))
    pl.camera_position = [tuple(c - n * dist + np.array([0.0, 0.0, 0.35 * dist])), tuple(c), (0.0, 0.0, 1.0)]
    pl.camera.azimuth = 18
    pl.screenshot(str(media / f"{spec['part_id']}.png"))
    pl.close()


def main(argv: list[str]) -> int:
    ids = argv or sorted(p.stem.upper() for p in (ROOT / "params").glob("*.json") if (ROOT / "out" / f"{p.stem.upper()}.stl").exists())
    results, failed = [], 0
    for part_id in ids:
        r = check(part_id)
        ok = r["watertight"] and r["bodies"] == 1 and r["sealed_voids"] == 0 and all(e["ok"] for e in r["envelope_checks"])
        failed += not ok
        r["qa_pass"] = ok
        results.append(r)
        env = ", ".join(f"{e['parameter']} {e['published_mm']}->{e['model_extent_mm']}" for e in r["envelope_checks"])
        print(f"{'PASS' if ok else 'FAIL'} {r['part_id']:<36} watertight={r['watertight']} bodies={r['bodies']} voids={r['sealed_voids']} "
              f"vol={r['volume_cm3']} cm3 mass~{r['mass_estimate_g']} g  [{env}]")
    (ROOT / "out" / "qa-summary.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
