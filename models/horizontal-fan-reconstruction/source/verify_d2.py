#!/usr/bin/env python3
"""Check actual partial D2 receipts and reject unsupported stationary admission."""
import hashlib,json,math


def validate_partial(report):
    def require(ok,msg):
        if not ok:raise ValueError(msg)
    require(report['status']=='incomplete_pair_inconclusive_domain_comparison' and report['current_completed60'] and not report['extended_completed60'],'Partial D2 classification')
    require(not report['both_cases_stationary_admitted'] and not report['domain_comparison_gate_evaluated'],'A missing final window cannot admit a domain comparison')
    for label,n,end in [('current',60,1020),('extended',40,1000)]:
        r=report['reports'][label];require(r['complete_solver_iterations']==n and r['last_complete_iteration']==end and all(x==n+1 for x in r['native_table_samples_including960'].values()),'Native completed count/table correspondence')
    e=report['reports']['extended'];require(e['started_iterations']==41 and not e['End_present'] and not e['target_reached'] and e['windows'][-1]['status']=='missing_required_window' and e['windows'][-1]['samples']==0,'Partial1001 is not a completed iteration or target window')
    required={'initial_time_matches_frozen_continuation','residual_p','residual_U','residual_turbulence','mass_balance','flow_stability','torque_stability','declared_flow_direction','complete_finite_fields','finite_measurements'}
    require(set(report['current_original_numerical_checks'])==required and all(report['current_original_numerical_checks'].values()),'Complete ten original current gates')
    require(len(report['current_additional_stationarity_checks'])==7 and all(report['current_additional_stationarity_checks'].values()),'Seven current-only stationarity screens')
    m=report['MPI1000_coverage'];require(m['global_cells']==680596 and m['each_cell_exactly_once'] and m['common_faces']==4542 and m['each_common_face_exactly_once'] and m['common_phi_matches_native_functionObject'] and set(m['finite_completed1000_field_counts'])=={'p','U','k','omega','nut'} and all(n==680596 for n in m['finite_completed1000_field_counts'].values()),'Actual private MPI1000 complete coverage')
    require(report['matched_complete981_1000_windows']['descriptive_only_not_stationary_domain_comparison'] and report['no_new_solver_or_OpenFOAM_reconstruction_run'] and report['checkpoint1000_is_not_missing1020_or_a_continuation'],'Private checkpoint audit scope')
    require(not any(report[k] for k in ['domain_independence_established','physical_validation_established','airflow_improvement_proven','local_fields_qualified']),'Unsupported D2 qualification')


def verify(root):
    read=lambda f:json.loads((root/f).read_text());sha=lambda f:hashlib.sha256((root/f).read_bytes()).hexdigest()
    def require(ok,msg):
        if not ok:raise ValueError(msg)
    for prefix in ['D2-executed','D2-first-preparation']:
        capsule=read('parameters/'+prefix+'-capsule-manifest.json')
        for name,record in capsule['files'].items():
            first,rest=name.split('/',1);file='parameters/'+prefix+('-configurations/' if first=='configs' else '-source/')+rest
            require((root/file).stat().st_size==record['bytes'] and sha(file)==record['sha256'],'Exact executed capsule '+file)
    archive=read('results/runtime/D2-native-archive-verification.json');first=read('results/runtime/D2-first-native-archive-verification.json');partial=read('results/runtime/D2-partial1000-preservation-verification.json')
    for a in [archive,first]:require(a['all_members_verified'] and a['local_transferred_archive_identity_verified'] and a['private_native_fields_and_meshes_not_published'],'Private native archive preservation')
    require(archive['global_wall_cap_seconds']==720 and archive['global_elapsed_seconds_setup_solver_reconstruction_audit_and_preservation']<=720,'Original aggregate720s cap, not a restarted cap')
    require(len(archive['members'])==99 and archive['archive_bytes']==189782229 and partial['all_transferred_members_verified'] and partial['private_native_processor_fields_not_published'] and len(partial['members'])==44 and not partial['solver_or_reconstruction_launched'],'Separate private partial processor custody')
    for prefix,a in [('D2',archive),('D2-first',first)]:
        executed=read('results/runtime/'+prefix+'-execution-receipt.json');require(sha('results/runtime/'+prefix+'-execution-receipt.json')==a['members']['cases/execution-receipt.json']['sha256'],'Native execution receipt identity')
        if prefix=='D2-first':require(not any('foamRun' in x['args'] for x in executed['commands']),'First preparation must contain zero flow commands')
        launcher=read('results/runtime/'+prefix+'-launcher-receipt-sanitized.json');require(launcher['original_native_launcher_receipt_sha256']==a['members']['launcher-receipt.json']['sha256'] and launcher['services_unchanged'] and not launcher['owned_container_remaining'] and launcher['CPU_max']==4 and launcher['RAM_limit_bytes']==5*1024**3 and launcher['memory_and_swap_limit_bytes']==5*1024**3 and launcher['network']=='none','Actual isolation and release')
        for label in ['current','extended']:
            f='results/cfd/'+prefix+'-'+label+'-independent-mesh-gate.json';g=read(f);require(g['accepted_for_bounded_pilot'] and all(x['Mesh_OK'] and x['failed_checks']==0 for x in g['checks'].values()) and sha(f)==a['members']['cases/'+label+'/independent-mesh-gate.json']['sha256'],'Both native independent gates')
    commands=read('results/runtime/D2-execution-receipt.json')['commands'];flow=[x for x in commands if 'foamRun' in x['args']]
    require(len(flow)==2 and flow[0]['case']=='current' and flow[0]['exit_status']==0 and flow[1]['case']=='extended' and flow[1]['exit_status']==124 and flow[1]['wall_cap_seconds']==159,'Exactly one actual pair, extended stopped without continuation')
    mesh=read('results/cfd/D2-mesh-preparation.json');require(mesh['extension_m']==.275 and mesh['layers']==50 and mesh['original_core_cells']==453496 and mesh['extended_cells']==680596 and mesh['original_points_numerically_identical'] and mesh['original_faces_vertex_ids_and_owners_identical'] and mesh['original_internal_neighbours_identical'] and mesh['original_cell_ids_preserved'] and mesh['core_MPI_assignment_preserved'] and mesh['minimum_added_volume_m3']>0 and mesh['maximum_core_volume_abs_difference_m3']<1e-18,'Exact unchanged core and fixed extension')
    require(sha('results/cfd/D2-mesh-preparation.json')==archive['members']['cases/mesh-preparation.json']['sha256'],'Actual mesh receipt identity')
    r=read('results/cfd/D2-partial-pair-analysis.json');validate_partial(r);require(r['analysis_script_sha256']==sha('source/analyze_d2_partial_result.py'),'Partial analysis source identity')
    for name,digest in r['dependency_sha256'].items():require(sha('source/'+name)==digest,'Partial analysis dependency')
    for name,digest in r['source_sha256'].items():require(archive['members'][name]['sha256']==digest,'Verified private serial/table input identity')
    for name,record in r['partial_native_members_used'].items():require(partial['members'][name]==record,'Verified private processor input identity')
    require(r['partial_checkpoint_manifest_sha256']==partial['original_native_manifest_sha256'] and r['protocol_sha256']==sha('parameters/D2-executed-configurations/protocol.json'),'Partial manifest/protocol identity')
    trace=read('results/cfd/D2-native-traces.json');require(trace['script_sha256']==sha('source/plot_d2_native_trace.py') and trace['PNG_sha256']==sha('results/cfd/D2-native-traces.png') and trace['completed_samples']=={'current':60,'extended':40} and trace['missing_extended_iterations_not_drawn'],'Actual native60/40 plot')
    for name,digest in trace['source_sha256'].items():require(archive['members'][name]['sha256']==digest,'Native plot input identity')
    release=read('results/runtime/D2-release-confirmation.json');require(release['services_unchanged'] and not release['own_flow_container_active'] and release['no_other_service_modified'],'Confirmed resources released')
    print('D2 exact mesh, native60/40, incomplete admission, private custody and release checked')


if __name__=='__main__':
    from pathlib import Path
    verify(Path(__file__).resolve().parents[1])
