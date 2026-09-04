#!/usr/bin/env python3
"""Smokes F47 hors ligne; aucune geometrie ou validation Porsche."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import time


ROOT = Path("/opt/917-f47-cfd-cae")
AATE_REVISION = "c0f75f953d67cd325d28d1300672d14288f22934"


def run(command: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        env={**os.environ, "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"},
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {command!r}\n"
            f"stdout:\n{completed.stdout[-4000:]}\nstderr:\n{completed.stderr[-4000:]}"
        )
    return completed


def openfoam_and_aate() -> tuple[dict[str, object], dict[str, object]]:
    completed = run([str(ROOT / "openfoam_smoke.sh")], timeout=300)
    if completed.stderr:
        raise RuntimeError(f"OpenFOAM smoke wrote stderr: {completed.stderr[-1000:]}")
    payload = json.loads(completed.stdout)
    return (
        {"passed": True, "version": payload["openfoam"], "fixture": "synthetic_poiseuille"},
        {
            "passed": payload["aate_help_invocations"] == 4,
            "version": payload["aate_revision"],
            "smoke": "four_real_help_invocations",
        },
    )


def cantera_smoke() -> dict[str, object]:
    import cantera as ct

    if ct.__version__ != "3.2.0":
        raise RuntimeError(f"unexpected Cantera version: {ct.__version__}")
    gas = ct.Solution("gri30.yaml")
    gas.TP = 300.0, ct.one_atm
    gas.set_equivalence_ratio(1.0, "CH4:1", "O2:1,N2:3.76")
    initial_h = gas.enthalpy_mass
    gas.equilibrate("HP")
    if not (2100.0 < gas.T < 2400.0):
        raise RuntimeError("generic Cantera equilibrium outside smoke range")
    if abs(gas.enthalpy_mass - initial_h) > max(1.0, abs(initial_h)) * 1e-8:
        raise RuntimeError("generic Cantera enthalpy did not close")
    return {"passed": True, "version": ct.__version__, "fixture": "generic_CH4_air_HP"}


def gmsh_smoke(root: Path) -> dict[str, object]:
    geometry = root / "circular-cylinder.geo"
    mesh = root / "circular-cylinder.msh"
    geometry.write_text(
        'SetFactory("OpenCASCADE");\n'
        'Cylinder(1) = {0, 0, 0, 0, 0, 1, 0.2, 2*Pi};\n'
        'Mesh.CharacteristicLengthMin = 0.08;\n'
        'Mesh.CharacteristicLengthMax = 0.12;\n'
        'Mesh 3;\n',
        encoding="ascii",
    )
    completed = run(["gmsh", "-3", "-format", "msh2", "-o", str(mesh), str(geometry)])
    mesh_text = mesh.read_text(encoding="ascii")
    if mesh.stat().st_size < 1000 or "$Elements" not in mesh_text or "$Nodes" not in mesh_text:
        raise RuntimeError("Gmsh did not generate the circular 3D fixture")
    version = run(["gmsh", "-version"]).stdout.strip()
    return {"passed": True, "version": version, "fixture": "circular_cylinder_3d"}


def calculix_smoke(root: Path) -> dict[str, object]:
    deck = root / "uniaxial.inp"
    deck.write_text(
        "*HEADING\nF47 synthetic cube\n"
        "*NODE\n1,0,0,0\n2,1,0,0\n3,1,1,0\n4,0,1,0\n"
        "5,0,0,1\n6,1,0,1\n7,1,1,1\n8,0,1,1\n"
        "*ELEMENT,TYPE=C3D8,ELSET=EALL\n1,1,2,3,4,5,6,7,8\n"
        "*MATERIAL,NAME=GENERIC\n*ELASTIC\n70000,0.3\n"
        "*SOLID SECTION,ELSET=EALL,MATERIAL=GENERIC\n"
        "*BOUNDARY\n1,1,3\n4,1,3\n5,1,3\n8,1,3\n"
        "*STEP\n*STATIC\n*CLOAD\n2,1,1\n3,1,1\n6,1,1\n7,1,1\n"
        "*NODE FILE\nU\n*EL FILE\nS\n*END STEP\n",
        encoding="ascii",
    )
    previous = Path.cwd()
    os.chdir(root)
    try:
        completed = run(["ccx", "-i", deck.stem], timeout=120)
    finally:
        os.chdir(previous)
    if "Job finished" not in completed.stdout + completed.stderr or not (root / "uniaxial.frd").is_file():
        raise RuntimeError("CalculiX synthetic solve did not finish")
    version = run(["dpkg-query", "-W", "-f=${Version}", "calculix-ccx"]).stdout.strip()
    return {"passed": True, "version": version, "fixture": "generic_linear_cube"}


def job_runner_smoke() -> dict[str, object]:
    workspace = Path("/workspace/f46")
    workspace.mkdir(mode=0o750, exist_ok=True)
    smoke_root = workspace / f"image-smoke-{os.getpid()}"
    smoke_root.mkdir(mode=0o700)
    try:
        input_path = smoke_root / "input.json"
        input_path.write_text('{"fixture":"generic-runner"}\n', encoding="ascii")
        import hashlib

        digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
        plan = {
            "status": "launch_authorized",
            "launch_authorized": True,
            "compute_stop_epoch": int(time.time()) + 60,
            "job_ids": ["F47-SYNTHETIC-RUNNER-SMOKE"],
        }
        manifest = {
            "execution_authorized": True,
            "jobs": [
                {
                    "id": "F47-SYNTHETIC-RUNNER-SMOKE",
                    "execution_ready": True,
                    "command": ["python3", "-c", "print('bounded-command-array-pass')"],
                    "timeout_seconds": 10,
                    "input_manifest_path": "input.json",
                    "input_manifest_sha256": digest,
                }
            ],
        }
        (smoke_root / "plan.json").write_text(json.dumps(plan), encoding="ascii")
        (smoke_root / "jobs.json").write_text(json.dumps(manifest), encoding="ascii")
        completed = run(
            [
                str(ROOT / "run_manifest.py"),
                "--plan", str(smoke_root / "plan.json"),
                "--manifest", str(smoke_root / "jobs.json"),
                "--output", str(smoke_root / "state.json"),
            ],
            timeout=30,
        )
        state = json.loads((smoke_root / "state.json").read_text(encoding="utf-8"))
        if completed.stdout or completed.stderr or state["jobs"][0]["status"] != "passed":
            raise RuntimeError("bounded job runner smoke failed")
        return {"passed": True, "version": "f47-1.0.0", "command_array_executed": True}
    finally:
        for path in smoke_root.iterdir():
            path.unlink()
        smoke_root.rmdir()


def cht_smoke() -> dict[str, object]:
    completed = run([str(ROOT / "cht_smoke.sh")], timeout=180)
    if completed.stderr:
        raise RuntimeError(f"CHT smoke wrote stderr: {completed.stderr[-1000:]}")
    payload = json.loads(completed.stdout)
    payload["minimal_conjugate_fixture_executed"] = True
    return payload


def cuda_smoke(required: bool) -> dict[str, object]:
    try:
        smi = run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"], timeout=20)
        allocation = run(["f47-cuda-smoke"], timeout=20)
    except (FileNotFoundError, RuntimeError) as exc:
        if required:
            raise RuntimeError("CUDA runtime smoke required but unavailable") from exc
        return {"passed": False, "version": "not_available_at_cpu_build", "allocation_bytes": 0}
    return {
        "passed": True,
        "version": smi.stdout.strip(),
        "allocation_bytes": 4096,
        "driver_api_output": allocation.stdout.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-cuda", action="store_true")
    args = parser.parse_args()
    if platform.machine() != "x86_64" or os.getuid() != 9147 or os.getgid() != 9147:
        raise RuntimeError("smoke requires native amd64 and dedicated uid/gid 9147")
    forbidden_executables = [name for name in ("ICEEngineFoam", "iceEngineFoam") if shutil.which(name)]
    if forbidden_executables:
        raise RuntimeError(f"unproved solver executable found: {forbidden_executables}")
    current = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="f47-smoke-", dir="/tmp") as temporary:
        root = Path(temporary)
        openfoam, aate = openfoam_and_aate()
        cantera = cantera_smoke()
        gmsh = gmsh_smoke(root)
        try:
            fea = calculix_smoke(root)
        finally:
            os.chdir(current)
        cht = cht_smoke()
        job_runner = job_runner_smoke()
        cuda = cuda_smoke(args.require_cuda)
    tools = {
        "openfoam": openfoam,
        "aate_icengines": aate,
        "cantera_3_2": cantera,
        "gmsh": gmsh,
        "cht": cht,
        "fea": fea,
        "cuda": cuda,
        "job_runner": job_runner,
        "historical_enginefoam": {"available": False, "passed": False, "version": "not_built"},
    }
    report = {
        "schema_version": "1.0.0",
        "status": "cpu_and_cht_smokes_passed_runtime_gpu_blocked",
        "platform": "linux/amd64",
        "runtime_uid": os.getuid(),
        "offline_fixture_inputs": True,
        "tools": tools,
        "exact_ICEEngineFoam_executable_found": bool(forbidden_executables),
        "all_required_F46_runtime_smokes_passed": all(
            tools[name]["passed"]
            for name in (
                "openfoam",
                "aate_icengines",
                "cantera_3_2",
                "gmsh",
                "cht",
                "fea",
                "cuda",
                "job_runner",
            )
        ),
        "engine_simulation_executed": False,
        "physical_validation": False,
        "manufacturing_release": False,
    }
    if args.require_cuda and not cuda["passed"]:
        raise RuntimeError("CUDA gate unexpectedly false")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
