"""Account for every acquired triangle before a complete source-CAD atlas trial."""
import argparse
from collections import deque
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2)+"\n")


def load(path, name, expected):
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def exact_nonzero(points):
    p = [[F.from_float(float(x)) for x in point] for point in points]
    a = [p[1][i]-p[0][i] for i in range(3)]; b = [p[2][i]-p[0][i] for i in range(3)]
    return any(a[i]*b[j]-a[j]*b[i] for i, j in ((1, 2), (2, 0), (0, 1)))


def nonzero_mask(vertices, faces, interval):
    output = np.zeros(len(faces), bool); exact_count = 0
    for start in range(0, len(faces), 50000):
        p = vertices[faces[start:start+50000]]
        a = interval.subtract((p[:, 1], p[:, 1]), (p[:, 0], p[:, 0]))
        b = interval.subtract((p[:, 2], p[:, 2]), (p[:, 0], p[:, 0]))
        certain = np.zeros(len(p), bool)
        for i, j in ((1, 2), (2, 0), (0, 1)):
            first = interval.multiply((a[0][:, i], a[1][:, i]), (b[0][:, j], b[1][:, j]))
            second = interval.multiply((a[0][:, j], a[1][:, j]), (b[0][:, i], b[1][:, i]))
            low, high = interval.subtract(first, second)
            certain |= (low > 0) | (high < 0)
        for index in np.flatnonzero(~certain):
            certain[index] = exact_nonzero(p[index]); exact_count += 1
        output[start:start+len(p)] = certain
    return output, exact_count


def edges(faces, vertex_count):
    values = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    keys = values.min(1)*vertex_count+values.max(1)
    order = np.argsort(keys, kind="stable"); keys = keys[order]
    uses = np.tile(np.arange(len(faces), dtype=np.int64), 3)[order]
    forward = (values[:, 0] < values[:, 1])[order]
    starts = np.r_[0, np.flatnonzero(keys[1:] != keys[:-1])+1]
    counts = np.diff(np.r_[starts, len(keys)])
    bad_multi = np.flatnonzero(counts > 2)
    pairs = starts[counts == 2]
    bad_winding = pairs[forward[pairs] == forward[pairs+1]]
    multi_faces = np.unique(np.concatenate([uses[starts[i]:starts[i]+counts[i]] for i in bad_multi])) if len(bad_multi) else np.empty(0, np.int64)
    winding_faces = np.unique(np.r_[uses[bad_winding], uses[bad_winding+1]])
    adjacency = keys[1:] == keys[:-1]
    first, second = uses[:-1][adjacency], uses[1:][adjacency]
    graph = coo_matrix((np.ones(len(first), bool), (first, second)), shape=(len(faces), len(faces))).tocsr()
    graph = graph.maximum(graph.T); graph.sort_indices()
    return graph, multi_faces, winding_faces, {"source_edges": len(starts), "boundary_edges": int((counts == 1).sum()),
        "nonmanifold_edges": len(bad_multi), "inconsistently_wound_two_use_edges": len(bad_winding)}


def controls(interval):
    vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [2, 0, 0], [0, 0, 2.**-70]], float)
    faces = np.array([[0, 1, 2], [1, 3, 2], [0, 1, 4], [0, 1, 5]])
    good, _ = nonzero_mask(vertices, faces, interval); assert good.tolist() == [True, True, False, True]
    graph, multi, winding, info = edges(faces[:2], len(vertices))
    assert connected_components(graph, directed=False)[0] == 1 and info["boundary_edges"] == 4
    assert len(multi) == len(winding) == 0
    _, _, winding, _ = edges(np.array([[0, 1, 2], [1, 2, 3]]), 6); assert winding.tolist() == [0, 1]
    _, multi, _, _ = edges(np.array([[0, 1, 2], [1, 0, 3], [0, 1, 5]]), 6); assert multi.tolist() == [0, 1, 2]
    point = np.array([[0, 1, 2], [0, 3, 4]])
    assert connected_components(edges(point, 6)[0], directed=False)[0] == 2
    return {"exact_degenerate_and_thin_triangle_controls": True, "shared_edge_and_point_contact_distinguished": True,
            "inconsistent_winding_and_nonmanifold_source_uses_found": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "arrays", "intersections", "paper", "observed-sheet", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    assert sha(args.arrays) == "dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a"
    assert sha(args.intersections) == "1ee2ad7b6e6fdf24b3288c78ccb9ec4952a76f2a496ff2c35f887a728913fb04"
    interval = load(args.repository/"docs/research/935-unoptimized-volume-20261105/source/inspect_interval_volume.py", "source_triangle_intervals", "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71")
    checked = controls(interval); save(args.output/"controls.json", checked)
    with np.load(args.arrays, allow_pickle=False) as data:
        vertices, faces = data["vertices"], data["triangles"]
    assert vertices.shape == (1281608, 3) and faces.shape == (2466040, 3)
    assert np.isfinite(vertices).all() and faces.min() >= 0 and faces.max() < len(vertices)
    reasons = np.zeros(len(faces), np.uint8)
    nonzero, fallback = nonzero_mask(vertices, faces, interval); reasons[~nonzero] |= 1
    indexed = np.unique(np.load(args.intersections, allow_pickle=False)); reasons[indexed] |= 2
    _, inverse, multiplicity = np.unique(vertices, axis=0, return_inverse=True, return_counts=True)
    duplicate_vertices = multiplicity[inverse] > 1
    reasons[np.any(duplicate_vertices[faces], axis=1)] |= 4
    initial_ids = np.flatnonzero(reasons == 0)
    _, multi, winding, initial_edges = edges(faces[initial_ids], len(vertices))
    reasons[initial_ids[multi]] |= 8; reasons[initial_ids[winding]] |= 16
    admitted = np.flatnonzero(reasons == 0); quarantined = np.flatnonzero(reasons != 0)
    graph, multi, winding, final_edges = edges(faces[admitted], len(vertices)); assert len(multi) == len(winding) == 0
    component_count, labels = connected_components(graph, directed=False)
    counts = np.bincount(labels, minlength=component_count)
    # Fixed exhaustive traversal: smallest remaining source ID, sorted neighbors,
    # no spatial welding or anatomical component interpretation.
    seen = np.zeros(len(admitted), bool); order = []
    for seed in range(len(admitted)):
        if seen[seed]:
            continue
        queue = deque([seed]); seen[seed] = True
        while queue:
            row = queue.popleft(); order.append(row)
            for neighbor in graph.indices[graph.indptr[row]:graph.indptr[row+1]]:
                if not seen[neighbor]:
                    seen[neighbor] = True; queue.append(int(neighbor))
    assert len(order) == len(admitted) and seen.all()
    ordered = admitted[np.asarray(order, np.int64)]
    chunk_limit = 30000; chunks = [ordered[i:i+chunk_limit] for i in range(0, len(ordered), chunk_limit)]
    chunk_owner = np.full(len(faces), -1, np.int32)
    for i, ids in enumerate(chunks):chunk_owner[ids] = i
    prior = []
    for i in (1, 2, 3):
        with np.load(args.paper/("stud_passage_"+str(i)+"_wall_candidate-partition.npz"), allow_pickle=False) as data:
            prior.extend(data["selected_source_face_ids"])
    with np.load(args.observed_sheet, allow_pickle=False) as data:prior.extend(data["source_face_ids"])
    prior = np.unique(prior); assert len(prior) == 18682
    assert np.array_equal(np.sort(np.r_[admitted, quarantined]), np.arange(len(faces)))
    output = args.output/"private-source-atlas-plan.npz"
    np.savez_compressed(output, admitted_source_face_ids=admitted, quarantined_source_face_ids=quarantined,
                        source_quarantine_reason_bits=reasons, source_traversal_face_ids=ordered,
                        source_chunk_owner=chunk_owner, source_component_labels=labels)
    lengths = np.linalg.norm(vertices[faces[:, [1, 2, 0]]]-vertices[faces], axis=2)
    result = {"source_sha256": sha(Path(__file__)), "arrays_sha256": sha(args.arrays), "intersection_index_sha256": sha(args.intersections),
        "controls": checked, "all_acquired_faces_accounted": len(faces), "source_vertices": len(vertices),
        "exact_degenerate_triangles": int((~nonzero).sum()), "exact_triangle_fallbacks": fallback,
        "faces_in_legacy_intersection_index": len(indexed), "coincident_distinct_source_vertex_ids": int(duplicate_vertices.sum()),
        "source_faces_quarantined": len(quarantined), "source_faces_admitted_for_CAD_trial": len(admitted),
        "quarantine_reason_counts_not_disjoint": {str(bit): int(((reasons & bit) != 0).sum()) for bit in (1, 2, 4, 8, 16)},
        "initial_edge_audit": initial_edges, "admitted_edge_audit": final_edges,
        "admitted_edge_components": int(component_count), "largest_admitted_component_faces": int(counts.max()),
        "planned_native_chunks": len(chunks), "maximum_faces_per_native_chunk": chunk_limit,
        "prior_exact_CAD_source_faces": len(prior), "prior_faces_admitted_in_new_plan": int((reasons[prior] == 0).sum()),
        "source_edge_length_quantiles_nominal_mm": dict(zip(("minimum", "p01", "median", "maximum"), map(float, np.quantile(lengths, (0, .01, .5, 1))))),
        "source_edges_below_1e_minus7_nominal_mm": int((lengths < 1e-7).sum()),
        "private_plan_sha256": sha(output), "source_coordinates_or_faces_modified": False,
        "quarantined_records_retained_in_original": True, "anatomical_identity_inferred": False,
        "native_CAD_construction_not_yet_executed": True, "physical_acceptance": False, "manufacturing_authorized": False,
        "new_paid_compute_usd": 0, "seconds": time.monotonic()-started}
    save(args.output/"report.json", result); signal.alarm(0); print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
