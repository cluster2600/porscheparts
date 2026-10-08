"""Figures, light mesh and mass estimate of the PicoGK monocoque.

Reads the member groups written by the PicoGK run (work/monocoque-*.stl and
work/monocoque.report.json) and writes:

- ../derived/zesad-monocoque.vtp: the four groups, decimated, with a
  "group" cell array (0 skin, 1 closed sections, 2 sandwich panels, 3 wheel
  tubs), for viewing without PicoGK;
- ../derived/zesad-monocoque.report.json: the PicoGK report plus a mass
  estimate from ASSUMED layups;
- ../evidence/zesad-monocoque-views.png, -sections.png and -turntable.gif.

    python3 figures.py            # cadsim image
    python3 figures.py --frames 8 # quick draft
"""
import argparse
import json
import pathlib

import numpy as np

HERE = pathlib.Path(__file__).parent
WORK = HERE / "work"
DERIVED = HERE.parent / "derived"
EVIDENCE = HERE.parent / "evidence"
GROUPS = ["skin", "sections", "panels", "tubs"]
LABELS = {"skin": "outer skin", "sections": "closed sections", "panels": "sandwich panels", "tubs": "wheel tubs"}
COLOURS = {"skin": "#8a929e", "sections": "#f07b3f", "panels": "#4f9aa8", "tubs": "#e9b44c"}
# ASSUMED layups, kg/m2 of mid-surface: CFRP at 1.55 g/cm3; panels are two
# 1.2 mm CFRP faces on a 22.6 mm aramid honeycomb at 48 kg/m3.
LAYUP = {
    "skin": ("2.0 mm CFRP", 2.0 * 1.55),
    "sections": ("2.5 mm CFRP", 2.5 * 1.55),
    "panels": ("2 x 1.2 mm CFRP on 22.6 mm honeycomb, 48 kg/m3", 2 * 1.2 * 1.55 + 22.6 * 0.048),
    "tubs": ("1.5 mm CFRP", 1.5 * 1.55),
}
CUTS_D = [500, 1200, 1820, 2400]
BG = "#0e1218"


def read_stl(path):
    """Binary STL without trusting its normals (PicoGK leaves some NaN)."""
    import pyvista as pv
    n = int(np.fromfile(path, dtype="<u4", count=1, offset=80)[0])
    rec = np.fromfile(path, dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")], count=n, offset=84)
    pts, tri = np.unique(rec["v"].reshape(-1, 3), axis=0, return_inverse=True)
    tri = tri.reshape(-1, 3)
    tri = tri[(tri[:, 0] != tri[:, 1]) & (tri[:, 1] != tri[:, 2]) & (tri[:, 2] != tri[:, 0])]
    return pv.PolyData(pts.astype(float), np.c_[np.full(len(tri), 3), tri].ravel())


def camera(p, az, el, scale=1.0):
    c, r = np.array([-1190.0, 0.0, 640.0]), 3900.0
    a, e = np.radians(az), np.radians(el)
    p.camera.position = tuple(c + scale * 1.55 * r * np.array([np.cos(a) * np.cos(e), np.sin(a) * np.cos(e), np.sin(e)]))
    p.camera.focal_point = tuple(c)
    p.camera.up = (0, 0, 1)
    p.camera.view_angle = 24


def add(p, meshes, skin_opacity=1.0, half=False):
    for k, m in meshes.items():
        if half:
            m = m.clip(normal=(0, -1, 0), origin=(0, 0, 0))
        if skin_opacity == 0 and k == "skin":
            continue
        p.add_mesh(m, color=COLOURS[k], smooth_shading=True, specular=0.5, specular_power=30, ambient=0.25,
                   opacity=skin_opacity if k == "skin" else 1.0)


def views(meshes):
    import pyvista as pv
    p = pv.Plotter(off_screen=True, shape=(2, 2), window_size=(2400, 1400))
    panes = [("three-quarter front", 35, 18, 1.0, False), ("three-quarter rear", -145, 22, 1.0, False),
             ("without the skin", 40, 28, 0.0, False), ("cut on the centre line, skin removed", 90, 8, 0.0, True)]
    for i, (name, az, el, op, half) in enumerate(panes):
        p.subplot(i // 2, i % 2)
        p.set_background(BG, top="#232b36")
        add(p, meshes, op, half)
        camera(p, az, el, 0.62 if half else 0.85)
        p.add_text(name, font_size=10, color="white")
    p.subplot(0, 0)
    p.add_legend([[LABELS[k], COLOURS[k]] for k in GROUPS], bcolor=BG, face="rectangle", size=(0.24, 0.2), loc="lower right")
    p.enable_anti_aliasing("ssaa")
    p.screenshot(EVIDENCE / "zesad-monocoque-views.png")
    p.close()


def sections(full):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, len(CUTS_D), figsize=(18, 4.4), facecolor=BG)
    for ax, d in zip(axes, CUTS_D):
        ax.set_facecolor(BG)
        for k in GROUPS:
            s = full[k].slice(normal=(1, 0, 0), origin=(-d, 0, 0))
            if s.n_points == 0:
                continue
            pts, lines = np.asarray(s.points), s.lines.reshape(-1, 3)[:, 1:]
            seg = pts[lines][:, :, 1:]
            ax.add_collection(matplotlib.collections.LineCollection(seg, colors=COLOURS[k], linewidths=1.1))
        ax.set_xlim(-900, 900)
        ax.set_ylim(100, 1360)
        ax.set_aspect("equal")
        ax.set_title(f"d = {d} mm", color="white", fontsize=11)
        ax.tick_params(colors="#9aa3ad", labelsize=8)
        for sp in ax.spines.values():
            sp.set_color("#3a4350")
    handles = [matplotlib.lines.Line2D([], [], color=COLOURS[k], lw=3, label=LABELS[k]) for k in GROUPS]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False, labelcolor="white")
    fig.suptitle("Cross-sections, looking forward (y, z in mm). d is measured behind the plate 0 line.",
                 color="white", fontsize=12)
    fig.savefig(EVIDENCE / "zesad-monocoque-sections.png", dpi=110, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


def turntable(meshes, frames):
    import pyvista as pv
    from PIL import Image
    p = pv.Plotter(off_screen=True, window_size=(1280, 720))
    p.set_background(BG, top="#232b36")
    add(p, meshes, 0.18)
    images = []
    for i in range(frames):
        camera(p, 35 + 360.0 * i / frames, 20, 1.05)
        p.reset_camera_clipping_range()
        p.render()
        images.append(Image.fromarray(p.screenshot(return_img=True)).resize((800, 450), Image.LANCZOS))
    p.close()
    palette = images[0].quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    gif = [im.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG) for im in images]
    gif[0].save(EVIDENCE / "zesad-monocoque-turntable.gif", save_all=True, append_images=gif[1:], duration=90, loop=0)


def report():
    r = json.loads((WORK / "monocoque.report.json").read_text())
    total = 0.0
    for k in GROUPS:
        g = r["groups"][k]
        layup, kg_m2 = LAYUP[k]
        g["assumed_layup"] = layup
        g["mass_kg_estimate"] = round(g["area_m2_estimate"] * kg_m2, 1)
        total += g["mass_kg_estimate"]
    r["mass_kg_estimate"] = round(total, 1)
    r["mass_basis"] = ("area from voxel volume / geometric thickness, times an ASSUMED layup areal mass; "
                       "no joints, inserts, adhesive, glass or lids; order of magnitude only")
    (DERIVED / "zesad-monocoque.report.json").write_text(json.dumps(r, indent=2) + "\n")
    return r


def main():
    import pyvista as pv
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=48)
    a = ap.parse_args()
    pv.OFF_SCREEN = True
    EVIDENCE.mkdir(exist_ok=True)
    full = {k: read_stl(WORK / f"monocoque-{k}.stl") for k in GROUPS}
    light = {k: m.decimate(0.97) for k, m in full.items()}
    parts = []
    for i, k in enumerate(GROUPS):
        m = light[k].copy()
        m.cell_data["group"] = np.full(m.n_cells, i, np.uint8)
        parts.append(m)
    merged = pv.merge(parts).extract_surface(algorithm="dataset_surface")
    merged.save(DERIVED / "zesad-monocoque.vtp")
    r = report()
    sections(full)
    views(full)
    turntable(light, a.frames)
    print(f"{merged.n_cells} triangles in the light mesh; mass estimate {r['mass_kg_estimate']} kg (ASSUMED layups)")


if __name__ == "__main__":
    main()
