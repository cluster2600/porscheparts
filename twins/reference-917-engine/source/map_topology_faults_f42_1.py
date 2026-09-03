#!/usr/bin/env python3
"""Cartographie privee/publique des faces F42.1 a reconstruire."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.TopoDS import TopoDS

from audit_brep_f42 import bbox, read_step


def face_map(shape):
    result = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_FACE, result)
    return result


def surface_type(face) -> str:
    return str(BRepAdaptor_Surface(face, True).GetType()).split(".")[-1]


def patch_plan(kind: str, self_intersect: bool, invalid_pcurve: bool) -> dict[str, Any]:
    if self_intersect:
        return {
            "classification": "likely_scan_derived_outer_BSpline_face_manual_provenance_required",
            "patch": "rebuild_local_face_from_locked_F40_profiles_with_original_3D_boundary_curves",
            "may_change_3D_surface": True,
            "allowed_in_F42_1": False,
            "acceptance": "sampled_and_continuous_skin_deviation_le_0_02_and_zero_BOP_faults",
        }
    if kind == "GeomAbs_BSplineSurface":
        return {
            "classification": "likely_scan_derived_outer_or_boolean_trimmed_BSpline",
            "patch": (
                "reproject_2D_curve_on_unchanged_surface_then_rebuild_trim_wire; "
                "if projection remains invalid regenerate owning Boolean only"
            ),
            "may_change_3D_surface": False,
            "allowed_in_F42_1": True,
            "acceptance": "unchanged_3D_surface_handle_and_zero_curve_on_surface_fault",
        }
    return {
        "classification": "analytic_functional_or_boolean_face_provenance_required",
        "patch": "redo_originating_internal_analytic_cutter_and Boolean on locked outer skin",
        "may_change_3D_surface": False,
        "allowed_in_F42_1": False,
        "acceptance": "locked_outer_skin_distance_le_0_02_and_functional_surface_contract_review",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--repair-report", type=Path, required=True)
    parser.add_argument("--gmsh-log", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.repair_report.read_text(encoding="utf-8"))
    log = args.gmsh_log.read_text(encoding="utf-8", errors="replace")
    invalid_events = [
        (int(count), int(face))
        for count, face in re.findall(
            r"Warning : (\d+) elements remain invalid in surface (\d+)", log
        )
    ]
    invalid_faces = sorted({face for _, face in invalid_events})
    shape, _ = read_step(args.step)
    faces = face_map(shape)
    bop = report["roundtrip"]["boolean_argument_analyzer"]
    self_faces = set(bop["self_intersecting_face_indices_private"])
    pcurve_faces = set(bop["invalid_pcurve_face_indices_private"])
    records: list[dict[str, Any]] = []
    for tag in invalid_faces:
        if tag < 1 or tag > faces.Extent():
            records.append({"gmsh_surface_tag": tag, "OCCT_face_index_resolved": False})
            continue
        face = TopoDS.Face_s(faces.FindKey(tag))
        props = GProp_GProps()
        BRepGProp.SurfaceProperties_s(face, props)
        kind = surface_type(face)
        is_self = tag in self_faces
        is_pcurve = tag in pcurve_faces
        records.append(
            {
                "gmsh_surface_tag": tag,
                "OCCT_face_index_resolved": True,
                "surface_type": kind,
                "area_scan_units_squared": float(props.Mass()),
                "center_of_mass_scan_units": [float(value) for value in props.CentreOfMass().Coord()],
                "bbox_scan_units": bbox(face),
                "BOP_self_intersect": is_self,
                "BOP_invalid_curve_on_surface": is_pcurve,
                "patch_plan": patch_plan(kind, is_self, is_pcurve),
            }
        )
    private = {
        "schema": "porsche-917-f42.1-private-face-reconstruction-map/v1",
        "phase": "F42.1",
        "mapping_limit": (
            "Gmsh entity tags are mapped provisionally to OCCT face traversal indices after the "
            "same STEP roundtrip; persistent topological naming is unavailable"
        ),
        "gmsh": {
            "software": "Gmsh 4.12.1 using OpenCASCADE STEP importer",
            "container_image_digest": "sha256:4a19fa7d1f253beb3106970ae2635cff85d5aeeaf062aaf807d1dab7b940fb33",
            "input_mount": "read_only",
            "warning_event_count": len(invalid_events),
            "cumulative_invalid_elements_across_repeated_refinement_warnings": sum(
                count for count, _ in invalid_events
            ),
            "unique_invalid_surface_count": len(invalid_faces),
            "three_dimensional_mesh_completed": "Done meshing 3D" in log,
            "run_incomplete_or_terminated_without_3D_completion": "Done meshing 3D" not in log,
        },
        "faces": records,
        "BOP_summary": {
            "self_intersecting_face_count": len(self_faces),
            "invalid_pcurve_face_count": len(pcurve_faces),
            "invalid_pcurve_edge_count": len(bop["invalid_pcurve_edge_indices_private"]),
        },
        "verdict": "RECONSTRUCTION_MAP_ONLY_NOT_GEOMETRY_NOT_PRINTABLE",
    }
    public_faces = [
        {
            key: value
            for key, value in record.items()
            if key not in {"center_of_mass_scan_units", "bbox_scan_units"}
        }
        for record in records
    ]
    public = {
        **{key: value for key, value in private.items() if key != "faces"},
        "schema": "porsche-917-f42.1-public-face-reconstruction-map/v1",
        "faces": public_faces,
        "publication": {
            "private_STEP_published": False,
            "scan_derived_coordinates_published": False,
            "map_is_geometry": False,
        },
    }
    args.private_output.parent.mkdir(parents=True, exist_ok=True)
    args.public_output.parent.mkdir(parents=True, exist_ok=True)
    args.private_output.write_text(json.dumps(private, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.public_output.write_text(json.dumps(public, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"private": str(args.private_output), "public": str(args.public_output), "faces": len(records)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
