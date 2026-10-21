"""Root-authorized once-only guard dependency link; no source compilation or runtime test."""
from pathlib import Path
import hashlib,json,os,resource,signal,subprocess,time,traceback
R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E=R/'work/962-engineering'
D=E/'cp1-oneway-cooling-release-richardson2-observer003-build-root-execution-006'
B=E/'cp1-oneway-cooling-release-richardson2-END181-dof-map-observer-prep-003/build-006'
CAP=64*1024**2
GRANT='305d8ae8868f8b96009cf2f4b61e982782f5bc36bbcfac3d50c65f7a440fef22'
def rec(p):
 h=hashlib.sha256();size=0
 with p.open('rb') as f:
  while True:
   b=f.read(1024**2)
   if not b:break
   h.update(b);size+=len(b)
 return dict(path=str(p.relative_to(R)) if p.is_relative_to(R) else str(p),sha256=h.hexdigest(),bytes=size)

def group_exists(pid):
 try:os.killpg(pid,0);return True
 except ProcessLookupError:return False

def check(records):
 changed={};digest=hashlib.sha256();count=0
 for name,pin in sorted(records.items()):
  path=Path(name) if Path(name).is_absolute() else R/name
  try:
   got=rec(path);digest.update(json.dumps(got,sort_keys=True).encode());count+=1
   if got!=pin:changed[name]=dict(expected=pin,actual=got)
  except Exception as exc:changed[name]=repr(exc)
 return dict(count=count,observed_sha256=digest.hexdigest(),changed=changed)

def output_size(root):
 size=0
 for p in root.rglob('*'):
  if p.is_symlink():raise ValueError('Unexpected owned output symlink: '+str(p))
  if p.is_file():size+=p.stat().st_size
 return size

def stop_wait(proc):
 actions=[]
 if group_exists(proc.pid):
  try:os.killpg(proc.pid,signal.SIGTERM);actions.append('TERM')
  except ProcessLookupError:pass
 try:proc.wait(timeout=8)
 except subprocess.TimeoutExpired:pass
 if group_exists(proc.pid):
  try:os.killpg(proc.pid,signal.SIGKILL);actions.append('KILL')
  except ProcessLookupError:pass
 proc.wait(timeout=8);deadline=time.monotonic()+8
 while group_exists(proc.pid) and time.monotonic()<deadline:time.sleep(.05)
 return dict(actions=actions,returncode=proc.returncode,group_absent=not group_exists(proc.pid))

def limits():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(CAP,CAP))

def sample(pgid):
 env={'PATH':'/usr/bin:/bin','LC_ALL':'C'}
 ps=subprocess.run(['/bin/ps','-axo','pid=,pgid=,rss=,stat='],capture_output=True,text=True,env=env,timeout=5)
 if ps.returncode:raise ValueError('RSS ps failed: '+ps.stderr)
 live={};zombies=[];owned_rows=[]
 for row in ps.stdout.splitlines():
  x=row.split()
  if len(x)>=2 and (x[1]==str(pgid) or x[0]==str(pgid)):
   if len(x)!=4 or not all(v.isdigit() for v in x[:3]):
    raise ValueError('Missing/nonnumeric owned RSS data: '+repr(row))
   if int(x[1])!=pgid:raise ValueError('Direct wrapper PGID changed: '+repr(row))
   rss=int(x[2])*1024
   owned_rows.append(dict(raw=row,pid=int(x[0]),pgid=int(x[1]),reported_RSS_KiB=int(x[2]),RSS_bytes=rss,state=x[3]))
   if x[3].startswith('Z'):zombies.append(int(x[0]))
   else:live[int(x[0])]=rss
 if not owned_rows:raise ValueError('No owned resource rows observed')

 thread_observation=dict(observed_counts={},unobserved_pids=sorted(live),error=None)
 try:
  if not live:raise ValueError('No non-zombie PID available for non-gating thread observation')
  tp=subprocess.run(['/bin/ps','-M','-p',','.join(map(str,live)),'-o','pid='],capture_output=True,text=True,env=env,timeout=5)
  counts={}
  for row in tp.stdout.splitlines():
   x=row.split()
   if x and x[-1].isdigit() and int(x[-1]) in live:
    pid=int(x[-1]);counts[pid]=counts.get(pid,0)+1
  thread_observation=dict(observed_counts=counts,unobserved_pids=sorted(set(live)-set(counts)),returncode=tp.returncode,error=tp.stderr if tp.returncode else None)
 except Exception as exc:thread_observation['error']=repr(exc)
 # Thread snapshots are non-gating and follow the RSS snapshot. Missing values stay unknown.
 return dict(RSS_bytes=sum(row['RSS_bytes'] for row in owned_rows),processes=len(owned_rows),raw_owned_rows=owned_rows,threads=sum(thread_observation['observed_counts'].values()) if thread_observation['observed_counts'] else None,thread_observation=thread_observation,zombie_pids=zombies)
G=D/'link-correction-grant.json';assert rec(G)['sha256']==GRANT
grant=json.loads(G.read_text());actual_path=D/'actual-contract.json';preflight_path=D/'input-preflight.json';plan_path=D/'finite-link-argv.json'
actual=json.loads(actual_path.read_text());preflight=json.loads(preflight_path.read_text());plan=json.loads(plan_path.read_text())
assert grant['link_execution_authorized'] and grant['invocations']==1 and not grant['automatic_retry'] and not grant['source_recompilation_authorized'] and not grant['guard_execution_authorized'] and not grant['host_or_plugin_or_native_execution_authorized']
assert actual['controller']==rec(Path(__file__)) and actual['preflight']==rec(preflight_path) and actual['grant']==rec(G) and actual['plan']==rec(plan_path)==grant['finite_plan']
assert actual['argv']==plan['argv'] and actual['controls']==grant['controls']
assert actual['argv'][0]=='/Library/Developer/CommandLineTools/usr/bin/ld' and actual['argv'][actual['argv'].index('-o')+1]==str(B/'guard_rows')
records=preflight['protected_records'];direct={str(p):rec(p) for p in [actual_path,preflight_path,Path(__file__)]};assert not set(records)&set(direct);pins={**records,**direct}
before=check(pins);assert not before['changed'];assert not B.exists() and not (D/'receipt.json').exists();B.mkdir();(B/'tmp').mkdir()
receipt=dict(schema='962-observer003-once-framework-dependency-link-receipt/v1',actual=rec(actual_path),controller=rec(Path(__file__)),grant=rec(G),before=before,resource_samples=[],resource_observation_exit_races=[],returncode=None,link_completed=False,guard_executed=False,plugin_or_host_or_native_executed=False,ABI_acceptance=False,automatic_retry=False)
proc=None;failure=None;started=time.monotonic();requests=[]
def record_controller_stop(signum,frame):requests.append(dict(signal=signum,name=signal.Signals(signum).name,elapsed_seconds=time.monotonic()-started))
signal.signal(signal.SIGTERM,record_controller_stop);signal.signal(signal.SIGINT,record_controller_stop)
try:
 if requests:raise ValueError('Controller stop requested before link')
 with (B/'link.stdout').open('xb') as out,(B/'link.stderr').open('xb') as err:
  proc=subprocess.Popen(actual['argv'],cwd=B,env=actual['environment'],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,preexec_fn=limits);receipt['pid']=proc.pid
  while proc.poll() is None:
   if requests:raise ValueError('Controller interruption requested')
   if time.monotonic()-started>120:raise ValueError('120s link wall cap')
   if output_size(B)>CAP:raise ValueError('64MiB owned output cap')
   try:s=sample(proc.pid)
   except Exception as exc:
    if proc.poll() is not None:receipt['resource_observation_exit_races'].append(dict(error=repr(exc),direct_process_returncode=proc.returncode));break
    raise
   s['elapsed_seconds']=time.monotonic()-started;receipt['resource_samples'].append(s)
   if s['RSS_bytes']>2*1024**3:raise ValueError('2GiB sampled owned-group RSS cap')
   time.sleep(.05)
  proc.wait(timeout=8)
 receipt['returncode']=proc.returncode
 if group_exists(proc.pid):raise ValueError('Owned group remains after normal link exit')
 receipt['owned_group_absent']=True
 if requests:raise ValueError('Controller interruption requested; preserve linker result')
 if proc.returncode:raise ValueError('Corrected link failed; no retry')
 if output_size(B)>CAP:raise ValueError('64MiB completion output cap')
 receipt['actual_guard_binary']=rec(B/'guard_rows');receipt['link_completed']=True
except Exception:
 failure=traceback.format_exc()
 if proc is not None:
  try:receipt['termination']=stop_wait(proc)
  except Exception:receipt['cleanup_error']=traceback.format_exc()
  finally:receipt['returncode']=proc.poll();receipt['owned_group_absent']=not group_exists(proc.pid)
finally:
 receipt['failure']=failure;receipt['controller_stop_requests']=requests;receipt['elapsed_seconds']=time.monotonic()-started;receipt['after']=check(pins)
 receipt['all_declared_inputs_and_controls_unchanged']=not receipt['after']['changed'] and before['observed_sha256']==receipt['after']['observed_sha256']
 if requests or not receipt['all_declared_inputs_and_controls_unchanged']:receipt['link_completed']=False
 receipt['peak_sampled_owned_group_RSS_bytes']=max((x['RSS_bytes'] for x in receipt['resource_samples']),default=None);receipt['peak_observed_threads_nongating']=max((x['threads'] for x in receipt['resource_samples'] if x['threads'] is not None),default=None)
 try:receipt['owned_output_bytes']=output_size(B)
 except Exception:receipt['output_census_error']=traceback.format_exc();receipt['link_completed']=False
 receipt['owned_outputs']={str(p.relative_to(B)):rec(p) for p in B.rglob('*') if p.is_file() and not p.is_symlink()}
 (D/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
raise SystemExit(0 if receipt['link_completed'] and failure is None and not requests else 2)
