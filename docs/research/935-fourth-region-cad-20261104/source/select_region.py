#!/usr/bin/env python3
"""Select acquired triangles around the independently replayed fourth-region sections."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["arrays", "frame", "sections", "intersections", "plan", "output"]:
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError("Existing selection output refused")
    pins = [(a.arrays, "dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a"),
            (a.frame, "3a5ffb7316148716b3668ec762e284feb67bda040cbda81ba7697cf39765b289"),
            (a.intersections, "1ee2ad7b6e6fdf24b3288c78ccb9ec4952a76f2a496ff2c35f887a728913fb04")]
    section_hashes = ["aea268a6c52a6976310aaeeddf8701cfa563a89b93f1a12f5d08c7af42f49c82",
                      "641d7d55a936a098f26be3f02a21fcbac882091fa936cd75aab1d57c5d6feefe",
                      "2d90e04ed43a2dbcd8fc8d4437678b03ec481f8ac83063eeb3adc34c31e0cb0a"]
    points, seeds = [], []
    for station, expected in zip([91, 94, 97], section_hashes, strict=True):
        path = a.sections / f"section-{station}.npz"
        pins.append((path, expected))
    for path, expected in pins:
        if sha(path) != expected:
            raise ValueError("Registered input mismatch: " + path.name)
    for station in [91, 94, 97]:
        with np.load(a.sections / f"section-{station}.npz", allow_pickle=False) as s:
            points.append(s["points_ABC"].reshape(-1, 3))
            seeds.append(s["source_face_ids"])
    with np.load(a.arrays, allow_pickle=False) as s:
        vertices, faces = s["vertices"], s["triangles"]
    frame = np.load(a.frame, allow_pickle=False)
    endpoints, seed_ids = np.concatenate(points), np.unique(np.concatenate(seeds))
    lo, hi = endpoints.min(axis=0), endpoints.max(axis=0)
    lo[:2] -= 1.; hi[:2] += 1.
    # Section-plane positions are fixed by the original registered stations, not rounded samples.
    lo[2], hi[2] = -97., -91.
    triangles_ABC = (vertices @ frame.T)[faces]
    eligible = np.flatnonzero(np.all(triangles_ABC.max(axis=1) >= lo, axis=1) &
                              np.all(triangles_ABC.min(axis=1) <= hi, axis=1))
    if not np.isin(seed_ids, eligible).all():
        raise ValueError("Search box did not retain every acquired seed face")
    edge_faces = defaultdict(list)
    for i, face in enumerate(faces[eligible]):
        for j in range(3):
            edge_faces[tuple(sorted((int(face[j]), int(face[(j + 1) % 3]))))].append(i)
    rows, cols = [], []
    for uses in edge_faces.values():
        for index in uses[1:]:
            rows += [uses[0], index]; cols += [index, uses[0]]
    graph = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(eligible), len(eligible))).tocsr()
    count, labels = connected_components(graph, directed=False)
    retained = np.unique(labels[np.searchsorted(eligible, seed_ids)])
    selected = eligible[np.isin(labels, retained)]
    source_vertices, local_faces = np.unique(faces[selected], return_inverse=True)
    v, f = vertices[source_vertices], local_faces.reshape(-1, 3)
    area2 = np.linalg.norm(np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]), axis=1)
    indexed_conflicts = np.intersect1d(selected, np.load(a.intersections, allow_pickle=False).ravel())
    report = {"scope": "Source-supported fourth search region; anatomy unresolved",
              "plan_sha256": sha(a.plan), "source_sha256": sha(__file__),
              "inputs_sha256": {str(path): expected for path, expected in pins},
              "search_box_ABC_mm": [lo.tolist(), hi.tolist()],
              "eligible_faces": len(eligible), "eligible_components": int(count),
              "retained_components": len(retained), "source_faces": len(f),
              "source_vertices": len(v), "seed_faces": len(seed_ids),
              "all_seed_faces_retained": bool(np.isin(seed_ids, selected).all()),
              "area_mm2": float(area2.sum() / 2), "zero_area_faces": int((area2 == 0).sum()),
              "indexed_intersection_faces": len(indexed_conflicts),
              "coincident_distinct_vertices": len(v) - len(np.unique(v, axis=0)),
              "size_admitted": bool(len(f) <= 60000),
              "defect_index_admitted": bool(not len(indexed_conflicts) and np.all(area2 > 0)),
              "coordinates_changed": False, "physical_acceptance": False,
              "manufacturing_authorized": False}
    a.output.mkdir(parents=True)
    np.savez_compressed(a.output / "selected-source.npz", vertices=v, triangles=f,
                        source_vertex_ids=source_vertices, source_face_ids=selected)
    (a.output / "selection.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ["eligible_faces", "eligible_components", "source_faces",
          "source_vertices", "retained_components", "all_seed_faces_retained", "zero_area_faces",
          "indexed_intersection_faces", "coincident_distinct_vertices", "size_admitted", "defect_index_admitted"]}))


if __name__ == "__main__":
    main()
