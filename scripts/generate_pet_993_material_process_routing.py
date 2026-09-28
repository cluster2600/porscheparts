#!/usr/bin/env python3
"""Generate fail-closed material, process and reference-model routes for PET 993.

The routing covers every PET part master but deliberately stops before selecting a
material, manufacturing process, solver result, PhysicsNeMo model or release.  It
uses archetype hypotheses as a triage key; those hypotheses are not geometry or
human-reviewed part classification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
READINESS_INDEX = ROOT / "twins" / "pet-993" / "engineering-readiness-f0.json"
PORSCHEFANATICS_CROSSWALK = (
    ROOT / "twins" / "pet-993" / "porschefanatics-crosswalk-f0.json"
)
PROGRAM_DEFINITION = ROOT / "twins" / "vehicle-993" / "program-definition.json"
OUTPUT = ROOT / "twins" / "pet-993" / "material-process-routing-f0.json"
WORK_ROOT = ROOT / "work" / "pet-993" / "material-process-routing"
SHARD_IDS = tuple("0123456789abcdef")


class ContractError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected_object:{path}")
    return value


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def render_jsonl(values: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(value, sort_keys=True, ensure_ascii=False) + "\n"
        for value in values
    )


GROUP_SPECS: dict[str, dict[str, Any]] = {
    "bearing_tribology": {
        "materials": [
            "oem_material_to_identify",
            "bearing_steel_family_candidate",
            "copper_alloy_family_candidate",
            "engineering_polymer_family_candidate",
        ],
        "routes": ["usinage_CNC", "fonderie_ou_forge"],
        "disposition": "candidate_part_manufacture_after_F3_and_tribology_definition",
        "properties": [
            "elasticity_and_yield",
            "contact_fatigue",
            "friction_and_wear",
            "lubricant_compatibility",
            "thermal_expansion",
        ],
    },
    "body_structure": {
        "materials": [
            "oem_material_to_identify",
            "steel_sheet_family_candidate",
            "aluminum_sheet_family_candidate",
            "fiber_composite_family_candidate",
        ],
        "routes": [
            "tolerie_et_soudage",
            "fonderie_ou_forge",
            "fabrication_additive_polymere",
            "fabrication_additive_metal",
        ],
        "disposition": "mixed_manufacture_candidates_after_body_F3_and_crash_model",
        "properties": [
            "orthotropic_or_isotropic_constitutive_model",
            "yield_failure_and_damage",
            "fatigue",
            "joining_and_heat_affected_zone",
            "corrosion_and_galvanic_compatibility",
        ],
    },
    "brake_safety": {
        "materials": [
            "oem_material_to_identify",
            "cast_iron_or_steel_family_candidate",
            "aluminum_housing_family_candidate",
            "friction_material_system_to_identify",
        ],
        "routes": ["usinage_CNC", "fonderie_ou_forge"],
        "disposition": "safety_critical_manufacture_or_procurement_after_F3_and_professional_review",
        "properties": [
            "temperature_dependent_friction",
            "thermal_capacity_and_conductivity",
            "elasticity_and_yield",
            "fatigue_and_thermal_shock",
            "fluid_compatibility",
        ],
    },
    "electrical_control": {
        "materials": [
            "oem_component_material_stack_to_identify",
            "copper_conductor_family_candidate",
            "electrical_grade_polymer_family_candidate",
        ],
        "routes": ["fabrication_additive_polymere"],
        "disposition": "qualified_supplier_first_additive_route_limited_to_nonfunctional_housing_prototype",
        "properties": [
            "electrical_resistivity_and_insulation",
            "temperature_rating",
            "flammability_and_smoke",
            "connector_contact_and_sealing",
            "emc_and_control_logic",
        ],
    },
    "elastomer_sealing": {
        "materials": [
            "oem_elastomer_to_identify",
            "elastomer_family_candidate",
            "thermoplastic_elastomer_family_candidate",
            "fluoropolymer_family_candidate",
        ],
        "routes": ["fabrication_additive_polymere"],
        "disposition": "material_specific_molding_or_supplier_route_required_additive_prototype_only",
        "properties": [
            "hyperelasticity_and_viscoelasticity",
            "compression_set",
            "fatigue_and_tear",
            "temperature_range",
            "fluid_permeation_and_chemical_compatibility",
        ],
    },
    "fluid_thermal": {
        "materials": [
            "oem_material_to_identify",
            "fluid_compatible_elastomer_family_candidate",
            "engineering_polymer_family_candidate",
            "aluminum_or_steel_family_candidate",
        ],
        "routes": [
            "usinage_CNC",
            "fonderie_ou_forge",
            "fabrication_additive_polymere",
            "fabrication_additive_metal",
        ],
        "disposition": "mixed_manufacture_or_supplier_candidates_after_pressure_temperature_and_media_definition",
        "properties": [
            "pressure_temperature_envelope",
            "thermal_conductivity_and_expansion",
            "roughness_and_flow_loss",
            "creep_fatigue_and_burst",
            "fluid_compatibility_and_permeation",
        ],
    },
    "generic_mixed": {
        "materials": [
            "oem_material_to_identify",
            "steel_family_candidate",
            "aluminum_family_candidate",
            "engineering_polymer_family_candidate",
        ],
        "routes": [
            "usinage_CNC",
            "tolerie_et_soudage",
            "fonderie_ou_forge",
            "fabrication_additive_polymere",
            "fabrication_additive_metal",
        ],
        "disposition": "classification_or_decomposition_required_before_route_selection",
        "properties": [
            "density",
            "elasticity_and_strength",
            "temperature_range",
            "fatigue_creep_or_wear_by_failure_mode",
            "environmental_compatibility",
        ],
    },
    "glazing_optical": {
        "materials": [
            "oem_glazing_specification_to_identify",
            "automotive_glass_family_candidate",
            "optical_polycarbonate_family_candidate",
        ],
        "routes": ["fabrication_additive_polymere"],
        "disposition": "qualified_supplier_first_additive_route_limited_to_fit_or_tooling_proxy",
        "properties": [
            "optical_transmission_and_distortion",
            "impact_and_fragmentation_behavior",
            "scratch_and_uv_resistance",
            "thermal_expansion",
            "regulatory_glazing_requirements",
        ],
    },
    "insulation_trim": {
        "materials": [
            "oem_material_to_identify",
            "thermoplastic_or_thermoset_family_candidate",
            "fiber_or_foam_insulation_family_candidate",
            "thin_metal_heat_shield_family_candidate",
        ],
        "routes": [
            "tolerie_et_soudage",
            "fabrication_additive_polymere",
            "fabrication_additive_metal",
        ],
        "disposition": "mixed_manufacture_or_supplier_candidates_after_cabin_fire_and_temperature_definition",
        "properties": [
            "thermal_and_acoustic_response",
            "flammability_and_smoke",
            "creep_and_uv_aging",
            "moisture_and_chemical_resistance",
            "surface_and_attachment_behavior",
        ],
    },
    "label_service": {
        "materials": ["exact_oem_or_service_specification_to_identify"],
        "routes": [],
        "disposition": "specification_or_qualified_supplier_item_not_part_geometry",
        "properties": [
            "identity_and_specification",
            "temperature_and_chemical_compatibility",
            "aging_and_legibility",
            "application_or_service_procedure",
        ],
    },
    "polymer_trim": {
        "materials": [
            "oem_polymer_to_identify",
            "engineering_thermoplastic_family_candidate",
            "thermoset_family_candidate",
            "fiber_reinforced_polymer_family_candidate",
        ],
        "routes": ["fabrication_additive_polymere"],
        "disposition": "additive_prototype_candidate_production_route_requires_process_specific_qualification",
        "properties": [
            "anisotropic_process_dependent_stiffness",
            "creep_and_snap_fit_fatigue",
            "heat_deflection_temperature",
            "flammability_uv_and_chemical_aging",
            "surface_finish_and_dimensional_stability",
        ],
    },
    "rigid_mechanical": {
        "materials": [
            "oem_material_to_identify",
            "steel_family_candidate",
            "aluminum_alloy_family_candidate",
            "engineering_polymer_family_candidate",
        ],
        "routes": [
            "usinage_CNC",
            "tolerie_et_soudage",
            "fonderie_ou_forge",
            "fabrication_additive_polymere",
            "fabrication_additive_metal",
        ],
        "disposition": "candidate_part_manufacture_after_F3_reference_analysis",
        "properties": [
            "density_elasticity_and_poisson_ratio",
            "yield_and_ultimate_strength",
            "fatigue_and_notch_sensitivity",
            "thermal_expansion",
            "corrosion_wear_and_galvanic_compatibility",
        ],
    },
    "rotating_hot": {
        "materials": [
            "oem_material_to_identify",
            "heat_resistant_steel_family_candidate",
            "nickel_superalloy_family_candidate",
            "titanium_family_candidate_with_extra_controls",
        ],
        "routes": ["usinage_CNC", "fonderie_ou_forge", "fabrication_additive_metal"],
        "disposition": "high_energy_rotating_or_hot_part_requires_F3_reference_analysis_and_professional_review",
        "properties": [
            "temperature_dependent_strength",
            "low_and_high_cycle_fatigue",
            "creep_and_oxidation",
            "fracture_and_defect_tolerance",
            "rotordynamic_mass_balance_and_thermal_growth",
        ],
    },
    "spring_compliant": {
        "materials": [
            "oem_material_to_identify",
            "spring_steel_family_candidate",
            "elastomer_family_candidate",
            "fiber_composite_spring_family_candidate",
        ],
        "routes": ["fonderie_ou_forge", "fabrication_additive_polymere", "fabrication_additive_metal"],
        "disposition": "candidate_manufacture_after_cycle_load_and_relaxation_definition",
        "properties": [
            "cyclic_stress_strain",
            "fatigue_and_relaxation",
            "temperature_dependent_stiffness",
            "surface_and_residual_stress",
            "environmental_aging",
        ],
    },
    "suspension_steering": {
        "materials": [
            "oem_material_to_identify",
            "high_strength_steel_family_candidate",
            "aluminum_alloy_family_candidate",
            "titanium_family_candidate_with_extra_controls",
        ],
        "routes": ["usinage_CNC", "fonderie_ou_forge", "fabrication_additive_metal"],
        "disposition": "safety_critical_manufacture_after_F3_fatigue_vehicle_dynamics_and_professional_review",
        "properties": [
            "yield_ultimate_and_buckling",
            "variable_amplitude_fatigue",
            "joint_contact_and_bearing",
            "fracture_and_defect_tolerance",
            "corrosion_and_galvanic_compatibility",
        ],
    },
}


ARCHETYPE_GROUP: dict[str, str] = {
    "bearing_or_bushing": "bearing_tribology",
    "body_panel_or_external_structure": "body_structure",
    "brake_hydraulic_friction_component": "brake_safety",
    "cover_cap_or_trim": "polymer_trim",
    "elastomer_mount_buffer_or_grommet": "elastomer_sealing",
    "fastener_or_retainer": "rigid_mechanical",
    "filter_screen_or_flow_conditioner": "fluid_thermal",
    "fluid_hose_pipe_or_duct": "fluid_thermal",
    "fuel_exhaust_or_emissions_component": "fluid_thermal",
    "generic_rigid_interface_piece": "generic_mixed",
    "generic_system_0xx_service_or_documentation": "label_service",
    "generic_system_1xx_engine_component": "generic_mixed",
    "generic_system_2xx_fuel_exhaust_component": "fluid_thermal",
    "generic_system_3xx_transmission_component": "generic_mixed",
    "generic_system_4xx_front_axle_steering_component": "suspension_steering",
    "generic_system_5xx_rear_axle_driveline_component": "suspension_steering",
    "generic_system_6xx_brake_hydraulic_component": "brake_safety",
    "generic_system_7xx_controls_pedals_clutch_component": "generic_mixed",
    "generic_system_8xx_body_cabin_electrical_component": "generic_mixed",
    "generic_system_9xx_option_accessory_component": "generic_mixed",
    "glazing_mirror_or_optical_component": "glazing_optical",
    "guide_rail_slide_or_hinge": "rigid_mechanical",
    "heat_exchanger_or_cooler": "fluid_thermal",
    "housing_case_or_manifold": "rigid_mechanical",
    "hvac_or_cabin_thermal_component": "fluid_thermal",
    "instrument_gauge_or_display_component": "electrical_control",
    "insulation_absorber_or_heat_shield": "insulation_trim",
    "joint_coupling_or_flange": "rigid_mechanical",
    "label_decal_film_or_trim_item": "label_service",
    "linkage_lever_cable_or_control": "rigid_mechanical",
    "load_bearing_bracket_carrier_or_mount": "rigid_mechanical",
    "pump_valve_or_injector": "fluid_thermal",
    "rotating_powertrain_component": "rotating_hot",
    "seal_gasket_or_boot": "elastomer_sealing",
    "seat_restraint_or_occupant_structure": "body_structure",
    "sensor_actuator_or_electrical_component": "electrical_control",
    "service_material_chemical_or_kit": "label_service",
    "shim_spacer_or_alignment_component": "rigid_mechanical",
    "spring_belt_or_compliant_mechanism": "spring_compliant",
    "structural_reinforcement_member_or_plate": "body_structure",
    "turbocharger_rotating_hot_flow_assembly": "rotating_hot",
    "wheel_suspension_or_steering_component": "suspension_steering",
}


def load_readiness_tasks(index: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    shards = index.get("output", {}).get("shards", [])
    if not isinstance(shards, list) or len(shards) != len(SHARD_IDS):
        raise ContractError("readiness_shard_count")
    by_shard: dict[str, list[dict[str, Any]]] = {}
    for expected_id, item in zip(SHARD_IDS, shards):
        if not isinstance(item, dict) or item.get("shard_id") != expected_id:
            raise ContractError(f"readiness_shard_order:{expected_id}")
        path = ROOT / str(item.get("path", ""))
        if not path.is_file() or sha256_file(path) != item.get("sha256"):
            raise ContractError(f"readiness_shard_digest:{expected_id}")
        tasks = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(tasks) != item.get("record_count"):
            raise ContractError(f"readiness_shard_records:{expected_id}")
        by_shard[expected_id] = tasks
    return by_shard


def load_commercial_alternative_links() -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    manifest = load_json(PORSCHEFANATICS_CROSSWALK)
    output = manifest.get("output", {})
    path = ROOT / str(output.get("detailed_crosswalk", ""))
    if not path.is_file() or sha256_file(path) != output.get("sha256"):
        raise ContractError("porschefanatics_crosswalk_output_digest")
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(records) != output.get("record_count"):
        raise ContractError("porschefanatics_crosswalk_record_count")
    by_master: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        master_id = str(record.get("part_master_twin_id", ""))
        if not master_id:
            raise ContractError("porschefanatics_crosswalk_master_id")
        by_master.setdefault(master_id, []).append(record)
    for values in by_master.values():
        values.sort(key=lambda item: str(item.get("link_id")))
    return by_master, manifest


def reference_routes(
    domain_ids: list[str], domains: dict[str, Any]
) -> list[dict[str, Any]]:
    result = []
    for domain_id in sorted(str(value) for value in domain_ids):
        contract = domains.get(domain_id)
        if not isinstance(contract, dict):
            raise ContractError(f"unknown_simulation_domain:{domain_id}")
        result.append(
            {
                "domain_id": domain_id,
                "reference_method": contract.get("reference_method"),
                "required_geometry_or_inputs": contract.get("required_geometry"),
                "reference_solver_status": "not_run",
            }
        )
    return result


def build_route(
    task: dict[str, Any],
    domains: dict[str, Any],
    material_policy: dict[str, Any],
    titanium_requirements: list[str],
    commercial_links: list[dict[str, Any]],
) -> dict[str, Any]:
    engineering_route = task.get("engineering_route", {})
    risk = task.get("risk_and_priority", {})
    archetype = str(engineering_route.get("engineering_archetype", ""))
    group_id = ARCHETYPE_GROUP.get(archetype)
    if group_id is None:
        raise ContractError(f"unrouted_archetype:{archetype}")
    profile = GROUP_SPECS[group_id]
    material_candidates = list(profile["materials"])
    process_candidates = list(profile["routes"])
    titanium_candidate = any("titanium" in value for value in material_candidates)
    commercial_process_ids = sorted(
        {
            str(item.get("porschefanatics_record", {}).get("manufacturing_process_id"))
            for item in commercial_links
            if item.get("porschefanatics_record", {}).get("manufacturing_process_id")
        }
    )
    unqualified_material_labels = sorted(
        {
            str(value)
            for item in commercial_links
            for value in item.get("porschefanatics_record", {}).get(
                "material_ids_without_qualified_basis", []
            )
        }
    )
    return {
        "screening_task_id": "MPR-" + str(task.get("engineering_task_id", "")),
        "part_master_twin_id": task.get("part_master_twin_id"),
        "engineering_task_id": task.get("engineering_task_id"),
        "source_archetype": {
            "engineering_archetype": archetype,
            "classification_rule_id": engineering_route.get("classification_rule_id"),
            "classification_confidence": engineering_route.get(
                "classification_confidence"
            ),
            "human_reviewed_classification": engineering_route.get(
                "human_reviewed_classification"
            ),
        },
        "routing_profile": {
            "group_id": group_id,
            "disposition": profile["disposition"],
            "candidate_material_families": material_candidates,
            "candidate_manufacturing_routes": process_candidates,
            "required_property_models": list(profile["properties"]),
            "titanium_extra_requirements": (
                titanium_requirements if titanium_candidate else []
            ),
        },
        "reference_model_routes": reference_routes(
            engineering_route.get("simulation_domain_ids", []), domains
        ),
        "physicsnemo_route": {
            "candidate_models": list(
                engineering_route.get("physicsnemo_candidate_models", [])
            ),
            "selected_model": None,
            "reference_dataset_status": "missing_converged_reference_solver_samples",
            "execution_enabled": False,
        },
        "commercial_alternative_evidence": {
            "exact_replacement_link_count": len(commercial_links),
            "link_ids": [str(item.get("link_id")) for item in commercial_links],
            "commercial_process_ids_not_selected": commercial_process_ids,
            "commercial_material_labels_without_oem_or_selection_credit": (
                unqualified_material_labels
            ),
            "qualified_material_basis_link_count": sum(
                bool(
                    item.get("porschefanatics_record", {}).get(
                        "material_ids_with_qualified_basis", []
                    )
                )
                for item in commercial_links
            ),
            "proves_oem_geometry_material_or_equivalence": False,
        },
        "selection_inputs": {
            "required": list(material_policy.get("required_inputs", [])),
            "complete": [],
            "missing": list(material_policy.get("required_inputs", [])),
        },
        "selection": {
            "selected_material": None,
            "selected_manufacturing_route": None,
            "selected_reference_solver": None,
            "selected_physicsnemo_model": None,
            "status": "blocked_missing_part_specific_geometry_loads_environment_and_process_data",
        },
        "risk_boundary": {
            "criticality_tier": risk.get("criticality_tier"),
            "professional_engineering_review_required": risk.get(
                "professional_engineering_review_required"
            ),
            "physical_validation_unavailable_by_program_constraint": True,
        },
        "claims": {
            "material_selected": False,
            "manufacturing_route_selected": False,
            "reference_simulation_passed": False,
            "physicsnemo_trained_or_validated": False,
            "omniverse_material_or_physics_validated": False,
            "manufacturing_released": False,
            "road_or_track_use_authorized": False,
        },
    }


def build() -> tuple[dict[str, Any], dict[str, str]]:
    readiness = load_json(READINESS_INDEX)
    program = load_json(PROGRAM_DEFINITION)
    task_shards = load_readiness_tasks(readiness)
    commercial_links_by_master, commercial_crosswalk = (
        load_commercial_alternative_links()
    )
    archetype_counts = readiness.get("coverage", {}).get(
        "tasks_by_engineering_archetype", {}
    )
    if set(archetype_counts) != set(ARCHETYPE_GROUP):
        raise ContractError("archetype_profile_coverage")
    if set(ARCHETYPE_GROUP.values()) - set(GROUP_SPECS):
        raise ContractError("unknown_profile_group")

    domains = program.get("simulation_domains", {})
    material_policy = program.get("material_selection_policy", {})
    manufacturing_policy = program.get("manufacturing_policy", {})
    physicsnemo_policy = program.get("physicsnemo_policy", {})
    allowed_routes = set(manufacturing_policy.get("routes_considered", []))
    for group_id, profile in GROUP_SPECS.items():
        unknown_routes = set(profile["routes"]) - allowed_routes
        if unknown_routes:
            raise ContractError(f"unsupported_routes:{group_id}:{sorted(unknown_routes)}")
    titanium_requirements = list(material_policy.get("titanium_extra_requirements", []))
    if len(titanium_requirements) != 8:
        raise ContractError("titanium_requirement_count")

    routes_by_shard: dict[str, list[dict[str, Any]]] = {}
    by_archetype: Counter[str] = Counter()
    by_group: Counter[str] = Counter()
    by_disposition: Counter[str] = Counter()
    additive_candidates = 0
    titanium_candidates = 0
    tasks_with_commercial_alternatives = 0
    commercial_alternative_links = 0
    for shard_id in SHARD_IDS:
        routes = []
        for task in task_shards[shard_id]:
            route = build_route(
                task,
                domains,
                material_policy,
                titanium_requirements,
                commercial_links_by_master.get(
                    str(task.get("part_master_twin_id", "")), []
                ),
            )
            routes.append(route)
            profile = route["routing_profile"]
            archetype = route["source_archetype"]["engineering_archetype"]
            by_archetype[archetype] += 1
            by_group[profile["group_id"]] += 1
            by_disposition[profile["disposition"]] += 1
            additive_candidates += int(
                any("fabrication_additive" in item for item in profile["candidate_manufacturing_routes"])
            )
            titanium_candidates += int(bool(profile["titanium_extra_requirements"]))
            link_count = route["commercial_alternative_evidence"][
                "exact_replacement_link_count"
            ]
            tasks_with_commercial_alternatives += int(link_count > 0)
            commercial_alternative_links += link_count
        routes_by_shard[shard_id] = routes

    shard_texts = {
        shard_id: render_jsonl(routes_by_shard[shard_id]) for shard_id in SHARD_IDS
    }
    task_count = sum(by_archetype.values())
    manifest = {
        "$comment": (
            "Routage F0 matiere-procede-modele de reference pour chaque maitre PET. "
            "Les familles et routes sont des candidats de triage non selectionnes; aucune "
            "piece, simulation, fabrication ou aptitude vehicule n'est validee."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "engineering_readiness_index": relative(READINESS_INDEX),
            "engineering_readiness_index_sha256": sha256_file(READINESS_INDEX),
            "program_definition": relative(PROGRAM_DEFINITION),
            "program_definition_sha256": sha256_file(PROGRAM_DEFINITION),
            "porschefanatics_crosswalk": relative(PORSCHEFANATICS_CROSSWALK),
            "porschefanatics_crosswalk_sha256": sha256_file(
                PORSCHEFANATICS_CROSSWALK
            ),
            "archetype_routes_are_human_reviewed": False,
        },
        "scope": {
            "part_master_routing_tasks": task_count,
            "archetype_profiles": len(ARCHETYPE_GROUP),
            "profile_groups": len(GROUP_SPECS),
            "tasks_with_material_family_candidates": task_count,
            "tasks_with_manufacturing_route_candidates": sum(
                count
                for disposition, count in by_disposition.items()
                if disposition != "specification_or_qualified_supplier_item_not_part_geometry"
            ),
            "tasks_with_additive_route_candidate": additive_candidates,
            "tasks_with_titanium_family_candidate": titanium_candidates,
            "tasks_with_exact_commercial_alternative_evidence": (
                tasks_with_commercial_alternatives
            ),
            "exact_commercial_alternative_links": commercial_alternative_links,
            "commercial_alternative_links_with_qualified_material_basis": int(
                commercial_crosswalk.get("scope", {}).get(
                    "links_with_qualified_material_basis", 0
                )
            ),
            "selected_materials": 0,
            "selected_manufacturing_routes": 0,
            "passed_reference_simulations": 0,
            "trained_or_validated_physicsnemo_models": 0,
            "omniverse_material_or_physics_validations": 0,
            "manufacturing_releases": 0,
        },
        "coverage": {
            "tasks_by_engineering_archetype": dict(sorted(by_archetype.items())),
            "tasks_by_profile_group": dict(sorted(by_group.items())),
            "tasks_by_disposition": dict(sorted(by_disposition.items())),
        },
        "profile_registry": {
            archetype: {
                "profile_group": group_id,
                **GROUP_SPECS[group_id],
            }
            for archetype, group_id in sorted(ARCHETYPE_GROUP.items())
        },
        "selection_policy": {
            "method": material_policy.get("virtual_selection_method"),
            "required_inputs": material_policy.get("required_inputs", []),
            "titanium_extra_requirements": titanium_requirements,
            "candidate_family_is_selected_grade": False,
            "candidate_route_is_selected_process": False,
            "system_fallback_archetype_is_part_classification": False,
            "reference_solver_precedes_physicsnemo": True,
            "physical_validation_unavailable_by_program_constraint": True,
        },
        "physicsnemo_boundary": {
            "canonical_repository": physicsnemo_policy.get("canonical_repository"),
            "discovered_commit": physicsnemo_policy.get("discovered_commit"),
            "verified_model_families": physicsnemo_policy.get(
                "verified_model_families", []
            ),
            "verified_data_interfaces": physicsnemo_policy.get(
                "verified_data_interfaces", []
            ),
            "role": "surrogate_only_after_converged_reference_solver_dataset",
            "model_and_datapipe_are_independent_axes": True,
            "execution_enabled": False,
        },
        "commercial_alternative_boundary": {
            "link_method": "exact_normalized_replacesOem",
            "general_993_fitment_creates_part_master_link": False,
            "commercial_material_is_oem_material": False,
            "commercial_process_is_selected_manufacturing_route": False,
            "replacement_claim_proves_functional_equivalence": False,
        },
        "output": {
            "tracked": False,
            "work_root": relative(WORK_ROOT),
            "shards": [
                {
                    "shard_id": shard_id,
                    "path": relative(WORK_ROOT / f"{shard_id}.jsonl"),
                    "record_count": len(routes_by_shard[shard_id]),
                    "sha256": sha256_bytes(shard_texts[shard_id].encode("utf-8")),
                }
                for shard_id in SHARD_IDS
            ],
        },
        "claim_boundary": {
            "archetype_is_verified_part_identity": False,
            "material_candidate_is_material_selection": False,
            "route_candidate_is_process_selection": False,
            "reference_model_route_is_solver_result": False,
            "physicsnemo_execution_enabled": False,
            "omniverse_material_or_physics_validated": False,
            "part_is_dimensionally_accurate": False,
            "part_is_manufacturing_released": False,
            "vehicle_is_functioning": False,
        },
        "next_gate": (
            "resolve_configuration_then_author_F2_or_F3_geometry_interfaces_loads_"
            "environment_and_process_dependent_material_properties_before_selection"
        ),
    }
    validate(manifest, routes_by_shard)
    return manifest, shard_texts


def validate(
    manifest: dict[str, Any], routes_by_shard: dict[str, list[dict[str, Any]]]
) -> None:
    scope = manifest.get("scope", {})
    if scope.get("part_master_routing_tasks") != 6013:
        raise ContractError("routing_task_count")
    if scope.get("archetype_profiles") != 42:
        raise ContractError("archetype_profile_count")
    if scope.get("profile_groups") != len(GROUP_SPECS):
        raise ContractError("profile_group_count")
    if sum(manifest.get("coverage", {}).get("tasks_by_engineering_archetype", {}).values()) != 6013:
        raise ContractError("archetype_partition")
    if sum(manifest.get("coverage", {}).get("tasks_by_profile_group", {}).values()) != 6013:
        raise ContractError("profile_group_partition")
    if sum(manifest.get("coverage", {}).get("tasks_by_disposition", {}).values()) != 6013:
        raise ContractError("disposition_partition")
    if set(routes_by_shard) != set(SHARD_IDS):
        raise ContractError("routing_shards")
    routes = [route for shard_id in SHARD_IDS for route in routes_by_shard[shard_id]]
    if len(routes) != 6013 or len({route["screening_task_id"] for route in routes}) != 6013:
        raise ContractError("routing_task_identity")
    for route in routes:
        source = route.get("source_archetype", {})
        if source.get("human_reviewed_classification") is not False:
            raise ContractError("classification_overclaim")
        if not route.get("routing_profile", {}).get("candidate_material_families"):
            raise ContractError("missing_material_candidates")
        if route.get("selection_inputs", {}).get("complete"):
            raise ContractError("selection_inputs_overclaim")
        if not route.get("selection_inputs", {}).get("missing"):
            raise ContractError("missing_selection_blockers")
        if any(value is not None for key, value in route.get("selection", {}).items() if key.startswith("selected_")):
            raise ContractError("selection_overclaim")
        if any(value is not False for value in route.get("claims", {}).values()):
            raise ContractError("route_claim_overclaim")
        if any(item.get("reference_solver_status") != "not_run" for item in route.get("reference_model_routes", [])):
            raise ContractError("solver_overclaim")
        physicsnemo = route.get("physicsnemo_route", {})
        if physicsnemo.get("selected_model") is not None:
            raise ContractError("physicsnemo_selection_overclaim")
        if physicsnemo.get("execution_enabled") is not False:
            raise ContractError("physicsnemo_execution_overclaim")
        if not set(physicsnemo.get("candidate_models", [])) <= set(
            manifest.get("physicsnemo_boundary", {}).get(
                "verified_model_families", []
            )
        ):
            raise ContractError("unverified_physicsnemo_candidate")
        commercial = route.get("commercial_alternative_evidence", {})
        if commercial.get("proves_oem_geometry_material_or_equivalence") is not False:
            raise ContractError("commercial_evidence_overclaim")
        if commercial.get("qualified_material_basis_link_count") != 0:
            raise ContractError("commercial_material_basis_overclaim")
    if any(
        scope.get(key) != 0
        for key in (
            "selected_materials",
            "selected_manufacturing_routes",
            "passed_reference_simulations",
            "trained_or_validated_physicsnemo_models",
            "omniverse_material_or_physics_validations",
            "manufacturing_releases",
        )
    ):
        raise ContractError("aggregate_selection_overclaim")
    if any(value is not False for value in manifest.get("claim_boundary", {}).values()):
        raise ContractError("claim_boundary")
    physicsnemo = manifest.get("physicsnemo_boundary", {})
    if physicsnemo.get("execution_enabled") is not False:
        raise ContractError("aggregate_physicsnemo_execution_overclaim")
    if physicsnemo.get("model_and_datapipe_are_independent_axes") is not True:
        raise ContractError("physicsnemo_axis_collapse")
    if scope.get("tasks_with_exact_commercial_alternative_evidence") != 2:
        raise ContractError("commercial_alternative_task_count")
    if scope.get("exact_commercial_alternative_links") != 6:
        raise ContractError("commercial_alternative_link_count")
    if scope.get("commercial_alternative_links_with_qualified_material_basis") != 0:
        raise ContractError("aggregate_commercial_material_basis_overclaim")
    commercial_boundary = manifest.get("commercial_alternative_boundary", {})
    if any(value is not False for key, value in commercial_boundary.items() if key != "link_method"):
        raise ContractError("commercial_alternative_boundary")


def validate_index() -> None:
    manifest = load_json(OUTPUT)
    sources = manifest.get("source_boundary", {})
    if sources.get("engineering_readiness_index_sha256") != sha256_file(READINESS_INDEX):
        raise ContractError("readiness_index_digest")
    if sources.get("program_definition_sha256") != sha256_file(PROGRAM_DEFINITION):
        raise ContractError("program_definition_digest")
    if sources.get("porschefanatics_crosswalk_sha256") != sha256_file(
        PORSCHEFANATICS_CROSSWALK
    ):
        raise ContractError("porschefanatics_crosswalk_digest")
    scope = manifest.get("scope", {})
    if scope.get("part_master_routing_tasks") != 6013:
        raise ContractError("tracked_routing_task_count")
    if scope.get("archetype_profiles") != 42:
        raise ContractError("tracked_archetype_profile_count")
    if scope.get("tasks_with_exact_commercial_alternative_evidence") != 2:
        raise ContractError("tracked_commercial_alternative_task_count")
    if scope.get("exact_commercial_alternative_links") != 6:
        raise ContractError("tracked_commercial_alternative_link_count")
    if scope.get("commercial_alternative_links_with_qualified_material_basis") != 0:
        raise ContractError("tracked_commercial_material_basis_overclaim")
    readiness = load_json(READINESS_INDEX)
    if manifest.get("coverage", {}).get("tasks_by_engineering_archetype") != readiness.get("coverage", {}).get("tasks_by_engineering_archetype"):
        raise ContractError("tracked_archetype_coverage")
    shards = manifest.get("output", {}).get("shards", [])
    if len(shards) != 16 or sum(item.get("record_count", 0) for item in shards) != 6013:
        raise ContractError("tracked_shard_partition")
    if manifest.get("output", {}).get("tracked") is not False:
        raise ContractError("tracked_output_boundary")
    commercial_boundary = manifest.get("commercial_alternative_boundary", {})
    if any(
        value is not False
        for key, value in commercial_boundary.items()
        if key != "link_method"
    ):
        raise ContractError("tracked_commercial_alternative_boundary")
    if any(value is not False for value in manifest.get("claim_boundary", {}).values()):
        raise ContractError("tracked_claim_boundary")


def run(*, write: bool) -> int:
    manifest, shard_texts = build()
    expected = render_json(manifest)
    if write:
        WORK_ROOT.mkdir(parents=True, exist_ok=True)
        for shard_id, text in shard_texts.items():
            (WORK_ROOT / f"{shard_id}.jsonl").write_text(text, encoding="utf-8")
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(expected, encoding="utf-8")
        print(f"wrote {relative(OUTPUT)} and {len(shard_texts)} work shards")
        return 0
    if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
        print(f"stale generated routing: {relative(OUTPUT)}", file=sys.stderr)
        return 1
    for shard_id, text in shard_texts.items():
        path = WORK_ROOT / f"{shard_id}.jsonl"
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            print(f"stale generated routing shard: {relative(path)}", file=sys.stderr)
            return 1
    print(f"current {relative(OUTPUT)} and {len(shard_texts)} work shards")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.check_index:
            validate_index()
            print(f"valid {relative(OUTPUT)}")
            return 0
        return run(write=args.write)
    except ContractError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
