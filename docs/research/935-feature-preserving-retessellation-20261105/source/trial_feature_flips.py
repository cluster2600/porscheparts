"""One bounded quad-flip trial preserving feature edges rather than face rows."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def topology(vertices, faces, tags):
    directed = np.concatenate((faces[:,[0,1]], faces[:,[1,2]], faces[:,[2,0]]))
    keys = directed.min(axis=1)*len(vertices) + directed.max(axis=1)
    order = np.argsort(keys, kind="stable"); ordered = keys[order]
    assert len(ordered) % 2 == 0 and np.array_equal(ordered[::2], ordered[1::2])
    assert not np.any(ordered[1:-1:2] == ordered[2::2])
    assert not np.any(np.sign(directed[:,1]-directed[:,0])[order].reshape(-1,2).sum(axis=1))
    pairs = order.reshape(-1,2) % len(faces)
    xyz = vertices[faces]
    normals = np.cross(xyz[:,1]-xyz[:,0], xyz[:,2]-xyz[:,0])
    normals /= np.linalg.norm(normals, axis=1)[:,None]
    # Slightly conservative around the verifier's fixed 30-degree threshold.
    crease = np.einsum("ij,ij->i", normals[pairs[:,0]], normals[pairs[:,1]]) < np.cos(np.deg2rad(29.9999999))
    feature = crease | (tags[pairs[:,0]] != tags[pairs[:,1]])
    return directed, order, ordered[::2], pairs, feature


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh", "baseline", "tags", "geometry-report", "parent-preservation", "repository", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(mode=0o700, exist_ok=False)
    assert sha(args.mesh) == "7adc8f931feac78eb6298e1415c8d49b7a92bced5dde5dbcc6bc3afd2e9e947f"
    assert sha(args.baseline) == "05159cdbf903729da5b8556d2ff2c2d29680a45c2b4bd42b34e031a122205594"
    assert sha(args.tags) == "877cf9c6638eb388755a378775428c7a5067409f166b3ea38d03b1837f2fae2f"
    geometry = json.loads(args.geometry_report.read_text())
    parent = json.loads(args.parent_preservation.read_text())
    assert geometry["input_sha256"] == sha(args.mesh) and geometry["geometry_export_gate_passed"]
    assert geometry["intersection_pairs"] == 0 and geometry["vertex_manifold"]
    assert parent["candidate_sha256"] == sha(args.mesh) and parent["preservation_checks_passed"]
    helper_path = args.repository / "docs/research/935-mesh-admission-20261104/source/trial_bounded_quad_flips.py"
    helper = load_module(helper_path, "frozen_quad_operator")
    plan = {"scope": "Separate numerical retessellation; print master unchanged",
            "mesh_sha256": sha(args.mesh), "baseline_sha256": sha(args.baseline), "tags_sha256": sha(args.tags),
            "geometry_report_sha256": sha(args.geometry_report), "parent_preservation_sha256": sha(args.parent_preservation),
            "source_sha256": sha(Path(__file__)), "quad_helper_sha256": sha(helper_path),
            "upstream_verdict": "Hypothetical closed surface admitted for diagnostic study only; exact fixed faces force low-quality cells",
            "passes": 1, "vertices_unchanged_exactly": True, "same_construction_tag_per_changed_pair": True,
            "feature_contract": "Preserve all baseline and input edges above 30 degrees and all construction-tag boundary edges, with exact endpoints",
            "per_patch_correspondence_limit_mm": .0029, "cumulative_correspondence_limit_mm": .01,
            "prior_independent_bound_mm": parent["composed_complete_surface_correspondence_bound_mm"],
            "relative_volume_change_limit": .0001, "incident_tet_mean_ratio_bin": .01,
            "forced_face_reduction_min_fraction": .5, "bad_face_bin": .01,
            "bad_face_count_must_not_increase": True, "parameter_sweep": False,
            "physics_admitted": False, "manufacturing_qualified": False}
    assert plan["prior_independent_bound_mm"] + .0029 <= .01
    save(args.output/"plan.json", plan); save(args.output/"quad-controls.json", helper.controls())
    started = time.monotonic()
    with np.load(args.mesh, allow_pickle=False) as data: vertices, faces = data["vertices"], data["triangles"]
    with np.load(args.baseline, allow_pickle=False) as data: base_vertices, base_faces = data["vertices"], data["triangles"]
    tags = np.load(args.tags, allow_pickle=False); assert len(tags) == len(faces) == len(base_faces)
    base_directed, base_order, base_keys, _, base_feature = topology(base_vertices, base_faces, tags)
    baseline_features = base_keys[base_feature]
    baseline_endpoints = np.unique(base_directed[base_order[::2][base_feature]])
    assert np.array_equal(vertices[baseline_endpoints], base_vertices[baseline_endpoints])
    del base_directed, base_order, base_keys, base_vertices, base_faces
    directed, order, keys, pairs, input_feature = topology(vertices, faces, tags)
    feature_keys = np.union1d(baseline_features, keys[input_feature])
    assert np.isin(baseline_features, keys, assume_unique=True).all()
    np.save(args.output/"private-feature-edge-keys.npy", feature_keys)
    q = helper.qvalues(vertices, faces); forced = q**(2/3) < .01
    assert int(forced.sum()) == 633
    eligible = np.flatnonzero(forced[pairs].any(axis=1) & ~np.isin(keys, feature_keys, assume_unique=True)
                              & (tags[pairs[:,0]] == tags[pairs[:,1]]))
    proposals = []
    for position in eligible:
        ra, rb = map(int, pairs[position]); a, b = map(int, directed[order[2*position]])
        first, second = faces[ra], faces[rb]
        i = int(np.flatnonzero(first == a)[0])
        if first[(i+1) % 3] != b: a, b = b, a
        j = int(np.flatnonzero(second == b)[0]); assert second[(j+1) % 3] == a
        c = int(first[(first != a) & (first != b)][0]); d = int(second[(second != a) & (second != b)][0])
        new_key = min(c,d)*len(vertices) + max(c,d); index = np.searchsorted(keys, new_key)
        if c == d or (index < len(keys) and keys[index] == new_key): continue
        certificate = helper.certificate(vertices[[a,b,c,d]])
        if certificate is None or certificate[0] > .0029: continue
        replacement = np.array([[c,a,d],[d,b,c]])
        new_q = helper.qvalues(vertices, replacement); old_q = q[[ra,rb]]
        improvement = int((old_q**(2/3) < .01).sum()) - int((new_q**(2/3) < .01).sum())
        if improvement < 1 or new_q.min() <= old_q.min()*(1+1e-6): continue
        if (new_q < .01).sum() > (old_q < .01).sum(): continue
        proposals.append((improvement, float(new_q.min()-old_q.min()), ra,rb,a,b,c,d,*certificate,new_key))
    proposals.sort(key=lambda row: (-row[0],-row[1],row[2],row[3]))
    candidate = faces.copy(); touched = np.zeros(len(faces),bool); new_edges = set(); records = []
    for row in proposals:
        _,_,ra,rb,a,b,c,d,bound,t,s,key = row
        if touched[ra] or touched[rb] or key in new_edges: continue
        candidate[ra],candidate[rb] = [c,a,d],[d,b,c]
        touched[[ra,rb]] = True; new_edges.add(key); records.append([ra,rb,a,b,c,d,bound,t,s])
    np.savez_compressed(args.output/"candidate.npz", vertices=vertices, triangles=candidate)
    np.savez_compressed(args.output/"private-flip-provenance.npz", records=np.asarray(records,float).reshape(-1,9))
    new_q = helper.qvalues(vertices,candidate); after = int((new_q**(2/3) < .01).sum())
    reduction = 1-after/int(forced.sum())
    result = {"before_forced_faces": int(forced.sum()), "after_forced_faces": after,
              "forced_face_reduction_fraction": reduction, "quality_gate_passed": reduction >= .5,
              "bad_faces_before": int((q < .01).sum()), "bad_faces_after": int((new_q < .01).sum()),
              "minimum_face_quality_before": float(q.min()), "minimum_face_quality_after": float(new_q.min()),
              "baseline_feature_edges": len(baseline_features), "input_feature_edges": int(input_feature.sum()),
              "protected_feature_edges_union": len(feature_keys), "eligible_edges": len(eligible),
              "qualified_proposals": len(proposals), "flips": len(records),
              "maximum_producer_patch_bound_mm": max((r[6] for r in records), default=0),
              "candidate_sha256": sha(args.output/"candidate.npz"),
              "independent_preservation_and_native_audit_pending": True,
              "accepted_for_meshing": False, "physics_admitted": False, "manufacturing_qualified": False,
              "seconds": time.monotonic()-started}
    save(args.output/"producer.json", result); print(json.dumps(result),flush=True)


if __name__ == "__main__":
    main()
