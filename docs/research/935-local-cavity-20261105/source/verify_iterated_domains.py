"""Verify rebuilt 3-to-2 domains from a previously inspected intermediate.

DE must pierce the strict interior of ABC. Certified signs prove both endpoint
sides and all three barycentric numerator signs. This is independent of the
producer's twelve supporting-halfspace tests. Coordinates remain unchanged.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


PREDICATES = np.array([[0, 1, 2, 3], [0, 1, 3, 4], [0, 1, 4, 2], [2, 3, 4, 0], [2, 3, 4, 1]])


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def piercing(points, exact):
    xyz = points[:, PREDICATES].reshape(-1, 4, 3)
    low, high = exact.determinant_interval(xyz)
    signs = np.where(low > 0, 1, np.where(high < 0, -1, 0)).astype(np.int8)
    ambiguous = np.flatnonzero(signs == 0)
    for i in ambiguous:
        value = exact.exact_determinant(xyz[i])
        signs[i] = (value > 0) - (value < 0)
    signs = signs.reshape(-1, 5)
    barycentric_positive = (signs[:, 0] != 0) & (signs[:, 0] == signs[:, 1]) & (signs[:, 1] == signs[:, 2])
    opposite_endpoints = signs[:, 3] * signs[:, 4] < 0
    return barycentric_positive & opposite_endpoints, len(ambiguous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "source-report", "construction-report", "candidate", "proposal", "inspector", "control", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    started = time.monotonic()
    source_report = json.loads(args.source_report.read_text())
    construction = json.loads(args.construction_report.read_text())
    assert source_report["source_sha256"] == "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    assert source_report["all_cells_positive_for_stored_binary_coordinates"] and source_report["actual_complete_boundary_and_orientation_exact"]
    assert source_report["all_internal_faces_oppositely_oriented"]
    assert sha(args.source) == source_report["mesh_sha256"] == construction["mesh_sha256"]
    assert sha(args.proposal) == construction["proposal_sha256"]
    assert sha(args.candidate) == construction["candidate_sha256"]
    assert sha(args.control) == "2051ab4e59bddb09cc1066f90105144c6c6a0c552c92af4bfc7d5a25b94374b3"
    assert sha(args.inspector) == "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    spec = importlib.util.spec_from_file_location("frozen_local_domain_signs", args.inspector)
    exact = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exact)
    with np.load(args.control, allow_pickle=False) as data:
        control = data["nodes"][[3, 4, 0, 1, 2]][None]
    assert piercing(control, exact)[0].all()
    concave = control.copy()
    concave[0, 0] = control[0, [1, 2, 3, 4]].mean(axis=0)
    assert not piercing(concave, exact)[0].any()
    flat = control.copy()
    flat[0, 0] = control[0, 2]
    assert not piercing(flat, exact)[0].any()
    with np.load(args.source, allow_pickle=False) as data:
        nodes, cells, boundary = data["nodes"], data["tets"].astype(np.uint32), data["boundary"]
    with np.load(args.candidate, allow_pickle=False) as data:
        assert np.array_equal(data["nodes"], nodes) and np.array_equal(data["boundary"], boundary)
        candidate = data["tets"]
    with np.load(args.proposal, allow_pickle=False) as data:
        rows, new_cells, keys = data["old_cell_ids"], data["new_cells"], data["edge_keys"]
    assert rows.shape == (len(keys), 3) and new_cells.shape == (len(keys), 2, 4)
    assert len(np.unique(rows)) == rows.size and rows.max() < len(cells)
    removed = np.zeros(len(cells), dtype=bool)
    removed[rows] = True
    unchanged_count = len(cells) - rows.size
    assert np.array_equal(candidate[:unchanged_count], cells[~removed])
    assert np.array_equal(candidate[unchanged_count:], new_cells.reshape(-1, 4))
    assert len(candidate) == len(cells) - len(keys)
    fallback = 0
    for start in range(0, len(rows), 2000):
        stop = min(start + 2000, len(rows))
        endpoints = np.column_stack((keys[start:stop] // np.uint64(2**32), keys[start:stop] % np.uint64(2**32))).astype(np.uint32)
        old = cells[rows[start:stop]]
        assert np.all((old == endpoints[:, None, 0, None]).sum(axis=2) == 1)
        assert np.all((old == endpoints[:, None, 1, None]).sum(axis=2) == 1)
        keep = (old != endpoints[:, None, 0, None]) & (old != endpoints[:, None, 1, None])
        outer = np.sort(np.where(keep, old, np.iinfo(np.uint32).max).reshape(-1, 12), axis=1)[:, :6]
        assert np.all(outer[:, ::2] == outer[:, 1::2]) and np.all(np.diff(outer[:, ::2].astype(np.int64), axis=1) > 0)
        outer = outer[:, ::2]
        vertices = np.column_stack((endpoints, outer))
        valid, extra = piercing(nodes[vertices], exact)
        assert valid.all(), "Local segment/triangle domain proof failed"
        fallback += extra
        expected = vertices[:, np.array([[2, 3, 4, 0], [2, 3, 4, 1]])]
        actual = np.sort(new_cells[start:stop], axis=2)
        expected = np.sort(expected, axis=2)
        matching = np.all(actual[:, :, None] == expected[:, None], axis=3)
        assert np.all(matching.sum(axis=1) == 1) and np.all(matching.sum(axis=2) == 1)
    result = {"source_sha256": sha(Path(__file__)), "input_sha256": sha(args.source), "candidate_sha256": sha(args.candidate),
              "proposal_sha256": sha(args.proposal), "input_report_sha256": sha(args.source_report), "construction_report_sha256": sha(args.construction_report), "all_node_coordinates_exact": True, "declared_boundary_indices_exact": True,
              "disjoint_original_cell_replacements": len(rows), "every_local_domain_segment_triangle_proof_passed": True,
              "all_unaffected_cells_and_new_cell_mapping_exact": True, "exact_fraction_fallbacks": fallback,
              "geometry_scope": "Each three-cell fan and two-cell replacement partitions the same strict convex bipyramid; unchanged coordinates and outside cells",
              "controls": {"known_convex_patch": True, "concave_patch_refused": True, "coplanar_patch_refused": True},
              "whole_volume_orientation_face_pairing_and_quality_still_required": True,
              "physics_admitted": False, "manufacturing_qualified": False, "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
