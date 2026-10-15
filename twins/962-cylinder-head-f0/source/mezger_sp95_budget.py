"""Assumed 4 L / 1,000 metric PS SP95 sizing; no combustion or fitment validation."""
import hashlib
import json
import math
from pathlib import Path

from thermal_budget import calculate as tec_budget

POWER_W = 1000 * 735.49875
BORE_M = .102
STROKE_M = .0816
DISPLACEMENT_M3 = math.pi / 4 * BORE_M ** 2 * STROKE_M * 6
# shortcut: constant water/air properties, replace with f(T,p,mixture) for CHT.
WATER_CP_J_KG_K = 4180
WATER_DENSITY_KG_M3 = 965
OLD_PORT_AREA_M2 = 75.84238854259502e-6


def calculate(rpm=7000, brake_efficiency=.30, lambda_value=.82,
              volumetric_efficiency=1., charge_c=50., fuel_lhv_j_kg=42.5e6,
              stoich_afr=14.4, fuel_density_kg_m3=745.,
              head_heat_fraction=.12, water_delta_k=15.):
    """One steady full-power scenario; all arguments are unmeasured assumptions."""
    assumptions = locals().copy()
    try:
        valid = all(type(v) in (int, float) and math.isfinite(v)
                    for v in assumptions.values())
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError("Inputs must be finite numbers, not booleans or strings")
    if (any(v <= 0 for k, v in assumptions.items() if k != "charge_c")
            or charge_c <= -273.15 or not 0 < brake_efficiency < 1
            or head_heat_fraction >= 1 - brake_efficiency
            or volumetric_efficiency > 2 or lambda_value > 2):
        raise ValueError("Invalid thermodynamic assumptions")
    try:
        omega = rpm * 2 * math.pi / 60
        torque = POWER_W / omega
        fuel_power = POWER_W / brake_efficiency
        fuel_mass = fuel_power / fuel_lhv_j_kg
        fuel_l_h = fuel_mass / fuel_density_kg_m3 * 3.6e6
        air_mass = fuel_mass * stoich_afr * lambda_value
        manifold_pa = (air_mass * 287.05 * (charge_c + 273.15)
                       / (volumetric_efficiency * DISPLACEMENT_M3 * rpm / 120))
        # Assumed 1.01325 bar ambient, 2 kPa filter loss, 10 kPa charge-path loss.
        pressure_ratio = (manifold_pa + 10000) / (101325 - 2000)
        if pressure_ratio < 1:
            raise ValueError("This study requires a compressor pressure ratio >= 1")
        compressor_k = 298.15 * (1 + (pressure_ratio ** (2 / 7) - 1) / .72)
        intercooler_w = air_mass * 1005 * (compressor_k - charge_c - 273.15)
        if intercooler_w < 0:
            raise ValueError("Charge target is above the calculated compressor outlet")
        head_heat = fuel_power * head_heat_fraction
        water_mass = head_heat / (WATER_CP_J_KG_K * water_delta_k)
        per_head_water_volume = water_mass / WATER_DENSITY_KG_M3 / 6
        values = dict(
            power_kw=POWER_W / 1000, displacement_cm3=DISPLACEMENT_M3 * 1e6,
            torque_nm=torque, bmep_bar=4 * math.pi * torque / DISPLACEMENT_M3 / 1e5,
            mean_piston_speed_m_s=2 * STROKE_M * rpm / 60,
            fuel_power_kw=fuel_power / 1000,
            total_non_brake_power_kw=(fuel_power - POWER_W) / 1000,
            bsfc_g_kwh=fuel_mass * 3.6e9 / POWER_W,
            fuel_kg_h=fuel_mass * 3600, fuel_l_h=fuel_l_h,
            assumed_pump_delivery_l_h=fuel_l_h * 1.25,
            assumed_pump_pressure_bar=3 + manifold_pa / 1e5 - 1.01325,
            injector_cm3_min_each_at_80pct=fuel_l_h * 1000 / 60 / 6 / .8,
            air_kg_s=air_mass, air_each_turbo_kg_s=air_mass / 2,
            air_each_turbo_lb_min=air_mass / 2 * 60 / .45359237,
            manifold_absolute_bar=manifold_pa / 1e5,
            boost_gauge_bar=manifold_pa / 1e5 - 1.01325,
            compressor_pressure_ratio=pressure_ratio,
            compressor_outlet_c=compressor_k - 273.15,
            intercoolers_total_kw=intercooler_w / 1000,
            head_coolant_total_kw=head_heat / 1000,
            head_coolant_each_kw=head_heat / 6000,
            unallocated_non_brake_power_kw=(fuel_power - POWER_W - head_heat) / 1000,
            water_total_kg_s=water_mass,
            water_total_l_min=water_mass / WATER_DENSITY_KG_M3 * 60000,
            water_each_bank_l_min=per_head_water_volume * 3 * 60000,
            water_each_head_l_min=per_head_water_volume * 60000,
            old_port_mean_speed_m_s=per_head_water_volume / OLD_PORT_AREA_M2,
            old_port_dynamic_pressure_bar=(WATER_DENSITY_KG_M3 / 2
                * (per_head_water_volume / OLD_PORT_AREA_M2) ** 2 / 1e5),
            head_port_id_at_3m_s_mm=math.sqrt(4 * per_head_water_volume / (math.pi * 3)) * 1000,
            bank_header_id_at_3m_s_mm=math.sqrt(4 * per_head_water_volume / math.pi) * 1000,
        )
        if not all(math.isfinite(v) for v in values.values()):
            raise ValueError("Budget overflow")
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Budget overflow") from exc
    return dict(assumptions=assumptions, results=values)


def report():
    nominal = calculate()
    sweeps = {}
    for parameter, points, columns in (
        ("rpm", [6500, 7000, 7500, 8000],
         ["torque_nm", "bmep_bar", "mean_piston_speed_m_s", "boost_gauge_bar"]),
        ("brake_efficiency", [.26, .30, .34],
         ["bsfc_g_kwh", "fuel_l_h", "air_kg_s", "boost_gauge_bar", "head_coolant_total_kw"]),
        ("lambda_value", [.78, .82, .86], ["air_kg_s", "boost_gauge_bar"]),
        ("volumetric_efficiency", [.9, 1., 1.1], ["boost_gauge_bar"]),
        ("charge_c", [40, 50, 60], ["boost_gauge_bar", "intercoolers_total_kw"]),
    ):
        sweeps[parameter] = []
        for point in points:
            result = calculate(**{parameter: point})["results"]
            sweeps[parameter].append({parameter: point, **{k: result[k] for k in columns}})
    cooling = []
    for fraction in (.08, .12, .16):
        for delta in (10, 15, 20):
            result = calculate(head_heat_fraction=fraction, water_delta_k=delta)["results"]
            cooling.append(dict(head_heat_fraction=fraction, water_delta_k=delta,
                                **{k: result[k] for k in (
                                    "head_coolant_total_kw", "water_total_l_min",
                                    "water_each_head_l_min", "head_port_id_at_3m_s_mm")}))
    fuel = []
    # Property brackets are illustrative, not certificates for E5/E10 batches.
    for lhv, afr, density in ((41.5e6, 14.1, 755), (42.5e6, 14.4, 745), (43e6, 14.7, 735)):
        point = calculate(fuel_lhv_j_kg=lhv, stoich_afr=afr, fuel_density_kg_m3=density)
        fuel.append(dict(**{k: point["assumptions"][k] for k in (
            "fuel_lhv_j_kg", "stoich_afr", "fuel_density_kg_m3")},
            **{k: point["results"][k] for k in ("fuel_l_h", "air_kg_s", "boost_gauge_bar")}))
    return dict(
        source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (
            Path(__file__), Path(__file__).with_name("thermal_budget.py"),
            Path(__file__).resolve().parents[1] / "derived/architecture-report.json")},
        status="assumption_only_not_a_validated_sp95_operating_point",
        target=dict(engine="Mezger", displacement_l=4, crankshaft_power_ch=1000,
                    fuel="SP95", ron=95, ethanol_volume_fraction=None, turbos=2,
                    valves_per_cylinder=4, ignition_points_per_cylinder=2),
        constants=dict(bore_mm=102, stroke_mm=81.6, cylinders=6, strokes=4,
                       ambient_pa=101325, filter_loss_pa=2000, charge_path_loss_pa=10000,
                       compressor_inlet_c=25, compressor_isentropic_efficiency=.72,
                       water_cp_j_kg_k=WATER_CP_J_KG_K, water_density_kg_m3=WATER_DENSITY_KG_M3,
                       air_cp_j_kg_k=1005, air_gamma=1.4, air_r_j_kg_k=287.05,
                       old_study_port_area_mm2=OLD_PORT_AREA_M2 * 1e6, target_port_mean_speed_m_s=3,
                       injectors=6, injector_duty=.8, injector_differential_bar=3,
                       fuel_pump_delivery_factor=1.25),
        nominal=nominal, one_at_a_time_sensitivity=sweeps,
        fuel_property_brackets=fuel, cooling_sensitivity=cooling,
        clearance_volume_sweep=[dict(compression_ratio=ratio,
            total_clearance_volume_cm3=DISPLACEMENT_M3 / 6 * 1e6 / (ratio - 1))
            for ratio in (8, 8.5, 9, 9.5)],
        hypothetical_peak_pressure_loads=[dict(peak_cylinder_pressure_bar=p,
            gas_force_kn=p * 1e5 * math.pi * BORE_M ** 2 / 4 / 1000) for p in (140, 180, 220)],
        wall_conduction_sensitivity=[dict(heat_flux_mw_m2=q, thickness_mm=4.5,
            conductivity_w_m_k=k, solid_only_delta_k=q * 1e6 * .0045 / k)
            for q in (1, 3, 5) for k in (100, 160, 220, 320)],
        peltier_entire_head_loop=[tec_budget(nominal["results"]["head_coolant_total_kw"] * 1000,
                                           cop, 48, .9, 0) for cop in (.5, 1, 2)],
        unknowns=dict(exact_donor_variant=None, measured_interfaces=None,
                      compression_ratio=None, peak_cylinder_pressure_bar=None,
                      cam_timing_and_lift=None, coolant_mixture=None,
                      coolant_heat_split=None, alloy_and_lpbf_process=None,
                      knock_limited_boost_bar=None, ignition_timing_deg=None,
                      compressor_map_selection=None, turbine_backpressure_bar=None),
        qualification=dict(combustion_validated=False, knock_validated=False,
                           fitment_validated=False, cfd_cht_validated=False,
                           material_qualified=False, manufacturing_authorized=False),
    )


if __name__ == "__main__":
    destination = Path(__file__).resolve().parents[1] / "derived/mezger-sp95-budget.json"
    destination.write_text(json.dumps(report(), indent=2, allow_nan=False) + "\n")
    print(destination)
