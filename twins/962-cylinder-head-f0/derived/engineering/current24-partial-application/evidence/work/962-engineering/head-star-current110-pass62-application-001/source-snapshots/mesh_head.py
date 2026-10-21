"""Bounded exact-surface tetrahedralization of a retained 962 study head."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import signal
import struct
import subprocess
import sys
import time

import numpy as np

FAMILY = Path(__file__).resolve().parents[1]
ROOT = FAMILY.parents[1]
DELIVERY = FAMILY / "derived/family/delivery-report.json"
VOLUME_RELATIVE_BOUND = 1e-6
OPTIONS = {"General.NumThreads": 2, "Mesh.MaxNumThreads3D": 2,
    "Mesh.Algorithm3D": 1, "Mesh.MeshOnlyEmpty": 1, "Mesh.Renumber": 0,
    "Mesh.ElementOrder": 1, "Mesh.Optimize": 0, "Mesh.OptimizeNetgen": 0,
    "Mesh.MeshSizeExtendFromBoundary": 0, "Mesh.RandomSeed": 1,
    "Mesh.Binary": 1, "Mesh.SaveAll": 1, "Mesh.MshFileVersion": 4.1}
RECORD = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)),
                   ("attribute", "<u2")])


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def array_sha(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def save(path, value):
    text = json.dumps(value, indent=2, allow_nan=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text)
    temporary.replace(path)


def new_output(path):
    if path.exists() or path.is_symlink():
        raise ValueError("Output directory must be new; preserve every previous attempt")
    path.mkdir(parents=True)


def claim_worker(output):
    """A worker can consume only one fresh, source-bound controller launch."""
    allowed = {"receipt.json", "native.log", "source-executed.py"}
    if not output.is_dir() or {item.name for item in output.iterdir()} != allowed:
        raise ValueError("Worker requires a fresh controller directory; existing results are preserved")
    receipt = json.loads((output / "receipt.json").read_text())
    if (receipt["status"] != "running" or receipt["command"] != [sys.executable, *sys.argv]
            or receipt["source_sha256"] != sha(Path(__file__).resolve())
            or receipt["source_sha256"] != sha(output / "source-executed.py")
            or type(receipt["native_deadline_s"]) is not int
            or not 1 <= receipt["native_deadline_s"] <= 300):
        raise ValueError("Worker controller identity, source or hard deadline changed")
    with (output / "worker-claimed.json").open("x") as stream:
        json.dump(dict(pid=os.getpid(), source_sha256=receipt["source_sha256"]), stream)
    return receipt["native_deadline_s"]


def read_binary_stl(path):
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError("Expected a complete binary STL header")
    count = struct.unpack_from("<I", data, 80)[0]
    if count == 0 or len(data) != 84 + 50 * count:
        raise ValueError("Expected nonempty 50-byte binary STL records with no trailing bytes")
    records = np.frombuffer(data, dtype=RECORD, offset=84, count=count)
    if not np.isfinite(records["normal"]).all():
        raise ValueError("Nonfinite STL normals")
    triangles = records["vertices"].copy()
    points, faces = index_triangles(triangles)
    return triangles, points, faces


def index_triangles(triangles):
    triangles = np.asarray(triangles)
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or len(triangles) == 0:
        raise ValueError("Expected nonempty triangle coordinates with shape (N,3,3)")
    if not np.isfinite(triangles).all():
        raise ValueError("Nonfinite triangle coordinates")
    xyz = triangles.astype(np.float64)
    crosses = np.cross(xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0])
    twice_area = np.linalg.norm(crosses, axis=1)
    if not np.isfinite(twice_area).all() or np.any(twice_area <= 0):
        raise ValueError("Zero-area, degenerate or nonfinite triangle")
    points, inverse = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    if not np.array_equal(points[faces], triangles):
        raise ValueError("Exact indexed reconstruction failed")
    return points.astype(np.float64), faces.astype(np.int64)


def topology(faces):
    directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    ordered = np.sort(directed, axis=1)
    edges, inverse, counts = np.unique(ordered, axis=0, return_inverse=True, return_counts=True)
    balance = np.bincount(inverse, weights=np.where(directed[:, 0] < directed[:, 1], 1, -1))
    result = dict(unique_edges=len(edges), boundary_edges=int(np.sum(counts == 1)),
        nonmanifold_edges=int(np.sum(counts != 2)),
        orientation_imbalanced_edges=int(np.count_nonzero(balance)))
    if result["boundary_edges"] or result["nonmanifold_edges"] or result["orientation_imbalanced_edges"]:
        raise ValueError("Surface must be closed, edge-manifold and consistently oriented")
    return result


def bound_head(bore):
    delivery = json.loads(DELIVERY.read_text())
    matches = [item for item in delivery["models"] if item["bore_mm"] == bore]
    if len(matches) != 1 or delivery["length_unit"] != "mm":
        raise ValueError("Retained bore identity or units changed")
    model = matches[0]
    report_path = ROOT / model["report_path"]
    if sha(report_path) != model["report_sha256"]:
        raise ValueError("Retained inspection report changed")
    inspection = json.loads(report_path.read_text())
    config_path = FAMILY / "source/family/configs" / f"bore-{bore}.json"
    config = json.loads(config_path.read_text())
    stl = ROOT / model["inspection_directory"] / "solid.stl"
    if (config["geometry"]["bore_mm"] != bore or sha(config_path) != inspection["config_sha256"]
            or sha(stl) != inspection["mesh_metrics"]["solid"]["sha256"]
            or model["metal_volume_cm3"] != inspection["mesh_metrics"]["solid"]["volume_mm3"] / 1000):
        raise ValueError("Bore, configuration, solid mesh or retained volume changed")
    paths = [DELIVERY, report_path, config_path, stl, Path(__file__).resolve()]
    return stl, inspection["mesh_metrics"]["solid"], {
        str(path.relative_to(ROOT)): sha(path) for path in paths}


def surface_roundtrip(gmsh, points, faces, exact_tagged_order=True):
    tags, coordinates, _ = gmsh.model.mesh.getNodes()
    order = np.argsort(tags)
    tags = np.asarray(tags)[order]
    coordinates = np.asarray(coordinates).reshape(-1, 3)[order]
    expected_tags = np.arange(1, len(points) + 1, dtype=np.uint64)
    selected = np.searchsorted(tags, expected_tags)
    types, elements, nodes = gmsh.model.mesh.getElements(2)
    if (len(tags) < len(points) or np.any(selected >= len(tags))
            or not np.array_equal(tags[selected], expected_tags)
            or not np.array_equal(coordinates[selected], points) or list(types) != [2]):
        raise ValueError("Original surface nodes or linear surface elements changed")
    order = np.argsort(elements[0])
    face_tags = np.asarray(elements[0])[order]
    connectivity = np.asarray(nodes[0]).reshape(-1, 3)[order]
    tags_equal = np.array_equal(face_tags, np.arange(1, len(faces) + 1))
    tagged_order_equal = np.array_equal(connectivity, faces + 1)
    if exact_tagged_order:
        matched = tags_equal and tagged_order_equal
    else:
        # Retagging, element permutation and cyclic vertex rotation preserve an oriented triangle.
        matched = connectivity.shape == faces.shape and np.array_equal(
            canonical_oriented(connectivity), canonical_oriented(faces + 1))
    if not matched:
        raise ValueError("Original oriented surface connectivity or triangle count changed")
    return dict(exact_source_coordinates=True, exact_source_oriented_connectivity=True,
        original_surface_nodes=len(points), original_surface_triangles=len(faces),
        source_element_tags_preserved=bool(tags_equal),
        source_tagged_vertex_order_preserved=bool(tagged_order_equal),
        comparison="exact_tagged_index_order" if exact_tagged_order else "exact_oriented_triangle_set")


def distribution(values):
    values = np.asarray(values, dtype=float)
    if not len(values) or not np.isfinite(values).all():
        raise ValueError("Nonempty finite mesh-quality values required")
    percentiles = np.percentile(values, [0, 1, 5, 50, 95, 99, 100])
    return {**dict(zip(("minimum", "p01", "p05", "p50", "p95", "p99", "maximum"),
                       map(float, percentiles))),
            "count": len(values), "nonpositive_count": int(np.sum(values <= 0))}


def tetra_volumes(points, cells):
    output = np.empty(len(cells), dtype=np.float64)
    for start in range(0, len(cells), 100000):
        xyz = points[cells[start:start + 100000]]
        output[start:start + len(xyz)] = np.einsum("ij,ij->i", xyz[:, 1] - xyz[:, 0],
            np.cross(xyz[:, 2] - xyz[:, 0], xyz[:, 3] - xyz[:, 0])) / 6
    return output


def canonical_oriented(faces):
    rotated = np.take_along_axis(faces, (faces.argmin(axis=1)[:, None] + np.arange(3)) % 3, axis=1)
    return rotated[np.lexsort(rotated.T[::-1])]


def tetra_boundary(cells, source_faces):
    faces = np.concatenate([cells[:, [0, 2, 1]], cells[:, [0, 1, 3]],
                            cells[:, [1, 2, 3]], cells[:, [2, 0, 3]]])
    _, first, counts = np.unique(np.sort(faces, axis=1), axis=0,
                                 return_index=True, return_counts=True)
    if np.any(counts > 2):
        raise ValueError("Nonmanifold tetrahedral faces")
    boundary = faces[first[counts == 1]]
    if boundary.shape != source_faces.shape or not np.array_equal(
            canonical_oriented(boundary), canonical_oriented(source_faces)):
        raise ValueError("Actual oriented tetrahedron boundary differs from the exact source surface")
    return dict(boundary_triangles=len(boundary), exact_oriented_tetra_boundary=True,
                nonmanifold_volume_faces=0)


def volume_arrays(gmsh):
    types, tags, nodes = gmsh.model.mesh.getElements(3)
    if list(types) != [4] or not len(tags[0]):
        raise ValueError("Expected nonempty linear tetrahedra only")
    node_tags, xyz, _ = gmsh.model.mesh.getNodes()
    order = np.argsort(node_tags)
    sorted_tags = np.asarray(node_tags)[order]
    cell_tags = np.asarray(nodes[0]).reshape(-1, 4)
    indices = np.searchsorted(sorted_tags, cell_tags)
    if np.any(indices >= len(sorted_tags)) or not np.array_equal(sorted_tags[indices], cell_tags):
        raise ValueError("Missing tetrahedron nodes")
    return np.asarray(xyz).reshape(-1, 3)[order], indices, tags[0], cell_tags


def worker(args):
    deadline = claim_worker(args.output)
    signal.alarm(deadline)
    import gmsh
    output = args.output
    started = time.monotonic()
    stl, retained, pins = bound_head(args.bore)
    options = dict(OPTIONS)
    if args.algorithm == "hxt":
        options.update({"Mesh.Algorithm3D": 10, "General.NumThreads": 4, "Mesh.MaxNumThreads3D": 4})
    result = dict(status="running", stage="reading_exact_binary_stl", length_unit="mm",
        input_hashes=pins, bore_mm=args.bore, gmsh_version=gmsh.__version__,
        numpy_version=np.__version__, machine=platform.machine(), python=sys.version,
        executable=sys.executable, executable_sha256=sha(Path(sys.executable).resolve()),
        gmsh_module_sha256=sha(Path(gmsh.__file__)),
        libgmsh_sha256=sha(Path(gmsh.lib._name)), algorithm=args.algorithm, options=options,
        volume_relative_bookkeeping_bound=VOLUME_RELATIVE_BOUND,
        bound_is_not_manufacturing_tolerance=True,
        qualification=dict(geometric_volume_gate_passed=False, mesh_convergence_established=False,
            engineering_accepted=False, strength_validated=False, manufacturing_authorized=False))
    checkpoint = lambda: save(output / "worker-report.json", result)
    checkpoint()
    initialized = False
    try:
        if gmsh.__version__ != "4.15.2" or platform.machine() != "arm64":
            raise ValueError("This trial requires the observed native ARM64 Gmsh 4.15.2 runtime")
        triangles, points, faces = read_binary_stl(stl)
        if len(faces) != retained["triangles"]:
            raise ValueError("Retained triangle count changed")
        result.update(surface_topology=topology(faces), surface_nodes=len(points),
            surface_triangles=len(faces), source_points_sha256=array_sha(points),
            source_faces_sha256=array_sha(faces))
        xyz = triangles.astype(np.float64)
        source_volume = float(np.einsum("ij,ij->i", xyz[:, 0], np.cross(xyz[:, 1], xyz[:, 2])).sum() / 6)
        relative_source = abs(source_volume / retained["volume_mm3"] - 1)
        result.update(source_signed_volume_mm3=source_volume,
                      retained_volume_mm3=retained["volume_mm3"], source_volume_relative_error=relative_source)
        if source_volume <= 0 or relative_source > VOLUME_RELATIVE_BOUND:
            raise ValueError("Source signed volume fails the retained-volume bookkeeping gate")
        del triangles, xyz
        gmsh.initialize([], readConfigFiles=False, run=False)
        initialized = True
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.logger.start()
        for key, value in options.items():
            gmsh.option.setNumber(key, value)
        gmsh.model.add("962_exact_indexed_head_geometric_trial")
        gmsh.model.addDiscreteEntity(2, 1)
        gmsh.model.mesh.addNodes(2, 1, np.arange(1, len(points) + 1, dtype=np.uint64), points.ravel())
        gmsh.model.mesh.addElementsByType(1, 2,
            np.arange(1, len(faces) + 1, dtype=np.uint64), (faces + 1).astype(np.uint64).ravel())
        result["import_roundtrip"] = surface_roundtrip(gmsh, points, faces)
        gmsh.model.geo.addSurfaceLoop([1], 1)
        gmsh.model.geo.addVolume([1], 1)
        gmsh.model.geo.synchronize()
        gmsh.write(str(output / "before-volume.msh"))
        result.update(stage="generating_linear_tetrahedra", before_volume_sha256=sha(output / "before-volume.msh"))
        checkpoint()
        gmsh.model.mesh.generate(3)
        result.update(stage="auditing_generated_volume")
        checkpoint()
        result["surface_after_tetrahedralization"] = surface_roundtrip(gmsh, points, faces, exact_tagged_order=False)
        volume_path = output / "head-volume.msh"
        gmsh.write(str(volume_path))
        result["mesh_sha256"] = sha(volume_path)
        coordinates, cells, tags, cell_node_tags = volume_arrays(gmsh)
        result.update(tetrahedra=len(cells), all_mesh_nodes=len(coordinates),
                      tetra_connectivity_sha256=array_sha(cell_node_tags))
        quality = {name: distribution(gmsh.model.mesh.getElementQualities(tags, measure)) for name, measure in
            (("minimum_jacobian", "minDetJac"), ("native_volume_mm3", "volume"), ("minimum_SICN", "minSICN"))}
        signed_volumes = tetra_volumes(coordinates, cells)
        quality["independent_signed_volume_mm3"] = distribution(signed_volumes)
        result["quality"] = quality
        result["summed_tetra_volume_mm3"] = math.fsum(signed_volumes)
        result["volume_relative_error"] = abs(result["summed_tetra_volume_mm3"] / retained["volume_mm3"] - 1)
        checkpoint()
        if any(item["nonpositive_count"] for item in quality.values()):
            raise ValueError("Tetrahedron Jacobian, signed volume and SICN must all be strictly positive")
        if result["volume_relative_error"] > VOLUME_RELATIVE_BOUND:
            raise ValueError("Summed tetrahedron volume fails the 1 ppm numerical bookkeeping bound")
        # Cell indices refer to sorted node tags; convert the source tags to that same index space.
        node_tags, _, _ = gmsh.model.mesh.getNodes()
        sorted_tags = np.sort(node_tags)
        source_indices = np.searchsorted(sorted_tags, faces + 1)
        result["tetra_boundary"] = tetra_boundary(cells, source_indices)
        result.update(stage="verifying_saved_mesh")
        checkpoint()
        gmsh.clear()
        gmsh.open(str(volume_path))
        result["saved_surface_roundtrip"] = surface_roundtrip(gmsh, points, faces, exact_tagged_order=False)
        reread_coordinates, reread_cells, _, reread_tags = volume_arrays(gmsh)
        if (not np.array_equal(reread_coordinates, coordinates) or len(reread_cells) != len(cells)
                or not np.array_equal(reread_tags, cell_node_tags)):
            raise ValueError("Saved tetrahedral coordinates or connectivity changed")
        result["saved_tetra_connectivity_exact"] = True
        result["saved_all_node_coordinates_exact"] = True
        result["qualification"]["geometric_volume_gate_passed"] = True
        result.update(status="completed_geometric_volume_only", stage="finished")
    except Exception as error:
        result.update(status="failed", error=type(error).__name__ + ": " + str(error))
        if initialized:
            try:
                gmsh.write(str(output / "failed-current-mesh.msh"))
            except Exception as export_error:
                result["failed_mesh_export_error"] = str(export_error)
    finally:
        if initialized:
            result["gmsh_warnings_errors"] = [line for line in gmsh.logger.get()
                if line.startswith(("Warning", "Error"))]
            gmsh.logger.stop()
            gmsh.finalize()
        result.update(worker_wall_s=time.monotonic() - started,
            inputs_unchanged=all(sha(ROOT / path) == digest for path, digest in pins.items()))
        if not result["inputs_unchanged"]:
            result.update(status="failed", error="Bound inputs changed during the trial")
            result["qualification"]["geometric_volume_gate_passed"] = False
        checkpoint()
        signal.alarm(0)
    return 0 if result["status"] == "completed_geometric_volume_only" else 2


def run(args):
    if type(args.deadline_s) is not int or not 1 <= args.deadline_s <= 300:
        raise ValueError("Native deadline must be an integer in 1..300 seconds")
    new_output(args.output)
    source = Path(__file__).resolve()
    with (args.output / "source-executed.py").open("xb") as stream:
        stream.write(source.read_bytes())
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--bore", str(args.bore),
               "--algorithm", args.algorithm, "--output", str(args.output.resolve())]
    receipt = dict(status="running", native_deadline_s=args.deadline_s, command=command,
        algorithm=args.algorithm,
        source_sha256=sha(source), source_snapshot="source-executed.py",
        source_snapshot_sha256=sha(args.output / "source-executed.py"), no_surface_remesh_or_repair=True,
        engineering_accepted=False, manufacturing_authorized=False)
    save(args.output / "receipt.json", receipt)
    started = time.monotonic()
    with (args.output / "native.log").open("x") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            process.wait(timeout=args.deadline_s)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            receipt["status"] = "timed_out_native_process_killed_outputs_preserved"
    report_path = args.output / "worker-report.json"
    receipt.update(returncode=process.returncode, native_pid=process.pid, wall_s=time.monotonic() - started,
                   native_log_sha256=sha(args.output / "native.log"))
    if report_path.exists():
        receipt.update(worker_report_sha256=sha(report_path), worker_report=json.loads(report_path.read_text()))
    if receipt["status"] == "running":
        receipt["status"] = ("completed_geometric_volume_only" if process.returncode == 0 else "failed_outputs_preserved")
    save(args.output / "receipt.json", receipt)
    print(json.dumps({key: receipt[key] for key in ("status", "returncode", "wall_s")}), flush=True)
    return 0 if receipt["status"] == "completed_geometric_volume_only" else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bore", type=int, choices=(95, 98, 100, 102), default=95)
    parser.add_argument("--algorithm", choices=("delaunay", "hxt"), default="delaunay")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--deadline-s", type=int, default=300)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        raise SystemExit(worker(args) if args.worker else run(args))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
