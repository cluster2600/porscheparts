#!/usr/bin/env python3
"""Export a small, checked visualization STL from a dashboard F0 PicoGK build.

Run in the native Linux checkout with the local picogk-tools venv::

    python parts/993-int-dashboard-trim-0001/source/export_visual_mesh.py \
      --input work/dashboard-trim-picogk-f0-20261106 \
      --output work/dashboard-trim-picogk-f0-20261106/dashboard-f0-visual-repro.stl

The output and its JSON sidecar must be new paths under work/. This script
never writes a manufacturing mesh or modifies the PicoGK build inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
import platform
import tempfile
from pathlib import Path

import numpy as np
import pyvista as pv
import trimesh

PART_ID = "993-INT-DASHBOARD-TRIM-0001"
TARGET_FACES = 18_000
MAX_STL_BYTES = 1_048_576
MAX_BOUNDS_SHIFT_MM = 0.75  # one source voxel
MAX_VOLUME_DELTA_PERCENT = 0.5
ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "work"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def topology(mesh: trimesh.Trimesh, voxel_mm: float) -> dict:
    shells = mesh.split(only_watertight=False)
    signed = np.asarray([float(shell.volume) for shell in shells])
    tiny = (2.0 * voxel_mm) ** 3
    edges = mesh.edges_sorted.astype(np.int64)
    keys = edges[:, 0] * np.int64(len(mesh.vertices)) + edges[:, 1]
    _, counts = np.unique(keys, return_counts=True)
    return {
        "triangles": int(len(mesh.faces)),
        "vertices_after_welding": int(len(mesh.vertices)),
        "components": int(len(shells)),
        "positive_volume_bodies": int((signed > tiny).sum()),
        "sealed_voids": int((signed < -tiny).sum()),
        "subvoxel_components": int((np.abs(signed) <= tiny).sum()),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "boundary_edges": int((counts == 1).sum()),
        "nonmanifold_edges": int((counts > 2).sum()),
        "degenerate_faces": int((mesh.area_faces <= 1e-12).sum()),
        "bounds_min_mm": [round(float(v), 3) for v in mesh.bounds[0]],
        "bounds_max_mm": [round(float(v), 3) for v in mesh.bounds[1]],
        "size_mm": [round(float(v), 3) for v in mesh.extents],
        "volume_cm3": round(float(mesh.volume) / 1000.0, 3),
    }


def require_one_closed_body(qa: dict, label: str) -> None:
    expected = {
        "components": 1,
        "positive_volume_bodies": 1,
        "sealed_voids": 0,
        "subvoxel_components": 0,
        "watertight": True,
        "winding_consistent": True,
        "boundary_edges": 0,
        "nonmanifold_edges": 0,
        "degenerate_faces": 0,
    }
    for key, value in expected.items():
        require(qa[key] == value, f"{label}: {key} = {qa[key]!r}, expected {value!r}")
    require(qa["volume_cm3"] > 0, f"{label}: nonpositive volume")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="PicoGK build directory under work/")
    parser.add_argument("--output", type=Path, required=True, help="new visualization STL path under work/")
    args = parser.parse_args()

    work = WORK.resolve(strict=True)
    input_dir = args.input.expanduser().resolve(strict=True)
    require(input_dir.is_dir() and input_dir.is_relative_to(work), "--input must be a directory under work/")
    output_parent = args.output.expanduser().parent.resolve(strict=True)
    output = output_parent / args.output.name
    sidecar = output.with_suffix(".json")
    require(output_parent.is_relative_to(work), "--output must be under work/")
    require(output.suffix.lower() == ".stl", "--output must end in .stl")
    require(not os.path.lexists(output) and not os.path.lexists(sidecar),
            "output STL and JSON sidecar must be new paths")

    source = input_dir / f"{PART_ID}.stl"
    report_path = input_dir / f"{PART_ID}.report.json"
    manifest_path = input_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    require(manifest.get("part_id") == PART_ID and report.get("part_id") == PART_ID,
            "input part ID does not match dashboard F0")
    require(report.get("generator") == "dashboard_trim_panel" and
            manifest.get("input_basis") == "assumed_geometry", "input is not the F0 concept generator")
    source_hash = sha256(source)
    require(source_hash == manifest.get("mesh_sha256"), "source STL hash differs from build manifest")
    require(sha256(report_path) == manifest.get("report_sha256"), "report hash differs from build manifest")
    voxel_mm = float(report["voxel_mm"])
    require(voxel_mm > 0, "invalid source voxel size")

    mesh = trimesh.load_mesh(source, process=True)
    degenerate_removed = int((mesh.area_faces <= 1e-12).sum())
    if degenerate_removed:
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        mesh.merge_vertices()
    source_qa = topology(mesh, voxel_mm)
    require_one_closed_body(source_qa, "cleaned PicoGK source")
    require(source_qa["triangles"] == int(report["triangles"]) - degenerate_removed,
            "cleaned triangle count disagrees with generator report")
    require(max(abs(a - float(b)) for a, b in zip(source_qa["size_mm"], report["bbox_mm"])) <= 0.15,
            "source dimensions disagree with generator report")
    require(abs(source_qa["volume_cm3"] - float(report["volume_cm3"])) <= 0.05,
            "source volume disagrees with generator report")

    faces = np.column_stack((np.full(len(mesh.faces), 3, dtype=np.int64), mesh.faces))
    poly = pv.PolyData(np.asarray(mesh.vertices), faces)
    require(poly.n_cells > TARGET_FACES, "source has too few faces for the fixed target")
    reduced = poly.decimate(1.0 - TARGET_FACES / poly.n_cells,
                            volume_preservation=True, boundary_constraints=True)
    require(reduced.n_cells == TARGET_FACES, "decimator did not reach 18,000 triangles")

    with tempfile.TemporaryDirectory(prefix=".dashboard-f0-visual-", dir=output_parent) as temporary:
        staging = Path(temporary)
        staged_stl = staging / output.name
        staged_json = staging / sidecar.name
        reduced.save(str(staged_stl), binary=True)
        require(staged_stl.stat().st_size < MAX_STL_BYTES, "visualization STL exceeds 1 MiB")
        visual = trimesh.load_mesh(staged_stl, process=True)
        output_qa = topology(visual, voxel_mm)
        require_one_closed_body(output_qa, "visualization STL")
        require(output_qa["triangles"] == TARGET_FACES, "saved STL changed triangle count")
        min_shift = np.abs(np.asarray(output_qa["bounds_min_mm"]) - np.asarray(source_qa["bounds_min_mm"]))
        max_shift = np.abs(np.asarray(output_qa["bounds_max_mm"]) - np.asarray(source_qa["bounds_max_mm"]))
        bounds_shift = float(max(np.max(min_shift), np.max(max_shift)))
        size_delta = np.asarray(output_qa["size_mm"]) - np.asarray(source_qa["size_mm"])
        volume_delta_percent = 100.0 * (output_qa["volume_cm3"] - source_qa["volume_cm3"]) / source_qa["volume_cm3"]
        require(bounds_shift <= MAX_BOUNDS_SHIFT_MM,
                f"visualization bounds shifted by {bounds_shift:.3f} mm")
        require(abs(volume_delta_percent) <= MAX_VOLUME_DELTA_PERCENT,
                f"visualization volume changed by {volume_delta_percent:.3f}%")
        sidecar_data = {
            "part_id": PART_ID,
            "purpose": "F0 concept visualization only; not a manufacturing file or evidence of fit, function, or safety",
            "source_stl": source.relative_to(ROOT).as_posix(),
            "source_sha256": source_hash,
            "source_manifest_sha256": sha256(manifest_path),
            "source_report_sha256": sha256(report_path),
            "output_stl": output.relative_to(ROOT).as_posix(),
            "output_sha256": sha256(staged_stl),
            "output_bytes": staged_stl.stat().st_size,
            "tool_versions": {
                "python": platform.python_version(),
                "numpy": metadata.version("numpy"),
                "trimesh": metadata.version("trimesh"),
                "pyvista": metadata.version("pyvista"),
                "vtk": metadata.version("vtk"),
            },
            "export_script_sha256": sha256(Path(__file__)),
            "method": {
                "degenerate_faces_removed": degenerate_removed,
                "cleanup": "remove degenerate faces using the nondegenerate mask; remove unreferenced vertices; merge vertices",
                "decimator": "PyVista PolyData.decimate",
                "target_triangles": TARGET_FACES,
                "volume_preservation": True,
                "boundary_constraints": True,
                "binary_stl": True,
            },
            "source_after_cleanup": source_qa,
            "visualization": output_qa,
            "comparison": {
                "max_absolute_bound_shift_mm": round(bounds_shift, 3),
                "size_delta_mm": [round(float(v), 3) for v in size_delta],
                "volume_delta_percent": round(volume_delta_percent, 3),
                "max_bound_shift_allowed_mm": MAX_BOUNDS_SHIFT_MM,
                "max_volume_delta_allowed_percent": MAX_VOLUME_DELTA_PERCENT,
            },
        }
        staged_json.write_text(json.dumps(sidecar_data, indent=2) + "\n", encoding="utf-8")
        # Publish only after every source, topology, size and volume check passes.
        require(not os.path.lexists(output) and not os.path.lexists(sidecar),
                "output appeared during QA")
        os.link(staged_stl, output)
        try:
            os.link(staged_json, sidecar)
        except BaseException:
            output.unlink()
            raise
    print(json.dumps({"output": str(output), "sha256": sidecar_data["output_sha256"],
                      "bytes": sidecar_data["output_bytes"], "triangles": TARGET_FACES,
                      "sidecar": str(sidecar), "volume_delta_percent": sidecar_data["comparison"]["volume_delta_percent"]},
                     indent=2))


if __name__ == "__main__":
    main()
