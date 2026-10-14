"""Re-read the two sector meshes before allowing a local rest witness."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from uniform_interface_projection import read_mesh
from audit_frame_interface import face_geometry
root=Path('work/bionic-airflow-20261012');results=[]
for number in (42,43):
 case=root/f'directed-sector-{number:03d}';r=json.loads((case/'report.json').read_text());m=json.loads((case/'manifest.json').read_text());assert r['native_exit_code']==0 and sha(case/'manifest.json')==r['manifest_sha256']
 assert all(sha(case/n)==h for n,h in r['output_sha256'].items())
 p,f,sel,internal=read_mesh(case);volume=sum(float(np.dot(*face_geometry(p[face])))/3 for face in f[internal:]);results.append(dict(case=case.name,receipt_sha256=sha(case/'report.json'),boundary_volume_m3=volume,all_payloads_verified=True,mesh_gate_passed=r['mesh_gate_passed']))
 for prefix in ('0','system','constant'):
  for path in (case/prefix).rglob('*'):
   if path.is_file() and 'polyMesh' not in path.parts:assert sha(path)==sha(root/'projected-interface-035'/path.relative_to(case))
assert not results[0]['mesh_gate_passed'] and results[1]['mesh_gate_passed'];assert abs(results[0]['boundary_volume_m3']/results[1]['boundary_volume_m3']-1)<1e-12
with Path(__file__).with_name('pair-readback.json').open('x') as f:json.dump(dict(source_sha256=sha(Path(__file__)),results=results,equations_and_initial_fields_identical=True,physical_performance_validated=False),f,indent=2)
print(json.dumps(results))
