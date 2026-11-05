#!/usr/bin/env python3
"""Extract compact, source-admitted cavity inputs before any paid compute."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time

import igl
import igl.predicates
import numpy as np


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, data):
    with path.open("x") as stream:
        json.dump(data, stream, separators=(",", ":"), allow_nan=False); stream.write("\n")


def load(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def input_case(case_id, nodes, old, source_sha, metadata):
    return {"schema": "935-exact-cavity-input-1", "case_id": case_id,
        "source_mesh_sha256": source_sha, "nodes": nodes.tolist(), "old_cells": old.tolist(),
        "coordinates_f64_sha256": hashlib.sha256(np.asarray(nodes, dtype="<f8").tobytes()).hexdigest(),
        "cells_u32_sha256": hashlib.sha256(np.asarray(old, dtype="<u4").tobytes()).hexdigest(), **metadata}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "parent", "benchmark", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False); (args.output/"cases").mkdir()
    started = time.monotonic(); base = args.repository/"docs/research"
    contract_path = base/"935-signed-partition-20261105/source/centroid_star_contract.py"
    geometry_path = base/"935-residual-source-admission-20261105/source/convex_partition_contract.py"
    contract = load(contract_path, "batch_source_centroid_contract", "0983f355f6983a3d5611144362871f404e969bd5f11e6ad7889a0fce35b054bb")
    geometry = load(geometry_path, "batch_source_exact_primitives", "c06c37065561813a27791a4096d41c9e221f83ba48e775b2de6489f1f5a84a07")
    source = load(base/"935-signed-partition-20261105/source/propose_centroid_cavities_v2.py", "batch_complete_source_incidence", "286d590e57b3c13d342e5ab29d747f4683bbf83cfc8581af3a99d93c6593f726")
    helper = load(base/"935-local-physics-20261105/source/inspect_tetrahedra.py", "batch_source_face_keys", "fe8c7fa88f35d2d14094438bbae3b0860bde085a39b68f7ab941790cb4d1bec3")
    assert sha(args.parent/"manifest.json") == "e651636ad4a9aaa5640f69d12df304f52bb7f539bda1a65433a53fdd1bb6fb00"
    assert sha(args.benchmark/"manifest.json") == "4a9c29a825f7125e6b810d16e7fa2383993c4499086bcfc6d87500ce7521af04"
    mesh = args.parent/"partition-verification/candidate.npz"
    mesh_sha = sha(mesh)
    assert mesh_sha == "1bc2e8dddaf07c43ca36d35608f4fdb508f22e0694e922108a96466887f6182d"
    condition_path = args.parent/"partition-whole-condition/private-exact-severe-values.json"
    assert sha(condition_path) == "e339ca30c5ebf16f68dbaa5a14fe059df9a4de09f3069f0c1a1176f75b8a1878"
    conditions = {r["cell_id"]: Fraction(*map(int, r["reciprocal_frobenius_squared"])) for r in json.loads(condition_path.read_text())}
    targets = sorted(i for i, r in conditions.items() if r*10**32 <= 1); assert len(targets) == 26
    with np.load(mesh, allow_pickle=False) as data:
        nodes, cells, surface = data["nodes"], data["tets"], data["boundary"]
    actual_boundary_vertices = np.zeros(len(nodes), bool); actual_boundary_vertices[surface] = True
    all_target_vertices = set(map(int, cells[targets].ravel()))
    seeds = {i for i in all_target_vertices if actual_boundary_vertices[i]}
    stars = source.complete_vertex_stars(cells, seeds)
    initial_boundaries = {v:contract.boundary(cells[ids]) for v, ids in stars.items()}
    face_queries = sorted({tuple(sorted(f)) for faces in initial_boundaries.values() for f in faces})
    neighbors = source.complete_face_hits(cells, face_queries, helper.records)
    profiles = []; unique = {}; duplicate_profiles = 0
    for seed in sorted(seeds):
        expanded = set(stars[seed])
        for face in initial_boundaries[seed]:
            expanded.update(neighbors[tuple(sorted(face))])
        for level, ids in ((0, stars[seed]), (1, sorted(expanded))):
            key = tuple(ids)
            if key in unique:
                duplicate_profiles += 1
                profiles.append({"seed": seed, "face_neighbor_ring": level, "duplicate_of_profile": unique[key]})
                continue
            unique[key] = len(profiles)
            profiles.append({"seed": seed, "face_neighbor_ring": level, "old_global_cell_ids": ids})
    all_faces = sorted({tuple(sorted(f)) for p in profiles if "old_global_cell_ids" in p for f in contract.boundary(cells[p["old_global_cell_ids"]])})
    tags_path = Path('/Users/maxime/Developer/PorschePartsArtifacts/935-condition-directed-20261105-001/peel-proof/candidate-tags.npy')
    assert sha(tags_path) == "716a7c0f155551ec42db10527b4c53ea2ed95948d0cc027e7b786f3b9f4ce0b5"
    with np.load('/Users/maxime/Developer/PorschePartsArtifacts/935-condition-directed-20261105-001/peel-proof/candidate-surface.npz', allow_pickle=False) as data:
        assert np.array_equal(surface, data["triangles"])
    labels = source.boundary_tags(surface, np.load(tags_path, allow_pickle=False), all_faces, helper.records)
    known_path = args.benchmark/"centroid-proposal-v2/private-centroid-cavity-proposal.json"
    assert sha(known_path) == "3af178341af867be6f26027bddbca4eb2095674856fb5b80502308b408c77cbc"
    known = json.loads(known_path.read_text())[0]; known_ids = tuple(known["old_cell_ids"])
    cases = []; case_metadata = []; rejected = Counter(); benchmark = None
    for number, profile in enumerate(profiles):
        if "old_global_cell_ids" not in profile:
            continue
        ids = profile["old_global_cell_ids"]; old_global = cells[ids]
        vertices = np.unique(old_global); local_nodes = nodes[vertices]
        old_local = np.searchsorted(vertices, old_global).astype(np.uint32)
        faces = contract.boundary(old_local)
        record = {"profile": number, "face_neighbor_ring": profile["face_neighbor_ring"],
            "old_cells": len(ids), "boundary_faces": len(faces), "source_vertices": len(vertices)}
        reason = None
        if len(ids) > 96 or len(faces) > 196:
            reason = "declared_local_resource_profile_exceeded"
        else:
            try:
                contract.source_admission(local_nodes, old_local, geometry)
            except AssertionError as error:
                reason = str(error) or "source_topology_or_shape_refused"
        if reason is None:
            found, pairs, _ = igl.predicates.find_self_intersections(np.ascontiguousarray(local_nodes), np.asarray(faces, dtype=np.int64), False)
            assert bool(found) == bool(len(pairs)); record["source_boundary_intersection_pairs"] = len(pairs)
            if len(pairs):
                reason = "source_cavity_boundary_intersections"
        if reason is not None:
            rejected[reason] += 1; record["verdict"] = reason; case_metadata.append(record); continue
        case_id = "case-"+str(len(cases)).zfill(4)
        captured = sorted(set(ids).intersection(targets))
        assert captured
        data = input_case(case_id, local_nodes, old_local, mesh_sha, {
            "source_seed_vertex": profile["seed"], "face_neighbor_ring": profile["face_neighbor_ring"],
            "source_global_cell_ids": ids, "source_global_vertex_ids": vertices.tolist(),
            "target_source_cell_ids": captured, "source_topology_fixed_faces_and_retention_admitted": True,
            "source_native_boundary_intersection_pairs": 0,
            "global_boundary_faces": sum(labels.get(tuple(sorted(int(vertices[v]) for v in f)), -1) >= 0 for f in faces),
            "native_source_admission_is_not_a_new_volume_or_physics_admission": True})
        relative = "cases/"+case_id+".json"; save(args.output/relative, data)
        cases.append({"case_id": case_id, "path": relative})
        record.update(case_id=case_id, verdict="source_admitted_for_bounded_exact_candidate_trial")
        case_metadata.append(record)
        if tuple(ids) == known_ids:
            assert benchmark is None
            inverse = {int(v):i for i, v in enumerate(vertices)}
            new_local = [[len(vertices) if int(v) == len(nodes) else inverse[int(v)] for v in tet] for tet in known["new_cells"]]
            benchmark = {"case": relative, "expected": {"new_point_hex": [float(x).hex() for x in known["new_point"]],
                "new_cells_u32_sha256": hashlib.sha256(np.asarray(new_local, dtype="<u4").tobytes()).hexdigest(),
                "old_bins": [1]*5, "new_bins": [0]*5}, "case_id": case_id}
    assert benchmark is not None and 0 < len(cases) <= 256
    reference_path = args.benchmark/"centroid-reference-control/literal-centroid-star-reference.npz"
    assert sha(reference_path) == "c7538b9d60465ddc94f11f28e0d04700ab22bd7c03c1fbbcd50bb82f5a9e7194"
    with np.load(reference_path, allow_pickle=False) as data:
        control_nodes, control_old = data["source_nodes"], data["old_cells"].astype(np.uint32)
    save(args.output/"control.json", input_case("control", control_nodes, control_old, "synthetic-control", {"literal_reference_sha256": sha(reference_path)}))
    shutil.copyfile(geometry_path, args.output/"geometry_primitives.py")
    shutil.copyfile(contract_path, args.output/"centroid_contract.py")
    worker = Path(__file__).with_name("exact_cavity_worker.py"); shutil.copyfile(worker, args.output/"exact_cavity_worker.py")
    preparation = {"source_sha256": sha(Path(__file__)), "source_mesh_sha256": mesh_sha,
        "benchmark_parent_manifest_sha256": sha(args.benchmark/"manifest.json"),
        "target_exact_condition_threshold": 10**16, "target_source_cells": len(targets),
        "unique_target_vertices": len(all_target_vertices), "boundary_seed_vertices": len(seeds),
        "fixed_source_profiles": len(profiles), "duplicate_source_profiles_omitted": duplicate_profiles,
        "unique_source_profiles_screened": len(unique), "source_admitted_cases": len(cases),
        "rejection_counts": dict(rejected), "profiles": case_metadata,
        "known_independently_verified_benchmark_case": benchmark["case_id"],
        "worker_runtime_requires_only_python_standard_library": True,
        "remote_hardware_requested_for_parallel_exact_proofs_not_GPU_inference": True,
        "full_scan_or_complete_volume_transfer_required": False,
        "geometry_or_connectivity_modified": False, "physics_admitted": False, "manufacturing_qualified": False,
        "new_paid_compute_usd": 0, "seconds": time.monotonic()-started}
    save(args.output/"preparation-report.json", preparation)
    files = [{"path":str(p.relative_to(args.output)), "bytes":p.stat().st_size, "sha256":sha(p)} for p in sorted(args.output.rglob('*')) if p.is_file()]
    job = {"schema":"935-exact-cavity-job-1", "source_mesh_sha256":mesh_sha, "cases":cases,
        "control_case":"control.json", "benchmark_case":benchmark["case"], "benchmark_expected":benchmark["expected"],
        "files":files, "fixed_quality_and_all_eight_exact_condition_counts_nonregressing":True,
        "global_source_reconstruction_and_independent_verification_required":True,
        "new_points_are_numerical_interior_mesh_only":True, "physics_admitted":False, "manufacturing_qualified":False}
    save(args.output/"job.json", job)
    print(json.dumps({k:v for k,v in preparation.items() if k!='profiles'}), flush=True)


if __name__ == "__main__":
    main()
