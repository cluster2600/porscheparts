"""Root explicit CLT-linker correction: at most three fixed build commands, stop at first failure.
No guards, host loading, Make or native physics are executed.
"""
from pathlib import Path
import hashlib,json,os,resource,shlex,signal,subprocess,time,traceback
R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E=R/'work/962-engineering'
P=E/'cp1-oneway-cooling-release-richardson2-END181-dof-map-observer-prep-003'
S=E/'moose-public-source-001/moose'
D=E/'cp1-oneway-cooling-release-richardson2-observer003-build-root-execution-005'
A=E/'cp1-observer003-root-build-admission-001/admission.json'
AUTH='d4a07f779dbfeebae57afbc9efcfa52981f016206e35f4c11063d77fb99a0eee'
RECIPE='d29067e60a64c8c2164126ffef1d818ed963c5b22bbabd32813662de4e4e90a4'
G=D/'driver-compatibility-grant-binding.json'
GRANT='91fb221d946ea60b08be978c7599f33cf68b87f3c64baa7a102c2f0f0b102795'
PLAN='2c394d0878f2c862e0134d55c1b6cc33858a106ece7041ede4e4a26d874ca28e'
CLT_LD='/Library/Developer/CommandLineTools/usr/bin/ld'
CAP=64*1024**2

def rec(p):
 h=hashlib.sha256();size=0
 with p.open('rb') as f:
  while True:
   b=f.read(1024**2)
   if not b:break
   h.update(b);size+=len(b)
 return dict(path=str(p.relative_to(R)) if p.is_relative_to(R) else str(p),sha256=h.hexdigest(),bytes=size)
def aliases():
 result={}
 for name in ['mpicxx','clang-19','clang++','arm64-apple-darwin20.0.0-clang++','ld']:
  p=E/'moose-local-installed-002/bin'/name
  result[name]=dict(path=str(p),resolved=str(p.resolve(strict=True)),link=os.readlink(p) if p.is_symlink() else None)
 return result
def group_exists(pid):
 try:os.killpg(pid,0);return True
 except ProcessLookupError:return False
def git_state():
 env={'PATH':'/usr/bin:/bin','LC_ALL':'C','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_TERMINAL_PROMPT':'0'}
 def run(args):
  p=subprocess.run(['/usr/bin/git','-c','core.fsmonitor=false','-c','core.hooksPath=/dev/null','-c','submodule.recurse=false','-C',str(S),*args],env=env,capture_output=True,text=True,timeout=30)
  if p.returncode:raise ValueError(p.stderr)
  return p.stdout.strip()
 state=dict(commit=run(['rev-parse','HEAD']),tree=run(['rev-parse','HEAD^{tree}']),porcelain=run(['status','--porcelain','--untracked-files=all']))
 if state!=dict(commit='7c06bdcefd02f9f31f4508839f21f410561309a4',tree='4106bbd47b9387bda37cff0d679735c57c5391bc',porcelain=''):raise ValueError('Public source not exact and clean')
 return state
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

def dependencies(depfile,ordinal,before):
 if not depfile.exists():return None
 text=depfile.read_text().replace(chr(92)+chr(10),' ')
 names=shlex.split(text.split(':',1)[1])
 rows={};errors={}
 for name in dict.fromkeys(names):
  path=Path(name)
  if not path.is_absolute():path=P/'build-005'/path
  try:rows[str(path)]=dict(record=rec(path),content_identity_known_before_compilation=str(path) in before)
  except Exception as exc:errors[str(path)]=repr(exc)
 out=D/f'step{ordinal}-dependency-headers.json'
 out.write_text(json.dumps(dict(schema='962-observer003-actual-compiler-dependencies/v1',depfile=rec(depfile),headers=rows,errors=errors,full_SDK_or_ABI_equivalence=False),indent=2)+'\n')
 return rec(out)
assert len(AUTH)==64 and all(c in '0123456789abcdef' for c in AUTH), 'HELD: new root admission required'
assert rec(A)['sha256']==AUTH
admission=json.loads(A.read_text());assert admission['compiler_invocations_authorized']==4 and admission['run_each_step_once_stop_first_failure'] and not admission['automatic_retry']
assert not admission['guard_execution_authorized'] and not admission['host_library_load_authorized'] and not admission['native_case_or_field_capture_authorized']
actual_path=D/'actual-contract.json';manifest_path=D/'input-manifest.json'
actual=json.loads(actual_path.read_text());manifest=json.loads(manifest_path.read_text());recipe_path=P/'build-recipe.json'
assert rec(recipe_path)['sha256']==RECIPE and actual['input_manifest']==rec(manifest_path)
assert actual['controller']==rec(Path(__file__)) and actual['root_admission']==rec(A)
assert actual['compiler_step_indices']==[0,1,2] and actual['threads_scope']=='Three strictly sequential fixed build commands; OMP/BLAS/VECLIB1 environment; observed internal process/thread counts recorded with no invented thread-count refusal.'
assert rec(G)['sha256']==GRANT and actual['driver_compatibility_grant_binding']==rec(G)
grant=json.loads(G.read_text());assert grant['build_invocations_authorized']==3 and not grant['observer_or_shim_recompilation_authorized'] and not grant['automatic_retry']
assert actual['selected_linker']==rec(Path(CLT_LD))
records=manifest['protected_records'];direct={str(p):rec(p) for p in [actual_path,manifest_path,Path(__file__),A]}
assert not set(records)&set(direct);pins={**records,**direct}
initial=check(pins);assert not initial['changed'];source_before=git_state();assert aliases()==actual['compiler_aliases_before']
B=P/'build-005';assert not B.exists() and not (D/'receipt.json').exists();B.mkdir();(B/'tmp').mkdir()
recipe=json.loads(recipe_path.read_text());plan_path=D/'finite-build-argv.json';assert rec(plan_path)['sha256']==PLAN and actual['finite_plan']==rec(plan_path);plan=json.loads(plan_path.read_text());assert [x['name'] for x in plan['ordered_steps']]==['direct_CLT_plugin_link','compile_unchanged_guard_main','direct_CLT_guard_link'];env=actual['environment'];assert env['TMPDIR']==str(B/'tmp')
assert set(env)=={'PATH','SDKROOT','CPLUS_INCLUDE_PATH','LC_ALL','LANG','TMPDIR','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'}
assert all(env[x]=='1' for x in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'])
receipt=dict(schema='962-observer003-once-root-admitted-build-receipt/v1',actual=rec(actual_path),admission=rec(A),controller=rec(Path(__file__)),initial=initial,source_before=source_before,steps=[],completed_three_build_steps=False,guards_executed=False,host_loaded=False,native_executed=False,scientific_or_ABI_acceptance=False,threads_scope=actual['threads_scope'],automatic_retry=False)
failure=None
try:
 for index,step in enumerate(plan['ordered_steps']):
  ordinal=index+1;argv=list(step['argv'])
  depfile=B/f'step{ordinal}.d'
  if index==1:argv+=['-MD','-MF',str(depfile)]
  item=dict(ordinal=ordinal,recipe_index=index,name=step['name'],argv=argv,before=check(pins),samples=0,resource_samples=[],peak_RSS_bytes=0,peak_processes=0,peak_observed_threads=None)
  receipt['steps'].append(item)
  if item['before']['changed']:raise ValueError('Protected input changed before compiler step')
  outp,errp=B/f'step{ordinal}.stdout',B/f'step{ordinal}.stderr';proc=None;started=time.monotonic()
  try:
   with outp.open('xb') as out,errp.open('xb') as err:
    proc=subprocess.Popen(argv,cwd=B,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,preexec_fn=limits);item['pid']=proc.pid
    while proc.poll() is None:
     if time.monotonic()-started>120:raise ValueError('120s per-step wall cap')
     if output_size(B)>CAP:raise ValueError('64MiB owned build/log cap')
     try:s=sample(proc.pid)
     except Exception:
      if proc.poll() is not None:break
      raise
     s['elapsed_seconds']=time.monotonic()-started;item['resource_samples'].append(s);item['samples']+=1;item['peak_RSS_bytes']=max(item['peak_RSS_bytes'],s['RSS_bytes']);item['peak_processes']=max(item['peak_processes'],s['processes']);item['peak_observed_threads']=max(item['peak_observed_threads'] or s['threads'],s['threads']) if s['threads'] is not None else item['peak_observed_threads'];item['last_sample']=s
     if s['RSS_bytes']>2*1024**3:raise ValueError('2GiB sampled owned-group RSS cap')
     time.sleep(.05)
    proc.wait(timeout=8)
   item['returncode']=proc.returncode
   if group_exists(proc.pid):raise ValueError('Owned group remains after normal compiler exit')
   if proc.returncode:raise ValueError('Compiler step failed; no retry or next step')
   if output_size(B)>CAP:raise ValueError('64MiB completion output cap')
   if index==0:
    item['actual_plugin']=rec(B/'libcoupon_end181_observer-opt.dylib')
    spec=recipe['ordered_steps'][3];template=R/spec['template']['path'];assert rec(template)==spec['template']
    (B/'libcoupon_end181_observer-opt.la').write_bytes(template.read_bytes());item['actual_descriptor']=rec(B/'libcoupon_end181_observer-opt.la')
  except Exception:
   if proc is not None:item['termination']=stop_wait(proc)
   raise
  finally:
   item['elapsed_seconds']=time.monotonic()-started;item['stdout']=rec(outp) if outp.exists() else None;item['stderr']=rec(errp) if errp.exists() else None
   item['dependencies']=dependencies(depfile,ordinal,manifest['header_records']);item['after']=check(pins)
  if item['after']['changed']:raise ValueError('Protected input changed after compiler step')
 receipt['completed_three_build_steps']=True
except Exception:failure=traceback.format_exc()
finally:
 receipt['failure']=failure;receipt['final_snapshot']=check(pins);receipt['compiler_aliases_after']=aliases()
 if receipt['compiler_aliases_after']!=actual['compiler_aliases_before']:receipt['completed_three_build_steps']=False
 try:receipt['source_after']=git_state()
 except Exception:receipt['source_after_error']=traceback.format_exc();receipt['completed_three_build_steps']=False
 try:receipt['owned_output_bytes']=output_size(B)
 except Exception:receipt['output_census_error']=traceback.format_exc();receipt['completed_three_build_steps']=False
 receipt['owned_outputs']={str(p.relative_to(B)):rec(p) for p in B.rglob('*') if p.is_file() and not p.is_symlink()}
 if receipt['final_snapshot']['changed']:receipt['completed_three_build_steps']=False
 (D/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
raise SystemExit(0 if receipt['completed_three_build_steps'] and failure is None else 2)
