#!/usr/bin/env python3
"""Verify fixed source membership, training constraints and complete-face error bounds."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def polynomial(uv, c):
    u, v = uv[..., 0], uv[..., 1]
    return c[0] + u*(c[1]+u*c[3]) + v*(c[2]+u*c[4]+v*c[5])


def inspect(arrays, engineering, study):
    if sha(arrays) != "dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a":
        raise ValueError("Original arrays changed")
    manifest = engineering/"manifest.json"
    if sha(manifest) != "29b5ccb0c9bc3c6e31e451e555a1700e4334d4922d2720cbd1cd8eac7d2942c1":
        raise ValueError("Original mask manifest changed")
    masks = {v["path"]: v["sha256"] for v in json.loads(manifest.read_text())["files"]}
    with np.load(arrays, allow_pickle=False) as s:
        vertices, faces = s["vertices"], s["triangles"]
    result = json.loads((study/"study.json").read_text())
    if result["digital_limit_mm"] != .01 or len(result["regions"]) != 8:
        raise ValueError("Registered digital limit or region count changed")
    verified = []
    for i, record in enumerate(result["regions"]):
        name = f"chamber-candidates/chamber_planar_region_{i}-source-face-ids.npy"
        if sha(engineering/name) != masks[name] or record["mask_sha256"] != masks[name]:
            raise ValueError("Frozen mask changed")
        fi = np.load(engineering/name, allow_pickle=False)
        vi, inverse = np.unique(faces[fi], return_inverse=True)
        tri = inverse.reshape(-1, 3)
        xyz = vertices[vi]
        if record["state"] != "fitted_for_diagnostics":
            raise ValueError("This verifier requires the eight recorded diagnostic fits")
        edge_rows = np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
        face_rows = np.tile(np.arange(len(tri)), 3)
        _, grouping, uses = np.unique(edge_rows, axis=0, return_inverse=True, return_counts=True)
        order = np.argsort(grouping, kind="stable")
        starts = np.r_[0, np.cumsum(uses)[:-1]]
        two = starts[uses == 2]
        if np.any(uses > 2):
            raise ValueError("Original nonmanifold mask")
        pairs = face_rows[order[np.column_stack([two, two+1])]]
        graph = coo_matrix((np.ones(2*len(pairs)),
                            (np.r_[pairs[:, 0], pairs[:, 1]], np.r_[pairs[:, 1], pairs[:, 0]])),
                           shape=(len(tri), len(tri))).tocsr()
        count, _ = connected_components(graph, directed=False)
        if (count != record["topology"]["edge_connected_components"] or
                int((uses == 1).sum()) != record["topology"]["boundary_edges"]):
            raise ValueError("Recorded source topology changed")
        with np.load(study/f"region-{i}-models.npz", allow_pickle=False) as s:
            if not np.array_equal(s["original_source_face_ids"], fi) or not np.array_equal(s["original_source_vertex_ids"], vi):
                raise ValueError("Model source membership changed")
            origin, frame, scale, cs, recorded_bounds = (s[k] for k in
                ["origin", "frame", "uv_scale", "coefficients", "per_face_upper_bounds"])
        if not np.allclose(frame @ frame.T, np.eye(3), atol=1e-12, rtol=0):
            raise ValueError("Nonorthonormal correspondence frame")
        local = (xyz-origin) @ frame.T
        uv, height = local[:, :2]/scale, local[:, 2]
        training, heldout = vi % 5 != 0, vi % 5 == 0
        area = np.linalg.norm(np.cross(xyz[tri[:, 1]]-xyz[tri[:, 0]], xyz[tri[:, 2]]-xyz[tri[:, 0]]), axis=1)/2
        if np.any(area <= 0):
            raise ValueError("Degenerate source face")
        weights = np.zeros(len(vi))
        for j in range(3):
            np.add.at(weights, tri[:, j], area/3)
        if not np.allclose(origin, np.average(xyz[training], axis=0, weights=weights[training]), atol=1e-10, rtol=0):
            raise ValueError("Frame center is not training-only")
        covariance = (local[training]*weights[training, None]).T @ local[training]
        offdiag = covariance-np.diag(np.diag(covariance))
        if np.max(np.abs(offdiag)) > 1e-10*np.max(np.abs(covariance)):
            raise ValueError("Frame is not a training principal frame")
        if not np.allclose(scale, np.ptp(local[training, :2], axis=0), atol=1e-10, rtol=0):
            raise ValueError("Chart scale is not training-only")
        checks = []
        for index, (model, columns) in enumerate(zip(record["models"], [3, 6], strict=True)):
            c = cs[index]
            if model["coefficients"] != columns or (columns == 3 and np.any(c[3:] != 0)):
                raise ValueError("Polynomial degree changed")
            prediction = polynomial(uv, c)
            residual = prediction-height
            u, v = uv[training].T
            matrix = np.column_stack([np.ones(len(u)), u, v, u*u, u*v, v*v])[:, :columns]
            normal_residual = matrix.T @ (weights[training]*residual[training])
            if np.max(np.abs(normal_residual)) > 1e-8*max(1., float(weights.sum())):
                raise ValueError("Coefficients do not solve training-only normal equations")
            # Independent midpoint interpolation obtains Bernstein edge coefficients,
            # without the producer's quadratic Hessian expression.
            values = [residual[tri[:, j]] for j in range(3)]
            for a, b in [(0, 1), (1, 2), (2, 0)]:
                midpoint = (uv[tri[:, a]]+uv[tri[:, b]])/2
                middle_residual = polynomial(midpoint, c)-(height[tri[:, a]]+height[tri[:, b]])/2
                values.append(2*middle_residual-(residual[tri[:, a]]+residual[tri[:, b]])/2)
            bounds = np.max(np.abs(np.column_stack(values)), axis=1)
            if not np.allclose(bounds, recorded_bounds[index], atol=1e-9, rtol=1e-9):
                raise ValueError("Per-triangle Bernstein certificate changed")
            metrics = {"heldout_p95_mm": np.quantile(np.abs(residual[heldout]), .95),
                       "heldout_max_mm": np.max(np.abs(residual[heldout])),
                       "all_vertex_max_mm": np.max(np.abs(residual)),
                       "whole_triangle_correspondence_upper_bound_mm": bounds.max()}
            for name, value in metrics.items():
                if not np.isclose(model[name], value, atol=1e-9, rtol=1e-9):
                    raise ValueError("Recorded residual score changed")
            if (model["digital_bound_passed"] != bool(bounds.max() <= .01) or
                    model["vertex_limit_demonstrably_failed"] != bool(metrics["all_vertex_max_mm"] > .01)
                    or model["native_surface_admitted"] or model["physical_acceptance"]):
                raise ValueError("Unsupported acceptance flag")
            checks.append({"model": model["model"], "whole_triangle_bound_mm": float(bounds.max()),
                           "source_vertices_demonstrate_limit_failure": bool(metrics["all_vertex_max_mm"] > .01)})
        verified.append({"id": record["id"], "source_faces": len(tri),
                         "edge_connected_components": count, "models": checks})
    return {"status": "passed", "regions": verified,
            "checks": {"frozen_source_membership": True, "independent_source_connectivity": True,
                       "training_only_frame_scale_and_normal_equations": True,
                       "heldout_and_full_vertex_scores": True, "every_triangle_Bernstein_bounds": True,
                       "acceptance_flags": True},
            "source_sha256": sha(__file__), "physical_acceptance": False,
            "manufacturing_authorized": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["arrays", "engineering", "study", "output"]:
        p.add_argument("--"+name, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError("Existing surface verification refused")
    report = inspect(a.arrays, a.engineering, a.study)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("x") as stream:
        stream.write(json.dumps(report, indent=2)+"\n")
    print("Independent source/fit/full-triangle Bernstein verification passed.")


if __name__ == "__main__":
    main()
