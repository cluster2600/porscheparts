#!/usr/bin/env python3
"""Private reversible PCA pose normalization and removal of exactly zero-area faces."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from audit_private_scan import read_obj


def normalize(vertices, faces):
    centre = vertices.mean(axis=0)
    centred = vertices - centre
    eigenvalues, eigenvectors = np.linalg.eigh(centred.T @ centred / len(vertices))
    axes = eigenvectors[:, [2, 1, 0]]
    for i in range(3):
        if axes[np.argmax(np.abs(axes[:, i])), i] < 0:
            axes[:, i] *= -1
    if np.linalg.det(axes) < 0:
        axes[:, 1] *= -1
    pose = centred @ axes
    matrix = np.eye(4)
    matrix[:3, :3] = axes.T
    matrix[:3, 3] = -axes.T @ centre
    inverse = np.linalg.inv(matrix)
    restored = pose @ inverse[:3, :3].T + inverse[:3, 3]
    error = float(np.max(np.linalg.norm(restored - vertices, axis=1)))
    limit = float(128 * np.finfo(float).eps * max(1, np.abs(vertices).max()))
    if error > limit or not np.allclose(axes.T @ axes, np.eye(3), atol=1e-12) or not np.isclose(np.linalg.det(axes), 1):
        raise ValueError("Rigid transform or round-trip error")
    triangles = vertices[faces]
    area2 = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1)
    removed = np.flatnonzero(area2 == 0)
    kept = faces[area2 != 0]
    return pose, kept, {
        "method": "global_right_handed_PCA_rigid_pose_only",
        "transform_source_to_normalized": matrix.tolist(), "transform_normalized_to_source": inverse.tolist(),
        "source_units": None, "scale_factor": 1, "scale_verified": False,
        "pca_eigenvalues_source_units_squared": eigenvalues.tolist(),
        "maximum_inverse_transform_error_source_units": error,
        "inverse_transform_error_limit_source_units": limit,
        "removed_face_indices_zero_based": removed.tolist(), "removed_exact_zero_area_faces": len(removed),
        "source_vertex_order_preserved": True, "nonzero_faces_preserved_without_reordering": True,
        "hole_filling_executed": False, "component_registration_executed": False,
        "measured_axis_or_datum_established": False, "source_identity_verified": False,
        "solver_ready": False, "manufacturing_authorized": False,
    }


def prepare(source, output, expected_sha256):
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    if sha != expected_sha256:
        raise ValueError("Source hash differs from intake receipt")
    vertices, faces, ignored = read_obj(source)
    if ignored:
        raise ValueError("This private preparation supports position/face-only OBJ")
    pose, kept, report = normalize(vertices, faces)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    target = output / "pose-normalized-open-scan.obj"
    with target.open("x") as stream:
        stream.write("# Private research derivative: units unknown; not registered, repaired or qualified\n")
        for vertex in pose:
            stream.write("v " + " ".join(format(float(v), ".17g") for v in vertex) + "\n")
        for face in kept:
            stream.write("f " + " ".join(str(int(i) + 1) for i in face) + "\n")
    target.chmod(0o600)
    # Read the actual exported coordinates rather than only checking in-memory arrays.
    exported, exported_faces, _ = read_obj(target)
    if not np.array_equal(exported_faces, kept):
        raise ValueError("Exported face correspondence changed")
    inverse = np.asarray(report["transform_normalized_to_source"])
    error = float(np.max(np.linalg.norm(exported @ inverse[:3, :3].T + inverse[:3, 3] - vertices, axis=1)))
    if error > report["inverse_transform_error_limit_source_units"]:
        raise ValueError("Exported coordinate round-trip failed")
    if hashlib.sha256(source.read_bytes()).hexdigest() != sha:
        raise ValueError("Source changed during preparation")
    report.update({"status": "private_pose_normalization_not_registered_or_solver_ready",
        "source_sha256": sha, "export_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "exported_vertices": len(exported), "exported_faces": len(kept),
        "maximum_export_roundtrip_error_source_units": error,
        "publication_permission": "unconfirmed_private_only", "raw_unchanged": True})
    path = output / "transform-and-cleanup.json"
    path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    path.chmod(0o600)
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--expected-sha256", required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[3]
    out = args.output.resolve()
    if out.is_relative_to(root) and not out.is_relative_to(root / "work"):
        ap.error("All scan derivatives must remain in ignored work/ or outside the repository")
    report = prepare(args.source, out, args.expected_sha256)
    print("Private reversible pose prepared; " + str(report["removed_exact_zero_area_faces"]) + " zero-area faces removed; holes and relative component alignment unchanged")
