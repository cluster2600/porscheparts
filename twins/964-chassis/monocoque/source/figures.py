"""Figures of the plate-50-05a shell: four views, and the torsion stress map.

Reads ../derived/monocoque-shell.ply, ../derived/torsion-snapshot.npz and,
when present, ../derived/torsion-monocoque*.{json,npz},
../derived/torsion-rings*.{json,npz}, ../derived/torsion-members.json,
../derived/torsion-layup.json and ../derived/bending*.{json,npz}; writes
../evidence/shell-views.png, ../evidence/torsion-von-mises.png,
../evidence/torsion-monocoque.png, ../evidence/torsion-architectures.png,
../evidence/torsion-members.png, ../evidence/torsion-layup.png and
../evidence/bending.png.

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
    if (DERIVED / "torsion-members.json").exists():
        members()
    if (DERIVED / "torsion-layup.json").exists():
        layup()
    if (DERIVED / "bending.json").exists():
        bending(pv, cmap)


def bending(pv, cmap):
    """Vertical bending: stress on the CFRP monocoque, the deflection of the
    sill line for the four cases, and what each member is worth in bending
    against torsion (cabin measures, finest mesh)."""
    import json
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    r = json.loads((DERIVED / "bending.json").read_text())
    t = np.load(DERIVED / "bending-snapshot.npz")
    pts, tri = t["points"].astype(float), t["triangles"]
    m = pv.PolyData(pts, np.c_[np.full(len(tri), 3), tri].ravel())
    m.point_data["von Mises, MPa"] = t["von_mises_monocoque_cfrp"]
    clim = (0.0, float(np.percentile(t["von_mises_monocoque_cfrp"][np.unique(tri)], 97)))
    row = r["cases"]["monocoque, CFRP layup"]
    p = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(2600, 900))
    for i, (az, el) in enumerate(((32, 16), (-90, -25))):
        p.subplot(0, i)
        p.set_background("#0e1218", top="#232b36")
        p.add_mesh(m, scalars="von Mises, MPa", cmap=cmap, clim=clim, smooth_shading=True, specular=0.4, ambient=0.25,
                   show_scalar_bar=(i == 1), scalar_bar_args={"color": "white"})
        p.add_points(pts[t["load_nodes"]], color="white", point_size=6, render_points_as_spheres=True)
        camera(p, np.array([-1190.0, 0.0, 640.0]), 3780.0, az, el)
    p.subplot(0, 0)
    p.add_text(f"bending, CFRP monocoque: K = {row['K'][-1]:,} N/mm ({row['mass_kg'][-1]} kg); "
               "white: load on the sills (supports inside the wheel houses, at the axles)", font_size=11, color="white")
    p.enable_anti_aliasing("ssaa")
    top = Image.fromarray(p.screenshot(return_img=True))
    p.close()
    mem = r.get("members", {}).get("members")
    fig, axes = plt.subplots(1, 2 if mem else 1, figsize=(16, 4.8), facecolor="#0e1218",
                             gridspec_kw={"width_ratios": [1.5, 1]} if mem else None)
    ax = axes[0] if mem else axes
    styles = {"open shell, 0.8 mm steel": ("#8a929e", "--"), "open shell, CFRP layup": ("#8a929e", ":"),
              "monocoque, 0.8 mm steel": ("#f07b3f", "-"), "monocoque, CFRP layup": ("#4f9aa8", "-")}
    d = np.array(r["profile_d_mm"])
    for name, row in r["cases"].items():
        w = np.array([np.nan if v is None else v for v in row["profile_mm_per_kN"]])
        c, ls = styles[name]
        ax.plot(d, w, color=c, ls=ls, lw=2, label=f"{name}: K {row['K'][-1]:,} N/mm, cabin {row['K_cabin'][-1]:,}")
    for at in r["load_case"]["axles_d_mm"]:
        ax.axvline(at, color="#4f9aa8", lw=1)
    ax.axvline(sum(r["load_case"]["axles_d_mm"]) / 2, color="white", lw=1, ls=":")
    ax.set_xlabel("d, mm behind the plate 0 line (blue: axles, dotted: load)", color="#9aa3ad")
    ax.set_ylabel("sill-line deflection, mm per kN", color="#9aa3ad")
    ax.legend(frameon=False, labelcolor="white", fontsize=9, loc="lower left")
    if mem:
        bx = axes[1]
        tors = json.loads((DERIVED / "torsion-members.json").read_text())["members"]
        names = sorted(mem, key=lambda n: -mem[n]["K_cabin_lost_fraction"][-1])
        y = np.arange(len(names))
        bx.barh(y - 0.19, [100 * mem[n]["K_cabin_lost_fraction"][-1] for n in names], height=0.38, color="#4f9aa8",
                label="bending, cabin")
        bx.barh(y + 0.19, [100 * tors[n]["K_cabin_lost_fraction"][-1] if n in tors else 0 for n in names], height=0.38,
                color="#e9b44c", label="torsion, cabin")
        bx.set_yticks(y, names, color="white")
        bx.invert_yaxis()
        bx.set_xlabel("cabin stiffness lost when the member is removed, %", color="#9aa3ad")
        bx.legend(frameon=False, labelcolor="white", fontsize=9, loc="lower right")
    for a in np.atleast_1d(axes):
        a.set_facecolor("#0e1218")
        a.tick_params(colors="#9aa3ad")
        for sp in a.spines.values():
            sp.set_color("#3a4350")
    fig.tight_layout()
    fig.canvas.draw()
    bottom = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3])
    plt.close(fig)
    bottom = bottom.resize((top.width, int(bottom.height * top.width / bottom.width)), Image.LANCZOS)
    out = Image.new("RGB", (top.width, top.height + bottom.height), (14, 18, 24))
    out.paste(top, (0, 0))
    out.paste(bottom, (0, top.height))
    out.save(EVIDENCE / "bending.png")
    print("wrote bending.png")


def layup():
    """Return of 0.5 mm more CFRP per wall family, and F1 against F0."""
    import json
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    r = json.loads((DERIVED / "torsion-layup.json").read_text())
    fams = list(r["sensitivity"])
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(16, 4.8), facecolor="#0e1218", gridspec_kw={"width_ratios": [1.6, 1]})
    y = np.arange(len(fams))
    for j, (key, colour, label) in enumerate((("K_per_kg", "#f07b3f", "K at the load points"),
                                              ("K_cabin_per_kg", "#e9b44c", "cabin K"))):
        ax.barh(y + (j - 0.5) * 0.38, [r["sensitivity"][f][key][-1] for f in fams], height=0.38, color=colour,
                label=f"{label}, {r['meshes'][-1]['sections']} sections")
    ax.set_yticks(y, [f"{f} ({r['sensitivity'][f]['area_m2'][-1]} m², {r['f0_mm'][f]} mm)" for f in fams], color="white")
    ax.invert_yaxis()
    ax.set_xlabel(f"N.m/deg gained per kg of CFRP added (+{r['step_mm']} mm)", color="#9aa3ad")
    f1 = r["F1"]
    labels = [f"{m['sections']} sections" for m in r["meshes"]]
    x = np.arange(len(labels))
    for j, (key, f0key, colour, name) in enumerate((("K_gain_fraction", "K_F0", "#f07b3f", "K"),
                                                    ("K_cabin_gain_fraction", "K_cabin_F0", "#e9b44c", "cabin K"))):
        bx.bar(x + (j - 0.5) * 0.38, [100 * g for g in f1[key]], width=0.38, color=colour, label=name)
    bx.axhline(0, color="#9aa3ad", lw=0.8)
    bx.set_xticks(x, labels, color="white")
    bx.set_ylabel("F1 against F0, same mass, %", color="#9aa3ad")
    changed = ", ".join(f"{f} {v:.2f}" for f, v in f1["mm"][-1].items() if abs(v - r["f0_mm"][f]) > 0.005)
    bx.set_title(f"F1 at F0 mass: engine-lid ring out\n{changed} mm", color="white", fontsize=9)
    for a, loc in ((ax, "lower right"), (bx, "lower center")):
        a.set_facecolor("#0e1218")
        a.tick_params(colors="#9aa3ad")
        for sp in a.spines.values():
            sp.set_color("#3a4350")
        a.legend(frameon=False, labelcolor="white", fontsize=9, loc=loc)
    fig.tight_layout()
    fig.savefig(EVIDENCE / "torsion-layup.png", dpi=110, facecolor="#0e1218")
    plt.close(fig)
    print("wrote torsion-layup.png")


def members():
    """Leave-one-out: stiffness each member carries, and its return per kg
    against the whole architecture's."""
    import json
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    r = json.loads((DERIVED / "torsion-members.json").read_text())
    names = sorted(r["members"], key=lambda n: -r["members"][n]["K_lost_fraction"][-1])
    full = r["meshes"][-1]
    avg = full["K_full"] / full["mass_full_kg"]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(16, 5.2), facecolor="#0e1218")
    y = np.arange(len(names))
    for a in (ax, bx):
        a.set_facecolor("#0e1218")
        a.tick_params(colors="#9aa3ad")
        for sp in a.spines.values():
            sp.set_color("#3a4350")
        a.set_yticks(y, names, color="white")
        a.invert_yaxis()
    for j, (key, colour, label) in enumerate((("K_lost_fraction", "#f07b3f", "K at the load points"),
                                              ("K_cabin_lost_fraction", "#e9b44c", "cabin K, d 400 to 1950"))):
        lost = [100 * r["members"][n][key][-1] for n in names]
        ax.barh(y + (j - 0.5) * 0.38, lost, height=0.38, color=colour, label=f"{label}, {full['sections']} sections")
    for j, (mesh, colour) in enumerate(zip(r["meshes"], ("#4f9aa8", "#f07b3f"))):
        ret = [r["members"][n]["return_N_m_deg_per_kg"][j] or 0 for n in names]
        bx.barh(y + (j - 0.5) * 0.38, ret, height=0.38, color=colour, label=f"{mesh['sections']} sections")
    bx.axvline(avg, color="white", ls="--", lw=1)
    bx.text(avg, -0.9, f" whole architecture: {avg:.0f}", color="white", fontsize=9, va="bottom")
    ax.set_xlabel("K lost when the member is removed, %", color="#9aa3ad")
    bx.set_xlabel("return: K lost per kg of member, N.m/deg/kg", color="#9aa3ad")
    for a in (ax, bx):
        a.legend(frameon=False, labelcolor="white", fontsize=9, loc="lower right")
    fig.suptitle(f"Members of the picogk/ monocoque in torsion, CFRP layup (full: K {full['K_full']:,} N.m/deg, "
                 f"{full['mass_full_kg']} kg; leave-one-out)", color="white")
    fig.tight_layout()
    fig.savefig(EVIDENCE / "torsion-members.png", dpi=110, facecolor="#0e1218")
    plt.close(fig)
    print("wrote torsion-members.png")


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
    shells_json = DERIVED / "torsion-shell-tubes.json"
    shell = json.loads(shells_json.read_text()) if shells_json.exists() else None
    shell_tubes = np.load(DERIVED / "torsion-shell-tubes-model.npz") if shell else None
    p = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(2600, 900))
    for i, (t, title) in enumerate(((tb, "picogk/: closed sections formed by the skin"),
                                    (tg, "picogk-rings/: tubes tangent to the skin" + (", meshed as shells" if shell else "")))):
        pts, tri, kind = t["points"].astype(float), t["triangles"], t["kind"]
        p.subplot(0, i)
        p.set_background("#0e1218", top="#232b36")
        for k, colour, op in ((0, "#8a929e", 0.12), (2, "#4f9aa8", 0.5), (3, "#4f9aa8", 0.5), (1, "#f07b3f", 1.0)):
            m = tri[kind == k]
            if len(m):
                p.add_mesh(pv.PolyData(pts, np.c_[np.full(len(m), 3), m].ravel()), color=colour, opacity=op,
                           smooth_shading=True, ambient=0.3)
        if "tube_segments" in t.files and shell_tubes is not None:     # the tubes as meshed, with their walls
            sp, stri, n0 = shell_tubes["points"].astype(float), shell_tubes["triangles"], int(shell_tubes["n_shell"])
            m = stri[n0:]
            p.add_mesh(pv.PolyData(sp, np.c_[np.full(len(m), 3), m].ravel()), color="#f07b3f", smooth_shading=True, ambient=0.3)
        elif "tube_segments" in t.files:
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
    if shell:
        series[2] = (rings, "rings, CFRP layup", "picogk-rings/, beam tubes on a 40 mm strip", "#9a7a3a")
        series.append((shell, "rings, CFRP layup", "picogk-rings/, tubes meshed as shells", "#e9b44c"))
    for doc, key, label, colour in series:
        row = doc["cases"][key]
        k = np.array(row["K"], float)
        ax.errorbar(row["mass_kg"], k[-1], yerr=[[k[-1] - k.min()], [k.max() - k[-1]]], fmt="o", color=colour,
                    ms=9, capsize=4, label=label)
        tw = np.array([np.nan if v is None else v for v in row["twist_deg"]])
        bx.plot(np.array(doc["twist_stations_d_mm"]), tw, color=colour, lw=2, label=f"{label}: K {row['K'][-1]:,}")
    sens = rings.get("bond_sensitivity")
    if sens:                                     # the tube result hinges on the bond width
        row = rings["cases"]["rings, CFRP layup"]
        ks = [r["K"][-1] for r in sens["rows"]] + [row["K"][-1]]
        ax.vlines(row["mass_kg"] + 1.2, min(ks), max(ks), color="#9a7a3a", lw=6, alpha=0.35,
                  label="picogk-rings/, beam tubes: bond strip 0 to 60 mm")
        for r in sens["rows"]:
            ax.annotate(f"{2 * r['bond_radius_mm']:.0f} mm", (row["mass_kg"] + 2.2, r["K"][-1]), color="#9a7a3a", fontsize=8,
                        va="center")
        ax.annotate(f"{2 * rings['meshes'][-1]['tubes']['bond_radius_mm']:.0f} mm", (row["mass_kg"] + 2.2, row["K"][-1]),
                    color="#9a7a3a", fontsize=8, va="center")
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
