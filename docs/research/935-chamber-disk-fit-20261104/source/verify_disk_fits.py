"""Independently inspect fixed disk fits and complete curve/seam certificates."""
import argparse
from collections import defaultdict
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import sys

import numpy as np


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path, expected, name):
    if sha(path) != expected:
        raise ValueError("Frozen independent helper changed")
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(result)
    return result


def close(actual, expected, message):
    if not np.allclose(actual, expected, atol=1e-9, rtol=1e-9):
        raise ValueError(message)


def world(points, model, family, evaluator):
    if model is None:
        return points.copy()
    local = (points - model["origin"]) @ model["frame"].T
    uv = local[:, :2] / model["uv_scale"]
    height = evaluator.polynomial(uv, model["coefficients"][family])
    return np.column_stack((local[:, :2], height)) @ model["frame"] + model["origin"]


def curve_certificate(first, last, left, right, family, evaluator):
    points = np.array([first, (first + last) / 2, last])
    delta = world(points, left, family, evaluator) - world(points, right, family, evaluator)
    controls = np.array([delta[0], 2*delta[1] - (delta[0] + delta[2])/2, delta[2]])
    return float(np.linalg.norm(controls, axis=1).max()), float(np.linalg.norm(delta, axis=1).max())


def projection_check(uv, triangles, helper):
    points = [tuple(helper.F(float(x)) for x in p) for p in uv]
    polygons = [tuple(points[int(v)] for v in tri) for tri in triangles]
    if any(helper.det(*t) == 0 for t in polygons):
        return False
    for i, j in helper.broadphase(uv, triangles):
        touched, strict = helper.separate(polygons[i], polygons[j])
        if not touched:
            continue
        common = set(triangles[i]) & set(triangles[j])
        if strict or not common:
            return False
        if len(common) == 1:
            for own, other in ((i, j), (j, i)):
                winding = 1 if helper.det(*polygons[other]) > 0 else -1
                for v in triangles[own]:
                    if int(v) not in common and all(winding * helper.det(polygons[other][k], polygons[other][(k+1) % 3], points[int(v)]) >= 0 for k in range(3)):
                        return False
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("arrays", "parent", "plan", "study", "evaluator", "chart_verifier", "output"):
        p.add_argument("--" + key.replace("_", "-"), dest=key, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError("Existing verification output refused")
    plan = json.loads(a.plan.read_text())
    if sha(a.arrays) != plan["source_arrays_sha256"] or sha(a.parent / "manifest.json") != plan["parent_manifest_sha256"]:
        raise ValueError("Pinned source changed")
    evaluator = load(a.evaluator, plan["independent_evaluator_sha256"], "frozen_polynomial_evaluator")
    geometry = load(a.chart_verifier, "413219170f6aaea2a0be5c2c54544f6dd40e3fa81618215907046345d7d96af7", "frozen_rational_chart_verifier")
    files = {x["path"]: x for x in json.loads((a.parent / "manifest.json").read_text())["files"]}
    report = json.loads((a.study / "study.json").read_text())
    if report["plan_sha256"] != sha(a.plan) or len(report["regions"]) != 8:
        raise ValueError("Fixed plan or region scope changed")
    with np.load(a.arrays, allow_pickle=False) as d:
        vertices, faces = d["vertices"], d["triangles"]
    verified, domain_count, fitted_count, short_count = [], 0, 0, 0
    for region, row in enumerate(report["regions"]):
        source = a.parent / plan["parent_atlas"] / f"region-{region}-atlas.npz"
        if sha(source) != files[str(source.relative_to(a.parent))]["sha256"]:
            raise ValueError("Frozen parent domain changed")
        with np.load(source, allow_pickle=False) as d:
            ids, labels, parent_vi, parent_cuts = (d[k] for k in ("original_face_ids", "labels", "original_vertex_ids", "cut_edges"))
        if row["region"] != region or len(row["domains"]) != int(labels.max()) + 1 or row["source_faces"] != len(ids):
            raise ValueError("Complete domain/face scope changed")
        models = {}
        family_bounds = [[], []]
        for label, record in enumerate(row["domains"]):
            selected = ids[labels == label]
            vi, inverse = np.unique(faces[selected], return_inverse=True)
            tri, xyz = inverse.reshape(-1, 3), vertices[vi]
            train, test = vi % 5 != 0, vi % 5 == 0
            domain_count += 1
            if record["domain"] != label or record["source_faces"] != len(selected) or record["training_vertices"] != int(train.sum()) or record["heldout_vertices"] != int(test.sum()):
                raise ValueError("Fixed source-ID split or source coverage changed")
            if train.sum() < 40 or test.sum() < 10:
                if record["state"] != "exact_reference_retained_short_support" or "models" in record:
                    raise ValueError("Unsupported fit on insufficient source data")
                short_count += 1
                continue
            if record["state"] != "fitted_for_diagnostics":
                raise ValueError("Supported domain diagnostic fit missing")
            model_path = a.study / f"region-{region}-domain-{label:03d}.npz"
            if sha(model_path) != record["model_sha256"]:
                raise ValueError("Fit artifact hash mismatch")
            with np.load(model_path, allow_pickle=False) as d:
                model = {k: d[k].copy() for k in d.files}
            if not np.array_equal(model["original_source_face_ids"], selected) or not np.array_equal(model["original_source_vertex_ids"], vi):
                raise ValueError("Original model membership changed")
            origin, frame, scale = (model[k] for k in ("origin", "frame", "uv_scale"))
            local = (xyz - origin) @ frame.T
            uv, h = local[:, :2] / scale, local[:, 2]
            area = np.linalg.norm(np.cross(xyz[tri[:, 1]] - xyz[tri[:, 0]], xyz[tri[:, 2]] - xyz[tri[:, 0]]), axis=1) / 2
            weights = np.zeros(len(vi))
            for k in range(3):
                np.add.at(weights, tri[:, k], area / 3)
            close(frame @ frame.T, np.eye(3), "Nonorthonormal fit frame")
            close(origin, np.average(xyz[train], axis=0, weights=weights[train]), "Frame center is not training-only")
            close(scale, np.ptp(local[train, :2], axis=0), "Scale is not training-only")
            covariance = (local[train] * weights[train, None]).T @ local[train]
            if np.max(np.abs(covariance - np.diag(np.diag(covariance)))) > 1e-10 * np.max(np.abs(covariance)):
                raise ValueError("Frame is not training principal axes")
            projection = projection_check(uv, tri, geometry)
            if projection != record["new_frame_projection_admitted"]:
                raise ValueError("New fitted projection admission changed")
            edge_rows = np.sort(np.concatenate([faces[selected][:, [0, 1]], faces[selected][:, [1, 2]], faces[selected][:, [2, 0]]]), axis=1)
            all_edges, uses = np.unique(edge_rows, axis=0, return_counts=True)
            edges = all_edges[uses == 1]
            boundary_path = a.study / f"region-{region}-domain-{label:03d}-boundary.npz"
            if sha(boundary_path) != record["boundary_certificate_sha256"]:
                raise ValueError("Boundary artifact hash mismatch")
            with np.load(boundary_path, allow_pickle=False) as boundary:
                if not np.array_equal(boundary["original_boundary_edges"], edges):
                    raise ValueError("Source boundary edge membership changed")
                for family, columns in enumerate((3, 6)):
                    c, metrics = model["coefficients"][family], record["models"][family]
                    if metrics["coefficients"] != columns or metrics["heldout_vertices"] != int(test.sum()) or (columns == 3 and np.any(c[3:] != 0)):
                        raise ValueError("Fixed primitive model degree or split changed")
                    residual = evaluator.polynomial(uv, c) - h
                    u, v = uv[train].T
                    design = np.column_stack([np.ones(len(u)), u, v, u*u, u*v, v*v])[:, :columns]
                    if np.max(np.abs(design.T @ (weights[train] * residual[train]))) > 1e-8 * max(1., weights.sum()):
                        raise ValueError("Training-only normal equations changed")
                    coefficients = [residual[tri[:, k]] for k in range(3)]
                    for first, last in ((0, 1), (1, 2), (2, 0)):
                        middle = evaluator.polynomial((uv[tri[:, first]] + uv[tri[:, last]]) / 2, c) - (h[tri[:, first]] + h[tri[:, last]]) / 2
                        coefficients.append(2*middle - (residual[tri[:, first]] + residual[tri[:, last]]) / 2)
                    bounds = np.max(np.abs(np.column_stack(coefficients)), axis=1)
                    close(model["per_face_upper_bounds"][family], bounds, "Complete-triangle certificate changed")
                    scores = {"heldout_p95_mm": np.quantile(np.abs(residual[test]), .95),
                              "heldout_max_mm": np.abs(residual[test]).max(), "all_vertex_max_mm": np.abs(residual).max(),
                              "whole_triangle_correspondence_upper_bound_mm": bounds.max()}
                    for key, value in scores.items():
                        close(metrics[key], value, "Residual score changed")
                    actual = np.array([curve_certificate(vertices[first], vertices[last], model, None, family, evaluator) for first, last in edges])
                    close(boundary["upper_mm"][family], actual[:, 0], "Source boundary curve certificate changed")
                    close(boundary["sample_max_mm"][family], actual[:, 1], "Source boundary sample witness changed")
                    close(metrics["source_boundary_upper_mm"], actual[:, 0].max(), "Boundary maximum score changed")
                    close(metrics["source_boundary_sample_max_mm"], actual[:, 1].max(), "Boundary witness score changed")
                    digital = bool(bounds.max() <= .01)
                    continuity = bool(actual[:, 0].max() <= 1e-6)
                    if (metrics["digital_bound_passed"] != digital or metrics["vertex_limit_demonstrably_failed"] != bool(np.abs(residual).max() > .01) or metrics["source_boundary_continuity_passed"] != continuity or
                            metrics["eligible_for_native_export_screen"] != bool(digital and continuity and projection) or metrics["native_surface_admitted"] or metrics["physical_acceptance"]):
                        raise ValueError("Unsupported digital/boundary/native admission")
                    family_bounds[family].append(float(bounds.max()))
            models[label] = model
            fitted_count += 1
        cuts, cut_labels = parent_vi[parent_cuts[:, :2]], parent_cuts[:, 2:]
        incident = defaultdict(set)
        for face, label in zip(faces[ids], labels, strict=True):
            for v in face:
                incident[int(v)].add(int(label))
        contacts = [(v, left, right) for v, domains in sorted(incident.items()) for left, right in itertools.combinations(sorted(domains), 2)]
        if row["cut_edges"] != len(cuts) or row["interdomain_vertex_pairs"] != len(contacts) or row["diagnostic_includes_rejected_models_and_exact_source_neighbors"] is not True:
            raise ValueError("Diagnostic seam population metadata changed")
        seam_path = a.study / f"region-{region}-seams.npz"
        if sha(seam_path) != row["seam_certificate_sha256"]:
            raise ValueError("Seam artifact hash mismatch")
        with np.load(seam_path, allow_pickle=False) as seam:
            if (not np.array_equal(seam["original_cut_edges"], cuts) or not np.array_equal(seam["cut_labels"], cut_labels) or
                    not np.array_equal(seam["original_vertex_contacts"], np.array(contacts, dtype=np.int64).reshape(-1, 3))):
                raise ValueError("Exact original inter-domain incidence changed")
            for family in range(2):
                actual = np.array([curve_certificate(vertices[first], vertices[last], models.get(int(left)), models.get(int(right)), family, evaluator)
                                   for (first, last), (left, right) in zip(cuts, cut_labels, strict=True)])
                point_errors = []
                for v, left, right in contacts:
                    p = vertices[[v]]
                    point_errors.append(float(np.linalg.norm(world(p, models.get(left), family, evaluator) - world(p, models.get(right), family, evaluator))))
                close(seam["upper_mm"][family], actual[:, 0], "Seam Bernstein curve certificate changed")
                close(seam["sample_max_mm"][family], actual[:, 1], "Seam sample witness changed")
                close(seam["point_errors_mm"][family], point_errors, "Original shared-vertex continuity changed")
                close(row["seam_family_maximum_upper_mm"][family], actual[:, 0].max(), "Seam maximum score changed")
                close(row["seam_family_sample_maximum_mm"][family], actual[:, 1].max(), "Seam witness score changed")
                close(row["vertex_family_maximum_mm"][family], max(point_errors), "Shared-vertex maximum score changed")
        verified.append({"region": region, "domains": len(row["domains"]),
                         "fitted": len(models), "full_face_bounds_mm": family_bounds,
                         "cut_edges": len(cuts), "shared_vertex_pairs": len(contacts)})
    if domain_count != 405 or fitted_count + short_count != domain_count:
        raise ValueError("Registered complete study population changed")
    if report["native_surfaces_created"] or report["reference_geometry_replaced"] or report["physical_acceptance"] or report["manufacturing_authorized"]:
        raise ValueError("Unsupported geometry or physical release")
    output = {"verifier_source_sha256": sha(__file__), "plan_sha256": sha(a.plan), "study_sha256": sha(a.study / "study.json"), "regions": verified,
              "domains_verified": domain_count, "fitted_domains_verified": fitted_count,
              "short_support_references_retained": short_count, "primitive_models_verified": 2*fitted_count,
              "independent_training_scores_and_complete_triangle_bounds": True,
              "new_frame_exact_rational_contact_checks": True,
              "independent_boundary_cut_curve_and_vertex_certificates": True,
              "native_geometry_adopted": False, "physical_acceptance": False, "manufacturing_authorized": False}
    a.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output))


if __name__ == "__main__":
    main()
