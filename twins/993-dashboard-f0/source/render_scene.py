#!/usr/bin/env python3
"""Render an assumed 993 dashboard F0 scene from separate PicoGK STL layers."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pyvista as pv
from PIL import Image, ImageColor, ImageDraw, ImageFont, __version__ as pillow_version

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "work"
SCENE_SPEC = Path(__file__).with_name("scene.json")
CSHARP_SOURCE = Path(__file__).with_name("Program.cs")
RENDER_SOURCE = Path(__file__).resolve()
VIEW_SIZE = (1700, 900)
PANEL_WIDTH = 420
HEADER_HEIGHT = 110
FOOTER_HEIGHT = 120
BACKGROUND = "#f5f6f8"
LABELS = {
    "DASHBOARD_TRIM": "Dashboard trim",
    "INSTRUMENT_HOOD": "Instrument hood",
    "INSTRUMENT_CLUSTER": "Instrument cluster",
    "INSTRUMENT_GAUGE_MARKS": "Gauge rings and marks",
    "CENTER_AIR_VENTS": "Centre air vents",
    "SIDE_AIR_VENTS": "Side air vents",
    "DEFROST_OUTLETS_AND_DUCTS": "Defrost outlet marks",
    "GLOVEBOX": "Glovebox outline",
    "CENTER_CONSOLE": "Centre console",
    "HVAC_RADIO_CONTROLS": "HVAC and radio controls",
    "SWITCHES_AND_BLANKS": "Switches and blanks",
    "KNEE_STRIP_RESERVED": "Knee strip reserved zone",
}
VIEWS = (
    ("front", (0.0, -1.0, 0.0), "Front / occupant side"),
    ("three-quarter", (0.72, -1.55, 0.72), "Three-quarter / occupant side"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def binary_stl_qa(path: Path) -> tuple[int, int]:
    """Count source triangles and zero-area faces without changing the mesh."""
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"STL is too short: {path}")
    count = int.from_bytes(data[80:84], "little")
    if len(data) != 84 + 50 * count:
        raise ValueError(f"expected a PicoGK binary STL: {path}")
    triangle_type = np.dtype([
        ("normal", "<f4", (3,)),
        ("vertices", "<f4", (3, 3)),
        ("attribute", "<u2"),
    ])
    vertices = np.frombuffer(data, dtype=triangle_type, count=count, offset=84)["vertices"]
    cross = np.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0])
    degenerate = int(np.count_nonzero(np.linalg.norm(cross, axis=1) <= 1e-12))
    return count, degenerate


def inside_work(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if WORK.resolve() not in resolved.parents:
        raise ValueError(f"path must be inside the repository work/ directory: {resolved}")
    return resolved


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def load_layers(report_path: Path, report: dict) -> list[dict]:
    source_layers = report.get("layers")
    if not isinstance(source_layers, list) or not source_layers:
        raise ValueError("scene report must contain a non-empty layers list")
    seen: set[str] = set()
    layers: list[dict] = []
    for index, item in enumerate(source_layers):
        if not isinstance(item, dict):
            raise ValueError(f"layer {index}: expected an object")
        family = item.get("family_id")
        file_name = item.get("file")
        expected_hash = item.get("sha256")
        colour = item.get("colour")
        if not all(isinstance(value, str) and value for value in
                   (family, file_name, expected_hash, colour)):
            raise ValueError(f"layer {index}: family_id, file, sha256 and colour are required")
        if family in seen:
            raise ValueError(f"duplicate layer family_id: {family}")
        seen.add(family)
        if Path(file_name).name != file_name or not file_name.lower().endswith(".stl"):
            raise ValueError(f"layer {family}: file must be a plain STL basename")
        stl = (report_path.parent / file_name).resolve()
        if report_path.parent not in stl.parents or not stl.is_file():
            raise ValueError(f"layer {family}: STL missing or outside report directory")
        actual_hash = sha256(stl)
        if actual_hash.lower() != expected_hash.lower():
            raise ValueError(f"layer {family}: STL hash does not match scene report")
        try:
            ImageColor.getrgb(colour)
            pv.Color(colour)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"layer {family}: invalid colour {colour!r}") from exc
        raw_count, degenerate_count = binary_stl_qa(stl)
        if raw_count != item.get("triangles"):
            raise ValueError(f"layer {family}: raw STL triangle count differs from receipt")
        mesh = pv.read(str(stl))
        if not isinstance(mesh, pv.PolyData) or mesh.n_cells == 0:
            raise ValueError(f"layer {family}: STL must contain a non-empty triangle mesh")
        if not all(math.isfinite(value) for value in mesh.bounds):
            raise ValueError(f"layer {family}: STL has non-finite bounds")
        layers.append({
            "family_id": family,
            "label": LABELS.get(family, family.replace("_", " ").title()),
            "file": file_name,
            "sha256": actual_hash,
            "colour": colour,
            "triangles_reported": item.get("triangles"),
            "triangles_loaded": mesh.n_cells,
            "zero_area_faces_raw": degenerate_count,
            "faces_omitted_by_vtk": raw_count - mesh.n_cells,
            "mesh": mesh,
        })
    return layers


def render_mesh(layers: list[dict], vector: tuple[float, float, float]) -> Image.Image:
    plotter = pv.Plotter(off_screen=True, window_size=VIEW_SIZE, lighting="three lights")
    try:
        plotter.set_background(BACKGROUND)
        for layer in layers:
            plotter.add_mesh(layer["mesh"], color=layer["colour"],
                             smooth_shading=False, specular=0.0,
                             ambient=0.40, diffuse=0.60, show_edges=False)
        plotter.view_vector(vector, viewup=(0, 0, 1))
        plotter.enable_parallel_projection()
        plotter.reset_camera()
        plotter.camera.zoom(1.48)
        frame = plotter.screenshot(return_img=True)
        return Image.fromarray(frame).convert("RGB")
    finally:
        plotter.close()


def compose(frame: Image.Image, layers: list[dict], view_label: str) -> Image.Image:
    width = VIEW_SIZE[0] + PANEL_WIDTH
    height = HEADER_HEIGHT + VIEW_SIZE[1] + FOOTER_HEIGHT
    canvas = Image.new("RGB", (width, height), BACKGROUND)
    canvas.paste(frame, (0, HEADER_HEIGHT))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, width, HEADER_HEIGHT), fill="#ffffff")
    draw.text((35, 22), "993 DASHBOARD  |  SCHEMATIC F0 / ASSUMED LAYOUT / NO SCAN",
              fill="#17212b", font=font(27, bold=True))
    draw.text((37, 67), view_label + "  |  X lateral, Y to windshield, Z up",
              fill="#526170", font=font(18))
    panel_left = VIEW_SIZE[0]
    draw.rectangle((panel_left, HEADER_HEIGHT, width, HEADER_HEIGHT + VIEW_SIZE[1]),
                   fill="#ffffff")
    draw.line((panel_left, HEADER_HEIGHT, panel_left, HEADER_HEIGHT + VIEW_SIZE[1]),
              fill="#d8dde3", width=2)
    draw.text((panel_left + 28, HEADER_HEIGHT + 26), "DISPLAY LAYERS",
              fill="#17212b", font=font(19, bold=True))
    row_y = HEADER_HEIGHT + 78
    row_step = min(63, max(43, (VIEW_SIZE[1] - 145) // len(layers)))
    for layer in layers:
        colour = ImageColor.getrgb(layer["colour"])
        draw.rounded_rectangle((panel_left + 28, row_y + 4,
                                panel_left + 55, row_y + 31), radius=4,
                               fill=colour, outline="#c3cad2", width=1)
        draw.text((panel_left + 69, row_y + 4), layer["label"],
                  fill="#17212b", font=font(16))
        row_y += row_step
    footer_top = HEADER_HEIGHT + VIEW_SIZE[1]
    draw.rectangle((0, footer_top, width, height), fill="#e9eef3")
    draw.text((35, footer_top + 20),
              "SYNTHETIC F0 DISPLAY  |  Assumed dimensions and display poses",
              fill="#7c3f17", font=font(19, bold=True))
    draw.text((35, footer_top + 60),
              "No measured vehicle transform. No claim of fit, safety, OEM identity or manufacturing readiness.",
              fill="#17212b", font=font(17))
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path,
                        help="PicoGK scene-report.json inside work/")
    parser.add_argument("--output", type=Path,
                        help="fresh output directory inside work/; default: <report parent>/renders")
    args = parser.parse_args()
    report_path = inside_work(args.report)
    if not report_path.is_file():
        parser.error(f"scene report does not exist: {report_path}")
    output = inside_work(args.output or (report_path.parent / "renders"))
    if output.exists():
        parser.error(f"choose a fresh output directory: {output}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        parser.error("scene report must be a JSON object")
    if report.get("status") != "visual_concept_only" or report.get("coordinate_frame") != "visual_stage_not_vehicle":
        parser.error("receipt must describe the unverified F0 visual stage")
    layers = load_layers(report_path, report)
    for source in (SCENE_SPEC, CSHARP_SOURCE, RENDER_SOURCE):
        if not source.is_file():
            parser.error(f"source file required for provenance is missing: {source}")
    if report.get("scene_sha256") != sha256(SCENE_SPEC):
        parser.error("scene source changed after the PicoGK receipt was generated")
    output.mkdir(parents=True)
    pv.OFF_SCREEN = True
    view_records = []
    for view_id, vector, label in VIEWS:
        frame = render_mesh(layers, vector)
        image = compose(frame, layers, label)
        path = output / f"dashboard-{view_id}.png"
        image.save(path, optimize=True)
        view_records.append({
            "view": view_id,
            "file": path.name,
            "sha256": sha256(path),
            "camera_vector": list(vector),
            "projection": "parallel",
            "resolution_px": list(image.size),
        })
    provenance = {
        "schema": "993-dashboard-f0-render.v1",
        "image_kind": "CAD technical illustration",
        "publication_terms": {
            "origin": "original project render",
            "geometry": "project-generated PicoGK F0 visual scene",
            "external_photo_scan_or_model": False,
        },
        "scene_id": report.get("scene_id"),
        "status": report.get("status"),
        "coordinate_frame": report.get("coordinate_frame"),
        "source_report": report_path.name,
        "source_report_sha256": sha256(report_path),
        "source_files": [
            {"file": source.relative_to(ROOT).as_posix(), "sha256": sha256(source)}
            for source in (SCENE_SPEC, CSHARP_SOURCE, RENDER_SOURCE)
        ],
        "renderer": {
            "pyvista": pv.__version__,
            "vtk": ".".join(map(str, pv.vtk_version_info)),
            "pillow": pillow_version,
        },
        "views": view_records,
        "render_qa": {
            "raw_stl_unchanged": True,
            "note": "Zero-area triangles are skipped by VTK in the PNG. They add no visible surface but remain a mesh-quality limitation in the source STL.",
        },
        "layers": [{key: value for key, value in layer.items() if key != "mesh"}
                   for layer in layers],
        "limitations": [
            "Synthetic F0 display in a visual frame; dimensions and poses are assumed.",
            "No measured vehicle transform or physical assembly is represented.",
            "Images do not establish fit, safety, OEM identity, or manufacturing readiness.",
        ],
    }
    sidecar = output / "render-report.json"
    sidecar.write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
    print(json.dumps({"images": [item["file"] for item in view_records],
                      "sidecar": str(sidecar)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
