#!/usr/bin/env python3
"""Valide le contrat F14 de donnees PhysicsNeMo du moteur 917.

Le validateur controle la chaine de provenance, l'immuabilite des artefacts et
les frontieres d'autorite. Il n'entraine aucun modele, ne lance aucun solveur
et ne transforme pas un echantillon structurellement valide en preuve moteur.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


EXPECTED_CASE_IDS = {
    f"CASE-917-F13-{index:03d}" for index in range(1, 13)
}
EXPECTED_MODELS = {"DoMINO", "GeoTransolver", "Transolver", "MeshGraphNet"}
EXPECTED_DATAPIPES = {"DoMINODataPipe", "TransolverDataPipe", "MeshDataset"}
RUNTIME_VERIFIED_MODELS = {"DoMINO", "GeoTransolver", "MeshGraphNet"}
REQUIRED_ARTIFACT_ROLES = {
    "geometry",
    "mesh",
    "solver_config",
    "boundary_conditions",
    "fields",
    "convergence_report",
    "mesh_independence_report",
    "correlation_report",
}
REQUIRED_VERIFICATION_FLAGS = {
    "acceptance_thresholds_predeclared",
    "converged",
    "conservation_passed",
    "mesh_independence_passed",
    "correlated_to_physical_data",
    "uncertainty_quantified",
}
REQUIRED_SAMPLE_IDS = (
    "sample_id",
    "case_id",
    "variant_id",
    "geometry_family_id",
    "operating_point_family_id",
    "physical_test_campaign_id",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
OCI_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _safe_file(root: Path, relative: Any) -> Path | None:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        return None
    candidate = (root / relative).resolve()
    if not _inside(candidate, root.resolve()):
        return None
    if not candidate.is_file() or candidate.is_symlink():
        return None
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _objects_by_name(items: Any, label: str, errors: list[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list) or not items:
        errors.append(f"{label}_missing_or_empty")
        return {}
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{label}_not_object:{index}")
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"{label}_name_missing:{index}")
            continue
        if name in result:
            errors.append(f"{label}_duplicate:{name}")
            continue
        result[name] = item
    return result


def _validate_authority(contract: dict[str, Any], errors: list[str]) -> None:
    boundary = contract.get("authority_boundary")
    if not isinstance(boundary, dict):
        errors.append("authority_boundary_missing")
        return
    if boundary.get("contract_only") is not True:
        errors.append("authority_contract_only_must_be_true")
    if boundary.get("accepted_sample_count") != 0:
        errors.append("authority_accepted_sample_count_must_be_zero")
    if boundary.get("classical_cases_passed") != 0:
        errors.append("authority_classical_cases_passed_must_be_zero")
    for key in (
        "dataset_ready",
        "training_authorized",
        "inference_authorized",
        "engine_simulation_proven",
        "reported_1600_hp_proven",
        "fabrication_authorized",
        "print_release",
        "engine_start_authorized",
    ):
        if boundary.get(key) is not False:
            errors.append(f"authority_must_be_false:{key}")


def _validate_runtime(
    root: Path, contract: dict[str, Any], errors: list[str]
) -> dict[str, Any]:
    runtime = contract.get("runtime")
    if not isinstance(runtime, dict):
        errors.append("runtime_missing")
        return {}
    lock_path = _safe_file(root, runtime.get("image_lock_path"))
    if lock_path is None:
        errors.append("runtime_image_lock_missing_or_unsafe")
        return {}
    try:
        lock = load_json(lock_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"runtime_image_lock_invalid:{exc}")
        return {}
    image = lock.get("image", {})
    immutable = image.get("immutable_reference")
    if runtime.get("immutable_reference") != immutable:
        errors.append("runtime_immutable_reference_mismatch")
    digest = image.get("digest")
    if not isinstance(digest, str) or not OCI_DIGEST_RE.fullmatch(digest):
        errors.append("runtime_image_digest_invalid")
    if lock.get("verification", {}).get("offline_smoke", {}).get(
        "physicsnemo_version"
    ) != runtime.get("physicsnemo_version"):
        errors.append("runtime_physicsnemo_version_mismatch")
    gates = lock.get("release_gates", {})
    for key in (
        "gpu_runtime_verified",
        "ssh_transport_verified_for_current_rental",
        "classical_solver_reference_cases_executed",
        "physicsnemo_surrogate_trained",
        "physical_correlation_completed",
        "engine_simulation_validated",
        "manufacturing_release",
        "print_release",
        "functional_engine_release",
        "vast_long_job_allowed",
    ):
        if gates.get(key) is not False:
            errors.append(f"runtime_lock_gate_must_be_false:{key}")
    if runtime.get("gpu_runtime_verified") is not False:
        errors.append("runtime_gpu_gate_must_be_false")
    if runtime.get("vast_long_job_allowed") is not False:
        errors.append("runtime_vast_gate_must_be_false")
    return lock


def _validate_reference_cases(
    root: Path, contract: dict[str, Any], errors: list[str]
) -> set[str]:
    section = contract.get("reference_cases")
    if not isinstance(section, dict):
        errors.append("reference_cases_missing")
        return set()
    required = section.get("required_case_ids")
    required_set = set(required) if isinstance(required, list) else set()
    if required_set != EXPECTED_CASE_IDS or len(required or []) != len(EXPECTED_CASE_IDS):
        errors.append("reference_case_ids_mismatch")
    if section.get("passed_case_ids") != []:
        errors.append("reference_passed_case_ids_must_be_empty")
    if section.get("all_required_before_whole_engine_training") is not True:
        errors.append("reference_all_required_gate_missing")
    registry_path = _safe_file(root, section.get("registry_path"))
    if registry_path is None:
        errors.append("reference_registry_missing_or_unsafe")
        return required_set
    try:
        registry = load_json(registry_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"reference_registry_invalid:{exc}")
        return required_set
    actual = [item.get("id") for item in registry.get("solver_cases", []) if isinstance(item, dict)]
    if set(actual) != EXPECTED_CASE_IDS or len(actual) != len(EXPECTED_CASE_IDS):
        errors.append("reference_registry_case_ids_mismatch")
    return required_set


def _validate_live_discovery(
    contract: dict[str, Any], known_cases: set[str], errors: list[str]
) -> None:
    discovery = contract.get("live_discovery")
    if not isinstance(discovery, dict):
        errors.append("live_discovery_missing")
        return
    if discovery.get("repository") != "https://github.com/NVIDIA/physicsnemo":
        errors.append("live_discovery_repository_invalid")
    if not isinstance(discovery.get("commit"), str) or not COMMIT_RE.fullmatch(
        discovery["commit"]
    ):
        errors.append("live_discovery_commit_invalid")
    if discovery.get("runtime_pin_compatibility_verified") is not False:
        errors.append("live_discovery_compatibility_gate_must_be_false")

    models = _objects_by_name(discovery.get("candidate_models"), "model", errors)
    if set(models) != EXPECTED_MODELS:
        errors.append("model_menu_mismatch")
    if not 2 <= len(models) <= 4:
        errors.append("model_menu_size_invalid")
    for name, model in models.items():
        repo_path = model.get("repo_path")
        if (
            not isinstance(repo_path, str)
            or Path(repo_path).is_absolute()
            or ".." in Path(repo_path).parts
            or not repo_path.startswith("physicsnemo/models/")
        ):
            errors.append(f"model_repo_path_invalid:{name}")
        refs = model.get("case_refs")
        if not isinstance(refs, list) or not refs:
            errors.append(f"model_case_refs_missing:{name}")
        elif not set(refs).issubset(known_cases):
            errors.append(f"model_case_ref_unknown:{name}")
        if model.get("selection_status") != "candidate_not_selected":
            errors.append(f"model_selection_must_remain_candidate:{name}")
        expected_import = name in RUNTIME_VERIFIED_MODELS
        if model.get("runtime_import_verified") is not expected_import:
            errors.append(f"model_runtime_import_claim_invalid:{name}")

    datapipes = _objects_by_name(
        discovery.get("candidate_datapipes"), "datapipe", errors
    )
    if set(datapipes) != EXPECTED_DATAPIPES:
        errors.append("datapipe_menu_mismatch")
    for name, datapipe in datapipes.items():
        repo_path = datapipe.get("repo_path")
        if (
            not isinstance(repo_path, str)
            or Path(repo_path).is_absolute()
            or ".." in Path(repo_path).parts
            or not repo_path.startswith("physicsnemo/datapipes/")
        ):
            errors.append(f"datapipe_repo_path_invalid:{name}")
        selection_status = datapipe.get("selection_status")
        if selection_status is None:
            errors.append(f"datapipe_selection_status_missing:{name}")
        elif selection_status != "candidate_not_selected":
            errors.append(f"datapipe_selection_must_remain_candidate:{name}")

    examples = discovery.get("reference_examples")
    if not isinstance(examples, list) or len(examples) < 2:
        errors.append("reference_examples_missing")
    else:
        for index, example in enumerate(examples):
            path = example.get("repo_path") if isinstance(example, dict) else None
            if (
                not isinstance(path, str)
                or Path(path).is_absolute()
                or ".." in Path(path).parts
                or not path.startswith("examples/")
            ):
                errors.append(f"reference_example_path_invalid:{index}")


def _validate_contract_sections(contract: dict[str, Any], errors: list[str]) -> None:
    sample_contract = contract.get("sample_contract")
    if not isinstance(sample_contract, dict):
        errors.append("sample_contract_missing")
        return
    roles = sample_contract.get("required_artifact_roles")
    if not isinstance(roles, list) or set(roles) != REQUIRED_ARTIFACT_ROLES:
        errors.append("sample_required_artifact_roles_mismatch")
    flags = sample_contract.get("required_verification_flags")
    if not isinstance(flags, list) or set(flags) != REQUIRED_VERIFICATION_FLAGS:
        errors.append("sample_required_verification_flags_mismatch")
    expected_geometry = {
        "source_kind": "dimensioned_cad",
        "identity_verified": True,
        "scale_verified": True,
        "interface_fidelity_verified": True,
        "raw_scan_used_as_solver_geometry": False,
    }
    if sample_contract.get("required_geometry_state") != expected_geometry:
        errors.append("sample_required_geometry_state_mismatch")
    if sample_contract.get("self_release_forbidden") is not True:
        errors.append("sample_self_release_gate_missing")

    split = contract.get("split_policy")
    if not isinstance(split, dict):
        errors.append("split_policy_missing")
    else:
        if set(split.get("group_keys", [])) != {
            "geometry_family_id",
            "physical_test_campaign_id",
            "operating_point_family_id",
        }:
            errors.append("split_group_keys_mismatch")
        for key in ("train_fraction", "validation_fraction", "test_fraction"):
            if split.get(key) is not None:
                errors.append(f"split_fraction_must_be_null:{key}")
        if split.get("cross_split_group_leakage_allowed") is not False:
            errors.append("split_group_leakage_must_be_forbidden")

    proof = contract.get("proof_chain")
    if not isinstance(proof, dict):
        errors.append("proof_chain_missing")
    else:
        if proof.get("simulation_claim_status") != "not_proven":
            errors.append("proof_simulation_claim_must_be_not_proven")
        if proof.get("physicsnemo_is_proof_by_itself") is not False:
            errors.append("proof_physicsnemo_self_proof_must_be_false")
        if proof.get("omniverse_render_is_proof") is not False:
            errors.append("proof_omniverse_render_must_be_false")

    current = contract.get("current_state")
    if not isinstance(current, dict):
        errors.append("current_state_missing")
    else:
        for key in ("sample_files_seen", "accepted_samples", "rejected_samples"):
            if current.get(key) != 0:
                errors.append(f"current_state_count_must_be_zero:{key}")
        for key in (
            "dataset_manifest_present",
            "split_manifest_present",
            "model_selection_present",
            "training_results_present",
        ):
            if current.get(key) is not False:
                errors.append(f"current_state_gate_must_be_false:{key}")

    release = contract.get("release_gates")
    if not isinstance(release, dict):
        errors.append("release_gates_missing")
    else:
        if release.get("contract_valid") is not True:
            errors.append("release_contract_valid_must_be_true")
        for key, value in release.items():
            if key != "contract_valid" and value is not False:
                errors.append(f"release_gate_must_be_false:{key}")


def _validate_sample(
    sample_path: Path,
    contract: dict[str, Any],
    known_cases: set[str],
) -> list[str]:
    errors: list[str] = []
    try:
        sample = load_json(sample_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"sample_manifest_invalid:{sample_path.name}:{exc}"]
    label = sample.get("sample_id", sample_path.parent.name)
    for key in REQUIRED_SAMPLE_IDS:
        if not isinstance(sample.get(key), str) or not sample[key]:
            errors.append(f"sample_identifier_missing:{label}:{key}")
    if sample.get("case_id") not in known_cases:
        errors.append(f"sample_case_unknown:{label}")

    producer = sample.get("producer")
    if not isinstance(producer, dict):
        errors.append(f"sample_producer_missing:{label}")
    else:
        for key in ("solver_name", "solver_version"):
            if not isinstance(producer.get(key), str) or not producer[key]:
                errors.append(f"sample_producer_field_missing:{label}:{key}")
        if not isinstance(producer.get("container_digest"), str) or not OCI_DIGEST_RE.fullmatch(
            producer["container_digest"]
        ):
            errors.append(f"sample_container_digest_invalid:{label}")
        if not isinstance(producer.get("source_commit"), str) or not COMMIT_RE.fullmatch(
            producer["source_commit"]
        ):
            errors.append(f"sample_source_commit_invalid:{label}")

    required_geometry = contract["sample_contract"]["required_geometry_state"]
    if sample.get("geometry_state") != required_geometry:
        errors.append(f"sample_geometry_state_invalid:{label}")

    flags = sample.get("verification")
    if not isinstance(flags, dict):
        errors.append(f"sample_verification_missing:{label}")
    else:
        for key in REQUIRED_VERIFICATION_FLAGS:
            if flags.get(key) is not True:
                errors.append(f"sample_verification_gate_failed:{label}:{key}")

    rights = sample.get("rights")
    if not isinstance(rights, dict) or rights.get("training_allowed") is not True:
        errors.append(f"sample_training_rights_missing:{label}")
    authority = sample.get("authority_boundary")
    if not isinstance(authority, dict):
        errors.append(f"sample_authority_boundary_missing:{label}")
    else:
        for key in (
            "training_authorized",
            "engine_simulation_proven",
            "reported_1600_hp_proven",
            "fabrication_authorized",
        ):
            if authority.get(key) is not False:
                errors.append(f"sample_authority_must_be_false:{label}:{key}")

    artifacts = sample.get("artifacts")
    role_index: dict[str, dict[str, Any]] = {}
    if not isinstance(artifacts, list):
        errors.append(f"sample_artifacts_missing:{label}")
        artifacts = []
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            errors.append(f"sample_artifact_not_object:{label}:{index}")
            continue
        role = artifact.get("role")
        if role not in REQUIRED_ARTIFACT_ROLES:
            errors.append(f"sample_artifact_role_invalid:{label}:{role}")
            continue
        if role in role_index:
            errors.append(f"sample_artifact_role_duplicate:{label}:{role}")
            continue
        role_index[role] = artifact
        artifact_path = _safe_file(sample_path.parent, artifact.get("path"))
        if artifact_path is None:
            errors.append(f"sample_artifact_missing_or_unsafe:{label}:{role}")
            continue
        expected_hash = artifact.get("sha256")
        if not isinstance(expected_hash, str) or not SHA256_RE.fullmatch(expected_hash):
            errors.append(f"sample_artifact_sha256_invalid:{label}:{role}")
        elif _sha256(artifact_path) != expected_hash:
            errors.append(f"sample_artifact_sha256_mismatch:{label}:{role}")
        if role == "mesh":
            declared_format = artifact.get("format")
            allowed = set(contract["sample_contract"].get("allowed_mesh_formats", []))
            if declared_format not in allowed:
                errors.append(f"sample_mesh_format_invalid:{label}")
    missing = REQUIRED_ARTIFACT_ROLES - set(role_index)
    for role in sorted(missing):
        errors.append(f"sample_artifact_role_missing:{label}:{role}")
    return errors


def evaluate(
    project_root: Path,
    contract_path: Path,
    samples_root: Path | None = None,
) -> dict[str, Any]:
    root = project_root.resolve()
    errors: list[str] = []
    try:
        contract = load_json(contract_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "report_status": "failed",
            "errors": [f"contract_invalid:{exc}"],
            "sample_files_seen": 0,
            "accepted_samples": 0,
            "rejected_samples": 0,
            "dataset_ready": False,
            "training_authorized": False,
            "engine_simulation_proven": False,
            "reported_1600_hp_proven": False,
        }

    if contract.get("schema_version") != "1.0.0":
        errors.append("schema_version_invalid")
    if contract.get("phase") != "F14":
        errors.append("phase_invalid")
    if contract.get("status") != "dataset_contract_ready_zero_samples_training_blocked":
        errors.append("status_invalid")
    _validate_authority(contract, errors)
    _validate_runtime(root, contract, errors)
    known_cases = _validate_reference_cases(root, contract, errors)
    _validate_live_discovery(contract, known_cases, errors)
    _validate_contract_sections(contract, errors)

    if samples_root is None:
        raw_root = contract.get("current_state", {}).get("sample_root", "")
        samples_root = (root / raw_root).resolve()
    sample_files = sorted(samples_root.glob("*/sample.json")) if samples_root.is_dir() else []
    accepted = 0
    rejected = 0
    for sample_file in sample_files:
        sample_errors = _validate_sample(sample_file, contract, known_cases)
        if sample_errors:
            rejected += 1
            errors.extend(sample_errors)
        else:
            accepted += 1

    return {
        "schema_version": "1.0.0",
        "phase": "F14",
        "report_status": "passed" if not errors else "failed",
        "errors": errors,
        "sample_files_seen": len(sample_files),
        "accepted_samples": accepted,
        "rejected_samples": rejected,
        "reference_case_count": len(known_cases),
        "model_candidate_count": len(
            contract.get("live_discovery", {}).get("candidate_models", [])
        ),
        "datapipe_candidate_count": len(
            contract.get("live_discovery", {}).get("candidate_datapipes", [])
        ),
        "dataset_ready": False,
        "training_authorized": False,
        "engine_simulation_proven": False,
        "reported_1600_hp_proven": False,
        "fabrication_authorized": False,
        "claim_scope": (
            "Un rapport passed valide le contrat et, le cas echeant, la structure "
            "des echantillons. Il ne prouve ni dataset publie, entrainement, calcul "
            "moteur, 1600 hp, fabrication ou demarrage."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[3]
    parser.add_argument("--project-root", type=Path, default=default_root)
    parser.add_argument(
        "--contract",
        type=Path,
        default=default_root / "twins/reference-917-engine/physicsnemo-dataset-f14.json",
    )
    parser.add_argument("--samples-root", type=Path)
    parser.add_argument(
        "--report",
        type=Path,
        default=default_root / "work/917-physicsnemo-f14/validation.json",
    )
    args = parser.parse_args()
    report = evaluate(args.project_root, args.contract, args.samples_root)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["report_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
