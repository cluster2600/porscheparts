import sys,re,json,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from audit_diagnostic import ascii_list
from run_case import ascii_faces
case=Path(sys.argv[1]); stamp=sys.argv[2]; hashes={}
def read(name):
 b=(case/name).read_bytes(); hashes[name]=hashlib.sha256(b).hexdigest(); return b.decode()
def field(name,vector=False):
 text=read(stamp+'/'+name)
 m=re.search(r'internalField\s+nonuniform List<(scalar|vector)>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S)
 assert m, name
 values=np.fromstring(m[3].translate(str.maketrans('()','  ')),sep=' ')
 assert len(values)==int(m[2])*(3 if vector else 1) and np.isfinite(values).all()
 return values.reshape(-1,3) if vector else values
T=field('T'); idx=int(T.argmin()); p=field('p'); U=field('U',True); rho=field('rho')
mesh='constant/polyMesh/'
owner=ascii_list(read(mesh+'owner')).astype(np.int64); neigh=ascii_list(read(mesh+'neighbour')).astype(np.int64)
ids=set(np.flatnonzero(owner==idx))|set(np.flatnonzero(neigh==idx))
assert len(ids)>=6
selected={i:f for i,f in enumerate(ascii_faces(read(mesh+'faces'))) if i in ids}
points=ascii_list(read(mesh+'points'),True)
vertices=points[np.unique(np.concatenate(list(selected.values())))]; lo=vertices.min(axis=0); hi=vertices.max(axis=0)
assert np.all(hi>lo)
patches={}
for name,body in re.findall(r'(\w+)\s*\{([^{}]*)\}',read(mesh+'boundary')):
 a=re.search(r'startFace\s+(\d+)',body); b=re.search(r'nFaces\s+(\d+)',body)
 if a and b:
  patch=[i for i in ids if int(a[1])<=i<int(a[1])+int(b[1])]
  if patch: patches[name]=[int(i) for i in patch]
speed=float(np.linalg.norm(U[idx]))
result={'case':case.name,'checkpoint':stamp,'cell':idx,'temperature_min_K':float(T[idx]),'temperature_percentiles_K':np.percentile(T,[0,.001,.01,.1,1,50,100]).tolist(),'cells_below_100K':int((T<100).sum()),'pressure_at_cold_cell_Pa':float(p[idx]),'density_at_cold_cell_kg_m3':float(rho[idx]),'velocity_at_cold_cell_m_s':U[idx].tolist(),'speed_m_s':speed,'total_temperature_kinematic_K':float(T[idx]+speed**2/(2*1004.675)),'center_m':((lo+hi)/2).tolist(),'extent_m':(hi-lo).tolist(),'boundary_faces':patches,'input_sha256':hashes,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'performance_ranking_authorized':False}
print(json.dumps(result,indent=2))
