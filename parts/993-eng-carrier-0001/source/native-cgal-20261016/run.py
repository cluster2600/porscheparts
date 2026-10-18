"""Bound one CGAL snap job, pinning runtime, sources and the input identity."""
import argparse,hashlib,json,os,signal,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--grid-bits',type=int,required=True);p.add_argument('--iterations',type=int,required=True)
    group=p.add_mutually_exclusive_group(required=True);group.add_argument('--max-drift-mm',type=float);group.add_argument('--cumulative-grid-bound',action='store_true')
    args=p.parse_args();assert 0<=args.grid_bits<52 and 0<=args.iterations<=100
    assert args.input.is_file() and not args.output.exists();out=args.output.resolve()
    assert out.parent==ROOT/'jobs','Output must be a fresh direct child of the owned jobs directory'
    runtime_file=ROOT/'installation-receipt.json';runtime=json.loads(runtime_file.read_text())
    PYTHON=Path(runtime['audit_python'])
    binary=ROOT/'build/carrier_autorefine';worker=Path(__file__).with_name('worker.py');adapter=ROOT/'autorefine.cpp'
    assert runtime['CGAL_commit']=='109ed62eeaa7e38eb383e9444700e6ff7bd4c449'
    assert sha(binary)==runtime['binary_sha256'] and sha(adapter)==runtime['adapter_source_sha256']
    assert all(sha(path)==value for path,value in runtime['runtime_files_sha256'].items())
    out.mkdir();(out/'runner.py').write_bytes(Path(__file__).read_bytes());(out/'worker.py').write_bytes(worker.read_bytes())
    (out/'adapter.cpp').write_bytes(adapter.read_bytes());(out/'installation-receipt.json').write_bytes(runtime_file.read_bytes())
    identities={str(q):sha(q) for q in [args.input.resolve(),Path(__file__).resolve(),worker.resolve(),binary,adapter,runtime_file]}
    identities.update(runtime['runtime_files_sha256'])
    owned={str(out/n):sha(out/n) for n in ['runner.py','worker.py','adapter.cpp','installation-receipt.json']}
    unit='carrier-cgal-snap-'+uuid.uuid4().hex[:12]
    command=['systemd-run','--user','--scope','--quiet','--unit',unit,'-p','CPUQuota=200%','-p','MemoryMax=4G',
      '-p','MemorySwapMax=0','-p','TasksMax=128','-p','RuntimeMaxSec=610','/usr/bin/timeout','--kill-after=10s','600',
      '/usr/bin/bwrap','--ro-bind','/','/','--unshare-net','--unshare-pid','--unshare-ipc','--die-with-parent','--new-session',
      '--proc','/proc','--dev','/dev','--tmpfs','/tmp','--ro-bind',str(args.input.resolve()),'/tmp/input.npz',
      '--bind',str(out),'/tmp/output','--chdir','/tmp/output','--clearenv','--setenv','PATH','/usr/bin:/bin',
      '--setenv','OMP_NUM_THREADS','1','--setenv','OPENBLAS_NUM_THREADS','1','--setenv','PYTHONDONTWRITEBYTECODE','1',
      str(PYTHON),'/tmp/output/worker.py','/tmp/input.npz','/tmp/output',str(binary),
      '--grid-bits',str(args.grid_bits),'--iterations',str(args.iterations)]
    command+=['--cumulative-grid-bound'] if args.cumulative_grid_bound else ['--max-drift-mm',str(args.max_drift_mm)]
    receipt={'command':command,'unit':unit+'.scope','inputs_sha256':identities,'copied_sources_sha256':owned,
             'timeout_seconds':600,'grid_bits':args.grid_bits,'iteration_budget':args.iterations}
    (out/'execution-plan.json').write_text(json.dumps(receipt,indent=2)+'\n')
    start=time.monotonic();process=None
    try:
        with (out/'stdout.log').open('w') as log:
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);code=process.wait(timeout=630)
        receipt.update(status='executed' if code==0 else 'rejected_or_failed',returncode=code)
    except subprocess.TimeoutExpired:receipt.update(status='timed_out',returncode=None)
    finally:
        subprocess.run(['systemctl','--user','kill',unit+'.scope'],capture_output=True,timeout=10)
        subprocess.run(['systemctl','--user','stop',unit+'.scope'],capture_output=True,timeout=15)
        if process is not None and process.poll() is None:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=10)
        state=subprocess.run(['systemctl','--user','is-active',unit+'.scope'],capture_output=True,text=True,timeout=10)
        receipt['owned_scope_inactive']=state.returncode!=0
        receipt['identities_unchanged']=all(sha(path)==value for path,value in {**identities,**owned}.items())
        if not receipt['identities_unchanged']:receipt['status']='failed_identity_changed'
        receipt['seconds']=time.monotonic()-start;(out/'execution-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return 0 if receipt['status']=='executed' and receipt['owned_scope_inactive'] else 1

if __name__=='__main__':sys.exit(main())
