#!/usr/bin/env python3
"""Inventory original and selection-created boundaries without repairing a scan."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np
import scipy
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
COVERAGE = HERE.parent / "scan-coverage-20261029"
REGIONS_SHA = "f6fb9ff814d7ba6eae0441902ae23308f7544fbd3fd3392c89bdbb2e4554add4"
RUN_SHA = "70a4634dd933cbf74a3d388260bee7717496f6f5a06b8b58eef26b34a2d7fea4"
TARGETS = ("FloorLeftSearch", "FloorRightSearch", "CentralRouteSearch")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def edge_table(faces, vertex_count):
    """Use Int64 keys; 32-bit multiplication is unsafe for this scan."""
    f = np.asarray(faces, dtype=np.int64)
    if f.ndim != 2 or f.shape[1] != 3 or vertex_count < 1:
        raise ValueError("Expected triangular faces and a positive vertex count")
    if vertex_count > 3_037_000_499 or (len(f) and (f.min() < 0 or f.max() >= vertex_count)):
        raise ValueError("Source index cannot be encoded safely")
    edges = np.concatenate((f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]))
    lower, upper = edges.min(axis=1), edges.max(axis=1)
    packed = lower * vertex_count + upper
    if not (np.array_equal(packed // vertex_count, lower) and
            np.array_equal(packed % vertex_count, upper)):
        raise ValueError("Edge-key round trip failed")
    keys, counts = np.unique(packed, return_counts=True)
    order = np.argsort(packed, kind="stable")
    sorted_keys = packed[order]
    join = sorted_keys[1:] == sorted_keys[:-1]
    # Consecutive incidents also connect a non-manifold fan without hiding it.
    rows = order[:-1][join] % max(len(f), 1)
    cols = order[1:][join] % max(len(f), 1)
    graph = coo_matrix((np.ones(len(rows), dtype=np.uint8), (rows, cols)),
                       shape=(len(f), len(f))).tocsr()
    components, labels = connected_components(graph, directed=False)
    signs = np.where(edges[:, 0] < edges[:, 1], 1, -1)
    starts = np.r_[0, np.flatnonzero(sorted_keys[1:] != sorted_keys[:-1]) + 1]
    orientation_sum = np.add.reduceat(signs[order], starts) if len(order) else np.array([], dtype=int)
    summary = {
        "unique_edges": int(len(keys)),
        "open_edges": int(np.count_nonzero(counts == 1)),
        "nonmanifold_edges": int(np.count_nonzero(counts > 2)),
        "same_direction_two_face_edges": int(np.count_nonzero((counts == 2) & (orientation_sum != 0))),
        "edge_connected_surface_components": int(components),
    }
    return keys, counts, labels.astype(np.int32), summary


def boundary_graph(edges):
    """Classify topology only; a cycle is not automatically a physical opening."""
    if not len(edges):
        return {"components": 0, "simple_cycles": 0, "other_components": 0}
    vertices, local = np.unique(edges, return_inverse=True)
    local = local.reshape(-1, 2)
    graph = coo_matrix((np.ones(len(local), dtype=np.uint8), (local[:, 0], local[:, 1])),
                       shape=(len(vertices), len(vertices))).tocsr()
    number, labels = connected_components(graph, directed=False)
    degree = np.bincount(local.ravel(), minlength=len(vertices))
    bad = np.unique(labels[degree != 2])
    return {"components": int(number), "simple_cycles": int(number - len(bad)),
            "other_components": int(len(bad))}


def classify_boundary(local_keys, local_counts, source_keys, source_counts, vertex_count):
    keys = local_keys[local_counts == 1]
    slots = np.searchsorted(source_keys, keys)
    if np.any(slots >= len(source_keys)) or not np.array_equal(source_keys[slots], keys):
        raise ValueError("Selected boundary is not in the original source")
    counts = source_counts[slots]
    # 0: original open edge; 1: selection cut; 2: source non-manifold edge.
    origins = np.where(counts == 1, 0, np.where(counts == 2, 1, 2)).astype(np.uint8)
    return np.column_stack((keys // vertex_count, keys % vertex_count)), origins


def run(scan, vertices_path, faces_path, output):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / "work") or output == ROOT / "work" or output.exists():
        raise ValueError("Output must be a new directory under private work/")
    if digest(COVERAGE / "regions.json") != REGIONS_SHA or digest(COVERAGE / "run.json") != RUN_SHA:
        raise ValueError("Frozen search-region evidence changed")
    parent = json.loads((COVERAGE / "run.json").read_text())
    inputs = [(scan, parent["source_sha256"]),
              (vertices_path, parent["input_array_sha256"]["verts_vehicle.npy"]),
              (faces_path, parent["input_array_sha256"]["faces.npy"])]
    for path, expected in inputs:
        if digest(path) != expected:
            raise ValueError("Original scan or registered array hash mismatch")
    vertices = np.load(vertices_path, allow_pickle=False)
    faces = np.load(faces_path, allow_pickle=False)
    if vertices.shape != (parent["source_vertices"], 3) or faces.shape != (parent["source_triangles"], 3):
        raise ValueError("Unexpected admitted array shape")
    if not np.isfinite(vertices).all():
        raise ValueError("Non-finite source vertices")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".boundary-review-", dir=output.parent))
    try:
        keys, counts, labels, source_summary = edge_table(faces, len(vertices))
        sizes = np.bincount(labels)
        source_summary["component_triangle_counts"] = sizes.tolist()
        zero_area = 0
        for start in range(0, len(faces), 100_000):
            p = vertices[faces[start:start + 100_000]].astype(np.float64)
            cross = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
            zero_area += int(np.count_nonzero(np.all(cross == 0, axis=1)))
        source_summary["zero_area_triangles_exact_float64_cross"] = zero_area
        np.save(staging / "source_face_components.npy", labels)
        np.savez(staging / "source_open_edges.npz", source_vertex_ids=np.column_stack(
            (keys[counts == 1] // len(vertices), keys[counts == 1] % len(vertices))))
        config = json.loads((COVERAGE / "regions.json").read_text())
        assigned = np.zeros(len(faces), dtype=bool)
        reports = {}
        for region in config["regions"]:
            bounds = np.asarray(region["bounds"]).reshape(3, 2)
            inside = np.all((vertices >= bounds[:, 0]) & (vertices <= bounds[:, 1]), axis=1)
            selected = np.flatnonzero(np.all(inside[faces], axis=1) & ~assigned).astype(np.int32)
            assigned[selected] = True
            if region["name"] not in TARGETS:
                continue
            expected = parent["groups"][region["name"]]
            ids_digest = hashlib.sha256(selected.astype("<i4").tobytes()).hexdigest()
            if ids_digest != expected["source_face_ids_sha256"]:
                raise ValueError("Search-region source-face correspondence changed")
            local_keys, local_counts, local_labels, local_summary = edge_table(faces[selected], len(vertices))
            edges, origins = classify_boundary(local_keys, local_counts, keys, counts, len(vertices))
            group_labels, group_sizes = np.unique(labels[selected], return_counts=True)
            local_summary.update({
                "triangles": int(len(selected)), "source_face_ids_sha256": ids_digest,
                "boundary_edges": int(len(edges)),
                "source_open_edges": int(np.count_nonzero(origins == 0)),
                "selection_cut_edges": int(np.count_nonzero(origins == 1)),
                "ambiguous_source_nonmanifold_edges": int(np.count_nonzero(origins == 2)),
                "boundary_graph": boundary_graph(edges),
                "local_component_triangle_counts": np.bincount(local_labels).tolist(),
                "source_component_overlap": [
                    {"component": int(label), "region_triangles": int(size),
                     "full_component_triangles": int(sizes[label])}
                    for label, size in zip(group_labels, group_sizes)],
                "physical_boundary_identified": False,
            })
            np.savez(staging / (region["name"] + ".npz"), source_face_ids=selected,
                     source_vertex_ids=edges, boundary_origin=origins,
                     local_face_components=local_labels)
            reports[region["name"]] = local_summary
        report = {
            "classification": "observed_mesh_topology_not_physical_component_segmentation",
            "source_sha256": parent["source_sha256"], "input_array_sha256": parent["input_array_sha256"],
            "regions_sha256": REGIONS_SHA, "parent_run_sha256": RUN_SHA,
            "author_sha256": digest(__file__), "numpy": np.__version__, "scipy": scipy.__version__,
            "source_vertices": int(len(vertices)), "source_triangles": int(len(faces)),
            "source": source_summary, "regions": reports,
            "boundary_origin_encoding": {"0": "original_source_open_edge", "1": "selection_cut_of_two_face_source_edge", "2": "source_nonmanifold_edge"},
            "geometry_modified": False, "physical_segmentation_validated": False,
            "surface_fit_performed": False, "self_intersections_checked": False,
            "vertex_manifoldness_checked": False, "structural_analysis_admitted": False,
            "decision": "Connected-component extraction cannot isolate the floor and central cover: their dominant observations share a source component. Identify physical seams and missing surfaces before structural CAD.",
            "private_outputs_sha256": {p.name: digest(p) for p in sorted(staging.iterdir())},
        }
        (staging / "run.json").write_text(json.dumps(report, indent=2) + "\n")
        staging.rename(output)
        return report
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan", type=Path, required=True)
    parser.add_argument("--vertices", type=Path, required=True)
    parser.add_argument("--faces", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.scan, args.vertices, args.faces, args.output)
    print(json.dumps({"output": str(args.output), "source": result["source"], "regions": result["regions"]}))


if __name__ == "__main__":
    main()
