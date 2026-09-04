#!/usr/bin/env python3
"""Evaluate F42 AdditiveFOAM metrics without hiding temperature saturation.

The input is a JSON array of post-processed case metrics. Peak temperatures at
or above 3299 K are treated as right-censored by the unchanged 3300 K limiter;
such a DOE cannot be ranked or declared converged.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from prepare_additivefoam_f42_doe import build_matrix, load_json, validate_spec


CAP_TOLERANCE_K = 1.0


def relative_difference(reference: float, candidate: float) -> float:
    scale = max(abs(reference), abs(candidate))
    if scale == 0.0:
        return 0.0
    return abs(reference - candidate) / scale


def validate_measurement(item: dict, temperature_limit_k: float) -> dict:
    required_numbers = (
        "temperature_max_k",
        "temperature_p99_k",
        "molten_volume_mm3",
        "melt_pool_length_mm",
        "melt_pool_width_mm",
        "melt_pool_depth_mm",
        "maximum_courant_number",
    )
    missing = [name for name in required_numbers if name not in item]
    if missing:
        raise ValueError(f"metriques_absentes:{item.get('case_id')}:{','.join(missing)}")
    values = [float(item[name]) for name in required_numbers]
    numerically_finite = all(math.isfinite(value) for value in values)
    cap_hit = float(item["temperature_max_k"]) >= temperature_limit_k - CAP_TOLERANCE_K
    cap_overshoot = float(item["temperature_max_k"]) > temperature_limit_k + CAP_TOLERANCE_K
    physically_ordered = (
        float(item["temperature_max_k"]) >= float(item["temperature_p99_k"]) > 0.0
        and all(float(item[name]) >= 0.0 for name in required_numbers[2:])
    )
    solver_valid = (
        item.get("completed") is True
        and item.get("finite") is True
        and numerically_finite
        and physically_ordered
        and item.get("fatal_error", False) is False
        and 0.0 <= float(item["maximum_courant_number"]) <= 0.5
        and not cap_overshoot
    )
    return {
        **item,
        "numerically_finite": numerically_finite,
        "metrics_physically_ordered": physically_ordered,
        "solver_temperature_cap_hit": cap_hit,
        "temperature_limit_overshoot": cap_overshoot,
        "solver_valid_before_cap_gate": solver_valid,
        "temperature_observation": "right_censored" if cap_hit else "observed_below_limit",
    }


def compare_nominal_to_fine(nominal: dict, fine: dict, acceptance: dict) -> dict:
    differences = {
        "temperature_p99": relative_difference(
            float(nominal["temperature_p99_k"]), float(fine["temperature_p99_k"])
        ),
        "molten_volume": relative_difference(
            float(nominal["molten_volume_mm3"]), float(fine["molten_volume_mm3"])
        ),
        "melt_pool_length": relative_difference(
            float(nominal["melt_pool_length_mm"]), float(fine["melt_pool_length_mm"])
        ),
        "melt_pool_width": relative_difference(
            float(nominal["melt_pool_width_mm"]), float(fine["melt_pool_width_mm"])
        ),
        "melt_pool_depth": relative_difference(
            float(nominal["melt_pool_depth_mm"]), float(fine["melt_pool_depth_mm"])
        ),
    }
    cap_free = not nominal["solver_temperature_cap_hit"] and not fine["solver_temperature_cap_hit"]
    passes = (
        nominal["solver_valid_before_cap_gate"]
        and fine["solver_valid_before_cap_gate"]
        and cap_free
        and differences["temperature_p99"] <= acceptance["maximum_relative_difference_temperature_p99"]
        and differences["molten_volume"] <= acceptance["maximum_relative_difference_molten_volume"]
        and all(
            differences[name] <= acceptance["maximum_relative_difference_melt_pool_dimensions"]
            for name in ("melt_pool_length", "melt_pool_width", "melt_pool_depth")
        )
    )
    return {
        "nominal_to_fine_relative_differences": differences,
        "temperature_cap_free": cap_free,
        "passes": passes,
    }


def evaluate(spec: dict, measurements: list[dict]) -> dict:
    matrix = build_matrix(spec)
    matrix_ids = {row["case_id"] for row in matrix}
    temperature_limit = float(spec["additivefoam"]["temperature_limit_k"])
    checked = [validate_measurement(item, temperature_limit) for item in measurements]
    keys = [(item.get("case_id"), item.get("resolution")) for item in checked]
    if len(keys) != len(set(keys)):
        raise ValueError("mesures_Doe_dupliquees")
    unknown = sorted({str(item.get("case_id")) for item in checked if item.get("case_id") not in matrix_ids})
    if unknown:
        raise ValueError(f"cas_Doe_inconnus:{','.join(unknown)}")

    nominal = {item["case_id"]: item for item in checked if item.get("resolution") == "nominal"}
    screening_complete = set(nominal) == matrix_ids
    all_cap_free = screening_complete and all(
        not item["solver_temperature_cap_hit"] for item in nominal.values()
    )
    all_solver_valid = screening_complete and all(
        item["solver_valid_before_cap_gate"] for item in nominal.values()
    )

    convergence = {}
    acceptance = spec["resolution_study"]["acceptance"]
    by_key = {(item["case_id"], item.get("resolution")): item for item in checked}
    all_three_levels_present = True
    for selected_id in spec["resolution_study"]["case_ids"]:
        levels = {
            resolution: by_key.get((selected_id, resolution))
            for resolution in ("coarse", "nominal", "fine")
        }
        present = all(levels.values())
        all_three_levels_present = all_three_levels_present and present
        convergence[selected_id] = {
            "all_three_levels_present": present,
            "nominal_to_fine": compare_nominal_to_fine(levels["nominal"], levels["fine"], acceptance)
            if present
            else None,
        }
    convergence_complete = all_three_levels_present and all(
        value["nominal_to_fine"]["passes"] for value in convergence.values()
    )
    cap_count = sum(item["solver_temperature_cap_hit"] for item in checked)

    gates = {
        "all_27_screening_cases_present": screening_complete,
        "all_screening_solver_runs_valid_before_cap_gate": all_solver_valid,
        "temperature_cap_free": all_cap_free,
        "all_three_resolution_levels_present": all_three_levels_present,
        "resolution_convergence_complete": convergence_complete,
        "doe_response_ranking_permitted": all_solver_valid and all_cap_free and convergence_complete,
        "support_geometry_generated": False,
        "machine_build_file_generated": False,
        "supplier_parameter_card_qualified": False,
        "physical_coupon_qualified": False,
        "metal_print_authorized": False,
        "engine_start_authorized": False,
    }
    return {
        "schema_version": "1.0.0",
        "phase": "F42",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "classification": "postprocessed_additivefoam_doe_not_machine_qualification",
        "temperature_limit_policy": {
            "temperature_limit_k": temperature_limit,
            "solver_dictionary_must_remain_unchanged": True,
            "cap_detection_threshold_k": temperature_limit - CAP_TOLERANCE_K,
            "cap_hit_count": cap_count,
            "interpretation": "right_censored_invalid_for_peak_ranking_and_convergence",
        },
        "measurements": checked,
        "convergence": convergence,
        "gates": gates,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, default=Path(__file__).resolve().parents[1] / "f42-lpbf-doe.json")
    parser.add_argument("--measurements", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    spec = load_json(args.spec)
    validate_spec(spec, args.spec)
    payload = load_json(args.measurements)
    measurements = payload["measurements"] if isinstance(payload, dict) else payload
    if not isinstance(measurements, list):
        raise SystemExit("measurements_doit_etre_une_liste")
    report = evaluate(spec, measurements)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "gates": report["gates"]}, sort_keys=True))
    return 0 if report["gates"]["doe_response_ranking_permitted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
