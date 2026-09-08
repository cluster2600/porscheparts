#!/usr/bin/env python3
"""End-tank d'intercooler 993 Turbo, concept AlSi10Mg LPBF F0."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PART_ID = "993-ENG-INTERCOOLER-END-TANK-ALSI10MG-F0-0001"

# Valeurs publiées pour l'intercooler aftermarket complet, pas pour cet end-tank.
PUBLISHED_CORE_DIMENSIONS_MM = (260.0, 260.0, 100.0)
PUBLISHED_OUTER_CONNECTION_DIAMETER_MM = 66.0
PUBLISHED_INNER_CONNECTION_DIAMETER_MM = 68.0
PUBLISHED_MAXIMUM_WIDTH_MM = 860.0
PUBLISHED_MAXIMUM_HEIGHT_MM = 240.0
PUBLISHED_MOUNT_SPACING_MM = 690.0
PUBLISHED_ASSEMBLY_MATERIAL = "aluminium, exact alloy not disclosed"

# Interprétation/géométrie F0 indépendante.
CORE_FACE_WIDTH_MM = 260.0
CORE_FACE_HEIGHT_MM = 100.0
TRANSITION_LENGTH_MM = 120.0
NOMINAL_WALL_MM = 2.2
CORE_FLANGE_AXIAL_MM = 6.0
CORE_FLANGE_MARGIN_MM = 7.0
PORT_COLLAR_AXIAL_MM = 8.0
FLOW_GUIDE_COUNT = 3
FLOW_GUIDE_THICKNESS_MM = 1.5
FLOW_GUIDE_START_X_MM = 5.0
FLOW_GUIDE_END_X_MM = 100.0
FLOW_GUIDE_Z_MM = (-25.0, 0.0, 25.0)

# AlSi10Mg : valeurs génériques de criblage, pas une carte admissible fournisseur.
DENSITY_G_CM3 = 2.67
ELASTIC_MODULUS_MPA = 70_000.0
POISSON_RATIO = 0.33
COMPARISON_YIELD_STRENGTH_MPA = 245.0
THERMAL_EXPANSION_PER_K = 21.0e-6

# Cas de débit, pression et température synthétique.
ENGINE_DISPLACEMENT_L = 3.6
ENGINE_SPEED_RPM = 5750.0
VOLUMETRIC_EFFICIENCY = 0.95
MANIFOLD_ABSOLUTE_PRESSURE_PA = 180_000.0
MANIFOLD_TEMPERATURE_K = 330.0
AIR_GAS_CONSTANT_J_KG_K = 287.0
AIR_DYNAMIC_VISCOSITY_PA_S = 1.9e-5
CORE_OPEN_AREA_RATIO = 0.65
SCREEN_GAUGE_PRESSURE_PA = 80_000.0
SCREEN_DELTA_T_K = 100.0
SCREEN_DUTY_HOURS = 100.0
RECTANGULAR_PANEL_COEFFICIENT = 0.308


def engineering_screen(cad_volume_mm3: float | None = None) -> dict[str, object]:
    cad_mass_g = (
        cad_volume_mm3 / 1000.0 * DENSITY_G_CM3
        if cad_volume_mm3 is not None
        else None
    )
    port_inner_diameter_mm = (
        PUBLISHED_OUTER_CONNECTION_DIAMETER_MM - 2.0 * NOMINAL_WALL_MM
    )
    port_flow_area_m2 = math.pi * (port_inner_diameter_mm / 2000.0) ** 2
    core_geometric_area_m2 = CORE_FACE_WIDTH_MM * CORE_FACE_HEIGHT_MM / 1_000_000.0
    core_open_area_m2 = core_geometric_area_m2 * CORE_OPEN_AREA_RATIO
    total_volume_flow_m3_s = (
        ENGINE_DISPLACEMENT_L
        / 1000.0
        * ENGINE_SPEED_RPM
        / (2.0 * 60.0)
        * VOLUMETRIC_EFFICIENCY
    )
    bank_volume_flow_m3_s = total_volume_flow_m3_s / 2.0
    air_density_kg_m3 = (
        MANIFOLD_ABSOLUTE_PRESSURE_PA
        / (AIR_GAS_CONSTANT_J_KG_K * MANIFOLD_TEMPERATURE_K)
    )
    mass_flow_bank_kg_s = bank_volume_flow_m3_s * air_density_kg_m3
    port_velocity_m_s = bank_volume_flow_m3_s / port_flow_area_m2
    core_velocity_m_s = bank_volume_flow_m3_s / core_open_area_m2
    port_reynolds = (
        air_density_kg_m3
        * port_velocity_m_s
        * (port_inner_diameter_mm / 1000.0)
        / AIR_DYNAMIC_VISCOSITY_PA_S
    )
    area_ratio = core_open_area_m2 / port_flow_area_m2
    port_dynamic_pressure_pa = 0.5 * air_density_kg_m3 * port_velocity_m_s**2
    sudden_expansion_loss_coefficient = (1.0 - 1.0 / area_ratio) ** 2
    expansion_pressure_loss_pa = (
        sudden_expansion_loss_coefficient * port_dynamic_pressure_pa
    )
    kinetic_pressure_recovery_pa = (
        0.5
        * air_density_kg_m3
        * (port_velocity_m_s**2 - core_velocity_m_s**2)
    )
    flow_power_loss_w = expansion_pressure_loss_pa * bank_volume_flow_m3_s

    port_hoop_stress_mpa = (
        SCREEN_GAUGE_PRESSURE_PA
        / 1_000_000.0
        * (PUBLISHED_OUTER_CONNECTION_DIAMETER_MM / 2.0)
        / NOMINAL_WALL_MM
    )
    unsupported_panel_bay_mm = CORE_FACE_HEIGHT_MM / (FLOW_GUIDE_COUNT + 1)
    panel_bending_stress_mpa = (
        RECTANGULAR_PANEL_COEFFICIENT
        * (SCREEN_GAUGE_PRESSURE_PA / 1_000_000.0)
        * (unsupported_panel_bay_mm / NOMINAL_WALL_MM) ** 2
    )
    core_face_pressure_force_n = SCREEN_GAUGE_PRESSURE_PA * core_geometric_area_m2
    free_width_growth_mm = (
        THERMAL_EXPANSION_PER_K
        * (CORE_FACE_WIDTH_MM + 2.0 * CORE_FLANGE_MARGIN_MM)
        * SCREEN_DELTA_T_K
    )
    constrained_elastic_thermal_stress_mpa = (
        ELASTIC_MODULUS_MPA * THERMAL_EXPANSION_PER_K * SCREEN_DELTA_T_K
    )
    bank_pulse_frequency_hz = ENGINE_SPEED_RPM / 60.0 * 3.0 / 2.0
    cycles = bank_pulse_frequency_hz * SCREEN_DUTY_HOURS * 3600.0

    return {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "status": "f0_published_intercooler_dimensions_clean_sheet_end_tank_screen_only",
        "geometry_authority": {
            "published": {
                "two_core_dimensions_mm": list(PUBLISHED_CORE_DIMENSIONS_MM),
                "outer_connection_diameter_mm": PUBLISHED_OUTER_CONNECTION_DIAMETER_MM,
                "inner_connection_diameter_mm": PUBLISHED_INNER_CONNECTION_DIAMETER_MM,
                "assembly_maximum_width_mm": PUBLISHED_MAXIMUM_WIDTH_MM,
                "assembly_maximum_height_mm": PUBLISHED_MAXIMUM_HEIGHT_MM,
                "assembly_mount_spacing_mm": PUBLISHED_MOUNT_SPACING_MM,
                "assembly_material": PUBLISHED_ASSEMBLY_MATERIAL,
            },
            "interpretations": [
                "260 x 100 mm is used as one rectangular core face; published dimension orientation is not a drawing",
                "66 mm published outside connection is used as the F0 circular outer diameter",
                "the separate 68 mm inner connection is not represented by this single outer end-tank",
                "AlSi10Mg is a separate LPBF candidate; the commercial aluminium alloy is not disclosed",
            ],
            "hypotheses": [
                "120 mm centered round-to-rectangle transition",
                "2.2 mm nominal shell and 7 mm rectangular flange margin",
                "three 1.5 mm open internal guides ending before the circular port",
                "8 mm circular collar and no hose bead",
                "no mounts, weld preparation, core braze, left/right handedness or installed clearances",
            ],
            "not_claimed": "No TA Technix, Albert Motorsport, Porsche or production intercooler surface, end-tank geometry, flow distribution, fitment or pressure capability is claimed.",
        },
        "synthetic_flow_case": {
            "engine_displacement_l": ENGINE_DISPLACEMENT_L,
            "engine_speed_rpm": ENGINE_SPEED_RPM,
            "volumetric_efficiency": VOLUMETRIC_EFFICIENCY,
            "manifold_absolute_pressure_pa": MANIFOLD_ABSOLUTE_PRESSURE_PA,
            "manifold_temperature_k": MANIFOLD_TEMPERATURE_K,
            "core_open_area_ratio": CORE_OPEN_AREA_RATIO,
            "screen_gauge_pressure_pa": SCREEN_GAUGE_PRESSURE_PA,
            "delta_t_k": SCREEN_DELTA_T_K,
            "duty_hours": SCREEN_DUTY_HOURS,
            "authority": "regression inputs only; no target intercooler flow, boost, temperature, core porosity or duty trace was measured",
        },
        "material_screen": {
            "candidate": "EOS Aluminium AlSi10Mg LPBF, study only",
            "density_g_cm3": DENSITY_G_CM3,
            "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
            "poisson_ratio": POISSON_RATIO,
            "comparison_yield_strength_mpa": COMPARISON_YIELD_STRENGTH_MPA,
            "thermal_expansion_per_k": THERMAL_EXPANSION_PER_K,
            "scope": "generic screening values; no machine, orientation, heat-treatment, weld/braze, pressure-fatigue or temperature-specific allowable",
        },
        "results": {
            "cad_volume_mm3": cad_volume_mm3,
            "cad_mass_g": cad_mass_g,
            "port_inner_diameter_screen_mm": port_inner_diameter_mm,
            "port_flow_area_m2": port_flow_area_m2,
            "core_geometric_area_m2": core_geometric_area_m2,
            "core_open_area_m2": core_open_area_m2,
            "total_engine_volume_flow_m3_s": total_volume_flow_m3_s,
            "bank_volume_flow_m3_s": bank_volume_flow_m3_s,
            "air_density_kg_m3": air_density_kg_m3,
            "mass_flow_bank_kg_s": mass_flow_bank_kg_s,
            "port_velocity_m_s": port_velocity_m_s,
            "core_face_velocity_m_s": core_velocity_m_s,
            "port_reynolds": port_reynolds,
            "effective_area_ratio": area_ratio,
            "port_dynamic_pressure_pa": port_dynamic_pressure_pa,
            "sudden_expansion_loss_coefficient": sudden_expansion_loss_coefficient,
            "screening_expansion_pressure_loss_pa": expansion_pressure_loss_pa,
            "ideal_kinetic_pressure_recovery_pa": kinetic_pressure_recovery_pa,
            "screening_flow_power_loss_w": flow_power_loss_w,
            "port_thin_wall_hoop_stress_mpa": port_hoop_stress_mpa,
            "unsupported_panel_bay_mm": unsupported_panel_bay_mm,
            "guided_panel_bending_stress_screen_mpa": panel_bending_stress_mpa,
            "ambient_yield_to_panel_stress_ratio": COMPARISON_YIELD_STRENGTH_MPA / panel_bending_stress_mpa,
            "core_face_pressure_force_n": core_face_pressure_force_n,
            "free_flange_width_growth_mm": free_width_growth_mm,
            "fully_constrained_elastic_thermal_stress_mpa": constrained_elastic_thermal_stress_mpa,
            "ambient_yield_to_constrained_thermal_ratio": COMPARISON_YIELD_STRENGTH_MPA / constrained_elastic_thermal_stress_mpa,
            "bank_pulse_frequency_hz": bank_pulse_frequency_hz,
            "pressure_pulses_at_duty": cycles,
        },
        "equations": {
            "four_stroke_flow": "Q_total=Vd*N/(2*60)*VE; Q_bank=Q_total/2",
            "ideal_gas_density": "rho=p_abs/(R*T)",
            "continuity": "v=Q/A; m_dot=rho*Q",
            "reynolds": "Re=rho*v*D/mu",
            "sudden_expansion": "K=(1-A1/A2)^2; delta_p=K*rho*v1^2/2",
            "kinetic_recovery": "delta_p_ideal=rho*(v1^2-v2^2)/2",
            "flow_power": "P_loss=delta_p*Q",
            "thin_wall_port": "sigma_hoop=p*r/t",
            "guided_panel": "sigma=C*p*(bay/t)^2",
            "pressure_force": "F=p*A_core",
            "thermal_expansion": "delta_W=alpha*W*delta_T",
            "fully_constrained_thermal": "sigma=E*alpha*delta_T",
            "pressure_cycles": "n=(N/60)*(3/2)*t_seconds",
            "mass": "m=rho*Vcad",
        },
        "dfam_screen": {
            "additive_value": "smooth round-to-rectangle transition, integrated guides and flange can be printed as one open inspectable part",
            "open_flow_path": True,
            "trapped_powder_volume": False,
            "integrated_flow_guides": FLOW_GUIDE_COUNT,
            "minimum_nominal_wall_mm": FLOW_GUIDE_THICKNESS_MM,
            "orientation_selected": False,
            "support_strategy_defined": False,
            "core_and_hose_interfaces_require_machining": True,
            "process_comparison_required": [
                "TIG-welded aluminium sheet end-tank",
                "cast aluminium end-tank plus machining",
                "LPBF AlSi10Mg end-tank with integrated guides",
            ],
        },
        "interpretation": {
            "flow": "steady equal-bank incompressible screen; compressor map, pulses, bends, core resistance, heat transfer and leakage are absent",
            "mechanics": "thin-wall and guided flat-panel formulas omit loft curvature, guide junctions, flange, braze/weld, vibration and fatigue",
            "thermal": "free and fully constrained bounds are mutually exclusive limits, not a coupled thermal-stress prediction",
            "mass": "CAD mass covers one synthetic end-tank only and is not comparable to the published 14 kg two-core assembly",
            "physicsnemo": "deferred until correlated CFD/CHT/pressure-structure cases define train, holdout and OOD sets",
            "simready": "deferred until both cores, end-tanks, hoses, supports, decklid and installed clearances are measured",
        },
        "release_blockers": [
            "No measured TA Technix, Albert Motorsport or factory end-tank, core face, port, flange, weld/braze, mount or installed clearance.",
            "The published 260 x 260 x 100 mm values do not define which dimensions form the end-tank core face.",
            "The 66 and 68 mm connections describe different assembly positions and do not define wall, bead, hose overlap or tolerance.",
            "The commercial product is aluminium but its alloy, temper, sheet/cast route, weld filler and heat treatment are undisclosed.",
            "No target core pressure-drop curve, open-area ratio, heat rejection, charge flow, temperature or boost duty trace.",
            "No compressor maps, throttle transients, surge case, pressure pulses, engine movement, vibration or backfire load.",
            "No 3D CFD flow-uniformity, conjugate heat transfer, pressure-structure FEA, modal, weld/braze or fatigue analysis.",
            "No qualified AlSi10Mg card for thin walls, guide junctions, orientation, roughness, heat treatment, porosity and temperature.",
            "No orientation, supports, recoater, distortion compensation, machining stock or sealing-surface definition.",
            "No CT, dimensional inspection, roughness, leak, proof pressure, burst, pressure-cycle, thermal-cycle or shaker test.",
            "No verified left/right handedness, pair assembly, hose routing, decklid duct, support or vehicle fit.",
            "No professional charge-air engineering review or approved validation plan.",
        ],
        "manufacturing_authorized": False,
        "engine_operation_authorized": False,
        "release_authorized": False,
    }


def _loft_rectangle_to_circle(
    rectangle_width_mm: float,
    rectangle_height_mm: float,
    circle_radius_mm: float,
):
    from build123d import BuildSketch, Circle, Plane, Rectangle, loft

    with BuildSketch(Plane.YZ) as rectangular:
        Rectangle(rectangle_width_mm, rectangle_height_mm)
    with BuildSketch(Plane.YZ.offset(TRANSITION_LENGTH_MM)) as circular:
        Circle(circle_radius_mm)
    return loft([rectangular.sketch, circular.sketch])


def _cylinder_x(radius_mm: float, length_mm: float, center_x_mm: float):
    from build123d import Align, Cylinder, Pos, Rot

    return Pos(center_x_mm, 0.0, 0.0) * Rot(0.0, 90.0, 0.0) * Cylinder(
        radius_mm,
        length_mm,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )


def build_geometry():
    from build123d import Align, Box, Pos

    outer = _loft_rectangle_to_circle(
        CORE_FACE_WIDTH_MM + 2.0 * NOMINAL_WALL_MM,
        CORE_FACE_HEIGHT_MM + 2.0 * NOMINAL_WALL_MM,
        PUBLISHED_OUTER_CONNECTION_DIAMETER_MM / 2.0,
    )
    inner = _loft_rectangle_to_circle(
        CORE_FACE_WIDTH_MM,
        CORE_FACE_HEIGHT_MM,
        PUBLISHED_OUTER_CONNECTION_DIAMETER_MM / 2.0 - NOMINAL_WALL_MM,
    )
    shell = outer - inner

    align_min_x = (Align.MIN, Align.CENTER, Align.CENTER)
    flange_outer = Pos(-CORE_FLANGE_AXIAL_MM, 0.0, 0.0) * Box(
        CORE_FLANGE_AXIAL_MM,
        CORE_FACE_WIDTH_MM + 2.0 * CORE_FLANGE_MARGIN_MM,
        CORE_FACE_HEIGHT_MM + 2.0 * CORE_FLANGE_MARGIN_MM,
        align=align_min_x,
    )
    flange_inner = Pos(-CORE_FLANGE_AXIAL_MM - 0.5, 0.0, 0.0) * Box(
        CORE_FLANGE_AXIAL_MM + 1.0,
        CORE_FACE_WIDTH_MM,
        CORE_FACE_HEIGHT_MM,
        align=align_min_x,
    )
    shell = shell + (flange_outer - flange_inner)

    collar_outer = _cylinder_x(
        PUBLISHED_OUTER_CONNECTION_DIAMETER_MM / 2.0,
        PORT_COLLAR_AXIAL_MM,
        TRANSITION_LENGTH_MM + PORT_COLLAR_AXIAL_MM / 2.0,
    )
    collar_inner = _cylinder_x(
        PUBLISHED_OUTER_CONNECTION_DIAMETER_MM / 2.0 - NOMINAL_WALL_MM,
        PORT_COLLAR_AXIAL_MM + 1.0,
        TRANSITION_LENGTH_MM + PORT_COLLAR_AXIAL_MM / 2.0,
    )
    shell = shell + (collar_outer - collar_inner)

    guide_length = FLOW_GUIDE_END_X_MM - FLOW_GUIDE_START_X_MM
    guide_union = None
    for z_mm in FLOW_GUIDE_Z_MM:
        guide_box = Pos(FLOW_GUIDE_START_X_MM, 0.0, z_mm) * Box(
            guide_length,
            CORE_FACE_WIDTH_MM,
            FLOW_GUIDE_THICKNESS_MM,
            align=align_min_x,
        )
        guide = guide_box & outer
        guide_union = guide if guide_union is None else guide_union + guide
    solid = shell + guide_union
    flow_volume = inner - guide_union
    return solid, flow_volume


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
            raise SystemExit("Le F0 doit contenir exactement un solide BREP valide.")
        if not flow_volume.is_valid or len(flow_volume.solids()) != 1:
            raise SystemExit("Le volume fluide doit rester connecté de la face au port.")
        bbox = solid.bounding_box()
        envelope = [bbox.size.X, bbox.size.Y, bbox.size.Z]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        export_step(solid, str(args.out))
        roundtrip = import_step(str(args.out))
        if not roundtrip.is_valid or len(roundtrip.solids()) != 1:
            raise SystemExit("Le STEP relu ne conserve pas le solide valide.")
        if abs(roundtrip.volume - solid.volume) > 0.05:
            raise SystemExit("Le STEP relu ne reproduit pas le volume OCCT attendu.")
        cad_volume_mm3 = roundtrip.volume

    report = engineering_screen(cad_volume_mm3)
    if solid is not None and flow_volume is not None and envelope is not None:
        report["step_roundtrip"] = {
            "status": "passed",
            "valid_brep": True,
            "solid_count": 1,
            "semantic_solids": ["end_tank_shell_flange_collar_and_guides"],
            "connected_flow_volume_count": len(flow_volume.solids()),
            "volume_mm3": cad_volume_mm3,
            "envelope_mm": envelope,
            "flow_guide_count": FLOW_GUIDE_COUNT,
            "open_ports": ["rectangular_core_face", "round_hose_port"],
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
