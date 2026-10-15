"""Native axial refinement outside the one-cell collar of a verified witness."""
import json,os,shlex,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha,IMAGE
from uniform_interface_projection import read_mesh
from audit_diagnostic import ascii_list
w=Path(__file__).parent;parent=Path('work/bionic-airflow-20261012/reconstructed-interface-038');case=Path('work/bionic-airflow-20261012/protected-axial-056')
prior=json.loads((parent/'report.json').read_text());assert prior['mesh_gate_passed'] and prior['native_exit_code']==0
assert all(sha(parent/n)==h for n,h in prior['output_sha256'].items())
p,faces,interface,internal=read_mesh(parent);mesh=parent/'constant/polyMesh'
owner=ascii_list((mesh/'owner').read_text()).astype(int);neighbour=ascii_list((mesh/'neighbour').read_text()).astype(int)
count=int(max(owner.max(),neighbour.max())+1);protected=np.unique(np.r_[owner[interface],neighbour[interface]])
selected=np.setdiff1d(np.arange(count),protected)
assert count==20480 and len(protected)==len(selected)==10240 and len(interface)==5120
case.mkdir(exist_ok=False)
for prefix in ('0','constant','system'):
 for source in (parent/prefix).rglob('*'):
  if source.is_file():
   name=str(source.relative_to(parent));assert sha(source)==prior['output_sha256'][name]
   target=case/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
shutil.copytree(case/'constant/polyMesh',case/'input/polyMesh')
sets=case/'constant/polyMesh/sets';sets.mkdir(exist_ok=True)
(sets/'outsideCollar').write_text('FoamFile {version 2.0; format ascii; class cellSet; location "constant/polyMesh/sets"; object outsideCollar;}\n'+str(len(selected))+'\n(\n'+'\n'.join(map(str,selected))+'\n)\n')
(case/'system/refineMeshDict').write_text('''FoamFile {version 2.0; format ascii; class dictionary; object refineMeshDict;}
set outsideCollar;
coordinateSystem global;
globalCoeffs {tan1 (1 0 0); tan2 (0 1 0);}
directions (normal);
useHexTopology false;
geometricCut false;
writeMesh false;
''')
(case/'selection.json').write_text(json.dumps(dict(parent_cells=count,interface_faces=interface.tolist(),protected_cells=protected.tolist(),selected_cells=selected.tolist(),selection_rule='All cells except either neighbour of an MRF interface face',direction='global axial z',physical_turbo_geometry_present=False),indent=2)+'\n')
manifest=dict(source_sha256=sha(Path(__file__)),parent_receipt_sha256=sha(parent/'report.json'),image=IMAGE,solver_launched=False,file_sha256={str(x.relative_to(case)):sha(x) for x in case.rglob('*') if x.is_file()})
(case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; set -e; cd /case; refineMesh -overwrite > log.refineMesh 2>&1; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1'
cmd=['docker','run','--name','bionic-protected-axial-056','--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 240 bash -c '+shlex.quote(command)]
(case/'execution.json').write_text(json.dumps(dict(command=cmd,timeout_seconds=240),indent=2)+'\n');started=time.monotonic()
with (case/'container.log').open('x') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=270)
log=(case/'log.checkMesh').read_text() if (case/'log.checkMesh').exists() else ''
result=dict(native_exit_code=r.returncode,elapsed_seconds=time.monotonic()-started,manifest_sha256=sha(case/'manifest.json'),execution_sha256=sha(case/'execution.json'),mesh_gate_passed='Mesh OK.' in log and 'Failed ' not in log,solver_launched=False,performance_ranking_authorized=False,output_sha256={str(x.relative_to(case)):sha(x) for x in case.rglob('*') if x.is_file()})
(case/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='output_sha256'}))
