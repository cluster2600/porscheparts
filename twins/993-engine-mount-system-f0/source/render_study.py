"""Render the retained STL triangles; colors and exploded positions are illustrative."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

from build_study import FAMILY, check, read_stl, sha256


def main():
    derived, media = FAMILY / "derived", FAMILY / "media"
    check(derived)
    names = ["carrier-reference", "993-ENG-BRACKET-0001",
             "993-ENG-MOUNTING-0001", "993-ENG-MOUNTING-ISOLATOR-F0"]
    meshes = []
    for name in names:
        points, faces = read_stl(derived / (name + ".stl"))
        meshes.append(np.asarray(points)[faces])
    colors = ["#aab7c4", "#e4a056", "#599dcd", "#9a82c7"]
    fig = plt.figure(figsize=(15, 8), facecolor="#f4f6f8")

    def panel(position, title, instances, limits):
        ax = fig.add_subplot(position, projection="3d", facecolor="#f4f6f8")
        for index, pose in instances:
            triangles = meshes[index] + np.asarray(pose)
            ax.add_collection3d(Poly3DCollection(triangles, facecolors=colors[index],
                                               linewidths=0, shade=True, zsort="average"))
        for setter, bounds in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), limits):
            setter(*bounds)
        ax.set_box_aspect([b - a for a, b in limits])
        ax.set_proj_type("ortho")
        ax.view_init(elev=24, azim=-65)
        ax.set_axis_off()
        ax.set_title(title, fontsize=13, color="#253345", pad=0)

    panel(211, "Ensemble éclaté — positions non mesurées",
          [(0, (0, 0, 0)), (1, (0, 0, 100)), (2, (-275, 0, 80)),
           (2, (275, 0, 80)), (3, (-275, 0, 145)), (3, (275, 0, 145))],
          [(-345, 345), (-70, 70), (-30, 185)])
    panel(223, "Console centrale — plaque et nervures",
          [(1, (0, 0, 0))], [(-75, 75), (-40, 40), (-5, 70)])
    panel(224, "Boîtier et enveloppe souple séparée",
          [(2, (0, 0, 0)), (3, (0, 0, 68))], [(-65, 65), (-35, 35), (-5, 100)])
    fig.suptitle("Supports moteur 993 Turbo · étude paramétrique PicoGK F0",
                 fontsize=20, color="#253345", y=.97)
    fig.text(.5, .035, "Géométrie hypothétique · perçages non mesurés · aucune autorisation de fabrication",
             ha="center", fontsize=12, color="#674b3a")
    fig.subplots_adjust(top=.90, bottom=.08, hspace=.02, wspace=.02)
    media.mkdir(exist_ok=True)
    output = media / "engine-mount-study.png"
    fig.savefig(output, dpi=140, facecolor=fig.get_facecolor())
    plt.close(fig)
    metadata = {"status": "illustration_only", "triangle_subsampling": False,
                "inputs": {str(p.relative_to(FAMILY)): sha256(p) for p in
                           [derived / (n + ".stl") for n in names] + [Path(__file__)]},
                "image_sha256": sha256(output)}
    (media / "engine-mount-study.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
