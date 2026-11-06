"""Bound the quality-bin benefit of reusing a rejected relocation proposal.

Only original cell coordinates are admitted. Native output supplies proposed
interior target positions, never an accepted mesh. A cell with no moved vertex
cannot change its quality under any clipping of those proposed displacements.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "source-report", "surface", "proposal", "inspector", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(300)
    assert sha(args.source) == "b06d28ec39019fa8f91c2e8cd0397c2eb9cd87bf84df7006c8526025aef03450"
    assert sha(args.proposal) == "65b77a5b91e220a242a8e78262ff41f9190a5ee6012c790ad6c37f249beb4521"
    assert sha(args.inspector) == "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    upstream = json.loads(args.source_report.read_text())
    assert upstream["mesh_sha256"] == sha(args.source)
    assert upstream["all_cells_positive_for_stored_binary_coordinates"]
    assert upstream["all_internal_faces_oppositely_oriented"]
    assert upstream["actual_complete_boundary_and_orientation_exact"]
    spec = importlib.util.spec_from_file_location("retained_coverage_signs", args.inspector)
    exact = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exact)
    exact.controls()
    with np.load(args.source, allow_pickle=False) as source:
        nodes, tets, boundary = (source[key] for key in ("nodes", "tets", "boundary"))
    with np.load(args.surface, allow_pickle=False) as surface:
        vertices = surface["vertices"]
    assert np.array_equal(nodes[:len(vertices)], vertices)
    with np.load(args.proposal, allow_pickle=False) as raw:
        tags = raw["node_tags"]
        order = np.argsort(tags)
        assert np.array_equal(tags[order], np.arange(1, len(nodes) + 1))
        targets = raw["coordinates"][order]
        assert targets.shape == nodes.shape and np.isfinite(targets).all()
        assert np.array_equal(raw["face_node_tags"], boundary + 1)
        native_tets = raw["cell_node_tags"]
        assert native_tets.shape == tets.shape
        for start in range(0, len(tets), 50000):
            assert np.array_equal(native_tets[start:start + 50000], tets[start:start + 50000] + 1)
    moved = np.any(nodes != targets, axis=1)
    assert not moved[:len(vertices)].any()
    bins = {value: 0 for value in (.0001, .001, .01, .05, .1)}
    affected_bins = {value: 0 for value in bins}
    quality_minimum = float("inf")
    fallback = 0
    affected_total = 0
    for start in range(0, len(tets), 50000):
        cells = tets[start:start + 50000]
        xyz = nodes[cells]
        low, high = exact.determinant_interval(xyz)
        determinant = np.einsum("ij,ij->i", xyz[:, 1] - xyz[:, 0], np.cross(xyz[:, 2] - xyz[:, 0], xyz[:, 3] - xyz[:, 0]))
        for i in np.flatnonzero(low <= 0):
            value = exact.exact_determinant(xyz[i])
            assert value > 0
            determinant[i] = float(value)
            fallback += 1
        assert np.all(determinant > 0)
        squared_edges = sum(np.sum((xyz[:, i] - xyz[:, j]) ** 2, axis=1)
                            for i, j in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)))
        quality = 12 * (determinant / 2) ** (2 / 3) / squared_edges
        affected = moved[cells].any(axis=1)
        affected_total += int(affected.sum())
        quality_minimum = min(quality_minimum, float(quality.min()))
        for value in bins:
            bad = quality < value
            bins[value] += int(bad.sum())
            affected_bins[value] += int((bad & affected).sum())
    assert {str(key): value for key, value in bins.items()} == upstream["mean_ratio_below"]
    # All four slots, shared vertices and a stationary cell are covered.
    probe_cells = np.array([[0, 1, 2, 3], [1, 2, 3, 4], [0, 4, 5, 6]])
    probe_moved = np.array([False, False, False, True, False, False, False])
    assert np.array_equal(probe_moved[probe_cells].any(axis=1), [True, True, False])
    required = (bins[.01] + 1) // 2
    result = {"source_sha256": sha(Path(__file__)), "input_sha256": sha(args.source),
              "proposal_sha256": sha(args.proposal), "inspector_sha256": sha(args.inspector),
              "upstream_verdict": "Positive consistent raw input; hypothetical envelope and volume shape-quality failure retained; rejected proposal used only as displacement targets",
              "moved_vertices": int(moved.sum()), "protected_vertices_moved": 0,
              "tetrahedra": len(tets), "affected_cells": affected_total,
              "source_minimum_mean_ratio": quality_minimum, "exact_positive_fallbacks": fallback,
              "source_below": {str(key): value for key, value in bins.items()},
              "optimistic_repairable_below": {str(key): value for key, value in affected_bins.items()},
              "required_below_0p01_repairs": required,
              "optimistic_fixed_target_reachable": affected_bins[.01] >= required,
              "bound_ignores_feasibility_and_new_bad_cells": True,
              "coverage_controls_passed": True, "coordinates_modified": False,
              "physics_admitted": False, "manufacturing_qualified": False,
              "new_paid_compute_usd": 0, "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
