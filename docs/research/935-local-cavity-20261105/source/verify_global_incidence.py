"""Independently verify sparse cavity recovery by sorting every source edge."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def full_index(cells):
    keys = np.empty((len(cells), 6), dtype=np.uint64)
    for slot, (left, right) in enumerate(PAIRS):
        a, b = cells[:, left], cells[:, right]
        keys[:, slot] = np.minimum(a, b).astype(np.uint64) * np.uint64(2**32) + np.maximum(a, b).astype(np.uint64)
    keys = keys.ravel()
    order = np.argsort(keys, kind="stable")
    ordered = keys[order]
    starts = np.r_[0, np.flatnonzero(ordered[1:] != ordered[:-1]) + 1]
    return ordered[starts], starts, np.diff(np.r_[starts, len(ordered)]), order


def controls(producer):
    fixture = np.array([[3, 4, 0, 1], [3, 4, 1, 2], [3, 4, 2, 0]], dtype=np.uint32)
    repeated = np.tile(fixture, (16668, 1))
    selected = np.unique(producer.edges(fixture).ravel())
    counts, first = producer.incidence(repeated, selected)
    values, starts, actual, order = full_index(repeated)
    assert np.array_equal(values, selected) and np.array_equal(counts, actual)
    for i in range(len(values)):
        expected = order[starts[i]:starts[i] + min(3, actual[i])] // 6
        assert np.array_equal(first[i, :len(expected)], expected)
    cyclic = {tuple(sorted(row)) for row in fixture.tolist()}
    assert cyclic == {(0, 1, 3, 4), (1, 2, 3, 4), (0, 2, 3, 4)}
    fan = np.array([[4, 5, 0, 1], [4, 5, 1, 2], [4, 5, 2, 3]], dtype=np.uint32)
    assert len(np.unique(fixture)) == 5 and len(np.unique(fan)) == 6
    return {"full_sort_matches_sparse_counting_across_50000_cell_boundary": True,
            "first_three_incident_ids_match_across_chunks": True,
            "closed_cycle_and_open_fan_have_distinct_links": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh", "coverage-report", "cache", "producer", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    started = time.monotonic()
    report = json.loads(args.coverage_report.read_text())
    assert sha(args.mesh) == report["mesh_sha256"] == "b06d28ec39019fa8f91c2e8cd0397c2eb9cd87bf84df7006c8526025aef03450"
    assert sha(args.cache) == report["private_cavity_cache_sha256"]
    assert sha(args.producer) == report["source_sha256"]
    spec = importlib.util.spec_from_file_location("retained_sparse_cavity_counter", args.producer)
    producer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(producer)
    tests = controls(producer)
    with np.load(args.mesh, allow_pickle=False) as data:
        cells = data["tets"].astype(np.uint32)
    with np.load(args.cache, allow_pickle=False) as data:
        cached_keys, cached_cells, cached_outer, bad_ids = (data[key] for key in ("edge_keys", "cell_ids", "outer_vertices", "bad_cell_ids"))
    assert np.all(np.diff(bad_ids.astype(np.int64)) > 0) and len(bad_ids) == report["bad_cells"]
    print(json.dumps({"stage": "independent_all_edge_sort", "edge_occurrences": 6 * len(cells)}), flush=True)
    values, starts, counts, order = full_index(cells)
    selected = np.unique(producer.edges(cells[bad_ids]).ravel())
    positions = np.searchsorted(values, selected)
    assert np.array_equal(values[positions], selected)
    keys, frequencies = np.unique(counts[positions], return_counts=True)
    assert {str(int(k)): int(v) for k, v in zip(keys, frequencies)} == report["selected_edge_valence_histogram"]
    degree_three = positions[counts[positions] == 3]
    all_rows = (order[starts[degree_three, None] + np.arange(3)] // 6).astype(np.uint32)
    edge_keys = values[degree_three]
    endpoints = np.column_stack((edge_keys // np.uint64(2**32), edge_keys % np.uint64(2**32))).astype(np.uint32)
    patch = cells[all_rows]
    keep = (patch != endpoints[:, None, 0, None]) & (patch != endpoints[:, None, 1, None])
    outer = np.sort(np.where(keep, patch, np.iinfo(np.uint32).max).reshape(-1, 12), axis=1)[:, :6]
    closed = np.all(outer[:, ::2] == outer[:, 1::2], axis=1) & np.all(np.diff(outer[:, ::2].astype(np.int64), axis=1) > 0, axis=1)
    assert np.array_equal(edge_keys[closed], cached_keys)
    assert np.array_equal(np.sort(all_rows[closed], axis=1), np.sort(cached_cells, axis=1))
    assert np.array_equal(outer[closed][:, ::2], cached_outer)
    covered = np.unique(all_rows[closed].ravel())
    assert len(np.intersect1d(covered, bad_ids, assume_unique=True)) == report["optimistically_repairable_bad_cells"]
    hashes = {}
    for name, value in (("edge_keys", values), ("edge_starts", starts), ("edge_counts", counts), ("edge_order", order)):
        path = args.output / ("private-" + name + ".npy")
        np.save(path, value)
        hashes[path.name] = sha(path)
    result = {"source_sha256": sha(Path(__file__)), "mesh_sha256": sha(args.mesh), "coverage_report_sha256": sha(args.coverage_report),
              "cache_sha256": sha(args.cache), "all_source_edge_occurrences": 6 * len(cells), "distinct_source_edges": len(values),
              "selected_edge_counts_and_histogram_match": True, "every_closed_cavity_key_cells_and_link_match": True,
              "all_optimistic_coverage_counts_reproduced": True, "controls": tests, "global_index_sha256": hashes,
              "coordinates_modified": False, "physics_admitted": False, "manufacturing_qualified": False,
              "new_paid_compute_usd": 0, "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
