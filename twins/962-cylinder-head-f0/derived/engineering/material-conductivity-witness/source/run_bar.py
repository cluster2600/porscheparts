"""Fixed Z/XY bar invocations in the existing isolated MOOSE runtime; assessment separate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

SOURCE=Path(__file__).resolve().parent
CASE_INPUTS={'Z':['conductivity-z.i'],'XY':['conductivity-z.i','conductivity-xy.i']}
RESOURCES={'soft_seconds':30,'kill_grace_seconds':5,'controller_wait_seconds':40,
           'RuntimeMaxSec':45,'MemoryMax_GiB':2,'MemorySwapMax':0,'CPUQuota_percent':200,
           'TasksMax':128,'MPI_ranks':1,'software_threads':1}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def same(path,digest):
    try:return sha(path)==digest
    except OSError:return False


def checked_contract(path,digest):
    path=Path(path)
    if path.is_symlink() or sha(path)!=digest:raise ValueError('Exact frozen bar contract required')
    card=json.loads(path.read_text())
    if card.get('native_launch_authorized') is not True or card.get('case_inputs')!=CASE_INPUTS or card.get('resources')!=RESOURCES:
        raise ValueError('Separate fixed two-case launch authority and unchanged resources required')
    pins=card['source_sha256s']
    if not {'run_bar.py','old-runtime-contract.json','conductivity-z.i','conductivity-xy.i'}.issubset(pins):
        raise ValueError('Complete fixed launcher/input/runtime-proof pins required')
    for name,h in pins.items():
        p=SOURCE/name
        if Path(name).name!=name or not p.is_file() or p.is_symlink() or not same(p,h):
            raise ValueError('Frozen bar source changed: '+name)
    if sha(Path(__file__).resolve())!=pins['run_bar.py']:raise ValueError('Executed launcher source differs')
    old=json.loads((SOURCE/'old-runtime-contract.json').read_text())
    if card['runtime_sha256s']!=old['runtime_sha256s'] or card['required_rootfs']!=old['required_rootfs']:
        raise ValueError('Exact existing eight-file MOOSE runtime identity required')
    return card


def command(rootfs,output,case):
    if case not in CASE_INPUTS:raise ValueError("Only fixed Z and XY cases are permitted")
    a=['systemd-run','--user','--scope','--quiet','-p','MemoryMax=2G','-p','MemorySwapMax=0',
        '-p','CPUQuota=200%','-p','TasksMax=128','-p','RuntimeMaxSec=45',
        'timeout','--signal=TERM','--kill-after=5s','30','bwrap','--unshare-user','--uid','0','--gid','0',
        '--ro-bind',str(rootfs),'/', '--dev','/dev','--proc','/proc','--tmpfs','/tmp',
        '--bind',str(output),'/tmp/work','--unshare-net','--unshare-pid','--die-with-parent','--clearenv',
        '--chdir','/tmp/work']
    for key,value in {'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/tmp',
        'USER':'root','LOGNAME':'root','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1',
        'OMPI_ALLOW_RUN_AS_ROOT':'1','OMPI_ALLOW_RUN_AS_ROOT_CONFIRM':'1','OMPI_MCA_btl_vader_single_copy_mechanism':'none'}.items():
        a+=['--setenv',key,value]
    native={'Z':'. /environment; exec /opt/moose/bin/moose-opt -i conductivity-z.i --n-threads=1',
            'XY':'. /environment; exec /opt/moose/bin/moose-opt -i conductivity-z.i conductivity-xy.i --n-threads=1'}[case]
    return a+['/bin/bash','-c',native]


def run_case(rootfs,directory,case,card,contract_path,digest):
    checked_contract(contract_path,digest)
    if any(not same(rootfs/name,h) for name,h in card['runtime_sha256s'].items()):
        raise ValueError('Installed runtime changed before case')
    if directory.exists() or directory.is_symlink():raise ValueError('Case output must be fresh')
    directory.mkdir();snapshots=directory/'source-snapshots';snapshots.mkdir()
    for name in card['source_sha256s']:shutil.copyfile(SOURCE/name,snapshots/name)
    for name in CASE_INPUTS[case]:shutil.copyfile(SOURCE/name,directory/name)
    shutil.copyfile(contract_path,directory/'frozen-contract.json')
    inputs={str(p.relative_to(directory)):sha(p) for p in directory.rglob('*') if p.is_file()}
    argv=command(rootfs,directory,case);process=None;started=time.monotonic();failure=None
    receipt=dict(status='running',passed=False,case=case,direction=case,command=argv,
        contract_sha256=digest,network='none',rootfs='read_only',automatic_retry=False,
        head_input_read=False,head_solve=False,independent_assessment_performed=False,
        nonlinear_iterate_material_range_coverage_unverified=True,input_sha256=inputs)
    with (directory/'launch.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    previous_sigterm=signal.getsignal(signal.SIGTERM)
    def interrupted(*_):raise KeyboardInterrupt('Controller SIGTERM')
    try:
        with (directory/'native.log').open('xb') as stream:
            try:
                signal.signal(signal.SIGTERM,interrupted)
                process=subprocess.Popen(argv,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
                process.wait(timeout=40)
            except BaseException as exc:
                failure=type(exc).__name__+': '+str(exc)
                raise
            finally:
                try:
                    if process is not None:
                        if process.poll() is None:
                            try:os.killpg(process.pid,signal.SIGKILL)
                            except ProcessLookupError:pass
                        process.wait()
                finally:signal.signal(signal.SIGTERM,previous_sigterm)
    finally:
        reaped=process is not None and process.poll() is not None
        unchanged=all(same(directory/name,h) for name,h in inputs.items()) and all(same(SOURCE/name,h) for name,h in card['source_sha256s'].items()) and same(contract_path,digest)
        runtime_unchanged=all(same(rootfs/name,h) for name,h in card['runtime_sha256s'].items())
        receipt.update(status='native_stopped_outputs_preserved',returncode=process.returncode if process else None,
            process_reaped=reaped,wall_seconds=time.monotonic()-started,controller_error=failure,
            binary_and_runtime_unchanged=runtime_unchanged,inputs_unchanged=unchanged,
            native_execution_completed=process is not None and process.returncode==0 and reaped and failure is None and unchanged and runtime_unchanged)
        receipt['artifact_sha256']={str(p.relative_to(directory)):sha(p) for p in sorted(directory.rglob('*'))
            if p.is_file() and not p.is_symlink() and p.name not in ['native-execution.json','assessment.json']}
        with (directory/'native-execution.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    if not receipt['native_execution_completed']:raise RuntimeError('Native case did not complete unchanged; no retry or next case')
    return receipt


def run(rootfs,output,contract_path,digest):
    card=checked_contract(contract_path,digest)
    if Path(output).is_symlink():raise ValueError('Output must be a new owned directory')
    rootfs=Path(rootfs).resolve();output=Path(output).resolve();contract_path=Path(contract_path).resolve()
    if str(rootfs)!=card['required_rootfs'] or str(output)!=card['reserved_remote_output']:
        raise ValueError('Fixed existing runtime and declared fresh output required')
    if output.exists():raise ValueError('Output exists; preserve its bytes')
    for name,h in card['runtime_sha256s'].items():
        if not same(rootfs/name,h):raise ValueError('Installed runtime identity changed')
    output.mkdir();shutil.copyfile(contract_path,output/'frozen-contract.json');cases={};error=None
    try:
        for case in ['Z','XY']:
            result=run_case(rootfs,output/case,case,card,contract_path,digest)
            cases[case]=dict(returncode=result['returncode'],native_execution_completed=result['native_execution_completed'],
                receipt_sha256=sha(output/case/'native-execution.json'))
    except BaseException as exc:
        error=type(exc).__name__+': '+str(exc)
        raise
    finally:
        summary=dict(status='fixed_two_case_invocation_stopped',case_results=cases,controller_error=error,
            contract_sha256=digest,native_invocations_completed=set(cases)=={'Z','XY'} and error is None,
            independent_assessment_performed=False,material_witness_passed=False,
            nonlinear_iterate_material_range_coverage_unverified=True,head_or_manufacturing_admitted=False,
            automatic_retry=False)
        with (output/'execution-summary.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rootfs',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--contract-sha256',required=True)
    parser.add_argument('--execute',action='store_true',help='Requires separately frozen root launch authority')
    args=parser.parse_args()
    if not args.execute:raise SystemExit('Held source preparation; native execution not authorized')
    print(json.dumps(run(args.rootfs,args.output,args.contract,args.contract_sha256)))
