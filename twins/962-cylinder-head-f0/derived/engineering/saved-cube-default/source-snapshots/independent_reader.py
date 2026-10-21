"""Read two retained tiny MSHs only; no generation, optimizer, mesh write or solve."""
from pathlib import Path
import hashlib,json,math,platform,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
arrsha=lambda a:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
contract=load(OUT/'frozen-contract.json')
for n,h in contract['input_hashes'].items():
 if sha(ROOT/n)!=h:raise ValueError('Frozen saved-cube input drift: '+n)
for n,h in contract['external_runtime_hashes'].items():
 if sha(Path(n))!=h:raise ValueError('Frozen reader runtime changed')
import gmsh
runtime={'python':sha(Path(sys.executable).resolve()),'gmsh_module':sha(Path(gmsh.__file__)),'gmsh_library':sha(Path(gmsh.lib._name))}
assert runtime==contract['runtime_sha256s'] and gmsh.__version__=='4.15.2' and np.__version__=='2.0.2' and platform.machine()=='arm64'
P=np.array([[0,0,0],[7,0,0],[7,7,0],[0,7,0],[0,0,7],[7,0,7],[7,7,7],[0,7,7]],dtype=float)
F=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]],dtype=int)+1
def canonical(f):
 f=tuple(int(x) for x in f);i=f.index(min(f));return f[i:]+f[:i]
expected_faces=sorted(canonical(f) for f in F)
def distribution(a):
 assert len(a)>0 and np.isfinite(a).all()
 return {'count':len(a),'minimum':float(a.min()),'maximum':float(a.max()),'nonpositive_count':int(np.count_nonzero(a<=0)),'below_point1_count':int(np.count_nonzero(a<.1)),'array_sha256':arrsha(a)}
def inspect(path):
 gmsh.open(str(path));tags,coords,_=gmsh.model.mesh.getNodes();ix=np.argsort(tags);tags=np.asarray(tags)[ix];coords=np.asarray(coords).reshape(-1,3)[ix]
 assert np.isfinite(coords).all() and len(np.unique(tags))==len(tags) and np.all((coords>=0)&(coords<=7))
 boundary=np.arange(1,9);ix=np.searchsorted(tags,boundary);assert np.array_equal(tags[ix],boundary) and np.array_equal(coords[ix],P)
 types,ets,ens=gmsh.model.mesh.getElements(3);assert list(types)==[4];et=np.asarray(ets[0]);en=np.asarray(ens[0]).reshape(-1,4);order=np.argsort(et);et,en=et[order],en[order]
 assert len(np.unique(et))==len(et);ci=np.searchsorted(tags,en);assert np.array_equal(tags[ci],en)
 referenced=np.unique(en);inner=referenced[~np.isin(referenced,boundary)];inner_xyz=coords[np.searchsorted(tags,inner)];assert np.all((inner_xyz>0)&(inner_xyz<7))
 dims={};periodic=[]
 for dim,tag in gmsh.model.getEntities():
  if dim in [1,2]:
   masters=gmsh.model.mesh.getPeriodic(dim,[tag]);master,nodes,node_masters,transform=gmsh.model.mesh.getPeriodicNodes(dim,tag,True)
   assert list(masters)==[tag] and master==tag and len(nodes)==len(node_masters)==len(transform)==0;periodic.append([dim,tag])
  for n in gmsh.model.mesh.getNodes(dim,tag,False,False)[0]:
   assert int(n) not in dims;dims[int(n)]=dim
 assert set(dims)==set(map(int,tags)) and all(dims[n]<3 for n in boundary) and all(dims[int(n)]==3 for n in tags if n>8)
 types,_,ens=gmsh.model.mesh.getElements(2);assert list(types)==[2];surface=np.asarray(ens[0]).reshape(-1,3);assert sorted(canonical(f) for f in surface)==expected_faces
 inc={}
 for tet in en:
  for ix in [[0,2,1],[0,1,3],[1,2,3],[2,0,3]]:
   f=tuple(int(x) for x in tet[ix]);inc.setdefault(tuple(sorted(f)),[]).append(f)
 exterior=[];internal=0
 for fs in inc.values():
  assert len(fs)<=2
  if len(fs)==1:exterior.append(canonical(fs[0]))
  else:assert canonical(fs[0])==canonical(fs[1][::-1]);internal+=1
 assert sorted(exterior)==expected_faces
 xyz=coords[ci];signed=np.einsum('ij,ij->i',xyz[:,1]-xyz[:,0],np.cross(xyz[:,2]-xyz[:,0],xyz[:,3]-xyz[:,0]))/6
 assert np.isfinite(signed).all() and np.all(signed>0)
 total=math.fsum(signed);relative=abs(total/343-1);assert relative<=1e-6
 qualities={label:np.asarray(gmsh.model.mesh.getElementQualities(et,name)) for label,name in [('SICN','minSICN'),('Jacobian','minDetJac'),('native_volume_mm3','volume')]}
 for label,q in qualities.items():
  assert len(q)==len(et) and np.isfinite(q).all()
  if label!='SICN':assert np.all(q>0)
 canonical_tets=np.sort(en,axis=1);canonical_tets=canonical_tets[np.lexsort(canonical_tets.T[::-1])]
 assert len(np.unique(canonical_tets,axis=0))==len(canonical_tets)
 report={'mesh_sha256':sha(path),'mesh_bytes':path.stat().st_size,'nodes':len(tags),'tetrahedra':len(et),'referenced_nodes':len(referenced),'referenced_interior_nodes':len(inner),'unreferenced_nodes':len(tags)-len(referenced),'all_counted_interior_nodes_strictly_inside_cube':True,'boundary_triangles':len(exterior),'internal_opposite_face_pairs':internal,'exact_explicit_and_tetra_exterior_boundary':True,'node_classifications':[[n,dims[n]] for n in sorted(dims)],'node_counts_by_classification_dimension':{str(d):sum(v==d for v in dims.values()) for d in range(4)},'no_curve_or_surface_periodic_mapping':True,'periodic_entities_checked':periodic,'quality':{k:distribution(v) for k,v in qualities.items()},'independent_signed_volume_mm3':{'sum':total,'relative_error':relative,**distribution(signed)},'sorted_node_tags_sha256':arrsha(tags),'sorted_coordinates_sha256':arrsha(coords),'tetra_tags_sha256':arrsha(et),'tagged_tetra_connectivity_sha256':arrsha(en),'canonical_cells_sha256':arrsha(canonical_tets),'software_geometric_invariants_passed':True}
 arrays={'node_tags':tags.tolist(),'coordinates_mm':coords.tolist(),'tetra_tags':et.tolist(),'tetra_node_tags':en.tolist(),'native_qualities':{k:v.tolist() for k,v in qualities.items()},'independent_signed_volume_mm3':signed.tolist()}
 gmsh.clear();return report,arrays,(tags,coords,et,en,canonical_tets)
started=time.monotonic();gmsh.initialize([],readConfigFiles=False,run=False)
try:
 gmsh.option.setNumber('General.Terminal',0);gmsh.option.setNumber('General.NumThreads',2)
 before,ba,b=inspect(ROOT/contract['before_mesh']);after,aa,a=inspect(ROOT/contract['after_mesh'])
finally:gmsh.finalize()
common=np.intersect1d(b[0],a[0]);ib=np.searchsorted(b[0],common);ia=np.searchsorted(a[0],common);moved=np.any(b[1][ib]!=a[1][ia],axis=1);same_tags=np.array_equal(b[0],a[0]);changed_topology=not np.array_equal(b[4],a[4])
x,y=before['quality']['SICN']['minimum'],after['quality']['SICN']['minimum']
assessment={'minimum_SICN_before':x,'minimum_SICN_after':y,'minimum_SICN_change':y-x,'actual_SICN_threshold':.1,'minimum_SICN_strictly_improved':y>x,'actual_SICN_gate_passed':y>=.1,'canonical_volume_topology_changed':changed_topology,'tetrahedra_before':before['tetrahedra'],'tetrahedra_after':after['tetrahedra'],'same_node_tags':same_tags,'common_node_coordinates_changed':int(np.count_nonzero(moved)),'common_interior_node_coordinates_changed':int(np.count_nonzero(moved&(common>8))),'boundary_node_coordinates_changed':int(np.count_nonzero(moved&(common<=8))),'added_node_tags':np.setdiff1d(a[0],b[0]).tolist(),'removed_node_tags':np.setdiff1d(b[0],a[0]).tolist(),'optimization_had_effect':changed_topology or bool(np.any(moved)) or not same_tags,'source_fixture_controller_passed':False,'retained_fixture_error':'Exception: Unknown element 216','fresh_saved_file_quality_queries_all_succeeded':True,'later_saved_file_diagnosis_does_not_rewrite_original_failure':True,'head_accepted':False}
assessment['postrun_cube_quality_success']=assessment['actual_SICN_gate_passed'] and assessment['minimum_SICN_strictly_improved'] and assessment['optimization_had_effect']
original_worker=load(ROOT/'work/962-engineering/saved-cube-default-fixture-001/default-force/worker-report.json')
assert before['tetrahedra']==original_worker['before']['tetrahedra']==191
for k,stored in [('SICN','SICN'),('Jacobian','jacobian'),('native_volume_mm3','volume_mm3')]:assert before['quality'][k]['minimum']==original_worker['before']['quality'][stored]['minimum']
for n,h in contract['input_hashes'].items():assert sha(ROOT/n)==h
for n,h in contract['external_runtime_hashes'].items():assert sha(Path(n))==h
with (OUT/'arrays.json').open('x') as f:json.dump({'before':ba,'after':aa},f,indent=2,allow_nan=False);f.write('\n')
report={'schema':'962-saved-default-cube-independent-readback/v1','status':'saved_files_independently_read_original_fixture_failure_preserved','scope':'Read-only postrun before/after file diagnosis; no optimizer repeat or source/contract repair.','runtime_sha256s':runtime,'frozen_contract_sha256':sha(OUT/'frozen-contract.json'),'before':before,'after':after,'assessment':assessment,'full_small_array_payload_sha256':sha(OUT/'arrays.json'),'bound_inputs_unchanged':True,'native_generation_optimization_write_or_solve_calls':0,'head_geometry_read':False,'head_execution_authorized':False,'thermal_resolution_established':False,'manufacturing_authorized':False,'reader_wall_seconds':time.monotonic()-started}
with (OUT/'review.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps({'status':report['status'],'assessment':assessment}))
