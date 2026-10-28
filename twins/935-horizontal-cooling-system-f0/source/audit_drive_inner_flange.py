"""Audit the eight larger interior openings on the observed 935 drive flange.

This is scan-feature metrology in uncalibrated source units, not a mounting
pattern, through-hole certificate, or manufacturing specification.
"""

import json
import math
from pathlib import Path
import struct
import sys

import numpy as np
from scipy.optimize import least_squares

from audit_drive_axial_openings import DRIVE_SHA256, DTYPE, digest


OUTER_REPORT_SHA256 = "da8093bb6c71cd364035dfcf5ced88732062a108c0a8af2ead21e6b111900c3c"
SEEDS = ((60, 20), (84, 41), (114, 41), (138, 20),
         (138, -13), (114, -34), (84, -34), (60, -13))
BANDS = ((-175.0, -170.0), (-170.0, -165.0))


def sidewall_centroids(path: Path) -> np.ndarray:
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
        vertices = np.asarray(triangles[offset:offset + 100_000], dtype=np.float64)
        centres = vertices.mean(axis=1)
        cross = np.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0])
        normal_z = np.abs(cross[:, 2]) / np.maximum(np.linalg.norm(cross, axis=1), 1e-30)
        radial = np.hypot(centres[:, 0] - 99.28, centres[:, 1] - 2)
        keep = ((radial > 22) & (radial < 50) & (centres[:, 2] >= -175)
                & (centres[:, 2] < -165) & (normal_z < .7))
        chunks.append(centres[keep])
    return np.concatenate(chunks)


def fit_opening(faces: np.ndarray, seed: tuple[int, int], band: tuple[float, float]) -> dict:
    x, y = seed
    near = np.hypot(faces[:, 0] - x, faces[:, 1] - y) < 10
    xy = faces[near & (faces[:, 2] >= band[0]) & (faces[:, 2] < band[1]), :2]
    if len(xy) < 500:
        raise ValueError("Too few acquired inner sidewall faces")
    bounds = ([x - 4, y - 4, 4], [x + 4, y + 4, 11])
    fit = least_squares(lambda p: np.hypot(xy[:, 0] - p[0], xy[:, 1] - p[1]) - p[2],
                        (x, y, 7.5), loss="soft_l1", f_scale=.1, bounds=bounds)
    if not fit.success:
        raise ValueError("Initial inner-opening fit failed")
    centre_radius = fit.x
    acquired_count = len(xy)
    for _ in range(3):
        radial = np.hypot(xy[:, 0] - centre_radius[0], xy[:, 1] - centre_radius[1])
        retained = xy[np.abs(radial - centre_radius[2]) < .8]
        if len(retained) < 200:
            raise ValueError("Clipped inner-opening arc too sparse")
        fit = least_squares(lambda p: np.hypot(retained[:, 0] - p[0],
                                              retained[:, 1] - p[1]) - p[2],
                            centre_radius, loss="soft_l1", f_scale=.1, bounds=bounds)
        if not fit.success:
            raise ValueError("Refined inner-opening fit failed")
        centre_radius = fit.x
    cx, cy, radius = map(float, centre_radius)
    residual = np.hypot(retained[:, 0] - cx, retained[:, 1] - cy) - radius
    angles = np.sort(np.mod(np.arctan2(retained[:, 1] - cy, retained[:, 0] - cx), 2 * math.pi))
    coverage = math.degrees(2 * math.pi - np.diff(np.r_[angles, angles[0] + 2 * math.pi]).max())
    return {"seed_xy_source_units": seed, "z_band_source_units": band,
            "selected_sidewall_face_centroids": acquired_count,
            "retained_after_radial_clipping": len(retained),
            "fit_centre_xy_source_units": [cx, cy], "fit_radius_source_units": radius,
            "clipped_radial_rms_source_units": float(np.sqrt(np.mean(residual**2))),
            "angular_coverage_deg": coverage}


def fit_ring(centres: np.ndarray) -> dict:
    fit = least_squares(lambda p: np.hypot(centres[:, 0] - p[0], centres[:, 1] - p[1]) - p[2],
                        (99, 2, 39))
    if not fit.success:
        raise ValueError("Inner ring fit failed")
    cx, cy, radius = map(float, fit.x)
    radial = np.hypot(centres[:, 0] - cx, centres[:, 1] - cy)
    angles = np.sort(np.mod(np.arctan2(centres[:, 1] - cy, centres[:, 0] - cx), 2 * math.pi))
    steps = np.degrees(np.diff(np.r_[angles, angles[0] + 2 * math.pi]))
    return {"centre_xy_source_units": [cx, cy], "radius_source_units": radius,
            "diameter_source_units": 2 * radius,
            "radial_rms_source_units": float(np.sqrt(np.mean((radial - radius)**2))),
            "maximum_absolute_step_deviation_from_45_deg": float(np.max(np.abs(steps - 45))),
            "angular_steps_deg": list(map(float, steps))}


def fixture() -> None:
    angle = np.arange(8) * math.pi / 4 + math.pi / 8
    centres = np.column_stack((99 + 39 * np.cos(angle), 2 + 39 * np.sin(angle)))
    pattern = fit_ring(centres)
    if (np.linalg.norm(np.asarray(pattern["centre_xy_source_units"]) - [99, 2]) > 1e-6
            or abs(pattern["radius_source_units"] - 39) > 1e-6):
        raise ValueError("Eight-centre ring fixture failed")
    sample = np.linspace(0, 2 * math.pi, 600, endpoint=False)
    xy = np.column_stack((60 + 7.5 * np.cos(sample), 20 + 7.5 * np.sin(sample),
                          np.full(len(sample), -172.5)))
    opening = fit_opening(xy, (60, 20), BANDS[0])
    if abs(opening["fit_radius_source_units"] - 7.5) > 1e-6:
        raise ValueError("Inner opening fixture failed")


def render(faces: np.ndarray, openings: list[dict], rings: list[dict], outer: list[dict],
           path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    for index, (axis, band) in enumerate(zip(axes, BANDS)):
        selected = faces[(faces[:, 2] >= band[0]) & (faces[:, 2] < band[1])]
        axis.scatter(selected[:, 0], selected[:, 1], s=.12, c="0.5", rasterized=True)
        for row in openings:
            fit = row["fits"][index]
            xy = fit["fit_centre_xy_source_units"]
            axis.add_patch(plt.Circle(xy, fit["fit_radius_source_units"],
                                      fill=False, edgecolor="tab:red", linewidth=1))
            axis.plot(*xy, "r+", markersize=4)
        axis.add_patch(plt.Circle(rings[index]["centre_xy_source_units"],
                                  rings[index]["radius_source_units"], fill=False,
                                  edgecolor="tab:blue", linewidth=1))
        axis.add_patch(plt.Circle(outer[index]["centre_xy_source_units"],
                                  outer[index]["radius_source_units"], fill=False,
                                  edgecolor="tab:green", linewidth=.8, linestyle="--"))
        axis.set(xlim=(45, 155), ylim=(-52, 53), xlabel="X, source units",
                 ylabel="Y, source units", title=f"Acquired sidewalls, Z {band}")
        axis.set_aspect("equal")
    fig.suptitle("935 drive flange: inner opening candidates; outer ring from earlier scan audit")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run(drive: Path, outer_report: Path, output: Path) -> None:
    drive, outer_report, output = (path.resolve() for path in (drive, outer_report, output))
    if output.exists() or not output.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("Use a new private work/ output directory")
    if digest(drive) != DRIVE_SHA256 or digest(outer_report) != OUTER_REPORT_SHA256:
        raise ValueError("Pinned observed drive or outer flange audit changed")
    outer = json.loads(outer_report.read_text())
    if (outer["drive_stl_sha256"] != DRIVE_SHA256
            or outer["status"] != "eight_lower_flange_opening_candidates_only"
            or outer["source_unit_to_mm_verified"] is not False
            or outer["mounting_role_verified"] is not False):
        raise ValueError("Unqualified outer flange audit required")
    fixture()
    faces = sidewall_centroids(drive)
    openings = [{"seed_xy_source_units": seed,
                 "fits": [fit_opening(faces, seed, band) for band in BANDS]} for seed in SEEDS]
    rings = [fit_ring(np.asarray([row["fits"][i]["fit_centre_xy_source_units"]
                                    for row in openings])) for i in range(len(BANDS))]
    outer_rings = outer["outer_circle_fits"]
    if len(outer_rings) != 2:
        raise ValueError("Two outer flange ring fits required")
    cross = []
    for inner, exterior in zip(rings, outer_rings):
        offset = float(np.linalg.norm(np.asarray(inner["centre_xy_source_units"])
                                      - exterior["centre_xy_source_units"]))
        cross.append({"centre_offset_source_units": offset,
                      "inner_to_outer_radius_ratio": inner["radius_source_units"]
                      / exterior["radius_source_units"]})
    result = {"status": "eight_inner_flange_recess_candidates_only",
              "drive_stl_sha256": DRIVE_SHA256, "outer_report_sha256": OUTER_REPORT_SHA256,
              "seeds_xy_source_units": SEEDS, "z_bands_source_units": BANDS,
              "openings": openings, "inner_circle_fits": rings,
              "comparison_to_outer_circle_same_scan": cross,
              "same_scan_bands_are_independent_dimensions": False,
              "source_unit_to_mm_verified": False, "through_holes_verified": False,
              "mounting_role_verified": False, "bolt_pattern_defined": False,
              "manufacturing_authorized": False}
    output.mkdir(parents=True, mode=0o700)
    report, image = output / "inner-flange.json", output / "inner-flange.png"
    report.write_text(json.dumps(result, indent=2) + "\n")
    render(faces, openings, rings, outer_rings, image)
    for file in output.iterdir():
        file.chmod(0o600)
    print(json.dumps({"status": result["status"], "report_sha256": digest(report),
                      "image_sha256": digest(image)}))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: audit_drive_inner_flange.py PINNED_DRIVE_STL OUTER_REPORT NEW_PRIVATE_OUTPUT")
    run(*(Path(arg) for arg in sys.argv[1:]))
