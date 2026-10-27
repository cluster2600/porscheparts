"""Test whether the partial 935 drive-output arc supports a spline count."""

import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import numpy as np

DRIVE_SHA256 = "fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35"
HUB_SHA256 = "b45d4eab6d6a6d8ac89035bbf8d23d0f9fb3b110a9fc1a479e2e46430bd8a660"
DTYPE = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def selected_centroids(path: Path) -> np.ndarray:
    with path.open("rb") as stream:
        header = stream.read(84)
    if len(header) != 84:
        raise ValueError("Binary STL header required")
    count = struct.unpack("<I", header[80:])[0]
    if not 1 <= count <= 5_000_000 or path.stat().st_size != 84 + 50 * count:
        raise ValueError("Complete bounded binary STL required")
    triangles = np.memmap(path, mode="r", dtype=DTYPE, offset=84, shape=(count,))["vertices"]
    chunks = []
    for offset in range(0, count, 100_000):
        centres = triangles[offset:offset + 100_000].mean(axis=1)
        radii = np.hypot(centres[:, 0], centres[:, 1])
        keep = ((centres[:, 2] >= -20) & (centres[:, 2] < 0)
                & (radii > 5.5) & (radii < 8.5))
        chunks.append(np.asarray(centres[keep], dtype=np.float64))
    return np.concatenate(chunks)


def blocked_angular_holdout(z: np.ndarray, radius: np.ndarray, angle: np.ndarray) -> list[dict]:
    """Predict four held-out contiguous angular sectors, fitting only the others."""
    sorted_angles = np.sort(angle)
    circular_gaps = np.diff(np.r_[sorted_angles, sorted_angles[0] + 2 * math.pi])
    seam = sorted_angles[(int(np.argmax(circular_gaps)) + 1) % len(angle)]
    unwrapped = np.mod(angle - seam, 2 * math.pi)
    folds = np.array_split(np.argsort(unwrapped), 4)
    residuals = np.zeros((35, 2), dtype=np.float64)
    fold_scores = np.zeros((35, 4), dtype=np.float64)
    for fold_index, test in enumerate(folds):
        train = np.ones(len(z), dtype=bool)
        train[test] = False
        base = np.column_stack((np.ones(len(z)), z, np.cos(angle), np.sin(angle)))
        base_coefficients = np.linalg.lstsq(base[train], radius[train], rcond=None)[0]
        base_sse = float(np.sum((radius[test] - base[test] @ base_coefficients)**2))
        if base_sse <= 0:
            raise ValueError("Nonpositive held-out baseline error")
        for index, period in enumerate(range(6, 41)):
            design = np.column_stack((base, np.cos(period * angle), np.sin(period * angle)))
            coefficients = np.linalg.lstsq(design[train], radius[train], rcond=None)[0]
            candidate_sse = float(np.sum((radius[test] - design[test] @ coefficients)**2))
            residuals[index] += (base_sse, candidate_sse)
            fold_scores[index, fold_index] = 1 - candidate_sse / base_sse
    rows = [{"lobes_hypothesis": period,
             "held_out_mse_reduction_fraction": float(1 - residuals[index, 1] / residuals[index, 0]),
             "fold_reductions": fold_scores[index].tolist()}
            for index, period in enumerate(range(6, 41))]
    rows.sort(key=lambda row: row["held_out_mse_reduction_fraction"], reverse=True)
    return rows


def fit_band(points: np.ndarray, low: int, high: int) -> dict:
    z = points[:, 2]
    points = points[(z >= low) & (z < high)]
    if len(points) < 500 or not np.isfinite(points).all():
        raise ValueError("Insufficient finite acquired sidewall points")
    x, y, z = points.T
    radius, angle = np.hypot(x, y), np.arctan2(y, x)
    base = np.column_stack((np.ones(len(z)), z - z.mean(), np.cos(angle), np.sin(angle)))
    base_fit = base @ np.linalg.lstsq(base, radius, rcond=None)[0]
    mse_base = float(np.mean((radius - base_fit)**2))
    if mse_base <= 0:
        raise ValueError("Nonpositive baseline variance")
    periods = []
    for count in range(6, 41):
        design = np.column_stack((base, np.cos(count * angle), np.sin(count * angle)))
        coefficients = np.linalg.lstsq(design, radius, rcond=None)[0]
        mse = float(np.mean((radius - design @ coefficients)**2))
        periods.append({"lobes_hypothesis": count,
                        "in_sample_mse_reduction_fraction": 1 - mse / mse_base,
                        "harmonic_amplitude_source_units": float(np.hypot(*coefficients[-2:])),
                        "harmonic_phase_deg_modulo_pitch": float(math.degrees(math.atan2(coefficients[-1], coefficients[-2])) / count)})
    periods.sort(key=lambda row: row["in_sample_mse_reduction_fraction"], reverse=True)
    holdout = blocked_angular_holdout(z, radius, angle)
    return {"z_band_source_units": [low, high], "face_centroids": len(points),
            "baseline_radial_rms_source_units": math.sqrt(mse_base),
            "ranked_periods": periods, "top_period": periods[0]["lobes_hypothesis"],
            "held_out_ranked_periods": holdout,
            "held_out_top_period": holdout[0]["lobes_hypothesis"],
            "period_22_held_out_mse_reduction_fraction": next(row["held_out_mse_reduction_fraction"]
                                                              for row in holdout if row["lobes_hypothesis"] == 22),
            "period_22_in_sample_mse_reduction_fraction": next(row["in_sample_mse_reduction_fraction"]
                                                               for row in periods if row["lobes_hypothesis"] == 22)}


def fixture() -> None:
    angle = np.linspace(-2.9, .35, 800)
    z = np.linspace(-20, -15, len(angle))
    radius = 7 + .08 * np.cos(22 * angle + .2) + .1 * np.cos(angle)
    points = np.column_stack((radius * np.cos(angle), radius * np.sin(angle), z))
    result = fit_band(points, -20, -15)
    if (result["top_period"] != 22 or result["held_out_top_period"] != 22
            or result["period_22_in_sample_mse_reduction_fraction"] < .99
            or result["period_22_held_out_mse_reduction_fraction"] < .99):
        raise ValueError("Known 22-period fixture failed")
    wrapped = angle + 3.1
    rotated_points = np.column_stack((radius * np.cos(wrapped), radius * np.sin(wrapped), z))
    rotated_result = fit_band(rotated_points, -20, -15)
    if (rotated_result["held_out_top_period"] != 22
            or rotated_result["period_22_held_out_mse_reduction_fraction"] < .99):
        raise ValueError("Angular seam fixture failed")


def run(drive: Path, metrology: Path, target: Path) -> None:
    drive, metrology, target = drive.resolve(), metrology.resolve(), target.resolve()
    if target.exists() or not target.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("Use a new private work/ report")
    if digest(drive) != DRIVE_SHA256 or digest(metrology) != HUB_SHA256:
        raise ValueError("Pinned scan-derived input changed")
    reference = json.loads(metrology.read_text())
    if reference["scale_verified"] or reference["shaft_hub_fit_verified"]:
        raise ValueError("This audit only covers the unresolved output arc")
    fixture()
    centres = selected_centroids(drive)
    bands = [fit_band(centres, low, high) for low, high in ((-20, -15), (-15, -10), (-10, -5), (-5, 0))]
    for band, reference_band in zip(bands, reference["sidewall_circle_fits"]["drive_observed"]):
        if band["z_band_source_units"] != reference_band["z_band_source_units"]:
            raise ValueError("Axial band registration changed")
    result = {"status": "partial_output_arc_no_spline_count_admitted",
              "drive_stl_sha256": DRIVE_SHA256, "metrology_sha256": HUB_SHA256,
              "method": "Per-band radial least-squares baseline in Z and first angular harmonic; one higher harmonic at a time, 6 to 40; four contiguous angular holdout sectors with train-only fits",
              "selection_radius_source_units": [5.5, 8.5],
              "fixture_22_lobes_passed": True, "angular_seam_fixture_passed": True,
              "bands": bands,
              "full_output_circumference_observed": False,
              "in_sample_scores_are_independent_validation": False,
              "held_out_sectors_are_independent_scans": False,
              "output_spline_count_verified": False, "thread_pitch_verified": False,
              "source_unit_to_mm_verified": False, "manufacturing_authorized": False}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"],
                      "top_periods": [band["top_period"] for band in bands],
                      "held_out_top_periods": [band["held_out_top_period"] for band in bands],
                      "sha256": digest(target)}))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: audit_output_patch_periods.py DRIVE_STL HUB_METROLOGY_JSON NEW_PRIVATE_JSON")
    run(*(Path(arg) for arg in sys.argv[1:]))
