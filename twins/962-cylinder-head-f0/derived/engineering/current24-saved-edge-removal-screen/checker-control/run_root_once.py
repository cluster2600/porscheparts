"""HELD ONE independent saved55 edge-removal verification; root admission required."""
from pathlib import Path
import hashlib,json,os,re,resource,signal,subprocess,sys,time,traceback
R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E=R/'work/962-engineering'
X=E/'head-star-current24-edge-removal-independent-verifier-execution-prep-001'
D=E/'head-star-current24-edge-removal-independent-verifier-root-execution-001'
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
auth=json.loads(A.read_text());actual_path=X/'actual-contract.json';case_path=X/'preflight.json'
runtime_path=E/'head-star-current24-interior-flip-guards-execution-prep-002/runtime-preflight.json'
actual=json.loads(actual_path.read_text());case=json.loads(case_path.read_text());runtime=json.loads(runtime_path.read_text())
assert auth['schema']=='962-current24-independent-saved55-edge-verifier-root-admission/v1'
assert auth['actual']==rec(actual_path) and auth['controller']==rec(Path(__file__)) and auth['preflight']==rec(case_path) and auth['runtime_preflight']==rec(runtime_path)
assert auth['verification_execution_authorized'] is True and type(auth['invocations']) is int and auth['invocations']==1
assert auth['checker_source_peer_reviewed_and_accepted'] is True and auth['exact_child_peer_reviewed_and_accepted'] is True and auth['automatic_retry'] is False
assert auth['analytic_guard_groups']==9 and auth['controls']==actual['controls']
assert all(auth[k] is False for k in ['native_execution_authorized','geometry_write_authorized','global_embedding_or_infeasibility_authorized','physical_acceptance'])
assert actual['schema']=='962-current24-independent-saved55-edge-verifier-held-actual/v1'
assert actual['controller']==rec(Path(__file__)) and actual['preflight']==rec(case_path) and actual['runtime_preflight']==rec(runtime_path)
assert all(actual[k] is False for k in ['verification_execution_authorized','native_execution_authorized','geometry_write_authorized','global_embedding_or_infeasibility_authorized','physical_acceptance','automatic_retry'])
assert actual['selected_interpreter']==runtime['selected_interpreter']
assert str(Path(sys.executable).resolve())==runtime['observed']['resolved_executable'] and sys.version==runtime['observed']['version']
assert sys.flags.isolated==1 and sys.flags.dont_write_bytecode==1 and sys.flags.no_site==1 and sys.flags.optimize==0
assert 'site' not in sys.modules and '_distutils_hack' not in sys.modules and runtime['observed']['flags']['no_site']==1
assert actual['argv']==[runtime['observed']['resolved_executable'],'-B','-I','-S',str(R/actual['checker_source']['path']),'--verify']
assert actual['cwd']==str(D) and actual['checker_source']==rec(R/actual['checker_source']['path'])
assert actual['controls']==dict(wall_seconds=60,TERM_grace_seconds=8,KILL_wait_seconds=8,sampled_owned_RSS_bytes=2147483648,total_owned_output_bytes=33554432,sample_seconds=.05,thread_environment=1,retries=0)
assert actual['environment']==dict(PATH='/usr/bin:/bin',LC_ALL='C',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',TMPDIR=str(D/'tmp'))
records=actual['protected_records'];assert len(records)==actual['protected_record_count']==50 and case['protected_records']==records
assert case['controller']==rec(Path(__file__)) and case['runtime_preflight']==rec(runtime_path)
runtime_records=runtime['runtime_files'];assert len(runtime_records)==91 and not set(records)&set(runtime_records)
direct={str(p):rec(p) for p in [actual_path,case_path,runtime_path,Path(__file__),A]}
for role in ['exact_child_peer','exact_child_bindings']:
 pin=auth[role];path=Path(pin['path']) if Path(pin['path']).is_absolute() else R/pin['path']
 assert rec(path)==pin and str(path) not in direct;direct[str(path)]=pin
assert len(direct)==7 and not set(records)&set(direct) and not set(runtime_records)&set(direct)
pins={**records,**runtime_records,**direct};assert len(pins)==actual['expected_total_records']==148
before=check(pins);links_before=provider_links(runtime_records)
assert not before['changed'] and links_before==runtime['runtime_path_metadata']
os_before=subprocess.run(['/usr/bin/sw_vers','-buildVersion'],capture_output=True,text=True,check=True,timeout=5).stdout.strip();assert os_before==runtime['OS_build']
assert set(p.name for p in D.iterdir())=={'admission.json'}, 'Fresh owned directory with admission only required'
(D/'tmp').mkdir();(D/'run-started.json').write_text(json.dumps(dict(actual=rec(actual_path),admission=rec(A),argv=actual['argv'],exact_child_peer=auth['exact_child_peer']))+'\n')
receipt=dict(schema='962-current24-independent-saved55-edge-verification-once-receipt/v1',actual=rec(actual_path),admission=rec(A),controller=rec(Path(__file__)),preflight=rec(case_path),runtime_preflight=rec(runtime_path),exact_child_peer=auth['exact_child_peer'],exact_child_bindings=auth['exact_child_bindings'],before=before,runtime_paths_before=links_before,OS_build_before=os_before,resource_samples=[],resource_observation_exit_races=[],process_started=False,returncode=None,termination=None,complete_independent_verification=False,independent_result_acceptance=False,complete_application_eligibility=None,mesh_application_authorized=False,native_executed=False,physical_acceptance=False,automatic_retry=False)
proc=None;failure=None;started=time.monotonic();controller_stop_requests=[]
old_TERM=signal.signal(signal.SIGTERM,record_controller_stop);old_INT=signal.signal(signal.SIGINT,record_controller_stop)
try:
 if controller_stop_requests:raise ValueError('Stop requested before independent verification')
 with (D/'verifier.stdout.json').open('xb') as out,(D/'verifier.stderr').open('xb') as err:
  proc=subprocess.Popen(actual['argv'],cwd=D,env=actual['environment'],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,preexec_fn=limits);receipt['process_started']=True;receipt['pid']=proc.pid
  while proc.poll() is None:
   if controller_stop_requests:raise ValueError('Controller stop requested; no retry')
   if time.monotonic()-started>60:raise ValueError('60s combined guard and saved-verifier wall cap')
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
 if proc.returncode:raise ValueError('Independent verifier failed; preserve complete outputs, no retry')
 if output_size(D)>CAP:raise ValueError('32MiB completion output cap')
 if (D/'verifier.stderr').read_bytes()!=b'':raise ValueError('Unexpected verifier stderr; preserve all output')
 result_raw=(D/'verifier.stdout.json').read_bytes();result=json.loads(result_raw)
 if result['schema']!='962-current24-independent-saved55-edge-removal-exact-verification/v1' or result['complete_finite_family_verified'] is not True:raise ValueError('Complete exact saved55 verification output required')
 guards=result['analytic_guards']
 expected_names=['right_D1_Q2_2over3','regular_D2_Q2_1','orientation_sign_quality_invariant','coincident_refusal','boundary_and_exact_threshold','maximal_diagonal_Catalan_complete','missing_duplicate_extra_candidate_refusal','disjoint_removal_duplicate_conflict','disconnected_link_no_subset_refusal']
 if guards!=dict(guard_count=9,names=expected_names,all_passed=True):raise ValueError('Nine exact analytic guard groups required')
 if any(type(result[k]) is not int or result[k]!=v for k,v in actual['expected_saved_summary_counts'].items()):raise ValueError('Complete55/1033/current row and conflict metadata parity required')
 if result['inputs_before']!=actual['checker_input_records'] or result['inputs_after']!=actual['checker_input_records']:raise ValueError('All30 fixed verifier inputs beforeafter exact required')
 if result['full271_words499_cells_and_six_typed_hashes_parent_associated'] is not True or result['prior1983_cells66_nodes86_poor_protected'] is not True:raise ValueError('Complete saved context/six hashes/protected history required')
 if result['complete_application_eligibility'] is not None or any(result[k] is not False for k in ['mesh_application_authorized','global_embedding_accepted','global_infeasibility_or_topology_necessity_proved','native_or_physical_or_manufacturing_accepted']):raise ValueError('No global/application/physical qualification')
 for key,pin in actual['expected_report_projection_sha256s'].items():
  if result[key]!=pin:raise ValueError('Full fixed report row projection changed: '+key)
 failed=result['full_candidate_quality_failure_IDs']
 if not isinstance(failed,list) or len(failed)!=1033 or len(set(failed))!=len(failed) or hashlib.sha256(json.dumps(failed,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()!=actual['expected_quality_failed_IDs_sha256']:raise ValueError('Every reported quality failure ID must remain, exact order/no subset')
 if result['full_local_finite_pass_IDs']!=[]:raise ValueError('Original all-failed finite result changed; refuse parity')
 if not re.fullmatch('[0-9a-f]{64}',result['exact_conflicting_pair_union_sha256']):raise ValueError('Complete exact pair-union digest required')
 receipt['verification_output']=rec(D/'verifier.stdout.json');receipt['analytic_guards']=guards
 receipt['confirmed_saved_summary_counts']={k:result[k] for k in actual['expected_saved_summary_counts']}
 receipt['confirmed_complete_report_projection_sha256s']={k:result[k] for k in actual['expected_report_projection_sha256s']}
 receipt['quality_failed_candidate_ID_count']=len(failed);receipt['quality_failed_candidate_IDs_sha256']=actual['expected_quality_failed_IDs_sha256']
 receipt['exact_conflicting_pair_union_sha256']=result['exact_conflicting_pair_union_sha256'];receipt['complete_application_eligibility']=None
 receipt['complete_independent_verification']=True
except Exception:
 failure=traceback.format_exc()
 if proc is not None:
  try:receipt['termination']=stop_wait(proc)
  except Exception:receipt['cleanup_error']=traceback.format_exc()
  finally:receipt['returncode']=proc.poll();receipt['owned_group_absent']=not group_exists(proc.pid)
finally:
 receipt['elapsed_seconds']=time.monotonic()-started;receipt['after']=check(pins)
 try:receipt['runtime_paths_after']=provider_links(runtime_records)
 except Exception:receipt['runtime_paths_after']=None;receipt['runtime_paths_after_error']=traceback.format_exc()
 try:receipt['OS_build_after']=subprocess.run(['/usr/bin/sw_vers','-buildVersion'],capture_output=True,text=True,check=True,timeout=5).stdout.strip()
 except Exception:receipt['OS_build_after']=None;receipt['OS_build_after_error']=traceback.format_exc()
 receipt['all_bound_files_unchanged']=not receipt['after']['changed'] and before['observed_sha256']==receipt['after']['observed_sha256'];receipt['all_runtime_paths_unchanged']=receipt['runtime_paths_after']==links_before;receipt['OS_build_unchanged']=receipt['OS_build_after']==os_before
 signal.signal(signal.SIGINT,old_INT);signal.signal(signal.SIGTERM,old_TERM)
 receipt['stop_handler_cutoff_elapsed_seconds']=time.monotonic()-started;receipt['controller_stop_requests']=list(controller_stop_requests);receipt['controller_interruption_requested']=bool(controller_stop_requests)
 receipt['stop_scope']='Handled requests before restoring original handlers only; postcutoff nonzero/partial/absent owner remains incomplete.'
 if controller_stop_requests and failure is None:failure='Stop requested before cutoff; refuse completion'
 receipt['failure']=failure
 receipt['complete_independent_verification']=bool(receipt['complete_independent_verification'] and failure is None and not controller_stop_requests and proc is not None and proc.returncode==0 and receipt.get('owned_group_absent') is True and receipt['all_bound_files_unchanged'] and receipt['all_runtime_paths_unchanged'] and receipt['OS_build_unchanged'])
 receipt['peak_sampled_owned_RSS_bytes']=max((r['RSS_bytes'] for r in receipt['resource_samples']),default=None);receipt['RSS_scope']='Sampled only; numericzero retained, missing/nonnumeric never invented; not hardquota/truepeak.'
 receipt['owned_outputs']={n:rec(D/n) for n in ['verifier.stdout.json','verifier.stderr','run-started.json'] if (D/n).exists()}
 receipt['owned_output_bytes_before_receipt']=output_size(D)
 encoded=(json.dumps(receipt,indent=2)+'\n').encode()
 if receipt['owned_output_bytes_before_receipt']+len(encoded)>CAP:
  sys.stderr.write('INCOMPLETE: full receipt exceeds remaining32MiB; all raw outputs retained, no receipt written\n')
  raise SystemExit(2)
 with (D/'receipt.json').open('xb') as out:out.write(encoded)
 if output_size(D)>CAP:raise SystemExit(2)
raise SystemExit(0 if receipt['complete_independent_verification'] and not controller_stop_requests else 2)
