"""Bound a native local meshing worker by time, RSS and its owned process group."""
from pathlib import Path
import subprocess,os,signal,time,json,hashlib
w=Path('work/carrier-interface-20261028');out=w/'netgen-carrier-native-005';assert not out.exists();out.mkdir();worker=(w/'netgen_carrier_worker_005.py').resolve();runtime=(w/'runtime-netgen-001/bin/python').absolute();start=time.monotonic();peak=0;reason=None
with(out/'stdout.log').open('w')as stdout,(out/'stderr.log').open('w')as stderr:
 process=subprocess.Popen([str(runtime),str(worker)],stdout=stdout,stderr=stderr,start_new_session=True,env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
 (out/'plan.json').write_text(json.dumps(dict(pid=process.pid,worker=str(worker),runtime=str(runtime),created_epoch=time.time(),maximum_resident_bytes=24*1024**3,maximum_wall_seconds=1850,worker_alarm_seconds=1800),indent=2)+'\n')
 while process.poll()is None:
  probe=subprocess.run(['ps','-p',str(process.pid),'-o','rss='],capture_output=True,text=True);rss=int(probe.stdout.strip()or 0)*1024;peak=max(peak,rss)
  if rss>24*1024**3 or time.monotonic()-start>1850:
   reason='resident_memory_limit'if rss>24*1024**3 else'wall_time_limit'
   try:os.killpg(process.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:process.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
   break
  time.sleep(2)
 rc=process.wait()
report=dict(actual_returncode=rc,termination_reason=reason,peak_observed_resident_bytes=peak,maximum_resident_bytes=24*1024**3,elapsed_seconds=time.monotonic()-start,source_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),worker_reaped=True,manufacturing_authorized=False);(out/'actual-terminal.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
