#!/usr/bin/env python3
"""Dimensionne et compare les concepts de culasse 2V/4V F29.

Ce calcul est volontairement un filtre de conception : ecoulement quasi-statique,
plaque circulaire mince, conduction 1D et mouvement de soupape sinusoidal. Il ne
remplace ni CFD, ni FEA 3D, ni dynamique de distribution, ni essai moteur.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = ROOT / "twins/reference-917-engine/clean-sheet-cylinder-head-f29.json"
DEFAULT_OUTPUT = ROOT / "work/917-clean-sheet-head-f29/design-study.json"
YOUNGS_MODULUS_PA = 70.0e9
POISSON_RATIO = 0.33
INTAKE_DISCHARGE_COEFFICIENT = 0.72
EXHAUST_DISCHARGE_COEFFICIENT = 0.68
INTAKE_GAS_DIFFERENTIAL_PA = 150_000.0
EXHAUST_GAS_DIFFERENTIAL_PA = 600_000.0
CAM_EVENT_DURATION_CRANK_DEG = 280.0


class StudyError(ValueError):
    """Le contrat F29 ou un resultat de calcul est incoherent."""


@dataclass(frozen=True)
class ValveCandidate:
    intake_diameter_mm: float
    exhaust_diameter_mm: float
    intake_lift_mm: float
    exhaust_lift_mm: float
    seat_ring_radius_mm: float
    minimum_seat_bridge_mm: float
    chamber_edge_margin_mm: float
    intake_mean_effective_area_mm2: float
    exhaust_mean_effective_area_mm2: float
    total_valve_mass_g: float


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StudyError(f"missing_input:{path}") from exc
    except json.JSONDecodeError as exc:
        raise StudyError(f"invalid_json:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise StudyError(f"expected_json_object:{path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise StudyError(message)


def valve_positions(architecture: str, ring_radius_mm: float) -> dict[str, list[list[float]]]:
    if architecture == "2v":
        return {
            "intake": [[0.0, ring_radius_mm]],
            "exhaust": [[0.0, -ring_radius_mm]],
        }
    if architecture == "4v":
        coordinate = ring_radius_mm / math.sqrt(2.0)
        return {
            "intake": [[-coordinate, coordinate], [coordinate, coordinate]],
            "exhaust": [[-coordinate, -coordinate], [coordinate, -coordinate]],
        }
    raise StudyError(f"unsupported_architecture:{architecture}")


def pairwise_seat_bridge_mm(
    positions: dict[str, list[list[float]]],
    intake_diameter_mm: float,
    exhaust_diameter_mm: float,
) -> float:
    valves: list[tuple[float, float, float]] = []
    valves.extend((x, y, intake_diameter_mm) for x, y in positions["intake"])
    valves.extend((x, y, exhaust_diameter_mm) for x, y in positions["exhaust"])
    bridges = []
    for first, second in itertools.combinations(valves, 2):
        centre_distance = math.hypot(first[0] - second[0], first[1] - second[1])
        bridges.append(centre_distance - 0.5 * (first[2] + second[2]))
    return min(bridges)


def chamber_edge_margin_mm(
    bore_mm: float,
    positions: dict[str, list[list[float]]],
    intake_diameter_mm: float,
    exhaust_diameter_mm: float,
) -> float:
    margins = []
    for valve_type, diameter in (
        ("intake", intake_diameter_mm),
        ("exhaust", exhaust_diameter_mm),
    ):
        for x, y in positions[valve_type]:
            margins.append(0.5 * bore_mm - math.hypot(x, y) - 0.5 * diameter)
    return min(margins)


def effective_area_mm2(
    count: int,
    diameter_mm: float,
    lift_mm: float,
    discharge_coefficient: float,
) -> float:
    curtain_area = count * math.pi * diameter_mm * lift_mm
    throat_diameter = 0.86 * diameter_mm
    throat_area = count * math.pi * throat_diameter**2 / 4.0
    return discharge_coefficient * min(curtain_area, throat_area)


def mean_effective_area_mm2(
    count: int,
    diameter_mm: float,
    maximum_lift_mm: float,
    discharge_coefficient: float,
    samples: int,
) -> float:
    require(samples >= 3 and samples % 2 == 1, "lift_profile_sample_count_must_be_odd")
    values = []
    for index in range(samples):
        phase = math.pi * index / (samples - 1)
        lift = maximum_lift_mm * math.sin(phase)
        values.append(
            effective_area_mm2(count, diameter_mm, lift, discharge_coefficient)
        )
    step = 1.0 / (samples - 1)
    integral = step * (
        0.5 * values[0] + sum(values[1:-1]) + 0.5 * values[-1]
    )
    return integral


def estimated_valve_mass_kg(diameter_mm: float, density_kg_m3: float) -> float:
    diameter_m = diameter_mm / 1000.0
    head_thickness_m = 0.08 * diameter_m
    stem_diameter_m = max(0.0055, 0.115 * diameter_m)
    stem_length_m = 0.065
    volume_m3 = (
        math.pi * (diameter_m / 2.0) ** 2 * head_thickness_m
        + math.pi * (stem_diameter_m / 2.0) ** 2 * stem_length_m
    )
    return density_kg_m3 * volume_m3


def iter_candidates(
    architecture: str,
    architecture_config: dict[str, Any],
    bore_mm: float,
    samples: int,
    minimum_bridge_mm: float,
    minimum_edge_margin_mm: float,
    intake_density_kg_m3: float,
    exhaust_density_kg_m3: float,
) -> Iterable[ValveCandidate]:
    intake_count = int(architecture_config["intake_count"])
    exhaust_count = int(architecture_config["exhaust_count"])
    ring_radius_mm = float(architecture_config["seat_ring_radius_ratio"]) * bore_mm
    positions = valve_positions(architecture, ring_radius_mm)
    grids = (
        architecture_config["intake_diameter_ratios"],
        architecture_config["exhaust_diameter_ratios"],
        architecture_config["intake_lift_ratios"],
        architecture_config["exhaust_lift_ratios"],
    )
    for intake_ratio, exhaust_ratio, intake_lift_ratio, exhaust_lift_ratio in itertools.product(*grids):
        intake_diameter_mm = float(intake_ratio) * bore_mm
        exhaust_diameter_mm = float(exhaust_ratio) * bore_mm
        intake_lift_mm = float(intake_lift_ratio) * intake_diameter_mm
        exhaust_lift_mm = float(exhaust_lift_ratio) * exhaust_diameter_mm
        bridge = pairwise_seat_bridge_mm(
            positions, intake_diameter_mm, exhaust_diameter_mm
        )
        edge_margin = chamber_edge_margin_mm(
            bore_mm, positions, intake_diameter_mm, exhaust_diameter_mm
        )
        if bridge < minimum_bridge_mm or edge_margin < minimum_edge_margin_mm:
            continue
        intake_mass = intake_count * estimated_valve_mass_kg(
            intake_diameter_mm, intake_density_kg_m3
        )
        exhaust_mass = exhaust_count * estimated_valve_mass_kg(
            exhaust_diameter_mm, exhaust_density_kg_m3
        )
        yield ValveCandidate(
            intake_diameter_mm=intake_diameter_mm,
            exhaust_diameter_mm=exhaust_diameter_mm,
            intake_lift_mm=intake_lift_mm,
            exhaust_lift_mm=exhaust_lift_mm,
            seat_ring_radius_mm=ring_radius_mm,
            minimum_seat_bridge_mm=bridge,
            chamber_edge_margin_mm=edge_margin,
            intake_mean_effective_area_mm2=mean_effective_area_mm2(
                intake_count,
                intake_diameter_mm,
                intake_lift_mm,
                INTAKE_DISCHARGE_COEFFICIENT,
                samples,
            ),
            exhaust_mean_effective_area_mm2=mean_effective_area_mm2(
                exhaust_count,
                exhaust_diameter_mm,
                exhaust_lift_mm,
                EXHAUST_DISCHARGE_COEFFICIENT,
                samples,
            ),
            total_valve_mass_g=1000.0 * (intake_mass + exhaust_mass),
        )


def select_candidate(candidates: Iterable[ValveCandidate]) -> ValveCandidate:
    values = list(candidates)
    require(bool(values), "no_packaging_candidate_survived")
    return max(
        values,
        key=lambda candidate: (
            candidate.intake_mean_effective_area_mm2
            + 0.65 * candidate.exhaust_mean_effective_area_mm2
            - 0.05 * candidate.total_valve_mass_g,
            candidate.minimum_seat_bridge_mm,
            candidate.chamber_edge_margin_mm,
        ),
    )


def mass_flow_kg_s(area_mm2: float, density_kg_m3: float, pressure_drop_pa: float) -> float:
    return area_mm2 * 1.0e-6 * math.sqrt(2.0 * density_kg_m3 * pressure_drop_pa)


def valve_dynamic_screen(
    count: int,
    diameter_mm: float,
    lift_mm: float,
    density_kg_m3: float,
    speed_rpm: float,
    gas_differential_pa: float,
) -> dict[str, float]:
    mass_per_valve_kg = estimated_valve_mass_kg(diameter_mm, density_kg_m3)
    event_time_s = CAM_EVENT_DURATION_CRANK_DEG / (6.0 * speed_rpm)
    maximum_acceleration_m_s2 = (
        2.0 * math.pi**2 * (lift_mm / 1000.0) / event_time_s**2
    )
    gas_force_n = (
        gas_differential_pa * math.pi * (diameter_mm / 1000.0) ** 2 / 4.0
    )
    target_open_force_n = 1.25 * mass_per_valve_kg * maximum_acceleration_m_s2 + gas_force_n
    target_seat_force_n = 0.45 * target_open_force_n
    spring_rate_n_m = (target_open_force_n - target_seat_force_n) / (lift_mm / 1000.0)
    natural_frequency_hz = math.sqrt(spring_rate_n_m / mass_per_valve_kg) / (2.0 * math.pi)
    cam_frequency_hz = speed_rpm / 120.0
    return {
        "valve_count": count,
        "estimated_mass_per_valve_g": mass_per_valve_kg * 1000.0,
        "event_time_ms": event_time_s * 1000.0,
        "maximum_acceleration_m_s2": maximum_acceleration_m_s2,
        "gas_force_per_valve_n": gas_force_n,
        "target_open_force_per_spring_n": target_open_force_n,
        "target_seat_force_per_spring_n": target_seat_force_n,
        "implied_spring_rate_n_mm": spring_rate_n_m / 1000.0,
        "single_mass_natural_frequency_hz": natural_frequency_hz,
        "natural_to_cam_frequency_ratio": natural_frequency_hz / cam_frequency_hz,
    }


def pressure_and_thermal_screen(
    bore_mm: float,
    pressure_mpa: float,
    heat_flux_w_m2: float,
    deck_thickness_mm: float,
    intake_count: int,
    exhaust_count: int,
    intake_diameter_mm: float,
    exhaust_diameter_mm: float,
    minimum_bridge_mm: float,
    spark_plug_diameter_mm: float,
    material: dict[str, Any],
) -> dict[str, float]:
    bore_m = bore_mm / 1000.0
    radius_m = bore_m / 2.0
    thickness_m = deck_thickness_mm / 1000.0
    pressure_pa = pressure_mpa * 1.0e6
    flexural_rigidity = (
        YOUNGS_MODULUS_PA
        * thickness_m**3
        / (12.0 * (1.0 - POISSON_RATIO**2))
    )
    base_deflection_m = pressure_pa * radius_m**4 / (64.0 * flexural_rigidity)
    base_stress_pa = (
        (3.0 + POISSON_RATIO)
        / 8.0
        * pressure_pa
        * (radius_m / thickness_m) ** 2
    )
    bore_area_mm2 = math.pi * bore_mm**2 / 4.0
    opening_area_mm2 = (
        intake_count * math.pi * intake_diameter_mm**2 / 4.0
        + exhaust_count * math.pi * exhaust_diameter_mm**2 / 4.0
        + math.pi * spark_plug_diameter_mm**2 / 4.0
    )
    opening_fraction = opening_area_mm2 / bore_area_mm2
    ligament_factor = 1.0 / max(0.1, 1.0 - opening_fraction) ** 1.35
    bridge_factor = 1.0 + 0.08 * (2.0 / minimum_bridge_mm)
    stress_proxy_mpa = base_stress_pa * ligament_factor * bridge_factor / 1.0e6
    deflection_proxy_mm = base_deflection_m * ligament_factor * 1000.0
    yield_strength_mpa = float(material["room_temperature_yield_strength_mpa"])
    valve_perimeter_ratio = (
        intake_count * intake_diameter_mm + exhaust_count * exhaust_diameter_mm
    ) / bore_mm
    conduction_delta_k = (
        heat_flux_w_m2
        * thickness_m
        / float(material["screening_thermal_conductivity_w_mk"])
        * (1.0 + 0.12 * valve_perimeter_ratio)
    )
    return {
        "opening_area_fraction": opening_fraction,
        "ligament_penalty_factor": ligament_factor,
        "bridge_penalty_factor": bridge_factor,
        "pressure_stress_proxy_mpa": stress_proxy_mpa,
        "pressure_deflection_proxy_mm": deflection_proxy_mm,
        "room_temperature_yield_margin_proxy": yield_strength_mpa / stress_proxy_mpa,
        "one_dimensional_deck_temperature_rise_k": conduction_delta_k,
    }


def round_floats(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, list):
        return [round_floats(item) for item in value]
    if isinstance(value, dict):
        return {key: round_floats(item) for key, item in value.items()}
    return value


def build_study(contract_path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    require(contract.get("phase") == "F29", "contract_phase_must_be_f29")
    gates = contract.get("release_gates")
    require(
        isinstance(gates, dict) and gates and all(value is False for value in gates.values()),
        "release_gates_must_be_exact_false_booleans",
    )
    search = contract["architecture_search"]
    geometry = contract["geometry_hypotheses"]
    materials = contract["material_screening"]["head_candidates"]
    selected_material_id = contract["material_screening"]["screening_selection"]
    selected_material = next(
        (item for item in materials if item["id"] == selected_material_id), None
    )
    require(selected_material is not None, "selected_material_missing")
    valvetrain = contract["valvetrain_screening"]
    samples = int(search["sample_count"])
    variants = []

    for scenario in contract["scenarios"]:
        bore_mm = float(scenario["bore_mm"])
        for architecture in ("2v", "4v"):
            architecture_config = search[architecture]
            selected = select_candidate(
                iter_candidates(
                    architecture,
                    architecture_config,
                    bore_mm,
                    samples,
                    float(search["minimum_seat_bridge_mm"]),
                    float(search["minimum_chamber_edge_margin_mm"]),
                    float(valvetrain["intake_valve"]["density_kg_m3"]),
                    float(valvetrain["exhaust_valve"]["density_kg_m3"]),
                )
            )
            intake_count = int(architecture_config["intake_count"])
            exhaust_count = int(architecture_config["exhaust_count"])
            positions = valve_positions(architecture, selected.seat_ring_radius_mm)
            intake_peak_area = effective_area_mm2(
                intake_count,
                selected.intake_diameter_mm,
                selected.intake_lift_mm,
                INTAKE_DISCHARGE_COEFFICIENT,
            )
            exhaust_peak_area = effective_area_mm2(
                exhaust_count,
                selected.exhaust_diameter_mm,
                selected.exhaust_lift_mm,
                EXHAUST_DISCHARGE_COEFFICIENT,
            )
            material_screens = {
                material["id"]: pressure_and_thermal_screen(
                    bore_mm=bore_mm,
                    pressure_mpa=float(scenario["screening_peak_cylinder_pressure_mpa"]),
                    heat_flux_w_m2=float(scenario["screening_combustion_heat_flux_w_m2"]),
                    deck_thickness_mm=float(geometry["deck_thickness_mm"]),
                    intake_count=intake_count,
                    exhaust_count=exhaust_count,
                    intake_diameter_mm=selected.intake_diameter_mm,
                    exhaust_diameter_mm=selected.exhaust_diameter_mm,
                    minimum_bridge_mm=selected.minimum_seat_bridge_mm,
                    spark_plug_diameter_mm=float(geometry["spark_plug_bore_diameter_mm"]),
                    material=material,
                )
                for material in materials
            }
            variants.append(
                {
                    "id": f"{scenario['id']}_{architecture}",
                    "scenario_id": scenario["id"],
                    "architecture": architecture,
                    "bore_mm": bore_mm,
                    "stroke_mm": float(scenario["stroke_mm"]),
                    "intake_count": intake_count,
                    "exhaust_count": exhaust_count,
                    "total_valve_count": intake_count + exhaust_count,
                    "intake_diameter_mm": selected.intake_diameter_mm,
                    "exhaust_diameter_mm": selected.exhaust_diameter_mm,
                    "intake_maximum_lift_mm": selected.intake_lift_mm,
                    "exhaust_maximum_lift_mm": selected.exhaust_lift_mm,
                    "seat_ring_radius_mm": selected.seat_ring_radius_mm,
                    "valve_positions_xy_mm": positions,
                    "minimum_seat_bridge_mm": selected.minimum_seat_bridge_mm,
                    "chamber_edge_margin_mm": selected.chamber_edge_margin_mm,
                    "estimated_total_valve_mass_g": selected.total_valve_mass_g,
                    "flow_screen": {
                        "intake_mean_effective_area_mm2": selected.intake_mean_effective_area_mm2,
                        "exhaust_mean_effective_area_mm2": selected.exhaust_mean_effective_area_mm2,
                        "intake_peak_effective_area_mm2": intake_peak_area,
                        "exhaust_peak_effective_area_mm2": exhaust_peak_area,
                        "intake_reference_mass_flow_kg_s": mass_flow_kg_s(
                            intake_peak_area,
                            float(scenario["intake_reference_density_kg_m3"]),
                            float(scenario["flow_bench_pressure_drop_pa"]),
                        ),
                        "flow_model": "quasi_steady_fixed_pressure_drop_not_engine_volumetric_efficiency",
                    },
                    "valve_dynamics_screen": {
                        "intake": valve_dynamic_screen(
                            intake_count,
                            selected.intake_diameter_mm,
                            selected.intake_lift_mm,
                            float(valvetrain["intake_valve"]["density_kg_m3"]),
                            float(scenario["screening_speed_rpm"]),
                            INTAKE_GAS_DIFFERENTIAL_PA,
                        ),
                        "exhaust": valve_dynamic_screen(
                            exhaust_count,
                            selected.exhaust_diameter_mm,
                            selected.exhaust_lift_mm,
                            float(valvetrain["exhaust_valve"]["density_kg_m3"]),
                            float(scenario["screening_speed_rpm"]),
                            EXHAUST_GAS_DIFFERENTIAL_PA,
                        ),
                    },
                    "material_screens": material_screens,
                    "selected_material_for_screening": selected_material_id,
                    "cad_parameters": {
                        "head_height_mm": float(geometry["head_height_mm"]),
                        "outer_radius_mm": bore_mm / 2.0
                        + float(geometry["radial_wall_allowance_mm"]),
                        "deck_thickness_mm": float(geometry["deck_thickness_mm"]),
                        "chamber_depth_mm": float(geometry["combustion_chamber_depth_mm"]),
                        "fin_count": int(geometry["fin_count"]),
                        "fin_thickness_mm": float(geometry["fin_thickness_mm"]),
                        "fin_overhang_mm": float(geometry["fin_overhang_mm"]),
                        "fastener_hole_diameter_mm": float(geometry["fastener_hole_diameter_mm"]),
                        "spark_plug_bore_diameter_mm": float(geometry["spark_plug_bore_diameter_mm"]),
                        "port_to_valve_diameter_ratio": float(geometry["port_to_valve_diameter_ratio"]),
                    },
                }
            )

    comparisons = []
    for scenario in contract["scenarios"]:
        pair = {
            item["architecture"]: item
            for item in variants
            if item["scenario_id"] == scenario["id"]
        }
        flow_values = {
            architecture: item["flow_screen"]["intake_mean_effective_area_mm2"]
            + 0.65 * item["flow_screen"]["exhaust_mean_effective_area_mm2"]
            for architecture, item in pair.items()
        }
        dynamics_values = {
            architecture: 1.0
            / max(
                item["valve_dynamics_screen"]["intake"]["target_open_force_per_spring_n"],
                item["valve_dynamics_screen"]["exhaust"]["target_open_force_per_spring_n"],
            )
            for architecture, item in pair.items()
        }
        structural_values = {
            architecture: item["material_screens"][selected_material_id][
                "room_temperature_yield_margin_proxy"
            ]
            for architecture, item in pair.items()
        }
        thermal_values = {
            architecture: 1.0
            / item["material_screens"][selected_material_id][
                "one_dimensional_deck_temperature_rise_k"
            ]
            for architecture, item in pair.items()
        }

        def normalized(values: dict[str, float], architecture: str) -> float:
            return values[architecture] / max(values.values())

        scores = {}
        for architecture in ("2v", "4v"):
            scores[architecture] = (
                0.45 * normalized(flow_values, architecture)
                + 0.20 * normalized(dynamics_values, architecture)
                + 0.20 * normalized(structural_values, architecture)
                + 0.15 * normalized(thermal_values, architecture)
                - (0.03 if architecture == "4v" else 0.0)
            )
        lead = max(scores, key=scores.get)
        comparisons.append(
            {
                "scenario_id": scenario["id"],
                "screening_scores": scores,
                "screening_lead": lead,
                "four_valve_change_percent": {
                    "combined_mean_effective_area": 100.0
                    * (flow_values["4v"] / flow_values["2v"] - 1.0),
                    "estimated_total_valve_mass": 100.0
                    * (
                        pair["4v"]["estimated_total_valve_mass_g"]
                        / pair["2v"]["estimated_total_valve_mass_g"]
                        - 1.0
                    ),
                    "pressure_stress_proxy": 100.0
                    * (
                        pair["4v"]["material_screens"][selected_material_id][
                            "pressure_stress_proxy_mpa"
                        ]
                        / pair["2v"]["material_screens"][selected_material_id][
                            "pressure_stress_proxy_mpa"
                        ]
                        - 1.0
                    ),
                    "deck_temperature_rise_proxy": 100.0
                    * (
                        pair["4v"]["material_screens"][selected_material_id][
                            "one_dimensional_deck_temperature_rise_k"
                        ]
                        / pair["2v"]["material_screens"][selected_material_id][
                            "one_dimensional_deck_temperature_rise_k"
                        ]
                        - 1.0
                    ),
                },
                "decision_scope": "weighted_concept_screen_only_not_architecture_release",
            }
        )

    return round_floats(
        {
            "schema_version": "1.0.0",
            "phase": "F29",
            "status": "completed_analytical_concept_screen_not_validated_digital_twin",
            "contract": {
                "path": str(contract_path.relative_to(ROOT)),
                "sha256": sha256(contract_path),
            },
            "variant_count": len(variants),
            "variants": variants,
            "comparisons": comparisons,
            "material_screening_selection": selected_material_id,
            "model_limits": [
                "quasi_steady_flow_only_no_ports_or_combustion_cfd",
                "closed_form_plate_proxy_only_no_3d_nonlinear_thermomechanical_fea",
                "room_temperature_yield_only_no_hot_fatigue_or_creep",
                "one_dimensional_conduction_only_no_cooling_air_or_conjugate_heat_transfer",
                "sinusoidal_valve_motion_only_no_cam_profile_contact_or_surge_analysis",
                "no_measured_917_head_fitment_interfaces",
                "no_engine_efficiency_power_or_1600_hp_validation",
            ],
            "release_gates": contract["release_gates"],
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    contract_path = args.contract.resolve()
    output_path = args.output.resolve()
    contract = load_json(contract_path)
    report = build_study(contract_path, contract)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": report["status"], "output": str(output_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
