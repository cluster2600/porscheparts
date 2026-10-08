"""Figures of the plate-50-05a shell: four views, and the torsion stress map.

Reads ../derived/monocoque-shell.ply and ../derived/torsion-snapshot.npz,
writes ../evidence/shell-views.png and ../evidence/torsion-von-mises.png.

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
    print("wrote shell-views.png and torsion-von-mises.png")


if __name__ == "__main__":
    main()
