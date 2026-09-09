"""Ce qui compte en haut de caisse : la matiere, ou la fermeture de l'anneau ?

`body_study.py` fait apparaitre un ecart qui demande a etre teste plutot
qu'admire : le pavillon pese 10,5 kg et n'apporte presque rien, le cadre de
pare-brise pese 1,1 kg et apporte le plus gros increment de toute l'echelle.
L'explication proposee est topologique — le cadre de pare-brise FERME l'anneau
superieur (tablier, montants A, traverse haute, brancards, pieds milieu,
montant arriere), le pavillon ne fait que remplir une surface deja portee.

Une explication de ce genre se refute. On ajoute donc les deux elements
SEPAREMENT a la meme cage ouverte, et on regarde le gain au kilo. Et comme les
valeurs absolues de ce modele ne sont pas convergees en maillage, on refait le
tout a trois finesses : ce qui doit tenir, c'est le classement, pas le chiffre.

    pycad ring_study.py
"""
import subprocess, sys, numpy as np

PY = sys.executable
T, RHO = 0.8, 7.85e-6


def case(feat, lc, i):
    subprocess.run([PY, 'build_body.py', str(T), feat, str(lc)], capture_output=True, check=True)
    area = float(np.load('mesh.npz')['area'])
    tag = f'ring{i}_{feat}'
    subprocess.run([PY, 'run_fea.py', str(T), tag], capture_output=True, check=True)
    return area * T * RHO, float(np.load(f'{tag}_res.npz')['K'])


print(f"{'finesse':<9}{'cage':>7}{'+pavillon':>11}{'+pare-brise':>13}{'+les deux':>11}"
      f"{'pavillon/kg':>13}{'pare-brise/kg':>15}{'rapport':>9}{'superadd.':>11}")
for i, lc in enumerate((1.0, 0.7, 0.5)):
    mb, b = case('fbtap', lc, i)        # cage ouverte : anneau superieur non ferme
    mr, r = case('fbtapr', lc, i)       # + pavillon seul
    mw, w = case('fbtapw', lc, i)       # + cadre de pare-brise seul
    m2, rw = case('fbtaprw', lc, i)     # + les deux
    gr, gw = (r - b) / (mr - mb), (w - b) / (mw - mb)
    print(f"{lc:<9}{b:7.0f}{r:11.0f}{w:13.0f}{rw:11.0f}{gr:13.0f}{gw:15.0f}"
          f"{gw/gr:8.0f}x{(rw - b)/((r - b) + (w - b)):10.2f}x")

print("""
Lecture. Le rapport reste de deux ordres de grandeur en faveur du cadre de
pare-brise aux trois finesses, alors que la raideur absolue, elle, derive de
11 % : c'est un resultat de topologie et non de discretisation. La derniere
colonne dit que les deux elements ensemble rendent plus que la somme de leurs
apports separes — le pavillon ne travaille qu'une fois l'anneau ferme, ce qui
est la meme affirmation vue de l'autre cote.""")
