"""Compare every native face winding to certified positive source tetrahedra.

This is an exact integer permutation test, distinct from floating-point native
face areas, cell centres and volume formulas. It preserves all geometry.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def mapping(faces, owners, neighbours, source):
    labels = np.concatenate((owners, neighbours))
    assert np.array_equal(np.bincount(labels, minlength=len(source)), np.full(len(source), 4))
    order = np.argsort(labels, kind="stable")
    del labels
    face_ids = np.concatenate((np.arange(len(faces)), np.arange(len(neighbours))))
    face_ids = face_ids[order].reshape(len(source), 4)
    del order
    vertices = faces[face_ids].reshape(len(source), 12)
    del face_ids
    vertices.sort(axis=1)
    native = vertices[:, [0, 3, 6, 9]].copy()
    assert np.all(native[:, 1:] > native[:, :-1])
    assert np.array_equal(vertices, np.repeat(native, 3, axis=1))
    del vertices
    canonical = np.sort(source, axis=1)
    source_order = np.lexsort(tuple(canonical[:, k] for k in (3, 2, 1, 0)))
    native_order = np.lexsort(tuple(native[:, k] for k in (3, 2, 1, 0)))
    ordered = canonical[source_order]
    assert np.all(np.any(ordered[1:] != ordered[:-1], axis=1)), "Duplicate source cells"
    assert np.array_equal(ordered, native[native_order]), "Native/source cell sets differ"
    result = np.empty(len(source), dtype=np.int64)
    result[native_order] = source_order
    return result


def errors(faces, labels, source, row_map, outward):
    wrong = []
    for first in range(0, len(labels), 131072):
        last = min(first + 131072, len(labels))
        tetrahedra = source[row_map[labels[first:last]]]
        match = faces[first:last, :, None] == tetrahedra[:, None, :]
        assert np.all(match.sum(axis=2) == 1), "Face not in reference cell"
        positions = match.argmax(axis=2)
        assert np.all(positions[:, 0] != positions[:, 1])
        assert np.all(positions[:, 1] != positions[:, 2])
        assert np.all(positions[:, 0] != positions[:, 2])
        permutation = np.column_stack((6 - positions.sum(axis=1), positions))
        parity = np.zeros(last - first, dtype=bool)
        for i in range(4):
            for j in range(i + 1, 4):
                parity ^= permutation[:, i] > permutation[:, j]
        # [opposite vertex, face vertices] has even parity for an outward
        # face of a positively oriented tetrahedron; the neighbour is inward.
        bad = parity if outward else ~parity
        wrong.append(np.flatnonzero(bad) + first)
    return np.concatenate(wrong)


def inspect(folder, reference, reader):
    with np.load(reference, allow_pickle=False) as data:
        source = data["tets"]
    faces = reader.values(folder / "faces", 4, np.int64, face=True)
    owners = reader.values(folder / "owner", 1, np.int64)
    neighbours = reader.values(folder / "neighbour", 1, np.int64)
    assert len(owners) == len(faces) and len(neighbours) <= len(faces)
    assert np.all(owners >= 0) and np.all(owners < len(source))
    assert np.all(neighbours >= 0) and np.all(neighbours < len(source))
    row_map = mapping(faces, owners, neighbours, source)
    owner_bad = errors(faces, owners, source, row_map, True)
    neighbour_bad = errors(faces[:len(neighbours)], neighbours, source, row_map, False)
    assert np.array_equal(owner_bad[owner_bad < len(neighbours)], neighbour_bad)
    return faces, owners, neighbours, source, row_map, owner_bad, neighbour_bad


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("parent", "reference", "positive-report", "reader", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    assert sha(args.parent / "manifest.json") == "91fbc0ecc6dfdeb2b95949676698f0ea9a1a8605d783efdfa61e2fe3722ed64d"
    assert sha(args.reference) == "233f7bd83072772fa0b92d0287f20cec3cf44c4988546be42addf5579630299e"
    assert sha(args.positive_report) == "2534890f0c46caaa8394320fa03a8d60057c842d97238dfa57b4cb816c20e596"
    positive = json.loads(args.positive_report.read_text())
    assert positive["mesh_sha256"] == sha(args.reference)
    assert positive["all_cells_positive_for_stored_binary_coordinates"]
    assert positive["all_internal_faces_oppositely_oriented"]
    assert sha(args.reader) == "fbcd4fc8dddb319aeff88131c678e26ccba6ae97decb988fcc185872c67644ae"
    spec = importlib.util.spec_from_file_location("frozen_winding_reader", args.reader)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    args.output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    control_reference = args.parent / "ascii-control/precision-control.npz"
    assert sha(control_reference) == "aa34b174bccae6cef41478a1e84d491b39d82817f5cc34b89ad2dd2a43b55107"
    native = args.parent / "cloud-import-001/recovered"
    manifest = {row["path"]: row["sha256"] for row in json.loads((args.parent / "manifest.json").read_text())["files"]}
    for name in ("points", "faces", "owner", "neighbour"):
        path = native / "control/constant/polyMesh" / name
        assert sha(path) == manifest[str(path.relative_to(args.parent))]
    assert sha(args.parent / "independent-foam/report.json") == manifest["independent-foam/report.json"]
    faces, owners, neighbours, source, row_map, a, b = inspect(native / "control/constant/polyMesh", control_reference, reader)
    assert len(a) == len(b) == 0
    corrupted = faces.copy()
    corrupted[0, [0, 1]] = corrupted[0, [1, 0]]
    assert np.array_equal(errors(corrupted, owners, source, row_map, True), np.array([0]))
    assert np.array_equal(errors(corrupted[:len(neighbours)], neighbours, source, row_map, False), np.array([0]))
    del faces, owners, neighbours, source, row_map
    folder = native / "head/constant/polyMesh"
    witness = json.loads((args.parent / "independent-foam/report.json").read_text())
    for name, expected in witness["native_file_sha256"].items():
        assert sha(folder / name) == expected
    faces, owners, neighbours, source, row_map, owner_bad, neighbour_bad = inspect(folder, args.reference, reader)
    private = args.output / "private-native-face-winding-errors.npz"
    np.savez_compressed(private, owner_bad_faces=owner_bad, neighbour_bad_faces=neighbour_bad,
        owner_cells=owners[owner_bad], neighbour_cells=neighbours[neighbour_bad])
    report = {"source_sha256": sha(Path(__file__)), "reference_sha256": sha(args.reference),
        "positive_report_sha256": sha(args.positive_report), "native_file_sha256": witness["native_file_sha256"],
        "native_cells": len(source), "all_native_cell_sets_mapped_bijectively_to_unique_source_cells": True,
        "native_cell_order_matches_source": bool(np.array_equal(row_map, np.arange(len(source)))),
        "owner_face_windings_checked": len(owners), "neighbour_face_windings_checked": len(neighbours),
        "owner_winding_errors": len(owner_bad), "neighbour_winding_errors": len(neighbour_bad),
        "boundary_winding_errors": int(np.count_nonzero(owner_bad >= len(neighbours))),
        "internal_owner_neighbour_error_sets_identical": True,
        "complete_combinatorial_winding_passed": len(owner_bad) == len(neighbour_bad) == 0,
        "control_positive_passed": True, "single_reversed_control_face_rejected_for_both_incident_cells": True,
        "predicate": "Integer permutation parity relative to certified positive source tetrahedra; no floating face areas or cell centres",
        "native_geometry_formula_accuracy_not_established": True,
        "private_error_indices_sha256": sha(private), "geometry_or_connectivity_modified": False,
        "field_solve_executed": False, "physics_admitted": False, "manufacturing_qualified": False,
        "new_paid_compute_usd": 0, "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
