#!/usr/bin/env python3
"""Construit et valide la feuille d'acquisition d'echelle/orientation F21.

F21 specialise le validateur generique F11 pour le scan canonique du carter 917.
Le fichier suivi reste volontairement vide de mesure et de coordonnee. Les
mesures et leurs preuves sont destinees a une copie de travail locale hors Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CONTRACT_REL = Path(
    "twins/reference-917-engine/scan-scale-orientation-acquisition-f21.json"
)
UPSTREAMS = {
    "f11_engineering_input_template": Path(
        "twins/reference-917-engine/engineering-inputs-f11.template.json"
    ),
    "f11_reengineering_contract": Path(
        "twins/reference-917-engine/reengineering-contract-f11.json"
    ),
    "f16_kinematic_interface_readiness": Path(
        "twins/reference-917-engine/kinematic-interface-readiness-f16.json"
    ),
    "f18_boundary_review": Path(
        "twins/reference-917-engine/boundary-review-execution-evidence-f18.json"
    ),
    "f20_fia_valvetrain_flow": Path(
        "twins/reference-917-engine/valvetrain-flow-inputs-f20.json"
    ),
}
UPSTREAM_ROLES = {
    "f11_engineering_input_template": "generic_scale_input_schema",
    "f11_reengineering_contract": "canonical_scan_identity_and_generic_gate_policy",
    "f16_kinematic_interface_readiness": "measurement_campaign_and_named_datum_contract",
    "f18_boundary_review": "current_scan_boundary_and_semantic_state",
    "f20_fia_valvetrain_flow": "documentary_facts_without_scan_calibration_authority",
}

SCAN_SHA256 = "428c4143d073f8330022f2fecbd1ac1ee7784d4f1565f1160020448dbdffa0ae"
F11_SCALE_FEATURE_IDS = ("control_A", "control_B", "control_C")
F16_SCALE_CAMPAIGN_IDS = ("MC-SCALE-01", "MC-SCALE-02", "MC-SCALE-03")
ORIENTATION_DATUMS = (
    (
        "OR-PRIMARY-AXIS",
        "crankshaft_axis",
        "primary_axis",
        "axe_physique identifie sur la piece ou cible enregistree de facon tracable",
    ),
    (
        "OR-SECONDARY-PLANE",
        "crankcase_split_plane",
        "secondary_plane",
        "plan de joint du carter identifie physiquement et dans le scan",
    ),
    (
        "OR-HANDEDNESS",
        "bank_positive_deck_plane",
        "handedness_reference",
        "repere asymetrique mesurable distinguant sans ambiguite la banque positive",
    ),
)

FIA_DIMENSION_REFS_WITHOUT_SAME_FEATURE_METROLOGY = (
    "FACT-4907-BORE",
    "FACT-4907-STROKE",
    "FACT-45-PISTON-COMPRESSION-HEIGHT",
    "FACT-45-CRANKPIN-BEARING-DIAMETER",
    "FACT-45-CONNECTING-ROD-BIG-END-DIAMETER",
    "F20-INTAKE-VALVE-OUTER-DIAMETER",
    "F20-EXHAUST-VALVE-OUTER-DIAMETER",
    "F20-INTAKE-PORT-DIAMETER",
    "F20-INTAKE-VALVE-MAX-LIFT",
    "F20-EXHAUST-VALVE-MAX-LIFT",
    "F20-INTAKE-COLD-CLEARANCE",
    "F20-EXHAUST-COLD-CLEARANCE",
)
FIA_OTHER_NON_CALIBRATION_REFS = (
    "FACT-4907-DISPLACEMENT",
    "FACT-45-CRANKSHAFT-MASS",
    "FACT-45-CONNECTING-ROD-MASS",
    "FACT-45-PISTON-GROUP-MASS",
    "FACT-45-CRANKSHAFT-CONSTRUCTION",
    "FACT-4907-CRANKSHAFT-CONSTRUCTION",
    "F20-CAMSHAFT-COUNT",
    "F20-CAMSHAFT-ARRANGEMENT",
    "F20-CAMSHAFT-DRIVE",
    "F20-VALVE-ACTUATION",
    "F20-INTAKE-OPENS-BTDC",
    "F20-INTAKE-CLOSES-ABDC",
    "F20-EXHAUST-OPENS-BBDC",
    "F20-EXHAUST-CLOSES-ATDC",
)

RELEASE_GATE_IDS = (
    "scan_identity_verified",
    "three_independent_scale_controls_verified",
    "same_feature_physical_correspondence_verified",
    "traceable_provenance_verified",
    "uncertainty_budget_accepted",
    "scan_scale_verified",
    "orientation_primary_axis_verified",
    "orientation_secondary_plane_verified",
    "orientation_handedness_verified",
    "scan_orientation_verified",
    "f11_source_identity_and_scale_adapter_ready",
    "scan_variant_binding_authorized",
    "cad_reconstruction_authorized",
    "classical_solver_authorized",
    "physicsnemo_dataset_authorized",
    "physicsnemo_training_authorized",
    "omniverse_simready_authorized",
    "fabrication_authorized",
    "metal_print_authorized",
    "engine_start_authorized",
)

PROVENANCE_TEMPLATE = {
    "evidence_manifest_ref": None,
    "evidence_artifact_sha256": None,
    "instrument_id": None,
    "calibration_certificate_ref": None,
    "measurement_method": None,
    "measurement_temperature_c": None,
    "operator_or_lab": None,
    "review_status": "missing",
}

FORBIDDEN_COORDINATE_KEYS = {
    "coordinates",
    "origin_mm",
    "direction",
    "normal",
    "transform",
    "transform_mm",
    "matrix",
    "quaternion",
    "euler_angles",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_upstreams(project_root: Path) -> dict[str, dict[str, Any]]:
    return {
        source_id: load_json(project_root / relative_path)
        for source_id, relative_path in UPSTREAMS.items()
    }


def upstream_manifest(project_root: Path) -> list[dict[str, Any]]:
    return [
        {
            "id": source_id,
            "path": str(relative_path),
            "sha256": sha256(project_root / relative_path),
            "role": UPSTREAM_ROLES[source_id],
        }
        for source_id, relative_path in UPSTREAMS.items()
    ]


def scale_control_slot(ordinal: int, f11_feature_id: str) -> dict[str, Any]:
    return {
        "id": f"SC-{ordinal:02d}",
        "f11_feature_id": f11_feature_id,
        "f11_evidence_kind": "scale_control_metrology_report",
        "required": True,
        "status": "missing",
        "independence_requirement": "distinct_physical_feature_and_distinct_scan_region",
        "calibration_basis_required": "physical_measurement_of_the_same_feature_observable_on_the_exact_scan",
        "physical_feature_id": None,
        "scan_region_token": None,
        "observable_on_exact_scan": None,
        "same_feature_measured_physically": None,
        "scan_distance_obj_units": None,
        "physical_distance_mm": None,
        "combined_standard_uncertainty_mm": None,
        "documentary_source_refs": [],
        "provenance": dict(PROVENANCE_TEMPLATE),
    }


def orientation_slot(
    slot_id: str, datum_ref: str, role: str, requirement: str
) -> dict[str, Any]:
    return {
        "id": slot_id,
        "f16_datum_ref": datum_ref,
        "role": role,
        "required_observation": requirement,
        "required": True,
        "status": "missing",
        "observed_on_exact_scan": None,
        "physical_registration_verified": None,
        "scan_region_token": None,
        "semantic_direction_rule": None,
        "angular_uncertainty_deg": None,
        "documentary_source_refs": [],
        "provenance": dict(PROVENANCE_TEMPLATE),
    }


def build_contract(project_root: Path) -> dict[str, Any]:
    return {
        "$comment": (
            "Feuille canonique F21 sans mesure ni coordonnee. Copier hors Git pour "
            "l'acquisition; le fichier suivi ne libere ni echelle, ni orientation, ni CAO."
        ),
        "schema_version": "1.0.0",
        "phase": "F21",
        "status": "acquisition_sheet_ready_scale_and_orientation_unverified",
        "asset": {
            "id": "porsche-917-engine-scan-scale-orientation-f21",
            "source_scan_sha256": SCAN_SHA256,
            "source_scope": "external_crankcase_and_cylinder_scan_reference_only",
            "identity_status": "unverified",
            "native_units": "unconfirmed_OBJ_units",
            "tracked_raw_scan": False,
            "tracked_scan_coordinates": False,
            "tracked_measurements": False,
        },
        "upstream_contracts": upstream_manifest(project_root),
        "f11_compatibility": {
            "adapter_target": "source_identity_and_scale",
            "identity_report": None,
            "mm_per_obj_unit": None,
            "maximum_relative_spread": 0.005,
            "required_control_count": 3,
            "control_id_mapping": [
                {
                    "f21_slot_id": f"SC-{index:02d}",
                    "f11_feature_id": feature_id,
                }
                for index, feature_id in enumerate(F11_SCALE_FEATURE_IDS, start=1)
            ],
            "evidence_claim_pattern": (
                "source_identity_and_scale.scale_controls.{f11_feature_id}"
            ),
            "ready": False,
        },
        "identity_evidence_slot": {
            "id": "ID-01",
            "f11_claim_id": "source_identity_and_scale.identity_report",
            "f11_evidence_kind": "identity_metrology_report",
            "required": True,
            "status": "missing",
            "physical_asset_or_part_set_id": None,
            "variant_id": None,
            "documentary_trace_ref": None,
            "provenance": dict(PROVENANCE_TEMPLATE),
        },
        "acquisition_record_policy": {
            "working_record_location": "work/917-engine/metrology/f21/",
            "working_record_must_remain_outside_git": True,
            "exact_scan_hash_required": True,
            "exact_physical_asset_identity_required": True,
            "three_distinct_physical_features_required": True,
            "three_distinct_scan_regions_required": True,
            "same_feature_scan_to_physical_correspondence_required": True,
            "traceable_instrument_and_calibration_required": True,
            "uncertainty_required_per_control": True,
            "tracked_contract_may_contain_coordinates": False,
            "tracked_contract_may_contain_measurements": False,
        },
        "scale_control_slots": [
            scale_control_slot(index, feature_id)
            for index, feature_id in enumerate(F11_SCALE_FEATURE_IDS, start=1)
        ],
        "orientation_datum_slots": [
            orientation_slot(*definition) for definition in ORIENTATION_DATUMS
        ],
        "orientation_policy": {
            "required_datum_count": 3,
            "primary_axis_plus_secondary_plane_plus_handedness_required": True,
            "render_view_or_filename_cannot_define_orientation": True,
            "documentary_engine_layout_cannot_define_scan_orientation": True,
            "numeric_frame_is_local_evidence_only_until_reviewed": True,
            "orientation_ready": False,
        },
        "documentary_dimension_exclusion": {
            "source_id": "SRC-FIA-917-HOMOLOGATION-250",
            "source_role": "documentary_engine_facts_only",
            "documentary_source_has_scan_scale_authority": False,
            "documentary_source_has_scan_orientation_authority": False,
            "dimension_refs_without_same_feature_metrology_prohibited_for_scan_calibration": list(
                FIA_DIMENSION_REFS_WITHOUT_SAME_FEATURE_METROLOGY
            ),
            "other_documentary_refs_without_scan_calibration_authority": list(
                FIA_OTHER_NON_CALIBRATION_REFS
            ),
            "rule": (
                "A documentary dimension cannot calibrate the scan. F21 accepts only a "
                "physical measurement of the same feature directly observable on the "
                "exact scan, with traceable provenance and uncertainty."
            ),
            "exception_without_physical_metrology": False,
        },
        "current_readiness": {
            "required_scale_control_count": 3,
            "completed_scale_control_count": 0,
            "required_orientation_datum_count": 3,
            "completed_orientation_datum_count": 0,
            "f18_confirmed_interface_count": 0,
            "identity_ready": False,
            "f11_adapter_ready": False,
            "scale_ready": False,
            "orientation_ready": False,
            "cad_input_ready": False,
        },
        "release_gates": {gate_id: False for gate_id in RELEASE_GATE_IDS},
        "prohibited_use": [
            "treat_OBJ_native_units_as_mm",
            "calibrate_scan_from_FIA_or_other_documentary_dimensions",
            "calibrate_from_a_feature_not_observable_on_the_exact_scan",
            "reuse_one_feature_or_one_scan_region_as_three_independent_controls",
            "define_orientation_from_render_view_filename_or_vehicle_layout",
            "bind_scan_to_an_engine_variant_before_identity_metrology",
            "commit_raw_scan_coordinates_or_measurement_evidence",
            "author_fit_critical_CAD_from_this_empty_sheet",
            "release_classical_solver_or_PhysicsNeMo_data",
            "release_Omniverse_SimReady_fabrication_printing_or_engine_start",
        ],
    }


def _walk_keys(value: Any, path: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in FORBIDDEN_COORDINATE_KEYS:
                errors.append(f"tracked_coordinate_field_forbidden:{child_path}")
            errors.extend(_walk_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_walk_keys(child, f"{path}[{index}]"))
    return errors


def validate_upstreams(
    upstream: dict[str, dict[str, Any]]
) -> list[str]:
    errors: list[str] = []
    f11_input = upstream["f11_engineering_input_template"]
    f11_contract = upstream["f11_reengineering_contract"]
    f16 = upstream["f16_kinematic_interface_readiness"]
    f18 = upstream["f18_boundary_review"]
    f20 = upstream["f20_fia_valvetrain_flow"]

    f11_scale = f11_input.get("source_identity_and_scale", {})
    f11_controls = f11_scale.get("scale_controls", [])
    if (
        len(f11_controls) != 3
        or tuple(item.get("feature_id") for item in f11_controls)
        != F11_SCALE_FEATURE_IDS
        or f11_scale.get("maximum_relative_spread") != 0.005
    ):
        errors.append("f11_generic_scale_contract_incompatible")
    if f11_contract.get("asset", {}).get("source_scan_sha256") != SCAN_SHA256:
        errors.append("f11_scan_sha256_mismatch")

    f16_measurements = {
        item.get("id"): item for item in f16.get("measurement_campaign_template", [])
    }
    if any(
        measurement_id not in f16_measurements
        or f16_measurements[measurement_id].get("value") is not None
        for measurement_id in F16_SCALE_CAMPAIGN_IDS
    ):
        errors.append("f16_scale_campaign_contract_incompatible")
    fixed_datums = {
        item.get("id"): item
        for item in f16.get("datum_registry_contract", {}).get("fixed_datums", [])
    }
    for _, datum_ref, _, _ in ORIENTATION_DATUMS:
        if datum_ref not in fixed_datums:
            errors.append(f"f16_named_datum_missing:{datum_ref}")
    if f16.get("work_branch", {}).get("scan_binding") is not False:
        errors.append("f16_scan_must_remain_unbound")
    if any(f16.get("release_gates", {}).values()):
        errors.append("f16_release_gate_open")

    custody = f18.get("source_custody", {})
    inventory = f18.get("inventory", {})
    if custody.get("sha256") != SCAN_SHA256:
        errors.append("f18_scan_sha256_mismatch")
    if inventory.get("confirmed_interface_count") != 0:
        errors.append("f18_interface_state_changed_requires_f21_review")
    if inventory.get("units") != "unconfirmed OBJ coordinate units":
        errors.append("f18_units_must_remain_unconfirmed")
    for gate_id in ("scale_confirmed", "units_confirmed", "axis_semantics_confirmed"):
        if f18.get("release_gates", {}).get(gate_id) is not False:
            errors.append(f"f18_release_gate_open:{gate_id}")

    if f20.get("source_contract", {}).get("source_id") != "SRC-FIA-917-HOMOLOGATION-250":
        errors.append("f20_fia_source_contract_mismatch")
    authority = f20.get("authority_boundary", {})
    if any(
        authority.get(gate_id) is not False
        for gate_id in (
            "cad_dimension_release_authorized",
            "boundary_condition_release_authorized",
            "solver_execution_authorized",
            "manufacturing_authorized",
            "physicsnemo_training_authorized",
        )
    ):
        errors.append("f20_documentary_authority_must_remain_closed")
    return errors


def validate_contract(project_root: Path, contract: dict[str, Any]) -> list[str]:
    expected = build_contract(project_root)
    errors = validate_upstreams(load_upstreams(project_root))

    if contract != expected:
        errors.append("canonical_f21_contract_mismatch")

    if contract.get("schema_version") != "1.0.0" or contract.get("phase") != "F21":
        errors.append("f21_schema_or_phase_mismatch")
    if contract.get("asset") != expected["asset"]:
        errors.append("canonical_scan_asset_contract_mismatch")
    if contract.get("upstream_contracts") != expected["upstream_contracts"]:
        expected_by_id = {item["id"]: item for item in expected["upstream_contracts"]}
        observed_by_id = {
            item.get("id"): item for item in contract.get("upstream_contracts", [])
        }
        for source_id, item in expected_by_id.items():
            if observed_by_id.get(source_id, {}).get("sha256") != item["sha256"]:
                errors.append(f"upstream_sha256_mismatch:{source_id}")
        errors.append("upstream_contract_manifest_mismatch")

    if contract.get("f11_compatibility") != expected["f11_compatibility"]:
        errors.append("f11_compatibility_mismatch")
    if contract.get("identity_evidence_slot") != expected["identity_evidence_slot"]:
        errors.append("identity_evidence_template_mismatch")
    if contract.get("acquisition_record_policy") != expected["acquisition_record_policy"]:
        errors.append("acquisition_record_policy_mismatch")

    controls = contract.get("scale_control_slots", [])
    if len(controls) != 3:
        errors.append("exactly_three_scale_control_slots_required")
    expected_controls = expected["scale_control_slots"]
    if controls != expected_controls:
        errors.append("scale_control_template_mismatch")
    feature_ids = [item.get("f11_feature_id") for item in controls if isinstance(item, dict)]
    if len(feature_ids) != len(set(feature_ids)) or tuple(feature_ids) != F11_SCALE_FEATURE_IDS:
        errors.append("scale_control_independence_contract_mismatch")

    if contract.get("orientation_datum_slots") != expected["orientation_datum_slots"]:
        errors.append("orientation_datum_template_mismatch")
    if contract.get("orientation_policy") != expected["orientation_policy"]:
        errors.append("orientation_policy_mismatch")
    if (
        contract.get("documentary_dimension_exclusion")
        != expected["documentary_dimension_exclusion"]
    ):
        errors.append("documentary_dimension_exclusion_mismatch")
    if contract.get("current_readiness") != expected["current_readiness"]:
        errors.append("current_readiness_must_remain_empty")

    gates = contract.get("release_gates", {})
    if set(gates) != set(RELEASE_GATE_IDS) or any(value is not False for value in gates.values()):
        errors.append("all_f21_release_gates_must_be_false")
    if contract.get("prohibited_use") != expected["prohibited_use"]:
        errors.append("prohibited_use_contract_mismatch")
    errors.extend(_walk_keys(contract))
    return sorted(set(errors))


def evaluate(project_root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    errors = validate_contract(project_root, contract)
    return {
        "schema_version": "1.0.0",
        "phase": "F21",
        "report_status": "passed_fail_closed" if not errors else "failed",
        "contract_errors": errors,
        "scan_sha256": SCAN_SHA256,
        "readiness": {
            "identity_ready": False,
            "scale_controls_required": 3,
            "scale_controls_completed": 0,
            "orientation_datums_required": 3,
            "orientation_datums_completed": 0,
            "f11_adapter_ready": False,
            "scale_ready": False,
            "orientation_ready": False,
            "cad_ready": False,
        },
        "release": {gate_id: False for gate_id in RELEASE_GATE_IDS},
        "tracked_sensitive_content": {
            "raw_scan": False,
            "scan_coordinates": False,
            "physical_measurements": False,
            "proprietary_pdf": False,
        },
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[3]
    )
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    project_root = args.root.resolve()
    contract_path = (
        args.contract.resolve()
        if args.contract
        else project_root / CONTRACT_REL
    )
    if args.generate:
        write_json(contract_path, build_contract(project_root))
    contract = load_json(contract_path)
    report = evaluate(project_root, contract)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["report_status"] == "passed_fail_closed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
