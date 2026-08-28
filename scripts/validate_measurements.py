#!/usr/bin/env python3
"""Validate measurement records without external dependencies.

The checks here exist because a measurement is only evidence when the instrument,
the spread of the readings and the claimed uncertainty agree with each other. A
value typed by hand that does not match its own samples, or an uncertainty finer
than the instrument can resolve, is a transcription error waiting to become a
dimension of record.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from statistics import fmean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "catalog" / "measurements"
MEASUREMENT_ID_PATTERN = re.compile(r"^MEAS-[A-Z0-9][A-Z0-9._-]{2,63}$")
PART_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,63}$")
DIMENSION_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{1,15}$")

INSTRUMENT_TYPES = {"caliper", "micrometer", "height_gauge", "dial_indicator", "gauge_pin", "thread_gauge", "scale_bar", "camera", "scanner", "other"}
INTERFACES = {"manual", "serial", "usb", "network"}
CALIBRATION_STATUSES = {"calibrated", "checked_against_reference", "unknown"}
METHODS = {"direct", "indirect", "gauge", "photogrammetry", "scan", "derived"}
UNITS = {"mm", "deg", "kg", "N", "Nm"}
UNCERTAINTY_BASES = {"repeatability", "instrument_resolution", "combined", "estimated"}
CAPTURE_MODES = {"manual_entry", "instrument_stream"}
EVIDENCE_LEVELS = {"A", "C", "E", "unrated"}

REQUIRED_KEYS = {"schema_version", "measurement_id", "subject", "session", "datum", "instruments", "readings", "evidence", "notes"}

# Fallback tolerance when an instrument declares no resolution, in record units.
DEFAULT_VALUE_TOLERANCE = 0.005


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _date(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _validate_instruments(record: dict, errors: list[str]) -> dict[str, dict]:
    instruments = record.get("instruments")
    known: dict[str, dict] = {}
    if not isinstance(instruments, list) or not instruments:
        errors.append("instruments: expected at least one instrument")
        return known

    for index, instrument in enumerate(instruments):
        label = f"instruments[{index}]"
        if not isinstance(instrument, dict):
            errors.append(f"{label}: expected an object")
            continue
        identifier = instrument.get("instrument_id")
        if not _text(identifier):
            errors.append(f"{label}.instrument_id: expected a non-empty string")
        elif identifier in known:
            errors.append(f"{label}.instrument_id: duplicate identifier {identifier}")
        else:
            known[identifier] = instrument

        if instrument.get("type") not in INSTRUMENT_TYPES:
            errors.append(f"{label}.type: expected one of {sorted(INSTRUMENT_TYPES)}")
        if not _text(instrument.get("model")):
            errors.append(f"{label}.model: expected a non-empty string")
        if instrument.get("interface") not in INTERFACES:
            errors.append(f"{label}.interface: expected one of {sorted(INTERFACES)}")

        resolution = instrument.get("resolution_mm")
        if resolution is not None and (not _number(resolution) or resolution <= 0):
            errors.append(f"{label}.resolution_mm: expected null or a positive number")

        calibration = instrument.get("calibration")
        if not isinstance(calibration, dict):
            errors.append(f"{label}.calibration: expected an object")
            continue
        status = calibration.get("status")
        if status not in CALIBRATION_STATUSES:
            errors.append(f"{label}.calibration.status: expected one of {sorted(CALIBRATION_STATUSES)}")
        if not _date(calibration.get("checked_on")):
            errors.append(f"{label}.calibration.checked_on: expected null or YYYY-MM-DD")
        if status == "calibrated" and calibration.get("checked_on") is None:
            errors.append(f"{label}.calibration.checked_on: required when the instrument is declared calibrated")

    return known


def _validate_reading(reading: Any, label: str, instruments: dict[str, dict], errors: list[str]) -> None:
    if not isinstance(reading, dict):
        errors.append(f"{label}: expected an object")
        return

    identifier = reading.get("dimension_id")
    if not isinstance(identifier, str) or not DIMENSION_ID_PATTERN.fullmatch(identifier):
        errors.append(f"{label}.dimension_id: expected an uppercase identifier such as D01")

    if not _text(reading.get("description")):
        errors.append(f"{label}.description: expected a non-empty string")
    if reading.get("method") not in METHODS:
        errors.append(f"{label}.method: expected one of {sorted(METHODS)}")
    if reading.get("unit") not in UNITS:
        errors.append(f"{label}.unit: expected one of {sorted(UNITS)}")
    if reading.get("uncertainty_basis") not in UNCERTAINTY_BASES:
        errors.append(f"{label}.uncertainty_basis: expected one of {sorted(UNCERTAINTY_BASES)}")

    capture_mode = reading.get("capture_mode")
    if capture_mode not in CAPTURE_MODES:
        errors.append(f"{label}.capture_mode: expected one of {sorted(CAPTURE_MODES)}")

    instrument_id = reading.get("instrument_id")
    instrument = instruments.get(instrument_id) if isinstance(instrument_id, str) else None
    if instrument is None:
        errors.append(f"{label}.instrument_id: no instrument declares {instrument_id!r}")

    captured_at = reading.get("captured_at")
    if captured_at is not None:
        if not isinstance(captured_at, str):
            errors.append(f"{label}.captured_at: expected null or an ISO 8601 timestamp")
        else:
            try:
                datetime.fromisoformat(captured_at)
            except ValueError:
                errors.append(f"{label}.captured_at: expected null or an ISO 8601 timestamp")

    # A reading claimed to come off an instrument must carry the moment it was
    # taken and must come from an instrument that can actually stream.
    if capture_mode == "instrument_stream":
        if captured_at is None:
            errors.append(f"{label}.captured_at: required when capture_mode is instrument_stream")
        if instrument is not None and instrument.get("interface") == "manual":
            errors.append(f"{label}.capture_mode: instrument {instrument_id} has a manual interface")

    samples = reading.get("samples")
    if not isinstance(samples, list) or not samples or not all(_number(value) for value in samples):
        errors.append(f"{label}.samples: expected a non-empty array of numbers")
        return

    value = reading.get("value")
    if not _number(value):
        errors.append(f"{label}.value: expected a number")
        return

    resolution = instrument.get("resolution_mm") if instrument else None
    tolerance = resolution / 2 if _number(resolution) else DEFAULT_VALUE_TOLERANCE
    mean = fmean(samples)
    if abs(value - mean) > tolerance:
        errors.append(
            f"{label}.value: {value} does not match the mean of its samples "
            f"({mean:.4f}) within {tolerance}"
        )

    uncertainty = reading.get("uncertainty")
    if not _number(uncertainty):
        errors.append(f"{label}.uncertainty: expected a number")
        return
    if uncertainty <= 0:
        errors.append(f"{label}.uncertainty: expected a value greater than zero")
    # An uncertainty finer than half the instrument resolution claims a precision
    # the device cannot deliver.
    if _number(resolution) and reading.get("unit") == "mm" and uncertainty < resolution / 2:
        errors.append(
            f"{label}.uncertainty: {uncertainty} is finer than half the instrument "
            f"resolution ({resolution / 2})"
        )


def validate_measurement(record: Any) -> list[str]:
    if not isinstance(record, dict):
        return ["root: expected an object"]
    errors: list[str] = []

    missing = REQUIRED_KEYS - record.keys()
    extra = record.keys() - REQUIRED_KEYS
    if missing:
        errors.append(f"root: missing fields: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"root: unknown fields: {', '.join(sorted(extra))}")

    if record.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    identifier = record.get("measurement_id")
    if not isinstance(identifier, str) or not MEASUREMENT_ID_PATTERN.fullmatch(identifier):
        errors.append("measurement_id: expected MEAS- followed by an uppercase stable identifier")

    subject = record.get("subject")
    if not isinstance(subject, dict):
        errors.append("subject: expected an object")
    else:
        part_id = subject.get("part_id")
        if part_id is not None and (not isinstance(part_id, str) or not PART_ID_PATTERN.fullmatch(part_id)):
            errors.append("subject.part_id: expected null or a catalogue part identifier")
        for field in ("variant", "description"):
            if not _text(subject.get(field)):
                errors.append(f"subject.{field}: expected a non-empty string")
        if not isinstance(subject.get("part_reference"), str):
            errors.append("subject.part_reference: expected a string")

    session = record.get("session")
    if not isinstance(session, dict):
        errors.append("session: expected an object")
    else:
        performed_on = session.get("performed_on")
        if not _date(performed_on) or performed_on is None:
            errors.append("session.performed_on: expected YYYY-MM-DD")
        elif date.fromisoformat(performed_on) > date.today():
            errors.append("session.performed_on: date is in the future")
        if not _text(session.get("operator_role")):
            errors.append("session.operator_role: expected a role, not a personal name")
        temperature = session.get("ambient_temperature_c")
        if temperature is not None and not _number(temperature):
            errors.append("session.ambient_temperature_c: expected null or a number")

    datum = record.get("datum")
    if not isinstance(datum, dict):
        errors.append("datum: expected an object")
    else:
        for field in ("origin", "axes"):
            if not _text(datum.get(field)):
                errors.append(f"datum.{field}: expected a non-empty string")
        reference_image = datum.get("reference_image")
        if reference_image is not None and not isinstance(reference_image, str):
            errors.append("datum.reference_image: expected null or a path")

    instruments = _validate_instruments(record, errors)

    readings = record.get("readings")
    if not isinstance(readings, list) or not readings:
        errors.append("readings: expected at least one reading")
        readings = []
    else:
        seen: set[str] = set()
        for index, reading in enumerate(readings):
            _validate_reading(reading, f"readings[{index}]", instruments, errors)
            if isinstance(reading, dict):
                identifier = reading.get("dimension_id")
                if isinstance(identifier, str):
                    if identifier in seen:
                        errors.append(f"readings[{index}].dimension_id: duplicate identifier {identifier}")
                    seen.add(identifier)

    evidence = record.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("evidence: expected an object")
    else:
        level = evidence.get("level")
        if level not in EVIDENCE_LEVELS:
            errors.append(f"evidence.level: expected one of {sorted(EVIDENCE_LEVELS)}")
        for field in ("files", "contradictions"):
            values = evidence.get(field)
            if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
                errors.append(f"evidence.{field}: expected a string array")

        # Level A is the dimension of record. It requires a repeated measurement
        # taken with an instrument whose calibration is known.
        if level == "A" and isinstance(readings, list):
            for index, reading in enumerate(readings):
                if not isinstance(reading, dict):
                    continue
                samples = reading.get("samples")
                if isinstance(samples, list) and len(samples) < 3:
                    errors.append(f"readings[{index}].samples: evidence level A requires at least three samples")
                instrument = instruments.get(reading.get("instrument_id"))
                if instrument is not None:
                    calibration = instrument.get("calibration")
                    if isinstance(calibration, dict) and calibration.get("status") == "unknown":
                        errors.append(
                            f"readings[{index}].instrument_id: evidence level A requires a "
                            f"known calibration state for {reading.get('instrument_id')}"
                        )

    if not isinstance(record.get("notes"), str):
        errors.append("notes: expected a string")

    return errors


def load_and_validate(path: Path) -> list[str]:
    try:
        return validate_measurement(json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        return [f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]


def main(arguments: list[str] | None = None) -> int:
    args = sys.argv[1:] if arguments is None else arguments
    paths = [Path(value).resolve() for value in args] if args else sorted(REGISTRY.glob("*.json"))
    if not paths:
        print("measurements: no measurement records yet")
        return 0

    failures = 0
    for path in paths:
        errors = load_and_validate(path)
        label = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        if errors:
            failures += 1
            print(f"FAIL {label}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"OK   {label}")
    if failures:
        print(f"measurements: {failures} invalid record(s)")
        return 1
    print(f"measurements: {len(paths)} valid record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
