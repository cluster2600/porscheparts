"""Full-duration native log-control comparison against rejected 044; no physics change."""
import json,os,shlex,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha,IMAGE
w=Path(__file__).parent;base=Path('work/bionic-airflow-20261012');parent=base/'directed-equilibrium-044'
prior=json.loads((parent/'report.json').read_text())
assert prior['native_exit_code']==0 and prior['native_end']
assert all(sha(parent/n)==h for n,h in prior['output_sha256'].items())
build=Path('work/bionic-native-diagnostics-20261012');audit=json.loads((build/'source-audit.json').read_text());binary=build/'baseline-build-v6/bin/rhoPimpleFoam'
assert audit['all_original_regular_payloads_unchanged'] and sha(binary)==audit['compiled_binary_sha256']
cases=[]
for name,executable in (('native-residual-full-055','rhoPimpleFoam'),):
    case=base/name;case.mkdir(exist_ok=False)
    for prefix in ('0','constant','system'):
        for source in (parent/prefix).rglob('*'):
            if source.is_file():
                path=str(source.relative_to(parent));assert sha(source)==prior['output_sha256'][path]
                target=case/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    path=case/'system/fvSolution';text=path.read_text()
    assert text.count('p {solver GAMG;')==1
    path.write_text(text.replace('p {solver GAMG;','p {solver GAMG; log 2;'))
    hashes={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()}
    manifest=dict(source_sha256=sha(Path(__file__)),parent_receipt_sha256=sha(parent/'report.json'),source_audit_sha256=sha(build/'source-audit.json'),image=IMAGE,executable=executable,compiled_binary_sha256=sha(binary),file_sha256=hashes,expected_samples=200,physical_equilibrium_qualified=False,only_input_change='system/fvSolution: p log 2; inherited by pFinal',software_identity_criterion='All final field payloads must be byte-identical; no numerical tolerance.')
    if cases:assert hashes==json.loads((cases[0]/'manifest.json').read_text())['file_sha256']
    (case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');cases.append(case)
for case in cases:
    manifest=json.loads((case/'manifest.json').read_text());executable=manifest['executable']
    command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; set -e; cd /case; sha256sum "$(command -v '+executable+')" > log.binary-sha; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1; grep -q "Mesh OK." log.checkMesh; ! grep -q "Failed " log.checkMesh; '+executable+' > log.rhoPimpleFoam 2>&1'
    cmd=['docker','run','--name','bionic-'+case.name,'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--mount',f'type=bind,source={binary.parent.resolve()},target=/binary,readonly','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 900 bash -c '+shlex.quote(command)]
    execution=dict(command=cmd,timeout_seconds=900);(case/'execution.json').write_text(json.dumps(execution,indent=2)+'\n');start=time.monotonic()
    with (case/'container.log').open('x') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=930)
    assert all(sha(case/n)==h for n,h in manifest['file_sha256'].items())
    log=(case/'log.rhoPimpleFoam').read_text() if (case/'log.rhoPimpleFoam').exists() else ''
    result=dict(native_exit_code=r.returncode,elapsed_seconds=time.monotonic()-start,manifest_sha256=sha(case/'manifest.json'),execution_sha256=sha(case/'execution.json'),solver_launched=bool(log),native_end=log.rstrip().endswith('End'),physical_equilibrium_qualified=False,performance_ranking_authorized=False)
    if r.returncode==0:
        assert result['native_end'];data=np.loadtxt(case/'postProcessing/maxima/0/volFieldValue.dat');assert data.shape==(200,4) and np.isfinite(data).all() and abs(data[-1,0]-2e-5)<1e-18
        result['samples']=len(data)
    result['output_sha256']={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()}
    (case/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(case.name,{k:v for k,v in result.items() if k!='output_sha256'},flush=True)
