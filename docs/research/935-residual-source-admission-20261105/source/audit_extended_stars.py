#!/usr/bin/env python3
"""Exact supporting-plane admission of complete valence-3-to-8 edge stars."""
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

FACES = np.array([[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]])


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def support(nodes, cells, center, predicates):
    vertices = sorted(set(map(int, cells.ravel())))
    assert len(vertices) == len(cells)+2
    boundary = [face for tet in cells for face in tet[FACES] if not all(v in face for v in center)]
    assert len(boundary) == 2*len(cells)
    rows = np.array([[*map(int, face), vertex] for face in boundary for vertex in vertices if vertex not in face])
    low, high = predicates.determinant_interval(nodes[rows])
    signs = np.where(high < 0, -1, np.where(low > 0, 1, 0))
    ambiguous = np.flatnonzero(signs == 0)
    for i in ambiguous:
        value = predicates.exact_determinant(nodes[rows[i]])
        signs[i] = int(value > 0)-int(value < 0)
    counts = Counter(map(int, signs))
    return {"strict_support": counts[0] == counts[1] == 0,
        "weak_support": counts[1] == 0, "negative_inside_probes": counts[-1],
        "exact_coplanar_probes": counts[0], "positive_outside_probes": counts[1],
        "exact_fallbacks": len(ambiguous)}


def controls(predicates):
    ring = np.array([[1., 0, 0], [.5, 1, 0], [-.5, 1, 0], [-1, 0, 0], [-.5, -1, 0], [.5, -1, 0]])
    nodes = np.vstack(([0., 0, 1], [0., 0, -1], ring))
    cells = np.array([[0, 1, 2+i, 2+(i+1)%6] for i in range(6)])
    for i in range(len(cells)):
        if predicates.exact_determinant(nodes[cells[i]]) < 0:
            cells[i, [1, 2]] = cells[i, [2, 1]]
    assert support(nodes, cells, (0, 1), predicates)["strict_support"]
    wrong = nodes.copy(); wrong[2] = [.1, 0, 0]
    assert not support(wrong, cells, (0, 1), predicates)["weak_support"]
    # A duplicated coplanar supporting edge is not a strictly convex cavity.
    flat = nodes.copy(); flat[2] = [.5, 0, 0]
    result = support(flat, cells, (0, 1), predicates)
    assert result["exact_coplanar_probes"] > 0 and not result["strict_support"]
    return {"literal_convex_hexagonal_bipyramid": True, "nonconvex_source_refused": True,
        "exact_coplanarity_distinguished_from_strict_support": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "parent", "audit", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    path = args.repository/"docs/research/935-unoptimized-volume-20261105/source/inspect_interval_volume.py"
    assert sha(path) == "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    spec = importlib.util.spec_from_file_location("extended_star_exact", path)
    predicates = importlib.util.module_from_spec(spec); spec.loader.exec_module(predicates)
    tested = controls(predicates)
    mesh = args.parent/"peel-proof/candidate-volume.npz"
    assert sha(mesh) == "a4b19f3303e55e4a13830829664e26596247d26cd41632704d4584706773538a"
    star_path = args.audit/"private-attribution-and-stars.json"
    assert sha(star_path) == "b7c8985c06875dfe3886e66389cc9039ae6b99f2f6be05932544e4e4be47e0ad"
    stars = {}
    for row in json.loads(star_path.read_text()):
        for edge in row["edges"]:
            if not edge["boundary_face_ids"]:
                stars[tuple(edge["vertices"])] = edge["complete_cell_ids"]
    with np.load(mesh, allow_pickle=False) as data:
        nodes, cells = data["nodes"], data["tets"]
    values = json.loads((args.parent/"peeled-whole-condition/private-exact-severe-values.json").read_text())
    worst = min(values, key=lambda row: Fraction(*map(int, row["reciprocal_frobenius_squared"])))['cell_id']
    rows = []; counts = Counter()
    for edge, ids in sorted(stars.items()):
        result = support(nodes, cells[ids], edge, predicates)
        label = "strict" if result["strict_support"] else "weak_only" if result["weak_support"] else "nonconvex"
        counts[f"degree_{len(ids)}_{label}"] += 1
        rows.append({"edge": list(edge), "source_cell_ids": ids, "valence": len(ids),
            "contains_global_worst": worst in ids, **result})
    private = args.output/"private-exact-support.json"; private.write_text(json.dumps(rows, separators=(",", ":"))+"\n")
    result = {"source_sha256": sha(Path(__file__)), "mesh_sha256": sha(mesh), "controls": tested,
        "complete_interior_stars_examined": len(rows), "exact_support_counts": dict(counts),
        "global_worst_incident_stars": [{k:v for k,v in row.items() if k not in ("edge", "source_cell_ids")} for row in rows if row["contains_global_worst"]],
        "strictly_supported_stars_beyond_valence_four": sum(r["strict_support"] and r["valence"] > 4 for r in rows),
        "private_support_sha256": sha(private), "geometry_or_connectivity_modified": False,
        "strict_support_does_not_by_itself_admit_a_replacement": True,
        "physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0,
        "seconds": time.monotonic()-started}
    (args.output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
