#!/usr/bin/env python3
"""Render a product view of every part from its own CAD, for its folder's README.

A part folder on GitHub used to open on a bare list of STEP, STL and JSON files:
nothing showed what the part looks like. This script tessellates each part's
derived CAD (STEP preferred, STL otherwise) and renders two images into
`parts/<id>/media/`:

- `preview.png` — a shaded three-quarter view;
- `views.png`   — front, side and top orthographic views with the CAD bounding
                  box in millimeters.

Both are **geometry views of a concept CAD**, not photographs, not renders of a
manufactured part, and not evidence of fit or function. `preview.json` records
which file each image was made from, with its SHA-256, so a stale image is
detected when the CAD changes.

    # rendering needs pyvista/VTK and build123d: run it in the cadsim image,
    # memory-capped, one part at a time (see `make part-previews`)
    python3 scripts/render_part_previews.py --write [--only PART_ID]

    # the check needs only the standard library: it runs in `make check`
    python3 scripts/render_part_previews.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "catalog" / "parts"
PARTS = ROOT / "parts"

# Material family keyword -> display color. A color hints at the material; it
# says nothing about the finish, which no record specifies.
COLORS = [
    (("inconel", "in625", "in718", "nickel", "n07751", "n06625"), "#9a8f7c"),
    (("ti-6al-4v", "titanium", "ti64", "grade 5"), "#8f9aa6"),
    (("fiber", "fibre", "composite", "resin", "carbon"), "#3b3f45"),
    (("abs", "asa", "petg", "pa12", "polymer", "nylon", "to_be_determined_after"), "#34373b"),
    (("steel", "acier"), "#8a9097"),
    (("alsi10mg", "aluminum", "aluminium", "al2139", "6063", "cp1", "aheadd"), "#c4c9cf"),
]
DEFAULT_COLOR = "#b5bac0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(RECORDS.glob("*.json"))]


def sources(part_id: str) -> list[Path]:
    """The part's derived CAD, one file per stem, STEP before STL, at most three.

    A PicoGK model (`derived/*-picogk.stl`, see parts/picogk-catalog/) takes
    precedence: when one exists, only the PicoGK models are shown.
    """
    folder = PARTS / part_id.lower() / "derived"
    if not folder.is_dir():
        return []
    picogk = sorted(folder.glob("*-picogk.stl"))
    if picogk:
        return picogk[:3]
    chosen: dict[str, Path] = {}
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() not in (".step", ".stp", ".stl"):
            continue
        if p.stem not in chosen or p.suffix.lower() in (".step", ".stp"):
            chosen[p.stem] = p
    return list(chosen.values())[:3]


def color(record: dict) -> str:
    m = record.get("manufacturing", {}).get("material", {})
    text = " ".join(str(m.get(k, "")) for k in ("family", "grade")).lower()
    for keys, value in COLORS:
        if any(k in text for k in keys):
            return value
    return DEFAULT_COLOR


# --- rendering (cadsim image only) -------------------------------------------

def mesh_of(path: Path):
    import pyvista as pv
    if path.suffix.lower() == ".stl":
        return pv.read(str(path))
    from build123d import export_stl, import_step
    shape = import_step(str(path))
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "m.stl"
        size = max(shape.bounding_box().size.X, shape.bounding_box().size.Y,
                   shape.bounding_box().size.Z)
        export_stl(shape, str(out), tolerance=max(size / 2000, 0.005), angular_tolerance=0.15)
        return pv.read(str(out))


def render(record: dict) -> dict | None:
    import pyvista as pv
    pv.OFF_SCREEN = True
    part_id = record["part_id"]
    files = sources(part_id)
    if not files:
        return None
    meshes = [mesh_of(f) for f in files]
    smooth = all(f.name.endswith("-picogk.stl") for f in files)   # voxel meshes read as solids smoothed
    tint = color(record)
    media = PARTS / part_id.lower() / "media"
    media.mkdir(exist_ok=True)

    def scene(plotter, view: str):
        plotter.set_background("white")
        offset = 0.0
        for m in meshes:
            m = m.copy()
            if len(meshes) > 1:
                b = m.bounds
                m.translate((offset - b[0], -(b[2] + b[3]) / 2, 0), inplace=True)
                offset += (b[1] - b[0]) * 1.25
            plotter.add_mesh(m, color=tint, smooth_shading=smooth, specular=0.35 if smooth else 0.25,
                             specular_power=20 if smooth else 15, ambient=0.25, diffuse=0.8)
            edges = m.extract_feature_edges(feature_angle=35, boundary_edges=True,
                                            non_manifold_edges=False, manifold_edges=False)
            if edges.n_points and not smooth:
                plotter.add_mesh(edges, color="#2b2f33", line_width=1.2)
        if view == "iso":
            # three-quarter view from front-left, above: shows the X-Z profile
            # that most extruded parts are drawn in, plus depth
            plotter.view_vector((0.9, -1.7, 1.0), viewup=(0, 0, 1))
        else:
            {"front": plotter.view_xz, "side": plotter.view_yz, "top": plotter.view_xy}[view]()
            plotter.enable_parallel_projection()
        plotter.reset_camera()
        plotter.camera.zoom(1.15 if view == "iso" else 1.05)

    p = pv.Plotter(off_screen=True, window_size=(1400, 900), lighting="three lights")
    scene(p, "iso")
    p.enable_anti_aliasing("ssaa")
    p.screenshot(str(media / "preview.png"))
    p.close()

    union = meshes[0].merge(meshes[1:]) if len(meshes) > 1 else meshes[0]
    b = union.bounds
    dims = [round(b[1] - b[0], 1), round(b[3] - b[2], 1), round(b[5] - b[4], 1)]
    p = pv.Plotter(off_screen=True, shape=(1, 3), window_size=(1800, 620), border=False,
                   lighting="three lights")
    labels = {"front": f"front (X-Z)  {dims[0]} x {dims[2]} mm",
              "side": f"side (Y-Z)  {dims[1]} x {dims[2]} mm",
              "top": f"top (X-Y)  {dims[0]} x {dims[1]} mm"}
    for i, view in enumerate(("front", "side", "top")):
        p.subplot(0, i)
        scene(p, view)
        p.add_text(labels[view], position="lower_edge", font_size=10, color="#2b2f33")
    p.enable_anti_aliasing("ssaa")
    p.screenshot(str(media / "views.png"))
    p.close()

    info = {
        "part_id": part_id,
        "note": ("Geometry views of the part's PicoGK concept model (parts/picogk-catalog/). "
                 if smooth else "Geometry views of the concept CAD. ")
                + "Not a photograph, not a render of a manufactured part, not evidence of fit or function.",
        "sources": [{"path": f.relative_to(ROOT).as_posix(), "sha256": sha256(f)} for f in files],
        "bounding_box_mm": dims,
        "images": ["preview.png", "views.png"],
        "generator": "scripts/render_part_previews.py",
    }
    (media / "preview.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8", newline="\n")
    return info


# --- check (standard library only) -------------------------------------------

def check() -> int:
    stale, missing = [], []
    for record in records():
        part_id = record["part_id"]
        files = sources(part_id)
        info_path = PARTS / part_id.lower() / "media" / "preview.json"
        if not files:
            continue
        if not info_path.exists():
            missing.append(part_id)
            continue
        info = json.loads(info_path.read_text(encoding="utf-8"))
        expected = [{"path": f.relative_to(ROOT).as_posix(), "sha256": sha256(f)} for f in files]
        images = [info_path.parent / name for name in info.get("images", [])]
        if info.get("sources") != expected or not all(i.exists() for i in images):
            stale.append(part_id)
    for part_id in missing:
        print(f"FAIL   no preview for {part_id}", file=sys.stderr)
    for part_id in stale:
        print(f"FAIL   preview older than its CAD: {part_id}", file=sys.stderr)
    if missing or stale:
        print("       rerun: make part-previews", file=sys.stderr)
        return 1
    print("OK   parts/*/media, every part with CAD has a preview made from its current CAD")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--only", help="render a single part_id")
    ap.add_argument("--list", action="store_true", help="print part_ids that have CAD")
    a = ap.parse_args()
    if a.check:
        return check()
    todo = [r for r in records() if not a.only or r["part_id"].lower() == a.only.lower()]
    if a.list:
        for r in todo:
            if sources(r["part_id"]):
                print(r["part_id"])
        return 0
    for r in todo:
        info = render(r)
        print(f"{'rendered' if info else 'no CAD  '} {r['part_id']}"
              + (f"  {info['bounding_box_mm']} mm" if info else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
