#!/usr/bin/env python3
"""Roue de compresseur K16 993, concept AlSi10Mg LPBF F0."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-K16-COMPRESSOR-WHEEL-ALSI10MG-F0-0001"

# Donnees fournisseur publiees pour le K16 droit BorgWarner 53169886735.
PUBLISHED_COMPRESSOR_INDUCER_DIAMETER_MM = 40.6
PUBLISHED_COMPRESSOR_EXDUCER_DIAMETER_MM = 60.5
PUBLISHED_MAIN_BLADE_COUNT = 6
PUBLISHED_SPLITTER_BLADE_COUNT = 6
PUBLISHED_COMPRESSOR_WHEEL_REFERENCE = "53241232006"
PUBLISHED_TURBO_REFERENCE = "53169886735"

# Topologie F0 independante : aucune pale ni surface BorgWarner n'est reprise.
BACKPLATE_DIAMETER_MM = PUBLISHED_COMPRESSOR_EXDUCER_DIAMETER_MM
BACKPLATE_THICKNESS_MM = 3.0
TOTAL_HEIGHT_MM = 18.0
BORE_DIAMETER_MM = 6.0
HUB_BOTTOM_RADIUS_MM = 8.0
HUB_TOP_RADIUS_MM = 4.0
MAIN_BLADE_INNER_RADIUS_MM = 7.0
MAIN_BLADE_HEIGHT_MM = 11.0
SPLITTER_BLADE_INNER_RADIUS_MM = 16.0
SPLITTER_BLADE_HEIGHT_MM = 7.0
BLADE_THICKNESS_MM = 1.2
BLADE_BASE_Z_MM = 2.5
INDUCER_HUB_DIAMETER_MM = 12.0

# EOS AlSi10Mg : valeurs generiques de criblage, pas des admissibles rotor.
DENSITY_KG_M3 = 2670.0
ELASTIC_MODULUS_PA = 70.0e9
POISSON_RATIO = 0.33
COMPARISON_YIELD_STRENGTH_PA = 245.0e6
THERMAL_EXPANSION_PER_K = 21.0e-6
SPECIFIC_HEAT_J_KG_K = 900.0

# Cas synthetique aero-thermo-mecanique.
AIR_GAMMA = 1.4
AIR_GAS_CONSTANT_J_KG_K = 287.05
AIR_CP_J_KG_K = 1005.0
AIR_DYNAMIC_VISCOSITY_PA_S = 1.9e-5
INLET_TEMPERATURE_K = 330.0
INLET_ABSOLUTE_PRESSURE_PA = 180_000.0
TARGET_TIP_MACH = 0.90
PRESSURE_RATIO = 1.80
ISENTROPIC_EFFICIENCY = 0.72
ENGINE_DISPLACEMENT_L = 3.6
ENGINE_SPEED_RPM = 5750.0
ENGINE_VOLUMETRIC_EFFICIENCY = 0.95
STRESS_CONCENTRATION_FACTOR = 2.0
OVERSPEED_FACTOR = 1.20
THERMAL_DELTA_T_K = 150.0
RESIDUAL_UNBALANCE_MG_MM = 10.0
SCREEN_DUTY_HOURS = 100.0


def _blade_volume_mm3(inner_radius_mm: float, height_mm: float) -> float:
    return (
        (PUBLISHED_COMPRESSOR_EXDUCER_DIAMETER_MM / 2.0 - inner_radius_mm)
        * BLADE_THICKNESS_MM
        * height_mm
    )


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    cad_mass_kg = (
        cad_volume_mm3 / 1.0e9 * DENSITY_KG_M3
        if cad_volume_mm3 is not None
        else None
    )
    load_mass_kg = cad_mass_kg if cad_mass_kg is not None else 0.035
    radius_m = PUBLISHED_COMPRESSOR_EXDUCER_DIAMETER_MM / 2000.0
    cylindrical_stock_volume_mm3 = (
        math.pi
        * (PUBLISHED_COMPRESSOR_EXDUCER_DIAMETER_MM / 2.0) ** 2
        * TOTAL_HEIGHT_MM
    )
    cylindrical_stock_mass_kg = cylindrical_stock_volume_mm3 / 1.0e9 * DENSITY_KG_M3

    sound_speed_m_s = math.sqrt(AIR_GAMMA * AIR_GAS_CONSTANT_J_KG_K * INLET_TEMPERATURE_K)
    tip_speed_m_s = TARGET_TIP_MACH * sound_speed_m_s
    angular_speed_rad_s = tip_speed_m_s / radius_m
    shaft_speed_rpm = angular_speed_rad_s * 60.0 / (2.0 * math.pi)
    shaft_frequency_hz = shaft_speed_rpm / 60.0
    centrifugal_acceleration_m_s2 = angular_speed_rad_s**2 * radius_m

    density_air_kg_m3 = INLET_ABSOLUTE_PRESSURE_PA / (
        AIR_GAS_CONSTANT_J_KG_K * INLET_TEMPERATURE_K
    )
    total_engine_flow_m3_s = (
        ENGINE_DISPLACEMENT_L
        / 1000.0
        * ENGINE_SPEED_RPM
        / (2.0 * 60.0)
        * ENGINE_VOLUMETRIC_EFFICIENCY
    )
    bank_flow_m3_s = total_engine_flow_m3_s / 2.0
    inducer_area_m2 = math.pi / 4.0 * (
        (PUBLISHED_COMPRESSOR_INDUCER_DIAMETER_MM / 1000.0) ** 2
        - (INDUCER_HUB_DIAMETER_MM / 1000.0) ** 2
    )
    inducer_axial_velocity_m_s = bank_flow_m3_s / inducer_area_m2
    inducer_axial_mach = inducer_axial_velocity_m_s / sound_speed_m_s
    flow_coefficient = inducer_axial_velocity_m_s / tip_speed_m_s
    inducer_reynolds = (
        density_air_kg_m3
        * inducer_axial_velocity_m_s
        * (PUBLISHED_COMPRESSOR_INDUCER_DIAMETER_MM / 1000.0)
        / AIR_DYNAMIC_VISCOSITY_PA_S
    )
    bank_mass_flow_kg_s = density_air_kg_m3 * bank_flow_m3_s
    isentropic_outlet_temperature_k = INLET_TEMPERATURE_K * PRESSURE_RATIO ** (
        (AIR_GAMMA - 1.0) / AIR_GAMMA
    )
    efficiency_adjusted_outlet_temperature_k = INLET_TEMPERATURE_K + (
        isentropic_outlet_temperature_k - INLET_TEMPERATURE_K
    ) / ISENTROPIC_EFFICIENCY
    specific_compressor_work_j_kg = AIR_CP_J_KG_K * (
        efficiency_adjusted_outlet_temperature_k - INLET_TEMPERATURE_K
    )
    compressor_power_w = bank_mass_flow_kg_s * specific_compressor_work_j_kg
    compressor_torque_nm = compressor_power_w / angular_speed_rad_s

    disk_stress_pa = (
        (3.0 + POISSON_RATIO)
        / 8.0
        * DENSITY_KG_M3
        * angular_speed_rad_s**2
        * radius_m**2
    )
    overspeed_disk_stress_pa = disk_stress_pa * OVERSPEED_FACTOR**2

    main_blade_volume_mm3 = _blade_volume_mm3(
        MAIN_BLADE_INNER_RADIUS_MM, MAIN_BLADE_HEIGHT_MM
    )
    splitter_blade_volume_mm3 = _blade_volume_mm3(
        SPLITTER_BLADE_INNER_RADIUS_MM, SPLITTER_BLADE_HEIGHT_MM
    )
    main_blade_mass_kg = main_blade_volume_mm3 / 1.0e9 * DENSITY_KG_M3
    splitter_blade_mass_kg = splitter_blade_volume_mm3 / 1.0e9 * DENSITY_KG_M3
    main_blade_mean_radius_m = (
        MAIN_BLADE_INNER_RADIUS_MM
        + PUBLISHED_COMPRESSOR_EXDUCER_DIAMETER_MM / 2.0
    ) / 2000.0
    splitter_blade_mean_radius_m = (
        SPLITTER_BLADE_INNER_RADIUS_MM
        + PUBLISHED_COMPRESSOR_EXDUCER_DIAMETER_MM / 2.0
    ) / 2000.0
    main_blade_centrifugal_force_n = (
        main_blade_mass_kg * angular_speed_rad_s**2 * main_blade_mean_radius_m
    )
    splitter_blade_centrifugal_force_n = (
        splitter_blade_mass_kg
        * angular_speed_rad_s**2
        * splitter_blade_mean_radius_m
    )
    main_blade_root_area_mm2 = BLADE_THICKNESS_MM * MAIN_BLADE_HEIGHT_MM
    splitter_blade_root_area_mm2 = BLADE_THICKNESS_MM * SPLITTER_BLADE_HEIGHT_MM
    main_blade_root_stress_pa = (
        STRESS_CONCENTRATION_FACTOR
        * main_blade_centrifugal_force_n
        / main_blade_root_area_mm2
        * 1.0e6
    )
    splitter_blade_root_stress_pa = (
        STRESS_CONCENTRATION_FACTOR
        * splitter_blade_centrifugal_force_n
        / splitter_blade_root_area_mm2
        * 1.0e6
    )
    governing_root_stress_pa = max(main_blade_root_stress_pa, splitter_blade_root_stress_pa)
    overspeed_governing_root_stress_pa = governing_root_stress_pa * OVERSPEED_FACTOR**2

    disk_radial_growth_mm = disk_stress_pa / ELASTIC_MODULUS_PA * radius_m * 1000.0
    free_thermal_radius_growth_mm = (
        THERMAL_EXPANSION_PER_K * radius_m * THERMAL_DELTA_T_K * 1000.0
    )
    fully_constrained_thermal_stress_pa = (
        ELASTIC_MODULUS_PA * THERMAL_EXPANSION_PER_K * THERMAL_DELTA_T_K
    )
    approximate_polar_inertia_kg_m2 = 0.5 * load_mass_kg * radius_m**2
    approximate_rotational_energy_j = (
        0.5 * approximate_polar_inertia_kg_m2 * angular_speed_rad_s**2
    )
    residual_unbalance_kg_m = RESIDUAL_UNBALANCE_MG_MM * 1.0e-9
    residual_unbalance_force_n = residual_unbalance_kg_m * angular_speed_rad_s**2
    revolutions_at_duty = shaft_frequency_hz * SCREEN_DUTY_HOURS * 3600.0

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_published_diameters_clean_sheet_alsi10mg_impeller_screen_only",
        "geometry_authority": {
            "published": {
                "compressor_wheel_reference": PUBLISHED_COMPRESSOR_WHEEL_REFERENCE,
                "right_turbo_reference": PUBLISHED_TURBO_REFERENCE,
                "inducer_diameter_mm": PUBLISHED_COMPRESSOR_INDUCER_DIAMETER_MM,
                "exducer_diameter_mm": PUBLISHED_COMPRESSOR_EXDUCER_DIAMETER_MM,
                "main_blade_count": PUBLISHED_MAIN_BLADE_COUNT,
                "splitter_blade_count": PUBLISHED_SPLITTER_BLADE_COUNT,
            },
            "interpretations": [
                "40.6 and 60.5 mm are treated as inducer and exducer diameters exactly as labelled by the supplier",
                "6+6 is interpreted as six full blades and six splitter blades",
                "AlSi10Mg is a separate LPBF candidate; the BorgWarner wheel alloy and process are not published",
            ],
            "hypotheses": [
                "60.5 mm by 3 mm backplate and 18 mm total height",
                "6 mm through bore and conical 8-to-4 mm hub radii",
                "six straight 1.2 by 11 mm main blades starting at radius 7 mm",
                "six straight 1.2 by 7 mm splitters starting at radius 16 mm",
                "12 mm inducer hub diameter used only for the flow-area screen",
                "no blade camber, sweep, twist, fillet, balance cut, nut, shaft fit or tip clearance",
            ],
            "not_claimed": "No BorgWarner, Porsche, K16 or production compressor wheel blade profile, hub, bore, balance, fit, material, map or burst capability is claimed.",
        },
        "synthetic_operating_case": {
            "target_tip_mach": TARGET_TIP_MACH,
            "inlet_temperature_k": INLET_TEMPERATURE_K,
            "inlet_absolute_pressure_pa": INLET_ABSOLUTE_PRESSURE_PA,
            "pressure_ratio": PRESSURE_RATIO,
            "isentropic_efficiency": ISENTROPIC_EFFICIENCY,
            "engine_displacement_l": ENGINE_DISPLACEMENT_L,
            "engine_speed_rpm": ENGINE_SPEED_RPM,
            "engine_volumetric_efficiency": ENGINE_VOLUMETRIC_EFFICIENCY,
            "overspeed_factor": OVERSPEED_FACTOR,
            "thermal_delta_t_k": THERMAL_DELTA_T_K,
            "residual_unbalance_mg_mm": RESIDUAL_UNBALANCE_MG_MM,
            "duty_hours": SCREEN_DUTY_HOURS,
            "authority": "regression inputs only; no target shaft-speed trace, compressor map, inlet state, balance grade, clearance, temperature or duty cycle was measured",
        },
        "material_screen": {
            "candidate": "EOS Aluminium AlSi10Mg LPBF, study only",
            "density_kg_m3": DENSITY_KG_M3,
            "elastic_modulus_pa": ELASTIC_MODULUS_PA,
            "poisson_ratio": POISSON_RATIO,
            "comparison_yield_strength_pa": COMPARISON_YIELD_STRENGTH_PA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "specific_heat_j_kg_k": SPECIFIC_HEAT_J_KG_K,
            "scope": "generic room-temperature screening values; no rotating polished-surface, temperature, HCF, defect, overspeed or burst allowable",
        },
        "results": {
            "cad_volume_mm3": cad_volume_mm3,
            "cad_mass_g": cad_mass_kg * 1000.0 if cad_mass_kg is not None else None,
            "cylindrical_stock_volume_mm3": cylindrical_stock_volume_mm3,
            "cylindrical_stock_mass_g": cylindrical_stock_mass_kg * 1000.0,
            "cylindrical_stock_to_cad_mass_ratio": (
                cylindrical_stock_mass_kg / cad_mass_kg if cad_mass_kg else None
            ),
            "sound_speed_m_s": sound_speed_m_s,
            "tip_speed_m_s": tip_speed_m_s,
            "derived_shaft_speed_rpm": shaft_speed_rpm,
            "shaft_frequency_hz": shaft_frequency_hz,
            "centrifugal_tip_acceleration_m_s2": centrifugal_acceleration_m_s2,
            "air_density_kg_m3": density_air_kg_m3,
            "bank_volume_flow_m3_s": bank_flow_m3_s,
            "bank_mass_flow_kg_s": bank_mass_flow_kg_s,
            "inducer_annulus_area_m2": inducer_area_m2,
            "inducer_axial_velocity_m_s": inducer_axial_velocity_m_s,
            "inducer_axial_mach": inducer_axial_mach,
            "flow_coefficient": flow_coefficient,
            "inducer_reynolds": inducer_reynolds,
            "isentropic_outlet_temperature_k": isentropic_outlet_temperature_k,
            "efficiency_adjusted_outlet_temperature_k": efficiency_adjusted_outlet_temperature_k,
            "specific_compressor_work_j_kg": specific_compressor_work_j_kg,
            "screening_compressor_power_w": compressor_power_w,
            "screening_compressor_torque_nm": compressor_torque_nm,
            "rotating_disk_stress_mpa": disk_stress_pa / 1.0e6,
            "overspeed_rotating_disk_stress_mpa": overspeed_disk_stress_pa / 1.0e6,
            "ambient_yield_to_overspeed_disk_stress_ratio": COMPARISON_YIELD_STRENGTH_PA / overspeed_disk_stress_pa,
            "main_blade_volume_mm3": main_blade_volume_mm3,
            "splitter_blade_volume_mm3": splitter_blade_volume_mm3,
            "main_blade_centrifugal_force_n": main_blade_centrifugal_force_n,
            "splitter_blade_centrifugal_force_n": splitter_blade_centrifugal_force_n,
            "main_blade_root_stress_mpa": main_blade_root_stress_pa / 1.0e6,
            "splitter_blade_root_stress_mpa": splitter_blade_root_stress_pa / 1.0e6,
            "governing_blade_root_stress_mpa": governing_root_stress_pa / 1.0e6,
            "overspeed_governing_blade_root_stress_mpa": overspeed_governing_root_stress_pa / 1.0e6,
            "ambient_yield_to_overspeed_blade_root_stress_ratio": COMPARISON_YIELD_STRENGTH_PA / overspeed_governing_root_stress_pa,
            "elastic_disk_radius_growth_mm": disk_radial_growth_mm,
            "free_thermal_radius_growth_mm": free_thermal_radius_growth_mm,
            "screening_combined_radius_growth_mm": disk_radial_growth_mm + free_thermal_radius_growth_mm,
            "fully_constrained_thermal_stress_mpa": fully_constrained_thermal_stress_pa / 1.0e6,
            "ambient_yield_to_constrained_thermal_ratio": COMPARISON_YIELD_STRENGTH_PA / fully_constrained_thermal_stress_pa,
            "approximate_polar_inertia_kg_m2": approximate_polar_inertia_kg_m2,
            "approximate_rotational_energy_j": approximate_rotational_energy_j,
            "residual_unbalance_force_n": residual_unbalance_force_n,
            "main_blade_pass_frequency_hz": PUBLISHED_MAIN_BLADE_COUNT * shaft_frequency_hz,
            "all_blade_pass_frequency_hz": (PUBLISHED_MAIN_BLADE_COUNT + PUBLISHED_SPLITTER_BLADE_COUNT) * shaft_frequency_hz,
            "revolutions_at_duty": revolutions_at_duty,
        },
        "equations": {
            "mass": "m=rho*Vcad",
            "speed_of_sound": "a=sqrt(gamma*R*T)",
            "tip_speed_and_rpm": "U=Mtip*a; omega=U/r; N=omega*60/(2*pi)",
            "engine_bank_flow": "Qbank=Vd*Nengine/(2*60)*VE/2",
            "continuity": "Ca=Qbank/Ainducer; mdot=rho_air*Qbank",
            "ideal_gas": "rho_air=p/(R*T)",
            "compressor_temperature": "T2s=T1*PR^((gamma-1)/gamma); T2=T1+(T2s-T1)/eta",
            "compressor_power": "w=cp*(T2-T1); P=mdot*w; torque=P/omega",
            "rotating_disk": "sigma=(3+nu)/8*rho*omega^2*r^2",
            "blade_centrifugal": "F=m_blade*omega^2*r_mean; sigma_root=Kt*F/Aroot",
            "overspeed": "sigma_over=sigma*factor^2",
            "elastic_growth": "delta_r=sigma/E*r",
            "thermal_growth": "delta_r=alpha*r*delta_T",
            "fully_constrained_thermal": "sigma=E*alpha*delta_T",
            "rotational_energy": "Erot=0.5*I*omega^2; Iapprox=0.5*m*r^2",
            "unbalance": "F=U_residual*omega^2",
            "blade_pass": "f_bpf=Z*N/60",
            "revolutions": "n=N/60*t_seconds",
        },
        "dfam_screen": {
            "additive_value": "twelve integral blades and hub can be iterated without casting tooling, while future load-shaped or internally cooled features remain possible",
            "open_blade_topology": True,
            "trapped_powder_volume": False,
            "main_blade_count": PUBLISHED_MAIN_BLADE_COUNT,
            "splitter_blade_count": PUBLISHED_SPLITTER_BLADE_COUNT,
            "minimum_nominal_blade_thickness_mm": BLADE_THICKNESS_MM,
            "orientation_selected": False,
            "support_strategy_defined": False,
            "bore_backface_and_balance_features_require_machining": True,
            "process_comparison_required": [
                "qualified cast aluminium compressor wheel",
                "five-axis machined billet aluminium compressor wheel",
                "LPBF AlSi10Mg wheel with post-machining and full overspeed/burst qualification",
            ],
        },
        "interpretation": {
            "geometry": "straight prismatic F0 blades are topology markers and not aerodynamic profiles",
            "aerodynamics": "one-point continuity and ideal-gas compression omit maps, slip, diffusion, incidence, choking, surge, leakage and housing interaction",
            "mechanics": "rotating-disk and lumped blade-root equations omit real blade curvature, fillets, bore fit, nut preload, plasticity, defects and rotor dynamics",
            "thermal": "free and fully constrained bounds are not a coupled transient wheel solution",
            "energy": "polar inertia uses a solid-disk approximation, not the CAD mass distribution or a containment result",
            "fatigue": "revolutions are counted without life because no qualified AlSi10Mg rotor HCF or defect card exists",
            "physicsnemo": "deferred until correlated CFD, thermal-structure, rotor-dynamic and burst cases define train, holdout and OOD sets",
            "simready": "deferred until compressor housing, shaft, nut, backplate, diffuser, clearances and balance datums are measured",
        },
        "release_blockers": [
            "No measured K16 compressor wheel, scan, CAD surface, blade camber, sweep, twist, fillet, height, hub, bore or balance feature.",
            "The published 40.6/60.5 mm and 6+6 count do not define an aerodynamic or manufacturing geometry.",
            "No evidence that BorgWarner wheel 53241232006 uses AlSi10Mg, LPBF or the assumed 6 mm bore.",
            "No measured compressor map, shaft-speed trace, inlet state, pressure ratio, efficiency, surge, choke or transient duty.",
            "No measured turbine power balance, bearing losses, shaft torque, acceleration or overspeed requirement.",
            "No compressor housing, diffuser, backplate, shaft, nut, thrust system, tip clearance, axial clearance or interference fit.",
            "No 3D rotating CFD, mesh convergence, blade loading, fluid-structure coupling or housing interaction.",
            "No nonlinear rotating FEA, contact/preload, rotor dynamics, Campbell diagram, modal, fracture, HCF or probabilistic burst analysis.",
            "The straight 1.2 mm blades fail the ambient overspeed root-stress screen and require redesign before any higher-fidelity model.",
            "No AlSi10Mg temperature-dependent strength, HCF, fracture, defect, surface, corrosion or creep card for the exact route.",
            "No qualified orientation, supports, recoater strategy, distortion compensation, heat treatment, HIP decision or machining stock.",
            "No CT, metallography, dimensional inspection, surface finish, balance, spin proof, overspeed, burst or containment test.",
            "No validated compatibility with left/right K16 variants, housing clocking, charge plumbing or engine calibration.",
            "No professional turbo machinery review, approved validation plan, dyno authorization or vehicle release.",
        ],
        "manufacturing_authorized": False,
        "turbo_operation_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


def build_geometry():
    from build123d import Align, Box, Cone, Cylinder, Pos, Rot

    outer_radius_mm = PUBLISHED_COMPRESSOR_EXDUCER_DIAMETER_MM / 2.0
    backplate = Cylinder(
        outer_radius_mm,
        BACKPLATE_THICKNESS_MM,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    hub = Pos(0.0, 0.0, BACKPLATE_THICKNESS_MM - 0.5) * Cone(
        HUB_BOTTOM_RADIUS_MM,
        HUB_TOP_RADIUS_MM,
        TOTAL_HEIGHT_MM - BACKPLATE_THICKNESS_MM + 0.5,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    blade_clip = Pos(0.0, 0.0, BLADE_BASE_Z_MM) * Cylinder(
        outer_radius_mm,
        max(MAIN_BLADE_HEIGHT_MM, SPLITTER_BLADE_HEIGHT_MM),
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )

    blades = None
    for index in range(PUBLISHED_MAIN_BLADE_COUNT):
        length_mm = outer_radius_mm - MAIN_BLADE_INNER_RADIUS_MM
        center_radius_mm = (outer_radius_mm + MAIN_BLADE_INNER_RADIUS_MM) / 2.0
        blade = Rot(0.0, 0.0, index * 360.0 / PUBLISHED_MAIN_BLADE_COUNT) * (
            Pos(center_radius_mm, 0.0, BLADE_BASE_Z_MM + MAIN_BLADE_HEIGHT_MM / 2.0)
            * Box(
                length_mm,
                BLADE_THICKNESS_MM,
                MAIN_BLADE_HEIGHT_MM,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )
        )
        blades = blade if blades is None else blades + blade

    for index in range(PUBLISHED_SPLITTER_BLADE_COUNT):
        length_mm = outer_radius_mm - SPLITTER_BLADE_INNER_RADIUS_MM
        center_radius_mm = (outer_radius_mm + SPLITTER_BLADE_INNER_RADIUS_MM) / 2.0
        angle_deg = (
            index * 360.0 / PUBLISHED_SPLITTER_BLADE_COUNT
            + 180.0 / PUBLISHED_SPLITTER_BLADE_COUNT
        )
        blade = Rot(0.0, 0.0, angle_deg) * (
            Pos(center_radius_mm, 0.0, BLADE_BASE_Z_MM + SPLITTER_BLADE_HEIGHT_MM / 2.0)
            * Box(
                length_mm,
                BLADE_THICKNESS_MM,
                SPLITTER_BLADE_HEIGHT_MM,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )
        )
        blades = blade if blades is None else blades + blade

    assert blades is not None
    body = backplate + hub + (blades & blade_clip)
    bore = Pos(0.0, 0.0, -1.0) * Cylinder(
        BORE_DIAMETER_MM / 2.0,
        TOTAL_HEIGHT_MM + 2.0,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    return body - bore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    cad_volume_mm3 = None
    envelope = None
    if args.out:
        from build123d import export_step, import_step

        shape = build_geometry()
        if not shape.is_valid or len(shape.solids()) != 1:
            raise SystemExit("Le F0 doit contenir exactement un solide BREP valide.")
        bbox = shape.bounding_box()
        envelope = [bbox.size.X, bbox.size.Y, bbox.size.Z]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        export_step(shape, str(args.out))
        roundtrip = import_step(str(args.out))
        if not roundtrip.is_valid or len(roundtrip.solids()) != 1:
            raise SystemExit("Le STEP relu ne conserve pas le solide valide.")
        if abs(roundtrip.volume - shape.volume) > 0.05:
            raise SystemExit("Le STEP relu ne reproduit pas le volume OCCT attendu.")
        cad_volume_mm3 = roundtrip.volume

    report = engineering_screen(cad_volume_mm3)
    if args.out and envelope is not None:
        report["step_roundtrip"] = {
            "status": "passed",
            "valid_brep": True,
            "solid_count": 1,
            "semantic_solids": ["clean_sheet_k16_compressor_wheel_topology"],
            "volume_mm3": cad_volume_mm3,
            "envelope_mm": envelope,
            "main_blade_count": PUBLISHED_MAIN_BLADE_COUNT,
            "splitter_blade_count": PUBLISHED_SPLITTER_BLADE_COUNT,
            "through_bore_count": 1,
            "minimum_nominal_blade_thickness_mm": BLADE_THICKNESS_MM,
            "maximum_volume_delta_mm3": 0.05,
        }

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
