"""Run one PicoGK closing study under the catalogue's machine-wide lock."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import tempfile
import time
import uuid


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def limits():
    os.nice(10)
    resource.setrlimit(resource.RLIMIT_CPU,(2400,2420))


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--dotnet',type=Path,required=True);p.add_argument('--assembly',type=Path,required=True);p.add_argument('--mode',choices=['control','carrier'],required=True);p.add_argument('--input',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--voxel',type=float,required=True);p.add_argument('--radius',type=float,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    if a.mode=='carrier'and not a.input:raise ValueError('Carrier input required')
    out=a.output.resolve();out.mkdir(parents=True);(out/'output').mkdir();source=Path(__file__).resolve().parent/'picogk-closing';assembly=a.assembly.resolve();dotnet=a.dotnet.resolve();paths=[Path(__file__).resolve(),dotnet,*sorted(assembly.parent.glob('*.dll')),*sorted(assembly.parent.glob('*.dylib')),*sorted(source.glob('*'))]+([a.input.resolve()]if a.input else[]);inputs={str(p):sha(p)for p in paths if p.is_file()}
    owner=uuid.uuid4().hex;lock=Path(tempfile.gettempdir())/'picogk-catalog.lock';value=f'{os.getpid()} {time.time()} carrier-closing-{owner}\n'.encode()
    cmd=[str(dotnet),str(assembly),a.mode,str(a.input.resolve())if a.input else'-',str(out/'output'),str(a.voxel),str(a.radius)]
    (out/'plan.json').write_text(json.dumps(dict(argv=cmd,owner=owner,lock=str(lock),input_sha256=inputs,resources=dict(wall_seconds=300,CPU_seconds=[2400,2420],sampled_process_RSS_limit_bytes=6*1024**3,nice=10),thread_environment=dict(OMP_NUM_THREADS='1',TBB_NUM_THREADS='1'),native_thread_limit_independently_verified=False),indent=2)+'\n')
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,value);os.close(fd);start=time.monotonic();peak=0;reason=None;child=None
    try:
        env=os.environ.copy();env.update(OMP_NUM_THREADS='1',TBB_NUM_THREADS='1',DYLD_LIBRARY_PATH=str(assembly.parent))
        with (out/'stdout.log').open('w')as stdout,(out/'stderr.log').open('w')as stderr:
            child=subprocess.Popen(cmd,cwd=out,env=env,stdout=stdout,stderr=stderr,start_new_session=True,preexec_fn=limits)
            while child.poll()is None:
                sample=subprocess.run(['ps','-o','rss=','-p',str(child.pid)],capture_output=True,text=True)
                if sample.returncode==0 and sample.stdout.strip():peak=max(peak,int(sample.stdout.strip())*1024)
                if peak>6*1024**3 or time.monotonic()-start>300:
                    reason='sampled_RSS_limit'if peak>6*1024**3 else'wall_limit';break
                time.sleep(.5)
            if child.poll()is None:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=10)
            rc=child.wait()
    finally:
        if child is not None and child.poll()is None:
            os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=10)
        owned=lock.exists()and lock.read_bytes()==value
        if owned:lock.unlink()
    receipt=dict(actual_returncode=rc,termination_reason=reason,elapsed_seconds=time.monotonic()-start,peak_sampled_RSS_bytes=peak,child_reaped=child is not None and child.returncode is not None,owned_lock_released=owned and not lock.exists(),inputs_unchanged=inputs=={str(p):sha(p)for p in paths if p.is_file()})
    (out/'actual-terminal.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));return rc if rc else(0 if receipt['inputs_unchanged']and receipt['owned_lock_released']else 2)

if __name__=='__main__':raise SystemExit(main())
