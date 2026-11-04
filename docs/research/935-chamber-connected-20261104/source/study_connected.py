#!/usr/bin/env python3
"""Select source components by area before reusing unchanged smooth-surface diagnostics."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def module(path, name, expected):
    if sha(path) != expected:
        raise ValueError("Pinned helper changed: "+path.name)
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def rank_components(labels, areas, ids):
    return sorted((dict(label=int(label), faces=int((labels == label).sum()),
                        area_mm2=float(areas[labels == label].sum()),
                        minimum_original_face_id=int(ids[labels == label].min())) for label in np.unique(labels)),
                  key=lambda x: (-x["area_mm2"], x["minimum_original_face_id"]))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["arrays", "engineering", "intersections", "fitter", "topology", "plan", "output"]:
        p.add_argument("--"+name, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError("Existing connected study refused")
    if sha(a.arrays) != "dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a":
        raise ValueError("Original arrays changed")
    if sha(a.intersections) != "1ee2ad7b6e6fdf24b3288c78ccb9ec4952a76f2a496ff2c35f887a728913fb04":
        raise ValueError("Original intersection inventory changed")
    fitter = module(a.fitter, "frozen_chamber_fitter", FITTER_SHA)
    topology = module(a.topology, "frozen_source_topology", "fca5259ef3b3412a72e441fea39816e14fea4e375095e1c83def2e4117f6ae8e")
    for i, expected in enumerate(fitter.MASK_SHA):
        if sha(a.engineering/f"chamber-candidates/chamber_planar_region_{i}-source-face-ids.npy") != expected:
            raise ValueError("Original chamber mask changed")
    assert rank_components(np.array([0, 0, 1]), np.array([1., 1., 3.]), np.array([1, 2, 3]))[0]["label"] == 1
    assert rank_components(np.array([0, 1]), np.array([1., 1.]), np.array([8, 4]))[0]["label"] == 1
    with np.load(a.arrays, allow_pickle=False) as s:
        vertices, faces = s["vertices"], s["triangles"]
    conflict_ids = np.unique(np.load(a.intersections, allow_pickle=False))
    a.output.mkdir(parents=True)
    # Select every region before fitting any region. Model outcomes cannot choose masks.
    regions, selections = [], []
    for i in range(8):
        ids = np.load(a.engineering/f"chamber-candidates/chamber_planar_region_{i}-source-face-ids.npy", allow_pickle=False)
        vi, local = np.unique(faces[ids], return_inverse=True)
        v, f = vertices[vi], local.reshape(-1, 3)
        _, _, _, labels, _ = topology.atlas(v, f)
        xyz = vertices[faces[ids]]
        area = np.linalg.norm(np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0]), axis=1)/2
        ranked = rank_components(labels, area, ids)
        selected = ids[labels == ranked[0]["label"]]
        np.savez_compressed(a.output/f"region-{i}-selection.npz", parent_original_face_ids=ids,
                            component_labels=labels, selected_original_face_ids=selected)
        regions.append({"id": f"historical_chamber_region_{i}", "parent_faces": len(ids),
                        "parent_components": len(ranked), "component_ledger": ranked,
                        "selected_faces": len(selected), "all_parent_observations_retained": True})
        selections.append(selected)
    (a.output/"selection.json").write_text(json.dumps({"plan_sha256": sha(a.plan), "regions": regions}, indent=2)+"\n")
    for i, ids in enumerate(selections):
        if len(np.intersect1d(ids, conflict_ids)):
            regions[i].update(state="not_fitted", reason="Original indexed intersection face")
            continue
        try:
            result = fitter.fit_region(vertices, faces, ids, topology, a.output/f"region-{i}-models.npz")
            regions[i].update(state="fitted_for_diagnostics", **result)
        except ValueError as error:
            regions[i].update(state="not_fitted", reason=str(error))
    report = {"source_sha256": sha(__file__), "plan_sha256": sha(a.plan), "fitter_sha256": sha(a.fitter),
              "regions": regions, "controls": {"area_over_face_count": True, "minimum_face_id_tie": True},
              "native_CAD_created": False, "physical_acceptance": False, "manufacturing_authorized": False}
    (a.output/"study.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"regions": [{k: r[k] for k in ["id", "parent_faces", "parent_components", "selected_faces", "state"]}
                                  | {"models": r.get("models", []), "reason": r.get("reason")} for r in regions]}))


FITTER_SHA = "9518d2e6ac5e92ecf1f0c1b23dfc74cda4671b2fe147758521d9d43737af63a0"

if __name__ == "__main__":
    main()
