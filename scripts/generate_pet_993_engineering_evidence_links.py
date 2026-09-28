#!/usr/bin/env python3
"""Link detailed F0/F1 engineering evidence to PET part masters, fail closed."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CROSSWALK = ROOT / "twins" / "pet-993" / "catalog-crosswalk-f0.json"
CATALOGUE_ENGINEERING = ROOT / "twins" / "catalogue-parts" / "engineering-f0.json"
ENGINE_COMPONENTS = ROOT / "twins" / "engine-simulation-contracts" / "components-f1.json"
ENGINE_LOAD_CASES = ROOT / "twins" / "engine-simulation-contracts" / "load-cases-f1.json"
ENGINE_CARRIER_VIRTUAL_F2 = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engine-carrier-virtual-f2-readiness.json"
)
VALVE_DIMENSIONAL_SURROGATES = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "valve-dimensional-surrogates-f1.json"
)
K16_ENVELOPE_FLOW_SURROGATES = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "k16-envelope-flow-readiness-f1.json"
)
CHARGE_AIR_CHAIN_SURROGATES = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "charge-air-chain-readiness-f1.json"
)
HEAT_SHIELD_SURROGATE = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "turbo-heat-shield-readiness-f1.json"
)
TURBO_LUBRICATION_CONTROL_TOPOLOGY = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "turbo-lubrication-control-topology-readiness-f1.json"
)
OIL_TANK_CIRCUIT_TOPOLOGY = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "oil-tank-circuit-topology-readiness-f1.json"
)
OIL_COOLER_CIRCUIT_TOPOLOGY = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "oil-cooler-circuit-topology-readiness-f1.json"
)
ENGINEERING_GUIDES_OPENUSD_VALIDATION = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering-guides-openusd-validation-f1.json"
)
OUTPUT = ROOT / "twins" / "pet-993" / "engineering-evidence-links-f0.json"
EXPECTED_K16_PART_ID = "993-TURBOCHARGER-K16-PAIR-0001"

PART_COMPONENT_IDS = {
    "993-ENG-INTAKE-VALVE-F1-0001": ["CMP-993-INTAKE-VALVE-PROXY"],
    "993-ENG-EXHAUST-VALVE-F1-0001": ["CMP-993-EXHAUST-VALVE-PROXY"],
    "993-TURBOCHARGER-K16-PAIR-0001": [
        "CMP-993-K16-LEFT-PROXY",
        "CMP-993-K16-RIGHT-PROXY",
    ],
}


class ContractError(ValueError):
    """Raised when an evidence link could overstate engineering maturity."""


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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def catalogue_contract_summary(record: dict[str, Any]) -> dict[str, Any]:
    simulation = record.get("simulation", {})
    cases = simulation.get("load_cases", [])
    if not isinstance(cases, list):
        raise ContractError("catalogue_load_cases")
    return {
        "twin_id": record.get("twin_id"),
        "current_fidelity": record.get("current_fidelity"),
        "engineering_status": record.get("engineering_status"),
        "simulation_domain_ids": simulation.get("domain_ids", []),
        "load_case_ids": [case.get("load_case_id") for case in cases],
        "load_case_statuses": [case.get("status") for case in cases],
        "analysis_geometry": simulation.get("analysis_geometry"),
        "selected_functional_route": record.get("manufacturing", {}).get(
            "selected_functional_route"
        ),
        "virtual_material_screening": record.get("virtual_material_screening"),
    }


def build() -> dict[str, Any]:
    crosswalk = load_json(CROSSWALK)
    catalogue_engineering = load_json(CATALOGUE_ENGINEERING)
    engine_components = load_json(ENGINE_COMPONENTS)
    engine_load_cases = load_json(ENGINE_LOAD_CASES)
    engine_carrier_virtual_f2 = load_json(ENGINE_CARRIER_VIRTUAL_F2)
    valve_dimensional_surrogates = load_json(VALVE_DIMENSIONAL_SURROGATES)
    k16_envelope_flow_surrogates = load_json(K16_ENVELOPE_FLOW_SURROGATES)
    charge_air_chain_surrogates = load_json(CHARGE_AIR_CHAIN_SURROGATES)
    heat_shield_surrogate = load_json(HEAT_SHIELD_SURROGATE)
    turbo_lubrication_control = load_json(TURBO_LUBRICATION_CONTROL_TOPOLOGY)
    oil_tank_circuit = load_json(OIL_TANK_CIRCUIT_TOPOLOGY)
    oil_cooler_circuit = load_json(OIL_COOLER_CIRCUIT_TOPOLOGY)
    engineering_guides_validation = load_json(
        ENGINEERING_GUIDES_OPENUSD_VALIDATION
    )
    if engineering_guides_validation.get("status") != (
        "passed_openusd_strict_not_nvidia_asset_validator_or_simready"
    ):
        raise ContractError("engineering_guides_openusd_validation_status")
    if any(
        value is not False
        for value in engineering_guides_validation.get("claim_boundary", {}).values()
    ):
        raise ContractError("engineering_guides_openusd_validation_claim")
    openusd_validation_by_role = {
        str(item.get("role")): item
        for item in engineering_guides_validation.get("validated_stages", [])
        if isinstance(item, dict)
    }
    if engine_carrier_virtual_f2.get("status") != (
        "F2_virtual_readiness_complete_no_F2_geometry_credit"
    ):
        raise ContractError("engine_carrier_virtual_f2_status")
    if any(
        value is not False
        for value in engine_carrier_virtual_f2.get("release_gates", {}).values()
    ):
        raise ContractError("engine_carrier_virtual_f2_release")
    virtual_f2_summary = {
        "contract": relative(ENGINE_CARRIER_VIRTUAL_F2),
        "status": engine_carrier_virtual_f2.get("status"),
        "interface_hypothesis_count": len(
            engine_carrier_virtual_f2.get("interface_hypotheses", [])
        ),
        "unknown_parameter_count": len(
            engine_carrier_virtual_f2.get("parameter_registry", [])
        ),
        "blocked_load_case_count": len(
            engine_carrier_virtual_f2.get("load_cases", [])
        ),
        "mass_constrained_surrogate_status": engine_carrier_virtual_f2.get(
            "mass_constrained_surrogate", {}
        ).get("status"),
        "mass_constraint_closed": engine_carrier_virtual_f2.get(
            "mass_constrained_surrogate", {}
        ).get("mass_constraint_closed"),
        "equivalent_wall_mm": engine_carrier_virtual_f2.get(
            "mass_constrained_surrogate", {}
        ).get("equivalent_wall_mm"),
        "interface_search_domain_count": engine_carrier_virtual_f2.get(
            "mass_constrained_surrogate", {}
        ).get("interface_search_domain_count"),
        "selected_interface_point_count": engine_carrier_virtual_f2.get(
            "mass_constrained_surrogate", {}
        ).get("selected_interface_point_count"),
        "mass_constrained_surrogate_component_credit": engine_carrier_virtual_f2.get(
            "mass_constrained_surrogate", {}
        ).get("component_geometry_credit"),
        "F2_interface_geometry": engine_carrier_virtual_f2.get(
            "release_gates", {}
        ).get("F2_interface_geometry"),
        "reference_CAE_passed": engine_carrier_virtual_f2.get(
            "release_gates", {}
        ).get("reference_CAE_passed"),
        "physicsnemo_validated": engine_carrier_virtual_f2.get(
            "release_gates", {}
        ).get("physicsnemo_validated"),
        "simready_validated": engine_carrier_virtual_f2.get(
            "release_gates", {}
        ).get("simready_validated"),
        "openusd_strict_validation": openusd_validation_by_role.get(
            "engine_carrier_mass_constrained_F1_guide", {}
        ).get("result"),
        "nvidia_asset_validator": engineering_guides_validation.get(
            "results", {}
        ).get("nvidia_asset_validator"),
    }
    if valve_dimensional_surrogates.get("status") != (
        "F1_valve_dimensional_surrogates_complete_no_component_CAE_credit"
    ):
        raise ContractError("valve_dimensional_surrogate_status")
    if any(
        value is not False
        for value in valve_dimensional_surrogates.get("claim_boundary", {}).values()
    ):
        raise ContractError("valve_dimensional_surrogate_claim")
    valve_variants_by_part: dict[str, list[dict[str, Any]]] = {}
    for variant in valve_dimensional_surrogates.get("variants", []):
        if not isinstance(variant, dict) or not isinstance(variant.get("part_id"), str):
            raise ContractError("valve_dimensional_surrogate_variant")
        valve_variants_by_part.setdefault(variant["part_id"], []).append(variant)
    valve_summary_by_part = {
        part_id: {
            "contract": relative(VALVE_DIMENSIONAL_SURROGATES),
            "status": valve_dimensional_surrogates.get("status"),
            "variant_ids": sorted(str(item["variant_id"]) for item in variants),
            "variant_count": len(variants),
            "linked_pet_part_master_twin_ids": sorted(
                {
                    str(master_id)
                    for item in variants
                    for master_id in item.get("pet_part_master_twin_ids", [])
                }
            ),
            "editable_scad": valve_dimensional_surrogates.get("assets", {}).get(
                "editable_scad"
            ),
            "openusd_guide": valve_dimensional_surrogates.get("assets", {}).get(
                "openusd_guide"
            ),
            "selected_interface_coordinate_count": valve_dimensional_surrogates.get(
                "interface_readiness", {}
            ).get("selected_interface_coordinate_count"),
            "F1_dimensional_surrogate": True,
            "F2_interface_geometry": False,
            "analysis_geometry_available": False,
            "qualified_material_decision": False,
            "component_CAE_credit": False,
            "openusd_strict_validation": openusd_validation_by_role.get(
                "three_valve_dimensional_F1_guides", {}
            ).get("result"),
            "nvidia_asset_validator": engineering_guides_validation.get(
                "results", {}
            ).get("nvidia_asset_validator"),
        }
        for part_id, variants in valve_variants_by_part.items()
    }
    if k16_envelope_flow_surrogates.get("status") != (
        "F1_K16_envelope_and_diameter_guides_complete_zeroD_execution_blocked"
    ):
        raise ContractError("k16_envelope_flow_surrogate_status")
    if any(
        value is not False
        for value in k16_envelope_flow_surrogates.get("claim_boundary", {}).values()
    ):
        raise ContractError("k16_envelope_flow_surrogate_claim")
    k16_variants = k16_envelope_flow_surrogates.get("variants", [])
    if not isinstance(k16_variants, list) or len(k16_variants) != 2:
        raise ContractError("k16_envelope_flow_surrogate_variants")
    k16_summary = {
        "contract": relative(K16_ENVELOPE_FLOW_SURROGATES),
        "status": k16_envelope_flow_surrogates.get("status"),
        "variant_ids": sorted(str(item["variant_id"]) for item in k16_variants),
        "variant_count": len(k16_variants),
        "linked_pet_part_master_twin_ids": sorted(
            {
                str(master_id)
                for item in k16_variants
                for master_id in item.get("pet_part_master_twin_ids", [])
            }
        ),
        "editable_scad": k16_envelope_flow_surrogates.get("assets", {}).get(
            "editable_scad"
        ),
        "openusd_guide": k16_envelope_flow_surrogates.get("assets", {}).get(
            "openusd_guide"
        ),
        "right_side_wheel_diameter_guide_count": k16_envelope_flow_surrogates.get(
            "summary", {}
        ).get("right_side_wheel_diameter_guides"),
        "symbolic_zeroD_equation_count": k16_envelope_flow_surrogates.get(
            "summary", {}
        ).get("symbolic_zeroD_equation_contracts"),
        "evaluated_zeroD_operating_points": k16_envelope_flow_surrogates.get(
            "summary", {}
        ).get("evaluated_zeroD_operating_points"),
        "selected_interface_coordinate_count": k16_envelope_flow_surrogates.get(
            "flow_interface_readiness", {}
        ).get("selected_interface_coordinate_count"),
        "F1_envelope_and_diameter_guides": True,
        "F2_interface_geometry": False,
        "F3_analysis_geometry": False,
        "qualified_material_decision": False,
        "component_CAE_credit": False,
        "physicsnemo_execution_enabled": k16_envelope_flow_surrogates.get(
            "physicsnemo_discovery", {}
        ).get("execution_enabled"),
        "openusd_strict_validation": openusd_validation_by_role.get(
            "two_K16_envelope_and_right_diameter_F1_guides", {}
        ).get("result"),
        "nvidia_asset_validator": engineering_guides_validation.get(
            "results", {}
        ).get("nvidia_asset_validator"),
    }
    if charge_air_chain_surrogates.get("status") != (
        "F1_charge_air_chain_guides_complete_zeroD_execution_blocked"
    ):
        raise ContractError("charge_air_chain_surrogate_status")
    if any(
        value is not False
        for value in charge_air_chain_surrogates.get("claim_boundary", {}).values()
    ):
        raise ContractError("charge_air_chain_surrogate_claim")
    charge_air_components = charge_air_chain_surrogates.get("components", [])
    if not isinstance(charge_air_components, list) or len(charge_air_components) != 5:
        raise ContractError("charge_air_chain_surrogate_components")
    charge_air_validation = openusd_validation_by_role.get(
        "five_charge_air_envelope_and_aftermarket_diameter_F1_guides", {}
    ).get("result")
    if charge_air_validation != "passed":
        raise ContractError("charge_air_chain_openusd_validation")
    charge_air_reference_links = []
    for component in charge_air_components:
        if not isinstance(component, dict):
            raise ContractError("charge_air_chain_component")
        component_id = component.get("component_id")
        reference = component.get("oem_reference")
        master_id = component.get("pet_part_master_twin_id")
        if not all(isinstance(value, str) and value for value in (component_id, reference, master_id)):
            raise ContractError("charge_air_chain_component_identity")
        charge_air_reference_links.append(
            {
                "evidence_id": f"CHARGE-AIR-{component_id}",
                "normalized_oem_reference": reference,
                "pet_part_master_twin_ids": [master_id],
                "charge_air_chain_surrogate_contract": {
                    "contract": relative(CHARGE_AIR_CHAIN_SURROGATES),
                    "status": charge_air_chain_surrogates.get("status"),
                    "component_id": component_id,
                    "role": component.get("role"),
                    "oem_reference": reference,
                    "pet_part_master_twin_id": master_id,
                    "dimension_semantics": component.get("dimension_semantics"),
                    "editable_scad": charge_air_chain_surrogates.get("assets", {}).get(
                        "editable_scad"
                    ),
                    "openusd_guide": charge_air_chain_surrogates.get("assets", {}).get(
                        "openusd_guide"
                    ),
                    "symbolic_zeroD_equation_count": charge_air_chain_surrogates.get(
                        "summary", {}
                    ).get("symbolic_zeroD_equation_contracts"),
                    "evaluated_zeroD_operating_points": charge_air_chain_surrogates.get(
                        "summary", {}
                    ).get("evaluated_zeroD_operating_points"),
                    "selected_interface_coordinate_count": component.get(
                        "interface_coordinate_count"
                    ),
                    "F1_envelope_guide": True,
                    "F2_interface_geometry": False,
                    "F3_analysis_geometry": False,
                    "qualified_material_decision": False,
                    "component_CAE_credit": False,
                    "physicsnemo_execution_enabled": charge_air_chain_surrogates.get(
                        "physicsnemo_discovery", {}
                    ).get("execution_enabled"),
                    "openusd_strict_validation": charge_air_validation,
                    "nvidia_asset_validator": engineering_guides_validation.get(
                        "results", {}
                    ).get("nvidia_asset_validator"),
                },
                "evidence_status": "linked_by_exact_PET_master_identity_no_solver_or_release_credit",
                "claims": {
                    "analysis_geometry_available": False,
                    "material_selected_or_qualified": False,
                    "reference_solver_passed": False,
                    "physicsnemo_executed_or_validated": False,
                    "simready_validated": False,
                    "manufacturing_released": False,
                },
            }
        )
    charge_air_reference_links.sort(key=lambda item: item["normalized_oem_reference"])

    if heat_shield_surrogate.get("status") != (
        "F1_turbo_heat_shield_envelope_thermal_readiness_complete_reference_solution_blocked"
    ):
        raise ContractError("heat_shield_surrogate_status")
    if any(
        value is not False
        for value in heat_shield_surrogate.get("claim_boundary", {}).values()
    ):
        raise ContractError("heat_shield_surrogate_claim")
    heat_subject = heat_shield_surrogate.get("subject", {})
    heat_master_id = heat_subject.get("pet_part_master_twin_id")
    if (
        heat_subject.get("oem_reference") != "99312311351"
        or not isinstance(heat_master_id, str)
    ):
        raise ContractError("heat_shield_surrogate_identity")
    heat_validation = openusd_validation_by_role.get(
        "one_turbo_heat_shield_envelope_thermal_F1_guide", {}
    ).get("result")
    if heat_validation != "passed":
        raise ContractError("heat_shield_openusd_validation")
    heat_shield_reference_link = {
        "evidence_id": "HEAT-SHIELD-993-TURBO-LEFT",
        "normalized_oem_reference": "99312311351",
        "pet_part_master_twin_ids": [heat_master_id],
        "heat_shield_thermal_surrogate_contract": {
            "contract": relative(HEAT_SHIELD_SURROGATE),
            "status": heat_shield_surrogate.get("status"),
            "oem_reference": heat_subject.get("oem_reference"),
            "pet_part_master_twin_id": heat_master_id,
            "editable_scad": heat_shield_surrogate.get("assets", {}).get(
                "editable_scad"
            ),
            "openusd_guide": heat_shield_surrogate.get("assets", {}).get(
                "openusd_guide"
            ),
            "symbolic_thermal_equation_count": heat_shield_surrogate.get(
                "summary", {}
            ).get("symbolic_thermal_equation_contracts"),
            "blocked_reference_load_case_count": heat_shield_surrogate.get(
                "summary", {}
            ).get("blocked_reference_load_cases"),
            "unknown_engineering_parameter_count": heat_shield_surrogate.get(
                "summary", {}
            ).get("unknown_engineering_parameters"),
            "evaluated_thermal_operating_points": heat_shield_surrogate.get(
                "summary", {}
            ).get("evaluated_thermal_operating_points"),
            "selected_interface_coordinate_count": heat_shield_surrogate.get(
                "summary", {}
            ).get("selected_interface_coordinates"),
            "F1_envelope_thermal_readiness": True,
            "F2_interface_geometry": False,
            "F3_analysis_geometry": False,
            "qualified_material_decision": False,
            "component_CAE_credit": False,
            "physicsnemo_execution_enabled": heat_shield_surrogate.get(
                "physicsnemo_discovery", {}
            ).get("execution_enabled"),
            "openusd_strict_validation": heat_validation,
            "nvidia_asset_validator": engineering_guides_validation.get(
                "results", {}
            ).get("nvidia_asset_validator"),
        },
        "evidence_status": "linked_by_exact_PET_master_identity_no_solver_or_release_credit",
        "claims": {
            "analysis_geometry_available": False,
            "material_selected_or_qualified": False,
            "reference_solver_passed": False,
            "physicsnemo_executed_or_validated": False,
            "simready_validated": False,
            "manufacturing_released": False,
        },
    }
    if turbo_lubrication_control.get("status") != (
        "F1_202_16_turbo_lubrication_control_topology_complete_reference_solution_blocked"
    ):
        raise ContractError("turbo_lubrication_control_topology_status")
    if any(
        value is not False
        for value in turbo_lubrication_control.get("claim_boundary", {}).values()
    ):
        raise ContractError("turbo_lubrication_control_topology_claim")
    turbo_topology_roster = turbo_lubrication_control.get("part_roster", [])
    if not isinstance(turbo_topology_roster, list) or len(turbo_topology_roster) != 40:
        raise ContractError("turbo_lubrication_control_topology_roster")
    turbo_topology_validation = openusd_validation_by_role.get(
        "forty_202_16_turbo_lubrication_control_topology_F1_entries", {}
    ).get("result")
    if turbo_topology_validation != "passed":
        raise ContractError("turbo_lubrication_control_openusd_validation")
    turbo_topology_reference_links = []
    for item in turbo_topology_roster:
        if not isinstance(item, dict):
            raise ContractError("turbo_lubrication_control_topology_component")
        reference = item.get("normalized_oem_reference")
        master_id = item.get("pet_part_master_twin_id")
        if not all(isinstance(value, str) and value for value in (reference, master_id)):
            raise ContractError("turbo_lubrication_control_topology_identity")
        turbo_topology_reference_links.append(
            {
                "evidence_id": f"TURBO-LUBRICATION-CONTROL-{reference}",
                "normalized_oem_reference": reference,
                "pet_part_master_twin_ids": [master_id],
                "turbo_lubrication_control_topology_contract": {
                    "contract": relative(TURBO_LUBRICATION_CONTROL_TOPOLOGY),
                    "status": turbo_lubrication_control.get("status"),
                    "pet_illustration": "202-16",
                    "pet_positions": item.get("pet_positions", []),
                    "role_hypothesis": item.get("role_hypothesis"),
                    "role_status": item.get("role_status"),
                    "editable_topology_source": turbo_lubrication_control.get(
                        "assets", {}
                    ).get("editable_topology_source"),
                    "openusd_guide": turbo_lubrication_control.get("assets", {}).get(
                        "openusd_guide"
                    ),
                    "symbolic_equation_count": turbo_lubrication_control.get(
                        "summary", {}
                    ).get("symbolic_equation_contracts"),
                    "blocked_reference_load_case_count": turbo_lubrication_control.get(
                        "summary", {}
                    ).get("blocked_reference_load_cases"),
                    "unknown_engineering_parameter_count": turbo_lubrication_control.get(
                        "summary", {}
                    ).get("unknown_engineering_parameters"),
                    "known_interface_coordinate_count": turbo_lubrication_control.get(
                        "summary", {}
                    ).get("known_interface_coordinates"),
                    "F1_nonspatial_topology_readiness": True,
                    "F2_interface_geometry": False,
                    "F3_analysis_geometry": False,
                    "qualified_material_decision": False,
                    "component_CAE_credit": False,
                    "physicsnemo_execution_enabled": turbo_lubrication_control.get(
                        "physicsnemo_discovery", {}
                    ).get("execution_enabled"),
                    "openusd_strict_validation": turbo_topology_validation,
                    "nvidia_asset_validator": engineering_guides_validation.get(
                        "results", {}
                    ).get("nvidia_asset_validator"),
                },
                "evidence_status": "linked_by_exact_PET_master_identity_no_geometry_solver_or_release_credit",
                "claims": {
                    "analysis_geometry_available": False,
                    "material_selected_or_qualified": False,
                    "reference_solver_passed": False,
                    "physicsnemo_executed_or_validated": False,
                    "simready_validated": False,
                    "manufacturing_released": False,
                },
            }
        )
    if oil_tank_circuit.get("status") != (
        "F1_104_01_oil_tank_circuit_topology_complete_reference_solution_blocked"
    ):
        raise ContractError("oil_tank_circuit_topology_status")
    if any(
        value is not False
        for value in oil_tank_circuit.get("claim_boundary", {}).values()
    ):
        raise ContractError("oil_tank_circuit_topology_claim")
    oil_tank_roster = oil_tank_circuit.get("part_roster", [])
    if not isinstance(oil_tank_roster, list) or len(oil_tank_roster) != 81:
        raise ContractError("oil_tank_circuit_topology_roster")
    oil_tank_validation = openusd_validation_by_role.get(
        "eighty_one_104_01_oil_tank_circuit_topology_F1_entries", {}
    ).get("result")
    if oil_tank_validation != "passed":
        raise ContractError("oil_tank_circuit_openusd_validation")
    oil_tank_reference_links = []
    for item in oil_tank_roster:
        if not isinstance(item, dict):
            raise ContractError("oil_tank_circuit_topology_component")
        reference = item.get("normalized_oem_reference")
        master_id = item.get("pet_part_master_twin_id")
        if not all(isinstance(value, str) and value for value in (reference, master_id)):
            raise ContractError("oil_tank_circuit_topology_identity")
        oil_tank_reference_links.append(
            {
                "evidence_id": f"OIL-TANK-CIRCUIT-{reference}",
                "normalized_oem_reference": reference,
                "pet_part_master_twin_ids": [master_id],
                "oil_tank_circuit_topology_contract": {
                    "contract": relative(OIL_TANK_CIRCUIT_TOPOLOGY),
                    "status": oil_tank_circuit.get("status"),
                    "pet_illustration": "104-01",
                    "pet_positions": item.get("pet_positions", []),
                    "role_hypothesis": item.get("role_hypothesis"),
                    "role_status": item.get("role_status"),
                    "editable_topology_source": oil_tank_circuit.get(
                        "assets", {}
                    ).get("editable_topology_source"),
                    "openusd_guide": oil_tank_circuit.get("assets", {}).get(
                        "openusd_guide"
                    ),
                    "symbolic_equation_count": oil_tank_circuit.get(
                        "summary", {}
                    ).get("symbolic_equation_contracts"),
                    "blocked_reference_load_case_count": oil_tank_circuit.get(
                        "summary", {}
                    ).get("blocked_reference_load_cases"),
                    "unknown_engineering_parameter_count": oil_tank_circuit.get(
                        "summary", {}
                    ).get("unknown_engineering_parameters"),
                    "known_interface_coordinate_count": oil_tank_circuit.get(
                        "summary", {}
                    ).get("known_interface_coordinates"),
                    "F1_nonspatial_topology_readiness": True,
                    "F2_interface_geometry": False,
                    "F3_analysis_geometry": False,
                    "qualified_material_decision": False,
                    "component_CAE_credit": False,
                    "physicsnemo_execution_enabled": oil_tank_circuit.get(
                        "physicsnemo_discovery", {}
                    ).get("execution_enabled"),
                    "openusd_strict_validation": oil_tank_validation,
                    "nvidia_asset_validator": engineering_guides_validation.get(
                        "results", {}
                    ).get("nvidia_asset_validator"),
                },
                "evidence_status": "linked_by_exact_PET_master_identity_no_geometry_solver_or_release_credit",
                "claims": {
                    "analysis_geometry_available": False,
                    "material_selected_or_qualified": False,
                    "reference_solver_passed": False,
                    "physicsnemo_executed_or_validated": False,
                    "simready_validated": False,
                    "manufacturing_released": False,
                },
            }
        )
    if oil_cooler_circuit.get("status") != (
        "F1_104_05_oil_cooler_circuit_topology_complete_reference_solution_blocked"
    ):
        raise ContractError("oil_cooler_circuit_topology_status")
    if any(
        value is not False
        for value in oil_cooler_circuit.get("claim_boundary", {}).values()
    ):
        raise ContractError("oil_cooler_circuit_topology_claim")
    oil_cooler_roster = oil_cooler_circuit.get("part_roster", [])
    if not isinstance(oil_cooler_roster, list) or len(oil_cooler_roster) != 43:
        raise ContractError("oil_cooler_circuit_topology_roster")
    oil_cooler_validation = openusd_validation_by_role.get(
        "forty_three_104_05_oil_cooler_circuit_topology_F1_entries", {}
    ).get("result")
    if oil_cooler_validation != "passed":
        raise ContractError("oil_cooler_circuit_openusd_validation")
    oil_cooler_reference_links = []
    for item in oil_cooler_roster:
        if not isinstance(item, dict):
            raise ContractError("oil_cooler_circuit_topology_component")
        reference = item.get("normalized_oem_reference")
        master_id = item.get("pet_part_master_twin_id")
        if not all(isinstance(value, str) and value for value in (reference, master_id)):
            raise ContractError("oil_cooler_circuit_topology_identity")
        oil_cooler_reference_links.append(
            {
                "evidence_id": f"OIL-COOLER-CIRCUIT-{reference}",
                "normalized_oem_reference": reference,
                "pet_part_master_twin_ids": [master_id],
                "oil_cooler_circuit_topology_contract": {
                    "contract": relative(OIL_COOLER_CIRCUIT_TOPOLOGY),
                    "status": oil_cooler_circuit.get("status"),
                    "pet_illustration": "104-05",
                    "pet_positions": item.get("pet_positions", []),
                    "role_hypothesis": item.get("role_hypothesis"),
                    "role_status": item.get("role_status"),
                    "editable_topology_source": oil_cooler_circuit.get(
                        "assets", {}
                    ).get("editable_topology_source"),
                    "openusd_guide": oil_cooler_circuit.get("assets", {}).get(
                        "openusd_guide"
                    ),
                    "symbolic_equation_count": oil_cooler_circuit.get(
                        "summary", {}
                    ).get("symbolic_equation_contracts"),
                    "blocked_reference_load_case_count": oil_cooler_circuit.get(
                        "summary", {}
                    ).get("blocked_reference_load_cases"),
                    "unknown_engineering_parameter_count": oil_cooler_circuit.get(
                        "summary", {}
                    ).get("unknown_engineering_parameters"),
                    "known_interface_coordinate_count": oil_cooler_circuit.get(
                        "summary", {}
                    ).get("known_interface_coordinates"),
                    "F1_nonspatial_topology_readiness": True,
                    "F2_interface_geometry": False,
                    "F3_analysis_geometry": False,
                    "qualified_material_decision": False,
                    "component_CAE_credit": False,
                    "physicsnemo_execution_enabled": oil_cooler_circuit.get(
                        "physicsnemo_discovery", {}
                    ).get("execution_enabled"),
                    "openusd_strict_validation": oil_cooler_validation,
                    "nvidia_asset_validator": engineering_guides_validation.get(
                        "results", {}
                    ).get("nvidia_asset_validator"),
                },
                "evidence_status": "linked_by_exact_PET_master_identity_no_geometry_solver_or_release_credit",
                "claims": {
                    "analysis_geometry_available": False,
                    "material_selected_or_qualified": False,
                    "reference_solver_passed": False,
                    "physicsnemo_executed_or_validated": False,
                    "simready_validated": False,
                    "manufacturing_released": False,
                },
            }
        )
    declared_reference_links = (
        charge_air_reference_links
        + [heat_shield_reference_link]
        + turbo_topology_reference_links
        + oil_tank_reference_links
        + oil_cooler_reference_links
    )
    declared_reference_links.sort(
        key=lambda item: (item["normalized_oem_reference"], item["evidence_id"])
    )

    catalogue_by_part: dict[str, list[dict[str, Any]]] = {}
    for record in catalogue_engineering.get("parts", []):
        if not isinstance(record, dict):
            raise ContractError("catalogue_engineering_part")
        part_id = record.get("subject", {}).get("part_id")
        if isinstance(part_id, str):
            catalogue_by_part.setdefault(part_id, []).append(record)

    components_by_id = {
        item["component_id"]: item
        for item in engine_components.get("components", [])
        if isinstance(item, dict) and isinstance(item.get("component_id"), str)
    }
    load_cases = engine_load_cases.get("load_cases", [])
    if not isinstance(load_cases, list):
        raise ContractError("engine_load_cases")

    links: list[dict[str, Any]] = []
    unique_masters: set[str] = set()
    unique_catalogue_twins: set[str] = set()
    unique_components: set[str] = set()
    unique_load_cases: set[str] = set()
    part_load_case_links = 0

    for entry in crosswalk.get("parts", []):
        if not isinstance(entry, dict):
            raise ContractError("crosswalk_part")
        matches = entry.get("pet_occurrence_matches", [])
        if not matches:
            continue
        part_id = entry.get("part_id")
        if not isinstance(part_id, str):
            raise ContractError("part_id")
        master_ids = sorted(
            {
                match["part_master_twin_id"]
                for match in matches
                if isinstance(match, dict)
                and isinstance(match.get("part_master_twin_id"), str)
            }
        )
        if not master_ids:
            raise ContractError(f"matched_part_without_master:{part_id}")
        component_ids = PART_COMPONENT_IDS.get(part_id, [])
        unknown_components = set(component_ids) - set(components_by_id)
        if unknown_components:
            raise ContractError(
                f"unknown_engine_components:{part_id}:{sorted(unknown_components)}"
            )
        component_records = [components_by_id[value] for value in component_ids]
        virtual_f2 = (
            virtual_f2_summary if part_id == "993-ENG-CARRIER-0001" else None
        )
        valve_surrogate = valve_summary_by_part.get(part_id)
        if valve_surrogate is not None and valve_surrogate.get(
            "linked_pet_part_master_twin_ids"
        ) != master_ids:
            raise ContractError(f"valve_surrogate_master_links:{part_id}")
        k16_surrogate = k16_summary if part_id == EXPECTED_K16_PART_ID else None
        if k16_surrogate is not None and k16_surrogate.get(
            "linked_pet_part_master_twin_ids"
        ) != master_ids:
            raise ContractError(f"k16_surrogate_master_links:{part_id}")
        case_records = [
            case
            for case in load_cases
            if isinstance(case, dict)
            and set(case.get("targets", [])).intersection(component_ids)
        ]
        catalogue_records = [
            catalogue_contract_summary(record)
            for record in catalogue_by_part.get(part_id, [])
        ]
        for record in catalogue_records:
            twin_id = record.get("twin_id")
            if isinstance(twin_id, str):
                unique_catalogue_twins.add(twin_id)
        unique_masters.update(master_ids)
        unique_components.update(component_ids)
        unique_load_cases.update(
            str(case["load_case_id"])
            for case in case_records
            if isinstance(case.get("load_case_id"), str)
        )
        unique_load_cases.update(
            str(case_id)
            for record in catalogue_records
            for case_id in record["load_case_ids"]
            if isinstance(case_id, str)
        )
        part_load_case_links += len(case_records) + sum(
            len(record["load_case_ids"]) for record in catalogue_records
        )
        links.append(
            {
                "part_id": part_id,
                "part_record": entry.get("part_record"),
                "crosswalk_status": entry.get("status"),
                "pet_part_master_twin_ids": master_ids,
                "catalogue_twin_contracts": catalogue_records,
                "engine_component_contracts": component_records,
                "engine_load_case_contracts": case_records,
                "virtual_F2_readiness_contract": virtual_f2,
                "valve_dimensional_surrogate_contract": valve_surrogate,
                "k16_envelope_flow_surrogate_contract": k16_surrogate,
                "evidence_status": "linked_for_review_no_solver_or_release_credit",
                "claims": {
                    "analysis_geometry_available": False,
                    "material_selected_or_qualified": False,
                    "reference_solver_passed": False,
                    "physicsnemo_executed_or_validated": False,
                    "simready_validated": False,
                    "manufacturing_released": False,
                },
            }
        )

    links.sort(key=lambda item: item["part_id"])
    return {
        "$comment": (
            "Raccord F0/F1 entre dossiers d'ingenierie et maitres PET. "
            "Un lien apporte un plan de calcul et des blocages, jamais un resultat."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "catalog_crosswalk": relative(CROSSWALK),
            "catalog_crosswalk_sha256": sha256_file(CROSSWALK),
            "catalogue_engineering": relative(CATALOGUE_ENGINEERING),
            "catalogue_engineering_sha256": sha256_file(CATALOGUE_ENGINEERING),
            "engine_components": relative(ENGINE_COMPONENTS),
            "engine_components_sha256": sha256_file(ENGINE_COMPONENTS),
            "engine_load_cases": relative(ENGINE_LOAD_CASES),
            "engine_load_cases_sha256": sha256_file(ENGINE_LOAD_CASES),
            "engine_carrier_virtual_F2_readiness": relative(
                ENGINE_CARRIER_VIRTUAL_F2
            ),
            "engine_carrier_virtual_F2_readiness_sha256": sha256_file(
                ENGINE_CARRIER_VIRTUAL_F2
            ),
            "valve_dimensional_surrogates": relative(
                VALVE_DIMENSIONAL_SURROGATES
            ),
            "valve_dimensional_surrogates_sha256": sha256_file(
                VALVE_DIMENSIONAL_SURROGATES
            ),
            "k16_envelope_flow_surrogates": relative(
                K16_ENVELOPE_FLOW_SURROGATES
            ),
            "k16_envelope_flow_surrogates_sha256": sha256_file(
                K16_ENVELOPE_FLOW_SURROGATES
            ),
            "charge_air_chain_surrogates": relative(
                CHARGE_AIR_CHAIN_SURROGATES
            ),
            "charge_air_chain_surrogates_sha256": sha256_file(
                CHARGE_AIR_CHAIN_SURROGATES
            ),
            "heat_shield_surrogate": relative(HEAT_SHIELD_SURROGATE),
            "heat_shield_surrogate_sha256": sha256_file(HEAT_SHIELD_SURROGATE),
            "turbo_lubrication_control_topology": relative(
                TURBO_LUBRICATION_CONTROL_TOPOLOGY
            ),
            "turbo_lubrication_control_topology_sha256": sha256_file(
                TURBO_LUBRICATION_CONTROL_TOPOLOGY
            ),
            "oil_tank_circuit_topology": relative(OIL_TANK_CIRCUIT_TOPOLOGY),
            "oil_tank_circuit_topology_sha256": sha256_file(
                OIL_TANK_CIRCUIT_TOPOLOGY
            ),
            "oil_cooler_circuit_topology": relative(OIL_COOLER_CIRCUIT_TOPOLOGY),
            "oil_cooler_circuit_topology_sha256": sha256_file(
                OIL_COOLER_CIRCUIT_TOPOLOGY
            ),
            "engineering_guides_openusd_validation": relative(
                ENGINEERING_GUIDES_OPENUSD_VALIDATION
            ),
            "engineering_guides_openusd_validation_sha256": sha256_file(
                ENGINEERING_GUIDES_OPENUSD_VALIDATION
            ),
        },
        "summary": {
            "linked_catalog_part_records": len(links),
            "linked_pet_part_masters": len(unique_masters),
            "linked_catalogue_twin_contracts": len(unique_catalogue_twins),
            "linked_engine_component_contracts": len(unique_components),
            "unique_load_case_contracts": len(unique_load_cases),
            "part_to_load_case_links": part_load_case_links,
            "linked_virtual_F2_readiness_contracts": sum(
                link["virtual_F2_readiness_contract"] is not None for link in links
            ),
            "linked_mass_constrained_structural_surrogates": sum(
                bool(
                    link.get("virtual_F2_readiness_contract", {}).get(
                        "mass_constraint_closed"
                    )
                )
                for link in links
                if link.get("virtual_F2_readiness_contract") is not None
            ),
            "mass_constrained_surrogate_component_credits": 0,
            "linked_valve_dimensional_surrogate_contracts": sum(
                link["valve_dimensional_surrogate_contract"] is not None
                for link in links
            ),
            "linked_valve_dimensional_surrogate_variants": sum(
                link.get("valve_dimensional_surrogate_contract", {}).get(
                    "variant_count", 0
                )
                for link in links
                if link.get("valve_dimensional_surrogate_contract") is not None
            ),
            "linked_pet_masters_with_valve_dimensional_surrogates": len(
                {
                    master_id
                    for link in links
                    if link.get("valve_dimensional_surrogate_contract") is not None
                    for master_id in link["pet_part_master_twin_ids"]
                }
            ),
            "valve_dimensional_surrogate_component_CAE_credits": 0,
            "linked_k16_envelope_flow_surrogate_contracts": sum(
                link["k16_envelope_flow_surrogate_contract"] is not None
                for link in links
            ),
            "linked_k16_envelope_flow_surrogate_variants": sum(
                link.get("k16_envelope_flow_surrogate_contract", {}).get(
                    "variant_count", 0
                )
                for link in links
                if link.get("k16_envelope_flow_surrogate_contract") is not None
            ),
            "linked_pet_masters_with_k16_envelope_flow_surrogates": len(
                {
                    master_id
                    for link in links
                    if link.get("k16_envelope_flow_surrogate_contract") is not None
                    for master_id in link["pet_part_master_twin_ids"]
                }
            ),
            "k16_evaluated_zeroD_operating_points": 0,
            "k16_envelope_flow_surrogate_component_CAE_credits": 0,
            "linked_charge_air_chain_surrogate_contracts": len(
                charge_air_reference_links
            ),
            "linked_charge_air_chain_surrogate_variants": len(
                charge_air_reference_links
            ),
            "linked_pet_masters_with_charge_air_chain_surrogates": len(
                {
                    master_id
                    for link in charge_air_reference_links
                    for master_id in link["pet_part_master_twin_ids"]
                }
            ),
            "charge_air_evaluated_zeroD_operating_points": 0,
            "charge_air_chain_surrogate_component_CAE_credits": 0,
            "linked_heat_shield_thermal_surrogate_contracts": 1,
            "linked_pet_masters_with_heat_shield_thermal_surrogate": 1,
            "heat_shield_evaluated_thermal_operating_points": 0,
            "heat_shield_thermal_surrogate_component_CAE_credits": 0,
            "linked_turbo_lubrication_control_topology_contracts": len(
                turbo_topology_reference_links
            ),
            "linked_pet_masters_with_turbo_lubrication_control_topology": len(
                {
                    master_id
                    for link in turbo_topology_reference_links
                    for master_id in link["pet_part_master_twin_ids"]
                }
            ),
            "turbo_lubrication_control_symbolic_equations": turbo_lubrication_control.get(
                "summary", {}
            ).get("symbolic_equation_contracts"),
            "turbo_lubrication_control_blocked_load_cases": turbo_lubrication_control.get(
                "summary", {}
            ).get("blocked_reference_load_cases"),
            "turbo_lubrication_control_component_CAE_credits": 0,
            "linked_oil_tank_circuit_topology_contracts": len(
                oil_tank_reference_links
            ),
            "linked_pet_masters_with_oil_tank_circuit_topology": len(
                {
                    master_id
                    for link in oil_tank_reference_links
                    for master_id in link["pet_part_master_twin_ids"]
                }
            ),
            "oil_tank_circuit_symbolic_equations": oil_tank_circuit.get(
                "summary", {}
            ).get("symbolic_equation_contracts"),
            "oil_tank_circuit_blocked_load_cases": oil_tank_circuit.get(
                "summary", {}
            ).get("blocked_reference_load_cases"),
            "oil_tank_circuit_component_CAE_credits": 0,
            "linked_oil_cooler_circuit_topology_contracts": len(
                oil_cooler_reference_links
            ),
            "linked_pet_masters_with_oil_cooler_circuit_topology": len(
                {
                    master_id
                    for link in oil_cooler_reference_links
                    for master_id in link["pet_part_master_twin_ids"]
                }
            ),
            "oil_cooler_circuit_symbolic_equations": oil_cooler_circuit.get(
                "summary", {}
            ).get("symbolic_equation_contracts"),
            "oil_cooler_circuit_blocked_load_cases": oil_cooler_circuit.get(
                "summary", {}
            ).get("blocked_reference_load_cases"),
            "oil_cooler_circuit_component_CAE_credits": 0,
            "strict_openusd_validated_engineering_guide_stages": int(
                engineering_guides_validation.get("scope", {}).get(
                    "validated_stage_count", 0
                )
            ),
            "nvidia_asset_validator_passes": 0,
            "analysis_geometry_available": 0,
            "qualified_material_decisions": 0,
            "reference_solver_results": 0,
            "physicsnemo_results": 0,
            "simready_assets": 0,
            "manufacturing_releases": 0,
        },
        "physicsnemo_policy": {
            "execution_enabled": False,
            "role": "surrogate_only_after_validated_reference_solver_dataset",
        },
        "links": links,
        "declared_reference_links": declared_reference_links,
    }


def validate(contract: dict[str, Any]) -> None:
    boundary = contract.get("source_boundary", {})
    for name, path in (
        ("catalog_crosswalk", CROSSWALK),
        ("catalogue_engineering", CATALOGUE_ENGINEERING),
        ("engine_components", ENGINE_COMPONENTS),
        ("engine_load_cases", ENGINE_LOAD_CASES),
        ("engine_carrier_virtual_F2_readiness", ENGINE_CARRIER_VIRTUAL_F2),
        ("valve_dimensional_surrogates", VALVE_DIMENSIONAL_SURROGATES),
        ("k16_envelope_flow_surrogates", K16_ENVELOPE_FLOW_SURROGATES),
        ("charge_air_chain_surrogates", CHARGE_AIR_CHAIN_SURROGATES),
        ("heat_shield_surrogate", HEAT_SHIELD_SURROGATE),
        (
            "turbo_lubrication_control_topology",
            TURBO_LUBRICATION_CONTROL_TOPOLOGY,
        ),
        ("oil_tank_circuit_topology", OIL_TANK_CIRCUIT_TOPOLOGY),
        ("oil_cooler_circuit_topology", OIL_COOLER_CIRCUIT_TOPOLOGY),
        (
            "engineering_guides_openusd_validation",
            ENGINEERING_GUIDES_OPENUSD_VALIDATION,
        ),
    ):
        if boundary.get(f"{name}_sha256") != sha256_file(path):
            raise ContractError(f"source_digest:{name}")
    summary = contract.get("summary", {})
    expected = {
        "linked_catalog_part_records": 4,
        "linked_pet_part_masters": 8,
        "linked_catalogue_twin_contracts": 3,
        "linked_engine_component_contracts": 4,
        "unique_load_case_contracts": 10,
        "part_to_load_case_links": 13,
        "linked_virtual_F2_readiness_contracts": 1,
        "linked_mass_constrained_structural_surrogates": 1,
        "mass_constrained_surrogate_component_credits": 0,
        "linked_valve_dimensional_surrogate_contracts": 2,
        "linked_valve_dimensional_surrogate_variants": 3,
        "linked_pet_masters_with_valve_dimensional_surrogates": 3,
        "valve_dimensional_surrogate_component_CAE_credits": 0,
        "linked_k16_envelope_flow_surrogate_contracts": 1,
        "linked_k16_envelope_flow_surrogate_variants": 2,
        "linked_pet_masters_with_k16_envelope_flow_surrogates": 4,
        "k16_evaluated_zeroD_operating_points": 0,
        "k16_envelope_flow_surrogate_component_CAE_credits": 0,
        "linked_charge_air_chain_surrogate_contracts": 5,
        "linked_charge_air_chain_surrogate_variants": 5,
        "linked_pet_masters_with_charge_air_chain_surrogates": 5,
        "charge_air_evaluated_zeroD_operating_points": 0,
        "charge_air_chain_surrogate_component_CAE_credits": 0,
        "linked_heat_shield_thermal_surrogate_contracts": 1,
        "linked_pet_masters_with_heat_shield_thermal_surrogate": 1,
        "heat_shield_evaluated_thermal_operating_points": 0,
        "heat_shield_thermal_surrogate_component_CAE_credits": 0,
        "linked_turbo_lubrication_control_topology_contracts": 40,
        "linked_pet_masters_with_turbo_lubrication_control_topology": 40,
        "turbo_lubrication_control_symbolic_equations": 10,
        "turbo_lubrication_control_blocked_load_cases": 6,
        "turbo_lubrication_control_component_CAE_credits": 0,
        "linked_oil_tank_circuit_topology_contracts": 81,
        "linked_pet_masters_with_oil_tank_circuit_topology": 81,
        "oil_tank_circuit_symbolic_equations": 11,
        "oil_tank_circuit_blocked_load_cases": 7,
        "oil_tank_circuit_component_CAE_credits": 0,
        "linked_oil_cooler_circuit_topology_contracts": 43,
        "linked_pet_masters_with_oil_cooler_circuit_topology": 43,
        "oil_cooler_circuit_symbolic_equations": 14,
        "oil_cooler_circuit_blocked_load_cases": 8,
        "oil_cooler_circuit_component_CAE_credits": 0,
        "strict_openusd_validated_engineering_guide_stages": 8,
        "nvidia_asset_validator_passes": 0,
    }
    for field, value in expected.items():
        if summary.get(field) != value:
            raise ContractError(f"summary:{field}:{summary.get(field)}:{value}")
    for field in (
        "analysis_geometry_available",
        "qualified_material_decisions",
        "reference_solver_results",
        "physicsnemo_results",
        "simready_assets",
        "manufacturing_releases",
    ):
        if summary.get(field) != 0:
            raise ContractError(f"overclaim:{field}")
    reference_links = contract.get("declared_reference_links")
    if not isinstance(reference_links, list) or len(reference_links) != 170:
        raise ContractError("declared_reference_links")
    expected_charge_references = {
        "99311033053",
        "99311034054",
        "99311063256",
        "99311063356",
        "99360611400",
    }
    charge_links = [
        link
        for link in reference_links
        if link.get("charge_air_chain_surrogate_contract") is not None
    ]
    if {
        link.get("normalized_oem_reference") for link in charge_links
    } != expected_charge_references:
        raise ContractError("charge_air_reference_links")
    if len(
        {
            master_id
            for link in charge_links
            for master_id in link.get("pet_part_master_twin_ids", [])
        }
    ) != 5:
        raise ContractError("charge_air_master_links")
    for link in charge_links:
        surrogate = link.get("charge_air_chain_surrogate_contract")
        if not isinstance(surrogate, dict):
            raise ContractError("charge_air_surrogate_link")
        if (
            surrogate.get("symbolic_zeroD_equation_count") != 8
            or surrogate.get("evaluated_zeroD_operating_points") != 0
            or surrogate.get("selected_interface_coordinate_count") != 0
            or surrogate.get("F1_envelope_guide") is not True
            or surrogate.get("openusd_strict_validation") != "passed"
            or surrogate.get("nvidia_asset_validator")
            != "not_run_preflight_blocked"
        ):
            raise ContractError("charge_air_surrogate_counts")
        for field in (
            "F2_interface_geometry",
            "F3_analysis_geometry",
            "qualified_material_decision",
            "component_CAE_credit",
            "physicsnemo_execution_enabled",
        ):
            if surrogate.get(field) is not False:
                raise ContractError(f"charge_air_surrogate_overclaim:{field}")
        if any(link.get("claims", {}).values()):
            raise ContractError("charge_air_link_claim")
    heat_links = [
        link
        for link in reference_links
        if link.get("heat_shield_thermal_surrogate_contract") is not None
    ]
    if len(heat_links) != 1 or heat_links[0].get("normalized_oem_reference") != (
        "99312311351"
    ):
        raise ContractError("heat_shield_reference_link")
    heat = heat_links[0]["heat_shield_thermal_surrogate_contract"]
    if (
        heat.get("symbolic_thermal_equation_count") != 7
        or heat.get("blocked_reference_load_case_count") != 4
        or heat.get("unknown_engineering_parameter_count") != 25
        or heat.get("evaluated_thermal_operating_points") != 0
        or heat.get("selected_interface_coordinate_count") != 0
        or heat.get("F1_envelope_thermal_readiness") is not True
        or heat.get("openusd_strict_validation") != "passed"
        or heat.get("nvidia_asset_validator") != "not_run_preflight_blocked"
    ):
        raise ContractError("heat_shield_surrogate_counts")
    for field in (
        "F2_interface_geometry",
        "F3_analysis_geometry",
        "qualified_material_decision",
        "component_CAE_credit",
        "physicsnemo_execution_enabled",
    ):
        if heat.get(field) is not False:
            raise ContractError(f"heat_shield_surrogate_overclaim:{field}")
    if any(heat_links[0].get("claims", {}).values()):
        raise ContractError("heat_shield_link_claim")
    turbo_topology_links = [
        link
        for link in reference_links
        if link.get("turbo_lubrication_control_topology_contract") is not None
    ]
    if len(turbo_topology_links) != 40 or len(
        {
            master_id
            for link in turbo_topology_links
            for master_id in link.get("pet_part_master_twin_ids", [])
        }
    ) != 40:
        raise ContractError("turbo_lubrication_control_topology_links")
    for link in turbo_topology_links:
        topology = link.get("turbo_lubrication_control_topology_contract")
        if not isinstance(topology, dict):
            raise ContractError("turbo_lubrication_control_topology_link")
        if (
            topology.get("symbolic_equation_count") != 10
            or topology.get("blocked_reference_load_case_count") != 6
            or topology.get("unknown_engineering_parameter_count") != 36
            or topology.get("known_interface_coordinate_count") != 0
            or topology.get("F1_nonspatial_topology_readiness") is not True
            or topology.get("openusd_strict_validation") != "passed"
            or topology.get("nvidia_asset_validator")
            != "not_run_preflight_blocked"
        ):
            raise ContractError("turbo_lubrication_control_topology_counts")
        for field in (
            "F2_interface_geometry",
            "F3_analysis_geometry",
            "qualified_material_decision",
            "component_CAE_credit",
            "physicsnemo_execution_enabled",
        ):
            if topology.get(field) is not False:
                raise ContractError(
                    f"turbo_lubrication_control_topology_overclaim:{field}"
                )
        if any(link.get("claims", {}).values()):
            raise ContractError("turbo_lubrication_control_topology_link_claim")
    oil_tank_links = [
        link
        for link in reference_links
        if link.get("oil_tank_circuit_topology_contract") is not None
    ]
    if len(oil_tank_links) != 81 or len(
        {
            master_id
            for link in oil_tank_links
            for master_id in link.get("pet_part_master_twin_ids", [])
        }
    ) != 81:
        raise ContractError("oil_tank_circuit_topology_links")
    for link in oil_tank_links:
        topology = link.get("oil_tank_circuit_topology_contract")
        if not isinstance(topology, dict):
            raise ContractError("oil_tank_circuit_topology_link")
        if (
            topology.get("symbolic_equation_count") != 11
            or topology.get("blocked_reference_load_case_count") != 7
            or topology.get("unknown_engineering_parameter_count") != 40
            or topology.get("known_interface_coordinate_count") != 0
            or topology.get("F1_nonspatial_topology_readiness") is not True
            or topology.get("openusd_strict_validation") != "passed"
            or topology.get("nvidia_asset_validator")
            != "not_run_preflight_blocked"
        ):
            raise ContractError("oil_tank_circuit_topology_counts")
        for field in (
            "F2_interface_geometry",
            "F3_analysis_geometry",
            "qualified_material_decision",
            "component_CAE_credit",
            "physicsnemo_execution_enabled",
        ):
            if topology.get(field) is not False:
                raise ContractError(f"oil_tank_circuit_topology_overclaim:{field}")
        if any(link.get("claims", {}).values()):
            raise ContractError("oil_tank_circuit_topology_link_claim")
    oil_cooler_links = [
        link
        for link in reference_links
        if link.get("oil_cooler_circuit_topology_contract") is not None
    ]
    if len(oil_cooler_links) != 43 or len(
        {
            master_id
            for link in oil_cooler_links
            for master_id in link.get("pet_part_master_twin_ids", [])
        }
    ) != 43:
        raise ContractError("oil_cooler_circuit_topology_links")
    for link in oil_cooler_links:
        topology = link.get("oil_cooler_circuit_topology_contract")
        if not isinstance(topology, dict):
            raise ContractError("oil_cooler_circuit_topology_link")
        if (
            topology.get("symbolic_equation_count") != 14
            or topology.get("blocked_reference_load_case_count") != 8
            or topology.get("unknown_engineering_parameter_count") != 44
            or topology.get("known_interface_coordinate_count") != 0
            or topology.get("F1_nonspatial_topology_readiness") is not True
            or topology.get("openusd_strict_validation") != "passed"
            or topology.get("nvidia_asset_validator")
            != "not_run_preflight_blocked"
        ):
            raise ContractError("oil_cooler_circuit_topology_counts")
        for field in (
            "F2_interface_geometry",
            "F3_analysis_geometry",
            "qualified_material_decision",
            "component_CAE_credit",
            "physicsnemo_execution_enabled",
        ):
            if topology.get(field) is not False:
                raise ContractError(f"oil_cooler_circuit_topology_overclaim:{field}")
        if any(link.get("claims", {}).values()):
            raise ContractError("oil_cooler_circuit_topology_link_claim")
    if contract.get("physicsnemo_policy", {}).get("execution_enabled") is not False:
        raise ContractError("physicsnemo_execution")
    links = contract.get("links")
    if not isinstance(links, list) or len(links) != 4:
        raise ContractError("links")
    virtual_links = [
        link
        for link in links
        if link.get("virtual_F2_readiness_contract") is not None
    ]
    if len(virtual_links) != 1 or virtual_links[0].get("part_id") != (
        "993-ENG-CARRIER-0001"
    ):
        raise ContractError("virtual_F2_link")
    virtual = virtual_links[0]["virtual_F2_readiness_contract"]
    if (
        virtual.get("interface_hypothesis_count") != 2
        or virtual.get("unknown_parameter_count") != 19
        or virtual.get("blocked_load_case_count") != 8
        or virtual.get("mass_constrained_surrogate_status")
        != "F1_mass_constrained_structural_surrogate_no_component_credit"
        or virtual.get("mass_constraint_closed") is not True
        or virtual.get("interface_search_domain_count") != 2
        or virtual.get("selected_interface_point_count") != 0
    ):
        raise ContractError("virtual_F2_counts")
    if virtual.get("mass_constrained_surrogate_component_credit") is not False:
        raise ContractError("virtual_F2_mass_surrogate_credit")
    if virtual.get("openusd_strict_validation") != "passed":
        raise ContractError("virtual_F2_openusd_validation")
    if virtual.get("nvidia_asset_validator") != "not_run_preflight_blocked":
        raise ContractError("virtual_F2_nvidia_validator_overclaim")
    for field in (
        "F2_interface_geometry",
        "reference_CAE_passed",
        "physicsnemo_validated",
        "simready_validated",
    ):
        if virtual.get(field) is not False:
            raise ContractError(f"virtual_F2_overclaim:{field}")
    valve_links = [
        link
        for link in links
        if link.get("valve_dimensional_surrogate_contract") is not None
    ]
    if {link.get("part_id") for link in valve_links} != {
        "993-ENG-INTAKE-VALVE-F1-0001",
        "993-ENG-EXHAUST-VALVE-F1-0001",
    }:
        raise ContractError("valve_dimensional_surrogate_links")
    if sum(
        link["valve_dimensional_surrogate_contract"].get("variant_count", 0)
        for link in valve_links
    ) != 3:
        raise ContractError("valve_dimensional_surrogate_variant_count")
    for link in valve_links:
        valve = link["valve_dimensional_surrogate_contract"]
        if valve.get("F1_dimensional_surrogate") is not True:
            raise ContractError("valve_dimensional_surrogate_missing")
        if valve.get("openusd_strict_validation") != "passed":
            raise ContractError("valve_dimensional_surrogate_openusd_validation")
        if valve.get("nvidia_asset_validator") != "not_run_preflight_blocked":
            raise ContractError("valve_dimensional_surrogate_nvidia_validator_overclaim")
        for field in (
            "F2_interface_geometry",
            "analysis_geometry_available",
            "qualified_material_decision",
            "component_CAE_credit",
        ):
            if valve.get(field) is not False:
                raise ContractError(f"valve_dimensional_surrogate_overclaim:{field}")
    k16_links = [
        link
        for link in links
        if link.get("k16_envelope_flow_surrogate_contract") is not None
    ]
    if len(k16_links) != 1 or k16_links[0].get("part_id") != EXPECTED_K16_PART_ID:
        raise ContractError("k16_envelope_flow_surrogate_links")
    k16 = k16_links[0]["k16_envelope_flow_surrogate_contract"]
    if (
        k16.get("variant_count") != 2
        or len(k16.get("linked_pet_part_master_twin_ids", [])) != 4
        or k16.get("right_side_wheel_diameter_guide_count") != 4
        or k16.get("symbolic_zeroD_equation_count") != 6
        or k16.get("evaluated_zeroD_operating_points") != 0
        or k16.get("selected_interface_coordinate_count") != 0
    ):
        raise ContractError("k16_envelope_flow_surrogate_counts")
    if k16.get("F1_envelope_and_diameter_guides") is not True:
        raise ContractError("k16_envelope_flow_surrogate_missing")
    if k16.get("openusd_strict_validation") != "passed":
        raise ContractError("k16_envelope_flow_surrogate_openusd_validation")
    if k16.get("nvidia_asset_validator") != "not_run_preflight_blocked":
        raise ContractError("k16_envelope_flow_surrogate_nvidia_validator_overclaim")
    for field in (
        "F2_interface_geometry",
        "F3_analysis_geometry",
        "qualified_material_decision",
        "component_CAE_credit",
        "physicsnemo_execution_enabled",
    ):
        if k16.get(field) is not False:
            raise ContractError(f"k16_envelope_flow_surrogate_overclaim:{field}")
    for link in links:
        if any(link.get("claims", {}).values()):
            raise ContractError(f"link_claim:{link.get('part_id')}")
        for record in link.get("catalogue_twin_contracts", []):
            if record.get("selected_functional_route") is not None:
                raise ContractError(f"selected_process:{link.get('part_id')}")
            if any(
                not str(status).startswith("blocked_")
                for status in record.get("load_case_statuses", [])
            ):
                raise ContractError(f"catalogue_load_case_status:{link.get('part_id')}")
        for case in link.get("engine_load_case_contracts", []):
            if not str(case.get("status", "")).startswith("blocked_"):
                raise ContractError(f"engine_load_case_status:{case.get('load_case_id')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    args = parser.parse_args(argv)
    try:
        contract = build()
        validate(contract)
        expected = render(contract)
        if args.write:
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(expected, encoding="utf-8")
            print(f"wrote {relative(OUTPUT)}")
            return 0
        if not OUTPUT.exists():
            print(f"missing:{OUTPUT}")
            return 1
        if args.check and OUTPUT.read_text(encoding="utf-8") != expected:
            print(f"stale:{OUTPUT}")
            return 1
        validate(load_json(OUTPUT))
        print(f"valid {relative(OUTPUT)}")
        return 0
    except ContractError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
