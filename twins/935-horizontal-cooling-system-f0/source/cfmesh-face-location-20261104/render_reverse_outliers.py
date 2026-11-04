from pathlib import Path
import hashlib
import json
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
base=Path('work/935-facet-provenance-20261028')
if (base/'reverse-outlier-points-20261104.npz').exists() or (base/'reverse-outliers-20261104.png').exists(): raise SystemExit('output exists')
for name, expected in [('broader-limit-0020.off','7d273b6072449c1e9140a995847fc4704990944fbb888d74a6a10a5a3db79091'), ('cfmesh-rotor17-20261104.obj','60f8564a87add660078b8609b09d6bfe6b8e439f146afe02ad6de91457b37f35')]:
    with (base/name).open('rb') as stream:
        h=hashlib.sha256()
        for block in iter(lambda:stream.read(1048576),b''): h.update(block)
    if h.hexdigest()!=expected: raise SystemExit('unexpected input hash')
source=trimesh.load_mesh(base/'broader-limit-0020.off',process=False)
wall=trimesh.load_mesh(base/'cfmesh-rotor17-20261104.obj',process=False)
ids=np.linspace(0,len(source.faces)-1,4096,dtype=int); points=source.vertices[source.faces[ids]].mean(axis=1)
nearest=[]; dist=[]
for i in range(0,len(points),32):
 q,d,_=trimesh.proximity.closest_point(wall,points[i:i+32]*.001); nearest.extend(q*1000); dist.extend(d*1000)
nearest=np.array(nearest); d=np.array(dist); flagged=d>.5
assert flagged.sum()==3 and abs(d.max()-.5870562247980166)<1e-10
np.savez_compressed(base/'reverse-outlier-points-20261104.npz',points=points[flagged],nearest=nearest[flagged],distances=d[flagged],face_ids=ids[flagged])
fig,axes=plt.subplots(1,3,figsize=(15,5),constrained_layout=True)
for ax,(x,y,title) in zip(axes,[(0,1,'XY'),(0,2,'XZ'),(1,2,'YZ')]):
 ax.scatter(points[:,x],points[:,y],s=1,c='#a2acb0',alpha=.5,label='Input face centres')
 ax.scatter(points[flagged,x],points[flagged,y],s=50,c='#cc3929',label='Distance > 0.5 source unit')
 for index, (a,b) in enumerate(zip(points[flagged],nearest[flagged]),1):
  ax.annotate(str(index),(a[x],a[y]),xytext=(5,5),textcoords='offset points')
 ax.set_aspect('equal'); ax.set_title(title); ax.set_xlabel('uncalibrated source units'); ax.set_ylabel('uncalibrated source units'); ax.grid(alpha=.2)
axes[0].legend(fontsize=7); fig.suptitle('935 rotor: three sampled input points with largest wall discrepancy\nTriangulated provisional cfMesh wall; scan scale and physical registration unverified'); fig.savefig(base/'reverse-outliers-20261104.png',dpi=180); plt.close(fig)
print(json.dumps({'outliers':int(flagged.sum()),'distances':d[flagged].tolist(),'minimum_pairwise_source_unit':float(min(np.linalg.norm(points[flagged][i]-points[flagged][j]) for i in range(3) for j in range(i+1,3)))}))
