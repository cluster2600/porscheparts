"""Locate weak tetrahedra of the rejected private Gmsh fluid volume."""
import hashlib,json
from pathlib import Path
import sys
import gmsh
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
mesh,output=map(lambda s:Path(s).resolve(),sys.argv[1:])
if output.exists():raise SystemExit('Output must be fresh')
if hashlib.sha256(mesh.read_bytes()).hexdigest()!='2a7346eb7696b67c59ffd23d791f1d8ddd82f69ab22f87986e1b1ac43b0006e7':raise SystemExit('Mesh hash mismatch')
output.mkdir(mode=0o700)
gmsh.initialize();gmsh.option.setNumber('General.Terminal',0);gmsh.open(str(mesh))
tags,coords,_=gmsh.model.mesh.getNodes();nodes=np.full((tags.max()+1,3),np.nan);nodes[tags]=coords.reshape(-1,3)
_,refs=gmsh.model.mesh.getElementsByType(4);cells=refs.reshape(-1,4)
rotor_nodes=np.unique(gmsh.model.mesh.getElementsByType(2,4)[1]);outer_nodes=np.unique(np.concatenate([gmsh.model.mesh.getElementsByType(2,i)[1] for i in (1,2,3)]))
weak_parts=[];weak_ids=[]
for start in range(0,len(cells),100000):
 end=min(start+100000,len(cells));x=nodes[cells[start:end]];a,b,c,d=np.moveaxis(x,1,0)
 six=np.einsum('ij,ij->i',b-a,np.cross(c-a,d-a))
 edge=sum(np.einsum('ij,ij->i',x[:,i]-x[:,j],x[:,i]-x[:,j]) for i,j in ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3)))
 ratio=12*(np.abs(six)/2)**(2/3)/edge
 selected=np.flatnonzero(ratio<.01)
 if len(selected):weak_parts.append(ratio[selected]);weak_ids.append(selected+start)
ids=np.concatenate(weak_ids);qualities=np.concatenate(weak_parts);weak=cells[ids];centre=nodes[weak].mean(axis=1)
touch_rotor=np.isin(weak,rotor_nodes).any(axis=1);touch_outer=np.isin(weak,outer_nodes).any(axis=1)
report={'status':'rejected_gmsh_weak_cell_localization_not_CFD','mesh_sha256':hashlib.sha256(mesh.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'weak_lt_0p01':len(ids),'touch_rotor':int(touch_rotor.sum()),'touch_outer':int(touch_outer.sum()),'touch_both':int((touch_rotor&touch_outer).sum()),'touch_neither':int((~(touch_rotor|touch_outer)).sum()),'centre_bounds_m':[centre.min(axis=0).tolist(),centre.max(axis=0).tolist()],'CFD_admitted':False}
np.savez_compressed(output/'weak-cells.npz',cell_ids=ids,mean_ratio=qualities,centres_m=centre,touch_rotor=touch_rotor,touch_outer=touch_outer)
(output/'localization.json').write_text(json.dumps(report,indent=2)+'\n')
rv=nodes[rotor_nodes];sample=rv[np.linspace(0,len(rv)-1,min(len(rv),30000),dtype=int)]
fig,axes=plt.subplots(1,2,figsize=(13,6))
for axis,ij,title in [(axes[0],(0,1),'Top: XY'),(axes[1],(0,2),'Side: XZ')]:
 axis.scatter(sample[:,ij[0]]*1000,sample[:,ij[1]]*1000,c='lightgray',s=.2,rasterized=True)
 axis.scatter(centre[:,ij[0]]*1000,centre[:,ij[1]]*1000,c=np.log10(qualities),cmap='viridis',s=7,rasterized=True)
 axis.set(xlabel='conditional mm',ylabel='conditional mm',title=title,aspect='equal')
fig.suptitle('935 corrected rotor: rejected Gmsh fluid cells with mean ratio < 0.01')
fig.tight_layout();fig.savefig(output/'weak-cells.png',dpi=160);plt.close(fig)
for p in output.iterdir():p.chmod(0o600)
print(json.dumps(report),flush=True)
gmsh.finalize()
