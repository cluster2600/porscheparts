#!/usr/bin/env python3
"""Build the virtual-only F2 readiness contract for the 993 Turbo engine carrier.

The contract turns catalogue identities and the few documentary values into an
explicit interface graph, a parameter registry and symbolic load cases. It does
not invent interface coordinates and therefore grants no F2 geometry, solver,
SimReady or manufacturing credit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engine-carrier-virtual-f2-readiness.json"
)
USD_OUTPUT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering"
    / "993-engine-carrier-virtual-f2-readiness.usda"
)

SOURCE_PATHS = {
    "part_record": ROOT / "catalog" / "parts" / "993-eng-carrier-0001.json",
    "declared_part_data": ROOT / "catalog" / "reference" / "993-declared-part-data.json",
    "manual_measurements": ROOT / "catalog" / "measurements" / "MEAS-MANUAL-993-ALL.json",
    "porschefanatics_context": (
        ROOT
        / "twins"
        / "catalogue-parts"
        / "evidence"
        / "porschefanatics-993-oem-context.json"
    ),
    "catalogue_twin_index": ROOT / "twins" / "catalogue-parts" / "index.json",
    "material_screening": (
        ROOT
        / "twins"
        / "catalogue-parts"
        / "engine-carrier-material-screening-f1.json"
    ),
    "mass_constrained_surrogate": (
        ROOT
        / "twins"
        / "catalogue-parts"
        / "engine-carrier-mass-constrained-surrogate-f1.json"
    ),
    "load_case_evidence": (
        ROOT / "parts" / "993-eng-carrier-0001" / "evidence" / "load-cases.md"
    ),
}

GRAVITY_M_S2 = 9.80665
DOCUMENTARY_ENGINE_MASS_KG = 195.0


class ContractError(ValueError):
    """Raised when the contract would silently promote an unsupported claim."""


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load:{relative(path)}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected_object:{relative(path)}")
    return value


def source_manifest() -> list[dict[str, str]]:
    roles = {
        "part_record": "classification_provenance_and_known_limits",
        "declared_part_data": "declared_envelope_mass_and_material_observation",
        "manual_measurements": "candidate_torque_record_not_turbo_applicability_proof",
        "porschefanatics_context": "pet_identity_variant_quantity_and_companion_parts",
        "catalogue_twin_index": "F1_envelope_identity_and_asset_paths",
        "material_screening": "generic_coupon_tradeoff_without_component_credit",
        "mass_constrained_surrogate": (
            "envelope_mass_constrained_structural_witness_without_component_credit"
        ),
        "load_case_evidence": "documentary_mass_load_unknowns_and_review_boundary",
    }
    return [
        {
            "id": identifier,
            "path": relative(path),
            "sha256": sha256_file(path),
            "role": roles[identifier],
        }
        for identifier, path in SOURCE_PATHS.items()
    ]


def porschefanatics_record(
    payload: dict[str, Any], reference: str
) -> dict[str, Any]:
    records = payload.get("records")
    if not isinstance(records, list):
        raise ContractError("porschefanatics_records")
    matches = [
        item
        for item in records
        if isinstance(item, dict) and item.get("oem_reference") == reference
    ]
    if len(matches) != 1:
        raise ContractError(f"porschefanatics_identity:{reference}:{len(matches)}")
    record = matches[0]
    if record.get("pet_verified") is not True or record.get("depth") != "read":
        raise ContractError(f"porschefanatics_unverified:{reference}")
    return record


def declared_carrier(payload: dict[str, Any]) -> dict[str, Any]:
    matches = [
        item
        for item in payload.get("entries", [])
        if isinstance(item, dict) and item.get("oem_reference") == "993 115 021 53"
    ]
    if len(matches) != 1:
        raise ContractError(f"declared_carrier:{len(matches)}")
    record = matches[0]
    if record.get("dimensions_mm") != [600, 50, 50] or record.get("mass_kg") != 1.96:
        raise ContractError("declared_carrier_values")
    return record


def torque_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    matches = [
        item
        for item in payload.get("declared_values", [])
        if isinstance(item, dict) and item.get("value_id") == "MNL-TORQUE-0047"
    ]
    if len(matches) != 1:
        raise ContractError(f"torque_candidate:{len(matches)}")
    record = matches[0]
    if record.get("numeric_values") != [85.0]:
        raise ContractError("torque_candidate_value")
    details = record.get("details", {})
    if details.get("thread") != "M 12" or details.get("pdf_page") != 74:
        raise ContractError("torque_candidate_details")
    return record


def parameter(
    identifier: str, quantity: str, unit: str | None, required_by: list[str]
) -> dict[str, Any]:
    return {
        "id": identifier,
        "quantity": quantity,
        "value": None,
        "unit": unit,
        "uncertainty": None,
        "status": "unknown_virtual_inference_or_external_evidence_required",
        "required_by": required_by,
    }


def render_usd() -> str:
    return '''#usda 1.0
(
    defaultPrim = "EngineCarrierVirtualF2Readiness"
    metersPerUnit = 0.001
    upAxis = "Z"
    subLayers = [
        @../usd/993-engine-carrier-turbo.usda@
        @993-engine-carrier-mass-constrained-surrogate-f1.usda@
    ]
)

def Xform "EngineCarrierVirtualF2Readiness" (
    kind = "component"
)
{
    custom string contractStatus = "F2_readiness_only_no_F2_geometry_credit"
    custom bool f2InterfaceGeometryPresent = false
    custom bool vehicleTransformKnown = false
    custom bool physicsAssigned = false
    custom bool simReadyValidated = false
    custom string sourceEnvelope = "TWIN-993-ENGINE-CARRIER-TURBO"

    def Scope "InterfaceHypotheses"
    {
        def Xform "CarrierToEngineBracket"
        {
            custom string peerOemReference = "993 115 103 52"
            custom string relationshipStatus = "PET_group_topology_hypothesis_only"
            custom bool coordinatesKnown = false
            custom bool attachmentGeometryKnown = false
        }

        def Xform "CarrierToEngineMounts"
        {
            custom string peerOemReference = "993 375 049 05"
            custom int peerQuantityPerCar = 2
            custom string relationshipStatus = "PET_group_topology_hypothesis_only"
            custom bool coordinatesKnown = false
            custom bool attachmentGeometryKnown = false
        }
    }

    def Scope "SolverReadiness"
    {
        custom bool referenceCaeEnabled = false
        custom bool physicsNeMoEnabled = false
        custom bool manufacturingEnabled = false
    }
}
'''


def build_report(usd_text: str) -> dict[str, Any]:
    part = load_json(SOURCE_PATHS["part_record"])
    declared = declared_carrier(load_json(SOURCE_PATHS["declared_part_data"]))
    manual = torque_candidate(load_json(SOURCE_PATHS["manual_measurements"]))
    context = load_json(SOURCE_PATHS["porschefanatics_context"])
    carrier = porschefanatics_record(context, "993 115 021 53")
    bracket = porschefanatics_record(context, "993 115 103 52")
    mounts = porschefanatics_record(context, "993 375 049 05")
    twin_index = load_json(SOURCE_PATHS["catalogue_twin_index"])
    material_screening = load_json(SOURCE_PATHS["material_screening"])
    mass_surrogate = load_json(SOURCE_PATHS["mass_constrained_surrogate"])
    load_text = SOURCE_PATHS["load_case_evidence"].read_text(encoding="utf-8")

    if part.get("classification", {}).get("safety_class") != "safety_critical":
        raise ContractError("safety_class")
    if "environ 195 kg" not in load_text:
        raise ContractError("documentary_engine_mass_anchor")
    if material_screening.get("screening_decision", {}).get("component_credit") is not False:
        raise ContractError("material_screening_component_credit")
    if mass_surrogate.get("status") != (
        "F1_mass_constrained_structural_surrogate_no_component_credit"
    ):
        raise ContractError("mass_constrained_surrogate_status")
    if mass_surrogate.get("derived_section", {}).get("mass_constraint_closed") is not True:
        raise ContractError("mass_constrained_surrogate_mass_closure")
    if any(
        value is not False
        for value in mass_surrogate.get("claim_boundary", {}).values()
    ):
        raise ContractError("mass_constrained_surrogate_claim_boundary")
    twins = twin_index.get("twins", [])
    proxy_matches = [
        item
        for item in twins
        if isinstance(item, dict)
        and item.get("subject", {}).get("oem_reference") == "993 115 021 53"
    ]
    if len(proxy_matches) != 1 or proxy_matches[0].get("fidelity") != "F1_envelope":
        raise ContractError("carrier_F1_proxy")

    static_upper_N = DOCUMENTARY_ENGINE_MASS_KG * GRAVITY_M_S2
    conditional_mount_upper_N = static_upper_N / 2.0
    parameters = [
        parameter("P-F2-001", "carrier_to_bracket_interface_centres_xyz", "mm", ["package", "structural"]),
        parameter("P-F2-002", "carrier_to_mount_interface_centres_xyz", "mm", ["package", "structural", "multibody"]),
        parameter("P-F2-003", "interface_axes_and_normals", None, ["package", "structural"]),
        parameter("P-F2-004", "hole_diameters_thread_engagement_and_pattern", "mm", ["package", "structural"]),
        parameter("P-F2-005", "bearing_faces_and_contact_areas", "mm2", ["structural"]),
        parameter("P-F2-006", "carrier_thickness_and_section_profile", "mm", ["structural"]),
        parameter("P-F2-007", "fillet_hole_and_boss_geometry", "mm", ["structural", "fatigue"]),
        parameter("P-F2-008", "carrier_to_vehicle_transform", "mm_deg", ["vehicle_integration", "omniverse"]),
        parameter("P-LOAD-001", "powertrain_mass_fraction_reacted_by_carrier", None, ["vertical", "longitudinal", "lateral"]),
        parameter("P-LOAD-002", "powertrain_centre_of_gravity_xyz", "mm", ["vertical", "longitudinal", "lateral", "torque"]),
        parameter("P-LOAD-003", "turbo_engine_torque_envelope", "N_m", ["torque", "fatigue"]),
        parameter("P-LOAD-004", "vertical_dynamic_factor", "g", ["pothole", "fatigue"]),
        parameter("P-LOAD-005", "longitudinal_acceleration_factor", "g", ["longitudinal", "fatigue"]),
        parameter("P-LOAD-006", "lateral_acceleration_factor", "g", ["lateral", "fatigue"]),
        parameter("P-LOAD-007", "mount_stiffness_and_damping_matrix", "N_per_mm", ["modal", "multibody"]),
        parameter("P-LOAD-008", "temperature_field_and_gradient", "degC", ["thermal", "fatigue"]),
        parameter("P-LOAD-009", "duty_cycle_and_load_spectrum", None, ["fatigue"]),
        parameter("P-MAT-001", "qualified_material_elastic_plastic_fatigue_curves", None, ["structural", "modal", "fatigue"]),
        parameter("P-ACC-001", "stress_displacement_modal_and_fatigue_limits", None, ["all_reference_solvers"]),
    ]

    return {
        "$comment": (
            "Contrat d'inference virtuelle vers F2. Il structure les interfaces et "
            "les equations, mais ne fournit aucune cote d'interface ni autorisation."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "status": "F2_virtual_readiness_complete_no_F2_geometry_credit",
        "subject": {
            "part_id": "993-ENG-CARRIER-0001",
            "oem_reference": carrier["oem_reference"],
            "part_master_twin_id": "TWIN-PET-993-PART-F77CBF8A0C10743C3178",
            "variant": "993-turbo",
            "quantity_per_car": carrier["quantity_per_car"],
            "safety_class": "safety_critical",
            "current_component_fidelity": "F1_envelope_identity_linked_unvalidated",
        },
        "source_boundary": {
            "files": source_manifest(),
            "source_integrity_checked": True,
            "porschefanatics_source_repository_commit": context["source_repository_commit"],
            "public_images_copied_into_repository": False,
            "pet_illustration_used_as_scale_reference": False,
        },
        "documentary_inputs": {
            "pet_identity": {
                "group": carrier["pet_group"],
                "position": carrier["pet_position"],
                "quantity_per_car": carrier["quantity_per_car"],
                "proven_variants": carrier["fits_vehicles"],
                "status": "verified_in_catalogue_context",
            },
            "declared_envelope_mm": declared["dimensions_mm"],
            "declared_part_mass_kg": declared["mass_kg"],
            "documentary_powertrain_mass_candidate_kg": {
                "value": DOCUMENTARY_ENGINE_MASS_KG,
                "scope": "GT2_Race_complete_engine_outside_gearbox_rounded_anchor",
                "status": "community_documentary_candidate_not_exact_Turbo_mass_or_carrier_load",
            },
            "tightening_candidate": {
                "value_id": manual["value_id"],
                "thread": manual["details"]["thread"],
                "torque_Nm": manual["numeric_values"][0],
                "status": "manual_record_candidate_not_proven_applicable_to_Turbo_reference",
                "used_to_compute_preload": False,
            },
        },
        "coordinate_system": {
            "units": "mm",
            "local_axes": {
                "X": "hypothesis_along_declared_600_mm_envelope",
                "Y": "hypothesis_along_declared_50_mm_envelope",
                "Z": "hypothesis_along_declared_50_mm_envelope",
            },
            "origin": None,
            "vehicle_transform": None,
            "status": "visual_envelope_frame_only_not_vehicle_registered",
        },
        "mass_constrained_surrogate": {
            "contract": relative(SOURCE_PATHS["mass_constrained_surrogate"]),
            "status": mass_surrogate["status"],
            "editable_scad": mass_surrogate["assets"]["editable_scad"],
            "openusd_guide": mass_surrogate["assets"]["openusd_guide"],
            "equivalent_wall_mm": mass_surrogate["derived_section"][
                "equivalent_wall_mm"
            ],
            "fill_fraction": mass_surrogate["derived_section"]["fill_fraction"],
            "mass_constraint_closed": mass_surrogate["derived_section"][
                "mass_constraint_closed"
            ],
            "interface_search_domain_count": len(
                mass_surrogate["interface_search_domains"]
            ),
            "selected_interface_point_count": sum(
                int(item["selected_point_count"])
                for item in mass_surrogate["interface_search_domains"]
            ),
            "component_geometry_credit": False,
            "reference_CAE_credit": False,
        },
        "interface_hypotheses": [
            {
                "interface_id": "IF-993-EC-CARRIER-BRACKET",
                "peer_oem_reference": bracket["oem_reference"],
                "peer_name": bracket["english_name"],
                "peer_quantity_per_car": bracket["quantity_per_car"],
                "identity_status": "verified_same_Turbo_PET_group",
                "relationship_status": "topology_hypothesis_not_attachment_proof",
                "coordinates_mm": None,
                "axes": None,
                "contact_geometry": None,
                "tolerance_mm": None,
                "confirmed_interface_geometry": False,
            },
            {
                "interface_id": "IF-993-EC-CARRIER-MOUNTS",
                "peer_oem_reference": mounts["oem_reference"],
                "peer_name": mounts["english_name"],
                "peer_quantity_per_car": mounts["quantity_per_car"],
                "identity_status": "verified_in_Turbo_PET_context",
                "relationship_status": "topology_hypothesis_not_attachment_proof",
                "coordinates_mm": None,
                "axes": None,
                "contact_geometry": None,
                "tolerance_mm": None,
                "confirmed_interface_geometry": False,
            },
        ],
        "parameter_registry": parameters,
        "mathematical_model": {
            "status": "partial_symbolic_screening_only",
            "constants": {"standard_gravity_m_s2": GRAVITY_M_S2},
            "equations": [
                "F_carrier_static_N = m_powertrain_kg * g_m_s2 * alpha_carrier",
                "R_left_N + R_right_N = F_carrier_static_N",
                "sum_forces_xyz = 0 and sum_moments_xyz = 0 for every solved load case",
                "F_dynamic_axis_N = m_powertrain_kg * g_m_s2 * acceleration_factor_axis_g * alpha_carrier",
                "M_reaction_Nm = T_engine_Nm plus cross(r_CG_m, F_inertial_N)",
            ],
            "computed_documentary_bounds": {
                "alpha_carrier_assumption_range": [0.0, 1.0],
                "static_gravity_force_range_N": [0.0, round(static_upper_N, 6)],
                "conditional_equal_mount_reaction_range_N_each": [
                    0.0,
                    round(conditional_mount_upper_N, 6),
                ],
                "conditional_note": (
                    "La reaction par support ne vaut que sous symetrie, charge centree et "
                    "partage egal ; ces hypotheses ne sont pas validees."
                ),
                "component_strength_or_life_conclusion": None,
            },
            "dimensional_balance_required": True,
            "energy_balance_required_where_applicable": True,
        },
        "load_cases": [
            {
                "id": "LC-993-EC-STATIC-GRAVITY",
                "kind": "static_vertical",
                "known_input_ids": ["documentary_powertrain_mass_candidate_kg"],
                "missing_parameter_ids": ["P-LOAD-001", "P-LOAD-002"],
                "status": "blocked_partial_documentary_bound_only",
            },
            {
                "id": "LC-993-EC-ENGINE-TORQUE",
                "kind": "powertrain_reaction_torque",
                "missing_parameter_ids": ["P-LOAD-002", "P-LOAD-003"],
                "status": "blocked_no_Turbo_torque_envelope_or_reaction_arm",
            },
            {
                "id": "LC-993-EC-LONGITUDINAL",
                "kind": "longitudinal_inertia",
                "missing_parameter_ids": ["P-LOAD-001", "P-LOAD-002", "P-LOAD-005"],
                "status": "blocked",
            },
            {
                "id": "LC-993-EC-LATERAL",
                "kind": "lateral_inertia",
                "missing_parameter_ids": ["P-LOAD-001", "P-LOAD-002", "P-LOAD-006"],
                "status": "blocked",
            },
            {
                "id": "LC-993-EC-POTHOLE",
                "kind": "vertical_shock",
                "missing_parameter_ids": ["P-LOAD-001", "P-LOAD-002", "P-LOAD-004"],
                "status": "blocked",
            },
            {
                "id": "LC-993-EC-MODAL",
                "kind": "normal_modes_with_mount_compliance",
                "missing_parameter_ids": ["P-LOAD-007", "P-MAT-001", "P-ACC-001"],
                "status": "blocked",
            },
            {
                "id": "LC-993-EC-THERMAL",
                "kind": "thermal_expansion_and_gradient",
                "missing_parameter_ids": ["P-LOAD-008", "P-MAT-001", "P-ACC-001"],
                "status": "blocked",
            },
            {
                "id": "LC-993-EC-FATIGUE",
                "kind": "variable_amplitude_fatigue",
                "missing_parameter_ids": ["P-LOAD-003", "P-LOAD-004", "P-LOAD-005", "P-LOAD-006", "P-LOAD-009", "P-MAT-001", "P-ACC-001"],
                "status": "blocked",
            },
        ],
        "model_roles": {
            "llm": {
                "allowed": [
                    "propose_explicit_hypotheses_with_uncertainty",
                    "detect_cross_source_contradictions",
                    "generate_solver_input_drafts_for_deterministic_review",
                ],
                "prohibited": [
                    "invent_measurements_or_tolerances",
                    "replace_equilibrium_or_reference_solver",
                    "approve_material_manufacturing_or_vehicle_release",
                ],
                "output_authority": "hypothesis_only",
            },
            "reference_solver": {
                "structural": "CalculiX_after_F3_load_bearing_geometry",
                "package": "parametric_CAD_tolerance_stack_and_collision_check_after_F2",
                "current_mass_constrained_surrogate": (
                    "analytic_sensitivity_bookends_only_not_reference_CAE"
                ),
                "enabled": False,
            },
            "physicsnemo": {
                "candidate_models": ["GeoTransolver", "MeshGraphNet", "Transolver", "FIGConvUNet"],
                "role": "surrogate_only_after_converged_reference_CAE_dataset",
                "training_enabled": False,
                "inference_enabled": False,
                "validated": False,
            },
            "omniverse": {
                "semantic_layer": relative(USD_OUTPUT),
                "semantic_layer_sha256": sha256_bytes(usd_text.encode("utf-8")),
                "F1_envelope_composed": True,
                "F1_mass_constrained_surrogate_composed": True,
                "F2_interface_geometry_present": False,
                "physics_assignment_present": False,
                "simready_validated": False,
            },
        },
        "virtual_inference_policy": {
            "physical_measurements_expected_from_user": False,
            "allowed_future_inputs": [
                "licensed_multi_view_public_images",
                "catalogue_identity_and_quantity_evidence",
                "declared_bounding_envelopes",
                "cross_reference_family_geometry_kept_as_non_transferable_prior",
            ],
            "required_output_for_each_inference": [
                "method",
                "source_image_or_record_ids",
                "uncertainty_interval",
                "scale_anchor",
                "variant_scope",
                "independent_consistency_check",
            ],
            "automatic_promotion_to_F2": False,
        },
        "release_gates": {
            "F2_interface_geometry": False,
            "F3_engineering_geometry": False,
            "qualified_material_selected": False,
            "reference_CAE_passed": False,
            "physicsnemo_validated": False,
            "simready_validated": False,
            "professional_engineering_review": False,
            "manufacturing": False,
            "installation": False,
            "road_use": False,
        },
        "next_gate": (
            "infer_and_cross_check_interface_coordinates_with_uncertainty_then_author_"
            "an_editable_F2_hypothesis_without_fit_or_release_claim"
        ),
    }


def validate(report: dict[str, Any], usd_text: str) -> None:
    if report.get("status") != "F2_virtual_readiness_complete_no_F2_geometry_credit":
        raise ContractError("status")
    files = report.get("source_boundary", {}).get("files", [])
    expected_digests = {relative(path): sha256_file(path) for path in SOURCE_PATHS.values()}
    observed_digests = {
        item.get("path"): item.get("sha256") for item in files if isinstance(item, dict)
    }
    if observed_digests != expected_digests:
        raise ContractError("source_digests")
    parameters = report.get("parameter_registry")
    if not isinstance(parameters, list) or len(parameters) != 19:
        raise ContractError("parameter_registry")
    if any(item.get("value") is not None or item.get("uncertainty") is not None for item in parameters):
        raise ContractError("invented_parameter")
    interfaces = report.get("interface_hypotheses")
    if not isinstance(interfaces, list) or len(interfaces) != 2:
        raise ContractError("interface_hypotheses")
    if any(item.get("confirmed_interface_geometry") is not False for item in interfaces):
        raise ContractError("confirmed_interface_geometry")
    surrogate = report.get("mass_constrained_surrogate", {})
    if surrogate.get("mass_constraint_closed") is not True:
        raise ContractError("mass_surrogate_closure")
    if surrogate.get("interface_search_domain_count") != 2:
        raise ContractError("mass_surrogate_search_domains")
    if surrogate.get("selected_interface_point_count") != 0:
        raise ContractError("mass_surrogate_interface_overclaim")
    if surrogate.get("component_geometry_credit") is not False:
        raise ContractError("mass_surrogate_component_credit")
    if surrogate.get("reference_CAE_credit") is not False:
        raise ContractError("mass_surrogate_reference_CAE_credit")
    if report.get("documentary_inputs", {}).get("tightening_candidate", {}).get("used_to_compute_preload") is not False:
        raise ContractError("unsupported_preload")
    bounds = report.get("mathematical_model", {}).get("computed_documentary_bounds", {})
    if bounds.get("static_gravity_force_range_N") != [0.0, 1912.29675]:
        raise ContractError("gravity_bound")
    if not isinstance(report.get("load_cases"), list) or len(report["load_cases"]) != 8:
        raise ContractError("load_cases")
    if any(not str(item.get("status", "")).startswith("blocked") for item in report["load_cases"]):
        raise ContractError("load_case_promoted")
    if any(value is not False for value in report.get("release_gates", {}).values()):
        raise ContractError("release_gate")
    omniverse = report.get("model_roles", {}).get("omniverse", {})
    if omniverse.get("semantic_layer_sha256") != sha256_bytes(usd_text.encode("utf-8")):
        raise ContractError("usd_digest")
    for prohibited in ("Physics", "Mesh", "xformOp:", "translate ="):
        if prohibited in usd_text:
            raise ContractError(f"usd_overclaim:{prohibited}")
    required_usd_tokens = (
        "f2InterfaceGeometryPresent = false",
        "physicsAssigned = false",
        "simReadyValidated = false",
        "coordinatesKnown = false",
    )
    if any(token not in usd_text for token in required_usd_tokens):
        raise ContractError("usd_fail_closed_metadata")


def render_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def run(write: bool) -> int:
    try:
        usd_text = render_usd()
        report = build_report(usd_text)
        validate(report, usd_text)
    except (ContractError, OSError) as exc:
        print(f"invalid virtual F2 readiness contract: {exc}", file=sys.stderr)
        return 1

    expected = {OUTPUT: render_json(report), USD_OUTPUT: usd_text}
    failures: list[str] = []
    for path, content in expected.items():
        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"wrote {relative(path)}")
        elif not path.is_file():
            failures.append(f"missing generated file: {relative(path)}")
        elif path.read_text(encoding="utf-8") != content:
            failures.append(f"stale generated file: {relative(path)}")
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    if not write:
        print(f"current {relative(OUTPUT)} and {relative(USD_OUTPUT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    return run(write=args.write)


if __name__ == "__main__":
    raise SystemExit(main())
