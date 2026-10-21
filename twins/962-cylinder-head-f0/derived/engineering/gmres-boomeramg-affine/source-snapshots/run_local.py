"""One authorised synthetic solve in an existing read-only isolated MOOSE rootfs."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
from assess_affine import assess,sha


def same(path,digest):
    try:return sha(path)==digest
    except OSError:return False


def checked_contract(path,digest):
    if sha(path)!=digest:raise ValueError('Exact frozen witness contract required')
    card=json.loads(path.read_text());source=Path(__file__).resolve().parent
    for name,h in card['source_sha256s'].items():
        if Path(name).name!=name or sha(source/name)!=h:raise ValueError('Frozen witness source changed')
    return card


def command(rootfs,output):
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
    return a+['/bin/bash','-c','. /environment; exec /opt/moose/bin/moose-opt -i affine.i --n-threads=1']


def run(rootfs,output,contract_path,digest):
    rootfs=Path(rootfs).resolve();output=Path(output).resolve();contract_path=Path(contract_path).resolve()
    card=checked_contract(contract_path,digest)
    if str(rootfs)!=card['required_rootfs'] or str(output)!=card['reserved_remote_output']:
        raise ValueError('Fixed existing runtime and fresh owned output required')
    if output.exists() or output.is_symlink():raise ValueError('Output must be new; failed evidence is retained')
    for name,h in card['runtime_sha256s'].items():
        if sha(rootfs/name)!=h:raise ValueError('Installed runtime identity changed')
    source=Path(__file__).resolve().parent;output.mkdir()
    snapshots=output/'source-snapshots';snapshots.mkdir()
    for name in card['source_sha256s']:shutil.copyfile(source/name,snapshots/name)
    shutil.copyfile(source/'affine.i',output/'affine.i');shutil.copyfile(contract_path,output/'frozen-contract.json')
    argv=command(rootfs,output);process=None;start=time.monotonic();failure=None
    receipt=dict(status='running',passed=False,command=argv,contract_sha256=digest,network='none',rootfs='read_only',
        automatic_retry=False,head_input_read=False,head_solve=False)
    (output/'launch.json').write_text(json.dumps(receipt,indent=2)+'\n')
    with (output/'native.log').open('xb') as stream:
        try:
            process=subprocess.Popen(argv,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            process.wait(timeout=40)
        except BaseException as exc:
            failure=type(exc).__name__+': '+str(exc)
            raise
        finally:
            if process is not None:
                if process.poll() is None:
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                process.wait()
            receipt.update(status='native_stopped_outputs_preserved',returncode=process.returncode if process else None,
                process_reaped=process is not None and process.poll() is not None,wall_seconds=time.monotonic()-start,
                controller_error=failure,
                binary_and_runtime_unchanged=all(same(rootfs/name,h) for name,h in card['runtime_sha256s'].items()),
                inputs_unchanged=same(output/'affine.i',card['source_sha256s']['affine.i']) and
                    same(output/'frozen-contract.json',digest) and all(same(source/name,h) and same(snapshots/name,h) for name,h in card['source_sha256s'].items()))
            receipt['artifact_sha256']={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*'))
                if p.is_file() and not p.is_symlink() and p.name not in ['native-execution.json','assessment.json']}
            (output/'native-execution.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if process.returncode:raise RuntimeError('Native witness failed; no retry authorised')
    try:result=assess(output,contract_path,digest)
    except Exception as exc:result=dict(status='synthetic_witness_rejected_outputs_preserved',passed=False,error=type(exc).__name__+': '+str(exc))
    with (output/'assessment.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    if not result['passed']:raise RuntimeError('Witness admission failed; assessment retained and no retry authorised')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rootfs',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--contract-sha256',required=True)
    parser.add_argument('--execute',action='store_true',help='Requires separate owner launch authorisation')
    args=parser.parse_args()
    if not args.execute:raise SystemExit('Native execution held; explicit separate launch authority required')
    print(json.dumps(run(args.rootfs,args.output,args.contract,args.contract_sha256)))
