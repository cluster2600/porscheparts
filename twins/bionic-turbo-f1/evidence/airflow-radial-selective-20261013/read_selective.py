"""Reread topology, target provenance, motion and native geometric metrics."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from uniform_interface_projection import metrics
from frame_balance_batches import geometry
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');parent=root/'radial-isolated-079';split=root/'radial-split-078'
for c in (parent,split):
 r=json.loads((c/'report.json').read_text());assert all(sha(c/n)==h for n,h in r['output_sha256'].items())
m=parent/'constant/polyMesh';p=ascii_list((m/'points').read_text(),True);f=[np.array(x,int) for x in ascii_faces((m/'faces').read_text())];o=ascii_list((m/'owner').read_text()).astype(int);n=ascii_list((m/'neighbour').read_text()).astype(int);internal=len(n);cells=int(max(o.max(),n.max())+1)
assert all(len(x)==4 for x in f) and cells==13568
text=(split/'constant/domain1/polyMesh/boundary').read_text();join=re.search(r'domain1_to_rotorZone\s*\{(.*?)\}',text,re.S)[1];start=int(re.search(r'startFace\s+(\d+)',join)[1]);count=int(re.search(r'nFaces\s+(\d+)',join)[1]);joinfaces=f[start:start+count]
jp=np.unique(np.concatenate(joinfaces));boundary=np.unique(np.concatenate(f[internal:]));endfaces=[face for face in f[internal:] if np.all(p[face,2]==p[:,2].min()) or np.all(p[face,2]==p[:,2].max())];ends=np.unique(np.concatenate(endfaces));fixed=np.union1d(jp,ends);moving=np.setdiff1d(boundary,fixed);inside=np.setdiff1d(np.arange(len(p)),boundary)
assert len(jp)==6912 and len(ends)==768 and len(fixed)==7424 and len(moving)==6656 and len(inside)==6656
expected=p.copy();ratio=1.01415140625;expected[moving,:2]*=(1+(ratio-1)*7/8)/ratio
results={};manifests=[]
for name in ('radial-selective-initial-080','radial-selective-snap-081'):
 case=root/name;r=json.loads((case/'report.json').read_text());assert r['native_exit_code']==0 and not r['container_state']['OOMKilled'] and r['mesh_gate_passed']
 assert all(sha(case/k)==v for k,v in r['output_sha256'].items())
 initial=w/(name+'-inputs');manifest=json.loads((initial/'manifest.json').read_text());manifests.append(manifest['file_sha256']);assert all(sha(initial/k)==v for k,v in manifest['file_sha256'].items())
 assert np.array_equal(ascii_list((initial/'constant/polyMesh/points').read_text(),True),expected)
 assert np.array_equal(manifest['protected_point_labels'],fixed) and np.array_equal(manifest['moving_point_labels'],moving)
 mesh=case/'constant/polyMesh';q=ascii_list((mesh/'points').read_text(),True);g=[np.array(x,int) for x in ascii_faces((mesh/'faces').read_text())]
 assert len(g)==len(f) and all(np.array_equal(a,b) for a,b in zip(f,g))
 for field,labels in (('owner',o),('neighbour',n)):assert np.array_equal(ascii_list((mesh/field).read_text()).astype(int),labels)
 assert (mesh/'boundary').read_text().split('walls',1)[1].split('//',1)[0]==(m/'boundary').read_text().split('walls',1)[1].split('//',1)[0]
 assert 'rotorZone' not in (mesh/'cellZones').read_text()
 assert np.array_equal(q[fixed],p[fixed]) and np.array_equal(q[inside],p[inside])
 if name.endswith('080'):assert np.array_equal(q,expected)
 c,s,warp=geometry(q[np.array(g)]);part=np.einsum('ij,ij->i',c,s)/3
 volume=np.bincount(o,weights=part,minlength=cells)-np.bincount(n,weights=part[:internal],minlength=cells);assert volume.min()>0
 move=np.linalg.norm(q-expected,axis=1);error=np.linalg.norm(q-p,axis=1)
 metric=metrics(q,joinfaces,10471.975511966);assert metric['max_normal_frame_speed_m_s']<1e-8
 results[name]=dict(mesh_admitted=True,points=len(q),faces=len(g),cells=cells,join_faces=count,end_faces=len(endfaces),fixed_points=len(fixed),moving_points=len(moving),interior_points=len(inside),join_and_ends_coordinates_exact=True,all_internal_points_unchanged=True,topology_and_boundary_metadata_preserved=True,join=metric,maximum_face_warp_m=float(warp.max()),boundary_volume_m3=float(volume.sum()),minimum_cell_volume_m3=float(volume.min()),outer_motion_max_m=float(move[moving].max()),outer_motion_min_m=float(move[moving].min()),outer_source_vertex_error_max_m=float(error[moving].max()),solver_launched=False)
assert manifests[0]==manifests[1]
tri=np.array([p[face[[0,j,j+1]]] for face in f[internal:] for j in (1,2)])
stl=(w/'radial-selective-initial-080-inputs/constant/triSurface/walls.stl').read_text();vertices=np.array([[float(x) for x in line.split()[1:]] for line in stl.splitlines() if line.startswith('vertex ')])
assert np.array_equal(vertices,tri.reshape(-1,3))
assert results['radial-selective-snap-081']['outer_motion_min_m']>0
result=dict(reader_sha256=sha(Path(__file__)),all_payloads_verified=True,prepared_inputs_identical=True,target_triangles_exact=len(tri),selection_reproduces_join_and_all_end_faces=True,initial_offset_fraction=1/8,initial_offset_max_m=float(np.linalg.norm(expected-p,axis=1).max()),cases=results,physical_turbo_geometry_present=False,performance_validated=False)
(w/'readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
