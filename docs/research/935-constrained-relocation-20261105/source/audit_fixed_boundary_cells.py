"""Bound every fixed-connectivity interior relocation by boundary-only cells."""
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
    for name in ("source", "source-report", "surface", "inspector", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(300)
    assert sha(args.source) == "b06d28ec39019fa8f91c2e8cd0397c2eb9cd87bf84df7006c8526025aef03450"
    assert sha(args.surface) == "5b04e72b5f7b48f340a39c14009292c52c1bf1ac422ad64cd3250c17ddf51db4"
    assert sha(args.inspector) == "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    upstream = json.loads(args.source_report.read_text())
    assert upstream["mesh_sha256"] == sha(args.source) and upstream["surface_sha256"] == sha(args.surface)
    assert upstream["all_cells_positive_for_stored_binary_coordinates"] and upstream["actual_complete_boundary_and_orientation_exact"]
    spec = importlib.util.spec_from_file_location("retained_fixed_cell_signs", args.inspector)
    exact = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exact)
    exact.controls()
    with np.load(args.source, allow_pickle=False) as source:
        nodes, tets = source["nodes"], source["tets"]
    with np.load(args.surface, allow_pickle=False) as surface:
        vertices = surface["vertices"]
    assert np.array_equal(nodes[:len(vertices)], vertices)
    counts = np.zeros(5, dtype=np.int64)
    bins = {value: np.zeros(5, dtype=np.int64) for value in (.0001, .001, .01, .05, .1)}
    minima = np.full(5, np.inf)
    fallback = 0
    for start in range(0, len(tets), 50000):
        cells = tets[start:start + 50000]
        interior = (cells >= len(vertices)).sum(axis=1)
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
        counts += np.bincount(interior, minlength=5)
        for value in bins:
            bins[value] += np.bincount(interior[quality < value], minlength=5)
        np.minimum.at(minima, interior, quality)
    for value in bins:
        assert int(bins[value].sum()) == upstream["mean_ratio_below"][str(value)]
    assert counts.sum() == len(tets)
    # Independent scalar enumeration checks the vertex partition predicate.
    sample = np.array([[0, 1, 2, 3], [0, 1, 2, 4], [4, 5, 6, 7]])
    assert np.array_equal((sample >= 4).sum(axis=1), [sum(int(v >= 4) for v in row) for row in sample])
    fixed_bad, all_bad = int(bins[.01][0]), int(bins[.01].sum())
    movable_bad = all_bad - fixed_bad
    result = {"source_sha256": sha(Path(__file__)), "input_sha256": sha(args.source),
              "surface_sha256": sha(args.surface), "inspector_sha256": sha(args.inspector),
              "upstream_verdict": "Consistent positive hypothetical raw volume; diagnostic quality failure; no field or physical admission",
              "boundary_vertices": len(vertices), "interior_vertices": len(nodes) - len(vertices),
              "cell_counts_by_number_of_interior_vertices": counts.tolist(),
              "below_bins_by_number_of_interior_vertices": {str(key): value.tolist() for key, value in bins.items()},
              "minimum_quality_by_number_of_interior_vertices": [float(v) if np.isfinite(v) else None for v in minima],
              "exact_positive_fallbacks": fallback, "fixed_boundary_only_cells_below_0p01": fixed_bad,
              "maximum_repairable_below_0p01_by_any_interior_relocation": movable_bad,
              "required_below_0p01_repairs": (all_bad + 1) // 2,
              "optimistic_fixed_target_reachable_by_any_interior_relocation": 2 * movable_bad >= all_bad,
              "bound_requires_fixed_connectivity_and_exact_boundary": True,
              "bound_does_not_exclude_topology_changes_or_other_admission_contracts": True,
              "partition_control_passed": True, "coordinates_modified": False,
              "physics_admitted": False, "manufacturing_qualified": False,
              "new_paid_compute_usd": 0, "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
