"""Repatch, merge and stitch refined projected fixed region with intact rotating region."""
import json,os,re,shlex,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import IMAGE,sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');split=root/'radial-split-078';snap=root/'outer-wall-bisect-086'
def verify(c):
 r=json.loads((c/'report.json').read_text());assert r['native_exit_code']==0 and not r['container_state']['OOMKilled'];assert all(sha(c/n)==h for n,h in r['output_sha256'].items());return r
for c in (split,snap):verify(c)
assert verify(snap)['mesh_gate_passed']
core=('points','faces','owner','neighbour','boundary','cellZones','faceZones','pointZones')
def copy_mesh(src,dest):
 dest.mkdir(parents=True)
 for n in core:
  if (src/n).exists():shutil.copy2(src/n,dest/n)
def execute(case,command,parents):
 active=subprocess.check_output(['docker','ps','--format','{{.Names}} {{.Status}}']).decode();assert not any(s.startswith('bionic-') for s in active.splitlines()),active
 manifest=dict(image=IMAGE,source_sha256=sha(Path(__file__)),parents={str(c):sha(c/'report.json') for c in parents},synthetic_only=True,file_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
 (case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');shutil.copytree(case,w/(case.name+'-inputs'));(case/'docker-before.txt').write_text(active)
 command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; set -e; cd /case; '+command
 container='bionic-'+case.name;cmd=['docker','run','--name',container,'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 240 bash -c '+shlex.quote(command)]
 (case/'execution.json').write_text(json.dumps(dict(command=cmd,timeout_seconds=240),indent=2)+'\n');start=time.monotonic()
 with (case/'container.log').open('x') as out:r=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT,timeout=270)
 state=json.loads(subprocess.check_output(['docker','inspect',container]))[0]['State'];log=(case/'log.checkMesh').read_text() if (case/'log.checkMesh').exists() else ''
 report=dict(native_exit_code=r.returncode,elapsed_seconds=time.monotonic()-start,container_state=state,solver_launched=False,mesh_gate_passed='Mesh OK.' in log and 'Failed ' not in log,output_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
 (case/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(case.name,json.dumps({k:v for k,v in report.items() if k!='output_sha256'}),flush=True);assert report['mesh_gate_passed'] and r.returncode==0
# Select refined join by exact point correspondence with the named source078 patch.
from scipy.spatial import cKDTree
sm=split/'constant/domain1/polyMesh';nm=snap/'constant/polyMesh'
sf=[np.array(x,int) for x in ascii_faces((sm/'faces').read_text())];nf=[np.array(x,int) for x in ascii_faces((nm/'faces').read_text())]
p=ascii_list((sm/'points').read_text(),True);q=ascii_list((nm/'points').read_text(),True)
b=re.search(r'domain1_to_rotorZone\s*\{(.*?)\}',(sm/'boundary').read_text(),re.S)[1];start=int(re.search(r'startFace\s+(\d+)',b)[1]);count=int(re.search(r'nFaces\s+(\d+)',b)[1]);assert count==6784
joinpoints=np.unique(np.concatenate(sf[start:start+count]));dist,ix=cKDTree(q).query(p[joinpoints]);assert np.all(dist==0) and len(set(ix))==len(joinpoints)==6912
pm=dict(zip(joinpoints,ix))
def cyc(face):
 f=tuple(map(int,face));return min(f[i:]+f[:i] for i in range(len(f)))
expected={cyc([pm[x] for x in face]) for face in sf[start:start+count]};assert len(expected)==6784
internal=len(ascii_list((nm/'neighbour').read_text()));ids=[i for i in range(internal,len(nf)) if cyc(nf[i]) in expected];assert len(ids)==6784 and {cyc(nf[i]) for i in ids}==expected
case=root/'refined-wall-patches-087';assert not case.exists();case.mkdir();copy_mesh(nm,case/'constant/polyMesh');shutil.copytree(snap/'system',case/'system')
# No inherited addressing or face sets; only this verified native selection.
sets=case/'constant/polyMesh/sets';sets.mkdir();(sets/'joinFaces').write_text('FoamFile {version 2.0; format ascii; class faceSet; object joinFaces;}\n'+str(count)+'\n(\n'+'\n'.join(map(str,ids))+'\n)\n')
(case/'system/createPatchDict').write_text('FoamFile {version 2.0; format ascii; class dictionary; object createPatchDict;}\npointSync false; patches ({name domain1_to_rotorZone; patchInfo {type wall;} constructFrom set; set joinFaces;});\n')
execute(case,'createPatch -overwrite > log.createPatch 2>&1; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1',[split,snap])
patchcase=case;verify(patchcase)
case=root/'refined-wall-stitch-088';assert not case.exists();case.mkdir()
for src,dest in ((split/'constant/rotorZone/polyMesh',case),(patchcase/'constant/polyMesh',case/'add')):
 copy_mesh(src,dest/'constant/polyMesh');shutil.copytree(snap/'system',dest/'system')
# Replace only obsolete region-coupling metadata with an ordinary stitchable wall.
bpath=case/'constant/polyMesh/boundary';s=bpath.read_text();assert s.count('type            mappedWall;')==1
s=s.replace('type            mappedWall;','type            wall;')
for key in ('sampleMode','sampleRegion','samplePatch'):s,n=re.subn(r'^\s*'+key+r'\s+[^;]+;\n','',s,flags=re.M);assert n==1
bpath.write_text(s)
(case/'system/createPatchDict').write_text('FoamFile {version 2.0; format ascii; class dictionary; object createPatchDict;}\npointSync false; patches ();\n')
execute(case,'mergeMeshes /case /case/add -overwrite > log.mergeMeshes 2>&1; cp -a constant/polyMesh merged-polyMesh; stitchMesh -perfect -overwrite rotorZone_to_domain1 domain1_to_rotorZone > log.stitchMesh 2>&1; cp -a constant/polyMesh stitched-polyMesh; createPatch -overwrite > log.createPatch 2>&1; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1',[split,patchcase])
