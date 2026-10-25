"""Two-hour native parallel assembly with serial result recovery; at-most-240 GiB address-space cap."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--binary',type=Path,required=True);p.add_argument('--deck',type=Path,required=True);p.add_argument('--mesh',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--expected-binary',required=True);p.add_argument('--seconds',type=int,default=7200);p.add_argument('--memory-gib',type=int,default=110);p.add_argument('--threads',type=int,default=8);a=p.parse_args()
    if a.output.exists()or not 1<=a.seconds<=7200 or not 1<=a.memory_gib<=240 or not 1<=a.threads<=8:raise ValueError('Fresh bounded run required')
    binary=a.binary.resolve()
    if sha(binary)!=a.expected_binary:raise ValueError('Qualified native binary identity differs')
    a.output.mkdir(parents=True);case=(a.output/'case').resolve();case.mkdir();shutil.copyfile(a.deck,case/'job.inp')
    if a.mesh:shutil.copyfile(a.mesh,case/'mesh.inp')
    paths=[a.deck.resolve(),binary,Path(__file__).resolve(),case/'job.inp']+([a.mesh.resolve(),case/'mesh.inp']if a.mesh else[]);inputs={str(x):sha(x)for x in paths};env=os.environ.copy();env.update(OMP_NUM_THREADS=str(a.threads),CCX_NPROC_RESULTS='1',OPENBLAS_NUM_THREADS='1');cmd=['/usr/bin/time','-v','stdbuf','-oL','-eL',str(binary),'-i','job'];(a.output/'plan.json').write_text(json.dumps(dict(argv=cmd,working_directory=str(case),input_sha256=inputs,threads_requested=a.threads,results_threads_requested=1,memory_virtual_limit_GiB=a.memory_gib,wall_limit_seconds=a.seconds,execution='owned native process inside approved leased runtime'),indent=2)+'\n')
    def bounds():resource.setrlimit(resource.RLIMIT_AS,(a.memory_gib*1024**3,)*2)
    started=time.monotonic();timed_out=False
    with(a.output/'stdout.log').open('w')as stdout,(a.output/'stderr.log').open('w')as stderr:
        child=subprocess.Popen(cmd,cwd=case,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True,preexec_fn=bounds)
        try:rc=child.wait(timeout=a.seconds)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=10)
            rc=124
    text=(a.output/'stdout.log').read_text(errors='replace');report=dict(actual_returncode=rc,outer_timeout=timed_out,elapsed_seconds=time.monotonic()-started,process_reaped=child.returncode is not None,inputs_unchanged=inputs=={str(x):sha(x)for x in paths},solver_finished_marker='Job finished'in text,solver_error_marker='*ERROR'in text.upper(),native_binary_sha256=a.expected_binary,output_sha256={x.name:sha(x)for x in case.iterdir()if x.is_file()})
    (a.output/'actual-terminal.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='output_sha256'}));return rc if rc else(0 if report['inputs_unchanged']and report['process_reaped']and report['solver_finished_marker']and not report['solver_error_marker']else 2)

if __name__=='__main__':raise SystemExit(main())
