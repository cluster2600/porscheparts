"""Independently inspect native PicoGK 935 flange-feature witnesses.

The scan comparison is in-sample against the same acquired sidewalls used for
the fitted input. It verifies geometry transport, not fitment or calibration.
"""

import json
from pathlib import Path
import struct
import sys

import numpy as np

from audit_drive_lower_flange import DTYPE, DRIVE_SHA256, digest, selected_faces


def triangles(path: Path) -> np.ndarray:
    with path.open("rb") as stream:
        header = stream.read(84)
    if len(header) != 84:
        raise ValueError("Complete binary STL required")
    count = struct.unpack("<I", header[80:])[0]
    if not 1 <= count <= 1_000_000 or path.stat().st_size != 84 + 50 * count:
        raise ValueError("Bounded binary STL required")
    return np.memmap(path, mode="r", dtype=DTYPE, offset=84, shape=(count,))["vertices"]


def radial_residual(points: np.ndarray, fits: list[dict]) -> np.ndarray:
    low, high = fits
    t = np.clip((points[:, 2] + 185) / 10, 0, 1)
    cx = low["fit_centre_xy_source_units"][0] * (1 - t) + high["fit_centre_xy_source_units"][0] * t
    cy = low["fit_centre_xy_source_units"][1] * (1 - t) + high["fit_centre_xy_source_units"][1] * t
    radius = low["fit_radius_source_units"] * (1 - t) + high["fit_radius_source_units"] * t
    return np.hypot(points[:, 0] - cx, points[:, 1] - cy) - radius


def fixture() -> None:
    fits = [{"fit_centre_xy_source_units": [2, 3], "fit_radius_source_units": 3},
            {"fit_centre_xy_source_units": [2, 3], "fit_radius_source_units": 3}]
    points = np.array([[5, 3, -185], [2, 0, -175]], dtype=float)
    if not np.allclose(radial_residual(points, fits), 0, atol=1e-12):
        raise ValueError("Radial reviewer fixture failed")


def render(scan: np.ndarray, meshes: list[np.ndarray], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    for axis, band in zip(axes, ((-190, -180), (-180, -170))):
        acquired = scan[(scan[:, 2] >= band[0]) & (scan[:, 2] < band[1])]
        for mesh in meshes:
            vertices = mesh.reshape(-1, 3)
            selected = vertices[(vertices[:, 2] >= band[0] + 1) & (vertices[:, 2] < band[1] - 1)]
            axis.scatter(selected[::40, 0], selected[::40, 1], s=.8, color="tab:blue", alpha=.55,
                         rasterized=True)
        axis.scatter(acquired[::5, 0], acquired[::5, 1], s=1.1, color="0.15",
                     alpha=.65, rasterized=True, label="acquired sidewall centroids")
        axis.set(xlim=(30, 170), ylim=(-70, 70), xlabel="X, source units",
                 ylabel="Y, source units", title=f"Scan and PicoGK witnesses, Z {band}")
        axis.set_aspect("equal")
    axes[0].legend(markerscale=4, loc="upper right")
    fig.suptitle("935 lower flange: analytic wall witnesses; no physical mounting claim")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run(scan_path: Path, report_path: Path, native: Path, output: Path) -> None:
    scan_path, report_path, native, output = (path.resolve() for path in (scan_path, report_path, native, output))
    if output.exists() or not output.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("Use a new private work/ output directory")
    if digest(scan_path) != DRIVE_SHA256:
        raise ValueError("Pinned observed drive surface changed")
    fixture()
    report = json.loads(report_path.read_text())
    receipt = json.loads((native / "receipt.json").read_text())
    if (receipt["status"] != "PicoGK_scan_feature_witness_only"
            or receipt["report_sha256"] != digest(report_path)
            or receipt["drive_stl_sha256"] != DRIVE_SHA256
            or receipt["source_unit_to_mm_verified"] is not False
            or receipt["manufacturing_authorized"] is not False
            or receipt["physical_validation"] is not False
            or len(report["openings"]) != 8 or len(receipt["openings"]) != 8):
        raise ValueError("Unqualified witness lineage mismatch")
    all_triangles = triangles(native / receipt["combined_file"])
    if digest(native / receipt["combined_file"]) != receipt["combined_sha256"]:
        raise ValueError("Combined native mesh changed")
    scan = selected_faces(scan_path)
    rows, meshes, offset = [], [], 0
    for i, (opening, row) in enumerate(zip(report["openings"], receipt["openings"])):
        if row["id"] != i or row["file"] != f"opening_{i:02}.stl":
            raise ValueError("Unexpected witness order")
        path = native / row["file"]
        if digest(path) != row["sha256"]:
            raise ValueError("Native component changed")
        mesh = triangles(path)
        if len(mesh) != row["triangles"] or not np.array_equal(all_triangles[offset:offset + len(mesh)], mesh):
            raise ValueError("Native concatenation changed triangle coordinates or order")
        offset += len(mesh)
        v = np.asarray(mesh, dtype=np.float64)
        cross = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
        if np.any(np.linalg.norm(cross, axis=1) == 0):
            raise ValueError("Zero-area witness triangle")
        vertices = v.reshape(-1, 3)
        vertices = vertices[(vertices[:, 2] > -189.5) & (vertices[:, 2] < -170.5)]
        residual = radial_residual(vertices, opening["fits"])
        shell_distance = np.minimum(np.abs(residual - .4), np.abs(residual + .4))
        seed = opening["seed_xy_source_units"]
        near = np.hypot(scan[:, 0] - seed[0], scan[:, 1] - seed[1]) < 4.5
        observed = np.abs(radial_residual(scan[near], opening["fits"]))
        shell_q95 = float(np.quantile(shell_distance, .95))
        scan_q95 = float(np.quantile(observed, .95))
        if shell_q95 > .03 or scan_q95 > .35:
            raise ValueError("Witness or acquired-wall deviation exceeds diagnostic bound")
        rows.append({"id": i, "native_triangles": len(mesh),
                     "native_shell_distance_q95_source_units": shell_q95,
                     "acquired_wall_in_sample_radial_q95_source_units": scan_q95,
                     "acquired_wall_max_radial_residual_source_units": float(observed.max()),
                     "acquired_sidewall_face_centroids": int(near.sum())})
        meshes.append(mesh)
    if offset != len(all_triangles) or offset != receipt["combined_triangles"]:
        raise ValueError("Native triangle total changed")
    result = {"status": "native_witness_transport_and_in_sample_wall_screen_passed",
              "drive_stl_sha256": DRIVE_SHA256, "fit_report_sha256": digest(report_path),
              "native_receipt_sha256": digest(native / "receipt.json"),
              "combined_native_sha256": receipt["combined_sha256"],
              "combined_native_triangles": offset, "components": rows,
              "comparison_is_independent_metrology": False,
              "source_unit_to_mm_verified": False, "interface_verified": False,
              "manufacturing_authorized": False, "physical_validation": False}
    output.mkdir(parents=True, mode=0o700)
    path, image = output / "review.json", output / "witness-overlay.png"
    path.write_text(json.dumps(result, indent=2) + "\n")
    render(scan, meshes, image)
    for file in output.iterdir():
        file.chmod(0o600)
    print(json.dumps({"status": result["status"], "review_sha256": digest(path),
                      "image_sha256": digest(image)}))


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("usage: review_flange_witness.py PINNED_DRIVE_STL FIT_REPORT NATIVE_DIR NEW_PRIVATE_OUTPUT")
    run(*(Path(arg) for arg in sys.argv[1:]))
