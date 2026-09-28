#!/usr/bin/env python3
"""Generate fail-closed engineering contracts for the catalogue part twins.

This is an input-readiness stage, not a structural solver. It derives only
quantities supported by catalogue data, selects plausible manufacturing routes,
and records the measurements, baseline CAE results and physical correlation
required before PhysicsNeMo can be trained as a surrogate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TWIN_ROOT = ROOT / "twins" / "catalogue-parts"
INDEX = TWIN_ROOT / "index.json"
OUTPUT = TWIN_ROOT / "engineering-f0.json"
ENGINE_CARRIER_SCREENING = TWIN_ROOT / "engine-carrier-material-screening-f1.json"
STEEL_SCREENING_DENSITY_KG_M3 = 7850.0


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parameter_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["parameter_id"]: item
        for item in record["physical"]["size_parameters"]
        if isinstance(item, dict) and isinstance(item.get("parameter_id"), str)
    }


def blocked_tests() -> dict[str, dict[str, str]]:
    return {
        "identity_and_provenance": {
            "status": "pass_documentary",
            "claim": "identity_and_application_only",
        },
        "dimensional_interface_readiness": {
            "status": "blocked_missing_measured_interfaces_and_tolerances",
            "claim": "not_tested",
        },
        "mesh_readiness": {
            "status": "blocked_F1_proxy_is_not_analysis_geometry",
            "claim": "not_tested",
        },
        "reference_cae": {
            "status": "blocked_not_run",
            "claim": "no_FEA_result",
        },
        "physicsnemo": {
            "status": "blocked_not_run",
            "claim": "no_surrogate_result",
        },
        "physical_correlation": {
            "status": "blocked_no_test_article_or_rig",
            "claim": "not_tested",
        },
        "manufacturing_release": {
            "status": "blocked_pending_professional_engineering_and_validation",
            "claim": "not_released",
        },
    }


def structural_load_cases(prefix: str) -> list[dict[str, Any]]:
    definitions = [
        ("RADIAL", "radial_static_and_fatigue"),
        ("CORNERING", "lateral_bending_and_fatigue"),
        ("TORQUE", "drive_and_braking_torque"),
        ("IMPACT", "road_impact_transient"),
    ]
    return [
        {
            "load_case_id": f"LC-{prefix}-{suffix}",
            "kind": kind,
            "baseline_solver": "CalculiX_after_complete_geometry_and_inputs",
            "status": "blocked_missing_loads_geometry_material_and_acceptance_criteria",
        }
        for suffix, kind in definitions
    ]


def wheel_contract(twin: dict[str, Any]) -> dict[str, Any]:
    source_path = ROOT / twin["subject"]["record"]
    component = load_json(source_path)
    parameters = parameter_map(component)
    width_mm = float(parameters["RIM_WIDTH"]["value"]) * 25.4
    offset_mm = float(parameters["OFFSET"]["value"])
    inboard_bead_seat_mm = width_mm / 2.0 + offset_mm
    outboard_bead_seat_mm = width_mm / 2.0 - offset_mm
    material = component["physical"]["material"]

    return {
        "twin_id": twin["twin_id"],
        "subject": twin["subject"],
        "engineering_status": "blocked_input_acquisition",
        "current_fidelity": twin["fidelity"],
        "minimum_reference_cae_fidelity": "F3_measured_interfaces_and_complete_load_bearing_surfaces",
        "safety_class": "wheel_safety_critical",
        "known_inputs": {
            "parameters": parameters,
            "mass": component["physical"]["mass"],
            "material": material,
        },
        "screening_metrics": {
            "nominal_bead_seat_width_mm": round(width_mm, 6),
            "mounting_plane_to_inboard_bead_seat_mm": round(inboard_bead_seat_mm, 6),
            "mounting_plane_to_outboard_bead_seat_mm": round(outboard_bead_seat_mm, 6),
            "interpretation": (
                "nominal bead-seat distances only; flange thickness, tyre envelope and body clearance are excluded"
            ),
        },
        "reverse_engineering": {
            "status": "blocked_missing_complete_geometry",
            "required_acquisitions": [
                "licensed_full_surface_scan_or_owner_measurement_set",
                "hub_mounting_face_and_fastener_seat_geometry",
                "barrel_flange_and_spoke_thickness_map",
                "dimensional_tolerances_and_runout",
                "material_grade_heat_treatment_and_forging_state",
                "non_destructive_inspection_baseline",
            ],
        },
        "manufacturing": {
            "original_process": material["process"],
            "functional_routes": {
                "machined_wheel": "blocked_not_demonstrated_equivalent_to_forged_reference",
                "metal_additive_wheel": "blocked_safety_critical_and_unqualified",
                "polymer_additive_proxy": "fit_and_clearance_only_after_complete_geometry",
            },
            "selected_functional_route": None,
        },
        "simulation": {
            "analysis_geometry": "unavailable",
            "reference_solver": "CalculiX",
            "load_cases": structural_load_cases(twin["twin_id"].removeprefix("TWIN-")),
            "required_inputs": [
                "vehicle_corner_mass_and_dynamic_amplification",
                "tyre_load_and_pressure_envelopes",
                "hub_bolt_preload_and_contact_definition",
                "qualified_material_curve_and_fatigue_data",
                "mesh_convergence_plan",
                "acceptance_criteria_and_regulatory_test_plan",
            ],
        },
        "digital_twin_tests": blocked_tests(),
    }


def carrier_contract(twin: dict[str, Any]) -> dict[str, Any]:
    dimensions_mm = [float(value) for value in twin["geometry"]["parameters"]["bounding_box_mm"]]
    mass_kg = float(twin["physical"]["mass"]["value_kg"])
    envelope_volume_m3 = dimensions_mm[0] * dimensions_mm[1] * dimensions_mm[2] * 1e-9
    apparent_solid_fraction = mass_kg / (envelope_volume_m3 * STEEL_SCREENING_DENSITY_KG_M3)
    load_cases = [
        ("VERTICAL", "engine_mass_vertical_static_and_road_amplification"),
        ("TORQUE", "powertrain_reaction_torque"),
        ("LONGITUDINAL", "acceleration_and_braking_inertia"),
        ("LATERAL", "cornering_inertia"),
        ("MODAL", "modal_and_engine_order_separation"),
        ("FATIGUE", "combined_variable_amplitude_fatigue"),
    ]
    material_screening = load_json(ENGINE_CARRIER_SCREENING)
    if material_screening.get("subject", {}).get("part_id") != "993-ENG-CARRIER-0001":
        raise ValueError("engine carrier material screening subject mismatch")
    if material_screening.get("screening_decision", {}).get("component_credit") is not False:
        raise ValueError("engine carrier material screening overclaims component credit")

    return {
        "twin_id": twin["twin_id"],
        "subject": twin["subject"],
        "engineering_status": "blocked_input_acquisition",
        "current_fidelity": twin["fidelity"],
        "minimum_reference_cae_fidelity": "F3_measured_interfaces_and_load_bearing_geometry",
        "safety_class": "powertrain_mounting_safety_critical",
        "known_inputs": {
            "declared_bounding_box_mm": dimensions_mm,
            "declared_mass_kg": mass_kg,
            "material_family": twin["physical"]["material"]["family"],
            "material_status": twin["physical"]["material_status"],
        },
        "screening_metrics": {
            "declared_envelope_volume_m3": round(envelope_volume_m3, 9),
            "apparent_solid_fraction_if_steel": round(apparent_solid_fraction, 6),
            "interpretation": (
                "catalogue consistency check only; the seller envelope is not a measured solid or analysis geometry"
            ),
        },
        "reverse_engineering": {
            "status": "blocked_missing_complete_geometry",
            "measurement_plan": "parts/993-eng-carrier-0001/evidence/measurement-plan.md",
            "load_case_plan": "parts/993-eng-carrier-0001/evidence/load-cases.md",
            "required_acquisitions": [
                "measured_mounting_interface_coordinates_and_hole_geometries",
                "complete_curved_body_and_boss_geometry",
                "thickness_map_flatness_and_as_found_damage",
                "identified_material_grade_heat_treatment_and_coating",
                "engine_and_transmission_support_load_distribution",
                "mount_stiffness_preload_contacts_and_fastener_data",
            ],
        },
        "manufacturing": {
            "functional_routes": {
                "machined_wrought_steel": "concept_candidate_pending_geometry_loads_grade_and_fatigue_review",
                "cast_or_forged_steel": "concept_candidate_pending_original_process_identification",
                "metal_additive": "screened_out_for_current_600_mm_safety_critical_concept",
                "polymer_additive_proxy": "fit_and_fixture_check_only_after_complete_geometry",
            },
            "selected_functional_route": None,
        },
        "virtual_material_screening": {
            "record": relative(ENGINE_CARRIER_SCREENING),
            "record_sha256": sha256_file(ENGINE_CARRIER_SCREENING),
            "status": material_screening["status"],
            "analytic_results": material_screening["analytic_results"],
            "screening_decision": material_screening["screening_decision"],
            "component_credit": False,
        },
        "simulation": {
            "analysis_geometry": "unavailable",
            "reference_solver": "CalculiX",
            "load_cases": [
                {
                    "load_case_id": f"LC-993-ENGINE-CARRIER-{suffix}",
                    "kind": kind,
                    "baseline_solver": "CalculiX_after_complete_geometry_and_inputs",
                    "status": "blocked_missing_loads_geometry_material_and_acceptance_criteria",
                }
                for suffix, kind in load_cases
            ],
            "required_inputs": [
                "measured_engine_and_transmission_masses_and_centres_of_gravity",
                "measured_mount_reaction_distribution",
                "powertrain_torque_envelope_and_duty_cycle",
                "road_load_acceleration_spectrum",
                "qualified_material_curve_and_fatigue_data",
                "fastener_preload_contact_and_mount_stiffness",
                "mesh_convergence_plan",
                "stress_displacement_modal_and_fatigue_acceptance_criteria",
            ],
        },
        "digital_twin_tests": blocked_tests(),
    }


def generic_domain_ids(identifier: str) -> list[str]:
    if "TURBOCHARGER" in identifier:
        return ["rotordynamics", "structural", "thermal_fluid"]
    if "PRESSURE-HOSE" in identifier:
        return ["network_flow", "structural", "thermal_fluid"]
    if "INTERCOOLER" in identifier:
        if "TEMPERATURE-SENSOR" in identifier:
            return ["controls", "electrical_network", "thermal_fluid"]
        if "BRACKET" in identifier or "AIR-DUCT" in identifier:
            return ["package_interfaces", "structural", "thermal_fluid"]
        return ["network_flow", "structural", "thermal_fluid"]
    if "HEAT-SHIELD" in identifier:
        return ["package_interfaces", "structural", "thermal_fluid"]
    return ["package_interfaces"]


def material_system_hypothesis(identifier: str) -> str:
    if "TURBOCHARGER" in identifier:
        return "multimaterial_high_temperature_turbomachinery_assembly"
    if "PRESSURE-HOSE" in identifier:
        return "reinforced_high_temperature_elastomer_hose_system"
    if "HEAT-SHIELD" in identifier:
        return "thin_gauge_high_temperature_metal_sheet_system"
    if "AIR-DUCT" in identifier:
        return "temperature_resistant_polymer_or_composite_duct"
    if "BRACKET" in identifier:
        return "formed_or_machined_metal_bracket_system"
    if "TEMPERATURE-SENSOR" in identifier:
        return "multimaterial_temperature_sensor_assembly"
    if "INTERCOOLER" in identifier:
        return "brazed_aluminium_heat_exchanger_system"
    return "function_specific_material_system_to_identify"


def generic_reference_contract(twin: dict[str, Any]) -> dict[str, Any]:
    identifier = twin["subject"]["id"]
    dimensions_mm = [
        float(value) for value in twin["geometry"]["parameters"]["bounding_box_mm"]
    ]
    mass_record = twin["physical"]["mass"]
    mass_kg = mass_record.get("value_kg")
    envelope_volume_m3 = dimensions_mm[0] * dimensions_mm[1] * dimensions_mm[2] * 1e-9
    envelope_density = (
        float(mass_kg) / envelope_volume_m3
        if isinstance(mass_kg, (int, float)) and envelope_volume_m3 > 0
        else None
    )
    part_record = twin["subject"].get("part_record")
    safety_class = "not_assessed"
    if isinstance(part_record, str):
        part = load_json(ROOT / part_record)
        safety_class = part.get("classification", {}).get("safety_class", safety_class)
    return {
        "twin_id": twin["twin_id"],
        "subject": twin["subject"],
        "engineering_status": "blocked_input_acquisition",
        "current_fidelity": twin["fidelity"],
        "minimum_reference_cae_fidelity": "F2_interfaces_then_domain_specific_F3_geometry",
        "safety_class": safety_class,
        "known_inputs": {
            "declared_bounding_box_mm": dimensions_mm,
            "declared_mass_kg": mass_kg,
            "material_family": twin["physical"]["material"].get("family"),
            "material_status": twin["physical"]["material_status"],
        },
        "screening_metrics": {
            "declared_envelope_volume_m3": round(envelope_volume_m3, 9),
            "mass_per_envelope_volume_kg_m3": (
                round(envelope_density, 6) if envelope_density is not None else None
            ),
            "interpretation": (
                "packaging consistency metric only; voids and multimaterial construction prevent material inference"
            ),
        },
        "reverse_engineering": {
            "status": "blocked_missing_complete_geometry_material_and_interfaces",
            "required_acquisitions": [
                "licensed_editable_surface_or_parametric_reconstruction",
                "interface_coordinates_sealing_surfaces_and_fastener_geometry",
                "wall_thickness_internal_passages_and_tolerances",
                "operating_temperature_pressure_load_and_environment_envelopes",
                "material_system_grades_processes_and_supplier_evidence",
                "acceptance_criteria_and_inspection_plan",
            ],
        },
        "materials": {
            "selected_material_system": None,
            "screening_hypothesis": material_system_hypothesis(identifier),
            "hypothesis_status": "unqualified_requires_source_environment_and_failure_mode_review",
            "single_material_assumption_allowed": False,
        },
        "manufacturing": {
            "selected_functional_route": None,
            "candidate_routes": {
                "original_equivalent_process": "blocked_original_process_not_identified",
                "machined_reconstruction": "blocked_geometry_material_and_validation_missing",
                "additive_functional_reconstruction": "blocked_geometry_material_process_and_validation_missing",
                "additive_proxy": "packaging_only_after_interface_geometry_is_available",
            },
        },
        "simulation": {
            "analysis_geometry": "unavailable",
            "domain_ids": generic_domain_ids(identifier),
            "reference_solver": "domain_specific_reference_solver_from_vehicle_program",
            "load_cases": [],
            "required_inputs": [
                "complete_analysis_geometry_and_mesh_plan",
                "qualified_material_and_process_properties",
                "loads_boundary_conditions_contacts_and_duty_cycle",
                "analytical_checks_and_acceptance_criteria",
                "reference_solver_convergence_and_balance_evidence",
            ],
        },
        "digital_twin_tests": blocked_tests(),
    }


def build_contract() -> dict[str, Any]:
    index = load_json(INDEX)
    parts: list[dict[str, Any]] = []
    for twin in index["twins"]:
        if twin["representation"] == "annular_wheel_interface_proxy":
            parts.append(wheel_contract(twin))
        elif twin["subject"].get("part_id") == "993-ENG-CARRIER-0001":
            parts.append(carrier_contract(twin))
        elif twin["representation"] == "declared_bounding_envelope":
            parts.append(generic_reference_contract(twin))
        else:
            raise ValueError(f"unsupported twin: {twin['twin_id']}")

    return {
        "$comment": (
            "Contrats F0 d'ingenierie inverse et de simulation. Les controles courants testent la disponibilite "
            "des entrees ; ils ne constituent ni FEA, ni essai physique, ni validation de fabrication."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_twin_index": relative(INDEX),
        "engineering_level": "F0_input_readiness",
        "summary": {
            "parts": len(parts),
            "ready_for_reference_cae": sum(
                part["digital_twin_tests"]["reference_cae"]["status"] == "pass" for part in parts
            ),
            "ready_for_physicsnemo": 0,
            "released_for_functional_manufacture": 0,
        },
        "solver_policy": {
            "reference_structural_solver": "CalculiX",
            "reference_solver_required_before_surrogate": True,
            "proxy_geometry_must_not_be_meshed_for_strength_claims": True,
        },
        "physicsnemo_policy": {
            "runtime_target": "nvidia-physicsnemo_2.2.0",
            "execution_enabled": False,
            "role": "surrogate_only_after_validated_CAE_baseline_and_physical_correlation",
            "candidate_architecture": "GeoTransolver_one_shot_pilot_for_unstructured_CAE_meshes",
            "candidate_architectures": [
                "GeoTransolver",
                "MeshGraphNet",
                "Transolver",
                "FIGConvUNet",
            ],
            "candidate_status": "pilot_selected_for_future_dataset_design_not_training",
            "discovery_contract": "twins/catalogue-parts/physicsnemo-structural-f0.json",
            "required_before_enablement": [
                "full_editable_geometry_with_measured_interfaces",
                "qualified_material_properties_and_manufacturing_state",
                "validated_CalculiX_cases_with_mesh_convergence",
                "physical_test_correlation",
                "parameterized_CAE_training_domain",
                "separate_train_validation_and_held_out_test_sets",
                "documented_field_and_scalar_error_thresholds",
                "uncertainty_and_out_of_domain_rejection",
            ],
            "planned_inputs": [
                "mesh_coordinates_and_connectivity",
                "boundary_condition_labels",
                "material_and_process_features",
                "loads_preloads_and_contact_parameters",
            ],
            "planned_outputs": [
                "nodal_displacement",
                "stress_and_strain_fields",
                "modal_or_fatigue_scalars_when_present_in_reference_data",
            ],
            "prohibited_claims": [
                "PhysicsNeMo_prediction_as_reference_solution",
                "training_on_F1_documentary_proxies",
                "manufacturing_release_without_physical_validation",
            ],
        },
        "parts": parts,
    }


def run(write: bool) -> int:
    content = json.dumps(build_contract(), ensure_ascii=False, indent=2) + "\n"
    if write:
        OUTPUT.write_text(content, encoding="utf-8")
        print(f"wrote {relative(OUTPUT)}")
        return 0
    if not OUTPUT.is_file():
        print(f"missing generated file: {relative(OUTPUT)}", file=sys.stderr)
        return 1
    if OUTPUT.read_text(encoding="utf-8") != content:
        print(f"stale generated file: {relative(OUTPUT)}", file=sys.stderr)
        return 1
    print("catalogue engineering: 18 fail-closed F0 contracts are current")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write the generated engineering contract")
    mode.add_argument("--check", action="store_true", help="verify the checked-in contract is current")
    args = parser.parse_args(argv)
    return run(write=args.write)


if __name__ == "__main__":
    raise SystemExit(main())
