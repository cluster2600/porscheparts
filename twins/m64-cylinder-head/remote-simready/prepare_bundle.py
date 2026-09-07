#!/usr/bin/env python3
"""Prepare an immutable M64 input bundle; never connect, rent or run phases."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import time

PROFILE = "m64-omni-static-v1"
PHASE_LIMITS_MIB = {
    "preflight": 2, "context": 2, "convert": 8, "minimum": 2,
    "material": 24, "physics": 32, "profile-initial": 2, "conform": 24,
    "asset-validation": 2, "geometry-validation": 2,
    "physics-validation": 2, "profile-validation": 2, "render": 8,
    "wrapper": 2,
}
ALLOWED_SKILL_SUFFIXES = {".py", ".sh", ".ps1", ".md", ".json", ".yaml", ".yml", ".toml", ".sig", ".stl"}


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def record(root, path):
    return {"path": path.relative_to(root).as_posix(), "size": path.stat().st_size, "sha256": digest(path)}


def write_json(path, value):
    with path.open("x", encoding="utf-8") as target:
        json.dump(value, target, sort_keys=True, indent=2)
        target.write("\n")
    path.chmod(0o600)


def copy_regular(source, destination):
    if source.is_symlink() or not source.is_file() or source.stat().st_nlink != 1:
        raise ValueError(f"non-regular source refused: {source.name}")
    if source.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("source file exceeds bound")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with source.open("rb") as inp, destination.open("xb") as out:
        shutil.copyfileobj(inp, out)
    destination.chmod(0o600)


def prepare(root, assembly, skill, context, material_prompt, physics_prompt):
    if not re.fullmatch(r"m64-[a-z0-9][a-z0-9-]{0,63}", root.name):
        raise ValueError("bundle basename must be the M64 job ID")
    if root.exists() or root.is_symlink() or root.parent.resolve() != root.parent:
        raise ValueError("new bundle under canonical parent required")
    root.mkdir(mode=0o700)
    code = []
    for source in sorted((Path(__file__).parent / "phases").glob("*.py")):
        destination = root / "phases" / source.name
        copy_regular(source, destination)
        code.append(record(root, destination))
    for source in sorted(skill.rglob("*")):
        relative = source.relative_to(skill)
        if "__pycache__" in relative.parts:
            continue
        if source.is_symlink():
            raise ValueError("skill symlink refused")
        if source.is_dir():
            continue
        if source.suffix not in ALLOWED_SKILL_SUFFIXES or any(part.startswith(".") for part in relative.parts):
            raise ValueError(f"unexpected skill file: {relative}")
        destination = root / "skill" / relative
        copy_regular(source, destination)
        code.append(record(root, destination))
    if not (root / "skill/SKILL.md").is_file():
        raise ValueError("complete installed skill required")
    write_json(root / "code-manifest.json", {
        "schema_version": "1.0.0", "profile": PROFILE,
        "files": sorted(code, key=lambda item: item["path"]),
    })
    for source, name in ((assembly, "assembly.step"), (context, "asset-context.json"),
                         (material_prompt, "material-prompt.txt"), (physics_prompt, "physics-prompt.txt")):
        copy_regular(source, root / "inputs" / name)
    # Invalid contextual data must fail before any remote allocation.
    context_data = json.loads((root / "inputs/asset-context.json").read_text())
    if not isinstance(context_data, dict) or context_data.get("manufacturing_authorized") is not False:
        raise ValueError("context must explicitly retain the manufacturing hold")
    if context_data.get("source_step_sha256") != digest(root / "inputs/assembly.step"):
        raise ValueError("context describes a different STEP")
    total = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
    if total > 128 * 1024 * 1024:
        raise ValueError("bundle exceeds transport limit")
    return {"bundle": str(root), "code_manifest_sha256": digest(root / "code-manifest.json"),
            "assembly_sha256": digest(root / "inputs/assembly.step"), "bytes": total,
            "cloud_instance_created": False}


def bind(root, instance_id, label, image, created, deadline, budget, max_dph):
    if type(instance_id) is not int or instance_id <= 0 or not re.fullmatch(r"[A-Za-z0-9._-]+", label):
        raise ValueError("invalid instance identity")
    if not re.fullmatch(r"ghcr.io/cluster2600/3dprinting993-simready-m64-runtime@sha256:[0-9a-f]{64}", image):
        raise ValueError("pinned approved image required")
    if not 0 < deadline - created <= 7200 or created > time.time() or deadline <= time.time():
        raise ValueError("invalid two-hour deadline")
    if not all(math.isfinite(x) for x in (budget, max_dph)) or not 0 < budget <= 20 or not 0 < max_dph <= 2.5:
        raise ValueError("budget exceeds authorization")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("bundle symlink refused")
        if path.is_file():
            files.append(record(root, path))
    # Refuse re-binding or accidentally bundling outputs.
    if any(item["path"] == "job-manifest.json" or item["path"].startswith("results/") for item in files):
        raise ValueError("bundle already bound or executed")
    outputs = [{"path": f"results/{name}", "max_bytes": mib * 1024 * 1024}
               for name, mib in PHASE_LIMITS_MIB.items()]
    reserve = 2 * (sum(x["size"] for x in files) + sum(x["max_bytes"] for x in outputs)) / 1e9 * .05
    if (deadline - created) / 3600 * max_dph + reserve > budget:
        raise ValueError("allocation does not cover deadline plus transfer reserve")
    manifest = {"schema_version": "1.0.0", "profile": PROFILE, "job_id": root.name,
                "instance_id": instance_id, "label": label, "image": image,
                "created_epoch": created, "deadline_epoch": deadline,
                "max_dph": max_dph, "budget_usd": budget, "files": files, "outputs": outputs}
    write_json(root / "job-manifest.json", manifest)
    return {"manifest": str(root / "job-manifest.json"), "manifest_sha256": digest(root / "job-manifest.json"),
            "transfer_reserve_usd": reserve, "cloud_instance_created": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("prepare")
    new.add_argument("--output", type=Path, required=True)
    for option in ("assembly", "skill", "context", "material-prompt", "physics-prompt"):
        new.add_argument("--" + option, type=Path, required=True)
    attach = commands.add_parser("bind")
    attach.add_argument("--bundle", type=Path, required=True)
    for option in ("instance-id", "created", "deadline"):
        attach.add_argument("--" + option, type=int, required=True)
    for option in ("label", "image"):
        attach.add_argument("--" + option, required=True)
    attach.add_argument("--budget", type=float, required=True)
    attach.add_argument("--max-dph", type=float, default=2.5)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.output, args.assembly, args.skill, args.context, args.material_prompt, args.physics_prompt)
    else:
        result = bind(args.bundle, args.instance_id, args.label, args.image, args.created, args.deadline, args.budget, args.max_dph)
    print(json.dumps(result, indent=2))
