#!/usr/bin/env python3
"""Generate a PET 104-01 oil-tank circuit F1 topology contract.

The PET records identify parts, not their interfaces or dimensions. The USD
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
    ROOT / "catalog" / "sources" / "src-porschefanatics-993-oil-tank-pet.json"
)
TURBO_LUBRICATION_CONTROL_REPORT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "turbo-lubrication-control-topology-readiness-f1.json"
)
PROGRAM_DEFINITION = ROOT / "twins" / "vehicle-993" / "program-definition.json"
SIMREADY_PREFLIGHT = (
    ROOT / "twins" / "vehicle-993" / "functional-flow-simready-preflight-f0.json"
)
REPORT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "oil-tank-circuit-topology-readiness-f1.json"
)
USD_OUTPUT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering"
    / "993-oil-tank-circuit-topology-f1.usda"
)

ILLUSTRATION = "104-01"
EXPECTED_OCCURRENCES = 153
EXPECTED_REFERENCES = 81
EXPECTED_SOURCE_COUNTS = {"pet-993-pdf-rsworkshop": 72, "pet-classic-993": 81}
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
    if "oil tank" in text:
        return "oil_storage_tank"
    if "tank gauge" in text:
        return "oil_level_gauge"
    if "dipstick" in text:
        return "oil_level_dipstick"
    if "filler neck" in text:
        return "oil_filler_neck"
    if "fuel tank cap" in text:
        return "service_cap_identity_ambiguous"
    if "filling hose" in text:
        return "oil_filling_hose"
    if "breather hose" in text:
        return "breather_hose"
    if "return line" in text:
        return "oil_return_line"
    if "oil hose" in text:
        return "oil_hose"
    if "oil tube" in text or "oil pipe" in text:
        return "oil_transport_tube_or_pipe"
    if "guide tube" in text:
        return "guide_or_service_tube"
    if "connecting piece" in text or "connection piece" in text or "socket" in text:
        return "connection_fitting"
    if "valve" in text:
        return "valve_identity_unresolved"
    if any(token in text for token in ("gasket", "o-ring", "seal", "sealing")):
        return "sealing_element"
    if any(token in text for token in ("rubber sleeve", "grommet", "bellows")):
        return "compliant_sleeve_grommet_or_bellows"
    if any(token in text for token in ("clamp", "holder", "tie-wrap")):
        return "support_or_retention"
    if "stopper" in text:
        return "closure_or_service_plug"
    if "spacer" in text or "sleeve" in text:
        return "spacer_or_sleeve"
    if any(token in text for token in ("screw", "bolt", "nut", "washer", "stud")):
        return "fastener_or_closure"
    raise ContractError(f"unclassified_description:{descriptions}")


def derive() -> dict[str, Any]:
    index = load_json(PET_INDEX)
    one_xx = [
        item
        for item in index.get("output", {}).get("shards", [])
        if isinstance(item, dict) and item.get("system_id") == "1xx"
    ]
    if len(one_xx) != 1:
        raise ContractError("pet_1xx_shard")
    occurrence_path = ROOT / str(one_xx[0].get("path"))
    if sha256_file(occurrence_path) != one_xx[0].get("sha256"):
        raise ContractError("pet_1xx_shard_digest")
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
        master_occurrence_ids = {
            item.get("occurrence_twin_id")
            for item in master.get("documentary_graph", {}).get("occurrences", [])
            if isinstance(item, dict) and item.get("pet_illustration") == ILLUSTRATION
        }
        selected_ids = {item.get("twin_id") for item in selected_occurrences}
        if master_occurrence_ids != selected_ids:
            raise ContractError(f"part_master_occurrence_mismatch:{reference}")
        positions = sorted(
            {
                int(item.get("catalogue_context", {}).get("position"))
                for item in selected_occurrences
                if item.get("catalogue_context", {}).get("position") is not None
            }
        )
        descriptions = sorted(
            {str(item.get("subject", {}).get("description")) for item in selected_occurrences},
            key=lambda value: (value.lower(), value),
        )
        roster.append(
            {
                "normalized_oem_reference": reference,
                "display_references": master.get("subject", {}).get("display_references", []),
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
                "interface_geometry": None,
                "material": None,
                "vehicle_transform": None,
            }
        )

    porschefanatics = load_json(PORSCHEFANATICS_SOURCE)
    if (
        porschefanatics.get("source_id") != "SRC-PORSCHEFANATICS-993-OIL-TANK-PET"
        or not str(porschefanatics.get("url", "")).endswith("/104-01/")
        or porschefanatics.get("quality", {}).get("dimensional_accuracy") != "unknown"
    ):
        raise ContractError("porschefanatics_source_boundary")
    turbo_lubrication = load_json(TURBO_LUBRICATION_CONTROL_REPORT)
    if turbo_lubrication.get("status") != (
        "F1_202_16_turbo_lubrication_control_topology_complete_reference_solution_blocked"
    ):
        raise ContractError("turbo_lubrication_control_contract")
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
        "occurrence_path": occurrence_path,
        "master_sources": master_sources,
        "roster": roster,
        "source_counts": source_counts,
        "physicsnemo": physicsnemo,
        "preflight": preflight,
    }


TOPOLOGY_NODES = [
    ("OilTankStorage", "oil_storage_boundary", (0.0, 0.0, 0.0)),
    ("EnginePressureSupplyBoundary", "engine_pressure_supply_boundary", (4.0, -1.0, 0.0)),
    ("EngineScavengeReturnBoundary", "engine_scavenge_return_boundary", (4.0, 1.0, 0.0)),
    ("TurboLubricationReturnBoundary", "adjacent_202_16_return_boundary", (6.5, 2.5, 0.0)),
    ("OilFillerBoundary", "oil_filler_boundary", (-3.0, 2.0, 0.0)),
    ("OilLevelMeasurement", "oil_level_measurement_boundary", (-3.0, 0.0, 0.0)),
    ("VehicleElectricalBoundary", "vehicle_electrical_boundary", (-5.5, 0.0, 0.0)),
    ("CrankcaseVentBoundary", "crankcase_vent_boundary", (1.5, 3.0, 0.0)),
    ("VentSystemBoundary", "vent_system_boundary", (-1.0, 3.5, 0.0)),
    ("ServiceDrainBoundary", "service_drain_boundary", (0.0, -3.0, 0.0)),
    ("AmbientThermalBoundary", "ambient_thermal_boundary", (-3.0, -2.0, 0.0)),
]

TOPOLOGY_EDGES = [
    ("TankToEngineSupply", "OilTankStorage", "EnginePressureSupplyBoundary", "oil_supply_hypothesis"),
    ("EngineReturnToTank", "EngineScavengeReturnBoundary", "OilTankStorage", "oil_return_hypothesis"),
    ("TurboReturnCoupling", "TurboLubricationReturnBoundary", "EngineScavengeReturnBoundary", "cross_system_return_hypothesis"),
    ("FillerToTank", "OilFillerBoundary", "OilTankStorage", "service_fill_hypothesis"),
    ("TankToLevel", "OilTankStorage", "OilLevelMeasurement", "level_measurement_hypothesis"),
    ("LevelSignal", "OilLevelMeasurement", "VehicleElectricalBoundary", "sensor_signal_hypothesis"),
    ("CrankcaseBreather", "CrankcaseVentBoundary", "OilTankStorage", "breather_flow_hypothesis"),
    ("TankVent", "OilTankStorage", "VentSystemBoundary", "vent_flow_hypothesis"),
    ("TankDrain", "OilTankStorage", "ServiceDrainBoundary", "service_drain_hypothesis"),
    ("TankHeatTransfer", "OilTankStorage", "AmbientThermalBoundary", "lumped_heat_transfer_hypothesis"),
]


def render_usd(roster: list[dict[str, Any]]) -> str:
    positions = {name: point for name, _, point in TOPOLOGY_NODES}
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "OilTankCircuitTopologyF1"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        ")",
        "",
        'def Xform "OilTankCircuitTopologyF1" (',
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
        ("OTC-GEO-001", "oil_tank_internal_volume", "m3", ["mass_balance"]),
        ("OTC-GEO-002", "oil_tank_internal_geometry", None, ["free_surface", "CFD"]),
        ("OTC-GEO-003", "line_lengths", "m", ["hydraulics"]),
        ("OTC-GEO-004", "line_internal_diameters", "m", ["hydraulics"]),
        ("OTC-GEO-005", "line_roughness", "m", ["hydraulics"]),
        ("OTC-GEO-006", "fitting_minor_loss_coefficients", None, ["hydraulics"]),
        ("OTC-GEO-007", "port_coordinates_and_thread_specs", "mm", ["F2_interfaces"]),
        ("OTC-GEO-008", "tank_wall_thickness_map", "mm", ["structural", "manufacturing"]),
        ("OTC-GEO-009", "mount_coordinates_and_stiffness", None, ["durability", "vehicle_package"]),
        ("OTC-GEO-010", "dipstick_and_gauge_reference_heights", "mm", ["level_measurement"]),
        ("OTC-BC-001", "engine_supply_flow_map", "kg_s", ["hydraulics"]),
        ("OTC-BC-002", "engine_scavenge_return_flow_map", "kg_s", ["hydraulics"]),
        ("OTC-BC-003", "supply_boundary_pressure_map", "Pa", ["hydraulics"]),
        ("OTC-BC-004", "return_boundary_pressure_map", "Pa", ["hydraulics"]),
        ("OTC-BC-005", "oil_temperature_history", "K", ["thermal", "viscosity"]),
        ("OTC-BC-006", "engine_speed_load_history", None, ["transient"]),
        ("OTC-BC-007", "vehicle_acceleration_history", "m_s2", ["free_surface", "loads"]),
        ("OTC-BC-008", "ambient_temperature_and_airflow", None, ["thermal"]),
        ("OTC-BC-009", "vent_boundary_pressure_and_flow", None, ["ventilation"]),
        ("OTC-FLD-001", "oil_density_vs_temperature", "kg_m3", ["hydraulics", "level"]),
        ("OTC-FLD-002", "oil_dynamic_viscosity_vs_temperature", "Pa_s", ["hydraulics"]),
        ("OTC-FLD-003", "oil_specific_heat_vs_temperature", "J_kg_K", ["thermal"]),
        ("OTC-FLD-004", "oil_thermal_conductivity_vs_temperature", "W_m_K", ["thermal"]),
        ("OTC-FLD-005", "oil_air_phase_and_deaeration_properties", None, ["multiphase"]),
        ("OTC-MAT-001", "tank_material_and_temper", None, ["structural", "manufacturing"]),
        ("OTC-MAT-002", "line_and_fitting_materials", None, ["thermal", "fatigue"]),
        ("OTC-MAT-003", "hose_and_bellows_materials", None, ["compatibility", "durability"]),
        ("OTC-MAT-004", "seal_and_grommet_materials", None, ["compatibility", "temperature"]),
        ("OTC-MAT-005", "bracket_and_fastener_materials", None, ["durability", "galvanic"]),
        ("OTC-SNS-001", "tank_gauge_transfer_function", None, ["instrumentation"]),
        ("OTC-SNS-002", "dipstick_wet_dry_calibration", "mm", ["service"]),
        ("OTC-SNS-003", "gauge_electrical_interface", None, ["electrical"]),
        ("OTC-SNS-004", "oil_level_acceptance_window", "m", ["acceptance"]),
        ("OTC-ACC-001", "minimum_supply_pressure_margin", "Pa", ["acceptance"]),
        ("OTC-ACC-002", "maximum_pressure_drop", "Pa", ["acceptance"]),
        ("OTC-ACC-003", "minimum_usable_oil_volume", "m3", ["acceptance"]),
        ("OTC-ACC-004", "maximum_oil_temperature", "K", ["acceptance"]),
        ("OTC-ACC-005", "allowable_leakage_rate", "kg_s", ["acceptance"]),
        ("OTC-ACC-006", "allowable_aeration_fraction", None, ["acceptance"]),
        ("OTC-ACC-007", "pressure_thermal_vibration_cycle_life", "cycles", ["acceptance"]),
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
        {"id": "tank_oil_mass_balance", "equation": "d(rho_oil*V_oil)/dt=sum(mdot_in)-sum(mdot_out)", "missing_parameter_families": ["tank_geometry", "boundary_flows", "oil_properties"]},
        {"id": "tank_gas_mass_balance", "equation": "dm_gas/dt=mdot_breather_in-mdot_vent_out", "missing_parameter_families": ["vent_topology", "gas_properties", "boundary_flows"]},
        {"id": "line_pressure_drop", "equation": "delta_p=f*(L/D)*(rho*v^2/2)+sum(K_i)*(rho*v^2/2)", "missing_parameter_families": ["line_geometry", "fittings", "oil_properties"]},
        {"id": "reynolds_number", "equation": "Re=rho*v*D/mu(T)", "missing_parameter_families": ["line_geometry", "oil_properties", "temperature"]},
        {"id": "friction_factor", "equation": "1/sqrt(f)=-2*log10(epsilon/(3.7*D)+2.51/(Re*sqrt(f)))", "missing_parameter_families": ["roughness", "diameter", "Reynolds_number"]},
        {"id": "vehicle_acceleration_head", "equation": "delta_p_inertial=rho*(g_vector-a_vehicle).delta_r", "missing_parameter_families": ["vehicle_orientation", "acceleration_history", "geometry"]},
        {"id": "tank_energy_balance", "equation": "d(m*cp*T)/dt=sum(mdot*h)_in-sum(mdot*h)_out+Qdot_engine-Qdot_ambient", "missing_parameter_families": ["oil_properties", "boundary_enthalpy", "heat_transfer"]},
        {"id": "thermal_expansion_level", "equation": "V_oil(T)=m_oil/rho(T); h_level=f(V_oil,tank_geometry,a_vehicle)", "missing_parameter_families": ["tank_geometry", "oil_density", "vehicle_acceleration"]},
        {"id": "deaeration_residence", "equation": "d(alpha_air*V)/dt=Q_air_in-Q_air_out(alpha_air,tau_deaeration)", "missing_parameter_families": ["multiphase_properties", "tank_geometry", "boundary_flows"]},
        {"id": "gauge_transfer", "equation": "signal=g(h_level,T,supply_voltage)", "missing_parameter_families": ["gauge_calibration", "temperature", "electrical_interface"]},
        {"id": "tank_wall_screening", "equation": "sigma_screen~p_internal*r_characteristic/t_wall", "missing_parameter_families": ["tank_geometry", "wall_thickness", "pressure", "material_allowables"]},
    ]
    load_cases = [
        {"id": "LC-993-OTC-COLD-START", "kind": "cold_start_high_viscosity", "status": "blocked"},
        {"id": "LC-993-OTC-HOT-IDLE", "kind": "hot_idle_low_pressure", "status": "blocked"},
        {"id": "LC-993-OTC-RATED", "kind": "rated_engine_speed_thermal_steady", "status": "blocked"},
        {"id": "LC-993-OTC-BRAKING", "kind": "maximum_braking_oil_pickup_and_level", "status": "blocked"},
        {"id": "LC-993-OTC-CORNERING", "kind": "sustained_lateral_acceleration_oil_pickup_and_level", "status": "blocked"},
        {"id": "LC-993-OTC-HEAT-SOAK", "kind": "shutdown_heat_soak", "status": "blocked"},
        {"id": "LC-993-OTC-FAULT", "kind": "restriction_leak_vent_blockage_or_overfill", "status": "blocked"},
    ]
    return {
        "$comment": (
            "Contrat F1 de topologie documentaire de la planche PET 104-01. "
            "Le graphe est non spatial et ne constitue ni geometrie de piece ni preuve de fonctionnement."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "status": "F1_104_01_oil_tank_circuit_topology_complete_reference_solution_blocked",
        "source_boundary": {
            "files": [
                source_entry(PET_INDEX, "PET_occurrence_and_part_master_manifest"),
                source_entry(data["occurrence_path"], "PET_104_01_occurrence_records"),
                *data["master_sources"],
                source_entry(PORSCHEFANATICS_SOURCE, "PorscheFanatics_identity_and_system_context_only"),
                source_entry(TURBO_LUBRICATION_CONTROL_REPORT, "adjacent_202_16_topology_without_interface_transfer"),
                source_entry(PROGRAM_DEFINITION, "PhysicsNeMo_and_Omniverse_policy"),
                source_entry(SIMREADY_PREFLIGHT, "blocked_Omniverse_preflight"),
            ],
            "pet_illustration": ILLUSTRATION,
            "porschefanatics_used_for_identity_and_system_context_only": True,
            "porschefanatics_catalogue_page": "https://porschefanatics.com/oem/993/104-01/",
            "llm_generated_dimensions_used": False,
            "adjacent_topology_connections_transferred_as_fact": False,
            "independent_metrology_used": False,
            "third_party_geometry_redistributed": False,
        },
        "summary": {
            "pet_104_01_occurrences": EXPECTED_OCCURRENCES,
            "pet_104_01_unique_part_masters": EXPECTED_REFERENCES,
            "pet_part_masters_seen_in_both_sources": sum(
                len(item["pet_source_ids"]) == 2 for item in roster
            ),
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
            "ports_and_connections_are_proven": False,
            "cross_system_turbo_return_is_proven": False,
            "diagram_coordinates_are_vehicle_coordinates": False,
        },
        "parameter_registry": parameters,
        "mathematical_model": {
            "status": "symbolic_contracts_only_no_operating_point_evaluated",
            "equations": equations,
            "reference_solver_credit": False,
            "network_solution_credit": False,
            "required_first_reference_methods": [
                "configuration_resolved_lumped_oil_network_with_balance_checks",
                "transient_multiphase_CFD_after_F3_tank_and_line_domains",
                "conjugate_heat_transfer_after_material_and_thermal_boundary_evidence",
                "tank_mount_structural_and_vibration_analysis_after_F3_geometry",
            ],
        },
        "load_cases": load_cases,
        "material_and_manufacturing_route": {
            "status": "role_based_screening_hypotheses_only_no_selection",
            "candidate_matrix": [
                {"role": "oil_storage_tank", "candidate_family": "oil_and_temperature_compatible_formable_metal", "candidate_process": "sheet_forming_joining_machining_and_leak_test", "status": "unsourced_unselected"},
                {"role": "oil_line_or_fitting", "candidate_family": "oil_and_temperature_compatible_tube_or_hose_system", "candidate_process": "tube_forming_hose_assembly_and_machining", "status": "unsourced_unselected"},
                {"role": "seal_grommet_or_bellows", "candidate_family": "oil_temperature_and_ozone_compatible_elastomer_or_metal_seal", "candidate_process": "qualified_commercial_or_tooled_process", "status": "unsourced_unselected"},
                {"role": "support_or_retention", "candidate_family": "corrosion_heat_and_fatigue_resistant_metal", "candidate_process": "sheet_forming_or_machining", "status": "unsourced_unselected"},
                {"role": "fit_and_routing_mockup_only", "candidate_family": "polymer_additive_manufacturing", "candidate_process": "FDM_SLS_or_MJF", "status": "unsourced_unselected_nonfunctional_only"},
            ],
            "selected_material_count": 0,
            "selected_functional_manufacturing_route_count": 0,
            "functional_additive_manufacturing_disposition": "prohibited_without_F2_F3_fluid_thermal_vibration_material_leak_and_professional_review",
            "prototype_disposition": "nonfunctional_fit_and_routing_mockups_only_after_scale_and_interface_evidence",
        },
        "physicsnemo_discovery": {
            "canonical_repository": data["physicsnemo"].get("canonical_repository"),
            "commit": data["physicsnemo"].get("discovered_commit"),
            "paths_verified_live_during_authoring": True,
            "model_menu": [
                {"model": "MeshGraphNet", "role": "candidate_graph_or_mesh_field_surrogate_after_reference_dataset", "selected": False},
                {"model": "DoMINO", "role": "candidate_transient_CFD_CHT_surface_volume_surrogate_after_F3_dataset", "selected": False},
                {"model": "GeoTransolver", "role": "candidate_geometry_aware_unstructured_field_surrogate_after_F3_dataset", "selected": False},
                {"model": "Transolver", "role": "candidate_unstructured_PDE_field_surrogate_after_reference_dataset", "selected": False},
            ],
            "datapipe_menu": [
                {"datapipe": "StokesDataset", "role": "future_mesh_graph_velocity_pressure_field preprocessing reference"},
                {"datapipe": "DoMINODataPipe", "role": "future_surface_volume_CAE_preprocessing"},
                {"datapipe": "TransolverDataPipe", "role": "future_unstructured_mesh_field_preprocessing"},
            ],
            "reference_examples": [
                {"example": "cfd/stokes_mgn", "role": "mesh_graph_field learning reference not oil-system validation"},
                {"example": "cfd/transient_conjugate_heat_transfer_tank_fill", "role": "transient tank CHT reference not oil-system validation"},
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
            "is_reference_solver_result": False,
            "is_physicsnemo_result": False,
            "is_simready_validated": False,
            "is_manufacturing_or_vehicle_release": False,
        },
        "next_gate": "resolve_104_01_configuration_topology_F2_interfaces_and_oil_properties",
    }


def validate(data: dict[str, Any], usd_text: str, report: dict[str, Any]) -> None:
    if report.get("status") != (
        "F1_104_01_oil_tank_circuit_topology_complete_reference_solution_blocked"
    ):
        raise ContractError("status")
    summary = report.get("summary", {})
    expected = {
        "pet_104_01_occurrences": 153,
        "pet_104_01_unique_part_masters": 81,
        "pet_part_masters_seen_in_both_sources": 72,
        "topology_nodes": 11,
        "topology_edges": 10,
        "symbolic_equation_contracts": 11,
        "blocked_reference_load_cases": 7,
        "unknown_engineering_parameters": 40,
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
    if len(roster) != 81 or len({item.get("pet_part_master_twin_id") for item in roster}) != 81:
        raise ContractError("part_roster")
    if any(
        item.get("interface_geometry") is not None
        or item.get("material") is not None
        or item.get("vehicle_transform") is not None
        for item in roster
    ):
        raise ContractError("part_roster_overclaim")
    parameters = report.get("parameter_registry", [])
    if len(parameters) != 40 or any(
        item.get("value") is not None or item.get("uncertainty") is not None
        for item in parameters
    ):
        raise ContractError("parameter_registry")
    if len(report.get("mathematical_model", {}).get("equations", [])) != 11:
        raise ContractError("equations")
    if report.get("mathematical_model", {}).get("reference_solver_credit") is not False:
        raise ContractError("reference_solver_overclaim")
    if len(report.get("load_cases", [])) != 7 or any(
        item.get("status") != "blocked" for item in report.get("load_cases", [])
    ):
        raise ContractError("load_cases")
    if report.get("physicsnemo_discovery", {}).get("execution_enabled") is not False:
        raise ContractError("physicsnemo_execution")
    if report.get("omniverse_handoff", {}).get("simready_validated") is not False:
        raise ContractError("simready_overclaim")
    if any(value is not False for value in report.get("claim_boundary", {}).values()):
        raise ContractError("claim_boundary")
    if usd_text.count('purpose = "guide"') != 21:
        raise ContractError("usd_guide_count")
    if usd_text.count('def Scope "Part_') != 81:
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
                f"wrote {relative(REPORT)}: 81 PET masters, 11 equations, "
                "7 blocked cases, 0 solver results"
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
        print(f"current {relative(REPORT)}: 81 PET masters, topology remains F1")
        return 0
    except (ContractError, OSError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
