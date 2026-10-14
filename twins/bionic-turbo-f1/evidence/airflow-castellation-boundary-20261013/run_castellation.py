"""One nonzero outer surface refinement request, no snap or layers."""
import json,re,shutil
from pathlib import Path
from run_native import execute,sha
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');parent=root/'outer-wall-bisect-086';target=root/'castellation-target-089'
for c in (parent,target):
 r=json.loads((c/'report.json').read_text());assert r['native_exit_code']==0 and not r['container_state']['OOMKilled'];assert all(sha(c/n)==h for n,h in r['output_sha256'].items())
s=(target/'log.surfaceCheck').read_text();assert 'Surface is closed. All edges connected to two faces.' in s and 'Number of unconnected parts : 1' in s and 'Triangles    : 28672 in 4 region(s)' in s and 'Surface has no illegal triangles.' in s
for name,count in [('rear',768),('front',768),('join',13568),('outer',13568)]:assert re.search(r'\d+\s+'+name+r'\s+'+str(count)+r'\s',s)
proof=json.loads((w/'target-preparation.json').read_text());assert sha(target/'constant/triSurface/collar.stl')==proof['surface_sha256']
case=root/'regional-castellation-090';assert not case.exists();(case/'constant/polyMesh').mkdir(parents=True)
core=('points','faces','owner','neighbour','boundary','cellZones','faceZones','pointZones')
for n in core:shutil.copy2(parent/'constant/polyMesh'/n,case/'constant/polyMesh'/n)
shutil.copytree(parent/'system',case/'system');shutil.copytree(target/'constant/triSurface',case/'constant/triSurface')
p=case/'system/snappyHexMeshDict';s=p.read_text();s=s.replace('castellatedMesh false; snap true; addLayers false;','castellatedMesh true; snap false; addLayers false;')
s=s.replace('geometry {walls {type triSurfaceMesh; file "walls.stl";}}','geometry {collar {type triSurfaceMesh; file "collar.stl";}}')
s=s.replace('refinementSurfaces {walls {level (0 0); patchInfo {type wall;}}}','refinementSurfaces {collar {level (0 0); patchInfo {type wall;} regions {rear {level (0 0);} front {level (0 0);} join {level (0 0);} outer {level (1 1);}}}')
s,n=re.subn(r'locationInMesh\s*\([^)]*\);','locationInMesh ('+' '.join(format(x,'.17g') for x in proof['location_in_mesh'])+');',s);assert n==1
s+='\ndebugFlags (mesh);\nwriteFlags (scalarLevels);\n';p.write_text(s)
assert 'writePrecision 16;' in (case/'system/controlDict').read_text()
(w/'protocol.json').write_text(json.dumps(dict(parent_mesh='086',surface_gate='089',source_reading_published_before_preparation=True,preflight_receipt_sha256=sha(Path('work/bionic-airflow-delivery-20261013-castellation-boundary/preflight-verified.json')),outer_level=[1,1],other_levels=[0,0],level_rationale='Smallest nonzero isotropic refinement request to exercise boundary transitions; not a solver adjustment or sweep.',snap=False,layers=False,quality_unchanged=True,nCellsBetweenLevels=3,debug_mesh_snapshots=True,initial_mesh_core_byte_identical=True,synthetic_only=True),indent=2)+'\n')
execute(case,'snappyHexMesh -overwrite > log.snappyHexMesh 2>&1; checkMesh -allTopology -allGeometry > log.checkMesh 2>&1',[parent,target])
