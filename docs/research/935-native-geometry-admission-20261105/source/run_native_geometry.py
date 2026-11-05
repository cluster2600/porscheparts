"""Execute manifest-bound structured controls and one optional head diagnostic.

Both declared runtimes are exercised: existing Kali OpenFOAM 14 for controls,
then the pinned Vast OpenFOAM 13 image if local head capacity is insufficient.
No thresholds or input mesh coordinates are adjusted to obtain a pass.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import time


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def main(root):
    assert not (root / "worker-pid.json").exists()
    write(root / "worker-pid.json", {"pid": os.getpid(), "epoch": time.time()})
    plan = json.loads((root / "geometry-plan.json").read_text())
    manifest = json.loads((root / "input-manifest.json").read_text())
    for row in manifest["files"]:
        assert sha(root / row["path"]) == row["sha256"]
    assert plan["foam_setup"] in ("/opt/openfoam13/etc/bashrc", "/opt/openfoam14/etc/bashrc")
    assert Path(plan["foam_setup"]).is_file()
    assert plan["head_address_space_gib"] == 48 and plan["head_timeout_seconds"] == 600
    assert plan["control_helper_sha256"] == sha(root / "structured_control.py")
    assert plan["field_solve_permitted"] is False
    write(root / "runtime.json", {"python": os.sys.version.split()[0],
        "worker_source_sha256": sha(Path(__file__)), "foam_setup": plan["foam_setup"],
        "foam_setup_sha256": sha(Path(plan["foam_setup"])),
        "host_affinity_count": len(os.sched_getaffinity(0)),
        "head_address_space_gib": 48, "field_solve_permitted": False})

    def run(name, argv, seconds, gib=1):
        def limit():
            resource.setrlimit(resource.RLIMIT_AS, (gib * 1024**3, gib * 1024**3))
        # Source only the exact validated runtime setup; all task paths are fixed.
        command = 'source "' + plan["foam_setup"] + '" >/dev/null 2>&1 || exit 91; "$@"'
        started = time.monotonic()
        with (root / (name + ".log")).open("x") as stream:
            child = subprocess.Popen(["bash", "-c", command, "geometry-step", *argv], cwd=root,
                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True, preexec_fn=limit)
            timed_out = False
            try:
                code = child.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    code = child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    code = child.wait()
        result = {"argv": argv, "exit_code": code, "timeout": timed_out,
            "seconds": time.monotonic() - started, "address_space_gib": gib,
            "log_sha256": sha(root / (name + ".log"))}
        write(root / (name + "-execution.json"), result)
        return code == 0 and not timed_out

    def text(name):
        return (root / (name + ".log")).read_text()

    assert run("version", ["foamVersion"], 30)
    assert run("block-mesh", ["blockMesh", "-case", "control"], 60)
    assert run("control-contract", ["python3", "structured_control.py", "--root", str(root)], 60)
    contract = json.loads((root / "control-contract.json").read_text())
    assert contract["complete_analytic_coordinate_cell_face_boundary_comparison_passed"]
    standard = run("default-control", ["checkMesh", "-case", "control"], 60)
    extended = run("geometry-control", ["checkMesh", "-noTopology", "-allGeometry", "-case", "control"], 60)
    # A failed checkMesh may return zero. Native report content is mandatory.
    run("inverted-control", ["checkMesh", "-noTopology", "-allGeometry", "-case", "inverted-control"], 60)
    negative = text("inverted-control")
    controls_passed = (standard and extended and "Mesh OK." in text("default-control")
        and "Mesh OK." in text("geometry-control")
        and "Cell determinant check OK." in text("geometry-control")
        and "Mesh OK." not in negative
        and re.search(r"Number of negative volume cells:\s*8\b", negative) is not None
        and re.search(r"Failed [1-9][0-9]* mesh checks", negative) is not None)
    write(root / "control-admission.json", {"passed": controls_passed,
        "content_required_even_when_process_exit_zero": True,
        "analytic_contract_sha256": sha(root / "control-contract.json")})
    assert controls_passed, "Structured native controls failed; head diagnostic refused"
    head_started = bool(plan["run_head"])
    selected_passed = False
    if head_started:
        assert plan["upstream_head_admission"] == "diagnostic_only"
        head_success = run("head-geometry", ["checkMesh", "-noTopology", "-allGeometry", "-case", "head"], 600, gib=48)
        selected_passed = head_success and "Mesh OK." in text("head-geometry") and not re.search(r"Failed [1-9][0-9]* mesh checks", text("head-geometry"))
    for row in manifest["files"]:
        assert sha(root / row["path"]) == row["sha256"], "A native check changed an input"
    return {"terminal": "bounded_native_geometry_diagnostic_finished",
        "controls_passed": True, "head_started": head_started,
        "native_head_selected_checks_passed": selected_passed,
        "all_original_inputs_rehashed_unchanged": True,
        "native_full_topology_not_completed_by_this_selector": True,
        "case_specific_operator_admission": False, "field_solve_executed": False,
        "physics_admitted": False, "manufacturing_qualified": False}


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    try:
        result = main(root)
    except Exception as error:
        result = {"terminal": "worker_failed_closed", "exception_type": type(error).__name__,
            "error": str(error), "physics_admitted": False, "manufacturing_qualified": False}
    write(root / "terminal-state.json", result)
    inputs = {row["path"]: row for row in json.loads((root / "input-manifest.json").read_text())["files"]}
    files = []
    unchanged = []
    for path in sorted(root.rglob("*")):
        assert not path.is_symlink()
        if not path.is_file():
            continue
        row = {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        if row["path"] in inputs and row["sha256"] == inputs[row["path"]]["sha256"]:
            unchanged.append(row)
        elif row["path"] not in ("inputs.tar.gz", "inputs.tar"):
            files.append(row)
    write(root / "result-manifest.json", {"files": files, "unchanged_inputs": unchanged,
        "unchanged_input_count": len(unchanged), "expected_input_count": len(inputs)})
