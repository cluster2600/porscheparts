"""Isolate synthetic coordinate offset from standalone-region mesh quality."""
import json,os,shlex,shutil,subprocess,time,sys
from pathlib import Path
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import IMAGE,sha
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');source=w/'selective-initial-071-inputs';case=root/'selective-unshifted-072';assert not case.exists()
shutil.copytree(source,case);original=root/'collar-split-065/constant/domain1/polyMesh/points';shutil.copy2(original,case/'constant/polyMesh/points')
manifest=json.loads((case/'manifest.json').read_text());manifest.update(source_sha256=sha(Path(__file__)),paired_case='selective-initial-071',only_prepared_change='constant/polyMesh/points',offset_fraction=0,original_points_sha256=sha(original));manifest['file_sha256']={n:sha(case/n) for n in manifest['file_sha256']}
prior=json.loads((source/'manifest.json').read_text());assert [n for n,h in prior['file_sha256'].items() if manifest['file_sha256'][n]!=h]==['constant/polyMesh/points']
(case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');shutil.copytree(case,w/'selective-unshifted-072-inputs')
(case/'docker-before.txt').write_bytes(subprocess.check_output(['docker','ps','--format','{{.Names}} {{.Status}}']))
command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; set -e; cd /case; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1';container='bionic-selective-unshifted-072'
cmd=['docker','run','--name',container,'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 240 bash -c '+shlex.quote(command)]
(case/'execution.json').write_text(json.dumps(dict(command=cmd,timeout_seconds=240),indent=2)+'\n');start=time.monotonic()
with (case/'container.log').open('x') as f:result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=270)
state=json.loads(subprocess.check_output(['docker','inspect',container]))[0]['State'];log=(case/'log.checkMesh').read_text()
report=dict(native_exit_code=result.returncode,elapsed_seconds=time.monotonic()-start,container_state=state,mesh_gate_passed='Mesh OK.' in log and 'Failed ' not in log,solver_launched=False,output_sha256={str(x.relative_to(case)):sha(x) for x in case.rglob('*') if x.is_file()});(case/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k!='output_sha256'})
