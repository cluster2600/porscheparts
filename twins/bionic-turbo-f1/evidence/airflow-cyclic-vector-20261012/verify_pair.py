"""Verify identical inputs, all native centre components and diagnostic controls."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from cyclic_vector_trace import vtk_field
root=Path('work/bionic-airflow-20261012');a=root/'cyclic-vector-049';b=root/'cyclic-vector-050';x=json.loads((a/'manifest.json').read_text());y=json.loads((b/'manifest.json').read_text());assert x['file_sha256']==y['file_sha256'] and x['trace_absolute_tolerance_formula']==y['trace_absolute_tolerance_formula']
outputs=[]
for case in (a,b):
 report=json.loads((case/'report.json').read_text());assert report['native_exit_code']==0 and not report['solver_launched'] and all(sha(case/n)==h for n,h in report['output_sha256'].items())
 arrays={}
 for name in ('C','Cx','Cy','Cz'):
  text=(case/'0'/name).read_text();m=re.search(r'internalField\s+nonuniform\s+List<(?:vector|scalar)>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S);assert m and int(m[1])==12480
  values=np.fromstring(m[2].translate(str.maketrans('()','  ')),sep=' ');assert np.isfinite(values).all();arrays[name]=values.reshape(12480,-1)
 for k,name in enumerate(('Cx','Cy','Cz')):np.testing.assert_array_equal(arrays[name][:,0],arrays['C'][:,k])
 for j,patch in enumerate(('periodicLower','periodicUpper'),1):
  for folder in ('traces','ownerValues'):assert np.all(vtk_field(case/folder/patch/(patch+'_0.vtk'),'patchID',80)==j)
 outputs.append(dict(case=case.name,all_payloads_verified=True,native_centres_and_components_verified=True))
read=json.loads(Path(__file__).with_name('cyclic-vector-050-readback.json').read_text());assert read['manufactured_trace_passed']
for row in read['results']:
 if row['field'] in ('basisX','basisY','tagged'):assert row['identity_error']>100*row['tolerance'] and row['inverse_rotation_error']>100*row['tolerance']
commands=[json.loads((case/'execution.json').read_text())['command'] for case in (a,b)];assert commands[0].replace(' -ascii ',' ')==commands[1]
result=dict(source_sha256=sha(Path(__file__)),prepared_inputs_byte_identical=True,only_native_command_change='Remove -ascii from both VTK exports; binary Float32 output, same tolerance.',cases=outputs,identity_and_inverse_negative_controls_rejected=True,scope='Boundary interpolation trace only, not matrix-coupling convergence or flow stability.')
with Path(__file__).with_name('paired-readback.json').open('x') as out:json.dump(result,out,indent=2)
print(json.dumps(result))
