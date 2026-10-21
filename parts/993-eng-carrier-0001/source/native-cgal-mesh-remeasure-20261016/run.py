"""Bound a new direct measurement using the explicitly pinned existing distance kernel."""
import argparse,hashlib,json,shutil,subprocess,time,uuid
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['input','candidate','final_job','plan','output']:p.add_argument(n,type=Path)
    p.add_argument('--distance-runtime',type=Path,required=True);a=p.parse_args()
    paths={n:getattr(a,n).resolve() for n in ['input','candidate','final_job','plan','output','distance_runtime']};out=paths['output'];assert not out.exists()
    runtime=paths['distance_runtime'];manifest=runtime/'installation-receipt.json';installation=json.loads(manifest.read_text());binary=runtime/'build/carrier_exact_distance'
    assert sha(binary)==installation['binary_sha256']
    assert all(sha(runtime/n)==value for n,value in installation['source_files_sha256'].items())
    base_receipt=Path(installation['CGAL_installation_receipt']);assert sha(base_receipt)==installation['CGAL_installation_receipt_sha256']
    include=base_receipt.parent/'src/CGAL-6.1.3/include'
    headers={str(include/name):value for name,value in {**installation['CGAL_header_sha256'],**installation['distance_header_sha256']}.items()}
    deps={**headers,**installation['runtime_files_sha256'],str(base_receipt):sha(base_receipt)};assert all(sha(n)==value for n,value in deps.items())
    files=[paths['input'],paths['candidate'],paths['plan'],manifest,binary,SOURCE/'run.py',SOURCE/'worker.py']
    files += [paths['final_job']/n for n in ['native.json','audit.json','execution-receipt.json','result.npz']]
    before={str(n):sha(n) for n in files};before.update(deps);out.mkdir(parents=True)
    for n in ['run.py','worker.py']:shutil.copyfile(SOURCE/n,out/n)
    copied={str(out/n):sha(out/n) for n in ['run.py','worker.py']}
    unit='carrier-direct-remeasure-'+uuid.uuid4().hex[:12]+'.scope'
    command=['systemd-run','--user','--scope','--quiet','--unit',unit,'-p','CPUQuota=200%','-p','MemoryMax=4G','-p','MemorySwapMax=0','-p','RuntimeMaxSec=610','timeout','--kill-after=10s','600','bwrap','--ro-bind','/','/','--unshare-net','--unshare-pid','--die-with-parent','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--bind',str(out),'/tmp/output',installation['audit_python'],'/tmp/output/worker.py',str(paths['input']),str(paths['candidate']),str(paths['final_job']),str(paths['plan']),'/tmp/output',str(binary)]
    receipt={'command':command,'unit':unit,'inputs_sha256':before,'copied_sources_sha256':copied,'limits':{'cpu':2,'memory':'4G','swap':0,'seconds':600,'network':'none'}}
    (out/'execution-plan.json').write_text(json.dumps(receipt,indent=2)+'\n');start=time.monotonic();code=None
    try:
        with (out/'stdout.log').open('w') as log:code=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=630).returncode
    finally:
        subprocess.run(['systemctl','--user','kill',unit],capture_output=True,timeout=10);subprocess.run(['systemctl','--user','stop',unit],capture_output=True,timeout=15)
        receipt.update(returncode=code,status='executed' if code==0 else 'rejected_or_failed',seconds=time.monotonic()-start,
            identities_unchanged=all(sha(n)==value for n,value in {**before,**copied}.items()),
            owned_scope_inactive=subprocess.run(['systemctl','--user','is-active',unit],capture_output=True).returncode!=0)
        (out/'execution-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return 0 if code==0 and receipt['identities_unchanged'] and receipt['owned_scope_inactive'] else 1

if __name__=='__main__':raise SystemExit(main())
