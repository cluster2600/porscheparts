"""Bound one local unoptimized head-volume diagnostic after a cube control."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "repository", "candidate", "admission", "python", "scientific-site"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.root.mkdir(mode=0o700, exist_ok=False)
    admission = json.loads(args.admission.read_text())
    expected = "7adc8f931feac78eb6298e1415c8d49b7a92bced5dde5dbcc6bc3afd2e9e947f"
    assert sha(args.candidate) == expected == admission["input_sha256"]
    assert admission["geometry_export_gate_passed"] and admission["intersection_pairs"] == 0
    assert admission["vertex_manifold"] and admission["connected_components"] == 1
    source = Path(__file__).with_name("mesh_without_optimization.py")
    recipe = args.repository / "docs/research/935-hypothesis-study-20261029/source/mesh_solid.py"
    inspector = args.repository / "docs/research/935-local-physics-20261105/source/inspect_tetrahedra.py"
    policy = {"candidate_sha256": expected, "admission_sha256": sha(args.admission),
              "controller_sha256": sha(Path(__file__)), "wrapper_sha256": sha(source),
              "recipe_sha256": sha(recipe), "inspector_sha256": sha(inspector),
              "construction_only": True, "optimize": False, "interior_size_mm": 2.0,
              "head_timeout_seconds": 900, "sampled_rss_limit_gib": 40,
              "head_threads": 8, "upstream_verdict": "Diagnostic only; protected poor faces and hypothetical geometry retained",
              "parameter_sweep": False, "physics_admitted": False, "new_paid_compute_usd": 0}
    write(args.root / "predeclared-policy.json", policy)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(args.scientific_site)
    base = [str(args.python), "-B", str(source), "--recipe", str(recipe)]
    control = base + ["--input", "cube", "--output", str(args.root / "cube"), "--threads", "2"]
    with (args.root / "cube.log").open("x") as log:
        done = subprocess.run(control, env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=60)
    assert done.returncode == 0, "Native cube construction failed"
    # Analytic, independently fixed cube surface; never derived from mesher output.
    cube_vertices = np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],
                              [0,0,1],[1,0,1],[1,1,1],[0,1,1]], float)
    cube_faces = np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],
                           [0,1,5],[0,5,4],[1,2,6],[1,6,5],
                           [2,3,7],[2,7,6],[3,0,4],[3,4,7]])
    np.savez_compressed(args.root / "cube-source.npz", vertices=cube_vertices, triangles=cube_faces)
    write(args.root / "cube-source.json", {"input_sha256": sha(args.root / "cube-source.npz"),
          "geometry_export_gate_passed": True, "signed_volume_mm3": 1.0,
          "scope": "Synthetic analytic unit cube contract, no specimen dimensions"})
    with (args.root / "cube-inspection.log").open("x") as log:
        done = subprocess.run([str(args.python), "-B", str(inspector), "--mesh",
            str(args.root / "cube/solid.npz"), "--source-mesh", str(args.root / "cube-source.npz"),
            "--source-report", str(args.root / "cube-source.json"), "--output", str(args.root / "cube-inspection")],
            env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=60)
    assert done.returncode == 0, "Independent cube inspection failed"
    assert shutil.disk_usage(args.root).free > 10 * 1024**3
    command = base + ["--input", str(args.candidate), "--output", str(args.root / "head"), "--threads", "8"]
    peak = 0
    started = time.monotonic()
    terminal = "running"
    with (args.root / "head.log").open("x") as log:
        child = subprocess.Popen(command, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        write(args.root / "running.json", {"pid": child.pid, "argv": command, "policy": policy})
        try:
            while child.poll() is None:
                time.sleep(2)
                usage = subprocess.run(["ps", "-o", "rss=", "-p", str(child.pid)], capture_output=True, text=True)
                if usage.stdout.strip():
                    peak = max(peak, int(usage.stdout.strip()))
                if (time.monotonic() - started > 900 or peak > 40 * 1024**2
                        or shutil.disk_usage(args.root).free < 4 * 1024**3):
                    terminal = "bounded_limit_reached"
                    os.killpg(child.pid, signal.SIGTERM)
                    break
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
    if terminal == "running":
        terminal = "native_export_complete" if child.returncode == 0 else "native_failure"
    result = {"terminal": terminal, "exit_code": child.returncode,
              "seconds": time.monotonic() - started, "sampled_peak_rss_kib": peak,
              "mesh_exported": (args.root / "head/solid.npz").exists(),
              "log_sha256": sha(args.root / "head.log"), "head_independent_inspection_pending": True,
              "physics_admitted": False, "manufacturing_qualified": False, "new_paid_compute_usd": 0}
    write(args.root / "execution.json", result)
    print(json.dumps(result), flush=True)
    if terminal != "native_export_complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
