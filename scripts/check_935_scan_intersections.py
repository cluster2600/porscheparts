#!/usr/bin/env python3
"""Inspect the frozen OBJ without welding, scaling, repairing or releasing it."""
import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import sys
import time

import igl
import igl.predicates
import numpy as np

SOURCE_SHA = "4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486"
# Independently measured with the previously executed Trimesh 4.7.4 reader.
VERTICES_SHA = "9c62ec1ff0cb72a26908878cd8607699745d0c7da20a5f9705a0003c04c695e2"
FACES_SHA = "84177b945a073ff4f30c75983131584c2b7ed7101f9570b38d95894e8d013303"


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def detect(vertices, faces):
    vertices, faces = np.asarray(vertices), np.asarray(faces)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
        raise ValueError("invalid vertices")
    if faces.ndim != 2 or faces.shape[1] != 3 or faces.dtype.kind not in "iu":
        raise ValueError("invalid faces")
    if len(faces) and (faces.min() < 0 or faces.max() >= len(vertices)):
        raise ValueError("face index outside vertices")
    cross = np.cross(vertices[faces[:, 1]] - vertices[faces[:, 0]],
                     vertices[faces[:, 2]] - vertices[faces[:, 0]])
    keep = np.any(cross != 0, axis=1)
    source_ids = np.flatnonzero(keep)
    if not len(source_ids):
        return np.empty((0, 2), dtype=np.int64), np.empty(0, dtype=bool), np.flatnonzero(~keep)
    found, pairs, coplanar = igl.predicates.find_self_intersections(
        np.ascontiguousarray(vertices, dtype=np.float64),
        np.ascontiguousarray(faces[keep], dtype=np.int64), False)
    pairs = np.asarray(pairs).reshape((-1, 2))
    coplanar = np.asarray(coplanar).reshape(-1).astype(bool)
    if bool(found) != bool(len(pairs)) or len(coplanar) != len(pairs):
        raise ValueError("inconsistent detector result")
    if len(pairs) and (pairs.min() < 0 or pairs.max() >= len(source_ids)):
        raise ValueError("detector returned invalid face indices")
    return source_ids[pairs], coplanar, np.flatnonzero(~keep)


def controls():
    a = np.array([[-1,-1,0], [1,-1,0], [0,1,0]], dtype=float)
    b = np.array([[0,-.5,-1], [0,-.5,1], [0,.5,0]], dtype=float)
    f = np.array([[0,1,2], [3,4,5]])
    results = {}
    for name, v, faces, expected in [
        ("separated", np.vstack((a, a + [4,0,0])), f, False),
        ("crossing", np.vstack((a, b)), f, True),
        ("coplanar_overlap", np.vstack((a, a + [.2,0,0])), f, True),
        ("adjacent", np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0]], dtype=float), np.array([[0,1,2],[0,2,3]]), False),
    ]:
        pairs, cp, excluded = detect(v, faces)
        if bool(len(pairs)) != expected or len(excluded):
            raise ValueError("control failed: " + name)
        if name == "coplanar_overlap" and not cp.all():
            raise ValueError("coplanar flag control failed")
        results[name] = {"pairs": len(pairs), "coplanar_pairs": int(cp.sum())}
    pairs, _, excluded = detect(np.vstack((a,b)), np.vstack(([0,0,0],f)))
    if excluded.tolist() != [0] or {tuple(sorted(p)) for p in pairs.tolist()} != {(1,2)}:
        raise ValueError("original face-index mapping control failed")
    results["degenerate_face_mapping"] = "passed"
    try:
        detect(a, np.array([[0,1,99]]))
    except ValueError:
        results["invalid_face_rejection"] = "passed"
    else:
        raise ValueError("invalid face index admitted")
    return results


def run(source, output):
    if sha256(source) != SOURCE_SHA:
        raise ValueError("unexpected source SHA-256")
    if output.exists():
        raise FileExistsError(output)
    checks = controls()
    started = time.monotonic()
    vertices, faces = igl.read_triangle_mesh(str(source))
    vsha = hashlib.sha256(np.asarray(vertices, dtype="<f8").tobytes()).hexdigest()
    fsha = hashlib.sha256(np.asarray(faces, dtype="<i8").tobytes()).hexdigest()
    if (vsha, fsha) != (VERTICES_SHA, FACES_SHA):
        raise ValueError("OBJ reader disagrees with independent coordinate/connectivity hashes")
    pairs, coplanar, excluded = detect(vertices, faces)
    if sha256(source) != SOURCE_SHA:
        raise ValueError("source changed during inspection")
    output.mkdir(parents=True, exist_ok=False)
    np.save(output / "intersecting-source-face-pairs.npy", pairs)
    np.save(output / "coplanar-pair-flags.npy", coplanar)
    np.save(output / "excluded-zero-area-source-faces.npy", excluded)
    report = {
        "source_sha256": SOURCE_SHA, "vertices_sha256": vsha, "faces_sha256": fsha,
        "reader_agrees_with_independent_trimesh": True,
        "source_faces": len(faces), "tested_faces": len(faces) - len(excluded),
        "zero_area_faces_excluded_from_detector": len(excluded),
        "intersection_pairs": len(pairs), "coplanar_pairs": int(coplanar.sum()),
        "involved_source_faces": len(np.unique(pairs)),
        "welding": "none", "scaling": "none", "source_modified": False,
        "units": "unverified_OBJ_units", "print_ready": False,
        "scope": "raw scan triangle intersections; hardware contacts not classified",
        "controls": checks, "elapsed_seconds": time.monotonic() - started,
        "runtime": {p: metadata.version(p) for p in ("libigl", "numpy", "scipy")},
    }
    (output / "inspection.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "manifest.json").write_text(json.dumps(
        {p.name: sha256(p) for p in sorted(output.iterdir()) if p.is_file()}, indent=2) + "\n")
    return report


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        print(json.dumps(controls(), indent=2))
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("source", type=Path)
        parser.add_argument("output", type=Path)
        args = parser.parse_args()
        print(json.dumps(run(args.source, args.output), indent=2))
