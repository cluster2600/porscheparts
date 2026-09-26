"""Private hashfixed native CCX requalification; two exact G13 RHS, retained K, fresh CPU CG."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
MEDIUM=HERE/'caps_medium_candidate.py'
MEDIUM_SHA='4ddbb328b3a7f46d8af7191ee2e7c8d2dfeb654c381bc93d04b37ca7ae00347e'
if hashlib.sha256(MEDIUM.read_bytes()).hexdigest()!=MEDIUM_SHA:raise ValueError('frozen medium source changed')
spec=importlib.util.spec_from_file_location('g14_medium',MEDIUM)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
c=m.c;reference=c.prior.reference
OLD=c.REPO/'work/m64-g13/native-fea/run-1'
OLD_SHA='8f4cfa8a0713d58689c0068a3e792a0c178cc5b948d2ab2a7d3617f4276d6ab9'
BUILD=HERE.parent/'native-ccx-hashfix-v1'
BUILD_SCRIPT=HERE.parent/'build_ccx_hashfix.py'
BUILD_SCRIPT_SHA='28c6769896467c555b4ba603464550d4678e4019794cb8240f2e260c74709723'
PATCH_SHA='7f0cd7472afa3a2b411a36721aa79120d88234ac33241795c4706c532185b2f2'
PLAN=(('serial-z','minus_z'),('serial-x','x'))


def runtime(inventory_sha):
    if c.g8.sha256(BUILD/'build-inventory.json')!=inventory_sha or c.g8.sha256(BUILD_SCRIPT)!=BUILD_SCRIPT_SHA:
        raise ValueError('reviewed build inventory or builder changed')
    inventory=json.loads((BUILD/'build-inventory.json').read_text())
    build=json.loads((BUILD/'build.json').read_text())
    smoke=json.loads((BUILD/'qualification-smoke.json').read_text())
    binary=Path(inventory['binary']['path'])
    if (binary!=BUILD/'CalculiX/ccx_2.21/src/ccx_2.21' or c.g8.sha256(binary)!=inventory['binary']['sha256']
            or inventory['patch_sha256']!=PATCH_SHA or build['complete'] is not True or build['error'] is not None
            or build['source_sha256']!=BUILD_SCRIPT_SHA or build['build_inventory_sha256']!=inventory_sha
            or build['changed_members']!=['I2Ohash_util.o'] or build['originals_verified_after'] is not True
            or smoke['passed'] is not True or smoke['binary_sha256']!=inventory['binary']['sha256']):
        raise ValueError('completed isolated build and analytic cube smoke required')
    for name,row in inventory['dynamic_libraries'].items():
        if str(Path(name).resolve())!=row['resolved_path'] or c.g8.sha256(Path(name))!=row['sha256']:
            raise ValueError('native library changed: '+name)
    for name,digest in smoke['smoke_artifacts'].items():
        if c.g8.sha256(c.g13.confined(BUILD/'smoke',name))!=digest:raise ValueError('smoke artifact changed')
    return dict(binary=str(binary),binary_sha256=inventory['binary']['sha256'],inventory_sha256=inventory_sha,
        build_sha256=c.g8.sha256(BUILD/'build.json'),smoke_sha256=c.g8.sha256(BUILD/'qualification-smoke.json'),
        dynamic_libraries=inventory['dynamic_libraries'],patch_sha256=PATCH_SHA)


def ccx(case,name,binary,seconds,new_session=True):
    """Own bounded direct process; receipt retains the real native code even on failure."""
    begin=time.monotonic();reason=None;process=None
    with (case/(name+'.log')).open('x') as log:
        try:
            process=subprocess.Popen([str(binary),name],cwd=case,stdout=log,stderr=subprocess.STDOUT,
                start_new_session=new_session,env=dict(os.environ,**c.THREAD_ENV))
            process.wait(timeout=seconds)
        except BaseException as exc:reason=type(exc).__name__+': '+str(exc)
        finally:
            if process is not None:
                if new_session:
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                elif process.poll() is None:process.kill()
                process.wait()
            row=dict(native_returncode=process.returncode if process else None,error=reason,
                seconds=time.monotonic()-begin,native_process_reaped=process is not None)
            c.g11.publish(case/(name+'-execution.json'),row)
    if reason is not None or row['native_returncode']!=0:raise ValueError('native CCX failed: '+str(row))
    c.g13.serial_log(case/(name+'.log'))
    return row


def inputs(inventory_sha):
    if c.g8.sha256(OLD/'summary-0001.json')!=OLD_SHA:raise ValueError('qualified G13 reference changed')
    old=c.native.native_gate(OLD/'summary-0001.json')  # Rehash both retained DATs, all K/DOF and provenance.
    proof=runtime(inventory_sha)
    old_libraries=json.loads((OLD/'summary-0001.json').read_text())['dynamic_libraries']
    if proof['dynamic_libraries']!=old_libraries:raise ValueError('only the SPOOLES hash implementation may change')
    return dict(runtime=proof,retained_reference=old,source_sha256=c.g8.sha256(Path(__file__)))


def run(args):
    proof=inputs(args.inventory_sha256);args.output.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,args.output/Path(__file__).name)
    report=dict(classification='G14_hashfixed_native_CPU_reference_requalification',proof=proof,rows=[],
        complete=False,error=None,all_numerical_checks_passed=False,matrix_reexported=False,fresh_CPU_CG=True,
        FEA_executed=False,CUDA_executed=False,AMG_executed=False,manufacturing_authorized=False,
        engine_start_authorized=False,old_medium_failure_preserved=True)
    c.g11.publish(args.output/'identity.json',proof)
    start=time.monotonic();deadline=start+2700
    def remaining(limit):
        seconds=min(limit,deadline-time.monotonic()-30)
        if seconds<=0:raise TimeoutError('45-minute reference deadline')
        return seconds
    signal.setitimer(signal.ITIMER_REAL,2700)
    try:
        text=(OLD/'serial-x-control/x.inp').read_text();points,_,support=c.g9.deck(text)
        matrix,mapping=c.g9.bench.read_matrix(OLD/'matrix/matrix.sti',OLD/'matrix/matrix.dof',points,support)
        for label,name in PLAN:
            case=args.output/label;case.mkdir()
            old_case=OLD/('serial-x-control' if name=='x' else 'serial-z-r1')
            shutil.copyfile(old_case/(name+'.inp'),case/(name+'.inp'))
            report['FEA_executed']=True;direct=ccx(case,name,proof['runtime']['binary'],remaining(1200))
            _,loads,fixed=c.g9.deck((case/(name+'.inp')).read_text())
            if fixed!=support:raise ValueError('G13 support mismatch')
            rhs=c.g9.rhs_for(mapping,loads)
            u,timing=c.g9.bench.solve(matrix,rhs,'cpu',max_seconds=remaining(900))
            residual=float(c.np.linalg.norm(matrix@u-rhs)/c.np.linalg.norm(rhs))
            solution=dict(u=u,passed=bool(timing['info']==0 and c.np.isfinite(u).all() and residual<=1e-8))
            compared=reference.compare(case,name,matrix,mapping,solution,rhs,points,support)
            row=dict(id=label,direction=name,direct=direct,solver=timing,relative_residual=residual,**compared,
                hashes={p.name:c.g8.sha256(p) for p in sorted(case.iterdir()) if p.is_file()})
            c.g11.publish(case/'case.json',row);report['rows'].append(row)
            c.g11.publish(args.output/('checkpoint-'+name+'.json'),report)
            print(json.dumps(dict(direction=name,passed=row['passed'],direct_seconds=direct['seconds'])),flush=True)
            if not row['passed']:raise ValueError('unchanged G13 numerical gate failed')
        if inputs(args.inventory_sha256)!=proof:raise ValueError('runtime or retained reference changed during run')
        report.update(complete=True,all_numerical_checks_passed=True,runtime_verified_after=True)
    except BaseException as exc:report['error']=type(exc).__name__+': '+str(exc)
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        report.update(wall_seconds=time.monotonic()-start,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            max_child_RSS_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            artifacts_sha256={str(p.relative_to(args.output)):c.g8.sha256(p) for p in sorted(args.output.rglob('*')) if p.is_file()})
        c.g11.publish(args.output/'summary.json',report)
    return 0 if report['all_numerical_checks_passed'] else 2


if __name__=='__main__':
    def interrupted(signum,frame):raise InterruptedError('native reference deadline or interruption')
    for sig in (signal.SIGTERM,signal.SIGALRM):signal.signal(sig,interrupted)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--inventory-sha256',required=True)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args();args.output=args.output.resolve()
    if not args.output.is_relative_to(HERE) or args.output==HERE:parser.error('new private FEA output required')
    if args.check:print(json.dumps(inputs(args.inventory_sha256)));raise SystemExit(0)
    raise SystemExit(run(args))
