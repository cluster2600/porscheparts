from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,time,traceback
R=Path('project-role://engineering-checkout');E=R/'work/962-engineering'
P=E/'cp1-oneway-cooling-release-richardson2-native-execution-prep-001'
D=E/'cp1-oneway-cooling-release-richardson2-native-root-execution-001'
A=D/'authorization.json';auth=json.loads(A.read_text())
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
def children(pid):
 p=subprocess.run(['/usr/bin/pgrep','-P',str(pid)],capture_output=True,text=True,timeout=2)
 return [int(x) for x in p.stdout.split()] if p.returncode==0 else []
def member(pid):
 p=subprocess.run(['/bin/ps','-o','pid=,ppid=,pgid=','-p',str(pid)],capture_output=True,text=True,timeout=2)
 v=p.stdout.split();return tuple(map(int,v)) if len(v)==3 else None
actual=P/'actual-contract.json';assert sha(actual)==auth['actual']['sha256']=='159e63ae039c63df348b978a5759356f361d08234d7a5e70f4ea8c281d6ccc6d'
assert sha(Path(__file__))==auth['root_controller']['sha256']
for key in ('exact_child_peer','exact_child_bindings','index','root_source_and_guards'):
 pin=auth[key];assert sha(R/pin['path'])==pin['sha256']
assert auth['native_once_authorized'] is True and auth['automatic_retry'] is False
c=json.loads(actual.read_text());out=Path(c['output']);assert not out.exists() and not out.is_symlink()
before=input_map(c);rb=runtime_map(c);py=Path(c['outer_python']['path']);pybefore=dict(path=str(py),resolved_path=str(py.resolve()),sha256=sha(py.resolve()),bytes=py.resolve().stat().st_size)
assert pybefore['sha256']==c['outer_python']['sha256'];assert len(before)==168
source=R/c['source']['path'];assert sha(source)==c['source']['sha256']
argv=[str(py),'-I','-B',str(source),'--stage','coupon','--contract',str(actual),'--contract-sha256',sha(actual),'--execute']
started=time.monotonic();proc=None;owned=set();signals=[];samples=[];stop=None;error=None;interrupted=False
def request(*_):
 global interrupted
 interrupted=True
old=signal.signal(signal.SIGTERM,request)
try:
 with (D/'adapter.stdout.log').open('x') as stdout,(D/'adapter.stderr.log').open('x') as stderr:
  proc=subprocess.Popen(argv,cwd=R,stdout=stdout,stderr=stderr,start_new_session=True,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','VECLIB_MAXIMUM_THREADS':'1','FI_PROVIDER':'tcp'})
  last_sample=0
  while proc.poll() is None:
   for pid in children(proc.pid):
    v=member(pid)
    if v and v==(pid,proc.pid,pid):owned.add(pid)
   t=time.monotonic()-started
   if t-last_sample>=.5:
    p=subprocess.run(['/bin/ps','-o','rss=','-p',str(proc.pid)],capture_output=True,text=True,timeout=2)
    if p.returncode==0 and p.stdout.strip().isdigit():samples.append(dict(wall_seconds=t,RSS_bytes=int(p.stdout)*1024))
    last_sample=t
   if interrupted or t>=115:
    stop='root_SIGTERM' if interrupted else 'outer115s'
    os.killpg(proc.pid,signal.SIGTERM);signals.append(dict(group=proc.pid,signal='SIGTERM'))
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
     for pid in owned:
      if group_exists(pid):os.killpg(pid,signal.SIGKILL);signals.append(dict(group=pid,signal='SIGKILL'))
     if group_exists(proc.pid):os.killpg(proc.pid,signal.SIGKILL);signals.append(dict(group=proc.pid,signal='SIGKILL'))
     proc.wait()
    break
   time.sleep(.1)
  proc.wait()
except BaseException as exc:
 error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
finally:
 try:
  if proc is not None and proc.poll() is None:
   os.killpg(proc.pid,signal.SIGTERM);signals.append(dict(group=proc.pid,signal='SIGTERM_cleanup'))
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:
    for pid in owned:
     if group_exists(pid):os.killpg(pid,signal.SIGKILL);signals.append(dict(group=pid,signal='SIGKILL_cleanup'))
    if group_exists(proc.pid):os.killpg(proc.pid,signal.SIGKILL)
    proc.wait()
  lingering=[pid for pid in owned if group_exists(pid)]
  for pid in lingering:
   os.killpg(pid,signal.SIGKILL);signals.append(dict(group=pid,signal='SIGKILL_lingering'))
  if lingering:stop=stop or 'lingering_owned_native_group'
 finally:signal.signal(signal.SIGTERM,old)
after=input_map(c);ra=runtime_map(c);pyafter=dict(path=str(py),resolved_path=str(py.resolve()),sha256=sha(py.resolve()),bytes=py.resolve().stat().st_size)
outputs={}
if out.exists():
 for p in sorted(out.rglob('*')):
  assert not p.is_symlink()
  if p.is_file():outputs[str(p.relative_to(out))]=ident(p)
receipt=json.loads((out/'native-execution.json').read_text()) if (out/'native-execution.json').is_file() else None
absent=proc is not None and not group_exists(proc.pid) and all(not group_exists(pid) for pid in owned)
completed=bool(proc is not None and proc.returncode==0 and stop is None and error is None and absent and receipt and receipt.get('native_execution_completed') is True and receipt.get('process_reaped') is True and before==after and rb==ra and pybefore==pyafter)
closed=dict(schema='962-cooling-release-richardson2-native-root-once-closed/v1',authorization=ident(A),actual=ident(actual),index=auth['index'],child_peer=auth['exact_child_peer'],child_bindings=auth['exact_child_bindings'],root_controller=ident(Path(__file__)),returncode=proc.returncode if proc else None,wall_seconds=time.monotonic()-started,stop_reason=stop,signals=signals,error=error,owned_adapter_group_absent=absent,owned_native_group_IDs=sorted(owned),lingering_owned_groups_before_cleanup=lingering,waited_reaped=proc is not None and proc.poll() is not None,inputs_before=before,inputs_after=after,all_project_and_review_inputs_unchanged=before==after,selected_runtime_before=rb,selected_runtime_after=ra,outer_python_before=pybefore,outer_python_after=pyafter,outputs=outputs,stdout=ident(D/'adapter.stdout.log'),stderr=ident(D/'adapter.stderr.log'),RSS_samples=samples,max_observed_adapter_RSS_bytes=max((x['RSS_bytes'] for x in samples),default=0),native_capture_completed=completed,native_inner_cleanup_wait_attributed_to_source_receipt=True,independent_capture_acceptance=False,complete_native_storage_assessed=False,independent_3D_assessment_performed=False,engineering_accepted=False,physics_qualified=False,material_qualified=False,process_calibrated=False,manufacturing_authorized=False,automatic_retry=False)
freeze(D/'closed-result.json',closed)
print(json.dumps(dict(closed=ident(D/'closed-result.json'),returncode=closed['returncode'],wall_seconds=closed['wall_seconds'],completed=completed,output_count=len(outputs),output_bytes=sum(x['bytes'] for x in outputs.values()),signals=signals,stop=stop,error=error,owned_native_groups=sorted(owned),groups_absent=absent)),flush=True)
if not completed:raise SystemExit(2)
