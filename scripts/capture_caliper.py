#!/usr/bin/env python3
"""Record readings from a measuring instrument into a measurement record.

Two capture paths, and the record says which one was used:

  serial  the instrument sends the value itself (Mitutoyo Digimatic and other
          serial or USB-serial gauges). Readings are timestamped by the machine.
  manual  values are typed in. Honest, and marked as such: a typed value is
          never recorded as an instrument stream.

Examples:
  capture_caliper.py --record catalog/measurements/meas-993-door-strap.json \\
      --dimension D01 --description "Strap eye bore" --port /dev/ttyUSB0 --repeats 3

  capture_caliper.py --record <file> --dimension D02 --description "Plate thickness" \\
      --manual --values 3.98,4.01,3.99

The record is created from templates/measurement-record.json when missing, then
validated with scripts/validate_measurements.py before it is written back.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from statistics import fmean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "measurement-record.json"

sys.path.insert(0, str(ROOT))
from scripts.validate_measurements import validate_measurement  # noqa: E402


def read_serial(port: str, baud: int, repeats: int, timeout: float) -> list[float]:
    """Read `repeats` values from a serial instrument.

    Digimatic-style gauges send one reading per line when their data button is
    pressed, so this blocks until the operator has taken every sample.
    """
    try:
        import serial  # type: ignore
    except ImportError:  # pragma: no cover - depends on the host
        raise SystemExit(
            "serial capture needs pyserial: pip install pyserial, "
            "or use --manual to type the values"
        )

    values: list[float] = []
    with serial.Serial(port, baud, timeout=timeout) as link:
        while len(values) < repeats:
            print(f"  waiting for sample {len(values) + 1}/{repeats} ...", flush=True)
            raw = link.readline().decode("ascii", errors="ignore").strip()
            if not raw:
                continue
            cleaned = raw.replace("+", "").replace("mm", "").strip()
            try:
                values.append(float(cleaned))
            except ValueError:
                print(f"  ignored unparsable frame: {raw!r}", file=sys.stderr)
    return values


def load_record(path: Path, measurement_id: str | None) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    record = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    record["measurement_id"] = measurement_id or f"MEAS-{path.stem.upper().replace('_', '-')}"
    record["session"]["performed_on"] = date.today().isoformat()
    record["readings"] = []
    return record


def build_reading(
    dimension_id: str,
    description: str,
    instrument: dict[str, Any],
    samples: list[float],
    unit: str,
    method: str,
    streamed: bool,
) -> dict[str, Any]:
    resolution = instrument.get("resolution_mm")
    spread = (max(samples) - min(samples)) / 2 if len(samples) > 1 else 0.0
    floor = resolution / 2 if isinstance(resolution, (int, float)) else 0.0
    uncertainty = max(spread, floor)
    if uncertainty <= 0:
        raise SystemExit(
            "cannot derive an uncertainty: declare resolution_mm on the instrument "
            "or take repeated samples"
        )
    if spread > 0 and floor > 0:
        basis = "combined"
    elif spread > 0:
        basis = "repeatability"
    else:
        basis = "instrument_resolution"

    digits = 4 if unit == "mm" else 3
    return {
        "dimension_id": dimension_id,
        "description": description,
        "instrument_id": instrument["instrument_id"],
        "method": method,
        "unit": unit,
        "samples": samples,
        "value": round(fmean(samples), digits),
        "uncertainty": round(uncertainty, digits),
        "uncertainty_basis": basis,
        "capture_mode": "instrument_stream" if streamed else "manual_entry",
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds") if streamed else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--record", required=True, type=Path, help="measurement record to create or extend")
    parser.add_argument("--measurement-id", help="identifier used when the record is created")
    parser.add_argument("--dimension", required=True, help="dimension identifier, for example D01")
    parser.add_argument("--description", required=True, help="what is measured, between which faces")
    parser.add_argument("--instrument", default="CAL-01", help="instrument_id declared in the record")
    parser.add_argument("--unit", default="mm", choices=["mm", "deg", "kg", "N", "Nm"])
    parser.add_argument("--method", default="direct", choices=["direct", "indirect", "gauge", "photogrammetry", "scan", "derived"])
    parser.add_argument("--repeats", type=int, default=3, help="number of samples to take")
    parser.add_argument("--port", help="serial port of the instrument, for example /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--manual", action="store_true", help="type the values instead of reading an instrument")
    parser.add_argument("--values", help="comma separated values, implies --manual")
    args = parser.parse_args(argv)

    record = load_record(args.record, args.measurement_id)
    instruments = {item["instrument_id"]: item for item in record.get("instruments", [])}
    if args.instrument not in instruments:
        raise SystemExit(
            f"instrument {args.instrument!r} is not declared in {args.record}. "
            "Add it, with its resolution and calibration state, before capturing."
        )
    instrument = instruments[args.instrument]

    manual = args.manual or args.values is not None
    if manual:
        if args.values:
            samples = [float(value) for value in args.values.split(",") if value.strip()]
        else:
            print(f"Type {args.repeats} values for {args.dimension}, one per line:")
            samples = [float(input(f"  sample {index + 1}: ")) for index in range(args.repeats)]
    else:
        if not args.port:
            raise SystemExit("give --port for serial capture, or --manual to type the values")
        if instrument.get("interface") == "manual":
            raise SystemExit(
                f"instrument {args.instrument} declares a manual interface; "
                "set it to serial or usb before streaming from it"
            )
        samples = read_serial(args.port, args.baud, args.repeats, args.timeout)

    reading = build_reading(
        args.dimension, args.description, instrument, samples, args.unit, args.method, streamed=not manual
    )
    record["readings"] = [item for item in record["readings"] if item.get("dimension_id") != args.dimension]
    record["readings"].append(reading)
    record["readings"].sort(key=lambda item: item["dimension_id"])

    errors = validate_measurement(record)
    if errors:
        print(f"record would be invalid, nothing written to {args.record}:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"{args.dimension}: {reading['value']} {reading['unit']} "
        f"+/- {reading['uncertainty']} ({reading['uncertainty_basis']}, "
        f"{len(samples)} samples, {reading['capture_mode']}) -> {args.record}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
