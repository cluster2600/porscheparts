"""One fixed imported-cube MOOSE invocation; assessment is a separate later step."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

SOURCE = Path(__file__).resolve().parent
RESOURCES = dict(soft_seconds=30,kill_grace_seconds=5,controller_wait_seconds=40,RuntimeMaxSec=45,
    MemoryMax_GiB=2,MemorySwapMax=0,CPUQuota_percent=200,TasksMax=128,MPI_ranks=1,software_threads=1)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def same(path,digest):
    try: return sha(path) == digest
    except OSError: return False


def checked_contract(path,digest):
    path = Path(path)
    if path.is_symlink() or sha(path) != digest: raise ValueError('Exact frozen cube contract required')
    c = json.loads(path.read_text()); pins = c['source_sha256s']
    if c.get('native_launch_authorized') is not True or c.get('root_and_peer_review_complete') is not True or c.get('resources') != RESOURCES:
        raise ValueError('Separate reviewed single-case launch and exact resources required')
    required = {'run_cube.py','assess_cube.py','old-runtime-contract.json','imported-cube.i','imported-cube.msh','cube-reference.json'}
    if not required <= set(pins): raise ValueError('Complete fixed input/source pins required')
    for name,h in pins.items():
        p = SOURCE/name
        if Path(name).name != name or not p.is_file() or p.is_symlink() or not same(p,h): raise ValueError('Frozen cube source/input changed: '+name)
    if not same(__file__,pins['run_cube.py']) or c.get('mesh_sha256') != pins['imported-cube.msh']:
        raise ValueError('Executed controller and actual mesh identity required')
    old = json.loads((SOURCE/'old-runtime-contract.json').read_text())
    if c['required_rootfs'] != old['required_rootfs'] or c['runtime_sha256s'] != old['runtime_sha256s']:
        raise ValueError('Unchanged exact eight-file existing MOOSE runtime required')
    return c


def command(rootfs,output):
    a=['systemd-run','--user','--scope','--quiet','-p','MemoryMax=2G','-p','MemorySwapMax=0',
        '-p','CPUQuota=200%','-p','TasksMax=128','-p','RuntimeMaxSec=45',
        'timeout','--signal=TERM','--kill-after=5s','30','bwrap','--unshare-user','--uid','0','--gid','0',
        '--ro-bind',str(rootfs),'/', '--dev','/dev','--proc','/proc','--tmpfs','/tmp',
        '--bind',str(output),'/tmp/work','--unshare-net','--unshare-pid','--die-with-parent','--clearenv',
        '--chdir','/tmp/work']
    for key,value in {'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/tmp',
        'USER':'root','LOGNAME':'root','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1',
        'OMPI_ALLOW_RUN_AS_ROOT':'1','OMPI_ALLOW_RUN_AS_ROOT_CONFIRM':'1','OMPI_MCA_btl_vader_single_copy_mechanism':'none'}.items(): a+=['--setenv',key,value]
    return a+['/bin/bash','-c','. /environment; exec /opt/moose/bin/moose-opt -i imported-cube.i --n-threads=1']


def run(rootfs,output,contract_path,digest):
    c=checked_contract(contract_path,digest)
    if Path(output).is_symlink(): raise ValueError('Fresh task-owned output required')
    rootfs=Path(rootfs).resolve(); output=Path(output).resolve(); contract_path=Path(contract_path).resolve()
    if str(rootfs)!=c['required_rootfs'] or str(output)!=c['reserved_remote_output'] or output.exists():
        raise ValueError('Exact existing rootfs and fresh fixed output required')
    if any(not same(rootfs/name,h) for name,h in c['runtime_sha256s'].items()): raise ValueError('Runtime drift before output creation')
    output.mkdir(); snapshots=output/'source-snapshots'; snapshots.mkdir()
    for name in c['source_sha256s']: shutil.copyfile(SOURCE/name,snapshots/name)
    for name in ['imported-cube.i','imported-cube.msh']: shutil.copyfile(SOURCE/name,output/name)
    shutil.copyfile(contract_path,output/'frozen-contract.json')
    inputs={str(p.relative_to(output)):sha(p) for p in output.rglob('*') if p.is_file()}
    argv=command(rootfs,output); process=None; start=time.monotonic(); failure=None; term_requested=False
    receipt=dict(status='running',passed=False,command=argv,contract_sha256=digest,input_sha256=inputs,
        network='none',rootfs='read_only',automatic_retry=False,head_input_read=False,independent_assessment_performed=False)
    with (output/'launch.json').open('x') as stream: json.dump(receipt,stream,indent=2); stream.write('\n')
    previous=signal.getsignal(signal.SIGTERM)
    def interrupted(*_):
        nonlocal term_requested
        term_requested=True
    try:
        with (output/'native.log').open('xb') as stream:
            try:
                signal.signal(signal.SIGTERM,interrupted)
                process=subprocess.Popen(argv,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
                if term_requested: raise InterruptedError('Controller SIGTERM requested')
                process.wait(timeout=40)
                if term_requested: raise InterruptedError('Controller SIGTERM requested')
            except BaseException as exc:
                failure=type(exc).__name__+': '+str(exc)
                raise
            finally:
                try:
                    if process is not None:
                        if process.poll() is None:
                            try: os.killpg(process.pid,signal.SIGKILL)
                            except ProcessLookupError: pass
                        process.wait()
                finally: signal.signal(signal.SIGTERM,previous)
    finally:
        reaped=process is not None and process.poll() is not None
        unchanged=all(same(output/name,h) for name,h in inputs.items()) and all(same(SOURCE/name,h) for name,h in c['source_sha256s'].items()) and same(contract_path,digest)
        runtime_unchanged=all(same(rootfs/name,h) for name,h in c['runtime_sha256s'].items())
        receipt.update(status='native_stopped_outputs_preserved',returncode=process.returncode if process else None,
            process_reaped=reaped,controller_error=failure,controller_SIGTERM_requested=term_requested,
            wall_seconds=time.monotonic()-start,inputs_unchanged=unchanged,binary_and_runtime_unchanged=runtime_unchanged,
            native_execution_completed=process is not None and process.returncode==0 and reaped and failure is None and not term_requested and unchanged and runtime_unchanged)
        receipt['artifact_sha256']={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file() and not p.is_symlink() and p.name not in ['native-execution.json','assessment.json']}
        with (output/'native-execution.json').open('x') as stream: json.dump(receipt,stream,indent=2); stream.write('\n')
    if not receipt['native_execution_completed']: raise RuntimeError('Native invocation incomplete; outputs retained, no retry')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rootfs',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--contract',type=Path,required=True); parser.add_argument('--contract-sha256',required=True)
    parser.add_argument('--execute',action='store_true'); args=parser.parse_args()
    if not args.execute: raise SystemExit('Held source; separate native launch authorization required')
    print(json.dumps(run(args.rootfs,args.output,args.contract,args.contract_sha256)))
