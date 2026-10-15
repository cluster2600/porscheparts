"""Native outer-row bisection on projected synthetic subdomain; no flow solver."""
import json,os,re,shlex,shutil,subprocess,sys,time,tarfile,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import IMAGE,sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');split=root/'radial-split-078';snap=root/'radial-selective-snap-081'
def verify(c):
 r=json.loads((c/'report.json').read_text());assert r['native_exit_code']==0 and not r['container_state']['OOMKilled'];assert all(sha(c/n)==h for n,h in r['output_sha256'].items());return r
for c in (split,snap):verify(c)
assert verify(snap)['mesh_gate_passed']
archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz');assert sha(archive)=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
with tarfile.open(archive) as tar:
 member=next(x for x in tar.getmembers() if x.name.endswith('/refineWallLayer/refineWallLayer.C'));data=tar.extractfile(member).read()
(w/'refineWallLayer.C').write_bytes(data)
(w/'source-reference.json').write_text(json.dumps(dict(url='https://dl.openfoam.com/source/v2406/OpenFOAM-v2406.tgz',archive_sha256=sha(archive),member=member.name,member_sha256=hashlib.sha256(data).hexdigest(),scope='Patch-point adjacent cells and edges leaving selected patch; weight0.5 is midpoint bisection; no generic frozen-boundary guarantee.'),indent=2)+'\n')
# Outer patch selection uses the original geometric stations and native domain faces.
m=split/'constant/domain1/polyMesh';p=ascii_list((m/'points').read_text(),True);f=[np.array(x,int) for x in ascii_faces((m/'faces').read_text())];o=ascii_list((m/'owner').read_text()).astype(int);internal=len(ascii_list((m/'neighbour').read_text()))
spec=json.loads((root/'full-collar-063/construction.json').read_text());R=np.interp(p[:,2],spec['stations_m'],spec['radii_m']);ratio=np.linalg.norm(p[:,:2],axis=1)/R;q=spec['radial_ratios'][2];levels=np.array([1,(1+q)/2,q]);assert np.max(np.min(abs(ratio[:,None]-levels),axis=1))<1e-12
outerpoint=abs(ratio-q)<1e-12;ids=np.array([i for i in range(internal,len(f)) if outerpoint[f[i]].all()]);assert len(ids)==6784
outercells=np.unique(o[ids]);assert len(outercells)==6784
# Candidate cells at patch vertices must equal the intended single outer row.
patchpoints=np.unique(np.concatenate([f[i] for i in ids]));candidate=set()
n=ascii_list((m/'neighbour').read_text()).astype(int)
for i,face in enumerate(f):
 if np.isin(face,patchpoints).any():
  candidate.add(int(o[i]))
  if i<len(n):candidate.add(int(n[i]))
assert candidate==set(outercells)
np0=ascii_list((snap/'constant/polyMesh/points').read_text(),True);nf=list(ascii_faces((snap/'constant/polyMesh/faces').read_text()));assert all(np.array_equal(x,y) for x,y in zip(f,nf))
core=('points','faces','owner','neighbour','boundary','cellZones','faceZones','pointZones')
def copy_mesh(src,dest):
 dest.mkdir(parents=True)
 for name in core:
  if (src/name).exists():shutil.copy2(src/name,dest/name)
def execute(case,command,parents):
 active=subprocess.check_output(['docker','ps','--format','{{.Names}} {{.Status}}']).decode();assert not any(s.startswith('bionic-') for s in active.splitlines()),active
 man=dict(source_sha256=sha(Path(__file__)),image=IMAGE,parents={str(c):sha(c/'report.json') for c in parents},outer_faces_source078=ids.tolist(),outer_cells_source078=outercells.tolist(),patch_vertex_candidate_cells_verified=True,edge_fraction=.5,synthetic_only=True,file_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
 (case/'manifest.json').write_text(json.dumps(man,indent=2)+'\n');shutil.copytree(case,w/(case.name+'-inputs'));(case/'docker-before.txt').write_text(active)
 command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; set -e; cd /case; '+command
 container='bionic-'+case.name;cmd=['docker','run','--name',container,'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 240 bash -c '+shlex.quote(command)]
 (case/'execution.json').write_text(json.dumps(dict(command=cmd,timeout_seconds=240),indent=2)+'\n');began=time.monotonic()
 with (case/'container.log').open('x') as out:r=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT,timeout=270)
 state=json.loads(subprocess.check_output(['docker','inspect',container]))[0]['State'];log=(case/'log.checkMesh').read_text() if (case/'log.checkMesh').exists() else ''
 report=dict(native_exit_code=r.returncode,elapsed_seconds=time.monotonic()-began,container_state=state,mesh_gate_passed='Mesh OK.' in log and 'Failed ' not in log,solver_launched=False,output_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
 (case/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(case.name,json.dumps({k:v for k,v in report.items() if k!='output_sha256'}),flush=True);return report
case=root/'outer-wall-patch-085';assert not case.exists();case.mkdir();copy_mesh(snap/'constant/polyMesh',case/'constant/polyMesh');shutil.copytree(snap/'system',case/'system')
sets=case/'constant/polyMesh/sets';sets.mkdir();(sets/'outerFaces').write_text('FoamFile {version 2.0; format ascii; class faceSet; object outerFaces;}\n'+str(len(ids))+'\n(\n'+'\n'.join(map(str,ids))+'\n)\n')
(case/'system/createPatchDict').write_text('FoamFile {version 2.0; format ascii; class dictionary; object createPatchDict;}\npointSync false; patches ({name outerWall; patchInfo {type wall;} constructFrom set; set outerFaces;});\n')
r=execute(case,'createPatch -overwrite > log.createPatch 2>&1; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1',[split,snap]);assert r['mesh_gate_passed']
parent=case;verify(parent);case=root/'outer-wall-bisect-086';assert not case.exists();case.mkdir();copy_mesh(parent/'constant/polyMesh',case/'constant/polyMesh');shutil.copytree(parent/'system',case/'system')
# Do not copy sets or processor addressing which the native utility would remove.
assert not (case/'constant/polyMesh/sets').exists() and not list((case/'constant/polyMesh').glob('*Addressing'))
execute(case,"refineWallLayer '(outerWall)' 0.5 -overwrite > log.refineWallLayer 2>&1; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1",[parent])
