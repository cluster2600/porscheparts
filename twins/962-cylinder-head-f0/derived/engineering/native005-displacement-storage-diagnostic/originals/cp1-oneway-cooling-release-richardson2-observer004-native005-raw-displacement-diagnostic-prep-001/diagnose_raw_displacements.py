"""HELD/UNRUN native005 raw displacement storage diagnostic; no CLI/output writes.

The strict e69fdefe collector and parser validate_map remain unchanged. This
separate adapter does not establish independent actual dt/scaling, field
mechanics, reaction conventions or physical truth.
"""
import hashlib
import json
from pathlib import Path

STRICT={
  "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-field-collector-prep-001/collect_current_associations.py",
  "sha256": "e69fdefee51675c8747acf9ad55566de2797dac9740648a9f86d03349c626b68",
  "bytes": 19192
}
EXPECTED_NATIVE=Path("/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993/work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004")
KEYS={'map','X','F','Y','X_info','F_info','Y_info','native_log','END181_nodal','exodus_1','exodus_2','transfer_manifest'}


def structural_map(mapping,coordinates,time_word,parser):
    """Structural association only: actual dt/scaling provenance stays UNVERIFIED.

    Coordinates/time are supplied by this run's transfer/Exodus join, not the
    map. This adapter never calls validate_map or manufactures expected dt or
    scaling. All three storage views have a common solver origin.
    """
    need=parser.need;word_is_finite=parser.word_is_finite
    need(mapping['schema']=='962-RICH2-END181-node-global-DOF-map/v1',"Observer schema changed")
    need(mapping['scope']=='integer_associations_only_no_field_acceptance' and
         mapping['constraint_mask_scope']=='original_case_expected_labels_not_live_BC_or_DofMap_observation',"Map scope changed")
    for k,v in dict(step=181,event='TIMESTEP_END',nonlinear_system_name='nl0',physical_displacement_DOF_count=1275,
                    source_node_count=425,MPI_ranks=1,threads=1,Real_bytes=8,PetscScalar_bytes=8).items():
        need(type(mapping[k]) is type(v) and mapping[k]==v,"Fixed observer metadata changed: "+k)
    need(type(mapping['PetscInt_bytes']) is int and mapping['PetscInt_bytes'] in (4,8),"Unsupported observed integer width")
    need(mapping['PETSc_version']==[3,25,4] and all(type(x) is int for x in mapping['PETSc_version']),"Pinned PETSc version required")
    need(type(mapping['nonlinear_system_number']) is int and mapping['nonlinear_system_number']>=0,"Observed system number required")
    ndof=mapping['global_DOF_count'];need(type(ndof) is int and 1275<=ndof<=1700,"Observed full global size outside source contract")
    need(word_is_finite(mapping['time_binary64_LE_hex']) and mapping['time_binary64_LE_hex']==time_word,"Exact map/Exodus event-time word mismatch")
    need(word_is_finite(mapping['dt_binary64_LE_hex']),"Finite observed dt word required; semantic provenance UNVERIFIED")
    coords=coordinates;observed_scaling=[]
    need(len(coords)==425 and all(len(p)==3 and all(word_is_finite(w) for w in p) for p in coords),"Complete425 transfer/Exodus coordinate triples required")
    variables=mapping['variables'];need(len(variables)==4,"Four variable rows required")
    numbers=[]
    for slot,row in enumerate(variables):
        need(type(row['slot']) is int and row['slot']==slot and row['name']==NAMES[slot],"Variable slot/name changed")
        need(type(row['number']) is int and 0<=row['number']<4,"Variable number outside four-variable permutation")
        need(row['family']=='LAGRANGE' and row['order']=='FIRST' and row['physical_displacement'] is (slot<3),"FE/physical variable contract changed")
        need(word_is_finite(row['existing_scaling_binary64_LE_hex']),"Finite observed scaling word required; semantic provenance UNVERIFIED")
        observed_scaling.append(row['existing_scaling_binary64_LE_hex'])
        numbers.append(row['number'])
    need(set(numbers)==set(range(4)),"Complete variable-number permutation required")
    rows=mapping['rows'];need(len(rows)==1700,"All425x4 map rows required")
    dofs=set();physical=[];mask=[]
    for ordinal,row in enumerate(rows):
        node,slot=divmod(ordinal,4)
        need(type(row['source_node_ID']) is int and row['source_node_ID']==node and
             type(row['variable_slot']) is int and row['variable_slot']==slot and
             type(row['variable_number']) is int and row['variable_number']==numbers[slot],"Ordered node/slot/number association changed")
        need(row['coordinate_binary64_LE_hex']==coords[node],"Node coordinate word mismatch across slots/current capture")
        present=row['dof_present'];need(type(present) is bool and row['DOF_state']==('present' if present else 'absent'),"DOF presence/state mismatch")
        constrained=(node==0 and slot<3) or (node==32 and slot in (1,2)) or (node==137 and slot==2)
        need(type(row['constrained']) is bool and row['constrained']==constrained,"Original expected six-mask labels changed")
        if constrained:mask.append([node,slot])
        index=row['global_DOF']
        if present:
            need(type(index) is int and 0<=index<ndof and index not in dofs,"Duplicate/out-of-range global index")
            dofs.add(index)
        else:need(slot==3 and index is None,"Only placeholder may be absent with null index")
        if slot<3:
            need(present,"All1275 physical DOFs must be present");physical.append(dict(source_node_ID=node,slot=slot,global_DOF=index))
    need(dofs==set(range(ndof)) and len(physical)==1275 and len(mask)==6,"Complete actual global range/physical/mask closure required")
    for k in ['assembly_invoked','solution_or_physical_state_written','field_acceptance']:
        need(mapping[k] is False,"Observer read-only/field scope changed")
    reaction=mapping['reaction_convention']
    need(reaction['system']=='auxiliary_save_in' and reaction['save_in']==['rx','ry','rz'] and
         reaction['DOF_presence_is_not_kernel_activation'] is True and reaction['reaction_values_recorded_by_this_observer'] is False and
         reaction['unchanged_END181_collector_required'] is True and reaction['solver_F_has_nodal_BC_rows'] is True and
         reaction['constrained_F_is_not_reaction'] is True and reaction['scaling_changed_or_removed'] is False,"Reaction/scaling caveat changed")
    return dict(ndof=ndof,integer_bytes=mapping['PetscInt_bytes'],physical_rows=physical,expected_mask_labels=mask,
        transfer_Exodus_coordinate_and_map_Exodus_time_words_compared=True,
        observed_dt_binary64_LE_hex=mapping['dt_binary64_LE_hex'],observed_scaling_words=observed_scaling,
        actual_dt_independently_verified=False,scaling_independently_verified=False,
        strict_validate_map_called=False,strict_semantic_validation_passed=False,
        common_solver_origin_internal_storage_consistency_only=True,installed_ABI_proved=False,
        live_BC_observed=False,field_or_SI_force_or_reaction_accepted=False)



def diagnose_saved_displacements(binding_bytes,binding_sha256,parser,assessor,strict):
    """Future one-process offline call only; any exception is INCOMPLETE.

    A separately reviewed external caller must protect exact module loading,
    input namespace and complete control/exception/stream/output accounting.
    No authority follows from this source packet or operational native RC0.
    """
    need=strict.need
    need(type(binding_bytes) is bytes and type(binding_sha256) is str and hashlib.sha256(binding_bytes).hexdigest()==binding_sha256,'External diagnostic binding digest required')
    strict.module_identity(strict,STRICT,['need','strict_json','read_pin','word','module_identity'])
    need(strict.NATIVE==EXPECTED_NATIVE,'Fixed current native capture required')
    selected={k:v for k,v in strict.FILES.items() if k in KEYS}
    need(set(selected)==KEYS and len(selected)==12 and sum(v['bytes'] for v in selected.values())==16493574,'Exact twelve captured descriptors required')
    dependencies={'strict_helpers':STRICT,'parser':strict.PARSER,'assessor':strict.ASSESSOR}
    binding=strict.strict_json(binding_bytes)
    need(binding['schema']=='962-native005-raw-displacement-diagnostic-intake/v1' and binding['root_issued'] is True and binding['raw_saved_data_diagnostic_authorized'] is True and type(binding['invocations']) is int and binding['invocations']==1,'Separate once-only raw diagnostic authority required')
    need(all(binding[k] is True for k in ('independent_source_review_complete','root_source_review_complete','selected_decoder_runtime_review_complete')),'Source/loading/decoder runtime gates pending')
    need(all(binding[k] is False for k in ('native_execution_authorized','runtime_query_authorized','strict_semantic_acceptance','field_association_accepted','full_mechanical_assessment_authorized','physics_qualified','material_qualified','manufacturing_authorized','automatic_retry')),'No semantic/field/physics/native promotion')
    need(binding['source_dependencies']==dependencies and binding['captured_input_records']==selected and binding['operational_root']==strict.OPERATIONAL_ROOT and 'binding_sha256' not in binding,'Exact acyclic source/capture binding required')
    root_raw=strict.read_pin(strict.OPERATIONAL_ROOT,strict.META_CAP)
    root=strict.strict_json(root_raw)
    need(root['decision']=='ACCEPT_ONE_FIXED_NATIVE_COUPON_OPERATIONAL_CAPTURE_ONLY' and root['authority']['scientific_body_intake_authorized'] is False,'Separate prior operational-only acceptance required')
    strict.module_identity(parser,strict.PARSER,['strict_json','word_is_finite','scan_vectors','vector_words','parse_monitor_trace','bind_stream_headers'])
    strict.module_identity(assessor,strict.ASSESSOR,['geometry_family','node_sample'])
    payloads={k:strict.read_pin(v,v['bytes']) for k,v in selected.items()}
    transfer=strict.strict_json(payloads['transfer_manifest'])
    geometry,cells,frames,family=assessor.geometry_family(EXPECTED_NATIVE,['thermoelastic.e','thermoelastic.e-s002'],transfer)
    need(set(geometry)==set(range(425)) and len(cells)==256 and set(frames)==set(range(183)),'Complete current source-node/HEX8/frame association required')
    coordinates=[[strict.word(x) for x in geometry[node]] for node in range(425)]
    frame=frames[181]
    member=next(row for row in family if row['filename']==frame['member'])
    time_word=strict.word(member['times'][frame['index']])
    mapping=parser.strict_json(payloads['map'])
    association=structural_map(mapping,coordinates,time_word,parser)
    scans={name:parser.scan_vectors(payloads[name],association['integer_bytes'],payloads[name+'_info']) for name in ('X','F','Y')}
    trace=parser.parse_monitor_trace(payloads['native_log'].decode('utf-8','strict'))
    headers=parser.bind_stream_headers(scans,trace,association['ndof'],association['integer_bytes'])
    events=[row for row in headers['rows'] if row['step']==181]
    need([row['monitor_iteration'] for row in events]==[0,1],'Complete own END181 monitor pair required')
    indices=[row['global_DOF'] for row in association['physical_rows']]
    need(len(indices)==len(set(indices))==1275,'All physical global-index associations required')
    ordinal=events[1]['object_ordinal']
    X1=parser.vector_words(payloads['X'],scans['X']['objects'][ordinal],indices)
    old={n for n,p in geometry.items() if p[0]<=1.};born={n for n,p in geometry.items() if p[0]>=1.};shared=old&born
    need(len(old)==len(born)==225 and len(shared)==25 and shared=={r['source_node_id'] for r in transfer['node_rows'] if r['shared'] is True},'Exact transfer/native shared25 relation required')
    # Exact END CSV schema includes temperature/reactions. Reused parsing is
    # structural and lexical only; no force/temperature mechanics is accepted.
    end,storage=assessor.node_sample(EXPECTED_NATIVE/'thermoelastic_end_0181.csv',geometry,set(geometry),(*assessor.DISP,'temperature',*assessor.FORCE),shared)
    positions={r['source_node_id']:r['csv_line_numbers_1_based'] for r in storage['verified_doublets']}
    comparisons=[]
    for i,row in enumerate(association['physical_rows']):
        node=row['source_node_ID'];component=assessor.DISP[row['slot']]
        csv_word=strict.word(end[node][component]);cdf_word=strict.word(frame['fields'][component][node]);x_word=X1[i]
        comparisons.append(dict(**row,component=component,X1_word_LE=x_word,END181_CSV_word_LE=csv_word,END181_Exodus_word_LE=cdf_word,shared_doublet_line_numbers_1_based=positions.get(node),X1_CSV_exact_word_match=x_word==csv_word,X1_Exodus_exact_word_match=x_word==cdf_word,CSV_Exodus_exact_word_match=csv_word==cdf_word))
    need(len(comparisons)==1275,'No partial physical comparison family')
    match_keys=('X1_CSV_exact_word_match','X1_Exodus_exact_word_match','CSV_Exodus_exact_word_match')
    counts={key:dict(comparisons=1275,matches=sum(row[key] for row in comparisons),mismatches=sum(not row[key] for row in comparisons)) for key in match_keys}
    internally_equal=all(row[key] for row in comparisons for key in match_keys)
    report=dict(schema='962-native005-raw-displacement-storage-diagnostic/v1',status='COMPLETE_INTERNAL_DISPLACEMENT_STORAGE_MATCH' if internally_equal else 'COMPLETE_INTERNAL_DISPLACEMENT_STORAGE_MISMATCHES',binding_sha256=binding_sha256,source_dependencies=dependencies,captured_input_records=selected,operational_root=strict.OPERATIONAL_ROOT,geometry=dict(source_nodes=425,cells=256,END_frames=183,family=family,END181_member=frame['member'],END181_index=frame['index'],END181_time_word_LE=time_word),structural_map_association=association,stream_scans=scans,complete_trace=trace,header_associations=headers,selected_X1_object_ordinal=ordinal,comparison_rows=comparisons,comparison_counts=counts,all_three_internal_word_relations_match=internally_equal,nodal_storage=storage,source_CSV_bytes_retained_read_only=True,signed_zero_bits_preserved=True,observed_actual_dt_and_scaling_provenance='INDEPENDENTLY_UNVERIFIED',strict_validate_map_called=False,strict_semantic_validation_passed=False,field_association_accepted=False,common_solver_origin_internal_storage_consistency_only=True,physics_force_reaction_or_unscaling_accepted=False,live_BC_observed=False,Y0_uninterpreted_nonfinite_bits_retained_in_original_stream=True,Y1_replaced_by_rounded_X1_minus_X0=False,POLICY_loaded_or_changed=False,full_mechanical_assessment_performed=False,physics_material_LPBF_manufacturing_qualified=False,automatic_retry=False)
    # Two complete normal-path observations are not protection against ABA or
    # concurrent namespace mutation. A future caller must enforce that scope.
    for key,pin in selected.items():
        need(strict.read_pin(pin,pin['bytes'])==payloads[key],'Captured diagnostic artifact changed')
    need(strict.read_pin(strict.OPERATIONAL_ROOT,strict.META_CAP)==root_raw,'Operational root record changed')
    strict.module_identity(strict,STRICT,['read_pin','word','module_identity'])
    strict.module_identity(parser,strict.PARSER,['scan_vectors','parse_monitor_trace','bind_stream_headers'])
    strict.module_identity(assessor,strict.ASSESSOR,['geometry_family','node_sample'])
    need(len((json.dumps(report,allow_nan=False)+'\n').encode('utf-8'))<=strict.CAP,'Complete report exceeds32MiB; refuse without truncation')
    return report

