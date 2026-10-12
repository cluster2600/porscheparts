"""Bounded native rest test of admitted projected witness, with unchanged equations."""
import json,os,shlex,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha,IMAGE
from static_mrf_witness import assess
parent=Path('work/bionic-airflow-20261012/full-collar-063');case=Path('work/bionic-airflow-20261012/full-collar-equilibrium-064')
receipt=json.loads((parent/'report.json').read_text());audit_path=Path('work/bionic-full-collar-mesh-20261012/readback.json');audit=json.loads(audit_path.read_text())
assert receipt['mesh_gate_passed'] and receipt['native_exit_code']==0 and audit['all_cell_edges_cancel'] and audit['boundary_matches_constructed_domain']
assert all(sha(parent/n)==h for n,h in receipt['output_sha256'].items())
original=Path('work/bionic-airflow-20261012/static-mrf-profile-026/variable-radius');original_manifest=json.loads((original/'manifest.json').read_text())
case.mkdir(parents=True,exist_ok=False)
for name,h in original_manifest['file_sha256'].items():
 assert sha(original/name)==h
 target=case/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original/name,target)
for name in ('p','T','U'):
 p=case/'0'/name;s=p.read_text();assert s.rstrip().endswith('}')
 p.write_text(s.rstrip()[:-1]+' defaultFaces {type empty;} }\n')
shutil.copytree(parent/'constant/polyMesh',case/'constant/polyMesh')
manifest=dict(source_sha256=sha(Path(__file__)),parent_receipt_sha256=sha(parent/'report.json'),geometry_audit_sha256=sha(audit_path),image=IMAGE,criteria=original_manifest['criteria'],expected_cells=audit['cells'],expected_interface_faces=audit['interface']['faces'],solver_admission_scope='Full collar positioned by geometry062; synthetic lateral/front walls, no rotor or ports; equations from 026 unchanged, zero-face empty patch added.',file_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
(case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; cd /case; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1 && grep -q "Mesh OK." log.checkMesh && ! grep -q "Failed " log.checkMesh && rhoPimpleFoam > log.rhoPimpleFoam 2>&1'
execution=dict(timeout_seconds=1200,cpus=1,memory_gib=2,container='bionic-full-collar-equilibrium-064',command=command)
(case/'execution.json').write_text(json.dumps(execution,indent=2)+'\n');started=time.monotonic()
r=subprocess.run(['docker','run','--name',execution['container'],'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 1200 bash -c '+shlex.quote(command)],capture_output=True,text=True,timeout=1230)
assert all(sha(case/n)==h for n,h in manifest['file_sha256'].items())
log=(case/'log.rhoPimpleFoam').read_text() if (case/'log.rhoPimpleFoam').exists() else ''
result=dict(native_exit_code=r.returncode,stderr=r.stderr,elapsed_seconds=time.monotonic()-started,manifest_sha256=sha(case/'manifest.json'),execution_sha256=sha(case/'execution.json'),solver_launched=bool(log),native_end=log.rstrip().endswith('End'),performance_ranking_authorized=False)
if r.returncode==0:
 assert result['native_end']
 low=np.loadtxt(case/'postProcessing/minima/0/volFieldValue.dat');high=np.loadtxt(case/'postProcessing/maxima/0/volFieldValue.dat')
 assert len(low)==200 and abs(low[-1,0]-2e-5)<1e-15
 result.update(assess(low,high,manifest['criteria']));result.update(samples=len(low),pressure_linear_iteration_cap_hits=log.count('No Iterations 1000'))
result['output_sha256']={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()}
(case/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='output_sha256'}),flush=True)
