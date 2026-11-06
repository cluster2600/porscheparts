#!/usr/bin/env python3
"""Finite six-ring alternatives for the current worst cell, indices only."""
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


def ring(old, center):
    neighbors = {}; seen = set()
    for tet in old:
        assert all(v in tet for v in center)
        pair = tuple(sorted(set(map(int, tet))-set(center)))
        assert len(pair) == 2 and pair not in seen
        seen.add(pair); a, b = pair
        neighbors.setdefault(a, set()).add(b); neighbors.setdefault(b, set()).add(a)
    assert len(neighbors) == 6 and all(len(v) == 2 for v in neighbors.values())
    first = min(neighbors); sequence = [first, min(neighbors[first])]
    while len(sequence) < 6:
        following = neighbors[sequence[-1]]-{sequence[-2]}; assert len(following) == 1
        vertex = following.pop(); assert vertex not in sequence
        sequence.append(vertex)
    assert first in neighbors[sequence[-1]]
    return tuple(sequence)


def triangulations(vertices):
    if len(vertices) < 3:
        return ((),)
    result = []
    for split in range(1, len(vertices)-1):
        for left in triangulations(vertices[:split+1]):
            for right in triangulations(vertices[split:]):
                triangle = tuple(sorted((vertices[0], vertices[split], vertices[-1])))
                result.append(tuple(sorted(left+right+(triangle,))))
    assert len(result) == len(set(result))
    return tuple(result)


def actual_alternatives(nodes, old, center, contract, geometry):
    ordered = ring(old, center)
    choices = triangulations(ordered); assert len(choices) == 14
    perimeter = {tuple(sorted((ordered[i], ordered[(i+1)%6]))) for i in range(6)}
    candidates = []
    for triangles in choices:
        edges = {tuple(sorted((t[a], t[b]))) for t in triangles for a, b in ((0, 1), (1, 2), (2, 0))}
        diagonals = tuple(sorted(edges-perimeter)); assert len(diagonals) == 3
        candidates.append((diagonals, triangles))
    points, _ = geometry.exact_points(nodes, sorted(set(map(int, old.ravel()))))
    admitted = []; rejected = Counter()
    for index, (diagonals, triangles) in enumerate(sorted(candidates)):
        new = np.array([[apex, *triangle] for triangle in triangles for apex in center], dtype=old.dtype)
        assert new.shape == (8, 4)
        for i, tet in enumerate(new):
            if geometry.determinant([points[int(v)] for v in tet]) < 0:
                new[i, [1, 2]] = new[i, [2, 1]]
        try:
            proof = contract.certify(nodes, old, new, geometry)
        except AssertionError as error:
            rejected[str(error) or "source_shape_contract"] += 1
        else:
            admitted.append((index, new, diagonals, proof))
    return admitted, rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "parent", "reference", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--control-only", action="store_true")
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    contract = load(Path(__file__).with_name("six_eight_contract.py"), "actual_six_eight_partition", "b1cdab885ad364a10351ee1db39df6d34bcacc19f76776b4b5370cf807801dc5")
    base = args.repository/"docs/research"
    geometry = load(base/"935-residual-source-admission-20261105/source/convex_partition_contract.py", "six_eight_source_primitives", "c06c37065561813a27791a4096d41c9e221f83ba48e775b2de6489f1f5a84a07")
    edge = load(base/"935-condition-directed-20261105/source/verify_surface_peels.py", "six_eight_complete_edge_stars", "986bae3440420f1220b790f5ae8d54a92ebd427fb0c4a2c706712733317ddaf6")
    assert sha(args.reference) == "490a8b78c0d1063138c506d3a22171dc3367b387d180a16b3215f20b5646b0c9"
    with np.load(args.reference, allow_pickle=False) as data:
        nodes, old, literal = data["nodes"], data["old_cells"], data["reference_cells"]
    alternatives, _ = actual_alternatives(nodes, old, (0, 1), contract, geometry)
    assert alternatives and {tuple(sorted(map(int, t))) for t in alternatives[0][1]} == {tuple(sorted(map(int, t))) for t in literal}
    assert alternatives[0][3]["exact_domain_volume"] == Fraction(7, 6)
    tested = {"actual_fourteen_alternative_path_matches_literal_concave_reference": True,
        "independent_expected_reference_volume": "7/6", "canonical_complete_cycle": ring(old, (0, 1)) == (2, 3, 4, 5, 6, 7)}
    (args.output/"controls.json").write_text(json.dumps(tested, indent=2)+"\n")
    if args.control_only:
        print(json.dumps(tested), flush=True); return
    assert sha(args.parent/"manifest.json") == "e651636ad4a9aaa5640f69d12df304f52bb7f539bda1a65433a53fdd1bb6fb00"
    mesh = args.parent/"partition-verification/candidate.npz"
    assert sha(mesh) == "1bc2e8dddaf07c43ca36d35608f4fdb508f22e0694e922108a96466887f6182d"
    values = args.parent/"partition-whole-condition/private-exact-severe-values.json"
    assert sha(values) == "e339ca30c5ebf16f68dbaa5a14fe059df9a4de09f3069f0c1a1176f75b8a1878"
    conditions = {r["cell_id"]: Fraction(*map(int, r["reciprocal_frobenius_squared"])) for r in json.loads(values.read_text())}
    worst = min(conditions, key=conditions.__getitem__)
    with np.load(mesh, allow_pickle=False) as data:
        nodes, cells, boundary = data["nodes"], data["tets"], data["boundary"]
    pairs = {tuple(sorted((int(cells[worst, a]), int(cells[worst, b])))) for a in range(4) for b in range(a+1, 4)}
    queries = {edge.key(*e) for e in pairs}
    source = edge.all_edge_cells(cells, queries); surface = edge.all_edge_cells(boundary, queries)
    stars = [(e, source[edge.key(*e)]) for e in sorted(pairs) if len(source[edge.key(*e)]) == 6 and not surface[edge.key(*e)]]
    assert len(stars) == 2
    candidates = []; diagnostics = []; reasons = Counter()
    for center, ids in stars:
        alternatives, rejected = actual_alternatives(nodes, cells[ids], center, contract, geometry)
        reasons.update(rejected)
        diagnostics.append({"center": list(center), "source_cell_ids": ids, "alternatives_examined": 14,
            "accepted_local_alternatives": len(alternatives), "reasons": dict(rejected)})
        for index, new, diagonals, proof in alternatives:
            candidates.append({"old_cell_ids": ids, "old_center": list(center), "new_cells": new.tolist(),
                "new_diagonals": diagonals, "alternative_index": index, "contains_global_worst": worst in ids,
                "severe_gain": sum(i in conditions for i in ids), "critical_gain": proof["old_bins"][0]-proof["new_bins"][0],
                "exact_domain_volume": [str(proof["exact_domain_volume"].numerator), str(proof["exact_domain_volume"].denominator)]})
    occupied = edge.all_edge_cells(cells, {edge.key(*d) for c in candidates for d in c["new_diagonals"]})
    accepted = [c for c in candidates if all(not occupied[edge.key(*d)] for d in c["new_diagonals"])]
    reasons["created_diagonal_already_present"] = len(candidates)-len(accepted)
    # Both stars contain the same worst source cell: choose one finite canonical alternative.
    chosen = sorted(accepted, key=lambda c: (tuple(c["old_center"]), c["alternative_index"]))[:1]
    proposal = args.output/"private-six-eight-proposal.json"; proposal.write_text(json.dumps(chosen, separators=(",", ":"))+"\n")
    diagnostic = args.output/"private-six-eight-diagnostics.json"; diagnostic.write_text(json.dumps(diagnostics, separators=(",", ":"))+"\n")
    result = {"source_sha256": sha(Path(__file__)), "mesh_sha256": sha(mesh), "controls": tested,
        "complete_current_worst_interior_six_stars": len(stars), "finite_alternatives_examined": 28,
        "exact_domain_and_quality_alternatives": len(candidates), "globally_absent_diagonal_alternatives": len(accepted),
        "chosen_nonoverlapping_cavities": len(chosen), "global_worst_replaced_if_applied": bool(chosen),
        "severe_cells_replaced_if_applied": sum(c["severe_gain"] for c in chosen), "reasons": dict(reasons),
        "fixed_source_boundary_and_quality_contracts_unchanged": True, "geometry_or_connectivity_modified": False,
        "proposal_sha256": sha(proposal), "private_diagnostics_sha256": sha(diagnostic),
        "separate_source_star_and_complete_volume_verification_required": True,
        "physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0,
        "seconds": time.monotonic()-started}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
