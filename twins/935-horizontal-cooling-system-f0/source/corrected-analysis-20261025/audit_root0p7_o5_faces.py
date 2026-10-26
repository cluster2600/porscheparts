"""Locate weak tetrahedra against the pinned exploratory 935 rotor wall."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from audit_root0p7_tet_quality import mean_ratio, triangle_quality


EXPECTED = "b62927d017b78a784bce79d8117a1899b05b6aefffe0fa2c926fa291ca2108d9"


def main(volume_path, output_path):
    volume = Path(volume_path)
    output = Path(output_path).resolve()
    if not output.is_relative_to((Path.cwd() / "work").resolve()) or output.exists():
        raise ValueError("A new private work/ output is required")
    digest = hashlib.sha256(volume.read_bytes()).hexdigest()
    if digest != EXPECTED:
        raise ValueError("Unexpected audited volume")
    with np.load(volume) as data:
        vertices = data["vertices"]
        cells = data["tetrahedra"]
        boundary = data["boundary"]
        markers = data["markers"]
    if len(cells) != 3714547 or len(boundary) != 895732:
        raise ValueError("Unexpected volume topology")

    ratios = np.concatenate([
        mean_ratio(vertices[cells[i:i + 100000]])
        for i in range(0, len(cells), 100000)
    ])
    weak = cells[ratios < .01]
    if len(weak) != 2929:
        raise ValueError("Unexpected weak-cell count")
    rotor = boundary[markers == 4]
    row = np.dtype((np.void, rotor.dtype.itemsize * 3))
    keys = np.ascontiguousarray(np.sort(rotor, axis=1)).view(row).ravel()
    order = np.argsort(keys)
    sorted_keys = keys[order]
    if np.any(sorted_keys[1:] == sorted_keys[:-1]):
        raise ValueError("Duplicate rotor boundary face")
    faces = np.stack([
        weak[:, [1, 2, 3]], weak[:, [0, 3, 2]],
        weak[:, [0, 1, 3]], weak[:, [0, 2, 1]],
    ], axis=1).reshape(-1, 3)
    queries = np.ascontiguousarray(np.sort(faces, axis=1)).view(row).ravel()
    locations = np.searchsorted(sorted_keys, queries)
    matches = np.zeros(len(queries), dtype=bool)
    valid = locations < len(sorted_keys)
    matches[valid] = sorted_keys[locations[valid]] == queries[valid]
    face_count = matches.reshape(-1, 4).sum(axis=1)
    incident = rotor[order[locations[matches]]]
    incident_quality = triangle_quality(vertices[incident])
    all_quality = triangle_quality(vertices[rotor])

    report = {
        "status": "o5_weak_rotor_face_audit",
        "volume_npz_sha256": digest,
        "weak_cells": len(weak),
        "weak_with_complete_rotor_boundary_face": int(np.count_nonzero(face_count)),
        "weak_without_complete_rotor_boundary_face": int(np.count_nonzero(face_count == 0)),
        "incident_rotor_faces": int(matches.sum()),
        "incident_rotor_triangle_quality_median": float(np.median(incident_quality)),
        "incident_rotor_triangle_quality_lt_0p1": int(np.count_nonzero(incident_quality < .1)),
        "all_rotor_triangle_quality_median": float(np.median(all_quality)),
        "all_rotor_triangle_quality_lt_0p1": int(np.count_nonzero(all_quality < .1)),
        "CFD_admitted": False,
    }
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: audit_root0p7_o5_faces.py AUDITED_VOLUME_NPZ NEW_PRIVATE_JSON")
    main(sys.argv[1], sys.argv[2])
