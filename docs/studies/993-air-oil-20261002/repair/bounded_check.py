#!/usr/bin/env python3
"""Run a full native Boolean argument check in an isolated, bounded process."""
import argparse,json,subprocess,sys,time
from pathlib import Path

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('step',type=Path);ap.add_argument('output',type=Path)
    ap.add_argument('--timeout',type=int,default=420);a=ap.parse_args()
    if a.output.exists():raise ValueError('output_must_be_new')
    a.output.mkdir();t=time.monotonic();r={'timeout_seconds':a.timeout,'input':str(a.step),'status':'running','manufacturing_authorized':False}
    with (a.output/'execution.log').open('w') as stream:
        try:
            p=subprocess.run([sys.executable,'-B','-u',str(Path(__file__).with_name('diagnose.py')),str(a.step),str(a.output/'native-BOP.json')],stdout=stream,stderr=subprocess.STDOUT,timeout=a.timeout)
            r.update(status='completed' if p.returncode==0 else 'worker_failed',returncode=p.returncode)
        except subprocess.TimeoutExpired:
            r.update(status='bounded_timeout_child_stopped',passed=False)
    r['elapsed_seconds']=time.monotonic()-t
    if (a.output/'native-BOP.json').exists():r['passed']=json.loads((a.output/'native-BOP.json').read_text())['passed']
    (a.output/'execution.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
