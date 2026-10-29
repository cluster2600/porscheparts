#!/usr/bin/env python3
"""Preserve observed scan geometry and report gaps; never infer a solid."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import numpy as np
import scipy
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
import trimesh

EXPECTED_SHA256 = "4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486"


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inspect(mesh):
    v, f = np.asarray(mesh.vertices), np.asarray(mesh.faces)
    if not len(v) or not len(f) or not np.isfinite(v).all():
        raise ValueError("empty or nonfinite geometry")
    if f.min() < 0 or f.max() >= len(v):
        raise ValueError("invalid triangle indices")
    edges = np.concatenate((f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]))
    edges.sort(axis=1)
    edges, counts = np.unique(edges, axis=0, return_counts=True)
    boundary = edges[counts == 1]
    graph = coo_matrix((np.ones(len(edges), dtype=np.uint8),
                       (edges[:, 0], edges[:, 1])), shape=(len(v), len(v)))
    _, labels = connected_components(graph, directed=False)
    face_labels = labels[f[:, 0]]
    sizes = np.bincount(face_labels)
    component_ids = np.flatnonzero(sizes)
    order = component_ids[np.argsort(sizes[component_ids])[::-1]]
    zero_area = np.linalg.norm(np.cross(v[f[:, 1]] - v[f[:, 0]],
                                        v[f[:, 2]] - v[f[:, 0]]), axis=1) == 0
    report = {
        "vertices": len(v), "triangles": len(f),
        "boundary_edges": len(boundary),
        "nonmanifold_edges": int(np.count_nonzero(counts > 2)),
        "zero_area_triangles": int(zero_area.sum()),
        "duplicate_triangles": len(f) - len(np.unique(np.sort(f, axis=1), axis=0)),
        "watertight_edge_incidence": bool(np.all(counts == 2)),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "bounds_source_units": mesh.bounds.tolist(),
        "connected_surface_components": len(order),
        "components": [{"id": int(i), "triangles": int(sizes[i])} for i in order],
        "self_intersections": "not_evaluated",
    }
    return report, boundary, face_labels, int(order[0])


def write_observed_component(mesh, mask, path):
    """17 digits preserve Float64 coordinates; no decimation or hole filling."""
    faces = np.asarray(mesh.faces)[mask]
    indices, inverse = np.unique(faces, return_inverse=True)
    vertices = np.asarray(mesh.vertices)[indices]
    faces = inverse.reshape((-1, 3))
    with path.open("x") as stream:
        stream.write("# Observed surface only. Units unverified. NOT PRINT READY.\n")
        for p in vertices:
            stream.write("v %.17g %.17g %.17g\n" % tuple(p))
        for f in faces + 1:
            stream.write("f %d %d %d\n" % tuple(f))
    restored = trimesh.load_mesh(path, process=False, maintain_order=True)
    if not (np.array_equal(vertices, restored.vertices) and
            np.array_equal(faces, restored.faces)):
        raise ValueError("export did not preserve coordinates and connectivity")
    return {"vertices": len(vertices), "triangles": len(faces),
            "float64_roundtrip_exact": True, "coordinate_change_source_units": 0.0}


def sampled_deviation(reference, candidate, samples=2000):
    result, maps = {}, {}
    for name, a, b in (("reference_to_candidate", reference, candidate),
                       ("candidate_to_reference", candidate, reference)):
        points, _ = trimesh.sample.sample_surface(a, samples, seed=935)
        _, distance, _ = trimesh.proximity.closest_point(b, points)
        if not np.isfinite(distance).all():
            raise ValueError("nonfinite deviation")
        result[name] = {"samples": samples, "seed": 935,
                        "median_source_units": float(np.median(distance)),
                        "p95_source_units": float(np.percentile(distance, 95)),
                        "sample_max_source_units": float(distance.max())}
        maps[name] = np.column_stack((points, distance))
    result["scope"] = "sampled surface distance; not a certified Hausdorff bound or physical tolerance"
    return result, maps


def run(source, output, contract, candidate=None):
    started = time.monotonic()
    if sha256(source) != EXPECTED_SHA256:
        raise ValueError("unexpected source SHA-256")
    if contract.get("asset_id") != "wolfe-classics-935-cylinder-head":
        raise ValueError("unexpected baseline contract")
    output.mkdir(parents=True, exist_ok=False)
    mesh = trimesh.load_mesh(source, process=False, maintain_order=True)
    report, boundary, labels, main_id = inspect(mesh)
    mask = labels == main_id
    report["main_component_export"] = write_observed_component(
        mesh, mask, output / "observed-main-with-attached-hardware.obj")
    np.save(output / "main-source-face-indices.npy", np.flatnonzero(mask))
    if (~mask).any():
        report["other_components_export"] = write_observed_component(
            mesh, ~mask, output / "observed-other-components.obj")
    # Boundary segments locate gaps; they do not classify a gap as a port.
    np.save(output / "boundary-segments-source-units.npy", mesh.vertices[boundary])
    report["source_sha256"] = EXPECTED_SHA256
    report["units"] = "unverified_OBJ_units"
    report["classification"] = "connected surfaces only; attached hardware not separated"
    report["missing_input_packages"] = [p["id"] for p in contract["input_packages"]
                                         if p["status"] != "complete"]
    report["release"] = {"faithful_cad_validated": False, "solver_ready": False,
                          "print_ready": False, "manufacturing_authorized": False}
    if candidate is not None:
        other = trimesh.load_mesh(candidate, process=False, maintain_order=True)
        main_mesh = mesh.submesh([np.flatnonzero(mask)], append=True, repair=False)
        report["candidate_sha256"] = sha256(candidate)
        report["candidate_deviation"], maps = sampled_deviation(main_mesh, other)
        for name, values in maps.items():
            np.savetxt(output / (name + ".csv"), values, delimiter=",",
                       header="x_source_units,y_source_units,z_source_units,distance_source_units")
    if sha256(source) != EXPECTED_SHA256:
        raise ValueError("source changed during audit")
    report["elapsed_seconds"] = time.monotonic() - started
    report["runtime"] = {"python": platform.python_version(), "numpy": np.__version__,
                         "scipy": scipy.__version__, "trimesh": trimesh.__version__,
                         "machine": platform.machine()}
    (output / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    files = {p.name: sha256(p) for p in sorted(output.iterdir()) if p.is_file()}
    (output / "manifest.json").write_text(json.dumps(files, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--candidate", type=Path)
    args = parser.parse_args()
    result = run(args.source, args.output, json.loads(args.contract.read_text()), args.candidate)
    print(json.dumps({k: result[k] for k in ("triangles", "boundary_edges", "release", "elapsed_seconds")}))
