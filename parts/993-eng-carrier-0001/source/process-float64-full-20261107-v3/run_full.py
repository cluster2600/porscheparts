"""Same-profile complete carrier calendar entrypoint; supports and machine jobs excluded."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import common

CONTROL_STATUS={
 'storage-controls.json':'full_index_storage_cap_and_source_bound_continuation_controls_passed',
 'math-controls.json':'finite_outward_bounds_match_exact_rational_geometry_and_section_controls',
 'lifecycle-controls.json':'actual_outer_sigterm_cleanup_control_passed',
 'current-controls.json':'current_full_calendar_source_and_worker_controls_passed',
 'result.json':'public_full_calendar_bounded_controls_passed'}


def admitted_controls(root, manifest_sha):
    root=Path(root).resolve(strict=True);records={}
    for name,status in CONTROL_STATUS.items():
        path=root/name;value=json.loads(path.read_text())
        if value.get('status')!=status or value.get('source_manifest_sha256')!=manifest_sha:
            raise ValueError('Required bounded preparation control differs: '+name)
        records[name]=dict(path=str(path),sha256=common.sha(path))
    storage=json.loads((root/'storage-controls.json').read_text())
    if not(storage['actual_next_layer_written_after_resume']and len(storage['refusals'])==17 and all(x['refused']for x in storage['refusals'])):
        raise ValueError('Complete storage/refusal control roster differs')
    current=json.loads((root/'current-controls.json').read_text())
    if not(current['complete_indices']==1034 and current['current_layer_calls']==1 and current['golden_array_and_npz_byte_parity']and current['original_and_independent_domain_audits_passed']and not current['full_calendar_executed']):
        raise ValueError('Current-source worker control differs')
    terminal=root/'supervision/terminal.json';value=json.loads(terminal.read_text())
    if not(value['actual_returncode']==0 and value['reason']=='complete'and value['prepared_sources_unchanged']and value['child_reaped']and value['owned_group_cleanup']['group_absent']):
        raise ValueError('Bounded preparation process closure differs')
    records['supervision-terminal']=dict(path=str(terminal),sha256=common.sha(terminal))
    return records


def main(args):
    expected,replay,old_args,original,paths,profile,repo=common.bindings(args)
    if not re.fullmatch(r'\d{3}',args.attempt):raise ValueError('Use an exact three-digit attempt identifier')
    values=[args.resume_marker,args.resume_sha256,args.prior_terminal,args.prior_terminal_sha256]
    if not(all(v is None for v in values)or all(v is not None for v in values)):
        raise ValueError('Continuation requires all four original pinned identities')
    resume=values[0]is not None
    controls=admitted_controls(args.controls_root,args.source_manifest_sha256)
    root=Path(args.output).resolve();args.output=str(root);private=root/'scientific'
    if not root.parent.is_dir()or shutil.disk_usage(root.parent).free<12*1024**3:
        raise ValueError('Existing output parent with at least12GiB free is required')
    pins={str(HERE/name):h for name,h in expected['bundle_sources_sha256'].items()}
    pins.update({str(repo/name):h for name,h in expected['repository_sources_sha256'].items()})
    pins[str(HERE/'source-manifest.json')]=args.source_manifest_sha256
    pins[str(Path(args.input_manifest).resolve())]=common.sha(args.input_manifest)
    source={str(paths[name]):h for name,h in original['private_inputs_sha256'].items()}
    pins.update(source)
    contract=dict(schema='current-carrier-public-full-calendar-v1',source_manifest_sha256=args.source_manifest_sha256,
                  historical_full_contract_sha256=expected['historical_full_contract_sha256'],
                  indices=list(range(1034)),heights_mm=[(i+.5)*.06 for i in range(1034)],layer_height_mm=.06,
                  private_output_root=str(private),source_sha256=pins,geometry_source_sha256=source,
                  driver_sha256=common.sha(HERE/'full_driver.py'),controls=controls,
                  golden_arrays_path=str(paths['golden_arrays']),golden_arrays_sha256=common.sha(paths['golden_arrays']),
                  python_path=sys.executable,python_sha256=common.sha(sys.executable),
                  wall_limit_seconds=7200,aggregate_RSS_limit_bytes=8*1024**3,
                  scientific_output_cap_bytes=4*1024**3,storage_reserve_bytes=8*1024**3,
                  initial_free_bytes_required=12*1024**3,workers=1,maximum_pending_layers=2,threads=1,
                  fresh_indexed_calls=1034,fresh_reference_calls=1,fresh_total_worker_calls=1035)
    if resume:
        if not private.is_dir()or json.loads((root/'contract.json').read_text())!=contract:
            raise ValueError('Continuation must retain the exact source contract and original output location')
        if (private/'full-result.json').exists():raise ValueError('Completed full output must not be resumed')
    else:
        root.mkdir(mode=0o700,exist_ok=False);common.write(root/'contract.json',contract)
    contract_sha=common.sha(root/'contract.json')
    runroot=root/'runs'/('attempt-'+args.attempt)
    runroot.mkdir(parents=True,exist_ok=False)
    command=[sys.executable,'-I','-B','-S',str(HERE/'full_driver.py')]
    for name in ['repository_root','input_manifest','source_manifest_sha256','output']:
        command+=['--'+name.replace('_','-'),str(getattr(args,name))]
    command+=['--contract-sha256',contract_sha,'--run-root',str(runroot)]
    if resume:
        for name,value in zip(['resume-marker','resume-sha256','prior-terminal','prior-terminal-sha256'],values):command+=['--'+name,value]
    common.write(runroot/'start-intent.json',dict(command=command,contract_sha256=contract_sha,
                 wall_limit_seconds=7200,aggregate_RSS_limit_bytes=8*1024**3,
                 scientific_output_cap_bytes=4*1024**3,storage_reserve_bytes=8*1024**3,
                 supports_or_machine_job=False,new_paid_action=False))
    def verify():
        common.bindings(args)
        if common.sha(root/'contract.json')!=contract_sha:raise ValueError('Execution contract changed')
        for path,h in pins.items():
            if common.sha(path)!=h:raise ValueError('Bound full-calendar source changed')
        for row in controls.values():
            if common.sha(row['path'])!=row['sha256']:raise ValueError('Bound control receipt changed')
    guard=common.module('qualified_public_full_guard',HERE/'guard.py')
    report=guard.supervise(command,runroot,verify,root.parent,contract_sha)
    print(json.dumps(report),flush=True)
    if report['reason']!='complete'or report['actual_returncode']!=0:
        raise RuntimeError('Full-calendar replay did not complete; original outputs and terminal retained')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['repository-root','input-manifest','source-manifest-sha256','controls-root','output']:parser.add_argument('--'+name,required=True)
    parser.add_argument('--attempt',default='001')
    for name in ['resume-marker','resume-sha256','prior-terminal','prior-terminal-sha256']:parser.add_argument('--'+name)
    main(parser.parse_args())
