"""One admission-guarded HXT volume/quality trial of the retained quality surface."""
import argparse
import json
import math
import os
from pathlib import Path
import platform
import re
import signal
import stat
import subprocess
import sys
import threading
import time

import numpy as np

import audit_quality_head
import audit_quality_patch
import mesh_head
import prepare_head_analysis
from mesh_head import (ROOT, FAMILY, array_sha, distribution, new_output, save, sha,
                       surface_roundtrip, tetra_boundary, tetra_volumes, volume_arrays)

CANDIDATE = ROOT / "work/962-engineering/quality-patch-head-001/native/quality-candidate.bin"
CANDIDATE_SHA = "7f0d96988684f7d36dab8f65c5b63b1919c2c2121768cf9caec466867a5c2b43"
CANDIDATE_VOLUME = 915458.4757034747
OUTPUT = ROOT / "work/962-engineering/quality-volume-hxt-001"
GATES = {"distance", "features", "topology", "global_intersections", "fixed_face_necessary_quality"}
DEADLINE = 300
RSS_STOP = 8 * 1024**3
OPTIONS = {**mesh_head.OPTIONS, "Mesh.Algorithm3D": 10, "Mesh.Optimize": 1,
           "General.NumThreads": 2, "Mesh.MaxNumThreads3D": 2}
RUNTIME_HASHES = dict(gmsh_module="f4b0935cebde899750293d87a643090e5ea33c9b18d249267f507db68a0e01c3",
                      libgmsh="def0f5c10988a986e5e879b3db9669d8fe016a81e2d994bbaf2b8497c6b8a58a")


def require_admission(path, expected_sha):
    if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha) or sha(path) != expected_sha:
        raise ValueError("Exact root surface-admission receipt hash required")
    receipt = json.loads(path.read_text())
    volume = receipt.get("candidate_volume_mm3")
    gates = receipt.get("gates")
    pins = receipt.get("input_hashes")
    if (receipt.get("candidate_sha256") != CANDIDATE_SHA or receipt.get("length_unit") != "mm"
            or type(volume) not in (int, float) or not math.isfinite(volume)
            or volume != CANDIDATE_VOLUME or receipt.get("numerical_surface_admitted") is not True
            or not isinstance(gates, dict) or set(gates) != GATES
            or any(type(value) is not bool or value is not True for value in gates.values())
            or not isinstance(pins, dict) or not pins):
        raise ValueError("Every declared numerical surface-admission gate must explicitly pass")
    for name, digest in pins.items():
        if not isinstance(name, str):
            raise ValueError("Relative bound evidence paths required")
        relative = Path(name)
        target = ROOT / relative
        if (relative.is_absolute() or ".." in relative.parts
                or not target.resolve().is_relative_to(ROOT.resolve())
                or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or sha(target) != digest):
            raise ValueError("Bound surface-admission evidence changed")
    if sha(CANDIDATE) != CANDIDATE_SHA:
        raise ValueError("Admitted candidate bytes changed")
    return receipt


def source_files():
    return [Path(__file__).resolve(), *(Path(module.__file__).resolve() for module in
            [mesh_head, audit_quality_head, audit_quality_patch, prepare_head_analysis])]


def claim_worker(args):
    expected = {"receipt.json", "native.log", "source-snapshots", "surface-admission.json"}
    if not args.output.is_dir() or {p.name for p in args.output.iterdir()} != expected:
        raise ValueError("Fresh controller-owned worker directory required")
    receipt = json.loads((args.output / "receipt.json").read_text())
    if (receipt["status"] != "running" or receipt["command"] != [sys.executable, *sys.argv]
            or receipt["options"] != OPTIONS or receipt["native_deadline_s"] != DEADLINE
            or receipt["sampled_RSS_stop_bytes"] != RSS_STOP
            or receipt["admission_sha256"] != args.admission_sha256
            or sha(args.output / "surface-admission.json") != args.admission_sha256):
        raise ValueError("Controller, options or admission binding changed")
    for name, digest in receipt["source_sha256s"].items():
        if sha(ROOT / name) != digest or sha(args.output / "source-snapshots" / Path(name).name) != digest:
            raise ValueError("Executed source or frozen snapshot changed")
    require_admission(args.admission, args.admission_sha256)
    with (args.output / "worker-claimed.json").open("x") as stream:
        json.dump(dict(pid=os.getpid()), stream)
    return receipt


def tagged_volume(gmsh):
    coordinates, cells, element_tags, connectivity = volume_arrays(gmsh)
    node_tags = np.sort(np.asarray(gmsh.model.mesh.getNodes()[0]))
    order = np.argsort(element_tags)
    return coordinates, cells, node_tags, np.asarray(element_tags)[order], connectivity[order]


def internal_face_orientation(cells):
    faces = np.concatenate([cells[:, [0, 2, 1]], cells[:, [0, 1, 3]],
                            cells[:, [1, 2, 3]], cells[:, [2, 0, 3]]])
    _, inverse, counts = np.unique(np.sort(faces, axis=1), axis=0,
                                    return_inverse=True, return_counts=True)
    odd = ((faces[:, 0] > faces[:, 1]) ^ (faces[:, 0] > faces[:, 2])
           ^ (faces[:, 1] > faces[:, 2]))
    balance = np.zeros(len(counts), dtype=np.int64)
    np.add.at(balance, inverse, np.where(odd, -1, 1))
    if np.any(counts > 2) or np.any(balance[counts == 2] != 0):
        raise ValueError("Internal tetrahedron faces must have exactly opposite orientations")
    return dict(internal_faces=int(np.count_nonzero(counts == 2)),
                same_oriented_internal_faces=0, exact_internal_orientation_balance=True)


def matching_mesh(path, expected_digest):
    if not isinstance(expected_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
        return False
    try:
        metadata = path.lstat()
        return (stat.S_ISREG(metadata.st_mode) and metadata.st_size > 0
                and sha(path) == expected_digest)
    except OSError:
        return False


def worker(args):
    launch = claim_worker(args)
    report = dict(status="running", stage="checking_runtime", options=OPTIONS,
        qualification=dict(geometric_volume_gate_passed=False, mesh_convergence_established=False,
            thermal_resolution_established=False, engineering_accepted=False,
            thermal_performance_validated=False, strength_validated=False, manufacturing_authorized=False))
    checkpoint = lambda: save(args.output / "worker-report.json", report)
    initialized = False
    mesh_path = args.output / "head-volume.msh"
    started = time.monotonic()
    try:
        import gmsh
        runtime = dict(python=sys.version, executable=sys.executable,
            executable_sha256=sha(Path(sys.executable).resolve()), numpy=np.__version__,
            machine=platform.machine(), gmsh=gmsh.__version__,
            gmsh_module_sha256=sha(Path(gmsh.__file__)), libgmsh_sha256=sha(Path(gmsh.lib._name)))
        report["runtime"] = runtime
        if (runtime["machine"] != "arm64" or runtime["gmsh"] != "4.15.2"
                or runtime["gmsh_module_sha256"] != RUNTIME_HASHES["gmsh_module"]
                or runtime["libgmsh_sha256"] != RUNTIME_HASHES["libgmsh"]):
            raise ValueError("Observed native ARM64 Gmsh4.15.2 runtime required")
        points, faces = audit_quality_head.read(CANDIDATE)
        points, faces = np.array(points, dtype=np.float64), np.array(faces, dtype=np.int64)
        if (len(points), len(faces)) != (902145, 1804706):
            raise ValueError("Admitted candidate counts changed")
        surface = prepare_head_analysis.validate_surface(points, faces)
        report.update(surface=surface, candidate_sha256=CANDIDATE_SHA,
            candidate_volume_reference_mm3=CANDIDATE_VOLUME, volume_relative_bookkeeping_bound=1e-6,
            bookkeeping_bound_is_manufacturing_tolerance=False)
        if abs(surface["signed_volume_mm3"] / CANDIDATE_VOLUME - 1) > 1e-6:
            raise ValueError("Candidate volume numerical bookkeeping failed")
        gmsh.initialize([], readConfigFiles=False, run=False); initialized = True
        gmsh.option.setNumber("General.Terminal", 1); gmsh.logger.start()
        for key, value in OPTIONS.items():
            gmsh.option.setNumber(key, value)
        report["standard_optimization_threshold"] = gmsh.option.getNumber("Mesh.OptimizeThreshold")
        gmsh.model.add("962_admitted_quality_surface_volume_trial")
        gmsh.model.addDiscreteEntity(2, 1)
        gmsh.model.mesh.addNodes(2, 1, np.arange(1, len(points)+1, dtype=np.uint64), points.ravel())
        gmsh.model.mesh.addElementsByType(1, 2, np.arange(1, len(faces)+1, dtype=np.uint64),
                                          (faces+1).astype(np.uint64).ravel())
        report["surface_import"] = surface_roundtrip(gmsh, points, faces)
        gmsh.model.geo.addSurfaceLoop([1], 1); gmsh.model.geo.addVolume([1], 1)
        gmsh.model.geo.synchronize()
        report.update(stage="generating_and_standard_optimizing_HXT"); checkpoint()
        gmsh.model.mesh.generate(3)
        gmsh.write(str(mesh_path))
        report.update(mesh_sha256=sha(mesh_path), mesh_bytes=mesh_path.stat().st_size,
                      stage="auditing_all_linear_tetrahedra"); checkpoint()
        report["surface_after_meshing"] = surface_roundtrip(gmsh, points, faces, exact_tagged_order=False)
        coordinates, cells, node_tags, tet_tags, tet_nodes = tagged_volume(gmsh)
        referenced = np.unique(tet_nodes)
        interior = referenced[~np.isin(referenced, np.arange(1, len(points)+1, dtype=np.uint64))]
        report.update(tetrahedra=len(cells), total_mesh_nodes=len(coordinates),
            retained_boundary_nodes=len(points), tetra_referenced_nodes=len(referenced),
            tetra_referenced_interior_nodes=len(interior), unreferenced_mesh_nodes=len(node_tags)-len(referenced),
            interior_node_count_establishes_thermal_resolution=False)
        quality = {name: distribution(gmsh.model.mesh.getElementQualities(tet_tags, measure))
            for name, measure in [("minimum_jacobian", "minDetJac"),
                                  ("native_volume_mm3", "volume"), ("minimum_SICN", "minSICN")]}
        signed = tetra_volumes(coordinates, cells)
        quality["independent_signed_volume_mm3"] = distribution(signed)
        report.update(quality=quality, summed_tetra_volume_mm3=math.fsum(signed))
        report["volume_relative_error"] = abs(report["summed_tetra_volume_mm3"] / CANDIDATE_VOLUME - 1)
        source_indices = np.searchsorted(node_tags, faces+1)
        report["actual_tetra_boundary"] = tetra_boundary(cells, source_indices)
        report["internal_tetra_face_orientation"] = internal_face_orientation(cells)
        checkpoint()
        report.update(stage="reading_back_the_single_saved_mesh"); checkpoint()
        gmsh.clear(); gmsh.open(str(mesh_path))
        report["saved_surface"] = surface_roundtrip(gmsh, points, faces, exact_tagged_order=False)
        q, _, nt, et, en = tagged_volume(gmsh)
        if (not np.array_equal(q, coordinates) or not np.array_equal(nt, node_tags)
                or not np.array_equal(et, tet_tags) or not np.array_equal(en, tet_nodes)):
            raise ValueError("Saved mesh tagged coordinates or tetra connectivity changed")
        if sha(mesh_path) != report["mesh_sha256"]:
            raise ValueError("Saved mesh bytes changed during readback")
        report.update(saved_mesh_identity_exact=True, sorted_node_tags_sha256=array_sha(node_tags),
            sorted_coordinates_sha256=array_sha(coordinates), sorted_tetra_tags_sha256=array_sha(tet_tags),
            tagged_tetra_connectivity_sha256=array_sha(tet_nodes))
        if any(q["nonpositive_count"] for q in quality.values()) or quality["minimum_SICN"]["minimum"] < .1:
            raise ValueError("All Jacobians/volumes must be positive and actual minimum SICN at least0.1")
        if report["volume_relative_error"] > 1e-6:
            raise ValueError("Candidate-relative tetra volume bookkeeping exceeds1e-6")
        report.update(status="completed_geometric_volume_quality_only", stage="finished")
        report["qualification"]["geometric_volume_gate_passed"] = True
    except Exception as exc:
        report.update(status="failed_outputs_preserved", error=type(exc).__name__+": "+str(exc))
    finally:
        if initialized:
            report["gmsh_warnings_errors"] = [s for s in gmsh.logger.get() if s.startswith(("Warning", "Error"))]
            gmsh.logger.stop(); gmsh.finalize()
        try:
            require_admission(args.admission, args.admission_sha256)
            report["bound_inputs_unchanged"] = (sha(args.output / "surface-admission.json") == args.admission_sha256
                and all(sha(ROOT/p) == h and sha(args.output / "source-snapshots" / Path(p).name) == h
                        for p, h in launch["source_sha256s"].items()))
        except Exception:
            report["bound_inputs_unchanged"] = False
        if not report["bound_inputs_unchanged"]:
            report.update(status="failed_bound_input_drift")
            report["qualification"]["geometric_volume_gate_passed"] = False
        if report["qualification"]["geometric_volume_gate_passed"] and sha(mesh_path) != report["mesh_sha256"]:
            report.update(status="failed_saved_mesh_drift")
            report["qualification"]["geometric_volume_gate_passed"] = False
        report["worker_wall_s"] = time.monotonic()-started; checkpoint()
    return 0 if report["status"] == "completed_geometric_volume_quality_only" else 2


def run(args):
    require_admission(args.admission, args.admission_sha256)
    if args.output.resolve() != OUTPUT.resolve():
        raise ValueError("Only the single declared fresh output is permitted")
    new_output(args.output)
    snapshots = args.output / "source-snapshots"; snapshots.mkdir()
    pins = {str(p.relative_to(ROOT)): sha(p) for p in source_files()}
    for name in pins:
        (snapshots / Path(name).name).write_bytes((ROOT/name).read_bytes())
    (args.output / "surface-admission.json").write_bytes(args.admission.read_bytes())
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--output", str(args.output.resolve()),
               "--admission", str(args.admission.resolve()), "--admission-sha256", args.admission_sha256]
    report = dict(status="running", command=command, source_sha256s=pins, options=OPTIONS,
        admission_sha256=args.admission_sha256, native_deadline_s=DEADLINE,
        sampled_RSS_stop_bytes=RSS_STOP, sampled_RSS_is_not_a_hard_peak_limit=True,
        hard_address_space_limit_applied=False, hard_OS_CPU_quota_applied=False,
        expected_output_disk_bytes_at_most=1024**3, automatic_retry=False,
        sampled_output_bytes_exclude_atomic_report_temporary_files=True,
        geometric_volume_gate_passed=False, engineering_accepted=False, manufacturing_authorized=False)
    save(args.output / "receipt.json", report)
    started = time.monotonic(); stopped = {"reason": None}; samples = []; stop_lock = threading.Lock()
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C", "PYTHONUTF8": "1",
           "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2", "PYTHONDONTWRITEBYTECODE": "1"}
    with (args.output / "native.log").open("x") as log:
        process = watchdog = None
        def stop(reason):
            with stop_lock:
                if stopped["reason"] is None:
                    stopped["reason"] = reason
                    if process is not None:
                        try: os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
        try:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
            watchdog = threading.Timer(DEADLINE, lambda: stop("native_deadline"))
            watchdog.daemon = True; watchdog.start()
            while process.poll() is None:
                try:
                    p = subprocess.run(["ps", "-o", "rss=", "-p", str(process.pid)], capture_output=True, text=True, timeout=2)
                    if process.poll() is not None: break
                    rss = int(p.stdout.strip()) * 1024
                    disk = sum(p.stat().st_size for p in args.output.rglob("*")
                               if not p.name.endswith(".tmp") and p.is_file())
                    samples.append(dict(wall_s=time.monotonic()-started, RSS_bytes=rss, output_bytes=disk))
                    if rss >= RSS_STOP: stop("sampled_RSS_stop")
                    if disk >= 1024**3: stop("sampled_output_disk_stop")
                except (OSError, ValueError, subprocess.SubprocessError):
                    if process.poll() is None: stop("RSS_observation_failed")
                try: process.wait(timeout=.5)
                except subprocess.TimeoutExpired: pass
        finally:
            if watchdog is not None: watchdog.cancel()
            if process is not None:
                if process.poll() is None: stop("controller_interrupted")
                process.wait()
    report.update(returncode=process.returncode, native_process_window_s=time.monotonic()-started,
        stop_reason=stopped["reason"], RSS_samples=samples,
        max_observed_RSS_bytes=max((s["RSS_bytes"] for s in samples), default=None),
        native_log_sha256=sha(args.output / "native.log"))
    path = args.output / "worker-report.json"
    if path.exists(): report.update(worker_report_sha256=sha(path), worker_report=json.loads(path.read_text()))
    try:
        require_admission(args.admission, args.admission_sha256)
        report["bound_inputs_unchanged"] = (sha(args.output / "surface-admission.json") == args.admission_sha256
            and all(sha(ROOT/p) == h and sha(snapshots / Path(p).name) == h for p, h in pins.items()))
    except Exception:
        report["bound_inputs_unchanged"] = False
    mesh = args.output / "head-volume.msh"
    actual = report.get("worker_report", {})
    mesh_matches_worker = matching_mesh(mesh, actual.get("mesh_sha256"))
    if mesh_matches_worker:
        report.update(mesh_sha256=sha(mesh), mesh_bytes=mesh.stat().st_size)
    passed = (process.returncode == 0 and stopped["reason"] is None and report["bound_inputs_unchanged"]
              and actual.get("status") == "completed_geometric_volume_quality_only"
              and actual.get("qualification", {}).get("geometric_volume_gate_passed") is True
              and mesh_matches_worker and report.get("mesh_sha256") == actual.get("mesh_sha256"))
    report.update(status="completed_geometric_volume_quality_only" if passed else "stopped_or_rejected_outputs_preserved",
                  geometric_volume_gate_passed=passed)
    save(args.output / "receipt.json", report)
    print(json.dumps({k:report.get(k) for k in ["status", "returncode", "stop_reason", "native_process_window_s"]}))
    return 0 if passed else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--admission-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    raise SystemExit(worker(args) if args.worker else run(args))
