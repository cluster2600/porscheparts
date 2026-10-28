"""HELD one selected current204 saved-case Netgen operation; no generation, stitching or head apply."""
from pathlib import Path
import ast,hashlib,importlib.util,json,sys,time

ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
CAVITY='work/962-engineering/head-star-current204-local-stages-prep-001/generate_case.py'
CAVITY_SHA='fc1aba0a0ae93995f8fc4eea86d3fe693ce0360ac3f98d158ba5f01ae8983e3d'
CUBE='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/reader.py'
CUBE_SHA='97b7e9fc7d17defa84594c50dac1d4e09cd39bb47ef2059e00b6ac07fe8c029b'
MANIFEST='work/962-engineering/head-star-current204-local-stages-prep-001/case-manifest.json'
MANIFEST_SHA='3a558ede04cbc52c59e401befb36b8983ebd9b7f57d4266de0bea38fb1a963c5'
BATCH='work/962-engineering/head-star-current204-batch-shells-001/report.json'
BATCH_SHA='4f9fc0354918a907083006484d534c34c3b2621dfcc83b00cc4a4b731f009e86'
INPUT=INPUT_SHA=WORKER=WORKER_SHA=ARRAYS=ARRAYS_SHA=None
AUDIT_INPUTS={'twins/962-cylinder-head-f0/source/mesh_head.py':'69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5','work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py':'a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4',MANIFEST:MANIFEST_SHA,BATCH:BATCH_SHA}
BATCH_EVIDENCE={'work/962-engineering/head-star-current204-batch-shells-001/receipt.json': '78e215c5c85f01ca614e44e4e443fd4181086f63e2edc5d5aee81fbef77dbedb', 'work/962-engineering/head-star-current204-batch-shells-root-execution-001/closed-result.json': '67d9b2763fcd5ac887eddca79010d8a21dc6365b19f56224512acbaf7a3150e2', 'work/962-engineering/head-star-current204-batch-shells-root-execution-001/result-review.json': '5a80128a5e4dd3ea685449c1124fd1fad4c07a3bb1c586f9f80a2e26caacf913', 'work/962-engineering/head-star-current204-batch-shells-result-peer-001/review.json': '3fd325b3e4e18b942bda26d9292127d1dc1c2b8ecc5841d11257dc61884030da', 'work/962-engineering/head-star-current204-batch-shells-root-execution-001/result-peer-acceptance.json': '47a98aad883748178b7b25a1a5957ca01c0780eb0274f778567e6c5fb22fe538'}
GENERATION_RUNNER='work/962-engineering/head-star-current204-local-stages-prep-001/run_generation.py'
GENERATION_RUNNER_SHA='05b4f8996f1f642120b70be755e6609f7b641041cad1a867ea8da9e56ecb423b'
AUDIT_INPUTS.update(BATCH_EVIDENCE)
AUDIT_INPUTS[GENERATION_RUNNER]=GENERATION_RUNNER_SHA
OPTIONS={'General.NumThreads':2,'Mesh.MaxNumThreads3D':2,'Mesh.Renumber':0,
 'Mesh.Optimize':0,'Mesh.OptimizeNetgen':0,'Mesh.OptimizeThreshold':.3,
 'Mesh.Binary':1,'Mesh.SaveAll':1,'Mesh.MshFileVersion':4.1}
COUNTS={'generate':0,'createGeometry_dim3':1,'optimize_Netgen':1,
 'rebuildElementCache':1,'write_mesh':1,'solve':0}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def require_authority(c):
 if (c.get('native_execution_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or c.get('selected_runtime_review_complete') is not True or c.get('cavity_Netgen_optimizer_authorized') is not True
     or any(c.get(k) is not False for k in ['generation_authorized','head_execution_authorized','stitching_authorized',
      'native_head_application_authorized','engineering_accepted','physics_qualified','manufacturing_authorized'])):
  raise ValueError('Reviewed specific saved-cavity optimizer-only authority required')
 if (not isinstance(c.get('output_directory'),str) or OUT.parent!=ROOT/'work/962-engineering'
     or (ROOT/c['output_directory']).resolve()!=OUT):raise ValueError('Exact fresh actual output binding required')
 if (c.get('options')!=OPTIONS or c.get('declared_operation_counts')!=COUNTS or c.get('automatic_retry') is not False
     or c.get('optimization')!={'method':'Netgen','force':True} or c.get('geometry_creation_dim_tags')!=[[3,1]]):
  raise ValueError('Fixed saved input, options and one-operation policy required')

def require_contract(c):
 require_authority(c)
 configure_baseline(c)
 for name,digest in [(CAVITY,CAVITY_SHA),(CUBE,CUBE_SHA),(INPUT,INPUT_SHA),(WORKER,WORKER_SHA),(ARRAYS,ARRAYS_SHA)]:
  if c['input_hashes'].get(name)!=digest:raise ValueError('Exact input/helper must be a direct pin')
 for name,digest in AUDIT_INPUTS.items():
  if c['input_hashes'].get(name)!=digest:raise ValueError('Every consumed audit source and shell input must be a direct pin')
 for name,digest in c['input_hashes'].items():
  if Path(name).is_absolute() or not (ROOT/name).resolve().is_relative_to(ROOT):raise ValueError('Project-relative input pin required')
  if sha(ROOT/name)!=digest:raise ValueError('Input drift: '+name)
 if len(c['external_runtime_hashes'])!=3:raise ValueError('Selected three native runtime identities required')
 for name,digest in c['external_runtime_hashes'].items():
  if sha(Path(name))!=digest:raise ValueError('Runtime drift')
 if (sha(OUT/'reader.py')!=c['reader_sha256'] or sha(OUT/'run_readback.py')!=c['runner_sha256']
     or sha(Path(sys.executable).resolve())!=c['runtime']['python_executable_sha256']):
  raise ValueError('Materialized source or selected Python changed')

def configure_baseline(c):
 global INPUT,INPUT_SHA,WORKER,WORKER_SHA,ARRAYS,ARRAYS_SHA
 b=c['generation_baseline'];directory='work/962-engineering/head-star-current204-apex-'+str(c['case_apex'])+'-generation-001'
 expected={'mesh':directory+'/cavity.msh','worker':directory+'/fixture-report.json','arrays':directory+'/arrays.json','receipt':directory+'/execution-receipt.json','actual':directory+'/frozen-contract.json'}
 if set(b)!=set(expected)|{'root_closed','result_peer'} or any(b[k]['path']!=v for k,v in expected.items()):raise ValueError('Same-case generation plus root closure and stopped peer direct pins required')
 for row in b.values():
  if not isinstance(row,dict) or c['input_hashes'].get(row['path'])!=row['sha256']:raise ValueError('All stopped generation/proof records must be direct pins')
 INPUT,INPUT_SHA=b['mesh']['path'],b['mesh']['sha256'];WORKER,WORKER_SHA=b['worker']['path'],b['worker']['sha256'];ARRAYS,ARRAYS_SHA=b['arrays']['path'],b['arrays']['sha256']

def load_cavity_module():
 spec=importlib.util.spec_from_file_location('frozen_specific_cavity_audit',ROOT/CAVITY)
 cavity=importlib.util.module_from_spec(spec);spec.loader.exec_module(cavity)
 return cavity

def require_saved_baseline(worker,c,case):
 r=worker.get('saved_reopen',{});q=r.get('quality',{}).get('SICN',{});b=c['generation_baseline']
 if (worker.get('status')!='completed_finite_selected_cavity_generation_only' or worker.get('fixture_procedural_checks_passed') is not True
     or worker.get('actual_SICN_gate_passed') is not False or worker.get('next_stage')!='one_Netgen'
     or worker.get('saved_mesh_identity_exact') is not True or worker.get('bound_inputs_unchanged') is not True
     or worker.get('case_apex')!=case['apex'] or worker.get('case_key')!=case['case_key']
     or worker.get('case_record_sha256')!=case['source_record_sha256'] or worker.get('case_manifest_sha256')!=MANIFEST_SHA
     or worker.get('local_shell_serialized_sha256')!=case['shell_serialized_sha256']
     or worker.get('source_batch_sha256')!=BATCH_SHA or worker.get('mesh_sha256')!=INPUT_SHA
     or worker.get('mesh_bytes')!=b['mesh']['bytes'] or worker.get('full_tiny_arrays_sha256')!=ARRAYS_SHA
     or worker.get('after_generation')!=r or r.get('unreferenced_nodes')!=0
     or type(r.get('tetrahedra')) is not int or r['tetrahedra']<=0 or q.get('count')!=r['tetrahedra']
     or type(q.get('nonpositive_count')) is not int or not 0<=q['nonpositive_count']<=r['tetrahedra'] or type(q.get('minimum')) not in (int,float)
     or q['minimum']>=.1 or q.get('below_point1_count',0)<=0):
  raise ValueError('Same-case stopped procedural generation with actual strict-quality rejection required')
 receipt=json.loads((ROOT/b['receipt']['path']).read_text())
 if (receipt.get('returncode')!=2 or receipt.get('stop_reason') is not None
     or receipt.get('fixture_report_sha256')!=WORKER_SHA or receipt.get('contract_sha256')!=b['actual']['sha256']
     or receipt.get('reader_sha256')!=CAVITY_SHA or receipt.get('runner_sha256')!=GENERATION_RUNNER_SHA
     or c.get('generation_runner_sha256')!=GENERATION_RUNNER_SHA):
  raise ValueError('Natural procedural generation quality rejection receipt required; stopped/error runs are never retried')


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

def main():
 c=json.loads((OUT/'frozen-contract.json').read_text());require_contract(c)
 if {p.name for p in OUT.iterdir()}!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:
  raise ValueError('Only fresh materialized inputs and owned native.log are permitted')
 started=time.monotonic();gmsh=None;initialized=False;live={}
 report=dict(next_stage='hold_case',later_head_storage_compatible=False,schema='962-finite-selected-current204-Netgen/v1',status='running',stage='imports',
  fixture_procedural_checks_passed=False,actual_SICN_gate_passed=False,actual_SICN_threshold=.1,
  native_operation_counts={k:0 for k in COUNTS},call_counts_are_attempts=True,options=OPTIONS,
  frozen_contract_sha256=sha(OUT/'frozen-contract.json'),input_mesh_sha256=INPUT_SHA,input_worker_sha256=WORKER_SHA,input_arrays_sha256=ARRAYS_SHA,
  full_head_geometry_read=False,generation_authorized=False,head_execution_authorized=False,stitching_authorized=False,
  native_head_application_authorized=False,engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False,
  global_self_intersection_checked=False,geometric_tetrahedron_overlap_checked=False,new_interior_node_point_in_cavity_containment_checked=False,
  dynamic_interior_count_and_retagging_allowed=True,interior_ancestry_inferred=False)
 try:
  cavity=load_cavity_module();case,data=cavity.configure_case(c,stage='netgen')
  worker=json.loads((ROOT/WORKER).read_text());require_saved_baseline(worker,c,case)
  arrays=json.loads((ROOT/ARRAYS).read_text())
  helper,gmsh,observed,actual=cavity.load_audit_helper(c);report.update(runtime=observed,runtime_sha256s=actual)
  if c['expected_runtime']!=cavity.RUNTIME:raise ValueError('Fixed expected runtime changed')
  points,faces,shell=cavity.shell_rows(data)
  helper.P=helper.np.asarray(points,dtype='<f8');helper.F=helper.np.asarray(faces,dtype=helper.np.int64)
  tree=ast.parse((ROOT/CUBE).read_text());names=['geometry_flag_only','optimize_once']
  selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
  if {n.name for n in selected}!=set(names):raise ValueError('Exact Netgen helper definitions missing')
  exec(compile(ast.Module(body=selected,type_ignores=[]),CUBE,'exec'),helper.__dict__)
  expected=expected_live(helper,worker,arrays)
  gmsh.initialize([],readConfigFiles=False,run=False);initialized=True
  gmsh.option.setNumber('General.Terminal',1);gmsh.logger.start()
  for key,value in OPTIONS.items():gmsh.option.setNumber(key,value)
  if 'Netgen' not in gmsh.option.getString('General.BuildOptions').split():raise ValueError('Compiled Netgen token absent')
  gmsh.open(str(ROOT/INPUT));report['stage']='full_before_audit';live['before']=cavity.inspect_cavity(gmsh,helper)
  require_before(helper,live['before'],expected);before=cavity.boundary_snapshot(gmsh,helper)
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError('Fixed options changed before geometry/optimizer operations')
  report.update(single_saved_before_state_exact=True,shell=shell,original_source_classifications=data['original_source_classifications'],
   local_to_global_shell_node_tags=data['local_to_global_node_tags'],all_shell_nodes_fixed_only_for_this_cavity_operation=True)
  report['stage']='volume_only_geometry_flag'
  inspect=lambda:cavity.inspect_cavity(gmsh,helper)
  live['after_geometry_flag']=helper.geometry_flag_only(gmsh,live['before'],inspect,report['native_operation_counts'])
  require_before(helper,live['after_geometry_flag'],live['before'])
  report['geometry_flag_full_state_unchanged']=True
  report['stage']='calling_Netgen';helper.optimize_once(gmsh,report['native_operation_counts'])
  report['Netgen_returned_and_cache_refresh_completed']=True
  report['stage']='complete_after_audit';live['after']=cavity.inspect_cavity(gmsh,helper)
  cavity.require_boundary_same(before,cavity.boundary_snapshot(gmsh,helper))
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError('Fixed Netgen options changed')
  path=OUT/'cavity.msh';report['stage']='saving';report['native_operation_counts']['write_mesh']+=1
  gmsh.write(str(path));digest=sha(path)
  gmsh.clear();gmsh.open(str(path));report['stage']='complete_saved_reopen_audit'
  live['saved_reopen']=cavity.inspect_cavity(gmsh,helper)
  helper.require_same(live['after'],live['saved_reopen'],'saved reopen')
  if live['after'][0]!=live['saved_reopen'][0]:raise ValueError('Complete after/saved reports differ')
  cavity.require_boundary_same(before,cavity.boundary_snapshot(gmsh,helper))
  if sha(path)!=digest:raise ValueError('Saved mesh changed during reopen')
  report.update(mesh_sha256=digest,mesh_bytes=path.stat().st_size,saved_mesh_identity_exact=True,
   exact_boundary_bits_faces_classifications=True,fixture_procedural_checks_passed=True,
   actual_SICN_gate_passed=helper.quality_gate(live['after'][0]),stage='completed_all_local_checks',status='completed_finite_selected_cavity_Netgen_only')
  storage=cavity.candidate_storage_admission(live['after'][0],case)
  report.update(case_key=case['case_key'],case_apex=case['apex'],case_record_sha256=case['source_record_sha256'],case_manifest_sha256=MANIFEST_SHA,source_batch_sha256=BATCH_SHA,later_head_storage_compatible=storage,next_stage='domain' if report['actual_SICN_gate_passed'] and storage else 'hold_case')
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
