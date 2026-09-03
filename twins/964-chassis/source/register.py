import numpy as np, json
from scipy.spatial import cKDTree
V=np.load('verts_vehicle.npy'); ch=json.load(open('datum_chain.json'))
Yh={int(k):v for k,v in ch['Yh'].items()}; Xl={int(k):v for k,v in ch['X_local'].items()}
# underbody structure only (exclude wheels/ground noise), plan projection
sel=(V[:,2]>60)&(V[:,2]<420); P=V[sel][:,:2]
tree=cKDTree(P[np.random.default_rng(0).choice(len(P),min(900_000,len(P)),replace=False)])
pts=[(p,s) for p in Xl for s in (+1,-1)]
def resid(off):
    q=np.array([[Xl[p]+off, s*Yh[p]] for p,s in pts])
    d,_=tree.query(q,k=1,workers=-1)
    return d
offs=np.arange(-1400,200,2.0)
scores=np.array([np.sqrt((resid(o)**2).mean()) for o in offs])
best=offs[scores.argmin()]
print(f"best longitudinal registration offset: {best:+.1f} mm   (RMS {scores.min():.1f} mm)")
print(f"  runner-up spread: RMS at +-100mm = {scores[np.abs(offs-best)<=100].max():.1f} mm -> minimum is {'sharp' if scores[np.abs(offs-best)<=100].max()>scores.min()*1.6 else 'shallow'}")
d=resid(best)
print(f"\n{'point':<7}{'X_vehicle':>11}{'Y':>9}{'dist to structure':>20}")
names={20:'front final sect',3:'FA side member',5:'FA outer x-mbr',17:'jack front',18:'jack rear',19:'platform rear',12:'trans x-mbr',21:'engine mount'}
for i,(p,s) in enumerate(pts):
    if s>0: print(f"P{p:<6}{Xl[p]+best:>11.1f}{s*Yh[p]:>9.1f}{d[i]:>16.1f} mm   {names.get(p,'')}")
print(f"\nmean {d.mean():.1f} mm, median {np.median(d):.1f} mm, max {d.max():.1f} mm")
print(f"points landing within 40 mm of scanned structure: {(d<40).sum()}/{len(d)}")
np.save('reg_offset.npy', np.array([best]))
