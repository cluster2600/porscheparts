#!/usr/bin/env python3
"""Build the fail-closed F49 material and LPBF qualification contract.

F49 performs no CAD or mesh operation.  It binds manufacturer and standards
records, screens the minimum requested build envelope, and keeps every physical
qualification gate closed until route-specific coupons and inspections exist.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any


CONTRACT_PATH = Path("twins/reference-917-engine/material-lpbf-qualification-f49.json")
EVIDENCE_DIR = Path("twins/reference-917-engine/evidence/f49-material-lpbf")
COMPARISON_PATH = EVIDENCE_DIR / "material-comparison.csv"
MANIFEST_PATH = EVIDENCE_DIR / "manifest.json"
F45_PATH = Path("twins/reference-917-engine/valvetrain-material-screen-f45.json")
F47_PATH = Path("twins/reference-917-engine/cae-load-transfer-f47.json")
F47_INTERNAL_PATH = Path("twins/reference-917-engine/internal-brep-contract-f47.json")
F47_SUMMARY_PATH = Path("twins/reference-917-engine/evidence/f47-cae-loads/summary.json")
SCRIPT_PATH = Path("twins/reference-917-engine/source/build_material_lpbf_qualification_f49.py")

SOURCE_PATHS = (
    Path("catalog/sources/src-constellium-aheadd-cp1-product-sheet.json"),
    Path("catalog/sources/src-velo3d-cp1-material-datasheet.json"),
    Path("catalog/sources/src-pwr-velo3d-cp1-production.json"),
    Path("catalog/sources/src-velo3d-sapphire-product-brief.json"),
    Path("catalog/sources/src-sae-ams7074-cp1.json"),
    Path("catalog/sources/src-eckart-a20x-lpbf.json"),
    Path("catalog/sources/src-eos-alsi10mg-material-data.json"),
    Path("catalog/sources/src-eos-alf357-material-data.json"),
    Path("catalog/sources/src-sae-ams4132j-2618-t61.json"),
    Path("catalog/sources/src-nasa-2618-elevated-temperature.json"),
    Path("catalog/sources/src-iso-astm-52920-2023.json"),
    Path("catalog/sources/src-iso-astm-ts-52930-2021.json"),
    Path("catalog/sources/src-iso-astm-52928-2024.json"),
    Path("catalog/sources/src-iso-astm-52929-2025.json"),
    Path("catalog/sources/src-iso-astm-52953-2025.json"),
    Path("catalog/sources/src-iso-15708-ct-2025.json"),
    Path("catalog/sources/src-astm-e21-20.json"),
    Path("catalog/sources/src-astm-e8-e8m-25.json"),
    Path("catalog/sources/src-astm-e1461-13r22.json"),
    Path("catalog/sources/src-astm-e1417-e1417m-21e1.json"),
    Path("catalog/sources/src-astm-f3318-18.json"),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def source_bindings(root: Path) -> dict[str, dict[str, str]]:
    bindings: dict[str, dict[str, str]] = {}
    for relative in SOURCE_PATHS:
        record = json.loads((root / relative).read_text(encoding="utf-8"))
        bindings[record["source_id"]] = {
            "path": relative.as_posix(),
            "sha256": sha256(root / relative),
            "publisher": record["publisher"],
            "url": record["url"],
        }
    return dict(sorted(bindings.items()))


def orientation_screen() -> dict[str, Any]:
    length, width, height = 225.0, 120.0, 98.0
    roll_deg = 35.0
    roll = math.radians(roll_deg)
    projected_width = width * math.cos(roll) + height * math.sin(roll)
    projected_height = width * math.sin(roll) + height * math.cos(roll)
    required_diameter = math.hypot(length, projected_width)
    machine_diameter = 315.0
    machine_height = 400.0
    return {
        "screening_input_envelope_mm": [length, width, height],
        "input_classification": "minimum_requested_machine_fit_envelope_not_a_CAD_definition",
        "candidate_orientation": {
            "long_axis_yaw_deg": 0.0,
            "roll_about_long_axis_deg": roll_deg,
            "reason": "incline_air_cooling_features_and_avoid_a_flat_stack_screen_only",
            "supplier_flow_project_selected": False,
        },
        "axis_aligned_envelope_after_roll_mm": [
            round(length, 6),
            round(projected_width, 6),
            round(projected_height, 6),
        ],
        "required_platform_diameter_from_bounding_box_mm": round(required_diameter, 6),
        "published_machine_volume": {
            "shape": "circular_platform",
            "diameter_mm": machine_diameter,
            "height_mm": machine_height,
        },
        "diametral_clearance_before_stock_supports_and_supplier_margin_mm": round(
            machine_diameter - required_diameter, 6
        ),
        "height_clearance_before_plate_and_supports_mm": round(
            machine_height - projected_height, 6
        ),
        "bare_envelope_screen_pass": required_diameter <= machine_diameter
        and projected_height <= machine_height,
        "support_extent_mm": None,
        "supplier_edge_margin_mm": None,
        "recoater_clearance_verified": False,
        "final_build_fit_verified": False,
    }


def material_candidates() -> list[dict[str, Any]]:
    return [
        {
            "id": "Aheadd_CP1_400C_4h",
            "manufacturing_route": "LPBF_Velo3D_Sapphire_50um_then_400C_4h",
            "powder_specification": "SAE_AMS7074_issued_2025",
            "density_kg_m3": 2670.0,
            "room_temperature": {
                "yield_mpa": 323.0,
                "uts_mpa": 342.0,
                "elongation_percent": 12.8,
                "thermal_conductivity_w_mk": 187.0,
                "source": "SRC-CONSTELLIUM-AHEADD-CP1-PRODUCT-SHEET",
            },
            "machine_specific_50um_screening_minimum": {
                "yield_mpa": 297.0,
                "uts_mpa": 331.0,
                "elongation_percent": 13.9,
                "vertical_machined_specimens_n": 56,
                "source": "SRC-VELO3D-CP1-MATERIAL-DATASHEET",
                "design_allowable": False,
            },
            "public_hot_tensile_points": [],
            "supplier_thermal_stability_scope_c": [250.0, 300.0],
            "stability_statement_is_strength_curve": False,
            "complete_hot_card": False,
            "screening_rank": 1,
            "screening_role": "primary_coupon_candidate_for_heat_rejection_and_thermal_stability",
            "blocking_gaps": [
                "yield_uts_elongation_vs_temperature_for_exact_route",
                "thermal_conductivity_cp_density_cte_E_plasticity_vs_temperature",
                "LCF_HCF_TMF_creep_and_stress_relaxation",
                "defect_surface_and_orientation_allowables",
                "multiple_build_and_machine_repeatability",
            ],
        },
        {
            "id": "A20X_A205_LPBF_T7",
            "manufacturing_route": "LPBF_then_proprietary_ECKART_T7",
            "powder_specification": "SAE_AMS7033_issued_2021",
            "density_kg_m3": 2850.0,
            "room_temperature": {
                "yield_mpa": 445.0,
                "uts_mpa": 511.0,
                "elongation_percent": 11.0,
                "thermal_conductivity_w_mk": None,
                "source": "SRC-ECKART-A20X-LPBF",
            },
            "public_hot_tensile_points": [
                {"temperature_c": 100.0, "yield_mpa": 375.0, "uts_mpa": 423.0, "elongation_percent": 10.0},
                {"temperature_c": 150.0, "yield_mpa": 354.0, "uts_mpa": 369.0, "elongation_percent": 20.0},
                {"temperature_c": 200.0, "yield_mpa": 311.0, "uts_mpa": 331.0, "elongation_percent": 15.0},
                {"temperature_c": 250.0, "yield_mpa": 215.0, "uts_mpa": 224.0, "elongation_percent": 12.0},
            ],
            "supplier_thermal_stability_scope_c": [20.0, 190.0],
            "point_at_250C_extends_supplier_service_scope": False,
            "complete_hot_card": False,
            "screening_rank": 2,
            "screening_role": "alternate_coupon_candidate_if_CP1_hot_strength_is_insufficient",
            "blocking_gaps": [
                "thermal_conductivity_vs_temperature",
                "public_heat_treatment_recipe_for_purchased_route",
                "E_cte_plasticity_fatigue_TMF_creep_vs_temperature",
                "machine_specific_process_and_repeatability",
            ],
        },
        {
            "id": "EOS_AlSi10Mg_T6",
            "manufacturing_route": "EOS_M290_30um_T6_reference_process",
            "powder_specification": "ASTM_F3318_18_finished_part_baseline",
            "density_kg_m3": 2660.0,
            "room_temperature": {
                "yield_mpa": 245.0,
                "uts_mpa": 460.0,
                "elongation_percent": 5.0,
                "thermal_conductivity_w_mk": {"horizontal": 155.0, "vertical": 165.0},
                "source": "SRC-EOS-ALSI10MG-MATERIAL-DATA",
            },
            "public_hot_tensile_points": [],
            "supplier_thermal_stability_scope_c": None,
            "complete_hot_card": False,
            "screening_rank": 3,
            "screening_role": "mature_process_control_not_preferred_for_turbo_head",
            "blocking_gaps": [
                "hot_mechanical_card",
                "fatigue_TMF_creep_and_stress_relaxation_for_final_route",
                "T6_porosity_and_leak_tightness_demonstration",
            ],
        },
        {
            "id": "EOS_AlF357_T6_like",
            "manufacturing_route": "EOS_M290_30um_T6_like_reference_process",
            "powder_specification": "SAE_AMS4289_chemistry_listed_by_EOS",
            "density_kg_m3": None,
            "room_temperature": {
                "yield_mpa": 265.0,
                "uts_mpa": 330.0,
                "elongation_percent": 11.5,
                "thermal_conductivity_w_mk": 150.0,
                "source": "SRC-EOS-ALF357-MATERIAL-DATA",
            },
            "public_hot_tensile_points": [],
            "supplier_thermal_stability_scope_c": None,
            "complete_hot_card": False,
            "screening_rank": 4,
            "screening_role": "AlSi7Mg_family_process_control",
            "blocking_gaps": [
                "hot_mechanical_and_thermal_card",
                "fatigue_TMF_creep_and_stress_relaxation_for_final_route",
                "route_specific_density_and_defect_allowables",
            ],
        },
        {
            "id": "2618_T61_wrought_machined_reference",
            "manufacturing_route": "forged_or_rolled_stock_then_machined_not_LPBF",
            "powder_specification": None,
            "product_specification": "SAE_AMS4132J_2026_for_2618_T61_forgings",
            "density_kg_m3": 2760.0,
            "room_temperature": {
                "yield_mpa": None,
                "uts_mpa": None,
                "elongation_percent": None,
                "thermal_conductivity_w_mk": None,
                "source": "SRC-SAE-AMS4132J-2618-T61",
            },
            "public_hot_tensile_points": [
                {
                    "temperature_c": 204.0,
                    "yield_mpa_approximate": 269.0,
                    "exposure_h": 100.0,
                    "product_form": "2618_T6511_extrusion",
                },
                {
                    "temperature_c": 260.0,
                    "yield_mpa_approximate": 172.0,
                    "exposure_h": 100.0,
                    "product_form": "2618_T6511_extrusion",
                },
            ],
            "hot_points_source": "SRC-NASA-2618-ELEVATED-TEMPERATURE",
            "digitized_graph_values_are_design_allowables": False,
            "complete_hot_card": False,
            "screening_rank": 5,
            "screening_role": "machined_wrought_reference_only",
            "blocking_gaps": [
                "same_product_form_and_temper_comparison",
                "current_controlled_hot_allowables",
                "thermal_and_fatigue_card_for_head_duty",
            ],
        },
    ]


def build_contract(root: Path) -> dict[str, Any]:
    f47_summary = json.loads((root / F47_SUMMARY_PATH).read_text(encoding="utf-8"))
    f47_metrics = f47_summary["metrics"]["architectures"]
    peak_gas_temperature = max(
        f47_metrics[architecture]["temperature_k"]["cross_model"]["maximum"]
        for architecture in ("2v", "4v")
    )
    peak_pressure = max(
        f47_metrics[architecture]["pressure_pa_abs"]["cross_model"]["maximum"]
        for architecture in ("2v", "4v")
    )
    candidates = material_candidates()
    gates = {
        "controlled_standard_copies_reviewed": False,
        "supplier_DfAM_and_build_placement_approved": False,
        "powder_lot_and_reuse_plan_approved": False,
        "machine_IQ_OQ_PQ_current": False,
        "exact_machine_material_parameter_set_approved": False,
        "support_and_recoater_review_passed": False,
        "machining_and_powder_removal_plan_approved": False,
        "AdditiveFOAM_calibrated_and_converged": False,
        "coupon_hot_material_card_qualified": False,
        "HIP_route_selected_and_qualified": False,
        "thermomechanical_analysis_correlated": False,
        "CT_detectability_and_acceptance_approved": False,
        "surface_NDT_accepted": False,
        "pressure_leak_and_flow_tests_accepted": False,
        "independent_engineering_review_signed": False,
        "metal_print_authorized": False,
        "engine_start_authorized": False,
    }
    contract: dict[str, Any] = {
        "schema_version": "1.0.0",
        "phase": "F49",
        "asset_id": "917-30-turbo-head-material-lpbf-qualification-f49",
        "classification": "material_and_process_screening_not_part_qualification_not_print_release",
        "$comment": "F49 ne cree ni CAO ni maillage. CP1 est un candidat d'eprouvettes, pas une matiere qualifiee. Toutes les portes de fabrication et de demarrage restent fermees.",
        "scope": {
            "architectures": ["2v", "4v"],
            "same_material_process_and_acceptance_for_both_architectures": True,
            "air_cooled_turbo_head": True,
            "CAD_or_mesh_created": False,
            "external_scan_skin_modified": False,
            "functional_interface_dimension_created": False,
            "geometry_claimed": False,
            "outer_surface_policy": {
                "authority": "F43_scan_contour_outer_skin_via_F47_internal_contract",
                "same_exact_F43_bytes_required_for_2v_and_4v": True,
                "external_shape_change_allowed": False,
                "uniform_or_directional_scaling_allowed": False,
                "global_envelope_authored_by_F49": False,
                "internal_analytic_scope": "functional_circular_cylinders_only_per_F47",
                "historical_proxy_geometry_reusable": False,
            },
        },
        "upstream": {
            "F45_material_and_valvetrain_screen": {
                "path": F45_PATH.as_posix(),
                "sha256": sha256(root / F45_PATH),
            },
            "F47_CAE_load_contract": {
                "path": F47_PATH.as_posix(),
                "sha256": sha256(root / F47_PATH),
            },
            "F47_internal_geometry_policy": {
                "path": F47_INTERNAL_PATH.as_posix(),
                "sha256": sha256(root / F47_INTERNAL_PATH),
            },
            "F47_load_summary": {
                "path": F47_SUMMARY_PATH.as_posix(),
                "sha256": sha256(root / F47_SUMMARY_PATH),
                "peak_cross_model_gas_temperature_k": round(peak_gas_temperature, 9),
                "peak_cross_model_absolute_pressure_pa": round(peak_pressure, 6),
                "gas_temperature_is_not_metal_temperature": True,
                "loads_are_physically_correlated": False,
            },
        },
        "source_bindings": source_bindings(root),
        "material_comparison": candidates,
        "screening_decision": {
            "primary_coupon_candidate": "Aheadd_CP1_400C_4h",
            "alternate_coupon_candidate": "A20X_A205_LPBF_T7",
            "process_controls": ["EOS_AlSi10Mg_T6", "EOS_AlF357_T6_like"],
            "machined_reference": "2618_T61_wrought_machined_reference",
            "qualified_material": None,
            "reason": "CP1 combine la conductivite publique la plus elevee du tableau et une stabilite fournisseur 250-300 degC; A20X conserve les meilleurs points de traction a chaud. CP1 ne dispose toutefois pas d'une carte mecanique publique a chaud et aucun candidat ne fournit la carte route-machine-orientation complete.",
            "selection_is_manufacturing_release": False,
        },
        "selected_machine_route": {
            "service_provider_candidate": "PWR_Advanced_Cooling_Technology",
            "provider_source": "SRC-PWR-VELO3D-CP1-PRODUCTION",
            "provider_committed_to_this_part": False,
            "machine_manufacturer": "Velo3D",
            "machine_model": "Sapphire_standard",
            "machine_source": "SRC-VELO3D-SAPPHIRE-PRODUCT-BRIEF",
            "laser_configuration": "dual_1kW",
            "recoater": "non_contact",
            "candidate_layer_thickness_um": 50.0,
            "candidate_layer_reason": "higher_public_CP1_tensile_minima_than_100um_route_and_lower_rate_screen",
            "supplier_parameter_card_received": False,
            "machine_build_file_created": False,
            "supplier_order_placed": False,
            "fit_screen": orientation_screen(),
        },
        "process_plan": {
            "orientation_status": "35deg_roll_screen_requires_supplier_Flow_optimization",
            "orientation_DOE_roll_deg": [25.0, 35.0, 45.0],
            "support_policy": {
                "internal_gas_or_oil_passage_supports_allowed": False,
                "support_contact_on_seat_guide_bore_deck_or_bearing_surface_allowed": False,
                "external_supports": "sacrificial_and_accessible_only_on_designated_nonfunctional_machined_pads",
                "cooling_feature_support_removal_verified": False,
                "powder_removal_access_verified": False,
                "support_projection_generated": False,
            },
            "machining_allowance_hypotheses": {
                "classification": "process_planning_start_values_not_released_dimensions",
                "deck_axial_mm": 1.0,
                "port_flange_axial_mm": 1.0,
                "seat_bore_radial_mm": 0.3,
                "guide_bore_radial_mm": 0.2,
                "stud_passage_radial_mm": 0.3,
                "carrier_support_axial_mm": 0.8,
                "shaft_bore_radial_mm": 0.3,
                "threads": "print_solid_or_pilot_then_machine_with_inserts_where_approved",
                "supplier_and_machinist_approved": False,
            },
            "post_processing": {
                "baseline_route": {
                    "material": "Aheadd_CP1",
                    "cycle": "400_degC_4h",
                    "quench": "none",
                    "T6_designation_used": False,
                    "source": "SRC-CONSTELLIUM-AHEADD-CP1-PRODUCT-SHEET",
                    "route_qualified_on_head_coupons": False,
                },
                "HIP_branch": {
                    "manufacturer_declares_400C_compatible": True,
                    "pressure_mpa": None,
                    "hold_time_h": None,
                    "cooling_rate": None,
                    "selected": False,
                    "qualification_requires_side_by_side_fatigue_thermal_and_CT_results": True,
                },
                "A20X_branch": {
                    "temper": "T7",
                    "public_full_recipe_available": False,
                    "transfer_to_CP1_allowed": False,
                },
                "part_on_plate_heat_treatment_sequence_approved": False,
                "support_removal_sequence_approved": False,
                "final_machining_and_cleaning_sequence_approved": False,
            },
        },
        "coupon_qualification_plan": {
            "minimum_independent_builds_for_screening": 3,
            "screening_replicates_per_temperature_orientation_route": 3,
            "design_allowable_statistical_sample_plan": None,
            "orientations": ["X", "Y", "Z", "45deg"],
            "route_branches": ["CP1_400C_4h_without_HIP", "CP1_HIP_at_400C_supplier_cycle_then_final_route"],
            "temperatures_c": [20.0, 150.0, 200.0, 250.0, 300.0],
            "tests": [
                {"property": "yield_uts_elongation_reduction_of_area", "method": "ASTM_E21_at_hot_points_and_ASTM_E8_E8M_25_at_20C"},
                {"property": "thermal_diffusivity", "method": "ASTM_E1461"},
                {"property": "thermal_conductivity", "method": "k_equals_diffusivity_times_density_times_cp_same_route_temperature"},
                {"property": "E_nu_CTE_cp_density_hardness_plasticity", "method": "approved_current_methods_to_be_frozen_in_PQR"},
                {"property": "HCF_LCF_TMF", "method": "load_ratio_waveform_surface_and_temperature_from_correlated_duty_cycle"},
                {"property": "creep_and_stress_relaxation", "method": "200_250_300C_screen_with_100h_and_1000h_holds"},
                {"property": "microstructure_porosity_and_defect_sensitivity", "method": "metallography_CT_and_notched_coupon_plan"},
                {"property": "thin_feature_overhang_support_and_powder_removal", "method": "route_specific_witness_artifacts"},
            ],
            "coupon_locations": ["platform_center", "platform_near_edge_1", "platform_near_edge_2", "adjacent_to_part_hot_feature_region"],
            "coupon_heat_history_matches_part": False,
            "coupon_machining_surface_and_HIP_match_part": False,
            "screening_reference_only_if_exact_50um_route": {
                "minimum_yield_mpa_at_20C": 297.0,
                "minimum_uts_mpa_at_20C": 331.0,
                "minimum_elongation_percent_at_20C": 13.9,
                "design_allowable": False,
            },
            "hot_strength_acceptance_curves": None,
            "thermal_property_acceptance_curves": None,
            "fatigue_TMF_creep_acceptance_curves": None,
            "statistical_lower_tolerance_basis": None,
            "qualification_complete": False,
        },
        "inspection_and_acceptance_plan": {
            "powder": {
                "required_specification": "SAE_AMS7074_controlled_copy",
                "lifecycle_standard": "ISO_ASTM_52928_2024",
                "lot_CoA_reviewed": False,
                "virgin_reused_blend_limits": None,
                "oxygen_hydrogen_and_contamination_limits": None,
            },
            "process_site": {
                "quality_standard": "ISO_ASTM_52920_2023",
                "machine_standard": "ISO_ASTM_TS_52930_2021_IQ_OQ_PQ",
                "material_reporting_standard": "ISO_ASTM_52929_2025",
                "monitoring_data_standard": "ISO_ASTM_52953_2025",
                "native_Assure_monitoring_archive_received": False,
                "current_certificates_and_audit_received": False,
            },
            "CT": {
                "standard_family": "ISO_15708_parts_1_to_4_current_2024_2025",
                "reference_defect_artifact_required": True,
                "voxel_size_um": None,
                "probability_of_detection_curve": None,
                "maximum_accepted_defect_by_zone": None,
                "gas_oil_wall_segmentation_accepted": False,
            },
            "surface_NDT": {
                "method": "ASTM_E1417_E1417M_21e1_liquid_penetrant",
                "procedure_level": None,
                "linear_indication_limit": None,
                "rounded_indication_limit": None,
                "accepted": False,
            },
            "metrology": {
                "CMM_datum_scheme": None,
                "surface_profile_limits": None,
                "machined_bore_and_face_limits": None,
                "accepted": False,
            },
            "pressure_leak_and_cleanliness": {
                "proof_pressure_pa": None,
                "leak_rate_limit": None,
                "test_fluid_temperature_and_duration": None,
                "oil_and_gas_circuit_cross_leak_limit": None,
                "residual_powder_limit": None,
                "accepted": False,
            },
            "acceptance_criteria_frozen_before_build": False,
        },
        "additivefoam_contract": {
            "repository": "https://github.com/ORNL/AdditiveFOAM",
            "pinned_revision": "9c05c5eb54db03faa342b14b0806efe740de8c44",
            "classification": "process_model_calibration_contract_not_virtual_print_proof",
            "required_inputs": {
                "exact_supplier_scan_strategy_and_path": False,
                "beam_profile_spot_power_and_absorptivity": False,
                "powder_and_solid_k_cp_density_vs_temperature": False,
                "solidus_liquidus_latent_heat_and_emissivity": False,
                "build_plate_contact_preheat_and_gas_boundary": False,
                "support_geometry_and_contact_properties": False,
                "coupon_melt_pool_calibration_data": False,
            },
            "numerical_acceptance": {
                "all_fields_finite": True,
                "temperature_cap_k": 3300.0,
                "temperature_cap_hit_allowed": False,
                "maximum_relative_change_melt_pool_dimensions_between_last_two_levels": 0.05,
                "maximum_relative_change_molten_volume_between_last_two_levels": 0.05,
                "maximum_relative_change_temperature_p99_between_last_two_levels": 0.03,
                "mass_and_energy_balance_tolerance": None,
            },
            "outputs_required": [
                "melt_pool_width_depth_length_by_layer_and_scan_feature",
                "cooling_rate_and_thermal_gradient_distributions",
                "temperature_cap_and_conservation_audit",
                "mesh_and_time_step_convergence",
                "coupon_calibration_error_with_uncertainty",
            ],
            "simulation_executed_for_CP1_route": False,
            "calibrated_to_physical_CP1_coupon": False,
            "qualified_for_production_head": False,
        },
        "thermomechanical_contract": {
            "F47_loads_bound_by_hash": True,
            "F47_loads_correlated": False,
            "same_F47_load_basis_for_2v_and_4v": True,
            "solid_mesh_available_for_this_contract": False,
            "required_material_fields_vs_temperature": [
                "thermal_conductivity",
                "heat_capacity",
                "density",
                "elastic_modulus",
                "poisson_ratio",
                "thermal_expansion",
                "yield_and_plastic_hardening",
                "LCF_HCF_TMF",
                "creep_and_stress_relaxation",
                "defect_surface_orientation_knockdowns",
            ],
            "qualified_material_card_path": None,
            "approved_duty_cycle_path": None,
            "approved_surface_sets_path": None,
            "yield_margin_requirement": None,
            "fatigue_life_requirement_cycles": None,
            "creep_strain_requirement": None,
            "distortion_and_seal_flatness_requirement": None,
            "mesh_time_step_and_cycle_convergence_requirement": None,
            "analysis_executed": False,
            "physical_thermal_and_pressure_correlation_complete": False,
            "accepted": False,
        },
        "release_gates": gates,
        "conclusion": {
            "material_screening_result": "CP1_first_coupon_route_A20X_alternate",
            "machine_screening_result": "Sapphire_bare_envelope_only",
            "part_qualified": False,
            "printable_part_claimed": False,
            "manufacturing_release_claimed": False,
        },
    }
    validate_contract(contract)
    return contract


def validate_contract(contract: dict[str, Any]) -> None:
    if contract["phase"] != "F49":
        raise ValueError("wrong_phase")
    if contract["screening_decision"]["qualified_material"] is not None:
        raise ValueError("qualified_material_must_remain_null")
    if any(contract["release_gates"].values()):
        raise ValueError("release_gate_must_remain_closed")
    scope = contract["scope"]
    if scope["CAD_or_mesh_created"] or scope["external_scan_skin_modified"] or scope["geometry_claimed"]:
        raise ValueError("F49_must_not_author_geometry")
    outer = scope["outer_surface_policy"]
    if outer != {
        "authority": "F43_scan_contour_outer_skin_via_F47_internal_contract",
        "same_exact_F43_bytes_required_for_2v_and_4v": True,
        "external_shape_change_allowed": False,
        "uniform_or_directional_scaling_allowed": False,
        "global_envelope_authored_by_F49": False,
        "internal_analytic_scope": "functional_circular_cylinders_only_per_F47",
        "historical_proxy_geometry_reusable": False,
    }:
        raise ValueError("F43_outer_surface_policy_must_remain_fail_closed")
    if not contract["selected_machine_route"]["fit_screen"]["bare_envelope_screen_pass"]:
        raise ValueError("selected_machine_fails_minimum_envelope")
    if contract["selected_machine_route"]["fit_screen"]["final_build_fit_verified"]:
        raise ValueError("bare_envelope_cannot_be_promoted_to_final_fit")
    if any(item["complete_hot_card"] for item in contract["material_comparison"]):
        raise ValueError("public_source_set_does_not_complete_a_hot_card")
    if contract["coupon_qualification_plan"]["qualification_complete"]:
        raise ValueError("coupon_qualification_not_executed")
    if contract["additivefoam_contract"]["simulation_executed_for_CP1_route"]:
        raise ValueError("AdditiveFOAM_execution_not_evidenced")
    if contract["thermomechanical_contract"]["analysis_executed"]:
        raise ValueError("thermomechanical_execution_not_evidenced")


def serialize_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def comparison_csv(contract: dict[str, Any]) -> str:
    buffer = io.StringIO(newline="")
    fields = [
        "screening_rank",
        "material_id",
        "route",
        "density_kg_m3",
        "rt_yield_mpa",
        "rt_uts_mpa",
        "rt_elongation_percent",
        "rt_thermal_conductivity_w_mk",
        "hot_tensile_points_count",
        "complete_hot_card",
        "screening_role",
        "qualified_material",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for item in sorted(contract["material_comparison"], key=lambda row: row["screening_rank"]):
        room = item["room_temperature"]
        conductivity = room["thermal_conductivity_w_mk"]
        if isinstance(conductivity, dict):
            conductivity = "/".join(f"{key}:{value:g}" for key, value in sorted(conductivity.items()))
        writer.writerow(
            {
                "screening_rank": item["screening_rank"],
                "material_id": item["id"],
                "route": item["manufacturing_route"],
                "density_kg_m3": "" if item["density_kg_m3"] is None else item["density_kg_m3"],
                "rt_yield_mpa": "" if room["yield_mpa"] is None else room["yield_mpa"],
                "rt_uts_mpa": "" if room["uts_mpa"] is None else room["uts_mpa"],
                "rt_elongation_percent": "" if room["elongation_percent"] is None else room["elongation_percent"],
                "rt_thermal_conductivity_w_mk": "" if conductivity is None else conductivity,
                "hot_tensile_points_count": len(item["public_hot_tensile_points"]),
                "complete_hot_card": str(item["complete_hot_card"]).lower(),
                "screening_role": item["screening_role"],
                "qualified_material": "false",
            }
        )
    return buffer.getvalue()


def expected_outputs(root: Path) -> dict[Path, str]:
    contract = build_contract(root)
    contract_text = serialize_json(contract)
    csv_text = comparison_csv(contract)
    outputs = {
        CONTRACT_PATH: contract_text,
        COMPARISON_PATH: csv_text,
    }
    manifest = {
        "schema_version": "1.0.0",
        "phase": "F49",
        "classification": "deterministic_material_process_screening_manifest",
        "generator": {
            "path": SCRIPT_PATH.as_posix(),
            "sha256": sha256(root / SCRIPT_PATH),
        },
        "artifacts": [
            {
                "path": path.as_posix(),
                "bytes": len(text.encode("utf-8")),
                "sha256": sha256_bytes(text.encode("utf-8")),
            }
            for path, text in sorted(outputs.items(), key=lambda item: item[0].as_posix())
        ],
        "release_claimed": False,
    }
    outputs[MANIFEST_PATH] = serialize_json(manifest)
    return outputs


def write_or_check(root: Path, check: bool) -> int:
    failures: list[str] = []
    for relative, expected in expected_outputs(root).items():
        path = root / relative
        if check:
            if not path.is_file():
                failures.append(f"missing:{relative}")
            elif path.read_text(encoding="utf-8") != expected:
                failures.append(f"stale:{relative}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
    if failures:
        for failure in failures:
            print(failure)
        return 1
    print("F49 material/LPBF qualification evidence: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    return write_or_check(args.project_root.resolve(), args.check)


if __name__ == "__main__":
    raise SystemExit(main())
