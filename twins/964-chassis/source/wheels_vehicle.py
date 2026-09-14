"""Centres d'essieu dans le REPERE VEHICULE, et non dans le repere du scan.

Corrige un piege : `wheel_fits.npy`, produit par `wheels.py`, est exprime dans les
axes du scan brut, ou +Y est l'avant et +X la droite, et ses colonnes ne sont pas
nommees. Ses valeurs ne peuvent donc PAS etre combinees avec `verts_vehicle.npy`,
qui est aligne. Le faire donne un centre d'essieu avant hors de la boite
englobante du vehicule.

Ce script rejoue l'ajustement dans le repere vehicule, ou X est vers l'avant, Y
vers la gauche et Z vers le haut : le plan de roue est donc XZ et le cercle s'y
ajuste. Il ne relit pas l'OBJ de 210 Mo, seulement les .npy deja produits par
`align.py`.

Sortie : `wheel_fits_vehicle.npz`, avec des noms de champs explicites.
"""
import numpy as np, trimesh
from trimesh.graph import connected_components

V = np.load('verts_vehicle.npy').astype(np.float64)
F = np.load('faces.npy').astype(np.int64)
m = trimesh.Trimesh(vertices=V, faces=F, process=False)
cc = sorted(connected_components(m.face_adjacency, nodes=np.arange(len(F)), engine='scipy'),
            key=len, reverse=True)


def fit_circle(x, z):
    """Kasa + raffinement robuste IRLS (poids de Cauchy) -> centre et rayon."""
    A = np.c_[x, z, np.ones(len(x))]; b = x ** 2 + z ** 2
    for _ in range(15):
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
        cx, cz = sol[0] / 2, sol[1] / 2
        r = np.sqrt(sol[2] + cx ** 2 + cz ** 2)
        d = np.abs(np.hypot(x - cx, z - cz) - r)
        w = 1.0 / (1.0 + (d / max(np.median(d) * 3, 1.0)) ** 2)
        A = np.c_[x, z, np.ones(len(x))] * w[:, None]; b = (x ** 2 + z ** 2) * w
    return cx, cz, r, d


rows = []
print(f"{'roue':<14}{'n':>9}{'X (avant)':>11}{'Z (haut)':>10}{'R':>8}{'Y lateral':>11}{'resid p90':>11}")
for i in (1, 2, 3, 4):
    P = V[np.unique(F[cc[i]].ravel())]
    cx, cz, r, _ = fit_circle(P[:, 0], P[:, 2])
    keep = np.abs(np.hypot(P[:, 0] - cx, P[:, 2] - cz) - r)
    keep = keep < np.percentile(keep, 70)          # bande de roulement bien ajustee
    cx, cz, r, d = fit_circle(P[keep, 0], P[keep, 2])
    y = P[:, 1].mean()
    side = 'GAUCHE' if y > 0 else 'DROITE'
    end = ''                                        # attribue apres coup, voir plus bas
    rows.append((cx, y, cz, r))
    print(f"{side:<14}{len(P):>9}{cx:>11.1f}{cz:>10.1f}{r:>8.1f}{y:>11.1f}"
          f"{np.percentile(d,90):>11.2f}")

a = np.array(rows[:])
# L'origine du repere ADR-0003 est SUR l'essieu avant : les roues avant sont donc a
# X ~ 0 et les arriere a X ~ -2280. Un test de signe se trompe, on separe par rang.
order = np.argsort(-a[:, 0])
front, rear = a[order[:2]], a[order[2:]]
fX, rX = front[:, 0].mean(), rear[:, 0].mean()
print(f"\nessieu avant   X = {fX:8.1f} mm      essieu arriere X = {rX:8.1f} mm")
print(f"EMPATTEMENT      = {fX-rX:8.1f} mm      usine 2272 -> {fX-rX-2272:+.1f} mm "
      f"({100*(fX-rX-2272)/2272:+.3f} %)")
# Controle d'auto-coherence : l'origine ADR-0003 est posee SUR l'essieu avant, donc
# un fX proche de zero confirme que le repere et cet ajustement sont d'accord.
print(f"controle : |X essieu avant| = {abs(fX):.1f} mm, doit etre proche de 0 par"
      f" definition du repere")
print(f"\necartement des centres de composant de roue, INDICATIF : avant"
      f" {abs(front[0,1]-front[1,1]):.1f} mm, arriere {abs(rear[0,1]-rear[1,1]):.1f} mm.")
print("Ce n'est PAS une voie : Y est ici la moyenne du composant de roue entier,"
      " flanc compris,\nnon le plan de roue. Les voies du dossier restent celles du"
      " README du jumeau.")
np.savez('wheel_fits_vehicle.npz', centre_x=a[:, 0], centre_y=a[:, 1], centre_z=a[:, 2],
         radius=a[:, 3], front_axle_x=fX, rear_axle_x=rX, wheelbase=fX - rX,
         frame='vehicle: X avant, Y gauche, Z haut, origine ADR-0003')
print("\n-> wheel_fits_vehicle.npz  (repere vehicule, champs nommes)")
