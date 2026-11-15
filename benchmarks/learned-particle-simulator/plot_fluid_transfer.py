#!/usr/bin/env python3
"""Side views of the fluid cases: the authors' scene, and a tank of another size.

Each panel shows the particles seen along z and the outline of the tank the model was given. Dashed:
the outline of the training tank, which was NOT given to the model in the two right-hand panels.
Usage: plot_fluid_transfer.py EVAL_DIR OUT.png
"""
import glob
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ev, out = sys.argv[1], sys.argv[2]
panels = (("authors' validation scene, step 300", ev + "/gpu/out-fluid/outcomes/npz/66/*.npz", ev + "/hf/fancy_fluid/dataset/66/66.npz", 300),
          ("still slab, tank of the training size, step 300", ev + "/gpu/out-cases/outcomes/npz/fluid-still-training-tank/*.npz",
           ev + "/gpu/cases/fluid-still-training-tank/fluid-still-training-tank.npz", 300),
          ("still slab, tank 2.4 x 1.6 m, step 300", ev + "/gpu/out-cases/outcomes/npz/fluid-still/*.npz", ev + "/gpu/cases/fluid-still/fluid-still.npz", 300),
          ("dam break, tank 2.4 x 1.6 m, step 100", ev + "/gpu/out-cases/outcomes/npz/fluid-dam/*.npz", ev + "/gpu/cases/fluid-dam/fluid-dam.npz", 100))
fig, axes = plt.subplots(1, 4, figsize=(18, 4.4), sharey=True)
for ax, (title, roll, case, step) in zip(axes, panels):
    p = np.load(glob.glob(roll)[0])["position"][step]
    box = np.load(case)["box"]
    lo, hi = box.min(axis=0), box.max(axis=0)
    ax.plot([-2, -2, 2, 2], [2, 0, 0, 2], "--", color="#b03a2e", lw=1.2)
    ax.plot([lo[0], lo[0], hi[0], hi[0]], [hi[1], lo[1], lo[1], hi[1]], color="#333333", lw=2.2)
    inside = ((p >= lo) & (p <= hi)).all(axis=1)
    ax.scatter(p[inside, 0], p[inside, 1], s=1.5, color="#1f5fa8", alpha=0.5, linewidths=0)
    ax.scatter(p[~inside, 0], p[~inside, 1], s=2.5, color="#d35400", alpha=0.8, linewidths=0)
    ax.set_title(f"{title}\n{int((~inside).sum()):,} of {len(p):,} particles outside", fontsize=10)
    ax.set_aspect("equal")
    ax.set_xlim(-2.6, 2.6)
    ax.set_ylim(-0.9, 2.1)
    ax.set_xlabel("x, m")
axes[0].set_ylabel("height, m")
fig.suptitle("WorldParticle fluid checkpoint, seen along z. Blue: particles inside the tank given to the model (black). Orange: outside it.\n"
             "Red dashes: the tank of the training scenes, 4 x 2 m, which the model was not given in the two right-hand panels.", fontsize=10.5)
fig.text(0.5, 0.005, "Rollouts of a released research model. Not a flow result for any part.", ha="center", fontsize=9, color="#444444")
fig.tight_layout(rect=(0, 0.03, 1, 0.88))
fig.savefig(out, dpi=110)
