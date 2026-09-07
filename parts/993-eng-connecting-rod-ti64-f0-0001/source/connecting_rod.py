#!/usr/bin/env python3
"""Bielle 993/993 Turbo, concept topologique Ti-6Al-4V LPBF F0."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-CONNECTING-ROD-TI64-F0-0001"

# Valeurs publiées par TZR/PAUTER pour la bielle acier et son option titane.
PUBLISHED_CENTER_DISTANCE_MM = 127.0
PUBLISHED_PISTON_PIN_DIAMETER_MM = 23.01
PUBLISHED_BIG_END_HOUSING_DIAMETER_MM = 58.01
PUBLISHED_BIG_END_WIDTH_MM = 18.75
PUBLISHED_SMALL_END_WIDTH_MM = 19.58
PUBLISHED_STEEL_MASS_G = 535.0
PUBLISHED_TITANIUM_MASS_REDUCTION_RATIO = 0.33
PUBLISHED_BIG_END_DIAMETER_TOLERANCE_MM = 0.003

# Enveloppe topologique F0 indépendante : aucune forme PAUTER n'est reproduite.
BIG_END_OUTER_DIAMETER_MM = 78.0
SMALL_END_OUTER_DIAMETER_MM = 40.0
STRUT_WIDTH_MM = 10.0
STRUT_THICKNESS_MM = 14.0
STRUT_OVERLAP_MM = 8.0
BIG_STRUT_X_MM = 25.0
BIG_STRUT_Y_MM = 20.0
SMALL_STRUT_X_MM = 110.0
SMALL_STRUT_Y_MM = 10.0
CAP_SPLIT_GAP_MM = 0.4
BOLT_AXIS_Y_MM = 36.0
BOLT_CLEARANCE_DIAMETER_MM = 8.4
BOLT_LUG_LENGTH_X_MM = 28.0
BOLT_LUG_WIDTH_Y_MM = 12.0
BOLT_LUG_THICKNESS_MM = PUBLISHED_BIG_END_WIDTH_MM

# Cas de charge synthétique, pas une donnée M64/60 mesurée.
ENGINE_BORE_MM = 100.0
ENGINE_STROKE_MM = 76.4
ENGINE_SPEED_RPM = 6720.0
PEAK_CYLINDER_PRESSURE_MPA = 12.0
PISTON_AND_PIN_MASS_G = 600.0
ROD_RECIPROCATING_MASS_FRACTION = 1.0 / 3.0
SYNTHETIC_DUTY_HOURS = 100.0
STRESS_CONCENTRATION_FACTOR = 1.5
EULER_EFFECTIVE_LENGTH_FACTOR = 1.0
SCREEN_DELTA_T_K = 100.0

# EOS Ti64 Grade 5 : valeurs typiques de criblage, jamais des admissibles bielle.
DENSITY_G_CM3 = 4.42
ELASTIC_MODULUS_MPA = 110_000.0
COMPARISON_YIELD_STRENGTH_MPA = 980.0
COMPARISON_ULTIMATE_STRENGTH_MPA = 1080.0
THERMAL_EXPANSION_PER_K = 9.0e-6
SPECIFIC_HEAT_J_KG_K = 580.0


def published_titanium_target_mass_g() -> float:
    return PUBLISHED_STEEL_MASS_G * (1.0 - PUBLISHED_TITANIUM_MASS_REDUCTION_RATIO)


def strut_length_mm() -> float:
    return math.hypot(
        SMALL_STRUT_X_MM - BIG_STRUT_X_MM,
        BIG_STRUT_Y_MM + SMALL_STRUT_Y_MM,
    )


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    target_titanium_mass_g = published_titanium_target_mass_g()
    cad_mass_g = (
        cad_volume_mm3 / 1000.0 * DENSITY_G_CM3
        if cad_volume_mm3 is not None
        else None
    )
    load_mass_g = cad_mass_g if cad_mass_g is not None else target_titanium_mass_g

    bore_area_m2 = math.pi * (ENGINE_BORE_MM / 2000.0) ** 2
    gas_force_n = PEAK_CYLINDER_PRESSURE_MPA * 1_000_000.0 * bore_area_m2
    crank_radius_m = ENGINE_STROKE_MM / 2000.0
    rod_length_m = PUBLISHED_CENTER_DISTANCE_MM / 1000.0
    angular_speed_rad_s = 2.0 * math.pi * ENGINE_SPEED_RPM / 60.0
    tdc_acceleration_m_s2 = (
        crank_radius_m
        * angular_speed_rad_s**2
        * (1.0 + crank_radius_m / rod_length_m)
    )
    reciprocating_mass_kg = (
        PISTON_AND_PIN_MASS_G
        + ROD_RECIPROCATING_MASS_FRACTION * load_mass_g
    ) / 1000.0
    inertia_force_n = reciprocating_mass_kg * tdc_acceleration_m_s2
    conservative_compression_force_n = gas_force_n + inertia_force_n

    effective_shaft_area_mm2 = 2.0 * STRUT_WIDTH_MM * STRUT_THICKNESS_MM
    compression_stress_mpa = conservative_compression_force_n / effective_shaft_area_mm2
    tensile_stress_mpa = inertia_force_n / effective_shaft_area_mm2
    local_compression_screen_mpa = STRESS_CONCENTRATION_FACTOR * compression_stress_mpa
    local_tension_screen_mpa = STRESS_CONCENTRATION_FACTOR * tensile_stress_mpa
    alternating_stress_mpa = (
        local_compression_screen_mpa + local_tension_screen_mpa
    ) / 2.0
    mean_stress_mpa = (
        local_tension_screen_mpa - local_compression_screen_mpa
    ) / 2.0

    strut_width_m = STRUT_WIDTH_MM / 1000.0
    strut_thickness_m = STRUT_THICKNESS_MM / 1000.0
    combined_weak_axis_i_m4 = (
        2.0 * strut_width_m * strut_thickness_m**3 / 12.0
    )
    euler_length_m = strut_length_mm() / 1000.0
    euler_buckling_load_n = (
        math.pi**2
        * ELASTIC_MODULUS_MPA
        * 1_000_000.0
        * combined_weak_axis_i_m4
        / (EULER_EFFECTIVE_LENGTH_FACTOR * euler_length_m) ** 2
    )

    big_end_projected_area_m2 = (
        PUBLISHED_BIG_END_HOUSING_DIAMETER_MM
        * PUBLISHED_BIG_END_WIDTH_MM
        / 1_000_000.0
    )
    small_end_projected_area_m2 = (
        PUBLISHED_PISTON_PIN_DIAMETER_MM
        * PUBLISHED_SMALL_END_WIDTH_MM
        / 1_000_000.0
    )
    big_end_bearing_pressure_mpa = (
        conservative_compression_force_n / big_end_projected_area_m2 / 1_000_000.0
    )
    small_end_bearing_pressure_mpa = (
        conservative_compression_force_n / small_end_projected_area_m2 / 1_000_000.0
    )
    cycles = ENGINE_SPEED_RPM / 60.0 * SYNTHETIC_DUTY_HOURS * 3600.0
    free_thermal_expansion_mm = (
        THERMAL_EXPANSION_PER_K
        * PUBLISHED_CENTER_DISTANCE_MM
        * SCREEN_DELTA_T_K
    )

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_published_key_dimensions_clean_sheet_ti64_topology_screen_only",
        "geometry_authority": {
            "published": {
                "center_distance_mm": PUBLISHED_CENTER_DISTANCE_MM,
                "piston_pin_diameter_mm": PUBLISHED_PISTON_PIN_DIAMETER_MM,
                "big_end_housing_diameter_mm": PUBLISHED_BIG_END_HOUSING_DIAMETER_MM,
                "big_end_width_mm": PUBLISHED_BIG_END_WIDTH_MM,
                "small_end_width_mm": PUBLISHED_SMALL_END_WIDTH_MM,
                "steel_mass_g": PUBLISHED_STEEL_MASS_G,
                "titanium_mass_reduction_ratio": PUBLISHED_TITANIUM_MASS_REDUCTION_RATIO,
                "big_end_diameter_tolerance_mm": PUBLISHED_BIG_END_DIAMETER_TOLERANCE_MM,
                "steel_shaft_description": "X-shaft",
                "steel_material": "4340 Chrome Moly",
                "fastener_family": "ARP 2000",
            },
            "interpretations": [
                "23.01 mm product pin size used as nominal F0 small-end bore without clearance",
                "33 percent saving applied to the published 535 g steel mass as a target only",
                "Ti-6Al-4V selected from a separate EOS LPBF material family; PAUTER titanium alloy is not published",
            ],
            "hypotheses": [
                "78 mm big-end and 40 mm small-end outside diameters",
                "two open diagonal load struts, 10 x 14 mm",
                "0.4 mm visual cap split",
                "two 8.4 mm bolt passages on synthetic 36 mm offsets",
                "lug and cap geometry without threads, bolts, bearings or oil channel",
            ],
            "not_claimed": "No PAUTER surface, cap, bolt pattern, bearing fit, balance, oil path, tolerance stack or fatigue life is claimed.",
        },
        "synthetic_load_case": {
            "engine_bore_mm": ENGINE_BORE_MM,
            "engine_stroke_mm": ENGINE_STROKE_MM,
            "engine_speed_rpm": ENGINE_SPEED_RPM,
            "peak_cylinder_pressure_mpa": PEAK_CYLINDER_PRESSURE_MPA,
            "piston_and_pin_mass_g": PISTON_AND_PIN_MASS_G,
            "rod_reciprocating_mass_fraction": ROD_RECIPROCATING_MASS_FRACTION,
            "stress_concentration_factor": STRESS_CONCENTRATION_FACTOR,
            "duty_hours": SYNTHETIC_DUTY_HOURS,
            "authority": "regression inputs only; bore and stroke are documentary M64 values, while pressure, masses, speed duty and load split are not measured on the target engine",
        },
        "material_screen": {
            "candidate": "EOS Titanium Ti64 Grade 5 LPBF, study only",
            "density_g_cm3": DENSITY_G_CM3,
            "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
            "comparison_yield_strength_mpa": COMPARISON_YIELD_STRENGTH_MPA,
            "comparison_ultimate_strength_mpa": COMPARISON_ULTIMATE_STRENGTH_MPA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "specific_heat_j_kg_k": SPECIFIC_HEAT_J_KG_K,
            "scope": "typical EOS strength plus wrought TIMET physical references; no orientation-specific polished/HIP hot fatigue, defect or surface allowable",
        },
        "results": {
            "cad_volume_mm3": cad_volume_mm3,
            "cad_mass_g": cad_mass_g,
            "published_titanium_target_mass_g": target_titanium_mass_g,
            "cad_minus_published_target_g": (
                cad_mass_g - target_titanium_mass_g
                if cad_mass_g is not None
                else None
            ),
            "published_saving_each_g": PUBLISHED_STEEL_MASS_G - target_titanium_mass_g,
            "published_saving_six_rods_g": 6.0 * (PUBLISHED_STEEL_MASS_G - target_titanium_mass_g),
            "load_mass_basis_g": load_mass_g,
            "piston_area_m2": bore_area_m2,
            "synthetic_peak_gas_force_n": gas_force_n,
            "angular_speed_rad_s": angular_speed_rad_s,
            "synthetic_tdc_acceleration_m_s2": tdc_acceleration_m_s2,
            "synthetic_reciprocating_mass_kg": reciprocating_mass_kg,
            "synthetic_tensile_inertia_force_n": inertia_force_n,
            "conservative_compression_force_n": conservative_compression_force_n,
            "effective_shaft_area_mm2": effective_shaft_area_mm2,
            "nominal_compression_stress_mpa": compression_stress_mpa,
            "nominal_tension_stress_mpa": tensile_stress_mpa,
            "local_compression_screen_mpa": local_compression_screen_mpa,
            "local_tension_screen_mpa": local_tension_screen_mpa,
            "alternating_stress_screen_mpa": alternating_stress_mpa,
            "mean_stress_screen_mpa": mean_stress_mpa,
            "ambient_yield_to_local_compression_ratio": COMPARISON_YIELD_STRENGTH_MPA / local_compression_screen_mpa,
            "combined_weak_axis_i_m4": combined_weak_axis_i_m4,
            "euler_buckling_load_n": euler_buckling_load_n,
            "euler_to_compression_load_ratio": euler_buckling_load_n / conservative_compression_force_n,
            "big_end_projected_bearing_pressure_mpa": big_end_bearing_pressure_mpa,
            "small_end_projected_bearing_pressure_mpa": small_end_bearing_pressure_mpa,
            "load_cycles_at_duty": cycles,
            "load_cycle_frequency_hz": ENGINE_SPEED_RPM / 60.0,
            "free_center_distance_thermal_expansion_mm": free_thermal_expansion_mm,
            "lumped_heat_capacity_j_k": load_mass_g / 1000.0 * SPECIFIC_HEAT_J_KG_K,
            "strut_length_mm": strut_length_mm(),
        },
        "equations": {
            "titanium_target_mass": "m_ti_target=m_steel*(1-0.33)",
            "gas_force": "F_gas=p_peak*pi*bore^2/4",
            "tdc_acceleration": "a=r*omega^2*(1+r/L); omega=2*pi*N/60",
            "inertia_force": "F_i=(m_piston_pin+m_rod/3)*a",
            "conservative_compression": "F_comp=F_gas+F_i",
            "nominal_stress": "sigma=F/A; sigma_local=Kt*sigma",
            "stress_cycle": "sigma_a=(sigma_local_comp+sigma_local_tension)/2; sigma_m=(sigma_local_tension-sigma_local_comp)/2",
            "euler_buckling": "Pcr=pi^2*E*I/(K*L)^2",
            "projected_bearing_pressure": "p_bearing=F/(d*w)",
            "load_cycles": "n=N/60*t_seconds",
            "thermal_expansion": "delta_L=alpha*L*delta_T",
            "mass": "m=rho*Vcad",
        },
        "dfam_screen": {
            "additive_value": "open two-strut topology can be reshaped or graded from load fields without machining internal pockets",
            "open_cell_topology": True,
            "trapped_powder_volume": False,
            "minimum_nominal_strut_mm": STRUT_WIDTH_MM,
            "cap_separate_solid": True,
            "standard_fasteners_required": True,
            "bearing_and_bolt_surfaces_require_machining": True,
            "orientation_selected": False,
            "support_strategy_defined": False,
            "process_comparison_required": [
                "forged and machined 4340 steel X-shaft rod",
                "conventionally manufactured titanium rod",
                "LPBF Ti64 topology-optimized rod with machined bores and cap joint",
            ],
        },
        "interpretation": {
            "mass": "the 33 percent statement is a supplier claim for an on-request titanium rod, not validation of this Ti64 F0",
            "loads": "gas and inertia equations are screening bounds, not a crank-angle multibody or combustion solution",
            "stress": "two-strut area, Kt and Euler columns do not replace 3D contact FEA, bolt preload, bearing loads or fatigue",
            "fatigue": "mean and alternating stresses are reported without Goodman/Soderberg life because no qualified S-N or defect distribution exists",
            "academic_evidence": "published full-scale testing found the LPBF Ti64 topology-optimized rod inferior in fatigue to the conventional reference",
            "physicsnemo": "deferred until correlated crank-angle FEA and physical fatigue data define grouped train, holdout and OOD sets",
            "simready": "deferred until cap, bolts, bearings, crankpin, piston pin, cylinder and paired-rod assembly interfaces are measured",
        },
        "release_blockers": [
            "No measured PAUTER rod, CAD surface, big/small outside diameters, shaft, cap, bolt locations, oil path or mass distribution.",
            "The 23.01 mm pin size is not a published finished small-end clearance or bushing specification.",
            "The titanium option alloy, process, heat treatment, HIP, orientation and actual mass are not published.",
            "No crankshaft journal, bearing shell, pin, piston, cap-joint, bolt-stretch, side-clearance or paired-rod tolerance stack.",
            "No measured cylinder-pressure trace, reciprocating masses, overspeed case, combustion knock case or crank-angle load history.",
            "No 3D nonlinear contact FEA, mesh convergence, multiaxial fatigue, fracture, buckling, modal or oil-film analysis.",
            "No qualified LPBF Ti64 fatigue card for actual surface, pore distribution, build orientation, machining and post-treatment.",
            "No topology optimization with frozen keep-outs, load cases, manufacturing constraints and independent verification.",
            "No dimensional inspection, CT, surface finish, balance, ressuage, bolt preload, proof load or full-scale fatigue test.",
            "No professional engine engineering review, dyno validation or approved validation plan.",
        ],
        "manufacturing_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


def _cylinder_z(radius_mm: float, height_mm: float, x_mm: float = 0.0):
    from build123d import Align, Cylinder, Pos

    return Pos(x_mm, 0.0, 0.0) * Cylinder(
        radius_mm,
        height_mm,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )


def _cylinder_x(radius_mm: float, length_mm: float, y_mm: float):
    from build123d import Align, Cylinder, Pos, Rot

    return Pos(0.0, y_mm, 0.0) * Rot(0.0, 90.0, 0.0) * Cylinder(
        radius_mm,
        length_mm,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )


def _strut(start: tuple[float, float], end: tuple[float, float]):
    from build123d import Align, Box, Pos, Rot

    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy) + STRUT_OVERLAP_MM
    angle_deg = math.degrees(math.atan2(dy, dx))
    midpoint = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
    return Pos(midpoint[0], midpoint[1], 0.0) * Rot(0.0, 0.0, angle_deg) * Box(
        length,
        STRUT_WIDTH_MM,
        STRUT_THICKNESS_MM,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )


def build_geometry():
    from build123d import Align, Box, Pos

    big_outer = _cylinder_z(
        BIG_END_OUTER_DIAMETER_MM / 2.0,
        PUBLISHED_BIG_END_WIDTH_MM,
    )
    small_outer = _cylinder_z(
        SMALL_END_OUTER_DIAMETER_MM / 2.0,
        PUBLISHED_SMALL_END_WIDTH_MM,
        PUBLISHED_CENTER_DISTANCE_MM,
    )
    upper_strut = _strut(
        (BIG_STRUT_X_MM, BIG_STRUT_Y_MM),
        (SMALL_STRUT_X_MM, -SMALL_STRUT_Y_MM),
    )
    lower_strut = _strut(
        (BIG_STRUT_X_MM, -BIG_STRUT_Y_MM),
        (SMALL_STRUT_X_MM, SMALL_STRUT_Y_MM),
    )
    outer = big_outer + small_outer + upper_strut + lower_strut

    for y_mm in (-BOLT_AXIS_Y_MM, BOLT_AXIS_Y_MM):
        outer = outer + Pos(0.0, y_mm, 0.0) * Box(
            BOLT_LUG_LENGTH_X_MM,
            BOLT_LUG_WIDTH_Y_MM,
            BOLT_LUG_THICKNESS_MM,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )

    bore_overshoot_mm = 2.0
    solid = outer - _cylinder_z(
        PUBLISHED_BIG_END_HOUSING_DIAMETER_MM / 2.0,
        PUBLISHED_BIG_END_WIDTH_MM + bore_overshoot_mm,
    )
    solid = solid - _cylinder_z(
        PUBLISHED_PISTON_PIN_DIAMETER_MM / 2.0,
        PUBLISHED_SMALL_END_WIDTH_MM + bore_overshoot_mm,
        PUBLISHED_CENTER_DISTANCE_MM,
    )
    for y_mm in (-BOLT_AXIS_Y_MM, BOLT_AXIS_Y_MM):
        solid = solid - _cylinder_x(
            BOLT_CLEARANCE_DIAMETER_MM / 2.0,
            BOLT_LUG_LENGTH_X_MM + bore_overshoot_mm,
            y_mm,
        )

    split_tool = Box(
        CAP_SPLIT_GAP_MM,
        2.0 * (BOLT_AXIS_Y_MM + BOLT_LUG_WIDTH_Y_MM),
        PUBLISHED_SMALL_END_WIDTH_MM + bore_overshoot_mm,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    return solid - split_tool


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    cad_volume_mm3 = None
    shape = None
    envelope = None
    if args.out:
        from build123d import export_step, import_step

        shape = build_geometry()
        if not shape.is_valid or len(shape.solids()) != 2:
            raise SystemExit("Le F0 doit contenir exactement un corps et un chapeau valides.")
        bbox = shape.bounding_box()
        envelope = [bbox.size.X, bbox.size.Y, bbox.size.Z]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        export_step(shape, str(args.out))
        roundtrip = import_step(str(args.out))
        if not roundtrip.is_valid or len(roundtrip.solids()) != 2:
            raise SystemExit("Le STEP relu ne conserve pas les deux solides valides.")
        if abs(roundtrip.volume - shape.volume) > 0.05:
            raise SystemExit("Le STEP relu ne reproduit pas le volume OCCT attendu.")
        cad_volume_mm3 = roundtrip.volume

    report = engineering_screen(cad_volume_mm3)
    if shape is not None and envelope is not None:
        report["step_roundtrip"] = {
            "status": "passed",
            "valid_brep": True,
            "solid_count": 2,
            "semantic_solids": ["rod_body", "rod_cap"],
            "volume_mm3": cad_volume_mm3,
            "envelope_mm": envelope,
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
