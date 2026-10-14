"""Independent readback of pre-native inputs, target and paired difference."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');parent=root/'collar-split-065';m=parent/'constant/domain1/polyMesh'
r=json.loads((parent/'report.json').read_text());assert all(sha(parent/n)==h for n,h in r['output_sha256'].items())
p=ascii_list((m/'points').read_text(),True);faces=[np.array(f) for f in ascii_faces((m/'faces').read_text())]
a=w/'selective-initial-071-inputs';b=w/'selective-unshifted-072-inputs';ma=json.loads((a/'manifest.json').read_text());mb=json.loads((b/'manifest.json').read_text())
assert set(ma['file_sha256'])==set(mb['file_sha256'])
diff=[n for n in ma['file_sha256'] if sha(a/n)!=sha(b/n)];assert diff==['constant/polyMesh/points']
expected=p.copy();fixed=np.unique(np.concatenate(faces[20480:]));moving=np.setdiff1d(np.arange(len(p)),fixed);q=1.01415140625
expected[moving,:2]*=(1+(q-1)*7/8)/q
assert np.array_equal(ascii_list((a/'constant/polyMesh/points').read_text(),True),expected)
tri=[]
for f in faces[13440:]:
 for j in range(1,len(f)-1):tri.extend(p[f[[0,j,j+1]]])
actual=np.array([[float(x) for x in l.split()[1:]] for l in (a/'constant/triSurface/walls.stl').read_text().splitlines() if l.startswith('vertex ')])
assert np.array_equal(np.array(tri),actual)
for name in ('selective-initial-071','selective-unshifted-072'):
 case=root/name;initial=w/(name+'-inputs');manifest=json.loads((initial/'manifest.json').read_text())
 assert all(sha(initial/n)==h for n,h in manifest['file_sha256'].items())
 for n in ('points','faces','owner','neighbour','boundary','pointZones','cellZones','faceZones'):assert sha(initial/'constant/polyMesh'/n)==sha(case/'constant/polyMesh'/n)
 assert not (case/'log.snappyHexMesh').exists()
res=dict(source_sha256=sha(Path(__file__)),parent_report_sha256=sha(parent/'report.json'),only_prepared_file_change=diff,all_mesh_inputs_unchanged_by_check=True,target_vertices_exact=True,target_triangles=len(actual)//3,frozen_point_count=len(fixed),moving_point_count=len(moving),maximum_synthetic_offset_m=float(np.linalg.norm(expected-p,axis=1).max()),snap_executed=False,flow_solver_executed=False)
with (w/'paired-inputs.json').open('x') as f:json.dump(res,f,indent=2)
print(res)
