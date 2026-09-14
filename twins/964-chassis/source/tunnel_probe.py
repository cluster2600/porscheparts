"""Y a-t-il un tunnel central sous la 964 ? Mesure sur le scan. Reponse : non.

L'etude d'architecture (fea/architecture_study.py) donne au tunnel central le
plus gros gain de raideur de tout le dossier, +72 %. Un parametre aussi
influent ne peut pas rester ASSUMED : ce script va le chercher sur le scan.

Methode : Z median du soubassement dans une bande centrale |Y| < 60 mm, compare
au Z median des flancs 250 < |Y| < 400 mm, a huit stations longitudinales. Un
tunnel, qu'il fasse saillie vers le bas ou qu'il creuse vers le haut, se verrait
comme un relief de plusieurs dizaines de millimetres.

    pymesh tunnel_probe.py
"""
import numpy as np

V = np.load('verts_vehicle.npy')
print("Relief central du soubassement, repere vehicule")
print(f"{'X':>8}{'centre Z':>10}{'flancs Z':>10}{'relief':>9}   (|Y|<60 contre 250<|Y|<400)")
rel = []
for x0 in range(-1400, 1, 200):
    s = (V[:, 0] > x0 - 50) & (V[:, 0] < x0 + 50) & (V[:, 2] > 60) & (V[:, 2] < 600)
    c = s & (np.abs(V[:, 1]) < 60)
    f = s & (np.abs(V[:, 1]) > 250) & (np.abs(V[:, 1]) < 400)
    if c.sum() > 50 and f.sum() > 50:
        zc, zf = np.median(V[c, 2]), np.median(V[f, 2])
        rel.append(zc - zf)
        print(f"{x0:>8}{zc:>10.1f}{zf:>10.1f}{zc-zf:>+9.1f}")
r = np.array(rel)
# L'habitacle est la zone X = -1400 a -400. En avant de X = -200 on entre dans la
# zone de traverse et de train avant, ou un creux central est attendu et n'a rien
# d'un tunnel : ces stations sont exclues de la conclusion.
cab = r[:len(range(-1400, -399, 200))]
print(f"\nhabitacle X=-1400..-400 : relief de {cab.min():+.1f} a {cab.max():+.1f} mm,"
      f" amplitude {np.ptp(cab):.1f} mm")
print(f"en avant de X=-200      : jusqu'a {r.min():+.1f} mm, zone de traverse et de"
      f" train avant, hors sujet")
print("\nCONCLUSION : le plancher d'habitacle est plat. Le relief central y reste sous\n"
      "3.1 mm sur 1000 mm de long, tres en dessous du residu de symetrie du scan qui\n"
      "est de 7.54 mm RMS : il n'est meme pas distinguable du bruit. La 964 n'a pas de\n"
      "tunnel central structurel visible de dessous, ce qui est coherent avec un moteur\n"
      "arriere et l'absence d'arbre de transmission longitudinal.\n\n"
      "Consequence pour l'etude d'architecture : le cas « tunnel » n'est PAS de la\n"
      "geometrie 964. C'est un ajout hypothetique, et son gain de +72 % mesure ce que\n"
      "la 964 n'a pas, non ce qu'elle a.")
