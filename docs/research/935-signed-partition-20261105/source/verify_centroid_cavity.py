#!/usr/bin/env python3
"""Separate actual-source centroid, Fraction planes and complete star export checks."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import importlib.util
from itertools import combinations
import json
from pathlib import Path
import signal
import time

import numpy as np

FACES = ((1, 2, 3), (0, 3, 2), (0, 1, 3), (0, 2, 1))


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def independent_chain(cells):
    result = Counter()
    for tet in cells:
        for indices in FACES:
            face = [int(tet[i]) for i in indices]
            parity = sum(face[i] > face[j] for i in range(3) for j in range(i+1, 3))
            result[tuple(sorted(face))] += 1 if parity % 2 == 0 else -1
    result = {face:sign for face, sign in result.items() if sign}
    assert all(abs(sign) == 1 for sign in result.values())
    return result


def local(nodes, old, point, new, contract, geometry, oracle):
    old_geometry, old_volume, old_cubes = oracle.fractions(nodes, old)
    old_volumes = [oracle.inner(oracle.minus(p[1], p[0]), oracle.outer(oracle.minus(p[2], p[0]), oracle.minus(p[3], p[0])))/6 for p in old_geometry]
    ideal = tuple(sum((volume*sum(p[i][axis] for i in range(4))/4 for volume, p in zip(old_volumes, old_geometry)), F(0))/old_volume for axis in range(3))
    expected = np.array([float(value) for value in ideal])
    assert np.array_equal(point.view(np.uint64), expected.view(np.uint64)), "Stored point differs from independent exact volume centroid"
    assert not np.any(np.all(nodes == point, axis=1)), "New numerical point duplicates a source node"
    augmented = np.vstack((nodes, point))
    old_boundary = independent_chain(old); new_boundary = independent_chain(new)
    assert old_boundary == new_boundary
    center = len(nodes)
    expected_sets = {tuple(sorted((center, *face))) for face in old_boundary}
    assert len(expected_sets) == len(new) and {tuple(sorted(map(int, t))) for t in new} == expected_sets
    source_ids = {int(i) for tet in old for i in tet}
    assert source_ids == {v for face in old_boundary for v in face}
    shared = contract.certify(augmented, old, new, geometry)
    new_geometry, new_volume, new_cubes = oracle.fractions(augmented, new)
    assert old_volume == new_volume == shared["exact_domain_volume"]
    old_bins = [sum(q < F.from_float(t)**3 for q in old_cubes) for t in contract.BINS]
    new_bins = [sum(q < F.from_float(t)**3 for q in new_cubes) for t in contract.BINS]
    assert old_bins == shared["old_bins"] and new_bins == shared["new_bins"]
    assert min(new_cubes) >= F.from_float(.01)**3 and all(a >= b for a, b in zip(old_bins, new_bins))
    planes = [oracle.witness(a, b) for cells in (old_geometry, new_geometry) for a, b in combinations(cells, 2)]
    assert len(planes) == shared["old_pair_separations"]+shared["new_pair_separations"]
    return augmented, ideal, old_bins, new_bins, planes, shared


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "parent", "proposal-root", "reference", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--control-only", action="store_true")
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    contract = load(Path(__file__).with_name("centroid_star_contract.py"), "verified_shared_centroid_partition", "0983f355f6983a3d5611144362871f404e969bd5f11e6ad7889a0fce35b054bb")
    base = args.repository/"docs/research"
    geometry = load(base/"935-residual-source-admission-20261105/source/convex_partition_contract.py", "verified_exact_centroid_primitives", "c06c37065561813a27791a4096d41c9e221f83ba48e775b2de6489f1f5a84a07")
    oracle = load(base/"935-residual-source-admission-20261105/source/verify_partition_flips.py", "independent_Fraction_centroid_and_planes", "beb8cde3ec10a526726c117c38e9cdc029c3eab6f325a80dfe32b61a1ea57301")
    assert sha(args.reference) == "c7538b9d60465ddc94f11f28e0d04700ab22bd7c03c1fbbcd50bb82f5a9e7194"
    with np.load(args.reference, allow_pickle=False) as data:
        source_nodes, old, expected_nodes, new = data["source_nodes"], data["old_cells"], data["augmented_nodes"], data["reference_cells"]
    actual_nodes, ideal, _, _, planes, _ = local(source_nodes, old, expected_nodes[-1], new, contract, geometry, oracle)
    assert np.array_equal(actual_nodes.view(np.uint64), expected_nodes.view(np.uint64))
    assert ideal == (F(0), F(27, 56)+F(1, 1 << 26), F(0)) and len(planes) == 81
    for bad in (new[:, [0, 2, 1, 3]], new[[0, 0, *range(2, 12)]]):
        try:
            local(source_nodes, old, expected_nodes[-1], bad, contract, geometry, oracle)
        except AssertionError:
            pass
        else:
            raise AssertionError("Forged source boundary or partition accepted")
    controls = {"independent_Fraction_volume_centroid_matches_analytic_reference": True,
        "independent_oriented_boundary_and_81_plane_witnesses": True,
        "reversed_and_duplicate_refused": True}
    (args.output/"controls.json").write_text(json.dumps(controls, indent=2)+"\n")
    if args.control_only:
        print(json.dumps(controls), flush=True); return
    mesh = args.parent/"partition-verification/candidate.npz"
    assert sha(mesh) == "1bc2e8dddaf07c43ca36d35608f4fdb508f22e0694e922108a96466887f6182d"
    proposal_path = args.proposal_root/"private-centroid-cavity-proposal.json"
    assert sha(proposal_path) == "3af178341af867be6f26027bddbca4eb2095674856fb5b80502308b408c77cbc"
    proposed = json.loads(proposal_path.read_text()); assert len(proposed) == 1
    item = proposed[0]; assert item["profile"] == 2 and item["face_neighbor_ring"] == 0
    with np.load(mesh, allow_pickle=False) as data:
        nodes, cells, boundary = data["nodes"], data["tets"], data["boundary"]
    seed = int(item["source_seed_vertex"])
    ids = np.array(item["old_cell_ids"], dtype=np.int64)
    complete = np.flatnonzero(np.any(cells == seed, axis=1))
    assert len(ids) == 37 and np.array_equal(ids, complete), "Proposal is not the complete source vertex star"
    assert np.any(boundary == seed), "Source vertex is not on the actual boundary"
    assert np.array_equal(np.unique(cells[ids]), np.array(item["source_vertices"]))
    point = np.array(item["new_point"], dtype=np.float64); new = np.array(item["new_cells"], dtype=cells.dtype)
    assert new.shape == (44, 4)
    augmented, ideal, old_bins, new_bins, planes, shared = local(nodes, cells[ids], point, new, contract, geometry, oracle)
    assert ideal == tuple(F(*map(int, value)) for value in item["ideal_volume_centroid"])
    assert len(planes) == 1612
    keep = np.ones(len(cells), bool); keep[ids] = False
    candidate = np.concatenate((cells[keep], new))
    output = args.output/"candidate.npz"
    np.savez_compressed(output, nodes=augmented, tets=candidate, boundary=boundary)
    with np.load(output, allow_pickle=False) as exported:
        assert np.array_equal(exported["nodes"][:-1].view(np.uint64), nodes.view(np.uint64))
        assert np.array_equal(exported["nodes"][-1].view(np.uint64), point.view(np.uint64))
        assert np.array_equal(exported["tets"], candidate) and np.array_equal(exported["boundary"], boundary)
    mapping = args.output/"private-source-map.npz"
    np.savez_compressed(mapping, replaced_source_cell_ids=ids, new_candidate_cell_ids=np.arange(keep.sum(), len(candidate), dtype=np.int64))
    witness_path = args.output/"private-exact-Fraction-plane-witnesses.json"
    witness_path.write_text(json.dumps(planes, separators=(",", ":"))+"\n")
    result = {"source_sha256": sha(Path(__file__)), "controls": controls, "parent_mesh_sha256": sha(mesh),
        "complete_source_boundary_vertex_star_cells": len(ids), "new_cells": len(new),
        "nodes_before": len(nodes), "nodes_after": len(augmented), "tetrahedra_before": len(cells), "tetrahedra_after": len(candidate),
        "all_original_coordinates_bit_identical": True, "all_complete_boundary_rows_bit_identical": True,
        "all_unmodified_cell_tuples_identical": True, "new_numerical_interior_points": 1,
        "independent_Fraction_centroid_volume_and_thresholds_passed": True,
        "independent_complete_oriented_triangle_chain_equal": True, "independent_exact_separating_plane_witnesses": len(planes),
        "shared_source_admission_and_domain_contract_explicit": True,
        "old_local_bins": old_bins, "new_local_bins": new_bins,
        "new_minimum_quality_approx": float(shared["new_minimum_quality_cubed"])**(1/3),
        "all_new_exact_mean_ratios_at_least_binary64_0_1": new_bins == [0, 0, 0, 0, 0],
        "candidate_sha256": sha(output), "private_source_map_sha256": sha(mapping),
        "private_Fraction_plane_witnesses_sha256": sha(witness_path),
        "whole_volume_and_fresh_complete_condition_census_required": True,
        "native_volume_readback_and_operator_admission_required": True,
        "global_intersection_status_inherited_not_exhaustively_upgraded": True,
        "physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0,
        "seconds": time.monotonic()-started}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
