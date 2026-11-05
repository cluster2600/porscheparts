#!/usr/bin/env python3
"""Check area-ranked selections independently, then recompute all graph certificates."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect(arrays, engineering, study, evaluator):
    if sha(arrays) != "dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a":
        raise ValueError("Original arrays changed")
    if sha(engineering/"manifest.json") != "29b5ccb0c9bc3c6e31e451e555a1700e4334d4922d2720cbd1cd8eac7d2942c1":
        raise ValueError("Original engineering manifest changed")
    if sha(evaluator) != "5edae0828f23856c2cc7eb942c9d8520b174433149fa478fee4ddb3826cf23d6":
        raise ValueError("Independent polynomial evaluator changed")
    spec = importlib.util.spec_from_file_location("retained_independent_polynomial", evaluator)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    pins = {p["path"]: p["sha256"] for p in json.loads((engineering/"manifest.json").read_text())["files"]}
    with np.load(arrays, allow_pickle=False) as s:
        vertices, faces = s["vertices"], s["triangles"]
    report = json.loads((study/"study.json").read_text())
    if len(report["regions"]) != 8:
        raise ValueError("Missing original regions")
    verified = []
    for i, record in enumerate(report["regions"]):
        path = f"chamber-candidates/chamber_planar_region_{i}-source-face-ids.npy"
        if sha(engineering/path) != pins[path]:
            raise ValueError("Original mask changed")
        parent = np.load(engineering/path, allow_pickle=False)
        pf = faces[parent]
        edges = np.sort(np.concatenate([pf[:, [0, 1]], pf[:, [1, 2]], pf[:, [2, 0]]]), axis=1)
        _, inverse, uses = np.unique(edges, axis=0, return_inverse=True, return_counts=True)
        order = np.argsort(inverse, kind="stable"); starts = np.r_[0, np.cumsum(uses)[:-1]][uses == 2]
        pairs = np.tile(np.arange(len(pf)), 3)[order[np.column_stack([starts, starts+1])]]
        graph = coo_matrix((np.ones(2*len(pairs)), (np.r_[pairs[:, 0], pairs[:, 1]], np.r_[pairs[:, 1], pairs[:, 0]])), shape=(len(pf), len(pf))).tocsr()
        count, labels = connected_components(graph, directed=False)
        xyz = vertices[pf]
        areas = np.linalg.norm(np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0]), axis=1)/2
        ranking = sorted([(float(areas[labels == k].sum()), int(parent[labels == k].min()), k)
                          for k in range(count)], key=lambda x: (-x[0], x[1]))
        expected = parent[labels == ranking[0][2]]
        with np.load(study/f"region-{i}-selection.npz", allow_pickle=False) as s:
            if (not np.array_equal(s["parent_original_face_ids"], parent) or
                    not np.array_equal(s["selected_original_face_ids"], expected)):
                raise ValueError("Selection is not the fixed largest-area source component")
            relations = np.unique(np.column_stack([s["component_labels"], labels]), axis=0)
            if len(relations) != count or any(len(np.unique(relations[:, k])) != count for k in [0, 1]):
                raise ValueError("Parent source component partition changed")
        ledger = record["component_ledger"]
        if len(ledger) != count or record["selected_faces"] != len(expected):
            raise ValueError("Component coverage changed")
        for item, (area, minimum, label) in zip(ledger, ranking, strict=True):
            if (item["minimum_original_face_id"] != minimum or item["faces"] != int((labels == label).sum()) or
                    not np.isclose(item["area_mm2"], area, rtol=1e-12, atol=1e-12)):
                raise ValueError("Recorded component ranking changed")
        vi, local = np.unique(faces[expected], return_inverse=True)
        tri = local.reshape(-1, 3); xyz = vertices[vi]
        if record["state"] != "fitted_for_diagnostics":
            raise ValueError("Unexpected refusal for the recorded connected-region dataset")
        with np.load(study/f"region-{i}-models.npz", allow_pickle=False) as s:
            if not np.array_equal(s["original_source_face_ids"], expected) or not np.array_equal(s["original_source_vertex_ids"], vi):
                raise ValueError("Fit source membership changed")
            origin, frame, scale, cs, stored = (s[k] for k in ["origin", "frame", "uv_scale", "coefficients", "per_face_upper_bounds"])
        coords = (xyz-origin) @ frame.T; uv, h = coords[:, :2]/scale, coords[:, 2]
        train, test = vi % 5 != 0, vi % 5 == 0
        areas = np.linalg.norm(np.cross(xyz[tri[:, 1]]-xyz[tri[:, 0]], xyz[tri[:, 2]]-xyz[tri[:, 0]]), axis=1)/2
        weights = np.zeros(len(vi))
        for k in range(3): np.add.at(weights, tri[:, k], areas/3)
        if (not np.allclose(frame @ frame.T, np.eye(3), atol=1e-12, rtol=0) or
                not np.allclose(origin, np.average(xyz[train], axis=0, weights=weights[train]), atol=1e-10, rtol=0) or
                not np.allclose(scale, np.ptp(coords[train, :2], axis=0), atol=1e-10, rtol=0)):
            raise ValueError("Training-only frame or scale changed")
        covariance = (coords[train]*weights[train, None]).T @ coords[train]
        if np.max(np.abs(covariance-np.diag(np.diag(covariance)))) > 1e-10*np.max(np.abs(covariance)):
            raise ValueError("Frame is not a training principal frame")
        checked = []
        for m, (model, columns) in enumerate(zip(record["models"], [3, 6], strict=True)):
            c = cs[m]
            if (model["coefficients"] != columns or model["heldout_vertices"] != int(test.sum()) or
                    (columns == 3 and np.any(c[3:] != 0))):
                raise ValueError("Fixed model degree or source split changed")
            residual = helper.polynomial(uv, c)-h
            u, v = uv[train].T
            design = np.column_stack([np.ones(len(u)), u, v, u*u, u*v, v*v])[:, :columns]
            if np.max(np.abs(design.T @ (weights[train]*residual[train]))) > 1e-8*max(1., weights.sum()):
                raise ValueError("Training-only fit equations changed")
            coefficients = [residual[tri[:, k]] for k in range(3)]
            for a, b in [(0, 1), (1, 2), (2, 0)]:
                mid = helper.polynomial((uv[tri[:, a]]+uv[tri[:, b]])/2, c)-(h[tri[:, a]]+h[tri[:, b]])/2
                coefficients.append(2*mid-(residual[tri[:, a]]+residual[tri[:, b]])/2)
            bounds = np.max(np.abs(np.column_stack(coefficients)), axis=1)
            scores = {"heldout_p95_mm": np.quantile(np.abs(residual[test]), .95), "heldout_max_mm": np.abs(residual[test]).max(),
                      "all_vertex_max_mm": np.abs(residual).max(), "whole_triangle_correspondence_upper_bound_mm": bounds.max()}
            if not np.allclose(stored[m], bounds, atol=1e-9, rtol=1e-9):
                raise ValueError("Actual full-face certificate changed")
            for key, value in scores.items():
                if not np.isclose(model[key], value, atol=1e-9, rtol=1e-9):
                    raise ValueError("Actual source score changed")
            if (model["digital_bound_passed"] != bool(bounds.max() <= .01) or model["native_surface_admitted"] or model["physical_acceptance"]):
                raise ValueError("Unsupported acceptance flag")
            checked.append({"model": model["model"], "bound_mm": float(bounds.max()), "digital_pass": bool(bounds.max() <= .01)})
        verified.append({"region": i, "parent_components": count, "selected_faces": len(expected), "models": checked})
    return {"status": "passed", "regions": verified, "checks": {"all_parent_faces_partitioned": True,
            "independent_component_ranking": True, "source_membership": True,
            "conditional_training_and_full_triangle_scores": True, "acceptance_flags": True},
            "source_sha256": sha(__file__), "physical_acceptance": False, "manufacturing_authorized": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["arrays", "engineering", "study", "evaluator", "output"]:
        p.add_argument("--"+name, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists(): raise ValueError("Existing connected verification refused")
    result = inspect(a.arrays, a.engineering, a.study, a.evaluator)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("x") as stream: stream.write(json.dumps(result, indent=2)+"\n")
    print("Independent component selection and complete-face score verification passed.")


if __name__ == "__main__":
    main()
