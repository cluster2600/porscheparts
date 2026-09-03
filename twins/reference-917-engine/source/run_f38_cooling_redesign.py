#!/usr/bin/env python3
"""Prépare, résume et illustre le recoupement thermique F38.

La méthode A est un canal inter-ailettes OpenFOAM compressible RANS. La méthode
B est une corrélation de Gnielinski avec efficacité d'ailette. Les deux
méthodes partagent uniquement géométrie, propriétés et conditions limites.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path


def header(name: str, class_name: str = "dictionary", location: str | None = None) -> str:
    location_line = f'    location "{location}";\n' if location else ""
    return (
        "FoamFile\n{\n    format ascii;\n"
        f"    class {class_name};\n{location_line}    object {name};\n}}\n\n"
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_field(
    case: Path,
    name: str,
    dimensions: str,
    internal: str,
    boundaries: str,
    class_name: str = "volScalarField",
) -> None:
    (case / "0" / name).write_text(
        header(name, class_name, "0")
        + f"dimensions {dimensions};\ninternalField uniform {internal};\nboundaryField\n{{\n{boundaries}\n}}\n",
        encoding="utf-8",
    )


def prepare_case(case: Path, contract: dict, cells: list[int], end_time: int = 1200) -> None:
    case.mkdir(parents=True, exist_ok=False)
    for directory in (case / "0", case / "constant", case / "system"):
        directory.mkdir(parents=True, exist_ok=True)
    reference = contract["openfoam_reference_case"]
    bc = contract["boundary_conditions"]
    length = float(reference["length_m"])
    gap = float(reference["gap_m"])
    span = float(reference["span_m"])
    velocity = float(reference["velocity_m_s"])
    nx, ny, nz = cells
    (case / "system/blockMeshDict").write_text(
        header("blockMeshDict")
        + f"""convertToMeters 1;
vertices
(
    (0 0 0) ({length} 0 0) ({length} {gap} 0) (0 {gap} 0)
    (0 0 {span}) ({length} 0 {span}) ({length} {gap} {span}) (0 {gap} {span})
);
blocks (hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1));
edges ();
boundary
(
    inlet {{ type patch; faces ((0 3 7 4)); }}
    outlet {{ type patch; faces ((1 2 6 5)); }}
    hotFins {{ type wall; faces ((0 1 5 4) (3 2 6 7)); }}
    symmetryZmin {{ type symmetryPlane; faces ((0 1 2 3)); }}
    symmetryZmax {{ type symmetryPlane; faces ((4 5 6 7)); }}
);
""",
        encoding="utf-8",
    )
    (case / "system/controlDict").write_text(
        header("controlDict", location="system")
        + """solver fluid;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime __END_TIME__;
deltaT 1;
writeControl timeStep;
writeInterval __END_TIME__;
writeFormat ascii;
writePrecision 12;
runTimeModifiable false;
functions
{
    inletMassFlow
    {
        type surfaceFieldValue;
        libs ("libfieldFunctionObjects.so");
        writeControl timeStep;
        writeInterval 25;
        writeFields false;
        patch inlet;
        operation sum;
        fields (phi);
    }
    outletMassFlow
    {
        type surfaceFieldValue;
        libs ("libfieldFunctionObjects.so");
        writeControl timeStep;
        writeInterval 25;
        writeFields false;
        patch outlet;
        operation sum;
        fields (phi);
    }
    outletTemperature
    {
        type surfaceFieldValue;
        libs ("libfieldFunctionObjects.so");
        writeControl timeStep;
        writeInterval 25;
        writeFields false;
        patch outlet;
        operation areaAverage;
        weightField phi;
        fields (T);
    }
    inletPressure
    {
        type surfaceFieldValue;
        libs ("libfieldFunctionObjects.so");
        writeControl timeStep;
        writeInterval 25;
        writeFields false;
        patch inlet;
        operation areaAverage;
        fields (p);
    }
    outletPressure
    {
        type surfaceFieldValue;
        libs ("libfieldFunctionObjects.so");
        writeControl timeStep;
        writeInterval 25;
        writeFields false;
        patch outlet;
        operation areaAverage;
        fields (p);
    }
    finHeatFlux
    {
        type wallHeatFlux;
        libs ("libfieldFunctionObjects.so");
        writeControl timeStep;
        writeInterval 25;
        patches (hotFins);
    }
}
""".replace("__END_TIME__", str(end_time)),
        encoding="utf-8",
    )
    (case / "system/fvSchemes").write_text(
        header("fvSchemes", location="system")
        + """ddtSchemes { default steadyState; }
gradSchemes
{
    default Gauss linear;
    limited cellLimited Gauss linear 1;
    grad(U) $limited;
    grad(k) $limited;
    grad(omega) $limited;
}
divSchemes
{
    default none;
    div(phi,U) bounded Gauss linearUpwind limited;
    div(div(phi,U)) Gauss linear;
    energy bounded Gauss upwind;
    div(phi,K) $energy;
    div(phi,h) $energy;
    turbulence bounded Gauss upwind;
    div(phi,k) $turbulence;
    div(phi,omega) $turbulence;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear orthogonal; }
interpolationSchemes { default linear; }
snGradSchemes { default orthogonal; }
wallDist { method meshWave; }
fluxRequired { default no; p; }
""",
        encoding="utf-8",
    )
    (case / "system/fvSolution").write_text(
        header("fvSolution", location="system")
        + """solvers
{
    Phi { solver GAMG; smoother DIC; tolerance 1e-9; relTol 0.01; }
    p { solver GAMG; smoother DIC; tolerance 1e-8; relTol 0.01; }
    "(U|h|k|omega)" { solver PBiCGStab; preconditioner DILU; tolerance 1e-9; relTol 0.05; }
}
potentialFlow { nNonOrthogonalCorrectors 0; }
PIMPLE
{
    nNonOrthogonalCorrectors 0;
    residualControl { p 1e-6; U 1e-6; "(k|omega|h)" 1e-6; }
}
relaxationFactors
{
    fields { p 0.25; rho 0.02; }
    equations { U 0.35; h 0.25; "(k|omega)" 0.4; }
}
""",
        encoding="utf-8",
    )
    (case / "system/sampleDict").write_text(
        header("sampleDict", location="system")
        + f"""type sets;
libs ("libsampling.so");
interpolationScheme cellPoint;
setFormat raw;
sets
(
    centreLine
    {{
        type lineUniform;
        axis x;
        start (0 {gap / 2.0} {span / 2.0});
        end ({length} {gap / 2.0} {span / 2.0});
        nPoints 101;
    }}
);
fields (T);
""",
        encoding="utf-8",
    )
    (case / "constant/physicalProperties").write_text(
        header("physicalProperties", location="constant")
        + f"""thermoType
{{
    type hePsiThermo;
    mixture pureMixture;
    transport const;
    thermo hConst;
    equationOfState perfectGas;
    specie specie;
    energy sensibleEnthalpy;
}}
mixture
{{
    specie {{ molWeight 28.97; }}
    thermodynamics {{ Cp {bc['air_specific_heat_j_kgk']}; hf 0; }}
    transport {{ mu {bc['air_dynamic_viscosity_pa_s']}; Pr {bc['air_prandtl']}; }}
}}
""",
        encoding="utf-8",
    )
    (case / "constant/momentumTransport").write_text(
        header("momentumTransport", location="constant")
        + """simulationType RAS;
RAS { model kOmegaSST; turbulence on; printCoeffs on; }
""",
        encoding="utf-8",
    )
    temperature_in = float(bc["air_inlet_temperature_k"])
    temperature_wall = float(bc["isothermal_wall_temperature_k"])
    turbulence_intensity = 0.05
    hydraulic_diameter = 2.0 * gap * span / (gap + span)
    turbulent_length = 0.07 * hydraulic_diameter
    turbulent_k = 1.5 * (turbulence_intensity * velocity) ** 2
    turbulent_omega = math.sqrt(turbulent_k) / (0.09 ** 0.25 * turbulent_length)
    write_field(
        case,
        "U",
        "[0 1 -1 0 0 0 0]",
        f"({velocity} 0 0)",
        f"""    inlet {{ type fixedValue; value uniform ({velocity} 0 0); }}
    outlet {{ type pressureInletOutletVelocity; value uniform ({velocity} 0 0); }}
    hotFins {{ type noSlip; }}
    symmetryZmin {{ type symmetryPlane; }}
    symmetryZmax {{ type symmetryPlane; }}""",
        "volVectorField",
    )
    write_field(
        case,
        "p",
        "[1 -1 -2 0 0 0 0]",
        "100000",
        """    inlet { type zeroGradient; }
    outlet { type fixedValue; value uniform 100000; }
    hotFins { type zeroGradient; }
    symmetryZmin { type symmetryPlane; }
    symmetryZmax { type symmetryPlane; }""",
    )
    write_field(
        case,
        "T",
        "[0 0 0 1 0 0 0]",
        f"{temperature_in}",
        f"""    inlet {{ type fixedValue; value uniform {temperature_in}; }}
    outlet {{ type inletOutlet; inletValue uniform {temperature_in}; value uniform {temperature_in}; }}
    hotFins {{ type fixedValue; value uniform {temperature_wall}; }}
    symmetryZmin {{ type symmetryPlane; }}
    symmetryZmax {{ type symmetryPlane; }}""",
    )
    write_field(
        case,
        "k",
        "[0 2 -2 0 0 0 0]",
        f"{turbulent_k}",
        f"""    inlet {{ type fixedValue; value uniform {turbulent_k}; }}
    outlet {{ type inletOutlet; inletValue uniform {turbulent_k}; value uniform {turbulent_k}; }}
    hotFins {{ type kqRWallFunction; value uniform 1e-10; }}
    symmetryZmin {{ type symmetryPlane; }}
    symmetryZmax {{ type symmetryPlane; }}""",
    )
    write_field(
        case,
        "omega",
        "[0 0 -1 0 0 0 0]",
        f"{turbulent_omega}",
        f"""    inlet {{ type fixedValue; value uniform {turbulent_omega}; }}
    outlet {{ type inletOutlet; inletValue uniform {turbulent_omega}; value uniform {turbulent_omega}; }}
    hotFins {{ type omegaWallFunction; value uniform {turbulent_omega}; }}
    symmetryZmin {{ type symmetryPlane; }}
    symmetryZmax {{ type symmetryPlane; }}""",
    )
    write_field(
        case,
        "nut",
        "[0 2 -1 0 0 0 0]",
        "0",
        """    inlet { type calculated; value uniform 0; }
    outlet { type calculated; value uniform 0; }
    hotFins { type nutkWallFunction; value uniform 0; }
    symmetryZmin { type symmetryPlane; }
    symmetryZmax { type symmetryPlane; }""",
    )
    write_field(
        case,
        "alphat",
        "[1 -1 -1 0 0 0 0]",
        "1e-3",
        """    inlet { type calculated; value uniform 1e-3; }
    outlet { type calculated; value uniform 1e-3; }
    hotFins { type compressible::alphatWallFunction; value uniform 1e-3; }
    symmetryZmin { type symmetryPlane; }
    symmetryZmax { type symmetryPlane; }""",
    )
    (case / "case-metadata.json").write_text(
        json.dumps(
            {
                "classification": "F38_canonical_inter_fin_OpenFOAM_RANS_reference_not_full_head_CHT",
                "cells": cells,
                "length_m": length,
                "gap_m": gap,
                "span_m": span,
                "velocity_m_s": velocity,
                "wall_temperature_k": temperature_wall,
                "inlet_temperature_k": temperature_in,
                "hydraulic_diameter_m": hydraulic_diameter,
                "end_time_steps": end_time,
                "absolute_scale_confirmed": False,
                "release_claim": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def last_number(path: Path, column: int = -1) -> float:
    data = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.replace("(", " ").replace(")", " ").split()
        try:
            data.append(float(fields[column]))
        except (ValueError, IndexError):
            continue
    if not data:
        raise ValueError(f"aucune donnée numérique dans {path}")
    return data[-1]


def find_post(case: Path, function: str, field_fragment: str) -> Path:
    matches = sorted((case / "postProcessing" / function).glob(f"*/{field_fragment}"))
    if not matches:
        raise FileNotFoundError(f"sortie {function}/{field_fragment} absente")
    return matches[-1]


def parse_wall_heat_flux(path: Path) -> float:
    # wallHeatFlux.dat columns: time, min, max, integral. We need |integral|.
    # OpenFOAM 14 ajoute ensuite la moyenne surfacique q; Q est donc l'avant-dernière colonne.
    return abs(last_number(path, -2))


def parse_case(case: Path, contract: dict) -> dict:
    metadata = json.loads((case / "case-metadata.json").read_text(encoding="utf-8"))
    wall_file = find_post(case, "finHeatFlux", "wallHeatFlux.dat")
    inlet_mass = abs(last_number(find_post(case, "inletMassFlow", "surfaceFieldValue.dat")))
    outlet_mass = abs(last_number(find_post(case, "outletMassFlow", "surfaceFieldValue.dat")))
    outlet_temperature = last_number(find_post(case, "outletTemperature", "surfaceFieldValue.dat"))
    inlet_pressure = last_number(find_post(case, "inletPressure", "surfaceFieldValue.dat"))
    outlet_pressure = last_number(find_post(case, "outletPressure", "surfaceFieldValue.dat"))
    heat = parse_wall_heat_flux(wall_file)
    bc = contract["boundary_conditions"]
    area = 2.0 * metadata["length_m"] * metadata["span_m"]
    delta_t_lm_numerator = float(bc["isothermal_wall_temperature_k"]) - float(bc["air_inlet_temperature_k"])
    delta_t_lm_denominator = float(bc["isothermal_wall_temperature_k"]) - outlet_temperature
    if delta_t_lm_denominator <= 0 or outlet_temperature <= float(bc["air_inlet_temperature_k"]):
        delta_t_lm = delta_t_lm_numerator
    else:
        delta_t_lm = (delta_t_lm_numerator - delta_t_lm_denominator) / math.log(
            delta_t_lm_numerator / delta_t_lm_denominator
        )
    h = heat / (area * delta_t_lm)
    enthalpy_gain = outlet_mass * float(bc["air_specific_heat_j_kgk"]) * (
        outlet_temperature - float(bc["air_inlet_temperature_k"])
    )
    energy_error = abs(heat - enthalpy_gain) / max(heat, 1e-12)
    mass_error = abs(inlet_mass - outlet_mass) / max(inlet_mass, 1e-12)
    centreline_matches = sorted((case / "postProcessing/sampleDict").glob("*/centreLine*.xy"))
    centreline = []
    if centreline_matches:
        for line in centreline_matches[-1].read_text(encoding="utf-8").splitlines():
            fields = line.split()
            if len(fields) >= 2 and not line.startswith("#"):
                centreline.append([float(fields[0]), float(fields[-1])])
    return {
        "case_id": case.name,
        "cells": metadata["cells"],
        "cell_count": math.prod(metadata["cells"]),
        "mass_flow_in_kg_s": inlet_mass,
        "mass_flow_out_kg_s": outlet_mass,
        "mass_balance_relative": mass_error,
        "outlet_temperature_k": outlet_temperature,
        "wall_heat_w": heat,
        "air_enthalpy_gain_w": enthalpy_gain,
        "energy_balance_relative": energy_error,
        "effective_h_w_m2k": h,
        "pressure_drop_pa": inlet_pressure - outlet_pressure,
        "centreline_temperature_k": centreline,
        "metadata_sha256": sha256(case / "case-metadata.json"),
        "solver_log_sha256": sha256(case / "log.foamRun"),
    }


def analytical(contract: dict) -> dict:
    bc = contract["boundary_conditions"]
    design = contract["f38_fin_pack"]
    gap = float(design["clear_gap_mm"]) * 1e-3
    span = float(design["mean_span_mm"]) * 1e-3
    length = float(design["mean_flow_length_mm"]) * 1e-3
    velocity = float(design["passage_velocity_m_s"])
    rho = float(bc["air_density_kg_m3"])
    mu = float(bc["air_dynamic_viscosity_pa_s"])
    conductivity = float(bc["air_thermal_conductivity_w_mk"])
    prandtl = float(bc["air_prandtl"])
    hydraulic_diameter = 2.0 * gap * span / (gap + span)
    reynolds = rho * velocity * hydraulic_diameter / mu
    friction = (0.79 * math.log(reynolds) - 1.64) ** -2
    nusselt = (
        (friction / 8.0) * (reynolds - 1000.0) * prandtl
        / (1.0 + 12.7 * math.sqrt(friction / 8.0) * (prandtl ** (2.0 / 3.0) - 1.0))
    )
    h = nusselt * conductivity / hydraulic_diameter
    pressure = friction * (length / hydraulic_diameter) * 0.5 * rho * velocity**2
    fin_height = float(design["fin_height_mm"]) * 1e-3
    fin_thickness = float(design["fin_thickness_mm"]) * 1e-3
    solid_k = 135.0  # conservative F38 sensitivity, not a qualified hot coupon card
    m = math.sqrt(2.0 * h / (solid_k * fin_thickness))
    fin_efficiency = math.tanh(m * fin_height) / (m * fin_height)
    effective_h = h * fin_efficiency
    heat_load = float(bc["chamber_heat_load_w_per_head"])
    area = design["whole_head_wetted_surface_area_m2"]
    if area is None:
        area = float(design["provisional_flat_fin_face_area_m2_not_BRep"])
    else:
        area = float(area)
    inlet_k = float(bc["air_inlet_temperature_k"])
    root_c = inlet_k - 273.15 + heat_load / (effective_h * area)
    bridge_c = solve_bridge_temperature(contract, root_c, heat_load)
    mass_flow = float(bc["nominal_head_air_mass_flow_kg_s"])
    outlet_c = inlet_k - 273.15 + heat_load / (mass_flow * float(bc["air_specific_heat_j_kgk"]))
    return {
        "method": "Gnielinski_smooth_channel_plus_Darcy_Weisbach_plus_1D_adiabatic_tip_fin_efficiency",
        "hydraulic_diameter_m": hydraulic_diameter,
        "reynolds": reynolds,
        "darcy_friction_factor": friction,
        "nusselt": nusselt,
        "bare_channel_h_w_m2k": h,
        "fin_efficiency": fin_efficiency,
        "effective_h_w_m2k": effective_h,
        "pressure_drop_straight_channel_pa": pressure,
        "predicted_bridge_temperature_c": bridge_c,
        "predicted_fin_root_temperature_c": root_c,
        "predicted_outlet_air_temperature_c": outlet_c,
        "solid_thermal_conductivity_w_mk_assumption": solid_k,
        "hot_material_coupon_card_qualified": False,
        "correlation_physically_validated_on_head": False,
    }


def design_sweep(contract: dict) -> list[dict]:
    bc = contract["boundary_conditions"]
    design = contract["f38_fin_pack"]
    gap = float(design["clear_gap_mm"]) * 1e-3
    span = float(design["mean_span_mm"]) * 1e-3
    length = float(design["mean_flow_length_mm"]) * 1e-3
    open_area = float(design["open_passage_area_m2"])
    hydraulic_diameter = 2.0 * gap * span / (gap + span)
    rho = float(bc["air_density_kg_m3"])
    mu = float(bc["air_dynamic_viscosity_pa_s"])
    conductivity = float(bc["air_thermal_conductivity_w_mk"])
    prandtl = float(bc["air_prandtl"])
    fin_height = float(design["fin_height_mm"]) * 1e-3
    fin_thickness = float(design["fin_thickness_mm"]) * 1e-3
    mass_flow = float(bc["nominal_head_air_mass_flow_kg_s"])
    results = []
    for variant in contract["cooling_variants"]:
        velocity = mass_flow * float(variant["air_capture_fraction"]) / (rho * open_area)
        reynolds = rho * velocity * hydraulic_diameter / mu
        friction = (0.79 * math.log(reynolds) - 1.64) ** -2
        nusselt = (
            (friction / 8.0) * (reynolds - 1000.0) * prandtl
            / (1.0 + 12.7 * math.sqrt(friction / 8.0) * (prandtl ** (2.0 / 3.0) - 1.0))
        )
        h = nusselt * conductivity / hydraulic_diameter
        fin_m = math.sqrt(2.0 * h / (135.0 * fin_thickness))
        efficiency = math.tanh(fin_m * fin_height) / (fin_m * fin_height)
        effective_h = h * efficiency
        dynamic_pressure = 0.5 * rho * velocity**2
        straight_loss = friction * length / hydraulic_diameter * dynamic_pressure
        total_pressure = straight_loss + float(variant["minor_loss_k"]) * dynamic_pressure
        projection = thermal_projection(contract, effective_h)
        results.append(
            {
                **variant,
                "velocity_m_s": velocity,
                "reynolds": reynolds,
                "effective_h_w_m2k": effective_h,
                "straight_pressure_drop_pa": straight_loss,
                "total_pressure_drop_pa": total_pressure,
                "blower_pressure_screen_passed": total_pressure <= float(bc["maximum_pressure_drop_pa"]),
                "projected_bridge_temperature_c": projection["bridge_temperature_c"],
                "temperature_screen_passed": projection["passes_260c_screen"],
                "global_temperature_status": projection["global_temperature_status"],
            }
        )
    return results


def conductivity_at_c(contract: dict, temperature_c: float) -> float:
    points = contract["provisional_hot_material_card_cp1"]["conductivity_w_mk_by_temperature_c"]
    if temperature_c <= points[0][0]:
        return float(points[0][1])
    if temperature_c >= points[-1][0]:
        return float(points[-1][1])
    for (t0, k0), (t1, k1) in zip(points, points[1:]):
        if t0 <= temperature_c <= t1:
            fraction = (temperature_c - t0) / (t1 - t0)
            return float(k0) + fraction * (float(k1) - float(k0))
    raise AssertionError("intervalle de conductivité introuvable")


def conductivity_integral(contract: dict, low_c: float, high_c: float, steps: int = 800) -> float:
    if high_c <= low_c:
        return 0.0
    width = (high_c - low_c) / steps
    total = 0.0
    for index in range(steps + 1):
        temperature = low_c + index * width
        weight = 0.5 if index in (0, steps) else 1.0
        total += weight * conductivity_at_c(contract, temperature)
    return total * width


def solve_bridge_temperature(contract: dict, root_c: float, heat_w: float) -> float:
    network = contract["bridge_network"]
    length = float(network["characteristic_conduction_length_mm"]) * 1e-3
    area = float(network["effective_bridge_cross_section_mm2"]) * 1e-6
    required_integral = heat_w * length / area
    low = root_c
    high = root_c + 800.0
    for _ in range(100):
        middle = 0.5 * (low + high)
        if conductivity_integral(contract, root_c, middle) < required_integral:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def thermal_projection(contract: dict, h: float) -> dict:
    bc = contract["boundary_conditions"]
    design = contract["f38_fin_pack"]
    heat = float(bc["chamber_heat_load_w_per_head"])
    area_raw = design["whole_head_wetted_surface_area_m2"]
    area_status = design["whole_head_wetted_surface_area_status"]
    area_is_brep = area_status == "measured_from_accepted_F38_BRep"
    area = float(area_raw) if area_raw is not None else float(design["provisional_flat_fin_face_area_m2_not_BRep"])
    inlet_c = float(bc["air_inlet_temperature_k"]) - 273.15
    convection_r = 1.0 / (h * area)
    root_c = inlet_c + heat * convection_r
    bridge_c = solve_bridge_temperature(contract, root_c, heat)
    network = contract["bridge_network"]
    equivalent_conduction_r = (bridge_c - root_c) / heat
    outlet_c = inlet_c + heat / (
        float(bc["nominal_head_air_mass_flow_kg_s"]) * float(bc["air_specific_heat_j_kgk"])
    )
    return {
        "model": "two_resistance_steady_screen_not_3D_CHT",
        "heat_load_w": heat,
        "wetted_area_m2": area,
        "wetted_area_measured_from_F38_BRep": area_is_brep,
        "global_temperature_status": "computed_from_F38_BRep_surface" if area_is_brep else area_status,
        "hot_conductivity_card": contract["provisional_hot_material_card_cp1"],
        "bridge_network": network,
        "equivalent_conduction_resistance_k_w": equivalent_conduction_r,
        "convection_resistance_k_w": convection_r,
        "fin_root_temperature_c": root_c,
        "bridge_temperature_c": bridge_c,
        "outlet_air_temperature_c": outlet_c,
        "passes_260c_screen": bridge_c <= float(bc["maximum_burst_bridge_temperature_c"]),
        "within_cp1_interpolation_range": bridge_c <= float(contract["provisional_hot_material_card_cp1"]["maximum_interpolation_temperature_c"]),
    }


def render(report: dict, output: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import FancyArrowPatch, Rectangle

    design = report["design"]
    cases = report["openfoam"]["cases"]
    method_b = report["analytical_method"]
    fig = plt.figure(figsize=(16, 9), facecolor="#eef2f4")
    grid = fig.add_gridspec(2, 2, hspace=0.25, wspace=0.18)
    ax_geom = fig.add_subplot(grid[:, 0])
    ax_geom.set_facecolor("#0b1b24")
    ax_geom.add_patch(Rectangle((0, 0), 1, 1, color="#0b1b24", zorder=-100))
    fin_count = 12
    pitch = 1.0 / (fin_count + 1)
    for i in range(fin_count):
        y = 0.10 + i * pitch * 0.78
        ax_geom.add_patch(Rectangle((0.23, y), 0.57, 0.020, color="#d49a34", ec="#ffd06b", lw=0.8))
    ax_geom.add_patch(Rectangle((0.17, 0.06), 0.70, 0.86, fill=False, ec="#70c7e8", lw=3))
    ax_geom.plot([0.21, 0.34, 0.48], [0.87, 0.74, 0.54], color="#70c7e8", lw=5)
    ax_geom.plot([0.83, 0.70, 0.56], [0.87, 0.74, 0.54], color="#70c7e8", lw=5)
    centreline = cases[-1].get("centreline_temperature_k", [])
    outlet_fraction = 0.0
    if centreline:
        outlet_fraction = min(1.0, max(0.0, (centreline[-1][1] - 308.15) / (533.15 - 308.15)))
    arrow_color = plt.cm.coolwarm(outlet_fraction)
    for y in np.linspace(0.14, 0.82, 8):
        ax_geom.add_patch(FancyArrowPatch((0.03, y), (0.95, y), arrowstyle="-|>", mutation_scale=13, color=arrow_color, lw=1.8, alpha=0.75))
    ax_geom.text(0.04, 0.96, "Coupe du canal F38 — schéma, pas CHT", color="white", fontsize=16, weight="bold", va="top")
    ax_geom.text(0.04, 0.015, "12 niveaux d'ailettes · 22 passages équivalents · carénage 12 mm · déflecteurs", color="#d9edf7", fontsize=11)
    ax_geom.set_xlim(0, 1)
    ax_geom.set_ylim(0, 1)
    ax_geom.axis("off")

    ax_h = fig.add_subplot(grid[0, 1])
    labels = [item["case_id"] for item in cases] + ["Gnielinski + ηailette"]
    values = [item["effective_h_w_m2k"] for item in cases] + [method_b["effective_h_w_m2k"]]
    bars = ax_h.bar(labels, values, color=["#6baed6", "#2171b5", "#e89c31"])
    ax_h.set_ylabel("h effectif [W/m²K]")
    ax_h.set_title("Deux méthodes indépendantes")
    ax_h.tick_params(axis="x", rotation=12)
    for bar, value in zip(bars, values):
        ax_h.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.0f}", ha="center", va="bottom", fontsize=9)

    ax_t = fig.add_subplot(grid[1, 1])
    projection = report["thermal_projection"]
    names = ["OpenFOAM fin", "Corrélation"]
    temperatures = [projection["from_openfoam"]["bridge_temperature_c"], projection["from_analytical"]["bridge_temperature_c"]]
    colors = ["#c53f3f" if value > 260 else "#2c9c69" for value in temperatures]
    ax_t.bar(names, temperatures, color=colors)
    ax_t.axhline(260, color="#111", ls="--", lw=1.5, label="écran burst 260 °C")
    ax_t.set_ylim(0, max(300, max(temperatures) * 1.18))
    ax_t.set_ylabel("Température pont projetée [°C]")
    ax_t.set_title("Projection thermique F38 — pas une CHT")
    ax_t.legend(loc="upper right")
    for index, value in enumerate(temperatures):
        ax_t.text(index, value, f"{value:.1f} °C", ha="center", va="bottom", weight="bold")
    fig.suptitle("Porsche 917 — recalcul du refroidissement F38", fontsize=22, weight="bold")
    fig.text(0.5, 0.015, "Échelle du scan, carte matière à chaud et corrélation banc non acquises — impression/démarrage interdits", ha="center", color="#a32121", weight="bold")
    fig.savefig(output, dpi=170, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--summarize", action="store_true")
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    if args.prepare:
        cases_root = args.output / "openfoam-cases"
        cases_root.mkdir(parents=True, exist_ok=True)
        for case_id, cells in contract["openfoam_reference_case"]["grids"].items():
            prepare_case(
                cases_root / case_id,
                contract,
                cells,
                int(contract["openfoam_reference_case"]["end_time_steps"][case_id]),
            )
        print(json.dumps({"status": "prepared", "output": str(args.output)}))
        return 0
    if not args.summarize:
        raise SystemExit("utiliser --prepare ou --summarize")
    cases = [
        parse_case(args.output / "openfoam-cases" / name, contract)
        for name in contract["openfoam_reference_case"]["grids"]
    ]
    analytical_result = analytical(contract)
    fine = cases[-1]
    h_grid_change = abs(cases[-1]["effective_h_w_m2k"] - cases[-2]["effective_h_w_m2k"]) / cases[-1]["effective_h_w_m2k"]
    h_cross_difference = abs(fine["effective_h_w_m2k"] - analytical_result["effective_h_w_m2k"]) / analytical_result["effective_h_w_m2k"]
    pressure_cross_difference = abs(fine["pressure_drop_pa"] - analytical_result["pressure_drop_straight_channel_pa"]) / max(
        analytical_result["pressure_drop_straight_channel_pa"], 1e-12
    )
    report = {
        "schema_version": "1.0",
        "id": "917-head-f38-cooling-cross-check",
        "classification": "OpenFOAM_RANS_canonical_fin_passage_plus_independent_correlation_not_full_head_CHT_not_physical_validation",
        "inputs": {
            "contract": {"path": str(args.contract), "sha256": sha256(args.contract)},
            "f36_report": {
                "path": contract["source_evidence"]["f36_cfd_thermal"],
                "sha256": sha256(Path(contract["source_evidence"]["f36_cfd_thermal"])),
            },
            "f37_head_report": {
                "path": contract["source_evidence"]["f37_head_mesh"],
                "sha256": sha256(Path(contract["source_evidence"]["f37_head_mesh"])),
            },
        },
        "boundary_conditions": contract["boundary_conditions"],
        "design": contract["f38_fin_pack"],
        "openfoam": {
            "solver": "OpenFOAM_14_foamRun_fluid_hePsiThermo_kOmegaSST",
            "runtime": contract["openfoam_reference_case"]["runtime"],
            "geometry": contract["openfoam_reference_case"]["geometry"],
            "cases": cases,
            "fine_grid_h_change_relative": h_grid_change,
            "two_grid_h_agreement_below_5_percent": h_grid_change <= 0.05,
            "fine_energy_balance_below_5_percent": fine["energy_balance_relative"] <= 0.05,
            "fine_mass_balance_below_1_percent": fine["mass_balance_relative"] <= 0.01,
            "full_head_CHT": False,
        },
        "analytical_method": analytical_result,
        "cooling_variant_sweep": design_sweep(contract),
        "cross_method": {
            "h_relative_difference": h_cross_difference,
            "pressure_drop_relative_difference": pressure_cross_difference,
            "h_agreement_below_20_percent": h_cross_difference <= 0.20,
            "pressure_agreement_below_20_percent": pressure_cross_difference <= 0.20,
            "agreement_is_physical_validation": False,
        },
        "thermal_projection": {
            "from_openfoam": thermal_projection(contract, fine["effective_h_w_m2k"]),
            "from_analytical": thermal_projection(contract, analytical_result["effective_h_w_m2k"]),
        },
        "decision": {
            "cooling_layout_selected_for_next_full_head_CHT": True,
            "selection": "12_fin_levels_22_equivalent_passages_2mm_4p5mm_gap_12mm_shroud_with_splitter_and_exhaust_turning_vanes",
            "selection_basis": "fixed F34 nominal flow; best defensible geometry screen, not a temperature target fit",
            "full_head_cooling_closed": False,
            "reason": "le canal converge en h et bilan, mais deltaP diverge de 61,7% entre méthodes et Tpont=375,8-381,2C dépasse 260C et la plage CP1 de 300C; aucune CHT culasse complète",
            "canonical_channel_numerical_closure": (
                h_grid_change <= 0.05
                and fine["energy_balance_relative"] <= 0.05
                and fine["mass_balance_relative"] <= 0.01
                and h_cross_difference <= 0.20
                and pressure_cross_difference <= 0.20
            ),
            "temperature_screen_passed": (
                thermal_projection(contract, fine["effective_h_w_m2k"])["passes_260c_screen"]
                and thermal_projection(contract, analytical_result["effective_h_w_m2k"])["passes_260c_screen"]
            ),
            "temperature_within_CP1_interpolation_range": (
                thermal_projection(contract, fine["effective_h_w_m2k"])["within_cp1_interpolation_range"]
                and thermal_projection(contract, analytical_result["effective_h_w_m2k"])["within_cp1_interpolation_range"]
            ),
            "accepted_F38_BRep_linked": False,
            "whole_head_CHT_complete": False,
            "full_head_cooling_close_reason": "canonical passage omits bypass, baffle losses, conjugate conduction and measured fan map",
            "hot_material_coupon_card_qualified": False,
            "absolute_scale_confirmed": False,
            "physical_correlation_complete": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
    }
    report_path = args.output / "f38-cooling-cross-check.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    image_path = args.output / "917-head-f38-cooling-section.png"
    render(report, image_path)
    print(json.dumps({"status": "summarized", "report": str(report_path), "image": str(image_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
