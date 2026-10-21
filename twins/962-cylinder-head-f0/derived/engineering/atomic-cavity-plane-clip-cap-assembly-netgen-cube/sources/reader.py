"""One source-bound saved-cube Netgen fixture; no generation, solve or head input."""
from pathlib import Path
import hashlib,json,math,platform,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
arrsha=lambda a:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
INPUT='work/962-engineering/hxt-size-cap-fixture-001/capped-1p75/cube.msh'
OUTPUT=ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-fixture-001'
INPUT_SHA='e773cc4a2f68187c623e984eb9f58441f3fa5eed2733295e7eb26bd7b3910ac1'
OPTIONS={'General.NumThreads':2,'Mesh.MaxNumThreads3D':2,'Mesh.Renumber':0,'Mesh.Optimize':0,'Mesh.OptimizeNetgen':0,'Mesh.OptimizeThreshold':.3,'Mesh.Binary':1,'Mesh.SaveAll':1,'Mesh.MshFileVersion':4.1}
RUNTIME={'python':'3.10.11','numpy':'2.0.2','gmsh':'4.15.2','machine':'arm64'}
P=np.array([[0,0,0],[7,0,0],[7,7,0],[0,7,0],[0,0,7],[7,0,7],[7,7,7],[0,7,7]],dtype=float)
F=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]],dtype=int)+1
def canonical(f):
 f=tuple(int(x) for x in f);i=f.index(min(f));return f[i:]+f[:i]
expected_faces=sorted(canonical(f) for f in F)
def distribution(a):
 assert len(a)>0 and np.isfinite(a).all()
 return {'count':len(a),'minimum':float(a.min()),'maximum':float(a.max()),'nonpositive_count':int(np.count_nonzero(a<=0)),'below_point1_count':int(np.count_nonzero(a<.1)),'array_sha256':arrsha(a)}
def inspect_live():
 tags,coords,_=gmsh.model.mesh.getNodes();ix=np.argsort(tags);tags=np.asarray(tags)[ix];coords=np.asarray(coords).reshape(-1,3)[ix]
 assert np.isfinite(coords).all() and len(np.unique(tags))==len(tags) and np.all(tags>0) and np.all((coords>=0)&(coords<=7))
 boundary=np.arange(1,9);ix=np.searchsorted(tags,boundary);assert np.array_equal(tags[ix],boundary) and coords[ix].tobytes()==P.tobytes()
 types,ets,ens=gmsh.model.mesh.getElements(3);assert list(types)==[4];et=np.asarray(ets[0]);en=np.asarray(ens[0]).reshape(-1,4);order=np.argsort(et);et,en=et[order],en[order]
 assert len(np.unique(et))==len(et) and np.all(et>0);ci=np.searchsorted(tags,en);assert np.array_equal(tags[ci],en)
 referenced=np.unique(en);assert np.array_equal(referenced,tags);inner=referenced[~np.isin(referenced,boundary)];inner_xyz=coords[np.searchsorted(tags,inner)];assert np.all((inner_xyz>0)&(inner_xyz<7))
 dims={};entities={};periodic=[]
 for dim,tag in gmsh.model.getEntities():
  if dim in [1,2]:
   masters=gmsh.model.mesh.getPeriodic(dim,[tag]);master,nodes,node_masters,transform=gmsh.model.mesh.getPeriodicNodes(dim,tag,True)
   assert list(masters)==[tag] and master==tag and len(nodes)==len(node_masters)==len(transform)==0;periodic.append([dim,tag])
  for n in gmsh.model.mesh.getNodes(dim,tag,False,False)[0]:
   assert int(n) not in dims;dims[int(n)]=dim;entities[int(n)]=[dim,tag]
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
 report={'nodes':len(tags),'tetrahedra':len(et),'referenced_nodes':len(referenced),'referenced_interior_nodes':len(inner),'unreferenced_nodes':len(tags)-len(referenced),'all_counted_interior_nodes_strictly_inside_cube':True,'boundary_triangles':len(exterior),'internal_opposite_face_pairs':internal,'exact_explicit_and_tetra_exterior_boundary':True,'node_classifications':[[n,dims[n]] for n in sorted(dims)],'node_entity_classifications':[[n,*entities[n]] for n in sorted(entities)],'node_counts_by_classification_dimension':{str(d):sum(v==d for v in dims.values()) for d in range(4)},'no_curve_or_surface_periodic_mapping':True,'periodic_entities_checked':periodic,'quality':{k:distribution(v) for k,v in qualities.items()},'independent_signed_volume_mm3':{'sum':total,'relative_error':relative,**distribution(signed)},'sorted_node_tags_sha256':arrsha(tags),'sorted_coordinates_sha256':arrsha(coords),'tetra_tags_sha256':arrsha(et),'tagged_tetra_connectivity_sha256':arrsha(en),'canonical_cells_sha256':arrsha(canonical_tets),'software_geometric_invariants_passed':True}
 arrays={'node_tags':tags.tolist(),'coordinates_mm':coords.tolist(),'tetra_tags':et.tolist(),'tetra_node_tags':en.tolist(),'native_qualities':{k:v.tolist() for k,v in qualities.items()},'independent_signed_volume_mm3':signed.tolist()}
 return report,arrays,(tags,coords,et,en,canonical_tets),(*qualities.values(),signed)

def require_contract(c):
 if c.get('output_directory')!=str(OUTPUT.relative_to(ROOT)) or OUT!=OUTPUT.resolve():raise ValueError('Fixed fresh cube output directory required')
 if c.get('native_execution_authorized') is not True or c.get('head_execution_authorized') is not False:raise ValueError('Reviewed cube-only execution authority required')
 if c.get('input_mesh')!=INPUT or c.get('input_mesh_sha256')!=INPUT_SHA or c.get('options')!=OPTIONS or c.get('expected_runtime')!=RUNTIME:raise ValueError('Exact cube, options and runtime required')
 if c.get('optimization')!={'method':'Netgen','force':True} or c.get('geometry_creation_dim_tags')!=[[3,1]]:raise ValueError('Single fixed Netgen/dim3-only geometry operation required')
 if sha(ROOT/INPUT)!=INPUT_SHA:raise ValueError('Frozen cube bytes changed')
 for name,h in c['input_hashes'].items():
  if sha(ROOT/name)!=h:raise ValueError('Frozen input drift: '+name)
 for name,h in c['external_runtime_hashes'].items():
  if sha(Path(name))!=h:raise ValueError('Native runtime drift')
 if sha(OUT/'reader.py')!=c['reader_sha256'] or sha(OUT/'run_readback.py')!=c['runner_sha256']:raise ValueError('Materialized source copies changed')

def snapshot(live):
 report,arrays,state,quality=live
 return {'arrays':[(a.dtype.str,a.shape,a.tobytes()) for a in (*state[:4],*quality)],
  'classifications':report['node_entity_classifications'],
  'periodic':report['periodic_entities_checked']}

def require_same(before,after,stage):
 if snapshot(before)!=snapshot(after):raise ValueError('Exact live arrays/classifications/quality changed at '+stage)

def geometry_flag_only(gmsh,before,inspect,counts):
 if gmsh.model.getEntities(3)!=[(3,1)] or not gmsh.model.getBoundary([(3,1)],oriented=True,recursive=False):raise ValueError('Exactly one region(3,1) with a bounding shell required')
 counts['createGeometry_dim3']+=1
 gmsh.model.mesh.createGeometry([(3,1)])
 after=inspect();require_same(before,after,'volume-only createGeometry')
 return after

def optimize_once(gmsh,counts):
 counts['optimize_Netgen']+=1
 gmsh.model.mesh.optimize(method='Netgen',force=True)
 counts['rebuildElementCache']+=1
 gmsh.model.mesh.rebuildElementCache(False)

def quality_gate(report):
 q=report['quality']['SICN']
 return q['count']==report['tetrahedra'] and math.isfinite(q['minimum']) and q['minimum']>=.1 and q['below_point1_count']==0


def main():
 global gmsh
 c=load(OUT/'frozen-contract.json');require_contract(c)
 if {p.name for p in OUT.iterdir()}!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:raise ValueError('Only fresh materialized fixture inputs and owned native.log are permitted')
 import gmsh
 observed={'python':platform.python_version(),'numpy':np.__version__,'gmsh':gmsh.__version__,'machine':platform.machine()}
 if observed!=RUNTIME:raise ValueError('Loaded runtime versions changed')
 actual={'python':sha(Path(sys.executable).resolve()),'gmsh_module':sha(Path(gmsh.__file__)),'gmsh_library':sha(Path(gmsh.lib._name))}
 if actual!=c['runtime_sha256s']:raise ValueError('Actual loaded runtime hashes changed')
 started=time.monotonic();initialized=False;live={};report={'schema':'962-saved-cube-Netgen-fixture/v1','status':'running','stage':'initializing','fixture_procedural_checks_passed':False,'actual_SICN_gate_passed':False,'options':OPTIONS,'optimization':{'method':'Netgen','force':True},'call_counts_are_attempts':True,'native_operation_counts':{'generate':0,'createGeometry_dim3':0,'optimize_Netgen':0,'rebuildElementCache':0,'write_mesh':0,'solve':0},'runtime':observed,'runtime_sha256s':actual,'frozen_contract_sha256':sha(OUT/'frozen-contract.json'),'head_geometry_read':False,'head_execution_authorized':False,'physical_or_manufacturing_accepted':False,'internal_tag_changes_do_not_establish_ancestry_or_physical_topology_change':True}
 try:
  gmsh.initialize([],readConfigFiles=False,run=False);initialized=True
  gmsh.option.setNumber('General.Terminal',1);gmsh.logger.start()
  for k,v in OPTIONS.items():gmsh.option.setNumber(k,v)
  if 'Netgen' not in gmsh.option.getString('General.BuildOptions').split():raise ValueError('Compiled Netgen token absent')
  gmsh.open(str(ROOT/INPUT));report['stage']='full_before_audit';live['before']=inspect_live()
  before=live['before'][0]
  if before['nodes']!=42 or before['referenced_interior_nodes']!=34 or before['tetrahedra']!=191:raise ValueError('Exact retained cube42/34/191 required before optimizer')
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError('Fixed options changed')
  report['stage']='volume_only_geometry_flag'
  live['after_geometry_flag']=geometry_flag_only(gmsh,live['before'],inspect_live,report['native_operation_counts'])
  report['geometry_flag_full_arrays_classifications_and_quality_unchanged']=True
  report['stage']='calling_Netgen'
  optimize_once(gmsh,report['native_operation_counts'])
  report['Netgen_returned_and_cache_refresh_completed']=True
  report['stage']='full_after_audit';live['after']=inspect_live()
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError('Fixed options changed after optimizer')
  before_classes={row[0]:row[1:] for row in before['node_entity_classifications'] if row[0]<=8}
  after_classes={row[0]:row[1:] for row in live['after'][0]['node_entity_classifications'] if row[0]<=8}
  if before_classes!=after_classes:raise ValueError('Boundary entity classification changed')
  path=OUT/'cube.msh';report['stage']='saving';report['native_operation_counts']['write_mesh']+=1;gmsh.write(str(path));mesh_sha=sha(path)
  gmsh.clear();gmsh.open(str(path));report['stage']='saved_reopen_audit';live['saved_reopen']=inspect_live();require_same(live['after'],live['saved_reopen'],'saved reopen')
  if sha(path)!=mesh_sha:raise ValueError('Saved cube file changed during reopen')
  for name,item in live.items():report[name]=item[0]
  report.update(mesh_sha256=mesh_sha,mesh_bytes=path.stat().st_size,saved_mesh_identity_exact=True,actual_SICN_threshold=.1,actual_SICN_gate_passed=quality_gate(live['after'][0]),minimum_SICN_strictly_improved=live['after'][0]['quality']['SICN']['minimum']>before['quality']['SICN']['minimum'],fixture_procedural_checks_passed=True,stage='completed_all_local_checks',status='completed_cube_only')
  with (OUT/'arrays.json').open('x') as f:json.dump({name:item[1] for name,item in live.items()},f,indent=2,allow_nan=False);f.write('\n')
  report['full_tiny_arrays_sha256']=sha(OUT/'arrays.json')
 except Exception as exc:report.update(status='failed_outputs_preserved',error=type(exc).__name__+': '+str(exc))
 finally:
  if initialized:
   report['gmsh_warnings_errors']=[s for s in gmsh.logger.get() if s.startswith(('Warning','Error'))];gmsh.logger.stop();gmsh.finalize()
  try:require_contract(c);report['bound_inputs_unchanged']=sha(OUT/'frozen-contract.json')==report['frozen_contract_sha256']
  except Exception:report['bound_inputs_unchanged']=False
  for name,item in live.items():report.setdefault(name,item[0])
  report['wall_seconds']=time.monotonic()-started
  with (OUT/'fixture-report.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
 return 0 if report['fixture_procedural_checks_passed'] and report['actual_SICN_gate_passed'] and report['bound_inputs_unchanged'] else 2
if __name__=='__main__':raise SystemExit(main())
