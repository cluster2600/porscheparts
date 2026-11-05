"""Verify complete old edge stars and four-to-four source contracts before export."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import signal
import time

import numpy as np


PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def module(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def edge_incidence(cells, queries):
    assert np.all(queries[:, 0] < queries[:, 1])
    query_keys = queries[:, 0].astype(np.uint64) * np.uint64(2**32) + queries[:, 1]
    keys = np.unique(query_keys)
    found = np.zeros(len(keys), dtype=np.int64)
    if not len(keys):
        return found
    for start in range(0, len(cells), 50000):
        part = cells[start:start + 50000]
        for a, b in PAIRS:
            values = np.minimum(part[:, a], part[:, b]).astype(np.uint64) * np.uint64(2**32) + np.maximum(part[:, a], part[:, b])
            pos = np.searchsorted(keys, values)
            inside = pos < len(keys)
            pos, values = pos[inside], values[inside]
            np.add.at(found, pos[keys[pos] == values], 1)
    return found[np.searchsorted(keys, query_keys)]


def controls(reference, contract, exact, quality):
    assert sha(reference) == "90ae971f7ff2687c60e3bb9460d5241edeedae3fbaf6f07ad69be08604c36690"
    with np.load(reference, allow_pickle=False) as data:
        nodes, old, known = data["nodes"], data["old_cells"][None], data["reference_cells"][None]
    center, diagonal = np.array([[0, 1]], dtype=np.uint32), np.array([[2, 4]], dtype=np.uint32)
    gain, _, _ = contract.validate(nodes, old, center, diagonal, known, exact, quality)
    assert gain.tolist() == [1]
    assert edge_incidence(old[0], np.vstack((center, diagonal))).tolist() == [4, 0]
    assert edge_incidence(np.vstack((old[0], known[0, :1])), diagonal).tolist() == [1]
    for corruption in (known[:, :, [0, 2, 1, 3]], known[:, [0, 0, 2, 3]]):
        try:
            contract.validate(nodes, old, center, diagonal, corruption, exact, quality)
        except AssertionError:
            pass
        else:
            raise AssertionError("Corrupt four-cell reference accepted")
    return {"frozen_literal_reference_passed": True, "full_star_count_and_absent_edge_controls": True,
        "occupied_new_edge_detected": True, "reversed_and_duplicate_cells_refused": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "mesh", "proposal", "proposal-report", "reference", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--control-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    started = time.monotonic()
    root = args.repository / "docs/research"
    exact = module(root / "935-unoptimized-volume-20261105/source/inspect_interval_volume.py", "retained_four_validation_exact",
        "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71")
    quality = module(root / "935-residual-cavities-20261105/source/verify_two_three.py", "retained_four_validation_quality",
        "a785594fcb77460057824a6fe31c192b2131c7907e535b9e458428bf0b578acb").positive_quality
    contract = module(Path(__file__).with_name("four_four_contract.py"), "four_four_validation_contract",
        "a5379daacb7a099810acf678110b74d4e6d9c5f34b01ac38fff1472a4ab0228c")
    tested = controls(args.reference, contract, exact, quality)
    (args.output / "controls.json").write_text(json.dumps(tested, indent=2) + "\n")
    if args.control_only:
        print(json.dumps(tested), flush=True)
        return
    report = json.loads(args.proposal_report.read_text())
    assert report["source_sha256"] == "4298598e1fc5da3f28ad85fcb41cd5db427f5c5a6418f849b13c5bb07963c236"
    assert sha(args.mesh) == report["mesh_sha256"] == "233f7bd83072772fa0b92d0287f20cec3cf44c4988546be42addf5579630299e"
    assert sha(args.proposal) == report["proposal_sha256"]
    with np.load(args.proposal, allow_pickle=False) as data:
        old_ids, center, diagonal, proposed, gains = (data[name] for name in
            ("old_cell_ids", "old_center_edges", "new_edges", "new_cells", "critical_gains"))
    assert old_ids.shape == (report["packed_disjoint_cavities"], 4)
    assert proposed.shape == (len(old_ids), 4, 4) and center.shape == diagonal.shape == (len(old_ids), 2)
    assert all(value.dtype.kind in "ui" for value in (old_ids, center, diagonal, proposed))
    assert len(np.unique(old_ids)) == old_ids.size and len(np.unique(diagonal, axis=0)) == len(diagonal)
    if not len(old_ids):
        (args.output / "report.json").write_text(json.dumps({"terminal": "no_selected_cavities_no_candidate_exported",
            "controls": tested, "source_sha256": sha(Path(__file__)), "candidate_exported": False,
            "physics_admitted": False, "manufacturing_qualified": False}, indent=2) + "\n")
        return
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, cells, boundary = data["nodes"], data["tets"], data["boundary"]
    assert np.all(old_ids >= 0) and np.all(old_ids < len(cells))
    assert np.all(proposed >= 0) and np.all(proposed < len(nodes))
    incidence = edge_incidence(cells, np.vstack((center, diagonal)))
    assert np.all(incidence[:len(center)] == 4), "Incomplete old edge star"
    assert not incidence[len(center):].any(), "New edge already exists outside the proposed cavity"
    checked = []
    for start in range(0, len(old_ids), 1000):
        gain, _, _ = contract.validate(nodes, cells[old_ids[start:start + 1000]], center[start:start + 1000],
            diagonal[start:start + 1000], proposed[start:start + 1000], exact, quality)
        checked.extend(gain.tolist())
    assert np.array_equal(np.asarray(checked), gains)
    assert int(gains.sum()) == report["predicted_removed_critical_cells"]
    removed = np.zeros(len(cells), dtype=bool)
    removed[old_ids] = True
    candidate_cells = np.vstack((cells[~removed], proposed.reshape(-1, 4)))
    assert len(candidate_cells) == len(cells)
    assert shutil.disk_usage(args.output).free > 4 * 1024**3 + 2 * args.mesh.stat().st_size
    candidate = args.output / "candidate.npz"
    np.savez_compressed(candidate, nodes=nodes, tets=candidate_cells, boundary=boundary)
    with np.load(candidate, allow_pickle=False) as data:
        assert np.array_equal(data["nodes"].view(np.uint64), nodes.view(np.uint64))
        assert np.array_equal(data["boundary"], boundary) and np.array_equal(data["tets"], candidate_cells)
    result = {"source_sha256": sha(Path(__file__)), "contract_sha256": sha(Path(__file__).with_name("four_four_contract.py")),
        "input_mesh_sha256": sha(args.mesh), "proposal_sha256": sha(args.proposal), "candidate_sha256": sha(candidate),
        "terminal": "full_source_star_and_local_domain_contracts_passed_candidate_pending_whole_volume",
        "controls": tested, "cavities_checked": len(old_ids), "old_and_new_cells_each": int(old_ids.size),
        "critical_cells_removed": int(gains.sum()), "old_stars_independently_complete": True,
        "new_edges_globally_absent_and_unique": True, "old_cell_domains_disjoint": True,
        "strict_hull_expected_cell_sets_positive_signs_and_boundary_chains_passed": True,
        "no_reported_quality_bin_increases_in_any_local_cavity": True,
        "all_points_and_boundary_rows_bit_exact": True, "total_cell_count_unchanged": True,
        "shared_source_derived_contract_and_pinned_predicates": True,
        "global_intersection_status_inherited_not_exhaustively_rechecked": True,
        "native_solver_readback_required_for_new_connectivity": True,
        "whole_volume_required": True, "physics_admitted": False, "manufacturing_qualified": False,
        "new_paid_compute_usd": 0, "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    signal.alarm(0)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
