#!/usr/bin/env python3
"""Compare two independent F42 AdditiveFOAM executions fail-closed.

This is a hardware/runtime reproducibility screen, not a second physical model
and not a machine qualification.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path


METRIC_TOLERANCES = {
    "temperature_max_k": {"relative": 0.005, "absolute": 1.0},
    "temperature_p99_k": {"relative": 0.005, "absolute": 1.0},
    "molten_volume_mm3": {"relative": 0.01, "absolute": 1.0e-5},
    "melt_pool_length_mm": {"relative": 0.01, "absolute": 1.0e-4},
    "melt_pool_width_mm": {"relative": 0.01, "absolute": 1.0e-4},
    "melt_pool_depth_mm": {"relative": 0.01, "absolute": 1.0e-4},
    "maximum_courant_number": {"relative": 0.01, "absolute": 1.0e-5},
}


def load_measurements(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    measurements = payload.get("measurements") if isinstance(payload, dict) else payload
    if not isinstance(measurements, list):
        raise ValueError(f"mesures_invalides:{path}")
    return measurements


def keyed(measurements: list[dict], label: str) -> dict[tuple[str, str], dict]:
    result = {}
    for item in measurements:
        key = (str(item.get("case_id")), str(item.get("resolution")))
        if key in result:
            raise ValueError(f"mesure_dupliquee:{label}:{key[0]}:{key[1]}")
        result[key] = item
    return result


def metric_comparison(left: float, right: float, tolerance: dict) -> dict:
    finite = math.isfinite(left) and math.isfinite(right)
    absolute = abs(left - right) if finite else math.inf
    scale = max(abs(left), abs(right)) if finite else 0.0
    relative = absolute / scale if scale else absolute
    passes = finite and (
        absolute <= float(tolerance["absolute"])
        or relative <= float(tolerance["relative"])
    )
    return {
        "left": left,
        "right": right,
        "absolute_difference": absolute,
        "relative_difference": relative,
        "passes": passes,
    }


def compare(left: list[dict], right: list[dict], left_label: str, right_label: str) -> dict:
    left_by_key = keyed(left, left_label)
    right_by_key = keyed(right, right_label)
    same_case_set = set(left_by_key) == set(right_by_key)
    comparisons = []
    for key in sorted(set(left_by_key) | set(right_by_key)):
        lhs = left_by_key.get(key)
        rhs = right_by_key.get(key)
        if lhs is None or rhs is None:
            comparisons.append(
                {
                    "case_id": key[0],
                    "resolution": key[1],
                    "present_on_both_hosts": False,
                    "passes": False,
                }
            )
            continue
        run_state_matches = all(
            lhs.get(name) == rhs.get(name)
            for name in ("completed", "fatal_error", "finite")
        )
        metrics = {}
        for name, tolerance in METRIC_TOLERANCES.items():
            try:
                metrics[name] = metric_comparison(float(lhs[name]), float(rhs[name]), tolerance)
            except (KeyError, TypeError, ValueError):
                metrics[name] = {
                    "left": lhs.get(name),
                    "right": rhs.get(name),
                    "passes": False,
                    "error": "metrique_absente_ou_non_numerique",
                }
        cap_class_matches = (
            float(lhs.get("temperature_max_k", math.inf)) >= 3299.0
        ) == (
            float(rhs.get("temperature_max_k", math.inf)) >= 3299.0
        )
        passes = (
            run_state_matches
            and lhs.get("completed") is True
            and lhs.get("fatal_error") is False
            and lhs.get("finite") is True
            and cap_class_matches
            and all(value["passes"] for value in metrics.values())
        )
        comparisons.append(
            {
                "case_id": key[0],
                "resolution": key[1],
                "present_on_both_hosts": True,
                "run_state_matches": run_state_matches,
                "temperature_cap_classification_matches": cap_class_matches,
                "metrics": metrics,
                "passes": passes,
            }
        )
    reproducible = same_case_set and len(comparisons) == 33 and all(
        item["passes"] for item in comparisons
    )
    return {
        "schema_version": "1.0.0",
        "phase": "F42.2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "classification": "cross_host_runtime_reproducibility_not_second_physical_method",
        "hosts": {"left": left_label, "right": right_label},
        "metric_tolerances": METRIC_TOLERANCES,
        "case_set_identical": same_case_set,
        "comparison_count": len(comparisons),
        "comparisons": comparisons,
        "gates": {
            "all_33_runs_reproduced_within_tolerance": reproducible,
            "second_independent_physics_method_completed": False,
            "supplier_parameter_card_qualified": False,
            "physical_coupon_qualified": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--left", type=Path, required=True)
    parser.add_argument("--right", type=Path, required=True)
    parser.add_argument("--left-label", default="host-a")
    parser.add_argument("--right-label", default="host-b")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = compare(
        load_measurements(args.left),
        load_measurements(args.right),
        args.left_label,
        args.right_label,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "gates": report["gates"]}, sort_keys=True))
    return 0 if report["gates"]["all_33_runs_reproduced_within_tolerance"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
