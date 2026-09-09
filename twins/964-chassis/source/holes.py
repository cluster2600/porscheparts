import numpy as np, trimesh, time
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components as cco
m = trimesh.load('raw/964widebodyunderside2poin13.obj', process=False)
V=np.load('verts_vehicle.npy'); F=m.faces
t=time.time()
E=np.sort(m.edges_sorted.reshape(-1,2),axis=1)
uniq,cnt=np.unique(E,axis=0,return_counts=True)
B=uniq[cnt==1]                      # boundary edges: belong to exactly one face
print(f"boundary edges: {len(B):,}  ({time.time()-t:.1f}s)")
nodes=np.unique(B)
remap=np.full(V.shape[0],-1); remap[nodes]=np.arange(len(nodes))
g=coo_matrix((np.ones(len(B)),(remap[B[:,0]],remap[B[:,1]])),shape=(len(nodes),)*2)
n,lab=cco(g,directed=False)
print(f"boundary loops: {n:,}")
# characterise each loop
cent=np.zeros((n,3)); diam=np.zeros(n); npts=np.zeros(n,int); circ=np.zeros(n)
P=V[nodes]
for i in range(n):
    sel=P[lab==i]; npts[i]=len(sel); cent[i]=sel.mean(0)
    d=sel-cent[i]; r=np.linalg.norm(d,axis=1)
    diam[i]=2*r.mean(); circ[i]=r.std()/max(r.mean(),1e-9)   # low = circular
np.savez('loops.npz',cent=cent,diam=diam,npts=npts,circ=circ)
print(f"\nloops with 8+ pts, diameter 10-80 mm, circularity<0.25 (hole-like):")
ok=(npts>=8)&(diam>10)&(diam<80)&(circ<0.25)
print(f"  {ok.sum()} candidates out of {n}")
c=cent[ok]; d=diam[ok]
order=np.argsort(-np.abs(c[:,1]))
for j in order[:40]:
    print(f"   X={c[j,0]:9.1f}  Y={c[j,1]:8.1f}  Z={c[j,2]:7.1f}  dia={d[j]:5.1f}")
