"""Que rapporte chaque etage de la caisse, du plancher nu a la cellule fermee ?

`architecture_study.py` a repondu a une question de materiau : a masse egale,
fermer le caisson vaut plus que passer au carbone. Il s'arretait au tunnel.
Cette etude-ci prolonge l'echelle jusqu'a une cellule complete — passages de
roue, pieds milieu, pavillon, cadre de pare-brise — parce que c'est la seule
piste du dossier qui ne depende d'aucune donnee exterieure : elle ne demande que
des sections ASSUMED de plus.

Le but reste relatif. Aucun de ces chiffres n'est une raideur de 964 : ils
disent dans quel ordre les elements d'une caisse portent la torsion, et ce
classement-la ne depend pas des sections choisies autant que les valeurs.

Meme essai que partout ailleurs : arriere encastre, couple applique en pointes
de longeron. Acier 0,8 mm, l'epaisseur annoncee par Porsche.

    pycad body_study.py
"""
import subprocess, sys, numpy as np
from laminate import STEEL

PY = sys.executable
T = 0.8
LADDER = [
    ("f",       "plancher, longerons, traverses"),
    ("fb",      "+ tablier et cloison arriere"),
    ("fbt",     "+ tunnel central"),
    ("fbta",    "+ passages de roue"),
    ("fbtap",   "+ pieds milieu et brancards"),
    ("fbtapr",  "+ pavillon"),
    ("fbtaprw", "+ cadre de pare-brise"),
]


def run(feat):
    r = subprocess.run([PY, 'build_body.py', f'{T:.4f}', feat], capture_output=True, text=True)
    if r.returncode:
        print(r.stdout, r.stderr); sys.exit(1)
    area = float(np.load('mesh.npz')['area'])
    r = subprocess.run([PY, 'run_fea.py', f'{T:.4f}', f'body_{feat}'], capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-900:], r.stderr[-900:]); sys.exit(1)
    return area, float(np.load(f'body_{feat}_res.npz')['K'])


print(f"{'architecture':<34}{'aire m2':>9}{'masse kg':>10}{'K N.m/deg':>11}"
      f"{'K/m':>8}{'dK':>8}{'dK/dm':>9}")
prev = None
rows = []
for feat, label in LADDER:
    area, K = run(feat)
    m = area * T * STEEL['rho'] * 1e-6
    dK = f"{K - prev[1]:+8.0f}" if prev else "       -"
    dKdm = f"{(K - prev[1]) / (m - prev[0]):+9.0f}" if prev else "        -"
    print(f"{label:<34}{area/1e6:9.3f}{m:10.2f}{K:11.0f}{K/m:8.1f}{dK}{dKdm}")
    rows.append((feat, label, area, m, K))
    prev = (m, K)

f0, fN = rows[0], rows[-1]
print(f"\nDu plancher nu a la cellule fermee : K x {fN[4]/f0[4]:.2f} pour une masse x "
      f"{fN[3]/f0[3]:.2f}, soit une raideur specifique x {(fN[4]/fN[3])/(f0[4]/f0[3]):.2f}.")
best = max(rows[1:], key=lambda r: (r[4] - rows[rows.index(r) - 1][4]) / (r[3] - rows[rows.index(r) - 1][3]))
print(f"Meilleur rendement au kilo ajoute : « {best[1]} ».")
np.savez('body_study.npz', feat=[r[0] for r in rows], area=[r[2] for r in rows],
         mass=[r[3] for r in rows], K=[r[4] for r in rows])
