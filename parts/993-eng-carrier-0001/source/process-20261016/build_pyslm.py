"""Generate inspectable LPBF contours, hatch vectors and toothed support surfaces."""
import argparse
import csv
import hashlib
import importlib.metadata
import inspect
import json
import math
from pathlib import Path
import platform
import shutil
import time

import numpy as np
import pyslm
from pyslm import hatching
from pyslm.geometry import HatchGeometry
import pyslm.support
import trimesh

SOURCE = Path(__file__).resolve().parent
PARAMETERS = {
    "rotation_degrees_xyz": [0, 0, 45], "support_gap_mm": 10.0,
    "plate_thickness_mm": 20.0, "plate_size_mm": [500.0, 500.0],
    "layer_height_mm": 0.06, "overhang_angle_degrees": 45.0,
    "hatch_distance_mm": 0.08, "hatch_angle_degrees": 45.0,
    "spot_compensation_mm": 0.08, "contour_offset_mm": 0.08,
    "hatch_volume_offset_mm": 0.08, "inner_contours": 1, "outer_contours": 1,
    "support_grid_spacing_mm": [5.0, 5.0], "support_teeth_height_mm": 1.5,
    "support_teeth_top_length_mm": 0.1, "support_teeth_base_interval_mm": 1.5,
    "support_teeth_upper_penetration_mm": 0.2,
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def exact_mesh(path):
    mesh = trimesh.load_mesh(path, process=False)
    if not isinstance(mesh, trimesh.Trimesh) or not np.isfinite(mesh.vertices).all():
        raise ValueError("Input must be one finite triangle mesh")
    vertices, inverse = np.unique(mesh.vertices, axis=0, return_inverse=True)
    mesh = trimesh.Trimesh(vertices=vertices, faces=inverse[mesh.faces], process=False)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise ValueError("Input must be closed, consistently oriented and positive")
    if np.any(mesh.area_faces <= 0):
        raise ValueError("Input contains zero-area faces")
    return mesh


def packed_paths(paths):
    lengths = [len(path) for path in paths]
    points = np.vstack(paths) if lengths else np.empty((0, 2))
    if not np.isfinite(points).all():
        raise ValueError("Non-finite path coordinates")
    return points, np.r_[0, np.cumsum(lengths)].astype(np.int64)


def unique_segments(paths):
    pieces = [np.stack([p[:-1], p[1:]], axis=1) for p in paths if len(p) > 1]
    segments = np.concatenate(pieces, axis=0) if pieces else np.empty((0, 2, 2))
    raw_count = len(segments)
    segments = segments[np.any(segments[:, 0] != segments[:, 1], axis=1)]
    # PySLM's support slicer repeats its first entity; retain one exact exposure.
    reverse = ((segments[:, 0, 0] > segments[:, 1, 0]) |
               ((segments[:, 0, 0] == segments[:, 1, 0]) &
                (segments[:, 0, 1] > segments[:, 1, 1])))
    segments[reverse] = segments[reverse, ::-1]
    segments = np.unique(segments.reshape(-1, 4), axis=0).reshape(-1, 2, 2)
    return segments, raw_count - len(segments)


def support_section(surface, z, face_z_bounds):
    # Native tolerance and native intersection cases; omit only distant faces.
    tolerance = trimesh.constants.tol.merge
    local = np.flatnonzero((face_z_bounds[:, 0] <= z + tolerance) &
                           (face_z_bounds[:, 1] >= z - tolerance))
    return trimesh.intersections.mesh_plane(surface, [0, 0, 1], [0, 0, z],
        local_faces=local, cached_dots=surface.vertices[:, 2] - z)


def layer_geometry(part, z):
    polygons = []
    if part.geometry.bounds[0, 2] <= z <= part.geometry.bounds[1, 2]:
        section = part.geometry.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if section is not None:
            planar, _ = section.to_planar(np.eye(4, dtype=np.float32))
            if not planar.is_closed:
                raise ValueError("Open planar section; automatic gap filling is forbidden")
            polygons = planar.polygons_full
    paths = [path for polygon in polygons for path in hatching.utils.poly2Paths(polygon)]
    if any(len(p) < 4 or not np.array_equal(p[0], p[-1]) for p in paths):
        raise ValueError("Open or incomplete part contour")
    if any(not p.is_valid for p in polygons):
        raise ValueError("Invalid section polygon")
    hatch = hatching.Hatcher()
    hatch.hatchAngle = PARAMETERS["hatch_angle_degrees"]
    hatch.hatchDistance = PARAMETERS["hatch_distance_mm"]
    hatch.spotCompensation = PARAMETERS["spot_compensation_mm"]
    hatch.contourOffset = PARAMETERS["contour_offset_mm"]
    hatch.volumeOffsetHatch = PARAMETERS["hatch_volume_offset_mm"]
    hatch.numInnerContours = PARAMETERS["inner_contours"]
    hatch.numOuterContours = PARAMETERS["outer_contours"]
    layer = hatch.hatch(paths)
    contours, vectors = [], []
    if layer is not None:
        for item in layer.geometry:
            if isinstance(item, HatchGeometry):
                vectors.extend(item.coords.reshape(-1, 2, 2))
            else:
                contours.append(item.coords)
    vectors = np.asarray(vectors).reshape(-1, 2, 2)
    if not np.isfinite(vectors).all():
        raise ValueError("Non-finite hatch coordinates")
    return paths, contours, vectors, sum(p.area for p in polygons)


def build(input_path, output, expected_sha256=None, reuse_supports=None, identity_receipt=None):
    started = time.monotonic()
    source_sha256 = digest(__file__)
    runtime_files = [Path(inspect.getfile(pyslm.Part)),
                     Path(inspect.getfile(pyslm.support.BlockSupportGenerator)),
                     Path(inspect.getfile(pyslm.support.GridBlockSupportGenerator)),
                     Path(inspect.getfile(pyslm.support.GridBlockSupport))]
    runtime_sha256 = {str(p): digest(p) for p in runtime_files}
    upstream = json.loads((SOURCE / "upstream.json").read_text())
    if digest(runtime_files[1]) != upstream["patched_support_py_sha256"]:
        raise ValueError("Installed support generator differs from the pinned patch")
    input_path, output = Path(input_path).resolve(), Path(output).resolve()
    identity_sha256 = None
    if identity_receipt is not None:
        if expected_sha256 is not None:
            raise ValueError("Use either a SHA-256 or an identity receipt")
        identity_receipt = Path(identity_receipt).resolve()
        identity_sha256 = digest(identity_receipt)
        expected_sha256 = json.loads(identity_receipt.read_text())["candidate_STL_sha256"]
    if expected_sha256 is None:
        raise ValueError("An input SHA-256 or meshing identity receipt is required")
    if digest(input_path) != expected_sha256:
        raise ValueError("Input SHA-256 mismatch")
    mesh = exact_mesh(input_path)
    output.mkdir(parents=True, exist_ok=False)
    (output / "layers").mkdir()
    (output / "source").mkdir()
    for name in [Path(__file__).name, "upstream.json", "requirements-macos-arm64-python311.lock.txt"]:
        shutil.copy2(SOURCE / name, output / "source" / name)
    if digest(output / "source" / Path(__file__).name) != source_sha256:
        raise ValueError("Runner source changed while freezing the run")
    if identity_receipt is not None:
        shutil.copy2(identity_receipt, output / "source" / "meshing.json")
        if digest(output / "source" / "meshing.json") != identity_sha256:
            raise ValueError("Meshing receipt changed while freezing the run")
    part = pyslm.Part("carrier")
    part.setGeometry(mesh, fixGeometry=False, mergeVertices=False)
    part.rotation = PARAMETERS["rotation_degrees_xyz"]
    part.dropToPlatform(PARAMETERS["support_gap_mm"])
    part.geometry.export(output / "part-build.stl")
    plate = trimesh.creation.box((*PARAMETERS["plate_size_mm"], PARAMETERS["plate_thickness_mm"]))
    plate.apply_translation([0, 0, -PARAMETERS["plate_thickness_mm"] / 2])
    plate.export(output / "plate.stl")
    generator = pyslm.support.GridBlockSupportGenerator()
    generator.supportWallThickness = 1.0
    generator.supportTeethBaseInterval = PARAMETERS["support_teeth_base_interval_mm"]
    generator.gridSpacing = PARAMETERS["support_grid_spacing_mm"]
    generator.splineSimplificationFactor = None
    supports, block_report = [], []
    if reuse_supports is not None:
        reuse_supports = Path(reuse_supports)
        saved = json.loads((reuse_supports / "support-stage.json").read_text())
        if saved["input_sha256"] != expected_sha256 or saved["parameters"] != PARAMETERS:
            raise ValueError("Support checkpoint inputs or parameters differ")
        if saved["part_build_sha256"] != digest(output / "part-build.stl"):
            raise ValueError("Support checkpoint build pose differs")
        for name, expected in saved["outputs_sha256"].items():
            if digest(reuse_supports / name) != expected:
                raise ValueError("Support checkpoint hash mismatch")
            shutil.copy2(reuse_supports / name, output / name)
        for path in sorted(output.glob("support-*.npz")):
            with np.load(path, allow_pickle=False) as data:
                supports.append(trimesh.Trimesh(vertices=data["vertices"], faces=data["faces"],
                    face_attributes={"order": data["order"], "type": data["type"]}, process=False))
        block_report = saved["supports"]
    else:
        blocks = generator.identifySupportRegions(part, PARAMETERS["overhang_angle_degrees"], True)
        for i, block in enumerate(blocks):
            surface = block.geometry()
            if not len(surface.faces) or not np.isfinite(surface.vertices).all():
                raise ValueError("Empty or non-finite generated support surface")
            surface.visual.face_colors = [130, 150, 175, 255]
            surface.export(output / f"support-{i:03d}.stl")
            np.savez_compressed(output / f"support-{i:03d}.npz", vertices=surface.vertices,
                                faces=surface.faces, order=surface.face_attributes["order"],
                                type=surface.face_attributes["type"])
            supports.append(surface)
            block_report.append({"index": i, "faces": len(surface.faces),
                                 "bounds_mm": surface.bounds.tolist(), "surface_area_mm2": surface.area,
                                 "projected_envelope_volume_mm3": block.supportVolume.volume,
                                 "part_to_part_support": bool(block.intersectsPart),
                                 "watertight": bool(surface.is_watertight), "solid_volume_mm3": None})
    checkpoint = {"input_sha256": expected_sha256, "parameters": PARAMETERS,
                  "part_build_sha256": digest(output / "part-build.stl"), "supports": block_report,
                  "generator_source_sha256": saved["generator_source_sha256"] if reuse_supports else source_sha256,
                  "reused": reuse_supports is not None,
                  "outputs_sha256": {p.name: digest(p) for p in output.glob("support-*.*")}}
    (output / "support-stage.json").write_text(json.dumps(checkpoint, indent=2, allow_nan=False) + "\n")
    trimesh.Scene([part.geometry, plate] + supports).export(output / "build.glb")
    height = part.geometry.bounds[1, 2]
    n_layers = math.ceil(height / PARAMETERS["layer_height_mm"])
    support_bounds = []
    for surface in supports:
        face_z = surface.vertices[surface.faces, 2]
        support_bounds.append(np.column_stack((face_z.min(axis=1), face_z.max(axis=1))))
    rows = []
    for i in range(n_layers):
        z = (i + 0.5) * PARAMETERS["layer_height_mm"]
        raw, contours, vectors, area = layer_geometry(part, z)
        support_paths = [line[:, :2] for surface, bounds in zip(supports, support_bounds)
                         for line in support_section(surface, z, bounds)]
        support_vectors, duplicate_count = unique_segments(support_paths)
        raw_points, raw_offsets = packed_paths(raw)
        contour_points, contour_offsets = packed_paths(contours)
        np.savez_compressed(output / "layers" / f"layer-{i:05d}.npz", z_mm=z,
                            part_boundary_points_mm=raw_points, part_boundary_offsets=raw_offsets,
                            part_scan_contour_points_mm=contour_points,
                            part_scan_contour_offsets=contour_offsets,
                            part_hatch_segments_mm=vectors, support_scan_segments_mm=support_vectors)
        rows.append({"layer": i, "z_mm": z, "part_area_mm2": area,
                     "part_boundary_count": len(raw), "part_hatch_segments": len(vectors),
                     "support_scan_segments": len(support_vectors),
                     "duplicate_or_zero_support_segments_removed": duplicate_count,
                     "part_hatch_length_mm": np.linalg.norm(np.diff(vectors, axis=1), axis=2).sum(),
                     "support_scan_length_mm": np.linalg.norm(np.diff(support_vectors, axis=1), axis=2).sum()})
        if i % 100 == 0:
            print(f"Layer {i + 1}/{n_layers}", flush=True)
    with (output / "layers.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    if digest(input_path) != expected_sha256:
        raise ValueError("Input changed during build preparation")
    if identity_receipt is not None and digest(identity_receipt) != identity_sha256:
        raise ValueError("Meshing receipt changed during build preparation")
    if digest(__file__) != source_sha256 or any(digest(p) != value for p, value in runtime_sha256.items()):
        raise ValueError("Runner or installed PySLM source changed during build preparation")
    components = [part.geometry] + supports
    minimum = np.min([m.bounds[0] for m in components], axis=0)
    maximum = np.max([m.bounds[1] for m in components], axis=0)
    packages = {name: importlib.metadata.version(name) for name in
                ["PythonSLM", "numpy", "trimesh", "shapely", "pyclipr", "manifold3d", "vispy", "PyQt5"]}
    report = {
        "status": "open_build_preparation_completed", "input_sha256": expected_sha256,
        "source_sha256": source_sha256, "source_snapshot": "source/" + Path(__file__).name,
        "source_and_runtime_unchanged_at_completion": True, "parameters": PARAMETERS,
        "input_identity_receipt": None if identity_receipt is None else {
            "sha256": identity_sha256, "identity_field": "candidate_STL_sha256",
            "snapshot": "source/meshing.json"},
        "parameter_authority": "study geometry, PySLM hatch defaults and example_support_structure.py; no machine parameter set",
        "support_generator_settings": {k: v for k, v in vars(generator).items()
                                       if isinstance(v, (str, int, float, bool, list, type(None)))},
        "runtime": {"python": platform.python_version(), "platform": platform.platform(),
                    "machine": platform.machine(), "packages": packages,
                    "pyslm_source_files_sha256": {p.name: digest(p) for p in runtime_files}},
        "part_volume_mm3": mesh.volume, "part_bounds_mm": part.geometry.bounds.tolist(),
        "part_layer_volume_mm3": sum(row["part_area_mm2"] for row in rows) * PARAMETERS["layer_height_mm"],
        "n_layers": n_layers, "part_nonempty_layers": sum(row["part_area_mm2"] > 0 for row in rows),
        "part_hatch_segments": sum(row["part_hatch_segments"] for row in rows),
        "support_scan_segments": sum(row["support_scan_segments"] for row in rows),
        "support_exact_duplicates_removed": sum(row["duplicate_or_zero_support_segments_removed"] for row in rows),
        "supports": block_report, "build_bounds_mm": [minimum.tolist(), maximum.tolist()],
        "fits_500mm_square_plate": bool(np.all(minimum[:2] >= -250) and np.all(maximum[:2] <= 250)),
        "support_solid_mass_kg": None, "support_removal_tool_clearance_mm": None,
        "machine_native_file": False, "power_and_scan_speed_assigned": False,
        "elapsed_seconds": time.monotonic() - started,
        "outputs_sha256": {str(p.relative_to(output)): digest(p) for p in sorted(output.rglob("*")) if p.is_file()},
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    identity = parser.add_mutually_exclusive_group(required=True)
    identity.add_argument("--sha256")
    identity.add_argument("--identity-receipt", type=Path,
                          help="Gmsh meshing.json containing candidate_STL_sha256")
    parser.add_argument("--reuse-supports", type=Path)
    args = parser.parse_args()
    report = build(args.input, args.output, args.sha256, args.reuse_supports, args.identity_receipt)
    print(json.dumps({k: report[k] for k in ["status", "n_layers", "part_hatch_segments", "support_scan_segments"]}))
