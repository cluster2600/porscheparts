"""Bounded native radial subdivision, split and isolated-region admission."""
import json,os,re,shlex,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import IMAGE,sha
from audit_diagnostic import ascii_list
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');mode=sys.argv[1]
names={'full':'radial-full-077','split':'radial-split-078','isolated':'radial-isolated-079'}
assert mode in names
case=root/names[mode];assert not case.exists()
parent=root/({'full':'full-collar-063','split':'radial-full-077','isolated':'radial-split-078'}[mode])
r=json.loads((parent/'report.json').read_text());assert r['native_exit_code']==0
assert all(sha(parent/n)==h for n,h in r['output_sha256'].items())
if mode!='isolated':assert r['mesh_gate_passed']
active=subprocess.check_output(['docker','ps','--format','{{.Names}} {{.Status}}']).decode()
assert not any(line.startswith('bionic-') for line in active.splitlines()),active
case.mkdir();shutil.copytree(parent/'system',case/'system')
if mode=='full':
 (case/'constant').mkdir()
 path=case/'system/blockMeshDict';original=path.read_text()
 pattern=r'(hex\s+\([^)]*\)\s+)(\(1 1 1\))'
 updated,n=re.subn(pattern,r'\g<1>(2 1 1)',original)
 assert n==6784 and updated.count('rotorZone (1 1 1)')==20352
 assert updated.replace(') (2 1 1) simpleGrading',') (1 1 1) simpleGrading')==original
 path.write_text(updated);command='blockMesh > log.blockMesh 2>&1; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1'
elif mode=='split':
 shutil.copytree(parent/'constant',case/'constant')
 command='splitMeshRegions -cellZones -overwrite > log.splitMeshRegions 2>&1'
else:
 source=parent/'constant/domain1/polyMesh';mesh=case/'constant/polyMesh';mesh.mkdir(parents=True)
 for n in ('points','faces','owner','neighbour'):shutil.copy2(source/n,mesh/n)
 text=(source/'boundary').read_text();counts=[int(x) for x in re.findall(r'nFaces\s+(\d+)',text)];starts=[int(x) for x in re.findall(r'startFace\s+(\d+)',text)]
 internal=len(ascii_list((mesh/'neighbour').read_text()));assert min(starts)==internal and len(starts)==2 and starts[1]==starts[0]+counts[0]
 header=lambda n,c:f'FoamFile {{version 2.0; format ascii; class {c}; object {n};}}\n'
 (mesh/'boundary').write_text(header('boundary','polyBoundaryMesh')+f'1\n(\nwalls {{type wall; nFaces {sum(counts)}; startFace {internal};}}\n)\n')
 for n in ('cellZones','faceZones','pointZones'):(mesh/n).write_text(header(n,'regIOobject')+'0\n(\n)\n')
 command='checkMesh -allTopology -allGeometry > log.checkMesh 2>&1'
manifest=dict(image=IMAGE,parent=str(parent),parent_report_sha256=sha(parent/'report.json'),runner_sha256=sha(Path(__file__)),mode=mode,physical_turbo_geometry_present=False,only_full_input_change='6784 fixed blocks: (1 1 1) to (2 1 1)',file_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
(case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');shutil.copytree(case,w/(names[mode]+'-inputs'))
(case/'docker-before.txt').write_text(active)
command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; set -e; cd /case; '+command
container='bionic-'+names[mode]
cmd=['docker','run','--name',container,'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 240 bash -c '+shlex.quote(command)]
(case/'execution.json').write_text(json.dumps(dict(command=cmd,timeout_seconds=240),indent=2)+'\n');start=time.monotonic()
with (case/'container.log').open('x') as f:result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=270)
state=json.loads(subprocess.check_output(['docker','inspect',container]))[0]['State'];log=(case/'log.checkMesh').read_text() if (case/'log.checkMesh').exists() else ''
report=dict(native_exit_code=result.returncode,elapsed_seconds=time.monotonic()-start,container_state=state,mesh_gate_passed='Mesh OK.' in log and 'Failed ' not in log,solver_launched=False,output_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
(case/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='output_sha256'}))
