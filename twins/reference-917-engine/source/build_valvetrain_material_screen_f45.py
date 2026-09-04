#!/usr/bin/env python3
"""Pré-dimensionnement traçable 2V/4V et criblage matières F45.

Le calcul reste analytique et fail-closed. Il ne crée aucune surface de culasse,
ne change pas l'enveloppe issue du scan et ne définit aucune cote d'interface
Porsche. Les cotes de composants marquées ``research_hypothesis`` servent
uniquement à vérifier un paquetage dans un alésage circulaire de 90 mm.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


BORE_MM = 90.0
BORE_RADIUS_MM = BORE_MM / 2.0
RPM = 9000.0
EVENT_DURATION_CRANK_DEG = 300.0
DISCHARGE_COEFFICIENT = 0.72
THROAT_TO_HEAD_RATIO = 0.86
SPRING_G_MPA = 79_000.0
SPRING_DENSITY_KG_MM3 = 7_850.0e-9
SPRING_SHEAR_SCREEN_LIMIT_MPA = 1_000.0

AUTHORITY_PATH = Path("twins/reference-917-engine/head-architecture-authority-f45.json")
F20_PATH = Path("twins/reference-917-engine/valvetrain-flow-inputs-f20.json")
OUTPUT_PATH = Path("twins/reference-917-engine/valvetrain-material-screen-f45.json")
IMAGE_PATH = Path("twins/reference-917-engine/evidence/f45-valvetrain/valvetrain-material-screen-f45.png")
SOURCE_PATHS = (
    Path("catalog/sources/src-fia-917-homologation-250.json"),
    Path("catalog/sources/src-constellium-aheadd-ht1-fact-sheet.json"),
    Path("catalog/sources/src-eckart-a20x-lpbf.json"),
    Path("catalog/sources/src-eos-alf357-material-data.json"),
    Path("catalog/sources/src-eos-alsi10mg-material-data.json"),
    Path("catalog/sources/src-timet-ti64-physical-properties.json"),
    Path("catalog/sources/src-special-metals-inconel-751.json"),
    Path("catalog/sources/src-mahle-valvetrain-technical-2025.json"),
    Path("catalog/sources/src-swindon-m64-24v-head-kit.json"),
)


def rounded(value: float) -> float:
    return round(float(value), 6)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distance(point_a: list[float], point_b: list[float]) -> float:
    return math.hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])


def circle_pack(
    circles: list[dict[str, Any]],
    plug: dict[str, Any] | None,
) -> dict[str, Any]:
    edge_gaps = []
    pair_gaps = []
    plug_gaps = []
    for circle in circles:
        centre = circle["centre_xy_mm"]
        radius = circle["seat_envelope_diameter_mm"] / 2.0
        edge_gaps.append(BORE_RADIUS_MM - math.hypot(*centre) - radius)
    for index, first in enumerate(circles):
        for second in circles[index + 1 :]:
            first_radius = first["seat_envelope_diameter_mm"] / 2.0
            second_radius = second["seat_envelope_diameter_mm"] / 2.0
            pair_gaps.append(
                {
                    "between": [first["id"], second["id"]],
                    "gap_mm": rounded(
                        distance(first["centre_xy_mm"], second["centre_xy_mm"])
                        - first_radius
                        - second_radius
                    ),
                }
            )
    if plug is not None:
        for circle in circles:
            plug_gaps.append(
                {
                    "between": [circle["id"], plug["id"]],
                    "gap_mm": rounded(
                        distance(circle["centre_xy_mm"], plug["centre_xy_mm"])
                        - circle["seat_envelope_diameter_mm"] / 2.0
                        - plug["diameter_mm"] / 2.0
                    ),
                }
            )
    seat_area = sum(math.pi * (item["seat_envelope_diameter_mm"] / 2.0) ** 2 for item in circles)
    return {
        "bore_shape": "circle",
        "bore_diameter_mm": BORE_MM,
        "global_shape_change": False,
        "seat_envelope_area_fraction_of_bore": rounded(seat_area / (math.pi * BORE_RADIUS_MM**2)),
        "minimum_bore_edge_gap_mm": rounded(min(edge_gaps)),
        "minimum_seat_to_seat_gap_mm": rounded(min(item["gap_mm"] for item in pair_gaps)),
        "pairwise_seat_gaps": pair_gaps,
        "plug_package": plug,
        "minimum_seat_to_plug_gap_mm": None if not plug_gaps else rounded(min(item["gap_mm"] for item in plug_gaps)),
        "seat_to_plug_gaps": plug_gaps,
        "screen_pass": min(edge_gaps) >= 1.5
        and min(item["gap_mm"] for item in pair_gaps) >= 2.0
        and (not plug_gaps or min(item["gap_mm"] for item in plug_gaps) >= 3.0),
        "fitment_or_interface_proof": False,
    }


def valve_mass_kg(head_diameter_mm: float, stem_diameter_mm: float, density_kg_m3: float) -> float:
    head_disc_thickness_mm = 2.5
    stem_length_mm = 96.0
    volume_mm3 = (
        math.pi * (head_diameter_mm / 2.0) ** 2 * head_disc_thickness_mm
        + math.pi * (stem_diameter_mm / 2.0) ** 2 * stem_length_mm
    )
    return volume_mm3 * density_kg_m3 * 1.0e-9


def flow_screen(count: int, diameter_mm: float, lift_mm: float) -> dict[str, Any]:
    curtain = count * math.pi * diameter_mm * lift_mm
    throat = count * math.pi * (THROAT_TO_HEAD_RATIO * diameter_mm) ** 2 / 4.0
    limiting = min(curtain, throat)
    crossover_lift = throat / (count * math.pi * diameter_mm)
    return {
        "curtain_area_mm2": rounded(curtain),
        "throat_area_mm2": rounded(throat),
        "limiting_geometric_area_mm2": rounded(limiting),
        "effective_area_at_cd_0_72_mm2": rounded(DISCHARGE_COEFFICIENT * limiting),
        "throat_to_head_diameter_ratio": THROAT_TO_HEAD_RATIO,
        "curtain_throat_crossover_lift_mm": rounded(crossover_lift),
        "limiter_at_maximum_lift": "curtain" if curtain < throat else "throat",
        "flow_coefficient_correlated": False,
    }


def spring_rate_n_mm(coil: dict[str, float]) -> float:
    return (
        SPRING_G_MPA
        * coil["wire_diameter_mm"] ** 4
        / (8.0 * coil["mean_diameter_mm"] ** 3 * coil["active_coils"])
    )


def wahl_factor(coil: dict[str, float]) -> float:
    spring_index = coil["mean_diameter_mm"] / coil["wire_diameter_mm"]
    return (4.0 * spring_index - 1.0) / (4.0 * spring_index - 4.0) + 0.615 / spring_index


def spring_shear_mpa(force_n: float, coil: dict[str, float]) -> float:
    return (
        wahl_factor(coil)
        * 8.0
        * force_n
        * coil["mean_diameter_mm"]
        / (math.pi * coil["wire_diameter_mm"] ** 3)
    )


def spring_mass_kg(coil: dict[str, float], installed_height_mm: float) -> float:
    turns = coil["active_coils"] + 2.0
    helix_length_mm = math.hypot(math.pi * coil["mean_diameter_mm"] * turns, installed_height_mm)
    wire_area_mm2 = math.pi * coil["wire_diameter_mm"] ** 2 / 4.0
    return helix_length_mm * wire_area_mm2 * SPRING_DENSITY_KG_MM3


def spring_screen(
    spring: dict[str, Any],
    lift_mm: float,
    moving_mass_kg: float,
    opening_gas_force_n: float,
    acceleration_m_s2: float,
) -> dict[str, Any]:
    outer = spring["outer"]
    inner = spring["inner"]
    outer_rate = spring_rate_n_mm(outer)
    inner_rate = spring_rate_n_mm(inner)
    total_rate = outer_rate + inner_rate
    seat_force = spring["seat_force_n"]
    open_force = seat_force + total_rate * lift_mm
    outer_share = outer_rate / total_rate
    outer_seat_force = seat_force * outer_share
    inner_seat_force = seat_force * (1.0 - outer_share)
    outer_open_force = open_force * outer_share
    inner_open_force = open_force * (1.0 - outer_share)
    solid_outer = (outer["active_coils"] + 2.0) * outer["wire_diameter_mm"]
    solid_inner = (inner["active_coils"] + 2.0) * inner["wire_diameter_mm"]
    nominal_bind = min(
        spring["installed_height_mm"] - lift_mm - solid_outer,
        spring["installed_height_mm"] - lift_mm - solid_inner,
    )
    worst_bind = nominal_bind - spring["installed_height_minus_tolerance_mm"] - spring["lift_plus_tolerance_mm"]
    spring_mass = spring_mass_kg(outer, spring["installed_height_mm"]) + spring_mass_kg(
        inner, spring["installed_height_mm"]
    )
    effective_mass = moving_mass_kg + spring_mass / 3.0
    natural_frequency = math.sqrt(total_rate * 1000.0 / effective_mass) / (2.0 * math.pi)
    event_frequency = RPM / 120.0
    inertial_force = moving_mass_kg * acceleration_m_s2
    required_open_force = inertial_force + opening_gas_force_n
    outer_open_stress = spring_shear_mpa(outer_open_force, outer)
    inner_open_stress = spring_shear_mpa(inner_open_force, inner)
    return {
        "combined_rate_n_mm": rounded(total_rate),
        "seat_force_n": rounded(seat_force),
        "open_force_n": rounded(open_force),
        "outer": {
            **outer,
            "spring_index": rounded(outer["mean_diameter_mm"] / outer["wire_diameter_mm"]),
            "wahl_factor": rounded(wahl_factor(outer)),
            "seat_shear_mpa": rounded(spring_shear_mpa(outer_seat_force, outer)),
            "open_shear_mpa": rounded(outer_open_stress),
        },
        "inner": {
            **inner,
            "spring_index": rounded(inner["mean_diameter_mm"] / inner["wire_diameter_mm"]),
            "wahl_factor": rounded(wahl_factor(inner)),
            "seat_shear_mpa": rounded(spring_shear_mpa(inner_seat_force, inner)),
            "open_shear_mpa": rounded(inner_open_stress),
        },
        "nominal_coil_bind_margin_mm": rounded(nominal_bind),
        "worst_case_coil_bind_margin_mm": rounded(worst_bind),
        "estimated_dual_spring_mass_kg": rounded(spring_mass),
        "single_dof_natural_frequency_hz": rounded(natural_frequency),
        "valve_event_frequency_hz": rounded(event_frequency),
        "natural_to_event_frequency_ratio": rounded(natural_frequency / event_frequency),
        "inertial_force_n": rounded(inertial_force),
        "opening_gas_force_n": rounded(opening_gas_force_n),
        "combined_opening_load_n": rounded(required_open_force),
        "open_force_to_combined_load_margin": rounded(open_force / required_open_force),
        "maximum_wahl_corrected_shear_mpa": rounded(max(outer_open_stress, inner_open_stress)),
        "research_shear_screen_limit_mpa": SPRING_SHEAR_SCREEN_LIMIT_MPA,
        "research_shear_limit_is_supplier_allowable": False,
        "shear_screen_margin_to_1000_mpa": rounded(
            SPRING_SHEAR_SCREEN_LIMIT_MPA / max(outer_open_stress, inner_open_stress)
        ),
        "static_analytical_screen_pass": worst_bind >= 2.5
        and open_force / required_open_force >= 1.2
        and max(outer_open_stress, inner_open_stress) <= SPRING_SHEAR_SCREEN_LIMIT_MPA,
        "dynamic_screen_pass": False,
        "analytical_screen_pass": False,
        "dynamic_blocker": "Courbe de came, raideur dynamique, surge map fournisseur et essai spintron absents.",
        "supplier_curve_or_spintron_validated": False,
    }


def architecture_inputs() -> dict[str, Any]:
    return {
        "2v": {
            "classification": "F45_research_hypothesis_in_circular_90_mm_bore",
            "historical_reference": {
                "variant": "type_912_4_5_na_not_917_30",
                "intake_head_diameter_mm": 47.5,
                "exhaust_head_diameter_mm": 40.5,
                "intake_max_lift_mm": 12.1,
                "exhaust_max_lift_mm": 10.5,
                "direct_transfer_to_F45": False,
                "reason": "Valeurs FIA du moteur initial 4 494,2 cm3; elles ne définissent pas le 917/30 turbo.",
            },
            "valves": {
                "intake": {
                    "count": 1,
                    "head_diameter_mm": 42.0,
                    "stem_diameter_mm": 7.0,
                    "maximum_lift_mm": 11.5,
                    "seat_envelope_diameter_mm": 44.0,
                    "centres_xy_mm": [[0.0, 21.5]],
                    "density_kg_m3": 4420.0,
                    "additional_equivalent_moving_mass_kg": 0.038,
                    "opening_pressure_difference_mpa": 0.25,
                    "material": "purchased_forged_or_wrought_Ti_6Al_4V_candidate",
                },
                "exhaust": {
                    "count": 1,
                    "head_diameter_mm": 35.0,
                    "stem_diameter_mm": 7.0,
                    "maximum_lift_mm": 10.0,
                    "seat_envelope_diameter_mm": 37.0,
                    "centres_xy_mm": [[0.0, -21.0]],
                    "density_kg_m3": 8220.0,
                    "additional_equivalent_moving_mass_kg": 0.038,
                    "opening_pressure_difference_mpa": 0.50,
                    "material": "purchased_bar_or_forged_INCONEL_751_candidate",
                },
            },
            "spark_plug_package": None,
            "spring": {
                "material": "purchased_ultra_clean_CrSi_oil_tempered_nitrided_shot_peened_candidate",
                "installed_height_mm": 46.0,
                "installed_height_minus_tolerance_mm": 0.5,
                "lift_plus_tolerance_mm": 0.2,
                "seat_force_n": 400.0,
                "outer": {"wire_diameter_mm": 4.6, "mean_diameter_mm": 25.0, "active_coils": 4.8},
                "inner": {"wire_diameter_mm": 3.1, "mean_diameter_mm": 17.0, "active_coils": 5.5},
            },
        },
        "4v": {
            "classification": "F45_research_hypothesis_in_circular_90_mm_bore",
            "external_benchmark": {
                "source": "SRC-SWINDON-M64-24V-HEAD-KIT",
                "scope": "M64_95_to_102_7_mm_bore_not_917_geometry",
                "declared_intake_diameter_mm": 40.0,
                "declared_exhaust_diameter_mm": 33.0,
                "direct_transfer_to_F45": False,
            },
            "valves": {
                "intake": {
                    "count": 2,
                    "head_diameter_mm": 31.5,
                    "stem_diameter_mm": 7.0,
                    "maximum_lift_mm": 10.0,
                    "seat_envelope_diameter_mm": 33.5,
                    "centres_xy_mm": [[-19.5, 15.5], [19.5, 15.5]],
                    "density_kg_m3": 4420.0,
                    "additional_equivalent_moving_mass_kg": 0.025,
                    "opening_pressure_difference_mpa": 0.25,
                    "material": "purchased_forged_or_wrought_Ti_6Al_4V_candidate",
                },
                "exhaust": {
                    "count": 2,
                    "head_diameter_mm": 26.0,
                    "stem_diameter_mm": 7.0,
                    "maximum_lift_mm": 9.0,
                    "seat_envelope_diameter_mm": 29.0,
                    "centres_xy_mm": [[-19.5, -19.0], [19.5, -19.0]],
                    "density_kg_m3": 8220.0,
                    "additional_equivalent_moving_mass_kg": 0.025,
                    "opening_pressure_difference_mpa": 0.50,
                    "material": "purchased_bar_or_forged_INCONEL_751_candidate",
                },
            },
            "spark_plug_package": {
                "id": "central_M10_bore_packaging_envelope",
                "centre_xy_mm": [0.0, 0.0],
                "diameter_mm": 10.0,
                "classification": "research_hypothesis_not_Porsche_interface",
            },
            "spring": {
                "material": "purchased_ultra_clean_CrSi_oil_tempered_nitrided_shot_peened_candidate",
                "installed_height_mm": 42.0,
                "installed_height_minus_tolerance_mm": 0.5,
                "lift_plus_tolerance_mm": 0.2,
                "seat_force_n": 260.0,
                "outer": {"wire_diameter_mm": 3.8, "mean_diameter_mm": 22.0, "active_coils": 5.0},
                "inner": {"wire_diameter_mm": 2.5, "mean_diameter_mm": 14.5, "active_coils": 6.0},
            },
        },
    }


def material_matrix() -> list[dict[str, Any]]:
    missing_common = [
        "route_specific_k_vs_temperature",
        "route_specific_E_alpha_plasticity_vs_temperature",
        "LCF_HCF_and_thermomechanical_fatigue_after_final_heat_treatment",
        "creep_or_stress_relaxation",
        "defect_notch_and_surface_condition_allowables",
        "machine_powder_orientation_coupon_and_build_repeatability",
    ]
    return [
        {
            "id": "Aheadd_HT1_heat_treatment_1",
            "requested_alias": "Aheadd_HT1",
            "source": "SRC-CONSTELLIUM-AHEADD-HT1-FACT-SHEET",
            "density_kg_m3": None,
            "property_points": [
                {"temperature_c": 25, "yield_mpa": 425, "uts_mpa": 445, "elongation_percent": 6},
                {"temperature_c": 200, "yield_mpa": 238, "uts_mpa": 268, "elongation_percent": 13},
                {"temperature_c": 250, "yield_mpa": 188, "uts_mpa": 225, "elongation_percent": 6},
            ],
            "supplier_service_temperature_scope_c": 260,
            "room_temperature_conductivity_w_mk": None,
            "missing_for_release": missing_common,
            "complete_hot_card": False,
        },
        {
            "id": "Aheadd_HT1_heat_treatment_2",
            "requested_alias": "Aheadd_HT2",
            "normalization_note": "La source officielle nomme ceci traitement #2 du même alliage Aheadd HT1, pas un alliage Aheadd HT2 distinct.",
            "source": "SRC-CONSTELLIUM-AHEADD-HT1-FACT-SHEET",
            "density_kg_m3": None,
            "property_points": [
                {"temperature_c": 25, "yield_mpa": 285, "uts_mpa": 445, "elongation_percent": 6},
                {"temperature_c": 200, "yield_mpa": 270, "uts_mpa": 293, "elongation_percent": 11},
                {"temperature_c": 250, "yield_mpa": 216, "uts_mpa": 265, "elongation_percent": 5},
            ],
            "supplier_service_temperature_scope_c": 260,
            "room_temperature_conductivity_w_mk": None,
            "missing_for_release": missing_common,
            "complete_hot_card": False,
        },
        {
            "id": "A20X_A205_LPBF_T7",
            "source": "SRC-ECKART-A20X-LPBF",
            "density_kg_m3": 2850,
            "property_points": [
                {"temperature_c": 20, "yield_mpa": 445, "uts_mpa": 511, "elongation_percent": 11},
                {"temperature_c": 100, "yield_mpa": 375, "uts_mpa": 423, "elongation_percent": 10},
                {"temperature_c": 150, "yield_mpa": 354, "uts_mpa": 369, "elongation_percent": 20},
                {"temperature_c": 200, "yield_mpa": 311, "uts_mpa": 331, "elongation_percent": 15},
                {"temperature_c": 250, "yield_mpa": 215, "uts_mpa": 224, "elongation_percent": 12},
            ],
            "supplier_service_temperature_scope_c": 190,
            "room_temperature_conductivity_w_mk": None,
            "missing_for_release": missing_common,
            "complete_hot_card": False,
        },
        {
            "id": "EOS_AlF357_T6_like",
            "source": "SRC-EOS-ALF357-MATERIAL-DATA",
            "density_kg_m3": None,
            "property_points": [
                {"temperature_c": 20, "yield_mpa": 265, "uts_mpa": 330, "elongation_percent": 11.5}
            ],
            "supplier_service_temperature_scope_c": None,
            "room_temperature_conductivity_w_mk": 150,
            "missing_for_release": missing_common,
            "complete_hot_card": False,
        },
        {
            "id": "EOS_AlSi10Mg_T6",
            "source": "SRC-EOS-ALSI10MG-MATERIAL-DATA",
            "density_kg_m3": 2660,
            "property_points": [
                {"temperature_c": 20, "yield_mpa": 245, "uts_mpa": 460, "elongation_percent": 5}
            ],
            "supplier_service_temperature_scope_c": None,
            "room_temperature_conductivity_w_mk": {"vertical": 165, "horizontal": 155},
            "missing_for_release": missing_common,
            "complete_hot_card": False,
        },
    ]


def analyse_architecture(identifier: str, raw: dict[str, Any]) -> dict[str, Any]:
    event_time_s = EVENT_DURATION_CRANK_DEG / (6.0 * RPM)
    velocity_and_acceleration = {}
    circles = []
    family_reports: dict[str, Any] = {}
    total_valve_mass = 0.0
    for family in ("intake", "exhaust"):
        valve = raw["valves"][family]
        lift_m = valve["maximum_lift_mm"] / 1000.0
        velocity = math.pi * lift_m / event_time_s
        acceleration = 2.0 * math.pi**2 * lift_m / event_time_s**2
        mass_each = valve_mass_kg(
            valve["head_diameter_mm"], valve["stem_diameter_mm"], valve["density_kg_m3"]
        )
        moving_mass = mass_each + valve["additional_equivalent_moving_mass_kg"]
        gas_force = (
            valve["opening_pressure_difference_mpa"]
            * math.pi
            * valve["head_diameter_mm"] ** 2
            / 4.0
        )
        flow = flow_screen(valve["count"], valve["head_diameter_mm"], valve["maximum_lift_mm"])
        spring = spring_screen(raw["spring"], valve["maximum_lift_mm"], moving_mass, gas_force, acceleration)
        family_reports[family] = {
            **{key: value for key, value in valve.items() if key != "centres_xy_mm"},
            "centres_xy_mm": valve["centres_xy_mm"],
            "component_dimension_classification": "F45_research_hypothesis_not_Porsche_interface",
            "valve_mass_each_kg": rounded(mass_each),
            "total_valve_mass_kg": rounded(mass_each * valve["count"]),
            "equivalent_moving_mass_each_kg": rounded(moving_mass),
            "event_time_ms": rounded(event_time_s * 1000.0),
            "maximum_velocity_m_s": rounded(velocity),
            "maximum_acceleration_m_s2": rounded(acceleration),
            "flow": flow,
            "spring": spring,
        }
        total_valve_mass += mass_each * valve["count"]
        velocity_and_acceleration[family] = (velocity, acceleration)
        for index, centre in enumerate(valve["centres_xy_mm"], start=1):
            circles.append(
                {
                    "id": f"{family}_{index}",
                    "family": family,
                    "centre_xy_mm": centre,
                    "valve_head_diameter_mm": valve["head_diameter_mm"],
                    "seat_envelope_diameter_mm": valve["seat_envelope_diameter_mm"],
                }
            )
    packing = circle_pack(circles, raw["spark_plug_package"])
    spring_outer_diameter = raw["spring"]["outer"]["mean_diameter_mm"] + raw["spring"]["outer"]["wire_diameter_mm"]
    spring_gaps = []
    for index, first in enumerate(circles):
        for second in circles[index + 1 :]:
            spring_gaps.append(distance(first["centre_xy_mm"], second["centre_xy_mm"]) - spring_outer_diameter)
    packing["spring_outer_envelope_diameter_mm"] = rounded(spring_outer_diameter)
    packing["minimum_spring_envelope_gap_mm"] = rounded(min(spring_gaps))
    return {
        "id": f"917_30_turbo_5374_{identifier}_f45",
        "architecture": identifier,
        "classification": raw["classification"],
        "historical_reference": raw.get("historical_reference"),
        "external_benchmark": raw.get("external_benchmark"),
        "operating_screen": {
            "engine_speed_rpm": RPM,
            "event_duration_crank_deg": EVENT_DURATION_CRANK_DEG,
            "event_profile": "symmetric_half_cosine_full_lift_event_not_a_cam_law",
            "cam_or_valve_event_frequency_hz": rounded(RPM / 120.0),
            "pressure_trace_correlated": False,
        },
        "geometry_policy": {
            "external_head_envelope": "preserve_scan_contour_no_synthetic_body_in_this_sublot",
            "combustion_bore_shape": "circle",
            "combustion_bore_diameter_mm": BORE_MM,
            "global_anisotropic_scale_allowed": False,
            "global_ovalization_allowed": False,
            "body_or_fin_geometry_created": False,
        },
        "valves": family_reports,
        "packing": packing,
        "total_valve_mass_kg": rounded(total_valve_mass),
        "seat_and_guide_strategy": {
            "intake_seat_candidate": "purchased_sintered_high_speed_tool_steel_insert_finish_machined",
            "exhaust_seat_candidate": "purchased_copper_infiltrated_powder_metal_high_temperature_insert_finish_machined",
            "guide_candidate": "purchased_high_temperature_powder_metal_guide_finish_honed",
            "technical_basis": "SRC-MAHLE-VALVETRAIN-TECHNICAL-2025_generic_function_and_material_families_only",
            "seat_angle_contact_width_interference_and_bore": None,
            "guide_length_outer_diameter_interference_clearance_and_finish": None,
            "selected_supplier_part": None,
            "interface_dimension_invented": False,
        },
        "component_routes": {
            "head": "LPBF_candidate_not_selected",
            "valves": "purchased_forged_bar_or_wrought_not_printed",
            "springs": "purchased_CrSi_not_printed",
            "seats_and_guides": "purchased_inserts_finish_machined_not_printed",
        },
    }


def build_report(root: Path) -> dict[str, Any]:
    root = root.resolve()
    inputs = [AUTHORITY_PATH, F20_PATH, *SOURCE_PATHS]
    missing = [str(path) for path in inputs if not (root / path).is_file()]
    if missing:
        raise FileNotFoundError(f"required_inputs_missing:{','.join(missing)}")
    architectures = {
        key: analyse_architecture(key, value) for key, value in architecture_inputs().items()
    }
    two = architectures["2v"]
    four = architectures["4v"]
    comparison = {
        "four_vs_two_percent": {
            "intake_effective_area": rounded(
                100.0
                * (
                    four["valves"]["intake"]["flow"]["effective_area_at_cd_0_72_mm2"]
                    / two["valves"]["intake"]["flow"]["effective_area_at_cd_0_72_mm2"]
                    - 1.0
                )
            ),
            "exhaust_effective_area": rounded(
                100.0
                * (
                    four["valves"]["exhaust"]["flow"]["effective_area_at_cd_0_72_mm2"]
                    / two["valves"]["exhaust"]["flow"]["effective_area_at_cd_0_72_mm2"]
                    - 1.0
                )
            ),
            "total_valve_mass": rounded(100.0 * (four["total_valve_mass_kg"] / two["total_valve_mass_kg"] - 1.0)),
        },
        "decision": "no_architecture_release_analytical_screen_only",
    }
    release_gates = {
        "external_scan_contour_brep_integrated": False,
        "Porsche_917_interface_dimensions_verified": False,
        "cam_law_measured": False,
        "valve_supplier_drawing_approved": False,
        "spring_supplier_load_curve_and_surge_map_approved": False,
        "seat_and_guide_press_fits_qualified_hot": False,
        "complete_head_hot_material_card_available": False,
        "valvetrain_multibody_or_spintron_correlated": False,
        "thermal_mechanical_fatigue_correlated": False,
        "metal_print_authorized": False,
        "engine_start_authorized": False,
    }
    return {
        "$comment": "F45 compare analytiquement 2V et 4V dans un alésage circulaire de 90 mm sans créer ni modifier l'enveloppe de culasse. Aucun résultat ne libère la fabrication.",
        "schema_version": "1.0.0",
        "phase": "F45",
        "status": "analytical_valvetrain_and_material_screen_complete_all_release_gates_blocked",
        "asset_id": "porsche-917-30-turbo-f45-valvetrain-material-screen",
        "authority_boundary": {
            "target": "917_30_turbo_5374_2v_and_4v_research_candidates",
            "bore_mm": BORE_MM,
            "bore_source": "twins/reference-917-engine/head-architecture-authority-f45.json",
            "type_912_values_never_relabelled_as_917_30_exact": True,
            "all_new_component_dimensions_are_research_hypotheses": True,
            "Porsche_interface_dimensions_created": False,
            "external_scan_contour_modified": False,
            "global_ovalization": False,
        },
        "input_digests": {str(path): sha256(root / path) for path in inputs},
        "equations": {
            "curtain_area": "A_curtain=n*pi*d_v*L",
            "throat_area": "A_throat=n*pi*(0.86*d_v)^2/4",
            "event_time": "t_event=duration_crank_deg/(6*rpm)",
            "half_cosine_peak_velocity": "v_max=pi*L/t_event",
            "half_cosine_peak_acceleration": "a_max=2*pi^2*L/t_event^2",
            "gas_force_screen": "F_gas=delta_p*pi*d_v^2/4",
            "spring_rate": "k=G*d_wire^4/(8*D_mean^3*N_active)",
            "wahl_factor": "K_w=(4*C-1)/(4*C-4)+0.615/C; C=D_mean/d_wire",
            "spring_shear": "tau=K_w*8*F*D_mean/(pi*d_wire^3)",
            "system_frequency": "f_n=(1/(2*pi))*sqrt(k_total/(m_moving+m_spring/3))",
            "circle_edge_gap": "g_edge=R_bore-sqrt(x^2+y^2)-D_seat/2",
            "circle_pair_gap": "g_pair=distance(centres)-(D1+D2)/2",
        },
        "architectures": architectures,
        "comparison": comparison,
        "head_material_matrix": material_matrix(),
        "head_material_selection": {
            "selected": None,
            "reason": "Aucun candidat ne fournit la carte chaude route/machine/orientation complète requise; Aheadd HT1 traitement #2 et A20X ne sont que des points de criblage à 250 °C.",
            "coupon_plan_required": True,
        },
        "component_material_screen": {
            "intake_valve": {
                "candidate": "Ti_6Al_4V_forged_or_wrought_purchased",
                "source": "SRC-TIMET-TI64-PHYSICAL-PROPERTIES",
                "printed": False,
                "selected_supplier_part": None,
                "status": "candidate_only_supplier_drawing_and_hot_fatigue_missing",
            },
            "exhaust_valve": {
                "candidate": "INCONEL_alloy_751_bar_or_forged_purchased",
                "source": "SRC-SPECIAL-METALS-INCONEL-751",
                "printed": False,
                "selected_supplier_part": None,
                "status": "candidate_only_supplier_drawing_and_valve_process_route_missing",
            },
            "nimonic_exhaust_alternative": {
                "candidate": None,
                "source": None,
                "printed": False,
                "selected_supplier_part": None,
                "status": "not_scored_no_tracked_official_manufacturer_record",
            },
            "spring": {
                "candidate": "ultra_clean_CrSi_oil_tempered_nitrided_shot_peened_purchased",
                "source": "SRC-MAHLE-VALVETRAIN-TECHNICAL-2025_generic_only",
                "printed": False,
                "selected_supplier_part": None,
                "status": "research_hypothesis_no_supplier_curve_or_surge_map",
            },
            "seats_and_guides": {
                "candidate": "purchased_powder_metal_inserts_finish_machined",
                "source": "SRC-MAHLE-VALVETRAIN-TECHNICAL-2025_generic_only",
                "printed": False,
                "selected_supplier_part": None,
                "status": "family_screen_only_press_fits_and_hot_clearances_unknown",
            },
        },
        "release_gates": release_gates,
    }


def render(report: dict[str, Any], output: Path) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle

    output.parent.mkdir(parents=True, exist_ok=True)
    figure = plt.figure(figsize=(16, 9), facecolor="#07121b")
    grid = figure.add_gridspec(1, 3, width_ratios=[1.0, 1.0, 1.15], wspace=0.20)
    colours = {"intake": "#3aa7d8", "exhaust": "#e56743"}
    for index, architecture in enumerate(("2v", "4v")):
        axis = figure.add_subplot(grid[0, index], facecolor="#0d1d29")
        data = report["architectures"][architecture]
        axis.add_patch(Circle((0.0, 0.0), BORE_RADIUS_MM, fill=False, linewidth=3.0, edgecolor="#eef5f8"))
        for family, valve in data["valves"].items():
            for centre in valve["centres_xy_mm"]:
                axis.add_patch(
                    Circle(
                        centre,
                        valve["seat_envelope_diameter_mm"] / 2.0,
                        facecolor=colours[family],
                        edgecolor="#f9fbfc",
                        linewidth=1.5,
                        alpha=0.78,
                    )
                )
                axis.add_patch(
                    Circle(
                        centre,
                        valve["head_diameter_mm"] / 2.0,
                        fill=False,
                        edgecolor="#07121b",
                        linewidth=1.3,
                    )
                )
        plug = data["packing"]["plug_package"]
        if plug:
            axis.add_patch(
                Circle(
                    plug["centre_xy_mm"],
                    plug["diameter_mm"] / 2.0,
                    facecolor="#f3c45a",
                    edgecolor="#07121b",
                    linewidth=1.2,
                )
            )
        axis.set_aspect("equal", adjustable="box")
        axis.set_xlim(-50, 50)
        axis.set_ylim(-50, 50)
        axis.set_xticks([-45, 0, 45])
        axis.set_yticks([-45, 0, 45])
        axis.tick_params(colors="#9eb2bf")
        axis.grid(color="#25404f", linewidth=0.5, alpha=0.5)
        axis.set_title(
            f"{architecture.upper()} — paquetage circulaire\n"
            f"bord siège {data['packing']['minimum_bore_edge_gap_mm']:.2f} mm · pont {data['packing']['minimum_seat_to_seat_gap_mm']:.2f} mm",
            color="white",
            fontsize=11,
            fontweight="bold",
        )
        axis.set_xlabel("x [mm]", color="#9eb2bf")
        axis.set_ylabel("y [mm]", color="#9eb2bf")
    table_axis = figure.add_subplot(grid[0, 2], facecolor="#0d1d29")
    table_axis.axis("off")
    two = report["architectures"]["2v"]
    four = report["architectures"]["4v"]
    rows = [
        ["Aire adm. eff. [mm²]", f"{two['valves']['intake']['flow']['effective_area_at_cd_0_72_mm2']:.1f}", f"{four['valves']['intake']['flow']['effective_area_at_cd_0_72_mm2']:.1f}"],
        ["Aire éch. eff. [mm²]", f"{two['valves']['exhaust']['flow']['effective_area_at_cd_0_72_mm2']:.1f}", f"{four['valves']['exhaust']['flow']['effective_area_at_cd_0_72_mm2']:.1f}"],
        ["Masse soupapes [g]", f"{1000*two['total_valve_mass_kg']:.1f}", f"{1000*four['total_valve_mass_kg']:.1f}"],
        ["Accél. adm. [m/s²]", f"{two['valves']['intake']['maximum_acceleration_m_s2']:.0f}", f"{four['valves']['intake']['maximum_acceleration_m_s2']:.0f}"],
        ["Marge ressort adm.", f"{two['valves']['intake']['spring']['open_force_to_combined_load_margin']:.2f}", f"{four['valves']['intake']['spring']['open_force_to_combined_load_margin']:.2f}"],
        ["Marge ressort éch.", f"{two['valves']['exhaust']['spring']['open_force_to_combined_load_margin']:.2f}", f"{four['valves']['exhaust']['spring']['open_force_to_combined_load_margin']:.2f}"],
        ["Wahl max [MPa]", f"{max(two['valves']['intake']['spring']['maximum_wahl_corrected_shear_mpa'], two['valves']['exhaust']['spring']['maximum_wahl_corrected_shear_mpa']):.0f}", f"{max(four['valves']['intake']['spring']['maximum_wahl_corrected_shear_mpa'], four['valves']['exhaust']['spring']['maximum_wahl_corrected_shear_mpa']):.0f}"],
    ]
    table = table_axis.table(cellText=rows, colLabels=["Écran analytique", "2V", "4V"], cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.0, 1.9)
    for (row, _column), cell in table.get_celld().items():
        cell.set_edgecolor("#365263")
        cell.set_facecolor("#152b38" if row else "#213d4c")
        cell.get_text().set_color("white")
    table_axis.text(
        0.5,
        0.78,
        "Dimensionnement F45\nhypothèses non libérées",
        ha="center",
        va="center",
        color="white",
        fontsize=13,
        fontweight="bold",
        transform=table_axis.transAxes,
    )
    figure.suptitle(
        "Porsche 917/30 F45 — ALÉSAGE STRICTEMENT CIRCULAIRE Ø90 mm",
        color="white",
        fontsize=22,
        fontweight="bold",
        y=0.97,
    )
    figure.text(
        0.5,
        0.92,
        "Vue en plan des éléments fonctionnels uniquement — enveloppe scan-contour inchangée — aucune géométrie de corps synthétique",
        ha="center",
        color="#80c8e8",
        fontsize=11,
    )
    figure.text(
        0.5,
        0.025,
        "ÉCRAN ANALYTIQUE NON CORRÉLÉ · COTES D'INTERFACE PORSCHE INCONNUES · IMPRESSION ET DÉMARRAGE INTERDITS",
        ha="center",
        color="#ff9c8c",
        fontsize=11,
        fontweight="bold",
    )
    figure.savefig(
        output,
        dpi=160,
        facecolor=figure.get_facecolor(),
        metadata={"Software": "3dprinting993 F45 deterministic analytical screen"},
    )
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--image", type=Path, default=IMAGE_PATH)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--no-render", action="store_true")
    args = parser.parse_args()
    root = args.project_root.resolve()
    report = build_report(root)
    output = args.output if args.output.is_absolute() else root / args.output
    image = args.image if args.image.is_absolute() else root / args.image
    serialized = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != serialized:
            raise SystemExit("stale_or_missing_f45_valvetrain_material_report")
        if not args.no_render and (not image.is_file() or image.stat().st_size == 0):
            raise SystemExit("missing_f45_valvetrain_material_image")
        print(json.dumps({"status": "ok", "report": str(output), "image": str(image)}, sort_keys=True))
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(serialized, encoding="utf-8")
    if not args.no_render:
        render(report, image)
    print(json.dumps({"status": report["status"], "report": str(output), "image": str(image)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
