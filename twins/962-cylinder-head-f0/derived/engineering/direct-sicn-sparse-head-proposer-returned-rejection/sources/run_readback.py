"""One fresh expanded sparse-FD coordinate proposal; reviewed pins required."""
from pathlib import Path
import argparse,hashlib,json,os,re,signal,subprocess,threading,time
OUT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract-sha256',required=True);args=parser.parse_args()
 path=OUT/'frozen-contract.json'
 if not re.fullmatch('[0-9a-f]{64}',args.contract_sha256) or sha(path)!=args.contract_sha256:raise ValueError('Reviewed exact frozen contract required')
 c=json.loads(path.read_text());py=Path(c['native_python'])
 if sha(OUT/'reader.py')!=c['reader_sha256'] or sha(Path(__file__).resolve())!=c['runner_sha256'] or sha(py.resolve())!=c['runtime']['python_executable_sha256']:raise ValueError('Reader, runner or interpreter changed')
 if any((OUT/n).exists() or (OUT/n).is_symlink() for n in ['native.log','execution-receipt.json','fixture-report.json']):raise ValueError('One fresh expanded analytic proposal only; preserve previous outputs')
 started=time.monotonic();process=timer=None;stopped={'reason':None};lock=threading.Lock();samples=[]
 def stop(reason):
  with lock:
   if stopped['reason'] is None:
    stopped['reason']=reason
    if process is not None:
     try:os.killpg(process.pid,signal.SIGKILL)
     except ProcessLookupError:pass
 sigterm_requested=False
 def request_sigterm(*_):
  nonlocal sigterm_requested
  sigterm_requested=True
 previous_sigterm=signal.getsignal(signal.SIGTERM)
 try:
  with (OUT/'native.log').open('x') as log:
   try:
    signal.signal(signal.SIGTERM,request_sigterm)
    process=subprocess.Popen([str(py),'-B',str(OUT/'reader.py')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env={'PATH':'/usr/bin:/bin','LANG':'C','PYTHONUTF8':'1','OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','VECLIB_MAXIMUM_THREADS':'2','PYTHONDONTWRITEBYTECODE':'1'})
    timer=threading.Timer(max(0.,300-(time.monotonic()-started)),lambda:stop('direct_sicn_sparse_head_deadline'));timer.daemon=True;timer.start()
    while process.poll() is None and not sigterm_requested:
     try:
      ps=subprocess.run(['/bin/ps','-o','rss=','-p',str(process.pid)],capture_output=True,text=True,timeout=2)
      if process.poll() is not None:break
      rss=int(ps.stdout.strip())*1024;samples.append(dict(wall_seconds=time.monotonic()-started,RSS_bytes=rss))
      if rss>=8*1024**3:stop('sampled_RSS_stop')
      if sum(p.stat().st_size for p in OUT.iterdir() if p.is_file())>=16*1024**2:stop('sampled_output_disk_stop')
     except (OSError,ValueError,subprocess.SubprocessError):
      if process.poll() is None:stop('RSS_observation_failed')
     try:process.wait(timeout=.5)
     except subprocess.TimeoutExpired:pass
   finally:
    try:
     if timer is not None:timer.cancel()
     if process is not None:
      if process.poll() is None:stop('controller_SIGTERM' if sigterm_requested else 'controller_interrupted')
      process.wait()
    finally:
     if sigterm_requested and stopped['reason'] is None:stopped['reason']='controller_SIGTERM'
     signal.signal(signal.SIGTERM,previous_sigterm)
 finally:
  elapsed=time.monotonic()-started
  if elapsed>=300:stopped['reason']=stopped['reason'] or 'direct_sicn_sparse_head_deadline'
  output_bytes=sum(p.stat().st_size for p in OUT.iterdir() if p.is_file())
  if output_bytes>=16*1024**2:stopped['reason']=stopped['reason'] or 'sampled_output_disk_stop'
  report=dict(scope='one_sparse_expanded_coordinate_proposal',returncode=process.returncode if process is not None else None,stop_reason=stopped['reason'],wall_seconds=elapsed,hard_wall_seconds=300,sampled_RSS_stop_bytes=8*1024**3,threads=2,sampled_output_stop_bytes=16*1024**2,final_output_bytes_before_receipt=output_bytes,hard_OS_CPU_quota_applied=False,hard_address_space_limit_applied=False,RSS_samples=samples,max_observed_RSS_bytes=max((s['RSS_bytes'] for s in samples),default=0),reader_sha256=sha(OUT/'reader.py'),runner_sha256=sha(Path(__file__).resolve()),contract_sha256=sha(path),native_log_sha256=sha(OUT/'native.log') if (OUT/'native.log').is_file() else None,fixture_report_sha256=sha(OUT/'fixture-report.json') if (OUT/'fixture-report.json').is_file() else None,declared_operation_counts={'gmsh_generate':0,'gmsh_createGeometry':0,'gmsh_optimize':0,'trust_constr_minimize_invocations':1,'gmsh_write_mesh':0,'solve':0},operation_counts_are_declarations_not_observed=True,manufacturing_authorized=False)
  with (OUT/'execution-receipt.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
 return 0 if process is not None and process.returncode==0 and stopped['reason'] is None and (OUT/'fixture-report.json').is_file() else 2
if __name__=='__main__':raise SystemExit(main())
