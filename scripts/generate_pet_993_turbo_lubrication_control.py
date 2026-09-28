#!/usr/bin/env python3
"""Generate a PET 202-16 turbo lubrication/control F1 topology contract.

The PET records identify parts, not their interfaces or dimensions.  The USD
stage is therefore a non-spatial guide graph and never component geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PET_INDEX = ROOT / "twins" / "pet-993" / "index-f0.json"
PORSCHEFANATICS_SOURCE = (
    ROOT / "catalog" / "sources" / "src-porschefanatics-993-turbo-pet.json"
)
K16_REPORT = ROOT / "twins" / "catalogue-parts" / "k16-envelope-flow-readiness-f1.json"
PROGRAM_DEFINITION = ROOT / "twins" / "vehicle-993" / "program-definition.json"
SIMREADY_PREFLIGHT = (
    ROOT / "twins" / "vehicle-993" / "functional-flow-simready-preflight-f0.json"
)
REPORT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "turbo-lubrication-control-topology-readiness-f1.json"
)
USD_OUTPUT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering"
    / "993-turbo-lubrication-control-topology-f1.usda"
)

ILLUSTRATION = "202-16"
EXPECTED_OCCURRENCES = 71
EXPECTED_REFERENCES = 40
EXPECTED_SOURCE_COUNTS = {"pet-993-pdf-rsworkshop": 31, "pet-classic-993": 40}
EXPECTED_PHYSICSNEMO_COMMIT = "4fbfcfd62bf050b48ceec6b438da409b9f4644b3"


class ContractError(ValueError):
    """Raised when evidence is stale or the contract would overclaim."""


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


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ContractError(
                    f"cannot_load:{relative(path)}:{line_number}:{exc}"
                ) from exc
            if not isinstance(value, dict):
                raise ContractError(f"expected_object:{relative(path)}:{line_number}")
            values.append(value)
    return values


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


def source_entry(path: Path, role: str) -> dict[str, str]:
    return {"path": relative(path), "sha256": sha256_file(path), "role": role}


def usd_name(value: str) -> str:
    cleaned = "".join(character if character.isalnum() else "_" for character in value)
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"_{cleaned}"
    return cleaned


def usd_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def part_role(descriptions: list[str]) -> str:
    text = " ".join(descriptions).lower()
    if "turbocharger" in text:
        return "turbocharger_complete_unit"
    if "oil collection container" in text:
        return "oil_collection_container"
    if "vent line" in text:
        return "ventilation_line"
    if "oil pipe" in text:
        return "oil_transport_line"
    if "control box" in text:
        return "turbo_control_box_identity_unresolved"
    if "cover" in text:
        return "protective_cover_identity_unresolved"
    if "seal" in text or "o-ring" in text:
        return "sealing_element"
    if any(token in text for token in ("bracket", "clamp", "clip", "holder")):
        return "support_or_retention"
    if any(
        token in text
        for token in ("screw", "bolt", "nut", "washer", "stud", "plug")
    ):
        return "fastener_or_closure"
    raise ContractError(f"unclassified_description:{descriptions}")


def derive() -> dict[str, Any]:
    index = load_json(PET_INDEX)
    two_xx = [
        item
        for item in index.get("output", {}).get("shards", [])
        if isinstance(item, dict) and item.get("system_id") == "2xx"
    ]
    if len(two_xx) != 1:
        raise ContractError("pet_2xx_shard")
    occurrence_path = ROOT / str(two_xx[0].get("path"))
    if sha256_file(occurrence_path) != two_xx[0].get("sha256"):
        raise ContractError("pet_2xx_shard_digest")
    occurrences = [
        item
        for item in load_jsonl(occurrence_path)
        if item.get("catalogue_context", {}).get("pet_illustration") == ILLUSTRATION
    ]
    if len(occurrences) != EXPECTED_OCCURRENCES:
        raise ContractError(f"pet_occurrence_count:{len(occurrences)}")

    by_reference: dict[str, list[dict[str, Any]]] = {}
    source_counts: dict[str, int] = {}
    for item in occurrences:
        reference = normalize_reference(str(item.get("subject", {}).get("oem_reference", "")))
        if not reference:
            raise ContractError("empty_occurrence_reference")
        by_reference.setdefault(reference, []).append(item)
        source_id = str(item.get("catalogue_context", {}).get("pet_source_id"))
        source_counts[source_id] = source_counts.get(source_id, 0) + 1
    if len(by_reference) != EXPECTED_REFERENCES:
        raise ContractError(f"pet_reference_count:{len(by_reference)}")
    if source_counts != EXPECTED_SOURCE_COUNTS:
        raise ContractError(f"pet_source_counts:{source_counts}")

    masters: dict[str, dict[str, Any]] = {}
    master_sources: list[dict[str, str]] = []
    for shard in index.get("output", {}).get("part_master_shards", []):
        if not isinstance(shard, dict):
            raise ContractError("pet_part_master_shard")
        path = ROOT / str(shard.get("path"))
        if sha256_file(path) != shard.get("sha256"):
            raise ContractError(f"pet_part_master_shard_digest:{relative(path)}")
        records = load_jsonl(path)
        if len(records) != shard.get("record_count"):
            raise ContractError(f"pet_part_master_shard_count:{relative(path)}")
        master_sources.append(source_entry(path, "PET_part_master_shard"))
        for item in records:
            reference = item.get("subject", {}).get("normalized_oem_reference")
            if reference in by_reference:
                if reference in masters:
                    raise ContractError(f"duplicate_part_master:{reference}")
                masters[str(reference)] = item
    if set(masters) != set(by_reference):
        raise ContractError("missing_part_master")

    roster: list[dict[str, Any]] = []
    for reference in sorted(by_reference):
        master = masters[reference]
        selected_occurrences = by_reference[reference]
        documentary = master.get("documentary_graph", {})
        master_occurrence_ids = {
            item.get("occurrence_twin_id")
            for item in documentary.get("occurrences", [])
            if isinstance(item, dict) and item.get("pet_illustration") == ILLUSTRATION
        }
        selected_ids = {item.get("twin_id") for item in selected_occurrences}
        if master_occurrence_ids != selected_ids:
            raise ContractError(f"part_master_occurrence_mismatch:{reference}")
        positions = sorted(
            {
                int(item.get("catalogue_context", {}).get("position"))
                for item in selected_occurrences
            }
        )
        descriptions = sorted(
            {
                str(item.get("subject", {}).get("description"))
                for item in selected_occurrences
            },
            key=lambda value: (value.lower(), value),
        )
        roster.append(
            {
                "normalized_oem_reference": reference,
                "display_references": master.get("subject", {}).get(
                    "display_references", []
                ),
                "descriptions": descriptions,
                "pet_part_master_twin_id": master.get("twin_id"),
                "pet_positions": positions,
                "pet_occurrence_twin_ids": sorted(str(value) for value in selected_ids),
                "pet_source_ids": sorted(
                    {
                        str(item.get("catalogue_context", {}).get("pet_source_id"))
                        for item in selected_occurrences
                    }
                ),
                "role_hypothesis": part_role(descriptions),
                "role_status": "identity_based_candidate_not_interface_proof",
                "side_assignment": None,
                "interface_geometry": None,
                "material": None,
                "vehicle_transform": None,
            }
        )

    porschefanatics = load_json(PORSCHEFANATICS_SOURCE)
    if (
        porschefanatics.get("source_id") != "SRC-PORSCHEFANATICS-993-TURBO-PET"
        or "oil_lines" not in porschefanatics.get("coverage", {}).get("parts", [])
        or porschefanatics.get("quality", {}).get("dimensional_accuracy") != "unknown"
    ):
        raise ContractError("porschefanatics_source_boundary")
    k16 = load_json(K16_REPORT)
    if k16.get("status") != (
        "F1_K16_envelope_and_diameter_guides_complete_zeroD_execution_blocked"
    ):
        raise ContractError("k16_contract")
    program = load_json(PROGRAM_DEFINITION)
    physicsnemo = program.get("physicsnemo_policy", {})
    if (
        physicsnemo.get("execution_enabled") is not False
        or physicsnemo.get("discovered_commit") != EXPECTED_PHYSICSNEMO_COMMIT
    ):
        raise ContractError("physicsnemo_policy")
    preflight = load_json(SIMREADY_PREFLIGHT)
    if (
        preflight.get("status") != "blocked"
        or preflight.get("result_boundary", {}).get("simready_validated") is not False
    ):
        raise ContractError("simready_preflight")
    return {
        "index": index,
        "occurrence_path": occurrence_path,
        "master_sources": master_sources,
        "roster": roster,
        "porschefanatics": porschefanatics,
        "k16": k16,
        "physicsnemo": physicsnemo,
        "preflight": preflight,
        "source_counts": source_counts,
    }


TOPOLOGY_NODES = [
    ("OilSourceBoundary", "oil_source_boundary", (-5.0, 0.0, 0.0)),
    ("DistributionJunction", "distribution_junction", (-3.5, 0.0, 0.0)),
    ("LeftK16BearingSystem", "left_K16_bearing_system", (-1.5, 1.5, 0.0)),
    ("RightK16BearingSystem", "right_K16_bearing_system", (-1.5, -1.5, 0.0)),
    ("LeftOilCollector", "left_oil_collection_boundary", (0.5, 1.5, 0.0)),
    ("RightOilCollector", "right_oil_collection_boundary", (0.5, -1.5, 0.0)),
    ("OilReturnBoundary", "oil_return_boundary", (3.0, 0.0, 0.0)),
    ("VentBoundary", "vent_boundary", (3.0, 2.5, 0.0)),
    ("ControlInput", "control_input_boundary", (-4.0, -3.5, 0.0)),
    ("ControlBoxPair", "control_box_pair_identity_only", (-1.5, -3.5, 0.0)),
    ("WastegateTargetPair", "integrated_wastegate_target_pair_hypothesis", (1.5, -3.5, 0.0)),
]

TOPOLOGY_EDGES = [
    ("OilSupply", "OilSourceBoundary", "DistributionJunction", "oil_supply_hypothesis"),
    ("OilFeedLeft", "DistributionJunction", "LeftK16BearingSystem", "oil_feed_hypothesis"),
    ("OilFeedRight", "DistributionJunction", "RightK16BearingSystem", "oil_feed_hypothesis"),
    ("DrainLeft", "LeftK16BearingSystem", "LeftOilCollector", "gravity_or_pressure_return_hypothesis"),
    ("DrainRight", "RightK16BearingSystem", "RightOilCollector", "gravity_or_pressure_return_hypothesis"),
    ("ReturnLeft", "LeftOilCollector", "OilReturnBoundary", "oil_return_hypothesis"),
    ("ReturnRight", "RightOilCollector", "OilReturnBoundary", "oil_return_hypothesis"),
    ("VentLeft", "LeftOilCollector", "VentBoundary", "ventilation_hypothesis"),
    ("VentRight", "RightOilCollector", "VentBoundary", "ventilation_hypothesis"),
    ("ControlSignal", "ControlInput", "ControlBoxPair", "control_signal_hypothesis"),
    ("WastegateCommand", "ControlBoxPair", "WastegateTargetPair", "actuation_hypothesis"),
    ("WastegateLeft", "WastegateTargetPair", "LeftK16BearingSystem", "turbo_control_coupling_hypothesis"),
    ("WastegateRight", "WastegateTargetPair", "RightK16BearingSystem", "turbo_control_coupling_hypothesis"),
]


def render_usd(roster: list[dict[str, Any]]) -> str:
    positions = {name: point for name, _, point in TOPOLOGY_NODES}
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "TurboLubricationControlTopologyF1"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        ")",
        "",
        'def Xform "TurboLubricationControlTopologyF1" (',
        '    kind = "component"',
        ")",
        "{",
        '    custom string status = "F1_nonspatial_topology_readiness_not_part_geometry_or_SimReady"',
        f'    custom string petIllustration = "{ILLUSTRATION}"',
        f"    custom int petOccurrenceCount = {EXPECTED_OCCURRENCES}",
        f"    custom int petPartMasterCount = {EXPECTED_REFERENCES}",
        '    custom string coordinateSemantics = "diagram_units_not_vehicle_coordinates"',
        "    custom bool partGeometryPresent = false",
        "    custom bool physicsAssigned = false",
        "    custom bool materialAssigned = false",
        "    custom bool simReadyValidated = false",
        "",
        '    def Scope "PartRoster"',
        "    {",
    ]
    for item in roster:
        reference = str(item["normalized_oem_reference"])
        lines.extend(
            [
                f'        def Scope "Part_{usd_name(reference)}"',
                "        {",
                f'            custom string normalizedOemReference = "{usd_string(reference)}"',
                f'            custom string petPartMasterTwinId = "{usd_string(str(item["pet_part_master_twin_id"]))}"',
                f'            custom string roleHypothesis = "{usd_string(str(item["role_hypothesis"]))}"',
                '            custom string geometryStatus = "missing"',
                '            custom string materialStatus = "unknown"',
                "        }",
            ]
        )
    lines.extend(['    }', '', '    def Scope "TopologyGuide"', '    {'])
    for name, semantics, point in TOPOLOGY_NODES:
        lines.extend(
            [
                f'        def Sphere "{name}"',
                "        {",
                '            uniform token purpose = "guide"',
                "            double radius = 0.080000",
                f'            custom string topologySemantics = "{semantics}"',
                f"            double3 xformOp:translate = ({point[0]:.6f}, {point[1]:.6f}, {point[2]:.6f})",
                '            uniform token[] xformOpOrder = ["xformOp:translate"]',
                "        }",
            ]
        )
    for name, source, target, semantics in TOPOLOGY_EDGES:
        start = positions[source]
        end = positions[target]
        lines.extend(
            [
                f'        def BasisCurves "{name}"',
                "        {",
                '            uniform token purpose = "guide"',
                '            uniform token type = "linear"',
                '            uniform token wrap = "nonperiodic"',
                "            int[] curveVertexCounts = [2]",
                f"            point3f[] points = [({start[0]:.6f}, {start[1]:.6f}, {start[2]:.6f}), ({end[0]:.6f}, {end[1]:.6f}, {end[2]:.6f})]",
                "            float[] widths = [0.025000]",
                f'            custom string topologySemantics = "{semantics}"',
                "        }",
            ]
        )
    lines.extend(["    }", "}", ""])
    return "\n".join(lines)


def unknown_parameter(
    identifier: str, quantity: str, unit: str | None, required_by: list[str]
) -> dict[str, Any]:
    return {
        "id": identifier,
        "quantity": quantity,
        "value": None,
        "unit": unit,
        "uncertainty": None,
        "status": "unknown_source_or_measurement_required",
        "required_by": required_by,
    }


def parameter_registry() -> list[dict[str, Any]]:
    definitions = [
        ("TLC-GEO-001", "oil_line_lengths", "m", ["hydraulics"]),
        ("TLC-GEO-002", "oil_line_internal_diameters", "m", ["hydraulics"]),
        ("TLC-GEO-003", "oil_line_roughness", "m", ["hydraulics"]),
        ("TLC-GEO-004", "fitting_minor_loss_coefficients", None, ["hydraulics"]),
        ("TLC-GEO-005", "collector_internal_volumes", "m3", ["oil_return", "transient"]),
        ("TLC-GEO-006", "collector_orientation_and_height", "m", ["oil_return", "vehicle_package"]),
        ("TLC-GEO-007", "vent_line_lengths_and_diameters", "m", ["ventilation"]),
        ("TLC-GEO-008", "port_coordinates_and_thread_specs", "mm", ["F2_interfaces"]),
        ("TLC-GEO-009", "line_wall_thicknesses", "mm", ["structural", "manufacturing"]),
        ("TLC-GEO-010", "bracket_and_clamp_coordinates", "mm", ["durability", "vehicle_package"]),
        ("TLC-BC-001", "oil_supply_pressure_map", "Pa", ["hydraulics"]),
        ("TLC-BC-002", "oil_return_pressure_map", "Pa", ["hydraulics"]),
        ("TLC-BC-003", "oil_supply_temperature_history", "K", ["thermal", "viscosity"]),
        ("TLC-BC-004", "oil_mass_flow_targets_per_turbo", "kg_s", ["hydraulics", "acceptance"]),
        ("TLC-BC-005", "turbo_shaft_speed_map", "rad_s", ["bearing_heat"]),
        ("TLC-BC-006", "bearing_heat_rejection_map", "W", ["thermal"]),
        ("TLC-BC-007", "engine_speed_load_boost_transients", None, ["control", "thermal"]),
        ("TLC-BC-008", "shutdown_heat_soak_boundary_history", "K", ["thermal", "transient"]),
        ("TLC-BC-009", "vent_boundary_pressure_and_composition", None, ["ventilation"]),
        ("TLC-BC-010", "control_input_signal_definition", None, ["control"]),
        ("TLC-FLD-001", "oil_grade_and_density_vs_temperature", None, ["hydraulics", "thermal"]),
        ("TLC-FLD-002", "dynamic_viscosity_vs_temperature", "Pa_s", ["hydraulics"]),
        ("TLC-FLD-003", "specific_heat_vs_temperature", "J_kg_K", ["thermal"]),
        ("TLC-FLD-004", "thermal_conductivity_vs_temperature", "W_m_K", ["thermal"]),
        ("TLC-MAT-001", "line_and_fitting_materials", None, ["thermal", "durability", "manufacturing"]),
        ("TLC-MAT-002", "seal_and_o_ring_materials", None, ["temperature", "compatibility"]),
        ("TLC-MAT-003", "collector_materials", None, ["thermal", "durability", "manufacturing"]),
        ("TLC-MAT-004", "control_box_material_and_internal_mechanism", None, ["control", "thermal"]),
        ("TLC-CTL-001", "control_box_transfer_function", None, ["control"]),
        ("TLC-CTL-002", "wastegate_actuator_preload_and_range", None, ["control"]),
        ("TLC-CTL-003", "boost_target_and_limit_map", "Pa", ["control", "acceptance"]),
        ("TLC-ACC-001", "minimum_oil_pressure_margin", "Pa", ["acceptance"]),
        ("TLC-ACC-002", "maximum_bearing_oil_outlet_temperature", "K", ["acceptance"]),
        ("TLC-ACC-003", "maximum_collector_level_or_residence_time", None, ["acceptance"]),
        ("TLC-ACC-004", "allowable_leakage_rate", "kg_s", ["acceptance"]),
        ("TLC-ACC-005", "fatigue_pressure_and_thermal_cycle_life", "cycles", ["acceptance"]),
    ]
    return [unknown_parameter(*definition) for definition in definitions]


def build_report(data: dict[str, Any], usd_text: str) -> dict[str, Any]:
    parameters = parameter_registry()
    roster = data["roster"]
    role_counts: dict[str, int] = {}
    for item in roster:
        role = str(item["role_hypothesis"])
        role_counts[role] = role_counts.get(role, 0) + 1
    equations = [
        {"id": "node_mass_continuity", "equation": "sum(mdot_in)-sum(mdot_out)=d(rho*V)/dt", "missing_parameter_families": ["geometry", "boundary_conditions", "fluid_properties"]},
        {"id": "line_pressure_drop", "equation": "delta_p_f=f*(L/D)*(rho*v^2/2)", "missing_parameter_families": ["line_geometry", "fluid_properties"]},
        {"id": "minor_pressure_losses", "equation": "delta_p_K=sum(K_i)*(rho*v^2/2)", "missing_parameter_families": ["fitting_geometry", "fluid_properties"]},
        {"id": "reynolds_number", "equation": "Re=rho*v*D/mu(T)", "missing_parameter_families": ["line_geometry", "fluid_properties", "temperature"]},
        {"id": "friction_factor", "equation": "1/sqrt(f)=-2*log10(epsilon/(3.7*D)+2.51/(Re*sqrt(f)))", "missing_parameter_families": ["roughness", "diameter", "Reynolds_number"]},
        {"id": "bearing_heat_balance", "equation": "Qdot_bearing=mdot_oil*cp(T)*(T_out-T_in)+Qdot_loss", "missing_parameter_families": ["mass_flow", "oil_properties", "temperature_history", "bearing_loss"]},
        {"id": "line_enthalpy_balance", "equation": "d(rho*V*h)/dt=mdot_in*h_in-mdot_out*h_out+Qdot_wall", "missing_parameter_families": ["geometry", "fluid_properties", "wall_heat_flux"]},
        {"id": "collector_volume_balance", "equation": "dV_oil/dt=mdot_in/rho-mdot_out/rho", "missing_parameter_families": ["collector_volume", "oil_density", "flow_boundaries"]},
        {"id": "vent_mass_balance", "equation": "dm_gas/dt=mdot_generation-mdot_vent; pV=mRT", "missing_parameter_families": ["vent_geometry", "gas_properties", "boundary_pressure"]},
        {"id": "control_wastegate_coupling", "equation": "tau*du/dt+u=K*u_cmd; A_wg=f(u,preload,delta_p)", "missing_parameter_families": ["control_transfer", "actuator", "boost_boundary"]},
    ]
    load_cases = [
        {"id": "LC-993-TLC-COLD-START", "kind": "cold_start_high_viscosity", "status": "blocked"},
        {"id": "LC-993-TLC-HOT-IDLE", "kind": "hot_idle_low_supply_pressure", "status": "blocked"},
        {"id": "LC-993-TLC-RATED-BOOST", "kind": "rated_speed_boost_steady", "status": "blocked"},
        {"id": "LC-993-TLC-BOOST-TRANSIENT", "kind": "boost_transient_control_response", "status": "blocked"},
        {"id": "LC-993-TLC-HEAT-SOAK", "kind": "shutdown_heat_soak", "status": "blocked"},
        {"id": "LC-993-TLC-FAULT", "kind": "restriction_leak_or_vent_blockage", "status": "blocked"},
    ]
    return {
        "$comment": (
            "Contrat F1 de topologie documentaire de la planche PET 202-16. "
            "Le graphe est non spatial et ne constitue ni geometrie de piece ni preuve de fonctionnement."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "status": "F1_202_16_turbo_lubrication_control_topology_complete_reference_solution_blocked",
        "source_boundary": {
            "files": [
                source_entry(PET_INDEX, "PET_occurrence_and_part_master_manifest"),
                source_entry(data["occurrence_path"], "PET_202_16_occurrence_records"),
                *data["master_sources"],
                source_entry(PORSCHEFANATICS_SOURCE, "PorscheFanatics_identity_and_system_context_only"),
                source_entry(K16_REPORT, "adjacent_K16_envelope_contract_without_interface_transfer"),
                source_entry(PROGRAM_DEFINITION, "PhysicsNeMo_and_Omniverse_policy"),
                source_entry(SIMREADY_PREFLIGHT, "blocked_Omniverse_preflight"),
            ],
            "pet_illustration": ILLUSTRATION,
            "porschefanatics_used_for_identity_and_system_context_only": True,
            "llm_generated_dimensions_used": False,
            "manual_comparator_values_transferred_to_turbo": False,
            "independent_metrology_used": False,
            "third_party_geometry_redistributed": False,
        },
        "summary": {
            "pet_202_16_occurrences": EXPECTED_OCCURRENCES,
            "pet_202_16_unique_part_masters": EXPECTED_REFERENCES,
            "source_occurrence_counts": data["source_counts"],
            "role_hypothesis_counts": dict(sorted(role_counts.items())),
            "topology_nodes": len(TOPOLOGY_NODES),
            "topology_edges": len(TOPOLOGY_EDGES),
            "symbolic_equation_contracts": len(equations),
            "blocked_reference_load_cases": len(load_cases),
            "unknown_engineering_parameters": len(parameters),
            "known_interface_coordinates": 0,
            "qualified_material_decisions": 0,
            "reference_solver_results": 0,
            "physicsnemo_results": 0,
            "simready_assets": 0,
            "manufacturing_releases": 0,
        },
        "part_roster": roster,
        "topology_hypothesis": {
            "status": "LLM_assisted_nonspatial_hypothesis_requires_engineering_review",
            "nodes": [
                {"id": name, "semantics": semantics, "vehicle_coordinate": None}
                for name, semantics, _ in TOPOLOGY_NODES
            ],
            "edges": [
                {"id": name, "from": source, "to": target, "semantics": semantics, "connected_pet_references": None}
                for name, source, target, semantics in TOPOLOGY_EDGES
            ],
            "left_right_assignment_is_proven": False,
            "ports_and_connections_are_proven": False,
            "diagram_coordinates_are_vehicle_coordinates": False,
        },
        "parameter_registry": parameters,
        "mathematical_model": {
            "status": "symbolic_contracts_only_no_operating_point_evaluated",
            "equations": equations,
            "reference_solver_credit": False,
            "network_solution_credit": False,
            "required_first_reference_methods": [
                "configuration_resolved_lumped_hydraulic_network_with_balance_checks",
                "mesh_converged_CFD_CHT_after_F3_fluid_and_solid_domains",
                "control_system_identification_and_transient_co_simulation_after_boundary_measurement",
            ],
        },
        "load_cases": load_cases,
        "material_and_manufacturing_route": {
            "status": "role_based_screening_hypotheses_only_no_selection",
            "candidate_matrix": [
                {"role": "oil_transport_line_or_collector", "candidate_family": "temperature_and_oil_compatible_metal_system", "candidate_process": "tube_or_sheet_forming_joining_and_machining", "status": "unsourced_unselected"},
                {"role": "sealing_element", "candidate_family": "temperature_and_oil_compatible_elastomer_or_metal_seal", "candidate_process": "qualified_commercial_or_tooled_seal_process", "status": "unsourced_unselected"},
                {"role": "support_or_retention", "candidate_family": "corrosion_and_heat_resistant_metal", "candidate_process": "sheet_forming_or_machining", "status": "unsourced_unselected"},
                {"role": "fit_and_routing_mockup_only", "candidate_family": "polymer_additive_manufacturing", "candidate_process": "FDM_SLS_or_MJF", "status": "unsourced_unselected_nonfunctional_only"},
            ],
            "selected_material_count": 0,
            "selected_functional_manufacturing_route_count": 0,
            "functional_additive_manufacturing_disposition": "prohibited_without_F2_F3_material_temperature_pressure_fatigue_and_professional_review",
            "prototype_disposition": "nonfunctional_fit_and_routing_mockups_only_after_scale_and_interface_evidence",
        },
        "physicsnemo_discovery": {
            "canonical_repository": data["physicsnemo"].get("canonical_repository"),
            "commit": data["physicsnemo"].get("discovered_commit"),
            "paths_verified_live_during_authoring": True,
            "model_menu": [
                {"model": "MeshGraphNet", "role": "candidate_graph_network_or_mesh_field_surrogate_after_reference_dataset", "selected": False},
                {"model": "GeoTransolver", "role": "candidate_geometry_aware_unstructured_field_surrogate_after_F3_geometry", "selected": False},
                {"model": "Transolver", "role": "candidate_unstructured_PDE_field_surrogate_after_reference_dataset", "selected": False},
                {"model": "DoMINO", "role": "candidate_3D_CFD_CHT_surface_volume_surrogate_after_reference_dataset", "selected": False},
            ],
            "datapipe_menu": [
                {"datapipe": "DoMINODataPipe", "role": "future_surface_volume_CAE_preprocessing"},
                {"datapipe": "TransolverDataPipe", "role": "future_unstructured_mesh_field_preprocessing"},
            ],
            "reference_examples": [
                {"example": "cfd/stokes_mgn", "role": "mesh_graph_field_learning_reference_not_a_turbo_validation"},
                {"example": "cfd/transient_conjugate_heat_transfer_tank_fill", "role": "transient_CHT_reference_not_a_turbo_validation"},
            ],
            "execution_enabled": False,
            "eligibility_gate": "F3_domains_converged_reference_solver_dataset_held_out_cases_and_out_of_domain_rejection",
        },
        "omniverse_handoff": {
            "openusd_source_authoring": "completed_as_nonspatial_topology_guide",
            "property_assignment_intent": "run",
            "preflight_report": relative(SIMREADY_PREFLIGHT),
            "preflight_status": data["preflight"].get("status"),
            "preflight_blockers": data["preflight"].get("blockers", []),
            "material_and_physics_assignment": "not_run_preflight_blocked",
            "nvidia_asset_validator": "not_run_preflight_blocked",
            "simready_foundation": "not_run_preflight_blocked",
            "simready_validated": False,
        },
        "assets": {
            "editable_topology_source": relative(Path(__file__).resolve()),
            "openusd_guide": relative(USD_OUTPUT),
            "openusd_guide_sha256": sha256_text(usd_text),
            "openusd_part_roster_scope_count": EXPECTED_REFERENCES,
            "openusd_topology_node_guide_count": len(TOPOLOGY_NODES),
            "openusd_topology_edge_guide_count": len(TOPOLOGY_EDGES),
            "openusd_guide_primitive_count": len(TOPOLOGY_NODES) + len(TOPOLOGY_EDGES),
            "openusd_physics_schema_count": 0,
            "openusd_material_binding_count": 0,
        },
        "claim_boundary": {
            "is_complete_OEM_geometry": False,
            "is_F2_interface_geometry": False,
            "is_F3_analysis_geometry": False,
            "is_spatial_vehicle_topology": False,
            "is_vehicle_positioned_or_fitment_validated": False,
            "is_qualified_material_selection": False,
            "is_evaluated_operating_point": False,
            "is_reference_solver_or_control_result": False,
            "is_physicsnemo_result": False,
            "is_simready_validated": False,
            "is_manufacturing_or_vehicle_release": False,
        },
        "next_gate": "resolve_202_16_configuration_topology_side_assignment_and_F2_interfaces",
    }


def validate(data: dict[str, Any], usd_text: str, report: dict[str, Any]) -> None:
    if report.get("status") != (
        "F1_202_16_turbo_lubrication_control_topology_complete_reference_solution_blocked"
    ):
        raise ContractError("status")
    summary = report.get("summary", {})
    expected = {
        "pet_202_16_occurrences": 71,
        "pet_202_16_unique_part_masters": 40,
        "topology_nodes": 11,
        "topology_edges": 13,
        "symbolic_equation_contracts": 10,
        "blocked_reference_load_cases": 6,
        "unknown_engineering_parameters": 36,
        "known_interface_coordinates": 0,
        "qualified_material_decisions": 0,
        "reference_solver_results": 0,
        "physicsnemo_results": 0,
        "simready_assets": 0,
        "manufacturing_releases": 0,
    }
    for field, expected_value in expected.items():
        if summary.get(field) != expected_value:
            raise ContractError(f"summary:{field}:{summary.get(field)}")
    if summary.get("source_occurrence_counts") != EXPECTED_SOURCE_COUNTS:
        raise ContractError("source_occurrence_counts")
    roster = report.get("part_roster", [])
    if len(roster) != 40 or len(
        {item.get("pet_part_master_twin_id") for item in roster}
    ) != 40:
        raise ContractError("part_roster")
    if any(
        item.get("interface_geometry") is not None
        or item.get("material") is not None
        or item.get("vehicle_transform") is not None
        for item in roster
    ):
        raise ContractError("part_roster_overclaim")
    parameters = report.get("parameter_registry", [])
    if len(parameters) != 36 or any(
        item.get("value") is not None or item.get("uncertainty") is not None
        for item in parameters
    ):
        raise ContractError("parameter_registry")
    if len(report.get("mathematical_model", {}).get("equations", [])) != 10:
        raise ContractError("equations")
    if report.get("mathematical_model", {}).get("reference_solver_credit") is not False:
        raise ContractError("reference_solver_overclaim")
    if len(report.get("load_cases", [])) != 6 or any(
        item.get("status") != "blocked" for item in report.get("load_cases", [])
    ):
        raise ContractError("load_cases")
    if report.get("physicsnemo_discovery", {}).get("execution_enabled") is not False:
        raise ContractError("physicsnemo_execution")
    if report.get("omniverse_handoff", {}).get("simready_validated") is not False:
        raise ContractError("simready_overclaim")
    if any(value is not False for value in report.get("claim_boundary", {}).values()):
        raise ContractError("claim_boundary")
    if usd_text.count('purpose = "guide"') != 24:
        raise ContractError("usd_guide_count")
    if usd_text.count('def Scope "Part_') != 40:
        raise ContractError("usd_part_roster_count")
    for prohibited in (
        "UsdPhysics", "RigidBodyAPI", "CollisionAPI", "MassAPI", "MaterialBindingAPI"
    ):
        if prohibited in usd_text:
            raise ContractError(f"usd_overclaim:{prohibited}")
    if report.get("assets", {}).get("openusd_guide_sha256") != sha256_text(usd_text):
        raise ContractError("usd_digest")
    if [item.get("pet_part_master_twin_id") for item in roster] != [
        item.get("pet_part_master_twin_id") for item in data["roster"]
    ]:
        raise ContractError("roster_evidence")


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
        usd_text = render_usd(data["roster"])
        report = build_report(data, usd_text)
        validate(data, usd_text, report)
        outputs = {USD_OUTPUT: usd_text, REPORT: render_json(report)}
        if args.write:
            for path, content in outputs.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            print(
                f"wrote {relative(REPORT)}: 40 PET masters, 10 equations, "
                "6 blocked cases, 0 solver results"
            )
            return 0
        for path, content in outputs.items():
            if not path.is_file():
                print(f"missing:{relative(path)}")
                return 1
            if args.check and path.read_text(encoding="utf-8") != content:
                print(f"stale:{relative(path)}")
                return 1
        validate(data, USD_OUTPUT.read_text(encoding="utf-8"), load_json(REPORT))
        print(f"current {relative(REPORT)}: 40 PET masters, topology remains F1")
        return 0
    except (ContractError, OSError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
