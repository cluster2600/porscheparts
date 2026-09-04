#!/usr/bin/env python3
"""Valide le contrat fail-closed de la bielle de démonstration F44."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


CONTRACT_RELATIVE_PATH = Path("twins/reference-917-engine/connecting-rod-cad-f44.json")
EXPECTED_CONTRACT_COMMENT = (
    "F44 décrit une bielle unique de démonstration visuelle. Toutes les cotes sont des "
    "hypothèses de conception non mesurées; le montage de deux bielles sur le maneton F35 "
    "reste bloqué."
)
EXPECTED_PARAMETER_NOTES_SHA256 = "b933e223055bf09459fac475f68a9559050a3a3f85ebacddc467097215b4e489"
ALLOWED_CLASSIFICATIONS = {"design_hypothesis", "unknown_requires_traceable_measurement"}
EXPECTED_BINDINGS = {
    "rotating_assembly_cad_f35": (
        "twins/reference-917-engine/rotating-assembly-cad-f35.json",
        "b749e68c52829caae5b21d613ca1f0f1f2b6ad205d1ee69728595a1ccd518954",
    ),
    "parametric_cad_assembly_contract_f22": (
        "twins/reference-917-engine/parametric-cad-assembly-contract-f22.json",
        "87529899d643dd437f357c79fa4dd4fa5ac5ed95929c4fdf82c4985222fd6baa",
    ),
    "component_factory_f41": (
        "twins/reference-917-engine/component-factory-f41.json",
        "58ac9f7c6b3780c48c90bbf6061776480f6160632a1f166f278e139980f2fd5c",
    ),
    "variant_authority_f43": (
        "twins/reference-917-engine/variant-authority-f43.json",
        "021be0be4412f8bd16301af2b3c0536d56e6211d2fef56f94e88b7e9a0f1e15d",
    ),
}
EXPECTED_BINDING_ROLES = {
    "rotating_assembly_cad_f35": "design_hypothesis_parameter_snapshot_only",
    "parametric_cad_assembly_contract_f22": "unknown_interface_register_only",
    "component_factory_f41": "semantic_component_inventory_only",
    "variant_authority_f43": "2026_turbo_variant_identity_only",
}
SOURCE_BINDING_KEYS = {"id", "path", "sha256", "role", "geometry_transfer_authorized"}
EXPECTED_SCOPE = {
    "variant_id": "917_2026_flat12_twin_turbo_1600hp_target",
    "single_rod_demonstrator": True,
    "future_occurrence_count": 12,
    "paired_rod_assembly_allowed": False,
    "display_only": True,
    "engineering_study_only": True,
    "physical_joint_authoring_allowed": False,
    "physics_or_simulation_evidence": False,
    "manufacturing_geometry": False,
    "power_evidence": False,
}
PARAMETER_RECORD_KEYS = {"value", "unit", "classification", "source_refs", "note"}
EXPECTED_PARAMETER_SPECS = {
    "rod_center_distance_mm": (138.0, "mm", ("rotating_assembly_cad_f35",)),
    "rod_width_mm": (22.0, "mm", ("rotating_assembly_cad_f35",)),
    "crankpin_nominal_diameter_mm": (54.0, "mm", ("rotating_assembly_cad_f35",)),
    "crankpin_available_width_mm": (26.0, "mm", ("rotating_assembly_cad_f35",)),
    "paired_rod_axial_clearance_factor": (0.06, "ratio", ("rotating_assembly_cad_f35",)),
    "big_end_outer_diameter_mm": (80.0, "mm", ("rotating_assembly_cad_f35",)),
    "small_end_nominal_bore_mm": (26.0, "mm", ("rotating_assembly_cad_f35",)),
    "small_end_outer_diameter_mm": (42.0, "mm", ()),
    "beam_height_mm": (28.0, "mm", ()),
    "beam_end_overlap_mm": (6.0, "mm", ()),
    "cap_joint_visual_gap_mm": (0.4, "mm", ()),
    "rod_bolt_axis_offset_z_mm": (35.5, "mm", ()),
    "rod_bolt_shank_diameter_mm": (8.0, "mm", ()),
    "rod_bolt_clearance_diameter_mm": (8.6, "mm", ()),
    "rod_bolt_length_mm": (50.0, "mm", ()),
    "rod_bolt_head_diameter_mm": (13.0, "mm", ()),
    "rod_bolt_head_height_mm": (5.0, "mm", ()),
    "rod_bolt_boss_radial_margin_mm": (2.0, "mm", ()),
    "rod_bolt_seat_radial_clearance_mm": (0.5, "mm", ()),
    "rod_bolt_spotface_depth_mm": (1.5, "mm", ()),
    "big_end_bearing_running_clearance_radial_mm": (0.08, "mm", ()),
    "big_end_bearing_shell_thickness_mm": (1.8, "mm", ()),
    "big_end_bearing_axial_width_mm": (20.0, "mm", ()),
    "bearing_split_visual_gap_mm": (0.4, "mm", ()),
    "bearing_housing_visual_clearance_radial_mm": (0.05, "mm", ()),
    "small_end_bushing_inner_clearance_radial_mm": (0.05, "mm", ()),
    "small_end_bushing_thickness_mm": (1.5, "mm", ()),
    "small_end_bushing_axial_width_mm": (18.0, "mm", ()),
    "small_end_housing_visual_clearance_radial_mm": (0.05, "mm", ()),
    "oil_channel_visual_diameter_mm": (2.5, "mm", ()),
    "oil_channel_boolean_overlap_mm": (1.0, "mm", ()),
    "boolean_overshoot_mm": (2.0, "mm", ()),
    "stl_linear_tolerance_mm": (0.08, "mm", ()),
    "stl_angular_tolerance_rad": (0.12, "rad", ()),
}
EXPECTED_FEATURE_COUNTS = {
    "connecting_rod_body": 1,
    "connecting_rod_cap": 1,
    "cap_joint_plane": 1,
    "rod_bolt_through_hole": 2,
    "rod_bolt": 2,
    "big_end_half_bearing": 2,
    "small_end_bushing": 1,
    "internal_oil_channel": 1,
}
EXPECTED_FEATURE_REPRESENTATIONS = {
    "connecting_rod_body": "positive_solid",
    "connecting_rod_cap": "positive_solid",
    "cap_joint_plane": "split_gap_datum",
    "rod_bolt_through_hole": "subtractive_void",
    "rod_bolt": "positive_compound",
    "big_end_half_bearing": "positive_solid",
    "small_end_bushing": "positive_solid",
    "internal_oil_channel": "subtractive_void_and_reference_solid",
}
EXPECTED_SHAPE_IDS = [
    "connecting_rod_body",
    "connecting_rod_cap",
    "rod_bolt_01",
    "rod_bolt_02",
    "big_end_half_bearing_upper",
    "big_end_half_bearing_lower",
    "small_end_bushing",
    "oil_channel_reference",
    "connecting_rod_assembly",
]
EXPECTED_UNKNOWN_IDS = {
    "shared_crankpin_topology_and_finished_width",
    "cap_register_geometry_and_dowel_strategy",
    "rod_bolt_thread_grade_torque_and_preload",
    "bearing_clearance_crush_material_layers_and_oil_grooves",
    "small_end_bushing_interference_material_and_surface_finish",
    "oil_channel_path_diameter_supply_pressure_and_required_flow",
    "forging_or_additive_stock_surface_finish_and_tolerances",
    "load_spectrum_temperature_lubrication_and_fatigue_targets",
}
EXPECTED_RELEASE_GATES = {
    "dimensions_measured",
    "paired_rod_topology_resolved",
    "materials_qualified",
    "fits_and_tolerances_validated",
    "bolt_preload_validated",
    "bearing_and_lubrication_validated",
    "mass_and_inertia_validated",
    "fea_or_fatigue_validated",
    "physics_simulation_authorized",
    "manufacturing_authorized",
    "metal_print_authorized",
    "engine_start_authorized",
    "vehicle_installation_authorized",
    "power_claim_authorized",
    "1600_hp_proven",
}
EXPECTED_PAIR_FORMULA = (
    "required_span_mm = 2 * rod_width_mm + "
    "rod_width_mm * paired_rod_axial_clearance_factor"
)
EXPECTED_PAIR_RESOLUTIONS = [
    "measure_and_redesign_a_wider_crankpin",
    "engineer_and_validate_narrower_rods",
    "engineer_a_fork_and_blade_topology",
    "engineer_separate_crankpins",
]
EXPECTED_PAIR_AUDIT_KEYS = {
    "formula",
    "required_span_mm",
    "available_crankpin_width_mm",
    "deficit_mm",
    "maximum_equal_rod_width_if_side_by_side_mm",
    "status",
    "automatic_resize_allowed",
    "candidate_resolutions_not_selected",
}
EXPECTED_TOP_LEVEL_KEYS = {
    "$comment",
    "schema_version",
    "phase",
    "status",
    "asset_id",
    "source_bindings",
    "scope",
    "classification_vocabulary",
    "parameter_register",
    "unknown_required_inputs",
    "required_features",
    "pair_topology_audit",
    "output_policy",
    "release_gates",
}
EXPECTED_OUTPUT_POLICY = {
    "default_output": "work/917-connecting-rod-cad-f44",
    "overwrite_existing_output": False,
    "source_authority": [
        "twins/reference-917-engine/connecting-rod-cad-f44.json",
        "twins/reference-917-engine/source/build_connecting_rod_cad_f44.py",
    ],
    "neutral_cad": "step/connecting_rod_assembly.step",
    "derived_display_mesh": "stl/connecting_rod_assembly-display-only.stl",
    "geometry_report": "geometry-report.json",
    "expected_shape_ids": EXPECTED_SHAPE_IDS,
    "expected_step_count": len(EXPECTED_SHAPE_IDS),
    "expected_stl_count": len(EXPECTED_SHAPE_IDS),
    "property_assignment_intent": "skip",
    "paired_assembly_export_allowed": False,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("contract_must_be_a_json_object")
    return payload


def _tracked_file(project_root: Path, relative_path: str) -> Path:
    if not relative_path or Path(relative_path).is_absolute():
        raise ValueError(f"invalid_project_relative_path:{relative_path!r}")
    root = project_root.resolve()
    candidate = project_root / relative_path
    if candidate.is_symlink():
        raise ValueError(f"symlink_not_allowed:{relative_path}")
    resolved = candidate.resolve(strict=True)
    resolved.relative_to(root)
    if not resolved.is_file():
        raise ValueError(f"not_a_regular_file:{relative_path}")
    return resolved


def _number(record: Any, name: str, errors: list[str]) -> float | None:
    if not isinstance(record, dict):
        errors.append(f"parameter_register/{name}: record required")
        return None
    if set(record) != PARAMETER_RECORD_KEYS:
        errors.append(f"parameter_register/{name}: exact value/unit/classification/source_refs/note keys required")
    value = record.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        errors.append(f"parameter_register/{name}: finite numeric value required")
        return None
    if record.get("classification") != "design_hypothesis":
        errors.append(f"parameter_register/{name}: classification must be design_hypothesis")
    if not isinstance(record.get("source_refs"), list) or any(
        not isinstance(reference, str) for reference in record.get("source_refs", [])
    ):
        errors.append(f"parameter_register/{name}: source_refs string list required")
    if not isinstance(record.get("note"), str) or not record.get("note", "").strip():
        errors.append(f"parameter_register/{name}: non-empty note required")
    return float(value)


def pair_topology_audit(parameters: dict[str, Any]) -> dict[str, float]:
    """Calcule l'encombrement F35 sans corriger implicitement les cotes."""

    width = float(parameters["rod_width_mm"]["value"])
    factor = float(parameters["paired_rod_axial_clearance_factor"]["value"])
    available = float(parameters["crankpin_available_width_mm"]["value"])
    clearance = width * factor
    required = 2.0 * width + clearance
    return {
        "clearance_mm": clearance,
        "center_separation_mm": width + clearance,
        "required_span_mm": required,
        "available_crankpin_width_mm": available,
        "deficit_mm": required - available,
        "maximum_equal_rod_width_if_side_by_side_mm": available / (2.0 + factor),
    }


def validate(project_root: Path, contract_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        contract = _load(contract_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"contract_read_error:{exc}"]

    if contract.get("schema_version") != "1.0.0" or contract.get("phase") != "F44":
        errors.append("contract identity must be schema 1.0.0 phase F44")
    if set(contract) != EXPECTED_TOP_LEVEL_KEYS:
        errors.append(f"top-level keys mismatch: {sorted(contract)}")
    if contract.get("asset_id") != "porsche-917-2026-connecting-rod-cad-f44":
        errors.append("unexpected asset_id")
    if contract.get("$comment") != EXPECTED_CONTRACT_COMMENT:
        errors.append("$comment must remain the exact non-measured, display-only F44 disclaimer")
    if contract.get("status") != "display_only_detailed_connecting_rod_design_study_pair_topology_blocked":
        errors.append("status must disclose display-only study and blocked pair topology")

    bindings = contract.get("source_bindings")
    if not isinstance(bindings, list):
        errors.append("source_bindings list required")
        bindings = []
    indexed: dict[str, dict[str, Any]] = {}
    for record in bindings:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            errors.append("source_bindings entries require a string id")
            continue
        if set(record) != SOURCE_BINDING_KEYS:
            errors.append(f"source_bindings/{record['id']}: exact binding keys required")
        if record["id"] in indexed:
            errors.append(f"source_bindings duplicate id: {record['id']}")
            continue
        indexed[record["id"]] = record
    if set(indexed) != set(EXPECTED_BINDINGS):
        errors.append(f"source binding ids mismatch: {sorted(indexed)}")
    for binding_id, (expected_path, expected_digest) in EXPECTED_BINDINGS.items():
        record = indexed.get(binding_id)
        if not isinstance(record, dict):
            continue
        if record.get("path") != expected_path:
            errors.append(f"source_bindings/{binding_id}: path mismatch")
        if record.get("sha256") != expected_digest:
            errors.append(f"source_bindings/{binding_id}: declared sha256 mismatch")
        if record.get("role") != EXPECTED_BINDING_ROLES[binding_id]:
            errors.append(f"source_bindings/{binding_id}: role mismatch")
        if record.get("geometry_transfer_authorized") is not False:
            errors.append(f"source_bindings/{binding_id}: geometry transfer must remain false")
        try:
            source = _tracked_file(project_root, expected_path)
            if _sha256(source) != expected_digest:
                errors.append(f"source_bindings/{binding_id}: file sha256 mismatch")
        except (OSError, ValueError) as exc:
            errors.append(f"source_bindings/{binding_id}: {exc}")

    scope = contract.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope object required")
    else:
        if set(scope) != set(EXPECTED_SCOPE):
            errors.append("scope must use the exact closed F44 schema")
        for key, expected in EXPECTED_SCOPE.items():
            if scope.get(key) != expected or type(scope.get(key)) is not type(expected):
                errors.append(f"scope/{key} must remain {expected!r}")

    vocabulary = contract.get("classification_vocabulary")
    if vocabulary != ["design_hypothesis", "unknown_requires_traceable_measurement"]:
        errors.append("classification_vocabulary must contain exactly the two F44 classes")
    parameters = contract.get("parameter_register")
    if not isinstance(parameters, dict) or not parameters:
        errors.append("non-empty parameter_register object required")
        parameters = {}
    if set(parameters) != set(EXPECTED_PARAMETER_SPECS):
        errors.append("parameter_register names differ from the F44 geometry authority")
    values: dict[str, float] = {}
    notes: dict[str, str] = {}
    for name, (expected_value, expected_unit, expected_refs) in EXPECTED_PARAMETER_SPECS.items():
        record = parameters.get(name)
        candidate = _number(record, name, errors)
        if candidate is not None:
            values[name] = candidate
            if not math.isclose(candidate, expected_value, rel_tol=0.0, abs_tol=1e-12):
                errors.append(f"parameter_register/{name}: value changed")
        if isinstance(record, dict):
            if record.get("unit") != expected_unit:
                errors.append(f"parameter_register/{name}: unit must remain {expected_unit}")
            if record.get("source_refs") != list(expected_refs):
                errors.append(f"parameter_register/{name}: source_refs mismatch")
            if isinstance(record.get("note"), str):
                notes[name] = record["note"]
    if set(notes) == set(EXPECTED_PARAMETER_SPECS):
        notes_payload = json.dumps(
            notes,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if hashlib.sha256(notes_payload).hexdigest() != EXPECTED_PARAMETER_NOTES_SHA256:
            errors.append("parameter_register notes differ from the exact F44 disclaimers")
    if any(value <= 0.0 for value in values.values()):
        errors.append("all dimensional parameters must be positive")

    unknowns = contract.get("unknown_required_inputs")
    if not isinstance(unknowns, list) or not unknowns:
        errors.append("unknown_required_inputs must be a non-empty list")
        unknowns = []
    unknown_ids: set[str] = set()
    for record in unknowns:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            errors.append("unknown_required_inputs entries require an id")
            continue
        if set(record) != {"id", "value", "classification"}:
            errors.append(f"unknown_required_inputs/{record['id']}: exact id/value/classification keys required")
        if record["id"] in unknown_ids:
            errors.append(f"duplicate unknown input: {record['id']}")
        unknown_ids.add(record["id"])
        if record.get("value", "missing") is not None:
            errors.append(f"unknown_required_inputs/{record['id']}: value must remain null")
        if record.get("classification") != "unknown_requires_traceable_measurement":
            errors.append(f"unknown_required_inputs/{record['id']}: invalid classification")
    if unknown_ids != EXPECTED_UNKNOWN_IDS:
        errors.append(f"unknown_required_inputs ids mismatch: {sorted(unknown_ids)}")

    features = contract.get("required_features")
    if not isinstance(features, list):
        errors.append("required_features list required")
        features = []
    feature_records: dict[str, tuple[Any, Any]] = {}
    for record in features:
        if not isinstance(record, dict) or set(record) != {"id", "count", "representation"}:
            errors.append("required_features entries need exact id/count/representation keys")
            continue
        feature_id = record.get("id")
        if not isinstance(feature_id, str):
            errors.append("required_features entries require a string id")
            continue
        if feature_id in feature_records:
            errors.append(f"duplicate required feature: {record['id']}")
            continue
        feature_records[feature_id] = (record.get("count"), record.get("representation"))
    if set(feature_records) != set(EXPECTED_FEATURE_COUNTS):
        errors.append(f"required feature ids mismatch: {sorted(feature_records)}")
    for feature_id, expected_count in EXPECTED_FEATURE_COUNTS.items():
        actual = feature_records.get(feature_id)
        if actual is None:
            continue
        if actual[0] != expected_count:
            errors.append(f"required_features/{feature_id}: count mismatch")
        if actual[1] != EXPECTED_FEATURE_REPRESENTATIONS[feature_id]:
            errors.append(f"required_features/{feature_id}: representation mismatch")

    declared_audit = contract.get("pair_topology_audit")
    if not isinstance(declared_audit, dict):
        errors.append("pair_topology_audit object required")
        declared_audit = {}
    if set(declared_audit) != EXPECTED_PAIR_AUDIT_KEYS:
        errors.append("pair_topology_audit must use the exact closed F44 schema")
    if declared_audit.get("formula") != EXPECTED_PAIR_FORMULA:
        errors.append("pair_topology_audit/formula mismatch")
    if all(name in values for name in (
        "rod_width_mm", "paired_rod_axial_clearance_factor", "crankpin_available_width_mm"
    )):
        actual = pair_topology_audit(parameters)
        for name in (
            "required_span_mm", "available_crankpin_width_mm", "deficit_mm",
            "maximum_equal_rod_width_if_side_by_side_mm"
        ):
            declared = declared_audit.get(name)
            if (
                isinstance(declared, bool)
                or not isinstance(declared, (int, float))
                or not math.isfinite(float(declared))
                or not math.isclose(float(declared), actual[name], rel_tol=0.0, abs_tol=1e-9)
            ):
                errors.append(f"pair_topology_audit/{name}: computed mismatch")
        if actual["deficit_mm"] <= 0.0:
            errors.append("pair topology no longer exhibits the declared blocking mismatch")
    if declared_audit.get("status") != "blocked_incompatible_side_by_side_envelopes":
        errors.append("pair topology status must remain blocked")
    if declared_audit.get("automatic_resize_allowed") is not False:
        errors.append("automatic resize must remain false")
    if declared_audit.get("candidate_resolutions_not_selected") != EXPECTED_PAIR_RESOLUTIONS:
        errors.append("pair_topology_audit/candidate_resolutions_not_selected mismatch")

    output = contract.get("output_policy")
    if not isinstance(output, dict) or output != EXPECTED_OUTPUT_POLICY:
        errors.append("output_policy must match the exact fail-closed F44 policy")

    gates = contract.get("release_gates")
    if (
        not isinstance(gates, dict)
        or set(gates) != EXPECTED_RELEASE_GATES
        or any(value is not False for value in gates.values())
    ):
        errors.append("every release gate must be present and explicitly false")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--contract", type=Path)
    args = parser.parse_args()
    root = args.project_root.resolve()
    contract = args.contract or root / CONTRACT_RELATIVE_PATH
    errors = validate(root, contract)
    if errors:
        for error in errors:
            print(f"F44 connecting-rod contract error: {error}", file=sys.stderr)
        return 1
    print("F44 connecting-rod CAD contract validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
