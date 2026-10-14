"""Independent native readback of boundary permutation and rotating vector pairing."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from uniform_interface_projection import read_mesh,metrics
from audit_diagnostic import ascii_list
from internal_face_facets import balance
parent=Path('work/bionic-airflow-20261012/directed-sector-043');case=Path('work/bionic-airflow-20261012/periodic-sector-047')
r=json.loads((case/'report.json').read_text());assert r['mesh_gate_passed'] and all(sha(case/n)==h for n,h in r['output_sha256'].items())
p,f,interface,internal=read_mesh(parent);q,g,other,count=read_mesh(case);order=np.array(json.loads((case/'face-permutation.json').read_text()),int)
assert np.array_equal(p,q) and np.array_equal(interface,other) and internal==count and sorted(order)==list(range(len(f)))
assert all(np.array_equal(g[j],f[i]) for j,i in enumerate(order))
a=ascii_list((parent/'constant/polyMesh/owner').read_text()).astype(int);b=ascii_list((case/'constant/polyMesh/owner').read_text()).astype(int);assert np.array_equal(b,a[order])
for name in ('neighbour','cellZones','pointZones','faceZones'):assert sha(parent/'constant/polyMesh'/name)==sha(case/'constant/polyMesh'/name)
n=ascii_list((case/'constant/polyMesh/neighbour').read_text()).astype(int);text=(case/'constant/polyMesh/cellZones').read_text();m=re.search(r'cellLabels\s+List<label>\s+(\d+)\s*\((.*?)\)',text,re.S);zone=np.fromstring(m[2],sep=' ',dtype=int);assert len(zone)==int(m[1])
assert np.array_equal(np.sort(ascii_list((case/'constant/polyMesh/sets/nonOrthoFaces').read_text()).astype(int)),np.sort(np.argsort(order)[ascii_list((parent/'constant/polyMesh/sets/nonOrthoFaces').read_text()).astype(int)]))
angle=2*np.pi/128;c,s=np.cos(angle),np.sin(angle);rotation=np.array([[c,-s,0],[s,c,0],[0,0,1]]);errors=[]
for i in range(80):
 v=q[g[count+768+i]];w=q[g[count+848+i]];d=np.linalg.norm((v@rotation.T)[:,None]-w[None,:],axis=2);pair=d.argmin(axis=1);assert len(set(pair))==len(v)
 velocity=np.cross([0,0,10471.975511966],v);other_velocity=np.cross([0,0,10471.975511966],w[pair]);errors.append(float(np.linalg.norm(velocity@rotation.T-other_velocity,axis=1).max()))
assert max(errors)<1e-8
for name in ('system/controlDict','system/fvSchemes','system/fvSolution','constant/MRFProperties','constant/turbulenceProperties','constant/thermophysicalProperties'):assert sha(parent/name)==sha(case/name)
geometry,_=balance(q,g,b,n,10471.975511966,zone)
result=dict(source_sha256=sha(Path(__file__)),all_native_payloads_verified=True,points_faces_cells_preserved=True,owner_neighbour_zone_and_set_mapping_verified=True,original_walls_preserved=768,synthetic_wall_faces_replaced_by_cyclic=160,native_coupled_point_check='Coupled point location match (average 1.742144809353201e-17) OK.' in (case/'log.checkMesh').read_text(),max_analytic_rotated_vector_error_m_s=max(errors),geometry=geometry,interface=metrics(q,[g[i] for i in other],10471.975511966),scope='Different periodic local boundary problem. No real turbo patches modified. No flow yet.')
with Path(__file__).with_name('mesh-readback.json').open('x') as out:json.dump(result,out,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='geometry'}))
