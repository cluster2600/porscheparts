#!/usr/bin/env python3
"""Validate and extract one downloaded F41 CAD result archive fail-closed.

This validator proves transport integrity and the exact F41 CAD result
contract only.  It does not validate geometry, simulation, physical
correlation, or manufacturing readiness.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import gzip
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import sys
import tarfile
from typing import Any, BinaryIO
import zlib


REPO_ROOT = Path(__file__).resolve().parents[3]
FAMILIES = (
    "crankshaft",
    "main_bearing_pair",
    "connecting_rod",
    "piston",
    "piston_pin",
    "piston_ring",
)
FORMATS = ("STEP", "STL", "3MF")
EXPECTED_FORMAT_COUNTS = {"STEP": 6, "STL": 6, "3MF": 6, "USD": 0}
EXPECTED_STATUS = "passed_six_hash_bound_F35_seed_families_generated_not_released"
EXPECTED_RUNTIME_IMAGE = (
    "ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:"
    "18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57"
)
SOURCE_PATHS = {
    "source_contract_sha256": "twins/reference-917-engine/rotating-assembly-cad-f35.json",
    "source_generator_sha256": "twins/reference-917-engine/source/build_rotating_assembly_cad_f35.py",
    "source_math_sha256": "twins/reference-917-engine/source/rotating_assembly_f35_math.py",
}
RELEASE_GATE_KEYS = frozenset(
    {
        "all_3mf_meshes_validated",
        "all_editable_cad_generated",
        "all_family_counts_closed",
        "all_interface_dimensions_measured",
        "all_materials_qualified",
        "all_step_roundtrips_validated",
        "all_tolerances_and_clearances_released",
        "all_usd_assets_minimum_valid",
        "assembly_interference_check_passed",
        "combustion_and_boost_validated",
        "engine_start_authorized",
        "fatigue_and_rotordynamics_validated",
        "installation_in_993_authorized",
        "lubrication_and_cooling_validated",
        "metal_print_authorized",
        "performance_1600_hp_claim_authorized",
        "physical_dyno_correlated",
        "physical_flowbench_correlated",
        "professional_engineering_review_approved",
        "simready_property_assignment_complete",
    }
)

JOB_ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
MAX_COMPRESSED_BYTES = 512 * 1024**2
MAX_EXPANDED_BYTES = 2 * 1024**3
# This includes tar headers, PAX/GNU metadata and file payloads.  It is checked
# while inflating gzip, before tarfile parses any member.
MAX_DECOMPRESSED_TAR_BYTES = MAX_EXPANDED_BYTES + 64 * 1024**2
MAX_MEMBER_BYTES = 512 * 1024**2
MAX_MEMBER_COUNT = 100_000
MAX_PATH_BYTES = 1024
MAX_COMPONENT_BYTES = 255
MAX_JSON_BYTES = 16 * 1024**2
COPY_BLOCK_BYTES = 1024 * 1024
CLOSED_CLAIM_TOKENS = (
    "manufactur",
    "physical",
    "simulation",
    "engine_start",
    "metal_print",
    "1600_hp",
)


class ResultValidationError(RuntimeError):
    """The downloaded archive or its declared evidence violates the contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ResultValidationError(message)


def require_exact_int(value: object, expected: int, message: str) -> None:
    require(type(value) is int and value == expected, message)


def sha256_stream(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(COPY_BLOCK_BYTES), b""):
        digest.update(block)
    return digest.hexdigest()


def sha256_path(path: Path, *, require_nonempty: bool) -> tuple[str, int]:
    require(hasattr(os, "O_NOFOLLOW"), "O_NOFOLLOW_unavailable")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ResultValidationError(f"unsafe_or_missing_file:{path}:{error}") from error
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        require(stat.S_ISREG(metadata.st_mode), f"not_regular_file:{path}")
        require(not require_nonempty or metadata.st_size > 0, f"empty_file:{path}")
        return sha256_stream(stream), metadata.st_size


def artifact_relative_path(family: str, output_format: str) -> str:
    if output_format == "STEP":
        return f"artifacts/{family}/step/{family}.step"
    if output_format == "STL":
        return f"artifacts/{family}/stl/{family}-display-only.stl"
    if output_format == "3MF":
        return f"artifacts/{family}/3mf/{family}-prototype-only.3mf"
    raise AssertionError(output_format)


def expected_archive_layout(job_id: str) -> tuple[set[str], set[str]]:
    relative_files = {
        "cad-execution-report.json",
        "logs/f35-cad-seed.log",
        "preflight/cad.json",
    }
    for family in FAMILIES:
        relative_files.add(f"artifacts/{family}/cad-family-report.json")
        relative_files.update(artifact_relative_path(family, item) for item in FORMATS)
    files = {f"{job_id}/{item}" for item in relative_files}
    directories = {job_id}
    for name in files:
        path = PurePosixPath(name)
        for depth in range(1, len(path.parts)):
            directories.add(PurePosixPath(*path.parts[:depth]).as_posix())
    return files, directories


def checked_member_name(member: tarfile.TarInfo, job_id: str) -> tuple[str, PurePosixPath]:
    raw_name = member.name
    require(isinstance(raw_name, str) and bool(raw_name), "archive_member_name_empty")
    if member.isdir() and raw_name.endswith("/"):
        raw_name = raw_name[:-1]
    require(bool(raw_name), "archive_member_name_empty")
    require(raw_name.isascii(), f"archive_member_non_ascii:{member.name!r}")
    require("\\" not in raw_name, f"archive_member_backslash:{member.name!r}")
    require(
        not any(ord(character) < 32 or ord(character) == 127 for character in raw_name),
        f"archive_member_control_character:{member.name!r}",
    )
    raw_parts = raw_name.split("/")
    require(
        all(part not in ("", ".", "..") for part in raw_parts),
        f"archive_member_ambiguous_component:{member.name!r}",
    )
    path = PurePosixPath(raw_name)
    require(not path.is_absolute(), f"archive_member_absolute:{member.name!r}")
    require(path.as_posix() == raw_name, f"archive_member_noncanonical:{member.name!r}")
    require(path.parts and path.parts[0] == job_id, f"archive_member_wrong_root:{member.name!r}")
    require(len(raw_name.encode("ascii")) <= MAX_PATH_BYTES, f"archive_member_path_too_long:{member.name!r}")
    require(
        all(len(part.encode("ascii")) <= MAX_COMPONENT_BYTES for part in path.parts),
        f"archive_member_component_too_long:{member.name!r}",
    )
    return raw_name, path


def validate_archive_members(
    members: list[tarfile.TarInfo], job_id: str
) -> list[tuple[tarfile.TarInfo, str, PurePosixPath]]:
    require(bool(members), "archive_empty")
    require(len(members) <= MAX_MEMBER_COUNT, "archive_member_limit_exceeded")
    expected_files, expected_directories = expected_archive_layout(job_id)
    files: set[str] = set()
    directories: set[str] = set()
    exact_names: set[str] = set()
    casefold_names: dict[str, str] = {}
    path_types: dict[str, str] = {}
    total_bytes = 0
    checked: list[tuple[tarfile.TarInfo, str, PurePosixPath]] = []

    for member in members:
        name, path = checked_member_name(member, job_id)
        require(member.isfile() or member.isdir(), f"archive_member_special_type:{member.name!r}")
        require(member.size >= 0, f"archive_member_negative_size:{member.name!r}")
        if member.isdir():
            require(member.size == 0, f"archive_directory_nonzero_size:{member.name!r}")
            directories.add(name)
            member_type = "directory"
        else:
            require(member.size <= MAX_MEMBER_BYTES, f"archive_member_size_limit:{member.name!r}")
            total_bytes += member.size
            require(total_bytes <= MAX_EXPANDED_BYTES, "archive_expanded_size_limit")
            files.add(name)
            member_type = "file"

        require(name not in exact_names, f"archive_member_duplicate:{member.name!r}")
        exact_names.add(name)
        for depth in range(1, len(path.parts) + 1):
            prefix = PurePosixPath(*path.parts[:depth]).as_posix()
            folded = prefix.casefold()
            previous = casefold_names.get(folded)
            require(
                previous is None or previous == prefix,
                f"archive_member_casefold_collision:{previous!r}:{prefix!r}",
            )
            casefold_names[folded] = prefix
            if depth < len(path.parts):
                require(path_types.get(prefix) != "file", f"archive_file_directory_collision:{prefix!r}")
            else:
                previous_type = path_types.get(prefix)
                require(
                    previous_type is None or previous_type == member_type,
                    f"archive_file_directory_collision:{prefix!r}",
                )
                path_types[prefix] = member_type
        checked.append((member, name, path))

    for name, member_type in path_types.items():
        if member_type == "file":
            prefix = f"{name}/"
            require(
                not any(other.startswith(prefix) for other in exact_names),
                f"archive_file_directory_collision:{name!r}",
            )
    require(files == expected_files, "archive_regular_file_set_mismatch")
    require(directories == expected_directories, "archive_directory_set_mismatch")
    return checked


def directory_open_flags() -> int:
    require(hasattr(os, "O_NOFOLLOW"), "O_NOFOLLOW_unavailable")
    require(hasattr(os, "O_DIRECTORY"), "O_DIRECTORY_unavailable")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)


def open_directory_at(root_descriptor: int, parts: tuple[str, ...]) -> int:
    current = os.dup(root_descriptor)
    try:
        for part in parts:
            next_descriptor = os.open(part, directory_open_flags(), dir_fd=current)
            os.close(current)
            current = next_descriptor
        return current
    except BaseException:
        os.close(current)
        raise


def open_regular_at(root_descriptor: int, relative_path: str) -> int:
    path = PurePosixPath(relative_path)
    require(
        not path.is_absolute()
        and path.parts
        and all(part not in ("", ".", "..") for part in path.parts),
        f"unsafe_relative_result_path:{relative_path}",
    )
    parent_descriptor = open_directory_at(root_descriptor, tuple(path.parts[:-1]))
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        descriptor = os.open(path.parts[-1], flags, dir_fd=parent_descriptor)
    except BaseException:
        os.close(parent_descriptor)
        raise
    os.close(parent_descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        os.close(descriptor)
        raise ResultValidationError(f"result_not_regular:{relative_path}")
    return descriptor


def remove_tree_contents(directory_descriptor: int) -> None:
    for name in os.listdir(directory_descriptor):
        metadata = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
        if stat.S_ISDIR(metadata.st_mode):
            child = os.open(name, directory_open_flags(), dir_fd=directory_descriptor)
            try:
                remove_tree_contents(child)
            finally:
                os.close(child)
            os.rmdir(name, dir_fd=directory_descriptor)
        else:
            os.unlink(name, dir_fd=directory_descriptor)


def atomic_rename_noreplace(
    source_directory_descriptor: int,
    source_name: str,
    destination_directory_descriptor: int,
    destination_name: str,
) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    encoded_source = os.fsencode(source_name)
    encoded_destination = os.fsencode(destination_name)
    if hasattr(libc, "renameat2"):
        renameat2 = libc.renameat2
        renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            source_directory_descriptor,
            encoded_source,
            destination_directory_descriptor,
            encoded_destination,
            1,  # RENAME_NOREPLACE
        )
    elif hasattr(libc, "renameatx_np"):
        renameatx_np = libc.renameatx_np
        renameatx_np.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        renameatx_np.restype = ctypes.c_int
        result = renameatx_np(
            source_directory_descriptor,
            encoded_source,
            destination_directory_descriptor,
            encoded_destination,
            0x00000004,  # RENAME_EXCL on Darwin
        )
    else:  # pragma: no cover - Linux and macOS both expose one guarded primitive.
        raise ResultValidationError("atomic_noreplace_rename_unavailable")
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number in (errno.EEXIST, errno.ENOTEMPTY):
            raise ResultValidationError("extraction_output_must_be_new")
        raise ResultValidationError(
            f"atomic_result_publish_failed:{os.strerror(error_number)}"
        )


def decompress_gzip_to_tar(archive_stream: BinaryIO, staging_descriptor: int) -> tuple[int, int]:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )
    descriptor = os.open("archive.tar", flags, 0o600, dir_fd=staging_descriptor)
    total = 0
    try:
        with gzip.GzipFile(fileobj=archive_stream, mode="rb") as compressed, os.fdopen(
            descriptor, "wb", closefd=True
        ) as output:
            descriptor = -1
            while True:
                remaining = MAX_DECOMPRESSED_TAR_BYTES - total
                block = compressed.read(min(COPY_BLOCK_BYTES, remaining + 1))
                if not block:
                    break
                total += len(block)
                require(
                    total <= MAX_DECOMPRESSED_TAR_BYTES,
                    "gzip_decompressed_stream_limit_exceeded",
                )
                output.write(block)
            output.flush()
            os.fsync(output.fileno())
    except (gzip.BadGzipFile, EOFError, OSError, zlib.error) as error:
        raise ResultValidationError(f"gzip_stream_invalid:{error}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    require(total > 0, "gzip_decompressed_stream_empty")
    read_descriptor = os.open(
        "archive.tar",
        os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        dir_fd=staging_descriptor,
    )
    metadata = os.fstat(read_descriptor)
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_size == total, "decompressed_tar_size_mismatch")
    return read_descriptor, total


def create_private_staging(
    parent_descriptor: int, output_name: str
) -> tuple[str, int, int]:
    for _attempt in range(128):
        staging_name = f".{output_name}.f41-staging-{secrets.token_hex(10)}"
        try:
            os.mkdir(staging_name, mode=0o700, dir_fd=parent_descriptor)
        except FileExistsError:
            continue
        staging_descriptor = os.open(
            staging_name, directory_open_flags(), dir_fd=parent_descriptor
        )
        try:
            os.mkdir("payload", mode=0o700, dir_fd=staging_descriptor)
            payload_descriptor = os.open(
                "payload", directory_open_flags(), dir_fd=staging_descriptor
            )
        except BaseException:
            os.close(staging_descriptor)
            os.rmdir(staging_name, dir_fd=parent_descriptor)
            raise
        return staging_name, staging_descriptor, payload_descriptor
    raise ResultValidationError("private_staging_name_exhausted")


def cleanup_private_staging(
    parent_descriptor: int, staging_name: str | None, staging_descriptor: int
) -> None:
    if staging_name is None or staging_descriptor < 0:
        return
    try:
        remove_tree_contents(staging_descriptor)
    finally:
        os.close(staging_descriptor)
    try:
        os.rmdir(staging_name, dir_fd=parent_descriptor)
    except FileNotFoundError:
        pass


def require_destination_absent(parent_descriptor: int, name: str) -> None:
    try:
        os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return
    except OSError as error:
        raise ResultValidationError(f"extraction_output_status_failed:{error}") from error
    raise ResultValidationError("extraction_output_must_be_new")


def stable_file_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def extract_members(
    handle: tarfile.TarFile,
    members: list[tuple[tarfile.TarInfo, str, PurePosixPath]],
    extraction_descriptor: int,
) -> int:
    copied_total = 0
    ordered = sorted(
        members,
        key=lambda item: (len(item[2].parts), 0 if item[0].isdir() else 1, item[1]),
    )
    for member, _name, path in ordered:
        parent_descriptor = open_directory_at(extraction_descriptor, tuple(path.parts[:-1]))
        if member.isdir():
            try:
                os.mkdir(path.parts[-1], mode=0o700, dir_fd=parent_descriptor)
            except OSError as error:
                raise ResultValidationError(f"extraction_directory_failed:{member.name!r}:{error}") from error
            finally:
                os.close(parent_descriptor)
            continue

        source = handle.extractfile(member)
        if source is None:
            os.close(parent_descriptor)
            raise ResultValidationError(f"archive_member_unreadable:{member.name!r}")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
        try:
            descriptor = os.open(path.parts[-1], flags, 0o600, dir_fd=parent_descriptor)
        except OSError as error:
            source.close()
            raise ResultValidationError(f"unsafe_extraction_target:{member.name!r}:{error}") from error
        finally:
            os.close(parent_descriptor)
        copied = 0
        with source, os.fdopen(descriptor, "wb") as output:
            while True:
                block = source.read(COPY_BLOCK_BYTES)
                if not block:
                    break
                copied += len(block)
                require(copied <= member.size, f"archive_member_size_mismatch:{member.name!r}")
                copied_total += len(block)
                require(copied_total <= MAX_EXPANDED_BYTES, "archive_expanded_size_limit_during_copy")
                output.write(block)
            output.flush()
            os.fsync(output.fileno())
        require(copied == member.size, f"archive_member_size_mismatch:{member.name!r}")
    return copied_total


def duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ResultValidationError(f"json_duplicate_key:{key}")
        result[key] = value
    return result


def require_no_open_policy_flags(value: object, location: str) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key).casefold()
            if isinstance(nested, bool) and any(token in key_text for token in CLOSED_CLAIM_TOKENS):
                require(nested is False, f"policy_flag_must_remain_false:{location}.{key}")
            require_no_open_policy_flags(nested, f"{location}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            require_no_open_policy_flags(nested, f"{location}[{index}]")


def is_positive_finite_number(value: object) -> bool:
    if type(value) is int:
        return value > 0
    return type(value) is float and math.isfinite(value) and value > 0


def read_json_at(root_descriptor: int, relative_path: str) -> dict[str, Any]:
    try:
        descriptor = open_regular_at(root_descriptor, relative_path)
    except OSError as error:
        raise ResultValidationError(f"unsafe_or_missing_json:{relative_path}:{error}") from error
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        require(0 < metadata.st_size <= MAX_JSON_BYTES, f"json_size_invalid:{relative_path}")
        payload = stream.read(MAX_JSON_BYTES + 1)
    require(len(payload) == metadata.st_size, f"json_read_size_mismatch:{relative_path}")
    try:
        value = json.loads(payload.decode("utf-8", errors="strict"), object_pairs_hook=duplicate_rejecting_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ResultValidationError(f"invalid_json:{relative_path}:{error}") from error
    require(isinstance(value, dict), f"json_object_required:{relative_path}")
    return value


def expected_source_hashes() -> dict[str, str]:
    expected: dict[str, str] = {}
    for field, relative_path in SOURCE_PATHS.items():
        digest, size = sha256_path(REPO_ROOT / relative_path, require_nonempty=True)
        require(size > 0, f"local_hash_bound_source_empty:{relative_path}")
        expected[field] = digest
    return expected


def sha256_at(
    root_descriptor: int, relative_path: str, *, require_nonempty: bool
) -> tuple[str, int]:
    try:
        descriptor = open_regular_at(root_descriptor, relative_path)
    except OSError as error:
        raise ResultValidationError(f"unsafe_or_missing_result:{relative_path}:{error}") from error
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        require(
            not require_nonempty or metadata.st_size > 0,
            f"empty_result_file:{relative_path}",
        )
        return sha256_stream(stream), metadata.st_size


def verify_evidence(
    evidence: object,
    root_descriptor: int,
    expected_path: str,
    *,
    require_nonempty: bool,
) -> dict[str, object]:
    require(isinstance(evidence, dict), f"artifact_evidence_object_required:{expected_path}")
    require(set(evidence) == {"path", "sha256", "size_bytes"}, f"artifact_evidence_keys:{expected_path}")
    require(evidence.get("path") == expected_path, f"artifact_path_mismatch:{expected_path}")
    declared_hash = evidence.get("sha256")
    declared_size = evidence.get("size_bytes")
    require(
        isinstance(declared_hash, str) and SHA256_RE.fullmatch(declared_hash) is not None,
        f"artifact_sha256_invalid:{expected_path}",
    )
    require(
        type(declared_size) is int and declared_size >= (1 if require_nonempty else 0),
        f"artifact_size_invalid:{expected_path}",
    )
    digest, size = sha256_at(
        root_descriptor, expected_path, require_nonempty=require_nonempty
    )
    require(size == declared_size, f"artifact_size_mismatch:{expected_path}")
    require(digest == declared_hash, f"artifact_sha256_mismatch:{expected_path}")
    return {"path": expected_path, "sha256": digest, "size_bytes": size}


def validate_preflight(root_descriptor: int, source_hashes: dict[str, str]) -> None:
    report = read_json_at(root_descriptor, "preflight/cad.json")
    require_no_open_policy_flags(report, "cad_preflight")
    require(
        set(report)
        == {
            "schema_version",
            "phase",
            "runtime_phase",
            "status",
            "checks",
            "errors",
            "geometry_generated",
            "paid_instance_launched",
        },
        "cad_preflight_keys_mismatch",
    )
    require(report.get("schema_version") == "1.0.0", "cad_preflight_schema_mismatch")
    require(report.get("phase") == "F41", "cad_preflight_phase_mismatch")
    require(report.get("runtime_phase") == "cad", "cad_preflight_runtime_phase_mismatch")
    require(report.get("status") == "passed", "cad_preflight_status_mismatch")
    require(report.get("errors") == [], "cad_preflight_errors_not_empty")
    require(report.get("geometry_generated") is False, "cad_preflight_geometry_claim_open")
    require(report.get("paid_instance_launched") is False, "cad_preflight_paid_instance_claim_open")
    checks = report.get("checks")
    require(
        isinstance(checks, dict)
        and set(checks)
        == {
            "expected_image_ref",
            "reported_runtime_image_ref",
            "platform",
            "network_required_during_job",
            "F35_hash_bound_inputs",
            "build123d_version",
            "lib3mf_available",
        },
        "cad_preflight_check_schema_mismatch",
    )
    require(checks.get("expected_image_ref") == EXPECTED_RUNTIME_IMAGE, "cad_preflight_expected_image_mismatch")
    require(checks.get("reported_runtime_image_ref") == EXPECTED_RUNTIME_IMAGE, "cad_preflight_reported_image_mismatch")
    require(checks.get("platform") == "linux/amd64", "cad_preflight_platform_mismatch")
    require(checks.get("network_required_during_job") is False, "cad_preflight_offline_contract_mismatch")
    require(checks.get("build123d_version") == "0.11.1", "cad_preflight_build123d_version_mismatch")
    require(checks.get("lib3mf_available") is True, "cad_preflight_lib3mf_missing")
    hash_bound_inputs = checks.get("F35_hash_bound_inputs")
    require(
        isinstance(hash_bound_inputs, list) and len(hash_bound_inputs) == 3,
        "cad_preflight_hash_bound_inputs_mismatch",
    )
    expected_inputs = []
    for role, field in (
        ("contract", "source_contract_sha256"),
        ("generator", "source_generator_sha256"),
        ("math_module", "source_math_sha256"),
    ):
        expected_inputs.append(
            {
                "role": role,
                "path": SOURCE_PATHS[field],
                "sha256": source_hashes[field],
            }
        )
    require(hash_bound_inputs == expected_inputs, "cad_preflight_hash_bound_inputs_mismatch")


def validate_family_checks(checks: object, family: str) -> None:
    require(
        isinstance(checks, dict)
        and set(checks)
        == {
            "step_roundtrip",
            "3mf_roundtrip_shape_count",
            "3mf_roundtrip_solid_count",
        },
        f"cad_family_check_schema_mismatch:{family}",
    )
    require(
        type(checks.get("3mf_roundtrip_shape_count")) is int
        and checks["3mf_roundtrip_shape_count"] > 0,
        f"cad_family_3mf_shape_count_invalid:{family}",
    )
    require(
        type(checks.get("3mf_roundtrip_solid_count")) is int
        and checks["3mf_roundtrip_solid_count"] > 0,
        f"cad_family_3mf_solid_count_invalid:{family}",
    )
    step = checks.get("step_roundtrip")
    require(
        isinstance(step, dict)
        and set(step)
        == {
            "valid",
            "manifold",
            "solid_count",
            "all_solids_positive_volume",
            "volume_mm3",
            "bounds_size_mm",
        },
        f"cad_family_step_check_schema_mismatch:{family}",
    )
    require(step.get("valid") is True, f"cad_family_step_invalid:{family}")
    require(type(step.get("manifold")) is bool, f"cad_family_step_manifold_type_invalid:{family}")
    require(
        type(step.get("solid_count")) is int and step["solid_count"] > 0,
        f"cad_family_step_solid_count_invalid:{family}",
    )
    require(
        step.get("all_solids_positive_volume") is True,
        f"cad_family_step_nonpositive_solid:{family}",
    )
    volume = step.get("volume_mm3")
    require(
        is_positive_finite_number(volume),
        f"cad_family_step_volume_invalid:{family}",
    )
    bounds = step.get("bounds_size_mm")
    require(
        isinstance(bounds, list)
        and len(bounds) == 3
        and all(is_positive_finite_number(value) for value in bounds),
        f"cad_family_step_bounds_invalid:{family}",
    )


def validate_cad_report(root_descriptor: int) -> dict[str, object]:
    report = read_json_at(root_descriptor, "cad-execution-report.json")
    require_no_open_policy_flags(report, "cad_report")
    require(
        set(report)
        == {
            "schema_version",
            "phase",
            "runtime_phase",
            "status",
            "target_variant",
            "planned_family_count",
            "generateable_family_count",
            "generated_family_count",
            "blocked_family_count",
            "generated_format_counts",
            "family_reports",
            "source_generation_log",
            "release_gates",
            "paid_instance_launched",
        },
        "cad_report_keys_mismatch",
    )
    require(report.get("schema_version") == "1.0.0", "cad_report_schema_mismatch")
    require(report.get("phase") == "F41", "cad_report_phase_mismatch")
    require(report.get("runtime_phase") == "cad", "cad_report_runtime_phase_mismatch")
    require(report.get("status") == EXPECTED_STATUS, "cad_report_status_mismatch")
    require(report.get("target_variant") == "917_30_turbo_5374", "cad_report_variant_mismatch")
    require_exact_int(report.get("planned_family_count"), 138, "cad_report_planned_count_mismatch")
    require_exact_int(report.get("generateable_family_count"), 6, "cad_report_generateable_count_mismatch")
    require_exact_int(report.get("generated_family_count"), 6, "cad_report_generated_count_mismatch")
    require_exact_int(report.get("blocked_family_count"), 132, "cad_report_blocked_count_mismatch")
    format_counts = report.get("generated_format_counts")
    require(
        isinstance(format_counts, dict) and set(format_counts) == set(EXPECTED_FORMAT_COUNTS),
        "cad_report_format_counts_mismatch",
    )
    for output_format, expected_count in EXPECTED_FORMAT_COUNTS.items():
        require_exact_int(
            format_counts.get(output_format),
            expected_count,
            "cad_report_format_counts_mismatch",
        )
    require(report.get("paid_instance_launched") is False, "cad_report_paid_instance_claim_open")

    release_gates = report.get("release_gates")
    require(isinstance(release_gates, dict), "cad_report_release_gates_object_required")
    require(set(release_gates) == RELEASE_GATE_KEYS, "cad_report_release_gate_set_mismatch")
    require(all(value is False for value in release_gates.values()), "cad_report_release_gate_open")

    family_reports = report.get("family_reports")
    require(isinstance(family_reports, list) and len(family_reports) == 6, "cad_report_family_list_mismatch")
    by_family: dict[str, dict[str, Any]] = {}
    source_hashes = expected_source_hashes()
    artifacts: list[dict[str, object]] = []
    for family_report in family_reports:
        require(isinstance(family_report, dict), "cad_family_report_object_required")
        require(
            set(family_report)
            == {
                "family_id",
                "state",
                "source_seed",
                "source_contract_sha256",
                "source_generator_sha256",
                "source_math_sha256",
                "runtime_image_ref",
                "outputs",
                "checks",
                "manufacturing_released",
                "simulation_validated",
            },
            "cad_family_report_keys_mismatch",
        )
        family = family_report.get("family_id")
        require(isinstance(family, str) and family in FAMILIES, f"cad_family_id_invalid:{family!r}")
        require(family not in by_family, f"cad_family_id_duplicate:{family}")
        by_family[family] = family_report
        require(
            family_report.get("state") == "generated_research_seed_not_released",
            f"cad_family_state_mismatch:{family}",
        )
        require(family_report.get("source_seed") == "F35_rotating_917_30_turbo_5374", f"cad_family_seed_mismatch:{family}")
        require(family_report.get("runtime_image_ref") == EXPECTED_RUNTIME_IMAGE, f"cad_family_runtime_mismatch:{family}")
        for field, expected_hash in source_hashes.items():
            require(family_report.get(field) == expected_hash, f"cad_family_source_hash_mismatch:{family}:{field}")
        require(family_report.get("manufacturing_released") is False, f"cad_family_manufacturing_gate_open:{family}")
        require(family_report.get("simulation_validated") is False, f"cad_family_simulation_gate_open:{family}")
        validate_family_checks(family_report.get("checks"), family)
        outputs = family_report.get("outputs")
        require(isinstance(outputs, dict) and set(outputs) == set(FORMATS), f"cad_family_output_set_mismatch:{family}")
        for output_format in FORMATS:
            artifacts.append(
                verify_evidence(
                    outputs[output_format],
                    root_descriptor,
                    artifact_relative_path(family, output_format),
                    require_nonempty=True,
                )
            )
        sidecar = read_json_at(
            root_descriptor, f"artifacts/{family}/cad-family-report.json"
        )
        require(sidecar == family_report, f"cad_family_sidecar_mismatch:{family}")

    require(set(by_family) == set(FAMILIES), "cad_report_family_set_mismatch")
    log = verify_evidence(
        report.get("source_generation_log"),
        root_descriptor,
        "logs/f35-cad-seed.log",
        require_nonempty=True,
    )
    validate_preflight(root_descriptor, source_hashes)
    return {
        "artifact_count": len(artifacts),
        "artifact_bytes": sum(int(item["size_bytes"]) for item in artifacts),
        "source_generation_log": log,
        "family_ids": sorted(by_family),
    }


def validate_and_extract(archive: Path, expected_sha256: str, job_id: str, output: Path) -> dict[str, object]:
    require(JOB_ID_RE.fullmatch(job_id) is not None and job_id not in (".", ".."), "job_id_invalid")
    require(SHA256_RE.fullmatch(expected_sha256) is not None, "expected_archive_sha256_invalid")
    require(archive.name.endswith(".tar.gz"), "archive_suffix_must_be_tar_gz")
    require(hasattr(os, "O_NOFOLLOW"), "O_NOFOLLOW_unavailable")
    output = Path(os.path.abspath(output))
    require(output.name not in ("", ".", ".."), "extraction_output_name_invalid")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
    try:
        archive_descriptor = os.open(archive, flags)
    except OSError as error:
        raise ResultValidationError(f"archive_absent_or_unsafe:{error}") from error

    try:
        parent_descriptor = os.open(output.parent, directory_open_flags())
    except OSError as error:
        os.close(archive_descriptor)
        raise ResultValidationError(f"extraction_output_parent_unsafe:{error}") from error

    staging_name: str | None = None
    staging_descriptor = -1
    payload_descriptor = -1
    tar_descriptor = -1
    job_root_descriptor = -1
    try:
        require_destination_absent(parent_descriptor, output.name)
        with os.fdopen(archive_descriptor, "rb") as archive_stream:
            archive_descriptor = -1
            before = os.fstat(archive_stream.fileno())
            require(stat.S_ISREG(before.st_mode), "archive_not_regular")
            require(
                0 < before.st_size <= MAX_COMPRESSED_BYTES,
                "archive_compressed_size_invalid",
            )
            require(sha256_stream(archive_stream) == expected_sha256, "archive_sha256_mismatch")
            archive_stream.seek(0)

            staging_name, staging_descriptor, payload_descriptor = create_private_staging(
                parent_descriptor, output.name
            )
            tar_descriptor, decompressed_tar_bytes = decompress_gzip_to_tar(
                archive_stream, staging_descriptor
            )

            require(
                stable_file_identity(before)
                == stable_file_identity(os.fstat(archive_stream.fileno())),
                "archive_changed_during_validation",
            )
            archive_stream.seek(0)
            require(
                sha256_stream(archive_stream) == expected_sha256,
                "archive_changed_during_validation",
            )

            try:
                with os.fdopen(os.dup(tar_descriptor), "rb") as tar_stream, tarfile.open(
                    fileobj=tar_stream, mode="r:"
                ) as handle:
                    archive_members: list[tarfile.TarInfo] = []
                    for index, member in enumerate(handle):
                        require(index < MAX_MEMBER_COUNT, "archive_member_limit_exceeded")
                        archive_members.append(member)
                    members = validate_archive_members(archive_members, job_id)
                    copied_total = extract_members(handle, members, payload_descriptor)
            except (tarfile.TarError, EOFError, OSError) as error:
                raise ResultValidationError(f"archive_invalid:{error}") from error

            require(
                stable_file_identity(before)
                == stable_file_identity(os.fstat(archive_stream.fileno())),
                "archive_changed_during_validation",
            )
            archive_stream.seek(0)
            require(
                sha256_stream(archive_stream) == expected_sha256,
                "archive_changed_during_validation",
            )

        os.close(tar_descriptor)
        tar_descriptor = -1
        os.unlink("archive.tar", dir_fd=staging_descriptor)
        require(os.listdir(payload_descriptor) == [job_id], "extracted_root_mismatch")
        job_root_descriptor = os.open(
            job_id, directory_open_flags(), dir_fd=payload_descriptor
        )
        evidence = validate_cad_report(job_root_descriptor)

        result = {
            "schema_version": "1.0.0",
            "phase": "F41",
            "status": "passed_cad_results_archive_integrity_verified_not_released",
            "job_id": job_id,
            "archive_path": os.path.abspath(archive),
            "archive_sha256": expected_sha256,
            "archive_size_bytes": before.st_size,
            "decompressed_tar_bytes": decompressed_tar_bytes,
            "expanded_file_bytes": copied_total,
            "extracted_root": str(output / job_id),
            "planned_family_count": 138,
            "generateable_family_count": 6,
            "generated_family_count": 6,
            "blocked_family_count": 132,
            "generated_format_counts": EXPECTED_FORMAT_COUNTS,
            "verified_artifact_count": evidence["artifact_count"],
            "verified_artifact_bytes": evidence["artifact_bytes"],
            "source_generation_log_verified": True,
            "family_ids": evidence["family_ids"],
            "geometry_semantics_validated": False,
            "physical_validation_complete": False,
            "simulation_validated": False,
            "manufacturing_released": False,
            "release_gates_all_false": True,
            "git_modified": False,
        }

        os.close(job_root_descriptor)
        job_root_descriptor = -1
        os.close(payload_descriptor)
        payload_descriptor = -1
        require_destination_absent(parent_descriptor, output.name)
        atomic_rename_noreplace(
            staging_descriptor,
            "payload",
            parent_descriptor,
            output.name,
        )
        return result
    finally:
        if archive_descriptor >= 0:
            os.close(archive_descriptor)
        if job_root_descriptor >= 0:
            os.close(job_root_descriptor)
        if payload_descriptor >= 0:
            os.close(payload_descriptor)
        if tar_descriptor >= 0:
            os.close(tar_descriptor)
        if staging_descriptor >= 0:
            try:
                cleanup_private_staging(
                    parent_descriptor, staging_name, staging_descriptor
                )
            except OSError:
                # Preserve the primary validation error.  The private staging
                # directory is never the requested final output.
                pass
        os.close(parent_descriptor)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        report = validate_and_extract(
            arguments.archive,
            arguments.expected_sha256,
            arguments.job_id,
            arguments.output,
        )
    except ResultValidationError as error:
        print(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "phase": "F41",
                    "status": "blocked",
                    "error": str(error),
                    "geometry_semantics_validated": False,
                    "physical_validation_complete": False,
                    "simulation_validated": False,
                    "manufacturing_released": False,
                    "git_modified": False,
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
