#!/usr/bin/env python3
"""Verify completed20 native custody and reject pressure-unsteady admission."""
import hashlib,json
from pathlib import Path
from prepare_d2_restart1000 import identity
from d2_completion_guards import validate_plan


def validate_completed(result,summary):
    numerical=all(summary['criteria_checks'].values())
    pressure_stationary=all(result['reports']['extended']['stationarity_checks'].values())
    both=all(r['original_numerical_admission_supported'] and r['all_additional_stationarity_checks_pass'] for r in result['reports'].values())
    if result['both_cases_numerical_and_stationarity_admitted']!=both:raise ValueError('Admission must require both numeric and stationarity gates')
    if not both and result['status']!='inconclusive_domain_comparison':raise ValueError('Failed pressure/numeric prerequisites cannot admit domain comparison')
    if result['reports']['extended']['original_numerical_admission_supported']!=numerical:raise ValueError('Original numeric admission mismatch')
    if result['reports']['extended']['all_additional_stationarity_checks_pass']!=pressure_stationary:raise ValueError('Pressure stationarity admission mismatch')
    if any(result[k] for k in ['domain_independence_established','physical_validation_established','local_fields_qualified','airflow_improvement_proven']):raise ValueError('Unsupported qualification')


def verify(root):
    read=lambda name:json.loads((root/name).read_text())
    def require(condition,message):
        if not condition:raise ValueError(message)
    plan=read('parameters/D2-restart1000-protocol.json');validate_plan(plan)
    capsule=read('parameters/D2-completion-executed-capsule-manifest.json')
    for name,record in capsule['files'].items():
        first,rest=name.split('/',1);file='parameters/D2-completion-executed-'+('source/' if first=='source' else 'configurations/')+rest
        require(identity(root/file)==record,'Exact executed fixed20 capsule '+name)
    native=read('results/runtime/D2-supervisor-native-input-verification.json')
    require(native['capsule_manifest_identity']==identity(root/'parameters/D2-completion-executed-capsule-manifest.json') and native['all_hashes_and_sizes_checked'] and native['prepared_files']==96 and native['reused_native_inputs']==12,'Native preflight input identity')
    for public,frozen,key in [('parameters/D2-prepared-case-manifest.json','parameters/D2-completion-executed-configurations/prepared-case-manifest.json','prepared_manifest_identity'),('parameters/D2-supervisor-input-manifest.json','parameters/D2-completion-executed-configurations/previous-input-manifest.json','previous_input_manifest_identity')]:
        require(identity(root/public)==identity(root/frozen)==native[key],'Frozen prepared/reused manifest identity')
    archive=read('results/runtime/D2-completion-native-archive-verification.json');old=read('results/runtime/D2-native-archive-verification.json');members=archive['members']
    require(archive['all_members_verified'] and archive['all_transferred_members_verified'] and archive['local_transferred_archive_identity_verified'] and archive['native_processor_checkpoints_included'] and archive['private_archive_not_published'] and not archive['public_raw_scan_or_native_fields_included'],'Private complete native custody')
    require(len(members)==181 and archive['archive_identity']['bytes']==352214760,'Actual native archive coverage')
    proofmap={'results/cfd/D2-extended1020-flow-summary.json':'extended/flow-summary.json',
              'results/cfd/D2-completed-pair-analysis.json':'extended/comparison.json',
              'results/cfd/D2-completion-comparison-provenance.json':'extended/comparison-provenance.json',
              'results/runtime/D2-completion-native1020-verification.json':'extended/native1020-checkpoint-verification.json',
              'results/runtime/D2-completion-source-identity-verification.json':'extended/source-identity-verification.json'}
    for public,private in proofmap.items():require(identity(root/public)==members[private],'Actual native report identity '+public)
    e=read('results/runtime/D2-completion-execution-receipt.json');commands=e['commands']
    require(e['original_native_execution_receipt_sha256']==members['execution-receipt.json']['sha256'] and e['private_coordination_record_retained'],'Private native execution receipt identity, coordination not published')
    require(e['status']=='completed_exact20_no_retry' and e['restart_iteration']==1000 and e['target_iteration']==1020 and not e['current_control_replayed'] and e['no_retry_or_further_continuation'],'Single exact20 completion')
    require(len(commands)==3 and commands[0]['args']==plan['future_owned_commands_only'][0] and commands[1]['args']==plan['future_owned_commands_only'][1] and all(c['exit_status']==0 for c in commands) and [c['wall_cap_seconds'] for c in commands]==[110,25,30],'Exactly one actual solver command, reconstruction and analysis, no replay')
    launcher=read('results/runtime/D2-completion-launcher-receipt-sanitized.json')
    require(launcher['status']=='completed_exact20_preserved_and_released' and launcher['exit_status']==0 and launcher['global_wall_seconds_including_preservation_and_release']<=240 and launcher['services_unchanged'] and not launcher['owned_container_remaining'] and launcher['native_archive_verified'],'Actual240s cap and release')
    limits=launcher['actual_isolation'];require(limits['CPU_max']==4 and limits['RAM_limit_bytes']==5*1024**3 and limits['memory_and_swap_limit_bytes']==5*1024**3 and limits['network']=='none' and limits['pids_limit']==256 and all(limits['mounts_read_only'][p] for p in ['/prepared','/previous','/selections.npz','/capsule']),'Actual4CPU5GiB readonly isolation')
    release=read('results/runtime/D2-completion-release-confirmation.json');require(not release['own_flow_container_active'] and release['services_unchanged'] and release['no_new_solver_launched_for_confirmation'],'Independent resource release confirmation')
    fields=read('results/runtime/D2-completion-native1020-verification.json');require(fields['iteration']==1020 and fields['all32_native_files_complete_finite'] and len(fields['files'])==32,'Native complete seven fields/time across four ranks')
    for name,record in fields['files'].items():require(record==members['extended/'+name],'Private native1020 field custody')
    summary=read('results/cfd/D2-extended1020-flow-summary.json');result=read('results/cfd/D2-completed-pair-analysis.json');validate_completed(result,summary)
    require(summary['first_iteration']==1001 and summary['iterations_completed']==1020 and summary['native_window_sample_count']==20 and summary['contiguous_measurement_window_verified'] and all(n==680596 for n in summary['final_field_cell_counts'].values()),'Actual final20 complete/finite final fields')
    require(not any(summary['criteria_checks'][k] for k in ['residual_p','residual_U','residual_turbulence']) and not result['reports']['extended']['stationarity_checks']['common_pressure_std'] and not result['reports']['extended']['stationarity_checks']['between_windows_pressure'] and result['status']=='inconclusive_domain_comparison','Actual nonstationary pressure rejection despite completed20')
    require(result['analysis_script_sha256']==capsule['files']['source/analyze_d2_result.py']['sha256'] and result['protocol_sha256']==capsule['files']['configs/original-D2-protocol.json']['sha256'],'Exact native comparison algorithm and original frozen criteria')
    provenance=read('results/cfd/D2-completion-comparison-provenance.json')
    require(provenance['control_reused_complete60_no_solver_replay'] and provenance['extended_original_complete_iterations']==40 and provenance['extended_new_complete_iterations']==20 and provenance['raw_native_logs_not_concatenated'] and provenance['comparison_sha256']==identity(root/'results/cfd/D2-completed-pair-analysis.json')['sha256'],'Derived view explicitly40+20, immutable control60')
    for name,digest in result['source_sha256'].items():
        if name.startswith('current/'):
            require(digest==old['members']['cases/'+name]['sha256'],'Original readonly control field/table')
        elif '/derived960-to1020/' in name:
            function=name.split('/')[2];require(digest==provenance['tables'][function]['derived_view']['sha256'],'Explicit derived native table')
        else:require(digest==members[name]['sha256'],'Actual continuation field/table')
    trace=read('results/cfd/D2-completed-native-traces.json')
    require(trace['script_sha256']==identity(root/'source/plot_d2_completion_trace.py')['sha256'] and trace['PNG_sha256']==identity(root/'results/cfd/D2-completed-native-traces.png')['sha256'] and sorted(trace['completed_samples'].values())==[20,40,60] and trace['old_partial1001_excluded'] and trace['iterations_not_physical_time'],'Actual60/40+20 native plot')
    print('D2 exact20 completed, native custody, original pressure rejection and released240s lot checked')


if __name__=='__main__':verify(Path(__file__).resolve().parents[1])
