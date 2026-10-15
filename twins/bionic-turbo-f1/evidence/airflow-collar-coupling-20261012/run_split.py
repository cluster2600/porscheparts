"""Native region split of a copied collar; pinned parent is read-only."""
import json,os,shlex,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import IMAGE,sha
parent=Path('work/bionic-airflow-20261012/full-collar-063');case=Path('work/bionic-airflow-20261012/collar-split-065')
report=json.loads((parent/'report.json').read_text())
assert report['native_exit_code']==0 and report['mesh_gate_passed']
assert all(sha(parent/n)==h for n,h in report['output_sha256'].items())
assert not case.exists()
case.mkdir()
for name in ('system','constant'):shutil.copytree(parent/name,case/name)
(case/'manifest.json').write_text(json.dumps(dict(parent=str(parent),parent_report_sha256=sha(parent/'report.json'),runner_sha256=sha(Path(__file__)),image=IMAGE,file_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()}),indent=2)+'\n')
command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; set -e; cd /case; splitMeshRegions -cellZones -overwrite > log.splitMeshRegions 2>&1'
cmd=['docker','run','--name','bionic-collar-split-065','--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 240 bash -c '+shlex.quote(command)]
(case/'execution.json').write_text(json.dumps(dict(command=cmd,timeout_seconds=240),indent=2)+'\n');start=time.monotonic()
with (case/'container.log').open('x') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=270)
state=json.loads(subprocess.check_output(['docker','inspect','bionic-collar-split-065']))[0]['State']
result=dict(native_exit_code=r.returncode,elapsed_seconds=time.monotonic()-start,container_state=state,solver_launched=False,mesh_admission=False,output_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
(case/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='output_sha256'}))
