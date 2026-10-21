from pathlib import Path
import hashlib,json,os,signal,subprocess,time,traceback
R=Path('project-role://engineering-checkout');E=R/'work/962-engineering'
P=E/'head-star-current110-pass62-apply-execution-prep-001';D=E/'head-star-current110-pass62-application-root-execution-001'
A=D/'authorization.json';auth=json.loads(A.read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ident(p):return dict(path=str(p.relative_to(R)) if p.is_relative_to(R) else str(p),sha256=sha(p),bytes=p.stat().st_size)
def freeze(p,j):
 with p.open('x') as f:json.dump(j,f,indent=2,allow_nan=False);f.write('\n')
 p.chmod(0o444)
def pin_map(mapping,absolute=False):
 result={}
 for name,h in mapping.items():
  p=Path(name) if absolute else R/name
  assert p.is_file() and (absolute or not p.is_symlink()) and sha(p)==h,name
  result[name]=ident(p)
 return result
def group_exists(pid):
 try:os.killpg(pid,0);return True
 except ProcessLookupError:return False
def child_groups(pid):
 p=subprocess.run(['/usr/bin/pgrep','-P',str(pid)],capture_output=True,text=True,timeout=2)
 result=[]
 for item in p.stdout.split() if p.returncode==0 else []:
  child=int(item);v=subprocess.run(['/bin/ps','-o','pid=,ppid=,pgid=','-p',str(child)],capture_output=True,text=True,timeout=2).stdout.split()
  if len(v)==3 and tuple(map(int,v))==(child,pid,child):result.append(child)
 return result
actual=P/'actual-contract.json';assert sha(actual)==auth['actual']['sha256']=='bc3bc2847a2fb889c0f3ee51cdc879c2ae79611c36c667c016860e5a5996afba'
assert sha(Path(__file__))==auth['root_controller']['sha256']
for key in ('exact_child_peer','exact_child_bindings','index','preflight','root_source','guards','runtime_admission'):
 pin=auth[key];assert sha(R/pin['path'])==pin['sha256']
assert auth['native_once_authorized'] is True and auth['automatic_retry'] is False
c=json.loads(actual.read_text());out=R/c['output_directory'];assert not out.exists() and not out.is_symlink()
assert c['input_count']==134 and c['controls']['worker_wall_seconds']==1200 and c['controls']['outer_wall_seconds']==1230
before=pin_map(c['input_hashes']);rb=pin_map(c['external_runtime_hashes'],True)
source=E/'head-star-current110-pass62-apply-prep-002/mesh_apply_sicn_proposal.py';assert sha(source)==c['apply_source_sha256']
argv=[c['selected_native_python'],str(source),'--admission',str(E/'atomic-cavity-plane-clip-cap-assembly-surface-admission-001/surface-admission.json'),'--admission-sha256','035c45d02357c9b7375a8e7795f7c1915d7e015ee2b63b576cf181965c96d962','--output',str(out)]
started=time.monotonic();proc=None;owned=set();signals=[];samples=[];stop=None;error=None;interrupted=False;lingering=[]
def request(*_):
 global interrupted
 interrupted=True
def kill_owned(group,sig,label):
 if group_exists(group):os.killpg(group,sig);signals.append(dict(group=group,signal=label))
def stop_and_wait():
 kill_owned(proc.pid,signal.SIGTERM,'SIGTERM')
 try:proc.wait(timeout=8)
 except subprocess.TimeoutExpired:
  for pid in owned:kill_owned(pid,signal.SIGKILL,'SIGKILL_native')
  kill_owned(proc.pid,signal.SIGKILL,'SIGKILL_controller');proc.wait()
old=signal.signal(signal.SIGTERM,request)
try:
 with (D/'stdout.log').open('x') as stdout,(D/'stderr.log').open('x') as stderr:
  proc=subprocess.Popen(argv,cwd=R,stdout=stdout,stderr=stderr,start_new_session=True,env=c['environment'])
  last_sample=-1
  while proc.poll() is None:
   owned.update(child_groups(proc.pid));t=time.monotonic()-started
   if t-last_sample>=.5:
    resident={}
    for pid in [proc.pid,*sorted(owned)]:
     p=subprocess.run(['/bin/ps','-o','rss=','-p',str(pid)],capture_output=True,text=True,timeout=2)
     if p.returncode==0 and p.stdout.strip().isdigit():resident[str(pid)]=int(p.stdout)*1024
    disk=sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) if out.exists() else 0
    samples.append(dict(wall_seconds=t,RSS_bytes_by_owned_PID=resident,aggregate_sampled_RSS_bytes=sum(resident.values()),output_bytes=disk));last_sample=t
    if sum(resident.values())>=8*1024**3:stop='sampled_owned_RSS_8GiB'
    if disk>=1024**3:stop='sampled_output_1GiB'
   if interrupted or t>=1230 or stop:
    stop=stop or ('root_SIGTERM' if interrupted else 'outer1230s');stop_and_wait();break
   time.sleep(.1)
  proc.wait()
except BaseException as exc:
 error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
finally:
 try:
  if proc is not None and proc.poll() is None:stop=stop or 'root_cleanup';stop_and_wait()
  lingering=[pid for pid in owned if group_exists(pid)]
  for pid in lingering:kill_owned(pid,signal.SIGKILL,'SIGKILL_lingering')
  if lingering:stop=stop or 'lingering_owned_native_group'
 finally:signal.signal(signal.SIGTERM,old)
after=pin_map(c['input_hashes']);ra=pin_map(c['external_runtime_hashes'],True)
outputs={}
if out.exists():
 for p in sorted(out.rglob('*')):
  assert not p.is_symlink()
  if p.is_file():outputs[str(p.relative_to(out))]=ident(p)
receipt=json.loads((out/'receipt.json').read_text()) if (out/'receipt.json').is_file() else None
absent=proc is not None and not group_exists(proc.pid) and all(not group_exists(pid) for pid in owned)
closed=dict(schema='962-head-pass62-coordinate-application-root-once-closed/v1',authorization=ident(A),actual=ident(actual),index=auth['index'],exact_child_peer=auth['exact_child_peer'],exact_child_bindings=auth['exact_child_bindings'],root_controller=ident(Path(__file__)),argv=argv,environment=c['environment'],returncode=proc.returncode if proc else None,wall_seconds=time.monotonic()-started,stop_reason=stop,signals=signals,error=error,waited_reaped=proc is not None and proc.poll() is not None,owned_groups_absent=absent,owned_native_group_IDs=sorted(owned),lingering_owned_groups_before_cleanup=lingering,inputs_before=before,inputs_after=after,all134_input_records_unchanged=before==after,runtime_before=rb,runtime_after=ra,all4_selected_runtime_bodies_unchanged=rb==ra,outputs=outputs,stdout=ident(D/'stdout.log'),stderr=ident(D/'stderr.log'),RSS_samples=samples,max_aggregate_sampled_RSS_bytes=max((x['aggregate_sampled_RSS_bytes'] for x in samples),default=0),native_receipt_status=receipt.get('status') if receipt else None,native_receipt_returncode=receipt.get('returncode') if receipt else None,full_head_quality_accepted=False,independent_result_review_complete=False,head_PDE_authorized=False,engineering_accepted=False,physics_qualified=False,material_qualified=False,process_calibrated=False,manufacturing_authorized=False,automatic_retry=False)
freeze(D/'closed-result.json',closed)
print(json.dumps(dict(closed=ident(D/'closed-result.json'),returncode=closed['returncode'],wall_seconds=closed['wall_seconds'],stop_reason=stop,error=error,signals=signals,owned_groups_absent=absent,output_count=len(outputs),native_receipt_status=closed['native_receipt_status'])),flush=True)
if proc is None or proc.returncode not in (0,2) or stop or error or not absent or before!=after or rb!=ra:raise SystemExit(2)
