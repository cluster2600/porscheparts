#!/usr/bin/env python3
"""Valide puis extrait une archive publique dans un espace solveur borne."""

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


INBOX = Path("/workspace/inbox")
JOBS = Path("/workspace/jobs")
SOLVER_UID = 9139
SOLVER_GID = 9139
JOB_ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
MAX_ARCHIVE_BYTES = 2 * 1024**3
MAX_MEMBER_COUNT = 100_000
MAX_EXPANDED_BYTES = 20 * 1024**3
MAX_SINGLE_FILE_BYTES = 4 * 1024**3


class StagingError(RuntimeError):
    """Archive ou destination hors contrat."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise StagingError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_members(members: list[tarfile.TarInfo]) -> int:
    require(len(members) <= MAX_MEMBER_COUNT, "archive_member_limit_exceeded")
    names: set[str] = set()
    expanded_bytes = 0
    for member in members:
        raw_name = member.name
        require(bool(raw_name), "archive_member_name_empty")
        require("\\" not in raw_name, "archive_member_backslash_rejected")
        path = PurePosixPath(raw_name)
        require(not path.is_absolute(), "archive_absolute_path_rejected")
        require(".." not in path.parts, "archive_parent_path_rejected")
        normalized = path.as_posix()
        require(normalized not in ("", "."), "archive_member_name_invalid")
        require(normalized not in names, "archive_duplicate_member_rejected")
        names.add(normalized)
        require(member.isdir() or member.isreg(), "archive_special_member_rejected")
        if member.isreg():
            require(member.size >= 0, "archive_negative_member_size")
            require(member.size <= MAX_SINGLE_FILE_BYTES, "archive_file_limit_exceeded")
            expanded_bytes += member.size
            require(expanded_bytes <= MAX_EXPANDED_BYTES, "archive_expanded_limit_exceeded")
    return expanded_bytes


def sanitize_tree(root: Path) -> None:
    for current, directories, files in os.walk(root, topdown=False, followlinks=False):
        current_path = Path(current)
        for name in files:
            path = current_path / name
            require(not path.is_symlink(), "extracted_symlink_rejected")
            mode = path.stat().st_mode
            os.chmod(path, 0o750 if mode & 0o111 else 0o640)
            os.chown(path, SOLVER_UID, SOLVER_GID)
        for name in directories:
            path = current_path / name
            require(not path.is_symlink(), "extracted_symlink_rejected")
            os.chmod(path, 0o750)
            os.chown(path, SOLVER_UID, SOLVER_GID)
        os.chmod(current_path, 0o750)
        os.chown(current_path, SOLVER_UID, SOLVER_GID)


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
            expanded_bytes = validate_members(members)
            handle.extractall(temporary, members=members, filter="data")
        sanitize_tree(temporary)
        temporary.rename(target)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return {
        "schema_version": "1.0.0",
        "status": "archive_staged_solver_execution_not_started",
        "job_id": job_id,
        "archive_sha256": sha256_file(archive),
        "archive_bytes": archive.stat().st_size,
        "member_count": len(members),
        "expanded_regular_file_bytes": expanded_bytes,
        "target": str(target),
        "target_uid": target.stat().st_uid,
        "target_gid": target.stat().st_gid,
        "solver_started": False,
        "physical_claims_validated": False,
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
