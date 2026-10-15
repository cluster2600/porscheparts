"""Read all native payloads, final fields and geometric cell balances after native end."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from uniform_interface_projection import read_mesh,metrics
from internal_face_facets import balance
from audit_diagnostic import ascii_list
case=Path(sys.argv[1]);receipt=json.loads((case/'report.json').read_text());manifest=json.loads((case/'manifest.json').read_text())
assert receipt['native_exit_code']==0 and sha(case/'manifest.json')==receipt['manifest_sha256'] and all(sha(case/n)==h for n,h in receipt['output_sha256'].items())
assert all(sha(case/n)==h for n,h in manifest['file_sha256'].items())
p,f,selected,internal=read_mesh(case);mesh=case/'constant/polyMesh';o=ascii_list((mesh/'owner').read_text()).astype(int);n=ascii_list((mesh/'neighbour').read_text()).astype(int)
m=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',(mesh/'cellZones').read_text(),re.S);zone=np.fromstring(m[2],sep=' ',dtype=int);assert len(zone)==int(m[1])
text=(case/'constant/MRFProperties').read_text();omega=float(re.search(r'omega\s+constant\s+([^;]+)',text)[1])
for key,value in (('axis',[0,0,1]),('origin',[0,0,0])):assert np.array_equal(np.fromstring(re.search(key+r'\s*\(([^()]*)\)',text)[1],sep=' '),value)
geometry,_=balance(p,f,o,n,omega,zone);result=dict(case=case.name,source_sha256=sha(Path(__file__)),receipt_sha256=sha(case/'report.json'),all_native_payloads_verified=True,geometry=geometry,interface=metrics(p,[f[i] for i in selected],omega),omega=omega,physical_performance_validated=False)
if receipt['solver_launched']:
 assert receipt['native_end'];fields={}
 for name,components in (('p',1),('T',1),('U',3)):
  path=case/'2e-05'/name;text=path.read_text();match=re.search(r'internalField\s+nonuniform\s+List<(scalar|vector)>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S);assert match and int(match[2])==geometry['cells']
  a=np.fromstring(match[3].translate(str.maketrans('()','  ')),sep=' ');assert a.size==geometry['cells']*components and np.isfinite(a).all();a=a.reshape(-1,components)
  fields[name]=dict(sha256=sha(path),cells=len(a),minimum=a.min(axis=0).tolist(),maximum=a.max(axis=0).tolist(),max_magnitude=float(np.linalg.norm(a,axis=1).max()))
 log=(case/'log.rhoPimpleFoam').read_text();co=[float(v) for v in re.findall(r'Courant Number mean: [^\n]*?max: ([^\s]+)',log)];assert co and np.isfinite(co).all()
 result.update(final_fields=fields,max_native_courant=max(co),courant_samples=len(co),pressure_iteration_cap_hits=log.count('No Iterations 1000'),observed=receipt['observed'],stationary_equilibrium_reproduced=receipt['stationary_equilibrium_reproduced'])
with Path(__file__).with_name(case.name+'-readback.json').open('x') as out:json.dump(result,out,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='geometry'}))
