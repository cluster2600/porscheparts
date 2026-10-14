"""Read completed or budget-limited native witness without promoting partial rest."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from static_mrf_witness import assess
w=Path(__file__).parent;case=Path('work/bionic-airflow-20261012/coupled-equilibrium-084');r=json.loads((case/'report.json').read_text());m=json.loads((case/'manifest.json').read_text())
assert not r['container_state']['Running'] and not r['container_state']['OOMKilled'];assert sha(case/'manifest.json')==r['manifest_sha256'];assert all(sha(case/n)==h for n,h in r['output_sha256'].items());assert all(sha(case/n)==h for n,h in m['file_sha256'].items())
assert all(sha(w/'coupled-equilibrium-084-inputs'/n)==h for n,h in m['file_sha256'].items())
low=np.atleast_2d(np.loadtxt(case/'postProcessing/minima/0/volFieldValue.dat'));high=np.atleast_2d(np.loadtxt(case/'postProcessing/maxima/0/volFieldValue.dat'))
assert low.shape==high.shape and np.array_equal(low[:,0],high[:,0]) and np.isfinite(low).all() and np.isfinite(high).all();assert np.all(np.diff(low[:,0])>0)
partial=assess(low,high,m['criteria']);log=(case/'log.rhoPimpleFoam').read_text();co=np.array([float(x) for x in re.findall(r'Courant Number mean: [^\n]*?max: ([^\s]+)',log)]);assert np.isfinite(co).all()
mesh=case/'constant/polyMesh';o=ascii_list((mesh/'owner').read_text()).astype(int);n=ascii_list((mesh/'neighbour').read_text()).astype(int);cells=int(max(o.max(),n.max())+1);assert cells==33920 and len(n)==80768
finished=r['native_exit_code']==0 and r['native_end'] and len(low)==200 and abs(low[-1,0]-2e-5)<1e-15
if not finished:assert r['native_exit_code']==124 and not r['native_end']
fields={};times=sorted((float(p.name),p) for p in case.iterdir() if p.is_dir() and re.fullmatch(r'[0-9.eE+-]+',p.name) and float(p.name)>0)
for t,d in times:
 for name,components in (('p',1),('T',1),('U',3),('rho',1),('phi',1)):
  path=d/name;assert path.exists();s=path.read_text();mt=re.search(r'internalField\s+nonuniform\s+List<(scalar|vector)>\s+(\d+)\s*\((.*?)\)\s*;',s,re.S);count=len(n) if name=='phi' else cells;assert mt and int(mt[2])==count
  arr=np.fromstring(mt[3].translate(str.maketrans('()','  ')),sep=' ');assert arr.size==count*components and np.isfinite(arr).all();arr=arr.reshape(-1,components)
  if name in ('p','T','rho'):assert arr.min()>0
  fields[str(path.relative_to(case))]=dict(sha256=sha(path),values=count,minimum=arr.min(axis=0).tolist(),maximum=arr.max(axis=0).tolist(),max_magnitude=float(np.linalg.norm(arr,axis=1).max()))
if finished:assert any(abs(t-2e-5)<1e-15 for t,_ in times)
res=dict(reader_sha256=sha(Path(__file__)),receipt_sha256=sha(case/'report.json'),all_payloads_verified=True,initial_inputs_unchanged=True,native_exit_code=r['native_exit_code'],native_end=r['native_end'],elapsed_seconds=r['elapsed_seconds'],finished_target_duration=finished,samples=len(low),last_complete_history_time_s=float(low[-1,0]),observed_history=partial['observed'],history_thresholds_respected=partial['stationary_equilibrium_reproduced'],rest_20us_qualified=finished and partial['stationary_equilibrium_reproduced'],pressure_cap_hits=log.count('No Iterations 1000'),max_courant=float(co.max()),courant_samples=len(co),written_nonzero_time_directories=[t for t,_ in times],written_fields=fields,linear_convergence_qualified=False,physical_performance_validated=False,phi_scope='Relative mass flux, not physical turbo airflow.')
with (w/'readback.json').open('x') as f:json.dump(res,f,indent=2)
print(json.dumps(res))
