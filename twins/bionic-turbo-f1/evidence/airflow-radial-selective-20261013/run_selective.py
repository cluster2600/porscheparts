"""Bounded isolated snap witness with exact join and end-plane protection."""
import json,os,re,shlex,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import IMAGE,sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');parent=root/'radial-isolated-079';split=root/'radial-split-078';config_parent=root/'connected-nosmooth-075'
for c in (parent,split,config_parent):
 r=json.loads((c/'report.json').read_text());assert r['native_exit_code']==0 and all(sha(c/n)==h for n,h in r['output_sha256'].items())
assert json.loads((parent/'report.json').read_text())['mesh_gate_passed']
m=parent/'constant/polyMesh';p=ascii_list((m/'points').read_text(),True);f=[np.array(x,int) for x in ascii_faces((m/'faces').read_text())];internal=len(ascii_list((m/'neighbour').read_text()))
s=split/'constant/domain1/polyMesh';assert np.array_equal(p,ascii_list((s/'points').read_text(),True))
join=re.search(r'domain1_to_rotorZone\s*\{(.*?)\}',(s/'boundary').read_text(),re.S)[1];start=int(re.search(r'startFace\s+(\d+)',join)[1]);count=int(re.search(r'nFaces\s+(\d+)',join)[1])
jp=np.unique(np.concatenate(f[start:start+count]));boundary=np.unique(np.concatenate(f[internal:]));ends=np.flatnonzero((p[:,2]==p[:,2].min())|(p[:,2]==p[:,2].max()))
fixed=np.union1d(jp,ends);moving=np.setdiff1d(boundary,fixed);inside=np.setdiff1d(np.arange(len(p)),boundary)
assert len(jp)==6912 and len(ends)==768 and len(fixed)==7424 and len(moving)==6656 and len(inside)==6656
q=p.copy();ratio=1.01415140625;q[moving,:2]*=(1+(ratio-1)*7/8)/ratio
assert np.array_equal(q[fixed],p[fixed]) and np.array_equal(q[inside],p[inside])
assert np.all(np.linalg.norm(q[moving]-p[moving],axis=1)>0)
header=lambda n,c='dictionary':f'FoamFile {{version 2.0; format ascii; class {c}; object {n};}}\n'
vec=lambda x:' '.join(format(float(y),'.17g') for y in x)
tri=[]
for face in f[internal:]:
 for j in range(1,len(face)-1):
  t=p[face[[0,j,j+1]]];normal=np.cross(t[1]-t[0],t[2]-t[0]);assert np.linalg.norm(normal)>0
  tri.append((normal/np.linalg.norm(normal),t))
stl='solid walls\n'+''.join('facet normal '+vec(n)+'\nouter loop\n'+''.join('vertex '+vec(x)+'\n' for x in t)+'endloop\nendfacet\n' for n,t in tri)+'endsolid walls\n'
config=(config_parent/'system/snappyHexMeshDict').read_text();assert 'nSmoothPatch 0;' in config and 'nSolveIter 0;' in config
for name,snap in (('radial-selective-initial-080',False),('radial-selective-snap-081',True)):
 active=subprocess.check_output(['docker','ps','--format','{{.Names}} {{.Status}}']).decode();assert not any(line.startswith('bionic-') for line in active.splitlines()),active
 case=root/name;assert not case.exists();case.mkdir()
 for directory in ('constant','system'):shutil.copytree(parent/directory,case/directory)
 (case/'constant/polyMesh/points').write_text(header('points','vectorField')+str(len(q))+'\n(\n'+''.join('('+vec(v)+')\n' for v in q)+')\n')
 (case/'constant/polyMesh/pointZones').write_text(header('pointZones','regIOobject')+'1\n(\nfrozenPoints {type pointZone; pointLabels List<label> '+str(len(fixed))+'\n(\n'+'\n'.join(map(str,fixed))+'\n);}\n)\n')
 (case/'constant/triSurface').mkdir();(case/'constant/triSurface/walls.stl').write_text(stl);(case/'system/snappyHexMeshDict').write_text(config)
 manifest=dict(image=IMAGE,parent=str(parent),parent_report_sha256=sha(parent/'report.json'),split_report_sha256=sha(split/'report.json'),config_parent=str(config_parent),source_sha256=sha(Path(__file__)),synthetic_only=True,join_face_start=start,join_face_count=count,join_point_labels=jp.tolist(),end_point_labels=ends.tolist(),protected_point_labels=fixed.tolist(),moving_point_labels=moving.tolist(),interior_point_labels=inside.tolist(),offset_fraction=1/8,file_sha256={str(x.relative_to(case)):sha(x) for x in case.rglob('*') if x.is_file()})
 (case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');shutil.copytree(case,w/(name+'-inputs'));(case/'docker-before.txt').write_text(active)
 command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; set -e; cd /case; '+('snappyHexMesh -overwrite > log.snappyHexMesh 2>&1; ' if snap else '')+'checkMesh -allTopology -allGeometry > log.checkMesh 2>&1'
 container='bionic-'+name;cmd=['docker','run','--name',container,'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 240 bash -c '+shlex.quote(command)]
 (case/'execution.json').write_text(json.dumps(dict(command=cmd,timeout_seconds=240),indent=2)+'\n');began=time.monotonic()
 with (case/'container.log').open('x') as out:r=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT,timeout=270)
 state=json.loads(subprocess.check_output(['docker','inspect',container]))[0]['State'];log=(case/'log.checkMesh').read_text() if (case/'log.checkMesh').exists() else ''
 report=dict(native_exit_code=r.returncode,elapsed_seconds=time.monotonic()-began,container_state=state,mesh_gate_passed='Mesh OK.' in log and 'Failed ' not in log,solver_launched=False,output_sha256={str(x.relative_to(case)):sha(x) for x in case.rglob('*') if x.is_file()})
 (case/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(name,json.dumps({k:v for k,v in report.items() if k!='output_sha256'}),flush=True)
 if not snap:assert report['mesh_gate_passed'],'No snap on rejected initial mesh'
