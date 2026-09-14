#!/usr/bin/env python3
"""Collecteur d'échappement trois-en-un 993 Turbo, concept IN625 F0."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-EXHAUST-MANIFOLD-IN625-F0-0001"

# Données publiées. Kline ne publie aucune cote de passage ou d'interface.
PUBLISHED_MATERIAL = "Inconel 625"
PUBLISHED_MANIFOLD_MASS_KG = 2.9
PUBLISHED_HEAT_EXCHANGER_INCLUDED = True
PUBLISHED_PIECES_PER_VEHICLE = 2
OEM_LEFT_REFERENCE = "993 211 039 55"
OEM_RIGHT_REFERENCE = "993 211 040 55"

# Géométrie propre au F0 : aucune cote n'est transférée depuis Kline ou Porsche.
PRIMARY_INNER_DIAMETER_MM = 34.0
COLLECTOR_INNER_DIAMETER_MM = 56.0
NOMINAL_WALL_MM = 1.2
PRIMARY_START_CENTERS_MM = ((-55.0, -15.0), (0.0, 0.0), (55.0, 15.0))
PRIMARY_END_CENTERS_MM = ((-8.0, -4.0), (0.0, 0.0), (8.0, 4.0))
MERGE_Z_MM = 130.0
COLLECTOR_START_Z_MM = 105.0
TOTAL_LENGTH_MM = 215.0

# Cas moteur synthétique : criblage de régression, sans autorité M64/60.
ENGINE_DISPLACEMENT_L = 3.6
ENGINE_SPEED_RPM = 5750.0
VOLUMETRIC_EFFICIENCY = 0.95
BANK_COUNT = 2
CYLINDERS_PER_BANK = 3
INTAKE_REFERENCE_K = 300.0
EXHAUST_GAS_K = 900.0
REFERENCE_AIR_DENSITY_KG_M3 = 1.18
EXHAUST_DYNAMIC_VISCOSITY_PA_S = 4.2e-5
HEAT_CAPACITY_RATIO = 1.33
GAS_CONSTANT_J_KG_K = 287.0
JUNCTION_LOSS_COEFFICIENT = 0.2
SCREEN_GAUGE_PRESSURE_PA = 50_000.0

# Cas thermique synthétique et références IN625 de criblage.
REFERENCE_TEMPERATURE_K = 293.0
SCREEN_SURFACE_K = 750.0
SCREEN_AMBIENT_K = 330.0
EMISSIVITY_HYPOTHESIS = 0.8
STEFAN_BOLTZMANN_W_M2_K4 = 5.670374419e-8
DENSITY_G_CM3 = 8.44
ELASTIC_MODULUS_MPA = 204_000.0
COMPARISON_YIELD_STRENGTH_MPA = 640.0
THERMAL_EXPANSION_PER_K = 13.7e-6
THERMAL_CONDUCTIVITY_W_MK = 15.7
SPECIFIC_HEAT_J_KG_K = 511.0


def circle_area_m2(diameter_mm: float) -> float:
    return math.pi * (diameter_mm / 2000.0) ** 2


def primary_centerline_lengths_mm() -> list[float]:
    lengths = []
    for start, end in zip(PRIMARY_START_CENTERS_MM, PRIMARY_END_CENTERS_MM):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        lengths.append(math.sqrt(dx**2 + dy**2 + MERGE_Z_MM**2))
    return lengths


def approximate_outer_lateral_area_m2() -> float:
    primary_outer_diameter_mm = PRIMARY_INNER_DIAMETER_MM + 2.0 * NOMINAL_WALL_MM
    collector_outer_diameter_mm = COLLECTOR_INNER_DIAMETER_MM + 2.0 * NOMINAL_WALL_MM
    primary_area_mm2 = sum(
        math.pi * primary_outer_diameter_mm * length
        for length in primary_centerline_lengths_mm()
    )
    collector_area_mm2 = (
        math.pi
        * collector_outer_diameter_mm
        * (TOTAL_LENGTH_MM - COLLECTOR_START_Z_MM)
    )
    return (primary_area_mm2 + collector_area_mm2) / 1_000_000.0


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    primary_area_m2 = circle_area_m2(PRIMARY_INNER_DIAMETER_MM)
    collector_area_m2 = circle_area_m2(COLLECTOR_INNER_DIAMETER_MM)
    cold_volume_flow_total_m3_s = (
        ENGINE_DISPLACEMENT_L
        / 1000.0
        * ENGINE_SPEED_RPM
        / (2.0 * 60.0)
        * VOLUMETRIC_EFFICIENCY
    )
    cold_volume_flow_bank_m3_s = cold_volume_flow_total_m3_s / BANK_COUNT
    hot_volume_flow_bank_m3_s = (
        cold_volume_flow_bank_m3_s * EXHAUST_GAS_K / INTAKE_REFERENCE_K
    )
    hot_volume_flow_primary_m3_s = (
        hot_volume_flow_bank_m3_s / CYLINDERS_PER_BANK
    )
    hot_density_kg_m3 = (
        REFERENCE_AIR_DENSITY_KG_M3 * INTAKE_REFERENCE_K / EXHAUST_GAS_K
    )
    primary_velocity_m_s = hot_volume_flow_primary_m3_s / primary_area_m2
    collector_velocity_m_s = hot_volume_flow_bank_m3_s / collector_area_m2
    speed_of_sound_m_s = math.sqrt(
        HEAT_CAPACITY_RATIO * GAS_CONSTANT_J_KG_K * EXHAUST_GAS_K
    )
    primary_reynolds = (
        hot_density_kg_m3
        * primary_velocity_m_s
        * (PRIMARY_INNER_DIAMETER_MM / 1000.0)
        / EXHAUST_DYNAMIC_VISCOSITY_PA_S
    )
    collector_reynolds = (
        hot_density_kg_m3
        * collector_velocity_m_s
        * (COLLECTOR_INNER_DIAMETER_MM / 1000.0)
        / EXHAUST_DYNAMIC_VISCOSITY_PA_S
    )
    junction_pressure_loss_pa = (
        JUNCTION_LOSS_COEFFICIENT
        * 0.5
        * hot_density_kg_m3
        * collector_velocity_m_s**2
    )

    wall_m = NOMINAL_WALL_MM / 1000.0
    collector_radius_m = COLLECTOR_INNER_DIAMETER_MM / 2000.0
    hoop_stress_mpa = (
        SCREEN_GAUGE_PRESSURE_PA
        * collector_radius_m
        / wall_m
        / 1_000_000.0
    )
    pressure_force_n = SCREEN_GAUGE_PRESSURE_PA * collector_area_m2
    delta_t_k = EXHAUST_GAS_K - REFERENCE_TEMPERATURE_K
    free_expansion_mm = (
        THERMAL_EXPANSION_PER_K * TOTAL_LENGTH_MM * delta_t_k
    )
    fully_constrained_stress_mpa = (
        ELASTIC_MODULUS_MPA * THERMAL_EXPANSION_PER_K * delta_t_k
    )

    mean_primary_length_mm = sum(primary_centerline_lengths_mm()) / 3.0
    acoustic_path_mm = mean_primary_length_mm + (
        TOTAL_LENGTH_MM - MERGE_Z_MM
    )
    bank_pulse_frequency_hz = (
        ENGINE_SPEED_RPM / 60.0 * CYLINDERS_PER_BANK / 2.0
    )
    path_quarter_wave_hz = speed_of_sound_m_s / (
        4.0 * acoustic_path_mm / 1000.0
    )
    first_order_quarter_wave_length_mm = (
        speed_of_sound_m_s / (4.0 * bank_pulse_frequency_hz) * 1000.0
    )

    lateral_area_m2 = approximate_outer_lateral_area_m2()
    radiative_flux_w_m2 = (
        EMISSIVITY_HYPOTHESIS
        * STEFAN_BOLTZMANN_W_M2_K4
        * (SCREEN_SURFACE_K**4 - SCREEN_AMBIENT_K**4)
    )

    volume_mm3 = cad_volume_mm3 or 0.0
    mass_g = volume_mm3 / 1000.0 * DENSITY_G_CM3
    published_mass_g = PUBLISHED_MANIFOLD_MASS_KG * 1000.0

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_published_identity_material_mass_clean_sheet_flow_core_screen_only",
        "geometry_authority": {
            "published": [
                "993 Turbo manifold offering in Inconel 625",
                "2.9 kg per side with heat exchanger included",
                "left and right factory heat-exchanger identities in PET group 202-10",
            ],
            "catalogue_identity": [
                OEM_LEFT_REFERENCE,
                OEM_RIGHT_REFERENCE,
                "Kline 993 Turbo Inconel 625 manifold with heat exchanger",
            ],
            "hypotheses": [
                "34 mm primary inside diameter",
                "56 mm collector inside diameter",
                "1.2 mm nominal wall",
                "three synthetic inlet centers converging over 130 mm",
                "215 mm total axial envelope",
                "single open 3-to-1 flow shell without flanges or heat exchanger",
            ],
            "not_claimed": "No Porsche or Kline surface, tube path, flange, port, heat exchanger, fitment or performance is claimed.",
        },
        "synthetic_cases": {
            "engine_displacement_l": ENGINE_DISPLACEMENT_L,
            "engine_speed_rpm": ENGINE_SPEED_RPM,
            "volumetric_efficiency": VOLUMETRIC_EFFICIENCY,
            "intake_reference_k": INTAKE_REFERENCE_K,
            "exhaust_gas_k": EXHAUST_GAS_K,
            "screen_surface_k": SCREEN_SURFACE_K,
            "screen_gauge_pressure_pa": SCREEN_GAUGE_PRESSURE_PA,
            "junction_loss_coefficient": JUNCTION_LOSS_COEFFICIENT,
            "authority": "regression inputs only; no measured M64/60 flow, pulse, pressure, temperature, lambda, ignition, turbine or duty-cycle data",
        },
        "material_screen": {
            "candidate": "EOS NickelAlloy IN625 / UNS N06625, LPBF study only",
            "density_g_cm3": DENSITY_G_CM3,
            "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
            "comparison_yield_strength_mpa": COMPARISON_YIELD_STRENGTH_MPA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "thermal_conductivity_w_mk": THERMAL_CONDUCTIVITY_W_MK,
            "specific_heat_j_kg_k": SPECIFIC_HEAT_J_KG_K,
            "scope": "ambient LPBF and wrought thermal references only; no hot thin-wall LPBF fatigue or creep allowables",
        },
        "results": {
            "cad_volume_mm3": volume_mm3,
            "screening_mass_flow_core_g": mass_g,
            "published_mass_each_with_heat_exchanger_g": published_mass_g,
            "flow_core_to_published_assembly_mass_ratio": (
                mass_g / published_mass_g if mass_g else 0.0
            ),
            "primary_centerline_lengths_mm": primary_centerline_lengths_mm(),
            "mean_primary_centerline_length_mm": mean_primary_length_mm,
            "primary_flow_area_each_m2": primary_area_m2,
            "collector_flow_area_m2": collector_area_m2,
            "collector_to_three_primary_area_ratio": (
                collector_area_m2 / (3.0 * primary_area_m2)
            ),
            "cold_volume_flow_total_m3_s": cold_volume_flow_total_m3_s,
            "hot_volume_flow_bank_m3_s": hot_volume_flow_bank_m3_s,
            "hot_volume_flow_primary_m3_s": hot_volume_flow_primary_m3_s,
            "hot_density_kg_m3": hot_density_kg_m3,
            "primary_velocity_m_s": primary_velocity_m_s,
            "collector_velocity_m_s": collector_velocity_m_s,
            "primary_reynolds": primary_reynolds,
            "collector_reynolds": collector_reynolds,
            "collector_mach": collector_velocity_m_s / speed_of_sound_m_s,
            "screening_junction_pressure_loss_pa": junction_pressure_loss_pa,
            "screening_flow_power_bank_w": (
                junction_pressure_loss_pa * hot_volume_flow_bank_m3_s
            ),
            "thin_wall_hoop_stress_mpa": hoop_stress_mpa,
            "ambient_yield_to_hoop_ratio": (
                COMPARISON_YIELD_STRENGTH_MPA / hoop_stress_mpa
            ),
            "collector_pressure_force_n": pressure_force_n,
            "free_thermal_expansion_mm": free_expansion_mm,
            "fully_constrained_elastic_thermal_stress_mpa": fully_constrained_stress_mpa,
            "outer_lateral_area_approx_m2": lateral_area_m2,
            "radiative_flux_at_screen_surface_w_m2": radiative_flux_w_m2,
            "radiative_power_approx_w": radiative_flux_w_m2 * lateral_area_m2,
            "wall_through_thickness_resistance_m2_k_w": (
                wall_m / THERMAL_CONDUCTIVITY_W_MK
            ),
            "lumped_heat_capacity_flow_core_j_k": (
                mass_g / 1000.0 * SPECIFIC_HEAT_J_KG_K
            ),
            "bank_pulse_frequency_hz": bank_pulse_frequency_hz,
            "acoustic_path_mm": acoustic_path_mm,
            "path_quarter_wave_hz": path_quarter_wave_hz,
            "first_order_quarter_wave_length_mm": first_order_quarter_wave_length_mm,
        },
        "equations": {
            "mass": "m=rho*Vcad",
            "four_stroke_flow": "Qcold=Vd*N*eta_v/(2*60); Qhot,bank=Qcold/2*Thot/Tref",
            "continuity": "u_primary=(Qhot,bank/3)/Aprimary; u_collector=Qhot,bank/Acollector",
            "hot_density": "rho_hot=rho_ref*Tref/Thot",
            "reynolds": "Re=rho*u*D/mu",
            "mach": "M=u/sqrt(gamma*R*T)",
            "minor_loss_screen": "delta_p=K*rho*u_collector^2/2; P=delta_p*Qhot,bank",
            "thin_wall_pressure": "sigma_hoop=p*r/t; Faxial=p*Acollector",
            "free_thermal_expansion": "delta_L=alpha*L*delta_T",
            "fully_constrained_thermal_stress": "sigma_th=E*alpha*delta_T",
            "radiation": "q=epsilon*sigma_SB*A*(Tsurface^4-Tambient^4)",
            "thermal_resistance": "R_double_prime=t/k",
            "bank_pulse_frequency": "f=N/60*n_cyl_bank/2",
            "quarter_wave": "f1=a/(4*L); L1=a/(4*f_bank)",
        },
        "dfam_screen": {
            "part_consolidation": "three converging primaries and one collector in a single thin-wall BREP",
            "connected_internal_flow_volume": True,
            "open_inlets": 3,
            "open_outlets": 1,
            "trapped_powder_volume": False,
            "nominal_wall_mm": NOMINAL_WALL_MM,
            "internal_supports_allowed": False,
            "machining_allowance_defined": False,
            "orientation_selected": False,
            "process_comparison_required": [
                "bent and welded IN625 or stainless thin-wall manifold",
                "LPBF IN625 integrated 3-to-1 merge flow shell",
            ],
        },
        "interpretation": {
            "flow": "steady equal-bank ideal-gas screen; pulses, scavenging, bends, roughness, heat loss, turbine and lambda are absent",
            "mechanics": "thin-wall pressure membrane only; welds, flanges, supports, vibration, creep and fatigue are absent",
            "thermal": "uniform temperatures, free expansion and radiation screen only; no CHT, shielding, cabin heat or oxidation model",
            "constraint": "fully constrained elastic stress exceeds the ambient comparison value and is a warning, not a predicted hot stress",
            "mass": "2.9 kg includes the commercial heat exchanger; the F0 flow-core mass is not a like-for-like validation",
            "physicsnemo": "deferred until converged CFD/CHT/structure cases and physical correlation provide train, holdout and OOD datasets",
            "simready": "deferred until measured ports, routes, supports, turbine interface, heat exchanger and installed clearances exist",
        },
        "release_blockers": [
            "No measured Kline or factory manifold, exhaust ports, flanges, turbine interfaces, routes, supports, joints, clearances or tolerances.",
            "The published 2.9 kg includes the heat exchanger and cannot validate the F0 flow-core mass.",
            "No published 993 Turbo primary diameter, collector diameter, wall, merge length or tube centerline.",
            "No measured M64/60 exhaust flow, pulse, pressure, temperature, lambda, ignition, turbine map or duty cycle.",
            "No hot thin-wall LPBF material card, creep, oxidation, fatigue, anisotropy or surface-condition allowable.",
            "No heat-exchanger shell, cabin-air path, leak boundary or carbon-monoxide safety analysis.",
            "No build orientation, support strategy, recoater check, machining stock or distortion compensation.",
            "No transient compressible CFD, CHT, shell/contact/modal FEA, creep or thermal-fatigue calculation.",
            "No dimensional inspection, CT, ressuage, leak, pressure, thermal-cycle, shaker, dyno or vehicle fit test.",
            "No professional engine/exhaust engineering review or approved validation plan.",
        ],
        "manufacturing_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


def _lofted_circle(radius_mm: float, start: tuple[float, float], end: tuple[float, float]):
    from build123d import BuildSketch, Circle, Locations, Plane, loft

    with BuildSketch(Plane.XY) as lower:
        with Locations(start):
            Circle(radius_mm)
    with BuildSketch(Plane.XY.offset(MERGE_Z_MM)) as upper:
        with Locations(end):
            Circle(radius_mm)
    return loft([lower.sketch, upper.sketch])


def build_geometry():
    from build123d import Align, Cylinder, Pos

    primary_outer_radius_mm = PRIMARY_INNER_DIAMETER_MM / 2.0 + NOMINAL_WALL_MM
    primary_inner_radius_mm = PRIMARY_INNER_DIAMETER_MM / 2.0
    collector_outer_radius_mm = COLLECTOR_INNER_DIAMETER_MM / 2.0 + NOMINAL_WALL_MM
    collector_inner_radius_mm = COLLECTOR_INNER_DIAMETER_MM / 2.0
    collector_length_mm = TOTAL_LENGTH_MM - COLLECTOR_START_Z_MM
    align_min_z = (Align.CENTER, Align.CENTER, Align.MIN)

    outer = Pos(0.0, 0.0, COLLECTOR_START_Z_MM) * Cylinder(
        collector_outer_radius_mm,
        collector_length_mm,
        align=align_min_z,
    )
    flow_volume = Pos(0.0, 0.0, COLLECTOR_START_Z_MM) * Cylinder(
        collector_inner_radius_mm,
        collector_length_mm,
        align=align_min_z,
    )
    for start, end in zip(PRIMARY_START_CENTERS_MM, PRIMARY_END_CENTERS_MM):
        outer = outer + _lofted_circle(primary_outer_radius_mm, start, end)
        flow_volume = flow_volume + _lofted_circle(
            primary_inner_radius_mm, start, end
        )
    return outer - flow_volume, flow_volume


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    cad_volume_mm3 = None
    solid = None
    flow_volume = None
    envelope = None
    if args.out:
        from build123d import export_step, import_step

        solid, flow_volume = build_geometry()
        if not solid.is_valid or len(solid.solids()) != 1:
            raise SystemExit("Le concept OCCT n'est pas un solide BREP unique valide.")
        if not flow_volume.is_valid or len(flow_volume.solids()) != 1:
            raise SystemExit("Le volume interne trois-en-un n'est pas connecté.")
        bbox = solid.bounding_box()
        envelope = [bbox.size.X, bbox.size.Y, bbox.size.Z]

        args.out.parent.mkdir(parents=True, exist_ok=True)
        export_step(solid, str(args.out))
        roundtrip = import_step(str(args.out))
        if not roundtrip.is_valid or len(roundtrip.solids()) != 1:
            raise SystemExit("Le STEP relu n'est pas un solide BREP unique valide.")
        if abs(roundtrip.volume - solid.volume) > 0.05:
            raise SystemExit("Le STEP relu ne reproduit pas le volume OCCT attendu.")
        cad_volume_mm3 = roundtrip.volume

    report = engineering_screen(cad_volume_mm3)
    if solid is not None and flow_volume is not None and envelope is not None:
        report["step_roundtrip"] = {
            "status": "passed",
            "valid_brep": True,
            "solid_count": 1,
            "connected_flow_volume_count": 1,
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
