"""Compile/run a pinned complete CGAL self-intersection screen in an owned container."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid
IMAGE='sha256:7ed241be10194d98e4ae750cb7f983b0d501742f1ac651580b86c165cba39537'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--compile',action='store_true');p.add_argument('--first',type=Path);p.add_argument('--second',type=Path);p.add_argument('--binary',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    if not a.compile and not all([a.first,a.second,a.binary]):raise ValueError('Both complete meshes and worker binary required')
    out=a.output.resolve();out.mkdir(parents=True);(out/'output').mkdir();source=Path(__file__).with_name('check_self.cpp').resolve();paths=[Path(__file__).resolve(),source]+([]if a.compile else[p.resolve()for p in [a.first,a.second,a.binary]]);inputs={str(p):sha(p)for p in paths};owner=uuid.uuid4().hex;name='carrier-self-' +owner[:12];seconds=180 if a.compile else 300
    cmd=['docker','run','--rm','--pull=never','--name',name,'--label',f'carrier.self.owner={owner}','--network=none','--cpus=1','--memory=6g','--memory-swap=6g','--pids-limit=64','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--tmpfs','/tmp:rw,size=256m','--user',f'{os.getuid()}:{os.getgid()}','-v',f'{out}/output:/output']
    if a.compile:cmd+=['-v',f'{source}:/source/worker.cpp:ro'];worker=['g++','-std=c++17','-O1','-frounding-math','/source/worker.cpp','-o','/output/check-hausdorff','-lgmp','-lmpfr']
    else:
        cmd+=['-v',f'{a.first.resolve()}:/input/first.mesh64:ro','-v',f'{a.second.resolve()}:/input/second.mesh64:ro','-v',f'{a.binary.resolve()}:/source/check-hausdorff:ro'];worker=['/source/check-hausdorff','/input/first.mesh64','/input/second.mesh64','/output/assessment.json']
    cmd+=['--entrypoint','/usr/bin/timeout',IMAGE,'--kill-after=5s',str(seconds),*worker]
    (out/'plan.json').write_text(json.dumps(dict(argv=cmd,image=IMAGE,owner=owner,name=name,input_sha256=inputs,mode='compile'if a.compile else'exact_autorepair_with_post_export_self_intersection_screen'),indent=2)+'\n');start=time.monotonic();outer=False
    with(out/'stdout.log').open('w')as stdout,(out/'stderr.log').open('w')as stderr:
        try:rc=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=seconds+30).returncode
        except subprocess.TimeoutExpired:
            outer=True;rc=124;probe=subprocess.run(['docker','inspect','--format','{{index .Config.Labels "carrier.self.owner"}}',name],capture_output=True,text=True)
            if probe.returncode==0 and probe.stdout.strip()==owner:subprocess.run(['docker','rm','-f',name],capture_output=True,check=True)
    receipt=dict(actual_returncode=rc,outer_timeout=outer,elapsed_seconds=time.monotonic()-start,container_removed=subprocess.run(['docker','inspect',name],capture_output=True).returncode!=0,inputs_unchanged=inputs=={str(p):sha(p)for p in paths},output_sha256={p.name:sha(p)for p in(out/'output').iterdir()if p.is_file()})
    (out/'actual-terminal.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));return rc if rc else(0 if receipt['container_removed']and receipt['inputs_unchanged']else 2)

if __name__=='__main__':raise SystemExit(main())
