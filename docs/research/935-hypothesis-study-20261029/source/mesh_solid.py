"""Generate a conforming Gmsh tetrahedral mesh of an explicit study surface."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import gmsh
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('input')
parser.add_argument('output', type=Path)
parser.add_argument('--size', type=float, default=2.0)
parser.add_argument('--algorithm', type=int, default=10)
parser.add_argument('--threads', type=int, default=16)
args = parser.parse_args()
args.output.mkdir()
started = time.monotonic()
gmsh.initialize()
gmsh.option.setNumber('General.NumThreads', args.threads)
gmsh.option.setNumber('Mesh.Algorithm3D', args.algorithm)
gmsh.option.setNumber('Mesh.MeshSizeMax', args.size)
gmsh.option.setNumber('Mesh.MeshSizeMin', 0)
gmsh.option.setNumber('Mesh.Binary', 1)
gmsh.model.add('conditional_935_study')
if args.input == 'cube':
    v = np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]],float)
    f = np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])
    source_hash = None
else:
    path = Path(args.input)
    with path.open('rb') as s:
        source_hash = hashlib.file_digest(s,'sha256').hexdigest()
    arrays = np.load(path, allow_pickle=False)
    v, f = arrays['vertices'], arrays['triangles']
gmsh.model.addDiscreteEntity(2, 1)
gmsh.model.mesh.addNodes(2, 1, np.arange(1,len(v)+1), v.ravel())
gmsh.model.mesh.addElementsByType(1, 2, np.arange(1,len(f)+1), (f+1).ravel())
loop = gmsh.model.geo.addSurfaceLoop([1])
volume = gmsh.model.geo.addVolume([loop])
gmsh.model.geo.synchronize()
gmsh.model.addPhysicalGroup(3, [volume], 1, 'assumed_solid')
gmsh.model.addPhysicalGroup(2, [1], 2, 'observed_and_inferred_boundary')
gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary', 0)
gmsh.option.setNumber('Mesh.MeshSizeFromPoints', 0)
gmsh.option.setNumber('Mesh.MeshSizeFromCurvature', 0)
field = gmsh.model.mesh.field.add('MathEval')
gmsh.model.mesh.field.setString(field, 'F', str(args.size))
gmsh.model.mesh.field.setAsBackgroundMesh(field)
gmsh.model.mesh.generate(3)
gmsh.write(str(args.output/'solid.msh'))
node_tags, xyz, _ = gmsh.model.mesh.getNodes()
element_tags, node_ids = gmsh.model.mesh.getElementsByType(4)
if not len(element_tags):
    raise RuntimeError('No tetrahedral volume elements generated')
order = np.argsort(node_tags)
nodes = xyz.reshape(-1,3)[order]
tets = np.searchsorted(node_tags[order], node_ids).reshape(-1,4)
tri_tags, tri_nodes = gmsh.model.mesh.getElementsByType(2)
triangles = np.searchsorted(node_tags[order], tri_nodes).reshape(-1,3)
np.savez_compressed(args.output/'solid.npz', nodes=nodes,tets=tets,boundary=triangles)
det = np.linalg.det(nodes[tets[:,1:]] - nodes[tets[:,0,None]])
quality = gmsh.model.mesh.getElementQualities(element_tags, 'minSICN')
report = {'source_sha256':source_hash, 'gmsh_version':gmsh.__version__,
          'units':'mm','nodes':len(nodes),'tetrahedra':len(tets),'boundary_triangles':len(triangles),
          'signed_volume_mm3':float(det.sum()/6),'nonpositive_tetrahedra':int((det<=0).sum()),
          'quality_minSICN_quantiles':np.quantile(quality,[0,.01,.5,1]).tolist(),
          'elapsed_seconds':time.monotonic()-started,'physical_geometry_accepted':False}
(args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
gmsh.finalize()
