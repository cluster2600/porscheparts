"""Read the existing saved MSH only; never generate, optimize or write geometry."""
from pathlib import Path
import hashlib,json,math,platform,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
array_sha=lambda a:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def classify_positive_poor_chunk(values,tetra_tags,node_rows,offset,boundary_count,counts,representatives):
 """Complete participation bins; retain minimum(SICN,tag) per class."""
 if type(boundary_count) is not int or boundary_count<=0 or type(offset) is not int or offset<0:
  raise ValueError('Exact positive boundary count and nonnegative offset required')
 if set(counts)!={str(k) for k in range(5)} or any(type(v) is not int or v<0 for v in counts.values()):
  raise ValueError('Five exact nonnegative integer counters required')
 q=np.asarray(values);et=np.asarray(tetra_tags);en=np.asarray(node_rows)
 if (q.ndim!=1 or q.dtype.kind not in 'iuf' or not np.isfinite(q).all()
     or et.shape!=q.shape or et.dtype.kind not in 'iu' or np.any(et<=0)
     or en.shape!=(len(q),4) or en.dtype.kind not in 'iu' or np.any(en<=0)):
  raise ValueError('Complete finite SICN and integer tetrahedron/node rows required')
 positive=np.flatnonzero((q>0)&(q<.1));connections=en[positive]
 boundary_counts=np.count_nonzero((connections>=1)&(connections<=boundary_count),axis=1)
 for boundary_nodes in range(5):
  local=positive[boundary_counts==boundary_nodes];key=str(boundary_nodes)
  counts[key]+=len(local)
  if not len(local):continue
  minimum=float(q[local].min());ties=local[q[local]==minimum]
  chosen=int(ties[np.argmin(et[ties])]);tag=int(et[chosen])
  previous=representatives.get(key)
  if previous is not None and (minimum,tag)>=(previous['SICN'],previous['tetrahedron_tag']):continue
  representatives[key]=dict(native_array_index=offset+chosen,tetrahedron_tag=tag,SICN=minimum,
   original_boundary_node_count=boundary_nodes,interior_node_count=4-boundary_nodes)

def optimizer_after_proof(worker,receipt,contract):
 """Select the one actual optimized worker's after proof, never a reader alias."""
 if (receipt.get('returncode')!=2 or receipt.get('stop_reason') is not None
     or receipt.get('bound_inputs_unchanged') is not True or receipt.get('worker_report')!=worker
     or worker.get('optimizer_returned') is not True or worker.get('element_cache_refresh_completed') is not True
     or worker.get('saved_mesh_identity_exact') is not True
     or receipt.get('mesh_sha256')!=contract['MSH_sha256'] or worker.get('mesh_sha256')!=contract['MSH_sha256']
     or receipt.get('mesh_bytes')!=contract['MSH_bytes'] or worker.get('mesh_bytes')!=contract['MSH_bytes']
     or worker.get('candidate_sha256')!=contract['candidate_sha256']):
  raise ValueError('Exact completed optimized-worker after proof required')
 proof=worker['after'];n=proof['tetrahedra'];quality=proof['quality'];keys={'sorted_node_tags_sha256','sorted_coordinates_sha256','sorted_tetra_tags_sha256','tagged_tetra_connectivity_sha256'}
 if (type(n) is not int or n<=0 or set(proof['array_sha256s'])!=keys
     or set(quality)!={'minimum_jacobian','native_volume_mm3','minimum_SICN','independent_signed_volume_mm3'}
     or any(type(row.get('count')) is not int or row['count']!=n or type(row.get('nonpositive_count')) is not int for row in quality.values())
     or quality['minimum_SICN']['below_point1_count']-quality['minimum_SICN']['nonpositive_count']!=contract['expected_positive_poor_total']
     or quality['minimum_SICN']['nonpositive_count']!=contract['diagnostic_maximum_nonpositive_cells']):
  raise ValueError('Complete actual worker-after arrays, metric counts and poor-cell baseline required')
 return proof


def require_after_match(report,proof,expected_positive_poor_total):
 """Require direct full saved-file observations to match the single worker proof."""
 for observed,expected in [('actual_mesh_nodes','total_mesh_nodes'),('actual_tetrahedra','tetrahedra'),('actual_tetra_referenced_nodes','tetra_referenced_nodes'),('actual_unreferenced_mesh_nodes','unreferenced_mesh_nodes'),('actual_referenced_interior_nodes','tetra_referenced_interior_nodes')]:
  if type(report[observed]) is not int or report[observed]!=proof[expected]:raise ValueError('Saved node/tetrahedron/reference counts differ from worker.after')
 fields=['count','minimum','maximum','p01','p05','p50','p95','p99','nonpositive_count']
 for name,key in [('SICN','minimum_SICN'),('Jacobian','minimum_jacobian'),('native_volume_mm3','native_volume_mm3')]:
  observed=report['direct_native_quality_extrema'][name];expected=proof['quality'][key]
  if any(observed[k]!=expected[k] for k in [*fields,'array_sha256']):raise ValueError('Full saved native metric differs from worker.after: '+name)
  if name=='SICN' and observed['below_point1_count']!=expected['below_point1_count']:raise ValueError('SICN below-point1 count differs from worker.after')
 observed=report['independent_signed_volume_mm3'];expected=proof['quality']['independent_signed_volume_mm3']
 if (any(observed[k]!=expected[k] for k in fields) or observed['sum']!=proof['summed_tetra_volume_mm3'] or observed['relative_error_to_candidate']!=proof['volume_relative_error']):
  raise ValueError('Independent saved signed-volume distribution/sum differs from worker.after')
 if report['positive_poor_SICN_cells']['total']!=expected_positive_poor_total:raise ValueError('Exact current positive-poor partition required')


def classifications(core,gmsh,node_tags,boundary_count):
    np=core.np;dimensions=np.full(len(node_tags),-1,dtype=np.int8)
    entity_tags=np.zeros(len(node_tags),dtype=np.int64);periodic=[]
    for dim,tag in gmsh.model.getEntities():
        if dim in (1,2):
            masters=gmsh.model.mesh.getPeriodic(dim,[tag])
            master,nodes,node_masters,transform=gmsh.model.mesh.getPeriodicNodes(dim,tag,True)
            if list(masters)!=[tag] or master!=tag or len(nodes) or len(node_masters) or len(transform):
                raise ValueError("Curve/surface periodic mappings are forbidden")
            periodic.append([dim,tag])
        tags=np.asarray(gmsh.model.mesh.getNodes(dim,tag,False,False)[0])
        indices=np.searchsorted(node_tags,tags)
        if (len(np.unique(tags))!=len(tags) or np.any(indices>=len(node_tags))
                or not np.array_equal(node_tags[indices],tags) or np.any(dimensions[indices]!=-1)):
            raise ValueError("Unique complete node classification required")
        dimensions[indices]=dim;entity_tags[indices]=tag
    boundary=node_tags<=boundary_count
    if (np.any(dimensions<0) or np.count_nonzero(boundary)!=boundary_count
            or np.any(dimensions[boundary]>=3) or np.any(dimensions[~boundary]!=3)):
        raise ValueError("Fixed boundary nodes must classify below dim3 and interior nodes at dim3")
    return dict(node_classification_dimensions_sha256=core.array_sha(dimensions),
        node_classification_entity_tags_sha256=core.array_sha(entity_tags),
        boundary_node_classification_dimensions_sha256=core.array_sha(dimensions[boundary]),
        boundary_node_classification_entity_tags_sha256=core.array_sha(entity_tags[boundary]),
        node_counts_by_classification_dimension={str(d):int(np.count_nonzero(dimensions==d)) for d in range(4)},
        no_curve_or_surface_periodic_mapping=True,periodic_query_dimensions=[1,2],periodic_entities_checked=periodic)


def movable_from_poor_rows(poor_rows,interior_tags,boundary_count):
 """Only poor-cell members in the freshly proved dim3 tag set are variables."""
 if (type(boundary_count) is not int or boundary_count<=0
     or any(type(t) is not int or t<=boundary_count for t in interior_tags)
     or interior_tags!=sorted(set(interior_tags))):
  raise ValueError('Exact positive boundary count and sorted unique interior tags required')
 interior=set(interior_tags);members=set()
 for row in poor_rows:
  if len(row)!=4 or any(type(t) is not int or t<=0 for t in row) or len(set(row))!=4:
   raise ValueError('Complete positive distinct integer TET4 rows required')
  if any(t>boundary_count and t not in interior for t in row):
   raise ValueError('Poor row has an unclassified nonboundary tag')
  members.update(row)
 return sorted(members & interior)


def incident_positions(node_rows,movable_tags):
 """Every row touching any chosen tag, irrespective of its starting quality."""
 if (any(type(t) is not int or t<=0 for t in movable_tags)
     or movable_tags!=sorted(set(movable_tags))):
  raise ValueError('Sorted unique positive integer movable tags required')
 movable=set(movable_tags);positions=[]
 for index,row in enumerate(node_rows):
  if len(row)!=4 or any(type(t) is not int or t<=0 for t in row) or len(set(row))!=4:
   raise ValueError('Complete positive distinct integer TET4 rows required')
  if any(t in movable for t in row):positions.append(index)
 return positions


contract=json.loads((OUT/'frozen-contract.json').read_text())
for name,h in contract['input_hashes'].items():
 if sha(ROOT/name)!=h:raise ValueError('Bound saved-readback input drift: '+name)
w=ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-netgen-postexport-001';worker=json.loads((w/'worker-report.json').read_text());receipt=json.loads((w/'receipt.json').read_text());admission=json.loads((w/'surface-admission.json').read_text())
proof=optimizer_after_proof(worker,receipt,contract)
for name,h in admission['input_hashes'].items():
 if sha(ROOT/name)!=h:raise ValueError('Surface-admission evidence changed: '+name)
for name,h in receipt['source_sha256s'].items():
 if sha(ROOT/name)!=h or sha(w/'source-snapshots'/Path(name).name)!=h:raise ValueError('Executed source/snapshot changed')
import gmsh
if np.__version__!=worker['runtime']['numpy'] or gmsh.__version__!='4.15.2' or platform.machine()!='arm64' or sha(Path(gmsh.__file__))!=contract['runtime']['gmsh_module_sha256'] or sha(Path(gmsh.lib._name))!=contract['runtime']['libgmsh_sha256'] or sha(Path(sys.executable).resolve())!=contract['runtime']['python_executable_sha256']:raise ValueError('Pinned native Gmsh reader required')
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
  if report[key]!=proof['array_sha256s'][key]:raise ValueError('Saved-file tagged array differs from worker: '+key)
 candidate=ROOT/contract['candidate']
 with candidate.open('rb') as stream:header=stream.read(24)
 import struct
 nv,nf=struct.unpack_from('<QQ',header,8)
 if (nv,nf)!=(contract['candidate_vertices'],contract['candidate_oriented_triangles']):raise ValueError('Exact current source boundary counts required')
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
 positive_poor_counts={str(k):0 for k in range(5)};positive_poor_representatives={};poor_indices=[]
 for name,measure in [('SICN','minSICN'),('Jacobian','minDetJac'),('native_volume_mm3','volume')]:
  row=dict(count=0,minimum=None,maximum=None,nonpositive_count=0,below_point1_count=0 if name=='SICN' else None)
  metric_values=np.empty(len(tet_tags),dtype=np.float64)
  for offset in range(0,len(tet_tags),100000):
   q=np.asarray(gmsh.model.mesh.getElementQualities(tet_tags[offset:offset+100000],measure))
   if len(q)!=len(tet_tags[offset:offset+100000]) or not np.isfinite(q).all():raise ValueError('Incomplete/nonfinite native metric')
   metric_values[offset:offset+len(q)]=q
   row['count']+=len(q);row['minimum']=float(q.min()) if row['minimum'] is None else min(row['minimum'],float(q.min()));row['maximum']=float(q.max()) if row['maximum'] is None else max(row['maximum'],float(q.max()));row['nonpositive_count']+=int(np.count_nonzero(q<=0))
   if name=='SICN':
    row['below_point1_count']+=int(np.count_nonzero(q<.1))
    classify_positive_poor_chunk(q,tet_tags[offset:offset+len(q)],tet_nodes[offset:offset+len(q)],offset,nv,positive_poor_counts,positive_poor_representatives)
    poor_indices.extend((offset+np.flatnonzero((q>0)&(q<.1))).tolist())
    for local in np.flatnonzero(q<=0):
     index=offset+int(local);conn=tet_nodes[index];ids=np.searchsorted(tags,conn)
     if np.any(ids>=len(tags)) or not np.array_equal(tags[ids],conn):raise ValueError('Nonpositive-SICN cell references missing node')
     bad_tetrahedra.append(dict(native_array_index=index,tetrahedron_tag=int(tet_tags[index]),node_tags=conn.tolist(),coordinates_mm=xyz[ids].tolist(),SICN=float(q[local]),all_nodes_original_boundary_tags=bool(np.all((conn>=1)&(conn<=nv)))))
     if len(bad_tetrahedra)>contract['diagnostic_maximum_nonpositive_cells']:raise ValueError('Unexpected diagnostic cell count; preserve refusal without truncating evidence')
   else:
    for bad in [*bad_tetrahedra,*positive_poor_representatives.values()]:
     index=bad['native_array_index']
     if offset<=index<offset+len(q):bad[name]=float(q[index-offset])
  row.update(dict(zip(('p01','p05','p50','p95','p99'),map(float,np.percentile(metric_values,[1,5,50,95,99])))))
  row['array_sha256']=array_sha(metric_values[tetorder])
  native[name]=row
  if name=='SICN':sicn_values=metric_values
 report['direct_native_quality_extrema']=native
 for representative in positive_poor_representatives.values():
  conn=tet_nodes[representative['native_array_index']];ids=np.searchsorted(tags,conn)
  if np.any(ids>=len(tags)) or not np.array_equal(tags[ids],conn):raise ValueError('Positive poor cell references missing node')
  representative.update(node_tags=conn.tolist(),coordinates_mm=xyz[ids].tolist())
 volumes=np.empty(len(tet_tags),dtype=np.float64);referenced=np.zeros(len(tags),dtype=bool)
 for offset in range(0,len(tet_tags),100000):
  conn=tet_nodes[offset:offset+100000];ids=np.searchsorted(tags,conn)
  if np.any(ids>=len(tags)) or not np.array_equal(tags[ids],conn):raise ValueError('Tet references missing saved node')
  referenced[ids.ravel()]=True;v=xyz[ids];volumes[offset:offset+len(conn)]=np.einsum('ij,ij->i',v[:,1]-v[:,0],np.cross(v[:,2]-v[:,0],v[:,3]-v[:,0]))/6
 if not np.isfinite(volumes).all():raise ValueError('Nonfinite independent saved-file volume')
 total=math.fsum(volumes);report.update(independent_signed_volume_mm3=dict(count=len(volumes),minimum=float(volumes.min()),maximum=float(volumes.max()),nonpositive_count=int(np.count_nonzero(volumes<=0)),sum=total,relative_error_to_candidate=abs(total/worker['candidate_volume_reference_mm3']-1)),actual_tetra_referenced_nodes=int(np.count_nonzero(referenced)),actual_unreferenced_mesh_nodes=int(np.count_nonzero(~referenced)),actual_referenced_interior_nodes=int(np.count_nonzero(referenced & ((tags<1)|(tags>nv)))))
 report['independent_signed_volume_mm3'].update(dict(zip(('p01','p05','p50','p95','p99'),map(float,np.percentile(volumes,[1,5,50,95,99])))))
 for bad in [*bad_tetrahedra,*positive_poor_representatives.values()]:bad['independent_signed_volume_mm3']=float(volumes[bad['native_array_index']])
 report.update(nonpositive_SICN_tetrahedra=bad_tetrahedra,fixed_boundary_only_nonpositive_cells=all(bad['all_nodes_original_boundary_tags'] for bad in bad_tetrahedra))
 positive_poor_total=sum(positive_poor_counts.values())
 if positive_poor_total!=native['SICN']['below_point1_count']-native['SICN']['nonpositive_count']:raise ValueError('Complete positive-poor cell partition required')
 report['positive_poor_SICN_cells']=dict(total=positive_poor_total,
  by_original_boundary_node_count=positive_poor_counts,
  all_original_boundary_nodes=positive_poor_counts['4'],
  at_least_one_interior_node=positive_poor_total-positive_poor_counts['4'],
  representative_policy='One minimum(SICN,tetrahedron_tag) cell per nonempty0..4boundary-node class; at most5records, not a statistical sample.',
  representatives=positive_poor_representatives,
  original_boundary_definition='Exact admitted source surface tags1..nv; distinct from the surface-repair fixed-vertex mask.',
  positive_poor_feature_or_OEM_classification_computed=False)
 require_after_match(report,proof,contract['expected_positive_poor_total'])
 prior=json.loads((ROOT/contract['completed_saved_diagnosis']).read_text())
 if (prior.get('status')!='direct_saved_file_readback_completed' or prior.get('bound_inputs_unchanged') is not True
     or prior['positive_poor_SICN_cells']['total']!=positive_poor_total
     or prior['positive_poor_SICN_cells']['by_original_boundary_node_count']!=positive_poor_counts
     or positive_poor_counts!=contract['expected_positive_poor_bins']):
  raise ValueError('Complete current210 partition and prior stopped diagnosis required')
 fresh_classifications=classifications(sys.modules[__name__],gmsh,tags,nv)
 if fresh_classifications!=proof['classifications']:
  raise ValueError('Fresh complete classifications differ from single worker.after')
 poor_indices.sort(key=lambda i:int(tet_tags[i]))
 if len(poor_indices)!=positive_poor_total:raise ValueError('All positive-poor rows required')
 interior_tags=tags[tags>nv].tolist()
 movable_tags=movable_from_poor_rows(tet_nodes[poor_indices].tolist(),interior_tags,nv)
 incident_indices=[]
 for offset in range(0,len(tet_tags),100000):
  incident_indices.extend(offset+i for i in incident_positions(tet_nodes[offset:offset+100000].tolist(),movable_tags))
 incident_indices.sort(key=lambda i:int(tet_tags[i]))
 if not set(poor_indices)<=set(incident_indices):
  raise ValueError('A baseline poor cell has no selected interior member; retain refusal, never omit it')
 selected_nodes=tet_nodes[incident_indices]
 union_tags=np.unique(selected_nodes).tolist();union_positions=np.searchsorted(tags,union_tags)
 if np.any(union_positions>=len(tags)) or not np.array_equal(tags[union_positions],union_tags):
  raise ValueError('Complete incident-cell coordinate association required')
 movable=set(movable_tags);poor_set=set(poor_indices);star_counts={t:0 for t in movable_tags}
 cells=[]
 for i in incident_indices:
  row=tet_nodes[i].tolist();touch=sorted(movable.intersection(row))
  for t in touch:star_counts[t]+=1
  cells.append(dict(tetrahedron_tag=int(tet_tags[i]),native_array_index=i,node_tags=row,
   initial_native_SICN=float(sicn_values[i]),initially_positive_poor=i in poor_set,movable_node_tags=touch))
 nodes=[]
 for tag,index in zip(union_tags,union_positions):
  row=xyz[index].tolist()
  nodes.append(dict(node_tag=int(tag),coordinates_mm=row,binary64_hex=[float(x).hex() for x in row],
   in_movable_seed_set=tag in movable,source_boundary_tag=tag<=nv,
   freshly_proved_classification_scope='below_dim3' if tag<=nv else 'dim3'))
 report['complete_seed_star_census']=dict(
  schema='962-complete-current-poor-seed-stars/v1',
  seed_policy='Union of nodes of ALL current positive SICN<0.1 cells, intersect freshly verified complete dim3 classifications; no optimizer proposal.',
  positive_poor_tetrahedron_tags=[int(tet_tags[i]) for i in poor_indices],
  movable_node_tags=movable_tags,movable_count=len(movable_tags),prospective_coordinate_variables=3*len(movable_tags),
  complete_incident_tetrahedra=cells,complete_incident_tetrahedron_count=len(cells),
  initially_positive_poor_incident_tetrahedra=sum(row['initially_positive_poor'] for row in cells),
  initially_good_incident_tetrahedra=sum(not row['initially_positive_poor'] for row in cells),
  shared_by_multiple_movable_nodes_tetrahedra=sum(len(row['movable_node_tags'])>1 for row in cells),
  per_movable_node_complete_incident_counts=[[t,star_counts[t]] for t in movable_tags],
  unique_incident_nodes=nodes,unique_incident_node_count=len(nodes),
  unique_incident_boundary_node_count=sum(row['source_boundary_tag'] for row in nodes),
  unique_incident_other_interior_node_count=sum(not row['source_boundary_tag'] and not row['in_movable_seed_set'] for row in nodes),
  ordered_tagged_array_sha256s=dict(
   movable_node_tags_u64=array_sha(np.asarray(movable_tags,dtype='<u8')),
   selected_tetrahedron_tags_u64=array_sha(np.asarray([tet_tags[i] for i in incident_indices],dtype='<u8')),
   selected_tetrahedron_connectivity_u64=array_sha(np.asarray(selected_nodes,dtype='<u8').reshape(-1,4)),
   union_node_tags_u64=array_sha(np.asarray(union_tags,dtype='<u8')),
   union_coordinates_f64=array_sha(np.asarray(xyz[union_positions],dtype='<f8')),
   selected_initial_SICN_f64=array_sha(np.asarray(sicn_values[incident_indices],dtype='<f8'))),
  all_seed_stars_complete_including_initially_good_and_shared_cells=True,
  complete_list_policy='Complete or resource refusal; no sampling or record truncation.',
  cell_order='Increasing tetrahedron tag; original corner order retained.',node_order='Increasing node tag; coordinate hex preserves binary64 bits.',
  source_boundary_or_other_context_repair_policy_approved=False,
  shared_star_feasibility_computed=False,SLSQP_or_other_optimization_calls=0,candidate_or_geometry_export_written=False)
 report['direct_fresh_classifications']=fresh_classifications
 report['direct_counts_metrics_and_positive_poor_total_match_single_worker_after']=True
 report['single_optimized_worker_proof']=dict(worker_report_sha256=sha(w/'worker-report.json'),field='after',independent_prior_reader_alias_used=False)
 report.update(retained_only_not_repeated=dict(tetra_exterior_incidence=proof['actual_tetra_boundary'],internal_face_orientation=proof['internal_tetra_face_orientation']),SICN_point1_gate_passed=native['SICN']['minimum']>=.1 and native['SICN']['nonpositive_count']==0,thermal_resolution_established=False,status='direct_saved_file_readback_completed')
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
