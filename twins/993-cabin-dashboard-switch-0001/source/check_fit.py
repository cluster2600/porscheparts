#!/usr/bin/env python3
"""Check the first 993 digital-twin interface from measured dimensions.

The report uses worst-case margins: nominal margin minus the summed uncertainty
of both contributing dimensions. Missing measurements stop the calculation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED = {
    "D01": "visible face width",
    "D02": "visible face height",
    "D05": "clip tab length",
    "D08": "insertion body width",
    "D09": "insertion body height",
    "H01": "host opening width",
    "H02": "host opening height",
    "H03": "host panel thickness",
    "H05": "free depth behind host panel",
}

METRICS = {
    "horizontal_clearance": ("H01", "D08"),
    "vertical_clearance": ("H02", "D09"),
    "horizontal_overlap": ("D01", "H01"),
    "vertical_overlap": ("D02", "H02"),
    "clip_reach": ("D05", "H03"),
    "rear_clearance": ("H05", "D05"),
}


def load_readings(path: Path) -> dict[str, dict]:
    if not path.is_file():
        raise SystemExit(f"measurement record not found: {path}")
    record = json.loads(path.read_text(encoding="utf-8"))
    readings = {item.get("dimension_id"): item for item in record.get("readings", [])}
    missing = [identifier for identifier in REQUIRED if identifier not in readings]
    if missing:
        details = "\n".join(f"  {identifier}: {REQUIRED[identifier]}" for identifier in missing)
        raise SystemExit(f"missing measurements:\n{details}")
    for identifier in REQUIRED:
        reading = readings[identifier]
        if reading.get("unit") != "mm":
            raise SystemExit(f"{identifier}: expected mm")
        for field in ("value", "uncertainty"):
            value = reading.get(field)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise SystemExit(f"{identifier}.{field}: expected a number")
        if reading["uncertainty"] < 0:
            raise SystemExit(f"{identifier}.uncertainty: expected zero or greater")
    return readings


def calculate(readings: dict[str, dict]) -> dict:
    metrics = {}
    for name, (positive_id, negative_id) in METRICS.items():
        positive = readings[positive_id]
        negative = readings[negative_id]
        nominal = float(positive["value"]) - float(negative["value"])
        combined_uncertainty = float(positive["uncertainty"]) + float(negative["uncertainty"])
        worst_case = nominal - combined_uncertainty
        metrics[name] = {
            "positive_dimension": positive_id,
            "negative_dimension": negative_id,
            "nominal_margin_mm": round(nominal, 6),
            "combined_uncertainty_mm": round(combined_uncertainty, 6),
            "worst_case_margin_mm": round(worst_case, 6),
            "passed": worst_case > 0,
        }
    return {
        "schema_version": "1.0.0",
        "twin_id": "TWIN-993-CABIN-DASH-SWITCH-0001",
        "method": "worst_case_linear_stack",
        "metrics": metrics,
        "passed": all(metric["passed"] for metric in metrics.values()),
        "limitations": [
            "Positive static margins do not predict clip insertion force.",
            "Corner-radius compatibility H04 is not yet computed.",
            "A physical fit test is still required.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurements", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = calculate(load_readings(args.measurements))
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(payload, end="")
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

