"""Modele coque extensible de la caisse 964 : plancher seul -> caisse fermee.

Reprend la geometrie de `build_shell.py` sans la modifier, et permet d'y ajouter
les elements qui FERMENT le caisson. Le but n'est pas de modeliser une 964 —
aucune de ces sections n'est publiee — mais de repondre a des questions
RELATIVES : entre changer de materiau et fermer la caisse, lequel rapporte le
plus, et que rapporte chaque etage de la superstructure ?

Toutes les sections ajoutees sont ASSUMED. Voir README.md.

    pycad build_body.py <epaisseur_mm> <features> [finesse_maillage] [ordre]

    f  plancher, longerons, traverses          (identique a build_shell.py)
    b  tablier avant et cloison arriere         (le caisson est ferme en bout)
    t  tunnel central
    a  passages de roue                         (equerre sur les bouts de longeron)
    p  pieds milieu, brancards de pavillon, montant arriere
    r  pavillon
    w  cadre de pare-brise                      (montants A et traverse haute)

Dependances, verifiees au lancement : p exige b, r exige p, w exige p.
Le maillage est controle connexe avant d'etre ecrit : une piece flottante
donnerait un systeme singulier au solveur au lieu d'une erreur.
"""
import gmsh, numpy as np, sys, os

T = float(sys.argv[1]) if len(sys.argv) > 1 else 0.8
FEAT = sys.argv[2] if len(sys.argv) > 2 else "f"
LC = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0   # finesse de maillage
ORDER = int(sys.argv[4]) if len(sys.argv) > 4 else 1    # 1 = S3 lineaire, 2 = S6 quadratique
# L'ordre 2 n'est pas un raffinement : c'est une exigence de CalculiX, dont
# *SHELL SECTION, COMPOSITE n'accepte que des coques quadratiques S6 ou S8R.
# Un stratifie multicouche ne peut donc pas se calculer sur un maillage S3.

X_F, X_R = 400.0, -1500.0
YS_I, SILL_W, SILL_H = 600.0, 90.0, 120.0
Z0 = 271.7
# La traverse arriere du reseau de datums (P12, x = -1703) N'EST PAS ici. Elle
# tombe derriere le bord arriere du plancher modelise, donc derriere la section
# encastree de l'essai : elle ne peut porter aucun effort. Elle a longtemps
# figure dans ce dictionnaire, ou elle formait un ilot flottant — masse comptee,
# raideur nulle. Le controle de connexite de build_body.py interdit desormais
# qu'un tel ilot reparaisse sans etre signale.
XM = {'front_floor': 21.3, 'seat_base': -506.0}
XW, XH = 80.0, 70.0
H_BULK = 500.0            # hauteur de cloison, ASSUMED (niveau de ceinture de caisse)
TUN_W, TUN_H = 180.0, 120.0   # tunnel central, ASSUMED

# Les sections ASSUMED sont surchargeables par l'environnement, pour qu'un plan
# d'experiences puisse les balayer sans editer ce fichier. Sans surcharge, les
# valeurs ci-dessus sont inchangees et tous les resultats publies se rejouent.
_ov = lambda k, v: type(v)(os.environ[k]) if k in os.environ else v
SILL_W = _ov('BODY_SILL_W', SILL_W); SILL_H = _ov('BODY_SILL_H', SILL_H)
XW = _ov('BODY_XW', XW);             XH = _ov('BODY_XH', XH)
H_BULK = _ov('BODY_H_BULK', H_BULK)
TUN_W = _ov('BODY_TUN_W', TUN_W);    TUN_H = _ov('BODY_TUN_H', TUN_H)
Z_ROOF = Z0 + _ov('BODY_ROOF_H', 1150.0)
# --- superstructure, toutes cotes ASSUMED ---
X_HDR = -100.0            # station de la traverse haute de pare-brise
X_B = -900.0              # station des pieds milieu
RAIL_H = 80.0             # hauteur de brancard de pavillon et de traverse haute
ARCH_H, ARCH_L = 350.0, 450.0   # equerre de passage de roue sur le bout de longeron

DEPS = {'p': 'b', 'r': 'p', 'w': 'p'}
for feat, need in DEPS.items():
    if feat in FEAT and need not in FEAT:
        sys.exit(f"feature '{feat}' exige '{need}' : '{FEAT}' n'est pas constructible")

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

# --- a : passages de roue, equerre verticale sur le bout de chaque longeron ---
# Le passage de roue reel n'est pas publie. Ce qu'il fait en torsion l'est :
# il prolonge le longeron en hauteur a ses extremites. On modelise cet effet,
# pas la forme, par une equerre transversale + longitudinale posee sur le
# dessus du longeron, a chacun des quatre coins.
if 'a' in FEAT:
    ztop, zarch = Z0 + SILL_H, Z0 + SILL_H + ARCH_H
    for sgn, sname in ((1, 'L'), (-1, 'R')):
        yi, yo = sgn * YS_I, sgn * (YS_I + SILL_W)
        for xe, ename, inward in ((X_F, 'front', -1.0), (X_R, 'rear', 1.0)):
            xl = xe + inward * ARCH_L
            S[f'arch_{ename}_{sname}'] = [
                rect((xe, yi, ztop), (xe, yo, ztop), (xe, yo, zarch), (xe, yi, zarch)),
                rect((xe, yo, ztop), (xl, yo, ztop), (xl, yo, zarch), (xe, yo, zarch))]

# --- p : pieds milieu, brancards de pavillon, montant arriere ---
# Le pied milieu est pose sur la largeur du longeron, donc appuye sur toute sa
# section fermee et non sur une arete. Le brancard court de la traverse de
# pare-brise a la cloison arriere ; le montant arriere prolonge cette cloison
# jusqu'au pavillon, ce qui referme la cellule en haut a l'arriere.
if 'p' in FEAT:
    for sgn, sname in ((1, 'L'), (-1, 'R')):
        yi, yo = sgn * YS_I, sgn * (YS_I + SILL_W)
        S[f'pillar_B_{sname}'] = [rect((X_B, yi, Z0 + SILL_H), (X_B, yo, Z0 + SILL_H),
                                       (X_B, yo, Z_ROOF), (X_B, yi, Z_ROOF))]
        S[f'rail_{sname}'] = [rect((X_R, yi, Z_ROOF - RAIL_H), (X_HDR, yi, Z_ROOF - RAIL_H),
                                   (X_HDR, yi, Z_ROOF), (X_R, yi, Z_ROOF))]
    S['rear_upper'] = [rect((X_R, -YS_I, Z0 + H_BULK), (X_R, YS_I, Z0 + H_BULK),
                            (X_R, YS_I, Z_ROOF), (X_R, -YS_I, Z_ROOF))]

# --- r : pavillon ---
if 'r' in FEAT:
    S['roof'] = [rect((X_R, -YS_I, Z_ROOF), (X_HDR, -YS_I, Z_ROOF),
                      (X_HDR, YS_I, Z_ROOF), (X_R, YS_I, Z_ROOF))]

# --- w : cadre de pare-brise, montants A inclines + traverse haute ---
# Les montants A partent du haut du tablier et rejoignent la traverse : c'est
# le seul element du modele qui travaille en oblique.
if 'w' in FEAT:
    for sgn, sname in ((1, 'L'), (-1, 'R')):
        yi = sgn * YS_I
        S[f'pillar_A_{sname}'] = [rect((X_F, yi, Z0 + H_BULK - RAIL_H), (X_F, yi, Z0 + H_BULK),
                                       (X_HDR, yi, Z_ROOF), (X_HDR, yi, Z_ROOF - RAIL_H))]
    S['header'] = [rect((X_HDR, -YS_I, Z_ROOF - RAIL_H), (X_HDR, YS_I, Z_ROOF - RAIL_H),
                        (X_HDR, YS_I, Z_ROOF), (X_HDR, -YS_I, Z_ROOF))]

occ.synchronize(); occ.removeAllDuplicates(); occ.synchronize()
gmsh.option.setNumber("Mesh.MeshSizeMin", 25 * LC); gmsh.option.setNumber("Mesh.MeshSizeMax", 45 * LC)
gmsh.model.mesh.generate(2)
if ORDER == 2:
    gmsh.model.mesh.setOrder(2)
nt, nc, _ = gmsh.model.mesh.getNodes(); nc = nc.reshape(-1, 3)
et, eT, eN = gmsh.model.mesh.getElements(2)
TT, NPE = (9, 6) if ORDER == 2 else (2, 3)      # 9 = triangle quadratique a 6 noeuds
cells = (np.concatenate([eN[i].reshape(-1, NPE) for i, t in enumerate(et) if t == TT])
         if TT in et else np.zeros((0, NPE), int))
tri = cells[:, :3]                              # sommets : aire et connexite

# aire totale de coque -> masse surfacique reelle du modele
idx = {int(n): i for i, n in enumerate(nt)}
P = nc[[idx[int(n)] for n in tri.ravel()]].reshape(-1, 3, 3)
area = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1).sum()

# Controle de connexite. Un panneau colle par une arete que gmsh n'aurait pas
# imprimee resterait flottant : le solveur rendrait alors un systeme singulier ou
# une raideur fausse, pas une erreur. Ce controle echoue fermé a la place.
def n_components(tri, nnodes):
    parent = np.arange(nnodes)
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for e in tri:
        r = [find(v) for v in e]
        for x in r[1:]:
            if x != r[0]:
                parent[x] = r[0]
    return len({find(i) for i in np.unique(tri)})

ncomp = n_components(np.vectorize(idx.get)(tri), len(nt))
if ncomp != 1:
    sys.exit(f"maillage non connexe : {ncomp} composantes pour features '{FEAT}'")

np.savez('mesh.npz', nid=nt, xyz=nc, tri=tri, cells=cells, order=ORDER,
         quad=np.zeros((0, 4), int), T=T, area=area)
print(f"features '{FEAT}'  nodes {len(nt):,}  tri {len(tri):,}  t {T} mm  "
      f"aire {area/1e6:.3f} m2  ordre {ORDER}  connexe")
gmsh.finalize()
