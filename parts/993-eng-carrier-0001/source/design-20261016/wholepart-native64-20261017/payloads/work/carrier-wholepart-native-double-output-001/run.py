"""Execute the fixed four-state wholepart deck only after a reviewed plan SHA."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import os
import subprocess
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CONTROLLER=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/constitutive-refinement-20261017/sources/solver-supervision.py'
CONTROLLER_SHA='cbba58f0f6dd6333dc1063386eb61fe6f85652a4709e82032294c4c2c7726b0c'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def execute(path,expected):
    started=time.monotonic();raw=Path(path).read_bytes()
    if os.getpid()!=os.getpgrp()or os.getpid()!=os.getsid(0):raise ValueError('Launch in a newly owned session/process group')
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('The reviewed execution plan SHA differs')
    plan=json.loads(raw)
    if (plan['caller_sha256']!=sha(__file__)or sha(CONTROLLER)!=CONTROLLER_SHA or
            plan['wall_budget_seconds']!=900 or plan['cleanup_reserve_seconds']!=90 or plan['solver_timeout_seconds']!=720 or
            plan['case_name']!='wholepart-release'or plan['mechanical_DOF']!=310602 or
            plan['container_command']!=['--signal=TERM','--kill-after=10s','720','/usr/bin/ccx','-i','wholepart-release']):
        raise ValueError('Only the fixed bounded wholepart sensitivity is allowed')
    target=Path(plan['execution_directory'])
    if target.exists()or any(p.is_symlink()for p in [target,*target.parents]):raise FileExistsError('A new execution directory is required')
    target.mkdir(exist_ok=False)
    spec=importlib.util.spec_from_file_location('_private_unchanged_owned_CCX_supervisor',CONTROLLER)
    controller=importlib.util.module_from_spec(spec);spec.loader.exec_module(controller)
    controller.HERE=target
    cli=controller.DockerCLI();old={sig:signal.signal(sig,cli.cancel)for sig in (signal.SIGINT,signal.SIGTERM)}
    try:report=controller.supervise(plan,cli,started=started)
    finally:
        for sig,handler in old.items():signal.signal(sig,handler)
    report.update(plan_sha256=expected,plan_unchanged=sha(path)==expected,caller_sha256=sha(__file__),
        controller_sha256=sha(CONTROLLER),controller_bytes_unchanged=sha(CONTROLLER)==CONTROLLER_SHA,
        scope='Four linear wholepart sensitivity states only. Fictitious zmin fixture, not final print supports; no process prediction or numeric admission.',
        mechanical_DOF=plan['mechanical_DOF'],global_admission=False)
    if not report['plan_unchanged']or not report['controller_bytes_unchanged']:report['status']='integrity_refused_no_admission'
    solver_receipt=target/'solver-execution-receipt.json'
    with solver_receipt.open('x')as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    final=dict(status='pilot_refused',solver_receipt_sha256=sha(solver_receipt),pid=os.getpid(),PGID=os.getpgrp(),SID=os.getsid(0),global_admission=False)
    if report['status']=='solver_executed_no_numeric_admission'and report['actual_container_exit_code']==0 and report['container_removed']:
        timeout=min(60,900-(time.monotonic()-started)-5)
        if timeout>0:
            try:
                with(target/'assessment.stdout.log').open('xb')as out,(target/'assessment.stderr.log').open('xb')as err:
                    result=subprocess.run([plan['analysis_python'],'-I','-B',str(HERE/'assess.py'),plan['case_directory'],str(target/'numerical-assessment.json'),'--solver-receipt',str(solver_receipt),'--solver-receipt-sha256',sha(solver_receipt)],stdout=out,stderr=err,timeout=timeout,env={'PATH':'/usr/bin:/bin','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','VECLIB_MAXIMUM_THREADS':'1'})
                final['assessment_actual_returncode']=result.returncode
                if (target/'numerical-assessment.json').is_file():final['numerical_assessment_sha256']=sha(target/'numerical-assessment.json')
                if result.returncode==0:final['status']='wholepart_pilot_numeric_controls_passed_no_physical_prediction'
            except subprocess.TimeoutExpired:final['assessment_timed_out']=True
    final.update(total_wall_seconds=time.monotonic()-started,total_wall_budget_seconds=900,plan_unchanged=sha(path)==expected,all_pins_unchanged=all(sha(p)==h for p,h in plan['files_sha256'].items()))
    if final['total_wall_seconds']>900 or not final['plan_unchanged']or not final['all_pins_unchanged']:final['status']='integrity_or_total_budget_refused'
    with(target/'execution-receipt.json').open('x')as stream:json.dump(final,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({k:report.get(k)for k in ('status','actual_container_exit_code','container_removed','input_hashes_unchanged','wall_seconds')}))
    return 0 if final['status']=='wholepart_pilot_numeric_controls_passed_no_physical_prediction'else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('--plan-sha256',required=True);a=p.parse_args()
    raise SystemExit(execute(a.plan,a.plan_sha256))
