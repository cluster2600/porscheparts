from pathlib import Path
import hashlib,json,math,stat,struct
ROOT=Path('project-role://engineering-checkout')
BASE=ROOT/'work/962-engineering';HERE=BASE/'apex1613031-head-application-root-execution-001';OUT=BASE/'apex1613031-head-application-001'
def rec(p):
 p=Path(p)
 if not p.is_absolute():p=ROOT/p
 assert p.is_file() and not p.is_symlink()
 raw=p.read_bytes();return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),mode=oct(stat.S_IMODE(p.stat().st_mode)))
def read(p):return json.loads((ROOT/p).read_text())
c=read('work/962-engineering/apex1613031-head-application-execution-prep-001/actual-contract.json')
idx=read('work/962-engineering/apex1613031-head-application-execution-prep-001/index.json')
closed=json.loads((HERE/'closed-result.json').read_text());r=json.loads((OUT/'readback-report.json').read_text());e=json.loads((OUT/'execution-receipt.json').read_text())
parent=read('work/962-engineering/apex1613790-head-application-001/readback-report.json')
ctx=read('work/962-engineering/current127-apex1613031-head-context-001/readback-report.json')
a=read('work/962-engineering/fixed-shell-netgen-apex1613031-001/arrays.json')
f=read('work/962-engineering/fixed-shell-netgen-apex1613031-001/fixture-report.json')
paths=set(c['input_hashes'])-{c['MSH']}
paths.update('work/962-engineering/apex1613031-head-application-execution-prep-001/'+n for n in ('actual-contract.json','index.json'))
paths.update('work/962-engineering/apex1613031-head-application-exact-child-peer-001/'+n for n in ('review.json','bindings.json'))
paths.update(str(p.relative_to(ROOT)) for p in [HERE/'launch-once.py',HERE/'authorization.json',BASE/'apex1613031-head-application-root-launch-peer-001/review.json',HERE/'preflight.json',HERE/'materialization.json',HERE/'launch.json',HERE/'closed-result.json',HERE/'controller.stdout.log',HERE/'controller.stderr.log'])
paths.update(str(p.relative_to(ROOT)) for p in OUT.iterdir() if p.is_file() and p.name!='head-volume.msh')
before={p:rec(p) for p in sorted(paths)}
for p,h in c['input_hashes'].items():
 if p!=c['MSH']:assert before[p]['sha256']==h==closed['inputs79_before'][p]['sha256']==closed['inputs79_after'][p]['sha256']
assert closed['inputs79_before']==closed['inputs79_after'] and len(closed['inputs79_before'])==79
assert closed['runtime5_before']==closed['runtime5_after'] and closed['static4_before']==closed['static4_after']
assert closed['all79_inputs_unchanged'] and closed['runtime5_unchanged'] and closed['static4_unchanged']
assert closed['returncode']==e['returncode']==2 and e['stop_reason'] is None
assert closed['signals']==[] and not closed['outer_fallback_used'] and closed['error'] is None
assert closed['controller_waited_reaped'] and closed['controller_owned_group_absent']
assert closed['argv']==idx['exact_controller_argv'] and closed['environment']==idx['exact_controller_environment']
assert e['hard_wall_seconds']==1200 and e['threads']==2 and e['sampled_RSS_stop_bytes']==8589934592 and e['sampled_output_stop_bytes']==1073741824
assert 0<e['wall_seconds']<1200 and 0<e['max_observed_RSS_bytes']<e['sampled_RSS_stop_bytes']
assert e['max_observed_RSS_bytes']==max(x['RSS_bytes'] for x in e['RSS_samples'])
assert all(x['RSS_bytes']>=0 and math.isfinite(x['wall_seconds']) for x in e['RSS_samples'])
assert sorted(p.name for p in OUT.iterdir())==sorted(idx['expected_output_names'])
for name,expected in closed['outputs'].items():
 p=OUT/name;assert p.stat().st_size==expected['bytes'] and stat.S_IMODE(p.stat().st_mode)==0o444
 if name!='head-volume.msh':assert before[str(p.relative_to(ROOT))]['sha256']==expected['sha256']
assert e['readback_report_sha256']==closed['outputs']['readback-report.json']['sha256']
assert e['native_log_sha256']==closed['outputs']['native.log']['sha256']
assert (OUT/'frozen-contract.json').read_bytes()==(ROOT/idx['actual']['path']).read_bytes()
assert r['status']=='completed_partial_head_replacement_whole_head_quality_gate_applied' and r['stage']=='completed_partial_repair_audits'
assert r['procedural_checks_passed'] and r['partial_replacement_completed'] and r['actual_replacement14_SICN_gate_passed'] and r['saved_mesh_identity_exact'] and r['bound_inputs_unchanged']
assert r['actual_whole_head_SICN_gate_passed'] is False
assert r['before']==parent['after'] and r['after']==r['saved_reopen']
assert r['before_preservation']==r['after_preservation']==r['saved_preservation']
for stage in ('before','after','saved_reopen'):
 s=r[stage];assert (s['total_mesh_nodes'],s['tetrahedra'],s['tetra_referenced_interior_nodes'],s['unreferenced_mesh_nodes'])==(1097222,3621771,225491,0)
 assert all(v['nonpositive_count']==0 for v in s['quality'].values())
 assert s['quality']['minimum_SICN']['minimum']==.039074265058645995
 assert s['volume_relative_error']<=1e-6 and s['source_boundary_identity']==ctx['current_source_boundary_identity']
assert r['before']['quality']['minimum_SICN']['below_point1_count']==127
assert r['after']['quality']['minimum_SICN']['below_point1_count']==r['actual_whole_head_positive_poor_count']==126
p=r['before_preservation']
assert p['preservation']=={k:ctx['future_preservation_references'][k] for k in p['preservation']}
assert p['metadata_sha256s']=={k:ctx['future_preservation_references'][k+'_sha256'] for k in p['metadata_sha256s']}
assert p['maxima']==ctx['independently_derived_global_maxima']==dict(node=1613977,element_all_dimensions=32159077)
assert p['original_classification_projection_exact'] and p['new_nodes_on_volume1']==p['expected_new_nodes']==0
assert sum(x['count'] for x in ctx['full_entity_node_parameter_inventory'])==1097222
assert sum(x['count'] for x in p['retained_original_parameter_projection'])==1097221
assert [(x['dimension'],x['count'],x['parameter_width']) for x in p['retained_original_parameter_projection']]==[(2,871731,0),(3,225490,0)]
node_map={str(i+1):tag for i,tag in enumerate(f['local_to_global_shell_node_tags'])};node_map['10']=1613031
assert r['local_to_global_node_map']==node_map
slots=sorted(x['tetrahedron_tag'] for x in ctx['complete_old_apex_incident_rows'])
assert r['replacement_element_slots']==slots and len(slots)==14
rows={str(t):[node_map[str(n)] for n in row] for t,row in zip(slots,a['after']['tetra_node_tags'])}
assert r['replacement_ordered_rows']==rows
for key,values in r['replacement14_native_metrics'].items():
 assert len(values)==14 and all(math.isfinite(v) and v>0 for v in values)
 assert b''.join(struct.pack('<d',v) for v in values)==b''.join(struct.pack('<d',v) for v in a['after']['native_qualities'][key])
assert min(r['replacement14_native_metrics']['SICN'])==.1008883740399272 and all(v>=.1 for v in r['replacement14_native_metrics']['SICN'])
assert r['native_operation_counts']==c['declared_operation_counts']
assert r['gmsh_warnings_errors']==[]
for k in ('global_embedding_or_containment_proved','stronger_Mesh2_criterion_passed','engineering_accepted','physics_qualified','material_qualified','process_calibrated','manufacturing_authorized','declared_controller_command_conformant'):assert r[k] is False
assert r['mesh_sha256']==closed['outputs']['head-volume.msh']['sha256']=='48b66aafbd9f1eb69e44305982186e966fe8f041d9b4a6a59be4b610b5d12e08'
after={p:rec(p) for p in sorted(paths)};assert before==after
result=dict(schema='962-apex1613031-head-application-root-own-saved-result-review/v1',decision='COMPLETED_PROCEDURAL_PARTIAL_REPAIR_ONLY_PENDING_STOPPED_PEER',closed=rec(HERE/'closed-result.json'),report=rec(OUT/'readback-report.json'),receipt=rec(OUT/'execution-receipt.json'),current_small_count=len(before),current_small_before=before,current_small_after=after,all_current_small_unchanged=True,full79_before_after_equal=True,finite_runtime5_before_after_equal_root_launch_attributed=True,static4_before_after_equal=True,mesh_raw_identity=closed['outputs']['head-volume.msh'],mesh_body_rehashed_or_decoded_in_this_review=False,checks=dict(before_full_audit_equals_current_parent_after=True,after_full_audit_equals_saved_reopen=True,full_preservation_three_snapshots_equal=True,outside1097221nodes_and3621757TET4_exact=True,full_lower_entity_physical_periodic_metadata_bound=True,full_before_parameter_inventory1097222_and_actual_retained1097221_rule=True,retained_parameters_dim2_871731_dim3_225490_width0=True,local10_to_global_apex_storage_only=True,all14_slots_and_ordered_rows_derived=True,all42_native_metrics_binary64_exact_to_local_candidate=True,all14_local_SICN_at_least_point1=True,poor_count127_to126=True,whole_head_minimum_unchanged=.039074265058645995,whole_head_strict_gate_passed=False,one_native_diagnostic_no_retry=True),process=dict(returncode=2,root_wall_seconds=closed['wall_seconds'],controller_wall_seconds=e['wall_seconds'],native_report_wall_seconds=r['wall_seconds'],signals=[],outer_fallback=False,controller_waited_reaped=True,controller_owned_group_absent=True,sampled_leader_RSS_max_bytes=e['max_observed_RSS_bytes'],native_worker_cleanup='Controller/source-attributed; root observes only controller lifecycle.'),authority_note='authorization.expected_controller_argv is descriptive shorthand, not an argv array; exact frozen index/preflight/launch/closed arrays and environments are authoritative.',limits=['Saved native observations are attributed to reviewed source and one completed execution; no scientific helper, mesh decode or mathematical predicate kernel was rerun.','Full entity-coordinate/parameter arrays and native audit reductions remain source/run-attributed; this root review checks saved associations, maps, words and reductions.','The exact local occupied-domain proof remains separate; global embedding/non-overlap and historical414 Mesh_2 surface failures are unproved/not reevaluated.','No head PDE, strength/fatigue/material/process/LPBF/twin/surrogate or manufacturing acceptance.','Finite runtime files are not a transitive package/OS/ABI proof.'],source001_static_refusal_and_d60false_history_preserved=True,engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
out=HERE/'own-review.json'
with out.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);print(file=f)
out.chmod(0o444);print(json.dumps(rec(out)))

