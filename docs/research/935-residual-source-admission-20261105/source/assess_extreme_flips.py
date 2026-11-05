#!/usr/bin/env python3
"""Read-only three/four-edge cavity assessment targeted at exact extreme cells."""
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
    obj = importlib.util.module_from_spec(spec); spec.loader.exec_module(obj)
    return obj


def central_faces_present(cells, queries, records):
    result = np.zeros(len(queries), bool)
    for start in range(0, len(cells), 100000):
        chunk = cells[start:start+100000]
        for face in ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)):
            result |= np.isin(queries, records(np.sort(chunk[:, face], axis=1)))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "parent", "audit", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600)
    started = time.monotonic(); base = args.repository/"docs/research"
    geom = load(base/"935-local-cavity-20261105/source/assess_initial_cavities.py", "extreme_cavity_geometry", "ee60f26e2449fc2da97e34b0fa3f67c5472e0902b8a4166210e2089624887aa6")
    exact = load(base/"935-unoptimized-volume-20261105/source/inspect_interval_volume.py", "extreme_cavity_intervals", "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71")
    contract = load(base/"935-four-four-cavities-20261105/source/four_four_contract.py", "extreme_four_contract", "a5379daacb7a099810acf678110b74d4e6d9c5f34b01ac38fff1472a4ab0228c")
    four = load(base/"935-four-four-cavities-20261105/source/propose_four_four.py", "extreme_four_operator", "4298598e1fc5da3f28ad85fcb41cd5db427f5c5a6418f849b13c5bb07963c236")
    verify = load(base/"935-residual-cavities-20261105/source/verify_two_three.py", "extreme_quality_verifier", "a785594fcb77460057824a6fe31c192b2131c7907e535b9e458428bf0b578acb")
    edge = load(base/"935-condition-directed-20261105/source/verify_surface_peels.py", "extreme_edge_stars", "986bae3440420f1220b790f5ae8d54a92ebd427fb0c4a2c706712733317ddaf6")
    face = load(base/"935-local-physics-20261105/source/inspect_tetrahedra.py", "extreme_face_keys", "fe8c7fa88f35d2d14094438bbae3b0860bde085a39b68f7ab941790cb4d1bec3")
    tested = {"three_to_two": geom.controls(Path('/Users/maxime/Developer/PorschePartsArtifacts/935-constrained-relocation-20261105-001/topology-001/bipyramid-before.npz'), exact),
        "four_to_four": four.controls(Path('/Users/maxime/Developer/PorschePartsArtifacts/935-four-four-control-20261105-002/reference.npz'), geom, exact, contract, verify)}
    mesh = args.parent/"peel-proof/candidate-volume.npz"
    assert sha(mesh) == "a4b19f3303e55e4a13830829664e26596247d26cd41632704d4584706773538a"
    audit = json.loads((args.audit/"report.json").read_text())
    assert audit["source_sha256"] == "ae1eee889e95b31fff02eff9b08ec06f21d9678bf92dafa52a0d5c7c0bd92362"
    path = args.audit/"private-attribution-and-stars.json"
    assert sha(path) == audit["private_star_records_sha256"]
    stars = {}; boundary = {}
    for row in json.loads(path.read_text()):
        for item in row["edges"]:
            key = tuple(item["vertices"]); ids = item["complete_cell_ids"]
            assert key not in stars or stars[key] == ids
            stars[key] = ids; boundary[key] = item["boundary_face_ids"]
    with np.load(mesh, allow_pickle=False) as data:
        nodes, cells = data["nodes"], data["tets"]
    value_path = args.parent/"peeled-whole-condition/private-exact-severe-values.json"
    assert sha(value_path) == "e9747f2b6e05e8046039b2eb5622445a0141b8e6ca7edea8ba3ab27142aa3f11"
    source_values = json.loads(value_path.read_text())
    fractions = {row["cell_id"]: Fraction(*map(int, row["reciprocal_frobenius_squared"])) for row in source_values}
    worst = min(fractions, key=fractions.__getitem__)
    reasons = Counter(); candidates = []; diagnostics = []
    for center in sorted(stars):
        rows = stars[center]
        if boundary[center]:
            continue
        n = len(rows)
        if n not in (3, 4):
            reasons["other_valence_not_tested"] += 1; continue
        old = cells[rows]
        edge.cycle_link(old, center)
        old_q, signs, _ = geom.quality(nodes[old], exact); assert (signs > 0).all()
        source_extreme = sum(i in fractions and fractions[i]*10**30 <= 1 for i in rows)
        assert source_extreme > 0
        info = {"center": list(center), "old_rows": rows, "valence": n, "contains_global_worst": worst in rows}
        if n == 4:
            support, fallback, coplanar = contract.strict_support(nodes, old[None], np.array([center]), exact)
            hull = bool(support[0]); info.update(strict_support_passed=hull, exact_support_fallbacks=fallback, known_coplanar_support_rejections=coplanar)
            options = four.alternatives(nodes, old[None], np.array([center]), geom, exact, contract) if hull else []
        else:
            ring = sorted(set(map(int, old.ravel()))-set(center)); assert len(ring) == 3
            points = np.array([*center, *ring])
            hull = bool(geom.convex(nodes[points][None], exact)[0][0]); info["strict_support_passed"] = hull
            new = np.array([[*ring, center[0]], [*ring, center[1]]])
            q, signs, _ = geom.quality(nodes[new], exact); new[signs < 0] = new[signs < 0][:, [0, 2, 1, 3]]
            options = [(new[None], np.array([ring]), q[None], signs[None])] if hull else []
        if not hull:
            reasons[f"degree_{n}_strict_hull_rejected"] += 1
        for index, (proposed, entity, quality, signs) in enumerate(options):
            new = proposed[0]; q = quality[0]
            chain = bool(contract.chain_equal(old[None], proposed)[0]) if n == 4 else bool(geom.boundary_chain_equal(old[None], proposed)[0])
            passes = bool((q >= .01).all() and (signs != 0).all() and chain)
            passes &= all(int((q < t).sum()) <= int((old_q < t).sum()) for t in contract.BINS)
            info[f"alternative_{index}"] = {"minimum_new_quality": float(q.min()), "quality_and_chain_passed": passes}
            if passes:
                candidates.append({"center": center, "old_rows": rows, "new": new, "entity": entity[0], "degree": n, "gain": source_extreme, "contains_global_worst": worst in rows})
            else:
                reasons[f"degree_{n}_quality_or_chain_rejected_alternative"] += 1
        diagnostics.append(info)
    edge_candidates = [c for c in candidates if c["degree"] == 4]
    face_candidates = [c for c in candidates if c["degree"] == 3]
    new_edge_stars = edge.all_edge_cells(cells, {edge.key(*c["entity"]) for c in edge_candidates})
    central = face.records(np.sort(np.array([c["entity"] for c in face_candidates], dtype=np.uint32).reshape(-1, 3), axis=1))
    present = central_faces_present(cells, central, face.records) if len(central) else np.array([], bool)
    admissible = []
    for c in edge_candidates:
        if new_edge_stars[edge.key(*c["entity"])]:
            reasons["new_edge_already_present"] += 1
        else:
            admissible.append(c)
    for c, occupied in zip(face_candidates, present):
        if occupied:
            reasons["new_face_already_present"] += 1
        else:
            admissible.append(c)
    selected = []; used = set(); entities = set()
    for c in sorted(admissible, key=lambda c: (-int(c["contains_global_worst"]), -c["gain"], c["center"], tuple(c["entity"]))):
        entity = tuple(map(int, c["entity"]))
        if used & set(c["old_rows"]) or entity in entities:
            reasons["packing_conflict"] += 1; continue
        used.update(c["old_rows"]); entities.add(entity); selected.append(c)
    private = args.output/"private-assessed-stars.json"; private.write_text(json.dumps(diagnostics, separators=(",", ":"))+"\n")
    proposal = args.output/"private-selected-flips.json"
    proposal.write_text(json.dumps([{**c, "new": c["new"].tolist(), "entity": c["entity"].tolist()} for c in selected], separators=(",", ":"))+"\n")
    result = {"source_sha256": sha(Path(__file__)), "mesh_sha256": sha(mesh), "controls": tested,
        "unique_extreme_incident_interior_edges": int(sum(not boundary[e] for e in stars)),
        "degree_three_or_four_stars_assessed": len(diagnostics), "reasons": dict(reasons),
        "admissible_alternatives": len(admissible), "packed_cavities": len(selected),
        "contains_global_worst": any(c["contains_global_worst"] for c in selected),
        "extreme_source_cells_replaced_if_applied": int(sum(c["gain"] for c in selected)),
        "all_new_cells_must_meet_mean_ratio": .01, "all_five_quality_bins_nonregressing": True,
        "exact_same_oriented_boundary_required": True, "strict_hull_not_weakened": True,
        "private_diagnostics_sha256": sha(private), "private_proposals_sha256": sha(proposal),
        "geometry_or_connectivity_modified": False, "separate_verification_required_before_export": True,
        "physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0,
        "seconds": time.monotonic()-started}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
