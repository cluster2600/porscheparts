"""Held exact observer004 passive native capture owner; no launch without root admission."""
from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,time,traceback
import sys,re
R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993');E=R/'work/962-engineering'
P=E/'cp1-oneway-cooling-release-richardson2-observer004-native-measurement-execution-prep-003'
S=E/'cp1-oneway-cooling-release-richardson2-observer004-native-measurement-prep-003'
D=E/'cp1-oneway-cooling-release-richardson2-observer004-native-measurement-root-execution-003'
O=E/'cp1-oneway-cooling-release-richardson2-observer004-native-measurement-003'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def ident(p):return dict(path=str(p.relative_to(R)),sha256=sha(p),bytes=p.stat().st_size)

def freeze(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
 p.chmod(0o444)

def input_map(c):
 result={}
 for name,h in c['input_sha256'].items():
  p=R/name;assert p.is_file() and not p.is_symlink() and sha(p)==h,name
  result[name]=ident(p)
 return result

def runtime_map(c):
 prefix=E/'moose-local-installed-002';files={};links={}
 for name,h in c['runtime_sha256s'].items():
  p=prefix/name;assert p.is_file() and not p.is_symlink() and p.resolve()==p and sha(p)==h,name
  files[name]=ident(p)
 for name,target in c['runtime_symlinks'].items():
  p=prefix/name;assert p.is_symlink() and os.readlink(p)==target and p.resolve().is_relative_to(prefix),name
  links[name]=dict(raw_target=target,resolved_relative=str(p.resolve().relative_to(prefix)))
 return dict(files=files,links=links)

def group_exists(pid):
 try:os.killpg(pid,0);return True
 except ProcessLookupError:return False

def rec(p):
 h=hashlib.sha256();size=0
 with p.open('rb') as f:
  while True:
   b=f.read(1024**2)
   if not b:break
   h.update(b);size+=len(b)
 return dict(path=str(p.relative_to(R)) if p.is_relative_to(R) else str(p),sha256=h.hexdigest(),bytes=size)

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

def children(pid):
 p=subprocess.run(['/usr/bin/pgrep','-P',str(pid)],capture_output=True,text=True,timeout=2)
 if p.returncode==1 and not p.stdout.strip():return []
 if p.returncode!=0:raise ValueError('Owned children query failed: '+repr((p.returncode,p.stdout,p.stderr)))
 return [int(x) for x in p.stdout.split()]

def member(pid):
 p=subprocess.run(['/bin/ps','-o','pid=,ppid=,pgid=','-p',str(pid)],capture_output=True,text=True,timeout=2)
 if p.returncode==1 and not p.stdout.strip():return None
 v=p.stdout.split()
 if p.returncode!=0 or len(v)!=3:raise ValueError('Owned child identity query failed: '+repr((p.returncode,p.stdout,p.stderr)))
 return tuple(map(int,v))

def sample_owned(groups):
 p=subprocess.run(['/bin/ps','-axo','pid=,pgid=,rss=,stat='],capture_output=True,text=True,env={'PATH':'/usr/bin:/bin','LC_ALL':'C'},timeout=2)
 if p.returncode:raise ValueError('Owned group RSS query failed: '+repr((p.returncode,p.stderr)))
 rows=[]
 for line in p.stdout.splitlines():
  v=line.split()
  if len(v)>=2 and (v[1] in {str(g) for g in groups} or v[0] in {str(g) for g in groups}):
   if len(v)!=4 or not all(x.isdigit() for x in v[:3]):raise ValueError('Missing/nonnumeric owned RSS row: '+repr(line))
   if int(v[1]) not in groups:raise ValueError('Owned direct group changed: '+repr(line))
   rows.append(dict(raw=line,pid=int(v[0]),pgid=int(v[1]),RSS_bytes=int(v[2])*1024,state=v[3]))
 missing=[g for g in groups if not any(x['pgid']==g for x in rows) and group_exists(g)]
 if missing:raise ValueError('Live owned group has unavailable RSS: '+repr(missing))
 if not rows:raise ValueError('No owned RSS rows observed')
 return dict(RSS_bytes=sum(x['RSS_bytes'] for x in rows),owned_rows=rows)

def capture(function):
 try:return dict(observed=function(),error=None)
 except Exception as exc:return dict(observed=None,error=repr(exc))

def python_record(c):
 py=Path(c['outer_python']['path'])
 return dict(path=str(py),resolved_path=str(py.resolve()),sha256=sha(py.resolve()),bytes=py.resolve().stat().st_size)

def growth_bytes(output, root_execution, baseline):
    total = 0
    for root in (output, root_execution):
        for p in root.rglob("*"):
            if p.is_symlink():
                raise ValueError("Unexpected output symlink")
            if p.is_file():
                allowance = baseline.get(str(p.relative_to(output)), 0) if root == output else 0
                total += max(0, p.stat().st_size - allowance)
    return total


def inclusive_bytes():return output_size(O)+output_size(D)

def direct_map(a):
 result={}
 for role,pin in a['direct_roles'].items():
  name=pin['path'];path=R/name
  if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or path.resolve()!=path:raise ValueError('Invalid direct control path')
  got=rec(path)
  if got!=pin:raise ValueError('Changed direct control: '+role)
  result[role]=got
 return result

def main():
 started=time.monotonic();interrupted=False;requests=[];proc=None;owned=set();signals=[];samples=[];exit_races=[];stop=None;error=None;lingering=[]
 def request(signum,frame):
  nonlocal interrupted
  interrupted=True;requests.append(dict(signal=signum,name=signal.Signals(signum).name,elapsed_seconds=time.monotonic()-started))
 previous=signal.signal(signal.SIGTERM,request)
 a=None;c=None;before={};after={};outputs={};receipt=None;trace=None
 def stop_wait():
  if proc is not None and proc.poll() is None:
   if group_exists(proc.pid):
    try:os.killpg(proc.pid,signal.SIGTERM);signals.append(dict(group=proc.pid,signal='SIGTERM'))
    except ProcessLookupError:pass
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:
    for g in sorted(owned|{proc.pid}):
     if group_exists(g):
      try:os.killpg(g,signal.SIGKILL);signals.append(dict(group=g,signal='SIGKILL'))
      except ProcessLookupError:pass
    proc.wait(timeout=10)
  if proc is not None:proc.wait(timeout=10)
 try:
  if len(sys.argv)!=2 or not re.fullmatch('[0-9a-f]{64}',sys.argv[1]):raise ValueError('Exact external admission SHA argv required')
  A=D/'authorization.json'
  if not D.is_dir() or D.is_symlink() or not A.is_file() or A.is_symlink() or sha(A)!=sys.argv[1]:raise ValueError('Exact separately sealed root admission required')
  a=json.loads(A.read_text());actual=P/'actual-contract.json';c=json.loads(actual.read_text())
  if a.get('schema')!='962-observer004-native-measurement-root-admission/v1' or a.get('native_once_authorized') is not True or a.get('independent_exact_child_complete') is not True or a.get('root_source_review_complete') is not True or a.get('freshness_and_staging_complete') is not True:raise ValueError('Held source has no native authority')
  if set(a['direct_roles'])!=set(c['future_root_direct_roles']):raise ValueError('Exact nine launch/control roles required')
  if any(a.get(k) is not False for k in ('automatic_retry','assessment_execution_authorized','solver_change_authorized','head_execution_authorized','engineering_accepted','physics_qualified','material_qualified','process_calibrated','manufacturing_authorized')):raise ValueError('No additional scientific authority')
  if a['resources']!=c['resources'] or c['resources']!={'wall_seconds':100,'sampled_RSS_stop_bytes':2147483648,'sampled_output_stop_bytes':536870912} or a['outer_wall_seconds']!=115 or a['root_TERM_grace_seconds']!=10:raise ValueError('Exact inherited100/115/TERM10/2GiB/512MiB controls required')
  before['authorization']=rec(A);before['direct']=direct_map(a)
  if a['direct_roles']['actual']!=rec(actual) or a['direct_roles']['caller']!=c['source'] or a['direct_roles']['root_controller']!=rec(Path(__file__)):raise ValueError('Actual/caller/controller join failed')
  if c.get('authority_at_freeze')!='HELD_ROOT_ADMISSION_REQUIRED' or c.get('native_execution_authorized') is not False:raise ValueError('Exact held actual required')
  if any((D/n).exists() for n in ('adapter.stdout.log','adapter.stderr.log','closed-result.json')):raise ValueError('No retry/previous output namespace allowed')
  if not O.is_dir() or O.is_symlink() or set(p.name for p in O.iterdir())!=set(c['staged_inputs']):raise ValueError('Exactly four separately staged inputs required')
  for name,pin in c['staged_inputs'].items():
   if rec(O/name)!=pin or (O/name).is_symlink():raise ValueError('Staged identity changed')
  historical=json.loads((R/c['historical_native_closed']['path']).read_text());baseline={name:pin['bytes'] for name,pin in historical['outputs'].items()}
  before['staged_inputs']={name:rec(O/name) for name in c['staged_inputs']}
  before['inputs']=input_map(c);before['runtime']=runtime_map(c)
  before['selected_host_records']=check(c['expected_host_records'])
  before['provider_paths']=provider_links(c['expected_provider_paths'])
  before['python']=python_record(c)
  if before['selected_host_records']['changed'] or before['provider_paths']!=c['expected_provider_paths'] or before['python']!=c['outer_python_observed_metadata']:raise ValueError('Held selected-host/provider/Python identities not current')
  if Path(sys.executable).resolve()!=Path(c['outer_python']['path']).resolve():raise ValueError('Use the exact selected original outer Python')
  source=R/c['source']['path']
  if rec(source)!=c['source']:raise ValueError('Changed exact caller')
  argv=[c['outer_python']['path'],'-B','-I','-S',str(source),'--stage','coupon','--contract',str(actual),'--contract-sha256',sha(actual),'--root-admission-sha256',sys.argv[1],'--execute']
  if time.monotonic()-started>=115 or interrupted:raise ValueError('Outer deadline/stop before child launch')
  with (D/'adapter.stdout.log').open('x') as stdout,(D/'adapter.stderr.log').open('x') as stderr:
   proc=subprocess.Popen(argv,cwd=R,stdout=stdout,stderr=stderr,start_new_session=True,env=c['outer_environment'])
   last_sample=-1
   while proc.poll() is None:
    try:
     observation_operation='children(proc.pid)';observation_target_PID=proc.pid
     for pid in children(proc.pid):
      observation_operation='member(pid)';observation_target_PID=pid
      v=member(pid)
      if v==(pid,proc.pid,pid):owned.add(pid)
     elapsed=time.monotonic()-started
     if elapsed-last_sample>=.5:
      observation_operation='sample_owned({proc.pid}|owned)';observation_target_PID=None
      observed=sample_owned({proc.pid}|owned)
      samples.append(dict(wall_seconds=elapsed,**observed));last_sample=elapsed
      if observed['RSS_bytes']>=2147483648:stop=stop or 'sampled_owned_group_RSS_stop'
     observation_operation='inclusive_bytes()';observation_target_PID=None
     if inclusive_bytes()>=536870912:stop=stop or 'inclusive_output_stop'
     observation_operation='growth_bytes(O,D,baseline)';observation_target_PID=None
     if growth_bytes(O,D,baseline)>=33554432:stop=stop or 'incremental_growth_stop'
    except Exception as exc:
     direct_RC=proc.poll()
     if direct_RC is None:stop=stop or 'resource_or_group_observation_failed';error=dict(type=type(exc).__name__,message=str(exc),phase='owned_resource_poll',operation=observation_operation,target_PID=observation_target_PID,elapsed_seconds=time.monotonic()-started,owned_adapter_group_ID=proc.pid,owned_native_group_IDs=sorted(owned),traceback=traceback.format_exc())
     else:exit_races.append(dict(error=repr(exc),direct_returncode=direct_RC,elapsed_seconds=time.monotonic()-started,phase='owned_resource_poll',operation=observation_operation,target_PID=observation_target_PID,owned_adapter_group_ID=proc.pid,owned_native_group_IDs=sorted(owned),traceback=traceback.format_exc()))
    if interrupted:stop=stop or 'root_SIGTERM'
    if time.monotonic()-started>=115:stop=stop or 'outer115s'
    if stop:stop_wait();break
    try:proc.wait(timeout=.1)
    except subprocess.TimeoutExpired:pass
   proc.wait()
 except BaseException as exc:
  error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
 finally:
  try:
   stop_wait()
   lingering=[g for g in sorted(owned|({proc.pid} if proc is not None else set())) if group_exists(g)]
   for g in lingering:
    try:os.killpg(g,signal.SIGKILL);signals.append(dict(group=g,signal='SIGKILL_lingering'))
    except ProcessLookupError:pass
   if lingering:
    stop=stop or 'lingering_owned_native_group';until=time.monotonic()+10
    while any(group_exists(g) for g in lingering) and time.monotonic()<until:time.sleep(.05)
  except Exception as exc:
   stop=stop or 'cleanup_observation_failed';error=error or dict(type=type(exc).__name__,message=str(exc))
 if a is not None and c is not None:
  after={'authorization':capture(lambda:rec(D/'authorization.json')),'staged_inputs':capture(lambda:{name:rec(O/name) for name in c['staged_inputs']}),'direct':capture(lambda:direct_map(a)),'inputs':capture(lambda:input_map(c)),'runtime':capture(lambda:runtime_map(c)),'selected_host_records':capture(lambda:check(c['expected_host_records'])),'provider_paths':capture(lambda:provider_links(c['expected_provider_paths'])),'python':capture(lambda:python_record(c))}
  try:
   for root in (O,D):
    for p in sorted(root.rglob('*')):
     if p.is_symlink():raise ValueError('Unexpected owned output symlink')
     if p.is_file():outputs[str(p.relative_to(R))]=rec(p)
   if (O/'native-execution.json').is_file():receipt=json.loads((O/'native-execution.json').read_text())
   if (O/'native.log').is_file():trace=loaded_trace(O/'native.log',c['expected_provider_paths'])
  except Exception as exc:error=error or dict(type=type(exc).__name__,message=str(exc))
 absent=proc is not None and not group_exists(proc.pid) and all(not group_exists(g) for g in owned)
 identities=bool(before and after and set(before)==set(after) and all(after[k]['error'] is None and before[k]==after[k]['observed'] for k in before))
 plugin=str(E/'cp1-oneway-cooling-release-richardson2-END181-dof-map-observer-prep-004/build-001/libcoupon_end181_observer-opt.dylib')
 plugin_observed=bool(trace and plugin in {r['resolved'] for r in trace['rows']})
 native_group_join=bool(receipt and receipt.get('native_PID') in owned and receipt.get('native_group_absent') is True)
 candidate=bool(proc is not None and proc.returncode==0 and stop is None and error is None and not interrupted and not requests and absent and identities and native_group_join and plugin_observed and receipt and receipt.get('native_execution_completed_candidate') is True and receipt.get('process_reaped') is True)
 closed=dict(schema='962-observer004-native-measurement-root-once-closed/v1',authorization=rec(D/'authorization.json') if (D/'authorization.json').is_file() else None,actual=rec(P/'actual-contract.json'),root_controller=rec(Path(__file__)),returncode=proc.returncode if proc else None,wall_seconds=time.monotonic()-started,stop_reason=stop,signals=signals,error=error,controller_stop_requests=requests,owned_adapter_group_absent=absent,owned_native_group_IDs=sorted(owned),lingering_owned_groups_before_cleanup=lingering,waited_reaped=proc is not None and proc.poll() is not None,before=before,after=after,identities_unchanged=identities,native_group_join=native_group_join,outputs=outputs,RSS_samples=samples,resource_observation_exit_races=exit_races,max_observed_owned_RSS_bytes=max((x['RSS_bytes'] for x in samples),default=None),RSS_scope='sampled aggregate of owned adapter plus verified direct-child native groups',loaded_trace=trace,expected_corrected_plugin_path_observed=plugin_observed,loaded_library_full_transitive_or_ABI_acceptance=False,native_capture_completed_candidate=candidate,completion_requires_outer_RC0_and_root_inclusive_postchecks=True,measurement_stream_map_and_field_completeness_accepted=False,science_or_physical_qualification=False,automatic_retry=False,signal_capture_scope='Latch remains installed through complete receipt write. Scalar flags are prefinal; after handler restoration nonzero outer exit independently refuses acceptance. No all-interpreter-teardown guarantee.',inclusive_owned_bytes_before_receipt=capture(inclusive_bytes))
 freeze(D/'closed-result.json',closed)
 final_size=capture(inclusive_bytes);final_growth=capture(lambda:growth_bytes(O,D,baseline)) if c is not None and "baseline" in locals() else dict(observed=None,error="Historical baseline not observed");elapsed=time.monotonic()-started
 signal.signal(signal.SIGTERM,previous)
 # A signal after this cutoff is outside the saved latch; raw outer0 remains independently mandatory.
 if not candidate or interrupted or requests or final_size['error'] is not None or final_size['observed']>=536870912 or final_growth['error'] is not None or final_growth['observed']>=33554432 or elapsed>=115:
  print('Owner closure refused; retain prefinal candidate receipt and require independent outerRC0.',file=sys.stderr,flush=True);return 2
 return 0

if __name__=='__main__':raise SystemExit(main())
