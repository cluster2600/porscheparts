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
        "variant_id": "type_912_4_5_na",
        "slug": "type-912-4-5-na",
        "stage_suffix": "/type-912-4-5-na/stages/type-912-4-5-na-detail-f10.usda",
    },
    "turbo": {
        "phase": "f10-917-30-turbo-5374",
        "variant_id": "917_30_turbo_5374",
        "slug": "917-30-turbo-5374",
        "stage_suffix": "/917-30-turbo-5374/stages/917-30-turbo-5374-detail-f10.usda",
    },
}

RELEASE_GATES = (
    "measured_variant_geometry_ready",
    "physical_kinematics_ready",
    "manufacturing_geometry_ready",
    "combustion_simulation_ready",
    "performance_claim_authorized",
)


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
        expected[(run_id, "validate-simready")]["allowed_output_directories"] = (
            "conform",
            "validate-simready",
        )
        expected[(run_id, "minimum-usd")]["exact_outputs"] = [f10_stage]
        render_root = remote_root / "render-preview" / run_id
        preview = str(render_root / "917-engine-simready-preview.png")
        expected[(run_id, "render-preview")]["exact_outputs"] = [
            preview,
            str(render_root / "photos" / "917-engine-front.png"),
            str(render_root / "photos" / "917-engine-right.png"),
            str(render_root / "photos" / "917-engine-rear.png"),
            str(render_root / "photos" / "917-engine-left.png"),
            str(render_root / "917-engine-simready-turntable.mp4"),
            str(render_root / "render-media.sha256"),
        ]
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


def local_artifact(root: Path, job_id: str, remote_value: object) -> Path | None:
    """Traduit un artefact récupéré sous /workspace/results/<job> sans évasion."""

    normalized = validate_remote_path(remote_value)
    if normalized is None:
        return None
    remote = PurePosixPath(normalized)
    remote_job_root = PurePosixPath("/workspace/results") / job_id
    if not remote.is_relative_to(remote_job_root):
        return None
    relative = remote.relative_to(remote_job_root)
    local = (root / Path(*relative.parts)).resolve()
    if not local.is_relative_to(root) or not local.is_file():
        return None
    return local


def load_child_json(
    root: Path,
    job_id: str,
    remote_value: object,
    errors: list[str],
    label: str,
) -> dict | None:
    local = local_artifact(root, job_id, remote_value)
    if local is None:
        errors.append(f"{label}: rapport enfant absent ou hors du job: {remote_value}")
        return None
    try:
        payload = json.loads(local.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        errors.append(f"{label}: JSON enfant illisible: {remote_value}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{label}: JSON enfant doit être un objet: {remote_value}")
        return None
    return payload


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
    children = report.get("child_reports")
    if not isinstance(children, list) or not all(validate_remote_path(value) for value in children):
        errors.append(f"{label}: child_reports invalide")
        children = []
    if len(children) != len(set(children)):
        errors.append(f"{label}: child_reports dupliqué")
    remote_job_root = PurePosixPath("/workspace/results") / job_id
    expected_child_root = remote_job_root / (
        "f10" if item["phase"].startswith("f10-") else item["phase"]
    ) / item["run_id"]
    for child in children:
        normalized = validate_remote_path(child)
        if normalized is None:
            continue
        remote = PurePosixPath(normalized)
        if not remote.is_relative_to(expected_child_root):
            errors.append(f"{label}: rapport enfant hors de la phase attendue: {remote}")
        elif local_artifact(root, job_id, normalized) is None:
            errors.append(f"{label}: rapport enfant absent de l'archive extraite: {remote}")
    exact_outputs = contract.get("exact_outputs")
    if exact_outputs is not None and set(outputs) != set(exact_outputs):
        errors.append(f"{label}: output_paths différent du contrat exact")

    allowed_output_directories = contract.get(
        "allowed_output_directories", (contract["output_directory"],)
    )
    allowed_output_roots = [
        remote_job_root / directory / item["run_id"] for directory in allowed_output_directories
    ]
    for output in outputs:
        normalized = validate_remote_path(output)
        if normalized is None:
            continue
        remote = PurePosixPath(normalized)
        if not any(remote.is_relative_to(expected_root) for expected_root in allowed_output_roots):
            errors.append(f"{label}: sortie hors du run ou de la phase attendue: {remote}")
            continue
        if local_artifact(root, job_id, normalized) is None:
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
        context_report = str(
            PurePosixPath("/workspace/results")
            / job_id
            / "f10"
            / run_id
            / "generated"
            / definition["slug"]
            / "reports"
            / "asset-context.json"
        )
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
        require_inputs(
            run_id,
            "material",
            [minimum_report, f10_output, material_prompt, context_report],
        )
        material_output = one_output(run_id, "material")
        require_inputs(
            run_id,
            "physics",
            [material_report, material_output, physics_prompt, context_report],
        )
        physics_output = one_output(run_id, "physics")
        require_inputs(run_id, "conform", [physics_report, physics_output])
        conform_output = one_output(run_id, "conform")

        previous_report: str | None = None
        for phase in VALIDATION_PHASES[:-1]:
            required = [conform_report, conform_output]
            if previous_report:
                required.append(previous_report)
            require_inputs(run_id, phase, required)
            validation_output = one_output(run_id, phase)
            if conform_output and validation_output != conform_output:
                errors.append(f"{run_id}/{phase}: l'USD validé doit être l'exact stage conforme")
            previous_report = remote_report_path(job_id, run_id, phase)
        simready_phase = "validate-simready"
        require_inputs(run_id, simready_phase, [conform_report, conform_output, previous_report])
        simready_output = one_output(run_id, simready_phase)
        simready_report = remote_report_path(job_id, run_id, simready_phase)
        require_inputs(run_id, "render-preview", [conform_report, simready_output, simready_report])
    return errors


def provenance_errors(
    indexed: dict[tuple[str, str], dict],
    root: Path,
    job_id: str,
    run_ids: dict[str, str],
) -> tuple[list[str], dict[str, bool]]:
    """Valide contexte, boucle de réparation et rapport final de chaque branche."""

    errors: list[str] = []
    outcomes: dict[str, bool] = {name: False for name in VARIANTS}
    remote_root = PurePosixPath("/workspace/results") / job_id

    def report_item(run_id: str, phase: str) -> dict | None:
        return indexed.get((run_id, phase))

    def report_outputs(run_id: str, phase: str) -> list[str]:
        current = report_item(run_id, phase)
        values = current.get("output_paths", []) if current else []
        return values if isinstance(values, list) else []

    def has_child(run_id: str, phase: str, expected: str, label: str) -> None:
        current = report_item(run_id, phase)
        children = current.get("raw", {}).get("child_reports", []) if current else []
        if expected not in children:
            errors.append(f"{label}: attestation enfant absente: {expected}")

    def reference_passed(payload: dict) -> bool:
        if payload.get("passed") is not True:
            return False
        status = payload.get("status")
        return status is None or str(status).lower() in {"pass", "passed", "ready"}

    for name, definition in VARIANTS.items():
        run_id = run_ids[name]
        label = f"{run_id}"
        f10_item = report_item(run_id, definition["phase"])
        f10_outputs = report_outputs(run_id, definition["phase"])
        if f10_item is None or len(f10_outputs) != 1:
            continue
        f10_stage = f10_outputs[0]
        context_root = (
            remote_root
            / "f10"
            / run_id
            / "generated"
            / definition["slug"]
            / "reports"
        )
        context_report = str(context_root / "asset-context.json")
        context_markdown = str(context_root / "asset-context.md")
        has_child(run_id, definition["phase"], context_report, label)
        has_child(run_id, definition["phase"], context_markdown, label)
        if local_artifact(root, job_id, context_markdown) is None:
            errors.append(f"{label}: rapport Markdown de contexte absent")
        context = load_child_json(root, job_id, context_report, errors, label)
        if context is not None:
            if (
                context.get("schema_version") != "1.0.0"
                or context.get("status") != "passed"
                or context.get("passed") is not True
            ):
                errors.append(f"{label}: contexte d'actif non validé")
            if context.get("source_asset_path") != f10_stage:
                errors.append(f"{label}: contexte produit pour un autre stage F10")
            if context.get("variant_id") != definition["variant_id"]:
                errors.append(f"{label}: contexte produit pour une autre variante")
            documented = context.get("documented_geometry")
            if not isinstance(documented, dict) or any(
                field not in documented
                for field in ("cylinder_count", "bore_mm", "stroke_mm", "documented_displacement_cm3")
            ):
                errors.append(f"{label}: géométrie documentée du contexte incomplète")
            evidence = context.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                errors.append(f"{label}: preuves du contexte absentes")
            release = context.get("release_gates")
            if not isinstance(release, dict) or any(release.get(key) is not False for key in RELEASE_GATES):
                errors.append(f"{label}: limites de publication du contexte non bloquées")
            prompt = context.get("material_physics_prompt")
            if not isinstance(prompt, str) or not prompt.strip() or len(prompt.encode("utf-8")) > 8000:
                errors.append(f"{label}: prompt de contexte absent ou trop volumineux")

        conform_outputs = report_outputs(run_id, "conform")
        validate_outputs = report_outputs(run_id, "validate-simready")
        validate_item = report_item(run_id, "validate-simready")
        if len(conform_outputs) != 1 or len(validate_outputs) != 1 or validate_item is None:
            continue
        initial_usd = conform_outputs[0]
        final_usd = validate_outputs[0]
        conform_report = remote_report_path(job_id, run_id, "conform")
        repair_root = remote_root / "validate-simready" / run_id
        repair_report = str(repair_root / "repair-loop.json")
        repair_markdown = str(repair_root / "repair-loop.md")
        has_child(run_id, "validate-simready", repair_report, label)
        has_child(run_id, "validate-simready", repair_markdown, label)
        if local_artifact(root, job_id, repair_markdown) is None:
            errors.append(f"{label}: rapport Markdown de réparation absent")
        repair = load_child_json(root, job_id, repair_report, errors, label)
        branch_valid = repair is not None
        if repair is not None:
            status = repair.get("status")
            passed = repair.get("passed")
            if repair.get("schema_version") != "1.0.0" or status not in {"passed", "needs_rerun"}:
                errors.append(f"{label}: contrat de boucle de réparation invalide")
                branch_valid = False
            if passed is not (status == "passed"):
                errors.append(f"{label}: statut et booléen de réparation incohérents")
                branch_valid = False
            if repair.get("profile") != "Prop-Robotics-Neutral" or repair.get("profile_version") != "1.0.0":
                errors.append(f"{label}: profil de réparation inattendu")
                branch_valid = False
            if repair.get("source_conform_report") != conform_report:
                errors.append(f"{label}: réparation rattachée à un autre rapport de conformance")
                branch_valid = False
            if repair.get("initial_usd_path") != initial_usd or repair.get("final_usd_path") != final_usd:
                errors.append(f"{label}: lignée USD de la réparation incohérente")
                branch_valid = False
            repair_attempted = repair.get("repair_attempted")
            attempt_count = repair.get("attempt_count")
            attempts = repair.get("attempts")
            expected_attempt_count = 2 if repair_attempted is True else 1
            if (
                type(repair_attempted) is not bool
                or repair.get("max_attempts") != 2
                or attempt_count != expected_attempt_count
                or not isinstance(attempts, list)
                or len(attempts) != expected_attempt_count
                or [item.get("attempt") for item in attempts if isinstance(item, dict)]
                != list(range(1, expected_attempt_count + 1))
            ):
                errors.append(f"{label}: nombre de tentatives de réparation invalide")
                branch_valid = False
            for field in (
                "failed_requirement_ids",
                "repaired_requirement_ids",
                "blocked_requirement_ids",
                "unresolved_requirement_ids",
            ):
                value = repair.get(field)
                if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                    errors.append(f"{label}: {field} invalide")
                    branch_valid = False
            unresolved = repair.get("unresolved_requirement_ids", [])
            final_reports = repair.get("final_validation_reports")
            if not isinstance(final_reports, dict) or set(final_reports) != {
                "asset", "geometry", "physics", "simready"
            }:
                errors.append(f"{label}: rapports de validation finaux incomplets")
                branch_valid = False
                final_reports = {}
            final_children_passed = True
            for validator, child_path in final_reports.items():
                child = load_child_json(root, job_id, child_path, errors, f"{label}/{validator}")
                if child is None:
                    final_children_passed = False
                    continue
                asset_path = child.get("asset_path")
                child_outputs = child.get("output_paths")
                applies_to_final = asset_path == final_usd or (
                    isinstance(child_outputs, list)
                    and len(child_outputs) == 1
                    and child_outputs[0] == final_usd
                )
                if not applies_to_final:
                    errors.append(f"{label}/{validator}: validation appliquée à un autre USD final")
                    final_children_passed = False
                if not reference_passed(child):
                    final_children_passed = False
            top_status = validate_item.get("status")
            if top_status != status:
                errors.append(f"{label}: statut top-level différent de la boucle de réparation")
                branch_valid = False
            if status == "passed" and (unresolved or not final_children_passed):
                errors.append(f"{label}: réparation déclarée réussie avec constats non résolus")
                branch_valid = False
            branch_valid = bool(branch_valid and status == "passed" and final_children_passed and not unresolved)

        render_item = report_item(run_id, "render-preview")
        render_root = remote_root / "render-preview" / run_id
        preview = str(render_root / "917-engine-simready-preview.png")
        photos = [
            str(render_root / "photos" / filename)
            for filename in (
                "917-engine-front.png",
                "917-engine-right.png",
                "917-engine-rear.png",
                "917-engine-left.png",
            )
        ]
        movie = str(render_root / "917-engine-simready-turntable.mp4")
        checksum = str(render_root / "render-media.sha256")
        render_reference_report = str(render_root / "ovrtx-render-service.json")
        render_reference_markdown = str(render_root / "ovrtx-render-service.md")
        turntable_report = str(render_root / "ovrtx-turntable.json")
        turntable_markdown = str(render_root / "ovrtx-turntable.md")
        ffprobe_report = str(render_root / "turntable-video-ffprobe.json")
        render_attestation = str(render_root / "render-media-attestation.json")
        video_status_report = str(render_root / "video-f7-status.json")
        final_report = str(render_root / "omniverse-cad-to-simready-report.json")
        final_markdown = str(render_root / "omniverse-cad-to-simready-report.md")
        for child in (
            render_reference_report,
            render_reference_markdown,
            turntable_report,
            turntable_markdown,
            ffprobe_report,
            render_attestation,
            video_status_report,
            final_report,
            final_markdown,
        ):
            has_child(run_id, "render-preview", child, label)
            if local_artifact(root, job_id, child) is None:
                errors.append(f"{label}: rapport enfant de rendu absent: {child}")

        reference = load_child_json(root, job_id, render_reference_report, errors, label)
        if reference is None:
            branch_valid = False
        elif (
            not reference_passed(reference)
            or reference.get("asset_path") != final_usd
            or reference.get("output_image_path") != preview
            or reference.get("generated_files") != [preview]
        ):
            errors.append(f"{label}: lignée du rendu OVRTX principal incohérente")
            branch_valid = False

        expected_frames = [
            str(render_root / "turntable-frames" / f"frame_{index:03d}.png")
            for index in range(24)
        ]
        turntable = load_child_json(root, job_id, turntable_report, errors, label)
        if turntable is None:
            branch_valid = False
        else:
            frame_reports = turntable.get("frame_reports")
            if (
                not reference_passed(turntable)
                or turntable.get("asset_path") != final_usd
                or turntable.get("frames_requested") != 24
                or turntable.get("frames_rendered") != 24
                or turntable.get("generated_files") != expected_frames
                or not isinstance(frame_reports, list)
                or len(frame_reports) != 24
            ):
                errors.append(f"{label}: lignée du turntable OVRTX incohérente")
                branch_valid = False
            else:
                for index, frame in enumerate(frame_reports):
                    if (
                        not isinstance(frame, dict)
                        or frame.get("frame") != index
                        or frame.get("passed") is not True
                        or frame.get("output_image_path") != expected_frames[index]
                        or frame.get("pixel_inspection", {}).get("uniform") is not False
                        or local_artifact(root, job_id, expected_frames[index]) is None
                    ):
                        errors.append(f"{label}: frame turntable {index} non attestée")
                        branch_valid = False

        media_paths = [preview, *photos, movie]
        local_media: dict[str, Path] = {}
        for remote_media in media_paths:
            local = local_artifact(root, job_id, remote_media)
            if local is None:
                errors.append(f"{label}: média final absent: {remote_media}")
                branch_valid = False
            else:
                local_media[remote_media] = local
        for photo, frame_index in zip(photos, (0, 6, 12, 18), strict=True):
            local_frame = local_artifact(root, job_id, expected_frames[frame_index])
            if (
                photo not in local_media
                or local_frame is None
                or sha256_file(local_media[photo]) != sha256_file(local_frame)
            ):
                errors.append(f"{label}: photo {photo} différente de sa frame OVRTX")
                branch_valid = False
        local_checksum = local_artifact(root, job_id, checksum)
        if local_checksum is None:
            errors.append(f"{label}: manifeste de checksums média absent")
            branch_valid = False

        attestation = load_child_json(root, job_id, render_attestation, errors, label)
        if attestation is None:
            branch_valid = False
        else:
            expected_status = repair.get("status") if repair else None
            expected_digests = {
                remote_media: sha256_file(local_media[remote_media])
                for remote_media in media_paths
                if remote_media in local_media
            }
            if (
                attestation.get("schema_version") != "1.0.0"
                or not reference_passed(attestation)
                or attestation.get("claim_scope") != "omniverse_visual_diagnostic_only"
                or attestation.get("source_asset_path") != final_usd
                or attestation.get("preview_path") != preview
                or attestation.get("photo_paths") != photos
                or attestation.get("diagnostic_video_path") != movie
                or attestation.get("turntable_frame_paths") != expected_frames
                or attestation.get("media_sha256") != expected_digests
                or attestation.get("checksum_manifest_path") != checksum
                or attestation.get("ovrtx_render_report") != render_reference_report
                or attestation.get("ovrtx_turntable_report") != turntable_report
                or attestation.get("ffprobe_report") != ffprobe_report
                or attestation.get("upstream_simready_validation_status") != expected_status
                or attestation.get("simulation_validated") is not False
                or attestation.get("physical_simulation_validated") is not False
                or attestation.get("dyno_validated") is not False
                or attestation.get("performance_1600hp_validated") is not False
            ):
                errors.append(f"{label}: attestation média ou limites de revendication incohérentes")
                branch_valid = False
            if local_checksum is not None and len(expected_digests) == len(media_paths):
                expected_manifest = "".join(
                    f"{expected_digests[path]}  {PurePosixPath(path).name}\n"
                    for path in media_paths
                )
                if local_checksum.read_text(encoding="utf-8") != expected_manifest:
                    errors.append(f"{label}: contenu du manifeste de checksums média incohérent")
                    branch_valid = False

        video_status = load_child_json(root, job_id, video_status_report, errors, label)
        if video_status is None or (
            video_status.get("schema_version") != "1.0.0"
            or not reference_passed(video_status)
            or video_status.get("phase") != "turntable-diagnostic-film"
            or video_status.get("output_video_path") != movie
            or video_status.get("source_asset_path") != final_usd
            or video_status.get("disclosure_embedded") is not True
            or video_status.get("physical_simulation_claim_authorized") is not False
            or video_status.get("kinematic_f7_engine_motion_status")
            != "blocked_not_part_of_this_simready_run"
        ):
            errors.append(f"{label}: statut du film diagnostique incohérent")
            branch_valid = False

        probe = load_child_json(root, job_id, ffprobe_report, errors, label)
        if probe is None:
            branch_valid = False
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
                errors.append(f"{label}: métadonnées du film MP4 incohérentes")
                branch_valid = False

        consolidated = load_child_json(root, job_id, final_report, errors, label)
        if consolidated is None:
            branch_valid = False
        else:
            expected_status = repair.get("status") if repair else None
            if (
                consolidated.get("schema_version") != "1.0.0"
                or consolidated.get("overall_status") != expected_status
                or consolidated.get("passed") is not (expected_status == "passed")
            ):
                errors.append(f"{label}: statut du rapport consolidé incohérent")
                branch_valid = False
            request = consolidated.get("request_summary")
            if not isinstance(request, dict) or (
                request.get("job_id") != job_id
                or request.get("run_id") != run_id
                or request.get("variant_id") != definition["variant_id"]
                or request.get("simready_profile") != "Prop-Robotics-Neutral"
                or request.get("profile_version") != "1.0.0"
            ):
                errors.append(f"{label}: identité du rapport consolidé invalide")
                branch_valid = False
            final_artifacts = consolidated.get("final_artifacts")
            if not isinstance(final_artifacts, dict) or (
                final_artifacts.get("final_usd_path") != final_usd
                or final_artifacts.get("render_preview_path") != preview
                or final_artifacts.get("render_photo_paths") != photos
                or final_artifacts.get("diagnostic_video_path") != movie
                or final_artifacts.get("render_checksum_manifest_path") != checksum
                or final_artifacts.get("render_reference_report") != render_reference_report
                or final_artifacts.get("render_turntable_report") != turntable_report
                or final_artifacts.get("render_attestation_report") != render_attestation
                or final_artifacts.get("json_report_path") != final_report
                or final_artifacts.get("markdown_report_path") != final_markdown
            ):
                errors.append(f"{label}: artefacts finaux consolidés incohérents")
                branch_valid = False
            validation = consolidated.get("conformance_and_validation")
            if not isinstance(validation, dict) or validation.get("repair_loop_report") != repair_report:
                errors.append(f"{label}: attestation de réparation absente du rapport consolidé")
                branch_valid = False
            agents = consolidated.get("content_agents")
            if not isinstance(agents, dict) or (
                agents.get("credentials") != "redacted"
                or agents.get("render_report") != render_reference_report
                or agents.get("turntable_report") != turntable_report
            ):
                errors.append(f"{label}: statut de confidentialité des Content Agents invalide")
                branch_valid = False
            validation_scope = consolidated.get("validation_scope")
            if not isinstance(validation_scope, dict) or (
                validation_scope.get("simready_validated") is not (expected_status == "passed")
                or validation_scope.get("physical_simulation_validated") is not False
                or validation_scope.get("dyno_validated") is not False
                or validation_scope.get("performance_1600hp_validated") is not False
            ):
                errors.append(f"{label}: périmètre de validation consolidé invalide")
                branch_valid = False
            ordered = consolidated.get("ordered_stage_results")
            expected_stage_names = [
                "readiness", "preflight", "f1", "f2", "f3", "f10",
                "minimum-usd", "material", "physics", "conform",
                "validate-asset", "validate-geometry", "validate-physics",
                "validate-simready", "render-ovrtx",
            ]
            if (
                not isinstance(ordered, list)
                or [item.get("stage") for item in ordered if isinstance(item, dict)]
                != expected_stage_names
                or not isinstance(ordered[-1], dict)
                or ordered[-1].get("report_path") != render_reference_report
                or ordered[-1].get("status") != "passed"
                or ordered[-1].get("input_artifacts") != [final_usd]
                or ordered[-1].get("output_artifacts") != media_paths
            ):
                errors.append(f"{label}: chaîne ordonnée du rapport consolidé incomplète")
                branch_valid = False
            boundaries = consolidated.get("claim_boundaries")
            if not isinstance(boundaries, list) or len(boundaries) < 3:
                errors.append(f"{label}: limites de revendication absentes")
                branch_valid = False
        if render_item is None or render_item.get("status") != "passed":
            branch_valid = False
        outcomes[name] = branch_valid
    return errors, outcomes


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
    provenance, simready_outcomes = (
        provenance_errors(indexed, root, job_id, run_ids)
        if not missing and not report_contract_errors and not continuity
        else ([], {name: False for name in VARIANTS})
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
        or provenance
        or unexpected
    )
    simready_validated = bool(retrieval_complete and all(simready_outcomes.values()))
    # Une conformité/validation USD SimReady n'est pas une simulation physique
    # du moteur. Les preuves solveur, dyno et 1600 ch restent des gates séparés.
    simulation_validated = False
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
        "simready_validated": simready_validated,
        "simulation_validated": simulation_validated,
        "physical_simulation_validated": False,
        "dyno_validated": False,
        "performance_1600hp_validated": False,
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
        "provenance_errors": provenance,
        "simready_branch_outcomes": simready_outcomes,
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
