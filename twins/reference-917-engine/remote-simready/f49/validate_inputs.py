#!/usr/bin/env python3
"""Bloque le workflow SimReady tant que la paire STEP F49 n'est pas acceptee."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONTRACT = ROOT / "twins/reference-917-engine/simready-head-pair-f49.json"
F43_SHA256 = "38f8ed3071005e5f64156d8670b5a755c98599d8702ef030ff132b7a034f0f24"
FORBIDDEN_STEP_SHA256 = {
    "ca5ad5b5cc7b168946cb93d49adb7409e9e3ac4853b808e86ed8ad5f3477ea0b",
    "196e9b83629b0f5ecacc822153766fcf388da557a6fc30e50f7141f45479c6c9",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_path(value: str, *, root: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"objet JSON attendu: {path}")
    return payload


def add_file_lock_check(
    *,
    root: Path,
    record: dict[str, Any],
    label: str,
    checks: list[dict[str, Any]],
    blockers: list[str],
) -> None:
    path = resolve_path(str(record.get("path", "")), root=root)
    expected = record.get("sha256")
    exists = path.is_file() and not path.is_symlink()
    actual = sha256(path) if exists else None
    passed = exists and isinstance(expected, str) and actual == expected
    checks.append({"id": label, "passed": passed})
    if not passed:
        blockers.append(f"{label}: fichier absent, lien symbolique ou SHA-256 incorrect")


def validate_static_contract(
    contract: dict[str, Any], root: Path
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []
    external = contract["geometry_authority"]["external_skin"]
    for label, record in (
        ("f43_public_report_lock", external["public_report"]),
        ("visible_policy_lock", external["visible_policy"]),
        ("runtime_public_audit_lock", contract["runtime"]["public_audit"]),
        ("material_authority_lock", contract["assignment"]["material_candidate_authority"]),
        ("material_prompt_lock", contract["assignment"]["material_prompt"]),
        ("physics_prompt_lock", contract["assignment"]["physics_prompt"]),
        ("input_manifest_template_lock", contract["input_acceptance"]["manifest_template"]),
        ("input_validator_lock", contract["input_acceptance"]["validator"]),
        ("atomic_commands_lock", contract["atomic_workflow"]["command_contract"]),
    ):
        add_file_lock_check(
            root=root,
            record=record,
            label=label,
            checks=checks,
            blockers=blockers,
        )

    policy = read_json(resolve_path(external["visible_policy"]["path"], root=root))
    authority = policy.get("authority", {})
    visible_policy_passed = (
        authority.get("same_skin_required_for") == ["2V", "4V"]
        and authority.get("global_anisotropic_scaling_allowed") is False
        and authority.get("global_ellipse_or_oval_envelope_allowed") is False
        and authority.get("synthetic_head_envelope_allowed") is False
        and policy.get("historical_lineages_forbidden_from_current_product_gallery")
        == ["f39", "f42"]
    )
    checks.append({"id": "visible_policy_semantics", "passed": visible_policy_passed})
    if not visible_policy_passed:
        blockers.append("visible_policy_semantics: politique F49 incompatible")

    runtime = read_json(resolve_path(contract["runtime"]["public_audit"]["path"], root=root))
    runtime_passed = (
        runtime.get("image", {}).get("pinned_ref") == contract["runtime"]["image_ref"]
        and runtime.get("image", {}).get("os") == "linux"
        and runtime.get("image", {}).get("architecture") == "amd64"
        and runtime.get("public_registry_audit", {}).get("exact_digest_manifest_get_succeeded")
        is True
        and runtime.get("github_workflow", {}).get("conclusion") == "success"
        and runtime.get("unproven", {}).get("nvidia_gpu_visible") is False
        and contract["runtime"].get("current_live_gpu_and_service_readiness") is False
    )
    checks.append({"id": "runtime_scope_is_honest", "passed": runtime_passed})
    if not runtime_passed:
        blockers.append("runtime_scope_is_honest: qualification runtime contradictoire")
    return checks, blockers


def validate_variant(
    *,
    variant: dict[str, Any],
    expected: dict[str, Any],
    root: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    name = str(expected["variant"])
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []
    prefix = f"{name}:"

    actual_path_value = str(variant.get("step_path", ""))
    expected_suffix = str(expected["expected_private_path"])
    normalized = actual_path_value.replace("\\", "/")
    path_matches = normalized.endswith(expected_suffix)
    checks.append({"id": prefix + "expected_private_path", "passed": path_matches})
    if not path_matches:
        blockers.append(prefix + " chemin STEP non canonique")

    lowered = normalized.lower()
    lineage_clean = not any(token in lowered for token in ("/f39", "/f42"))
    checks.append({"id": prefix + "no_forbidden_lineage_path", "passed": lineage_clean})
    if not lineage_clean:
        blockers.append(prefix + " l'ancien lineage F39/F42 est interdit")

    step_path = resolve_path(actual_path_value, root=root)
    exists = step_path.is_file() and not step_path.is_symlink()
    actual_sha = sha256(step_path) if exists else None
    expected_sha = variant.get("step_sha256")
    expected_bytes = variant.get("step_bytes")
    hash_ok = (
        exists
        and isinstance(expected_sha, str)
        and len(expected_sha) == 64
        and actual_sha == expected_sha
        and expected_sha not in FORBIDDEN_STEP_SHA256
        and step_path.stat().st_size == expected_bytes
    )
    checks.append({"id": prefix + "step_file_exists_and_sha256_matches", "passed": hash_ok})
    if not hash_ok:
        blockers.append(prefix + " STEP absent, interdit, ou receipt SHA/taille incorrect")

    header_ok = False
    if exists:
        with step_path.open("rb") as handle:
            header_ok = b"ISO-10303-21;" in handle.read(256)
    checks.append({"id": prefix + "iso_10303_21_header_present", "passed": header_ok})
    if not header_ok:
        blockers.append(prefix + " en-tete STEP ISO-10303-21 absent")

    scalar_gates = {
        "solid_candidate_accepted": variant.get("solid_candidate_accepted") is True,
        "brepcheck_exact_valid": variant.get("brepcheck_exact_valid") is True,
        "bopalgo_fault_count_zero_after_step_roundtrip": variant.get(
            "bopalgo_fault_count_after_step_roundtrip"
        )
        == 0,
        "one_closed_manifold_solid": (
            variant.get("solid_count") == 1
            and variant.get("shell_count") == 1
            and variant.get("free_edge_count") == 0
            and variant.get("nonmanifold_edge_count") == 0
        ),
        "gmsh_volume_mesh_completed": variant.get("gmsh_volume_mesh_completed") is True,
        "external_skin_f43_source_sha256_matches": variant.get(
            "external_skin_f43_source_sha256"
        )
        == F43_SHA256,
        "external_face_signatures_locked_outside_openings": variant.get(
            "external_face_signatures_locked_outside_openings"
        )
        is True,
        "no_global_scale_transform": variant.get("no_global_scale_transform") is True,
        "no_anisotropic_scale": variant.get("no_anisotropic_scale") is True,
        "no_synthetic_external_envelope": variant.get("no_synthetic_external_envelope")
        is True,
        "no_forbidden_lineage": variant.get("no_forbidden_lineage") is True,
    }
    for gate, passed in scalar_gates.items():
        checks.append({"id": prefix + gate, "passed": passed})
        if not passed:
            blockers.append(prefix + f" gate ferme: {gate}")
    return checks, blockers


def validate(
    contract_path: Path, manifest_path: Path
) -> dict[str, Any]:
    root = ROOT
    contract = read_json(contract_path)
    checks, blockers = validate_static_contract(contract, root)

    if not manifest_path.is_file() or manifest_path.is_symlink():
        blockers.append("manifest: absent ou lien symbolique")
        return {
            "schema_version": "1.0.0",
            "phase": "F49",
            "status": "blocked",
            "passed": False,
            "checks": checks,
            "blockers": blockers,
            "next_step": "fournir le manifeste prive de la paire STEP F49 acceptee",
        }

    manifest = read_json(manifest_path)
    status_ok = manifest.get("status") == "ready_for_simready_input_gate"
    checks.append({"id": "manifest_status_ready", "passed": status_ok})
    if not status_ok:
        blockers.append("manifest: statut d'execution non pret")

    transform = manifest.get("transform", {})
    transform_ok = (
        transform.get("scale_xyz") == [1.0, 1.0, 1.0]
        and transform.get("anisotropic_scale") is False
        and transform.get("synthetic_external_envelope") is False
    )
    checks.append({"id": "identity_scale_only", "passed": transform_ok})
    if not transform_ok:
        blockers.append("manifest: seule l'echelle identite [1,1,1] est admise")

    f43_ok = manifest.get("f43_outer_source_sha256") == F43_SHA256
    checks.append({"id": "pair_f43_outer_lock", "passed": f43_ok})
    if not f43_ok:
        blockers.append("manifest: SHA-256 de la peau F43 incorrect")

    for label in ("private_audit", "public_report"):
        record = manifest.get(label, {})
        if not isinstance(record, dict):
            record = {}
        add_file_lock_check(
            root=root,
            record=record,
            label=label + "_lock",
            checks=checks,
            blockers=blockers,
        )

    expected_by_variant = {
        item["variant"]: item for item in contract["geometry_authority"]["future_step_pair"]
    }
    actual_variants = manifest.get("variants", [])
    unique_names = [item.get("variant") for item in actual_variants if isinstance(item, dict)]
    pair_ok = sorted(unique_names) == ["2V", "4V"] and len(unique_names) == 2
    checks.append({"id": "exact_2v_4v_pair", "passed": pair_ok})
    if not pair_ok:
        blockers.append("manifest: exactement une variante 2V et une variante 4V requises")
    else:
        for variant in actual_variants:
            variant_checks, variant_blockers = validate_variant(
                variant=variant,
                expected=expected_by_variant[variant["variant"]],
                root=root,
            )
            checks.extend(variant_checks)
            blockers.extend(variant_blockers)

    passed = not blockers
    return {
        "schema_version": "1.0.0",
        "phase": "F49",
        "status": "ready" if passed else "blocked",
        "passed": passed,
        "source_variants": ["2V", "4V"] if pair_ok else [],
        "f43_outer_source_sha256": F43_SHA256,
        "checks": checks,
        "blockers": blockers,
        "next_step": (
            "run preflight as the first NVIDIA stage"
            if passed
            else "repair and re-audit the F49 solids; do not inspect or convert them"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--permit-blocked", action="store_true")
    args = parser.parse_args()

    try:
        report = validate(args.contract.resolve(), args.manifest.resolve())
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as error:
        report = {
            "schema_version": "1.0.0",
            "phase": "F49",
            "status": "blocked",
            "passed": False,
            "checks": [],
            "blockers": [f"contrat ou manifeste invalide: {error}"],
            "next_step": "corriger le contrat sans lancer de conversion",
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if report["passed"]:
        return 0
    return 0 if args.permit_blocked else 2


if __name__ == "__main__":
    sys.exit(main())
