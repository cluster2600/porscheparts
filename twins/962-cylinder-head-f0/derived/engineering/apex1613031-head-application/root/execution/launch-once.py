"""Root-owned single bounded diagnostic replacement; no engineering acceptance."""
from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,time

ROOT=Path('project-role://engineering-checkout')
BASE=ROOT/'work/962-engineering'
HERE=Path(__file__).resolve().parent
PREP=BASE/'apex1613031-head-application-execution-prep-001'
PEER=BASE/'apex1613031-head-application-exact-child-peer-001'
ACTUAL_SHA='98c281e8e8633c7253a7e13e5a5979f1c31ab967ef1af798b0a0415fa07b26fb'
INDEX_SHA='7f73601402e90d3182783c42cc34ac99c21b42dabf42167750373ca80679f01b'
OUTER='runtime-role://controller/python'
OUTER_SHA='1699bf8aa705a8bb71613bef5cdd7d7c8c9d9a188a841f41679aa9b5830b8f60'

def record(path,allow_symlink=False):
 p=Path(path)
 if not p.is_absolute():p=ROOT/p
 assert p.is_file() and (allow_symlink or not p.is_symlink()),str(p)
 b=p.read_bytes()
 return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))

def freeze(name,data):
 p=HERE/name
 with p.open('x') as f:
  json.dump(data,f,indent=2,allow_nan=False)
  print(file=f)
 p.chmod(0o444)
 return record(p)

def group_exists(pid):
 try:os.killpg(pid,0);return True
 except ProcessLookupError:return False

def main():
 os.chdir(ROOT)
 for n in ('preflight.json','materialization.json','launch.json','closed-result.json','controller.stdout.log','controller.stderr.log'):
  assert not (HERE/n).exists() and not (HERE/n).is_symlink(),n
 static={}
 for p,sha in [(PREP/'actual-contract.json',ACTUAL_SHA),(PREP/'index.json',INDEX_SHA),(PEER/'review.json','ed5a82e9d171172b4132d6424bf5c2d66d0477c828b7f30f1c202bef63ab90cd'),(PEER/'bindings.json','b7197e956cb77b9fe835ef1fa1fb6649a8516cee20edff4924e4a86063c954bc')]:
  r=record(p);assert r['sha256']==sha;static[str(p)]=r
 c=json.loads((PREP/'actual-contract.json').read_text());idx=json.loads((PREP/'index.json').read_text())
 peer=json.loads((PEER/'review.json').read_text());bindings=json.loads((PEER/'bindings.json').read_text())
 assert peer['decision']=='CLEAR_EXACT_CHILD_BINDINGS_ONLY_PENDING_ROOT_FRESH_LAUNCH' and peer['blockers']==[]
 assert len(c['input_hashes'])==79 and len(idx['small_inputs_before'])==76
 assert idx['small_inputs_before']==idx['small_inputs_after']
 assert len(idx['complete_consumed_contract_keys'])==33
 assert idx['consumed_contract_values']=={k:c[k] for k in idx['complete_consumed_contract_keys']}
 assert all(c[k] is False for k in idx['ten_required_false_flag_comprehension'])
 assert c['automatic_retry'] is False and c['head_execution_authorized'] is False
 assert c['declared_controller_command_conformant'] is False
 assert all(c[k] is True for k in ('native_execution_authorized','partial_head_replacement_authorized','root_and_peer_review_complete','selected_runtime_review_complete'))
 assert c['guard_execution']['completed'] is True and c['guard_execution']['groups']==11 and c['guard_execution']['passed'] is True
 assert all(v is None for v in c['observed_after'].values())
 held=json.loads((ROOT/idx['held']['path']).read_text())
 assert len(held['input_hashes'])==66 and all(c['input_hashes'][k]==v for k,v in held['input_hashes'].items())
 assert len(bindings['current_small_records'])==78
 for rel,expected in bindings['current_small_records'].items():
  r=record(rel);assert (r['sha256'],r['bytes'])==(expected['sha256'],expected['bytes'])
 for rel,expected in idx['small_inputs_before'].items():
  assert bindings['current_small_records'][rel]['sha256']==expected['sha256']
 out=ROOT/c['output_directory']
 assert out==out.resolve() and not out.exists() and not out.is_symlink()
 assert idx['exact_controller_argv']==[OUTER,'-I','-B',str(out/'run_readback.py'),'--contract-sha256',ACTUAL_SHA]
 assert idx['exact_worker_argv']==[c['native_python'],'-B',str(out/'reader.py')]
 env={'PATH':'/usr/bin:/bin','LANG':'C','PYTHONUTF8':'1','OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','PYTHONDONTWRITEBYTECODE':'1'}
 assert idx['exact_controller_environment']==env and idx['exact_worker_environment']==env
 assert idx['outer_controls']['ordinary_wall_seconds']==1215 and idx['outer_controls']['TERM_grace_seconds']==8
 assert idx['inner_controls']==c['controls']==dict(automatic_retry=False,hard_wall_seconds=1200,native_threads=2,sampled_RSS_stop_bytes=8589934592,sampled_output_stop_bytes=1073741824)
 before={}
 for rel,expected in idx['small_inputs_before'].items():
  r=record(rel);assert (r['sha256'],r['bytes'])==(expected['sha256'],expected['bytes']);assert c['input_hashes'][rel]==r['sha256'];before[rel]=r
 msh=record(c['MSH']);assert (msh['sha256'],msh['bytes'])==(c['MSH_sha256'],c['MSH_bytes'])
 before[c['MSH']]=msh
 runtimes={}
 runtime_expected=dict(c['external_runtime_hashes']);runtime_expected[c['numpy_init']]=c['numpy_init_sha256'];runtime_expected[OUTER]=OUTER_SHA
 assert len(runtime_expected)==5
 for path,expected in runtime_expected.items():
  r=record(path,allow_symlink=True);assert r['sha256']==expected;r['resolved']=str(Path(path).resolve());runtimes[path]=r
 disk=shutil.disk_usage(ROOT);assert disk.free>1024**3
 future_sources={str(out/'reader.py'):idx['source'],str(out/'run_readback.py'):idx['controller']}
 assert len(idx['future_exact_source_copies'])==2
 for expected in idx['future_exact_source_copies']:
  p=ROOT/expected['path'];assert not p.exists() and not p.is_symlink()
  source=future_sources[str(p)];r=record(source['path']);assert (r['sha256'],r['bytes'])==(source['sha256'],source['bytes']);assert r['sha256']==expected['sha256']
 assert idx['future_contract_mirror']['sha256']==ACTUAL_SHA and idx['future_contract_mirror']['path']==str((out/'frozen-contract.json').relative_to(ROOT))
 preflight=freeze('preflight.json',dict(schema='962-apex1613031-head-application-root-preflight/v1',decision='ONE_BOUNDED_DIAGNOSTIC_LOCAL_REPLACEMENT_ONLY',static4=static,inputs77_before=before,runtime5_before=runtimes,outer_argv=idx['exact_controller_argv'],inner_argv=idx['exact_worker_argv'],controller_environment=env,inner_controls=idx['inner_controls'],outer_controls=idx['outer_controls'],disk_free_bytes=disk.free,source_and_exact_child_semantic_reviews_complete=True,guard11_once_receipt=c['root_guard_review'],native_runs_before_this_launch=0,automatic_retry=False,broader_head_or_physics_authority=False,source_author='replica_metrology',actual_preparer='existing_study_audit',exact_child_peer='clip_source_review',source001_static_refusal_preserved=True,source002_one_literal_correction_preserved=True,launch_source=record(__file__),launch_donor_source=record(BASE/'current127-apex1613031-head-context-root-execution-001/launch-once.py'),finite_runtime_scope='Five selected file identities, not a transitive package, stdlib, OS or ABI closure.'))
 out.mkdir()
 for future,source in future_sources.items():
  p=Path(future)
  with p.open('xb') as f:f.write((ROOT/source['path']).read_bytes())
  p.chmod(0o444)
 with (out/'frozen-contract.json').open('xb') as f:f.write((PREP/'actual-contract.json').read_bytes())
 (out/'frozen-contract.json').chmod(0o444)
 assert sorted(p.name for p in out.iterdir())==['frozen-contract.json','reader.py','run_readback.py']
 assert record(out/'frozen-contract.json')['sha256']==ACTUAL_SHA
 for rel,expected in c['input_hashes'].items():
  r=record(rel);assert r['sha256']==expected;before[rel]=r
 assert len(before)==79
 materialized=freeze('materialization.json',dict(preflight=preflight,inputs79_before=before,initial_files={p.name:record(p) for p in sorted(out.iterdir())},whole_actual_mirror=True))
 stdout=HERE/'controller.stdout.log';stderr=HERE/'controller.stderr.log'
 started=time.monotonic();proc=None;signals=[];fallback=False;error=None
 try:
  with stdout.open('xb') as so,stderr.open('xb') as se:
   proc=subprocess.Popen(idx['exact_controller_argv'],cwd=ROOT,stdout=so,stderr=se,start_new_session=True,env=env)
   assert os.getpgid(proc.pid)==proc.pid
   freeze('launch.json',dict(argv=idx['exact_controller_argv'],environment=env,pid=proc.pid,pgid=proc.pid,start_new_session=True,materialization=materialized,ordinary_deadline_seconds=1215,automatic_retry=False))
   try:proc.wait(timeout=max(0,1215-(time.monotonic()-started)))
   except subprocess.TimeoutExpired:
    fallback=True
    if proc.poll() is None and os.getpgid(proc.pid)==proc.pid:os.killpg(proc.pid,signal.SIGTERM);signals.append('SIGTERM')
    try:proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
     if proc.poll() is None and os.getpgid(proc.pid)==proc.pid:os.killpg(proc.pid,signal.SIGKILL);signals.append('SIGKILL')
     proc.wait()
 except BaseException as exc:error=repr(exc)
 finally:
  if proc is not None and proc.poll() is None:
   fallback=True
   if os.getpgid(proc.pid)==proc.pid:os.killpg(proc.pid,signal.SIGKILL);signals.append('SIGKILL-finally')
   proc.wait()
 elapsed=time.monotonic()-started
 after={rel:record(rel) for rel in before}
 runtime_after={p:{**record(p,allow_symlink=True),'resolved':str(Path(p).resolve())} for p in runtimes}
 static_after={p:record(p) for p in static}
 outputs={p.name:record(p) for p in sorted(out.iterdir()) if p.is_file()}
 receipt=json.loads((out/'execution-receipt.json').read_text()) if (out/'execution-receipt.json').is_file() else None
 closed=freeze('closed-result.json',dict(schema='962-apex1613031-head-application-root-closed/v1',preflight=preflight,materialization=materialized,argv=idx['exact_controller_argv'],environment=env,pid=proc.pid if proc else None,returncode=proc.returncode if proc else None,wall_seconds=elapsed,signals=signals,outer_fallback_used=fallback,error=error,controller_waited_reaped=proc is not None and proc.poll() is not None,controller_owned_group_absent=proc is not None and not group_exists(proc.pid),inputs79_before=before,inputs79_after=after,all79_inputs_unchanged=before==after,runtime5_before=runtimes,runtime5_after=runtime_after,runtime5_unchanged=runtimes==runtime_after,static4_before=static,static4_after=static_after,static4_unchanged=static==static_after,whole_actual_mirror_sha256=outputs['frozen-contract.json']['sha256'],outputs=outputs,controller_stdout=record(stdout),controller_stderr=record(stderr),inner_receipt=receipt,process_scope='Root observes controller ownership and reaping only. Native worker lifecycle, loaded versions, sampled resources and cleanup are controller/source-attributed. No universal descendant absence or true peak.',returncode_scope='Native RC2 can retain a completed partial diagnostic while the unchanged whole-head quality gate rejects; saved-result review remains necessary.',automatic_retry=False,engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False))
 for p in out.iterdir():
  if p.is_file():p.chmod(0o444)
 stdout.chmod(0o444);stderr.chmod(0o444)
 print(json.dumps(dict(closed=closed,returncode=proc.returncode if proc else None,wall_seconds=elapsed,outer_fallback_used=fallback,error=error,all79_inputs_unchanged=before==after,runtime5_unchanged=runtimes==runtime_after,output_files=list(outputs)),indent=2))
 return proc.returncode if proc is not None and not fallback and error is None and before==after and runtimes==runtime_after and static==static_after else 2

if __name__=='__main__':raise SystemExit(main())
