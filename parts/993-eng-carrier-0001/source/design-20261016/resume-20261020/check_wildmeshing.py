"""Supervised WildMeshing installation control; always retain terminal evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--python',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();python=Path(os.path.abspath(a.python));worker=Path(__file__).resolve().with_name('check_wildmeshing_install.py')
    if out.exists():raise ValueError('Fresh control directory required')
    out.mkdir(parents=True);snap=out/'source';snap.mkdir();(snap/'launcher.py').write_bytes(Path(__file__).read_bytes());(snap/'control.py').write_bytes(worker.read_bytes());worker=snap/'control.py';argv=[str(python),'-I','-B',str(worker),'--output',str(out/'output')];before=hashlib.sha256(worker.read_bytes()).hexdigest();(out/'plan.json').write_text(json.dumps(dict(argv=argv,cwd=str(out),wall_limit_seconds=60,CPU_limit_seconds=60,worker_sha256=before),indent=2)+'\n');start=time.monotonic();reason=None
    def limits():resource.setrlimit(resource.RLIMIT_CPU,(60,65))
    with (out/'stdout.log').open('w')as stdout,(out/'stderr.log').open('w')as stderr:
        process=subprocess.Popen(argv,cwd=out,stdout=stdout,stderr=stderr,start_new_session=True,preexec_fn=limits)
        try:process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            reason='wall_limit';os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
    if process.returncode==-signal.SIGXCPU:reason='CPU_limit'
    receipt=dict(actual_returncode=process.returncode,process_reaped=True,stop_reason=reason,elapsed_seconds=time.monotonic()-start,worker_unchanged=hashlib.sha256(worker.read_bytes()).hexdigest()==before)
    (out/'actual-terminal.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
    if reason:return 124
    if process.returncode:return 2
    data=json.loads((out/'output/assessment.json').read_text());print(data['status']);return 0 if data['status']=='installation_control_passed'and receipt['worker_unchanged']else 2

if __name__=='__main__':raise SystemExit(main())
