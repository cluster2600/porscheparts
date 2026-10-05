#!/usr/bin/env python3
"""Freeze a small original-code/config capsule; never run Docker or OpenFOAM."""
import argparse,json,shutil
from pathlib import Path
from prepare_d2_restart1000 import identity

SOURCES=['build_d2_completion_capsule.py','launch_d2_completion.py','run_d2_completion.py',
         'd2_completion_guards.py','complete_d2_comparison.py','prepare_d2_restart1000.py',
         'summarize_reference_flow.py','measurement_window.py','analyze_d2_result.py',
         'analyze_flow_balance.py','diagnose_and_merge_fv_cells.py']
CONFIGS={'completion-protocol.json':'parameters/D2-restart1000-protocol.json',
         'prepared-case-manifest.json':'parameters/D2-prepared-case-manifest.json',
         'previous-input-manifest.json':'parameters/D2-supervisor-input-manifest.json',
         'original-D2-protocol.json':'parameters/D2-executed-configurations/protocol.json',
         'checkpoint-audit.json':'results/runtime/D2-restart-checkpoint-audit.json'}


def build(root,output):
    output.mkdir(parents=True,exist_ok=False)
    for name in SOURCES:
        target=output/'source'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(root/'source'/name,target)
    for name,source in CONFIGS.items():
        target=output/'configs'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(root/source,target)
    manifest={'status':'fixed20_supervisor_prepared_not_launched','new_solver_launched':False,
              'files':{str(f.relative_to(output)):identity(f) for f in sorted(output.rglob('*')) if f.is_file()},
              'aggregate_wall_cap_seconds':240,'maximum_CPU':4,'memory_and_swap_GiB':5,
              'target_iteration':1020,'maximum_new_iterations':20,'current_control_replayed':False,
              'no_installation_or_new_access':True,'private_native_files_not_in_capsule':True}
    (output/'capsule-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Fixed20 capsule prepared; no solver or container launched')
    return manifest


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('root',type=Path);cli.add_argument('output',type=Path)
    args=cli.parse_args();build(args.root,args.output)
