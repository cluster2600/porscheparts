#!/usr/bin/env python3
"""Audit OCCT exact d'un STEP F41 prive, sans modifier sa peau externe.

Le controle d'epaisseur utilise des points issus de la triangulation uniquement
pour echantillonner les faces. Les points, normales et intersections sont ensuite
recalcules sur les surfaces B-Rep exactes. Les impacts issus des coutures de la
triangulation ne peuvent donc pas devenir des epaisseurs artificiellement nulles.
Ce reste un ecran par cordes normales echantillonnees, pas une preuve exhaustive
de l'epaisseur locale ni une qualification de fabrication.
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
from OCP.Bnd import Bnd_Box
from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepGProp import BRepGProp
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepTools import BRepTools
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import (
    TopAbs_EDGE,
    TopAbs_FACE,
    TopAbs_IN,
    TopAbs_OUT,
    TopAbs_SHELL,
    TopAbs_SOLID,
    TopAbs_VERTEX,
)
from OCP.TopExp import TopExp
from OCP.TopLoc import TopLoc_Location
from OCP.TopTools import (
    TopTools_IndexedDataMapOfShapeListOfShape,
    TopTools_IndexedMapOfShape,
)
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt, gp_Vec


SHAPE_TYPES = {
    TopAbs_SOLID: "solid",
    TopAbs_SHELL: "shell",
    TopAbs_FACE: "face",
    TopAbs_EDGE: "edge",
    TopAbs_VERTEX: "vertex",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_step(path: Path):
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"STEP_read_failed:{status}")
    transferred = reader.TransferRoots()
    if transferred < 1:
        raise RuntimeError("STEP_has_no_transferable_root")
    shape = reader.OneShape()
    if shape.IsNull():
        raise RuntimeError("STEP_transferred_null_shape")
    return shape, int(transferred)


def indexed_shapes(shape, kind):
    result = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, kind, result)
    return result


def bbox(shape) -> list[float]:
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, box, True, False)
    return [float(value) for value in box.Get()]


def shape_properties(shape) -> dict[str, Any]:
    volume = GProp_GProps()
    surface = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, volume)
    BRepGProp.SurfaceProperties_s(shape, surface)
    bounds = bbox(shape)
    return {
        "volume_scan_units_cubed": float(volume.Mass()),
        "surface_area_scan_units_squared": float(surface.Mass()),
        "center_of_mass_scan_units": [float(v) for v in volume.CentreOfMass().Coord()],
        "bbox_scan_units": bounds,
        "bbox_size_scan_units": [bounds[3 + axis] - bounds[axis] for axis in range(3)],
    }


def brepcheck(shape) -> dict[str, Any]:
    analyzer = BRepCheck_Analyzer(shape, True)
    analyzer.SetExactMethod(True)
    analyzer.SetParallel(True)
    counts: Counter[str] = Counter()
    checked = 0
    for kind in (TopAbs_SOLID, TopAbs_SHELL, TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX):
        items = indexed_shapes(shape, kind)
        for index in range(1, items.Extent() + 1):
            checked += 1
            result = analyzer.Result(items.FindKey(index))
            for status in result.Status():
                name = str(status).split(".")[-1]
                if name != "BRepCheck_NoError":
                    counts[name] += 1
    return {
        "exact_method": True,
        "parallel": True,
        "shape_valid": bool(analyzer.IsValid()),
        "subshapes_checked": checked,
        "nonzero_status_counts": dict(sorted(counts.items())),
    }


def topology(shape) -> dict[str, Any]:
    counts = {name: indexed_shapes(shape, kind).Extent() for kind, name in SHAPE_TYPES.items()}
    ancestors = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndUniqueAncestors_s(shape, TopAbs_EDGE, TopAbs_FACE, ancestors)
    free = 0
    seams = 0
    degenerated = 0
    manifold = 0
    nonmanifold = 0
    ancestor_histogram: Counter[int] = Counter()
    for index in range(1, ancestors.Extent() + 1):
        edge = TopoDS.Edge_s(ancestors.FindKey(index))
        face_list = list(ancestors.FindFromIndex(index))
        face_count = len(face_list)
        ancestor_histogram[face_count] += 1
        if BRep_Tool.Degenerated_s(edge):
            degenerated += 1
        elif face_count == 1 and BRep_Tool.IsClosed_s(edge, TopoDS.Face_s(face_list[0])):
            seams += 1
        elif face_count == 1:
            free += 1
        elif face_count == 2:
            manifold += 1
        else:
            nonmanifold += 1
    return {
        "unique_subshape_counts": counts,
        "unique_edge_face_ancestor_histogram": {
            str(key): value for key, value in sorted(ancestor_histogram.items())
        },
        "edge_classification": {
            "closed_surface_seams": seams,
            "degenerated_edges": degenerated,
            "free_edges": free,
            "two_face_manifold_edges": manifold,
            "nonmanifold_edges": nonmanifold,
        },
    }


def tolerance_and_small_features(shape) -> dict[str, Any]:
    tolerances: dict[str, list[float]] = {"vertex": [], "edge": [], "face": []}
    for kind, name in ((TopAbs_VERTEX, "vertex"), (TopAbs_EDGE, "edge"), (TopAbs_FACE, "face")):
        items = indexed_shapes(shape, kind)
        for index in range(1, items.Extent() + 1):
            item = items.FindKey(index)
            if kind == TopAbs_VERTEX:
                value = BRep_Tool.Tolerance_s(TopoDS.Vertex_s(item))
            elif kind == TopAbs_EDGE:
                value = BRep_Tool.Tolerance_s(TopoDS.Edge_s(item))
            else:
                value = BRep_Tool.Tolerance_s(TopoDS.Face_s(item))
            tolerances[name].append(float(value))

    edge_lengths: list[float] = []
    edges = indexed_shapes(shape, TopAbs_EDGE)
    for index in range(1, edges.Extent() + 1):
        props = GProp_GProps()
        BRepGProp.LinearProperties_s(edges.FindKey(index), props)
        edge_lengths.append(float(props.Mass()))
    face_areas: list[float] = []
    faces = indexed_shapes(shape, TopAbs_FACE)
    for index in range(1, faces.Extent() + 1):
        props = GProp_GProps()
        BRepGProp.SurfaceProperties_s(faces.FindKey(index), props)
        face_areas.append(float(props.Mass()))

    def summary(values: list[float]) -> dict[str, float | int]:
        array = np.asarray(values, dtype=float)
        return {
            "count": int(array.size),
            "min": float(np.min(array)),
            "p01": float(np.quantile(array, 0.01)),
            "median": float(np.median(array)),
            "max": float(np.max(array)),
        }

    return {
        "tolerance_scan_units": {name: summary(values) for name, values in tolerances.items()},
        "unique_edge_length_scan_units": summary(edge_lengths),
        "unique_face_area_scan_units_squared": summary(face_areas),
        "edge_count_below_1e_minus_5_scan_units": sum(value < 1.0e-5 for value in edge_lengths),
        "face_count_below_1e_minus_8_scan_units_squared": sum(value < 1.0e-8 for value in face_areas),
    }


def argument_analyzer(shape) -> dict[str, Any]:
    analyzer = BOPAlgo_ArgumentAnalyzer()
    analyzer.SetShape1(shape)
    analyzer.SelfInterMode = True
    analyzer.SmallEdgeMode = True
    analyzer.RebuildFaceMode = True
    analyzer.ContinuityMode = True
    analyzer.CurveOnSurfaceMode = True
    analyzer.Perform()
    counts: Counter[str] = Counter()
    faulty_shape_type_counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    for result in analyzer.GetCheckResult():
        status = str(result.GetCheckStatus()).split(".")[-1]
        counts[status] += 1
        faulty = list(result.GetFaultyShapes1())
        for item in faulty:
            shape_type = str(item.ShapeType()).split(".")[-1]
            faulty_shape_type_counts[shape_type] += 1
        if len(examples) < 20:
            examples.append(
                {
                    "status": status,
                    "faulty_shape_count": len(faulty),
                    "faulty_shape_types": [str(item.ShapeType()).split(".")[-1] for item in faulty],
                    "faulty_shape_bboxes_scan_units": [bbox(item) for item in faulty],
                }
            )
    return {
        "modes": [
            "self_intersection",
            "small_edge",
            "face_rebuild",
            "continuity",
            "curve_on_surface",
        ],
        "has_faulty": bool(analyzer.HasFaulty()),
        "has_error": bool(analyzer.HasErrors()),
        "has_warning": bool(analyzer.HasWarnings()),
        "result_count": int(sum(counts.values())),
        "status_counts": dict(sorted(counts.items())),
        "faulty_shape_type_counts": dict(sorted(faulty_shape_type_counts.items())),
        "first_twenty_results": examples,
    }


def weighted_quantile(values: np.ndarray, weights: np.ndarray, quantiles: list[float]) -> list[float]:
    order = np.argsort(values)
    sorted_values = values[order]
    sorted_weights = weights[order]
    centers = np.cumsum(sorted_weights) - 0.5 * sorted_weights
    centers /= np.sum(sorted_weights)
    return [float(np.interp(quantile, centers, sorted_values)) for quantile in quantiles]


def allocate_samples(areas: np.ndarray, requested: int) -> np.ndarray:
    if requested < len(areas):
        raise ValueError(f"sample_count_must_cover_each_face:{requested}<{len(areas)}")
    result = np.ones(len(areas), dtype=int)
    remaining = requested - len(areas)
    if remaining:
        shares = remaining * areas / np.sum(areas)
        whole = np.floor(shares).astype(int)
        result += whole
        left = remaining - int(np.sum(whole))
        if left:
            order = np.argsort(-(shares - whole))
            result[order[:left]] += 1
    return result


def inward_direction(shape, point: gp_Pnt, normal: gp_Vec) -> tuple[gp_Vec | None, float | None]:
    classifier = BRepClass3d_SolidClassifier(shape)
    normal.Normalize()
    for epsilon in (1.0e-4, 1.0e-3, 1.0e-2, 5.0e-2):
        minus = point.Translated(normal.Multiplied(-epsilon))
        plus = point.Translated(normal.Multiplied(epsilon))
        classifier.Perform(minus, 1.0e-7)
        minus_state = classifier.State()
        classifier.Perform(plus, 1.0e-7)
        plus_state = classifier.State()
        if minus_state == TopAbs_IN and plus_state == TopAbs_OUT:
            return normal.Multiplied(-1.0), epsilon
        if plus_state == TopAbs_IN and minus_state == TopAbs_OUT:
            return normal, epsilon
    return None, None


def exact_normal_chord_thickness(
    shape,
    requested_samples: int,
    seed: int,
    tessellation_deflection: float,
    threshold: float,
) -> dict[str, Any]:
    faces = indexed_shapes(shape, TopAbs_FACE)
    face_areas: list[float] = []
    for index in range(1, faces.Extent() + 1):
        props = GProp_GProps()
        BRepGProp.SurfaceProperties_s(faces.FindKey(index), props)
        face_areas.append(float(props.Mass()))
    areas = np.asarray(face_areas, dtype=float)
    allocation = allocate_samples(areas, requested_samples)

    BRepTools.Clean_s(shape)
    BRepMesh_IncrementalMesh(shape, tessellation_deflection, False, 0.35, True).Perform()
    rng = np.random.default_rng(seed)
    bounds = bbox(shape)
    diagonal = math.sqrt(sum((bounds[axis + 3] - bounds[axis]) ** 2 for axis in range(3)))
    intersector = IntCurvesFace_ShapeIntersector()
    intersector.Load(shape, 1.0e-7)

    resolved: list[float] = []
    weights: list[float] = []
    records: list[dict[str, Any]] = []
    unresolved_reasons: Counter[str] = Counter()
    candidate_triangle_count = 0

    for face_index in range(1, faces.Extent() + 1):
        face = TopoDS.Face_s(faces.FindKey(face_index))
        location = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation_s(face, location)
        if triangulation is None or not triangulation.HasUVNodes():
            unresolved_reasons["face_without_UV_triangulation"] += int(allocation[face_index - 1])
            continue
        triangle_count = triangulation.NbTriangles()
        candidate_triangle_count += triangle_count
        triangle_areas = np.empty(triangle_count, dtype=float)
        triangle_nodes: list[tuple[int, int, int]] = []
        transformation = location.Transformation()
        for triangle_index in range(1, triangle_count + 1):
            n1, n2, n3 = triangulation.Triangle(triangle_index).Get()
            triangle_nodes.append((n1, n2, n3))
            p1 = triangulation.Node(n1).Transformed(transformation)
            p2 = triangulation.Node(n2).Transformed(transformation)
            p3 = triangulation.Node(n3).Transformed(transformation)
            triangle_areas[triangle_index - 1] = 0.5 * gp_Vec(p1, p2).Crossed(gp_Vec(p1, p3)).Magnitude()
        positive = triangle_areas > 0.0
        if not bool(np.any(positive)):
            unresolved_reasons["face_without_positive_area_triangle"] += int(allocation[face_index - 1])
            continue
        probabilities = triangle_areas.copy()
        probabilities[~positive] = 0.0
        probabilities /= np.sum(probabilities)
        count = min(int(allocation[face_index - 1]), int(np.count_nonzero(positive)))
        if count < int(allocation[face_index - 1]):
            unresolved_reasons["sampling_triangle_shortfall"] += int(allocation[face_index - 1]) - count
        selected = rng.choice(triangle_count, size=count, replace=False, p=probabilities)
        per_sample_weight = areas[face_index - 1] / max(count, 1)
        adaptor = BRepAdaptor_Surface(face, True)
        for selected_index in selected:
            nodes = triangle_nodes[int(selected_index)]
            uv = [triangulation.UVNode(node) for node in nodes]
            u = sum(value.X() for value in uv) / 3.0
            v = sum(value.Y() for value in uv) / 3.0
            point = gp_Pnt()
            du = gp_Vec()
            dv = gp_Vec()
            try:
                adaptor.D1(u, v, point, du, dv)
            except Exception:
                unresolved_reasons["surface_D1_failed"] += 1
                continue
            normal = du.Crossed(dv)
            if normal.SquareMagnitude() <= 1.0e-20:
                unresolved_reasons["surface_normal_degenerate"] += 1
                continue
            inward, epsilon = inward_direction(shape, point, normal)
            if inward is None or epsilon is None:
                unresolved_reasons["material_side_not_resolved"] += 1
                continue
            origin = point.Translated(inward.Multiplied(epsilon))
            intersector.Perform(gp_Lin(origin, gp_Dir(inward)), 0.0, diagonal * 2.0)
            distances = sorted(
                float(intersector.WParameter(hit))
                for hit in range(1, intersector.NbPnt() + 1)
                if float(intersector.WParameter(hit)) > max(1.0e-6, epsilon * 0.05)
            )
            unique_distances: list[float] = []
            for distance in distances:
                if not unique_distances or distance - unique_distances[-1] > 1.0e-5:
                    unique_distances.append(distance)
            if not unique_distances:
                unresolved_reasons["no_positive_exact_BRep_intersection"] += 1
                continue
            thickness = unique_distances[0] + epsilon
            resolved.append(thickness)
            weights.append(per_sample_weight)
            if len(records) < 50 or thickness < max(record["normal_chord_scan_units"] for record in records):
                records.append(
                    {
                        "face_index": face_index,
                        "point_scan_units": [float(value) for value in point.Coord()],
                        "normal_chord_scan_units": float(thickness),
                        "coincident_exact_hits_collapsed": len(distances) - len(unique_distances),
                    }
                )
                records = sorted(records, key=lambda record: record["normal_chord_scan_units"])[:50]

    if not resolved:
        raise RuntimeError("no_exact_normal_chord_was_resolved")
    values = np.asarray(resolved, dtype=float)
    weight_array = np.asarray(weights, dtype=float)
    quantiles = weighted_quantile(values, weight_array, [0.01, 0.05, 0.5, 0.95, 0.99])
    below_area = float(np.sum(weight_array[values < threshold]))
    resolved_area = float(np.sum(weight_array))
    return {
        "classification": "sampled_exact_OCCT_surface_normal_chord_screen_not_global_minimum_not_medial_thickness_not_CT",
        "tessellation_role": "sampling_only; UV_centroids_seed_exact_surface_D1_and_exact_BRep_line_face_intersections",
        "tessellation_seam_neutralization": (
            "thickness_hits_are_computed by IntCurvesFace_ShapeIntersector on exact BRep faces; "
            "coincident exact hits within 1e-5 scan units are collapsed"
        ),
        "scan_unit_convention": "millimetre_by_project_convention_only_not_dimensionally_certified",
        "requested_samples": requested_samples,
        "resolved_samples": int(values.size),
        "unresolved_samples": int(sum(unresolved_reasons.values())),
        "unresolved_reasons": dict(sorted(unresolved_reasons.items())),
        "candidate_sampling_triangle_count": candidate_triangle_count,
        "total_face_count": int(faces.Extent()),
        "sampled_face_count": int(np.count_nonzero(allocation)),
        "allocated_samples_per_face_min": int(np.min(allocation)),
        "allocated_samples_per_face_max": int(np.max(allocation)),
        "tessellation_linear_deflection_scan_units": tessellation_deflection,
        "minimum_scan_units": float(np.min(values)),
        "p01_scan_units": quantiles[0],
        "p05_scan_units": quantiles[1],
        "median_scan_units": quantiles[2],
        "p95_scan_units": quantiles[3],
        "p99_scan_units": quantiles[4],
        "maximum_scan_units": float(np.max(values)),
        "threshold_scan_units": threshold,
        "resolved_area_weighted_fraction_below_threshold": below_area / resolved_area,
        "resolved_area_weighted_fraction_at_or_above_threshold": 1.0 - below_area / resolved_area,
        "thin_sample_count": int(np.count_nonzero(values < threshold)),
        "smallest_fifty_samples": records,
        "gate_all_sampled_exact_normal_chords_at_or_above_threshold": bool(np.min(values) >= threshold),
        "gate_global_wall_thickness_proven": False,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    input_hash = sha256(args.input)
    if args.expected_sha256 and input_hash != args.expected_sha256:
        raise RuntimeError(f"input_SHA256_mismatch:{input_hash}")
    shape, transferred = read_step(args.input)
    report: dict[str, Any] = {
        "schema": "porsche-917-f42-private-brep-audit/v1",
        "phase": "F42",
        "verdict": "FAIL_CLOSED_NOT_PRINTABLE_NOT_FITMENT_CERTIFIED",
        "input": {
            "filename": args.input.name,
            "sha256": input_hash,
            "bytes": args.input.stat().st_size,
            "repository_policy": "private_local_only_not_copied_to_git",
            "step_roots_transferred": transferred,
        },
        "unit_status": {
            "scan_unit_convention": "millimetre_by_project_convention_only",
            "absolute_scale_certified": False,
            "OEM_917_fitment_certified": False,
        },
        "external_envelope_lock": {
            "rule": "no_ovalization_no_global_offset_no_scan_envelope_change_without_identified_local_defect_and_proof",
            "input_modified": False,
            "external_envelope_changed": False,
        },
        "exact_properties": shape_properties(shape),
        "topology": topology(shape),
        "brepcheck": brepcheck(shape),
        "tolerances_and_small_features": tolerance_and_small_features(shape),
    }
    if not args.skip_argument_analyzer:
        report["boolean_argument_analyzer"] = argument_analyzer(shape)
    if not args.skip_thickness:
        report["exact_sampled_thickness"] = exact_normal_chord_thickness(
            shape,
            args.samples,
            args.seed,
            args.tessellation_deflection,
            args.thickness_threshold,
        )

    topology_gates = {
        "one_solid": report["topology"]["unique_subshape_counts"]["solid"] == 1,
        "one_shell": report["topology"]["unique_subshape_counts"]["shell"] == 1,
        "zero_free_edges": report["topology"]["edge_classification"]["free_edges"] == 0,
        "zero_nonmanifold_edges": report["topology"]["edge_classification"]["nonmanifold_edges"] == 0,
        "exact_brepcheck_valid": bool(report["brepcheck"]["shape_valid"]),
    }
    argument_gates = {
        "zero_boolean_argument_faults": not bool(
            report.get("boolean_argument_analyzer", {}).get("has_faulty", True)
        )
    }
    thickness_gates = {
        "all_sampled_exact_chords_at_least_threshold": bool(
            report.get("exact_sampled_thickness", {}).get(
                "gate_all_sampled_exact_normal_chords_at_or_above_threshold", False
            )
        ),
        "global_wall_thickness_proven": False,
    }
    report["gates"] = {**topology_gates, **argument_gates, **thickness_gates}
    report["repair_decision"] = {
        "repair_attempted": False,
        "private_F42_STEP_produced": False,
        "reason": (
            "No automatic heal is defensible before every Boolean-analyzer fault is localized. "
            "A broad ShapeFix/sew/offset could move the scan-derived external envelope."
        ),
        "required_before_local_repair": [
            "identify each exact faulty subshape and owning operation",
            "prove the defect is internal or prove zero external-skin displacement",
            "repeat exact BRepCheck, Boolean argument analysis, properties and thickness screen",
        ],
    }
    report["release_gates"] = {
        "dimensionally_certified": False,
        "material_hot_card_qualified": False,
        "thermomechanical_fatigue_correlated": False,
        "CT_CND_plan_executed": False,
        "bench_correlated": False,
        "manufacturing_authorized": False,
    }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--samples", type=int, default=640)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--tessellation-deflection", type=float, default=0.5)
    parser.add_argument("--thickness-threshold", type=float, default=1.5)
    parser.add_argument("--skip-argument-analyzer", action="store_true")
    parser.add_argument("--skip-thickness", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        raise FileNotFoundError(args.input)
    if args.samples < 1:
        raise ValueError("samples_must_be_positive")
    report = build_report(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "verdict": report["verdict"], "gates": report["gates"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
