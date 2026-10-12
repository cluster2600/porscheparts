"""Bound every native rear-wall face by the annulus certified on both STL surfaces."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'twins/bionic-turbo-f1/cfd')
from prepare_case import sha
from uniform_interface_projection import read_mesh
w=Path(__file__).parent;case=Path('work/bionic-airflow-20261012/full-collar-063')
proof_path=Path('work/bionic-collar-geometry-20261012/collar-062.json');proof=json.loads(proof_path.read_text())
spec=json.loads((case/'construction.json').read_text());assert sha(proof_path)==spec['collar_report_sha256']
p,faces,interface,internal=read_mesh(case);rear=[];bounds=[]
for i in range(internal,len(faces)):
 q=p[faces[i]]
 if np.all(q[:,2]==-.00375):
  xy=q[:,:2]*1000;d=np.roll(xy,-1,axis=0)-xy
  cross=xy[:,0]*np.roll(xy[:,1],-1)-xy[:,1]*np.roll(xy[:,0],-1)
  # Native quality and strict outward-facing polygon edges keep the origin outside these faces.
  assert not (np.all(cross>0) or np.all(cross<0))
  t=np.clip(-np.einsum('ij,ij->i',xy,d)/np.einsum('ij,ij->i',d,d),0,1)
  lo=float(np.linalg.norm(xy+t[:,None]*d,axis=1).min());hi=float(np.linalg.norm(xy,axis=1).max())
  for v in proof['variants'].values():
   annulus=v['annulus'];assert annulus['annulus_inner_radius_mm']<lo<=hi<annulus['annulus_outer_radius_mm']
  rear.append(i);bounds.append([lo,hi])
assert len(rear)==512
r=dict(source_sha256=sha(Path(__file__)),collar_report_sha256=sha(proof_path),rear_faces=rear,
       every_face_in_both_certified_stator_annuli=True,radial_bounds_mm=[min(v[0] for v in bounds),max(v[1] for v in bounds)],
       exact_native_plane_z_m=-.00375,other_walls_are_synthetic=True,performance_ranking_authorized=False)
with (w/'rear-patch-readback.json').open('x') as f:json.dump(r,f,indent=2)
print(json.dumps({k:v for k,v in r.items() if k!='rear_faces'}))
