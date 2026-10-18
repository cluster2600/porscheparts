"""HELD one distinct default optimizer on the unchanged apex1485102 saved cavity; no generation, geometry creation, Netgen or head apply."""
from pathlib import Path
from fractions import Fraction
import hashlib,importlib.util,json,struct,sys,time

ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
CAVITY='work/962-engineering/head-star-current204-local-stages-prep-001/generate_case.py'
CAVITY_SHA='fc1aba0a0ae93995f8fc4eea86d3fe693ce0360ac3f98d158ba5f01ae8983e3d'
CUBE='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/reader.py'
CUBE_SHA='97b7e9fc7d17defa84594c50dac1d4e09cd39bb47ef2059e00b6ac07fe8c029b'
MANIFEST='work/962-engineering/head-star-current204-local-stages-prep-001/case-manifest.json'
MANIFEST_SHA='3a558ede04cbc52c59e401befb36b8983ebd9b7f57d4266de0bea38fb1a963c5'
BATCH='work/962-engineering/head-star-current204-batch-shells-001/report.json'
BATCH_SHA='4f9fc0354918a907083006484d534c34c3b2621dfcc83b00cc4a4b731f009e86'
OUTPUT='work/962-engineering/apex1485102-default-optimizer-001'
DEFAULT='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-default-postexport-prep-001/mesh_delaunay_postexport.py'
DEFAULT_SHA='ebb1f1ba8e7c0b032a4eb0178bbf8c332c68070816e6626f4a3f4788ed638527'
BASELINE={'mesh': {'path': 'work/962-engineering/head-star-current204-apex-1485102-netgen-001/cavity.msh', 'sha256': 'e7e75ce60dc81be1033442bf4b723a252538d4a6116e80ca578e53b8b04e2c95', 'bytes': 5638}, 'worker': {'path': 'work/962-engineering/head-star-current204-apex-1485102-netgen-001/fixture-report.json', 'sha256': '42a8a3127a46a44aff7e0f44ae18b7653a335013a5d71c2911ef901e2b734333', 'bytes': 25499}, 'arrays': {'path': 'work/962-engineering/head-star-current204-apex-1485102-netgen-001/arrays.json', 'sha256': 'db0975cc75c3f6402b4b369f079966adf007428e7a64774b9bf8f60575a19a56', 'bytes': 58301}, 'receipt': {'path': 'work/962-engineering/head-star-current204-apex-1485102-netgen-001/execution-receipt.json', 'sha256': '48f40dc452b165cd2305a6eca52bc5a96b746134ad5f138e704abcc4c835746b', 'bytes': 1432}, 'actual': {'path': 'work/962-engineering/head-star-current204-apex-1485102-netgen-001/frozen-contract.json', 'sha256': 'aaebaa96359ebeeee10c506b92f7e3a796d3f72b2c844769db96c5b4480d2d38', 'bytes': 18664}, 'root_closed': {'path': 'work/962-engineering/head-star-current204-Netgen-root-execution-001/apex-1485102/closed-result.json', 'sha256': '9504281904b21fc20381ca6a0093775d7ab9fe101666019f361085a640c1d4a4', 'bytes': 2236}, 'result_peer': {'path': 'work/962-engineering/head-star-current204-Netgen-result-peer-001/review.json', 'sha256': '5ff930c217e28203526fbda3489c316ce6b4c307319538eba33e09bc88ebc1c3', 'bytes': 8732}, 'root_acceptance': {'path': 'work/962-engineering/head-star-current204-Netgen-root-execution-001/result-peer-acceptance.json', 'sha256': 'fc98600dfdf68e89ec78f442d4c8b32476ea829fe3697c0b2a1dfc95ce8d98ef', 'bytes': 1921}}
BASELINE_INTERIOR_TAGS=[39, 40, 41]
CURRENT_CENSUS='work/962-engineering/head-star-current126-full-stars-001/readback-report.json'
CURRENT_CONTRACT='work/962-engineering/head-star-current126-full-stars-001/frozen-contract.json'
CURRENT_ACCEPT='work/962-engineering/head-star-current126-full-stars-root-execution-001/result-peer-acceptance.json'
PARTIAL='work/962-engineering/apex1613031-head-application-001/readback-report.json'
PARTIAL_ACCEPT='work/962-engineering/apex1613031-head-application-root-execution-001/result-peer-acceptance.json'
ROOT_SAVED_REVIEW='work/962-engineering/head-star-current204-Netgen-root-execution-001/result-review.json'
INPUT=INPUT_SHA=WORKER=WORKER_SHA=ARRAYS=ARRAYS_SHA=None
AUDIT_INPUTS={'twins/962-cylinder-head-f0/source/mesh_head.py':'69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5','work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py':'a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4',MANIFEST:MANIFEST_SHA,BATCH:BATCH_SHA}
BATCH_EVIDENCE={'work/962-engineering/head-star-current204-batch-shells-001/receipt.json': '78e215c5c85f01ca614e44e4e443fd4181086f63e2edc5d5aee81fbef77dbedb', 'work/962-engineering/head-star-current204-batch-shells-root-execution-001/closed-result.json': '67d9b2763fcd5ac887eddca79010d8a21dc6365b19f56224512acbaf7a3150e2', 'work/962-engineering/head-star-current204-batch-shells-root-execution-001/result-review.json': '5a80128a5e4dd3ea685449c1124fd1fad4c07a3bb1c586f9f80a2e26caacf913', 'work/962-engineering/head-star-current204-batch-shells-result-peer-001/review.json': '3fd325b3e4e18b942bda26d9292127d1dc1c2b8ecc5841d11257dc61884030da', 'work/962-engineering/head-star-current204-batch-shells-root-execution-001/result-peer-acceptance.json': '47a98aad883748178b7b25a1a5957ca01c0780eb0274f778567e6c5fb22fe538'}
GENERATION_RUNNER='work/962-engineering/head-star-current204-local-stages-prep-001/run_generation.py'
GENERATION_RUNNER_SHA='05b4f8996f1f642120b70be755e6609f7b641041cad1a867ea8da9e56ecb423b'
AUDIT_INPUTS.update(BATCH_EVIDENCE)
AUDIT_INPUTS[GENERATION_RUNNER]=GENERATION_RUNNER_SHA
AUDIT_INPUTS.update({'work/962-engineering/head-star-current204-local-stages-prep-001/netgen_case.py': '38af98145aa8c4aa1798b5e5901a9837b962e8841d5b5d504674d6cefa922924', 'work/962-engineering/head-star-current204-local-stages-prep-001/run_netgen.py': '1e6ffec8141da0682b94f00eb4f8c49e31b493f32fd10ea35be04a9829e1ca06', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-default-postexport-prep-001/mesh_delaunay_postexport.py': 'ebb1f1ba8e7c0b032a4eb0178bbf8c332c68070816e6626f4a3f4788ed638527', 'twins/962-cylinder-head-f0/source/check_saved_cube_default.py': 'c8a87cc7bc312fae4bdb414c2a6c6e77b920382f5bd00ca7ae2d04e4d3de20a6', 'work/962-engineering/head-star-current204-Netgen-root-execution-001/result-review.json': '5d8943639eea7b7e246e51714c09a2ab39e43c0cb19a5374218e65d7095dd9fc', 'work/962-engineering/head-star-current204-generation-root-execution-002/apex-1485102/closed-result.json': '4d6a18fc675769119e12601851d61c3e9babf420f9131c11cf01daa2e0d96ca6', 'work/962-engineering/head-star-current204-apex-1485102-generation-001/fixture-report.json': 'dca3d4cabd29d1325ab239e3ec981eb762fcddf355ceb5c2dd15f8f478828175', 'work/962-engineering/head-star-current204-apex-1485102-generation-001/execution-receipt.json': '2ceab59460c35b766f71c39ac00c04d9126fcebd22a749cef0bd0974a17838b1', 'work/962-engineering/head-star-current126-full-stars-001/readback-report.json': 'ac40521a4add15f1bb414d7d1a1c2cd231a0107278b6fe43ec38dad27c269e1a', 'work/962-engineering/head-star-current126-full-stars-001/frozen-contract.json': 'd579a794f18bc9f7c4e153cb2042f32cb32b2c6b2f2235cec2edbef8aba91317', 'work/962-engineering/head-star-current126-full-stars-root-execution-001/result-peer-acceptance.json': 'f66d5857a0fa75352c3880ab2cd7bbc0bcae73833254f39423fd48971ebd52d9', 'work/962-engineering/head-star-current126-full-stars-root-execution-001/closed-result.json': '4ec76692bd1fb7bb592bf24c82b199830eb6a4828cf9726fc879fa387022fb99', 'work/962-engineering/apex1613031-head-application-001/readback-report.json': '64caf59811e229628ea1be138ebcc48cdf940c4ca2724be0b9080e255951c9f5', 'work/962-engineering/apex1613031-head-application-root-execution-001/result-peer-acceptance.json': '19ef174a208868bf174909a1add690971fdf018b8cf438c5c26e3a2bca9bfada', 'work/962-engineering/head-star-current126-full-stars-prep-001/reader.py': '2348c032ecbbb694563978cb333aff1a7e4d37a5052c3ed841a7128bf797409c', 'work/962-engineering/head-star-current126-full-stars-runtime-root-001/review.json': '28101a316a5070a9d33092f5afc08dd84a347f6b8e2b51bed88a4c00ab951e7c'})
OPTIONS={'General.NumThreads':2,'Mesh.MaxNumThreads3D':2,'Mesh.Renumber':0,
 'Mesh.Optimize':0,'Mesh.OptimizeNetgen':0,'Mesh.OptimizeThreshold':.3,
 'Mesh.Binary':1,'Mesh.SaveAll':1,'Mesh.MshFileVersion':4.1}
COUNTS={'generate':0,'createGeometry_dim3':0,'optimize_default':1,
 'rebuildElementCache':1,'write_mesh':1,'solve':0}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def require_authority(c):
 if (c.get('native_execution_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or c.get('selected_runtime_review_complete') is not True or c.get('cavity_default_optimizer_authorized') is not True
     or any(c.get(k) is not False for k in ['generation_authorized','head_execution_authorized','stitching_authorized',
      'native_head_application_authorized','head_edit_authorized','domain_execution_authorized','outside_owner_query_authorized','cavity_Netgen_optimizer_authorized','geometry_creation_authorized','PDE_solve_authorized','head_PDE_authorized','material_qualified','process_calibrated','engineering_accepted','physics_qualified','manufacturing_authorized'])):
  raise ValueError('Reviewed specific saved-cavity optimizer-only authority required')
 if (not isinstance(c.get('output_directory'),str) or OUT.parent!=ROOT/'work/962-engineering'
     or c['output_directory']!=OUTPUT or (ROOT/c['output_directory']).resolve()!=OUT):raise ValueError('Exact fresh actual output binding required')
 if (c.get('options')!=OPTIONS or c.get('declared_operation_counts')!=COUNTS or c.get('automatic_retry') is not False
     or c.get('optimization')!={'method':'','force':True} or c.get('geometry_creation_dim_tags')!=[]):
  raise ValueError('Fixed saved input, options and one default/cache/write policy required')
 if (c.get('declared_controller_command_conformant') is not False
     or c.get('upstream_census_launch_deviation_sha256')!='d60fff297c6c45dc92e117262e36ffde36e2169d53fcd32ce2b79fabde5eebc3'):
  raise ValueError('Historical d60 command deviation must remain explicit')

def require_contract(c):
 require_authority(c)
 configure_baseline(c)
 for name,digest in [(CAVITY,CAVITY_SHA),(CUBE,CUBE_SHA),(DEFAULT,DEFAULT_SHA),(INPUT,INPUT_SHA),(WORKER,WORKER_SHA),(ARRAYS,ARRAYS_SHA)]:
  if c['input_hashes'].get(name)!=digest:raise ValueError('Exact input/helper must be a direct pin')
 for name,digest in AUDIT_INPUTS.items():
  if c['input_hashes'].get(name)!=digest:raise ValueError('Every consumed audit source and shell input must be a direct pin')
 for name,digest in c['input_hashes'].items():
  if Path(name).is_absolute() or (ROOT/name).is_symlink() or not (ROOT/name).resolve().is_relative_to(ROOT):raise ValueError('Project-relative input pin required')
  if sha(ROOT/name)!=digest:raise ValueError('Input drift: '+name)
 if len(c['external_runtime_hashes'])!=3:raise ValueError('Selected three native runtime identities required')
 for name,digest in c['external_runtime_hashes'].items():
  if sha(Path(name))!=digest:raise ValueError('Runtime drift')
 if (sha(OUT/'reader.py')!=c['reader_sha256'] or sha(OUT/'run_readback.py')!=c['runner_sha256']
     or sha(Path(sys.executable).resolve())!=c['runtime']['python_executable_sha256']):
  raise ValueError('Materialized source or selected Python changed')

def configure_baseline(c):
 global INPUT,INPUT_SHA,WORKER,WORKER_SHA,ARRAYS,ARRAYS_SHA
 b=c['saved_Netgen_baseline']
 if type(c.get('case_apex')) is not int or c['case_apex']!=1485102 or b!=BASELINE:
  raise ValueError('Only exact naturalRC2 frozen apex1485102 Netgen capture and stopped proof history required')
 for row in b.values():
  if not isinstance(row,dict) or c['input_hashes'].get(row['path'])!=row['sha256']:
   raise ValueError('All original stopped Netgen/proof records must be direct pins')
 INPUT,INPUT_SHA=b['mesh']['path'],b['mesh']['sha256'];WORKER,WORKER_SHA=b['worker']['path'],b['worker']['sha256'];ARRAYS,ARRAYS_SHA=b['arrays']['path'],b['arrays']['sha256']
def load_cavity_module():
 spec=importlib.util.spec_from_file_location('frozen_specific_cavity_audit',ROOT/CAVITY)
 cavity=importlib.util.module_from_spec(spec);spec.loader.exec_module(cavity)
 return cavity

def require_saved_baseline(worker,c,case,shell):
 r=worker.get('saved_reopen',{});q=r.get('quality',{}).get('SICN',{});b=c['saved_Netgen_baseline']
 if (worker.get('status')!='completed_finite_selected_cavity_Netgen_only' or worker.get('fixture_procedural_checks_passed') is not True
     or worker.get('actual_SICN_gate_passed') is not False or worker.get('next_stage')!='hold_case'
     or worker.get('saved_mesh_identity_exact') is not True or worker.get('bound_inputs_unchanged') is not True
     or worker.get('case_apex')!=1485102 or worker.get('case_key')!=case['case_key']
     or worker.get('case_record_sha256')!=case['source_record_sha256'] or worker.get('case_manifest_sha256')!=MANIFEST_SHA
     or worker.get('source_batch_sha256')!=BATCH_SHA or worker.get('mesh_sha256')!=INPUT_SHA
     or worker.get('original_source_classifications')!=shell['original_source_classifications']
     or worker.get('local_to_global_shell_node_tags')!=shell['local_to_global_node_tags']
     or worker.get('mesh_bytes')!=b['mesh']['bytes'] or worker.get('full_tiny_arrays_sha256')!=ARRAYS_SHA
     or worker.get('after')!=r or (r.get('nodes'),r.get('tetrahedra'),r.get('referenced_interior_nodes'),r.get('unreferenced_nodes'))!=(31,64,3,0)
     or sorted(t for t,dim in r.get('node_classifications',[]) if dim==3)!=BASELINE_INTERIOR_TAGS
     or (q.get('count'),q.get('nonpositive_count'),q.get('below_point1_count'),q.get('minimum'))!=(64,0,1,0.07209708351715523)):
  raise ValueError('Exact unchanged31node64TET3interior positive but strict-quality-rejected Netgen baseline required')
 receipt=json.loads((ROOT/b['receipt']['path']).read_text());closed=json.loads((ROOT/b['root_closed']['path']).read_text())
 peer=json.loads((ROOT/b['result_peer']['path']).read_text());accepted=json.loads((ROOT/b['root_acceptance']['path']).read_text())
 review=json.loads((ROOT/ROOT_SAVED_REVIEW).read_text());rows=[x for x in review['cases'] if x['case_apex']==1485102]
 for role,name in [('mesh','cavity.msh'),('worker','fixture-report.json'),('arrays','arrays.json'),('receipt','execution-receipt.json'),('actual','frozen-contract.json')]:
  if closed['output_files'][name]!={k:b[role][k] for k in ['sha256','bytes']}:
   raise ValueError('Every exact stopped output descriptor must match the original root inventory')
 if (receipt.get('returncode')!=2 or receipt.get('stop_reason') is not None
     or receipt.get('fixture_report_sha256')!=WORKER_SHA or receipt.get('contract_sha256')!=b['actual']['sha256']
     or receipt.get('reader_sha256')!=AUDIT_INPUTS['work/962-engineering/head-star-current204-local-stages-prep-001/netgen_case.py']
     or receipt.get('runner_sha256')!='1e6ffec8141da0682b94f00eb4f8c49e31b493f32fd10ea35be04a9829e1ca06'
     or closed.get('case_apex')!=1485102 or closed.get('returncode')!=2 or closed.get('root_stop_reason') is not None or closed.get('root_error') is not None
     or any(closed.get(k) is not True for k in ['controller_wait_reaped','observed_controller_absent','all60_inputs_native3_NumPy_actual_before_after_unchanged'])
     or closed.get('controller_fallback_SIGKILL') is not False
     or peer.get('decision')!='CLEAR_COMPLETED_LOCAL_SAVED_EVIDENCE_47_PROVISIONAL_DOMAIN_ROUTES_68_REJECTS'
     or accepted.get('schema')!='962-root-stopped115-Netgen-peer-acceptance/v1' or accepted['peer_sha256']!=b['result_peer']['sha256']
     or accepted.get('quality_rejections_preserved')!=68 or 1485102 in accepted['local_quality_storage_pass_apices']
     or len(rows)!=1 or rows[0]['closed_sha256']!=b['root_closed']['sha256'] or rows[0]['worker_sha256']!=WORKER_SHA
     or rows[0]['arrays_sha256']!=ARRAYS_SHA or rows[0]['mesh_sha256']!=INPUT_SHA or rows[0]['next_stage']!='hold_case'):
  raise ValueError('Completed naturalRC2 baseline is held history; this distinct backend needs fresh authority')


def configure_case(c,cavity):
 if (c.get('case_apex')!=1485102 or c.get('case_manifest')!=MANIFEST or c.get('case_manifest_sha256')!=MANIFEST_SHA
     or c['input_hashes'].get(MANIFEST)!=MANIFEST_SHA or c['input_hashes'].get(BATCH)!=BATCH_SHA):
  raise ValueError('Only the exact historical1485102 source record may be rebound to current126')
 case,record=cavity.select_case(json.loads((ROOT/MANIFEST).read_text()),json.loads((ROOT/BATCH).read_text()),1485102)
 if (c.get('case_key')!=case['case_key'] or c.get('case_record_sha256')!=case['source_record_sha256']
     or c.get('output_directory')!=OUTPUT or (case['old_tetrahedra'],case['shell_nodes'],case['shell_faces'],case['original_boundary_shell_nodes'],case['other_interior_shell_nodes'])!=(52,28,52,18,10)):
  raise ValueError('Specific52cell28shell52face18boundary10dim3 metadata required; no inherited output authority')
 cavity.NV,cavity.NF,cavity.NB,cavity.APEX=28,52,18,1485102
 value=case['exact_volume_mm3'];cavity.VOLUME=Fraction(value['numerator'],value['denominator']);cavity.SHELL_SHA=case['shell_serialized_sha256']
 return case,record


def require_current_star(c,case,record):
 current=json.loads((ROOT/CURRENT_CENSUS).read_text());accepted=json.loads((ROOT/CURRENT_ACCEPT).read_text())
 contract=json.loads((ROOT/CURRENT_CONTRACT).read_text());partial=json.loads((ROOT/PARTIAL).read_text());partial_accepted=json.loads((ROOT/PARTIAL_ACCEPT).read_text())
 if (accepted.get('decision')!='ACCEPT_COMPLETE_CURRENT126_READ_ONLY_CENSUS_ASSOCIATIONS_ONLY'
     or accepted['current_report']['path']!=CURRENT_CENSUS or accepted['current_report']['sha256']!=AUDIT_INPUTS[CURRENT_CENSUS]
     or accepted['current_contract']['sha256']!=AUDIT_INPUTS[CURRENT_CONTRACT] or accepted.get('whole_head_quality_accepted') is not False
     or accepted.get('prior_d60_command_conformant') is not False
     or contract['MSH_sha256']!='48b66aafbd9f1eb69e44305982186e966fe8f041d9b4a6a59be4b610b5d12e08' or contract['expected_positive_poor_total']!=126
     or contract['partial_report_sha256']!=AUDIT_INPUTS[PARTIAL]
     or current['single_partial_replacement_saved_proof']['report_sha256']!=AUDIT_INPUTS[PARTIAL]
     or current['declared_controller_command_conformant'] is not False or partial['declared_controller_command_conformant'] is not False
     or partial['mesh_sha256']!=contract['MSH_sha256'] or partial['after']!=partial['saved_reopen']
     or partial_accepted.get('decision')!='ACCEPT_COMPLETED_PROCEDURAL_PARTIAL_HEAD_REPAIR_ONLY_WHOLE_HEAD_REJECTED'
     or partial_accepted['partial_report']['sha256']!=AUDIT_INPUTS[PARTIAL] or partial_accepted.get('whole_head_quality_accepted') is not False):
  raise ValueError('Exact accepted current126 census and quality-rejected partial parent required; no head or context proof transferred')
 census=current['complete_seed_star_census'];old=record['observation'];fresh=[r for r in census['complete_incident_tetrahedra'] if 1485102 in r['node_tags']]
 semantic=lambda row:{k:v for k,v in row.items() if k!='native_array_index'}
 compact=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
 if (len(fresh)!=52 or [semantic(r) for r in fresh]!=[semantic(r) for r in old['native_ordered_cell_rows']]
     or [r['tetrahedron_tag'] for r in fresh]!=case['old_tetrahedron_tags'] or len(old['selected_node_rows'])!=29):
  raise ValueError('All52 current ordered corner/quality/member rows must equal the original star; native indices are separate')
 nodes={r['node_tag']:r for r in census['unique_incident_nodes']};selected=[]
 for row in old['selected_node_rows']:
  other=nodes.get(row['node_tag']);fields={k:v for k,v in row.items() if k!='binary64_little_endian_bytes_hex'}
  if (other is None or fields!=other or struct.pack('<3d',*row['coordinates_mm'])!=struct.pack('<3d',*other['coordinates_mm'])
      or row['binary64_little_endian_bytes_hex']!=struct.pack('<3d',*other['coordinates_mm']).hex()):
   raise ValueError('Every original node coordinate word/classification/membership must still match the current parent')
  selected.append(other)
 binding=c['current_star_binding'];translation=[dict(tetrahedron_tag=a['tetrahedron_tag'],historical_native_array_index=a['native_array_index'],current_native_array_index=b['native_array_index']) for a,b in zip(old['native_ordered_cell_rows'],fresh)]
 if (binding['apex']!=1485102 or binding['old_complete_cell_count']!=52 or binding['old_complete_node_count']!=29
     or binding['original_source_record_sha256']!=case['source_record_sha256'] or binding['current_census_sha256']!=AUDIT_INPUTS[CURRENT_CENSUS]
     or binding['current_parent_MSH_sha256']!=contract['MSH_sha256'] or binding['semantic_rows_sha256']!=compact([semantic(r) for r in fresh])
     or binding['node_rows_sha256']!=compact(selected) or binding['native_index_translation']!=translation
     or binding['native_index_changes']!=sum(a['native_array_index']!=b['native_array_index'] for a,b in zip(old['native_ordered_cell_rows'],fresh))):
  raise ValueError('Explicit current native-index translation and exact saved semantic identities required; old indices are never current aliases')
 return binding

def optimize_and_refresh(gmsh,report,checkpoint):
    report.update(stage="calling_default_postexport_optimizer",optimizer_call_count=1)
    checkpoint()
    gmsh.model.mesh.optimize(method="",force=True)
    report.update(optimizer_returned=True,stage="refreshing_element_lookup_cache")
    checkpoint()
    # False forces rebuilding even if the pre-optimization cache is populated.
    # Gmsh4.15.2 GModel.cpp2046-2082: this changes lookup pointers, not the mesh.
    report["element_cache_refresh_count"]=1
    gmsh.model.mesh.rebuildElementCache(False)
    report.update(element_cache_refresh_completed=True,
                  stage="optimizer_returned_and_element_cache_refreshed")
    checkpoint()



def default_once(gmsh,report):
 try:optimize_and_refresh(gmsh,report,lambda:None)
 finally:
  report['native_operation_counts']['optimize_default']=report.get('optimizer_call_count',0)
  report['native_operation_counts']['rebuildElementCache']=report.get('element_cache_refresh_count',0)


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
 report=dict(next_stage='hold_case',later_head_storage_compatible=False,schema='962-apex1485102-default-optimizer-local-result/v1',status='running',stage='imports',
  fixture_procedural_checks_passed=False,actual_SICN_gate_passed=False,actual_SICN_threshold=.1,
  native_operation_counts={k:0 for k in COUNTS},call_counts_are_attempts=True,options=OPTIONS,
  frozen_contract_sha256=sha(OUT/'frozen-contract.json'),input_mesh_sha256=INPUT_SHA,input_worker_sha256=WORKER_SHA,input_arrays_sha256=ARRAYS_SHA,
  full_head_geometry_read=False,generation_authorized=False,head_execution_authorized=False,stitching_authorized=False,
  native_head_application_authorized=False,engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False,
  global_self_intersection_checked=False,geometric_tetrahedron_overlap_checked=False,new_interior_node_point_in_cavity_containment_checked=False,
  dynamic_interior_count_and_retagging_allowed=True,interior_ancestry_inferred=False,
  geometry_creation_authorized=False,cavity_Netgen_optimizer_authorized=False,PDE_solve_authorized=False,head_PDE_authorized=False,
  material_qualified=False,process_calibrated=False,declared_controller_command_conformant=False,
  upstream_census_launch_deviation_sha256=c['upstream_census_launch_deviation_sha256'],
  method='default_Gmsh_optimizer',Gamma_objective_is_not_SICN=True,local_domain_or_parent_context_proved=False)
 try:
  cavity=load_cavity_module();case,record=configure_case(c,cavity);data=record['shell']
  report['current_original_star_binding']=require_current_star(c,case,record)
  worker=json.loads((ROOT/WORKER).read_text());require_saved_baseline(worker,c,case,data)
  arrays=json.loads((ROOT/ARRAYS).read_text())
  helper,gmsh,observed,actual=cavity.load_audit_helper(c);report.update(runtime=observed,runtime_sha256s=actual)
  if c['expected_runtime']!=cavity.RUNTIME:raise ValueError('Fixed expected runtime changed')
  points,faces,shell=cavity.shell_rows(data)
  helper.P=helper.np.asarray(points,dtype='<f8');helper.F=helper.np.asarray(faces,dtype=helper.np.int64)
  expected=expected_live(helper,worker,arrays)
  gmsh.initialize([],readConfigFiles=False,run=False);initialized=True
  gmsh.option.setNumber('General.Terminal',1);gmsh.logger.start()
  for key,value in OPTIONS.items():gmsh.option.setNumber(key,value)
  gmsh.open(str(ROOT/INPUT));report['stage']='full_before_audit';live['before']=cavity.inspect_cavity(gmsh,helper)
  require_before(helper,live['before'],expected);before=cavity.boundary_snapshot(gmsh,helper)
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError('Fixed options changed before the default optimizer')
  report.update(single_saved_before_state_exact=True,shell=shell,original_source_classifications=data['original_source_classifications'],
   local_to_global_shell_node_tags=data['local_to_global_node_tags'],all_shell_nodes_fixed_only_for_this_cavity_operation=True)
  report['stage']='calling_default_optimizer';default_once(gmsh,report)
  report['default_returned_and_cache_refresh_completed']=True
  report['stage']='complete_after_audit';live['after']=cavity.inspect_cavity(gmsh,helper)
  cavity.require_boundary_same(before,cavity.boundary_snapshot(gmsh,helper))
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError('Fixed default options changed')
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
   actual_SICN_gate_passed=helper.quality_gate(live['after'][0]),stage='completed_all_local_checks',status='completed_saved_apex1485102_default_optimizer_only')
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
