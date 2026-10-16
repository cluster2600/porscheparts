"""Two bounded software-only cube fixtures; no head geometry is read or meshed."""
import argparse
import json
import math
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import threading
import time

import numpy as np
import mesh_head as mesh
import mesh_quality_head as quality

ROOT = mesh.ROOT
OUTPUT = ROOT / "work/962-engineering/hxt-size-cap-fixture-001"
RUNTIME = Path(sys.prefix)
RUNTIME_FILES = {
    str(RUNTIME / "bin/python"): "72956ad35cff7691dfed9e04c9593de825ffd5b2fa7e8bc9ae96ce9a1af65621",
    str(RUNTIME / "lib/python3.10/site-packages/gmsh.py"): "f4b0935cebde899750293d87a643090e5ea33c9b18d249267f507db68a0e01c3",
    str(RUNTIME / "lib/libgmsh.4.15.dylib"): "def0f5c10988a986e5e879b3db9669d8fe016a81e2d994bbaf2b8497c6b8a58a"}
CASES = {"uncapped": 1e22, "capped-1p75": 1.75}
DEADLINE = 30
RSS_STOP = 1024**3
DISK_STOP = 16 * 1024**2


def cube():
    points = np.array([[0,0,0], [7,0,0], [7,7,0], [0,7,0],
                       [0,0,7], [7,0,7], [7,7,7], [0,7,7]], dtype="<f8")
    faces = np.array([[0,2,1], [0,3,2], [4,5,6], [4,6,7],
                      [0,1,5], [0,5,4], [1,2,6], [1,6,5],
                      [2,3,7], [2,7,6], [3,0,4], [3,4,7]], dtype="<i8")
    triangles = points[faces]
    normals = np.cross(triangles[:,1]-triangles[:,0], triangles[:,2]-triangles[:,0])
    assert np.all(np.einsum("ij,ij->i", normals, triangles.mean(axis=1)-3.5) > 0)
    assert math.fsum(np.einsum("ij,ij->i", triangles[:,0],
                     np.cross(triangles[:,1], triangles[:,2]))) / 6 == 343
    assert mesh.topology(faces)["unique_edges"] == 18
    return points, faces


def options(case):
    return {**mesh.OPTIONS, "Mesh.Algorithm3D": 10, "Mesh.Optimize": 0,
            "Mesh.MeshSizeMax": CASES[case], "Mesh.MeshSizeMin": 0, "Mesh.MeshSizeFactor": 1}


def source_files():
    return [Path(__file__).resolve(), *quality.source_files()]


def specification():
    points, faces = cube()
    return dict(schema="962-HXT-size-cap-software-fixture/v1", length_unit="mm",
        native_execution_authorized_by_contract=False,
        purpose="Software insertion-sizing check, not a head dimension or engineering validation",
        source_basis=dict(release_url="https://gmsh.info/src/gmsh-4.15.2-source.tgz",
            release_archive_sha256="be3f66f225d27ba9fa014f07e83169285da8a051b0e8ab7103d88066b39bdd3e",
            clamp_locator="contrib/hxt/tetMesh/include/hxt_tetNodalSize.h:39-44",
            callback_locator="src/mesh/meshGRegionHxt.cpp:49-85,597-598",
            release_source_matches_installed_binary_build_attested=False),
        geometry=dict(points=points.tolist(), outward_triangles=faces.tolist(),
            points_sha256=mesh.array_sha(points), faces_sha256=mesh.array_sha(faces), analytic_volume_mm3=343),
        cases={case: options(case) for case in CASES},
        pass_conditions=dict(exact_oriented_boundary=True, positive_finite_jacobians_and_volumes=True,
            exact_internal_face_orientation=True, saved_mesh_identity=True, volume_relative_error_at_most=1e-6,
            capped_referenced_interior_nodes_strictly_greater=True),
        quality_scope=dict(record_actual_SICN=True, SICN_threshold_is_fixture_pass_condition=False,
            head_minimum_SICN_gate_unchanged=0.1, head_accepted=False, convergence_established=False,
            thermal_resolution_established=False, manufacturing_authorized=False),
        resources=dict(cases_at_most=2, deadline_s_per_case=DEADLINE, sampled_RSS_stop_bytes=RSS_STOP,
            sampled_total_output_stop_bytes=DISK_STOP, threads=2, hard_address_space_limit_applied=False,
            hard_OS_CPU_quota_applied=False, automatic_retry=False),
        runtime=dict(python="3.10.11", numpy="2.0.2", gmsh="4.15.2", machine="arm64"),
        runtime_file_sha256s=RUNTIME_FILES)


def require_contract(path, digest):
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest) or mesh.sha(path) != digest:
        raise ValueError("Exact reviewed fixture-contract hash required")
    contract = json.loads(path.read_text())
    for key, value in specification().items():
        if json.dumps(contract.get(key), sort_keys=True) != json.dumps(value, sort_keys=True):
            raise ValueError("Frozen software-fixture specification changed: " + key)
    expected_sources = {str(p.relative_to(ROOT)): mesh.sha(p) for p in source_files()}
    if contract.get("source_sha256s") != expected_sources:
        raise ValueError("Fixture source bindings changed")
    if contract.get("test_sha256") != mesh.sha(ROOT / "tests/test_962_hxt_size_cap_fixture_002.py"):
        raise ValueError("Fixture test binding changed")
    for name, expected in RUNTIME_FILES.items():
        if mesh.sha(Path(name)) != expected:
            raise ValueError("Observed fixture runtime changed")
    return contract


def bound_sources(output, contract):
    return all(mesh.sha(ROOT / name) == digest and
        mesh.sha(output / "source-snapshots" / Path(name).name) == digest
        for name, digest in contract["source_sha256s"].items())


def worker(args, contract):
    case_output = args.output / args.case
    launch = json.loads((case_output / "receipt.json").read_text())
    if (launch.get("command") != [sys.executable, *sys.argv] or launch.get("status") != "running"
            or launch.get("options") != options(args.case) or launch.get("contract_sha256") != args.contract_sha256
            or {p.name for p in case_output.iterdir()} != {"receipt.json", "native.log"}
            or not bound_sources(args.output, contract)):
        raise ValueError("Fresh source-bound fixture worker required")
    with (case_output / "worker-claimed.json").open("x") as stream:
        json.dump(dict(pid=os.getpid()), stream)
    report = dict(status="running", case=args.case, options=options(args.case), software_mesh_passed=False,
                  head_accepted=False, SICN_qualified_for_head=False)
    initialized = False
    try:
        import gmsh
        observed = dict(python=platform.python_version(), numpy=np.__version__, gmsh=gmsh.__version__, machine=platform.machine())
        if observed != contract["runtime"]:
            raise ValueError("Observed fixture runtime versions changed")
        report["runtime"] = observed
        actual_runtime_hashes = [mesh.sha(Path(sys.executable).resolve()), mesh.sha(Path(gmsh.__file__)),
                                 mesh.sha(Path(gmsh.lib._name))]
        if actual_runtime_hashes != list(RUNTIME_FILES.values()):
            raise ValueError("Actual loaded fixture interpreter/module/library changed")
        report["actual_runtime_sha256s"] = dict(zip(["python", "gmsh_module", "gmsh_library"], actual_runtime_hashes))
        points, faces = cube()
        gmsh.initialize([], readConfigFiles=False, run=False); initialized = True
        gmsh.option.setNumber("General.Terminal", 1); gmsh.logger.start()
        for key, value in options(args.case).items(): gmsh.option.setNumber(key, value)
        if any(gmsh.option.getNumber(key) != value for key, value in options(args.case).items()):
            raise ValueError("Gmsh fixture options differ from the contract")
        gmsh.model.add("software_cube_size_cap"); gmsh.model.addDiscreteEntity(2, 1)
        gmsh.model.mesh.addNodes(2, 1, np.arange(1, 9, dtype=np.uint64), points.ravel())
        gmsh.model.mesh.addElementsByType(1, 2, np.arange(1, 13, dtype=np.uint64), (faces+1).ravel())
        report["surface_import"] = mesh.surface_roundtrip(gmsh, points, faces)
        gmsh.model.geo.addSurfaceLoop([1], 1); gmsh.model.geo.addVolume([1], 1); gmsh.model.geo.synchronize()
        gmsh.model.mesh.generate(3)
        path = case_output / "cube.msh"; gmsh.write(str(path))
        report.update(mesh_sha256=mesh.sha(path), mesh_bytes=path.stat().st_size)
        coordinates, cells, node_tags, tet_tags, tet_nodes = quality.tagged_volume(gmsh)
        referenced = np.unique(tet_nodes)
        report.update(tetrahedra=len(cells), total_nodes=len(node_tags), referenced_nodes=len(referenced),
            referenced_interior_nodes=int(np.count_nonzero(~np.isin(referenced, np.arange(1,9)))),
            unreferenced_nodes=len(node_tags)-len(referenced))
        report["quality"] = {name: mesh.distribution(gmsh.model.mesh.getElementQualities(tet_tags, measure))
            for name, measure in [("jacobian", "minDetJac"), ("volume_mm3", "volume"), ("SICN", "minSICN")]}
        signed = mesh.tetra_volumes(coordinates, cells)
        report["independent_volume_mm3"] = mesh.distribution(signed)
        report["summed_volume_mm3"] = math.fsum(signed)
        report["volume_relative_error"] = abs(report["summed_volume_mm3"] / 343 - 1)
        report["actual_tetra_boundary"] = mesh.tetra_boundary(cells, np.searchsorted(node_tags, faces+1))
        report["internal_face_orientation"] = quality.internal_face_orientation(cells)
        if (report["independent_volume_mm3"]["nonpositive_count"]
                or report["quality"]["jacobian"]["nonpositive_count"]
                or report["quality"]["volume_mm3"]["nonpositive_count"] or report["volume_relative_error"] > 1e-6):
            raise ValueError("Positive finite fixture tetrahedra and analytic-volume bookkeeping required")
        gmsh.clear(); gmsh.open(str(path))
        report["saved_surface"] = mesh.surface_roundtrip(gmsh, points, faces, exact_tagged_order=False)
        q, _, nt, et, en = quality.tagged_volume(gmsh)
        if not all(np.array_equal(a,b) for a,b in [(q,coordinates), (nt,node_tags), (et,tet_tags), (en,tet_nodes)]):
            raise ValueError("Saved fixture mesh identity changed")
        if mesh.sha(path) != report["mesh_sha256"]: raise ValueError("Saved fixture mesh bytes changed")
        report.update(saved_mesh_identity_exact=True, status="completed_software_mesh_only", software_mesh_passed=True)
    except Exception as exc:
        report.update(status="failed_outputs_preserved", error=type(exc).__name__+": "+str(exc))
    finally:
        if initialized:
            report["gmsh_warnings_errors"] = [s for s in gmsh.logger.get() if s.startswith(("Warning", "Error"))]
            gmsh.logger.stop(); gmsh.finalize()
        try:
            require_contract(args.contract, args.contract_sha256)
            report["bound_inputs_unchanged"] = bound_sources(args.output, contract)
        except Exception: report["bound_inputs_unchanged"] = False
        if not report["bound_inputs_unchanged"]: report.update(status="failed_bound_input_drift", software_mesh_passed=False)
        mesh.save(case_output / "worker-report.json", report)
    return 0 if report["software_mesh_passed"] else 2


def launch_case(args, case):
    output = args.output / case; output.mkdir()
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--case", case,
        "--contract", str(args.contract.resolve()), "--contract-sha256", args.contract_sha256, "--output", str(args.output.resolve())]
    report = dict(status="running", command=command, options=options(case), contract_sha256=args.contract_sha256)
    mesh.save(output / "receipt.json", report)
    process = timer = None; stopped = {"reason": None}; lock = threading.Lock(); samples = []; started = time.monotonic()
    def stop(reason):
        with lock:
            if stopped["reason"] is None:
                stopped["reason"] = reason
                if process is not None:
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
    with (output / "native.log").open("x") as log:
        try:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                env={"PATH":os.environ.get("PATH", "/usr/bin:/bin"), "LANG":"C", "PYTHONUTF8":"1",
                     "OMP_NUM_THREADS":"2", "OPENBLAS_NUM_THREADS":"2", "PYTHONDONTWRITEBYTECODE":"1"})
            timer = threading.Timer(DEADLINE, lambda: stop("native_deadline")); timer.daemon=True; timer.start()
            while process.poll() is None:
                try:
                    ps = subprocess.run(["ps", "-o", "rss=", "-p", str(process.pid)], capture_output=True, text=True, timeout=2)
                    if process.poll() is not None: break
                    rss = int(ps.stdout.strip())*1024
                    disk = sum(p.stat().st_size for p in args.output.rglob("*") if not p.name.endswith(".tmp") and p.is_file())
                    samples.append(dict(wall_s=time.monotonic()-started, RSS_bytes=rss, output_bytes=disk))
                    if rss >= RSS_STOP: stop("sampled_RSS_stop")
                    if disk >= DISK_STOP: stop("sampled_output_stop")
                except (OSError, ValueError, subprocess.SubprocessError):
                    if process.poll() is None: stop("RSS_observation_failed")
                try: process.wait(timeout=.1)
                except subprocess.TimeoutExpired: pass
        finally:
            if timer is not None: timer.cancel()
            if process is not None:
                if process.poll() is None: stop("controller_interrupted")
                process.wait()
    report.update(returncode=process.returncode, stop_reason=stopped["reason"], wall_s=time.monotonic()-started,
                  samples=samples, native_log_sha256=mesh.sha(output / "native.log"))
    path = output / "worker-report.json"
    actual = json.loads(path.read_text()) if path.is_file() else {}
    passed = (process.returncode == 0 and stopped["reason"] is None and actual.get("software_mesh_passed") is True
        and actual.get("bound_inputs_unchanged") is True and quality.matching_mesh(output / "cube.msh", actual.get("mesh_sha256")))
    report.update(status="completed_software_mesh_only" if passed else "stopped_or_rejected_outputs_preserved",
        software_mesh_passed=passed, worker_report=actual, worker_report_sha256=mesh.sha(path) if path.is_file() else None)
    mesh.save(output / "receipt.json", report)
    return report


def interior_refinement_passed(cases):
    if set(cases) != set(CASES) or not all(row.get("software_mesh_passed") is True for row in cases.values()):
        return False
    counts = [cases[name].get("worker_report", {}).get("referenced_interior_nodes") for name in CASES]
    return all(type(n) is int and n >= 0 for n in counts) and counts[1] > counts[0]


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True); parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--case", choices=list(CASES), help=argparse.SUPPRESS)
    args=parser.parse_args(argv); contract=require_contract(args.contract, args.contract_sha256)
    if args.output.resolve() != OUTPUT.resolve() or mesh.sha(Path(sys.executable).resolve()) != next(iter(RUNTIME_FILES.values())):
        raise ValueError("Fixed fresh fixture output and observed native interpreter required")
    if args.worker:
        if args.case is None: raise ValueError("Declared worker case required")
        return worker(args, contract)
    if args.case is not None: raise ValueError("Only the two fixed controller cases are allowed")
    mesh.new_output(args.output); snapshots=args.output / "source-snapshots"; snapshots.mkdir()
    for name in contract["source_sha256s"]: (snapshots / Path(name).name).write_bytes((ROOT/name).read_bytes())
    (args.output / "contract.json").write_bytes(args.contract.read_bytes())
    report=dict(status="running", contract_sha256=args.contract_sha256, software_fixture_passed=False, head_accepted=False, cases={})
    mesh.save(args.output / "receipt.json", report)
    for case in CASES:
        report["cases"][case]=launch_case(args, case)
        if not report["cases"][case]["software_mesh_passed"]: break
    require_contract(args.contract, args.contract_sha256)
    passed = (interior_refinement_passed(report["cases"])
        and all(quality.matching_mesh(args.output / case / "cube.msh", row["worker_report"].get("mesh_sha256"))
                for case, row in report["cases"].items())
        and bound_sources(args.output, contract) and mesh.sha(args.output / "contract.json") == args.contract_sha256)
    report.update(status="completed_software_fixture_only" if passed else "rejected_or_incomplete_outputs_preserved",
                  software_fixture_passed=passed)
    mesh.save(args.output / "receipt.json", report)
    print(json.dumps(dict(status=report["status"], software_fixture_passed=passed, head_accepted=False)))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
