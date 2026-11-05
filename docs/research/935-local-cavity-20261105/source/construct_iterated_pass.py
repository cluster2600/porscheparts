"""Rebuild a convex 3-to-2 pass from an independently inspected intermediate."""
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


def module(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh", "mesh-report", "original", "surface", "core-dir", "inspector", "control", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--iteration", type=int, choices=(2, 3), required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    started = time.monotonic()
    assert sha(args.original) == "b06d28ec39019fa8f91c2e8cd0397c2eb9cd87bf84df7006c8526025aef03450"
    assert sha(args.surface) == "5b04e72b5f7b48f340a39c14009292c52c1bf1ac422ad64cd3250c17ddf51db4"
    report = json.loads(args.mesh_report.read_text())
    assert report["source_sha256"] == "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    assert report["mesh_sha256"] == sha(args.mesh) and report["surface_sha256"] == sha(args.surface)
    assert report["all_cells_positive_for_stored_binary_coordinates"] and report["actual_complete_boundary_and_orientation_exact"]
    assert report["all_internal_faces_oppositely_oriented"] and report["all_nodes_used"]
    geom = module(args.core_dir / "assess_initial_cavities.py", "retained_iterated_geometry", "ee60f26e2449fc2da97e34b0fa3f67c5472e0902b8a4166210e2089624887aa6")
    edge = module(args.core_dir / "audit_cavity_coverage.py", "retained_iterated_edges", "2b6faced01ab3182a5bab28f1955ac834a01c6b9a6d0bd41e21bd281cc3728fb")
    indexer = module(args.core_dir / "verify_global_incidence.py", "retained_iterated_index", "2d3d3b44ea5e055b3600231d935bed280197b33cc4400ee0553d826cc239d4f8")
    exact = module(args.inspector, "retained_iterated_exact", "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71")
    controls = geom.controls(args.control, exact)
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, cells, boundary = data["nodes"], data["tets"].astype(np.uint32), data["boundary"]
    with np.load(args.original, allow_pickle=False) as data:
        assert np.array_equal(nodes, data["nodes"]) and np.array_equal(boundary, data["boundary"])
    plan = {"source_sha256": sha(Path(__file__)), "mesh_sha256": sha(args.mesh), "input_report_sha256": sha(args.mesh_report),
            "original_mesh_sha256": sha(args.original), "iteration": args.iteration, "maximum_declared_passes": 3,
            "cumulative_reference_bad_cells": 526110, "cumulative_target_bad_cell_limit": 263055,
            "upstream_verdict": "Preceding local domains and complete independent cell/boundary/face inspection pass; shape and physical gates remain open",
            "node_motion_allowed": False, "strict_convexity_and_exact_boundary_chain_required": True,
            "minimum_quality_must_not_worsen": True, "ultra_low_bin_must_not_increase": .0001,
            "every_accepted_cavity_must_reduce_bad_bin": .01, "new_paid_compute_usd": 0,
            "physics_admitted": False, "manufacturing_qualified": False}
    (args.output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    bad = np.zeros(len(cells), dtype=bool)
    bins = {value: 0 for value in (.0001, .001, .01, .05, .1)}
    for start in range(0, len(cells), 50000):
        q, signs, _ = geom.quality(nodes[cells[start:start + 50000]], exact)
        assert np.all(signs > 0)
        bad[start:start + len(q)] = q < .01
        for value in bins:
            bins[value] += int((q < value).sum())
    assert {str(k): v for k, v in bins.items()} == report["mean_ratio_below"]
    assert bad.sum() > 263055, "Cumulative target already reached"
    index = indexer.full_index(cells)
    values, starts, counts, order = index
    selected = np.unique(edge.edges(cells[bad]).ravel())
    positions = np.searchsorted(values, selected)
    assert np.array_equal(values[positions], selected)
    degree_three = positions[counts[positions] == 3]
    rows = (order[starts[degree_three, None] + np.arange(3)] // 6).astype(np.uint32)
    keys = values[degree_three]
    endpoints = np.column_stack((keys // np.uint64(2**32), keys % np.uint64(2**32))).astype(np.uint32)
    vertices = cells[rows]
    keep = (vertices != endpoints[:, None, 0, None]) & (vertices != endpoints[:, None, 1, None])
    outer = np.sort(np.where(keep, vertices, np.iinfo(np.uint32).max).reshape(-1, 12), axis=1)[:, :6]
    closed = np.all(outer[:, ::2] == outer[:, 1::2], axis=1) & np.all(np.diff(outer[:, ::2].astype(np.int64), axis=1) > 0, axis=1)
    rows, keys, outer, endpoints = rows[closed], keys[closed], outer[closed][:, ::2], endpoints[closed]
    feasible = np.zeros(len(rows), dtype=bool)
    proposed = np.empty((len(rows), 2, 4), dtype=np.uint32)
    gains = np.zeros(len(rows), dtype=np.int64)
    for start in range(0, len(rows), 2000):
        stop = min(start + 2000, len(rows))
        vertex_ids = np.column_stack((endpoints[start:stop], outer[start:stop]))
        convex, _ = geom.convex(nodes[vertex_ids], exact)
        replacement = vertex_ids[:, geom.ALTERNATIVE].copy()
        q_new, signs, _ = geom.quality(nodes[replacement].reshape(-1, 4, 3), exact)
        flat = replacement.reshape(-1, 4)
        flat[signs < 0] = flat[signs < 0][:, [0, 2, 1, 3]]
        q_new = q_new.reshape(-1, 2)
        old = cells[rows[start:stop]]
        q_old, old_signs, _ = geom.quality(nodes[old].reshape(-1, 4, 3), exact)
        assert np.all(old_signs > 0)
        q_old = q_old.reshape(-1, 3)
        assert np.array_equal(q_old < .01, bad[rows[start:stop]])
        gain = (q_old < .01).sum(axis=1) - (q_new < .01).sum(axis=1)
        quality = (q_new.min(axis=1) >= q_old.min(axis=1)) & (gain > 0)
        quality &= (q_new < .0001).sum(axis=1) <= (q_old < .0001).sum(axis=1)
        quality &= np.all(signs.reshape(-1, 2) != 0, axis=1)
        absent = ~geom.existing_face(outer[start:stop], cells, index)
        feasible[start:stop] = convex & quality & absent & geom.boundary_chain_equal(old, replacement)
        proposed[start:stop], gains[start:stop] = replacement, gain
    eligible = np.flatnonzero(feasible)
    packed, conflicts, duplicate_faces = geom.pack(rows[eligible], outer[eligible], gains[eligible], keys[eligible], len(cells))
    packed = eligible[packed]
    if not len(packed):
        (args.output / "report.json").write_text(json.dumps({**plan, "terminal": "no_admissible_moves", "candidate_exported": False}, indent=2) + "\n")
        return
    old_ids, new_cells = rows[packed], proposed[packed]
    assert len(np.unique(old_ids)) == old_ids.size
    removed = np.zeros(len(cells), dtype=bool)
    removed[old_ids] = True
    result = np.vstack((cells[~removed], new_cells.reshape(-1, 4)))
    assert len(result) == len(cells) - len(packed)
    proposal = args.output / "proposal.npz"
    np.savez_compressed(proposal, edge_keys=keys[packed], old_cell_ids=old_ids, new_cells=new_cells, repair_gains=gains[packed])
    candidate = args.output / "candidate.npz"
    np.savez_compressed(candidate, nodes=nodes, tets=result, boundary=boundary)
    predicted_gain = int(gains[packed].sum())
    result = {**plan, "terminal": "candidate_exported_independent_proofs_pending", "candidate_exported": True,
              "candidate_sha256": sha(candidate), "proposal_sha256": sha(proposal), "before_cells": len(cells),
              "after_cells": len(cells) - len(packed), "initial_closed_cavities": len(rows), "admissible_cavities": len(eligible),
              "replacements": len(packed), "packing_cell_conflicts": conflicts, "packing_duplicate_faces": duplicate_faces,
              "predicted_repair_gain": predicted_gain, "predicted_bad_cells": int(bad.sum()) - predicted_gain,
              "controls": controls, "independent_local_domain_and_whole_volume_checks_required": True,
              "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
