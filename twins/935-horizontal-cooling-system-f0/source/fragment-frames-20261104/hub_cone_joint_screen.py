#!/usr/bin/env python3
"""Cross-tabulate sampled hub-cone distances to scan and rotor candidate."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()


def measure(mesh,points):
 out=[]
 for i in range(0,len(points),32):
  _,d,_=trimesh.proximity.closest_point(mesh,points[i:i+32]);out.extend(d)
 return np.asarray(out)

p=argparse.ArgumentParser(description=__doc__);p.add_argument('cone',type=Path);p.add_argument('scan',type=Path);p.add_argument('rotor',type=Path);p.add_argument('output',type=Path);a=p.parse_args();root=Path(__file__).resolve().parents[4]/'work'
if a.output.exists() or not a.output.resolve().is_relative_to(root.resolve()):raise SystemExit('fresh private output required')
expected=('00bf8340c979019bcd2a4df57760d9bbd31768c34725683990161cbaad3bcfd8','452f76162d6148017299edd1563e4e06b933dd9fe105bee30c185f96d98cc247','20c63d8d2c13cfe906a4385ffc521881ec835d5dcd2dc646d295659b82bfb53c')
if tuple(sha(f) for f in (a.cone,a.scan,a.rotor))!=expected:raise ValueError('input hash mismatch')
cone=trimesh.load_mesh(a.cone,process=False); rotor=trimesh.load_mesh(a.rotor,process=False)
with np.load(a.scan) as d:scan=trimesh.Trimesh(vertices=d['vertices'],faces=d['faces'],process=False)
points=cone.triangles.mean(axis=1)
if points.shape!=(654,3):raise ValueError('unexpected tessellation')
ds,dr=measure(scan,points),measure(rotor,points)
if not np.isfinite(ds).all() or not np.isfinite(dr).all():raise ValueError('invalid distances')
near=ds<=.5; far=ds>1.; high=dr>1.
result={'status':'point_screen_not_observed_surface_classification','input_sha256':expected,'sample_count':len(points),'unit':'uncalibrated_source_unit','bins':{'near_scan_at_most_0p5_and_rotor_over_1':int(np.count_nonzero(near&high)),'far_scan_over_1_and_rotor_over_1':int(np.count_nonzero(far&high)),'middle_scan_over_0p5_at_most_1_and_rotor_over_1':int(np.count_nonzero((~near)&(~far)&high)),'rotor_over_1_total':int(high.sum()),'near_scan_total':int(near.sum()),'far_scan_total':int(far.sum())},'scale_verified':False,'physical_registration_verified':False,'manufacturing_authorized':False}
a.output.mkdir(mode=0o700,parents=True);np.savez_compressed(a.output/'private-points.npz',points=points,scan_distance=ds,rotor_distance=dr)
fig,axes=plt.subplots(1,2,figsize=(11,5),constrained_layout=True)
for ax,values,title in zip(axes,(ds,dr),('Distance to aligned scan','Distance to candidate rotor')):
 s=ax.scatter(points[:,0],points[:,1],c=values,s=12,cmap='inferno',vmin=0,vmax=3);ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('uncalibrated source unit');ax.set_ylabel('uncalibrated source unit');fig.colorbar(s,ax=ax,label='sample distance, source units')
fig.suptitle('935 fitted hub cone: sampled centroid distances\nSame scan used for fit; not surface provenance or verified scale');fig.savefig(a.output/'cone-joint-screen.png',dpi=180);plt.close(fig)
result['image_sha256']=sha(a.output/'cone-joint-screen.png');result['private_points_sha256']=sha(a.output/'private-points.npz');(a.output/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
