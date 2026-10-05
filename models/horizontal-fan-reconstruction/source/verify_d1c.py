#!/usr/bin/env python3
"""Verify actual single-case D1C evidence without launching or admitting history."""
import hashlib,json,tempfile
from pathlib import Path


def verify(root):
    read=lambda p:json.loads((root/p).read_text())
    sha=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
    def require(value,message):
        if not value:raise ValueError(message)
    frozen=read('parameters/D1C-executed-capsule-manifest.json')
    for name,record in frozen['files'].items():
        path=Path(name);file=root/name if path.parts[0]=='source' else root/'parameters/D1C-executed-configurations'/Path(*path.parts[1:])
        require(file.stat().st_size==record['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==record['sha256'],'Executed D1C capsule identity')
    from prepare_d1c_capsule import prepare
    with tempfile.TemporaryDirectory(prefix='fan-D1C-capsule-check-') as t:
        prepare(root,Path(t)/'capsule')
    report=read('results/cfd/D1C-bounded-result.json');summary=read('results/cfd/D1C-960-flow-summary.json');archive=read('results/runtime/D1C-native-archive-verification.json');proposal=read('parameters/D1-coupling-proposed-protocol.json');native=read('parameters/D1C-executed-native-protocol.json')
    require(report['script_sha256']==sha('source/analyze_d1c_result.py') and report['baseline_report_sha256']==sha('results/cfd/D1-bounded-result.json') and report['proposal_sha256']==sha('parameters/D1-coupling-proposed-protocol.json'),'D1C native analysis provenance')
    require(native['acceptance_all_required']==proposal['acceptance_all_required'] and native['initial_fields_sha256']==proposal['initial_native_checkpoint_field_sha256'],'Executed criteria and checkpoint unchanged')
    require(report['complete_iterations']==list(range(901,961)) and report['complete_iteration_count']==60 and report['new_cases']==1 and report['incomplete_iterations_excluded']==[],'Exactly one actual complete60 branch')
    require(all(t['total_samples_including_initial900']==61 and t['new_samples_after900']==60 and t['iterations']==list(range(900,961)) for t in report['tables'].values()),'Exactly61 native rows and60 new measurements in every table')
    require(all(w['complete20_native_samples'] and w['prospectively_declared'] for w in report['windows']) and report['windows'][-1]['range']==[941,960],'All original prospective20 windows complete')
    initial=report['residual_trace_complete_iterations']['initial_max']
    require(max(initial[-20:])==summary['maximum_initial_residual_last_window']['p'] and max(initial[-20:])<=proposal['acceptance_all_required']['maximum_initial_residual_p'],'Native pressure trace must independently meet frozen criterion')
    require(summary['status']=='reference_pilot_admitted_numerically' and summary['criteria_checks'] and all(summary['criteria_checks'].values()) and all(n==453496 for n in summary['final_field_cell_counts'].values()) and report['candidate_original_frozen_gates_passed'],'Candidate numerical gates and actual finite field counts')
    from analyze_d1c_result import admission_supported
    require(admission_supported(True,summary),'Actual native complete admission')
    require(not admission_supported(False,summary),'A partial run must reject even a stale admitted summary')
    missing=dict(summary,criteria_checks={'residual_p':True})
    require(not admission_supported(True,missing),'Missing criteria cannot establish admission')
    missing=dict(summary,final_field_cell_counts={'p':453496})
    require(not admission_supported(True,missing),'Missing final fields cannot establish admission')
    require(report['last20_initial_p_max_reduction_percent']>=30 and not report['control_original_frozen_gates_passed'] and not report['paired_numerical_admission_established'] and not report['historical_fine_admission_restored'],'Coupling sensitivity cannot restore historical paired admission')
    require(report['shared_initial_partition_sha256']==proposal['shared_initial_MPI_partition_sha256'] and report['native_initial_processor_file_count']==80,'Exact preserved initial MPI partition identity')
    require(report['global_elapsed_seconds']<=300 and report['resources_released'] and report['services_unchanged'] and report['no_additional_phase_launched'],'Actual cap and owned resource release')
    iso=report['actual_isolation'];require(iso['CPU_max']==4 and iso['RAM_limit_bytes']==iso['memory_and_swap_limit_bytes']==5*1024**3 and iso['network']=='none' and all(iso['mounts_read_only'][p] for p in ['/native','/baseline','/capsule']),'Actual isolated CPU/memory/source caps')
    require(archive['archive_sha256']==report['native_archive_sha256'] and archive['all_members_verified'] and archive['local_transferred_archive_identity_verified'] and archive['telemetry_hashes_match_original_archived_native_flow_summary'] and archive['original_native_manifest_sha256']==report['native_manifest_sha256'],'Private archive and supplemental telemetry preservation')
    keys=['status','archive_bytes','archive_sha256','members','global_elapsed_seconds_setup_solver_reconstruction_audit_and_preservation','global_wall_cap_seconds','all_members_verified','private_archive_not_published']
    original=json.dumps({k:archive[k] for k in keys},indent=2)+'\n'
    require(hashlib.sha256(original.encode()).hexdigest()==archive['original_native_manifest_sha256'],'Exact native archive index recovered from sanitized verification')
    require(archive['members']['cases/consistent/flow-summary.json']['sha256']==sha('results/cfd/D1C-960-flow-summary.json'),'Original archived native flow summary identity')
    for name,entry in archive['native_telemetry_preserved_separately'].items():require(entry['sha256']==summary['file_sha256'][name],'Separate native tables match archived original summary')
    config=read('results/runtime/D1C-config-verification.json');require(config['runner_sha256']==sha('source/run_d1c_in_container.py') and config['all_initial_native_files_match'] and config['shared_initial_partition_verified'],'Actual executable and initial-field verification')
    fields=read('results/cfd/D1C-matched960-field-differences.json');require(fields['script_sha256']==sha('source/compare_d1c_native_fields.py') and fields['same_mesh_cells']==453496,'Matched960 actual field comparison')
    for name,entry in fields['dependency_sha256'].items():require(entry==sha('source/'+name),'Matched field reader dependency identity')
    old=read('results/runtime/D1-native-archive-verification.json')['members']
    for name,record in fields['used_native_inputs'].items():
        prefix,key=name.split('/',1)
        expected=old['D1-runtime-symlink-repair/cases/control/960/'+key] if prefix=='control' else archive['members']['cases/consistent/960/'+key] if prefix=='consistent' else config['native_source_files']['constant/polyMesh/'+key]
        require(record==expected,'Matched native fields and mesh provenance')
    require(fields['outlet']['consistent']['gross_reverse_to_net_ratio']>.1 and fields['outlet']['consistent']['reverse_area_fraction']>.35 and not fields['installed_cooling_improvement_established'],'Observed outlet reflux must remain an explicit unresolved limit')
    port=read('results/cfd/D1C-960-energy-and-port-analysis.json');require(port['analysis_script_sha256']==sha('source/analyze_flow_balance.py') and port['pressure_torque_recomputation_relative_error']<1e-6 and port['maximum_rotor_wall_velocity_difference_from_omega_cross_r_m_s']<1e-5 and not port['energy_balance_physically_qualified'],'Native port/wall-work independent identities and limits')
    render=read('results/cfd/D1C-residuals.json');require(render['script_sha256']==sha('source/plot_d1c_residuals.py') and render['control_report_sha256']==sha('results/cfd/D1-bounded-result.json') and render['candidate_report_sha256']==sha('results/cfd/D1C-bounded-result.json') and render['png_sha256']==sha('results/cfd/D1C-residuals.png') and render['plotted_complete_samples']=={'control':60,'consistent':60} and render['persistent_outlet_reflux_explicit'],'Actual60/60 residual rendering')
    require(not report['physical_validation_established'] and not report['installed_cooling_improvement_established'] and report['outlet_reverse_flow_remains_explicit_limit'],'Numerical admission cannot establish installed physical validation')
    print('D1C single native60 branch, frozen gates, private preservation and persistent reflux checked')


if __name__=='__main__':verify(Path(__file__).resolve().parents[1])
