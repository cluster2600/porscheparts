"""Independent native coupled-vector trace readback and negative controls."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from uniform_interface_projection import read_mesh
from audit_diagnostic import ascii_list
from audit_frame_interface import face_geometry
from cyclic_vector_trace import vtk_field,expected_trace
case=Path(sys.argv[1]);r=json.loads((case/'report.json').read_text());assert r['native_exit_code']==0 and all(sha(case/n)==h for n,h in r['output_sha256'].items())
manifest=json.loads((case/'manifest.json').read_text());assert all(sha(case/n)==h for n,h in manifest['file_sha256'].items())
def field(name):
 text=(case/'0'/name).read_text();m=re.search(r'internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S);assert m
 a=np.fromstring(m[2].translate(str.maketrans('()','  ')),sep=' ').reshape(-1,3);assert len(a)==int(m[1]) and np.isfinite(a).all();return a
p,f,_,internal=read_mesh(case);owner=ascii_list((case/'constant/polyMesh/owner').read_text()).astype(int);centres=field('C');angle=2*np.pi/128;c,s=np.cos(angle),np.sin(angle);rotation=np.array([[c,-s,0],[s,c,0],[0,0,1]]);results=[]
for k,patch in enumerate(('periodicLower','periodicUpper')):
 ids=np.arange(internal+768+80*k,internal+848+80*k);other=np.arange(internal+768+80*(1-k),internal+848+80*(1-k));o=owner[ids];n=owner[other];rot=rotation.T if k==0 else rotation
 geometry=[face_geometry(p[f[i]]) for i in ids];fc=np.array([x[0] for x in geometry]);sf=np.array([x[1] for x in geometry]);unit=sf/np.linalg.norm(sf,axis=1)[:,None]
 for name in ('basisX','basisY','basisZ','tagged'):
  values=field(name);expected,w=expected_trace(centres[o],centres[n],fc,unit,values[o],values[n],rot)
  trace=vtk_field(case/'traces'/patch/(patch+'_0.vtk'),name,80);own=vtk_field(case/'ownerValues'/patch/(patch+'_0.vtk'),name,80)
  tol=float(8*np.finfo(np.float32).eps*max(1.,np.abs(expected).max()));error=float(np.abs(trace-expected).max());own_error=float(np.abs(own-values[o]).max())
  identity=w[:,None]*values[o]+(1-w[:,None])*values[n];inverse=w[:,None]*values[o]+(1-w[:,None])*(values[n]@rot)
  results.append(dict(patch=patch,field=name,max_trace_error=error,max_owner_error=own_error,tolerance=tol,passed=error<=tol and own_error<=tol,identity_error=float(np.abs(trace-identity).max()),inverse_rotation_error=float(np.abs(trace-inverse).max()),weight_min=float(w.min()),weight_max=float(w.max())))
result=dict(source_sha256=sha(Path(__file__)),helper_sha256=sha(Path('twins/bionic-turbo-f1/cfd/cyclic_vector_trace.py')),receipt_sha256=sha(case/'report.json'),all_payloads_verified=True,results=results,manufactured_trace_passed=all(x['passed'] for x in results),solver_launched=False,physical_performance_validated=False)
with Path(__file__).with_name(case.name+'-readback.json').open('x') as out:json.dump(result,out,indent=2)
print(json.dumps(result))
