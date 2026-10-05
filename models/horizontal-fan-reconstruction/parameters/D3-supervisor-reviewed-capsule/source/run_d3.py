#!/usr/bin/env python3
"""Two sequential owned native20 solves, one global360s deadline and preservation."""
import json,os,resource,shutil,signal,subprocess,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
from d3_guards import LABELS,GLOBAL_CAP,PHASES,remaining,phase_deadline,validate_plan,verify_manifest,digest_file,archive_private,check_complete20


def native_command(args,cwd,log,deadline,cap):
    started=time.monotonic();limit=remaining(deadline,3)
    if limit<.1:raise TimeoutError('Insufficient owned-command cleanup reserve')
    proc=None
    with log.open('x') as stream:
        proc=subprocess.Popen(args,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        try:code=proc.wait(timeout=limit)
        except BaseException:
            if proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=min(1,remaining(deadline)))
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=min(1,remaining(deadline)))
            raise
    record={'args':args,'log':str(log.name),'exit_status':code,'phase_wall_cap_seconds':cap,'wall_seconds':time.monotonic()-started}
    if code:raise RuntimeError('Owned command failed: '+log.name+' exit='+str(code))
    return record


def copy_inputs(prepared,previous,selections,capsule,output,deadline):
    plan=json.loads((capsule/'configs/diagnostic-plan.json').read_text());validate_plan(plan)
    capsule_manifest=json.loads((capsule/'capsule-manifest.json').read_text())
    verify_manifest(capsule,capsule_manifest['files'],deadline,excluded=['capsule-manifest.json'])
    manifest=json.loads((capsule/'configs/prepared-inputs.json').read_text());verify_manifest(prepared,manifest,deadline)
    prior=json.loads((capsule/'configs/previous-inputs.json').read_text())
    for name,record in prior['files'].items():
        if digest_file(previous/name,deadline)!=record:raise ValueError('Preserved input identity differs')
    if digest_file(selections,deadline)!=prior['selections_identity']:raise ValueError('Common selections changed')
    base=json.loads((previous/'reference-protocol.json').read_text())
    if base['acceptance_all_required']!=plan['original_numerical_acceptance_all_required']:raise ValueError('Original numerical acceptance criteria changed')
    for label in LABELS:
        case=output/label;case.mkdir(exist_ok=False)
        for name,record in manifest.items():
            prefix=label+'/'
            if not name.startswith(prefix):continue
            target=case/name.removeprefix(prefix);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(prepared/name,target)
            if digest_file(target,deadline)!=record:raise ValueError('Working native input copy changed')
        for name,record in prior['files'].items():
            if name.startswith('1020/'):
                target=case/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(previous/name,target)
                if digest_file(target,deadline)!=record:raise ValueError('Serial1020 copy changed')
        protocol={k:base[k] for k in ['reference_configuration','rpm_assumed','fluid','boundary_conditions','model','acceptance_all_required']}
        protocol.update(protocol_id=plan['protocol_id']+'-'+label,iterations=1040,new_iterations=20,
            expected_actual_solver_iterations=list(range(1021,1041)),required_admission_sample_iterations=list(range(1021,1041)),
            expected_cell_count=680596,initial_fields_sha256={'1020/uniform/time':prior['files']['1020/uniform/time']['sha256']},
            frozen_system_file_sha256={name:digest_file(case/'system'/name,deadline)['sha256'] for name in ['controlDict','fvSchemes','fvSolution']},
            physical_validation_established=False,manufacturing_authorized=False)
        (case/'reference-protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    shutil.copytree(capsule,output/'used-capsule')
    (output/'source-identity-verification.json').write_text(json.dumps({'all_frozen_prepared_and_previous_inputs_verified':True,
        'shared_native1020_identity_verified':True,'no_redecomposition_or_regridding':True,'source_mounts_read_only':True},indent=2)+'\n')
    return plan,manifest


def run(prepared,previous,selections,capsule,output):
    started=time.monotonic();deadline=float(os.environ['FAN_D3_DEADLINE']);release=os.environ['FAN_D3_RELEASE'];os.nice(10)
    origin=deadline-GLOBAL_CAP
    if sys.platform!='linux' or not Path('/opt/openfoam13').is_dir() or not release.strip() or deadline<=started or deadline-started>GLOBAL_CAP:raise ValueError('Coordinated existing native runtime and original global deadline required')
    commands=[];completed=[];archive=None;phase='isolation_gate';error=None;status='failed_or_partial_no_retry'
    def command(args,case,log,cap,reserve,shared_deadline=None):
        finish=phase_deadline(deadline,cap,reserve)
        if shared_deadline is not None:finish=min(finish,shared_deadline)
        attempt={'args':args,'log':str((case/log).relative_to(output)),'phase_wall_cap_seconds':cap,'status':'attempted'};commands.append(attempt)
        try:attempt.update(native_command(args,case,case/log,finish,cap));attempt['status']='completed'
        except Exception as exc:attempt['status']='failed_or_timeout';attempt['error']=type(exc).__name__+': '+str(exc);raise
        return finish
    try:
        setup_deadline=origin+PHASES['setup']
        while not (output/'isolation-admitted.json').exists():remaining(setup_deadline);time.sleep(.05)
        gate=json.loads((output/'isolation-admitted.json').read_text())
        if not gate['actual_isolation_verified'] or gate['aggregate_deadline_monotonic']!=deadline or gate['capsule_manifest_sha256']!=digest_file(capsule/'capsule-manifest.json',setup_deadline)['sha256']:raise ValueError('Actual isolation/capsule gate differs')
        phase='identity_and_copy';plan,manifest=copy_inputs(prepared,previous,selections,capsule,output,setup_deadline)
        remaining(setup_deadline)
        for label,reserve in [(LABELS[0],240),(LABELS[1],150)]:
            phase=label+'_solver';case=output/label
            solver_end=command(['mpirun','-np','4','foamRun','-parallel','-case',str(case)],case,'log.foamRun',90,reserve)
            check_complete20((case/'log.foamRun').read_text());completed.append(label)
            for name,record in plan['cases'][label]['native_MPI_seed_files'].items():
                if digest_file(case/name,solver_end)!=record:raise ValueError('Native1020 working seed was rewritten')
            remaining(solver_end)
        phase='reconstruction';reconstruction_deadline=phase_deadline(deadline,40,110)
        for label in LABELS:
            case=output/label;command(['reconstructPar','-case',str(case),'-time','1040'],case,'log.reconstructPar',40,110,reconstruction_deadline)
        phase='analysis';command(['python3','-B',str(capsule/'source/analyze_d3.py'),str(output),str(previous),str(selections),str(capsule/'configs/diagnostic-plan.json')],output,'log.analysis',45,65)
        status='completed_two_fixed20_no_retry'
    except (Exception,KeyboardInterrupt) as exc:error=type(exc).__name__+': '+str(exc)
    finally:
        receipt={'status':status,'phase':phase,'error':error,'commands':commands,'completed_solver_arms':completed,
            'restart_iteration':1020,'target_iteration':1040,'maximum_new_iterations_per_arm':20,'solver_count_max':2,
            'no_retry_or_further_continuation':True,'global_wall_cap_seconds':360,
            'wall_seconds_from_host_launcher_before_preservation':time.monotonic()-origin,
            'child_peak_RSS_KiB_not_aggregate':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            'coordinated_release':release,'native_fields_and_archive_private':True,'physical_validation_established':False}
        (output/'execution-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        try:archive=archive_private(output,phase_deadline(deadline,60,5))
        except Exception as exc:
            (output/'preservation-failure.json').write_text(json.dumps({'error':type(exc).__name__+': '+str(exc),
                'native_files_remain_on_disk':True,'partial_archive_not_verified':True,'no_retry':True},indent=2)+'\n')
        (output/'preservation-receipt.json').write_text(json.dumps({'archive_all_members_verified':bool(archive),
            'aggregate_remaining_seconds':deadline-time.monotonic(),'raw_native_files_retained':True,'no_retry':True},indent=2)+'\n')
    return 0 if status=='completed_two_fixed20_no_retry' and archive else 2


if __name__=='__main__':
    raise SystemExit(run(Path('/prepared'),Path('/previous'),Path('/selections.npz'),Path('/capsule'),Path('/run')))
