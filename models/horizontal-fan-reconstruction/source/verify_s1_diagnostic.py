#!/usr/bin/env python3
"""Cross-check October5 preparation and CAD evidence without running solvers."""
import csv,hashlib,json,math
from assembly_interface_gate import evaluate
from prepare_d3_relaxation_pair import changed_system


def verify(root):
    read=lambda n:json.loads((root/n).read_text())
    sha=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
    def need(condition,message):
        if not condition:raise ValueError(message)
    old=read('results/runtime/D2-native-archive-verification.json')['members']
    completed=read('results/runtime/D2-completion-native-archive-verification.json')
    d=read('results/cfd/D2-establishment-diagnostic.json')
    need(d['analysis_script_sha256']==sha('source/diagnose_d2_establishment.py'),'Diagnostic source identity')
    for name,value in d['dependencies_sha256'].items():need(value==sha('source/'+name),'Diagnostic dependency identity')
    meshprep=read('results/cfd/D2-mesh-preparation.json')
    for name,entry in d['source_identity'].items():
        if name.startswith('extended/960/'):
            need(entry['sha256']==meshprep['initial_fields']['extended'][name.split('/')[-1]]['initialized_sha256'],'Original960 initializer identity')
        else:need(entry in list(old.values())+list(completed['members'].values()),'Preserved native archive input identity: '+name)
    need(not d['new_solver_launched'] and not d['geometry_or_criteria_changed'] and not d['physical_validation_established'],'Diagnostic qualification scope')
    need(d['native_geometry_volume_check']['positive_cells']==680596 and d['native_geometry_volume_check']['maximum_core_volume_difference_from_prior_independent_values_m3']<1e-20,'Independent native geometry volume check')
    need(d['linear_solver_diagnostic']['pressure_solves']==180 and [x['iteration'] for x in d['linear_solver_diagnostic']['first_p_initial_by_iteration']]==list(range(961,1021)),'Exactly60 complete archived iteration blocks')
    need(d['physical_time_proxies']['SIMPLE_iterations_are_not_physical_time'] and d['courant_cost_screen']['not_selected_transient_timestep_or_physical_validation'],'Physical time qualification')
    plan=read('parameters/D3-prepared-relaxation-protocol.json');prior=read('parameters/D2-restart1000-protocol.json')
    need(plan['preparer_sha256']==sha('source/prepare_d3_relaxation_pair.py') and plan['diagnostic_report_sha256']==sha('results/cfd/D2-establishment-diagnostic.json'),'D3 preparation source identity')
    for name,value in plan['dependencies_sha256'].items():need(value==sha('source/'+name),'D3 preparer dependency identity')
    need(plan['source_archive_sha256']==completed['archive_identity']['sha256'] and plan['source_archive_verification_sha256']==sha('results/runtime/D2-completion-native-archive-verification.json'),'D3 independently preserved source')
    need((plan['restart_iteration'],plan['target_iteration'],plan['new_iterations_per_case'],plan['solver_count_max'])==(1020,1040,20,2),'Fixed equal-work experiment')
    need(plan['original_numerical_acceptance_all_required']==prior['original_numerical_acceptance_all_required'],'No relaxed CFD admission criteria')
    need(plan['no_solver_container_or_reconstruction_launched'] and not plan['future_supervised_launcher_admitted'] and plan['no_automatic_extension_or_retry'],'Preparation cannot claim executed or supervised admission')
    budget=plan['budget_requires_resource_coordination_before_launch']
    need(budget['aggregate_wall_cap_seconds']==360 and sum(budget['phase_caps_seconds'].values())==360 and budget['CPU_max']==4 and budget['RAM_and_swap_limit_bytes']==5*1024**3,'Prospective bounded resource contract')
    for name,entry in plan['source_files'].items():need(entry==completed['members']['extended/'+name],'D3 frozen source inventory')
    a,b=plan['cases']['control015'],plan['cases']['candidate005']
    need(a['native_MPI_seed_files']==b['native_MPI_seed_files'] and len(a['native_MPI_seed_files'])==32,'Identical complete native seeds')
    control=(root/'parameters/D2-restart1000-controlDict').read_text();solution=(root/'parameters/D2-executed-configurations/system/fvSolution').read_text()
    for label,record in plan['cases'].items():
        expected=changed_system(control,solution,record['pressure_relaxation'])
        for name,text in zip(['controlDict','fvSolution'],expected):
            path='parameters/D3-prepared-configurations/'+label+'/'+name
            need((root/path).read_text()==text and sha(path)==record['system_files'][name]['sha256'],'D3 exact declared changes: '+label+'/'+name)
    contract=read('parameters/assembly-interface-contract.json');g=read('results/assembly/S1/geometry-report.json')
    need(g['interface_gate']==evaluate(contract,g) and not g['interface_gate']['functional_completion_allowed'],'Independent interface contract')
    need(g['builder_sha256']==sha('source/build_assembly_study.py') and g['parameters_sha256']==sha('parameters/assembly-study-S1.json') and g['interface_contract_sha256']==sha('parameters/assembly-interface-contract.json'),'S1 builder and inputs')
    need(g['source_assembly_sha256']==sha('V2-assembly.step') and g['source_rotor_sha256']==sha('V2-rotor.step'),'Unchanged source V2 geometry')
    need(g['assembly_step_sha256']==sha('results/assembly/S1/S1-assembly.step') and len(g['components'])==7,'S1 CAD assembly identity')
    solidcount=0
    for name,component in g['components'].items():
        prefix='results/assembly/S1/geometry/'+name
        need(component['brep_valid'] and component['volume_mm3']>0 and component['step_roundtrip_relative_volume_error']<=component['STEP_volume_representation_screen_relative']==1e-6,'S1 BRep representation checks')
        need(sha(prefix+'.step')==component['step_sha256'] and sha(prefix+'.stl')==component['stl_sha256'],'S1 component geometry identity')
        for mesh,digest in component['separate_solid_STL_sha256'].items():need(sha('results/assembly/S1/geometry/'+mesh)==digest,'S1 solid tessellation identity')
        solidcount+=component['solids']
    need(solidcount==19 and g['layout_clearance_checks']['original_plenum_intersection_volume_mm3']<1e-5,'S1 study layout checks')
    need(g['derived_sizing']['unconverged_diagnostic_Q_report_sha256']==sha('results/cfd/D2-establishment-diagnostic.json'),'Conditional Q source identity')
    stock=read('results/lpbf/V2-stock-scenario/stock-report.json')
    need(stock['source_rotor_sha256']==sha('V2-rotor.step') and stock['builder_sha256']==sha('source/prepare_v2_manufacturing_stock.py') and stock['parameters_sha256']==g['parameters_sha256'],'Stock input identities')
    need(stock['blank_step_sha256']==sha('results/lpbf/V2-stock-scenario/V2-stock-scenario.step') and stock['blank_stl_sha256']==sha('results/lpbf/V2-stock-scenario/V2-stock-scenario.stl'),'Stock CAD output identities')
    need(stock['brep_valid'] and stock['solids']==1 and stock['step_roundtrip_relative_volume_error']<1e-7 and stock['stock_blank_volume_mm3']>stock['original_volume_mm3'],'Connected stock BRep and roundtrip')
    screen=read('results/lpbf/V2-stock-orientation-screen.json')
    need(screen['stock_report_sha256']==sha('results/lpbf/V2-stock-scenario/stock-report.json') and screen['script_sha256']==sha('source/screen_v2_stock.py') and len(screen['orientations'])==6 and screen['relative_STL_BRep_volume_error']<.005,'Stock orientation screening identity and representation')
    need(not screen['process_qualification_established'] and not screen['support_solids_toolpath_or_thermal_history_generated'] and not screen['manufacturing_authorized'],'No qualified LPBF result inferred')
    usd=read('omniverse/S1-layout.json');validation=read('omniverse/S1-layout-validation.json')
    need(usd['asset_sha256']==sha('omniverse/S1-layout.usda')==validation['asset_sha256'] and usd['plot_sha256']==sha('results/assembly/S1-layout.png'),'Actual geometry USD and render identity')
    need(usd['script_sha256']==sha('source/export_s1_layout.py') and usd['source_geometry_report_sha256']==sha('results/assembly/S1/geometry-report.json'),'Actual geometry export provenance')
    text=(root/'omniverse/S1-layout.usda').read_text()
    need(len(usd['linked_input_sha256'])==5,'All stage geometry, interface, CFD and manufacturing links required')
    for name,digest in usd['linked_input_sha256'].items():
        need(name in text and digest==hashlib.sha256((root/'omniverse'/name).read_bytes()).hexdigest(),'USD actual linked evidence identity')
    need(len(usd['meshes'])==len(validation['meshes'])==19 and usd['metersPerUnit']==validation['metersPerUnit']==1 and usd['upAxis']==validation['upAxis']=='Z','USD stage layout')
    need(all(x['maximum_float32_coordinate_error_m']<=x['float32_representation_bound_m'] for x in usd['meshes'].values()) and usd['all_coordinates_checked'],'USD coordinate representation')
    need(not usd['NVIDIA_SimReady_qualified'] and not usd['digital_twin_validated'] and not validation['complete_generic_validation_established'] and not validation['validator_findings'],'OpenUSD qualification and missing shader rule preserved')
    packet=read('results/assembly/S1-review-packet.json')
    need(packet['script_sha256']==sha('source/build_s1_review_packet.py'),'Review packet builder identity')
    for name,digest in packet['input_sha256'].items():need(digest==sha(name),'Review packet dependency identity')
    sheet='results/assembly/S1-interface-measurement-sheet.csv'
    need(packet['measurement_sheet_sha256']==sha(sheet),'Measurement sheet identity')
    with (root/sheet).open() as stream:rows=list(csv.DictReader(stream))
    need(len(rows)==packet['measurement_rows']==52 and all(not value for row in rows for key,value in row.items() if key not in ['interface','feature']),'Unmeasured physical data must stay blank')
    need(not g['manufacturing_authorized'] and not stock['manufacturing_authorized'] and not packet['manufacturing_authorized'],'No manufacturing release')
    print('S1/D3 preserved inputs, CAD, qualification guards and review packet verified')
