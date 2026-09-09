#!/usr/bin/env python3
"""Vérifie la récupération fermée des six branches F42b sans élargir les claims."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import tempfile
from typing import Any


WORKFLOW_PROFILE = "f42b-six-usd-v1"
FAMILIES = (
    "connecting_rod",
    "crankshaft",
    "main_bearing_pair",
    "piston",
    "piston_pin",
    "piston_ring",
)
FAMILY_PHASES = (
    "minimum-usd",
    "material",
    "physics",
    "conform",
    "validate-asset",
    "validate-geometry",
    "validate-physics",
    "render-preview",
)
TOP_LEVEL_VALIDATORS = (
    "validate-asset",
    "validate-geometry",
    "validate-physics",
)
CANONICAL = {
    "connecting_rod": {
        "size_bytes": 22222,
        "sha256": "f995b603ec6d6b467e87b2ad26913e402b864bee10736fca16a65612260d1ec8",
        "default_prim_path": "/connecting_rod",
    },
    "crankshaft": {
        "size_bytes": 40439,
        "sha256": "20be6e2ff0afe25bde546148833d51d7546a7e50d9abe75e963808c472292cf1",
        "default_prim_path": "/crankshaft",
    },
    "main_bearing_pair": {
        "size_bytes": 15091,
        "sha256": "aaa12a2eb966a506be21f9f44733dac3edb4c5d399441a2d9a8fbfd44b657a33",
        "default_prim_path": "/main_bearing_pair",
    },
    "piston": {
        "size_bytes": 65639,
        "sha256": "95a4c5ef57c87af25e12a5784ced63c6fd88b3199f86213903ad2e03d05506df",
        "default_prim_path": "/piston",
    },
    "piston_pin": {
        "size_bytes": 11219,
        "sha256": "fefe43fdabd8b7eea63bf7b8e191f02eac2f4be28c538c644f76a63da526934d",
        "default_prim_path": "/piston_pin",
    },
    "piston_ring": {
        "size_bytes": 12156,
        "sha256": "a0f7bba825e4e3f9e3faae2d1318584d99ab836da0d224ab35039b4c0a7a1aa3",
        "default_prim_path": "/piston_ring",
    },
}
VISUAL_ASSIGNMENTS = {
    "connecting_rod": "titanium",
    "crankshaft": "steel",
    "main_bearing_pair": "steel",
    "piston": "light_alloy",
    "piston_pin": "steel",
    "piston_ring": "steel",
}
VISUAL_PALETTE = {
    "light_alloy": {"diffuse_color": [0.42, 0.47, 0.52], "metallic": 0.75, "roughness": 0.32},
    "steel": {"diffuse_color": [0.22, 0.25, 0.28], "metallic": 0.9, "roughness": 0.28},
    "titanium": {"diffuse_color": [0.32, 0.36, 0.4], "metallic": 0.85, "roughness": 0.38},
}
VISUAL_SOURCE_SHA256 = "41556bd0bce1bfac59fcafb046d0c168a68ae45e228141b6f9c8608ea01e95f3"
HISTORICAL_STATUSES = {
    "connecting_rod": "documentary_variant_context_not_grade_or_process_qualification",
    "crankshaft": "forging_documented_but_alloy_family_not_primary_source_qualified",
    "main_bearing_pair": "unknown",
    "piston": "documentary_variant_context_not_grade_or_process_qualification",
    "piston_pin": "unknown",
    "piston_ring": "unknown",
}
NVIDIA_VALIDATOR_SKILLS = {
    "validate-asset": "omni-asset-validate",
    "validate-geometry": "omni-asset-validate-geometry",
    "validate-physics": "omni-asset-validate-physics",
    "validate-simready": "simready-validate",
}
VALIDATION_FINDING_STATUSES = {"FAIL", "FAILED", "FAILURE"}
FALSE_CLAIMS = (
    "simulation_executed",
    "simulation_validated",
    "physical_simulation_validated",
    "physicsnemo_simulation_executed",
    "fea_executed",
    "fea_validated",
    "dyno_validated",
    "manufacturing_authorized",
    "manufacturing_released",
    "performance_claim_authorized",
    "performance_1600hp_validated",
    "performance_1600_hp_claim_authorized",
    "engine_start_authorized",
    "engine_installation_authorized",
    "installation_in_993_authorized",
)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def private_destination_policy(archive: Path) -> dict[str, Any]:
    helper_path = Path(__file__).resolve().with_name("_private_destination.py")
    spec = importlib.util.spec_from_file_location("f42b_private_destination", helper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("helper de destination privée F42b indisponible")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    repository_root = Path(__file__).resolve().parents[3]
    destination = module.prepare_destination(archive.parent, repository_root)
    info = destination.lstat()
    return {
        "passed": True,
        "destination_root": str(destination),
        "outside_git_worktree": True,
        "owner_uid": info.st_uid,
        "mode": "0700",
        "symlink": False,
    }


def expected_contract(job_id: str) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, str]]:
    remote_root = PurePosixPath("/workspace/results") / job_id
    expected: dict[tuple[str, str], dict[str, Any]] = {
        (job_id, "readiness"): {
            "output_directories": ("readiness",),
            "exact_outputs": [str(remote_root / "readiness" / job_id / "gpu-runtime.json")],
        },
        (job_id, "preflight"): {
            "output_directories": ("preflight",),
            "exact_outputs": [
                str(remote_root / "preflight" / job_id / "cad-to-simready-preflight.json"),
                str(remote_root / "preflight" / job_id / "cad-to-simready-preflight.env"),
                str(remote_root / "preflight" / job_id / "cad-to-simready-preflight.md"),
            ],
        },
    }
    run_ids = {family: f"{job_id}-{family}" for family in FAMILIES}
    for family, run_id in run_ids.items():
        for phase in FAMILY_PHASES:
            output_directories = ("conform",) if phase in TOP_LEVEL_VALIDATORS else (phase,)
            expected[(run_id, phase)] = {
                "family_id": family,
                "output_directories": output_directories,
            }
        expected[(run_id, "minimum-usd")]["exact_outputs"] = [
            str(remote_root / "minimum-usd" / run_id / "output" / f"{family}.usd")
        ]
        render_root = remote_root / "render-preview" / run_id
        expected[(run_id, "render-preview")]["exact_outputs"] = [
            str(render_root / f"{family}-simready-preview.png"),
            str(render_root / "photos" / f"{family}-front.png"),
            str(render_root / "photos" / f"{family}-right.png"),
            str(render_root / "photos" / f"{family}-rear.png"),
            str(render_root / "photos" / f"{family}-left.png"),
            str(render_root / f"{family}-simready-turntable.mp4"),
            str(render_root / "render-media.sha256"),
        ]
    if len(expected) != 50:
        raise AssertionError("le contrat F42b doit contenir exactement 50 rapports top-level")
    return expected, run_ids


def remote_report_path(job_id: str, run_id: str, phase: str) -> str:
    return str(
        PurePosixPath("/workspace/results")
        / job_id
        / phase
        / run_id
        / f"phase-{phase}.json"
    )


def validate_remote_path(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    path = PurePosixPath(value)
    if not path.is_absolute() or ".." in path.parts or not path.is_relative_to(PurePosixPath("/workspace")):
        return None
    return str(path)


def local_artifact(root: Path, job_id: str, remote_value: object) -> Path | None:
    normalized = validate_remote_path(remote_value)
    if normalized is None:
        return None
    remote = PurePosixPath(normalized)
    remote_job_root = PurePosixPath("/workspace/results") / job_id
    if not remote.is_relative_to(remote_job_root):
        return None
    relative = remote.relative_to(remote_job_root)
    local = root.joinpath(*relative.parts)
    try:
        info = local.lstat()
        resolved = local.resolve(strict=True)
    except OSError:
        return None
    if local.is_symlink() or not resolved.is_relative_to(root) or not info.st_size or not local.is_file():
        return None
    return resolved


def load_child_json(
    root: Path,
    job_id: str,
    remote_value: str,
    errors: list[str],
    label: str,
) -> dict[str, Any] | None:
    local = local_artifact(root, job_id, remote_value)
    if local is None:
        errors.append(f"{label}: rapport enfant absent ou non sûr: {remote_value}")
        return None
    try:
        payload = json.loads(local.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        errors.append(f"{label}: JSON enfant illisible: {remote_value}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{label}: JSON enfant doit être un objet: {remote_value}")
        return None
    return payload


def reference_passed(payload: dict[str, Any]) -> bool:
    return payload.get("passed") is True and str(payload.get("status", "passed")).lower() in {
        "pass",
        "passed",
        "ready",
    }


def reference_applies_to(payload: dict[str, Any], asset: str) -> bool:
    if payload.get("output_paths") == [asset]:
        return True
    return any(payload.get(key) == asset for key in ("asset_path", "output_usd_path", "stage"))


def conform_reference_valid(payload: dict[str, Any], asset: str) -> bool:
    return (
        reference_passed(payload)
        and reference_applies_to(payload, asset)
        and payload.get("profile") == "Prop-Robotics-Physx"
        and payload.get("profile_version") == "1.0.0"
    )


def nvidia_validation_outcome(
    payload: dict[str, Any], asset: str, validator_skill: str
) -> str | None:
    if payload.get("validator_skill") != validator_skill or payload.get("asset_path") != asset:
        return None
    status = str(payload.get("status", "")).upper()
    if payload.get("passed") is True:
        if status != "PASS" or payload.get("errors") not in (None, []):
            return None
        issues = payload.get("issues", [])
        counts = payload.get("issue_counts", {})
        if (
            not isinstance(issues, list)
            or any(
                isinstance(issue, dict)
                and str(issue.get("severity", "")).upper() in {"ERROR", "FAILURE"}
                for issue in issues
            )
            or not isinstance(counts, dict)
            or any(type(counts.get(key, 0)) is not int or counts.get(key, 0) != 0 for key in ("ERROR", "FAILURE"))
        ):
            return None
        return "passed"
    if payload.get("passed") is not False or status not in VALIDATION_FINDING_STATUSES:
        return None
    issues = payload.get("issues")
    if not isinstance(issues, list) or not issues:
        return None
    failing = [
        issue for issue in issues
        if isinstance(issue, dict)
        and str(issue.get("severity", "")).upper() in {"ERROR", "FAILURE"}
    ]
    errors = payload.get("errors")
    counts = payload.get("issue_counts")
    if (
        not failing
        or not isinstance(errors, list)
        or not errors
        or not isinstance(counts, dict)
        or any(type(counts.get(key, 0)) is not int for key in ("ERROR", "FAILURE"))
        or sum(counts.get(key, 0) for key in ("ERROR", "FAILURE")) < len(failing)
    ):
        return None
    return "needs_rerun"


def false_claim_errors(payload: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []

    def visit(value: object, location: str) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                nested_location = f"{location}.{key}"
                if key in FALSE_CLAIMS and nested is not False:
                    errors.append(f"{label}: claim interdit différent de false: {nested_location}")
                visit(nested, nested_location)
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                visit(nested, f"{location}[{index}]")

    visit(payload, "$")
    return errors


def validate_expected_report(
    item: dict[str, Any],
    contract: dict[str, Any],
    root: Path,
    job_id: str,
    instance_id: int,
    image: str,
) -> list[str]:
    errors: list[str] = []
    report = item["raw"]
    run_id = item["run_id"]
    phase = item["phase"]
    label = f"{run_id}/{phase}"
    expected_report = root / phase / run_id / f"phase-{phase}.json"
    if Path(item["report"]) != expected_report.resolve():
        errors.append(f"{label}: rapport hors de l'emplacement exact")
    if report.get("schema_version") != "1.0.0" or report.get("phase") != phase:
        errors.append(f"{label}: identité/schema du rapport invalide")
    status = report.get("status")
    exit_code = report.get("exit_code")
    if status == "passed":
        if report.get("passed") is not True or type(exit_code) is not int or exit_code != 0:
            errors.append(f"{label}: passed exige passed=true et exit_code=0")
    elif status == "needs_rerun":
        if report.get("passed") is not False or type(exit_code) is not int or exit_code != 3:
            errors.append(f"{label}: needs_rerun exige passed=false et exit_code=3")
        if phase not in TOP_LEVEL_VALIDATORS:
            errors.append(
                f"{label}: needs_rerun réservé aux trois validateurs NVIDIA diagnostiques"
            )
    else:
        errors.append(f"{label}: status doit être passed ou needs_rerun")
    control = report.get("control")
    if not isinstance(control, dict):
        errors.append(f"{label}: contrôle absent")
    else:
        if control.get("job_id") != job_id:
            errors.append(f"{label}: control.job_id différent")
        if type(control.get("instance_id")) is not int or control.get("instance_id") != instance_id:
            errors.append(f"{label}: control.instance_id différent")
        if control.get("expected_image") != image:
            errors.append(f"{label}: control.expected_image différent")
    for field in ("input_paths", "output_paths", "child_reports"):
        values = report.get(field)
        if not isinstance(values, list) or not all(validate_remote_path(value) for value in values):
            errors.append(f"{label}: {field} invalide")
        elif len(values) != len(set(values)):
            errors.append(f"{label}: {field} contient des doublons")
    outputs = report.get("output_paths")
    if not isinstance(outputs, list) or not outputs:
        errors.append(f"{label}: aucune sortie essentielle")
        return errors
    exact_outputs = contract.get("exact_outputs")
    if exact_outputs is not None and outputs != exact_outputs:
        errors.append(f"{label}: sorties différentes du contrat exact et ordonné")
    remote_root = PurePosixPath("/workspace/results") / job_id
    allowed_roots = [remote_root / directory / run_id for directory in contract["output_directories"]]
    for output in outputs:
        normalized = validate_remote_path(output)
        if normalized is None:
            continue
        remote = PurePosixPath(normalized)
        if not any(remote.is_relative_to(allowed) for allowed in allowed_roots):
            errors.append(f"{label}: sortie hors du run/phase: {remote}")
        elif local_artifact(root, job_id, normalized) is None:
            errors.append(f"{label}: sortie absente de l'archive: {remote}")
    expected_child_root = remote_root / phase / run_id
    for child in report.get("child_reports", []):
        normalized = validate_remote_path(child)
        if normalized is None:
            continue
        remote = PurePosixPath(normalized)
        if not remote.is_relative_to(expected_child_root):
            errors.append(f"{label}: enfant hors du répertoire de phase: {remote}")
        elif local_artifact(root, job_id, normalized) is None:
            errors.append(f"{label}: enfant absent de l'archive: {remote}")
    timestamps: dict[str, datetime] = {}
    for field in ("started_at", "finished_at"):
        value = report.get(field)
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            errors.append(f"{label}: horodatage {field} invalide")
            continue
        if parsed.tzinfo is None:
            errors.append(f"{label}: horodatage {field} sans fuseau")
        else:
            timestamps[field] = parsed
    if (
        "started_at" in timestamps
        and "finished_at" in timestamps
        and timestamps["finished_at"] < timestamps["started_at"]
    ):
        errors.append(f"{label}: durée de phase négative")
    return errors


def continuity_errors(
    indexed: dict[tuple[str, str], dict[str, Any]],
    job_id: str,
    run_ids: dict[str, str],
) -> tuple[list[str], dict[str, dict[str, str]]]:
    errors: list[str] = []
    stages: dict[str, dict[str, str]] = {family: {} for family in FAMILIES}

    def item(run_id: str, phase: str) -> dict[str, Any] | None:
        return indexed.get((run_id, phase))

    def one_output(run_id: str, phase: str) -> str | None:
        current = item(run_id, phase)
        outputs = current.get("output_paths", []) if current else []
        if len(outputs) != 1:
            errors.append(f"{run_id}/{phase}: une sortie USD unique est requise")
            return None
        return outputs[0]

    def require_inputs(run_id: str, phase: str, required: list[str | None]) -> None:
        current = item(run_id, phase)
        inputs = set(current.get("input_paths", [])) if current else set()
        for path in required:
            if path and path not in inputs:
                errors.append(f"{run_id}/{phase}: entrée amont absente: {path}")

    readiness_report = remote_report_path(job_id, job_id, "readiness")
    preflight_report = remote_report_path(job_id, job_id, "preflight")
    require_inputs(job_id, "preflight", [readiness_report])
    contract = f"/workspace/jobs/{job_id}/project/twins/reference-917-engine/component-factory-f42b-gpu.json"
    material_prompt = f"/workspace/jobs/{job_id}/inputs/material-prompt.txt"
    physics_prompt = f"/workspace/jobs/{job_id}/inputs/physics-prompt.txt"
    for family, run_id in run_ids.items():
        source = f"/workspace/jobs/{job_id}/inputs/f42a-usd/{family}.usd"
        minimum_report = remote_report_path(job_id, run_id, "minimum-usd")
        material_report = remote_report_path(job_id, run_id, "material")
        physics_report = remote_report_path(job_id, run_id, "physics")
        conform_report = remote_report_path(job_id, run_id, "conform")
        require_inputs(run_id, "minimum-usd", [contract, source])
        minimum = one_output(run_id, "minimum-usd")
        stages[family]["minimum-usd"] = minimum or ""
        context = str(
            PurePosixPath("/workspace/results")
            / job_id
            / "minimum-usd"
            / run_id
            / "asset-context.json"
        )
        input_audit = str(
            PurePosixPath("/workspace/results")
            / job_id
            / "minimum-usd"
            / run_id
            / "f42b-input-audit.json"
        )
        require_inputs(
            run_id,
            "material",
            [contract, minimum_report, minimum, source, context, input_audit, material_prompt],
        )
        material = one_output(run_id, "material")
        stages[family]["material"] = material or ""
        material_audit = str(
            PurePosixPath("/workspace/results")
            / job_id
            / "material"
            / run_id
            / "f42b-material-audit.json"
        )
        require_inputs(
            run_id,
            "physics",
            [contract, material_report, material, source, context, material_audit, physics_prompt],
        )
        physics = one_output(run_id, "physics")
        stages[family]["physics"] = physics or ""
        require_inputs(run_id, "conform", [physics_report, physics])
        conform = one_output(run_id, "conform")
        stages[family]["conform"] = conform or ""
        previous: str | None = None
        for phase in TOP_LEVEL_VALIDATORS:
            required = [conform_report, conform]
            if previous:
                required.append(previous)
            require_inputs(run_id, phase, required)
            validated = one_output(run_id, phase)
            if conform and validated != conform:
                errors.append(f"{run_id}/{phase}: le validateur doit viser l'exact USD conforme")
            previous = remote_report_path(job_id, run_id, phase)
        require_inputs(
            run_id,
            "render-preview",
            [conform_report, conform, previous],
        )

    for stage in ("minimum-usd", "material", "physics", "conform"):
        paths = [stages[family].get(stage) for family in FAMILIES]
        if any(not path for path in paths) or len(set(paths)) != len(FAMILIES):
            errors.append(f"{stage}: les six branches ne prouvent pas six USD distincts")
    return errors, stages


def chronological_errors(
    indexed: dict[tuple[str, str], dict[str, Any]], job_id: str, run_ids: dict[str, str]
) -> list[str]:
    errors: list[str] = []

    def moment(run_id: str, phase: str, field: str) -> datetime | None:
        item = indexed.get((run_id, phase))
        value = item.get("raw", {}).get(field) if item else None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
        return parsed if parsed.tzinfo else None

    readiness_finished = moment(job_id, "readiness", "finished_at")
    preflight_started = moment(job_id, "preflight", "started_at")
    if readiness_finished and preflight_started and readiness_finished > preflight_started:
        errors.append("readiness/preflight: ordre temporel inversé")
    preflight_finished = moment(job_id, "preflight", "finished_at")
    for family, run_id in run_ids.items():
        sequence = list(FAMILY_PHASES)
        if preflight_finished:
            first_started = moment(run_id, sequence[0], "started_at")
            if first_started and preflight_finished > first_started:
                errors.append(f"{run_id}: minimum exécuté avant la fin du preflight")
        for previous, current in zip(sequence, sequence[1:], strict=False):
            previous_finished = moment(run_id, previous, "finished_at")
            current_started = moment(run_id, current, "started_at")
            if previous_finished and current_started and previous_finished > current_started:
                errors.append(f"{run_id}: ordre temporel inversé {previous}->{current}")
    for previous_family, current_family in zip(FAMILIES[:-1], FAMILIES[1:], strict=True):
        previous_finished = moment(
            run_ids[previous_family], "render-preview", "finished_at"
        )
        current_started = moment(
            run_ids[current_family], "minimum-usd", "started_at"
        )
        if previous_finished and current_started and previous_finished > current_started:
            errors.append(
                f"ordre séquentiel inversé: {previous_family}->{current_family}"
            )
    return errors


def validate_pilot_runtime_gate(
    indexed: dict[tuple[str, str], dict[str, Any]],
    root: Path,
    job_id: str,
    run_ids: dict[str, str],
) -> tuple[list[str], dict[str, Any]]:
    """Atteste le pilote complet et sa projection, hors compteur phase-* de 50."""

    errors: list[str] = []
    remote_path = str(
        PurePosixPath("/workspace/results")
        / job_id
        / "pilot-gate"
        / job_id
        / "f42b-pilot-runtime-gate.json"
    )
    gate = load_child_json(root, job_id, remote_path, errors, "pilot-runtime-gate")
    if gate is None:
        return errors, {
            "report": remote_path,
            "report_sha256": None,
            "passed": False,
            "projected_total_seconds": None,
            "max_projected_total_seconds": 10800,
        }
    pilot = FAMILIES[0]
    pilot_run = run_ids[pilot]
    common = gate.get("common_phase_durations")
    pilot_durations = gate.get("pilot_phase_durations")
    if (
        gate.get("schema_version") != "1.0.0"
        or gate.get("workflow_profile") != WORKFLOW_PROFILE
        or gate.get("status") != "passed"
        or gate.get("passed") is not True
        or gate.get("job_id") != job_id
        or gate.get("pilot_family") != pilot
        or gate.get("pilot_run_id") != pilot_run
        or gate.get("pilot_includes_ovrtx_render") is not True
        or gate.get("projection_formula")
        != "common_readiness_preflight_seconds + 6 * pilot_family_pipeline_seconds"
        or gate.get("max_projected_total_seconds") != 10800
        or type(gate.get("projected_total_seconds")) is not int
        or gate.get("projected_total_seconds", 10801) > 10800
        or gate.get("remaining_families_authorized") is not True
    ):
        errors.append("pilot-runtime-gate: identité, statut ou plafond incohérent")

    def validate_durations(
        values: object, expected_phases: tuple[str, ...], run_id: str, label: str
    ) -> int:
        if not isinstance(values, list) or len(values) != len(expected_phases):
            errors.append(f"pilot-runtime-gate: durées {label} incomplètes")
            return -1
        total = 0
        for entry, phase in zip(values, expected_phases, strict=True):
            report_item = indexed.get((run_id, phase))
            expected_report = f"phase-{phase}.json"
            duration = entry.get("duration_seconds") if isinstance(entry, dict) else None
            status = entry.get("status") if isinstance(entry, dict) else None
            report_path = Path(report_item["report"]) if report_item else None
            expected_sha = sha256_file(report_path) if report_path and report_path.is_file() else None
            raw = report_item.get("raw", {}) if report_item else {}
            try:
                started = datetime.fromisoformat(
                    str(raw.get("started_at")).replace("Z", "+00:00")
                )
                finished = datetime.fromisoformat(
                    str(raw.get("finished_at")).replace("Z", "+00:00")
                )
                elapsed = (finished - started).total_seconds()
                expected_duration = math.ceil(elapsed)
                if started.tzinfo is None or finished.tzinfo is None or not 0 <= elapsed <= 10800:
                    raise ValueError
            except (TypeError, ValueError):
                expected_duration = None
            allowed_statuses = (
                {"passed", "needs_rerun"}
                if phase in TOP_LEVEL_VALIDATORS
                else {"passed"}
            )
            if (
                not isinstance(entry, dict)
                or entry.get("phase") != phase
                or entry.get("report_filename") != expected_report
                or entry.get("report_sha256") != expected_sha
                or type(duration) is not int
                or duration < 0
                or duration != expected_duration
                or status != (report_item.get("status") if report_item else None)
                or status not in allowed_statuses
            ):
                errors.append(f"pilot-runtime-gate: durée/hash invalide pour {label}/{phase}")
            else:
                total += duration
        return total

    common_total = validate_durations(
        common, ("readiness", "preflight"), job_id, "commun"
    )
    pilot_total = validate_durations(
        pilot_durations, FAMILY_PHASES, pilot_run, "pilote"
    )
    projected = common_total + len(FAMILIES) * pilot_total
    if (
        common_total < 0
        or pilot_total < 0
        or gate.get("common_duration_seconds") != common_total
        or gate.get("pilot_duration_seconds") != pilot_total
        or gate.get("projected_total_seconds") != projected
    ):
        errors.append("pilot-runtime-gate: somme ou projection non reproductible")
    try:
        gate_created = datetime.fromisoformat(
            str(gate.get("created_at")).replace("Z", "+00:00")
        )
        if gate_created.tzinfo is None:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("pilot-runtime-gate: created_at invalide")
        gate_created = None
    if gate_created is not None:
        pilot_finished_value = indexed.get(
            (pilot_run, "render-preview"), {}
        ).get("raw", {}).get("finished_at")
        try:
            pilot_finished = datetime.fromisoformat(
                str(pilot_finished_value).replace("Z", "+00:00")
            )
        except (TypeError, ValueError):
            pilot_finished = None
        if (
            pilot_finished is None
            or pilot_finished.tzinfo is None
            or gate_created < pilot_finished
        ):
            errors.append("pilot-runtime-gate: gate créé avant la fin du rendu pilote")
        for family in FAMILIES[1:]:
            first = indexed.get((run_ids[family], FAMILY_PHASES[0]), {}).get("raw", {}).get(
                "started_at"
            )
            try:
                started = datetime.fromisoformat(str(first).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                continue
            if started.tzinfo and started < gate_created:
                errors.append(
                    f"pilot-runtime-gate: {family} a démarré avant l'autorisation du pilote"
                )
    local = local_artifact(root, job_id, remote_path)
    return errors, {
        "report": remote_path,
        "report_sha256": sha256_file(local) if local else None,
        "passed": not errors,
        "common_duration_seconds": gate.get("common_duration_seconds"),
        "pilot_duration_seconds": gate.get("pilot_duration_seconds"),
        "projected_total_seconds": gate.get("projected_total_seconds"),
        "max_projected_total_seconds": gate.get("max_projected_total_seconds"),
        "remaining_families_authorized": gate.get("remaining_families_authorized"),
    }


def audit_errors(
    payload: dict[str, Any],
    family: str,
    stage: str,
    source: str,
    asset: str,
    local_asset: Path,
    label: str,
) -> list[str]:
    errors = false_claim_errors(payload, label)
    metadata = CANONICAL[family]
    if (
        payload.get("schema_version") != "1.0.0"
        or not reference_passed(payload)
        or payload.get("workflow_profile") != WORKFLOW_PROFILE
        or payload.get("family_id") != family
        or payload.get("audit_stage") != stage
        or payload.get("source_asset_path") != source
        or payload.get("source_asset_sha256") != metadata["sha256"]
        or payload.get("asset_path") != asset
        or payload.get("asset_sha256") != sha256_file(local_asset)
        or payload.get("output_paths") != [asset]
        or payload.get("default_prim_path") != metadata["default_prim_path"]
        or payload.get("geometry_identical_to_f42a") is not True
        or payload.get("physics_mode") != "static_collision_diagnostics_only"
        or payload.get("forbidden_prim_type_count") != 0
        or payload.get("forbidden_schema_count") != 0
        or payload.get("forbidden_property_count") != 0
        or payload.get("joint_count") != 0
        or payload.get("rigid_body_count") != 0
        or payload.get("mass_property_count") != 0
        or payload.get("time_stepping_executed") is not False
        or payload.get("physicsnemo_simulation_executed") is not False
        or payload.get("fea_executed") is not False
        or payload.get("simulation_validated") is not False
        or payload.get("manufacturing_authorized") is not False
    ):
        errors.append(f"{label}: audit USD F42b incomplet ou rattaché à un autre actif")
    meshes = payload.get("mesh_paths")
    source_bindings = payload.get("source_material_bindings")
    source_binding_signatures = payload.get("source_material_binding_signatures")
    bindings = payload.get("material_bindings")
    binding_signatures = payload.get("material_binding_signatures")
    material_contracts = payload.get("material_contracts")
    collisions = payload.get("collision_mesh_paths")
    mesh_collision_api = payload.get("mesh_collision_api_paths")
    collision_enabled = payload.get("collision_enabled")
    if (
        not isinstance(meshes, list)
        or not meshes
        or not all(isinstance(path, str) and path for path in meshes)
        or len(meshes) != len(set(meshes))
    ):
        errors.append(f"{label}: liste de Mesh invalide")
        meshes = []
    valid_source_signatures = (
        isinstance(source_bindings, dict)
        and isinstance(source_binding_signatures, dict)
        and set(source_bindings) == set(meshes)
        and set(source_binding_signatures) == set(meshes)
        and all(
            isinstance(path, str)
            and isinstance(target, str)
            and target.startswith(f"{metadata['default_prim_path']}/")
            for path, target in source_bindings.items()
        )
        and all(
            isinstance(signature, dict)
            and set(signature) == {"target", "relationship_metadata"}
            and signature.get("target") == source_bindings.get(path)
            and isinstance(signature.get("relationship_metadata"), dict)
            for path, signature in source_binding_signatures.items()
        )
    )
    valid_target_signatures = (
        valid_source_signatures
        and isinstance(bindings, dict)
        and isinstance(binding_signatures, dict)
        and set(bindings) == set(meshes)
        and set(binding_signatures) == set(meshes)
        and all(
            isinstance(signature, dict)
            and set(signature) == {"target", "relationship_metadata"}
            and signature.get("target") == bindings.get(path)
            and signature.get("relationship_metadata")
            == source_binding_signatures[path].get("relationship_metadata")
            for path, signature in binding_signatures.items()
        )
    )
    collision_lists_valid = (
        isinstance(collisions, list)
        and isinstance(mesh_collision_api, list)
        and all(isinstance(path, str) and path for path in collisions)
        and all(isinstance(path, str) and path for path in mesh_collision_api)
        and len(collisions) == len(set(collisions))
        and len(mesh_collision_api) == len(set(mesh_collision_api))
    )
    if (
        not valid_target_signatures
        or not isinstance(material_contracts, dict)
        or not collision_lists_valid
        or not isinstance(collision_enabled, dict)
        or (collision_lists_valid and not set(mesh_collision_api).issubset(set(meshes)))
    ):
        errors.append(f"{label}: binding matériau/collision invalide")
    elif stage == "minimum" and (
        bindings != source_bindings
        or material_contracts
        or collisions
        or mesh_collision_api
        or collision_enabled
    ):
        errors.append(f"{label}: binding source modifié ou collision présente au gate minimum")
    elif stage == "material" and (
        set(bindings) != set(meshes)
        or collisions
        or mesh_collision_api
        or collision_enabled
    ):
        errors.append(f"{label}: bindings visuels incomplets ou collision prématurée")
    elif stage in {"physics", "final"} and (
        set(bindings) != set(meshes)
        or set(collisions) != set(meshes)
        or mesh_collision_api
        or collision_enabled != {path: True for path in meshes}
    ):
        errors.append(f"{label}: chaque Mesh doit garder son matériau et CollisionAPI")
    if stage in {"material", "physics", "final"} and meshes:
        material_path = (
            f"{CANONICAL[family]['default_prim_path']}"
            "/F42bContractLooks/CanonicalVisualMaterial"
        )
        if bindings != {path: material_path for path in meshes}:
            errors.append(f"{label}: cibles de binding différentes du matériau canonique F42b")
        expected_material = {
            "material_path": material_path,
            "shader_path": f"{material_path}/PreviewSurface",
            "visual_material_assignment": VISUAL_ASSIGNMENTS[family],
            "visual_material_parameters": VISUAL_PALETTE[VISUAL_ASSIGNMENTS[family]],
            "visual_source_sha256": VISUAL_SOURCE_SHA256,
        }
        if material_contracts != {path: expected_material for path in meshes}:
            errors.append(f"{label}: shader/binding visuel différent de la palette F7")
    return errors


def provenance_errors(
    indexed: dict[tuple[str, str], dict[str, Any]],
    root: Path,
    job_id: str,
    run_ids: dict[str, str],
    stages: dict[str, dict[str, str]],
) -> tuple[list[str], dict[str, bool]]:
    errors: list[str] = []
    simready: dict[str, bool] = {family: False for family in FAMILIES}
    remote_root = PurePosixPath("/workspace/results") / job_id

    def children(run_id: str, phase: str) -> list[str]:
        item = indexed.get((run_id, phase))
        value = item.get("raw", {}).get("child_reports", []) if item else []
        return value if isinstance(value, list) else []

    def exact_child(run_id: str, phase: str, filename: str) -> tuple[str, dict[str, Any] | None]:
        path = str(remote_root / phase / run_id / filename)
        label = f"{run_id}/{phase}/{filename}"
        if path not in children(run_id, phase):
            errors.append(f"{label}: enfant exact absent du rapport top-level")
        return path, load_child_json(root, job_id, path, errors, label)

    def require_markdown(run_id: str, phase: str, filename: str) -> None:
        path = str(remote_root / phase / run_id / filename)
        if local_artifact(root, job_id, path) is None:
            errors.append(f"{run_id}/{phase}: preuve Markdown absente: {filename}")

    def diagnostic_agent_valid(
        payload: dict[str, Any] | None,
        input_asset: str,
        skill: str,
        run_id: str,
        phase: str,
    ) -> bool:
        if (
            payload is None
            or not reference_passed(payload)
            or payload.get("asset_path") != input_asset
            or payload.get("skill") != skill
        ):
            return False
        output = validate_remote_path(payload.get("output_usd_path"))
        expected_root = remote_root / phase / run_id / "agent-output"
        return (
            output is not None
            and PurePosixPath(output).is_relative_to(expected_root)
            and local_artifact(root, job_id, output) is not None
        )

    for family, run_id in run_ids.items():
        source = f"/workspace/jobs/{job_id}/inputs/f42a-usd/{family}.usd"
        minimum = stages[family]["minimum-usd"]
        material = stages[family]["material"]
        physics = stages[family]["physics"]
        conform = stages[family]["conform"]
        local_minimum = local_artifact(root, job_id, minimum)
        local_material = local_artifact(root, job_id, material)
        local_physics = local_artifact(root, job_id, physics)
        local_conform = local_artifact(root, job_id, conform)
        if local_minimum is None or local_minimum.stat().st_size != CANONICAL[family]["size_bytes"] or sha256_file(local_minimum) != CANONICAL[family]["sha256"]:
            errors.append(f"{run_id}: la copie minimum ne correspond pas octet pour octet à F42a")
            continue
        if any(path is None for path in (local_material, local_physics, local_conform)):
            errors.append(f"{run_id}: lignée USD Material/Physics/conform incomplète")
            continue

        input_audit_path, input_audit = exact_child(run_id, "minimum-usd", "f42b-input-audit.json")
        minimum_reference_path, minimum_reference = exact_child(
            run_id, "minimum-usd", "validate-usd-minimum.json"
        )
        context_path, context = exact_child(run_id, "minimum-usd", "asset-context.json")
        require_markdown(run_id, "minimum-usd", "validate-usd-minimum.md")
        require_markdown(run_id, "minimum-usd", "asset-context.md")
        if input_audit is not None:
            errors.extend(
                audit_errors(
                    input_audit,
                    family,
                    "minimum",
                    source,
                    minimum,
                    local_minimum,
                    input_audit_path,
                )
            )
        if minimum_reference is None or not reference_passed(minimum_reference):
            errors.append(f"{run_id}: gate validate-usd-minimum non réussi")
        elif not reference_applies_to(minimum_reference, minimum):
            errors.append(f"{run_id}: validate-usd-minimum appliqué à un autre actif")
        if context is not None:
            if (
                context.get("schema_version") != "1.0.0"
                or not reference_passed(context)
                or context.get("workflow_profile") != WORKFLOW_PROFILE
                or context.get("family_id") != family
                or context.get("source_asset_path") != source
                or context.get("source_asset_sha256") != CANONICAL[family]["sha256"]
                or context.get("default_prim_path") != CANONICAL[family]["default_prim_path"]
                or context.get("visual_material_assignment")
                != VISUAL_ASSIGNMENTS[family]
                or context.get("visual_material_parameters")
                != VISUAL_PALETTE[VISUAL_ASSIGNMENTS[family]]
                or context.get("historical_material_status")
                != HISTORICAL_STATUSES[family]
                or context.get("visual_claim_scope")
                != "visual_hypotheses_only_not_historical_material_identification"
                or not isinstance(context.get("physics_material_properties"), dict)
                or any(value is not None for value in context["physics_material_properties"].values())
                or context.get("physics_mode") != "static_collision_diagnostics_only"
            ):
                errors.append(f"{run_id}: contexte sourcé F42b incohérent")
            errors.extend(false_claim_errors(context, context_path))

        material_agent_path, material_agent = exact_child(run_id, "material", "material-agent.json")
        material_authoring_path, material_authoring = exact_child(
            run_id, "material", "f42b-material-authoring.json"
        )
        material_audit_path, material_audit = exact_child(run_id, "material", "f42b-material-audit.json")
        require_markdown(run_id, "material", "material-agent.md")
        if not diagnostic_agent_valid(
            material_agent, minimum, "material-agent-client", run_id, "material"
        ):
            errors.append(f"{material_agent_path}: résultat Material Agent non attesté")
        if material_authoring is None or (
            not reference_passed(material_authoring)
            or material_authoring.get("workflow_profile") != WORKFLOW_PROFILE
            or material_authoring.get("family_id") != family
            or material_authoring.get("asset_path") != material
            or material_authoring.get("asset_sha256") != sha256_file(local_material)
            or material_authoring.get("visual_material_assignment")
            != VISUAL_ASSIGNMENTS[family]
            or material_authoring.get("visual_material_parameters")
            != VISUAL_PALETTE[VISUAL_ASSIGNMENTS[family]]
            or material_authoring.get("visual_source_sha256")
            != VISUAL_SOURCE_SHA256
            or input_audit is None
            or material_authoring.get("replaced_source_material_bindings")
            != input_audit.get("material_bindings")
            or material_authoring.get("replaced_source_material_binding_signatures")
            != input_audit.get("material_binding_signatures")
            or material_authoring.get("physics_material_properties_authored") is not False
        ):
            errors.append(f"{material_authoring_path}: normalisation visuelle F7 non attestée")
        if material_authoring is not None:
            errors.extend(false_claim_errors(material_authoring, material_authoring_path))
        if material_audit is not None:
            errors.extend(
                audit_errors(
                    material_audit,
                    family,
                    "material",
                    source,
                    material,
                    local_material,
                    material_audit_path,
                )
            )
            if input_audit is None or (
                material_audit.get("source_material_bindings")
                != input_audit.get("material_bindings")
                or material_audit.get("source_material_binding_signatures")
                != input_audit.get("material_binding_signatures")
            ):
                errors.append(
                    f"{material_audit_path}: baseline de bindings différente du gate minimum"
                )

        physics_agent_path, physics_agent = exact_child(run_id, "physics", "physics-agent.json")
        physics_authoring_path, physics_authoring = exact_child(
            run_id, "physics", "f42b-physics-authoring.json"
        )
        physics_audit_path, physics_audit = exact_child(run_id, "physics", "f42b-physics-audit.json")
        require_markdown(run_id, "physics", "physics-agent.md")
        if not diagnostic_agent_valid(
            physics_agent, material, "physics-agent-client", run_id, "physics"
        ):
            errors.append(f"{physics_agent_path}: résultat Physics Agent non attesté")
        if physics_authoring is None or (
            not reference_passed(physics_authoring)
            or physics_authoring.get("workflow_profile") != WORKFLOW_PROFILE
            or physics_authoring.get("family_id") != family
            or physics_authoring.get("asset_path") != physics
            or physics_authoring.get("asset_sha256") != sha256_file(local_physics)
            or physics_authoring.get("authored_schemas") != ["PhysicsCollisionAPI"]
            or physics_authoring.get("collision_enabled") is not True
            or physics_authoring.get("mesh_collision_api_authored") is not False
            or physics_authoring.get("physics_material_properties_authored") is not False
            or physics_authoring.get("joint_count") != 0
            or physics_authoring.get("rigid_body_count") != 0
            or physics_authoring.get("mass_property_count") != 0
        ):
            errors.append(f"{physics_authoring_path}: normalisation CollisionAPI F42b non attestée")
        if physics_authoring is not None:
            errors.extend(false_claim_errors(physics_authoring, physics_authoring_path))
        if physics_audit is not None:
            errors.extend(
                audit_errors(
                    physics_audit,
                    family,
                    "physics",
                    source,
                    physics,
                    local_physics,
                    physics_audit_path,
                )
            )
            if input_audit is None or (
                physics_audit.get("source_material_bindings")
                != input_audit.get("material_bindings")
                or physics_audit.get("source_material_binding_signatures")
                != input_audit.get("material_binding_signatures")
            ):
                errors.append(
                    f"{physics_audit_path}: baseline de bindings différente du gate minimum"
                )

        conform_reference_path, conform_reference = exact_child(
            run_id, "conform", "simready-conform-profile.json"
        )
        require_markdown(run_id, "conform", "simready-conform-profile.md")
        if conform_reference is None or not conform_reference_valid(
            conform_reference, conform
        ):
            errors.append(f"{conform_reference_path}: conformance non attestée")

        top_validators_passed = True
        for phase in TOP_LEVEL_VALIDATORS:
            reference_path, reference = exact_child(run_id, phase, f"{phase}.json")
            require_markdown(run_id, phase, f"{phase}.md")
            top = indexed[(run_id, phase)]
            outcome = (
                nvidia_validation_outcome(
                    reference, conform, NVIDIA_VALIDATOR_SKILLS[phase]
                )
                if reference is not None
                else None
            )
            if outcome is None:
                errors.append(
                    f"{reference_path}: validateur bloqué, interrompu ou sans findings structurés"
                )
            expected_status = "passed" if outcome == "passed" else "needs_rerun"
            if outcome is not None and top["status"] != expected_status:
                errors.append(f"{reference_path}: statut enfant différent du top-level")
            top_validators_passed = top_validators_passed and outcome == "passed"

        render_root = remote_root / "render-preview" / run_id
        simready_path, simready_report = exact_child(run_id, "render-preview", "simready-validate.json")
        final_audit_path, final_audit = exact_child(run_id, "render-preview", "f42b-final-audit.json")
        render_path, render = exact_child(run_id, "render-preview", "ovrtx-render-service.json")
        turntable_path, turntable = exact_child(run_id, "render-preview", "ovrtx-turntable.json")
        ffprobe_path, probe = exact_child(run_id, "render-preview", "turntable-video-ffprobe.json")
        attestation_path, attestation = exact_child(run_id, "render-preview", "render-media-attestation.json")
        final_report_path, final_report = exact_child(run_id, "render-preview", "f42b-family-report.json")
        for filename in (
            "simready-validate.md",
            "ovrtx-render-service.md",
            "ovrtx-turntable.md",
            "f42b-family-report.md",
        ):
            require_markdown(run_id, "render-preview", filename)

        if final_audit is not None:
            errors.extend(
                audit_errors(
                    final_audit,
                    family,
                    "final",
                    source,
                    conform,
                    local_conform,
                    final_audit_path,
                )
            )
            if input_audit is None or (
                final_audit.get("source_material_bindings")
                != input_audit.get("material_bindings")
                or final_audit.get("source_material_binding_signatures")
                != input_audit.get("material_binding_signatures")
            ):
                errors.append(
                    f"{final_audit_path}: baseline de bindings différente du gate minimum"
                )
        simready_outcome = (
            nvidia_validation_outcome(
                simready_report, conform, NVIDIA_VALIDATOR_SKILLS["validate-simready"]
            )
            if simready_report is not None
            else None
        )
        if simready_outcome is None:
            errors.append(
                f"{simready_path}: validateur SimReady bloqué, interrompu ou sans findings structurés"
            )
        simready_passed = simready_outcome == "passed"
        simready[family] = bool(top_validators_passed and simready_passed)

        preview = str(render_root / f"{family}-simready-preview.png")
        photos = [
            str(render_root / "photos" / f"{family}-{view}.png")
            for view in ("front", "right", "rear", "left")
        ]
        movie = str(render_root / f"{family}-simready-turntable.mp4")
        checksum = str(render_root / "render-media.sha256")
        frames = [str(render_root / "turntable-frames" / f"frame_{index:03d}.png") for index in range(24)]
        if render is None or not reference_passed(render) or (
            render.get("asset_path") != conform
            or render.get("output_image_path") != preview
            or render.get("generated_files") != [preview]
        ):
            errors.append(f"{render_path}: lignée OVRTX preview incohérente")
        if turntable is None or not reference_passed(turntable) or (
            turntable.get("asset_path") != conform
            or turntable.get("frames_requested") != 24
            or turntable.get("frames_rendered") != 24
            or turntable.get("generated_files") != frames
        ):
            errors.append(f"{turntable_path}: lignée OVRTX turntable incohérente")
        else:
            frame_reports = turntable.get("frame_reports")
            if not isinstance(frame_reports, list) or len(frame_reports) != 24:
                errors.append(f"{turntable_path}: 24 attestations de frames requises")
            else:
                for index, frame in enumerate(frame_reports):
                    if (
                        not isinstance(frame, dict)
                        or frame.get("frame") != index
                        or frame.get("passed") is not True
                        or frame.get("output_image_path") != frames[index]
                        or frame.get("pixel_inspection", {}).get("uniform") is not False
                        or local_artifact(root, job_id, frames[index]) is None
                    ):
                        errors.append(f"{turntable_path}: frame {index} non attestée")
        media_paths = [preview, *photos, movie]
        local_media = {path: local_artifact(root, job_id, path) for path in media_paths}
        if any(path is None for path in local_media.values()):
            errors.append(f"{run_id}: média final OVRTX absent")
        for photo, frame_index in zip(photos, (0, 6, 12, 18), strict=True):
            local_photo = local_media[photo]
            local_frame = local_artifact(root, job_id, frames[frame_index])
            if local_photo is None or local_frame is None or sha256_file(local_photo) != sha256_file(local_frame):
                errors.append(f"{run_id}: photo {photo} différente de la frame OVRTX attendue")
        local_checksum = local_artifact(root, job_id, checksum)
        expected_digests = {
            path: sha256_file(local)
            for path, local in local_media.items()
            if local is not None
        }
        expected_media = [
            {
                "filename": PurePosixPath(path).name,
                "kind": "film"
                if path == movie
                else ("preview" if path == preview else "photo"),
                "sha256": expected_digests[path],
                "size_bytes": local_media[path].stat().st_size,
            }
            for path in media_paths
            if path in expected_digests and local_media[path] is not None
        ]
        if local_checksum is None:
            errors.append(f"{run_id}: manifeste de checksums média absent")
        elif len(expected_digests) == len(media_paths):
            expected_checksum = "".join(
                f"{expected_digests[path]}  {PurePosixPath(path).name}\n" for path in media_paths
            )
            if local_checksum.read_text(encoding="utf-8") != expected_checksum:
                errors.append(f"{run_id}: manifeste de checksums média incohérent")
        if probe is None:
            pass
        else:
            streams = probe.get("streams")
            try:
                duration = float(probe.get("format", {}).get("duration", 0))
            except (TypeError, ValueError):
                duration = 0.0
            if (
                not isinstance(streams, list)
                or len(streams) != 1
                or streams[0].get("codec_name") != "h264"
                or streams[0].get("pix_fmt") != "yuv420p"
                or streams[0].get("width") != 1280
                or streams[0].get("height") != 720
                or duration <= 0
            ):
                errors.append(f"{ffprobe_path}: MP4 H.264/yuv420p 1280x720 invalide")
        if attestation is not None:
            if (
                attestation.get("schema_version") != "1.0.0"
                or not reference_passed(attestation)
                or attestation.get("workflow_profile") != WORKFLOW_PROFILE
                or attestation.get("family_id") != family
                or attestation.get("claim_scope") != "omniverse_visual_diagnostic_only"
                or attestation.get("source_asset")
                != {
                    "filename": local_conform.name,
                    "sha256": sha256_file(local_conform),
                    "size_bytes": local_conform.stat().st_size,
                }
                or attestation.get("media") != expected_media
                or attestation.get("turntable_frame_count") != 24
                or attestation.get("photos_from_frame_indices") != [0, 6, 12, 18]
                or not isinstance(attestation.get("checksum_manifest"), dict)
                or attestation["checksum_manifest"].get("filename")
                != PurePosixPath(checksum).name
                or local_checksum is None
                or attestation["checksum_manifest"].get("sha256")
                != sha256_file(local_checksum)
                or attestation.get("simready_validation_status")
                != ("passed" if simready_passed else "needs_rerun")
                or attestation.get("simready_auto_repair_attempted") is not False
                or attestation.get("source_asset_mutated_by_render") is not False
                or attestation.get("static_collision_diagnostic_only") is not True
            ):
                errors.append(f"{attestation_path}: attestation média F42b incohérente")
            errors.extend(false_claim_errors(attestation, attestation_path))
        if final_report is not None:
            if (
                final_report.get("schema_version") != "1.0.0"
                or final_report.get("passed") is not True
                or final_report.get("workflow_profile") != WORKFLOW_PROFILE
                or final_report.get("family_id") != family
                or final_report.get("status")
                != (
                    "passed_visual_diagnostics_simready_validated"
                    if simready_passed
                    else "passed_visual_diagnostics_simready_findings_require_rerun"
                )
                or final_report.get("source_usd")
                != {
                    "filename": f"{family}.usd",
                    "size_bytes": CANONICAL[family]["size_bytes"],
                    "sha256": CANONICAL[family]["sha256"],
                }
                or final_report.get("final_usd")
                != {
                    "filename": local_conform.name,
                    "size_bytes": local_conform.stat().st_size,
                    "sha256": sha256_file(local_conform),
                }
                or final_report.get("geometry_identical_to_f42a") is not True
                or final_report.get("visual_material_assignment")
                != VISUAL_ASSIGNMENTS[family]
                or final_report.get("historical_material_status")
                != HISTORICAL_STATUSES[family]
                or final_report.get("physics_material_properties_known") is not False
                or final_report.get("physics_mode") != "static_collision_diagnostics_only"
                or final_report.get("nvidia_profile") != "Prop-Robotics-Physx@1.0.0"
                or final_report.get("simready_validation_only") is not True
                or final_report.get("simready_auto_repair_attempted") is not False
                or final_report.get("fet004_auto_repair_attempted") is not False
                or final_report.get("fet005_auto_repair_attempted") is not False
                or final_report.get("simready_validated") is not simready_passed
                or final_report.get("ovrtx_preview_validated") is not True
                or final_report.get("ovrtx_turntable_validated") is not True
                or final_report.get("media") != expected_media
                or final_report.get("joint_count") != 0
                or final_report.get("rigid_body_count") != 0
                or final_report.get("mass_property_count") != 0
            ):
                errors.append(f"{final_report_path}: rapport famille F42b incohérent")
            errors.extend(false_claim_errors(final_report, final_report_path))
    return errors, simready


def summarize(root: Path, archive: Path, job_id: str, instance_id: int, image: str) -> dict[str, Any]:
    root = root.resolve(strict=True)
    archive = archive.resolve(strict=True)
    if root.name != job_id or root.parent != archive.parent:
        raise RuntimeError(
            "root extrait et archive F42b doivent partager la destination privée exacte"
        )
    destination_policy = private_destination_policy(archive)
    expected, run_ids = expected_contract(job_id)
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    phase_reports: list[dict[str, Any]] = []
    duplicates: list[str] = []
    malformed: list[str] = []
    for path in sorted(root.rglob("phase-*.json")):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            malformed.append(str(path))
            continue
        phase = report.get("phase") if isinstance(report, dict) else None
        run_id = path.parent.name
        if (
            not isinstance(report, dict)
            or not isinstance(phase, str)
            or not phase
            or path.parent.parent.name != phase
            or path.name != f"phase-{phase}.json"
        ):
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
        else:
            indexed[key] = item

    missing = sorted(
        f"{run_id}/{phase}" for run_id, phase in expected if (run_id, phase) not in indexed
    )
    unexpected = sorted(
        f"{run_id}/{phase}" for run_id, phase in indexed if (run_id, phase) not in expected
    )
    report_contract_errors: list[str] = []
    invalid: set[tuple[str, str]] = set()
    for key, contract in expected.items():
        if key not in indexed:
            continue
        current_errors = validate_expected_report(
            indexed[key], contract, root, job_id, int(instance_id), image
        )
        if current_errors:
            invalid.add(key)
            report_contract_errors.extend(current_errors)
    incomplete = sorted(
        f"{run_id}/{phase}"
        for (run_id, phase), item in indexed.items()
        if (run_id, phase) in expected
        and ((run_id, phase) in invalid or item["status"] not in {"passed", "needs_rerun"})
    )
    needs_rerun = sorted(
        f"{run_id}/{phase}"
        for (run_id, phase), item in indexed.items()
        if (run_id, phase) in expected and item["status"] == "needs_rerun"
    )
    continuity: list[str] = []
    chronology: list[str] = []
    pilot_gate_errors: list[str] = []
    pilot_gate: dict[str, Any] = {
        "report": str(
            PurePosixPath("/workspace/results")
            / job_id
            / "pilot-gate"
            / job_id
            / "f42b-pilot-runtime-gate.json"
        ),
        "report_sha256": None,
        "passed": False,
        "projected_total_seconds": None,
        "max_projected_total_seconds": 10800,
    }
    stages = {family: {} for family in FAMILIES}
    if not missing and not report_contract_errors:
        continuity, stages = continuity_errors(indexed, job_id, run_ids)
        chronology = chronological_errors(indexed, job_id, run_ids)
        pilot_gate_errors, pilot_gate = validate_pilot_runtime_gate(
            indexed, root, job_id, run_ids
        )
    provenance: list[str] = []
    simready_outcomes = {family: False for family in FAMILIES}
    if not missing and not report_contract_errors and not continuity:
        provenance, simready_outcomes = provenance_errors(
            indexed, root, job_id, run_ids, stages
        )
    retrieval_complete = not (
        missing
        or incomplete
        or duplicates
        or malformed
        or unexpected
        or report_contract_errors
        or continuity
        or chronology
        or pilot_gate_errors
        or provenance
    )
    simready_validated = bool(retrieval_complete and all(simready_outcomes.values()))
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
        "workflow_profile": WORKFLOW_PROFILE,
        "status": "complete" if retrieval_complete else "partial",
        "passed": True,
        "retrieval_attempted": True,
        "artifact_archive_verified": True,
        "private_destination_policy": destination_policy,
        "retrieval_complete": retrieval_complete,
        "simready_validated": simready_validated,
        "simulation_executed": False,
        "simulation_validated": False,
        "physical_simulation_validated": False,
        "physicsnemo_simulation_executed": False,
        "fea_executed": False,
        "fea_validated": False,
        "dyno_validated": False,
        "manufacturing_authorized": False,
        "engine_installation_authorized": False,
        "performance_claim_authorized": False,
        "job_id": job_id,
        "instance_id": int(instance_id),
        "expected_image": image,
        "archive_path": str(archive),
        "archive_sha256": sha256_file(archive),
        "extracted_root": str(root),
        "expected_pipelines": {
            "shared_run_id": job_id,
            "family_run_ids": run_ids,
            "shared_phases": ["readiness", "preflight"],
            "family_phases": list(FAMILY_PHASES),
            "simready_validation": "render-preview child validation-only; no auto-repair",
            "required_report_count": len(expected),
        },
        "family_stage_paths": stages,
        "pilot_runtime_gate": pilot_gate,
        "phases": indexed_payload,
        "phase_reports": phase_reports_payload,
        "missing_phases": missing,
        "incomplete_phases": incomplete,
        "duplicate_reports": sorted(set(duplicates)),
        "malformed_reports": malformed,
        "unexpected_reports": unexpected,
        "report_contract_errors": report_contract_errors,
        "continuity_errors": continuity,
        "chronology_errors": chronology,
        "pilot_runtime_gate_errors": pilot_gate_errors,
        "provenance_errors": provenance,
        "simready_family_outcomes": simready_outcomes,
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
    resolved_root = args.root.resolve(strict=True)
    resolved_archive = args.archive.resolve(strict=True)
    if resolved_root.name != args.job_id or resolved_root.parent != resolved_archive.parent:
        parser.error("root extrait et archive F42b doivent partager la destination privée exacte")
    payload = summarize(
        resolved_root, resolved_archive, args.job_id, args.instance_id, args.expected_image
    )
    atomic_json(args.output.resolve(), payload)
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
