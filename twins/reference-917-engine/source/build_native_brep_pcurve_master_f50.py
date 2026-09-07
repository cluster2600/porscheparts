#!/usr/bin/env python3
"""Private F50 native-OCCT p-curve repair and round-trip audit.

This is deliberately not a STEP release path.  It reprojects only p-curves on
the existing B-Rep topology, shares all 3D curves and surfaces, then serializes
the clean candidate in OCCT's native ``.brep`` representation.  The native
round trip is audited before it may be used as a CAE meshing master.  A STEP
interoperability gate remains independent and fail-closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-step", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output-brep", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    parser.add_argument("--helper-dir", type=Path, required=True)
    args = parser.parse_args()
    if sha256(args.input_step) != args.expected_sha256:
        raise RuntimeError("input_SHA256_mismatch")

    sys.path.insert(0, str(args.helper_dir))
    from audit_brep_f42 import brepcheck, read_step, shape_properties, topology
    from repair_pcurves_f42_2 import make_trial
    from repair_topology_f42_1 import full_bop_map, property_delta, shared_geometry_audit

    original, roots = read_step(args.input_step)
    candidate, repair = make_trial(original, None, 2.0e-2)
    pre_export_bop = full_bop_map(candidate)
    if pre_export_bop["result_count"] != 0:
        raise RuntimeError("pre_export_BOP_not_zero")

    args.output_brep.parent.mkdir(parents=True, exist_ok=True)
    if not BRepTools.Write_s(candidate, str(args.output_brep)):
        raise RuntimeError("native_BREP_write_failed")

    roundtrip = TopoDS_Shape()
    builder = BRep_Builder()
    if not BRepTools.Read_s(roundtrip, str(args.output_brep), builder):
        raise RuntimeError("native_BREP_read_failed")
    native_bop = full_bop_map(roundtrip)
    native_check = brepcheck(roundtrip)
    native_topology = topology(roundtrip)
    original_properties = shape_properties(original)
    roundtrip_properties = shape_properties(roundtrip)
    geometry = shared_geometry_audit(original, candidate)
    delta = property_delta(original_properties, roundtrip_properties)
    edge_classes = native_topology["edge_classification"]
    accepted = (
        geometry["all_3D_surfaces_identical"]
        and geometry["all_3D_curves_identical_or_both_null"]
        and native_bop["result_count"] == 0
        and native_check["shape_valid"]
        and native_topology["unique_subshape_counts"]["solid"] == 1
        and native_topology["unique_subshape_counts"]["shell"] == 1
        and edge_classes["free_edges"] == 0
        and edge_classes["nonmanifold_edges"] == 0
        and delta["maximum_bbox_coordinate_delta_scan_units"] <= 1.0e-9
    )
    report = {
        "schema": "porsche-917-f50-private-native-brep-master/v1",
        "input": {"sha256": args.expected_sha256, "roots": roots},
        "operations": {
            "pcurve_reprojection_only": True,
            "shared_3D_geometry": geometry,
            "surface_or_curve_deformation_used": False,
            "sewing_used": False,
            "faceting_used": False,
            "global_ellipse_used": False,
            "global_oval_used": False,
            "global_box_used": False,
        },
        "pre_export_BOPAlgo": pre_export_bop,
        "repair": repair,
        "native_master": {
            "filename": args.output_brep.name,
            "sha256": sha256(args.output_brep),
            "bytes": args.output_brep.stat().st_size,
            "roundtrip_BOPAlgo": native_bop,
            "roundtrip_BRepCheck": native_check,
            "roundtrip_topology": native_topology,
            "property_delta_from_input": delta,
            "accepted_as_private_CAD_CAE_master": accepted,
        },
        "STEP_interoperability_gate": {
            "accepted": False,
            "status": "must_be_tested_separately_after_native_master",
        },
        "release": {
            "manufacturing_authorized": False,
            "engine_start_authorized": False,
        },
    }
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "accepted_as_private_CAD_CAE_master": accepted,
                "native_BOP_faults": native_bop["result_count"],
                "native_BRepCheck_valid": native_check["shape_valid"],
                "solid_count": native_topology["unique_subshape_counts"]["solid"],
                "shell_count": native_topology["unique_subshape_counts"]["shell"],
                "free_edges": edge_classes["free_edges"],
                "nonmanifold_edges": edge_classes["nonmanifold_edges"],
                "maximum_bbox_delta": delta["maximum_bbox_coordinate_delta_scan_units"],
            },
            sort_keys=True,
        )
    )
    return 0 if accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
