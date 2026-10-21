"""HELD current129 single28-to44 partial application; no mesher or optimizer."""
from pathlib import Path
from fractions import Fraction
from types import SimpleNamespace
from itertools import combinations
import ast,hashlib,json,math,platform,struct,sys,time
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
OUTPUT='work/962-engineering/apex1613790-head-application-001'
MESH='work/962-engineering/head-star-current204-combined-application-001/head-volume.msh'
CONTEXT='work/962-engineering/current129-apex1613790-head-context-001/readback-report.json'
CONTEXT_CONTRACT='work/962-engineering/current129-apex1613790-head-context-001/frozen-contract.json'
OBSERVATION='work/962-engineering/direct-sicn-apex1613790-cavity-study-001/saved-star-observation.json'
SHELL='work/962-engineering/direct-sicn-apex1613790-cavity-study-001/local-shell-input-001.json'
ARRAYS='work/962-engineering/fixed-shell-netgen-apex1613790-001/arrays.json'
WORKER='work/962-engineering/fixed-shell-netgen-apex1613790-001/fixture-report.json'
LOCAL_PEER='work/962-engineering/fixed-shell-netgen-apex1613790-result-peer-001/review.json'
DOMAIN='work/962-engineering/apex1613790-domain-equivalence-001/report.json'
DOMAIN_PEER='work/962-engineering/apex1613790-domain-equivalence-result-peer-001/review.json'
DOMAIN_SOURCE='work/962-engineering/apex1613790-domain-equivalence-prep-001/certify_domain.py'
DOMAIN_ACTUAL='work/962-engineering/apex1613790-domain-equivalence-execution-prep-001/actual-contract.json'
ORIGINAL_WORKER='work/962-engineering/head-star-current204-combined-application-001/readback-report.json'
ORIGINAL_RECEIPT='work/962-engineering/head-star-current204-combined-application-001/execution-receipt.json'
PARTIAL_CLOSED='work/962-engineering/head-star-current204-combined-application-root-execution-001/closed-result.json'
PARTIAL_METADATA='work/962-engineering/head-star-current129-full-stars-001/frozen-contract.json'
FIRST='work/962-engineering/head-star-current129-full-stars-001/readback-report.json'
PROOF_SOURCE='work/962-engineering/head-star-current129-full-stars-prep-001/reader.py'
CONTEXT_PEER='work/962-engineering/current129-apex1613790-head-context-result-peer-001/review.json'
CONTEXT_ACCEPT='work/962-engineering/current129-apex1613790-head-context-root-execution-001/result-peer-acceptance.json'
CONTEXT_CLOSED='work/962-engineering/current129-apex1613790-head-context-root-execution-001/closed-result.json'
DOMAIN_ACCEPT='work/962-engineering/apex1613790-domain-equivalence-root-execution-001/result-peer-acceptance.json'
LOCAL_ACCEPT='work/962-engineering/fixed-shell-netgen-apex1613790-root-execution-001/stopped-peer-acceptance.json'
DEVIATION='work/962-engineering/head-star-current129-full-stars-root-execution-001/launch-deviation-001.json'
HEAD='twins/962-cylinder-head-f0/source/mesh_head.py'
CORE='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py'
AUDIT='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-netgen-postexport-prep-002/mesh_delaunay_netgen_postexport.py'
FIXED_INPUTS={'twins/962-cylinder-head-f0/source/mesh_head.py': '69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5', 'work/962-engineering/apex1474426-head-application-prep-001/reader.py': '15443fe1c0adebb02a4abe8a4db1c8dbb2f5148ad37f992ae8e74df8cd28d7d1', 'work/962-engineering/apex1474426-head-application-prep-001/run_readback.py': '5ab38b53e4019506772cc429b46699ac0e217141c87a0a043718d8123ecb159c', 'work/962-engineering/apex1474426-head-application-prep-001/selfcheck.py': 'd2476918035cb02d62abfedb0c5e65614005a757ce0fbdedd853dc29aab9e9c5', 'work/962-engineering/apex1613790-domain-equivalence-001/report.json': 'c2808c3d087d748cb8ce8a53ca93ab1c635548a2fb372b98558c23efc0fa17ec', 'work/962-engineering/apex1613790-domain-equivalence-execution-prep-001/actual-contract.json': 'f23cb547e9ea6eb5726d7c697b42ff961a4595ea48ce792097ff50174d044c9e', 'work/962-engineering/apex1613790-domain-equivalence-prep-001/certify_domain.py': '169b475419b76e5f6ebaf5a9b59c75b4fa13354168daf40ca44f5e14d70cb1e4', 'work/962-engineering/apex1613790-domain-equivalence-result-peer-001/review.json': 'dcd79541a59bea5baaf2199c51d1072b4d7be1ec9386874086377eb2832831ca', 'work/962-engineering/apex1613790-domain-equivalence-root-execution-001/closed-result.json': 'c9d8493732bb070a740a965af36d7acf405822961ec30b54148c86488a5ea33d', 'work/962-engineering/apex1613790-domain-equivalence-root-execution-001/result-peer-acceptance.json': '068da5cdc4e92696708f95d1b66733bc9f468767c99a2ac3617fea8e5cf8f7ff', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-netgen-postexport-prep-002/mesh_delaunay_netgen_postexport.py': '0d1dd1f0625275343f16b713dae2d41143dda8da974bef42e59f6bfa3b0e388a', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py': 'a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4', 'work/962-engineering/current129-apex1613790-head-context-001/frozen-contract.json': 'c00ec1428e64e4615cbad22206c72f8a4644e2f9e616a46512ac51d4caca5cc8', 'work/962-engineering/current129-apex1613790-head-context-001/readback-report.json': '035adeb6d5d4d75756c0fde9eb07de44a6e4507995c58e9f217453f3bfcbe29a', 'work/962-engineering/current129-apex1613790-head-context-prep-001/reader.py': 'beafd637f8f7065bf4a40f777d970245d5ffdb5d7f8ca11fd6357c905b52ff14', 'work/962-engineering/current129-apex1613790-head-context-result-peer-001/review.json': '206d5aea3db8628de0e285e954f9013b0e97fdbc5be3d9f3980ff75a54ea118e', 'work/962-engineering/current129-apex1613790-head-context-root-execution-001/closed-result.json': 'cf7fa7cd1d2a90539c4345b2f3bd6f789cbaf904dd31d2a2bcb69201a891d218', 'work/962-engineering/current129-apex1613790-head-context-root-execution-001/result-peer-acceptance.json': 'c626d0601c7706f8bab96431f3d3baac34e89a8af824528364399162129eed7d', 'work/962-engineering/direct-sicn-apex1613790-cavity-study-001/local-shell-input-001.json': 'f31dfcd760db5c8765fcd0665ea3a9b17d5cf81d35d91467b924d3c660d0bcb9', 'work/962-engineering/direct-sicn-apex1613790-cavity-study-001/saved-star-observation.json': '94d4b57c10ab8b7d0fdf0f9a9385d7f93494ae29c0e59296937da89648cd410b', 'work/962-engineering/fixed-shell-netgen-apex1613790-001/arrays.json': 'fa230900eaa2318c09d22a088e846e0b0a74a0d1ebfee4b9427e24135576b4eb', 'work/962-engineering/fixed-shell-netgen-apex1613790-001/execution-receipt.json': '49e8aafeba44fd9d40a34dbac4e425ed0fba5a4def79a9010f4fede85ea25d5d', 'work/962-engineering/fixed-shell-netgen-apex1613790-001/fixture-report.json': 'fa8bf35b24066657e87cb7ce196e6e1b09a8b58bc583736fa7167d88cfa711e3', 'work/962-engineering/fixed-shell-netgen-apex1613790-result-peer-001/review.json': 'fd1eab60294ebe114bd3ab784773ae0b33ba8b5b05b5af267603b764952e2260', 'work/962-engineering/fixed-shell-netgen-apex1613790-root-execution-001/stopped-peer-acceptance.json': 'b54b588fc96c3014ae1631f2b01785ab7a2f732f2de48cef2ee6ece1dfe45100', 'work/962-engineering/head-star-current129-full-stars-001/frozen-contract.json': 'ec888011591b8eda74ae83a4a3e796d1ab6d2cf555d99fba1fbbc2c003fb215f', 'work/962-engineering/head-star-current129-full-stars-001/readback-report.json': 'a030a89ed377459bb7783c3da0dedec9b320dcb1935bec8a4e4d9a00ab49835b', 'work/962-engineering/head-star-current129-full-stars-prep-001/reader.py': '186f3a52ac2f227afc56dfc7ec1cf9ab7a85e0303c04a2ad7dea32b74aa6d108', 'work/962-engineering/head-star-current129-full-stars-result-peer-001/review.json': '312347305a02687824d62150fe61c5db6d08110bd13d559cadf83204dd60b620', 'work/962-engineering/head-star-current129-full-stars-root-execution-001/launch-deviation-001.json': 'd60fff297c6c45dc92e117262e36ffde36e2169d53fcd32ce2b79fabde5eebc3', 'work/962-engineering/head-star-current129-full-stars-root-execution-001/result-peer-acceptance.json': '88fb86b6973eec793069fc5f5d6a624e785c2af9c2aca8f05b13c557c02da540', 'work/962-engineering/head-star-current204-combined-application-001/execution-receipt.json': '911f4926f6dff9ec3b900ad8414f92a44adb7e5333e60ed6371bb413f46b18a1', 'work/962-engineering/head-star-current204-combined-application-001/frozen-contract.json': '98949f822fafd53199204eb812e5eec85b93516873743637de5b1baab5a2b600', 'work/962-engineering/head-star-current204-combined-application-001/head-volume.msh': 'b512a6ce68f48b95908cfe9c1c75a94c8b7c31a8929ea40254a1f9695a52f0b5', 'work/962-engineering/head-star-current204-combined-application-001/readback-report.json': '6ae60abe5266f1c932780b948961285ed6ef9b7944cf894be4ead4482c007a87', 'work/962-engineering/head-star-current204-combined-application-001/reader.py': 'c66da821a1d98794ed78f403067e02c349c11a59d6c22de72e587b05e5fc82f5', 'work/962-engineering/head-star-current204-combined-application-root-execution-001/closed-result.json': '36f4cfbde50c83680fd617dcc7536ddaba3c7d57ccb8cbf3b4263629df9f7684', 'work/962-engineering/head-star-current204-combined-application-root-execution-001/result-peer-acceptance.json': '8121973d3978ca0ce9575417fdcef90cd775d91ba1f47f50aeeb58f1f329d498', 'work/962-engineering/head-star-current204-union-context-prep-002/reader.py': 'c852a8a536a0ef2c58a37132fb51e42e525403d1f519375cc04a9860bfe53b29'}
ARRAYS_SHA=FIXED_INPUTS[ARRAYS];WORKER_SHA=FIXED_INPUTS[WORKER]
APEX=1613790;NMAX=1613974;EMAX=32159061;BOUNDARY=871731
RUNTIME={'python':'3.10.11','numpy':'2.0.2','gmsh':'4.15.2','machine':'arm64'}
OPTIONS={'General.NumThreads':2,'Mesh.MaxNumThreads3D':2,'Mesh.Renumber':0,
 'Mesh.Optimize':0,'Mesh.OptimizeNetgen':0,'Mesh.Binary':1,'Mesh.SaveAll':1,'Mesh.MshFileVersion':4.1}
CONTROLS={'hard_wall_seconds':1200,'sampled_RSS_stop_bytes':8*1024**3,'sampled_output_stop_bytes':1024**3,'native_threads':2,'automatic_retry':False}
COUNTS={'removeElements':1,'setNode':1,'addNodes':1,'addElementsByType':1,'rebuildNodeCache':1,
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
 if (c.get('schema')!='962-apex1613790-head-application/v1' or c.get('native_execution_authorized') is not True
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
 if (domain.get('schema')!='962-exact-apex1613790-old28-new44-domain-result/v1' or domain.get('status')!='same_compact_oriented_local_domain'
     or any(domain.get(k) is not True for k in ['exact_old_pair_embedding','exact_candidate_pair_embedding','local_domain_equivalence_proved','bound_inputs_unchanged','exact_common16_coordinate_words','exact_identical_oriented28_boundary','exact_signed_volume_identity'])
     or domain.get('pair_failures')!={'old':0,'candidate':0}
     or (domain.get('old_complete_unordered_pairs'),domain.get('candidate_complete_unordered_pairs'),domain.get('complete_unordered_pairs'),domain.get('plane_triples_enumerated'))!=(378,946,1324,74144)
     or domain.get('source_sha256')!=FIXED_INPUTS[DOMAIN_SOURCE] or domain.get('contract_sha256')!=FIXED_INPUTS[DOMAIN_ACTUAL]
     or domain.get('source_candidate_report_sha256')!=WORKER_SHA or domain.get('source_candidate_arrays_sha256')!=ARRAYS_SHA
     or domain.get('source_candidate_independent_peer_sha256')!=FIXED_INPUTS[LOCAL_PEER]
     or domain.get('qualification')!=QUALIFICATION or domain.get('native_optimizer_or_meshwrite_calls')!=0 or domain.get('coordinates_changed') is not False
     or peer.get('schema')!='962-apex1613790-domain-independent-stopped-saved-peer/v1' or peer.get('decision')!='CLEAR_COMPLETED_EXACT_LOCAL_DOMAIN_SAVED_ASSOCIATIONS_ONLY'
     or peer.get('report',{}).get('sha256')!=FIXED_INPUTS[DOMAIN] or peer.get('blockers')!=[]):
  raise ValueError('Completed current old28/new44 domain report and independent saved-association peer required')
 for name in [WORKER,ARRAYS,LOCAL_PEER,OBSERVATION,SHELL]:
  if domain['input_hashes'].get(name)!=FIXED_INPUTS[name]:raise ValueError('Current domain source/input association differs')
 expected_map={str(tag):i+1 for i,tag in enumerate(shell['local_to_global_node_tags'])};expected_map[str(APEX)]=17
 if domain.get('original_global_to_comparison_node_tags')!=expected_map:raise ValueError('Exact original28 comparison mapping required')
 expected_faces=sorted(min(tuple(face[i:]+face[:i]) for i in range(3)) for face in [row['local_node_tags'] for row in shell['oriented_triangle_rows']])
 for name,cells,count,internal in [('old',{row['tetrahedron_tag']:row['node_tags'] for row in observation['native_ordered_cell_rows']},378,42),('candidate',dict(zip(a['tetra_tags'],a['tetra_node_tags'])),946,74)]:
  data=domain[name];rows=domain['pair_results'][name]
  if (data['cell_count']!=len(cells) or data['internal_face_pairs']!=internal or data.get('all_exact_positive') is not True
      or [tuple(face) for face in data['oriented_boundary']]!=expected_faces
      or len(rows)!=count or [tuple(row['tetrahedron_tags']) for row in rows]!=list(combinations(sorted(cells),2))
      or any(row.get('intersection_equals_tagged_shared_simplex') is not True or row.get('plane_triples_enumerated')!=56 or row.get('illegal_intersection_vertices')!=0 or row.get('all_illegal_rational_witnesses')!=[] for row in rows)):
   raise ValueError('Complete current pair-result coverage/common shell required; predicates are not rerun')
 acceptance=json.loads((ROOT/DOMAIN_ACCEPT).read_text())
 if (acceptance.get('decision')!='ACCEPT_RELATIVE_LOCAL_OCCUPIED_DOMAIN_ONLY' or acceptance.get('accepted_relative_local_domain') is not True
     or acceptance['report']['sha256']!=FIXED_INPUTS[DOMAIN] or acceptance['peer']['sha256']!=FIXED_INPUTS[DOMAIN_PEER]
     or domain.get('source_candidate_root_acceptance_sha256')!=FIXED_INPUTS[LOCAL_ACCEPT]
     or any(r.get('upstream_census_launch_deviation_sha256')!=FIXED_INPUTS[DEVIATION] or r.get('declared_controller_command_conformant') is not False for r in [domain,peer,acceptance])):
  raise ValueError('Accepted relative-local domain and preserved d60 scope required')
 if domain['old']['exact_signed_volume_mm3']!=domain['candidate']['exact_signed_volume_mm3'] or domain['old']['exact_signed_volume_mm3']!={k:str(v) for k,v in shell['exact_enclosed_volume_mm3'].items()}:
  raise ValueError('Exact current common-shell volume proof differs')

def candidate_rows(worker,arrays,domain,peer,observation,shell):
 a=arrays['saved_reopen'];state=worker['saved_reopen']
 if (worker.get('status')!='completed_specific_cavity_Netgen_only'
     or any(worker.get(k) is not True for k in ['fixture_procedural_checks_passed','actual_SICN_gate_passed','saved_mesh_identity_exact','bound_inputs_unchanged','exact_boundary_bits_faces_classifications'])
     or any(worker.get(k) is not False for k in ['head_execution_authorized','stitching_authorized','native_head_application_authorized','engineering_accepted','physics_qualified','manufacturing_authorized'])
     or worker.get('full_tiny_arrays_sha256')!=ARRAYS_SHA or worker['after']!=state
     or (state['nodes'],state['tetrahedra'],state['referenced_interior_nodes'],state['unreferenced_nodes'])!=(20,44,4,0)
     or a['node_tags']!=sorted(set(a['node_tags'])) or a['tetra_tags']!=sorted(set(a['tetra_tags']))
     or {t for t,d in state['node_classifications'] if d==2}!=set(range(1,17))
     or {t for t,d in state['node_classifications'] if d==3}!=set(a['node_tags'])-set(range(1,17))
     or any([t,d,e]!=[t,(2 if t<=16 else 3),1] for t,d,e in state['node_entity_classifications'])
     or len(a['coordinates_mm'])!=20 or len(a['tetra_node_tags'])!=44 or arrays['after']!=a):
  raise ValueError('Exact completed current20-node44-cell raw saved Netgen state required')
 coordinates=[]
 for xyz in a['coordinates_mm']:
  if len(xyz)!=3 or any(type(v) is not float or not math.isfinite(v) for v in xyz):raise ValueError('Complete finite raw binary64 coordinate triples required')
  coordinates.append(list(xyz)) # Copy raw float words including signed zero, never Fraction roundtrips.
 if (any(len(row)!=4 or len(set(row))!=4 or any(type(t) is not int or t not in a['node_tags'] for t in row) for row in a['tetra_node_tags'])
     or set().union(*(set(row) for row in a['tetra_node_tags']))!=set(a['node_tags'])):raise ValueError('Full44 ordered TET4 membership and no orphan required')
 for name in ['SICN','Jacobian','native_volume_mm3']:
  values=a['native_qualities'][name]
  if len(values)!=44 or any(type(v) is not float or not math.isfinite(v) or v<=0 for v in values) or (name=='SICN' and any(v<.1 for v in values)):
   raise ValueError('Complete44 finite positive native metrics and unchanged SICN0.1 required')
 if [struct.pack('<3d',*row) for row in a['coordinates_mm']]!=[struct.pack('<3d',*row) for row in arrays['after']['coordinates_mm']]:raise ValueError('After/saved raw coordinate words differ')
 for saved,after in [(a['independent_signed_volume_mm3'],arrays['after']['independent_signed_volume_mm3']),*[(a['native_qualities'][n],arrays['after']['native_qualities'][n]) for n in ['SICN','Jacobian','native_volume_mm3']]]:
  if [struct.pack('<d',v) for v in saved]!=[struct.pack('<d',v) for v in after]:raise ValueError('After/saved raw metric words differ')
 require_domain(domain,peer,observation,shell,a)
 exact=domain['candidate']['quality_rows']
 if len(exact)!=44 or [row['tetrahedron_tag'] for row in exact]!=a['tetra_tags']:raise ValueError('Complete44 accepted exact candidate associations required')
 for proof,conn in zip(exact,a['tetra_node_tags']):
  det=proof['exact_determinant_mm3'];q=proof['exact_SICN_squared']
  if (proof['ordered_node_tags']!=conn or proof.get('exact_point1_gate_passed') is not True or Fraction(int(det['numerator']),int(det['denominator']))<=0 or Fraction(int(q['numerator']),int(q['denominator']))<Fraction(1,100)):
   raise ValueError('Every current exact candidate positive determinant and SICN squared gate required')
 return dict(zip(a['node_tags'],coordinates))


def edit_once(gmsh,case,counts):
 if len(case['old'])!=28 or not case['old']:raise ValueError('Complete nonempty28-cell removal required')
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
 if (observation.get('apex')!=APEX or len(mapping)!=16 or len(set(mapping))!=16 or APEX in mapping or len(old)!=28
     or any(len(row)!=4 or len(set(row))!=4 or APEX not in row for row in old.values())
     or context.get('status')!='complete_current129_partial_head_apex1613790_context_census' or context.get('complete_context_census') is not True
     or context.get('original_parent_MSH_sha256')!=FIXED_INPUTS[MESH]
     or context['complete_old_apex_incident_rows']!=[{'tetrahedron_tag':t,'node_tags':old[t]} for t in sorted(old)]
     or context['independently_derived_global_maxima']!={'node':NMAX,'element_all_dimensions':EMAX}
     or accepted.get('decision')!='ACCEPT_COMPLETED_READ_ONLY_CURRENT129_ONE_CASE_CONTEXT_ONLY' or accepted.get('accepted_read_only_context') is not True
     or accepted['peer']['sha256']!=FIXED_INPUTS[CONTEXT_PEER] or peer['source_report']['sha256']!=FIXED_INPUTS[CONTEXT]
     or closed['output_files']['readback-report.json']['sha256']!=FIXED_INPUTS[CONTEXT]
     or any(r.get('upstream_census_launch_deviation_sha256')!=FIXED_INPUTS[DEVIATION] or r.get('declared_controller_command_conformant') is not False for r in [observation,shell,context,accepted])):
  raise ValueError('Accepted fresh current129 original28-star context and preserved d60 required')
 original={r['node_tag']:r for r in observation['selected_node_rows']};native={r['node_tag']:r for r in context['selected17_native_node_rows']}
 classes={tag:[r['dimension'],r['entity_tag']] for tag,r in native.items()}
 if set(original)!=set(mapping+[APEX]) or set(native)!=set(original):raise ValueError('All17 original coordinate/class rows required')
 for tag,row in original.items():
  actual=native[tag]
  if (struct.pack('<3d',*row['coordinates_mm'])!=struct.pack('<3d',*actual['coordinates_mm']) or [float(v).hex() for v in row['coordinates_mm']]!=row['binary64_hex']
      or [float(v).hex() for v in actual['available_parametric_coordinates']]!=actual['parametric_binary64_hex']):raise ValueError('Every selected original word/available parameter row must join fresh context')
 if len(shell['vertex_rows'])!=16:raise ValueError('Complete16 fixed shell rows required')
 for local,row in enumerate(shell['vertex_rows'],1):
  tag=mapping[local-1]
  if (row['local_node_tag']!=local or row['source_global_node_tag']!=tag
      or struct.pack('<3d',*coordinates[local]).hex()!=row['binary64_little_endian_bytes_hex']
      or struct.pack('<3d',*coordinates[local])!=struct.pack('<3d',*original[tag]['coordinates_mm'])
      or classes[tag]!=([2,1] if row['original_source_boundary_node'] else [3,1])):raise ValueError('All13 source-boundary and3 source-interior shell identities must stay exact')
 if sum(r['original_source_boundary_node'] for r in shell['vertex_rows'])!=13 or classes[APEX]!=[3,1]:raise ValueError('Exact13/3 shell and volume apex classes required')
 expected={tuple(sorted(r['source_global_node_tags'])):r for r in shell['oriented_triangle_rows']};faces=context['all28_selected_shell_face_records']
 if len(faces)!=28 or {tuple(r['shell_face_key']) for r in faces}!=set(expected):raise ValueError('Every accepted selected shell face required')
 for face in faces:
  source=expected[tuple(face['shell_face_key'])]
  owners=face['owners'];inside=[r for r in owners if r['removed_star_owner']];outside=[r for r in owners if not r['removed_star_owner']]
  if (len(inside)!=1 or len(outside)>1 or inside[0]['tetrahedron_tag']!=source['source_owner_tetrahedron_tag']
      or inside[0]['node_tags']!=old[inside[0]['tetrahedron_tag']] or any((r['dimension'],r['entity_tag'])!=(3,1) for r in owners)):
   raise ValueError('Exact native volume1 old/outside owner associations required')
 interior=sorted(t for t,d in candidate['saved_reopen']['node_classifications'] if d==3)
 row=dict(apex=APEX,NV=16,N=20,K=28,M=44,I=4,candidate_interior_node_tags=interior,old_tetrahedron_tags=sorted(old))
 case=allocate_case(row,shell,arrays['saved_reopen'],NMAX,EMAX)
 case.update(old=old,nmax=NMAX,emax=EMAX,classes=classes,apices=[APEX],apex_parameters=list(native[APEX]['available_parametric_coordinates']),
  expected_counts={'nodes':1097222,'TET4':3621771,'interior':225491},expected_maxima={'node':NMAX+3,'element_all_dimensions':EMAX+16})
 if len(case['fresh_nodes'])!=3 or len(case['replacement'])!=44:raise ValueError('Only three fresh nodes and16 fresh TET slots permitted')
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
  if [int(dim),int(entity)]!=expected or [float(v).hex() for v in param]!=next(r['parametric_binary64_hex'] for r in context['selected17_native_node_rows'] if r['node_tag']==tag):raise ValueError('Selected original classification/parametric association changed')
  index=int(np.searchsorted(nt,tag));want=case['proposed'][tag] if after else next(r['coordinates_mm'] for r in context['selected17_native_node_rows'] if r['node_tag']==tag)
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
 proof=core.partial_after_proof(worker,receipt,closed,metadata);core.require_after_match(first,proof,129)
 if (metadata['MSH_sha256']!=FIXED_INPUTS[MESH] or metadata['partial_report_sha256']!=FIXED_INPUTS[ORIGINAL_WORKER]
     or metadata['partial_contract_sha256']!=FIXED_INPUTS['work/962-engineering/head-star-current204-combined-application-001/frozen-contract.json']
     or proof['array_sha256s']!=context['full_array_sha256s'] or proof['classifications']!=context['full_native_classifications']
     or proof['source_boundary_identity']!=context['current_source_boundary_identity'] or proof['quality']!=context['retained_current_quality_and_global_incidence']['quality']
     or (proof['total_mesh_nodes'],proof['tetrahedra'],proof['tetra_referenced_interior_nodes'],proof['unreferenced_mesh_nodes'])!=(1097219,3621755,225488,0)):
  raise ValueError('Single stopped current partial.after/saved, fresh129 census and current context required')
 for key,value in proof['array_sha256s'].items():
  if first[key]!=value:raise ValueError('Current census full tagged-array association differs')
 return proof


def valid_positive_volume(audit):
 return all(row['nonpositive_count']==0 for row in audit['quality'].values()) and audit['volume_relative_error']<=1e-6


def main():
 c=json.loads((OUT/'frozen-contract.json').read_text());require_contract(c)
 if {p.name for p in OUT.iterdir()}!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:raise ValueError('Exactly fresh three-file materialization plus native.log required')
 report=dict(schema='962-apex1613790-head-application-result/v1',status='running',stage='imports',procedural_checks_passed=False,
  actual_whole_head_SICN_gate_passed=False,expected_whole_head_positive_poor_count_not_observed=127,
  expected_count_is_not_acceptance=True,native_operation_counts={k:0 for k in COUNTS},call_counts_are_attempts=True,
  original_parent_MSH_sha256=FIXED_INPUTS[MESH],local_candidate_report_sha256=FIXED_INPUTS[WORKER],local_candidate_arrays_sha256=FIXED_INPUTS[ARRAYS],current_local_domain_report_sha256=FIXED_INPUTS[DOMAIN],current_local_domain_peer_sha256=FIXED_INPUTS[DOMAIN_PEER],context_sha256=FIXED_INPUTS[CONTEXT],
  upstream_census_launch_deviation_sha256=FIXED_INPUTS[DEVIATION],declared_controller_command_conformant=False,
  retained_original_parameter_scope='Derived from full verified native before arrays excluding only apex1613790; added nodes never enter retained reference.',
  original_local_domain_equivalence_is_separate=True,global_embedding_or_containment_proved=False,
  stronger_Mesh2_criterion_passed=False,engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
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
  if case['outside_reference']!={k:context['future_preservation_references'][k] for k in case['outside_reference']}:raise ValueError('Exact one-apex28-cell before masks differ from accepted context')
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
  if any(len(v)!=44 or not np.isfinite(v).all() or np.any(v<=0) for v in local_metrics.values()) or np.any(local_metrics['SICN']<.1):raise ValueError('Every actual replacement cell must freshly pass unchanged local SICN/positivity gate')
  report.update(after=after,after_preservation=after_snapshot,replacement44_native_metrics={k:v.tolist() for k,v in local_metrics.items()},actual_replacement44_SICN_gate_passed=True)
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
