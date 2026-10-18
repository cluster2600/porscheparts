"""Independent saved-association checks; no native, geometry parser or creator code."""
from pathlib import Path
import hashlib,json,math,struct

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'work/962-engineering'
OUT=BASE/'apex1474426-head-application-001'
HERE=Path(__file__).resolve().parent
def load(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def jsha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def words(values,kind='d'):
    return struct.pack('<'+kind*len(values),*values)

actual=load(BASE/'apex1474426-head-application-execution-prep-001/actual-contract.json')
closed=load(BASE/'apex1474426-head-application-root-execution-001/closed-result.json')
report=load(OUT/'readback-report.json')
receipt=load(OUT/'execution-receipt.json')
launch=load(BASE/'apex1474426-head-application-root-execution-001/launch.json')
guard=load(BASE/'apex1474426-head-application-root-execution-001/launch-guard.json')
assert sha(BASE/'apex1474426-head-application-root-execution-001/closed-result.json')=='0b2c61d3f5418394aca86733bdcda859739d7ab1e9d2fbafec9dbd3f1b8be250'
assert closed['actual_sha256']==sha(OUT/'frozen-contract.json')=='9633bd0cb14cbaa42eba497d706c4fb138b557feb9a5447220678d6a79e69d3f'
assert (OUT/'frozen-contract.json').read_bytes()==(BASE/'apex1474426-head-application-execution-prep-001/actual-contract.json').read_bytes()
assert closed['child_peer_sha256']==sha(BASE/'apex1474426-head-application-child-peer-001/review.json')=='261a7c5ddc65811b9b68e63f3708194ee407242ec188321f9f2b0c863f37cf57'
assert set(p.name for p in OUT.iterdir())==set(closed['outputs'])=={'reader.py','run_readback.py','frozen-contract.json','native.log','readback-report.json','execution-receipt.json','head-volume.msh'}
for name,identity in closed['outputs'].items():
    p=OUT/name
    assert p.is_file() and not p.is_symlink() and p.stat().st_size==identity['bytes']
    if name!='head-volume.msh':
        assert sha(p)==identity['sha256'],name
assert report['mesh_sha256']==closed['outputs']['head-volume.msh']['sha256']=='4c6543f8e905c2771f9f313e5e131d06d081928deafb8dd5b43b18d9d2c73a3f'
assert report['mesh_bytes']==closed['outputs']['head-volume.msh']['bytes']==235744782
assert len(actual['input_hashes'])==56 and set(closed['input_match_by_path'])==set(actual['input_hashes'])
assert all(closed['input_match_by_path'].values()) and closed['all56_inputs_unchanged']
assert set(closed['runtime_match_by_path'])==set(actual['external_runtime_hashes']) and all(closed['runtime_match_by_path'].values())
assert all(closed[k] is True for k in ['all3_selected_native_runtime_unchanged','selected_NumPy_unchanged','actual_unchanged','materialized_actual_copy_unchanged','child_peer_unchanged','wait_reaped'])
assert closed['returncode']==receipt['returncode']==2 and closed['stop_reason'] is receipt['stop_reason'] is None and closed['signals_sent']==[]
assert closed['universal_process_absence_claimed'] is False and all(closed['individual_owned_PID_absence'].values())
owned={row['role']:row for row in closed['observed_owned_processes']}
assert set(owned)=={'owned-controller','observed-owned-native-worker'}
assert owned['owned-controller']['PID']==launch['owned_controller_PID']==launch['owned_controller_PGID']
assert owned['observed-owned-native-worker']['PPID']==owned['owned-controller']['PID']
assert set(map(int,closed['individual_owned_PID_absence']))=={row['PID'] for row in owned.values()}
assert guard['actual_sha256']==launch['actual_sha256']==closed['actual_sha256'] and guard['child_peer_sha256']==launch['child_peer_sha256']==closed['child_peer_sha256']
assert guard['all54_existing_inputs_current_and_two_future_sources_absent'] and guard['all3_native_and_numpy_init_current'] and guard['only_one_partial_native_application']
assert launch['automatic_retry'] is False and launch['controller_policy_seconds']==1200 and launch['outer_cleanup_deadline_seconds']==1260
assert launch['argv']==[actual['native_python'],'-B',str(OUT/'run_readback.py'),'--contract-sha256',closed['actual_sha256']]
assert launch['environment']=={'PATH':'/usr/bin:/bin','LANG':'C','PYTHONUTF8':'1','OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','PYTHONDONTWRITEBYTECODE':'1'}
for label,name in [('controller_stdout','controller.stdout.log'),('controller_stderr','controller.stderr.log')]:
    p=BASE/'apex1474426-head-application-root-execution-001'/name
    assert p.stat().st_size==closed[label]['bytes'] and sha(p)==closed[label]['sha256']
for field,filename in [('reader_sha256','reader.py'),('runner_sha256','run_readback.py'),('contract_sha256','frozen-contract.json'),('native_log_sha256','native.log'),('readback_report_sha256','readback-report.json')]:
    assert receipt[field]==sha(OUT/filename)
assert receipt['hard_wall_seconds']==1200 and receipt['sampled_RSS_stop_bytes']==8589934592 and receipt['sampled_output_stop_bytes']==1073741824 and receipt['threads']==2
assert receipt['final_output_bytes_before_receipt']==sum(v['bytes'] for k,v in closed['outputs'].items() if k!='execution-receipt.json')
assert receipt['max_observed_RSS_bytes']==max(s['RSS_bytes'] for s in receipt['RSS_samples'])==4880629760
assert receipt['wall_seconds']<closed['wall_seconds']<1200 and receipt['max_observed_RSS_bytes']<8589934592
assert receipt['counters_are_declarations'] is True and receipt['native_generate_optimize_solve_calls_declared']==0 and receipt['mesh_write_calls_declared']==1
assert receipt['hard_OS_CPU_quota_applied'] is receipt['hard_address_space_limit_applied'] is False

original=load(BASE/'head-star-replacement-001/readback-report.json')
context=load(BASE/'direct-sicn-apex1474426-head-context-001/readback-report.json')
observation=load(BASE/'direct-sicn-apex1474426-cavity-study-001/saved-star-observation.json')
shell=load(BASE/'direct-sicn-apex1474426-cavity-study-001/local-shell-input-001.json')
candidate=load(BASE/'fixed-shell-netgen-apex1474426-001/fixture-report.json')
arrays=load(BASE/'fixed-shell-netgen-apex1474426-001/arrays.json')['saved_reopen']
assert report['before']==original['after']==original['saved_reopen']
assert report['before']['array_sha256s']==context['full_array_sha256s'] and report['before']['classifications']==context['full_native_classifications']
assert report['after']==report['saved_reopen'] and report['after_preservation']==report['saved_preservation']
before,after=report['before'],report['after']
assert report['procedural_checks_passed'] and report['saved_mesh_identity_exact'] and report['bound_inputs_unchanged'] and report['partial_replacement_completed'] and report['partial_replacement_attempted']
assert report['stage']=='completed_partial_repair_audits' and report['status']=='completed_partial_head_replacement_whole_head_quality_gate_applied'
assert report['call_counts_are_attempts'] is True and report['native_operation_counts']==actual['declared_operation_counts']
assert report['runtime']==actual['expected_runtime'] and report['runtime_sha256s']==actual['runtime_sha256s']
for field,rel in [('original_parent_MSH_sha256','head-star-replacement-001/head-volume.msh'),('context_sha256','direct-sicn-apex1474426-head-context-001/readback-report.json'),('local_candidate_report_sha256','fixed-shell-netgen-apex1474426-001/fixture-report.json'),('local_candidate_arrays_sha256','fixed-shell-netgen-apex1474426-001/arrays.json'),('current_local_domain_report_sha256','apex1474426-domain-equivalence-001/report.json'),('current_local_domain_peer_sha256','apex1474426-domain-equivalence-result-peer-001/review.json')]:
    assert report[field]==actual['input_hashes']['work/962-engineering/'+rel]
assert report['gmsh_warnings_errors']==[]
for stage,counts in [(before,(1097050,3620820,225319)),(after,(1097057,3620861,225326))]:
    assert (stage['total_mesh_nodes'],stage['tetrahedra'],stage['tetra_referenced_interior_nodes'])==counts
    assert stage['retained_boundary_nodes']==871731 and stage['tetra_referenced_nodes']==stage['total_mesh_nodes'] and stage['unreferenced_mesh_nodes']==0
    assert stage['volume_relative_error']<=1e-6 and stage['summed_tetra_volume_mm3']==915453.1236217882
    assert stage['actual_tetra_boundary']=={'boundary_triangles':1743878,'exact_oriented_tetra_boundary':True,'nonmanifold_volume_faces':0}
    assert stage['internal_tetra_face_orientation']['same_oriented_internal_faces']==0 and stage['internal_tetra_face_orientation']['exact_internal_orientation_balance']
    assert 4*stage['tetrahedra']==1743878+2*stage['internal_tetra_face_orientation']['internal_faces']
    assert stage['surface']==before['surface'] and stage['surface']['exact_source_coordinates'] and stage['surface']['exact_source_oriented_connectivity']
    assert stage['source_boundary_identity']==context['current_source_boundary_identity']
    assert stage['interior_node_count_establishes_thermal_resolution'] is False
    for row in stage['quality'].values():
        assert row['count']==stage['tetrahedra'] and row['nonpositive_count']==0 and 0<row['minimum']<=row['maximum']
        sequence=[row[k] for k in ['minimum','p01','p05','p50','p95','p99','maximum']]
        assert all(math.isfinite(v) for v in sequence) and sequence==sorted(sequence)
for label in ['before_preservation','after_preservation','saved_preservation']:
    snap=report[label]
    assert snap['preservation']==context['future_preservation_references'] and snap['original_classification_projection_exact']
    for key,digest in snap['metadata_sha256s'].items():assert digest==jsha(context[key])
assert report['before_preservation']['new_nodes_on_volume1']==0 and report['after_preservation']['new_nodes_on_volume1']==7
assert report['before_preservation']['maxima']=={'node':1613805,'element_all_dimensions':32158126}
assert report['after_preservation']['maxima']=={'node':1613812,'element_all_dimensions':32158167}
assert after['classifications']['node_counts_by_classification_dimension']=={'0':0,'1':0,'2':871731,'3':225326}
assert after['source_boundary_identity']==before['source_boundary_identity']

old={row['tetrahedron_tag']:row['node_tags'] for row in observation['native_ordered_cell_rows']}
assert len(old)==60 and all(len(row)==4 and len(set(row))==4 and 1474426 in row for row in old.values())
assert context['complete_old_apex_incident_rows']==[{'tetrahedron_tag':t,'node_tags':old[t]} for t in sorted(old)]
old_poor=sum(0<row['initial_native_SICN']<.1 for row in observation['native_ordered_cell_rows']);assert old_poor==4
node_map={i:t for i,t in enumerate(shell['local_to_global_node_tags'],1)}
node_map.update({33:1474426,**dict(zip(range(34,41),range(1613806,1613813)))})
assert len(node_map)==len(set(node_map.values()))==40 and {str(k):v for k,v in node_map.items()}==report['local_to_global_node_map']
slots=sorted(old)+list(range(32158127,32158168))
assert slots==report['replacement_element_slots'] and len(set(slots))==101 and arrays['node_tags']==list(range(1,41))
expected_rows={str(tag):[node_map[k] for k in row] for tag,row in zip(slots,arrays['tetra_node_tags'])}
assert expected_rows==report['replacement_ordered_rows'] and len(expected_rows)==101
original_words={row['node_tag']:row for row in observation['selected_node_rows']}
mapped_words={node_map[tag]:xyz for tag,xyz in zip(arrays['node_tags'],arrays['coordinates_mm'])}
for tag,xyz in mapped_words.items():assert len(xyz)==3 and all(math.isfinite(x) for x in xyz)
for i,row in enumerate(shell['vertex_rows'],1):
    xyz=arrays['coordinates_mm'][i-1];global_tag=node_map[i]
    assert row['local_node_tag']==i and row['source_global_node_tag']==global_tag
    assert words(xyz).hex()==row['binary64_little_endian_bytes_hex']==original_words[global_tag]['binary64_little_endian_bytes_hex']
    assert [float(v).hex() for v in xyz]==original_words[global_tag]['binary64_hex']
assert sum(row['original_source_boundary_node'] for row in shell['vertex_rows'])==27
metrics={}
for name,values in report['replacement101_native_metrics'].items():
    assert len(values)==101 and all(math.isfinite(v) and v>0 for v in values)
    assert words(values)==words(arrays['native_qualities'][name])
    assert hashlib.sha256(words(values)).hexdigest()==candidate['saved_reopen']['quality'][name]['array_sha256']
    metrics[name]={'count':101,'minimum':min(values),'maximum':max(values),'array_sha256':hashlib.sha256(words(values)).hexdigest(),'all101_binary64_equal_frozen_candidate':True}
assert min(report['replacement101_native_metrics']['SICN'])==.13807503254019585 and all(v>=.1 for v in report['replacement101_native_metrics']['SICN'])
assert report['actual_replacement101_SICN_gate_passed'] is True
assert before['quality']['minimum_SICN']['below_point1_count']==208 and after['quality']['minimum_SICN']['below_point1_count']==204
assert report['actual_whole_head_positive_poor_count']==204==208-old_poor
assert report['actual_whole_head_SICN_gate_passed'] is False and after['quality']['minimum_SICN']['minimum']==.039074265058645995<.1
assert report['expected_whole_head_positive_poor_count_not_observed']==204 and report['expected_count_is_not_acceptance'] is True
for key in ['global_embedding_or_containment_proved','stronger_Mesh2_criterion_passed','engineering_accepted','physics_qualified','manufacturing_authorized']:assert report[key] is False
assert receipt['manufacturing_authorized'] is False and closed['head_physics_or_manufacturing_qualified'] is False
result={
 'schema':'962-apex1474426-head-application-independent-saved-association-check/v1',
 'decision':'CLEAR_COMPLETED_PARTIAL_REPLACEMENT_STRICT_HEAD_REJECTED',
 'seven_output_inventory':closed['outputs'],
 'small_output_bodies_hashed':6,'large_MSH_body_read_or_hash_by_checker':False,
 'all56_root_input_flags_and_three_runtime_flags_joined':True,
 'complete_before_equals_current_partial_after_and_saved':True,
 'complete_after_equals_saved_reopen':True,
 'full_native_audit_observations_worker_attributed':True,
 'outside_and_metadata_hash_joins_checked':True,
 'raw_mapping':{'local_node_count':40,'fixed_shell_word_joins':32,'source_boundary_shell':27,'source_interior_shell':5,'local33_to_existing_apex':1474426,'fresh7_global_tags':list(range(1613806,1613813)),'old_slots':60,'fresh_element_slots':41,'ordered_rows':101,'ordered_replacement_rows_json_sha256':jsha(expected_rows),'mapped40_coordinate_word_sha256':hashlib.sha256(b''.join(words(mapped_words[t]) for t in sorted(mapped_words))).hexdigest(),'mapped40_sorted_global_tags_sha256':hashlib.sha256(words(sorted(mapped_words),'Q')).hexdigest(),'actual_head_coordinate_words_not_independently_decoded':True},
 'all303_local_native_metric_values_bit_equal_candidate':True,'local_metrics':metrics,
 'before':{'nodes':1097050,'TET4':3620820,'interior':225319,'positive_poor':208},
 'after':{'nodes':1097057,'TET4':3620861,'interior':225326,'orphans':0,'positive_poor':204,'minimum_SICN':.039074265058645995,'strict_head_gate_passed':False},
 'observed_poor_reduction_matches_removed_four_without_using_prediction_as_gate':True,
 'natural_RC2_procedural_complete_no_error_or_stop':True,
 'root_wait_and_individual_owned_absence_metadata_checked_not_reprobed':True,
 'controller_sampled_max_RSS_bytes':receipt['max_observed_RSS_bytes'],
 'no_global_metric_or_incidence_or_native_reopen_reexecution':True,
 'no_MSH_decode_or_pair_predicate_reexecution':True,
 'engineering_accepted':False,'physics_qualified':False,'manufacturing_authorized':False
}
(HERE/'independent-saved-check.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
print(json.dumps({'decision':result['decision'],'all303_metric_words_equal':True,'replacement_rows':101,'fixed_shell_words':32,'actual_positive_poor':204,'strict_head_gate_passed':False},sort_keys=True))
