#!/usr/bin/env python3
"""Read-only exact-domain four-to-four proposals around current extreme cells."""
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


def load(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def actual_alternatives(nodes, old, center, four, geom, exact, cycle, signed, geometry):
    result = []; rejected = Counter()
    for i, (new, diagonal, _, _) in enumerate(four.alternatives(nodes, old[None], np.array([center]), geom, exact, cycle)):
        try:
            proof = signed.certify(nodes, old, new[0], geometry)
        except AssertionError as error:
            rejected[str(error) or "source_shape_or_positive_volume_contract"] += 1
        else:
            result.append((i, new[0], diagonal[0], proof))
    return result, rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "parent", "reference", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--control-only", action="store_true")
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    base = args.repository/"docs/research"
    signed = load(Path(__file__).with_name("signed_partition_contract.py"), "actual_signed_partition", "a2f2c1f9617b786c27809c9930aad95bc10596ec26bdca7c03d176292ae8941f")
    geometry = load(base/"935-residual-source-admission-20261105/source/convex_partition_contract.py", "signed_exact_primitives", "c06c37065561813a27791a4096d41c9e221f83ba48e775b2de6489f1f5a84a07")
    four = load(base/"935-four-four-cavities-20261105/source/propose_four_four.py", "signed_ring_alternatives", "4298598e1fc5da3f28ad85fcb41cd5db427f5c5a6418f849b13c5bb07963c236")
    geom = load(base/"935-local-cavity-20261105/source/assess_initial_cavities.py", "signed_proposal_orientations", "ee60f26e2449fc2da97e34b0fa3f67c5472e0902b8a4166210e2089624887aa6")
    exact = load(base/"935-unoptimized-volume-20261105/source/inspect_interval_volume.py", "signed_interval_orientation", "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71")
    cycle = load(base/"935-four-four-cavities-20261105/source/four_four_contract.py", "signed_expected_cycles", "a5379daacb7a099810acf678110b74d4e6d9c5f34b01ac38fff1472a4ab0228c")
    edge = load(base/"935-condition-directed-20261105/source/verify_surface_peels.py", "signed_complete_edge_stars", "986bae3440420f1220b790f5ae8d54a92ebd427fb0c4a2c706712733317ddaf6")
    assert sha(args.reference) == "02bf45332f4fa6f1f160b229390c3e0bdc50a00cb798a9681a8a0fc7974be2a0"
    with np.load(args.reference, allow_pickle=False) as data:
        nodes, old, expected = data["nodes"], data["old_cells"], data["reference_cells"]
    actual, _ = actual_alternatives(nodes, old, (0, 1), four, geom, exact, cycle, signed, geometry)
    assert actual and {tuple(sorted(map(int, t))) for t in actual[0][1]} == {tuple(sorted(map(int, t))) for t in expected}
    assert actual[0][3]["exact_domain_volume"] == Fraction(1, 2)
    diagonal = actual[0][2]; query = {edge.key(*diagonal)}
    assert not edge.all_edge_cells(old, query)[edge.key(*diagonal)]
    assert edge.all_edge_cells(np.vstack((old, expected[:1])), query)[edge.key(*diagonal)]
    tested = {"actual_proposal_path_matches_literal_concave_reference": True,
        "independent_expected_reference_volume": "1/2", "complete_absence_and_occupied_edge_controls": True}
    (args.output/"controls.json").write_text(json.dumps(tested, indent=2)+"\n")
    if args.control_only:
        print(json.dumps(tested), flush=True); return
    assert sha(args.parent/"manifest.json") == "e651636ad4a9aaa5640f69d12df304f52bb7f539bda1a65433a53fdd1bb6fb00"
    mesh = args.parent/"partition-verification/candidate.npz"
    assert sha(mesh) == "1bc2e8dddaf07c43ca36d35608f4fdb508f22e0694e922108a96466887f6182d"
    values_path = args.parent/"partition-whole-condition/private-exact-severe-values.json"
    assert sha(values_path) == "e339ca30c5ebf16f68dbaa5a14fe059df9a4de09f3069f0c1a1176f75b8a1878"
    conditions = {r["cell_id"]: Fraction(*map(int, r["reciprocal_frobenius_squared"])) for r in json.loads(values_path.read_text())}
    worst = min(conditions, key=conditions.__getitem__)
    target = np.array(sorted(i for i, r in conditions.items() if r*10**32 <= 1), dtype=np.int64); assert len(target) == 26
    with np.load(mesh, allow_pickle=False) as data:
        nodes, cells, boundary = data["nodes"], data["tets"], data["boundary"]
    pairs = {tuple(sorted((int(t[a]), int(t[b])))) for t in cells[target] for a in range(4) for b in range(a+1, 4)}
    queries = {edge.key(*e) for e in pairs}
    source = edge.all_edge_cells(cells, queries); surface = edge.all_edge_cells(boundary, queries)
    histogram = Counter(); reasons = Counter(); candidates = []; diagnostics = []; worst_edges = []
    for center in sorted(pairs):
        rows = source[edge.key(*center)]
        if worst in rows:
            worst_edges.append({"valence": len(rows), "on_boundary": bool(surface[edge.key(*center)])})
        if surface[edge.key(*center)]:
            continue
        histogram[str(len(rows))] += 1
        if len(rows) != 4:
            continue
        edge.cycle_link(cells[rows], center)
        accepted, rejected = actual_alternatives(nodes, cells[rows], center, four, geom, exact, cycle, signed, geometry)
        reasons.update(rejected)
        diagnostics.append({"source_cell_ids": rows, "center": list(center), "contains_global_worst": worst in rows,
            "accepted_alternatives": len(accepted), "reasons": dict(rejected)})
        for alternative, new, diagonal, proof in accepted:
            candidates.append({"old_cell_ids": rows, "old_center": list(center), "new_cells": new.tolist(), "new_edge": diagonal.tolist(),
                "alternative_index": alternative, "contains_global_worst": worst in rows,
                "target_gain": sum(i in target for i in rows), "severe_gain": sum(i in conditions for i in rows),
                "critical_gain": proof["old_bins"][0]-proof["new_bins"][0],
                "exact_domain_volume": [str(proof["exact_domain_volume"].numerator), str(proof["exact_domain_volume"].denominator)]})
    occupied = edge.all_edge_cells(cells, {edge.key(*c["new_edge"]) for c in candidates})
    packed = []; used = set(); entities = set()
    for c in sorted(candidates, key=lambda c: (-int(c["contains_global_worst"]), -c["target_gain"], tuple(c["old_center"]), c["alternative_index"])):
        entity = edge.key(*c["new_edge"])
        if occupied[entity]:
            reasons["created_edge_already_present"] += 1; continue
        if used.intersection(c["old_cell_ids"]) or entity in entities:
            reasons["packing_conflict"] += 1; continue
        used.update(c["old_cell_ids"]); entities.add(entity); packed.append(c)
    proposed = args.output/"private-signed-extreme-proposals.json"; proposed.write_text(json.dumps(packed, separators=(",", ":"))+"\n")
    diagnostic = args.output/"private-signed-extreme-diagnostics.json"; diagnostic.write_text(json.dumps(diagnostics, separators=(",", ":"))+"\n")
    result = {"source_sha256": sha(Path(__file__)), "mesh_sha256": sha(mesh), "controls": tested,
        "target_condition_at_least": 10**16, "target_cells": len(target), "target_incident_unique_edges": len(pairs),
        "complete_interior_edge_valences": dict(histogram), "global_worst_incident_source_edge_constraints": worst_edges,
        "four_cell_stars_assessed": len(diagnostics), "exact_domain_and_quality_alternatives": len(candidates),
        "packed_cavities": len(packed), "target_cells_replaced_if_applied": sum(c["target_gain"] for c in packed),
        "severe_cells_replaced_if_applied": sum(c["severe_gain"] for c in packed),
        "global_worst_replaced_if_applied": any(c["contains_global_worst"] for c in packed), "reasons": dict(reasons),
        "strict_or_weak_convexity_not_used_as_domain_proof": True,
        "quality_and_boundary_thresholds_unchanged": True, "geometry_or_connectivity_modified": False,
        "proposal_sha256": sha(proposed), "private_diagnostics_sha256": sha(diagnostic),
        "separate_source_star_and_full_volume_verification_required": True,
        "physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0,
        "seconds": time.monotonic()-started}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
