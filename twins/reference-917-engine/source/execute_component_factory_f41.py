#!/usr/bin/env python3
"""Execute the hash-bound F41 seed factory in explicit CAD and USD phases.

Only the six F35 rotating families whose contract, generator and math module
are bound by SHA-256 are eligible. Every other family stays blocked instead of
receiving placeholder geometry. CAD and USD phases intentionally use different
immutable runtimes.
"""

from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any
import uuid


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = REPO_ROOT / "twins/reference-917-engine/component-factory-f41.json"
DEFAULT_OUTPUT = REPO_ROOT / "work/917-component-factory-f41-execution"
TARGET_VARIANT = "917_30_turbo_5374"
F35_FAMILIES = (
    "crankshaft",
    "main_bearing_pair",
    "connecting_rod",
    "piston",
    "piston_pin",
    "piston_ring",
)
GENERATEABLE_FAMILIES = F35_FAMILIES
F35_HASH_BOUND_PATHS = {
    "contract": "twins/reference-917-engine/rotating-assembly-cad-f35.json",
    "generator": "twins/reference-917-engine/source/build_rotating_assembly_cad_f35.py",
    "math_module": "twins/reference-917-engine/source/rotating_assembly_f35_math.py",
}


class FactoryError(RuntimeError):
    """Fail-closed execution error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FactoryError(message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FactoryError(f"missing_input:{path}") from exc
    except json.JSONDecodeError as exc:
        raise FactoryError(f"invalid_json:{path}:{exc}") from exc
    require(isinstance(value, dict), f"json_object_required:{path}")
    return value


def write_json(path: Path, value: Any) -> None:
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
            stream.write(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
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
        raise FactoryError(f"missing_input:{path}") from exc
    return digest.hexdigest()


def resolve(project_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise FactoryError(f"path_outside_output_root:{path}") from exc


def file_evidence(path: Path, output_root: Path) -> dict[str, Any]:
    require(path.is_file(), f"expected_file_missing:{path}")
    return {
        "path": relative(path, output_root),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    }


def verify_f35_hash_bound_inputs(project_root: Path, contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    seeds = contract.get("prototype_seeds")
    require(isinstance(seeds, dict), "prototype_seeds_required")
    seed = seeds.get("f35_rotating")
    require(isinstance(seed, dict), "F35_seed_required")
    require(set(seed.get("families", [])) == set(F35_FAMILIES), "F35_seed_family_set_mismatch")
    require(seed.get("generator") == F35_HASH_BOUND_PATHS["generator"], "F35_generator_path_mismatch")
    inputs = seed.get("hash_bound_inputs")
    require(isinstance(inputs, list), "F35_hash_bound_inputs_required")
    require(len(inputs) == len(F35_HASH_BOUND_PATHS), "F35_hash_bound_input_count_mismatch")
    by_role: dict[str, dict[str, Any]] = {}
    for item in inputs:
        require(isinstance(item, dict), "F35_hash_bound_input_object_required")
        role = item.get("role")
        require(role in F35_HASH_BOUND_PATHS, f"F35_hash_bound_input_role_invalid:{role}")
        require(role not in by_role, f"F35_hash_bound_input_role_duplicate:{role}")
        expected_path = F35_HASH_BOUND_PATHS[role]
        require(item.get("path") == expected_path, f"F35_hash_bound_input_path_mismatch:{role}")
        actual = sha256(resolve(project_root, expected_path))
        require(actual == item.get("sha256"), f"F35_hash_bound_input_hash_mismatch:{role}:{actual}")
        by_role[role] = item
    require(set(by_role) == set(F35_HASH_BOUND_PATHS), "F35_hash_bound_input_role_set_mismatch")
    return by_role


def contract_and_policy(project_root: Path, contract_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = read_json(contract_path)
    require(contract.get("phase") == "F41", "expected_F41_contract")
    engine = contract.get("engine", {})
    require(engine.get("cylinder_count") == 12, "exactly_12_cylinders_required")
    require(engine.get("total_valve_count") == 48, "exactly_48_valves_required")
    executable = contract.get("executable_factory")
    require(isinstance(executable, dict), "executable_factory_required")
    require(executable.get("target_variant") == TARGET_VARIANT, "unexpected_target_variant")
    require(executable.get("generateable_family_count") == 6, "exactly_six_F35_seeded_families_required")
    require(executable.get("blocked_family_count_before_new_sources") == 132, "exactly_132_blocked_families_required")
    require(executable.get("generated_occurrence_coverage_if_successful") == 81, "F35_occurrence_coverage_must_be_81")
    require(set(executable["cad_runtime"]["families"]) == set(GENERATEABLE_FAMILIES), "cad_family_set_mismatch")
    require(set(executable["usd_runtime"]["families"]) == set(GENERATEABLE_FAMILIES), "usd_family_set_mismatch")
    require("f34_step_seed" not in executable, "F34_step_seed_must_not_be_executable")
    require(executable.get("raw_scan_in_bundle_allowed") is False, "raw_scan_must_be_forbidden")
    require(executable.get("private_absolute_path_in_bundle_allowed") is False, "private_paths_must_be_forbidden")
    verify_f35_hash_bound_inputs(project_root, contract)
    require(all(value is False for value in contract["release_gates"].values()), "release_gate_must_remain_false")
    return contract, executable


def preflight(project_root: Path, contract_path: Path, phase: str) -> dict[str, Any]:
    errors: list[str] = []
    checks: dict[str, Any] = {}
    try:
        contract, executable = contract_and_policy(project_root, contract_path)
        runtime = executable[f"{phase}_runtime"]
        requested_ref = runtime["image_ref"]
        actual_ref = os.environ.get("F41_RUNTIME_IMAGE_REF")
        checks["expected_image_ref"] = requested_ref
        checks["reported_runtime_image_ref"] = actual_ref
        if actual_ref != requested_ref:
            errors.append("exact_immutable_runtime_image_ref_not_reported")
        checks["platform"] = runtime["platform"]
        checks["network_required_during_job"] = runtime["network_required_during_job"]
        if runtime["platform"] != "linux/amd64":
            errors.append("runtime_platform_must_be_linux_amd64")
        if runtime["network_required_during_job"] is not False:
            errors.append("runtime_job_must_be_offline")

        bound_inputs = verify_f35_hash_bound_inputs(project_root, contract)
        checks["F35_hash_bound_inputs"] = [
            {"role": role, "path": bound_inputs[role]["path"], "sha256": bound_inputs[role]["sha256"]}
            for role in sorted(bound_inputs)
        ]

        if phase == "cad":
            try:
                import build123d  # noqa: F401

                checks["build123d_version"] = metadata.version("build123d")
                checks["lib3mf_available"] = hasattr(build123d, "Lib3MF") and hasattr(build123d, "Mesher")
                if checks["build123d_version"] != "0.11.1":
                    errors.append("build123d_version_mismatch")
                if not checks["lib3mf_available"]:
                    errors.append("build123d_3mf_runtime_missing")
            except (ImportError, metadata.PackageNotFoundError) as exc:
                errors.append(f"cad_runtime_missing:{type(exc).__name__}")
        elif phase == "usd":
            adapter = project_root / "containers/simready-preflight/convert.py"
            converter = Path("/opt/usd-convert-cad/bin/usd-convert-cad")
            checks["adapter_path"] = str(adapter)
            checks["converter_path"] = str(converter)
            if not adapter.is_file():
                errors.append("usd_conversion_adapter_missing")
            if not converter.is_file():
                errors.append("packaged_usd_converter_missing")
            try:
                from pxr import Usd  # noqa: F401
                checks["openusd_available"] = True
            except ImportError:
                checks["openusd_available"] = False
                errors.append("openusd_runtime_missing")
        else:
            errors.append(f"unsupported_phase:{phase}")
    except FactoryError as exc:
        errors.append(str(exc))

    return {
        "schema_version": "1.0.0",
        "phase": "F41",
        "runtime_phase": phase,
        "status": "passed" if not errors else "blocked",
        "checks": checks,
        "errors": errors,
        "geometry_generated": False,
        "paid_instance_launched": False,
    }


def require_preflight(project_root: Path, contract_path: Path, output_root: Path, phase: str) -> dict[str, Any]:
    report = preflight(project_root, contract_path, phase)
    write_json(output_root / "preflight" / f"{phase}.json", report)
    require(report["status"] == "passed", f"{phase}_preflight_blocked:{','.join(report['errors'])}")
    return report


def shape_metrics(shape: Any) -> dict[str, Any]:
    solids = list(shape.solids())
    bounds = shape.bounding_box()
    return {
        "valid": bool(shape.is_valid),
        "manifold": bool(shape.is_manifold),
        "solid_count": len(solids),
        "all_solids_positive_volume": bool(solids) and all(solid.volume > 0.0 for solid in solids),
        "volume_mm3": round(sum(solid.volume for solid in solids), 6),
        "bounds_size_mm": [round(float(value), 6) for value in (bounds.size.X, bounds.size.Y, bounds.size.Z)],
    }


def export_meshes_from_step(step: Path, stl: Path, three_mf: Path, family_id: str, *, keep_existing_stl: bool) -> dict[str, Any]:
    from build123d import Mesher, export_stl, import_step

    shape = import_step(step)
    metrics = shape_metrics(shape)
    require(metrics["valid"], f"invalid_step_shape:{family_id}")
    require(metrics["solid_count"] > 0, f"step_has_no_solids:{family_id}")
    require(metrics["all_solids_positive_volume"], f"step_has_nonpositive_solid:{family_id}")
    stl.parent.mkdir(parents=True, exist_ok=True)
    if not keep_existing_stl:
        export_stl(shape, stl, tolerance=0.10, angular_tolerance=0.14)
    require(stl.is_file() and stl.stat().st_size > 0, f"stl_not_generated:{family_id}")
    three_mf.parent.mkdir(parents=True, exist_ok=True)
    mesher = Mesher()
    # Mesher expands a Compound and applies one uuid to every child, which
    # violates the 3MF uniqueness rule for multi-solid STEP files.  Add each
    # solid explicitly with a stable, family-scoped UUID instead.
    for index, solid in enumerate(shape.solids(), start=1):
        mesher.add_shape(
            solid,
            linear_deflection=0.10,
            angular_deflection=0.14,
            part_number=f"{family_id}-{index:03d}",
            uuid_value=uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"https://3dprinting993/f41/{family_id}/solid/{index}",
            ),
        )
    mesher.write(three_mf)
    require(three_mf.is_file() and three_mf.stat().st_size > 0, f"3mf_not_generated:{family_id}")
    reader = Mesher()
    reopened = reader.read(three_mf)
    require(len(reopened) >= 1, f"3mf_roundtrip_has_no_shapes:{family_id}")
    reopened_solids = sum(len(item.solids()) for item in reopened)
    require(reopened_solids >= 1, f"3mf_roundtrip_has_no_solids:{family_id}")
    return {
        "step_roundtrip": metrics,
        "3mf_roundtrip_shape_count": len(reopened),
        "3mf_roundtrip_solid_count": reopened_solids,
    }


def execute_cad(project_root: Path, contract_path: Path, output_root: Path) -> dict[str, Any]:
    contract, executable = contract_and_policy(project_root, contract_path)
    require_preflight(project_root, contract_path, output_root, "cad")
    final_report = output_root / "cad-execution-report.json"
    require(not final_report.exists(), "cad_phase_already_executed_refusing_overwrite")
    artifacts_root = output_root / "artifacts"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    runtime_ref = executable["cad_runtime"]["image_ref"]
    bound_inputs = verify_f35_hash_bound_inputs(project_root, contract)
    f35_contract = resolve(project_root, bound_inputs["contract"]["path"])
    f35_generator = resolve(project_root, bound_inputs["generator"]["path"])
    f35_math = resolve(project_root, bound_inputs["math_module"]["path"])
    log_path = output_root / "logs/f35-cad-seed.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    family_reports: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="f41-cad-seed-", dir=output_root) as temporary:
        seed_output = Path(temporary) / "917-rotating-assembly-f35"
        environment = os.environ.copy()
        environment["F35_CAD_RUNTIME_IMAGE_REF"] = runtime_ref
        command = [
            sys.executable,
            str(f35_generator),
            "--contract",
            str(f35_contract),
            "--output",
            str(seed_output),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, env=environment, check=False)
        log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
        require(completed.returncode == 0, f"F35_seed_generation_failed:{completed.returncode}")
        seed_report = read_json(seed_output / TARGET_VARIANT / "geometry-report.json")
        require(seed_report.get("variant_id") == TARGET_VARIANT, "F35_target_variant_report_mismatch")
        require(seed_report.get("prototype_count") == 6, "F35_exactly_six_prototypes_required")
        require(seed_report.get("physical_mass_assignment_enabled") is False, "F35_physical_mass_assignment_forbidden")

        for family_id in F35_FAMILIES:
            family_root = artifacts_root / family_id
            step = family_root / "step" / f"{family_id}.step"
            stl = family_root / "stl" / f"{family_id}-display-only.stl"
            three_mf = family_root / "3mf" / f"{family_id}-prototype-only.3mf"
            step.parent.mkdir(parents=True, exist_ok=True)
            stl.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(seed_output / TARGET_VARIANT / "step" / f"{family_id}.step", step)
            shutil.copyfile(seed_output / TARGET_VARIANT / "stl" / f"{family_id}-display-only.stl", stl)
            metrics = export_meshes_from_step(step, stl, three_mf, family_id, keep_existing_stl=True)
            report = {
                "family_id": family_id,
                "state": "generated_research_seed_not_released",
                "source_seed": "F35_rotating_917_30_turbo_5374",
                "source_contract_sha256": sha256(f35_contract),
                "source_generator_sha256": sha256(f35_generator),
                "source_math_sha256": sha256(f35_math),
                "runtime_image_ref": runtime_ref,
                "outputs": {
                    "STEP": file_evidence(step, output_root),
                    "STL": file_evidence(stl, output_root),
                    "3MF": file_evidence(three_mf, output_root),
                },
                "checks": metrics,
                "manufacturing_released": False,
                "simulation_validated": False,
            }
            write_json(family_root / "cad-family-report.json", report)
            family_reports.append(report)

    family_reports.sort(key=lambda item: item["family_id"])

    report = {
        "schema_version": "1.0.0",
        "phase": "F41",
        "runtime_phase": "cad",
        "status": "passed_six_hash_bound_F35_seed_families_generated_not_released",
        "target_variant": TARGET_VARIANT,
        "planned_family_count": len(contract["families"]),
        "generateable_family_count": len(GENERATEABLE_FAMILIES),
        "generated_family_count": len(family_reports),
        "blocked_family_count": len(contract["families"]) - len(family_reports),
        "generated_format_counts": {"STEP": 6, "STL": 6, "3MF": 6, "USD": 0},
        "family_reports": family_reports,
        "source_generation_log": file_evidence(log_path, output_root),
        "release_gates": contract["release_gates"],
        "paid_instance_launched": False,
    }
    require(report["generated_family_count"] == 6, "cad_generated_family_count_mismatch")
    write_json(final_report, report)
    return report


def validate_usd(path: Path) -> dict[str, Any]:
    from pxr import Usd, UsdGeom

    stage = Usd.Stage.Open(str(path))
    require(stage is not None, f"usd_stage_cannot_open:{path}")
    prims = list(stage.TraverseAll())
    require(len(prims) > 0, f"usd_stage_has_no_prims:{path}")
    physics_findings: list[str] = []
    for prim in prims:
        type_name = prim.GetTypeName()
        if type_name.endswith("Joint") or type_name == "PhysicsScene":
            physics_findings.append(f"prim_type:{prim.GetPath()}:{type_name}")
        for schema in prim.GetAppliedSchemas():
            if any(token in str(schema) for token in ("RigidBody", "Collision", "MassAPI", "PhysicsMaterial")):
                physics_findings.append(f"schema:{prim.GetPath()}:{schema}")
    require(not physics_findings, f"unexpected_physics_schema:{path}")
    return {
        "prim_count": len(prims),
        "meters_per_unit": UsdGeom.GetStageMetersPerUnit(stage),
        "up_axis": UsdGeom.GetStageUpAxis(stage),
        "physics_schema_count": 0,
    }


def execute_usd(project_root: Path, contract_path: Path, output_root: Path) -> dict[str, Any]:
    contract, executable = contract_and_policy(project_root, contract_path)
    require_preflight(project_root, contract_path, output_root, "usd")
    final_report = output_root / "usd-execution-report.json"
    require(not final_report.exists(), "usd_phase_already_executed_refusing_overwrite")
    cad_report = read_json(output_root / "cad-execution-report.json")
    require(cad_report.get("generated_family_count") == 6, "cad_phase_six_F35_families_required")
    cad_by_family = {item["family_id"]: item for item in cad_report["family_reports"]}
    require(set(cad_by_family) == set(GENERATEABLE_FAMILIES), "cad_report_family_set_mismatch")
    adapter = project_root / "containers/simready-preflight/convert.py"
    runtime_ref = executable["usd_runtime"]["image_ref"]
    family_reports: list[dict[str, Any]] = []
    for family_id in sorted(GENERATEABLE_FAMILIES):
        family_root = output_root / "artifacts" / family_id
        source = family_root / "step" / f"{family_id}.step"
        expected_step_sha = cad_by_family[family_id]["outputs"]["STEP"]["sha256"]
        require(sha256(source) == expected_step_sha, f"cad_step_hash_mismatch:{family_id}")
        usd = family_root / "usd" / f"{family_id}.usd"
        conversion_report = family_root / "usd/conversion-report.json"
        conversion_log = family_root / "usd/conversion.log"
        usd.parent.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            str(adapter),
            str(source),
            str(usd),
            "--report",
            str(conversion_report),
            "--log",
            str(conversion_log),
            "--up-axis",
            "z",
            "--quiet",
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        require(completed.returncode == 0, f"usd_conversion_failed:{family_id}:{completed.returncode}")
        conversion = read_json(conversion_report)
        require(conversion.get("status") == "passed", f"usd_conversion_report_failed:{family_id}")
        require(conversion.get("output_sha256") == sha256(usd), f"usd_conversion_hash_mismatch:{family_id}")
        checks = validate_usd(usd)
        report = {
            "family_id": family_id,
            "state": "generated_conversion_only_not_simready_or_released",
            "source_step_sha256": expected_step_sha,
            "runtime_image_ref": runtime_ref,
            "outputs": {
                "USD": file_evidence(usd, output_root),
                "conversion_report": file_evidence(conversion_report, output_root),
                "conversion_log": file_evidence(conversion_log, output_root),
            },
            "minimum_checks": checks,
            "material_assignment_status": "not_run",
            "physics_assignment_status": "not_run",
            "simready_status": "not_run",
            "manufacturing_released": False,
            "simulation_validated": False,
        }
        write_json(family_root / "usd-family-report.json", report)
        family_reports.append(report)

    report = {
        "schema_version": "1.0.0",
        "phase": "F41",
        "runtime_phase": "usd",
        "status": "passed_six_F35_seed_families_converted_to_minimum_openable_usd_not_simready",
        "planned_family_count": len(contract["families"]),
        "generateable_family_count": 6,
        "generated_family_count": 6,
        "blocked_family_count": len(contract["families"]) - 6,
        "generated_format_counts": {"STEP": 0, "STL": 0, "3MF": 0, "USD": 6},
        "family_reports": family_reports,
        "release_gates": contract["release_gates"],
        "paid_instance_launched": False,
    }
    write_json(final_report, report)
    return report


def verify_evidence(path: Path, evidence: dict[str, Any], output_root: Path) -> None:
    require(path.is_file(), f"final_artifact_missing:{path}")
    require(relative(path, output_root) == evidence.get("path"), f"final_artifact_path_mismatch:{path}")
    require(sha256(path) == evidence.get("sha256"), f"final_artifact_hash_mismatch:{path}")
    require(path.stat().st_size == evidence.get("size_bytes"), f"final_artifact_size_mismatch:{path}")


def finalize(project_root: Path, contract_path: Path, output_root: Path) -> dict[str, Any]:
    contract, executable = contract_and_policy(project_root, contract_path)
    cad = read_json(output_root / "cad-execution-report.json")
    usd = read_json(output_root / "usd-execution-report.json")
    require(cad.get("generated_family_count") == 6, "finalize_requires_six_F35_cad_families")
    require(usd.get("generated_family_count") == 6, "finalize_requires_six_F35_usd_families")
    cad_by_family = {item["family_id"]: item for item in cad["family_reports"]}
    usd_by_family = {item["family_id"]: item for item in usd["family_reports"]}
    require(set(cad_by_family) == set(GENERATEABLE_FAMILIES), "finalize_cad_family_set_mismatch")
    require(set(usd_by_family) == set(GENERATEABLE_FAMILIES), "finalize_usd_family_set_mismatch")

    family_states: list[dict[str, Any]] = []
    family_by_id = {item["id"]: item for item in contract["families"]}
    for family_id in sorted(family_by_id):
        family = family_by_id[family_id]
        if family_id in GENERATEABLE_FAMILIES:
            cad_outputs = cad_by_family[family_id]["outputs"]
            usd_output = usd_by_family[family_id]["outputs"]["USD"]
            for key, suffix in (("STEP", ".step"), ("STL", ".stl"), ("3MF", ".3mf")):
                evidence = cad_outputs[key]
                path = output_root / evidence["path"]
                require(path.suffix.lower() == suffix, f"unexpected_format_suffix:{family_id}:{key}")
                verify_evidence(path, evidence, output_root)
            usd_path = output_root / usd_output["path"]
            require(usd_path.suffix.lower() == ".usd", f"unexpected_usd_suffix:{family_id}")
            verify_evidence(usd_path, usd_output, output_root)
            state = "generated_research_seed_all_authorized_formats_not_released"
            outputs = {**cad_outputs, "USD": usd_output}
        else:
            state = "blocked_missing_measurements_or_source"
            outputs = {}
        family_states.append({
            "family_id": family_id,
            "quantity": family.get("quantity"),
            "knowledge_classification": family["knowledge_classification"],
            "planned": True,
            "generateable": family_id in GENERATEABLE_FAMILIES,
            "state": state,
            "outputs": outputs,
            "manufacturing_released": False,
            "simulation_validated": False,
        })

    occurrence_coverage = sum(family_by_id[family_id].get("quantity") or 0 for family_id in GENERATEABLE_FAMILIES)
    require(occurrence_coverage == executable["generated_occurrence_coverage_if_successful"], "generated_occurrence_coverage_mismatch")
    report = {
        "schema_version": "1.0.0",
        "phase": "F41",
        "status": "passed_six_F35_seed_families_generated_132_families_blocked_not_engine_complete",
        "target_variant": TARGET_VARIANT,
        "planned_family_count": len(family_states),
        "generateable_family_count": 6,
        "generated_family_count": 6,
        "blocked_family_count": len(family_states) - 6,
        "known_occurrence_count": sum(item.get("quantity") or 0 for item in contract["families"]),
        "generated_occurrence_coverage": occurrence_coverage,
        "generated_format_counts": {"STEP": 6, "STL": 6, "3MF": 6, "USD": 6},
        "generated_geometry_is_research_seed_only": True,
        "engine_complete": False,
        "material_assignment_complete": False,
        "physics_assignment_complete": False,
        "simready_complete": False,
        "family_states": family_states,
        "release_gates": contract["release_gates"],
        "prohibited_claims": contract["prohibited_claims"],
        "paid_instance_launched": False,
    }
    require(report["planned_family_count"] == 138, "planned_family_count_mismatch")
    require(report["blocked_family_count"] == 132, "blocked_family_count_mismatch")
    require(all(value is False for value in report["release_gates"].values()), "final_release_gate_must_remain_false")
    write_json(output_root / "factory-final-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight-cad", "preflight-usd", "cad", "usd", "finalize"))
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    contract_path = args.contract.resolve()
    output_root = args.output.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    try:
        if args.command.startswith("preflight-"):
            phase = args.command.removeprefix("preflight-")
            report = preflight(project_root, contract_path, phase)
            write_json(output_root / "preflight" / f"{phase}.json", report)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0 if report["status"] == "passed" else 2
        if args.command == "cad":
            report = execute_cad(project_root, contract_path, output_root)
        elif args.command == "usd":
            report = execute_usd(project_root, contract_path, output_root)
        else:
            report = finalize(project_root, contract_path, output_root)
        print(json.dumps({
            key: report[key]
            for key in (
                "status",
                "planned_family_count",
                "generateable_family_count",
                "generated_family_count",
                "blocked_family_count",
                "generated_format_counts",
                "paid_instance_launched",
            )
            if key in report
        }, indent=2, sort_keys=True))
        return 0
    except FactoryError as exc:
        error_report = {
            "schema_version": "1.0.0",
            "phase": "F41",
            "status": "blocked",
            "command": args.command,
            "error": str(exc),
            "generated_claim_allowed": False,
            "paid_instance_launched": False,
        }
        write_json(output_root / f"{args.command}-error.json", error_report)
        print(json.dumps(error_report, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
