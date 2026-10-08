"""The animated home-page banner, drawn from the same computation as the figures.

It is not a rendering of a car. The cell rotates so that one can see what the
model actually contains (thin shells, side rails, a roof, the windscreen
frame), and it is coloured by the von Mises stress of the torsion load case,
read from the same snapshot as `figures.py`, interpolated at the nodes. No
image enters this repository unless the data that produces it is already here.

The sections are ASSUMED and the mesh is not converged: the colour shows where
the load goes; it gives no stress value for a 964.

Rendering: pyvista/VTK, off screen, model drawn with a transparent background
at twice the final size and downscaled; text, colour scale and background
composed with PIL. Run where pyvista and PIL exist (the cadsim image does):

    python3 hero.py               # writes docs/media/diagrams/964-hero.gif
    python3 hero.py --frames 12   # quick draft
"""
import argparse
import pathlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parents[2]
OUT = ROOT / "docs" / "media" / "diagrams" / "964-hero.gif"

W, H, SS = 1280, 480, 2                    # final size, supersampling
MODEL_BOX = (430, 0, 1280, 480)            # where the model sits in the banner
BG_TOP, BG_BOTTOM = (22, 27, 36), (11, 14, 19)
FG, MUTED, ACCENT = (236, 232, 222), (150, 158, 170), (242, 177, 74)
# Low stress stays a readable slate blue on the dark ground; load runs through
# teal and amber to a pale hot white.
STOPS = ["#33415c", "#3e6a8a", "#4f9aa8", "#e9b44c", "#f07b3f", "#fff1d6"]


def colormap():
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list("hero", STOPS)


def load(name="fbtaprw"):
    """Vertices, faces and nodal von Mises stress from the stored snapshot."""
    d = np.load(HERE / "figures-mesh" / f"snap_{name}.npz")
    idx = {int(n): j for j, n in enumerate(d["nid"])}
    faces = np.vectorize(idx.get)(d["tri"])
    vm = np.zeros(len(d["nid"]))
    for n, v in zip(d["vmn"], d["vm"]):
        j = idx.get(int(n))
        if j is not None:
            vm[j] = v
    return d["xyz"], faces, vm, float(d["K"])


def font(size, bold=False):
    import matplotlib
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    path = pathlib.Path(matplotlib.get_data_path()) / "fonts" / "ttf" / name
    return ImageFont.truetype(str(path), size)


def background():
    """Vertical gradient, and the static text column."""
    t = np.linspace(0.0, 1.0, H)[:, None, None]
    grad = (np.array(BG_TOP) * (1 - t) + np.array(BG_BOTTOM) * t).astype(np.uint8)
    im = Image.fromarray(np.repeat(grad, W, axis=1), "RGB")
    return im


def text_layer(im, K, clim):
    d = ImageDraw.Draw(im)
    x = 56
    d.text((x, 78), "porscheparts", font=font(46, bold=True), fill=FG)
    d.rectangle((x, 142, x + 56, 145), fill=ACCENT)
    d.text((x, 164), "Reverse engineering", font=font(19), fill=FG)
    d.text((x, 190), "Porsche 911 · 964 and 993", font=font(19), fill=FG)
    d.text((x, 246), "Full 964 cell under torsion", font=font(15), fill=MUTED)
    d.text((x, 268), f"K = {K:,.0f} N·m/deg · linear S3 shells", font=font(15), fill=MUTED)
    # Colour scale: without one, a stress map is just a coloured picture.
    cmap = colormap()
    bar = (cmap(np.linspace(0, 1, 220))[:, :3] * 255).astype(np.uint8)
    im.paste(Image.fromarray(np.repeat(bar[None, :, :], 10, axis=0), "RGB"), (x, 316))
    d.text((x, 332), "0", font=font(12), fill=MUTED)
    d.text((x + 220, 332), f"{clim[1]:.0f}", font=font(12), fill=MUTED, anchor="ra")
    d.text((x + 110, 332), "von Mises, MPa", font=font(12), fill=MUTED, anchor="ma")
    d.text((x, 404), "Not a 964 and not a rendering: a snapshot of the calculation.",
           font=font(12), fill=MUTED)
    d.text((x, 422), "Sections ASSUMED; only the ratios are usable.", font=font(12), fill=MUTED)
    return im


def model_frames(xyz, faces, vm, clim, azimuths):
    import pyvista as pv
    pv.OFF_SCREEN = True
    mesh = pv.PolyData(xyz, np.c_[np.full(len(faces), 3), faces].ravel())
    mesh.point_data["vm"] = vm
    mesh = mesh.clean().compute_normals(split_vertices=True, feature_angle=35)
    edges = mesh.extract_feature_edges(35)
    bw, bh = MODEL_BOX[2] - MODEL_BOX[0], MODEL_BOX[3] - MODEL_BOX[1]
    p = pv.Plotter(off_screen=True, window_size=(bw * SS, bh * SS))
    p.add_mesh(mesh, scalars="vm", cmap=colormap(), clim=clim, smooth_shading=True,
               show_scalar_bar=False, ambient=0.22, diffuse=0.78, specular=0.3, specular_power=30)
    p.add_mesh(edges, color="#f3eee2", line_width=1.4 * SS, opacity=0.28)
    p.enable_anti_aliasing("ssaa")
    centre = np.asarray(mesh.center)
    radius = float(np.linalg.norm(np.ptp(xyz, axis=0))) * 1.38
    frames = []
    for az in azimuths:
        a = np.radians(az)
        eye = centre + radius * np.array([np.cos(a), np.sin(a), 0.38])
        p.camera.position = tuple(eye)
        p.camera.focal_point = tuple(centre)
        p.camera.up = (0.0, 0.0, 1.0)
        p.camera.view_angle = 30.0
        p.reset_camera_clipping_range()
        p.render()
        img = p.screenshot(transparent_background=True, return_img=True)
        im = Image.fromarray(img, "RGBA").resize((bw, bh), Image.LANCZOS)
        frames.append(im)
    p.close()
    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=60)
    a = ap.parse_args()

    xyz, faces, vm, K = load()
    # A high percentile keeps a clamping singularity from eating the scale.
    clim = (0.0, float(np.percentile(vm, 98)))
    base = text_layer(background(), K, clim)
    azimuths = np.linspace(0.0, 360.0, a.frames, endpoint=False) - 125.0
    images = []
    for model in model_frames(xyz, faces, vm, clim, azimuths):
        im = base.copy()
        im.paste(model, MODEL_BOX[:2], model)
        images.append(im)

    # One palette for all frames, built from a sample of them, with dithering:
    # a 256-colour GIF bands badly on smooth gradients otherwise.
    sample = Image.new("RGB", (W, H * 4))
    for k, i in enumerate(np.linspace(0, len(images) - 1, 4).astype(int)):
        sample.paste(images[i], (0, H * k))
    palette = sample.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    frames = [im.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG) for im in images]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=70, loop=0,
                   optimize=False, disposal=1)
    print(f"{OUT}  {OUT.stat().st_size / 1e6:.2f} MB  {a.frames} frames")


if __name__ == "__main__":
    main()
