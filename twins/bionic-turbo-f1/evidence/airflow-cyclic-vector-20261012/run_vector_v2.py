"""Native manufactured cyclic traces; no flow solver and no old case edits."""
import json,os,shlex,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha,header,IMAGE
parent=Path('work/bionic-airflow-20261012/periodic-sector-047');case=Path('work/bionic-airflow-20261012/cyclic-vector-050');receipt=json.loads((parent/'report.json').read_text());assert receipt['mesh_gate_passed']
case.mkdir(exist_ok=False)
for prefix in ('0','system','constant'):
 for source in (parent/prefix).rglob('*'):
  if source.is_file():
   name=str(source.relative_to(parent));assert sha(source)==receipt['output_sha256'][name]
   target=case/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
n=12480;i=np.arange(n,dtype=float);fields={name:np.tile(v,(n,1)) for name,v in zip(('basisX','basisY','basisZ'),np.eye(3))};fields['tagged']=np.column_stack((1+i/n,2+(i%97)/97,3+(i%71)/71))
for name,values in fields.items():
 text=header(name,'volVectorField')+'dimensions [0 0 0 0 0 0 0];\ninternalField nonuniform List<vector>\n'+str(n)+'\n(\n'+'\n'.join('('+' '.join(format(x,'.17g') for x in v)+')' for v in values)+'\n);\nboundaryField {walls {type zeroGradient;} periodicLower {type cyclic;} periodicUpper {type cyclic;}}\n'
 (case/'0'/name).write_text(text)
manifest=dict(source_sha256=sha(Path(__file__)),parent_receipt_sha256=sha(parent/'report.json'),image=IMAGE,scope='Manufactured diagnostic vector fields, dimensionless; no physical velocity or flow solver.',trace_absolute_tolerance_formula='8 * float32 epsilon * max(1, max absolute expected component)',file_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
(case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; cd /case; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1 && grep -q "Mesh OK." log.checkMesh && ! grep -q "Failed " log.checkMesh && postProcess -func writeCellCentres -time 0 > log.centres 2>&1 && foamToVTK -legacy -fields "(basisX basisY basisZ tagged)" -time 0 -no-internal -no-point-data -with-ids -patches "(periodicLower periodicUpper)" -name traces > log.traces 2>&1 && foamToVTK -legacy -fields "(basisX basisY basisZ tagged)" -time 0 -no-internal -no-point-data -with-ids -patches "(periodicLower periodicUpper)" -nearCellValue -name ownerValues > log.ownerValues 2>&1'
execution=dict(container='bionic-cyclic-vector-050',command=command,timeout_seconds=120,cpus=1,memory_gib=2)
(case/'execution.json').write_text(json.dumps(execution,indent=2)+'\n');start=time.monotonic()
r=subprocess.run(['docker','run','--name',execution['container'],'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 120 bash -c '+shlex.quote(command)],capture_output=True,text=True,timeout=150)
assert all(sha(case/n)==h for n,h in manifest['file_sha256'].items())
result=dict(native_exit_code=r.returncode,stderr=r.stderr,elapsed_seconds=time.monotonic()-start,manifest_sha256=sha(case/'manifest.json'),solver_launched=False,output_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
(case/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='output_sha256'}))
