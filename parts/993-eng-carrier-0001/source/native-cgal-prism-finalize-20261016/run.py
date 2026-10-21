"""Audit a sealed existing exact/float checkpoint; never repeat its CSG."""
import argparse,hashlib,json,os,shutil,signal,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('origin_job',type=Path);p.add_argument('output',type=Path)
    for name in ['roofs','mask','part']:p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();origin=args.origin_job.resolve();out=args.output.resolve();assert not out.exists() and out.parent==ROOT/'jobs'
    paths={role:getattr(args,role).resolve() for role in ['roofs','mask','part']}
    old_file=origin/'execution-receipt.json';old=json.loads(old_file.read_text())
    assert old['identities_unchanged'] and old['owned_scope_inactive'] and old['unadmitted_checkpoint_complete']
    assert all(sha(path)==value for path,value in {**old['inputs_sha256'],**old['copied_sources_sha256'],**old['unadmitted_geometry_checkpoint_files_sha256']}.items())
    exact=origin/'result.mesh64.unadmitted.exact';quantized=origin/'result.mesh64.unadmitted.mesh64'
    assert str(exact) in old['unadmitted_geometry_checkpoint_files_sha256'] and str(quantized) in old['unadmitted_geometry_checkpoint_files_sha256']
    assert all(old['inputs_sha256'][str(path)]==sha(path) for path in paths.values())
    manifest=ROOT/'installation-receipt.json';runtime=json.loads(manifest.read_text());binary=ROOT/'build/carrier_soup_boolean'
    assert sha(binary)==runtime['binary_sha256']
    assert all(sha(ROOT/name)==value for name,value in runtime['source_files_sha256'].items())
    dependencies={**runtime['compiled_dependency_files_sha256'],**runtime['runtime_files_sha256']}
    assert all(sha(path)==value for path,value in dependencies.items())
    inputs={str(path):sha(path) for path in [*paths.values(),exact,quantized,old_file,origin/'execution-plan.json',manifest,binary,ROOT/'run.py',ROOT/'worker.py',ROOT/'soup_boolean.cpp']}
    inputs.update(dependencies);out.mkdir()
    for name in ['run.py','worker.py','soup_boolean.cpp','installation-receipt.json']:shutil.copyfile(ROOT/name,out/name)
    for name in ['execution-receipt.json','execution-plan.json']:shutil.copyfile(origin/name,out/('origin-'+name))
    copied={str(path):sha(path) for path in out.iterdir() if path.is_file()}
    unit='carrier-checkpoint-finalize-'+uuid.uuid4().hex[:12]
    command=['systemd-run','--user','--scope','--quiet','--unit',unit,'-p','CPUQuota=200%','-p','MemoryMax=4G','-p','MemorySwapMax=0','-p','TasksMax=128','-p','RuntimeMaxSec=610',
      'timeout','--kill-after=10s','600','bwrap','--ro-bind','/','/','--unshare-net','--unshare-pid','--unshare-ipc','--die-with-parent','--new-session','--proc','/proc','--dev','/dev','--tmpfs','/tmp']
    for role,path in paths.items():command+=['--ro-bind',str(path),'/tmp/'+role+'.npz']
    command+=['--ro-bind',str(exact),'/tmp/checkpoint.exact','--ro-bind',str(quantized),'/tmp/checkpoint.mesh64',
      '--bind',str(out),'/tmp/output','--chdir','/tmp/output','--clearenv','--setenv','PATH','/usr/bin:/bin','--setenv','OMP_NUM_THREADS','1','--setenv','OPENBLAS_NUM_THREADS','1','--setenv','PYTHONDONTWRITEBYTECODE','1',
      runtime['audit_python'],'/tmp/output/worker.py','/tmp/roofs.npz','/tmp/mask.npz','/tmp/part.npz','/tmp/checkpoint.exact','/tmp/checkpoint.mesh64','/tmp/output',str(binary)]
    receipt={'command':command,'unit':unit+'.scope','inputs_sha256':inputs,'copied_sources_sha256':copied,'timeout_seconds':600,
      'operation':'finalize_existing_sealed_checkpoint_only','CSG_recomputed':False,'origin_execution_receipt_sha256':sha(old_file),
      'origin_geometry_checkpoint_sha256':sha(exact),'origin_quantized_checkpoint_sha256':sha(quantized)}
    (out/'execution-plan.json').write_text(json.dumps(receipt,indent=2)+'\n');start=time.monotonic();process=None
    try:
        with (out/'stdout.log').open('w') as log:
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);code=process.wait(timeout=630)
        receipt.update(status='executed' if code==0 else 'rejected_or_failed',returncode=code)
    except subprocess.TimeoutExpired:receipt.update(status='timed_out',returncode=None)
    finally:
        subprocess.run(['systemctl','--user','kill',unit+'.scope'],capture_output=True,timeout=10);subprocess.run(['systemctl','--user','stop',unit+'.scope'],capture_output=True,timeout=15)
        if process is not None and process.poll() is None:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=10)
        receipt['owned_scope_inactive']=subprocess.run(['systemctl','--user','is-active',unit+'.scope'],capture_output=True,timeout=10).returncode!=0
        receipt['identities_unchanged']=all(sha(path)==value for path,value in {**inputs,**copied}.items())
        if not receipt['identities_unchanged']:receipt['status']='failed_identity_changed'
        receipt['output_files_sha256']={path.name:sha(path) for path in out.iterdir() if path.is_file() and path.name in ['native.json','audit.json','result.mesh64','result.mesh64.exact','result.mesh64.source_faces','result.mesh64.all_source_faces','result.npz','native-invocation.json']}
        receipt['seconds']=time.monotonic()-start;(out/'execution-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return 0 if receipt['status']=='executed' and receipt['owned_scope_inactive'] else 1
if __name__=='__main__':sys.exit(main())
