"""Synthetic homothetic annulus with native collapsed-hex transition prisms."""
import json, math, os, shlex, subprocess, sys, time
from collections import Counter
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha, IMAGE
w=Path(__file__).parent;case=Path('work/bionic-airflow-20261012/conformal-transition-057')
assert not case.exists()
# Synthetic ratios are not measured turbo dimensions or a certified corridor.
sectors=128;stations=np.linspace(.006,.007,11);ratios=(63/64,1,33/32)
xy=[]
for ratio,n in ((ratios[0],sectors),(ratios[1],sectors),(ratios[2],2*sectors)):
 xy.extend((ratio*math.cos(2*math.pi*i/n),ratio*math.sin(2*math.pi*i/n)) for i in range(n))
stride=len(xy);vertices=[(x*(.032+.4*(z-.006)),y*(.032+.4*(z-.006)),z) for z in stations for x,y in xy]
polygons=[]
for i in range(sectors):
 j=(i+1)%sectors;a=sectors+i;b=sectors+j;d=2*sectors+2*i;m=d+1;c=2*sectors+(2*i+2)%(2*sectors)
 polygons.extend([(True,[i,a,b,j]),(False,[a,m,b]),(False,[a,d,m]),(False,[b,m,c])])
# Positive orientation and exact shared edge cancellation independently gate the stencil.
edge=Counter()
for zone,poly in polygons:
 p=np.array([xy[i] for i in poly]);area=np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1))/2
 assert area>0
 for a,b in zip(poly,poly[1:]+poly[:1]):edge[a,b]+=1
boundary=[(a,b) for (a,b),n in edge.items() if not edge[b,a]]
assert len(boundary)==3*sectors and all(n==1 for n in edge.values())
assert all(edge[b,a]==1 or (a,b) in boundary for a,b in edge)
blocks=[];walls=[];interface=[]
for k in range(len(stations)-1):
 for zone,poly in polygons:
  lo=[i+k*stride for i in poly];hi=[i+stride for i in lo]
  v=lo+hi if len(poly)==4 else lo+[lo[-1]]+hi+[hi[-1]]
  blocks.append('hex ('+' '.join(map(str,v))+')'+(' rotorZone' if zone else '')+' (1 1 1) simpleGrading (1 1 1)')
  if k==0:walls.append(lo[::-1])
  if k==len(stations)-2:walls.append(hi)
 for a,b in boundary:
  a+=k*stride;b+=k*stride;walls.append([a,b,b+stride,a+stride])
 for i in range(sectors):
  a=k*stride+sectors+i;b=k*stride+sectors+(i+1)%sectors;interface.append([a,b,b+stride,a+stride])
case.mkdir();(case/'system').mkdir();(case/'constant').mkdir()
header=lambda name:f'FoamFile {{version 2.0; format ascii; class dictionary; object {name};}}\n'
vec=lambda p:'('+' '.join(format(x,'.17g') if isinstance(x,float) else str(x) for x in p)+')'
(case/'system/blockMeshDict').write_text(header('blockMeshDict')+'vertices ('+' '.join(map(vec,vertices))+');\nblocks ('+'\n'.join(blocks)+');\nedges ();\nboundary (walls {type wall; faces ('+' '.join(map(vec,walls))+');});\n')
(case/'system/controlDict').write_text(header('controlDict')+'application blockMesh; startFrom startTime; startTime 0; stopAt endTime; endTime 0; deltaT 1e-7; writeControl timeStep; writeInterval 1; writeFormat ascii; writePrecision 16; runTimeModifiable false;\n')
(case/'system/fvSchemes').write_text(header('fvSchemes')+'ddtSchemes {default Euler;} gradSchemes {default Gauss linear;} divSchemes {default none;} laplacianSchemes {default Gauss linear corrected;} interpolationSchemes {default linear;} snGradSchemes {default corrected;}\n')
(case/'system/fvSolution').write_text(header('fvSolution')+'solvers {}\n')
(case/'construction.json').write_text(json.dumps(dict(synthetic_only=True,physical_turbo_geometry_present=False,sectors=sectors,stations_m=stations.tolist(),r_at_z6_m=.032,slope=.4,radial_ratios=ratios,expected_cells=len(blocks),expected_rotating_cells=sectors*10,expected_interface_faces=interface,vertices=vertices,walls=walls,source_sha256=sha(Path(__file__))),indent=2)+'\n')
(case/'manifest.json').write_text(json.dumps(dict(image=IMAGE,file_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()}),indent=2)+'\n')
command='source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1; set -e; cd /case; blockMesh > log.blockMesh 2>&1; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1'
cmd=['docker','run','--name','bionic-conformal-transition-057','--pull=never','--platform','linux/arm64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--cpus','1','--memory','2g','--tmpfs','/tmp:rw,nosuid,size=128m','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,source={case.resolve()},target=/case','--entrypoint','/bin/bash',IMAGE,'-c','timeout --signal=TERM --kill-after=10s 240 bash -c '+shlex.quote(command)]
(case/'execution.json').write_text(json.dumps(dict(command=cmd,timeout_seconds=240),indent=2)+'\n');started=time.monotonic()
with (case/'container.log').open('x') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=270)
log=(case/'log.checkMesh').read_text() if (case/'log.checkMesh').exists() else ''
result=dict(native_exit_code=r.returncode,elapsed_seconds=time.monotonic()-started,manifest_sha256=sha(case/'manifest.json'),execution_sha256=sha(case/'execution.json'),mesh_gate_passed='Mesh OK.' in log and 'Failed ' not in log,solver_launched=False,performance_ranking_authorized=False,output_sha256={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
(case/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='output_sha256'}))
