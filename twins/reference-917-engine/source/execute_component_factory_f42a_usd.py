#!/usr/bin/env python3
"""Convert the exact validated F41 STEP archive into six minimum-valid USD assets.

F42a is deliberately conversion-only.  It imports a closed file allowlist,
runs the NVIDIA CAD-to-SimReady preflight and minimum validator, and never
assigns materials or physics properties.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = REPO_ROOT / "twins/reference-917-engine/component-factory-f42a-usd.json"
EXPECTED_FAMILIES = (
    "connecting_rod",
    "crankshaft",
    "main_bearing_pair",
    "piston",
    "piston_pin",
    "piston_ring",
)
USD_SUFFIXES = {".usd", ".usda", ".usdc", ".usdz"}
REQUIRED_RELEASE_GATES = {
    "all_family_counts_closed",
    "all_interface_dimensions_measured",
    "all_materials_qualified",
    "all_tolerances_and_clearances_released",
    "all_editable_cad_generated",
    "all_step_roundtrips_validated",
    "all_3mf_meshes_validated",
    "all_usd_assets_minimum_valid",
    "simready_property_assignment_complete",
    "assembly_interference_check_passed",
    "lubrication_and_cooling_validated",
    "combustion_and_boost_validated",
    "fatigue_and_rotordynamics_validated",
    "physical_flowbench_correlated",
    "physical_dyno_correlated",
    "professional_engineering_review_approved",
    "metal_print_authorized",
    "engine_start_authorized",
    "installation_in_993_authorized",
    "performance_1600_hp_claim_authorized",
}


class F42aError(RuntimeError):
    """Fail-closed F42a execution error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise F42aError(message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise F42aError(f"missing_json:{path}") from exc
    except json.JSONDecodeError as exc:
        raise F42aError(f"invalid_json:{path}:{exc}") from exc
    require(isinstance(value, dict), f"json_object_required:{path}")
    return value


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except FileNotFoundError as exc:
        raise F42aError(f"missing_input:{path}") from exc
    return digest.hexdigest()


def regular_file(path: Path, label: str) -> os.stat_result:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise F42aError(f"missing_{label}:{path}") from exc
    require(stat.S_ISREG(info.st_mode), f"{label}_must_be_regular_file:{path}")
    require(not path.is_symlink(), f"{label}_symlink_forbidden:{path}")
    return info


def safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    require(value == path.as_posix(), f"non_canonical_allowlist_path:{value}")
    require(not path.is_absolute() and ".." not in path.parts, f"unsafe_allowlist_path:{value}")
    require(path.parts and all(part not in {"", "."} for part in path.parts), f"unsafe_allowlist_path:{value}")
    return path


def validate_contract(contract: dict[str, Any]) -> dict[str, Any]:
    require(contract.get("schema_version") == "1.0.0", "unexpected_contract_schema")
    require(contract.get("phase") == "F42a", "expected_F42a_contract")
    source = contract.get("source")
    runtime = contract.get("runtime")
    audit = contract.get("usd_audit")
    output = contract.get("output_contract")
    gates = contract.get("release_gates")
    allowlist = contract.get("input_allowlist")
    families = contract.get("families")
    require(isinstance(source, dict), "source_contract_required")
    require(source.get("phase") == "F41", "F41_source_required")
    run_id = source.get("run_id")
    require(
        isinstance(run_id, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,127}", run_id) is not None,
        "invalid_source_run_id",
    )
    require(run_id == source.get("archive_root"), "archive_root_must_match_run_id")
    require(source.get("archive_filename") == f"{run_id}.tar.gz", "archive_filename_mismatch")
    require(isinstance(source.get("archive_size_bytes"), int) and source["archive_size_bytes"] > 0, "archive_size_invalid")
    require(isinstance(source.get("archive_sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", source["archive_sha256"]) is not None, "archive_sha256_invalid")
    require(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", str(source.get("source_revision", ""))) is not None, "source_revision_invalid")
    require(isinstance(families, list) and tuple(families) == EXPECTED_FAMILIES, "exact_six_family_order_required")
    require(isinstance(allowlist, list) and len(allowlist) == 15, "exact_15_file_allowlist_required")
    require(isinstance(runtime, dict), "runtime_contract_required")
    require(runtime.get("image_repository") == "ghcr.io/cluster2600/3dprinting993-simready-workflow", "unexpected_runtime_image_repository")
    qualification = runtime.get("qualification_status")
    image_ref = runtime.get("image_ref")
    require(
        qualification in {"pending_new_simready_workflow_digest", "qualified_public_linux_amd64_digest"},
        "invalid_runtime_qualification_status",
    )
    if qualification == "pending_new_simready_workflow_digest":
        require(image_ref is None, "pending_runtime_must_not_pin_an_image")
    else:
        require(
            isinstance(image_ref, str)
            and re.fullmatch(r"ghcr\.io/cluster2600/3dprinting993-simready-workflow@sha256:[0-9a-f]{64}", image_ref) is not None,
            "qualified_runtime_requires_exact_digest",
        )
    require(runtime.get("platform") == "linux/amd64", "linux_amd64_runtime_required")
    require(runtime.get("network_required_during_job") is False, "offline_job_required")
    require(runtime.get("gpu_required") is False, "F42a_must_be_CPU_only")
    require(runtime.get("content_agents") == "skipped", "content_agents_must_be_skipped")
    require(runtime.get("skill_name") == "omniverse-cad-to-simready", "unexpected_skill_name")
    require(runtime.get("preflight_targets") == ["conversion", "validation"], "conversion_validation_preflight_required")
    require(runtime.get("conversion_route") == "usd-convert-cad", "usd_convert_cad_required")
    require(runtime.get("minimum_validator") == "validate-usd-minimum", "minimum_validator_required")
    adapter = runtime.get("converter_adapter")
    require(isinstance(adapter, dict), "converter_adapter_contract_required")
    require(adapter.get("path") == "/opt/usd-convert-cad-preflight/convert.py", "converter_adapter_path_mismatch")
    require(re.fullmatch(r"[0-9a-f]{64}", str(adapter.get("sha256", ""))) is not None, "converter_adapter_sha256_invalid")
    require(isinstance(adapter.get("size_bytes"), int) and adapter["size_bytes"] > 0, "converter_adapter_size_invalid")
    skill_files = runtime.get("skill_file_allowlist")
    require(isinstance(skill_files, list) and len(skill_files) == 5, "exact_skill_file_allowlist_required")
    required_skill_paths = {
        "SKILL.md",
        "references/preflight/scripts/preflight.py",
        "references/validate-usd-minimum/scripts/run.py",
        "shared/script_utils.py",
        "shared/usd_convert_cad_diagnostics.py",
    }
    require({safe_relative_path(str(item.get("path", ""))).as_posix() for item in skill_files if isinstance(item, dict)} == required_skill_paths, "skill_file_allowlist_path_set_mismatch")
    for item in skill_files:
        require(isinstance(item, dict), "skill_file_allowlist_entry_object_required")
        require(re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", ""))) is not None, f"skill_file_sha256_invalid:{item.get('path')}")
        require(isinstance(item.get("size_bytes"), int) and item["size_bytes"] > 0, f"skill_file_size_invalid:{item.get('path')}")
    require(isinstance(audit, dict), "usd_audit_required")
    require(audit.get("expected_up_axis") == "Z", "Z_up_required")
    require(audit.get("expected_meters_per_unit") == 0.001, "millimetre_stage_units_required")
    require(
        type(audit.get("bounds_relative_tolerance")) in (int, float)
        and math.isfinite(float(audit["bounds_relative_tolerance"]))
        and float(audit["bounds_relative_tolerance"]) == 0.01,
        "bounds_relative_tolerance_must_equal_0_01",
    )
    require(
        type(audit.get("bounds_absolute_tolerance_m")) in (int, float)
        and math.isfinite(float(audit["bounds_absolute_tolerance_m"]))
        and float(audit["bounds_absolute_tolerance_m"]) == 0.0001,
        "bounds_absolute_tolerance_must_equal_0_0001_m",
    )
    require(audit.get("physics_schema_count") == 0, "physics_must_be_absent")
    require(isinstance(output, dict), "output_contract_required")
    require(output.get("converted_family_count") == 6, "six_converted_families_required")
    require(
        isinstance(output.get("maximum_usd_size_bytes_per_family"), int)
        and 0 < output["maximum_usd_size_bytes_per_family"] <= 256 * 1024**2,
        "per_family_USD_size_limit_invalid",
    )
    require(
        isinstance(output.get("maximum_total_usd_size_bytes"), int)
        and output["maximum_usd_size_bytes_per_family"] <= output["maximum_total_usd_size_bytes"] <= 1024**3,
        "total_USD_size_limit_invalid",
    )
    require(output.get("property_assignment_intent") == "skip", "property_assignment_must_be_skipped")
    require(output.get("claim") == "conversion_only_minimum_openable_usd_not_simready", "conversion_only_claim_required")
    require(isinstance(gates, dict) and gates, "release_gates_required")
    require(set(gates) == REQUIRED_RELEASE_GATES, "release_gate_set_mismatch")
    require(all(value is False for value in gates.values()), "all_release_gates_must_remain_false")

    paths: set[str] = set()
    family_roles: dict[str, set[str]] = {family: set() for family in EXPECTED_FAMILIES}
    total_size = 0
    for item in allowlist:
        require(isinstance(item, dict), "allowlist_entry_object_required")
        path = safe_relative_path(str(item.get("path", ""))).as_posix()
        require(path not in paths, f"duplicate_allowlist_path:{path}")
        paths.add(path)
        role = item.get("role")
        require(role in {"step", "family_report", "cad_execution_report", "generation_log", "cad_preflight_report"}, f"invalid_allowlist_role:{path}")
        require(isinstance(item.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is not None, f"invalid_allowlist_sha256:{path}")
        require(isinstance(item.get("size_bytes"), int) and item["size_bytes"] >= 0, f"invalid_allowlist_size:{path}")
        total_size += item["size_bytes"]
        if role in {"step", "family_report"}:
            family = item.get("family_id")
            require(family in family_roles, f"invalid_allowlist_family:{path}")
            family_roles[family].add(role)
            expected_suffix = f"artifacts/{family}/step/{family}.step" if role == "step" else f"artifacts/{family}/cad-family-report.json"
            require(path == expected_suffix, f"unexpected_family_allowlist_path:{path}")
        else:
            require("family_id" not in item, f"non_family_entry_has_family:{path}")
            expected_non_family = {
                "cad_execution_report": "cad-execution-report.json",
                "generation_log": "logs/f35-cad-seed.log",
                "cad_preflight_report": "preflight/cad.json",
            }
            require(path == expected_non_family[role], f"unexpected_non_family_allowlist_path:{path}")
    require(all(roles == {"step", "family_report"} for roles in family_roles.values()), "each_family_requires_step_and_report")
    require(sum(1 for item in allowlist if item["role"] == "cad_execution_report") == 1, "one_cad_execution_report_required")
    require(sum(1 for item in allowlist if item["role"] == "generation_log") == 1, "one_generation_log_required")
    require(sum(1 for item in allowlist if item["role"] == "cad_preflight_report") == 1, "one_cad_preflight_report_required")
    require(total_size == source.get("imported_size_bytes"), "allowlist_total_size_mismatch")
    require(len(paths) == source.get("imported_file_count"), "allowlist_file_count_mismatch")
    return contract


def inspect_archive(archive_path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    info = regular_file(archive_path, "archive")
    source = contract["source"]
    require(info.st_size == source["archive_size_bytes"], f"archive_size_mismatch:{info.st_size}")
    archive_sha = sha256(archive_path)
    require(archive_sha == source["archive_sha256"], f"archive_sha256_mismatch:{archive_sha}")
    root = source["archive_root"]
    expected = {f"{root}/{item['path']}": item for item in contract["input_allowlist"]}
    found: dict[str, tarfile.TarInfo] = {}
    with tarfile.open(archive_path, mode="r:gz") as archive:
        for member in archive.getmembers():
            if member.name not in expected:
                continue
            require(member.name not in found, f"duplicate_archive_member:{member.name}")
            require(member.isreg() and not member.issym() and not member.islnk(), f"allowlisted_member_not_regular:{member.name}")
            require(member.size == expected[member.name]["size_bytes"], f"archive_member_size_mismatch:{member.name}:{member.size}")
            found[member.name] = member
        require(set(found) == set(expected), "archive_allowlist_member_set_mismatch")
        for name in sorted(found):
            stream = archive.extractfile(found[name])
            require(stream is not None, f"archive_member_unreadable:{name}")
            digest = hashlib.sha256()
            count = 0
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
                count += len(block)
            item = expected[name]
            require(count == item["size_bytes"], f"archive_member_read_size_mismatch:{name}:{count}")
            require(digest.hexdigest() == item["sha256"], f"archive_member_sha256_mismatch:{name}")
    return {
        "schema_version": "1.0.0",
        "phase": "F42a",
        "status": "passed_exact_F41_archive_allowlist_inspection",
        "source_revision": source["source_revision"],
        "archive": {
            "filename": archive_path.name,
            "sha256": archive_sha,
            "size_bytes": info.st_size,
            "run_id": source["run_id"],
        },
        "imported_file_count": len(found),
        "imported_size_bytes": sum(member.size for member in found.values()),
        "raw_scan_imported": False,
        "STL_imported": False,
        "3MF_imported": False,
        "release_gates": contract["release_gates"],
    }


def prepare_output_root(output_root: Path) -> Path:
    if output_root.exists():
        info = output_root.lstat()
        require(stat.S_ISDIR(info.st_mode) and not output_root.is_symlink(), f"output_root_must_be_real_directory:{output_root}")
        require(not any(output_root.iterdir()), f"output_root_must_be_empty:{output_root}")
    else:
        output_root.mkdir(parents=True)
    return output_root.resolve()


def extract_allowlist(archive_path: Path, output_root: Path, contract: dict[str, Any]) -> list[dict[str, Any]]:
    destination_root = output_root / "input" / contract["source"]["run_id"]
    root = contract["source"]["archive_root"]
    records: list[dict[str, Any]] = []
    with tarfile.open(archive_path, mode="r:gz") as archive:
        for item in contract["input_allowlist"]:
            member_name = f"{root}/{item['path']}"
            matches = [member for member in archive.getmembers() if member.name == member_name]
            require(len(matches) == 1, f"exactly_one_archive_member_required:{member_name}")
            member = matches[0]
            require(member.isreg() and member.size == item["size_bytes"], f"invalid_archive_member:{member_name}")
            source = archive.extractfile(member)
            require(source is not None, f"archive_member_unreadable:{member_name}")
            destination = destination_root.joinpath(*safe_relative_path(item["path"]).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp", delete=False) as stream:
                    temporary = Path(stream.name)
                    remaining = item["size_bytes"]
                    while remaining:
                        block = source.read(min(1024 * 1024, remaining))
                        require(block != b"", f"archive_member_truncated:{member_name}")
                        stream.write(block)
                        remaining -= len(block)
                    require(source.read(1) == b"", f"archive_member_larger_than_contract:{member_name}")
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(temporary, 0o444)
                os.replace(temporary, destination)
                temporary = None
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            require(sha256(destination) == item["sha256"], f"extracted_sha256_mismatch:{item['path']}")
            records.append({
                "path": destination.relative_to(output_root).as_posix(),
                "source_path": item["path"],
                "role": item["role"],
                "family_id": item.get("family_id"),
                "sha256": item["sha256"],
                "size_bytes": item["size_bytes"],
                "mode": "0444",
            })
    return records


def validate_f41_reports(input_root: Path, contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cad = read_json(input_root / "cad-execution-report.json")
    require(cad.get("phase") == "F41" and cad.get("runtime_phase") == "cad", "invalid_F41_cad_report_phase")
    require(cad.get("status") == "passed_six_hash_bound_F35_seed_families_generated_not_released", "unexpected_F41_cad_status")
    require(cad.get("target_variant") == "917_30_turbo_5374", "unexpected_F41_variant")
    require(cad.get("generated_family_count") == 6 and cad.get("blocked_family_count") == 132, "unexpected_F41_family_counts")
    require(cad.get("generated_format_counts") == {"3MF": 6, "STEP": 6, "STL": 6, "USD": 0}, "unexpected_F41_format_counts")
    require(cad.get("paid_instance_launched") is False, "F41_paid_instance_flag_must_be_false")
    require(cad.get("release_gates") == contract["release_gates"], "F41_release_gates_changed")
    reports = cad.get("family_reports")
    require(isinstance(reports, list) and len(reports) == 6, "six_F41_family_reports_required")
    by_family = {item.get("family_id"): item for item in reports if isinstance(item, dict)}
    require(set(by_family) == set(EXPECTED_FAMILIES), "F41_family_report_set_mismatch")
    source_triplets: set[tuple[str, str, str]] = set()
    allowlist_by_path = {item["path"]: item for item in contract["input_allowlist"]}
    for family in EXPECTED_FAMILIES:
        embedded = by_family[family]
        separate = read_json(input_root / f"artifacts/{family}/cad-family-report.json")
        require(separate == embedded, f"F41_family_report_copy_mismatch:{family}")
        require(embedded.get("manufacturing_released") is False, f"manufacturing_flag_must_be_false:{family}")
        require(embedded.get("simulation_validated") is False, f"simulation_flag_must_be_false:{family}")
        step_roundtrip = embedded.get("checks", {}).get("step_roundtrip", {})
        require(step_roundtrip.get("valid") is True, f"STEP_roundtrip_not_valid:{family}")
        require(step_roundtrip.get("manifold") is True, f"STEP_not_manifold:{family}")
        require(step_roundtrip.get("all_solids_positive_volume") is True, f"STEP_nonpositive_solid:{family}")
        bounds = step_roundtrip.get("bounds_size_mm")
        require(isinstance(bounds, list) and len(bounds) == 3 and all(isinstance(v, (int, float)) and v > 0 for v in bounds), f"invalid_STEP_bounds:{family}")
        expected_step = allowlist_by_path[f"artifacts/{family}/step/{family}.step"]
        actual_step = embedded.get("outputs", {}).get("STEP", {})
        require(actual_step.get("path") == expected_step["path"], f"STEP_path_mismatch:{family}")
        require(actual_step.get("sha256") == expected_step["sha256"], f"STEP_hash_mismatch:{family}")
        require(actual_step.get("size_bytes") == expected_step["size_bytes"], f"STEP_size_mismatch:{family}")
        triplet = (
            embedded.get("source_contract_sha256"),
            embedded.get("source_generator_sha256"),
            embedded.get("source_math_sha256"),
        )
        require(
            all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None for value in triplet),
            f"F41_source_hash_binding_invalid:{family}",
        )
        source_triplets.add(triplet)
    require(len(source_triplets) == 1, "F41_source_hash_binding_mismatch")

    preflight = read_json(input_root / "preflight/cad.json")
    require(preflight.get("status") == "passed", "F41_CAD_preflight_not_passed")
    require(preflight.get("geometry_generated") is False, "F41_preflight_geometry_flag_must_be_false")
    require(preflight.get("paid_instance_launched") is False, "F41_preflight_paid_flag_must_be_false")
    generation = read_json(input_root / "logs/f35-cad-seed.log")
    for key in ("physical_kinematics_ready", "manufacturing_geometry_ready", "engine_power_proven"):
        require(generation.get(key) is False, f"F35_generation_claim_must_be_false:{key}")
    expected_triplet = next(iter(source_triplets))
    require(generation.get("contract_sha256") == expected_triplet[0], "F35_generation_contract_hash_mismatch")
    return by_family


def require_skill_scripts(skill_root: Path, contract: dict[str, Any]) -> dict[str, Path]:
    try:
        info = skill_root.lstat()
    except FileNotFoundError as exc:
        raise F42aError(f"skill_root_missing:{skill_root}") from exc
    require(stat.S_ISDIR(info.st_mode) and not skill_root.is_symlink(), f"skill_root_must_be_real_directory:{skill_root}")
    allowed = {item["path"]: item for item in contract["runtime"]["skill_file_allowlist"]}
    for relative, expected in allowed.items():
        path = skill_root.joinpath(*safe_relative_path(relative).parts)
        info = regular_file(path, f"skill_allowlisted_file:{relative}")
        require(info.st_size == expected["size_bytes"], f"skill_file_size_mismatch:{relative}:{info.st_size}")
        require(sha256(path) == expected["sha256"], f"skill_file_sha256_mismatch:{relative}")
    scripts = {
        "preflight": skill_root / "references/preflight/scripts/preflight.py",
        "minimum": skill_root / "references/validate-usd-minimum/scripts/run.py",
    }
    for name, path in scripts.items():
        regular_file(path, f"skill_{name}_script")
    return scripts


def run_checked(command: list[str], *, environment: dict[str, str], label: str, timeout: int) -> None:
    try:
        completed = subprocess.run(command, env=environment, capture_output=True, text=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise F42aError(f"{label}_timeout:{timeout}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().replace("\n", " ")[-1000:]
        raise F42aError(f"{label}_failed:{completed.returncode}:{detail}")


def run_preflight(scripts: dict[str, Path], input_root: Path, output_root: Path, environment: dict[str, str]) -> Path:
    phase_root = output_root / "pipeline/00_preflight"
    report = phase_root / "cad-to-simready-preflight.json"
    markdown = phase_root / "cad-to-simready-preflight.md"
    phase_root.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(scripts["preflight"]),
        "--targets",
        "conversion,validation",
        "--source-asset",
        str(input_root / "artifacts/connecting_rod/step/connecting_rod.step"),
        "--output-root",
        str(output_root / "pipeline/01_conversion"),
        "--report",
        str(report),
        "--markdown-report",
        str(markdown),
        "--check-only",
        "--skip-content-agents",
        "--skip-deploy",
        "--no-update",
    ]
    run_checked(command, environment=environment, label="cad_to_simready_preflight", timeout=300)
    payload = read_json(report)
    require(payload.get("status") == "ready", "cad_to_simready_preflight_not_ready")
    targets = payload.get("targets")
    require(isinstance(targets, list) and set(targets) == {"conversion", "validation"}, "preflight_target_set_mismatch")
    return report


def output_file_evidence(path: Path, output_root: Path) -> dict[str, Any]:
    info = regular_file(path, "output")
    try:
        relative = path.resolve().relative_to(output_root.resolve()).as_posix()
    except ValueError as exc:
        raise F42aError(f"output_outside_root:{path}") from exc
    return {"path": relative, "sha256": sha256(path), "size_bytes": info.st_size}


def normalized_output_path(value: str, conversion_root: Path) -> Path:
    require(value != "", "converter_output_usd_path_missing")
    path = Path(value)
    path = path if path.is_absolute() else conversion_root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(conversion_root.resolve())
    except ValueError as exc:
        raise F42aError(f"converter_output_outside_family_root:{resolved}") from exc
    require(resolved.suffix.lower() in USD_SUFFIXES, f"unexpected_USD_suffix:{resolved.suffix}")
    regular_file(resolved, "converted_USD")
    return resolved


def close_enough(actual: float, expected: float, relative_tolerance: float, absolute_tolerance: float) -> bool:
    return math.isclose(actual, expected, rel_tol=relative_tolerance, abs_tol=absolute_tolerance)


def audit_minimum_report(report: dict[str, Any], family_report: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    require(report.get("passed") is True, "minimum_USD_validation_not_passed")
    metadata = report.get("metadata")
    require(isinstance(metadata, dict), "minimum_USD_metadata_required")
    audit = contract["usd_audit"]
    checks: dict[str, bool] = {
        "default_prim_valid": isinstance(metadata.get("default_prim_path"), str) and metadata["default_prim_path"].startswith("/"),
        "up_axis_Z": str(metadata.get("up_axis", "")).upper() == audit["expected_up_axis"],
        "meters_per_unit_0_001": isinstance(metadata.get("meters_per_unit"), (int, float)) and math.isclose(float(metadata["meters_per_unit"]), float(audit["expected_meters_per_unit"]), rel_tol=0.0, abs_tol=1e-12),
        "has_prims": isinstance(metadata.get("prim_count"), int) and metadata["prim_count"] > 0,
        "has_meshes": isinstance(metadata.get("mesh_count"), int) and metadata["mesh_count"] > 0,
        "used_layers_reported": isinstance(metadata.get("used_layers"), list) and len(metadata["used_layers"]) > 0,
        "no_rigid_bodies": metadata.get("rigid_body_count") == 0,
        "no_colliders": metadata.get("collider_count") == 0,
        "no_joints": metadata.get("joint_count") == 0,
    }
    expected_bounds = sorted(float(value) / 1000.0 for value in family_report["checks"]["step_roundtrip"]["bounds_size_mm"])
    actual_bounds_value = metadata.get("bounds", {}).get("meters", {}).get("size") if isinstance(metadata.get("bounds"), dict) else None
    actual_bounds = sorted(float(value) for value in actual_bounds_value) if isinstance(actual_bounds_value, list) and len(actual_bounds_value) == 3 else []
    checks["bounds_match_STEP"] = len(actual_bounds) == 3 and all(
        close_enough(actual, expected, float(audit["bounds_relative_tolerance"]), float(audit["bounds_absolute_tolerance_m"]))
        for actual, expected in zip(actual_bounds, expected_bounds)
    )
    failed = sorted(name for name, passed in checks.items() if not passed)
    require(not failed, f"USD_semantic_audit_failed:{','.join(failed)}")
    return {
        "schema_version": "1.0.0",
        "phase": "F42a",
        "status": "passed_conversion_only_minimum_USD_audit",
        "checks": checks,
        "expected_bounds_m_sorted": expected_bounds,
        "actual_bounds_m_sorted": actual_bounds,
        "material_assignment_status": "not_run",
        "physics_assignment_status": "not_run",
        "simulation_validated": False,
        "manufacturing_released": False,
    }


def run_family(
    family: str,
    family_report: dict[str, Any],
    scripts: dict[str, Path],
    converter_adapter: Path,
    input_root: Path,
    output_root: Path,
    environment: dict[str, str],
    contract: dict[str, Any],
) -> dict[str, Any]:
    source = input_root / f"artifacts/{family}/step/{family}.step"
    source_hash_before = sha256(source)
    conversion_root = output_root / "pipeline/01_conversion" / family
    conversion_report_path = conversion_root / "conversion.json"
    conversion_markdown_path = conversion_root / "conversion.md"
    adapter_report_path = conversion_root / "usd-convert-cad-adapter.json"
    adapter_log_path = conversion_root / "usd-convert-cad.log"
    output_usd = conversion_root / f"{family}.usd"
    conversion_root.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(converter_adapter),
        str(source),
        str(output_usd),
        "--report",
        str(adapter_report_path),
        "--log",
        str(adapter_log_path),
        "--up-axis",
        "z",
        "--quiet",
    ]
    run_checked(command, environment=environment, label=f"USD_conversion:{family}", timeout=2100)
    require(sha256(source) == source_hash_before, f"source_STEP_changed_during_conversion:{family}")
    adapter = read_json(adapter_report_path)
    require(adapter.get("status") == "passed" and not adapter.get("errors"), f"USD_conversion_report_has_errors:{family}")
    require(adapter.get("requested_up_axis") == "Z", f"converter_up_axis_not_Z:{family}")
    require(adapter.get("source_stable_during_conversion") is True, f"converter_source_stability_not_proven:{family}")
    require(adapter.get("atomic_output_commit") is True, f"converter_atomic_commit_not_proven:{family}")
    output_usd = normalized_output_path(str(adapter.get("output_usd", "")), conversion_root)
    require(
        0 < output_usd.stat().st_size <= contract["output_contract"]["maximum_usd_size_bytes_per_family"],
        f"converted_USD_size_outside_contract:{family}:{output_usd.stat().st_size}",
    )
    require(adapter.get("output_sha256") == sha256(output_usd), f"converter_output_hash_mismatch:{family}")
    conversion = {
        "schema_version": "1.0.0",
        "source_asset_path": str(source),
        "source_format": "cad",
        "converter_execution": "image_packaged_compatibility_adapter",
        "converter_adapter_path": str(converter_adapter),
        "converter_adapter_sha256": contract["runtime"]["converter_adapter"]["sha256"],
        "converter_reference": "usd-convert-cad",
        "converter_tool": str(adapter.get("converter", "usd-convert-cad")),
        "converter_command": command,
        "output_directory": str(conversion_root),
        "output_usd_path": str(output_usd),
        "generated_files": [str(output_usd), str(adapter_report_path), str(adapter_log_path)],
        "sidecar_inputs": [],
        "warnings": ["F42a uses the image-packaged usd-convert-cad compatibility adapter to force the 917 Z-up contract."],
        "errors": [],
        "next_step": "validate-usd-minimum",
    }
    atomic_json(conversion_report_path, conversion)
    atomic_text(conversion_markdown_path, "\n".join([
        "# Conversion Report",
        "",
        f"- Source asset: `{source}`",
        "- Source format: `cad`",
        "- Converter reference: `usd-convert-cad`",
        "- Requested up-axis: `Z`",
        f"- Output USD: `{output_usd}`",
        "- Next step: `validate-usd-minimum`",
        "",
    ]))

    minimum_root = output_root / "pipeline/02_minimum" / family
    minimum_root.mkdir(parents=True, exist_ok=True)
    minimum_report_path = minimum_root / "validate-usd-minimum.json"
    minimum_markdown_path = minimum_root / "validate-usd-minimum.md"
    command = [
        sys.executable,
        str(scripts["minimum"]),
        str(output_usd),
        "--next-step",
        "blocked_until_F42b_property_contract",
        "--report",
        str(minimum_report_path),
        "--markdown-report",
        str(minimum_markdown_path),
    ]
    run_checked(command, environment=environment, label=f"minimum_USD_validation:{family}", timeout=300)
    minimum = read_json(minimum_report_path)
    require(Path(str(minimum.get("asset_path", ""))).resolve() == output_usd, f"minimum_validator_asset_mismatch:{family}")
    audit = audit_minimum_report(minimum, family_report, contract)
    audit_path = output_root / "pipeline/03_audit" / family / "f42a-usd-family-audit.json"
    atomic_json(audit_path, audit)
    return {
        "family_id": family,
        "state": "generated_conversion_only_minimum_valid_not_simready_or_released",
        "source_STEP": output_file_evidence(source, output_root),
        "outputs": {
            "USD": output_file_evidence(output_usd, output_root),
            "conversion_report": output_file_evidence(conversion_report_path, output_root),
            "minimum_validation_report": output_file_evidence(minimum_report_path, output_root),
            "semantic_audit": output_file_evidence(audit_path, output_root),
        },
        "material_assignment_status": "not_run",
        "physics_assignment_status": "not_run",
        "simready_status": "not_run",
        "simulation_validated": False,
        "manufacturing_released": False,
    }


def final_markdown(report: dict[str, Any]) -> str:
    return "\n".join([
        "# F42a — conversion USD minimale des six STEP F41",
        "",
        f"- Statut : `{report['status']}`",
        f"- Archive F41 : `{report['source_archive']['sha256']}`",
        f"- Fichiers importés : `{report['imported_file_count']}` (`{report['imported_size_bytes']}` octets)",
        f"- USD minimum-valides : `{report['generated_family_count']}`",
        "- GPU : `non requis`",
        "- Matériaux, physique, assemblage et aperçu OVRTX : `non exécutés`",
        "- Simulation, fabrication, démarrage moteur et revendication 1600 ch : `non autorisés`",
        "",
        "Ce résultat valide uniquement la conversion et l'ouverture minimale des six prototypes USD.",
        "",
    ])


def execute(
    archive_path: Path,
    contract_path: Path,
    skill_root: Path,
    converter_adapter: Path,
    output_root: Path,
) -> dict[str, Any]:
    regular_file(contract_path, "contract")
    contract_hash_before = sha256(contract_path)
    contract = validate_contract(read_json(contract_path))
    require(
        contract["runtime"]["qualification_status"] == "qualified_public_linux_amd64_digest",
        "F42a_runtime_digest_qualification_pending",
    )
    require(
        os.environ.get("F42A_RUNTIME_IMAGE_REF") == contract["runtime"]["image_ref"],
        "exact_immutable_F42a_runtime_image_ref_not_reported",
    )
    require(
        os.environ.get("NVIDIA_VISIBLE_DEVICES") == "void"
        and os.environ.get("CUDA_VISIBLE_DEVICES") in {"", "-1"},
        "F42a_CPU_only_device_mask_not_enforced",
    )
    adapter_info = regular_file(converter_adapter, "usd_convert_cad_adapter")
    adapter_contract = contract["runtime"]["converter_adapter"]
    require(adapter_info.st_size == adapter_contract["size_bytes"], f"converter_adapter_size_mismatch:{adapter_info.st_size}")
    require(sha256(converter_adapter) == adapter_contract["sha256"], "converter_adapter_sha256_mismatch")
    inspection = inspect_archive(archive_path, contract)
    output_root = prepare_output_root(output_root)
    archive_hash_before = sha256(archive_path)
    imported = extract_allowlist(archive_path, output_root, contract)
    input_root = output_root / "input" / contract["source"]["run_id"]
    family_reports = validate_f41_reports(input_root, contract)
    input_manifest = {
        **inspection,
        "status": "passed_exact_F41_archive_allowlist_extracted_read_only",
        "contract_sha256": contract_hash_before,
        "files": imported,
    }
    atomic_json(output_root / "f42a-input-manifest.json", input_manifest)
    scripts = require_skill_scripts(skill_root, contract)
    safe_environment_names = {
        "HOME",
        "LANG",
        "LC_ALL",
        "LD_LIBRARY_PATH",
        "PATH",
        "PHYSICAL_AI_SIMREADY_VALIDATE_VENV",
        "PYTHONPATH",
        "USD_CONVERT_CAD_ROOT",
        "XDG_CACHE_HOME",
    }
    environment = {name: value for name, value in os.environ.items() if name in safe_environment_names}
    environment.update({
        "PHYSICAL_AI_REQUIRE_PREFLIGHT": "1",
        "PHYSICAL_AI_PREFLIGHT_MANIFEST": str(output_root / "pipeline/00_preflight/cad-to-simready-preflight.json"),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    preflight_path = run_preflight(scripts, input_root, output_root, environment)
    reports = [
        run_family(
            family,
            family_reports[family],
            scripts,
            converter_adapter,
            input_root,
            output_root,
            environment,
            contract,
        )
        for family in EXPECTED_FAMILIES
    ]
    total_usd_size = sum(item["outputs"]["USD"]["size_bytes"] for item in reports)
    require(
        total_usd_size <= contract["output_contract"]["maximum_total_usd_size_bytes"],
        f"total_USD_size_outside_contract:{total_usd_size}",
    )
    require_skill_scripts(skill_root, contract)
    require(sha256(converter_adapter) == adapter_contract["sha256"], "converter_adapter_changed_during_execution")
    require(sha256(contract_path) == contract_hash_before, "F42a_contract_changed_during_execution")
    require(sha256(archive_path) == archive_hash_before, "source_archive_changed_during_execution")
    report = {
        "schema_version": "1.0.0",
        "phase": "F42a",
        "status": "passed_six_hash_bound_F41_STEP_families_converted_to_minimum_USD_not_simready",
        "source_archive": inspection["archive"],
        "source_revision": inspection["source_revision"],
        "contract_sha256": contract_hash_before,
        "runtime_image_ref": contract["runtime"]["image_ref"],
        "generated_family_count": 6,
        "blocked_family_count": 132,
        "generated_format_counts": {"STEP": 0, "STL": 0, "3MF": 0, "USD": 6},
        "total_USD_size_bytes": total_usd_size,
        "imported_file_count": inspection["imported_file_count"],
        "imported_size_bytes": inspection["imported_size_bytes"],
        "family_reports": reports,
        "preflight_report": output_file_evidence(preflight_path, output_root),
        "six_imported_assets_minimum_valid": True,
        "all_138_families_minimum_valid": False,
        "property_assignment_intent": "skip",
        "preview_status": "not_run_until_separate_RTX_batch",
        "material_assignment_status": "not_run",
        "physics_assignment_status": "not_run",
        "assembly_status": "not_run",
        "simulation_validated": False,
        "manufacturing_authorized": False,
        "engine_start_authorized": False,
        "performance_1600_hp_claim_authorized": False,
        "paid_instance_launched": False,
        "release_gates": contract["release_gates"],
    }
    atomic_json(output_root / "usd-execution-report.json", report)
    atomic_json(output_root / "omniverse-cad-to-simready-report.json", report)
    atomic_text(output_root / "omniverse-cad-to-simready-report.md", final_markdown(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inspect", "run"))
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--skill-root", type=Path)
    parser.add_argument(
        "--converter-adapter",
        type=Path,
        default=Path("/opt/usd-convert-cad-preflight/convert.py"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    output_existed_before = args.output.exists() if args.output is not None else False
    try:
        contract = validate_contract(read_json(args.contract.resolve()))
        if args.command == "inspect":
            print(json.dumps(inspect_archive(args.archive.resolve(), contract), indent=2, sort_keys=True))
            return 0
        require(args.skill_root is not None, "--skill-root_required_for_run")
        require(args.output is not None, "--output_required_for_run")
        report = execute(
            args.archive.resolve(),
            args.contract.resolve(),
            args.skill_root.resolve(),
            args.converter_adapter.resolve(),
            args.output.resolve(),
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (F42aError, OSError, tarfile.TarError) as exc:
        if (
            args.output is not None
            and not output_existed_before
            and args.output.exists()
            and args.output.is_dir()
        ):
            atomic_json(args.output / "f42a-error.json", {
                "schema_version": "1.0.0",
                "phase": "F42a",
                "status": "blocked",
                "error": str(exc),
                "simulation_validated": False,
                "manufacturing_authorized": False,
                "engine_start_authorized": False,
                "performance_1600_hp_claim_authorized": False,
                "release_gates": contract.get("release_gates", {}) if "contract" in locals() else {},
            })
        print(f"F42a USD error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
