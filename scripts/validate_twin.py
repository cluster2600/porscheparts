#!/usr/bin/env python3
"""Validate the checked-in digital-twin reference envelope."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "twin" / "993" / "reference-envelope.json"
MEASUREMENTS = ROOT / "catalog" / "measurements" / "MEAS-MANUAL-993-ALL.json"
SOURCE_ID_PATTERN = re.compile(r"^SRC-[A-Z0-9][A-Z0-9._-]{2,63}$")


def validate(payload: Any, measurements: dict[str, dict[str, Any]]) -> list[str]:
    if not isinstance(payload, dict):
        return ["root: expected an object"]
    errors: list[str] = []
    required = (
        "schema_version",
        "twin_id",
        "status",
        "variant",
        "units",
        "coordinate_system",
        "source",
        "parameters",
        "geometry",
        "assumptions",
        "validation",
    )
    for field in required:
        if field not in payload:
            errors.append(f"root: missing {field}")
    if payload.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    if not isinstance(payload.get("twin_id"), str) or not payload["twin_id"].startswith("TWIN-"):
        errors.append("twin_id: expected a TWIN- identifier")
    if payload.get("status") != "reference_envelope":
        errors.append("status: expected reference_envelope")
    if payload.get("variant") != "USA":
        errors.append("variant: expected USA for the current sourced profile")
    if payload.get("units") != "mm":
        errors.append("units: expected mm")

    source = payload.get("source")
    source_id = None
    if not isinstance(source, dict):
        errors.append("source: expected an object")
    else:
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not SOURCE_ID_PATTERN.fullmatch(source_id):
            errors.append("source.source_id: expected a SRC- identifier")
        if source.get("measurement_record") != "catalog/measurements/MEAS-MANUAL-993-ALL.json":
            errors.append("source.measurement_record: unexpected registry path")

    parameters = payload.get("parameters")
    expected_parameters = {
        "length_mm",
        "width_mm",
        "height_mm",
        "wheelbase_mm",
        "front_track_mm",
        "rear_track_mm",
        "ground_clearance_mm",
    }
    if not isinstance(parameters, dict) or set(parameters) != expected_parameters:
        errors.append("parameters: expected the seven sourced envelope dimensions")
    else:
        seen_sources: set[str] = set()
        for name, parameter in parameters.items():
            label = f"parameters.{name}"
            if not isinstance(parameter, dict):
                errors.append(f"{label}: expected an object")
                continue
            value = parameter.get("value_mm")
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                errors.append(f"{label}.value_mm: expected a positive number")
            source_measurement_id = parameter.get("source_measurement_id")
            if not isinstance(source_measurement_id, str) or source_measurement_id in seen_sources:
                errors.append(f"{label}.source_measurement_id: missing or duplicate")
            else:
                seen_sources.add(source_measurement_id)
                row = measurements.get(source_measurement_id)
                if row is None:
                    errors.append(f"{label}.source_measurement_id: not found in measurement registry")
                elif row.get("source_id") != source_id:
                    errors.append(f"{label}.source_measurement_id: source mismatch")

    geometry = payload.get("geometry")
    if not isinstance(geometry, dict):
        errors.append("geometry: expected an object")
    else:
        master_file = geometry.get("master_file")
        if not isinstance(master_file, str) or not (ROOT / master_file).is_file():
            errors.append("geometry.master_file: referenced source file does not exist")
        if geometry.get("accuracy_mm") is not None:
            errors.append("geometry.accuracy_mm: reference envelope must not claim measured accuracy")
        if geometry.get("derived_files") != []:
            errors.append("geometry.derived_files: no derived mesh is checked in yet")

    validation = payload.get("validation")
    if (
        not isinstance(validation, dict)
        or validation.get("status") != "reference_only"
        or validation.get("vehicle_tested") is not False
        or validation.get("fitment_claim") is not False
    ):
        errors.append("validation: reference-only limits are required")
    return errors


def main() -> int:
    try:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        measurement_payload = json.loads(MEASUREMENTS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL twin: {exc}")
        return 1
    rows = measurement_payload.get("declared_values", [])
    measurements = {row.get("value_id"): row for row in rows if isinstance(row, dict)}
    errors = validate(payload, measurements)
    if errors:
        print("FAIL twin/993/reference-envelope.json")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK   twin/993/reference-envelope.json (reference envelope, 7 sourced dimensions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
