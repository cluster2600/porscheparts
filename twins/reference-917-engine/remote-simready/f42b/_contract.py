#!/usr/bin/env python3
"""Gates F42b fail-closed pour les six USD canoniques F42a.

Le module reste importable sans USD. Seule la commande ``audit-usd`` charge pxr.
Il n'écrit jamais de valeur secrète et ne répare jamais un actif.
"""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any


SCHEMA_VERSION = "1.0.0"
WORKFLOW_PROFILE = "f42b-six-usd-v1"
IMAGE_REPOSITORY = "ghcr.io/cluster2600/3dprinting993-simready-local-ai"
IMAGE_RE = re.compile(
    re.escape(IMAGE_REPOSITORY) + r"@sha256:[0-9a-f]{64}"
)
QUALIFIED_STATUS = "qualified_public_linux_amd64_digest"
PENDING_STATUS = "pending_public_linux_amd64_digest_qualification"
QUALIFICATION_EVIDENCE_PATH = "twins/reference-917-engine/evidence/f42b-gpu-runtime-qualification.json"
QUALIFICATION_BRANCH = "codex/917-f42-simready-runtime"
QUALIFICATION_WORKFLOW_PATH = ".github/workflows/containers.yml"
RUNTIME_RECEIPT_AUTHENTICITY_SCOPE = (
    "local_live_procedural_receipt_not_cryptographic_signature"
)
LAUNCHER_PIN_PATH = "deploy/openbao/openbao-vastai"
RUNTIME_ATTESTOR_PATH = "deploy/openbao/openbao-ghcr"
RUNTIME_ATTESTOR_COMMAND = "attest-simready-runtime"
PROFILE = "Prop-Robotics-Physx"
PROFILE_VERSION = "1.0.0"
FAMILY_ORDER = (
    "connecting_rod",
    "crankshaft",
    "main_bearing_pair",
    "piston",
    "piston_pin",
    "piston_ring",
)
CANONICAL = {
    "connecting_rod": (
        "connecting_rod.usd",
        22222,
        "f995b603ec6d6b467e87b2ad26913e402b864bee10736fca16a65612260d1ec8",
        "/connecting_rod",
    ),
    "crankshaft": (
        "crankshaft.usd",
        40439,
        "20be6e2ff0afe25bde546148833d51d7546a7e50d9abe75e963808c472292cf1",
        "/crankshaft",
    ),
    "main_bearing_pair": (
        "main_bearing_pair.usd",
        15091,
        "aaa12a2eb966a506be21f9f44733dac3edb4c5d399441a2d9a8fbfd44b657a33",
        "/main_bearing_pair",
    ),
    "piston": (
        "piston.usd",
        65639,
        "95a4c5ef57c87af25e12a5784ced63c6fd88b3199f86213903ad2e03d05506df",
        "/piston",
    ),
    "piston_pin": (
        "piston_pin.usd",
        11219,
        "fefe43fdabd8b7eea63bf7b8e191f02eac2f4be28c538c644f76a63da526934d",
        "/piston_pin",
    ),
    "piston_ring": (
        "piston_ring.usd",
        12156,
        "a0f7bba825e4e3f9e3faae2d1318584d99ab836da0d224ab35039b4c0a7a1aa3",
        "/piston_ring",
    ),
}
VISUAL = {
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
VISUAL_SOURCE_ASSIGNMENTS = {
    "connecting_rod": "motion-video-f7:visual_materials.family_assignments.connecting_rod",
    "crankshaft": "motion-video-f7:visual_materials.family_assignments.crankshaft",
    "main_bearing_pair": "motion-video-f7:visual_materials.family_assignments.main_bearing",
    "piston": "motion-video-f7:visual_materials.family_assignments.piston",
    "piston_pin": "motion-video-f7:visual_materials.family_assignments.piston_pin",
    "piston_ring": "motion-video-f7:visual_materials.family_assignments.piston_ring",
}
HISTORICAL = {
    "connecting_rod": (
        "forged_titanium",
        "documentary_variant_context_not_grade_or_process_qualification",
        ["917_GERMAN_SOURCE_AND_MEASUREMENT_MATRIX_F29.md:S06"],
    ),
    "crankshaft": (
        "unknown",
        "forging_documented_but_alloy_family_not_primary_source_qualified",
        [
            "917_GERMAN_SOURCE_AND_MEASUREMENT_MATRIX_F29.md:S01",
            "917_GERMAN_SOURCE_AND_MEASUREMENT_MATRIX_F29.md:S06",
        ],
    ),
    "main_bearing_pair": ("unknown", "unknown", []),
    "piston": (
        "light_alloy",
        "documentary_variant_context_not_grade_or_process_qualification",
        ["917_GERMAN_SOURCE_AND_MEASUREMENT_MATRIX_F29.md:S01"],
    ),
    "piston_pin": ("unknown", "unknown", []),
    "piston_ring": ("unknown", "unknown", []),
}
RELEASE_GATE_KEYS = {
    "runtime_digest_qualified",
    "private_usd_transferred_and_hash_verified",
    "all_six_family_runs_complete",
    "simready_property_assignment_complete",
    "physical_simulation_validated",
    "fea_validated",
    "manufacturing_authorized",
    "engine_installation_authorized",
    "performance_claim_authorized",
}
TOP_LEVEL_PHASES = (
    "minimum-usd",
    "material",
    "physics",
    "conform",
    "validate-asset",
    "validate-geometry",
    "validate-physics",
    "render-preview",
)
PHYSICS_PROPERTY_KEYS = (
    "density",
    "dynamic_friction",
    "restitution",
    "static_friction",
)
FORBIDDEN_SCHEMA_TOKENS = (
    "articulation",
    "deformable",
    "driveapi",
    "joint",
    "massapi",
    "rigidbodyapi",
)
FORBIDDEN_PRIM_TYPE_TOKENS = (
    "articulation",
    "deformable",
    "force",
    "joint",
    "physicsmaterial",
    "physicsscene",
)
FORBIDDEN_PROPERTY_TOKENS = (
    "angularvelocity",
    "damping",
    "density",
    "dynamicfriction",
    "force",
    "inertia",
    "joint",
    "mass",
    "poisson",
    "pressure",
    "restitution",
    "staticfriction",
    "stiffness",
    "stress",
    "strain",
    "temperature",
    "torque",
    "velocity",
    "youngs",
)
ALLOWED_PHYSICS_SCHEMAS = {
    "PhysicsCollisionAPI",
    "PhysicsMeshCollisionAPI",
}
ALLOWED_AUTHORED_PHYSICS_PROPERTIES = {
    "physics:approximation",
    "physics:collisionEnabled",
}
VALIDATION_FINDING_STATUSES = {"FAIL", "FAILED", "FAILURE"}


class ContractError(RuntimeError):
    """Violation d'un gate F42b."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def physics_schema_forbidden(schema: str) -> bool:
    normalized = schema.lower()
    if "physics" in normalized or "physx" in normalized:
        return schema not in ALLOWED_PHYSICS_SCHEMAS
    return any(token in normalized for token in FORBIDDEN_SCHEMA_TOKENS)


def physics_property_forbidden(name: str) -> bool:
    normalized = name.lower().replace("_", "")
    if normalized.startswith(("physics:", "physx")):
        return name not in ALLOWED_AUTHORED_PHYSICS_PROPERTIES
    return any(token in normalized for token in FORBIDDEN_PROPERTY_TOKENS)


def collision_schema_flags(schemas: list[str]) -> tuple[bool, bool]:
    return (
        "PhysicsCollisionAPI" in schemas,
        "PhysicsMeshCollisionAPI" in schemas,
    )


def physics_schema_allowed_on_prim(schema: str, prim_type: str) -> bool:
    return schema not in ALLOWED_PHYSICS_SCHEMAS or prim_type == "Mesh"


def physics_property_context_valid(
    name: str,
    prim_type: str,
    schemas: list[str],
    stage_name: str,
    value: Any,
    has_time_samples: bool,
    has_connections: bool,
) -> bool:
    if name not in ALLOWED_AUTHORED_PHYSICS_PROPERTIES:
        return False
    if prim_type != "Mesh" or stage_name not in {"physics", "final"}:
        return False
    if has_time_samples or has_connections:
        return False
    if name == "physics:collisionEnabled":
        return "PhysicsCollisionAPI" in schemas and value is True
    return "PhysicsMeshCollisionAPI" in schemas and value == "none"


def material_binding_properties_valid(
    names: list[str], prim_type: str, stage_name: str
) -> bool:
    expected = (
        ["material:binding"]
        if prim_type == "Mesh" and stage_name in {"minimum", "material", "physics", "final"}
        else []
    )
    return sorted(names) == expected


def direct_all_purpose_material_binding_signatures(
    stage: Any, usd_shade: Any
) -> dict[str, dict[str, Any]]:
    """Signe les bindings directs F42a après une validation fermée."""

    default_prim = stage.GetDefaultPrim()
    require(default_prim and default_prim.IsValid(), "defaultPrim absent du stage matériau")
    default_prefix = str(default_prim.GetPath()) + "/"
    signatures: dict[str, dict[str, Any]] = {}
    mesh_paths: list[str] = []
    for prim in stage.TraverseAll():
        path = str(prim.GetPath())
        type_name = prim.GetTypeName()
        names = sorted(
            prop.GetName()
            for prop in prim.GetProperties()
            if prop.GetName().startswith("material:binding")
        )
        require(
            material_binding_properties_valid(names, type_name, "minimum"),
            f"binding purpose/collection ou binding sur prim interdit: {path}",
        )
        if type_name != "Mesh":
            continue
        mesh_paths.append(path)
        material, relationship = usd_shade.MaterialBindingAPI(prim).ComputeBoundMaterial()
        require(
            material
            and material.GetPrim().IsValid()
            and relationship
            and relationship.IsAuthored()
            and str(relationship.GetPrim().GetPath()) == path,
            f"binding direct F42a sans Material local valide: {path}",
        )
        targets = list(relationship.GetTargets())
        require(len(targets) == 1, f"binding F42a multi-cible ou vide: {path}")
        material_path = str(targets[0])
        target_prim = stage.GetPrimAtPath(targets[0])
        require(
            material_path.startswith(default_prefix)
            and target_prim
            and target_prim.IsValid()
            and target_prim.GetTypeName() == "Material"
            and str(material.GetPrim().GetPath()) == material_path,
            f"cible de binding F42a externe ou non-Material: {path}",
        )
        signatures[path] = {
            "target": material_path,
            "relationship_metadata": _jsonable(relationship.GetAllMetadata()),
        }
    require(mesh_paths, "aucun Mesh dans le stage matériau")
    require(
        set(signatures) == set(mesh_paths),
        "chaque Mesh doit porter un binding direct all-purpose vers un Material local",
    )
    return signatures


def material_binding_targets(
    signatures: dict[str, dict[str, Any]],
) -> dict[str, str]:
    return {path: str(value["target"]) for path, value in signatures.items()}


def root_layer_authored_meshes(stage: Any, meshes: list[Any]) -> list[Any]:
    """Évite de créer des overs redondants sur les occurrences composées."""

    root_layer = stage.GetRootLayer()
    authored = [mesh for mesh in meshes if root_layer.GetPrimAtPath(mesh.GetPath())]
    require(authored, "aucun Mesh authored dans la root layer")
    return authored


def classify_nvidia_validation(
    report_path: Path,
    asset_path: Path,
    validator_skill: str,
    exit_code: int,
) -> str:
    report = read_json(report_path, "rapport validateur NVIDIA")
    asset = regular_file(asset_path, "USD validé")
    require(report.get("validator_skill") == validator_skill, "skill validateur NVIDIA inattendu")
    reported_asset = Path(str(report.get("asset_path", "")))
    require(reported_asset.is_absolute(), "asset_path du validateur NVIDIA invalide")
    require(reported_asset.resolve(strict=True) == asset, "validateur NVIDIA appliqué à un autre USD")
    status = str(report.get("status", "")).upper()
    if exit_code == 0:
        require(report.get("passed") is True and status == "PASS", "succès NVIDIA incohérent")
        require(report.get("errors") in (None, []), "succès NVIDIA avec erreurs")
        issues = report.get("issues", [])
        require(isinstance(issues, list), "succès NVIDIA avec issues invalides")
        require(
            not any(
                isinstance(issue, dict)
                and str(issue.get("severity", "")).upper() in {"ERROR", "FAILURE"}
                for issue in issues
            ),
            "succès NVIDIA avec finding ERROR/FAILURE",
        )
        counts = report.get("issue_counts", {})
        require(isinstance(counts, dict), "succès NVIDIA avec issue_counts invalide")
        require(
            all(type(counts.get(key, 0)) is int and counts.get(key, 0) == 0 for key in ("ERROR", "FAILURE")),
            "succès NVIDIA avec compteurs d'échec non nuls",
        )
        return "passed"
    require(exit_code == 1, f"exécution NVIDIA interrompue avec code {exit_code}")
    require(report.get("passed") is False and status in VALIDATION_FINDING_STATUSES, "échec NVIDIA bloqué, timeout ou invalide")
    issues = report.get("issues")
    require(isinstance(issues, list) and issues, "échec NVIDIA sans findings structurés")
    failing = [
        issue for issue in issues
        if isinstance(issue, dict)
        and str(issue.get("severity", "")).upper() in {"ERROR", "FAILURE"}
    ]
    require(failing, "échec NVIDIA sans finding ERROR/FAILURE")
    errors = report.get("errors")
    require(isinstance(errors, list) and errors, "échec NVIDIA sans erreurs dérivées des findings")
    counts = report.get("issue_counts")
    require(
        isinstance(counts, dict)
        and all(type(counts.get(key, 0)) is int for key in ("ERROR", "FAILURE"))
        and sum(counts.get(key, 0) for key in ("ERROR", "FAILURE")) >= len(failing),
        "compteurs de findings NVIDIA incohérents",
    )
    return "needs_rerun"


def regular_file(path: Path, label: str) -> Path:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise ContractError(f"{label} absent: {path}") from exc
    require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode), f"{label} doit etre un fichier regulier non symlink")
    return path.resolve(strict=True)


def read_json(path: Path, label: str) -> dict[str, Any]:
    resolved = regular_file(path, label)
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} illisible ou invalide") from exc
    require(isinstance(value, dict), f"{label} doit etre un objet JSON")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_relative(value: Any, label: str) -> Path:
    path = Path(str(value))
    require(bool(path.parts) and not path.is_absolute() and ".." not in path.parts, f"{label} doit etre relatif et borne")
    return path


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
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


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def repository_root(contract_path: Path) -> Path:
    resolved = contract_path.resolve(strict=True)
    require(resolved.name == "component-factory-f42b-gpu.json", "nom du contrat F42b inattendu")
    root = resolved.parents[2]
    require((root / "twins/reference-917-engine").is_dir(), "racine projet F42b introuvable")
    return root


def launcher_simready_pin(path: Path) -> tuple[str, set[str]]:
    wrapper = regular_file(path, "wrapper OpenBao Vast.ai")
    try:
        tree = ast.parse(wrapper.read_text(encoding="utf-8"), filename=str(wrapper))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise ContractError("wrapper OpenBao Vast.ai illisible ou invalide") from exc
    pin: list[str] = []
    revoked: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            if target.id == "SIMREADY_IMAGE" and isinstance(value, ast.Constant) and isinstance(value.value, str):
                pin.append(value.value)
            if target.id.startswith("SIMREADY_REVOKED_IMAGE_") and isinstance(value, ast.Constant) and isinstance(value.value, str):
                revoked.add(value.value)
    require(len(pin) == 1, "SIMREADY_IMAGE doit être un digest littéral unique dans le wrapper")
    return pin[0], revoked


def canonical_entries(contract: dict[str, Any]) -> list[dict[str, Any]]:
    source = contract.get("source_usd")
    require(isinstance(source, dict), "source_usd absent")
    entries = source.get("families")
    require(isinstance(entries, list), "source_usd.families doit etre une liste")
    require(len(entries) == len(FAMILY_ORDER), "six familles F42a exactement requises")
    require([entry.get("family_id") for entry in entries if isinstance(entry, dict)] == list(FAMILY_ORDER), "ordre ou familles F42a inattendus")
    for entry in entries:
        require(isinstance(entry, dict), "entree famille invalide")
        family = str(entry.get("family_id", ""))
        filename, size, digest, default_prim = CANONICAL[family]
        require(entry.get("filename") == filename, f"filename canonique different: {family}")
        require(entry.get("size_bytes") == size, f"taille canonique differente: {family}")
        require(entry.get("sha256") == digest, f"SHA-256 canonique different: {family}")
        require(entry.get("default_prim_path") == default_prim, f"defaultPrim canonique different: {family}")
    require(source.get("exact_file_count") == 6, "exact_file_count doit valoir 6")
    require(source.get("total_size_bytes") == sum(item[1] for item in CANONICAL.values()), "taille totale F42a differente")
    require(source.get("private_artifacts_committed") is False, "les USD prives ne doivent pas etre declares versionnes")
    require(
        source.get("minimum_material_binding_policy")
        == "preserve_exact_f42a_all_purpose_mesh_bindings_then_rebind_canonical_visual_material",
        "politique des bindings materiau F42a inattendue",
    )
    return entries


def _verify_live_runtime_attestation(
    contract: dict[str, Any],
    root: Path,
    evidence: dict[str, Any],
    evidence_path: Path,
    attestation_path: Path,
    expected_runtime_job_id: str,
    expected_runtime_nonce: str,
) -> None:
    require(
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", expected_runtime_job_id)
        is not None,
        "job id attendu pour le reçu runtime invalide",
    )
    require(
        re.fullmatch(r"[0-9a-f]{32}", expected_runtime_nonce) is not None,
        "nonce attendu pour le reçu runtime invalide",
    )
    attestation_file = regular_file(attestation_path, "attestation runtime live")
    info = attestation_file.lstat()
    require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o600, "attestation runtime live doit être possédée et en mode 0600")
    payload = read_json(attestation_file, "attestation runtime live")
    verified_at_raw = payload.get("verified_at")
    require(isinstance(verified_at_raw, str), "horodatage attestation runtime absent")
    try:
        verified_at = datetime.fromisoformat(verified_at_raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("horodatage attestation runtime invalide") from exc
    now = datetime.now(timezone.utc)
    require(verified_at.tzinfo is not None, "horodatage attestation runtime sans fuseau")
    age = (now - verified_at).total_seconds()
    require(-60 <= age <= 900 and now.timestamp() - info.st_mtime <= 900, "attestation runtime live absente, future ou périmée")

    producer = contract["runtime"]["runtime_attestation"]
    wrapper = regular_file(root / RUNTIME_ATTESTOR_PATH, "wrapper OpenBao GHCR")
    wrapper_bytes = wrapper.read_bytes()
    wrapper_text = wrapper_bytes.decode("utf-8")
    require(RUNTIME_ATTESTOR_COMMAND in wrapper_text, "wrapper OpenBao GHCR sans commande d'attestation runtime")
    committed_blob = hashlib.sha1(
        f"blob {len(wrapper_bytes)}\0".encode("ascii") + wrapper_bytes,
        usedforsecurity=False,
    ).hexdigest()
    required_steps = {
        "Build large local AI image from Docker store": "success",
        "Resolve published immutable digest": "success",
        "Verify published local AI manifest limits": "success",
        "Verify anonymous digest pull": "success",
        "Promote verified image": "success",
    }
    require(
        payload.get("schema_version") == SCHEMA_VERSION
        and payload.get("status") == "verified_public_runtime"
        and payload.get("image_ref") == evidence["image_ref"]
        and payload.get("manifest_digest") == evidence["manifest_digest"]
        and payload.get("platform") == "linux/amd64"
        and payload.get("source_revision") == evidence["source_revision"]
        and payload.get("source_branch") == evidence["source_branch"]
        and payload.get("run_attempt") == evidence["run_attempt"]
        and payload.get("workflow_path") == evidence["workflow_path"]
        and payload.get("workflow_git_blob") == evidence["workflow_git_blob"]
        and payload.get("github_run_id") == evidence["github_run_id"]
        and payload.get("github_run_url") == evidence["github_run_url"]
        and payload.get("qualification_evidence_sha256") == sha256(evidence_path)
        and payload.get("verified_steps") == required_steps
        and payload.get("attestor")
        == {
            "path": producer["producer_path"],
            "command": producer["producer_command"],
            "git_blob": committed_blob,
        }
        and payload.get("invocation")
        == {
            "job_id": expected_runtime_job_id,
            "nonce": expected_runtime_nonce,
            "authenticity_scope": RUNTIME_RECEIPT_AUTHENTICITY_SCOPE,
        },
        "attestation runtime live différente de la preuve publique qualifiée",
    )
    require(type(payload.get("github_job_id")) is int and payload["github_job_id"] > 0, "GitHub job id live invalide")
    require(
        payload.get("github_job_url")
        == f"https://github.com/cluster2600/3dprinting993/actions/runs/{evidence['github_run_id']}/job/{payload['github_job_id']}",
        "URL GitHub job live invalide",
    )


def validate_contract(
    contract_path: Path,
    *,
    permit_pending: bool = True,
    runtime_attestation_path: Path | None = None,
    runtime_job_id: str | None = None,
    runtime_nonce: str | None = None,
) -> dict[str, Any]:
    contract = read_json(contract_path, "contrat F42b")
    require(contract.get("schema_version") == SCHEMA_VERSION, "schema du contrat F42b inattendu")
    require(contract.get("phase") == "F42b-gpu-simready-diagnostics", "phase F42b inattendue")
    require(contract.get("workflow_profile") == WORKFLOW_PROFILE, "workflow_profile F42b inattendu")
    entries = canonical_entries(contract)
    root = repository_root(contract_path)

    source = contract["source_usd"]
    evidence_relative = safe_relative(source.get("evidence_path"), "source_usd.evidence_path")
    evidence = regular_file(root / evidence_relative, "preuve F42a")
    require(sha256(evidence) == source.get("evidence_sha256"), "preuve F42a differente de son SHA-256")
    f42a = read_json(evidence, "preuve F42a")
    repeatability = f42a.get("repeatability", {})
    require(repeatability.get("run_count") == 2, "deux runs F42a requis")
    require(repeatability.get("canonical_namespace") is True, "namespace F42a non canonique")
    require(repeatability.get("all_six_USD_bitwise_identical") is True, "USD F42a non bitwise identiques")
    expected_evidence = [
        {
            "family_id": item["family_id"],
            "USD_size_bytes": item["size_bytes"],
            "USD_sha256": item["sha256"],
            "default_prim_path": item["default_prim_path"],
        }
        for item in entries
    ]
    require(repeatability.get("families") == expected_evidence, "familles du contrat differentes de la preuve F42a")

    runtime = contract.get("runtime")
    require(isinstance(runtime, dict), "runtime absent")
    require(runtime.get("image_repository") == IMAGE_REPOSITORY, "depot image runtime inattendu")
    require(runtime.get("platform") == "linux/amd64" and runtime.get("gpu_required") is True, "runtime GPU linux/amd64 requis")
    require(runtime.get("simready_profile") == PROFILE and runtime.get("simready_profile_version") == PROFILE_VERSION, "profil NVIDIA PhysX inattendu")
    image_ref = runtime.get("qualified_image_ref")
    status = runtime.get("qualification_status")
    launcher = runtime.get("launcher_pin")
    require(launcher == {"path": LAUNCHER_PIN_PATH, "symbol": "SIMREADY_IMAGE"}, "contrat de pin launcher inattendu")
    require(
        runtime.get("runtime_attestation")
        == {
            "required": True,
            "producer_path": RUNTIME_ATTESTOR_PATH,
            "producer_command": RUNTIME_ATTESTOR_COMMAND,
            "max_age_seconds": 900,
        },
        "contrat d'attestation runtime live inattendu",
    )
    if image_ref is None:
        require(permit_pending and status == PENDING_STATUS, "digest runtime qualifie requis")
        require(runtime.get("qualification_evidence") is None, "preuve runtime doit rester nulle avant qualification")
        runtime_is_qualified = False
    else:
        require(status == QUALIFIED_STATUS and isinstance(image_ref, str) and IMAGE_RE.fullmatch(image_ref) is not None, "image runtime non qualifiee ou non epinglee")
        evidence_metadata = runtime.get("qualification_evidence")
        require(isinstance(evidence_metadata, dict), "preuve publique de qualification runtime absente")
        require(evidence_metadata.get("path") == QUALIFICATION_EVIDENCE_PATH, "chemin preuve runtime inattendu")
        evidence_path = regular_file(root / QUALIFICATION_EVIDENCE_PATH, "preuve publique de qualification runtime")
        require(sha256(evidence_path) == evidence_metadata.get("sha256"), "SHA-256 preuve runtime différent")
        evidence = read_json(evidence_path, "preuve publique de qualification runtime")
        digest = image_ref.rsplit("@", 1)[1]
        checks = evidence.get("checks")
        require(
            evidence.get("schema_version") == SCHEMA_VERSION
            and evidence.get("status") == QUALIFIED_STATUS
            and evidence.get("image_ref") == image_ref
            and evidence.get("image_repository") == IMAGE_REPOSITORY
            and evidence.get("manifest_digest") == digest
            and evidence.get("platform") == "linux/amd64",
            "identité de la preuve runtime incohérente",
        )
        require(type(evidence.get("github_run_id")) is int and evidence["github_run_id"] > 0, "GitHub run id de qualification invalide")
        require(
            evidence.get("github_run_url")
            == f"https://github.com/cluster2600/3dprinting993/actions/runs/{evidence['github_run_id']}",
            "URL du run GitHub de qualification invalide",
        )
        require(re.fullmatch(r"[0-9a-f]{40}", str(evidence.get("source_revision", ""))) is not None, "commit du run de qualification invalide")
        require(
            evidence.get("source_branch") == QUALIFICATION_BRANCH
            and evidence.get("run_attempt") == 1
            and evidence.get("workflow_path") == QUALIFICATION_WORKFLOW_PATH
            and re.fullmatch(r"[0-9a-f]{40}", str(evidence.get("workflow_git_blob", "")))
            is not None,
            "provenance du workflow de qualification invalide",
        )
        expected_checks = {
            "workflow_conclusion_success",
            "public_package_visible",
            "linux_amd64_manifest_verified",
            "anonymous_exact_digest_pull_verified",
            "runtime_smoke_verified",
        }
        require(isinstance(checks, dict) and set(checks) == expected_checks and all(value is True for value in checks.values()), "checks publics de qualification runtime incomplets")
        launcher_pin, revoked = launcher_simready_pin(root / LAUNCHER_PIN_PATH)
        require(launcher_pin == image_ref and image_ref not in revoked, "wrapper OpenBao non épinglé au digest qualifié ou digest révoqué")
        runtime_is_qualified = True
        if not permit_pending:
            require(runtime_attestation_path is not None, "--runtime-attestation live requise")
            require(runtime_job_id is not None, "--runtime-job-id requis")
            require(runtime_nonce is not None, "--runtime-nonce requis")
            _verify_live_runtime_attestation(
                contract,
                root,
                evidence,
                evidence_path,
                runtime_attestation_path,
                runtime_job_id,
                runtime_nonce,
            )

    materials = contract.get("materials")
    require(isinstance(materials, dict), "politique materiaux absente")
    require(materials.get("visual_claim_scope") == "visual_hypotheses_only_not_historical_material_identification", "scope visuel materiau inattendu")
    palette = materials.get("visual_palette_source")
    require(isinstance(palette, dict), "source palette visuelle absente")
    palette_path = regular_file(root / safe_relative(palette.get("path"), "visual_palette_source.path"), "preuve visuelle F7")
    require(sha256(palette_path) == palette.get("sha256"), "preuve visuelle F7 differente")
    palette_evidence = read_json(palette_path, "preuve visuelle F7")
    visual_materials = palette_evidence.get("visual_materials")
    require(isinstance(visual_materials, dict), "visual_materials F7 absent")
    require(visual_materials.get("claim_status") == materials["visual_claim_scope"], "scope visuel different de F7")
    f7_assignments = visual_materials.get("family_assignments")
    require(isinstance(f7_assignments, dict), "affectations F7 absentes")
    f7_palette = visual_materials.get("palette")
    require(isinstance(f7_palette, dict), "palette F7 absente")
    for label, expected in VISUAL_PALETTE.items():
        actual = f7_palette.get(label)
        require(isinstance(actual, dict), f"entrée palette F7 absente: {label}")
        require(actual.get("color") == expected["diffuse_color"], f"couleur F7 inattendue: {label}")
        require(actual.get("metallic") == expected["metallic"], f"metallic F7 inattendu: {label}")
        require(actual.get("roughness") == expected["roughness"], f"roughness F7 inattendue: {label}")
    assignments = materials.get("assignments")
    require(isinstance(assignments, list) and len(assignments) == 6, "six affectations visuelles requises")
    require([item.get("family_id") for item in assignments if isinstance(item, dict)] == list(FAMILY_ORDER), "affectations visuelles incompletes")
    for assignment in assignments:
        family = assignment["family_id"]
        require(assignment.get("visual_material") == VISUAL[family], f"materiau visuel inattendu: {family}")
        require(f7_assignments.get("main_bearing" if family == "main_bearing_pair" else family) == VISUAL[family], f"materiau visuel different de F7: {family}")
        require(assignment.get("visual_source_assignment") == VISUAL_SOURCE_ASSIGNMENTS[family], f"source visuelle inattendue: {family}")
        properties = assignment.get("physics_properties")
        require(isinstance(properties, dict) and tuple(sorted(properties)) == tuple(sorted(PHYSICS_PROPERTY_KEYS)), f"champs physiques inattendus: {family}")
        require(all(properties[key] is None for key in PHYSICS_PROPERTY_KEYS), f"propriete physique inventee: {family}")
        historical_family, historical_status, historical_evidence = HISTORICAL[family]
        require(assignment.get("historical_material_family") == historical_family, f"famille materiau historique inattendue: {family}")
        require(assignment.get("historical_material_status") == historical_status, f"statut historique inattendu: {family}")
        require(assignment.get("historical_evidence") == historical_evidence, f"preuves historiques inattendues: {family}")

    physics = contract.get("physics")
    require(isinstance(physics, dict), "politique physique absente")
    physics_path = regular_file(root / safe_relative(physics.get("evidence_path"), "physics.evidence_path"), "preuve physique F8")
    require(sha256(physics_path) == physics.get("evidence_sha256"), "preuve physique F8 differente")
    require(physics.get("mode") == "static_collision_diagnostics_only", "seuls les colliders statiques diagnostiques sont admis")
    require(physics.get("required_mesh_api") == "UsdPhysics.CollisionAPI", "CollisionAPI requis")
    require(physics.get("optional_mesh_api") is None, "MeshCollisionAPI doit être omise du profil déterministe")
    require(
        physics.get("allowed_operations") == ["author_static_collision_api_on_existing_mesh_prims"],
        "opérations physiques autorisées inattendues",
    )
    require(physics.get("geometry_must_remain_identical") is True, "identite geometrique requise")
    for key in ("joint_count", "rigid_body_count", "mass_property_count"):
        require(physics.get(key) == 0, f"{key} doit valoir zero")
    require(physics.get("simulation_validated") is False and physics.get("fea_validated") is False, "simulation ou FEA ne peut etre validee")
    forbidden = set(physics.get("forbidden_operations", []))
    for required in (
        "author_joint_or_drive",
        "author_rigid_body_or_articulation",
        "author_mass_density_or_inertia",
        "author_force_torque_velocity_or_initial_conditions",
        "run_fea_cfd_thermal_fatigue_or_physicsnemo_simulation",
    ):
        require(required in forbidden, f"interdiction physique absente: {required}")

    validation = contract.get("validation")
    require(isinstance(validation, dict), "politique validation absente")
    require(validation.get("top_level_phase_reports_per_family") == list(TOP_LEVEL_PHASES), "phases F42b inattendues")
    require(validation.get("simready_validation_location") == "render-preview-child-validation-only", "validation SimReady doit rester validation-only")
    for key in ("simready_auto_repair", "fet004_rb_mb_001_auto_repair", "fet005_gsp_001_auto_repair"):
        require(validation.get(key) is False, f"auto-reparation interdite: {key}")

    execution = contract.get("execution")
    require(isinstance(execution, dict), "politique d'execution absente")
    require(execution.get("sequential") is True, "les familles F42b doivent etre sequentielles")
    require(execution.get("pilot_family") == FAMILY_ORDER[0], "connecting_rod doit etre la famille pilote")
    require(execution.get("remaining_family_order") == list(FAMILY_ORDER[1:]), "ordre des cinq familles restantes inattendu")
    require(execution.get("pilot_must_include_ovrtx_render") is True, "le pilote doit inclure le rendu OVRTX")
    require(execution.get("projection_formula") == "common_readiness_preflight_seconds + 6 * pilot_family_pipeline_seconds", "formule de projection runtime inattendue")
    require(execution.get("max_projected_total_seconds") == 10800, "plafond runtime F42b doit valoir 10800 secondes")
    require(execution.get("remaining_families_blocked_until_projection_passes") is True, "les cinq familles doivent dependre du gate pilote")

    render = contract.get("render")
    require(isinstance(render, dict) and render.get("backend") == "OVRTX", "rendu OVRTX requis")
    require(render.get("source_asset_mutation_allowed") is False, "le rendu ne doit pas muter l'actif")
    require(render.get("photos_from_frame_indices") == [0, 6, 12, 18], "quatre photos de controle attendues")
    require(render.get("turntable", {}).get("frames") == 24, "turntable 24 frames requis")

    gates = contract.get("release_gates")
    require(isinstance(gates, dict) and gates, "release_gates absents")
    require(set(gates) == RELEASE_GATE_KEYS, "ensemble release_gates F42b inattendu")
    require(gates.get("runtime_digest_qualified") is runtime_is_qualified, "gate runtime_digest_qualified incoherent avec l'image")
    require(
        all(value is False for key, value in gates.items() if key != "runtime_digest_qualified"),
        "aucun gate de release F42b hors digest runtime ne peut etre valide",
    )
    return contract


def family_entry(contract: dict[str, Any], family: str) -> dict[str, Any]:
    require(family in FAMILY_ORDER, f"famille hors contrat: {family}")
    entries = contract["source_usd"]["families"]
    matches = [item for item in entries if item["family_id"] == family]
    require(len(matches) == 1, f"famille absente ou dupliquee: {family}")
    return matches[0]


def verify_asset(path: Path, entry: dict[str, Any], label: str = "USD F42a") -> Path:
    resolved = regular_file(path, label)
    require(resolved.name == entry["filename"], f"nom de fichier inattendu pour {entry['family_id']}")
    require(resolved.stat().st_size == entry["size_bytes"], f"taille differente pour {entry['family_id']}")
    require(sha256(resolved) == entry["sha256"], f"SHA-256 different pour {entry['family_id']}")
    return resolved


def verify_input_root(contract: dict[str, Any], input_root: Path) -> list[dict[str, Any]]:
    try:
        info = input_root.lstat()
    except FileNotFoundError as exc:
        raise ContractError(f"repertoire USD prive absent: {input_root}") from exc
    require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode), "repertoire USD prive invalide ou symlink")
    resolved_root = input_root.resolve(strict=True)
    entries = canonical_entries(contract)
    actual_names = sorted(item.name for item in resolved_root.iterdir())
    expected_names = sorted(item["filename"] for item in entries)
    require(actual_names == expected_names, "le repertoire prive doit contenir exactement les six USD canoniques")
    result = []
    for entry in entries:
        asset = verify_asset(resolved_root / entry["filename"], entry)
        result.append({**entry, "path": str(asset)})
    return result


def verify_control(contract_path: Path, control_path: Path, family: str | None = None) -> tuple[dict[str, Any], Path]:
    contract = validate_contract(contract_path, permit_pending=True)
    control = read_json(control_path, "job-control F42b")
    require(control.get("workflow_profile") == WORKFLOW_PROFILE, "workflow_profile du job different")
    job_root = control_path.resolve(strict=True).parent.parent
    expected_contract = (job_root / "project/twins/reference-917-engine/component-factory-f42b-gpu.json").resolve(strict=True)
    require(contract_path.resolve(strict=True) == expected_contract, "contrat F42b hors du projet transfere")
    metadata = control.get("f42b_contract")
    require(isinstance(metadata, dict), "f42b_contract absent du job-control")
    require(metadata.get("path") == "project/twins/reference-917-engine/component-factory-f42b-gpu.json", "chemin f42b_contract inattendu")
    require(metadata.get("sha256") == sha256(expected_contract), "SHA-256 f42b_contract different")

    runtime_attestation_relative = safe_relative(
        control.get("runtime_attestation_report"), "runtime_attestation_report"
    )
    require(
        str(runtime_attestation_relative) == "control/runtime-attestation.json",
        "chemin attestation runtime live inattendu",
    )
    runtime_attestation_path = regular_file(
        job_root / runtime_attestation_relative, "attestation runtime live transférée"
    )
    require(
        sha256(runtime_attestation_path) == control.get("runtime_attestation_sha256"),
        "SHA-256 attestation runtime live transférée différent",
    )
    qualified_evidence_path = regular_file(
        job_root / "project" / QUALIFICATION_EVIDENCE_PATH,
        "preuve runtime qualifiée transférée",
    )
    qualified_evidence = read_json(qualified_evidence_path, "preuve runtime qualifiée transférée")
    runtime_job_id = control.get("job_id")
    runtime_nonce = control.get("runtime_attestation_nonce")
    require(isinstance(runtime_job_id, str), "job id du reçu runtime absent")
    require(isinstance(runtime_nonce, str), "nonce du reçu runtime absent")
    _verify_live_runtime_attestation(
        contract,
        repository_root(contract_path),
        qualified_evidence,
        qualified_evidence_path,
        runtime_attestation_path,
        runtime_job_id,
        runtime_nonce,
    )

    assets = control.get("input_assets")
    require(isinstance(assets, list) and len(assets) == 6, "six input_assets exactement requis")
    expected_assets = []
    for entry in canonical_entries(contract):
        expected_assets.append({
            **entry,
            "path": f"inputs/f42a-usd/{entry['filename']}",
        })
    require(assets == expected_assets, "input_assets du job-control differents du contrat")
    manifest_relative = safe_relative(control.get("input_assets_manifest"), "input_assets_manifest")
    require(str(manifest_relative) == "control/f42b-input-manifest.json", "chemin manifeste F42b inattendu")
    manifest_path = regular_file(job_root / manifest_relative, "manifeste des USD F42b")
    require(sha256(manifest_path) == control.get("input_assets_manifest_sha256"), "SHA-256 du manifeste F42b different")
    manifest = read_json(manifest_path, "manifeste des USD F42b")
    require(manifest.get("workflow_profile") == WORKFLOW_PROFILE and manifest.get("assets") == expected_assets, "manifeste des USD F42b incoherent")

    runtime = contract["runtime"]
    qualified_ref = runtime.get("qualified_image_ref")
    require(runtime.get("qualification_status") == QUALIFIED_STATUS and isinstance(qualified_ref, str), "runtime F42b pas encore qualifie")
    require(control.get("expected_image") == qualified_ref, "image du job differente du contrat F42b")
    input_root = job_root / "inputs/f42a-usd"
    verify_input_root(contract, input_root)
    if family is None:
        return control, input_root
    entry = family_entry(contract, family)
    if family != contract["execution"]["pilot_family"]:
        output_root = Path("/workspace/results") / str(control.get("job_id", ""))
        gate_path = output_root / "pilot-gate" / str(control.get("job_id", "")) / "f42b-pilot-runtime-gate.json"
        gate = read_json(gate_path, "gate runtime du pilote F42b")
        require(gate.get("schema_version") == SCHEMA_VERSION, "schema du gate pilote inattendu")
        require(gate.get("workflow_profile") == WORKFLOW_PROFILE, "profil du gate pilote inattendu")
        require(gate.get("job_id") == control.get("job_id"), "job du gate pilote different")
        require(gate.get("pilot_family") == contract["execution"]["pilot_family"], "famille pilote differente")
        require(gate.get("status") == "passed" and gate.get("passed") is True, "projection runtime pilote non validee")
        require(type(gate.get("projected_total_seconds")) is int, "projection runtime doit etre entiere")
        require(gate["projected_total_seconds"] <= contract["execution"]["max_projected_total_seconds"], "projection runtime depasse 10800 secondes")
        recomputed = project_runtime(contract_path, output_root, str(control["job_id"]))
        for key in (
            "pilot_run_id",
            "pilot_includes_ovrtx_render",
            "common_phase_durations",
            "pilot_phase_durations",
            "common_duration_seconds",
            "pilot_duration_seconds",
            "projection_formula",
            "projected_total_seconds",
            "max_projected_total_seconds",
            "remaining_families_authorized",
        ):
            require(gate.get(key) == recomputed.get(key), f"gate runtime pilote non reproductible: {key}")
        require(recomputed.get("passed") is True, "projection runtime pilote recalculee non validee")
        gate_created = _aware_datetime(gate.get("created_at"), "pilot-runtime-gate.created_at")
        pilot_finished = max(
            _aware_datetime(item.get("finished_at"), f"pilot.{item.get('phase')}.finished_at")
            for item in (
                read_json(
                    output_root / phase / f"{control['job_id']}-{contract['execution']['pilot_family']}" / f"phase-{phase}.json",
                    f"rapport pilote {phase}",
                )
                for phase in TOP_LEVEL_PHASES
            )
        )
        require(gate_created >= pilot_finished, "gate runtime cree avant la fin du rendu pilote")
    return control, verify_asset(input_root / entry["filename"], entry)


def assignment_for(contract: dict[str, Any], family: str) -> dict[str, Any]:
    matches = [item for item in contract["materials"]["assignments"] if item["family_id"] == family]
    require(len(matches) == 1, f"affectation materiau absente: {family}")
    return matches[0]


def context_payload(contract_path: Path, control_path: Path, family: str) -> dict[str, Any]:
    contract = validate_contract(contract_path, permit_pending=True)
    _, source_asset = verify_control(contract_path, control_path, family)
    entry = family_entry(contract, family)
    assignment = assignment_for(contract, family)
    historical = assignment["historical_material_family"]
    historical_status = assignment["historical_material_status"]
    visual_parameters = VISUAL_PALETTE[assignment["visual_material"]]
    evidence = assignment["historical_evidence"] or ["aucune identification historique sourcee pour cette famille"]
    prompt = (
        f"Famille F42b attestee: {family}. USD source canonique F42a: {entry['sha256']}. "
        f"Affectation visuelle sourcee F7: {assignment['visual_material']} ({assignment['visual_source_assignment']}); "
        f"UsdPreviewSurface diffuseColor={visual_parameters['diffuse_color']}, metallic={visual_parameters['metallic']}, roughness={visual_parameters['roughness']}. "
        f"Materiau historique: {historical}; statut: {historical_status}; preuves: {', '.join(evidence)}. "
        "Toutes les proprietes physiques de materiau (densite, friction, restitution) sont inconnues et doivent rester non-authorees. "
        "Physique autorisee: CollisionAPI statique diagnostique sur les seuls Mesh existants, sans geometrie proxy. "
        "Interdit: rigid body, masse, inertie, joint, articulation, drive, force, couple, vitesse, time stepping, contact predictif, FEA, CFD, thermique, fatigue et simulation PhysicsNeMo. "
        "Ne jamais inventer ni auto-reparer RB.MB.001/FET004 ou GSP.001/FET005."
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed",
        "passed": True,
        "workflow_profile": WORKFLOW_PROFILE,
        "family_id": family,
        "source_asset_path": str(source_asset),
        "source_asset_sha256": entry["sha256"],
        "default_prim_path": entry["default_prim_path"],
        "visual_material_assignment": assignment["visual_material"],
        "visual_material_parameters": visual_parameters,
        "visual_claim_scope": contract["materials"]["visual_claim_scope"],
        "historical_material_family": historical,
        "historical_material_status": historical_status,
        "historical_evidence": assignment["historical_evidence"],
        "evidence": [
            {
                "path": contract["source_usd"]["evidence_path"],
                "sha256": contract["source_usd"]["evidence_sha256"],
            },
            {
                "path": contract["materials"]["visual_palette_source"]["path"],
                "sha256": contract["materials"]["visual_palette_source"]["sha256"],
            },
        ],
        "physics_material_properties": assignment["physics_properties"],
        "physics_mode": contract["physics"]["mode"],
        "material_physics_prompt": prompt,
        "simulation_validated": False,
        "fea_validated": False,
        "manufacturing_authorized": False,
    }


def author_visual_material(
    contract_path: Path,
    family: str,
    asset_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    try:
        from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
    except ImportError as exc:
        raise ContractError("pxr USD absent pour l'affectation visuelle F42b") from exc

    contract = validate_contract(contract_path, permit_pending=True)
    asset = regular_file(asset_path, "USD Material Agent")
    stage = Usd.Stage.Open(str(asset), load=Usd.Stage.LoadAll)
    require(stage is not None, "USD Material Agent illisible")
    meshes = [prim for prim in stage.TraverseAll() if prim.GetTypeName() == "Mesh"]
    require(meshes, "aucun Mesh pour l'affectation visuelle")
    authored_meshes = root_layer_authored_meshes(stage, meshes)
    source_material_signatures = direct_all_purpose_material_binding_signatures(
        stage, UsdShade
    )
    source_material_bindings = material_binding_targets(source_material_signatures)

    label = VISUAL[family]
    parameters = VISUAL_PALETTE[label]
    default_path = Sdf.Path(family_entry(contract, family)["default_prim_path"])
    looks_path = default_path.AppendChild("F42bContractLooks")
    require(not stage.GetPrimAtPath(looks_path).IsValid(), "namespace matériau contractuel déjà présent")
    UsdGeom.Scope.Define(stage, looks_path)
    material_path = looks_path.AppendChild("CanonicalVisualMaterial")
    shader_path = material_path.AppendChild("PreviewSurface")
    material = UsdShade.Material.Define(stage, material_path)
    material_prim = material.GetPrim()
    material_prim.SetCustomDataByKey("f42b_visual_material", label)
    material_prim.SetCustomDataByKey("f42b_visual_source_sha256", contract["materials"]["visual_palette_source"]["sha256"])
    material_prim.SetCustomDataByKey("f42b_claim_scope", contract["materials"]["visual_claim_scope"])
    shader = UsdShade.Shader.Define(stage, shader_path)
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(*parameters["diffuse_color"])
    )
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(parameters["metallic"])
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(parameters["roughness"])
    shader_output = shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput().ConnectToSource(shader_output)
    for mesh in authored_meshes:
        binding_api = UsdShade.MaterialBindingAPI.Apply(mesh)
        require(binding_api, f"MaterialBindingAPI impossible sur {mesh.GetPath()}")
        require(binding_api.Bind(material), f"binding canonique impossible sur {mesh.GetPath()}")
    require(stage.GetRootLayer().Save(), "écriture du matériau visuel F42b impossible")
    rebound_signatures = direct_all_purpose_material_binding_signatures(stage, UsdShade)
    rebound_targets = material_binding_targets(rebound_signatures)
    require(
        set(rebound_targets) == {str(mesh.GetPath()) for mesh in meshes}
        and set(rebound_targets.values()) == {str(material_path)},
        "le rebind canonique ne couvre pas tous les Mesh composés",
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed",
        "passed": True,
        "workflow_profile": WORKFLOW_PROFILE,
        "family_id": family,
        "asset_path": str(asset),
        "asset_sha256": sha256(asset),
        "visual_material_assignment": label,
        "visual_material_parameters": parameters,
        "visual_source_sha256": contract["materials"]["visual_palette_source"]["sha256"],
        "replaced_source_material_bindings": source_material_bindings,
        "replaced_source_material_binding_signatures": source_material_signatures,
        "material_path": str(material_path),
        "shader_path": str(shader_path),
        "mesh_paths": [str(mesh.GetPath()) for mesh in meshes],
        "authored_mesh_paths": [str(mesh.GetPath()) for mesh in authored_meshes],
        "physics_material_properties_authored": False,
        "simulation_executed": False,
        "fea_executed": False,
    }
    atomic_json(report_path, payload)
    return payload


def clone_contract_stage(source_path: Path, destination_path: Path) -> Path:
    """Copie un stage attesté vers un nouveau fichier exclusif non symlink."""

    source = regular_file(source_path, "stage contractuel source")
    require(destination_path.is_absolute(), "destination de stage contractuel absolue requise")
    parent = destination_path.parent.resolve(strict=True)
    require(parent.is_dir() and destination_path.parent == parent, "parent de stage contractuel non canonique")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(destination_path, flags, 0o600)
        with source.open("rb") as input_handle, os.fdopen(descriptor, "wb") as output_handle:
            while chunk := input_handle.read(1024 * 1024):
                output_handle.write(chunk)
            output_handle.flush()
            os.fsync(output_handle.fileno())
    except OSError as exc:
        try:
            destination_path.unlink()
        except FileNotFoundError:
            pass
        raise ContractError(f"copie exclusive du stage contractuel impossible: {exc}") from exc
    destination = regular_file(destination_path, "stage contractuel copié")
    require(sha256(destination) == sha256(source), "copie du stage contractuel différente de la source")
    return destination


def author_static_collisions(
    contract_path: Path,
    family: str,
    asset_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    try:
        from pxr import Usd, UsdPhysics
    except ImportError as exc:
        raise ContractError("pxr USD/Physics absent pour les colliders F42b") from exc

    validate_contract(contract_path, permit_pending=True)
    asset = regular_file(asset_path, "USD physique contractuel")
    stage = Usd.Stage.Open(str(asset), load=Usd.Stage.LoadAll)
    require(stage is not None, "USD physique contractuel illisible")
    meshes = [prim for prim in stage.TraverseAll() if prim.GetTypeName() == "Mesh"]
    require(meshes, "aucun Mesh pour les colliders statiques")
    authored_meshes = root_layer_authored_meshes(stage, meshes)
    for prim in stage.TraverseAll():
        require(
            not any("physics" in str(schema).lower() or "physx" in str(schema).lower() for schema in prim.GetAppliedSchemas()),
            "le stage matériel contractuel contient déjà un schéma Physics/Physx",
        )
        require(
            not any(
                prop.IsAuthored()
                and prop.GetName().lower().replace("_", "").startswith(("physics:", "physx"))
                for prop in prim.GetProperties()
            ),
            "le stage matériel contractuel contient déjà une propriété Physics/Physx",
        )
    for mesh in authored_meshes:
        collision = UsdPhysics.CollisionAPI.Apply(mesh)
        require(collision, f"CollisionAPI impossible sur {mesh.GetPath()}")
        collision.CreateCollisionEnabledAttr(True).Set(True)
    require(stage.GetRootLayer().Save(), "écriture des colliders statiques F42b impossible")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed",
        "passed": True,
        "workflow_profile": WORKFLOW_PROFILE,
        "family_id": family,
        "asset_path": str(asset),
        "asset_sha256": sha256(asset),
        "mesh_paths": [str(mesh.GetPath()) for mesh in meshes],
        "authored_mesh_paths": [str(mesh.GetPath()) for mesh in authored_meshes],
        "authored_schemas": ["PhysicsCollisionAPI"],
        "collision_enabled": True,
        "mesh_collision_api_authored": False,
        "physics_material_properties_authored": False,
        "joint_count": 0,
        "rigid_body_count": 0,
        "mass_property_count": 0,
        "simulation_executed": False,
        "physicsnemo_simulation_executed": False,
        "fea_executed": False,
    }
    atomic_json(report_path, payload)
    return payload


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(nested) for key, nested in value.items()}
    if hasattr(value, "GetArray"):
        return [_jsonable(item) for item in value.GetArray()]
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return list(value)
    except TypeError:
        return str(value)


def _base_stage_signature(stage: Any, excluded_prefix: str | None = None) -> dict[str, Any]:
    """Capture tout le stage hors des ajouts matériels/physiques contractuels."""

    def excluded(name: str) -> bool:
        return name.startswith(("material:binding", "physics:", "physx"))

    prims: list[dict[str, Any]] = []
    for prim in stage.TraverseAll():
        path = str(prim.GetPath())
        if excluded_prefix and (path == excluded_prefix or path.startswith(excluded_prefix + "/")):
            continue
        metadata = {
            str(key): _jsonable(value)
            for key, value in prim.GetAllMetadata().items()
            if str(key) != "apiSchemas"
        }
        attributes = {}
        for attribute in prim.GetAttributes():
            name = attribute.GetName()
            if excluded(name):
                continue
            attributes[name] = {
                "type": str(attribute.GetTypeName()),
                "metadata": _jsonable(attribute.GetAllMetadata()),
                "value": _attribute_signature(attribute),
                "connections": [str(value) for value in attribute.GetConnections()],
            }
        relationships = {}
        for relationship in prim.GetRelationships():
            name = relationship.GetName()
            if excluded(name):
                continue
            relationships[name] = {
                "metadata": _jsonable(relationship.GetAllMetadata()),
                "targets": [str(value) for value in relationship.GetTargets()],
            }
        prims.append({
            "path": path,
            "type": prim.GetTypeName(),
            "metadata": metadata,
            "attributes": attributes,
            "relationships": relationships,
        })
    return {
        "pseudo_root_metadata": _jsonable(stage.GetPseudoRoot().GetAllMetadata()),
        "sub_layers": list(stage.GetRootLayer().subLayerPaths),
        "prims": prims,
    }


def _static_layer_audit(path: Path, sdf_module: Any, label: str) -> None:
    """Refuse les dépendances/compositions avant toute ouverture composée Usd."""

    layer = sdf_module.Layer.FindOrOpen(str(path))
    require(layer is not None, f"couche Sdf illisible: {label}")
    require(not list(layer.subLayerPaths), f"sublayer interdit avant chargement: {label}")
    text = layer.ExportToString()
    require(re.search(r"@[^@\r\n]*@", text) is None, f"asset path externe interdit: {label}")
    require(
        re.search(
            r"(?m)^\s*(?:references|payload|inherits|specializes|variantSets?|variantSetNames)\s*=|^\s*variantSet\s+",
            text,
        )
        is None,
        f"arc de composition ou variant interdit: {label}",
    )


def _attribute_signature(attribute: Any) -> dict[str, Any]:
    samples = list(attribute.GetTimeSamples())
    values = {"default": _jsonable(attribute.Get())}
    for sample in samples:
        values[str(sample)] = _jsonable(attribute.Get(sample))
    encoded = json.dumps(values, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return {"samples": samples, "sha256": hashlib.sha256(encoded).hexdigest()}


def _geometry_signature(stage: Any) -> dict[str, Any]:
    from pxr import Usd, UsdGeom

    geometric_types = {
        "BasisCurves", "Capsule", "Cone", "Cube", "Cylinder", "Mesh",
        "NurbsCurves", "NurbsPatch", "Plane", "PointInstancer", "Points", "Sphere",
    }
    geometry = []
    xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    for prim in stage.TraverseAll():
        if prim.GetTypeName() not in geometric_types:
            continue
        attributes = {}
        for attribute in prim.GetAttributes():
            name = attribute.GetName()
            if name.startswith("primvars:displayColor") or name.startswith("primvars:displayOpacity"):
                continue
            if name.startswith("physics:") or name.startswith("physx"):
                continue
            attributes[name] = _attribute_signature(attribute)
        world_matrix = _jsonable(xform_cache.GetLocalToWorldTransform(prim))
        ancestor_xforms = {}
        ancestor = prim
        while ancestor and ancestor.IsValid() and not ancestor.IsPseudoRoot():
            for attribute in ancestor.GetAttributes():
                if attribute.GetName().startswith("xformOp:"):
                    ancestor_xforms[f"{ancestor.GetPath()}:{attribute.GetName()}"] = _attribute_signature(attribute)
            ancestor = ancestor.GetParent()
        geometry.append({
            "path": str(prim.GetPath()),
            "type": prim.GetTypeName(),
            "attributes": attributes,
            "world_matrix": world_matrix,
            "ancestor_xforms": ancestor_xforms,
        })
    require(any(item["type"] == "Mesh" for item in geometry), "aucun Mesh dans l'USD")
    encoded = json.dumps(geometry, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return {
        "prims": geometry,
        "meters_per_unit": UsdGeom.GetStageMetersPerUnit(stage),
        "up_axis": str(UsdGeom.GetStageUpAxis(stage)),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _stage_audit(contract: dict[str, Any], family: str, source_path: Path, asset_path: Path, stage_name: str) -> dict[str, Any]:
    try:
        from pxr import Sdf, Usd, UsdGeom, UsdShade
    except ImportError as exc:
        raise ContractError("pxr USD absent pour l'audit F42b") from exc

    entry = family_entry(contract, family)
    source_path = verify_asset(source_path, entry, "USD source F42a")
    asset_path = regular_file(asset_path, "USD F42b")
    _static_layer_audit(source_path, Sdf, "USD source F42a")
    _static_layer_audit(asset_path, Sdf, "USD F42b")
    source = Usd.Stage.Open(str(source_path), load=Usd.Stage.LoadAll)
    target = Usd.Stage.Open(str(asset_path), load=Usd.Stage.LoadAll)
    require(source is not None and target is not None, "USD source ou cible illisible")
    source_default = source.GetDefaultPrim()
    target_default = target.GetDefaultPrim()
    require(source_default and target_default, "defaultPrim absent")
    require(str(source_default.GetPath()) == entry["default_prim_path"], "defaultPrim source different du contrat")
    require(str(target_default.GetPath()) == entry["default_prim_path"], "defaultPrim F42b different du source")

    source_material_signatures = direct_all_purpose_material_binding_signatures(
        source, UsdShade
    )
    target_material_signatures = direct_all_purpose_material_binding_signatures(
        target, UsdShade
    )
    source_material_bindings = material_binding_targets(source_material_signatures)
    target_material_bindings = material_binding_targets(target_material_signatures)

    source_geometry = _geometry_signature(source)
    target_geometry = _geometry_signature(target)
    require(source_geometry == target_geometry, "geometrie ou transforms F42b differents du USD F42a")

    look_prefix = f"{entry['default_prim_path']}/F42bContractLooks"
    source_prims = {str(prim.GetPath()): prim.GetTypeName() for prim in source.TraverseAll()}
    target_prims = {str(prim.GetPath()): prim.GetTypeName() for prim in target.TraverseAll()}
    expected_added_prims = (
        {
            look_prefix: "Scope",
            f"{look_prefix}/CanonicalVisualMaterial": "Material",
            f"{look_prefix}/CanonicalVisualMaterial/PreviewSurface": "Shader",
        }
        if stage_name in {"material", "physics", "final"}
        else {}
    )
    require(
        target_prims == {**source_prims, **expected_added_prims},
        "prims ajoutés, supprimés ou ret typés hors allowlist F42b",
    )
    if expected_added_prims:
        scope_prim = target.GetPrimAtPath(look_prefix)
        material_prim = target.GetPrimAtPath(f"{look_prefix}/CanonicalVisualMaterial")
        shader_prim = target.GetPrimAtPath(f"{look_prefix}/CanonicalVisualMaterial/PreviewSurface")
        scope_metadata = scope_prim.GetAllAuthoredMetadata()
        material_metadata = material_prim.GetAllAuthoredMetadata()
        shader_metadata = shader_prim.GetAllAuthoredMetadata()
        require(
            not scope_prim.GetAuthoredProperties()
            and not scope_prim.GetAppliedSchemas()
            and set(scope_metadata).issubset({"specifier", "typeName"}),
            "Scope de look avec métadonnées ou contenu hors contrat",
        )
        require(
            not material_prim.GetAppliedSchemas()
            and {prop.GetName() for prop in material_prim.GetAuthoredProperties()}
            == {"outputs:surface"}
            and set(material_metadata).issubset({"specifier", "typeName", "customData"}),
            "Material de look avec métadonnées hors contrat",
        )
        require(
            set(shader_prim.GetAppliedSchemas()) == {"NodeDefAPI"}
            and {prop.GetName() for prop in shader_prim.GetAuthoredProperties()}
            == {
                "info:id",
                "inputs:diffuseColor",
                "inputs:metallic",
                "inputs:roughness",
                "outputs:surface",
            }
            and set(shader_metadata).issubset({"specifier", "typeName"}),
            "Shader de look avec métadonnées hors contrat",
        )
    require(
        _base_stage_signature(source)
        == _base_stage_signature(target, look_prefix if expected_added_prims else None),
        "métadonnées, composition, attributs ou relations hors allowlist F42b modifiés",
    )
    source_schemas = {
        str(prim.GetPath()): {str(value) for value in prim.GetAppliedSchemas()}
        for prim in source.TraverseAll()
    }

    applied_schemas: dict[str, list[str]] = {}
    forbidden_schemas: list[str] = []
    forbidden_prim_types: list[str] = []
    forbidden_properties: list[str] = []
    collision_meshes: list[str] = []
    mesh_collision_api_meshes: list[str] = []
    collision_enabled: dict[str, bool] = {}
    material_bindings: dict[str, str] = dict(target_material_bindings)
    material_contracts: dict[str, dict[str, Any]] = {}
    mesh_paths: list[str] = []
    for prim in target.TraverseAll():
        path = str(prim.GetPath())
        type_name = prim.GetTypeName()
        if any(token in type_name.lower() for token in FORBIDDEN_PRIM_TYPE_TOKENS):
            forbidden_prim_types.append(f"{path}:{type_name}")
        schemas = [str(value) for value in prim.GetAppliedSchemas()]
        if schemas:
            applied_schemas[path] = schemas
        if path in source_prims:
            expected_schemas = set(source_schemas[path])
            if type_name == "Mesh" and stage_name in {"material", "physics", "final"}:
                expected_schemas.add("MaterialBindingAPI")
            if type_name == "Mesh" and stage_name in {"physics", "final"}:
                expected_schemas.add("PhysicsCollisionAPI")
            require(set(schemas) == expected_schemas, f"schemas appliqués hors allowlist: {path}")
        for schema in schemas:
            if physics_schema_forbidden(schema):
                forbidden_schemas.append(f"{path}:{schema}")
            elif not physics_schema_allowed_on_prim(schema, type_name):
                forbidden_schemas.append(f"{path}:{schema}:non-Mesh")
        for prop in prim.GetProperties():
            name = prop.GetName()
            if prop.IsAuthored() and physics_property_forbidden(name):
                forbidden_properties.append(f"{path}:{name}")
            elif prop.IsAuthored() and name in ALLOWED_AUTHORED_PHYSICS_PROPERTIES:
                attribute = prim.GetAttribute(name)
                valid_context = bool(attribute) and physics_property_context_valid(
                    name,
                    type_name,
                    schemas,
                    stage_name,
                    attribute.Get(),
                    bool(attribute.GetTimeSamples()),
                    bool(attribute.GetConnections()),
                )
                if not valid_context:
                    forbidden_properties.append(f"{path}:{name}:contexte-ou-valeur")
        binding_properties = sorted(
            prop.GetName() for prop in prim.GetProperties()
            if prop.GetName().startswith("material:binding")
        )
        require(
            material_binding_properties_valid(binding_properties, type_name, stage_name),
            f"binding purpose/collection ou binding sur prim interdit: {path}",
        )
        if prim.GetTypeName() != "Mesh":
            continue
        mesh_paths.append(path)
        has_collision, has_mesh_collision = collision_schema_flags(schemas)
        if has_collision:
            enabled = prim.GetAttribute("physics:collisionEnabled").Get()
            collision_enabled[path] = enabled is True
            if enabled is True:
                collision_meshes.append(path)
        if has_mesh_collision:
            mesh_collision_api_meshes.append(path)
    require(not forbidden_schemas, f"schemas physiques interdits: {forbidden_schemas}")
    require(not forbidden_prim_types, f"types de prim physiques interdits: {forbidden_prim_types}")
    require(not forbidden_properties, f"proprietes physiques ou FEA interdites: {forbidden_properties}")
    require(
        {
            path: signature["relationship_metadata"]
            for path, signature in target_material_signatures.items()
        }
        == {
            path: signature["relationship_metadata"]
            for path, signature in source_material_signatures.items()
        },
        "les métadonnées des bindings F42a ne doivent pas être altérées",
    )
    if stage_name == "minimum":
        require(
            target_material_signatures == source_material_signatures,
            "les bindings all-purpose F42a et leurs métadonnées doivent rester identiques au gate minimum",
        )
        require(not collision_enabled and not mesh_collision_api_meshes, "collision inattendue au gate minimum")
    if stage_name in {"material", "physics", "final"}:
        require(set(material_bindings) == set(mesh_paths), "chaque Mesh doit conserver un binding materiau visuel")
        assignment = assignment_for(contract, family)
        visual_label = assignment["visual_material"]
        expected_parameters = VISUAL_PALETTE[visual_label]
        expected_material_path = f"{entry['default_prim_path']}/F42bContractLooks/CanonicalVisualMaterial"
        expected_shader_path = f"{expected_material_path}/PreviewSurface"
        for mesh_path in mesh_paths:
            require(material_bindings[mesh_path] == expected_material_path, f"matériau contractuel différent: {mesh_path}")
            material = UsdShade.Material(target.GetPrimAtPath(expected_material_path))
            require(material and material.GetPrim().IsValid(), "Material contractuel absent")
            require(
                {prop.GetName() for prop in material.GetPrim().GetAuthoredProperties()} == {"outputs:surface"},
                "outputs Material hors contrat ou renderContext alternatif",
            )
            custom = material.GetPrim().GetAllAuthoredMetadata().get("customData", {})
            require(
                set(custom)
                == {
                    "f42b_visual_material",
                    "f42b_visual_source_sha256",
                    "f42b_claim_scope",
                },
                "customData Material hors contrat",
            )
            require(custom.get("f42b_visual_material") == visual_label, "identifiant matériau visuel différent")
            require(custom.get("f42b_visual_source_sha256") == contract["materials"]["visual_palette_source"]["sha256"], "source du matériau visuel différente")
            require(custom.get("f42b_claim_scope") == contract["materials"]["visual_claim_scope"], "scope du matériau visuel différent")
            surface = material.GetSurfaceOutput()
            connected = surface.GetConnectedSource() if surface else None
            require(connected is not None, "shader de surface contractuel non connecté")
            require(
                str(connected[0].GetPrim().GetPath()) == expected_shader_path
                and str(connected[1]) == "surface",
                "connexion surface vers un shader alternatif",
            )
            shader = UsdShade.Shader(connected[0].GetPrim())
            require(shader and shader.GetPrim().IsValid(), "UsdPreviewSurface contractuel absent")
            require(str(shader.GetPrim().GetPath()) == expected_shader_path, "chemin shader contractuel différent")
            require(shader.GetIdAttr().Get() == "UsdPreviewSurface", "shader visuel différent de UsdPreviewSurface")
            require(
                {prop.GetName() for prop in shader.GetPrim().GetAuthoredProperties()}
                == {
                    "info:id",
                    "inputs:diffuseColor",
                    "inputs:metallic",
                    "inputs:roughness",
                    "outputs:surface",
                },
                "propriétés ou outputs shader visuel hors contrat",
            )
            inputs = {value.GetBaseName(): value for value in shader.GetInputs()}
            require(set(inputs) == {"diffuseColor", "metallic", "roughness"}, "inputs shader visuel hors contrat")
            require(
                all(not value.GetAttr().GetConnections() for value in inputs.values()),
                "input UsdPreviewSurface connecté à un nœud alternatif",
            )
            diffuse = inputs["diffuseColor"].Get()
            require(diffuse is not None and all(math.isclose(float(diffuse[index]), expected, abs_tol=1e-6) for index, expected in enumerate(expected_parameters["diffuse_color"])), "diffuseColor visuelle différente")
            require(math.isclose(float(inputs["metallic"].Get()), expected_parameters["metallic"], abs_tol=1e-6), "metallic visuel différent")
            require(math.isclose(float(inputs["roughness"].Get()), expected_parameters["roughness"], abs_tol=1e-6), "roughness visuelle différente")
            material_contracts[mesh_path] = {
                "material_path": expected_material_path,
                "shader_path": expected_shader_path,
                "visual_material_assignment": visual_label,
                "visual_material_parameters": expected_parameters,
                "visual_source_sha256": contract["materials"]["visual_palette_source"]["sha256"],
            }
    if stage_name == "material":
        require(not collision_enabled and not mesh_collision_api_meshes, "le gate material ne doit pas ajouter de collision")
    if stage_name in {"physics", "final"}:
        require(set(collision_meshes) == set(mesh_paths), "CollisionAPI statique requise sur chaque Mesh existant")
        require(not mesh_collision_api_meshes, "MeshCollisionAPI omise par le profil F42b déterministe")

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed",
        "passed": True,
        "workflow_profile": WORKFLOW_PROFILE,
        "family_id": family,
        "audit_stage": stage_name,
        "source_asset_path": str(source_path),
        "source_asset_sha256": sha256(source_path),
        "asset_path": str(asset_path),
        "asset_sha256": sha256(asset_path),
        "output_paths": [str(asset_path)],
        "default_prim_path": entry["default_prim_path"],
        "geometry_identical_to_f42a": True,
        "geometry_signature_sha256": source_geometry["sha256"],
        "mesh_paths": mesh_paths,
        "source_material_bindings": source_material_bindings,
        "source_material_binding_signatures": source_material_signatures,
        "material_bindings": material_bindings,
        "material_binding_signatures": target_material_signatures,
        "material_contracts": material_contracts,
        "collision_mesh_paths": collision_meshes,
        "mesh_collision_api_paths": mesh_collision_api_meshes,
        "collision_enabled": collision_enabled,
        "applied_schemas": applied_schemas,
        "forbidden_schema_count": 0,
        "forbidden_prim_type_count": 0,
        "forbidden_property_count": 0,
        "physics_mode": "static_collision_diagnostics_only",
        "joint_count": 0,
        "rigid_body_count": 0,
        "mass_property_count": 0,
        "time_stepping_executed": False,
        "physicsnemo_simulation_executed": False,
        "fea_executed": False,
        "simulation_validated": False,
        "manufacturing_authorized": False,
    }


def _validation_chain(latest_path: Path, asset: Path) -> list[Path]:
    latest = read_json(latest_path, "rapport validate-physics")

    def load_phase(path: Path, expected: str) -> dict[str, Any]:
        report = read_json(path, f"rapport {expected}")
        require(report.get("phase") == expected, f"phase precedente attendue: {expected}")
        status = report.get("status")
        require(status in {"passed", "needs_rerun"}, f"validation {expected} non terminee")
        require(report.get("passed") is (status == "passed"), f"statut/passed incoherent: {expected}")
        require(report.get("exit_code") == (0 if status == "passed" else 3), f"code de validation incoherent: {expected}")
        outputs = report.get("output_paths")
        require(isinstance(outputs, list) and len(outputs) == 1, f"sortie unique absente: {expected}")
        require(Path(str(outputs[0])).resolve(strict=True) == asset.resolve(strict=True), f"validation {expected} appliquee a un autre USD")
        return report

    def previous(report: dict[str, Any], expected: str) -> Path:
        matches = []
        for value in report.get("input_paths", []):
            candidate = Path(str(value))
            if not candidate.is_file() or candidate.suffix.lower() != ".json":
                continue
            try:
                nested = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if isinstance(nested, dict) and nested.get("phase") == expected:
                matches.append(candidate.resolve(strict=True))
        require(len(matches) == 1, f"chainage {expected} absent ou ambigu")
        return matches[0]

    physics = load_phase(latest_path, "validate-physics")
    geometry_path = previous(physics, "validate-geometry")
    geometry = load_phase(geometry_path, "validate-geometry")
    asset_path = previous(geometry, "validate-asset")
    load_phase(asset_path, "validate-asset")
    return [asset_path, geometry_path, latest_path.resolve(strict=True)]


def _validation_passed(report: dict[str, Any]) -> bool:
    status = str(report.get("status", "passed")).lower()
    return report.get("passed") is True and status in {"pass", "passed", "ready"}


def _aware_datetime(value: Any, label: str) -> datetime:
    require(isinstance(value, str) and value, f"timestamp absent: {label}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"timestamp invalide: {label}") from exc
    require(parsed.tzinfo is not None, f"timestamp sans fuseau: {label}")
    return parsed


def _phase_duration(path: Path, expected_phase: str, job_id: str, *, allow_findings: bool) -> dict[str, Any]:
    report = read_json(path, f"rapport {expected_phase}")
    require(report.get("schema_version") == SCHEMA_VERSION, f"schema de phase inattendu: {expected_phase}")
    require(report.get("phase") == expected_phase, f"phase attendue: {expected_phase}")
    status = report.get("status")
    allowed = {"passed", "needs_rerun"} if allow_findings else {"passed"}
    require(status in allowed, f"phase pilote non terminee: {expected_phase}")
    require(report.get("passed") is (status == "passed"), f"statut/passed incoherents: {expected_phase}")
    expected_exit_code = 0 if status == "passed" else 3
    require(
        type(report.get("exit_code")) is int
        and report.get("exit_code") == expected_exit_code,
        f"code de sortie incoherent: {expected_phase}",
    )
    control = report.get("control")
    require(isinstance(control, dict) and control.get("job_id") == job_id, f"phase d'un autre job: {expected_phase}")
    started = _aware_datetime(report.get("started_at"), f"{expected_phase}.started_at")
    finished = _aware_datetime(report.get("finished_at"), f"{expected_phase}.finished_at")
    elapsed = (finished - started).total_seconds()
    require(0 <= elapsed <= 10800, f"duree de phase invalide: {expected_phase}")
    return {
        "phase": expected_phase,
        "status": status,
        "duration_seconds": int(math.ceil(elapsed)),
        "report_filename": path.name,
        "report_sha256": sha256(path.resolve(strict=True)),
    }


def project_runtime(contract_path: Path, output_root: Path, job_id: str) -> dict[str, Any]:
    contract = validate_contract(contract_path, permit_pending=True)
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", job_id) is not None, "job-id invalide")
    root = output_root.resolve(strict=True)
    require(root.name == job_id, "output-root doit designer le job exact")
    pilot = contract["execution"]["pilot_family"]
    pilot_run = f"{job_id}-{pilot}"
    common_reports = [
        _phase_duration(root / "readiness" / job_id / "phase-readiness.json", "readiness", job_id, allow_findings=False),
        _phase_duration(root / "preflight" / job_id / "phase-preflight.json", "preflight", job_id, allow_findings=False),
    ]
    pilot_reports = []
    for phase in TOP_LEVEL_PHASES:
        pilot_reports.append(
            _phase_duration(
                root / phase / pilot_run / f"phase-{phase}.json",
                phase,
                job_id,
                allow_findings=phase in {"validate-asset", "validate-geometry", "validate-physics"},
            )
        )
    common_seconds = sum(item["duration_seconds"] for item in common_reports)
    pilot_seconds = sum(item["duration_seconds"] for item in pilot_reports)
    projected = common_seconds + len(FAMILY_ORDER) * pilot_seconds
    maximum = contract["execution"]["max_projected_total_seconds"]
    passed = projected <= maximum
    return {
        "schema_version": SCHEMA_VERSION,
        "workflow_profile": WORKFLOW_PROFILE,
        "status": "passed" if passed else "blocked_projected_runtime_exceeds_limit",
        "passed": passed,
        "job_id": job_id,
        "pilot_family": pilot,
        "pilot_run_id": pilot_run,
        "pilot_includes_ovrtx_render": True,
        "common_phase_durations": common_reports,
        "pilot_phase_durations": pilot_reports,
        "common_duration_seconds": common_seconds,
        "pilot_duration_seconds": pilot_seconds,
        "projection_formula": "common_readiness_preflight_seconds + 6 * pilot_family_pipeline_seconds",
        "projected_total_seconds": projected,
        "max_projected_total_seconds": maximum,
        "remaining_families_authorized": passed,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def final_payload(
    contract_path: Path,
    family: str,
    source_path: Path,
    final_path: Path,
    audit_path: Path,
    simready_path: Path,
    render_path: Path,
    turntable_path: Path,
    attestation_path: Path,
) -> dict[str, Any]:
    contract = validate_contract(contract_path, permit_pending=True)
    entry = family_entry(contract, family)
    source = verify_asset(source_path, entry)
    final = regular_file(final_path, "USD final F42b")
    audit = read_json(audit_path, "audit final F42b")
    simready = read_json(simready_path, "validation SimReady")
    render = read_json(render_path, "rapport OVRTX")
    turntable = read_json(turntable_path, "rapport turntable OVRTX")
    attestation = read_json(attestation_path, "attestation media F42b")
    require(audit.get("passed") is True and audit.get("asset_sha256") == sha256(final), "audit final absent ou lie a un autre USD")
    require(render.get("passed") is True and turntable.get("passed") is True, "rendu OVRTX incomplet")
    require(attestation.get("passed") is True and attestation.get("family_id") == family, "attestation media incoherente")
    simready_validated = _validation_passed(simready)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_visual_diagnostics_simready_validated" if simready_validated else "passed_visual_diagnostics_simready_findings_require_rerun",
        "passed": True,
        "workflow_profile": WORKFLOW_PROFILE,
        "family_id": family,
        "source_usd": {"filename": source.name, "size_bytes": source.stat().st_size, "sha256": sha256(source)},
        "final_usd": {"filename": final.name, "size_bytes": final.stat().st_size, "sha256": sha256(final)},
        "geometry_identical_to_f42a": True,
        "visual_material_assignment": assignment_for(contract, family)["visual_material"],
        "historical_material_status": assignment_for(contract, family)["historical_material_status"],
        "physics_material_properties_known": False,
        "physics_mode": "static_collision_diagnostics_only",
        "nvidia_profile": f"{PROFILE}@{PROFILE_VERSION}",
        "simready_validation_only": True,
        "simready_auto_repair_attempted": False,
        "fet004_auto_repair_attempted": False,
        "fet005_auto_repair_attempted": False,
        "simready_validated": simready_validated,
        "ovrtx_preview_validated": True,
        "ovrtx_turntable_validated": True,
        "media": attestation.get("media"),
        "joint_count": 0,
        "rigid_body_count": 0,
        "mass_property_count": 0,
        "simulation_executed": False,
        "simulation_validated": False,
        "fea_executed": False,
        "fea_validated": False,
        "manufacturing_authorized": False,
        "performance_claim_authorized": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-contract")
    validate.add_argument("--contract", required=True, type=Path)
    validate.add_argument("--require-qualified-runtime", action="store_true")
    validate.add_argument("--runtime-attestation", type=Path)
    validate.add_argument("--runtime-job-id")
    validate.add_argument("--runtime-nonce")

    inputs = sub.add_parser("verify-input-root")
    inputs.add_argument("--contract", required=True, type=Path)
    inputs.add_argument("--input-root", required=True, type=Path)
    inputs.add_argument("--report", type=Path)

    control = sub.add_parser("verify-control")
    control.add_argument("--contract", required=True, type=Path)
    control.add_argument("--control", required=True, type=Path)
    control.add_argument("--family", choices=FAMILY_ORDER)

    context = sub.add_parser("context")
    context.add_argument("--contract", required=True, type=Path)
    context.add_argument("--control", required=True, type=Path)
    context.add_argument("--family", required=True, choices=FAMILY_ORDER)
    context.add_argument("--report", required=True, type=Path)
    context.add_argument("--markdown-report", required=True, type=Path)

    audit = sub.add_parser("audit-usd")
    audit.add_argument("--contract", required=True, type=Path)
    audit.add_argument("--family", required=True, choices=FAMILY_ORDER)
    audit.add_argument("--source-asset", required=True, type=Path)
    audit.add_argument("--asset", required=True, type=Path)
    audit.add_argument("--stage", required=True, choices=("minimum", "material", "physics", "final"))
    audit.add_argument("--report", required=True, type=Path)

    material = sub.add_parser("author-material")
    material.add_argument("--contract", required=True, type=Path)
    material.add_argument("--family", required=True, choices=FAMILY_ORDER)
    material.add_argument("--asset", required=True, type=Path)
    material.add_argument("--report", required=True, type=Path)

    clone = sub.add_parser("clone-stage")
    clone.add_argument("--source", required=True, type=Path)
    clone.add_argument("--destination", required=True, type=Path)

    physics = sub.add_parser("author-static-collisions")
    physics.add_argument("--contract", required=True, type=Path)
    physics.add_argument("--family", required=True, choices=FAMILY_ORDER)
    physics.add_argument("--asset", required=True, type=Path)
    physics.add_argument("--report", required=True, type=Path)

    chain = sub.add_parser("verify-validation-chain")
    chain.add_argument("--latest", required=True, type=Path)
    chain.add_argument("--asset", required=True, type=Path)

    validation_report = sub.add_parser("classify-nvidia-validation")
    validation_report.add_argument("--report", required=True, type=Path)
    validation_report.add_argument("--asset", required=True, type=Path)
    validation_report.add_argument("--validator-skill", required=True)
    validation_report.add_argument("--exit-code", required=True, type=int)

    runtime = sub.add_parser("project-runtime")
    runtime.add_argument("--contract", required=True, type=Path)
    runtime.add_argument("--output-root", required=True, type=Path)
    runtime.add_argument("--job-id", required=True)
    runtime.add_argument("--report", required=True, type=Path)

    final = sub.add_parser("final-report")
    final.add_argument("--contract", required=True, type=Path)
    final.add_argument("--family", required=True, choices=FAMILY_ORDER)
    final.add_argument("--source-asset", required=True, type=Path)
    final.add_argument("--asset", required=True, type=Path)
    final.add_argument("--audit-report", required=True, type=Path)
    final.add_argument("--simready-report", required=True, type=Path)
    final.add_argument("--render-report", required=True, type=Path)
    final.add_argument("--turntable-report", required=True, type=Path)
    final.add_argument("--media-attestation", required=True, type=Path)
    final.add_argument("--report", required=True, type=Path)
    final.add_argument("--markdown-report", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate-contract":
            validate_contract(
                args.contract,
                permit_pending=not args.require_qualified_runtime,
                runtime_attestation_path=args.runtime_attestation,
                runtime_job_id=args.runtime_job_id,
                runtime_nonce=args.runtime_nonce,
            )
            return 0
        if args.command == "verify-input-root":
            contract = validate_contract(args.contract, permit_pending=True)
            assets = verify_input_root(contract, args.input_root)
            if args.report:
                atomic_json(args.report, {
                    "schema_version": SCHEMA_VERSION,
                    "status": "passed",
                    "passed": True,
                    "workflow_profile": WORKFLOW_PROFILE,
                    "asset_count": 6,
                    "total_size_bytes": sum(item["size_bytes"] for item in assets),
                    "assets": assets,
                    "private_artifacts_committed": False,
                })
            return 0
        if args.command == "verify-control":
            _, value = verify_control(args.contract, args.control, args.family)
            print(value)
            return 0
        if args.command == "context":
            payload = context_payload(args.contract, args.control, args.family)
            atomic_json(args.report, payload)
            atomic_text(
                args.markdown_report,
                "\n".join((
                    f"# Contexte F42b — {args.family}",
                    "",
                    f"- Affectation visuelle : `{payload['visual_material_assignment']}`.",
                    f"- Statut historique : `{payload['historical_material_status']}`.",
                    "- Propriétés physiques matériau : inconnues, non authorées.",
                    "- Physique : colliders statiques diagnostiques seulement.",
                    "- Simulation, FEA et autorisation de fabrication : non validées.",
                    "",
                )),
            )
            return 0
        if args.command == "audit-usd":
            contract = validate_contract(args.contract, permit_pending=True)
            payload = _stage_audit(contract, args.family, args.source_asset, args.asset, args.stage)
            atomic_json(args.report, payload)
            return 0
        if args.command == "author-material":
            author_visual_material(
                args.contract, args.family, args.asset, args.report
            )
            return 0
        if args.command == "clone-stage":
            print(clone_contract_stage(args.source, args.destination))
            return 0
        if args.command == "author-static-collisions":
            author_static_collisions(
                args.contract, args.family, args.asset, args.report
            )
            return 0
        if args.command == "verify-validation-chain":
            for path in _validation_chain(args.latest, args.asset):
                print(path)
            return 0
        if args.command == "classify-nvidia-validation":
            print(classify_nvidia_validation(
                args.report, args.asset, args.validator_skill, args.exit_code
            ))
            return 0
        if args.command == "project-runtime":
            payload = project_runtime(args.contract, args.output_root, args.job_id)
            atomic_json(args.report, payload)
            return 0 if payload["passed"] else 2
        if args.command == "final-report":
            payload = final_payload(
                args.contract, args.family, args.source_asset, args.asset,
                args.audit_report, args.simready_report, args.render_report,
                args.turntable_report, args.media_attestation,
            )
            atomic_json(args.report, payload)
            atomic_text(
                args.markdown_report,
                "\n".join((
                    f"# F42b GPU — {args.family}",
                    "",
                    f"- Statut : `{payload['status']}`.",
                    "- Géométrie F42a : inchangée.",
                    "- Physique : colliders statiques diagnostiques seulement.",
                    f"- Validation SimReady : `{str(payload['simready_validated']).lower()}` (sans auto-réparation).",
                    "- Photos et film : rendu OVRTX attesté.",
                    "- Simulation, FEA, fabrication et revendication de performance : non autorisées.",
                    "",
                )),
            )
            return 0
    except ContractError as exc:
        print(f"F42b contract error: {exc}", file=os.sys.stderr)
        return 2
    raise AssertionError("commande non traitee")


if __name__ == "__main__":
    raise SystemExit(main())
