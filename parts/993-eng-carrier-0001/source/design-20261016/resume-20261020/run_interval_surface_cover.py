"""Run complete interval surface covers in a pinned, bounded libigl worker."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid
IMAGE='sha256:3ccaf5701c7c9add59eda6e8db918106fc8d51f4c2ef5b148d8079262861c7e1'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--first',type=Path,required=True);p.add_argument('--second',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--worker-script',type=Path);p.add_argument('--reuse-proof-dir',type=Path);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    out=a.output.resolve();out.mkdir(parents=True);(out/'output').mkdir();core=Path(__file__).with_name('interval_surface_cover.py').resolve();worker=(a.worker_script or core).resolve();paths=[a.first.resolve(),a.second.resolve(),worker,core,Path(__file__).resolve()];
    if a.reuse_proof_dir:paths += [a.reuse_proof_dir.resolve()/name for name in ['assessment.json','first-to-second-cover.npz']]
    inputs={str(p):sha(p)for p in paths};owner=uuid.uuid4().hex;name='carrier-interval-cover-'+owner[:12]
    cmd=['docker','run','--rm','--pull=never','--name',name,'--label',f'carrier.interval.owner={owner}','--network=none','--cpus=1','--memory=6g','--memory-swap=6g','--pids-limit=64','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--tmpfs','/tmp:rw,size=128m','--user',f'{os.getuid()}:{os.getgid()}','-v',f'{a.first.resolve()}:/input/first.mesh64:ro','-v',f'{a.second.resolve()}:/input/second.mesh64:ro','-v',f'{worker}:/source/worker.py:ro','-v',f'{core}:/source/interval_surface_cover.py:ro','-v',f'{out}/output:/output','--entrypoint','/usr/bin/timeout',IMAGE,'--kill-after=5s','600','/usr/local/bin/python','-I','-B','/source/worker.py','--first','/input/first.mesh64','--second','/input/second.mesh64','--output','/output/result']
    if a.reuse_proof_dir:
        pos=cmd.index('--entrypoint')
        for file in paths[-2:]:cmd[pos:pos]=['-v',f'{file}:/reuse/{file.name}:ro'];pos+=2
    (out/'plan.json').write_text(json.dumps(dict(argv=cmd,image=IMAGE,owner=owner,name=name,input_sha256=inputs),indent=2)+'\n');start=time.monotonic();outer=False
    with(out/'stdout.log').open('w')as stdout,(out/'stderr.log').open('w')as stderr:
        try:rc=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=630).returncode
        except subprocess.TimeoutExpired:
            outer=True;rc=124;probe=subprocess.run(['docker','inspect','--format','{{index .Config.Labels "carrier.interval.owner"}}',name],capture_output=True,text=True)
            if probe.returncode==0 and probe.stdout.strip()==owner:subprocess.run(['docker','rm','-f',name],capture_output=True,check=True)
    receipt=dict(actual_returncode=rc,outer_timeout=outer,elapsed_seconds=time.monotonic()-start,container_removed=subprocess.run(['docker','inspect',name],capture_output=True).returncode!=0,inputs_unchanged=inputs=={str(p):sha(p)for p in paths})
    (out/'actual-terminal.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));return rc if rc else(0 if receipt['container_removed']and receipt['inputs_unchanged']else 2)

if __name__=='__main__':raise SystemExit(main())
