"""Saved JSON associations and bytes only; no native import or geometry predicate."""
from pathlib import Path
import hashlib,json,math,struct
ROOT=Path(__file__).resolve().parents[3];B=ROOT/'work/962-engineering';OUT=Path(__file__).parent
sha=lambda r:hashlib.sha256(r).hexdigest()
def load(rel):return json.loads((ROOT/rel).read_text())
AP='work/962-engineering/head-star-current204-full-stars-execution-prep-001/actual-contract.json'
CP='work/962-engineering/head-star-current204-full-stars-root-execution-001/closed-result.json'
RP='work/962-engineering/head-star-current204-full-stars-root-execution-001/result-review.json'
LP='work/962-engineering/head-star-current204-full-stars-root-execution-001/launch.json'
PEER='work/962-engineering/head-star-current204-full-stars-child-peer-001/review.json'
a=load(AP);closed=load(CP);root_review=load(RP);launch=load(LP);directory=ROOT/a['output_directory']
assert sha((ROOT/AP).read_bytes())=='a613681c5d653a4bd68e31604d50f14716bfc003d7eb2eff2f7149a89ecba7d2'
assert sha((ROOT/CP).read_bytes())=='67ce69c8c2a35d8b56763550043c18a3db28d963a1cee5675c41e9f8f1765456'
assert sha((ROOT/RP).read_bytes())=='af50c15ef52da35a5c265cbfa7bff10c3aa99694b0d86acad121a8bc2b2f68af'
assert sha((ROOT/LP).read_bytes())=='56936bca2f235e4f6285b39eb0aeeb92bdb71919b1ff1b9cfe0fc053e7f68363'
skip={a['MSH'],a['candidate']};assert len(skip)==2
bound=set(a['input_hashes'])-skip
bound.update([AP,CP,RP,LP,PEER,str(Path(__file__).relative_to(ROOT))])
bound.update(str((directory/n).relative_to(ROOT)) for n in closed['outputs'])
before={rel:sha((ROOT/rel).read_bytes()) for rel in sorted(bound)}
for rel,digest in a['input_hashes'].items():
 if rel not in skip:assert before[rel]==digest
assert len(a['input_hashes'])==72 and len(set(a['input_hashes'])-skip)==70
assert set(closed['outputs'])=={'reader.py','run_readback.py','frozen-contract.json','native.log','readback-report.json','execution-receipt.json'}
assert set(x.name for x in directory.iterdir())==set(closed['outputs'])
for n,meta in closed['outputs'].items():
 raw=(directory/n).read_bytes();assert len(raw)==meta['bytes'] and sha(raw)==meta['sha256']
assert (directory/'frozen-contract.json').read_bytes()==(ROOT/AP).read_bytes()
assert closed['actual_sha256']==sha((ROOT/AP).read_bytes()) and closed['child_peer_sha256']==sha((ROOT/PEER).read_bytes())
assert closed['returncode']==0 and closed['stop_reason'] is None and closed['signals_sent']==[] and closed['wait_reaped']
assert closed['all72_inputs_unchanged'] and set(closed['input_match_by_path'])==set(a['input_hashes']) and all(closed['input_match_by_path'].values())
assert closed['all4_selected_runtime_unchanged'] and set(closed['runtime_match_by_path'])==set(a['external_runtime_hashes']) and all(closed['runtime_match_by_path'].values())
assert all(closed[k] for k in ['actual_unchanged','materialized_actual_copy_unchanged','child_peer_unchanged'])
assert len(closed['observed_owned_worker_processes'])==1
assert set(closed['individual_owned_PID_absence'])==({str(launch['owned_controller_PID'])}|{str(row['PID']) for row in closed['observed_owned_worker_processes']})
assert all(row['PPID']==launch['owned_controller_PID'] for row in closed['observed_owned_worker_processes'])
assert launch['actual_sha256']==closed['actual_sha256'] and launch['child_peer_sha256']==closed['child_peer_sha256']
assert all(closed['individual_owned_PID_absence'].values()) and closed['universal_process_absence_claimed'] is False
r=json.loads((directory/'readback-report.json').read_text());receipt=json.loads((directory/'execution-receipt.json').read_text())
assert sha((directory/'readback-report.json').read_bytes())=='0124cdb9dd65a1d2434e0ff44e3d390257ad32bbc9c068c9c330532f46d03239'
assert receipt['returncode']==0 and receipt['stop_reason'] is None and receipt['wall_seconds']<120
for key,n in [('reader_sha256','reader.py'),('runner_sha256','run_readback.py'),('contract_sha256','frozen-contract.json'),('native_log_sha256','native.log'),('readback_report_sha256','readback-report.json')]:assert receipt[key]==closed['outputs'][n]['sha256']
assert receipt['hard_wall_seconds']==120 and receipt['sampled_RSS_stop_bytes']==8589934592 and receipt['sampled_output_stop_bytes']==1073741824 and receipt['threads']==2
assert receipt['max_observed_RSS_bytes']==max(x['RSS_bytes'] for x in receipt['RSS_samples']) and receipt['max_observed_RSS_bytes']<8589934592
assert not receipt['hard_OS_CPU_quota_applied'] and not receipt['hard_address_space_limit_applied'] and receipt['native_generate_optimize_meshwrite_solve_calls']==0
w=ROOT/'work/962-engineering/apex1474426-head-application-001';worker=json.loads((w/'readback-report.json').read_text());proof=worker['after'];assert proof==worker['saved_reopen']
assert r['status']=='direct_saved_file_readback_completed' and r['bound_inputs_unchanged'] and r['direct_counts_metrics_and_positive_poor_total_match_single_worker_after']
for observed,expected in [('actual_mesh_nodes','total_mesh_nodes'),('actual_tetrahedra','tetrahedra'),('actual_tetra_referenced_nodes','tetra_referenced_nodes'),('actual_unreferenced_mesh_nodes','unreferenced_mesh_nodes'),('actual_referenced_interior_nodes','tetra_referenced_interior_nodes')]:assert r[observed]==proof[expected]==a['expected_saved_counts'][expected]
for k in ['sorted_node_tags_sha256','sorted_coordinates_sha256','sorted_tetra_tags_sha256','tagged_tetra_connectivity_sha256']:assert r[k]==proof['array_sha256s'][k]
fields=['count','minimum','maximum','p01','p05','p50','p95','p99','nonpositive_count']
for label,key in [('SICN','minimum_SICN'),('Jacobian','minimum_jacobian'),('native_volume_mm3','native_volume_mm3')]:
 for k in fields+['array_sha256']:assert r['direct_native_quality_extrema'][label][k]==proof['quality'][key][k]
assert r['direct_native_quality_extrema']['SICN']['below_point1_count']==proof['quality']['minimum_SICN']['below_point1_count']==204
for k in fields:assert r['independent_signed_volume_mm3'][k]==proof['quality']['independent_signed_volume_mm3'][k]
assert r['independent_signed_volume_mm3']['sum']==proof['summed_tetra_volume_mm3'] and r['independent_signed_volume_mm3']['relative_error_to_candidate']==proof['volume_relative_error']
assert r['direct_fresh_classifications']==proof['classifications'] and r['retained_only_not_repeated']=={'tetra_exterior_incidence':proof['actual_tetra_boundary'],'internal_face_orientation':proof['internal_tetra_face_orientation']}
assert r['actual_explicit_surface_triangles']==a['candidate_oriented_triangles'] and r['exact_source_boundary_coordinates'] and r['exact_sorted_explicit_surface_connectivity']
assert r['single_partial_replacement_saved_proof']['report_sha256']==a['partial_report_sha256'] and r['single_partial_replacement_saved_proof']['after_equals_saved_reopen']
assert r['SICN_point1_gate_passed'] is False and not r['engineering_accepted'] and not r['manufacturing_authorized'] and not r['thermal_resolution_established']
assert r['nonpositive_SICN_tetrahedra']==[] and r['fixed_boundary_only_nonpositive_cells'] is True
c=r['complete_seed_star_census'];poor=r['positive_poor_SICN_cells'];cells=c['complete_incident_tetrahedra'];nodes=c['unique_incident_nodes'];seeds=c['movable_node_tags'];nv=a['candidate_vertices']
assert [row['tetrahedron_tag'] for row in cells]==sorted({row['tetrahedron_tag'] for row in cells})
assert [row['node_tag'] for row in nodes]==sorted({row['node_tag'] for row in nodes})
assert seeds==sorted(set(seeds)) and all(type(t) is int and t>nv for t in seeds)
node_map={row['node_tag']:row for row in nodes};cell_map={row['tetrahedron_tag']:row for row in cells};seedset=set(seeds);counts={t:0 for t in seeds};native_indices=set();allmembers=set();poor_members=set();calculated_poor=[];bins={str(k):0 for k in range(5)}
def point_equal(x,y):return all(struct.pack('<d',v)==struct.pack('<d',w) for v,w in zip(x,y))
for row in nodes:
 t=row['node_tag'];p=row['coordinates_mm'];assert type(t) is int and t>0 and len(p)==3 and all(math.isfinite(v) for v in p) and [v.hex() for v in p]==row['binary64_hex']
 assert row['in_movable_seed_set']==(t in seedset) and row['source_boundary_tag']==(t<=nv) and row['freshly_proved_classification_scope']==('below_dim3' if t<=nv else 'dim3')
for row in cells:
 conn=row['node_tags'];idx=row['native_array_index'];q=row['initial_native_SICN'];assert len(conn)==len(set(conn))==4 and all(type(t) is int and t in node_map for t in conn)
 assert type(idx) is int and 0<=idx<r['actual_tetrahedra'] and idx not in native_indices;native_indices.add(idx);allmembers.update(conn)
 touch=sorted(seedset.intersection(conn));assert touch and touch==row['movable_node_tags']
 for t in touch:counts[t]+=1
 assert math.isfinite(q) and q>0 and type(row['initially_positive_poor']) is bool and row['initially_positive_poor']==(q<.1)
 if q<.1:calculated_poor.append(row['tetrahedron_tag'])
assert allmembers==set(node_map)
rows=poor['complete_tagged_cells'];assert len(rows)==204 and [x['tetrahedron_tag'] for x in rows]==sorted({x['tetrahedron_tag'] for x in rows})==calculated_poor==c['positive_poor_tetrahedron_tags']
for row in rows:
 t=row['tetrahedron_tag'];cell=cell_map[t];conn=row['node_tags'];assert row['native_array_index']==cell['native_array_index'] and conn==cell['node_tags'] and row['SICN']==cell['initial_native_SICN'] and 0<row['SICN']<.1
 assert len(row['coordinates_mm'])==len(row['binary64_hex'])==4
 for tag,p,hx in zip(conn,row['coordinates_mm'],row['binary64_hex']):assert point_equal(p,node_map[tag]['coordinates_mm']) and hx==node_map[tag]['binary64_hex']==[v.hex() for v in p]
 boundary=sum(tag<=nv for tag in conn);assert row['original_boundary_node_count']==boundary and row['interior_node_count']==4-boundary;bins[str(boundary)]+=1;poor_members.update(conn)
 assert row['Jacobian']>0 and row['native_volume_mm3']>0 and row['independent_signed_volume_mm3']>0
assert sorted(t for t in poor_members if t>nv)==seeds
assert bins==poor['by_original_boundary_node_count']=={'0':0,'1':0,'2':15,'3':189,'4':0} and poor['total']==204 and poor['all_original_boundary_nodes']==0 and poor['at_least_one_interior_node']==204
assert set(poor['representatives'])=={'2','3'}
for group,rep in poor['representatives'].items():
 choices=[row for row in rows if row['original_boundary_node_count']==int(group)];chosen=min(choices,key=lambda x:(x['SICN'],x['tetrahedron_tag']))
 for key,value in rep.items():assert chosen[key]==value
assert c['movable_count']==len(seeds)==154 and c['prospective_coordinate_variables']==3*len(seeds)==462
assert c['complete_incident_tetrahedron_count']==len(cells)==5267 and c['initially_positive_poor_incident_tetrahedra']==len(calculated_poor)==204 and c['initially_good_incident_tetrahedra']==len(cells)-len(calculated_poor)==5063
assert c['shared_by_multiple_movable_nodes_tetrahedra']==sum(len(row['movable_node_tags'])>1 for row in cells)==223
assert c['per_movable_node_complete_incident_counts']==[[t,counts[t]] for t in seeds]
assert c['unique_incident_node_count']==len(nodes)==2905 and c['unique_incident_boundary_node_count']==sum(row['source_boundary_tag'] for row in nodes)==1821
assert c['unique_incident_other_interior_node_count']==sum(not row['source_boundary_tag'] and not row['in_movable_seed_set'] for row in nodes)==930
assert c['all_seed_stars_complete_including_initially_good_and_shared_cells'] and c['all_positive_poor_rows_covered_by_movable_stars'] and c['unseedable_positive_poor_tetrahedron_tags']==[]
sections={'movable_node_tags_u64':('Q',seeds),'selected_tetrahedron_tags_u64':('Q',[row['tetrahedron_tag'] for row in cells]),'selected_tetrahedron_connectivity_u64':('Q',[t for row in cells for t in row['node_tags']]),'union_node_tags_u64':('Q',[row['node_tag'] for row in nodes]),'union_coordinates_f64':('d',[v for row in nodes for v in row['coordinates_mm']]),'selected_initial_SICN_f64':('d',[row['initial_native_SICN'] for row in cells])}
digests={key:sha(struct.pack('<'+str(len(values))+kind,*values)) for key,(kind,values) in sections.items()};assert digests==c['ordered_tagged_array_sha256s']
assert not c['shared_star_feasibility_computed'] and not c['source_boundary_or_other_context_repair_policy_approved'] and c['SLSQP_or_other_optimization_calls']==0
after={rel:sha((ROOT/rel).read_bytes()) for rel in sorted(bound)};assert after==before
result={'schema':'962-current204-saved-census-independent-associations/v1','decision':'PASS_SAVED_ASSOCIATIONS_WITH_STRICT_HEAD_REJECTION','report_sha256':sha((directory/'readback-report.json').read_bytes()),'root_closed_sha256':sha((ROOT/CP).read_bytes()),'root_result_review_sha256':sha((ROOT/RP).read_bytes()),'checker_sha256':sha(Path(__file__).read_bytes()),'small_input_count':len(bound),'before_sha256s':before,'after_sha256s':after,'all_small_inputs_unchanged':True,'six_output_inventory':closed['outputs'],'complete_poor_cells_checked':204,'fresh_bins':bins,'complete_serialized_cells_checked':len(cells),'serialized_nodes_checked':len(nodes),'coordinate_hex_words_checked':3*len(nodes),'movable_count':len(seeds),'coordinate_variables':3*len(seeds),'initially_good_cells':5063,'shared_cells':223,'boundary_context_nodes':1821,'other_interior_context_nodes':930,'six_typed_hashes_reconstructed':digests,'all_current_global_array_native3_signed_count_classification_joins_match':True,'global_enumeration_completeness_attributed_to_bound_reader_not_subset_reproved':True,'full_global_metrics_volumes_incidence_or_native_reopen_recomputed':False,'geometry_predicate_MSH_runtime_body_read_or_hash':False,'root_owned_worker_observation_reaping_individual_absence_metadata_joined_not_probed':True,'root_wall_seconds':closed['wall_seconds'],'controller_wall_seconds':receipt['wall_seconds'],'reader_wall_seconds':r['readback_wall_seconds'],'RSS_samples':len(receipt['RSS_samples']),'max_sampled_RSS_bytes':receipt['max_observed_RSS_bytes'],'RSS_not_true_peak_or_hard_quota':True,'zero_nonpositive_flag_is_vacuous_all_empty':True,'head_gate_passed':False,'engineering_accepted':False,'physics_qualified':False,'manufacturing_authorized':False}
with (OUT/'independent-saved-check.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps({k:result[k] for k in ['decision','complete_poor_cells_checked','complete_serialized_cells_checked','serialized_nodes_checked','movable_count','initially_good_cells','shared_cells','all_small_inputs_unchanged']}))
