#!/usr/bin/env python3
"""Render parts/<id>/media/gyroid.png: outside view and cutaway of the core.

    python render_gyroid.py <PART_ID> [<PART_ID> ...] | --all

Reads derived/*-picogk-gyroid.stl and its provenance JSON (written by
tools/finish.py --variant gyroid). The cored STL is not committed (tens of MB
per part); the provenance JSON pins its SHA-256 and gyroid.json regenerates it. The cut plane is the axis-aligned plane
that crosses the most separate section loops, so the core shows when there is
one; the section is capped, so solid material reads as a flat face. Writes media/gyroid.json with the source and image hashes.
"""
import hashlib
import json
import sys
from pathlib import Path

import pyvista as pv
import vtk

CATALOG = Path(__file__).resolve().parents[1]
ROOT = CATALOG.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from render_part_previews import color, display_rotation_x_deg  # noqa: E402

CAPTION = "PicoGK concept model with gyroid core - not the original part, not a print file"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capped_clip(mesh, normal, origin):
    """vtkClipClosedSurface directly: pyvista refuses the few non-manifold edges
    finish.py tolerates (max(4, 1e-5 of the edges))."""
    plane = vtk.vtkPlane()
    plane.SetNormal(*normal)
    plane.SetOrigin(*origin)
    planes = vtk.vtkPlaneCollection()
    planes.AddItem(plane)
    f = vtk.vtkClipClosedSurface()
    f.SetClippingPlanes(planes)
    f.SetInputData(mesh.triangulate())
    f.Update()
    return pv.wrap(f.GetOutput()).triangulate()


def cut_plane(mesh, cored):
    """Axis and origin of the section: the plane crossing the most separate
    section loops (the gyroid shows as many small loops) when the part is cored,
    otherwise the mid-plane with the longest section."""
    lo, hi = mesh.bounds[0::2], mesh.bounds[1::2]
    best, best_score = (0, mesh.center), -1.0
    for i in range(3):
        n = [0.0, 0.0, 0.0]
        n[i] = 1.0
        for t in ((0.3, 0.38, 0.46, 0.5, 0.54, 0.62, 0.7) if cored else (0.5,)):
            o = list(mesh.center)
            o[i] = lo[i] + t * (hi[i] - lo[i])
            s = mesh.slice(normal=n, origin=o)
            if not s.n_cells:
                continue
            score = (s.connectivity().point_data["RegionId"].max() + 1.0 if cored else
                     float(s.compute_cell_sizes(area=False, volume=False)["Length"].sum()))
            if score > best_score:
                best, best_score = (i, o), score
    return best


def withdrawn(part_dir):
    """Deliberately withdrawn renders stay withdrawn (AGENTS.md): a part whose
    preview is a status card for withdrawn views gets no gyroid image either."""
    prev = part_dir / "media" / "preview.json"
    if not prev.exists():
        return False
    info = json.loads(prev.read_text(encoding="utf-8"))
    return info.get("kind") == "status_card" and "withdrawn" in info.get("note", "")


def render(part_id):
    part_dir = ROOT / "parts" / part_id.lower()
    if withdrawn(part_dir):
        print(f"{part_id}: views withdrawn, no gyroid image (model and provenance only)")
        return
    stls = sorted((part_dir / "derived").glob("*-picogk-gyroid.stl"))
    if len(stls) != 1:
        raise SystemExit(f"{part_id}: expected one derived/*-picogk-gyroid.stl, found {len(stls)}")
    stl = stls[0]
    prov = json.loads(stl.with_suffix(".json").read_text(encoding="utf-8"))
    record = json.loads((ROOT / "catalog" / "parts" / (part_id.lower() + ".json")).read_text(encoding="utf-8"))
    mesh = pv.read(str(stl))
    rot = display_rotation_x_deg(part_id, [part_dir / "derived" / "x-picogk.stl"])
    if rot:
        mesh = mesh.rotate_x(rot, inplace=False)
    tint = color(record)
    core = prov.get("core", {})
    axis, origin = cut_plane(mesh, bool(core.get("cored")))
    normal = [0.0, 0.0, 0.0]
    normal[axis] = 1.0
    # Capped section: solid material shows as a flat face, the core as a web.
    cut = capped_clip(mesh, normal, origin)
    on_plane = abs(cut.cell_centers().points[:, axis] - origin[axis]) < 1e-3
    cut.cell_data["section"] = on_plane.astype(float)
    # Look into the cut face from the removed side, slightly tilted.
    view = [0.35, -0.35, 0.45]
    view[axis] = 1.0 if cut.center[axis] < origin[axis] else -1.0
    light = "#" + "".join(f"{int(int(tint[i:i + 2], 16) * 0.45 + 255 * 0.55):02x}" for i in (1, 3, 5))
    dark = "#" + "".join(f"{int(int(tint[i:i + 2], 16) * 0.55):02x}" for i in (1, 3, 5))   # cut face

    p = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1800, 820), border=False,
                   lighting="three lights")
    for i, (m, label) in enumerate(((mesh, "outside"), (cut, "section " + "XYZ"[axis] + " (cut face in the darker tint)"))):
        p.subplot(0, i)
        p.set_background("white")
        if i == 0:
            p.add_mesh(m, color=tint, smooth_shading=True, specular=0.35, specular_power=20, ambient=0.25, diffuse=0.8)
        else:
            p.add_mesh(m, scalars="section", cmap=[light, dark], clim=[0, 1], show_scalar_bar=False,
                       smooth_shading=False, specular=0.2, ambient=0.35, diffuse=0.8)
        up = (0, 0, 1) if axis != 2 else (0, 1, 0)
        p.view_vector(view if i == 1 else (0.9, -1.7, 1.0), viewup=up if i == 1 else (0, 0, 1))
        p.reset_camera()
        p.camera.zoom(1.2 if i == 0 else 0.95)
        p.add_text(label, position="upper_left", font_size=11, color="#2b2f33")
    note = (f"gyroid core: {core['cell_mm']:g} mm cell, {core['wall_mm']:g} mm wall, {core['skin_mm']:g} mm skin, "
            f"{core['drains']} drains, {core['mass_saving_pct']:.1f} % less material than the same part solid"
            if core.get("cored") else
            "no zone holds three gyroid cells: the part stays solid (owner rule: core only where 3 cells fit)")
    p.subplot(0, 0)
    p.add_text(CAPTION, position="lower_left", font_size=9, color="#a5282c")
    p.subplot(0, 1)
    p.add_text(note, position="lower_left", font_size=9, color="#444b52")
    p.enable_anti_aliasing("ssaa")
    media = part_dir / "media"
    media.mkdir(exist_ok=True)
    p.screenshot(str(media / "gyroid.png"))
    p.close()
    info = {
        "part_id": record["part_id"],
        "kind": "geometry_render",
        "note": ("Outside view and mid-plane cutaway of the part's PicoGK gyroid-core concept model. Not a "
                 "photograph, not a render of a manufactured part, not evidence of fit, function or printability."),
        "sources": [{"path": stl.relative_to(ROOT).as_posix(), "sha256": sha256(stl)}],
        "cut_axis": "xyz"[axis],
        "cut_origin_mm": [round(float(v), 2) for v in origin],
        "core": core,
        "images": ["gyroid.png"],
        "generator": "parts/picogk-catalog/bionic/render_gyroid.py",
        "license": "Repository LICENSE; owner-authorized publication on PorscheFanatics.com.",
        "image_sha256": {"gyroid.png": sha256(media / "gyroid.png")},
    }
    (media / "gyroid.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"rendered {(media / 'gyroid.png').relative_to(ROOT)}")


def main(argv):
    ids = [a for a in argv if not a.startswith("--")]
    if "--all" in argv:
        ids = [json.loads(p.read_text(encoding="utf-8"))["part_id"]
               for p in sorted(ROOT.glob("parts/993-*/source/gyroid.json"))]
    if not ids:
        raise SystemExit(__doc__)
    for pid in ids:
        render(pid)


if __name__ == "__main__":
    main(sys.argv[1:])
