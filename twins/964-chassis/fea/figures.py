"""Figures for the home page, drawn from the computations in this directory.

They do not show a car: they show a result, and one of them shows a WRONG
result next to the correct one. That is deliberate. The ranking of body shell
elements was published with linear shells, then corrected with quadratic ones;
a home page that showed only the corrected version would hide the most useful
thing this repository has.

The values are read from `figures-data.json`, which freezes them and makes them
checkable without regenerating a 1.1 GB corpus. Each field records its origin:
which script produced it, with which mesh.

    pymesh figures.py            # writes the SVGs to docs/media/diagrams/
    pymesh figures.py --corpus   # recomputes the exponents from the corpora
"""
import argparse, json, pathlib, subprocess, sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parents[2]
OUT = ROOT / "docs" / "media" / "diagrams"
DATA = HERE / "figures-data.json"

# Explicit light background: GitHub renders the SVG as-is under both themes, and
# a transparent background would make the dark text unreadable in dark mode.
BG, FG, GRID = "#ffffff", "#1a1a1a", "#d8d8d8"
S3, S6 = "#c9a227", "#1f6f8b"

NOMS = {
    "f": "floor pan",
    "fb": "+ bulkheads",
    "fbt": "+ tunnel",
    "fbta": "+ wheel\narches",
    "fbtap": "+ B-pillars",
    "fbtapr": "+ roof",
    "fbtaprw": "+ windshield\nframe",
}


def style(ax):
    ax.set_facecolor(BG)
    ax.tick_params(colors=FG, labelsize=8)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.yaxis.grid(True, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)


def fig_echelle(d):
    """K per architecture, for both element orders, at known mass."""
    a = d["echelle_architectures"]
    feats = a["features"]
    x = np.arange(len(feats))
    fig, ax = plt.subplots(figsize=(8.2, 3.6), facecolor=BG)
    style(ax)
    ax.bar(x - 0.2, a["K_S3"], 0.4, label="linear shells S3", color=S3)
    ax.bar(x + 0.2, a["K_S6"], 0.4, label="quadratic shells S6", color=S6)
    for i, (k3, k6) in enumerate(zip(a["K_S3"], a["K_S6"])):
        ax.text(i, max(k3, k6) + 250, f"-{100*(1-k6/k3):.0f}%",
                ha="center", fontsize=7.5, color=FG)
    ax.set_xticks(x)
    ax.set_xticklabels([NOMS[f] for f in feats])
    ax.set_ylabel("torsional stiffness  K  (N.m/deg)", color=FG, fontsize=9)
    ax.set_ylim(0, max(a["K_S3"]) * 1.18)
    ax.legend(frameon=False, fontsize=8, labelcolor=FG, loc="upper left")
    ax.set_title("Linear triangles overestimate stiffness, and unevenly",
                 color=FG, fontsize=10.5, loc="left", pad=10)
    fig.text(0.012, 0.015,
             "Same geometry, same loading, same post-processing. The gap is 41% "
             "where bending dominates and 24% where shear dominates:\n"
             "this is not a matter of mesh refinement, it is the element order. "
             "Sections ASSUMED: only the ratios are usable.",
             fontsize=7.2, color="#555555", ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    p = OUT / "964-echelle-architectures.svg"
    fig.savefig(p, format="svg", facecolor=BG)
    plt.close(fig)
    return p


def fig_mecanisme(d):
    """Exponent d ln K / d ln G: the share of stiffness carried by shear."""
    a = d["exposant_G"]
    feats = a["features"]
    x = np.arange(len(feats))
    fig, ax = plt.subplots(figsize=(8.2, 3.6), facecolor=BG)
    style(ax)
    ax.plot(x, a["S3"], "o-", color=S3, label="S3 corpus, 3,000 cases", linewidth=2)
    ax.plot(x, a["S6"], "o-", color=S6, label="S6 corpus, 3,000 cases", linewidth=2)
    ax.axhline(0.0, color=GRID, linewidth=1)
    ax.annotate("pure bending", xy=(0.06, 0.02), xycoords="axes fraction",
                fontsize=8, color="#555555")
    ax.annotate("pure shear", xy=(0.06, 0.95), xycoords="axes fraction",
                fontsize=8, color="#555555")
    ax.set_xticks(x)
    ax.set_xticklabels([NOMS[f] for f in feats])
    ax.set_ylim(-0.05, 1.0)
    ax.set_ylabel("shear share\nd ln K / d ln G", color=FG, fontsize=9)
    ax.legend(frameon=False, fontsize=8, labelcolor=FG, loc="lower right")
    ax.set_title("Closing a ring does not just add stiffness: "
                 "it changes the mechanism that carries it",
                 color=FG, fontsize=10.5, loc="left", pad=10)
    fig.text(0.012, 0.015,
             "On the bare floor pan the body shell bends; on the closed cell it "
             "shears. The S3 curve never drops to zero: linear elements\n"
             "assign to shear a share that belongs to bending. This check is "
             "what disqualified the first corpus, before any training.",
             fontsize=7.2, color="#555555", ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    p = OUT / "964-mecanisme-architecture.svg"
    fig.savefig(p, format="svg", facecolor=BG)
    plt.close(fig)
    return p


def _snap(nom):
    return np.load(HERE / "figures-mesh" / f"snap_{nom}.npz")


def _pose(ax, xyz, zoom=1.35):
    """Isometric view, equal scales, no decoration: it is a diagram, not a rendering."""
    lo, hi = xyz.min(0), xyz.max(0)
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(lo[2], hi[2])
    # True proportions are kept, but the frame is filled: a cube shared by the
    # three axes would leave a flat model lost in the middle of empty space.
    ax.set_box_aspect(hi - lo, zoom=zoom)
    ax.view_init(elev=22, azim=-60)
    ax.set_axis_off()
    ax.set_facecolor(BG)


def fig_modele():
    """What the computation contains, and what it does not."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(8.2, 3.6), facecolor=BG)
    titres = [("f", "floor pan, side rails, cross members", 2442),
              ("fbtaprw", "full cell", 9093)]
    for i, (nom, legende, K) in enumerate(titres):
        d = _snap(nom)
        xyz, tri = d["xyz"], d["tri"]
        idx = {int(n): j for j, n in enumerate(d["nid"])}
        f = np.vectorize(idx.get)(tri)
        ax = fig.add_subplot(1, 2, i + 1, projection="3d")
        pc = Poly3DCollection(xyz[f], facecolor="#e8e4dc", edgecolor="#9a9a9a",
                              linewidth=0.15, rasterized=True)
        ax.add_collection3d(pc)
        _pose(ax, xyz, zoom=1.05)
        ax.set_title(f"{legende}\nK = {K} N.m/deg, linear S3 shells", color=FG, fontsize=8.5, y=1.0)
    fig.suptitle("What the computation contains. It is not a 964.",
                 color=FG, fontsize=10.5, x=0.012, ha="left")
    fig.text(0.012, 0.015,
             "Thin shells; side rail, cross member and pillar sections "
             "ASSUMED; no bonded glazing, no doors, no openings in the "
             "panels.\nThe model answers relative questions between these "
             "architectures; it yields no vehicle stiffness.",
             fontsize=7.2, color="#555555", ha="left", va="bottom")
    # tight_layout fights with 3D axes: the framing is set by hand.
    fig.subplots_adjust(left=0.0, right=1.0, bottom=0.13, top=0.87, wspace=0.0)
    p = OUT / "964-modele-coque.svg"
    fig.savefig(p, format="svg", facecolor=BG, dpi=170)
    plt.close(fig)
    return p


def fig_effort():
    """Where the load goes: von Mises stress on the bare floor pan."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    d = _snap("f")
    xyz, tri = d["xyz"], d["tri"]
    idx = {int(n): j for j, n in enumerate(d["nid"])}
    f = np.vectorize(idx.get)(tri)
    vm = np.zeros(len(d["nid"]))
    for n, v in zip(d["vmn"], d["vm"]):
        j = idx.get(int(n))
        if j is not None:
            vm[j] = v
    par_tri = vm[f].mean(axis=1)
    fig = plt.figure(figsize=(6.6, 3.4), facecolor=BG)
    ax = fig.add_subplot(111, projection="3d")
    pc = Poly3DCollection(xyz[f], cmap="magma_r", linewidth=0, rasterized=True)
    pc.set_array(par_tri)
    pc.set_clim(0, np.percentile(par_tri, 99))
    ax.add_collection3d(pc)
    _pose(ax, xyz)
    cb = fig.colorbar(pc, ax=ax, shrink=0.62, pad=0.02)
    cb.set_label("von Mises (MPa)", color=FG, fontsize=8)
    cb.ax.tick_params(colors=FG, labelsize=7.5)
    cb.outline.set_visible(False)
    fig.suptitle("The side rail carries the torsion, not the floor pan",
                 color=FG, fontsize=10.5, x=0.012, ha="left")
    fig.text(0.012, 0.015,
             "Mean stress of 25.5 MPa in the side rail versus 10.6 in the "
             "floor pan, and the 1% most loaded\nnodes are all in the side "
             "rail; they remain so after excluding the clamped zone.\n"
             "The manual puts high-strength steel there: computation and plate "
             "50-013 agree.",
             fontsize=7.2, color="#555555", ha="left", va="bottom")
    fig.subplots_adjust(left=0.0, right=0.98, bottom=0.13, top=0.90)
    p = OUT / "964-chemin-effort.svg"
    fig.savefig(p, format="svg", facecolor=BG, dpi=170)
    plt.close(fig)
    return p


def depuis_corpus(d):
    """Recomputes the G exponents from the corpora, if they are present."""
    sys.path.insert(0, str(HERE))
    import corpus_audit as A
    for cle, nom in (("S3", "corpus"), ("S6", "corpus_s6")):
        c = HERE / nom
        if not (c / "index.jsonl").exists():
            print(f"  {nom} missing, frozen value kept")
            continue
        rows = A.load(c)
        vals = []
        for f in d["exposant_G"]["features"]:
            sub = [r for r in rows if r["features"] == f]
            b, _, _ = A.fit(sub, A.LOGV)
            vals.append(round(b["G"], 3))
        d["exposant_G"][cle] = vals
        print(f"  {nom} reread: {vals}")
    DATA.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", action="store_true")
    a = ap.parse_args()
    d = json.loads(DATA.read_text())
    if a.corpus:
        depuis_corpus(d)
    OUT.mkdir(parents=True, exist_ok=True)
    for p in (fig_echelle(d), fig_mecanisme(d), fig_modele(), fig_effort()):
        print(f"wrote {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
