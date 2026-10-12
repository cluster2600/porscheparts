"""Bounded native background-only run; preserve its container and every output."""
import json,os,shlex,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from profile_background_v2 import prepare
from prepare_case import IMAGE,sha
case=Path('work/bionic-airflow-20261012/profile-background-030')
geometry=Path('twins/bionic-turbo-f1/evidence/airflow-rear-interface-20261012/geometry-027.json')
profiles=[Path('twins/bionic-turbo-f1/evidence/airflow-profile-interface-20261012')/(label+'-profile-023.json') for label in ('baseline','candidate')]
manifest=prepare(Path('work/bionic-airflow-20261012/baseline-conformal-022'),geometry,profiles,case)
execution=dict(source_sha256=sha(Path(__file__)),timeout_seconds=600,cpus=2,memory_gib=6,container='bionic-profile-background-030',solver_launched=False)
(case/'execution.json').write_text(json.dumps(execution,indent=2)+'\n')
command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; cd /case; blockMesh > log.blockMesh 2>&1 && checkMesh -allTopology -allGeometry > log.checkMesh 2>&1'
started=time.monotonic()
result=subprocess.run(['docker','run','--name',execution['container'],'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','2','--memory','6g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 600 bash -c '+shlex.quote(command)],capture_output=True,text=True,timeout=630)
log=(case/'log.checkMesh').read_text() if (case/'log.checkMesh').exists() else ''
report=dict(source_sha256=sha(Path(__file__)),manifest_sha256=sha(case/'manifest.json'),execution_sha256=sha(case/'execution.json'),native_exit_code=result.returncode,stderr=result.stderr,elapsed_seconds=time.monotonic()-started,mesh_gate_passed=result.returncode==0 and 'Mesh OK.' in log and 'Failed ' not in log,solver_launched=False,physical_walls_meshed=False,performance_ranking_authorized=False)
assert all(sha(case/name)==digest for name,digest in manifest['file_sha256'].items())
report['output_sha256']={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()}
(case/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='output_sha256'},indent=2),flush=True)
