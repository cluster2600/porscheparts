#!/usr/bin/env python3
"""Compare two traceable scan dimensions without approving a physical part."""
import argparse
import json
import math
from pathlib import Path
import re


def _finite_number(value, name, minimum=0.0, strict=False):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{name} must be a number")
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(f"{name} is outside its permitted range") from error
    if not math.isfinite(result) or result < minimum or (strict and result == minimum):
        raise ValueError(f"{name} is outside its permitted range")
    return result


def _dimension(record):
    if not isinstance(record, dict):
        raise ValueError("each dimension must be an object")
    for name in ("feature", "provenance"):
        if not isinstance(record.get(name), str) or not record[name].strip():
            raise ValueError(f"dimension requires a nonempty {name}")
    source = _finite_number(record.get("source_length"), "source_length", strict=True)
    source_error = _finite_number(record.get("source_uncertainty"), "source_uncertainty")
    physical = _finite_number(record.get("measured_mm"), "measured_mm", strict=True)
    physical_error = _finite_number(record.get("measured_uncertainty_mm"), "measured_uncertainty_mm")
    if source_error >= source or physical_error >= physical:
        raise ValueError("uncertainty must be smaller than its dimension")
    direction = record.get("direction")
    if not isinstance(direction, list) or len(direction) != 3:
        raise ValueError("direction must contain three numbers")
    if any(isinstance(x, bool) or not isinstance(x, (int, float))
           or not math.isfinite(x) for x in direction):
        raise ValueError("direction components must be finite numbers")
    v = [float(x) for x in direction]
    norm = math.sqrt(sum(x * x for x in v))
    if not math.isfinite(norm) or norm == 0:
        raise ValueError("direction must be nonzero")
    scale = physical / source
    interval = [(physical - physical_error) / (source + source_error),
                (physical + physical_error) / (source - source_error)]
    if (not math.isfinite(scale) or scale <= 0 or not math.isfinite(1 / scale)
            or not all(math.isfinite(x) and x > 0 for x in interval)):
        raise ValueError("scale and interval must be finite and positive")
    return {"feature": record["feature"], "provenance": record["provenance"],
            "direction": [x / norm for x in v], "nominal_mm_per_source_unit": scale,
            "interval_mm_per_source_unit": interval}


def assess(data):
    if not isinstance(data, dict) or data.get("scan_id") not in ("rotor", "drive"):
        raise ValueError("scan_id must be rotor or drive")
    digest = data.get("scan_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("scan_sha256 must be a lowercase SHA-256")
    dims = data.get("dimensions")
    if not isinstance(dims, list) or len(dims) != 2:
        raise ValueError("exactly two dimensions are required")
    a, b = map(_dimension, dims)
    if a["feature"].strip().casefold() == b["feature"].strip().casefold():
        raise ValueError("dimensions must refer to distinct features")
    cosine = max(-1.0, min(1.0, sum(x * y for x, y in zip(a["direction"], b["direction"]))))
    angle = math.degrees(math.acos(abs(cosine)))
    if angle < 1e-4:
        raise ValueError("dimension directions must not be parallel")
    low = max(a["interval_mm_per_source_unit"][0], b["interval_mm_per_source_unit"][0])
    high = min(a["interval_mm_per_source_unit"][1], b["interval_mm_per_source_unit"][1])
    consistent = low <= high
    scale = a["nominal_mm_per_source_unit"]
    return {"status": "conditional_dimension_consistency_not_calibration_approval",
            "scan_id": data["scan_id"], "scan_sha256": digest, "dimensions": [a, b],
            "acute_direction_angle_degrees": angle,
            "scale_intervals_overlap": consistent,
            "common_interval_mm_per_source_unit": [low, high] if consistent else None,
            "first_dimension_nominal_mm_per_source_unit": scale,
            "first_dimension_origin_scale_source_to_mm": [[scale, 0, 0, 0], [0, scale, 0, 0],
                                                          [0, 0, scale, 0], [0, 0, 0, 1]],
            "first_dimension_origin_scale_mm_to_source": [[1 / scale, 0, 0, 0], [0, 1 / scale, 0, 0],
                                                          [0, 0, 1 / scale, 0], [0, 0, 0, 1]],
            "scale_verified": False, "physical_registration_verified": False,
            "manufacturing_authorized": False,
            "limitations": ["Inputs are user-supplied and not independently authenticated.",
                            "Interval overlap does not prove scan scale, distortion, or registration.",
                            "Transforms only scale about the source origin; they do not assemble parts."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path, help="new JSON file; never overwrites")
    args = parser.parse_args()
    result = assess(json.loads(args.input.read_text()))
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
