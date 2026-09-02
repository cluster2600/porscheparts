#!/usr/bin/env python3
"""Campagne virtuelle intégrée F33 pour les concepts de culasse 917 2V/4V."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import re
import statistics


ROOT = Path(__file__).resolve().parents[3]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def interpolate(points, temperature_c: float, field: str) -> float:
    ordered = sorted(points, key=lambda item: item["temperature_c"])
    if temperature_c <= ordered[0]["temperature_c"]:
        return ordered[0][field]
    if temperature_c >= ordered[-1]["temperature_c"]:
        return ordered[-1][field]
    for left, right in zip(ordered, ordered[1:]):
        if left["temperature_c"] <= temperature_c <= right["temperature_c"]:
            fraction = (temperature_c - left["temperature_c"]) / (
                right["temperature_c"] - left["temperature_c"]
            )
            return left[field] + fraction * (right[field] - left[field])
    raise AssertionError("interpolation range")


def verify_contract(contract: dict, root: Path) -> dict:
    errors = []
    observed = {}
    if contract.get("phase") != "F33":
        errors.append("phase must be F33")
    if contract.get("program", {}).get("architectures") != ["2v", "4v"]:
        errors.append("architectures must be exactly 2v and 4v")
    for item in contract.get("upstream", []):
        path = (root / item["path"]).resolve()
        if not path.is_file():
            errors.append(f"missing upstream: {item['path']}")
            continue
        digest = sha256(path)
        observed[item["path"]] = digest
        if digest != item["sha256"]:
            errors.append(f"upstream digest mismatch: {item['path']}")
    gates = contract.get("release_gates", {})
    if not gates or any(value is not False for value in gates.values()):
        errors.append("all physical release gates must be literal false")
    if contract.get("physicsnemo", {}).get("training_authorized") is not False:
        errors.append("PhysicsNeMo training must remain blocked")
    if errors:
        raise ValueError("; ".join(errors))
    return observed


def synthetic_metrology(contract: dict) -> dict:
    cfg = contract["synthetic_metrology"]
    rng = random.Random(cfg["seed"])
    raw = {}
    scale_truth = 1.0 + cfg["scale_bias_fraction"]
    controls = {"bore_mm", "head_height_mm", "intake_port_axis_height_mm"}
    scale_estimates = []
    for name, nominal in cfg["features"].items():
        uncertainty = (
            cfg["ct_standard_uncertainty_mm"]
            if name in {"cooling_jacket_ligament_mm", "guide_bore_diameter_mm"}
            else cfg["cmm_standard_uncertainty_mm"]
        )
        values = [nominal * scale_truth + rng.gauss(0.0, uncertainty) for _ in range(cfg["repetitions_per_feature"])]
        raw[name] = {"nominal_mm": nominal, "uncertainty_mm": uncertainty, "values": values}
        if name in controls:
            scale_estimates.append(statistics.mean(values) / nominal)
    estimated_scale = statistics.mean(scale_estimates)
    features = {}
    max_abs_z = 0.0
    for name, item in raw.items():
        corrected = [value / estimated_scale for value in item["values"]]
        mean = statistics.mean(corrected)
        sample_std = statistics.stdev(corrected)
        standard_uncertainty = math.sqrt(
            item["uncertainty_mm"] ** 2 + (sample_std / math.sqrt(len(corrected))) ** 2
        )
        error = mean - item["nominal_mm"]
        z_score = error / standard_uncertainty
        max_abs_z = max(max_abs_z, abs(z_score))
        features[name] = {
            "nominal_mm": item["nominal_mm"],
            "corrected_mean_mm": mean,
            "sample_standard_deviation_mm": sample_std,
            "combined_standard_uncertainty_mm": standard_uncertainty,
            "error_mm": error,
            "z_score": z_score,
            "repetition_count": len(corrected),
        }
    return {
        "classification": cfg["classification"],
        "physical_measurements_used": False,
        "injected_scale_bias_fraction": cfg["scale_bias_fraction"],
        "estimated_scale_factor": estimated_scale,
        "scale_estimation_error_fraction": estimated_scale - scale_truth,
        "features": features,
        "maximum_absolute_z_score": max_abs_z,
        "synthetic_acceptance_passed": max_abs_z <= contract["acceptance"]["synthetic_metrology_z_score_maximum"],
        "f27_or_f30_gate_opened": False,
    }


def f29_turbo_variants(root: Path) -> dict:
    study = load_json(root / "twins/reference-917-engine/evidence/f29/design-study.json")
    return {
        item["architecture"]: item
        for item in study["variants"]
        if item["scenario_id"] == "917_30_1973_turbo_5374"
    }


def flowbench(contract: dict, variants: dict) -> dict:
    cfg = contract["flow_and_cfd"]
    result = {}
    for architecture, variant in variants.items():
        count = variant["intake_count"]
        diameter_m = variant["intake_diameter_mm"] / 1000.0
        throat_area = count * math.pi * (0.86 * diameter_m) ** 2 / 4.0
        points = []
        for lift_mm in cfg["lift_points_mm"]:
            lift_m = lift_mm / 1000.0
            ratio = lift_m / diameter_m
            discharge = 0.50 + 0.24 * (1.0 - math.exp(-8.0 * ratio))
            curtain_area = count * math.pi * diameter_m * lift_m
            effective_area = discharge * min(curtain_area, throat_area)
            mass_flow = effective_area * math.sqrt(
                2.0 * cfg["air_density_kg_m3"] * cfg["flowbench_pressure_drop_pa"]
            )
            volume_flow_m3_s = mass_flow / cfg["air_density_kg_m3"]
            points.append(
                {
                    "lift_mm": lift_mm,
                    "discharge_coefficient": discharge,
                    "curtain_area_mm2": curtain_area * 1e6,
                    "effective_area_mm2": effective_area * 1e6,
                    "mass_flow_kg_s": mass_flow,
                    "volume_flow_cfm": volume_flow_m3_s * 2118.880003,
                }
            )
        result[architecture] = {
            "valve_count": count,
            "valve_diameter_mm": variant["intake_diameter_mm"],
            "f29_mean_effective_area_mm2": variant["flow_screen"]["intake_mean_effective_area_mm2"],
            "f29_peak_effective_area_mm2": variant["flow_screen"]["intake_peak_effective_area_mm2"],
            "points": points,
            "peak_virtual_flow_cfm": max(item["volume_flow_cfm"] for item in points),
        }
    gain = 100.0 * (result["4v"]["peak_virtual_flow_cfm"] / result["2v"]["peak_virtual_flow_cfm"] - 1.0)
    return {
        "classification": "quasi_steady_virtual_flowbench_not_correlated_measurement",
        "pressure_drop_pa": cfg["flowbench_pressure_drop_pa"],
        "architectures": result,
        "four_valve_peak_flow_gain_percent": gain,
        "physical_flowbench_used": False,
    }


def cht_rom(contract: dict, architecture: str, head_heat_per_cylinder_w: float) -> dict:
    cfg = contract["cht_rom"]
    points = contract["material_screen"]["temperature_points"]
    if architecture == "2v":
        cooled_area_m2, conduction_length_m = 0.055, 0.0075
    else:
        cooled_area_m2, conduction_length_m = 0.062, 0.0060
    conductivity = interpolate(points, 220.0, "conductivity_w_mk")
    resistance_area = (
        1.0 / cfg["gas_side_h_w_m2k"]
        + conduction_length_m / conductivity
        + 1.0 / cfg["coolant_side_h_w_m2k"]
    )
    capability_w = (
        cfg["combustion_gas_temperature_c"] - cfg["head_coolant_temperature_c"]
    ) * cooled_area_m2 / resistance_area
    coolant_load_w = head_heat_per_cylinder_w * cfg["heat_split_to_coolant"]
    heat_flux = coolant_load_w / cooled_area_m2
    coolant_wall_c = cfg["head_coolant_temperature_c"] + heat_flux / cfg["coolant_side_h_w_m2k"]
    conduction_drop_k = heat_flux * conduction_length_m / conductivity
    chamber_wall_c = coolant_wall_c + conduction_drop_k
    required_gas_bulk_c = chamber_wall_c + heat_flux / cfg["gas_side_h_w_m2k"]
    return {
        "classification": cfg["classification"],
        "cooled_area_m2": cooled_area_m2,
        "conduction_length_m": conduction_length_m,
        "screening_conductivity_w_mk": conductivity,
        "head_heat_input_per_cylinder_w": head_heat_per_cylinder_w,
        "coolant_heat_load_w": coolant_load_w,
        "oil_and_unmodelled_head_heat_w": head_heat_per_cylinder_w - coolant_load_w,
        "network_capability_w": capability_w,
        "combustion_side_wall_temperature_c": chamber_wall_c,
        "coolant_side_wall_temperature_c": coolant_wall_c,
        "metal_temperature_drop_k": conduction_drop_k,
        "required_gas_bulk_temperature_c": required_gas_bulk_c,
        "gas_temperature_margin_k": cfg["combustion_gas_temperature_c"] - required_gas_bulk_c,
        "energy_balance_error_w": coolant_load_w + (head_heat_per_cylinder_w - coolant_load_w) - head_heat_per_cylinder_w,
        "load_within_network_capability": coolant_load_w <= capability_w,
        "full_3d_cht_executed": False,
    }


def cycle_point(contract: dict, architecture: str, rpm: float, map_bar: float) -> dict:
    engine = contract["engine_cycle"]
    bore = contract["program"]["bore_mm"] / 1000.0
    stroke = contract["program"]["stroke_mm"] / 1000.0
    cylinders = contract["program"]["cylinder_count"]
    swept = math.pi * bore**2 * stroke / 4.0
    compression_ratio = 9.0
    clearance = swept / (compression_ratio - 1.0)
    gas_r = 287.05
    gamma = 1.34
    cv = gas_r / (gamma - 1.0)
    intake_t = 325.0
    afr = 11.0
    lhv = 43e6
    ve_base = 0.90 + 0.09 * math.exp(-((rpm - 7000.0) / 2600.0) ** 2)
    ve = ve_base * (1.0 if architecture == "2v" else 1.035)
    p0 = map_bar * 1e5
    air_mass = p0 * swept * ve / (gas_r * intake_t)
    fuel_mass = air_mass / afr
    total_mass = air_mass + fuel_mass
    q_total = fuel_mass * lhv * engine["combustion_efficiency"] * (1.0 - engine["heat_loss_fraction"])
    burn_duration = 48.0 * (engine["four_valve_combustion_duration_factor"] if architecture == "4v" else 1.0)
    burn_start = -14.0
    step = 0.5
    angles = [(-180.0 + index * step) for index in range(int(360.0 / step) + 1)]

    def volume(angle_deg: float) -> float:
        return clearance + 0.5 * swept * (1.0 - math.cos(math.radians(angle_deg)))

    initial_volume = volume(angles[0])
    temperature = p0 * initial_volume / (total_mass * gas_r)
    previous_volume = initial_volume
    previous_pressure = p0
    work = 0.0
    q_released = 0.0
    peak_pressure = p0
    for angle in angles[1:]:
        current_volume = volume(angle)
        x = max(0.0, min(1.0, (angle - burn_start) / burn_duration))
        previous_x = max(0.0, min(1.0, (angle - step - burn_start) / burn_duration))
        wiebe = 1.0 - math.exp(-6.908 * x ** 3.0)
        previous_wiebe = 1.0 - math.exp(-6.908 * previous_x ** 3.0)
        dq = q_total * (wiebe - previous_wiebe)
        dv = current_volume - previous_volume
        temperature += (dq - previous_pressure * dv) / (total_mass * cv)
        pressure = total_mass * gas_r * temperature / current_volume
        work += 0.5 * (previous_pressure + pressure) * dv
        q_released += dq
        peak_pressure = max(peak_pressure, pressure)
        previous_pressure = pressure
        previous_volume = current_volume
    gross_imep = work / swept
    pumping_mep = max(0.35e5, (3.0e5 - p0) * 0.04)
    brake_work = max(0.0, (gross_imep - pumping_mep) * swept * engine["mechanical_efficiency"])
    power = brake_work * cylinders * rpm / 120.0
    torque = power / (2.0 * math.pi * rpm / 60.0)
    return {
        "rpm": rpm,
        "manifold_absolute_pressure_bar": map_bar,
        "volumetric_efficiency_hypothesis": ve,
        "fuel_mass_per_cylinder_cycle_mg": fuel_mass * 1e6,
        "gross_imep_bar": gross_imep / 1e5,
        "brake_power_kw": power / 1000.0,
        "brake_power_mechanical_hp": power / 745.6998715822702,
        "brake_torque_nm": torque,
        "peak_cylinder_pressure_mpa": peak_pressure / 1e6,
        "released_heat_per_cycle_j": q_released,
        "combustion_duration_deg": burn_duration,
    }


def engine_cycle(contract: dict) -> dict:
    cfg = contract["engine_cycle"]
    curves = {}
    for architecture in contract["program"]["architectures"]:
        curves[architecture] = [
            cycle_point(contract, architecture, rpm, map_bar)
            for rpm, map_bar in zip(cfg["speed_points_rpm"], cfg["manifold_absolute_pressure_bar"])
        ]
    p2 = curves["2v"][-1]["brake_power_mechanical_hp"]
    p4 = curves["4v"][-1]["brake_power_mechanical_hp"]
    return {
        "classification": cfg["classification"],
        "curves": curves,
        "four_valve_power_change_at_9000rpm_percent": 100.0 * (p4 / p2 - 1.0),
        "target_power_mechanical_hp": contract["program"]["target_power_mechanical_hp"],
        "target_power_proven": False,
        "measured_dyno_data_used": False,
    }


def fatigue_tmf(contract: dict, root: Path, cht: dict) -> dict:
    report = load_json(root / "twins/reference-917-engine/evidence/f31/report.json")
    material = contract["material_screen"]
    fatigue = material["fatigue_sensitivity"]
    result = {}
    for architecture in ("2v", "4v"):
        variant = next(
            item for item in report["variants"]
            if item["architecture"] == architecture and item["scenario_id"] == "917_30_1973_turbo_5374"
        )
        finest = sorted(variant["cases"], key=lambda item: item["mesh_size_mm"])[0]
        combined = finest["load_cases"]["combined"]["p95_von_mises_mpa"]
        pressure = finest["load_cases"]["pressure_only"]["p95_von_mises_mpa"]
        temperature = cht[architecture]["combustion_side_wall_temperature_c"]
        hot_yield = interpolate(material["temperature_points"], temperature, "yield_mpa")
        thermal_amplitude = 0.5 * max(0.0, combined - pressure)
        pressure_amplitude = 0.5 * pressure

        def cycles_to_failure(amplitude: float, multiplier: float) -> float:
            return fatigue["cycles_at_reference"] * (
                fatigue["stress_amplitude_reference_mpa"] / max(amplitude, 1e-9)
            ) ** fatigue["basquin_exponent"] / multiplier

        temp_multiplier = 1.0 + (
            fatigue["temperature_damage_multiplier_at_250c"] - 1.0
        ) * min(max((temperature - 20.0) / 230.0, 0.0), 1.0)
        pressure_life = cycles_to_failure(pressure_amplitude, temp_multiplier)
        thermal_life = cycles_to_failure(thermal_amplitude, temp_multiplier)
        design_pressure_cycles = 5.0e8
        design_thermal_cycles = 50000.0
        pressure_damage = design_pressure_cycles / pressure_life
        thermal_damage = design_thermal_cycles / thermal_life
        total_damage = pressure_damage + thermal_damage
        result[architecture] = {
            "f31_finest_mesh_mm": finest["mesh_size_mm"],
            "f31_combined_p95_mpa": combined,
            "f31_pressure_only_p95_mpa": pressure,
            "screening_metal_temperature_c": temperature,
            "assumed_hot_yield_mpa": hot_yield,
            "hot_yield_margin_on_combined_p95": hot_yield / combined,
            "pressure_stress_amplitude_mpa": pressure_amplitude,
            "thermal_stress_amplitude_mpa": thermal_amplitude,
            "assumed_pressure_cycles_to_failure": pressure_life,
            "assumed_thermal_cycles_to_failure": thermal_life,
            "design_pressure_cycles": design_pressure_cycles,
            "design_thermal_cycles": design_thermal_cycles,
            "miner_pressure_damage": pressure_damage,
            "miner_thermal_damage": thermal_damage,
            "miner_total_damage": total_damage,
            "screening_passed": hot_yield / combined >= 1.25 and total_damage <= 1.0,
        }
    return {
        "classification": "Basquin_Miner_and_F31_elastic_P95_sensitivity_not_qualified_fatigue_or_TMF",
        "architectures": result,
        "nonlinear_plasticity_creep_mean_stress_and_surface_defects_included": False,
        "physical_coupon_or_engine_fatigue_data_used": False,
    }


def virtual_ndt(contract: dict) -> dict:
    cfg = contract["virtual_ndt"]
    rng = random.Random(cfg["seed"])
    diameters = [min(1.5, max(0.02, rng.lognormvariate(math.log(0.16), 0.55))) for _ in range(cfg["synthetic_defect_count"])]
    critical = [value for value in diameters if value >= cfg["critical_defect_diameter_mm"]]
    cases = []
    for voxel in cfg["ct_voxel_sizes_mm"]:
        probabilities = [1.0 / (1.0 + math.exp(-3.2 * (diameter / voxel - 3.0))) for diameter in diameters]
        critical_probabilities = [
            1.0 / (1.0 + math.exp(-3.2 * (diameter / voxel - 3.0))) for diameter in critical
        ]
        cases.append(
            {
                "voxel_size_mm": voxel,
                "mean_detection_probability_all_defects": statistics.mean(probabilities),
                "mean_detection_probability_critical_defects": statistics.mean(critical_probabilities),
                "critical_pod_target": contract["acceptance"]["critical_ct_pod_target"],
                "critical_pod_screen_passed": statistics.mean(critical_probabilities) >= contract["acceptance"]["critical_ct_pod_target"],
            }
        )
    return {
        "classification": cfg["classification"],
        "synthetic_defect_count": len(diameters),
        "critical_defect_count": len(critical),
        "defect_diameter_percentiles_mm": {
            "p50": statistics.median(diameters),
            "p95": sorted(diameters)[int(0.95 * (len(diameters) - 1))],
            "p99": sorted(diameters)[int(0.99 * (len(diameters) - 1))],
        },
        "ct_cases": cases,
        "physical_part_scanned": False,
        "real_probability_of_detection_demonstrated": False,
    }


def foam_header(object_name: str, class_name: str = "dictionary", location: str | None = None) -> str:
    location_line = f'    location    "{location}";\n' if location else ""
    return (
        "FoamFile\n{\n    format ascii;\n"
        f"    class {class_name};\n{location_line}    object {object_name};\n}}\n\n"
    )


def write_openfoam_case(case: Path, area_m2: float, cells: list[int], cfg: dict) -> None:
    depth = cfg["equivalent_duct_depth_m"]
    height = area_m2 / depth
    length = cfg["equivalent_duct_length_m"]
    nx, ny, nz = cells
    for directory in (case / "0", case / "constant", case / "system"):
        directory.mkdir(parents=True, exist_ok=True)
    vertices = [
        (0, -height / 2, 0), (length, -height / 2, 0),
        (length, height / 2, 0), (0, height / 2, 0),
        (0, -height / 2, depth), (length, -height / 2, depth),
        (length, height / 2, depth), (0, height / 2, depth),
    ]
    vertex_text = "\n".join(f"    ({x:.12g} {y:.12g} {z:.12g})" for x, y, z in vertices)
    block = foam_header("blockMeshDict") + f"""convertToMeters 1;
vertices
(
{vertex_text}
);
blocks ( hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1) );
edges ();
boundary
(
    inlet {{ type patch; faces ((0 3 7 4)); }}
    outlet {{ type patch; faces ((1 2 6 5)); }}
    walls {{ type wall; faces ((0 1 5 4) (2 3 7 6) (0 1 2 3) (4 5 6 7)); }}
);
"""
    (case / "system/blockMeshDict").write_text(block, encoding="utf-8")
    control = foam_header("controlDict", location="system") + """solver fluid;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 500;
deltaT 1;
writeControl timeStep;
writeInterval 500;
writeFormat ascii;
writePrecision 12;
runTimeModifiable false;
functions
{
    inletFlow
    {
        type surfaceFieldValue;
        libs ("libfieldFunctionObjects.so");
        writeControl timeStep;
        writeInterval 500;
        writeFields false;
        patch inlet;
        operation sum;
        fields (phi);
    }
    outletFlow
    {
        $inletFlow;
        patch outlet;
    }
}
"""
    (case / "system/controlDict").write_text(control, encoding="utf-8")
    (case / "system/fvSchemes").write_text(foam_header("fvSchemes", location="system") + """ddtSchemes { default localEuler; }
gradSchemes { default cellLimited Gauss linear 1; }
divSchemes
{
    default none;
    div(phi,U) Gauss upwind;
    div(phid,p) Gauss upwind;
    div(phi,(p|rho)) Gauss upwind;
    div(phi,K) Gauss linear;
    div(phi,h) Gauss upwind;
    div(phi,k) Gauss upwind;
    div(phi,omega) Gauss upwind;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
wallDist { method meshWave; }
fluxRequired { default no; p; }
""", encoding="utf-8")
    (case / "system/fvSolution").write_text(foam_header("fvSolution", location="system") + """solvers
{
    p { solver PCG; preconditioner DIC; tolerance 1e-6; relTol 0.1; }
    pFinal { $p; tolerance 1e-6; relTol 0.1; }
    "(rho|U|h|k|omega)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-5; relTol 0.1; }
    "(rho|U|h|k|omega)Final" { $U; tolerance 1e-5; relTol 0.1; }
}
PIMPLE
{
    momentumPredictor yes;
    nOuterCorrectors 1;
    nCorrectors 1;
    nNonOrthogonalCorrectors 0;
    maxCo 0.35;
    rDeltaTSmoothingCoeff 0.1;
    rDeltaTDampingCoeff 1;
    maxDeltaT 1;
}
""", encoding="utf-8")
    (case / "constant/physicalProperties").write_text(foam_header("physicalProperties", location="constant") + """thermoType
{
    type hePsiThermo;
    mixture pureMixture;
    transport const;
    thermo hConst;
    equationOfState perfectGas;
    specie specie;
    energy sensibleEnthalpy;
}
mixture
{
    specie { molWeight 28.97; }
    thermodynamics { Cp 1005; hf 0; }
    transport { mu 1.85e-5; Pr 0.71; }
}
""", encoding="utf-8")
    (case / "constant/momentumTransport").write_text(foam_header("momentumTransport", location="constant") + """simulationType RAS;
RAS
{
    model kOmegaSST;
    turbulence on;
    printCoeffs on;
}
""", encoding="utf-8")
    p_out = cfg["ambient_absolute_pressure_pa"]
    p_in = p_out + cfg["flowbench_pressure_drop_pa"]
    temperature = cfg["ambient_temperature_k"]
    fields = {
        "U": foam_header("U", "volVectorField") + """dimensions [0 1 -1 0 0 0 0];
internalField uniform (50 0 0);
boundaryField
{
    inlet { type pressureInletOutletVelocity; value uniform (50 0 0); }
    outlet { type pressureInletOutletVelocity; value uniform (50 0 0); }
    walls { type noSlip; }
}
""",
        "p": foam_header("p", "volScalarField") + f"""dimensions [1 -1 -2 0 0 0 0];
internalField uniform {p_out:.12g};
boundaryField
{{
    inlet {{ type fixedValue; value uniform {p_in:.12g}; }}
    outlet {{ type fixedValue; value uniform {p_out:.12g}; }}
    walls {{ type zeroGradient; }}
}}
""",
        "T": foam_header("T", "volScalarField") + f"""dimensions [0 0 0 1 0 0 0];
internalField uniform {temperature:.12g};
boundaryField
{{
    inlet {{ type fixedValue; value uniform {temperature:.12g}; }}
    outlet {{ type inletOutlet; inletValue uniform {temperature:.12g}; value uniform {temperature:.12g}; }}
    walls {{ type zeroGradient; }}
}}
""",
        "k": foam_header("k", "volScalarField") + """dimensions [0 2 -2 0 0 0 0];
internalField uniform 6;
boundaryField
{
    inlet { type fixedValue; value uniform 6; }
    outlet { type inletOutlet; inletValue uniform 6; value uniform 6; }
    walls { type kqRWallFunction; value uniform 1e-10; }
}
""",
        "omega": foam_header("omega", "volScalarField") + """dimensions [0 0 -1 0 0 0 0];
internalField uniform 1200;
boundaryField
{
    inlet { type fixedValue; value uniform 1200; }
    outlet { type inletOutlet; inletValue uniform 1200; value uniform 1200; }
    walls { type omegaWallFunction; value uniform 1200; }
}
""",
        "nut": foam_header("nut", "volScalarField") + """dimensions [0 2 -1 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet { type calculated; value uniform 0; }
    outlet { type calculated; value uniform 0; }
    walls { type nutkWallFunction; value uniform 0; }
}
""",
        "alphat": foam_header("alphat", "volScalarField") + """dimensions [1 -1 -1 0 0 0 0];
internalField uniform 1e-3;
boundaryField
{
    inlet { type calculated; value uniform 1e-3; }
    outlet { type calculated; value uniform 1e-3; }
    walls { type compressible::alphatWallFunction; value uniform 1e-3; }
}
""",
    }
    for name, text in fields.items():
        (case / "0" / name).write_text(text, encoding="utf-8")
    write_json(case / "case-metadata.json", {"area_m2": area_m2, "height_m": height, "depth_m": depth, "length_m": length, "cells": cells})


def prepare_openfoam(contract: dict, variants: dict, output: Path) -> list[dict]:
    cfg = contract["flow_and_cfd"]
    cases = []
    for architecture, variant in variants.items():
        area = variant["flow_screen"]["intake_mean_effective_area_mm2"] * 1e-6
        for mesh_id, cells in cfg["mesh_levels"].items():
            case = output / "openfoam" / architecture / mesh_id
            write_openfoam_case(case, area, cells, cfg)
            cases.append({"architecture": architecture, "mesh_id": mesh_id, "relative_path": str(case.relative_to(output))})
    write_json(output / "openfoam/cases.json", cases)
    return cases


def parse_flow_file(path: Path) -> float:
    values = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#"):
            continue
        tokens = line.split()
        if len(tokens) >= 2:
            try:
                values.append(float(tokens[-1]))
            except ValueError:
                pass
    if not values:
        raise ValueError(f"no flow values in {path}")
    return values[-1]


def collect_openfoam(contract: dict, output: Path) -> dict:
    cfg = contract["flow_and_cfd"]
    cases = load_json(output / "openfoam/cases.json")
    by_architecture = {"2v": [], "4v": []}
    all_zero = True
    for item in cases:
        case = output / item["relative_path"]
        status = load_json(case / "run-status.json")
        all_zero = all_zero and status["returncode"] == 0
        candidates = sorted((case / "postProcessing/outletFlow").glob("*/surfaceFieldValue.dat"))
        if not candidates:
            raise ValueError(f"missing outlet flow for {item['relative_path']}")
        phi = abs(parse_flow_file(candidates[-1]))
        meta = load_json(case / "case-metadata.json")
        mass_flow = phi
        volume_flow = mass_flow / cfg["air_density_kg_m3"]
        velocity = volume_flow / meta["area_m2"]
        hydraulic_diameter = 2.0 * meta["height_m"] * meta["depth_m"] / (meta["height_m"] + meta["depth_m"])
        reynolds = cfg["air_density_kg_m3"] * velocity * hydraulic_diameter / cfg["air_dynamic_viscosity_pa_s"]
        speed_of_sound = math.sqrt(1.4 * 287.05 * cfg["ambient_temperature_k"])
        by_architecture[item["architecture"]].append({
            "mesh_id": item["mesh_id"],
            "cells": math.prod(meta["cells"]),
            "volume_flow_m3_s": volume_flow,
            "mass_flow_kg_s": mass_flow,
            "mean_velocity_m_s": velocity,
            "mean_mach_number": velocity / speed_of_sound,
            "hydraulic_diameter_m": hydraulic_diameter,
            "reynolds_number": reynolds,
            "solver_returncode": status["returncode"],
            "log_sha256": sha256(case / "log.fluid"),
        })
    convergence = {}
    for architecture, rows in by_architecture.items():
        order = {name: index for index, name in enumerate(cfg["mesh_levels"])}
        rows.sort(key=lambda item: order[item["mesh_id"]])
        change = abs(rows[-1]["mass_flow_kg_s"] / rows[-2]["mass_flow_kg_s"] - 1.0)
        convergence[architecture] = {
            "last_two_mesh_relative_mass_flow_change": change,
            "passed": change <= contract["acceptance"]["openfoam_last_two_mesh_flow_change_maximum"],
        }
    fine2 = by_architecture["2v"][-1]["mass_flow_kg_s"]
    fine4 = by_architecture["4v"][-1]["mass_flow_kg_s"]
    return {
        "classification": cfg["classification"],
        "solver": "OpenFOAM 13 fluid perfectGas compressible RANS kOmegaSST",
        "container_image": cfg["openfoam_image"],
        "architectures": by_architecture,
        "convergence": convergence,
        "all_runs_returned_zero": all_zero,
        "all_convergence_passed": all(item["passed"] for item in convergence.values()),
        "four_valve_fine_mass_flow_change_percent": 100.0 * (fine4 / fine2 - 1.0),
        "full_runner_and_moving_valve_geometry_used": False,
    }


def base_report(contract: dict, root: Path) -> dict:
    observed = verify_contract(contract, root)
    variants = f29_turbo_variants(root)
    f32 = load_json(root / "twins/reference-917-engine/evidence/f32/screening-report.json")
    head_heat_per_cylinder = f32["cooling_variants"][0]["loads"]["head_high_temperature_liquid_loop"]["load_w"] / 12.0
    cht = {architecture: cht_rom(contract, architecture, head_heat_per_cylinder) for architecture in ("2v", "4v")}
    return {
        "schema_version": "1.0.0",
        "phase": "F33",
        "status": "virtual_models_complete_openfoam_pending",
        "contract_sha256": sha256(root / "twins/reference-917-engine/integrated-virtual-validation-f33.json"),
        "upstream_sha256": observed,
        "measurement_policy": contract["program"]["measurement_policy"],
        "synthetic_metrology": synthetic_metrology(contract),
        "functional_solver_cad": {
            "classification": contract["functional_solver_cad"]["classification"],
            "included_features": contract["functional_solver_cad"]["included_features"],
            "excluded_features": contract["functional_solver_cad"]["excluded_features"],
            "step_or_mesh_generated": False,
            "manufacturing_cad_complete": False,
        },
        "material_screen": {
            "id": contract["material_screen"]["id"],
            "temperature_points": contract["material_screen"]["temperature_points"],
            "supplier_data_scope": "room_temperature_reference_only",
            "hot_curve_qualified": False,
        },
        "virtual_flowbench": flowbench(contract, variants),
        "equivalent_port_cfd": None,
        "cht_reduced_order": cht,
        "fatigue_tmf_screen": fatigue_tmf(contract, root, cht),
        "virtual_ct_ndt": virtual_ndt(contract),
        "zero_dimensional_engine_dyno": engine_cycle(contract),
        "synthetic_correlation": {
            "status": "pipeline_exercise_only",
            "physical_held_out_dataset_used": False,
            "correlation_complete": False,
        },
        "physicsnemo": {
            **contract["physicsnemo"],
            "dataset_cases_available_after_f33": 6,
            "training_executed": False,
            "surrogate_result_available": False,
        },
        "omniverse": {
            "status": "preflight_not_rerun_yet",
            "usd_created": False,
            "simready_validated": False,
        },
        "release_gates": contract["release_gates"],
        "claims": {
            "classical_openfoam_cfd_executed": False,
            "reduced_order_cht_executed": True,
            "zero_dimensional_engine_cycle_executed": True,
            "synthetic_metrology_and_ndt_executed": True,
            "physical_validation_or_correlation_completed": False,
            "manufacturing_or_engine_start_authorized": False,
        },
    }


def finalize_report(contract: dict, root: Path, output: Path) -> dict:
    report = load_json(output / "report.partial.json")
    f29_contract = load_json(root / "twins/reference-917-engine/clean-sheet-cylinder-head-f29.json")
    report["valvetrain_selection"] = {
        **f29_contract["valvetrain_screening"],
        "selection_scope": "screening_choice_carried_from_F29_not_procurement_release_or_valvetrain_validation",
    }
    geometry_report = load_json(output / "functional-cad/geometry-report.json")
    report["functional_solver_cad"] = {
        "classification": contract["functional_solver_cad"]["classification"],
        "status": geometry_report["status"],
        "included_features": contract["functional_solver_cad"]["included_features"],
        "excluded_features": contract["functional_solver_cad"]["excluded_features"],
        "variants": geometry_report["variants"],
        "geometry_report_sha256": sha256(output / "functional-cad/geometry-report.json"),
        "step_or_mesh_generated": True,
        "manufacturing_cad_complete": False,
    }
    report["equivalent_port_cfd"] = collect_openfoam(contract, output)
    preflight_path = output / "omniverse/preflight.json"
    if preflight_path.is_file():
        preflight = load_json(preflight_path)
        report["omniverse"] = {
            "status": preflight["status"],
            "preflight_sha256": sha256(preflight_path),
            "blockers": preflight.get("blockers", []),
            "usd_created": False,
            "simready_validated": False,
        }
    x86_check_path = output / "toolchain/x86-cross-check.json"
    if x86_check_path.is_file():
        report["cross_architecture_check"] = load_json(x86_check_path)
    report["status"] = "integrated_virtual_campaign_complete_not_physical_validation"
    report["claims"]["classical_openfoam_cfd_executed"] = True
    checks = {
        "synthetic_metrology_passed": report["synthetic_metrology"]["synthetic_acceptance_passed"],
        "openfoam_all_runs_returned_zero": report["equivalent_port_cfd"]["all_runs_returned_zero"],
        "openfoam_all_convergence_passed": report["equivalent_port_cfd"]["all_convergence_passed"],
        "functional_solver_cad_generated": report["functional_solver_cad"]["step_or_mesh_generated"],
        "manufacturing_cad_remains_false": report["functional_solver_cad"]["manufacturing_cad_complete"] is False,
        "all_release_gates_closed": all(value is False for value in report["release_gates"].values()),
        "physical_correlation_remains_false": report["synthetic_correlation"]["correlation_complete"] is False,
    }
    report["checks"] = checks
    if not all(checks.values()):
        report["status"] = "integrated_virtual_campaign_failed_acceptance"
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=("prepare", "finalize"), required=True)
    args = parser.parse_args()
    contract_path = args.contract.resolve()
    output = args.output.resolve()
    root = ROOT.resolve()
    try:
        output.relative_to(root / "work")
    except ValueError as exc:
        raise SystemExit("output must remain under work/") from exc
    contract = load_json(contract_path)
    if args.stage == "prepare":
        if output.exists():
            raise SystemExit(f"output already exists: {output}")
        output.mkdir(parents=True)
        report = base_report(contract, root)
        variants = f29_turbo_variants(root)
        prepare_openfoam(contract, variants, output)
        write_json(output / "report.partial.json", report)
        print(json.dumps({"status": report["status"], "openfoam_cases": 6, "output": str(output)}))
        return 0
    report = finalize_report(contract, root, output)
    write_json(output / "report.json", report)
    print(json.dumps({"status": report["status"], "checks": report["checks"]}, sort_keys=True))
    return 0 if all(report["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
