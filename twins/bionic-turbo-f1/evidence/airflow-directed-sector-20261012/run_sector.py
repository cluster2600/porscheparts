"""Bounded native admission of coarse and angularly refined sector partitions."""
import json,os,shlex,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha,IMAGE
from uniform_interface_projection import read_mesh,metrics
from internal_face_facets import facet_internal,balance
from star_cell_partition import partition
from directed_sector_witness import sector_grid,hex_topology,write_mesh
factor,number=map(int,sys.argv[1:]);assert (factor,number) in ((1,42),(8,43))
parent=Path('work/bionic-airflow-20261012/projected-interface-035');case=Path('work/bionic-airflow-20261012')/f'directed-sector-{number:03d}'
assert not case.exists();prior=json.loads((parent/'manifest.json').read_text());receipt=json.loads((parent/'report.json').read_text());assert receipt['mesh_gate_passed'] and receipt['native_exit_code']==0 and receipt['manifest_sha256']==sha(parent/'manifest.json')
p,_,_,_=read_mesh(parent);profile=prior['profile'];grid,audit=sector_grid(p,profile['nodes_z_radius_mm'],profile['shell_half_width_mm'],profile['sectors'],factor);points=grid.reshape(-1,3)
f,o,n,z=hex_topology(grid);flags=np.zeros(int(o.max())+1,bool);flags[z]=True;selected=np.flatnonzero(flags[o[:len(n)]]^flags[n]);audit['initial_interface']=metrics(points,[f[i] for i in selected],10471.975511966)
assert audit['initial_interface']['max_normal_frame_speed_m_s']<1e-8 and audit['initial_interface']['max_plane_distance_m']<1e-12
ff,oo,nn,parents,facet=facet_internal(points,f,o,n,selected);q,faces,owner,neighbour,zone,parent_cells=partition(points,ff,oo,nn,z)
flags=np.zeros(len(parent_cells),bool);flags[zone]=True;new_selected=np.flatnonzero(flags[owner[:len(neighbour)]]^flags[neighbour]);assert {tuple(faces[i]) for i in new_selected}=={tuple(f[i]) for i in selected}
assert faces[len(neighbour):]==f[len(n):] and np.array_equal(q[:len(points)],points)
audit['before_partition'],_=balance(points,f,o,n,10471.975511966,z);audit['after_partition'],_=balance(q,faces,owner,neighbour,10471.975511966,zone);audit['final_interface']=metrics(q,[faces[i] for i in new_selected],10471.975511966)
assert audit['after_partition']['max_rotating_cell_flux_m3_s']<1e-18 and audit['after_partition']['minimum_oriented_cell_volume_m3']>0
case.mkdir(parents=True,exist_ok=False)
for prefix in ('0','system','constant'):
 for source in (parent/prefix).rglob('*'):
  if source.is_file() and 'polyMesh' not in source.parts:
   name=str(source.relative_to(parent));assert sha(source)==receipt['output_sha256'][name]
   target=case/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
write_mesh(case/'input/base-polyMesh',points,f,o,n,z);write_mesh(case/'input/faceted-polyMesh',points,ff,oo,nn,z);write_mesh(case/'constant/polyMesh',q,faces,owner,neighbour,zone)
np.save(case/'parent-cell-labels.npy',parent_cells,allow_pickle=False)
audit.update(source_sha256=sha(Path('twins/bionic-turbo-f1/cfd/directed_sector_witness.py')),physical_turbo_geometry_present=False,faceted_faces=len(facet['split_original_faces']),equations_unchanged=True,mesh_generated_directly=True,old_blockMeshDict_unused=True)
(case/'geometry-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
manifest=dict(source_sha256=sha(Path(__file__)),parent_manifest_sha256=sha(parent/'manifest.json'),parent_receipt_sha256=sha(parent/'report.json'),geometry_source_sha256=audit['source_sha256'],faceter_source_sha256=sha(Path('twins/bionic-turbo-f1/cfd/internal_face_facets.py')),partition_source_sha256=sha(Path('twins/bionic-turbo-f1/cfd/star_cell_partition.py')),factor=factor,profile=profile,image=IMAGE,solver_launched=False,file_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
(case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; cd /case; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1'
execution=dict(timeout_seconds=240,cpus=1,memory_gib=2,container=f'bionic-directed-sector-{number:03d}',command=command)
(case/'execution.json').write_text(json.dumps(execution,indent=2)+'\n');started=time.monotonic()
r=subprocess.run(['docker','run','--name',execution['container'],'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 240 bash -c '+shlex.quote(command)],capture_output=True,text=True,timeout=270)
assert all(sha(case/n)==h for n,h in manifest['file_sha256'].items())
log=(case/'log.checkMesh').read_text();receipt=dict(native_exit_code=r.returncode,stderr=r.stderr,elapsed_seconds=time.monotonic()-started,manifest_sha256=sha(case/'manifest.json'),execution_sha256=sha(case/'execution.json'),mesh_gate_passed='Mesh OK.' in log and 'Failed ' not in log,solver_launched=False,performance_ranking_authorized=False,output_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
(case/'report.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(audit));print(json.dumps({k:v for k,v in receipt.items() if k!='output_sha256'}))
