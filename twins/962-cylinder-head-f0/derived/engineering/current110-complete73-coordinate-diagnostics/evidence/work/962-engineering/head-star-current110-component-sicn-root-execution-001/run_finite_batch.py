from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,time,traceback
R=Path('project-role://engineering-checkout')
E=R/'work/962-engineering';D=E/'head-star-current110-component-sicn-root-execution-001'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(p):
 p=Path(p);return dict(path=str(p.relative_to(R)),sha256=sha(p),bytes=p.stat().st_size)
def save(p,data):
 with p.open('x') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n')
 p.chmod(0o444)
def exists_group(pid):
 try:os.killpg(pid,0);return True
 except ProcessLookupError:return False
def member(pid):
 p=subprocess.run(['/bin/ps','-o','pid=,ppid=,pgid=','-p',str(pid)],capture_output=True,text=True,timeout=2)
 vals=p.stdout.split();return tuple(map(int,vals)) if len(vals)==3 else None
def children(pid):
 p=subprocess.run(['/usr/bin/pgrep','-P',str(pid)],capture_output=True,text=True,timeout=2)
 return [int(x) for x in p.stdout.split()] if p.returncode==0 else []
def rehash(mapping):
 for name,h in mapping.items():
  p=Path(name)
  if p.is_symlink() or not p.is_file() or sha(p)!=h:raise ValueError('Bound input/runtime drift: '+name)
A=D/'root-launch-authorization.json';assert sha(A)=='98ec15d86ea1beed651c4fb1d9342ff123c1161545be1bd44318460ded224042'
auth=json.loads(A.read_text());bp=R/auth['batch']['path'];assert sha(bp)==auth['batch']['sha256'];b=json.loads(bp.read_text())
for k in ('exact_batch_peer','exact_batch_peer_bindings','runtime_admission','source_review','guards_once'):
 pin=auth[k];assert sha(R/pin['path'])==pin['sha256']
assert auth['maximum_invocations']==73 and len(b['cases'])==73
results=[];started=time.monotonic();campaign_error=None;active=None;owned=set();interrupted=False
def signal_request(*args):
 global interrupted
 interrupted=True
old=signal.signal(signal.SIGTERM,signal_request)
try:
 for row in b['cases']:
  if interrupted:raise RuntimeError('Root SIGTERM; no subsequent case authorized')
  actual=R/row['actual']['path'];assert sha(actual)==row['actual']['sha256'];c=json.loads(actual.read_text())
  rehash(c['input_hashes']);rehash(c['runtime_files'])
  out=R/row['output_directory'];assert not out.exists() and not out.is_symlink()
  out.mkdir()
  for src,name,h in [(R/b['source']['path'],'reader.py',b['source']['sha256']),(R/b['controller']['path'],'run_readback.py',b['controller']['sha256']),(actual,'frozen-contract.json',row['actual']['sha256'])]:
   assert sha(src)==h
   with (out/name).open('xb') as f:f.write(src.read_bytes())
   (out/name).chmod(0o444);assert sha(out/name)==h
  case_start=time.monotonic();owned=set();signals=[];outer_stop=None;controller=None
  try:
   with (D/(row['case_key']+'-controller.log')).open('x') as log:
    controller=subprocess.Popen([c['native_python'],'-I','-B',str(out/'run_readback.py'),'--contract-sha256',row['actual']['sha256']],cwd=R,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env={'PATH':'/usr/bin:/bin','LANG':'C','PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','VECLIB_MAXIMUM_THREADS':'2'})
    active=controller
    while controller.poll() is None:
     for pid in children(controller.pid):
      v=member(pid)
      if v and v==(pid,controller.pid,pid):owned.add(pid)
     if interrupted or time.monotonic()-case_start>=40:
      outer_stop='root_SIGTERM' if interrupted else 'outer40s'
      os.killpg(controller.pid,signal.SIGTERM);signals.append(dict(group=controller.pid,signal='SIGTERM'))
      try:controller.wait(timeout=8)
      except subprocess.TimeoutExpired:
       for pid in list(owned):
        if exists_group(pid):
         os.killpg(pid,signal.SIGKILL);signals.append(dict(group=pid,signal='SIGKILL'))
       if exists_group(controller.pid):
        os.killpg(controller.pid,signal.SIGKILL);signals.append(dict(group=controller.pid,signal='SIGKILL'))
       controller.wait()
      break
     time.sleep(.1)
    controller.wait()
  finally:
   if controller is not None and controller.poll() is None:
    os.killpg(controller.pid,signal.SIGTERM);signals.append(dict(group=controller.pid,signal='SIGTERM_cleanup'))
    try:controller.wait(timeout=8)
    except subprocess.TimeoutExpired:
     for pid in owned:
      if exists_group(pid):os.killpg(pid,signal.SIGKILL);signals.append(dict(group=pid,signal='SIGKILL_cleanup'))
     if exists_group(controller.pid):os.killpg(controller.pid,signal.SIGKILL)
     controller.wait()
   lingering=[pid for pid in owned if exists_group(pid)]
   for pid in lingering:
    os.killpg(pid,signal.SIGKILL);signals.append(dict(group=pid,signal='SIGKILL_lingering'))
   active=None
  elapsed=time.monotonic()-case_start
  receipt=json.loads((out/'execution-receipt.json').read_text()) if (out/'execution-receipt.json').is_file() else None
  report=json.loads((out/'fixture-report.json').read_text()) if (out/'fixture-report.json').is_file() else None
  diag=json.loads((out/'diagnostic.json').read_text()) if (out/'diagnostic.json').is_file() else None
  rehash(c['input_hashes']);rehash(c['runtime_files'])
  group_absent=not exists_group(controller.pid) and all(not exists_group(pid) for pid in owned)
  record=dict(schema='962-current110-component-root-once-closed/v1',component_ID=row['component_ID'],case_key=row['case_key'],root_launch=identity(A),actual=identity(actual),materialized_contract=identity(out/'frozen-contract.json'),controller_PID=controller.pid,owned_worker_group_IDs=sorted(owned),waited_returncode=controller.returncode,wall_seconds=elapsed,outer_stop=outer_stop,signals=signals,lingering_owned_groups_before_cleanup=lingering,owned_groups_absent=group_absent,all_bound_inputs_and_selected_runtime_unchanged=True,controller_scope_labels_are_inherited_historical_declarations=True,report_status=report.get('status') if report else None,report_stage=report.get('stage') if report else None,report_error=report.get('error') if report else None,minimize_calls_attempted=report.get('minimize_calls_attempted') if report else None,controller_stop_reason=receipt.get('stop_reason') if receipt else None,all_component_exact_quality_gate=diag.get('all_component_exact_quality_gate') if diag else None,procedural_checks_passed=diag.get('procedural_checks_passed') if diag else None,solver=diag.get('solver') if diag else None,full_cells=diag.get('full_cells') if diag else None,positive_poor_cell_count=len(diag['positive_poor_cell_tags']) if diag else None,nonpositive_or_undefined_cell_count=len(diag['nonpositive_or_undefined_cell_tags']) if diag else None,outputs=[identity(p) for p in sorted(out.iterdir()) if p.is_file()],native_mesh_application=False,engineering_accepted=False,manufacturing_authorized=False)
  save(D/(row['case_key']+'-root-once-closed.json'),record);results.append(record)
  print(json.dumps(dict(completed=len(results),case=row['case_key'],returncode=controller.returncode,status=record['report_status'],quality=record['all_component_exact_quality_gate'],seconds=round(elapsed,3))),flush=True)
  if outer_stop or lingering or not group_absent or not receipt or receipt.get('stop_reason') or not report or report.get('error') or record['minimize_calls_attempted']!=1:
   raise RuntimeError('Stop finite campaign on resource/procedural/lifecycle failure; preserve all outputs')
except BaseException as error:
 campaign_error=dict(type=type(error).__name__,error=str(error),traceback=traceback.format_exc())
finally:
 signal.signal(signal.SIGTERM,old)
 summary=dict(schema='962-current110-fixed73-root-batch-once-closed/v1',root_launch=identity(A),batch=identity(bp),completed_controller_invocations=len(results),maximum73=True,wall_seconds=time.monotonic()-started,error=campaign_error,all_cases_closed= len(results)==73 and campaign_error is None,summary_counts={s:sum(r['report_status']==s for r in results) for s in sorted({str(r['report_status']) for r in results})},exact_quality_pass_components=sum(r['all_component_exact_quality_gate'] is True for r in results),procedural_pass_components=sum(r['procedural_checks_passed'] is True for r in results),total_minimize_calls_recorded=sum(r['minimize_calls_attempted'] or 0 for r in results),case_records=[identity(D/(r['case_key']+'-root-once-closed.json')) for r in results],native_mesh_application=False,engineering_accepted=False,manufacturing_authorized=False)
 save(D/'batch-once-closed.json',summary);print(json.dumps({k:v for k,v in summary.items() if k not in ('case_records','root_launch','batch')}),flush=True)
 if campaign_error:raise SystemExit(2)
