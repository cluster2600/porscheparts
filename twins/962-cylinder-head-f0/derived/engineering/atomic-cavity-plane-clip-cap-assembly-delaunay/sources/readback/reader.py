"""Audit one stopped Delaunay MSH; no generation, optimization or mesh writing."""
from pathlib import Path
import ast,hashlib,importlib.util,json,math,platform,sys,time
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent

def sha(path):
 digest=hashlib.sha256()
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
 return digest.hexdigest()

contract=json.loads((OUT/'frozen-contract.json').read_text())
if contract.get('native_read_only_audit_authorized') is not True or contract.get('source_and_guard_logic_reviewed') is not True:
 raise ValueError('Separate reviewed root authorization for this saved-file audit required')
if any((OUT/name).exists() or (OUT/name).is_symlink() for name in ['readback-report.json','readback-report.json.tmp','execution-receipt.json']):
 raise ValueError('A fresh saved-file audit output is required; previous evidence is preserved')

def require_inputs():
 for name,digest in contract['input_hashes'].items():
  relative=Path(name);path=ROOT/relative
  if relative.is_absolute() or '..' in relative.parts or path.is_symlink() or not path.is_file() or sha(path)!=digest:
   raise ValueError('Bound saved-Delaunay audit input changed: '+name)
 for name,digest in contract['external_runtime_hashes'].items():
  if sha(Path(name))!=digest:raise ValueError('Pinned saved-file runtime changed')
 if sha(OUT/'reader.py')!=contract['reader_sha256'] or sha(OUT/'run_readback.py')!=contract['runner_sha256']:
  raise ValueError('Materialized audit sources changed')

require_inputs()
work=ROOT/contract['native_output_directory'];receipt=json.loads((work/'receipt.json').read_text());worker=json.loads((work/'worker-report.json').read_text())
if receipt['returncode']!=-9 or receipt['stop_reason']!='native_deadline' or receipt['bound_inputs_unchanged'] is not True or receipt['worker_report']!=worker:
 raise ValueError('Exact stopped Delaunay result association required')
if contract['input_hashes'].get(str((work/'head-volume.msh').relative_to(ROOT)))!=contract['MSH_sha256']:raise ValueError('MSH identity must occur in the complete input map')
if (receipt['mesh_sha256']!=contract['MSH_sha256'] or worker['mesh_sha256']!=contract['MSH_sha256'] or receipt['mesh_bytes']!=contract['MSH_bytes'] or worker['mesh_bytes']!=contract['MSH_bytes'] or (work/'head-volume.msh').stat().st_size!=contract['MSH_bytes']):
 raise ValueError('Exact exported saved-file identity required')
for name,digest in receipt['source_sha256s'].items():
 if sha(ROOT/name)!=digest or sha(work/'source-snapshots'/Path(name).name)!=digest:
  raise ValueError('Executed Delaunay source/snapshot changed')
core_path=ROOT/contract['core_source']
if sha(core_path)!='a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4':raise ValueError('Exact frozen Delaunay core required before import')
spec=importlib.util.spec_from_file_location('_962_saved_delaunay_audit_core',core_path)
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
if ({str(path.relative_to(ROOT)):sha(path) for path in core.source_files()}!=receipt['source_sha256s'] or core.CANDIDATE_SHA!=contract['candidate_sha256'] or core.CANDIDATE_VOLUME!=contract['candidate_volume_mm3']):
 raise ValueError('Loaded exact frozen Delaunay core association changed')
core.require_admission(work/'surface-admission.json',receipt['admission_sha256'])
# Compile only these three unchanged functions; optimizer setup/worker code is not loaded.
helper=ROOT/contract['audit_helper_source']
if sha(helper)!='28746e14a041db464c3a41b732f1fc3e9ad9fd6ce96e886f728e5409d6ea0e36':raise ValueError('Exact reviewed audit helper required before AST selection')
names={'classifications','array_identity','audit_after'}
nodes=[node for node in ast.parse(helper.read_text()).body if isinstance(node,ast.FunctionDef) and node.name in names]
if len(nodes)!=3 or {node.name for node in nodes}!=names:raise ValueError('Exact selected saved-file audit helpers required')
namespace={'math':math};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),namespace)
import gmsh
if (gmsh.__version__!='4.15.2' or core.np.__version__!='2.0.2' or platform.machine()!='arm64' or sha(Path(gmsh.__file__))!=contract['runtime']['gmsh_module_sha256'] or sha(Path(gmsh.lib._name))!=contract['runtime']['libgmsh_sha256'] or sha(Path(sys.executable).resolve())!=contract['runtime']['python_executable_sha256']):
 raise ValueError('Exact native read-only runtime required')
points,faces=core.audit_quality_head.read(core.CANDIDATE)
points,faces=core.np.asarray(points,dtype=core.np.float64),core.np.asarray(faces,dtype=core.np.int64)
if (len(points),len(faces))!=(871731,1743878):raise ValueError('Exact current source surface counts required')
report=dict(status='reading_saved_mesh',stage='opening_saved_MSH',mesh_sha256=contract['MSH_sha256'],mesh_bytes=contract['MSH_bytes'],candidate_sha256=core.CANDIDATE_SHA,candidate_volume_reference_mm3=core.CANDIDATE_VOLUME,length_unit='mm',
 comparison_against_missing_worker_arrays_or_quality_performed=False,worker_volume_metrics_arrays_and_incidence_unavailable=True,
 direct_full_tetra_face_incidence_completed=False,direct_internal_face_orientation_completed=False,
 native_generate_optimize_meshwrite_solve_calls=0,engineering_accepted=False,manufacturing_authorized=False,
 mesh_convergence_established=False,thermal_resolution_established=False,
 runtime=dict(python=sys.version,numpy=core.np.__version__,gmsh=gmsh.__version__,machine=platform.machine(),executable_sha256=sha(Path(sys.executable).resolve()),gmsh_module_sha256=sha(Path(gmsh.__file__)),libgmsh_sha256=sha(Path(gmsh.lib._name))))
checkpoint=lambda:core.save(OUT/'readback-report.json',report)
started=time.monotonic();initialized=False;checkpoint()
try:
 gmsh.initialize([],readConfigFiles=False,run=False);initialized=True
 gmsh.option.setNumber('General.Terminal',0);gmsh.option.setNumber('General.NumThreads',2)
 gmsh.open(str(work/'head-volume.msh'))
 report['stage']='auditing_saved_tetrahedra_and_full_face_incidence';checkpoint()
 state,audit=namespace['audit_after'](core,gmsh,points,faces)
 node_tags=state[1];boundary=core.np.searchsorted(node_tags,core.np.arange(1,len(points)+1,dtype=core.np.uint64))
 if core.array_sha(state[0][boundary])!=core.array_sha(points):raise ValueError('Saved fixed-boundary coordinate bits differ from current source')
 report.update(audit=audit,direct_full_tetra_face_incidence_completed=True,direct_internal_face_orientation_completed=True,exact_source_boundary_coordinate_bits=True,source_points_sha256=core.array_sha(points),source_oriented_faces_sha256=core.array_sha(faces),stage='reopening_saved_file_for_tagged_array_identity');checkpoint()
 gmsh.clear();gmsh.open(str(work/'head-volume.msh'))
 again=core.tagged_volume(gmsh);identity=namespace['array_identity'](core,(again[0],again[2],again[3],again[4]))
 if identity!=audit['array_sha256s']:raise ValueError('Reopened saved-file tagged arrays changed')
 core.surface_roundtrip(gmsh,points,faces,exact_tagged_order=False)
 quality=audit['quality'];positive=all(row['nonpositive_count']==0 for row in quality.values())
 report.update(saved_file_reopen_array_identity_exact=True,reopened_array_sha256s=identity,SICN_point1_gate_passed=quality['minimum_SICN']['minimum']>=.1 and quality['minimum_SICN']['nonpositive_count']==0,all_four_metrics_finite_positive=positive,volume_relative_bookkeeping_bound=1e-6,bookkeeping_bound_is_not_manufacturing_tolerance=True)
 report['geometric_volume_numerical_checks_passed']=bool(report['SICN_point1_gate_passed'] and positive and audit['volume_relative_error']<=1e-6)
finally:
 if initialized:gmsh.finalize()
require_inputs();core.require_admission(work/'surface-admission.json',receipt['admission_sha256'])
report.update(status='direct_saved_file_audit_completed',stage='completed',bound_inputs_unchanged=True,readback_wall_seconds=time.monotonic()-started);checkpoint()
print(json.dumps({key:report[key] for key in ['status','SICN_point1_gate_passed','geometric_volume_numerical_checks_passed','readback_wall_seconds']}))
