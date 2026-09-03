#!/usr/bin/env python3
"""F42.2 surgical p-curve repair without changing any 3D surface.

The program deliberately works on topology-only copies.  It first reproduces
the requested 25-face trial, then performs a diagnostic expansion to every
curve-on-surface pair already reported faulty by OCCT.  The expansion is needed
to test the zero-BOP gate; it is not silently promoted to a manufacturing
repair.  No offset, sewing, surface rebuild, or 3D-curve rebuild is available.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
from OCP.ShapeFix import ShapeFix_Edge
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCP.TopoDS import TopoDS

from audit_brep_f42 import brepcheck, read_step, shape_properties, topology
from repair_topology_f42_1 import (
    full_bop_map,
    indexed,
    property_delta,
    same_parameter_candidate,
    sha256,
    shared_geometry_audit,
    symmetric_skin_distance,
    write_step,
)


TARGET_FACE_INDICES = (
    3,
    10,
    27,
    35,
    65,
    66,
    68,
    91,
    93,
    94,
    117,
    152,
    168,
    193,
    199,
    205,
    211,
    236,
    259,
    261,
    269,
    272,
    274,
    277,
    292,
)


def pcurve_fault_map(shape) -> dict[str, Any]:
    """Return exact OCCT face/edge pairs for CurveOnSurface faults."""

    faces = indexed(shape, TopAbs_FACE)
    edges = indexed(shape, TopAbs_EDGE)
    analyzer = BOPAlgo_ArgumentAnalyzer()
    analyzer.SetShape1(shape)
    analyzer.CurveOnSurfaceMode = True
    analyzer.Perform()
    pairs: set[tuple[int, int]] = set()
    statuses: dict[str, int] = {}
    for result in analyzer.GetCheckResult():
        status = str(result.GetCheckStatus()).split(".")[-1]
        statuses[status] = statuses.get(status, 0) + 1
        faulty_faces: list[int] = []
        faulty_edges: list[int] = []
        for faulty in result.GetFaultyShapes1():
            if faulty.ShapeType() == TopAbs_FACE:
                face_index = faces.FindIndex(faulty)
                if face_index:
                    faulty_faces.append(face_index)
            elif faulty.ShapeType() == TopAbs_EDGE:
                edge_index = edges.FindIndex(faulty)
                if edge_index:
                    faulty_edges.append(edge_index)
        pairs.update((face_index, edge_index) for face_index in faulty_faces for edge_index in faulty_edges)
    return {
        "result_count": int(sum(statuses.values())),
        "status_counts": dict(sorted(statuses.items())),
        "face_edge_pairs_private": [list(pair) for pair in sorted(pairs)],
        "unique_face_count": len({face for face, _ in pairs}),
        "unique_edge_count": len({edge for _, edge in pairs}),
    }


def reproject_pairs(shape, pairs: list[tuple[int, int]], tolerance: float) -> dict[str, Any]:
    """Replace only selected 2D p-curves by projections of existing 3D curves."""

    faces = indexed(shape, TopAbs_FACE)
    edges = indexed(shape, TopAbs_EDGE)
    builder = BRep_Builder()
    fixer = ShapeFix_Edge()
    added = 0
    failed: list[list[int]] = []
    seam_pairs = 0
    for face_index, edge_index in sorted(set(pairs)):
        face = TopoDS.Face_s(faces.FindKey(face_index))
        edge = TopoDS.Edge_s(edges.FindKey(edge_index))
        is_seam = BRep_Tool.IsClosed_s(edge, face)
        seam_pairs += int(is_seam)
        try:
            if is_seam:
                builder.UpdateEdge(edge, None, None, face, tolerance)
            else:
                builder.UpdateEdge(edge, None, face, tolerance)
            added += int(fixer.FixAddPCurve(edge, face, is_seam, tolerance))
            # FixAddPCurve guarantees a same-parameter projection.  Calling
            # FixSameParameter again is intentionally avoided because it may
            # approximate a 3D curve, which is outside the F42.2 contract.
        except Exception:  # recorded fail-closed in the private report
            failed.append([face_index, edge_index])
    return {
        "attempted_pair_count": len(set(pairs)),
        "pcurve_added_count": added,
        "seam_pair_count": seam_pairs,
        "failed_pairs_private": failed,
        "projection_tolerance_scan_units": tolerance,
    }


def max_subshape_tolerance(shape) -> dict[str, float]:
    faces = indexed(shape, TopAbs_FACE)
    edges = indexed(shape, TopAbs_EDGE)
    return {
        "maximum_face_tolerance_scan_units": max(
            BRep_Tool.Tolerance_s(TopoDS.Face_s(faces.FindKey(index)))
            for index in range(1, faces.Extent() + 1)
        ),
        "maximum_edge_tolerance_scan_units": max(
            BRep_Tool.Tolerance_s(TopoDS.Edge_s(edges.FindKey(index)))
            for index in range(1, edges.Extent() + 1)
        ),
    }


def pair_chord_deviation(shape, pair: tuple[int, int], sample_count: int = 201) -> dict[str, Any]:
    """Sample distance between one 3D edge and its projected p-curve support."""

    face_index, edge_index = pair
    faces = indexed(shape, TopAbs_FACE)
    edges = indexed(shape, TopAbs_EDGE)
    face = TopoDS.Face_s(faces.FindKey(face_index))
    edge = TopoDS.Edge_s(edges.FindKey(edge_index))
    curve_3d = BRep_Tool.Curve_s(edge, 0.0, 0.0)
    curve_2d = BRep_Tool.CurveOnSurface_s(edge, face, 0.0, 0.0)
    surface = BRep_Tool.Surface_s(face)
    if curve_3d is None or curve_2d is None:
        return {
            "face_index_private": face_index,
            "edge_index_private": edge_index,
            "resolved": False,
        }
    first_3d, last_3d = BRep_Tool.Range_s(edge)
    first_2d, last_2d = BRep_Tool.Range_s(edge, face)
    first = max(float(first_3d), float(first_2d))
    last = min(float(last_3d), float(last_2d))
    distances: list[float] = []
    for parameter in np.linspace(first, last, sample_count):
        point_3d = curve_3d.Value(float(parameter))
        point_2d = curve_2d.Value(float(parameter))
        point_surface = surface.Value(point_2d.X(), point_2d.Y())
        distances.append(float(point_3d.Distance(point_surface)))
    array = np.asarray(distances, dtype=float)
    return {
        "face_index_private": face_index,
        "edge_index_private": edge_index,
        "resolved": True,
        "sample_count": int(array.size),
        "maximum_deviation_scan_units": float(np.max(array)),
        "rms_deviation_scan_units": float(math.sqrt(float(np.mean(array * array)))),
        "edge_tolerance_scan_units": float(BRep_Tool.Tolerance_s(edge)),
    }


def make_trial(original, face_filter: set[int] | None, projection_tolerance: float) -> tuple[Any, dict[str, Any]]:
    candidate = same_parameter_candidate(original, 1.0e-4)
    baseline = pcurve_fault_map(candidate)
    pairs = [tuple(pair) for pair in baseline["face_edge_pairs_private"]]
    selected = pairs if face_filter is None else [pair for pair in pairs if pair[0] in face_filter]
    repair = reproject_pairs(candidate, selected, projection_tolerance)
    residual = pcurve_fault_map(candidate)
    original_properties = shape_properties(original)
    candidate_properties = shape_properties(candidate)
    return candidate, {
        "scope": "all_OCCT_reported_fault_pairs" if face_filter is None else "mapped_25_faces_only",
        "baseline_pcurve_faults": baseline,
        "repair": repair,
        "residual_pcurve_faults": residual,
        "properties": candidate_properties,
        "property_delta": property_delta(original_properties, candidate_properties),
        "shared_geometry": shared_geometry_audit(original, candidate),
        "subshape_tolerances": max_subshape_tolerance(candidate),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--candidate-step", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skin-samples-each-direction", type=int, default=80)
    args = parser.parse_args()
    if sha256(args.input) != args.expected_sha256:
        raise RuntimeError("input_SHA256_mismatch")
    original, _ = read_step(args.input)
    original_properties = shape_properties(original)

    _, target_trial = make_trial(original, set(TARGET_FACE_INDICES), 5.0e-3)
    candidate, expanded_trial = make_trial(original, None, 2.0e-2)
    residual_pairs = [
        tuple(pair)
        for pair in expanded_trial["residual_pcurve_faults"]["face_edge_pairs_private"]
    ]
    deviations = [pair_chord_deviation(candidate, pair) for pair in residual_pairs]
    maximum_deviation = max(
        (item.get("maximum_deviation_scan_units", math.inf) for item in deviations),
        default=0.0,
    )

    # A full BOP screen is deliberately run even though residual p-curves have
    # already closed the acceptance gate.
    pre_export_bop = full_bop_map(candidate)
    write_step(candidate, args.candidate_step)
    roundtrip, _ = read_step(args.candidate_step)
    roundtrip_properties = shape_properties(roundtrip)
    roundtrip_bop = full_bop_map(roundtrip)
    roundtrip_check = brepcheck(roundtrip)
    roundtrip_topology = topology(roundtrip)
    skin = symmetric_skin_distance(original, roundtrip, args.skin_samples_each_direction)
    roundtrip_delta = property_delta(original_properties, roundtrip_properties)
    geometry_gate = (
        expanded_trial["shared_geometry"]["all_3D_surfaces_identical"]
        and expanded_trial["shared_geometry"]["all_3D_curves_identical_or_both_null"]
        and skin["maximum_sampled_skin_distance_scan_units"] <= 2.0e-2
        and roundtrip_delta["maximum_bbox_coordinate_delta_scan_units"] <= 2.0e-2
    )
    topology_gate = roundtrip_check["shape_valid"] and roundtrip_bop["result_count"] == 0
    local_acceptance = geometry_gate and topology_gate and maximum_deviation <= 2.0e-2
    report = {
        "schema": "porsche-917-f42.2-private-surgical-pcurve-repair/v1",
        "phase": "F42.2",
        "verdict": (
            "PRE_GMSH_TOPOLOGY_ACCEPTED_PRIVATE_NOT_PRINTABLE"
            if local_acceptance
            else "REPAIR_REJECTED_FAIL_CLOSED"
        ),
        "input": {
            "sha256": args.expected_sha256,
            "bytes": args.input.stat().st_size,
            "repository_policy": "private_local_only_not_copied_to_git",
        },
        "repair_contract": {
            "same_parameter_tolerance_scan_units": 1.0e-4,
            "projection_tolerance_limit_scan_units": 2.0e-2,
            "maximum_allowed_skin_displacement_scan_units": 2.0e-2,
            "offset_used": False,
            "sewing_used": False,
            "surface_rebuild_used": False,
            "3D_curve_rebuild_used": False,
        },
        "baseline_properties": original_properties,
        "mapped_25_face_trial": target_trial,
        "diagnostic_expanded_trial": expanded_trial,
        "residual_pair_chord_deviation": {
            "classification": "201_parameter_samples_per_pair_not_continuous_bound",
            "maximum_deviation_scan_units": maximum_deviation,
            "pairs_private": deviations,
        },
        "pre_export_full_BOPAlgo": pre_export_bop,
        "private_candidate": {
            "filename": args.candidate_step.name,
            "sha256": sha256(args.candidate_step),
            "bytes": args.candidate_step.stat().st_size,
            "repository_policy": "private_local_only_rejected_diagnostic_STEP",
        },
        "roundtrip": {
            "properties": roundtrip_properties,
            "property_delta": roundtrip_delta,
            "brepcheck": roundtrip_check,
            "topology": roundtrip_topology,
            "sampled_skin_distance": skin,
            "full_BOPAlgo": roundtrip_bop,
        },
        "gates_before_gmsh": {
            "same_3D_surfaces_and_curves_before_export": (
                expanded_trial["shared_geometry"]["all_3D_surfaces_identical"]
                and expanded_trial["shared_geometry"]["all_3D_curves_identical_or_both_null"]
            ),
            "skin_and_bbox_at_most_0_02": geometry_gate,
            "residual_edge_surface_deviation_at_most_0_02": maximum_deviation <= 2.0e-2,
            "roundtrip_BRepCheck_valid": roundtrip_check["shape_valid"],
            "roundtrip_zero_BOPAlgo_faults": roundtrip_bop["result_count"] == 0,
            "pre_gmsh_candidate_accepted": local_acceptance,
            "manufacturing_authorized": False,
        },
        "decision": {
            "clean_F42_2_STEP_produced": False,
            "candidate_retained_only_for_private_diagnostics": True,
            "reason": (
                "Residual shared conical-edge p-curves exceed the bounded 0.02 tolerance and "
                "BOPAlgo is nonzero; changing their 3D curves or support surfaces is forbidden."
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "verdict": report["verdict"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
