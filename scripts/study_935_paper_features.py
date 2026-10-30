#!/usr/bin/env python3
"""Run a bounded, paper-guided feature study on the private frozen 935 inputs.

No full Point2CAD/GWS reproduction, gap repair, functional CAD or solver run is
performed. All geometry-bearing outputs must stay outside this repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from scripts.scan_feature_study import fit_cylinder, fit_plane, inspect_cylinder, split_source_ids

SOURCE_SHA256 = "4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486"
ARRAY_HASHES = {"vertices": "9c62ec1ff0cb72a26908878cd8607699745d0c7da20a5f9705a0003c04c695e2",
                "triangles": "84177b945a073ff4f30c75983131584c2b7ed7101f9570b38d95894e8d013303"}
LIMITS = {"p95_limit_mm": .4, "minimum_span_mm": 3., "minimum_coverage_degrees": 300.,
          "maximum_tilt_degrees": 15.}
SUPPORT_REJECTION = "insufficient source support"
SELECTOR = {"C_min_mm": -101., "C_max_mm": -89., "radial_min_mm": 3., "radial_max_mm": 10.,
            "maximum_abs_normal_C": .55, "minimum_abs_radial_normal_alignment": .8}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def run(source, arrays, baseline, output, support_policy="broad_roi"):
    repo = Path(__file__).resolve().parents[1]
    if support_policy not in {"broad_roi", "frozen_section_pairs"}:
        raise ValueError("unregistered support policy")
    if output.resolve().is_relative_to(repo):
        raise ValueError("private study output must be outside the repository")
    if output.exists():
        raise ValueError("refusing to overwrite a previous study")
    if digest(source) != SOURCE_SHA256:
        raise ValueError("original source SHA-256 mismatch")
    receipt = json.loads((baseline / "receipt.json").read_text())
    if digest(baseline / "manifest.json") != receipt["manifest_sha256"]:
        raise ValueError("baseline manifest mismatch")
    files = {x["path"]: x["sha256"] for x in json.loads((baseline / "manifest.json").read_text())["files"]}
    contract_path = baseline / "cad-support/patch-contracts.json"
    if digest(contract_path) != files["cad-support/patch-contracts.json"]:
        raise ValueError("baseline patch contract changed")
    contracts = json.loads(contract_path.read_text())
    needed = ["interface-contract.json", "geometry/source-frame-ABC.npy", "geometry/features.json",
              "geometry/planes.json", "refined-features/features.json", "cad-support/patch-contracts.json",
              "editable-cad/935-supported-planar-surfaces.step"]
    needed += ["cad-support/" + p["id"] + "-source-face-ids.npy" for p in contracts["patches"]]
    for name in needed:
        if digest(baseline / name) != files[name]:
            raise ValueError("baseline input changed: " + name)
    raw = np.load(arrays, allow_pickle=False)
    vertices, faces = raw["vertices"], raw["triangles"]
    for name, value, dtype in [("vertices", vertices, "<f8"), ("triangles", faces, "<i8")]:
        if hashlib.sha256(value.astype(dtype, copy=False).tobytes()).hexdigest() != ARRAY_HASHES[name]:
            raise ValueError("decoded source array mismatch: " + name)
    interface = json.loads((baseline / "interface-contract.json").read_text())
    if interface["mm_per_obj_unit"] != 1 or interface["source_sha256"] != SOURCE_SHA256:
        raise ValueError("baseline units/source mismatch")
    from scripts.scan_feature_cad import inspect_shape, synthetic_controls
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    output.mkdir(parents=True)
    contract = {"source_sha256": SOURCE_SHA256, "arrays_sha256": digest(arrays),
                "source_array_hashes": ARRAY_HASHES, "baseline_receipt_sha256": digest(baseline / "receipt.json"),
                "baseline_inputs": {p: files[p] for p in needed}, "source_units_mm_per_unit": 1.,
                "unit_basis": "direct owner instruction", "cylinder_evaluation_limits": LIMITS,
                "wall_selection_in_existing_ABC_frame": SELECTOR,
                "support_policy": support_policy,
                "section_pair_policy": "when selected, use only frozen retained C=-91/-94 circle pairs; no extrapolation; radial corridor equals 0.4 mm evaluation limit; abstain if either circle is absent",
                "minimum_selected_points": 100, "minimum_training_points": 40, "minimum_evaluation_points": 20,
                "partition": "original source vertex ID modulo 5; evaluation remainder 0; no coordinate welding",
                "admissibility": {"local_observed_primitive_fit": True,
                                  "full_head_functional_reconstruction": False,
                                  "full_head_hole_classification": False,
                                  "reason": "the frozen native baseline has open faces and unresolved interfaces"},
                "exact_Point2CAD_reproduction": False, "exact_GWS_reproduction": False,
                "paper_references": ["https://arxiv.org/abs/2610.13466v1",
                                     "https://openaccess.thecvf.com/content/CVPR2024/html/Liu_Point2CAD_Reverse_Engineering_CAD_Models_from_3D_Point_Clouds_CVPR_2024_paper.html"],
                "implementation_scope": "independent analytic prerequisites, cavity equations and restricted straight-cylinder CAD controls",
                "physical_acceptance": False, "manufacturing_acceptance": False}
    write_json(output / "registered-contract.json", contract)
    print("REGISTERED_CONTRACT_SHA256", digest(output / "registered-contract.json"), flush=True)
    controls = synthetic_controls()
    write_json(output / "native-controls.json", controls)
    print("Native controls passed:", len(controls), flush=True)

    frame = np.load(baseline / "geometry/source-frame-ABC.npy")
    abc = vertices @ frame.T
    tri = vertices[faces]
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    length = np.linalg.norm(cross, axis=1)
    normals = np.divide(cross, length[:, None], out=np.zeros_like(cross), where=length[:, None] > 0)
    centers = abc[faces].mean(axis=1)
    local_normals = normals @ frame.T
    del tri, cross, normals
    regions = []
    for plane in json.loads((baseline / "geometry/planes.json").read_text()):
        matching = [p for p in contracts["patches"] if p["plane_id"] == plane["id"]]
        ids = np.unique(np.concatenate([np.load(baseline / ("cad-support/" + p["id"] + "-source-face-ids.npy")) for p in matching]))
        regions.append({"id": plane["id"], "kind": "plane", "source_face_ids": ids,
                        "source_vertex_ids": np.unique(faces[ids]), "baseline_model": plane})
    features = json.loads((baseline / "geometry/features.json").read_text())["fits"]
    refined = json.loads((baseline / "refined-features/features.json").read_text())["fits"]
    for feature in features:
        if not feature["id"].startswith("stud_passage_") or feature["section_offset_mm"] != -91:
            continue
        hint = np.array(feature["search_hint_center_mm"])
        radial = centers[:, :2] - hint
        radius = np.linalg.norm(radial, axis=1)
        alignment = abs(np.sum(local_normals[:, :2] * radial, axis=1) / np.maximum(radius, 1e-30))
        select = ((centers[:, 2] >= SELECTOR["C_min_mm"]) & (centers[:, 2] <= SELECTOR["C_max_mm"])
                  & (radius >= SELECTOR["radial_min_mm"]) & (radius <= SELECTOR["radial_max_mm"])
                  & (abs(local_normals[:, 2]) <= SELECTOR["maximum_abs_normal_C"])
                  & (alignment >= SELECTOR["minimum_abs_radial_normal_alignment"]) & (length > 0))
        previous = next((f for f in refined if f["id"] == feature["id"] and f["state"] == "scan_fit_candidate"), None)
        if support_policy == "frozen_section_pairs":
            second = next((f for f in refined if f["id"] == feature["id"].replace("_C_91", "_C_94")
                           and f["state"] == "scan_fit_candidate"), None)
            if previous is None or second is None:
                select[:] = False
            else:
                first_center, second_center = np.array(previous["center_ABC_mm"]), np.array(second["center_ABC_mm"])
                position = (centers[:, 2] - first_center[2]) / (second_center[2] - first_center[2])
                reference_xy = first_center[:2] + position[:, None] * (second_center - first_center)[:2]
                reference_radius = (previous["diameter_mm"] + position * (second["diameter_mm"] - previous["diameter_mm"])) / 2
                radial_distance = np.linalg.norm(centers[:, :2] - reference_xy, axis=1)
                select &= ((position >= 0) & (position <= 1)
                           & (abs(radial_distance - reference_radius) <= LIMITS["p95_limit_mm"]))
        ids = np.flatnonzero(select)
        regions.append({"id": feature["id"].replace("_C_91", "_wall_candidate"), "kind": "cylinder",
                        "source_face_ids": ids, "source_vertex_ids": np.unique(faces[ids]),
                        "baseline_model": previous})
    membership = np.zeros(len(vertices), dtype=np.int16)
    for region in regions:
        membership[region["source_vertex_ids"]] += 1
    ambiguous = np.flatnonzero(membership > 1)
    np.save(output / "ambiguous-source-vertex-ids.npy", ambiguous)
    # Freeze all source-ID partitions before any point fitting or selection by fit result.
    partitions = []
    for region in regions:
        ids = region["source_vertex_ids"]
        ids = ids[membership[ids] == 1]
        train, held = split_source_ids(ids)
        path = output / (region["id"] + "-partition.npz")
        np.savez_compressed(path, training_source_vertex_ids=train, evaluation_source_vertex_ids=held,
                            selected_source_face_ids=region["source_face_ids"])
        region["training_ids"], region["evaluation_ids"] = train, held
        partitions.append({"id": region["id"], "kind": region["kind"], "file": path.name,
                           "sha256": digest(path), "training_points": len(train), "evaluation_points": len(held)})
    write_json(output / "registered-partitions.json", {"partitions": partitions,
               "ambiguous_vertices_excluded_from_all_fits": len(ambiguous),
               "prior_plane_masks_may_be_informed_by_previous_fits": True})
    records, models = [], []
    exported_ids, exported_labels = [], []
    for region in regions:
        train, held = region["training_ids"], region["evaluation_ids"]
        record = {"id": region["id"], "kind": region["kind"], "training_points": len(train),
                  "evaluation_points": len(held), "physical_dimension_accepted": False}
        try:
            if len(train) < 40 or len(held) < 20 or len(train) + len(held) < 100:
                raise ValueError(SUPPORT_REJECTION)
            if region["kind"] == "plane":
                model = fit_plane(vertices[train])
                distance = abs(vertices[held] @ model["normal"] - model["offset_mm"])
                previous = region["baseline_model"]
                before = abs(vertices[held] @ previous["normal_xyz"] - previous["offset_mm"])
                record.update(p95_mm=float(np.quantile(distance, .95)), max_mm=float(distance.max()),
                              baseline_p95_mm=float(np.quantile(before, .95)),
                              retained_as_scan_fit_candidate=bool(np.quantile(distance, .95) <= .25))
            else:
                model = fit_cylinder(vertices[train], frame[2])
                record.update(inspect_cylinder(model, vertices[held], frame[2], **LIMITS))
                previous = region["baseline_model"]
                if previous:
                    old_axis = np.array(previous["axis_xyz"])
                    delta = vertices[held] - np.array(previous["center_xyz_mm"])
                    residual = abs(np.linalg.norm(np.cross(delta, old_axis), axis=1) - previous["diameter_mm"] / 2)
                    record["baseline_p95_mm"] = float(np.quantile(residual, .95))
                    record["baseline_scope"] = "infinite axial extrapolation of the frozen section-circle candidate, not an existing CAD wall"
            models.append({"id": region["id"], "model": model})
            record["model"] = model
            if record["retained_as_scan_fit_candidate"]:
                exported_ids.append(train)
                exported_labels.append(np.full(len(train), len(exported_ids) - 1, dtype=np.int32))
        except ValueError as error:
            record.update(retained_as_scan_fit_candidate=False, rejection_reasons=[str(error)])
        records.append(record)
        print(record["id"], record["retained_as_scan_fit_candidate"], record.get("p95_mm"), flush=True)
    ids = np.concatenate(exported_ids) if exported_ids else np.empty(0, dtype=np.int64)
    labels = np.concatenate(exported_labels) if exported_labels else np.empty(0, dtype=np.int32)
    np.savez_compressed(output / "labelled-training-source-ids.npz", source_vertex_ids=ids, labels=labels)
    cloud = np.c_[vertices[ids], labels]
    np.savetxt(output / "labelled-training-xyzc.txt", cloud, fmt=["%.17g", "%.17g", "%.17g", "%d"])
    export = output / "labelled-training-xyzc.txt"
    reread = np.loadtxt(export, ndmin=2) if export.stat().st_size else np.empty((0, 4))
    assert reread.shape == (len(ids), 4)
    assert np.array_equal(reread[:, :3], vertices[ids]) and np.array_equal(reread[:, 3], labels)
    write_json(output / "primitive-fits.json", {"records": records, "all_fits_stored": models,
               "complete_head_created": False, "physical_acceptance": False})

    reader = STEPControl_Reader()
    assert reader.ReadFile(str(baseline / "editable-cad/935-supported-planar-surfaces.step")) == IFSelect_RetDone
    assert reader.TransferRoots() > 0
    native = inspect_shape(reader.OneShape())
    write_json(output / "partial-CAD-rim-review.json", native)
    summary = {"source_sha256": SOURCE_SHA256, "source_units_mm_per_unit": 1.,
               "support_policy": support_policy,
               "registered_contract_sha256": digest(output / "registered-contract.json"),
               "registered_partitions_sha256": digest(output / "registered-partitions.json"),
               "native_controls_passed": len(controls), "region_attempts": len(records),
               "retained_planes": sum(r["kind"] == "plane" and r["retained_as_scan_fit_candidate"] for r in records),
               "retained_cylinder_candidates": sum(r["kind"] == "cylinder" and r["retained_as_scan_fit_candidate"] for r in records),
               "exported_training_source_vertices": len(ids), "all_original_source_vertices": len(vertices),
               "unlabelled_or_evaluation_vertices_not_exported": len(vertices) - len(ids),
               "partial_CAD_rims_screened": len(native["rims"]),
               "circular_rim_candidates": sum(r.get("circular_rim_candidate", False) for r in native["rims"]),
               "full_head_hole_classification_admitted": native["solid_hole_classification_admitted"],
               "exact_Point2CAD_executed": False, "exact_GWS_executed": False,
               "functional_head_created": False, "physics_run": False,
               "physical_acceptance": False, "manufacturing_acceptance": False}
    write_json(output / "summary.json", summary)
    print(json.dumps(summary), flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--arrays", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--support-policy", choices=["broad_roi", "frozen_section_pairs"], default="broad_roi")
    args = parser.parse_args()
    run(args.source, args.arrays, args.baseline, args.output, args.support_policy)
