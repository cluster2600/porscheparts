"""HELD/UNRUN finite freshness owner; separate external root admission required."""
import time
started=time.monotonic();controller_stop_requests=[]
import hashlib,json,os,re,select,signal,subprocess,sys,traceback
from pathlib import Path

R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E=R/'work/962-engineering'
X=E/'cp1-oneway-cooling-release-richardson2-observer004-native003-freshness-operation-controls-prep-002'
C=E/'cp1-oneway-cooling-release-richardson2-observer004-native003-freshness-operation-root-execution-002'
H=E/'cp1-oneway-cooling-release-richardson2-observer004-native003-freshness-root-execution-001'
O=E/'cp1-oneway-cooling-release-richardson2-observer004-native-measurement-003'
N=E/'cp1-oneway-cooling-release-richardson2-observer004-native-measurement-root-execution-003'
STAGE_H=E/'cp1-oneway-cooling-release-richardson2-observer004-native003-four-input-staging-root-execution-001'
OP='freshness'
HELPER_REPORT='fresh-preflight.json'
CAP=33554432


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


def inclusive_bytes(records):
    files={}
    for root in [C,H,O]+([STAGE_H] if OP=='freshness' else []):
        if not root.exists():continue
        need(root.is_dir() and not root.is_symlink(),'Changed owned directory')
        for p in root.rglob('*'):
            need(not p.is_symlink(),'Unexpected owned symlink')
            if p.is_file():files[str(p)]=p.stat().st_size
    for pin in records.values():
        p=Path(pin['path']);p=p if p.is_absolute() else R/p
        files[str(p)]=p.stat().st_size
    return sum(files.values())


def event_record(event):
    return dict(ident=event.ident,filter=event.filter,flags=event.flags,fflags=event.fflags,data=event.data,udata=event.udata)


def normal_helper_receipt(actual):
    path=H/HELPER_REPORT;need(path.is_file() and not path.is_symlink() and path.stat().st_size<=CAP,'Complete fixed helper receipt required')
    value=json.loads(path.read_bytes())
    if OP=='stage':
        need(value['schema']=='962-observer004-native-measurement-four-input-staging/v1' and value['all_four_copies_byte_exact'] is True and value['no_execution'] is True and value['staged_inputs']==actual['expected_staged_inputs'] and value['error'] is None,'Pure four-input stage refused')
    else:
        q=value['query']
        need(value['schema']=='962-observer004-native003-fresh-preflight/v1' and value['status']=='COMPLETE_METADATA_ONLY' and value['all_declared_identities_unchanged'] is True and value['error'] is None,'Finite freshness refused')
        need(type(q['attempts']) is int and q['attempts']==1 and q['returncode']==0 and q['reaped'] is True and q['error'] is None and q.get('validation_error') is None and q['stop_actions']==[] and q['elapsed_through_cleanup']<=5,'One complete bounded metadata query required')
    need(value['authorization']==rec(H/'authorization.json'),'Helper authorization association changed')
    return value,rec(path)


def main():
    need(len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1]),'HELD: exact separate root admission digest required')
    A=C/'admission.json';need(rec(A)['sha256']==sys.argv[1],'Changed external root admission')
    auth=json.loads(A.read_text());actual_path=X/'held-actual.json';actual=json.loads(actual_path.read_text())
    need(auth['schema']=='962-native003-finite-operation-owner-admission/v1' and auth['operation']==actual['operation']==OP and auth['operation_once_authorized'] is True,'No operation authority')
    need(type(auth['invocations']) is int and auth['invocations']==1 and auth['automatic_retry'] is False and auth['controls']==actual['controls'],'One exact bounded operation required')
    need(auth['independent_control_peer_complete'] is True and auth['root_control_review_complete'] is True,'Pending exact operation controls')
    need(all(auth[k] is False for k in ['native_execution_authorized','fixture_execution_authorized','field_parsing_authorized','manufacturing_authorized']),'No scientific/native authority')
    need(auth['metadata_query_authorized'] is (OP=='freshness'),'Only the separate freshness operation may query selected metadata')
    need(auth['controller']==rec(Path(__file__))==actual['controller'] and auth['actual']==rec(actual_path) and auth['wrapper']==actual['wrapper'],'Changed owner/actual/wrapper')
    need(actual['status']=='HELD_UNRUN_SOURCE_ONLY' and actual['operation_authorized'] is False and actual['native_execution_authorized'] is False,'Immutable held operation required')
    need(actual['controls']==dict(whole_seconds=60,helper_monitor_stop_seconds=40,TERM_grace_seconds=8,stream_buffer_bytes=1048576,query_seconds=5,total_inclusive_bytes=33554432,thread_environment=1,retries=0),'Fixed operation controls')
    py=actual['selected_python']
    expected_environment=dict(PATH='/usr/bin:/bin',LANG='C',LC_ALL='C',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1',FI_PROVIDER='tcp')
    need(actual['environment']==expected_environment and all(os.environ.get(k)==v for k,v in expected_environment.items()),'Explicit selected thread-one environment required; no environment dump')
    need(str(Path(sys.executable).resolve(strict=True))==py['resolved_path'] and sys.version_info[:3]==(3,12,11),'Selected original3.12 owner required')
    need(sys.flags.isolated==sys.flags.dont_write_bytecode==sys.flags.no_site==1 and sys.flags.optimize==0 and 'site' not in sys.modules and '_distutils_hack' not in sys.modules,'Exact -B-I-S startup required')
    required=['kqueue','kevent','KQ_FILTER_PROC','KQ_NOTE_EXIT','KQ_EV_ADD','KQ_EV_ENABLE','KQ_EV_ONESHOT','KQ_EV_ERROR']
    need(all(hasattr(select,k) for k in required) and all(hasattr(os,k) for k in ['WUNTRACED','WNOHANG','WIFSTOPPED','WSTOPSIG','WIFEXITED','WIFSIGNALED','waitstatus_to_exitcode','getpgid','getsid','killpg','waitpid']),'Named supported APIs unavailable; no child launched')
    need(set(p.name for p in C.iterdir())=={'admission.json'} and set(p.name for p in H.iterdir())=={'authorization.json'} and not N.exists(),'Fresh distinct owner/helper roots and no native root required')
    if OP=='stage':need(not O.exists(),'No prior staged directory/retry')
    else:need(auth['stage_accepted_by_root'] is True,'Separate accepted stage required')
    records=dict(actual['protected_records']);records.update(actual=auth['actual'],controller=auth['controller'],wrapper=auth['wrapper'],owner_admission=rec(A),helper_authorization=auth['helper_authorization'])
    for key in ['exact_control_peer','exact_control_bindings','root_control_review','control_preparation_index']:records[key]=auth[key]
    need(selected(auth['control_preparation_index'])==X/'index.json','Fixed operation control index required')
    if OP=='freshness':
        records['accepted_stage_receipt']=auth['accepted_stage_receipt'];records['stage_root_acceptance']=auth['stage_root_acceptance']
        need(auth['accepted_stage_receipt']['path']==actual['expected_stage_receipt_path'],'Fixed accepted staging receipt path required')
    need(selected(auth['helper_authorization'])==H/'authorization.json','Fixed helper authorization path required')
    helper_auth=json.loads((H/'authorization.json').read_text())
    need(helper_auth['operation']==OP and helper_auth['helper']==actual['helper'] and helper_auth['plan']==actual['helper_plan'] and helper_auth['helper_source_peer']==actual['helper_source_peer'] and helper_auth['helper_source_bindings']==actual['helper_source_bindings'] and helper_auth['helper_root_review']==actual['helper_root_review'] and helper_auth['helper_preparation_index']==actual['helper_preparation_index'],'Helper authorization roles must equal held controls')
    if OP=='freshness':need(helper_auth['staging_receipt']==auth['accepted_stage_receipt'],'Exact accepted staging receipt must reach unchanged helper')
    before=identities(records,py);need(inclusive_bytes(records)<=CAP and time.monotonic()-started<40,'Preflight budget insufficient; no child launched')
    report=dict(schema='962-native003-finite-operation-owner-result/v1',operation=OP,actual=auth['actual'],admission=rec(A),before=before,after=None,process_started=False,PID=None,ownership_certificate=None,reaped=False,raw_returncode=None,events=[],stop_actions=[],failure=None,cleanup_errors=[],helper_receipt=None,helper_receipt_positive=False,group_absent=None,source_API_assumptions=dict(kqueue_module_file=getattr(select,'__file__',None),kqueue_origin=getattr(getattr(select,'__spec__',None),'origin',None),origin_body_pinned=False),sampled_RSS_bytes=None,RSS_scope='No RSS sampler or hard quota; no RSS pass is claimed.',native_executed=False,fixture_executed=False,physical_acceptance=False,automatic_retry=False)
    proc=None;kq=None;certificate=None;continued=False;exited=False;reaped=False;raw_returncode=None;positive=False
    old_TERM=signal.signal(signal.SIGTERM,record_controller_stop);old_INT=signal.signal(signal.SIGINT,record_controller_stop)
    old_CHLD=signal.signal(signal.SIGCHLD,signal.SIG_DFL);report['prior_SIGCHLD_disposition']=repr(old_CHLD)
    try:
        kq=select.kqueue()
        argv=[py['path'],'-B','-I','-S',str(R/actual['wrapper']['path']),auth['helper_authorization']['sha256']]
        need(argv[:-1]==actual['argv_prefix'] and argv==auth['argv'] and actual['cwd']==str(H),'Fixed same-PID wrapper route and sole late helper digest required')
        with (C/'helper.stdout').open('xb') as out,(C/'helper.stderr').open('xb') as err:
            need(not controller_stop_requests and time.monotonic()-started<40,'Stopped before launch')
            proc=subprocess.Popen(argv,cwd=H,env=actual['environment'],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
            report['process_started']=True;report['PID']=proc.pid
            handshake_deadline=min(started+40,time.monotonic()+5)
            while True:
                need(not controller_stop_requests and time.monotonic()<handshake_deadline,'Stopped/deadline before certified wrapper stop')
                pid,status=os.waitpid(proc.pid,os.WUNTRACED|os.WNOHANG)
                if pid:
                    need(pid==proc.pid,'Wrong direct-child status')
                    report['wrapper_wait_status']=status
                    if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                        reaped=True;raw_returncode=os.waitstatus_to_exitcode(status);proc.returncode=raw_returncode;raise ValueError('Wrapper terminated before certified stop')
                    need(os.WIFSTOPPED(status) and os.WSTOPSIG(status)==signal.SIGSTOP,'Exact stopped-before-exec handshake required');break
                time.sleep(.01)
            certificate=dict(PID=proc.pid,PGID=os.getpgid(proc.pid),SID=os.getsid(proc.pid),direct_child_unreaped=True,wait_status=report['wrapper_wait_status'])
            need(certificate['PID']==certificate['PGID']==certificate['SID'],'Changed new-session ownership')
            report['ownership_certificate']=certificate
            watch=select.kevent(proc.pid,filter=select.KQ_FILTER_PROC,flags=select.KQ_EV_ADD|select.KQ_EV_ENABLE|select.KQ_EV_ONESHOT,fflags=select.KQ_NOTE_EXIT)
            events=kq.control([watch],1,0);report['events'].extend(event_record(ev) for ev in events)
            need(not events,'Unexpected registration error/exit before continuation')
            need(not controller_stop_requests and time.monotonic()-started<40,'Stopped before exact exec')
            os.kill(proc.pid,signal.SIGCONT);continued=True
            while not exited:
                need(not controller_stop_requests and time.monotonic()-started<40,'Stop/deadline; reserve cleanup within whole60s')
                need(inclusive_bytes(records)<=CAP,'Complete inclusive32MiB cap')
                events=kq.control(None,1,.05)
                for ev in events:
                    report['events'].append(event_record(ev))
                    need(ev.ident==proc.pid and ev.filter==select.KQ_FILTER_PROC and not ev.flags&select.KQ_EV_ERROR and ev.fflags&select.KQ_NOTE_EXIT,'Unexpected kernel event')
                    exited=True
            value,report['helper_receipt']=normal_helper_receipt(actual);positive=True;report['helper_receipt_positive']=True
            deadline=started+58
            while True:
                need(not controller_stop_requests and time.monotonic()<deadline,'Stopped/deadline before exact terminal reap')
                pid,status=os.waitpid(proc.pid,os.WNOHANG)
                if pid:
                    need(pid==proc.pid and (os.WIFEXITED(status) or os.WIFSIGNALED(status)),'Wrong explicit final terminal reap');reaped=True;break
                time.sleep(.01)
            raw_returncode=os.waitstatus_to_exitcode(status);proc.returncode=raw_returncode
            need(raw_returncode==0,'Helper raw nonzero after positive prefinal receipt')
        need(not group_exists(proc.pid),'Owned group remains after final reap');report['group_absent']=True
        need((C/'helper.stdout').read_bytes()==b'' and (C/'helper.stderr').read_bytes()==b'','Unexpected wrapper/helper stream content; preserve and refuse')
        need(not controller_stop_requests,'Controller stopped during closure')
    except BaseException:report['failure']=traceback.format_exc()
    finally:
        if proc is not None and not reaped:
            try:
                if certificate is not None and continued:
                    need(certificate['PID']==certificate['PGID']==certificate['SID']==proc.pid and proc.returncode is None,'No retained ownership anchor for group signal')
                    for sig in [signal.SIGTERM,signal.SIGKILL]:
                        try:os.killpg(proc.pid,sig);report['stop_actions'].append(dict(scope='certified unreaped group',signal=int(sig)))
                        except BaseException:report['cleanup_errors'].append(traceback.format_exc())
                        if sig==signal.SIGTERM:
                            deadline=min(started+56,time.monotonic()+8)
                            while time.monotonic()<deadline:time.sleep(min(.05,max(0,deadline-time.monotonic())))
                else:
                    try:os.kill(proc.pid,signal.SIGKILL);report['stop_actions'].append(dict(scope='own unreaped direct child before helper continuation',signal=int(signal.SIGKILL)))
                    except BaseException:report['cleanup_errors'].append(traceback.format_exc())
                deadline=started+58
                while time.monotonic()<deadline:
                    pid,status=os.waitpid(proc.pid,os.WNOHANG)
                    if pid==proc.pid:
                        reaped=True;raw_returncode=os.waitstatus_to_exitcode(status);proc.returncode=raw_returncode;break
                    time.sleep(.01)
                need(reaped,'Owned child not reaped within reserved closure time')
            except BaseException:report['cleanup_errors'].append(traceback.format_exc())
        if proc is not None and reaped:
            try:report['group_absent']=not group_exists(proc.pid)
            except BaseException:report['group_absent']=None;report['cleanup_errors'].append(traceback.format_exc())
        if kq is not None:
            try:kq.close()
            except BaseException:report['cleanup_errors'].append(traceback.format_exc())
        report.update(reaped=reaped,raw_returncode=raw_returncode)
        try:report['after']=identities(records,py)
        except BaseException:report['identity_after_error']=traceback.format_exc()
        report['all_controls_unchanged']=report['after']==before
        report['final_streams_complete']=bool(reaped and report['group_absent'] is True)
        report['owned_streams']={name:rec(C/name) for name in ['helper.stdout','helper.stderr'] if (C/name).is_file()}
        report['elapsed_before_receipt']=time.monotonic()-started
        try:signal.signal(signal.SIGCHLD,old_CHLD);signal.signal(signal.SIGINT,old_INT);signal.signal(signal.SIGTERM,old_TERM)
        except BaseException:report['cleanup_errors'].append(traceback.format_exc())
        report['handler_cutoff_elapsed_seconds']=time.monotonic()-started
        report['handled_stop_requests']=list(controller_stop_requests)
        report['handled_stop_refusal_reason']='Controller stop request handled before recorded handler cutoff' if controller_stop_requests else None
        report['complete_candidate']=bool(positive and reaped and raw_returncode==0 and report['group_absent'] is True and report['failure'] is None and not report['cleanup_errors'] and report['all_controls_unchanged'] and not controller_stop_requests)
        report['whole_startup_return_external_clock_raw_outer0_and_final_inclusive_census_required']=True
        encoded=(json.dumps(report,indent=2,allow_nan=False)+'\n').encode()
        need(inclusive_bytes(records)+len(encoded)<=CAP,'Full owner receipt exceeds inclusive32MiB; retain existing evidence without truncation')
        with (C/'closed-result.json').open('xb') as f:f.write(encoded)
    if not report['complete_candidate'] or controller_stop_requests or inclusive_bytes(records)>CAP or time.monotonic()-started>=60:
        print('Final operation refusal; prefinal receipt is not acceptance.',file=sys.stderr,flush=True);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
