"""HELD read-only current204 selected116 union parent-context census; no candidate or geometry writes."""
from pathlib import Path
from types import SimpleNamespace
import ast, hashlib, json, math, platform, struct, sys, time

ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
OUTPUT='work/962-engineering/head-star-current204-union-context-001'
MSH_SHA='4c6543f8e905c2771f9f313e5e131d06d081928deafb8dd5b43b18d9d2c73a3f'
MESH='work/962-engineering/apex1474426-head-application-001/head-volume.msh'
WORKER='work/962-engineering/apex1474426-head-application-001/readback-report.json'
RECEIPT='work/962-engineering/apex1474426-head-application-001/execution-receipt.json'
FIRST='work/962-engineering/head-star-current204-full-stars-001/readback-report.json'
CLASS_HELPER='work/962-engineering/head-star-current204-full-stars-prep-001/reader.py'
FIRST_CONTRACT='work/962-engineering/head-star-current204-full-stars-001/frozen-contract.json'
CLOSED='work/962-engineering/apex1474426-head-application-root-execution-001/closed-result.json'
CENSUS_PEER='work/962-engineering/head-star-current204-full-stars-result-peer-001/review.json'
BATCH='work/962-engineering/head-star-current204-batch-shells-001/report.json'
MANIFEST='work/962-engineering/head-star-current204-local-stages-prep-001/case-manifest.json'
MESH_HELPER='twins/962-cylinder-head-f0/source/mesh_head.py'
FIXED_INPUTS={'work/962-engineering/apex1474426-head-application-001/head-volume.msh': '4c6543f8e905c2771f9f313e5e131d06d081928deafb8dd5b43b18d9d2c73a3f', 'work/962-engineering/apex1474426-head-application-001/readback-report.json': 'c39dce34ee4b7b3cdf5e470041ecc1316642dbc547b63047cd300d8ffc23d70d', 'work/962-engineering/apex1474426-head-application-001/execution-receipt.json': 'f78151937f4085a6611a209595402a9daa934be906f4f1e132ba2b913ea6f652', 'work/962-engineering/head-star-current204-full-stars-001/readback-report.json': '0124cdb9dd65a1d2434e0ff44e3d390257ad32bbc9c068c9c330532f46d03239', 'work/962-engineering/head-star-current204-full-stars-prep-001/reader.py': 'eb9b5cfeab50c9c74c87c3995b0ce97ebbc365581a2cc552f26fb73b96bd0a1f', 'work/962-engineering/head-star-current204-full-stars-001/frozen-contract.json': 'a613681c5d653a4bd68e31604d50f14716bfc003d7eb2eff2f7149a89ecba7d2', 'work/962-engineering/apex1474426-head-application-root-execution-001/closed-result.json': '0b2c61d3f5418394aca86733bdcda859739d7ab1e9d2fbafec9dbd3f1b8be250', 'work/962-engineering/head-star-current204-full-stars-result-peer-001/review.json': '239e8c4e154872a75aa1b5dd23599f344f6e857778b80c87461f9492dc655a01', 'work/962-engineering/head-star-current204-batch-shells-001/report.json': '4f9fc0354918a907083006484d534c34c3b2621dfcc83b00cc4a4b731f009e86', 'work/962-engineering/head-star-current204-local-stages-prep-001/case-manifest.json': '3a558ede04cbc52c59e401befb36b8983ebd9b7f57d4266de0bea38fb1a963c5', 'work/962-engineering/head-star-current204-full-stars-001/execution-receipt.json': 'f6cb320e261eb33f501aa36497f990213c5d856defa9b286f8bda25dab5f5d0c', 'work/962-engineering/head-star-current204-full-stars-root-execution-001/closed-result.json': '67ce69c8c2a35d8b56763550043c18a3db28d963a1cee5675c41e9f8f1765456', 'work/962-engineering/head-star-current204-full-stars-root-execution-001/result-review.json': 'af50c15ef52da35a5c265cbfa7bff10c3aa99694b0d86acad121a8bc2b2f68af', 'work/962-engineering/head-star-current204-full-stars-root-execution-001/result-peer-acceptance.json': 'f145fe76eab27efe97bcd64c5fe217f74bcaa12a2ae095ff9dac4ee9c3c20f26', 'work/962-engineering/head-star-current204-batch-shells-001/receipt.json': '78e215c5c85f01ca614e44e4e443fd4181086f63e2edc5d5aee81fbef77dbedb', 'work/962-engineering/head-star-current204-batch-shells-execution-prep-001/actual-contract.json': 'daf7c31a9cb24bdad32bf6ddf281d82dbd1a805b0d5a2a5bac159a32c6cb9d06', 'work/962-engineering/head-star-current204-batch-shells-root-execution-001/closed-result.json': '67d9b2763fcd5ac887eddca79010d8a21dc6365b19f56224512acbaf7a3150e2', 'work/962-engineering/head-star-current204-batch-shells-root-execution-001/result-review.json': '5a80128a5e4dd3ea685449c1124fd1fad4c07a3bb1c586f9f80a2e26caacf913', 'work/962-engineering/head-star-current204-batch-shells-root-execution-001/result-peer-acceptance.json': '47a98aad883748178b7b25a1a5957ca01c0780eb0274f778567e6c5fb22fe538', 'work/962-engineering/head-star-current204-batch-shells-result-peer-001/review.json': '3fd325b3e4e18b942bda26d9292127d1dc1c2b8ecc5841d11257dc61884030da', 'work/962-engineering/head-star-current204-local-stages-prep-001/held-contract.json': 'ddbeaae99f3a51297b7be6f16701985a9fd9d0b721e00113a564f07be4a4f6fe', 'work/962-engineering/head-star-current204-local-stages-source-peer-001/review.json': '88c1aa3923ea9eaf3d53e980fd4d3bb9fb9a9487be9c7101f4e7467a4101e7ac', 'work/962-engineering/head-star-current204-finite-batch-plan-001/NOTE.md': 'b5a4d575324e0ea268bd2ccb5ff853fa8ada83a4417f9c1cba17c3acd7e1a02f', 'twins/962-cylinder-head-f0/source/mesh_head.py': '69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5'}
FACES=((0,2,1),(0,1,3),(1,2,3),(2,0,3));CHUNK=100000;BOUNDARY=871731
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
 if (c.get('schema')!='962-current204-selected116-union-head-context/v1' or c.get('native_execution_authorized') is not True
     or c.get('native_read_only_query_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or c.get('selected_runtime_review_complete') is not True or any(c.get(k) is not False for k in FORBIDDEN)
     or c.get('automatic_retry') is not False or c.get('output_directory')!=OUTPUT or ROOT/OUTPUT!=OUT
     or c.get('MSH_sha256')!=MSH_SHA or c.get('MSH_bytes')!=235744782):raise ValueError('Exact read-only context authority required')
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

def current_after_proof(worker,receipt,closed,first,prior,peer,helpers):
 """One current partial.after==saved proof; no optimizer aliases or quality query."""
 proof=helpers['partial_after_proof'](worker,receipt,closed,prior)
 if (prior['MSH_sha256']!=MSH_SHA or prior['MSH_bytes']!=235744782
     or prior['partial_report_sha256']!=FIXED_INPUTS[WORKER] or prior['expected_positive_poor_total']!=204
     or first.get('status')!='direct_saved_file_readback_completed' or first.get('bound_inputs_unchanged') is not True
     or first.get('single_partial_replacement_saved_proof')!={'report_sha256':FIXED_INPUTS[WORKER],'field':'after','after_equals_saved_reopen':True,'independent_prior_reader_alias_used':False,'old210_bins_reused':False}
     or any(first.get(k)!=v for k,v in proof['array_sha256s'].items())
     or first['direct_fresh_classifications']!=proof['classifications']
     or peer.get('decision')!='CLEAR_COMPLETED_READ_ONLY_CENSUS_WHOLE_HEAD_QUALITY_REJECTED'
     or peer['records']['worker_report']['sha256']!=FIXED_INPUTS[FIRST] or peer['blockers']!=[] or peer['engineering_accepted'] is not False):
  raise ValueError('Current partial-after/saved census proof required')
 helpers['require_after_match'](first,proof,204)
 return proof

def one_case_records(observation,shell,case):
 APEX=case['apex'];NV=case['shell_nodes'];NF=case['shell_faces'];K=case['old_tetrahedra'];NB=case['original_boundary_shell_nodes']
 """One selected complete star and exact native owner/corner/word association; no candidate."""
 cells=observation['native_ordered_cell_rows'];points=observation['selected_node_rows'];mapping=shell['local_to_global_node_tags']
 old={row['tetrahedron_tag']:row['node_tags'] for row in cells};old_points={row['node_tag']:row for row in points}
 if (observation.get('apex')!=APEX or shell.get('excluded_source_apex_tag')!=APEX
     or shell.get('apex_not_in_shell_input') is not True or shell.get('necessary_face_quality_passed') is not True
     or shell.get('generation_input_rejected_by_necessary_face_quality') is not False
     or len(cells)!=K or len(old)!=K or len(points)!=NV+1 or len(old_points)!=NV+1
     or any(len(row)!=4 or len(set(row))!=4 or APEX not in row for row in old.values())
     or len(mapping)!=NV or any(type(t) is not int or t<=0 for t in mapping) or mapping!=sorted(set(mapping))
     or APEX in mapping or set(old_points)!=set(mapping+[APEX])
     or shell['global_to_local_node_tags']!={str(t):i+1 for i,t in enumerate(mapping)}):
  raise ValueError('Exact selected complete-star/shell identity required')
 source_boundary=shell['original_source_classifications']['boundary_global_node_tags']
 other=shell['original_source_classifications']['other_interior_global_node_tags']
 if (len(source_boundary)!=NB or len(other)!=NV-NB or source_boundary!=sorted(set(source_boundary))
     or other!=sorted(set(other)) or set(source_boundary)&set(other) or sorted(source_boundary+other)!=mapping
     or source_boundary!=[t for t in mapping if t<=BOUNDARY] or any(t<=BOUNDARY for t in other)):
  raise ValueError('Original per-case boundary and other-interior shell tags required')
 vertices=shell['vertex_rows']
 if len(vertices)!=NV:raise ValueError('All original shell coordinate rows required')
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
 if len(rows)!=NF:raise ValueError('Every selected case shell face required')
 for row in rows:
  local=row['local_node_tags'];owner=row['source_owner_tetrahedron_tag'];pattern=row['native_corner_indices']
  if len(local)!=3 or any(type(t) is not int or t<1 or t>NV for t in local) or len(set(local))!=3:
   raise ValueError('Exact per-case local shell triangles required')
  face=[mapping[t-1] for t in local];key=tuple(sorted(face))
  if (key in expected_faces or face!=row['source_global_node_tags'] or owner not in old
      or tuple(pattern) not in FACES or [old[owner][i] for i in pattern]!=face
      or next(cell['native_array_index'] for cell in cells if cell['tetrahedron_tag']==owner)!=row['source_native_array_index']):
   raise ValueError('Exact unique native shell owner/corner/order required')
  expected_faces[key]=face
 return old,old_points,mapping,expected_faces,set(source_boundary)


def encoded(value):
 return (json.dumps(value,indent=2,allow_nan=False)+'\n').encode()

def observation_node_matches(census,observed):
 extra='binary64_little_endian_bytes_hex'
 if set(observed)!=set(census)|{extra}:return False
 return (encoded({k:observed[k] for k in census})==encoded(census)
  and observed[extra]==struct.pack('<3d',*census['coordinates_mm']).hex()
  and observed[extra]==struct.pack('<3d',*observed['coordinates_mm']).hex())

def merge_case_records(cases,records,census_cells,census_nodes):
 old={};old_points={};faces={};boundary=set();shell_tags=set();by_apex={};summaries=[];used=set()
 for case in cases:
  apex=case['apex'];record=records[apex]
  if (record.get('eligible') is not True or set(record['all_vertex_tags'])&used
      or hashlib.sha256(encoded(record)).hexdigest()!=case['source_record_sha256']):
   raise ValueError('Selected whole vertex sets must remain disjoint and exact')
  used.update(record['all_vertex_tags']);observation=record['observation'];shell=record['shell']
  for value,key in [(shell,'shell_serialized_sha256'),(observation,'observation_serialized_sha256'),(record['necessary_face_screen'],'screen_serialized_sha256')]:
   if hashlib.sha256(encoded(value)).hexdigest()!=case[key]:raise ValueError('Exact selected embedded body identity changed')
  complete=[r for r in census_cells if apex in r['node_tags']]
  if (complete!=observation['native_ordered_cell_rows'] or len(complete)!=case['old_tetrahedra']
      or [r['tetrahedron_tag'] for r in complete]!=case['old_tetrahedron_tags']
      or sorted({t for r in complete for t in r['node_tags']})!=case['old_vertex_tags']
      or any(not observation_node_matches(census_nodes[r['node_tag']],r) for r in observation['selected_node_rows'])):
   raise ValueError('Every current complete incident cell including good/shared context must match')
  a,b,mapping,expected,original_boundary=one_case_records(observation,shell,case)
  if set(old)&set(a) or set(old_points)&set(b) or set(faces)&set(expected):raise ValueError('Selected cell, vertex or face collision refused')
  old.update(a);old_points.update(b);faces.update(expected);boundary.update(original_boundary);shell_tags.update(mapping);by_apex[apex]=a
  summaries.append({'apex':apex,'case_key':case['case_key'],'case_record_sha256':case['source_record_sha256'],
   'old_tetrahedra':case['old_tetrahedra'],'shell_nodes':case['shell_nodes'],'shell_faces':case['shell_faces'],
   'original_boundary_shell_nodes':case['original_boundary_shell_nodes'],'old_cell_tags':sorted(a),
   'shell_node_tags':mapping,'shell_face_keys':[list(k) for k in sorted(expected)]})
 return old,old_points,sorted(shell_tags),faces,boundary,by_apex,summaries

def selection_records(manifest,batch,first):
 cases=manifest['cases_in_increasing_apex_order'];tags=[r['apex'] for r in cases];star=first['complete_seed_star_census']
 if (manifest.get('schema')!='962-current204-finite-local-stage-manifest/v1' or manifest['selected_count']!=116
     or len(tags)!=116 or tags!=sorted(set(tags)) or set(tags)!=set(batch['selected_apex_tags'])
     or manifest['source_batch_report_sha256']!=FIXED_INPUTS[BATCH] or batch['source_census_sha256']!=FIXED_INPUTS[FIRST]
     or manifest['source_parent_MSH_sha256']!=MSH_SHA or batch['source_MSH_sha256']!=MSH_SHA
     or batch['source_current_positive_poor_cells']!=204 or star['movable_count']!=154
     or not set(tags)<=set(star['movable_node_tags']) or star['complete_incident_tetrahedron_count']!=5267):
  raise ValueError('Exact current154-seed census and frozen selected116 manifest required')
 records={r['apex']:r for r in batch['all_candidate_star_records']};nodes={r['node_tag']:r for r in star['unique_incident_nodes']}
 answer=merge_case_records(cases,records,star['complete_incident_tetrahedra'],nodes)
 if (len(answer[0]),len(answer[1]),len(answer[2]),len(answer[3]),len(answer[5]))!=(4164,2430,2314,4164,116):
  raise ValueError('Exact selected union old-cells/vertices/shells/faces/apices required')
 return answer

def mask_exclusions(apices,old,tags,element_tags):
 a=sorted(apices);e=sorted(old)
 if not a or len(a)!=len(set(a)) or not set(a)<=set(map(int,tags)) or not e or not set(e)<=set(map(int,element_tags)):
  raise ValueError('Every exact selected apex and old-cell exclusion must exist in the full arrays')
 return a,e

def parameter_projection(inventory):
 return [{k:row[k] for k in ['dimension','entity_tag','count','parameter_width','node_tags_u64_sha256','available_parameter_words_f64_sha256']} for row in inventory]

def validate_maxima(node_max,element_max,native_node_max,native_element_max):
 if any(type(v) is not int or v<=0 for v in [node_max,element_max,native_node_max,native_element_max]) or (node_max,element_max)!=(native_node_max,native_element_max):
  raise ValueError('Native maxima must equal independent complete all-dimensional arrays')
 return {'node':node_max,'element_all_dimensions':element_max}

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
  proof=current_after_proof(worker,receipt,closed,first,prior,peer,ns);expected=proof['array_sha256s']
  manifest=json.loads((ROOT/MANIFEST).read_text());batch=json.loads((ROOT/BATCH).read_text())
  old,old_points,mapping,expected_faces,original_boundary,by_apex,case_summaries=selection_records(manifest,batch,first)
  gmsh.initialize([],readConfigFiles=False,run=False);initialized=True
  gmsh.option.setNumber('General.NumThreads',2);gmsh.option.setNumber('Mesh.MaxNumThreads3D',2)
  report['stage']='opening_original_parent';save();gmsh.open(str(ROOT/MESH))
  xyz,_,et,en=ns['volume_arrays'](gmsh);tags=np.sort(np.asarray(gmsh.model.mesh.getNodes()[0],dtype='<u8'))
  order=np.argsort(et);et=np.asarray(et,dtype='<u8')[order];en=np.asarray(en,dtype='<u8')[order]
  if not np.isfinite(xyz).all() or len(np.unique(tags))!=len(tags) or len(np.unique(et))!=len(et):raise ValueError('Unique full finite arrays required')
  actual_arrays=dict(zip(['sorted_coordinates_sha256','sorted_node_tags_sha256','sorted_tetra_tags_sha256','tagged_tetra_connectivity_sha256'],map(arrsha,[xyz,tags,et,en])))
  if actual_arrays!=expected or (len(tags),len(et))!=(1097057,3620861):raise ValueError('Opened complete parent arrays differ from original worker.after')
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
  owners={key:[] for key in expected_faces};triangles={key:[] for key in expected_faces};apex_rows={apex:{} for apex in by_apex}
  for startrow in range(0,len(et),CHUNK):
   conn=en[startrow:startrow+CHUNK]
   for j in np.flatnonzero(np.any(np.isin(conn,np.asarray(sorted(by_apex),dtype='<u8')),axis=1)):
    row=conn[j].tolist();present=set(row)&set(by_apex)
    if len(present)!=1:raise ValueError('Selected apices unexpectedly share a current tetrahedron')
    apex_rows[next(iter(present))][int(et[startrow+j])]=row
   for pattern in FACES:
    rows=conn[:,pattern]
    for j in face_hits(np,rows,expected_faces):
     index=startrow+int(j);tag=int(et[index]);face=rows[j].tolist();key=tuple(sorted(face))
     owners[key].append({'tetrahedron_tag':tag,'node_tags':en[index].tolist(),'oriented_face':face,
      'native_corner_indices':list(pattern),'removed_star_owner':tag in old})
  if apex_rows!=by_apex:raise ValueError('Every selected apex complete incidence/order differs; omitted good/outside use refused')
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
  actual_max=validate_maxima(int(tags.max()),max_element,int(gmsh.model.mesh.getMaxNodeTag()),int(gmsh.model.mesh.getMaxElementTag()))
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
    raise ValueError('Selected union coordinate/class/entity/param join failed')
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
   if index>=len(tags) or int(tags[index])!=tag:raise ValueError('Outside owner references absent node')
   outside_coordinates.append({'node_tag':tag,'coordinates_mm':row,'binary64_hex':[x.hex() for x in row]})
  groups=[]
  for dim,tag in sorted(gmsh.model.getPhysicalGroups()):
   groups.append({'dimension':int(dim),'physical_tag':int(tag),'name':gmsh.model.getPhysicalName(dim,tag),
    'entity_tags':sorted(map(int,gmsh.model.getEntitiesForPhysicalGroup(dim,tag)))})
  excluded_nodes,excluded_cells=mask_exclusions(by_apex,old,tags,et)
  node_mask=~np.isin(tags,np.asarray(excluded_nodes,dtype='<u8'));cell_mask=~np.isin(et,np.asarray(excluded_cells,dtype='<u8'))
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
  report.update(status='complete_current204_selected116_union_parent_context_census',stage='completed',complete_context_census=True,
   original_parent_MSH_sha256=MSH_SHA,original_parent_MSH_bytes=235744782,full_array_sha256s=actual_arrays,
   full_native_classifications=classes,full_node_count=len(tags),full_TET4_count=len(et),
   selected_case_contexts=case_summaries,selected_apex_tags=sorted(by_apex),complete_old_selected_apex_incident_rows=[{'tetrahedron_tag':t,'node_tags':old[t]} for t in sorted(old)],
   all_selected_shell_face_records=joined,complete_outside_owner_rows=[{'tetrahedron_tag':t,'node_tags':outside_rows[t]} for t in sorted(outside_rows)],
   complete_outside_owner_coordinate_rows=outside_coordinates,selected_original_native_node_rows=selected_nodes,
   independently_derived_global_maxima=actual_max,full_lower_dimensional_inventory=lower,
   full_entity_metadata=entity_rows,full_physical_group_metadata=groups,full_periodic_metadata=periodic,full_entity_node_parameter_inventory=parameter_inventory,
   future_preservation_references=preservation,runtime=observed,runtime_sha256s=actual,bound_inputs_unchanged=True,
   current_source_boundary_identity=source_boundary_identity,
   retained_current_quality_and_global_incidence={'quality':proof['quality'],'actual_tetra_boundary':proof['actual_tetra_boundary'],'internal_tetra_face_orientation':proof['internal_tetra_face_orientation']},
   quality_and_global_incidence='Current204 partial.after/saved quality and whole-head face-incidence retained only; complete selected116 apex/face-owner lookup is freshly scanned.',
   candidate_or_MSH_written=False,selected_geometry_JSON_exported=True,connected_interface_ownership_only=True,
   global_embedding_containment_or_after_edit_preservation_proved=False,readback_wall_seconds=time.monotonic()-start)
  save();return 0
 except BaseException as error:
  report.update(status='refused_or_interrupted_context_census',complete_context_census=False,error=str(error));save();raise
 finally:
  if initialized:gmsh.finalize()

if __name__=='__main__':raise SystemExit(main())
