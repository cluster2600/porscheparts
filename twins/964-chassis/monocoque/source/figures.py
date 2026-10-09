"""Figures of the plate-50-05a shell: four views, and the torsion stress map.

Reads ../derived/monocoque-shell.ply, ../derived/torsion-snapshot.npz and,
when present, ../derived/torsion-monocoque*.{json,npz} and
../derived/torsion-rings*.{json,npz}; writes ../evidence/shell-views.png,
../evidence/torsion-von-mises.png, ../evidence/torsion-monocoque.png and
../evidence/torsion-architectures.png.

    python3 figures.py
"""
import pathlib

import numpy as np

HERE = pathlib.Path(__file__).parent
DERIVED = HERE.parent / "derived"
EVIDENCE = HERE.parent / "evidence"
STOPS = ["#33415c", "#3e6a8a", "#4f9aa8", "#e9b44c", "#f07b3f", "#fff1d6"]


def camera(p, c, r, az, el, scale=2.05):
    a, e = np.radians(az), np.radians(el)
    p.camera.position = tuple(c + scale * r * np.array([np.cos(a) * np.cos(e), np.sin(a) * np.cos(e), np.sin(e)]))
    p.camera.focal_point = tuple(c)
    p.camera.up = (0, 0, 1) if el < 80 else (1, 0, 0)
    p.camera.view_angle = 24


def main():
    import pyvista as pv
    from matplotlib.colors import LinearSegmentedColormap
    pv.OFF_SCREEN = True
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    shell = pv.read(DERIVED / "monocoque-shell.ply").compute_normals(split_vertices=False)
    c, r = np.array(shell.center), float(np.ptp(np.asarray(shell.points), axis=0).max())
    p = pv.Plotter(off_screen=True, shape=(2, 2), window_size=(2400, 1350))
    for i, (name, az, el, ortho) in enumerate((("three-quarter front", 32, 16, False), ("three-quarter rear", -148, 20, False),
                                               ("side", 90, 0, True), ("top", 90, 89.9, True))):
        p.subplot(i // 2, i % 2)
        p.set_background("#0e1218", top="#232b36")
        p.add_mesh(shell, color="#5b6370", smooth_shading=True, specular=0.6, specular_power=40, ambient=0.25)
        camera(p, c, r, az, el)
        if ortho:
            p.enable_parallel_projection()
            p.camera.parallel_scale = 0.55 * r
        p.add_text(name, font_size=10, color="white")
    p.enable_anti_aliasing("ssaa")
    p.screenshot(EVIDENCE / "shell-views.png")
    p.close()

    t = np.load(DERIVED / "torsion-snapshot.npz")
    m = pv.PolyData(t["points"].astype(float), np.c_[np.full(len(t["triangles"]), 3), t["triangles"]].ravel())
    m.point_data["von Mises, MPa"] = t["von_mises"]
    clim = (0.0, float(np.percentile(t["von_mises"], 97)))
    cmap = LinearSegmentedColormap.from_list("hero", STOPS)
    p = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(2600, 900))
    for i, az in enumerate((32, -148)):
        p.subplot(0, i)
        p.set_background("#0e1218", top="#232b36")
        p.add_mesh(m, scalars="von Mises, MPa", cmap=cmap, clim=clim, smooth_shading=True, specular=0.4, ambient=0.25,
                   show_scalar_bar=(i == 1), scalar_bar_args={"color": "white"})
        camera(p, np.array(m.center), r, az, 16)
    p.add_text(f"torsion, 0.8 mm steel, K = {float(t['K']):,.0f} N.m/deg (this surface model, not a 964)",
               font_size=10, color="white")
    p.enable_anti_aliasing("ssaa")
    p.screenshot(EVIDENCE / "torsion-von-mises.png")
    p.close()
    print("wrote shell-views.png and torsion-von-mises.png")
    if (DERIVED / "torsion-monocoque.json").exists():
        monocoque_torsion(pv, cmap)
    if (DERIVED / "torsion-rings.json").exists():
        architectures(pv)


def architectures(pv):
    """The two PicoGK architectures on one mesh and one load: their closed
    sections, K against mass across the three meshes, and the twist."""
    import json
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    boxes = json.loads((DERIVED / "torsion-monocoque.json").read_text())
    rings = json.loads((DERIVED / "torsion-rings.json").read_text())
    tb = np.load(DERIVED / "torsion-monocoque-snapshot.npz")
    tg = np.load(DERIVED / "torsion-rings-model.npz")
    p = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(2600, 900))
    for i, (t, title) in enumerate(((tb, "picogk/: closed sections formed by the skin"),
                                    (tg, "picogk-rings/: tubes tangent to the skin"))):
        pts, tri, kind = t["points"].astype(float), t["triangles"], t["kind"]
        p.subplot(0, i)
        p.set_background("#0e1218", top="#232b36")
        for k, colour, op in ((0, "#8a929e", 0.12), (2, "#4f9aa8", 0.5), (3, "#4f9aa8", 0.5), (1, "#f07b3f", 1.0)):
            m = tri[kind == k]
            if len(m):
                p.add_mesh(pv.PolyData(pts, np.c_[np.full(len(m), 3), m].ravel()), color=colour, opacity=op,
                           smooth_shading=True, ambient=0.3)
        if "tube_segments" in t.files:
            seg = t["tube_segments"]
            lines = pv.PolyData(pts, lines=np.c_[np.full(len(seg), 2), seg].ravel())
            p.add_mesh(lines.tube(radius=28.0), color="#f07b3f", smooth_shading=True, ambient=0.3)
        camera(p, np.array([-1190.0, 0.0, 640.0]), 3780.0, 32, 18)
        p.add_text(title, font_size=11, color="white")
    p.enable_anti_aliasing("ssaa")
    top = Image.fromarray(p.screenshot(return_img=True))
    p.close()
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(16, 4.6), facecolor="#0e1218", gridspec_kw={"width_ratios": [1, 1.6]})
    series = [(boxes, "open shell, CFRP layup", "open shell", "#8a929e"),
              (boxes, "monocoque, CFRP layup", "picogk/ (skin boxes)", "#f07b3f"),
              (rings, "rings, CFRP layup", "picogk-rings/ (tubes)", "#e9b44c"),
              (rings, "rings without tubes, CFRP layup", "picogk-rings/ without its tubes", "#4f9aa8")]
    for doc, key, label, colour in series:
        row = doc["cases"][key]
        k = np.array(row["K"], float)
        ax.errorbar(row["mass_kg"], k[-1], yerr=[[k[-1] - k.min()], [k.max() - k[-1]]], fmt="o", color=colour,
                    ms=9, capsize=4, label=label)
        tw = np.array([np.nan if v is None else v for v in row["twist_deg"]])
        bx.plot(np.array(doc["twist_stations_d_mm"]), tw, color=colour, lw=2, label=f"{label}: K {row['K'][-1]:,}")
    for a in (ax, bx):
        a.set_facecolor("#0e1218")
        a.tick_params(colors="#9aa3ad")
        for sp in a.spines.values():
            sp.set_color("#3a4350")
        a.legend(frameon=False, labelcolor="white", fontsize=9)
    ax.set_xlabel("mass, kg (assumed CFRP layups)", color="#9aa3ad")
    ax.set_ylabel("K, N.m/deg (finest mesh; bars: range over 3 meshes)", color="#9aa3ad")
    bx.set_xlabel("d, mm behind the plate 0 line", color="#9aa3ad")
    bx.set_ylabel("section rotation, deg", color="#9aa3ad")
    bx.axvspan(2050, 2450, color="#3a4350", alpha=0.6)
    fig.tight_layout()
    fig.canvas.draw()
    bottom = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3])
    plt.close(fig)
    bottom = bottom.resize((top.width, int(bottom.height * top.width / bottom.width)), Image.LANCZOS)
    out = Image.new("RGB", (top.width, top.height + bottom.height), (14, 18, 24))
    out.paste(top, (0, 0))
    out.paste(bottom, (0, top.height))
    out.save(EVIDENCE / "torsion-architectures.png")
    print("wrote torsion-architectures.png")


def monocoque_torsion(pv, cmap):
    """Open shell against the monocoque architecture, same steel, same load:
    stress on one colour scale, and the twist along the car for all cases."""
    import json
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    r = json.loads((DERIVED / "torsion-monocoque.json").read_text())
    t = np.load(DERIVED / "torsion-monocoque-snapshot.npz")
    pts, tri, kind = t["points"].astype(float), t["triangles"], t["kind"]
    mesh = "S3, finest mesh" if len(next(iter(r["cases"].values()))["K"]) > 1 else "S3"
    clim = (0.0, float(np.percentile(t["von_mises_open_steel"][np.unique(tri[kind != 1])], 97)))
    p = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(2600, 900))
    for i, (key, name, keep) in enumerate((("von_mises_open_steel", "open shell", kind != 1),
                                           ("von_mises_monocoque_steel", "monocoque", np.ones(len(kind), bool)))):
        m = pv.PolyData(pts, np.c_[np.full(keep.sum(), 3), tri[keep]].ravel())
        m.point_data["von Mises, MPa"] = t[key]
        m = m.extract_cells(np.arange(m.n_cells)).extract_surface()
        p.subplot(0, i)
        p.set_background("#0e1218", top="#232b36")
        p.add_mesh(m, scalars="von Mises, MPa", cmap=cmap, clim=clim, smooth_shading=True, specular=0.4, ambient=0.25,
                   show_scalar_bar=(i == 1), scalar_bar_args={"color": "white"})
        camera(p, np.array(m.center), 3780.0, 32, 16)
        k = r["cases"][f"{name}, 0.8 mm steel"]["K"][-1]
        p.add_text(f"{name}, 0.8 mm steel: K = {k:,} N.m/deg ({mesh})", font_size=11, color="white")
    p.enable_anti_aliasing("ssaa")
    top = Image.fromarray(p.screenshot(return_img=True))
    p.close()
    fig, ax = plt.subplots(figsize=(13, 3.6), facecolor="#0e1218")
    ax.set_facecolor("#0e1218")
    styles = {"open shell, 0.8 mm steel": ("#8a929e", "--"), "open shell, CFRP layup": ("#8a929e", ":"),
              "monocoque, 0.8 mm steel": ("#f07b3f", "-"), "monocoque, CFRP layup": ("#4f9aa8", "-")}
    d = np.array(r["twist_stations_d_mm"])
    for name, row in r["cases"].items():
        tw = np.array([np.nan if v is None else v for v in row["twist_deg"]])
        c, ls = styles[name]
        ax.plot(d, tw, color=c, ls=ls, lw=2, label=f"{name}: K {row['K'][-1]:,}, {row['mass_kg']} kg")
    ax.axvspan(2050, 2450, color="#3a4350", alpha=0.6)
    ax.axvspan(-200, 150, color="#3a4350", alpha=0.35)
    ax.text(2250, ax.get_ylim()[1] * 0.92, "clamp", color="#9aa3ad", ha="center")
    ax.text(-25, ax.get_ylim()[1] * 0.92, "load", color="#9aa3ad", ha="center")
    ax.set_xlabel("d, mm behind the plate 0 line", color="#9aa3ad")
    ax.set_ylabel("section rotation, deg\nunder 1.14 kN.m", color="#9aa3ad")
    ax.tick_params(colors="#9aa3ad")
    for sp in ax.spines.values():
        sp.set_color("#3a4350")
    ax.legend(frameon=False, labelcolor="white", fontsize=9, loc="upper center")
    ax.set_xlim(d.min(), d.max())
    fig.tight_layout()
    fig.canvas.draw()
    bottom = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3])
    plt.close(fig)
    bottom = bottom.resize((top.width, int(bottom.height * top.width / bottom.width)), Image.LANCZOS)
    out = Image.new("RGB", (top.width, top.height + bottom.height), (14, 18, 24))
    out.paste(top, (0, 0))
    out.paste(bottom, (0, top.height))
    out.save(EVIDENCE / "torsion-monocoque.png")
    print("wrote torsion-monocoque.png")


if __name__ == "__main__":
    main()
