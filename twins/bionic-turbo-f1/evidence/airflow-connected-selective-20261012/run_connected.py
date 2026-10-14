"""Selective boundary witness retaining full collar connectivity."""
import json,os,shlex,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import IMAGE,sha
from uniform_interface_projection import read_mesh
from audit_diagnostic import ascii_list
w=Path(__file__).parent;parent=Path('work/bionic-airflow-20261012/full-collar-063')
r=json.loads((parent/'report.json').read_text());assert r['mesh_gate_passed'] and r['native_exit_code']==0
assert all(sha(parent/n)==h for n,h in r['output_sha256'].items())
p,faces,interface,internal=read_mesh(parent);boundary=faces[internal:];ids=np.unique(np.concatenate(boundary))
assert len(ids)==20992 and len(interface)==6784
split=Path('work/bionic-airflow-20261012/collar-split-065');sr=json.loads((split/'report.json').read_text())
assert all(sha(split/n)==h for n,h in sr['output_sha256'].items())
m=split/'constant/domain1/polyMesh';mapping=ascii_list((m/'pointRegionAddressing').read_text()).astype(int)
assert np.array_equal(p[mapping],ascii_list((m/'points').read_text(),True))
prior=json.loads(Path('work/bionic-selective-boundary-20261012/selective-initial-071-inputs/manifest.json').read_text())
outer=mapping[prior['moving_point_labels']];protected=np.setdiff1d(ids,outer)
assert len(outer)==6912 and len(protected)==14080
q=p.copy();ratio=1.01415140625;q[outer,:2]*=(1+(ratio-1)*7/8)/ratio
assert np.array_equal(q[protected],p[protected]) and np.all(np.linalg.norm(q[outer]-p[outer],axis=1)>0)
# Coplanar parent quads are triangulated only as a target surface, not as mesh faces.
triangles=[]
for face in boundary:
 for j in range(1,len(face)-1):
  t=p[[face[0],face[j],face[j+1]]];normal=np.cross(t[1]-t[0],t[2]-t[0]);assert np.linalg.norm(normal)>0
  triangles.append((normal/np.linalg.norm(normal),t))
vec=lambda x:' '.join(format(float(y),'.17g') for y in x)
stl='solid walls\n'+''.join('facet normal '+vec(n)+'\n outer loop\n'+''.join(' vertex '+vec(x)+'\n' for x in t)+' endloop\nendfacet\n' for n,t in triangles)+'endsolid walls\n'
header=lambda n,c='dictionary':f'FoamFile {{version 2.0; format ascii; class {c}; object {n};}}\n'
config=header('snappyHexMeshDict')+'''castellatedMesh false; snap true; addLayers false;
geometry {walls {type triSurfaceMesh; file "walls.stl";}}
castellatedMeshControls {
 maxLocalCells 6000000; maxGlobalCells 6000000; minRefinementCells 0;
 maxLoadUnbalance .1; nCellsBetweenLevels 3; features ();
 refinementSurfaces {walls {level (0 0); patchInfo {type wall;}}}
 resolveFeatureAngle 30; refinementRegions {};
 locationInMesh (0.0315 0 0); allowFreeStandingZoneFaces true;
}
snapControls {nSmoothPatch 0; nSmoothInternal 3; tolerance 1.5; nSolveIter 100; nRelaxIter 8;
 nFeatureSnapIter 0; implicitFeatureSnap false; explicitFeatureSnap false; multiRegionFeatureSnap false;
 strictRegionSnap true;}
addLayersControls {}
meshQualityControls {#includeEtc "caseDicts/mesh/generation/meshQualityDict.cfg"
 maxBoundarySkewness 3.5; minTetQuality 1e-12;}
mergeTolerance 1e-7;
'''
plans=[('connected-initial-073','bionic-connected-initial-073',False),('connected-snap-074','bionic-connected-snap-074',True)]
for name,container,snap in plans:
 frozen=protected.tolist()
 case=Path('work/bionic-airflow-20261012')/name;assert not case.exists();case.mkdir()
 for directory in ('constant','system'):shutil.copytree(parent/directory,case/directory)
 (case/'constant/polyMesh/points').write_text(header('points','vectorField')+str(len(q))+'\n(\n'+''.join('('+vec(v)+')\n' for v in q)+')\n')
 (case/'constant/triSurface').mkdir();(case/'constant/triSurface/walls.stl').write_text(stl)
 (case/'system/snappyHexMeshDict').write_text(config)
 (case/'constant/polyMesh/pointZones').write_text(header('pointZones','regIOobject')+'1\n(\nfrozenPoints {type pointZone; pointLabels List<label> '+str(len(frozen))+'\n(\n'+'\n'.join(map(str,frozen))+'\n);}\n)\n')
 (case/'manifest.json').write_text(json.dumps(dict(image=IMAGE,parent=str(parent),parent_report_sha256=sha(parent/'report.json'),source_sha256=sha(Path(__file__)),synthetic_snap_only=True,solver_admission_granted=False,outer_point_labels=outer.tolist(),protected_point_labels=protected.tolist(),offset_fraction=1/8,file_sha256={str(x.relative_to(case)):sha(x) for x in case.rglob('*') if x.is_file()}),indent=2)+'\n')
 shutil.copytree(case,w/(name+'-inputs'))
 # Record active containers before each distinct bounded operation; do not stop any.
 (case/'docker-before.txt').write_bytes(subprocess.check_output(['docker','ps','--format','{{.Names}} {{.Status}}']))
 command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; set -e; cd /case; '+('snappyHexMesh -overwrite > log.snappyHexMesh 2>&1; ' if snap else '')+'checkMesh -allTopology -allGeometry > log.checkMesh 2>&1'
 cmd=['docker','run','--name',container,'--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 240 bash -c '+shlex.quote(command)]
 (case/'execution.json').write_text(json.dumps(dict(command=cmd,timeout_seconds=240),indent=2)+'\n');start=time.monotonic()
 with (case/'container.log').open('x') as f:result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=270)
 state=json.loads(subprocess.check_output(['docker','inspect',container]))[0]['State'];log=(case/'log.checkMesh').read_text() if (case/'log.checkMesh').exists() else ''
 report=dict(native_exit_code=result.returncode,elapsed_seconds=time.monotonic()-start,container_state=state,mesh_gate_passed='Mesh OK.' in log and 'Failed ' not in log,solver_launched=False,output_sha256={str(x.relative_to(case)):sha(x) for x in case.rglob('*') if x.is_file()})
 (case/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(name,json.dumps({k:v for k,v in report.items() if k!='output_sha256'}),flush=True)

 if not snap:assert report['mesh_gate_passed'], 'No projection on rejected input'
