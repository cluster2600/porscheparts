#!/usr/bin/env python3
"""Sample two fitted hub patches against aligned scan and candidate rotor."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import trimesh


def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()


def measure(mesh,points):
 values=[]
 for i in range(0,len(points),32):
  _,d,_=trimesh.proximity.closest_point(mesh,points[i:i+32]); values.extend(d)
 d=np.asarray(values)
 if not np.isfinite(d).all():raise ValueError('nonfinite distances')
 return {'count':len(d),'median':float(np.median(d)),'p95':float(np.percentile(d,95)),'max':float(d.max()),'over_1_source_unit':int(np.count_nonzero(d>1))}

p=argparse.ArgumentParser(description=__doc__);p.add_argument('patch0',type=Path);p.add_argument('patch1',type=Path);p.add_argument('scan',type=Path);p.add_argument('rotor',type=Path);p.add_argument('output',type=Path);a=p.parse_args();root=Path(__file__).resolve().parents[4]/'work'
if a.output.exists() or not a.output.resolve().is_relative_to(root.resolve()):raise SystemExit('fresh private work output required')
expected=('ec8f780d756e6068a1dbb90fc1ee85149989fa075efd3562d3b3abc411dcb9da','00bf8340c979019bcd2a4df57760d9bbd31768c34725683990161cbaad3bcfd8','452f76162d6148017299edd1563e4e06b933dd9fe105bee30c185f96d98cc247','20c63d8d2c13cfe906a4385ffc521881ec835d5dcd2dc646d295659b82bfb53c')
if tuple(sha(x) for x in (a.patch0,a.patch1,a.scan,a.rotor))!=expected:raise ValueError('input hash mismatch')
with np.load(a.scan) as d:scan=trimesh.Trimesh(vertices=d['vertices'],faces=d['faces'],process=False)
rotor=trimesh.load_mesh(a.rotor,process=False); rows=[]
for path in (a.patch0,a.patch1):
 mesh=trimesh.load_mesh(path,process=False); points=mesh.triangles.mean(axis=1)
 if not len(points) or not np.isfinite(points).all():raise ValueError('invalid hub patch')
 rows.append({'patch':path.stem,'triangles':len(points),'to_scan':measure(scan,points),'to_rotor_candidate':measure(rotor,points)})
result={'status':'sampled_patch_centroids_not_surface_or_fit_validation','input_sha256':expected,'unit':'uncalibrated_source_unit','patches':rows,'same_scan_as_fit':True,'physical_registration_verified':False,'scale_verified':False,'manufacturing_authorized':False}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
