"""Essai de torsion sur stratifie reel : coque composite multicouche, CalculiX.

`run_fea.py` ne sait resoudre qu'un materiau isotrope. C'est suffisant pour
comparer des architectures, mais pas pour concevoir un drapage : un empilement
+/-45 n'est pas isotrope, et son coefficient de Poisson equivalent de 0,767 n'est
meme pas admissible pour un isotrope. La prediction « +/-45 rend 1,75 fois le
cisaillement d'un quasi-isotrope » ne pouvait donc pas etre verifiee.

Ce script la verifie. Il ecrit un jeu CalculiX a *SHELL SECTION, COMPOSITE :
plis empiles, chacun avec son epaisseur, son materiau orthotrope et son angle.

Orientation materiau. Un angle de pli n'a de sens que par rapport a une direction
locale. Les panneaux du modele sont dans trois plans, et une orientation globale
unique serait degeneree sur ceux qui sont normaux a son axe. Les elements sont
donc classes par leur normale et recoivent chacun une *ORIENTATION dont l'axe 1
est une direction reellement dans le plan du panneau — la direction vehicule X
partout ou elle y est, Y sinon.

    pycad run_fea_laminate.py <empilement> <tag> [epaisseur_pli_mm] [n_plis]
    empilement : QI | PM45 | X0_90

Meme maillage, memes conditions aux limites et meme chargement que run_fea.py.
"""
import numpy as np, subprocess, os, sys, pathlib

STACK = sys.argv[1] if len(sys.argv) > 1 else "QI"
tag = sys.argv[2] if len(sys.argv) > 2 else "lam"
PLY_T = float(sys.argv[3]) if len(sys.argv) > 3 else 0.40    # mm, ASSUMED
N_PLY = int(sys.argv[4]) if len(sys.argv) > 4 else 8

# Empilements symetriques, meme nombre de plis donc meme masse.
SEQ = {
    "QI":    [0, 45, -45, 90, 90, -45, 45, 0],       # quasi-isotrope
    "PM45":  [45, -45, 45, -45, -45, 45, -45, 45],   # angle-ply +/-45
    "X0_90": [0, 90, 0, 90, 90, 0, 90, 0],           # croise 0/90
}
if STACK not in SEQ:
    sys.exit(f"empilement inconnu : {STACK}. Choix : {', '.join(SEQ)}")
seq = (SEQ[STACK] * ((N_PLY // 8) + 1))[:N_PLY]
T_TOT = PLY_T * N_PLY

# Pli UD carbone/epoxy. E1, E2, G12, nu12 sont ceux de laminate.py, donc la
# prediction analytique et ce calcul partent bien du meme materiau.
# nu23 et G23 sont ASSUMED : ils n'entrent pas dans le comportement membranaire
# mais CalculiX exige les neuf constantes.
UD = dict(E1=135000.0, E2=10000.0, E3=10000.0,
          nu12=0.30, nu13=0.30, nu23=0.40,
          G12=5000.0, G13=5000.0, G23=3500.0)

d = np.load('mesh.npz'); nid, xyz, tri = d['nid'], d['xyz'], d['tri']
cells = d['cells'] if 'cells' in d.files else tri
if cells.shape[1] != 6:
    sys.exit("maillage d'ordre 1 : *SHELL SECTION, COMPOSITE exige des S6.\n"
             "Reconstruire avec  pycad build_body.py <t> <features> <lc> 2")
idx = {int(n): i for i, n in enumerate(nid)}
YS_I, SILL_W, SILL_H, Z0 = 600.0, 90.0, 120.0, 271.7
X_F, X_R = float(xyz[:, 0].max()), float(xyz[:, 0].min())
ARM = 2 * (YS_I + SILL_W / 2)
F = 1000.0

rear = nid[xyz[:, 0] < X_R + 8]
band = (xyz[:, 0] > X_F - 8) & (xyz[:, 2] < Z0 + SILL_H + 1)
frL = nid[band & (xyz[:, 1] > YS_I - 1)]
frR = nid[band & (xyz[:, 1] < -YS_I + 1)]

# --- classement des elements par normale -------------------------------------
P = xyz[[idx[int(n)] for n in tri.ravel()]].reshape(-1, 3, 3)
nrm = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
nrm /= np.linalg.norm(nrm, axis=1)[:, None]
axis = np.argmax(np.abs(nrm), axis=1)        # 0 = normale X, 1 = normale Y, 2 = normale Z

# Axe 1 du repere materiau : X vehicule si le panneau le contient, Y sinon.
# Un panneau de normale X (traverse, cloison) ne contient pas X : on prend Y.
ORIENT = {0: ((0., 1., 0.), (0., 0., 1.)),    # normale X -> axe1 = Y, axe2 = Z
          1: ((1., 0., 0.), (0., 0., 1.)),    # normale Y -> axe1 = X, axe2 = Z
          2: ((1., 0., 0.), (0., 1., 0.))}    # normale Z -> axe1 = X, axe2 = Y
GROUP = {0: 'GX', 1: 'GY', 2: 'GZ'}

with open(f'{tag}.inp', 'w') as f:
    f.write("*NODE, NSET=NALL\n")
    for n, p in zip(nid, xyz):
        f.write(f"{int(n)}, {p[0]:.4f}, {p[1]:.4f}, {p[2]:.4f}\n")
    f.write("*ELEMENT, TYPE=S6, ELSET=SHELL\n")
    for i, e in enumerate(cells, 1):
        f.write(f"{i}, " + ", ".join(str(int(v)) for v in e) + "\n")
    def block(kw, items):
        """Ecrit un set sans virgule terminale : une virgule en fin de derniere
        ligne est lue par CalculiX comme une continuation, et il avale alors le
        mot-cle suivant."""
        f.write(kw + "\n")
        items = [str(int(x)) for x in items]
        for i in range(0, len(items), 8):
            f.write(", ".join(items[i:i + 8]) + "\n")

    present = [a for a in (0, 1, 2) if (axis == a).sum()]
    for a in present:
        block(f"*ELSET, ELSET={GROUP[a]}", np.nonzero(axis == a)[0] + 1)
    f.write("*MATERIAL, NAME=UD\n*ELASTIC, TYPE=ENGINEERING CONSTANTS\n")
    f.write(f"{UD['E1']}, {UD['E2']}, {UD['E3']}, {UD['nu12']}, {UD['nu13']}, "
            f"{UD['nu23']}, {UD['G12']}, {UD['G13']}\n{UD['G23']}\n")
    # Dans CalculiX, le 4e champ d'une couche est un NOM D'ORIENTATION, pas un
    # angle. Un angle de pli se materialise donc par une orientation propre :
    # le repere du panneau tourne de cet angle autour de sa normale.
    def rot(e1, e2, deg):
        c, s_ = np.cos(np.radians(deg)), np.sin(np.radians(deg))
        return e1 * c + e2 * s_, -e1 * s_ + e2 * c

    def oname(a, ang):
        return f"O{GROUP[a]}{'M' if ang < 0 else 'P'}{abs(int(ang)):02d}"

    for a in present:
        e1 = np.array(ORIENT[a][0]); e2 = np.array(ORIENT[a][1])
        for ang in sorted(set(seq)):
            va, vb = rot(e1, e2, ang)
            f.write(f"*ORIENTATION, NAME={oname(a, ang)}\n")
            f.write(", ".join(f"{v:.9f}" for v in np.concatenate([va, vb])) + "\n")
    for a in present:
        f.write(f"*SHELL SECTION, COMPOSITE, ELSET={GROUP[a]}\n")
        for ang in seq:
            f.write(f"{PLY_T}, , UD, {oname(a, ang)}\n")
    for nm, st in (('REAR', rear), ('FRL', frL), ('FRR', frR)):
        block(f"*NSET, NSET={nm}", st)
    f.write("*BOUNDARY\nREAR, 1, 6\n*STEP\n*STATIC\n")
    f.write(f"*CLOAD\nFRL, 3, {F/max(len(frL),1):.6f}\nFRR, 3, {-F/max(len(frR),1):.6f}\n")
    f.write("*NODE FILE, OUTPUT=2D\nU\n*END STEP\n")

for ext in ('.frd', '.dat', '.sta', '.cvg', '.12d'):
    pathlib.Path(tag + ext).unlink(missing_ok=True)
env = dict(os.environ)
S = '/home/maxime/work/964twin/syslibs/usr/lib/x86_64-linux-gnu'
env['LD_LIBRARY_PATH'] = f"{S}:{S}/lapack:{S}/blas:{S}/openmpi/lib"
env.setdefault('OMP_NUM_THREADS', '4')
r = subprocess.run(['/home/maxime/work/964twin/syslibs/usr/bin/ccx', '-i', tag],
                   capture_output=True, text=True, env=env, cwd='.')
if 'Job finished' not in r.stdout:
    print(r.stdout[-1500:], r.stderr[-500:]); sys.exit(1)

# CalculiX developpe une coque composite en solide 3D et ignore OUTPUT=2D : le
# .frd porte le modele etendu, pas les noeuds d'origine. Les noeuds de mesure
# sont donc repris PAR LEUR GEOMETRIE dans le modele etendu, ce qui ne depend
# d'aucune correspondance de numerotation.
coord, uz, mode = {}, {}, None
for line in open(f'{tag}.frd'):
    if '    2C' in line[:8]: mode = 'C'; continue
    if ' -4  DISP' in line: mode = 'U'; continue
    if line.startswith(' -3'): mode = None; continue
    if not line.startswith(' -1'): continue
    n = int(line[3:13])
    if mode == 'C':
        coord[n] = (float(line[13:25]), float(line[25:37]), float(line[37:49]))
    elif mode == 'U':
        uz[n] = float(line[37:49])
if not coord or not uz:
    sys.exit(f"{tag}: .frd sans bloc de coordonnees ou sans deplacements")

tol = T_TOT / 2.0 + 1.0
sel = {n: p for n, p in coord.items()
       if p[0] > X_F - 8 and p[2] < Z0 + SILL_H + tol}
gL = [n for n, p in sel.items() if p[1] > YS_I - tol]
gR = [n for n, p in sel.items() if p[1] < -YS_I + tol]
missing = [n for n in gL + gR if n not in uz]
if not gL or not gR or missing:
    sys.exit(f"{tag}: selection geometrique vide ou incomplete "
             f"(gauche {len(gL)}, droite {len(gR)}, absents {len(missing)})")
zl = np.mean([uz[n] for n in gL]); zr = np.mean([uz[n] for n in gR])
theta = np.degrees(np.arctan((zl - zr) / ARM))
K = F * ARM / 1000.0 / theta
groups = {GROUP[a]: int((axis == a).sum()) for a in (0, 1, 2)}
print(f"{STACK:<6} {N_PLY} plis x {PLY_T} mm = {T_TOT:.2f} mm | twist {theta:7.4f} deg | "
      f"K = {K:8.0f} N.m/deg | noeuds mesure G{len(gL)} D{len(gR)}")
np.savez(f'{tag}_res.npz', K=K, theta=theta, stack=STACK, seq=seq, T=T_TOT)
