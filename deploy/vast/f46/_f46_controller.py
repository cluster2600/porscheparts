#!/usr/bin/env python3
"""Contrôleur hors secret du cycle Vast F46.

Ce module valide uniquement des instantanés JSON produits par les wrappers
OpenBao approuvés. Il ne contacte ni Vast, ni GHCR et ne crée aucune instance.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any


IMAGE_RE = re.compile(
    r"(?P<repository>[a-z0-9][a-z0-9._/-]*)@(?P<digest>sha256:[0-9a-f]{64})"
)
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")
HEX_RE = re.compile(r"[0-9a-f]{64}")
MAX_JSON_BYTES = 4 * 1024 * 1024
REQUIRED_FAMILIES = {"OpenFOAM", "AATE_ICengines", "Cantera", "CHT", "FEA"}
REQUIRED_TOOL_KEYS = {
    "openfoam", "aate_icengines", "cantera_3_2", "cht", "fea", "cuda", "job_runner"
}
OPTIONAL_TOOL_KEYS = {"historical_enginefoam"}
SOLVER_AUTHORITY_PATH = Path(
    "twins/reference-917-engine/engine-solver-authority-f46.json"
)
SOLVER_AUTHORITY_SHA256 = (
    "f32953481ae75414425c8bd31f196708b502a3619cb96fdffd505628bde90482"
)
AATE_REVISION = "c0f75f953d67cd325d28d1300672d14288f22934"
HISTORICAL_ENGINEFOAM_REVISION = "221b8ab77307b0ea3831a055bedc2cd77c1417f9"
FORBIDDEN_SHAPE_NAME_RE = re.compile(r"(?:ellipse|elliptic|oval|ovale)", re.IGNORECASE)
FORBIDDEN_GEOMETRY_ALIAS_RE = re.compile(
    r"(?:^|[^a-z0-9])f(?:39|42)(?:[^a-z0-9]|$)", re.IGNORECASE
)
F46_LABEL = "3dprinting993-f46-cfd-cae"
F46_GPU_NAMES = (
    "RTX PRO 6000 WS",
    "RTX PRO 6000 Blackwell Max-Q",
    "RTX A6000",
)
F46_ATTEMPT_LABEL_RE = re.compile(
    rf"{re.escape(F46_LABEL)}-[0-9a-f]{{20}}"
)


class ContractError(RuntimeError):
    """Erreur fail-closed dont le texte ne contient aucune donnée secrète."""


def reject_constant(value: str) -> None:
    raise ValueError(f"constante JSON non finie interdite: {value}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise ContractError(f"JSON absent: {path}") from exc
    if not stat.S_ISREG(info.st_mode) or path.is_symlink() or not 0 < info.st_size <= MAX_JSON_BYTES:
        raise ContractError(f"JSON non régulier, vide ou trop volumineux: {path}")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"clé JSON dupliquée: {key}")
            result[key] = value
        return result

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ContractError(f"JSON strict invalide: {path}") from exc
    if not isinstance(payload, dict):
        raise ContractError(f"racine JSON invalide: {path}")
    return payload


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".partial"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def number(value: object, label: str, *, allow_zero: bool = False) -> Decimal:
    if isinstance(value, bool):
        raise ContractError(f"{label} invalide")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ContractError(f"{label} invalide") from exc
    if not result.is_finite() or result < 0 or (not allow_zero and result == 0):
        raise ContractError(f"{label} invalide")
    return result


def positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ContractError(f"{label} doit être un entier positif")
    return value


def is_f46_family_label(value: object) -> bool:
    return value == F46_LABEL or (
        isinstance(value, str) and F46_ATTEMPT_LABEL_RE.fullmatch(value) is not None
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_solver_authority(root: Path) -> dict[str, Any]:
    path = root / SOLVER_AUTHORITY_PATH
    if not path.is_file() or path.is_symlink() or sha256(path) != SOLVER_AUTHORITY_SHA256:
        raise ContractError("autorité des solveurs F46 absente ou différente")
    authority = load_json(path)
    names = authority.get("name_resolution")
    locks = authority.get("source_locks")
    if not isinstance(names, dict) or not isinstance(locks, dict):
        raise ContractError("autorité des solveurs F46 mal formée")
    if (
        names.get("exact_ICEEngineFoam_executable_found_in_official_sources") is not False
        or names.get("fabricated_alias_allowed") is not False
        or names.get("accepted_current_engine_framework") != "AATE_OpenFOAM_ICengines"
        or names.get("accepted_historical_counter_solver") != "OpenFOAM_3.0.x_engineFoam"
    ):
        raise ContractError("résolution des noms de solveurs F46 non autorisée")
    current = locks.get("current_engine_framework", {})
    historical = locks.get("historical_counter_solver", {})
    thermochemistry = locks.get("thermochemistry", {})
    if (
        current.get("repository") != "https://github.com/OpenFOAM/ICengines"
        or current.get("revision") != AATE_REVISION
        or historical.get("repository") != "https://github.com/OpenFOAM/OpenFOAM-3.0.x"
        or historical.get("revision") != HISTORICAL_ENGINEFOAM_REVISION
        or historical.get("executable") != "engineFoam"
        or thermochemistry.get("version") != "3.2.0"
    ):
        raise ContractError("verrous sources des solveurs F46 différents")
    return authority


def iter_strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)


def reject_forbidden_geometry_names(value: object, label: str) -> None:
    for item in iter_strings(value):
        if FORBIDDEN_SHAPE_NAME_RE.search(item):
            raise ContractError(f"forme ovale ou elliptique interdite dans {label}")
        if FORBIDDEN_GEOMETRY_ALIAS_RE.search(item):
            raise ContractError(f"alias géométrique F39/F42 interdit dans {label}")


def validate_functional_sections(payload: dict[str, Any], label: str) -> None:
    sections = payload.get("functional_sections")
    if not isinstance(sections, list) or not sections:
        raise ContractError(f"sections fonctionnelles absentes dans {label}")
    for section in sections:
        if (
            not isinstance(section, dict)
            or section.get("shape") != "circular"
            or not isinstance(section.get("justification"), str)
            or not section["justification"].strip()
        ):
            raise ContractError(
                f"section fonctionnelle non circulaire ou non justifiée dans {label}"
            )


def validate_contract(contract: dict[str, Any], manifest: dict[str, Any], root: Path) -> None:
    validate_solver_authority(root)
    if contract.get("id") != "917-f46-vast-cfd-cae-controller":
        raise ContractError("identité du contrat F46 invalide")
    if contract.get("classification") != "execution_controller_contract_not_execution_evidence":
        raise ContractError("classification du contrat F46 invalide")
    authority = contract.get("authority_boundary")
    if not isinstance(authority, dict) or authority.get("contract_prepared") is not True:
        raise ContractError("frontière d'autorité F46 invalide")
    for key in (
        "offer_selected_live",
        "image_verified_live",
        "instance_created",
        "simulation_executed",
        "physical_validation",
        "manufacturing_release",
    ):
        if authority.get(key) is not False:
            raise ContractError(f"autorité prématurée: {key}")
    if number(authority.get("spend_incurred_usd"), "spend_incurred_usd", allow_zero=True) != 0:
        raise ContractError("le contrat préparatoire ne peut déclarer une dépense")

    budget = contract.get("budget")
    if not isinstance(budget, dict):
        raise ContractError("budget F46 absent")
    hard = number(budget.get("hard_total_usd"), "hard_total_usd")
    planned = number(budget.get("planned_compute_ceiling_usd"), "planned_compute_ceiling_usd")
    network = number(budget.get("planned_network_ceiling_usd"), "planned_network_ceiling_usd")
    workload = number(budget.get("planned_workload_ceiling_usd"), "planned_workload_ceiling_usd")
    reserve = number(budget.get("cleanup_and_billing_reserve_usd"), "cleanup reserve")
    if (
        hard != Decimal("23")
        or planned + network != workload
        or workload + reserve != hard
        or planned >= workload
    ):
        raise ContractError("décomposition du plafond F46 incohérente")
    if number(budget.get("maximum_selected_dph_usd"), "maximum_selected_dph_usd") > Decimal("2.5"):
        raise ContractError("débit horaire supérieur au contrat")
    maximum_runtime = positive_integer(budget.get("maximum_runtime_seconds"), "maximum_runtime_seconds")
    cleanup_seconds = positive_integer(budget.get("cleanup_reserve_seconds"), "cleanup_reserve_seconds")
    if maximum_runtime > 28800 or cleanup_seconds < 900:
        raise ContractError("TTL ou réserve cleanup hors limites")

    offer_policy = contract.get("offer_policy")
    if not isinstance(offer_policy, dict):
        raise ContractError("politique d'offre F46 absente")
    if offer_policy.get("allowed_gpu_models") != list(F46_GPU_NAMES):
        raise ContractError("liste de GPU F46 différente du contrat")
    maximum_up = number(
        offer_policy.get("maximum_inet_up_cost_usd_per_gb"),
        "maximum_inet_up_cost_usd_per_gb",
        allow_zero=True,
    )
    maximum_down = number(
        offer_policy.get("maximum_inet_down_cost_usd_per_gb"),
        "maximum_inet_down_cost_usd_per_gb",
        allow_zero=True,
    )
    if maximum_up > Decimal("0.01") or maximum_down > Decimal("0.01"):
        raise ContractError("tarif réseau F46 supérieur à la borne")
    image_gb = number(budget.get("maximum_image_pull_gb"), "maximum_image_pull_gb")
    input_gb = number(budget.get("maximum_input_bundle_gb"), "maximum_input_bundle_gb")
    output_gb = number(budget.get("maximum_output_bundle_gb"), "maximum_output_bundle_gb")
    maximum_network = (image_gb + input_gb) * maximum_down + output_gb * maximum_up
    if maximum_network != network:
        raise ContractError("réserve réseau F46 différente des volumes et tarifs bornés")

    image = contract.get("image_policy")
    if not isinstance(image, dict):
        raise ContractError("politique image F46 absente")
    expected_ref = image.get("expected_immutable_ref")
    evidence_path = image.get("committed_evidence_path")
    evidence_sha = image.get("committed_evidence_sha256")
    if expected_ref is None:
        if evidence_path is not None or evidence_sha is not None:
            raise ContractError("preuve image présente sans digest verrouillé")
    else:
        match = IMAGE_RE.fullmatch(str(expected_ref))
        if match is None or match.group("repository") != image.get("expected_repository"):
            raise ContractError("référence image F46 verrouillée invalide")
        if not isinstance(evidence_path, str) or not HEX_RE.fullmatch(str(evidence_sha or "")):
            raise ContractError("preuve image verrouillée absente")
        candidate = root / evidence_path
        if not candidate.is_file() or candidate.is_symlink() or sha256(candidate) != evidence_sha:
            raise ContractError("preuve image verrouillée absente ou différente")
    if image.get("required_os") != "linux" or image.get("required_architecture") != "amd64":
        raise ContractError("plateforme image F46 invalide")
    if set(image.get("required_tools", {})) != REQUIRED_TOOL_KEYS:
        raise ContractError("outillage image F46 incomplet")
    if set(image.get("optional_tools", {})) != OPTIONAL_TOOL_KEYS:
        raise ContractError("outillage conditionnel image F46 incohérent")
    solver_policy = image.get("solver_authority")
    if not isinstance(solver_policy, dict) or solver_policy != {
        "path": str(SOLVER_AUTHORITY_PATH),
        "sha256": SOLVER_AUTHORITY_SHA256,
        "exact_ICEEngineFoam_executable_found": False,
        "fabricated_alias_allowed": False,
        "current_engine_framework": "AATE_OpenFOAM_ICengines",
        "historical_counter_solver_if_built": "OpenFOAM_3.0.x_engineFoam",
        "cantera_version": "3.2.0",
    }:
        raise ContractError("liaison à l'autorité des solveurs F46 invalide")

    lifecycle = contract.get("lifecycle")
    required_cleanup_flags = (
        "destroy_on_normal_exit",
        "destroy_on_error",
        "destroy_on_signal",
        "destroy_on_deadline",
        "destroy_on_budget_gate",
        "destroy_on_image_or_instance_drift",
        "inventory_after_must_be_empty_for_label",
        "complete_paginated_inventory_required",
    )
    if not isinstance(lifecycle, dict) or any(lifecycle.get(key) is not True for key in required_cleanup_flags):
        raise ContractError("chemins de cleanup F46 incomplets")
    if lifecycle.get("label") != F46_LABEL:
        raise ContractError("famille de label F46 invalide")
    if lifecycle.get("attempt_label_token_hex_chars") != 20:
        raise ContractError("entropie de label de tentative F46 invalide")
    if lifecycle.get("local_and_remote_deadline_must_match") is not True:
        raise ContractError("les deadlines locale et distante doivent être identiques")

    release = contract.get("current_release_gates")
    if not isinstance(release, dict) or not release or any(value is not False for value in release.values()):
        raise ContractError("toutes les portes F46 courantes doivent rester fermées")

    if manifest.get("id") != "917-f46-vast-cfd-cae-job-manifest":
        raise ContractError("identité du manifeste de jobs invalide")
    if manifest.get("classification") != "planned_jobs_not_execution_evidence":
        raise ContractError("classification du manifeste de jobs invalide")
    manifest_solver_authority = manifest.get("solver_authority")
    if not isinstance(manifest_solver_authority, dict) or manifest_solver_authority != {
        "exact_ICEEngineFoam_executable_found": False,
        "fabricated_alias_allowed": False,
        "current_engine_framework": "AATE_OpenFOAM_ICengines",
        "current_engine_framework_revision": AATE_REVISION,
        "historical_counter_solver": "OpenFOAM_3.0.x_engineFoam",
        "historical_counter_solver_revision": HISTORICAL_ENGINEFOAM_REVISION,
        "historical_counter_solver_included_only_if_built": True,
        "historical_counter_solver_image_built_and_digest_locked": False,
        "cantera_version": "3.2.0",
    }:
        raise ContractError("autorité solveur du manifeste F46 invalide")
    global_policy = manifest.get("global_policy")
    if not isinstance(global_policy, dict) or global_policy.get("geometry_domains_complete") not in (True, False):
        raise ContractError("état des domaines géométriques invalide")
    geometry_binding = manifest.get("geometry_binding")
    if not isinstance(geometry_binding, dict):
        raise ContractError("liaison géométrique F46 absente")
    if (
        geometry_binding.get("functional_sections_must_be_circular_and_justified") is not True
        or geometry_binding.get("forbidden_shape_name_tokens")
        != ["ellipse", "elliptic", "oval", "ovale"]
        or geometry_binding.get("forbidden_geometry_revision_aliases") != ["F39", "F42"]
    ):
        raise ContractError("politique de sections géométriques F46 non conforme")
    external_revision = geometry_binding.get("external_geometry_revision")
    if external_revision is not None and (
        not isinstance(external_revision, str) or not external_revision.strip()
    ):
        raise ContractError("révision géométrique F46 invalide")
    if external_revision is not None:
        reject_forbidden_geometry_names(external_revision, "révision géométrique")
    geometry_artifacts = geometry_binding.get("geometry_input_artifacts")
    if not isinstance(geometry_artifacts, list):
        raise ContractError("liste d'artefacts géométriques F46 invalide")
    for artifact in geometry_artifacts:
        if not isinstance(artifact, dict):
            raise ContractError("artefact géométrique F46 invalide")
        relative = artifact.get("path")
        digest = artifact.get("sha256")
        if (
            not isinstance(relative, str)
            or relative.startswith("/")
            or ".." in Path(relative).parts
            or not HEX_RE.fullmatch(str(digest or ""))
        ):
            raise ContractError("liaison d'artefact géométrique F46 invalide")
        reject_forbidden_geometry_names(relative, "artefact géométrique")
        artifact_path = root / relative
        if (
            not artifact_path.is_file()
            or artifact_path.is_symlink()
            or sha256(artifact_path) != digest
        ):
            raise ContractError("artefact géométrique F46 absent ou différent")
    if global_policy.get("geometry_domains_complete") is True and (
        external_revision is None or not geometry_artifacts
    ):
        raise ContractError("domaines déclarés complets sans géométrie liée")
    contract_families = contract.get("job_manifest", {}).get("required_families")
    if not isinstance(contract_families, list) or set(contract_families) != REQUIRED_FAMILIES:
        raise ContractError("familles de jobs du contrat F46 incohérentes")
    jobs = manifest.get("jobs")
    if not isinstance(jobs, list) or len(jobs) != 5:
        raise ContractError("le manifeste doit contenir cinq familles de jobs")
    if {job.get("family") for job in jobs if isinstance(job, dict)} != REQUIRED_FAMILIES:
        raise ContractError("familles de jobs F46 incomplètes")
    identifiers: set[str] = set()
    total_timeout = 0
    total_cases = 0
    for job in jobs:
        if not isinstance(job, dict):
            raise ContractError("job F46 invalide")
        identifier = job.get("id")
        if not isinstance(identifier, str) or identifier in identifiers:
            raise ContractError("identifiant de job absent ou dupliqué")
        identifiers.add(identifier)
        ready = job.get("execution_ready")
        if ready not in (True, False):
            raise ContractError(f"état d'exécution invalide: {identifier}")
        blocked = job.get("blocked_by")
        if ready:
            command = job.get("command")
            input_manifest_path = job.get("input_manifest_path")
            if (
                not isinstance(command, list)
                or not command
                or any(not isinstance(item, str) or not item or "\0" in item for item in command)
                or not isinstance(input_manifest_path, str)
                or input_manifest_path.startswith("/")
                or ".." in Path(input_manifest_path).parts
                or not HEX_RE.fullmatch(str(job.get("input_manifest_sha256", "")))
                or blocked not in ([], None)
            ):
                raise ContractError(f"job exécutable non complètement lié: {identifier}")
            input_manifest_file = root / input_manifest_path
            if (
                not input_manifest_file.is_file()
                or input_manifest_file.is_symlink()
                or sha256(input_manifest_file) != job["input_manifest_sha256"]
            ):
                raise ContractError(f"manifeste d'entrée absent ou différent: {identifier}")
            input_manifest = load_json(input_manifest_file)
            reject_forbidden_geometry_names(input_manifest, f"entrées {identifier}")
            if job.get("family") in {"OpenFOAM", "AATE_ICengines", "CHT"}:
                validate_functional_sections(input_manifest, f"entrées {identifier}")
        elif (
            job.get("command") is not None
            or job.get("input_manifest_path") is not None
            or job.get("input_manifest_sha256") is not None
        ):
            raise ContractError(f"job bloqué contenant une commande ou un digest: {identifier}")
        elif not isinstance(blocked, list) or not blocked:
            raise ContractError(f"blocages absents: {identifier}")
        required_executable = job.get("required_executable")
        if (
            isinstance(required_executable, str)
            and required_executable.casefold() == "iceenginefoam"
        ):
            raise ContractError("alias d'exécutable moteur non prouvé interdit")
        reject_forbidden_geometry_names(job, f"job {identifier}")
        total_timeout += positive_integer(job.get("timeout_seconds"), f"timeout {identifier}")
        total_cases += positive_integer(job.get("case_count"), f"case_count {identifier}")
    jobs_by_family = {job["family"]: job for job in jobs}
    aate_job = jobs_by_family["AATE_ICengines"]
    if (
        aate_job.get("solver_authority") != "AATE_OpenFOAM_ICengines"
        or aate_job.get("source_revision") != AATE_REVISION
    ):
        raise ContractError("job AATE/ICengines non lié à sa source")
    cantera_job = jobs_by_family["Cantera"]
    if (
        cantera_job.get("required_executable") != "python3"
        or cantera_job.get("required_python_distribution") != "Cantera==3.2.0"
    ):
        raise ContractError("job Cantera différent de la version 3.2.0")
    if total_timeout != positive_integer(global_policy.get("total_phase_timeout_seconds"), "total phase timeout"):
        raise ContractError("somme des timeouts de jobs incohérente")
    if total_timeout + positive_integer(global_policy.get("cleanup_reserve_seconds"), "manifest cleanup reserve") > maximum_runtime:
        raise ContractError("jobs et cleanup dépassent le TTL global")
    executable_cases = sum(job["case_count"] for job in jobs if job["execution_ready"])
    all_ready = all(job["execution_ready"] for job in jobs)
    if (
        total_cases != manifest.get("planned_case_count")
        or executable_cases != manifest.get("executable_case_count")
        or manifest.get("execution_authorized") is not all_ready
    ):
        raise ContractError("comptage des cas F46 incohérent")
    if global_policy.get("geometry_domains_complete") is not all_ready:
        raise ContractError("autorité géométrique incohérente avec la readiness globale")
    for key in ("simulation_validated", "manufacturing_release"):
        if manifest.get(key) is not False:
            raise ContractError(f"porte de manifeste prématurée: {key}")
    sources = manifest.get("source_contracts", [])
    source_bindings = [
        (source.get("path"), source.get("sha256"))
        for source in sources
        if isinstance(source, dict)
    ] if isinstance(sources, list) else []
    if source_bindings.count((str(SOLVER_AUTHORITY_PATH), SOLVER_AUTHORITY_SHA256)) != 1:
        raise ContractError("contrat d'autorité solveur F46 absent des sources")
    for source in sources:
        if not isinstance(source, dict) or not HEX_RE.fullmatch(str(source.get("sha256", ""))):
            raise ContractError("source amont mal formée")
        relative = source.get("path")
        if not isinstance(relative, str) or relative.startswith("/") or ".." in Path(relative).parts:
            raise ContractError("chemin source amont interdit")
        path = root / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != source["sha256"]:
            raise ContractError(f"source amont absente ou différente: {relative}")


def validate_evidence_classification(payload: dict[str, Any], allow_synthetic: bool) -> bool:
    classification = payload.get("classification")
    synthetic = classification == "synthetic_test_fixture"
    if synthetic and not allow_synthetic:
        raise ContractError("fixture synthétique interdite hors test explicite")
    if classification not in {"production_wrapper_evidence", "synthetic_test_fixture"}:
        raise ContractError("classification de preuve inconnue")
    return synthetic


def validate_image_proof(
    proof: dict[str, Any], contract: dict[str, Any], *, allow_synthetic: bool
) -> tuple[str, bool]:
    synthetic = validate_evidence_classification(proof, allow_synthetic)
    immutable = proof.get("immutable_ref")
    match = IMAGE_RE.fullmatch(str(immutable))
    if match is None:
        raise ContractError("référence image non immuable")
    policy = contract["image_policy"]
    if match.group("repository") != policy["expected_repository"]:
        raise ContractError("dépôt image différent du dépôt F46 autorisé")
    if proof.get("index_digest") != match.group("digest"):
        raise ContractError("digest index différent de la référence image")
    if not DIGEST_RE.fullmatch(str(proof.get("platform_manifest_digest", ""))):
        raise ContractError("digest du manifeste plateforme absent")
    if proof.get("os") != "linux" or proof.get("architecture") != "amd64":
        raise ContractError("image différente de linux/amd64")
    for gate in ("registry_digest_verified", "platform_manifest_verified", "runtime_smoke_verified"):
        if proof.get(gate) is not True:
            raise ContractError(f"preuve image manquante: {gate}")
    tools = proof.get("tools")
    if (
        proof.get("solver_authority_sha256") != SOLVER_AUTHORITY_SHA256
        or proof.get("exact_ICEEngineFoam_executable_found") is not False
    ):
        raise ContractError("preuve image non liée à l'autorité des solveurs")
    if not isinstance(tools, dict) or set(tools) != REQUIRED_TOOL_KEYS | OPTIONAL_TOOL_KEYS:
        raise ContractError("inventaire des outils image incomplet")
    for name in REQUIRED_TOOL_KEYS:
        result = tools[name]
        if not isinstance(result, dict) or result.get("passed") is not True:
            raise ContractError(f"smoke outil échoué: {name}")
        if not isinstance(result.get("version"), str) or not result["version"].strip():
            raise ContractError(f"version outil absente: {name}")
    if tools["aate_icengines"].get("version") != AATE_REVISION:
        raise ContractError("smoke AATE/ICengines différent de la révision verrouillée")
    if tools["cantera_3_2"].get("version") != "3.2.0":
        raise ContractError("smoke Cantera différent de 3.2.0")
    historical = tools["historical_enginefoam"]
    if not isinstance(historical, dict) or historical.get("available") not in (True, False):
        raise ContractError("état du solveur historique engineFoam absent")
    if historical["available"]:
        if (
            historical.get("passed") is not True
            or historical.get("version") != HISTORICAL_ENGINEFOAM_REVISION
        ):
            raise ContractError("engineFoam construit sans smoke ou mauvaise révision")
    elif historical.get("passed") is not False or historical.get("version") != "not_built":
        raise ContractError("engineFoam absent doit rester explicitement non construit")
    return str(immutable), synthetic


def validate_inventory(
    snapshot: dict[str, Any], label: str, *, allow_synthetic: bool, must_be_empty: bool
) -> bool:
    synthetic = validate_evidence_classification(snapshot, allow_synthetic)
    if snapshot.get("pagination_complete") is not True or snapshot.get("label_filter") != label:
        raise ContractError("inventaire incomplet ou filtre différent")
    instances = snapshot.get("instances")
    if not isinstance(instances, list):
        raise ContractError("liste d'instances invalide")
    for instance in instances:
        if (
            not isinstance(instance, dict)
            or label != F46_LABEL
            or not is_f46_family_label(instance.get("label"))
        ):
            raise ContractError("inventaire contient une entrée hors filtre")
    if must_be_empty and instances:
        raise ContractError("inventaire F46 non vide")
    return synthetic


def ledger_total(ledger: dict[str, Any], *, allow_synthetic: bool) -> tuple[Decimal, bool]:
    synthetic = validate_evidence_classification(ledger, allow_synthetic)
    entries = ledger.get("entries")
    if not isinstance(entries, list):
        raise ContractError("ledger de coûts invalide")
    seen: set[str] = set()
    total = Decimal("0")
    for entry in entries:
        if not isinstance(entry, dict):
            raise ContractError("entrée de ledger invalide")
        key = str(entry.get("charge_id", ""))
        if not key or key in seen:
            raise ContractError("charge_id absent ou dupliqué")
        seen.add(key)
        if entry.get("finalized") is not True:
            raise ContractError("charge antérieure non finalisée")
        total += number(entry.get("provider_charge_usd"), "provider_charge_usd", allow_zero=True)
    declared = number(ledger.get("cumulative_spend_usd"), "cumulative_spend_usd", allow_zero=True)
    if declared != total:
        raise ContractError("total du ledger différent de la somme des charges")
    return total, synthetic


def eligible_offer(offer: dict[str, Any], contract: dict[str, Any]) -> bool:
    policy = contract["offer_policy"]
    try:
        return (
            isinstance(offer.get("id"), int)
            and offer["id"] > 0
            and offer.get("gpu") in policy["allowed_gpu_models"]
            and number(offer.get("num_gpus"), "num_gpus") == policy["required_gpu_count"]
            and number(offer.get("gpu_fraction"), "gpu_fraction") == Decimal("1")
            and number(offer.get("gpu_ram_mb"), "gpu_ram_mb") >= number(policy["minimum_gpu_ram_mb"], "minimum_gpu_ram_mb")
            and number(offer.get("cpu_cores_effective"), "cpu cores") >= number(policy["minimum_cpu_cores_effective"], "minimum cpu cores")
            and number(offer.get("cpu_ram_mb"), "cpu ram") >= number(policy["minimum_cpu_ram_mb"], "minimum cpu ram")
            and number(offer.get("disk_space_gb"), "disk") >= number(policy["minimum_disk_space_gb"], "minimum disk")
            and number(offer.get("reliability"), "reliability") >= number(policy["minimum_reliability"], "minimum reliability")
            and number(offer.get("dph_total"), "dph_total", allow_zero=True) <= number(contract["budget"]["maximum_selected_dph_usd"], "maximum dph")
            and number(offer.get("inet_up_cost_usd_per_gb"), "inet_up_cost", allow_zero=True) <= number(policy["maximum_inet_up_cost_usd_per_gb"], "maximum inet up", allow_zero=True)
            and number(offer.get("inet_down_cost_usd_per_gb"), "inet_down_cost", allow_zero=True) <= number(policy["maximum_inet_down_cost_usd_per_gb"], "maximum inet down", allow_zero=True)
            and offer.get("verified") is True
            and offer.get("rentable") is True
            and offer.get("rented") is False
            and offer.get("rental_type") == "on-demand"
        )
    except ContractError:
        return False


def select_offer(
    snapshot: dict[str, Any], contract: dict[str, Any], now_epoch: int, *, allow_synthetic: bool
) -> tuple[dict[str, Any], bool]:
    synthetic = validate_evidence_classification(snapshot, allow_synthetic)
    if snapshot.get("pagination_complete") is not True:
        raise ContractError("instantané d'offres non paginé complètement")
    captured = positive_integer(snapshot.get("captured_at_epoch"), "captured_at_epoch")
    age = now_epoch - captured
    if age < 0 or age > contract["offer_policy"]["snapshot_max_age_seconds"]:
        raise ContractError("instantané d'offres périmé ou futur")
    offers = snapshot.get("offers")
    if not isinstance(offers, list):
        raise ContractError("liste d'offres invalide")
    candidates = [offer for offer in offers if isinstance(offer, dict) and eligible_offer(offer, contract)]
    if not candidates:
        raise ContractError("aucune offre F46 éligible")
    preference = {name: rank for rank, name in enumerate(contract["offer_policy"]["allowed_gpu_models"])}
    candidates.sort(
        key=lambda offer: (
            preference[offer["gpu"]],
            -float(offer["cpu_cores_effective"]),
            -float(offer["cpu_ram_mb"]),
            float(offer["dph_total"]),
            offer["id"],
        )
    )
    return candidates[0], synthetic


def build_plan(
    contract: dict[str, Any],
    manifest: dict[str, Any],
    offers: dict[str, Any],
    image_proof: dict[str, Any],
    inventory_before: dict[str, Any],
    ledger: dict[str, Any],
    *,
    now_epoch: int,
    operator_deadline_epoch: int,
    root: Path,
    allow_synthetic: bool = False,
) -> dict[str, Any]:
    validate_contract(contract, manifest, root)
    now_epoch = positive_integer(now_epoch, "now_epoch")
    operator_deadline_epoch = positive_integer(operator_deadline_epoch, "operator_deadline_epoch")
    immutable_ref, image_synthetic = validate_image_proof(
        image_proof, contract, allow_synthetic=allow_synthetic
    )
    image_policy = contract["image_policy"]
    digest_locked = image_policy.get("expected_immutable_ref") == immutable_ref
    if digest_locked:
        committed_proof = load_json(root / image_policy["committed_evidence_path"])
        if committed_proof != image_proof:
            raise ContractError("preuve image fournie différente de la preuve verrouillée")
    inventory_synthetic = validate_inventory(
        inventory_before,
        contract["lifecycle"]["label"],
        allow_synthetic=allow_synthetic,
        must_be_empty=True,
    )
    selected, offers_synthetic = select_offer(
        offers, contract, now_epoch, allow_synthetic=allow_synthetic
    )
    prior_spend, ledger_synthetic = ledger_total(ledger, allow_synthetic=allow_synthetic)
    budget = contract["budget"]
    planned_ceiling = number(budget["planned_compute_ceiling_usd"], "planned ceiling")
    network_ceiling = number(budget["planned_network_ceiling_usd"], "network ceiling")
    workload_ceiling = number(budget["planned_workload_ceiling_usd"], "workload ceiling")
    remaining = planned_ceiling - prior_spend
    if remaining <= 0:
        raise ContractError("plafond calcul déjà consommé")
    dph = number(selected["dph_total"], "selected dph")
    budget_seconds = int(
        ((remaining / dph) * Decimal("3600")).to_integral_value(rounding=ROUND_FLOOR)
    )
    operator_seconds = operator_deadline_epoch - now_epoch
    runtime_seconds = min(budget_seconds, operator_seconds, budget["maximum_runtime_seconds"])
    cleanup_seconds = budget["cleanup_reserve_seconds"]
    if runtime_seconds < budget["minimum_useful_runtime_seconds"] + cleanup_seconds:
        raise ContractError("fenêtre restante insuffisante pour calcul utile et cleanup")
    hard_deadline = now_epoch + runtime_seconds
    compute_deadline = hard_deadline - cleanup_seconds
    projected = prior_spend + dph * Decimal(runtime_seconds) / Decimal("3600")
    if projected > planned_ceiling:
        raise ContractError("projection de coût supérieure au plafond calcul")
    selected_up = number(
        selected["inet_up_cost_usd_per_gb"], "selected inet up", allow_zero=True
    )
    selected_down = number(
        selected["inet_down_cost_usd_per_gb"], "selected inet down", allow_zero=True
    )
    reserved_network = (
        number(budget["maximum_image_pull_gb"], "maximum image pull")
        + number(budget["maximum_input_bundle_gb"], "maximum input bundle")
    ) * selected_down + number(
        budget["maximum_output_bundle_gb"], "maximum output bundle"
    ) * selected_up
    projected_workload = projected + reserved_network
    if reserved_network > network_ceiling or projected_workload > workload_ceiling:
        raise ContractError("projection calcul plus réseau supérieure au plafond workload")

    synthetic = image_synthetic or inventory_synthetic or offers_synthetic or ledger_synthetic
    jobs_ready = all(job.get("execution_ready") is True for job in manifest["jobs"])
    commands_bound = all(
        isinstance(job.get("command"), list)
        and job["command"]
        and isinstance(job.get("input_manifest_path"), str)
        and HEX_RE.fullmatch(str(job.get("input_manifest_sha256", "")))
        for job in manifest["jobs"]
    )
    launch_authorized = jobs_ready and commands_bound and digest_locked and not synthetic
    blockers: list[str] = []
    if synthetic:
        blockers.append("au moins une preuve est une fixture synthétique")
    if not jobs_ready:
        blockers.append("au moins un job F46 reste bloqué")
    if not commands_bound:
        blockers.append("commandes ou manifestes d'entrée non liés par digest")
    if not digest_locked:
        blockers.append("digest et preuve image F46 non verrouillés dans le contrat")
    return {
        "schema_version": "1.0.0",
        "classification": "synthetic_test_fixture" if synthetic else "production_controller_plan",
        "status": "launch_authorized" if launch_authorized else "blocked",
        "launch_authorized": launch_authorized,
        "selected_offer": selected,
        "expected_image": immutable_ref,
        "expected_label_family": contract["lifecycle"]["label"],
        "expected_label": None,
        "prior_cumulative_spend_usd": str(prior_spend),
        "selected_dph_total_usd": str(dph),
        "projected_compute_spend_usd": str(projected.quantize(Decimal("0.000001"))),
        "reserved_network_transfer_usd": str(reserved_network.quantize(Decimal("0.000001"))),
        "projected_cumulative_spend_usd": str(projected_workload.quantize(Decimal("0.000001"))),
        "hard_total_budget_usd": str(number(budget["hard_total_usd"], "hard total")),
        "planned_compute_ceiling_usd": str(planned_ceiling),
        "planned_network_ceiling_usd": str(network_ceiling),
        "planned_workload_ceiling_usd": str(workload_ceiling),
        "local_deadline_epoch": hard_deadline,
        "remote_deadline_epoch": hard_deadline,
        "compute_stop_epoch": compute_deadline,
        "cleanup_reserve_seconds": cleanup_seconds,
        "job_manifest_id": manifest["id"],
        "job_ids": [job["id"] for job in manifest["jobs"]],
        "planned_case_count": manifest["planned_case_count"],
        "blockers": blockers,
        "created_at": datetime.fromtimestamp(now_epoch, timezone.utc).isoformat(),
        "release_gates": {key: False for key in contract["current_release_gates"]},
    }


def cost_check(
    contract: dict[str, Any],
    plan: dict[str, Any],
    ledger: dict[str, Any],
    instance: dict[str, Any],
    *,
    now_epoch: int,
    allow_synthetic: bool = False,
) -> dict[str, Any]:
    synthetic = validate_evidence_classification(instance, allow_synthetic)
    prior, ledger_synthetic = ledger_total(ledger, allow_synthetic=allow_synthetic)
    now_epoch = positive_integer(now_epoch, "now_epoch")
    if instance.get("id") != plan.get("selected_instance_id"):
        raise ContractError("instance courante différente du plan")
    expected_label = plan.get("expected_label")
    if not isinstance(expected_label, str) or F46_ATTEMPT_LABEL_RE.fullmatch(expected_label) is None:
        raise ContractError("label de tentative F46 absent ou invalide")
    if instance.get("label") != expected_label or instance.get("image") != plan.get("expected_image"):
        raise ContractError("label ou image de l'instance a dérivé")
    selected = plan.get("selected_offer", {})
    if instance.get("gpu") != selected.get("gpu"):
        raise ContractError("GPU de l'instance différent de l'offre")
    exact_fields = (
        ("num_gpus", "num_gpus"),
        ("gpu_fraction", "gpu_fraction"),
        ("gpu_ram_mb", "gpu_ram_mb"),
        ("cpu_cores_effective", "cpu_cores_effective"),
        ("cpu_ram_mb", "cpu_ram_mb"),
        ("disk_space_gb", "disk_space_gb"),
    )
    for instance_key, offer_key in exact_fields:
        if number(instance.get(instance_key), instance_key) != number(selected.get(offer_key), offer_key):
            raise ContractError(f"champ instance différent de l'offre: {instance_key}")
    if instance.get("machine_verification") != "verified" or instance.get("status") != "running":
        raise ContractError("instance non vérifiée ou non active")
    dph = number(instance.get("dph_total"), "instance dph")
    if dph != number(plan.get("selected_dph_total_usd"), "plan dph"):
        raise ContractError("coût horaire de l'instance a dérivé")
    start = positive_integer(instance.get("started_at_epoch"), "started_at_epoch")
    if now_epoch < start:
        raise ContractError("horodatage de coût antérieur au démarrage")
    elapsed_charge = Decimal(now_epoch - start) * dph / Decimal("3600")
    provider_charge = number(instance.get("provider_charge_usd"), "provider charge", allow_zero=True)
    current_charge = max(elapsed_charge, provider_charge)
    cumulative_compute = prior + current_charge
    reserved_network = number(
        plan.get("reserved_network_transfer_usd"),
        "reserved network transfer",
        allow_zero=True,
    )
    cumulative = cumulative_compute + reserved_network
    planned_cap = number(contract["budget"]["planned_compute_ceiling_usd"], "planned cap")
    hard_cap = number(contract["budget"]["hard_total_usd"], "hard cap")
    compute_deadline = positive_integer(plan.get("compute_stop_epoch"), "compute_stop_epoch")
    hard_deadline = positive_integer(plan.get("local_deadline_epoch"), "local_deadline_epoch")
    contract_ok = dph <= number(contract["budget"]["maximum_selected_dph_usd"], "max dph")
    continue_compute = (
        contract_ok
        and cumulative_compute < planned_cap
        and now_epoch < compute_deadline
        and plan.get("launch_authorized") is True
        and not synthetic
        and not ledger_synthetic
    )
    cleanup_required = not continue_compute
    hard_budget_exceeded = cumulative >= hard_cap
    return {
        "schema_version": "1.0.0",
        "classification": "synthetic_test_fixture" if synthetic or ledger_synthetic else "production_cost_evidence",
        "status": "continue" if continue_compute else "cleanup_required",
        "continue_compute": continue_compute,
        "cleanup_required": cleanup_required,
        "current_conservative_charge_usd": str(current_charge.quantize(Decimal("0.000001"))),
        "cumulative_compute_spend_usd": str(cumulative_compute.quantize(Decimal("0.000001"))),
        "reserved_network_transfer_usd": str(reserved_network.quantize(Decimal("0.000001"))),
        "cumulative_conservative_spend_usd": str(cumulative.quantize(Decimal("0.000001"))),
        "planned_compute_ceiling_usd": str(planned_cap),
        "planned_workload_ceiling_usd": str(
            number(contract["budget"]["planned_workload_ceiling_usd"], "planned workload")
        ),
        "hard_total_budget_usd": str(hard_cap),
        "hard_budget_exceeded": hard_budget_exceeded,
        "compute_deadline_reached": now_epoch >= compute_deadline,
        "hard_deadline_reached": now_epoch >= hard_deadline,
        "checked_at": datetime.fromtimestamp(now_epoch, timezone.utc).isoformat(),
    }


def finalize(
    contract: dict[str, Any],
    plan: dict[str, Any],
    jobs_state: dict[str, Any],
    ledger: dict[str, Any],
    destroy_report: dict[str, Any],
    inventory_after: dict[str, Any],
    *,
    allow_synthetic: bool = False,
) -> dict[str, Any]:
    synthetic_flags = [
        validate_evidence_classification(jobs_state, allow_synthetic),
        validate_evidence_classification(destroy_report, allow_synthetic),
        validate_inventory(
            inventory_after,
            contract["lifecycle"]["label"],
            allow_synthetic=allow_synthetic,
            must_be_empty=True,
        ),
    ]
    total, ledger_synthetic = ledger_total(ledger, allow_synthetic=allow_synthetic)
    synthetic = any(synthetic_flags) or ledger_synthetic
    expected_label = plan.get("expected_label")
    if not isinstance(expected_label, str) or F46_ATTEMPT_LABEL_RE.fullmatch(expected_label) is None:
        raise ContractError("label de tentative F46 absent ou invalide au cleanup")
    if destroy_report.get("destroyed") is not True or destroy_report.get("verified_absent") is not True:
        raise ContractError("destruction non vérifiée")
    if destroy_report.get("instance_id") != plan.get("selected_instance_id"):
        raise ContractError("rapport de destruction pour une autre instance")
    states = jobs_state.get("jobs")
    if not isinstance(states, list):
        raise ContractError("état des jobs invalide")
    expected_ids = set(plan.get("job_ids", []))
    actual_ids = {item.get("id") for item in states if isinstance(item, dict)}
    if not expected_ids or actual_ids != expected_ids:
        raise ContractError("état des jobs incomplet")
    terminal = {"passed", "failed", "blocked", "cancelled"}
    if any(not isinstance(item, dict) or item.get("status") not in terminal for item in states):
        raise ContractError("job non terminal au cleanup")
    hard = number(contract["budget"]["hard_total_usd"], "hard total")
    return {
        "schema_version": "1.0.0",
        "classification": "synthetic_test_fixture" if synthetic else "production_cleanup_evidence",
        "status": "cleanup_verified" if total <= hard else "cleanup_verified_budget_exceeded",
        "cleanup_verified": True,
        "empty_final_inventory_verified": True,
        "cumulative_spend_usd": str(total),
        "hard_total_budget_usd": str(hard),
        "budget_respected": total <= hard,
        "jobs_all_passed": bool(states) and all(item["status"] == "passed" for item in states),
        "simulation_validated": False,
        "metal_print_authorized": False,
        "engine_start_authorized": False,
    }


def preparation_report(contract: dict[str, Any], manifest: dict[str, Any], root: Path) -> dict[str, Any]:
    validate_contract(contract, manifest, root)
    artifact_paths = (
        "twins/reference-917-engine/engine-solver-authority-f46.json",
        "twins/reference-917-engine/f46-vast-cfd-cae-controller.json",
        "twins/reference-917-engine/f46-vast-job-manifest.json",
        "deploy/vast/f46/_f46_controller.py",
        "deploy/vast/f46/run-controller.sh",
        "deploy/vast/simready/_controller_common.sh",
        "deploy/vast/simready/check-instance.sh",
        "deploy/vast/simready/destroy-instance.sh",
        "deploy/openbao/openbao-vastai",
        "deploy/openbao/openbao-ghcr",
        "docs/917_F46_VAST_CFD_CAE_CONTROLLER.md",
    )
    artifacts = []
    for relative in artifact_paths:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ContractError(f"artefact contrôleur absent: {relative}")
        artifacts.append({"path": relative, "sha256": sha256(path), "bytes": path.stat().st_size})
    return {
        "schema_version": "1.0.0",
        "id": "917-f46-vast-cfd-cae-controller-preparation",
        "classification": "offline_preparation_evidence_not_live_vast_evidence",
        "status": "controller_prepared_launch_blocked",
        "spend_incurred_by_this_preparation_usd": 0.0,
        "vast_api_called_by_preparation": False,
        "ghcr_api_called_by_preparation": False,
        "live_offer_selected": False,
        "live_image_verified": False,
        "live_inventory_before_verified_empty": False,
        "instance_created": False,
        "solver_authority_sha256": SOLVER_AUTHORITY_SHA256,
        "exact_ICEEngineFoam_executable_found": False,
        "planned_case_count": manifest["planned_case_count"],
        "executable_case_count": manifest["executable_case_count"],
        "hard_total_budget_usd": contract["budget"]["hard_total_usd"],
        "planned_compute_ceiling_usd": contract["budget"]["planned_compute_ceiling_usd"],
        "planned_network_ceiling_usd": contract["budget"]["planned_network_ceiling_usd"],
        "planned_workload_ceiling_usd": contract["budget"]["planned_workload_ceiling_usd"],
        "cleanup_and_billing_reserve_usd": contract["budget"]["cleanup_and_billing_reserve_usd"],
        "current_blockers": [
            "F46 linux/amd64 image digest and committed smoke evidence absent",
            "live eligible offer snapshot absent",
            "live complete empty pre-launch inventory absent",
            "2V/4V solver domains, AATE application build and qualified hot material card incomplete",
            "all five job commands and input-manifest digests absent",
        ],
        "artifacts": artifacts,
        "release_gates": {key: False for key in contract["current_release_gates"]},
    }


def cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--jobs", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--allow-synthetic-fixture", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check")
    report_parser = subparsers.add_parser("preparation-report")
    report_group = report_parser.add_mutually_exclusive_group(required=True)
    report_group.add_argument("--output", type=Path)
    report_group.add_argument("--check-report", type=Path)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--offers", type=Path, required=True)
    plan_parser.add_argument("--image-proof", type=Path, required=True)
    plan_parser.add_argument("--inventory-before", type=Path, required=True)
    plan_parser.add_argument("--ledger", type=Path, required=True)
    plan_parser.add_argument("--now-epoch", type=int, required=True)
    plan_parser.add_argument("--operator-deadline-epoch", type=int, required=True)
    plan_parser.add_argument("--output", type=Path, required=True)
    cost_parser = subparsers.add_parser("cost-check")
    cost_parser.add_argument("--plan", type=Path, required=True)
    cost_parser.add_argument("--ledger", type=Path, required=True)
    cost_parser.add_argument("--instance", type=Path, required=True)
    cost_parser.add_argument("--now-epoch", type=int, required=True)
    cost_parser.add_argument("--output", type=Path, required=True)
    final_parser = subparsers.add_parser("finalize")
    final_parser.add_argument("--plan", type=Path, required=True)
    final_parser.add_argument("--jobs-state", type=Path, required=True)
    final_parser.add_argument("--ledger", type=Path, required=True)
    final_parser.add_argument("--destroy-report", type=Path, required=True)
    final_parser.add_argument("--inventory-after", type=Path, required=True)
    final_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = load_json(args.contract)
    jobs = load_json(args.jobs)
    try:
        validate_contract(contract, jobs, args.root.resolve())
        if args.command == "check":
            print("F46 Vast controller contract OK; live launch gates remain closed")
            return 0
        if args.command == "preparation-report":
            result = preparation_report(contract, jobs, args.root.resolve())
            if args.output is not None:
                atomic_json(args.output, result)
                return 0
            expected = load_json(args.check_report)
            if expected != result:
                raise ContractError("rapport de préparation F46 différent des sources")
            print(f"F46 preparation report OK: {args.check_report}")
            return 0
        if args.command == "plan":
            result = build_plan(
                contract,
                jobs,
                load_json(args.offers),
                load_json(args.image_proof),
                load_json(args.inventory_before),
                load_json(args.ledger),
                now_epoch=args.now_epoch,
                operator_deadline_epoch=args.operator_deadline_epoch,
                root=args.root.resolve(),
                allow_synthetic=args.allow_synthetic_fixture,
            )
        elif args.command == "cost-check":
            result = cost_check(
                contract,
                load_json(args.plan),
                load_json(args.ledger),
                load_json(args.instance),
                now_epoch=args.now_epoch,
                allow_synthetic=args.allow_synthetic_fixture,
            )
        else:
            result = finalize(
                contract,
                load_json(args.plan),
                load_json(args.jobs_state),
                load_json(args.ledger),
                load_json(args.destroy_report),
                load_json(args.inventory_after),
                allow_synthetic=args.allow_synthetic_fixture,
            )
        atomic_json(args.output, result)
        if args.command == "plan":
            return 0 if result["launch_authorized"] else 1
        if args.command == "cost-check":
            return 0 if result["continue_compute"] else 3
        return 0 if result["cleanup_verified"] and result["budget_respected"] else 1
    except ContractError as exc:
        if getattr(args, "output", None):
            atomic_json(
                args.output,
                {
                    "schema_version": "1.0.0",
                    "status": "blocked",
                    "launch_authorized": False,
                    "errors": [str(exc)],
                    "simulation_validated": False,
                    "metal_print_authorized": False,
                    "engine_start_authorized": False,
                },
            )
        print(f"f46-controller: {exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())
