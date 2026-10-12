"""Uniformly refine a copy of frozen witness 026; mesh diagnostic only."""
import json,os,shlex,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha,IMAGE
parent=Path('work/bionic-airflow-20261012/static-mrf-profile-026/variable-radius')
case=Path('work/bionic-airflow-20261012/uniform-interface-034')
report=json.loads((parent/'report.json').read_text());prior=json.loads((parent/'manifest.json').read_text())
assert report['native_exit_code']==0 and report['manifest_sha256']==sha(parent/'manifest.json')
case.mkdir(parents=True,exist_ok=False)
for prefix in ('0','system','constant'):
 for source in (parent/prefix).rglob('*'):
  if source.is_file():
   name=str(source.relative_to(parent));assert sha(source)==report['output_sha256'][name]
   target=case/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
shutil.copytree(case/'constant/polyMesh',case/'input/polyMesh')
manifest=dict(source_sha256=sha(Path(__file__)),parent_manifest_sha256=sha(parent/'manifest.json'),parent_receipt_sha256=sha(parent/'report.json'),profile=prior['profile_witness'],image=IMAGE,solver_launched=False,
              file_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file() and 'constant/polyMesh/' not in str(p.relative_to(case))})
(case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; cd /case; refineMesh -all -overwrite > log.refineMesh 2>&1 && checkMesh -allTopology -allGeometry > log.checkMesh 2>&1'
execution=dict(timeout_seconds=240,cpus=1,memory_gib=2,container='bionic-uniform-interface-034',command=command)
(case/'execution.json').write_text(json.dumps(execution,indent=2)+'\n');started=time.monotonic()
r=subprocess.run(['docker','run','--name',execution['container'],'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 240 bash -c '+shlex.quote(command)],capture_output=True,text=True,timeout=270)
assert all(sha(case/n)==h for n,h in manifest['file_sha256'].items())
log=(case/'log.checkMesh').read_text() if (case/'log.checkMesh').exists() else ''
receipt=dict(native_exit_code=r.returncode,stderr=r.stderr,elapsed_seconds=time.monotonic()-started,manifest_sha256=sha(case/'manifest.json'),execution_sha256=sha(case/'execution.json'),mesh_gate_passed='Mesh OK.' in log and 'Failed ' not in log,solver_launched=False,performance_ranking_authorized=False,output_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
(case/'report.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='output_sha256'}),flush=True)
