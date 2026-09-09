#!/usr/bin/env python3
"""Matérialise une allowlist depuis les blobs d'un commit Git exact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Sequence


APPROVED_GIT = Path("/usr/bin/git")
DEFAULT_WORKFLOW_PROFILE = "f42b-six-usd-v1"
ALLOWED_GIT_MODES = {"100644": 0o600, "100755": 0o700}
FULL_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
SAFE_COMPONENT = re.compile(r"[A-Za-z0-9._+@-]+")
MAX_RELATIVE_PATH_BYTES = 1024
MAX_BLOB_BYTES = 64 * 1024 * 1024


class SnapshotError(RuntimeError):
    """Le snapshot demandé ne respecte pas le contrat fermé."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SnapshotError(message)


def _approved_git() -> Path:
    """Retourne l'unique binaire Git approuvé après contrôle local."""

    _require(APPROVED_GIT.is_absolute(), "binaire Git approuvé non absolu")
    try:
        info = APPROVED_GIT.lstat()
    except OSError as error:
        raise SnapshotError("binaire Git approuvé inaccessible") from error
    _require(stat.S_ISREG(info.st_mode), "binaire Git approuvé non régulier")
    _require(info.st_uid == 0, "binaire Git approuvé non possédé par root")
    _require(info.st_mode & 0o022 == 0, "binaire Git approuvé modifiable par groupe/autres")
    _require(info.st_mode & 0o111 != 0, "binaire Git approuvé non exécutable")
    return APPROVED_GIT


def _git_environment() -> dict[str, str]:
    """Conserve l'environnement non-Git sans accepter de redirection GIT_* ."""

    return {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("GIT_")
    }


def _git(repository: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        [
            str(_approved_git()),
            "--no-replace-objects",
            "--literal-pathspecs",
            "-C",
            str(repository),
            *arguments,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        env=_git_environment(),
    )
    if result.returncode != 0:
        raise SnapshotError("lecture de l'objet Git refusée")
    return result.stdout


def _repository(path: Path) -> Path:
    try:
        repository = path.resolve(strict=True)
    except OSError as error:
        raise SnapshotError("dépôt Git inaccessible") from error
    _require(repository.is_dir(), "racine du dépôt Git invalide")
    inside = _git(repository, "rev-parse", "--is-inside-work-tree").decode(
        "ascii", errors="strict"
    ).strip()
    _require(inside == "true", "racine hors d'une worktree Git")
    top = _git(repository, "rev-parse", "--show-toplevel").decode(
        "utf-8", errors="strict"
    ).strip()
    try:
        top_level = Path(top).resolve(strict=True)
    except OSError as error:
        raise SnapshotError("racine Git canonique inaccessible") from error
    _require(top_level == repository, "--repository doit désigner la racine Git exacte")
    return repository


def _validate_revision(repository: Path, revision: str) -> int:
    _require(FULL_OBJECT_ID.fullmatch(revision) is not None, "révision hex complète requise")
    object_format = _git(repository, "rev-parse", "--show-object-format").decode(
        "ascii", errors="strict"
    ).strip()
    lengths = {"sha1": 40, "sha256": 64}
    _require(object_format in lengths, "format d'objet Git non approuvé")
    _require(len(revision) == lengths[object_format], "longueur de révision Git incorrecte")
    object_type = _git(repository, "cat-file", "-t", revision).decode(
        "ascii", errors="strict"
    ).strip()
    _require(object_type == "commit", "la révision exacte doit être un commit")
    return lengths[object_format]


def _validate_paths(paths: Sequence[str]) -> list[str]:
    _require(bool(paths), "allowlist Git vide")
    validated: list[str] = []
    exact: set[str] = set()
    folded_prefixes: dict[str, str] = {}
    for relative in paths:
        _require(bool(relative) and relative.isascii(), "chemin Git vide ou non ASCII")
        _require(
            len(relative.encode("ascii")) <= MAX_RELATIVE_PATH_BYTES,
            "chemin Git trop long",
        )
        _require(not relative.startswith("/") and "\\" not in relative, "chemin Git non relatif")
        components = relative.split("/")
        _require(
            all(
                component not in ("", ".", "..")
                and component.casefold() != ".git"
                and len(component.encode("ascii")) <= 255
                and SAFE_COMPONENT.fullmatch(component) is not None
                for component in components
            ),
            "chemin Git ambigu ou non sûr",
        )
        _require(relative not in exact, "chemin Git dupliqué")
        exact.add(relative)
        prefix_components: list[str] = []
        for component in components:
            prefix_components.append(component)
            prefix = "/".join(prefix_components)
            folded = prefix.casefold()
            previous = folded_prefixes.setdefault(folded, prefix)
            _require(previous == prefix, "collision de casse dans l'allowlist Git")
        validated.append(relative)
    return validated


def _tree_entry(repository: Path, revision: str, relative: str, oid_length: int) -> dict[str, str]:
    output = _git(
        repository,
        "ls-tree",
        "-z",
        "--full-tree",
        revision,
        "--",
        relative,
    )
    records = output.split(b"\0")
    _require(len(records) == 2 and records[1] == b"" and bool(records[0]), f"source Git absente: {relative}")
    try:
        header, raw_path = records[0].split(b"\t", 1)
        mode, object_type, raw_oid = header.split(b" ", 2)
        returned_path = raw_path.decode("ascii", errors="strict")
        git_mode = mode.decode("ascii", errors="strict")
        entry_type = object_type.decode("ascii", errors="strict")
        oid = raw_oid.decode("ascii", errors="strict")
    except (UnicodeDecodeError, ValueError) as error:
        raise SnapshotError(f"entrée Git illisible: {relative}") from error
    _require(returned_path == relative, f"source Git non exacte: {relative}")
    _require(entry_type == "blob" and git_mode in ALLOWED_GIT_MODES, f"mode Git interdit: {relative}")
    _require(
        len(oid) == oid_length and FULL_OBJECT_ID.fullmatch(oid) is not None,
        f"identifiant de blob Git invalide: {relative}",
    )
    raw_size = _git(repository, "cat-file", "-s", oid).decode("ascii", errors="strict").strip()
    _require(raw_size.isdigit(), f"taille de blob Git invalide: {relative}")
    size = int(raw_size)
    _require(size <= MAX_BLOB_BYTES, f"blob Git trop volumineux: {relative}")
    return {
        "path": relative,
        "git_blob": oid,
        "git_mode": git_mode,
        "expected_size": str(size),
    }


def _canonical_new_file(path: Path, label: str) -> Path:
    _require(path.is_absolute(), f"{label} absolu requis")
    _require(path.name not in ("", ".", ".."), f"{label} invalide")
    try:
        parent = path.parent.resolve(strict=True)
    except OSError as error:
        raise SnapshotError(f"parent de {label} inaccessible") from error
    _require(parent.is_dir(), f"parent de {label} non répertoire")
    canonical = parent / path.name
    try:
        canonical.lstat()
    except FileNotFoundError:
        return canonical
    except OSError as error:
        raise SnapshotError(f"{label} inaccessible") from error
    raise SnapshotError(f"{label} existe déjà ou est un symlink")


def _open_new_destination(path: Path) -> tuple[Path, int]:
    destination = _canonical_new_file(path, "destination")
    parent_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    parent_descriptor = os.open(destination.parent, parent_flags)
    try:
        try:
            os.mkdir(destination.name, 0o700, dir_fd=parent_descriptor)
        except FileExistsError as error:
            raise SnapshotError("destination existante ou symlink interdite") from error
        descriptor = os.open(destination.name, parent_flags, dir_fd=parent_descriptor)
    finally:
        os.close(parent_descriptor)
    os.fchmod(descriptor, 0o700)
    info = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        os.close(descriptor)
        raise SnapshotError("destination privée 0700 non garantie")
    return destination, descriptor


def _open_private_directory(root_descriptor: int, components: Sequence[str]) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.dup(root_descriptor)
    try:
        for component in components:
            try:
                os.mkdir(component, 0o700, dir_fd=descriptor)
                created = True
            except FileExistsError:
                created = False
            child = os.open(component, flags, dir_fd=descriptor)
            if created:
                os.fchmod(child, 0o700)
            info = os.fstat(child)
            _require(
                stat.S_ISDIR(info.st_mode)
                and info.st_uid == os.getuid()
                and stat.S_IMODE(info.st_mode) == 0o700,
                "répertoire de destination non privé ou non sûr",
            )
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _write_all(descriptor: int, data: bytes, digest: "hashlib._Hash") -> int:
    offset = 0
    while offset < len(data):
        written = os.write(descriptor, data[offset:])
        _require(written > 0, "écriture du snapshot Git interrompue")
        digest.update(data[offset : offset + written])
        offset += written
    return offset


def _stage_blob(
    repository: Path,
    root_descriptor: int,
    entry: dict[str, str],
) -> dict[str, object]:
    data = _git(repository, "cat-file", "blob", entry["git_blob"])
    expected_size = int(entry["expected_size"])
    _require(len(data) == expected_size, f"taille du blob Git incohérente: {entry['path']}")
    components = entry["path"].split("/")
    parent_descriptor = _open_private_directory(root_descriptor, components[:-1])
    staged_mode = ALLOWED_GIT_MODES[entry["git_mode"]]
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = -1
    try:
        descriptor = os.open(components[-1], flags, staged_mode, dir_fd=parent_descriptor)
        os.fchmod(descriptor, staged_mode)
        digest = hashlib.sha256()
        size = _write_all(descriptor, data, digest)
        os.fsync(descriptor)
        info = os.fstat(descriptor)
        _require(
            stat.S_ISREG(info.st_mode)
            and info.st_uid == os.getuid()
            and stat.S_IMODE(info.st_mode) == staged_mode
            and info.st_size == size,
            f"fichier stagé non sûr: {entry['path']}",
        )
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_descriptor)
    return {
        "path": entry["path"],
        "git_blob": entry["git_blob"],
        "git_mode": entry["git_mode"],
        "staged_mode": f"{staged_mode:04o}",
        "size_bytes": size,
        "sha256": digest.hexdigest(),
    }


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    canonical = _canonical_new_file(path, "manifeste")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    parent_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    parent_descriptor = os.open(canonical.parent, parent_flags)
    descriptor = -1
    try:
        descriptor = os.open(canonical.name, flags, 0o600, dir_fd=parent_descriptor)
        os.fchmod(descriptor, 0o600)
        digest = hashlib.sha256()
        written = _write_all(descriptor, data, digest)
        os.fsync(descriptor)
        info = os.fstat(descriptor)
        _require(
            stat.S_ISREG(info.st_mode)
            and info.st_uid == os.getuid()
            and stat.S_IMODE(info.st_mode) == 0o600
            and info.st_size == written,
            "manifeste JSON non sûr",
        )
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_descriptor)


def materialize(
    repository: Path,
    revision: str,
    destination: Path,
    manifest: Path,
    paths: Sequence[str],
    *,
    workflow_profile: str = DEFAULT_WORKFLOW_PROFILE,
) -> dict[str, object]:
    """Crée un arbre privé depuis les seuls blobs du commit indiqué."""

    _require(
        re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", workflow_profile) is not None,
        "profil de workflow invalide",
    )
    source = _repository(repository)
    oid_length = _validate_revision(source, revision)
    relative_paths = _validate_paths(paths)
    entries = [
        _tree_entry(source, revision, relative, oid_length)
        for relative in relative_paths
    ]
    manifest_path = _canonical_new_file(manifest, "manifeste")
    destination_path = _canonical_new_file(destination, "destination")
    _require(
        manifest_path != destination_path
        and not manifest_path.is_relative_to(destination_path),
        "manifeste interdit dans l'arbre matérialisé",
    )
    destination_path, root_descriptor = _open_new_destination(destination_path)
    try:
        staged = [_stage_blob(source, root_descriptor, entry) for entry in entries]
        os.fsync(root_descriptor)
    finally:
        os.close(root_descriptor)
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "workflow_profile": workflow_profile,
        "source_policy": "exact commit blobs; mutable worktree and inherited GIT_* ignored",
        "source_revision": revision,
        "git_binary": str(APPROVED_GIT),
        "file_count": len(staged),
        "total_size_bytes": sum(int(entry["size_bytes"]) for entry in staged),
        "files": staged,
    }
    _write_manifest(manifest_path, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Matérialise une allowlist depuis un commit Git exact."
    )
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--workflow-profile",
        default=DEFAULT_WORKFLOW_PROFILE,
    )
    parser.add_argument("paths", nargs="+")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        materialize(
            arguments.repository,
            arguments.revision,
            arguments.destination,
            arguments.manifest,
            arguments.paths,
            workflow_profile=arguments.workflow_profile,
        )
    except (OSError, SnapshotError, UnicodeError) as error:
        print(f"snapshot Git refusé: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
