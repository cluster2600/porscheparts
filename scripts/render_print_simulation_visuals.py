#!/usr/bin/env python3
"""Pictures and a build-up video of a part's LPBF print simulation.

Reads the published geometry report in `parts/<slug>/evidence/lpbf-f0/`,
checks that the analysed surface still has the hash the report recorded,
and places it on the machine plate in the orientation the simulation chose,
with the same kernel transform. It then draws:

- `build-plate.png`: the oriented part and a support proxy on the plate,
  inside the machine envelope;
- `layers.png`: six layer cross-sections, with the regions that need support;
- `build.mp4` and `build.gif`: the part growing layer by layer.

The support proxy is recomputed for the pictures at a coarser step than the
report (0.5 mm layers, 1 mm raster): it shows where supports go, the report's
numbers stay the reference. These are illustrations of a geometric
simulation, not an EOSPRINT build, a distortion result or a print release.

Run in the cadsim image, with PYTHONPATH pointing at shapely, rtree,
networkx, imageio and imageio-ffmpeg (see `make print-visuals`).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
KERNEL_PATH = ROOT / "twins/reference-917-engine/source/run_f50_lpbf_geometry_audit.py"
VISUAL_LAYER_MM = 0.5
VISUAL_RASTER_MM = 1.0
OVERHANG_DEG = 45.0
FRAME_COUNT = 120
PART_COLOR = "#7fa7c9"
SUPPORT_COLOR = "#e08a3c"
UNSUPPORTED_COLOR = "#c0392b"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_kernel():
    spec = importlib.util.spec_from_file_location("lpbf_f50_kernel", KERNEL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_inputs(slug: str):
    import trimesh

    folder = ROOT / f"parts/{slug}/evidence/lpbf-f0"
    report_path = next(folder.glob("*-lpbf-geometry-report.json"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    surface = next((ROOT / f"parts/{slug}/derived").glob("*.stl"))
    if sha256(surface) != report["analysis_surface"]["sha256"]:
        raise SystemExit(f"{surface.name} is not the surface the simulation analysed; rerun the simulation first.")
    mesh = trimesh.load_mesh(surface, process=True)
    return report, mesh


def place_on_plate(kernel, mesh, report):
    """The kernel's rigid transform, then the part centred on the plate."""
    oriented = kernel.orient(mesh, report["selected_candidate_orientation"])
    machine = report["machine_candidate"]
    width, depth = machine["build_width_mm"], machine["build_depth_mm"]
    centre = oriented.bounds.mean(axis=0)
    oriented.apply_translation([width / 2.0 - centre[0], depth / 2.0 - centre[1], 0.0])
    return oriented, (width, depth, machine["build_height_mm"])


def slices(kernel, mesh, heights):
    paths = mesh.section_multiplane(
        plane_origin=np.zeros(3), plane_normal=np.asarray([0.0, 0.0, 1.0]), heights=heights
    )
    return [kernel.path_to_polygon(path) for path in paths]


def support_proxy(kernel, mesh):
    """Unsupported regions and vertical support columns, at the visual step,
    with the same rules as the report: a region is unsupported when it lies
    beyond the 45 degree allowance of the layer below; a column runs down
    from it until it meets the part or the plate."""
    from shapely.geometry import GeometryCollection
    from shapely.ops import unary_union

    height = float(mesh.extents[2])
    count = int(math.ceil(height / VISUAL_LAYER_MM))
    z = (np.arange(count) + 0.5) * VISUAL_LAYER_MM
    layers = slices(kernel, mesh, z)
    allowance = VISUAL_LAYER_MM / math.tan(math.radians(OVERHANG_DEG))
    unsupported = [GeometryCollection()]
    for index in range(1, count):
        region = kernel.sanitize_polygonal(layers[index].difference(layers[index - 1].buffer(allowance)))
        parts = [p for p in kernel.geometry_components(region) if p.area >= 0.5]
        unsupported.append(unary_union(parts) if parts else GeometryCollection())
    bounds = np.asarray(mesh.bounds[:, :2], dtype=float)
    shape = kernel.rasterize(GeometryCollection(), bounds, VISUAL_RASTER_MM).shape
    columns = np.zeros(shape, dtype=bool)
    support = np.zeros((count,) + shape, dtype=bool)
    for index in range(count - 1, -1, -1):
        if index + 1 < count and not unsupported[index + 1].is_empty:
            columns |= kernel.rasterize(unsupported[index + 1], bounds, VISUAL_RASTER_MM)
        part = kernel.rasterize(layers[index], bounds, VISUAL_RASTER_MM)
        columns = columns & ~part
        support[index] = columns
    return z, layers, unsupported, support, bounds


def support_grid(support, bounds):
    """Support voxels as a pyvista grid with a layer index per cell."""
    import pyvista as pv

    count, ny, nx = support.shape
    grid = pv.ImageData(
        dimensions=(nx + 1, ny + 1, count + 1),
        spacing=(VISUAL_RASTER_MM, VISUAL_RASTER_MM, VISUAL_LAYER_MM),
        origin=(float(bounds[0, 0]), float(bounds[0, 1]), 0.0),
    )
    # rasterize's row 0 is the minimum y, as the grid's
    flags = support
    grid.cell_data["support"] = flags.reshape(-1).astype(np.uint8)
    grid.cell_data["layer"] = np.repeat(np.arange(count), nx * ny).astype(np.int32)
    return grid.threshold(0.5, scalars="support")


def plotter(window):
    import pyvista as pv

    pv.OFF_SCREEN = True
    p = pv.Plotter(off_screen=True, window_size=window, lighting="three lights")
    p.set_background("white")
    return p


def add_machine(p, size):
    import pyvista as pv

    width, depth, height = size
    plate = pv.Box(bounds=(0, width, 0, depth, -6.0, 0.0))
    p.add_mesh(plate, color="#8c8c8c", smooth_shading=False)
    envelope = pv.Box(bounds=(0, width, 0, depth, 0, height))
    p.add_mesh(envelope.extract_all_edges(), color="#b0b0b0", line_width=1)


def frame_camera(p, size):
    width, depth, height = size
    p.camera_position = [
        (width * 2.6, -depth * 1.7, height * 1.2),
        (width / 2.0, depth / 2.0, height * 0.22),
        (0.0, 0.0, 1.0),
    ]


def render_build_plate(out: Path, part_mesh, supports, size, report) -> None:
    p = plotter((1400, 1000))
    add_machine(p, size)
    p.add_mesh(part_mesh, color=PART_COLOR, smooth_shading=True)
    if supports.n_cells:
        p.add_mesh(supports, color=SUPPORT_COLOR, opacity=0.55)
    s = report["full_build_slicing"]
    p.add_text(
        f"{report['part_id']}\n"
        f"orientation {report['selected_candidate_orientation']}, {s['layer_count']:,} layers of "
        f"{s['layer_thickness_mm'] * 1000:.0f} um, {s['build_height_mm']:.1f} mm high\n"
        f"blue: part   orange: support proxy (visual, 0.5 mm / 1 mm)\n"
        "geometric simulation only - printing not authorized",
        position="upper_left", font_size=10, color="black",
    )
    frame_camera(p, size)
    p.screenshot(str(out))
    p.close()


def draw_slice(ax, layer, unsupported, support_mask, bounds, size, title):
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MplPath

    def patch(geometry, color, alpha=1.0, zorder=3):
        for poly in getattr(geometry, "geoms", [geometry]):
            if poly.is_empty or poly.geom_type != "Polygon":
                continue
            rings = [poly.exterior] + list(poly.interiors)
            verts, codes = [], []
            for ring in rings:
                coords = np.asarray(ring.coords)
                verts.extend(coords)
                codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(coords) - 2) + [MplPath.CLOSEPOLY])
            ax.add_patch(PathPatch(MplPath(verts, codes), facecolor=color, edgecolor="none", alpha=alpha, zorder=zorder))

    width, depth, _ = size
    ax.add_patch(__import__("matplotlib.patches", fromlist=["Rectangle"]).Rectangle(
        (0, 0), width, depth, facecolor="#f2f2f2", edgecolor="#999999"))
    if support_mask is not None and support_mask.any():
        extent = (bounds[0, 0], bounds[0, 0] + support_mask.shape[1] * VISUAL_RASTER_MM,
                  bounds[0, 1], bounds[0, 1] + support_mask.shape[0] * VISUAL_RASTER_MM)
        rgba = np.zeros(support_mask.shape + (4,))
        rgba[support_mask] = (0.88, 0.54, 0.24, 0.8)
        ax.imshow(rgba, extent=extent, origin="lower", interpolation="nearest", zorder=2)
    patch(layer, PART_COLOR)
    if unsupported is not None:
        patch(unsupported, UNSUPPORTED_COLOR, zorder=4)
    ax.set_xlim(0, width)
    ax.set_ylim(0, depth)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=9)
    ax.set_xticks([])
    ax.set_yticks([])


def render_layers(out: Path, z, layers, unsupported, support, bounds, size, report) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    picks = [int(len(z) * f) for f in (0.05, 0.2, 0.35, 0.5, 0.7, 0.9)]
    fig, axes = plt.subplots(2, 3, figsize=(12, 8.4), dpi=110)
    for ax, index in zip(axes.flat, picks):
        draw_slice(ax, layers[index], unsupported[index], support[index], bounds, size,
                   f"z = {z[index]:.1f} mm")
    fig.suptitle(
        f"{report['part_id']} - layer cross-sections on the {size[0]:.0f} x {size[1]:.0f} mm plate\n"
        "blue: part   red: region needing support   orange: support columns (visual proxy)",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def render_video(folder: Path, part_mesh, supports, z, layers, unsupported, support, bounds, size, report) -> None:
    import imageio.v2 as imageio
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    height = float(part_mesh.bounds[5])
    count = len(z)
    frames_mp4, frames_gif = [], []
    p = plotter((900, 760))
    for frame in range(FRAME_COUNT + 1):
        h = max(height * frame / FRAME_COUNT, VISUAL_LAYER_MM)
        index = min(int(h / VISUAL_LAYER_MM), count - 1)
        p.clear()
        add_machine(p, size)
        built = part_mesh.clip(normal="z", origin=(0, 0, h), invert=True)
        if built.n_cells:
            p.add_mesh(built, color=PART_COLOR, smooth_shading=True)
        cut = part_mesh.slice(normal="z", origin=(0, 0, h))
        if cut.n_cells:
            p.add_mesh(cut, color="#1b4f72", line_width=3)
        if supports.n_cells:
            grown = supports.threshold((0, index), scalars="layer")
            if grown.n_cells:
                p.add_mesh(grown, color=SUPPORT_COLOR, opacity=0.55)
        frame_camera(p, size)
        image3d = p.screenshot(return_img=True)

        fig = plt.figure(figsize=(14, 6.2), dpi=80)
        ax3 = fig.add_axes([0.0, 0.0, 0.56, 0.9])
        ax3.imshow(image3d)
        ax3.axis("off")
        ax2 = fig.add_axes([0.58, 0.08, 0.4, 0.78])
        draw_slice(ax2, layers[index], unsupported[index], support[index], bounds, size,
                   f"layer at z = {z[index]:.1f} mm")
        fig.suptitle(
            f"{report['part_id']} - LPBF build simulation, orientation "
            f"{report['selected_candidate_orientation']}, {100.0 * h / height:.0f} % "
            f"({int(h / report['full_build_slicing']['layer_thickness_mm']):,} of "
            f"{report['full_build_slicing']['layer_count']:,} layers)\n"
            "geometric simulation only: no laser path, distortion or recoater model - printing not authorized",
            fontsize=10,
        )
        fig.canvas.draw()
        rgb = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()
        plt.close(fig)
        frames_mp4.append(rgb)
        if frame % 2 == 0:
            frames_gif.append(rgb[::2, ::2])
    p.close()
    hold = [frames_mp4[-1]] * 36
    imageio.mimwrite(folder / "build.mp4", frames_mp4 + hold, fps=12, codec="libx264",
                     quality=7, macro_block_size=8)
    imageio.mimwrite(folder / "build.gif", frames_gif + [frames_gif[-1]] * 12, duration=0.12, loop=0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", required=True, help="part folder name under parts/")
    parser.add_argument("--no-video", action="store_true")
    args = parser.parse_args()

    import pyvista as pv

    kernel = load_kernel()
    report, mesh = load_inputs(args.part)
    oriented, size = place_on_plate(kernel, mesh, report)
    z, layers, unsupported, support, bounds = support_proxy(kernel, oriented)
    supports = support_grid(support, bounds)
    part_mesh = pv.wrap(oriented)

    folder = ROOT / f"parts/{args.part}/media/print-simulation"
    folder.mkdir(parents=True, exist_ok=True)
    render_build_plate(folder / "build-plate.png", part_mesh, supports, size, report)
    render_layers(folder / "layers.png", z, layers, unsupported, support, bounds, size, report)
    if not args.no_video:
        render_video(folder, part_mesh, supports, z, layers, unsupported, support, bounds, size, report)
    record = {
        "schema_version": "1.0.0",
        "part_id": report["part_id"],
        "source_report_surface_sha256": report["analysis_surface"]["sha256"],
        "orientation": report["selected_candidate_orientation"],
        "visual_support_proxy": {"layer_mm": VISUAL_LAYER_MM, "raster_mm": VISUAL_RASTER_MM,
                                 "overhang_deg": OVERHANG_DEG},
        "files": sorted(p.name for p in folder.iterdir() if p.name != "visuals.json"),
        "classification": "illustration of a geometric print simulation; not a build file, distortion result or print release",
    }
    (folder / "visuals.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
