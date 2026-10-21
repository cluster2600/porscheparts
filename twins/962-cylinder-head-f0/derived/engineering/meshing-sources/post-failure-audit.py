import hashlib,importlib.util,json,math,signal,time
from pathlib import Path
import gmsh,numpy as np
signal.alarm(120)
started=time.monotonic()
root=Path.cwd()
folder=root/'work/962-engineering/indexed-volume-hxt-001'
source=root/'twins/962-cylinder-head-f0/source/mesh_head.py'
spec=importlib.util.spec_from_file_location('head_volume_audit_helpers',source)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
mesh=folder/'failed-current-mesh.msh'
mesh_sha=m.sha(mesh)
stl,retained,pins=m.bound_head(95)
triangles,points,faces=m.read_binary_stl(stl);del triangles
result=dict(scope='saved_failed_mesh_diagnostic_without_remeshing',mesh_sha256=mesh_sha,source_sha256=m.sha(source),audit_source_sha256=m.sha(Path(__file__)),source_input_hashes=pins,gmsh_version=gmsh.__version__,geometry_gate_passed=False,engineering_accepted=False,manufacturing_authorized=False)
gmsh.initialize([],readConfigFiles=False,run=False)
gmsh.option.setNumber('General.Terminal',0)
gmsh.option.setNumber('General.NumThreads',4)
try:
 gmsh.open(str(mesh))
 node_tags,xyz,_=gmsh.model.mesh.getNodes();order=np.argsort(node_tags)
 node_tags=np.asarray(node_tags)[order];xyz=np.asarray(xyz).reshape(-1,3)[order]
 selected=np.searchsorted(node_tags,np.arange(1,len(points)+1))
 result['original_surface_coordinates_exact']=bool(np.array_equal(node_tags[selected],np.arange(1,len(points)+1)) and np.array_equal(xyz[selected],points))
 added=node_tags>len(points)
 result['added_node_tags']=node_tags[added].tolist();result['added_node_coordinates_mm']=xyz[added].tolist()
 types,tags,nodes=gmsh.model.mesh.getElements(2)
 if list(types)!=[2]:raise ValueError('Unexpected surface element types')
 actual=np.asarray(nodes[0]).reshape(-1,3)
 result['source_triangles']=len(faces);result['saved_triangles']=len(actual)
 def keys(a):
  a=np.ascontiguousarray(m.canonical_oriented(a).astype('<u8'))
  return a.view(np.dtype([('a','<u8'),('b','<u8'),('c','<u8')])).reshape(-1)
 before=keys(faces+1);after=keys(actual)
 result['original_oriented_triangles_missing']=len(np.setdiff1d(before,after,assume_unique=True))
 result['new_oriented_triangles']=len(np.setdiff1d(after,before,assume_unique=True))
 del before,after
 coordinates,cells,element_tags,_=m.volume_arrays(gmsh)
 result['tetrahedra']=len(cells)
 result['quality']={name:m.distribution(gmsh.model.mesh.getElementQualities(element_tags,measure)) for name,measure in [('minimum_jacobian','minDetJac'),('native_volume_mm3','volume'),('minimum_SICN','minSICN')]}
 volumes=m.tetra_volumes(coordinates,cells)
 result['quality']['independent_signed_volume_mm3']=m.distribution(volumes)
 result['summed_tetra_volume_mm3']=math.fsum(volumes)
 result['retained_source_volume_mm3']=retained['volume_mm3']
 result['volume_relative_error']=abs(result['summed_tetra_volume_mm3']/retained['volume_mm3']-1)
 result['unchanged_volume_bookkeeping_bound']=m.VOLUME_RELATIVE_BOUND
 result['all_tetra_metric_samples_positive_finite']=all(v['nonpositive_count']==0 for v in result['quality'].values())
 result['actual_saved_tetra_boundary_vs_saved_surface']=m.tetra_boundary(cells,np.searchsorted(node_tags,actual))
 result['status']='saved_mesh_diagnostic_complete_original_surface_identity_failed'
except Exception as error:
 result['status']='saved_mesh_diagnostic_failed';result['error']=type(error).__name__+': '+str(error)
finally:
 gmsh.finalize()
 result['mesh_unchanged']=m.sha(mesh)==mesh_sha
 result['wall_s']=time.monotonic()-started
 with (folder/'post-failure-audit.json').open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
print(json.dumps(result,indent=2,allow_nan=False))
signal.alarm(0)
