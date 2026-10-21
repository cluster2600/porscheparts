"""Bound a pinned experimental CGAL soup operation in a fresh owned folder."""
import argparse,hashlib,json,os,shutil,signal,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['self_union','union','intersection','difference'])
    p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('--second-input',type=Path)
    args=p.parse_args();source=args.input.resolve();out=args.output.resolve()
    assert source.is_file() and not out.exists() and out.parent==ROOT/'jobs'
    assert (args.mode=='self_union')==(args.second_input is None)
    second=args.second_input.resolve() if args.second_input else None
    if second:assert second.is_file()
    manifest=ROOT/'installation-receipt.json';runtime=json.loads(manifest.read_text());binary=ROOT/'build/carrier_soup_boolean'
    assert runtime['CGAL_commit']=='b4e8c1887ce6a0abeb618634125e5cfcd301ce16'
    assert sha(binary)==runtime['binary_sha256']
    assert all(sha(ROOT/name)==value for name,value in runtime['source_files_sha256'].items())
    dependencies={**runtime['runtime_files_sha256'],**runtime['compiled_dependency_files_sha256']}
    assert all(sha(path)==value for path,value in dependencies.items())
    inputs={str(path):sha(path) for path in [source,*([second] if second else []),manifest,binary,ROOT/'run.py',ROOT/'worker.py',ROOT/'soup_boolean.cpp']}
    inputs.update(dependencies);out.mkdir()
    for name in ['run.py','worker.py','soup_boolean.cpp','installation-receipt.json']:shutil.copyfile(ROOT/name,out/name)
    copied={str(path):sha(path) for path in out.iterdir() if path.is_file()}
    unit='carrier-experimental-soup-'+uuid.uuid4().hex[:12]
    command=['systemd-run','--user','--scope','--quiet','--unit',unit,'-p','CPUQuota=200%','-p','MemoryMax=4G',
      '-p','MemorySwapMax=0','-p','TasksMax=128','-p','RuntimeMaxSec=610','timeout','--kill-after=10s','600',
      'bwrap','--ro-bind','/','/','--unshare-net','--unshare-pid','--unshare-ipc','--die-with-parent','--new-session',
      '--proc','/proc','--dev','/dev','--tmpfs','/tmp','--ro-bind',str(source),'/tmp/input-A.npz']
    if second:command+=['--ro-bind',str(second),'/tmp/input-B.npz']
    command+=['--bind',str(out),'/tmp/output','--chdir','/tmp/output','--clearenv','--setenv','PATH','/usr/bin:/bin',
      '--setenv','OMP_NUM_THREADS','1','--setenv','OPENBLAS_NUM_THREADS','1','--setenv','PYTHONDONTWRITEBYTECODE','1',
      runtime['audit_python'],'/tmp/output/worker.py',args.mode,'/tmp/input-A.npz','/tmp/output',str(binary)]
    if second:command+=['--second-input','/tmp/input-B.npz']
    receipt={'command':command,'unit':unit+'.scope','operation':args.mode,'inputs_sha256':inputs,'copied_sources_sha256':copied,
      'timeout_seconds':600,'experimental':True,'precision_rule':'Exact Epeck throughout operation; one final float64 export; no snap/weld/tolerance'}
    (out/'execution-plan.json').write_text(json.dumps(receipt,indent=2)+'\n');start=time.monotonic();process=None
    try:
        with (out/'stdout.log').open('w') as log:
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);code=process.wait(timeout=630)
        receipt.update(status='executed' if code==0 else 'rejected_or_failed',returncode=code)
    except subprocess.TimeoutExpired:receipt.update(status='timed_out',returncode=None)
    finally:
        subprocess.run(['systemctl','--user','kill',unit+'.scope'],capture_output=True,timeout=10)
        subprocess.run(['systemctl','--user','stop',unit+'.scope'],capture_output=True,timeout=15)
        if process is not None and process.poll() is None:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=10)
        receipt['owned_scope_inactive']=subprocess.run(['systemctl','--user','is-active',unit+'.scope'],capture_output=True,timeout=10).returncode!=0
        receipt['identities_unchanged']=all(sha(path)==value for path,value in {**inputs,**copied}.items())
        if not receipt['identities_unchanged']:receipt['status']='failed_identity_changed'
        receipt['seconds']=time.monotonic()-start;(out/'execution-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return 0 if receipt['status']=='executed' and receipt['owned_scope_inactive'] else 1
if __name__=='__main__':sys.exit(main())
