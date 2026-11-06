"""Independently compare all native OpenFOAM mesh arrays with source tetrahedra.

Supports the actual ASCII vector/face/label lists, including inline small
lists. Checks tetrahedral face incidence and vertex sets; does not establish
native floating-point volume accuracy, field convergence or physical validity.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def values(path, width, dtype, face=False):
    text = path.read_text()
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    assert re.search(r"\bformat\s+ascii\s*;", text)
    tail = text[text.index("}") + 1:]
    header = re.match(r"\s*(\d+)\s*\(", tail, flags=re.S)
    assert header is not None
    count = int(header.group(1))
    body = tail[header.end():tail.rfind(")")]
    result = np.fromstring(body.translate(str.maketrans({"(": " ", ")": " "})), sep=" ", dtype=dtype)
    assert result.size == count * width
    result = result.reshape(count, width)
    if face:
        assert width == 4 and np.all(result[:, 0] == 3)
        result = result[:, 1:].copy()
    return result[:, 0] if width == 1 else result


def canonical(rows):
    rows = np.sort(rows, axis=1)
    order = np.lexsort(tuple(rows[:, i] for i in range(rows.shape[1] - 1, -1, -1)))
    return rows[order]


def inspect(folder, reference):
    with np.load(reference, allow_pickle=False) as data:
        expected_points, expected_cells, expected_boundary = data["nodes"], data["tets"], data["boundary"]
    points = values(folder / "points", 3, np.float64)
    faces = values(folder / "faces", 4, np.int64, face=True)
    owners = values(folder / "owner", 1, np.int64)
    neighbours = values(folder / "neighbour", 1, np.int64)
    assert len(owners) == len(faces) and len(neighbours) <= len(faces)
    assert np.all(faces >= 0) and np.all(faces < len(points))
    assert np.all(faces[:, 0] != faces[:, 1]) and np.all(faces[:, 1] != faces[:, 2]) and np.all(faces[:, 0] != faces[:, 2])
    assert np.all(owners >= 0) and np.all(owners < len(expected_cells))
    assert np.all(neighbours >= 0) and np.all(neighbours < len(expected_cells))
    assert np.all(owners[:len(neighbours)] != neighbours)
    labels = np.concatenate((owners, neighbours))
    assert np.array_equal(np.bincount(labels, minlength=len(expected_cells)), np.full(len(expected_cells), 4))
    order = np.argsort(labels, kind="stable")
    del labels
    face_ids = np.concatenate((np.arange(len(faces)), np.arange(len(neighbours))))
    face_ids = face_ids[order].reshape(len(expected_cells), 4)
    del order
    cell_vertices = faces[face_ids].reshape(len(expected_cells), 12)
    del face_ids
    cell_vertices.sort(axis=1)
    cells = cell_vertices[:, [0, 3, 6, 9]].copy()
    assert np.all(cells[:, 1:] > cells[:, :-1])
    assert np.array_equal(cell_vertices, np.repeat(cells, 3, axis=1))
    del cell_vertices
    exact_points = np.array_equal(points, expected_points)
    exact_cells = np.array_equal(canonical(cells), canonical(expected_cells))
    exact_boundary = np.array_equal(canonical(faces[len(neighbours):]), canonical(expected_boundary))
    return {"points": len(points), "cells": len(cells), "faces": len(faces),
        "internal_faces": len(neighbours), "boundary_faces": len(faces) - len(neighbours),
        "all_coordinates_exact": bool(exact_points), "all_tet_vertex_sets_exact": bool(exact_cells),
        "all_boundary_face_vertex_sets_exact": bool(exact_boundary),
        "all_cells_have_four_faces_and_four_distinct_vertices": True,
        "complete_topological_readback_passed": bool(exact_points and exact_cells and exact_boundary)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("poly-mesh", "reference", "control-poly-mesh", "control-reference", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    assert sha(args.control_reference) == "aa34b174bccae6cef41478a1e84d491b39d82817f5cc34b89ad2dd2a43b55107"
    assert sha(args.reference) == "233f7bd83072772fa0b92d0287f20cec3cf44c4988546be42addf5579630299e"
    control = inspect(args.control_poly_mesh, args.control_reference)
    assert control["complete_topological_readback_passed"] and control["cells"] == 2
    # Ensure a coordinate corruption cannot pass the independent comparison.
    with np.load(args.control_reference, allow_pickle=False) as data:
        corrupt = data["nodes"].copy()
        corrupt[0, 0] = np.nextafter(corrupt[0, 0], np.inf)
        corrupt_path = args.output / "corrupt-control-reference.npz"
        np.savez_compressed(corrupt_path, nodes=corrupt, tets=data["tets"], boundary=data["boundary"])
    corrupt_result = inspect(args.control_poly_mesh, corrupt_path)
    assert not corrupt_result["all_coordinates_exact"] and not corrupt_result["complete_topological_readback_passed"]
    head = inspect(args.poly_mesh, args.reference)
    report = {"source_sha256": sha(Path(__file__)), "reference_sha256": sha(args.reference),
        "native_file_sha256": {name: sha(args.poly_mesh / name) for name in ("points", "faces", "owner", "neighbour")},
        "control": control, "single_coordinate_corruption_refused": True, "head": head,
        "native_face_geometric_orientation_not_independently_checked": True,
        "case_specific_solver_admission": False, "field_solve_executed": False,
        "physics_admitted": False, "manufacturing_qualified": False,
        "new_paid_compute_usd": 0, "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
