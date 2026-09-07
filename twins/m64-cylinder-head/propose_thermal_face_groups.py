#!/usr/bin/env python3
"""Propose private face provenance groups, never physical boundary conditions.

Match F53 faces against F43 signatures or the finite cylindrical construction
tools recorded by F47. Candidate groups require visual/functional review; they
must not be accepted as a ready-to-solve M64 boundary partition.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cylinder_features(contract, variant_name):
    common = contract["common_candidate_geometry"]
    variant = contract["variants"][variant_name]
    features = []

    def add(identifier, role, start, end, radius):
        features.append({"feature_id": identifier, "candidate_function": role,
                         "start": start, "end": end, "radius": radius})

    def vertical(identifier, role, xy, z0, z1, diameter):
        add(identifier, role, [*xy, z0], [*xy, z1], diameter / 2)

    bore = common["bore"]
    vertical("circular_bore_chamber", "bore_chamber_or_cylinder_interface", [0., 0.],
             bore["z_start_mm"], bore["z_end_mm"], bore["diameter_mm"])
    for valve in variant["valves"]:
        identifier, xy, role = valve["id"], valve["centre_xy_mm"], valve["role"]
        vertical(identifier + "_seat", "seat_contact", xy,
                 common["seat_counterbore_z_start_mm"],
                 common["seat_counterbore_z_start_mm"] + common["seat_counterbore_depth_mm"],
                 valve["seat_envelope_diameter_mm"])
        diameter = valve["head_diameter_mm"] * valve["throat_ratio"]
        vertical(identifier + "_throat", role + "_gas", xy,
                 common["throat_z_start_mm"], common["throat_z_end_mm"], diameter)
        vertical(identifier + "_guide", "guide_contact_or_open_bore", xy,
                 common["guide_bore_z_start_mm"], common["guide_bore_z_end_mm"],
                 common["guide_bore_diameter_mm"])
        # This start height is explicit in build_internal_brep_variants_f47.py.
        add(identifier + "_port", role + "_gas", [*xy, 12.],
            [xy[0], valve["port_exit_y_mm"], valve["port_exit_z_mm"]], diameter / 2)
    plug = variant["spark_plug"]
    vertical("spark_plug_bore", "spark_plug_contact", plug["centre_xy_mm"],
             common["spark_bore_z_start_mm"], common["spark_bore_z_end_mm"], plug["diameter_mm"])
    oil = common["oil_domain"]
    main = oil["main_gallery"]
    add("main_oil_gallery", "oil_candidate", main["start_xyz_mm"], main["end_xyz_mm"], main["diameter_mm"] / 2)
    for index, access in enumerate(oil["vertical_cleanout_accesses"], 1):
        start = access["xyz_mm"]
        add(f"oil_cleanout_{index}", "oil_or_cleanout_plug", start,
            [start[0], start[1], access["z_end_mm"]], access["diameter_mm"] / 2)
    return features


def finite_cylinder_support_matches(points, feature, tolerance=1e-4):
    """All supplied exact surface samples must lie on one finite support."""
    import numpy as np
    points = np.asarray(points, dtype=float)
    start, end = np.asarray(feature["start"]), np.asarray(feature["end"])
    length = float(np.linalg.norm(end - start))
    radius = float(feature["radius"])
    if not len(points) or length <= 0 or radius <= 0 or not np.isfinite(points).all():
        raise ValueError("invalid_finite_cylinder_samples_or_dimensions")
    axis = (end - start) / length
    offsets = points - start
    axial = offsets @ axis
    radial = np.linalg.norm(offsets - axial[:, None] * axis, axis=1)
    matches = []
    if (abs(radial - radius) <= tolerance).all() and (axial >= -tolerance).all() and (axial <= length + tolerance).all():
        matches.append("cylindrical_side")
    if (radial <= radius + tolerance).all():
        if (abs(axial) <= tolerance).all():
            matches.append("start_cap")
        if (abs(axial - length) <= tolerance).all():
            matches.append("end_cap")
    return matches


def signature_candidates(record, outer_records, tolerance=1e-4):
    import numpy as np
    bbox = np.asarray(record["bbox_scan_units"])
    centroid = np.asarray(record["centroid_scan_units"])
    area = record["area_scan_units_squared"]
    matches = []
    for outer in outer_records:
        if record["surface_type"] != outer["surface_type"]:
            continue
        if max(abs(a-b) for a, b in zip(bbox, outer["bbox_scan_units"])) > tolerance:
            continue
        if max(abs(a-b) for a, b in zip(centroid, outer["centroid_scan_units"])) > tolerance:
            continue
        if abs(area - outer["area_scan_units_squared"]) > max(1e-8, abs(area)*1e-7):
            continue
        matches.append(outer["face_id"])
    return matches


def sample_trimmed_face(face):
    """Interior UV samples plus vertices, on the exact face support."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.BRepTools import BRepTools
    from OCP.TopAbs import TopAbs_IN, TopAbs_VERTEX
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pnt2d
    from audit_brep_f42 import indexed_shapes
    adaptor = BRepAdaptor_Surface(face)
    u0, u1, v0, v1 = BRepTools.UVBounds_s(face)
    points = []
    interior_count = 0
    for fu in (.1, .3, .5, .7, .9):
        for fv in (.1, .3, .5, .7, .9):
            u, v = u0 + fu*(u1-u0), v0 + fv*(v1-v0)
            classifier = BRepClass_FaceClassifier(face, gp_Pnt2d(u, v), 1e-7)
            if classifier.State() == TopAbs_IN:
                points.append(list(adaptor.Value(u, v).Coord()))
                interior_count += 1
    vertices = indexed_shapes(face, TopAbs_VERTEX)
    for index in range(1, vertices.Extent() + 1):
        points.append(list(BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(index))).Coord()))
    return points, interior_count


def partial_outer_candidates(record, points, outer_records, outer_faces, tolerance=1e-4):
    """Check exact-point distances to trimmed outer faces after bbox filtering."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.gp import gp_Pnt
    bounds = record["bbox_scan_units"]
    vertices = [BRepBuilderAPI_MakeVertex(gp_Pnt(*point)).Vertex() for point in points]
    matches = []
    for outer in outer_records:
        if outer["surface_type"] != record["surface_type"]:
            continue
        box = outer["bbox_scan_units"]
        if any(box[axis] > bounds[axis]+tolerance or box[axis+3] < bounds[axis+3]-tolerance
               for axis in range(3)):
            continue
        distances = []
        for vertex in vertices:
            distance = BRepExtrema_DistShapeShape(vertex, outer_faces.FindKey(outer["face_id"]))
            if not distance.IsDone() or distance.Value() > tolerance:
                break
            distances.append(float(distance.Value()))
        if len(distances) == len(vertices):
            matches.append({"outer_face_id": outer["face_id"],
                            "maximum_sampled_trimmed_face_distance": max(distances)})
    return matches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("step", "inventory", "outer-step", "outer-inventory", "contract", "builder"):
        parser.add_argument("--" + name, type=Path, required=True)
        parser.add_argument("--" + name + "-sha256", required=True)
    parser.add_argument("--helpers", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for name in ("step", "inventory", "outer_step", "outer_inventory", "contract", "builder"):
        if sha256(getattr(args, name)) != getattr(args, name + "_sha256"):
            raise ValueError(name + "_hash_mismatch")
    if args.output.exists():
        raise FileExistsError(args.output)
    sys.path.insert(0, str(args.helpers))
    from audit_brep_f42 import read_step, indexed_shapes
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    import OCP
    source = json.loads(args.inventory.read_text())
    outer = json.loads(args.outer_inventory.read_text())
    if source["source_sha256"] != args.step_sha256 or source["ocp_version"] != OCP.__version__:
        raise ValueError("inventory_source_or_import_version_mismatch")
    if outer["ocp_version"] != OCP.__version__:
        raise ValueError("outer_import_version_mismatch")
    if outer["source_sha256"] != args.outer_step_sha256:
        raise ValueError("outer_inventory_source_mismatch")
    contract = json.loads(args.contract.read_text())
    features = cylinder_features(contract, "4v")
    shape, _ = read_step(args.step)
    faces = indexed_shapes(shape, TopAbs_FACE)
    outer_shape, _ = read_step(args.outer_step)
    outer_faces = indexed_shapes(outer_shape, TopAbs_FACE)
    if faces.Extent() != len(source["faces"]):
        raise ValueError("inventory_face_count_mismatch")
    records = []
    for record in source["faces"]:
        face_id = record["face_id"]
        matching_outer = signature_candidates(record, outer["faces"])
        result = {"face_id": face_id, "area_scan_units_squared": record["area_scan_units_squared"],
                  "candidate_group": "unresolved", "outer_face_candidates": matching_outer,
                  "feature_candidates": []}
        if len(matching_outer) == 1:
            bounds = record["bbox_scan_units"]
            flat_z = abs(bounds[5]-bounds[2]) <= 1e-4
            result["candidate_group"] = "inherited_horizontal_surface_review" if flat_z else "inherited_surface_review"
        elif len(matching_outer) > 1:
            result["candidate_group"] = "ambiguous_outer_signature"
        else:
            points, interior_count = sample_trimmed_face(TopoDS.Face_s(faces.FindKey(face_id)))
            result["interior_sample_count"] = interior_count
            result["total_sample_count"] = len(points)
            if interior_count > 0:
                for feature in features:
                    for support in finite_cylinder_support_matches(points, feature):
                        result["feature_candidates"].append({"feature_id": feature["feature_id"],
                            "candidate_function": feature["candidate_function"], "support": support})
                if len(result["feature_candidates"]) == 1:
                    match = result["feature_candidates"][0]
                    result["candidate_group"] = match["candidate_function"]
                elif result["feature_candidates"]:
                    result["candidate_group"] = "ambiguous_construction_support"
                if result["candidate_group"] == "unresolved":
                    partial = partial_outer_candidates(record, points, outer["faces"], outer_faces)
                    result["partial_outer_candidates"] = partial
                    if len(partial) == 1:
                        bounds = record["bbox_scan_units"]
                        flat_z = abs(bounds[5]-bounds[2]) <= 1e-4
                        result["candidate_group"] = ("inherited_trimmed_horizontal_review" if flat_z
                                                     else "inherited_trimmed_surface_review")
                    elif partial:
                        result["candidate_group"] = "ambiguous_partial_outer_match"
        records.append(result)
    groups = Counter(row["candidate_group"] for row in records)
    areas = {name: math.fsum(row["area_scan_units_squared"] for row in records if row["candidate_group"] == name)
             for name in groups}
    summary = {"schema": "m64-reference-thermal-face-proposals/v1",
        "source_sha256": {name: getattr(args, name + "_sha256") for name in ("step", "inventory", "outer_step", "outer_inventory", "contract", "builder")},
        "outer_step_sha256": outer["source_sha256"], "ocp_version": OCP.__version__,
        "face_count": len(records), "candidate_group_counts": dict(groups),
        "candidate_group_area_scan_units_squared": areas,
        "method": "outer_signature_or_finite_F47_support_or_exact_sample_distances_to_trimmed_outer_face",
        "tolerance_scan_units": 1e-4, "sampling_not_exhaustive_surface_proof": True,
        "classification": "935_research_geometry_proposals_not_M64_interfaces",
        "physical_boundary_conditions_assigned": False, "temperature_assigned": False,
        "geometry_modified": False, "cht_solved": False, "manufacturing_authorized": False}
    args.output.mkdir(parents=True)
    (args.output / "private-proposed-face-groups.json").write_text(json.dumps({**summary, "faces": records}, indent=2) + "\n")
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
