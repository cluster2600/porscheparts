"""Build a separate source-tightened CG experiment in an owned local container."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

BASE='sha256:c9772ae9223a4f800a3ceda77d2494e67e34c8526eb0f204b3c8e052266641b4'
ARCHIVES={'calculix-ccx_2.21.orig.tar.bz2':'51d229aee320cf685216d360f7c04f9a57af0148fbe840483a964c86c315da82','calculix-ccx_2.21-1.debian.tar.xz':'6c2a934b66491c9e916cbf6328167d417f7e985b380e200facf92c3e953d255f'}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--archives',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    out=a.output.resolve();out.mkdir(parents=True);context=out/'context';context.mkdir();results=out/'output';results.mkdir();source=Path(__file__).resolve().parent/'dependencies/ccx-tightcg-2.21'
    for name,digest in ARCHIVES.items():
        file=a.archives/name
        if sha(file)!=digest:raise ValueError('Pinned Debian archive differs: '+name)
        shutil.copyfile(file,context/name)
    for name in ['build.sh','tighten.py']:shutil.copyfile(source/name,context/name)
    inputs={str(p):sha(p)for p in [*sorted(context.iterdir()),Path(__file__)]};owner=uuid.uuid4().hex;name='carrier-ccx-build-'+owner[:12]
    cmd=['docker','run','--pull=never','--name',name,'--label',f'carrier.ccx.build.owner={owner}','--network=bridge','--cpus=2','--memory=2g','--memory-swap=2g','--pids-limit=256','-v',f'{context}:/source:ro','-v',f'{results}:/output:rw','--entrypoint','/usr/bin/timeout',BASE,'--kill-after=5s','1200','/bin/sh','/source/build.sh']
    (out/'plan.json').write_text(json.dumps(dict(argv=cmd,base_image=BASE,owner=owner,container_name=name,input_sha256=inputs,network_scope='Public Debian package installation inside isolated builder',source_archives_sha256=ARCHIVES),indent=2)+'\n');start=time.monotonic();rc=None;image=None;state=None
    try:
        with(out/'stdout.log').open('w')as stdout,(out/'stderr.log').open('w')as stderr:
            try:rc=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=1230).returncode
            except subprocess.TimeoutExpired:rc=124
        probe=subprocess.run(['docker','inspect','--format','{{json .State}}',name],capture_output=True,text=True)
        if probe.returncode==0:
            raw=json.loads(probe.stdout);state={k:raw.get(k)for k in ['Status','Running','OOMKilled','ExitCode','Error']}
        if rc==0:
            commit=subprocess.run(['docker','commit',name],capture_output=True,text=True,check=True,timeout=120);image=commit.stdout.strip()
            if not image.startswith('sha256:'):raise ValueError('New image identity missing')
    finally:
        probe=subprocess.run(['docker','inspect','--format','{{index .Config.Labels "carrier.ccx.build.owner"}}',name],capture_output=True,text=True)
        if probe.returncode==0:
            if probe.stdout.strip()!=owner:raise ValueError('Builder ownership differs')
            subprocess.run(['docker','rm','-f',name],capture_output=True,check=True)
        receipt=dict(actual_returncode=rc,container_terminal_state=state,elapsed_seconds=time.monotonic()-start,container_removed=subprocess.run(['docker','inspect',name],capture_output=True).returncode!=0,inputs_unchanged=inputs=={str(p):sha(p)for p in [*sorted(context.iterdir()),Path(__file__)]},new_image=image,output_sha256={p.name:sha(p)for p in results.iterdir()if p.is_file()},numerical_controls_passed=False)
        (out/'actual-terminal.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items()if k!='output_sha256'}));return rc if rc else(0 if receipt['container_removed']and receipt['inputs_unchanged']and image else 2)

if __name__=='__main__':raise SystemExit(main())
