"""HELD/UNRUN retained-anchor owner for one fixed nine-method F1 fixture."""
import time
started=time.monotonic();controller_stop_requests=[]
import hashlib,json,os,re,select,signal,subprocess,sys,traceback
from pathlib import Path

R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E=R/'work/962-engineering'
X=E/'head-star-current24-qfnra-five-toy-owner-f1-guards-controls-prep-002'
D=E/'head-star-current24-qfnra-five-toy-owner-f1-guards-root-execution-001'
W=E/'head-star-current24-qfnra-five-toy-owner-f1-guards-root-terminal-review-001'
WRAPPER=X/'stopped_exec_wrapper.py'
CAP=33554432

PYTHON={"path":"/Users/maxime/.codex/worktrees/962-watercooled-head/3dprinting993/work/962-head/check-venv/bin/python","resolved_path":"/Users/maxime/.local/share/uv/python/cpython-3.12.11-macos-aarch64-none/bin/python3.12","sha256":"1699bf8aa705a8bb71613bef5cdd7d7c8c9d9a188a841f41679aa9b5830b8f60","bytes":49968,"is_symlink":True,"raw_target":"python3.12"}
ENV={"PATH":"/usr/bin:/bin","LANG":"C","LC_ALL":"C","OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1","VECLIB_MAXIMUM_THREADS":"1","FI_PROVIDER":"tcp"}
REQUIRED_PROTECTED={
  "owner": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-prep-002/run_owner_once.py",
    "sha256": "f3a27f43c1ea794a552f697d556c9b6a51668d829b86f438debf03a0cd6892e2",
    "bytes": 32207
  },
  "owner_index": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-prep-002/index.json",
    "sha256": "2dbcb8b744677ecd01506447cd86c742b70472a1e4c3c2e867813835f1abebf0",
    "bytes": 7297
  },
  "source_peer": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-source-peer-002/review.json",
    "sha256": "38140b44382931e1554443a240b1c886e9cc74e2f0d2918eea2d5b59c91b8003",
    "bytes": 5080
  },
  "source_findings": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-source-peer-002/findings.json",
    "sha256": "75dc7b38f01bad3cc63576b99a699d24963dfcdb2873eac7dd4645825d50d0b3",
    "bytes": 2055
  },
  "source_bindings": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-source-peer-002/bindings.json",
    "sha256": "6eb138364cae041dc96ab01fff288b5abdd26751262674de38bcfb2e1de4f1ca",
    "bytes": 19790
  },
  "root_guard_source_grant": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-root-source-review-002/review.json",
    "sha256": "2b998f3bc1a895e9035a890ab1f67cb99872b77a647952239b220c80d7554b46",
    "bytes": 3455
  },
  "F1_source_decision": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-root-source-decision-001/decision.json",
    "sha256": "f3800b137892918d7532ed07267664f9043541e3082b739c66df04b57d84e7bf",
    "bytes": 2944
  },
  "original_F1_findings": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-source-peer-001/findings.json",
    "sha256": "3630255f9c2d786d11bb66663860407dcfc247a135efaa89d2d81c015d5606c9",
    "bytes": 3048
  },
  "fixture": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-f1-guards-prep-001/test_final_evidence_guards.py",
    "sha256": "1a81cdcd45aee1aeb917478763c9169b6be5e858c5b41b9226574ae0c70ed5fb",
    "bytes": 14566
  },
  "fixture_bindings_json": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-f1-guards-prep-001/bindings.json",
    "sha256": "3f1e80dda286909dd4c9482bfd1ceb47ab023bb8fff87eb352ff5e9d4e079374",
    "bytes": 12195
  },
  "fixture_METHOD_md": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-f1-guards-prep-001/METHOD.md",
    "sha256": "1ce871393d929c38776f4eb9106885b50264084b61034babed7661dfa89a7c03",
    "bytes": 5499
  },
  "fixture_index_json": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-f1-guards-prep-001/index.json",
    "sha256": "42448c88fc7b60166250bf5525c6713dc5d496914e110a8d0c3fe876ba44a87f",
    "bytes": 2508
  },
  "fixture_root_review": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-f1-guards-root-source-review-001/review.json",
    "sha256": "8efb54f578bc8d08a1eebedc90de083e0c4642207800229ca95eb5877f093954",
    "bytes": 2038
  },
  "fixture_peer_0": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-f1-guards-source-peer-001/review.json",
    "sha256": "0b98fd3173a016db569a15c41eaa7a044b2c950d066143ea703d60efe4d23100",
    "bytes": 5871
  },
  "fixture_peer_1": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-f1-guards-source-peer-001/findings.json",
    "sha256": "d46e3debe179a47d7a0b7c55855af019f511a553b75051ae0a990d4d9040c490",
    "bytes": 773
  },
  "fixture_peer_2": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-f1-guards-source-peer-001/bindings.json",
    "sha256": "05496115fee2eca30f0d518eae10827b2c309e5b36d59bc734dafac4e0d05fc9",
    "bytes": 7048
  }
}

CONTROLS=dict(normal_seconds=40,TERM_absolute_seconds=48,KILL_reap_absolute_seconds=56,whole_seconds=60,
    TERM_grace_seconds=8,KILL_reap_grace_seconds=8,total_inclusive_bytes=33554432,thread_environment=1,retries=0,RSS_sampler=False)
RUNTIME_SELECTION=dict(path='work/962-engineering/head-star-current24-qfnra-five-toy-owner-f1-guard-runtime-selection-root-001/runtime-identity.json',sha256='ec373001917f5fb80fae1c507186e0505f3ba699abc550ea31585c6c8c144269',bytes=1624)
DIRECT_ROLES=('controller','wrapper','control_preparation_index','fixture_source_peer','fixture_source_bindings',
    'root_fixture_source_review','exact_control_peer','exact_control_bindings','root_control_review','runtime_selection')
METHODS=('test_01_complete_normal_control','test_02_final_stdout_rec_failure','test_03_final_stderr_rec_failure',
    'test_04_final_adapter_report_rec_failure','test_05_final_helper_report_rec_failure',
    'test_06_missing_final_stdout_descriptor','test_07_missing_final_stderr_descriptor',
    'test_08_missing_final_adapter_descriptor','test_09_missing_final_helper_descriptor')
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
    prefix=''.join(name+' (__main__.FinalEvidenceF1Guards.'+name+') ... ok\n' for name in METHODS)
    need(text.startswith(prefix),'Exact ordered nine method rows required')
    need(re.fullmatch(r'\n-{70}\nRan 9 tests in [0-9]+(?:\.[0-9]+)?s\n\nOK\n',text[len(prefix):]) is not None,'Complete Ran9/finalOK diagnostics required')
    return dict(methods=list(METHODS),method_count=9,all_nine_completed=True,F1_synthetic_only=True)


def admit():
    need(len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1]),'HELD: sole external root-admission digest required')
    A=D/'admission.json';ap=rec(A)
    need(ap['sha256']==sys.argv[1] and ap['bytes']<=CAP,'Changed/oversize root admission')
    auth=json.loads(A.read_bytes())
    need(auth['schema']=='962-five-toy-F1-nine-guard-root-admission/v1' and auth['root_issued'] is True and auth['guard_execution_authorized'] is True,'No guard authority')
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
    need(set(packet['files'])=={'run_guards_once.py','stopped_exec_wrapper.py','METHOD.md','source-reuse.json','source.diff'} and packet['file_count_including_this_index']==6,'Fixed six-file control source packet required')
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
    report=dict(schema='962-five-toy-F1-nine-guard-owner-result/v1',status='INCOMPLETE',admission=ap,before=before,after=None,
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
        report['status']='COMPLETE_NINE_F1_SYNTHETIC_GUARDS_CANDIDATE_ONLY' if report['complete_candidate'] else 'INCOMPLETE'
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

