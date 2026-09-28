#!/usr/bin/env python3
"""Validate PET-linked engineering guide stages with OpenUSD strict checking."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CARRIER_REPORT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engine-carrier-mass-constrained-surrogate-f1.json"
)
VALVE_REPORT = (
    ROOT / "twins" / "catalogue-parts" / "valve-dimensional-surrogates-f1.json"
)
K16_REPORT = (
    ROOT / "twins" / "catalogue-parts" / "k16-envelope-flow-readiness-f1.json"
)
CHARGE_AIR_REPORT = (
    ROOT / "twins" / "catalogue-parts" / "charge-air-chain-readiness-f1.json"
)
HEAT_SHIELD_REPORT = (
    ROOT / "twins" / "catalogue-parts" / "turbo-heat-shield-readiness-f1.json"
)
TURBO_LUBRICATION_CONTROL_REPORT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "turbo-lubrication-control-topology-readiness-f1.json"
)
OIL_TANK_CIRCUIT_REPORT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "oil-tank-circuit-topology-readiness-f1.json"
)
OIL_COOLER_CIRCUIT_REPORT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "oil-cooler-circuit-topology-readiness-f1.json"
)
OUTPUT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering-guides-openusd-validation-f1.json"
)


class ValidationError(ValueError):
    """Raised when an engineering guide is stale, invalid or overclaimed."""


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot_load:{relative(path)}:{exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"expected_object:{relative(path)}")
    return value


def render(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def tool_version(usdcat: str) -> str:
    result = subprocess.run(
        [usdcat, "--version"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0 or not output:
        raise ValidationError("cannot_identify_openusd_tool_version")
    return output


def validate_stage(
    checker: str,
    *,
    role: str,
    report_path: Path,
    report: dict[str, Any],
    expected_guide_primitives: int,
) -> dict[str, Any]:
    assets = report.get("assets", {})
    stage_value = assets.get("openusd_guide")
    expected_digest = assets.get("openusd_guide_sha256")
    if not isinstance(stage_value, str) or not isinstance(expected_digest, str):
        raise ValidationError(f"missing_stage_contract:{role}")
    stage = ROOT / stage_value
    if not stage.is_file() or sha256_file(stage) != expected_digest:
        raise ValidationError(f"stale_stage:{stage_value}")
    result = subprocess.run(
        [checker, "--strict", str(stage)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    combined = result.stdout + result.stderr
    if result.returncode != 0 or "Success!" not in combined:
        summary = " ".join(combined.split())[:500]
        raise ValidationError(f"usdchecker_failed:{stage_value}:{summary}")
    if any(value is not False for value in report.get("claim_boundary", {}).values()):
        raise ValidationError(f"source_report_overclaim:{role}")
    return {
        "role": role,
        "source_report": relative(report_path),
        "source_report_sha256": sha256_file(report_path),
        "stage": stage_value,
        "stage_sha256": expected_digest,
        "expected_guide_primitives": expected_guide_primitives,
        "strict_mode": True,
        "return_code": result.returncode,
        "result": "passed",
    }


def build_report() -> dict[str, Any]:
    checker = shutil.which("usdchecker")
    usdcat = shutil.which("usdcat")
    if checker is None or usdcat is None:
        raise ValidationError("openusd_cli_tools_unavailable")
    carrier = load_json(CARRIER_REPORT)
    valves = load_json(VALVE_REPORT)
    k16 = load_json(K16_REPORT)
    charge_air = load_json(CHARGE_AIR_REPORT)
    heat_shield = load_json(HEAT_SHIELD_REPORT)
    turbo_lubrication_control = load_json(TURBO_LUBRICATION_CONTROL_REPORT)
    oil_tank_circuit = load_json(OIL_TANK_CIRCUIT_REPORT)
    oil_cooler_circuit = load_json(OIL_COOLER_CIRCUIT_REPORT)
    validated = [
        validate_stage(
            checker,
            role="engine_carrier_mass_constrained_F1_guide",
            report_path=CARRIER_REPORT,
            report=carrier,
            expected_guide_primitives=4,
        ),
        validate_stage(
            checker,
            role="three_valve_dimensional_F1_guides",
            report_path=VALVE_REPORT,
            report=valves,
            expected_guide_primitives=9,
        ),
        validate_stage(
            checker,
            role="two_K16_envelope_and_right_diameter_F1_guides",
            report_path=K16_REPORT,
            report=k16,
            expected_guide_primitives=6,
        ),
        validate_stage(
            checker,
            role="five_charge_air_envelope_and_aftermarket_diameter_F1_guides",
            report_path=CHARGE_AIR_REPORT,
            report=charge_air,
            expected_guide_primitives=7,
        ),
        validate_stage(
            checker,
            role="one_turbo_heat_shield_envelope_thermal_F1_guide",
            report_path=HEAT_SHIELD_REPORT,
            report=heat_shield,
            expected_guide_primitives=1,
        ),
        validate_stage(
            checker,
            role="forty_202_16_turbo_lubrication_control_topology_F1_entries",
            report_path=TURBO_LUBRICATION_CONTROL_REPORT,
            report=turbo_lubrication_control,
            expected_guide_primitives=24,
        ),
        validate_stage(
            checker,
            role="eighty_one_104_01_oil_tank_circuit_topology_F1_entries",
            report_path=OIL_TANK_CIRCUIT_REPORT,
            report=oil_tank_circuit,
            expected_guide_primitives=21,
        ),
        validate_stage(
            checker,
            role="forty_three_104_05_oil_cooler_circuit_topology_F1_entries",
            report_path=OIL_COOLER_CIRCUIT_REPORT,
            report=oil_cooler_circuit,
            expected_guide_primitives=25,
        ),
    ]
    report = {
        "$comment": (
            "Validation OpenUSD stricte de guides d'ingenierie F1 lies au PET. "
            "Elle ne prouve ni geometrie OEM, ni physique, ni SimReady."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "status": "passed_openusd_strict_not_nvidia_asset_validator_or_simready",
        "validator": {
            "command": "usdchecker --strict",
            "tool_suite": tool_version(usdcat),
            "framework": "OpenUSD_compliance_and_dependency_checks",
        },
        "scope": {
            "validated_stage_count": len(validated),
            "validated_F1_surrogate_variants": 176,
            "guide_primitive_count": sum(
                item["expected_guide_primitives"] for item in validated
            ),
            "pet_linked_part_master_count": 171,
            "analysis_geometry_count": 0,
            "physics_schema_count": 0,
            "qualified_material_assignment_count": 0,
            "simready_asset_count": 0,
        },
        "validated_stages": validated,
        "results": {
            "strict_openusd_validation": "passed",
            "asset_dependency_resolution": "passed",
            "nvidia_asset_validator": "not_run_preflight_blocked",
            "simready_foundation": "not_run_preflight_blocked",
            "simready_validated": False,
        },
        "claim_boundary": {
            "openusd_pass_is_geometry_accuracy": False,
            "openusd_pass_is_interface_fit": False,
            "openusd_pass_is_material_or_physics_validation": False,
            "openusd_pass_is_reference_CAE": False,
            "openusd_pass_is_physicsnemo_validation": False,
            "openusd_pass_is_nvidia_asset_validator": False,
            "openusd_pass_is_simready": False,
            "openusd_pass_authorizes_manufacturing_or_road_use": False,
        },
    }
    validate_report(report)
    return report


def validate_report(report: dict[str, Any]) -> None:
    if report.get("status") != (
        "passed_openusd_strict_not_nvidia_asset_validator_or_simready"
    ):
        raise ValidationError("status")
    scope = report.get("scope", {})
    expected = {
        "validated_stage_count": 8,
        "validated_F1_surrogate_variants": 176,
        "guide_primitive_count": 97,
        "pet_linked_part_master_count": 171,
        "analysis_geometry_count": 0,
        "physics_schema_count": 0,
        "qualified_material_assignment_count": 0,
        "simready_asset_count": 0,
    }
    if any(scope.get(field) != value for field, value in expected.items()):
        raise ValidationError("scope")
    stages = report.get("validated_stages", [])
    if len(stages) != 8 or any(item.get("result") != "passed" for item in stages):
        raise ValidationError("validated_stages")
    if report.get("results", {}).get("simready_validated") is not False:
        raise ValidationError("simready_overclaim")
    if any(value is not False for value in report.get("claim_boundary", {}).values()):
        raise ValidationError("claim_boundary")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = build_report()
        expected = render(report)
        if args.write:
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(expected, encoding="utf-8")
            print(
                f"wrote {relative(OUTPUT)}: "
                f"{report['scope']['validated_stage_count']} strict OpenUSD validations passed"
            )
            return 0
        if not OUTPUT.is_file():
            print(f"missing:{relative(OUTPUT)}")
            return 1
        if args.check and OUTPUT.read_text(encoding="utf-8") != expected:
            print(f"stale:{relative(OUTPUT)}")
            return 1
        checked = load_json(OUTPUT)
        validate_report(checked)
        if checked.get("validated_stages") != report.get("validated_stages"):
            raise ValidationError("stage_evidence")
        print(
            f"current {relative(OUTPUT)}: "
            f"{checked['scope']['validated_stage_count']} strict OpenUSD validations passed"
        )
        return 0
    except (ValidationError, OSError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
