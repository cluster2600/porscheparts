#!/usr/bin/env python3
"""QA a generated PicoGK part, publish it as derived/<stem>-picogk.stl, render.

    python finish.py <PART_ID> [--max-tris 30000] [--no-render]

Independent of the generator: reads only out/<PART_ID>.stl and the part's
source/picogk.json. Publishes nothing unless every check passes:

- one solid body, no sealed void (a sealed cavity hides from inspection and
  traps powder, resin or water), closed main surface;
- every parameter named in "envelope" (basis published/catalogue/community)
  matches an extent of the model within max(1.5 mm, 2 voxels);
- the bounding box is reported next to the existing CAD's (media/preview.json)
  so a drift from the documented concept is visible.

Then the main body is decimated for the repository (the full-resolution STL
stays in out/, regenerable), written with a provenance JSON, and the part's
preview is re-rendered by scripts/render_part_previews.py.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pyvista as pv
import trimesh

CATALOG = Path(__file__).resolve().parents[1]
ROOT = CATALOG.parents[1]


def edge_counts(m):
    e = m.edges_sorted.astype(np.int64)
    _, n = np.unique(e[:, 0] * np.int64(len(m.vertices)) + e[:, 1], return_counts=True)
    return {"open": int((n == 1).sum()), "non_manifold": int((n > 2).sum()), "total": int(len(n))}


def legacy_bbox(part_dir):
    info = part_dir / "media" / "preview.json"
    if not info.exists():
        return None
    data = json.loads(info.read_text(encoding="utf-8"))
    if any(s["path"].endswith("-picogk.stl") for s in data.get("sources", [])):
        old = part_dir / "derived"
        prev = next(iter(sorted(old.glob("*-picogk.json"))), None)
        return json.loads(prev.read_text(encoding="utf-8")).get("legacy_bbox_mm") if prev else None
    return data.get("bounding_box_mm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("part_id")
    ap.add_argument("--max-tris", type=int, default=30_000)
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
    part_dir = ROOT / "parts" / a.part_id.lower()
    spec = json.loads((part_dir / "source" / "picogk.json").read_text(encoding="utf-8"))
    stl = CATALOG / "out" / f"{spec['part_id']}.stl"
    report = json.loads((CATALOG / "out" / f"{spec['part_id']}.report.json").read_text(encoding="utf-8"))
    voxel = float(spec["voxel_mm"])

    mesh = trimesh.load_mesh(stl, process=True)
    degenerate = int((mesh.area_faces <= 1e-12).sum())
    if degenerate:
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        mesh.merge_vertices()
    shells = mesh.split(only_watertight=False)
    signed = np.array([float(s.volume) for s in shells])
    tiny = (2.0 * voxel) ** 3
    main_body = shells[int(np.argmax(signed))]
    edges = edge_counts(main_body)
    size = (main_body.bounds[1] - main_body.bounds[0]).tolist()
    tol = max(1.5, 2 * voxel)
    envelope = []
    axes = spec.get("envelope_axes", {})          # optional {"param": "x"|"y"|"z"}: check that axis only
    for key in spec.get("envelope", []):
        p = spec["parameters"][key]
        if key in axes:
            nearest = size["xyz".index(axes[key])]
        else:                                     # no axis given: nearest extent (looser for cube-like boxes)
            nearest = min(size, key=lambda s: abs(s - p["value"]))
        envelope.append({"parameter": key, "basis": p["basis"], "value_mm": p["value"], "axis": axes.get(key, "nearest"),
                         "model_extent_mm": round(nearest, 2), "ok": abs(nearest - p["value"]) <= tol})
    qa = {
        "bodies": int((signed > tiny).sum()),
        "sealed_voids": int((signed < -tiny).sum()),
        "sub_voxel_shells_dropped": int((np.abs(signed) <= tiny).sum()),
        "main_body_edges": edges,
        "degenerate_faces_removed": degenerate,
        "volume_cm3": round(float(main_body.volume) / 1000, 2),
        "bbox_mm": [round(s, 1) for s in size],
        "envelope_checks": envelope,
    }
    qa["pass"] = (qa["bodies"] == 1 and qa["sealed_voids"] == 0 and edges["open"] == 0
                  and edges["non_manifold"] <= max(4, 1e-5 * edges["total"]) and all(e["ok"] for e in envelope))
    print(json.dumps(qa, indent=1))
    if not qa["pass"]:
        print(f"FAIL {spec['part_id']}: nothing published", file=sys.stderr)
        return 1

    # Publish a decimated main body; fragments below two voxels are dropped.
    faces = np.hstack([np.full((len(main_body.faces), 1), 3), main_body.faces]).astype(np.int64)
    poly = pv.PolyData(np.asarray(main_body.vertices), faces)
    # Display smoothing after QA: a light Taubin filter (volume-preserving) removes
    # the voxel terracing that decimation turns into shading streaks. The shift
    # of the bounding box is measured and recorded.
    bounds_raw = np.array(poly.bounds)
    poly = poly.smooth_taubin(n_iter=30, pass_band=0.05)
    smoothing_shift = float(np.abs(np.array(poly.bounds) - bounds_raw).max())
    max_tris = int(spec.get("max_tris", a.max_tris))   # per-part override for fine detail
    if poly.n_cells > max_tris:
        poly = poly.decimate(1.0 - max_tris / poly.n_cells)
    derived = part_dir / "derived"
    legacy = [p for p in sorted(derived.iterdir()) if p.suffix.lower() in (".step", ".stp", ".stl")
              and not p.name.endswith("-picogk.stl")]
    stem = (legacy[0].stem if legacy else spec["part_id"].lower()) + "-picogk"
    bbox_before = legacy_bbox(part_dir)
    out_stl = derived / f"{stem}.stl"
    poly.save(str(out_stl), binary=True)
    prov = {
        "part_id": spec["part_id"],
        "status": spec.get("status", ""),
        "kernel": report.get("kernel"),
        "generator": spec["generator"],
        "parameters": f"parts/{a.part_id.lower()}/source/picogk.json",
        "generator_report": {k: report[k] for k in ("voxel_mm", "triangles", "volume_cm3", "mass_estimate_g", "seconds")},
        "published_triangles": int(poly.n_cells),
        "display_smoothing": {"filter": "taubin", "iterations": 30, "pass_band": 0.05,
                              "max_bounds_shift_mm": round(smoothing_shift, 3)},
        "published_sha256": hashlib.sha256(out_stl.read_bytes()).hexdigest(),
        "legacy_bbox_mm": bbox_before,
        "qa": qa,
        "note": "PicoGK concept model; not a print file, not evidence of fit, function or safety.",
    }
    (derived / f"{stem}.json").write_text(json.dumps(prov, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"published {out_stl.relative_to(ROOT)} ({poly.n_cells} triangles); legacy bbox {bbox_before} -> {qa['bbox_mm']}")
    if not a.no_render:
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "render_part_previews.py"), "--write",
                            "--only", spec["part_id"]], capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr[-2000:])
        return r.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
