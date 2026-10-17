"""HELD three tagged setters and complete local saved-cavity native readback only."""
from pathlib import Path
from fractions import Fraction
import hashlib,importlib.util,json,math,struct,sys,time

ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
CAVITY='work/962-engineering/fixed-shell-generation-apex1435493-prep-001/reader.py'
CAVITY_SHA='d5f23d2512d0cdc53c3f648eaca6b3c5aba3105b4b3d14470ceab5761afd5879'
CUBE='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/reader.py'
CUBE_SHA='97b7e9fc7d17defa84594c50dac1d4e09cd39bb47ef2059e00b6ac07fe8c029b'
INPUT='work/962-engineering/fixed-shell-netgen-apex1435493-001/cavity.msh'
INPUT_SHA='f3a48c8f4da651d80150ce5c1d514149fe9fa0b0dba728db06e9c0c8b374db6a'
WORKER='work/962-engineering/fixed-shell-netgen-apex1435493-001/fixture-report.json'
WORKER_SHA='8529a8f8421dd989ae243b2a06b132b8a2952e9847aa31d34adb74289a16e6c7'
ARRAYS='work/962-engineering/fixed-shell-netgen-apex1435493-001/arrays.json'
ARRAYS_SHA='ace411a27a13332129f515ac456ab453cbede0920fe115bdb82057092e665e5f'
CANDIDATE='work/962-engineering/fixed-shell-coupled-sicn-001/diagnostic.json'
CANDIDATE_SHA='e9184514108a194e9f483c5bfb20ffef9d8334cddd01f60806d97b96f84f532a'
PEER='work/962-engineering/fixed-shell-coupled-sicn-result-peer-001/review.json'
PEER_SHA='0adbeea0bef35c5a1f30f610c87bb27ef4333530ff2039e9e4c91a512287732b'
FREE=[27,28,29]
SHELL='work/962-engineering/direct-sicn-apex1435493-cavity-study-001/local-shell-input-001.json'
AUDIT_INPUTS={
 'twins/962-cylinder-head-f0/source/mesh_head.py':'69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5',
 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py':'a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4',
 'work/962-engineering/direct-sicn-apex1435493-cavity-study-001/local-shell-input-001.json':'a6f15db60967807b057e357b8f159fa510c4a8cf6e3cb44c4327323c070398c8'}
OPTIONS={'General.NumThreads':2,'Mesh.MaxNumThreads3D':2,'Mesh.Renumber':0,
 'Mesh.Optimize':0,'Mesh.OptimizeNetgen':0,'Mesh.OptimizeThreshold':.3,
 'Mesh.Binary':1,'Mesh.SaveAll':1,'Mesh.MshFileVersion':4.1}
COUNTS={'generate':0,'createGeometry_dim3':0,'optimize_Netgen':0,'setNode':3,
 'rebuildElementCache':1,'write_mesh':1,'solve':0}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_cavity_module():
 spec=importlib.util.spec_from_file_location('frozen_specific_cavity_audit',ROOT/CAVITY)
 cavity=importlib.util.module_from_spec(spec);spec.loader.exec_module(cavity)
 return cavity

def expected_live(helper,worker,arrays):
 np=helper.np;a=arrays['saved_reopen']
 state=[np.asarray(a[key],dtype=dtype) for key,dtype in [('node_tags','<u8'),('coordinates_mm','<f8'),('tetra_tags','<u8'),('tetra_node_tags','<u8')]]
 canonical=np.sort(state[3],axis=1);canonical=canonical[np.lexsort(canonical.T[::-1])]
 quality=[np.asarray(a['native_qualities'][name],dtype='<f8') for name in ['SICN','Jacobian','native_volume_mm3']]
 quality.append(np.asarray(a['independent_signed_volume_mm3'],dtype='<f8'))
 return worker['saved_reopen'],a,(*state,canonical),tuple(quality)

def require_before(helper,opened,expected):
 helper.require_same(expected,opened,'fresh saved-cavity before-state')
 if opened[0]!=expected[0]:raise ValueError('Complete fresh before report differs from the single saved-state proof')


def require_authority(c):
 if (c.get('native_execution_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or c.get('selected_runtime_review_complete') is not True or c.get('local_candidate_application_authorized') is not True
     or any(c.get(k) is not False for k in ['generation_authorized','cavity_Netgen_optimizer_authorized',
      'head_execution_authorized','stitching_authorized','native_head_application_authorized',
      'engineering_accepted','physics_qualified','manufacturing_authorized'])):
  raise ValueError('Reviewed local three-setter readback-only authority required')
 if (not isinstance(c.get('output_directory'),str) or OUT.parent!=ROOT/'work/962-engineering'
     or (ROOT/c['output_directory']).resolve()!=OUT):raise ValueError('Exact fresh actual output required')
 if (c.get('options')!=OPTIONS or c.get('declared_operation_counts')!=COUNTS or c.get('automatic_retry') is not False
     or c.get('input_mesh')!=INPUT or c.get('input_mesh_sha256')!=INPUT_SHA
     or c.get('candidate')!=CANDIDATE or c.get('candidate_sha256')!=CANDIDATE_SHA or c.get('selected_tags')!=FREE):
  raise ValueError('Fixed original mesh, candidate and three setter rows required')


def require_contract(c):
 require_authority(c)
 for name,digest in [(CAVITY,CAVITY_SHA),(CUBE,CUBE_SHA),(INPUT,INPUT_SHA),(WORKER,WORKER_SHA),(ARRAYS,ARRAYS_SHA),(CANDIDATE,CANDIDATE_SHA),(PEER,PEER_SHA),*AUDIT_INPUTS.items()]:
  if c['input_hashes'].get(name)!=digest:raise ValueError('Consumed source/data/peer must be direct pinned: '+name)
 for name,digest in c['input_hashes'].items():
  if Path(name).is_absolute() or (ROOT/name).is_symlink() or not (ROOT/name).resolve().is_relative_to(ROOT) or sha(ROOT/name)!=digest:
   raise ValueError('Input drift: '+name)
 if len(c['external_runtime_hashes'])!=3:raise ValueError('Selected three native runtime identities required')
 for name,digest in c['external_runtime_hashes'].items():
  if sha(Path(name))!=digest:raise ValueError('Runtime drift')
 if (sha(OUT/'reader.py')!=c['reader_sha256'] or sha(OUT/'run_readback.py')!=c['runner_sha256']
     or sha(Path(sys.executable).resolve())!=c['runtime']['python_executable_sha256']):
  raise ValueError('Materialized source or selected Python changed')


def require_saved_baseline(worker):
 r=worker.get('saved_reopen',{});q=r.get('quality',{}).get('SICN',{})
 if (worker.get('status')!='completed_specific_cavity_Netgen_only' or worker.get('fixture_procedural_checks_passed') is not True
     or worker.get('actual_SICN_gate_passed') is not False or worker.get('saved_mesh_identity_exact') is not True
     or worker.get('bound_inputs_unchanged') is not True or worker.get('mesh_sha256')!=INPUT_SHA
     or worker.get('mesh_bytes')!=3486 or worker.get('full_tiny_arrays_sha256')!=ARRAYS_SHA
     or (r.get('nodes'),r.get('tetrahedra'),r.get('referenced_interior_nodes'),r.get('unreferenced_nodes'))!=(19,39,3,0)
     or (q.get('count'),q.get('below_point1_count'),q.get('nonpositive_count'),q.get('minimum'))!=(39,2,0,.08909847620076504)):
  raise ValueError('Exact original stopped Netgen19/39 baseline required')


def candidate_rows(d,a):
 tags=list(range(1,17))+FREE
 if (d.get('status') not in ['exact_feasible_point_solver_converged_native_unapproved','feasible_point_solver_not_converged']
     or d.get('all39_exact_quality_gate') is not True or d.get('procedural_checks_passed') is not True
     or d.get('all16_shell_coordinate_bits_unchanged') is not True or d.get('original_array_bits_unchanged') is not True
     or d.get('free_tags')!=FREE or d.get('full_source_nodes')!=19 or d.get('full_cells')!=39
     or a['node_tags']!=tags or len(a['tetra_tags'])!=39 or len(a['tetra_node_tags'])!=39):
  raise ValueError('Exact finite all39 analytic candidate and original19/39 association required')
 if any(d['input_hashes'].get(str(ROOT/name))!=digest for name,digest in [(ARRAYS,ARRAYS_SHA),(WORKER,WORKER_SHA),(SHELL,AUDIT_INPUTS[SHELL])]):
  raise ValueError('Candidate source-state direct pins differ')
 qualification={'native_application_authorized':False,'head_execution_authorized':False,'stitching_authorized':False,
  'engineering_accepted':False,'physics_qualified':False,'manufacturing_authorized':False}
 if d.get('qualification')!=qualification:raise ValueError('Analytic candidate grants no native/head/physical authority')
 rows=d['complete_proposed_coordinate_rows']
 if [r['node_tag'] for r in rows]!=tags or len(rows)!=19:raise ValueError('All19 sorted candidate rows required')
 old=dict(zip(a['node_tags'],a['coordinates_mm']));coordinates=[];changes=[]
 for row in rows:
  t=row['node_tag'];xyz=row['coordinates_mm'];words=row['binary64_hex']
  if (len(xyz)!=3 or len(words)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in xyz)
      or any(type(h) is not str or float(v).hex()!=h or struct.pack('<d',float.fromhex(h))!=struct.pack('<d',v) for v,h in zip(xyz,words))):
   raise ValueError('Exact finite candidate coordinate/hex association required')
  changed=struct.pack('<3d',*xyz)!=struct.pack('<3d',*old[t])
  if changed and t not in FREE:raise ValueError('Any shell coordinate bit drift refused')
  if changed:changes.append(t)
  coordinates.append([float(v) for v in xyz])
 exact=d['all39_signed_quality_rows']
 if len(exact)!=39 or [row['tetrahedron_tag'] for row in exact]!=a['tetra_tags']:
  raise ValueError('Complete39 exact candidate cell identities required')
 for proof,conn in zip(exact,a['tetra_node_tags']):
  det=proof['exact_native_ordered_determinant_mm3'];q=proof['exact_SICN_squared']
  if (proof['ordered_node_tags']!=conn or proof.get('positive_orientation') is not True or proof.get('exact_point1_gate_passed') is not True
      or not isinstance(q,dict) or Fraction(int(det['numerator']),int(det['denominator']))<=0
      or Fraction(int(q['numerator']),int(q['denominator']))<Fraction(1,100)):
   raise ValueError('Every saved exact candidate determinant/quality gate required')
 return coordinates,changes


def apply_once(gmsh,coordinates,counts):
 # The coordinate27 row is allowed to be an identity; every requested setter is counted as an attempt.
 for tag,xyz in zip(FREE,coordinates[-3:]):
  counts['setNode']+=1
  gmsh.model.mesh.setNode(tag,list(xyz),[])
 counts['rebuildElementCache']+=1
 gmsh.model.mesh.rebuildElementCache(False)


def require_applied_state(before,after,coordinates):
 a,b=before[1],after[1]
 if any(a[key]!=b[key] for key in ['node_tags','tetra_tags','tetra_node_tags']):
  raise ValueError('All19 node tags and39 native ordered cell rows must remain exact')
 if struct.pack('<'+'d'*57,*[v for row in b['coordinates_mm'] for v in row])!=struct.pack('<'+'d'*57,*[v for row in coordinates for v in row]):
  raise ValueError('Native returned coordinates differ from exact candidate bytes')
 for key in ['node_classifications','node_entity_classifications','node_counts_by_classification_dimension',
             'no_curve_or_surface_periodic_mapping','periodic_entities_checked']:
  if before[0][key]!=after[0][key]:raise ValueError('Full native classifications/periodic associations changed')


def main():
 c=json.loads((OUT/'frozen-contract.json').read_text());require_contract(c)
 if {p.name for p in OUT.iterdir()}!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:
  raise ValueError('Only fresh materialized inputs and native.log permitted')
 started=time.monotonic();gmsh=None;initialized=False;live={}
 report=dict(schema='962-specific-coupled-cavity-native-application/v1',status='running',stage='imports',
  fixture_procedural_checks_passed=False,actual_SICN_gate_passed=False,actual_SICN_threshold=.1,
  native_operation_counts={k:0 for k in COUNTS},call_counts_are_attempts=True,options=OPTIONS,
  frozen_contract_sha256=sha(OUT/'frozen-contract.json'),input_mesh_sha256=INPUT_SHA,candidate_sha256=CANDIDATE_SHA,
  requested_setter_tags=FREE,full_head_geometry_read=False,generation_authorized=False,optimizer_authorized=False,
  head_execution_authorized=False,stitching_authorized=False,native_head_application_authorized=False,
  engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False,
  global_self_intersection_checked=False,geometric_tetrahedron_overlap_checked=False,new_interior_node_point_in_cavity_containment_checked=False,
  epigraph_t_used_for_native_quality_gate=False,interior_ancestry_inferred=False)
 try:
  worker=json.loads((ROOT/WORKER).read_text());require_saved_baseline(worker)
  arrays=json.loads((ROOT/ARRAYS).read_text());candidate=json.loads((ROOT/CANDIDATE).read_text())
  coordinates,changes=candidate_rows(candidate,arrays['saved_reopen'])
  report['actual_coordinate_change_tags']=changes
  cavity=load_cavity_module();helper,gmsh,observed,actual=cavity.load_audit_helper(c);report.update(runtime=observed,runtime_sha256s=actual)
  if c['expected_runtime']!=cavity.RUNTIME:raise ValueError('Fixed expected runtime changed')
  data=json.loads((ROOT/cavity.SHELL).read_text());points,faces,shell=cavity.shell_rows(data)
  helper.P=helper.np.asarray(points,dtype='<f8');helper.F=helper.np.asarray(faces,dtype=helper.np.int64)
  expected=expected_live(helper,worker,arrays)
  gmsh.initialize([],readConfigFiles=False,run=False);initialized=True
  gmsh.option.setNumber('General.Terminal',1);gmsh.logger.start()
  for key,value in OPTIONS.items():gmsh.option.setNumber(key,value)
  gmsh.open(str(ROOT/INPUT));report['stage']='full_original_before_audit';live['before']=cavity.inspect_cavity(gmsh,helper)
  require_before(helper,live['before'],expected);boundary=cavity.boundary_snapshot(gmsh,helper)
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError('Options changed before setters')
  report.update(single_original_Netgen_before_state_exact=True,shell=shell,
   original_source_classifications=data['original_source_classifications'],all16_shell_nodes_fixed_for_this_local_operation=True)
  report['stage']='three_setters_and_cache';apply_once(gmsh,coordinates,report['native_operation_counts'])
  report['stage']='full_after_audit';live['after']=cavity.inspect_cavity(gmsh,helper)
  require_applied_state(live['before'],live['after'],coordinates)
  cavity.require_boundary_same(boundary,cavity.boundary_snapshot(gmsh,helper))
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError('Options changed after setters')
  path=OUT/'cavity.msh';report['stage']='saving';report['native_operation_counts']['write_mesh']+=1
  gmsh.write(str(path));digest=sha(path);gmsh.clear();gmsh.open(str(path))
  report['stage']='full_saved_reopen_audit';live['saved_reopen']=cavity.inspect_cavity(gmsh,helper)
  helper.require_same(live['after'],live['saved_reopen'],'saved reopen')
  if live['after'][0]!=live['saved_reopen'][0]:raise ValueError('Complete after/saved reports differ')
  require_applied_state(live['before'],live['saved_reopen'],coordinates)
  cavity.require_boundary_same(boundary,cavity.boundary_snapshot(gmsh,helper))
  if sha(path)!=digest:raise ValueError('Saved mesh changed during reopen')
  report.update(mesh_sha256=digest,mesh_bytes=path.stat().st_size,saved_mesh_identity_exact=True,
   exact_boundary_bits_faces_classifications=True,all39_ordered_connectivity_and19node_tags_exact=True,
   candidate_coordinate_bits_exact=True,fixture_procedural_checks_passed=True,
   actual_SICN_gate_passed=helper.quality_gate(live['after'][0]),stage='completed_all_local_checks',status='completed_specific_cavity_coordinate_application_only')
 except Exception as exc:report.update(status='failed_outputs_preserved',error=type(exc).__name__+': '+str(exc))
 finally:
  if initialized:
   report['gmsh_warnings_errors']=[s for s in gmsh.logger.get() if s.startswith(('Warning','Error'))]
   gmsh.logger.stop();gmsh.finalize()
  try:require_contract(c);report['bound_inputs_unchanged']=sha(OUT/'frozen-contract.json')==report['frozen_contract_sha256']
  except Exception:report['bound_inputs_unchanged']=False
  if live:
   with (OUT/'arrays.json').open('x') as stream:json.dump({name:item[1] for name,item in live.items()},stream,indent=2,allow_nan=False);stream.write('\n')
   report['full_tiny_arrays_sha256']=sha(OUT/'arrays.json')
  for name,item in live.items():report[name]=item[0]
  report['wall_seconds']=time.monotonic()-started
  with (OUT/'fixture-report.json').open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
 return 0 if report['fixture_procedural_checks_passed'] and report['actual_SICN_gate_passed'] and report['bound_inputs_unchanged'] else 2

if __name__=='__main__':raise SystemExit(main())
