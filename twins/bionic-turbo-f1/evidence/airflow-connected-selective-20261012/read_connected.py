"""Independent motion, topology, target and frame-geometry readback."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from uniform_interface_projection import read_mesh,metrics
from audit_diagnostic import ascii_list
from frame_balance_batches import geometry
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');parent=root/'full-collar-063';p,f,interface,internal=read_mesh(parent)
manifest=json.loads((w/'connected-initial-073-inputs/manifest.json').read_text());outer=np.array(manifest['outer_point_labels']);fixed=np.array(manifest['protected_point_labels']);mid=np.unique(np.concatenate([f[i] for i in interface]));boundary=np.unique(np.concatenate(f[internal:]));initial=ascii_list((w/'connected-initial-073-inputs/constant/polyMesh/points').read_text(),True)
assert len(outer)==6912 and len(fixed)==14080 and len(mid)==6912
expected=p.copy();ratio=1.01415140625;expected[outer,:2]*=(1+(ratio-1)*7/8)/ratio;assert np.array_equal(initial,expected)
zone_text=(parent/'constant/polyMesh/cellZones').read_text();match=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',zone_text,re.S);assert match
zone=np.fromstring(match[2],sep=' ',dtype=int);assert len(zone)==20352
results={};omega=10471.975511966
for name in ('connected-initial-073','connected-snap-074'):
 case=root/name;r=json.loads((case/'report.json').read_text());assert r['native_exit_code']==0 and not r['container_state']['OOMKilled']
 assert all(sha(case/n)==h for n,h in r['output_sha256'].items())
 original=w/(name+'-inputs');m=json.loads((original/'manifest.json').read_text());assert all(sha(original/n)==h for n,h in m['file_sha256'].items())
 q,g,ii,nn=read_mesh(case);assert np.array_equal(ii,interface) and nn==internal and len(g)==len(f) and all(np.array_equal(a,b) for a,b in zip(f,g))
 for field in ('owner','neighbour'):assert np.array_equal(ascii_list((case/'constant/polyMesh'/field).read_text()),ascii_list((parent/'constant/polyMesh'/field).read_text()))
 zmatch=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',(case/'constant/polyMesh/cellZones').read_text(),re.S);assert zmatch and np.array_equal(zone,np.fromstring(zmatch[2],sep=' ',dtype=int))
 cf=np.empty((len(g),3));sf=np.empty_like(cf);warp=np.empty(len(g))
 for size in sorted(set(map(len,g))):
  ids=np.array([i for i,v in enumerate(g) if len(v)==size]);cf[ids],sf[ids],warp[ids]=geometry(q[np.array([g[i] for i in ids])])
 frame=np.column_stack((-cf[:,1],cf[:,0],np.zeros(len(cf))))*omega;flux=np.einsum('ij,ij->i',frame,sf)
 owner=ascii_list((case/'constant/polyMesh/owner').read_text()).astype(int);neighbour=ascii_list((case/'constant/polyMesh/neighbour').read_text()).astype(int);net=np.zeros(int(max(owner.max(),neighbour.max())+1));np.add.at(net,owner,flux);np.add.at(net,neighbour,-flux[:internal])
 movement=np.linalg.norm(q-initial,axis=1);target=np.linalg.norm(q-p,axis=1)
 results[name]=dict(mesh_gate_passed=r['mesh_gate_passed'],protected_motion_max_m=float(movement[fixed].max()),outer_motion_max_m=float(movement[outer].max()),outer_motion_min_m=float(movement[outer].min()),outer_target_vertex_error_max_m=float(target[outer].max()),mrf_motion_max_m=float(movement[mid].max()),mrf=metrics(q,[g[i] for i in interface],omega),all_face_warp_max_m=float(warp.max()),rotating_cell_frame_balance_max_m3_s=float(abs(net[zone]).max()),join_preserved=bool(movement[fixed].max()<1e-16),topology_and_rotor_zone_preserved=True,solver_launched=False)
a=json.loads((w/'connected-initial-073-inputs/manifest.json').read_text())['file_sha256'];b=json.loads((w/'connected-snap-074-inputs/manifest.json').read_text())['file_sha256'];assert a==b
tri=[]
for face in f[internal:]:
 for j in range(1,len(face)-1):tri.extend(p[face[[0,j,j+1]]])
stl=(w/'connected-initial-073-inputs/constant/triSurface/walls.stl').read_text();vertices=np.array([[float(x) for x in l.split()[1:]] for l in stl.splitlines() if l.strip().startswith('vertex ')])
assert np.array_equal(vertices,np.array(tri))
res=dict(source_sha256=sha(Path(__file__)),parent_report_sha256=sha(parent/'report.json'),prepared_inputs_identical=True,target_vertices_exact=True,cases=results,performance_validated=False)
with (w/'readback.json').open('x') as out:json.dump(res,out,indent=2)
print(json.dumps(res,indent=2))
