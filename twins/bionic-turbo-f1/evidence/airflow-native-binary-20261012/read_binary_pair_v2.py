"""Verify native receipts, all final fields and exact executable-pair inputs."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha,IMAGE
from audit_diagnostic import ascii_list
w=Path(__file__).parent;base=Path('work/bionic-airflow-20261012')
cases=[base/name for name in ('binary-original-052','binary-rebuilt-053')]
source=json.loads((w/'source-audit.json').read_text());manifests=[];executions=[];outputs=[]
original_hash=re.search(r'^([a-f0-9]{64})  /usr/lib/openfoam/[^\n]+/bin/rhoPimpleFoam$',(w/'baseline-build-v6/compile.log').read_text(),re.M)[1]

def field_values(text,count):
    m=re.search(r'internalField\s+nonuniform\s+List<(scalar|vector)>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S)
    assert m and int(m[2])==count
    width=3 if m[1]=='vector' else 1
    a=np.fromstring(m[3].translate(str.maketrans('()','  ')),sep=' ')
    assert a.size==count*width and np.isfinite(a).all()
    return a.reshape(count,width)
assert field_values('internalField nonuniform List<scalar> 2 (1 2);',2).sum()==3
try:field_values('internalField nonuniform List<vector> 1 ((1 2));',1)
except AssertionError:pass
else:raise AssertionError('Truncated vector was accepted')
for case,expected_hash in zip(cases,(original_hash,source['compiled_binary_sha256'])):
    receipt=json.loads((case/'report.json').read_text());m=json.loads((case/'manifest.json').read_text());e=json.loads((case/'execution.json').read_text())
    assert receipt['native_exit_code']==0 and receipt['native_end'] and receipt['samples']==2
    assert sha(case/'manifest.json')==receipt['manifest_sha256'] and sha(case/'execution.json')==receipt['execution_sha256']
    assert all(sha(case/n)==h for n,h in receipt['output_sha256'].items())
    assert all(sha(case/n)==h for n,h in m['file_sha256'].items())
    assert m['image']==IMAGE and (case/'log.binary-sha').read_text().split()[0]==expected_hash
    owner=ascii_list((case/'constant/polyMesh/owner').read_text()).astype(int)
    neighbour=ascii_list((case/'constant/polyMesh/neighbour').read_text()).astype(int)
    internal=len(neighbour);cells=int(max(owner.max(),neighbour.max())+1)
    assert cells==12480 and internal==25936
    fields={}
    for path in sorted((case/'2e-07').iterdir()):
        if path.is_file():
            text=path.read_text();surface='class       surfaceScalarField;' in text
            a=field_values(text,internal if surface else cells)
            fields[path.name]=dict(sha256=sha(path),entries=len(a),minimum=a.min(axis=0).tolist(),maximum=a.max(axis=0).tolist())
    assert set(fields)=={'p','T','U','rho','phi'}
    outputs.append(dict(case=case.name,receipt_sha256=sha(case/'report.json'),binary_sha256=expected_hash,all_payloads_verified=True,fields=fields));manifests.append(m);executions.append(e)
assert manifests[0]['file_sha256']==manifests[1]['file_sha256']
a,b=[e['command'] for e in executions]
expected=[s.replace(str(cases[0].resolve()),str(cases[1].resolve())).replace('bionic-binary-original-052','bionic-binary-rebuilt-053') for s in a]
expected[-1]=expected[-1].replace('command -v rhoPimpleFoam','command -v /binary/rhoPimpleFoam').replace('; rhoPimpleFoam >','; /binary/rhoPimpleFoam >')
assert expected==b
identical=all(outputs[0]['fields'][n]['sha256']==outputs[1]['fields'][n]['sha256'] for n in outputs[0]['fields'])
result=dict(source_sha256=sha(Path(__file__)),cases=outputs,only_executable_differs_apart_from_case_and_container_names=True,all_final_field_payloads_byte_identical=identical,physical_duration_s=2e-7,physical_equilibrium_qualified=False,solver_instrumented=False)
with (w/'binary-pair-readback-v2.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
