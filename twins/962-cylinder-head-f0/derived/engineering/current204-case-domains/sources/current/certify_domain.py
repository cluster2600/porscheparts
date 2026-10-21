"""HELD one fixed47 current204 case exact domain query; no native/head action."""
from pathlib import Path
from fractions import Fraction
from itertools import combinations
import hashlib,importlib.util,json,math,re,struct,sys,time
ROOT=Path(__file__).resolve().parents[3]
OUTPUT=CASE=CONTEXT_DATA=None
WORKER=ARRAYS=None
QUALIFICATION=dict(native_application_authorized=False,head_execution_authorized=False,stitching_authorized=False,
 engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False,material_qualified=False,process_calibrated=False)
HELPER='work/962-engineering/fixed-shell-coupled-embedding-prep-001/check_embedding.py'
MANIFEST='work/962-engineering/head-star-current204-case-domains-prep-002/case-manifest.json'
MANIFEST_SHA='0628df655f81a509a43d4b31e64e42f9285226e1653969f939dfa681d8c34cbd'
BATCH='work/962-engineering/head-star-current204-batch-shells-001/report.json'
CONTEXT='work/962-engineering/head-star-current204-union-context-001/readback-report.json'
PEER='work/962-engineering/head-star-current204-Netgen-result-peer-001/review.json'
ACCEPT='work/962-engineering/head-star-current204-Netgen-root-execution-001/result-peer-acceptance.json'
FIXED_INPUTS={'work/962-engineering/apex1474426-domain-equivalence-prep-001/certify_domain.py': 'daebceae4a6a0402fbbe3f19c3bff5006ac6d2674d43cd452b32a4c7aa6a20d6', 'work/962-engineering/fixed-shell-coupled-embedding-prep-001/check_embedding.py': '1b489cc8149f4b5db8f90c594e32fe4c09b5db00151df6b1cfc88362d1018134', 'work/962-engineering/domain-equivalence-prep-001/certify_domain.py': '0fe593d385e5a0ab4944528fa1b869ddf2c41c28d050576afe9be18213462296', 'work/962-engineering/head-star-current204-local-stages-prep-001/case-manifest.json': '3a558ede04cbc52c59e401befb36b8983ebd9b7f57d4266de0bea38fb1a963c5', 'work/962-engineering/head-star-current204-batch-shells-001/report.json': '4f9fc0354918a907083006484d534c34c3b2621dfcc83b00cc4a4b731f009e86', 'work/962-engineering/head-star-current204-Netgen-root-execution-001/closed-result.json': 'f53e8b905c1bab7872cc0b0ffcdbc58333c19575e6c8c71f8491886b89c00e87', 'work/962-engineering/head-star-current204-Netgen-root-execution-001/result-review.json': '5d8943639eea7b7e246e51714c09a2ab39e43c0cb19a5374218e65d7095dd9fc', 'work/962-engineering/head-star-current204-Netgen-root-execution-001/result-peer-acceptance.json': 'fc98600dfdf68e89ec78f442d4c8b32476ea829fe3697c0b2a1dfc95ce8d98ef', 'work/962-engineering/head-star-current204-Netgen-result-peer-001/review.json': '5ff930c217e28203526fbda3489c316ce6b4c307319538eba33e09bc88ebc1c3', 'work/962-engineering/head-star-current204-Netgen-result-peer-001/independent-saved-check.json': 'df313b87aac09062ce23864e733274b2a90f9a5d45c4c9dee3dc000500254347', 'work/962-engineering/head-star-current204-union-context-001/readback-report.json': 'ceeadffb9cd777044239e463729a06780a399664364bafc03453297ef061a83a', 'work/962-engineering/head-star-current204-union-context-root-execution-001/closed-result.json': 'fe7c90c00ca003714f91cf8c4169c054704aa1296c93a42d5f5467e64a67c2d3', 'work/962-engineering/head-star-current204-union-context-root-execution-001/result-review.json': 'b65ee788d3d33628cd7c760895cd491afce811ffec4bd6a40298afd8446054d3', 'work/962-engineering/head-star-current204-union-context-root-execution-001/result-peer-acceptance.json': 'ac7dd0ae7e9ad02fd710968c5431f7564d1c02d3ef52583f40f3ca32a8956915', 'work/962-engineering/head-star-current204-union-context-result-peer-001/review.json': 'b2bccc9eea641cdb00666062e9556e6639498512dd4aaf65551e5347519f5d69', 'work/962-engineering/apex1474426-head-application-001/readback-report.json': 'c39dce34ee4b7b3cdf5e470041ecc1316642dbc547b63047cd300d8ffc23d70d', 'work/962-engineering/head-star-current204-full-stars-001/readback-report.json': '0124cdb9dd65a1d2434e0ff44e3d390257ad32bbc9c068c9c330532f46d03239', 'work/962-engineering/head-star-current204-case-domain-reuse-plan-001/NOTE.md': '75c3059bcf59fb16120e4c10a8b3d36076869a01cd139d1dfd619ef550387e88'}
INPUTS={}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
FACES=((0,2,1),(0,1,3),(1,2,3),(2,0,3))


def cycle(face):
 return min(tuple(face[i:]+face[:i]) for i in range(3))


def complex_rows(helper,points,cells,expected_shell):
 if not cells or any(len(row)!=4 or len(set(row))!=4 or not set(row)<=set(points) for row in cells.values()):
  raise ValueError('Complete nondegenerate tagged tetrahedron rows required')
 if len({tuple(sorted(row)) for row in cells.values()})!=len(cells):raise ValueError('Duplicate cell refused')
 incidence={};quality=[];volume=Fraction(0)
 for tag,row in sorted(cells.items()):
  det,q2=helper.exact_quality([[float(x) for x in points[t]] for t in row])
  if det<=0 or q2 is None:raise ValueError('Every old/new stored tetrahedron must be exact-positive; old quality may be poor')
  volume+=det/6
  quality.append(dict(tetrahedron_tag=tag,ordered_node_tags=row,exact_determinant_mm3=helper.rational(det),
   exact_SICN_squared=helper.rational(q2),exact_point1_gate_passed=q2>=Fraction(1,100)))
  for pattern in FACES:
   face=[row[i] for i in pattern];incidence.setdefault(tuple(sorted(face)),[]).append(face)
 boundary=[];internal=0
 for faces in incidence.values():
  if len(faces)==1:boundary.append(cycle(faces[0]))
  elif len(faces)==2 and cycle(faces[0])==cycle(list(reversed(faces[1]))):internal+=1
  else:raise ValueError('Complete opposite internal-face cancellation required')
 if sorted(boundary)!=sorted(cycle(list(f)) for f in expected_shell):
  raise ValueError('Exact geometric oriented boundary rows differ from the frozen shell')
 return dict(cell_count=len(cells),internal_face_pairs=internal,oriented_boundary=[list(x) for x in sorted(boundary)],
  all_exact_positive=True,quality_rows=quality,exact_signed_volume_mm3=helper.rational(volume)),volume



def select_case(manifest,apex):
 if (manifest.get('schema')!='962-current204-fixed47-case-domain-manifest/v1' or manifest.get('selected_count')!=47
     or len(manifest['cases_in_accepted_order'])!=47 or type(apex) is not int):raise ValueError('Only fixed47 accepted cases exist')
 rows=manifest['cases_in_accepted_order'];tags=[r['apex'] for r in rows]
 if tags!=sorted(set(tags)) or tags!=manifest['accepted_apices'] or apex not in tags:raise ValueError('No rerank, backfill or unselected case')
 case=rows[tags.index(apex)];nv,nf,k,n,m,i=[case[x] for x in ['NV','NF','K','N','M','I']]
 if (any(type(x) is not int or x<=0 for x in [nv,nf,k,n,m,i]) or nv<4 or nf<4 or n!=nv+i or m<k
     or case['candidate_interior_node_tags']!=sorted(set(case['candidate_interior_node_tags']))
     or len(case['candidate_interior_node_tags'])!=i or any(type(t) is not int or t<=nv for t in case['candidate_interior_node_tags'])):
  raise ValueError('Saved dynamic counts and actual referenced dim3 tags required')
 op=k*(k-1)//2;np=m*(m-1)//2
 if (case['old_unordered_pairs']!=op or case['candidate_unordered_pairs']!=np or case['total_pairs']!=op+np
     or case['plane_triples']!=56*(op+np) or (4*k-nf)%2 or (4*m-nf)%2
     or case['original_internal_pairs']!=(4*k-nf)//2 or case['candidate_internal_pairs']!=(4*m-nf)//2):raise ValueError('Exact complete enumeration budgets required')
 return case


def configure(c):
 global CASE,OUTPUT,WORKER,ARRAYS,INPUTS,CONTEXT_DATA
 if sha(ROOT/MANIFEST)!=MANIFEST_SHA:raise ValueError('Fixed finite manifest changed')
 manifest=json.loads((ROOT/MANIFEST).read_text());CASE=select_case(manifest,c.get('case_apex'));OUTPUT=CASE['output_directory']
 if c.get('case_record_sha256')!=CASE['source_record_sha256']:raise ValueError('Same-case subrecord required')
 WORKER=CASE['records']['worker']['path'];ARRAYS=CASE['records']['arrays']['path']
 INPUTS={**FIXED_INPUTS,MANIFEST:MANIFEST_SHA,**{r['path']:r['sha256'] for r in CASE['records'].values()}}
 accept=json.loads((ROOT/ACCEPT).read_text());CONTEXT_DATA=json.loads((ROOT/CONTEXT).read_text())
 if (accept['local_quality_storage_pass_apices']!=manifest['accepted_apices'] or accept['peer_sha256']!=FIXED_INPUTS[PEER]
     or CONTEXT_DATA['status']!='complete_current204_selected116_union_parent_context_census' or CONTEXT_DATA['complete_context_census'] is not True
     or CONTEXT_DATA['original_parent_MSH_sha256']!=manifest['source_parent_MSH_identity_metadata_only']['sha256']
     or CONTEXT_DATA['full_array_sha256s']!=manifest['current_full_array_sha256s']):raise ValueError('Current accepted Netgen and116 superset context lineage required')
 parent=json.loads((ROOT/'work/962-engineering/apex1474426-head-application-001/readback-report.json').read_text())
 if (parent['mesh_sha256']!=manifest['source_parent_MSH_identity_metadata_only']['sha256'] or parent['after']!=parent['saved_reopen']
     or parent['saved_reopen']['array_sha256s']!=CONTEXT_DATA['full_array_sha256s']
     or parent['saved_reopen']['classifications']!=CONTEXT_DATA['full_native_classifications']
     or parent['saved_reopen']['source_boundary_identity']!=CONTEXT_DATA['current_source_boundary_identity']):raise ValueError('Exact current partial.after/saved array/class/source-boundary proof required; whole-head quality stays separate')


def case_record():
 batch=json.loads((ROOT/BATCH).read_text());record=next(r for r in batch['all_candidate_star_records'] if r['apex']==CASE['apex'])
 encoded=lambda x:(json.dumps(x,indent=2,allow_nan=False)+'\n').encode()
 for obj,key in [(record,'source_record_sha256'),(record['shell'],'shell_serialized_sha256'),(record['observation'],'observation_serialized_sha256')]:
  if hashlib.sha256(encoded(obj)).hexdigest()!=CASE[key]:raise ValueError('Exact original case/shell/observation body required')
 return record


def context_join(observation,shell):
 apex=CASE['apex'];context=CONTEXT_DATA
 cc=next((r for r in context['selected_case_contexts'] if r['apex']==apex),None)
 if (cc is None or cc['case_record_sha256']!=CASE['source_record_sha256'] or cc['old_cell_tags']!=CASE['old_tetrahedron_tags']
     or cc['shell_node_tags']!=shell['local_to_global_node_tags'] or cc['shell_nodes']!=CASE['NV'] or cc['shell_faces']!=CASE['NF']
     or cc['old_tetrahedra']!=CASE['K'] or cc['original_boundary_shell_nodes']!=CASE['NB']):raise ValueError('Same selected original context case required')
 old={r['tetrahedron_tag']:r['node_tags'] for r in observation['native_ordered_cell_rows']}
 actual={r['tetrahedron_tag']:r['node_tags'] for r in context['complete_old_selected_apex_incident_rows'] if apex in r['node_tags']}
 if actual!=old or sorted(old)!=CASE['old_tetrahedron_tags']:raise ValueError('Complete original apex incidence must join116 source context')
 native={r['node_tag']:r for r in context['selected_original_native_node_rows']};boundary=set(shell['original_source_classifications']['boundary_global_node_tags'])
 classes=shell['original_source_classifications'];observed=observation['original_source_classifications']
 global_keys=('boundary_global_node_tags','other_interior_global_node_tags')
 local_keys=('boundary_local_node_tags','other_interior_local_node_tags')
 if (len(boundary)!=CASE['NB'] or set(observed)!=set(global_keys) or set(classes)!=set(global_keys+local_keys)
     or any(classes[key]!=observed[key] for key in global_keys)):raise ValueError('True source global classification labels required')
 inverse={str(t):i+1 for i,t in enumerate(shell['local_to_global_node_tags'])}
 if (shell['global_to_local_node_tags']!=inverse
     or any(classes[local]!=[inverse[str(t)] for t in classes[global_]] for global_,local in zip(global_keys,local_keys))):
  raise ValueError('Shell local class labels must match the exact global inverse')
 for row in observation['selected_node_rows']:
  other=native.get(row['node_tag']);xyz=row['coordinates_mm']
  if (other is None or struct.pack('<3d',*xyz)!=struct.pack('<3d',*other['coordinates_mm'])
      or row['binary64_hex']!=other['binary64_hex'] or other['dimension']!=(2 if row['node_tag'] in boundary else 3)):
   raise ValueError('Every original raw word/class must join native context')
 faces={tuple(r['shell_face_key']):r for r in context['all_selected_shell_face_records']}
 for row in shell['oriented_triangle_rows']:
  expected=[shell['local_to_global_node_tags'][t-1] for t in row['local_node_tags']];hit=faces.get(tuple(sorted(expected)))
  if hit is None or cycle(expected)!=cycle(hit['oriented_shell_face']):raise ValueError('Every shell face must join accepted full owner/TRI scan')
  removed=[r for r in hit['owners'] if r['removed_star_owner']]
  if len(removed)!=1 or removed[0]['tetrahedron_tag'] not in old:raise ValueError('Same-case removed owner required')


def accepted_native_records(worker):
 data={k:json.loads((ROOT/r['path']).read_text()) for k,r in CASE['records'].items() if k not in ['worker','arrays']}
 closed=data['root_closed'];receipt=data['receipt'];actual=data['actual']
 if (closed['case_apex']!=CASE['apex'] or closed['returncode']!=0 or closed['root_stop_reason'] is not None or closed['root_error'] is not None
     or closed['actual_sha256']!=CASE['records']['actual']['sha256'] or receipt['returncode']!=0 or receipt['stop_reason'] is not None
     or receipt['fixture_report_sha256']!=CASE['records']['worker']['sha256'] or receipt['contract_sha256']!=CASE['records']['actual']['sha256']
     or actual['case_apex']!=CASE['apex'] or actual['case_record_sha256']!=CASE['source_record_sha256']
     or worker['case_apex']!=CASE['apex'] or worker['case_record_sha256']!=CASE['source_record_sha256']
     or worker['next_stage']!='domain' or worker['later_head_storage_compatible'] is not True
     or worker['mesh_sha256']!=CASE['mesh_identity_root_inventory']['sha256']
     or any(closed['output_files'][name]['sha256']!=CASE['records'][role]['sha256'] for role,name in [('worker','fixture-report.json'),('arrays','arrays.json'),('actual','frozen-contract.json'),('receipt','execution-receipt.json')])):
  raise ValueError('Exact accepted natural same-case Netgen records must join')


def original(observation,shell):
 if observation.get('apex')!=CASE['apex'] or len(observation['native_ordered_cell_rows'])!=CASE['K'] or len(observation['selected_node_rows'])!=CASE['NV']+1:
  raise ValueError('Exact frozen complete selected source star required')
 mapping={t:i+1 for i,t in enumerate(shell['local_to_global_node_tags'])};mapping[CASE['apex']]=CASE['NV']+1
 if len(mapping)!=CASE['NV']+1 or sorted(mapping)!=CASE['old_vertex_tags'] or shell['global_to_local_node_tags']!={str(t):i+1 for i,t in enumerate(shell['local_to_global_node_tags'])}:
  raise ValueError('Specific exact shell inverse mapping required')
 points={};words={}
 for row in observation['selected_node_rows']:
  tag=row['node_tag'];xyz=row['coordinates_mm']
  if tag not in mapping or len(xyz)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in xyz) or [float(x).hex() for x in xyz]!=row['binary64_hex']:
   raise ValueError('Exact source coordinate/hex association required')
  points[mapping[tag]]=tuple(Fraction.from_float(float(x)) for x in xyz);words[tag]=xyz
 if set(points)!=set(range(1,CASE['NV']+2)):raise ValueError('Every original coordinate row required')
 for row in shell['vertex_rows']:
  t=row['source_global_node_tag'];xyz=words[t]
  if mapping[t]!=row['local_node_tag'] or struct.pack('<3d',*xyz).hex()!=row['binary64_little_endian_bytes_hex']:
   raise ValueError('Every fixed source word must match the shell')
 cells={r['tetrahedron_tag']:[mapping[t] for t in r['node_tags']] for r in observation['native_ordered_cell_rows']}
 if len(cells)!=CASE['K'] or any(CASE['NV']+1 not in row for row in cells.values()):raise ValueError('Complete original cone rows required')
 return points,cells,mapping


def saved_candidate(worker,arrays,shell,peer):
 a=arrays['saved_reopen'];state=worker['saved_reopen'];quality=state['quality']['SICN']
 interior=sorted(r[0] for r in state['node_classifications'] if r[1]==3)
 if (interior!=CASE['candidate_interior_node_tags'] or set(a['node_tags'])!=set(range(1,CASE['NV']+1))|set(interior)
     or state['node_classifications']!=[[t,2 if t<=CASE['NV'] else 3] for t in a['node_tags']]
     or state['node_entity_classifications']!=[[t,2 if t<=CASE['NV'] else 3,1] for t in a['node_tags']]):raise ValueError('Actual referenced dim3 tags/classes required; no contiguous-interior or ancestry assumption')
 if (worker.get('status')!='completed_finite_selected_cavity_Netgen_only'
     or any(worker.get(k) is not True for k in ['fixture_procedural_checks_passed','actual_SICN_gate_passed','saved_mesh_identity_exact','bound_inputs_unchanged','geometry_flag_full_state_unchanged','exact_boundary_bits_faces_classifications'])
     or any(worker.get(k) is not False for k in ['head_execution_authorized','stitching_authorized','native_head_application_authorized','engineering_accepted','physics_qualified','manufacturing_authorized'])
     or worker.get('full_tiny_arrays_sha256')!=INPUTS[ARRAYS] or worker['after']!=state or arrays['after']!=a
     or (state.get('nodes'),state.get('tetrahedra'),state.get('referenced_interior_nodes'),state.get('unreferenced_nodes'))!=(CASE['N'],CASE['M'],CASE['I'],0)
     or (quality.get('count'),quality.get('below_point1_count'),quality.get('nonpositive_count'))!=(CASE['M'],0,0)
     or worker.get('actual_SICN_threshold')!=.1 or not math.isfinite(quality.get('minimum',float('nan'))) or quality['minimum']<.1
     or a['node_tags']!=sorted(set(a['node_tags'])) or len(a['node_tags'])!=CASE['N'] or len(a['coordinates_mm'])!=CASE['N']
     or len(a['tetra_tags'])!=CASE['M'] or a['tetra_tags']!=sorted(set(a['tetra_tags'])) or len(a['tetra_node_tags'])!=CASE['M']
     or peer.get('decision')!='CLEAR_COMPLETED_LOCAL_SAVED_EVIDENCE_47_PROVISIONAL_DOMAIN_ROUTES_68_REJECTS'
     or INPUTS[WORKER]!=CASE['records']['worker']['sha256'] or INPUTS[ARRAYS]!=CASE['records']['arrays']['sha256']):
  raise ValueError('Exact accepted same-case saved Netgen candidate and stopped peer required')
 points={};words={}
 for tag,xyz in zip(a['node_tags'],a['coordinates_mm']):
  if len(xyz)!=3 or any(type(x) is not float or not math.isfinite(x) for x in xyz):
   raise ValueError('Complete finite binary64 candidate coordinate rows required')
  points[tag]=tuple(Fraction.from_float(x) for x in xyz);words[tag]=xyz
 if len(shell['vertex_rows'])!=CASE['NV'] or [row['local_node_tag'] for row in shell['vertex_rows']]!=list(range(1,CASE['NV']+1)):
  raise ValueError('Every ordered fixed shell row required')
 for row in shell['vertex_rows']:
  xyz=words[row['local_node_tag']]
  if struct.pack('<3d',*xyz).hex()!=row['binary64_little_endian_bytes_hex']:
   raise ValueError('Every source shell binary64 word must remain fixed')
 cells=dict(zip(a['tetra_tags'],a['tetra_node_tags']))
 if (any(type(t) is not int or t<=0 for t in cells)
     or any(len(row)!=4 or len(set(row))!=4 or any(type(t) is not int for t in row) or not set(row)<=set(points) for row in cells.values())
     or set().union(*(set(row) for row in cells.values()))!=set(points)):
  raise ValueError('Complete ordered TET4 membership and no orphan node required')
 return points,cells


def main(contract_path,digest):
 start=time.monotonic();path=Path(contract_path)
 if not re.fullmatch('[0-9a-f]{64}',digest) or path.is_symlink() or sha(path)!=digest:raise ValueError('Exact external actual contract required')
 c=json.loads(path.read_text());configure(c)
 if (c.get('schema')!='962-current204-one-fixed47-case-domain-actual/v1' or c.get('diagnostic_execution_authorized') is not True
     or c.get('root_and_peer_review_complete') is not True or c.get('native_execution_authorized') is not False
     or c.get('qualification')!=QUALIFICATION or c.get('automatic_retry') is not False
     or c.get('method')!='complete_old_and_candidate_exact_pairs56_and_common_shell' or c.get('output_directory')!=OUTPUT
     or c.get('source_sha256')!=sha(__file__) or c.get('python_sha256')!=sha(Path(sys.executable).resolve())):
  raise ValueError('One reviewed stdlib-only local domain diagnostic required')
 pins=c['input_hashes']
 if any(pins.get(k)!=v for k,v in INPUTS.items()):raise ValueError('Every consumed record/helper must be direct-pinned')
 for k,v in pins.items():
  f=ROOT/k
  if Path(k).is_absolute() or f.is_symlink() or not f.resolve().is_relative_to(ROOT) or sha(f)!=v:raise ValueError('Before input drift')
 out=ROOT/OUTPUT
 if out.exists() or out.is_symlink() or out.resolve()!=out:raise ValueError('Fresh raw canonical output required')
 spec=importlib.util.spec_from_file_location('frozen_exact_local_pair_helper',ROOT/HELPER)
 helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper) # stdlib-only definitions; never main().
 record=case_record();observation=record['observation'];shell=record['shell'];context_join(observation,shell)
 worker=json.loads((ROOT/WORKER).read_text());arrays=json.loads((ROOT/ARRAYS).read_text());peer=json.loads((ROOT/PEER).read_text());accepted_native_records(worker)
 new_points,new_cells=saved_candidate(worker,arrays,shell,peer);old_points,old_cells,mapping=original(observation,shell)
 expected=[row['local_node_tags'] for row in shell['oriented_triangle_rows']]
 if len(expected)!=CASE['NF'] or len({tuple(sorted(f)) for f in expected})!=CASE['NF']:raise ValueError('All unique frozen shell faces required')
 old,old_volume=complex_rows(helper,old_points,old_cells,expected);new,new_volume=complex_rows(helper,new_points,new_cells,expected)
 if old['internal_face_pairs']!=CASE['original_internal_pairs'] or new['internal_face_pairs']!=CASE['candidate_internal_pairs']:raise ValueError('Dynamic complete opposite internal pair counts required')
 if any(row['exact_point1_gate_passed'] is not True for row in new['quality_rows']):raise ValueError('Every candidate exact SICN squared at least1/100 required')
 if any(old_points[t]!=new_points[t] for t in range(1,CASE['NV']+1)):raise ValueError('Common exact shell coordinates differ')
 if old_volume!=new_volume or helper.rational(old_volume)!={k:str(v) for k,v in shell['exact_enclosed_volume_mm3'].items()}:
  raise ValueError('Exact common-shell signed-volume bookkeeping differs')
 pair_results={};pair_failures={}
 for name,points,cells,count in [('old',old_points,old_cells,CASE['old_unordered_pairs']),('candidate',new_points,new_cells,CASE['candidate_unordered_pairs'])]:
  pairs=[]
  for first,second in combinations(sorted(cells),2):
   row=helper.pair_check(points,cells[first],cells[second]);row['tetrahedron_tags']=[first,second];pairs.append(row)
  if len(pairs)!=count:raise ValueError('Complete fixed-case unordered pair enumeration required')
  pair_results[name]=pairs;pair_failures[name]=sum(not row['intersection_equals_tagged_shared_simplex'] for row in pairs)
 failures=sum(pair_failures.values())
 if any(sha(ROOT/k)!=v for k,v in pins.items()) or sha(path)!=digest:raise ValueError('After input/contract drift')
 report=dict(schema='962-current204-fixed47-one-case-domain-result/v1',
  status='same_compact_oriented_local_domain' if failures==0 else 'pair_embedding_failed_no_domain_certificate',
  source_sha256=c['source_sha256'],contract_sha256=digest,input_hashes=pins,old=old,candidate=new,
  case_apex=CASE['apex'],case_record_sha256=CASE['source_record_sha256'],original_global_to_comparison_node_tags=mapping,old_complete_unordered_pairs=CASE['old_unordered_pairs'],candidate_complete_unordered_pairs=CASE['candidate_unordered_pairs'],
  complete_unordered_pairs=CASE['total_pairs'],plane_triples_enumerated=CASE['plane_triples'],pair_failures=pair_failures,pair_results=pair_results,
  exact_common_shell_coordinate_words=True,exact_identical_oriented_boundary=True,exact_signed_volume_identity=True,
  exact_old_pair_embedding=pair_failures['old']==0,exact_candidate_pair_embedding=pair_failures['candidate']==0,
  local_domain_equivalence_proved=failures==0,
  argument='Finite exact positive embedded3-chains in R3 have the same geometric oriented boundary. Their compact difference has zero boundary; its integer multiplicity is constant and zero outside bounded support, hence zero. Multiplicity-one interiors imply identical closed tetrahedral unions.',
  assumptions_checked=['exact stored binary64 coordinates','positive nondegenerate complete old/candidate cells','complete opposite internal-face pairs','identical oriented shell and fixed words','complete old and candidate exact pair embeddings'],
  source_candidate_report_sha256=INPUTS[WORKER],source_candidate_arrays_sha256=INPUTS[ARRAYS],source_candidate_independent_peer_sha256=INPUTS[PEER],
  scope='Relative local occupied-domain equality only; no new proof of original full-head embedding, outside non-overlap, connected-neighbor join, head edit or physical validity.',
  parent_context_sha256=FIXED_INPUTS[CONTEXT],candidate_interior_node_tags=CASE['candidate_interior_node_tags'],future_subset_masks_and_originaltag_parameter_projection_required=True,qualification=QUALIFICATION,native_optimizer_or_meshwrite_calls=0,coordinates_changed=False,bound_inputs_unchanged=True,wall_seconds=time.monotonic()-start)
 out.mkdir()
 with (out/'report.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
 return 0 if failures==0 else 2

if __name__=='__main__':raise SystemExit(main(*sys.argv[1:]))
