"""Read the existing saved MSH only; never generate, optimize or write geometry."""
from pathlib import Path
import hashlib,json,math,platform,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
array_sha=lambda a:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
contract=json.loads((OUT/'frozen-contract.json').read_text())
for name,h in contract['input_hashes'].items():
 if sha(ROOT/name)!=h:raise ValueError('Bound saved-readback input drift: '+name)
w=ROOT/'work/962-engineering/atomic-cavity-volume-hxt-001';worker=json.loads((w/'worker-report.json').read_text());receipt=json.loads((w/'receipt.json').read_text());admission=json.loads((w/'surface-admission.json').read_text())
for name,h in admission['input_hashes'].items():
 if sha(ROOT/name)!=h:raise ValueError('Surface-admission evidence changed: '+name)
for name,h in receipt['source_sha256s'].items():
 if sha(ROOT/name)!=h or sha(w/'source-snapshots'/Path(name).name)!=h:raise ValueError('Executed source/snapshot changed')
import gmsh
if gmsh.__version__!='4.15.2' or platform.machine()!='arm64' or sha(Path(gmsh.__file__))!=contract['runtime']['gmsh_module_sha256'] or sha(Path(gmsh.lib._name))!=contract['runtime']['libgmsh_sha256'] or sha(Path(sys.executable).resolve())!=contract['runtime']['python_executable_sha256']:raise ValueError('Pinned native Gmsh reader required')
report=dict(status='reading_saved_mesh',meshing_optimization_or_solve_calls=0,engineering_accepted=False,manufacturing_authorized=False,runtime=dict(gmsh=gmsh.__version__,numpy=np.__version__,machine=platform.machine(),executable_sha256=sha(Path(sys.executable).resolve()),gmsh_module_sha256=sha(Path(gmsh.__file__)),libgmsh_sha256=sha(Path(gmsh.lib._name))))
start=time.monotonic();initialized=False
try:
 gmsh.initialize([],readConfigFiles=False,run=False);initialized=True;gmsh.option.setNumber('General.Terminal',0);gmsh.option.setNumber('General.NumThreads',2)
 gmsh.open(str(w/'head-volume.msh'))
 tags,xyz,_=gmsh.model.mesh.getNodes();order=np.argsort(tags);tags=np.asarray(tags)[order];xyz=np.asarray(xyz).reshape(-1,3)[order]
 types,tet_tags,tet_nodes=gmsh.model.mesh.getElements(3)
 if list(types)!=[4]:raise ValueError('Linear tetrahedra only required')
 tet_tags=np.asarray(tet_tags[0]);tet_nodes=np.asarray(tet_nodes[0]).reshape(-1,4);tetorder=np.argsort(tet_tags)
 report.update(actual_mesh_nodes=len(tags),actual_tetrahedra=len(tet_tags),sorted_node_tags_sha256=array_sha(tags),sorted_coordinates_sha256=array_sha(xyz),sorted_tetra_tags_sha256=array_sha(tet_tags[tetorder]),tagged_tetra_connectivity_sha256=array_sha(tet_nodes[tetorder]))
 for key in ['sorted_node_tags_sha256','sorted_coordinates_sha256','sorted_tetra_tags_sha256','tagged_tetra_connectivity_sha256']:
  if report[key]!=worker[key]:raise ValueError('Saved-file tagged array differs from worker: '+key)
 candidate=ROOT/contract['candidate']
 with candidate.open('rb') as stream:header=stream.read(24)
 import struct
 nv,nf=struct.unpack_from('<QQ',header,8)
 p=np.memmap(candidate,mode='r',dtype='<f8',offset=24,shape=(nv,3));f=np.memmap(candidate,mode='r',dtype='<u8',offset=24+24*nv,shape=(nf,3))
 expected=np.arange(1,nv+1,dtype=np.uint64);indices=np.searchsorted(tags,expected)
 if np.any(indices>=len(tags)) or not np.array_equal(tags[indices],expected) or not np.array_equal(xyz[indices],p):raise ValueError('Actual saved boundary coordinates differ')
 ft,face_tags,face_nodes=gmsh.model.mesh.getElements(2)
 if list(ft)!=[2]:raise ValueError('Explicit linear boundary triangles required')
 face_order=np.argsort(face_tags[0]);actual_faces=np.asarray(face_nodes[0]).reshape(-1,3)[face_order]
 if not np.array_equal(actual_faces,f+1):raise ValueError('Actual saved explicit tagged boundary connectivity differs')
 report.update(actual_explicit_surface_triangles=len(actual_faces),exact_source_boundary_coordinates=True,exact_sorted_explicit_surface_connectivity=True,explicit_surface_elements_are_not_an_independent_tetra_boundary_incidence_audit=True)
 del actual_faces,face_nodes,face_tags,face_order
 native={};bad_tetrahedra=[]
 for name,measure in [('SICN','minSICN'),('Jacobian','minDetJac'),('native_volume_mm3','volume')]:
  row=dict(count=0,minimum=None,maximum=None,nonpositive_count=0,below_point1_count=0 if name=='SICN' else None)
  for offset in range(0,len(tet_tags),100000):
   q=np.asarray(gmsh.model.mesh.getElementQualities(tet_tags[offset:offset+100000],measure))
   if len(q)!=len(tet_tags[offset:offset+100000]) or not np.isfinite(q).all():raise ValueError('Incomplete/nonfinite native metric')
   row['count']+=len(q);row['minimum']=float(q.min()) if row['minimum'] is None else min(row['minimum'],float(q.min()));row['maximum']=float(q.max()) if row['maximum'] is None else max(row['maximum'],float(q.max()));row['nonpositive_count']+=int(np.count_nonzero(q<=0))
   if name=='SICN':
    row['below_point1_count']+=int(np.count_nonzero(q<.1))
    for local in np.flatnonzero(q<=0):
     index=offset+int(local);conn=tet_nodes[index];ids=np.searchsorted(tags,conn)
     if np.any(ids>=len(tags)) or not np.array_equal(tags[ids],conn):raise ValueError('Nonpositive-SICN cell references missing node')
     bad_tetrahedra.append(dict(native_array_index=index,tetrahedron_tag=int(tet_tags[index]),node_tags=conn.tolist(),coordinates_mm=xyz[ids].tolist(),SICN=float(q[local]),all_nodes_original_boundary_tags=bool(np.all((conn>=1)&(conn<=nv)))))
     if len(bad_tetrahedra)>contract['diagnostic_maximum_nonpositive_cells']:raise ValueError('Unexpected diagnostic cell count; preserve refusal without truncating evidence')
   else:
    for bad in bad_tetrahedra:
     index=bad['native_array_index']
     if offset<=index<offset+len(q):bad[name]=float(q[index-offset])
  native[name]=row
 report['direct_native_quality_extrema']=native
 volumes=np.empty(len(tet_tags),dtype=np.float64);referenced=np.zeros(len(tags),dtype=bool)
 for offset in range(0,len(tet_tags),100000):
  conn=tet_nodes[offset:offset+100000];ids=np.searchsorted(tags,conn)
  if np.any(ids>=len(tags)) or not np.array_equal(tags[ids],conn):raise ValueError('Tet references missing saved node')
  referenced[ids.ravel()]=True;v=xyz[ids];volumes[offset:offset+len(conn)]=np.einsum('ij,ij->i',v[:,1]-v[:,0],np.cross(v[:,2]-v[:,0],v[:,3]-v[:,0]))/6
 if not np.isfinite(volumes).all():raise ValueError('Nonfinite independent saved-file volume')
 total=math.fsum(volumes);report.update(independent_signed_volume_mm3=dict(count=len(volumes),minimum=float(volumes.min()),maximum=float(volumes.max()),nonpositive_count=int(np.count_nonzero(volumes<=0)),sum=total,relative_error_to_candidate=abs(total/worker['candidate_volume_reference_mm3']-1)),actual_tetra_referenced_nodes=int(np.count_nonzero(referenced)),actual_unreferenced_mesh_nodes=int(np.count_nonzero(~referenced)),actual_referenced_interior_nodes=int(np.count_nonzero(referenced & ((tags<1)|(tags>nv)))))
 for bad in bad_tetrahedra:bad['independent_signed_volume_mm3']=float(volumes[bad['native_array_index']])
 report.update(nonpositive_SICN_tetrahedra=bad_tetrahedra,fixed_boundary_only_nonpositive_cells=all(bad['all_nodes_original_boundary_tags'] for bad in bad_tetrahedra))
 report.update(retained_only_not_repeated=dict(tetra_exterior_incidence=worker['actual_tetra_boundary'],internal_face_orientation=worker['internal_tetra_face_orientation']),SICN_point1_gate_passed=native['SICN']['minimum']>=.1 and native['SICN']['nonpositive_count']==0,thermal_resolution_established=False,status='direct_saved_file_readback_completed')
finally:
 if initialized:gmsh.finalize()
for name,h in contract['input_hashes'].items():
 if sha(ROOT/name)!=h:raise ValueError('Bound saved-readback input drift after query')
for name,h in admission['input_hashes'].items():
 if sha(ROOT/name)!=h:raise ValueError('Surface-admission evidence changed after query: '+name)
for name,h in contract['external_runtime_hashes'].items():
 if sha(Path(name))!=h:raise ValueError('Pinned runtime changed after query')
report.update(bound_inputs_unchanged=True,readback_wall_seconds=time.monotonic()-start)
with (OUT/'readback-report.json').open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
print(json.dumps({k:report[k] for k in ['status','actual_mesh_nodes','actual_tetrahedra','actual_referenced_interior_nodes','SICN_point1_gate_passed','readback_wall_seconds']}))
