"""Audit eight visible small openings on the lower 935 drive flange.

All coordinates are in uncalibrated source units. The visible openings do not
establish their mating role, a through condition or a manufacturing pattern.
"""

import json
import math
from pathlib import Path
import struct
import sys

import numpy as np
from scipy.optimize import least_squares

from audit_drive_axial_openings import DRIVE_SHA256, DTYPE, digest


SEEDS = ((157.15, 2.15), (140, 44), (100, 60), (60, 44),
         (40, 4), (60, -40), (100, -55), (140, -40))
BANDS = ((-190.0, -180.0), (-180.0, -170.0))


def selected_faces(path: Path) -> np.ndarray:
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
        nz = np.abs(cross[:, 2]) / np.maximum(np.linalg.norm(cross, axis=1), 1e-30)
        near = np.minimum.reduce([np.hypot(centres[:, 0] - x, centres[:, 1] - y)
                                  for x, y in SEEDS]) < 4.5
        keep = near & (centres[:, 2] >= -190) & (centres[:, 2] < -170) & (nz < .7)
        chunks.append(centres[keep])
    return np.concatenate(chunks)


def fit_opening(faces: np.ndarray, seed: tuple[float, float], band: tuple[float, float]) -> dict:
    x, y = seed
    near = np.hypot(faces[:, 0] - x, faces[:, 1] - y) < 4.5
    xy = faces[near & (faces[:, 2] >= band[0]) & (faces[:, 2] < band[1]), :2]
    if len(xy) < 200:
        raise ValueError("Insufficient acquired sidewall faces")
    fit = least_squares(lambda p: np.hypot(xy[:, 0] - p[0], xy[:, 1] - p[1]) - p[2],
                        (x, y, 2.6), loss="soft_l1", f_scale=.1,
                        bounds=([x - 5, y - 5, .2], [x + 5, y + 5, 5]))
    if not fit.success:
        raise ValueError("Partial circle fit failed")
    cx, cy, radius = map(float, fit.x)
    residual = np.hypot(xy[:, 0] - cx, xy[:, 1] - cy) - radius
    angles = np.sort(np.mod(np.arctan2(xy[:, 1] - cy, xy[:, 0] - cx), 2 * math.pi))
    coverage = math.degrees(2 * math.pi - np.diff(np.r_[angles, angles[0] + 2 * math.pi]).max())
    return {"seed_xy_source_units": [x, y], "z_band_source_units": band,
            "sidewall_face_centroids": len(xy), "fit_centre_xy_source_units": [cx, cy],
            "fit_radius_source_units": radius,
            "radial_rms_source_units": float(np.sqrt(np.mean(residual**2))),
            "angular_coverage_deg": coverage}


def fit_pattern(centres: np.ndarray) -> dict:
    initial = (float(centres[:, 0].mean()), float(centres[:, 1].mean()), 58.0)
    fit = least_squares(lambda p: np.hypot(centres[:, 0] - p[0], centres[:, 1] - p[1]) - p[2],
                        initial)
    if not fit.success:
        raise ValueError("Outer candidate circle fit failed")
    cx, cy, radius = map(float, fit.x)
    residual = np.hypot(centres[:, 0] - cx, centres[:, 1] - cy) - radius
    angles = np.sort(np.mod(np.arctan2(centres[:, 1] - cy, centres[:, 0] - cx), 2 * math.pi))
    steps = np.degrees(np.diff(np.r_[angles, angles[0] + 2 * math.pi]))
    return {"centre_xy_source_units": [cx, cy], "radius_source_units": radius,
            "diameter_source_units": 2 * radius,
            "radial_rms_source_units": float(np.sqrt(np.mean(residual**2))),
            "maximum_absolute_radial_residual_source_units": float(np.max(np.abs(residual))),
            "angular_steps_deg": list(map(float, steps)),
            "maximum_absolute_step_deviation_from_45_deg": float(np.max(np.abs(steps - 45)))}


def fixture() -> None:
    centre = np.array([99.2, 2.1])
    angles = np.linspace(0, 2 * math.pi, 8, endpoint=False)
    ring = centre + 58 * np.column_stack((np.cos(angles), np.sin(angles)))
    pattern = fit_pattern(ring)
    if (np.linalg.norm(np.asarray(pattern["centre_xy_source_units"]) - centre) > 1e-7
            or abs(pattern["radius_source_units"] - 58) > 1e-7):
        raise ValueError("Eight-point pattern fixture failed")
    sample = np.linspace(0, 2 * math.pi, 500, endpoint=False)
    local = np.column_stack((ring[0, 0] + 2.7 * np.cos(sample),
                             ring[0, 1] + 2.7 * np.sin(sample),
                             np.full(len(sample), -185.0)))
    opening = fit_opening(local, tuple(ring[0]), BANDS[0])
    if abs(opening["fit_radius_source_units"] - 2.7) > 1e-6:
        raise ValueError("Opening fixture failed")


def render(faces: np.ndarray, openings: list[dict], patterns: list[dict], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, panels = plt.subplots(1, 2, figsize=(12, 6))
    for index, (panel, band, pattern) in enumerate(zip(panels, BANDS, patterns)):
        selected = faces[(faces[:, 2] >= band[0]) & (faces[:, 2] < band[1])]
        panel.scatter(selected[:, 0], selected[:, 1], s=.12, c="0.4", rasterized=True)
        for opening in openings:
            fit = opening["fits"][index]
            x, y = fit["fit_centre_xy_source_units"]
            panel.add_patch(plt.Circle((x, y), fit["fit_radius_source_units"],
                                        fill=False, edgecolor="tab:red", linewidth=1))
            panel.plot(x, y, "r+", markersize=5)
        panel.add_patch(plt.Circle(pattern["centre_xy_source_units"], pattern["radius_source_units"],
                                    fill=False, edgecolor="tab:blue", linewidth=1))
        panel.set(xlim=(30, 170), ylim=(-70, 70), xlabel="X, source units",
                  ylabel="Y, source units", title=f"Acquired sidewalls, Z {band}")
        panel.set_aspect("equal")
    fig.suptitle("935 drive lower flange: eight geometric candidates, no mounting role established")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run(drive: Path, output: Path) -> None:
    drive, output = drive.resolve(), output.resolve()
    if output.exists() or not output.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("Use a new private work/ output directory")
    if digest(drive) != DRIVE_SHA256:
        raise ValueError("Pinned observed drive surface changed")
    fixture()
    faces = selected_faces(drive)
    openings = [{"seed_xy_source_units": seed,
                 "fits": [fit_opening(faces, seed, band) for band in BANDS]} for seed in SEEDS]
    patterns = [fit_pattern(np.asarray([row["fits"][index]["fit_centre_xy_source_units"]
                                        for row in openings])) for index in range(len(BANDS))]
    result = {"status": "eight_lower_flange_opening_candidates_only",
              "drive_stl_sha256": DRIVE_SHA256, "seeds_xy_source_units": SEEDS,
              "z_bands_source_units": BANDS, "openings": openings,
              "outer_circle_fits": patterns,
              "same_scan_bands_are_independent_dimensions": False,
              "source_unit_to_mm_verified": False, "mounting_role_verified": False,
              "through_holes_verified": False, "bolt_pattern_defined": False,
              "manufacturing_authorized": False}
    output.mkdir(parents=True, mode=0o700)
    report, image = output / "lower-flange.json", output / "lower-flange.png"
    report.write_text(json.dumps(result, indent=2) + "\n")
    render(faces, openings, patterns, image)
    for file in output.iterdir():
        file.chmod(0o600)
    print(json.dumps({"status": result["status"], "report_sha256": digest(report),
                      "image_sha256": digest(image)}))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: audit_drive_lower_flange.py PINNED_DRIVE_STL NEW_PRIVATE_OUTPUT_DIR")
    run(Path(sys.argv[1]), Path(sys.argv[2]))
