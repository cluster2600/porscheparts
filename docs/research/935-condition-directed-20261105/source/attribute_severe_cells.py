"""Attribute every severe cell to current surface constraints and construction tags.

Tag zero denotes retained parent-envelope skin, not acquired specimen identity.
Positive tags denote assumed cut caps, not measured engine interfaces.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


FACES = np.array([[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]])


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def surface_join(cells, surface, tags, vertex_count, records):
    query, inverse = np.unique(records(np.sort(cells[:, FACES].reshape(-1, 3), axis=1)), return_inverse=True)
    match = np.full(len(query), -1, dtype=np.int64)
    boundary_vertex = np.zeros(vertex_count, dtype=bool)
    skin_vertex = np.zeros(vertex_count, dtype=bool)
    cap_membership = np.zeros(vertex_count, dtype=np.uint64)
    assert tags.shape == (len(surface),) and tags.min() >= 0 and tags.max() <= 63
    for start in range(0, len(surface), 50000):
        faces = surface[start:start + 50000]
        labels = tags[start:start + len(faces)]
        boundary_vertex[faces] = True
        skin_vertex[faces[labels == 0]] = True
        for label in np.unique(labels[labels > 0]):
            np.bitwise_or.at(cap_membership, faces[labels == label].ravel(), np.uint64(1) << np.uint64(label - 1))
        values = records(np.sort(faces, axis=1))
        positions = np.searchsorted(query, values)
        within = positions < len(query)
        source_rows = np.flatnonzero(within)
        positions, values = positions[within], values[within]
        equal = query[positions] == values
        found = positions[equal]
        assert len(np.unique(found)) == len(found) and np.all(match[found] < 0), "Duplicate matched source boundary face"
        match[found] = start + source_rows[equal]
    source_rows = match[inverse].reshape(-1, 4)
    source_tags = np.full(source_rows.shape, -1, dtype=np.int64)
    found = source_rows >= 0
    source_tags[found] = tags[source_rows[found]]
    return source_rows, source_tags, boundary_vertex[cells], skin_vertex[cells], cap_membership[cells]


def controls(records):
    # Synthetic one-cell boundary: two retained triangles and two assumed caps.
    cells = np.array([[0, 1, 2, 3]], dtype=np.uint32)
    surface = cells[:, FACES].reshape(-1, 3)
    tags = np.array([0, 0, 1, 1])
    rows, labels, on_boundary, on_skin, caps = surface_join(cells, surface, tags, 4, records)
    assert rows.tolist() == [[0, 1, 2, 3]] and labels.tolist() == [[0, 0, 1, 1]]
    assert on_boundary.all() and on_skin.sum() == 4 and (caps > 0).sum() == 4
    assert np.bitwise_and.reduce(caps, axis=1).tolist() == [1]
    # A cell with a new fifth vertex cannot falsely acquire a complete boundary.
    rows2 = surface_join(np.array([[0, 1, 2, 4]], dtype=np.uint32), surface, tags, 5, records)[0]
    assert (rows2 >= 0).sum() == 1
    return {"literal_face_to_tag_join_passed": True,
        "tag_incidence_not_assumed_coplanarity": True, "absent_faces_not_assigned": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "parent", "surface-parent", "condition-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600)
    started = time.monotonic()
    path = args.repository / "docs/research/935-local-physics-20261105/source/inspect_tetrahedra.py"
    assert sha(path) == "fe8c7fa88f35d2d14094438bbae3b0860bde085a39b68f7ab941790cb4d1bec3"
    spec = importlib.util.spec_from_file_location("condition_surface_record_contract", path)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    tested = controls(helper.records)
    assert sha(args.parent / "manifest.json") == "70ea643568877eb271a0ec379950d8e1230fe9f6947d17c8876a4b02900a60b4"
    assert sha(args.surface_parent / "manifest.json") == "3d23346c1d874be4fed6f58ce3164f00c8e6fab066caef033f5eacb005bfc3c2"
    expected = {row["path"]: row["sha256"] for row in json.loads((args.surface_parent / "manifest.json").read_text())["files"]}
    for name in ("regularization-001/candidate.npz", "regularization-001/candidate-tags.npy"):
        assert sha(args.surface_parent / name) == expected[name]
    mesh = args.parent / "local-proof/candidate.npz"
    assert sha(mesh) == "62717026bdfc3dc9c1a6cde682b32db12900cad8460f158a7319c41d001e2462"
    condition = json.loads((args.condition_root / "report.json").read_text())
    assert condition["source_sha256"] == "0e3ba938b3e575f02b3b35c47f79b64b0fffb015de3acc6709827747cce279ca"
    assert condition["input_mesh_sha256"] == sha(mesh)
    assert sha(args.condition_root / "private-severe-ids.npz") == condition["private_ids_sha256"]
    with np.load(mesh, allow_pickle=False) as data:
        nodes, all_cells = data["nodes"], data["tets"]
    with np.load(args.surface_parent / "regularization-001/candidate.npz", allow_pickle=False) as data:
        vertices, surface = data["vertices"], data["triangles"]
    assert np.array_equal(nodes[:len(vertices)].view(np.uint64), vertices.view(np.uint64))
    tags = np.load(args.surface_parent / "regularization-001/candidate-tags.npy", allow_pickle=False)
    with np.load(args.condition_root / "private-severe-ids.npz", allow_pickle=False) as data:
        ids = data["cell_ids"]
    assert len(ids) == condition["exact_condition_values"] and np.all(ids < len(all_cells))
    cells = all_cells[ids]
    rows, labels, on_boundary, on_skin, cap_membership = surface_join(cells, surface, tags, len(nodes), helper.records)
    boundary_count = (rows >= 0).sum(axis=1)
    interior_count = (~on_boundary).sum(axis=1)
    cap_vertex_count = (cap_membership > 0).sum(axis=1)
    common_cap = np.bitwise_and.reduce(cap_membership, axis=1)
    by_shared_cap = {}
    for tag in np.unique(tags[tags > 0]):
        bit = np.uint64(1) << np.uint64(tag - 1)
        by_shared_cap[str(int(tag))] = int(((common_cap & bit) != 0).sum())
    matched = labels[labels >= 0]
    tag_values, tag_counts = np.unique(matched, return_counts=True)
    private = args.output / "private-cell-surface-attribution.npz"
    np.savez_compressed(private, cell_ids=ids, source_boundary_face_ids=rows, construction_tags=labels,
        vertex_cap_memberships=cap_membership, common_cap_memberships=common_cap,
        boundary_face_count=boundary_count, interior_vertex_count=interior_count)
    result = {"source_sha256": sha(Path(__file__)), "input_mesh_sha256": sha(mesh),
        "severe_ids_sha256": condition["private_ids_sha256"], "severe_cells_checked": len(ids),
        "source_surface_faces_scanned": len(surface), "source_surface_sha256": sha(args.surface_parent / "regularization-001/candidate.npz"),
        "source_tags_sha256": sha(args.surface_parent / "regularization-001/candidate-tags.npy"),
        "cells_by_actual_boundary_face_count_0_to_4": np.bincount(boundary_count, minlength=5).tolist(),
        "cells_by_interior_vertex_count_0_to_4": np.bincount(interior_count, minlength=5).tolist(),
        "cells_by_cap_incident_vertex_count_0_to_4": np.bincount(cap_vertex_count, minlength=5).tolist(),
        "matched_boundary_faces_by_construction_tag": {str(int(k)): int(v) for k, v in zip(tag_values, tag_counts)},
        "cells_with_any_cap_face": int(np.any(labels > 0, axis=1).sum()),
        "cells_with_any_parent_skin_face": int(np.any(labels == 0, axis=1).sum()),
        "cells_all_four_vertices_incident_to_one_common_cap_tag": int((common_cap != 0).sum()),
        "common_cap_cell_counts_by_tag": by_shared_cap,
        "cells_all_vertices_incident_to_parent_skin": int(on_skin.all(axis=1).sum()),
        "tag_zero_is_parent_envelope_not_acquired_scan_identity": True,
        "cap_membership_does_not_prove_exact_coplanarity_or_physical_interface_identity": True,
        "controls": tested, "private_attribution_sha256": sha(private),
        "geometry_or_connectivity_modified": False, "field_solve_executed": False,
        "physics_admitted": False, "manufacturing_qualified": False,
        "new_paid_compute_usd": 0, "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
