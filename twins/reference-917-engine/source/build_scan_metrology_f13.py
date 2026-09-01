#!/usr/bin/env python3
"""Build a fail-closed metrology hypothesis from the local 917 interface report."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any


BANK_IDS = ("positive", "negative")
RELEASE_KEYS = (
    "identity_confirmed",
    "scale_confirmed",
    "variant_confirmed",
    "functional_release_authorized",
    "fabrication_release_authorized",
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _validate_vector(value: Any, length: int) -> bool:
    return isinstance(value, list) and len(value) == length and all(_finite_number(item) for item in value)


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    local_input = contract.get("local_input", {})
    if local_input.get("expected_banks") != list(BANK_IDS):
        errors.append("contract_expected_banks_must_be_positive_negative")
    if local_input.get("expected_openings_per_bank") != 6:
        errors.append("contract_must_require_six_openings_per_bank")

    facts = contract.get("public_facts", {})
    bores = facts.get("candidate_bores", [])
    expected_bores = [
        ("type_912_4_5_na", 85.0, "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS", "C"),
        ("917_5_0_na", 86.8, "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS", "C"),
        ("917_30_turbo_5374", 90.0, "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS", "C"),
    ]
    actual_bores = (
        [
            (
                item.get("variant_id"),
                item.get("bore_mm"),
                item.get("source_id"),
                item.get("evidence_grade"),
            )
            for item in bores
        ]
        if isinstance(bores, list) and all(isinstance(item, dict) for item in bores)
        else []
    )
    if actual_bores != expected_bores:
        errors.append("contract_candidate_bores_must_be_85_86_8_90")
    pitch = facts.get("candidate_regular_pitch", {})
    if (
        not isinstance(pitch, dict)
        or pitch.get("value_mm") != 118.0
        or pitch.get("source_id") != "SRC-KFZ-TECH-917-TYPE912-ENGINE"
        or pitch.get("evidence_grade") != "D"
    ):
        errors.append("contract_pitch_must_remain_grade_d_candidate_118_mm")
    studs = facts.get("head_studs", {})
    if not isinstance(studs, dict) or [
        studs.get(key)
        for key in ("count", "free_length_mm", "shaft_diameter_mm", "mass_each_g")
    ] != [48, 149.5, 9.0, 65.0]:
        errors.append("contract_head_stud_facts_changed")
    if (
        not isinstance(studs, dict)
        or studs.get("source_id") != "SRC-PORSCHE-CHRISTOPHORUS-917-DILAVAR-STUDS"
        or studs.get("evidence_grade") != "A"
    ):
        errors.append("contract_head_stud_provenance_changed")
    if not isinstance(studs, dict) or studs.get("scan_observation_status") != "not_observed_in_interfaces_report":
        errors.append("contract_must_not_claim_studs_observed")

    controls = contract.get("required_physical_controls", [])
    if (
        not isinstance(controls, list)
        or not all(isinstance(item, dict) for item in controls)
        or [item.get("id") for item in controls] != ["PC-01", "PC-02", "PC-03"]
    ):
        errors.append("contract_requires_exactly_three_named_physical_controls")
    if not isinstance(controls, list) or any(
        not isinstance(item, dict) or item.get("status") != "missing" for item in controls
    ):
        errors.append("contract_physical_controls_must_start_missing")

    authority = contract.get("release_authority", {})
    if authority.get("minimum_independent_calibrated_physical_controls") != 3:
        errors.append("contract_must_require_three_calibrated_controls")
    forbidden_true = [
        key
        for key, value in authority.items()
        if (key.endswith("_enabled") or key.endswith("_implemented")) and value is not False
    ]
    if forbidden_true:
        errors.append("contract_release_authority_must_remain_disabled:" + ",".join(sorted(forbidden_true)))
    if contract.get("derivation_policy", {}).get("selection_allowed") is not False:
        errors.append("contract_variant_selection_must_be_disabled")
    return errors


def validate_interfaces(report: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_status = contract["local_input"]["expected_detection_status"]
    if report.get("status") != expected_status:
        errors.append("unexpected_interface_report_status")
    banks = report.get("banks")
    if not isinstance(banks, dict) or set(banks) != set(BANK_IDS):
        return errors + ["interfaces_report_requires_exactly_two_named_banks"]

    expected_count = contract["local_input"]["expected_openings_per_bank"]
    for bank_id in BANK_IDS:
        items = banks.get(bank_id)
        if not isinstance(items, list) or len(items) != expected_count:
            errors.append(f"bank_{bank_id}_must_have_{expected_count}_openings")
            continue
        longitudinal: list[float] = []
        for index, item in enumerate(items, start=1):
            prefix = f"bank_{bank_id}_opening_{index}"
            if not isinstance(item, dict):
                errors.append(prefix + "_must_be_object")
                continue
            for key in (
                "diameter_obj_units",
                "circle_fit_p95_obj_units",
                "hough_score",
                "ring_inliers",
            ):
                if not _finite_number(item.get(key)) or item[key] <= 0:
                    errors.append(f"{prefix}_{key}_must_be_positive_finite")
            if not _validate_vector(item.get("center_longitudinal_vertical"), 2):
                errors.append(prefix + "_invalid_longitudinal_vertical_center")
            else:
                longitudinal.append(float(item["center_longitudinal_vertical"][0]))
            if not _validate_vector(item.get("center_scan_coordinates"), 3):
                errors.append(prefix + "_invalid_scan_center")
            axis = item.get("axis_scan_coordinates")
            if not _validate_vector(axis, 3):
                errors.append(prefix + "_invalid_scan_axis")
            elif not math.isclose(math.sqrt(sum(float(value) ** 2 for value in axis)), 1.0, abs_tol=1e-6):
                errors.append(prefix + "_scan_axis_not_unit_length")
        if len(longitudinal) == expected_count and any(right <= left for left, right in zip(longitudinal, longitudinal[1:])):
            errors.append(f"bank_{bank_id}_openings_not_sorted_longitudinally")
    return errors


def _bank_geometry(items: list[dict[str, Any]]) -> dict[str, Any]:
    longitudinal = [float(item["center_longitudinal_vertical"][0]) for item in items]
    gaps = [right - left for left, right in zip(longitudinal, longitudinal[1:])]
    split_index = max(range(len(gaps)), key=gaps.__getitem__)
    regular = [gap for index, gap in enumerate(gaps) if index != split_index]
    return {
        "gaps": gaps,
        "central_split_index": split_index,
        "regular_gaps": regular,
    }


def _rms(values: list[float]) -> float:
    return math.sqrt(sum(value * value for value in values) / len(values))


def _release_block(contract_errors: list[str], input_errors: list[str]) -> dict[str, Any]:
    release = {key: False for key in RELEASE_KEYS}
    release.update(
        {
            "physical_controls_verified": 0,
            "physical_controls_required": 3,
            "blockers": [
                "three_independent_traceably_calibrated_physical_controls_missing",
                "source_identity_not_independently_verified",
                "engine_variant_not_independently_verified",
                "visible_opening_semantics_not_physically_verified",
                "professional_metrology_and_engineering_review_missing",
                "runtime_release_verifier_not_implemented",
            ]
            + (["contract_integrity_failed"] if contract_errors else [])
            + (["interfaces_report_validation_failed"] if input_errors else []),
        }
    )
    return release


def evaluate(contract_path: Path, interfaces_path: Path) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    interfaces = json.loads(interfaces_path.read_text(encoding="utf-8"))
    contract_errors = validate_contract(contract)
    input_errors = validate_interfaces(interfaces, contract) if not contract_errors else []
    release = _release_block(contract_errors, input_errors)
    base: dict[str, Any] = {
        "schema_version": "1.0.0",
        "phase": "F13",
        "asset_id": contract.get("asset_id"),
        "report_status": "failed" if contract_errors or input_errors else "passed_hypothesis_only",
        "input_custody": {
            "interfaces_report_sha256": file_sha256(interfaces_path),
            "raw_mesh_vertices_or_faces_copied_into_report": False,
            "derived_interface_measurements_may_be_included": True,
            "source_geometry_release": False,
        },
        "contract_integrity_errors": contract_errors,
        "input_validation_errors": input_errors,
        "facts": contract.get("public_facts", {}),
        "release": release,
    }
    if contract_errors or input_errors:
        return base

    bank_geometry = {
        bank_id: _bank_geometry(interfaces["banks"][bank_id]) for bank_id in BANK_IDS
    }
    regular_gaps = [
        gap
        for bank_id in BANK_IDS
        for gap in bank_geometry[bank_id]["regular_gaps"]
    ]
    pitch_mm = float(contract["public_facts"]["candidate_regular_pitch"]["value_mm"])
    gap_scales = [pitch_mm / gap for gap in regular_gaps]
    scale = statistics.median(gap_scales)
    scale_sensitivity = max(abs(candidate - scale) for candidate in gap_scales)
    scaled_pitch_residuals = [gap * scale - pitch_mm for gap in regular_gaps]
    bores = contract["public_facts"]["candidate_bores"]

    registry: list[dict[str, Any]] = []
    scaled_diameters: list[float] = []
    for bank_id in BANK_IDS:
        geometry = bank_geometry[bank_id]
        split_index = geometry["central_split_index"]
        for index, item in enumerate(interfaces["banks"][bank_id]):
            diameter_obj = float(item["diameter_obj_units"])
            diameter_mm = diameter_obj * scale
            scaled_diameters.append(diameter_mm)
            gap_obj = None if index == 0 else geometry["gaps"][index - 1]
            gap_class = None
            gap_residual = None
            if gap_obj is not None:
                gap_class = "central_split" if index - 1 == split_index else "regular_pitch"
                if gap_class == "regular_pitch":
                    gap_residual = gap_obj * scale - pitch_mm
            fit_p95_mm = float(item["circle_fit_p95_obj_units"]) * scale
            screening_envelope_mm = (
                2.0 * fit_p95_mm + diameter_obj * scale_sensitivity
            )
            registry.append(
                {
                    "interface_id": f"bank_{bank_id}_geometric_{index + 1:02d}",
                    "semantic_status": "visible_projected_opening_not_certified_bore_or_spigot",
                    "geometric_order_only": True,
                    "bank": bank_id,
                    "geometric_index": index + 1,
                    "center_longitudinal_vertical_obj_units": item["center_longitudinal_vertical"],
                    "center_scan_coordinates_obj_units": item["center_scan_coordinates"],
                    "axis_scan_coordinates": item["axis_scan_coordinates"],
                    "gap_from_previous_obj_units": gap_obj,
                    "gap_classification": gap_class,
                    "regular_pitch_residual_conditional_mm": gap_residual,
                    "visible_diameter_obj_units": diameter_obj,
                    "visible_diameter_conditional_mm": diameter_mm,
                    "circle_fit_p95_obj_units": float(item["circle_fit_p95_obj_units"]),
                    "circle_fit_p95_conditional_mm": fit_p95_mm,
                    "screening_envelope_conditional_mm": screening_envelope_mm,
                    "screening_envelope_is_traceable_uncertainty": False,
                    "ring_inliers": int(item["ring_inliers"]),
                    "hough_score": float(item["hough_score"]),
                    "candidate_bore_residuals_mm": {
                        candidate["variant_id"]: diameter_mm - float(candidate["bore_mm"])
                        for candidate in bores
                    },
                }
            )

    mean_diameter = statistics.mean(scaled_diameters)
    mean_regular_gap = statistics.mean(regular_gaps)
    candidate_comparison = []
    for candidate in bores:
        residuals = [value - float(candidate["bore_mm"]) for value in scaled_diameters]
        candidate_scale = float(candidate["bore_mm"]) / (
            mean_diameter / scale
        )
        implied_pitch = mean_regular_gap * candidate_scale
        candidate_comparison.append(
            {
                "variant_id": candidate["variant_id"],
                "published_bore_mm": candidate["bore_mm"],
                "mean_visible_diameter_residual_mm": statistics.mean(residuals),
                "mean_absolute_interface_residual_mm": statistics.mean(abs(value) for value in residuals),
                "conditional_scale_if_visible_opening_is_bore_mm_per_obj_unit": candidate_scale,
                "implied_regular_pitch_mm_using_observed_mean": implied_pitch,
                "implied_pitch_residual_to_118_mm": implied_pitch - pitch_mm,
                "implied_pitch_relative_residual_percent": (implied_pitch / pitch_mm - 1.0) * 100.0,
                "comparison_semantics": "numerical_screening_only_visible_opening_is_not_a_certified_bore",
            }
        )
    candidate_comparison.sort(key=lambda item: item["mean_absolute_interface_residual_mm"])

    base.update(
        {
            "observations": {
                "interface_count": len(registry),
                "source_report_units_claim": interfaces.get("units"),
                "source_report_units_claim_trusted": False,
                "banks": {
                    bank_id: {
                        "successive_gaps_obj_units": bank_geometry[bank_id]["gaps"],
                        "regular_gaps_obj_units": bank_geometry[bank_id]["regular_gaps"],
                        "central_split_gap_obj_units": bank_geometry[bank_id]["gaps"][bank_geometry[bank_id]["central_split_index"]],
                        "central_split_after_geometric_index": bank_geometry[bank_id]["central_split_index"] + 1,
                    }
                    for bank_id in BANK_IDS
                },
                "visible_diameter_mean_obj_units": statistics.mean(
                    float(item["diameter_obj_units"])
                    for bank_id in BANK_IDS
                    for item in interfaces["banks"][bank_id]
                ),
            },
            "derived": {
                "conditional_scale_mm_per_obj_unit": scale,
                "scale_basis": "118_mm_type_912_candidate_pitch_grade_D",
                "individual_regular_gap_scale_candidates": gap_scales,
                "regular_pitch_mean_obj_units": mean_regular_gap,
                "regular_pitch_sample_stdev_obj_units": statistics.stdev(regular_gaps),
                "regular_pitch_range_obj_units": [min(regular_gaps), max(regular_gaps)],
                "scale_sensitivity_envelope_mm_per_obj_unit": scale_sensitivity,
                "regular_pitch_residual_rms_conditional_mm": _rms(scaled_pitch_residuals),
                "visible_diameter_mean_conditional_mm": mean_diameter,
                "uncertainty_status": "screening_envelope_only_not_traceably_calibrated_measurement_uncertainty",
            },
            "hypotheses": {
                "scale": {
                    "value_mm_per_obj_unit": scale,
                    "status": "conditional_not_confirmed",
                    "assumption": "the_grade_C_118_mm_type_912_pitch_applies_to_this_scan",
                },
                "variant": {
                    "selected_variant_id": None,
                    "closest_numerical_candidate_id": candidate_comparison[0]["variant_id"],
                    "status": "ambiguous_not_selected",
                    "reason": "A projected visible opening cannot identify an engine variant or replace a physical bore/spigot measurement.",
                    "candidate_comparison": candidate_comparison,
                },
            },
            "interface_registry": registry,
            "required_physical_controls": contract["required_physical_controls"],
        }
    )
    return base


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--interfaces", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.contract, args.interfaces)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "report_status": report["report_status"],
        "interface_count": len(report.get("interface_registry", [])),
        "scale_confirmed": report["release"]["scale_confirmed"],
        "fabrication_release_authorized": report["release"]["fabrication_release_authorized"],
    }))
    return 0 if report["report_status"] == "passed_hypothesis_only" else 2


if __name__ == "__main__":
    raise SystemExit(main())
