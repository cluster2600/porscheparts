#!/usr/bin/env python3
"""Public images of the twin for its README: stills and one turntable GIF.

Every picture is a rendering of the study twin, never of a part:

    hero.gif            the v2 CAD body turning, grey where the scan supports it
                        within 0.2 mm, orange where it is inferred closure
    views.png           the same body from four sides
    scan-and-twin.png   the acquired scan (open, studs still on) beside the body
    features.png        the body made translucent, with the fitted valve, plug
                        and stud axes and the hypothesis valves and plugs

The geometry itself (meshes, STEP, USD) stays private; these are pixels. Each
frame carries a caption so that a picture taken out of the page still says
what it is. ``media/provenance.json`` records the inputs by hash and the
licence state of the scan.

Usage: render_media.py PRIVATE_DIR PARAMS_DIR MEDIA_DIR
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

CAPTION = "Study twin of a scanned 935-type head. Not measured, not a part."
BACKGROUND = "white"
FRAMES = 30
GIF_SIZE = (480, 360)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def body_from_stage(stage_path: Path):
    """Points, triangles and the inferred flag of each face, from the CAD-body stage."""

    from pxr import Usd, UsdGeom

    stage = Usd.Stage.Open(str(stage_path))
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath("/Head935/BareHead"))
    points = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)
    faces = np.asarray(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int64).reshape(-1, 3)
    inferred = np.asarray(UsdGeom.PrimvarsAPI(mesh).GetPrimvar("displayColor").GetIndices(), dtype=np.int8)
    return points, faces, inferred


def polydata(points, faces):
    import pyvista as pv

    return pv.PolyData(points, np.column_stack([np.full(len(faces), 3), faces]).ravel())


def caption(image, text=CAPTION):
    """Burn a one-line caption into the bottom of a frame."""

    from PIL import Image, ImageDraw, ImageFont

    img = Image.fromarray(image) if not isinstance(image, Image.Image) else image
    draw = ImageDraw.Draw(img)
    size = max(12, img.width // 46)
    while True:                               # shrink until the caption fits the frame
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", size)
        except OSError:
            font = ImageFont.load_default()
            break
        if draw.textbbox((0, 0), text, font=font)[2] <= img.width - 16 or size <= 9:
            break
        size -= 1
    box = draw.textbbox((0, 0), text, font=font)
    draw.rectangle([0, img.height - (box[3] - box[1]) - 14, img.width, img.height], fill=(255, 255, 255))
    draw.text(((img.width - (box[2] - box[0])) // 2, img.height - (box[3] - box[1]) - 10), text, fill=(60, 60, 60), font=font)
    return img


def hex_colour(rgb) -> str:
    return "#" + "".join(f"{int(round(255 * x)):02x}" for x in rgb)


def add_body(plotter, body, colours, opacity=1.0):
    plotter.add_mesh(body, scalars="inferred", cmap=[hex_colour(colours["observed"]), hex_colour(colours["inferred_closure"])], clim=[0, 1],
                     show_scalar_bar=False, smooth_shading=False, opacity=opacity, specular=0.1)


def orbit(centre, radius, azimuth_deg, elevation_deg):
    a, e = np.radians(azimuth_deg), np.radians(elevation_deg)
    eye = centre + radius * np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    return [tuple(eye), tuple(centre), (0.0, 0.0, 1.0)]


def axis_line(origin, direction, t0, t1):
    import pyvista as pv

    o, d = np.asarray(origin, dtype=float), np.asarray(direction, dtype=float)
    return pv.Line(o + t0 * d, o + t1 * d)


def main(private, params, media) -> None:
    import pyvista as pv
    from PIL import Image

    import assembly_thermal

    private, params, media = Path(private), Path(params), Path(media)
    media.mkdir(parents=True, exist_ok=True)
    hyp = json.loads((params.parent / "hypotheses.json").read_text())
    colours = {k: tuple(v) for k, v in hyp["display_colours"].items()}
    stage_path = private / "935-head-twin-cad.usdc"
    points, faces, inferred = body_from_stage(stage_path)
    body = polydata(points, faces)
    body.cell_data["inferred"] = inferred
    centre = 0.5 * (points.min(axis=0) + points.max(axis=0))
    radius = 2.3 * float(np.linalg.norm(points.max(axis=0) - points.min(axis=0)))
    pv.global_theme.background = BACKGROUND

    # hero.gif: one turn about the bore axis
    plotter = pv.Plotter(off_screen=True, window_size=GIF_SIZE)
    add_body(plotter, body, colours)
    frames = []
    for i in range(FRAMES):
        plotter.camera_position = orbit(centre, radius, 360.0 * i / FRAMES, 28.0)
        plotter.camera.view_angle = 22.0
        plotter.render()                      # a moved camera is not drawn until asked
        frames.append(caption(np.array(plotter.screenshot(return_img=True))))
    plotter.close()
    if all(np.array_equal(np.asarray(frames[0]), np.asarray(f)) for f in frames[1:]):
        raise SystemExit("the turntable frames are identical: the camera did not move")
    # One palette for every frame, so that the colours do not flicker.
    palette = frames[0].quantize(colors=64, method=Image.Quantize.MEDIANCUT)
    frames = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    frames[0].save(media / "hero.gif", save_all=True, append_images=frames[1:], duration=110, loop=0, optimize=False)

    # views.png: four sides
    plotter = pv.Plotter(off_screen=True, shape=(2, 2), window_size=(1500, 1200), border=False)
    views = [("cam side", 40.0, 35.0), ("chamber and deck", 40.0, -55.0), ("port, y- flange", -90.0, 12.0), ("fins, x+ side", 0.0, 12.0)]
    for index, (title, azimuth, elevation) in enumerate(views):
        plotter.subplot(index // 2, index % 2)
        add_body(plotter, body, colours)
        plotter.camera_position = orbit(centre, radius, azimuth, elevation)
        plotter.camera.view_angle = 20.0
        plotter.add_text(title, font_size=11, color="black")
    image = caption(plotter.screenshot(return_img=True), CAPTION + " Grey: within 0.2 mm of the scan. Orange: inferred closure.")
    plotter.close()
    image.save(media / "views.png", optimize=True)

    # scan-and-twin.png: what was acquired, beside what was built from it
    raw = np.load(private / "scan-raw64.npz")
    frame = json.loads((params / "frame.json").read_text())
    scan_points = (raw["v"] - np.array(frame["origin_scan"])) @ np.array(frame["rotation_scan_to_twin_rows"]).T
    scan = polydata(scan_points, raw["f"])
    plotter = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1700, 760), border=False)
    plotter.subplot(0, 0)
    plotter.add_mesh(scan, color=(0.60, 0.66, 0.74), smooth_shading=False, specular=0.1)
    plotter.camera_position = orbit(centre, radius * 1.15, 40.0, 30.0)
    plotter.camera.view_angle = 20.0
    plotter.add_text("acquired scan: open surface, studs still on", font_size=11, color="black")
    plotter.subplot(0, 1)
    add_body(plotter, body, colours)
    plotter.camera_position = orbit(centre, radius * 1.15, 40.0, 30.0)
    plotter.camera.view_angle = 20.0
    plotter.add_text("v2 CAD body: one closed solid, studs removed", font_size=11, color="black")
    image = caption(plotter.screenshot(return_img=True), CAPTION + " Orange: surface the scanner never saw.")
    plotter.close()
    image.save(media / "scan-and-twin.png", optimize=True)

    # features.png: fitted axes and the hypothesis solids of the assembly screen
    fits = json.loads((params / "feature-fits.json").read_text())
    case = json.loads((params / "assembly-case.json").read_text())
    comps = assembly_thermal.build_components(case, fits)
    plotter = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1700, 760), border=False)
    for column, (azimuth, elevation) in enumerate(((100.0, 20.0), (40.0, -50.0))):
        plotter.subplot(0, column)
        plotter.add_mesh(body, color=colours["observed"], opacity=0.18, smooth_shading=False)
        for name, datum in fits["group_datums"].items():
            colour = "crimson" if name.startswith("valve") else ("royalblue" if name.startswith("plug") else "seagreen")
            span = (-70.0, 60.0) if name == "valve_y_minus" else ((-25.0, 100.0) if name == "valve_y_plus" else (-25.0, 55.0))
            plotter.add_mesh(axis_line(datum["axis_point"], datum["axis_direction"], *span), color=colour, line_width=4)
        # The hypothesis solids, as point clouds of their analytic shapes.
        rng = np.random.default_rng(1)
        cloud = rng.uniform(points.min(axis=0), points.max(axis=0), size=(1_500_000, 3))
        plotter.add_points(cloud[assembly_thermal.added_solid(cloud, comps)], color=colours["analytic_hypothesis"],
                           point_size=3.0, render_points_as_spheres=False)
        plotter.camera_position = orbit(centre, radius * 1.1, azimuth, elevation)
        plotter.camera.view_angle = 20.0
        plotter.add_text(("from the port side", "from the chamber")[column], font_size=11, color="black")
    image = caption(plotter.screenshot(return_img=True),
                    "Fitted axes: valves red, plugs blue, stud passages green. Magenta: hypothetical valves and plugs. Not a part.")
    plotter.close()
    image.save(media / "features.png", optimize=True)

    names = ("hero.gif", "views.png", "scan-and-twin.png", "features.png")
    # Pictures another script added to the record (render_build_sim.py) stay in it.
    before = json.loads((media / "provenance.json").read_text()) if (media / "provenance.json").exists() else {}
    others = {name: entry for name, entry in before.get("images", {}).items() if name not in names and (media / name).exists()}
    other_inputs = {key: value for key, value in before.get("inputs", {}).items() if key.startswith("build_sim_")}
    (media / "provenance.json").write_text(json.dumps({
        "schema": "935-cad-twin-media/1",
        "kind": "renderings of a study twin; pixels only, no geometry file is published",
        "scan_sha256": frame["scan_sha256"],
        "scan_licence": "the owner states the scan is under an open, reusable licence; no standard identifier is "
                        "archived yet (issue #462) and the vendor page carried no licence text on 2026-11-06",
        "inputs": {"cad_body_stage_sha256": sha256(stage_path), "feature_fits_sha256": sha256(params / "feature-fits.json"),
                   "assembly_case_sha256": sha256(params / "assembly-case.json"), **other_inputs},
        "colours": {"grey": "twin surface within 0.2 mm of the acquired scan", "orange": "inferred closure (H01, H02, H04)",
                    "magenta": "hypothesis solids of the assembly thermal screen (H10)"},
        "publication_terms": "published by the owner's decision of 2026-11-11; every image carries its own caption",
        "images": {**{name: {"bytes": (media / name).stat().st_size, "sha256": sha256(media / name)} for name in names},
                   **others},
    }, indent=2) + "\n")
    print({name: (media / name).stat().st_size for name in names})


if __name__ == "__main__":
    main(*sys.argv[1:4])
