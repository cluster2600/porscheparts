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
    names = ["993-ENG-BRACKET-0001",
             "993-ENG-MOUNTING-0001", "993-ENG-MOUNTING-ISOLATOR-F0"]
    meshes = []
    for name in names:
        points, faces = read_stl(derived / (name + ".stl"))
        meshes.append(np.asarray(points)[faces])
    colors = ["#e4a056", "#599dcd", "#9a82c7"]
    fig = plt.figure(figsize=(15, 7), facecolor="#f4f6f8")

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

    panel(121, "Console — quatre racines et deux troncs",
          [(0, (0, 0, 0))], [(-70, 70), (-40, 40), (-5, 75)])
    panel(122, "Support — cage ramifiée et enveloppe à six lobes",
          [(1, (0, 0, 0)), (2, (0, 0, 70))], [(-65, 65), (-42, 42), (-5, 105)])
    fig.suptitle("Supports moteur bioniques 993 Turbo · PicoGK F0",
                 fontsize=20, color="#253345", y=.97)
    fig.text(.5, .035, "Morphologie bionique · charges non optimisées · interfaces non mesurées · fabrication interdite",
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
