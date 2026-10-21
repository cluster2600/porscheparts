"""Independent bounded-distance or global-intersection audit of the separate head surface."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

import numpy as np

from mesh_head import ROOT, FAMILY, array_sha, new_output, save, sha

SURFACE = ROOT / "work/962-engineering/analysis-flaps-025-001/analysis-surface.npz"
REFERENCE = ROOT / "work/962-engineering/analysis-surface-025-002/source-surface.npz"
CANCELLATION = ROOT / "work/962-engineering/analysis-flaps-025-001/receipt.json"
CONTRACT = FAMILY / "engineering/analysis-flap-contract.json"
IMAGE = "sha256:3ccaf5701c7c9add59eda6e8db918106fc8d51f4c2ef5b148d8079262861c7e1"
DISTANCE_PYTHON = Path("/Users/maxime/projects/3dprinting993/work/m64-private-20260907/bounded-chamfer-20260928.7I5Wgb1M/venv/bin/python")
WHOLEBODY = ROOT / "twins/m64-cylinder-head/source/wholebody"


def intersection_fixtures(cgal):
    base = [[0., 0, 0], [1., 0, 0], [0., 1, 0]]
    two = [[0, 1, 2], [3, 4, 5]]
    fixtures = [
        ("separate", base+[[0, 0, 1], [1, 0, 1], [0, 1, 1]], two, 0),
        ("crossing", base+[[.25, .25, -1], [.25, .25, 1], [.75, .25, 0]], two, 1),
        ("coplanar_contained", base+[[.1, .1, 0], [.2, .1, 0], [.1, .2, 0]], two, 1),
        ("coplanar_shared_vertex_overlap", base+[[.1, .1, 0], [.2, .1, 0]], [[0, 1, 2], [0, 3, 4]], 1),
        ("manifold_tetrahedron", base+[[0, 0, 1]], [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]], 0)]
    rows = []
    for name, xyz, faces, expected in fixtures:
        p, f = np.array(xyz, dtype=np.float64), np.array(faces, dtype=np.int64)
        old_p, old_f = p.copy(), f.copy()
        result = cgal.remesh_self_intersections(p, f, detect_only=True, first_only=False,
            stitch_all=False, cutoff=100001)
        unchanged = np.array_equal(p, old_p) and np.array_equal(f, old_f)
        rows.append(dict(name=name, expected_pairs=expected, observed_pairs=len(result[2]),
            input_arrays_unchanged=unchanged))
        if len(result[2]) != expected or not unchanged:
            raise ValueError("Global intersection known-result fixture failed: " + name)
    return rows


def audit_intersections(report, p, f):
    import igl
    import igl.copyleft.cgal as cgal
    if importlib.metadata.version("libigl") != "2.6.3":
        raise ValueError("Observed pinned libigl 2.6.3 runtime required")
    report["runtime"]["libigl_version"] = importlib.metadata.version("libigl")
    report["runtime"]["cgal_wrapper_sha256"] = sha(Path(cgal.__file__))
    report["runtime"]["igl_binary_modules"] = {str(q.relative_to(Path(igl.__file__).parent)): sha(q)
        for q in Path(igl.__file__).parent.rglob("*.so")}
    report["known_result_fixtures"] = intersection_fixtures(cgal)
    vertex_manifold = np.asarray(igl.is_vertex_manifold(f), dtype=bool)
    report["nonmanifold_vertex_count"] = int(np.sum(~vertex_manifold))
    cap = 100001
    result = cgal.remesh_self_intersections(p, f, detect_only=True, first_only=False,
        stitch_all=False, cutoff=cap)
    pairs = np.asarray(result[2], dtype=np.int64).reshape(-1, 2)
    report["intersections"] = dict(pair_count=len(pairs), pair_cap=cap, complete=len(pairs) < cap,
        detect_only=True, first_only=False, stitch_all=False, pairs=pairs.tolist())
    report["gate_passed"] = len(pairs) == 0 and len(pairs) < cap and report["nonmanifold_vertex_count"] == 0


def audit_distance(report, p, f):
    sys.path.insert(0, str(WHOLEBODY))
    from run_bounded_chamfer import distance_bounds
    import cascading_upper_bounds as cub
    reference = np.load(REFERENCE)
    q, g = reference["points_mm"], reference["triangles"]
    report["runtime"]["cascading_upper_bounds_version"] = importlib.metadata.version("cascading-upper-bounds")
    report["runtime"]["cub_python_module_sha256"] = sha(Path(cub.__file__))
    report["runtime"]["cub_binary_modules"] = {str(q.relative_to(Path(cub.__file__).parent)): sha(q)
        for q in Path(cub.__file__).parent.rglob("*.so")}
    report["distance"] = distance_bounds(q, g, p, f, tolerance=1e-4)
    report["gate_passed"] = bool(report["distance"]["completed"] and report["distance"]["upper"] <= .25)


def worker(args):
    receipt = json.loads((args.output / "receipt.json").read_text())
    if (receipt["status"] != "running" or receipt["worker_args"] != sys.argv[1:]
            or receipt["source_sha256"] != sha(Path(__file__))
            or receipt["source_sha256"] != sha(args.output / "source-executed.py")):
        raise ValueError("Fresh bound audit controller required")
    with (args.output / "worker-claimed.json").open("x") as stream:
        json.dump({"pid": os.getpid()}, stream)
    verify = lambda: all(sha(ROOT / p) == h for p, h in receipt["input_hashes"].items())
    if not verify():
        raise ValueError("Audit inputs changed")
    signal.alarm(300); started = time.monotonic()
    arrays = np.load(SURFACE); p, f = arrays["points_mm"], arrays["triangles"]
    p_hash, f_hash = array_sha(p), array_sha(f)
    report = dict(status="running", kind=args.kind, gate_passed=False,
        runtime=dict(python=sys.version, numpy=np.__version__, machine=platform.machine()),
        engineering_accepted=False, solver_admission_established=False,
        thermal_performance_validated=False, manufacturing_authorized=False)
    try:
        if args.kind == "intersections":
            audit_intersections(report, p, f)
        else:
            audit_distance(report, p, f)
        report["status"] = "independent_geometric_subgate_passed" if report["gate_passed"] else "rejected_outputs_preserved"
    except Exception as exc:
        report.update(status="failed_outputs_preserved", error=type(exc).__name__+": "+str(exc), gate_passed=False)
    finally:
        report.update(wall_s=time.monotonic()-started, bound_inputs_unchanged=verify(),
            candidate_arrays_unchanged=p_hash == array_sha(p) and f_hash == array_sha(f))
        if not report["bound_inputs_unchanged"] or not report["candidate_arrays_unchanged"]:
            report.update(status="failed_outputs_preserved", gate_passed=False, error="Audit changed or lost its bound inputs")
        save(args.output / "worker-report.json", report); signal.alarm(0)
    return 0 if report["gate_passed"] else 2


def run(args):
    from cancel_analysis_flaps import CONTRACT_SHA256
    if sha(CONTRACT) != CONTRACT_SHA256:
        raise ValueError("Frozen representation contract changed")
    cancellation = json.loads(CANCELLATION.read_text())
    if cancellation["output_hashes"]["analysis-surface.npz"] != sha(SURFACE):
        raise ValueError("Candidate differs from exact cancellation receipt")
    new_output(args.output)
    worker_args = ["--worker", "--kind", args.kind, "--output", str(args.output.resolve())]
    source = Path(__file__).resolve()
    paths = [source, SURFACE, REFERENCE, CANCELLATION, CONTRACT, FAMILY / "source/mesh_head.py"]
    paths += [WHOLEBODY / name for name in ("run_bounded_chamfer.py", "trial_meshers_2026.py", "run_local_surface_trial.py")]
    pins = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    if args.kind == "distance":
        command = [str(DISTANCE_PYTHON), str(source), *worker_args]
    else:
        command = ["docker", "run", "--rm", "--cidfile", str((args.output / "container-id").resolve()),
            "--network", "none", "--read-only", "--cpus", "2", "--memory", "4g", "--memory-swap", "4g",
            "--mount", f"type=bind,src={ROOT},dst={ROOT},readonly",
            "--mount", f"type=bind,src={args.output.resolve()},dst={args.output.resolve()}",
            "--workdir", str(ROOT), IMAGE, "python", "-B", str(source), *worker_args]
    (args.output / "source-executed.py").write_bytes(source.read_bytes())
    receipt = dict(status="running", kind=args.kind, source_sha256=sha(source),
        input_hashes=pins, worker_args=worker_args, command=command, native_deadline_s=300,
        docker_image=IMAGE if args.kind == "intersections" else None, engineering_accepted=False)
    save(args.output / "receipt.json", receipt); started = time.monotonic()
    environment = dict(os.environ)
    environment.update({name: "2" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")})
    with (args.output / "native.log").open("x") as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
            start_new_session=True, env=environment)
        try:
            process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            if args.kind == "intersections" and (args.output / "container-id").exists():
                subprocess.run(["docker", "kill", (args.output / "container-id").read_text().strip()],
                    stdout=stream, stderr=subprocess.STDOUT, timeout=20)
            os.killpg(process.pid, signal.SIGKILL); process.wait()
            receipt["status"] = "timed_out_native_process_killed_outputs_preserved"
    receipt.update(returncode=process.returncode, wall_s=time.monotonic()-started,
        native_log_sha256=sha(args.output / "native.log"))
    report = args.output / "worker-report.json"
    if report.exists():
        receipt.update(worker_report=json.loads(report.read_text()), worker_report_sha256=sha(report))
    if receipt["status"] == "running":
        receipt["status"] = "independent_subgate_passed" if process.returncode == 0 else "rejected_outputs_preserved"
    save(args.output / "receipt.json", receipt)
    print(json.dumps({k: receipt[k] for k in ("status", "kind", "returncode", "wall_s")}), flush=True)
    return 0 if process.returncode == 0 else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kind", choices=("distance", "intersections"), required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    raise SystemExit(worker(args) if args.worker else run(args))
