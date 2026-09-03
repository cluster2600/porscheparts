#!/usr/bin/env python3
"""Prépare une destination privée F42b hors de toute worktree Git."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile


MAX_ARCHIVE_BYTES = 4 * 1024**3
MAX_ARCHIVE_MEMBERS = 4096
MAX_ARCHIVE_CONTENT_BYTES = 12 * 1024**3
MAX_ARCHIVE_FILE_BYTES = 2 * 1024**3
MAX_ARCHIVE_PATH_BYTES = 1024


class DestinationError(RuntimeError):
    """La destination ne respecte pas la frontière privée F42b."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DestinationError(message)


def _inside_git_worktree(path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def prepare_destination(destination: Path, repository_root: Path) -> Path:
    """Crée au plus un répertoire privé, puis retourne son chemin canonique."""

    _require(destination.is_absolute(), "destination F42b explicitement absolue requise")
    repository = repository_root.resolve(strict=True)
    _require(repository.is_dir(), "racine du dépôt invalide")

    try:
        destination_info = destination.lstat()
    except FileNotFoundError:
        destination_info = None

    if destination_info is None:
        parent = destination.parent.resolve(strict=True)
        _require(parent.is_dir(), "parent de destination F42b absent")
        prospective = parent / destination.name
        _require(
            prospective != repository and not prospective.is_relative_to(repository),
            "destination F42b interdite dans le dépôt ou sa worktree",
        )
        _require(
            not _inside_git_worktree(parent),
            "destination F42b interdite dans toute worktree Git",
        )
        try:
            os.mkdir(prospective, 0o700)
        except FileExistsError as exc:
            raise DestinationError("course détectée à la création de la destination F42b") from exc
        destination = prospective
    else:
        _require(not stat.S_ISLNK(destination_info.st_mode), "destination F42b symlink interdite")
        _require(stat.S_ISDIR(destination_info.st_mode), "destination F42b doit être un répertoire")
        destination = destination.resolve(strict=True)

    info = destination.lstat()
    _require(not stat.S_ISLNK(info.st_mode) and stat.S_ISDIR(info.st_mode), "destination F42b non sûre")
    _require(info.st_uid == os.getuid(), "destination F42b doit appartenir à l'utilisateur courant")
    _require(stat.S_IMODE(info.st_mode) == 0o700, "destination F42b doit être en mode 0700")
    _require(
        destination != repository and not destination.is_relative_to(repository),
        "destination F42b interdite dans le dépôt ou sa worktree",
    )
    _require(
        not _inside_git_worktree(destination),
        "destination F42b interdite dans toute worktree Git",
    )
    return destination


def copy_stdin_exclusive(path: Path, max_bytes: int = MAX_ARCHIVE_BYTES) -> None:
    """Écrit stdin dans un nouveau fichier régulier sans suivre de symlink."""

    _require(path.is_absolute(), "chemin partiel absolu requis")
    parent = path.parent.resolve(strict=True)
    info = parent.lstat()
    _require(not stat.S_ISLNK(info.st_mode) and stat.S_ISDIR(info.st_mode), "parent partiel non sûr")
    _require(info.st_uid == os.getuid(), "parent partiel non possédé")
    _require(stat.S_IMODE(info.st_mode) == 0o700, "parent partiel doit être en mode 0700")
    _require(path.parent == parent, "parent partiel doit être un chemin canonique")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            copied = 0
            while True:
                chunk = sys.stdin.buffer.read(1024 * 1024)
                if not chunk:
                    break
                copied += len(chunk)
                _require(copied <= max_bytes, "archive F42b comprimée supérieure à la limite")
                handle.write(chunk)
            _require(copied > 0, "archive F42b vide")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def _member_path(member: tarfile.TarInfo, job_id: str) -> tuple[Path, str]:
    name = member.name[:-1] if member.isdir() and member.name.endswith("/") else member.name
    _require(bool(name) and name.isascii(), "nom de membre d'archive vide ou non ASCII")
    _require(
        "\\" not in name
        and all(ord(character) >= 32 and ord(character) != 127 for character in name),
        "nom de membre d'archive ambigu",
    )
    parts = name.split("/")
    _require(all(part not in ("", ".", "..") for part in parts), "chemin d'archive ambigu")
    _require(
        parts[0] == job_id
        and len(name.encode("ascii")) <= MAX_ARCHIVE_PATH_BYTES
        and all(len(part.encode("ascii")) <= 255 for part in parts),
        "membre d'archive hors du job ou trop long",
    )
    return Path(*parts), name


def extract_verified_archive(archive: Path, destination: Path, job_id: str) -> Path:
    """Valide les bornes et extrait sans liens, fichiers spéciaux ni écrasement."""

    _require(archive.is_absolute() and destination.is_absolute(), "chemins d'archive absolus requis")
    archive_info = archive.lstat()
    _require(not stat.S_ISLNK(archive_info.st_mode) and stat.S_ISREG(archive_info.st_mode), "archive F42b non régulière")
    _require(0 < archive_info.st_size <= MAX_ARCHIVE_BYTES, "taille d'archive F42b interdite")
    root = destination / job_id
    _require(not root.exists() and not root.is_symlink(), "répertoire extrait déjà présent")
    members: list[tuple[tarfile.TarInfo, Path]] = []
    names: set[str] = set()
    folded: dict[str, str] = {}
    total = 0
    try:
        with tarfile.open(archive, "r:gz") as handle:
            for index, member in enumerate(handle):
                _require(index < MAX_ARCHIVE_MEMBERS, "archive F42b avec trop de membres")
                relative, exact_name = _member_path(member, job_id)
                _require(
                    not member.issym()
                    and not member.islnk()
                    and (member.isfile() or member.isdir()),
                    "type de membre d'archive F42b interdit",
                )
                _require(member.size >= 0 and (not member.isdir() or member.size == 0), "taille de membre invalide")
                _require(not member.isfile() or member.size <= MAX_ARCHIVE_FILE_BYTES, "fichier d'archive trop volumineux")
                total += member.size if member.isfile() else 0
                _require(total <= MAX_ARCHIVE_CONTENT_BYTES, "contenu décompressé F42b supérieur à la limite")
                folded_name = exact_name.casefold()
                _require(exact_name not in names and folded_name not in folded, "membre d'archive dupliqué ou ambigu")
                names.add(exact_name)
                folded[folded_name] = exact_name
                members.append((member, relative))
            _require(bool(members), "archive F42b vide")
            _require({relative.parts[0] for _, relative in members} == {job_id}, "racine d'archive F42b inattendue")
            for member, relative in sorted(members, key=lambda item: (len(item[1].parts), str(item[1]))):
                target = destination / relative
                _require(target.resolve(strict=False).is_relative_to(destination), "cible d'extraction hors destination")
                if member.isdir():
                    target.mkdir(mode=0o700, parents=True, exist_ok=True)
                    _require(target.is_dir() and not target.is_symlink(), "collision d'extraction F42b")
                    continue
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                source = handle.extractfile(member)
                _require(source is not None, "contenu de membre d'archive absent")
                copied = 0
                with source, target.open("xb") as output:
                    os.chmod(target, 0o600)
                    while True:
                        chunk = source.read(1024 * 1024)
                        if not chunk:
                            break
                        copied += len(chunk)
                        _require(copied <= member.size, "taille extraite incohérente")
                        output.write(chunk)
                _require(copied == member.size, "taille extraite incohérente")
    except BaseException:
        if root.exists() and root.is_dir() and not root.is_symlink():
            shutil.rmtree(root)
        raise
    _require(root.is_dir() and not root.is_symlink(), "racine extraite F42b absente")
    return root


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--destination", required=True, type=Path)
    prepare.add_argument("--repository-root", required=True, type=Path)
    copy = subparsers.add_parser("copy-stdin-exclusive")
    copy.add_argument("--path", required=True, type=Path)
    copy.add_argument("--max-bytes", type=int, default=MAX_ARCHIVE_BYTES)
    extract = subparsers.add_parser("extract-archive")
    extract.add_argument("--archive", required=True, type=Path)
    extract.add_argument("--destination", required=True, type=Path)
    extract.add_argument("--job-id", required=True)
    args = parser.parse_args()

    try:
        if args.command == "prepare":
            print(prepare_destination(args.destination, args.repository_root))
        elif args.command == "copy-stdin-exclusive":
            copy_stdin_exclusive(args.path, args.max_bytes)
        else:
            print(extract_verified_archive(args.archive, args.destination, args.job_id))
    except (DestinationError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
