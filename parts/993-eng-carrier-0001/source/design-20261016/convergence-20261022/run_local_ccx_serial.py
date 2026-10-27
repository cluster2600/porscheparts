"""Owned serial native solve with a wall deadline and sampled process-RSS ceiling."""
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


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def rss_bytes(text):
    value=text.strip()
    if not value.isdecimal():raise ValueError('Nonnegative process RSS measurement required')
    return int(value)*1024


def stop_and_reap(child):
    if child.poll()is None:
        try:os.killpg(child.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        except PermissionError:
            # Darwin can reject a group signal while its last process is exiting.
            try:child.wait(timeout=.1)
            except subprocess.TimeoutExpired:child.terminate()
        try:child.wait(timeout=10)
        except subprocess.TimeoutExpired:child.kill();child.wait(timeout=10)
    else:child.wait()


def main():
    p=argparse.ArgumentParser(__doc__)
    for name in ['binary','deck','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--mesh',type=Path);p.add_argument('--expected-binary',required=True)
    p.add_argument('--seconds',type=int,required=True);p.add_argument('--rss-gib',type=float,required=True)
    a=p.parse_args()
    if a.output.exists()or not 1<=a.seconds<=1200 or not 1<=a.rss_gib<=24:raise ValueError('Fresh bounded local solve required')
    binary=a.binary.resolve()
    if sha(binary)!=a.expected_binary:raise ValueError('Qualified native binary identity differs')
    a.output.mkdir(parents=True);case=(a.output/'case').resolve();case.mkdir();shutil.copyfile(a.deck,case/'job.inp')
    if a.mesh:shutil.copyfile(a.mesh,case/'mesh.inp')
    inputs=[binary,Path(__file__),a.deck,case/'job.inp']+([a.mesh,case/'mesh.inp']if a.mesh else[])
    identities={str(path):sha(path)for path in inputs}
    env=os.environ.copy();env.update(OMP_NUM_THREADS='1',CCX_NPROC_RESULTS='1',OPENBLAS_NUM_THREADS='1')
    command=[str(binary),'-i','job'];plan=dict(argv=command,working_directory=str(case),input_sha256=identities,
        threads_requested=1,results_threads_requested=1,wall_limit_seconds=a.seconds,
        sampled_RSS_limit_GiB=a.rss_gib,memory_scope='Actual solver PID RSS; 0.5 s waits between probes, 5 s probe timeout; not an OS memory limit',execution='owned local native process')
    (a.output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    def cpu_bound():resource.setrlimit(resource.RLIMIT_CPU,(a.seconds+5,a.seconds+10))
    started=time.monotonic();reason=None;maximum=0
    with(a.output/'stdout.log').open('w')as stdout,(a.output/'stderr.log').open('w')as stderr:
        child=subprocess.Popen(command,cwd=case,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True,preexec_fn=cpu_bound)
        (a.output/'process-identity.json').write_text(json.dumps(dict(pid=child.pid,argv=command,working_directory=str(case)))+'\n')
        try:
            while child.poll()is None:
                if time.monotonic()-started>=a.seconds:reason='wall_timeout';break
                measurement=subprocess.run(['/bin/ps','-o','rss=','-p',str(child.pid)],capture_output=True,text=True,timeout=5)
                if child.poll()is not None:break
                if measurement.returncode:raise ValueError('Live solver RSS observation failed')
                maximum=max(maximum,rss_bytes(measurement.stdout))
                if maximum>a.rss_gib*1024**3:reason='sampled_RSS_limit';break
                try:child.wait(timeout=.5)
                except subprocess.TimeoutExpired:pass
        except Exception as error:reason='monitor_failure:'+type(error).__name__
        finally:
            stop_and_reap(child)
    text=(a.output/'stdout.log').read_text(errors='replace');rc=124 if reason=='wall_timeout'else 125 if reason else child.returncode
    report=dict(actual_returncode=rc,outer_timeout=reason=='wall_timeout',termination_reason=reason,
        elapsed_seconds=time.monotonic()-started,maximum_sampled_solver_RSS_bytes=maximum,
        process_reaped=child.returncode is not None,inputs_unchanged=identities=={str(path):sha(path)for path in inputs},
        solver_finished_marker='Job finished'in text,solver_error_marker='*ERROR'in text.upper(),
        native_binary_sha256=a.expected_binary,output_sha256={x.name:sha(x)for x in case.iterdir()if x.is_file()})
    (a.output/'actual-terminal.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='output_sha256'}))
    return rc if rc else(0 if report['inputs_unchanged']and report['solver_finished_marker']and not report['solver_error_marker']else 2)


if __name__=='__main__':raise SystemExit(main())
