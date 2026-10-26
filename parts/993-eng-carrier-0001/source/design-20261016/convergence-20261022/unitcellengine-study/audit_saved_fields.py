"""Check complete saved fields, independent boundary work and byte identities."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

p=Path(sys.argv[1]);r=json.loads((p/'assessment.json').read_text());N=r['resolution']
assert r['status']=='independent_operator_energy_checks_passed' and not (p/'saved-field-audit.json').exists()
f=np.load(p/'fields.npz');s=np.load(p/'stress-all-ip.npy',mmap_mode='r')
assert f['xi'].shape==((N+1)**3,3,6) and f['physical_forces'].shape==f['xi'].shape and s.shape==(N**3,8,6,6)
perm=[0,1,2,3,5,4];C=np.array(r['effective_C_MPa'])[np.ix_(perm,perm)]
k,j,i=np.indices((N+1,)*3);xyz=np.column_stack([i.ravel(),j.ravel(),k.ravel()])/N
assert np.isfinite(f['xi']).all() and np.isfinite(f['physical_forces']).all()
rows=[]
for mode in range(6):
 H=np.zeros((3,3))
 if mode<3:H[mode,mode]=1
 else:
  a,b=[(0,1),(1,2),(0,2)][mode-3];H[a,b]=H[b,a]=.5
 u=xyz@H.T-f['xi'][:,:,mode];work=.5*float(np.sum(f['physical_forces'][:,:,mode]*u));macro=.5*C[mode,mode]
 error=abs(work-macro)/abs(macro);assert error<=1e-4
 rows.append(dict(mode=mode,physical_boundary_work=work,macro_energy=macro,relative_work_error=error))
mean=np.zeros((6,6))
for start in range(0,len(s),2048):
 chunk=s[start:start+2048];assert np.isfinite(chunk).all();mean+=chunk.sum(axis=(0,1))/(8*N**3)
error=float(np.linalg.norm(mean-C)/np.linalg.norm(C));assert error<=1e-10
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for b in iter(lambda:stream.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
files=[p/x for x in ['operator.py','mesh.npz','result.npz','fields.npz','stress-all-ip.npy','assessment.json','solve-record.json']]
report=dict(status='complete_saved_field_rosters_and_boundary_work_passed',resolution=N,physical_nodes=(N+1)**3,stress_points_per_case=N**3*8,actual_cases=6,cases=rows,saved_stress_average_relative_error=error,file_sha256={x.name:sha(x) for x in files},auditor_sha256=sha(Path(__file__)))
(p/'saved-field-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
