#!/usr/bin/env python3
"""Generate fail-closed PET-linked K16 envelope and diameter guides.

Only supplier-declared complete-unit envelopes, masses and right-side wheel
diameters are used.  Wheel diameter coupons are deliberately placed outside
the assembly envelopes: their display locations and thicknesses are not K16
geometry.  The accompanying 0D equations remain symbolic until sourced maps,
operating points and fluid properties exist.
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
PART = ROOT / "catalog" / "parts" / "993-turbocharger-k16-pair-0001.json"
FVD_SOURCE = ROOT / "catalog" / "sources" / "src-fvd-993-k16-oem-dimensions.json"
INTERNAL_SOURCE = (
    ROOT
    / "catalog"
    / "sources"
    / "src-invasionautoproducts-993-k16-internal-data.json"
)
CROSSWALK = ROOT / "twins" / "pet-993" / "catalog-crosswalk-f0.json"
ENGINE_FAMILIES = (
    ROOT / "twins" / "engine-simulation-contracts" / "engine-components-f1.json"
)
ENGINE_LOAD_CASES = (
    ROOT / "twins" / "engine-simulation-contracts" / "load-cases-f1.json"
)
ENGINE_MATERIALS = (
    ROOT / "twins" / "engine-simulation-contracts" / "materials-f1.json"
)
PROGRAM_DEFINITION = ROOT / "twins" / "vehicle-993" / "program-definition.json"
COLD_SIDE_PARAMETERS = (
    ROOT / "simulation" / "993-k16-cold-side-baseline" / "parameters.json"
)
REPORT = (
    ROOT / "twins" / "catalogue-parts" / "k16-envelope-flow-readiness-f1.json"
)
SCAD_OUTPUT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering"
    / "993-k16-envelope-diameter-guides-f1.scad"
)
USD_OUTPUT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering"
    / "993-k16-envelope-diameter-guides-f1.usda"
)

EXPECTED_PART_ID = "993-TURBOCHARGER-K16-PAIR-0001"
EXPECTED_REFERENCES = {
    "left": ["99312301351", "99312301352"],
    "right": ["99312301451", "99312301452"],
}
EXPECTED_DIMENSIONS = {
    "envelope_mm": [280.0, 190.0, 210.0],
    "left_declared_mass_kg": 5.76,
    "right_declared_mass_kg": 5.6,
    "compressor_inducer_mm": 40.6,
    "compressor_exducer_mm": 60.5,
    "turbine_inducer_mm": 54.96,
    "turbine_exducer_mm": 48.97,
}
EXPECTED_PHYSICSNEMO_COMMIT = "4fbfcfd62bf050b48ceec6b438da409b9f4644b3"


class ContractError(ValueError):
    """Raised when a K16 guide would lose provenance or overclaim maturity."""


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


def normalize_reference(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())


def pet_master_links(crosswalk: dict[str, Any]) -> dict[str, list[str]]:
    entry = next(
        (
            item
            for item in crosswalk.get("parts", [])
            if isinstance(item, dict) and item.get("part_id") == EXPECTED_PART_ID
        ),
        None,
    )
    if entry is None or entry.get("unmatched_oem_references") != []:
        raise ContractError("k16_crosswalk")
    by_reference: dict[str, set[str]] = {}
    for match in entry.get("pet_occurrence_matches", []):
        if not isinstance(match, dict):
            raise ContractError("k16_crosswalk_match")
        reference = match.get("oem_reference")
        master_id = match.get("part_master_twin_id")
        if not isinstance(reference, str) or not isinstance(master_id, str):
            raise ContractError("k16_crosswalk_identity")
        by_reference.setdefault(normalize_reference(reference), set()).add(master_id)
    expected = set(EXPECTED_REFERENCES["left"] + EXPECTED_REFERENCES["right"])
    if set(by_reference) != expected:
        raise ContractError(f"k16_crosswalk_references:{sorted(by_reference)}")
    return {key: sorted(value) for key, value in sorted(by_reference.items())}


def derive() -> dict[str, Any]:
    part = load_json(PART)
    fvd = load_json(FVD_SOURCE)
    internal = load_json(INTERNAL_SOURCE)
    families = load_json(ENGINE_FAMILIES)
    load_cases = load_json(ENGINE_LOAD_CASES)
    materials = load_json(ENGINE_MATERIALS)
    program = load_json(PROGRAM_DEFINITION)
    cold_side = load_json(COLD_SIDE_PARAMETERS)

    if part.get("part_id") != EXPECTED_PART_ID:
        raise ContractError("part_identity")
    actual_references = {
        normalize_reference(value)
        for value in part.get("vehicle", {}).get("porsche_part_numbers", [])
        if isinstance(value, str)
    }
    if actual_references != set(
        EXPECTED_REFERENCES["left"] + EXPECTED_REFERENCES["right"]
    ):
        raise ContractError("part_references")
    if fvd.get("source_id") != "SRC-FVD-993-K16-OEM-DIMENSIONS":
        raise ContractError("fvd_source_identity")
    if internal.get("source_id") != "SRC-INVASIONAUTOPRODUCTS-993-K16-INTERNAL-DATA":
        raise ContractError("internal_source_identity")

    family = families.get("families", {}).get("turbocharger_k16_pair")
    if not isinstance(family, dict):
        raise ContractError("engine_family")
    for field, expected in EXPECTED_DIMENSIONS.items():
        if family.get(field) != expected:
            raise ContractError(f"engine_family_value:{field}")
    load_case = next(
        (
            item
            for item in load_cases.get("load_cases", [])
            if isinstance(item, dict)
            and item.get("load_case_id") == "LC-993-K16-COMPRESSOR-TURBINE"
        ),
        None,
    )
    if load_case is None or not str(load_case.get("status", "")).startswith("blocked_"):
        raise ContractError("k16_load_case")
    material = materials.get("materials", {}).get("k16_subassemblies_unknown")
    if not isinstance(material, dict) or material.get("assignment_status") != "unassigned":
        raise ContractError("k16_material_status")

    physicsnemo = program.get("physicsnemo_policy", {})
    if (
        physicsnemo.get("execution_enabled") is not False
        or physicsnemo.get("discovered_commit") != EXPECTED_PHYSICSNEMO_COMMIT
    ):
        raise ContractError("physicsnemo_policy")
    verified_models = set(physicsnemo.get("verified_model_families", []))
    required_models = {"DoMINO", "GeoTransolver", "Transolver", "MeshGraphNet"}
    if not required_models <= verified_models:
        raise ContractError("physicsnemo_model_discovery")

    declared_reference = cold_side.get("declared_k16_reference", {})
    cold_expected = {
        "complete_unit_envelope_mm": EXPECTED_DIMENSIONS["envelope_mm"],
        "left_mass_kg": EXPECTED_DIMENSIONS["left_declared_mass_kg"],
        "right_mass_kg": EXPECTED_DIMENSIONS["right_declared_mass_kg"],
        "right_turbine_inducer_mm": EXPECTED_DIMENSIONS["turbine_inducer_mm"],
        "right_turbine_exducer_mm": EXPECTED_DIMENSIONS["turbine_exducer_mm"],
        "right_compressor_inducer_mm": EXPECTED_DIMENSIONS["compressor_inducer_mm"],
        "right_compressor_exducer_mm": EXPECTED_DIMENSIONS["compressor_exducer_mm"],
    }
    for field, expected in cold_expected.items():
        if declared_reference.get(field) != expected:
            raise ContractError(f"cold_side_reference:{field}")

    links = pet_master_links(load_json(CROSSWALK))
    envelope_m = [value / 1000.0 for value in EXPECTED_DIMENSIONS["envelope_mm"]]
    envelope_volume_m3 = math.prod(envelope_m)
    left_mass = EXPECTED_DIMENSIONS["left_declared_mass_kg"]
    right_mass = EXPECTED_DIMENSIONS["right_declared_mass_kg"]

    variants = []
    for side, mass in (("left", left_mass), ("right", right_mass)):
        references = EXPECTED_REFERENCES[side]
        variants.append(
            {
                "variant_id": f"993-k16-{side}-f1",
                "side": side,
                "oem_references": references,
                "pet_part_master_twin_ids": sorted(
                    {master for reference in references for master in links[reference]}
                ),
                "supplier_declared_complete_unit_envelope_mm": list(
                    EXPECTED_DIMENSIONS["envelope_mm"]
                ),
                "supplier_declared_complete_unit_mass_kg": mass,
                "mass_per_envelope_volume_kg_m3": round(
                    mass / envelope_volume_m3, 9
                ),
                "wheel_diameter_guides_mm": (
                    {
                        "compressor_inducer": EXPECTED_DIMENSIONS[
                            "compressor_inducer_mm"
                        ],
                        "compressor_exducer": EXPECTED_DIMENSIONS[
                            "compressor_exducer_mm"
                        ],
                        "turbine_inducer": EXPECTED_DIMENSIONS[
                            "turbine_inducer_mm"
                        ],
                        "turbine_exducer": EXPECTED_DIMENSIONS[
                            "turbine_exducer_mm"
                        ],
                    }
                    if side == "right"
                    else None
                ),
                "wheel_diameter_evidence": (
                    "right_turbo_supplier_catalogue_only"
                    if side == "right"
                    else "not_available_and_not_mirrored_from_right"
                ),
                "interface_coordinate_count": 0,
                "geometry_credit": "F1_complete_unit_envelope_and_separate_diameter_guides_only",
            }
        )

    return {
        "variants": variants,
        "envelope_volume_m3": envelope_volume_m3,
        "pair_declared_mass_kg": left_mass + right_mass,
        "pair_mass_difference_kg": left_mass - right_mass,
        "pair_mass_relative_difference": (left_mass - right_mass)
        / ((left_mass + right_mass) / 2.0),
        "combined_mass_per_combined_envelope_volume_kg_m3": (left_mass + right_mass)
        / (2.0 * envelope_volume_m3),
        "load_case": load_case,
        "material": material,
        "physicsnemo": physicsnemo,
        "cold_side": cold_side,
    }


def render_scad(data: dict[str, Any]) -> str:
    right = next(item for item in data["variants"] if item["side"] == "right")
    gauges = right["wheel_diameter_guides_mm"]
    assert isinstance(gauges, dict)
    lines = [
        "// PET-linked K16 F1 guides; not OEM, interface, aero or manufacturing geometry.",
        "// Boxes are complete-unit supplier envelopes; diameter coupons are spatially unrelated.",
        "$fn = 96;",
        "envelope_mm = [280.000000, 190.000000, 210.000000];",
        "coupon_thickness_mm = 2.000000; // visualization hypothesis only",
        "",
        "module complete_unit_envelope() {",
        "    cube(envelope_mm, center = true);",
        "}",
        "",
        "module diameter_coupon(diameter_mm) {",
        "    cylinder(h = coupon_thickness_mm, d = diameter_mm, center = true);",
        "}",
        "",
        "// Left and right display offsets are not vehicle coordinates.",
        "translate([-180.000000, 0, 0]) complete_unit_envelope();",
        "translate([180.000000, 0, 0]) complete_unit_envelope();",
        "",
        "// Right-side catalogue diameter coupons; never positioned inside either turbo.",
    ]
    for index, (name, value) in enumerate(sorted(gauges.items())):
        lines.extend(
            [
                f"// {name}: supplier-declared diameter",
                f"translate([{(-90.0 + index * 60.0):.6f}, -250.000000, 0]) ",
                f"    diameter_coupon({float(value):.6f});",
            ]
        )
    return "\n".join(lines) + "\n"


def render_variant_usd(variant: dict[str, Any], x_offset: float) -> str:
    references = ",".join(variant["oem_references"])
    masters = ",".join(variant["pet_part_master_twin_ids"])
    name = "K16LeftF1" if variant["side"] == "left" else "K16RightF1"
    extra = ""
    gauges = variant["wheel_diameter_guides_mm"]
    if isinstance(gauges, dict):
        gauge_prims = []
        for index, (key, value) in enumerate(sorted(gauges.items())):
            prim_name = "".join(part.capitalize() for part in key.split("_")) + "Gauge"
            gauge_prims.append(
                f'''            def Cylinder "{prim_name}"
            {{
                custom string dimensionalEvidence = "right_turbo_supplier_catalogue_only"
                uniform token axis = "Z"
                double height = 2.000000
                double radius = {float(value) / 2.0:.6f}
                uniform token purpose = "guide"
                double3 xformOp:translate = ({(-90.0 + index * 60.0):.6f}, 0, 0)
                uniform token[] xformOpOrder = ["xformOp:translate"]
            }}'''
            )
        extra = '''

        def Xform "UnpositionedRightWheelDiameterCoupons"
        {
            custom string placementStatus = "display_layout_only_not_internal_coordinates"
            double3 xformOp:translate = (0, -250.000000, 0)
            uniform token[] xformOpOrder = ["xformOp:translate"]
''' + "\n\n".join(gauge_prims) + '''
        }'''
    return f'''    def Xform "{name}" (
        kind = "component"
    )
    {{
        custom string fidelity = "F1_complete_unit_envelope_guide_unvalidated"
        custom string side = "{variant['side']}"
        custom string oemReferences = "{references}"
        custom string petPartMasterTwinIds = "{masters}"
        custom double declaredCompleteUnitMassKg = {variant['supplier_declared_complete_unit_mass_kg']:.6f}
        custom bool internalGeometryPresent = false
        custom bool interfaceGeometryPresent = false
        custom bool analysisGeometryAvailable = false
        custom bool materialAssigned = false
        custom bool simReadyValidated = false
        double3 xformOp:translate = ({x_offset:.6f}, 0, 0)
        uniform token[] xformOpOrder = ["xformOp:translate"]

        def Cube "CompleteUnitEnvelopeGuide"
        {{
            custom string dimensionalEvidence = "supplier_declared_complete_unit_envelope"
            double size = 1
            uniform token purpose = "guide"
            double3 xformOp:scale = (280.000000, 190.000000, 210.000000)
            uniform token[] xformOpOrder = ["xformOp:scale"]
        }}{extra}
    }}'''


def render_usd(data: dict[str, Any]) -> str:
    variants = [
        render_variant_usd(variant, offset)
        for variant, offset in zip(data["variants"], (-180.0, 180.0), strict=True)
    ]
    return '''#usda 1.0
(
    defaultPrim = "K16EnvelopeDiameterGuidesF1"
    metersPerUnit = 0.001
    upAxis = "Z"
)

def Xform "K16EnvelopeDiameterGuidesF1" (
    kind = "assembly"
)
{
    custom string status = "F1_guides_not_F2_F3_CFD_rotordynamics_or_SimReady"
    custom bool physicsAssigned = false
    custom bool materialAssigned = false
    custom bool simReadyValidated = false
''' + "\n\n".join(variants) + '''
}
'''


def source_entry(path: Path, role: str) -> dict[str, Any]:
    return {"path": relative(path), "sha256": sha256_file(path), "role": role}


def build_report(data: dict[str, Any], scad_text: str, usd_text: str) -> dict[str, Any]:
    variants = data["variants"]
    all_masters = sorted(
        {
            master
            for variant in variants
            for master in variant["pet_part_master_twin_ids"]
        }
    )
    cold_side = data["cold_side"]
    load_case = data["load_case"]
    physicsnemo = data["physicsnemo"]
    return {
        "$comment": (
            "Guides F1 K16 lies au PET et modele mathematique 0D fail-closed. "
            "Les coupons de diametre ne sont pas places dans les enveloppes."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "status": "F1_K16_envelope_and_diameter_guides_complete_zeroD_execution_blocked",
        "source_boundary": {
            "files": [
                source_entry(PART, "part_identity_claim_and_safety_boundary"),
                source_entry(FVD_SOURCE, "supplier_declared_complete_unit_envelopes_and_masses"),
                source_entry(INTERNAL_SOURCE, "right_side_catalogue_wheel_diameters_and_wastegate_data"),
                source_entry(CROSSWALK, "exact_OEM_identity_to_four_PET_master_links"),
                source_entry(ENGINE_FAMILIES, "structured_F1_K16_values"),
                source_entry(ENGINE_LOAD_CASES, "blocked_reference_solver_input_contract"),
                source_entry(ENGINE_MATERIALS, "unassigned_multimaterial_contract"),
                source_entry(PROGRAM_DEFINITION, "PhysicsNeMo_and_Omniverse_execution_policy"),
                source_entry(COLD_SIDE_PARAMETERS, "synthetic_solver_harness_boundary"),
            ],
            "third_party_geometry_redistributed": False,
            "llm_generated_dimensions_used": False,
            "independent_metrology_used": False,
        },
        "summary": {
            "assembly_variants": 2,
            "pet_linked_oem_references": 4,
            "pet_linked_part_masters": len(all_masters),
            "supplier_declared_envelopes": 2,
            "supplier_declared_masses": 2,
            "right_side_wheel_diameter_guides": 4,
            "left_side_wheel_diameter_guides": 0,
            "algebraic_consistency_checks": 5,
            "symbolic_zeroD_equation_contracts": 6,
            "evaluated_zeroD_operating_points": 0,
            "selected_interface_coordinates": 0,
            "qualified_material_decisions": 0,
            "reference_solver_results": 0,
            "physicsnemo_results": 0,
            "simready_assets": 0,
            "manufacturing_releases": 0,
        },
        "geometry_model": {
            "representation": "two_complete_unit_bounding_boxes_plus_four_unpositioned_right_side_diameter_coupons",
            "coupon_thickness_mm": 2.0,
            "coupon_thickness_status": "visualization_hypothesis",
            "display_offsets_status": "not_vehicle_or_internal_coordinates",
            "unknowns": [
                "all_mounting_and_fluid_interface_coordinates_sections_and_tolerances",
                "compressor_and_turbine_housing_internal_and_external_surfaces",
                "wheel_blade_profiles_bores_backfaces_and_axial_positions",
                "shaft_CHRA_bearing_seal_clearance_and_lubrication_geometry",
                "wastegate_flap_port_linkage_and_actuator_installation_geometry",
                "wall_thicknesses_surface_finishes_and_balance_features",
            ],
        },
        "variants": variants,
        "mass_and_dimension_consistency": {
            "status": "passed_arithmetic_only_not_geometry_or_material_validation",
            "checks": [
                {
                    "check_id": "equal_supplier_envelopes",
                    "result": "passed",
                    "value_mm": EXPECTED_DIMENSIONS["envelope_mm"],
                },
                {
                    "check_id": "pair_mass_sum",
                    "result": "passed",
                    "value_kg": round(data["pair_declared_mass_kg"], 9),
                },
                {
                    "check_id": "left_right_mass_difference",
                    "result": "passed",
                    "value_kg": round(data["pair_mass_difference_kg"], 9),
                    "relative_to_pair_mean": round(data["pair_mass_relative_difference"], 9),
                },
                {
                    "check_id": "compressor_diameter_order",
                    "result": "passed_supplier_values_are_numerically_ordered_only",
                    "inducer_to_exducer_ratio": round(
                        EXPECTED_DIMENSIONS["compressor_inducer_mm"]
                        / EXPECTED_DIMENSIONS["compressor_exducer_mm"],
                        9,
                    ),
                },
                {
                    "check_id": "turbine_diameter_order",
                    "result": "passed_supplier_values_are_numerically_ordered_only",
                    "exducer_to_inducer_ratio": round(
                        EXPECTED_DIMENSIONS["turbine_exducer_mm"]
                        / EXPECTED_DIMENSIONS["turbine_inducer_mm"],
                        9,
                    ),
                },
            ],
            "complete_unit_envelope_volume_m3": round(data["envelope_volume_m3"], 9),
            "combined_mass_per_combined_envelope_volume_kg_m3": round(
                data["combined_mass_per_combined_envelope_volume_kg_m3"], 9
            ),
            "interpretation": "packaging_and_data_consistency_only_multimaterial_void_assembly_prevents_density_inference",
        },
        "flow_interface_readiness": {
            "interface_topology_hypotheses": [
                "compressor_inlet_air",
                "compressor_outlet_charge_air",
                "turbine_inlet_exhaust_gas",
                "turbine_outlet_exhaust_gas",
                "oil_feed",
                "oil_drain",
                "wastegate_bypass",
                "actuator_pressure_or_control_reference",
            ],
            "topology_status": "LLM_assisted_engineering_hypotheses_for_review",
            "selected_interface_coordinate_count": 0,
            "selected_flow_area_count": 0,
            "selected_sealing_surface_count": 0,
            "supplier_declared_right_actuator_observations": {
                "wastegate_pressure_bar": 0.5,
                "rod_lift_mm": 4.2,
                "simulation_boundary_condition_status": "not_promoted_requires_definition_and_verification",
            },
        },
        "zeroD_model": {
            "status": "symbolic_contracts_only_no_operating_point_evaluated",
            "equations": [
                {
                    "id": "compressor_pressure_ratio",
                    "equation": "PR_c = p02 / p01",
                    "missing": ["p01_total_Pa", "p02_total_Pa"],
                },
                {
                    "id": "compressor_power",
                    "equation": "P_c = mdot_c * cp_c * T01 * (PR_c^((gamma_c-1)/gamma_c)-1) / eta_c",
                    "missing": ["mdot_c", "cp_c", "T01", "gamma_c", "eta_c", "PR_c"],
                },
                {
                    "id": "turbine_power",
                    "equation": "P_t = mdot_t * cp_t * T03 * eta_t * (1-PR_t^-((gamma_t-1)/gamma_t))",
                    "missing": ["mdot_t", "cp_t", "T03", "gamma_t", "eta_t", "PR_t"],
                },
                {
                    "id": "shaft_power_balance",
                    "equation": "P_t * eta_mech = P_c + P_bearing + dE_rotor_dt",
                    "missing": ["eta_mech", "P_bearing", "rotor_inertia", "rotor_speed_history"],
                },
                {
                    "id": "corrected_map_coordinates",
                    "equation": "mdot_corr = mdot*sqrt(T/Tref)/(P/Pref); N_corr = N/sqrt(T/Tref)",
                    "missing": ["mdot", "T", "P", "Tref", "Pref", "rotor_speed_N"],
                },
                {
                    "id": "wheel_tip_speed",
                    "equation": "U_tip = pi * D * N / 60",
                    "missing": ["verified_wheel_operating_diameter", "rotor_speed_rpm"],
                },
            ],
            "required_map_and_operating_inputs": list(load_case["required_inputs"]),
            "map_available": False,
            "operating_point_available": False,
            "shaft_balance_evaluated": False,
            "reference_solver_credit": False,
        },
        "cold_side_solver_harness": {
            "case_id": cold_side.get("case_id"),
            "status": "toolchain_smoke_not_K16_reference_CFD",
            "geometry_source": cold_side.get("geometry_source"),
            "synthetic_geometry": cold_side.get("geometry", {}),
            "synthetic_flow": cold_side.get("flow", {}),
            "values_promoted_to_K16_operating_point": 0,
            "reason": "stationary_equivalent_diffuser_without_wheel_CHRA_hot_side_or_K16_flowpath",
        },
        "material_and_manufacturing_route": {
            "assembly_material_status": data["material"].get("assignment_status"),
            "required_identification": data["material"].get("required_identification", []),
            "LLM_hypothesis_matrix": [
                {"subassembly": "compressor_housing", "candidate_family": "cast_aluminium_family", "status": "unsourced_hypothesis_not_selected"},
                {"subassembly": "turbine_housing", "candidate_family": "high_temperature_cast_iron_or_nickel_family", "status": "unsourced_hypothesis_not_selected"},
                {"subassembly": "compressor_wheel", "candidate_family": "forged_aluminium_or_titanium_family", "status": "unsourced_hypothesis_not_selected"},
                {"subassembly": "turbine_wheel", "candidate_family": "nickel_superalloy_family", "status": "unsourced_hypothesis_not_selected"},
                {"subassembly": "shaft_bearings_and_seals", "candidate_family": "specialist_turbomachinery_material_system", "status": "unsourced_hypothesis_not_selected"},
            ],
            "selected_material_count": 0,
            "selected_functional_manufacturing_route_count": 0,
            "whole_turbo_additive_or_CNC_release": "prohibited_pending_F3_reference_analysis_balance_containment_and_professional_review",
            "first_permitted_candidate_scope": "non_rotating_cold_side_adapter_after_F2_interfaces_and_reference_CFD",
        },
        "physicsnemo_discovery": {
            "canonical_repository": physicsnemo.get("canonical_repository"),
            "commit": physicsnemo.get("discovered_commit"),
            "discovered_on": physicsnemo.get("discovered_on"),
            "paths_verified_live_during_authoring": True,
            "local_revalidation_required_before_execution": True,
            "model_menu": [
                {
                    "model": "GeoTransolver",
                    "path": "physicsnemo/models/geotransolver",
                    "role": "candidate_irregular_mesh_field_surrogate_after_reference_CFD_dataset",
                    "selected": False,
                },
                {
                    "model": "Transolver",
                    "path": "physicsnemo/models/transolver",
                    "role": "candidate_irregular_mesh_field_surrogate_after_reference_CFD_dataset",
                    "selected": False,
                },
                {
                    "model": "MeshGraphNet",
                    "path": "physicsnemo/models/meshgraphnet",
                    "role": "exploratory_mesh_graph_candidate_requires_K16_specific_compressible_formulation",
                    "selected": False,
                },
                {
                    "model": "DoMINO",
                    "path": "physicsnemo/models/domino",
                    "role": "not_selected_external_aerodynamics_example_is_not_internal_K16_validation",
                    "selected": False,
                },
            ],
            "verified_datapipes": [
                "physicsnemo/datapipes/cae/DoMINODataPipe",
                "physicsnemo/datapipes/cae/TransolverDataPipe",
            ],
            "verified_examples": [
                "examples/cfd/external_aerodynamics/domino",
                "examples/cfd/external_aerodynamics/transformer_models",
                "examples/cfd/stokes_mgn",
            ],
            "execution_enabled": False,
            "eligibility_gate": "converged_mesh_independent_K16_reference_CFD_dataset_with_held_out_cases_and_acceptance_thresholds",
        },
        "omniverse_handoff": {
            "openusd_source_authoring": "completed_as_guides",
            "property_assignment_intent": "run",
            "content_agents_preflight": "blocked_by_recorded_program_preflight",
            "material_and_physics_assignment": "not_run",
            "nvidia_asset_validator": "not_run_preflight_blocked",
            "simready_foundation": "not_run_preflight_blocked",
            "simready_validated": False,
        },
        "assets": {
            "editable_scad": relative(SCAD_OUTPUT),
            "editable_scad_sha256": sha256_bytes(scad_text.encode("utf-8")),
            "openusd_guide": relative(USD_OUTPUT),
            "openusd_guide_sha256": sha256_bytes(usd_text.encode("utf-8")),
            "openusd_variant_prim_count": 2,
            "openusd_guide_primitive_count": 6,
            "openusd_physics_schema_count": 0,
            "openusd_material_binding_count": 0,
        },
        "claim_boundary": {
            "is_complete_OEM_geometry": False,
            "is_F2_interface_geometry": False,
            "is_F3_analysis_geometry": False,
            "is_dimensionally_accurate_part_shape": False,
            "is_fitment_validated": False,
            "is_qualified_material_selection": False,
            "is_evaluated_operating_point": False,
            "is_reference_CFD_or_rotordynamics_result": False,
            "is_physicsnemo_result": False,
            "is_simready_validated": False,
            "is_manufacturing_or_engine_release": False,
        },
        "next_gate": "resolve_PET_configuration_then_source_or_reconstruct_F2_interfaces_and_F3_internal_flowpath_before_reference_CFD",
    }


def validate(data: dict[str, Any], scad_text: str, usd_text: str, report: dict[str, Any]) -> None:
    if report.get("status") != "F1_K16_envelope_and_diameter_guides_complete_zeroD_execution_blocked":
        raise ContractError("status")
    expected_summary = {
        "assembly_variants": 2,
        "pet_linked_oem_references": 4,
        "pet_linked_part_masters": 4,
        "supplier_declared_envelopes": 2,
        "supplier_declared_masses": 2,
        "right_side_wheel_diameter_guides": 4,
        "left_side_wheel_diameter_guides": 0,
        "algebraic_consistency_checks": 5,
        "symbolic_zeroD_equation_contracts": 6,
        "evaluated_zeroD_operating_points": 0,
        "selected_interface_coordinates": 0,
        "qualified_material_decisions": 0,
        "reference_solver_results": 0,
        "physicsnemo_results": 0,
        "simready_assets": 0,
        "manufacturing_releases": 0,
    }
    summary = report.get("summary", {})
    if any(summary.get(field) != value for field, value in expected_summary.items()):
        raise ContractError("summary")
    if len(data.get("variants", [])) != 2 or usd_text.count('kind = "component"') != 2:
        raise ContractError("variant_prims")
    if usd_text.count('purpose = "guide"') != 6:
        raise ContractError("guide_primitives")
    if usd_text.count("DiameterCoupons") != 1:
        raise ContractError("diameter_coupon_group")
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
        raise ContractError("zeroD_reference_credit")
    if report.get("physicsnemo_discovery", {}).get("execution_enabled") is not False:
        raise ContractError("physicsnemo_execution")
    if report.get("omniverse_handoff", {}).get("simready_validated") is not False:
        raise ContractError("simready_overclaim")
    if report.get("material_and_manufacturing_route", {}).get("selected_material_count") != 0:
        raise ContractError("material_overclaim")
    if any(value is not False for value in report.get("claim_boundary", {}).values()):
        raise ContractError("claim_boundary")
    assets = report.get("assets", {})
    if assets.get("editable_scad_sha256") != sha256_bytes(scad_text.encode("utf-8")):
        raise ContractError("scad_digest")
    if assets.get("openusd_guide_sha256") != sha256_bytes(usd_text.encode("utf-8")):
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
        checked = load_json(REPORT)
        validate(data, SCAD_OUTPUT.read_text(), USD_OUTPUT.read_text(), checked)
        print(f"current {relative(REPORT)}: 2 K16 F1 variants, 0 operating points")
        return 0
    except (ContractError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
