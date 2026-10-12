"""Project only the uniform witness interface; preserve walls and audit native quality."""
import json,os,re,shlex,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha,IMAGE
from uniform_interface_projection import read_mesh
from uniform_interface_projection_v2 import project
from audit_diagnostic import ascii_list
parent=Path('work/bionic-airflow-20261012/uniform-interface-034');case=Path('work/bionic-airflow-20261012/projected-interface-035')
prior=json.loads((parent/'manifest.json').read_text());receipt=json.loads((parent/'report.json').read_text())
assert receipt['mesh_gate_passed'] and receipt['native_exit_code']==0 and receipt['manifest_sha256']==sha(parent/'manifest.json')
p,faces,selected,internal=read_mesh(parent);interface=[faces[i] for i in selected]
q,audit=project(p,interface,prior['profile']['nodes_z_radius_mm'],10471.975511966)
moved=np.flatnonzero(np.linalg.norm(q-p,axis=1)>0);interface_ids=np.unique(np.concatenate(interface));assert set(moved)<=set(interface_ids)
# Moving interior vertices on an end plane preserves its union; lateral wall vertices must stay exact.
for face in faces[internal:]:
    if np.ptp(p[face,2])>1e-14:assert np.array_equal(p[face],q[face])
    else:
        assert abs(p[face[0],2]-p[:,2].min())<1e-14 or abs(p[face[0],2]-p[:,2].max())<1e-14
        assert np.array_equal(p[face,2],q[face,2])
case.mkdir(parents=True,exist_ok=False)
for prefix in ('0','system','constant'):
 for source in (parent/prefix).rglob('*'):
  if source.is_file():
   name=str(source.relative_to(parent));assert sha(source)==receipt['output_sha256'][name]
   target=case/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
shutil.copytree(case/'constant/polyMesh',case/'input/polyMesh')
path=case/'constant/polyMesh/points';text=path.read_text();header=text[:re.search(r'\n\s*\d+\s*\n\(',text).start()]
path.write_text(header+'\n'+str(len(q))+'\n(\n'+'\n'.join('('+' '.join(format(x,'.17g') for x in v)+')' for v in q)+'\n)\n')
assert np.array_equal(ascii_list(path.read_text(),True),q)
audit.update(source_sha256=sha(Path('twins/bionic-turbo-f1/cfd/uniform_interface_projection_v2.py')),interface_faces=len(selected),only_interface_points_moved=True,lateral_wall_points_unchanged=True,cap_planes_unchanged=True,connectivity_unchanged=True,physical_turbo_geometry_present=False)
(case/'projection-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
manifest=dict(source_sha256=sha(Path(__file__)),parent_manifest_sha256=sha(parent/'manifest.json'),parent_receipt_sha256=sha(parent/'report.json'),projection_source_sha256=audit['source_sha256'],profile=prior['profile'],image=IMAGE,solver_launched=False,file_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
(case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; cd /case; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1'
execution=dict(timeout_seconds=240,cpus=1,memory_gib=2,container='bionic-projected-interface-035',command=command)
(case/'execution.json').write_text(json.dumps(execution,indent=2)+'\n');started=time.monotonic()
r=subprocess.run(['docker','run','--name',execution['container'],'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 240 bash -c '+shlex.quote(command)],capture_output=True,text=True,timeout=270)
assert all(sha(case/n)==h for n,h in manifest['file_sha256'].items())
log=(case/'log.checkMesh').read_text();receipt=dict(native_exit_code=r.returncode,stderr=r.stderr,elapsed_seconds=time.monotonic()-started,manifest_sha256=sha(case/'manifest.json'),execution_sha256=sha(case/'execution.json'),mesh_gate_passed='Mesh OK.' in log and 'Failed ' not in log,solver_launched=False,performance_ranking_authorized=False,output_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
(case/'report.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(audit));print(json.dumps({k:v for k,v in receipt.items() if k!='output_sha256'}))
