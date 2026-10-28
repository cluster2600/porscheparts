"""HELD one-shot standalone18 guard owner. Root admission required; no app/plugin/native run."""
from pathlib import Path
import hashlib,json,os,re,resource,signal,subprocess,sys,time,traceback
R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E=R/'work/962-engineering'
H=E/'cp1-oneway-cooling-release-richardson2-observer003-guard-runtime-prep-001'
X=E/'cp1-oneway-cooling-release-richardson2-observer003-guard-execution-prep-002'
D=E/'cp1-oneway-cooling-release-richardson2-observer003-guard-root-execution-001'
CAP=32*1024**2
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

def provider_links(paths):
 return {name:dict(is_symlink=Path(name).is_symlink(),raw_target=os.readlink(name) if Path(name).is_symlink() else None,resolved=str(Path(name).resolve(strict=True))) for name in paths}

def loaded_trace(path,declared):
 text=path.read_bytes().decode('utf-8');rows=[];unparsed=[]
 for line in text.splitlines():
  if not line.startswith('dyld'):continue
  match=re.fullmatch(r'dyld(?:\[\d+\])?:\s+(?:loaded:\s+)?(?:<[^>]+>\s+)?(/.*)',line)
  if not match:unparsed.append(line);continue
  name=match.group(1);system=name.startswith(('/usr/lib/','/System/Library/','/System/Volumes/Preboot/Cryptexes/OS/'))
  resolved=str(Path(name).resolve()) if name.startswith(str(E/'moose-local-installed-002')+'/') else name
  rows.append(dict(raw=line,path=name,resolved=resolved,OS_system_image_attribution=system,shared_cache_placement_observed=False))
 observed={x['resolved'] for x in rows};expected={x['resolved'] for x in declared.values()}
 moose=str(E/'moose-local-installed-002/lib/combined/libmoose-opt.0.dylib')
 return dict(rows=rows,unparsed_dyld_rows=unparsed,declared_direct_provider_paths_observed=sorted(expected&observed),declared_direct_provider_paths_not_observed=sorted(expected-observed),expected_MOOSE_provider_observed=moose in observed,additional_non_system_paths=sorted({x['resolved'] for x in rows if not x['OS_system_image_attribution'] and x['resolved'] not in expected}),full_transitive_or_ABI_acceptance=False)

# Root supplies the exact future admission digest; preparation itself carries no launch authority.
assert len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1]), 'HELD: root admission digest required'
A=D/'admission.json';assert rec(A)['sha256']==sys.argv[1]
auth=json.loads(A.read_text());actual_path=X/'actual-contract.json';preflight_path=X/'input-runtime-preflight.json'
actual=json.loads(actual_path.read_text());preflight=json.loads(preflight_path.read_text());plan_path=H/'held-runtime-plan.json';plan=json.loads(plan_path.read_text())
assert auth['schema']=='962-observer003-root-standalone18-guard-admission/v1'
assert auth['actual']==rec(actual_path) and auth['controller']==rec(Path(__file__)) and auth['preflight']==rec(preflight_path)
assert auth['guard_execution_authorized'] is True and auth['invocations']==1 and auth['expected_assertions']==18 and auth['automatic_retry'] is False
assert all(auth[k] is False for k in ['plugin_load_authorized','host_execution_authorized','native_execution_authorized','physical_acceptance'])
assert actual['controller']==rec(Path(__file__)) and actual['preflight']==rec(preflight_path) and actual['held_plan']==rec(plan_path)
assert actual['argv']==plan['argv'] and len(actual['argv'])==1 and actual['environment']==plan['environment'] and actual['cwd']==plan['cwd']==str(D)
assert actual['expected_assertions']==18 and actual['guard_source']==plan['source_assertion_census']['source']
assert all(actual[k] is False for k in ['guard_execution_authorized','runtime_probe_authorized','plugin_load_authorized','host_execution_authorized','native_execution_authorized','ABI_acceptance'])
assert actual['controls']==plan['proposed_controls'] and auth['controls']==actual['controls']
assert actual['outer_python']==preflight['outer_python'] and str(Path(sys.executable).resolve())==preflight['outer_python']['resolved']
records=preflight['protected_records'];direct={str(q):rec(q) for q in [actual_path,preflight_path,Path(__file__),A]};assert not set(records)&set(direct)
pins={**records,**direct};before=check(pins);links_before=provider_links(preflight['declared_provider_records'])
assert not before['changed'] and links_before==preflight['provider_path_metadata']
assert not any((D/n).exists() for n in ['receipt.json','run-started.json','guard.stdout','guard.stderr','tmp'])
(D/'tmp').mkdir();(D/'run-started.json').write_text(json.dumps(dict(actual=rec(actual_path),admission=rec(A)))+'\n')
receipt=dict(schema='962-observer003-once-standalone18-guard-receipt/v1',actual=rec(actual_path),admission=rec(A),controller=rec(Path(__file__)),preflight=rec(preflight_path),before=before,provider_paths_before=links_before,expected_assertions=18,resource_samples=[],resource_observation_exit_races=[],guard_process_started=False,returncode=None,termination=None,standalone18_guards_completed=False,plugin_loaded=False,host_executed=False,native_executed=False,ABI_acceptance=False,physical_acceptance=False,loaded_library_attribution_accepted=False,automatic_retry=False)
proc=None;failure=None;started=time.monotonic()
try:
 with (D/'guard.stdout').open('xb') as out,(D/'guard.stderr').open('xb') as err:
  proc=subprocess.Popen(actual['argv'],cwd=D,env=actual['environment'],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,preexec_fn=limits);receipt['guard_process_started']=True;receipt['pid']=proc.pid
  while proc.poll() is None:
   if time.monotonic()-started>60:raise ValueError('60s one-guard wall cap')
   if output_size(D)>CAP:raise ValueError('32MiB owned output cap')
   try:s=sample(proc.pid)
   except Exception as exc:
    if proc.poll() is not None:receipt['resource_observation_exit_races'].append(dict(error=repr(exc),direct_process_returncode=proc.returncode,elapsed_seconds=time.monotonic()-started));break
    raise
   s['elapsed_seconds']=time.monotonic()-started;receipt['resource_samples'].append(s)
   if s['RSS_bytes']>2*1024**3:raise ValueError('2GiB sampled owned-group RSS cap')
   time.sleep(.05)
  proc.wait(timeout=8)
 receipt['returncode']=proc.returncode
 if group_exists(proc.pid):raise ValueError('Owned group remains after normal guard exit')
 receipt['owned_group_absent']=True
 if proc.returncode:raise ValueError('Standalone guard failed; no retry')
 if output_size(D)>CAP:raise ValueError('32MiB completion output cap')
 if (D/'guard.stdout').read_bytes()!=b'':raise ValueError('Unexpected own guard stdout; preserve exact output')
 receipt['standalone18_guards_completed']=True
 try:receipt['loaded_trace']=loaded_trace(D/'guard.stderr',preflight['provider_path_metadata'])
 except Exception:receipt['loaded_trace_error']=traceback.format_exc()
except Exception:
 failure=traceback.format_exc()
 if proc is not None:
  receipt['returncode']=proc.poll();receipt['termination']=stop_wait(proc);receipt['returncode']=proc.returncode;receipt['owned_group_absent']=receipt['termination']['group_absent']
finally:
 receipt['failure']=failure;receipt['elapsed_seconds']=time.monotonic()-started
 receipt['after']=check(pins);receipt['provider_paths_after']=provider_links(preflight['declared_provider_records'])
 receipt['all_declared_inputs_and_control_records_unchanged']=not receipt['after']['changed'] and before['observed_sha256']==receipt['after']['observed_sha256']
 receipt['all_declared_provider_path_associations_unchanged']=receipt['provider_paths_after']==links_before
 if not receipt['all_declared_inputs_and_control_records_unchanged'] or not receipt['all_declared_provider_path_associations_unchanged']:receipt['standalone18_guards_completed']=False
 if 'loaded_trace' not in receipt and 'loaded_trace_error' not in receipt and (D/'guard.stderr').exists():
  try:receipt['loaded_trace']=loaded_trace(D/'guard.stderr',preflight['provider_path_metadata'])
  except Exception:receipt['loaded_trace_error']=traceback.format_exc()
 receipt['peak_observed_owned_group_RSS_bytes']=max((x['RSS_bytes'] for x in receipt['resource_samples']),default=None)
 receipt['RSS_peak_scope']='Sampled observations only; null means no successful sample, never an invented zero.'
 receipt['peak_observed_threads_nongating']=max((x['threads'] for x in receipt['resource_samples'] if x['threads'] is not None),default=None)
 receipt['owned_outputs']={n:rec(D/n) for n in ['guard.stdout','guard.stderr','run-started.json'] if (D/n).exists()}
 receipt['owned_output_bytes_before_receipt']=output_size(D)
 (D/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
raise SystemExit(0 if receipt['standalone18_guards_completed'] and failure is None else 2)
