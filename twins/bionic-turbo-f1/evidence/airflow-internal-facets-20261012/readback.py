"""Verify every native payload and re-read immutable geometry and topology."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from uniform_interface_projection import read_mesh,metrics
from audit_diagnostic import ascii_list
from frame_balance_batches import geometry
root=Path('work/bionic-airflow-20261012');base=root/'projected-interface-035';p0,f0,sel0,n0=read_mesh(base);result=[]
for name in ('internal-facets-040','star-partition-041'):
 case=root/name;r=json.loads((case/'report.json').read_text());m=json.loads((case/'manifest.json').read_text())
 assert r['native_exit_code']==0 and not r['mesh_gate_passed'] and not r['solver_launched'] and sha(case/'manifest.json')==r['manifest_sha256']
 assert all(sha(case/n)==h for n,h in r['output_sha256'].items())
 assert all(sha(case/n)==h for n,h in m['file_sha256'].items() if not n.startswith('constant/polyMesh/sets/'))
 p,faces,selected,internal=read_mesh(case);mesh=case/'constant/polyMesh';owner=ascii_list((mesh/'owner').read_text()).astype(int);nei=ascii_list((mesh/'neighbour').read_text()).astype(int)
 assert np.array_equal(p[:len(p0)],p0) and len(owner)==len(faces) and len(nei)==internal
 assert [list(f) for f in faces[internal:]]==[list(f) for f in f0[n0:]]
 assert {tuple(faces[i]) for i in selected}=={tuple(f0[i]) for i in sel0}
 boundary=0.;original=0.
 for points,ff,first in ((p,faces,internal),(p0,f0,n0)):
  groups={}
  for face in ff[first:]:groups.setdefault(len(face),[]).append(face)
  volume=0.
  for group in groups.values():
   c,s,_=geometry(points[np.asarray(group)]);volume+=float(np.einsum('ij,ij->',c,s))/3
  if first==internal:boundary=volume
  else:original=volume
 assert abs(boundary/original-1)<1e-12
 for prefix in ('0','system'):
  for path in (base/prefix).rglob('*'):
   if path.is_file():assert sha(path)==sha(case/path.relative_to(base))
 match=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',(mesh/'cellZones').read_text(),re.S);zone=np.fromstring(match[2],sep=' ',dtype=int);assert len(zone)==int(match[1]) and len(np.unique(zone))==len(zone)
 if name.endswith('041'):
  parents=np.load(case/'parent-cell-labels.npy',allow_pickle=False);old=ascii_list((base/'constant/polyMesh/cellZones').read_text()) if False else None
  match0=re.search(r'cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',(base/'constant/polyMesh/cellZones').read_text(),re.S);zone0=np.fromstring(match0[2],sep=' ',dtype=int)
  assert np.array_equal(zone,np.flatnonzero(np.isin(parents,zone0))) and len(parents)==max(owner.max(),nei.max())+1
  counts=np.bincount(parents);assert np.all(counts==8)
 result.append(dict(case=name,all_payloads_verified=True,receipt_sha256=sha(case/'report.json'),points=len(p),faces=len(faces),cells=int(max(owner.max(),nei.max()))+1,rotating_cells=len(zone),interface=metrics(p,[faces[i] for i in selected],10471.975511966),boundary_volume_m3=boundary,original_boundary_volume_m3=original,original_point_values_and_boundary_connectivity_identical=True,equations_and_initial_fields_identical=True,mesh_gate_passed=False,solver_launched=False))
report=dict(source_sha256=sha(Path(__file__)),results=result,physical_performance_validated=False)
with Path(__file__).with_name('readback.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report))
