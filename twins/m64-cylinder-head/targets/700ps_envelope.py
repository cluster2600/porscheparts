#!/usr/bin/env python3
"""Traceable 0-D target balance; no engine performance or release prediction."""

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path


PS_W = 735.49875
MECHANICAL_HP_W = 745.6998715822702
KG_PER_LB = 0.45359237
R_AIR = 287.05
CP_AIR = 1005.0
GAMMA_AIR = 1.4
REFERENCE_T_K = 288.15
REFERENCE_P_PA = 101325.0


def balance(*, power_ps, rpm, displacement_l, bsfc_kg_per_kwh,
            lambda_ratio, stoichiometric_afr, volumetric_efficiency,
            manifold_temperature_k, ambient_pressure_pa,
            compressor_inlet_temperature_k, inlet_pressure_loss_pa,
            charge_path_pressure_loss_pa, compressor_isentropic_efficiency,
            fuel_lhv_mj_per_kg, turbochargers):
    inputs = dict(locals())
    for key, value in inputs.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number")
        if key in ("inlet_pressure_loss_pa", "charge_path_pressure_loss_pa"):
            if value < 0:
                raise ValueError(f"{key} must be nonnegative")
        elif value <= 0:
            raise ValueError(f"{key} must be positive")
    if not isinstance(turbochargers, int):
        raise ValueError("turbochargers must be an integer")
    if compressor_isentropic_efficiency > 1:
        raise ValueError("compressor_isentropic_efficiency must not exceed one")
    p_in = ambient_pressure_pa - inlet_pressure_loss_pa
    if p_in <= 0:
        raise ValueError("compressor inlet absolute pressure must be positive")

    power_w = power_ps * PS_W
    displacement_m3 = displacement_l * 1e-3
    omega = rpm * 2 * math.pi / 60
    torque_nm = power_w / omega
    # Four-stroke: one cycle every two crank revolutions.
    bmep_pa = power_w * 120 / (rpm * displacement_m3)
    fuel_kg_s = (power_w / 1000) * bsfc_kg_per_kwh / 3600
    afr = lambda_ratio * stoichiometric_afr
    air_kg_s = fuel_kg_s * afr
    volume_flow_m3_s = volumetric_efficiency * displacement_m3 * rpm / 120
    p_manifold = air_kg_s * R_AIR * manifold_temperature_k / volume_flow_m3_s
    p_out = p_manifold + charge_path_pressure_loss_pa
    pr = p_out / p_in
    if pr < 1:
        raise ValueError("scenario does not require compression; this model requires PR >= 1")
    t_out = compressor_inlet_temperature_k * (
        1 + (pr ** ((GAMMA_AIR - 1) / GAMMA_AIR) - 1) /
        compressor_isentropic_efficiency
    )
    charge_heat_kw = air_kg_s * CP_AIR * (t_out - manifold_temperature_k) / 1000
    fuel_power_kw = fuel_kg_s * fuel_lhv_mj_per_kg * 1000
    brake_efficiency = power_w / 1000 / fuel_power_kw
    if brake_efficiency >= 1:
        raise ValueError("BSFC and LHV imply nonphysical brake efficiency >= 1")
    corrected_air_kg_s = air_kg_s * math.sqrt(
        compressor_inlet_temperature_k / REFERENCE_T_K) / (p_in / REFERENCE_P_PA)
    return {
        "power_kw_target": power_w / 1000,
        "power_mechanical_hp_target": power_w / MECHANICAL_HP_W,
        "torque_nm_required_at_this_rpm": torque_nm,
        "bmep_bar_required": bmep_pa / 1e5,
        "fuel_kg_per_h": fuel_kg_s * 3600,
        "air_fuel_mass_ratio": afr,
        "air_kg_per_s": air_kg_s,
        "air_lb_per_min": air_kg_s * 60 / KG_PER_LB,
        "air_per_turbo_kg_per_s": air_kg_s / turbochargers,
        "air_per_turbo_lb_per_min": air_kg_s * 60 / KG_PER_LB / turbochargers,
        "corrected_air_per_turbo_lb_per_min_reporting_reference": corrected_air_kg_s * 60 / KG_PER_LB / turbochargers,
        "compressor_inlet_absolute_bar": p_in / 1e5,
        "manifold_absolute_bar_required": p_manifold / 1e5,
        "manifold_gauge_bar_relative_to_local_ambient": (p_manifold - ambient_pressure_pa) / 1e5,
        "compressor_pressure_ratio_required": pr,
        "compressor_outlet_temperature_k_constant_property_model": t_out,
        "charge_cooler_heat_kw_constant_property_model": charge_heat_kw,
        "fuel_lower_heating_power_kw": fuel_power_kw,
        "brake_thermal_efficiency_implied_by_BSFC_and_LHV": brake_efficiency,
        "fuel_power_minus_brake_kw_NOT_head_heat": fuel_power_kw - power_w / 1000,
    }


def report(target):
    model = target["balance_model"]
    base = model["base_case"]
    axes = model["sensitivity_axes"]
    power = target["user_target"]["power"]
    if (power["unit"] != "PS" or power["location"] != "crankshaft" or
            power["value"] != base["power_ps"]):
        raise ValueError("target must consistently specify metric crankshaft PS")
    if (target["user_target"]["cycle"] != "four_stroke" or
            target["user_target"]["turbochargers"] != base["turbochargers"]):
        raise ValueError("target cycle and turbo count must match this model")
    if model["constant_air_properties"] != {
            "R_j_per_kg_k": R_AIR, "cp_j_per_kg_k": CP_AIR, "gamma": GAMMA_AIR}:
        raise ValueError("documented constant air properties must match the implementation")
    reference = model["corrected_flow_reference"]
    if reference["temperature_k"] != REFERENCE_T_K or reference["pressure_pa"] != REFERENCE_P_PA:
        raise ValueError("documented corrected-flow reference must match the implementation")
    if any(not values or any(not math.isfinite(v) for v in values) for values in axes.values()):
        raise ValueError("sensitivity axes must contain finite values")
    ofat = []
    for key, values in axes.items():
        for value in values:
            case = dict(base, **{key: value})
            ofat.append({"axis": key, "value": value, "result": balance(**case)})
    # All endpoint combinations, not a probability distribution or measured envelope.
    corners = []
    for values in itertools.product(*(sorted(set((min(v), max(v)))) for v in axes.values())):
        overrides = dict(zip(axes, values))
        corners.append({"inputs": overrides, "result": balance(**dict(base, **overrides))})
    keys = balance(**base)
    extrema = {
        key: {"minimum": min(c["result"][key] for c in corners),
              "maximum": max(c["result"][key] for c in corners)}
        for key in keys
    }
    return {
        "target_id": target["id"],
        "status": "calculated_target_sensitivity_not_achieved_engine_performance",
        "units": "explicit_in_field_names; pressures absolute except explicitly gauge",
        "base_inputs": base,
        "base_result": balance(**base),
        "one_factor_at_a_time": ofat,
        "corner_count": len(corners),
        "corner_extrema_not_qualified_operating_limits": extrema,
        "corners": corners,
        "exclusions": model["missing_physics"],
        "maximum_cylinder_pressure_predicted": False,
        "head_heat_flux_predicted": False,
        "performance_validated": False,
        "manufacturing_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=Path(__file__).with_name("700ps-biturbo.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = args.target.read_bytes()
    result = report(json.loads(data))
    result["target_sha256"] = hashlib.sha256(data).hexdigest()
    result["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        # A generated result never silently overwrites an earlier calculation.
        with args.output.open("x") as stream:
            stream.write(encoded)
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
