#!/usr/bin/env python3
"""Generate a PET-linked F1 turbo heat-shield guide and thermal contract.

The only dimensional inputs are a supplier-declared product envelope and mass.
The generated cube is therefore a packaging guide, not the heat-shield surface.
All thermal, structural and manufacturing parameters remain explicit unknowns.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DECLARED_DATA = ROOT / "catalog" / "reference" / "993-declared-part-data.json"
SOURCE = (
    ROOT / "catalog" / "sources" / "src-fvd-993-turbo-heat-shield-dimensions.json"
)
PORSCHEFANATICS_SOURCE = (
    ROOT / "catalog" / "sources" / "src-porschefanatics-993-turbo-pet.json"
)
PET_INDEX = ROOT / "twins" / "pet-993" / "index-f0.json"
PROGRAM_DEFINITION = ROOT / "twins" / "vehicle-993" / "program-definition.json"
SIMREADY_PREFLIGHT = (
    ROOT / "twins" / "vehicle-993" / "functional-flow-simready-preflight-f0.json"
)
K16_REPORT = ROOT / "twins" / "catalogue-parts" / "k16-envelope-flow-readiness-f1.json"
REPORT = ROOT / "twins" / "catalogue-parts" / "turbo-heat-shield-readiness-f1.json"
SCAD_OUTPUT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering"
    / "993-turbo-heat-shield-left-guide-f1.scad"
)
USD_OUTPUT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering"
    / "993-turbo-heat-shield-left-guide-f1.usda"
)

ENTRY_ID = "993-TURBO-HEAT-SHIELD-COVER-LEFT"
OEM_REFERENCE = "99312311351"
DISPLAY_REFERENCE = "993 123 113 51"
PET_MASTER_ID = "TWIN-PET-993-PART-B6629ABCA63D241CEDCC"
DIMENSIONS_MM = [160.0, 110.0, 105.0]
MASS_KG = 0.23
EXPECTED_PHYSICSNEMO_COMMIT = "4fbfcfd62bf050b48ceec6b438da409b9f4644b3"


class ContractError(ValueError):
    """Raised when the heat-shield contract would promote unsupported evidence."""


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load:{relative(path)}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected_object:{relative(path)}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_reference(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())


def read_part_master(index: dict[str, Any]) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    shards = index.get("output", {}).get("part_master_shards", [])
    if not isinstance(shards, list) or len(shards) != 16:
        raise ContractError("pet_part_master_shards")
    for shard in shards:
        if not isinstance(shard, dict):
            raise ContractError("pet_part_master_shard")
        path_value = shard.get("path")
        expected_digest = shard.get("sha256")
        if not isinstance(path_value, str) or not isinstance(expected_digest, str):
            raise ContractError("pet_part_master_shard_identity")
        path = ROOT / path_value
        if sha256_file(path) != expected_digest:
            raise ContractError(f"pet_part_master_shard_digest:{path_value}")
        records = 0
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                records += 1
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ContractError(
                        f"pet_part_master_json:{path_value}:{line_number}:{exc}"
                    ) from exc
                if (
                    item.get("subject", {}).get("normalized_oem_reference")
                    == OEM_REFERENCE
                ):
                    matches.append(item)
        if records != shard.get("record_count"):
            raise ContractError(f"pet_part_master_shard_count:{path_value}")
    if len(matches) != 1:
        raise ContractError(f"pet_part_master_identity:{len(matches)}")
    return matches[0]


def derive() -> dict[str, Any]:
    declared = load_json(DECLARED_DATA)
    entries = [
        item
        for item in declared.get("entries", [])
        if isinstance(item, dict) and item.get("entry_id") == ENTRY_ID
    ]
    if len(entries) != 1:
        raise ContractError(f"declared_entry:{len(entries)}")
    entry = entries[0]
    expected_values = {
        "source_id": "SRC-FVD-993-TURBO-HEAT-SHIELD-DIMENSIONS",
        "dimensions_mm": DIMENSIONS_MM,
        "mass_kg": MASS_KG,
        "material": "a_determiner",
        "oem_reference": DISPLAY_REFERENCE,
        "quantity_per_car": 1,
    }
    for field, expected in expected_values.items():
        if entry.get(field) != expected:
            raise ContractError(f"declared_entry_value:{field}")

    source = load_json(SOURCE)
    if (
        source.get("source_id") != expected_values["source_id"]
        or source.get("quality", {}).get("evidence_level") != "C"
        or source.get("rights", {}).get("redistribution") != "prohibited"
    ):
        raise ContractError("supplier_source_boundary")
    porschefanatics = load_json(PORSCHEFANATICS_SOURCE)
    if (
        porschefanatics.get("source_id") != "SRC-PORSCHEFANATICS-993-TURBO-PET"
        or "oil_lines" not in porschefanatics.get("coverage", {}).get("parts", [])
    ):
        raise ContractError("porschefanatics_source")

    master = read_part_master(load_json(PET_INDEX))
    if master.get("twin_id") != PET_MASTER_ID:
        raise ContractError("pet_part_master_id")
    documentary = master.get("documentary_graph", {})
    if documentary.get("pet_illustrations") != ["202-16"]:
        raise ContractError("pet_illustration")
    occurrences = documentary.get("occurrences", [])
    if len(occurrences) != 2 or {item.get("position") for item in occurrences} != {7}:
        raise ContractError("pet_occurrences")
    observations = documentary.get("declared_engineering_observations", [])
    if not any(
        isinstance(item, dict)
        and item.get("entry_id") == ENTRY_ID
        and item.get("bounding_box_mm") == DIMENSIONS_MM
        and item.get("mass_kg") == MASS_KG
        and item.get("source_id") == expected_values["source_id"]
        for item in observations
    ):
        raise ContractError("pet_declared_observation")

    program = load_json(PROGRAM_DEFINITION)
    physicsnemo = program.get("physicsnemo_policy", {})
    if (
        physicsnemo.get("execution_enabled") is not False
        or physicsnemo.get("discovered_commit") != EXPECTED_PHYSICSNEMO_COMMIT
    ):
        raise ContractError("physicsnemo_policy")
    preflight = load_json(SIMREADY_PREFLIGHT)
    if preflight.get("status") != "blocked":
        raise ContractError("simready_preflight_must_be_reassessed")
    if preflight.get("result_boundary", {}).get("simready_validated") is not False:
        raise ContractError("simready_preflight_overclaim")
    k16 = load_json(K16_REPORT)
    if k16.get("status") != (
        "F1_K16_envelope_and_diameter_guides_complete_zeroD_execution_blocked"
    ):
        raise ContractError("upstream_k16_contract")
    return {
        "entry": entry,
        "source": source,
        "porschefanatics": porschefanatics,
        "master": master,
        "physicsnemo": physicsnemo,
        "preflight": preflight,
        "k16": k16,
    }


def render_scad() -> str:
    return """// 993 123 113 51 supplier-envelope guide; not an OEM heat-shield surface.
envelope_mm = [160.000000, 110.000000, 105.000000];
supplier_declared_mass_kg = 0.230000;

module supplier_envelope_guide() {
    cube(envelope_mm, center = true);
}

supplier_envelope_guide();
"""


def render_usd() -> str:
    return f'''#usda 1.0
(
    defaultPrim = "TurboHeatShieldLeftGuideF1"
    metersPerUnit = 0.001
    upAxis = "Z"
)

def Xform "TurboHeatShieldLeftGuideF1" (
    kind = "component"
)
{{
    custom string status = "F1_supplier_envelope_thermal_readiness_not_OEM_surface_or_SimReady"
    custom string oemReference = "{OEM_REFERENCE}"
    custom string petPartMasterTwinId = "{PET_MASTER_ID}"
    custom string dimensionalEvidence = "supplier_product_bounding_box_not_surface_thickness_mounts_or_hot_side"
    custom double supplierDeclaredMassKg = {MASS_KG:.6f}
    custom bool componentTransformIsVehicleCoordinate = false
    custom bool interfaceGeometryPresent = false
    custom bool analysisGeometryAvailable = false
    custom bool materialAssigned = false
    custom bool physicsAssigned = false
    custom bool simReadyValidated = false

    def Cube "BoundingEnvelopeGuide"
    {{
        double size = 1
        uniform token purpose = "guide"
        double3 xformOp:scale = ({DIMENSIONS_MM[0]:.6f}, {DIMENSIONS_MM[1]:.6f}, {DIMENSIONS_MM[2]:.6f})
        uniform token[] xformOpOrder = ["xformOp:scale"]
    }}
}}
'''


def unknown_parameter(
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


def source_entry(path: Path, role: str) -> dict[str, str]:
    return {"path": relative(path), "sha256": sha256_file(path), "role": role}


def build_report(data: dict[str, Any], scad_text: str, usd_text: str) -> dict[str, Any]:
    envelope_volume_m3 = math.prod(value / 1000.0 for value in DIMENSIONS_MM)
    parameters = [
        unknown_parameter("HS-GEO-001", "formed_surface_and_edge_profile", "mm", ["package", "thermal", "structural"]),
        unknown_parameter("HS-GEO-002", "sheet_or_laminate_thickness_map", "mm", ["thermal", "structural", "mass"]),
        unknown_parameter("HS-GEO-003", "mounting_hole_slot_and_bracket_coordinates", "mm", ["package", "structural"]),
        unknown_parameter("HS-GEO-004", "hot_source_to_shield_gap_map", "mm", ["radiation", "convection", "package"]),
        unknown_parameter("HS-GEO-005", "shield_to_protected_components_clearance", "mm", ["package", "acceptance"]),
        unknown_parameter("HS-GEO-006", "radiative_view_factor_map", None, ["radiation"]),
        unknown_parameter("HS-BC-001", "hot_gas_or_turbine_surface_temperature_history", "degC", ["thermal"]),
        unknown_parameter("HS-BC-002", "hot_side_convection_coefficient", "W_m2_K", ["thermal"]),
        unknown_parameter("HS-BC-003", "cold_side_ambient_temperature_history", "degC", ["thermal"]),
        unknown_parameter("HS-BC-004", "cold_side_convection_coefficient", "W_m2_K", ["thermal"]),
        unknown_parameter("HS-BC-005", "mount_contact_conductance", "W_m2_K", ["thermal"]),
        unknown_parameter("HS-BC-006", "engine_vibration_and_shock_spectrum", None, ["structural", "fatigue"]),
        unknown_parameter("HS-MAT-001", "density", "kg_m3", ["mass", "structural"]),
        unknown_parameter("HS-MAT-002", "temperature_dependent_specific_heat", "J_kg_K", ["thermal"]),
        unknown_parameter("HS-MAT-003", "temperature_dependent_thermal_conductivity", "W_m_K", ["thermal"]),
        unknown_parameter("HS-MAT-004", "temperature_dependent_emissivity_each_face", None, ["radiation"]),
        unknown_parameter("HS-MAT-005", "temperature_dependent_elastic_plastic_curve", None, ["structural"]),
        unknown_parameter("HS-MAT-006", "thermal_expansion_coefficient", "K_inv", ["structural"]),
        unknown_parameter("HS-MAT-007", "fatigue_creep_oxidation_and_corrosion_data", None, ["durability"]),
        unknown_parameter("HS-MAT-008", "coating_or_insulation_stack_and_ageing", None, ["thermal", "durability"]),
        unknown_parameter("HS-ACC-001", "maximum_protected_component_temperature", "degC", ["acceptance"]),
        unknown_parameter("HS-ACC-002", "maximum_shield_temperature", "degC", ["acceptance"]),
        unknown_parameter("HS-ACC-003", "minimum_hot_and_cold_clearance", "mm", ["acceptance"]),
        unknown_parameter("HS-ACC-004", "stress_buckling_and_deflection_limits", None, ["acceptance"]),
        unknown_parameter("HS-ACC-005", "fatigue_and_thermal_cycle_life_target", "cycles", ["acceptance"]),
    ]
    return {
        "$comment": (
            "Guide F1 et contrat thermique du couvercle 993 123 113 51. "
            "L'enveloppe et la masse fournisseur ne definissent ni la forme ni le materiau."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "status": "F1_turbo_heat_shield_envelope_thermal_readiness_complete_reference_solution_blocked",
        "source_boundary": {
            "files": [
                source_entry(DECLARED_DATA, "structured_supplier_envelope_and_mass"),
                source_entry(SOURCE, "supplier_page_provenance_and_rights"),
                source_entry(PORSCHEFANATICS_SOURCE, "PorscheFanatics_PET_202_16_identity_context"),
                source_entry(PET_INDEX, "PET_part_master_shard_manifest"),
                source_entry(PROGRAM_DEFINITION, "PhysicsNeMo_and_Omniverse_policy"),
                source_entry(SIMREADY_PREFLIGHT, "blocked_Omniverse_preflight"),
                source_entry(K16_REPORT, "adjacent_turbo_contract_without_spatial_transfer"),
            ],
            "third_party_photograph_or_geometry_redistributed": False,
            "llm_generated_dimensions_used": False,
            "independent_metrology_used": False,
            "porschefanatics_used_for_identity_and_system_context_only": True,
        },
        "subject": {
            "entry_id": ENTRY_ID,
            "oem_reference": OEM_REFERENCE,
            "display_reference": DISPLAY_REFERENCE,
            "pet_part_master_twin_id": PET_MASTER_ID,
            "pet_illustration": "202-16",
            "pet_position": 7,
            "quantity_per_car": 1,
            "side": "left_as_declared_by_supplier_not_vehicle_positioned",
        },
        "summary": {
            "pet_linked_component_guides": 1,
            "pet_linked_part_masters": 1,
            "supplier_declared_bounding_boxes": 1,
            "supplier_declared_mass_observations": 1,
            "symbolic_thermal_equation_contracts": 7,
            "blocked_reference_load_cases": 4,
            "unknown_engineering_parameters": len(parameters),
            "evaluated_thermal_operating_points": 0,
            "selected_interface_coordinates": 0,
            "qualified_material_decisions": 0,
            "reference_solver_results": 0,
            "physicsnemo_results": 0,
            "simready_assets": 0,
            "manufacturing_releases": 0,
        },
        "documentary_inputs": {
            "supplier_declared_bounding_box_mm": DIMENSIONS_MM,
            "supplier_declared_mass_kg": MASS_KG,
            "bounding_box_volume_m3": envelope_volume_m3,
            "mass_divided_by_bounding_box_volume_kg_m3": MASS_KG / envelope_volume_m3,
            "quotient_semantics": "packaging_arithmetic_only_not_material_density_or_solid_volume",
            "material_label": None,
            "surface_thickness_and_mount_geometry": None,
        },
        "interface_hypotheses": {
            "status": "LLM_assisted_topology_hypothesis_requires_engineering_review",
            "nodes": [
                "left_K16_hot_source_unknown_surface",
                "left_heat_shield_unknown_formed_surface",
                "protected_component_zone_unknown_membership",
                "engine_bay_ambient_unknown_flow_field",
                "unknown_mounting_interfaces",
            ],
            "edges": [
                "hot_source_radiation_and_convection_to_shield_hypothesis",
                "shield_conduction_and_reradiation_to_protected_zone_hypothesis",
                "mount_conduction_to_support_structure_hypothesis",
            ],
            "upstream_k16_contract": relative(K16_REPORT),
            "known_vehicle_transform_count": 0,
            "known_interface_coordinate_count": 0,
            "topology_is_not_packaging_fitment_or_thermal_proof": True,
        },
        "parameter_registry": parameters,
        "thermal_model": {
            "status": "symbolic_contracts_only_no_operating_point_evaluated",
            "equations": [
                {"id": "hot_side_radiation", "equation": "Qdot_rad_hot = F_hot_shield*epsilon_eff*sigma*A_hot*(T_hot^4-T_shield_hot^4)", "missing": ["view_factor_map", "emissivities", "hot_surface_area", "temperature_history"]},
                {"id": "hot_side_convection", "equation": "Qdot_conv_hot = h_hot*A_hot*(T_gas-T_shield_hot)", "missing": ["h_hot", "hot_surface_area", "gas_temperature_history"]},
                {"id": "through_thickness_conduction", "equation": "Qdot_cond = integral_A(k(T)/t(x,y)*(T_hot_face-T_cold_face))dA", "missing": ["formed_surface", "thickness_map", "k(T)"]},
                {"id": "cold_side_rejection", "equation": "Qdot_cold = h_cold*A_cold*(T_cold-T_ambient)+epsilon_cold*sigma*A_cold*(T_cold^4-T_surroundings^4)", "missing": ["h_cold", "cold_surface_area", "emissivity", "ambient_and_surroundings_temperature"]},
                {"id": "transient_energy_balance", "equation": "m*cp(T)*dTbar/dt = Qdot_rad_hot+Qdot_conv_hot-Qdot_cold-Qdot_mount", "missing": ["cp(T)", "temperature_field", "mount_contact_conductance", "boundary_histories"]},
                {"id": "free_thermal_expansion", "equation": "delta_L = alpha(T)*L*delta_T", "missing": ["alpha(T)", "formed_lengths", "temperature_field"]},
                {"id": "conditional_fully_restrained_stress", "equation": "sigma_th = E(T)*alpha(T)*delta_T/(1-nu(T))", "missing": ["restraint_state", "E(T)", "alpha(T)", "nu(T)", "temperature_field"], "use_boundary": "screening_upper_bound_only_not_component_stress_solution"},
            ],
            "operating_point_available": False,
            "reference_solver_credit": False,
            "thermal_solution_credit": False,
            "required_first_reference_methods": [
                "view_factor_and_lumped_thermal_network_after_F2_surfaces_gaps_and_material_properties",
                "mesh_converged_conduction_radiation_convection_CHT_after_F3_domains",
                "thermomechanical_buckling_modal_and_fatigue_analysis_after_mount_and_material_definition",
            ],
        },
        "load_cases": [
            {"id": "LC-993-HS-STEADY-HOT", "kind": "steady_hot_side", "status": "blocked", "missing_parameter_ids": ["HS-GEO-001", "HS-GEO-002", "HS-GEO-004", "HS-GEO-006", "HS-BC-001", "HS-BC-002", "HS-BC-003", "HS-BC-004", "HS-MAT-002", "HS-MAT-003", "HS-MAT-004", "HS-ACC-001", "HS-ACC-002"]},
            {"id": "LC-993-HS-TRANSIENT-SOAK", "kind": "turbo_heat_soak_transient", "status": "blocked", "missing_parameter_ids": ["HS-BC-001", "HS-BC-003", "HS-BC-005", "HS-MAT-002", "HS-MAT-003", "HS-MAT-004", "HS-ACC-001", "HS-ACC-002"]},
            {"id": "LC-993-HS-THERMAL-SHOCK", "kind": "thermal_cycle_and_shock", "status": "blocked", "missing_parameter_ids": ["HS-GEO-002", "HS-GEO-003", "HS-MAT-005", "HS-MAT-006", "HS-MAT-007", "HS-ACC-004", "HS-ACC-005"]},
            {"id": "LC-993-HS-VIBRATION-DURABILITY", "kind": "engine_vibration_thermal_fatigue", "status": "blocked", "missing_parameter_ids": ["HS-GEO-001", "HS-GEO-002", "HS-GEO-003", "HS-BC-006", "HS-MAT-005", "HS-MAT-007", "HS-ACC-003", "HS-ACC-004", "HS-ACC-005"]},
        ],
        "material_and_manufacturing_route": {
            "status": "LLM_screening_hypotheses_only_no_selection",
            "candidate_matrix": [
                {"candidate_family": "temperature_resistant_steel_sheet_system", "candidate_process": "sheet_forming_trimming_and_joining", "unresolved_failure_modes": ["oxidation", "thermal_fatigue", "mass", "coating_durability"], "status": "unsourced_unselected"},
                {"candidate_family": "ferritic_or_austenitic_stainless_sheet_system", "candidate_process": "sheet_forming_trimming_and_joining", "unresolved_failure_modes": ["thermal_fatigue", "distortion", "mass", "galvanic_compatibility"], "status": "unsourced_unselected"},
                {"candidate_family": "nickel_alloy_sheet_system", "candidate_process": "sheet_forming_trimming_and_joining", "unresolved_failure_modes": ["cost", "mass", "formability", "joining"], "status": "unsourced_unselected"},
                {"candidate_family": "metal_skin_with_high_temperature_insulation_stack", "candidate_process": "formed_skin_plus_retained_insulation", "unresolved_failure_modes": ["fibre_or_layer_retention", "moisture", "erosion", "serviceability"], "status": "unsourced_unselected"},
            ],
            "selected_material_count": 0,
            "selected_functional_manufacturing_route_count": 0,
            "additive_route_disposition": "not_preferred_without_evidence_thin_sheet_forming_is_the_first_process_hypothesis",
            "CNC_route_disposition": "cutting_and_tooling_may_support_sheet_process_but_billet_machining_is_not_selected",
            "release": "prohibited_pending_F2_F3_thermal_environment_material_durability_fastener_clearance_and_professional_review",
        },
        "physicsnemo_discovery": {
            "canonical_repository": data["physicsnemo"].get("canonical_repository"),
            "commit": data["physicsnemo"].get("discovered_commit"),
            "paths_verified_live_during_authoring": True,
            "local_revalidation_required_before_execution": True,
            "problem_shape": "future_unstructured_surface_and_volume_thermal_CHT_fields_conditioned_on_geometry_and_boundary_cases",
            "model_menu": [
                {"model": "DoMINO", "path": "physicsnemo/models/domino", "role": "candidate_surface_and_volume_CHT_surrogate_after_reference_dataset", "selected": False},
                {"model": "GeoTransolver", "path": "physicsnemo/models/geotransolver", "role": "candidate_geometry_aware_field_surrogate_on_general discretizations", "selected": False},
                {"model": "Transolver", "path": "physicsnemo/models/transolver", "role": "candidate_PDE_field_surrogate_on_structured_or_unstructured_meshes", "selected": False},
                {"model": "MeshGraphNet", "path": "physicsnemo/models/meshgraphnet", "role": "candidate_graph_mesh thermomechanical_or flow field surrogate requiring a custom formulation", "selected": False},
            ],
            "datapipe_menu": [
                {"datapipe": "DoMINODataPipe", "path": "physicsnemo/datapipes/cae/domino_datapipe.py", "role": "surface_volume_or_combined_CAE_preprocessing"},
                {"datapipe": "TransolverDataPipe", "path": "physicsnemo/datapipes/cae/transolver_datapipe.py", "role": "surface_or_volume_mesh_field_preprocessing"},
            ],
            "reference_examples": [
                {"path": "examples/cfd/transient_conjugate_heat_transfer_tank_fill", "role": "closest_transient_CHT_DoMINO_instantiation_but_not_a_turbo_heat_shield_validation"},
                {"path": "examples/cfd/stokes_mgn", "role": "mesh_graph_field_learning_reference_not_a_thermal_component_recipe"},
            ],
            "execution_enabled": False,
            "eligibility_gate": "F3_solid_and_fluid_domains_plus_converged_radiation_CHT_thermomechanical_dataset_with_held_out_geometries_and_load_cases",
        },
        "omniverse_handoff": {
            "openusd_source_authoring": "completed_as_one_envelope_guide",
            "property_assignment_intent": "run",
            "preflight_report": relative(SIMREADY_PREFLIGHT),
            "preflight_status": data["preflight"].get("status"),
            "preflight_blockers": data["preflight"].get("blockers", []),
            "guide_composed_into_vehicle": False,
            "vehicle_transform_known": False,
            "material_and_physics_assignment": "not_run_preflight_blocked",
            "nvidia_asset_validator": "not_run_preflight_blocked",
            "simready_foundation": "not_run_preflight_blocked",
            "simready_validated": False,
        },
        "assets": {
            "editable_scad": relative(SCAD_OUTPUT),
            "editable_scad_sha256": sha256_text(scad_text),
            "openusd_guide": relative(USD_OUTPUT),
            "openusd_guide_sha256": sha256_text(usd_text),
            "openusd_component_prim_count": 1,
            "openusd_guide_primitive_count": 1,
            "openusd_physics_schema_count": 0,
            "openusd_material_binding_count": 0,
        },
        "claim_boundary": {
            "is_complete_OEM_geometry": False,
            "is_F2_interface_geometry": False,
            "is_F3_analysis_geometry": False,
            "is_dimensionally_accurate_part_shape": False,
            "is_vehicle_positioned_or_fitment_validated": False,
            "is_qualified_material_selection": False,
            "is_evaluated_thermal_operating_point": False,
            "is_reference_thermal_CHT_or_thermomechanical_result": False,
            "is_physicsnemo_result": False,
            "is_simready_validated": False,
            "is_manufacturing_or_vehicle_release": False,
        },
        "next_gate": "resolve_Turbo_GT2_applicability_then_infer_and_cross_check_F2_surface_mount_gap_clearance_and_material_hypotheses",
    }


def validate(
    data: dict[str, Any], scad_text: str, usd_text: str, report: dict[str, Any]
) -> None:
    if report.get("status") != (
        "F1_turbo_heat_shield_envelope_thermal_readiness_complete_reference_solution_blocked"
    ):
        raise ContractError("status")
    summary = report.get("summary", {})
    expected_summary = {
        "pet_linked_component_guides": 1,
        "pet_linked_part_masters": 1,
        "supplier_declared_bounding_boxes": 1,
        "supplier_declared_mass_observations": 1,
        "symbolic_thermal_equation_contracts": 7,
        "blocked_reference_load_cases": 4,
        "unknown_engineering_parameters": 25,
        "evaluated_thermal_operating_points": 0,
        "selected_interface_coordinates": 0,
        "qualified_material_decisions": 0,
        "reference_solver_results": 0,
        "physicsnemo_results": 0,
        "simready_assets": 0,
        "manufacturing_releases": 0,
    }
    if summary != expected_summary:
        raise ContractError(f"summary:{summary}")
    parameters = report.get("parameter_registry", [])
    if len(parameters) != 25 or any(
        item.get("value") is not None or item.get("uncertainty") is not None
        for item in parameters
    ):
        raise ContractError("parameter_registry")
    if len(report.get("thermal_model", {}).get("equations", [])) != 7:
        raise ContractError("thermal_equations")
    if report.get("thermal_model", {}).get("reference_solver_credit") is not False:
        raise ContractError("reference_solver_overclaim")
    if len(report.get("load_cases", [])) != 4 or any(
        item.get("status") != "blocked" for item in report.get("load_cases", [])
    ):
        raise ContractError("load_cases")
    if report.get("material_and_manufacturing_route", {}).get("selected_material_count") != 0:
        raise ContractError("material_overclaim")
    if report.get("physicsnemo_discovery", {}).get("execution_enabled") is not False:
        raise ContractError("physicsnemo_execution")
    if {item.get("model") for item in report["physicsnemo_discovery"]["model_menu"]} != {
        "DoMINO", "GeoTransolver", "Transolver", "MeshGraphNet"
    }:
        raise ContractError("physicsnemo_model_menu")
    if report.get("omniverse_handoff", {}).get("simready_validated") is not False:
        raise ContractError("simready_overclaim")
    if usd_text.count('kind = "component"') != 1 or usd_text.count('purpose = "guide"') != 1:
        raise ContractError("usd_guide_counts")
    for prohibited in (
        "UsdPhysics", "RigidBodyAPI", "CollisionAPI", "MassAPI", "MaterialBindingAPI"
    ):
        if prohibited in usd_text:
            raise ContractError(f"usd_overclaim:{prohibited}")
    if any(value is not False for value in report.get("claim_boundary", {}).values()):
        raise ContractError("claim_boundary")
    assets = report.get("assets", {})
    if assets.get("editable_scad_sha256") != sha256_text(scad_text):
        raise ContractError("scad_digest")
    if assets.get("openusd_guide_sha256") != sha256_text(usd_text):
        raise ContractError("usd_digest")


def render_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    args = parser.parse_args(argv)
    try:
        data = derive()
        scad_text = render_scad()
        usd_text = render_usd()
        report = build_report(data, scad_text, usd_text)
        validate(data, scad_text, usd_text, report)
        expected = {
            REPORT: render_json(report),
            SCAD_OUTPUT: scad_text,
            USD_OUTPUT: usd_text,
        }
        if args.write:
            for path, content in expected.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                print(f"wrote {relative(path)}")
            return 0
        for path, content in expected.items():
            if not path.is_file():
                print(f"missing:{relative(path)}")
                return 1
            if args.check and path.read_text(encoding="utf-8") != content:
                print(f"stale:{relative(path)}")
                return 1
        validate(
            data,
            SCAD_OUTPUT.read_text(encoding="utf-8"),
            USD_OUTPUT.read_text(encoding="utf-8"),
            load_json(REPORT),
        )
        print(f"current {relative(REPORT)}: 1 PET-linked heat-shield guide")
        return 0
    except (ContractError, OSError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
