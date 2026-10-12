"""Read native topology and independently verify boundary and cell closure."""
import json,re,sys
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from uniform_interface_projection import read_mesh,metrics
from audit_diagnostic import ascii_list
from frame_balance_batches import geometry
w=Path(__file__).parent;case=Path('work/bionic-airflow-20261012/inner-transition-060')
r=json.loads((case/'report.json').read_text());assert r['native_exit_code']==0 and r['mesh_gate_passed']
assert all(sha(case/n)==h for n,h in r['output_sha256'].items())
spec=json.loads((case/'construction.json').read_text());p,faces,interface,internal=read_mesh(case);mesh=case/'constant/polyMesh'
o=ascii_list((mesh/'owner').read_text()).astype(int);n=ascii_list((mesh/'neighbour').read_text()).astype(int);count=int(max(o.max(),n.max())+1)
distance,mapping=cKDTree(p).query(spec['vertices']);assert distance.max()<1e-16 and len(set(mapping))==len(p)==len(spec['vertices'])
def key(face):return tuple(sorted(set(map(int,face))))
assert Counter(key(mapping[f]) for f in spec['walls'])==Counter(key(f) for f in faces[internal:])
assert Counter(key(mapping[f]) for f in spec['expected_interface_faces'])==Counter(key(faces[i]) for i in interface)
assert count==spec['expected_cells']==5120 and all(len(faces[i])==4 for i in interface)
cf=np.empty((len(faces),3));sf=cf.copy();warp=np.empty(len(faces))
for width in sorted(set(map(len,faces))):
 ids=np.array([i for i,f in enumerate(faces) if len(f)==width]);c,s,d=geometry(p[np.array([faces[i] for i in ids])]);cf[ids]=c;sf[ids]=s;warp[ids]=d
cellfaces=[[] for _ in range(count)]
for i,c in enumerate(o):cellfaces[c].append((i,1))
for i,c in enumerate(n):cellfaces[c].append((i,-1))
for items in cellfaces:
 edges=Counter()
 for i,sign in items:
  face=list(faces[i][::sign])
  for a,b in zip(face,face[1:]+face[:1]):edges[a,b]+=1
 assert all(v==1 and edges[b,a]==1 for (a,b),v in edges.items())
volumes=np.einsum('ij,ij->i',cf,sf)/3
vol=np.bincount(o,weights=volumes,minlength=count)-np.bincount(n,weights=volumes[:internal],minlength=count)
flux=np.einsum('ij,ij->i',np.cross([0,0,10471.975511966],cf),sf)
net=np.bincount(o,weights=flux,minlength=count)-np.bincount(n,weights=flux[:internal],minlength=count)
zone=np.fromstring(re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*\d+\s*\((.*?)\)',(mesh/'cellZones').read_text(),re.S)[1],sep=' ',dtype=int)
assert len(zone)==3840 and vol.min()>0 and warp.max()<1e-12
# Analytic volume between two regular polygons, homothetic in z.
N=spec['sectors'];ri,_,ro=spec['radial_ratios'];area=(N*ro**2*np.sin(2*np.pi/N)-2*N*ri**2*np.sin(2*np.pi/(2*N)))/2
R0=.032;R1=.0324;expected=area*.001*(R0**2+R0*R1+R1**2)/3
assert abs(vol.sum()/expected-1)<1e-12
m=metrics(p,[faces[i] for i in interface],10471.975511966);assert m['max_normal_frame_speed_m_s']<1e-8 and abs(net).max()<1e-16
result=dict(reader_sha256=sha(Path(__file__)),all_payloads_verified=True,cells=count,rotating_cells=len(zone),points=len(p),faces=len(faces),boundary_faces=len(faces)-internal,interface=m,original_point_rounding_m=float(distance.max()),all_cell_edges_cancel=True,boundary_matches_constructed_domain=True,interface_matches_constructed_quads=True,minimum_cell_volume_m3=float(vol.min()),boundary_volume_m3=float(vol.sum()),analytic_volume_m3=float(expected),maximum_face_warp_m=float(warp.max()),max_all_cell_geometric_frame_flux_m3_s=float(abs(net).max()),max_rotating_cell_geometric_frame_flux_m3_s=float(abs(net[zone]).max()),synthetic_domain_distinct_from_038_056=True,native_mesh_admitted=True,rest_test_performed=False,performance_ranking_authorized=False)
with (w/'readback.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
