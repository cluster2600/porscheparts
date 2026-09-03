#!/usr/bin/env python3
"""Tentative F42.1 de reparation p-curves strictement non deformante.

La copie topologique partage explicitement les surfaces et courbes 3D OCCT avec
l'original (`copyGeom=False`). Seul `BRepLib.SameParameter` est applique. Aucun
offset, aucune couture globale et aucun remodelage de surface n'est disponible
dans ce programme.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy, BRepBuilderAPI_MakeVertex
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepLib import BRepLib
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCP.TopExp import TopExp
from OCP.TopLoc import TopLoc_Location
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Pnt

from audit_brep_f42 import brepcheck, read_step, shape_properties, topology


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def indexed(shape, kind):
    result = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, kind, result)
    return result


def same_parameter_candidate(original, tolerance: float):
    # copyGeom=False is the central non-deformation lock: 3D geometry is shared.
    candidate = BRepBuilderAPI_Copy(original, False, False).Shape()
    BRepLib.SameParameter_s(candidate, tolerance, True)
    return candidate


def shared_geometry_audit(original, candidate) -> dict[str, Any]:
    original_faces = indexed(original, TopAbs_FACE)
    candidate_faces = indexed(candidate, TopAbs_FACE)
    original_edges = indexed(original, TopAbs_EDGE)
    candidate_edges = indexed(candidate, TopAbs_EDGE)
    shared_surfaces = 0
    if original_faces.Extent() == candidate_faces.Extent():
        for index in range(1, original_faces.Extent() + 1):
            surface_a = BRep_Tool.Surface_s(TopoDS.Face_s(original_faces.FindKey(index)))
            surface_b = BRep_Tool.Surface_s(TopoDS.Face_s(candidate_faces.FindKey(index)))
            shared_surfaces += int(surface_a is surface_b)
    shared_curves = 0
    both_null_curves = 0
    max_range_delta = 0.0
    if original_edges.Extent() == candidate_edges.Extent():
        for index in range(1, original_edges.Extent() + 1):
            edge_a = TopoDS.Edge_s(original_edges.FindKey(index))
            edge_b = TopoDS.Edge_s(candidate_edges.FindKey(index))
            curve_a = BRep_Tool.Curve_s(edge_a, 0.0, 0.0)
            curve_b = BRep_Tool.Curve_s(edge_b, 0.0, 0.0)
            if curve_a is None and curve_b is None:
                both_null_curves += 1
            else:
                shared_curves += int(curve_a is curve_b)
            range_a = BRep_Tool.Range_s(edge_a)
            range_b = BRep_Tool.Range_s(edge_b)
            max_range_delta = max(
                max_range_delta,
                abs(float(range_a[0]) - float(range_b[0])),
                abs(float(range_a[1]) - float(range_b[1])),
            )
    return {
        "copy_mode": "BRepBuilderAPI_Copy(copyGeom=False,copyMesh=False)",
        "surface_count_original": original_faces.Extent(),
        "surface_count_candidate": candidate_faces.Extent(),
        "identical_3D_surface_handle_count": shared_surfaces,
        "edge_count_original": original_edges.Extent(),
        "edge_count_candidate": candidate_edges.Extent(),
        "identical_3D_curve_handle_count": shared_curves,
        "both_null_degenerated_curve_count": both_null_curves,
        "maximum_3D_curve_parameter_range_delta": max_range_delta,
        "all_3D_surfaces_identical": shared_surfaces == original_faces.Extent(),
        "all_3D_curves_identical_or_both_null": (
            shared_curves + both_null_curves == original_edges.Extent()
        ),
    }


def property_delta(original: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    bbox_delta = [
        abs(float(a) - float(b))
        for a, b in zip(original["bbox_scan_units"], candidate["bbox_scan_units"])
    ]
    volume_delta = candidate["volume_scan_units_cubed"] - original["volume_scan_units_cubed"]
    area_delta = (
        candidate["surface_area_scan_units_squared"]
        - original["surface_area_scan_units_squared"]
    )
    return {
        "maximum_bbox_coordinate_delta_scan_units": max(bbox_delta),
        "bbox_coordinate_deltas_scan_units": bbox_delta,
        "volume_delta_scan_units_cubed": volume_delta,
        "volume_relative_delta": volume_delta / original["volume_scan_units_cubed"],
        "surface_area_delta_scan_units_squared": area_delta,
        "surface_area_relative_delta": area_delta / original["surface_area_scan_units_squared"],
    }


def pcurve_faults(shape) -> dict[str, Any]:
    analyzer = BOPAlgo_ArgumentAnalyzer()
    analyzer.SetShape1(shape)
    analyzer.CurveOnSurfaceMode = True
    analyzer.Perform()
    counts = Counter(
        str(result.GetCheckStatus()).split(".")[-1]
        for result in analyzer.GetCheckResult()
    )
    return {"status_counts": dict(sorted(counts.items())), "fault_count": int(sum(counts.values()))}


def full_bop_map(shape) -> dict[str, Any]:
    faces = indexed(shape, TopAbs_FACE)
    edges = indexed(shape, TopAbs_EDGE)
    analyzer = BOPAlgo_ArgumentAnalyzer()
    analyzer.SetShape1(shape)
    analyzer.SelfInterMode = True
    analyzer.SmallEdgeMode = True
    analyzer.RebuildFaceMode = True
    analyzer.ContinuityMode = True
    analyzer.CurveOnSurfaceMode = True
    analyzer.Perform()
    counts: Counter[str] = Counter()
    self_faces: set[int] = set()
    pcurve_faces: set[int] = set()
    pcurve_edges: set[int] = set()
    for result in analyzer.GetCheckResult():
        status = str(result.GetCheckStatus()).split(".")[-1]
        counts[status] += 1
        for faulty in result.GetFaultyShapes1():
            if faulty.ShapeType() == TopAbs_FACE:
                face_index = faces.FindIndex(faulty)
                if face_index:
                    (self_faces if status == "BOPAlgo_SelfIntersect" else pcurve_faces).add(
                        face_index
                    )
            elif faulty.ShapeType() == TopAbs_EDGE:
                edge_index = edges.FindIndex(faulty)
                if edge_index:
                    pcurve_edges.add(edge_index)
    return {
        "has_faulty": bool(analyzer.HasFaulty()),
        "status_counts": dict(sorted(counts.items())),
        "result_count": int(sum(counts.values())),
        "self_intersecting_face_indices_private": sorted(self_faces),
        "invalid_pcurve_face_indices_private": sorted(pcurve_faces),
        "invalid_pcurve_edge_indices_private": sorted(pcurve_edges),
    }


def face_seed_points(shape, maximum: int) -> list[gp_Pnt]:
    BRepMesh_IncrementalMesh(shape, 0.8, False, 0.45, True).Perform()
    faces = indexed(shape, TopAbs_FACE)
    indices = np.linspace(1, faces.Extent(), num=min(maximum, faces.Extent()), dtype=int)
    result: list[gp_Pnt] = []
    for face_index in indices:
        face = TopoDS.Face_s(faces.FindKey(int(face_index)))
        location = TopLoc_Location()
        mesh = BRep_Tool.Triangulation_s(face, location)
        if mesh is None or not mesh.HasUVNodes() or mesh.NbTriangles() == 0:
            continue
        triangle = mesh.Triangle(max(1, mesh.NbTriangles() // 2)).Get()
        uv = [mesh.UVNode(node) for node in triangle]
        u = sum(point.X() for point in uv) / 3.0
        v = sum(point.Y() for point in uv) / 3.0
        point = gp_Pnt()
        BRepAdaptor_Surface(face, True).D0(u, v, point)
        result.append(point)
    return result


def directed_sample_distance(source, target, samples: int) -> dict[str, Any]:
    points = face_seed_points(source, samples)
    extrema = BRepExtrema_DistShapeShape()
    extrema.SetMultiThread(True)
    extrema.LoadS2(target)
    distances: list[float] = []
    failures = 0
    for point in points:
        extrema.LoadS1(BRepBuilderAPI_MakeVertex(point).Shape())
        extrema.Perform()
        if not extrema.IsDone():
            failures += 1
            continue
        distances.append(float(extrema.Value()))
    array = np.asarray(distances, dtype=float)
    return {
        "requested_face_samples": samples,
        "resolved_samples": int(array.size),
        "failures": failures,
        "maximum_scan_units": float(np.max(array)) if array.size else math.inf,
        "p95_scan_units": float(np.quantile(array, 0.95)) if array.size else math.inf,
    }


def symmetric_skin_distance(shape_a, shape_b, samples_each_direction: int) -> dict[str, Any]:
    a_to_b = directed_sample_distance(shape_a, shape_b, samples_each_direction)
    b_to_a = directed_sample_distance(shape_b, shape_a, samples_each_direction)
    return {
        "classification": "symmetric_exact_OCCT_point_to_trimmed_BRep_sample_not_continuous_Hausdorff",
        "original_to_candidate": a_to_b,
        "candidate_to_original": b_to_a,
        "maximum_sampled_skin_distance_scan_units": max(
            a_to_b["maximum_scan_units"], b_to_a["maximum_scan_units"]
        ),
    }


def write_step(shape, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    status = writer.Write(str(path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"STEP_write_failed:{status}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate-step", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--skin-samples-each-direction", type=int, default=80)
    args = parser.parse_args()
    if sha256(args.input) != args.expected_sha256:
        raise RuntimeError("input_SHA256_mismatch")
    original, _ = read_step(args.input)
    original_properties = shape_properties(original)
    baseline_pcurve = pcurve_faults(original)

    trials: list[dict[str, Any]] = []
    candidates: dict[float, Any] = {}
    for tolerance in (1.0e-7, 1.0e-6, 1.0e-5, 1.0e-4, 1.0e-3, 2.0e-2):
        candidate = same_parameter_candidate(original, tolerance)
        candidates[tolerance] = candidate
        candidate_properties = shape_properties(candidate)
        geometry = shared_geometry_audit(original, candidate)
        delta = property_delta(original_properties, candidate_properties)
        faults = pcurve_faults(candidate)
        invariant = (
            geometry["all_3D_surfaces_identical"]
            and geometry["all_3D_curves_identical_or_both_null"]
            and geometry["maximum_3D_curve_parameter_range_delta"] <= 1.0e-12
            and delta["maximum_bbox_coordinate_delta_scan_units"] <= 1.0e-12
            and abs(delta["volume_delta_scan_units_cubed"]) <= 1.0e-6
            and abs(delta["surface_area_delta_scan_units_squared"]) <= 1.0e-6
        )
        trials.append(
            {
                "same_parameter_tolerance_scan_units": tolerance,
                "properties": candidate_properties,
                "property_delta": delta,
                "shared_geometry": geometry,
                "pcurve_screen": faults,
                "strict_non_deformation_invariants_pass": invariant,
            }
        )
    acceptable = [trial for trial in trials if trial["strict_non_deformation_invariants_pass"]]
    selected_trial = min(
        acceptable,
        key=lambda trial: (
            trial["pcurve_screen"]["fault_count"],
            trial["same_parameter_tolerance_scan_units"],
        ),
    )
    tolerance = float(selected_trial["same_parameter_tolerance_scan_units"])
    candidate = candidates[tolerance]
    write_step(candidate, args.candidate_step)
    roundtrip, _ = read_step(args.candidate_step)
    roundtrip_properties = shape_properties(roundtrip)
    roundtrip_delta = property_delta(original_properties, roundtrip_properties)
    skin = symmetric_skin_distance(original, roundtrip, args.skin_samples_each_direction)
    full = full_bop_map(roundtrip)
    shape_check = brepcheck(roundtrip)
    shape_topology = topology(roundtrip)

    skin_limit = 0.02
    geometry_gate = (
        skin["maximum_sampled_skin_distance_scan_units"] <= skin_limit
        and roundtrip_delta["maximum_bbox_coordinate_delta_scan_units"] <= skin_limit
    )
    clean_gate = (
        shape_check["shape_valid"]
        and shape_topology["unique_subshape_counts"]["solid"] == 1
        and full["result_count"] == 0
        and geometry_gate
    )
    report = {
        "schema": "porsche-917-f42.1-topology-only-repair/v1",
        "phase": "F42.1",
        "verdict": (
            "TOPOLOGY_REPAIR_ACCEPTED_PRIVATE_NOT_PRINTABLE"
            if clean_gate
            else "REPAIR_REJECTED_FAIL_CLOSED"
        ),
        "input": {
            "sha256": args.expected_sha256,
            "bytes": args.input.stat().st_size,
            "repository_policy": "private_local_only_not_copied_to_git",
        },
        "repair_scope": {
            "operation": "BRepLib.SameParameter forced on topology-only copy",
            "offset_used": False,
            "3D_surface_rebuild_used": False,
            "sewing_used": False,
            "maximum_allowed_skin_displacement_scan_units": skin_limit,
        },
        "baseline": {
            "properties": original_properties,
            "pcurve_screen": baseline_pcurve,
        },
        "tolerance_trials": trials,
        "selected_tolerance_scan_units": tolerance,
        "selected_pre_export": selected_trial,
        "private_candidate": {
            "filename": args.candidate_step.name,
            "sha256": sha256(args.candidate_step),
            "bytes": args.candidate_step.stat().st_size,
            "repository_policy": "private_local_only_rejected_candidate_not_release_STEP",
        },
        "roundtrip": {
            "properties": roundtrip_properties,
            "property_delta": roundtrip_delta,
            "brepcheck": shape_check,
            "topology": shape_topology,
            "sampled_skin_distance": skin,
            "boolean_argument_analyzer": full,
        },
        "gates": {
            "strict_pre_export_non_deformation_invariants": selected_trial[
                "strict_non_deformation_invariants_pass"
            ],
            "sampled_skin_distance_at_most_0_02": geometry_gate,
            "roundtrip_exact_BRepCheck_valid": shape_check["shape_valid"],
            "zero_BOPAlgo_faults": full["result_count"] == 0,
            "private_candidate_accepted_as_clean_repair": clean_gate,
            "manufacturing_authorized": False,
        },
        "decision": {
            "clean_F42_1_STEP_produced": clean_gate,
            "candidate_retained_only_for_private_diagnostics": not clean_gate,
            "reason": (
                "SameParameter reduces invalid p-curves but cannot repair self-intersecting "
                "3D faces without forbidden surface reconstruction."
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "verdict": report["verdict"], "gates": report["gates"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
