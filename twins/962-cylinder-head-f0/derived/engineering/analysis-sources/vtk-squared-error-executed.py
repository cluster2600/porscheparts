"""One corrected squared-error VTK input trial; independent distance gates remain mandatory."""
import argparse
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

from mesh_head import ROOT, FAMILY, array_sha, bound_head, new_output, read_binary_stl, save, sha, topology

CONTRACT = FAMILY / "engineering/analysis-squared-error-contract.json"
CONTRACT_SHA256 = "528be29a0b80fcf11b1d29e72be4709c869ff67903d4c9f2e2131c44001d7714"


def squared_error_setting(distance_mm):
    if not math.isfinite(distance_mm) or distance_mm <= 0:
        raise ValueError("Positive finite distance scale required")
    return distance_mm * distance_mm


def verify_contract(path=CONTRACT):
    if sha(path) != CONTRACT_SHA256:
        raise ValueError("Frozen contract changed; a separately declared trial is required")
    contract = json.loads(path.read_text())
    if (contract["bore_mm"] != 95 or contract["representation_deviation_budget_mm"] != .25
            or contract["surface_gates"]["euler_characteristic"] != -208
            or contract["volume_mesh_gates"]["minimum_SICN"] != .1):
        raise ValueError("Predeclared representation or quality gates changed")
    for relative, digest in contract["input_hashes"].items():
        if sha(ROOT / relative) != digest:
            raise ValueError("Bound source changed: " + relative)
    return contract


def validate_surface(points, faces):
    points, faces = np.asarray(points), np.asarray(faces)
    if (points.ndim != 2 or points.shape[1:] != (3,) or not np.isfinite(points).all()
            or faces.ndim != 2 or faces.shape[1:] != (3,) or not len(faces)
            or not np.issubdtype(faces.dtype, np.integer) or faces.min() < 0
            or faces.max() >= len(points) or len(np.unique(faces)) != len(points)):
        raise ValueError("Finite, nonempty, fully referenced indexed surface required")
    xyz = points[faces]
    cross = np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0])
    if not np.isfinite(cross).all() or np.any(np.linalg.norm(cross, axis=1) <= 0):
        raise ValueError("Nonfinite or zero-area triangle")
    result = topology(faces)
    result.update(vertices=len(points), triangles=len(faces),
        euler_characteristic=len(points)-result["unique_edges"]+len(faces),
        signed_volume_mm3=math.fsum(np.einsum("ij,ij->i", xyz[:, 0],
            np.cross(xyz[:, 1], xyz[:, 2])) / 6),
        points_sha256=array_sha(points), faces_sha256=array_sha(faces))
    if result["signed_volume_mm3"] <= 0:
        raise ValueError("Positive oriented enclosed volume required")
    return result


def polydata(points, faces):
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
    poly = vtk.vtkPolyData(); xyz = vtk.vtkPoints()
    xyz.SetData(numpy_to_vtk(np.ascontiguousarray(points, dtype=np.float64), deep=True))
    cells = vtk.vtkCellArray()
    cells.SetData(numpy_to_vtkIdTypeArray(np.arange(0, 3*len(faces)+1, 3, dtype=np.int64), deep=True),
        numpy_to_vtkIdTypeArray(np.ascontiguousarray(faces, dtype=np.int64).ravel(), deep=True))
    poly.SetPoints(xyz); poly.SetPolys(cells)
    return poly


def poly_arrays(poly):
    from vtk.util.numpy_support import vtk_to_numpy
    points = vtk_to_numpy(poly.GetPoints().GetData()).astype(np.float64).copy()
    offsets = vtk_to_numpy(poly.GetPolys().GetOffsetsArray())
    if not np.all(np.diff(offsets) == 3):
        raise ValueError("Linear triangle cells only")
    faces = vtk_to_numpy(poly.GetPolys().GetConnectivityArray()).reshape(-1, 3).astype(np.int64).copy()
    return points, faces


def compact_unused(points, faces):
    """Remove unused indices only; never identify distinct coordinates."""
    used, inverse = np.unique(faces, return_inverse=True)
    return points[used], inverse.reshape(-1, 3).astype(np.int64)


def edge_diagnostics(faces):
    directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges, inverse, counts = np.unique(np.sort(directed, axis=1), axis=0,
        return_inverse=True, return_counts=True)
    balance = np.bincount(inverse, weights=np.where(directed[:, 0] < directed[:, 1], 1, -1))
    return dict(unique_edges=len(edges), boundary_edges=int(np.sum(counts == 1)),
        nonmanifold_edges=int(np.sum(counts > 2)),
        orientation_imbalanced_edges=int(np.count_nonzero(balance)),
        maximum_faces_per_edge=int(counts.max()))


def prepare(output, report):
    import vtk
    vtk.vtkMultiThreader.SetGlobalMaximumNumberOfThreads(4)
    vtk.vtkSMPTools.Initialize(4)
    if vtk.vtkMultiThreader.GetGlobalMaximumNumberOfThreads() > 4:
        raise ValueError("VTK thread cap was not applied")
    contract = verify_contract()
    source, _, _ = bound_head(95)
    report.update(stage="exact_source_indexing", vtk_version=vtk.vtkVersion.GetVTKVersion(),
        vtk_maximum_threads=vtk.vtkMultiThreader.GetGlobalMaximumNumberOfThreads(),
        vtk_SMP_estimated_threads=vtk.vtkSMPTools.GetEstimatedNumberOfThreads())
    save(output / "worker-report.json", report)
    _, points, faces = read_binary_stl(source)
    report["source_surface"] = validate_surface(points, faces)
    np.savez_compressed(output / "source-surface.npz", points_mm=points, triangles=faces)
    original = polydata(points, faces)
    check_points, check_faces = poly_arrays(original)
    if not np.array_equal(check_points, points) or not np.array_equal(check_faces, faces):
        raise ValueError("Exact VTK indexed import roundtrip failed")
    report.update(stage="topology_preserving_error_controlled_decimation", exact_indexed_VTK_import=True)
    save(output / "worker-report.json", report)
    decimator = vtk.vtkDecimatePro(); decimator.SetInputData(original)
    decimator.SetTargetReduction(1.0); decimator.PreserveTopologyOn()
    decimator.SplittingOff(); decimator.BoundaryVertexDeletionOff()
    decimator.SetErrorIsAbsolute(True); decimator.SetAbsoluteError(squared_error_setting(contract["representation_deviation_budget_mm"]))
    decimator.AccumulateErrorOn(); decimator.Update()
    candidate = decimator.GetOutput()
    q, g = poly_arrays(candidate)
    # VTK keeps unused input points in some builds; compact only unused indices, without welding.
    q, g = compact_unused(q, g)
    candidate = polydata(q, g)
    # Preserve even a rejected result before any geometric acceptance checks.
    np.savez_compressed(output / "analysis-surface.npz", points_mm=q, triangles=g)
    report["candidate_arrays_sha256"] = sha(output / "analysis-surface.npz")
    report["candidate_edge_diagnostics"] = edge_diagnostics(g)
    report.update(candidate_vertices=len(q), candidate_triangles=len(g))
    save(output / "worker-report.json", report)
    report["candidate_surface"] = validate_surface(q, g)
    connection = vtk.vtkPolyDataConnectivityFilter(); connection.SetInputData(candidate)
    connection.SetExtractionModeToAllRegions(); connection.Update()
    count = connection.GetNumberOfExtractedRegions()
    report["candidate_surface"]["connected_components"] = count
    if count != 1 or report["candidate_surface"]["euler_characteristic"] != -208:
        raise ValueError("Connected component count or source Euler characteristic changed")
    writer = vtk.vtkSTLWriter(); writer.SetFileName(str(output / "analysis-surface.stl"))
    writer.SetFileTypeToBinary(); writer.SetInputData(candidate)
    if not writer.Write():
        raise ValueError("Analysis STL export failed")
    report["stl_role"] = "Convenience export; float64 NPZ arrays are authoritative for all independent audits."
    report["relative_enclosed_volume_change"] = report["candidate_surface"]["signed_volume_mm3"] / report["source_surface"]["signed_volume_mm3"] - 1
    report["decimator"] = dict(target_reduction=1.0, achieved_reduction=1-len(g)/len(faces),
        numeric_absolute_squared_error_mm2=squared_error_setting(.25), intended_independent_distance_budget_mm=.25, preserve_topology=True, splitting=False,
        boundary_vertex_deletion=False, accumulate_error=True, feature_angle_degrees=decimator.GetFeatureAngle())
    distance = vtk.vtkImplicitPolyDataDistance(); distance.SetInput(candidate)
    inspection = json.loads((FAMILY / "derived/family/bore-95-report.json").read_text())
    rows = [{"point_mm": point, "candidate_signed_metal_distance_mm": distance.EvaluateFunction(point)}
        for point in inspection["dry_opening_probes_mm"]]
    report["dry_opening_probes"] = rows
    if any(not math.isfinite(r["candidate_signed_metal_distance_mm"]) or r["candidate_signed_metal_distance_mm"] <= 0 for r in rows):
        raise ValueError("A retained dry opening probe was blocked")
    report.update(status="prepared_candidate_independent_geometric_and_semantic_gates_pending", stage="finished")


def worker(args):
    output = args.output
    allowed = {"receipt.json", "native.log", "source-executed.py"}
    if not output.is_dir() or {p.name for p in output.iterdir()} != allowed:
        raise ValueError("Worker requires one fresh controller directory")
    receipt = json.loads((output / "receipt.json").read_text())
    if (receipt["status"] != "running" or receipt["command"] != [sys.executable, *sys.argv]
            or receipt["source_sha256"] != sha(Path(__file__))
            or receipt["source_sha256"] != sha(output / "source-executed.py")
            or receipt["contract_sha256"] != sha(CONTRACT)):
        raise ValueError("Worker source, command or frozen contract changed")
    with (output / "worker-claimed.json").open("x") as stream:
        json.dump({"pid": os.getpid()}, stream)
    deadline = receipt["native_deadline_s"]
    if type(deadline) is not int or not 1 <= deadline <= 300:
        raise ValueError("Bounded hard deadline required")
    signal.alarm(deadline)
    started = time.monotonic()
    report = dict(status="running", stage="initializing", source_sha256=sha(Path(__file__)),
        contract_sha256=sha(CONTRACT), python=sys.version, machine=platform.machine(),
        executable_sha256=sha(Path(sys.executable).resolve()), numpy_version=np.__version__,
        qualification=dict(analysis_surface_geometric_gate_passed=False, solver_admission_established=False,
            mesh_convergence_established=False, engineering_accepted=False, thermal_performance_validated=False,
            strength_validated=False, manufacturing_authorized=False))
    try:
        prepare(output, report)
    except Exception as exc:
        report.update(status="failed_outputs_preserved", error=type(exc).__name__+": "+str(exc))
    finally:
        report["wall_s"] = time.monotonic()-started
        try:
            verify_contract(); report["source_inputs_unchanged"] = (
                receipt["contract_sha256"] == sha(CONTRACT)
                and receipt["source_sha256"] == sha(Path(__file__))
                and receipt["source_sha256"] == sha(output / "source-executed.py"))
        except (ValueError, OSError):
            report["source_inputs_unchanged"] = False
        if not report["source_inputs_unchanged"]:
            report.update(status="failed_outputs_preserved", error="Frozen inputs changed")
        report["output_hashes"] = {p.name: sha(p) for p in output.iterdir() if p.suffix in (".npz", ".stl")}
        save(output / "worker-report.json", report)
        signal.alarm(0)
    return 0 if report["status"].startswith("prepared_candidate_") else 2


def run(args):
    if type(args.deadline_s) is not int or not 1 <= args.deadline_s <= 300:
        raise ValueError("Native deadline must be an integer in 1..300 seconds")
    verify_contract(); new_output(args.output)
    (args.output / "source-executed.py").write_bytes(Path(__file__).read_bytes())
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--output", str(args.output.resolve())]
    receipt = dict(status="running", native_deadline_s=args.deadline_s, command=command,
        source_sha256=sha(Path(__file__)), contract_sha256=sha(CONTRACT), engineering_accepted=False)
    receipt["contract"] = verify_contract()
    save(args.output / "receipt.json", receipt)
    started = time.monotonic()
    with (args.output / "native.log").open("x") as log:
        environment = dict(os.environ)
        environment.update({name: "4" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "VTK_SMP_MAX_THREADS")})
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True, env=environment)
        try:
            process.wait(timeout=args.deadline_s)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL); process.wait()
            receipt["status"] = "timed_out_native_process_killed_outputs_preserved"
    receipt.update(returncode=process.returncode, wall_s=time.monotonic()-started,
        native_log_sha256=sha(args.output / "native.log"))
    report_path = args.output / "worker-report.json"
    if report_path.exists():
        receipt.update(worker_report_sha256=sha(report_path), worker_report=json.loads(report_path.read_text()))
    if receipt["status"] == "running":
        receipt["status"] = "preparation_completed_audits_pending" if process.returncode == 0 else "failed_outputs_preserved"
    save(args.output / "receipt.json", receipt)
    print(json.dumps({k: receipt[k] for k in ("status", "returncode", "wall_s")}), flush=True)
    return 0 if process.returncode == 0 else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--deadline-s", type=int, default=300)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        raise SystemExit(worker(args) if args.worker else run(args))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
