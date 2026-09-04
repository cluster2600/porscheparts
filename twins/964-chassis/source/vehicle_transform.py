"""Matrice 4x4 du repere vehicule, et sa verification bout en bout.

La fiche de jumeau ne decrivait le passage scan -> vehicule qu'en prose : « lacet
-2.236 deg, roulis -0.451 deg, axe median a X_scan +112.0 mm ». Utile a lire,
inutilisable par une machine. Ce script compose la matrice homogene equivalente
depuis `frame_params.npy`, la VERIFIE contre le resultat de `align.py`, et la
sort au format attendu par le champ `coordinate_system.vehicle_transform`.

La verification n'est pas cosmetique : elle attrape toute erreur de convention de
signe ou d'ordre de composition, qui sont ici la faute la plus facile a commettre
— la chaine enchaine une translation, deux rotations et une permutation d'axes.

    pymesh vehicle_transform.py
"""
import numpy as np, trimesh, json

yaw, x0, roll, fY, ground = np.load('frame_params.npy')
c, s = np.cos(-yaw), np.sin(-yaw)
cy, sy = np.cos(-roll), np.sin(-roll)

T1 = np.eye(4); T1[0, 3] = -x0                                    # recentrage lateral
Rz = np.eye(4); Rz[0, 0] = c;  Rz[0, 1] = -s; Rz[1, 0] = s;  Rz[1, 1] = c    # lacet
Ry = np.eye(4); Ry[0, 0] = cy; Ry[0, 2] = sy; Ry[2, 0] = -sy; Ry[2, 2] = cy  # roulis
P = np.zeros((4, 4)); P[3, 3] = 1                                 # axes ADR-0003
P[0, 1] = 1;  P[0, 3] = -fY        # X vehicule (avant)  =  y - fY
P[1, 0] = -1                       # Y vehicule (gauche) = -x
P[2, 2] = 1;  P[2, 3] = -ground    # Z vehicule (haut)   =  z - sol
M = P @ Ry @ Rz @ T1

np.set_printoptions(suppress=True, precision=6)
print("M, scan -> vehicule :\n", M)
R = M[:3, :3]
print(f"\ncontrole d'orthonormalite : |R.Rt - I| max = {np.abs(R @ R.T - np.eye(3)).max():.2e}"
      f"   det = {np.linalg.det(R):.9f}  (doit valoir 1)")

m = trimesh.load('raw/964widebodyunderside2poin13.obj', process=False)
Vs = np.asarray(m.vertices)
Vv = np.load('verts_vehicle.npy').astype(np.float64)
i = np.random.default_rng(0).choice(len(Vs), 200000, replace=False)
err = np.linalg.norm((M @ np.c_[Vs[i], np.ones(len(i))].T).T[:, :3] - Vv[i], axis=1)
print(f"\nverification sur {len(i):,} sommets : erreur max {err.max():.2e} mm, "
      f"moyenne {err.mean():.2e} mm")
assert err.max() < 1e-3, "la matrice ne reproduit pas align.py, ne pas publier"
print("-> conforme a align.py")
print("\nvehicle_transform :")
print(json.dumps([round(float(v), 6) for v in M.ravel()]))
