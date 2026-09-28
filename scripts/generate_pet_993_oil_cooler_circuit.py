#!/usr/bin/env python3
"""Generate the fail-closed PET 104-05 oil-cooler circuit F1 contract.

The PET records prove identities and catalogue grouping only.  The generated
OpenUSD stage is a non-spatial topology guide, never cooler, duct or pipe
geometry and never a solver or SimReady result.
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
    ROOT / "catalog" / "sources" / "src-porschefanatics-993-oil-cooler-pet.json"
)
OIL_TANK_REPORT = (
    ROOT / "twins" / "catalogue-parts" / "oil-tank-circuit-topology-readiness-f1.json"
)
PROGRAM_DEFINITION = ROOT / "twins" / "vehicle-993" / "program-definition.json"
SIMREADY_PREFLIGHT = (
    ROOT / "twins" / "vehicle-993" / "functional-flow-simready-preflight-f0.json"
)
REPORT = (
    ROOT / "twins" / "catalogue-parts" / "oil-cooler-circuit-topology-readiness-f1.json"
)
USD_OUTPUT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering"
    / "993-oil-cooler-circuit-topology-f1.usda"
)

ILLUSTRATION = "104-05"
EXPECTED_OCCURRENCES = 80
EXPECTED_REFERENCES = 43
EXPECTED_BOTH_SOURCES = 37
EXPECTED_SOURCE_COUNTS = {"pet-993-pdf-rsworkshop": 37, "pet-classic-993": 43}
EXPECTED_PHYSICSNEMO_COMMIT = "4fbfcfd62bf050b48ceec6b438da409b9f4644b3"


class ContractError(ValueError):
    """Raised when source evidence is stale or a claim would be promoted."""


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
    return cleaned if cleaned and not cleaned[0].isdigit() else f"_{cleaned}"


def usd_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def part_role(descriptions: list[str]) -> str:
    text = " ".join(descriptions).lower()
    if "oil cooler" in text:
        return "oil_to_air_heat_exchanger_core"
    if "oil pipe" in text:
        return "oil_transport_pipe"
    if any(token in text for token in ("air guide", "air-guide", "air duct", "baffle")):
        return "cooling_air_guide_or_baffle"
    if "blower" in text:
        return "cooling_air_blower"
    if "temperature sensor" in text:
        return "temperature_sensor"
    if "series resistor" in text:
        return "blower_series_resistor"
    if "union" in text:
        return "fluid_union_identity_unresolved"
    if any(token in text for token in ("o-ring", "sealing ring", "seal", "gasket")):
        return "sealing_element"
    if any(token in text for token in ("rubber mounting", "rubber buffer", "buffer", "edge protection")):
        return "compliant_mount_buffer_or_edge_protection"
    if any(token in text for token in ("clamp", "cable holder", "bracket")):
        return "support_or_retention"
    if any(
        token in text
        for token in (
            "screw",
            "bolt",
            "nut",
            "washer",
            "retaining clip",
            "speed nut",
        )
    ):
        return "fastener_or_retainer"
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
        reference = normalize_reference(
            str(item.get("subject", {}).get("oem_reference", ""))
        )
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
                "pet_positions": sorted(
                    {
                        int(item.get("catalogue_context", {}).get("position"))
                        for item in selected_occurrences
                        if item.get("catalogue_context", {}).get("position") is not None
                    }
                ),
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
        porschefanatics.get("source_id")
        != "SRC-PORSCHEFANATICS-993-OIL-COOLER-PET"
        or not str(porschefanatics.get("url", "")).endswith("/104-05/")
        or porschefanatics.get("quality", {}).get("dimensional_accuracy") != "unknown"
    ):
        raise ContractError("porschefanatics_source_boundary")
    oil_tank = load_json(OIL_TANK_REPORT)
    if oil_tank.get("status") != (
        "F1_104_01_oil_tank_circuit_topology_complete_reference_solution_blocked"
    ) or any(value is not False for value in oil_tank.get("claim_boundary", {}).values()):
        raise ContractError("oil_tank_contract")
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
    ("UpstreamOilBoundary", "unresolved_upstream_oil_boundary", (-5.5, 0.0, 0.0)),
    ("OilCoolerCore", "oil_to_air_heat_exchanger_core", (0.0, 0.0, 0.0)),
    ("DownstreamOilBoundary", "unresolved_downstream_oil_boundary", (5.5, 0.0, 0.0)),
    ("CoolingAirInlet", "vehicle_cooling_air_inlet_boundary", (-4.0, -3.0, 0.0)),
    ("AirGuideCowl", "air_guide_cowl_boundary", (-1.5, -2.0, 0.0)),
    ("CoolingBlower", "electrically_driven_blower_boundary", (-1.5, -4.5, 0.0)),
    ("CoolingAirOutlet", "vehicle_cooling_air_outlet_boundary", (4.0, -3.0, 0.0)),
    ("TemperatureSensor", "temperature_sensor_boundary", (0.0, 2.0, 0.0)),
    ("ElectricalPowerBoundary", "vehicle_electrical_power_boundary", (-5.0, 4.0, 0.0)),
    ("ThermalControlBoundary", "unresolved_fan_control_boundary", (-1.5, 4.0, 0.0)),
    ("VehicleMountBoundary", "vehicle_mount_and_vibration_boundary", (4.0, 3.0, 0.0)),
    ("AmbientThermalBoundary", "ambient_thermal_boundary", (5.5, -5.0, 0.0)),
]

TOPOLOGY_EDGES = [
    ("OilSupply", "UpstreamOilBoundary", "OilCoolerCore", "oil_supply_hypothesis"),
    ("OilReturn", "OilCoolerCore", "DownstreamOilBoundary", "oil_return_hypothesis"),
    ("AirInletToGuide", "CoolingAirInlet", "AirGuideCowl", "cooling_air_path_hypothesis"),
    ("GuideToCore", "AirGuideCowl", "OilCoolerCore", "guided_air_path_hypothesis"),
    ("BlowerToGuide", "CoolingBlower", "AirGuideCowl", "forced_air_path_hypothesis"),
    ("CoreToAirOutlet", "OilCoolerCore", "CoolingAirOutlet", "heated_air_path_hypothesis"),
    ("SensorThermalSample", "OilCoolerCore", "TemperatureSensor", "thermal_observation_hypothesis"),
    ("SensorSignal", "TemperatureSensor", "ThermalControlBoundary", "sensor_signal_hypothesis"),
    ("ControlToBlower", "ThermalControlBoundary", "CoolingBlower", "blower_control_hypothesis"),
    ("PowerToControl", "ElectricalPowerBoundary", "ThermalControlBoundary", "electrical_power_hypothesis"),
    ("PowerToBlower", "ElectricalPowerBoundary", "CoolingBlower", "electrical_power_hypothesis"),
    ("CoreToMount", "OilCoolerCore", "VehicleMountBoundary", "mechanical_support_hypothesis"),
    ("CoreToAmbient", "OilCoolerCore", "AmbientThermalBoundary", "ambient_heat_transfer_hypothesis"),
]


def render_usd(roster: list[dict[str, Any]]) -> str:
    positions = {name: point for name, _, point in TOPOLOGY_NODES}
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "OilCoolerCircuitTopologyF1"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        ")",
        "",
        'def Xform "OilCoolerCircuitTopologyF1" (',
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
        ("OCC-GEO-001", "cooler_oil_internal_volume", "m3", ["oil_mass_balance"]),
        ("OCC-GEO-002", "cooler_air_internal_volume", "m3", ["air_mass_balance"]),
        ("OCC-GEO-003", "oil_port_coordinates_sections_and_threads", None, ["F2_interfaces"]),
        ("OCC-GEO-004", "air_guide_and_cowl_geometry", None, ["airflow_CFD"]),
        ("OCC-GEO-005", "oil_pipe_internal_diameters", "m", ["oil_hydraulics"]),
        ("OCC-GEO-006", "oil_pipe_lengths", "m", ["oil_hydraulics"]),
        ("OCC-GEO-007", "oil_pipe_roughness", "m", ["oil_hydraulics"]),
        ("OCC-GEO-008", "fitting_minor_loss_coefficients", None, ["oil_hydraulics"]),
        ("OCC-GEO-009", "core_tube_fin_and_surface_geometry", None, ["CHT"]),
        ("OCC-GEO-010", "wall_and_fin_thicknesses", "m", ["CHT", "structural"]),
        ("OCC-GEO-011", "blower_geometry_and_characteristic_curve", None, ["airflow"]),
        ("OCC-GEO-012", "mount_coordinates_and_stiffness", None, ["vibration"]),
        ("OCC-BC-001", "oil_mass_flow_map", "kg_s", ["oil_hydraulics", "thermal"]),
        ("OCC-BC-002", "oil_inlet_temperature_map", "K", ["thermal"]),
        ("OCC-BC-003", "oil_inlet_pressure_map", "Pa", ["oil_hydraulics"]),
        ("OCC-BC-004", "air_mass_flow_map", "kg_s", ["airflow", "thermal"]),
        ("OCC-BC-005", "air_inlet_temperature_map", "K", ["thermal"]),
        ("OCC-BC-006", "ambient_pressure_map", "Pa", ["airflow"]),
        ("OCC-BC-007", "vehicle_speed_and_yaw_history", None, ["airflow"]),
        ("OCC-BC-008", "blower_voltage_current_and_duty_cycle", None, ["electrical"]),
        ("OCC-BC-009", "engine_speed_and_load_history", None, ["transient"]),
        ("OCC-BC-010", "vehicle_vibration_and_acceleration_history", "m_s2", ["durability"]),
        ("OCC-FLD-001", "oil_density_vs_temperature", "kg_m3", ["hydraulics", "thermal"]),
        ("OCC-FLD-002", "oil_dynamic_viscosity_vs_temperature", "Pa_s", ["hydraulics"]),
        ("OCC-FLD-003", "oil_specific_heat_vs_temperature", "J_kgK", ["thermal"]),
        ("OCC-FLD-004", "oil_thermal_conductivity_vs_temperature", "W_mK", ["CHT"]),
        ("OCC-FLD-005", "air_density_vs_temperature", "kg_m3", ["airflow"]),
        ("OCC-FLD-006", "air_dynamic_viscosity_vs_temperature", "Pa_s", ["airflow"]),
        ("OCC-FLD-007", "air_specific_heat_vs_temperature", "J_kgK", ["thermal"]),
        ("OCC-FLD-008", "air_thermal_conductivity_vs_temperature", "W_mK", ["CHT"]),
        ("OCC-THM-001", "oil_side_heat_transfer_coefficient", "W_m2K", ["CHT"]),
        ("OCC-THM-002", "air_side_heat_transfer_coefficient", "W_m2K", ["CHT"]),
        ("OCC-THM-003", "thermal_contact_resistances", "m2K_W", ["CHT"]),
        ("OCC-THM-004", "surface_emissivities", None, ["radiation"]),
        ("OCC-THM-005", "oil_and_air_fouling_factors", "m2K_W", ["thermal"]),
        ("OCC-THM-006", "core_thermal_mass", "J_K", ["transient"]),
        ("OCC-MAT-001", "core_alloy_temperature_dependent_properties", None, ["thermal", "structural"]),
        ("OCC-MAT-002", "oil_pipe_material_properties", None, ["pressure", "fatigue"]),
        ("OCC-MAT-003", "air_guide_material_properties", None, ["thermal", "vibration"]),
        ("OCC-MAT-004", "mount_elastomer_properties", None, ["vibration"]),
        ("OCC-MAT-005", "fastener_coating_and_corrosion_system", None, ["durability"]),
        ("OCC-MAT-006", "seal_oil_temperature_compatibility", None, ["leak_tightness"]),
        ("OCC-CTL-001", "temperature_sensor_transfer_function", None, ["control"]),
        ("OCC-CTL-002", "blower_switching_and_hysteresis_logic", None, ["control"]),
    ]
    return [unknown_parameter(*definition) for definition in definitions]


def build_report(data: dict[str, Any], usd_text: str) -> dict[str, Any]:
    roster = data["roster"]
    role_counts: dict[str, int] = {}
    for item in roster:
        role = str(item["role_hypothesis"])
        role_counts[role] = role_counts.get(role, 0) + 1
    parameters = parameter_registry()
    equations = [
        {"id": "oil_mass_balance", "equation": "dm_oil_cv/dt=sum(mdot_oil_in)-sum(mdot_oil_out)", "missing_parameter_families": ["oil_volume", "oil_flow_map"]},
        {"id": "air_mass_balance", "equation": "dm_air_cv/dt=sum(mdot_air_in)-sum(mdot_air_out)", "missing_parameter_families": ["air_volume", "air_flow_map"]},
        {"id": "oil_pressure_drop", "equation": "delta_p_oil=f*(L/D)*(rho*v^2/2)+sum(K_i)*(rho*v^2/2)", "missing_parameter_families": ["pipe_geometry", "oil_properties", "fittings"]},
        {"id": "air_pressure_drop", "equation": "delta_p_air=sum(K_j)*(rho_air*v_air^2/2)+delta_p_core", "missing_parameter_families": ["air_geometry", "core_pressure_loss", "air_properties"]},
        {"id": "oil_heat_rate", "equation": "Qdot_oil=mdot_oil*cp_oil*(T_oil_in-T_oil_out)", "missing_parameter_families": ["oil_flow", "oil_specific_heat", "oil_temperatures"]},
        {"id": "air_heat_rate", "equation": "Qdot_air=mdot_air*cp_air*(T_air_out-T_air_in)", "missing_parameter_families": ["air_flow", "air_specific_heat", "air_temperatures"]},
        {"id": "heat_exchanger_balance", "equation": "Qdot_oil=Qdot_air+Qdot_loss+dE_core/dt", "missing_parameter_families": ["thermal_losses", "core_thermal_mass"]},
        {"id": "ntu", "equation": "NTU=UA/C_min", "missing_parameter_families": ["UA", "heat_capacity_rates"]},
        {"id": "effectiveness", "equation": "epsilon=Qdot/(C_min*(T_oil_in-T_air_in))", "missing_parameter_families": ["heat_rate", "capacity_rate", "inlet_temperatures"]},
        {"id": "overall_conductance", "equation": "1/UA=1/(h_oil*A_oil)+R_wall+R_contact+1/(h_air*A_air)+R_fouling", "missing_parameter_families": ["core_geometry", "heat_transfer_coefficients", "materials"]},
        {"id": "core_transient_energy", "equation": "C_core*dT_core/dt=Qdot_oil_to_core-Qdot_core_to_air-Qdot_ambient", "missing_parameter_families": ["core_thermal_mass", "boundary_histories"]},
        {"id": "fan_system_operating_point", "equation": "delta_p_fan(Q,n)=delta_p_system(Q)", "missing_parameter_families": ["fan_curve", "system_curve", "speed"]},
        {"id": "blower_electrical_power", "equation": "P_electric=V*I; P_air=delta_p_air*Q_air=eta_fan*P_electric", "missing_parameter_families": ["voltage", "current", "fan_efficiency"]},
        {"id": "thermal_control", "equation": "u_fan=H(T_sensor-T_on)-H(T_off-T_sensor)", "missing_parameter_families": ["sensor_transfer", "switch_thresholds", "hysteresis"]},
    ]
    load_cases = [
        {"id": "LC-993-OCC-COLD-START", "kind": "cold_start_high_oil_viscosity", "status": "blocked"},
        {"id": "LC-993-OCC-HOT-IDLE", "kind": "hot_idle_low_ram_air_forced_blower", "status": "blocked"},
        {"id": "LC-993-OCC-RATED", "kind": "rated_engine_load_and_vehicle_speed", "status": "blocked"},
        {"id": "LC-993-OCC-HEAT-SOAK", "kind": "shutdown_heat_soak", "status": "blocked"},
        {"id": "LC-993-OCC-FAN-OFF", "kind": "blower_open_circuit_or_control_failure", "status": "blocked"},
        {"id": "LC-993-OCC-BLOCKAGE", "kind": "partial_air_or_oil_path_blockage", "status": "blocked"},
        {"id": "LC-993-OCC-LEAK", "kind": "seal_or_pipe_leak_fault", "status": "blocked"},
        {"id": "LC-993-OCC-VIBRATION", "kind": "road_and_powertrain_vibration_durability", "status": "blocked"},
    ]
    return {
        "$comment": (
            "Contrat F1 de topologie documentaire de la planche PET 104-05. "
            "Le graphe est non spatial et ne constitue ni geometrie de piece ni preuve thermique."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "status": "F1_104_05_oil_cooler_circuit_topology_complete_reference_solution_blocked",
        "source_boundary": {
            "files": [
                source_entry(PET_INDEX, "PET_occurrence_and_part_master_manifest"),
                source_entry(data["occurrence_path"], "PET_104_05_occurrence_records"),
                *data["master_sources"],
                source_entry(PORSCHEFANATICS_SOURCE, "PorscheFanatics_identity_and_system_context_only"),
                source_entry(OIL_TANK_REPORT, "adjacent_104_01_topology_without_interface_transfer"),
                source_entry(PROGRAM_DEFINITION, "PhysicsNeMo_and_Omniverse_policy"),
                source_entry(SIMREADY_PREFLIGHT, "blocked_Omniverse_preflight"),
            ],
            "pet_illustration": ILLUSTRATION,
            "porschefanatics_used_for_identity_and_system_context_only": True,
            "porschefanatics_catalogue_page": "https://porschefanatics.com/oem/993/104-05/",
            "porschefanatics_live_http_status_observed_during_authoring": 200,
            "llm_generated_dimensions_used": False,
            "adjacent_topology_connections_transferred_as_fact": False,
            "independent_metrology_used": False,
            "third_party_geometry_redistributed": False,
        },
        "summary": {
            "pet_104_05_occurrences": EXPECTED_OCCURRENCES,
            "pet_104_05_unique_part_masters": EXPECTED_REFERENCES,
            "pet_part_masters_seen_in_both_sources": sum(len(item["pet_source_ids"]) == 2 for item in roster),
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
            "nodes": [{"id": name, "semantics": semantics, "vehicle_coordinate": None} for name, semantics, _ in TOPOLOGY_NODES],
            "edges": [{"id": name, "from": source, "to": target, "semantics": semantics, "connected_pet_references": None} for name, source, target, semantics in TOPOLOGY_EDGES],
            "ports_and_connections_are_proven": False,
            "oil_tank_or_engine_boundary_coupling_is_proven": False,
            "fan_control_logic_is_proven": False,
            "diagram_coordinates_are_vehicle_coordinates": False,
        },
        "parameter_registry": parameters,
        "mathematical_model": {
            "status": "symbolic_contracts_only_no_operating_point_evaluated",
            "equations": equations,
            "reference_solver_credit": False,
            "network_solution_credit": False,
            "required_first_reference_methods": [
                "configuration_resolved_lumped_oil_and_air_network_with_balance_checks",
                "oil_side_and_air_side_pressure_drop_characterization",
                "conjugate_heat_transfer_after_F3_core_pipe_and_air_domains",
                "fan_curve_and_control_hardware_in_the_loop_or_bench_validation",
                "mount_vibration_and_pressure_fatigue_analysis_after_F3_geometry",
            ],
        },
        "load_cases": load_cases,
        "material_and_manufacturing_route": {
            "status": "role_based_screening_hypotheses_only_no_selection",
            "candidate_matrix": [
                {"role": "heat_exchanger_core", "candidate_family": "thermally_conductive_corrosion_and_oil_compatible_metal", "candidate_process": "qualified_heat_exchanger_manufacturing_brazing_or_welding_and_leak_test", "status": "unsourced_unselected"},
                {"role": "oil_pipe_or_union", "candidate_family": "oil_temperature_pressure_and_fatigue_compatible_tube_or_fitting_metal", "candidate_process": "tube_forming_joining_machining_and_pressure_test", "status": "unsourced_unselected"},
                {"role": "air_guide_or_cowl", "candidate_family": "temperature_and_vibration_compatible_polymer_or_sheet_material", "candidate_process": "moulding_sheet_forming_or_nonfunctional_additive_mockup", "status": "unsourced_unselected"},
                {"role": "seal_or_compliant_mount", "candidate_family": "oil_temperature_ozone_and_compression_set_compatible_elastomer", "candidate_process": "qualified_commercial_or_tooled_process", "status": "unsourced_unselected"},
                {"role": "blower_and_electrical_control", "candidate_family": "qualified_automotive_electromechanical_assembly", "candidate_process": "commercial_component_validation_not_replication_by_default", "status": "unsourced_unselected"},
                {"role": "fit_and_routing_mockup_only", "candidate_family": "polymer_additive_manufacturing", "candidate_process": "FDM_SLS_or_MJF", "status": "unsourced_unselected_nonfunctional_only"},
            ],
            "selected_material_count": 0,
            "selected_functional_manufacturing_route_count": 0,
            "functional_additive_manufacturing_disposition": "prohibited_without_F2_F3_fluid_thermal_vibration_material_leak_electrical_and_professional_review",
            "prototype_disposition": "nonfunctional_fit_and_routing_mockups_only_after_scale_and_interface_evidence",
        },
        "physicsnemo_discovery": {
            "canonical_repository": data["physicsnemo"].get("canonical_repository"),
            "commit": data["physicsnemo"].get("discovered_commit"),
            "paths_verified_live_during_authoring": True,
            "problem_shape": "future_unstructured_oil_air_CFD_CHT_fields_plus_low_order_network_features",
            "model_menu": [
                {"model": "MeshGraphNet", "role": "candidate_mesh_graph pressure_velocity_temperature surrogate after reference dataset", "selected": False},
                {"model": "DoMINO", "role": "candidate surface_volume transient CFD_CHT surrogate after F3 dataset", "selected": False},
                {"model": "GeoTransolver", "role": "candidate geometry_aware unstructured field surrogate after F3 dataset", "selected": False},
                {"model": "Transolver", "role": "candidate structured_or_unstructured PDE field surrogate after reference dataset", "selected": False},
            ],
            "datapipe_menu": [
                {"datapipe": "VTKReader", "role": "future VTK reference-solver field ingestion"},
                {"datapipe": "DoMINODataPipe", "role": "future surface_volume CAE preprocessing"},
                {"datapipe": "TransolverDataPipe", "role": "future unstructured mesh field preprocessing"},
            ],
            "reference_examples": [
                {"example": "cfd/stokes_mgn", "role": "mesh graph velocity and pressure field learning reference, not oil-cooler validation"},
                {"example": "cfd/transient_conjugate_heat_transfer_tank_fill", "role": "transient surface_volume CHT reference, not oil-cooler validation"},
            ],
            "execution_enabled": False,
            "eligibility_gate": "F3_domains_converged_reference_solver_dataset_held_out_geometries_and_loads_and_out_of_domain_rejection",
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
        "next_gate": "resolve_104_05_configuration_topology_F2_interfaces_oil_air_properties_and_fan_control",
    }


def validate(data: dict[str, Any], usd_text: str, report: dict[str, Any]) -> None:
    if report.get("status") != (
        "F1_104_05_oil_cooler_circuit_topology_complete_reference_solution_blocked"
    ):
        raise ContractError("status")
    summary = report.get("summary", {})
    expected = {
        "pet_104_05_occurrences": 80,
        "pet_104_05_unique_part_masters": 43,
        "pet_part_masters_seen_in_both_sources": 37,
        "topology_nodes": 12,
        "topology_edges": 13,
        "symbolic_equation_contracts": 14,
        "blocked_reference_load_cases": 8,
        "unknown_engineering_parameters": 44,
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
    if len(roster) != 43 or len({item.get("pet_part_master_twin_id") for item in roster}) != 43:
        raise ContractError("part_roster")
    if any(
        item.get("interface_geometry") is not None
        or item.get("material") is not None
        or item.get("vehicle_transform") is not None
        for item in roster
    ):
        raise ContractError("part_roster_overclaim")
    parameters = report.get("parameter_registry", [])
    if len(parameters) != 44 or any(
        item.get("value") is not None or item.get("uncertainty") is not None
        for item in parameters
    ):
        raise ContractError("parameter_registry")
    if len(report.get("mathematical_model", {}).get("equations", [])) != 14:
        raise ContractError("equations")
    if report.get("mathematical_model", {}).get("reference_solver_credit") is not False:
        raise ContractError("reference_solver_overclaim")
    if len(report.get("load_cases", [])) != 8 or any(
        item.get("status") != "blocked" for item in report.get("load_cases", [])
    ):
        raise ContractError("load_cases")
    if report.get("physicsnemo_discovery", {}).get("execution_enabled") is not False:
        raise ContractError("physicsnemo_execution")
    if report.get("omniverse_handoff", {}).get("simready_validated") is not False:
        raise ContractError("simready_overclaim")
    if any(value is not False for value in report.get("claim_boundary", {}).values()):
        raise ContractError("claim_boundary")
    if usd_text.count('purpose = "guide"') != 25:
        raise ContractError("usd_guide_count")
    if usd_text.count('def Scope "Part_') != 43:
        raise ContractError("usd_part_roster_count")
    for prohibited in (
        "UsdPhysics",
        "RigidBodyAPI",
        "CollisionAPI",
        "MassAPI",
        "MaterialBindingAPI",
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
                f"wrote {relative(REPORT)}: 43 PET masters, 14 equations, "
                "8 blocked cases, 0 solver results"
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
        print(f"current {relative(REPORT)}: 43 PET masters, topology remains F1")
        return 0
    except (ContractError, OSError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
