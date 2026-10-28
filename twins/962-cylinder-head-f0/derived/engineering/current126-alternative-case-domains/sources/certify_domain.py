"""HELD one fixed15 current126 alternative exact local-domain query before any parent-owner context."""
from pathlib import Path
from fractions import Fraction
from itertools import combinations
import hashlib,importlib.util,json,math,re,struct,sys,time
ROOT=Path(__file__).resolve().parents[3]
OUTPUT=CASE=CENSUS_DATA=None
WORKER=ARRAYS=None
QUALIFICATION=dict(native_application_authorized=False,head_execution_authorized=False,stitching_authorized=False,
 engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False,material_qualified=False,process_calibrated=False,head_PDE_authorized=False)
HELPER='work/962-engineering/fixed-shell-coupled-embedding-prep-001/check_embedding.py'
MANIFEST='work/962-engineering/head-star-current126-alternative-case-domains-prep-001/case-manifest.json'
MANIFEST_SHA='66200c5c18ff6137037ffdf5750cb966ff6f99df1ef6e6d1f290695d02ac7cf7'
BATCH='work/962-engineering/head-star-current126-alternative-batch-shells-001/report.json'
PEER='work/962-engineering/current126-alternative-Netgen-result-peer-001/review.json'
PEER_BINDINGS='work/962-engineering/current126-alternative-Netgen-result-peer-001/bindings.json'
ACCEPT='work/962-engineering/current126-alternative-Netgen-root-execution-001/result-peer-acceptance.json'
CENSUS='work/962-engineering/head-star-current126-full-stars-001/readback-report.json'
CENSUS_CONTRACT='work/962-engineering/head-star-current126-full-stars-001/frozen-contract.json'
CENSUS_ACCEPT='work/962-engineering/head-star-current126-full-stars-root-execution-001/result-peer-acceptance.json'
PARTIAL='work/962-engineering/apex1613031-head-application-001/readback-report.json'
PARTIAL_RECEIPT='work/962-engineering/apex1613031-head-application-001/execution-receipt.json'
PARTIAL_CLOSED='work/962-engineering/apex1613031-head-application-root-execution-001/closed-result.json'
PARTIAL_ACCEPT='work/962-engineering/apex1613031-head-application-root-execution-001/result-peer-acceptance.json'
FIXED_INPUTS={'work/962-engineering/head-star-current204-case-domains-prep-002/certify_domain.py': '7060580b7aa2743dec511bb9fc5e8cfb40ef86ea3332b068c5de9c845422efc8', 'work/962-engineering/apex1613031-domain-equivalence-prep-001/certify_domain.py': '3cb92684b1d757617854d5ea1b0896e04db632648251810fc784289110330118', 'work/962-engineering/fixed-shell-coupled-embedding-prep-001/check_embedding.py': '1b489cc8149f4b5db8f90c594e32fe4c09b5db00151df6b1cfc88362d1018134', 'work/962-engineering/domain-equivalence-prep-001/certify_domain.py': '0fe593d385e5a0ab4944528fa1b869ddf2c41c28d050576afe9be18213462296', 'work/962-engineering/head-star-current126-full-stars-prep-001/reader.py': '2348c032ecbbb694563978cb333aff1a7e4d37a5052c3ed841a7128bf797409c', 'work/962-engineering/head-star-current126-alternative-batch-shells-001/report.json': '721e05802e305a124b99f97c779426e3d7b8960cab30fbabc3d93ee318e3de73', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-manifest.json': 'e83b8824581d68c3b3ca29acbd9f50573833561298159cf7969bbd46eb722e4c', 'work/962-engineering/current126-alternative-Netgen-result-peer-001/review.json': '8bd554dffc1f7cc918ef7597a9dd6536e93015406f86d8dcce166d2cc960bdb9', 'work/962-engineering/current126-alternative-Netgen-result-peer-001/bindings.json': '0d920fd251ba9dd35eeacece6f260043f146fc4c1f12c0c87679aa72d7d13301', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/result-peer-acceptance.json': '930277138dfe5564c47165989096b2f1b936362f428391d1fab61b039127ae15', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/closed-result.json': 'ec4948878d396f995dda6df26795342bd0682f679d8e6c52acf3737be6294c3d', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/own-review.json': 'bfefc5be656cfc4fc2a4cde5f193c9cf10c36911973b9ae1916194d9bfd2553e', 'work/962-engineering/head-star-current126-full-stars-001/readback-report.json': 'ac40521a4add15f1bb414d7d1a1c2cd231a0107278b6fe43ec38dad27c269e1a', 'work/962-engineering/head-star-current126-full-stars-001/frozen-contract.json': 'd579a794f18bc9f7c4e153cb2042f32cb32b2c6b2f2235cec2edbef8aba91317', 'work/962-engineering/head-star-current126-full-stars-root-execution-001/result-peer-acceptance.json': 'f66d5857a0fa75352c3880ab2cd7bbc0bcae73833254f39423fd48971ebd52d9', 'work/962-engineering/head-star-current126-full-stars-root-execution-001/closed-result.json': '4ec76692bd1fb7bb592bf24c82b199830eb6a4828cf9726fc879fa387022fb99', 'work/962-engineering/head-star-current126-full-stars-result-peer-001/review.json': 'f22ee8bfc026caec2b6182bddfdfa250795ea3ee698c73c41a823a6dd1f5a4c4', 'work/962-engineering/head-star-current126-full-stars-result-peer-001/bindings.json': 'c2c33a39a1cb3f393288ee4a7f344f17d45bfa44c8c81347fe07cca6421b66d5', 'work/962-engineering/apex1613031-head-application-001/readback-report.json': '64caf59811e229628ea1be138ebcc48cdf940c4ca2724be0b9080e255951c9f5', 'work/962-engineering/apex1613031-head-application-001/execution-receipt.json': '496b0e01950b777acd1c1759177fe26fac5659e5ec6512bb19ff9cb56b5fd46d', 'work/962-engineering/apex1613031-head-application-root-execution-001/closed-result.json': '9324c5ef88293efa33f9e14cfeff3e092795eec337fceeaffd7481ac2ee41471', 'work/962-engineering/apex1613031-head-application-root-execution-001/result-peer-acceptance.json': '19ef174a208868bf174909a1add690971fdf018b8cf438c5c26e3a2bca9bfada', 'work/962-engineering/head-star-current126-alternative-local-pipeline-reuse-plan-001/NOTE.md': '277365db120978ffc3b75702d192698f031677a267328c2e0bab176dfedf2c6c', 'work/962-engineering/head-star-current126-full-stars-runtime-root-001/review.json': '28101a316a5070a9d33092f5afc08dd84a347f6b8e2b51bed88a4c00ab951e7c'}
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
 if (manifest.get('schema')!='962-current126-alternative-fixed15-case-domain-manifest/v1' or manifest.get('selected_count')!=15
     or len(manifest['cases_in_accepted_order'])!=15 or type(apex) is not int):raise ValueError('Only fixed15 accepted cases exist')
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


def partial_after_proof(worker,receipt,closed,contract):
 """Bind the actual partial-replacement after/saved proof without optimizer aliases."""
 if (worker.get('schema')!='962-apex1613031-head-application-result/v1'
     or worker.get('status')!='completed_partial_head_replacement_whole_head_quality_gate_applied'
     or worker.get('stage')!='completed_partial_repair_audits'
     or any(worker.get(k) is not True for k in ['procedural_checks_passed','partial_replacement_completed','saved_mesh_identity_exact','bound_inputs_unchanged'])
     or worker.get('after')!=worker.get('saved_reopen')
     or worker.get('mesh_sha256')!=contract['MSH_sha256'] or worker.get('mesh_bytes')!=contract['MSH_bytes']
     or any(worker.get(key)!=contract[key] for key in ['local_candidate_report_sha256','local_candidate_arrays_sha256','current_local_domain_report_sha256','current_local_domain_peer_sha256'])
     or worker.get('native_operation_counts')!=contract['expected_partial_operation_counts'] or worker.get('call_counts_are_attempts') is not True
     or worker.get('upstream_census_launch_deviation_sha256')!=contract['upstream_census_launch_deviation_sha256']
     or worker.get('declared_controller_command_conformant') is not False or contract['declared_controller_command_conformant'] is not False
     or worker.get('original_parent_MSH_sha256')!=contract['original_parent_MSH_sha256']
     or receipt.get('returncode')!=2 or receipt.get('stop_reason') is not None
     or receipt.get('readback_report_sha256')!=contract['partial_report_sha256']
     or receipt.get('contract_sha256')!=contract['partial_contract_sha256']
     or receipt.get('reader_sha256')!=contract['partial_reader_sha256']
     or receipt.get('runner_sha256')!=contract['partial_runner_sha256']
     or receipt.get('native_log_sha256')!=contract['partial_native_log_sha256']
     or receipt.get('native_generate_optimize_solve_calls_declared')!=0 or receipt.get('mesh_write_calls_declared')!=1 or receipt.get('counters_are_declarations') is not True
     or closed.get('schema')!='962-apex1613031-head-application-root-closed/v1'
     or closed.get('returncode')!=2 or closed.get('error') is not None or closed.get('signals')!=[] or closed.get('outer_fallback_used') is not False
     or any(closed.get(k) is not True for k in ['controller_waited_reaped','controller_owned_group_absent','all79_inputs_unchanged','runtime5_unchanged','static4_unchanged'])
     or closed.get('automatic_retry') is not False
     or closed.get('whole_actual_mirror_sha256')!=contract['partial_contract_sha256']
     or closed.get('outputs')!=contract['partial_output_inventory']):
  raise ValueError('Exact stopped partial-replacement after/saved proof required')
 proof=worker['after'];n=proof['tetrahedra'];quality=proof['quality'];keys={'sorted_node_tags_sha256','sorted_coordinates_sha256','sorted_tetra_tags_sha256','tagged_tetra_connectivity_sha256'}
 counts={k:proof[k] for k in contract['expected_saved_counts']}
 if (counts!=contract['expected_saved_counts'] or any(type(v) is not int for v in counts.values())
     or set(proof['array_sha256s'])!=keys
     or set(quality)!={'minimum_jacobian','native_volume_mm3','minimum_SICN','independent_signed_volume_mm3'}
     or any(type(row.get('count')) is not int or row['count']!=n or type(row.get('nonpositive_count')) is not int for row in quality.values())
     or quality['minimum_SICN']['below_point1_count']-quality['minimum_SICN']['nonpositive_count']!=contract['expected_positive_poor_total']
     or quality['minimum_SICN']['nonpositive_count']!=contract['diagnostic_maximum_nonpositive_cells']
     or worker.get('actual_whole_head_positive_poor_count')!=contract['expected_positive_poor_total']
     or worker.get('actual_whole_head_SICN_gate_passed') is not (quality['minimum_SICN']['minimum']>=.1 and quality['minimum_SICN']['nonpositive_count']==0)
     or proof['source_boundary_identity']!=contract['expected_source_boundary_identity']):
  raise ValueError('Complete current partial-head arrays/counts/quality/boundary proof required')
 return proof


def require_after_match(report,proof,expected_positive_poor_total):
 """Require direct full saved-file observations to match the single worker proof."""
 for observed,expected in [('actual_mesh_nodes','total_mesh_nodes'),('actual_tetrahedra','tetrahedra'),('actual_tetra_referenced_nodes','tetra_referenced_nodes'),('actual_unreferenced_mesh_nodes','unreferenced_mesh_nodes'),('actual_referenced_interior_nodes','tetra_referenced_interior_nodes')]:
  if type(report[observed]) is not int or report[observed]!=proof[expected]:raise ValueError('Saved node/tetrahedron/reference counts differ from worker.after')
 fields=['count','minimum','maximum','p01','p05','p50','p95','p99','nonpositive_count']
 for name,key in [('SICN','minimum_SICN'),('Jacobian','minimum_jacobian'),('native_volume_mm3','native_volume_mm3')]:
  observed=report['direct_native_quality_extrema'][name];expected=proof['quality'][key]
  if any(observed[k]!=expected[k] for k in [*fields,'array_sha256']):raise ValueError('Full saved native metric differs from worker.after: '+name)
  if name=='SICN' and observed['below_point1_count']!=expected['below_point1_count']:raise ValueError('SICN below-point1 count differs from worker.after')
 observed=report['independent_signed_volume_mm3'];expected=proof['quality']['independent_signed_volume_mm3']
 if (any(observed[k]!=expected[k] for k in fields) or observed['sum']!=proof['summed_tetra_volume_mm3'] or observed['relative_error_to_candidate']!=proof['volume_relative_error']):
  raise ValueError('Independent saved signed-volume distribution/sum differs from worker.after')
 if report['positive_poor_SICN_cells']['total']!=expected_positive_poor_total:raise ValueError('Exact current positive-poor partition required')


def current_proof():
 c=json.loads((ROOT/CENSUS_CONTRACT).read_text());report=json.loads((ROOT/CENSUS).read_text())
 worker=json.loads((ROOT/PARTIAL).read_text());receipt=json.loads((ROOT/PARTIAL_RECEIPT).read_text());closed=json.loads((ROOT/PARTIAL_CLOSED).read_text())
 accepted=json.loads((ROOT/CENSUS_ACCEPT).read_text());partial_accepted=json.loads((ROOT/PARTIAL_ACCEPT).read_text())
 if (c['MSH_sha256']!='48b66aafbd9f1eb69e44305982186e966fe8f041d9b4a6a59be4b610b5d12e08' or c['MSH_bytes']!=235786462
     or c['expected_positive_poor_total']!=126 or c['partial_report_sha256']!=FIXED_INPUTS[PARTIAL]
     or accepted.get('decision')!='ACCEPT_COMPLETE_CURRENT126_READ_ONLY_CENSUS_ASSOCIATIONS_ONLY'
     or accepted['current_report']['path']!=CENSUS or accepted['current_report']['sha256']!=FIXED_INPUTS[CENSUS]
     or accepted['current_contract']['path']!=CENSUS_CONTRACT or accepted['current_contract']['sha256']!=FIXED_INPUTS[CENSUS_CONTRACT]
     or accepted.get('prior_d60_command_conformant') is not False or accepted.get('whole_head_quality_accepted') is not False
     or partial_accepted.get('decision')!='ACCEPT_COMPLETED_PROCEDURAL_PARTIAL_HEAD_REPAIR_ONLY_WHOLE_HEAD_REJECTED'
     or partial_accepted['partial_report']['path']!=PARTIAL or partial_accepted['partial_report']['sha256']!=FIXED_INPUTS[PARTIAL]
     or partial_accepted.get('whole_head_quality_accepted') is not False):
  raise ValueError('Exact current126 census and quality-rejected partial-head acceptance required; no context alias')
 proof=partial_after_proof(worker,receipt,closed,c);require_after_match(report,proof,126)
 if (any(report[key]!=proof['array_sha256s'][key] for key in proof['array_sha256s'])
     or report['direct_fresh_classifications']!=proof['classifications']
     or report['declared_controller_command_conformant'] is not False
     or report['upstream_census_launch_deviation_sha256']!=c['upstream_census_launch_deviation_sha256']
     or report['complete_seed_star_census']['movable_count']!=100
     or report['complete_seed_star_census']['complete_incident_tetrahedron_count']!=3123
     or report['complete_seed_star_census']['all_seed_stars_complete_including_initially_good_and_shared_cells'] is not True
     or report['complete_seed_star_census']['all_positive_poor_rows_covered_by_movable_stars'] is not True):
  raise ValueError('Full current100seed census arrays/classes/completeness must match the single after/saved proof')
 return report


def configure(c):
 global CASE,OUTPUT,WORKER,ARRAYS,INPUTS,CENSUS_DATA
 if sha(ROOT/MANIFEST)!=MANIFEST_SHA:raise ValueError('Fixed finite15 manifest changed')
 manifest=json.loads((ROOT/MANIFEST).read_text());CASE=select_case(manifest,c.get('case_apex'));OUTPUT=CASE['output_directory']
 if c.get('case_record_sha256')!=CASE['source_record_sha256']:raise ValueError('Same-case subrecord required')
 WORKER=CASE['records']['worker']['path'];ARRAYS=CASE['records']['arrays']['path']
 INPUTS={**FIXED_INPUTS,MANIFEST:MANIFEST_SHA,**{r['path']:r['sha256'] for r in CASE['records'].values()},**{r['path']:r['sha256'] for r in CASE['old_inputs'].values()}}
 accepted=json.loads((ROOT/ACCEPT).read_text());peer=json.loads((ROOT/PEER).read_text());bindings=json.loads((ROOT/PEER_BINDINGS).read_text())
 if (accepted.get('decision')!='ACCEPT_COMPLETE28_NETGEN_CAPTURES_AND15_DOMAIN_PREPARATION_CANDIDATES_ONLY'
     or accepted['accepted_quality_and_storage_for_domain_preparation']!=manifest['accepted_apices']
     or [r['apex'] for r in accepted['held13_terminal_Netgen_results']]!=manifest['held13_Netgen_apices']
     or accepted.get('held1613791_without_Netgen') is not True or manifest.get('held1613791_without_Netgen') is not True
     or accepted['peer_review']['path']!=PEER or accepted['peer_review']['sha256']!=FIXED_INPUTS[PEER]
     or accepted['peer_bindings']['path']!=PEER_BINDINGS or accepted['peer_bindings']['sha256']!=FIXED_INPUTS[PEER_BINDINGS]
     or peer.get('decision')!='CLEAR_COMPLETED_SAVED28_NETGEN_ASSOCIATIONS_ONLY'
     or peer['bindings']['sha256']!=FIXED_INPUTS[PEER_BINDINGS]
     or bindings.get('schema')!='962-current126-alternative28-Netgen-independent-stopped-bindings/v1'
     or bindings['domain_preparation_candidate_tags']!=manifest['accepted_apices']
     or manifest.get('parent_outside_owner_context_exists_for_these15') is not False
     or manifest.get('declared_controller_command_conformant') is not False):
  raise ValueError('Exact current15 candidate/peer/root history required; outside-owner context does not yet exist')
 CENSUS_DATA=current_proof()


def case_record():
 batch=json.loads((ROOT/BATCH).read_text());record=next(r for r in batch['all_candidate_star_records'] if r['apex']==CASE['apex'])
 encoded=lambda x:(json.dumps(x,indent=2,allow_nan=False)+'\n').encode()
 for obj,key in [(record,'source_record_sha256'),(record['shell'],'shell_serialized_sha256'),(record['observation'],'observation_serialized_sha256')]:
  if hashlib.sha256(encoded(obj)).hexdigest()!=CASE[key]:raise ValueError('Exact original case/shell/observation body required')
 for key,value in [('shell',record['shell']),('observation',record['observation']),('screen',record['necessary_face_screen'])]:
  descriptor=CASE['old_inputs'][key];raw=encoded(value)
  if (INPUTS.get(descriptor['path'])!=descriptor['sha256'] or sha(ROOT/descriptor['path'])!=descriptor['sha256']
      or len(raw)!=descriptor['bytes'] or (ROOT/descriptor['path']).read_bytes()!=raw):
   raise ValueError('All three current exact saved case inputs must remain direct byte pins')
 return record


def census_join(observation,shell):
 apex=CASE['apex'];census=CENSUS_DATA['complete_seed_star_census']
 if (observation.get('source_census_sha256')!=FIXED_INPUTS[CENSUS]
     or observation.get('original_parent_MSH_sha256')!='48b66aafbd9f1eb69e44305982186e966fe8f041d9b4a6a59be4b610b5d12e08'
     or apex not in census['movable_node_tags'] or observation.get('embedding_domain_and_external_owner_checks_performed') is not False):
  raise ValueError('Exact current seed/census source required; no parent-owner or geometric proof is inherited')
 old=observation['native_ordered_cell_rows']
 actual=[r for r in census['complete_incident_tetrahedra'] if apex in r['node_tags']]
 if actual!=old or [r['tetrahedron_tag'] for r in actual]!=CASE['old_tetrahedron_tags'] or len(actual)!=CASE['K']:
  raise ValueError('Every current original apex cell/native index/corner/quality/member row must match')
 native={r['node_tag']:r for r in census['unique_incident_nodes']}
 global_keys=('boundary_global_node_tags','other_interior_global_node_tags');local_keys=('boundary_local_node_tags','other_interior_local_node_tags')
 classes=shell['original_source_classifications'];observed=observation['original_source_classifications']
 if (set(observed)!=set(global_keys) or set(classes)!=set(global_keys+local_keys)
     or any(classes[key]!=observed[key] for key in global_keys) or len(classes[global_keys[0]])!=CASE['NB']):
  raise ValueError('Exactly two observed global and four shell class lists required')
 inverse={str(t):i+1 for i,t in enumerate(shell['local_to_global_node_tags'])}
 if (shell['global_to_local_node_tags']!=inverse
     or any(classes[local]!=[inverse[str(t)] for t in classes[global_]] for global_,local in zip(global_keys,local_keys))):
  raise ValueError('Current global/local inverse and temporary shell labels differ')
 fields={'node_tag','coordinates_mm','binary64_hex','in_movable_seed_set','source_boundary_tag','freshly_proved_classification_scope'}
 shell_tags=set(shell['local_to_global_node_tags'])
 for row in observation['selected_node_rows']:
  other=native.get(row['node_tag'])
  if (other is None or set(other)!=fields or set(row)!=fields|{'binary64_little_endian_bytes_hex'}
      or any(row[key]!=other[key] for key in fields)
      or struct.pack('<3d',*row['coordinates_mm'])!=struct.pack('<3d',*other['coordinates_mm'])
      or row['binary64_little_endian_bytes_hex']!=struct.pack('<3d',*other['coordinates_mm']).hex()):
   raise ValueError('All original six census fields plus exact LE word augmentation required')
  if row['node_tag'] in shell_tags:
   boundary=row['source_boundary_tag']
   if (boundary!=(row['node_tag'] in classes[global_keys[0]])
       or (not boundary)!=(row['node_tag'] in classes[global_keys[1]])
       or row['freshly_proved_classification_scope']!=('below_dim3' if boundary else 'dim3')):
    raise ValueError('Original source classification is distinct from temporary fixed local shell status')
 if sorted(r['node_tag'] for r in observation['selected_node_rows'])!=CASE['old_vertex_tags']:
  raise ValueError('Complete original source-node membership required')


def accepted_native_records(worker):
 data={k:json.loads((ROOT/r['path']).read_text()) for k,r in CASE['records'].items() if k not in ['worker','arrays']}
 closed=data['root_closed'];receipt=data['receipt'];actual=data['actual']
 binding=json.loads((ROOT/PEER_BINDINGS).read_text());rows=[r for r in binding['per_case_bindings'] if r['apex']==CASE['apex']]
 if len(rows)!=1:raise ValueError('Exactly one current stopped candidate association required')
 row=rows[0]
 for role,name in [('worker','fixture-report.json'),('arrays','arrays.json'),('receipt','execution-receipt.json'),('actual','frozen-contract.json')]:
  if (closed['outputs'][name]!=CASE['records'][role] or row['outputs'][name]!=CASE['records'][role]
      or {k:binding['fresh_records'][CASE['records'][role]['path']][k] for k in ['path','sha256','bytes']}!=CASE['records'][role]):
   raise ValueError('Actual current descriptor schema and full saved inventory must join')
 if (closed['case_apex']!=CASE['apex'] or closed['returncode']!=0 or closed['error'] is not None or closed['signals']!=[]
     or closed['stop_reason'] is not None or closed['root_halt'] is not None or closed['valid_matching_closed_controller_receipt'] is not True
     or closed['waited_reaped'] is not True or closed['owned_controller_group_absent'] is not True
     or closed['actual']['sha256']!=CASE['records']['actual']['sha256'] or receipt['returncode']!=0 or receipt['stop_reason'] is not None
     or receipt['fixture_report_sha256']!=CASE['records']['worker']['sha256'] or receipt['contract_sha256']!=CASE['records']['actual']['sha256']
     or receipt['reader_sha256']!=actual['reader_sha256'] or receipt['runner_sha256']!=actual['runner_sha256']
     or actual['case_apex']!=CASE['apex'] or actual['case_record_sha256']!=CASE['source_record_sha256']
     or worker['case_apex']!=CASE['apex'] or worker['case_record_sha256']!=CASE['source_record_sha256']
     or worker['case_manifest_sha256']!=FIXED_INPUTS['work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-manifest.json']
     or worker['source_batch_sha256']!=FIXED_INPUTS[BATCH]
     or worker['next_stage']!='domain' or worker['later_head_storage_compatible'] is not True
     or worker['mesh_sha256']!=CASE['mesh_identity_root_inventory']['sha256']
     or worker['mesh_bytes']!=CASE['mesh_identity_root_inventory']['bytes']
     or closed['outputs']['cavity.msh']!=CASE['mesh_identity_root_inventory']
     or row['same_case_record_sha256']!=CASE['source_record_sha256'] or row['source_shell_sha256']!=CASE['shell_serialized_sha256']
     or (row['nodes'],row['tetrahedra'],row['referenced_interior_nodes'],row['next_stage'])!=(CASE['N'],CASE['M'],CASE['I'],'domain')):
  raise ValueError('Exact accepted natural same-case current Netgen capture/peer/root metadata required')


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
     or peer.get('decision')!='CLEAR_COMPLETED_SAVED28_NETGEN_ASSOCIATIONS_ONLY'
     or worker.get('original_source_classifications')!=shell['original_source_classifications']
     or worker.get('local_to_global_shell_node_tags')!=shell['local_to_global_node_tags']
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
 if (c.get('schema')!='962-current126-alternative-one-fixed15-case-domain-actual/v1' or c.get('diagnostic_execution_authorized') is not True
     or c.get('root_and_peer_review_complete') is not True or c.get('native_execution_authorized') is not False
     or c.get('qualification')!=QUALIFICATION or c.get('automatic_retry') is not False
     or c.get('method')!='complete_old_and_candidate_exact_pairs56_and_common_shell' or c.get('output_directory')!=OUTPUT
     or c.get('declared_controller_command_conformant') is not False
     or c.get('upstream_census_launch_deviation_sha256')!='d60fff297c6c45dc92e117262e36ffde36e2169d53fcd32ce2b79fabde5eebc3'
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
 record=case_record();observation=record['observation'];shell=record['shell'];census_join(observation,shell)
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
 report=dict(schema='962-current126-alternative-fixed15-one-case-domain-result/v1',
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
  source_census_sha256=FIXED_INPUTS[CENSUS],source_partial_report_sha256=FIXED_INPUTS[PARTIAL],
  source_candidate_root_acceptance_sha256=FIXED_INPUTS[ACCEPT],source_candidate_peer_bindings_sha256=FIXED_INPUTS[PEER_BINDINGS],
  parent_context_sha256=None,parent_owner_context_queried=False,outside_owner_context_established=False,
  declared_controller_command_conformant=False,upstream_census_launch_deviation_sha256='d60fff297c6c45dc92e117262e36ffde36e2169d53fcd32ce2b79fabde5eebc3',candidate_interior_node_tags=CASE['candidate_interior_node_tags'],future_subset_masks_and_originaltag_parameter_projection_required=True,qualification=QUALIFICATION,native_optimizer_or_meshwrite_calls=0,coordinates_changed=False,bound_inputs_unchanged=True,wall_seconds=time.monotonic()-start)
 out.mkdir()
 with (out/'report.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
 return 0 if failures==0 else 2

if __name__=='__main__':raise SystemExit(main(*sys.argv[1:]))
