"""Small, fail-closed helpers shared by the six optional tool integrations."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CARRIER_RECORD = "catalog/parts/993-eng-carrier-0001.json"
CARRIER_CONVERGENCE = "docs/reports/carrier-resume-20261020/CONVERGENCE.md"


def load(path):
    def reject_constant(value):
        raise ValueError("nonfinite JSON")

    return json.loads(Path(path).read_text(), parse_constant=reject_constant)


def write(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
        )


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite(value, positive=False):
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or (positive and value <= 0)
    ):
        raise ValueError("finite numeric value required")
    return float(value)


def new_directory(path):
    path = Path(path)
    if path.is_symlink() or path.exists():
        raise ValueError("new output directory required")
    path.mkdir(parents=True, mode=0o700)
    return path


def source_path(root, relative):
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("relative artifact path required")
    root = Path(root).resolve(strict=True)
    candidate = root / relative
    chain = [candidate, *list(candidate.parents)[: len(relative.parts) - 1]]
    if not candidate.is_file() or any(p.is_symlink() for p in chain):
        raise ValueError("regular artifact without symlink required")
    if not candidate.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError("artifact outside root")
    return candidate


def checked(argv, cwd, timeout=120, env=None):
    """No shell; kill the owned process group on timeout, including descendants."""
    finite(timeout, positive=True)
    start = time.monotonic()
    process = subprocess.Popen(
        [str(x) for x in argv],
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise TimeoutError("owned tool process exceeded deadline") from None
    if process.returncode:
        # Logs stay in the private working directory, never in public receipts.
        log = Path(cwd) / f"failure-{process.pid}.log"
        log.write_text(output)
        raise RuntimeError(
            f"{Path(argv[0]).name} exited {process.returncode}; private failure log retained"
        )
    return {
        "exit_status": process.returncode,
        "elapsed_seconds": time.monotonic() - start,
        "stdout": output,
    }


def verify_inputs(manifest, root):
    entries = manifest["inputs"]
    if not entries or len({item["path"] for item in entries}) != len(entries):
        raise ValueError("nonempty unique input list required")
    for item in entries:
        target = source_path(root, item["path"])
        if sha256(target) != item["sha256"]:
            raise ValueError("input SHA-256 mismatch")


def receipt(tool, status, inputs, outputs=None, checks=None, limitations=None):
    return {
        "schema_version": 1,
        "tool": tool,
        "status": status,
        "inputs": inputs,
        "outputs": outputs or [],
        "checks": checks or {},
        "limitations": limitations or [],
        "manufacturing_authorized": False,
    }
