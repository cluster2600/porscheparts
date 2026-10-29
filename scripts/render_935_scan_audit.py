#!/usr/bin/env python3
"""Orthographic audit views; this is not a manufacturing drawing."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
import trimesh

from audit_935_faithful_scan import EXPECTED_SHA256, sha256

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path)
parser.add_argument("audit_directory", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
if args.output.exists() or sha256(args.source) != EXPECTED_SHA256:
    raise SystemExit("Existing output or incorrect source")
mesh = trimesh.load_mesh(args.source, process=False, maintain_order=True)
points, _ = trimesh.sample.sample_surface(mesh, 120000, seed=935)
segments = np.load(args.audit_directory / "boundary-segments-source-units.npy", allow_pickle=False)
fig, axes = plt.subplots(1, 3, figsize=(15, 6), layout="constrained")
for ax, (i, j), title in zip(axes, [(0, 1), (0, 2), (1, 2)], ["XY", "XZ", "YZ"]):
    ax.scatter(points[:, i], points[:, j], s=.07, color="#728b9b", rasterized=True)
    ax.add_collection(LineCollection(segments[:, :, [i, j]], colors="#c74935", linewidths=.12))
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.set_xlabel("OBJ source units — scale unverified")
    ax.grid(alpha=.15)
fig.suptitle("935 Xtreme — observed scan surfaces and open edges\n"
             "Red: open edges (functional openings and scan gaps not yet classified). NOT PRINT READY.")
fig.savefig(args.output, dpi=170)
plt.close(fig)
