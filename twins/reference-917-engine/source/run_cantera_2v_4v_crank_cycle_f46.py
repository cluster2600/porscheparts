#!/usr/bin/env python3
"""F46: calcul 0D angle-vilebrequin comparable des culasses turbo 2V/4V.

Le solveur utilise Cantera 3.2 pour la thermodynamique, les débits ouverts et,
dans la voie de référence, la cinétique ``nDodecane_IG``. La voie de contrôle
désactive toute cinétique et impose une loi de Wiebe indépendante. Les lois de
soupape, Cd, conditions turbo et paroi restent des hypothèses non corrélées.
Le programme ne crée aucune géométrie de culasse et n'autorise aucune pièce.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import html
import json
import math
from pathlib import Path
import shutil
import sys
from typing import Any, Iterable

try:
    import cantera as ct
except ModuleNotFoundError:
    ct = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "twins/reference-917-engine/cantera-2v-4v-crank-cycle-f46.json"
F45 = ROOT / "twins/reference-917-engine/valvetrain-material-screen-f45.json"
DEFAULT_OUTPUT = ROOT / "twins/reference-917-engine/evidence/f46-cantera-cycle"
RAW_COLUMNS = (
    "crank_angle_deg",
    "volume_m3",
    "pressure_pa_abs",
    "temperature_k",
    "mass_kg",
    "intake_lift_mm",
    "exhaust_lift_mm",
    "intake_effective_area_m2",
    "exhaust_effective_area_m2",
    "intake_net_mass_flow_kg_s",
    "exhaust_net_mass_flow_kg_s",
    "fuel_mass_flow_kg_s",
    "heat_release_rate_w",
    "wall_heat_rate_w",
    "wall_heat_flux_w_m2",
    "apparent_residual_marker_mass_fraction",
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_constant)


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant rejected: {value}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rounded(value: float, digits: int = 9) -> float:
    return round(float(value), digits)


def _finite(value: float) -> bool:
    return math.isfinite(float(value))


def _resolve_cantera_data_file(filename: str) -> Path:
    if ct is None:
        raise RuntimeError("Cantera 3.2.0 is required to resolve the mechanism")
    for directory in ct.get_data_directories():
        candidate = Path(directory) / filename
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"Cantera data file not found: {filename}")


def validate_contract(contract: dict[str, Any], root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    if contract.get("phase") != "F46" or contract.get("schema_version") != "1.0.0":
        errors.append("contract phase/schema mismatch")
    geometry = contract.get("geometry", {})
    if geometry.get("oval_or_ellipse_created") is not False:
        errors.append("oval_or_ellipse_created must remain false")
    if geometry.get("external_head_geometry_used") is not False:
        errors.append("F46 0D must not create external head geometry")
    if geometry.get("external_scan_contour_modified") is not False:
        errors.append("F46 must not modify the scan contour")
    if geometry.get("bore_mm") != 90.0 or geometry.get("stroke_mm") != 70.4:
        errors.append("F46 bore/stroke must remain 90.0 x 70.4 mm")
    if geometry.get("cylinder_count") != 12:
        errors.append("F46 must remain a flat-12 comparison")
    steps = contract.get("numerics", {}).get("crank_angle_steps_deg")
    if steps != [1.0, 0.5, 0.25]:
        errors.append("exact three-level crank-step ladder required")
    cds = contract.get("valve_law", {}).get("flow_coefficients_cd")
    if cds != [0.62, 0.72, 0.82]:
        errors.append("exact Cd bracket required")
    if contract.get("common_operating_point", {}).get("power_target_is_solver_boundary") is not False:
        errors.append("1600 hp target must not drive the forward solution")
    if any(value is not False for value in contract.get("release_gates", {}).values()):
        errors.append("all physical release gates must remain false")
    for item in contract.get("upstream_manifest", []):
        path = root / item.get("path", "")
        if not path.is_file():
            errors.append(f"upstream missing: {item.get('path')}")
        elif sha256(path) != item.get("sha256"):
            errors.append(f"upstream hash mismatch: {item.get('path')}")
    combustion = contract.get("combustion_models", {}).get("cantera_finite_rate", {})
    if combustion.get("cantera_version") != "3.2.0":
        errors.append("Cantera version must be 3.2.0")
    if combustion.get("spark_ignition_represented") is not False:
        errors.append("single-zone F46 may not claim spark ignition")
    if combustion.get("knock_prediction_authorized") is not False:
        errors.append("F46 may not claim knock prediction")
    return errors


def slider_crank_geometry(contract: dict[str, Any]) -> dict[str, float]:
    geometry = contract["geometry"]
    bore = float(geometry["bore_mm"]) * 1e-3
    stroke = float(geometry["stroke_mm"]) * 1e-3
    rod = float(geometry["connecting_rod_length_mm"]) * 1e-3
    crank = stroke / 2.0
    area = math.pi * bore**2 / 4.0
    swept = area * stroke
    clearance = swept / (float(geometry["compression_ratio"]) - 1.0)
    return {
        "bore_m": bore,
        "stroke_m": stroke,
        "rod_m": rod,
        "crank_m": crank,
        "piston_area_m2": area,
        "swept_volume_m3": swept,
        "clearance_volume_m3": clearance,
        "rod_crank_ratio": rod / crank,
    }


def piston_displacement_m(theta_rad: float, geometry: dict[str, float]) -> float:
    r = geometry["crank_m"]
    length = geometry["rod_m"]
    sine = math.sin(theta_rad)
    return r * (1.0 - math.cos(theta_rad)) + length - math.sqrt(
        length**2 - (r * sine) ** 2
    )


def cylinder_volume_m3(crank_angle_deg: float, geometry: dict[str, float]) -> float:
    theta = math.radians(crank_angle_deg % 360.0)
    return geometry["clearance_volume_m3"] + geometry["piston_area_m2"] * piston_displacement_m(theta, geometry)


def dvolume_dt(time_s: float, rpm: float, geometry: dict[str, float]) -> float:
    omega = 2.0 * math.pi * rpm / 60.0
    theta = omega * time_s
    r = geometry["crank_m"]
    length = geometry["rod_m"]
    sine = math.sin(theta)
    cosine = math.cos(theta)
    root = math.sqrt(length**2 - (r * sine) ** 2)
    dx_dtheta = r * sine + r**2 * sine * cosine / root
    return geometry["piston_area_m2"] * dx_dtheta * omega


def valve_lift_mm(
    crank_angle_deg: float,
    open_deg: float,
    close_deg: float,
    maximum_lift_mm: float,
) -> float:
    opening = open_deg % 720.0
    duration = (close_deg - open_deg) % 720.0
    progress = (crank_angle_deg - opening) % 720.0
    if progress > duration:
        return 0.0
    return 0.5 * maximum_lift_mm * (1.0 - math.cos(2.0 * math.pi * progress / duration))


def valve_effective_area_m2(
    count: int,
    head_diameter_mm: float,
    throat_area_mm2: float,
    lift_mm: float,
    cd: float,
) -> float:
    curtain_mm2 = count * math.pi * head_diameter_mm * max(lift_mm, 0.0)
    return cd * min(curtain_mm2, throat_area_mm2) * 1e-6


def compressible_orifice_mass_flow(
    upstream_pressure_pa: float,
    upstream_temperature_k: float,
    upstream_gamma: float,
    upstream_r_j_kg_k: float,
    downstream_pressure_pa: float,
    effective_area_m2: float,
) -> float:
    if effective_area_m2 <= 0.0 or upstream_pressure_pa <= downstream_pressure_pa:
        return 0.0
    gamma = min(max(upstream_gamma, 1.01), 1.67)
    ratio = max(downstream_pressure_pa / upstream_pressure_pa, 1e-12)
    critical = (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
    if ratio <= critical:
        factor = math.sqrt(gamma) * (2.0 / (gamma + 1.0)) ** (
            (gamma + 1.0) / (2.0 * (gamma - 1.0))
        )
    else:
        expression = 2.0 * gamma / (gamma - 1.0) * (
            ratio ** (2.0 / gamma) - ratio ** ((gamma + 1.0) / gamma)
        )
        factor = math.sqrt(max(expression, 0.0))
    return effective_area_m2 * upstream_pressure_pa / math.sqrt(
        max(upstream_r_j_kg_k * upstream_temperature_k, 1e-30)
    ) * factor


def wiebe_fraction_and_derivative(
    crank_angle_deg: float,
    start_deg: float,
    duration_deg: float,
    a: float,
    exponent_m: float,
) -> tuple[float, float]:
    progress = crank_angle_deg - start_deg
    if progress <= 0.0:
        return 0.0, 0.0
    if progress >= duration_deg:
        return 1.0 - math.exp(-a), 0.0
    normalized = progress / duration_deg
    power = exponent_m + 1.0
    exponential = math.exp(-a * normalized**power)
    fraction = 1.0 - exponential
    derivative_per_deg = exponential * a * power * normalized**exponent_m / duration_deg
    return fraction, derivative_per_deg


def _thermo_numbers(phase: Any) -> tuple[float, float]:
    cv = max(float(phase.cv_mass), 1e-30)
    gamma = float(phase.cp_mass) / cv
    r_specific = float(ct.gas_constant) / float(phase.mean_molecular_weight)
    return gamma, r_specific


def _set_flow(device: Any, value: float) -> None:
    device.mass_flow_coeff = max(float(value), 0.0)


def _initial_product_phase(mechanism: str, phase_name: str, pressure_pa: float, temperature_k: float, phi: float) -> Any:
    gas = ct.Solution(mechanism, phase_name)
    gas.TP = 700.0, pressure_pa
    gas.set_equivalence_ratio(phi, "c12h26", "o2:1,n2:3.76")
    gas.equilibrate("HP")
    gas.TP = temperature_k, pressure_pa
    return gas


def _species_marker(phase: Any) -> float:
    marker = 0.0
    for species in ("co2", "h2o", "co"):
        if species in phase.species_names:
            marker += float(phase[species].Y[0])
    return marker


def _chemical_heat_release_rate_w(phase: Any, volume_m3: float) -> float:
    return max(
        0.0,
        -float(sum(a * b for a, b in zip(phase.net_production_rates, phase.partial_molar_enthalpies))) * volume_m3,
    )


def _angle_crossed(previous_abs_deg: float, current_abs_deg: float, target_cycle_deg: float) -> bool:
    cycle = math.floor(previous_abs_deg / 720.0)
    for candidate_cycle in (cycle, cycle + 1):
        target = candidate_cycle * 720.0 + target_cycle_deg
        if previous_abs_deg < target <= current_abs_deg + 1e-12:
            return True
    return False


def _make_gzip_csv(path: Path, rows: Iterable[dict[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with __import__("io").TextIOWrapper(compressed, encoding="utf-8", newline="") as text_stream:
                writer = csv.DictWriter(text_stream, fieldnames=RAW_COLUMNS, lineterminator="\n")
                writer.writeheader()
                for row in rows:
                    writer.writerow({key: f"{row[key]:.12g}" for key in RAW_COLUMNS})


def run_case(
    contract: dict[str, Any],
    f45: dict[str, Any],
    architecture_id: str,
    model_id: str,
    cd: float,
    crank_step_deg: float,
) -> tuple[dict[str, Any], list[dict[str, float]]]:
    if ct is None:
        raise RuntimeError("Cantera 3.2.0 is required to execute F46")
    if ct.__version__ != "3.2.0":
        raise RuntimeError(f"Cantera 3.2.0 required, got {ct.__version__}")
    common = contract["common_operating_point"]
    finite = contract["combustion_models"]["cantera_finite_rate"]
    wiebe = contract["combustion_models"]["wiebe_counter_model"]
    valve = contract["valve_law"]
    numerical = contract["numerics"]
    geometry = slider_crank_geometry(contract)
    architecture = f45["architectures"][architecture_id]
    intake_valve = architecture["valves"]["intake"]
    exhaust_valve = architecture["valves"]["exhaust"]
    mechanism = finite["mechanism_file"]
    phase_name = finite["phase_name"]
    rpm = float(common["speed_rpm"])
    omega_deg_s = 6.0 * rpm
    dt = crank_step_deg / omega_deg_s

    intake_phase = ct.Solution(mechanism, phase_name)
    intake_phase.TPX = (
        float(common["intake_temperature_k"]),
        float(common["intake_pressure_pa_abs"]),
        common["air_composition_mole"],
    )
    fuel_phase = ct.Solution(mechanism, phase_name)
    fuel_phase.TPX = 500.0, float(common["intake_pressure_pa_abs"]), "c12h26:1"
    exhaust_phase = _initial_product_phase(
        mechanism,
        phase_name,
        float(common["exhaust_pressure_pa_abs"]),
        float(common["exhaust_reservoir_temperature_k"]),
        float(common["equivalence_ratio"]),
    )
    cylinder_phase = _initial_product_phase(
        mechanism,
        phase_name,
        float(common["exhaust_pressure_pa_abs"]),
        float(common["exhaust_reservoir_temperature_k"]),
        float(common["equivalence_ratio"]),
    )
    if model_id == "wiebe_counter_model":
        cylinder_phase.set_multiplier(0.0)
    elif model_id != "cantera_finite_rate":
        raise ValueError(f"unknown model: {model_id}")

    cylinder = ct.IdealGasReactor(
        cylinder_phase,
        energy="on",
        volume=geometry["clearance_volume_m3"],
        clone=True,
        name=f"cylinder_{architecture_id}_{model_id}",
    )
    intake_reservoir = ct.Reservoir(intake_phase, clone=True, name="intake")
    fuel_reservoir = ct.Reservoir(fuel_phase, clone=True, name="fuel")
    exhaust_reservoir = ct.Reservoir(exhaust_phase, clone=True, name="exhaust")
    wall_phase = ct.Solution(mechanism, phase_name)
    wall_phase.TPX = float(common["wall_temperature_k"]), 101325.0, "n2:1"
    wall_reservoir = ct.Reservoir(wall_phase, clone=True, name="wall_sink")

    intake_forward = ct.MassFlowController(intake_reservoir, cylinder, mdot=0.0)
    intake_reverse = ct.MassFlowController(cylinder, intake_reservoir, mdot=0.0)
    exhaust_forward = ct.MassFlowController(cylinder, exhaust_reservoir, mdot=0.0)
    exhaust_reverse = ct.MassFlowController(exhaust_reservoir, cylinder, mdot=0.0)
    injector = ct.MassFlowController(fuel_reservoir, cylinder, mdot=0.0)
    piston_wall = ct.Wall(
        cylinder,
        wall_reservoir,
        A=geometry["piston_area_m2"],
        velocity=lambda time_s: dvolume_dt(time_s, rpm, geometry) / geometry["piston_area_m2"],
    )
    heat_wall = ct.Wall(cylinder, wall_reservoir, A=geometry["piston_area_m2"], U=0.0)
    combustion_wall = ct.Wall(cylinder, wall_reservoir, A=geometry["piston_area_m2"], Q=0.0)
    network = ct.ReactorNet([cylinder])
    network.rtol = float(numerical["relative_tolerance"])
    network.atol = float(numerical["absolute_tolerance"])
    network.initialize()

    intake_gamma, intake_r = _thermo_numbers(intake_reservoir.phase)
    exhaust_gamma, exhaust_r = _thermo_numbers(exhaust_reservoir.phase)
    air_density = float(intake_reservoir.phase.density)
    stoich_air_fuel_ratio = 14.914  # dérivé de C12H26 + 18.5(O2+3.76N2)
    cycles = int(numerical["cycles"])
    steps_per_cycle = int(round(720.0 / crank_step_deg))
    total_steps = cycles * steps_per_cycle
    mean_piston_speed = 2.0 * geometry["stroke_m"] * rpm / 60.0

    current_cycle = 0
    cycle_stats: list[dict[str, float]] = []
    stats: dict[str, float] = {}
    fuel_target_kg = 0.0
    raw_rows: list[dict[str, float]] = []

    def reset_cycle() -> dict[str, float]:
        return {
            "mass_start_kg": float(cylinder.mass),
            "internal_energy_start_j": float(cylinder.mass * cylinder.phase.int_energy_mass),
            "air_forward_kg": 0.0,
            "intake_reverse_kg": 0.0,
            "exhaust_forward_kg": 0.0,
            "exhaust_reverse_kg": 0.0,
            "fuel_kg": 0.0,
            "enthalpy_in_j": 0.0,
            "enthalpy_out_j": 0.0,
            "boundary_work_j": 0.0,
            "wall_heat_out_j": 0.0,
            "external_combustion_heat_in_j": 0.0,
            "chemical_heat_release_j": 0.0,
            "peak_pressure_pa": float(cylinder.phase.P),
            "peak_temperature_k": float(cylinder.phase.T),
            "peak_heat_release_rate_w": 0.0,
            "peak_wall_heat_flux_w_m2": 0.0,
            "fuel_target_kg": 0.0,
            "ivc_marker_fraction": 0.0,
        }

    stats = reset_cycle()
    previous_volume = float(cylinder.volume)
    previous_abs_angle = 0.0

    for step_index in range(total_steps):
        abs_angle = step_index * crank_step_deg
        cycle_index = int(abs_angle // 720.0)
        crank_angle = abs_angle % 720.0
        if cycle_index != current_cycle:
            mass_end = float(cylinder.mass)
            energy_end = float(cylinder.mass * cylinder.phase.int_energy_mass)
            stats["mass_end_kg"] = mass_end
            stats["internal_energy_end_j"] = energy_end
            stats["fuel_target_kg"] = fuel_target_kg
            cycle_stats.append(stats)
            current_cycle = cycle_index
            stats = reset_cycle()
            fuel_target_kg = 0.0
            previous_volume = float(cylinder.volume)

        phase = cylinder.phase
        pressure = float(phase.P)
        temperature = float(phase.T)
        cyl_gamma, cyl_r = _thermo_numbers(phase)
        intake_lift = valve_lift_mm(
            crank_angle,
            float(valve["intake_open_deg_atdc_overlap"]),
            float(valve["intake_close_deg_atdc_overlap"]),
            float(intake_valve["maximum_lift_mm"]),
        )
        exhaust_lift = valve_lift_mm(
            crank_angle,
            float(valve["exhaust_open_deg_atdc_overlap"]),
            float(valve["exhaust_close_deg_atdc_overlap"]),
            float(exhaust_valve["maximum_lift_mm"]),
        )
        intake_area = valve_effective_area_m2(
            int(intake_valve["count"]),
            float(intake_valve["head_diameter_mm"]),
            float(intake_valve["flow"]["throat_area_mm2"]),
            intake_lift,
            cd,
        )
        exhaust_area = valve_effective_area_m2(
            int(exhaust_valve["count"]),
            float(exhaust_valve["head_diameter_mm"]),
            float(exhaust_valve["flow"]["throat_area_mm2"]),
            exhaust_lift,
            cd,
        )
        p_intake = float(intake_reservoir.phase.P)
        p_exhaust = float(exhaust_reservoir.phase.P)
        mdot_if = compressible_orifice_mass_flow(
            p_intake, float(intake_reservoir.phase.T), intake_gamma, intake_r, pressure, intake_area
        )
        mdot_ir = compressible_orifice_mass_flow(
            pressure, temperature, cyl_gamma, cyl_r, p_intake, intake_area
        )
        mdot_ef = compressible_orifice_mass_flow(
            pressure, temperature, cyl_gamma, cyl_r, p_exhaust, exhaust_area
        )
        mdot_er = compressible_orifice_mass_flow(
            p_exhaust, float(exhaust_reservoir.phase.T), exhaust_gamma, exhaust_r, pressure, exhaust_area
        )
        _set_flow(intake_forward, mdot_if)
        _set_flow(intake_reverse, mdot_ir)
        _set_flow(exhaust_forward, mdot_ef)
        _set_flow(exhaust_reverse, mdot_er)

        if _angle_crossed(previous_abs_angle, abs_angle, 230.0):
            net_air = max(stats["air_forward_kg"] - stats["intake_reverse_kg"], 0.0)
            fuel_target_kg = float(common["equivalence_ratio"]) * net_air / stoich_air_fuel_ratio
            stats["fuel_target_kg"] = fuel_target_kg
            stats["ivc_marker_fraction"] = _species_marker(phase)
        injection_start = float(finite["injection_start_deg"])
        injection_end = float(finite["injection_end_deg"])
        injection_duration_s = (injection_end - injection_start) / omega_deg_s
        if injection_start <= crank_angle < injection_end and fuel_target_kg > 0.0:
            fuel_mdot = fuel_target_kg / injection_duration_s
        else:
            fuel_mdot = 0.0
        _set_flow(injector, fuel_mdot)

        chamber_height = piston_displacement_m(math.radians(crank_angle % 360.0), geometry)
        wall_area = 2.0 * geometry["piston_area_m2"] + math.pi * geometry["bore_m"] * chamber_height
        htc = 130.0 * (max(pressure, 1e4) / 1e5) ** 0.8 * (
            max(temperature, 200.0) / 300.0
        ) ** -0.53 * (max(mean_piston_speed, 1.0) / 10.0) ** 0.8
        heat_wall.area = wall_area
        heat_wall.heat_transfer_coeff = htc

        combustion_qdot = 0.0
        if model_id == "wiebe_counter_model" and fuel_target_kg > 0.0:
            _, dx_ddeg = wiebe_fraction_and_derivative(
                crank_angle,
                float(wiebe["start_deg"]),
                float(wiebe["duration_deg"]),
                float(wiebe["a"]),
                float(wiebe["m"]),
            )
            combustion_qdot = (
                fuel_target_kg
                * float(common["fuel_lhv_j_kg"])
                * float(wiebe["efficiency"])
                * dx_ddeg
                * omega_deg_s
            )
            combustion_wall.area = wall_area
            combustion_wall.heat_flux = -combustion_qdot / max(wall_area, 1e-30)
        else:
            combustion_wall.heat_flux = 0.0

        chemical_qdot = (
            _chemical_heat_release_rate_w(phase, float(cylinder.volume))
            if model_id == "cantera_finite_rate"
            else 0.0
        )
        wall_heat_rate = float(heat_wall.heat_rate)
        wall_heat_flux = wall_heat_rate / max(wall_area, 1e-30)
        row = {
            "crank_angle_deg": crank_angle,
            "volume_m3": float(cylinder.volume),
            "pressure_pa_abs": pressure,
            "temperature_k": temperature,
            "mass_kg": float(cylinder.mass),
            "intake_lift_mm": intake_lift,
            "exhaust_lift_mm": exhaust_lift,
            "intake_effective_area_m2": intake_area,
            "exhaust_effective_area_m2": exhaust_area,
            "intake_net_mass_flow_kg_s": mdot_if - mdot_ir,
            "exhaust_net_mass_flow_kg_s": mdot_ef - mdot_er,
            "fuel_mass_flow_kg_s": fuel_mdot,
            "heat_release_rate_w": chemical_qdot if model_id == "cantera_finite_rate" else combustion_qdot,
            "wall_heat_rate_w": wall_heat_rate,
            "wall_heat_flux_w_m2": wall_heat_flux,
            "apparent_residual_marker_mass_fraction": _species_marker(phase),
        }
        if cycle_index == cycles - 1:
            raw_rows.append(row)

        stats["air_forward_kg"] += mdot_if * dt
        stats["intake_reverse_kg"] += mdot_ir * dt
        stats["exhaust_forward_kg"] += mdot_ef * dt
        stats["exhaust_reverse_kg"] += mdot_er * dt
        stats["fuel_kg"] += fuel_mdot * dt
        stats["enthalpy_in_j"] += (
            mdot_if * float(intake_reservoir.phase.enthalpy_mass)
            + mdot_er * float(exhaust_reservoir.phase.enthalpy_mass)
            + fuel_mdot * float(fuel_reservoir.phase.enthalpy_mass)
        ) * dt
        stats["enthalpy_out_j"] += (mdot_ir + mdot_ef) * float(phase.enthalpy_mass) * dt
        stats["wall_heat_out_j"] += wall_heat_rate * dt
        stats["external_combustion_heat_in_j"] += combustion_qdot * dt
        stats["chemical_heat_release_j"] += chemical_qdot * dt
        stats["peak_pressure_pa"] = max(stats["peak_pressure_pa"], pressure)
        stats["peak_temperature_k"] = max(stats["peak_temperature_k"], temperature)
        stats["peak_heat_release_rate_w"] = max(
            stats["peak_heat_release_rate_w"], row["heat_release_rate_w"]
        )
        stats["peak_wall_heat_flux_w_m2"] = max(
            stats["peak_wall_heat_flux_w_m2"], wall_heat_flux
        )

        next_time = (step_index + 1) * dt
        # Les coefficients quasi-stationnaires sont gelés sur chaque pas et
        # changent de manière discontinue au pas suivant. CVODES doit donc
        # repartir de l'état courant au lieu d'extrapoler l'ancien système.
        network.reinitialize()
        network.advance(next_time)
        new_volume = float(cylinder.volume)
        stats["boundary_work_j"] += pressure * (new_volume - previous_volume)
        previous_volume = new_volume
        previous_abs_angle = abs_angle

    mass_end = float(cylinder.mass)
    energy_end = float(cylinder.mass * cylinder.phase.int_energy_mass)
    stats["mass_end_kg"] = mass_end
    stats["internal_energy_end_j"] = energy_end
    stats["fuel_target_kg"] = fuel_target_kg
    cycle_stats.append(stats)

    last = cycle_stats[-1]
    mass_expected_delta = (
        last["air_forward_kg"]
        + last["exhaust_reverse_kg"]
        + last["fuel_kg"]
        - last["intake_reverse_kg"]
        - last["exhaust_forward_kg"]
    )
    mass_actual_delta = last["mass_end_kg"] - last["mass_start_kg"]
    mass_residual = mass_actual_delta - mass_expected_delta
    energy_expected_delta = (
        last["enthalpy_in_j"]
        - last["enthalpy_out_j"]
        - last["boundary_work_j"]
        - last["wall_heat_out_j"]
        + last["external_combustion_heat_in_j"]
    )
    energy_actual_delta = last["internal_energy_end_j"] - last["internal_energy_start_j"]
    energy_residual = energy_actual_delta - energy_expected_delta
    indicated_work = last["boundary_work_j"]
    imep_pa = indicated_work / geometry["swept_volume_m3"]
    cycle_rate_hz = rpm / 120.0
    indicated_power_w = indicated_work * cycle_rate_hz * int(contract["geometry"]["cylinder_count"])
    net_intake = last["air_forward_kg"] - last["intake_reverse_kg"]
    volumetric_efficiency = net_intake / max(air_density * geometry["swept_volume_m3"], 1e-30)
    mass_scale = max(
        abs(mass_expected_delta),
        last["air_forward_kg"] + last["fuel_kg"] + last["exhaust_reverse_kg"],
        1e-12,
    )
    energy_scale = max(
        abs(last["enthalpy_in_j"])
        + abs(last["enthalpy_out_j"])
        + abs(last["boundary_work_j"])
        + abs(last["wall_heat_out_j"])
        + abs(last["external_combustion_heat_in_j"]),
        1.0,
    )
    peak_hrr = max((row["heat_release_rate_w"] for row in raw_rows), default=0.0)
    positive_heat = [max(row["heat_release_rate_w"], 0.0) for row in raw_rows]
    total_heat = sum(value * dt for value in positive_heat)
    phasing: dict[str, float | None] = {"ca10_deg": None, "ca50_deg": None, "ca90_deg": None}
    if total_heat > 0.0:
        cumulative = 0.0
        targets = [(0.1, "ca10_deg"), (0.5, "ca50_deg"), (0.9, "ca90_deg")]
        target_index = 0
        for row, rate in zip(raw_rows, positive_heat):
            cumulative += rate * dt
            while target_index < len(targets) and cumulative >= targets[target_index][0] * total_heat:
                phasing[targets[target_index][1]] = rounded(row["crank_angle_deg"], 6)
                target_index += 1
    cycle_peaks = [item["peak_pressure_pa"] for item in cycle_stats]
    cycle_works = [item["boundary_work_j"] for item in cycle_stats]
    convergence_cycle = {
        "cycles_executed": cycles,
        "last_two_peak_pressure_relative_change": rounded(
            abs(cycle_peaks[-1] - cycle_peaks[-2]) / max(abs(cycle_peaks[-1]), 1.0)
        ),
        "last_two_indicated_work_relative_change": rounded(
            abs(cycle_works[-1] - cycle_works[-2]) / max(abs(cycle_works[-1]), 1.0)
        ),
        "numerical_periodicity_screen_pass": (
            abs(cycle_peaks[-1] - cycle_peaks[-2]) / max(abs(cycle_peaks[-1]), 1.0) < 0.01
            and abs(cycle_works[-1] - cycle_works[-2]) / max(abs(cycle_works[-1]), 1.0) < 0.01
        ),
        "physical_periodic_state_validated": False,
    }
    summary = {
        "case_id": f"{architecture_id}-{model_id}-cd{cd:.2f}-dca{crank_step_deg:g}",
        "architecture": architecture_id,
        "variant_id": architecture["id"],
        "model": model_id,
        "Cd": cd,
        "crank_step_deg": crank_step_deg,
        "cantera_version": ct.__version__,
        "last_cycle": {
            "peak_pressure_pa_abs": rounded(last["peak_pressure_pa"]),
            "peak_temperature_k": rounded(last["peak_temperature_k"]),
            "peak_heat_release_rate_w": rounded(peak_hrr),
            "chemical_heat_release_j": rounded(last["chemical_heat_release_j"]),
            "prescribed_combustion_heat_j": rounded(last["external_combustion_heat_in_j"]),
            "wall_heat_out_j": rounded(last["wall_heat_out_j"]),
            "peak_wall_heat_flux_w_m2": rounded(last["peak_wall_heat_flux_w_m2"]),
            "indicated_work_j_per_cylinder_cycle": rounded(indicated_work),
            "imep_pa": rounded(imep_pa),
            "indicated_power_w_12_cylinder_screen": rounded(indicated_power_w),
            "air_forward_kg": rounded(last["air_forward_kg"], 12),
            "intake_reverse_kg": rounded(last["intake_reverse_kg"], 12),
            "exhaust_forward_kg": rounded(last["exhaust_forward_kg"], 12),
            "exhaust_reverse_kg": rounded(last["exhaust_reverse_kg"], 12),
            "fuel_injected_kg": rounded(last["fuel_kg"], 12),
            "fuel_target_kg": rounded(last["fuel_target_kg"], 12),
            "volumetric_efficiency_screen": rounded(volumetric_efficiency),
            "ivc_apparent_product_marker_mass_fraction": rounded(last["ivc_marker_fraction"]),
            "combustion_phasing": phasing,
        },
        "balances": {
            "mass_actual_delta_kg": rounded(mass_actual_delta, 12),
            "mass_expected_delta_kg": rounded(mass_expected_delta, 12),
            "mass_residual_kg": rounded(mass_residual, 12),
            "mass_residual_fraction": rounded(abs(mass_residual) / mass_scale),
            "energy_actual_delta_j": rounded(energy_actual_delta),
            "energy_expected_delta_j": rounded(energy_expected_delta),
            "energy_residual_j": rounded(energy_residual),
            "energy_residual_fraction": rounded(abs(energy_residual) / energy_scale),
        },
        "cycle_convergence": convergence_cycle,
        "unavailable": {
            "true_residual_mass_fraction": "no_conserved_residual_tracer_in_single_zone_mechanism",
            "tumble_and_swirl": "zero_dimensional_model_has_no_velocity_field",
            "knock_margin": "surrogate_and_chemistry_not_correlated_to_917_race_fuel",
        },
        "validation_claimed": False,
    }
    return summary, raw_rows


def _relative_change(coarse: float, fine: float) -> float:
    return abs(fine - coarse) / max(abs(fine), 1e-30)


def _case_lookup(cases: list[dict[str, Any]], arch: str, model: str, cd: float, step: float) -> dict[str, Any]:
    return next(
        case
        for case in cases
        if case["architecture"] == arch
        and case["model"] == model
        and case["Cd"] == cd
        and case["crank_step_deg"] == step
    )


def _build_comparisons(contract: dict[str, Any], cases: list[dict[str, Any]]) -> dict[str, Any]:
    baseline_cd = float(contract["valve_law"]["baseline_cd"])
    finest = min(float(value) for value in contract["numerics"]["crank_angle_steps_deg"])
    fields = (
        "peak_pressure_pa_abs",
        "peak_temperature_k",
        "indicated_work_j_per_cylinder_cycle",
        "volumetric_efficiency_screen",
        "wall_heat_out_j",
    )
    convergence: dict[str, Any] = {}
    for arch in ("2v", "4v"):
        convergence[arch] = {}
        for model in ("cantera_finite_rate", "wiebe_counter_model"):
            ordered = [
                _case_lookup(cases, arch, model, baseline_cd, step)
                for step in contract["numerics"]["crank_angle_steps_deg"]
            ]
            comparisons = {}
            for field in fields:
                values = [case["last_cycle"][field] for case in ordered]
                comparisons[field] = {
                    "values_by_step": {
                        str(step): value
                        for step, value in zip(contract["numerics"]["crank_angle_steps_deg"], values)
                    },
                    "coarse_to_medium_relative_change": rounded(_relative_change(values[0], values[1])),
                    "medium_to_fine_relative_change": rounded(_relative_change(values[1], values[2])),
                }
            convergence[arch][model] = comparisons
    architecture_comparison: dict[str, Any] = {}
    for model in ("cantera_finite_rate", "wiebe_counter_model"):
        two = _case_lookup(cases, "2v", model, baseline_cd, finest)
        four = _case_lookup(cases, "4v", model, baseline_cd, finest)
        architecture_comparison[model] = {
            field: {
                "2v": two["last_cycle"][field],
                "4v": four["last_cycle"][field],
                "four_v_change_fraction": rounded(
                    (four["last_cycle"][field] - two["last_cycle"][field])
                    / max(abs(two["last_cycle"][field]), 1e-30)
                ),
            }
            for field in fields
        }
    cd_bracket: dict[str, Any] = {}
    for arch in ("2v", "4v"):
        cd_bracket[arch] = {}
        for model in ("cantera_finite_rate", "wiebe_counter_model"):
            cd_bracket[arch][model] = {
                str(cd): {
                    field: _case_lookup(cases, arch, model, float(cd), finest)["last_cycle"][field]
                    for field in fields
                }
                for cd in contract["valve_law"]["flow_coefficients_cd"]
            }
    cross_model: dict[str, Any] = {}
    for arch in ("2v", "4v"):
        kinetic = _case_lookup(cases, arch, "cantera_finite_rate", baseline_cd, finest)
        wiebe = _case_lookup(cases, arch, "wiebe_counter_model", baseline_cd, finest)
        cross_model[arch] = {
            field: {
                "cantera_finite_rate": kinetic["last_cycle"][field],
                "wiebe_counter_model": wiebe["last_cycle"][field],
                "relative_difference_vs_cantera": rounded(
                    abs(wiebe["last_cycle"][field] - kinetic["last_cycle"][field])
                    / max(abs(kinetic["last_cycle"][field]), 1e-30)
                ),
            }
            for field in fields
        }
    return {
        "step_convergence": convergence,
        "architecture_comparison_at_baseline_Cd_and_finest_step": architecture_comparison,
        "Cd_bracket_at_finest_step": cd_bracket,
        "cross_combustion_model_at_baseline_Cd_and_finest_step": cross_model,
    }


def _quality_assessment(contract: dict[str, Any], cases: list[dict[str, Any]], comparisons: dict[str, Any]) -> dict[str, Any]:
    mass_limit = float(contract["numerics"]["mass_balance_acceptance_fraction"])
    energy_limit = float(contract["numerics"]["energy_balance_acceptance_fraction"])
    step_limit = float(contract["numerics"]["step_convergence_acceptance_fraction"])
    mass_worst = max(case["balances"]["mass_residual_fraction"] for case in cases)
    energy_worst = max(case["balances"]["energy_residual_fraction"] for case in cases)
    periodic_worst = max(
        max(
            case["cycle_convergence"]["last_two_peak_pressure_relative_change"],
            case["cycle_convergence"]["last_two_indicated_work_relative_change"],
        )
        for case in cases
    )
    step_changes = [
        field["medium_to_fine_relative_change"]
        for architecture in comparisons["step_convergence"].values()
        for model in architecture.values()
        for field in model.values()
    ]
    cross_changes = [
        field["relative_difference_vs_cantera"]
        for architecture in comparisons["cross_combustion_model_at_baseline_Cd_and_finest_step"].values()
        for field in architecture.values()
    ]
    return {
        "mass_balance": {
            "limit_fraction": mass_limit,
            "worst_case_fraction": rounded(mass_worst),
            "all_cases_pass": mass_worst <= mass_limit,
        },
        "energy_balance": {
            "limit_fraction": energy_limit,
            "worst_case_fraction": rounded(energy_worst),
            "all_cases_pass": energy_worst <= energy_limit,
        },
        "last_cycle_numerical_periodicity": {
            "screen_limit_fraction": 0.01,
            "worst_case_fraction": rounded(periodic_worst),
            "all_cases_pass": periodic_worst <= 0.01,
            "physical_periodicity_validated": False,
        },
        "crank_step_convergence": {
            "limit_fraction": step_limit,
            "worst_medium_to_fine_fraction": rounded(max(step_changes)),
            "all_baseline_metrics_pass": max(step_changes) <= step_limit,
        },
        "cross_combustion_model": {
            "authority_limit_fraction": 0.05,
            "worst_relative_difference": rounded(max(cross_changes)),
            "all_metrics_pass": max(cross_changes) <= 0.05,
            "failed_comparison_blocks_validation": True,
        },
        "zero_dimensional_numerical_screen_completed": True,
        "physical_validation_completed": False,
    }


def _svg_polyline(points: list[tuple[float, float]], color: str, width: float = 2.5) -> str:
    encoded = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f'<polyline points="{encoded}" fill="none" stroke="{color}" stroke-width="{width}"/>'


def render_svg(report: dict[str, Any], raw_by_case: dict[str, list[dict[str, float]]], output: Path) -> None:
    width, height = 1600, 1000
    margin_x, margin_y = 90, 90
    plot_w, plot_h = 650, 340
    colors = {"2v": "#ef9f27", "4v": "#53b5e8"}
    panels = [
        (90, 150, "Pression cylindre — Cantera cinétique", "pressure_pa_abs", 1e-5, "bar"),
        (860, 150, "Température cylindre — Cantera cinétique", "temperature_k", 1.0, "K"),
        (90, 590, "Débits admission nets — Cd 0,72", "intake_net_mass_flow_kg_s", 1000.0, "g/s"),
        (860, 590, "Dégagement de chaleur — Cantera", "heat_release_rate_w", 1e-3, "kW"),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#071722"/>',
        '<text x="70" y="60" fill="#f5f7f9" font-family="sans-serif" font-size="34" font-weight="700">F46 — Porsche 917/30 turbo · comparaison 2V / 4V · calcul 0D non corrélé</text>',
        '<text x="70" y="100" fill="#ff8d8d" font-family="sans-serif" font-size="20">Aucune géométrie ovale · aucune autorisation d’impression ou de démarrage</text>',
    ]
    for panel_x, panel_y, title, field, scale, unit in panels:
        datasets = {}
        for arch in ("2v", "4v"):
            case = next(
                item
                for item in report["cases"]
                if item["architecture"] == arch
                and item["model"] == "cantera_finite_rate"
                and item["Cd"] == 0.72
                and item["crank_step_deg"] == 0.25
            )
            datasets[arch] = raw_by_case[case["case_id"]]
        values = [row[field] * scale for rows in datasets.values() for row in rows]
        y_min = min(values)
        y_max = max(values)
        if math.isclose(y_min, y_max):
            y_max = y_min + 1.0
        parts.extend([
            f'<rect x="{panel_x}" y="{panel_y}" width="{plot_w}" height="{plot_h}" rx="12" fill="#0d2533" stroke="#24485e"/>',
            f'<text x="{panel_x + 22}" y="{panel_y + 34}" fill="#f5f7f9" font-family="sans-serif" font-size="21" font-weight="600">{html.escape(title)}</text>',
            f'<text x="{panel_x + 22}" y="{panel_y + 62}" fill="#9bc2d6" font-family="monospace" font-size="15">min {y_min:.3g} · max {y_max:.3g} {unit}</text>',
        ])
        left = panel_x + 55
        top = panel_y + 80
        inner_w = plot_w - 75
        inner_h = plot_h - 115
        parts.append(f'<line x1="{left}" y1="{top + inner_h}" x2="{left + inner_w}" y2="{top + inner_h}" stroke="#54788b"/>')
        parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + inner_h}" stroke="#54788b"/>')
        for angle in (0, 180, 360, 540, 720):
            x = left + inner_w * angle / 720.0
            parts.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{top + inner_h}" stroke="#18394b"/>')
            parts.append(f'<text x="{x - 12}" y="{top + inner_h + 24}" fill="#9bc2d6" font-family="monospace" font-size="13">{angle}</text>')
        for arch, rows in datasets.items():
            points = []
            for row in rows:
                x = left + inner_w * row["crank_angle_deg"] / 720.0
                value = row[field] * scale
                y = top + inner_h * (1.0 - (value - y_min) / (y_max - y_min))
                points.append((x, y))
            parts.append(_svg_polyline(points, colors[arch]))
        parts.append(f'<text x="{left + inner_w - 160}" y="{top + 18}" fill="{colors["2v"]}" font-family="sans-serif" font-size="15">2V</text>')
        parts.append(f'<text x="{left + inner_w - 100}" y="{top + 18}" fill="{colors["4v"]}" font-family="sans-serif" font-size="15">4V</text>')
    parts.append('</svg>')
    output.write_text("\n".join(parts) + "\n", encoding="utf-8")


def execute(contract_path: Path, output_dir: Path, root: Path = ROOT) -> dict[str, Any]:
    contract = _load_json(contract_path)
    errors = validate_contract(contract, root)
    if errors:
        raise ValueError("; ".join(errors))
    f45 = _load_json(root / "twins/reference-917-engine/valvetrain-material-screen-f45.json")
    mechanism_name = contract["combustion_models"]["cantera_finite_rate"]["mechanism_file"]
    mechanism_path = _resolve_cantera_data_file(mechanism_name)
    mechanism_actual_hash = sha256(mechanism_path)
    mechanism_expected_hash = contract["combustion_models"]["cantera_finite_rate"]["mechanism_sha256"]
    if mechanism_actual_hash != mechanism_expected_hash:
        raise ValueError(
            f"Cantera mechanism hash mismatch: expected {mechanism_expected_hash}, got {mechanism_actual_hash}"
        )
    if output_dir.exists():
        shutil.rmtree(output_dir)
    raw_dir = output_dir / "raw"
    figures_dir = output_dir / "figures"
    raw_dir.mkdir(parents=True)
    figures_dir.mkdir(parents=True)
    cases: list[dict[str, Any]] = []
    raw_by_case: dict[str, list[dict[str, float]]] = {}
    for architecture in ("2v", "4v"):
        for model in ("cantera_finite_rate", "wiebe_counter_model"):
            for cd in contract["valve_law"]["flow_coefficients_cd"]:
                for step in contract["numerics"]["crank_angle_steps_deg"]:
                    print(
                        f"F46 run architecture={architecture} model={model} Cd={float(cd):.2f} dCA={float(step):g}",
                        file=sys.stderr,
                        flush=True,
                    )
                    summary, rows = run_case(
                        contract,
                        f45,
                        architecture,
                        model,
                        float(cd),
                        float(step),
                    )
                    raw_path = raw_dir / f"{summary['case_id']}.csv.gz"
                    _make_gzip_csv(raw_path, rows)
                    summary["raw_timeseries"] = {
                        "path": str(raw_path.relative_to(root)),
                        "sha256": sha256(raw_path),
                        "rows": len(rows),
                        "columns": list(RAW_COLUMNS),
                    }
                    cases.append(summary)
                    raw_by_case[summary["case_id"]] = rows
    comparisons = _build_comparisons(contract, cases)
    report = {
        "schema_version": "1.0.0",
        "phase": "F46",
        "classification": contract["classification"],
        "runtime": {
            "cantera_version": ct.__version__,
            "python_version": sys.version.split()[0],
            "mechanism_file": mechanism_name,
            "mechanism_sha256_expected": mechanism_expected_hash,
            "mechanism_sha256_actual": mechanism_actual_hash,
            "case_count": len(cases),
        },
        "input_manifest": {
            "contract_path": str(contract_path.relative_to(root)),
            "contract_sha256": sha256(contract_path),
            "valvetrain_f45_path": str(F45.relative_to(ROOT)),
            "valvetrain_f45_sha256": sha256(F45),
        },
        "equations": {
            "slider_crank": "x=r(1-cos(theta))+l-sqrt(l^2-r^2 sin^2(theta)); V=Vc+Ap*x",
            "curtain_area": "Acurtain=N*pi*D*L(theta)",
            "effective_valve_area": "Aeff=Cd*min(Acurtain,Athroat)",
            "compressible_orifice": "mdot=Aeff*p0/sqrt(R*T0)*Phi(gamma,p1/p0), choked below critical pressure ratio",
            "wiebe": "xb=1-exp(-a*((theta-theta0)/duration)^(m+1))",
            "first_law": "DeltaU=Hin-Hout-Wboundary-Qwall+Qprescribed",
            "mass_balance": "Deltam=min-mout",
        },
        "common_conditions_identical_between_architectures": contract["common_operating_point"],
        "cases": cases,
        "comparisons": comparisons,
        "quality_assessment": _quality_assessment(contract, cases, comparisons),
        "scope_limitations": contract["unavailable_from_zero_dimensional_model"],
        "release_gates": contract["release_gates"],
        "conclusion": {
            "numerical_execution_completed": True,
            "Cantera_finite_rate_and_Wiebe_counter_model_executed": True,
            "both_architectures_share_identical_non_geometry_boundaries": True,
            "external_geometry_created": False,
            "oval_or_ellipse_created": False,
            "combustion_validation_claimed": False,
            "print_or_engine_start_authorized": False,
        },
    }
    report_path = output_dir / "cycle-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "phase": "F46",
        "classification": report["classification"],
        "runtime": report["runtime"],
        "input_manifest": report["input_manifest"],
        "quality_assessment": report["quality_assessment"],
        "comparisons": report["comparisons"],
        "scope_limitations": report["scope_limitations"],
        "release_gates": report["release_gates"],
        "conclusion": report["conclusion"],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    render_svg(report, raw_by_case, figures_dir / "f46-2v-4v-cycle.svg")
    manifest = {
        "phase": "F46",
        "artifacts": [
            {
                "path": str(path.relative_to(root)),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in sorted(output_dir.rglob("*"))
            if path.is_file() and path.name != "manifest.json"
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def check_evidence(contract_path: Path, output_dir: Path, root: Path = ROOT) -> list[str]:
    errors = validate_contract(_load_json(contract_path), root)
    report_path = output_dir / "cycle-report.json"
    manifest_path = output_dir / "manifest.json"
    if not report_path.is_file():
        errors.append("missing cycle-report.json")
        return errors
    if not manifest_path.is_file():
        errors.append("missing manifest.json")
        return errors
    report = _load_json(report_path)
    manifest = _load_json(manifest_path)
    if report.get("runtime", {}).get("cantera_version") != "3.2.0":
        errors.append("evidence was not executed with Cantera 3.2.0")
    if len(report.get("cases", [])) != 36:
        errors.append("exact 36-case matrix required")
    if report.get("conclusion", {}).get("oval_or_ellipse_created") is not False:
        errors.append("evidence must keep oval_or_ellipse_created false")
    if any(value is not False for value in report.get("release_gates", {}).values()):
        errors.append("all evidence release gates must remain false")
    listed = {item["path"]: item for item in manifest.get("artifacts", [])}
    for relative, item in listed.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"manifest artifact missing: {relative}")
        elif sha256(path) != item.get("sha256"):
            errors.append(f"manifest artifact hash mismatch: {relative}")
    expected_raw = {
        case.get("raw_timeseries", {}).get("path")
        for case in report.get("cases", [])
    }
    if None in expected_raw or len(expected_raw) != 36:
        errors.append("each case must bind one unique raw file")
    for case in report.get("cases", []):
        raw = case.get("raw_timeseries", {})
        path = root / raw.get("path", "")
        if not path.is_file() or sha256(path) != raw.get("sha256"):
            errors.append(f"raw binding invalid: {case.get('case_id')}")
        if case.get("validation_claimed") is not False:
            errors.append(f"case validation flag must remain false: {case.get('case_id')}")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    contract = (args.contract or root / CONTRACT.relative_to(ROOT)).resolve()
    output = (args.output or root / DEFAULT_OUTPUT.relative_to(ROOT)).resolve()
    if args.check:
        errors = check_evidence(contract, output, root)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print("F46 Cantera crank-cycle evidence: OK")
        return 0
    execute(contract, output, root)
    print(output / "cycle-report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
