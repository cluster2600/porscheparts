"""HELD single fixed-shell apex1435493 cavity generation; no head stitching."""
from pathlib import Path
from fractions import Fraction
import ast,hashlib,importlib.util,json,math,platform,struct,sys,time

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
SHELL='work/962-engineering/direct-sicn-apex1435493-cavity-study-001/local-shell-input-001.json'
SHELL_SHA='a6f15db60967807b057e357b8f159fa510c4a8cf6e3cb44c4327323c070398c8'
HELPER='twins/962-cylinder-head-f0/source/mesh_head.py'
HELPER_SHA='69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5'
ORIENTATION='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py'
ORIENTATION_SHA='a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4'
CUBE='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/reader.py'
CUBE_SHA='97b7e9fc7d17defa84594c50dac1d4e09cd39bb47ef2059e00b6ac07fe8c029b'
OPTIONS={'General.NumThreads':2,'Mesh.MaxNumThreads3D':2,'Mesh.Algorithm3D':1,
 'Mesh.MeshOnlyEmpty':1,'Mesh.Renumber':0,'Mesh.ElementOrder':1,'Mesh.Optimize':0,
 'Mesh.OptimizeNetgen':0,'Mesh.MeshSizeExtendFromBoundary':0,'Mesh.RandomSeed':1,
 'Mesh.Binary':1,'Mesh.SaveAll':1,'Mesh.MshFileVersion':4.1}
RUNTIME={'python':'3.10.11','numpy':'2.0.2','gmsh':'4.15.2','machine':'arm64'}
COUNTS={'generate':1,'createGeometry_dim3':0,'optimize_Netgen':0,
 'rebuildElementCache':0,'write_mesh':1,'solve':0}
VOLUME=Fraction(1450956179458166404046894365859946143854307,522673715590561479879743397015195972796416)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def save(path,value):
 with Path(path).open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')

def validate_shell(points,faces):
 if (len(points)!=16 or any(len(p)!=3 or any(not math.isfinite(float(x)) for x in p) for p in points)
     or len(faces)!=28 or any(len(f)!=3 or len(set(f))!=3 or any(type(t) is not int or not 1<=t<=16 for t in f) for f in faces)):
  raise ValueError('Exact finite sixteen-node/twenty-eight-triangle cavity shell required')
 if len({struct.pack('<3d',*p) for p in points})!=16:raise ValueError('Duplicate shell coordinate bits')
 edges={};keys=set();referenced=set()
 p=[[Fraction.from_float(float(v)) for v in row] for row in points]
 cross=lambda a,b:[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
 for face in faces:
  key=tuple(sorted(face))
  if key in keys:raise ValueError('Duplicate shell face')
  keys.add(key);referenced.update(face)
  a,b,c=[p[t-1] for t in face]
  if not any(cross([y-x for x,y in zip(a,b)],[y-x for x,y in zip(a,c)])):raise ValueError('Degenerate shell triangle')
  for i in range(3):edges.setdefault(tuple(sorted((face[i],face[(i+1)%3]))),[]).append((face[i],face[(i+1)%3]))
 if referenced!=set(range(1,17)) or any(len(v)!=2 or v[0]!=v[1][::-1] for v in edges.values()):
  raise ValueError('Complete closed oppositely oriented shell required before meshing')
 volume=sum((sum(x*y for x,y in zip(p[f[0]-1],cross(p[f[1]-1],p[f[2]-1])))/6 for f in faces),Fraction(0))
 if volume!=VOLUME:raise ValueError('Exact old cavity oriented volume changed')
 return dict(vertices=16,faces=28,edges=len(edges),exact_volume_mm3={'numerator':str(volume.numerator),'denominator':str(volume.denominator)})

def shell_rows(data):
 if (data.get('schema')!='962-fixed-cavity-local-shell-input/v1' or data.get('vertices')!=16
     or data.get('oriented_triangles')!=28 or data.get('excluded_source_apex_tag')!=1435493
     or data.get('apex_not_in_shell_input') is not True):raise ValueError('Specific frozen cavity identity required')
 mapping=data['local_to_global_node_tags'];rows=data['vertex_rows'];triangles=data['oriented_triangle_rows']
 if (len(mapping)!=16 or any(type(t) is not int or t<=0 for t in mapping) or mapping!=sorted(set(mapping))
     or 1435493 in mapping or data['global_to_local_node_tags']!={str(t):i+1 for i,t in enumerate(mapping)}
     or len(rows)!=16 or len(triangles)!=28):raise ValueError('Complete exact local/global shell mapping required')
 points=[];faces=[]
 for i,row in enumerate(rows):
  xyz=row['coordinates_mm']
  if (row['local_node_tag']!=i+1 or row['source_global_node_tag']!=mapping[i]
      or len(xyz)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in xyz)
      or [float(v).hex() for v in xyz]!=row['binary64_hex']
      or struct.pack('<3d',*xyz).hex()!=row['binary64_little_endian_bytes_hex']
      or row['prospective_cavity_fixed'] is not True
      or row['original_source_boundary_node'] is not (i<9)
      or row['original_source_classification']!=('below_dim3' if i<9 else 'dim3')):
   raise ValueError('Exact shell coordinate bits or original classification changed')
  points.append(xyz)
 expected=dict(boundary_global_node_tags=mapping[:9],other_interior_global_node_tags=mapping[9:],
  boundary_local_node_tags=list(range(1,10)),other_interior_local_node_tags=list(range(10,17)))
 if data['original_source_classifications']!=expected:raise ValueError('Original nine-boundary/seven-interior distinction changed')
 for i,row in enumerate(triangles):
  if row['local_face_id']!=i+1 or type(row['source_owner_tetrahedron_tag']) is not int or row['source_owner_tetrahedron_tag']<=0:
   raise ValueError('Frozen local face/old owner association changed')
  faces.append(row['local_node_tags'])
 if data['exact_enclosed_volume_mm3']!={'numerator':VOLUME.numerator,'denominator':VOLUME.denominator}:
  raise ValueError('Exact saved cavity volume identity changed')
 return points,faces,validate_shell(points,faces)

def require_authority(c):
 if (c.get('native_execution_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or c.get('selected_runtime_review_complete') is not True or c.get('head_execution_authorized') is not False
     or c.get('cavity_generation_authorized') is not True or c.get('stitching_authorized') is not False
     or c.get('native_head_application_authorized') is not False or c.get('manufacturing_authorized') is not False):
  raise ValueError('Reviewed single specific cavity generation-only authority required')
 if (not isinstance(c.get('output_directory'),str) or OUT.parent!=ROOT/'work/962-engineering'
     or (ROOT/c['output_directory']).resolve()!=OUT):raise ValueError('Exact fresh actual output binding required')
 if (c.get('options')!=OPTIONS or c.get('expected_runtime')!=RUNTIME or c.get('declared_operation_counts')!=COUNTS
     or c.get('automatic_retry') is not False or c.get('local_shell_input')!=SHELL
     or c.get('local_shell_input_sha256')!=SHELL_SHA):raise ValueError('Fixed shell, options and operation policy required')

def require_contract(c):
 require_authority(c)
 for name,digest in [(SHELL,SHELL_SHA),(HELPER,HELPER_SHA),(ORIENTATION,ORIENTATION_SHA),(CUBE,CUBE_SHA)]:
  if c['input_hashes'].get(name)!=digest:raise ValueError('Exact shell/helper must be a direct pin')
 for name,digest in c['input_hashes'].items():
  if Path(name).is_absolute() or not (ROOT/name).resolve().is_relative_to(ROOT):raise ValueError('Project-relative input pin required')
  if sha(ROOT/name)!=digest:raise ValueError('Input drift: '+name)
 if len(c['external_runtime_hashes'])!=3:raise ValueError('Selected three native runtime identities required')
 for name,digest in c['external_runtime_hashes'].items():
  if sha(Path(name))!=digest:raise ValueError('Runtime drift')
 if (sha(OUT/'reader.py')!=c['reader_sha256'] or sha(OUT/'run_readback.py')!=c['runner_sha256']
     or sha(Path(sys.executable).resolve())!=c['runtime']['python_executable_sha256']):
  raise ValueError('Materialized source or selected Python changed')

def load_audit_helper(c):
 import numpy as np
 import gmsh
 if Path(np.__file__).resolve()!=Path(c['numpy_init']).resolve():raise ValueError('Selected NumPy origin changed')
 observed=dict(python=platform.python_version(),numpy=np.__version__,gmsh=gmsh.__version__,machine=platform.machine())
 actual=dict(python=sha(Path(sys.executable).resolve()),gmsh_module=sha(Path(gmsh.__file__)),gmsh_library=sha(Path(gmsh.lib._name)))
 if observed!=RUNTIME or actual!=c['runtime_sha256s']:raise ValueError('Loaded runtime identity changed')
 spec=importlib.util.spec_from_file_location('specific_cavity_mesh_audit',ROOT/HELPER)
 helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 if helper.np is not np or helper.OPTIONS!=OPTIONS:raise ValueError('Generic helper runtime or fixed options changed')
 helper.arrsha=helper.array_sha
 for source,names in [(ORIENTATION,['internal_face_orientation']),
                      (CUBE,['canonical','distribution','snapshot','require_same','quality_gate'])]:
  tree=ast.parse((ROOT/source).read_text())
  selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
  if {n.name for n in selected}!=set(names):raise ValueError('Exact selected audit definitions missing')
  exec(compile(ast.Module(body=selected,type_ignores=[]),source,'exec'),helper.__dict__)
 return helper,gmsh,observed,actual

def construct_shell(gmsh,helper,data):
 points,faces,proof=shell_rows(data)
 helper.P=helper.np.asarray(points,dtype='<f8');helper.F=helper.np.asarray(faces,dtype=helper.np.int64)
 gmsh.model.add('fixed_shell_apex1435493_cavity')
 gmsh.model.addDiscreteEntity(2,1)
 gmsh.model.mesh.addNodes(2,1,list(range(1,17)),helper.P.ravel())
 gmsh.model.mesh.addElementsByType(1,2,list(range(1,29)),helper.F.ravel())
 gmsh.model.geo.addSurfaceLoop([1],1);gmsh.model.geo.addVolume([1],1)
 gmsh.model.geo.synchronize()
 return proof

def boundary_snapshot(gmsh,helper):
 np=helper.np;tags,xyz,_=gmsh.model.mesh.getNodes();order=np.argsort(tags)
 tags=np.asarray(tags)[order];xyz=np.asarray(xyz).reshape(-1,3)[order];ix=np.searchsorted(tags,np.arange(1,17))
 if np.any(ix>=len(tags)) or not np.array_equal(tags[ix],np.arange(1,17)):raise ValueError('Boundary tags missing')
 bits=xyz[ix].astype('<f8',copy=False).tobytes()
 if bits!=helper.P.astype('<f8',copy=False).tobytes():raise ValueError('Boundary coordinate bits changed')
 types,element_tags,element_nodes=gmsh.model.mesh.getElements(2)
 if list(types)!=[2] or len(element_tags[0])!=28:raise ValueError('Exactly twenty-eight TRI3 elements required')
 faces=sorted((int(t),helper.canonical(row)) for t,row in zip(element_tags[0],np.asarray(element_nodes[0]).reshape(-1,3)))
 expected=sorted((i+1,helper.canonical(row)) for i,row in enumerate(helper.F))
 if faces!=expected:raise ValueError('Tagged oriented shell triangles changed')
 classes={}
 for dim,entity in gmsh.model.getEntities():
  for tag in gmsh.model.mesh.getNodes(dim,entity,False,False)[0]:
   if int(tag)<=16:
    if int(tag) in classes:raise ValueError('Boundary node classified twice')
    classes[int(tag)]=(dim,entity)
 if set(classes)!=set(range(1,17)) or any(dim>=3 for dim,entity in classes.values()):raise ValueError('Boundary classification missing')
 return {'coordinate_bytes':bits,'tagged_oriented_triangles':faces,'classifications':sorted(classes.items())}

def require_boundary_same(before,after):
 if before!=after:raise ValueError('Every boundary coordinate bit, tagged oriented face and classification must remain exact')

def check_metric_rows(values,count,name):
 if len(values)!=count or count<=0 or any(not math.isfinite(float(v)) for v in values):
  raise ValueError('Complete finite metric rows required: '+name)
 if name!='SICN' and any(v<=0 for v in values):raise ValueError('Strictly positive metric rows required: '+name)

def inspect_cavity(gmsh,helper):
 np=helper.np;coords,cells,et,en=helper.volume_arrays(gmsh)
 tags=np.sort(np.asarray(gmsh.model.mesh.getNodes()[0]));et=np.asarray(et);en=np.asarray(en)
 order=np.argsort(et);et,en,cells=et[order],en[order],cells[order]
 if (not np.isfinite(coords).all() or len(tags)!=len(np.unique(tags)) or np.any(tags<=0)
     or len(et)!=len(np.unique(et)) or np.any(et<=0) or len(np.unique(coords,axis=0))!=len(coords)):
  raise ValueError('Finite unique positive tags and distinct node coordinates required')
 referenced=np.unique(en)
 if not np.array_equal(referenced,tags):raise ValueError('Unreferenced nodes prohibited')
 canonical_tets=np.sort(en,axis=1);canonical_tets=canonical_tets[np.lexsort(canonical_tets.T[::-1])]
 if len(np.unique(canonical_tets,axis=0))!=len(et):raise ValueError('Duplicate tetrahedra prohibited')
 boundary_snapshot(gmsh,helper)
 dims={};entities={};periodic=[]
 for dim,entity in gmsh.model.getEntities():
  if dim in [1,2]:
   masters=gmsh.model.mesh.getPeriodic(dim,[entity]);master,nodes,node_masters,transform=gmsh.model.mesh.getPeriodicNodes(dim,entity,True)
   if list(masters)!=[entity] or master!=entity or len(nodes) or len(node_masters) or len(transform):raise ValueError('Periodic mapping prohibited')
   periodic.append([dim,entity])
  for tag in gmsh.model.mesh.getNodes(dim,entity,False,False)[0]:
   tag=int(tag)
   if tag in dims:raise ValueError('Node classified twice')
   dims[tag]=dim;entities[tag]=[dim,entity]
 if set(dims)!=set(map(int,tags)) or any(dims[n]>=3 for n in range(1,17)) or any(dims[int(n)]!=3 for n in tags if n>16):
  raise ValueError('Complete cavity-shell/interior native classifications required')
 source_indices=np.searchsorted(tags,helper.F)
 exterior=helper.tetra_boundary(cells,source_indices);internal=helper.internal_face_orientation(cells)
 signed=helper.tetra_volumes(coords,cells);check_metric_rows(signed,len(et),'independent_signed_volume_mm3')
 total=math.fsum(signed);relative=abs(total/float(VOLUME)-1)
 if relative>1e-6:raise ValueError('Exact old cavity volume numerical bookkeeping bound failed')
 qualities={label:np.asarray(gmsh.model.mesh.getElementQualities(et,name)) for label,name in [('SICN','minSICN'),('Jacobian','minDetJac'),('native_volume_mm3','volume')]}
 for label,values in qualities.items():check_metric_rows(values,len(et),label)
 native_total=math.fsum(qualities['native_volume_mm3'])
 if abs(native_total/float(VOLUME)-1)>1e-6:raise ValueError('Native volume bookkeeping bound failed')
 report=dict(nodes=len(tags),tetrahedra=len(et),referenced_nodes=len(referenced),referenced_interior_nodes=int(np.count_nonzero(tags>16)),
  unreferenced_nodes=0,duplicate_tetrahedra=0,**exterior,**internal,
  node_classifications=[[n,dims[n]] for n in sorted(dims)],node_entity_classifications=[[n,*entities[n]] for n in sorted(entities)],
  node_counts_by_classification_dimension={str(d):sum(v==d for v in dims.values()) for d in range(4)},
  no_curve_or_surface_periodic_mapping=True,periodic_entities_checked=periodic,
  quality={k:helper.distribution(v) for k,v in qualities.items()},
  independent_signed_volume_mm3={'sum':total,'relative_error':relative,**helper.distribution(signed)},native_volume_sum_mm3=native_total,
  sorted_node_tags_sha256=helper.array_sha(tags),sorted_coordinates_sha256=helper.array_sha(coords),tetra_tags_sha256=helper.array_sha(et),
  tagged_tetra_connectivity_sha256=helper.array_sha(en),canonical_cells_sha256=helper.array_sha(canonical_tets),software_geometric_invariants_passed=True)
 arrays=dict(node_tags=tags.tolist(),coordinates_mm=coords.tolist(),tetra_tags=et.tolist(),tetra_node_tags=en.tolist(),
  native_qualities={k:v.tolist() for k,v in qualities.items()},independent_signed_volume_mm3=signed.tolist())
 return report,arrays,(tags,coords,et,en,canonical_tets),(*qualities.values(),signed)

def generate_once(gmsh,counts):
 counts['generate']+=1
 gmsh.model.mesh.generate(3)

def main():
 c=json.loads((OUT/'frozen-contract.json').read_text());require_contract(c)
 if {p.name for p in OUT.iterdir()}!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:
  raise ValueError('Only fresh materialized inputs and owned native.log are permitted')
 started=time.monotonic();gmsh=None;initialized=False;live={}
 report=dict(schema='962-fixed-shell-generation-apex1435493/v1',status='running',stage='imports',
  fixture_procedural_checks_passed=False,actual_SICN_gate_passed=False,actual_SICN_threshold=.1,
  native_operation_counts={k:0 for k in COUNTS},call_counts_are_attempts=True,options=OPTIONS,
  frozen_contract_sha256=sha(OUT/'frozen-contract.json'),local_shell_sha256=SHELL_SHA,input_MSH_read=False,full_head_geometry_read=False,
  head_execution_authorized=False,stitching_authorized=False,native_head_application_authorized=False,
  global_self_intersection_checked=False,geometric_tetrahedron_overlap_checked=False,
  new_interior_node_point_in_cavity_containment_checked=False,
  engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
 try:
  data=json.loads((ROOT/SHELL).read_text());shell_rows(data)
  helper,gmsh,observed,actual=load_audit_helper(c);report.update(runtime=observed,runtime_sha256s=actual)
  gmsh.initialize([],readConfigFiles=False,run=False);initialized=True
  gmsh.option.setNumber('General.Terminal',1);gmsh.logger.start()
  for key,value in OPTIONS.items():gmsh.option.setNumber(key,value)
  report['stage']='constructing_frozen_cavity_shell';report['shell']=construct_shell(gmsh,helper,data)
  report['original_source_classifications']=data['original_source_classifications']
  report['local_to_global_shell_node_tags']=data['local_to_global_node_tags']
  report['all16_shell_nodes_fixed_only_for_this_cavity_generation']=True
  before=boundary_snapshot(gmsh,helper)
  report['stage']='generating_once';generate_once(gmsh,report['native_operation_counts'])
  report['stage']='complete_generated_audit';live['after_generation']=inspect_cavity(gmsh,helper)
  require_boundary_same(before,boundary_snapshot(gmsh,helper))
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError('Fixed generation options changed')
  path=OUT/'cavity.msh';report['stage']='saving';report['native_operation_counts']['write_mesh']+=1
  gmsh.write(str(path));digest=sha(path)
  gmsh.clear();gmsh.open(str(path));report['stage']='complete_saved_reopen_audit'
  live['saved_reopen']=inspect_cavity(gmsh,helper)
  helper.require_same(live['after_generation'],live['saved_reopen'],'saved reopen')
  require_boundary_same(before,boundary_snapshot(gmsh,helper))
  if sha(path)!=digest:raise ValueError('Saved mesh changed during reopen')
  report.update(mesh_sha256=digest,mesh_bytes=path.stat().st_size,saved_mesh_identity_exact=True,
   exact_boundary_bits_faces_classifications=True,fixture_procedural_checks_passed=True,
   actual_SICN_gate_passed=helper.quality_gate(live['after_generation'][0]),stage='completed_all_local_checks',status='completed_specific_cavity_generation_only')
 except Exception as exc:report.update(status='failed_outputs_preserved',error=type(exc).__name__+': '+str(exc))
 finally:
  if initialized:
   report['gmsh_warnings_errors']=[s for s in gmsh.logger.get() if s.startswith(('Warning','Error'))]
   gmsh.logger.stop();gmsh.finalize()
  try:require_contract(c);report['bound_inputs_unchanged']=sha(OUT/'frozen-contract.json')==report['frozen_contract_sha256']
  except Exception:report['bound_inputs_unchanged']=False
  if live:
   save(OUT/'arrays.json',{name:item[1] for name,item in live.items()});report['full_tiny_arrays_sha256']=sha(OUT/'arrays.json')
  for name,item in live.items():report[name]=item[0]
  report['wall_seconds']=time.monotonic()-started;save(OUT/'fixture-report.json',report)
 return 0 if report['fixture_procedural_checks_passed'] and report['actual_SICN_gate_passed'] and report['bound_inputs_unchanged'] else 2

if __name__=='__main__':raise SystemExit(main())
