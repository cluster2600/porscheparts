"""Deux figures pour la page d'accueil, tirees des calculs de ce dossier.

Elles ne montrent pas une voiture : elles montrent un resultat, et l'une des deux
montre un resultat FAUX a cote du vrai. C'est voulu. Le classement des elements
de caisse a ete publie en coques lineaires, puis corrige en quadratiques ; une
page d'accueil qui ne montrerait que la version corrigee cacherait ce que ce
depot a de plus utile.

Les valeurs sont lues dans `figures-data.json`, qui les fige et les rend
verifiables sans avoir a regenerer un corpus de 1,1 Go. Chaque champ y porte son
origine : quel script l'a produit, avec quel maillage.

    pymesh figures.py            # ecrit les SVG dans docs/media/diagrams/
    pymesh figures.py --corpus   # recalcule les exposants depuis les corpus
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

# Fond clair explicite : GitHub rend le SVG tel quel sous ses deux themes, et un
# fond transparent rendrait le texte sombre illisible en mode nuit.
BG, FG, GRID = "#ffffff", "#1a1a1a", "#d8d8d8"
S3, S6 = "#c9a227", "#1f6f8b"

NOMS = {
    "f": "plancher",
    "fb": "+ cloisons",
    "fbt": "+ tunnel",
    "fbta": "+ passages\nde roue",
    "fbtap": "+ pieds\nmilieu",
    "fbtapr": "+ pavillon",
    "fbtaprw": "+ cadre de\npare-brise",
}


def style(ax):
    ax.set_facecolor(BG)
    ax.tick_params(colors=FG, labelsize=8)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.yaxis.grid(True, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)


def fig_echelle(d):
    """K par architecture, dans les deux ordres d'element, a masse connue."""
    a = d["echelle_architectures"]
    feats = a["features"]
    x = np.arange(len(feats))
    fig, ax = plt.subplots(figsize=(8.2, 3.6), facecolor=BG)
    style(ax)
    ax.bar(x - 0.2, a["K_S3"], 0.4, label="coques lineaires S3", color=S3)
    ax.bar(x + 0.2, a["K_S6"], 0.4, label="coques quadratiques S6", color=S6)
    for i, (k3, k6) in enumerate(zip(a["K_S3"], a["K_S6"])):
        ax.text(i, max(k3, k6) + 250, f"-{100*(1-k6/k3):.0f} %",
                ha="center", fontsize=7.5, color=FG)
    ax.set_xticks(x)
    ax.set_xticklabels([NOMS[f] for f in feats])
    ax.set_ylabel("raideur en torsion  K  (N.m/deg)", color=FG, fontsize=9)
    ax.set_ylim(0, max(a["K_S3"]) * 1.18)
    ax.legend(frameon=False, fontsize=8, labelcolor=FG, loc="upper left")
    ax.set_title("Les triangles lineaires surestiment la raideur, et inegalement",
                 color=FG, fontsize=10.5, loc="left", pad=10)
    fig.text(0.012, 0.015,
             "Meme geometrie, meme chargement, meme depouillement. L'ecart est de "
             "41 % la ou la flexion domine et de 24 % la ou le cisaillement domine :\n"
             "ce n'est pas une affaire de finesse de maillage, c'est l'ordre de "
             "l'element. Sections ASSUMED : seuls les rapports sont exploitables.",
             fontsize=7.2, color="#555555", ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    p = OUT / "964-echelle-architectures.svg"
    fig.savefig(p, format="svg", facecolor=BG)
    plt.close(fig)
    return p


def fig_mecanisme(d):
    """Exposant d ln K / d ln G : la part de la raideur portee par le cisaillement."""
    a = d["exposant_G"]
    feats = a["features"]
    x = np.arange(len(feats))
    fig, ax = plt.subplots(figsize=(8.2, 3.6), facecolor=BG)
    style(ax)
    ax.plot(x, a["S3"], "o-", color=S3, label="corpus en S3, 3000 cas", linewidth=2)
    ax.plot(x, a["S6"], "o-", color=S6, label="corpus en S6, 3000 cas", linewidth=2)
    ax.axhline(0.0, color=GRID, linewidth=1)
    ax.annotate("flexion pure", xy=(0.06, 0.02), xycoords="axes fraction",
                fontsize=8, color="#555555")
    ax.annotate("cisaillement pur", xy=(0.06, 0.95), xycoords="axes fraction",
                fontsize=8, color="#555555")
    ax.set_xticks(x)
    ax.set_xticklabels([NOMS[f] for f in feats])
    ax.set_ylim(-0.05, 1.0)
    ax.set_ylabel("part du cisaillement\nd ln K / d ln G", color=FG, fontsize=9)
    ax.legend(frameon=False, fontsize=8, labelcolor=FG, loc="lower right")
    ax.set_title("Fermer un anneau ne fait pas qu'ajouter de la raideur : "
                 "cela change le mecanisme qui la porte",
                 color=FG, fontsize=10.5, loc="left", pad=10)
    fig.text(0.012, 0.015,
             "Sur le plancher nu la caisse flechit, sur la cellule fermee elle "
             "cisaille. La courbe S3 ne descend jamais a zero : les elements "
             "lineaires\nattribuent au cisaillement une part qui revient a la "
             "flexion. C'est ce controle qui a disqualifie le premier corpus, "
             "avant tout entrainement.",
             fontsize=7.2, color="#555555", ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    p = OUT / "964-mecanisme-architecture.svg"
    fig.savefig(p, format="svg", facecolor=BG)
    plt.close(fig)
    return p


def _snap(nom):
    return np.load(HERE / "figures-mesh" / f"snap_{nom}.npz")


def _pose(ax, xyz, zoom=1.35):
    """Vue isometrique, echelles egales, sans decor : c'est un schema, pas un rendu."""
    lo, hi = xyz.min(0), xyz.max(0)
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(lo[2], hi[2])
    # Proportions reelles conservees, mais le cadre est rempli : un cube commun
    # aux trois axes laisserait un modele plat perdu au milieu du vide.
    ax.set_box_aspect(hi - lo, zoom=zoom)
    ax.view_init(elev=22, azim=-60)
    ax.set_axis_off()
    ax.set_facecolor(BG)


def fig_modele():
    """Ce que le calcul contient — et ce qu'il ne contient pas."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(8.2, 3.6), facecolor=BG)
    titres = [("f", "plancher, longerons, traverses", 2442),
              ("fbtaprw", "cellule complete", 9093)]
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
        ax.set_title(f"{legende}\nK = {K} N.m/deg", color=FG, fontsize=8.5, y=1.0)
    fig.suptitle("Ce que le calcul contient. Ce n'est pas une 964.",
                 color=FG, fontsize=10.5, x=0.012, ha="left")
    fig.text(0.012, 0.015,
             "Coques minces, sections de longeron, de traverse et de montant "
             "ASSUMED, ni vitrage colle, ni portes, ni ouvertures dans les "
             "panneaux.\nLe modele repond a des questions relatives entre ces "
             "architectures ; il ne rend aucune raideur de vehicule.",
             fontsize=7.2, color="#555555", ha="left", va="bottom")
    # tight_layout se bat avec des axes 3D : le cadrage est impose a la main.
    fig.subplots_adjust(left=0.0, right=1.0, bottom=0.13, top=0.87, wspace=0.0)
    p = OUT / "964-modele-coque.svg"
    fig.savefig(p, format="svg", facecolor=BG, dpi=170)
    plt.close(fig)
    return p


def fig_effort():
    """Ou passe l'effort : contrainte de von Mises sur le plancher nu."""
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
    fig.suptitle("Le longeron porte la torsion, pas le plancher",
                 color=FG, fontsize=10.5, x=0.012, ha="left")
    fig.text(0.012, 0.015,
             "Contrainte moyenne de 25,5 MPa dans le longeron contre 10,6 dans le "
             "plancher, et les 1 % de noeuds\nles plus charges sont a 100 % dans le "
             "longeron — ils le restent apres exclusion de la zone\nd'encastrement. "
             "Le manuel y place l'acier haute resistance : calcul et planche 50-013 "
             "concordent.",
             fontsize=7.2, color="#555555", ha="left", va="bottom")
    fig.subplots_adjust(left=0.0, right=0.98, bottom=0.13, top=0.90)
    p = OUT / "964-chemin-effort.svg"
    fig.savefig(p, format="svg", facecolor=BG, dpi=170)
    plt.close(fig)
    return p


def depuis_corpus(d):
    """Recalcule les exposants de G depuis les corpus, s'ils sont presents."""
    sys.path.insert(0, str(HERE))
    import corpus_audit as A
    for cle, nom in (("S3", "corpus"), ("S6", "corpus_s6")):
        c = HERE / nom
        if not (c / "index.jsonl").exists():
            print(f"  {nom} absent, valeur figee conservee")
            continue
        rows = A.load(c)
        vals = []
        for f in d["exposant_G"]["features"]:
            sub = [r for r in rows if r["features"] == f]
            b, _, _ = A.fit(sub, A.LOGV)
            vals.append(round(b["G"], 3))
        d["exposant_G"][cle] = vals
        print(f"  {nom} relu : {vals}")
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
        print(f"ecrit {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
