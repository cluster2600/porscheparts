"""Bounded physical-wall meshing only; retain rejected native outputs and container."""
import json,os,shlex,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_profile_mesh import prepare
from prepare_case import IMAGE,sha
case=Path('work/bionic-airflow-20261012/baseline-profile-mesh-031')
manifest=prepare(Path('work/bionic-airflow-20261012/baseline-conformal-022'),Path('work/bionic-airflow-20261012/profile-background-030'),Path('twins/bionic-turbo-f1/evidence/airflow-structured-background-20261012/native-background-030.json'),case)
execution=dict(source_sha256=sha(Path(__file__)),timeout_seconds=1800,cpus=2,memory_gib=8,container='bionic-profile-mesh-031',solver_launched=False)
(case/'execution.json').write_text(json.dumps(execution,indent=2)+'\n')
names=['blockMesh','snappyHexMesh','topoSet','checkMesh'];args=['','-overwrite','','-allTopology -allGeometry']
command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; cd /case; '
for name,arg in zip(names,args):
    command+=f'{name} {arg} > log.{name} 2>&1; rc=$?; echo "$rc" > exit.{name}; if [ "$rc" -ne 0 ]; then exit "$rc"; fi; '
started=time.monotonic()
result=subprocess.run(['docker','run','--name',execution['container'],'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','256','--cpus','2','--memory','8g','--tmpfs','/tmp:rw,nosuid,size=256m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 1800 bash -c '+shlex.quote(command)],capture_output=True,text=True,timeout=1830)
log=(case/'log.checkMesh').read_text() if (case/'log.checkMesh').exists() else ''
report=dict(source_sha256=sha(Path(__file__)),case_manifest_sha256=sha(case/'case-manifest.json'),execution_sha256=sha(case/'execution.json'),native_exit_code=result.returncode,stderr=result.stderr,elapsed_seconds=time.monotonic()-started,mesh_gate_passed=result.returncode==0 and 'Mesh OK.' in log and 'Failed ' not in log,solver_launched=False,performance_ranking_authorized=False,stages=[])
for name in names:
    if (case/f'exit.{name}').exists():report['stages'].append(dict(name=name,exit_code=int((case/f'exit.{name}').read_text()),log='log.'+name,sha256=sha(case/('log.'+name))))
assert all(sha(case/name)==digest for name,digest in manifest['file_sha256'].items())
report['output_sha256']={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()}
(case/'run-mesh.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='output_sha256'},indent=2),flush=True)
