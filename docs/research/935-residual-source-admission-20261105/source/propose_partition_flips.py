#!/usr/bin/env python3
"""Propose boundary-exact four-to-four flips using actual convex partition proofs."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def module(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def actual_alternatives(nodes, old, center, four, geom, exact, cycle, partition):
    accepted = []; rejected = Counter()
    for index, (new, diagonal, _, _) in enumerate(four.alternatives(nodes, old[None], np.array([center]), geom, exact, cycle)):
        try:
            proof = partition.certify(nodes, old, new[0])
        except AssertionError as error:
            rejected[str(error) or "positive_volume_or_fixed_quality_contract"] += 1
        else:
            accepted.append((index, new[0], diagonal[0], proof))
    return accepted, rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "parent", "support", "reference", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--control-only", action="store_true")
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    base = args.repository/"docs/research"
    partition = module(Path(__file__).with_name("convex_partition_contract.py"), "actual_convex_partition", "c06c37065561813a27791a4096d41c9e221f83ba48e775b2de6489f1f5a84a07")
    four = module(base/"935-four-four-cavities-20261105/source/propose_four_four.py", "partition_four_alternatives", "4298598e1fc5da3f28ad85fcb41cd5db427f5c5a6418f849b13c5bb07963c236")
    geom = module(base/"935-local-cavity-20261105/source/assess_initial_cavities.py", "partition_approx_proposals", "ee60f26e2449fc2da97e34b0fa3f67c5472e0902b8a4166210e2089624887aa6")
    exact = module(base/"935-unoptimized-volume-20261105/source/inspect_interval_volume.py", "partition_interval_orientation", "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71")
    cycle = module(base/"935-four-four-cavities-20261105/source/four_four_contract.py", "partition_cycle_identity", "a5379daacb7a099810acf678110b74d4e6d9c5f34b01ac38fff1472a4ab0228c")
    edge = module(base/"935-condition-directed-20261105/source/verify_surface_peels.py", "partition_complete_edge_incidence", "986bae3440420f1220b790f5ae8d54a92ebd427fb0c4a2c706712733317ddaf6")
    assert sha(args.reference) == "8dbad69d7fe07762fa7c2cfda2f165ccae35b7c846cb8bb1b1efda220bedeb83"
    with np.load(args.reference, allow_pickle=False) as data:
        nodes, old, expected = data["nodes"], data["old_cells"], data["reference_cells"]
    actual, _ = actual_alternatives(nodes, old, (0, 1), four, geom, exact, cycle, partition)
    assert actual and {tuple(sorted(map(int, t))) for t in actual[0][1]} == {tuple(sorted(map(int, t))) for t in expected}
    assert actual[0][3]["exact_domain_volume"] == Fraction(2, 3)
    assert not edge.all_edge_cells(old, {edge.key(*actual[0][2])})[edge.key(*actual[0][2])]
    assert edge.all_edge_cells(np.vstack((old, expected[:1])), {edge.key(*actual[0][2])})[edge.key(*actual[0][2])]
    tested = {"actual_proposal_path_matches_literal_coplanar_reference": True,
        "complete_edge_absence_and_occupied_controls": True, "reference_volume": "2/3"}
    (args.output/"controls.json").write_text(json.dumps(tested, indent=2)+"\n")
    if args.control_only:
        print(json.dumps(tested), flush=True); return
    mesh = args.parent/"peel-proof/candidate-volume.npz"
    assert sha(mesh) == "a4b19f3303e55e4a13830829664e26596247d26cd41632704d4584706773538a"
    support = args.support/"private-exact-support.json"
    assert sha(support) == "e439b2e80f501047b98be224d3a664f58b69dff8a79a75b5220d47a032c8b2f2"
    rows = [r for r in json.loads(support.read_text()) if r["valence"] == 4 and r["weak_support"] and not r["strict_support"]]
    assert len(rows) == 19
    with np.load(mesh, allow_pickle=False) as data:
        nodes, cells = data["nodes"], data["tets"]
    values_path = args.parent/"peeled-whole-condition/private-exact-severe-values.json"
    assert sha(values_path) == "e9747f2b6e05e8046039b2eb5622445a0141b8e6ca7edea8ba3ab27142aa3f11"
    values = json.loads(values_path.read_text())
    conditions = {row["cell_id"]: Fraction(*map(int, row["reciprocal_frobenius_squared"])) for row in values}
    worst = min(conditions, key=conditions.__getitem__)
    candidates = []; reasons = Counter(); diagnostics = []
    for row in rows:
        ids, center = row["source_cell_ids"], row["edge"]
        edge.cycle_link(cells[ids], center)
        actual, rejected = actual_alternatives(nodes, cells[ids], center, four, geom, exact, cycle, partition)
        reasons.update(rejected)
        diagnostics.append({"old_cell_ids": ids, "center": center, "accepted_alternatives": len(actual), "reasons": dict(rejected), "contains_global_worst": worst in ids})
        for index, new, diagonal, proof in actual:
            candidates.append({"old_cell_ids": ids, "old_center": center, "new_cells": new.tolist(),
                "new_edge": diagonal.tolist(), "alternative_index": index, "contains_global_worst": worst in ids,
                "extreme_gain": sum(i in conditions and conditions[i]*10**30 <= 1 for i in ids),
                "critical_gain": proof["old_bins"][0]-proof["new_bins"][0],
                "hull_facets": proof["hull_facets"], "exact_domain_volume": [str(proof["exact_domain_volume"].numerator), str(proof["exact_domain_volume"].denominator)]})
    occupied = edge.all_edge_cells(cells, {edge.key(*c["new_edge"]) for c in candidates})
    packed = []; used = set(); entities = set()
    for c in sorted(candidates, key=lambda c: (-int(c["contains_global_worst"]), -c["extreme_gain"], tuple(c["old_center"]), c["alternative_index"])):
        entity = edge.key(*c["new_edge"])
        if occupied[entity]:
            reasons["created_edge_already_present"] += 1; continue
        if used & set(c["old_cell_ids"]) or entity in entities:
            reasons["packing_conflict"] += 1; continue
        used.update(c["old_cell_ids"]); entities.add(entity); packed.append(c)
    proposal = args.output/"private-partition-proposals.json"; proposal.write_text(json.dumps(packed, separators=(",", ":"))+"\n")
    diagnostic = args.output/"private-partition-diagnostics.json"; diagnostic.write_text(json.dumps(diagnostics, separators=(",", ":"))+"\n")
    result = {"source_sha256": sha(Path(__file__)), "contract_sha256": sha(Path(__file__).with_name("convex_partition_contract.py")),
        "mesh_sha256": sha(mesh), "controls": tested, "weakly_convex_source_stars_tested": len(rows),
        "exact_partition_admitted_alternatives": len(candidates), "packed_cavities": len(packed),
        "global_worst_replaced_if_applied": any(c["contains_global_worst"] for c in packed),
        "extreme_cells_replaced_if_applied": sum(c["extreme_gain"] for c in packed),
        "critical_cells_removed_if_applied": sum(c["critical_gain"] for c in packed), "reasons": dict(reasons),
        "all_new_cells_exact_mean_ratio_floor": .01, "all_five_bins_exact_nonregression": True,
        "actual_old_and_new_convex_domain_partitions_proven": True, "exact_boundary_and_points_preserved": True,
        "separate_verification_required_before_export": True, "geometry_or_connectivity_modified": False,
        "proposal_sha256": sha(proposal), "private_diagnostics_sha256": sha(diagnostic),
        "physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0,
        "seconds": time.monotonic()-started}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
