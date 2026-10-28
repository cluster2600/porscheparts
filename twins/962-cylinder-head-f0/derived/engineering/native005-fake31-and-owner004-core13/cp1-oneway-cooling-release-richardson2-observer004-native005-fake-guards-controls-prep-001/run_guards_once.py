"""HELD/UNRUN retained-anchor owner for one fixed31-method native005 fake fixture."""
import time
started=time.monotonic();controller_stop_requests=[]
import hashlib,json,os,re,select,signal,subprocess,sys,traceback
from pathlib import Path

R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E=R/'work/962-engineering'
X=E/'cp1-oneway-cooling-release-richardson2-observer004-native005-fake-guards-controls-prep-001'
D=E/'cp1-oneway-cooling-release-richardson2-observer004-native005-fake-guards-root-execution-001'
W=E/'cp1-oneway-cooling-release-richardson2-observer004-native005-fake-guards-root-terminal-review-001'
WRAPPER=X/'stopped_exec_wrapper.py'
CAP=33554432

PYTHON={"path":"/Users/maxime/.codex/worktrees/962-watercooled-head/3dprinting993/work/962-head/check-venv/bin/python","resolved_path":"/Users/maxime/.local/share/uv/python/cpython-3.12.11-macos-aarch64-none/bin/python3.12","sha256":"1699bf8aa705a8bb71613bef5cdd7d7c8c9d9a188a841f41679aa9b5830b8f60","bytes":49968,"is_symlink":True,"raw_target":"python3.12"}
ENV={"PATH":"/usr/bin:/bin","LANG":"C","LC_ALL":"C","OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1","VECLIB_MAXIMUM_THREADS":"1","FI_PROVIDER":"tcp"}
REQUIRED_PROTECTED={
  "owner": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-prep-005/run_root_once.py",
    "sha256": "34826ad993e4d874455adb40777df545f76cf611a6f23ae021a49302dc0dd649",
    "bytes": 61563
  },
  "caller": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-prep-005/run_native_capture.py",
    "sha256": "a04276da60fe09d9af26d32c7661fb421105b7c93724d43c728025dd1fd51aa5",
    "bytes": 45810
  },
  "native_wrapper": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-prep-005/stopped_exec_wrapper.py",
    "sha256": "a81328f9e07bded2120d8f908f8831bdafead07132ae09a1af4ccfcc4bf50e17",
    "bytes": 5295
  },
  "source005_index": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-prep-005/index.json",
    "sha256": "acb06644ef2df3ed06273b4d936ecab8a76cd7760b1ddcc6e911bca0d1c554c3",
    "bytes": 6734
  },
  "control_contract": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native003-owned-control-choices-001/control-contract.json",
    "sha256": "10aaa53acc3fbe15f07aeadd75f33c0edb886d8d79d4fe824f898907cb12a819",
    "bytes": 39675
  },
  "control_clarification": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native003-owned-control-choices-clarification-001/CLARIFICATION.json",
    "sha256": "df5ce24e733c94cfe5522c7a824f38c4739538e87e71f40831ef37aae83c1d5b",
    "bytes": 8610
  },
  "predecessor004_findings": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native004-source-peer-001/findings.json",
    "sha256": "4a70b1e33769e838d74d68d808fe60ca49b6ac5f2a5103efa8cdaa2f6fc38787",
    "bytes": 9189
  },
  "source005_root_review": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-root-source-review-001/review.json",
    "sha256": "a8f8dd842abdc4a309b8bd4dc7c420af65ef1e9bb5b80826eb71ea93f9cd76f8",
    "bytes": 3969
  },
  "source005_peer_review": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-source-peer-001/review.json",
    "sha256": "777233540d91a59b70df3ae0947eddb32a07a3a7b1cc715de4906873d4fc946f",
    "bytes": 5291
  },
  "source005_peer_findings": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-source-peer-001/findings.json",
    "sha256": "0a014c7e61dd2d05f78f054238b101695041892e740f7636d9d024f2246f240f",
    "bytes": 10552
  },
  "source005_peer_bindings": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-source-peer-001/bindings.json",
    "sha256": "29a29c02987c67782cd5a1ab8654bc43f3309995e49a6bad25fd4e04b9546691",
    "bytes": 14116
  },
  "fixture": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-fake-guards-prep-001/test_native005_guards.py",
    "sha256": "48e1514f59b0d3608b55613fc15a2989a8f9dda02c464659ec49944372d99c60",
    "bytes": 54219
  },
  "fixture_index_json": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-fake-guards-prep-001/index.json",
    "sha256": "cba1bd690951d76394c39440c41c2ad9c30ad0e515d55e8d6241d79f5beed63d",
    "bytes": 5698
  },
  "fixture_METHOD_md": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-fake-guards-prep-001/METHOD.md",
    "sha256": "2e7b91c9d418691783bad613defe6460445f13e47820d56c0a26fe4fcc1aeb29",
    "bytes": 7965
  },
  "fixture_bindings_json": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-fake-guards-prep-001/named-bindings.json",
    "sha256": "b02c20ad01b102052c72e97f5bd35781d4e72a91828a8522569c7569b2e1a0d0",
    "bytes": 31643
  },
  "fixture_coverage_json": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-fake-guards-prep-001/coverage.json",
    "sha256": "16b2c7024a43883a999782669a4835492e71bde9d7255d0edf38588576d03f1f",
    "bytes": 23152
  },
  "fixture_peer_0": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-fake-guards-source-peer-001/review.json",
    "sha256": "9c7c8f5f6ad8f4f3f0dc3caa4a6bcf84ebd16b3e8aea7605d80ee63c96b56965",
    "bytes": 5629
  },
  "fixture_peer_1": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-fake-guards-source-peer-001/findings.json",
    "sha256": "45b28cbd872f23777ebdc15d984e3da4fb45834964b61f2713803e796b057774",
    "bytes": 22893
  },
  "fixture_peer_2": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-fake-guards-source-peer-001/bindings.json",
    "sha256": "f16871e36de42c3d654306b91e08cc1829ca280fddce9198b3e361ccf0328fd8",
    "bytes": 6476
  },
  "fixture_root_review": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-fake-guards-root-source-review-001/review.json",
    "sha256": "896ede06ca1daedb5321bd93230190e9b6bef420ae4953adaf3f1c4d96f17e4a",
    "bytes": 5336
  }
}

CONTROLS=dict(normal_seconds=40,TERM_absolute_seconds=48,KILL_reap_absolute_seconds=56,whole_seconds=60,
    TERM_grace_seconds=8,KILL_reap_grace_seconds=8,total_inclusive_bytes=33554432,thread_environment=1,retries=0,RSS_sampler=False)
RUNTIME_SELECTION=dict(path='work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-fake-guard-runtime-selection-root-001/runtime-identity.json',sha256='dea37e06655d76b90c12d6174f3c4fd601a710a4fc4d59f8197778b029ff9322',bytes=1765)
DIRECT_ROLES=('controller','wrapper','control_preparation_index','fixture_source_peer','fixture_source_bindings',
    'root_fixture_source_review','exact_control_peer','exact_control_bindings','root_control_review','runtime_selection')
METHODS=('test_01_owner_normal_real_main_and_future_deadline','test_02_owner_already_default_precondition','test_03_caller_normal_identity_running_receipt_return','test_04_caller_already_default_precondition','test_05_lost_owner_handshake_revokes_next_signal','test_06_lost_terminal_relationship_never_resignals','test_07_lost_owner_query_closes_only_that_pid_authority','test_08_lost_caller_query_has_no_pid_signal','test_09_lost_native_reap_stays_unknown','test_10_actual_caller_evidence_rejects_clock_echo_and_stdout_mutants','test_11_full_main_postwrite_failure_preserves_prefinal_bytes_and_raw_refusal','test_12_identity_edge_refuses_without_normal_wait_or_replacement','test_13_precontinuation_abort_is_direct_pid_only','test_14_cont_uncertainty_group_cleanup_and_first_deadlines','test_15_owner_constructor_unknown_or_late_preserves_exact_ownership','test_16_native_constructor_unknown_or_late_never_gains_signal_authority','test_17_sample_error_is_not_erased_by_exit_event','test_18_postreap_presence_or_unknown_never_resignals','test_19_actual_fixed_queries_drain_split_streams_and_accept_reported_zero','test_20_reaped_query_partial_eof_error_never_signals_reused_pid','test_21_unreaped_query_timeout_parent_refusal_precedes_own_pid_cleanup','test_22_actual_retained_destructor_normal_unreaped_and_partial_instances','test_23_no_wait_after_cutoff_and_unknown_does_not_become_zero','test_24_canonical_original_token_variants_are_refused','test_25_actual_deadline_bypasses_capture_and_same_and_preserves_consumed_status','test_26_actual_inclusive_union_counts_distinct_paths_and_pending_receipt','test_27_wrapper_real_main_orders_hello_stop_and_exact_handoff','test_28_early_consumed_terminal_is_not_continued_or_reaped_twice','test_29_whole_owner_unreaped_late_return_preserves_unknown_without_new_api','test_30_whole_owner_query_timeout_latches_term_before_query_pid_cleanup','test_31_actual_timeout_conversion_and_original_equality_return_check')
HELD_LEADERS=[]


class _RetainedPopen(subprocess.Popen):
    # Last-resort refusal must never acquire Popen's implicit destructor poll.
    def __del__(self):
        pass


def need(condition, message):
    if not condition:
        raise ValueError(message)


def rec(p):
 h=hashlib.sha256();size=0
 with p.open('rb') as f:
  while True:
   b=f.read(1024**2)
   if not b:break
   h.update(b);size+=len(b)
 return dict(path=str(p.relative_to(R)) if p.is_relative_to(R) else str(p),sha256=h.hexdigest(),bytes=size)


def record_controller_stop(signum,frame):
 controller_stop_requests.append(dict(signal=signum,name=signal.Signals(signum).name,elapsed_seconds=time.monotonic()-started))


def group_exists(pid):
 try:os.killpg(pid,0);return True
 except ProcessLookupError:return False


def selected(pin):
    name=Path(pin['path']);p=name if name.is_absolute() else R/name
    need('..' not in name.parts and p.is_file() and not p.is_symlink() and p.resolve(strict=True)==p,'Canonical fixed control required')
    got=rec(p);need(got==pin,'Changed control: '+str(name));return p


def identities(records,py):
    out={}
    for name,v in records.items():selected(v);out[name]=dict(v)
    p=Path(py['path']);target=p.resolve(strict=True)
    need(str(target)==py['resolved_path'] and target.is_file() and not target.is_symlink(),'Changed selected interpreter route')
    body=rec(target);need(body['sha256']==py['sha256'] and body['bytes']==py['bytes'],'Changed selected interpreter body')
    out['selected_python']=dict(body=body,path=str(p),resolved=str(target),is_symlink=p.is_symlink(),raw_target=os.readlink(p) if p.is_symlink() else None)
    return out


def event_record(event):
    return dict(ident=event.ident,filter=event.filter,flags=event.flags,fflags=event.fflags,data=event.data,udata=event.udata)


def gate(ceiling,message,stop=True):
    need(time.monotonic()<started+ceiling and (not stop or not controller_stop_requests),message)


def inclusive_census(first_party):
    # Installed runtime/provider bodies are excluded unless copied into owned D.
    files={}
    for p in D.rglob('*'):
        need(not p.is_symlink(),'Unexpected owned symlink')
        if p.is_file():files[str(p)]=p.stat().st_size
    for pin in first_party.values():
        p=Path(pin['path']);p=p if p.is_absolute() else R/p
        need(p.is_file() and not p.is_symlink(),'Missing first-party census input')
        files[str(p)]=p.stat().st_size
    for p in (W/'outer.stdout',W/'outer.stderr'):
        need(p.is_file() and not p.is_symlink() and p.resolve(strict=True)==p,'Fixed outer streams required')
        files[str(p)]=p.stat().st_size
    return dict(files=files,total_bytes=sum(files.values()))


def exit_events(kq,pid,report,timeout):
    events=kq.control(None,1,timeout)
    for ev in events:
        report['events'].append(event_record(ev))
        need(ev.ident==pid and ev.filter==select.KQ_FILTER_PROC and not ev.flags&select.KQ_EV_ERROR and ev.fflags&select.KQ_NOTE_EXIT,'Unexpected exit event')
    return bool(events)


def reap(proc,report,deadline):
    while time.monotonic()<deadline:
        pid,status=os.waitpid(proc.pid,os.WNOHANG)
        if pid:
            need(pid==proc.pid and (os.WIFEXITED(status) or os.WIFSIGNALED(status)),'Wrong exact terminal status')
            report['reaped']=True;report['raw_returncode']=os.waitstatus_to_exitcode(status);proc.returncode=report['raw_returncode']
            need(time.monotonic()<deadline,'Terminal wait returned beyond absolute deadline')
            return
        time.sleep(min(.01,max(0,deadline-time.monotonic())))
    raise ValueError('Exact direct-child reap incomplete at bounded deadline')


def diagnostics():
    need(all((D/name).stat().st_size<=CAP for name in ('fixture.stdout','fixture.stderr')),'Full stream exceeds cap; retained without parsing')
    with (D/'fixture.stdout').open('rb') as f:out=f.read(CAP+1)
    with (D/'fixture.stderr').open('rb') as f:err=f.read(CAP+1)
    need(len(out)+len(err)<=CAP and out==b'','Unexpected/oversize full diagnostics retained')
    text=err.decode('utf-8','strict')
    prefix=''.join(name+' (__main__.Native005Guards.'+name+') ... ok\n' for name in METHODS)
    need(text.startswith(prefix),'Exact ordered31 method rows required')
    need(re.fullmatch(r'\n-{70}\nRan 31 tests in [0-9]+(?:\.[0-9]+)?s\n\nOK\n',text[len(prefix):]) is not None,'Complete Ran31/finalOK diagnostics required')
    return dict(methods=list(METHODS),method_count=31,all_31_completed=True,native005_fake_synthetic_only=True)


def admit():
    need(len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1]),'HELD: sole external root-admission digest required')
    A=D/'admission.json';ap=rec(A)
    need(ap['sha256']==sys.argv[1] and ap['bytes']<=CAP,'Changed/oversize root admission')
    auth=json.loads(A.read_bytes())
    need(auth['schema']=='962-native005-fake-guard-root-admission/v1' and auth['root_issued'] is True and auth['guard_execution_authorized'] is True,'No guard authority')
    need(type(auth['invocations']) is int and auth['invocations']==1 and auth['automatic_retry'] is False and auth['controls']==CONTROLS,'One fixed bounded invocation required')
    need(all(auth[k] is True for k in ('independent_fixture_source_review_complete','independent_control_source_review_complete','root_control_review_complete','selected_runtime_and_inputs_accepted_by_root')),'Pending source/control/fixed-runtime admission')
    need(all(auth[k] is False for k in ('real_head_input_authorized','Z3_authorized','native_execution_authorized','physical_acceptance','manufacturing_authorized')),'No scientific/native authority')
    need(auth['selected_python']==PYTHON and auth['runtime_selection']==RUNTIME_SELECTION and auth['environment']==ENV and all(os.environ.get(k)==v for k,v in ENV.items()),'Exact3.12/thread-one route required; no environment dump')
    need(str(Path(sys.executable).resolve(strict=True))==PYTHON['resolved_path'] and sys.version_info[:3]==(3,12,11),'Selected3.12.11 owner required')
    need(Path(PYTHON['path']).is_symlink() is PYTHON['is_symlink'] and os.readlink(PYTHON['path'])==PYTHON['raw_target'],'Changed selected alias metadata')
    need(sys.flags.isolated==sys.flags.dont_write_bytecode==sys.flags.no_site==1 and sys.flags.optimize==0 and 'site' not in sys.modules and '_distutils_hack' not in sys.modules,'Exact -B-I-S startup required')
    need(signal.getsignal(signal.SIGCHLD)==signal.SIG_DFL,'Already-default SIGCHLD and no competing waiter required')
    need(all(hasattr(select,k) for k in ('kqueue','kevent','KQ_FILTER_PROC','KQ_NOTE_EXIT','KQ_EV_ADD','KQ_EV_ENABLE','KQ_EV_ONESHOT','KQ_EV_ERROR')) and all(hasattr(os,k) for k in ('waitpid','WUNTRACED','WNOHANG','WIFSTOPPED','WSTOPSIG','WIFEXITED','WIFSIGNALED','waitstatus_to_exitcode','getpgid','getsid','killpg','kill')),'Named APIs unavailable; no launch')
    need(not D.is_symlink() and D.resolve(strict=True)==D and set(p.name for p in D.iterdir())=={'admission.json'},'Fresh fixed owned root required')
    need(auth['fixture']==REQUIRED_PROTECTED['fixture'] and auth['owner_source']==REQUIRED_PROTECTED['owner'],'Pinned fixture and selected owner source required')
    need(auth['root_fixture_source_review']==REQUIRED_PROTECTED['fixture_root_review'],'Exact root focused fixture source decision required')
    need(auth['fixture_source_peer']==REQUIRED_PROTECTED['fixture_peer_0'] and auth['fixture_source_bindings']==REQUIRED_PROTECTED['fixture_peer_2'],'Exact independent fixture source peer required')
    need(selected(auth['controller'])==X/'run_guards_once.py' and auth['controller']==rec(Path(__file__)) and selected(auth['wrapper'])==WRAPPER and selected(auth['control_preparation_index'])==X/'index.json','Fixed executed controller and source preparation paths required')
    need(auth['outer_stream_paths']==[str(W/'outer.stdout'),str(W/'outer.stderr')],'Fixed external streams required')
    first=dict(auth['protected_records'])
    need(all(first.get(k)==v for k,v in REQUIRED_PROTECTED.items()),'All known finite provenance must be protected')
    for k in DIRECT_ROLES:first['direct_'+k]=auth[k]
    packet=json.loads(selected(auth['control_preparation_index']).read_bytes())
    need(set(packet['files'])=={'run_guards_once.py','stopped_exec_wrapper.py','METHOD.md','bindings.json','source-reuse.json','source.diff','source.inverse.diff'} and packet['file_count_including_this_index']==8,'Fixed eight-file control source packet required')
    need(all(pin in first.values() for pin in packet['files'].values()),'All finite control source/proof files must be admitted and protected')
    first['root_admission']=ap
    records={}
    for pin in first.values():
        p=Path(pin['path']);p=p if p.is_absolute() else R/p
        need(str(p) not in records or records[str(p)]==pin,'Conflicting descriptor for one canonical path')
        records[str(p)]=pin
    need(type(auth['expected_canonical_input_count']) is int and len(records)==auth['expected_canonical_input_count'],'Exact canonical unique input count required')
    before=identities(records,PYTHON)
    need(inclusive_census(first)['total_bytes']<=CAP,'Initial full inclusive cap')
    gate(40,'Preflight exhausted normal40; no child launched')
    return auth,first,records,before,ap


def main():
    auth,first,records,before,ap=admit()
    report=dict(schema='962-native005-fake-guard-owner-result/v1',status='INCOMPLETE',admission=ap,before=before,after=None,
        PID=None,ownership_certificate=None,process_started=False,continuation_intent=False,normal_NOTE_EXIT=False,
        group_signal_intent_ended=False,reaped=False,raw_returncode=None,direct_relationship_unknown=False,events=[],
        stop_actions=[],cleanup_errors=[],failure=None,group_absent=None,postreap_absence_observations=0,
        diagnostics=None,owned_streams={},stream_read_errors=[],finalization_errors=[],receipt_write_error=None,
        complete_candidate=False,last_resort_unreaped_exit=False,sampled_RSS_bytes=None,sampled_RSS_observation_pass=None,
        RSS_scope='No RSS sampler, query, hard quota or pass claim.',source_descriptor_reads=True,
        scientific_body_read=False,Z3_executed=False,native_execution=False,physical_acceptance=False,automatic_retry=False)
    proc=None;kq=None;certificate=None
    old_TERM=signal.signal(signal.SIGTERM,record_controller_stop);old_INT=signal.signal(signal.SIGINT,record_controller_stop)
    try:
        kq=select.kqueue()
        argv=[PYTHON['path'],'-B','-I','-S',str(WRAPPER),ap['sha256']]
        need(auth['argv_prefix']==argv[:-1] and auth['cwd']==str(D),'Fixed stopped-wrapper invocation required')
        with (D/'fixture.stdout').open('xb') as out,(D/'fixture.stderr').open('xb') as err:
            gate(40,'Stopped before fixed wrapper launch')
            proc=_RetainedPopen(argv,cwd=D,env=ENV,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
            HELD_LEADERS.append(proc);report.update(process_started=True,PID=proc.pid)
            handshake=min(started+40,time.monotonic()+5)
            while True:
                need(not controller_stop_requests and time.monotonic()<handshake,'Stopped/late wrapper handshake')
                pid,status=os.waitpid(proc.pid,os.WUNTRACED|os.WNOHANG)
                if pid:
                    need(pid==proc.pid,'Wrong direct-child status')
                    report['wrapper_wait_status']=status
                    if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                        report['reaped']=True;report['raw_returncode']=os.waitstatus_to_exitcode(status);proc.returncode=report['raw_returncode']
                        raise ValueError('Wrapper ended before stopped ownership certificate')
                    need(not controller_stop_requests and time.monotonic()<handshake,'Stopped status returned beyond handshake cutoff')
                    need(os.WIFSTOPPED(status) and os.WSTOPSIG(status)==signal.SIGSTOP,'Exact stopped-before-exec status required')
                    break
                time.sleep(min(.01,max(0,handshake-time.monotonic())))
            certificate=dict(PID=proc.pid,PGID=os.getpgid(proc.pid),SID=os.getsid(proc.pid),direct_child_unreaped=True,wait_status=status)
            need(certificate['PID']==certificate['PGID']==certificate['SID'],'Changed stopped session identity')
            report['ownership_certificate']=certificate
            watch=select.kevent(proc.pid,filter=select.KQ_FILTER_PROC,flags=select.KQ_EV_ADD|select.KQ_EV_ENABLE|select.KQ_EV_ONESHOT,fflags=select.KQ_NOTE_EXIT)
            events=kq.control([watch],1,0);report['events'].extend(event_record(ev) for ev in events)
            need(not events,'Unexpected registration event before continuation')
            gate(40,'Stopped/late before continuation intent')
            report['continuation_intent']=True
            os.kill(proc.pid,signal.SIGCONT)
            gate(40,'SIGCONT returned late/stopped')
            while True:
                gate(40,'Normal40 exhausted; reserve cleanup')
                need(inclusive_census(first)['total_bytes']<=CAP,'Inclusive cap exceeded')
                seen=exit_events(kq,proc.pid,report,min(.05,max(0,started+40-time.monotonic())))
                if seen:
                    report['normal_NOTE_EXIT']=True;report['group_signal_intent_ended']=True
                gate(40,'Exit query returned late/stopped')
                if seen:
                    break
            reap(proc,report,started+56)
            need(report['raw_returncode']==0,'Fixture raw nonzero; full diagnostics retained')
        gate(60,'Stopped/late normal stream closure')
    except BaseException as exc:
        if isinstance(exc,ChildProcessError):report['direct_relationship_unknown']=True
        report['failure']=traceback.format_exc()
    finally:
        if proc is not None and not report['reaped']:
            if proc not in HELD_LEADERS:HELD_LEADERS.append(proc)
            if not report['group_signal_intent_ended']:
                if certificate is not None and report['continuation_intent']:
                    try:
                        need(not report['direct_relationship_unknown'] and certificate['PID']==certificate['PGID']==certificate['SID']==proc.pid and proc.returncode is None,'Lost retained group anchor')
                        gate(48,'TERM absolute48 expired',stop=False)
                        try:os.killpg(proc.pid,signal.SIGTERM);report['stop_actions'].append(dict(scope='certified unreaped group',signal=int(signal.SIGTERM)))
                        except BaseException:report['cleanup_errors'].append(traceback.format_exc())
                        deadline=min(started+48,time.monotonic()+8)
                        while time.monotonic()<deadline:
                            try:exit_events(kq,proc.pid,report,min(.05,max(0,deadline-time.monotonic())))
                            except BaseException:report['cleanup_errors'].append(traceback.format_exc());break
                    except BaseException:report['cleanup_errors'].append(traceback.format_exc())
                    try:
                        need(not report['direct_relationship_unknown'] and certificate['PID']==certificate['PGID']==certificate['SID']==proc.pid and proc.returncode is None,'Unknown/released group anchor; no KILL')
                        gate(56,'KILL absolute56 expired',stop=False)
                        try:os.killpg(proc.pid,signal.SIGKILL);report['stop_actions'].append(dict(scope='certified unreaped group',signal=int(signal.SIGKILL)))
                        except BaseException:report['cleanup_errors'].append(traceback.format_exc())
                    except BaseException:report['cleanup_errors'].append(traceback.format_exc())
                else:
                    try:
                        need(not report['direct_relationship_unknown'] and proc.returncode is None,'Unknown direct relationship; no PID signal')
                        gate(56,'Own-PID KILL absolute56 expired',stop=False)
                        try:os.kill(proc.pid,signal.SIGKILL);report['stop_actions'].append(dict(scope='only own unreaped PID before continuation certificate',signal=int(signal.SIGKILL)))
                        except BaseException:report['cleanup_errors'].append(traceback.format_exc())
                    except BaseException:report['cleanup_errors'].append(traceback.format_exc())
            # No signal error can skip this separate bounded explicit reap attempt.
            try:reap(proc,report,min(started+56,time.monotonic()+8))
            except BaseException as exc:
                if isinstance(exc,ChildProcessError):report['direct_relationship_unknown']=True
                report['cleanup_errors'].append(traceback.format_exc())
        # One absence-only check after deliberate reap. No later numeric group signal.
        if proc is not None and report['reaped']:
            try:
                report['postreap_absence_observations']+=1;report['group_absent']=not group_exists(proc.pid)
            except BaseException:
                report['group_absent']=None;report['cleanup_errors'].append(traceback.format_exc())
            if report['group_absent'] is False:report['cleanup_errors'].append('Postreap group present; no numeric-PGID cleanup')
        if kq is not None:
            try:kq.close()
            except BaseException:report['cleanup_errors'].append(traceback.format_exc())
        try:
            gate(60,'Stopped/late identity closure')
            report['after']=identities(records,PYTHON);gate(60,'Identity closure returned late/stopped')
        except BaseException:report['finalization_errors'].append(traceback.format_exc())
        report['all_controls_unchanged']=report['after']==before
        for name in ('fixture.stdout','fixture.stderr'):
            try:
                p=D/name;need(p.is_file() and not p.is_symlink(),'Missing final fixed stream')
                report['owned_streams'][name]=rec(p)
            except BaseException:report['stream_read_errors'].append(traceback.format_exc())
        if report['reaped'] and report['group_absent'] is True and report['raw_returncode']==0:
            try:report['diagnostics']=diagnostics();gate(60,'Diagnostics returned late/stopped')
            except BaseException:report['finalization_errors'].append(traceback.format_exc())
        try:
            report['inclusive_before_receipt']=inclusive_census(first)
            gate(60,'Stopped/late before full receipt')
            need(report['inclusive_before_receipt']['total_bytes']<=CAP,'Final inclusive cap exceeded')
        except BaseException:report['finalization_errors'].append(traceback.format_exc())
        try:signal.signal(signal.SIGINT,old_INT);signal.signal(signal.SIGTERM,old_TERM)
        except BaseException:report['cleanup_errors'].append(traceback.format_exc())
        report['handler_cutoff_elapsed_seconds']=time.monotonic()-started
        report['handled_stop_requests']=list(controller_stop_requests)
        report['post_cutoff_scope']='Signals after restoration may terminate owner/leave missing receipt; no all-lifetime capture claim.'
        report['last_resort_unreaped_exit']=proc is not None and not report['reaped']
        report['complete_candidate']=bool(report['normal_NOTE_EXIT'] and report['reaped'] and report['raw_returncode']==0 and report['group_absent'] is True and report['postreap_absence_observations']==1 and report['failure'] is None and not report['cleanup_errors'] and not report['finalization_errors'] and not report['stream_read_errors'] and set(report['owned_streams'])=={'fixture.stdout','fixture.stderr'} and report['diagnostics'] is not None and report['all_controls_unchanged'] and not controller_stop_requests and time.monotonic()<started+60)
        report['status']='COMPLETE_31_NATIVE005_FAKE_GUARDS_CANDIDATE_ONLY' if report['complete_candidate'] else 'INCOMPLETE'
        report['root_full_startup_return_clock_outer0_final_census_and_independent_absence_required']=True
        try:
            gate(60,'No full receipt serialization time',stop=False)
            encoded=(json.dumps(report,indent=2,allow_nan=False)+'\n').encode()
            need(inclusive_census(first)['total_bytes']+len(encoded)<=CAP,'Full receipt exceeds cap; no truncation')
            gate(60,'Receipt serialization returned late',stop=False)
            with (D/'closed-result.json').open('xb') as f:f.write(encoded);f.flush()
            need(inclusive_census(first)['total_bytes']<=CAP,'Receipt close made final cap fail')
            gate(60,'Receipt close/final census returned late',stop=False)
        except BaseException:
            report['receipt_write_error']=traceback.format_exc()
            try:
                raw=report['receipt_write_error'].encode()
                if time.monotonic()<started+60 and inclusive_census(first)['total_bytes']+len(raw)<=CAP:
                    with (D/'receipt-error.txt').open('xb') as f:f.write(raw);f.flush()
            except BaseException:pass
            try:print(report['receipt_write_error'],file=sys.stderr,flush=True)
            except BaseException:pass
    rc=0 if report['complete_candidate'] and report['receipt_write_error'] is None and not report['stream_read_errors'] and not report['finalization_errors'] and not controller_stop_requests and time.monotonic()<started+60 else 2
    if proc is not None and not report['reaped']:
        # Last-resort refusal only; no destructor poll, cleanup or absence claim.
        try:sys.stdout.flush();sys.stderr.flush()
        except BaseException:pass
        os._exit(2)
    return rc


if __name__=='__main__':raise SystemExit(main())

