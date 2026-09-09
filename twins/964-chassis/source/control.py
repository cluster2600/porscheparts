import numpy as np, json
from scipy.spatial import cKDTree
rng=np.random.default_rng(1)
V=np.load('verts_vehicle.npy')
sel=(V[:,2]>60)&(V[:,2]<420); P=V[sel][:,:2]
tree=cKDTree(P[rng.choice(len(P),min(900_000,len(P)),replace=False)])
# control: random points in the car's plan footprint
q=np.c_[rng.uniform(-3300,880,20000), rng.uniform(-880,880,20000)]
d,_=tree.query(q,k=1,workers=-1)
print("CONTROL - random points in the vehicle plan footprint:")
for t in (1,3,10,40):
    print(f"  within {t:>3} mm of structure: {100*(d<t).mean():5.1f} %")
print(f"  median distance: {np.median(d):.1f} mm")
print()
ch=json.load(open('datum_chain.json')); off=float(np.load('reg_offset.npy')[0])
Yh={int(k):v for k,v in ch['Yh'].items()}; Xl={int(k):v for k,v in ch['X_local'].items()}
qq=np.array([[Xl[p]+off,s*Yh[p]] for p in Xl for s in (1,-1)])
dd,_=tree.query(qq,k=1,workers=-1)
print(f"DATUM POINTS: median {np.median(dd):.1f} mm, all within {dd.max():.1f} mm")
print(f"probability a random point beats {dd.max():.1f} mm: {100*(d<dd.max()).mean():.1f} %")
print(f"-> chance of 16/16 random points doing so: {(d<dd.max()).mean()**16:.2e}")
