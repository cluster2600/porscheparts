#!/usr/bin/env python3
"""Verify cross-stage hashes, completed fields and explicit qualification limits."""
import hashlib
import json


def verify(root):
    def read(name):return json.loads((root/name).read_text())
    def sha(name):return hashlib.sha256((root/name).read_bytes()).hexdigest()
    def require(condition,message):
        if not condition:raise ValueError(message)
    comparison=read('results/lpbf/manufacturing-comparison.json')
    require(len(comparison['cases'])==12,'Twelve declared manufacturing scenarios required')
    require(not any(comparison[k] for k in ['mesh_independence_established','process_calibrated','fabrication_validated','service_validated']),'Unsupported manufacturing qualification')
    for case in comparison['cases']:
        label=case['case'].removeprefix('manufacturing-')
        variant=label.split('-')[0]
        name='results/lpbf/'+label+'-summary.json'
        summary=read(name)
        require(sha(name)==case['summary_sha256'],'Manufacturing summary changed: '+label)
        require(case['source_step_sha256']==sha(variant+'-rotor.step'),'Manufacturing CAD identity: '+label)
        require([s['state'] for s in summary['states']]==['attached','released'],'Both physical field states required')
        require(all(s['nodes']==summary['assumptions']['nodes'] and s['integration_points']==4*summary['assumptions']['tetrahedra'] for s in summary['states']),'Native field coverage incomplete: '+label)
        require(not summary['process_calibrated'] and not summary['distortion_prediction_qualified'] and not summary['manufacturing_authorized'],'Unsupported native manufacturing qualification')
        prep='results/lpbf/'+label+'-preparation.json'
        require(sha(prep)==summary['file_sha256']['preparation.json'],'Manufacturing preparation identity')
    for variant in ['R0','V5']:
        control=comparison['native_zero_and_linear_scaling_controls'][variant]
        require(control['passed'] and control['relative_full_vs_twice_half_native_displacement_error']<=control['limits']['relative_scaling'] and control['maximum_zero_strain_displacement_mm']<=control['limits']['zero_displacement_mm'] and control['maximum_zero_strain_elastic_stress_MPa']<=control['limits']['zero_stress_MPa'],'Zero/linear native-field control failed')
        bundle=read('results/lpbf/'+variant+'-manufacturing-native.json')
        export=read('omniverse/'+variant+'-manufacturing-release.json')
        summary=read('results/lpbf/'+variant+'-diagonal-edge-summary.json')
        require(bundle['field_bundle_sha256']==sha('results/lpbf/'+variant+'-manufacturing-native.npz')==export['field_bundle_sha256'],'Native field bundle identity')
        require(bundle['source_field_sha256']==summary['file_sha256']['rotor.frd']==export['source_field_sha256'],'Export source field identity')
        require(bundle['summary_sha256']==sha('results/lpbf/'+variant+'-diagonal-edge-summary.json'),'Export source summary identity')
        require(export['asset_sha256']==sha('omniverse/'+variant+'-manufacturing-release.usda'),'Actual-field USD identity')
        require(export['plot_sha256']==sha('results/lpbf/'+variant+'-manufacturing-release.png'),'Actual-field render identity')
        require(export['asset_meters_per_unit']==1 and export['up_axis']=='Z' and export['asset_deformation_scale']==1 and not export['NVIDIA_SimReady_qualified'],'USD units/scale/qualification')
        boundary=read('results/lpbf/'+variant+'-native-boundary-verification.json')
        require(boundary['field_bundle_sha256']==bundle['field_bundle_sha256'] and boundary['every_edge_has_two_opposite_orientations'] and boundary['minimum_subtriangle_area_mm2']>0 and boundary['relative_linearized_boundary_volume_error']<=boundary['volume_representation_bound_relative'] and not boundary['physical_validation_established'],'Native oriented boundary and CAD-volume check')
        validation=read('omniverse/'+variant+'-manufacturing-validation.json')
        require(validation['asset_sha256']==export['asset_sha256'] and validation['meshes'][0]['all_edges_incident_to_two_triangles'],'USD boundary topology')
        coordinates=read('results/lpbf/'+variant+'-USD-field-coordinate-verification.json')
        require(coordinates['asset_sha256']==export['asset_sha256'] and coordinates['all_boundary_coordinates_checked']==bundle['boundary_nodes'] and coordinates['maximum_actual_USD_storage_error_mm']<=coordinates['representation_precision_bound_mm'] and coordinates['precision_bound_is_not_manufacturing_acceptance_limit'],'Actual float32 USD coordinate verification')
    benchmark=read('results/lpbf/native-analytic-benchmark-independent-verification.json')
    require(benchmark['status']=='passed' and benchmark['native_field_coverage_complete'] and benchmark['maximum_displacement_error_mm']<=benchmark['displacement_limit_mm'] and benchmark['maximum_released_stress_component_MPa']<=benchmark['stress_limit_MPa'] and not benchmark['process_calibration_established'],'Independent native analytical benchmark')
    for variant in ['R0','V2']:
        for grid in ['h7','h5p6']:
            base='results/cfd/'+variant+'-common-'+grid
            gate=read(base+'-independent-mesh-gate.json')
            require(gate['accepted_for_bounded_pilot'] and all(c['Mesh_OK'] and c['failed_checks']==0 for c in gate['checks'].values()),'Independent CFD gate failed: '+base)
            mesh=read(base+'-mesh-report.json')
            require(mesh['minimum_Gauss4_jacobian']>0 and not mesh['CAD_domain_changed'],'Mesh positivity/CAD identity')
            if grid=='h7':
                flow=read(base+'-flow-summary.json');protocol='parameters/'+variant+'-common-h7-protocol.json'
            else:
                for phase in [150,300,450,600]:
                    flow=read('results/cfd/'+variant+'-fine-150steps-phase'+str(phase)+'-summary.json')
                    protocol='parameters/'+variant+'-fine-150steps-phase'+str(phase)+'-protocol.json'
                    require(flow['first_iteration']==phase-149 and flow['expected_first_iteration']==phase-149,'Actual continuation must start at its frozen checkpoint')
                    require(flow['file_sha256']['reference-protocol.json']==sha(protocol),'Frozen phase protocol identity')
                end_iteration=750 if variant=='R0' else 900
                label=variant+'-fine-pressure015-'+str(end_iteration)
                flow=read('results/cfd/'+label+'-summary.json');protocol='parameters/'+label+'-protocol.json'
                initial=600 if variant=='R0' else 750
                require(flow['first_iteration']==initial+1 and flow['expected_first_iteration']==initial+1,'Actual numerical sensitivity checkpoint')
                previous_name='parameters/R0-fine-150steps-phase600-protocol.json' if variant=='R0' else 'parameters/V2-fine-continuation750-protocol.json'
                previous=read(previous_name);next_protocol=read(protocol)
                require(previous['acceptance_all_required']==next_protocol['acceptance_all_required'] and next_protocol['previous_frozen_protocol_sha256']==sha(previous_name),'Numerical sensitivity must preserve original thresholds and previous protocol')
                require(next_protocol['numerical_pressure_relaxation_before']==.25 and next_protocol['numerical_pressure_relaxation_after']==.15,'Matched pressure relaxation must be explicit')
            require(flow['file_sha256']['reference-protocol.json']==sha(protocol),'Final frozen flow protocol identity')
            admitted=all(flow['criteria_checks'].values())
            require((flow['status']=='reference_pilot_admitted_numerically')==admitted,'Flow status must reflect every original criterion')
            if grid=='h7':require(admitted,'Common coarse operating point must be admitted')
            require(flow['criteria_checks']['complete_finite_fields'] and flow['criteria_checks']['finite_measurements'] and flow['criteria_checks']['declared_flow_direction'],'Actual finite final fields required even for a nonconverged report')
            require(all(n==mesh['volume_elements'] for n in flow['final_field_cell_counts'].values()),'Complete CFD field/mesh count identity')
            require(not any(flow[k] for k in ['aerodynamic_mesh_independence_established','physical_validation_established','performance_improvement_proven']),'Unsupported flow qualification')
            balance=read(base+'-balance-v4.json')
            require(balance['analysis_script_sha256']==sha('source/analyze_flow_balance.py') and balance['pressure_torque_recomputation_relative_error']<1e-6 and balance['maximum_rotor_wall_velocity_difference_from_omega_cross_r_m_s']<1e-5,'Independent torque and wall velocity checks')
            require(balance['port_energy_ratio_is_not_qualified_fan_efficiency'] and not balance['energy_balance_physically_qualified'],'Unqualified port energy ratio')
    mechanics=read('results/mechanics/three-variant-comparison.json')
    require(len(mechanics['records'])==6 and not mechanics['safe_rpm_or_fatigue_qualified'] and not mechanics['local_stress_convergence_established'],'Mechanical comparison scope')
    for name,digest in mechanics['source_sha256'].items():require(sha(name)==digest,'Mechanical comparison input identity')
    plot=read('results/mechanics/V2-fields.json')
    require(plot['source_summary_sha256']==sha('results/mechanics/mesh-V2-h3p6.json') and plot['source_fields_sha256']==sha('results/mechanics/mesh-V2-h3p6.npz') and plot['png_sha256']==sha('results/mechanics/V2-fields.png') and plot['full_color_maxima_retained'],'Actual V2 mechanical render identity')
    r=read('results/cfd/matched-grid-comparison.json')
    for name,digest in r['source_sha256'].items():require(sha(name)==digest,'Flow comparison input identity')
    require(r['paired_fine_grid_admitted']==all(r['records'][v+'-h5p6']['all_frozen_flow_gates_passed'] for v in ['R0','V2']) and (r['V2_vs_R0_percent_change']['h5p6'] is not None)==r['paired_fine_grid_admitted'],'Unadmitted fine results must not be classified as an admitted comparison')
    require(not r['grid_independence_established'] and not r['physical_validation_established'],'Comparison qualification')
    archive=read('results/runtime/native-archive-verification.json')
    require(archive['all_members_verified'] and archive['local_transferred_archive_identity_verified'] and not archive['raw_scan_included'] and archive['private_archive_not_published'] and archive['archive_source_script_sha256']==sha('source/archive_native_evidence.py'),'Private native archive verification and scope')
    print('Continuation native-field identities and validation boundaries passed')
