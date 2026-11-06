"""Construct the first intermediate of a bounded local topology iteration.

The original 50% target is cumulative and remains unmet by this initial pack.
No node moves. Independent local-domain and whole-volume inspection are required
before this intermediate can supply the next numerical pass.
"""
import argparse
import hashlib
import json
from pathlib import Path
import signal
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def replace(cells, old_ids, new_cells):
    assert old_ids.ndim == 2 and old_ids.shape[1] == 3 and new_cells.shape == (len(old_ids), 2, 4)
    assert len(np.unique(old_ids)) == old_ids.size and old_ids.max() < len(cells)
    removed = np.zeros(len(cells), dtype=bool)
    removed[old_ids] = True
    result = np.vstack((cells[~removed], new_cells.reshape(-1, 4)))
    assert len(result) == len(cells) - len(old_ids)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh", "proposal", "assessment", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    started = time.monotonic()
    assert sha(args.mesh) == "b06d28ec39019fa8f91c2e8cd0397c2eb9cd87bf84df7006c8526025aef03450"
    assert sha(args.proposal) == "005f1f71f356189d1389813ba02f887badeb9cc1ab9937f624cbfbee7fe08e96"
    assessment = json.loads(args.assessment.read_text())
    assert assessment["packed_proposal_sha256"] == sha(args.proposal)
    assert assessment["mesh_sha256"] == sha(args.mesh)
    plan = {"source_sha256": sha(Path(__file__)), "mesh_sha256": sha(args.mesh),
            "assessment_sha256": sha(args.assessment), "proposal_sha256": sha(args.proposal),
            "method": "Monotone convex 3-to-2 local topology iteration", "current_pass": 1,
            "maximum_declared_passes": 3, "cumulative_target_reduction_fraction": .5,
            "rebuild_cavities_only_from_independently_checked_intermediates": True,
            "stop_at_target_or_no_admissible_moves_or_budget": True,
            "intermediate_only": True, "node_motion_allowed": False,
            "local_domain_proof_and_whole_volume_inspection_required": True,
            "new_paid_compute_usd": 0, "physics_admitted": False, "manufacturing_qualified": False}
    (args.output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    fixture = np.array([[3, 4, 0, 1], [3, 4, 1, 2], [3, 4, 2, 0]])
    alternate = np.array([[[0, 1, 2, 3], [0, 2, 1, 4]]])
    assert np.array_equal(replace(fixture, np.array([[0, 1, 2]]), alternate), alternate[0])
    try:
        replace(fixture, np.array([[0, 1, 1]]), alternate)
    except AssertionError:
        pass
    else:
        raise AssertionError("Overlapping replacement accepted")
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, cells, boundary = data["nodes"], data["tets"].astype(np.uint32), data["boundary"]
    with np.load(args.proposal, allow_pickle=False) as data:
        old_ids, new_cells, gains = data["old_cell_ids"], data["new_cells"], data["repair_gains"]
    assert len(old_ids) == assessment["greedy_packed_cavities"] and np.all(gains > 0)
    result = replace(cells, old_ids, new_cells)
    candidate = args.output / "candidate.npz"
    np.savez_compressed(candidate, nodes=nodes, tets=result, boundary=boundary)
    report = {**plan, "candidate_sha256": sha(candidate), "before_cells": len(cells), "after_cells": len(result),
              "replacements": len(old_ids), "predicted_bad_cell_repair_gain": int(gains.sum()),
              "predicted_bad_cells": assessment["predicted_bad_cells_if_applied"],
              "cumulative_target_pending": True, "independent_inspection_pending": True,
              "controls": {"known_3_to_2_replacement": True, "overlapping_cell_ids_refused": True},
              "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
