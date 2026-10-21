"""HELD fixed-shell cube generation witness; no head or cavity execution."""
from pathlib import Path
from fractions import Fraction
import hashlib,importlib.util,json,math,platform,sys,time

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
HELPER='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/reader.py'
HELPER_SHA='97b7e9fc7d17defa84594c50dac1d4e09cd39bb47ef2059e00b6ac07fe8c029b'
OPTIONS={'General.NumThreads':2,'Mesh.MaxNumThreads3D':2,'Mesh.Algorithm3D':1,
 'Mesh.MeshOnlyEmpty':1,'Mesh.Renumber':0,'Mesh.ElementOrder':1,'Mesh.Optimize':0,
 'Mesh.OptimizeNetgen':0,'Mesh.MeshSizeExtendFromBoundary':0,'Mesh.RandomSeed':1,
 'Mesh.Binary':1,'Mesh.SaveAll':1,'Mesh.MshFileVersion':4.1}
RUNTIME={'python':'3.10.11','numpy':'2.0.2','gmsh':'4.15.2','machine':'arm64'}
COUNTS={'generate':1,'createGeometry_dim3':0,'optimize_Netgen':0,
 'rebuildElementCache':0,'write_mesh':1,'solve':0}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def save(path,value):
 with Path(path).open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')

def validate_shell(points,faces):
 if (len(points)!=8 or any(len(p)!=3 or any(not math.isfinite(float(x)) for x in p) for p in points)
     or len(faces)!=12 or any(len(f)!=3 or len(set(f))!=3 or any(type(t) is not int or not 1<=t<=8 for t in f) for f in faces)):
  raise ValueError('Exact finite eight-node/twelve-triangle shell required')
 edges={};keys=set()
 for face in faces:
  key=tuple(sorted(face))
  if key in keys:raise ValueError('Duplicate shell face')
  keys.add(key)
  for i in range(3):edges.setdefault(tuple(sorted((face[i],face[(i+1)%3]))),[]).append((face[i],face[(i+1)%3]))
 if any(len(v)!=2 or v[0]!=v[1][::-1] for v in edges.values()):
  raise ValueError('Closed oppositely oriented shell required before meshing')
 p=[[Fraction.from_float(float(v)) for v in row] for row in points]
 cross=lambda a,b:[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
 volume=sum((sum(x*y for x,y in zip(p[f[0]-1],cross(p[f[1]-1],p[f[2]-1])))/6 for f in faces),Fraction(0))
 if volume!=343:raise ValueError('Exact literal oriented shell volume must be 343 mm3')
 return {'vertices':8,'faces':12,'edges':len(edges),'signed_volume_mm3':343}

def require_authority(c):
 if (c.get('native_execution_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or c.get('selected_runtime_review_complete') is not True or c.get('head_execution_authorized') is not False
     or c.get('cavity_execution_authorized') is not False or c.get('manufacturing_authorized') is not False):
  raise ValueError('Reviewed tiny generation-only authority required')
 if (not isinstance(c.get('output_directory'),str) or OUT.parent!=ROOT/'work/962-engineering'
     or (ROOT/c['output_directory']).resolve()!=OUT):raise ValueError('Exact fresh actual output binding required')
 if (c.get('options')!=OPTIONS or c.get('expected_runtime')!=RUNTIME or c.get('declared_operation_counts')!=COUNTS
     or c.get('automatic_retry') is not False or c.get('audit_helper_source')!=HELPER
     or c.get('audit_helper_sha256')!=HELPER_SHA):raise ValueError('Fixed source, options and operation policy required')

def require_contract(c):
 require_authority(c)
 if c['input_hashes'].get(HELPER)!=HELPER_SHA:raise ValueError('Exact helper must be a direct pin')
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
 path=ROOT/HELPER
 if sha(path)!=HELPER_SHA:raise ValueError('Audit helper changed')
 spec=importlib.util.spec_from_file_location('fixed_shell_cube_audit',path)
 helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 if helper.np is not np:raise ValueError('Audit helper NumPy object changed')
 helper.gmsh=gmsh
 return helper,gmsh,observed,actual

def construct_shell(gmsh,helper):
 proof=validate_shell(helper.P.tolist(),helper.F.tolist())
 gmsh.model.add('fixed_shell_generation_cube')
 gmsh.model.addDiscreteEntity(2,1)
 gmsh.model.mesh.addNodes(2,1,list(range(1,9)),helper.P.ravel())
 gmsh.model.mesh.addElementsByType(1,2,list(range(1,13)),helper.F.ravel())
 gmsh.model.geo.addSurfaceLoop([1],1);gmsh.model.geo.addVolume([1],1)
 gmsh.model.geo.synchronize()
 return proof

def boundary_snapshot(gmsh,helper):
 np=helper.np;tags,xyz,_=gmsh.model.mesh.getNodes();order=np.argsort(tags)
 tags=np.asarray(tags)[order];xyz=np.asarray(xyz).reshape(-1,3)[order];ix=np.searchsorted(tags,np.arange(1,9))
 if np.any(ix>=len(tags)) or not np.array_equal(tags[ix],np.arange(1,9)):raise ValueError('Boundary tags missing')
 bits=xyz[ix].astype('<f8',copy=False).tobytes()
 if bits!=helper.P.astype('<f8',copy=False).tobytes():raise ValueError('Boundary coordinate bits changed')
 types,element_tags,element_nodes=gmsh.model.mesh.getElements(2)
 if list(types)!=[2] or len(element_tags[0])!=12:raise ValueError('Exactly twelve TRI3 elements required')
 faces=sorted((int(t),helper.canonical(row)) for t,row in zip(element_tags[0],np.asarray(element_nodes[0]).reshape(-1,3)))
 expected=sorted((i+1,helper.canonical(row)) for i,row in enumerate(helper.F))
 if faces!=expected:raise ValueError('Tagged oriented shell triangles changed')
 classes={}
 for dim,entity in gmsh.model.getEntities():
  for tag in gmsh.model.mesh.getNodes(dim,entity,False,False)[0]:
   if int(tag)<=8:
    if int(tag) in classes:raise ValueError('Boundary node classified twice')
    classes[int(tag)]=(dim,entity)
 if set(classes)!=set(range(1,9)) or any(dim>=3 for dim,entity in classes.values()):raise ValueError('Boundary classification missing')
 return {'coordinate_bytes':bits,'tagged_oriented_triangles':faces,'classifications':sorted(classes.items())}

def require_boundary_same(before,after):
 if before!=after:raise ValueError('Every boundary coordinate bit, tagged oriented face and classification must remain exact')

def generate_once(gmsh,counts):
 counts['generate']+=1
 gmsh.model.mesh.generate(3)

def main():
 c=json.loads((OUT/'frozen-contract.json').read_text());require_contract(c)
 if {p.name for p in OUT.iterdir()}!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:
  raise ValueError('Only fresh materialized tiny inputs and owned native.log are permitted')
 started=time.monotonic();gmsh=None;initialized=False;live={}
 report=dict(schema='962-fixed-shell-generation-cube/v1',status='running',stage='imports',
  fixture_procedural_checks_passed=False,actual_SICN_gate_passed=False,actual_SICN_threshold=.1,
  native_operation_counts={k:0 for k in COUNTS},call_counts_are_attempts=True,
  options=OPTIONS,frozen_contract_sha256=sha(OUT/'frozen-contract.json'),input_MSH_read=False,
  head_geometry_read=False,head_execution_authorized=False,cavity_execution_authorized=False,
  engineering_accepted=False,manufacturing_authorized=False)
 try:
  helper,gmsh,observed,actual=load_audit_helper(c);report.update(runtime=observed,runtime_sha256s=actual)
  gmsh.initialize([],readConfigFiles=False,run=False);initialized=True
  gmsh.option.setNumber('General.Terminal',1);gmsh.logger.start()
  for key,value in OPTIONS.items():gmsh.option.setNumber(key,value)
  report['stage']='constructing_literal_shell';report['shell']=construct_shell(gmsh,helper)
  before=boundary_snapshot(gmsh,helper)
  report['stage']='generating_once';generate_once(gmsh,report['native_operation_counts'])
  report['stage']='complete_generated_audit';live['after_generation']=helper.inspect_live()
  require_boundary_same(before,boundary_snapshot(gmsh,helper))
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError('Fixed generation options changed')
  path=OUT/'cube.msh';report['stage']='saving';report['native_operation_counts']['write_mesh']+=1
  gmsh.write(str(path));digest=sha(path)
  gmsh.clear();gmsh.open(str(path));report['stage']='complete_saved_reopen_audit'
  live['saved_reopen']=helper.inspect_live()
  helper.require_same(live['after_generation'],live['saved_reopen'],'saved reopen')
  require_boundary_same(before,boundary_snapshot(gmsh,helper))
  if sha(path)!=digest:raise ValueError('Saved mesh changed during reopen')
  report.update(mesh_sha256=digest,mesh_bytes=path.stat().st_size,saved_mesh_identity_exact=True,
   exact_boundary_bits_faces_classifications=True,fixture_procedural_checks_passed=True,
   actual_SICN_gate_passed=helper.quality_gate(live['after_generation'][0]),stage='completed_all_local_checks',status='completed_cube_generation_only')
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
