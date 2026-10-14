#!/usr/bin/env python3
"""Prepare and launch a bounded transient diagnostic; never qualify performance."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid

from prepare_case import IMAGE, sha
from run_cartesian_pilot import verify


def prepare(parent, output):
    hashes = verify(parent)
    manifest = json.loads((parent / "case-manifest.json").read_text())
    proof = json.loads((parent / "cartesian-proof.json").read_text())
    if "transonic_countertrial" not in manifest:
        raise ValueError("Verified runtime 008 inputs required")
    output.mkdir(parents=True, exist_ok=False)
    for name in manifest["file_sha256"] | proof["mesh"]["mesh_sha256"]:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(parent / name, target)
        if sha(target) != hashes[name]:
            raise ValueError("Copy changed: " + name)
    (output / "provenance").mkdir()
    for name in ("case-manifest.json", "cartesian-proof.json"):
        shutil.copyfile(parent / name, output / "provenance" / name)
    edits = {
        "system/fvSchemes": [
            ("default steadyState;", "default Euler;"),
            ("bounded Gauss linearUpwind grad(U)", "Gauss upwind"),
            ("bounded Gauss linearUpwind grad(h)", "Gauss upwind"),
            ("bounded Gauss linearUpwind grad(K)", "Gauss upwind"),
            ("div(phi,k) bounded Gauss upwind", "div(phi,k) Gauss upwind"),
            ("div(phi,omega) bounded Gauss upwind", "div(phi,omega) Gauss upwind"),
        ],
        "system/controlDict": [
            ("application rhoSimpleFoam;", "application rhoPimpleFoam;"),
            ("endTime 800; deltaT 1;", "endTime 0.00002; deltaT 1e-8;\nadjustTimeStep yes; maxCo 0.3; maxDeltaT 1e-7;"),
            ("writeInterval 100;", "writeInterval 20;"),
        ],
    }
    for name, replacements in edits.items():
        content = (output / name).read_text()
        for old, new in replacements:
            if content.count(old) != 1:
                raise ValueError("Unexpected runtime 008 input: " + old)
            content = content.replace(old, new)
        (output / name).write_text(content)
    (output / "system/fvSolution").write_text('''FoamFile {version 2.0; format ascii; class dictionary; object fvSolution;}
solvers {
 "(rho|rhoFinal)" {solver diagonal;}
 p {solver GAMG; smoother GaussSeidel; scaleCorrection false; tolerance 1e-8; relTol .01;}
 pFinal {$p; relTol 0;}
 "(U|k|omega|h).*" {solver PBiCGStab; preconditioner DILU; tolerance 1e-9; relTol 0;}
}
PIMPLE {nOuterCorrectors 2; nCorrectors 2; nNonOrthogonalCorrectors 0;
 momentumPredictor yes; transonic yes; turbOnFinalIterOnly yes;}
relaxationFactors {equations {".*" 1;}}
''')
    for name in (*edits, "system/fvSolution"):
        manifest["file_sha256"][name] = sha(output / name)
    manifest["transient_diagnostic"] = {
        "source_sha256": sha(Path(__file__)), "parent_manifest_sha256": hashes["case-manifest.json"],
        "solver": "rhoPimpleFoam", "end_time_s": 2e-5, "max_courant": .3,
        "max_delta_t_s": 1e-7, "operating_conditions_changed": False,
        "method": "Euler time integration, conservative upwind convection, two PIMPLE outer correctors.",
        "limitation": "Short startup only, fixed MRF and staircase walls; not a sliding-mesh or performance result.",
    }
    (output / "case-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    proof["case_manifest_sha256"] = sha(output / "case-manifest.json")
    proof["derivation"] = {"source_sha256": sha(Path(__file__)),
                           "parent_proof_sha256": hashes["cartesian-proof.json"],
                           "method": "Exact mesh copy; transient equations only, all boundary conditions unchanged."}
    (output / "cartesian-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    if any(sha(parent / name) != digest for name, digest in hashes.items()):
        raise ValueError("Parent changed during copying")
    verify(output)


# The watchdog lives with the solver in Docker, independently of the calling terminal.
SUPERVISOR = r'''#!/bin/bash
source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1
cd /case || exit 90
stdbuf -oL -eL rhoPimpleFoam > log.transient-rhoPimpleFoam 2>&1 &
solver=$!
watch() {
    while kill -0 "$solver" 2>/dev/null; do
        if grep -Eq 'FOAM FATAL|Foam::sigFpe' log.transient-rhoPimpleFoam; then
            echo native_fatal > rejection-reason.txt
        fi
        for table in postProcessing/scalarMinima/*/volFieldValue.dat; do
            [ -f "$table" ] || continue
            if ! awk '!/^#/ && NF {if (NF != 3 || $2 !~ /^[+0-9.eE-]+$/ || $3 !~ /^[+0-9.eE-]+$/ || !($2 > 0) || !($3 > 0)) exit 1}' "$table"; then
                echo nonphysical_pressure_or_temperature > rejection-reason.txt
            fi
        done
        if [ -f rejection-reason.txt ]; then
            kill -TERM "$solver" 2>/dev/null
            sleep 2
            kill -KILL "$solver" 2>/dev/null
            return
        fi
        sleep 5
    done
}
watch &
watchdog=$!
wait "$solver"
code=$?
kill "$watchdog" 2>/dev/null
wait "$watchdog" 2>/dev/null
[ ! -f rejection-reason.txt ] || code=65
exit "$code"
'''

ENTRYPOINT = r'''cd /case || exit 90
timeout --signal=TERM --kill-after=15s 7200 bash transient-supervisor.sh
code=$?
status=failed
if [ "$code" -eq 0 ] && grep -q '^End$' log.transient-rhoPimpleFoam && [ ! -f rejection-reason.txt ]; then
    status=native_completed_requires_history_audit
elif [ "$code" -eq 0 ]; then
    code=66
fi
printf '{"status":"%s","exit_code":%s,"performance_ranking_authorized":false}\n' "$status" "$code" > native-exit.json.tmp
mv native-exit.json.tmp native-exit.json
exit "$code"
'''


def launch(case):
    case = case.resolve()
    hashes = verify(case)
    manifest = json.loads((case / "case-manifest.json").read_text())
    if manifest.get("transient_diagnostic", {}).get("source_sha256") != sha(Path(__file__)):
        raise ValueError("Current transient preparation required")
    if (case / "postProcessing").exists() or any(
            p.name not in ("0",) and p.name[:1].isdigit() for p in case.iterdir()):
        raise ValueError("Existing solver outputs")
    if (case / "launch-transient.json").exists() or (case / "transient-supervisor.sh").exists():
        raise ValueError("Already launched; prepare a new case")
    container = "bionic-transient-" + uuid.uuid4().hex[:12]
    (case / "transient-supervisor.sh").write_text(SUPERVISOR)
    report = {"status": "launch_requested", "container": container, "image": IMAGE,
              "input_sha256": hashes, "source_sha256": sha(Path(__file__)),
              "supervisor_sha256": sha(case / "transient-supervisor.sh"),
              "timeout_seconds": 7200, "cpus": 2, "memory_gb": 6,
              "performance_ranking_authorized": False}
    path = case / "launch-transient.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    result = subprocess.run([
        "docker", "run", "-d", "--pull=never", "--platform", "linux/arm64", "--network", "none",
        "--read-only", "--name", container, "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--pids-limit", "256", "--cpus", "2", "--memory", "6g", "--tmpfs", "/tmp:rw,nosuid,size=256m",
        "--user", f"{os.getuid()}:{os.getgid()}", "--mount", f"type=bind,source={case},target=/case",
        "--entrypoint", "/bin/bash", IMAGE, "-c", ENTRYPOINT], capture_output=True, text=True, timeout=60)
    report["status"] = "launched" if result.returncode == 0 else "launch_failed"
    report["container_id"] = result.stdout.strip()
    report["launch_error"] = result.stderr.strip()
    path.write_text(json.dumps(report, indent=2) + "\n")
    if result.returncode:
        raise RuntimeError("Detached launch failed: " + result.stderr)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("parent", type=Path)
    prep.add_argument("output", type=Path)
    run = sub.add_parser("launch")
    run.add_argument("case", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.parent, args.output)
        print("Transient diagnostic prepared; performance comparison unauthorized.")
    else:
        print(json.dumps(launch(args.case)))
