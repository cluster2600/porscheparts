import numpy as np, trimesh
from scipy.spatial import cKDTree
from scipy.optimize import minimize
rng=np.random.default_rng(0)
m = trimesh.load('raw/964widebodyunderside2poin13.obj', process=False)
V = np.asarray(m.vertices)
# work on the structural underbody band (exclude tyres/flares extremes), downsample
band = (V[:,2] > -330) & (V[:,2] < 120)
P = V[band]
idx = rng.choice(len(P), size=min(250_000,len(P)), replace=False)
S = P[idx]
tree = cKDTree(P[rng.choice(len(P), size=min(600_000,len(P)), replace=False)])
print(f"points in band {len(P):,}  sample {len(S):,}")

def mirror(S, yaw, x0, roll):
    """reflect across plane through (x0,0,0) with normal rotated by yaw (about Z) and roll (about Y)."""
    n = np.array([np.cos(yaw)*np.cos(roll), np.sin(yaw), np.sin(roll)])
    n = n/np.linalg.norm(n)
    d = (S - np.array([x0,0,0])) @ n
    return S - 2*d[:,None]*n

def cost(p):
    Sm = mirror(S, p[0], p[1], p[2])
    dist,_ = tree.query(Sm, k=1, workers=-1)
    dist = np.sort(dist)[:int(0.85*len(dist))]      # trimmed: ignore asymmetric scan coverage
    return np.sqrt((dist**2).mean())

best=None
for x0 in (0,50,100,150):
    for yaw in (0,-0.02,-0.04,0.02):
        c=cost([yaw,x0,0.0])
        if best is None or c<best[0]: best=(c,[yaw,x0,0.0])
print(f"grid seed rms={best[0]:.2f} mm at yaw={best[1][0]:.4f} x0={best[1][1]:.1f}")
r = minimize(cost, best[1], method='Nelder-Mead',
             options=dict(xatol=1e-4, fatol=1e-3, maxiter=400))
yaw,x0,roll = r.x
print(f"\nSYMMETRY PLANE FIT")
print(f"  trimmed RMS mirror error : {r.fun:.2f} mm")
print(f"  yaw   : {np.degrees(yaw):+.3f} deg   (car rotated vs scan axes)")
print(f"  roll  : {np.degrees(roll):+.3f} deg")
print(f"  lateral offset x0 : {x0:+.1f} mm  (centreline position in scan X)")
np.save('sym_plane.npy', r.x)
