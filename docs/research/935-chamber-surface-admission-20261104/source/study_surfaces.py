#!/usr/bin/env python3
"""Audit fixed source masks and bound plane/quadratic graph reconstruction error."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


MASK_SHA = [
    "d5627022685cda87535dce070b9097f841dfacd27205c2763237b6c6a4a2faa3",
    "f36a2874fea0b52308274761d8caf8bc6ea1d7baf31e35ed9542cc428007ebaa",
    "ae664abb663a73ff5f31668ee471ba07b3b7b1b43ecda0ee8d0d270b14589d69",
    "ebd25cce2baf21080cc4f4f2efcbf5ea81f422d7ea25a471000e17aeec5a18c4",
    "87aee6473fee7890d1de05ef99cccdc3edd27733e913ec521b2b4114551c0f4a",
    "95d7f0b764ef029d6833011df0350697800d51022d28b4d70aec50e4f808162a",
    "edc2d15579e8bcaace464547c254e2badd055cf2c080e3af4dc00d3f10a60788",
    "01aa07a7abe5423fb62336e3fb4384a340e55b5f310b0ca5f7721440a2fe732d"]


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def design(uv):
    u, v = np.moveaxis(uv, -1, 0)
    return np.stack([np.ones_like(u), u, v, u*u, u*v, v*v], axis=-1)


def bernstein_bound(uv, height, triangles, coefficients):
    """Coefficients in barycentric degree-two Bernstein form bound every face."""
    residual = design(uv) @ coefficients - height
    vertex_coeff = residual[triangles]
    q = np.array([[coefficients[3], coefficients[4]/2],
                  [coefficients[4]/2, coefficients[5]]])
    edge_coeff = []
    for i, j in [(0, 1), (1, 2), (2, 0)]:
        delta = uv[triangles[:, j]] - uv[triangles[:, i]]
        curvature = np.einsum("ij,jk,ik->i", delta, q, delta)
        edge_coeff.append((vertex_coeff[:, i] + vertex_coeff[:, j] - curvature)/2)
    values = np.column_stack([vertex_coeff, *edge_coeff])
    return np.max(np.abs(values), axis=1), values


def controls():
    uv = np.array([[0., 0.], [1., 0.], [0., 1.]])
    triangle = np.array([[0, 1, 2]])
    # q = u^2 + v^2, source triangle interpolates its vertex heights.
    c = np.array([0., 0., 0., 1., 0., 1.])
    bound, values = bernstein_bound(uv, np.array([0., 1., 1.]), triangle, c)
    assert abs(bound[0] - 1.) < 1e-14 and np.allclose(values[0], [0, 0, 0, -.5, -1, -.5])
    bound, _ = bernstein_bound(uv, np.array([0., 1., 1.]), triangle,
                               np.array([0., 1., 1., 0., 0., 0.]))
    assert bound[0] == 0
    bound, _ = bernstein_bound(uv, np.array([0., 0., 0.]), triangle,
                               np.array([.2, 0., 0., 0., 0., 0.]))
    assert abs(bound[0] - .2) < 1e-14
    return {"quadratic_interior_error_despite_exact_vertices": True,
            "exact_affine_graph": True, "constant_displacement": True}


def fit_region(vertices, faces, face_ids, helper, output):
    vi, local = np.unique(faces[face_ids], return_inverse=True)
    xyz, tri = vertices[vi], local.reshape(-1, 3)
    _, _, _, _, topology = helper.atlas(xyz, tri)
    area = np.linalg.norm(np.cross(xyz[tri[:, 1]] - xyz[tri[:, 0]],
                                   xyz[tri[:, 2]] - xyz[tri[:, 0]]), axis=1)/2
    weights = np.bincount(tri.ravel(), weights=np.repeat(area/3, 3), minlength=len(xyz))
    heldout = vi % 5 == 0
    training = ~heldout
    if training.sum() < 40 or heldout.sum() < 10:
        raise ValueError("Insufficient fixed source-ID split")
    origin = np.average(xyz[training], axis=0, weights=weights[training])
    _, singular, frame = np.linalg.svd((xyz[training]-origin)*np.sqrt(weights[training, None]), full_matrices=False)
    if singular[1] <= 1e-12:
        raise ValueError("Rank-deficient source support")
    coordinates = (xyz-origin) @ frame.T
    scale = np.ptp(coordinates[training, :2], axis=0)
    if np.any(scale <= 1e-12):
        raise ValueError("Degenerate training chart")
    uv, h = coordinates[:, :2]/scale, coordinates[:, 2]
    matrix = design(uv)
    results, coefficients, certificates = [], [], []
    for name, columns in [("plane", 3), ("quadratic", 6)]:
        weighted = matrix[training, :columns]*np.sqrt(weights[training, None])
        c, _, rank, _ = np.linalg.lstsq(weighted, h[training]*np.sqrt(weights[training]), rcond=None)
        if rank != columns:
            raise ValueError("Rank-deficient polynomial fit")
        c = np.pad(c, (0, 6-columns))
        error = np.abs(matrix @ c-h)
        bounds, _ = bernstein_bound(uv, h, tri, c)
        results.append({"model": name, "coefficients": columns,
                        "heldout_vertices": int(heldout.sum()),
                        "heldout_p95_mm": float(np.quantile(error[heldout], .95)),
                        "heldout_max_mm": float(error[heldout].max()),
                        "all_vertex_max_mm": float(error.max()),
                        "whole_triangle_correspondence_upper_bound_mm": float(bounds.max()),
                        "digital_bound_passed": bool(bounds.max() <= .01),
                        "vertex_limit_demonstrably_failed": bool(error.max() > .01),
                        "native_surface_admitted": False, "physical_acceptance": False})
        coefficients.append(c); certificates.append(bounds)
    np.savez_compressed(output, original_source_vertex_ids=vi, original_source_face_ids=face_ids,
                        origin=origin, frame=frame, uv_scale=scale, coefficients=np.array(coefficients),
                        per_face_upper_bounds=np.array(certificates))
    return {"source_faces": len(tri), "source_vertices": len(xyz), "topology": topology,
            "models": results}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["arrays", "masks", "intersections", "helper", "plan", "output"]:
        p.add_argument("--"+name, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError("Existing surface-study output refused")
    pins = [(a.arrays, "dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a"),
            (a.intersections, "1ee2ad7b6e6fdf24b3288c78ccb9ec4952a76f2a496ff2c35f887a728913fb04"),
            (a.helper, "fca5259ef3b3412a72e441fea39816e14fea4e375095e1c83def2e4117f6ae8e")]
    pins += [(a.masks/f"chamber_planar_region_{i}-source-face-ids.npy", h) for i, h in enumerate(MASK_SHA)]
    for path, expected in pins:
        if sha(path) != expected:
            raise ValueError("Registered source/mask/helper changed: "+path.name)
    checks = controls()
    with np.load(a.arrays, allow_pickle=False) as s:
        vertices, faces = s["vertices"], s["triangles"]
    conflicts = np.unique(np.load(a.intersections, allow_pickle=False))
    spec = importlib.util.spec_from_file_location("retained_source_topology_audit", a.helper)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    a.output.mkdir(parents=True)
    regions = []
    for i in range(8):
        ids = np.load(a.masks/f"chamber_planar_region_{i}-source-face-ids.npy", allow_pickle=False)
        record = {"id": f"historical_chamber_region_{i}", "mask_sha256": MASK_SHA[i]}
        if len(np.intersect1d(ids, conflicts)):
            record.update(state="upstream_rejected", reason="Original indexed intersection face")
        else:
            try:
                result = fit_region(vertices, faces, ids, helper, a.output/f"region-{i}-models.npz")
                record.update(state="fitted_for_diagnostics", **result)
            except ValueError as error:
                record.update(state="not_fitted", reason=str(error))
        regions.append(record)
    report = {"scope": "Fixed chamber-search masks; no anatomical or functional acceptance",
              "source_sha256": sha(__file__), "plan_sha256": sha(a.plan),
              "input_sha256": {str(path): expected for path, expected in pins},
              "digital_limit_mm": .01, "controls": checks, "regions": regions,
              "models_exported_as_native_CAD": False, "physical_metrology_accepted": False,
              "manufacturing_authorized": False}
    (a.output/"study.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"regions": [{"id": r["id"], "state": r["state"],
                      "models": r.get("models", []), "reason": r.get("reason")} for r in regions]}))


if __name__ == "__main__":
    main()
