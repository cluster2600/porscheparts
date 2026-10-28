"""Render sampled 935 assembly context with witness points from composed USD."""

import json
from pathlib import Path
import struct
import sys

import numpy as np

from compose_flange_witness_usd import DTYPE, DRIVE_SHA256, digest


COLORS = {"engine_context": "#8e9ba4", "drive_observed": "#b46e36",
          "rotor_candidate": "#178bb6", "provisional_shroud": "#77a957"}


def centroids(path: Path, expected_hash: str, target_count: int) -> np.ndarray:
    if digest(path) != expected_hash:
        raise ValueError("Pinned native component changed")
    with path.open("rb") as stream:
        header = stream.read(84)
    count = struct.unpack("<I", header[80:])[0]
    if not 1 <= count <= 5_000_000 or path.stat().st_size != 84 + 50 * count:
        raise ValueError("Complete bounded binary STL required")
    triangles = np.memmap(path, mode="r", dtype=DTYPE, offset=84, shape=(count,))["vertices"]
    step = max(1, count // target_count)
    return np.asarray(triangles[::step], dtype=np.float64).mean(axis=1)


def run(native: Path, composed: Path, output: Path) -> None:
    from pxr import Usd, UsdGeom
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    native, composed, output = (path.resolve() for path in (native, composed, output))
    if output.exists() or not output.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("Use a new private work/ output directory")
    receipt_path = native / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    report = json.loads((composed / "composition-report.json").read_text())
    stage_path = composed / "assembly-with-flange-witness.usdc"
    if (digest(receipt_path) != "b63b4830d028c3455e7e40e25180f62463057794148b380661483a02f8069a2b"
            or report["composed_usd_sha256"] != digest(stage_path)
            or report["base_usd_sha256"] != digest(composed / "base-assembly.usdc")
            or report["source_unit_to_mm_verified"] is not False
            or report["witness_component_count"] != 8):
        raise ValueError("Pinned unqualified composed assembly required")
    components = {row["id"]: row for row in receipt["components"]}
    if set(components) != set(COLORS) or components["drive_observed"]["sha256"] != DRIVE_SHA256:
        raise ValueError("Four pinned assembly components required")
    stage = Usd.Stage.Open(str(stage_path), load=Usd.Stage.LoadNone)
    if UsdGeom.GetStageMetersPerUnit(stage) != 1 or UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z:
        raise ValueError("Composed USD SI units or axis changed")
    witness = []
    for i in range(8):
        mesh = UsdGeom.Mesh(stage.GetPrimAtPath(f"/World/inspection/flange_opening_{i:02}"))
        if not mesh or not mesh.GetPrim().IsValid():
            raise ValueError("Missing USD witness prim")
        witness.append(np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)[::30] * 1000)
    witness = np.concatenate(witness)
    positions = {name: centroids(native / row["file"], row["sha256"], 25000)
                 for name, row in components.items()}
    local_drive = centroids(native / components["drive_observed"]["file"],
                            DRIVE_SHA256, 350000)
    local_drive = local_drive[(local_drive[:, 0] > 25) & (local_drive[:, 0] < 175)
                              & (np.abs(local_drive[:, 1]) < 75)
                              & (local_drive[:, 2] > -195) & (local_drive[:, 2] < -155)]
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for axis, (a, b, title) in zip(axes[0], ((0, 1, "Full assembly — XY"), (0, 2, "Full assembly — XZ"))):
        for name in ("engine_context", "provisional_shroud", "drive_observed", "rotor_candidate"):
            points = positions[name]
            axis.scatter(points[:, a], points[:, b], s=.12, alpha=.2,
                         color=COLORS[name], rasterized=True, label=name)
        axis.scatter(witness[:, a], witness[:, b], s=1.5, alpha=.9,
                     color="magenta", rasterized=True, label="PicoGK flange witnesses")
        axis.set(xlabel="XYZ"[a] + ", source units", ylabel="XYZ"[b] + ", source units",
                 title=title)
        axis.set_aspect("equal")
    axes[0, 0].legend(markerscale=8, fontsize=7, loc="lower left")
    for axis, (a, b, title) in zip(axes[1], ((0, 1, "Drive lower flange — XY"),
                                                (0, 2, "Drive lower flange — XZ"))):
        axis.scatter(local_drive[:, a], local_drive[:, b], s=.12, alpha=.16,
                     color=COLORS["drive_observed"], rasterized=True)
        axis.scatter(witness[:, a], witness[:, b], s=1.2, alpha=.7,
                     color="magenta", rasterized=True)
        axis.set(xlabel="XYZ"[a] + ", source units", ylabel="XYZ"[b] + ", source units",
                 title=title)
        if b == 1:
            axis.set(xlim=(25, 175), ylim=(-75, 75))
        else:
            axis.set(xlim=(25, 175), ylim=(-195, -155))
        axis.set_aspect("equal")
    fig.suptitle("935 inspection assembly: PicoGK wall witnesses in USD; scale and fitment unverified")
    fig.tight_layout()
    output.mkdir(parents=True, mode=0o700)
    image = output / "flange-witness-context.png"
    fig.savefig(image, dpi=180)
    plt.close(fig)
    result = {"status": "sampled_composed_USD_context_review",
              "composition_report_sha256": digest(composed / "composition-report.json"),
              "composed_usd_sha256": report["composed_usd_sha256"],
              "image_sha256": digest(image), "witness_points_rendered": len(witness),
              "native_component_samples": {name: len(points) for name, points in positions.items()},
              "render_is_sampled": True, "scale_verified": False,
              "historical_installation_verified": False, "physical_validation": False}
    (output / "render-report.json").write_text(json.dumps(result, indent=2) + "\n")
    for file in output.iterdir():
        file.chmod(0o600)
    print(json.dumps({"status": result["status"], "image_sha256": result["image_sha256"]}))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: render_flange_witness_context.py NATIVE_ASSEMBLY COMPOSED_USD NEW_PRIVATE_OUTPUT")
    run(*(Path(arg) for arg in sys.argv[1:]))
