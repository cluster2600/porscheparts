"""The animated home-page banner, drawn from the same computation as the figures.

It is not a rendering and it is not a car. The cell rotates so that one can see
what the model actually contains (thin shells, a side rail, a tunnel, a roof),
and it is colored by the von Mises stress of the torsion load case, read from
the same snapshot as `figures.py`. No image enters this repository unless the
data that produces it is already here.

The sections are ASSUMED and the mesh is not converged: the color shows where
the load goes; it gives no stress value for a 964.

    pymesh hero.py               # writes docs/media/diagrams/964-hero.gif
    pymesh hero.py --frames 24   # quick draft
"""
import argparse, io, pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parents[2]
OUT = ROOT / "docs" / "media" / "diagrams" / "964-hero.gif"

# Same explicit light background as the other figures: GitHub renders the file
# as-is under both themes, and a transparent background would make text unreadable.
BG, FG, MUTED = "#ffffff", "#1a1a1a", "#666666"

LARGEUR, HAUTEUR, DPI, SS = 12.8, 5.0, 100, 2


def charge(nom="fbtaprw"):
    """Vertices, faces and nodal von Mises stress from the stored snapshot."""
    d = np.load(HERE / "figures-mesh" / f"snap_{nom}.npz")
    xyz, tri = d["xyz"], d["tri"]
    idx = {int(n): j for j, n in enumerate(d["nid"])}
    faces = np.vectorize(idx.get)(tri)
    vm = np.zeros(len(d["nid"]), dtype="float32")
    for n, v in zip(d["vmn"], d["vm"]):
        j = idx.get(int(n))
        if j is not None:
            vm[j] = v
    return xyz, faces, vm[faces].mean(axis=1), float(d["K"])


def frame(xyz, faces, par_tri, K, azim, clim):
    """One frame: text on the left, the rotating cell on the right."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(LARGEUR, HAUTEUR), facecolor=BG, dpi=DPI)
    # Axes placed by hand: tight_layout and subplots_adjust fight with a 3D
    # view, and the banner must keep its text column on the left.
    ax = fig.add_axes((0.42, 0.02, 0.57, 0.96), projection="3d")
    pc = Poly3DCollection(xyz[faces], cmap="magma_r", linewidth=0)
    pc.set_array(par_tri)
    pc.set_clim(*clim)
    ax.add_collection3d(pc)

    lo, hi = xyz.min(0), xyz.max(0)
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(lo[2], hi[2])
    # True proportions are kept; the frame is filled, otherwise the body shell
    # gets lost in the middle of a cube shared by the three axes.
    ax.set_box_aspect(hi - lo, zoom=1.05)
    ax.view_init(elev=16, azim=azim)
    ax.set_axis_off()
    ax.set_facecolor(BG)

    fig.text(0.045, 0.80, "porscheparts", color=FG, fontsize=26,
             fontweight="bold", ha="left", va="top")
    fig.text(0.045, 0.645, "Reverse engineering\nPorsche 911 964 and 993",
             color=FG, fontsize=13, ha="left", va="top", linespacing=1.5)
    fig.text(0.045, 0.46, f"Full 964 cell, von Mises\n"
             f"under torsional torque\nK = {K:.0f} N.m/deg, linear S3 shells",
             color=MUTED, fontsize=10.5, ha="left", va="top", linespacing=1.6)
    # Horizontal color bar in the text column: without a scale, a stress map
    # is just a colored picture.
    cax = fig.add_axes((0.045, 0.235, 0.17, 0.026))
    cb = fig.colorbar(pc, cax=cax, orientation="horizontal")
    cb.set_label("von Mises (MPa)", color=MUTED, fontsize=8.5, labelpad=3)
    cb.ax.tick_params(colors=MUTED, labelsize=7.5, length=2)
    cb.outline.set_visible(False)

    fig.text(0.045, 0.055, "Not a 964, not a rendering: a snapshot of the computation.\n"
             "Sections ASSUMED; only the ratios are usable.",
             color=MUTED, fontsize=8.8, ha="left", va="bottom", linespacing=1.5)

    # Render at double size then downscale: the 12,972-triangle shells show
    # heavy moire at the final size, and supersampling smooths it out.
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=BG, dpi=DPI * SS)
    plt.close(fig)
    buf.seek(0)
    im = Image.open(buf).convert("RGB")
    return im.resize((int(LARGEUR * DPI), int(HAUTEUR * DPI)), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=48)
    ap.add_argument("--couleurs", type=int, default=96)
    a = ap.parse_args()

    xyz, faces, par_tri, K = charge()
    # A high percentile keeps a clamping singularity from eating the scale.
    clim = (0.0, float(np.percentile(par_tri, 98)))
    azims = np.linspace(-180, 180, a.frames, endpoint=False)
    images = [frame(xyz, faces, par_tri, K, az, clim) for az in azims]

    pal = images[0].quantize(colors=a.couleurs, method=Image.MEDIANCUT)
    images = [im.quantize(palette=pal, dither=Image.NONE) for im in images]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(OUT, save_all=True, append_images=images[1:],
                   duration=90, loop=0, optimize=True)
    print(f"{OUT}  {OUT.stat().st_size / 1e6:.2f} MB  {a.frames} frames")


if __name__ == "__main__":
    main()
