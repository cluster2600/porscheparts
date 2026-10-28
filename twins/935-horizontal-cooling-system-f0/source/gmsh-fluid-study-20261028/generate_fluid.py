"""Private exploratory Gmsh trial on the conditional root-0.7 fluid PLC."""
import hashlib
import json
from pathlib import Path
import sys
import time
import gmsh
import numpy as np

source = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).resolve()
if output.exists() or output.parent != source.parent:
    raise SystemExit('Use a fresh private sibling output')
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
known_inputs = {
    '9fcd93a5c54ebfc98b8cd86d4550e3a416d3e62fb217e5ebfb67eb2f2a9f2085': (447868, 895732),
    '9dcfef8c123e63016271e3977fdd2d01b21997a94c3343e5e2d6f79198794c8a': (447868, 895732),
    'e71fc12382db13129166d4a37cc006a45238134ceaf4d32e3873b44b23d611f5': (447861, 895718),
    '7bb4f474ff0423747784c258dab79ab01e917b648c137654d335e381ce195936': (447852, 895700),
    '35e1427ed6cfdd858cca31803525a23bb65efa2258e349f06cc9bc7ab2bf7509': (447826, 895648),
}
if source_hash not in known_inputs:
    raise SystemExit('PLC input hash mismatch')
with np.load(source) as p:
    vertices = p['vertices'].copy()
    triangles = p['triangles'].copy()
    markers = p['markers'].copy()
if (len(vertices), len(triangles)) != known_inputs[source_hash] or set(markers) != {1, 2, 3, 4}:
    raise SystemExit('PLC shape/markers mismatch')
output.mkdir(mode=0o700)
gmsh.initialize()
gmsh.option.setNumber('General.Terminal', 1)
gmsh.model.add('root0p7-fluid')
for marker in range(1,5):
    gmsh.model.addDiscreteEntity(2, marker)
gmsh.model.mesh.addNodes(2, 1, np.arange(1,len(vertices)+1), vertices.ravel())
for marker in range(1,5):
    ids=np.flatnonzero(markers==marker)
    gmsh.model.mesh.addElementsByType(marker, 2, ids+1, (triangles[ids]+1).ravel())
t0=time.monotonic()
gmsh.model.mesh.createTopology(False,True)
entities=gmsh.model.getEntities(2)
counts={str(tag):len(gmsh.model.mesh.getElementsByType(2,tag)[0]) for dim,tag in entities}
print('topology',entities,counts, 'seconds',time.monotonic()-t0,flush=True)
if entities != [(2,1),(2,2),(2,3),(2,4)] or [counts[str(i)] for i in range(1,5)] != [2304,2304,12394,len(triangles)-17002]:
    raise SystemExit('Gmsh changed boundary patch entities')
if len(sys.argv)>3 and sys.argv[3]=='topology':
    gmsh.finalize()
    raise SystemExit(0)
outer=gmsh.model.geo.addSurfaceLoop([1,2,3])
inner=gmsh.model.geo.addSurfaceLoop([4])
vol=gmsh.model.geo.addVolume([outer,inner])
gmsh.model.geo.synchronize()
gmsh.model.addPhysicalGroup(3,[vol],1)
for marker in range(1,5):
    gmsh.model.addPhysicalGroup(2,[marker],marker)
gmsh.option.setNumber('Mesh.Algorithm3D',1)
gmsh.option.setNumber('Mesh.MeshSizeMin',0.002)
gmsh.option.setNumber('Mesh.MeshSizeMax',0.020)
gmsh.option.setNumber('Mesh.Optimize',1)
gmsh.option.setNumber('Mesh.SaveAll',1)
gmsh.model.mesh.generate(3)
nodes=gmsh.model.mesh.getNodes()[0]
tets=gmsh.model.mesh.getElementsByType(4)[0]
report={'source_sha256':source_hash,'gmsh_version':gmsh.option.getString('General.Version'),'nodes':len(nodes),'tetrahedra':len(tets),'patch_elements_after':{str(tag):len(gmsh.model.mesh.getElementsByType(2,tag)[0]) for dim,tag in entities},'wall_seconds':time.monotonic()-t0,'status':'exploratory_not_CFD_admitted'}
(output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
gmsh.write(str(output/'fluid.msh'))
print(json.dumps(report),flush=True)
gmsh.finalize()
