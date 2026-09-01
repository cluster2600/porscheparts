#!/usr/bin/env python3
"""Construit le rapport d'ecarts F12 du moteur 917 complet.

Ce script audite des preuves; il ne cree ni geometrie, ni resultat de calcul,
ni autorisation de fabrication. Une valeur declaree dans le registre n'est
jamais suffisante sans preuve typee, hachee et relue depuis le disque.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


ASSET_ID = "porsche-917-whole-engine-reengineering-f12"
ALL_VARIANTS = ("917_30_turbo_5374", "type_912_4_5_na")
TURBO_VARIANT = ("917_30_turbo_5374",)


@dataclass
class EvidenceRegistry:
    """Interdit qu'un même paquet satisfasse des claims incompatibles."""

    manifest_digests: dict[str, str] = field(default_factory=dict)
    manifest_paths: dict[Path, str] = field(default_factory=dict)
    evidence_ids: dict[str, str] = field(default_factory=dict)
    artifact_digests: dict[str, str] = field(default_factory=dict)
    artifact_paths: dict[Path, str] = field(default_factory=dict)


WORKSTREAM_RULES: dict[str, dict[str, Any]] = {
    "provenance": {
        "status_field": "provenance_status",
        "ready_status": "verified",
        "required_fields": (),
        "evidence_kind": "family_provenance_report",
    },
    "parametric_geometry": {
        "status_field": "parametric_geometry_status",
        "ready_status": "validated",
        "required_fields": ("parametric_master",),
        "evidence_kind": "family_parametric_geometry_report",
    },
    "interfaces_tolerances": {
        "status_field": "interfaces_tolerances_status",
        "ready_status": "validated",
        "required_fields": ("datum_scheme", "tolerance_stack_report"),
        "evidence_kind": "family_interfaces_tolerances_report",
    },
    "material_mass": {
        "status_field": "material_mass_status",
        "ready_status": "characterized",
        "required_fields": ("material_specification", "mass_kg"),
        "evidence_kind": "family_material_mass_report",
    },
    "manufacturing": {
        "status_field": "manufacturing_status",
        "ready_status": "qualified",
        "required_fields": ("manufacturing_route", "manufacturing_plan"),
        "evidence_kind": "family_manufacturing_qualification_report",
    },
    "physics": {
        "status_field": "physics_status",
        "ready_status": "validated_and_correlated",
        "required_fields": (
            "physics_model_ids",
            "reference_solver_validated",
            "physical_correlation_validated",
        ),
        "evidence_kind": "family_reference_physics_correlation_report",
    },
    "verification_test": {
        "status_field": "test_status",
        "ready_status": "passed",
        "required_fields": ("test_plan",),
        "evidence_kind": "family_verification_test_report",
    },
}


# Limite de confiance intentionnelle. Ces valeurs ne sont pas configurables par
# le contrat JSON. Le jour où un vérificateur existe, le code devra réellement
# l'appeler et contrôler son attestation avant de changer cette frontière.
RUNTIME_VERIFIERS: dict[str, bool] = {
    "cryptographic_release_authority": False,
    "reference_solver_attestation_verifier": False,
    "manufacturing_qualification_attestation_verifier": False,
    "instrumented_bench_attestation_verifier": False,
    "physicsnemo_dataset_split_ood_verifier": False,
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_present(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def resolve_evidence_path(reference: str, project_root: Path) -> Path:
    path = Path(reference).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def _non_empty_strings(data: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return all(isinstance(data.get(key), str) and data[key].strip() for key in keys)


def _valid_issued_at(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _verify_manifest_artifacts(
    manifest: dict[str, Any], manifest_path: Path
) -> tuple[bool, list[str], list[tuple[Path, str]]]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return False, ["manifest_artifacts_missing"], []
    findings: list[str] = []
    verified: list[tuple[Path, str]] = []
    seen_paths: set[Path] = set()
    seen_digests: set[str] = set()
    for index, artifact in enumerate(artifacts):
        prefix = f"artifact_{index}"
        if not isinstance(artifact, dict):
            findings.append(f"{prefix}_not_an_object")
            continue
        path_ref = artifact.get("path")
        expected_hash = artifact.get("sha256")
        role = artifact.get("role")
        if not _non_empty_strings(artifact, ("path", "sha256", "role")):
            findings.append(f"{prefix}_path_sha256_or_role_missing")
            continue
        if len(str(expected_hash)) != 64:
            findings.append(f"{prefix}_sha256_invalid")
            continue
        path = resolve_evidence_path(str(path_ref), manifest_path.parent)
        digest = str(expected_hash).lower()
        if path in seen_paths or digest in seen_digests:
            findings.append(f"{prefix}_duplicate_within_manifest")
            continue
        seen_paths.add(path)
        seen_digests.add(digest)
        if not path.is_file():
            findings.append(f"{prefix}_missing")
            continue
        if sha256(path) != digest:
            findings.append(f"{prefix}_sha256_mismatch")
            continue
        if not isinstance(role, str) or not role.strip():
            findings.append(f"{prefix}_role_invalid")
            continue
        verified.append((path, digest))
    return not findings, findings, verified


def _registry_conflicts(
    registry: EvidenceRegistry,
    *,
    claim_id: str,
    evidence_id: str,
    manifest_path: Path,
    manifest_digest: str,
    artifacts: list[tuple[Path, str]],
) -> list[str]:
    findings: list[str] = []
    checks: tuple[tuple[str, Any, dict[Any, str]], ...] = (
        ("manifest_digest", manifest_digest, registry.manifest_digests),
        ("manifest_path", manifest_path, registry.manifest_paths),
        ("evidence_id", evidence_id, registry.evidence_ids),
    )
    for label, key, index in checks:
        previous = index.get(key)
        if previous is not None and previous != claim_id:
            findings.append(f"{label}_reused_by_incompatible_claim:{previous}")
    for path, digest in artifacts:
        previous_digest = registry.artifact_digests.get(digest)
        if previous_digest is not None and previous_digest != claim_id:
            findings.append(
                f"artifact_digest_reused_by_incompatible_claim:{previous_digest}"
            )
        previous_path = registry.artifact_paths.get(path)
        if previous_path is not None and previous_path != claim_id:
            findings.append(
                f"artifact_path_reused_by_incompatible_claim:{previous_path}"
            )
    return findings


def _register_evidence(
    registry: EvidenceRegistry,
    *,
    claim_id: str,
    evidence_id: str,
    manifest_path: Path,
    manifest_digest: str,
    artifacts: list[tuple[Path, str]],
) -> None:
    registry.manifest_digests[manifest_digest] = claim_id
    registry.manifest_paths[manifest_path] = claim_id
    registry.evidence_ids[evidence_id] = claim_id
    for path, digest in artifacts:
        registry.artifact_digests[digest] = claim_id
        registry.artifact_paths[path] = claim_id


def verify_evidence_manifest(
    reference: Any,
    project_root: Path,
    *,
    family_id: str,
    workstream_id: str,
    evidence_kind: str,
    variant_ids: tuple[str, ...],
    registry: EvidenceRegistry,
) -> tuple[bool, str]:
    """Relit un manifeste typé et re-hache chacun de ses artefacts."""

    if not isinstance(reference, dict):
        return False, "evidence_reference_not_an_object"
    raw_path = reference.get("path")
    expected_hash = reference.get("sha256")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return False, "evidence_manifest_path_missing"
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        return False, "evidence_manifest_sha256_missing_or_invalid"
    manifest_path = resolve_evidence_path(raw_path, project_root)
    if not manifest_path.is_file():
        return False, "evidence_manifest_missing"
    manifest_digest = sha256(manifest_path)
    if manifest_digest != expected_hash.lower():
        return False, "evidence_manifest_sha256_mismatch"
    try:
        manifest = load_json(manifest_path)
    except (OSError, json.JSONDecodeError, ValueError):
        return False, "evidence_manifest_not_valid_json_object"

    claim_id = f"family.{family_id}.{workstream_id}"
    required_strings = (
        "evidence_id",
        "evidence_kind",
        "claim_id",
        "asset_id",
        "family_id",
        "workstream_id",
        "revision",
    )
    if manifest.get("schema_version") != "1.0.0" or not _non_empty_strings(
        manifest, required_strings
    ):
        return False, "evidence_manifest_schema_or_identifiers_incomplete"
    expected_identifiers = {
        "asset_id": ASSET_ID,
        "family_id": family_id,
        "workstream_id": workstream_id,
        "claim_id": claim_id,
        "evidence_kind": evidence_kind,
    }
    for key, expected in expected_identifiers.items():
        if manifest.get(key) != expected:
            return False, f"evidence_manifest_{key}_mismatch"
    manifest_variants = manifest.get("variant_ids")
    if (
        not isinstance(manifest_variants, list)
        or not manifest_variants
        or not all(isinstance(item, str) and item.strip() for item in manifest_variants)
        or set(manifest_variants) != set(variant_ids)
    ):
        return False, "evidence_manifest_variant_scope_mismatch"
    if not _valid_issued_at(manifest.get("issued_at")):
        return False, "evidence_manifest_issued_at_invalid"

    producer = manifest.get("producer")
    method = manifest.get("method")
    result = manifest.get("result")
    if not isinstance(producer, dict) or not _non_empty_strings(
        producer, ("name", "role", "organization")
    ):
        return False, "evidence_manifest_producer_incomplete"
    if not isinstance(method, dict) or not _non_empty_strings(
        method, ("name", "description")
    ):
        return False, "evidence_manifest_method_incomplete"
    if not isinstance(result, dict) or result.get("status") != "passed":
        return False, "evidence_manifest_result_not_passed"
    if result.get("measured_or_simulated") not in {
        "measured",
        "simulated",
        "manufactured",
        "tested",
        "reviewed",
        "documented",
    }:
        return False, "evidence_manifest_result_class_invalid"
    acceptance = result.get("acceptance_criteria")
    if not isinstance(acceptance, list) or not acceptance or not all(
        isinstance(item, str) and item.strip() for item in acceptance
    ):
        return False, "evidence_manifest_acceptance_criteria_missing"

    artifacts_ok, artifact_findings, artifacts = _verify_manifest_artifacts(
        manifest, manifest_path
    )
    if not artifacts_ok:
        return False, ";".join(artifact_findings)
    conflicts = _registry_conflicts(
        registry,
        claim_id=claim_id,
        evidence_id=manifest["evidence_id"],
        manifest_path=manifest_path,
        manifest_digest=manifest_digest,
        artifacts=artifacts,
    )
    if conflicts:
        return False, ";".join(conflicts)
    _register_evidence(
        registry,
        claim_id=claim_id,
        evidence_id=manifest["evidence_id"],
        manifest_path=manifest_path,
        manifest_digest=manifest_digest,
        artifacts=artifacts,
    )
    return True, "typed_manifest_and_artifacts_verified"


def verify_evidence_refs(
    refs: Any,
    project_root: Path,
    family_id: str,
    workstream_id: str,
    evidence_kind: str,
    variant_ids: tuple[str, ...],
    registry: EvidenceRegistry,
) -> tuple[bool, list[str]]:
    if not isinstance(refs, list) or not refs:
        return False, ["typed_evidence_missing"]
    findings: list[str] = []
    for index, reference in enumerate(refs):
        ready, finding = verify_evidence_manifest(
            reference,
            project_root,
            family_id=family_id,
            workstream_id=workstream_id,
            evidence_kind=evidence_kind,
            variant_ids=variant_ids,
            registry=registry,
        )
        if not ready:
            findings.append(f"evidence_{index}:{finding}")
    return not findings, findings


def required_field_ready(family: dict[str, Any], field: str) -> bool:
    value = family.get(field)
    if field == "mass_kg":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0
    if field in {"reference_solver_validated", "physical_correlation_validated"}:
        return value is True
    if field == "physics_model_ids":
        return isinstance(value, list) and bool(value) and all(
            isinstance(item, str) and item for item in value
        )
    return is_present(value)


def evaluate_workstream(
    family: dict[str, Any],
    workstream_id: str,
    project_root: Path,
    registry: EvidenceRegistry,
) -> dict[str, Any]:
    rule = WORKSTREAM_RULES[workstream_id]
    status = family.get(rule["status_field"])
    missing_fields = [
        field
        for field in rule["required_fields"]
        if not required_field_ready(family, field)
    ]
    refs = family.get("workstream_evidence_refs", {}).get(workstream_id)
    variant_ids = (
        TURBO_VARIANT
        if family.get("visual_variant") == "917_30_only"
        else ALL_VARIANTS
    )
    evidence_ok, evidence_findings = verify_evidence_refs(
        refs,
        project_root,
        family["id"],
        workstream_id,
        rule["evidence_kind"],
        variant_ids,
        registry,
    )
    ready = (
        status == rule["ready_status"]
        and not missing_fields
        and evidence_ok
    )
    gaps: list[str] = []
    if status != rule["ready_status"]:
        gaps.append(f"status:{status or 'missing'}")
    gaps.extend(f"field:{field}" for field in missing_fields)
    gaps.extend(evidence_findings)
    return {
        "id": workstream_id,
        "status": "ready" if ready else "blocked",
        "declared_status": status,
        "evidence_kind": rule["evidence_kind"],
        "variant_ids": list(variant_ids),
        "evidence_package_ready": evidence_ok,
        "missing": gaps,
    }


def family_variant(family: dict[str, Any]) -> str:
    return "917_30_only" if family.get("variant") == "917_30_only" else "base_and_turbo"


def duplicate_ids(items: list[dict[str, Any]]) -> list[str]:
    counts = Counter(item.get("id") for item in items)
    return sorted(str(item) for item, count in counts.items() if count > 1)


def audit_contract_integrity(
    contract: dict[str, Any], visual: dict[str, Any], visual_path: Path
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    registry = contract.get("family_registry")
    visual_families = visual.get("component_families")
    if not isinstance(registry, list):
        return ["family_registry_missing"], {}
    if not isinstance(visual_families, list):
        return ["visual_component_families_missing"], {}

    if contract.get("asset", {}).get("id") != ASSET_ID:
        errors.append("asset_id_mismatch")
    declared_workstreams = contract.get("workstream_contracts", {})
    for workstream_id, rule in WORKSTREAM_RULES.items():
        declared = declared_workstreams.get(workstream_id, {})
        if declared.get("ready_status") != rule["ready_status"]:
            errors.append(f"workstream_ready_status_mismatch:{workstream_id}")
        if declared.get("evidence_kind") != rule["evidence_kind"]:
            errors.append(f"workstream_evidence_kind_mismatch:{workstream_id}")
    declared_verifiers = contract.get("runtime_verifier_contract", {})
    for verifier_id in RUNTIME_VERIFIERS:
        if declared_verifiers.get(verifier_id) != "not_implemented":
            errors.append(f"runtime_verifier_contract_mismatch:{verifier_id}")
    if declared_verifiers.get("configuration_is_authority") is not False:
        errors.append("runtime_configuration_cannot_be_release_authority")

    expected_hash = contract.get("asset", {}).get("upstream_visual_registry_sha256")
    actual_hash = sha256(visual_path)
    if actual_hash != expected_hash:
        errors.append("upstream_visual_registry_sha256_mismatch")
    if visual.get("status") != "F1_complete_functional_family_assembly_not_manufacturing_geometry":
        errors.append("upstream_visual_status_not_fail_closed")

    registry_duplicates = duplicate_ids(registry)
    visual_duplicates = duplicate_ids(visual_families)
    if registry_duplicates:
        errors.append("duplicate_registry_family_ids:" + ",".join(registry_duplicates))
    if visual_duplicates:
        errors.append("duplicate_visual_family_ids:" + ",".join(visual_duplicates))

    registry_by_id = {item.get("id"): item for item in registry}
    visual_by_id = {item.get("id"): item for item in visual_families}
    missing = sorted(set(visual_by_id) - set(registry_by_id))
    extra = sorted(set(registry_by_id) - set(visual_by_id))
    if missing:
        errors.append("registry_missing_families:" + ",".join(missing))
    if extra:
        errors.append("registry_extra_families:" + ",".join(extra))

    accepted_routes = set(contract.get("accepted_manufacturing_routes", {}))
    physics_models = set(contract.get("physical_model_catalogue", {}))
    for family_id in sorted(set(registry_by_id) & set(visual_by_id)):
        registered = registry_by_id[family_id]
        observed = visual_by_id[family_id]
        comparisons = {
            "visual_count": observed.get("count"),
            "visual_variant": family_variant(observed),
            "source_confidence": observed.get("confidence"),
        }
        for field, expected in comparisons.items():
            if registered.get(field) != expected:
                errors.append(f"family_mismatch:{family_id}:{field}")
        if registered.get("manufacturing_route") not in accepted_routes:
            errors.append(f"unsupported_route:{family_id}")
        unknown_models = sorted(set(registered.get("physics_model_ids", [])) - physics_models)
        if unknown_models:
            errors.append(
                f"unknown_physics_models:{family_id}:" + ",".join(unknown_models)
            )

    na_count = sum(
        int(item.get("count", 0))
        for item in visual_families
        if item.get("variant") != "917_30_only"
    )
    turbo_delta = sum(
        int(item.get("count", 0))
        for item in visual_families
        if item.get("variant") == "917_30_only"
    )
    snapshot = contract.get("visual_snapshot", {})
    expected_snapshot = {
        "family_count": len(visual_families),
        "na_visual_instance_count": na_count,
        "turbo_only_visual_instance_delta": turbo_delta,
        "turbo_visual_instance_count": na_count + turbo_delta,
    }
    for field, expected in expected_snapshot.items():
        if snapshot.get(field) != expected:
            errors.append(f"visual_snapshot_mismatch:{field}")
    if snapshot.get("real_bom_item_count") is not None:
        errors.append("real_bom_item_count_must_remain_null_in_f12")
    if snapshot.get("real_bom_complete") is not False:
        errors.append("real_bom_cannot_be_complete_in_f12")

    backlog = contract.get("unbounded_bom_backlog")
    if not isinstance(backlog, list) or not backlog:
        errors.append("unbounded_bom_backlog_missing")
        backlog = []
    if duplicate_ids(backlog):
        errors.append("duplicate_backlog_ids")
    for item in backlog:
        if item.get("quantity") is not None or item.get("dimensions") is not None:
            errors.append(f"invented_backlog_data:{item.get('id')}")
        if item.get("status") not in {"not_enumerated", "topology_not_reconstructed"}:
            errors.append(f"backlog_status_not_fail_closed:{item.get('id')}")

    return errors, {
        "family_count": len(visual_families),
        "na_visual_instance_count": na_count,
        "turbo_only_visual_instance_delta": turbo_delta,
        "turbo_visual_instance_count": na_count + turbo_delta,
        "real_bom_item_count": None,
        "real_bom_complete": False,
        "unbounded_backlog_category_count": len(backlog),
    }


def evaluate(
    project_root: Path, contract_path: Path, visual_registry_path: Path
) -> dict[str, Any]:
    project_root = project_root.resolve()
    contract_path = contract_path.resolve()
    visual_registry_path = visual_registry_path.resolve()
    contract = load_json(contract_path)
    visual = load_json(visual_registry_path)

    integrity_errors, bom_assessment = audit_contract_integrity(
        contract, visual, visual_registry_path
    )
    family_reports: list[dict[str, Any]] = []
    gap_counter: Counter[str] = Counter()
    evidence_registry = EvidenceRegistry()

    for family in contract.get("family_registry", []):
        if not isinstance(family, dict) or not isinstance(family.get("id"), str):
            continue
        workstreams = [
            evaluate_workstream(
                family, workstream_id, project_root, evidence_registry
            )
            for workstream_id in WORKSTREAM_RULES
        ]
        ready_by_id = {item["id"]: item["status"] == "ready" for item in workstreams}
        evidence_package_ready = all(ready_by_id.values())
        release = family.get("release") if isinstance(family.get("release"), dict) else {}
        runtime_family_release_ready = all(
            RUNTIME_VERIFIERS[verifier_id]
            for verifier_id in (
                "cryptographic_release_authority",
                "reference_solver_attestation_verifier",
                "manufacturing_qualification_attestation_verifier",
            )
        )
        functional_authorized = (
            evidence_package_ready
            and release.get("status") == "released"
            and release.get("functional") is True
            and runtime_family_release_ready
        )
        assembly_authorized = (
            functional_authorized
            and release.get("assembly") is True
            and RUNTIME_VERIFIERS["cryptographic_release_authority"]
        )
        printable_authorized = (
            functional_authorized
            and family.get("manufacturing_route") == "lpbf"
            and release.get("printable") is True
            and RUNTIME_VERIFIERS[
                "manufacturing_qualification_attestation_verifier"
            ]
        )
        for item in workstreams:
            if item["status"] != "ready":
                gap_counter[item["id"]] += 1
        declared_conflict = any(
            release.get(flag) is True
            for flag in ("functional", "printable", "assembly")
        ) and (not evidence_package_ready or not runtime_family_release_ready)
        family_reports.append(
            {
                "id": family["id"],
                "visual_reference": {
                    "count": family.get("visual_count"),
                    "variant": family.get("visual_variant"),
                    "confidence": family.get("source_confidence"),
                    "is_real_bom_evidence": False,
                },
                "candidate_manufacturing_route": family.get("manufacturing_route"),
                "workstreams": workstreams,
                "ready_workstream_count": sum(ready_by_id.values()),
                "evidence_package_ready": evidence_package_ready,
                "release_is_separate_from_evidence_package": True,
                "release_claim_conflict": declared_conflict,
                "functional_release_authorized": functional_authorized,
                "print_release_authorized": printable_authorized,
                "assembly_release_authorized": assembly_authorized,
            }
        )

    backlog_open = bool(contract.get("unbounded_bom_backlog"))
    whole_gates = contract.get("whole_engine_gates", {})
    all_declared_gates_passed = (
        isinstance(whole_gates, dict)
        and bool(whole_gates)
        and all(value is True for value in whole_gates.values())
    )
    all_family_evidence_packages_ready = bool(family_reports) and all(
        item["evidence_package_ready"] for item in family_reports
    )
    no_integrity_errors = not integrity_errors
    whole_engine_evidence_package_ready = (
        no_integrity_errors
        and not backlog_open
        and all_declared_gates_passed
        and all_family_evidence_packages_ready
    )
    runtime_engine_release_ready = all(RUNTIME_VERIFIERS.values())
    whole_engine_release = (
        whole_engine_evidence_package_ready
        and runtime_engine_release_ready
    )
    physics_ready = bool(family_reports) and all(
        next(
            item
            for item in family["workstreams"]
            if item["id"] == "physics"
        )["status"]
        == "ready"
        for family in family_reports
    )
    physicsnemo_evidence_package_ready = (
        whole_gates.get("physicsnemo_training_authorized") is True
        and physics_ready
        and whole_gates.get("reference_multiphysics_correlated") is True
        and not backlog_open
        and no_integrity_errors
    )
    physicsnemo_authorized = (
        physicsnemo_evidence_package_ready
        and RUNTIME_VERIFIERS["reference_solver_attestation_verifier"]
        and RUNTIME_VERIFIERS["physicsnemo_dataset_split_ood_verifier"]
        and RUNTIME_VERIFIERS["cryptographic_release_authority"]
    )
    runtime_verifier_report = {
        verifier_id: {
            "implementation_status": "implemented" if implemented else "not_implemented",
            "verified": False,
            "configuration_can_override": False,
        }
        for verifier_id, implemented in RUNTIME_VERIFIERS.items()
    }

    return {
        "schema_version": "1.0.0",
        "phase": "F12",
        "report_status": "passed" if no_integrity_errors else "failed",
        "engineering_status": (
            "released"
            if whole_engine_release
            else (
                "evidence_package_ready_release_blocked"
                if whole_engine_evidence_package_ready
                else "blocked"
            )
        ),
        "asset_id": contract.get("asset", {}).get("id"),
        "contract_integrity_errors": integrity_errors,
        "bom_assessment": {
            **bom_assessment,
            "status": "visual_snapshot_not_real_bom",
            "why_271_is_not_a_bom": [
                "the upstream file explicitly stops at visual family assembly",
                "the visual count excludes an unbounded small-parts and internal-passage backlog",
                "no procurement, fastener, seal, sensor or route-qualified item register exists",
            ],
        },
        "family_gap_summary": {
            "family_count": len(family_reports),
            "families_with_functional_release": sum(
                item["functional_release_authorized"] for item in family_reports
            ),
            "families_with_print_release": sum(
                item["print_release_authorized"] for item in family_reports
            ),
            "families_with_evidence_package_ready": sum(
                item["evidence_package_ready"] for item in family_reports
            ),
            "blocked_family_count": sum(
                not item["functional_release_authorized"] for item in family_reports
            ),
            "blocked_by_workstream": dict(sorted(gap_counter.items())),
        },
        "families": family_reports,
        "unbounded_bom_backlog": contract.get("unbounded_bom_backlog", []),
        "runtime_verifiers": runtime_verifier_report,
        "evidence_package": {
            "whole_engine_ready": whole_engine_evidence_package_ready,
            "all_family_packages_ready": all_family_evidence_packages_ready,
            "declared_whole_engine_gates_passed": all_declared_gates_passed,
            "real_bom_closed": not backlog_open,
            "is_release_authority": False,
        },
        "physicsnemo": {
            "role": "surrogate_after_reference_solver_and_physical_correlation",
            "evidence_package_ready": physicsnemo_evidence_package_ready,
            "training_authorized": physicsnemo_authorized,
            "reason": (
                "runtime solver, dataset/OOD and release attestations verified"
                if physicsnemo_authorized
                else "blocked: typed evidence and true flags cannot replace absent runtime solver, dataset/OOD and cryptographic verifiers"
            ),
        },
        "release": {
            "whole_engine_functional_authorized": whole_engine_release,
            "mixed_route_manufacturing_authorized": whole_engine_release,
            "lpbf_part_package_authorized": whole_engine_release and any(
                item["print_release_authorized"] for item in family_reports
            ),
            "engine_start_authorized": whole_engine_release
            and whole_gates.get("instrumented_engine_bench_passed") is True
            and RUNTIME_VERIFIERS["instrumented_bench_attestation_verifier"]
            and RUNTIME_VERIFIERS["cryptographic_release_authority"],
            "reason": (
                "runtime cryptographic, solver, manufacturing and bench attestations verified"
                if whole_engine_release
                else "blocked: evidence_package_ready is not a release; runtime cryptographic, solver, manufacturing and bench verifiers are not implemented"
            ),
        },
        "scope": "gap audit only; no functional geometry, quantity, material, mass, tolerance, solver result or manufacturing release is inferred",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("twins/reference-917-engine/whole-engine-reengineering-f12.json"),
    )
    parser.add_argument(
        "--visual-registry",
        type=Path,
        default=Path("twins/reference-917-engine/complete-engine-f1.json"),
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    contract = args.contract if args.contract.is_absolute() else root / args.contract
    visual = (
        args.visual_registry
        if args.visual_registry.is_absolute()
        else root / args.visual_registry
    )
    report = evaluate(root, contract, visual)
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["report_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
