#!/usr/bin/env python3
"""Generate PET-linked F1 charge-air guides and a fail-closed 0D contract.

The five primary shapes are supplier-declared envelopes associated with exact
OEM references on PET illustration 107-45.  They are not measurements of the
OEM surfaces or interfaces.  Two aftermarket hose diameters are rendered as
unpositioned coupons and are never promoted to OEM flow areas.
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
PET_INDEX = ROOT / "twins" / "pet-993" / "index-f0.json"
PET_OFFICIAL_SOURCE = (
    ROOT / "catalog" / "sources" / "src-porsche-austria-993-107-45-pet.json"
)
PORSCHEFANATICS_SOURCE = (
    ROOT / "catalog" / "sources" / "src-porschefanatics-993-turbo-pet.json"
)
PROGRAM_DEFINITION = ROOT / "twins" / "vehicle-993" / "program-definition.json"
SIMREADY_PREFLIGHT = (
    ROOT / "twins" / "vehicle-993" / "functional-flow-simready-preflight-f0.json"
)
K16_REPORT = ROOT / "twins" / "catalogue-parts" / "k16-envelope-flow-readiness-f1.json"
REPORT = ROOT / "twins" / "catalogue-parts" / "charge-air-chain-readiness-f1.json"
SCAD_OUTPUT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering"
    / "993-charge-air-chain-guides-f1.scad"
)
USD_OUTPUT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering"
    / "993-charge-air-chain-guides-f1.usda"
)

EXPECTED_PHYSICSNEMO_COMMIT = "4fbfcfd62bf050b48ceec6b438da409b9f4644b3"
EXPECTED_COMPONENTS = {
    "993-INTERCOOLER-PRESSURE-HOSE-LEFT": {
        "oem_reference": "99311063356",
        "dimensions_mm": [430.0, 70.0, 115.0],
        "mass_kg": 0.42,
        "source_id": "SRC-FVD-993-INTERCOOLER-HOSE-LEFT-DIMENSIONS",
        "role": "left_turbo_to_intercooler_pressure_hose",
        "dimension_semantics": "supplier_replacement_product_bounding_box_not_OEM_surface",
    },
    "993-INTERCOOLER-PRESSURE-HOSE-RIGHT": {
        "oem_reference": "99311063256",
        "dimensions_mm": [430.0, 70.0, 90.0],
        "mass_kg": 0.42,
        "source_id": "SRC-FVD-993-INTERCOOLER-HOSE-RIGHT-DIMENSIONS",
        "role": "right_turbo_to_intercooler_pressure_hose",
        "dimension_semantics": "supplier_replacement_product_bounding_box_not_OEM_surface",
    },
    "993-INTERCOOLER-REPLACEMENT-AKS": {
        "oem_reference": "99311033053",
        "dimensions_mm": [260.0, 270.0, 60.0],
        "mass_kg": 7.06,
        "source_id": "SRC-AKS-DASIS-993-INTERCOOLER-DIMENSIONS",
        "role": "replacement_intercooler_core_reference",
        "dimension_semantics": "aftermarket_core_only_not_complete_OEM_intercooler_envelope",
    },
    "993-INTERCOOLER-AIR-DUCT": {
        "oem_reference": "99311034054",
        "dimensions_mm": [600.0, 280.0, 50.0],
        "mass_kg": 0.9,
        "source_id": "SRC-FVD-993-INTERCOOLER-AIR-DUCT-DIMENSIONS",
        "role": "ambient_air_guide_reference",
        "dimension_semantics": "supplier_replacement_product_bounding_box_not_OEM_surface",
    },
    "993-INTERCOOLER-TEMPERATURE-SENSOR": {
        "oem_reference": "99360611400",
        "dimensions_mm": [75.0, 35.0, 20.0],
        "mass_kg": 0.02,
        "source_id": "SRC-FVD-993-CHARGE-AIR-TEMPERATURE-SENSOR-DIMENSIONS",
        "role": "charge_air_temperature_observation_reference",
        "dimension_semantics": "supplier_product_bounding_box_not_thread_or_probe_geometry",
    },
}
SOURCE_FILE_BY_ID = {
    "SRC-FVD-993-INTERCOOLER-HOSE-LEFT-DIMENSIONS": ROOT
    / "catalog"
    / "sources"
    / "src-fvd-993-intercooler-hose-left-dimensions.json",
    "SRC-FVD-993-INTERCOOLER-HOSE-RIGHT-DIMENSIONS": ROOT
    / "catalog"
    / "sources"
    / "src-fvd-993-intercooler-hose-right-dimensions.json",
    "SRC-AKS-DASIS-993-INTERCOOLER-DIMENSIONS": ROOT
    / "catalog"
    / "sources"
    / "src-aks-dasis-993-intercooler-dimensions.json",
    "SRC-FVD-993-INTERCOOLER-AIR-DUCT-DIMENSIONS": ROOT
    / "catalog"
    / "sources"
    / "src-fvd-993-intercooler-air-duct-dimensions.json",
    "SRC-FVD-993-CHARGE-AIR-TEMPERATURE-SENSOR-DIMENSIONS": ROOT
    / "catalog"
    / "sources"
    / "src-fvd-993-charge-air-temperature-sensor-dimensions.json",
}


class ContractError(ValueError):
    """Raised if a charge-air guide loses provenance or overstates maturity."""


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


def read_part_masters(index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_reference: dict[str, dict[str, Any]] = {}
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
        record_count = 0
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                record_count += 1
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ContractError(
                        f"pet_part_master_json:{path_value}:{line_number}:{exc}"
                    ) from exc
                reference = record.get("subject", {}).get("normalized_oem_reference")
                if isinstance(reference, str):
                    by_reference[reference] = record
        if record_count != shard.get("record_count"):
            raise ContractError(f"pet_part_master_shard_count:{path_value}")
    return by_reference


def declared_entries() -> dict[str, dict[str, Any]]:
    payload = load_json(DECLARED_DATA)
    return {
        item["entry_id"]: item
        for item in payload.get("entries", [])
        if isinstance(item, dict) and isinstance(item.get("entry_id"), str)
    }


def derive() -> dict[str, Any]:
    entries = declared_entries()
    masters = read_part_masters(load_json(PET_INDEX))
    official_pet = load_json(PET_OFFICIAL_SOURCE)
    porschefanatics = load_json(PORSCHEFANATICS_SOURCE)
    program = load_json(PROGRAM_DEFINITION)
    preflight = load_json(SIMREADY_PREFLIGHT)
    k16 = load_json(K16_REPORT)

    if official_pet.get("source_id") != "SRC-PORSCHE-AUSTRIA-993-107-45-PET":
        raise ContractError("official_pet_source")
    if porschefanatics.get("source_id") != "SRC-PORSCHEFANATICS-993-TURBO-PET":
        raise ContractError("porschefanatics_source")
    if preflight.get("status") != "blocked":
        raise ContractError("simready_preflight_must_be_reassessed")
    if preflight.get("result_boundary", {}).get("simready_validated") is not False:
        raise ContractError("simready_preflight_overclaim")
    physicsnemo = program.get("physicsnemo_policy", {})
    if (
        physicsnemo.get("execution_enabled") is not False
        or physicsnemo.get("discovered_commit") != EXPECTED_PHYSICSNEMO_COMMIT
    ):
        raise ContractError("physicsnemo_policy")
    if k16.get("status") != (
        "F1_K16_envelope_and_diameter_guides_complete_zeroD_execution_blocked"
    ):
        raise ContractError("upstream_k16_contract")

    components: list[dict[str, Any]] = []
    for entry_id, expected in EXPECTED_COMPONENTS.items():
        entry = entries.get(entry_id)
        if not isinstance(entry, dict):
            raise ContractError(f"declared_entry:{entry_id}")
        for field in ("dimensions_mm", "mass_kg", "source_id"):
            if entry.get(field) != expected[field]:
                raise ContractError(f"declared_entry_value:{entry_id}:{field}")
        reference = entry.get("oem_reference")
        if not isinstance(reference, str) or normalize_reference(reference) != expected[
            "oem_reference"
        ]:
            raise ContractError(f"declared_entry_reference:{entry_id}")
        source_path = SOURCE_FILE_BY_ID[expected["source_id"]]
        if load_json(source_path).get("source_id") != expected["source_id"]:
            raise ContractError(f"source_identity:{entry_id}")
        master = masters.get(expected["oem_reference"])
        if not isinstance(master, dict):
            raise ContractError(f"pet_master_missing:{entry_id}")
        observations = master.get("documentary_graph", {}).get(
            "declared_engineering_observations", []
        )
        if not any(
            isinstance(item, dict)
            and item.get("entry_id") == entry_id
            and item.get("bounding_box_mm") == expected["dimensions_mm"]
            and item.get("source_id") == expected["source_id"]
            for item in observations
        ):
            raise ContractError(f"pet_master_declared_observation:{entry_id}")
        dimensions = [float(value) for value in expected["dimensions_mm"]]
        components.append(
            {
                "component_id": entry_id,
                "name": entry.get("name"),
                "role": expected["role"],
                "oem_reference": expected["oem_reference"],
                "display_reference": reference,
                "pet_part_master_twin_id": master.get("twin_id"),
                "pet_illustrations": master.get("documentary_graph", {}).get(
                    "pet_illustrations", []
                ),
                "source_id": expected["source_id"],
                "supplier_declared_bounding_box_mm": dimensions,
                "supplier_declared_mass_kg": expected["mass_kg"],
                "bounding_box_volume_m3": math.prod(value / 1000.0 for value in dimensions),
                "dimension_semantics": expected["dimension_semantics"],
                "geometry_credit": "F1_envelope_guide_only",
                "interface_coordinate_count": 0,
                "selected_material": None,
            }
        )
    components.sort(key=lambda item: item["oem_reference"])

    hose_kit = entries.get("993-INTERCOOLER-PRESSURE-HOSE-KIT-FVD", {})
    hose_extra = hose_kit.get("additional_declared_dimensions", {})
    if hose_extra != {
        "connection_length_mm": 410.0,
        "diameter_pair_mm": [43.0, 57.0],
        "semantics": "aftermarket_connection_reference_not_OEM_interface_geometry",
    }:
        raise ContractError("aftermarket_hose_dimensions")
    ta_core = entries.get("993-INTERCOOLER-TA-TECHNIX-CORE-MODULE", {})
    ta_extra = ta_core.get("additional_declared_dimensions", {})
    if (
        ta_extra.get("connection_inner_diameter_mm", 0)
        <= ta_extra.get("connection_outer_diameter_mm", 0)
        or ta_extra.get("status")
        != "quarantined_source_inconsistency_inner_diameter_exceeds_outer_diameter"
    ):
        raise ContractError("TA_Technix_inconsistency_not_quarantined")

    return {
        "components": components,
        "hose_kit": hose_kit,
        "hose_extra": hose_extra,
        "ta_core": ta_core,
        "ta_extra": ta_extra,
        "physicsnemo": physicsnemo,
        "preflight": preflight,
        "k16": k16,
    }


def scad_identifier(value: str) -> str:
    return value.lower().replace("-", "_")


def render_scad(data: dict[str, Any]) -> str:
    lines = [
        "// PET 107-45 charge-air F1 guides; not OEM shapes or interfaces.",
        "// Component offsets and two aftermarket diameter coupons are display-only.",
        "$fn = 96;",
        "coupon_thickness_mm = 2.000000; // visualization hypothesis only",
        "",
        "module envelope_guide(size_mm) { cube(size_mm, center = true); }",
        "module diameter_coupon(diameter_mm) {",
        "    cylinder(h = coupon_thickness_mm, d = diameter_mm, center = true);",
        "}",
        "",
    ]
    offsets = [(-520.0, 0.0, 0.0), (520.0, 0.0, 0.0), (0.0, 360.0, 0.0), (0.0, -360.0, 0.0), (0.0, 0.0, 180.0)]
    for component, offset in zip(data["components"], offsets, strict=True):
        dims = component["supplier_declared_bounding_box_mm"]
        lines.extend(
            [
                f"// {component['component_id']}: {component['dimension_semantics']}",
                f"{scad_identifier(component['component_id'])}_mm = [{dims[0]:.6f}, {dims[1]:.6f}, {dims[2]:.6f}];",
                f"translate([{offset[0]:.6f}, {offset[1]:.6f}, {offset[2]:.6f}])",
                f"    envelope_guide({scad_identifier(component['component_id'])}_mm);",
                "",
            ]
        )
    lines.append("// Aftermarket 43/57 mm coupons: no side, endpoint or OEM applicability assigned.")
    for offset, diameter in zip((-60.0, 60.0), data["hose_extra"]["diameter_pair_mm"], strict=True):
        lines.extend(
            [
                f"translate([{offset:.6f}, -720.000000, 0])",
                f"    diameter_coupon({float(diameter):.6f});",
            ]
        )
    return "\n".join(lines) + "\n"


def usd_name(identifier: str) -> str:
    return "Guide" + "".join(
        part.capitalize() for part in identifier.lower().split("-")
    )


def render_usd(data: dict[str, Any]) -> str:
    offsets = [(-520.0, 0.0, 0.0), (520.0, 0.0, 0.0), (0.0, 360.0, 0.0), (0.0, -360.0, 0.0), (0.0, 0.0, 180.0)]
    component_blocks: list[str] = []
    for component, offset in zip(data["components"], offsets, strict=True):
        dims = component["supplier_declared_bounding_box_mm"]
        component_blocks.append(
            f'''    def Xform "{usd_name(component['component_id'])}" (
        kind = "component"
    )
    {{
        custom string componentId = "{component['component_id']}"
        custom string fidelity = "F1_supplier_envelope_guide_unvalidated"
        custom string oemReference = "{component['oem_reference']}"
        custom string petPartMasterTwinId = "{component['pet_part_master_twin_id']}"
        custom string dimensionalEvidence = "{component['dimension_semantics']}"
        custom double supplierDeclaredMassKg = {float(component['supplier_declared_mass_kg']):.6f}
        custom bool interfaceGeometryPresent = false
        custom bool analysisGeometryAvailable = false
        custom bool materialAssigned = false
        custom bool simReadyValidated = false
        double3 xformOp:translate = ({offset[0]:.6f}, {offset[1]:.6f}, {offset[2]:.6f})
        uniform token[] xformOpOrder = ["xformOp:translate"]

        def Cube "BoundingEnvelopeGuide"
        {{
            double size = 1
            uniform token purpose = "guide"
            double3 xformOp:scale = ({dims[0]:.6f}, {dims[1]:.6f}, {dims[2]:.6f})
            uniform token[] xformOpOrder = ["xformOp:scale"]
        }}
    }}'''
        )
    coupons = []
    for offset, diameter in zip((-60.0, 60.0), data["hose_extra"]["diameter_pair_mm"], strict=True):
        coupons.append(
            f'''        def Cylinder "AftermarketDiameter{int(diameter)}Coupon"
        {{
            custom string dimensionalEvidence = "aftermarket_hose_kit_not_OEM_interface"
            custom bool assignedToEndpoint = false
            uniform token axis = "Z"
            double height = 2.000000
            double radius = {float(diameter) / 2.0:.6f}
            uniform token purpose = "guide"
            double3 xformOp:translate = ({offset:.6f}, 0, 0)
            uniform token[] xformOpOrder = ["xformOp:translate"]
        }}'''
        )
    return '''#usda 1.0
(
    defaultPrim = "ChargeAirChainGuidesF1"
    metersPerUnit = 0.001
    upAxis = "Z"
)

def Xform "ChargeAirChainGuidesF1" (
    kind = "assembly"
)
{
    custom string status = "F1_envelopes_not_F2_F3_CFD_CHT_sensor_or_SimReady"
    custom bool componentTransformsAreVehicleCoordinates = false
    custom bool physicsAssigned = false
    custom bool materialAssigned = false
    custom bool simReadyValidated = false
''' + "\n\n".join(component_blocks) + '''

    def Xform "UnpositionedAftermarketDiameterCoupons"
    {
        custom string placementStatus = "display_layout_only_not_OEM_endpoints"
        double3 xformOp:translate = (0, -720.000000, 0)
        uniform token[] xformOpOrder = ["xformOp:translate"]

''' + "\n\n".join(coupons) + '''
    }
}
'''


def source_entry(path: Path, role: str) -> dict[str, Any]:
    return {"path": relative(path), "sha256": sha256_file(path), "role": role}


def build_report(data: dict[str, Any], scad_text: str, usd_text: str) -> dict[str, Any]:
    components = data["components"]
    masses = [float(item["supplier_declared_mass_kg"]) for item in components]
    preflight = data["preflight"]
    physicsnemo = data["physicsnemo"]
    source_files = [
        source_entry(DECLARED_DATA, "structured_supplier_observations"),
        source_entry(PET_INDEX, "PET_master_shard_manifest"),
        source_entry(PET_OFFICIAL_SOURCE, "official_107_45_identity_context"),
        source_entry(PORSCHEFANATICS_SOURCE, "PorscheFanatics_107_45_catalogue_context"),
        source_entry(PROGRAM_DEFINITION, "PhysicsNeMo_and_Omniverse_policy"),
        source_entry(SIMREADY_PREFLIGHT, "blocked_Omniverse_preflight"),
        source_entry(K16_REPORT, "upstream_turbo_envelope_and_zeroD_boundary"),
    ]
    source_files.extend(
        source_entry(path, "supplier_declared_component_observation")
        for path in SOURCE_FILE_BY_ID.values()
    )
    return {
        "$comment": (
            "Guides F1 de la chaine d'air de suralimentation lies exactement au PET 107-45. "
            "Les enveloppes, coupons et equations ne constituent ni CAO OEM ni preuve de fonctionnement."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "status": "F1_charge_air_chain_guides_complete_zeroD_execution_blocked",
        "source_boundary": {
            "files": source_files,
            "third_party_geometry_redistributed": False,
            "llm_generated_dimensions_used": False,
            "independent_metrology_used": False,
            "porschefanatics_used_for_identity_and_system_context_only": True,
        },
        "summary": {
            "pet_linked_component_guides": 5,
            "pet_linked_oem_references": 5,
            "pet_linked_part_masters": 5,
            "supplier_declared_bounding_boxes": 5,
            "supplier_declared_mass_observations": 5,
            "aftermarket_unpositioned_diameter_coupons": 2,
            "quarantined_source_inconsistencies": 1,
            "symbolic_zeroD_equation_contracts": 8,
            "evaluated_zeroD_operating_points": 0,
            "selected_interface_coordinates": 0,
            "selected_flow_areas": 0,
            "qualified_material_decisions": 0,
            "reference_solver_results": 0,
            "physicsnemo_results": 0,
            "simready_assets": 0,
            "manufacturing_releases": 0,
        },
        "components": components,
        "aftermarket_dimensional_guides": {
            "source_entry_id": data["hose_kit"].get("entry_id"),
            "connection_length_mm": data["hose_extra"]["connection_length_mm"],
            "diameter_pair_mm": data["hose_extra"]["diameter_pair_mm"],
            "representation": "two_unpositioned_diameter_coupons_only",
            "assigned_side_count": 0,
            "assigned_endpoint_count": 0,
            "promoted_OEM_interface_dimension_count": 0,
            "pressure_test_value_available": False,
            "geometry_credit": "aftermarket_reference_guides_only",
        },
        "quarantined_evidence": [
            {
                "entry_id": data["ta_core"].get("entry_id"),
                "source_id": data["ta_core"].get("source_id"),
                "outer_diameter_mm": data["ta_extra"].get(
                    "connection_outer_diameter_mm"
                ),
                "inner_diameter_mm": data["ta_extra"].get(
                    "connection_inner_diameter_mm"
                ),
                "reason": "declared_inner_diameter_exceeds_declared_outer_diameter",
                "promoted_to_geometry_or_flow_area": False,
            }
        ],
        "arithmetic_consistency": {
            "status": "passed_arithmetic_only_not_geometry_thermal_or_flow_validation",
            "positive_bounding_box_count": sum(
                all(float(value) > 0 for value in item["supplier_declared_bounding_box_mm"])
                for item in components
            ),
            "sum_of_non_equivalent_supplier_mass_observations_kg": round(sum(masses), 9),
            "mass_sum_interpretation": "not_a_vehicle_BOM_mass_and_not_a_complete_OEM_charge_air_assembly",
            "left_right_supplier_hose_box_length_difference_mm": 0.0,
            "supplier_individual_hose_box_length_minus_aftermarket_kit_connection_length_mm": 20.0,
            "dimension_comparison_interpretation": "different_product_and_dimension_semantics_no_fit_inference",
        },
        "network_topology": {
            "status": "LLM_assisted_functional_hypothesis_requires_engineering_review",
            "nodes": [
                "K16_left_compressor_outlet_unknown_interface",
                "left_pressure_hose_unknown_endpoints",
                "intercooler_left_inlet_unknown_interface",
                "K16_right_compressor_outlet_unknown_interface",
                "right_pressure_hose_unknown_endpoints",
                "intercooler_right_inlet_unknown_interface",
                "intercooler_internal_charge_air_control_volume_unknown",
                "engine_charge_air_outlet_unknown_interface",
                "ambient_duct_stream_unknown_section",
                "charge_air_temperature_sensor_unknown_transfer_function",
            ],
            "edges": [
                "K16_left_to_left_hose_to_intercooler_hypothesis",
                "K16_right_to_right_hose_to_intercooler_hypothesis",
                "intercooler_charge_air_to_engine_hypothesis",
                "ambient_air_through_duct_and_core_hypothesis",
                "sensor_observes_supplier_described_intercooler_inlet_region_hypothesis",
            ],
            "known_vehicle_transform_count": 0,
            "known_OEM_interface_coordinate_count": 0,
            "known_OEM_flow_area_count": 0,
            "upstream_k16_contract": relative(K16_REPORT),
            "topology_is_packaging_or_fitment_proof": False,
        },
        "zeroD_model": {
            "status": "symbolic_contracts_only_no_operating_point_evaluated",
            "equations": [
                {
                    "id": "charge_air_mass_balance",
                    "equation": "dm_cv/dt = mdot_L + mdot_R - mdot_engine",
                    "missing": ["mdot_L", "mdot_R", "mdot_engine", "control_volume"],
                },
                {
                    "id": "left_hose_velocity",
                    "equation": "v_L = mdot_L / (rho_L * A_L)",
                    "missing": ["mdot_L", "rho_L", "OEM_left_internal_flow_area"],
                },
                {
                    "id": "right_hose_velocity",
                    "equation": "v_R = mdot_R / (rho_R * A_R)",
                    "missing": ["mdot_R", "rho_R", "OEM_right_internal_flow_area"],
                },
                {
                    "id": "hose_pressure_loss",
                    "equation": "delta_p_i = (f_i*L_i/Dh_i + sum(K_i))*rho_i*v_i^2/2",
                    "missing": ["OEM_lengths", "hydraulic_diameters", "roughness", "bend_and_joint_loss_coefficients", "Reynolds_number"],
                },
                {
                    "id": "intercooler_energy_balance",
                    "equation": "Qdot = mdot_charge*cp_charge*(T_in-T_out)",
                    "missing": ["mdot_charge", "cp_charge", "T_in", "T_out"],
                },
                {
                    "id": "intercooler_effectiveness",
                    "equation": "epsilon = (T_in-T_out)/(T_in-T_ambient)",
                    "missing": ["T_in", "T_out", "T_ambient", "operating_point_definition"],
                },
                {
                    "id": "intercooler_pressure_loss",
                    "equation": "delta_p_ic = zeta_ic*rho_charge*v_core^2/2",
                    "missing": ["zeta_ic_map", "free_flow_area", "rho_charge", "core_geometry"],
                },
                {
                    "id": "sensor_first_order_response",
                    "equation": "tau_s*dT_s/dt + T_s = T_gas",
                    "missing": ["sensor_calibration", "tau_s", "tolerance", "installation_conduction_and_radiation"],
                },
            ],
            "operating_point_available": False,
            "reference_solver_credit": False,
            "network_solution_credit": False,
            "required_first_reference_methods": [
                "0D_1D_pressure_flow_temperature_network_after_F2_interfaces",
                "mesh_independent_CFD_and_CHT_after_F3_internal_fluid_and_solid_domains",
                "sensor_calibration_model_after_identification_or_bench_data",
            ],
        },
        "material_and_manufacturing_route": {
            "status": "LLM_hypotheses_only_no_selection",
            "hypothesis_matrix": [
                {"component": "pressure_hoses", "candidate_family": "high_temperature_reinforced_elastomer_or_silicone_system", "candidate_process": "mandrel_moulding_or_equivalent", "status": "unsourced_unselected"},
                {"component": "intercooler_core_and_end_tanks", "candidate_family": "aluminium_heat_exchanger_alloy_system", "candidate_process": "brazing_welding_and_finish_machining", "status": "unsourced_unselected"},
                {"component": "ambient_air_duct", "candidate_family": "temperature_resistant_polymer_or_composite", "candidate_process": "moulding_or_additive_prototype_then_qualified_production_process", "status": "unsourced_unselected"},
                {"component": "temperature_sensor", "candidate_family": "purchased_multimaterial_sensor_assembly", "candidate_process": "buy_and_validate_not_reverse_engineer_for_functional_release", "status": "unsourced_unselected"},
            ],
            "selected_material_count": 0,
            "selected_functional_manufacturing_route_count": 0,
            "additive_or_CNC_release": "prohibited_pending_F2_F3_material_environment_pressure_thermal_fatigue_and_professional_review",
        },
        "physicsnemo_discovery": {
            "canonical_repository": physicsnemo.get("canonical_repository"),
            "commit": physicsnemo.get("discovered_commit"),
            "paths_verified_live_during_authoring": True,
            "local_revalidation_required_before_execution": True,
            "model_menu": [
                {"model": "GeoTransolver", "path": "physicsnemo/models/geotransolver", "role": "candidate_irregular_mesh_CFD_or_CHT_field_surrogate_after_reference_dataset", "selected": False},
                {"model": "Transolver", "path": "physicsnemo/models/transolver", "role": "candidate_irregular_mesh_CFD_or_CHT_field_surrogate_after_reference_dataset", "selected": False},
                {"model": "MeshGraphNet", "path": "physicsnemo/models/meshgraphnet", "role": "exploratory_mesh_graph_candidate_requires_charge_air_specific_formulation", "selected": False},
                {"model": "DoMINO", "path": "physicsnemo/models/domino", "role": "not_selected_external_aerodynamics_recipe_is_not_internal_charge_air_validation", "selected": False},
            ],
            "verified_data_interfaces": [
                "physicsnemo/datapipes/cae/TransolverDataPipe",
                "physicsnemo/datapipes/cae/DoMINODataPipe",
            ],
            "execution_enabled": False,
            "eligibility_gate": "F3_watertight_fluid_and_solid_domains_plus_converged_CFD_CHT_dataset_with_held_out_geometry_and_operating_cases",
        },
        "omniverse_handoff": {
            "openusd_source_authoring": "completed_as_guides",
            "property_assignment_intent": "run",
            "preflight_report": relative(SIMREADY_PREFLIGHT),
            "preflight_status": preflight.get("status"),
            "preflight_blockers": preflight.get("blockers", []),
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
            "openusd_component_prim_count": 5,
            "openusd_guide_primitive_count": 7,
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
            "is_evaluated_operating_point": False,
            "is_reference_network_CFD_CHT_or_sensor_result": False,
            "is_physicsnemo_result": False,
            "is_simready_validated": False,
            "is_manufacturing_or_vehicle_release": False,
        },
        "next_gate": "resolve_configuration_applicability_then_acquire_F2_interface_coordinates_sections_tolerances_and_material_identification",
    }


def validate(data: dict[str, Any], scad_text: str, usd_text: str, report: dict[str, Any]) -> None:
    if report.get("status") != "F1_charge_air_chain_guides_complete_zeroD_execution_blocked":
        raise ContractError("status")
    expected_summary = {
        "pet_linked_component_guides": 5,
        "pet_linked_oem_references": 5,
        "pet_linked_part_masters": 5,
        "supplier_declared_bounding_boxes": 5,
        "supplier_declared_mass_observations": 5,
        "aftermarket_unpositioned_diameter_coupons": 2,
        "quarantined_source_inconsistencies": 1,
        "symbolic_zeroD_equation_contracts": 8,
        "evaluated_zeroD_operating_points": 0,
        "selected_interface_coordinates": 0,
        "selected_flow_areas": 0,
        "qualified_material_decisions": 0,
        "reference_solver_results": 0,
        "physicsnemo_results": 0,
        "simready_assets": 0,
        "manufacturing_releases": 0,
    }
    if report.get("summary") != expected_summary:
        raise ContractError("summary")
    components = report.get("components", [])
    if len(components) != 5 or len({item.get("oem_reference") for item in components}) != 5:
        raise ContractError("components")
    if len({item.get("pet_part_master_twin_id") for item in components}) != 5:
        raise ContractError("pet_master_links")
    if any(item.get("interface_coordinate_count") != 0 for item in components):
        raise ContractError("interface_overclaim")
    if usd_text.count('kind = "component"') != 5 or usd_text.count('purpose = "guide"') != 7:
        raise ContractError("usd_guide_counts")
    for prohibited in (
        "UsdPhysics",
        "RigidBodyAPI",
        "CollisionAPI",
        "MassAPI",
        "MaterialBindingAPI",
    ):
        if prohibited in usd_text:
            raise ContractError(f"usd_overclaim:{prohibited}")
    if report.get("zeroD_model", {}).get("reference_solver_credit") is not False:
        raise ContractError("reference_solver_overclaim")
    if report.get("physicsnemo_discovery", {}).get("execution_enabled") is not False:
        raise ContractError("physicsnemo_execution")
    if report.get("omniverse_handoff", {}).get("simready_validated") is not False:
        raise ContractError("simready_overclaim")
    if report.get("material_and_manufacturing_route", {}).get("selected_material_count") != 0:
        raise ContractError("material_overclaim")
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
        scad_text = render_scad(data)
        usd_text = render_usd(data)
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
        print(f"current {relative(REPORT)}: 5 PET-linked charge-air guides")
        return 0
    except (ContractError, OSError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
