import importlib.util,json,signal,time
from pathlib import Path
import gmsh,numpy as np
signal.alarm(90)
started=time.monotonic()
root=Path.cwd();folder=root/'work/962-engineering/indexed-volume-hxt-001'
source=root/'twins/962-cylinder-head-f0/source/mesh_head.py'
spec=importlib.util.spec_from_file_location('canonical_head_audit',source)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
previous=folder/'post-failure-audit.json';data=json.loads(previous.read_text())
mesh=folder/'failed-current-mesh.msh'
assert data['mesh_sha256']==m.sha(mesh) and data['mesh_unchanged']
assert data['original_oriented_triangles_missing']==0 and data['new_oriented_triangles']==0
assert data['all_tetra_metric_samples_positive_finite']
assert data['volume_relative_error']<=m.VOLUME_RELATIVE_BOUND
assert data['actual_saved_tetra_boundary_vs_saved_surface']['exact_oriented_tetra_boundary']
stl,retained,pins=m.bound_head(95)
_,points,faces=m.read_binary_stl(stl)
gmsh.initialize([],readConfigFiles=False,run=False);gmsh.option.setNumber('General.Terminal',0)
try:
 gmsh.open(str(mesh))
 check=m.surface_roundtrip(gmsh,points,faces,exact_tagged_order=False)
 types,tags,nodes=gmsh.model.mesh.getElements(2);order=np.argsort(tags[0])
 actual=np.asarray(nodes[0]).reshape(-1,3)[order]
 def rotate(a):return np.take_along_axis(a,(a.argmin(axis=1)[:,None]+np.arange(3))%3,axis=1)
 tagged_oriented_match=np.all(rotate(actual)==rotate(faces+1),axis=1)
 raw_row_match=np.all(actual==faces+1,axis=1)
 result=dict(status='exact_surface_positive_volume_geometric_gate_passed_not_engineering_accepted',mesh_sha256=m.sha(mesh),canonical_surface_check=check,tagged_rows_with_identical_oriented_triangle=int(np.sum(tagged_oriented_match)),tagged_rows_with_identical_raw_vertex_order=int(np.sum(raw_row_match)),surface_triangle_count=len(faces),prior_diagnostic_path=str(previous.relative_to(root)),prior_diagnostic_sha256=m.sha(previous),quality=data['quality'],tetrahedra=data['tetrahedra'],summed_tetra_volume_mm3=data['summed_tetra_volume_mm3'],retained_source_volume_mm3=retained['volume_mm3'],volume_relative_error=data['volume_relative_error'],volume_bookkeeping_bound=m.VOLUME_RELATIVE_BOUND,actual_tetra_boundary=data['actual_saved_tetra_boundary_vs_saved_surface'],input_hashes=pins,current_audit_source_sha256=m.sha(Path(__file__)),qualification=dict(geometric_volume_gate_passed=True,engineering_accepted=False,mesh_convergence_established=False,strength_validated=False,manufacturing_authorized=False),interpretation='The original failed receipt is retained. Its exact-tagged-order assertion rejected a geometrically unchanged oriented triangle set; this separate read-only audit accepts only the geometric bookkeeping gate. Extremely poor SICN prevents engineering mesh acceptance.')
finally:gmsh.finalize()
result['mesh_unchanged']=m.sha(mesh)==data['mesh_sha256'];result['wall_s']=time.monotonic()-started
with (folder/'canonical-audit.json').open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
print(json.dumps({k:result[k] for k in ['status','canonical_surface_check','tagged_rows_with_identical_oriented_triangle','tagged_rows_with_identical_raw_vertex_order','surface_triangle_count','wall_s']},indent=2))
signal.alarm(0)
