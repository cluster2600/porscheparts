from pathlib import Path
import argparse,json,hashlib
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path('work/935-editable-fragments-20261104')
report=Path('work/935-hub-surfaces-20261006/hub-surfaces-20261006-001/hub-surfaces.json')
scan=Path('work/935-reconstruction-20261005/surfaces-002/rotor/axis-aligned.npz')
cone=root/'hub-patches-001/patch-01.stl'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
assert [sha(p) for p in (cone,report,scan)]==['00bf8340c979019bcd2a4df57760d9bbd31768c34725683990161cbaad3bcfd8','41ebfafdb38124e4b878baf6da3822893265ba3f25c3f2ea85b0b2daca383a37','452f76162d6148017299edd1563e4e06b933dd9fe105bee30c185f96d98cc247']
patch=next(x for x in json.loads(report.read_text())['patches'] if x['id']=='hub-patch-01')
with np.load(scan) as d: v=d['vertices']; faces=d['faces']
ids=np.array(patch['selected_face_indices']); sm=trimesh.Trimesh(vertices=v,faces=faces[ids],process=False)
cm=trimesh.load_mesh(cone,process=False)
pts=sm.triangles_center; area=sm.area_faces
_,dist,_=trimesh.proximity.closest_point(cm,pts)
assert np.isfinite(dist).all() and len(dist)==2963
order=np.argsort(dist); dd=dist[order]; aa=area[order]; cum=np.cumsum(aa)/sum(aa)
def wq(q): return float(dd[np.searchsorted(cum,q)])
out={'description':'selected scan triangle centroids to fitted cone triangle surface; weights are scan triangle areas','scan_face_count':len(dist),'weighted_median':wq(.5),'weighted_p95':wq(.95),'weighted_fraction_within_0p5':float(area[dist<=.5].sum()/area.sum()),'weighted_fraction_within_1p0':float(area[dist<=1].sum()/area.sum()),'maximum':float(dist.max()),'units':'uncalibrated source units','independent_validation':False,'whole_surface_bound':False,'manufacturing_authorized':False}
parser=argparse.ArgumentParser(description='Compare selected scan centroids to an open fitted cone.')
parser.add_argument('output',type=Path)
folder=parser.parse_args().output
private_root=Path('work').resolve()
if folder.exists() or not folder.resolve().is_relative_to(private_root):
 raise SystemExit('fresh private output required')
folder.mkdir(parents=True,exist_ok=False)
(folder/'receipt.json').write_text(json.dumps(out,indent=2)+'\n')
np.savez_compressed(folder/'private-scan-centroids.npz',points=pts,distances=dist,areas=area,face_ids=ids)
fig,axs=plt.subplots(1,2,figsize=(13,6),constrained_layout=True)
for ax,(x,y,label) in zip(axs,[(0,1,'XY'),(0,2,'XZ')]):
 sc=ax.scatter(pts[:,x],pts[:,y],c=dist,s=4,cmap='magma',vmin=0,vmax=3);ax.set_aspect('equal');ax.set_title(label);ax.set_xlabel('X — source units');ax.set_ylabel(('Y' if y==1 else 'Z')+' — source units')
fig.colorbar(sc,ax=axs,label='Centroid distance to cone, clipped at 3 source units')
fig.suptitle('Selected scan triangles to fitted cone — uncalibrated, same acquisition used for fit\nProjection of centroids; no whole-surface or manufacturing validation')
fig.savefig(folder/'scan-to-cone.png',dpi=150)
print(json.dumps(out,indent=2))
