"""One bounded public Draftwright CLI call in a fresh drawing-only environment."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,time
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
STEP=ROOT/'parts/993-eng-carrier-0001/derived/workflow-20261016/carrier.step'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((BASE/'plan.json').read_text());assert sha(STEP)==plan['step']['sha256']
python=BASE/'drawing-env/bin/python'
check=subprocess.run([str(python),'-m','pip','--isolated','check'],capture_output=True,text=True,timeout=30)
(BASE/'pip-check.txt').write_text(check.stdout+check.stderr);assert check.returncode==0
freeze=subprocess.run([str(python),'-m','pip','--isolated','freeze','--all'],capture_output=True,text=True,check=True,timeout=30)
(BASE/'requirements-frozen.txt').write_text(freeze.stdout)
version=subprocess.run([str(BASE/'drawing-env/bin/draftwright'),'--version'],capture_output=True,text=True,check=True,timeout=30)
(BASE/'version.txt').write_text(version.stdout+version.stderr)
output=BASE/'drawing-001';assert not output.exists()
command=[str(BASE/'drawing-env/bin/draftwright'),str(STEP),'--out-dir',str(output),'--format','all',
 '--title','Support moteur 993 — cotes nominales CAO','--number','993-ENG-CARRIER-0001-ETUDE',
 '--tolerance','','--pmi','off','--material','','--revision','','--document-type','Étude nominale CAO',
 '--projection','first','--page','A3','--annotation-layout','demand-guided','--no-progress']
before={str(STEP):sha(STEP),**{str(BASE/'source'/p):h for p,h in plan['source']['files_sha256'].items()}}
started=time.perf_counter();interrupted=False
with (BASE/'stdout.log').open('w') as stdout,(BASE/'stderr.log').open('w') as stderr:
 process=subprocess.Popen(command,cwd='/',stdout=stdout,stderr=stderr,start_new_session=True,
  preexec_fn=lambda:os.nice(10),env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'})
 try:returncode=process.wait(timeout=480)
 except subprocess.TimeoutExpired:
  interrupted=True;os.killpg(process.pid,signal.SIGTERM)
  try:returncode=process.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);returncode=process.wait(timeout=10)
receipt=dict(schema='carrier-draftwright-cli-execution-1',command=command,working_directory='/',pid=process.pid,
 returncode=returncode,timeout_seconds=480,timeout_triggered=interrupted,process_group_closed=process.poll() is not None,
 nice=10,threads=dict(OMP_NUM_THREADS=1,OPENBLAS_NUM_THREADS=1,MKL_NUM_THREADS=1),seconds=time.perf_counter()-started,
 input_sha256=before,inputs_unchanged=all(sha(Path(p))==h for p,h in before.items()),
 output_files_sha256={p.relative_to(output).as_posix():sha(p) for p in output.rglob('*') if p.is_file()} if output.exists() else {},
 log_sha256={p:sha(BASE/p) for p in ['stdout.log','stderr.log','requirements-frozen.txt','version.txt','pip-check.txt']},
 manufacturing_or_drawing_admission=False)
(BASE/'execution-receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(returncode=returncode,timeout_triggered=interrupted,seconds=receipt['seconds'],outputs=list(receipt['output_files_sha256']),inputs_unchanged=receipt['inputs_unchanged']),indent=2),flush=True)
