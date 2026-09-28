#!/usr/bin/env python3
"""Build the M64-Z-CC F1 stand-in shell from the canonical 917 engine-case OBJ.

Reverse-engineering lane (M64-Z-CC): convert the 917 engine-case scan into one
cleaned, watertight-checked, decimated shell mesh for use as a visual
stand-in block in the Omniverse assembly. This is a stand-in, NOT M64
geometry. See provenance JSON for open issues.

Methodology mirrors twins/reference-917-engine (prepare_scan.py):
- refuse any source whose SHA-256 differs from the canonical scan hash;
- raw scan and heavy derived meshes stay outside Git;
- report topology with the same edge-incidence semantics;
- units remain unconfirmed OBJ units; no mm scale is asserted.

Stages:
  stats   - before-state topology of the raw OBJ (read-only)
  shell   - clean + decimate + watertight repair attempt -> STL + report JSON
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pymeshlab
import trimesh

EXPECTED_SHA256 = "428c4143d073f8330022f2fecbd1ac1ee7784d4f1565f1160020448dbdffa0ae"
INPUT_PATH = Path(
    "/home/lolman/imports/mac-obj/projects/3dprinting993/raw-scans/"
    "917-engine/original/917-engine-case-with-cylinders.obj"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def topology(mesh: trimesh.Trimesh) -> dict[str, object]:
    """Same edge-incidence semantics as prepare_scan.py topology()."""
    faces = np.asarray(mesh.faces, dtype=np.int64)
    edges = np.vstack((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    edges.sort(axis=1)
    _, incidence = np.unique(edges, axis=0, return_counts=True)
    areas = np.asarray(mesh.area_faces)
    return {
        "vertices": int(len(mesh.vertices)),
        "triangles": int(len(mesh.faces)),
        "boundary_edges": int(np.count_nonzero(incidence == 1)),
        "non_manifold_edges": int(np.count_nonzero(incidence > 2)),
        "zero_area_faces": int(np.count_nonzero(areas <= np.finfo(float).eps)),
        "watertight": bool(np.all(incidence == 2)),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "body_count": int(mesh.body_count),
        "extents_obj_units": np.asarray(mesh.extents).tolist(),
        "bounds_obj_units": np.asarray(mesh.bounds).tolist(),
    }


def tool_versions() -> dict[str, str]:
    import pymeshlab as pm

    version_text = pm.print_pymeshlab_version.__doc__ or ""
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "trimesh": trimesh.__version__,
        "pymeshlab": "PyMeshLab 2025.7.post1 based on MeshLab 2025.07d",
        "pymeshlab_doc": version_text.strip(),
    }


def stage_stats(outdir: Path) -> int:
    src_hash = sha256(INPUT_PATH)
    if src_hash != EXPECTED_SHA256:
        raise SystemExit(f"unexpected source SHA-256: {src_hash}")
    mesh = trimesh.load_mesh(INPUT_PATH, process=False)
    report = {
        "stage": "stats",
        "input": str(INPUT_PATH),
        "sha256": src_hash,
        "tool_versions": tool_versions(),
        "before": topology(mesh),
        "units": "unconfirmed_OBJ_units",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (outdir / "stats-before.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report["before"], indent=2))
    return 0


def stage_shell(outdir: Path, target_faces: int) -> int:
    src_hash = sha256(INPUT_PATH)
    if src_hash != EXPECTED_SHA256:
        raise SystemExit(f"unexpected source SHA-256: {src_hash}")

    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(str(INPUT_PATH))
    before_ml = {
        "vertices": ms.current_mesh().vertex_number(),
        "triangles": ms.current_mesh().face_number(),
    }

    # Cleaning (same filter set as the reference pipeline prepare_scan.py)
    ops = []
    for filt in (
        "meshing_remove_duplicate_vertices",
        "meshing_remove_duplicate_faces",
        "meshing_remove_null_faces",
        "meshing_remove_unreferenced_vertices",
    ):
        ms.apply_filter(filt)
        ops.append(filt)

    # Decimate to assembly-usable size
    ms.apply_filter(
        "meshing_decimation_quadric_edge_collapse",
        targetfacenum=target_faces,
        preserveboundary=True,
        preservenormal=True,
        preservetopology=True,
        optimalplacement=True,
        planarquadric=True,
        autoclean=True,
    )
    ops.append(f"meshing_decimation_quadric_edge_collapse(targetfacenum={target_faces})")

    # Watertight repair attempt: merge close vertices, then close small holes
    ms.apply_filter("meshing_remove_duplicate_vertices")
    ms.apply_filter("meshing_close_holes", maxholesize=300)
    ops.append("meshing_close_holes(maxholesize=300)")
    ms.apply_filter("meshing_remove_unreferenced_vertices")

    ms.save_current_mesh(str(outdir / "shell-decimated.obj"), save_vertex_normal=False)

    mesh = trimesh.load_mesh(outdir / "shell-decimated.obj", process=False)
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    after = topology(mesh)

    # If still open after hole-closing, seal with voxel/alpha-free fallback:
    # keep largest body and report; do not silently boolean-wrap.
    watertight = bool(np.asarray(after["boundary_edges"]) == 0)
    watertight_final = watertight
    if not watertight:
        parts = sorted(
            mesh.split(only_watertight=False),
            key=lambda item: len(item.faces),
            reverse=True,
        )
        main = parts[0]
        main.fix_normals()
        after_main = topology(main)
        if after_main["watertight"]:
            mesh = main
            after = after_main
            watertight_final = True
            ops.append(f"kept largest of {len(parts)} disconnected bodies")
        else:
            ops.append(
                f"remained open after repair: {after['boundary_edges']} boundary edges; "
                "shell exported as-is and flagged not_watertight"
            )

    stl_path = outdir / "917-case-f1-shell.stl"
    mesh.export(stl_path)

    report = {
        "stage": "shell",
        "input": str(INPUT_PATH),
        "sha256": src_hash,
        "tool_versions": tool_versions(),
        "before": {"pymeshlab_load": before_ml},
        "after": after,
        "ops": ops,
        "watertight_final": watertight_final,
        "output_stl_bytes": stl_path.stat().st_size,
        "units": "unconfirmed_OBJ_units",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (outdir / "stats-after.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("stats", "shell"))
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--target-faces", type=int, default=1500000)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.stage == "stats":
        return stage_stats(args.outdir)
    return stage_shell(args.outdir, args.target_faces)


if __name__ == "__main__":
    raise SystemExit(main())
