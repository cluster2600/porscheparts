"""HELD current127 single14-to14 partial application; no mesher or optimizer."""
from pathlib import Path
from fractions import Fraction
from types import SimpleNamespace
from itertools import combinations
import ast,hashlib,json,math,platform,struct,sys,time
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
OUTPUT='work/962-engineering/apex1613031-head-application-001'
MESH='work/962-engineering/apex1613790-head-application-001/head-volume.msh'
CONTEXT='work/962-engineering/current127-apex1613031-head-context-001/readback-report.json'
CONTEXT_CONTRACT='work/962-engineering/current127-apex1613031-head-context-001/frozen-contract.json'
OBSERVATION='work/962-engineering/direct-sicn-apex1613031-cavity-study-001/saved-star-observation.json'
SHELL='work/962-engineering/direct-sicn-apex1613031-cavity-study-001/local-shell-input-001.json'
ARRAYS='work/962-engineering/fixed-shell-netgen-apex1613031-001/arrays.json'
WORKER='work/962-engineering/fixed-shell-netgen-apex1613031-001/fixture-report.json'
LOCAL_PEER='work/962-engineering/fixed-shell-netgen-apex1613031-result-peer-001/review.json'
LOCAL_BINDINGS='work/962-engineering/fixed-shell-netgen-apex1613031-result-peer-001/bindings.json'
DOMAIN='work/962-engineering/apex1613031-domain-equivalence-001/report.json'
DOMAIN_PEER='work/962-engineering/apex1613031-domain-equivalence-result-peer-001/review.json'
DOMAIN_BINDINGS='work/962-engineering/apex1613031-domain-equivalence-result-peer-001/bindings.json'
DOMAIN_SOURCE='work/962-engineering/apex1613031-domain-equivalence-prep-001/certify_domain.py'
DOMAIN_ACTUAL='work/962-engineering/apex1613031-domain-equivalence-execution-prep-001/actual-contract.json'
ORIGINAL_WORKER='work/962-engineering/apex1613790-head-application-001/readback-report.json'
ORIGINAL_RECEIPT='work/962-engineering/apex1613790-head-application-001/execution-receipt.json'
PARTIAL_CLOSED='work/962-engineering/apex1613790-head-application-root-execution-001/closed-result.json'
PARTIAL_METADATA='work/962-engineering/head-star-current127-full-stars-002/frozen-contract.json'
FIRST='work/962-engineering/head-star-current127-full-stars-002/readback-report.json'
PROOF_SOURCE='work/962-engineering/head-star-current127-full-stars-prep-001/reader.py'
CONTEXT_PEER='work/962-engineering/current127-apex1613031-head-context-result-peer-001/review.json'
CONTEXT_BINDINGS='work/962-engineering/current127-apex1613031-head-context-result-peer-001/bindings.json'
CONTEXT_ACCEPT='work/962-engineering/current127-apex1613031-head-context-root-execution-001/result-peer-acceptance.json'
CONTEXT_CLOSED='work/962-engineering/current127-apex1613031-head-context-root-execution-001/closed-result.json'
DOMAIN_ACCEPT='work/962-engineering/apex1613031-domain-equivalence-root-execution-001/result-peer-acceptance.json'
LOCAL_ACCEPT='work/962-engineering/fixed-shell-netgen-apex1613031-root-execution-001/result-peer-acceptance.json'
DEVIATION='work/962-engineering/head-star-current129-full-stars-root-execution-001/launch-deviation-001.json'
HEAD='twins/962-cylinder-head-f0/source/mesh_head.py'
CORE='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py'
AUDIT='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-netgen-postexport-prep-002/mesh_delaunay_netgen_postexport.py'
FIXED_INPUTS={'twins/962-cylinder-head-f0/source/mesh_head.py': '69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5', 'work/962-engineering/apex1474426-head-application-prep-001/reader.py': '15443fe1c0adebb02a4abe8a4db1c8dbb2f5148ad37f992ae8e74df8cd28d7d1', 'work/962-engineering/apex1613031-domain-equivalence-001/report.json': '6e12be8b4be563c49ebf0dd06ecf9d69b8fcb338d8cd777303899de509e610d9', 'work/962-engineering/apex1613031-domain-equivalence-execution-prep-001/actual-contract.json': '9886958b431db631b2ad1d9591dabea299119210802d2abe64cf9e501f2ee61d', 'work/962-engineering/apex1613031-domain-equivalence-prep-001/certify_domain.py': '3cb92684b1d757617854d5ea1b0896e04db632648251810fc784289110330118', 'work/962-engineering/apex1613031-domain-equivalence-result-peer-001/bindings.json': '7c86ae0026c221ed92af3729e85d0a40fc8c069f845c4ce5de9f23e224d29893', 'work/962-engineering/apex1613031-domain-equivalence-result-peer-001/review.json': '431e33c21d3364d43b9036177575cf95f6551aba99f673c069f6ef11c7632079', 'work/962-engineering/apex1613031-domain-equivalence-root-execution-001/result-peer-acceptance.json': '53df7322ea94a9388d896978be4f50abeb3bb5bf65ae8338ad530836982afa13', 'work/962-engineering/apex1613790-head-application-001/execution-receipt.json': '28bb0647a28de19e2413c0066468946ac5eee77e4b2e24a8b5f570ca184150fa', 'work/962-engineering/apex1613790-head-application-001/frozen-contract.json': 'd016fb42f6363995739193521db416741ff8609ef0ca12c22b3dc7e8fdfce272', 'work/962-engineering/apex1613790-head-application-001/head-volume.msh': '8b16732d63cc69e48af113f6b618cc6378aaf121dbe1c63920dd6dd5eab8d07a', 'work/962-engineering/apex1613790-head-application-001/readback-report.json': 'bb1266ede7b8fd41f282a04c2363ba0eb684a94b6272956895bb7a30a09ffad0', 'work/962-engineering/apex1613790-head-application-prep-001/held-contract.json': '0b15a69b86520b8e1a284f6b927ae39afcbf2a9b282740f861dba0d1b1cd53b6', 'work/962-engineering/apex1613790-head-application-prep-001/reader.py': '0e3db83e33b1dec8b49e42401b313735c7c5fecfcd17cee5268f5ccc7a797a90', 'work/962-engineering/apex1613790-head-application-prep-001/run_readback.py': '5ab38b53e4019506772cc429b46699ac0e217141c87a0a043718d8123ecb159c', 'work/962-engineering/apex1613790-head-application-prep-001/selfcheck.py': '46ef833a30cc15876a59e12a487740bb503e253204776ac7c2876f1971495eae', 'work/962-engineering/apex1613790-head-application-root-execution-001/closed-result.json': 'e6951a0c920f88dda87efce797c111b1da83bb81f33cc2cd2c8acb900867504f', 'work/962-engineering/apex1613790-head-application-root-execution-001/result-peer-acceptance.json': 'e4bdec1ed7926231190f21a0b9986f47363bbbcf41daec2948e884459fef051c', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-netgen-postexport-prep-002/mesh_delaunay_netgen_postexport.py': '0d1dd1f0625275343f16b713dae2d41143dda8da974bef42e59f6bfa3b0e388a', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py': 'a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4', 'work/962-engineering/current127-apex1613031-head-context-001/frozen-contract.json': '37db8019cbfe3db7e14e932ea337ff82fea599aec1f136ddf443b9659055b115', 'work/962-engineering/current127-apex1613031-head-context-001/readback-report.json': '2a420ddbf8b88d648a30359ee2ecbe1441f2a7f3a8305b1d488b55ffb6dc9902', 'work/962-engineering/current127-apex1613031-head-context-prep-001/reader.py': '7b38ef1fd0928544126e3b4f9720049037ad47e82a48162863b3a103057c81dd', 'work/962-engineering/current127-apex1613031-head-context-result-peer-001/ROOT-OWN-REVIEW-LINEAGE-COMPANION-001.json': '45312e2ac9cfe1a7eb258a2ee9d92f1c517264004bc91905265c705a25b99130', 'work/962-engineering/current127-apex1613031-head-context-result-peer-001/bindings.json': 'a1787e73ecbf7f80dfbb29d2881b7653410d87e0e98089ee4dcd6a95d5e9f536', 'work/962-engineering/current127-apex1613031-head-context-result-peer-001/review.json': '9fd13ef8e7fb55c6d2756ca40e2b202bea6be5ac179173ccdf173e83f3ccff01', 'work/962-engineering/current127-apex1613031-head-context-root-execution-001/closed-result.json': '5083013cb604515bcde15f3328f72e20ef46b30e06f0fd5fa9cc5c17d86d87e8', 'work/962-engineering/current127-apex1613031-head-context-root-execution-001/own-review-lineage-correction-001.json': '8ff39b1bf07481d22d070935597f452850d23eab484086b1fb6e0dfdb6977e6c', 'work/962-engineering/current127-apex1613031-head-context-root-execution-001/own-review.json': '8671261afe1ec6b5fa68eeaf14c7e40f0bc016a9e464558ed4dd99038ff69135', 'work/962-engineering/current127-apex1613031-head-context-root-execution-001/result-peer-acceptance.json': '49c9181cdba8650211754723ef6729efaa4b3b05b2d7d3a82a3ba7cc78d45859', 'work/962-engineering/current127-apex1613031-head-context-source-peer-001/AUTHOR-LINEAGE-CORRECTION-001.json': 'ea8c38acd2d9ae09821d139ef0958516dc24d40aeea5f45960f0983b6e1d9804', 'work/962-engineering/direct-sicn-apex1613031-cavity-study-001/local-shell-input-001.json': '6529ffc5a5ca738c4bfe3041d858f2d40cc50efc6ee0e1dc5bcc626fd720d92d', 'work/962-engineering/direct-sicn-apex1613031-cavity-study-001/saved-star-observation.json': '89689ac5ce5f12c8922be4cbe45e36565f60eed080633aaffa79539c8e12c8d3', 'work/962-engineering/fixed-shell-netgen-apex1613031-001/arrays.json': '84df4795b0e7499c45b56a0af800e2470a51b5333a881b8150ea735ed2d03954', 'work/962-engineering/fixed-shell-netgen-apex1613031-001/fixture-report.json': 'a7f4aa89c415be333b03301575898c4f2fc7ea56a9664c22422bb81ad2092a8b', 'work/962-engineering/fixed-shell-netgen-apex1613031-result-peer-001/bindings.json': 'dc23febe02576eaa17aab53c697bef3d67e4d774090780e0f313527d2dab1f51', 'work/962-engineering/fixed-shell-netgen-apex1613031-result-peer-001/review.json': 'b92bf933b272e39d5362c1adaf4bac155e98258668456d29abf5d6d4cb0b6fbe', 'work/962-engineering/fixed-shell-netgen-apex1613031-root-execution-001/result-peer-acceptance.json': '42ae8e27bc62f63c280c185c1d036223fbeea05f4452aec39cbfce4653c9813e', 'work/962-engineering/head-star-current127-full-stars-002/frozen-contract.json': '54ad12959a10bb153afec2f2541bec2d22ec3f6e22ee0302c581062265c8fc95', 'work/962-engineering/head-star-current127-full-stars-002/readback-report.json': '34e3e29a23cedeb155485156cb40b4e92b6d0017eefd852f30383927eaaa7ef7', 'work/962-engineering/head-star-current127-full-stars-execution-prep-002/actual-contract.json': '54ad12959a10bb153afec2f2541bec2d22ec3f6e22ee0302c581062265c8fc95', 'work/962-engineering/head-star-current127-full-stars-prep-001/reader.py': '11ad364b54b6b8f264f1727027659351ab38c9144b4c98c64e5265203fcb8a63', 'work/962-engineering/head-star-current127-full-stars-result-peer-001/bindings.json': '968353193fa36fb96ec9dc85b4268ad3d37f011b19acff745c0a250dcf4fc2ac', 'work/962-engineering/head-star-current127-full-stars-result-peer-001/review.json': 'e3f53c5b7280138296e4ffd8399149a61b9ecaf3bf796e4f780c74806a20b68b', 'work/962-engineering/head-star-current127-full-stars-root-execution-001/result-peer-acceptance.json': 'bac2ff58db7e1f33556e8460e23d35cdd0cb7089c64afa6921ac7640b1bf0444', 'work/962-engineering/head-star-current129-full-stars-root-execution-001/launch-deviation-001.json': 'd60fff297c6c45dc92e117262e36ffde36e2169d53fcd32ce2b79fabde5eebc3', 'work/962-engineering/head-star-current204-combined-application-001/reader.py': 'c66da821a1d98794ed78f403067e02c349c11a59d6c22de72e587b05e5fc82f5', 'work/962-engineering/head-star-current204-union-context-prep-002/reader.py': 'c852a8a536a0ef2c58a37132fb51e42e525403d1f519375cc04a9860bfe53b29'}
ARRAYS_SHA=FIXED_INPUTS[ARRAYS];WORKER_SHA=FIXED_INPUTS[WORKER]
APEX=1613031;NMAX=1613977;EMAX=32159077;BOUNDARY=871731
RUNTIME={'python':'3.10.11','numpy':'2.0.2','gmsh':'4.15.2','machine':'arm64'}
OPTIONS={'General.NumThreads':2,'Mesh.MaxNumThreads3D':2,'Mesh.Renumber':0,
 'Mesh.Optimize':0,'Mesh.OptimizeNetgen':0,'Mesh.Binary':1,'Mesh.SaveAll':1,'Mesh.MshFileVersion':4.1}
CONTROLS={'hard_wall_seconds':1200,'sampled_RSS_stop_bytes':8*1024**3,'sampled_output_stop_bytes':1024**3,'native_threads':2,'automatic_retry':False}
COUNTS={'removeElements':1,'setNode':1,'addNodes':0,'addElementsByType':1,'rebuildNodeCache':1,
 'rebuildElementCache':1,'write_mesh':1,'generate':0,'optimize':0,'createGeometry':0,'reclassifyNodes':0,'solve':0}
FORBIDDEN=['generation_authorized','optimization_authorized','reclassification_authorized','renumbering_authorized',
 'surface_TRI_insertion_authorized','stitching_authorized','head_PDE_authorized','engineering_accepted','physics_qualified','manufacturing_authorized']

QUALIFICATION=dict(native_application_authorized=False,head_execution_authorized=False,stitching_authorized=False,
 engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)


def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024**2),b''):h.update(block)
 return h.hexdigest()


def json_sha(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def selected(path,names,namespace):
 tree=ast.parse((ROOT/path).read_text());rows=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 if {n.name for n in rows}!=set(names):raise ValueError('Exact selected frozen helper definitions required')
 exec(compile(ast.Module(body=rows,type_ignores=[]),path,'exec'),namespace)


def require_contract(c):
 if (c.get('schema')!='962-apex1613031-head-application/v1' or c.get('native_execution_authorized') is not True
     or c.get('partial_head_replacement_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or c.get('selected_runtime_review_complete') is not True or c.get('automatic_retry') is not False or c.get('head_execution_authorized') is not False
     or c.get('upstream_census_launch_deviation_sha256')!=FIXED_INPUTS[DEVIATION] or c.get('declared_controller_command_conformant') is not False
     or any(c.get(k) is not False for k in FORBIDDEN) or c.get('options')!=OPTIONS
     or c.get('declared_operation_counts')!=COUNTS or c.get('controls')!=CONTROLS or c.get('output_directory')!=OUTPUT or ROOT/OUTPUT!=OUT):
  raise ValueError('Separate reviewed one-partial-replacement actual authority required')
 if any(c['input_hashes'].get(k)!=v for k,v in FIXED_INPUTS.items()):raise ValueError('Every consumed source/data/peer requires its exact direct pin')
 for name,digest in c['input_hashes'].items():
  path=ROOT/name
  if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or not path.resolve().is_relative_to(ROOT) or sha(path)!=digest:
   raise ValueError('Bound input drift: '+name)
 original=json.loads((ROOT/CONTEXT_CONTRACT).read_text())
 for key in ['external_runtime_hashes','runtime_sha256s','runtime','native_python','numpy_init','numpy_init_sha256','expected_runtime']:
  if c[key]!=original[key]:raise ValueError('Selected original runtime scope changed: '+key)
 if sha(Path(c['numpy_init']))!=c['numpy_init_sha256']:raise ValueError('Selected NumPy init changed')
 if len(c['external_runtime_hashes'])!=3:raise ValueError('Exactly three selected native runtime identities required')
 for name,digest in c['external_runtime_hashes'].items():
  if sha(name)!=digest:raise ValueError('Selected runtime drift')
 if (sha(OUT/'reader.py')!=c['reader_sha256'] or sha(OUT/'run_readback.py')!=c['runner_sha256']
     or sha(Path(sys.executable).resolve())!=c['runtime']['python_executable_sha256']):raise ValueError('Materialized source or interpreter changed')


def require_domain(domain,peer,observation,shell,a):
 if (domain.get('schema')!='962-exact-apex1613031-old14-new14-domain-result/v1' or domain.get('status')!='same_compact_oriented_local_domain'
     or any(domain.get(k) is not True for k in ['exact_old_pair_embedding','exact_candidate_pair_embedding','local_domain_equivalence_proved','bound_inputs_unchanged','exact_common9_coordinate_words','exact_identical_oriented14_boundary','exact_signed_volume_identity'])
     or domain.get('pair_failures')!={'old':0,'candidate':0}
     or (domain.get('old_complete_unordered_pairs'),domain.get('candidate_complete_unordered_pairs'),domain.get('complete_unordered_pairs'),domain.get('plane_triples_enumerated'))!=(91,91,182,10192)
     or domain.get('source_sha256')!=FIXED_INPUTS[DOMAIN_SOURCE] or domain.get('contract_sha256')!=FIXED_INPUTS[DOMAIN_ACTUAL]
     or domain.get('source_candidate_report_sha256')!=WORKER_SHA or domain.get('source_candidate_arrays_sha256')!=ARRAYS_SHA
     or domain.get('source_candidate_independent_peer_sha256')!=FIXED_INPUTS[LOCAL_PEER]
     or domain.get('qualification')!=QUALIFICATION or domain.get('native_optimizer_or_meshwrite_calls')!=0 or domain.get('coordinates_changed') is not False
     or peer.get('schema')!='962-apex1613031-domain-independent-stopped-peer/v1' or peer.get('decision')!='CLEAR_COMPLETED_EXACT_LOCAL_DOMAIN_SAVED_ASSOCIATIONS'
     or peer.get('report',{}).get('sha256')!=FIXED_INPUTS[DOMAIN] or peer.get('bindings',{}).get('sha256')!=FIXED_INPUTS[DOMAIN_BINDINGS] or peer.get('blockers')!=[]):
  raise ValueError('Completed current old14/new14 domain report and independent saved-association peer required')
 for name in [WORKER,ARRAYS,LOCAL_PEER,OBSERVATION,SHELL]:
  if domain['input_hashes'].get(name)!=FIXED_INPUTS[name]:raise ValueError('Current domain source/input association differs')
 expected_map={str(tag):i+1 for i,tag in enumerate(shell['local_to_global_node_tags'])};expected_map[str(APEX)]=10
 if domain.get('original_global_to_comparison_node_tags')!=expected_map:raise ValueError('Exact original14 comparison mapping required')
 expected_faces=sorted(min(tuple(face[i:]+face[:i]) for i in range(3)) for face in [row['local_node_tags'] for row in shell['oriented_triangle_rows']])
 for name,cells,count,internal in [('old',{row['tetrahedron_tag']:row['node_tags'] for row in observation['native_ordered_cell_rows']},91,21),('candidate',dict(zip(a['tetra_tags'],a['tetra_node_tags'])),91,21)]:
  data=domain[name];rows=domain['pair_results'][name]
  if (data['cell_count']!=len(cells) or data['internal_face_pairs']!=internal or data.get('all_exact_positive') is not True
      or [tuple(face) for face in data['oriented_boundary']]!=expected_faces
      or len(rows)!=count or [tuple(row['tetrahedron_tags']) for row in rows]!=list(combinations(sorted(cells),2))
      or any(row.get('intersection_equals_tagged_shared_simplex') is not True or row.get('plane_triples_enumerated')!=56 or row.get('illegal_intersection_vertices')!=0 or row.get('all_illegal_rational_witnesses')!=[] for row in rows)):
   raise ValueError('Complete current pair-result coverage/common shell required; predicates are not rerun')
 acceptance=json.loads((ROOT/DOMAIN_ACCEPT).read_text())
 if (acceptance.get('decision')!='ACCEPT_RELATIVE_LOCAL_OCCUPIED_DOMAIN_EQUALITY_ONLY' or acceptance.get('relative_local_domain_accepted') is not True
     or acceptance['report']['sha256']!=FIXED_INPUTS[DOMAIN] or acceptance['peer']['sha256']!=FIXED_INPUTS[DOMAIN_PEER]
     or acceptance['peer_bindings']['sha256']!=FIXED_INPUTS[DOMAIN_BINDINGS] or acceptance.get('historical_d60_command_conformant') is not False
     or domain.get('source_candidate_root_acceptance_sha256')!=FIXED_INPUTS[LOCAL_ACCEPT]
     or any(r.get('upstream_census_launch_deviation_sha256')!=FIXED_INPUTS[DEVIATION] or r.get('declared_controller_command_conformant') is not False for r in [domain,peer])):
  raise ValueError('Accepted relative-local domain and preserved d60 scope required')
 if domain['old']['exact_signed_volume_mm3']!=domain['candidate']['exact_signed_volume_mm3'] or domain['old']['exact_signed_volume_mm3']!={k:str(v) for k,v in shell['exact_enclosed_volume_mm3'].items()}:
  raise ValueError('Exact current common-shell volume proof differs')

def candidate_rows(worker,arrays,domain,peer,observation,shell):
 a=arrays['saved_reopen'];state=worker['saved_reopen']
 if (worker.get('status')!='completed_specific_cavity_Netgen_only'
     or any(worker.get(k) is not True for k in ['fixture_procedural_checks_passed','actual_SICN_gate_passed','saved_mesh_identity_exact','bound_inputs_unchanged','exact_boundary_bits_faces_classifications'])
     or any(worker.get(k) is not False for k in ['head_execution_authorized','stitching_authorized','native_head_application_authorized','engineering_accepted','physics_qualified','manufacturing_authorized'])
     or worker.get('full_tiny_arrays_sha256')!=ARRAYS_SHA or worker['after']!=state
     or (state['nodes'],state['tetrahedra'],state['referenced_interior_nodes'],state['unreferenced_nodes'])!=(10,14,1,0)
     or a['node_tags']!=sorted(set(a['node_tags'])) or a['tetra_tags']!=sorted(set(a['tetra_tags']))
     or {t for t,d in state['node_classifications'] if d==2}!=set(range(1,10))
     or {t for t,d in state['node_classifications'] if d==3}!=set(a['node_tags'])-set(range(1,10))
     or any([t,d,e]!=[t,(2 if t<=9 else 3),1] for t,d,e in state['node_entity_classifications'])
     or len(a['coordinates_mm'])!=10 or len(a['tetra_node_tags'])!=14 or arrays['after']!=a):
  raise ValueError('Exact completed current10-node14-cell raw saved Netgen state required')
 local_peer=json.loads((ROOT/LOCAL_PEER).read_text());local_bindings=json.loads((ROOT/LOCAL_BINDINGS).read_text());acceptance=json.loads((ROOT/LOCAL_ACCEPT).read_text())
 if (local_peer.get('schema')!='962-apex1613031-Netgen-result-peer/v1'
     or local_peer.get('decision')!='CLEAR_COMPLETED_LOCAL_SOFTWARE_QUALITY_PASS_ONLY_NO_DOMAIN_OR_HEAD_ADMISSION'
     or local_peer.get('bindings',{}).get('sha256')!=FIXED_INPUTS[LOCAL_BINDINGS]
     or local_peer.get('checked',{}).get('negative_baseline_d60false_historical1435493_label_and_false_qualifications_retained') is not True
     or local_bindings.get('schema')!='962-apex1613031-Netgen-result-peer-bindings/v1'
     or local_bindings.get('full8_output_inventory',{}).get('fixture-report.json')!={'path':WORKER,'sha256':WORKER_SHA,'bytes':17220}
     or local_bindings.get('full8_output_inventory',{}).get('arrays.json')!={'path':ARRAYS,'sha256':ARRAYS_SHA,'bytes':13885}
     or local_bindings.get('d60_historical_command_conformant') is not False
     or acceptance.get('schema')!='962-apex1613031-root-Netgen-result-peer-acceptance/v1'
     or acceptance.get('decision')!='ACCEPT_COMPLETED_LOCAL_SOFTWARE_QUALITY_PASS_ONLY'
     or acceptance.get('peer',{}).get('sha256')!=FIXED_INPUTS[LOCAL_PEER]
     or acceptance.get('peer_bindings',{}).get('sha256')!=FIXED_INPUTS[LOCAL_BINDINGS]
     or acceptance.get('historical_d60_command_conformant') is not False
     or any(acceptance.get(k) is not False for k in ['next_domain_query_execution_authorized','outside_owner_context_query_authorized','head_execution_authorized','stitching_authorized','feasibility_accepted','engineering_accepted','physics_qualified','material_qualified','process_calibrated','manufacturing_authorized'])):
  raise ValueError('Actual current Netgen peer full8 descriptors and root local-only acceptance required')
 coordinates=[]
 for xyz in a['coordinates_mm']:
  if len(xyz)!=3 or any(type(v) is not float or not math.isfinite(v) for v in xyz):raise ValueError('Complete finite raw binary64 coordinate triples required')
  coordinates.append(list(xyz)) # Copy raw float words including signed zero, never Fraction roundtrips.
 if (any(len(row)!=4 or len(set(row))!=4 or any(type(t) is not int or t not in a['node_tags'] for t in row) for row in a['tetra_node_tags'])
     or set().union(*(set(row) for row in a['tetra_node_tags']))!=set(a['node_tags'])):raise ValueError('Full14 ordered TET4 membership and no orphan required')
 for name in ['SICN','Jacobian','native_volume_mm3']:
  values=a['native_qualities'][name]
  if len(values)!=14 or any(type(v) is not float or not math.isfinite(v) or v<=0 for v in values) or (name=='SICN' and any(v<.1 for v in values)):
   raise ValueError('Complete14 finite positive native metrics and unchanged SICN0.1 required')
 if [struct.pack('<3d',*row) for row in a['coordinates_mm']]!=[struct.pack('<3d',*row) for row in arrays['after']['coordinates_mm']]:raise ValueError('After/saved raw coordinate words differ')
 for saved,after in [(a['independent_signed_volume_mm3'],arrays['after']['independent_signed_volume_mm3']),*[(a['native_qualities'][n],arrays['after']['native_qualities'][n]) for n in ['SICN','Jacobian','native_volume_mm3']]]:
  if [struct.pack('<d',v) for v in saved]!=[struct.pack('<d',v) for v in after]:raise ValueError('After/saved raw metric words differ')
 require_domain(domain,peer,observation,shell,a)
 exact=domain['candidate']['quality_rows']
 if len(exact)!=14 or [row['tetrahedron_tag'] for row in exact]!=a['tetra_tags']:raise ValueError('Complete14 accepted exact candidate associations required')
 for proof,conn in zip(exact,a['tetra_node_tags']):
  det=proof['exact_determinant_mm3'];q=proof['exact_SICN_squared']
  if (proof['ordered_node_tags']!=conn or proof.get('exact_point1_gate_passed') is not True or Fraction(int(det['numerator']),int(det['denominator']))<=0 or Fraction(int(q['numerator']),int(q['denominator']))<Fraction(1,100)):
   raise ValueError('Every current exact candidate positive determinant and SICN squared gate required')
 return dict(zip(a['node_tags'],coordinates))


def edit_once(gmsh,case,counts):
 if len(case['old'])!=14 or not case['old']:raise ValueError('Complete nonempty14-cell removal required')
 if gmsh.model.mesh.getMaxNodeTag()!=case['nmax'] or gmsh.model.mesh.getMaxElementTag()!=case['emax']:raise ValueError('Fresh full-parent maxima changed before edit')
 for tag,row in case['old'].items():
  kind,nodes,dim,entity=gmsh.model.mesh.getElement(tag)
  if kind!=4 or list(nodes)!=row or (dim,entity)!=(3,1):raise ValueError('Every complete old row/entity must remain exact')
 xyz,param,dim,entity=gmsh.model.mesh.getNode(APEX)
 if (dim,entity)!=(3,1) or [struct.pack('<d',v) for v in param]!=[struct.pack('<d',v) for v in case['apex_parameters']]:raise ValueError('Original apex storage class/parameters changed')
 counts['removeElements']+=1;gmsh.model.mesh.removeElements(3,1,sorted(case['old']))
 counts['setNode']+=1;gmsh.model.mesh.setNode(APEX,case['proposed'][APEX],case['apex_parameters'])
 tags=case['fresh_nodes']
 if tags:
  counts['addNodes']+=1;gmsh.model.mesh.addNodes(3,1,tags,[x for t in tags for x in case['proposed'][t]])
 counts['addElementsByType']+=1;gmsh.model.mesh.addElementsByType(1,4,list(case['replacement']),[t for r in case['replacement'].values() for t in r])
 counts['rebuildNodeCache']+=1;gmsh.model.mesh.rebuildNodeCache(False)
 counts['rebuildElementCache']+=1;gmsh.model.mesh.rebuildElementCache(False)


def allocate_case(row,shell,a,nmax,emax):
 """Only fixed saved tag/row associations; first actual interior tag is a storage slot."""
 interior=row['candidate_interior_node_tags'];tags=a['node_tags'];xyz=a['coordinates_mm'];old=row['old_tetrahedron_tags']
 if (interior!=sorted(set(interior)) or len(interior)!=row['I'] or row['I']<1 or row['M']<row['K']
     or tags!=sorted(set(tags)) or len(tags)!=len(xyz) or len(tags)!=row['N']
     or set(tags)!=set(range(1,row['NV']+1))|set(interior) or any(type(t) is not int or t<=row['NV'] for t in interior)
     or old!=sorted(set(old)) or len(old)!=row['K'] or a['tetra_tags']!=sorted(set(a['tetra_tags']))
     or len(a['tetra_tags'])!=row['M'] or len(a['tetra_node_tags'])!=row['M']
     or any(len(p)!=3 or any(type(v) is not float or not math.isfinite(v) for v in p) for p in xyz)
     or any(len(c)!=4 or len(set(c))!=4 or not set(c)<=set(tags) for c in a['tetra_node_tags'])
     or set().union(*(set(c) for c in a['tetra_node_tags']))!=set(tags)):
  raise ValueError('Complete saved tag lookup/dynamic counts/no-orphan storage policy required')
 coordinates=dict(zip(tags,xyz));fresh=list(range(nmax+1,nmax+row['I']));slots=old+list(range(emax+1,emax+row['M']-row['K']+1))
 if (len(shell['local_to_global_node_tags'])!=row['NV'] or len(set(shell['local_to_global_node_tags']))!=row['NV'] or row['apex'] in shell['local_to_global_node_tags']
     or any(type(t) is not int or t<=0 or t>nmax for t in [row['apex'],*shell['local_to_global_node_tags']])
     or any(type(t) is not int or t<=0 or t>emax for t in old)
     or max([nmax,*fresh,emax,*slots])>=2**64 or len(slots)!=len(set(slots))):raise ValueError('Tag allocation overflow/collision')
 mapping={i+1:t for i,t in enumerate(shell['local_to_global_node_tags'])};mapping.update(dict(zip(interior,[row['apex'],*fresh])))
 if len(mapping)!=row['N'] or len(set(mapping.values()))!=row['N']:raise ValueError('Complete injective local/global storage map required')
 proposed={mapping[t]:list(coordinates[t]) for t in tags}
 replacement={slot:[mapping[t] for t in conn] for slot,conn in zip(slots,a['tetra_node_tags'])}
 return dict(apex=row['apex'],node_map=mapping,fresh_nodes=fresh,element_slots=slots,replacement=replacement,proposed=proposed,
  local_tetra_tags=a['tetra_tags'],interior_node_tags=interior)


def make_case(observation,shell,candidate,arrays,context,domain,domain_peer):
 coordinates=candidate_rows(candidate,arrays,domain,domain_peer,observation,shell)
 mapping=shell['local_to_global_node_tags'];old={row['tetrahedron_tag']:row['node_tags'] for row in observation['native_ordered_cell_rows']}
 accepted=json.loads((ROOT/CONTEXT_ACCEPT).read_text());peer=json.loads((ROOT/CONTEXT_PEER).read_text());closed=json.loads((ROOT/CONTEXT_CLOSED).read_text())
 if (observation.get('apex')!=APEX or len(mapping)!=9 or len(set(mapping))!=9 or APEX in mapping or len(old)!=14
     or any(len(row)!=4 or len(set(row))!=4 or APEX not in row for row in old.values())
     or context.get('status')!='complete_current127_partial_head_apex1613031_context_census' or context.get('complete_context_census') is not True
     or context.get('original_parent_MSH_sha256')!=FIXED_INPUTS[MESH]
     or context['complete_old_apex_incident_rows']!=[{'tetrahedron_tag':t,'node_tags':old[t]} for t in sorted(old)]
     or context['independently_derived_global_maxima']!={'node':NMAX,'element_all_dimensions':EMAX}
     or accepted.get('decision')!='ACCEPT_COMPLETED_READ_ONLY_CURRENT129_ONE_CASE_CONTEXT_ONLY' or accepted.get('accepted_read_only_context') is not True
     or accepted.get('schema')!='962-current127-apex1613031-context-root-peer-acceptance/v1'
     or peer.get('schema')!='962-current127-apex1613031-context-independent-stopped-peer/v1'
     or peer.get('decision')!='CLEAR_COMPLETED_READ_ONLY_CONTEXT_SAVED_ASSOCIATIONS_ONLY'
     or accepted['report']['sha256']!=FIXED_INPUTS[CONTEXT] or accepted['peer']['sha256']!=FIXED_INPUTS[CONTEXT_PEER]
     or accepted['peer_bindings']['sha256']!=FIXED_INPUTS[CONTEXT_BINDINGS] or peer['bindings']['sha256']!=FIXED_INPUTS[CONTEXT_BINDINGS]
     or peer['report']['sha256']!=FIXED_INPUTS[CONTEXT]
     or closed.get('schema')!='962-current127-apex1613031-context-root-closed/v1'
     or closed['outputs']['readback-report.json']['sha256']!=FIXED_INPUTS[CONTEXT]
     or closed.get('returncode')!=0 or closed.get('error') is not None or closed.get('signals')!=[] or closed.get('outer_fallback_used') is not False
     or any(closed.get(k) is not True for k in ['controller_waited_reaped','controller_owned_group_absent','all66_inputs_unchanged','runtime5_unchanged','static4_unchanged'])
     or any(r.get('upstream_census_launch_deviation_sha256')!=FIXED_INPUTS[DEVIATION] or r.get('declared_controller_command_conformant') is not False for r in [observation,shell,context,accepted])):
  raise ValueError('Accepted fresh current127 original14-star context and preserved d60 required')
 original={r['node_tag']:r for r in observation['selected_node_rows']};native={r['node_tag']:r for r in context['selected10_native_node_rows']}
 classes={tag:[r['dimension'],r['entity_tag']] for tag,r in native.items()}
 if set(original)!=set(mapping+[APEX]) or set(native)!=set(original):raise ValueError('All10 original coordinate/class rows required')
 for tag,row in original.items():
  actual=native[tag]
  if (struct.pack('<3d',*row['coordinates_mm'])!=struct.pack('<3d',*actual['coordinates_mm']) or [float(v).hex() for v in row['coordinates_mm']]!=row['binary64_hex']
      or [float(v).hex() for v in actual['available_parametric_coordinates']]!=actual['parametric_binary64_hex']):raise ValueError('Every selected original word/available parameter row must join fresh context')
 if len(shell['vertex_rows'])!=9:raise ValueError('Complete9 fixed shell rows required')
 for local,row in enumerate(shell['vertex_rows'],1):
  tag=mapping[local-1]
  if (row['local_node_tag']!=local or row['source_global_node_tag']!=tag
      or struct.pack('<3d',*coordinates[local]).hex()!=row['binary64_little_endian_bytes_hex']
      or struct.pack('<3d',*coordinates[local])!=struct.pack('<3d',*original[tag]['coordinates_mm'])
      or classes[tag]!=([2,1] if row['original_source_boundary_node'] else [3,1])):raise ValueError('All5 source-boundary and4 source-interior shell identities must stay exact')
 if sum(r['original_source_boundary_node'] for r in shell['vertex_rows'])!=5 or classes[APEX]!=[3,1]:raise ValueError('Exact5/4 shell and volume apex classes required')
 expected={tuple(sorted(r['source_global_node_tags'])):r for r in shell['oriented_triangle_rows']};faces=context['all14_selected_shell_face_records']
 if len(faces)!=14 or {tuple(r['shell_face_key']) for r in faces}!=set(expected):raise ValueError('Every accepted selected shell face required')
 for face in faces:
  source=expected[tuple(face['shell_face_key'])]
  owners=face['owners'];inside=[r for r in owners if r['removed_star_owner']];outside=[r for r in owners if not r['removed_star_owner']]
  if (len(inside)!=1 or len(outside)>1 or inside[0]['tetrahedron_tag']!=source['source_owner_tetrahedron_tag']
      or inside[0]['node_tags']!=old[inside[0]['tetrahedron_tag']] or any((r['dimension'],r['entity_tag'])!=(3,1) for r in owners)):
   raise ValueError('Exact native volume1 old/outside owner associations required')
 interior=sorted(t for t,d in candidate['saved_reopen']['node_classifications'] if d==3)
 row=dict(apex=APEX,NV=9,N=10,K=14,M=14,I=1,candidate_interior_node_tags=interior,old_tetrahedron_tags=sorted(old))
 case=allocate_case(row,shell,arrays['saved_reopen'],NMAX,EMAX)
 case.update(old=old,nmax=NMAX,emax=EMAX,classes=classes,apices=[APEX],apex_parameters=list(native[APEX]['available_parametric_coordinates']),
  expected_counts={'nodes':1097222,'TET4':3621771,'interior':225491},expected_maxima={'node':NMAX,'element_all_dimensions':EMAX})
 if case['fresh_nodes']!=[] or case['element_slots']!=sorted(old) or len(case['replacement'])!=14:raise ValueError('Only apex storage and the same14 old TET slots permitted')
 return case


def source_reference(core,gmsh,context):
 np=core.np;nt,xyz,_=gmsh.model.mesh.getNodes();ix=np.argsort(nt);nt=np.asarray(nt,dtype='<u8')[ix];xyz=np.asarray(xyz,dtype='<f8').reshape(-1,3)[ix]
 expected=np.arange(1,BOUNDARY+1,dtype='<u8');where=np.searchsorted(nt,expected)
 if np.any(where>=len(nt)) or not np.array_equal(nt[where],expected):raise ValueError('Every original surface tag required')
 points=np.ascontiguousarray(xyz[where]);types,tags,conn=gmsh.model.mesh.getElements(2)
 if list(types)!=[2] or len(tags)!=1:raise ValueError('Exact complete original TRI3 surface required')
 order=np.argsort(tags[0]);tt=np.asarray(tags[0],dtype='<u8')[order];rows=np.asarray(conn[0],dtype='<u8').reshape(-1,3)[order]
 lower=context['full_lower_dimensional_inventory']
 if (len(lower)!=1 or len(rows)!=1743878 or core.array_sha(tt)!=lower[0]['element_tags_u64_sha256']
     or core.array_sha(rows)!=lower[0]['ordered_connectivity_u64_sha256'] or np.any(rows<1) or np.any(rows>BOUNDARY)):
  raise ValueError('Full ordered parent surface typed hashes changed')
 return points,rows.astype(np.int64)-1


def outside_reference(core,state,case):
 np=core.np;xyz,nt,et,en=state;a=np.asarray(case['apices'],dtype='<u8');u=np.asarray(sorted(case['old']),dtype='<u8')
 if not np.isin(a,nt).all() or not np.isin(u,et).all():raise ValueError('Every exact subset A/U tag must occur in full verified parent arrays')
 nodes=~np.isin(nt,a);cells=~np.isin(et,u)
 return {'outside_node_tags_u64_sha256':core.array_sha(nt[nodes]),'outside_coordinate_words_f64_sha256':core.array_sha(xyz[nodes]),
  'outside_tetra_tags_u64_sha256':core.array_sha(et[cells]),'outside_ordered_tetra_connectivity_u64_sha256':core.array_sha(en[cells]),
  'outside_nodes':int(np.count_nonzero(nodes)),'outside_TET4':int(np.count_nonzero(cells))}


def parameter_projection(inventory):
 return [{k:row[k] for k in ['dimension','entity_tag','count','parameter_width','node_tags_u64_sha256','available_parameter_words_f64_sha256']} for row in inventory]


def retained_positions(tags,retained):
 if (tags!=sorted(set(tags)) or retained!=sorted(set(retained)) or any(type(t) is not int or t<=0 for t in tags+retained)):
  raise ValueError('Sorted unique positive actual and retained original tags required')
 indices={tag:i for i,tag in enumerate(tags)}
 if not set(retained)<=set(tags):raise ValueError('A retained original tag disappeared')
 return [indices[tag] for tag in retained]


def parameter_record(core,dim,entity,owned,owned_xyz,params,width):
 return {'dimension':dim,'entity_tag':entity,'count':len(owned),'parameter_width':width,
  'node_tags_u64_sha256':core.array_sha(owned),'coordinate_words_f64_sha256':core.array_sha(owned_xyz),
  'available_parameter_words_f64_sha256':core.array_sha(params)}


def metadata_snapshot(core,gmsh,state,case,context,after):
 np=core.np;xyz,nt,et,en=state;entities=sorted((int(d),int(t)) for d,t in gmsh.model.getEntities())
 parameter_inventory=[];entity_rows=[];lower=[];periodic=[];all_lower=[];groups=[];dimensions=np.full(len(nt),-1,dtype=np.int8);entity_tags=np.zeros(len(nt),dtype=np.int64)
 for dim,entity in entities:
  boundary=[list(map(int,row)) for row in gmsh.model.getBoundary([(dim,entity)],combined=False,oriented=True,recursive=False)] if dim else []
  entity_rows.append({'dimension':dim,'entity_tag':entity,'oriented_immediate_boundary':boundary,'name':gmsh.model.getEntityName(dim,entity)})
  owned,owned_xyz,owned_param=gmsh.model.mesh.getNodes(dim,entity,False,True)
  owned=np.asarray(owned,dtype='<u8');ix=np.argsort(owned);owned=owned[ix];where=np.searchsorted(nt,owned)
  owned_xyz=np.asarray(owned_xyz,dtype='<f8').reshape(-1,3)[ix];parameter_width=dim if len(owned_param) else 0
  if (len(np.unique(owned))!=len(owned) or np.any(where>=len(nt)) or not np.array_equal(nt[where],owned) or np.any(dimensions[where]!=-1)
      or owned_xyz.tobytes()!=np.asarray(xyz[where],dtype='<f8').tobytes() or len(owned_param) not in (0,len(owned)*dim)):
   raise ValueError('Complete entity ownership/coordinate/available-parameter association required')
  dimensions[where]=dim;entity_tags[where]=entity
  params=np.asarray(owned_param,dtype='<f8').reshape(len(owned),parameter_width)[ix] if parameter_width else np.empty((len(owned),0),dtype='<f8')
  if not np.isfinite(params).all():raise ValueError('Finite available parameter words required')
  full=parameter_record(core,dim,entity,owned,owned_xyz,params,parameter_width)
  expected=next(r for r in context['full_entity_node_parameter_inventory'] if (r['dimension'],r['entity_tag'])==(dim,entity))
  if not after:
   if full!=expected:raise ValueError('Full before entity tags/coordinates/available parameters must equal fresh current context')
   case.setdefault('retained_entity_node_tags',{})[(dim,entity)]=owned[owned!=APEX].copy()
  retained=case['retained_entity_node_tags'][(dim,entity)]
  keep=retained_positions(owned.tolist(),retained.tolist())
  observed=parameter_record(core,dim,entity,owned[keep],owned_xyz[keep],params[keep],parameter_width)
  if not after:case.setdefault('retained_parameter_inventory',{})[(dim,entity)]=observed
  elif observed!=case['retained_parameter_inventory'][(dim,entity)]:raise ValueError('Every retained original parameter/coordinate word must remain exact')
  parameter_inventory.append(observed)
  if dim in (1,2):
   master,nodes,masters,transform=gmsh.model.mesh.getPeriodicNodes(dim,entity,True)
   periodic.append({'dimension':dim,'entity_tag':entity,'master_entity':int(master),'node_tags':list(map(int,nodes)),
    'master_node_tags':list(map(int,masters)),'affine_transform':list(map(float,transform))})
  if dim>=3:continue
  types,element_tags,element_nodes=gmsh.model.mesh.getElements(dim,entity)
  if not (len(types)==len(element_tags)==len(element_nodes)):raise ValueError('Complete lower-dimensional blocks required')
  for kind,tt,flat in zip(types,element_tags,element_nodes):
   kind=int(kind);properties=gmsh.model.mesh.getElementProperties(kind);width=int(properties[3])
   if int(properties[1])!=dim or width<=0 or len(flat)!=len(tt)*width:raise ValueError('Lower-dimensional type/row width changed')
   ix=np.argsort(tt);tt=np.asarray(tt,dtype='<u8')[ix];rows=np.asarray(flat,dtype='<u8').reshape(-1,width)[ix]
   if len(tt)!=len(np.unique(tt)) or (len(tt) and int(tt.min())<=0):raise ValueError('Unique positive lower-dimensional tags required')
   all_lower.append(tt)
   lower.append({'dimension':dim,'entity_tag':entity,'element_type':kind,'nodes_per_element':width,'count':len(tt),
    'minimum_tag':int(tt.min()) if len(tt) else None,'maximum_tag':int(tt.max()) if len(tt) else None,
    'element_tags_u64_sha256':core.array_sha(tt),'ordered_connectivity_u64_sha256':core.array_sha(rows)})
 for dim,tag in sorted(gmsh.model.getPhysicalGroups()):
  groups.append({'dimension':int(dim),'physical_tag':int(tag),'name':gmsh.model.getPhysicalName(dim,tag),'entity_tags':sorted(map(int,gmsh.model.getEntitiesForPhysicalGroup(dim,tag)))})
 lower.sort(key=lambda row:(row['dimension'],row['entity_tag'],row['element_type']))
 if np.any(dimensions<0):raise ValueError('Missing current node classifications')
 original=~np.isin(nt,np.asarray(case['fresh_nodes'],dtype='<u8'))
 if (core.array_sha(nt[original])!=context['full_array_sha256s']['sorted_node_tags_sha256']
     or core.array_sha(dimensions[original])!=context['full_native_classifications']['node_classification_dimensions_sha256']
     or core.array_sha(entity_tags[original])!=context['full_native_classifications']['node_classification_entity_tags_sha256']):
  raise ValueError('Every original node tag and classification must remain exact')
 fresh=np.flatnonzero(~original)
 if (len(fresh)!=(len(case['fresh_nodes']) if after else 0) or (after and (nt[fresh].tolist()!=case['fresh_nodes'] or np.any(dimensions[fresh]!=3) or np.any(entity_tags[fresh]!=1)))):
  raise ValueError('Only exact allocated fresh nodes on existing volume1 permitted')
 node_mask=~np.isin(nt,np.asarray([*case['apices'],*case['fresh_nodes']],dtype='<u8'))
 removed=list(case['replacement'] if after else case['old']);cell_mask=~np.isin(et,np.asarray(removed,dtype='<u8'))
 preservation={'outside_node_tags_u64_sha256':core.array_sha(nt[node_mask]),'outside_coordinate_words_f64_sha256':core.array_sha(xyz[node_mask]),
  'outside_tetra_tags_u64_sha256':core.array_sha(et[cell_mask]),'outside_ordered_tetra_connectivity_u64_sha256':core.array_sha(en[cell_mask]),
  'outside_nodes':int(np.count_nonzero(node_mask)),'outside_TET4':int(np.count_nonzero(cell_mask))}
 for key,value in preservation.items():
  if case['outside_reference'][key]!=value:raise ValueError('Outside preservation changed: '+key)
 metadata={'full_lower_dimensional_inventory':lower,'full_entity_metadata':entity_rows,'full_physical_group_metadata':groups,'full_periodic_metadata':periodic}
 for key,value in metadata.items():
  if value!=context[key]:raise ValueError('Complete original lower/entity/physical/periodic metadata changed: '+key)
 all_et=np.concatenate([et,*all_lower])
 if len(np.unique(all_et))!=len(all_et):raise ValueError('All-dimensional element tag collision refused')
 maxima={'node':int(nt.max()),'element_all_dimensions':int(all_et.max())}
 if maxima!=(case['expected_maxima'] if after else {'node':NMAX,'element_all_dimensions':EMAX}):raise ValueError('Complete actual maxima changed')
 if (int(gmsh.model.mesh.getMaxNodeTag()),int(gmsh.model.mesh.getMaxElementTag()))!=(maxima['node'],maxima['element_all_dimensions']):raise ValueError('Native tag caches differ from complete current arrays')
 for tag,expected in case['classes'].items():
  coordinates,param,dim,entity=gmsh.model.mesh.getNode(tag)
  if [int(dim),int(entity)]!=expected or [float(v).hex() for v in param]!=next(r['parametric_binary64_hex'] for r in context['selected10_native_node_rows'] if r['node_tag']==tag):raise ValueError('Selected original classification/parametric association changed')
  index=int(np.searchsorted(nt,tag));want=case['proposed'][tag] if after else next(r['coordinates_mm'] for r in context['selected10_native_node_rows'] if r['node_tag']==tag)
  if int(nt[index])!=tag or struct.pack('<3d',*coordinates)!=struct.pack('<3d',*want) or struct.pack('<3d',*xyz[index])!=struct.pack('<3d',*want):raise ValueError('Selected original coordinate words changed')
 if after:
  for tag,row in case['replacement'].items():
   index=int(np.searchsorted(et,tag))
   if index>=len(et) or int(et[index])!=tag or en[index].tolist()!=row:raise ValueError('Every new ordered replacement row required')
  for tag in case['fresh_nodes']:
   index=int(np.searchsorted(nt,tag))
   if struct.pack('<3d',*xyz[index])!=struct.pack('<3d',*case['proposed'][tag]):raise ValueError('Fresh proposed coordinate words changed')
 return dict(preservation=preservation,metadata_sha256s={key:json_sha(value) for key,value in metadata.items()},
  original_classification_projection_exact=True,new_nodes_on_volume1=len(case['fresh_nodes']) if after else 0,expected_new_nodes=len(case['fresh_nodes']),retained_original_parameter_projection=parameter_projection(parameter_inventory),maxima=maxima)


def require_snapshot(before,after):
 if (before['preservation']!=after['preservation'] or before['metadata_sha256s']!=after['metadata_sha256s']
     or before['retained_original_parameter_projection']!=after['retained_original_parameter_projection']):raise ValueError('Any subset outside or original metadata/parameter drift refused')
 if after['original_classification_projection_exact'] is not True or after['new_nodes_on_volume1']!=before['expected_new_nodes']:raise ValueError('Every original classification and allocated new node required')


def require_original_records(core,worker,receipt,first,closed,metadata,context):
 proof=core.partial_after_proof(worker,receipt,closed,metadata);core.require_after_match(first,proof,127)
 if (metadata['MSH_sha256']!=FIXED_INPUTS[MESH] or metadata['partial_report_sha256']!=FIXED_INPUTS[ORIGINAL_WORKER]
     or metadata['partial_contract_sha256']!=FIXED_INPUTS['work/962-engineering/apex1613790-head-application-001/frozen-contract.json']
     or proof['array_sha256s']!=context['full_array_sha256s'] or proof['classifications']!=context['full_native_classifications']
     or proof['source_boundary_identity']!=context['current_source_boundary_identity'] or proof['quality']!=context['retained_current_quality_and_global_incidence']['quality']
     or (proof['total_mesh_nodes'],proof['tetrahedra'],proof['tetra_referenced_interior_nodes'],proof['unreferenced_mesh_nodes'])!=(1097222,3621771,225491,0)):
  raise ValueError('Single stopped current partial.after/saved, fresh127 census and current context required')
 for key,value in proof['array_sha256s'].items():
  if first[key]!=value:raise ValueError('Current census full tagged-array association differs')
 return proof


def valid_positive_volume(audit):
 return all(row['nonpositive_count']==0 for row in audit['quality'].values()) and audit['volume_relative_error']<=1e-6


def main():
 c=json.loads((OUT/'frozen-contract.json').read_text());require_contract(c)
 if {p.name for p in OUT.iterdir()}!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:raise ValueError('Exactly fresh three-file materialization plus native.log required')
 report=dict(schema='962-apex1613031-head-application-result/v1',status='running',stage='imports',procedural_checks_passed=False,
  actual_whole_head_SICN_gate_passed=False,expected_whole_head_positive_poor_count_not_observed=126,
  expected_count_is_not_acceptance=True,native_operation_counts={k:0 for k in COUNTS},call_counts_are_attempts=True,
  original_parent_MSH_sha256=FIXED_INPUTS[MESH],local_candidate_report_sha256=FIXED_INPUTS[WORKER],local_candidate_arrays_sha256=FIXED_INPUTS[ARRAYS],current_local_domain_report_sha256=FIXED_INPUTS[DOMAIN],current_local_domain_peer_sha256=FIXED_INPUTS[DOMAIN_PEER],context_sha256=FIXED_INPUTS[CONTEXT],
  upstream_census_launch_deviation_sha256=FIXED_INPUTS[DEVIATION],declared_controller_command_conformant=False,
  retained_original_parameter_scope='Derived from full verified native before arrays excluding only apex1613031; added nodes never enter retained reference.',
  original_local_domain_equivalence_is_separate=True,global_embedding_or_containment_proved=False,
  stronger_Mesh2_criterion_passed=False,engineering_accepted=False,physics_qualified=False,material_qualified=False,process_calibrated=False,manufacturing_authorized=False)
 started=time.monotonic();gmsh=None;initialized=False
 def checkpoint():
  with (OUT/'readback-report.json').open('w') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
 try:
  import numpy as np
  import gmsh
  observed={'python':platform.python_version(),'numpy':np.__version__,'gmsh':gmsh.__version__,'machine':platform.machine()}
  runtime={'python':sha(Path(sys.executable).resolve()),'gmsh_module':sha(gmsh.__file__),'gmsh_library':sha(gmsh.lib._name)}
  if (observed!=RUNTIME or runtime!=c['runtime_sha256s'] or Path(np.__file__).resolve()!=Path(c['numpy_init']).resolve() or sha(np.__file__)!=c['numpy_init_sha256']):raise ValueError('Exact selected native/NumPy runtime required')
  report.update(runtime=observed,runtime_sha256s=runtime)
  ns={'np':np,'math':math,'hashlib':hashlib}
  selected(HEAD,['array_sha','volume_arrays','canonical_oriented','surface_roundtrip','distribution','tetra_volumes','tetra_boundary'],ns)
  selected(CORE,['tagged_volume','internal_face_orientation'],ns)
  selected(AUDIT,['classifications','array_identity','boundary_identity','audit_after'],ns)
  selected(PROOF_SOURCE,['partial_after_proof','require_after_match'],ns)
  core=SimpleNamespace(np=np,CANDIDATE_VOLUME=915453.1236217883,**{k:v for k,v in ns.items() if callable(v)})
  context=json.loads((ROOT/CONTEXT).read_text());observation=json.loads((ROOT/OBSERVATION).read_text());shell=json.loads((ROOT/SHELL).read_text())
  candidate=json.loads((ROOT/WORKER).read_text());arrays=json.loads((ROOT/ARRAYS).read_text())
  domain=json.loads((ROOT/DOMAIN).read_text());domain_peer=json.loads((ROOT/DOMAIN_PEER).read_text());case=make_case(observation,shell,candidate,arrays,context,domain,domain_peer)
  worker=json.loads((ROOT/ORIGINAL_WORKER).read_text());first=json.loads((ROOT/FIRST).read_text())
  proof=require_original_records(core,worker,json.loads((ROOT/ORIGINAL_RECEIPT).read_text()),first,json.loads((ROOT/PARTIAL_CLOSED).read_text()),json.loads((ROOT/PARTIAL_METADATA).read_text()),context)
  report.update(local_to_global_node_map=case['node_map'],replacement_element_slots=case['element_slots'],replacement_ordered_rows=case['replacement'])
  gmsh.initialize([],readConfigFiles=False,run=False);initialized=True;gmsh.logger.start()
  for key,value in OPTIONS.items():gmsh.option.setNumber(key,value)
  report['stage']='opening_exact_current_partial_head';checkpoint();gmsh.open(str(ROOT/MESH))
  points,faces=source_reference(core,gmsh,context)
  report['stage']='complete_before_audit';checkpoint();state,before=core.audit_after(core,gmsh,points,faces)
  before['source_boundary_identity']=core.boundary_identity(core,state,points,before['classifications'])
  if before!=proof or not valid_positive_volume(before):raise ValueError('Complete fresh original audit must equal sole current partial worker.after')
  case['outside_reference']=outside_reference(core,state,case)
  if case['outside_reference']!={k:context['future_preservation_references'][k] for k in case['outside_reference']}:raise ValueError('Exact one-apex14-cell before masks differ from accepted context')
  before_snapshot=metadata_snapshot(core,gmsh,state,case,context,False);del state
  report.update(before=before,before_preservation=before_snapshot,stage='one_tag_sparse_replacement');checkpoint()
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError('Options changed before replacement')
  report['partial_replacement_attempted']=True;edit_once(gmsh,case,report['native_operation_counts']);report['partial_replacement_completed']=True
  report['stage']='complete_after_audit';checkpoint();state,after=core.audit_after(core,gmsh,points,faces)
  after['source_boundary_identity']=core.boundary_identity(core,state,points,after['classifications'])
  after_snapshot=metadata_snapshot(core,gmsh,state,case,context,True);require_snapshot(before_snapshot,after_snapshot)
  if (after['total_mesh_nodes'],after['tetrahedra'],after['tetra_referenced_interior_nodes'])!=(1097222,3621771,225491) or not valid_positive_volume(after):raise ValueError('Actual changed counts/positive metrics/relative volume gate failed')
  if after['source_boundary_identity']!=before['source_boundary_identity']:raise ValueError('Original exact boundary bits/classes/periodicity changed')
  local_et=np.asarray(case['element_slots'],dtype='<u8');local_metrics={name:np.asarray(gmsh.model.mesh.getElementQualities(local_et,api),dtype='<f8') for name,api in [('SICN','minSICN'),('Jacobian','minDetJac'),('native_volume_mm3','volume')]}
  if any(len(v)!=14 or not np.isfinite(v).all() or np.any(v<=0) for v in local_metrics.values()) or np.any(local_metrics['SICN']<.1):raise ValueError('Every actual replacement cell must freshly pass unchanged local SICN/positivity gate')
  report.update(after=after,after_preservation=after_snapshot,replacement14_native_metrics={k:v.tolist() for k,v in local_metrics.items()},actual_replacement14_SICN_gate_passed=True)
  del state
  path=OUT/'head-volume.msh';report['stage']='saving_partial_repair';checkpoint();report['native_operation_counts']['write_mesh']+=1;gmsh.write(str(path));digest=sha(path)
  gmsh.clear();gmsh.open(str(path));report['stage']='complete_saved_reopen_audit';checkpoint();state,saved=core.audit_after(core,gmsh,points,faces)
  saved['source_boundary_identity']=core.boundary_identity(core,state,points,saved['classifications'])
  saved_snapshot=metadata_snapshot(core,gmsh,state,case,context,True);require_snapshot(before_snapshot,saved_snapshot)
  if saved!=after or saved_snapshot!=after_snapshot or sha(path)!=digest:raise ValueError('Full after/saved tagged arrays/metrics/classifications/metadata identity changed')
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()) or report['native_operation_counts']!=COUNTS:raise ValueError('Exact options/API operation attempts changed')
  report.update(saved_reopen=saved,saved_preservation=saved_snapshot,saved_mesh_identity_exact=True,mesh_sha256=digest,mesh_bytes=path.stat().st_size,
   procedural_checks_passed=True,actual_whole_head_SICN_gate_passed=after['quality']['minimum_SICN']['minimum']>=.1,
   actual_whole_head_positive_poor_count=after['quality']['minimum_SICN']['below_point1_count'],stage='completed_partial_repair_audits',status='completed_partial_head_replacement_whole_head_quality_gate_applied')
 except Exception as error:report.update(status='refused_or_failed_outputs_preserved',error=type(error).__name__+': '+str(error))
 finally:
  if initialized:
   try:report['gmsh_warnings_errors']=[s for s in gmsh.logger.get() if s.startswith(('Warning','Error'))];gmsh.logger.stop()
   except Exception as error:report.update(status='failed_runtime_cleanup',cleanup_error=type(error).__name__+': '+str(error),procedural_checks_passed=False)
   try:gmsh.finalize()
   except Exception as error:report.update(status='failed_runtime_cleanup',finalize_error=type(error).__name__+': '+str(error),procedural_checks_passed=False)
  try:require_contract(c);report['bound_inputs_unchanged']=True
  except Exception:report['bound_inputs_unchanged']=False
  report['wall_seconds']=time.monotonic()-started;checkpoint()
 return 0 if report['procedural_checks_passed'] and report['actual_whole_head_SICN_gate_passed'] and report['bound_inputs_unchanged'] else 2


if __name__=='__main__':raise SystemExit(main())
