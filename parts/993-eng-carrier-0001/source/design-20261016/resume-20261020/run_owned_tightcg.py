"""Run an explicitly separate source-tightened CG numerical experiment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--deck',type=Path,required=True);p.add_argument('--mesh',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=int,default=300);p.add_argument('--memory-gib',type=int,choices=[6,8,12],default=6);p.add_argument('--build-receipt',type=Path,required=True);a=p.parse_args()
    build=json.loads(a.build_receipt.read_text())
    if build['actual_returncode']!=0 or not build['inputs_unchanged'] or not build['container_removed']:raise ValueError('Successful immutable owned build required')
    image=build['new_image'];binary=build['output_sha256']['ccx-tightcg'];program='/usr/local/bin/ccx-tightcg'
    if not image.startswith('sha256:')or len(image)!=71 or any(c not in '0123456789abcdef'for c in image[7:]):raise ValueError('Pinned experimental image required')
    if a.output.exists():raise ValueError('Fresh output required')
    if not 1<=a.seconds<=1800:raise ValueError('Execution bound must be 1..1800 seconds')
    out=a.output.resolve();out.mkdir(parents=True);case=out/'case';case.mkdir();shutil.copyfile(a.deck,case/'job.inp')
    if a.mesh:shutil.copyfile(a.mesh,case/'mesh.inp')
    paths=[a.deck.resolve(),Path(__file__).resolve(),a.build_receipt.resolve(),case/'job.inp']+([a.mesh.resolve(),case/'mesh.inp']if a.mesh else[]);inputs={str(p):sha(p)for p in paths}
    owner=uuid.uuid4().hex;name='carrier-ccx-'+owner[:12]
    limits=['--rm','--pull=never','--network=none','--cpus=1',f'--memory={a.memory_gib}g',f'--memory-swap={a.memory_gib}g','--pids-limit=128','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges']
    probe=subprocess.run(['docker','run',*limits,'--entrypoint','/usr/bin/sha256sum',image,program],capture_output=True,text=True,timeout=30)
    (out/'binary-probe.json').write_text(json.dumps(dict(argv=probe.args,returncode=probe.returncode,stdout=probe.stdout,stderr=probe.stderr),indent=2)+'\n')
    if probe.returncode or probe.stdout.split()[0]!=binary:raise ValueError('Pinned CCX binary identity differs')
    cmd=['docker','run',*[x for x in limits if x!='--rm'],'--name',name,'--label',f'carrier.ccx.owner={owner}','--cidfile',str(out/'cid.txt'),'--tmpfs','/tmp:rw,size=128m','--user',f'{os.getuid()}:{os.getgid()}','-v',f'{case}:/case:rw','-w','/case','-e','OMP_NUM_THREADS=1','-e','CCX_NPROC_RESULTS=1','-e','OPENBLAS_NUM_THREADS=1','--entrypoint','/usr/bin/timeout',image,'--kill-after=5s',str(a.seconds),program,'-i','job']
    (out/'plan.json').write_text(json.dumps(dict(argv=cmd,image=image,ccx_binary_sha256=binary,program=program,source_CG_tolerance=1e-12,original_acceptance_tolerances_changed=False,owner=owner,name=name,input_sha256=inputs),indent=2)+'\n');start=time.monotonic();timed_out=False
    with (out/'stdout.log').open('w')as stdout,(out/'stderr.log').open('w')as stderr:
        try:result=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=a.seconds+30);rc=result.returncode
        except subprocess.TimeoutExpired:
            timed_out=True;rc=124
            check=subprocess.run(['docker','inspect','--format','{{index .Config.Labels "carrier.ccx.owner"}}',name],capture_output=True,text=True)
            if check.returncode==0 and check.stdout.strip()==owner:subprocess.run(['docker','rm','-f',name],capture_output=True,check=True)
    state_probe=subprocess.run(['docker','inspect','--format','{{json .State}}',name],capture_output=True,text=True)
    state=None
    if state_probe.returncode==0:
        raw=json.loads(state_probe.stdout);state={key:raw.get(key)for key in ['Status','Running','OOMKilled','ExitCode','Error']}
        ownership=subprocess.run(['docker','inspect','--format','{{index .Config.Labels \"carrier.ccx.owner\"}}',name],capture_output=True,text=True)
        if ownership.returncode!=0 or ownership.stdout.strip()!=owner:raise ValueError('Owned container identity differs before cleanup')
        subprocess.run(['docker','rm','-f',name],capture_output=True,check=True)
    text=(out/'stdout.log').read_text(errors='replace')
    receipt=dict(actual_returncode=rc,container_terminal_state=state,memory_limit_GiB=a.memory_gib,outer_timeout=timed_out,elapsed_seconds=time.monotonic()-start,container_removed=subprocess.run(['docker','inspect',name],capture_output=True).returncode!=0,inputs_unchanged=inputs=={str(p):sha(p)for p in paths},solver_finished_marker='Job finished' in text,solver_error_marker='*ERROR' in text.upper(),output_sha256={p.name:sha(p)for p in case.iterdir()if p.is_file()})
    (out/'actual-terminal.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items()if k!='output_sha256'}))
    return rc if rc else(0 if receipt['inputs_unchanged']and receipt['container_removed']and receipt['solver_finished_marker']and not receipt['solver_error_marker']else 2)

if __name__=='__main__':raise SystemExit(main())
