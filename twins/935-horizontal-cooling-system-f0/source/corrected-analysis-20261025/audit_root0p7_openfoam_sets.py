"""Locate native OpenFOAM O5 mesh failures against the pinned 935 boundary."""

import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np


VOLUME_SHA = "b62927d017b78a784bce79d8117a1899b05b6aefffe0fa2c926fa291ca2108d9"
CELL_SETS = {"underdeterminedCells": 95978, "twoInternalFacesCells": 7891,
             "oneInternalFaceCells": 13, "highAspectRatioCells": 22}
FACE_SETS = {"nonOrthoFaces": 170609, "skewFaces": 1864,
             "lowWeightFaces": 11685, "lowVolRatioFaces": 1135}
INTERNAL_FACES = 6981228


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_set(path, expected, upper_bound):
    match = re.search(r"\n(\d+)\s*\n\(\s*([\d\s]+)\)", Path(path).read_text())
    if not match or int(match.group(1)) != expected:
        raise ValueError(f"Unexpected OpenFOAM set header: {path}")
    values = np.fromstring(match.group(2), sep=" ", dtype=np.int64)
    if len(values) != expected or len(np.unique(values)) != expected or values.min() < 0 or values.max() >= upper_bound:
        raise ValueError(f"Invalid OpenFOAM set indices: {path}")
    return values


def boundary_labels(faces, boundary, markers):
    row = np.dtype((np.void, boundary.dtype.itemsize * 3))
    keys = np.ascontiguousarray(np.sort(boundary, axis=1)).view(row).ravel()
    order = np.argsort(keys)
    if np.any(keys[order][1:] == keys[order][:-1]):
        raise ValueError("Duplicate boundary triangles")
    queries = np.ascontiguousarray(np.sort(faces, axis=1)).view(row).ravel()
    places = np.searchsorted(keys[order], queries)
    labels = np.zeros(len(queries), dtype=markers.dtype)
    valid = places < len(keys)
    valid[valid] = keys[order][places[valid]] == queries[valid]
    labels[valid] = markers[order[places[valid]]]
    return labels


def main(volume_path, sets_dir, skew_faces_path, log_path, output_path):
    root = Path(__file__).resolve().parents[4]
    output = Path(output_path).resolve()
    if not output.is_relative_to(root / "work") or output.exists():
        raise ValueError("Use a new private output under ignored work/")
    if sha(volume_path) != VOLUME_SHA:
        raise ValueError("Audited O5 volume changed")
    log = Path(log_path).read_text()
    if "Failed 5 mesh checks." not in log or "cells:            3714547" not in log:
        raise ValueError("Native checkMesh result changed")
    with np.load(volume_path) as data:
        vertices = data["vertices"]
        cells = data["tetrahedra"]
        boundary = data["boundary"]
        markers = data["markers"]
    if (len(vertices), len(cells), len(boundary)) != (817235, 3714547, 895732):
        raise ValueError("Unexpected O5 volume topology")
    if dict(zip(*np.unique(markers, return_counts=True))) != {1: 2304, 2: 2304, 3: 12394, 4: 878730}:
        raise ValueError("Unexpected O5 boundary markers")

    sets_dir = Path(sets_dir)
    report = {"schema": "935-root-0p7-native-failure-localization-v1",
              "source_sha256": sha(__file__), "volume_npz_sha256": VOLUME_SHA,
              "checkMesh_log_sha256": sha(log_path), "marker_map": {"1": "inlet", "2": "outlet", "3": "duct", "4": "rotor"},
              "cell_sets": {}, "face_sets": {}, "scale_verified": False, "CFD_accepted": False}
    face_corners = np.array([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]])
    underdetermined_centers = None
    for name, count in CELL_SETS.items():
        path = sets_dir / name
        indices = read_set(path, count, len(cells))
        tetrahedra = cells[indices]
        labels = boundary_labels(tetrahedra[:, face_corners].reshape(-1, 3), boundary, markers).reshape(-1, 4)
        centers = vertices[tetrahedra].mean(axis=1)
        radii = np.hypot(centers[:, 0], centers[:, 1])
        report["cell_sets"][name] = {
            "cells": count, "set_sha256": sha(path),
            "touching_marker_cells": {str(i): int(np.any(labels == i, axis=1).sum()) for i in range(1, 5)},
            "touching_no_boundary": int(np.all(labels == 0, axis=1).sum()),
            "radius_0p08_to_0p10_m_cells": int(((radii >= .08) & (radii < .10)).sum()),
        }
        if name == "underdeterminedCells":
            underdetermined_centers = centers

    for name, count in FACE_SETS.items():
        path = sets_dir / name
        indices = read_set(path, count, 7876960)
        report["face_sets"][name] = {"faces": count, "internal_faces": int((indices < INTERNAL_FACES).sum()),
                                      "boundary_faces": int((indices >= INTERNAL_FACES).sum()), "set_sha256": sha(path)}

    skew = json.loads(Path(skew_faces_path).read_text())
    skew_ids = read_set(sets_dir / "skewFaces", FACE_SETS["skewFaces"], 7876960)
    if set(map(int, skew)) != set(skew_ids[skew_ids >= INTERNAL_FACES]):
        raise ValueError("Skew boundary faces do not match OpenFOAM set")
    skew_triangles = np.asarray(list(skew.values()), dtype=np.int64)
    if skew_triangles.shape != (1850, 3) or not np.all(boundary_labels(skew_triangles, boundary, markers) == 4):
        raise ValueError("A skew boundary face is not an O5 rotor triangle")
    skew_centers = vertices[skew_triangles].mean(axis=1)
    skew_radii = np.hypot(skew_centers[:, 0], skew_centers[:, 1])
    under_radii = np.hypot(underdetermined_centers[:, 0], underdetermined_centers[:, 1])
    report["skew_boundary_face_source_sha256"] = sha(skew_faces_path)
    report["skew_boundary_faces_by_marker"] = {"4": 1850}
    report["radial_0p08_to_0p10_m_hotspot"] = {
        "underdetermined_cells": int(((under_radii >= .08) & (under_radii < .10)).sum()),
        "skew_rotor_boundary_faces": int(((skew_radii >= .08) & (skew_radii < .10)).sum()),
    }
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["radial_0p08_to_0p10_m_hotspot"]))


if __name__ == "__main__":
    if len(sys.argv) != 6:
        raise SystemExit("usage: audit_root0p7_openfoam_sets.py VOLUME_NPZ SETS_DIR SKEW_BOUNDARY_JSON CHECKMESH_LOG NEW_PRIVATE_JSON")
    main(*sys.argv[1:])
