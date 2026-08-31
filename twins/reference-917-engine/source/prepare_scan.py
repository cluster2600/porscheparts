#!/usr/bin/env python3
"""Prepare the local Porsche 917 engine scan without modifying the source."""

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


EXPECTED_SHA256 = "428c4143d073f8330022f2fecbd1ac1ee7784d4f1565f1160020448dbdffa0ae"


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
    areas = np.asarray(mesh.area_faces)
    return {
        "vertices": int(len(mesh.vertices)),
        "triangles": int(len(mesh.faces)),
        "boundary_edges": int(np.count_nonzero(incidence == 1)),
        "non_manifold_edges": int(np.count_nonzero(incidence > 2)),
        "zero_area_faces": int(np.count_nonzero(areas <= np.finfo(float).eps)),
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


def component_mesh(mesh: trimesh.Trimesh, labels: np.ndarray, component_id: int) -> trimesh.Trimesh:
    selected = labels[np.asarray(mesh.faces)[:, 0]] == component_id
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


def deviation(reference: trimesh.Trimesh, candidate: trimesh.Trimesh) -> dict[str, float | int]:
    points, _ = trimesh.sample.sample_surface(reference, 50_000, seed=917)
    _, distances, _ = trimesh.proximity.closest_point(candidate, points)
    return {
        "samples": int(len(distances)),
        "median_obj_units": float(np.median(distances)),
        "p95_obj_units": float(np.percentile(distances, 95)),
        "max_obj_units": float(np.max(distances)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    directories = {
        name: output / name for name in ("input", "components", "derived", "reports")
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)

    source_hash = sha256(source)
    if source_hash != EXPECTED_SHA256:
        raise SystemExit(f"unexpected source SHA-256: {source_hash}")

    working_copy = directories["input"] / "917-engine-working-copy.obj"
    if not working_copy.exists():
        shutil.copy2(source, working_copy)
    if sha256(working_copy) != source_hash:
        raise SystemExit("working copy does not match the immutable source")

    mesh = trimesh.load_mesh(working_copy, process=False, maintain_order=True)
    labels, vertex_sizes = component_labels(mesh)
    face_labels = labels[np.asarray(mesh.faces)[:, 0]]
    face_sizes = np.bincount(face_labels, minlength=len(vertex_sizes))
    order = np.argsort(face_sizes)[::-1]

    components = []
    vertices = np.asarray(mesh.vertices)
    for rank, component_id in enumerate(order, start=1):
        indices = np.flatnonzero(labels == component_id)
        bounds = np.vstack((vertices[indices].min(axis=0), vertices[indices].max(axis=0)))
        classification = "main_engine_assembly" if rank == 1 else "detached_element_unclassified"
        part = component_mesh(mesh, labels, int(component_id))
        part_path = directories["components"] / f"component-{rank:02d}-{classification}.ply"
        part.export(part_path, file_type="ply", encoding="binary")
        components.append(
            {
                "rank": rank,
                "component_id": int(component_id),
                "classification": classification,
                "path": str(part_path.resolve()),
                "vertices": int(vertex_sizes[component_id]),
                "triangles": int(face_sizes[component_id]),
                "bounds_min": bounds[0].tolist(),
                "bounds_max": bounds[1].tolist(),
                "dimensions_obj_units": (bounds[1] - bounds[0]).tolist(),
            }
        )

    full_ply = directories["derived"] / "917-engine-full.ply"
    mesh.export(full_ply, file_type="ply", encoding="binary")
    light_600k = directories["derived"] / "917-engine-light-600k.ply"
    light_250k = directories["derived"] / "917-engine-preview-250k.ply"
    simplify(full_ply, light_600k, 600_000)
    simplify(full_ply, light_250k, 250_000)
    mesh_600k = trimesh.load_mesh(light_600k, process=False)
    mesh_250k = trimesh.load_mesh(light_250k, process=False)

    centred = vertices - vertices.mean(axis=0)
    eigenvalues, eigenvectors = np.linalg.eigh(np.cov(centred.T))
    frame = eigenvectors[:, np.argsort(eigenvalues)[::-1]].T

    report = {
        "source": str(source),
        "source_sha256": source_hash,
        "working_copy": str(working_copy),
        "identity": "Porsche 917 suggested by filename; not independently verified",
        "units": "OBJ units; millimetres plausible from overall envelope but unconfirmed",
        "bounds_min": np.asarray(mesh.bounds[0]).tolist(),
        "bounds_max": np.asarray(mesh.bounds[1]).tolist(),
        "dimensions_obj_units": np.asarray(mesh.extents).tolist(),
        "pca_frame_rows_long_transverse_1_transverse_2": frame.tolist(),
        "components": components,
        "topology": {
            "source": topology(mesh),
            "light_600k": topology(mesh_600k),
            "preview_250k": topology(mesh_250k),
        },
        "simplification_deviation": {
            "light_600k": deviation(mesh, mesh_600k),
            "preview_250k": deviation(mesh, mesh_250k),
        },
        "limitations": [
            "The scan contains open boundaries and cannot be printed as a closed solid without a derived display reconstruction.",
            "Topological connectivity does not prove that every attached surface belongs to the engine.",
            "No automatic hole filling is applied to the reference mesh.",
            "The source licence and physical scale remain unverified.",
        ],
    }
    report_path = directories["reports"] / "mesh-preparation.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
