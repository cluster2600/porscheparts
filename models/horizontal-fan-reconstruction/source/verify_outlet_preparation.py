#!/usr/bin/env python3
"""Verify preparation provenance and reject a confounded outlet protocol; no solve."""
import hashlib,json,math


def require(condition,message):
    if not condition:raise ValueError(message)


def validate_protocol(p,d,previous):
    require(p['status']=='prepared_not_executed' and not any(p[k] for k in ['new_solver_run','new_mesh_generated','physical_validation_established']),'Preparation must not claim execution or validation')
    n=p['numerics'];e=p['extension'];run=p['execution'];obs=p['common_observables'];b=p['budget_proposed_not_launched']
    require(n['SIMPLE_consistent']=='yes' and n['pressure_relaxation']==.15 and n['pressure_relTol']==.01 and n['pressure_absolute_tolerance']==1e-8,'Matched coupling/numerics changed')
    require(all(n[k] for k in ['core_MPI_assignment_preserved','core_initial_fields_equal','core_geometry_and_MRF_membership_unchanged']),'Common core identity must be preserved')
    require(n['core_cells']==453496 and e['faces_per_layer']==d['native_outlet']['faces']==4542,'Baseline core/outlet count')
    require(e['layers']==50 and e['added_prisms']==e['layers']*e['faces_per_layer'] and e['total_cells']==n['core_cells']+e['added_prisms'],'Prism count')
    require(math.isclose(e['uniform_dz_m']*e['layers'],e['length_m']) and e['length_m']==.275 and math.isclose(e['new_outlet_z_m'],e['current_outlet_z_m']-e['length_m']),'Proposed axial sizing')
    require(not e['physical_minimum_distance_proven'] and not e['independent_mesh_gate_run'] and e['side_boundary']['U']=='slip' and not e['added_region_MRF'] and e['core_cell_ids_preserved'],'Virtual buffer scope/BC changed')
    require(obs['flow']['operation']=='orientedSum' and obs['flow']['outside_MRF'] and d['native_outlet']['owner_cells_inside_MRF']==0,'Conservative common face flux outside MRF')
    require(obs['pressure']['operation']=='volAverage' and not obs['pressure']['is_fan_port_pressure_rise'] and obs['fixed_cell_zones']==d['common_zones'],'Fixed common pressure statistic')
    require(run['cases']==['current-outlet','extended-outlet'] and run['sequential'] and run['iterations_each']==60 and p['restart_iteration']==960 and run['target_iteration']==1020 and run['windows']==[[961,980],[981,1000],[1001,1020]],'Fresh matched continuations required')
    require(not run['existing900_to960_control_reused_as_new_control'] and run['no_automatic_continuation'] and run['telemetry_interval']==1 and run['checkpoint_interval']==20,'Telemetry/window budget')
    require(p['original_numerical_acceptance_all_required']==previous['acceptance_all_required'],'Original gates must remain unchanged')
    g=p['domain_comparison_screen'];require(g['requires_both_numerical_and_stationarity_gates'] and not g['matrix_residuals_comparable_as_physical_domain_effect'] and g['thresholds_are_analyst_screening_not_Porsche_acceptance'],'Numerical and domain dependence must be distinct')
    require(g['common_flow_last20_relative_difference_max']==.01 and g['rotor_torque_and_input_power_last20_relative_difference_max']==.02 and g['common_pressure_last20_difference_Pa_floor']==5 and g['common_pressure_last20_relative_difference_max']==.01,'Prespecified domain screening bands')
    require(b['CPU']==4 and b['memory_and_swap_GiB']==5 and b['global_wall_cap_seconds_all_runtime_stages']==720 and b['stop_on_deadline_without_retry'] and b['actual_mesher_and_runner_not_yet_implemented'] and b['fresh_resource_and_concurrent_job_preflight_required'],'Unexecuted runtime budget and preconditions')


def verify(root):
    read=lambda name:json.loads((root/name).read_text())
    sha=lambda name:hashlib.sha256((root/name).read_bytes()).hexdigest()
    d=read('results/cfd/outlet-preparation-diagnostic.json');p=read('parameters/outlet-sensitivity-proposed-protocol.json');previous=read('parameters/D1C-executed-native-protocol.json')
    require(d['script_sha256']==sha('source/diagnose_outlet_preparation.py'),'Diagnostic source identity')
    for name,digest in d['dependency_sha256'].items():require(sha('source/'+name)==digest,'Diagnostic dependency identity')
    require(not any(d[k] for k in ['new_solver_run','new_mesh_generated','physical_validation_established']) and d['private_selections_not_published'] and d['extension_distance_is_not_yet_proven_sufficient'],'Preparation qualification boundary')
    archive=read('results/runtime/D1C-native-archive-verification.json');config=read('results/runtime/D1C-config-verification.json')['native_source_files'];old=read('results/runtime/D1-native-archive-verification.json')['members'];historical=read('results/cfd/pressure-diagnostic-input-manifest.json')['members']
    for key,record in d['used_native_inputs'].items():
        label,name=key.split('/',1)
        if label=='consistent':expected=archive['members']['cases/consistent/960/'+name]
        elif label=='control':expected=old['D1-runtime-symlink-repair/cases/control/960/'+name]
        elif label=='mesh':expected=config['constant/polyMesh/'+name]
        else:expected=historical['cfd-V2-fine-pressure015-900/900/p']
        require(record==expected,'Published native diagnostic provenance '+key)
    require(p['diagnostic_sha256']==sha('results/cfd/outlet-preparation-diagnostic.json') and p['baseline_D1C_summary_sha256']==sha('results/cfd/D1C-960-flow-summary.json') and p['baseline_native_archive_sha256']==archive['archive_sha256'] and p['rotor_STEP_sha256']==sha('V2-rotor.step'),'Proposed baseline identity')
    require(p['seed_fields']=={k:v for k,v in archive['members'].items() if k.startswith('cases/consistent/960/')},'Complete unchanged restart seed identity')
    validate_protocol(p,d,previous)
    hot=d['local317Pa_difference']['largest_pressure_difference_cells'][0]
    require(math.isclose(hot['consistent_minus_control_Pa'],hot['consistent_minus900_Pa']-hot['control_minus900_Pa']) and hot['cell']==288831 and math.isclose(hot['consistent_minus_control_Pa'],317.66885808),'Local pressure difference arithmetic')
    require(d['local317Pa_difference']['different_numerical_coupling_only_no_domain_difference_in_this_pair'],'Local coupling contrast must not imply domain causality')
    fo=(root/'parameters/outlet-common-functionObjects.dict').read_text()
    require(fo.count('operation orientedSum;')==1 and fo.count('operation volAverage;')==3 and fo.count('writeInterval 1;')==4,'Common functionObject statistics and cadence')
    print('Outlet preparation provenance, matched statistics and unexecuted budget passed')


if __name__=='__main__':
    from pathlib import Path
    verify(Path(__file__).resolve().parents[1])
