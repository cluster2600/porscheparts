#!/usr/bin/env python3
"""Compile la comparaison assainie +Y/-Y F42.3 depuis deux tranchages complets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any


EXPECTED_LAYERS = 4122
EXPECTED_THICKNESS_MM = 0.05


class F423Error(RuntimeError):
    """Erreur fail-closed de comparaison F42.3."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise F423Error("report_must_be_object")
    return value


def load_metrics(path: Path) -> list[dict[str, float]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        raw = list(csv.DictReader(stream))
    if len(raw) != EXPECTED_LAYERS:
        raise F423Error(f"expected_{EXPECTED_LAYERS}_rows:{len(raw)}")
    rows: list[dict[str, float]] = []
    for expected, row in enumerate(raw):
        try:
            numeric = {key: float(value) for key, value in row.items()}
        except (TypeError, ValueError) as exc:
            raise F423Error(f"non_numeric_metric:{expected}") from exc
        if int(numeric["layer_index"]) != expected:
            raise F423Error(f"non_contiguous_layer:{expected}")
        if abs(numeric["z_mm"] - (expected + 0.5) * EXPECTED_THICKNESS_MM) > 1.0e-8:
            raise F423Error(f"invalid_z:{expected}")
        if not all(math.isfinite(value) and value >= 0.0 for value in numeric.values()):
            raise F423Error(f"invalid_metric:{expected}")
        rows.append(numeric)
    return rows


def relative_change_percent(candidate: float, reference: float) -> float | None:
    if reference == 0.0:
        return None
    return 100.0 * (candidate - reference) / reference


def summarize(rows: list[dict[str, float]]) -> dict[str, Any]:
    thickness = EXPECTED_THICKNESS_MM
    return {
        "layer_count": len(rows),
        "empty_layer_count": sum(row["part_area_mm2"] <= 0.0 for row in rows),
        "layers_with_new_islands": sum(row["new_island_count"] > 0.0 for row in rows),
        "new_island_count_total": int(sum(row["new_island_count"] for row in rows)),
        "layers_with_unsupported_regions": sum(
            row["unsupported_component_count"] > 0.0 for row in rows
        ),
        "unsupported_area_layer_integral_mm2_layers": sum(
            row["unsupported_area_mm2"] for row in rows
        ),
        "maximum_unsupported_area_one_layer_mm2": max(
            row["unsupported_area_mm2"] for row in rows
        ),
        "support_volume_cm3": sum(
            row["support_cross_section_area_mm2"] * thickness for row in rows
        )
        / 1000.0,
        "support_vertical_side_surface_mm2": sum(
            row["support_cross_section_perimeter_mm"] * thickness for row in rows
        ),
        "first_midplane_part_area_mm2": rows[0]["part_area_mm2"],
        "first_midplane_part_component_count": int(rows[0]["part_component_count"]),
        "first_midplane_support_area_mm2": rows[0]["support_cross_section_area_mm2"],
        "first_1mm_material_volume_mm3": sum(
            row["part_area_mm2"] * thickness for row in rows[:20]
        ),
    }


def validate_slice_report(
    report: dict[str, Any], orientation: str, metrics_path: Path, summary: dict[str, Any]
) -> None:
    slicing = report.get("geometric_slicing", {})
    gates = report.get("gates", {})
    if not slicing.get("executed") or slicing.get("required_layer_count") != EXPECTED_LAYERS:
        raise F423Error(f"incomplete_slice:{orientation}")
    if slicing.get("layer_thickness_mm") != EXPECTED_THICKNESS_MM:
        raise F423Error(f"wrong_layer_thickness:{orientation}")
    if not gates.get("actual_full_layer_slicing_completed"):
        raise F423Error(f"full_slice_gate_closed:{orientation}")
    evaluated = report.get("machine_envelope", {}).get("evaluated_orientation")
    if orientation == "scan_y_down":
        evaluated = evaluated or report.get("machine_envelope", {}).get("locked_orientation")
    if evaluated != orientation:
        raise F423Error(f"orientation_mismatch:{orientation}:{evaluated}")
    if report.get("publication", {}).get("public_layer_metrics_sha256") != sha256(metrics_path):
        raise F423Error(f"metrics_hash_mismatch:{orientation}")
    reported_volume = float(report.get("support_proxy", {}).get("volume_cm3", -1.0))
    if abs(reported_volume - summary["support_volume_cm3"]) > 1.0e-6:
        raise F423Error(f"support_volume_mismatch:{orientation}")


def compile_comparison(
    reference_report_path: Path,
    reference_metrics_path: Path,
    candidate_report_path: Path,
    candidate_metrics_path: Path,
) -> dict[str, Any]:
    reference_report = load_json(reference_report_path)
    candidate_report = load_json(candidate_report_path)
    if reference_report.get("private_input", {}).get("sha256") != candidate_report.get(
        "private_input", {}
    ).get("sha256"):
        raise F423Error("input_geometry_hash_mismatch")
    reference = summarize(load_metrics(reference_metrics_path))
    candidate = summarize(load_metrics(candidate_metrics_path))
    validate_slice_report(reference_report, "scan_y_down", reference_metrics_path, reference)
    validate_slice_report(candidate_report, "scan_y_up", candidate_metrics_path, candidate)

    reference_surface = next(
        item
        for item in reference_report["orientation_screen"]["results"]
        if item["orientation"] == "+Y_locked"
    )
    candidate_surface = next(
        item
        for item in candidate_report["orientation_screen"]["results"]
        if item["orientation"] == "-Y"
    )
    changes = {
        key: relative_change_percent(float(candidate[key]), float(reference[key]))
        for key in (
            "new_island_count_total",
            "unsupported_area_layer_integral_mm2_layers",
            "maximum_unsupported_area_one_layer_mm2",
            "support_volume_cm3",
            "support_vertical_side_surface_mm2",
            "first_midplane_part_area_mm2",
            "first_1mm_material_volume_mm3",
        )
    }
    surface_change = relative_change_percent(
        float(candidate_surface["downward_projected_area_mm2"]),
        float(reference_surface["downward_projected_area_mm2"]),
    )
    numerical_better = bool(
        candidate["empty_layer_count"] <= reference["empty_layer_count"]
        and candidate["new_island_count_total"] <= reference["new_island_count_total"]
        and candidate["unsupported_area_layer_integral_mm2_layers"]
        < reference["unsupported_area_layer_integral_mm2_layers"]
        and candidate["support_volume_cm3"] < reference["support_volume_cm3"]
    )
    envelope_fit = bool(
        candidate_report["machine_envelope"]["nominal_envelope_fit"]
        and reference_report["machine_envelope"]["nominal_envelope_fit"]
    )
    return {
        "schema_version": "1.0.0",
        "phase": "F42.3",
        "title": "Complete +Y versus -Y LPBF geometric orientation comparison",
        "private_input": {
            "sha256": reference_report["private_input"]["sha256"],
            "published": False,
        },
        "common_method": {
            "actual_midplane_slices_per_orientation": EXPECTED_LAYERS,
            "layer_thickness_mm": EXPECTED_THICKNESS_MM,
            "overhang_limit_deg_from_horizontal": 45.0,
            "minimum_reported_feature_area_mm2": 0.01,
            "support_raster_pitch_mm": 0.25,
            "support_method": "same conservative vertical solid-column proxy for both orientations",
        },
        "orientations": {
            "reference_scan_y_down_plus_y": reference,
            "candidate_scan_y_up_minus_y": candidate,
        },
        "comparison_percent_candidate_minus_reference": changes,
        "cardinal_surface_proxy": {
            "reference_plus_y_projected_area_mm2": reference_surface[
                "downward_projected_area_mm2"
            ],
            "candidate_minus_y_projected_area_mm2": candidate_surface[
                "downward_projected_area_mm2"
            ],
            "candidate_change_percent": surface_change,
            "statement": "surface proxy alone cannot select build orientation",
        },
        "machine_envelope": {
            "machine": "BLT-S310",
            "reference_extents_mm": reference_report["machine_envelope"][
                "part_extents_in_locked_build_frame_mm"
            ],
            "candidate_extents_mm": candidate_report["machine_envelope"][
                "part_extents_in_locked_build_frame_mm"
            ],
            "both_nominally_fit": envelope_fit,
            "supplier_placement_reviewed": False,
        },
        "functional_interface_and_build_plate": {
            "build_plate_facing_side_reversed": True,
            "first_midplane_and_first_1mm_metrics_compared": True,
            "functional_interface_semantic_labels_available": False,
            "functional_interface_contact_with_plate_ruled_out": False,
            "machining_allowance_and_protected_surface_plan_reviewed": False,
            "conclusion": "-Y changes the plate-facing side; interface damage and machining access cannot be excluded from the welded surface alone",
        },
        "recoater": {
            "nominal_layer_schedules_complete": True,
            "candidate_collision_clearance_verified": False,
            "candidate_introduces_no_new_risk_verified": False,
            "missing": [
                "calibrated thermo-mechanical distortion field for -Y",
                "blade clearance, stiffness and sweep direction",
                "supplier-optimized -Y supports and placement",
            ],
        },
        "decision": {
            "candidate_numerically_better_on_all_required_geometric_metrics": numerical_better,
            "no_new_interface_or_recoater_risk_demonstrated": False,
            "orientation_change_authorized": False,
            "selected_orientation": "scan_y_down (+Y) retained",
            "reason": "the mandatory no-new-interface/recoater-risk condition is unproven",
        },
        "publication": {
            "contains_private_geometry": False,
            "contains_coordinates_or_contours": False,
            "reference_metrics_sha256": sha256(reference_metrics_path),
            "candidate_metrics_sha256": sha256(candidate_metrics_path),
        },
        "gates": {
            "both_actual_4122_layer_slices_completed": True,
            "both_nominal_machine_envelopes_fit": envelope_fit,
            "functional_interfaces_reviewed_for_candidate": False,
            "candidate_recoater_clearance_verified": False,
            "supplier_slicer_candidate_reviewed": False,
            "process_thermal_model_correlated": False,
            "machine_file_generated_and_signed": False,
            "manufacturing_release": False,
        },
        "verdict": {"part_authorized_for_print": False, "orientation_change_authorized": False},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-report", type=Path, required=True)
    parser.add_argument("--reference-metrics", type=Path, required=True)
    parser.add_argument("--candidate-report", type=Path, required=True)
    parser.add_argument("--candidate-metrics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compile_comparison(
        args.reference_report,
        args.reference_metrics,
        args.candidate_report,
        args.candidate_metrics,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except F423Error as exc:
        raise SystemExit(f"F42.3 FAIL-CLOSED: {exc}") from exc
