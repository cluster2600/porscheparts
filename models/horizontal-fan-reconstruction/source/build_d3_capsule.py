#!/usr/bin/env python3
"""Freeze original D3 supervisor/configs and native-input identities; no solve."""
import argparse,json,re,shutil,time
from pathlib import Path
from d3_guards import IMAGE,LABELS,GLOBAL_CAP,PHASES,validate_plan,verify_manifest,digest_file

SOURCES=['build_d3_capsule.py','launch_d3.py','run_d3.py','analyze_d3.py','d3_guards.py',
         'd2_completion_guards.py','prepare_d2_restart1000.py','summarize_reference_flow.py',
         'measurement_window.py','analyze_flow_balance.py','analyze_d2_result.py','audit_d3_checkpoint.py','diagnose_and_merge_fv_cells.py']


def build(root,prepared,previous,selections,output):
    started=time.monotonic();deadline=started+120
    root,prepared,previous,selections=[p.resolve(strict=True) for p in [root,prepared,previous,selections]];output=output.resolve()
    if output.exists() or any(output==p or p in output.parents or output in p.parents for p in [prepared,previous,root]):raise ValueError('Fresh private capsule directory required')
    plan_file=root/'parameters/D3-prepared-relaxation-protocol.json';plan=json.loads(plan_file.read_text());validate_plan(plan)
    if digest_file(prepared/'preparation-report.json',deadline)!=digest_file(plan_file,deadline):raise ValueError('Previously sealed preparation differs')
    prepared_files={'preparation-report.json':digest_file(plan_file,deadline)}
    for label in LABELS:
        for name,record in plan['source_files'].items():
            if name.startswith('system/'):record=plan['cases'][label]['system_files'][name.split('/')[-1]]
            prepared_files[label+'/'+name]=record
    verify_manifest(prepared,prepared_files,deadline)
    preserved=json.loads((root/'results/runtime/D2-completion-native-archive-verification.json').read_text())
    previous_files={name.removeprefix('extended/'):record for name,record in preserved['members'].items()
                    if name.startswith(('extended/1020/','extended/postProcessing/commonOutletFlux/','extended/postProcessing/commonPressureBandMean/','extended/postProcessing/rotorForces/'))
                    or name in ['extended/private-maps.npz','extended/reference-protocol.json']}
    if len([n for n in previous_files if n.startswith('1020/')])!=8:raise ValueError('Preserved complete serial1020 fields/time required')
    for name,record in previous_files.items():
        if (previous/name).is_symlink() or digest_file(previous/name,deadline)!=record:raise ValueError('Independent preserved input changed')
    original=json.loads((root/'results/runtime/D2-native-archive-verification.json').read_text())
    selected_identity=original['members']['cases/common-selections-private.npz']
    if digest_file(selections,deadline)!=selected_identity:raise ValueError('Original common selections differ')
    output.mkdir(parents=True)
    for name in SOURCES:
        target=output/'source'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(root/'source'/name,target)
    configs={'diagnostic-plan.json':plan,'prepared-inputs.json':prepared_files,
             'previous-inputs.json':{'files':previous_files,'selections_identity':selected_identity},
             'supervisor-contract.json':{'status':'prepared_offline_only_no_native_execution','existing_image':IMAGE,
                'global_wall_cap_seconds':GLOBAL_CAP,'phase_caps_seconds':PHASES,'new_solver_count_max':2,
                'shared_native_checkpoint':1020,'target_iteration':1040,'new_iterations_per_arm':20,
                'requires_explicit_resource_coordination_after_support_release':True,
                'actual_container_inspection_before_solver_required':True,
                'trusted_reviewed_capsule_manifest_SHA256_required_before_launch':True,
                'source_mounts_read_only':True,'archive_verified_within_global_deadline_required':True,
                'no_foreign_process_or_service_stop':True,'no_install_or_new_access':True}}
    (output/'configs').mkdir()
    for name,data in configs.items():(output/'configs'/name).write_text(json.dumps(data,indent=2)+'\n')
    manifest={'status':'D3_exact_supervisor_prepared_not_launched','new_solver_launched':False,
              'files':{str(f.relative_to(output)):digest_file(f,deadline) for f in sorted(output.rglob('*')) if f.is_file()},
              'global_wall_cap_seconds':GLOBAL_CAP,'maximum_CPU':4,'RAM_and_swap_limit_bytes':5*1024**3,
              'new_solver_count_max':2,'iterations_per_arm':20,'no_native_fields_in_capsule':True,
              'elapsed_preparation_seconds':time.monotonic()-started}
    (output/'capsule-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('D3 exact supervisor capsule prepared; no solver/container launched');return manifest


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ['root','prepared','previous','selections','output']:cli.add_argument(name,type=Path)
    a=cli.parse_args();build(a.root,a.prepared,a.previous,a.selections,a.output)
