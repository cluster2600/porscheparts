#!/usr/bin/env python3
"""Résume sans écrasement les rapports baseline et les deux chaînes F10."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import tempfile


BASELINE_PHASES = ("readiness", "preflight", "f1", "f2", "f3")
DOWNSTREAM_PHASES = (
    "minimum-usd",
    "material",
    "physics",
    "conform",
    "validate-asset",
    "validate-geometry",
    "validate-physics",
    "validate-simready",
    "render-preview",
)
VALIDATION_PHASES = (
    "validate-asset",
    "validate-geometry",
    "validate-physics",
    "validate-simready",
)
VARIANTS = {
    "na": {
        "phase": "f10-type-912-4-5-na",
        "stage_suffix": "/type-912-4-5-na/stages/type-912-4-5-na-detail-f10.usda",
    },
    "turbo": {
        "phase": "f10-917-30-turbo-5374",
        "stage_suffix": "/917-30-turbo-5374/stages/917-30-turbo-5374-detail-f10.usda",
    },
}


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def expected_contract(job_id: str) -> tuple[dict[tuple[str, str], dict], dict[str, str]]:
    remote_root = PurePosixPath("/workspace/results") / job_id
    expected = {
        (job_id, "readiness"): {
            "output_directory": "readiness",
            "exact_outputs": [str(remote_root / "readiness" / job_id / "gpu-runtime.json")],
        },
        (job_id, "preflight"): {
            "output_directory": "preflight",
            "exact_outputs": [
                str(remote_root / "preflight" / job_id / "cad-to-simready-preflight.json"),
                str(remote_root / "preflight" / job_id / "cad-to-simready-preflight.env"),
                str(remote_root / "preflight" / job_id / "cad-to-simready-preflight.md"),
            ],
        },
        (job_id, "f1"): {
            "output_directory": "f1",
            "exact_outputs": [str(remote_root / "f1" / job_id / "stages/917-complete-engine-f1.usda")],
        },
        (job_id, "f2"): {
            "output_directory": "f2",
            "exact_outputs": [str(remote_root / "f2" / job_id / "stages/917-engine-kinematic-f2.usda")],
        },
        (job_id, "f3"): {
            "output_directory": "f3",
            "exact_outputs": [str(remote_root / "f3" / job_id / "stages/917-engine-detail-f3.usda")],
        },
    }
    run_ids = {name: f"{job_id}-{name}" for name in VARIANTS}
    for name, definition in VARIANTS.items():
        run_id = run_ids[name]
        f10_stage = str(remote_root / "f10" / run_id / "generated") + definition["stage_suffix"]
        expected[(run_id, definition["phase"])] = {
            "output_directory": "f10",
            "stage_suffix": definition["stage_suffix"],
            "exact_outputs": [f10_stage],
        }
        for phase in DOWNSTREAM_PHASES:
            if phase == "minimum-usd":
                output_directory = "f10"
            elif phase in VALIDATION_PHASES:
                output_directory = "conform"
            else:
                output_directory = phase
            expected[(run_id, phase)] = {"output_directory": output_directory}
        expected[(run_id, "minimum-usd")]["exact_outputs"] = [f10_stage]
        preview = str(remote_root / "render-preview" / run_id / "917-engine-simready-preview.png")
        expected[(run_id, "render-preview")]["exact_outputs"] = [preview, f"{preview}.sha256"]
    return expected, run_ids


def remote_report_path(job_id: str, run_id: str, phase: str) -> str:
    directory = "f10" if phase.startswith("f10-") else phase
    filename = "phase-f10.json" if phase.startswith("f10-") else f"phase-{phase}.json"
    return str(PurePosixPath("/workspace/results") / job_id / directory / run_id / filename)


def validate_remote_path(value: object, *, workspace_only: bool = True) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    path = PurePosixPath(value)
    if not path.is_absolute() or ".." in path.parts:
        return None
    if workspace_only and not path.is_relative_to(PurePosixPath("/workspace")):
        return None
    return str(path)


def validate_expected_report(
    item: dict,
    contract: dict,
    root: Path,
    job_id: str,
    instance_id: int,
    image: str,
) -> list[str]:
    errors: list[str] = []
    report = item["raw"]
    label = f"{item['run_id']}/{item['phase']}"
    expected_filename = "phase-f10.json" if item["phase"].startswith("f10-") else f"phase-{item['phase']}.json"
    expected_report = root / (
        "f10" if item["phase"].startswith("f10-") else item["phase"]
    ) / item["run_id"] / expected_filename
    if Path(item["report"]) != expected_report.resolve():
        errors.append(f"{label}: rapport hors de l'emplacement exact du run")
    if Path(item["report"]).name != expected_filename:
        errors.append(f"{label}: nom de rapport différent de {expected_filename}")
    if report.get("schema_version") != "1.0.0":
        errors.append(f"{label}: schema_version différent de 1.0.0")
    status = report.get("status")
    if status == "passed":
        exit_code = report.get("exit_code")
        if report.get("passed") is not True or type(exit_code) is not int or exit_code != 0:
            errors.append(f"{label}: passed exige passed=true et exit_code=0")
    elif status == "needs_rerun":
        exit_code = report.get("exit_code")
        if report.get("passed") is not False or type(exit_code) is not int or exit_code != 3:
            errors.append(f"{label}: needs_rerun exige passed=false et exit_code=3")
    else:
        errors.append(f"{label}: status doit être passed ou needs_rerun")
    control = report.get("control")
    if not isinstance(control, dict):
        errors.append(f"{label}: contrôle absent")
    else:
        if control.get("job_id") != job_id:
            errors.append(f"{label}: control.job_id différent")
        control_instance = control.get("instance_id")
        if type(control_instance) is not int or control_instance != instance_id:
            errors.append(f"{label}: control.instance_id différent")
        if control.get("expected_image") != image:
            errors.append(f"{label}: control.expected_image différent")

    for field in ("input_paths", "output_paths"):
        values = report.get(field)
        if not isinstance(values, list) or not all(validate_remote_path(value) for value in values):
            errors.append(f"{label}: {field} invalide")
    outputs = report.get("output_paths")
    if not isinstance(outputs, list) or not outputs or not all(isinstance(value, str) for value in outputs):
        errors.append(f"{label}: output_paths essentiel absent")
        return errors
    if len(outputs) != len(set(outputs)):
        errors.append(f"{label}: output_paths dupliqué")
    exact_outputs = contract.get("exact_outputs")
    if exact_outputs is not None and set(outputs) != set(exact_outputs):
        errors.append(f"{label}: output_paths différent du contrat exact")

    remote_job_root = PurePosixPath("/workspace/results") / job_id
    expected_output_root = remote_job_root / contract["output_directory"] / item["run_id"]
    for output in outputs:
        normalized = validate_remote_path(output)
        if normalized is None:
            continue
        remote = PurePosixPath(normalized)
        if not remote.is_relative_to(expected_output_root):
            errors.append(f"{label}: sortie hors du run ou de la phase attendue: {remote}")
            continue
        relative = remote.relative_to(remote_job_root)
        local = (root / Path(*relative.parts)).resolve()
        if not local.is_relative_to(root) or not local.is_file():
            errors.append(f"{label}: sortie absente de l'archive extraite: {remote}")
    return errors


def continuity_errors(indexed: dict[tuple[str, str], dict], job_id: str, run_ids: dict[str, str]) -> list[str]:
    errors: list[str] = []

    def item(run_id: str, phase: str) -> dict | None:
        return indexed.get((run_id, phase))

    def one_output(run_id: str, phase: str) -> str | None:
        current = item(run_id, phase)
        outputs = current.get("output_paths", []) if current else []
        if len(outputs) != 1:
            errors.append(f"{run_id}/{phase}: une sortie concrète unique est requise pour la continuité")
            return None
        return outputs[0]

    def require_inputs(run_id: str, phase: str, required: list[str | None]) -> None:
        current = item(run_id, phase)
        inputs = set(current.get("input_paths", [])) if current else set()
        for required_path in required:
            if required_path and required_path not in inputs:
                errors.append(f"{run_id}/{phase}: entrée amont absente: {required_path}")

    readiness_report = remote_report_path(job_id, job_id, "readiness")
    preflight_report = remote_report_path(job_id, job_id, "preflight")
    f1_report = remote_report_path(job_id, job_id, "f1")
    f2_report = remote_report_path(job_id, job_id, "f2")
    require_inputs(job_id, "preflight", [readiness_report])
    require_inputs(job_id, "f1", [preflight_report])
    f1_output = one_output(job_id, "f1")
    require_inputs(job_id, "f2", [f1_report, f1_output])
    f2_output = one_output(job_id, "f2")
    require_inputs(job_id, "f3", [f2_report, f2_output, preflight_report])

    for name, definition in VARIANTS.items():
        run_id = run_ids[name]
        f10_phase = definition["phase"]
        f10_report = remote_report_path(job_id, run_id, f10_phase)
        minimum_report = remote_report_path(job_id, run_id, "minimum-usd")
        material_report = remote_report_path(job_id, run_id, "material")
        physics_report = remote_report_path(job_id, run_id, "physics")
        conform_report = remote_report_path(job_id, run_id, "conform")
        require_inputs(run_id, f10_phase, [preflight_report])
        f10_output = one_output(run_id, f10_phase)
        minimum_output = one_output(run_id, "minimum-usd")
        require_inputs(run_id, "minimum-usd", [f10_report, f10_output])
        if f10_output and minimum_output != f10_output:
            errors.append(f"{run_id}/minimum-usd: la sortie doit être l'exact stage F10")
        material_prompt = f"/workspace/jobs/{job_id}/inputs/material-prompt.txt"
        physics_prompt = f"/workspace/jobs/{job_id}/inputs/physics-prompt.txt"
        require_inputs(run_id, "material", [minimum_report, f10_output, material_prompt])
        material_output = one_output(run_id, "material")
        require_inputs(run_id, "physics", [material_report, material_output, physics_prompt])
        physics_output = one_output(run_id, "physics")
        require_inputs(run_id, "conform", [physics_report, physics_output])
        conform_output = one_output(run_id, "conform")

        previous_report: str | None = None
        for phase in VALIDATION_PHASES:
            required = [conform_report, conform_output]
            if previous_report:
                required.append(previous_report)
            require_inputs(run_id, phase, required)
            validation_output = one_output(run_id, phase)
            if conform_output and validation_output != conform_output:
                errors.append(f"{run_id}/{phase}: l'USD validé doit être l'exact stage conforme")
            previous_report = remote_report_path(job_id, run_id, phase)
        require_inputs(run_id, "render-preview", [conform_report, conform_output, previous_report])
    return errors


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize(
    root: Path,
    archive: Path,
    job_id: str,
    instance_id: int,
    image: str,
) -> dict:
    root = root.resolve()
    archive = archive.resolve()
    expected, run_ids = expected_contract(job_id)
    indexed: dict[tuple[str, str], dict] = {}
    phase_reports: list[dict] = []
    duplicates: list[str] = []
    malformed: list[str] = []

    for path in sorted(root.rglob("phase-*.json")):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            malformed.append(str(path))
            continue
        phase = report.get("phase")
        run_id = path.parent.name
        phase_directory = path.parent.parent.name
        if not isinstance(phase, str) or not phase:
            malformed.append(str(path))
            continue
        expected_directory = "f10" if phase.startswith("f10-") else phase
        if phase_directory != expected_directory:
            malformed.append(str(path))
            continue
        item = {
            "run_id": run_id,
            "phase": phase,
            "status": report.get("status"),
            "passed": report.get("passed"),
            "exit_code": report.get("exit_code"),
            "report": str(path.resolve()),
            "input_paths": report.get("input_paths", []),
            "output_paths": report.get("output_paths", []),
            "control": report.get("control"),
            "raw": report,
        }
        phase_reports.append(item)
        key = (run_id, phase)
        if key in indexed:
            duplicates.append(f"{run_id}/{phase}")
            continue
        indexed[key] = item

    missing = sorted(f"{run_id}/{phase}" for run_id, phase in expected if (run_id, phase) not in indexed)
    report_contract_errors: list[str] = []
    contract_invalid: set[tuple[str, str]] = set()
    for key, contract in expected.items():
        if key in indexed:
            errors = validate_expected_report(indexed[key], contract, root, job_id, instance_id, image)
            if errors:
                contract_invalid.add(key)
                report_contract_errors.extend(errors)
    incomplete = sorted(
        f"{run_id}/{phase}"
        for (run_id, phase), item in indexed.items()
        if (run_id, phase) in expected
        and ((run_id, phase) in contract_invalid or item["status"] not in {"passed", "needs_rerun"})
    )
    needs_rerun = sorted(
        f"{run_id}/{phase}"
        for (run_id, phase), item in indexed.items()
        if (run_id, phase) in expected and item["status"] == "needs_rerun"
    )
    stage_errors: list[str] = []
    f10_stages: dict[str, str] = {}
    for name, definition in VARIANTS.items():
        run_id = run_ids[name]
        item = indexed.get((run_id, definition["phase"]))
        outputs = item.get("output_paths", []) if item else []
        if not isinstance(outputs, list):
            outputs = []
        matching = [str(value) for value in outputs if str(value).endswith(definition["stage_suffix"])]
        if len(matching) != 1:
            stage_errors.append(f"{run_id}/{definition['phase']}: stage de détail exact absent ou ambigu")
        else:
            f10_stages[name] = matching[0]
    if len(set(f10_stages.values())) != len(VARIANTS):
        stage_errors.append("les deux branches F10 ne prouvent pas deux stages distincts")

    continuity = (
        continuity_errors(indexed, job_id, run_ids)
        if not missing and not report_contract_errors
        else []
    )
    unexpected = sorted(
        f"{run_id}/{phase}" for run_id, phase in indexed if (run_id, phase) not in expected
    )
    retrieval_complete = not (
        missing
        or incomplete
        or duplicates
        or malformed
        or report_contract_errors
        or stage_errors
        or continuity
        or unexpected
    )
    validation_keys = {
        (run_ids[name], phase) for name in VARIANTS for phase in VALIDATION_PHASES
    }
    simulation_validated = bool(
        retrieval_complete
        and not needs_rerun
        and all(indexed[key]["status"] == "passed" for key in validation_keys)
    )
    indexed_payload = {
        f"{run_id}/{phase}": {key: value for key, value in item.items() if key != "raw"}
        for (run_id, phase), item in sorted(indexed.items())
    }
    phase_reports_payload = [
        {key: value for key, value in item.items() if key != "raw"}
        for item in phase_reports
    ]
    return {
        "schema_version": "1.0.0",
        "status": "complete" if retrieval_complete else "partial",
        "passed": True,
        "retrieval_attempted": True,
        "artifact_archive_verified": True,
        "retrieval_complete": retrieval_complete,
        "simulation_validated": simulation_validated,
        "job_id": job_id,
        "instance_id": int(instance_id),
        "expected_image": image,
        "archive_path": str(archive),
        "archive_sha256": sha256_file(archive),
        "extracted_root": str(root),
        "expected_pipelines": {
            "baseline_run_id": job_id,
            "f10_run_ids": run_ids,
            "required_report_count": len(expected),
        },
        "f10_detail_stages": f10_stages,
        "phases": indexed_payload,
        "phase_reports": phase_reports_payload,
        "missing_phases": missing,
        "incomplete_phases": incomplete,
        "duplicate_reports": sorted(set(duplicates)),
        "malformed_reports": malformed,
        "report_contract_errors": report_contract_errors,
        "f10_stage_errors": stage_errors,
        "continuity_errors": continuity,
        "unexpected_reports": unexpected,
        "needs_rerun_phases": needs_rerun,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--instance-id", type=int, required=True)
    parser.add_argument("--expected-image", required=True)
    args = parser.parse_args()
    payload = summarize(args.root, args.archive, args.job_id, args.instance_id, args.expected_image)
    atomic_json(args.output.resolve(), payload)
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
