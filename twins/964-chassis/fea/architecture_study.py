"""Architecture contre materiau : lequel rapporte le plus en raideur de torsion ?

L'etude composite conclut que le gain d'un monocoque est architectural et non
materiel. C'est une affirmation RELATIVE, donc elle se teste sans dependre
d'aucune raideur de caisse 964 publiee — ce qui tombe bien, il n'en existe pas.

Plan d'experience : le meme essai de torsion, sur trois architectures de plus en
plus fermees, avec deux materiaux A MASSE EGALE. La comparaison porte sur la
raideur specifique K/m, seule grandeur qui autorise a departager.

  f    plancher, longerons, traverses          (le modele d'origine)
  fb   + tablier avant et cloison arriere      (le caisson est ferme en bout)
  fbt  + tunnel central                        (poutre longitudinale fermee)

    pycad architecture_study.py
"""
import subprocess, sys, numpy as np
from laminate import hybrid, STEEL

PY = sys.executable
T_STEEL = 0.8
ARCH = [("f", "plancher seul"), ("fb", "+ cloisons"), ("fbt", "+ cloisons + tunnel")]
carbon = hybrid(1.0)
# masse surfacique egale a l'acier 0,8 mm -> epaisseur equivalente du stratifie
T_CARB = T_STEEL * STEEL['rho'] / carbon['rho']

MATS = [("acier 0,8 mm", T_STEEL, STEEL['E'], STEEL['nu'], STEEL['rho']),
        (f"carbone QI {T_CARB:.2f} mm", T_CARB, carbon['E'], carbon['nu'], carbon['rho'])]


def build(feat, t):
    r = subprocess.run([PY, 'build_body.py', f'{t:.4f}', feat], capture_output=True, text=True)
    if r.returncode: print(r.stdout, r.stderr); sys.exit(1)
    return float(np.load('mesh.npz')['area'])


def solve(t, tag, E, nu):
    r = subprocess.run([PY, 'run_fea.py', f'{t:.4f}', tag, f'{E:.1f}', f'{nu:.4f}'],
                       capture_output=True, text=True)
    if r.returncode: print(r.stdout[-900:], r.stderr[-900:]); sys.exit(1)
    return float(np.load(f'{tag}_res.npz')['K'])


print(f"{'architecture':<22}{'materiau':<20}{'aire m2':>9}{'masse kg':>10}"
      f"{'K N.m/deg':>11}{'K/m':>9}")
res = {}
for feat, aname in ARCH:
    for mname, t, E, nu, rho in MATS:
        area = build(feat, t)                       # mm2
        K = solve(t, f"arch_{feat}_{mname[:3]}", E, nu)
        m = area * t * rho * 1e-6                   # kg  (mm2 * mm * g/cm3 * 1e-6)
        res[(feat, mname)] = (K, m, area)
        print(f"{aname:<22}{mname:<20}{area/1e6:9.3f}{m:10.2f}{K:11.0f}{K/m:9.1f}")

s0 = res[("f", MATS[0][0])]
s2 = res[("fbt", MATS[0][0])]
c0 = res[("f", MATS[1][0])]
print(f"\n--- Ce que rapporte chaque levier, a masse egale ---")
print(f"fermer la caisse, a acier constant : K/m x {(s2[0]/s2[1])/(s0[0]/s0[1]):.2f}"
      f"   ({s0[0]:.0f} -> {s2[0]:.0f} N.m/deg pour {s0[1]:.1f} -> {s2[1]:.1f} kg)")
print(f"passer au carbone, a plancher seul : K/m x {(c0[0]/c0[1])/(s0[0]/s0[1]):.2f}"
      f"   ({s0[0]:.0f} -> {c0[0]:.0f} N.m/deg a masse egale)")
c2 = res[("fbt", MATS[1][0])]
print(f"les deux ensemble                  : K/m x {(c2[0]/c2[1])/(s0[0]/s0[1]):.2f}")
print("\nLe rapport des deux premiers chiffres est la reponse : il dit combien de fois\n"
      "l'architecture pese plus lourd que le materiau dans le resultat final.")
