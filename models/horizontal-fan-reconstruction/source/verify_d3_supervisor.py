#!/usr/bin/env python3
"""Verify frozen D3 preparation and actual CAD render; never launch a solver."""
import hashlib,json
from pathlib import Path
from build_d3_capsule import SOURCES
from d3_guards import LABELS,PHASES,GLOBAL_CAP,IMAGE,validate_plan,NUMERICAL


def verify(root):
    def read(name):return json.loads((root/name).read_text())
    def sha(name):return hashlib.sha256((root/name).read_bytes()).hexdigest()
    def need(condition,message):
        if not condition:raise ValueError(message)
    prefix='parameters/D3-supervisor-reviewed-capsule/'
    manifest=read(prefix+'capsule-manifest.json')
    actual={str(p.relative_to(root/prefix)) for p in (root/prefix).rglob('*') if p.is_file() and p.name!='capsule-manifest.json' and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    need(actual==set(manifest['files']),'Reviewed capsule exact file inventory')
    for name,identity in manifest['files'].items():
        p=root/prefix/name
        need(p.stat().st_size==identity['bytes'] and sha(prefix+name)==identity['sha256'],'Reviewed capsule payload identity: '+name)
    need(set(n.removeprefix('source/') for n in actual if n.startswith('source/'))==set(SOURCES),'Complete reviewed source dependency closure')
    for name in SOURCES:need(sha(prefix+'source/'+name)==sha('source/'+name),'Reviewed source must match live source: '+name)
    plan=read('parameters/D3-prepared-relaxation-protocol.json');validate_plan(plan)
    need(read(prefix+'configs/diagnostic-plan.json')==plan,'Original two-arm protocol unchanged')
    need((manifest['global_wall_cap_seconds'],manifest['maximum_CPU'],manifest['RAM_and_swap_limit_bytes'],manifest['new_solver_count_max'],manifest['iterations_per_arm'])==(360,4,5*1024**3,2,20),'Exact frozen supervisor caps')
    need(manifest['new_solver_launched'] is False and manifest['no_native_fields_in_capsule'],'No solver or native fields in published capsule')
    contract=read(prefix+'configs/supervisor-contract.json')
    need(contract['phase_caps_seconds']==PHASES and sum(PHASES.values())==GLOBAL_CAP and contract['existing_image']==IMAGE,'Single aggregate deadline and existing image')
    for flag in ['requires_explicit_resource_coordination_after_support_release','actual_container_inspection_before_solver_required','trusted_reviewed_capsule_manifest_SHA256_required_before_launch','source_mounts_read_only','archive_verified_within_global_deadline_required','no_foreign_process_or_service_stop','no_install_or_new_access']:need(contract[flag] is True,'Missing preparation gate: '+flag)
    audit=read('results/runtime/D3-supervisor-input-copy-audit.json')
    need(audit['capsule_manifest_identity']=={'bytes':(root/prefix/'capsule-manifest.json').stat().st_size,'sha256':sha(prefix+'capsule-manifest.json')},'Input-copy QA uses reviewed capsule')
    need(audit['audit_script_sha256']==sha('source/audit_d3_input_copy.py') and audit['runtime_copy_helper_sha256']==sha('source/run_d3.py'),'Copy-audit source identities')
    need(audit['all64_working_MPI1020_seed_files_verified'] and audit['both_serial1020_copies_verified'] and audit['working_arms_differences']==['system/fvSolution'],'Working-source copies differ only in pressure relaxation')
    need(audit['no_subprocess_solver_container_or_reconstruction_launched'] and audit['no_native1040_results_created'] and not audit['physical_validation_established'],'Copy QA must not be represented as execution')
    seeds={label+'/'+name:record for label in LABELS for name,record in plan['cases'][label]['native_MPI_seed_files'].items()}
    need(audit['native_MPI_seed_files']==seeds and len(seeds)==64,'All native partition seed identities')
    for label,protocol in audit['working_protocols'].items():
        need(label in LABELS and protocol['acceptance_all_required']==NUMERICAL and protocol['expected_actual_solver_iterations']==protocol['required_admission_sample_iterations']==list(range(1021,1041)),'Exact per-arm native20 window and unchanged criteria')
        need(protocol['new_iterations']==20 and protocol['expected_cell_count']==680596 and not protocol['physical_validation_established'] and not protocol['manufacturing_authorized'],'Original mesh and qualification scope')
    tests=read('results/runtime/D3-supervisor-offline-tests.json')
    need(tests['test_source_sha256']==sha('source/test_d3_supervisor.py') and tests['tests_run']==19 and tests['exit_status']==0 and not tests['native_solver_or_container_executed'],'Offline tests source and scope')
    for name,digest in tests['source_sha256'].items():need(digest==sha('source/'+name),'Tested source identity: '+name)
    render=read('results/assembly/fan-S1-assembly-and-V2-stock-study.json')
    need(render['script_sha256']==sha('source/render_s1_delivery.py') and render['PNG_sha256']==sha('results/assembly/fan-S1-assembly-and-V2-stock-study.png'),'Rendered real CAD output and source')
    for name,digest in render['dependency_sha256'].items():need(digest==sha('source/'+name),'Render dependency identity')
    for name,digest in render['source_STL_sha256'].items():need(digest==sha(name),'Real rendered STL identity: '+name)
    need(render['source_geometry_report_sha256']==sha('results/assembly/S1/geometry-report.json') and render['source_stock_report_sha256']==sha('results/lpbf/V2-stock-scenario/stock-report.json'),'Render source CAD reports')
    need(render['assembly_solids']==19 and len(render['source_STL_sha256'])==20 and render['same_native_CAD_coordinates_no_invented_geometry'] and render['render_units']=='mm' and render['diameter275mm_is_assumed_not_measured'] and render['stock_panel_not_installed_assembly'],'Render dimensions and coordinate scope')
    need(not render['physical_validation_established'] and not render['manufacturing_authorized'],'Real CAD image does not qualify physical part')
    print('D3 reviewed supervisor, independent input copies, offline tests and real S1 CAD view verified; no solve')


if __name__=='__main__':verify(Path(__file__).resolve().parents[1])
