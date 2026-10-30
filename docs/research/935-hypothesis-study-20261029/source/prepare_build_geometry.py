"""Keep the closed fine surface and propose removable-support locations for review."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy import ndimage
import trimesh
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('frame',type=Path);p.add_argument('air_grid',type=Path);p.add_argument('output',type=Path)
a=p.parse_args();a.output.mkdir()
digest=hashlib.sha256(a.source.read_bytes()).hexdigest()
assert digest=='bcced05cf880809afc007b546f2f1ceba8fb5b71870ed8dd4fb6ea11bfdeb7aa'
d=np.load(a.source);v=d['vertices']@np.load(a.frame).T;f=d['triangles'];minimum=v.min(axis=0);offset=np.array([10.,10.,10.])-minimum;v=v+offset
mesh=trimesh.Trimesh(v,f,process=False)
mesh.export(a.output/'head-reference-aligned.stl')
grid=np.load(a.air_grid);outside=~grid['occupied'];seed=np.zeros_like(outside)
seed[[0,-1],:,:]=True;seed[:,[0,-1],:]=True;seed[:,:,[0,-1]]=True
air=ndimage.binary_propagation(seed&outside,mask=outside)
def accessible(pt):
    idx=np.floor((pt-offset-grid['origin'])/float(grid['pitch'])).astype(int)
    return bool((idx<0).any() or (idx>=air.shape).any() or air[tuple(idx)])
xs=np.arange(v[:,0].min()+2.137,v[:,0].max(),6.)
ys=np.arange(v[:,1].min()+2.419,v[:,1].max(),6.)
xy=np.array(np.meshgrid(xs,ys,indexing='ij')).reshape(2,-1).T
origins=np.column_stack([xy,np.full(len(xy),5.)]);directions=np.tile([0.,0.,1.],(len(xy),1))
loc,ray,face=mesh.ray.intersects_location(origins,directions,multiple_hits=True)
supports=[];odd_rays=0;inaccessible=0;short=0
for r in np.unique(ray):
    ids=np.flatnonzero(ray==r);ids=ids[np.argsort(loc[ids,2])]
    keep=np.r_[True,np.diff(loc[ids,2])>1e-4];ids=ids[keep]
    if len(ids)%2:odd_rays+=1;continue
    previous=5.
    for pair in range(0,len(ids),2):
        entry=ids[pair];z=float(loc[entry,2]);mid=np.array([*xy[r],(previous+z)/2])
        if z-previous<2:short+=1
        elif not accessible(mid):inaccessible+=1
        elif mesh.face_normals[face[entry],2]<-np.cos(np.pi/4):
            supports.append([float(xy[r,0]),float(xy[r,1]),previous-.25,z+.25])
        previous=float(loc[ids[pair+1],2])
assert supports
q={'source_sha256':digest,'transform':'ABC row-frame, then translation; no source face edits before STL float32 export','translation_after_ABC_mm':offset.tolist(),'source_triangle_count':len(f),'support_columns':supports,'support_grid_mm':6,'stem_radius_mm':1.2,'contact_tip_radius_mm':.5,'contact_overlap_mm':.25,'base_plate_mm':[float(v[:,0].max()+40),float(v[:,1].max()+10),5.],'coupon_centre_mm':[float(v[:,0].max()+20),20.,5.],'coupon_radius_mm':6.,'coupon_height_mm':20.,'odd_intersection_rays_rejected':odd_rays,'air_intervals_rejected_as_inaccessible':inaccessible,'short_intervals_skipped':short,'assumptions':['Entire scanned assembly is treated as a monolithic demonstrator; attached hardware not a separately qualified head design','Build orientation and support dimensions are provisional','Accessibility screen uses the 2 mm exterior-air grid; support removal is not physically validated','30 micron slicing does not restore detail finer than the 0.25 mm reconstruction voxel'],'manufacturing_qualified':False,'engine_qualified':False}
(a.output/'build-hypotheses.json').write_text(json.dumps(q,indent=2)+'\n')
print(json.dumps({k:q[k] for k in ['source_triangle_count','base_plate_mm','odd_intersection_rays_rejected','air_intervals_rejected_as_inaccessible']}));print('Support columns:',len(supports),flush=True)
