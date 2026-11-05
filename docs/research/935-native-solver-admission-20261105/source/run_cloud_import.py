"""Bound one hash-verified native control then full-head OpenFOAM import.

Runs inside the preselected pinned mesh-CFD image. No field solve or changes
to the input domain; produces a terminal receipt and complete output manifest.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, data):
    with path.open("x") as stream:
        stream.write(json.dumps(data, indent=2) + "\n")


def main():
    root = Path(__file__).resolve().parent
    assert not (root / "worker-pid.json").exists()
    write(root / "worker-pid.json", {"pid": os.getpid(), "epoch": time.time()})
    manifest = json.loads((root / "input-manifest.json").read_text())
    for row in manifest["files"]:
        assert sha(root / row["path"]) == row["sha256"]
    assert sha(root / "head.msh") == "4052bfb3deb225b403873a79f73f01279b63bbbe500808540076103c5f4c3118"
    assert sha(root / "control.msh") == "2b99e340d85e0fe7c8bc1bf34ba442c8488f4ead4d488428858d9b9e4fc24fb1"
    spec = importlib.util.spec_from_file_location("retained_precision_probe", root / "precision_probe.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    assert sha(root / "precision_probe.py") == "e6bca21f9c31812dcd73e7801b375ecda68d671eac8c1e421b41fda58ff937d2"
    assert Path("/opt/openfoam13/etc/bashrc").is_file()
    assert len(os.sched_getaffinity(0)) >= 2
    write(root / "runtime.json", {"python": os.sys.version.split()[0],
        "source_sha256": sha(Path(__file__)), "affinity_count": len(os.sched_getaffinity(0)),
        "openfoam_setup_sha256": sha(Path("/opt/openfoam13/etc/bashrc")),
        "child_address_space_gib": 48, "field_solve_permitted": False})

    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (48 * 1024**3, 48 * 1024**3))

    def run(name, shell, seconds):
        started = time.monotonic()
        with (root / (name + ".log")).open("x") as stream:
            child = subprocess.Popen(["bash", "-c", shell], cwd=root, stdout=stream,
                                     stderr=subprocess.STDOUT, start_new_session=True, preexec_fn=limit)
            timeout = False
            try:
                code = child.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                timeout = True
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    code = child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    code = child.wait()
        result = {"exit_code": code, "timeout": timeout, "seconds": time.monotonic() - started,
                  "log_sha256": sha(root / (name + ".log"))}
        write(root / (name + "-execution.json"), result)
        return code == 0 and not timeout

    prefix = "source /opt/openfoam13/etc/bashrc >/dev/null 2>&1 || exit 91; "
    assert run("version", prefix + "foamVersion; command -v gmshToFoam; command -v checkMesh", 30)
    for name in ("control", "head"):
        folder = root / name
        (folder / "system").mkdir(parents=True)
        (folder / "constant").mkdir()
        (folder / "system/controlDict").write_text(helper.CONTROL)
        os.link(root / (name + ".msh"), folder / "input.msh")
    assert run("control-convert", prefix + "gmshToFoam -case control control/input.msh", 60)
    assert run("control-check", prefix + "checkMesh -case control", 60)
    assert "Mesh OK." in (root / "control-check.log").read_text()
    checked = helper.readback(root / "control/constant/polyMesh", root / "precision-control.npz")
    assert all(checked[k] for k in ("all_coordinates_exact", "all_tet_vertex_sets_exact", "all_boundary_face_vertex_sets_exact"))
    write(root / "control-readback.json", checked)
    converted = run("head-convert", prefix + "gmshToFoam -case head head/input.msh", 720)
    checked_head = run("head-check", prefix + "checkMesh -case head", 240) if converted else False
    return {"terminal": "bounded_import_diagnostic_finished", "head_conversion_passed": converted,
            "head_native_check_passed": checked_head and "Mesh OK." in (root / "head-check.log").read_text(),
            "head_all_arrays_independently_read_back": False,
            "case_specific_solver_admission": False, "field_solve_executed": False,
            "physics_admitted": False, "manufacturing_qualified": False}


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    try:
        result = main()
    except Exception as error:
        result = {"terminal": "worker_failed_closed", "exception_type": type(error).__name__,
                  "error": str(error), "physics_admitted": False, "manufacturing_qualified": False}
    write(root / "terminal-state.json", result)
    files = []
    omitted = []
    for path in sorted(root.rglob("*")):
        assert not path.is_symlink()
        if not path.is_file():
            continue
        row = {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        if row["path"] in ("head.msh", "head/input.msh", "control/input.msh"):
            omitted.append(row)
        else:
            files.append(row)
    write(root / "result-manifest.json", {"files": files, "omitted_duplicate_inputs": omitted})
