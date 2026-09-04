"""Modele coque extensible de la caisse 964 : plancher seul -> caisson ferme.

Reprend la geometrie de `build_shell.py` sans la modifier, et permet d'y ajouter
les elements qui FERMENT le caisson : tablier avant, cloison arriere, tunnel
central. Le but n'est pas de modeliser une 964 — aucune de ces sections n'est
publiee — mais de repondre a une question relative : entre changer de materiau et
fermer la caisse, lequel rapporte le plus ?

Toutes les sections ajoutees sont ASSUMED. Voir README.md.

    pycad build_body.py <epaisseur_mm> <features>
    features : chaine parmi f (floor+sills+crossmembers), b (bulkheads), t (tunnel)
"""
import gmsh, numpy as np, sys

T = float(sys.argv[1]) if len(sys.argv) > 1 else 0.8
FEAT = sys.argv[2] if len(sys.argv) > 2 else "f"
LC = 1.0

X_F, X_R = 400.0, -1500.0
YS_I, SILL_W, SILL_H = 600.0, 90.0, 120.0
Z0 = 271.7
XM = {'front_floor': 21.3, 'seat_base': -506.0, 'trans': -1703.0}
XW, XH = 80.0, 70.0
H_BULK = 500.0            # hauteur de cloison, ASSUMED (niveau de ceinture de caisse)
TUN_W, TUN_H = 180.0, 120.0   # tunnel central, ASSUMED

gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.add("body"); occ = gmsh.model.occ


def rect(p1, p2, p3, p4):
    ts = [occ.addPoint(*p) for p in (p1, p2, p3, p4)]
    ls = [occ.addLine(ts[i], ts[(i + 1) % 4]) for i in range(4)]
    return occ.addPlaneSurface([occ.addCurveLoop(ls)])


S = {}
# --- f : plancher, longerons, traverses (identique a build_shell.py) ---
S['floor'] = [rect((X_R, -YS_I, Z0), (X_F, -YS_I, Z0), (X_F, YS_I, Z0), (X_R, YS_I, Z0))]
for nm, sgn in (('sill_L', 1), ('sill_R', -1)):
    yi, yo = sgn * YS_I, sgn * (YS_I + SILL_W)
    S[nm] = [rect((X_R, yi, Z0), (X_F, yi, Z0), (X_F, yo, Z0), (X_R, yo, Z0)),
             rect((X_R, yi, Z0 + SILL_H), (X_F, yi, Z0 + SILL_H), (X_F, yo, Z0 + SILL_H), (X_R, yo, Z0 + SILL_H)),
             rect((X_R, yi, Z0), (X_F, yi, Z0), (X_F, yi, Z0 + SILL_H), (X_R, yi, Z0 + SILL_H)),
             rect((X_R, yo, Z0), (X_F, yo, Z0), (X_F, yo, Z0 + SILL_H), (X_R, yo, Z0 + SILL_H))]
for nm, x in XM.items():
    a, b = x - XW / 2, x + XW / 2
    S[nm] = [rect((a, -YS_I, Z0 - XH), (b, -YS_I, Z0 - XH), (b, YS_I, Z0 - XH), (a, YS_I, Z0 - XH)),
             rect((a, -YS_I, Z0 - XH), (a, -YS_I, Z0), (a, YS_I, Z0), (a, YS_I, Z0 - XH)),
             rect((b, -YS_I, Z0 - XH), (b, -YS_I, Z0), (b, YS_I, Z0), (b, YS_I, Z0 - XH))]

# --- b : cloisons transversales, ce qui ferme le caisson en bout ---
if 'b' in FEAT:
    for nm, x in (('bulk_front', X_F), ('bulk_rear', X_R)):
        S[nm] = [rect((x, -YS_I, Z0), (x, YS_I, Z0), (x, YS_I, Z0 + H_BULK), (x, -YS_I, Z0 + H_BULK))]

# --- t : tunnel central, poutre fermee longitudinale ---
if 't' in FEAT:
    yl, yr = TUN_W / 2, -TUN_W / 2
    S['tunnel'] = [rect((X_R, yr, Z0 + TUN_H), (X_F, yr, Z0 + TUN_H), (X_F, yl, Z0 + TUN_H), (X_R, yl, Z0 + TUN_H)),
                   rect((X_R, yl, Z0), (X_F, yl, Z0), (X_F, yl, Z0 + TUN_H), (X_R, yl, Z0 + TUN_H)),
                   rect((X_R, yr, Z0), (X_F, yr, Z0), (X_F, yr, Z0 + TUN_H), (X_R, yr, Z0 + TUN_H))]

occ.synchronize(); occ.removeAllDuplicates(); occ.synchronize()
gmsh.option.setNumber("Mesh.MeshSizeMin", 25 * LC); gmsh.option.setNumber("Mesh.MeshSizeMax", 45 * LC)
gmsh.model.mesh.generate(2)
nt, nc, _ = gmsh.model.mesh.getNodes(); nc = nc.reshape(-1, 3)
et, eT, eN = gmsh.model.mesh.getElements(2)
tri = np.concatenate([eN[i].reshape(-1, 3) for i, t in enumerate(et) if t == 2]) if 2 in et else np.zeros((0, 3), int)

# aire totale de coque -> masse surfacique reelle du modele
idx = {int(n): i for i, n in enumerate(nt)}
P = nc[[idx[int(n)] for n in tri.ravel()]].reshape(-1, 3, 3)
area = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1).sum()

np.savez('mesh.npz', nid=nt, xyz=nc, tri=tri, quad=np.zeros((0, 4), int), T=T, area=area)
print(f"features '{FEAT}'  nodes {len(nt):,}  tri {len(tri):,}  t {T} mm  "
      f"aire {area/1e6:.3f} m2")
gmsh.finalize()
