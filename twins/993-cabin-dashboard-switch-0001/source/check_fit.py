#!/usr/bin/env python3
"""Check the first 993 digital-twin interface from measured dimensions.

The report gives worst-case static margins. Linear margins are the nominal
difference minus the summed uncertainty of both dimensions. The corner margin
(H04) is the smallest all-round gap between two rounded-rectangle sections,
evaluated at the worst corner of the uncertainty box. The interface contract is
`../interface-contract.json`; the measurement inputs are defined by the frozen
plan in `../evidence/measurement-plan.md` and by `../measurement-plan-addendum.md`.

The calculation fails closed: a missing, duplicated, unit-mismatched,
non-finite, nonphysical or unsupported reading stops it before any report is
written. A passed report covers static geometry only. It never evaluates clip
insertion or retention force and never establishes a physical fit.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CANDIDATE_PART_ID = "993-INT-SWITCH-BLANK-0001"
CONTRACT_ID = "CONTRACT-993-DASH-SWITCH-FIT-0001"
MIN_SAMPLES = 3

REQUIRED = {
    "D01": "visible face width",
    "D02": "visible face height",
    "D05": "clip tab length",
    "D08": "insertion body width",
    "D09": "insertion body height",
    "D10": "smallest outer corner radius of the insertion body",
    "H01": "host opening width",
    "H02": "host opening height",
    "H03": "host panel thickness",
    "H04": "largest inner corner radius of the host opening",
    "H05": "free depth behind host panel",
}

# Supported measurement methods, from the plan's method column. Any other
# method, including a host value derived from the removed part, is refused.
METHODS = {
    "D01": {"direct"}, "D02": {"direct"}, "D05": {"direct"},
    "D08": {"direct"}, "D09": {"direct"}, "D10": {"gauge"},
    "H01": {"direct"}, "H02": {"direct"}, "H03": {"direct"},
    "H04": {"gauge"}, "H05": {"direct", "gauge"},
}

# A corner radius cannot exceed half the smaller side of its own feature.
RADII = {"D10": ("D08", "D09"), "H04": ("H01", "H02")}

METRICS = {
    "horizontal_clearance": ("H01", "D08"),
    "vertical_clearance": ("H02", "D09"),
    "horizontal_overlap": ("D01", "H01"),
    "vertical_overlap": ("D02", "H02"),
    "clip_reach": ("D05", "H03"),
    "rear_clearance": ("H05", "D05"),
}

CORNER_METRIC = "corner_insertion_clearance"
CORNER_INPUTS = {
    "container": {"width": "H01", "height": "H02", "corner_radius": "H04"},
    "contained": {"width": "D08", "height": "D09", "corner_radius": "D10"},
}

LINEAR_LIMITATIONS = [
    "Total difference across both sides; the lateral position of the part is not modelled.",
    "Uncertainties are treated as bounding half-widths and summed.",
]
METRIC_LIMITATIONS = {
    "horizontal_clearance": LINEAR_LIMITATIONS + ["Straight sides only; corners are evaluated by corner_insertion_clearance."],
    "vertical_clearance": LINEAR_LIMITATIONS + ["Straight sides only; corners are evaluated by corner_insertion_clearance."],
    "horizontal_overlap": LINEAR_LIMITATIONS + ["Whether the face covers the opening corners is not evaluated."],
    "vertical_overlap": LINEAR_LIMITATIONS + ["Whether the face covers the opening corners is not evaluated."],
    "clip_reach": LINEAR_LIMITATIONS + ["Static length only: tab deflection, engagement and force are not evaluated."],
    "rear_clearance": LINEAR_LIMITATIONS + ["Static length only: wiring and parts behind the panel are not modelled."],
    CORNER_METRIC: [
        "Per-side gap with the body centred, the best placement; a positive value does not guarantee the placement the clips impose.",
        "Assumes circular-arc corners tangent to straight sides, H04 the largest opening corner and D10 the smallest body corner; the record cannot prove this, the photographs must.",
        "Assumes H01, H02 and H04 share one section, D08, D09 and D10 share one section, and insertion along Z without tilt.",
    ],
}

NOT_EVALUATED = {
    "clip_insertion_force": "No measured force-displacement data of the tabs and no elastic tab model; static margins do not predict it.",
    "clip_retention_force": "No measured retention or extraction force.",
    "face_corner_coverage": "The face overlap metrics are linear only.",
    "insertion_path": "Tilted insertion, tab deflection and contact sequence are not modelled.",
    "flush_with_neighbouring_trim": "Not measured in the plan.",
    "physical_fit": "Only a fit in the real opening, compared with this report, can establish it.",
}


def _fail(message: str) -> None:
    raise SystemExit(message)


def _load_measurement_validator():
    path = ROOT / "scripts" / "validate_measurements.py"
    spec = importlib.util.spec_from_file_location("_dt01_validate_measurements", path)
    if spec is None or spec.loader is None:
        _fail(f"cannot load the measurement validator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _reject_constant(name: str) -> None:
    _fail(f"non-finite number {name} in the measurement record")


def _finite_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def check_values(readings: dict[str, dict]) -> None:
    """Refuse absent, unit-mismatched, non-finite or nonphysical readings."""
    missing = [identifier for identifier in REQUIRED if identifier not in readings]
    if missing:
        details = "\n".join(f"  {identifier}: {REQUIRED[identifier]}" for identifier in missing)
        _fail(f"missing measurements:\n{details}")
    for identifier in REQUIRED:
        reading = readings[identifier]
        if not isinstance(reading, dict):
            _fail(f"{identifier}: expected a reading object")
        if reading.get("unit") != "mm":
            _fail(f"{identifier}: expected mm, got {reading.get('unit')!r}")
        for field in ("value", "uncertainty"):
            if not _finite_number(reading.get(field)):
                _fail(f"{identifier}.{field}: expected a finite number")
        if reading["uncertainty"] <= 0:
            _fail(f"{identifier}.uncertainty: expected a value greater than zero")
        if identifier in RADII:
            if reading["value"] < 0:
                _fail(f"{identifier}: nonphysical negative corner radius")
        elif reading["value"] - reading["uncertainty"] <= 0:
            _fail(f"{identifier}: nonphysical length, value minus uncertainty is not positive")
    for radius_id, (width_id, height_id) in RADII.items():
        limit = min(readings[width_id]["value"], readings[height_id]["value"]) / 2
        if readings[radius_id]["value"] > limit:
            _fail(
                f"{radius_id}: nonphysical corner radius {readings[radius_id]['value']} mm exceeds half "
                f"the smaller side of {width_id} x {height_id} ({limit} mm)"
            )


def load_readings(path: Path) -> dict[str, dict]:
    if not path.is_file():
        _fail(f"measurement record not found: {path}")
    try:
        record = json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_constant)
    except json.JSONDecodeError as exc:
        _fail(f"{path}: invalid JSON: {exc}")
    if not isinstance(record, dict):
        _fail(f"{path}: expected a measurement record object")
    # A documented specification carries declared values, not readings taken on
    # the car: it never feeds a fit check (decision 0013).
    kind = record.get("record_kind", "physical_measurement")
    if kind != "physical_measurement":
        _fail(f"{path} is a {kind} record: declared values do not feed a fit check")
    errors = _load_measurement_validator().validate_measurement(record)
    if errors:
        _fail(f"{path} fails scripts/validate_measurements.py:\n" + "\n".join(f"  {error}" for error in errors))
    part_id = (record.get("subject") or {}).get("part_id")
    if part_id != CANDIDATE_PART_ID:
        _fail(f"{path}: subject.part_id is {part_id!r}, this twin checks {CANDIDATE_PART_ID}")

    readings: dict[str, dict] = {}
    for item in record.get("readings", []):
        identifier = item.get("dimension_id")
        if identifier in readings:
            _fail(f"{identifier}: contradictory duplicate readings")
        readings[identifier] = item
    check_values(readings)
    for identifier in REQUIRED:
        reading = readings[identifier]
        method = reading.get("method")
        if identifier.startswith("H") and method == "derived":
            _fail(f"{identifier}: host readings must be taken on the empty opening, not derived from the part")
        if method not in METHODS[identifier]:
            _fail(f"{identifier}: method {method!r} is not supported, expected one of {sorted(METHODS[identifier])}")
        samples = reading.get("samples")
        if not isinstance(samples, list) or len(samples) < MIN_SAMPLES:
            _fail(f"{identifier}: the measurement plan requires at least {MIN_SAMPLES} samples")
        if not all(_finite_number(sample) for sample in samples):
            _fail(f"{identifier}.samples: expected finite numbers")
    return readings


def rounded_rectangle_margin(container: tuple[float, float, float], contained: tuple[float, float, float]) -> tuple[float, str]:
    """Smallest all-round gap of a centred rounded rectangle inside another.

    Each argument is (width, height, corner radius). The result is the largest
    uniform offset of the contained section that stays inside the container,
    so it is negative on interference, with the feature that governs it.
    """
    width, height, radius = container
    inner_width, inner_height, inner_radius = contained
    for name, (w, h, r) in (("container", container), ("contained", contained)):
        if not (0 <= r <= min(w, h) / 2):
            raise ValueError(f"{name}: corner radius {r} outside [0, {min(w, h) / 2}]")
    c_x = (width - inner_width) / 2
    c_y = (height - inner_height) / 2
    delta = radius - inner_radius
    alpha = c_x - delta
    beta = c_y - delta
    if alpha < 0 and beta < 0:
        return delta - math.hypot(alpha, beta), "corner"
    return min(c_x, c_y), "side"


def corner_metric(readings: dict[str, dict]) -> dict:
    ids = CORNER_INPUTS
    value = {key: float(readings[key]["value"]) for key in REQUIRED}
    spread = {key: float(readings[key]["uncertainty"]) for key in REQUIRED}
    outer, inner = ids["container"], ids["contained"]

    def section(group: dict[str, str], source: dict[str, float]) -> tuple[float, float, float]:
        return source[group["width"]], source[group["height"]], source[group["corner_radius"]]

    nominal, nominal_governs = rounded_rectangle_margin(section(outer, value), section(inner, value))

    # Monotone in every input: the worst corner of the uncertainty box is the
    # exact worst case. Physical bounds cap the radii, and capping is recorded.
    worst = {
        outer["width"]: value[outer["width"]] - spread[outer["width"]],
        outer["height"]: value[outer["height"]] - spread[outer["height"]],
        inner["width"]: value[inner["width"]] + spread[inner["width"]],
        inner["height"]: value[inner["height"]] + spread[inner["height"]],
    }
    bounds_applied = []
    container_radius = value[outer["corner_radius"]] + spread[outer["corner_radius"]]
    cap = min(worst[outer["width"]], worst[outer["height"]]) / 2
    if container_radius > cap:
        container_radius = cap
        bounds_applied.append(f"{outer['corner_radius']} capped at half the smaller worst-case opening side")
    contained_radius = value[inner["corner_radius"]] - spread[inner["corner_radius"]]
    if contained_radius < 0:
        contained_radius = 0.0
        bounds_applied.append(f"{inner['corner_radius']} floored at zero, a sharp corner")
    worst[outer["corner_radius"]] = container_radius
    worst[inner["corner_radius"]] = contained_radius
    worst_case, worst_governs = rounded_rectangle_margin(section(outer, worst), section(inner, worst))
    return {
        "rule": "rounded_rectangle_containment",
        "basis": "per_side_centred",
        "container": dict(outer),
        "contained": dict(inner),
        "nominal_margin_mm": round(nominal, 6),
        "nominal_governed_by": nominal_governs,
        "worst_case_inputs_mm": {key: round(worst[key], 6) for key in sorted(worst)},
        "bounds_applied": bounds_applied,
        "uncertainty_effect_mm": round(nominal - worst_case, 6),
        "worst_case_margin_mm": round(worst_case, 6),
        "worst_case_governed_by": worst_governs,
        "passed": worst_case > 0,
        "limitations": list(METRIC_LIMITATIONS[CORNER_METRIC]),
    }


def calculate(readings: dict[str, dict], inputs: dict | None = None) -> dict:
    check_values(readings)
    metrics = {}
    for name, (positive_id, negative_id) in METRICS.items():
        positive = readings[positive_id]
        negative = readings[negative_id]
        nominal = float(positive["value"]) - float(negative["value"])
        combined_uncertainty = float(positive["uncertainty"]) + float(negative["uncertainty"])
        worst_case = nominal - combined_uncertainty
        metrics[name] = {
            "rule": "linear_difference",
            "basis": "total_across_both_sides",
            "positive_dimension": positive_id,
            "negative_dimension": negative_id,
            "nominal_margin_mm": round(nominal, 6),
            "combined_uncertainty_mm": round(combined_uncertainty, 6),
            "worst_case_margin_mm": round(worst_case, 6),
            "passed": worst_case > 0,
            "limitations": list(METRIC_LIMITATIONS[name]),
        }
    metrics[CORNER_METRIC] = corner_metric(readings)
    report = {
        "schema_version": "1.1.0",
        "twin_id": "TWIN-993-CABIN-DASH-SWITCH-0001",
        "contract_id": CONTRACT_ID,
        "method": "worst_case_static_geometry",
    }
    if inputs is not None:
        report["inputs"] = inputs
    report.update({
        "metrics": metrics,
        "passed": all(metric["passed"] for metric in metrics.values()),
        "passed_scope": "static geometric margins listed in metrics only",
        "physical_fit_status": "not_established",
        "not_evaluated": dict(NOT_EVALUATED),
        "limitations": [
            "A passed report is a digital check of static geometry, not a fit.",
            "Clip insertion and retention force are outside the pass and need measured data and a separate model.",
            "A physical fit test is still required.",
        ],
    })
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurements", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    readings = load_readings(args.measurements)
    record = json.loads(args.measurements.read_text(encoding="utf-8"))
    inputs = {
        "measurement_id": record["measurement_id"],
        "measurement_sha256": hashlib.sha256(args.measurements.read_bytes()).hexdigest(),
        "evidence_level": record["evidence"]["level"],
    }
    report = calculate(readings, inputs)
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
