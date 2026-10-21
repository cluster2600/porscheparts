"""One bound topology/intersection audit; never distance or solver admission."""
import argparse
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

import numpy as np

from audit_envelope_surface import audit_intersections
from audit_quality_head import read
from mesh_head import ROOT, FAMILY, array_sha, new_output, sha
from prepare_head_analysis import validate_surface

CONTRACT = FAMILY / "engineering/analysis-quality-topology-contract.json"
OUTPUT = ROOT / "work/962-engineering/quality-patch-topology-001"
IMAGE = "sha256:3ccaf5701c7c9add59eda6e8db918106fc8d51f4c2ef5b148d8079262861c7e1"
CANDIDATE = ROOT / "work/962-engineering/quality-patch-head-001/native/quality-candidate.bin"
CANDIDATE_SHA = "7f0d96988684f7d36dab8f65c5b63b1919c2c2121768cf9caec466867a5c2b43"
RESOURCES = dict(cpus=2, memory_bytes=4294967296, memory_swap_bytes=4294967296,
                 swap_bytes=0, hard_wall_seconds=300, network="none")


def write_new(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def verify(contract):
    if (contract["schema"] != "962-quality-topology-audit/v1"
            or contract["resources"] != RESOURCES or contract["image_id"] != IMAGE
            or contract["candidate"] != str(CANDIDATE.relative_to(ROOT))
            or contract["input_hashes"].get(contract["candidate"]) != CANDIDATE_SHA
            or contract["expected_counts"] != dict(vertices=902145, triangles=1804706)
            or any(v is not False for v in contract["qualification"].values())):
        raise ValueError("Frozen candidate, resources or scope changed")
    for name, digest in contract["input_hashes"].items():
        if sha(ROOT / name) != digest:
            raise ValueError("Bound audit input changed: " + name)


def require_topology(surface, components):
    """Keep component, orientation, Euler and volume checks independent."""
    if type(components) is not int or components != 1:
        raise ValueError("One connected surface component required")
    for key in ("boundary_edges", "nonmanifold_edges", "orientation_imbalanced_edges"):
        if type(surface.get(key)) is not int or surface[key] != 0:
            raise ValueError("Closed oriented edge-manifold surface required")
    if type(surface.get("euler_characteristic")) is not int or surface["euler_characteristic"] != -208:
        raise ValueError("Original Euler characteristic -208 required")
    volume = surface.get("signed_volume_mm3")
    if type(volume) not in (int, float) or not math.isfinite(volume) or volume <= 0:
        raise ValueError("Finite positive signed enclosed volume required")


def components(igl, faces):
    labels = np.asarray(igl.facet_components(faces)).reshape(-1)
    if len(labels) != len(faces) or not np.issubdtype(labels.dtype, np.integer) or np.any(labels < 0):
        raise ValueError("Complete integer facet-component labels required")
    return int(len(np.unique(labels)))


def worker(output):
    expected = {"running-receipt.json", "frozen-contract.json", "source-snapshots", "native.log"}
    if not output.is_dir() or {p.name for p in output.iterdir()} != expected:
        raise ValueError("Fresh controller-owned audit directory required")
    receipt = json.loads((output / "running-receipt.json").read_text())
    contract = json.loads((output / "frozen-contract.json").read_text())
    if (receipt["worker_args"] != sys.argv[1:]
            or receipt["source_sha256"] != sha(Path(__file__))
            or receipt["contract_sha256"] != sha(output / "frozen-contract.json")
            or receipt["contract_sha256"] != sha(CONTRACT)):
        raise ValueError("Bound controller/source/contract identity required")
    for name, digest in receipt["source_snapshots"].items():
        if sha(output / name) != digest:
            raise ValueError("Frozen source snapshot changed")
    for name, digest in contract["input_hashes"].items():
        if name.endswith(".py") and sha(output / "source-snapshots" / Path(name).name) != digest:
            raise ValueError("Executed dependency differs from its bound source snapshot")
    verify(contract)
    write_new(output / "worker-claimed.json", dict(pid=os.getpid()))
    signal.alarm(300)
    start = time.monotonic()
    report = dict(status="running", gate_passed=False, topology_gate_passed=False,
        solver_admission_established=False, engineering_accepted=False,
        independent_distance_completed=False, feature_channel_BCC_review_completed=False,
        thermal_performance_validated=False, strength_validated=False, manufacturing_authorized=False,
        runtime=dict(python=sys.version, executable=sys.executable,
            executable_sha256=sha(Path(sys.executable).resolve()), numpy=np.__version__, machine=platform.machine()))
    p_hash = f_hash = None
    try:
        import igl
        import igl.copyleft.cgal as cgal
        runtime = dict(libigl_version=importlib.metadata.version("libigl"),
            cgal_wrapper_sha256=sha(Path(cgal.__file__)),
            igl_binary_modules={str(q.relative_to(Path(igl.__file__).parent)): sha(q)
                for q in Path(igl.__file__).parent.rglob("*.so")})
        if runtime != contract["pinned_intersection_runtime"] or platform.machine() != "aarch64":
            raise ValueError("Pinned ARM64 libigl/native module identity changed")
        report["runtime"].update(runtime)
        p, f = read(CANDIDATE)
        p, f = np.array(p, dtype=np.float64), np.array(f, dtype=np.int64)
        p_hash, f_hash = array_sha(p), array_sha(f)
        surface = validate_surface(p, f)
        if any(surface[key] != value for key, value in contract["expected_counts"].items()):
            raise ValueError("Candidate coordinate/triangle counts changed")
        tetra = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]], dtype=np.int64)
        component_fixtures = [components(igl, tetra), components(igl, np.concatenate((tetra, tetra + 4)))]
        if component_fixtures != [1, 2]:
            raise ValueError("Known connected/disconnected facet fixtures failed")
        count = components(igl, f)
        report.update(surface=surface, connected_components=count, component_fixture_results=component_fixtures)
        require_topology(surface, count)
        report["topology_gate_passed"] = True
        audit_intersections(report, p, f)
        report["status"] = "topology_and_global_intersection_subgates_passed" if report["gate_passed"] else "rejected_outputs_preserved"
    except Exception as exc:
        report.update(status="failed_or_rejected_outputs_preserved", error=type(exc).__name__ + ": " + str(exc), gate_passed=False)
    finally:
        try:
            verify(contract)
            report["bound_inputs_unchanged"] = sha(CONTRACT) == receipt["contract_sha256"]
        except Exception:
            report["bound_inputs_unchanged"] = False
        report["candidate_arrays_unchanged"] = p_hash is not None and p_hash == array_sha(p) and f_hash == array_sha(f)
        if not report["bound_inputs_unchanged"] or not report["candidate_arrays_unchanged"]:
            report.update(status="failed_bound_input_or_array_drift", gate_passed=False)
        report["wall_seconds"] = time.monotonic() - start
        write_new(output / "worker-report.json", report)
        signal.alarm(0)
    return 0 if report["gate_passed"] else 2


def run(output):
    if output.resolve() != OUTPUT.resolve():
        raise ValueError("Only the declared fresh audit case is authorized")
    contract = json.loads(CONTRACT.read_text())
    verify(contract)
    new_output(output)
    (output / "frozen-contract.json").write_bytes(CONTRACT.read_bytes())
    snapshot = output / "source-snapshots"
    snapshot.mkdir()
    for name in contract["input_hashes"]:
        if name.endswith(".py"):
            (snapshot / Path(name).name).write_bytes((ROOT / name).read_bytes())
    snapshots = {str(p.relative_to(output)): sha(p) for p in snapshot.iterdir()}
    args = ["--worker", "--output", str(output.resolve())]
    name = "962-quality-patch-topology-001"
    command = ["docker", "run", "--pull=never", "--name", name, "--network", "none", "--read-only",
        "--cpus", "2", "--memory", "4294967296", "--memory-swap", "4294967296",
        "-e", "OMP_NUM_THREADS=2", "-e", "OPENBLAS_NUM_THREADS=2", "-e", "MKL_NUM_THREADS=2",
        "--mount", f"type=bind,src={ROOT},dst={ROOT},readonly",
        "--mount", f"type=bind,src={output.resolve()},dst={output.resolve()}",
        "--workdir", str(ROOT), "--entrypoint", "python3", IMAGE, "-B", str(Path(__file__).resolve()), *args]
    receipt = dict(status="running", source_sha256=sha(Path(__file__)), contract_sha256=sha(CONTRACT),
        source_snapshots=snapshots, worker_args=args, command=command, resources=RESOURCES,
        solver_admission_established=False, engineering_accepted=False, manufacturing_authorized=False)
    write_new(output / "running-receipt.json", receipt)
    start = time.monotonic()
    with (output / "native.log").open("x") as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)
        deadline = False
        try:
            process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            deadline = True
            subprocess.run(["docker", "kill", name], stdout=stream, stderr=subprocess.STDOUT, timeout=10)
            process.wait(timeout=10)
    state = subprocess.run(["docker", "inspect", name, "--format", "{{json .State}}"], capture_output=True, text=True, timeout=10)
    report = output / "worker-report.json"
    receipt.update(returncode=process.returncode, deadline_exceeded=deadline,
        wall_seconds=time.monotonic()-start, container_state=json.loads(state.stdout) if state.returncode == 0 else state.stderr,
        native_log_sha256=sha(output / "native.log"))
    if report.exists():
        receipt.update(worker_report=json.loads(report.read_text()), worker_report_sha256=sha(report))
    passed = (not deadline and process.returncode == 0 and isinstance(receipt["container_state"], dict)
        and receipt["container_state"].get("OOMKilled") is False
        and receipt.get("worker_report", {}).get("gate_passed") is True)
    receipt["status"] = "topology_intersection_subgates_passed_no_solver_admission" if passed else "failed_or_rejected_outputs_preserved"
    write_new(output / "receipt.json", receipt)
    if isinstance(receipt["container_state"], dict) and receipt["container_state"].get("Running") is False:
        cleaned = subprocess.run(["docker", "rm", name], capture_output=True, text=True, timeout=10)
        write_new(output / "owned-container-cleanup.json", dict(returncode=cleaned.returncode, stdout=cleaned.stdout, stderr=cleaned.stderr))
    print(json.dumps({k: receipt[k] for k in ("status", "returncode", "deadline_exceeded", "wall_seconds")}), flush=True)
    return 0 if passed else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    raise SystemExit(worker(args.output) if args.worker else run(args.output))
