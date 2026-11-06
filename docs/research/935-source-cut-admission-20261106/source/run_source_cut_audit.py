"""Run the fixed source cut audit with a real child handle and shared limits."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda:stream.read(1024**2),b''):h.update(data)
    return h.hexdigest()


def save(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--job',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    spec=json.loads(args.job.read_text());source=Path(spec['inputs'][-1]['path'])
    assert source.name=='audit_source_cuts.py' and sha(source)==spec['inputs'][-1]['sha256']
    args.output.mkdir(mode=0o700,exist_ok=False);started=time.monotonic();complete=False;rows=[];stop=False
    def interrupt(signum,frame):
        nonlocal stop
        stop=True
    signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
    environment=os.environ.copy();environment.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    try:
        for name,extra in [('controls',['--controls-only']),('source',[])]:
            command=[sys.executable,'-B',str(source),'--job',str(args.job),'--output',str(args.output/name),*extra]
            before=time.monotonic();peak=0;limited=False
            with (args.output/(name+'.log')).open('x') as log:
                child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=environment,start_new_session=True)
                save(args.output/(name+'-running.json'),dict(pid=child.pid,argv=command,epoch=time.time()))
                try:
                    while child.poll() is None:
                        time.sleep(.5)
                        r=subprocess.run(['ps','-p',str(child.pid),'-o','rss='],capture_output=True,text=True)
                        if r.stdout.strip():peak=max(peak,int(r.stdout.strip()))
                        if stop or time.monotonic()-started>300 or peak>4*1024**2 or shutil.disk_usage(args.output).free<4*1024**3:
                            limited=True;os.killpg(child.pid,signal.SIGTERM);break
                    try:child.wait(timeout=10)
                    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                finally:
                    if child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
            row=dict(stage=name,exit_code=child.returncode,controller_limit_reached=limited,seconds=time.monotonic()-before,
                     sampled_peak_rss_kib=peak,log_sha256=sha(args.output/(name+'.log')),exact_owned_child_reaped=True)
            save(args.output/(name+'-execution.json'),row);rows.append(row);print(json.dumps(row),flush=True)
            assert child.returncode==0 and not limited
        report=json.loads((args.output/'source/report.json').read_text());assert len(report['planes'])==3
        for item in spec['inputs']:assert sha(item['path'])==item['sha256']
        complete=True
    finally:
        save(args.output/'terminal.json',dict(complete=complete,source_sha256=sha(__file__),job_sha256=sha(args.job),
             stages=rows,seconds=time.monotonic()-started,all_owned_children_reaped=True,physical_acceptance=False,manufacturing_authorized=False))
        save(args.output/'manifest.json',dict(complete=complete,files=[dict(path=str(p.relative_to(args.output)),bytes=p.stat().st_size,sha256=sha(p))
             for p in sorted(args.output.rglob('*')) if p.is_file()]))


if __name__=='__main__':main()
