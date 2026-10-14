import json,os,shlex,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import IMAGE,sha
case=Path('work/bionic-airflow-20261012/baseline-profile-mesh-031').resolve()
log=case/'log.writeCellCentres'
assert not (case/'0/C').exists() and not log.exists()
inputs={p.name:sha(p) for p in (case/'constant/polyMesh').iterdir() if p.is_file()}
command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; cd /case; exec postProcess -func writeCellCentres -time 0'
with log.open('x') as f:
 r=subprocess.run(['docker','run','--name','bionic-profile-centres-031','--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','3g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 120 bash -c '+shlex.quote(command)],stdout=f,stderr=subprocess.STDOUT,timeout=150)
assert all(sha(case/'constant/polyMesh'/n)==d for n,d in inputs.items())
report={'source_sha256':sha(Path(__file__)),'native_exit_code':r.returncode,'mesh_unchanged':True,'mesh_sha256':inputs,'log_sha256':sha(log),'geometry_only':True,'flow_solver_launched':False,'outputs':{str(p.relative_to(case)):sha(p) for p in (case/'0').glob('C*')}}
(case/'write-centres-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'native_exit_code':r.returncode,'geometry_only':True}))
