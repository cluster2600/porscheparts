"""La banniere animee de la page d'accueil, tiree du meme calcul que les figures.

Ce n'est pas un rendu et ce n'est pas une voiture. La cellule tourne pour qu'on
voie ce que le modele contient reellement — des coques minces, un longeron, un
tunnel, un pavillon — et elle est coloree par la contrainte de von Mises du cas
de torsion, lue dans le meme instantane que `figures.py`. Aucune image n'entre
dans ce depot sans que la donnee qui la produit y soit deja.

Les sections sont ASSUMED et le maillage n'est pas converge : la couleur montre
ou passe l'effort, elle ne donne aucune contrainte de 964.

    pymesh hero.py            # ecrit docs/media/diagrams/964-hero.gif
    pymesh hero.py --frames 24   # brouillon rapide
"""
import argparse, io, pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parents[2]
OUT = ROOT / "docs" / "media" / "diagrams" / "964-hero.gif"

# Meme fond clair explicite que les autres figures : GitHub rend le fichier tel
# quel sous ses deux themes, un fond transparent rendrait le texte illisible.
BG, FG, MUTED = "#ffffff", "#1a1a1a", "#666666"

LARGEUR, HAUTEUR, DPI, SS = 12.8, 5.0, 100, 2


def charge(nom="fbtaprw"):
    """Sommets, faces et von Mises nodal de l'instantane conserve."""
    d = np.load(HERE / "figures-mesh" / f"snap_{nom}.npz")
    xyz, tri = d["xyz"], d["tri"]
    idx = {int(n): j for j, n in enumerate(d["nid"])}
    faces = np.vectorize(idx.get)(tri)
    vm = np.zeros(len(d["nid"]), dtype="float32")
    for n, v in zip(d["vmn"], d["vm"]):
        j = idx.get(int(n))
        if j is not None:
            vm[j] = v
    return xyz, faces, vm[faces].mean(axis=1), float(d["K"])


def frame(xyz, faces, par_tri, K, azim, clim):
    """Une image : le texte a gauche, la cellule qui tourne a droite."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(LARGEUR, HAUTEUR), facecolor=BG, dpi=DPI)
    # Axes places a la main : tight_layout et subplots_adjust se battent avec
    # une vue 3D, et la banniere doit garder sa colonne de texte a gauche.
    ax = fig.add_axes((0.42, 0.02, 0.57, 0.96), projection="3d")
    pc = Poly3DCollection(xyz[faces], cmap="magma_r", linewidth=0)
    pc.set_array(par_tri)
    pc.set_clim(*clim)
    ax.add_collection3d(pc)

    lo, hi = xyz.min(0), xyz.max(0)
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(lo[2], hi[2])
    # Proportions reelles conservees ; le cadre est rempli, sinon la caisse se
    # perd au milieu d'un cube commun aux trois axes.
    ax.set_box_aspect(hi - lo, zoom=1.05)
    ax.view_init(elev=16, azim=azim)
    ax.set_axis_off()
    ax.set_facecolor(BG)

    fig.text(0.045, 0.80, "porscheparts", color=FG, fontsize=26,
             fontweight="bold", ha="left", va="top")
    fig.text(0.045, 0.645, "Retroconception ouverte\nPorsche 911 964 et 993",
             color=FG, fontsize=13, ha="left", va="top", linespacing=1.5)
    fig.text(0.045, 0.46, f"Cellule complete 964, von Mises\n"
             f"sous couple de torsion\nK = {K:.0f} N.m/deg, coques S6",
             color=MUTED, fontsize=10.5, ha="left", va="top", linespacing=1.6)
    # Barre de couleur horizontale dans la colonne de texte : sans echelle,
    # une carte de contrainte n'est qu'une image coloree.
    cax = fig.add_axes((0.045, 0.235, 0.17, 0.026))
    cb = fig.colorbar(pc, cax=cax, orientation="horizontal")
    cb.set_label("von Mises (MPa)", color=MUTED, fontsize=8.5, labelpad=3)
    cb.ax.tick_params(colors=MUTED, labelsize=7.5, length=2)
    cb.outline.set_visible(False)

    fig.text(0.045, 0.055, "Ni une 964, ni un rendu : l'instantane du calcul.\n"
             "Sections ASSUMED, seuls les rapports sont exploitables.",
             color=MUTED, fontsize=8.8, ha="left", va="bottom", linespacing=1.5)

    # Rendu au double puis reduction : les coques de 12 972 triangles moirent
    # violemment a la taille finale, le sur-echantillonnage les lisse.
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=BG, dpi=DPI * SS)
    plt.close(fig)
    buf.seek(0)
    im = Image.open(buf).convert("RGB")
    return im.resize((int(LARGEUR * DPI), int(HAUTEUR * DPI)), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=48)
    ap.add_argument("--couleurs", type=int, default=96)
    a = ap.parse_args()

    xyz, faces, par_tri, K = charge()
    # Le 99e centile evite qu'une singularite d'encastrement mange l'echelle.
    clim = (0.0, float(np.percentile(par_tri, 98)))
    azims = np.linspace(-180, 180, a.frames, endpoint=False)
    images = [frame(xyz, faces, par_tri, K, az, clim) for az in azims]

    pal = images[0].quantize(colors=a.couleurs, method=Image.MEDIANCUT)
    images = [im.quantize(palette=pal, dither=Image.NONE) for im in images]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(OUT, save_all=True, append_images=images[1:],
                   duration=90, loop=0, optimize=True)
    print(f"{OUT}  {OUT.stat().st_size / 1e6:.2f} Mo  {a.frames} images")


if __name__ == "__main__":
    main()
