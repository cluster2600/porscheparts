"""Render four sampled poses from the inspection-only 935 kinematic USD."""

import json
from pathlib import Path
import sys

import numpy as np

from compose_flange_witness_usd import digest
from render_flange_witness_context import centroids


RECEIPT_SHA256 = "b63b4830d028c3455e7e40e25180f62463057794148b380661483a02f8069a2b"
FRAMES = (0, 60, 120, 180)


def run(native: Path, composed: Path, output: Path) -> None:
    from pxr import Usd, UsdGeom
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    native, composed, output = (path.resolve() for path in (native, composed, output))
    if output.exists() or not output.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("Use a new private work/ output directory")
    receipt_path = native / "receipt.json"
    if digest(receipt_path) != RECEIPT_SHA256:
        raise ValueError("Pinned native assembly required")
    receipt = json.loads(receipt_path.read_text())
    components = {row["id"]: row for row in receipt["components"]}
    if set(components) != {"engine_context", "drive_observed", "rotor_candidate", "provisional_shroud"}:
        raise ValueError("Four original assembly components required")
    report_path = composed / "kinematic-report.json"
    report = json.loads(report_path.read_text())
    stage_path = composed / "kinematic-inspection.usdc"
    if (report["status"] != "kinematic_inspection_only"
            or report["kinematic_usd_sha256"] != digest(stage_path)
            or report["rotor_time_samples"] != 241
            or report["operating_speed_defined"] is not False
            or report["physics_joint_defined"] is not False
            or report["source_unit_to_mm_verified"] is not False):
        raise ValueError("Unqualified 240-phase kinematic USD required")
    stage = Usd.Stage.Open(str(stage_path), load=Usd.Stage.LoadNone)
    if (UsdGeom.GetStageMetersPerUnit(stage) != 1
            or UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z):
        raise ValueError("USD stage metadata changed")
    rotor_prim = stage.GetPrimAtPath("/World/rotor_candidate")
    ops = UsdGeom.Xformable(rotor_prim).GetOrderedXformOps()
    if len(ops) != 1 or ops[0].GetTimeSamples() != list(range(241)):
        raise ValueError("Rotor time samples changed")
    rotor_row = components["rotor_candidate"]
    drive_row = components["drive_observed"]
    shroud_row = components["provisional_shroud"]
    rotor = centroids(native / rotor_row["file"], rotor_row["sha256"], 50_000)
    drive = centroids(native / drive_row["file"], drive_row["sha256"], 50_000)
    shroud = centroids(native / shroud_row["file"], shroud_row["sha256"], 50_000)
    nearby_drive = drive[(drive[:, 0] < 180) & (np.abs(drive[:, 1]) < 150)]
    fig, axes = plt.subplots(2, 2, figsize=(10, 10))
    for ax, frame in zip(axes.flat, FRAMES):
        angle = float(ops[0].Get(Usd.TimeCode(frame)))
        theta = np.deg2rad(angle)
        c, s = np.cos(theta), np.sin(theta)
        rotating_xy = np.column_stack((c * rotor[:, 0] - s * rotor[:, 1],
                                       s * rotor[:, 0] + c * rotor[:, 1]))
        ax.scatter(shroud[:, 0], shroud[:, 1], s=.1, alpha=.16,
                   color="#77a957", rasterized=True)
        ax.scatter(nearby_drive[:, 0], nearby_drive[:, 1], s=.15, alpha=.2,
                   color="#b46e36", rasterized=True)
        ax.scatter(rotating_xy[:, 0], rotating_xy[:, 1], s=.15, alpha=.42,
                   color="#178bb6", rasterized=True)
        ax.set(xlim=(-185, 185), ylim=(-185, 185), title=f"USD frame {frame}: {angle:g}°",
               xlabel="X, source units", ylabel="Y, source units")
        ax.set_aspect("equal")
    fig.suptitle("935 rotor kinematic inspection; provisional Z axis and scale")
    fig.tight_layout()
    output.mkdir(parents=True, mode=0o700)
    image = output / "kinematic-four-poses.png"
    fig.savefig(image, dpi=180)
    plt.close(fig)
    result = {"status": "sampled_kinematic_USD_preview_only",
              "kinematic_report_sha256": digest(report_path),
              "kinematic_usd_sha256": report["kinematic_usd_sha256"],
              "image_sha256": digest(image), "frames": FRAMES,
              "render_is_sampled": True, "axis_verified_on_historical_935": False,
              "operating_speed_defined": False, "physical_validation": False}
    (output / "render-report.json").write_text(json.dumps(result, indent=2) + "\n")
    for file in output.iterdir():
        file.chmod(0o600)
    print(json.dumps({"status": result["status"], "image_sha256": result["image_sha256"]}))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: render_kinematic_usd.py NATIVE_ASSEMBLY KINEMATIC_USD_DIR NEW_PRIVATE_OUTPUT")
    run(*(Path(arg) for arg in sys.argv[1:]))
