#!/usr/bin/env python3
"""Execute uniquement un manifeste F46 autorise, lie par SHA et par deadline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time


WORKSPACE = Path("/workspace/f46")
GLOBAL_STOP = Path("/workspace/F46_STOP")
FORBIDDEN = re.compile(r"(?:ellipse|elliptic|oval|ovale|(?:^|[^A-Za-z0-9])F(?:39|42)(?:[^A-Za-z0-9]|$))", re.IGNORECASE)


def load(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"regular JSON file required: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("JSON object required")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def confined(path: Path) -> Path:
    resolved = path.resolve(strict=True)
    if WORKSPACE.resolve() not in resolved.parents:
        raise RuntimeError("path outside /workspace/f46")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (os.getuid(), os.getgid()) != (9147, 9147):
        raise RuntimeError("runner must execute as uid/gid 9147")
    plan_path = confined(args.plan)
    manifest_path = confined(args.manifest)
    output_parent = args.output.parent.resolve(strict=True)
    if WORKSPACE.resolve() not in output_parent.parents or args.output.exists() or args.output.is_symlink():
        raise RuntimeError("new output under /workspace/f46 required")
    plan = load(plan_path)
    manifest = load(manifest_path)
    serialized = json.dumps(manifest, sort_keys=True)
    if FORBIDDEN.search(serialized):
        raise RuntimeError("forbidden geometry token or legacy alias in job manifest")
    if "iceEngineFoam" in serialized or "ICEEngineFoam" in serialized:
        raise RuntimeError("unproved solver executable name rejected")
    if plan.get("launch_authorized") is not True or plan.get("status") != "launch_authorized":
        raise RuntimeError("plan is not launch-authorized")
    now = int(time.time())
    stop_epoch = plan.get("compute_stop_epoch")
    if not isinstance(stop_epoch, int) or isinstance(stop_epoch, bool) or stop_epoch <= now:
        raise RuntimeError("compute deadline already reached or malformed")
    jobs = manifest.get("jobs")
    if manifest.get("execution_authorized") is not True or not isinstance(jobs, list) or not jobs:
        raise RuntimeError("job manifest is not execution-authorized")
    expected_ids = plan.get("job_ids")
    actual_ids = [job.get("id") for job in jobs if isinstance(job, dict)]
    if actual_ids != expected_ids or len(actual_ids) != len(jobs):
        raise RuntimeError("ordered job identifiers differ from plan")
    state: dict[str, object] = {"classification": "production_wrapper_evidence", "jobs": []}
    atomic_write(args.output, state)
    for job in jobs:
        if GLOBAL_STOP.exists() or int(time.time()) >= stop_epoch:
            state["jobs"].append({"id": job["id"], "status": "cancelled"})
            atomic_write(args.output, state)
            continue
        command = job.get("command")
        timeout = job.get("timeout_seconds")
        relative_input = job.get("input_manifest_path")
        expected_sha = job.get("input_manifest_sha256")
        if (
            job.get("execution_ready") is not True
            or not isinstance(command, list)
            or not command
            or not all(isinstance(value, str) and value and "\x00" not in value for value in command)
            or not isinstance(timeout, int)
            or isinstance(timeout, bool)
            or timeout <= 0
            or not isinstance(relative_input, str)
            or relative_input.startswith("/")
            or ".." in Path(relative_input).parts
            or re.fullmatch(r"[0-9a-f]{64}", str(expected_sha)) is None
        ):
            raise RuntimeError(f"job contract incomplete: {job.get('id')}")
        input_path = confined(manifest_path.parent / relative_input)
        if sha256(input_path) != expected_sha:
            raise RuntimeError(f"input manifest digest mismatch: {job['id']}")
        remaining = stop_epoch - int(time.time())
        bounded_timeout = min(timeout, remaining)
        if bounded_timeout <= 0:
            result = {"id": job["id"], "status": "cancelled"}
        else:
            started = int(time.time())
            try:
                completed = subprocess.run(
                    command,
                    cwd=input_path.parent,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=bounded_timeout,
                    check=False,
                    env={**os.environ, "HOME": "/tmp", "PYTHONNOUSERSITE": "1"},
                )
                result = {
                    "id": job["id"],
                    "status": "passed" if completed.returncode == 0 else "failed",
                    "returncode": completed.returncode,
                    "started_at_epoch": started,
                    "finished_at_epoch": int(time.time()),
                    "log_tail": completed.stdout[-4000:],
                }
            except subprocess.TimeoutExpired as exc:
                result = {
                    "id": job["id"],
                    "status": "timed_out",
                    "started_at_epoch": started,
                    "finished_at_epoch": int(time.time()),
                    "log_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
                }
        state["jobs"].append(result)
        atomic_write(args.output, state)
        if result["status"] != "passed":
            break
    return 0 if all(item["status"] == "passed" for item in state["jobs"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
