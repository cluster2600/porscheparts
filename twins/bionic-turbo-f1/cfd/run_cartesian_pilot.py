#!/usr/bin/env python3
"""Run an explicitly diagnostic solver after the independent Cartesian proof."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

import check_cartesian_cells
from prepare_case import IMAGE, sha


def verify(case):
    proof = json.loads((case / "cartesian-proof.json").read_text())
    manifest = json.loads((case / "case-manifest.json").read_text())
    if (proof.get("schema") != "bionic-cartesian-diagnostic-admission/v1"
            or proof.get("status") != "cartesian_geometry_proven"
            or proof.get("source_sha256") != sha(Path(check_cartesian_cells.__file__))
            or proof.get("case_manifest_sha256") != sha(case / "case-manifest.json")
            or proof.get("diagnostic_solver_authorized") is not True
            or proof.get("proof", {}).get("all_cells_axis_aligned_boxes") is not True
            or proof.get("performance_ranking_authorized") is not False
            or manifest.get("image") != IMAGE):
        raise ValueError("Current independent Cartesian proof required")
    hashes = manifest["file_sha256"] | proof["mesh"]["mesh_sha256"]
    hashes["case-manifest.json"] = sha(case / "case-manifest.json")
    hashes["cartesian-proof.json"] = sha(case / "cartesian-proof.json")
    for name, digest in hashes.items():
        if not (case / name).resolve().is_relative_to(case.resolve()) or sha(case / name) != digest:
            raise ValueError("Changed or escaping input: " + name)
    return hashes


def run(case):
    case = case.resolve()
    hashes = verify(case)
    if (case / "postProcessing").exists() or any(p.is_dir() and re.fullmatch(r"\d+(?:\.\d+)?", p.name) and p.name != "0" for p in case.iterdir()):
        raise ValueError("Existing solver output: prepare a fresh case")
    report_path = case / "run-cartesian-solve.json"
    log = case / "log.cartesian-rhoSimpleFoam"
    if report_path.exists() or log.exists():
        raise ValueError("Diagnostic solver already attempted")
    container = "bionic-cartesian-" + uuid.uuid4().hex[:12]
    report = {"schema": "bionic-cartesian-diagnostic-solve/v1", "status": "running",
              "container": container, "image": IMAGE, "source_sha256": sha(Path(__file__)),
              "input_sha256": hashes, "timeout_seconds": 7200, "cpus": 2, "memory_gb": 6,
              "canonical_mesh_gate_passed": False, "performance_ranking_authorized": False,
              "engineering_validated": False}
    with report_path.open("x") as stream:
        json.dump(report, stream, indent=2)
    started = time.monotonic()
    argv = ["docker", "run", "--rm", "--pull=never", "--platform", "linux/arm64", "--network", "none",
            "--read-only", "--name", container, "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--pids-limit", "256", "--cpus", "2", "--memory", "6g", "--tmpfs", "/tmp:rw,nosuid,size=256m",
            "--user", f"{os.getuid()}:{os.getgid()}", "--mount", f"type=bind,source={case},target=/case",
            "--entrypoint", "/bin/bash", IMAGE, "-c",
            "source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; cd /case; exec rhoSimpleFoam"]
    try:
        with log.open("x") as stream:
            result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT, timeout=7200)
        report["exit_code"] = result.returncode
        if result.returncode or "FOAM FATAL" in log.read_text():
            raise ValueError("Native diagnostic solver failed")
        if any(sha(case / name) != digest for name, digest in hashes.items()):
            raise ValueError("Input changed during diagnostic solve")
        report["status"] = "native_completed_requires_history_audit"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = str(error)
    finally:
        subprocess.run(["docker", "rm", "-f", container], capture_output=True, timeout=15)
        report["elapsed_seconds"] = time.monotonic() - started
        report["log_sha256"] = sha(log) if log.exists() else None
        report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


if __name__ == "__main__":
    report = run(Path(sys.argv[1]))
    print(json.dumps({"status": report["status"], "error": report.get("error")}))
    raise SystemExit(0 if report["status"] == "native_completed_requires_history_audit" else 1)
