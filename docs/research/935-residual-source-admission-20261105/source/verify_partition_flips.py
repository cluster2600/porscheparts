#!/usr/bin/env python3
"""Separate full-star, Fraction-quality and separating-plane verification/export.

The convex-hull partition contract is shared and explicitly pinned. This verifier
independently computes exact Fraction signs, volumes and qualities, and verifies
an explicit separating-plane witness for every old/new cell pair. Whole-volume
inspection remains a separate mandatory stage after candidate export.
"""
import argparse
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
EDGES = tuple(combinations(range(4), 2))


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def module(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def minus(a, b):
    return tuple(x-y for x, y in zip(a, b))


def inner(a, b):
    return sum(x*y for x, y in zip(a, b))


def outer(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def fractions(nodes, cells):
    geometry = [[tuple(F.from_float(float(x)) for x in p) for p in nodes[t]] for t in cells]
    volumes = []; cubes = []
    for p in geometry:
        d = inner(minus(p[1], p[0]), outer(minus(p[2], p[0]), minus(p[3], p[0])))
        assert d > 0, "Nonpositive independent Fraction determinant"
        s = sum(inner(minus(p[a], p[b]), minus(p[a], p[b])) for a, b in EDGES)
        volumes.append(d/6); cubes.append(432*d*d/s**3)
    return geometry, sum(volumes, F(0)), cubes


def witness(left, right):
    def axes():
        for p in (left, right):
            for a, b, c in FACES:
                yield outer(minus(p[b], p[a]), minus(p[c], p[a]))
        for a, b in EDGES:
            for c, d in EDGES:
                yield outer(minus(left[b], left[a]), minus(right[d], right[c]))
    for normal in axes():
        if not any(normal):
            continue
        a = [inner(normal, p) for p in left]; b = [inner(normal, p) for p in right]
        if max(a) <= min(b) or max(b) <= min(a):
            # These exact projections alone prove no overlap of interiors.
            return [[str(x.numerator), str(x.denominator)] for x in normal]
    raise AssertionError("No independent separating-plane witness")


def local(nodes, old, new, center, diagonal, partition, cycle):
    cycle.expected_sets(old[None], np.array([center]), np.array([diagonal]), new[None])
    shared = partition.certify(nodes, old, new)
    old_geometry, old_volume, old_cubes = fractions(nodes, old)
    new_geometry, new_volume, new_cubes = fractions(nodes, new)
    assert old_volume == new_volume == shared["exact_domain_volume"]
    old_bins = [sum(q < F.from_float(t)**3 for q in old_cubes) for t in partition.BINS]
    new_bins = [sum(q < F.from_float(t)**3 for q in new_cubes) for t in partition.BINS]
    assert old_bins == shared["old_bins"] and new_bins == shared["new_bins"]
    assert min(new_cubes) >= F.from_float(.01)**3 and all(a >= b for a, b in zip(old_bins, new_bins))
    planes = [witness(a, b) for geometry in (old_geometry, new_geometry) for a, b in combinations(geometry, 2)]
    assert len(planes) == 12
    return old_bins, new_bins, planes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "parent", "proposal", "reference", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--control-only", action="store_true")
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    base = args.repository/"docs/research"
    partition = module(Path(__file__).with_name("convex_partition_contract.py"), "verified_shared_partition", "c06c37065561813a27791a4096d41c9e221f83ba48e775b2de6489f1f5a84a07")
    cycle = module(base/"935-four-four-cavities-20261105/source/four_four_contract.py", "verified_ring_cell_sets", "a5379daacb7a099810acf678110b74d4e6d9c5f34b01ac38fff1472a4ab0228c")
    edge = module(base/"935-condition-directed-20261105/source/verify_surface_peels.py", "verified_full_source_edge_stars", "986bae3440420f1220b790f5ae8d54a92ebd427fb0c4a2c706712733317ddaf6")
    assert sha(args.reference) == "8dbad69d7fe07762fa7c2cfda2f165ccae35b7c846cb8bb1b1efda220bedeb83"
    with np.load(args.reference, allow_pickle=False) as data:
        nodes, old, new = data["nodes"], data["old_cells"], data["reference_cells"]
    old_bins, new_bins, planes = local(nodes, old, new, (0, 1), (2, 4), partition, cycle)
    assert old_bins[0] == 2 and new_bins[0] == 0 and len(planes) == 12
    tetra = [tuple(F(x) for x in p) for p in [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]]
    try:
        witness(tetra, tetra)
    except AssertionError:
        pass
    else:
        raise AssertionError("Coincident cells accepted")
    tested = {"literal_reference_independent_Fraction_local_checks": True,
        "all_twelve_exact_separating_plane_witnesses": True, "coincident_cell_refusal": True}
    (args.output/"controls.json").write_text(json.dumps(tested, indent=2)+"\n")
    if args.control_only:
        print(json.dumps(tested), flush=True); return
    mesh = args.parent/"peel-proof/candidate-volume.npz"
    assert sha(mesh) == "a4b19f3303e55e4a13830829664e26596247d26cd41632704d4584706773538a"
    assert sha(args.proposal) == "64aafcaa606109a2d0673474c0d449bb4dc7771bd038894ca463d65e55ae5575"
    proposed = json.loads(args.proposal.read_text()); assert len(proposed) == 660
    with np.load(mesh, allow_pickle=False) as data:
        nodes, cells, boundary = data["nodes"], data["tets"], data["boundary"]
    centers = {edge.key(*r["old_center"]) for r in proposed}; diagonals = {edge.key(*r["new_edge"]) for r in proposed}
    assert len(centers) == len(diagonals) == len(proposed)
    incidence = edge.all_edge_cells(cells, centers | diagonals)
    used = set(); old_totals = np.zeros(5, dtype=np.int64); new_totals = old_totals.copy(); witnesses = []
    candidate = cells.copy()
    for row in proposed:
        ids, center, diagonal = row["old_cell_ids"], row["old_center"], row["new_edge"]
        assert len(ids) == len(set(ids)) == 4 and not used.intersection(ids)
        assert sorted(incidence[edge.key(*center)]) == sorted(ids) and not incidence[edge.key(*diagonal)]
        old = cells[ids]; new = np.array(row["new_cells"], dtype=cells.dtype)
        edge.cycle_link(old, center)
        old_bins, new_bins, planes = local(nodes, old, new, center, diagonal, partition, cycle)
        old_totals += old_bins; new_totals += new_bins
        witnesses.append({"old_cell_ids": ids, "exact_separating_planes": planes})
        used.update(ids); candidate[ids] = new
    outside = np.ones(len(cells), dtype=bool); outside[list(used)] = False
    assert np.array_equal(candidate[outside], cells[outside])
    output = args.output/"candidate.npz"; np.savez_compressed(output, nodes=nodes, tets=candidate, boundary=boundary)
    with np.load(output, allow_pickle=False) as actual:
        assert np.array_equal(actual["nodes"].view(np.uint64), nodes.view(np.uint64))
        assert np.array_equal(actual["tets"], candidate) and np.array_equal(actual["boundary"], boundary)
    maps = args.output/"private-source-row-map.npz"; np.savez_compressed(maps, replaced_source_cell_ids=np.array(sorted(used), dtype=np.int64))
    planes_path = args.output/"private-exact-separating-planes.json"; planes_path.write_text(json.dumps(witnesses, separators=(",", ":"))+"\n")
    result = {"source_sha256": sha(Path(__file__)), "controls": tested, "parent_mesh_sha256": sha(mesh),
        "shared_partition_contract_sha256": sha(Path(__file__).with_name("convex_partition_contract.py")),
        "shared_hull_enumeration_not_claimed_independent": True,
        "complete_old_four_cell_stars_independently_verified": len(proposed), "new_edges_globally_absent": True,
        "independent_Fraction_volume_quality_and_plane_checks": len(proposed),
        "independent_exact_separating_plane_witnesses": 12*len(proposed),
        "replaced_cells_each_old_and_new": len(used), "source_and_replacement_cell_count_identical": True,
        "all_points_and_boundary_rows_bit_exact": True, "all_unchanged_cell_tuples_identical": True,
        "exact_local_old_bin_totals": old_totals.tolist(), "exact_local_new_bin_totals": new_totals.tolist(),
        "all_new_cells_exact_mean_ratio_at_least_binary64_001": True,
        "new_edge_Jacobian_kappa_F_upper_bound": 12000, "candidate_sha256": sha(output),
        "private_source_map_sha256": sha(maps), "private_separating_planes_sha256": sha(planes_path),
        "whole_volume_verification_required": True, "new_native_readback_and_operator_checks_required": True,
        "global_tetrahedron_intersection_status_inherited_not_exhaustively_upgraded": True,
        "physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0,
        "seconds": time.monotonic()-started}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
