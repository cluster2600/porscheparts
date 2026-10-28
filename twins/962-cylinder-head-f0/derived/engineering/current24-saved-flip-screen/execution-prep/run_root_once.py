"""HELD ONE fixed15-input saved flip diagnostic; accepted17 gate and root admission required."""
from pathlib import Path
import hashlib,json,os,re,resource,signal,subprocess,sys,time,traceback
R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E=R/'work/962-engineering'
X=E/'head-star-current24-interior-flip-saved-execution-prep-001'
D=E/'head-star-current24-interior-flip-saved-root-execution-001'
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

def record_controller_stop(signum,frame):
 controller_stop_requests.append(dict(signal=signum,name=signal.Signals(signum).name,elapsed_seconds=time.monotonic()-started))

assert len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1]), 'External root admission digest required'
A=D/'admission.json';assert rec(A)['sha256']==sys.argv[1]
auth=json.loads(A.read_text());actual_path=X/'actual-contract.json'
preflight_path=E/'head-star-current24-interior-flip-guards-execution-prep-002/runtime-preflight.json'
actual=json.loads(actual_path.read_text());preflight=json.loads(preflight_path.read_text())
assert auth['schema']=='962-current24-fixed15-saved-flip-root-admission/v1'
assert auth['actual']==rec(actual_path) and auth['controller']==rec(Path(__file__)) and auth['runtime_preflight']==rec(preflight_path)
assert auth['saved_metadata_execution_authorized'] is True and type(auth['invocations']) is int and auth['invocations']==1
assert auth['accepted17_result_reviewed_and_accepted'] is True and auth['automatic_retry'] is False
assert all(auth[k] is False for k in ['native_execution_authorized','geometry_write_authorized','physical_acceptance'])
assert actual['schema']=='962-current24-fixed15-saved-flip-held-actual/v1'
assert actual['controller']==rec(Path(__file__)) and actual['runtime_preflight']==rec(preflight_path)
assert all(actual[k] is False for k in ['saved_execution_authorized','native_execution_authorized','geometry_write_authorized','physical_acceptance','automatic_retry'])
assert actual['selected_interpreter']==preflight['selected_interpreter']
assert str(Path(sys.executable).resolve())==preflight['observed']['resolved_executable'] and sys.version==preflight['observed']['version']
assert sys.flags.isolated==1 and sys.flags.dont_write_bytecode==1 and sys.flags.no_site==1 and sys.flags.optimize==0
assert 'site' not in sys.modules and '_distutils_hack' not in sys.modules
assert preflight['observed']['flags']['no_site']==1
assert actual['controls']==dict(wall_seconds=60,TERM_grace_seconds=8,KILL_wait_seconds=8,sampled_owned_RSS_bytes=2147483648,total_owned_output_bytes=33554432,sample_seconds=.05,thread_environment=1,retries=0) and auth['controls']==actual['controls']
assert actual['child_argv_prefix']==[preflight['observed']['resolved_executable'],'-B','-I','-S',str(R/actual['caller']['path'])]
assert actual['external_actual_digest_append_policy']=='append exactly root admission actual.sha256 as sole caller argument'
argv=actual['child_argv_prefix']+[auth['actual']['sha256']]
assert actual['cwd']==str(D)
assert actual['environment']==dict(PATH='/usr/bin:/bin',LC_ALL='C',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',TMPDIR=str(D/'tmp'))
records=actual['protected_records'];assert len(records)==actual['protected_record_count']
runtime=preflight['runtime_files'];assert len(runtime)==91 and not set(records)&set(runtime)
direct={str(q):rec(q) for q in [actual_path,preflight_path,Path(__file__),A]}
for role in ['exact_child_peer','exact_child_bindings','accepted17_result','accepted17_review','accepted17_acceptance']:
 pin=auth[role];assert isinstance(pin,dict)
 path=Path(pin['path']) if Path(pin['path']).is_absolute() else R/pin['path']
 assert rec(path)==pin and str(path) not in direct;direct[str(path)]=pin
assert not set(records)&set(direct) and not set(runtime)&set(direct)
# The future17 result must be the no-site002 exact child, not the unrun001 history.
gate_pin=auth['accepted17_result'];gate_path=Path(gate_pin['path']) if Path(gate_pin['path']).is_absolute() else R/gate_pin['path']
gate=json.loads(gate_path.read_text())
assert gate['schema']=='962-current24-flip17-once-synthetic-result/v1' and gate['actual']==actual['required17_actual'] and gate['runtime_preflight']==rec(preflight_path)
assert gate['all17_tests_completed'] is True and gate['expected_tests']==17 and gate['returncode']==0 and gate['failure'] is None and gate['controller_stop_requests']==[]
assert gate['all_bound_files_unchanged'] is True and gate['all_runtime_paths_unchanged'] is True and gate['OS_build_unchanged'] is True and gate['owned_group_absent'] is True
pins={**records,**runtime,**direct};before=check(pins);links_before=provider_links(runtime)
assert not before['changed'] and links_before==preflight['runtime_path_metadata']
os_before=subprocess.run(['/usr/bin/sw_vers','-buildVersion'],capture_output=True,text=True,check=True,timeout=5).stdout.strip();assert os_before==preflight['OS_build']
assert set(p.name for p in D.iterdir())=={'admission.json'}, 'Fresh owned output required'
(D/'tmp').mkdir();(D/'run-started.json').write_text(json.dumps(dict(actual=rec(actual_path),admission=rec(A),accepted17_result=gate_pin,caller_argv=argv))+'\n')
receipt=dict(schema='962-current24-fixed15-saved-flip-once-receipt/v1',actual=rec(actual_path),admission=rec(A),controller=rec(Path(__file__)),runtime_preflight=rec(preflight_path),accepted17_evidence={k:auth[k] for k in ['accepted17_result','accepted17_review','accepted17_acceptance']},before=before,runtime_paths_before=links_before,OS_build_before=os_before,resource_samples=[],resource_observation_exit_races=[],process_started=False,returncode=None,termination=None,complete_saved_diagnostic=False,independent_arithmetic_acceptance=False,complete_flip_eligibility=None,mesh_application_authorized=False,native_executed=False,physical_acceptance=False,automatic_retry=False)
proc=None;failure=None;started=time.monotonic();controller_stop_requests=[]
old_TERM=signal.signal(signal.SIGTERM,record_controller_stop);old_INT=signal.signal(signal.SIGINT,record_controller_stop)
try:
 if controller_stop_requests:raise ValueError('Stop requested before saved call')
 with (D/'caller.stdout').open('xb') as out,(D/'caller.stderr').open('xb') as err:
  proc=subprocess.Popen(argv,cwd=D,env=actual['environment'],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,preexec_fn=limits);receipt['process_started']=True;receipt['pid']=proc.pid
  while proc.poll() is None:
   if controller_stop_requests:raise ValueError('Controller stop requested; no retry')
   if time.monotonic()-started>60:raise ValueError('60s saved-call wall cap')
   if output_size(D)>CAP:raise ValueError('32MiB owned output cap')
   try:row=sample(proc.pid)
   except Exception as exc:
    if proc.poll() is not None:receipt['resource_observation_exit_races'].append(dict(error=repr(exc),direct_process_returncode=proc.returncode,elapsed_seconds=time.monotonic()-started));break
    raise
   row['elapsed_seconds']=time.monotonic()-started;receipt['resource_samples'].append(row)
   if row['RSS_bytes']>2*1024**3:raise ValueError('2GiB sampled owned RSS cap')
   time.sleep(.05)
  proc.wait(timeout=8)
 receipt['returncode']=proc.returncode
 if group_exists(proc.pid):raise ValueError('Owned group remains after normal exit')
 receipt['owned_group_absent']=True
 if controller_stop_requests:raise ValueError('Stop requested during final wait')
 if proc.returncode:raise ValueError('Saved caller refused/failed; preserve outputs, no retry')
 if output_size(D)>CAP:raise ValueError('32MiB completion output cap')
 report_raw=(D/'report.json').read_bytes();report=json.loads(report_raw)
 summary=json.loads((D/'caller.stdout').read_bytes())
 if (D/'caller.stderr').read_bytes()!=b'':raise ValueError('Unexpected caller stderr; preserve complete output')
 if summary['driver_calls']!=1 or summary['report']!=rec(D/'report.json'):raise ValueError('One caller/result exact byte association required')
 if report['schema']!='962-current24-complete-saved-interior-flip-local-screen/v1' or report['status']!='complete_saved_local_screen_only_eligibility_unavailable':raise ValueError('Complete fixed saved schema/status required')
 if report['procedure_preservation_passed'] is not True or report['complete_context_byte_identical'] is not True or report['all_finite_rows_retained'] is not True:raise ValueError('Complete preserved context required')
 if report['complete_flip_eligibility'] is not None or report['mesh_application_authorized'] is not False:raise ValueError('Eligibility unavailable/application false required')
 if len(report['complete_context_before']['points'])!=271 or len(report['complete_context_before']['cells'])!=499 or len(report['complete_context_before']['poor'])!=24:raise ValueError('Full271/499/24 scope required')
 if report['association_count']!=len(report['associations']) or report['local_disposition_count']!=len(report['complete_local_dispositions']) or report['association_count']!=report['local_disposition_count']:raise ValueError('Every association disposition required')
 if any(r['complete_flip_eligibility'] is not None or r['mesh_application_authorized'] is not False for r in report['complete_local_dispositions']):raise ValueError('No accepted/applicable flip allowed')
 receipt['report']=rec(D/'report.json');receipt['association_count']=report['association_count'];receipt['local_status_counts']=report['local_status_counts'];receipt['observed_pair_conflict_count']=report['observed_pair_conflict_count']
 receipt['complete_saved_diagnostic']=True
except Exception:
 failure=traceback.format_exc()
 if proc is not None:
  try:receipt['termination']=stop_wait(proc)
  except Exception:receipt['cleanup_error']=traceback.format_exc()
  finally:receipt['returncode']=proc.poll();receipt['owned_group_absent']=not group_exists(proc.pid)
finally:
 receipt['elapsed_seconds']=time.monotonic()-started;receipt['after']=check(pins)
 try:receipt['runtime_paths_after']=provider_links(runtime)
 except Exception:receipt['runtime_paths_after']=None;receipt['runtime_paths_after_error']=traceback.format_exc()
 try:receipt['OS_build_after']=subprocess.run(['/usr/bin/sw_vers','-buildVersion'],capture_output=True,text=True,check=True,timeout=5).stdout.strip()
 except Exception:receipt['OS_build_after']=None;receipt['OS_build_after_error']=traceback.format_exc()
 receipt['all_bound_files_unchanged']=not receipt['after']['changed'] and before['observed_sha256']==receipt['after']['observed_sha256'];receipt['all_runtime_paths_unchanged']=receipt['runtime_paths_after']==links_before;receipt['OS_build_unchanged']=receipt['OS_build_after']==os_before
 signal.signal(signal.SIGINT,old_INT);signal.signal(signal.SIGTERM,old_TERM)
 receipt['stop_handler_cutoff_elapsed_seconds']=time.monotonic()-started;receipt['controller_stop_requests']=list(controller_stop_requests);receipt['controller_interruption_requested']=bool(controller_stop_requests)
 receipt['stop_scope']='Handled requests before restoring original handlers only; postcutoff nonzero/partial/absent owner completion remains incomplete.'
 if controller_stop_requests and failure is None:failure='Stop requested before cutoff; refuse completion'
 receipt['failure']=failure
 receipt['complete_saved_diagnostic']=bool(receipt['complete_saved_diagnostic'] and failure is None and not controller_stop_requests and proc is not None and proc.returncode==0 and receipt.get('owned_group_absent') is True and receipt['all_bound_files_unchanged'] and receipt['all_runtime_paths_unchanged'] and receipt['OS_build_unchanged'])
 receipt['peak_sampled_owned_RSS_bytes']=max((r['RSS_bytes'] for r in receipt['resource_samples']),default=None);receipt['RSS_scope']='Sampled only; numericzero retained, absent/nonnumeric not fabricated; not hardquota/truepeak.'
 receipt['owned_outputs']={n:rec(D/n) for n in ['caller.stdout','caller.stderr','report.json','run-started.json'] if (D/n).exists()}
 receipt['owned_output_bytes_before_receipt']=output_size(D)
 encoded=(json.dumps(receipt,indent=2)+'\n').encode()
 # Aggregate budget includes the COMPLETE receipt. Never truncate report/logs.
 if receipt['owned_output_bytes_before_receipt']+len(encoded)>CAP:
  sys.stderr.write('INCOMPLETE: full receipt exceeds remaining32MiB output budget; raw outputs retained, no receipt written\n')
  raise SystemExit(2)
 with (D/'receipt.json').open('xb') as out:out.write(encoded)
 if output_size(D)>CAP:raise SystemExit(2)
raise SystemExit(0 if receipt['complete_saved_diagnostic'] and not controller_stop_requests else 2)
