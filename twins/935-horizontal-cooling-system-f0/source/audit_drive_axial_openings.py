"""Inspect two visible round openings near the 935 drive output axis.

The coordinates are in uncalibrated assembly source units. This is a partial
surface audit, not a mounting pattern or a through-hole certification.
"""

import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import numpy as np
from scipy.optimize import least_squares

DRIVE_SHA256 = "fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35"
DTYPE = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
SEEDS = ((0.0, 30.0), (0.0, -30.0))  # visual picks in the provisional assembly frame
Z_WINDOWS = ((-43.0, -39.0), (-41.0, -39.0))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def nearby_faces(path: Path) -> np.ndarray:
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
        double_area = np.linalg.norm(cross, axis=1)
        nz = np.abs(cross[:, 2]) / np.maximum(double_area, 1e-30)
        near_seed = np.minimum(*(np.hypot(centres[:, 0] - x, centres[:, 1] - y)
                                 for x, y in SEEDS)) < 8.0
        keep = near_seed & (centres[:, 2] >= -55) & (centres[:, 2] < -38)
        chunks.append(np.column_stack((centres[keep], nz[keep])))
    return np.concatenate(chunks)


def fit_opening(faces: np.ndarray, seed: tuple[float, float], z_window: tuple[float, float]) -> dict:
    x, y = seed
    low, high = z_window
    radial = np.hypot(faces[:, 0] - x, faces[:, 1] - y)
    selected = faces[(radial < 4.5) & (faces[:, 2] >= low) & (faces[:, 2] < high)
                     & (faces[:, 3] < 0.7)]
    if len(selected) < 200:
        raise ValueError("Insufficient acquired sidewall faces for opening fit")
    xy = selected[:, :2]
    fit = least_squares(lambda p: np.hypot(xy[:, 0] - p[0], xy[:, 1] - p[1]) - p[2],
                        (x, y, 3.0), loss="soft_l1", f_scale=0.1,
                        bounds=([-10, y - 10, 0.1], [10, y + 10, 10]))
    if not fit.success:
        raise ValueError("Opening circle fit did not converge")
    cx, cy, radius = map(float, fit.x)
    residual = np.hypot(xy[:, 0] - cx, xy[:, 1] - cy) - radius
    angles = np.sort(np.mod(np.arctan2(xy[:, 1] - cy, xy[:, 0] - cx), 2 * math.pi))
    coverage = math.degrees(2 * math.pi - np.diff(np.r_[angles, angles[0] + 2 * math.pi]).max())
    return {"seed_xy_source_units": [x, y], "z_window_source_units": [low, high],
            "sidewall_face_centroids": len(selected), "fit_centre_xy_source_units": [cx, cy],
            "fit_radius_source_units": radius,
            "radial_rms_source_units": float(np.sqrt(np.mean(residual**2))),
            "radial_absolute_q95_source_units": float(np.quantile(np.abs(residual), .95)),
            "angular_coverage_deg": coverage}


def fixture() -> None:
    angles = np.linspace(-2.4, 2.4, 320)
    centre = (0.7, 30.4)
    radius = 3.2
    faces = np.column_stack((centre[0] + radius * np.cos(angles),
                             centre[1] + radius * np.sin(angles),
                             np.full(len(angles), -40.0), np.zeros(len(angles))))
    result = fit_opening(faces, SEEDS[0], Z_WINDOWS[0])
    if (np.linalg.norm(np.asarray(result["fit_centre_xy_source_units"]) - centre) > 1e-3
            or abs(result["fit_radius_source_units"] - radius) > 1e-3
            or not 260 < result["angular_coverage_deg"] < 280):
        raise ValueError("Partial-circle fit fixture failed")


def render(faces: np.ndarray, fits: list[dict], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, panels = plt.subplots(1, 2, figsize=(11, 5))
    for panel, seed, fit in zip(panels, SEEDS, fits):
        near = faces[np.hypot(faces[:, 0] - seed[0], faces[:, 1] - seed[1]) < 7]
        panel.scatter(near[:, 0], near[:, 1], c=near[:, 2], s=.5,
                      cmap="turbo", vmin=-55, vmax=-38, rasterized=True)
        centre = fit["fit_centre_xy_source_units"]
        circle = plt.Circle(centre, fit["fit_radius_source_units"], fill=False,
                            color="black", linewidth=1.4)
        panel.add_patch(circle)
        panel.set(xlabel="X, source units", ylabel="Y, source units",
                  title=f"Visual seed {seed}; black = partial-arc fit")
        panel.set_aspect("equal")
    fig.suptitle("935 drive: candidate openings, no mounting role or scale established")
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
    faces = nearby_faces(drive)
    fits = [fit_opening(faces, seed, window) for seed in SEEDS for window in Z_WINDOWS]
    primary = fits[::2]
    seed_sensitivity = []
    for seed, nominal in zip(SEEDS, primary):
        variants = [fit_opening(faces, (seed[0] + dx, seed[1] + dy), Z_WINDOWS[0])
                    for dx, dy in ((-0.5, 0), (0.5, 0), (0, -0.5), (0, 0.5))]
        centre = np.asarray(nominal["fit_centre_xy_source_units"])
        seed_sensitivity.append({
            "seed_xy_source_units": seed,
            "perturbation_source_units": 0.5,
            "maximum_centre_shift_source_units": max(float(np.linalg.norm(
                np.asarray(row["fit_centre_xy_source_units"]) - centre)) for row in variants),
            "maximum_radius_shift_source_units": max(abs(row["fit_radius_source_units"]
                                                         - nominal["fit_radius_source_units"]) for row in variants),
            "minimum_angular_coverage_deg": min(row["angular_coverage_deg"] for row in variants)})
    centres = np.asarray([row["fit_centre_xy_source_units"] for row in primary])
    result = {"status": "two_partial_round_openings_geometric_candidates_only",
              "drive_stl_sha256": DRIVE_SHA256,
              "selection": {"seed_xy_source_units": SEEDS, "z_windows_source_units": Z_WINDOWS,
                            "maximum_seed_radius_source_units": 4.5,
                            "maximum_abs_normal_z_for_sidewall": 0.7},
              "fits": fits,
              "visual_seed_sensitivity": seed_sensitivity,
              "candidate_centre_spacing_source_units": float(np.linalg.norm(centres[0] - centres[1])),
              "partial_circle_fixture_passed": True,
              "separate_z_windows_are_independent_scans": False,
              "source_unit_to_mm_verified": False, "mounting_role_verified": False,
              "through_holes_verified": False, "third_or_other_holes_excluded": False,
              "bolt_pattern_defined": False, "manufacturing_authorized": False}
    output.mkdir(parents=True, mode=0o700)
    report = output / "axial-openings.json"
    report.write_text(json.dumps(result, indent=2) + "\n")
    render(faces, primary, output / "axial-openings.png")
    for path in output.iterdir():
        path.chmod(0o600)
    print(json.dumps({"status": result["status"], "report_sha256": digest(report),
                      "image_sha256": digest(output / "axial-openings.png")}))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: audit_drive_axial_openings.py PINNED_DRIVE_STL NEW_PRIVATE_OUTPUT_DIR")
    run(Path(sys.argv[1]), Path(sys.argv[2]))
