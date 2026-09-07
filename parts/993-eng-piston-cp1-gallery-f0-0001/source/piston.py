#!/usr/bin/env python3
"""Piston M64/60 à galerie de refroidissement, concept CP1 LPBF F0."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-PISTON-CP1-GALLERY-F0-0001"

# Faits documentaires M64/60, jamais une définition de piston.
PUBLISHED_ENGINE_BORE_MM = 100.0
PUBLISHED_ENGINE_STROKE_MM = 76.4
PUBLISHED_ENGINE_SPEED_RPM = 6720.0
PUBLISHED_ADDITIVE_MASS_REDUCTION_RATIO = 0.10
PUBLISHED_ADDITIVE_ENDURANCE_HOURS = 200.0

# Géométrie F0 indépendante : aucune surface Porsche, MAHLE ou fournisseur.
PISTON_OUTER_DIAMETER_MM = 99.0
PISTON_HEIGHT_MM = 70.0
INNER_CAVITY_DIAMETER_MM = 82.0
INNER_CAVITY_TOP_Z_MM = 19.0
PIN_AXIS_Z_MM = -4.0
PIN_BORE_DIAMETER_MM = 23.0
PIN_BOSS_OUTER_DIAMETER_MM = 32.0
PIN_BOSS_LENGTH_MM = 92.0
RING_GROOVE_ROOT_DIAMETER_MM = 93.0
RING_GROOVE_HEIGHTS_MM = (1.5, 1.5, 3.0)
RING_GROOVE_CENTER_Z_MM = (22.0, 18.5, 14.5)
BOWL_DIAMETER_MM = 60.0
BOWL_DEPTH_MM = 3.0
GALLERY_MAJOR_RADIUS_MM = 34.0
GALLERY_MINOR_RADIUS_MM = 3.5
GALLERY_CENTER_Z_MM = 26.0
GALLERY_PORT_DIAMETER_MM = 3.0
GALLERY_PORT_CENTER_X_MM = 42.0
GALLERY_PORT_LENGTH_MM = 18.0

# Matériau CP1 : données Velo3D/Constellium de comparaison à l'ambiante.
DENSITY_G_CM3 = 2.67
COMPARISON_YIELD_STRENGTH_MPA = 297.0
COMPARISON_ULTIMATE_STRENGTH_MPA = 331.0
THERMAL_CONDUCTIVITY_W_MK = 187.0
ELASTIC_MODULUS_MPA_PROVISIONAL = 70_000.0
POISSON_RATIO_PROVISIONAL = 0.33
THERMAL_EXPANSION_PER_K_PROVISIONAL = 23.0e-6
SPECIFIC_HEAT_J_KG_K_PROVISIONAL = 900.0

# Cas de charge/thermique/hydraulique synthétique.
PEAK_CYLINDER_PRESSURE_MPA = 12.0
ROD_LENGTH_MM = 127.0
PIN_AND_RING_MASS_G = 140.0
SCREEN_DELTA_T_K = 200.0
SCREEN_CROWN_UNSUPPORTED_RADIUS_MM = 41.0
SCREEN_CROWN_MINIMUM_THICKNESS_MM = 5.5
SCREEN_PIN_PROJECTED_WIDTH_MM = 40.0
SCREEN_OIL_FLOW_L_MIN = 2.0
SCREEN_OIL_DENSITY_KG_M3 = 850.0
SCREEN_OIL_DYNAMIC_VISCOSITY_PA_S = 0.010
SCREEN_OIL_SPECIFIC_HEAT_J_KG_K = 2000.0
SCREEN_GALLERY_HEAT_REJECTION_W = 5000.0
SCREEN_DUTY_HOURS = 100.0


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    cad_mass_g = (
        cad_volume_mm3 / 1000.0 * DENSITY_G_CM3
        if cad_volume_mm3 is not None
        else None
    )
    load_mass_g = cad_mass_g if cad_mass_g is not None else 500.0

    piston_area_mm2 = math.pi * PUBLISHED_ENGINE_BORE_MM**2 / 4.0
    gas_force_n = PEAK_CYLINDER_PRESSURE_MPA * piston_area_mm2
    crank_radius_m = PUBLISHED_ENGINE_STROKE_MM / 2000.0
    rod_length_m = ROD_LENGTH_MM / 1000.0
    omega_rad_s = 2.0 * math.pi * PUBLISHED_ENGINE_SPEED_RPM / 60.0
    tdc_acceleration_m_s2 = (
        crank_radius_m
        * omega_rad_s**2
        * (1.0 + crank_radius_m / rod_length_m)
    )
    reciprocating_mass_kg = (load_mass_g + PIN_AND_RING_MASS_G) / 1000.0
    inertia_force_n = reciprocating_mass_kg * tdc_acceleration_m_s2
    conservative_pin_force_n = gas_force_n + inertia_force_n

    crown_radius_mm = SCREEN_CROWN_UNSUPPORTED_RADIUS_MM
    crown_thickness_mm = SCREEN_CROWN_MINIMUM_THICKNESS_MM
    plate_factor = (3.0 + POISSON_RATIO_PROVISIONAL) / 8.0
    crown_bending_stress_mpa = (
        plate_factor
        * PEAK_CYLINDER_PRESSURE_MPA
        * crown_radius_mm**2
        / crown_thickness_mm**2
    )
    plate_rigidity_n_mm = (
        ELASTIC_MODULUS_MPA_PROVISIONAL
        * crown_thickness_mm**3
        / (12.0 * (1.0 - POISSON_RATIO_PROVISIONAL**2))
    )
    crown_center_deflection_mm = (
        PEAK_CYLINDER_PRESSURE_MPA
        * crown_radius_mm**4
        / (64.0 * plate_rigidity_n_mm)
    )
    pin_projected_area_mm2 = PIN_BORE_DIAMETER_MM * SCREEN_PIN_PROJECTED_WIDTH_MM
    pin_projected_pressure_mpa = conservative_pin_force_n / pin_projected_area_mm2

    gallery_hydraulic_diameter_m = 2.0 * GALLERY_MINOR_RADIUS_MM / 1000.0
    gallery_flow_area_m2 = math.pi * (gallery_hydraulic_diameter_m / 2.0) ** 2
    gallery_path_length_m = 2.0 * math.pi * GALLERY_MAJOR_RADIUS_MM / 1000.0
    oil_volume_flow_m3_s = SCREEN_OIL_FLOW_L_MIN / 1000.0 / 60.0
    oil_velocity_m_s = oil_volume_flow_m3_s / gallery_flow_area_m2
    oil_reynolds = (
        SCREEN_OIL_DENSITY_KG_M3
        * oil_velocity_m_s
        * gallery_hydraulic_diameter_m
        / SCREEN_OIL_DYNAMIC_VISCOSITY_PA_S
    )
    darcy_friction_factor = 64.0 / oil_reynolds
    gallery_pressure_loss_pa = (
        darcy_friction_factor
        * gallery_path_length_m
        / gallery_hydraulic_diameter_m
        * SCREEN_OIL_DENSITY_KG_M3
        * oil_velocity_m_s**2
        / 2.0
    )
    oil_mass_flow_kg_s = oil_volume_flow_m3_s * SCREEN_OIL_DENSITY_KG_M3
    oil_temperature_rise_k = (
        SCREEN_GALLERY_HEAT_REJECTION_W
        / (oil_mass_flow_kg_s * SCREEN_OIL_SPECIFIC_HEAT_J_KG_K)
    )

    crown_conduction_area_m2 = math.pi * (crown_radius_mm / 1000.0) ** 2
    conduction_upper_bound_w = (
        THERMAL_CONDUCTIVITY_W_MK
        * crown_conduction_area_m2
        * SCREEN_DELTA_T_K
        / (crown_thickness_mm / 1000.0)
    )
    free_diameter_growth_mm = (
        THERMAL_EXPANSION_PER_K_PROVISIONAL
        * PISTON_OUTER_DIAMETER_MM
        * SCREEN_DELTA_T_K
    )
    cycles = PUBLISHED_ENGINE_SPEED_RPM / 60.0 * SCREEN_DUTY_HOURS * 3600.0

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_documentary_bore_clean_sheet_cp1_gallery_screen_only",
        "geometry_authority": {
            "published": {
                "m64_60_engine_bore_mm": PUBLISHED_ENGINE_BORE_MM,
                "m64_60_engine_stroke_mm": PUBLISHED_ENGINE_STROKE_MM,
                "m64_60_limiter_rpm": PUBLISHED_ENGINE_SPEED_RPM,
                "porsche_additive_piston_mass_reduction_ratio": PUBLISHED_ADDITIVE_MASS_REDUCTION_RATIO,
                "porsche_additive_piston_endurance_hours": PUBLISHED_ADDITIVE_ENDURANCE_HOURS,
                "porsche_additive_feature": "load-optimized piston with integrated closed crown cooling duct",
                "porsche_additive_scope": "modern 911 GT2 RS development piston, not Porsche 993",
            },
            "interpretations": [
                "100 mm M64/60 bore is an engine documentary value, not a finished piston diameter",
                "CP1 is a separate LPBF candidate selected for its published conductivity and thermal-stability rationale",
                "two temporary radial ports make powder removal possible; their final sealing route is undefined",
            ],
            "hypotheses": [
                "99 mm cylindrical envelope and 70 mm total height",
                "82 mm underside cavity ending at z=19 mm",
                "23 mm pin bore, 32 mm bosses and synthetic pin-axis position",
                "three ring grooves without lands, profiles, side clearances or ring specifications",
                "34 mm mean-radius by 7 mm hydraulic-diameter toroidal cooling gallery",
                "5.5 mm minimum analytical crown ligament above the gallery",
            ],
            "not_claimed": "No Porsche, MAHLE, Swindon or production piston surface, clearance, bowl, ring pack, pin, boss, gallery, tolerance or mass distribution is claimed.",
        },
        "synthetic_load_case": {
            "peak_cylinder_pressure_mpa": PEAK_CYLINDER_PRESSURE_MPA,
            "rod_length_mm": ROD_LENGTH_MM,
            "pin_and_ring_mass_g": PIN_AND_RING_MASS_G,
            "delta_t_k": SCREEN_DELTA_T_K,
            "oil_flow_l_min": SCREEN_OIL_FLOW_L_MIN,
            "gallery_heat_rejection_w": SCREEN_GALLERY_HEAT_REJECTION_W,
            "duty_hours": SCREEN_DUTY_HOURS,
            "authority": "regression inputs only; none is a measured target-piston load, temperature, lubrication or duty trace",
        },
        "material_screen": {
            "candidate": "Velo3D/Constellium Aheadd CP1, 50 micrometre LPBF plus 400 C for 4 h, study only",
            "density_g_cm3": DENSITY_G_CM3,
            "comparison_minimum_yield_strength_mpa": COMPARISON_YIELD_STRENGTH_MPA,
            "comparison_minimum_ultimate_strength_mpa": COMPARISON_ULTIMATE_STRENGTH_MPA,
            "thermal_conductivity_w_mk": THERMAL_CONDUCTIVITY_W_MK,
            "provisional_elastic_modulus_mpa": ELASTIC_MODULUS_MPA_PROVISIONAL,
            "provisional_poisson_ratio": POISSON_RATIO_PROVISIONAL,
            "provisional_thermal_expansion_per_k": THERMAL_EXPANSION_PER_K_PROVISIONAL,
            "scope": "density and tensile minima are route-specific published values; modulus, Poisson ratio, expansion and heat capacity are unqualified analytical placeholders",
        },
        "results": {
            "cad_volume_mm3": cad_volume_mm3,
            "cad_mass_g": cad_mass_g,
            "load_mass_basis_g": load_mass_g,
            "piston_area_mm2": piston_area_mm2,
            "synthetic_peak_gas_force_n": gas_force_n,
            "angular_speed_rad_s": omega_rad_s,
            "synthetic_tdc_acceleration_m_s2": tdc_acceleration_m_s2,
            "synthetic_reciprocating_mass_kg": reciprocating_mass_kg,
            "synthetic_tensile_inertia_force_n": inertia_force_n,
            "conservative_pin_force_n": conservative_pin_force_n,
            "crown_plate_factor": plate_factor,
            "crown_plate_rigidity_n_mm": plate_rigidity_n_mm,
            "crown_bending_stress_screen_mpa": crown_bending_stress_mpa,
            "ambient_yield_to_crown_stress_ratio": COMPARISON_YIELD_STRENGTH_MPA / crown_bending_stress_mpa,
            "crown_center_deflection_screen_mm": crown_center_deflection_mm,
            "deflection_to_crown_thickness_ratio": crown_center_deflection_mm / crown_thickness_mm,
            "pin_projected_area_mm2": pin_projected_area_mm2,
            "pin_projected_pressure_screen_mpa": pin_projected_pressure_mpa,
            "gallery_hydraulic_diameter_m": gallery_hydraulic_diameter_m,
            "gallery_flow_area_m2": gallery_flow_area_m2,
            "gallery_path_length_m": gallery_path_length_m,
            "oil_volume_flow_m3_s": oil_volume_flow_m3_s,
            "oil_velocity_m_s": oil_velocity_m_s,
            "oil_reynolds": oil_reynolds,
            "darcy_friction_factor": darcy_friction_factor,
            "gallery_pressure_loss_pa": gallery_pressure_loss_pa,
            "oil_mass_flow_kg_s": oil_mass_flow_kg_s,
            "oil_temperature_rise_for_5kw_k": oil_temperature_rise_k,
            "one_dimensional_crown_conduction_upper_bound_w": conduction_upper_bound_w,
            "free_outer_diameter_growth_mm": free_diameter_growth_mm,
            "load_cycles_at_duty": cycles,
            "lumped_heat_capacity_j_k": load_mass_g / 1000.0 * SPECIFIC_HEAT_J_KG_K_PROVISIONAL,
        },
        "equations": {
            "mass": "m=rho*Vcad",
            "gas_force": "F_gas=p_peak*pi*bore^2/4",
            "tdc_acceleration": "a=r*omega^2*(1+r/L); omega=2*pi*N/60",
            "inertia_force": "F_i=(m_piston+m_pin_rings)*a",
            "clamped_circular_plate_stress": "sigma=((3+nu)/8)*p*a^2/t^2",
            "clamped_circular_plate_deflection": "w=p*a^4/(64*D); D=E*t^3/(12*(1-nu^2))",
            "projected_pin_pressure": "p_pin=F/(d_pin*w_bearing)",
            "gallery_reynolds": "Re=rho*v*Dh/mu",
            "laminar_darcy": "f=64/Re",
            "gallery_pressure_loss": "delta_p=f*(L/Dh)*rho*v^2/2",
            "oil_temperature_rise": "delta_T=Q/(m_dot*cp)",
            "crown_conduction": "Q=k*A*delta_T/t",
            "thermal_expansion": "delta_D=alpha*D*delta_T",
            "load_cycles": "n=N/60*t_seconds",
        },
        "dfam_screen": {
            "additive_value": "closed crown gallery and load-shaped internal support can be integrated without a casting core",
            "gallery_closed_after_post_processing": True,
            "temporary_powder_ports_present": True,
            "temporary_powder_port_count": 2,
            "internal_support_strategy_defined": False,
            "orientation_selected": False,
            "minimum_gallery_hydraulic_diameter_mm": 2.0 * GALLERY_MINOR_RADIUS_MM,
            "critical_surfaces_require_machining": True,
            "process_comparison_required": [
                "forged 2618-type piston without additive gallery",
                "conventional piston with drilled or cast oil cooling strategy",
                "LPBF CP1 piston with temporary depowdering ports and sealed gallery",
            ],
        },
        "interpretation": {
            "mass": "the CAD mass is an independent F0 value and cannot use Porsche's 10 percent GT2 RS reduction as a 993 target",
            "mechanics": "the clamped-plate and projected-bearing equations are screening bounds, not piston FEA or contact mechanics",
            "thermal": "one-dimensional conduction and free growth omit combustion transients, rings, skirt contact, oil jets and cylinder heat transfer",
            "hydraulics": "smooth circular laminar gallery equations omit rotating acceleration, two-phase oil, entrance losses, ports and crankcase windage",
            "fatigue": "cycle count is reported without life because no CP1 hot fatigue, creep, oxidation or defect card exists for this route",
            "physicsnemo": "deferred until correlated transient thermal-structural and oil-flow cases define train, holdout and OOD sets",
            "simready": "deferred until piston, pin, rings, rod, cylinder, valves and combustion interfaces are measured",
        },
        "release_blockers": [
            "No measured Porsche 993 piston, scan, CAD surface, compression height, skirt profile, crown, pin axis, boss or mass distribution.",
            "The 100 mm engine bore is not a finished piston diameter or clearance specification.",
            "No ring count, groove profile, land, side clearance, end gap, coating, lubrication or blow-by evidence for the target piston.",
            "No piston pin length, material, wall, retention, interference, boss contact or rod small-end stack.",
            "No measured cylinder-pressure trace, detonation case, reciprocating masses, overspeed or crank-angle load history.",
            "No measured crown, gallery, skirt, ring, pin-boss or cylinder temperature/heat-flux boundary conditions.",
            "No 3D nonlinear thermo-mechanical contact FEA, mesh convergence, plasticity, creep, fracture, modal or fatigue analysis.",
            "No CFD/VOF oil-gallery solution with piston acceleration, oil jet capture, aeration, drainage and pressure supply.",
            "No complete CP1 temperature-dependent strength, fatigue, creep, expansion, conductivity or oxidation card for the exact LPBF route.",
            "No qualified orientation, supports, distortion compensation, heat treatment, HIP decision, powder evacuation or port-sealing process.",
            "No CT, metrology, roughness, porosity, ring-groove inspection, proof pressure, fatigue or 200-hour engine validation.",
            "No professional engine engineering review, dyno programme or approved validation plan.",
        ],
        "manufacturing_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


def _cylinder_z(radius_mm: float, height_mm: float, z_mm: float = 0.0):
    from build123d import Align, Cylinder, Pos

    return Pos(0.0, 0.0, z_mm) * Cylinder(
        radius_mm,
        height_mm,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )


def _cylinder_x(radius_mm: float, length_mm: float, x_mm: float, z_mm: float):
    from build123d import Align, Cylinder, Pos, Rot

    return Pos(x_mm, 0.0, z_mm) * Rot(0.0, 90.0, 0.0) * Cylinder(
        radius_mm,
        length_mm,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )


def build_geometry():
    from build123d import Align, Cylinder, Pos, Torus

    outer = _cylinder_z(PISTON_OUTER_DIAMETER_MM / 2.0, PISTON_HEIGHT_MM)

    for center_z, height in zip(RING_GROOVE_CENTER_Z_MM, RING_GROOVE_HEIGHTS_MM):
        groove = _cylinder_z(PISTON_OUTER_DIAMETER_MM / 2.0 + 1.0, height, center_z)
        groove = groove - _cylinder_z(RING_GROOVE_ROOT_DIAMETER_MM / 2.0, height + 0.2, center_z)
        outer = outer - groove

    bowl = Pos(0.0, 0.0, PISTON_HEIGHT_MM / 2.0 - BOWL_DEPTH_MM / 2.0) * Cylinder(
        BOWL_DIAMETER_MM / 2.0,
        BOWL_DEPTH_MM,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    outer = outer - bowl

    cavity_bottom_z = -PISTON_HEIGHT_MM / 2.0 - 1.0
    cavity_height = INNER_CAVITY_TOP_Z_MM - cavity_bottom_z
    cavity = _cylinder_z(
        INNER_CAVITY_DIAMETER_MM / 2.0,
        cavity_height,
        (cavity_bottom_z + INNER_CAVITY_TOP_Z_MM) / 2.0,
    )
    body = outer - cavity

    pin_boss = _cylinder_x(
        PIN_BOSS_OUTER_DIAMETER_MM / 2.0,
        PIN_BOSS_LENGTH_MM,
        0.0,
        PIN_AXIS_Z_MM,
    )
    body = body + pin_boss
    body = body - _cylinder_x(
        PIN_BORE_DIAMETER_MM / 2.0,
        PISTON_OUTER_DIAMETER_MM + 4.0,
        0.0,
        PIN_AXIS_Z_MM,
    )

    gallery = Pos(0.0, 0.0, GALLERY_CENTER_Z_MM) * Torus(
        GALLERY_MAJOR_RADIUS_MM,
        GALLERY_MINOR_RADIUS_MM,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    body = body - gallery
    for x_mm in (-GALLERY_PORT_CENTER_X_MM, GALLERY_PORT_CENTER_X_MM):
        body = body - _cylinder_x(
            GALLERY_PORT_DIAMETER_MM / 2.0,
            GALLERY_PORT_LENGTH_MM,
            x_mm,
            GALLERY_CENTER_Z_MM,
        )
    return body


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
    if shape is not None and envelope is not None:
        report["step_roundtrip"] = {
            "status": "passed",
            "valid_brep": True,
            "solid_count": 1,
            "semantic_solids": ["piston_body_with_open_powder_ports"],
            "volume_mm3": cad_volume_mm3,
            "envelope_mm": envelope,
            "gallery_mean_radius_mm": GALLERY_MAJOR_RADIUS_MM,
            "gallery_hydraulic_diameter_mm": 2.0 * GALLERY_MINOR_RADIUS_MM,
            "powder_port_count": 2,
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
