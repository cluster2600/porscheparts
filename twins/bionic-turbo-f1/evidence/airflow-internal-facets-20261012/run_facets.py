"""Native admission of a new internal-facet witness, preserving all source points."""
import json,os,re,shlex,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha,IMAGE
from uniform_interface_projection import read_mesh,metrics
from internal_face_facets import facet_internal,balance
from audit_diagnostic import ascii_list
parent=Path('work/bionic-airflow-20261012/projected-interface-035');case=Path('work/bionic-airflow-20261012/internal-facets-040')
prior=json.loads((parent/'manifest.json').read_text());receipt=json.loads((parent/'report.json').read_text())
assert receipt['mesh_gate_passed'] and receipt['native_exit_code']==0 and receipt['manifest_sha256']==sha(parent/'manifest.json')
p,faces,selected,internal=read_mesh(parent);mesh=parent/'constant/polyMesh'
owner=ascii_list((mesh/'owner').read_text()).astype(int);neighbour=ascii_list((mesh/'neighbour').read_text()).astype(int)
zone_text=(mesh/'cellZones').read_text();m=re.search(r'cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',zone_text,re.S);zone=np.fromstring(m[2],sep=' ',dtype=int);assert len(zone)==int(m[1])
assert re.search(r'\n0\s*\(\s*\)',(mesh/'faceZones').read_text())
new,own,nei,parents,audit=facet_internal(p,faces,owner,neighbour,selected)
assert all(new[j]==list(faces[i]) for j,i in enumerate(parents) if i in set(selected))
assert new[len(nei):]==[list(f) for f in faces[internal:]]
assert np.array_equal(own[len(nei):],owner[internal:])
audit['before'],_=balance(p,faces,owner,neighbour,10471.975511966,zone)
audit['after'],_=balance(p,new,own,nei,10471.975511966,zone)
audit['interface']=metrics(p,[faces[i] for i in selected],10471.975511966)
assert audit['after']['max_area_closure_m2']<1e-15 and audit['after']['minimum_oriented_cell_volume_m3']>0
assert audit['after']['max_rotating_cell_flux_m3_s']<1e-18
case.mkdir(parents=True,exist_ok=False)
for prefix in ('0','system','constant'):
 for source in (parent/prefix).rglob('*'):
  if source.is_file():
   name=str(source.relative_to(parent));assert sha(source)==receipt['output_sha256'][name]
   target=case/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
shutil.copytree(case/'constant/polyMesh',case/'input/polyMesh')
def write_list(name,values):
 path=case/'constant/polyMesh'/name;text=path.read_text();header=text[:re.search(r'\n\s*\d+\s*\n\(',text).start()];header=re.sub(r'\s*note\s+"[^"]*";','',header)
 path.write_text(header+'\n'+str(len(values))+'\n(\n'+'\n'.join(values)+'\n)\n')
write_list('faces',[str(len(f))+'('+' '.join(map(str,f))+')' for f in new]);write_list('owner',list(map(str,own)));write_list('neighbour',list(map(str,nei)))
path=case/'constant/polyMesh/boundary';delta=len(nei)-internal
path.write_text(re.sub(r'(startFace\s+)(\d+)',lambda m:m[1]+str(int(m[2])+delta),path.read_text()))
assert sha(case/'constant/polyMesh/points')==sha(mesh/'points') and sha(case/'constant/polyMesh/cellZones')==sha(mesh/'cellZones')
audit.update(source_sha256=sha(Path('twins/bionic-turbo-f1/cfd/internal_face_facets.py')),new_internal_faces=len(nei),original_internal_faces=internal,physical_turbo_geometry_present=False)
(case/'facet-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
manifest=dict(source_sha256=sha(Path(__file__)),parent_manifest_sha256=sha(parent/'manifest.json'),parent_receipt_sha256=sha(parent/'report.json'),facet_source_sha256=audit['source_sha256'],profile=prior['profile'],image=IMAGE,solver_launched=False,file_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
(case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; cd /case; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1'
execution=dict(timeout_seconds=240,cpus=1,memory_gib=2,container='bionic-internal-facets-040',command=command)
(case/'execution.json').write_text(json.dumps(execution,indent=2)+'\n');started=time.monotonic()
r=subprocess.run(['docker','run','--name',execution['container'],'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 240 bash -c '+shlex.quote(command)],capture_output=True,text=True,timeout=270)
assert all(sha(case/n)==h for n,h in manifest['file_sha256'].items())
log=(case/'log.checkMesh').read_text();receipt=dict(native_exit_code=r.returncode,stderr=r.stderr,elapsed_seconds=time.monotonic()-started,manifest_sha256=sha(case/'manifest.json'),execution_sha256=sha(case/'execution.json'),mesh_gate_passed='Mesh OK.' in log and 'Failed ' not in log,solver_launched=False,performance_ranking_authorized=False,output_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
(case/'report.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in audit.items() if k!='split_original_faces'}));print(json.dumps({k:v for k,v in receipt.items() if k!='output_sha256'}))
