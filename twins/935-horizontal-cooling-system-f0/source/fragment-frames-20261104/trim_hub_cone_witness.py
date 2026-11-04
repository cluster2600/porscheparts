#!/usr/bin/env python3
"""Select fitted cone triangles by sampled proximity to the scan-fit subset."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import trimesh


def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()


def samples(t):
 a,b,c=t[:,0],t[:,1],t[:,2]
 return np.stack((a,b,c,(a+b)/2,(b+c)/2,(c+a)/2,(a+b+c)/3),axis=1)

p=argparse.ArgumentParser(description=__doc__);p.add_argument('cone',type=Path);p.add_argument('fit_report',type=Path);p.add_argument('scan',type=Path);p.add_argument('output',type=Path);p.add_argument('--subdivisions',type=int,choices=(0,1,2),default=0);a=p.parse_args();root=Path(__file__).resolve().parents[4]/'work'
if a.output.exists() or not a.output.resolve().is_relative_to(root.resolve()):raise SystemExit('fresh private output required')
expected=('00bf8340c979019bcd2a4df57760d9bbd31768c34725683990161cbaad3bcfd8','41ebfafdb38124e4b878baf6da3822893265ba3f25c3f2ea85b0b2daca383a37','452f76162d6148017299edd1563e4e06b933dd9fe105bee30c185f96d98cc247')
if tuple(sha(f) for f in (a.cone,a.fit_report,a.scan))!=expected:raise ValueError('input hash mismatch')
r=json.loads(a.fit_report.read_text());patches=[x for x in r['patches'] if x['id']=='hub-patch-01']
if len(patches)!=1 or r['scale_verified']:raise ValueError('unexpected evidence status')
ids=np.asarray(patches[0]['selected_face_indices'],dtype=np.int64)
with np.load(a.scan) as d:v=d['vertices'];f=d['faces']
if len(ids)!=2963 or len(np.unique(ids))!=len(ids) or ids.min()<0 or ids.max()>=len(f):raise ValueError('invalid scan selection')
selected=trimesh.Trimesh(vertices=v,faces=f[ids],process=False);cone=trimesh.load_mesh(a.cone,process=False);tri=cone.triangles
if tri.shape!=(654,3,3):raise ValueError('unexpected cone tessellation')
original_area=float(trimesh.triangles.area(tri).sum())
for _ in range(a.subdivisions):
 vertices,faces=trimesh.remesh.subdivide(tri.reshape(-1,3),np.arange(len(tri)*3).reshape(-1,3))
 tri=vertices[faces]
if not np.isclose(float(trimesh.triangles.area(tri).sum()),original_area,rtol=1e-12,atol=1e-12):raise ValueError('subdivision changed area')
query=samples(tri).reshape(-1,3); distances=[]
for i in range(0,len(query),64):
 _,d,_=trimesh.proximity.closest_point(selected,query[i:i+64]);distances.extend(d)
d=np.asarray(distances).reshape(len(tri),7)
if not np.isfinite(d).all():raise ValueError('invalid distance')
a.output.mkdir(mode=0o700,parents=True);np.savez_compressed(a.output/'private-sample-distances.npz',distances=d)
rows=[]
for threshold in (.5,1.):
 mask=(d<=threshold).all(axis=1);chosen=tri[mask]
 if not len(chosen):
  rows.append({'threshold_source_units':threshold,'selected_triangles':0,'total_triangles':len(mask),'selected_sample_max_source_units':None,'output_sha256':None,'file':None})
  continue
 out=a.output/('cone-witness-0p5.stl' if threshold==.5 else 'cone-witness-1p0.stl')
 mesh=trimesh.Trimesh(vertices=chosen.reshape(-1,3),faces=np.arange(len(chosen)*3).reshape(-1,3),process=False);mesh.export(out,file_type='stl');read=trimesh.load_mesh(out,process=False)
 if not np.array_equal(chosen.astype(np.float32),read.triangles.astype(np.float32)):raise ValueError('triangle readback changed')
 rows.append({'threshold_source_units':threshold,'selected_triangles':int(mask.sum()),'total_triangles':len(mask),'selected_sample_max_source_units':float(d[mask].max()),'output_sha256':sha(out),'file':out.name})
result={'status':'sample_selected_open_cone_witness_not_a_reconstruction_or_tolerance','input_sha256':expected,'subdivision_iterations':a.subdivisions,'samples_per_triangle':7,'scan_subset_faces':len(ids),'rows':rows,'source_units_calibrated':False,'physical_registration_verified':False,'complete_surface_bound':False,'manufacturing_authorized':False,'sample_distances_sha256':sha(a.output/'private-sample-distances.npz')}
(a.output/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
