#!/usr/bin/env python3
"""Soupape d'admission 993 creuse en Ti-6Al-4V, concept LPBF F0."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-INTAKE-VALVE-TI64-HOLLOW-F0-0001"

# Faits publies par FVD pour la reference de soupape, sans plan de definition.
PUBLISHED_HEAD_DIAMETER_MM = 49.0
PUBLISHED_STEM_DIAMETER_MM = 8.0
PUBLISHED_PRODUCT_ENVELOPE_MM = [50.0, 110.0, 50.0]
PUBLISHED_PRODUCT_MASS_G = 120.0
PUBLISHED_PART_NUMBER = "99310540902"

# Geometrie F0 independante. Aucune surface Porsche, FVD ou Swindon.
TOTAL_LENGTH_MM = 109.0
HEAD_FACE_THICKNESS_MM = 3.0
HEAD_TAPER_HEIGHT_MM = 7.0
NECK_DIAMETER_MM = 12.0
HOLLOW_BORE_DIAMETER_MM = 5.0
HEAD_CAVITY_BOTTOM_Z_MM = 2.2
HEAD_CAVITY_HEIGHT_MM = 6.8
HEAD_CAVITY_BOTTOM_RADIUS_MM = 16.0
HEAD_CAVITY_TOP_RADIUS_MM = 2.5
INTERNAL_WEB_THICKNESS_MM = 1.2
INTERNAL_RADIAL_WEB_COUNT = 4

# EOS/TIMET Ti-6Al-4V : valeurs de comparaison, pas des admissibles soupape.
DENSITY_G_CM3 = 4.42
ELASTIC_MODULUS_MPA = 110_000.0
POISSON_RATIO = 0.34
COMPARISON_YIELD_STRENGTH_MPA = 980.0
COMPARISON_ULTIMATE_STRENGTH_MPA = 1080.0
THERMAL_CONDUCTIVITY_W_MK = 6.7
THERMAL_EXPANSION_PER_K = 9.0e-6
SPECIFIC_HEAT_J_KG_K = 580.0

# Cas synthetique de criblage dynamique, mecanique et thermique.
ENGINE_SPEED_RPM = 6720.0
VALVE_LIFT_MM = 12.0
EVENT_DURATION_CRANK_DEG = 240.0
SPRING_SEAT_FORCE_N = 520.0
SPRING_RATE_N_MM = 40.0
PRESSURE_DIFFERENTIAL_MPA = 0.20
UNSUPPORTED_HEAD_RADIUS_MM = 19.0
HEAD_LIGAMENT_MM = 2.2
FREE_STEM_LENGTH_MM = 95.0
THERMAL_DELTA_T_K = 400.0
CONDUCTION_LENGTH_MM = 60.0
SCREEN_DUTY_HOURS = 100.0


def engineering_screen(
    cad_volume_mm3: float | None = None,
    solid_reference_volume_mm3: float | None = None,
) -> dict[str, object]:
    cad_mass_g = (
        cad_volume_mm3 / 1000.0 * DENSITY_G_CM3
        if cad_volume_mm3 is not None
        else None
    )
    solid_reference_mass_g = (
        solid_reference_volume_mm3 / 1000.0 * DENSITY_G_CM3
        if solid_reference_volume_mm3 is not None
        else None
    )
    f0_mass_reduction_ratio = (
        1.0 - cad_volume_mm3 / solid_reference_volume_mm3
        if cad_volume_mm3 is not None
        and solid_reference_volume_mm3 is not None
        else None
    )
    load_mass_g = cad_mass_g if cad_mass_g is not None else 60.0

    engine_omega_rad_s = 2.0 * math.pi * ENGINE_SPEED_RPM / 60.0
    cam_omega_rad_s = engine_omega_rad_s / 2.0
    event_duration_s = math.radians(EVENT_DURATION_CRANK_DEG / 2.0) / cam_omega_rad_s
    lift_m = VALVE_LIFT_MM / 1000.0
    simple_harmonic_peak_velocity_m_s = math.pi * lift_m / event_duration_s
    simple_harmonic_peak_acceleration_m_s2 = (
        2.0 * math.pi**2 * lift_m / event_duration_s**2
    )
    inertia_force_n = load_mass_g / 1000.0 * simple_harmonic_peak_acceleration_m_s2
    maximum_spring_force_n = SPRING_SEAT_FORCE_N + SPRING_RATE_N_MM * VALVE_LIFT_MM

    head_area_mm2 = math.pi * PUBLISHED_HEAD_DIAMETER_MM**2 / 4.0
    differential_pressure_force_n = PRESSURE_DIFFERENTIAL_MPA * head_area_mm2
    conservative_axial_force_n = (
        maximum_spring_force_n + inertia_force_n + differential_pressure_force_n
    )
    stem_area_mm2 = math.pi / 4.0 * (
        PUBLISHED_STEM_DIAMETER_MM**2 - HOLLOW_BORE_DIAMETER_MM**2
    )
    solid_stem_area_mm2 = math.pi / 4.0 * PUBLISHED_STEM_DIAMETER_MM**2
    axial_stress_mpa = conservative_axial_force_n / stem_area_mm2

    stem_i_mm4 = math.pi / 64.0 * (
        PUBLISHED_STEM_DIAMETER_MM**4 - HOLLOW_BORE_DIAMETER_MM**4
    )
    euler_buckling_load_n = (
        math.pi**2
        * ELASTIC_MODULUS_MPA
        * stem_i_mm4
        / FREE_STEM_LENGTH_MM**2
    )

    plate_factor = (3.0 + POISSON_RATIO) / 8.0
    head_plate_stress_mpa = (
        plate_factor
        * PRESSURE_DIFFERENTIAL_MPA
        * UNSUPPORTED_HEAD_RADIUS_MM**2
        / HEAD_LIGAMENT_MM**2
    )
    plate_rigidity_n_mm = (
        ELASTIC_MODULUS_MPA
        * HEAD_LIGAMENT_MM**3
        / (12.0 * (1.0 - POISSON_RATIO**2))
    )
    head_center_deflection_mm = (
        PRESSURE_DIFFERENTIAL_MPA
        * UNSUPPORTED_HEAD_RADIUS_MM**4
        / (64.0 * plate_rigidity_n_mm)
    )

    stem_area_m2 = stem_area_mm2 / 1_000_000.0
    stem_i_m4 = stem_i_mm4 / 1.0e12
    free_length_m = FREE_STEM_LENGTH_MM / 1000.0
    stem_mass_kg = (
        DENSITY_G_CM3 * 1000.0 * stem_area_m2 * free_length_m
    )
    total_mass_kg = load_mass_g / 1000.0
    head_equivalent_mass_kg = max(total_mass_kg - stem_mass_kg, 0.001)
    bending_stiffness_n_m = (
        3.0 * ELASTIC_MODULUS_MPA * 1_000_000.0 * stem_i_m4 / free_length_m**3
    )
    effective_modal_mass_kg = head_equivalent_mass_kg + 0.236 * stem_mass_kg
    first_bending_frequency_hz = (
        math.sqrt(bending_stiffness_n_m / effective_modal_mass_kg)
        / (2.0 * math.pi)
    )
    valve_event_frequency_hz = ENGINE_SPEED_RPM / 120.0

    peak_kinetic_energy_j = (
        0.5 * total_mass_kg * simple_harmonic_peak_velocity_m_s**2
    )
    spring_energy_j = (
        SPRING_SEAT_FORCE_N * VALVE_LIFT_MM
        + 0.5 * SPRING_RATE_N_MM * VALVE_LIFT_MM**2
    ) / 1000.0
    free_stem_growth_mm = (
        THERMAL_EXPANSION_PER_K * TOTAL_LENGTH_MM * THERMAL_DELTA_T_K
    )
    fully_constrained_thermal_stress_mpa = (
        ELASTIC_MODULUS_MPA * THERMAL_EXPANSION_PER_K * THERMAL_DELTA_T_K
    )
    one_dimensional_conduction_w = (
        THERMAL_CONDUCTIVITY_W_MK
        * stem_area_m2
        * THERMAL_DELTA_T_K
        / (CONDUCTION_LENGTH_MM / 1000.0)
    )
    cycles = valve_event_frequency_hz * SCREEN_DUTY_HOURS * 3600.0

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_published_envelope_clean_sheet_hollow_ti64_screen_only",
        "geometry_authority": {
            "published": {
                "porsche_part_number": PUBLISHED_PART_NUMBER,
                "head_diameter_mm": PUBLISHED_HEAD_DIAMETER_MM,
                "stem_diameter_mm": PUBLISHED_STEM_DIAMETER_MM,
                "product_envelope_mm": PUBLISHED_PRODUCT_ENVELOPE_MM,
                "product_mass_g": PUBLISHED_PRODUCT_MASS_G,
                "porschefanatics_titanium_valve_context": "Swindon 24-valve kit candidate; grade, individual geometry and two-valve compatibility not published",
            },
            "interpretations": [
                "the 50 x 110 x 50 mm listing is treated only as a product envelope",
                "109 mm is a provisional F0 length constrained below the published 110 mm envelope",
                "Ti-6Al-4V is a separate LPBF candidate; the listed 993 valve material is not published",
            ],
            "hypotheses": [
                "3 mm flat head and 7 mm conical transition to a 12 mm neck",
                "5 mm axial bore open at the stem tip for powder evacuation",
                "16 mm radius head cavity with 2.2 mm minimum bottom ligament",
                "four radial 1.2 mm internal webs intersecting the head cavity",
                "no keeper groove, seat cone, margin, tip pad, coating or final bore closure",
            ],
            "not_claimed": "No Porsche, FVD, Swindon or production valve surface, seat, keeper, stem finish, hollow architecture, fitment, material or dynamic capability is claimed.",
        },
        "synthetic_load_case": {
            "engine_speed_rpm": ENGINE_SPEED_RPM,
            "valve_lift_mm": VALVE_LIFT_MM,
            "event_duration_crank_deg": EVENT_DURATION_CRANK_DEG,
            "spring_seat_force_n": SPRING_SEAT_FORCE_N,
            "spring_rate_n_mm": SPRING_RATE_N_MM,
            "pressure_differential_mpa": PRESSURE_DIFFERENTIAL_MPA,
            "thermal_delta_t_k": THERMAL_DELTA_T_K,
            "duty_hours": SCREEN_DUTY_HOURS,
            "authority": "regression inputs only; no target cam law, spring, pressure trace, valve temperature, guide condition or duty cycle was measured",
        },
        "material_screen": {
            "candidate": "EOS Titanium Ti64 Grade 5 LPBF, study only",
            "density_g_cm3": DENSITY_G_CM3,
            "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
            "poisson_ratio": POISSON_RATIO,
            "comparison_yield_strength_mpa": COMPARISON_YIELD_STRENGTH_MPA,
            "comparison_ultimate_strength_mpa": COMPARISON_ULTIMATE_STRENGTH_MPA,
            "thermal_conductivity_w_mk": THERMAL_CONDUCTIVITY_W_MK,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "specific_heat_j_kg_k": SPECIFIC_HEAT_J_KG_K,
            "scope": "room-temperature comparison values from EOS/TIMET references; no hot polished-stem, seat-impact, wear, creep, oxidation or defect allowable",
        },
        "results": {
            "cad_volume_mm3": cad_volume_mm3,
            "cad_mass_g": cad_mass_g,
            "solid_reference_volume_mm3": solid_reference_volume_mm3,
            "solid_reference_mass_g": solid_reference_mass_g,
            "f0_mass_reduction_ratio_vs_same_outer_solid": f0_mass_reduction_ratio,
            "cad_minus_published_product_mass_g": (
                cad_mass_g - PUBLISHED_PRODUCT_MASS_G
                if cad_mass_g is not None
                else None
            ),
            "engine_angular_speed_rad_s": engine_omega_rad_s,
            "cam_angular_speed_rad_s": cam_omega_rad_s,
            "simple_harmonic_event_duration_s": event_duration_s,
            "simple_harmonic_peak_velocity_m_s": simple_harmonic_peak_velocity_m_s,
            "simple_harmonic_peak_acceleration_m_s2": simple_harmonic_peak_acceleration_m_s2,
            "load_mass_basis_g": load_mass_g,
            "synthetic_peak_inertia_force_n": inertia_force_n,
            "maximum_spring_force_n": maximum_spring_force_n,
            "head_projected_area_mm2": head_area_mm2,
            "differential_pressure_force_n": differential_pressure_force_n,
            "conservative_axial_force_n": conservative_axial_force_n,
            "hollow_stem_area_mm2": stem_area_mm2,
            "solid_stem_area_mm2": solid_stem_area_mm2,
            "nominal_hollow_stem_axial_stress_mpa": axial_stress_mpa,
            "ambient_yield_to_axial_stress_ratio": COMPARISON_YIELD_STRENGTH_MPA / axial_stress_mpa,
            "hollow_stem_second_moment_mm4": stem_i_mm4,
            "euler_buckling_load_n": euler_buckling_load_n,
            "euler_to_axial_force_ratio": euler_buckling_load_n / conservative_axial_force_n,
            "head_plate_factor": plate_factor,
            "head_plate_bending_stress_screen_mpa": head_plate_stress_mpa,
            "head_plate_rigidity_n_mm": plate_rigidity_n_mm,
            "head_center_deflection_screen_mm": head_center_deflection_mm,
            "ambient_yield_to_head_plate_stress_ratio": COMPARISON_YIELD_STRENGTH_MPA / head_plate_stress_mpa,
            "stem_mass_screen_kg": stem_mass_kg,
            "head_equivalent_mass_screen_kg": head_equivalent_mass_kg,
            "effective_modal_mass_kg": effective_modal_mass_kg,
            "cantilever_bending_stiffness_n_m": bending_stiffness_n_m,
            "first_bending_frequency_screen_hz": first_bending_frequency_hz,
            "valve_event_frequency_hz": valve_event_frequency_hz,
            "bending_frequency_to_event_frequency_ratio": first_bending_frequency_hz / valve_event_frequency_hz,
            "peak_kinetic_energy_j": peak_kinetic_energy_j,
            "spring_energy_over_lift_j": spring_energy_j,
            "free_total_length_growth_mm": free_stem_growth_mm,
            "fully_constrained_elastic_thermal_stress_mpa": fully_constrained_thermal_stress_mpa,
            "ambient_yield_to_constrained_thermal_ratio": COMPARISON_YIELD_STRENGTH_MPA / fully_constrained_thermal_stress_mpa,
            "one_dimensional_stem_conduction_w": one_dimensional_conduction_w,
            "valve_events_at_duty": cycles,
            "lumped_heat_capacity_j_k": total_mass_kg * SPECIFIC_HEAT_J_KG_K,
        },
        "equations": {
            "mass": "m=rho*Vcad",
            "simple_harmonic_event": "T=theta_cam/omega_cam; vmax=pi*L/T; amax=2*pi^2*L/T^2",
            "spring_force": "Fmax=Fseat+k*L",
            "pressure_force": "Fp=delta_p*pi*Dhead^2/4",
            "axial_stress": "sigma=(Fspring+Finertia+Fp)/(pi*(Do^2-Di^2)/4)",
            "annular_second_moment": "I=pi*(Do^4-Di^4)/64",
            "euler_buckling": "Pcr=pi^2*E*I/L^2",
            "clamped_head_plate": "sigma=((3+nu)/8)*p*a^2/t^2; w=p*a^4/(64*D)",
            "first_bending_mode": "f1=sqrt((3*E*I/L^3)/(mhead+0.236*mstem))/(2*pi)",
            "kinetic_energy": "Ek=m*vmax^2/2",
            "spring_energy": "Es=Fseat*L+k*L^2/2",
            "thermal_expansion": "delta_L=alpha*L*delta_T",
            "fully_constrained_thermal": "sigma=E*alpha*delta_T",
            "one_dimensional_conduction": "Q=k*A*delta_T/L",
            "load_cycles": "n=N/120*t_seconds",
        },
        "dfam_screen": {
            "additive_value": "hollow head and stem plus internal radial webs can be made as one load-shaped body before a separately qualified tip closure",
            "open_powder_path_present": True,
            "powder_path_minimum_diameter_mm": HOLLOW_BORE_DIAMETER_MM,
            "internal_radial_web_count": INTERNAL_RADIAL_WEB_COUNT,
            "minimum_internal_web_mm": INTERNAL_WEB_THICKNESS_MM,
            "trapped_powder_volume_claimed": False,
            "tip_closure_defined": False,
            "orientation_selected": False,
            "critical_surfaces_require_machining": True,
            "process_comparison_required": [
                "forged and fully machined solid titanium valve",
                "conventionally fabricated or friction-welded hollow valve",
                "LPBF hollow Ti64 body with qualified depowdering and tip closure",
            ],
        },
        "interpretation": {
            "mass": "the reduction compares hollow and solid F0 bodies with the same invented exterior; it is not a reduction from an OEM valve",
            "dynamics": "the simple-harmonic cam law and spring are regression inputs, not a measured M64 valvetrain model",
            "mechanics": "annular stem, Euler and circular-plate equations omit seat contact, guide side load, keeper groove, impact, defects and multiaxial fatigue",
            "thermal": "one-dimensional conduction and free/fully-constrained bounds omit gas convection, seat/guide contact, cyclic gradients, oxidation and coatings",
            "fatigue": "the event count is reported without life because no qualified hot HCF/LCF, impact or wear card exists",
            "physicsnemo": "deferred until correlated valvetrain multibody, thermal and structural cases define train, holdout and OOD sets",
            "simready": "deferred until head, seat, guide, spring, retainer, keeper, cam/follower and piston-clearance interfaces are measured",
        },
        "release_blockers": [
            "No measured 993 intake valve, scan, CAD surface, full length, seat, margin, neck, tip, keeper groove or mass distribution.",
            "The published 50 x 110 x 50 mm is a commercial envelope and does not define functional length or datums.",
            "No evidence that Porsche part 99310540902 is titanium, hollow, LPBF or compatible with the Swindon four-valve system.",
            "No measured cam law, lift, lash, follower ratio, spring curve, retainer, keeper, guide or seat geometry.",
            "No cylinder/manifold pressure trace, gas force history, overspeed, float, bounce, impact or piston-clearance case.",
            "No measured head, stem, seat, guide, port or gas temperatures and no transient heat-transfer coefficients.",
            "No nonlinear contact FEA, multibody valvetrain solution, modal correlation, mesh convergence or fatigue analysis.",
            "No Ti64 hot strength, HCF/LCF, creep, oxidation, impact, fretting, galling, wear or coating card for the exact route.",
            "No qualified stem-axis orientation, supports, distortion compensation, heat treatment, HIP decision or alpha-case control.",
            "No demonstrated powder evacuation through the 5 mm by roughly 100 mm bore and no qualified internal cleanliness criterion.",
            "No tip closure design, joining route, proof test, CT acceptance, leakage criterion or retained-fragment analysis.",
            "No definition or machining capability for stem finish, straightness, seat runout, keeper groove, tip hardness and mass matching.",
            "No full-valve CT, metallography, dimensional inspection, hot spin/impact, rig fatigue, motored-head or fired-engine validation.",
            "No professional engine/valvetrain review, approved validation plan, dyno authorization or vehicle release.",
        ],
        "manufacturing_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


def _outer_geometry():
    from build123d import Align, Cone, Cylinder, Pos

    head = Cylinder(
        PUBLISHED_HEAD_DIAMETER_MM / 2.0,
        HEAD_FACE_THICKNESS_MM,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    taper = Pos(0.0, 0.0, HEAD_FACE_THICKNESS_MM) * Cone(
        PUBLISHED_HEAD_DIAMETER_MM / 2.0,
        NECK_DIAMETER_MM / 2.0,
        HEAD_TAPER_HEIGHT_MM,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    stem_start_z = HEAD_FACE_THICKNESS_MM + HEAD_TAPER_HEIGHT_MM
    stem = Pos(0.0, 0.0, stem_start_z) * Cylinder(
        PUBLISHED_STEM_DIAMETER_MM / 2.0,
        TOTAL_LENGTH_MM - stem_start_z,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    return head + taper + stem


def build_geometry():
    from build123d import Align, Box, Cone, Cylinder, Pos

    outer = _outer_geometry()
    head_cavity = Pos(0.0, 0.0, HEAD_CAVITY_BOTTOM_Z_MM) * Cone(
        HEAD_CAVITY_BOTTOM_RADIUS_MM,
        HEAD_CAVITY_TOP_RADIUS_MM,
        HEAD_CAVITY_HEIGHT_MM,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    bore = Pos(0.0, 0.0, HEAD_CAVITY_BOTTOM_Z_MM + HEAD_CAVITY_HEIGHT_MM - 0.5) * Cylinder(
        HOLLOW_BORE_DIAMETER_MM / 2.0,
        TOTAL_LENGTH_MM + 2.0,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    body = outer - (head_cavity + bore)

    web_z = HEAD_CAVITY_BOTTOM_Z_MM + HEAD_CAVITY_HEIGHT_MM / 2.0
    web_x = Pos(0.0, 0.0, web_z) * Box(
        2.0 * HEAD_CAVITY_BOTTOM_RADIUS_MM,
        INTERNAL_WEB_THICKNESS_MM,
        HEAD_CAVITY_HEIGHT_MM,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    web_y = Pos(0.0, 0.0, web_z) * Box(
        INTERNAL_WEB_THICKNESS_MM,
        2.0 * HEAD_CAVITY_BOTTOM_RADIUS_MM,
        HEAD_CAVITY_HEIGHT_MM,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    internal_webs = (web_x + web_y) & head_cavity
    body = (body + internal_webs) - bore
    return body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    cad_volume_mm3 = None
    solid_reference_volume_mm3 = None
    envelope = None
    if args.out:
        from build123d import export_step, import_step

        shape = build_geometry()
        solid_reference = _outer_geometry()
        if not shape.is_valid or len(shape.solids()) != 1:
            raise SystemExit("Le F0 creux doit contenir exactement un solide BREP valide.")
        if not solid_reference.is_valid or len(solid_reference.solids()) != 1:
            raise SystemExit("La reference F0 pleine doit contenir un solide BREP valide.")
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
        solid_reference_volume_mm3 = solid_reference.volume

    report = engineering_screen(cad_volume_mm3, solid_reference_volume_mm3)
    if args.out and envelope is not None:
        report["step_roundtrip"] = {
            "status": "passed",
            "valid_brep": True,
            "solid_count": 1,
            "semantic_solids": ["hollow_intake_valve_body_with_open_tip_bore"],
            "volume_mm3": cad_volume_mm3,
            "solid_reference_volume_mm3": solid_reference_volume_mm3,
            "envelope_mm": envelope,
            "open_powder_port_count": 1,
            "open_powder_port_diameter_mm": HOLLOW_BORE_DIAMETER_MM,
            "internal_radial_web_count": INTERNAL_RADIAL_WEB_COUNT,
            "minimum_head_ligament_mm": HEAD_CAVITY_BOTTOM_Z_MM,
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
