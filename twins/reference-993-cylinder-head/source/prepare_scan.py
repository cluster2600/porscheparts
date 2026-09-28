#!/usr/bin/env python3
"""Prepare the purchased Wolfe Classics 935 cylinder-head scan.

The source OBJ is never modified. Heavy and licence-restricted outputs belong
under ``work/`` or ``raw-scans/`` and must not be committed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pymeshlab
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


EXPECTED_SHA256 = "4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def topology(mesh: trimesh.Trimesh) -> dict[str, int | bool]:
    faces = np.asarray(mesh.faces, dtype=np.int64)
    edges = np.vstack((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    edges.sort(axis=1)
    _, incidence = np.unique(edges, axis=0, return_counts=True)
    return {
        "vertices": int(len(mesh.vertices)),
        "triangles": int(len(mesh.faces)),
        "boundary_edges": int(np.count_nonzero(incidence == 1)),
        "non_manifold_edges": int(np.count_nonzero(incidence > 2)),
        "watertight": bool(np.all(incidence == 2)),
    }


def component_labels(mesh: trimesh.Trimesh) -> tuple[np.ndarray, np.ndarray]:
    faces = np.asarray(mesh.faces, dtype=np.int32)
    rows = np.concatenate(
        (faces[:, 0], faces[:, 1], faces[:, 1], faces[:, 2], faces[:, 2], faces[:, 0])
    )
    cols = np.concatenate(
        (faces[:, 1], faces[:, 0], faces[:, 2], faces[:, 1], faces[:, 0], faces[:, 2])
    )
    graph = coo_matrix(
        (np.ones(rows.size, dtype=np.uint8), (rows, cols)),
        shape=(len(mesh.vertices), len(mesh.vertices)),
    ).tocsr()
    count, labels = connected_components(graph, directed=False, return_labels=True)
    return labels, np.bincount(labels, minlength=count)


def mesh_for_components(
    mesh: trimesh.Trimesh, labels: np.ndarray, component_ids: set[int]
) -> trimesh.Trimesh:
    selected = np.isin(labels[np.asarray(mesh.faces)[:, 0]], list(component_ids))
    return mesh.submesh([selected], append=True, repair=False)


def simplify(source: Path, target: Path, target_faces: int) -> None:
    mesh_set = pymeshlab.MeshSet()
    mesh_set.load_new_mesh(str(source))
    mesh_set.apply_filter("meshing_remove_duplicate_vertices")
    mesh_set.apply_filter("meshing_remove_duplicate_faces")
    mesh_set.apply_filter("meshing_remove_null_faces")
    mesh_set.apply_filter("meshing_remove_unreferenced_vertices")
    mesh_set.apply_filter(
        "meshing_decimation_quadric_edge_collapse",
        targetfacenum=target_faces,
        preserveboundary=True,
        preservenormal=True,
        preservetopology=True,
        optimalplacement=True,
        planarquadric=True,
        autoclean=True,
    )
    mesh_set.apply_filter("compute_normal_per_face")
    mesh_set.apply_filter("compute_normal_per_vertex")
    mesh_set.save_current_mesh(str(target), save_vertex_normal=True)


def deviation(reference: trimesh.Trimesh, candidate: trimesh.Trimesh) -> dict[str, float]:
    points, _ = trimesh.sample.sample_surface(reference, 30_000, seed=935)
    _, distances, _ = trimesh.proximity.closest_point(candidate, points)
    return {
        "samples": int(len(distances)),
        "median_units": float(np.median(distances)),
        "p95_units": float(np.percentile(distances, 95)),
        "max_units": float(np.max(distances)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    input_dir = output / "input"
    component_dir = output / "components"
    derived_dir = output / "derived"
    report_dir = output / "reports"
    for directory in (input_dir, component_dir, derived_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)

    source_hash = sha256(source)
    if source_hash != EXPECTED_SHA256:
        raise SystemExit(f"unexpected source SHA-256: {source_hash}")

    working_copy = input_dir / "935-xtreme-cylinder-head-working-copy.obj"
    if not working_copy.exists():
        shutil.copy2(source, working_copy)
    if sha256(working_copy) != source_hash:
        raise SystemExit("working copy does not match the immutable source")

    mesh = trimesh.load_mesh(working_copy, process=False, maintain_order=True)
    labels, vertex_sizes = component_labels(mesh)
    face_labels = labels[np.asarray(mesh.faces)[:, 0]]
    face_sizes = np.bincount(face_labels, minlength=len(vertex_sizes))
    order = np.argsort(face_sizes)[::-1]
    main_id = int(order[0])
    detached_ids = {int(i) for i in order[1:] if face_sizes[i] >= 100}
    parasite_ids = {int(i) for i in order[1:] if face_sizes[i] < 100}

    head_with_studs = mesh_for_components(mesh, labels, {main_id})
    detached = mesh_for_components(mesh, labels, detached_ids) if detached_ids else None
    parasites = mesh_for_components(mesh, labels, parasite_ids) if parasite_ids else None

    main_path = component_dir / "head-with-studs-full.ply"
    head_with_studs.export(main_path, file_type="ply", encoding="binary")
    if detached is not None:
        detached.export(component_dir / "detached-element-full.ply", file_type="ply", encoding="binary")
    if parasites is not None:
        parasites.export(component_dir / "scan-parasites-full.ply", file_type="ply", encoding="binary")

    light_300k = derived_dir / "head-with-studs-light-300k.ply"
    light_100k = derived_dir / "head-with-studs-light-100k.ply"
    simplify(main_path, light_300k, 300_000)
    simplify(main_path, light_100k, 100_000)
    mesh_300k = trimesh.load_mesh(light_300k, process=False)
    mesh_100k = trimesh.load_mesh(light_100k, process=False)

    components = []
    vertices = np.asarray(mesh.vertices)
    for rank, component_id in enumerate(order, start=1):
        index = np.flatnonzero(labels == component_id)
        bounds = np.vstack((vertices[index].min(axis=0), vertices[index].max(axis=0)))
        components.append(
            {
                "rank": rank,
                "component_id": int(component_id),
                "classification": (
                    "head_with_attached_studs"
                    if component_id == main_id
                    else "detached_element"
                    if component_id in detached_ids
                    else "scan_parasite"
                ),
                "vertices": int(vertex_sizes[component_id]),
                "triangles": int(face_sizes[component_id]),
                "bounds_min": bounds[0].tolist(),
                "bounds_max": bounds[1].tolist(),
                "dimensions": (bounds[1] - bounds[0]).tolist(),
            }
        )

    report = {
        "source": str(source),
        "source_sha256": source_hash,
        "working_copy": str(working_copy),
        "units": "OBJ units; millimetres plausible but unconfirmed",
        "components": components,
        "topology": {
            "head_with_studs": topology(head_with_studs),
            "light_300k": topology(mesh_300k),
            "light_100k": topology(mesh_100k),
        },
        "simplification_deviation": {
            "light_300k": {
                "decision": "accepted_for_working_geometry",
                **deviation(head_with_studs, mesh_300k),
            },
            "light_100k": {
                "decision": "rejected_for_measurement_preview_only",
                **deviation(head_with_studs, mesh_100k),
            },
        },
        "limitations": [
            "Attached studs remain topologically connected to the cylinder head.",
            "No unit is declared by OBJ.",
            "No automatic hole filling is applied because functional openings and scan gaps are not yet classified.",
        ],
    }
    report_path = report_dir / "mesh-preparation.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
