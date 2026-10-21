from pathlib import Path
import hashlib,json,os,signal,subprocess,time
ROOT=Path('project-role://engineering-checkout');H=ROOT/'work/962-engineering/apex1613031-head-application-review-delivery-001'
PY=Path('runtime-role://controller/python')
def rec(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
assert rec(PY)['sha256']=='1699bf8aa705a8bb71613bef5cdd7d7c8c9d9a188a841f41679aa9b5830b8f60'
source=H/'prepare_download.py';auth=H/'authorization.json'
assert rec(source)['sha256']=='cb808730a0e5cfcf4c3d2658d3ecb57baa6bd6752c3b32b91fc12d48ce5762b2'
assert rec(auth)['sha256']=='ebb005b51bf86b1e8fe2e62784117f13d9a7b03d60cdea2469b97d95aef5b864'
before={str(p):rec(p) for p in [PY,source,auth,ROOT/'work/962-engineering/apex1613031-head-application-root-execution-001/result-peer-acceptance.json']}
for name in ('stdout.log','stderr.log','root-execution.json','head-volume.msh.gz','receipt.json'):assert not (H/name).exists()
argv=[str(PY),'-I','-B',str(source)];started=time.monotonic();signals=[];proc=None;error=None
try:
 with (H/'stdout.log').open('xb') as so,(H/'stderr.log').open('xb') as se:
  proc=subprocess.Popen(argv,cwd=ROOT,stdout=so,stderr=se,env={'PATH':'/usr/bin:/bin','LANG':'C','PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'},start_new_session=True)
  assert os.getpgid(proc.pid)==proc.pid
  try:proc.wait(timeout=max(0,90-(time.monotonic()-started)))
  except subprocess.TimeoutExpired:
   if proc.poll() is None and os.getpgid(proc.pid)==proc.pid:os.killpg(proc.pid,signal.SIGKILL);signals.append('SIGKILL-timeout')
   proc.wait()
except BaseException as exc:error=repr(exc)
finally:
 if proc is not None and proc.poll() is None:
  if os.getpgid(proc.pid)==proc.pid:os.killpg(proc.pid,signal.SIGKILL);signals.append('SIGKILL-finally')
  proc.wait()
elapsed=time.monotonic()-started
try:os.killpg(proc.pid,0);absent=False
except ProcessLookupError:absent=True
after={p:rec(Path(p)) for p in before};assert before==after
outputs={p.name:rec(p) for p in H.iterdir() if p.is_file() and p.name in ('head-volume.msh.gz','receipt.json','stdout.log','stderr.log')}
result=dict(schema='962-apex1613031-byte-delivery-root-execution/v1',argv=argv,pid=proc.pid,pgid=proc.pid,start_new_session=True,returncode=proc.returncode,wall_seconds=elapsed,wall_limit_seconds=90,signals=signals,error=error,waited_reaped=True,owned_group_absent=absent,small_controls_before=before,small_controls_after=after,small_controls_unchanged=True,outputs=outputs,no_native_or_mesh_decode=True,automatic_retry=False,whole_head_admitted=False,manufacturing_authorized=False)
p=H/'root-execution.json'
with p.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);print(file=f)
for p in H.iterdir():
 if p.is_file():p.chmod(0o444)
print(json.dumps(dict(root=rec(H/'root-execution.json'),returncode=proc.returncode,wall_seconds=elapsed,signals=signals,error=error,owned_group_absent=absent,outputs=outputs),indent=2))
raise SystemExit(0 if proc.returncode==0 and not signals and error is None and absent else 2)
