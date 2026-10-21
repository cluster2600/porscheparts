"""Run exact planar-patch remeshing in a bounded owned CGAL container."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid
IMAGE='sha256:7ed241be10194d98e4ae750cb7f983b0d501742f1ac651580b86c165cba39537'


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--binary',type=Path,required=True);a=p.parse_args();out=a.output.resolve();mesh=a.mesh.resolve()
    if out.exists():raise ValueError('Fresh output required')
    source=Path(__file__).resolve().parent;root=Path(__file__).resolve().parents[5];audit=root/'parts/993-eng-carrier-0001/source/remesh-20261016/audit.py';worker=a.binary.resolve()
    inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [mesh,worker,Path(__file__)]};out.mkdir(parents=True);(out/'output').mkdir();owner=uuid.uuid4().hex;name='carrier-planar-'+owner[:12]
    cmd=['docker','run','--rm','--pull=never','--name',name,'--label',f'carrier.audit.owner={owner}','--cidfile',str(out/'cid.txt'),'--network=none','--cpus=1','--memory=4g','--memory-swap=4g','--pids-limit=64','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--tmpfs','/tmp:rw,size=128m','--user',f'{os.getuid()}:{os.getgid()}','-v',f'{mesh}:/input/mesh.mesh64:ro','-v',f'{worker}:/source/remesh-planar:ro','-v',f'{out}/output:/output','--entrypoint','/usr/bin/timeout',IMAGE,'--kill-after=5s','230','/source/remesh-planar','/input/mesh.mesh64','/output/result']
    (out/'plan.json').write_text(json.dumps(dict(argv=cmd,image=IMAGE,owner=owner,name=name,input_sha256=inputs),indent=2)+'\n');start=time.monotonic();timed_out=False
    with (out/'stdout.log').open('w')as stdout,(out/'stderr.log').open('w')as stderr:
        try:result=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=260);rc=result.returncode
        except subprocess.TimeoutExpired:
            timed_out=True;rc=124
            check=subprocess.run(['docker','inspect','--format','{{index .Config.Labels "carrier.audit.owner"}}',name],capture_output=True,text=True)
            if check.returncode==0 and check.stdout.strip()==owner:subprocess.run(['docker','rm','-f',name],capture_output=True,check=True)
    receipt=dict(actual_returncode=rc,outer_timeout=timed_out,elapsed_seconds=time.monotonic()-start,container_removed=subprocess.run(['docker','inspect',name],capture_output=True).returncode!=0,inputs_unchanged=inputs=={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [mesh,worker,Path(__file__)]})
    (out/'actual-terminal.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
    if rc:return rc
    report=json.loads((out/'output/result.json').read_text());print(json.dumps(report));return 0 if not report['output_vertices_absent_from_input']and receipt['inputs_unchanged']and receipt['container_removed']else 2

if __name__=='__main__':raise SystemExit(main())
