"""Bound the 935 visual hub-space/drive surface gap over tilt azimuth."""

import json
import math
from pathlib import Path
import sys
import time

import fcl
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_surface_contacts import DTYPE, fixtures, load, query, sha  # noqa: E402

AXIS_SHA256 = "378af4cb4fc0459773d2fa5901a6b00976786d7defd1a118d3f1de6567b55119"
HUB_SHA256 = "6017e24759bc15a347ef52c0e7bb130cf0e385c2b9c8c82133d599185ba12b3c"
DRIVE_SHA256 = "fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35"
SAMPLES = 12
ROUNDING_MARGIN = 1e-4  # numerical reserve in uncalibrated source units


def rotation_to_axis(theta: float, azimuth: float) -> np.ndarray:
    """Minimal rotation from +Z to a direction tilted by theta at azimuth."""
    s, c = math.sin(theta), math.cos(theta)
    axis = np.array([s * math.cos(azimuth), s * math.sin(azimuth), c])
    cross = np.cross(np.array([0., 0., 1.]), axis)
    skew = np.array([[0., -cross[2], cross[1]], [cross[2], 0., -cross[0]],
                     [-cross[1], cross[0], 0.]])
    matrix = np.eye(3) + skew + skew @ skew / (1 + c)
    if (not np.allclose(matrix @ matrix.T, np.eye(3), atol=1e-12)
            or not np.allclose(matrix @ np.array([0., 0., 1.]), axis, atol=1e-12)):
        raise ValueError("Tilt rotation fixture failed")
    return matrix


def between_azimuth_motion(radius: float, theta: float, count: int) -> float:
    """Maximum point motion to the nearest sampled tilt azimuth."""
    if not (math.isfinite(radius) and radius > 0 and 0 <= theta < math.pi / 2 and count >= 3):
        raise ValueError("Bounded radius, tilt and sample count required")
    nearest_delta = math.pi / count
    quaternion_dot = math.cos(theta / 2)**2 + math.sin(theta / 2)**2 * math.cos(nearest_delta)
    relative_angle = 2 * math.acos(min(1., max(-1., quaternion_dot)))
    return 2 * radius * math.sin(relative_angle / 2)


def max_vertex_norm(path: Path, triangles: int) -> float:
    vertices = np.memmap(path, mode="r", dtype=DTYPE, offset=84, shape=(triangles,))["vertices"]
    maximum = 0.
    for start in range(0, triangles, 100_000):
        chunk = np.asarray(vertices[start:start + 100_000], dtype=np.float64)
        maximum = max(maximum, float(np.linalg.norm(chunk, axis=-1).max()))
    return maximum


def run(native: Path, assembly: Path, axis_path: Path, target: Path) -> None:
    native, assembly, axis_path, target = map(Path.resolve, (native, assembly, axis_path, target))
    if target.exists() or not target.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("Use a new private work/ report")
    if sha(native / "receipt.json") != HUB_SHA256 or sha(axis_path) != AXIS_SHA256:
        raise ValueError("Pinned PicoGK or axis receipt changed")
    hub = json.loads((native / "receipt.json").read_text())
    axis = json.loads(axis_path.read_text())
    parent = json.loads((assembly / "receipt.json").read_text())
    drive_row = next(row for row in parent["components"] if row["id"] == "drive_observed")
    drive_path = assembly / drive_row["file"]
    mesh_path = native / "hub-space-hypothesis.stl"
    if (hub["status"] != "visual_hub_space_hypothesis_not_a_coupling"
            or hub["functional_component"] or hub["scale_verified"]
            or sha(mesh_path) != hub["mesh_sha256"]
            or drive_row["sha256"] != DRIVE_SHA256 or sha(drive_path) != DRIVE_SHA256
            or axis["scale_verified"] or axis["operating_clearance_verified"]):
        raise ValueError("Only pinned uncalibrated visual surfaces are accepted")
    angle = math.radians(float(axis["observed_bore_axis_deviation_deg"]))
    observed_axis = np.asarray(axis["observed_bore_axis_in_candidate_frame"], dtype=float)
    if (not 0 < angle < math.radians(2) or abs(np.linalg.norm(observed_axis) - 1) > 1e-6
            or abs(math.acos(observed_axis[2]) - angle) > 1e-6):
        raise ValueError("Observed bore-axis fit inconsistent")
    controls = fixtures()
    if (between_azimuth_motion(1., 0., SAMPLES) != 0
            or between_azimuth_motion(1., angle, 2 * SAMPLES) >= between_azimuth_motion(1., angle, SAMPLES)):
        raise ValueError("Azimuth interpolation fixture failed")
    radius = max_vertex_norm(mesh_path, hub["triangles"])
    motion = between_azimuth_motion(radius, angle, SAMPLES)
    midpoint_operator_norm = float(np.linalg.svd(
        rotation_to_axis(angle, math.pi / SAMPLES) - rotation_to_axis(angle, 0.),
        compute_uv=False)[0])
    if abs(midpoint_operator_norm * radius - motion) > 1e-9:
        raise ValueError("Quaternion interpolation bound disagrees with matrix fixture")
    moving = load(mesh_path, hub["triangles"])
    fixed = load(drive_path, drive_row["triangles"])
    started = time.monotonic()
    rows = []
    for index in range(SAMPLES):
        azimuth = 2 * math.pi * index / SAMPLES
        moving.setTransform(fcl.Transform(rotation_to_axis(angle, azimuth)))
        result = query(moving, fixed)
        rows.append({"azimuth_deg": 360 * index / SAMPLES, **result})
        print(index, result, flush=True)
    distances = [row["minimum_surface_distance_native_units"] for row in rows if not row["surface_crossing"]]
    minimum = min(distances) if len(distances) == SAMPLES else None
    lower = minimum - motion - ROUNDING_MARGIN if minimum is not None else None
    result = {"status": "conditional_hub_space_tilt_azimuth_screen",
              "hub_receipt_sha256": HUB_SHA256, "axis_receipt_sha256": AXIS_SHA256,
              "drive_sha256": DRIVE_SHA256, "samples": SAMPLES,
              "tilt_angle_deg": math.degrees(angle), "tilt_origin_source_units": [0, 0, 0],
              "maximum_vertex_norm_source_units": radius,
              "maximum_between_sample_motion_source_units": motion,
              "rounding_margin_source_units": ROUNDING_MARGIN,
              "sampled_minimum_distance_source_units": minimum,
              "continuous_azimuth_lower_bound_source_units": lower,
              "observed_surfaces_separated_for_this_tilt_magnitude": lower is not None and lower > 0,
              "bound_method": "1-Lipschitz surface distance; quaternion relative rotation to nearest azimuth sample",
              "fixtures": controls, "midpoint_matrix_fixture_passed": True,
              "azimuths": rows, "elapsed_s": time.monotonic() - started,
              "source_unit_to_mm_verified": False, "historical_shaft_axis_verified": False,
              "axis_translation_or_running_deflection_checked": False,
              "thermal_clearance_checked": False, "solid_containment_checked": False,
              "functional_coupling_defined": False, "manufacturing_authorized": False}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n")
    print("report_sha256", sha(target))


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("usage: review_hub_space_tilt.py NATIVE_OUTPUT ASSEMBLY_OUTPUT AXIS_RECEIPT NEW_PRIVATE_JSON")
    run(*(Path(arg) for arg in sys.argv[1:]))
