"""Native admission only of face-pyramid partition; no solver on rejected meshes."""
import json,os,re,shlex,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha,IMAGE
from uniform_interface_projection import read_mesh,metrics
from internal_face_facets import balance
from star_cell_partition import partition
from audit_diagnostic import ascii_list
parent=Path('work/bionic-airflow-20261012/internal-facets-040');case=Path('work/bionic-airflow-20261012/star-partition-041')
prior=json.loads((parent/'manifest.json').read_text());receipt=json.loads((parent/'report.json').read_text())
assert receipt['native_exit_code']==0 and not receipt['mesh_gate_passed'] and receipt['manifest_sha256']==sha(parent/'manifest.json')
p,faces,selected,internal=read_mesh(parent);mesh=parent/'constant/polyMesh'
owner=ascii_list((mesh/'owner').read_text()).astype(int);neighbour=ascii_list((mesh/'neighbour').read_text()).astype(int)
zone_text=(mesh/'cellZones').read_text();m=re.search(r'cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',zone_text,re.S);zone=np.fromstring(m[2],sep=' ',dtype=int);assert len(zone)==int(m[1])
q,new,own,nei,new_zone,parents=partition(p,faces,owner,neighbour,zone)
flags=np.zeros(len(parents),bool);flags[new_zone]=True;interface=np.flatnonzero(flags[own[:len(nei)]]^flags[nei])
assert {tuple(new[i]) for i in interface}=={tuple(faces[i]) for i in selected}
assert new[len(nei):]==[list(f) for f in faces[internal:]] and np.array_equal(q[:len(p)],p)
audit,_=balance(q,new,own,nei,10471.975511966,new_zone)
audit.update(interface=metrics(q,[new[i] for i in interface],10471.975511966),original_points_byte_values_unchanged=True,boundary_faces_unchanged=True,interface_faces_unchanged=True,parent_cells=len(owner) and len(parents)//8,new_cells=len(parents),new_rotating_cells=len(new_zone),source_sha256=sha(Path('twins/bionic-turbo-f1/cfd/star_cell_partition.py')))
assert audit['max_area_closure_m2']<1e-15 and audit['minimum_oriented_cell_volume_m3']>0 and audit['max_rotating_cell_flux_m3_s']<1e-18
case.mkdir(parents=True,exist_ok=False)
for prefix in ('0','system','constant'):
 for source in (parent/prefix).rglob('*'):
  if source.is_file():
   name=str(source.relative_to(parent));assert sha(source)==receipt['output_sha256'][name]
   target=case/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
shutil.copytree(case/'constant/polyMesh',case/'input/polyMesh')
def write_list(name,values):
 path=case/'constant/polyMesh'/name;text=path.read_text();match=re.search(r'\n\s*\d+\s*\n\(',text)
 if not match:raise ValueError('Unsupported native list')
 header=re.sub(r'\s*note\s+"[^"]*";','',text[:match.start()]);path.write_text(header+'\n'+str(len(values))+'\n(\n'+'\n'.join(values)+'\n)\n')
write_list('points',['('+' '.join(format(x,'.17g') for x in v)+')' for v in q]);write_list('faces',[str(len(f))+'('+' '.join(map(str,f))+')' for f in new]);write_list('owner',list(map(str,own)));write_list('neighbour',list(map(str,nei)))
path=case/'constant/polyMesh/boundary';delta=len(nei)-internal;path.write_text(re.sub(r'(startFace\s+)(\d+)',lambda m:m[1]+str(int(m[2])+delta),path.read_text()))
path=case/'constant/polyMesh/cellZones';path.write_text(zone_text[:m.start()]+f'cellLabels List<label>\n{len(new_zone)}\n(\n'+'\n'.join(map(str,new_zone))+'\n)'+zone_text[m.end():])
for path in (case/'constant/polyMesh/sets').iterdir():
 text=path.read_text()
 if re.search(r'class\s+cellSet\s*;',text):
  labels=ascii_list(text).astype(int);mapped=np.flatnonzero(np.isin(parents,labels));write_list('sets/'+path.name,list(map(str,mapped)))
 elif re.search(r'class\s+faceSet\s*;',text):
  # Old diagnostic face labels refer to the preserved input snapshot, not the new mesh.
  path.rename(case/('parent-diagnostic-'+path.name))
 else:raise ValueError('Unsupported set metadata')
assert np.array_equal(ascii_list((case/'constant/polyMesh/points').read_text(),True),q)
(case/'partition-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
np.save(case/'parent-cell-labels.npy',parents,allow_pickle=False)
manifest=dict(source_sha256=sha(Path(__file__)),parent_manifest_sha256=sha(parent/'manifest.json'),parent_receipt_sha256=sha(parent/'report.json'),partition_source_sha256=audit['source_sha256'],image=IMAGE,solver_launched=False,file_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
(case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; cd /case; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1'
execution=dict(timeout_seconds=240,cpus=1,memory_gib=2,container='bionic-star-partition-041',command=command)
(case/'execution.json').write_text(json.dumps(execution,indent=2)+'\n');started=time.monotonic()
r=subprocess.run(['docker','run','--name',execution['container'],'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 240 bash -c '+shlex.quote(command)],capture_output=True,text=True,timeout=270)
# checkMesh may regenerate diagnostic sets; prepared physical mesh and equations must remain exact.
assert all(sha(case/n)==h for n,h in manifest['file_sha256'].items() if not n.startswith('constant/polyMesh/sets/'))
log=(case/'log.checkMesh').read_text();receipt=dict(native_exit_code=r.returncode,stderr=r.stderr,elapsed_seconds=time.monotonic()-started,manifest_sha256=sha(case/'manifest.json'),execution_sha256=sha(case/'execution.json'),mesh_gate_passed='Mesh OK.' in log and 'Failed ' not in log,solver_launched=False,performance_ranking_authorized=False,output_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
(case/'report.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(audit));print(json.dumps({k:v for k,v in receipt.items() if k!='output_sha256'}))
