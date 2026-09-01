#!/usr/bin/env python3
"""Crée et vérifie un manifeste déterministe du skill et des prompts transférés."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_tree(root: Path) -> list[dict]:
    root_info = root.lstat()
    if not stat.S_ISDIR(root_info.st_mode) or stat.S_ISLNK(root_info.st_mode):
        raise RuntimeError("la racine du skill doit être un répertoire réel")
    root = root.resolve(strict=True)
    entries: list[dict] = []

    def visit(directory: Path) -> None:
        with os.scandir(directory) as iterator:
            children = sorted(iterator, key=lambda entry: entry.name.encode("utf-8"))
        for child in children:
            path = Path(child.path)
            info = path.lstat()
            relative = path.relative_to(root).as_posix()
            if stat.S_ISLNK(info.st_mode):
                raise RuntimeError(f"lien symbolique interdit dans le skill: {relative}")
            if stat.S_ISDIR(info.st_mode):
                entries.append({"path": relative, "type": "directory"})
                visit(path)
            elif stat.S_ISREG(info.st_mode):
                entries.append(
                    {
                        "path": relative,
                        "type": "file",
                        "size": info.st_size,
                        "sha256": sha256_file(path),
                    }
                )
            else:
                raise RuntimeError(f"fichier spécial interdit dans le skill: {relative}")

    visit(root)
    if not entries or not (root / "SKILL.md").is_file():
        raise RuntimeError("skill vide ou SKILL.md absent")
    return entries


def tree_sha256(entries: list[dict]) -> str:
    canonical = json.dumps(entries, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
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


def create_skill_manifest(root: Path, output: Path) -> dict:
    entries = scan_tree(root)
    payload = {
        "schema_version": "1.0.0",
        "skill_name": "omniverse-cad-to-simready",
        "entries": entries,
        "tree_sha256": tree_sha256(entries),
    }
    atomic_json(output.resolve(), payload)
    return payload


def verify_bundle(job_root: Path, control_path: Path) -> None:
    job_root = job_root.resolve(strict=True)
    control_path = control_path.resolve(strict=True)
    if control_path.parent.parent != job_root:
        raise RuntimeError("contrat de contrôle hors du job")
    control = json.loads(control_path.read_text(encoding="utf-8"))
    manifest_path = (control_path.parent / str(control.get("skill_manifest_report", ""))).resolve()
    if manifest_path.parent != control_path.parent or not manifest_path.is_file():
        raise RuntimeError("manifeste du skill absent ou hors contrôle")
    if sha256_file(manifest_path) != control.get("skill_manifest_sha256"):
        raise RuntimeError("checksum du manifeste skill différent")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "1.0.0" or manifest.get("skill_name") != "omniverse-cad-to-simready":
        raise RuntimeError("manifeste du skill invalide")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or manifest.get("tree_sha256") != tree_sha256(entries):
        raise RuntimeError("hash déterministe du manifeste skill invalide")
    if manifest.get("tree_sha256") != control.get("skill_tree_sha256"):
        raise RuntimeError("hash du skill différent du contrat")
    skill_root = job_root / "vendor" / "omniverse-cad-to-simready"
    actual_entries = scan_tree(skill_root)
    if actual_entries != entries or tree_sha256(actual_entries) != manifest["tree_sha256"]:
        raise RuntimeError("arbre du skill transféré différent du manifeste")

    prompts = control.get("input_prompts")
    if not isinstance(prompts, dict) or set(prompts) != {"material", "physics"}:
        raise RuntimeError("contrat des prompts incomplet")
    expected_names = {"material": "material-prompt.txt", "physics": "physics-prompt.txt"}
    for name, filename in expected_names.items():
        metadata = prompts.get(name)
        path = job_root / "inputs" / filename
        if not isinstance(metadata, dict) or metadata.get("filename") != filename:
            raise RuntimeError(f"métadonnées du prompt {name} invalides")
        try:
            info = path.lstat()
        except FileNotFoundError as exc:
            raise RuntimeError(f"prompt {name} absent") from exc
        if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"prompt {name} doit être un fichier régulier")
        if info.st_size != metadata.get("size") or sha256_file(path) != metadata.get("sha256"):
            raise RuntimeError(f"prompt {name} différent du contrat")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create-skill")
    create.add_argument("--root", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--job-root", type=Path, required=True)
    verify.add_argument("--control", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "create-skill":
        payload = create_skill_manifest(args.root, args.output)
        print(payload["tree_sha256"])
    else:
        verify_bundle(args.job_root, args.control)
        print("bundle transféré vérifié")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
