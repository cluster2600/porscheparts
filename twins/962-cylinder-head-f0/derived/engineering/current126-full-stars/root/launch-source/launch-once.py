"""One root-authorized current126 read-only census; no retry or mesh edit."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,signal,subprocess,sys,time

ROOT=Path('project-role://engineering-checkout')
BASE=ROOT/'work/962-engineering'
PREP=BASE/'head-star-current126-full-stars-execution-prep-001'
PEER=BASE/'head-star-current126-full-stars-exact-child-peer-001'
CONTROL=BASE/'head-star-current126-full-stars-root-execution-001'
OUTER='runtime-role://controller/python'
OUTER_SHA='1699bf8aa705a8bb71613bef5cdd7d7c8c9d9a188a841f41679aa9b5830b8f60'
ACTUAL_SHA='d579a794f18bc9f7c4e153cb2042f32cb32b2c6b2f2235cec2edbef8aba91317'
INDEX_SHA='768aad54cfc1f2c620e8da4e3a5a9e69f73c45f85e18058dd4147d2f53805856'
PINS={
 'actual':('head-star-current126-full-stars-execution-prep-001/actual-contract.json',ACTUAL_SHA),
 'index':('head-star-current126-full-stars-execution-prep-001/index.json',INDEX_SHA),
 'child':('head-star-current126-full-stars-exact-child-peer-001/review.json','4fd56aa0073054a0d2010247cc8f020c4254f37dd14241ae78dad46b6e44321d'),
 'child_bindings':('head-star-current126-full-stars-exact-child-peer-001/bindings.json','826b3d135f42c08b319baec082aa83246dda0fddad06a36c2b0917b94d3a9599'),
 'root_guards':('head-star-current126-full-stars-root-source-001/review.json','6eecaf29b2fa8002afac6958aad76479e23745ea4b1857023058810b9d540b80'),
 'finite_runtime':('head-star-current126-full-stars-runtime-root-001/review.json','28101a316a5070a9d33092f5afc08dd84a347f6b8e2b51bed88a4c00ab951e7c'),
 'parent_acceptance':('apex1613031-head-application-root-execution-001/result-peer-acceptance.json','19ef174a208868bf174909a1add690971fdf018b8cf438c5c26e3a2bca9bfada'),
}
ENV={'PATH':'/usr/bin:/bin','LANG':'C','PYTHONUTF8':'1','OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','PYTHONDONTWRITEBYTECODE':'1'}
FALSE_KEYS=('optimization_authorized','generation_authorized','geometry_export_authorized','mesh_write_authorized','head_edit_authorized','head_execution_authorized','head_PDE_authorized','PDE_solve_authorized','manufacturing_authorized','engineering_accepted','physics_qualified','material_qualified','process_calibrated','automatic_retry','stitching_authorized','renumbering_authorized')

def record(path,allow_runtime_symlink=False):
 p=Path(path)
 if not p.is_absolute():p=ROOT/p
 assert p.is_file(),str(p)
 if not allow_runtime_symlink:
  assert p.is_relative_to(ROOT) and p==p.resolve(),str(p)
  assert not any(q.is_symlink() for q in (p,*p.parents) if q.is_relative_to(ROOT)),str(p)
 before=p.stat();h=hashlib.sha256()
 with p.open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 after=p.stat()
 assert (before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns),str(p)
 return dict(path=str(p),sha256=h.hexdigest(),bytes=after.st_size)

def freeze(name,value):
 p=CONTROL/name
 with p.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
 p.chmod(0o444)
 return record(p)

def group_exists(pid):
 try:os.killpg(pid,0);return True
 except ProcessLookupError:return False

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--authorization-sha256',required=True)
 args=parser.parse_args()
 assert re.fullmatch('[0-9a-f]{64}',args.authorization_sha256)
 os.chdir(ROOT)
 assert sys.flags.isolated and sys.dont_write_bytecode
 assert record(Path(sys.executable).resolve(),True)['sha256']==OUTER_SHA
 assert CONTROL.is_dir() and CONTROL==CONTROL.resolve() and not CONTROL.is_symlink()
 assert sorted(p.name for p in CONTROL.iterdir())==['authorization.json']
 authorization=record(CONTROL/'authorization.json');assert authorization['sha256']==args.authorization_sha256
 auth=json.loads((CONTROL/'authorization.json').read_text())
 assert auth['schema']=='962-current126-census-root-launch-authorization/v1'
 assert auth['decision']=='ROOT_AUTHORIZES_EXACTLY_ONE_CURRENT126_READ_ONLY_CENSUS'
 launch_source=record(__file__)
 assert auth['launch_source']==launch_source
 assert auth['native_serialization_and_resources_reviewed'] is True
 assert auth['read_only_query_authorized'] is True
 assert all(auth[k] is False for k in ('automatic_retry','head_edit_authorized','PDE_solve_authorized','physical_qualification'))
 static={}
 for label,(rel,expected) in PINS.items():
  row=record(BASE/rel);assert row['sha256']==expected
  assert auth[label]==row
  static[label]=row
 static['authorization']=authorization;static['launch_source']=launch_source
 c=json.loads((PREP/'actual-contract.json').read_text());idx=json.loads((PREP/'index.json').read_text())
 child=json.loads((PEER/'review.json').read_text());bindings=json.loads((PEER/'bindings.json').read_text())
 assert child['decision']=='CLEAR_EXACT_CHILD_BINDINGS_ONLY_CONDITIONAL_READ_ONLY_CENSUS' and child['blockers']==[]
 assert bindings['all108_input_hashes']==c['input_hashes']
 assert len(c['input_hashes'])==108 and len(idx['current_small_inputs_before'])==104
 assert len(idx['deferred_raw_geometry_inputs'])==len(idx['absent_future_source_copies'])==2
 assert len(idx['caller_inventory']['effective_consumed_contract_keys'])==32
 assert set(idx['caller_inventory']['effective_consumed_contract_keys'])<=set(c)
 assert len(idx['caller_inventory']['dynamic_proof_keys'])==4
 assert all(c[k] is False for k in FALSE_KEYS) and all(v is False for v in c['qualification'].values())
 assert all(c[k] is True for k in ('native_execution_authorized','native_launch_authorized','read_only_saved_mesh_query_authorized','execution_requires_external_child_and_fresh_root_authorization'))
 assert c['exact_child_review_complete_at_freeze'] is c['fresh_root_launch_checks_complete_at_freeze'] is False
 assert c['declared_controller_command_conformant'] is False and c['upstream_census_launch_deviation_sha256']=='d60fff297c6c45dc92e117262e36ffde36e2169d53fcd32ce2b79fabde5eebc3'
 assert c['expected_positive_poor_total']==126 and c['single_partial_replacement_saved_proof']['positive_poor']==126
 assert 'single_partial_after_saved_proof' not in c
 assert all(v is None for v in c['observations_pending'].values()) and c['native_result'] is c['actual_child_sha256'] is None
 held=json.loads((ROOT/idx['held']['path']).read_text())
 assert len(held['input_hashes'])==98 and all(c['input_hashes'][p]==h for p,h in held['input_hashes'].items())
 assert all(c[k]==held[k] for k in idx['caller_inventory']['effective_consumed_contract_keys'] if k!='input_hashes')
 guard=json.loads((BASE/PINS['root_guards'][0]).read_text())
 assert guard['guard_execution']==dict(completed=True,methods=6,passed=True) and guard['returncode']==0
 assert guard['error'] is None and guard['signals']==[] and guard['all_inputs_unchanged'] is True
 parent=json.loads((BASE/PINS['parent_acceptance'][0]).read_text())
 assert parent['procedural_partial_repair_accepted'] is True and parent['whole_head_quality_accepted'] is False
 assert parent['mesh']['sha256']==c['MSH_sha256'] and parent['observed']['positive_poor_after']==126
 out=ROOT/c['output_directory']
 assert out==out.resolve() and not out.exists() and not out.is_symlink()
 assert idx['outer_controller_command']==[OUTER,'-I','-B',str(out/'run_readback.py'),'--contract-sha256',ACTUAL_SHA]
 assert idx['native_worker_command']==[c['native_python'],'-B',str(out/'reader.py')]
 assert idx['outer_controller_environment']==idx['native_worker_environment']==c['outer_controller_environment']==c['native_worker_environment']==ENV
 assert c['controls']==idx['inner_controller_controls']==dict(complete_or_refuse_no_sampling_or_truncation=True,hard_OS_CPU_or_address_space_quota=False,hard_wall_seconds=120,sampled_RSS_stop_bytes=8589934592,sampled_output_stop_bytes=1073741824,threads=2)
 assert c['root_outer_controls']==idx['root_outer_controls']
 assert c['root_outer_controls']['ordinary_wall_seconds']==135 and c['root_outer_controls']['TERM_grace_seconds']==8
 assert all(c['root_outer_controls'][k] is True for k in ('start_new_session','TERM_at_deadline','SIGKILL_only_verified_owned_group_if_needed','wait_and_reap_required'))
 assert c['root_outer_controls']['automatic_retry'] is False
 before={}
 for rel,expected in idx['current_small_inputs_before'].items():
  row=record(rel);assert (row['sha256'],row['bytes'])==(expected['sha256'],expected['bytes'])
  assert c['input_hashes'][rel]==idx['current_small_input_hashes_after'][rel]==row['sha256'];before[rel]=row
 for rel,expected in idx['deferred_raw_geometry_inputs'].items():
  row=record(rel);assert (row['sha256'],row['bytes'])==(expected['sha256'],expected['bytes'])
  assert c['input_hashes'][rel]==row['sha256'];before[rel]=row
 assert len(before)==106
 runtime={}
 finite=json.loads((BASE/PINS['finite_runtime'][0]).read_text())
 expected_runtime=dict(c['external_runtime_hashes']);expected_runtime[OUTER]=OUTER_SHA
 assert len(expected_runtime)==5 and expected_runtime[c['numpy_init']]==c['numpy_init_sha256']
 for path,expected in expected_runtime.items():
  row=record(path,True);row['resolved']=str(Path(path).resolve())
  assert row['sha256']==expected and row['resolved']==finite['runtime5'][path]['resolved'];runtime[path]=row
 disk=shutil.disk_usage(ROOT);assert disk.free>1024**3
 for rel,expected in idx['absent_future_source_copies'].items():
  path=ROOT/rel;assert path.parent==out and not path.exists() and not path.is_symlink()
  row=record(expected['source']);assert (row['sha256'],row['bytes'])==(expected['sha256'],expected['bytes'])
 assert len(idx['future_materialization'])==3
 assert idx['future_materialization'][2]==dict(path=str((out/'frozen-contract.json').relative_to(ROOT)),sha256=ACTUAL_SHA,bytes=36806,role='whole_actual_mirror_digest_external_not_self_pinned')
 assert str((out/'frozen-contract.json').relative_to(ROOT)) not in c['input_hashes']
 preflight=freeze('preflight.json',dict(schema='962-current126-census-root-preflight/v1',authorization=authorization,static9_before=static,inputs106_before=before,runtime5_before=runtime,outer_command=idx['outer_controller_command'],worker_command=idx['native_worker_command'],environment=ENV,inner_controls=c['controls'],outer_controls=c['root_outer_controls'],free_disk_bytes=disk.free,upstream_d60_command_conformant=False,native_query_runs_before_this_launch=0,automatic_retry=False,head_edit_authorized=False,physical_qualification=False))
 out.mkdir()
 for rel,expected in idx['absent_future_source_copies'].items():
  path=ROOT/rel
  with path.open('xb') as stream:stream.write((ROOT/expected['source']).read_bytes())
  path.chmod(0o444)
 with (out/'frozen-contract.json').open('xb') as stream:stream.write((PREP/'actual-contract.json').read_bytes())
 (out/'frozen-contract.json').chmod(0o444)
 assert sorted(p.name for p in out.iterdir())==['frozen-contract.json','reader.py','run_readback.py']
 assert record(out/'frozen-contract.json')['sha256']==ACTUAL_SHA
 for rel,expected in c['input_hashes'].items():
  row=record(rel);assert row['sha256']==expected;before[rel]=row
 assert len(before)==108
 materialized=freeze('materialization.json',dict(preflight=preflight,all108_inputs_before=before,initial3_files={p.name:record(p) for p in sorted(out.iterdir())},whole_actual_mirror_sha256=ACTUAL_SHA))
 stdout=CONTROL/'controller.stdout.log';stderr=CONTROL/'controller.stderr.log'
 proc=None;signals=[];fallback=False;error=None;started=time.monotonic()
 def send_owned(sig,label):
  if proc.poll() is not None:return
  try:
   assert os.getpgid(proc.pid)==proc.pid,'Controller owned process group identity changed'
   os.killpg(proc.pid,sig);signals.append(label)
  except ProcessLookupError:pass
 try:
  with stdout.open('xb') as so,stderr.open('xb') as se:
   proc=subprocess.Popen(idx['outer_controller_command'],cwd=ROOT,stdout=so,stderr=se,start_new_session=True,env=ENV)
   freeze('launch.json',dict(argv=idx['outer_controller_command'],environment=ENV,owned_controller_PID=proc.pid,owned_controller_PGID=proc.pid,PGID_basis='Popen start_new_session; verified again before any group signal',start_new_session=True,materialization=materialized,ordinary_deadline_seconds=135,native_worker_PID_observed=False,automatic_retry=False))
   try:proc.wait(timeout=max(0.,135-(time.monotonic()-started)))
   except subprocess.TimeoutExpired:
    fallback=True;send_owned(signal.SIGTERM,'SIGTERM')
    try:proc.wait(timeout=8)
    except subprocess.TimeoutExpired:send_owned(signal.SIGKILL,'SIGKILL');proc.wait()
 except BaseException as exc:error=repr(exc)
 finally:
  if proc is not None:
   if proc.poll() is None:fallback=True;send_owned(signal.SIGKILL,'SIGKILL-finally')
   proc.wait()
 elapsed=time.monotonic()-started
 after={};runtime_after={};static_after={};after_errors=[]
 for rel in before:
  try:after[rel]=record(rel)
  except BaseException as exc:after_errors.append(dict(kind='input',path=rel,error=repr(exc)))
 for path in runtime:
  try:runtime_after[path]=dict(record(path,True),resolved=str(Path(path).resolve()))
  except BaseException as exc:after_errors.append(dict(kind='runtime',path=path,error=repr(exc)))
 for label,row in static.items():
  try:static_after[label]=record(row['path'])
  except BaseException as exc:after_errors.append(dict(kind='static',path=row['path'],error=repr(exc)))
 outputs={};receipt=None;receipt_error=None
 for path in sorted(out.iterdir()):
  try:outputs[path.name]=record(path)
  except BaseException as exc:after_errors.append(dict(kind='output',path=str(path),error=repr(exc)))
 if (out/'execution-receipt.json').is_file():
  try:receipt=json.loads((out/'execution-receipt.json').read_text())
  except BaseException as exc:receipt_error=repr(exc)
 valid_receipt=(isinstance(receipt,dict) and receipt.get('reader_sha256')==c['reader_sha256'] and receipt.get('runner_sha256')==c['runner_sha256'] and receipt.get('contract_sha256')==ACTUAL_SHA and receipt.get('native_generate_optimize_meshwrite_solve_calls')==0 and receipt.get('returncode')==0 and receipt.get('stop_reason') is None and receipt.get('readback_report_sha256')==outputs.get('readback-report.json',{}).get('sha256'))
 complete6=set(outputs)=={'reader.py','run_readback.py','frozen-contract.json','native.log','execution-receipt.json','readback-report.json'}
 clean=(proc is not None and proc.returncode==0 and not fallback and error is None and not after_errors and before==after and runtime==runtime_after and static==static_after and valid_receipt and complete6)
 closed=freeze('closed-result.json',dict(schema='962-current126-head-census-root-closed/v1',authorization=authorization,preflight=preflight,materialization=materialized,actual=static['actual'],index=static['index'],child=static['child'],child_bindings=static['child_bindings'],launch_source=static['launch_source'],argv=idx['outer_controller_command'],worker_command_from_exact4fb=idx['native_worker_command'],environment=ENV,root_controller_PID=proc.pid if proc else None,root_controller_PGID=proc.pid if proc else None,returncode=proc.returncode if proc else None,wall_seconds=elapsed,signals=signals,outer_fallback_used=fallback,error=error,after_observation_errors=after_errors,controller_waited_reaped=proc is not None and proc.poll() is not None,controller_owned_group_observed_absent=proc is not None and not group_exists(proc.pid),native_worker_PID_observed=False,native_cleanup_scope='Attributed to exact4fb finally/wait and saved controller receipt; root observes its controller only, not universal descendant absence.',inputs108_before=before,inputs108_after=after,all108_inputs_unchanged=before==after,runtime5_before=runtime,runtime5_after=runtime_after,runtime5_unchanged=runtime==runtime_after,static9_before=static,static9_after=static_after,static9_unchanged=static==static_after,output_files=outputs,complete6_output_names=complete6,whole_actual_mirror_sha256=outputs.get('frozen-contract.json',{}).get('sha256'),controller_stdout=record(stdout),controller_stderr=record(stderr),inner_receipt=receipt,inner_receipt_parse_error=receipt_error,valid_closed_controller_receipt=bool(valid_receipt),fresh_saved_association_review_still_required=True,halt_before_any_further_native_if_fallback_or_invalid_receipt=fallback or not valid_receipt,ordinary_sampled_controls_not_OS_quota=True,true_peak_or_complete_ABI_claim=False,upstream_d60_command_conformant=False,expected_positive_poor_baseline=126,native_query_runs=1 if proc else 0,completed_capture_only=bool(clean),whole_head_quality_accepted=False,engineering_accepted=False,physics_qualified=False,material_qualified=False,process_calibrated=False,manufacturing_authorized=False,automatic_retry=False))
 for path in out.iterdir():
  if path.is_file() and not path.is_symlink():path.chmod(0o444)
 stdout.chmod(0o444);stderr.chmod(0o444)
 print(json.dumps(dict(closed=closed,returncode=proc.returncode if proc else None,wall_seconds=elapsed,completed_capture_only=bool(clean),automatic_retry=False),indent=2))
 return 0 if clean else 2

if __name__=='__main__':raise SystemExit(main())
