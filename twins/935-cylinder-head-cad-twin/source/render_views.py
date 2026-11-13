"""Screenshots of the twin (private) and a non-geometric scorecard chart (public).

Private, geometry-bearing (owner decision 2026-11-06 keeps them out of Git):
  twin-observed-inferred.png  twin surface: grey = within 0.2 mm of the scan,
                              orange = inferred closure; studs in blue
  scan-deviation.png          acquired scan coloured by distance to T1
  thermal-field.png           CalculiX temperature on the tet-mesh boundary
Public (no geometry):
  media/scorecard-t1-cdf.png  cumulative share of scan area vs distance

Usage: render_views.py PRIVATE_DIR PARAMS_DIR OUT_DIR MEDIA_DIR
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_usd import classify  # noqa: E402  (visual aid only; evidence is score_twin.py)

VIEWS = (("iso, intake side", (1, -1, 0.8)), ("iso, exhaust side", (-1, 1, 0.8)),
         ("deck (combustion face)", (0, 0, -1)), ("cam side", (0, 0, 1)))


def poly(v, f):
    import pyvista as pv

    return pv.PolyData(v, np.column_stack((np.full(len(f), 3), f)).ravel())


def grid_shots(meshes, out, title, scalar_bar=None):
    import pyvista as pv

    pv.OFF_SCREEN = True
    p = pv.Plotter(off_screen=True, shape=(2, 2), window_size=(1800, 1400), border=False)
    for i, (label, direction) in enumerate(VIEWS):
        p.subplot(i // 2, i % 2)
        for m, kw in meshes:
            p.add_mesh(m, **kw)
        p.view_vector(direction, viewup=(0, 0, -1) if direction[2] == 0 or abs(direction[2]) < 1 else (0, 1, 0))
        p.add_text(label, font_size=11)
        if i == 0:
            p.add_text(title, position="lower_left", font_size=9)
        p.enable_parallel_projection()
        p.reset_camera()
    p.screenshot(str(out))
    p.close()


def main(private, params, out, media):
    import matplotlib
    import pyvista as pv
    import trimesh

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    private, params, out, media = map(Path, (private, params, out, media))
    out.mkdir(parents=True, exist_ok=True)
    media.mkdir(parents=True, exist_ok=True)
    hyp = json.loads((params.parent / "hypotheses.json").read_text())
    col = hyp["display_colours"]
    occ = json.loads((params / "occupancy-summary.json").read_text())
    bare = np.load(private / "bare-scan-twin.npz")

    sim = trimesh.load(private / "t1-sim-surface.stl", process=False, force="mesh")
    d = classify(np.asarray(sim.vertices), np.asarray(sim.faces), bare["v"], bare["f"])
    twin = poly(np.asarray(sim.vertices), np.asarray(sim.faces))
    rgb = np.where((d > 0.2)[:, None], np.array(col["inferred_closure"]), np.array(col["observed"]))
    twin.cell_data["rgb"] = (rgb * 255).astype(np.uint8)
    meshes = [(twin, {"scalars": "rgb", "rgb": True, "smooth_shading": False})]
    for s in occ["studs"]:
        if not s["accepted"]:
            continue
        ax = np.array(s["axis"], float)
        ax /= np.linalg.norm(ax)
        t0 = s.get("seat_level_along_axis", 0.0)
        c = np.array(s["point_on_axis"]) + (t0 + s["protrusion_mm"] / 2) * ax
        meshes.append((pv.Cylinder(center=c, direction=ax, radius=s["radius_mm"], height=s["protrusion_mm"]),
                       {"color": col["hardware"]}))
    grid_shots(meshes, out / "twin-observed-inferred.png",
               "935 bare-head twin T1 - grey observed, orange inferred (hypotheses), blue studs (hardware)")

    t1 = trimesh.load(private / "t1-bare-head.stl", process=False, force="mesh")
    used = np.unique(bare["f"])
    remap = -np.ones(len(bare["v"]), dtype=np.int64)
    remap[used] = np.arange(len(used))
    sv, sf = bare["v"][used], remap[bare["f"]]
    ds = classify(sv, sf, np.asarray(t1.vertices), np.asarray(t1.faces))
    scan = poly(sv, sf)
    scan.cell_data["distance_mm"] = ds
    grid_shots([(scan, {"scalars": "distance_mm", "clim": (0, 0.3), "cmap": "viridis",
                        "scalar_bar_args": {"title": "scan to twin (mm)"}})],
               out / "scan-deviation.png", "Acquired scan coloured by distance to the T1 twin (0-0.3 mm)")

    area = scan.compute_cell_sizes(length=False, volume=False)["Area"]
    o = np.argsort(ds)
    cum = np.cumsum(area[o]) / area.sum()
    fig, axp = plt.subplots(figsize=(7, 4), dpi=150)
    axp.plot(ds[o], cum * 100, color="#2b6cb0", lw=2)
    for t in (0.05, 0.1, 0.2):
        share = area[ds <= t].sum() / area.sum() * 100
        axp.axvline(t, color="#999", lw=0.8, ls="--")
        axp.annotate(f"{share:.1f}% within {t} mm", (t, share), textcoords="offset points", xytext=(6, -14), fontsize=8)
    axp.set_xlim(0, 0.4)
    axp.set_ylim(0, 100)
    axp.set_xlabel("distance from acquired scan facet to twin surface (mm)")
    axp.set_ylabel("share of acquired scan area (%)")
    axp.set_title("935 twin T1 scorecard (hardware excluded)", fontsize=10)
    axp.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(media / "scorecard-t1-cdf.png")

    frd = private / "thermal" / "head.frd"
    tets = private / "t1-tets.npz"
    if frd.exists() and tets.exists():
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from sim_thermal import read_frd_temperatures

        tm = np.load(tets)
        temps = read_frd_temperatures(frd)
        cells = np.column_stack((np.full(len(tm["t"]), 4), tm["t"])).ravel()
        ug = pv.UnstructuredGrid(cells, np.full(len(tm["t"]), pv.CellType.TETRA, dtype=np.uint8), tm["v"])
        ug.point_data["T_C"] = temps[: len(tm["v"])]
        surf = ug.extract_surface()
        grid_shots([(surf, {"scalars": "T_C", "cmap": "inferno", "scalar_bar_args": {"title": "T (degC)"}})],
                   out / "thermal-field.png", "Steady thermal screen under declared hypotheses (uncorrelated)")
    print("renders written to", out, "chart to", media)


if __name__ == "__main__":
    main(*sys.argv[1:5])
