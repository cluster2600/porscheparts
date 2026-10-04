#!/usr/bin/env python3
"""Single fixed20 native stage, archive in the same isolated240s lot, no retry."""
import json,os,re,resource,shutil,subprocess,sys,time
from pathlib import Path
from d2_completion_guards import remaining,validate_plan,check_complete20,archive_private,digest_file


def run(prepared,previous,selections,capsule,output):
    started=time.monotonic();deadline=float(os.environ['FAN_D2_COMPLETION_DEADLINE'])
    release=os.environ['FAN_D2_COMPLETION_RELEASE'];os.nice(10)
    if sys.platform!='linux' or not Path('/opt/openfoam13').is_dir() or not release.strip():raise ValueError('Coordinated existing native runtime required')
    if deadline-started>240 or deadline<=started:raise ValueError('Fresh frozen240s aggregate deadline required')
    commands=[];status='failed_or_partial_no_retry';error=None;phase='isolation_gate';archive=None
    case=output/'extended';finish_by=deadline-55
    def command(args,log,cap):
        limit=min(cap,int(remaining(finish_by)))
        if limit<1:raise TimeoutError('No stage budget remains')
        t=time.monotonic()
        with (case/log).open('x') as stream:
            code=subprocess.run(['timeout','--signal=TERM','--kill-after=3',str(limit),*args],cwd=case,stdout=stream,stderr=subprocess.STDOUT).returncode
        commands.append({'args':args,'log':log,'exit_status':code,'wall_cap_seconds':limit,'wall_seconds':time.monotonic()-t})
        if code:raise RuntimeError('Owned stage command failed or timed out: '+log)
    try:
        # Host writes this only after docker inspect confirms the actual caps/mounts.
        gate_deadline=min(started+10,finish_by)
        while not (output/'isolation-admitted.json').exists():
            remaining(gate_deadline);time.sleep(.05)
        gate=json.loads((output/'isolation-admitted.json').read_text())
        if not gate['actual_isolation_verified'] or gate['aggregate_deadline_monotonic']!=deadline:raise ValueError('Actual isolation not admitted')
        phase='identity_and_copy';plan=json.loads((capsule/'configs/completion-protocol.json').read_text());validate_plan(plan)
        manifest=json.loads((capsule/'capsule-manifest.json').read_text())
        for name,record in manifest['files'].items():
            if digest_file(capsule/name,finish_by)!=record:raise ValueError('Frozen capsule changed')
        seeds=json.loads((capsule/'configs/prepared-case-manifest.json').read_text())['files']
        actual={str(p.relative_to(prepared)) for p in prepared.rglob('*') if p.is_file()}
        if actual!=set(seeds):raise ValueError('Prepared source file coverage differs')
        case.mkdir(exist_ok=False)
        for name,record in seeds.items():
            if digest_file(prepared/name,finish_by)!=record:raise ValueError('Prepared source changed: '+name)
            target=case/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(prepared/name,target)
            if digest_file(target,finish_by)!=record:raise ValueError('Private work copy changed')
        prior=json.loads((capsule/'configs/previous-input-manifest.json').read_text())
        for name,record in prior['files'].items():
            if digest_file(previous/name,finish_by)!=record:raise ValueError('Reused native input changed: '+name)
        if digest_file(selections,finish_by)!=prior['selections_identity']:raise ValueError('Common original selections changed')
        if time.monotonic()>deadline-210:raise TimeoutError('Setup admission exceeded frozen30s share')
        shutil.copytree(capsule,output/'used-capsule')
        (case/'source-identity-verification.json').write_text(json.dumps({'all_prepared_and_prior_inputs_verified':True,'read_only_control_reused':True,'no_redecomposition_or_regridding':True},indent=2)+'\n')
        phase='solver';command(plan['future_owned_commands_only'][0],'log.foamRun',110)
        steps=check_complete20((case/'log.foamRun').read_text())
        phase='reconstruction';command(plan['future_owned_commands_only'][1],'log.reconstructPar',25)
        phase='analysis';command(['python3','-B',str(capsule/'source/complete_d2_comparison.py')],'log.analysis',30)
        status='completed_exact20_no_retry'
    except Exception as exc:
        error=type(exc).__name__+': '+str(exc)
    finally:
        receipt={'status':status,'phase':phase,'error':error,'commands':commands,
                 'new_cases':['extended'],'restart_iteration':1000,'target_iteration':1020,
                 'maximum_new_iterations':20,'current_control_replayed':False,'no_retry_or_further_continuation':True,
                 'wall_seconds_before_preservation':time.monotonic()-started,
                 'aggregate_wall_cap_seconds':240,'child_peak_RSS_KiB_not_aggregate':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                 'coordinated_release':release,'native_fields_and_archive_private':True,'physical_validation_established':False}
        (output/'execution-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        try:
            archive=archive_private(output,min(time.monotonic()+45,deadline-10))
        except Exception as exc:
            receipt['preservation_error']=type(exc).__name__+': '+str(exc)
            receipt['native_files_remain_on_disk_even_if_archive_partial']=True
            (output/'preservation-failure.json').write_text(json.dumps(receipt,indent=2)+'\n')
        (output/'preservation-receipt.json').write_text(json.dumps({'archive_all_members_verified':bool(archive),'aggregate_remaining_seconds':deadline-time.monotonic(),'raw_native_outputs_retained':True,'no_retry':True},indent=2)+'\n')
    return 0 if status=='completed_exact20_no_retry' and archive else 2


if __name__=='__main__':
    raise SystemExit(run(Path('/prepared'),Path('/previous'),Path('/selections.npz'),Path('/capsule'),Path('/run')))
