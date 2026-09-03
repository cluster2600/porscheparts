#!/usr/bin/env python3
"""Valider le bundle public F41 avant son extraction pour la CAO."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import tempfile
from typing import BinaryIO


INBOX = Path("/workspace/inbox")
JOBS = Path("/workspace/jobs")
CAD_UID = 9178
CAD_GID = 9178
BUNDLE_ROOT = "917-component-factory-f41"
BUNDLE_MANIFEST_RELATIVE = "BUNDLE-MANIFEST.json"
BUNDLE_MANIFEST = f"{BUNDLE_ROOT}/{BUNDLE_MANIFEST_RELATIVE}"
F28_RUNTIME_IMAGE = (
    "ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:"
    "18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57"
)
USD_RUNTIME_IMAGE = (
    "ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:"
    "41ddde8e527fcc17a3f29ac90183bd1326c330388240baf2004f99de980d6ebe"
)
REQUIRED_RUNTIME_IMAGES = [F28_RUNTIME_IMAGE, USD_RUNTIME_IMAGE]
# Cette allowlist reproduit le builder public F41. Un changement du bundle doit
# donc d'abord mettre a jour et tester explicitement cette frontiere.
ALLOWED_BUNDLE_RELATIVE_FILES = frozenset(
    {
        "REMOTE_JOB.md",
        "containers/simready-preflight/convert.py",
        "docs/917_COMPONENT_FACTORY_F41.md",
        "twins/reference-917-engine/component-factory-f41.json",
        "twins/reference-917-engine/rotating-assembly-cad-f35.json",
        "twins/reference-917-engine/source/build_rotating_assembly_cad_f35.py",
        "twins/reference-917-engine/source/execute_component_factory_f41.py",
        "twins/reference-917-engine/source/rotating_assembly_f35_math.py",
        "twins/reference-917-engine/source/run_component_factory_f41_cad_job.sh",
        "twins/reference-917-engine/source/run_component_factory_f41_usd_job.sh",
    }
)
EXPECTED_BUNDLE_FILE_MODES = {
    "REMOTE_JOB.md": "0644",
    "containers/simready-preflight/convert.py": "0644",
    "docs/917_COMPONENT_FACTORY_F41.md": "0644",
    "twins/reference-917-engine/component-factory-f41.json": "0644",
    "twins/reference-917-engine/rotating-assembly-cad-f35.json": "0644",
    "twins/reference-917-engine/source/build_rotating_assembly_cad_f35.py": "0644",
    "twins/reference-917-engine/source/execute_component_factory_f41.py": "0755",
    "twins/reference-917-engine/source/rotating_assembly_f35_math.py": "0644",
    "twins/reference-917-engine/source/run_component_factory_f41_cad_job.sh": "0755",
    "twins/reference-917-engine/source/run_component_factory_f41_usd_job.sh": "0755",
}
if set(EXPECTED_BUNDLE_FILE_MODES) != set(ALLOWED_BUNDLE_RELATIVE_FILES):
    raise RuntimeError("F41 bundle mode contract does not match the path allowlist")
JOB_ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
REVISION_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
PUBLIC_REMOTE_REF_RE = re.compile(
    r"refs/remotes/[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._/-]{0,254}"
)
MAX_ARCHIVE_BYTES = 512 * 1024**2
MAX_MEMBER_COUNT = 10_000
MAX_EXPANDED_BYTES = 2 * 1024**3
MAX_SINGLE_FILE_BYTES = 64 * 1024**2
MAX_MANIFEST_BYTES = 1024**2
ALLOWED_SUFFIXES = {
    ".csv",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
ALLOWED_BASENAMES = {"COPYING", "LICENSE", "Makefile", ".gitignore"}
FORBIDDEN_PATH_PARTS = {
    ".git",
    ".ssh",
    "private",
    "proprietary",
    "raw-scans",
    "secrets",
}
FORBIDDEN_FILENAMES = {
    ".env",
    "authorized_keys",
    "id_ed25519",
    "id_rsa",
    "id_vastai",
}
FORBIDDEN_TEXT_MARKERS = (
    b"/Users/",
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
    b"-----BEGIN PRIVATE KEY-----",
    b"NVIDIA_API_KEY=",
    b"OPENBAO_TOKEN=",
    b"VAST_API_KEY=",
)


class StagingError(RuntimeError):
    """Bundle ou destination hors contrat public."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise StagingError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_name(raw_name: str) -> str:
    require(bool(raw_name), "archive_member_name_empty")
    require("\\" not in raw_name, "archive_member_backslash_rejected")
    path = PurePosixPath(raw_name)
    require(not path.is_absolute(), "archive_absolute_path_rejected")
    require(".." not in path.parts, "archive_parent_path_rejected")
    normalized = path.as_posix()
    require(normalized not in ("", "."), "archive_member_name_invalid")
    return normalized


def validate_public_path(name: str, *, is_directory: bool) -> None:
    path = PurePosixPath(name)
    require(
        name == BUNDLE_ROOT or name.startswith(f"{BUNDLE_ROOT}/"),
        "bundle_root_rejected",
    )
    lowered_parts = {part.lower() for part in path.parts}
    require(
        not lowered_parts.intersection(FORBIDDEN_PATH_PARTS),
        "private_or_repository_path_rejected",
    )
    if is_directory:
        return
    basename = path.name
    require(basename not in FORBIDDEN_FILENAMES, "secret_filename_rejected")
    if name == BUNDLE_MANIFEST:
        return
    relative = path.relative_to(PurePosixPath(BUNDLE_ROOT)).as_posix()
    require(relative in ALLOWED_BUNDLE_RELATIVE_FILES, "bundle_path_not_allowlisted")
    require(
        basename in ALLOWED_BASENAMES or path.suffix.lower() in ALLOWED_SUFFIXES,
        "non_text_or_geometry_payload_rejected",
    )


def validate_members(members: list[tarfile.TarInfo]) -> tuple[int, dict[str, tarfile.TarInfo]]:
    require(len(members) <= MAX_MEMBER_COUNT, "archive_member_limit_exceeded")
    indexed: dict[str, tarfile.TarInfo] = {}
    expanded_bytes = 0
    for member in members:
        name = normalized_name(member.name)
        require(name not in indexed, "archive_duplicate_member_rejected")
        require(member.isdir() or member.isreg(), "archive_special_member_rejected")
        validate_public_path(name, is_directory=member.isdir())
        indexed[name] = member
        if member.isreg():
            require(member.size >= 0, "archive_negative_member_size")
            require(member.size <= MAX_SINGLE_FILE_BYTES, "archive_file_limit_exceeded")
            expanded_bytes += member.size
            require(expanded_bytes <= MAX_EXPANDED_BYTES, "archive_expanded_limit_exceeded")
    return expanded_bytes, indexed


def read_member(handle: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    stream: BinaryIO | None = handle.extractfile(member)
    require(stream is not None, "archive_regular_member_unreadable")
    payload = stream.read(MAX_SINGLE_FILE_BYTES + 1)
    stream.close()
    require(len(payload) == member.size, "archive_member_size_mismatch")
    return payload


def validate_public_bundle(
    handle: tarfile.TarFile, members: list[tarfile.TarInfo]
) -> dict[str, object]:
    expanded_bytes, indexed = validate_members(members)
    require(BUNDLE_MANIFEST in indexed, "bundle_manifest_missing")
    manifest_member = indexed[BUNDLE_MANIFEST]
    require(manifest_member.isreg(), "public_manifest_not_regular")
    require(manifest_member.size <= MAX_MANIFEST_BYTES, "public_manifest_too_large")
    manifest_payload = read_member(handle, manifest_member)
    try:
        manifest = json.loads(manifest_payload.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StagingError(f"public_manifest_invalid: {error}") from error
    require(isinstance(manifest, dict), "public_manifest_not_object")
    expected_keys = {
        "all_payload_files_utf8_text",
        "archive_member_count",
        "binary_payload_included",
        "bundle_root",
        "file_count",
        "files",
        "newly_generated_geometry_included",
        "phase",
        "private_absolute_path_included",
        "public_remote_refs",
        "raw_scan_included",
        "required_runtime_images",
        "schema_version",
        "secret_included",
        "source_repository_state",
        "source_revision",
        "status",
    }
    require(set(manifest) == expected_keys, "bundle_manifest_keys_mismatch")
    require(manifest["schema_version"] == "1.1.0", "bundle_manifest_schema_rejected")
    require(manifest["phase"] == "F41", "bundle_manifest_phase_rejected")
    require(
        manifest["status"] == "public_transfer_bundle_file_manifest",
        "bundle_manifest_status_rejected",
    )
    require(manifest["bundle_root"] == BUNDLE_ROOT, "bundle_manifest_root_rejected")
    require(
        manifest["source_repository_state"] == "clean_commit_visible_at_exact_remote_ref",
        "source_repository_state_rejected",
    )
    require(
        isinstance(manifest["source_revision"], str)
        and REVISION_RE.fullmatch(manifest["source_revision"]) is not None,
        "source_revision_rejected",
    )
    public_remote_refs = manifest["public_remote_refs"]
    require(
        isinstance(public_remote_refs, list)
        and 1 <= len(public_remote_refs) <= 32
        and all(isinstance(item, str) for item in public_remote_refs)
        and len(public_remote_refs) == len(set(public_remote_refs)),
        "public_remote_refs_rejected",
    )
    for remote_ref in public_remote_refs:
        require(
            isinstance(remote_ref, str)
            and PUBLIC_REMOTE_REF_RE.fullmatch(remote_ref) is not None
            and ".." not in remote_ref
            and "//" not in remote_ref,
            "public_remote_ref_rejected",
        )
    require(
        manifest["all_payload_files_utf8_text"] is True,
        "utf8_text_declaration_required",
    )
    require(manifest["binary_payload_included"] is False, "binary_declaration_rejected")
    require(manifest["raw_scan_included"] is False, "raw_scan_declaration_rejected")
    require(
        manifest["private_absolute_path_included"] is False,
        "private_absolute_path_declaration_rejected",
    )
    require(manifest["secret_included"] is False, "secret_declaration_rejected")
    require(
        manifest["newly_generated_geometry_included"] is False,
        "generated_geometry_declaration_rejected",
    )
    require(
        manifest["required_runtime_images"] == REQUIRED_RUNTIME_IMAGES,
        "runtime_image_contract_rejected",
    )

    declared_files = manifest["files"]
    require(isinstance(declared_files, list) and declared_files, "bundle_file_list_required")
    require(len(declared_files) <= MAX_MEMBER_COUNT, "public_file_map_limit_exceeded")
    require(manifest["file_count"] == len(declared_files), "bundle_file_count_mismatch")
    require(
        isinstance(manifest["archive_member_count"], int)
        and not isinstance(manifest["archive_member_count"], bool)
        and manifest["archive_member_count"] == len(members)
        and manifest["archive_member_count"] == len(declared_files) + 1,
        "archive_member_count_mismatch",
    )
    declared_by_name: dict[str, dict[str, object]] = {}
    for entry in declared_files:
        require(isinstance(entry, dict), "bundle_file_entry_not_object")
        require(
            set(entry) == {"mode", "path", "sha256", "size_bytes"},
            "bundle_file_entry_keys_mismatch",
        )
        relative_name = entry["path"]
        require(isinstance(relative_name, str), "bundle_file_name_not_string")
        require(normalized_name(relative_name) == relative_name, "bundle_file_name_not_normalized")
        require(relative_name in ALLOWED_BUNDLE_RELATIVE_FILES, "bundle_path_not_allowlisted")
        require(relative_name not in declared_by_name, "bundle_manifest_duplicate_file")
        require(
            isinstance(entry["sha256"], str)
            and SHA256_RE.fullmatch(entry["sha256"]) is not None,
            "bundle_file_digest_rejected",
        )
        require(
            isinstance(entry["size_bytes"], int)
            and not isinstance(entry["size_bytes"], bool)
            and 0 <= entry["size_bytes"] <= MAX_SINGLE_FILE_BYTES,
            "bundle_file_size_rejected",
        )
        expected_mode = EXPECTED_BUNDLE_FILE_MODES[relative_name]
        require(entry["mode"] == expected_mode, "bundle_file_mode_rejected")
        declared_by_name[relative_name] = entry

    payload_members = {
        PurePosixPath(name).relative_to(PurePosixPath(BUNDLE_ROOT)).as_posix(): member
        for name, member in indexed.items()
        if member.isreg() and name != BUNDLE_MANIFEST
    }
    require(set(declared_by_name) == set(payload_members), "bundle_file_list_not_exact")
    verified_hashes: dict[str, str] = {}
    payload_bytes = 0
    for name, entry in sorted(declared_by_name.items()):
        member = payload_members[name]
        require(
            member.mode & 0o777 == int(str(entry["mode"]), 8),
            "bundle_file_archive_mode_mismatch",
        )
        payload = read_member(handle, member)
        require(len(payload) == entry["size_bytes"], "bundle_file_declared_size_mismatch")
        actual_digest = sha256_bytes(payload)
        require(actual_digest == entry["sha256"], "bundle_file_digest_mismatch")
        require(b"\0" not in payload, "binary_payload_rejected")
        try:
            payload.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise StagingError(f"non_utf8_payload_rejected: {name}") from error
        require(
            not any(marker in payload for marker in FORBIDDEN_TEXT_MARKERS),
            "private_key_material_rejected",
        )
        verified_hashes[name] = actual_digest
        payload_bytes += len(payload)

    return {
        "bundle_root": BUNDLE_ROOT,
        "expanded_bytes": expanded_bytes,
        "manifest_sha256": sha256_bytes(manifest_payload),
        "payload_bytes": payload_bytes,
        "payload_file_count": len(payload_members),
        "public_remote_refs": public_remote_refs,
        "source_repository_state": manifest["source_repository_state"],
        "source_revision": manifest["source_revision"],
        "verified_hashes": verified_hashes,
    }


def sanitize_tree(root: Path) -> None:
    for current, directories, files in os.walk(root, topdown=False, followlinks=False):
        current_path = Path(current)
        for name in files:
            path = current_path / name
            require(not path.is_symlink(), "extracted_symlink_rejected")
            mode = path.stat().st_mode
            os.chmod(path, 0o750 if mode & 0o111 else 0o640)
            os.chown(path, CAD_UID, CAD_GID)
        for name in directories:
            path = current_path / name
            require(not path.is_symlink(), "extracted_symlink_rejected")
            os.chmod(path, 0o750)
            os.chown(path, CAD_UID, CAD_GID)
        os.chmod(current_path, 0o750)
        os.chown(current_path, CAD_UID, CAD_GID)


def stage_archive(archive: Path, job_id: str) -> dict[str, object]:
    require(os.geteuid() == 0, "stage_job_requires_root")
    require(JOB_ID_RE.fullmatch(job_id) is not None, "job_id_invalid")
    require(archive.parent.resolve() == INBOX.resolve(), "archive_must_be_in_inbox")
    require(archive.exists(), "archive_missing")
    require(archive.is_file() and not archive.is_symlink(), "archive_must_be_regular_file")
    require(archive.stat().st_size <= MAX_ARCHIVE_BYTES, "archive_size_limit_exceeded")

    target = JOBS / job_id
    require(not target.exists(), "job_already_exists")
    temporary = Path(tempfile.mkdtemp(prefix=f".{job_id}-", dir=JOBS))
    try:
        with tarfile.open(archive, mode="r:*") as handle:
            members = handle.getmembers()
            public = validate_public_bundle(handle, members)
            handle.extractall(temporary, members=members, filter="data")
        sanitize_tree(temporary)
        temporary.rename(target)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return {
        "schema_version": "1.0.0",
        "status": "public_archive_staged_cad_execution_not_started",
        "job_id": job_id,
        "archive_sha256": sha256_file(archive),
        "archive_bytes": archive.stat().st_size,
        "member_count": len(members),
        "expanded_regular_file_bytes": public["expanded_bytes"],
        "bundle_manifest_sha256": public["manifest_sha256"],
        "public_payload_file_count": public["payload_file_count"],
        "public_payload_bytes": public["payload_bytes"],
        "bundle_root": public["bundle_root"],
        "project_root": str(target / BUNDLE_ROOT),
        "regular_payloads_utf8_text_only": True,
        "source_repository_state": public["source_repository_state"],
        "source_revision": public["source_revision"],
        "public_remote_refs": public["public_remote_refs"],
        "target": str(target),
        "target_uid": target.stat().st_uid,
        "target_gid": target.stat().st_gid,
        "cad_started": False,
        "private_assets_included": False,
        "secret_material_included": False,
        "physical_claims_validated": False,
        "manufacturing_authorized": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("job_id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = stage_archive(args.archive, args.job_id)
    except (OSError, StagingError, tarfile.TarError) as error:
        print(f"stage_job_error: {error}", file=sys.stderr)
        return 2
    json.dump(report, sys.stdout, indent=2, sort_keys=True, allow_nan=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
