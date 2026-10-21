"""HELD read-only current127 apex1613031 parent context; no candidate or geometry writes."""
from pathlib import Path
from types import SimpleNamespace
import ast, hashlib, json, math, platform, struct, sys, time

ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
OUTPUT='work/962-engineering/current127-apex1613031-head-context-001'
MESH='work/962-engineering/apex1613790-head-application-001/head-volume.msh'
MSH_SHA='8b16732d63cc69e48af113f6b618cc6378aaf121dbe1c63920dd6dd5eab8d07a'
WORKER='work/962-engineering/apex1613790-head-application-001/readback-report.json'
RECEIPT='work/962-engineering/apex1613790-head-application-001/execution-receipt.json'
FIRST='work/962-engineering/head-star-current127-full-stars-002/readback-report.json'
OBS='work/962-engineering/direct-sicn-apex1613031-cavity-study-001/saved-star-observation.json'
SHELL='work/962-engineering/direct-sicn-apex1613031-cavity-study-001/local-shell-input-001.json'
MESH_HELPER='twins/962-cylinder-head-f0/source/mesh_head.py'
CLASS_HELPER='work/962-engineering/head-star-current127-full-stars-prep-001/reader.py'
FIRST_CONTRACT='work/962-engineering/head-star-current127-full-stars-002/frozen-contract.json'
FIRST_ACTUAL='work/962-engineering/head-star-current127-full-stars-execution-prep-002/actual-contract.json'
CLOSED='work/962-engineering/apex1613790-head-application-root-execution-001/closed-result.json'
CENSUS_PEER='work/962-engineering/head-star-current127-full-stars-result-peer-001/review.json'
CENSUS_BINDINGS='work/962-engineering/head-star-current127-full-stars-result-peer-001/bindings.json'
SCREEN='work/962-engineering/direct-sicn-apex1613031-cavity-study-001/fixed-shell-tight-face-screen-001.json'
EXTRACT_RECEIPT='work/962-engineering/direct-sicn-apex1613031-cavity-study-001/receipt.json'
EXTRACT_CLOSED='work/962-engineering/direct-sicn-apex1613031-cavity-extract-root-execution-001/closed.json'
EXTRACT_PEER='work/962-engineering/direct-sicn-apex1613031-cavity-extract-result-peer-001/review.json'
CENSUS_ACCEPT='work/962-engineering/head-star-current127-full-stars-root-execution-001/result-peer-acceptance.json'
DEVIATION='work/962-engineering/head-star-current129-full-stars-root-execution-001/launch-deviation-001.json'
FIXED_INPUTS={'twins/962-cylinder-head-f0/source/mesh_head.py': '69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5', 'work/962-engineering/apex1613031-domain-equivalence-001/report.json': '6e12be8b4be563c49ebf0dd06ecf9d69b8fcb338d8cd777303899de509e610d9', 'work/962-engineering/apex1613031-domain-equivalence-result-peer-001/bindings.json': '7c86ae0026c221ed92af3729e85d0a40fc8c069f845c4ce5de9f23e224d29893', 'work/962-engineering/apex1613031-domain-equivalence-result-peer-001/review.json': '431e33c21d3364d43b9036177575cf95f6551aba99f673c069f6ef11c7632079', 'work/962-engineering/apex1613031-domain-equivalence-root-execution-001/result-peer-acceptance.json': '53df7322ea94a9388d896978be4f50abeb3bb5bf65ae8338ad530836982afa13', 'work/962-engineering/apex1613790-head-application-001/execution-receipt.json': '28bb0647a28de19e2413c0066468946ac5eee77e4b2e24a8b5f570ca184150fa', 'work/962-engineering/apex1613790-head-application-001/frozen-contract.json': 'd016fb42f6363995739193521db416741ff8609ef0ca12c22b3dc7e8fdfce272', 'work/962-engineering/apex1613790-head-application-001/head-volume.msh': '8b16732d63cc69e48af113f6b618cc6378aaf121dbe1c63920dd6dd5eab8d07a', 'work/962-engineering/apex1613790-head-application-001/native.log': 'be91c1696a3304d503e61582ad3ea0019c38c58184763cc6b33585e8d6a13baa', 'work/962-engineering/apex1613790-head-application-001/readback-report.json': 'bb1266ede7b8fd41f282a04c2363ba0eb684a94b6272956895bb7a30a09ffad0', 'work/962-engineering/apex1613790-head-application-001/reader.py': '0e3db83e33b1dec8b49e42401b313735c7c5fecfcd17cee5268f5ccc7a797a90', 'work/962-engineering/apex1613790-head-application-001/run_readback.py': '5ab38b53e4019506772cc429b46699ac0e217141c87a0a043718d8123ecb159c', 'work/962-engineering/apex1613790-head-application-root-execution-001/closed-result.json': 'e6951a0c920f88dda87efce797c111b1da83bb81f33cc2cd2c8acb900867504f', 'work/962-engineering/apex1613790-head-application-root-execution-001/result-peer-acceptance.json': 'e4bdec1ed7926231190f21a0b9986f47363bbbcf41daec2948e884459fef051c', 'work/962-engineering/apex1613790-head-application-root-execution-001/result-review.json': '0b23a7741967708062cce3f2eeea36740facb1d9ebd5ba7c3d47156b82a1cc52', 'work/962-engineering/current129-apex1613790-head-context-prep-001/held-contract.json': '01ff9e8d0365c19f3a509364ef3bd1646fede36f74de6e96bddf468a4a71aff5', 'work/962-engineering/current129-apex1613790-head-context-prep-001/reader.py': 'beafd637f8f7065bf4a40f777d970245d5ffdb5d7f8ca11fd6357c905b52ff14', 'work/962-engineering/current129-apex1613790-head-context-prep-001/selfcheck.py': 'e1d6dd129361b8d41e068ac6d56095902953986559fed663fe6cf76331322ec0', 'work/962-engineering/direct-sicn-apex1474426-head-context-prep-001/reader.py': '4640bc7c306f3016674a16a49734975bbaa96752075fc42deddb0a5fc2dabddb', 'work/962-engineering/direct-sicn-apex1613031-cavity-extract-prep-001/extract_shell.py': 'a223996f23975912bdfb03590af5550fe2f92fbaf6a1b1b58fb488f2508cffbe', 'work/962-engineering/direct-sicn-apex1613031-cavity-extract-prep-001/held-contract.json': '2dff48e0abf11acd82929489e287a010d0f2d1854f15bf2f38c7264b3223a8ba', 'work/962-engineering/direct-sicn-apex1613031-cavity-extract-result-peer-001/bindings.json': '828ce82491ed11d4566c91a0e28529d5fd7d4b597a18dea340f02946f6f75109', 'work/962-engineering/direct-sicn-apex1613031-cavity-extract-result-peer-001/review.json': 'a49de0ebf1915641e613b2ec7cc456c87876bbbdfd3452919551a889850a5cef', 'work/962-engineering/direct-sicn-apex1613031-cavity-extract-root-execution-001/closed.json': 'efc92338d42f459cf6c4b8e079cba74251f3f5966b7ebf19c33281dd0b795bc1', 'work/962-engineering/direct-sicn-apex1613031-cavity-extract-root-execution-001/own-review.json': '581a56cca01279de9ad44345434ed1129250a150d82de8b1423ae42f76c855f4', 'work/962-engineering/direct-sicn-apex1613031-cavity-extract-root-execution-001/result-peer-acceptance.json': '18a4c51a085cb70ec28e2eaade18f621c7f450a22eba2f4102956cb9c6910e74', 'work/962-engineering/direct-sicn-apex1613031-cavity-study-001/fixed-shell-tight-face-screen-001.json': '998208d59c5067ea60e62d2cb00d22b914118e0edd8fd1ab5866ebbcd8c6570e', 'work/962-engineering/direct-sicn-apex1613031-cavity-study-001/local-shell-input-001.json': '6529ffc5a5ca738c4bfe3041d858f2d40cc50efc6ee0e1dc5bcc626fd720d92d', 'work/962-engineering/direct-sicn-apex1613031-cavity-study-001/receipt.json': '7b5fad28cdc8529e1bbbbc179d2d24b4b96bbab6771ae435ede82e251f977707', 'work/962-engineering/direct-sicn-apex1613031-cavity-study-001/saved-star-observation.json': '89689ac5ce5f12c8922be4cbe45e36565f60eed080633aaffa79539c8e12c8d3', 'work/962-engineering/direct-sicn-cube-prep-001/held-contract.json': 'db6def5bf8909387b6ba4be4dc68769360dd396eca55e35b88718b6ff558e5cd', 'work/962-engineering/fixed-shell-generation-apex1613790-runtime-origin-001/closed-result.json': '5af4f4182a39648008de2672d6874a3b202e091c77281940fd5976fab1ef7398', 'work/962-engineering/head-star-current127-full-stars-002/execution-receipt.json': '47ce1dd32a343875a58180ae94363f55db1cfe4a78db689ac1e0ffd786e75274', 'work/962-engineering/head-star-current127-full-stars-002/frozen-contract.json': '54ad12959a10bb153afec2f2541bec2d22ec3f6e22ee0302c581062265c8fc95', 'work/962-engineering/head-star-current127-full-stars-002/readback-report.json': '34e3e29a23cedeb155485156cb40b4e92b6d0017eefd852f30383927eaaa7ef7', 'work/962-engineering/head-star-current127-full-stars-execution-prep-002/actual-contract.json': '54ad12959a10bb153afec2f2541bec2d22ec3f6e22ee0302c581062265c8fc95', 'work/962-engineering/head-star-current127-full-stars-execution-prep-002/index.json': 'baed07f0752f043ac76883f9d9e70f73cba02945f76287b80b81364787c6a53e', 'work/962-engineering/head-star-current127-full-stars-prep-001/reader.py': '11ad364b54b6b8f264f1727027659351ab38c9144b4c98c64e5265203fcb8a63', 'work/962-engineering/head-star-current127-full-stars-result-peer-001/bindings.json': '968353193fa36fb96ec9dc85b4268ad3d37f011b19acff745c0a250dcf4fc2ac', 'work/962-engineering/head-star-current127-full-stars-result-peer-001/review.json': 'e3f53c5b7280138296e4ffd8399149a61b9ecaf3bf796e4f780c74806a20b68b', 'work/962-engineering/head-star-current127-full-stars-root-execution-001/closed-result.json': '34529d377e1e8aa9a858214aec6ed6e568cbee3c1bde39f504d06dfac604ee9c', 'work/962-engineering/head-star-current127-full-stars-root-execution-001/result-peer-acceptance.json': 'bac2ff58db7e1f33556e8460e23d35cdd0cb7089c64afa6921ac7640b1bf0444', 'work/962-engineering/head-star-current127-full-stars-root-execution-001/result-review.json': 'c0c368ab44e7c73a3286b5e47ade87cc63b4f870e8bc96ac3accdd5afbaaf4e8', 'work/962-engineering/head-star-current129-full-stars-root-execution-001/launch-deviation-001.json': 'd60fff297c6c45dc92e117262e36ffde36e2169d53fcd32ce2b79fabde5eebc3', 'work/962-engineering/head-star-current204-union-context-prep-002/reader.py': 'c852a8a536a0ef2c58a37132fb51e42e525403d1f519375cc04a9860bfe53b29'}
FACES=((0,2,1),(0,1,3),(1,2,3),(2,0,3));CHUNK=100000;APEX=1613031;BOUNDARY=871731
RUNTIME={'python':'3.10.11','numpy':'2.0.2','gmsh':'4.15.2','machine':'arm64'}
NUMPY_SHA='c09e25b58f6b2f8e2cb3c158168f902d447f8171e5ea6513c0aca41ecbda7c2b'
FORBIDDEN=['optimization_authorized','mesh_write_authorized','generation_authorized','head_edit_authorized',
 'head_execution_authorized','stitching_authorized','engineering_accepted','physics_qualified','manufacturing_authorized']

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024**2),b''):h.update(block)
 return h.hexdigest()

def canonical(face):
 return min(tuple(face[i:]+face[:i]) for i in range(3))

def json_sha(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def validate_interface(expected,owners,triangles):
 """Complete selected-face records, not a global incidence/embedding proof."""
 answer=[]
 if set(owners)!=set(expected) or set(triangles)!=set(expected):raise ValueError('Every selected face must be retained')
 for key,face in expected.items():
  rows=owners[key];old=[x for x in rows if x['removed_star_owner']];outside=[x for x in rows if not x['removed_star_owner']]
  if len(old)!=1 or len(outside)>1 or len(rows) not in (1,2):raise ValueError('Exactly one old owner and at most one outside owner required')
  if canonical(old[0]['oriented_face'])!=canonical(face):raise ValueError('Old owner winding differs from frozen outward shell')
  if outside:
   if canonical(outside[0]['oriented_face'])!=canonical(list(reversed(face))) or triangles[key]:
    raise ValueError('Interior selected face requires opposite outside owner and no exterior TRI')
  elif len(triangles[key])!=1 or canonical(triangles[key][0]['node_tags'])!=canonical(face):
   raise ValueError('One-owner selected face needs one exact oriented parent exterior TRI')
  answer.append({'shell_face_key':list(key),'oriented_shell_face':face,'owners':rows,
   'parent_exterior_TRI_rows':triangles[key],'interface_kind':'internal_with_outside_owner' if outside else 'parent_exterior'})
 return answer

def face_hits(np,rows,keys):
 """Exact uint64 unordered triples; NumPy search only, no coordinate predicate."""
 dtype=np.dtype([('a','<u8'),('b','<u8'),('c','<u8')])
 values=np.ascontiguousarray(np.sort(rows,axis=1),dtype='<u8').view(dtype).reshape(-1)
 wanted=np.ascontiguousarray(sorted(keys),dtype='<u8').reshape(-1,3).view(dtype).reshape(-1)
 positions=np.searchsorted(wanted,values);possible=np.flatnonzero(positions<len(wanted))
 return possible[wanted[positions[possible]]==values[possible]]

def require_inputs(c):
 if (c.get('schema')!='962-current127-apex1613031-head-context/v1' or c.get('native_execution_authorized') is not True
     or c.get('native_read_only_query_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or c.get('selected_runtime_review_complete') is not True or any(c.get(k) is not False for k in FORBIDDEN)
     or c.get('upstream_census_launch_deviation_sha256')!=FIXED_INPUTS[DEVIATION]
     or c.get('declared_controller_command_conformant') is not False or c.get('automatic_retry') is not False or c.get('output_directory')!=OUTPUT or ROOT/OUTPUT!=OUT
     or c.get('MSH_sha256')!=MSH_SHA or c.get('MSH_bytes')!=235786462):raise ValueError('Exact read-only context authority required')
 if any(c['input_hashes'].get(k)!=v for k,v in FIXED_INPUTS.items()):raise ValueError('Every consumed record/source/parent must be a direct fixed pin')
 for name,digest in c['input_hashes'].items():
  f=ROOT/name
  if Path(name).is_absolute() or f.is_symlink() or not f.resolve().is_relative_to(ROOT) or sha(f)!=digest:raise ValueError('Input drift: '+name)
 if len(c['external_runtime_hashes'])!=3:raise ValueError('Selected native3 identity map required')
 for name,digest in c['external_runtime_hashes'].items():
  if sha(name)!=digest:raise ValueError('Selected runtime drift')
 if (sha(OUT/'reader.py')!=c['reader_sha256'] or sha(OUT/'run_readback.py')!=c['runner_sha256']
     or sha(Path(sys.executable).resolve())!=c['runtime']['python_executable_sha256']):raise ValueError('Materialized source/interpreter changed')

def selected_functions(path,names,namespace):
 tree=ast.parse((ROOT/path).read_text());rows=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 if {n.name for n in rows}!=set(names):raise ValueError('Selected frozen helper definition absent')
 exec(compile(ast.Module(body=rows,type_ignores=[]),path,'exec'),namespace)

def current_after_proof(worker,receipt,closed,first,prior,peer,peer_bindings,acceptance,helpers):
 """Current partial.after==saved and descriptor-shaped accepted127 census; d60 stays false."""
 proof=helpers['partial_after_proof'](worker,receipt,closed,prior)
 report_record=peer_bindings.get('outputs',{}).get('readback-report.json',{})
 contract_record=peer_bindings.get('outputs',{}).get('frozen-contract.json',{})
 actual_record=peer_bindings.get('selected_control_records',{}).get('actual',{})
 if (prior['MSH_sha256']!=MSH_SHA or prior['MSH_bytes']!=235786462
     or prior['partial_report_sha256']!=FIXED_INPUTS[WORKER] or prior['expected_positive_poor_total']!=127
     or first.get('status')!='direct_saved_file_readback_completed' or first.get('bound_inputs_unchanged') is not True
     or first.get('single_partial_replacement_saved_proof')!={'report_sha256':FIXED_INPUTS[WORKER],'field':'after','after_equals_saved_reopen':True,'independent_prior_reader_alias_used':False,'old210_bins_reused':False}
     or any(first.get(k)!=v for k,v in proof['array_sha256s'].items())
     or first['direct_fresh_classifications']!=proof['classifications']
     or peer.get('schema')!='962-current127-census-independent-stopped-saved-review/v1'
     or peer.get('decision')!='CLEAR_COMPLETED_READ_ONLY_CENSUS_SAVED_ASSOCIATIONS_ONLY'
     or peer.get('blockers')!=[] or peer.get('checked',{}).get('d60_false_conformance_preserved') is not True
     or any(peer.get(k) is not False for k in ['engineering_accepted','head_edit_authorized','head_PDE_authorized','physics_qualified','material_qualified','process_calibrated','manufacturing_authorized','automatic_retry'])
     or peer.get('bindings',{}).get('path')!=CENSUS_BINDINGS or peer['bindings'].get('sha256')!=FIXED_INPUTS[CENSUS_BINDINGS]
     or peer_bindings.get('schema')!='962-current127-census-saved-result-bindings/v1'
     or report_record.get('path')!=FIRST or report_record.get('sha256')!=FIXED_INPUTS[FIRST]
     or contract_record.get('path')!=FIRST_CONTRACT or contract_record.get('sha256')!=FIXED_INPUTS[FIRST_CONTRACT]
     or actual_record.get('path')!=FIRST_ACTUAL or actual_record.get('sha256')!=FIXED_INPUTS[FIRST_ACTUAL]
     or peer_bindings.get('source_proof',{}).get('path')!=WORKER or peer_bindings['source_proof'].get('sha256')!=FIXED_INPUTS[WORKER]
     or acceptance.get('schema')!='962-current127-census-root-stopped-peer-acceptance/v1'
     or acceptance.get('decision')!='ACCEPT_COMPLETED_READ_ONLY_CENSUS_SAVED_ASSOCIATIONS_ONLY'
     or acceptance.get('peer',{}).get('path')!=CENSUS_PEER or acceptance['peer'].get('sha256')!=FIXED_INPUTS[CENSUS_PEER]
     or acceptance.get('bindings')!=peer['bindings'] or acceptance.get('report')!=report_record
     or acceptance.get('upstream_d60_command_conformance') is not False
     or acceptance.get('positive_poor')!=127 or acceptance.get('nodes')!=1097222 or acceptance.get('TET4')!=3621771
     or any(acceptance.get(k) is not False for k in ['whole_head_quality_accepted','stronger_Mesh2_criterion_passed','geometry_repair_feasibility_proved','head_PDE_authorized','physics_qualified','material_qualified','process_calibrated','manufacturing_authorized','automatic_retry'])):
  raise ValueError('Current partial-after/saved127 census descriptor proof with historical d60 false required')
 helpers['require_after_match'](first,proof,127)
 return proof

def selection_records(observation,shell):
 """Specific original14/10/9 map and native owner/corner identity; no candidate."""
 cells=observation['native_ordered_cell_rows'];points=observation['selected_node_rows'];mapping=shell['local_to_global_node_tags']
 old={row['tetrahedron_tag']:row['node_tags'] for row in cells};old_points={row['node_tag']:row for row in points}
 if (observation.get('apex')!=APEX or shell.get('excluded_source_apex_tag')!=APEX
     or observation.get('source_census_sha256')!=FIXED_INPUTS[FIRST] or observation.get('original_parent_MSH_sha256')!=MSH_SHA
     or any(record.get('upstream_census_launch_deviation_sha256')!=FIXED_INPUTS[DEVIATION]
            or record.get('declared_controller_command_conformant') is not False for record in [observation,shell])
     or shell.get('apex_not_in_shell_input') is not True or shell.get('necessary_face_quality_passed') is not True
     or shell.get('generation_input_rejected_by_necessary_face_quality') is not False
     or len(cells)!=14 or len(old)!=14 or len(points)!=10 or len(old_points)!=10
     or any(len(row)!=4 or len(set(row))!=4 or APEX not in row for row in old.values())
     or len(mapping)!=9 or any(type(t) is not int or t<=0 for t in mapping) or mapping!=sorted(set(mapping))
     or APEX in mapping or set(old_points)!=set(mapping+[APEX])
     or shell['global_to_local_node_tags']!={str(t):i+1 for i,t in enumerate(mapping)}):
  raise ValueError('Specific current original14/10 and9shell identity required')
 source_boundary=shell['original_source_classifications']['boundary_global_node_tags']
 other=shell['original_source_classifications']['other_interior_global_node_tags']
 if (len(source_boundary)!=5 or len(other)!=4 or source_boundary!=sorted(set(source_boundary))
     or other!=sorted(set(other)) or set(source_boundary)&set(other) or sorted(source_boundary+other)!=mapping
     or source_boundary!=[t for t in mapping if t<=BOUNDARY] or any(t<=BOUNDARY for t in other)):
  raise ValueError('Original5 boundary and4 other dim3 shell tags required')
 vertices=shell['vertex_rows']
 if len(vertices)!=9:raise ValueError('All9 original coordinate rows required')
 for local,(tag,row) in enumerate(zip(mapping,vertices),1):
  point=old_points[tag];xyz=row['coordinates_mm']
  if (row['local_node_tag']!=local or row['source_global_node_tag']!=tag or len(xyz)!=3
      or any(type(x) not in (int,float) or not math.isfinite(x) for x in xyz)
      or [float(x).hex() for x in xyz]!=row['binary64_hex'] or row['binary64_hex']!=point['binary64_hex']
      or struct.pack('<3d',*xyz)!=struct.pack('<3d',*point['coordinates_mm'])
      or struct.pack('<3d',*xyz).hex()!=row['binary64_little_endian_bytes_hex']
      or row['original_source_boundary_node'] is not (tag in source_boundary)):
   raise ValueError('Original shell coordinate words/classification flags differ')
 rows=shell['oriented_triangle_rows'];expected_faces={}
 if len(rows)!=14:raise ValueError('Complete14 shell faces required')
 for row in rows:
  local=row['local_node_tags'];owner=row['source_owner_tetrahedron_tag'];pattern=row['native_corner_indices']
  if len(local)!=3 or any(type(t) is not int or t<1 or t>9 for t in local) or len(set(local))!=3:
   raise ValueError('Exact local1..9 shell triangles required')
  face=[mapping[t-1] for t in local];key=tuple(sorted(face))
  if (key in expected_faces or face!=row['source_global_node_tags'] or owner not in old
      or tuple(pattern) not in FACES or [old[owner][i] for i in pattern]!=face
      or next(cell['native_array_index'] for cell in cells if cell['tetrahedron_tag']==owner)!=row['source_native_array_index']):
   raise ValueError('Exact unique native shell owner/corner/order required')
  expected_faces[key]=face
 return old,old_points,mapping,expected_faces,set(source_boundary)

def parameter_projection(inventory):
 return [{k:row[k] for k in ['dimension','entity_tag','count','parameter_width','node_tags_u64_sha256','available_parameter_words_f64_sha256']} for row in inventory]

def main():
 start=time.monotonic();c=json.loads((OUT/'frozen-contract.json').read_text());require_inputs(c)
 if {p.name for p in OUT.iterdir()}!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:raise ValueError('Fresh materialized output only')
 report={'status':'running','stage':'runtime_and_original_proof','complete_context_census':False,
  'native_generate_optimize_meshwrite_solve_calls':0,'quality_recomputed':False,**{k:False for k in FORBIDDEN}}
 def save():
  with (OUT/'readback-report.json').open('w') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
 save();initialized=False
 try:
  import numpy as np
  import gmsh
  observed={'python':platform.python_version(),'numpy':np.__version__,'gmsh':gmsh.__version__,'machine':platform.machine()}
  actual={'python':sha(Path(sys.executable).resolve()),'gmsh_module':sha(gmsh.__file__),'gmsh_library':sha(gmsh.lib._name)}
  if (observed!=RUNTIME or actual!=c['runtime_sha256s'] or Path(np.__file__).resolve()!=Path(c['numpy_init']).resolve()
      or sha(np.__file__)!=NUMPY_SHA):raise ValueError('Loaded selected runtime/NumPy origin or bytes changed')
  arrsha=lambda a:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
  ns={'np':np};selected_functions(MESH_HELPER,['volume_arrays'],ns)
  selected_functions(CLASS_HELPER,['classifications','partial_after_proof','require_after_match'],ns)
  core=SimpleNamespace(np=np,array_sha=arrsha)
  worker=json.loads((ROOT/WORKER).read_text());receipt=json.loads((ROOT/RECEIPT).read_text());first=json.loads((ROOT/FIRST).read_text())
  prior=json.loads((ROOT/FIRST_CONTRACT).read_text());closed=json.loads((ROOT/CLOSED).read_text());peer=json.loads((ROOT/CENSUS_PEER).read_text())
  peer_bindings=json.loads((ROOT/CENSUS_BINDINGS).read_text());acceptance=json.loads((ROOT/CENSUS_ACCEPT).read_text())
  proof=current_after_proof(worker,receipt,closed,first,prior,peer,peer_bindings,acceptance,ns);expected=proof['array_sha256s']
  observation=json.loads((ROOT/OBS).read_text());shell=json.loads((ROOT/SHELL).read_text())
  old,old_points,mapping,expected_faces,original_boundary=selection_records(observation,shell)
  gmsh.initialize([],readConfigFiles=False,run=False);initialized=True
  gmsh.option.setNumber('General.NumThreads',2);gmsh.option.setNumber('Mesh.MaxNumThreads3D',2)
  report['stage']='opening_original_parent';save();gmsh.open(str(ROOT/MESH))
  xyz,_,et,en=ns['volume_arrays'](gmsh);tags=np.sort(np.asarray(gmsh.model.mesh.getNodes()[0],dtype='<u8'))
  order=np.argsort(et);et=np.asarray(et,dtype='<u8')[order];en=np.asarray(en,dtype='<u8')[order]
  if not np.isfinite(xyz).all() or len(np.unique(tags))!=len(tags) or len(np.unique(et))!=len(et):raise ValueError('Unique full finite arrays required')
  actual_arrays=dict(zip(['sorted_coordinates_sha256','sorted_node_tags_sha256','sorted_tetra_tags_sha256','tagged_tetra_connectivity_sha256'],map(arrsha,[xyz,tags,et,en])))
  if actual_arrays!=expected or (len(tags),len(et))!=(1097222,3621771):raise ValueError('Opened complete parent arrays differ from original worker.after')
  classes=ns['classifications'](core,gmsh,tags,BOUNDARY)
  if classes!=proof['classifications']:raise ValueError('Complete native classifications differ from original worker.after')
  boundary_tags=np.arange(1,BOUNDARY+1,dtype='<u8');boundary_ix=np.searchsorted(tags,boundary_tags)
  if np.any(boundary_ix>=len(tags)) or not np.array_equal(tags[boundary_ix],boundary_tags):raise ValueError('Complete original source boundary tags required')
  source_boundary_identity={'source_boundary_nodes':BOUNDARY,'source_node_tags_sha256':arrsha(boundary_tags),
   'source_coordinate_bits_sha256':arrsha(xyz[boundary_ix]),
   'classification_dimensions_sha256':classes['boundary_node_classification_dimensions_sha256'],
   'classification_entity_tags_sha256':classes['boundary_node_classification_entity_tags_sha256'],
   'no_curve_or_surface_periodic_mapping':classes['no_curve_or_surface_periodic_mapping'],
   'periodic_entities_checked':classes['periodic_entities_checked']}
  if source_boundary_identity!=proof['source_boundary_identity']:raise ValueError('Current original source boundary identity differs')
  if not np.array_equal(np.unique(en),tags):raise ValueError('Complete parent reference/orphan association changed')
  report['stage']='complete_selected_face_owner_scan';save()
  owners={key:[] for key in expected_faces};triangles={key:[] for key in expected_faces};apex_rows={}
  for startrow in range(0,len(et),CHUNK):
   conn=en[startrow:startrow+CHUNK]
   for j in np.flatnonzero(np.any(conn==APEX,axis=1)):
    apex_rows[int(et[startrow+j])]=conn[j].tolist()
   for pattern in FACES:
    rows=conn[:,pattern]
    for j in face_hits(np,rows,expected_faces):
     index=startrow+int(j);tag=int(et[index]);face=rows[j].tolist();key=tuple(sorted(face))
     owners[key].append({'tetrahedron_tag':tag,'node_tags':en[index].tolist(),'oriented_face':face,
      'native_corner_indices':list(pattern),'removed_star_owner':tag in old})
  if apex_rows!=old:raise ValueError('Complete original apex incidence/order differs; outside apex use refused')
  entities=sorted((int(d),int(t)) for d,t in gmsh.model.getEntities());entity_rows=[];lower=[];periodic=[];max_element=int(et.max());all_lower_tags=[]
  parameter_inventory=[];node_seen=np.zeros(len(tags),dtype=np.uint8)
  for dim,entity in entities:
   boundary=[list(map(int,row)) for row in gmsh.model.getBoundary([(dim,entity)],combined=False,oriented=True,recursive=False)] if dim else []
   entity_rows.append({'dimension':dim,'entity_tag':entity,'oriented_immediate_boundary':boundary,'name':gmsh.model.getEntityName(dim,entity)})
   owned,owned_xyz,owned_param=gmsh.model.mesh.getNodes(dim,entity,False,True)
   owned=np.asarray(owned,dtype='<u8');ix=np.argsort(owned);owned=owned[ix];where=np.searchsorted(tags,owned)
   owned_xyz=np.asarray(owned_xyz,dtype='<f8').reshape(-1,3)[ix];parameter_width=dim if len(owned_param) else 0
   if (len(np.unique(owned))!=len(owned) or np.any(where>=len(tags)) or not np.array_equal(tags[where],owned)
       or np.any(node_seen[where]) or owned_xyz.tobytes()!=np.asarray(xyz[where],dtype='<f8').tobytes()
       or len(owned_param) not in (0,len(owned)*dim)):
    raise ValueError('Complete entity ownership/coordinate/available-parametric association changed')
   node_seen[where]=1
   params=np.asarray(owned_param,dtype='<f8').reshape(len(owned),parameter_width)[ix] if parameter_width else np.empty((len(owned),0),dtype='<f8')
   if not np.isfinite(params).all():raise ValueError('Finite full original parameter rows required')
   parameter_inventory.append({'dimension':dim,'entity_tag':entity,'count':len(owned),'parameter_width':parameter_width,
    'node_tags_u64_sha256':arrsha(owned),'coordinate_words_f64_sha256':arrsha(owned_xyz),'available_parameter_words_f64_sha256':arrsha(params)})
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
    if len(tt):max_element=max(max_element,int(tt.max()));all_lower_tags.append(tt)
    lower.append({'dimension':dim,'entity_tag':entity,'element_type':kind,'nodes_per_element':width,'count':len(tt),
     'minimum_tag':int(tt.min()) if len(tt) else None,'maximum_tag':int(tt.max()) if len(tt) else None,
     'element_tags_u64_sha256':arrsha(tt),'ordered_connectivity_u64_sha256':arrsha(rows)})
    if dim==2 and kind==2:
     for begin in range(0,len(tt),CHUNK):
      for j in face_hits(np,rows[begin:begin+CHUNK],expected_faces):
       index=begin+int(j);face=rows[index].tolist()
       triangles[tuple(sorted(face))].append({'dimension':dim,'entity_tag':entity,'element_type':kind,'element_tag':int(tt[index]),'node_tags':face})
  if not np.all(node_seen==1):raise ValueError('Every original node entity/parameter row must be captured once')
  lower.sort(key=lambda row:(row['dimension'],row['entity_tag'],row['element_type']))
  all_et=np.concatenate([et,*all_lower_tags])
  if len(np.unique(all_et))!=len(all_et):raise ValueError('All-dimensional element tag collision refused')
  actual_max={'node':int(tags.max()),'element_all_dimensions':max_element}
  if (int(gmsh.model.mesh.getMaxNodeTag()),int(gmsh.model.mesh.getMaxElementTag()))!=(actual_max['node'],max_element):
   raise ValueError('Native maxima differ from complete independent all-dimensional arrays')
  if sum(x['count'] for x in lower if x['dimension']==2 and x['element_type']==2)!=1743878:
   raise ValueError('Complete parent exterior TRI count differs from original surface authority')
  joined=validate_interface(expected_faces,owners,triangles);outside_rows={};all_owner_tags=set()
  for record in joined:
   for row in record['owners']:
    tag=row['tetrahedron_tag'];kind,nodes,dim,entity=gmsh.model.mesh.getElement(tag)
    if int(kind)!=4 or list(map(int,nodes))!=row['node_tags'] or int(dim)!=3:raise ValueError('Selected native row/owner join changed')
    row['dimension']=int(dim);row['entity_tag']=int(entity);all_owner_tags.add(tag)
    if not row['removed_star_owner']:outside_rows[tag]=row['node_tags']
  selected_nodes=[]
  for tag in sorted(old_points):
   coordinates,param,dim,entity=gmsh.model.mesh.getNode(tag);coordinates=list(map(float,coordinates));param=list(map(float,param))
   index=int(np.searchsorted(tags,tag));want=old_points[tag]
   if (index>=len(tags) or int(tags[index])!=tag or struct.pack('<3d',*coordinates)!=struct.pack('<3d',*xyz[index])
       or struct.pack('<3d',*coordinates)!=struct.pack('<3d',*want['coordinates_mm'])
       or [x.hex() for x in coordinates]!=want['binary64_hex'] or not all(math.isfinite(x) for x in param)
       or int(dim)!=(2 if tag in original_boundary else 3) or (int(dim),int(entity)) not in entities):
    raise ValueError('Selected10 coordinate/class/entity/param join failed')
   selected_nodes.append({'node_tag':tag,'dimension':int(dim),'entity_tag':int(entity),'coordinates_mm':coordinates,
    'binary64_hex':[x.hex() for x in coordinates],'available_parametric_coordinates':param,'parametric_binary64_hex':[x.hex() for x in param]})
  selected_classes={row['node_tag']:[row['dimension'],row['entity_tag']] for row in selected_nodes}
  for face in joined:
   for triangle in face['parent_exterior_TRI_rows']:
    if any(selected_classes[t]!=[2,triangle['entity_tag']] for t in triangle['node_tags']):
     raise ValueError('Exterior interface TRI has inconsistent selected surface-node classification')
  outside_tags=sorted({t for row in outside_rows.values() for t in row});outside_coordinates=[]
  for tag in outside_tags:
   index=int(np.searchsorted(tags,tag));row=list(map(float,xyz[index]))
   if int(tags[index])!=tag:raise ValueError('Outside owner references absent node')
   outside_coordinates.append({'node_tag':tag,'coordinates_mm':row,'binary64_hex':[x.hex() for x in row]})
  groups=[]
  for dim,tag in sorted(gmsh.model.getPhysicalGroups()):
   groups.append({'dimension':int(dim),'physical_tag':int(tag),'name':gmsh.model.getPhysicalName(dim,tag),
    'entity_tags':sorted(map(int,gmsh.model.getEntitiesForPhysicalGroup(dim,tag)))})
  node_mask=tags!=APEX;cell_mask=~np.isin(et,np.asarray(sorted(old),dtype='<u8'))
  preservation={'outside_node_tags_u64_sha256':arrsha(tags[node_mask]),'outside_coordinate_words_f64_sha256':arrsha(xyz[node_mask]),
   'outside_tetra_tags_u64_sha256':arrsha(et[cell_mask]),'outside_ordered_tetra_connectivity_u64_sha256':arrsha(en[cell_mask]),
   'outside_nodes':int(np.count_nonzero(node_mask)),'outside_TET4':int(np.count_nonzero(cell_mask)),
   'full_lower_dimensional_inventory_sha256':json_sha(lower),'full_entity_metadata_sha256':json_sha(entity_rows),
   'full_physical_group_metadata_sha256':json_sha(groups),'full_periodic_metadata_sha256':json_sha(periodic),
   'full_classification_proof_sha256':json_sha(classes),'full_original_entity_parametric_metadata_sha256':json_sha(parameter_projection(parameter_inventory))}
  metadata={'full_lower_dimensional_inventory':json_sha(lower),'full_entity_metadata':json_sha(entity_rows),
   'full_physical_group_metadata':json_sha(groups),'full_periodic_metadata':json_sha(periodic)}
  if metadata!=worker['after_preservation']['metadata_sha256s']:raise ValueError('Current partial lower/entity/physical/periodic metadata differs')
  require_inputs(c)
  if sha(np.__file__)!=NUMPY_SHA:raise ValueError('Selected NumPy bytes changed after query')
  report.update(status='complete_current127_partial_head_apex1613031_context_census',stage='completed',complete_context_census=True,
   original_parent_MSH_sha256=MSH_SHA,original_parent_MSH_bytes=235786462,full_array_sha256s=actual_arrays,
   full_native_classifications=classes,full_node_count=len(tags),full_TET4_count=len(et),
   complete_old_apex_incident_rows=[{'tetrahedron_tag':t,'node_tags':old[t]} for t in sorted(old)],
   all14_selected_shell_face_records=joined,complete_outside_owner_rows=[{'tetrahedron_tag':t,'node_tags':outside_rows[t]} for t in sorted(outside_rows)],
   complete_outside_owner_coordinate_rows=outside_coordinates,selected10_native_node_rows=selected_nodes,
   independently_derived_global_maxima=actual_max,full_lower_dimensional_inventory=lower,
   full_entity_metadata=entity_rows,full_physical_group_metadata=groups,full_periodic_metadata=periodic,full_entity_node_parameter_inventory=parameter_inventory,
   future_preservation_references=preservation,runtime=observed,runtime_sha256s=actual,bound_inputs_unchanged=True,
   current_source_boundary_identity=source_boundary_identity,
   upstream_census_launch_deviation_sha256=FIXED_INPUTS[DEVIATION],declared_controller_command_conformant=False,
   outside_mask_scope={'excluded_apex_tags':[APEX],'excluded_original_TET4_tags':sorted(old),'subset':'This one original14-cell1613031 star only; no other case or union masks transferred.'},
   parameter_reference_scope='All1097222 current original tags exactly once. The prior bb126 retained1097218-tag projection is a different subset and is not compared to this full inventory. Future application must scan retained original tags excluding only1613031; no hash subtraction or transferred masks.',
   retained_current_quality_and_global_incidence={'quality':proof['quality'],'actual_tetra_boundary':proof['actual_tetra_boundary'],'internal_tetra_face_orientation':proof['internal_tetra_face_orientation']},
   quality_and_global_incidence='Retained current partial.after/saved only; no native qualities or global incidence recomputed.',
   candidate_or_MSH_written=False,selected_geometry_JSON_exported=True,connected_interface_ownership_only=True,
   global_embedding_containment_or_after_edit_preservation_proved=False,readback_wall_seconds=time.monotonic()-start)
  save();return 0
 except BaseException as error:
  report.update(status='refused_or_interrupted_context_census',complete_context_census=False,error=str(error));save();raise
 finally:
  if initialized:gmsh.finalize()

if __name__=='__main__':raise SystemExit(main())
