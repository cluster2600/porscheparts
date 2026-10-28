"""Root-owned single bounded launch; immutable inputs and stopped outputs only."""
from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,time

ROOT=Path('project-role://engineering-checkout')
BASE=ROOT/'work/962-engineering'
HERE=Path(__file__).resolve().parent
PREP=BASE/'current127-apex1613031-head-context-execution-prep-001'
PEER=BASE/'current127-apex1613031-head-context-exact-child-peer-001'
ACTUAL_SHA='37db8019cbfe3db7e14e932ea337ff82fea599aec1f136ddf443b9659055b115'
INDEX_SHA='737967bec8e9bb7e1530185aa2fd50461c11a74c5fcdba7f06415da3f4b916e3'
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
 with p.open('x') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n')
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
 for p,sha in [(PREP/'actual-contract.json',ACTUAL_SHA),(PREP/'index.json',INDEX_SHA),(PEER/'review.json','382e1ce857d2f1ae7c55599c33928d2ef2739613aaf8a10a568124dd8eb81a48'),(PEER/'bindings.json','ae95a176c84f4a9e39c961d50f5868af9d0d5c68d82d496a97ec8884d29fac81')]:
  r=record(p);assert r['sha256']==sha;static[str(p)]=r
 c=json.loads((PREP/'actual-contract.json').read_text());idx=json.loads((PREP/'index.json').read_text())
 peer=json.loads((PEER/'review.json').read_text());bindings=json.loads((PEER/'bindings.json').read_text())
 assert peer['decision']=='CLEAR_EXACT_CHILD_READ_ONLY_INTENT_BINDINGS_ONLY' and peer['blockers']==[]
 assert bindings['all63_current_small_before']==idx['all63_current_small_records']
 assert len(c['input_hashes'])==66 and len(idx['all63_current_small_records'])==63
 assert set(idx['source_AST_consumed_keys'])<=set(c)
 assert all(c[k] is False for k in idx['FORBIDDEN_false_comprehension_keys'])
 assert c['declared_controller_command_conformant'] is False and c['actual_child_sha256'] is None
 assert all(c[k] is True for k in ('native_execution_authorized','native_read_only_query_authorized','root_and_peer_review_complete','selected_runtime_review_complete'))
 out=ROOT/c['output_directory']
 assert out==out.resolve() and not out.exists() and not out.is_symlink()
 assert idx['outer_argv']==[OUTER,'-I','-B',str(out/'run_readback.py'),'--contract-sha256',ACTUAL_SHA]
 assert idx['inner_argv']==[c['native_python'],'-B',str(out/'reader.py')]
 assert idx['root_outer_controls']['ordinary_wall_seconds']==135 and idx['root_outer_controls']['TERM_grace_seconds']==8
 assert idx['inner_controls']['hard_wall_seconds']==120 and idx['inner_controls']['automatic_retry'] is False
 before={}
 for rel,expected in idx['all63_current_small_records'].items():
  r=record(rel);assert (r['sha256'],r['bytes'])==(expected['sha256'],expected['bytes']);assert c['input_hashes'][rel]==r['sha256'];before[rel]=r
 msh=record(c['MSH']);assert (msh['sha256'],msh['bytes'])==(c['MSH_sha256'],c['MSH_bytes'])
 before[c['MSH']]=msh
 runtimes={}
 runtime_expected=dict(c['external_runtime_hashes']);runtime_expected[c['numpy_init']]=c['numpy_init_sha256'];runtime_expected[OUTER]=OUTER_SHA
 for path,expected in runtime_expected.items():
  r=record(path,allow_symlink=True);assert r['sha256']==expected;r['resolved']=str(Path(path).resolve());runtimes[path]=r
 disk=shutil.disk_usage(ROOT);assert disk.free>1024**3
 for future,expected in idx['future2_exact_source_copies'].items():
  assert not (ROOT/future).exists() and not (ROOT/future).is_symlink()
  r=record(expected['source']);assert (r['sha256'],r['bytes'])==(expected['sha256'],expected['bytes'])
 preflight=freeze('preflight.json',dict(schema='962-current127-apex1613031-context-root-preflight/v1',decision='ONE_BOUNDED_READ_ONLY_QUERY',static=static,inputs64_before=before,runtime5_before=runtimes,outer_argv=idx['outer_argv'],inner_argv=idx['inner_argv'],inner_controls=idx['inner_controls'],outer_controls=idx['root_outer_controls'],disk_free_bytes=disk.free,source_and_peer_semantic_reviews_complete=True,guard4_once_receipt=c['root_source_review_sha256'],native_runs_before_this_launch=0,automatic_retry=False,broader_head_or_physics_authority=False,source_author='replica_metrology',source_author_correction_retained=True,launch_source=record(__file__)))
 out.mkdir()
 for future,expected in idx['future2_exact_source_copies'].items():
  p=ROOT/future
  with p.open('xb') as f:f.write((ROOT/expected['source']).read_bytes())
  p.chmod(0o444)
 with (out/'frozen-contract.json').open('xb') as f:f.write((PREP/'actual-contract.json').read_bytes())
 (out/'frozen-contract.json').chmod(0o444)
 assert sorted(p.name for p in out.iterdir())==['frozen-contract.json','reader.py','run_readback.py']
 assert record(out/'frozen-contract.json')['sha256']==ACTUAL_SHA
 for rel,expected in c['input_hashes'].items():
  r=record(rel);assert r['sha256']==expected;before[rel]=r
 materialized=freeze('materialization.json',dict(preflight=preflight,inputs66_before=before,initial_files={p.name:record(p) for p in sorted(out.iterdir())},whole_actual_mirror=True))
 stdout=HERE/'controller.stdout.log';stderr=HERE/'controller.stderr.log'
 started=time.monotonic();proc=None;signals=[];fallback=False;error=None
 try:
  with stdout.open('xb') as so,stderr.open('xb') as se:
   proc=subprocess.Popen(idx['outer_argv'],cwd=ROOT,stdout=so,stderr=se,start_new_session=True,env={'PATH':'/usr/bin:/bin','LANG':'C','PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'})
   assert os.getpgid(proc.pid)==proc.pid
   freeze('launch.json',dict(argv=idx['outer_argv'],pid=proc.pid,pgid=proc.pid,start_new_session=True,materialization=materialized,ordinary_deadline_seconds=135,automatic_retry=False))
   try:proc.wait(timeout=max(0,135-(time.monotonic()-started)))
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
 closed=freeze('closed-result.json',dict(schema='962-current127-apex1613031-context-root-closed/v1',preflight=preflight,materialization=materialized,argv=idx['outer_argv'],pid=proc.pid if proc else None,returncode=proc.returncode if proc else None,wall_seconds=elapsed,signals=signals,outer_fallback_used=fallback,error=error,controller_waited_reaped=proc is not None and proc.poll() is not None,controller_owned_group_absent=proc is not None and not group_exists(proc.pid),inputs66_before=before,inputs66_after=after,all66_inputs_unchanged=before==after,runtime5_before=runtimes,runtime5_after=runtime_after,runtime5_unchanged=runtimes==runtime_after,static4_before=static,static4_after=static_after,static4_unchanged=static==static_after,whole_actual_mirror_sha256=outputs['frozen-contract.json']['sha256'],outputs=outputs,controller_stdout=record(stdout),controller_stderr=record(stderr),inner_receipt=receipt,process_scope='Root observes controller ownership and reaping only. Native worker lifecycle, loaded versions, sampled resources and cleanup are controller/source-attributed. No universal descendant absence or true peak.',automatic_retry=False,engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False))
 for p in out.iterdir():
  if p.is_file():p.chmod(0o444)
 stdout.chmod(0o444);stderr.chmod(0o444)
 print(json.dumps(dict(closed=closed,returncode=proc.returncode if proc else None,wall_seconds=elapsed,outer_fallback_used=fallback,error=error,all66_inputs_unchanged=before==after,runtime5_unchanged=runtimes==runtime_after,output_files=list(outputs)),indent=2))
 return 0 if proc is not None and proc.returncode==0 and not fallback and error is None and before==after and runtimes==runtime_after and static==static_after else 2

if __name__=='__main__':raise SystemExit(main())
