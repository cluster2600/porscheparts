#!/usr/bin/env python3
"""Read-only source attribution and complete edge stars of residual severe cells."""
import argparse
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


def groups(mask, boundary_rows, cap, boundary_vertices):
    b = (boundary_rows >= 0).sum(axis=1)
    c = (cap != 0).sum(axis=1)
    common = np.bitwise_and.reduce(cap, axis=1)
    return {"cells": int(mask.sum()),
        "actual_boundary_face_count_0_to_4": np.bincount(b[mask], minlength=5).tolist(),
        "cap_incident_vertex_count_0_to_4": np.bincount(c[mask], minlength=5).tolist(),
        "interior_vertex_count_0_to_4": np.bincount((~boundary_vertices[mask]).sum(axis=1), minlength=5).tolist(),
        "all_four_vertices_incident_to_one_cap": int(((common != 0)&mask).sum())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "parent", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600)
    started = time.monotonic(); base = args.repository/"docs/research"
    join = module(base/"935-condition-directed-20261105/source/attribute_severe_cells.py", "residual_source_join", "8edd2077f110a11038009c851d4cb052b6be41ee8e6eeca4751cdda4a2dfa046")
    record = module(base/"935-local-physics-20261105/source/inspect_tetrahedra.py", "residual_face_keys", "fe8c7fa88f35d2d14094438bbae3b0860bde085a39b68f7ab941790cb4d1bec3")
    edge = module(base/"935-condition-directed-20261105/source/verify_surface_peels.py", "residual_complete_stars", "986bae3440420f1220b790f5ae8d54a92ebd427fb0c4a2c706712733317ddaf6")
    tested = join.controls(record.records); tested.update(edge.controls())
    assert sha(args.parent/"manifest.json") == "5daee08ce4a12bbe1c389d7eecd7125c63392b3c961954e7d5bb1d18078c02ea"
    inventory = {row["path"]: row["sha256"] for row in json.loads((args.parent/"manifest.json").read_text())["files"]}
    for name in ("peel-proof/candidate-volume.npz", "peel-proof/candidate-surface.npz", "peel-proof/candidate-tags.npy", "peeled-whole-condition/report.json", "peeled-whole-condition/private-exact-severe-values.json", "peeled-whole-volume/report.json", "peeled-native-surface/report.json"):
        assert sha(args.parent/name) == inventory[name]
    mesh = args.parent/"peel-proof/candidate-volume.npz"
    assert sha(mesh) == "a4b19f3303e55e4a13830829664e26596247d26cd41632704d4584706773538a"
    assert json.loads((args.parent/"peeled-whole-volume/report.json").read_text())["all_cells_positive_for_stored_binary_coordinates"]
    assert json.loads((args.parent/"peeled-native-surface/report.json").read_text())["geometry_export_gate_passed"]
    with np.load(mesh, allow_pickle=False) as data:
        nodes, cells = data["nodes"], data["tets"]
    with np.load(args.parent/"peel-proof/candidate-surface.npz", allow_pickle=False) as data:
        vertices, faces = data["vertices"], data["triangles"]
    assert np.array_equal(nodes[:len(vertices)].view(np.uint64), vertices.view(np.uint64))
    tags = np.load(args.parent/"peel-proof/candidate-tags.npy", allow_pickle=False)
    values = json.loads((args.parent/"peeled-whole-condition/private-exact-severe-values.json").read_text())
    ids = np.array([row["cell_id"] for row in values], dtype=np.int64)
    reciprocal = [Fraction(*map(int, row["reciprocal_frobenius_squared"])) for row in values]
    assert len(ids) == len(np.unique(ids)) == 15945 and all(r*10**24 <= 1 for r in reciprocal)
    boundary_rows, construction, on_boundary, on_skin, cap = join.surface_join(cells[ids], faces, tags, len(nodes), record.records)
    by_threshold = {}
    extreme = None
    for name, threshold in (("1e12", 10**12), ("1e15", 10**15), ("eps_inverse", 2**52), ("1e16", 10**16), ("3_eps_inverse", 3*2**52)):
        mask = np.array([r*threshold*threshold <= 1 for r in reciprocal])
        by_threshold[name] = groups(mask, boundary_rows, cap, on_boundary)
        if name == "1e15":
            extreme = mask
    positions = np.flatnonzero(extreme)
    pairs = sorted({tuple(sorted((int(t[a]), int(t[b])))) for t in cells[ids[extreme]] for a in range(4) for b in range(a+1, 4)})
    keys = {edge.key(*p) for p in pairs}
    stars = edge.all_edge_cells(cells, keys)
    boundary_stars = edge.all_edge_cells(faces, keys)
    valences = np.array([len(stars[edge.key(*p)]) for p in pairs])
    boundary_edge = np.array([bool(boundary_stars[edge.key(*p)]) for p in pairs])
    per_cell = []
    for position in positions:
        tet = cells[ids[position]]
        local = [tuple(sorted((int(tet[a]), int(tet[b])))) for a in range(4) for b in range(a+1, 4)]
        per_cell.append({"source_cell_id": int(ids[position]),
            "actual_boundary_face_count": int((boundary_rows[position] >= 0).sum()),
            "cap_incident_vertices": int((cap[position] != 0).sum()),
            "interior_vertices": int((~on_boundary[position]).sum()),
            "edges": [{"vertices": list(p), "complete_cell_ids": stars[edge.key(*p)], "boundary_face_ids": boundary_stars[edge.key(*p)]} for p in local]})
    worst = min(range(len(reciprocal)), key=reciprocal.__getitem__)
    private = args.output/"private-attribution-and-stars.json"
    private.write_text(json.dumps(per_cell, separators=(",", ":"))+"\n")
    arrays = args.output/"private-residual-attribution.npz"
    np.savez_compressed(arrays, cell_ids=ids, source_boundary_face_ids=boundary_rows,
        construction_tags=construction, vertex_cap_memberships=cap, boundary_vertices=on_boundary,
        extreme_positions=positions)
    result = {"source_sha256": sha(Path(__file__)), "input_mesh_sha256": sha(mesh), "controls": tested,
        "severe_cells_attributed": len(ids), "source_surface_faces_scanned": len(faces),
        "groups_by_exact_condition_threshold": by_threshold,
        "extreme_edge_audit": {"condition_threshold": 10**15, "cells": len(positions), "unique_edges": len(pairs),
            "boundary_edges": int(boundary_edge.sum()), "interior_edges": int((~boundary_edge).sum()),
            "interior_edge_valences": {str(int(v)): int(((valences == v)&~boundary_edge).sum()) for v in np.unique(valences[~boundary_edge])}},
        "maximum_condition_cell_source_constraints": {"actual_boundary_faces": int((boundary_rows[worst] >= 0).sum()),
            "cap_incident_vertices": int((cap[worst] != 0).sum()), "interior_vertices": int((~on_boundary[worst]).sum()),
            "common_cap_membership_bits": int(np.bitwise_and.reduce(cap[worst])),
            "reciprocal_frobenius_squared": [str(reciprocal[worst].numerator), str(reciprocal[worst].denominator)]},
        "private_star_records_sha256": sha(private), "private_attribution_sha256": sha(arrays),
        "tag_zero_does_not_establish_acquired_scan_identity": True, "cap_incidence_does_not_establish_exact_coplanarity": True,
        "geometry_modified": False, "native_metrics_recomputed": False, "physics_admitted": False,
        "manufacturing_qualified": False, "new_paid_compute_usd": 0, "seconds": time.monotonic()-started}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
