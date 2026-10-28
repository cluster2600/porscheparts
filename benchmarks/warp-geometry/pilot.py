#!/usr/bin/env python3
"""Check Warp point-to-surface queries against an analytic synthetic box oracle.

Units are millimetres. This is a runtime geometry pilot, not a part, scan,
manufacturing qualification, CFD calculation, or speedup demonstration.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import time


MIN_SAMPLES = 64
MAX_SAMPLES = 1_000_000
MAX_REPEATS = 20
TOLERANCE_MM = 0.0001
SEED = 993
SCHEMA_VERSION = "warp-geometry-pilot/v1"
REPORT_BEGIN = "WARP_GEOMETRY_REPORT_BEGIN"
REPORT_END = "WARP_GEOMETRY_REPORT_END"


def bounded_integer(minimum, maximum):
    def parse(value):
        try:
            number = int(value)
        except ValueError as error:
            raise argparse.ArgumentTypeError("must be an integer") from error
        if not minimum <= number <= maximum:
            raise argparse.ArgumentTypeError(f"must be between {minimum} and {maximum}")
        return number

    return parse


def parser():
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--device", choices=("cpu", "cuda:0"), default="cuda:0",
                         help="CUDA is required by default; cpu is an explicit smoke test only")
    command.add_argument("--output", type=Path, required=True,
                         help="new report JSON file in an existing directory; never overwritten")
    command.add_argument("--samples", type=bounded_integer(MIN_SAMPLES, MAX_SAMPLES), default=4096,
                         help="probe count per case (64 through 1000000)")
    command.add_argument("--repeats", type=bounded_integer(1, MAX_REPEATS), default=5,
                         help="warm full-pipeline repetitions (1 through 20)")
    return command


def box_mesh(center, half_extent):
    import numpy as np

    corners = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                        [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], dtype=np.float32)
    vertices = corners * np.asarray(half_extent, dtype=np.float32) + np.asarray(center, dtype=np.float32)
    # Each face has outward winding; every directed edge has its reverse.
    triangles = np.array([[0, 3, 2], [0, 2, 1], [4, 5, 6], [4, 6, 7],
                          [0, 1, 5], [0, 5, 4], [2, 3, 7], [2, 7, 6],
                          [0, 4, 7], [0, 7, 3], [1, 2, 6], [1, 6, 5]], dtype=np.int32)
    return vertices, triangles


def box_surface_oracle(points, center, half_extent):
    """Independent float64 analytic distance to the surface, including inside."""
    import numpy as np

    points = np.asarray(points, dtype=np.float64)
    center = np.asarray(center, dtype=np.float64)
    half_extent = np.asarray(half_extent, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or center.shape != (3,) or half_extent.shape != (3,):
        raise ValueError("points must have shape (N, 3); center and half_extent must have shape (3,)")
    if not (np.isfinite(points).all() and np.isfinite(center).all()
            and np.isfinite(half_extent).all() and (half_extent > 0).all()):
        raise ValueError("box inputs must be finite and half extents positive")
    relative = np.abs(points - center)
    outside = np.linalg.norm(np.maximum(relative - half_extent, 0.0), axis=1)
    inside = np.maximum(np.min(half_extent - relative, axis=1), 0.0)
    return outside + inside


def make_cases(samples):
    import numpy as np

    if not MIN_SAMPLES <= samples <= MAX_SAMPLES:
        raise ValueError("sample count is outside the fixed pilot limits")
    rng = np.random.default_rng(SEED)
    half = np.array([10.0, 15.0, 5.0], dtype=np.float32)
    zero = np.zeros(3, dtype=np.float32)
    corners, _ = box_mesh(zero, half)
    edges = np.array([[10, 0, 5], [0, -15, 5], [-10, 15, 0], [10, 15, 0]], dtype=np.float32)
    surfaces = rng.uniform(-1.0, 1.0, (samples, 3)).astype(np.float32) * half
    axes = np.arange(samples) % 3
    surfaces[np.arange(samples), axes] = np.where(np.arange(samples) % 2, 1.0, -1.0) * half[axes]
    surfaces[:12] = np.concatenate([corners, edges])
    mixed = rng.uniform(-1.75, 1.75, (samples, 3)).astype(np.float32) * half
    # Guaranteed center, interior, face, edge, corner and exterior probes.
    mixed[:12] = [[0, 0, 0], [1, 2, 3], [9, 0, 0], [10, 0, 0],
                  [10, 15, 0], [10, 15, 5], [11, 0, 0], [11, 16, 0],
                  [11, 16, 6], [-11, -16, -6], [0, 0, -4], [0, 0, -6]]
    return [
        {"name": "surface_identity", "center": zero, "half_extent": half, "probes": surfaces},
        {"name": "mixed_probes", "center": zero, "half_extent": half, "probes": mixed},
        {"name": "translated_box", "center": np.array([3.0, -7.0, 2.5], dtype=np.float32),
         "half_extent": half, "probes": mixed.copy()},
    ]


def assess_distances(actual, expected, hits):
    """Fail on any missing, nonfinite, negative or out-of-tolerance result."""
    import numpy as np

    actual = np.asarray(actual, dtype=np.float64)
    expected = np.asarray(expected, dtype=np.float64)
    hits = np.asarray(hits)
    if actual.shape != expected.shape or actual.shape != hits.shape or actual.ndim != 1 or not actual.size:
        raise ValueError("distance, oracle and query-hit arrays must have the same nonempty vector shape")
    finite = np.isfinite(actual) & np.isfinite(expected)
    errors = np.abs(actual[finite] - expected[finite])
    maximum = float(errors.max()) if errors.size else None
    rms = float(np.sqrt(np.mean(errors * errors))) if errors.size else None
    misses = int(np.count_nonzero(hits != 1))
    invalid = int(np.count_nonzero(~finite | (actual < 0.0) | (expected < 0.0)))
    return {"passed": bool(invalid == 0 and misses == 0 and maximum is not None and maximum <= TOLERANCE_MM),
            "max_abs_error_mm": maximum, "rms_abs_error_mm": rms,
            "query_miss_count": misses, "invalid_distance_count": invalid,
            "tolerance_mm": TOLERANCE_MM}


def fixture_hash(case):
    vertices, triangles = box_mesh(case["center"], case["half_extent"])
    digest = hashlib.sha256()
    for array in (vertices, triangles, case["probes"]):
        # Force explicit byte order for stable fixture identities across hosts.
        digest.update(array.astype(array.dtype.newbyteorder("<"), copy=False).tobytes(order="C"))
    return digest.hexdigest()


def load_kernel():
    path = Path(__file__).with_name("kernels.py")
    spec = importlib.util.spec_from_file_location("warp_geometry_pilot_kernels", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.point_surface_distances


def warp_pass(wp, kernel, device, cases):
    """Fresh buffers and BVHs each pass; include transfers and host readback."""
    results = []
    for case in cases:
        vertices, triangles = box_mesh(case["center"], case["half_extent"])
        mesh = wp.Mesh(points=wp.array(vertices, dtype=wp.vec3, device=device),
                       indices=wp.array(triangles.reshape(-1), dtype=wp.int32, device=device))
        probes = wp.array(case["probes"], dtype=wp.vec3, device=device)
        distances = wp.empty(len(case["probes"]), dtype=wp.float32, device=device)
        hits = wp.empty(len(case["probes"]), dtype=wp.int32, device=device)
        wp.launch(kernel, dim=len(case["probes"]), inputs=[mesh.id, probes],
                  outputs=[distances, hits], device=device)
        wp.synchronize_device(device)
        results.append((distances.numpy(), hits.numpy()))
    wp.synchronize_device(device)
    return results


def run_pilot(samples, repeats, requested_device):
    import numpy as np

    if requested_device not in ("cpu", "cuda:0") or not 1 <= repeats <= MAX_REPEATS:
        raise ValueError("device or repeat count is outside the fixed pilot limits")
    cases = make_cases(samples)
    oracle_start = time.perf_counter()
    expected = [box_surface_oracle(case["probes"], case["center"], case["half_extent"]) for case in cases]
    oracle_wall = time.perf_counter() - oracle_start
    cold_start = time.perf_counter()
    import warp as wp

    if os.environ.get("WARP_CACHE_PATH"):
        wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
    wp.init()
    device = wp.get_device(requested_device)
    if requested_device == "cuda:0" and not device.is_cuda:
        raise RuntimeError("CUDA was requested but Warp did not select a CUDA device")
    if requested_device == "cpu" and device.is_cuda:
        raise RuntimeError("CPU smoke test did not select a CPU device")
    kernel = load_kernel()
    cold_results = warp_pass(wp, kernel, device, cases)
    cold_wall = time.perf_counter() - cold_start
    assessments = [[] for _ in cases]
    for index, (distances, hits) in enumerate(cold_results):
        assessments[index].append(assess_distances(distances, expected[index], hits))
    warm_walls = []
    for _ in range(repeats):
        wp.synchronize_device(device)
        start = time.perf_counter()
        results = warp_pass(wp, kernel, device, cases)
        warm_walls.append(time.perf_counter() - start)
        for index, (distances, hits) in enumerate(results):
            assessments[index].append(assess_distances(distances, expected[index], hits))
    case_reports = []
    for case, oracle, checks in zip(cases, expected, assessments):
        check = {"passed": all(item["passed"] for item in checks),
                 "max_abs_error_mm": max(item["max_abs_error_mm"] for item in checks if item["max_abs_error_mm"] is not None)
                 if any(item["max_abs_error_mm"] is not None for item in checks) else None,
                 "rms_abs_error_mm": max(item["rms_abs_error_mm"] for item in checks if item["rms_abs_error_mm"] is not None)
                 if any(item["rms_abs_error_mm"] is not None for item in checks) else None,
                 "query_miss_count": max(item["query_miss_count"] for item in checks),
                 "invalid_distance_count": max(item["invalid_distance_count"] for item in checks),
                 "tolerance_mm": TOLERANCE_MM}
        case_reports.append({"name": case["name"], "fixture_sha256": fixture_hash(case),
                             "probe_count": samples, "box_center_mm": case["center"].tolist(),
                             "box_half_extent_mm": case["half_extent"].tolist(),
                             "oracle_min_distance_mm": float(oracle.min()),
                             "oracle_max_distance_mm": float(oracle.max()),
                             "oracle_zero_distance_count": int(np.count_nonzero(oracle == 0.0)),
                             "checks_across_cold_and_warm_passes": len(checks), **check})
    passed = all(case["passed"] for case in case_reports)
    return {"schema_version": SCHEMA_VERSION, "status": "passed" if passed else "failed",
            "source_sha256": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                              for name in ("pilot.py", "kernels.py")},
            "versions": {"python": platform.python_version(), "numpy": np.__version__, "warp": wp.__version__},
            "device": {"requested": requested_device, "actual": str(device), "name": device.name,
                       "type": "cuda" if device.is_cuda else "cpu", "arch": getattr(device, "arch", None)},
            "units": "mm", "distance_kind": "unsigned_point_to_surface", "warp_precision": "float32",
            "oracle": "independent analytic axis-aligned box surface distance in float64",
            "seed": SEED, "samples_per_case": samples, "probe_count": samples * len(cases), "repeats": repeats,
            "timing": {"numpy_oracle_wall_s": oracle_wall, "cold_full_pipeline_wall_s": cold_wall,
                       "warm_full_pipeline_wall_s": warm_walls,
                       "scope": "all cases; fresh mesh/BVH and buffers, host/device transfers, query, synchronization, host readback",
                       "cold_scope": "also includes Warp import/init and kernel module loading; JIT compilation may use an existing disk cache",
                       "fixture_generation_and_oracle_assessment_included": False,
                       "speedup_claimed": False, "kernel_cache_directory": str(wp.config.kernel_cache_dir)},
            "cases": case_reports, "geometry_only": True, "manufacturing_authorized": False,
            "cuda_dispatch_completed": bool(device.is_cuda), "gpu_validated": bool(device.is_cuda and passed),
            "application_validated": False, "cpu_smoke_only": not device.is_cuda}


def main(argv=None):
    command = parser()
    args = command.parse_args(argv)
    if not args.output.parent.is_dir():
        command.error("output parent directory must already exist")
    if args.output.exists() or args.output.is_symlink():
        command.error("output already exists; choose a new report path")
    try:
        report = run_pilot(args.samples, args.repeats, args.device)
    except Exception as error:
        report = {"schema_version": SCHEMA_VERSION, "status": "error", "error": str(error),
                  "device": {"requested": args.device, "actual": None},
                  "geometry_only": True, "manufacturing_authorized": False,
                  "gpu_validated": False, "application_validated": False}
    try:
        payload = json.dumps(report, indent=2, allow_nan=False) + "\n"
        # Exclusive creation also rejects a concurrent writer or dangling symlink.
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(payload)
    except (OSError, ValueError) as error:
        print(f"Cannot write report: {error}", file=sys.stderr)
        return 1
    print(REPORT_BEGIN)
    print(payload, end="")
    print(REPORT_END)
    if report["status"] != "passed":
        print(report.get("error", "Warp distances failed the fixed analytic oracle checks"), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
