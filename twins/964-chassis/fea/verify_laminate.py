"""Validation de la chaine stratifiee sur un cas a reponse analytique connue.

Avant d'utiliser `run_fea_laminate.py` pour conclure quoi que ce soit, il faut
savoir s'il pose correctement les orientations. Le cas choisi est le plus
discriminant possible : traction uniaxiale sur un empilement UNIDIRECTIONNEL.

Le module apparent doit alors valoir exactement une constante connue du pli :

    0 degre   -> E1                                        135 000 MPa
    90 degres -> E2                                         10 000 MPa
    45 degres -> loi de transformation hors axe              13 200 MPa
                 1/Ex = c4/E1 + s4/E2 + (1/G12 - 2 nu12/E1) s2 c2

Un montage qui confondrait les axes, ou qui n'appliquerait pas l'angle de pli,
echouerait ici de facon spectaculaire — il rendrait 135 000 la ou on attend
10 000. C'est donc un vrai controle, pas une formalite.

Note sur un essai ecarte. Un panneau carre encastre sur un bord et charge dans
son plan sur le bord oppose avait d'abord ete pris pour du cisaillement pur. Il
n'en est pas : une console courte travaille aussi en flexion plane, dominee par
E, et le cas ne separe donc pas E de G. Pour separer les deux, voir
`dominance_study.py`, qui fait varier les modules independamment.

    pycad verify_laminate.py
"""
import gmsh, numpy as np, subprocess, os, sys, pathlib

L, LC, PLY_T, N_PLY = 1000.0, 80.0, 0.40, 8
UD = dict(E1=135000.0, E2=10000.0, E3=10000.0, nu12=0.30, nu13=0.30,
          nu23=0.40, G12=5000.0, G13=5000.0, G23=3500.0)
FX, T_TOT = 1000.0, PLY_T * N_PLY
SYS = '/home/maxime/work/964twin/syslibs/usr/lib/x86_64-linux-gnu'
CCX = '/home/maxime/work/964twin/syslibs/usr/bin/ccx'


def attendu(ang):
    """Module apparent hors axe d'un pli UD, loi de transformation classique."""
    c, s = np.cos(np.radians(ang)), np.sin(np.radians(ang))
    inv = (c**4 / UD['E1'] + s**4 / UD['E2']
           + (1.0 / UD['G12'] - 2 * UD['nu12'] / UD['E1']) * s**2 * c**2)
    return 1.0 / inv


gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.add("plate"); gmsh.model.occ.addRectangle(0, 0, 0, L, L)
gmsh.model.occ.synchronize()
gmsh.option.setNumber("Mesh.MeshSizeMin", LC); gmsh.option.setNumber("Mesh.MeshSizeMax", LC)
gmsh.model.mesh.generate(2); gmsh.model.mesh.setOrder(2)
nt, nc, _ = gmsh.model.mesh.getNodes(); nc = nc.reshape(-1, 3)
et, _, eN = gmsh.model.mesh.getElements(2)
cells = np.concatenate([eN[i].reshape(-1, 6) for i, t in enumerate(et) if t == 9])
gmsh.finalize()

left = nt[nc[:, 0] < 1e-6]
right = nt[nc[:, 0] > L - 1e-6]
corner = int(nt[np.argmin(nc[:, 0] ** 2 + nc[:, 1] ** 2)])


def Ex(ang):
    tag = f"vlam{'m' if ang < 0 else ''}{abs(int(ang)):02d}"
    with open(f'{tag}.inp', 'w') as f:
        f.write("*NODE, NSET=NALL\n")
        for n, p in zip(nt, nc):
            f.write(f"{int(n)}, {p[0]:.4f}, {p[1]:.4f}, {p[2]:.4f}\n")
        f.write("*ELEMENT, TYPE=S6, ELSET=SHELL\n")
        for i, e in enumerate(cells, 1):
            f.write(f"{i}, " + ", ".join(str(int(v)) for v in e) + "\n")
        f.write("*MATERIAL, NAME=UD\n*ELASTIC, TYPE=ENGINEERING CONSTANTS\n")
        f.write(f"{UD['E1']}, {UD['E2']}, {UD['E3']}, {UD['nu12']}, {UD['nu13']}, "
                f"{UD['nu23']}, {UD['G12']}, {UD['G13']}\n{UD['G23']}\n")
        c, s = np.cos(np.radians(ang)), np.sin(np.radians(ang))
        f.write("*ORIENTATION, NAME=OA\n")
        f.write(f"{c:.9f}, {s:.9f}, 0.0, {-s:.9f}, {c:.9f}, 0.0\n")
        f.write("*SHELL SECTION, COMPOSITE, ELSET=SHELL\n")
        for _ in range(N_PLY):
            f.write(f"{PLY_T}, , UD, OA\n")
        for nm, st in (('LEFT', left), ('RIGHT', right)):
            f.write(f"*NSET, NSET={nm}\n")
            ii = [str(int(x)) for x in st]
            for i in range(0, len(ii), 8):
                f.write(", ".join(ii[i:i + 8]) + "\n")
        f.write(f"*BOUNDARY\nLEFT, 1, 1\n{corner}, 2, 2\nNALL, 3, 3\n*STEP\n*STATIC\n")
        f.write(f"*CLOAD\nRIGHT, 1, {FX/len(right):.6f}\n*NODE FILE\nU\n*END STEP\n")
    for ext in ('.frd', '.dat', '.sta', '.cvg', '.12d'):
        pathlib.Path(tag + ext).unlink(missing_ok=True)
    env = dict(os.environ)
    env['LD_LIBRARY_PATH'] = f"{SYS}:{SYS}/lapack:{SYS}/blas:{SYS}/openmpi/lib"
    r = subprocess.run([CCX, '-i', tag], capture_output=True, text=True, env=env)
    if 'Job finished' not in r.stdout:
        print(r.stdout[-800:]); sys.exit(1)
    coord, ux, mode = {}, {}, None
    for line in open(f'{tag}.frd'):
        if '    2C' in line[:8]: mode = 'C'; continue
        if ' -4  DISP' in line: mode = 'U'; continue
        if line.startswith(' -3'): mode = None; continue
        if not line.startswith(' -1'): continue
        n = int(line[3:13])
        if mode == 'C':
            coord[n] = (float(line[13:25]), float(line[25:37]), float(line[37:49]))
        elif mode == 'U':
            ux[n] = float(line[13:25])
    sel = [n for n, p in coord.items() if p[0] > L - 1e-6]
    u = float(np.mean([ux[n] for n in sel]))
    return (FX / (L * T_TOT)) / (u / L)


print(f"Traction uniaxiale, pli UD, {N_PLY} plis x {PLY_T} mm\n")
print(f"{'angle':>6}{'E_x calcule':>13}{'E_x attendu':>13}{'ecart':>8}")
worst = 0.0
for a in (0, 90, 45):
    calc, att = Ex(a), attendu(a)
    err = abs(calc - att) / att
    worst = max(worst, err)
    print(f"{a:6d}{calc:13.0f}{att:13.0f}{err*100:7.1f}%")
print(f"\nEcart maximal {worst*100:.1f} %. "
      f"{'Chaine stratifiee VALIDE.' if worst < 0.05 else 'ECHEC : ne pas utiliser run_fea_laminate.py.'}")
if worst >= 0.05:
    sys.exit(1)
