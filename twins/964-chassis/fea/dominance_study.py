"""Cette caisse travaille-t-elle en cisaillement, ou en flexion ? Test direct.

Tout le dossier affirme « cisaillement de membrane, le critere est G ». Cette
affirmation reposait sur deux observations, et AUCUNE des deux ne la demontre :

  - la raideur suit lineairement l'epaisseur, et non son cube. Cela ecarte la
    flexion de PLAQUE, mais pas la flexion d'une POUTRE a paroi mince, dont
    l'inertie varie aussi lineairement avec l'epaisseur ;
  - la prediction iso-raideur en changeant de materiau tombe a 6,9 %. Mais tous
    les materiaux compares etaient ISOTROPES, ou G est proportionnel a E : ce
    controle ne peut pas, par construction, distinguer l'un de l'autre.

Le seul moyen de trancher est de faire varier E et G SEPAREMENT, ce qu'aucun
materiau isotrope ne permet. On utilise donc un materiau orthotrope fictif ou
les deux sont decouples — non physique, et c'est voulu : c'est un instrument de
mesure, pas un materiau.

  cas 1 : E, G          reference
  cas 2 : 2E, G         seule la raideur d'extension double
  cas 3 : E, 2G         seul le module de cisaillement double

Celui des deux qui deplace le plus la raideur en torsion nomme le mecanisme.

    pycad dominance_study.py [features]
"""
import numpy as np, subprocess, os, sys, pathlib

FEAT = sys.argv[1] if len(sys.argv) > 1 else "f"
E0, G0, T = 210000.0, 80769.0, 0.8      # acier de reference, E et G desormais independants
PY = sys.executable
CCX = '/home/maxime/work/964twin/syslibs/usr/bin/ccx'
SYS = '/home/maxime/work/964twin/syslibs/usr/lib/x86_64-linux-gnu'


def deck(tag, E, G, nid, xyz, cells):
    YS_I, SILL_W, SILL_H, Z0 = 600.0, 90.0, 120.0, 271.7
    X_F, X_R = float(xyz[:, 0].max()), float(xyz[:, 0].min())
    rear = nid[xyz[:, 0] < X_R + 8]
    band = (xyz[:, 0] > X_F - 8) & (xyz[:, 2] < Z0 + SILL_H + 1)
    frL = nid[band & (xyz[:, 1] > YS_I - 1)]
    frR = nid[band & (xyz[:, 1] < -YS_I + 1)]
    nu = 0.30
    with open(f'{tag}.inp', 'w') as f:
        f.write("*NODE, NSET=NALL\n")
        for n, p in zip(nid, xyz):
            f.write(f"{int(n)}, {p[0]:.4f}, {p[1]:.4f}, {p[2]:.4f}\n")
        f.write("*ELEMENT, TYPE=S6, ELSET=SHELL\n")
        for i, e in enumerate(cells, 1):
            f.write(f"{i}, " + ", ".join(str(int(v)) for v in e) + "\n")
        # Materiau orthotrope a E et G decouples. Isotrope en extension
        # (E1 = E2 = E3), mais son G est impose independamment.
        f.write("*MATERIAL, NAME=MAT\n*ELASTIC, TYPE=ENGINEERING CONSTANTS\n")
        f.write(f"{E}, {E}, {E}, {nu}, {nu}, {nu}, {G}, {G}\n{G}\n")
        f.write(f"*SHELL SECTION, ELSET=SHELL, MATERIAL=MAT\n{T}\n")
        for nm, st in (('REAR', rear), ('FRL', frL), ('FRR', frR)):
            f.write(f"*NSET, NSET={nm}\n")
            ii = [str(int(x)) for x in st]
            for i in range(0, len(ii), 8):
                f.write(", ".join(ii[i:i + 8]) + "\n")
        f.write("*BOUNDARY\nREAR, 1, 6\n*STEP\n*STATIC\n")
        f.write(f"*CLOAD\nFRL, 3, {1000.0/len(frL):.6f}\nFRR, 3, {-1000.0/len(frR):.6f}\n")
        f.write("*NODE FILE\nU\n*END STEP\n")
    return frL, frR


def run(tag, E, G):
    d = np.load('mesh.npz')
    nid, xyz = d['nid'], d['xyz']
    cells = d['cells']
    deck(tag, E, G, nid, xyz, cells)
    for ext in ('.frd', '.dat', '.sta', '.cvg', '.12d'):
        pathlib.Path(tag + ext).unlink(missing_ok=True)
    env = dict(os.environ)
    env['LD_LIBRARY_PATH'] = f"{SYS}:{SYS}/lapack:{SYS}/blas:{SYS}/openmpi/lib"
    env.setdefault('OMP_NUM_THREADS', '4')
    r = subprocess.run([CCX, '-i', tag], capture_output=True, text=True, env=env)
    if 'Job finished' not in r.stdout:
        print(r.stdout[-900:]); sys.exit(1)
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
    X_F = max(p[0] for p in coord.values())
    gL = [n for n, p in coord.items() if p[0] > X_F - 8 and p[2] < 271.7 + 120 + 2 and p[1] > 599]
    gR = [n for n, p in coord.items() if p[0] > X_F - 8 and p[2] < 271.7 + 120 + 2 and p[1] < -599]
    zl = np.mean([uz[n] for n in gL]); zr = np.mean([uz[n] for n in gR])
    ARM = 2 * (600.0 + 45.0)
    theta = np.degrees(np.arctan((zl - zr) / ARM))
    return 1000.0 * ARM / 1000.0 / theta


subprocess.run([PY, 'build_body.py', str(T), FEAT, '1.0', '2'], capture_output=True, check=True)
print(f"Architecture '{FEAT}', coques S6, epaisseur {T} mm\n")
print(f"{'cas':<16}{'E (MPa)':>10}{'G (MPa)':>10}{'K N.m/deg':>12}{'K/K_ref':>10}")
K = {}
for name, E, G in (("reference", E0, G0), ("E double", 2 * E0, G0), ("G double", E0, 2 * G0)):
    K[name] = run(f"dom_{name.split()[0]}", E, G)
    print(f"{name:<16}{E:10.0f}{G:10.0f}{K[name]:12.0f}{K[name]/K['reference']:10.3f}")

sE = K["E double"] / K["reference"] - 1.0
sG = K["G double"] / K["reference"] - 1.0
print(f"""
Sensibilite au doublement : E -> {sE*100:+.1f} %   G -> {sG*100:+.1f} %

Lecture. Pour une structure en cisaillement de membrane pur, doubler G doublerait
la raideur et doubler E ne changerait rien. Pour une poutre en flexion pure,
l'inverse. La part de chacun se lit directement ci-dessus.""")
