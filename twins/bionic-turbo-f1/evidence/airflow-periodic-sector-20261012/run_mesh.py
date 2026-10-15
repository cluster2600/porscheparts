"""New periodic boundary problem, retaining every point, face and cell of 043."""
import json,os,shlex,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha,header,IMAGE
from uniform_interface_projection import read_mesh
from audit_diagnostic import ascii_list
from periodic_sector_boundary import paired_cuts
parent=Path('work/bionic-airflow-20261012/directed-sector-043');case=Path('work/bionic-airflow-20261012/periodic-sector-047')
receipt=json.loads((parent/'report.json').read_text());assert receipt['mesh_gate_passed'] and receipt['native_exit_code']==0
p,f,selected,internal=read_mesh(parent);order,audit=paired_cuts(p,f,internal,2*np.pi/128)
assert audit['paired_faces']==80 and audit['walls']==768
case.mkdir(exist_ok=False)
for prefix in ('0','system','constant'):
 for source in (parent/prefix).rglob('*'):
  if source.is_file():
   name=str(source.relative_to(parent));assert sha(source)==receipt['output_sha256'][name]
   target=case/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
mesh=case/'constant/polyMesh';owner=ascii_list((mesh/'owner').read_text()).astype(int)
def write(path,kind,entries):path.write_text(header(path.name,kind)+str(len(entries))+'\n(\n'+'\n'.join(entries)+'\n)\n')
write(mesh/'faces','faceList',[str(len(f[i]))+'('+' '.join(map(str,f[i]))+')' for i in order]);write(mesh/'owner','labelList',list(map(str,owner[order])))
inverse=np.argsort(order)
for path in (mesh/'sets').glob('*'):
 text=path.read_text();assert 'faceSet' in text
 labels=ascii_list(text).astype(int);write(path,'faceSet',list(map(str,inverse[labels])))
for name in ('faceZones','pointZones'):assert (mesh/name).read_text().split('}')[-1].strip()=='0()'
boundary=[f'walls {{type wall; nFaces 768; startFace {internal};}}']
for index,(name,other) in enumerate((('periodicLower','periodicUpper'),('periodicUpper','periodicLower'))):
 boundary.append(f'{name} {{type cyclic; neighbourPatch {other}; transform rotational; rotationAxis (0 0 1); rotationCentre (0 0 0); nFaces 80; startFace {internal+768+80*index};}}')
(mesh/'boundary').write_text(header('boundary','polyBoundaryMesh')+'3\n(\n'+'\n'.join(boundary)+'\n)\n')
for path in (case/'0').iterdir():
 text=path.read_text();end=text.rfind('}');assert end>=0
 path.write_text(text[:end]+'periodicLower {type cyclic;} periodicUpper {type cyclic;}'+text[end:])
(case/'face-permutation.json').write_text(json.dumps(order.tolist())+'\n')
(case/'pair-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
manifest=dict(source_sha256=sha(Path(__file__)),helper_sha256=sha(Path('twins/bionic-turbo-f1/cfd/periodic_sector_boundary.py')),parent_receipt_sha256=sha(parent/'report.json'),image=IMAGE,scope='Different synthetic periodic sector boundary problem, not a real turbo correction.',file_sha256={str(x.relative_to(case)):sha(x) for x in case.rglob('*') if x.is_file()})
(case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; cd /case; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1'
execution=dict(container='bionic-periodic-sector-047',command=command,timeout_seconds=120,cpus=1,memory_gib=2)
(case/'execution.json').write_text(json.dumps(execution,indent=2)+'\n');start=time.monotonic()
r=subprocess.run(['docker','run','--name',execution['container'],'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 120 bash -c '+shlex.quote(command)],capture_output=True,text=True,timeout=150)
log=(case/'log.checkMesh').read_text();result=dict(native_exit_code=r.returncode,stderr=r.stderr,elapsed_seconds=time.monotonic()-start,manifest_sha256=sha(case/'manifest.json'),mesh_gate_passed=r.returncode==0 and 'Mesh OK.' in log and 'Failed ' not in log,solver_launched=False,output_sha256={str(x.relative_to(case)):sha(x) for x in case.rglob('*') if x.is_file()})
(case/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='output_sha256'}))
