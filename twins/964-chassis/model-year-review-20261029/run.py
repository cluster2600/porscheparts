"""Replay the original scan and render rear-mount search regions, locally only.

This script performs no point recognition or model-year classification.
"""
import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
TWIN = ROOT / "twins/964-chassis"
sys.path.insert(0, str(TWIN / "source"))
from tunnel_probe import sha256

REGISTRATION = TWIN / "derived/scan-recalage-20260925.json"
CROPS = {
    "rear_inner_under": ([-2700, -1500, -650, 650, 0, 900],
                         [(-2200, 0, -1800), (-2200, 0, 400), (1, 0, 0)]),
    "rear_left_inner": ([-2700, -1500, 100, 650, 0, 900],
                        [(-2100, -1500, 420), (-2100, 350, 420), (0, 0, 1)]),
    "rear_right_inner": ([-2700, -1500, -650, -100, 0, 900],
                         [(-2100, 1500, 420), (-2100, -350, 420), (0, 0, 1)]),
    "rear_upper_plan": ([-2600, -2100, -600, 600, 500, 900],
                        [(-2350, 0, 2200), (-2350, 0, 600), (1, 0, 0)]),
}


def registered_vertices(vertices, parameters):
    """Replay align.py's arithmetic using the retained frame, without refitting."""
    v = np.array(vertices, dtype=np.float64, copy=True)
    parameters = np.asarray(parameters, dtype=np.float64)
    if (v.ndim != 2 or v.shape[1] != 3 or not len(v)
            or not np.isfinite(v).all() or parameters.shape != (5,)
            or not np.isfinite(parameters).all()):
        raise ValueError("Expected finite Nx3 vertices and five retained frame parameters")
    yaw, x0, roll, front, ground = parameters
    v[:, 0] -= x0
    c, s = np.cos(-yaw), np.sin(-yaw)
    v[:, [0, 1]] = np.c_[v[:, 0]*c - v[:, 1]*s, v[:, 0]*s + v[:, 1]*c]
    c, s = np.cos(-roll), np.sin(-roll)
    v[:, [0, 2]] = np.c_[v[:, 0]*c + v[:, 2]*s, -v[:, 0]*s + v[:, 2]*c]
    return np.c_[v[:, 1] - front, -v[:, 0], v[:, 2] - ground].astype(np.float32)


def crop_faces(vertices, faces, bounds):
    """Retain complete source triangles only; do not interpolate cut edges."""
    bounds = np.asarray(bounds).reshape(3, 2)
    inside = ((vertices >= bounds[:, 0]) & (vertices <= bounds[:, 1])).all(axis=1)
    return faces[inside[faces].all(axis=1)], int(inside.sum())


def render(vertices, faces, output):
    import pyvista as pv
    results = {}
    for name, (bounds, camera) in CROPS.items():
        selected, vertex_count = crop_faces(vertices, faces, bounds)
        if not len(selected):
            raise ValueError(f"Empty search crop: {name}")
        cells = np.column_stack((np.full(len(selected), 3), selected))
        surface = pv.PolyData(vertices, cells).clean(point_merging=False)
        plot = pv.Plotter(off_screen=True, window_size=(1600, 1100))
        try:
            plot.set_background("#e4e9ec")
            plot.add_mesh(surface, color="#a7afb7", smooth_shading=False)
            plot.add_text(name.replace("_", " ") +
                          "\nOriginal scan crop; no anchor identified; mm",
                          font_size=12, color="black")
            plot.add_axes()
            plot.show_grid(color="black")
            plot.camera_position = camera
            plot.enable_parallel_projection()
            plot.camera.zoom(0.85)
            image = output / f"{name}.png"
            plot.screenshot(image)
        finally:
            plot.close()
        results[name] = {"bounds_mm": bounds, "camera": camera,
                         "source_triangles": len(selected),
                         "source_vertices_inside_bounds": vertex_count,
                         "image_sha256": sha256(image)}
    return results, {"pyvista": pv.__version__, "vtk": str(pv.vtk_version_info)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Review output must be a new private directory")
    registration = json.loads(REGISTRATION.read_text())
    scan_hash = sha256(args.scan)
    if scan_hash != registration["source_sha256"]:
        raise ValueError("Original scan digest does not match the retained registration")
    # Admission by exact digest makes this parser specific to this vertex/triangle OBJ.
    with args.scan.open() as stream:
        vertices = np.loadtxt((line[2:] for line in stream if line.startswith("v ")))
    with args.scan.open() as stream:
        faces = np.loadtxt((line[2:] for line in stream if line.startswith("f ")),
                           dtype=np.int32) - 1
    if (vertices.shape != (2400031, 3) or faces.shape != (4684929, 3)
            or faces.min() != 0 or faces.max() != len(vertices)-1):
        raise ValueError("Original scan topology does not match the retained input")
    vertices = registered_vertices(vertices, registration["frame_parameters_yaw_x0_roll_front_axle_ground"])
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    arrays = {}
    for name, array in (("verts_vehicle.npy", vertices), ("faces.npy", faces)):
        target = args.output / name
        np.save(target, array)
        arrays[name] = sha256(target)
        if arrays[name] != registration["outputs"][name]:
            raise ValueError(f"Replayed array differs from the retained bytes: {name}")
    interface = args.output / "interface-review"
    subprocess.run([sys.executable, str(TWIN / "source/interface_review.py"),
                    "--vertices", str(args.output / "verts_vehicle.npy"),
                    "--output", str(interface)], check=True)
    crops, versions = render(vertices, faces, args.output)
    if sha256(args.scan) != scan_hash:
        raise ValueError("Source scan changed during the review")
    sources = [Path(__file__).resolve(), REGISTRATION,
               TWIN / "source/align.py", TWIN / "source/interface_review.py",
               TWIN / "source/tunnel_probe.py", TWIN / "derived/monocoque-interface.json",
               ROOT / "catalog/measurements/MEAS-MANUAL-964-BODY-CONTROL.json"]
    report = {
        "classification": "model_year_search_views_not_an_identification",
        "source_sha256": scan_hash, "source_unchanged": True,
        "original_vertices": len(vertices), "original_triangles": len(faces),
        "array_sha256": arrays, "historical_array_bytes_reproduced": True,
        "input_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in sources},
        "versions": {"python": platform.python_version(), "numpy": np.__version__, **versions},
        "interface_review_sha256": sha256(interface / "interface-review.json"),
        "crops": crops,
        "crop_policy": "Broad visual search regions; bounds are not mounting datums or a Z measurement",
        "model_year": None, "model_year_group": None,
        "p14_measured_span_mm": None,
        "classification_policy": "Manual feature review required; never select a year by nearest points to the nominal spans",
        "publication": "Scan views and arrays remain private; redistribution rights are unconfirmed",
        "release_flags": {"model_year_identified": False, "registered_hardpoints": False,
                          "fitment_validated": False, "manufacturing_released": False},
    }
    (args.output / "run.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"historical_array_bytes_reproduced": True, "model_year": None,
                      "crop_triangles": {k: v["source_triangles"] for k, v in crops.items()}}))


if __name__ == "__main__":
    main()
