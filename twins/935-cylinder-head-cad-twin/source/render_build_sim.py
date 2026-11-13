#!/usr/bin/env python3
"""Pictures of the build screen: the build growing, and what it leaves behind.

    build-sim.gif          the print body growing lump by lump on its plate,
                           coloured by the rise of its time-averaged
                           temperature over the plate; supports in grey
    build-sim-result.png   left, von Mises stress at room temperature on the
                           plate; right, distortion after release with rigid
                           motion and uniform shrinkage removed, the shape
                           exaggerated

Voxel cells of a screen under declared hypotheses, drawn as they were solved.
Each frame carries a caption so that a picture taken out of the page still
says what it is.

Usage: render_build_sim.py RUN_DIR MEDIA_DIR [EXAGGERATION]
Run under xvfb-run with an interpreter that has pyvista and Pillow, with
software OpenGL (GALLIUM_DRIVER=llvmpipe LIBGL_ALWAYS_SOFTWARE=1) and, on WSL,
inside `bwrap --dev-bind / / --dev /dev --proc /proc`, where /dev/dxg does not
exist: the d3d12 driver took the whole VM down twice during this render.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_media import caption, sha256  # noqa: E402

CAPTION = "Build screen of a study print body, declared hypotheses. Not a process, not a part."
GIF_SIZE = (520, 560)


def grid_of(xyz, conn, keep):
    import pyvista as pv

    cells = conn[keep]
    return pv.UnstructuredGrid(np.column_stack([np.full(len(cells), 8), cells]).ravel(),
                               np.full(len(cells), 12, dtype=np.uint8), xyz.astype(float))


VIEW_ANGLE = 20.0


def camera(xyz, aspect, azimuth=-58.0, elevation=22.0, margin=1.12):
    """A view that holds the whole bounding sphere of `xyz` in a frame of width / height `aspect`."""

    lo, hi = xyz.min(axis=0), xyz.max(axis=0)
    centre = 0.5 * (lo + hi)
    half = np.radians(VIEW_ANGLE) / 2.0
    narrow = min(half, np.arctan(np.tan(half) * aspect))        # the vertical angle is the one VTK is given
    radius = margin * np.linalg.norm(hi - lo) / 2.0 / np.sin(narrow)
    a, e = np.radians(azimuth), np.radians(elevation)
    eye = centre + radius * np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    return [tuple(eye), tuple(centre), (0.0, 0.0, 1.0)]


def look(plotter, view) -> None:
    plotter.camera_position = view
    plotter.camera.view_angle = VIEW_ANGLE
    plotter.camera.clipping_range = (1.0, 1.0e5)


def main(run_dir, media, exaggeration="20") -> None:
    import pyvista as pv
    from PIL import Image

    run, media, factor = Path(run_dir), Path(media), float(exaggeration)
    m = np.load(run / "mesh.npz")
    case = json.loads((run / "case.json").read_text())
    thermal = json.loads((run / "thermal.json").read_text())
    temps = np.load(run / "thermal-end-of-lump.npy")
    fields = np.load(run / "mechanics-fields.npz")
    xyz, conn, kind, lump = m["xyz"], m["conn"], m["kind"], m["lump"]
    t_plate = case["plate"]["temperature_K"]
    top = float(np.ceil(thermal["largest_rise_over_plate_K"] / 10.0) * 10.0)
    pv.global_theme.background = "white"
    view = camera(xyz, GIF_SIZE[0] / GIF_SIZE[1])
    bar = dict(title="rise over the plate, K", n_labels=5, fmt="%.0f", color="black", vertical=False,
               position_x=0.2, position_y=0.87, height=0.11, width=0.6, title_font_size=14, label_font_size=12)

    frames = []
    lumps = int(lump.max()) + 1
    for j in range(lumps):
        plotter = pv.Plotter(off_screen=True, window_size=GIF_SIZE)
        plotter.add_mesh(grid_of(xyz, conn, kind == 1), color="#b8bcc2", show_edges=False)
        if ((kind == 3) & (lump <= j)).any():
            plotter.add_mesh(grid_of(xyz, conn, (kind == 3) & (lump <= j)), color="#8d9299", opacity=0.45)
        body = grid_of(xyz, conn, (kind == 2) & (lump <= j))
        body.point_data["rise"] = np.nan_to_num(temps[j] - t_plate, nan=0.0)
        plotter.add_mesh(body, scalars="rise", cmap="inferno", clim=[0.0, top], scalar_bar_args=bar, show_edges=False)
        look(plotter, view)
        row = thermal["lumps"][j]
        frame = caption(plotter.screenshot(return_img=True),
                        f"{CAPTION}  {row['end_time_s'] / 3600.0:4.1f} h, {(j + 1) * float(m['rows_per_lump']) * float(m['pitch']):.0f} mm")
        plotter.close()
        frames.append(frame.convert("RGB"))
    # One palette for every frame, taken from a strip of frames across the build: a palette per
    # frame makes the colour scale flicker.
    picked = frames[::max(1, lumps // 6)] + [frames[-1]]
    strip = Image.new("RGB", (GIF_SIZE[0] * len(picked), frames[0].height), "white")
    for i, frame in enumerate(picked):
        strip.paste(frame, (i * GIF_SIZE[0], 0))
    palette = strip.quantize(colors=160, method=Image.Quantize.MEDIANCUT)
    frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    frames += [frames[-1]] * 6
    frames[0].save(media / "build-sim.gif", save_all=True, append_images=frames[1:], duration=260, loop=0, optimize=False)

    part = kind == 2
    plotter = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1700, 900), border=False)
    plotter.subplot(0, 0)
    body = grid_of(xyz, conn, part)
    body.cell_data["vm"] = fields["room_temperature_on_plate_vm"][part]
    plotter.add_mesh(grid_of(xyz, conn, kind == 1), color="#b8bcc2")
    if (kind == 3).any():
        plotter.add_mesh(grid_of(xyz, conn, kind == 3), color="#8d9299", opacity=0.35)
    wide = dict(color="black", vertical=False, title_font_size=20, label_font_size=18, n_labels=5,
                position_x=0.15, position_y=0.86, width=0.7, height=0.12)
    plotter.add_mesh(body, scalars="vm", cmap="viridis",
                     scalar_bar_args=dict(title="von Mises stress, MPa (cell mean), at room temperature on the plate", fmt="%.0f", **wide))
    look(plotter, camera(xyz, 850 / 900))
    plotter.subplot(0, 1)
    warp = fields["released_warp"].astype(float)
    moved = grid_of(xyz + factor * warp, conn, part)
    moved.point_data["warp"] = np.linalg.norm(warp, axis=1)
    plotter.add_mesh(moved, scalars="warp", cmap="magma",
                     scalar_bar_args=dict(title=f"distortion after release, mm (shape exaggerated {factor:g} times)", fmt="%.2f", **wide))
    look(plotter, camera((xyz + factor * warp)[np.unique(conn[part])], 850 / 900))
    image = caption(plotter.screenshot(return_img=True), CAPTION)
    plotter.close()
    image.save(media / "build-sim-result.png", optimize=True)

    # Add both pictures to the record of public images, with the case they were computed on.
    record = json.loads((media / "provenance.json").read_text())
    record["inputs"]["build_sim_case_sha256"] = sha256(run / "case.json")
    record["inputs"]["build_sim_occupancy_sha256"] = json.loads((run / "prepare.json").read_text())["occupancy_sha256"]
    record["colours"]["build screen"] = ("inferno: rise of the time-averaged temperature over the plate; viridis: von Mises "
                                         "stress; magma: distortion after release; grey: plate and support columns")
    for name in ("build-sim.gif", "build-sim-result.png"):
        record["images"][name] = {"bytes": (media / name).stat().st_size, "sha256": sha256(media / name)}
    (media / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"frames": lumps, "colour_scale_top_K": top, "exaggeration": factor,
                      "bytes": {name: record["images"][name]["bytes"] for name in ("build-sim.gif", "build-sim-result.png")}}))


if __name__ == "__main__":
    main(*sys.argv[1:])
