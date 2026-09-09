"""Carbone/kevlar contre acier, a raideur en torsion egale, sur le meme essai.

Reprend l'essai de torsion de run_fea.py sans en changer ni la geometrie, ni le
chargement, ni les conditions aux limites : seuls le materiau et l'epaisseur
changent. La reference est le plancher acier a 0,8 mm, 2442 N.m/deg.

La raideur de ce caisson suit lineairement l'epaisseur (README.md, rapport 1,251
pour 1,250) parce qu'il travaille en cisaillement de membrane. On s'en sert pour
predire l'epaisseur iso-raideur, PUIS on la verifie par un calcul complet.

    pycad build_shell.py 0.8 1.0 && pycad composite_study.py
"""
import subprocess, sys, os, numpy as np
from laminate import hybrid, STEEL

PY = sys.executable
REF_T, REF_K = 0.8, 2442.0          # acier, plancher de reference


def run(t, tag, E, nu):
    r = subprocess.run([PY, 'run_fea.py', f'{t:.4f}', tag, f'{E:.1f}', f'{nu:.4f}'],
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-800:], r.stderr[-800:]); sys.exit(1)
    d = np.load(f'{tag}_res.npz')
    return float(d['K']), float(np.percentile(d['vm'], 99))


def areal_mass(t_mm, rho):
    """Masse surfacique, kg/m2."""
    return t_mm * rho


G_steel = STEEL['E'] / (2 * (1 + STEEL['nu']))
cases = [("acier 0,8 mm (reference)", None), ("carbone QI", 1.0),
         ("hybride carbone/aramide 50/50 QI", 0.5), ("aramide QI", 0.0)]

PLY = 0.25   # epaisseur de pli cuit, prepreg tisse, mm — valeur de travail ASSUMED
print(f"{'materiau':<34}{'E':>8}{'G':>8}{'t iso-K':>9}{'plis':>6}{'K calc':>9}"
      f"{'vM p99':>8}{'kg/m2':>8}{'vs acier':>10}")
ref_areal = areal_mass(REF_T, STEEL['rho'])
rows = []
for name, f in cases:
    if f is None:
        E, nu, rho, G = STEEL['E'], STEEL['nu'], STEEL['rho'], G_steel
        t = REF_T
    else:
        m = hybrid(f)
        E, nu, rho, G = m['E'], m['nu'], m['rho'], m['G']
        t = REF_T * G_steel / G          # prediction iso-raideur, membrane en cisaillement
    K, vm99 = run(t, "study_ref" if f is None else f"study_c{int(f*100):03d}", E, nu)
    a = areal_mass(t, rho)
    plies = "-" if f is None else f"{int(np.ceil(t/PLY/4)*4)}"   # multiple de 4, stack QI
    rows.append((name, E, G, t, K, a, vm99))
    print(f"{name:<34}{E:8.0f}{G:8.0f}{t:9.2f}{plies:>6}{K:9.0f}{vm99:8.1f}{a:8.2f}"
          f"{a/ref_areal:9.2f}x")

print(f"\nControle : la prediction iso-raideur vise {REF_K:.0f} N.m/deg.")
err = max(abs(r[4] - REF_K) / REF_K for r in rows[1:])
print(f"Ecart maximal des cas composites au calcul complet : {err*100:.2f} %.")
print("Un ecart faible confirme que la raideur suit G*t et non G*t^3 : caisson en\n"
      "cisaillement de membrane, la loi d'echelle du README tient aussi en materiau.")

print("\nUtilisation : l'acier de reference plafonne a 86 MPa von Mises pour une limite\n"
      "d'elasticite d'au moins 200 MPa meme en acier doux. Le plancher n'est donc pas\n"
      "dimensionne par la contrainte en torsion mais par la raideur et par des criteres\n"
      "de fabrication, d'emboutissage et de tenue au choc local. Un echange de materiau\n"
      "a iso-raideur ne rend pas la marge en contrainte, il la deplace.")
