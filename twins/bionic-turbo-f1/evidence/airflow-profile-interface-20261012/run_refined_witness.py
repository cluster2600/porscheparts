"""Bounded paired native witnesses; reject mesh diagnostics before launching flow."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
import profile_mrf_witness_v2 as profile
import static_mrf_witness as witness
from prepare_case import IMAGE,sha

root=Path('work/bionic-airflow-20261012/static-mrf-profile-025')
parent=Path('work/bionic-airflow-20261012/baseline-interface-015')
source=Path('work/bionic-interface-profile-20261012/profile-023.json')
root.mkdir(parents=True,exist_ok=False)
for label,omega in (('inertial',0.),('variable-radius',10471.975511966)):
    case=root/label
    manifest=profile.prepare(parent,case,source,omega)
    execution=dict(source_sha256=sha(Path(__file__)),native_wall_limit_seconds=600,cpus=1,memory_gib=2,
                   performance_ranking_authorized=False)
    (case/'execution.json').write_text(json.dumps(execution,indent=2)+'\n')
    command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; cd /case; blockMesh > log.blockMesh 2>&1 && topoSet > log.topoSet 2>&1 && checkMesh -allTopology -allGeometry > log.checkMesh 2>&1 && grep -q "Mesh OK." log.checkMesh && ! grep -q "Failed .* mesh checks" log.checkMesh && rhoPimpleFoam > log.rhoPimpleFoam 2>&1'
    started=time.monotonic()
    result=subprocess.run(['docker','run','--rm','--name','bionic-profile-025-'+label,'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 600 bash -c '+shlex.quote(command)],capture_output=True,text=True,timeout=630)
    report=dict(native_exit_code=result.returncode,stderr=result.stderr,elapsed_seconds=time.monotonic()-started,
                manifest_sha256=sha(case/'manifest.json'),execution_sha256=sha(case/'execution.json'),performance_ranking_authorized=False)
    if result.returncode==0:
        assert 'Mesh OK.' in (case/'log.checkMesh').read_text()
        log=(case/'log.rhoPimpleFoam').read_text();assert log.rstrip().endswith('End')
        low=np.loadtxt(case/'postProcessing/minima/0/volFieldValue.dat')
        high=np.loadtxt(case/'postProcessing/maxima/0/volFieldValue.dat')
        assert len(low)==200 and abs(low[-1,0]-2e-5)<1e-15
        report.update(witness.assess(low,high,manifest['criteria']))
        report['samples']=len(low)
        report['pressure_linear_iteration_cap_hits']=log.count('No Iterations 1000')
    assert all(sha(case/name)==digest for name,digest in manifest['file_sha256'].items())
    report['output_sha256']={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()}
    (case/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(label,json.dumps({k:v for k,v in report.items() if k!='output_sha256'}),flush=True)
