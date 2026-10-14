"""Reread paired snap outputs; immutability and mesh admission are separate."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from uniform_interface_projection import read_mesh,metrics
from audit_diagnostic import ascii_list
w=Path(__file__).parent;base=Path('work/bionic-airflow-20261012');parent=base/'full-collar-063'
p,f,interface,internal=read_mesh(parent);ids=np.unique(np.concatenate(f[internal:]));mid=np.unique(np.concatenate([f[i] for i in interface]));results={}
for name in ('snap-control-068','snap-frozen-069'):
 case=base/name;r=json.loads((case/'report.json').read_text());assert r['native_exit_code']==0 and not r['container_state']['OOMKilled']
 assert all(sha(case/n)==h for n,h in r['output_sha256'].items())
 q,g,faces2,internal2=read_mesh(case);assert q.shape==p.shape and internal2==internal and np.array_equal(interface,faces2)
 assert len(g)==len(f) and all(np.array_equal(a,b) for a,b in zip(f,g))
 for field in ('owner','neighbour'):
  assert np.array_equal(ascii_list((parent/'constant/polyMesh'/field).read_text()),ascii_list((case/'constant/polyMesh'/field).read_text()))
 distance=np.linalg.norm(q-p,axis=1);log=(case/'log.snappyHexMesh').read_text();assert all('Smoothing iteration '+str(i) in log for i in range(3))
 m=metrics(q,[g[i] for i in interface],10471.975511966)
 results[name]=dict(mesh_gate_passed=r['mesh_gate_passed'],all_payloads_verified=True,topology_labels_unchanged=True,maximum_point_motion_m=float(distance.max()),maximum_boundary_motion_m=float(distance[ids].max()),boundary_points_moved_above_1e_16=int(np.count_nonzero(distance[ids]>1e-16)),maximum_interface_motion_m=float(distance[mid].max()),interface=m,boundary_preservation_passed=bool(distance[ids].max()<1e-16),solver_launched=False)
a=json.loads((base/'snap-control-068/manifest.json').read_text())['file_sha256'];b=json.loads((base/'snap-frozen-069/manifest.json').read_text())['file_sha256'];assert a.keys()==b.keys()
differences=[n for n in a if a[n]!=b[n]];assert differences==['constant/polyMesh/pointZones']
result=dict(reader_sha256=sha(Path(__file__)),paired_prepared_differences=differences,cases=results,physical_turbo_modified=False)
with (w/'pair-readback.json').open('x') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result))
