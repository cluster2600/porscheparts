#!/usr/bin/env python3
"""Produit le rapport consolidé CAD-to-SimReady d'une branche 917."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_PHASE_STAGES = (
    "readiness",
    "preflight",
    "f1",
    "f2",
    "f3",
    "f10",
    "minimum-usd",
    "material",
    "physics",
    "conform",
    "validate-asset",
    "validate-geometry",
    "validate-physics",
    "validate-simready",
)


def load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"rapport JSON objet attendu: {path}")
    return payload


def phase_path(output_root: Path, phase: str, run_id: str) -> Path:
    return output_root / phase / run_id / f"phase-{phase}.json"


def strict_phase_status(payload: dict[str, Any], label: str) -> str:
    status = payload.get("status")
    if status not in {"passed", "needs_rerun"}:
        raise SystemExit(f"{label}: statut de phase final invalide")
    if payload.get("passed") is not (status == "passed"):
        raise SystemExit(f"{label}: statut et booléen passed incohérents")
    return status


def require_reference_passed(payload: dict[str, Any], label: str) -> None:
    if payload.get("passed") is not True:
        raise SystemExit(f"{label}: passed=true requis")
    status = payload.get("status")
    if status is not None and str(status).lower() not in {"pass", "passed", "ready"}:
        raise SystemExit(f"{label}: status contradictoire avec passed=true")


def one_existing_path(values: object, label: str) -> str:
    if not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], str):
        raise SystemExit(f"{label}: une sortie unique est requise")
    path = Path(values[0]).resolve(strict=True)
    if not path.is_file():
        raise SystemExit(f"{label}: sortie absente")
    return str(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stage_entry(name: str, path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    status = strict_phase_status(payload, name)
    return {
        "stage": name,
        "report_path": str(path.resolve()),
        "status": status,
        "input_artifacts": payload.get("input_paths", []),
        "output_artifacts": payload.get("output_paths", []),
        "blocker_reason": payload.get("note") if status == "failed" else None,
        "rerun_reason": payload.get("note") if status == "needs_rerun" else None,
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Rapport consolidé Porsche 917 CAD-to-SimReady",
        "",
        f"- Statut global : `{payload['overall_status']}`",
        f"- Variante : `{payload['request_summary']['variant_id']}`",
        f"- Profil : `{payload['request_summary']['simready_profile']}@{payload['request_summary']['profile_version']}`",
        f"- Affectation de propriétés : `{payload['request_summary']['property_assignment_intent']}`",
        f"- USD final : `{payload['final_artifacts']['final_usd_path']}`",
        f"- Aperçu : `{payload['final_artifacts']['render_preview_path']}`",
        f"- Film diagnostique : `{payload['final_artifacts']['diagnostic_video_path']}`",
        "",
        "## Photos",
        "",
    ]
    lines.extend(f"- `{path}`" for path in payload["final_artifacts"]["render_photo_paths"])
    lines.extend(["", "## Résultats ordonnés", ""])
    for item in payload["ordered_stage_results"]:
        lines.append(f"- `{item['stage']}` : `{item['status']}` — `{item['report_path']}`")
    lines.extend(["", "## Limites", ""])
    lines.extend(f"- {item}" for item in payload["claim_boundaries"])
    lines.extend(["", "## Suite recommandée", ""])
    lines.extend(f"- {item}" for item in payload["recommended_next_work"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--asset-context-report", required=True, type=Path)
    parser.add_argument("--render-reference-report", required=True, type=Path)
    parser.add_argument("--turntable-report", required=True, type=Path)
    parser.add_argument("--render-attestation", required=True, type=Path)
    parser.add_argument("--preview", required=True, type=Path)
    parser.add_argument("--profile", default="Prop-Robotics-Neutral")
    parser.add_argument("--profile-version", default="1.0.0")
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--markdown-report", required=True, type=Path)
    args = parser.parse_args()

    output_root = args.output_root.resolve(strict=True)
    ordered: list[dict[str, Any]] = []
    payloads: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}
    for name in EXPECTED_PHASE_STAGES[:5]:
        path = phase_path(output_root, name, args.job_id).resolve(strict=True)
        payload = load(path)
        paths[name], payloads[name] = path, payload
        ordered.append(stage_entry(name, path, payload))

    f10_path = (output_root / "f10" / args.run_id / "phase-f10.json").resolve(strict=True)
    f10_payload = load(f10_path)
    paths["f10"], payloads["f10"] = f10_path, f10_payload
    ordered.append(stage_entry("f10", f10_path, f10_payload))
    for name in EXPECTED_PHASE_STAGES[6:]:
        path = phase_path(output_root, name, args.run_id).resolve(strict=True)
        payload = load(path)
        paths[name], payloads[name] = path, payload
        ordered.append(stage_entry(name, path, payload))

    context_path = args.asset_context_report.resolve(strict=True)
    context = load(context_path)
    if (
        context.get("schema_version") != "1.0.0"
        or context.get("status") != "passed"
        or context.get("passed") is not True
    ):
        raise SystemExit("contexte d'actif non validé")

    final_validation = payloads["validate-simready"]
    final_usd = one_existing_path(final_validation.get("output_paths"), "validate-simready")
    repair_paths = [
        Path(value).resolve()
        for value in final_validation.get("child_reports", [])
        if isinstance(value, str) and Path(value).name == "repair-loop.json"
    ]
    if len(repair_paths) != 1 or not repair_paths[0].is_file():
        raise SystemExit("rapport de boucle de réparation absent ou ambigu")
    repair_loop = load(repair_paths[0])
    repair_status = repair_loop.get("status")
    if repair_status not in {"passed", "needs_rerun"}:
        raise SystemExit("statut de réparation invalide")
    if repair_loop.get("passed") is not (repair_status == "passed"):
        raise SystemExit("statut et booléen de réparation incohérents")
    if repair_loop.get("final_usd_path") != final_usd:
        raise SystemExit("USD final différent de la boucle de réparation")
    if strict_phase_status(final_validation, "validate-simready") != repair_status:
        raise SystemExit("statut du validateur final différent de la réparation")

    preview = args.preview.resolve(strict=True)
    render_reference_path = args.render_reference_report.resolve(strict=True)
    render_reference = load(render_reference_path)
    require_reference_passed(render_reference, "rendu OVRTX")
    if (
        render_reference.get("asset_path") != final_usd
        or render_reference.get("output_image_path") != str(preview)
        or render_reference.get("generated_files") != [str(preview)]
    ):
        raise SystemExit("lignée du rendu OVRTX incohérente")

    turntable_path = args.turntable_report.resolve(strict=True)
    turntable = load(turntable_path)
    require_reference_passed(turntable, "turntable OVRTX")
    frame_paths_raw = turntable.get("generated_files")
    if (
        turntable.get("asset_path") != final_usd
        or turntable.get("frames_requested") != 24
        or turntable.get("frames_rendered") != 24
        or not isinstance(frame_paths_raw, list)
        or len(frame_paths_raw) != 24
        or len(set(frame_paths_raw)) != 24
    ):
        raise SystemExit("lignée du turntable OVRTX incohérente")
    frame_paths = [Path(value).resolve(strict=True) for value in frame_paths_raw]

    attestation_path = args.render_attestation.resolve(strict=True)
    attestation = load(attestation_path)
    require_reference_passed(attestation, "attestation média")
    if (
        attestation.get("schema_version") != "1.0.0"
        or attestation.get("claim_scope") != "omniverse_visual_diagnostic_only"
        or attestation.get("source_asset_path") != final_usd
        or attestation.get("preview_path") != str(preview)
        or attestation.get("turntable_frame_paths") != [str(path) for path in frame_paths]
        or attestation.get("ovrtx_render_report") != str(render_reference_path)
        or attestation.get("ovrtx_turntable_report") != str(turntable_path)
        or attestation.get("simulation_validated") is not False
        or attestation.get("physical_simulation_validated") is not False
        or attestation.get("dyno_validated") is not False
        or attestation.get("performance_1600hp_validated") is not False
    ):
        raise SystemExit("attestation média ou limites de revendication incohérentes")
    photos_raw = attestation.get("photo_paths")
    if not isinstance(photos_raw, list) or len(photos_raw) != 4 or len(set(photos_raw)) != 4:
        raise SystemExit("quatre photos distinctes sont requises")
    photos = [Path(value).resolve(strict=True) for value in photos_raw]
    movie = Path(str(attestation.get("diagnostic_video_path", ""))).resolve(strict=True)
    if movie.suffix.lower() != ".mp4" or movie.stat().st_size <= 0:
        raise SystemExit("film MP4 diagnostique absent")
    checksum_path = Path(str(attestation.get("checksum_manifest_path", ""))).resolve(strict=True)
    media = [preview, *photos, movie]
    media_sha = attestation.get("media_sha256")
    actual_sha = {str(path): sha256(path) for path in media}
    if media_sha != actual_sha:
        raise SystemExit("checksums média incohérents")
    expected_checksum = "".join(f"{actual_sha[str(path)]}  {path.name}\n" for path in media)
    if checksum_path.read_text(encoding="utf-8") != expected_checksum:
        raise SystemExit("manifeste de checksums média incohérent")

    ordered.append(
        {
            "stage": "render-ovrtx",
            "report_path": str(render_reference_path),
            "status": "passed",
            "input_artifacts": [final_usd],
            "output_artifacts": [str(preview), *[str(path) for path in photos], str(movie)],
            "blocker_reason": None,
            "rerun_reason": None,
        }
    )
    if [item["stage"] for item in ordered] != [*EXPECTED_PHASE_STAGES, "render-ovrtx"]:
        raise SystemExit("ordre des quinze étapes incohérent")

    overall = repair_status
    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "overall_status": overall,
        "passed": overall == "passed",
        "request_summary": {
            "source_asset_path": context.get("source_asset_path"),
            "detected_source_format": context.get("source_format"),
            "output_root": str(output_root),
            "job_id": args.job_id,
            "run_id": args.run_id,
            "variant_id": context.get("variant_id"),
            "simready_profile": args.profile,
            "profile_version": args.profile_version,
            "property_assignment_intent": "run",
        },
        "asset_context": {
            "report_path": str(context_path),
            "identity": context.get("likely_identity"),
            "confidence": context.get("confidence"),
            "evidence": context.get("evidence", []),
        },
        "ordered_stage_results": ordered,
        "content_agents": {
            "preflight_report": str(paths["preflight"]),
            "material_report": str(paths["material"]),
            "physics_report": str(paths["physics"]),
            "render_report": str(render_reference_path),
            "turntable_report": str(turntable_path),
            "service_urls": {
                "renderer": "from-verified-preflight-manifest",
                "material": "from-verified-preflight-manifest",
                "physics": "from-verified-preflight-manifest",
            },
            "credentials": "redacted",
        },
        "conformance_and_validation": {
            "conform_report": str(paths["conform"]),
            "repair_loop_report": str(repair_paths[0]),
            "repair_loop": repair_loop,
            "final_disposition": overall,
        },
        "validation_scope": {
            "simready_validated": overall == "passed",
            "physical_simulation_validated": False,
            "dyno_validated": False,
            "performance_1600hp_validated": False,
        },
        "final_artifacts": {
            "final_usd_path": final_usd,
            "render_preview_path": str(preview),
            "render_photo_paths": [str(path) for path in photos],
            "diagnostic_video_path": str(movie),
            "render_checksum_manifest_path": str(checksum_path),
            "render_reference_report": str(render_reference_path),
            "render_turntable_report": str(turntable_path),
            "render_attestation_report": str(attestation_path),
            "package_root": None,
            "package_validation_report": None,
            "markdown_report_path": str(args.markdown_report.resolve()),
            "json_report_path": str(args.report.resolve()),
        },
        "claim_boundaries": [
            "SimReady décrit ici la préparation et les validateurs USD, pas une simulation moteur physique",
            "les photos et le film sont des visualisations OVRTX diagnostiques, pas un essai de fonctionnement",
            "aucune libération fabrication, impression métal/titane, sécurité ou endurance",
            "aucune preuve de combustion, puissance 1600 ch, couple ou performance dyno",
        ],
        "recommended_next_work": [
            "résoudre tout requirement SimReady encore classé needs_rerun",
            "rendre séparément la cinématique F7 sur le banc avec sa mention à sec",
            "calibrer matériaux, interfaces, charges et solveurs avec mesures",
            "exécuter ensuite les cas physiques et comparer aux essais instrumentés",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_report.write_text(markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
