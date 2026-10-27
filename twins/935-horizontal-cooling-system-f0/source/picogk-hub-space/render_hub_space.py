"""Render the four observed 935 hub bands with the PicoGK visual annulus."""

import json
from pathlib import Path
import struct
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_surface_contacts import sha  # noqa: E402

DTYPE = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])


def centroids(path: Path) -> np.ndarray:
    with path.open("rb") as stream:
        header = stream.read(84)
    count = struct.unpack("<I", header[80:])[0]
    if count < 1 or count > 5_000_000 or path.stat().st_size != 84 + 50 * count:
        raise ValueError("Complete bounded binary STL required")
    vertices = np.memmap(path, mode="r", dtype=DTYPE, offset=84, shape=(count,))["vertices"]
    return np.asarray(vertices.mean(axis=1), dtype=np.float32)


def run(native: Path, assembly: Path, target: Path) -> None:
    native, assembly, target = native.resolve(), assembly.resolve(), target.resolve()
    if target.exists() or target.suffix != ".png" or not target.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("Use a new private work/ PNG")
    receipt = json.loads((native / "receipt.json").read_text())
    parent = json.loads((assembly / "receipt.json").read_text())
    parts = {item["id"]: item for item in parent["components"]}
    if receipt["status"] != "visual_hub_space_hypothesis_not_a_coupling" or receipt["scale_verified"]:
        raise ValueError("Only the uncalibrated visual hypothesis is allowed")
    if sha(native / "hub-space-hypothesis.stl") != receipt["mesh_sha256"]:
        raise ValueError("Native PicoGK mesh changed")
    data = {}
    for name in ("drive_observed", "rotor_candidate"):
        item = parts[name]
        path = assembly / item["file"]
        if sha(path) != item["sha256"] or item["sha256"] != receipt[name.split("_")[0] + "_sha256"]:
            raise ValueError(f"Pinned {name} changed")
        data[name] = centroids(path)
    inner, outer = receipt["inner_radius_mm_hypothesis"], receipt["outer_radius_mm_hypothesis"]
    bands = [(-20, -15), (-15, -10), (-10, -5), (-5, 0)]
    fig, axes = plt.subplots(1, 4, figsize=(16, 5.3), sharex=True, sharey=True)
    for ax, (low, high) in zip(axes, bands):
        ax.add_patch(Circle((0, 0), outer, color="#f3b95c", alpha=.22, label="visual hub space"))
        ax.add_patch(Circle((0, 0), inner, color="white"))
        for radius, color in ((inner, "#a35c00"), (outer, "#a35c00")):
            ax.add_patch(Circle((0, 0), radius, fill=False, color=color, linewidth=.8))
        for name, color in (("drive_observed", "#2b4a6f"), ("rotor_candidate", "#a02e39")):
            points = data[name]
            radius = np.hypot(points[:, 0], points[:, 1])
            selection = (points[:, 2] >= low) & (points[:, 2] < high) & (radius < 13)
            ax.scatter(points[selection, 0], points[selection, 1], s=.4, c=color, rasterized=True,
                       label=name.replace("_", " "))
        ax.set(xlim=(-13, 13), ylim=(-13, 13), title=f"z = {low} to {high} source units", xlabel="x (source units)")
        ax.set_aspect("equal")
        ax.grid(alpha=.15)
    axes[0].set_ylabel("y (source units)")
    handles, labels = axes[-1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(.5, .095), ncol=3, frameon=False)
    fig.suptitle("935 output / rotor bore: observed scan centroids and conditional PicoGK space")
    fig.text(.5, .025, "Uncalibrated scale; drive arc incomplete. Orange annulus has no torque or retention features.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .20, 1, .90))
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, dpi=180)
    plt.close(fig)
    print("png_sha256", sha(target))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: render_hub_space.py NATIVE_OUTPUT ASSEMBLY_OUTPUT NEW_PRIVATE_PNG")
    run(*(Path(arg) for arg in sys.argv[1:]))
