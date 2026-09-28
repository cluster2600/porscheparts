#!/usr/bin/env python3
"""Generate the fail-closed functional flow topology for the virtual 993."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / "twins" / "vehicle-993" / "program-definition.json"
SKELETON = ROOT / "catalog" / "reference" / "993-assembly-skeleton.json"
TURBO_SEED = ROOT / "twins" / "vehicle-993" / "turbo-integration-seed-f0.json"
OUTPUT = ROOT / "twins" / "vehicle-993" / "functional-flow-graph-f0.json"


class ContractError(ValueError):
    """Raised when the functional topology is incomplete or overclaims physics."""


FLOW_TYPES: dict[str, dict[str, Any]] = {
    "configuration_metadata": {
        "state_variables": ["variant_id", "revision_id", "option_state"],
        "conservation_law": None,
        "reference_model": "configuration_constraint_graph",
    },
    "mechanical_power": {
        "state_variables": ["torque_Nm", "angular_speed_rad_s", "power_W"],
        "conservation_law": "power_W=torque_Nm*angular_speed_rad_s",
        "reference_model": "rotational_power_balance_and_multibody",
    },
    "structural_wrench": {
        "state_variables": [
            "force_vector_N",
            "moment_vector_Nm",
            "displacement_vector_m",
            "rotation_vector_rad",
        ],
        "conservation_law": "sum_forces_N=0_and_sum_moments_Nm=0",
        "reference_model": "interface_free_body_then_CalculiX",
    },
    "thermofluid_mass_energy": {
        "state_variables": [
            "mass_flow_kg_s",
            "pressure_Pa",
            "temperature_K",
            "specific_enthalpy_J_kg",
        ],
        "conservation_law": "sum_mass_flow_kg_s=0_and_sum_enthalpy_flow_W=0",
        "reference_model": "zero_one_dimensional_network_then_OpenFOAM",
    },
    "electrical_power_and_signal": {
        "state_variables": ["voltage_V", "current_A", "power_W", "signal_value"],
        "conservation_law": "Kirchhoff_current_voltage_and_power_balance",
        "reference_model": "circuit_graph_then_SPICE_and_state_machines",
    },
    "hydraulic_power": {
        "state_variables": [
            "pressure_Pa",
            "volume_flow_m3_s",
            "fluid_temperature_K",
            "power_W",
        ],
        "conservation_law": "flow_continuity_and_power_W=pressure_Pa*volume_flow_m3_s",
        "reference_model": "zero_dimensional_hydraulic_network",
    },
    "kinematic_command": {
        "state_variables": ["position_m_or_rad", "velocity_m_s_or_rad_s", "effort_N_or_Nm"],
        "conservation_law": "compatible_joint_motion_and_virtual_work",
        "reference_model": "analytical_kinematics_then_multibody",
    },
    "vehicle_state": {
        "state_variables": [
            "velocity_m_s",
            "linear_acceleration_m_s2",
            "yaw_rate_rad_s",
            "wheel_speed_rad_s",
        ],
        "conservation_law": "vehicle_linear_and_angular_momentum_balance",
        "reference_model": "bicycle_then_7DoF_14DoF_and_multibody",
    },
    "thermal_energy": {
        "state_variables": ["temperature_K", "heat_rate_W", "thermal_resistance_K_W"],
        "conservation_law": "sum_heat_rate_W_plus_stored_energy_rate_W=0",
        "reference_model": "thermal_resistance_network_then_CHT",
    },
    "occupant_control_load": {
        "state_variables": ["force_N", "moment_Nm", "travel_m_or_rad"],
        "conservation_law": "control_input_reaction_and_travel_compatibility",
        "reference_model": "free_body_and_ergonomic_envelope_model",
    },
}


def edge(
    edge_id: str,
    source: str,
    target: str,
    flow_type: str,
    direction: str,
    role: str,
) -> dict[str, Any]:
    return {
        "flow_edge_id": edge_id,
        "source_system_id": source,
        "target_system_id": target,
        "flow_type_id": flow_type,
        "direction": direction,
        "engineering_role": role,
        "topology_status": "engineering_hypothesis_requires_interface_evidence",
        "source_port_id": None,
        "target_port_id": None,
        "geometry_interface_id": None,
        "parameter_values": {},
        "balance_residual": None,
        "acceptance_threshold": None,
        "reference_solver_result": None,
        "physicsnemo_result": None,
        "simready_binding": None,
    }


PHYSICAL_EDGES = [
    edge("FLOW-1XX-2XX-THERMOFLUID", "1xx", "2xx", "thermofluid_mass_energy", "bidirectional_coupling", "fuel_charge_air_exhaust_and_heat_exchange"),
    edge("FLOW-1XX-3XX-POWER", "1xx", "3xx", "mechanical_power", "source_to_target", "engine_crankshaft_to_clutch_and_transmission"),
    edge("FLOW-1XX-8XX-MOUNTS", "1xx", "8xx", "structural_wrench", "bidirectional_equilibrium", "powertrain_loads_to_body_and_mount_reactions"),
    edge("FLOW-1XX-9XX-CONTROL", "1xx", "9xx", "electrical_power_and_signal", "bidirectional_coupling", "starting_charging_ignition_injection_and_engine_signals"),
    edge("FLOW-2XX-8XX-THERMAL", "2xx", "8xx", "thermal_energy", "bidirectional_coupling", "hot_exhaust_fuel_and_charge_air_environment_to_body"),
    edge("FLOW-2XX-9XX-CONTROL", "2xx", "9xx", "electrical_power_and_signal", "bidirectional_coupling", "fuel_pumps_sensors_actuators_and_diagnostics"),
    edge("FLOW-3XX-5XX-POWER", "3xx", "5xx", "mechanical_power", "source_to_target", "gearbox_differential_and_rear_wheel_drive"),
    edge("FLOW-3XX-7XX-CLUTCH", "3xx", "7xx", "hydraulic_power", "bidirectional_coupling", "clutch_actuation_and_pedal_reaction"),
    edge("FLOW-3XX-9XX-SIGNALS", "3xx", "9xx", "electrical_power_and_signal", "bidirectional_coupling", "starter_reverse_speed_and_driveline_signals"),
    edge("FLOW-4XX-5XX-STATE", "4xx", "5xx", "vehicle_state", "bidirectional_coupling", "front_rear_chassis_state_and_road_contact_consistency"),
    edge("FLOW-4XX-6XX-BRAKE", "6xx", "4xx", "mechanical_power", "source_to_target", "front_brake_torque_and_wheel_energy_dissipation"),
    edge("FLOW-4XX-7XX-STEERING", "7xx", "4xx", "kinematic_command", "source_to_target", "steering_wheel_column_rack_and_road_wheel_command"),
    edge("FLOW-4XX-8XX-LOAD", "4xx", "8xx", "structural_wrench", "bidirectional_equilibrium", "front_suspension_and_steering_loads_to_body"),
    edge("FLOW-5XX-6XX-BRAKE", "6xx", "5xx", "mechanical_power", "source_to_target", "rear_brake_torque_and_wheel_energy_dissipation"),
    edge("FLOW-5XX-8XX-LOAD", "5xx", "8xx", "structural_wrench", "bidirectional_equilibrium", "rear_suspension_and_driveline_loads_to_body"),
    edge("FLOW-6XX-7XX-HYDRAULIC", "7xx", "6xx", "hydraulic_power", "source_to_target", "driver_brake_input_to_master_cylinder_and_brake_network"),
    edge("FLOW-6XX-9XX-CONTROL", "6xx", "9xx", "electrical_power_and_signal", "bidirectional_coupling", "brake_switch_warning_and_control_signals"),
    edge("FLOW-7XX-8XX-CONTROL-LOAD", "7xx", "8xx", "occupant_control_load", "bidirectional_equilibrium", "pedal_column_seat_and_body_control_reactions"),
    edge("FLOW-7XX-9XX-SIGNALS", "7xx", "9xx", "electrical_power_and_signal", "bidirectional_coupling", "driver_switches_interlocks_and_feedback"),
    edge("FLOW-8XX-9XX-BODY-ELECTRICAL", "9xx", "8xx", "electrical_power_and_signal", "bidirectional_coupling", "lighting_body_equipment_HVAC_and_cabin_signals"),
]


MISSIONS = [
    {
        "mission_id": "MISSION-993-START-IDLE",
        "name": "demarrage_et_ralenti",
        "required_system_ids": ["1xx", "2xx", "3xx", "7xx", "8xx", "9xx"],
        "required_flow_edge_ids": [
            "FLOW-1XX-2XX-THERMOFLUID",
            "FLOW-1XX-3XX-POWER",
            "FLOW-1XX-8XX-MOUNTS",
            "FLOW-1XX-9XX-CONTROL",
            "FLOW-3XX-7XX-CLUTCH",
        ],
    },
    {
        "mission_id": "MISSION-993-ACCELERATION",
        "name": "acceleration_longitudinale",
        "required_system_ids": ["1xx", "2xx", "3xx", "4xx", "5xx", "8xx", "9xx"],
        "required_flow_edge_ids": [
            "FLOW-1XX-2XX-THERMOFLUID",
            "FLOW-1XX-3XX-POWER",
            "FLOW-3XX-5XX-POWER",
            "FLOW-4XX-5XX-STATE",
            "FLOW-1XX-8XX-MOUNTS",
        ],
    },
    {
        "mission_id": "MISSION-993-BRAKING",
        "name": "freinage_stabilise_et_transitoire",
        "required_system_ids": ["4xx", "5xx", "6xx", "7xx", "8xx", "9xx"],
        "required_flow_edge_ids": [
            "FLOW-6XX-7XX-HYDRAULIC",
            "FLOW-4XX-6XX-BRAKE",
            "FLOW-5XX-6XX-BRAKE",
            "FLOW-4XX-8XX-LOAD",
            "FLOW-5XX-8XX-LOAD",
        ],
    },
    {
        "mission_id": "MISSION-993-CORNERING",
        "name": "virage_stationnaire_et_transition",
        "required_system_ids": ["4xx", "5xx", "7xx", "8xx"],
        "required_flow_edge_ids": [
            "FLOW-4XX-5XX-STATE",
            "FLOW-4XX-7XX-STEERING",
            "FLOW-4XX-8XX-LOAD",
            "FLOW-5XX-8XX-LOAD",
        ],
    },
    {
        "mission_id": "MISSION-993-THERMAL-SOAK",
        "name": "montee_en_temperature_et_arret_chaud",
        "required_system_ids": ["1xx", "2xx", "8xx", "9xx"],
        "required_flow_edge_ids": [
            "FLOW-1XX-2XX-THERMOFLUID",
            "FLOW-2XX-8XX-THERMAL",
            "FLOW-1XX-9XX-CONTROL",
            "FLOW-8XX-9XX-BODY-ELECTRICAL",
        ],
    },
    {
        "mission_id": "MISSION-993-STEERING-MANOEUVRE",
        "name": "manoeuvre_direction_basse_vitesse",
        "required_system_ids": ["4xx", "5xx", "7xx", "8xx"],
        "required_flow_edge_ids": [
            "FLOW-4XX-7XX-STEERING",
            "FLOW-4XX-5XX-STATE",
            "FLOW-4XX-8XX-LOAD",
            "FLOW-7XX-8XX-CONTROL-LOAD",
        ],
    },
    {
        "mission_id": "MISSION-993-ELECTRICAL-PEAK",
        "name": "charge_electrique_de_pointe",
        "required_system_ids": ["1xx", "2xx", "6xx", "7xx", "8xx", "9xx"],
        "required_flow_edge_ids": [
            "FLOW-1XX-9XX-CONTROL",
            "FLOW-2XX-9XX-CONTROL",
            "FLOW-6XX-9XX-CONTROL",
            "FLOW-7XX-9XX-SIGNALS",
            "FLOW-8XX-9XX-BODY-ELECTRICAL",
        ],
    },
]


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


def route_pairs(definition: dict[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for route in definition.get("system_routes", []):
        source = route.get("system_id")
        if source == "0xx":
            continue
        for target in route.get("integration_interfaces", []):
            if target == "all_systems":
                continue
            pairs.add(tuple(sorted((str(source), str(target)))))
    return pairs


def build() -> dict[str, Any]:
    definition = load_json(DEFINITION)
    skeleton = load_json(SKELETON)
    turbo_seed = load_json(TURBO_SEED)
    system_ids = [str(item["system_id"]) for item in skeleton.get("systems", [])]
    if len(system_ids) != 10 or len(set(system_ids)) != 10:
        raise ContractError("system_ids")
    routes = {
        str(item["system_id"]): item for item in definition.get("system_routes", [])
    }
    if set(routes) != set(system_ids):
        raise ContractError("system_routes")

    configuration_edges = [
        edge(
            f"FLOW-0XX-{target.upper()}-CONFIG",
            "0xx",
            target,
            "configuration_metadata",
            "source_to_target",
            "variant_revision_option_and_quantity_context",
        )
        for target in system_ids
        if target != "0xx"
    ]
    edges = configuration_edges + PHYSICAL_EDGES
    edge_ids = [item["flow_edge_id"] for item in edges]
    if len(edge_ids) != len(set(edge_ids)):
        raise ContractError("duplicate_flow_edge")
    known_edge_ids = set(edge_ids)

    seed_system_counts = turbo_seed.get("coverage", {}).get(
        "candidate_occurrences_by_system", {}
    )
    bindings: list[dict[str, Any]] = []
    system_contracts: list[dict[str, Any]] = []
    for system in skeleton["systems"]:
        system_id = str(system["system_id"])
        related_edges = sorted(
            item["flow_edge_id"]
            for item in edges
            if system_id in (item["source_system_id"], item["target_system_id"])
        )
        illustrations = system.get("illustrations", [])
        for illustration in illustrations:
            illustration_id = str(illustration["illustration"])
            bindings.append(
                {
                    "work_package_id": f"WP-993-{illustration_id}",
                    "catalogue_illustration": illustration_id,
                    "system_id": system_id,
                    "flow_edge_ids": related_edges,
                    "binding_status": "system_level_topology_only_missing_part_ports",
                    "quantified_ports": 0,
                    "closed_balance_equations": 0,
                }
            )
        system_contracts.append(
            {
                "system_id": system_id,
                "name": system.get("name"),
                "criticality": routes[system_id].get("criticality"),
                "simulation_domain_ids": routes[system_id].get(
                    "simulation_domains", []
                ),
                "flow_edge_ids": related_edges,
                "catalogue_illustration_count": len(illustrations),
                "turbo_seed_candidate_occurrence_count": int(
                    seed_system_counts.get(system_id, 0)
                ),
                "port_definition_status": "blocked_missing_F2_component_interfaces",
                "material_property_status": "blocked_unqualified",
                "reference_model_status": "blocked_unquantified_ports_and_boundaries",
                "physicsnemo_status": "blocked_no_reference_dataset",
            }
        )

    mission_contracts = []
    for mission in MISSIONS:
        unknown = set(mission["required_flow_edge_ids"]) - known_edge_ids
        if unknown:
            raise ContractError(f"mission_unknown_edges:{mission['mission_id']}:{sorted(unknown)}")
        mission_contracts.append(
            {
                **mission,
                "status": "blocked_unquantified_system_models_and_interfaces",
                "input_scenario": None,
                "reference_solver_results": [],
                "balance_residuals": {},
                "acceptance_criteria": {},
                "physicsnemo_results": [],
                "functional_pass": False,
            }
        )

    covered_pairs = {
        tuple(sorted((item["source_system_id"], item["target_system_id"])))
        for item in PHYSICAL_EDGES
    }
    expected_pairs = route_pairs(definition)
    return {
        "$comment": (
            "Topologie fonctionnelle F0 des flux du vehicule. Les aretes indiquent les "
            "bilans a fermer; aucun port, parametre ou resultat physique n'est encore qualifie."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "program_definition": relative(DEFINITION),
            "program_definition_sha256": sha256_file(DEFINITION),
            "assembly_skeleton": relative(SKELETON),
            "assembly_skeleton_sha256": sha256_file(SKELETON),
            "turbo_integration_seed": relative(TURBO_SEED),
            "turbo_integration_seed_sha256": sha256_file(TURBO_SEED),
        },
        "scope": {
            "system_count": len(system_contracts),
            "flow_type_count": len(FLOW_TYPES),
            "flow_edge_count": len(edges),
            "configuration_metadata_edge_count": len(configuration_edges),
            "physical_coupling_edge_count": len(PHYSICAL_EDGES),
            "declared_integration_interface_pairs": len(expected_pairs),
            "covered_integration_interface_pairs": len(expected_pairs.intersection(covered_pairs)),
            "work_package_bindings": len(bindings),
            "virtual_mission_contracts": len(mission_contracts),
            "quantified_component_ports": 0,
            "closed_balance_equations": 0,
            "reference_solver_results": 0,
            "physicsnemo_results": 0,
            "simready_bindings": 0,
            "passed_virtual_missions": 0,
            "functioning_vehicle_claim": False,
        },
        "flow_types": FLOW_TYPES,
        "flow_edges": edges,
        "systems": system_contracts,
        "work_package_bindings": bindings,
        "balance_closure_policy": {
            "required_for_each_quantified_edge": [
                "source_and_target_port_identity",
                "common_units_and_sign_convention",
                "source_parameter_and_uncertainty",
                "reference_model_revision",
                "computed_residual",
                "predeclared_acceptance_threshold",
            ],
            "LLM_may_author_topology_and_triage_residuals": True,
            "LLM_may_supply_physical_values_or_pass_a_balance": False,
            "physicsnemo_role": "field_surrogate_only_after_reference_balance_closure",
            "omniverse_role": "bind_validated_ports_transforms_materials_and_results_after_F2_F3",
        },
        "virtual_missions": mission_contracts,
        "assembly_readiness": {
            "functional_topology": "complete_system_level_hypothesis",
            "part_level_ports": "blocked",
            "parameterization": "blocked",
            "reference_models": "blocked",
            "multiphysics_balance_closure": "blocked",
            "PhysicsNeMo": "blocked",
            "Omniverse_SimReady": "blocked",
            "functioning_vehicle": False,
        },
        "prohibited_claims": [
            "flow_edge_is_a_measured_interface",
            "system_topology_is_part_level_connectivity",
            "equation_definition_is_a_solved_balance",
            "mission_contract_is_a_virtual_mission_pass",
            "LLM_topology_is_physical_evidence",
            "flow_graph_authorizes_manufacturing_installation_or_road_use",
        ],
    }


def validate(contract: dict[str, Any]) -> None:
    boundary = contract.get("source_boundary", {})
    for name, path in (
        ("program_definition", DEFINITION),
        ("assembly_skeleton", SKELETON),
        ("turbo_integration_seed", TURBO_SEED),
    ):
        if boundary.get(f"{name}_sha256") != sha256_file(path):
            raise ContractError(f"source_digest:{name}")
    scope = contract.get("scope", {})
    expected = {
        "system_count": 10,
        "flow_type_count": 10,
        "flow_edge_count": 29,
        "configuration_metadata_edge_count": 9,
        "physical_coupling_edge_count": 20,
        "declared_integration_interface_pairs": 20,
        "covered_integration_interface_pairs": 20,
        "work_package_bindings": 239,
        "virtual_mission_contracts": 7,
    }
    for field, value in expected.items():
        if scope.get(field) != value:
            raise ContractError(f"scope:{field}:{scope.get(field)}:{value}")
    for field in (
        "quantified_component_ports",
        "closed_balance_equations",
        "reference_solver_results",
        "physicsnemo_results",
        "simready_bindings",
        "passed_virtual_missions",
    ):
        if scope.get(field) != 0:
            raise ContractError(f"overclaim:{field}")
    if scope.get("functioning_vehicle_claim") is not False:
        raise ContractError("functioning_vehicle_claim")
    edges = contract.get("flow_edges", [])
    edge_ids = {item.get("flow_edge_id") for item in edges}
    if len(edge_ids) != scope["flow_edge_count"]:
        raise ContractError("edge_ids")
    for item in edges:
        if item.get("flow_type_id") not in contract.get("flow_types", {}):
            raise ContractError(f"edge_flow_type:{item.get('flow_edge_id')}")
        if item.get("parameter_values") != {} or item.get("balance_residual") is not None:
            raise ContractError(f"edge_result:{item.get('flow_edge_id')}")
        if item.get("reference_solver_result") is not None:
            raise ContractError(f"edge_solver_result:{item.get('flow_edge_id')}")
        if item.get("physicsnemo_result") is not None:
            raise ContractError(f"edge_physicsnemo_result:{item.get('flow_edge_id')}")
    bindings = contract.get("work_package_bindings", [])
    if len(bindings) != 239 or len({item.get("work_package_id") for item in bindings}) != 239:
        raise ContractError("work_package_bindings")
    if any(item.get("quantified_ports") != 0 for item in bindings):
        raise ContractError("binding_quantified_port")
    missions = contract.get("virtual_missions", [])
    if len(missions) != 7:
        raise ContractError("missions")
    for mission in missions:
        if set(mission.get("required_flow_edge_ids", [])) - edge_ids:
            raise ContractError(f"mission_edges:{mission.get('mission_id')}")
        if mission.get("functional_pass") is not False:
            raise ContractError(f"mission_pass:{mission.get('mission_id')}")
        if mission.get("reference_solver_results") != []:
            raise ContractError(f"mission_solver_results:{mission.get('mission_id')}")
    policy = contract.get("balance_closure_policy", {})
    if policy.get("LLM_may_supply_physical_values_or_pass_a_balance") is not False:
        raise ContractError("llm_overclaim")
    if contract.get("assembly_readiness", {}).get("functioning_vehicle") is not False:
        raise ContractError("assembly_functioning_vehicle")


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
