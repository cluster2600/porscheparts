"""Synthetic existing-region snap with fixed join and nonzero target offset."""
import json,os,shlex,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import IMAGE,sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');parent=root/'collar-split-065';base=root/'full-collar-063'
r=json.loads((parent/'report.json').read_text());assert all(sha(parent/n)==h for n,h in r['output_sha256'].items())
m=parent/'constant/domain1/polyMesh';p=ascii_list((m/'points').read_text(),True);faces=[np.array(f) for f in ascii_faces((m/'faces').read_text())];internal=13440
assert len(p)==13824 and len(faces)==27264
frozen=np.unique(np.concatenate(faces[20480:]));moving=np.setdiff1d(np.arange(len(p)),frozen)
assert len(frozen)==6912 and len(moving)==6912
# Synthetic offset is one eighth of the existing collar width; no real wall changes.
q=p.copy();ratio=1.01415140625;q[moving,:2]*=(1+(ratio-1)*7/8)/ratio
assert np.array_equal(q[frozen],p[frozen]) and np.all(np.linalg.norm(q[moving]-p[moving],axis=1)>0)
header=lambda n,c='dictionary':f'FoamFile {{version 2.0; format ascii; class {c}; object {n};}}\n'
vec=lambda x:' '.join(format(float(y),'.17g') for y in x)
stl=['solid walls']
for f in faces[internal:]:
 for j in range(1,len(f)-1):
  t=p[f[[0,j,j+1]]];normal=np.cross(t[1]-t[0],t[2]-t[0]);assert np.linalg.norm(normal)>0
  stl+=['facet normal '+vec(normal/np.linalg.norm(normal)),'outer loop',*['vertex '+vec(x) for x in t],'endloop','endfacet']
stl+=['endsolid walls'];config=(root/'snap-frozen-nosmooth-070/system/snappyHexMeshDict').read_text()
assert 'nSmoothPatch 0;' in config and 'castellatedMesh false;' in config
for name,snap in [('selective-initial-071',False),('selective-snap-072',True)]:
 case=root/name;assert not case.exists();case.mkdir();shutil.copytree(base/'system',case/'system');mesh=case/'constant/polyMesh';mesh.mkdir(parents=True)
 for n in ('faces','owner','neighbour'):shutil.copy2(m/n,mesh/n)
 (mesh/'points').write_text(header('points','vectorField')+str(len(q))+'\n(\n'+''.join('('+vec(v)+')\n' for v in q)+')\n')
 (mesh/'boundary').write_text(header('boundary','polyBoundaryMesh')+'1\n(\nwalls {type wall; nFaces 13824; startFace 13440;}\n)\n')
 for n in ('cellZones','faceZones'):(mesh/n).write_text(header(n,'regIOobject')+'0\n(\n)\n')
 (mesh/'pointZones').write_text(header('pointZones','regIOobject')+'1\n(\nfrozenPoints {type pointZone; pointLabels List<label> '+str(len(frozen))+'\n(\n'+'\n'.join(map(str,frozen))+'\n);}\n)\n')
 (case/'constant/triSurface').mkdir();(case/'constant/triSurface/walls.stl').write_text('\n'.join(stl)+'\n');(case/'system/snappyHexMeshDict').write_text(config)
 manifest=dict(parent=str(parent),parent_report_sha256=sha(parent/'report.json'),source_sha256=sha(Path(__file__)),image=IMAGE,synthetic_only=True,offset_fraction=1/8,original_patch_roles={'walls':'outer and end walls','domain1_to_rotorZone':'protected join now synthetic wall'},boundary_conversion='Two contiguous patches combined as walls; all face vertices and ownership retained; mapped metadata removed; no stale RegionAddressing copied.',frozen_point_labels=frozen.tolist(),moving_point_labels=moving.tolist(),file_sha256={str(x.relative_to(case)):sha(x) for x in case.rglob('*') if x.is_file()})
 (case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');initial=w/(name+'-inputs');shutil.copytree(case,initial)
 (case/'docker-before.txt').write_bytes(subprocess.check_output(['docker','ps','--format','{{.Names}} {{.Status}}']))
 command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; set -e; cd /case; '+('snappyHexMesh -overwrite > log.snappyHexMesh 2>&1; ' if snap else '')+'checkMesh -allTopology -allGeometry > log.checkMesh 2>&1'
 container='bionic-'+name
 cmd=['docker','run','--name',container,'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 240 bash -c '+shlex.quote(command)]
 (case/'execution.json').write_text(json.dumps(dict(command=cmd,timeout_seconds=240),indent=2)+'\n');start=time.monotonic()
 with (case/'container.log').open('x') as f:result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=270)
 state=json.loads(subprocess.check_output(['docker','inspect',container]))[0]['State'];log=(case/'log.checkMesh').read_text() if (case/'log.checkMesh').exists() else ''
 report=dict(native_exit_code=result.returncode,elapsed_seconds=time.monotonic()-start,container_state=state,mesh_gate_passed='Mesh OK.' in log and 'Failed ' not in log,solver_launched=False,output_sha256={str(x.relative_to(case)):sha(x) for x in case.rglob('*') if x.is_file()})
 (case/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(name,{k:v for k,v in report.items() if k!='output_sha256'},flush=True)
 assert report['mesh_gate_passed'], 'Stop before next operation on rejected input'
