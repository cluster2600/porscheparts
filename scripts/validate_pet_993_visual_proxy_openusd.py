#!/usr/bin/env python3
"""Validate the complete PET 993 visual twin with a real OpenUSD checker."""

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
ATLAS_MANIFEST = ROOT / "twins" / "pet-993" / "visual-proxy-atlas-f0.json"
OUTPUT = ROOT / "twins" / "pet-993" / "visual-proxy-atlas-openusd-validation-f0.json"


class ValidationError(ValueError):
    """Raised when the OpenUSD evidence cannot be reproduced."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot_load:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"expected_object:{path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


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
    text = (result.stdout + result.stderr).strip()
    if result.returncode != 0 or not text:
        raise ValidationError("cannot_identify_usd_tool_version")
    return text


def validated_stage(
    checker: str, role: str, path: Path, expected_sha256: str
) -> dict[str, Any]:
    if not path.is_file():
        raise ValidationError(f"missing_stage:{relative(path)}")
    actual_sha256 = sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise ValidationError(f"stale_stage_digest:{relative(path)}")
    result = subprocess.run(
        [checker, "--strict", str(path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    combined = result.stdout + result.stderr
    if result.returncode != 0 or "Success!" not in combined:
        summary = " ".join(combined.split())[:500]
        raise ValidationError(f"usdchecker_failed:{relative(path)}:{summary}")
    return {
        "role": role,
        "path": relative(path),
        "sha256": actual_sha256,
        "strict_mode": True,
        "return_code": result.returncode,
        "result": "passed",
    }


def build_report() -> dict[str, Any]:
    manifest = load_json(ATLAS_MANIFEST)
    checker = shutil.which("usdchecker")
    usdcat = shutil.which("usdcat")
    if checker is None or usdcat is None:
        raise ValidationError("openusd_cli_tools_unavailable")
    output = manifest.get("output", {})
    stage_contracts = (
        (
            "archetype_prototype_library",
            output.get("prototype_stage"),
            output.get("prototype_stage_sha256"),
        ),
        (
            "complete_visual_proxy_atlas",
            output.get("root_stage"),
            output.get("root_stage_sha256"),
        ),
        (
            "documentary_visual_functional_composition",
            output.get("composed_catalogue_digital_twin_stage"),
            output.get("composed_catalogue_digital_twin_stage_sha256"),
        ),
    )
    validated: list[dict[str, Any]] = []
    for role, path_value, digest in stage_contracts:
        if not isinstance(path_value, str) or not isinstance(digest, str):
            raise ValidationError(f"invalid_stage_contract:{role}")
        validated.append(validated_stage(checker, role, ROOT / path_value, digest))
    atlas = manifest.get("atlas", {})
    if atlas.get("part_master_proxy_instances") != 6013:
        raise ValidationError("unexpected_proxy_count")
    if atlas.get("engineering_geometry_count") != 0:
        raise ValidationError("engineering_geometry_overclaim")
    if any(value is not False for value in manifest.get("claim_boundary", {}).values()):
        raise ValidationError("atlas_claim_boundary")
    report = {
        "$comment": (
            "Validation OpenUSD stricte de l'atlas visuel PET 993 et de sa composition. "
            "Elle prouve la conformite et la resolution des actifs USD, pas SimReady, "
            "la justesse dimensionnelle, la physique ou le fonctionnement du vehicule."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "status": "passed_openusd_strict_not_simready",
        "source": {
            "atlas_manifest": relative(ATLAS_MANIFEST),
            "atlas_manifest_sha256": sha256_file(ATLAS_MANIFEST),
        },
        "validator": {
            "command": "usdchecker --strict",
            "tool_suite": tool_version(usdcat),
            "validation_framework": "OpenUSD_compliance_and_asset_dependency_checks",
        },
        "scope": {
            "validated_root_stages": len(validated),
            "visual_proxy_instances_resolved_through_atlas": 6013,
            "archetype_prototypes_resolved": int(atlas.get("archetype_prototypes", 0)),
            "shard_layers_resolved_through_atlas": int(atlas.get("shard_layers", 0)),
            "documentary_visual_and_functional_layers_composed": True,
        },
        "validated_stages": validated,
        "results": {
            "strict_openusd_validation": "passed",
            "asset_dependency_resolution": "passed",
            "composition_resolution": "passed",
            "openusd_python_api": "not_required_for_this_cli_validation",
            "nvidia_asset_validator": "not_run",
            "simready_foundation": "not_run",
            "simready_validated": False,
        },
        "claim_boundary": {
            "openusd_pass_is_simready_pass": False,
            "openusd_pass_proves_dimensional_accuracy": False,
            "openusd_pass_proves_vehicle_transforms": False,
            "openusd_pass_proves_material_or_physics": False,
            "openusd_pass_proves_physicsnemo_readiness": False,
            "openusd_pass_proves_functioning_vehicle": False,
            "openusd_pass_authorizes_manufacturing_or_road_use": False,
        },
    }
    validate_report_index(report)
    return report


def validate_report_index(report: dict[str, Any]) -> None:
    if report.get("status") != "passed_openusd_strict_not_simready":
        raise ValidationError("report_status")
    if report.get("source", {}).get("atlas_manifest_sha256") != sha256_file(
        ATLAS_MANIFEST
    ):
        raise ValidationError("atlas_manifest_digest")
    scope = report.get("scope", {})
    if scope.get("validated_root_stages") != 3:
        raise ValidationError("validated_root_stage_count")
    if scope.get("visual_proxy_instances_resolved_through_atlas") != 6013:
        raise ValidationError("validated_proxy_instance_count")
    stages = report.get("validated_stages", [])
    if not isinstance(stages, list) or len(stages) != 3:
        raise ValidationError("validated_stage_records")
    if any(item.get("result") != "passed" for item in stages):
        raise ValidationError("validated_stage_result")
    if report.get("results", {}).get("simready_validated") is not False:
        raise ValidationError("simready_overclaim")
    if any(value is not False for value in report.get("claim_boundary", {}).values()):
        raise ValidationError("report_claim_boundary")


def check_report_index() -> None:
    report = load_json(OUTPUT)
    validate_report_index(report)
    manifest = load_json(ATLAS_MANIFEST)
    expected = {
        str(manifest["output"]["prototype_stage"]): str(
            manifest["output"]["prototype_stage_sha256"]
        ),
        str(manifest["output"]["root_stage"]): str(
            manifest["output"]["root_stage_sha256"]
        ),
        str(manifest["output"]["composed_catalogue_digital_twin_stage"]): str(
            manifest["output"]["composed_catalogue_digital_twin_stage_sha256"]
        ),
    }
    actual = {str(item["path"]): str(item["sha256"]) for item in report["validated_stages"]}
    if actual != expected:
        raise ValidationError("validated_stage_digest_contract")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.check_index:
            check_report_index()
            print(f"valid {relative(OUTPUT)}: strict OpenUSD evidence index")
            return 0
        report = build_report()
        expected = render(report)
        if args.write:
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(expected, encoding="utf-8")
            print(f"wrote {relative(OUTPUT)}: 3 strict OpenUSD validations passed")
            return 0
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            raise ValidationError(f"stale_validation_report:{relative(OUTPUT)}")
        print(f"current {relative(OUTPUT)}: 3 strict OpenUSD validations passed")
        return 0
    except (ValidationError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
