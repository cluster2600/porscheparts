"""Render private inspection views of the audited exploratory fluid mesh."""

import hashlib
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from audit_root0p7_tet_quality import EXPECTED, mean_ratio


def main(volume_path, output_path):
    root = Path.cwd() / "work"
    output = Path(output_path).resolve()
    if not output.is_relative_to(root.resolve()) or output.exists():
        raise ValueError("A new private work/ output is required")
    if hashlib.sha256(Path(volume_path).read_bytes()).hexdigest() != EXPECTED:
        raise ValueError("Unexpected audited volume")
    with np.load(volume_path) as data:
        vertices, cells = data["vertices"], data["tetrahedra"]
        boundary, markers = data["boundary"], data["markers"]
    ratios = np.concatenate([mean_ratio(vertices[cells[i:i + 100000]]) for i in range(0, len(cells), 100000)])
    weak = vertices[cells[ratios < .01]].mean(axis=1)
    if len(weak) != 3461:
        raise ValueError("Unexpected weak-cell count")
    rotor = vertices[np.unique(boundary[markers == 4])]

    figure, axes = plt.subplots(1, 2, figsize=(14, 6), dpi=150)
    for axis, (x, y), title in zip(axes, ((0, 1), (0, 2)), ("Top view: XY", "Side view: XZ")):
        axis.scatter(rotor[::5, x], rotor[::5, y], s=.08, c="#9ca3af", rasterized=True, label="rotor wall vertices (sampled)")
        axis.scatter(weak[:, x], weak[:, y], s=2, c="#dc2626", alpha=.55, rasterized=True, label="weak tetra centroids")
        axis.set_aspect("equal")
        axis.set_xlabel("X (assumed m)")
        axis.set_ylabel(("Y" if y == 1 else "Z") + " (assumed m)")
        axis.set_title(title)
        axis.legend(loc="upper right", markerscale=3)
    figure.suptitle("935 pilot fluid mesh: 3,461 cells with mean ratio < 0.01\nScale is unverified; exploratory duct is not the 935 shroud")
    figure.tight_layout()
    figure.savefig(output)
    plt.close(figure)
    print(hashlib.sha256(output.read_bytes()).hexdigest(), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: render_root0p7_weak_cells.py AUDITED_VOLUME_NPZ NEW_PRIVATE_PNG")
    main(sys.argv[1], sys.argv[2])
