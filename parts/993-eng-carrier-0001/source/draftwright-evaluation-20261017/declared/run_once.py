"""Run the one separately authorized authored drawing attempt within 480 seconds."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,time
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]
ENV=ROOT/'work/carrier-draftwright-20261017/drawing-env'
SOURCE=ROOT/'work/carrier-draftwright-20261017/source'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
step=ROOT/'parts/993-eng-carrier-0001/derived/workflow-20261016/carrier.step'
proof=ROOT/'work/carrier-draftwright-20261017/nominal-model-inspection.json'
files=[step,proof,BASE/'draw_f0.py',BASE/'run_once.py',ROOT/'work/carrier-draftwright-20261017/requirements-frozen.txt']
for name in ['sheet.py','sheet_views.py','drawing.py','drawing_diagnostics.py','model/declare.py','model/ir_foundation.py']:
 a=SOURCE/'src/draftwright'/name;b=ENV/'lib/python3.13/site-packages/draftwright'/name
 assert a.read_bytes()==b.read_bytes();files.extend((a,b))
before={str(p):sha(p) for p in files}
assert sha(step)=='de0e55a3150dacc5428bbc301d18d2e43477f038c3f4df295d9373af8e906b63'
command=[str(ENV/'bin/python'),'-B',str(BASE/'draw_f0.py')]
plan=dict(schema='carrier-draftwright-authored-attempt-plan-1',command=command,timeout_seconds=480,nice=10,
 threads=1,input_sha256=before,automatic_trial='Preserved separately at work/carrier-draftwright-20261017; not relabelled or rerun.',
 declared_scope='Eight established nominal F0 dimensions; no default tolerance/PMI/finish/GDT; no physical-recognition lint.',
 software_adoption=False)
(BASE/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
started=time.perf_counter();timeout=False
with (BASE/'stdout.log').open('w') as out,(BASE/'stderr.log').open('w') as err:
 p=subprocess.Popen(command,cwd='/',stdout=out,stderr=err,start_new_session=True,preexec_fn=lambda:os.nice(10),
  env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'})
 try:rc=p.wait(timeout=480)
 except subprocess.TimeoutExpired:
  timeout=True;os.killpg(p.pid,signal.SIGTERM)
  try:rc=p.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait(timeout=10)
report=dict(schema='carrier-draftwright-authored-attempt-execution-1',returncode=rc,timeout_triggered=timeout,seconds=time.perf_counter()-started,
 pid=p.pid,process_closed=p.poll() is not None,input_sha256=before,inputs_unchanged=all(sha(Path(k))==h for k,h in before.items()),
 outputs_sha256={x.relative_to(BASE).as_posix():sha(x) for x in BASE.rglob('*') if x.is_file() and x.name not in ['execution-receipt.json']},
 scope='One explicit Sheet construction only; not an automatic recognition retry.',adoption=False)
(BASE/'execution-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k]for k in ['returncode','timeout_triggered','seconds','inputs_unchanged']},indent=2),flush=True)
