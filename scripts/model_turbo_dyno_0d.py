#!/usr/bin/env python3
"""Normalize public 993 Turbo dyno points without claiming a turbo map."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "simulation" / "993-turbo-dyno" / "dyno-reference.json"
DEFAULT_OUTPUT = ROOT / "simulation" / "993-turbo-dyno" / "derived-dyno-curves.json"
SOURCES = ROOT / "catalog" / "sources"
TORQUE_FACTORS = {"Nm": 1.0, "lb_ft": 1.3558179483314004}
POWER_KW_FACTORS = {"kW": 1.0, "PS": 0.73549875, "hp": 0.7456998715822702, "whp": 0.7456998715822702}
POWER_UNITS = set(POWER_KW_FACTORS)
TORQUE_UNITS = set(TORQUE_FACTORS)
R_AIR = 287.05


def _positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _known_source_ids() -> set[str]:
    known: set[str] = set()
    for path in SOURCES.glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(record, dict) and isinstance(record.get("source_id"), str):
            known.add(record["source_id"])
    return known


def validate_data(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["root: expected an object"]
    errors: list[str] = []
    for field in ("schema_version", "dataset_id", "status", "engine_context", "fit_policy", "runs"):
        if field not in payload:
            errors.append(f"root: missing {field}")
    if payload.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    if payload.get("status") != "reference_only":
        errors.append("status: expected reference_only")

    engine = payload.get("engine_context")
    if not isinstance(engine, dict):
        errors.append("engine_context: expected an object")
    else:
        if not _positive(engine.get("displacement_m3")):
            errors.append("engine_context.displacement_m3: expected a positive number")
        if engine.get("strokes") != 4:
            errors.append("engine_context.strokes: expected four-stroke engine")
        if engine.get("turbo_count") != 2:
            errors.append("engine_context.turbo_count: expected two turbochargers")
        airflow = engine.get("airflow_envelope")
        if not isinstance(airflow, dict):
            errors.append("engine_context.airflow_envelope: expected an object")
        else:
            for field in ("manifold_pressure_abs_pa", "manifold_temperature_k", "volumetric_efficiency_min", "volumetric_efficiency_max", "bank_split"):
                if not _positive(airflow.get(field)):
                    errors.append(f"engine_context.airflow_envelope.{field}: expected a positive number")
            if airflow.get("volumetric_efficiency_max", 0) < airflow.get("volumetric_efficiency_min", 0):
                errors.append("engine_context.airflow_envelope: VE max must not be below VE min")
            if airflow.get("bank_split", 0) > 1:
                errors.append("engine_context.airflow_envelope.bank_split: expected a fraction <= 1")

    fit_policy = payload.get("fit_policy")
    if not isinstance(fit_policy, dict) or fit_policy.get("status") != "not_calibrated":
        errors.append("fit_policy: status must remain not_calibrated")

    runs = payload.get("runs")
    if not isinstance(runs, list) or not runs:
        errors.append("runs: expected a non-empty array")
        return errors

    known_sources = _known_source_ids()
    run_ids: set[str] = set()
    for index, run in enumerate(runs):
        label = f"runs[{index}]"
        if not isinstance(run, dict):
            errors.append(f"{label}: expected an object")
            continue
        for field in ("run_id", "configuration_class", "source_id", "evidence_level", "calibration_role", "test_context", "notes"):
            if field not in run:
                errors.append(f"{label}: missing {field}")
        run_id = run.get("run_id")
        if not isinstance(run_id, str) or not run_id.strip():
            errors.append(f"{label}.run_id: expected a non-empty string")
        elif run_id in run_ids:
            errors.append(f"{label}.run_id: duplicate {run_id}")
        else:
            run_ids.add(run_id)
        if run.get("source_id") not in known_sources:
            errors.append(f"{label}.source_id: source is not registered")

        context = run.get("test_context")
        if not isinstance(context, dict):
            errors.append(f"{label}.test_context: expected an object")
        else:
            for field in ("test_type", "power_basis", "torque_basis", "standard", "correction"):
                if not isinstance(context.get(field), str):
                    errors.append(f"{label}.test_context.{field}: expected a string")

        points = run.get("reported_points", [])
        targets = run.get("reported_targets", [])
        bands = run.get("reported_bands", [])
        if not isinstance(points, list):
            errors.append(f"{label}.reported_points: expected an array")
            points = []
        if not isinstance(targets, list):
            errors.append(f"{label}.reported_targets: expected an array")
            targets = []
        if not isinstance(bands, list):
            errors.append(f"{label}.reported_bands: expected an array")
            bands = []
        if not points and not targets and not bands:
            errors.append(f"{label}: expected points, targets or bands")

        for position, point in enumerate(points):
            point_label = f"{label}.reported_points[{position}]"
            if not isinstance(point, dict):
                errors.append(f"{point_label}: expected an object")
                continue
            if not _positive(point.get("rpm")):
                errors.append(f"{point_label}.rpm: expected a positive number")
            has_torque = point.get("torque_value") is not None
            has_power = point.get("power_value") is not None
            if not has_torque and not has_power:
                errors.append(f"{point_label}: expected torque_value or power_value")
            if has_torque and (not _positive(point.get("torque_value")) or point.get("torque_unit") not in TORQUE_UNITS):
                errors.append(f"{point_label}: invalid torque value or unit")
            if has_power and (not _positive(point.get("power_value")) or point.get("power_unit") not in POWER_UNITS):
                errors.append(f"{point_label}: invalid power value or unit")

        for collection_name, collection in (("reported_targets", targets), ("reported_bands", bands)):
            for position, item in enumerate(collection):
                item_label = f"{label}.{collection_name}[{position}]"
                if not isinstance(item, dict):
                    errors.append(f"{item_label}: expected an object")
                    continue
                if not _positive(item.get("value")) or item.get("unit") not in POWER_UNITS:
                    errors.append(f"{item_label}: expected positive power value and known unit")
                if collection_name == "reported_targets" and item.get("rpm") is not None and not _positive(item.get("rpm")):
                    errors.append(f"{item_label}.rpm: expected null or a positive number")
                if collection_name == "reported_bands":
                    if not _positive(item.get("rpm_min")) or not _positive(item.get("rpm_max")) or item["rpm_max"] < item["rpm_min"]:
                        errors.append(f"{item_label}: invalid rpm range")

    return errors


def torque_nm(point: dict[str, Any]) -> float | None:
    value = point.get("torque_value")
    unit = point.get("torque_unit")
    if value is None or unit not in TORQUE_FACTORS:
        return None
    return float(value) * TORQUE_FACTORS[unit]


def power_kw(value: float, unit: str) -> float:
    return float(value) * POWER_KW_FACTORS[unit]


def power_from_torque_kw(torque: float, rpm: float) -> float:
    return torque * 2.0 * math.pi * rpm / 60.0 / 1000.0


def bmep_bar(torque: float, displacement_m3: float) -> float:
    return 4.0 * math.pi * torque / displacement_m3 / 100000.0


def airflow_context(rpm: float, engine: dict[str, Any]) -> dict[str, Any]:
    airflow = engine["airflow_envelope"]
    density = airflow["manifold_pressure_abs_pa"] / (R_AIR * airflow["manifold_temperature_k"])
    swept_volume_rate = engine["displacement_m3"] * rpm / (2.0 * 60.0)
    total_min = density * swept_volume_rate * airflow["volumetric_efficiency_min"]
    total_max = density * swept_volume_rate * airflow["volumetric_efficiency_max"]
    return {
        "assumed_manifold_density_kg_m3": density,
        "mass_flow_total_min_kg_s": total_min,
        "mass_flow_total_max_kg_s": total_max,
        "mass_flow_per_turbo_min_kg_s": total_min * airflow["bank_split"],
        "mass_flow_per_turbo_max_kg_s": total_max * airflow["bank_split"],
        "basis": "0D envelope from assumed manifold pressure, temperature, VE and equal bank split; not measured dyno airflow.",
    }


def derive_run(run: dict[str, Any], engine: dict[str, Any]) -> dict[str, Any]:
    derived_points: list[dict[str, Any]] = []
    consistency_checks: list[dict[str, Any]] = []
    same_point_consistency_rpm: set[float] = set()
    for point in run.get("reported_points", []):
        result: dict[str, Any] = {"rpm": point["rpm"]}
        torque = torque_nm(point)
        if torque is not None:
            result["torque_nm"] = torque
            result["power_from_torque_kw"] = power_from_torque_kw(torque, point["rpm"])
            result["power_from_torque_hp"] = result["power_from_torque_kw"] / POWER_KW_FACTORS["hp"]
            result["bmep_bar"] = bmep_bar(torque, engine["displacement_m3"])
        if point.get("power_value") is not None:
            result["reported_power_kw"] = power_kw(point["power_value"], point["power_unit"])
            result["reported_power_unit"] = point["power_unit"]
            result["reported_power_value"] = point["power_value"]
        if torque is not None and point.get("power_value") is not None:
            derived = result["power_from_torque_kw"]
            reported = result["reported_power_kw"]
            relative_error = abs(derived - reported) / reported if reported else None
            same_point_consistency_rpm.add(point["rpm"])
            consistency_checks.append({
                "rpm": point["rpm"],
                "status": "within_5_percent" if relative_error is not None and relative_error <= 0.05 else "inconsistent_over_5_percent",
                "reported_power_kw": reported,
                "power_from_torque_kw": derived,
                "relative_error": relative_error,
                "note": "A mismatch can indicate different power/torque bases, rounding or an incomplete forum transcription.",
            })
        result["airflow_context"] = airflow_context(point["rpm"], engine)
        derived_points.append(result)

    # Some reports publish power and torque as separate rows at the same RPM.
    # Compare those rows too, while keeping the source values untouched.
    torque_by_rpm: dict[float, float] = {}
    power_by_rpm: dict[float, tuple[float, str]] = {}
    for point in run.get("reported_points", []):
        torque = torque_nm(point)
        if torque is not None:
            torque_by_rpm[point["rpm"]] = torque
        if point.get("power_value") is not None:
            power_by_rpm[point["rpm"]] = (power_kw(point["power_value"], point["power_unit"]), point["power_unit"])
    for rpm in sorted(set(torque_by_rpm) & set(power_by_rpm) - same_point_consistency_rpm):
        expected = power_from_torque_kw(torque_by_rpm[rpm], rpm)
        reported, unit = power_by_rpm[rpm]
        relative_error = abs(expected - reported) / reported if reported else None
        consistency_checks.append({
            "rpm": rpm,
            "status": "within_5_percent" if relative_error is not None and relative_error <= 0.05 else "inconsistent_over_5_percent",
            "reported_power_kw": reported,
            "power_from_torque_kw": expected,
            "relative_error": relative_error,
            "power_unit": unit,
            "note": "Power and torque were published as separate same-RPM rows; differing bases or transcription are possible.",
        })

    for target in run.get("reported_targets", []):
        target_rpm = target.get("rpm")
        if target_rpm is None:
            continue
        for point in run.get("reported_points", []):
            if point.get("rpm") != target_rpm or torque_nm(point) is None:
                continue
            expected = power_from_torque_kw(torque_nm(point), target_rpm)
            reported = power_kw(target["value"], target["unit"])
            relative_error = abs(expected - reported) / reported if reported else None
            consistency_checks.append({
                "rpm": target_rpm,
                "target": target["label"],
                "status": "within_5_percent" if relative_error is not None and relative_error <= 0.05 else "inconsistent_over_5_percent",
                "reported_power_kw": reported,
                "power_from_torque_kw": expected,
                "relative_error": relative_error,
                "note": "Target-versus-torque comparison is a plausibility check, not a correction of the source.",
            })

    return {
        "run_id": run["run_id"],
        "twin_variant": run.get("twin_variant"),
        "configuration_class": run["configuration_class"],
        "source_id": run["source_id"],
        "evidence_level": run["evidence_level"],
        "calibration_role": run["calibration_role"],
        "test_context": run["test_context"],
        "reported_targets": run.get("reported_targets", []),
        "reported_bands": run.get("reported_bands", []),
        "derived_points": derived_points,
        "consistency_checks": consistency_checks,
        "notes": run["notes"],
    }


def build_output(payload: dict[str, Any], source_path: Path) -> dict[str, Any]:
    engine = payload["engine_context"]
    return {
        "$comment": "Sortie dérivée : conversions et enveloppe 0D, sans donnée brute de banc ni carte de turbo.",
        "schema_version": "1.0.0",
        "dataset_id": payload["dataset_id"],
        "generated_from": str(source_path.relative_to(ROOT)),
        "model": {
            "name": "transparent_0d_dyno_normalizer",
            "status": "reference_only",
            "constants": {"air_gas_constant_j_kg_k": R_AIR, "lb_ft_to_nm": TORQUE_FACTORS["lb_ft"]},
            "engine_context": engine,
            "limitations": [
                "Les points de banc restent issus de publications publiques et de rapports de forum.",
                "Le débit est une enveloppe issue d'hypothèses moteur ; il ne calibre pas un compresseur.",
                "Aucune interpolation ne doit être extrapolée hors de la plage de points.",
            ],
        },
        "runs": [derive_run(run, engine) for run in payload["runs"]],
    }


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true", help="write the derived reference output")
    parser.add_argument("--check", action="store_true", help="validate input and checked-in derived output")
    args = parser.parse_args(arguments)
    try:
        payload = json.loads(args.data.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"turbo-dyno: cannot read {args.data}: {exc}")
    errors = validate_data(payload)
    if errors:
        raise SystemExit("turbo-dyno: invalid data\n" + "\n".join(f"  - {error}" for error in errors))
    derived = build_output(payload, args.data)
    serialized = json.dumps(derived, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    if args.check or not args.write:
        if not args.output.is_file():
            print(f"FAIL {args.output}: derived output does not exist")
            return 1
        if args.output.read_text(encoding="utf-8") != serialized:
            print(f"FAIL {args.output}: regenerate with --write")
            return 1
    action = "generated" if args.write else "validated"
    print(f"OK   {args.data.relative_to(ROOT)} ({action} {len(payload['runs'])} dyno references)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
