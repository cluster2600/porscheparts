#!/usr/bin/env python3
"""Side views of the two cloth transfer cases at the end of their rollouts.

Each panel shows the sheet's vertices seen along z, the obstacle the model was given, and, dashed,
the sphere of the training scenes, which was NOT given to the model in these two cases.
Usage: plot_cloth_transfer.py EVAL_DIR OUT.png
"""
import glob
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ev, out = sys.argv[1], sys.argv[2]
ref = np.load(ev + "/hf/cloth_on_ball/dataset/10/10.npz")
ground = float(ref["ground_points"][0, 1])
centre, radius = ref["sphere_points"].mean(axis=0), 0.3
fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
panels = (("authors' scene: sheet over a sphere", glob.glob(ev + "/out/outcomes/npz/10/*.npz")[0], "sphere"),
          ("no sphere: ground plane only", glob.glob(ev + "/out-cases/outcomes/npz/cloth-plane/*.npz")[0], None),
          ("half-cylinder of radius 0.3 m on the ground", glob.glob(ev + "/out-cases/outcomes/npz/cloth-tunnel/*.npz")[0], "tunnel"))
t = np.linspace(0, 2 * np.pi, 200)
for ax, (title, path, given) in zip(axes, panels):
    end = np.load(path)["position"][-1]
    ax.axhline(ground, color="#555555", lw=2)
    if given == "sphere":
        ax.fill(centre[0] + radius * np.cos(t), centre[1] + radius * np.sin(t), color="#c9ccd1")
    else:
        ax.plot(centre[0] + radius * np.cos(t), centre[1] + radius * np.sin(t), "--", color="#b03a2e", lw=1.5)
    if given == "tunnel":
        half = np.linspace(0, np.pi, 100)
        ax.fill(radius * np.cos(half), ground + radius * np.sin(half), color="#c9ccd1")
    ax.scatter(end[:, 0], end[:, 1], s=1.5, color="#1f5fa8", alpha=0.6, linewidths=0)
    ax.set_title(title, fontsize=11)
    ax.set_aspect("equal")
    ax.set_xlim(-0.75, 0.75)
    ax.set_ylim(-0.08, 0.7)
    ax.set_xlabel("x, m")
axes[0].set_ylabel("height, m")
fig.suptitle("WorldParticle cloth checkpoint after 89 steps, seen along z. Blue: sheet vertices. Grey: the obstacle given to the model.\n"
             "Red dashes: where the training sphere was, not given to the model. The sheet drapes over it anyway.", fontsize=10.5)
fig.text(0.5, 0.005, "Rollouts of a released research model on CPU. Not a draping result for any mould.", ha="center", fontsize=9, color="#444444")
fig.tight_layout(rect=(0, 0.03, 1, 0.9))
fig.savefig(out, dpi=110)
