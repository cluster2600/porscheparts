"""HELD ONE9-test pure QF_NRA synthetic owner; separate root admission required."""
from pathlib import Path
import hashlib,json,os,re,resource,signal,subprocess,sys,time,traceback
started=time.monotonic();controller_stop_requests=[]
R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E=R/'work/962-engineering'
X=E/'head-star-current24-qfnra-word-validator-guards-execution-prep-001'
D=E/'head-star-current24-qfnra-word-validator-guards-root-execution-001'
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

# Preparation supplies no launch authority. Root later seals this external digest.
assert len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1]), 'HELD: external root admission digest required'
A=D/'admission.json';assert rec(A)['sha256']==sys.argv[1]
auth=json.loads(A.read_text());actual_path=X/'actual-contract.json';preflight_path=E/'head-star-current24-edge-removal-guards-execution-prep-001/runtime-preflight.json'
actual=json.loads(actual_path.read_text());preflight=json.loads(preflight_path.read_text())
assert auth['schema']=='962-current24-qfnra-validator9-root-synthetic-admission/v1'
assert auth['actual']==rec(actual_path) and auth['controller']==rec(Path(__file__)) and auth['runtime_preflight']==rec(preflight_path)
assert auth['guard_source_review_complete'] is True
assert auth['synthetic_guard_execution_authorized'] is True and type(auth['invocations']) is int and auth['invocations']==1 and type(auth['expected_tests']) is int and auth['expected_tests']==9
assert auth['automatic_retry'] is False and auth['controls']==actual['controls']
assert all(auth[k] is False for k in ['real_head_data_execution_authorized','real_measurement_data_execution_authorized','native_execution_authorized','geometry_write_authorized','physical_acceptance','real_sampler_main_execution_authorized','native_retry_authorized','real_solver_execution_authorized','real_coordinate_coefficient_execution_authorized','real_model_or_word_execution_authorized','real_word_validator_execution_authorized'])
assert actual['schema']=='962-current24-qfnra-validator9-held-synthetic-actual/v1'
assert actual['controller']==rec(Path(__file__)) and actual['runtime_preflight']==rec(preflight_path)
assert all(actual[k] is False for k in ['synthetic_execution_authorized','real_head_data_execution_authorized','real_measurement_data_execution_authorized','native_execution_authorized','geometry_write_authorized','physical_acceptance','real_sampler_main_execution_authorized','native_retry_authorized','automatic_retry','real_solver_execution_authorized','real_coordinate_coefficient_execution_authorized','real_model_or_word_execution_authorized','real_word_validator_execution_authorized'])
assert type(actual['expected_tests']) is int and actual['expected_tests']==9 and len(actual['test_methods'])==9 and actual['test_methods']==sorted(set(actual['test_methods']))
assert actual['argv']==[preflight['observed']['resolved_executable'],'-B','-I','-S',str(R/actual['fixture_source']['path'])]
assert actual['cwd']==str(D) and actual['fixture_source']==rec(R/actual['fixture_source']['path'])
assert actual['selected_interpreter']==preflight['selected_interpreter']
assert str(Path(sys.executable).resolve())==preflight['observed']['resolved_executable']
assert sys.version==preflight['observed']['version'] and sys.flags.isolated==1 and sys.flags.dont_write_bytecode==1 and sys.flags.optimize==0 and sys.flags.no_site==1
assert 'site' not in sys.modules and '_distutils_hack' not in sys.modules
assert preflight['observed']['flags']['no_site']==1
assert actual['controls']==dict(wall_seconds=60,TERM_grace_seconds=8,KILL_wait_seconds=8,sampled_owned_RSS_bytes=2147483648,total_owned_output_bytes=33554432,sample_seconds=.05,thread_environment=1,retries=0)
expected_environment=dict(PATH='/usr/bin:/bin',LC_ALL='C',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',TMPDIR=str(D/'tmp'))
assert actual['environment']==expected_environment
records=actual['protected_records'];assert type(actual['protected_record_count']) is int and len(records)==actual['protected_record_count']
runtime=preflight['runtime_files'];assert not set(records)&set(runtime)
direct={str(q):rec(q) for q in [actual_path,preflight_path,Path(__file__),A]}
for role in ['exact_child_peer','exact_child_bindings','guard_source_peer','guard_source_bindings','guard_root_source_review']:
 pin=auth[role];path=Path(pin['path']) if Path(pin['path']).is_absolute() else R/pin['path']
 if role in ['guard_source_peer','guard_source_bindings']:assert pin==actual[role]
 assert rec(path)==pin and str(path) not in direct;direct[str(path)]=pin
assert not set(records)&set(direct) and not set(runtime)&set(direct)
pins={**records,**runtime,**direct}
assert len(runtime)==actual['runtime_record_count']==91 and len(direct)==actual['direct_control_record_count_at_launch']==9
canonical_paths=[str((Path(k) if Path(k).is_absolute() else R/k).resolve(strict=True)) for k in pins]
assert len(set(canonical_paths))==len(pins)==actual['total_record_count_at_launch'], 'Canonical unique complete identity count required'
before=check(pins);links_before=provider_links(runtime)
assert not before['changed'] and links_before==preflight['runtime_path_metadata']
os_before=subprocess.run(['/usr/bin/sw_vers','-buildVersion'],capture_output=True,text=True,check=True,timeout=5).stdout.strip()
assert os_before==preflight['OS_build']
assert set(p.name for p in D.iterdir())=={'admission.json'}, 'Fresh owned directory with admission only required'
(D/'tmp').mkdir();(D/'run-started.json').write_text(json.dumps(dict(actual=rec(actual_path),admission=rec(A),expected_tests=9))+'\n')
receipt=dict(schema='962-current24-qfnra-validator9-once-synthetic-result/v1',actual=rec(actual_path),admission=rec(A),controller=rec(Path(__file__)),runtime_preflight=rec(preflight_path),before=before,runtime_paths_before=links_before,OS_build_before=os_before,expected_tests=9,resource_samples=[],resource_observation_exit_races=[],process_started=False,returncode=None,termination=None,all9_tests_completed=False,earlier_flip_fixture_files_executed=False,real_head_coordinate_field_or_scientific_body_read=False,source_or_descriptor_metadata_read=True,native_executed=False,physical_acceptance=False,automatic_retry=False)
proc=None;failure=None
old_TERM=signal.signal(signal.SIGTERM,record_controller_stop);old_INT=signal.signal(signal.SIGINT,record_controller_stop)
try:
 if controller_stop_requests or time.monotonic()-started>=60:raise ValueError('Controller stop/deadline before synthetic launch')
 with (D/'tests.stdout').open('xb') as out,(D/'tests.stderr').open('xb') as err:
  proc=subprocess.Popen(actual['argv'],cwd=D,env=actual['environment'],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,preexec_fn=limits);receipt['process_started']=True;receipt['pid']=proc.pid
  while proc.poll() is None:
   if controller_stop_requests:raise ValueError('Controller stop requested; no retry')
   if time.monotonic()-started>60:raise ValueError('60s synthetic wall cap')
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
 if controller_stop_requests:raise ValueError('Controller stop requested during final wait')
 if proc.returncode:raise ValueError('Synthetic fixture failed; no retry')
 if output_size(D)>CAP:raise ValueError('32MiB completion output cap')
 if (D/'tests.stdout').read_bytes()!=b'':raise ValueError('Unexpected synthetic stdout; preserve all output')
 text=(D/'tests.stderr').read_bytes().decode('utf-8')
 names=re.findall(r'^([A-Za-z0-9_]+) \(__main__\.IndependentWordValidatorFixtures\) \.\.\. ok$',text,re.M)
 counts=re.findall(r'^Ran ([0-9]+) tests in ([0-9.]+)s$',text,re.M)
 receipt['unittest_test_names']=names;receipt['unittest_count_lines']=counts
 if names!=actual['test_methods'] or len(counts)!=1 or counts[0][0]!='9' or not text.endswith('\nOK\n'):
  raise ValueError('Complete9 named unittest successes and finalOK required')
 receipt['all9_tests_completed']=True
except Exception:
 failure=traceback.format_exc()
 if proc is not None:
  try:receipt['termination']=stop_wait(proc)
  except Exception:receipt['cleanup_error']=traceback.format_exc()
  finally:receipt['returncode']=proc.poll();receipt['owned_group_absent']=not group_exists(proc.pid)
finally:
 receipt['elapsed_seconds']=time.monotonic()-started
 receipt['after']=check(pins)
 try:receipt['runtime_paths_after']=provider_links(runtime)
 except Exception:receipt['runtime_paths_after']=None;receipt['runtime_paths_after_error']=traceback.format_exc()
 try:receipt['OS_build_after']=subprocess.run(['/usr/bin/sw_vers','-buildVersion'],capture_output=True,text=True,check=True,timeout=5).stdout.strip()
 except Exception:receipt['OS_build_after']=None;receipt['OS_build_after_error']=traceback.format_exc()
 receipt['all_bound_files_unchanged']=not receipt['after']['changed'] and before['observed_sha256']==receipt['after']['observed_sha256']
 receipt['all_runtime_paths_unchanged']=receipt['runtime_paths_after']==links_before
 receipt['OS_build_unchanged']=receipt['OS_build_after']==os_before
 # No scientific/synthetic child remains after this cutoff. Later default signals
 # can terminate this owner: absent/partial/nonzero outer receipts stay incomplete.
 signal.signal(signal.SIGINT,old_INT);signal.signal(signal.SIGTERM,old_TERM)
 receipt['stop_handler_cutoff_elapsed_seconds']=time.monotonic()-started
 receipt['controller_stop_requests']=list(controller_stop_requests)
 receipt['controller_interruption_requested']=bool(controller_stop_requests)
 receipt['stop_scope']='Requests handled before restoring handlers only; no all-process-lifetime signal claim.'
 if controller_stop_requests and failure is None:failure='Controller stop requested before handler cutoff; refuse completion'
 receipt['failure']=failure
 receipt['all9_tests_completed']=bool(receipt['all9_tests_completed'] and failure is None and not controller_stop_requests and proc is not None and proc.returncode==0 and receipt.get('owned_group_absent') is True and receipt['all_bound_files_unchanged'] and receipt['all_runtime_paths_unchanged'] and receipt['OS_build_unchanged'])
 receipt['peak_sampled_owned_RSS_bytes']=max((x['RSS_bytes'] for x in receipt['resource_samples']),default=None)
 receipt['RSS_scope']='Sampled only, not hard quota/truepeak; numeric zero retained, missing observations never invented.'
 receipt['owned_outputs']={n:rec(D/n) for n in ['tests.stdout','tests.stderr','run-started.json'] if (D/n).exists()}
 receipt['owned_output_bytes_before_receipt']=output_size(D)
 encoded=(json.dumps(receipt,indent=2)+'\n').encode()
 if receipt['owned_output_bytes_before_receipt']+len(encoded)>CAP:
  receipt['all9_tests_completed']=False;receipt['failure']='32MiB complete receipt/output cap exceeded; incomplete'
  encoded=(json.dumps(receipt,indent=2)+'\n').encode()
 (D/'receipt.json').write_bytes(encoded)
final_bytes=output_size(D);final_elapsed=time.monotonic()-started
if not receipt['all9_tests_completed'] or controller_stop_requests or final_bytes>CAP or final_elapsed>=60:
 print('Final whole-time/inclusive-byte/stop/completion refusal; prefinal receipt is not acceptance.',file=sys.stderr,flush=True)
 raise SystemExit(2)
raise SystemExit(0)
