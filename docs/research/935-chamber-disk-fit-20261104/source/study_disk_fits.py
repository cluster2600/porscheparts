"""Run the unchanged primitive fitter on every fixed, admitted source disk."""
import argparse
from collections import Counter, defaultdict
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
        raise ValueError("Frozen helper changed: " + path.name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


def curve_power(p, q, model, family):
    if model is None:
        return np.array([p, q - p, np.zeros(3)])
    origin, frame, scale = (model[k] for k in ("origin", "frame", "uv_scale"))
    c = model["coefficients"][family]
    u, v = ((p - origin) @ frame.T)[:2] / scale
    du, dv = ((q - p) @ frame.T)[:2] / scale
    h0 = c[0] + c[1]*u + c[2]*v + c[3]*u*u + c[4]*u*v + c[5]*v*v
    h1 = c[1]*du + c[2]*dv + 2*c[3]*u*du + c[4]*(u*dv + v*du) + 2*c[5]*v*dv
    h2 = c[3]*du*du + c[4]*du*dv + c[5]*dv*dv
    return np.array([origin + u*scale[0]*frame[0] + v*scale[1]*frame[1] + h0*frame[2],
                     du*scale[0]*frame[0] + dv*scale[1]*frame[1] + h1*frame[2], h2*frame[2]])


def curve_bounds(power):
    control = np.array([power[0], power[0] + power[1]/2, power.sum(axis=0)])
    sampled = np.array([power[0], power[0] + power[1]/2 + power[2]/4, power.sum(axis=0)])
    return float(np.linalg.norm(control, axis=1).max()), float(np.linalg.norm(sampled, axis=1).max())


def boundary_edges(faces):
    counts = Counter(tuple(sorted((int(f[i]), int(f[(i+1) % 3])))) for f in faces for i in range(3))
    return np.array(sorted(e for e, n in counts.items() if n == 1), dtype=np.int64).reshape(-1, 2)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("arrays", "parent", "plan", "fitter", "topology", "predicate", "output"):
        p.add_argument("--" + key, type=Path, required=True)
    a = p.parse_args()
    plan = json.loads(a.plan.read_text())
    if sha(a.arrays) != plan["source_arrays_sha256"] or sha(a.parent / "manifest.json") != plan["parent_manifest_sha256"]:
        raise ValueError("Pinned source/atlas changed")
    files = {r["path"]: r for r in json.loads((a.parent / "manifest.json").read_text())["files"]}
    fitter = load(a.fitter, plan["fitter_sha256"], "frozen_primitive_fitter")
    topology = load(a.topology, plan["source_topology_sha256"], "frozen_native_topology")
    predicate = load(a.predicate, "625331bb7e070cda2cc006f6e6a606d2fce2ed6dfc92243a5c06ebe3b9f2bbad", "frozen_dyadic_predicates")
    atlas_source = a.parent / "source/build_atlas.py"
    contacts = load(atlas_source, files["source/build_atlas.py"]["sha256"], "frozen_full_contact_checker")
    with np.load(a.arrays, allow_pickle=False) as d:
        vertices, faces = d["vertices"], d["triangles"]
    a.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    regions = []
    for region in range(8):
        path = a.parent / plan["parent_atlas"] / f"region-{region}-atlas.npz"
        if sha(path) != files[str(path.relative_to(a.parent))]["sha256"]:
            raise ValueError("Registered disk atlas changed")
        with np.load(path, allow_pickle=False) as d:
            ids, labels, parent_vi, local_cuts = (d[k] for k in ("original_face_ids", "labels", "original_vertex_ids", "cut_edges"))
        records, models = [], {}
        for label in range(int(labels.max()) + 1):
            selected = ids[labels == label]
            vi, inverse = np.unique(faces[selected], return_inverse=True)
            train, test = int(np.count_nonzero(vi % 5)), int(np.count_nonzero(vi % 5 == 0))
            item = {"domain": label, "source_faces": len(selected), "training_vertices": train, "heldout_vertices": test}
            target = a.output / f"region-{region}-domain-{label:03d}.npz"
            if train < 40 or test < 10:
                item.update(state="exact_reference_retained_short_support", reason="Insufficient fixed source-ID split")
                records.append(item)
                continue
            try:
                result = fitter.fit_region(vertices, faces, selected, topology, target)
            except ValueError as error:
                item.update(state="fit_refused", reason=str(error))
                records.append(item)
                continue
            with np.load(target, allow_pickle=False) as d:
                model = {k: d[k].copy() for k in d.files}
            models[label] = model
            tri = inverse.reshape(-1, 3)
            uv = ((vertices[vi] - model["origin"]) @ model["frame"].T)[:, :2] / model["uv_scale"]
            try:
                conflicts = contacts.contact_audit(uv, tri, predicate.candidates(uv, tri), predicate)
                projection_ok, projection_reason = len(conflicts) == 0, None
            except ValueError as error:
                projection_ok, projection_reason = False, str(error)
            edges = boundary_edges(faces[selected])
            upper, sample = np.zeros((2, len(edges))), np.zeros((2, len(edges)))
            for family in range(2):
                for e, (first, last) in enumerate(edges):
                    difference = curve_power(vertices[first], vertices[last], model, family) - curve_power(vertices[first], vertices[last], None, family)
                    upper[family, e], sample[family, e] = curve_bounds(difference)
            certificate = a.output / f"region-{region}-domain-{label:03d}-boundary.npz"
            np.savez_compressed(certificate, original_boundary_edges=edges, upper_mm=upper, sample_max_mm=sample)
            item.update(state="fitted_for_diagnostics", **result, model_sha256=sha(target),
                        new_frame_projection_admitted=projection_ok, projection_reason=projection_reason,
                        boundary_certificate_sha256=sha(certificate))
            for family, row in enumerate(item["models"]):
                row.update(source_boundary_upper_mm=float(upper[family].max()),
                           source_boundary_sample_max_mm=float(sample[family].max()),
                           source_boundary_continuity_passed=bool(upper[family].max() <= 1e-6),
                           eligible_for_native_export_screen=bool(row["digital_bound_passed"] and projection_ok and upper[family].max() <= 1e-6))
            records.append(item)
        cuts = parent_vi[local_cuts[:, :2]]
        cut_labels = local_cuts[:, 2:]
        upper, sample = np.zeros((2, len(cuts))), np.zeros((2, len(cuts)))
        for family in range(2):
            for e, ((first, last), (left, right)) in enumerate(zip(cuts, cut_labels, strict=True)):
                power = curve_power(vertices[first], vertices[last], models.get(int(left)), family) - curve_power(vertices[first], vertices[last], models.get(int(right)), family)
                upper[family, e], sample[family, e] = curve_bounds(power)
        incident = defaultdict(set)
        for face, label in zip(faces[ids], labels, strict=True):
            for v in face:
                incident[int(v)].add(int(label))
        points = [(v, left, right) for v, uses in sorted(incident.items()) for left, right in itertools.combinations(sorted(uses), 2)]
        point_errors = np.zeros((2, len(points)))
        for family in range(2):
            for j, (v, left, right) in enumerate(points):
                delta = curve_power(vertices[v], vertices[v], models.get(left), family)[0] - curve_power(vertices[v], vertices[v], models.get(right), family)[0]
                point_errors[family, j] = np.linalg.norm(delta)
        seam_path = a.output / f"region-{region}-seams.npz"
        np.savez_compressed(seam_path, original_cut_edges=cuts, cut_labels=cut_labels, upper_mm=upper,
                            sample_max_mm=sample, original_vertex_contacts=np.array(points, dtype=np.int64).reshape(-1, 3), point_errors_mm=point_errors)
        regions.append({"region": region, "source_faces": len(ids), "domains": records,
                        "cut_edges": len(cuts), "interdomain_vertex_pairs": len(points),
                        "seam_certificate_sha256": sha(seam_path),
                        "seam_family_maximum_upper_mm": upper.max(axis=1).tolist(),
                        "seam_family_sample_maximum_mm": sample.max(axis=1).tolist(),
                        "vertex_family_maximum_mm": point_errors.max(axis=1).tolist(),
                        "diagnostic_includes_rejected_models_and_exact_source_neighbors": True})
    report = {"plan_sha256": sha(a.plan), "source_sha256": sha(__file__), "regions": regions,
              "native_surfaces_created": False, "reference_geometry_replaced": False,
              "physical_acceptance": False, "manufacturing_authorized": False}
    (a.output / "study.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"regions": [{"region": r["region"], "domains": len(r["domains"]),
                                  "fitted": sum(d["state"] == "fitted_for_diagnostics" for d in r["domains"]),
                                  "digital_passes": sum(m["digital_bound_passed"] for d in r["domains"] for m in d.get("models", [])),
                                  "eligible": sum(m["eligible_for_native_export_screen"] for d in r["domains"] for m in d.get("models", []))} for r in regions]}))


if __name__ == "__main__":
    main()
