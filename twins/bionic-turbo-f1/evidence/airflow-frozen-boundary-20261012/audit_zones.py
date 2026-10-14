"""Check zone labels, boundaries, STL target and pinned snap parameters."""
import hashlib,json,re,sys,tarfile
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from uniform_interface_projection import read_mesh
w=Path(__file__).parent;base=Path('work/bionic-airflow-20261012');parent=base/'full-collar-063'
p,faces,interface,internal=read_mesh(parent);boundaryids=np.unique(np.concatenate(faces[internal:]))
def labels(path,name,entry):
 s=path.read_text();m=re.search(name+r'\s*\{.*?'+entry+r'\s+List<label>\s*(\d+)\s*\((.*?)\)',s,re.S);assert m
 a=np.fromstring(m[2],sep=' ',dtype=int);assert len(a)==int(m[1]);return a
original=labels(parent/'constant/polyMesh/cellZones','rotorZone','cellLabels')
records={}
for name in ('snap-control-068','snap-frozen-069','snap-frozen-nosmooth-070'):
 case=base/name;r=json.loads((case/'report.json').read_text());assert all(sha(case/n)==h for n,h in r['output_sha256'].items())
 assert np.array_equal(original,labels(case/'constant/polyMesh/cellZones','rotorZone','cellLabels'))
 frozen=labels(case/'constant/polyMesh/pointZones','frozenPoints','pointLabels')
 assert np.array_equal(frozen,[] if name=='snap-control-068' else boundaryids)
 # Same patch dictionary content aside from serialized location/header.
 def patches(path):return re.findall(r'(walls|defaultFaces)\s*\{(.*?)\}',path.read_text(),re.S)
 assert patches(case/'constant/polyMesh/boundary')==patches(parent/'constant/polyMesh/boundary')
 cfg=(case/'system/snappyHexMeshDict').read_text();basecfg=(base/'baseline-profile-mesh-031/system/snappyHexMeshDict').read_text()
 block=lambda s,k:re.search(k+r'\s*\{(.*?)\}',s,re.S)[1]
 assert block(cfg,'meshQualityControls')==block(basecfg,'meshQualityControls')
 assert block(cfg,'snapControls').replace('nSmoothPatch 0;','nSmoothPatch 3;')==block(basecfg,'snapControls')
 records[name]=dict(rotor_labels_unchanged=True,patches_unchanged=True,frozen_point_count=len(frozen),mesh_quality_controls_unchanged=True,snap_controls_from_031=True)
# Target STL carries the exact parent face triangulation and signed normals.
stl=(base/'snap-control-068/constant/triSurface/walls.stl').read_text()
target=np.array([[float(v) for v in line.split()[1:]] for line in stl.splitlines() if line.strip().startswith('vertex ')])
expected=np.array([p[j] for f in faces[internal:] for i in range(1,len(f)-1) for j in (f[0],f[i],f[i+1])]);assert np.array_equal(target,expected)
result=dict(source_sha256=sha(Path(__file__)),target_vertices_exactly_parent_triangulation=True,records=records,not_a_physical_turbo_mesh=True,no_refinement_or_layers=True)
with (w/'zone-target-readback.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
