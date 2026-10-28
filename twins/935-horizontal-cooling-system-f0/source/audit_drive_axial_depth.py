"""Compare acquired sidewalls through the depth of two drive openings.

Coordinates are uncalibrated source units. Separate axial bands from one scan
are correlated observations, not independent dimensions or a hole certificate.
"""

import json
from pathlib import Path
import sys

import numpy as np

from audit_drive_axial_openings import (
    DRIVE_SHA256, SEEDS, digest, fit_opening, fixture, nearby_faces,
)


BANDS = ((-54.0, -49.0), (-49.0, -44.0), (-44.0, -39.0))


def analyze(faces: np.ndarray) -> dict:
    openings = []
    for seed in SEEDS:
        fits = [fit_opening(faces, seed, band) for band in BANDS]
        centers = np.asarray([fit["fit_centre_xy_source_units"] for fit in fits])
        radii = np.asarray([fit["fit_radius_source_units"] for fit in fits])
        pairwise = np.linalg.norm(centers[:, None, :] - centers[None, :, :], axis=2)
        openings.append({
            "seed_xy_source_units": seed,
            "axial_band_fits": fits,
            "maximum_fitted_centre_separation_source_units": float(pairwise.max()),
            "fitted_radius_range_source_units": [float(radii.min()), float(radii.max())],
            "minimum_angular_coverage_deg": min(fit["angular_coverage_deg"] for fit in fits),
        })
    return {
        "status": "axial_depth_partial_sidewalls_only",
        "drive_stl_sha256": DRIVE_SHA256,
        "selection": {"z_bands_source_units": BANDS,
                      "maximum_seed_radius_source_units": 4.5,
                      "maximum_abs_normal_z_for_sidewall": 0.7},
        "openings": openings,
        "same_scan_bands_are_independent_dimensions": False,
        "through_holes_verified": False,
        "mounting_role_verified": False,
        "source_unit_to_mm_verified": False,
        "manufacturing_authorized": False,
    }


def render(faces: np.ndarray, result: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, panels = plt.subplots(2, 2, figsize=(12, 8), sharey=True)
    for row, (seed, opening) in enumerate(zip(SEEDS, result["openings"])):
        selected = faces[np.hypot(faces[:, 0] - seed[0], faces[:, 1] - seed[1]) < 5]
        for col, component in enumerate((0, 1)):
            panel = panels[row, col]
            panel.scatter(selected[:, component], selected[:, 2], c=selected[:, 3],
                          vmin=0, vmax=1, cmap="viridis", s=0.3, rasterized=True)
            for fit in opening["axial_band_fits"]:
                centre = fit["fit_centre_xy_source_units"][component]
                radius = fit["fit_radius_source_units"]
                middle = sum(fit["z_window_source_units"]) / 2
                panel.plot((centre - radius, centre + radius), (middle, middle),
                           "r.", markersize=3)
            panel.set(xlabel=("X" if col == 0 else "Y") + ", source units",
                      ylabel="Z, source units",
                      title=f"Seed Y={seed[1]:.0f}; " + ("XZ" if col == 0 else "YZ"))
            panel.set_ylim(-55, -38)
            panel.grid(alpha=0.2)
    fig.suptitle("935 drive: axial sections; red = partial-circle spans, colour = |normal Z|")
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
    result = analyze(faces)
    output.mkdir(parents=True, mode=0o700)
    report = output / "axial-depth.json"
    figure = output / "axial-depth.png"
    report.write_text(json.dumps(result, indent=2) + "\n")
    render(faces, result, figure)
    for file in output.iterdir():
        file.chmod(0o600)
    print(json.dumps({"status": result["status"], "report_sha256": digest(report),
                      "image_sha256": digest(figure)}))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: audit_drive_axial_depth.py PINNED_DRIVE_STL NEW_PRIVATE_OUTPUT_DIR")
    run(Path(sys.argv[1]), Path(sys.argv[2]))
