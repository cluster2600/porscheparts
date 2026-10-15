import json,os,shlex,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import IMAGE,sha
w=Path(__file__).parent
def execute(case,command,parents):
 active=subprocess.check_output(['docker','ps','--format','{{.Names}} {{.Status}}']).decode();assert not any(s.startswith('bionic-') for s in active.splitlines()),active
 manifest=dict(image=IMAGE,source_sha256=sha(Path(__file__)),phase_sources={p.name:sha(p) for p in w.glob('*.py')},parents={str(c):sha(c/'report.json') for c in parents},synthetic_only=True,file_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
 (case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');shutil.copytree(case,w/(case.name+'-inputs'));(case/'docker-before.txt').write_text(active)
 command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; set -e; cd /case; '+command
 container='bionic-'+case.name;cmd=['docker','run','--name',container,'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 240 bash -c '+shlex.quote(command)]
 (case/'execution.json').write_text(json.dumps(dict(command=cmd,timeout_seconds=240),indent=2)+'\n');start=time.monotonic()
 with (case/'container.log').open('x') as out:r=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT,timeout=270)
 state=json.loads(subprocess.check_output(['docker','inspect',container]))[0]['State'];log=(case/'log.checkMesh').read_text() if (case/'log.checkMesh').exists() else ''
 report=dict(native_exit_code=r.returncode,elapsed_seconds=time.monotonic()-start,container_state=state,solver_launched=False,mesh_gate_passed='Mesh OK.' in log and 'Failed ' not in log,output_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
 (case/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(case.name,json.dumps({k:v for k,v in report.items() if k!='output_sha256'}),flush=True);return report
