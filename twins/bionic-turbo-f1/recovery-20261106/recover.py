"""Verify and recover the selected turbo archives without executing their contents."""

import argparse
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "benchmarks/free-tools"))
from ft_common import load, new_directory, sha256, source_path, verify_inputs
from storage import private_root


def verify(path, entry):
    if path.is_symlink() or not path.is_file() or path.stat().st_size != entry["bytes"] or sha256(path) != entry["sha256"]:
        raise ValueError(f"size or digest mismatch: {path.name}")


def package(identifier):
    selected = next(p for p in load(HERE / "packages.json")["packages"] if p["id"] == identifier)
    source = source_path(ROOT, selected["source_directory"] + "/archive-receipt.json").parent
    for name, digest in selected["source_sha256"].items():
        if sha256(source_path(source, name)) != digest:
            raise ValueError("stale source manifest")
    receipt = load(source / "archive-receipt.json")
    if sha256(source / "file-manifest.json") != receipt["manifest_sha256"]:
        raise ValueError("file manifest does not match archive receipt")
    for key in ("bytes", "sha256"):
        if selected["archive"][key] != receipt["archive_" + key]:
            raise ValueError("archive descriptor differs from historical receipt")
    if "parts-manifest.json" in selected["source_sha256"]:
        original = load(source / "parts-manifest.json")
        observed = [{k: part[k] for k in ("name", "bytes", "sha256")} for part in selected["parts"]]
        if observed != original["parts"] or selected["archive"]["name"] != original["archive"]:
            raise ValueError("split order or identity differs from historical manifest")
    elif len(selected["parts"]) != 1 or any(selected["parts"][0][k] != selected["archive"][k] for k in ("name", "bytes", "sha256")):
        raise ValueError("single archive descriptor mismatch")
    entries = load(source / "file-manifest.json")["files"]
    entries.append({"path": "file-manifest.json", "bytes": (source / "file-manifest.json").stat().st_size, "sha256": receipt["manifest_sha256"]})
    return selected, entries


def reconstruct(selected, parts_root, destination):
    destination = Path(destination)
    private_root(destination.parent)
    parts = []
    for entry in selected["parts"]:
        part = source_path(parts_root, entry["name"])
        verify(part, entry)
        parts.append(part)
    with destination.open("xb") as output:
        for part in parts:
            with part.open("rb") as stream:
                shutil.copyfileobj(stream, output, length=1024 * 1024)
    verify(destination, selected["archive"])


def extract(archive, archive_entry, entries, destination):
    verify(archive, archive_entry)
    expected = {entry["path"]: entry for entry in entries}
    if not expected or len(expected) != len(entries):
        raise ValueError("nonempty unique payload manifest required")
    allowed_directories = set()
    for name in expected:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or str(path) != name:
            raise ValueError("unsafe payload path")
        allowed_directories.update(str(parent) for parent in path.parents if str(parent) != ".")
    with tarfile.open(archive, "r:gz") as bundle:
        members = []
        seen = set()
        for member in bundle:
            name = member.name.rstrip("/") if member.isdir() else member.name
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or str(path) != name or name in seen:
                raise ValueError("unsafe or duplicate archive path")
            seen.add(name)
            if member.isdir():
                if name not in allowed_directories:
                    raise ValueError("unexpected archive directory")
            elif name not in expected or not (member.isfile() or member.islnk()):
                raise ValueError("unexpected archive member or size")
            elif member.isfile() and member.size != expected[name]["bytes"]:
                raise ValueError("unexpected archive member or size")
            else:
                members.append(member)
            if len(seen) > len(expected) + len(allowed_directories):
                raise ValueError("too many archive members")
        if {member.name for member in members} != set(expected):
            raise ValueError("missing archive payload")
        by_name = {member.name: member for member in members}
        for member in members:
            if member.islnk():
                target = by_name.get(member.linkname)
                if target is None or not target.isfile() or member.size != 0:
                    raise ValueError("hardlink target must be an allowlisted regular member")
                if any(expected[member.name][key] != expected[target.name][key] for key in ("bytes", "sha256")):
                    raise ValueError("hardlink payload identity mismatch")
        private_root(destination)
        destination = new_directory(destination).resolve()
        for member in members:
            target = destination / member.name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            stored = by_name[member.linkname] if member.islnk() else member
            with bundle.extractfile(stored) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            target.chmod(0o600)
            verify(target, expected[member.name])
    verify_inputs({"inputs": entries}, destination)
    return {"files": len(entries), "bytes": sum(entry["bytes"] for entry in entries), "all_payload_sha256_verified": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", choices=("contact", "native"))
    parser.add_argument("parts", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    selected, entries = package(args.package)
    private_root(args.output)
    output = new_directory(args.output).resolve()
    archive = output / selected["archive"]["name"]
    reconstruct(selected, args.parts, archive)
    result = extract(archive, selected["archive"], entries, output / "payload")
    print(json.dumps({"package": args.package, "archive_sha256": sha256(archive), "logical_payload_files": selected["file_count"], "embedded_manifests": 1, **result}, indent=2))
