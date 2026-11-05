"""Verify both exclusion bounds with the frozen inspector's arithmetic order."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "surface", "proposal", "inspector", "fixed-report", "coverage-report", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(300)
    fixed = json.loads(args.fixed_report.read_text())
    coverage = json.loads(args.coverage_report.read_text())
    assert sha(args.source) == fixed["input_sha256"] == coverage["input_sha256"]
    assert sha(args.proposal) == coverage["proposal_sha256"]
    assert sha(args.inspector) == fixed["inspector_sha256"] == "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    spec = importlib.util.spec_from_file_location("frozen_partition_signs", args.inspector)
    exact = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exact)
    with np.load(args.source, allow_pickle=False) as data:
        nodes, tets = data["nodes"], data["tets"]
    with np.load(args.surface, allow_pickle=False) as data:
        protected = len(data["vertices"])
    with np.load(args.proposal, allow_pickle=False) as data:
        order = np.argsort(data["node_tags"])
        assert np.array_equal(data["node_tags"][order], np.arange(1, len(nodes) + 1))
        moved = np.any(data["coordinates"][order] != nodes, axis=1)
    partitions = {value: np.zeros(5, dtype=np.int64) for value in (.0001, .001, .01, .05, .1)}
    affected = {value: 0 for value in partitions}
    mismatch = {value: 0 for value in partitions}
    minimum = float("inf")
    for start in range(0, len(tets), 50000):
        cells = tets[start:start + 50000]
        xyz = nodes[cells]
        low, high = exact.determinant_interval(xyz)
        determinant = np.einsum("ij,ij->i", xyz[:, 1] - xyz[:, 0], np.cross(xyz[:, 2] - xyz[:, 0], xyz[:, 3] - xyz[:, 0]))
        for i in np.flatnonzero(low <= 0):
            value = exact.exact_determinant(xyz[i])
            assert value > 0
            determinant[i] = float(value)
        assert np.all(determinant > 0)
        volume = determinant / 6
        squared_edges = sum(np.sum((xyz[:, i] - xyz[:, j]) ** 2, axis=1)
                            for i, j in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)))
        reference = 12 * (3 * volume) ** (2 / 3) / squared_edges
        equivalent = 12 * (determinant / 2) ** (2 / 3) / squared_edges
        minimum = min(minimum, float(reference.min()))
        interior = (cells >= protected).sum(axis=1)
        touched = moved[cells].any(axis=1)
        for value in partitions:
            bad = reference < value
            mismatch[value] += int(np.count_nonzero(bad != (equivalent < value)))
            partitions[value] += np.bincount(interior[bad], minlength=5)
            affected[value] += int((bad & touched).sum())
    assert not any(mismatch.values())
    assert {str(k): v.tolist() for k, v in partitions.items()} == fixed["below_bins_by_number_of_interior_vertices"]
    assert {str(k): v for k, v in affected.items()} == coverage["optimistic_repairable_below"]
    result = {"source_sha256": sha(Path(__file__)), "input_sha256": sha(args.source),
              "fixed_report_sha256": sha(args.fixed_report), "coverage_report_sha256": sha(args.coverage_report),
              "tetrahedra_compared": len(tets), "minimum_using_frozen_inspector_arithmetic": minimum,
              "bin_predicate_disagreements": {str(k): v for k, v in mismatch.items()},
              "all_partition_and_coverage_counts_reproduced": True,
              "coordinates_modified": False, "physics_admitted": False, "manufacturing_qualified": False}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
