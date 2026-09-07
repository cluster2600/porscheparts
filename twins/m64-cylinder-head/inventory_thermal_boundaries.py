#!/usr/bin/env python3
"""Inventory exact private STEP faces before assigning CHT boundary conditions.

This does not generate a new head, infer a physical scale, classify a face from
its appearance, or run a solver. Face indices are valid only for the bound STEP
hash and OCCT import; private coordinates must not be committed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys


ROLES = {
    "combustion_gas", "intake_gas", "exhaust_gas", "cooling_air",
    "oil", "seat_contact", "guide_contact", "cylinder_contact",
    "cam_carrier_contact", "fastener_contact", "spark_plug_contact",
    "declared_adiabatic",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_assignments(mapping: dict | None, source_hash: str, face_count: int,
                         ocp_version: str = "7.9.3.1") -> dict:
    """Reject stale or overlapping labels rather than defaulting to adiabatic."""
    if mapping is None:
        return {}
    if mapping.get("source_sha256") != source_hash:
        raise ValueError("boundary_mapping_source_hash_mismatch")
    if mapping.get("ocp_version") != ocp_version:
        raise ValueError("boundary_mapping_OCCT_import_version_mismatch")
    assignments = mapping.get("assignments")
    if not isinstance(assignments, list):
        raise ValueError("assignments_list_required")
    by_face = {}
    for group in assignments:
        role = group.get("role")
        evidence = group.get("evidence")
        if role not in ROLES:
            raise ValueError("unknown_thermal_boundary_role")
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError("boundary_assignment_evidence_required")
        indices = group.get("face_ids")
        if not isinstance(indices, list) or not indices:
            raise ValueError("nonempty_face_ids_required")
        for index in indices:
            if type(index) is not int or not 1 <= index <= face_count:
                raise ValueError("face_index_out_of_range")
            if index in by_face:
                raise ValueError("overlapping_boundary_assignments")
            by_face[index] = {"role": role, "evidence": evidence}
    return by_face


def summarize(records: list[dict], whole_area: float, source_hash: str) -> dict:
    if not records or not math.isfinite(whole_area) or whole_area <= 0:
        raise ValueError("positive_complete_surface_required")
    areas = [row["area_scan_units_squared"] for row in records]
    if any(not math.isfinite(value) or value <= 0 for value in areas):
        raise ValueError("nonpositive_or_nonfinite_face_area")
    if len({row["face_id"] for row in records}) != len(records):
        raise ValueError("duplicate_inventory_face_id")
    summed_area = math.fsum(areas)
    relative_error = abs(summed_area - whole_area) / whole_area
    if relative_error > 1e-8:
        raise ValueError("face_area_sum_does_not_match_whole_surface")
    assigned = [row for row in records if row["thermal_role"] is not None]
    return {
        "schema": "m64-thermal-boundary-inventory-summary/v1",
        "source_sha256": source_hash,
        "classification": "private_reference_geometry_preprocessing_not_M64_fitment",
        "face_count": len(records),
        "surface_type_counts": dict(sorted(Counter(row["surface_type"] for row in records).items())),
        "surface_area_scan_units_squared": summed_area,
        "whole_shape_surface_area_scan_units_squared": whole_area,
        "face_area_sum_relative_error": relative_error,
        "assigned_face_count": len(assigned),
        "unassigned_face_count": len(records) - len(assigned),
        "assigned_surface_area_fraction": math.fsum(row["area_scan_units_squared"] for row in assigned) / summed_area,
        "role_counts": dict(sorted(Counter(row["thermal_role"] for row in assigned).items())),
        "boundary_partition_complete": len(assigned) == len(records),
        "absolute_scale_certified": False,
        "geometry_modified": False,
        "material_assigned": False,
        "cht_case_generated": False,
        "cht_solved": False,
        "manufacturing_authorized": False,
    }


def inventory(args) -> dict:
    source_hash = sha256(args.input)
    if source_hash != args.sha256:
        raise ValueError("STEP_source_hash_mismatch")
    if args.output.exists():
        raise FileExistsError(args.output)
    sys.path.insert(0, str(args.helpers))
    from audit_brep_f42 import read_step, indexed_shapes, bbox
    import OCP
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SOLID
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
    from OCP.TopoDS import TopoDS

    shape, roots = read_step(args.input)
    if roots != 1 or indexed_shapes(shape, TopAbs_SOLID).Extent() != 1:
        raise ValueError("single_root_single_solid_required")
    faces = indexed_shapes(shape, TopAbs_FACE)
    mapping = json.loads(args.assignments.read_text()) if args.assignments else None
    by_face = validate_assignments(mapping, source_hash, faces.Extent(), OCP.__version__)
    neighbors = {index: set() for index in range(1, faces.Extent() + 1)}
    ancestors = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndUniqueAncestors_s(shape, TopAbs_EDGE, TopAbs_FACE, ancestors)
    for edge_index in range(1, ancestors.Extent() + 1):
        indices = [faces.FindIndex(face) for face in ancestors.FindFromIndex(edge_index)]
        for index in indices:
            neighbors[index].update(set(indices) - {index})
    records = []
    for index in range(1, faces.Extent() + 1):
        face = TopoDS.Face_s(faces.FindKey(index))
        properties = GProp_GProps()
        BRepGProp.SurfaceProperties_s(face, properties)
        records.append({
            "face_id": index,
            "surface_type": str(BRepAdaptor_Surface(face).GetType()).split(".")[-1],
            "area_scan_units_squared": float(properties.Mass()),
            "centroid_scan_units": list(properties.CentreOfMass().Coord()),
            "bbox_scan_units": bbox(face),
            "adjacent_face_ids": sorted(neighbors[index]),
            "thermal_role": by_face.get(index, {}).get("role"),
            "assignment_evidence": by_face.get(index, {}).get("evidence"),
        })
    global_properties = GProp_GProps()
    BRepGProp.SurfaceProperties_s(shape, global_properties)
    summary = summarize(records, float(global_properties.Mass()), source_hash)
    summary["ocp_version"] = OCP.__version__
    private = {"source_sha256": source_hash, "ocp_version": OCP.__version__,
               "face_id_method": "TopExp.MapShapes FACE, one-based, exact imported shape",
               "physical_length_unit": None, "faces": records}
    args.output.mkdir(parents=True, exist_ok=False)
    private_path = args.output / "private-face-inventory.json"
    private_path.write_text(json.dumps(private, indent=2) + "\n")
    summary["private_inventory_sha256"] = sha256(private_path)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--helpers", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--assignments", type=Path)
    args = parser.parse_args()
    print(json.dumps(inventory(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
