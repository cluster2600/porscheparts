#!/usr/bin/env python3
"""Generate a fail-closed F13 interface master from detected 917 scan openings.

The generated geometry is deliberately limited to measured opening markers,
axes and datums.  It is a fit-check/layout aid, never manufacturing geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INTERFACES = REPO_ROOT / "work/917-engine/vast-output/reports/interfaces.json"
DEFAULT_SOURCE_CONTRACT = (
    REPO_ROOT / "twins/reference-917-engine/source-scan-integrity-f11.json"
)
DEFAULT_ENGINEERING_CONTRACT = (
    REPO_ROOT / "twins/reference-917-engine/reengineering-contract-f11.json"
)
DEFAULT_REFERENCE_CONTRACT = REPO_ROOT / "twins/reference-917-engine/complete-engine-f1.json"
DEFAULT_AMS_SOURCE = REPO_ROOT / "catalog/sources/src-ams-917-engine-technical-analysis.json"
DEFAULT_OUTPUT = REPO_ROOT / "work/917-parametric-interface-f13"


class InputError(ValueError):
    """Raised when an upstream report cannot support an F13 layout master."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InputError(f"missing input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError(f"expected a JSON object in {path}")
    return data


def number(value: Any, pointer: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{pointer} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise InputError(f"{pointer} must be a finite number")
    return result


def vector(value: Any, length: int, pointer: str) -> list[float]:
    if not isinstance(value, list) or len(value) != length:
        raise InputError(f"{pointer} must contain {length} numbers")
    return [number(item, f"{pointer}/{index}") for index, item in enumerate(value)]


def measured(value: Any, unit: str, source_pointer: str, method: str) -> dict[str, Any]:
    return {
        "value": value,
        "unit": unit,
        "classification": "measured_from_scan_obj_units",
        "provenance": {
            "source": "detected_interface_report",
            "json_pointer": source_pointer,
            "method": method,
        },
    }


def published_candidate(
    value: float,
    unit: str,
    field: str,
    source_ids: list[str],
    *,
    source: str = "complete-engine-f1.json",
    json_pointer: str | None = None,
) -> dict[str, Any]:
    return {
        "value": value,
        "unit": unit,
        "classification": "published_reference_candidate",
        "provenance": {
            "source": source,
            "json_pointer": json_pointer or f"/declared_dimensions/{field}",
            "source_ids": source_ids,
            "warning": (
                "The aggregate contract does not isolate a factory drawing for this field; "
                "the value is not used to scale the scan."
            ),
        },
    }


def validate_contracts(
    interfaces: dict[str, Any],
    source_contract: dict[str, Any],
    engineering_contract: dict[str, Any],
    reference_contract: dict[str, Any],
    ams_source: dict[str, Any],
) -> None:
    if interfaces.get("status") != "F1_detected_exterior_interfaces":
        raise InputError("interfaces report is not F1_detected_exterior_interfaces")
    units = interfaces.get("units")
    if not isinstance(units, str) or "unconfirmed" not in units.lower():
        raise InputError("interfaces report must keep OBJ units explicitly unconfirmed")

    artifacts = source_contract.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 1:
        raise InputError("source contract must identify exactly one raw scan artifact")
    source_sha = artifacts[0].get("sha256")
    engineering_sha = engineering_contract.get("asset", {}).get("source_scan_sha256")
    if not isinstance(source_sha, str) or source_sha != engineering_sha:
        raise InputError("source and engineering contracts disagree on the scan SHA-256")
    if engineering_contract.get("asset", {}).get("current_verified_level") != "F0_source_integrity":
        raise InputError("engineering contract must remain at F0_source_integrity")
    if engineering_contract.get("release_authority", {}).get("manufacturing_release_enabled") is not False:
        raise InputError("manufacturing release must remain disabled")

    source_ids = reference_contract.get("source_ids")
    if not isinstance(source_ids, list) or not source_ids:
        raise InputError("reference contract must list source_ids")
    dimensions = reference_contract.get("declared_dimensions")
    if not isinstance(dimensions, dict):
        raise InputError("reference contract must provide declared_dimensions")
    for name in ("bore_mm", "cylinder_regular_pitch_mm", "central_pair_pitch_mm"):
        number(dimensions.get(name), f"/declared_dimensions/{name}")
    if ams_source.get("source_id") != "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS":
        raise InputError("unexpected source record for the 5.0 L reference candidate")


def cylinder_records(interfaces: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for bank_name, sign, prefix in (("positive", 1, "P"), ("negative", -1, "N")):
        bank = interfaces.get("banks", {}).get(bank_name)
        if not isinstance(bank, list) or len(bank) != 6:
            raise InputError(f"/banks/{bank_name} must contain exactly six openings")
        for index, opening in enumerate(bank):
            pointer = f"/banks/{bank_name}/{index}"
            if not isinstance(opening, dict):
                raise InputError(f"{pointer} must be an object")
            centre_lv = vector(
                opening.get("center_longitudinal_vertical"),
                2,
                f"{pointer}/center_longitudinal_vertical",
            )
            rim_depth = number(
                opening.get("rim_outward_depth_mode_obj_units"),
                f"{pointer}/rim_outward_depth_mode_obj_units",
            )
            diameter = number(
                opening.get("diameter_obj_units"), f"{pointer}/diameter_obj_units"
            )
            if diameter <= 0 or rim_depth <= 0:
                raise InputError(f"{pointer} diameter and outward depth must be positive")
            scan_centre = vector(
                opening.get("center_scan_coordinates"),
                3,
                f"{pointer}/center_scan_coordinates",
            )
            scan_axis = vector(
                opening.get("axis_scan_coordinates"),
                3,
                f"{pointer}/axis_scan_coordinates",
            )
            axis_norm = math.sqrt(sum(item * item for item in scan_axis))
            if not math.isclose(axis_norm, 1.0, rel_tol=0.0, abs_tol=1e-5):
                raise InputError(f"{pointer}/axis_scan_coordinates is not unit length")

            layout_centre = [centre_lv[0], sign * rim_depth, centre_lv[1]]
            result.append(
                {
                    "id": f"CYL-{prefix}{index + 1}",
                    "bank": bank_name,
                    "bank_index": index + 1,
                    "interface_role": (
                        "visible_opening_and_axis_marker_for_case_cylinder_head_fit_check"
                    ),
                    "layout_center": measured(
                        layout_centre,
                        "OBJ_unit",
                        pointer,
                        (
                            "X and Z from fitted circle center; Y from signed modal outward rim "
                            "depth. This is a visible rim marker, not a machined datum."
                        ),
                    ),
                    "scan_center": measured(
                        scan_centre,
                        "OBJ_unit",
                        f"{pointer}/center_scan_coordinates",
                        "Back-transform of the detected opening center into scan coordinates.",
                    ),
                    "scan_axis": {
                        "value": scan_axis,
                        "unit": "unit_vector",
                        "classification": "measured_from_scan_obj_units",
                        "provenance": {
                            "source": "detected_interface_report",
                            "json_pointer": f"{pointer}/axis_scan_coordinates",
                            "method": "PCA bank-axis direction; not a metrology-certified bore axis.",
                        },
                    },
                    "visible_opening_diameter": measured(
                        diameter,
                        "OBJ_unit",
                        f"{pointer}/diameter_obj_units",
                        "Hough detection followed by a RANSAC circle fit on the visible opening.",
                    ),
                    "circle_fit_p95": measured(
                        number(
                            opening.get("circle_fit_p95_obj_units"),
                            f"{pointer}/circle_fit_p95_obj_units",
                        ),
                        "OBJ_unit",
                        f"{pointer}/circle_fit_p95_obj_units",
                        "95th percentile absolute residual of the detected ring fit.",
                    ),
                    "released_interfaces": [],
                }
            )
    return result


def pitch_records(interfaces: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for bank_name in ("positive", "negative"):
        pointer = f"/pitch/{bank_name}"
        source = interfaces.get("pitch", {}).get(bank_name)
        if not isinstance(source, dict):
            raise InputError(f"{pointer} must be an object")
        gaps = vector(
            source.get("successive_longitudinal_gaps_obj_units"),
            5,
            f"{pointer}/successive_longitudinal_gaps_obj_units",
        )
        split_after = source.get("central_split_after_cylinder")
        if split_after != 3:
            raise InputError(f"{pointer}/central_split_after_cylinder must be 3")
        result[bank_name] = {
            "successive_gaps": measured(
                gaps,
                "OBJ_unit",
                f"{pointer}/successive_longitudinal_gaps_obj_units",
                "Successive X differences between fitted opening centers.",
            ),
            "median_regular_pitch": measured(
                number(
                    source.get("median_regular_pitch_obj_units"),
                    f"{pointer}/median_regular_pitch_obj_units",
                ),
                "OBJ_unit",
                f"{pointer}/median_regular_pitch_obj_units",
                "Median after excluding the largest central gap.",
            ),
            "central_gap": measured(
                number(
                    source.get("central_split_gap_obj_units"),
                    f"{pointer}/central_split_gap_obj_units",
                ),
                "OBJ_unit",
                f"{pointer}/central_split_gap_obj_units",
                "Largest successive X gap; it does not prove a physical crankcase split face.",
            ),
            "central_split_after_cylinder": 3,
        }
    return result


def build_spec(
    interfaces: dict[str, Any],
    source_contract: dict[str, Any],
    engineering_contract: dict[str, Any],
    reference_contract: dict[str, Any],
    ams_source: dict[str, Any],
    paths: dict[str, Path],
) -> dict[str, Any]:
    validate_contracts(
        interfaces,
        source_contract,
        engineering_contract,
        reference_contract,
        ams_source,
    )
    cylinders = cylinder_records(interfaces)
    pitch = pitch_records(interfaces)

    positive_x = [item["layout_center"]["value"][0] for item in cylinders[:6]]
    negative_x = [item["layout_center"]["value"][0] for item in cylinders[6:]]
    row_mid_gaps = {
        "positive": (positive_x[2] + positive_x[3]) / 2.0,
        "negative": (negative_x[2] + negative_x[3]) / 2.0,
    }
    central_x = (row_mid_gaps["positive"] + row_mid_gaps["negative"]) / 2.0
    frame = interfaces.get("frame_rows_longitudinal_bank_axis_vertical")
    if not isinstance(frame, list) or len(frame) != 3:
        raise InputError("/frame_rows_longitudinal_bank_axis_vertical must have three rows")
    frame_rows = [vector(row, 3, f"/frame_rows_longitudinal_bank_axis_vertical/{i}") for i, row in enumerate(frame)]

    dimensions = reference_contract["declared_dimensions"]
    source_ids = [str(item) for item in reference_contract["source_ids"]]
    source_artifact = source_contract["artifacts"][0]
    observed_opening_mean = number(
        interfaces.get("mean_visible_opening_diameter_obj_units"),
        "/mean_visible_opening_diameter_obj_units",
    )
    recomputed_opening_mean = sum(
        item["visible_opening_diameter"]["value"] for item in cylinders
    ) / len(cylinders)
    if not math.isclose(observed_opening_mean, recomputed_opening_mean, abs_tol=1e-9):
        raise InputError("reported and recomputed mean visible opening diameters disagree")
    regular_gaps = []
    for bank in ("positive", "negative"):
        gaps = pitch[bank]["successive_gaps"]["value"]
        regular_gaps.extend(gap for index, gap in enumerate(gaps) if index != 2)
    observed_regular_pitch_mean = sum(regular_gaps) / len(regular_gaps)

    bore_candidates = {
        "type_912_4_5_na": published_candidate(
            number(dimensions["bore_mm"], "/declared_dimensions/bore_mm"),
            "mm",
            "bore_mm",
            source_ids,
        ),
        "917_5_0_na_4999": published_candidate(
            86.8,
            "mm",
            "bore_mm",
            ["SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS"],
            source="catalog/sources/src-ams-917-engine-technical-analysis.json",
            json_pointer="/notes (textual 86.8 x 70.4 mm declaration)",
        ),
        "917_30_turbo_5374": published_candidate(
            number(
                engineering_contract["engine_variants"][1]["documented_dimensions"]["bore_mm"],
                "/engine_variants/1/documented_dimensions/bore_mm",
            ),
            "mm",
            "bore_mm",
            engineering_contract["engine_variants"][1]["source_ids"],
            source="reengineering-contract-f11.json",
            json_pointer="/engine_variants/1/documented_dimensions/bore_mm",
        ),
    }
    scale_hypotheses = []
    for variant_id, bore in bore_candidates.items():
        mm_per_obj_unit = bore["value"] / observed_opening_mean
        implied_pitch_mm = observed_regular_pitch_mean * mm_per_obj_unit
        delta_vs_reference_percent = (
            (implied_pitch_mm / dimensions["cylinder_regular_pitch_mm"]) - 1.0
        ) * 100.0
        scale_hypotheses.append(
            {
                "variant_id": variant_id,
                "status": "hypothesis_candidate_not_identity_or_scale_release",
                "assumption": "visible scan opening diameter equals the published bore",
                "published_bore": bore,
                "candidate_mm_per_obj_unit": {
                    "value": mm_per_obj_unit,
                    "unit": "mm/OBJ_unit",
                    "classification": "derived_hypothesis_not_measurement",
                    "provenance": {
                        "formula": "published bore mm / measured mean visible opening OBJ units",
                        "inputs": [
                            "published_reference_candidate",
                            "measured_from_scan_obj_units",
                        ],
                    },
                },
                "implied_regular_pitch": {
                    "value": implied_pitch_mm,
                    "unit": "mm",
                    "classification": "derived_hypothesis_not_measurement",
                    "provenance": {
                        "formula": "measured mean regular pitch OBJ units * candidate mm/OBJ_unit",
                        "comparison_reference": "published 118 mm regular pitch candidate",
                    },
                },
                "pitch_delta_vs_118_percent": delta_vs_reference_percent,
                "identity_released": False,
                "scale_released": False,
            }
        )
    return {
        "schema_version": "1.0.0",
        "phase": "F13",
        "status": "provisional_interface_master_fit_check_only",
        "asset_id": "porsche-917-case-cylinder-head-interface-master-f13",
        "classification": "layout_reference_not_manufacturing_geometry",
        "units": {
            "native": "OBJ_unit",
            "unit_status": "unconfirmed",
            "mm_per_obj_unit": None,
            "rule": "No conversion to millimetres is permitted until F1 identity and scale controls pass.",
        },
        "source_contracts": [
            {
                "role": "detected_interface_report",
                "path": str(paths["interfaces"]),
                "status": interfaces["status"],
                "sha256": file_sha256(paths["interfaces"]),
            },
            {
                "role": "raw_scan_integrity",
                "path": str(paths["source_contract"]),
                "evidence_id": source_contract.get("evidence_id"),
                "raw_scan_sha256": source_artifact["sha256"],
            },
            {
                "role": "fail_closed_engineering_contract",
                "path": str(paths["engineering_contract"]),
                "verified_level": engineering_contract["asset"]["current_verified_level"],
            },
            {
                "role": "published_reference_candidates",
                "path": str(paths["reference_contract"]),
                "source_ids": source_ids,
            },
            {
                "role": "published_5_0_l_reference_candidate",
                "path": str(paths["ams_source"]),
                "source_ids": [ams_source["source_id"]],
            },
        ],
        "coordinate_system": {
            "canonical_local": "X=detected longitudinal, Y=opposed bank axis, Z=detected vertical",
            "scan_centroid": measured(
                vector(interfaces.get("centroid_scan_coordinates"), 3, "/centroid_scan_coordinates"),
                "OBJ_unit",
                "/centroid_scan_coordinates",
                "Centroid of the source mesh used for the PCA frame.",
            ),
            "frame_rows": {
                "value": frame_rows,
                "unit": "unit_vector",
                "classification": "measured_from_scan_obj_units",
                "provenance": {
                    "source": "detected_interface_report",
                    "json_pointer": "/frame_rows_longitudinal_bank_axis_vertical",
                    "method": "PCA basis with deterministic signs; not a factory datum system.",
                },
            },
        },
        "datums": [
            {
                "id": "D-SCAN-ORIGIN",
                "type": "point",
                "definition": "source mesh centroid",
                "value": measured(
                    vector(interfaces.get("centroid_scan_coordinates"), 3, "/centroid_scan_coordinates"),
                    "OBJ_unit",
                    "/centroid_scan_coordinates",
                    "Centroid of the source mesh.",
                ),
                "manufacturing_datum": False,
            },
            {
                "id": "D-LONGITUDINAL",
                "type": "axis",
                "definition": "first PCA frame row",
                "value": {
                    "value": frame_rows[0],
                    "unit": "unit_vector",
                    "classification": "measured_from_scan_obj_units",
                    "provenance": {
                        "source": "detected_interface_report",
                        "json_pointer": "/frame_rows_longitudinal_bank_axis_vertical/0",
                    },
                },
                "manufacturing_datum": False,
            },
            {
                "id": "D-BANK",
                "type": "axis",
                "definition": "second PCA frame row",
                "value": {
                    "value": frame_rows[1],
                    "unit": "unit_vector",
                    "classification": "measured_from_scan_obj_units",
                    "provenance": {
                        "source": "detected_interface_report",
                        "json_pointer": "/frame_rows_longitudinal_bank_axis_vertical/1",
                    },
                },
                "manufacturing_datum": False,
            },
            {
                "id": "D-VERTICAL",
                "type": "axis",
                "definition": "third PCA frame row",
                "value": {
                    "value": frame_rows[2],
                    "unit": "unit_vector",
                    "classification": "measured_from_scan_obj_units",
                    "provenance": {
                        "source": "detected_interface_report",
                        "json_pointer": "/frame_rows_longitudinal_bank_axis_vertical/2",
                    },
                },
                "manufacturing_datum": False,
            },
            {
                "id": "D-CENTRAL-MID-GAP",
                "type": "plane_normal_to_local_X",
                "definition": (
                    "mean of the two row midpoints between detected openings 3 and 4; "
                    "layout datum only, not a verified crankcase split face"
                ),
                "x": measured(
                    central_x,
                    "OBJ_unit",
                    "/banks/*/2-3/center_longitudinal_vertical",
                    "Arithmetic mean of the positive and negative row mid-gap X positions.",
                ),
                "row_mid_gap_x": {
                    bank: measured(
                        value,
                        "OBJ_unit",
                        f"/banks/{bank}/2-3/center_longitudinal_vertical",
                        "Midpoint between detected opening centers 3 and 4.",
                    )
                    for bank, value in row_mid_gaps.items()
                },
                "manufacturing_datum": False,
            },
        ],
        "banks": [
            {
                "id": "BANK-POSITIVE",
                "axis_local": [0, 1, 0],
                "cylinder_ids": [item["id"] for item in cylinders[:6]],
            },
            {
                "id": "BANK-NEGATIVE",
                "axis_local": [0, -1, 0],
                "cylinder_ids": [item["id"] for item in cylinders[6:]],
            },
        ],
        "cylinder_interfaces": cylinders,
        "detected_pitch": pitch,
        "published_reference_candidates": {
            "variant_bores": bore_candidates,
            "regular_cylinder_pitch": published_candidate(
                number(
                    dimensions["cylinder_regular_pitch_mm"],
                    "/declared_dimensions/cylinder_regular_pitch_mm",
                ),
                "mm",
                "cylinder_regular_pitch_mm",
                source_ids,
            ),
            "central_pair_pitch": published_candidate(
                number(
                    dimensions["central_pair_pitch_mm"],
                    "/declared_dimensions/central_pair_pitch_mm",
                ),
                "mm",
                "central_pair_pitch_mm",
                source_ids,
            ),
        },
        "scan_to_published_scale_hypotheses": {
            "status": "comparison_only_no_scale_or_identity_release",
            "mean_visible_opening": measured(
                observed_opening_mean,
                "OBJ_unit",
                "/mean_visible_opening_diameter_obj_units",
                "Mean of the twelve fitted visible opening diameters.",
            ),
            "mean_regular_pitch": measured(
                observed_regular_pitch_mean,
                "OBJ_unit",
                "/pitch/*/successive_longitudinal_gaps_obj_units excluding central gaps",
                "Arithmetic mean of the eight non-central successive opening gaps.",
            ),
            "candidates": scale_hypotheses,
            "decision": None,
            "reason": (
                "The 5.0 L candidate is numerically closest, but a circular visible opening "
                "has not been proven to be the finished bore and no physical scale control exists."
            ),
        },
        "component_interface_scope": {
            "crankcase": "central layout plane and frame only; no crankcase solid or split face",
            "individual_cylinder": "visible opening marker and detected axis only; no barrel, fins, registers or bore",
            "individual_head": "coaxial placement reference only; the source scan contains no head geometry",
        },
        "stud_locations": [],
        "stud_status": "not_detected_not_generated",
        "release_gates": {
            "metric_scale_confirmed": False,
            "identity_confirmed": False,
            "machined_datums_confirmed": False,
            "head_geometry_present": False,
            "stud_pattern_measured": False,
            "tolerances_defined": False,
            "functional_release": False,
            "print_release": False,
            "metal_print_release": False,
        },
        "prohibited_uses": [
            "conversion of OBJ units to millimetres",
            "functional manufacture or any metal print",
            "machining, tolerance, sealing, fastener or combustion decisions",
            "claim that a visible opening is a certified cylinder bore",
            "PhysicsNeMo or classical solver training data without qualified geometry and loads",
        ],
        "next_required_measurements": [
            "three independent physical scale controls with uncertainty",
            "crankcase split and cylinder-register datums",
            "cylinder base, head joint and register geometry",
            "stud count, centers, diameters, threads and clamp path",
            "one variant-specific cylinder and head by calibrated metrology or CT",
            "fit, clearance, surface, material and thermal-load specifications",
        ],
    }


def render_scad(spec: dict[str, Any]) -> str:
    rows = []
    for item in spec["cylinder_interfaces"]:
        center = ", ".join(f"{value:.9f}" for value in item["layout_center"]["value"])
        diameter = item["visible_opening_diameter"]["value"]
        sign = 1 if item["bank"] == "positive" else -1
        rows.append(f'    ["{item["id"]}", [{center}], {diameter:.9f}, {sign}]')
    cylinder_rows = ",\n".join(rows)
    central_x = next(datum for datum in spec["datums"] if datum["id"] == "D-CENTRAL-MID-GAP")["x"]["value"]
    centers = [item["layout_center"]["value"] for item in spec["cylinder_interfaces"]]
    mean_diameter = sum(
        item["visible_opening_diameter"]["value"] for item in spec["cylinder_interfaces"]
    ) / len(centers)
    y_span = max(item[1] for item in centers) - min(item[1] for item in centers) + mean_diameter
    z_span = max(item[2] for item in centers) - min(item[2] for item in centers) + mean_diameter
    return f'''/*
GENERATED F13 917 CASE-CYLINDER-HEAD INTERFACE MASTER
FIT-CHECK / LAYOUT ONLY. OBJ SCALE IS UNCONFIRMED.
NO FUNCTIONAL, PRINT OR METAL-PRINT RELEASE.
Stud locations are absent because none were detected or measured.
*/

$fn = 96;
MM_PER_OBJ_UNIT = undef;
FABRICATION_RELEASED = false;
CENTRAL_MID_GAP_X = {central_x:.9f};
MEAN_VISIBLE_OPENING = {mean_diameter:.9f};
DISPLAY_PLANE_Y_SPAN = {y_span:.9f};
DISPLAY_PLANE_Z_SPAN = {z_span:.9f};

// Each row: [id, measured visible-rim center in OBJ units, measured diameter, bank sign].
CYLINDER_INTERFACES = [
{cylinder_rows}
];

// These dimensions are visualization parameters derived from the measured diameter.
// They are not engine dimensions and must never be dimensioned from the output solid.
function marker_thickness(d) = d * 0.015;
function axis_length(d) = d * 1.20;
function axis_diameter(d) = d * 0.010;

module observed_opening_marker(center, diameter, bank_sign) {{
    color(bank_sign > 0 ? [0.85, 0.25, 0.15, 0.55] : [0.15, 0.40, 0.90, 0.55])
        translate(center)
            rotate([90, 0, 0])
                cylinder(d=diameter, h=marker_thickness(diameter), center=true);
}}

module detected_axis_marker(center, diameter) {{
    color([0.95, 0.85, 0.15, 0.85])
        translate(center)
            rotate([90, 0, 0])
                cylinder(d=axis_diameter(diameter), h=axis_length(diameter), center=true);
}}

module central_mid_gap_layout_plane() {{
    // Display surface only: it is not a detected or machined crankcase split face.
    color([0.2, 0.9, 0.6, 0.20])
        translate([CENTRAL_MID_GAP_X, 0, 0])
            cube([MEAN_VISIBLE_OPENING * 0.01, DISPLAY_PLANE_Y_SPAN, DISPLAY_PLANE_Z_SPAN], center=true);
}}

central_mid_gap_layout_plane();
for (interface = CYLINDER_INTERFACES) {{
    observed_opening_marker(interface[1], interface[2], interface[3]);
    detected_axis_marker(interface[1], interface[2]);
}}
'''


def render_build123d(spec_filename: str) -> str:
    return f'''#!/usr/bin/env python3
"""Generated F13 STEP exporter: fit-check/layout only, never fabrication."""

from __future__ import annotations

import json
import os
from pathlib import Path

from build123d import Align, Box, Compound, Cylinder, Pos, export_step


HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE / "{spec_filename}").read_text(encoding="utf-8"))
if SPEC["units"]["mm_per_obj_unit"] is not None:
    raise RuntimeError("F13 refuses a metric conversion until the source-scale gate is qualified")
if any(SPEC["release_gates"][key] for key in ("functional_release", "print_release", "metal_print_release")):
    raise RuntimeError("F13 release gates must remain false")
if SPEC["stud_locations"]:
    raise RuntimeError("F13 has no measured stud detector; refusing stud geometry")
if os.environ.get("F13_ALLOW_UNSCALED_STEP") != "fit-check-only":
    raise RuntimeError(
        "Refusing implicit OBJ-to-STEP kernel-unit mapping; set "
        "F13_ALLOW_UNSCALED_STEP=fit-check-only only for an explicitly quarantined layout review"
    )


def marker(center, diameter, bank_sign):
    thickness = diameter * 0.015  # visualization-only ratio
    rotation = (-90.0 * bank_sign, 0.0, 0.0)
    return Pos(*center) * Cylinder(
        diameter / 2.0,
        thickness,
        rotation=rotation,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )


def axis_marker(center, diameter, bank_sign):
    length = diameter * 1.20  # visualization-only ratio
    rotation = (-90.0 * bank_sign, 0.0, 0.0)
    return Pos(*center) * Cylinder(
        diameter * 0.005,
        length,
        rotation=rotation,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )


children = []
for item in SPEC["cylinder_interfaces"]:
    center = item["layout_center"]["value"]
    diameter = item["visible_opening_diameter"]["value"]
    bank_sign = 1 if item["bank"] == "positive" else -1
    children.append(marker(center, diameter, bank_sign))
    children.append(axis_marker(center, diameter, bank_sign))

central = next(item for item in SPEC["datums"] if item["id"] == "D-CENTRAL-MID-GAP")
centers = [item["layout_center"]["value"] for item in SPEC["cylinder_interfaces"]]
mean_diameter = sum(item["visible_opening_diameter"]["value"] for item in SPEC["cylinder_interfaces"]) / len(centers)
y_span = max(item[1] for item in centers) - min(item[1] for item in centers) + mean_diameter
z_span = max(item[2] for item in centers) - min(item[2] for item in centers) + mean_diameter
children.append(
    Pos(central["x"]["value"], 0.0, (max(item[2] for item in centers) + min(item[2] for item in centers)) / 2.0)
    * Box(mean_diameter * 0.01, y_span, z_span, align=Align.CENTER)
)

assembly = Compound(children=children, label="917 F13 FIT-CHECK ONLY - OBJ SCALE UNCONFIRMED")
output = HERE / "917-engine-interface-master-f13-fit-check-only.step"
export_step(assembly, output)
(HERE / "step-export-report.json").write_text(
    json.dumps(
        {{
            "status": "fit_check_step_generated",
            "output": str(output),
            "native_units": "OBJ_unit",
            "unit_status": "unconfirmed",
            "step_kernel_unit": "mm",
            "coordinate_mapping": (
                "1 OBJ numeric unit is written as 1 STEP kernel millimetre for quarantined "
                "visualization transport only; this is not a physical scale conversion"
            ),
            "physical_mm_conversion_released": False,
            "fabrication_released": False,
            "solid_count": len(children),
            "stud_count": 0,
        }},
        indent=2,
    )
    + "\\n",
    encoding="utf-8",
)
print(output)
'''


def write_outputs(spec: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    spec_path = output_dir / "917-engine-interface-master-f13.spec.json"
    scad_path = output_dir / "917-engine-interface-master-f13.scad"
    build123d_path = output_dir / "917-engine-interface-master-f13-build123d.py"
    report_path = output_dir / "generation-report.json"

    spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    scad_path.write_text(render_scad(spec), encoding="utf-8")
    build123d_path.write_text(render_build123d(spec_path.name), encoding="utf-8")
    build123d_path.chmod(0o755)

    report = {
        "status": "generated_fit_check_only",
        "phase": "F13",
        "outputs": {
            "spec": str(spec_path),
            "openscad": str(scad_path),
            "build123d_step_exporter": str(build123d_path),
        },
        "cylinder_interface_count": len(spec["cylinder_interfaces"]),
        "bank_counts": {
            "positive": sum(item["bank"] == "positive" for item in spec["cylinder_interfaces"]),
            "negative": sum(item["bank"] == "negative" for item in spec["cylinder_interfaces"]),
        },
        "stud_count": len(spec["stud_locations"]),
        "unit_status": spec["units"]["unit_status"],
        "fabrication_released": False,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interfaces", type=Path, default=DEFAULT_INTERFACES)
    parser.add_argument("--source-contract", type=Path, default=DEFAULT_SOURCE_CONTRACT)
    parser.add_argument("--engineering-contract", type=Path, default=DEFAULT_ENGINEERING_CONTRACT)
    parser.add_argument("--reference-contract", type=Path, default=DEFAULT_REFERENCE_CONTRACT)
    parser.add_argument("--ams-source", type=Path, default=DEFAULT_AMS_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    paths = {
        "interfaces": args.interfaces,
        "source_contract": args.source_contract,
        "engineering_contract": args.engineering_contract,
        "reference_contract": args.reference_contract,
        "ams_source": args.ams_source,
    }
    spec = build_spec(
        load_json(args.interfaces),
        load_json(args.source_contract),
        load_json(args.engineering_contract),
        load_json(args.reference_contract),
        load_json(args.ams_source),
        paths,
    )
    report = write_outputs(spec, args.output_dir)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
