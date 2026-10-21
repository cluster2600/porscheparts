"""HELD source only: one retained-leader five-toy owner; no actual/admission."""
import time
started=time.monotonic();controller_stop_requests=[]
import hashlib,json,os,re,resource,select,signal,subprocess,sys,traceback
from pathlib import Path

R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E=R/'work/962-engineering'
P=E/'head-star-current24-qfnra-five-toy-owner-prep-004'
D=E/'head-star-current24-qfnra-five-toy-root-execution-001'
PY='/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10'
CAP=33554432
RSS_CAP=2147483648
IDS=('rational','algebraic','maxfinite','negative_half_minsubnormal','unsat')
ENV=dict(PATH='/usr/bin:/bin',LANG='C',LC_ALL='C',PYTHONDONTWRITEBYTECODE='1',
         OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
         VECLIB_MAXIMUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
CONTROLS=dict(normal_seconds=40,TERM_absolute_seconds=48,KILL_reap_absolute_seconds=56,
              whole_seconds=60,TERM_grace_seconds=8,KILL_grace_seconds=8,
              RSS_query_seconds=5,sampled_RSS_bytes=RSS_CAP,inclusive_bytes=CAP,
              thread_environment=1,retries=0)
CHOICE_SHA='a96c130fd8044ebe55d7a8c3e2cab0067e2f60d77b58cd8a33b1b4427eb7f9c5'
# Retain even an unreaped refusal through explicit last-resort os._exit; no destructor poll.
HELD_LEADERS=[]


class _RetainedPopen(subprocess.Popen):
    # Source policy only; base construction/active-list effects remain unproved.
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


def provider_links(paths):
 return {name:dict(is_symlink=Path(name).is_symlink(),raw_target=os.readlink(name) if Path(name).is_symlink() else None,resolved=str(Path(name).resolve(strict=True))) for name in paths}


def limits():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(CAP,CAP))


def left(ceiling):
    return started+ceiling-time.monotonic()


def gate(ceiling,message):
    need(not controller_stop_requests and left(ceiling)>0,message)


def inclusive_bytes(records):
    files={}
    if D.exists():
        need(D.is_dir() and not D.is_symlink(),'Changed output root')
        for p in D.rglob('*'):
            need(not p.is_symlink(),'Unexpected owned symlink')
            if p.is_file():files[str(p)]=p.stat().st_size
    # Count every first-party relative control/source pin. Installed absolute
    # runtime bodies are identity evidence, not artifacts or copied outputs.
    for pin in records.values():
        if not Path(pin['path']).is_absolute():
            p=R/pin['path'];files[str(p)]=p.stat().st_size
    return sum(files.values())


def sample(pgid):
    """Adapted donor RSS parser, one ps call only; no thread subprocess."""
    query_started=time.monotonic()
    remaining=left(40);need(remaining>0,'No normal time remains for RSS')
    timeout=min(5,remaining)
    env={'PATH':'/usr/bin:/bin','LC_ALL':'C'}
    value=dict(argv=['/bin/ps','-axo','pid=,pgid=,rss=,stat='],timeout_seconds=timeout,
        returncode=None,stdout=None,stderr=None,RSS_bytes=None,processes=None,
        raw_owned_rows=[],threads=None,thread_observation=None,zombie_pids=[],
        live_pids=None,error=None,late=False)
    try:
        ps=subprocess.run(['/bin/ps','-axo','pid=,pgid=,rss=,stat='],capture_output=True,text=True,env=env,timeout=timeout)
        value.update(returncode=ps.returncode,stdout=ps.stdout,stderr=ps.stderr)
        if ps.returncode:raise ValueError('RSS ps failed: '+ps.stderr)
        live={};zombies=[];owned_rows=[]
        for row in ps.stdout.splitlines():
            x=row.split()
            if len(x)>=2 and (x[1]==str(pgid) or x[0]==str(pgid)):
                if len(x)!=4 or not all(v.isdigit() for v in x[:3]):
                    raise ValueError('Missing/nonnumeric owned RSS data: '+repr(row))
                if int(x[1])!=pgid:raise ValueError('Direct wrapper PGID changed: '+repr(row))
                rss=int(x[2])*1024
                owned_rows.append(dict(raw=row,pid=int(x[0]),pgid=int(x[1]),reported_RSS_KiB=int(x[2]),RSS_bytes=rss,state=x[3]))
                value['raw_owned_rows']=owned_rows
                if x[3].startswith('Z'):zombies.append(int(x[0]))
                else:live[int(x[0])]=rss
        if not owned_rows:raise ValueError('No owned resource rows observed')
        value.update(RSS_bytes=sum(row['RSS_bytes'] for row in owned_rows),
                     processes=len(owned_rows),zombie_pids=zombies,live_pids=sorted(live))
    except BaseException as exc:
        value['error']=traceback.format_exc()
        if isinstance(exc,subprocess.TimeoutExpired):
            # TimeoutExpired may supply bytes even for text=True. Preserve exact
            # available bytes without inventing EOF or a successful sample.
            value['timeout_stdout_hex']=(exc.output.encode() if isinstance(exc.output,str) else exc.output).hex() if exc.output is not None else None
            value['timeout_stderr_hex']=(exc.stderr.encode() if isinstance(exc.stderr,str) else exc.stderr).hex() if exc.stderr is not None else None
    value['elapsed_through_parse']=time.monotonic()-query_started
    value['late']=left(40)<=0 or value['elapsed_through_parse']>timeout
    return value


def exit_events(kq,pid,report,timeout):
    events=kq.control(None,1,timeout)
    report['events'].extend(event_record(ev) for ev in events)
    for ev in events:
        need(ev.ident==pid and ev.filter==select.KQ_FILTER_PROC and not ev.flags&select.KQ_EV_ERROR and ev.fflags&select.KQ_NOTE_EXIT,'Unknown/error ownership event')
    return bool(events)


def add_pin(records,pin):
    key=pin['path']
    if key in records:need(records[key]==pin,'Conflicting same-path pin')
    records[key]=pin


def admit():
    need(len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1]),'HELD: separate admission digest required')
    A=D/'admission.json';need(rec(A)['sha256']==sys.argv[1],'Changed admission')
    auth=json.loads(A.read_text());actual_path=P/'actual-contract.json';actual=json.loads(actual_path.read_text())
    need(auth['schema']=='962-five-toy-owner-root-admission/v1' and actual['schema']=='962-five-toy-owner-held-actual/v1','Exact future source contract required')
    need(auth['five_toy_execution_authorized'] is True and type(auth['invocations']) is int and auth['invocations']==1 and auth['automatic_retry'] is False,'Exactly one five-toy call required')
    need(actual['status']=='HELD_UNRUN' and actual['execution_authorized'] is False,'Immutable held actual required')
    need(actual['automatic_retry'] is False and actual['toy_IDs']==list(IDS),'Fixed five original IDs/no retry required')
    need(all(auth[k] is True for k in ['source_review_complete','fake_guard_acceptance_complete','selected_runtime_and_API_acceptance_complete','exact_child_review_complete']),'Pending source/guard/runtime/exact-child gates')
    need(all(auth[k] is False for k in ['real_head_input_authorized','real_head_model_or_word_authorized','native_execution_authorized','field_parsing_authorized','geometry_write_authorized','physical_acceptance','manufacturing_authorized']),'Five synthetic toys only')
    need(all(actual[k] is False for k in ['real_head_input_authorized','real_head_model_or_word_authorized','native_execution_authorized','field_parsing_authorized','geometry_write_authorized','physical_acceptance','manufacturing_authorized']),'Held actual contains no engineering authority')
    need(auth['actual']==rec(actual_path) and auth['controller']==actual['controller']==rec(Path(__file__)),'Changed actual/controller')
    need(auth['adapter']==actual['adapter'] and auth['wrapper']==actual['wrapper'],'Changed entry sources')
    need(auth['controls']==actual['controls']==CONTROLS,'Fixed40/48/56/60 resources required')
    need(actual['environment']==ENV and all(os.environ.get(k)==v for k,v in ENV.items()),'Fixed requested thread-one environment; no environment dump')
    py=actual['selected_python']
    need(py['path']==PY and py['sha256']=='72956ad35cff7691dfed9e04c9593de825ffd5b2fa7e8bc9ae96ce9a1af65621' and py['bytes']==152624,'Historical3.10 selection changed')
    need(sys.version_info[:3]==(3,10,11) and str(Path(sys.executable).resolve(strict=True))==py['resolved_path'],'Selected3.10.11 owner required')
    need(sys.flags.isolated==sys.flags.no_site==sys.flags.dont_write_bytecode==1 and sys.flags.optimize==0 and 'site' not in sys.modules and '_distutils_hack' not in sys.modules,'Exact-B-I-S startup required')
    need(signal.getsignal(signal.SIGCHLD)==signal.SIG_DFL,'SIGCHLD must already be default; no changed disposition or competing waiter permitted')
    required=['kqueue','kevent','KQ_FILTER_PROC','KQ_NOTE_EXIT','KQ_EV_ADD','KQ_EV_ENABLE','KQ_EV_ONESHOT','KQ_EV_ERROR']
    need(all(hasattr(select,k) for k in required) and all(hasattr(os,k) for k in ['WUNTRACED','WNOHANG','WIFSTOPPED','WSTOPSIG','WIFEXITED','WIFSIGNALED','waitstatus_to_exitcode','getpgid','getsid','killpg','waitpid']),'Named APIs unavailable')
    need(actual['transport']['sha256']=='76c13fe57d9598276b349e12dedd8bdfb1eff1ec3ad29d4c95a073abc8e6d49a' and actual['transport']['bytes']==21489,'Frozen transport required')
    need(actual['protocol']['sha256']=='9b5885a35bfbc681c0354e937b9f57621b3d8137adc25b4e2ba455e86ce59785' and actual['protocol']['bytes']==12459,'Frozen protocol required')
    need(actual['root_source_choice']['sha256']==CHOICE_SHA,'Changed root source choice')
    need(actual['historical_runtime_preflight']['sha256']=='3b4f731ff16ec475b5de2d567292b25169a7c9c8618d38c1c8cd363d4f8c9169' and actual['historical_runtime_preflight']['bytes']==78434,'Unchanged historical no-site metadata required')
    historical=json.loads(selected(actual['historical_runtime_preflight']).read_text())
    need(len(historical['runtime_files'])==91 and historical['selected_provider']['sha256']=='e5cc7bf02c9c26f5d63e7528659129183167d3f39fa6fb85853a62fe7990eaf3','Complete saved91/provider expectations required')
    need(type(actual['protected_record_count']) is int and len(actual['protected_records'])==actual['protected_record_count'],'Complete finite protected count required')
    records={}
    for pin in actual['protected_records'].values():add_pin(records,pin)
    for pin in [rec(A),auth['actual'],actual['controller'],actual['adapter'],actual['wrapper'],actual['transport'],actual['protocol'],actual['source_index'],actual['root_source_choice'],actual['historical_runtime_preflight']]:add_pin(records,pin)
    for pin in historical['runtime_files'].values():add_pin(records,pin)
    provider=historical['selected_provider']
    need(provider['path'] in actual['expected_aliases'],'Selected historical provider route must be explicit')
    add_pin(records,dict(path=actual['expected_aliases'][provider['path']]['resolved'],sha256=provider['sha256'],bytes=provider['bytes']))
    need(actual['Z3_body']['path']=='/opt/homebrew/Cellar/z3/5.1.0/bin/z3' and actual['Z3_body']['sha256']=='b9a2c3a7dc833da652955116ad743cc733aa7938dbe64f528f71cb09066e2512' and actual['Z3_body']['bytes']==16244496,'Pinned Z3 body changed; no discovery or fallback')
    add_pin(records,actual['Z3_body'])
    for key in ['source_peer','source_bindings','fake_guard_acceptance','runtime_selection','root_control_review','exact_child_peer','exact_child_bindings']:
        add_pin(records,auth[key])
    need(type(actual['canonical_pin_count']) is int and len(records)==actual['canonical_pin_count'],'Exact canonical closure required')
    need('/opt/homebrew/bin/z3' in actual['expected_aliases'] and PY in actual['expected_aliases'],'Finite selected routes required')
    need(actual['expected_aliases']['/opt/homebrew/bin/z3']['resolved']==actual['Z3_body']['path'],'Declared Z3 alias/body join required')
    aliases=provider_links(actual['expected_aliases']);need(aliases==actual['expected_aliases'],'Changed selected alias/provider routes')
    before=identities(records,py)
    runtime=json.loads(selected(auth['runtime_selection']).read_text())
    need(runtime['schema']=='962-five-toy-selected-runtime-acceptance/v1' and runtime['root_accepted'] is True and runtime['Python_version_info']==[3,10,11] and runtime['selected_python']==py and runtime['kqueue_ownership_API_accepted'] is True and runtime['Z3_current_identity_accepted'] is True and runtime['no_competing_waiter_attested'] is True,'Separately accepted current finite runtime/API evidence required')
    need(D.is_dir() and not D.is_symlink() and set(x.name for x in D.iterdir())=={'admission.json'},'Fresh admission-only output root required')
    need(inclusive_bytes(records)<=CAP,'Preflight inclusive cap exceeded')
    gate(40,'Preflight exhausted normal reservation')
    argv=[PY,'-B','-I','-S',str(R/actual['wrapper']['path']),rec(A)['sha256']]
    need(auth['argv_prefix']==argv[:-1],'Fixed single stopped-wrapper argv required')
    return auth,actual,records,before,aliases,argv


def normal_reports(actual,report):
    gate(40,'Late normal report capture')
    ap=D/'adapter-report.json';hp=D/'toys/report.json'
    need(ap.is_file() and hp.is_file() and not ap.is_symlink() and not hp.is_symlink(),'Missing complete helper evidence is unknown/refusal')
    need(ap.stat().st_size<=CAP and hp.stat().st_size<=CAP,'Report exceeds cap')
    adapter=json.loads(ap.read_bytes());helper=json.loads(hp.read_bytes())
    report['adapter_report']=rec(ap);report['helper_report']=rec(hp)
    need(adapter['schema']=='962-five-toy-fixed-adapter-result/v1' and adapter['status']=='COMPLETE_TOY_ADAPTER_ONLY' and adapter['transport_calls']==1 and adapter['transport_returned'] is True and adapter['traceback'] is None and adapter['all_controls_unchanged'] is True and adapter['returned_report_agrees_with_saved'] is True,'Fixed adapter refused')
    need(adapter['helper_report']==report['helper_report'] and adapter['owned_group']==report['PID'] and adapter['helper_complete'] is True and adapter['helper_failure'] is None,'Helper/owner association changed')
    need(helper['schema']=='962-current24-five-persistent-Z3-toy-check/v1' and helper['complete'] is True and helper['failure'] is None and helper['unattempted_session_IDs']==[] and helper['unattempted_session_count']==0,'Incomplete fixed toy family')
    need([r['ID'] for r in helper['results']]==list(IDS),'All five original toy IDs in order required')
    need(all(r['status']=='COMPLETE_TOY_ONLY' and type(r['check_count']) is int and r['check_count']==1 and r['solver_returncode']==0 and r['direct_child_reaped'] is True and r['cleanup']==[] and r['stderr_bytes']==0 for r in helper['results']),'Every solver session must close once without error')
    need(helper['real_head_input_or_model_used'] is False and helper['head_word_or_quality_accepted'] is False and helper['native_retry_or_geometry_application_authorized'] is False and helper['physical_or_manufacturing_accepted'] is False,'No real engineering acceptance')
    names={'report.json'}|{('toy_'+ID+suffix) for ID in IDS for suffix in ('.stdout','.stderr','.jsonl')}
    need(set(p.name for p in (D/'toys').iterdir())==names,'Complete exact16 helper files required')
    report['capture_files']={}
    for p in sorted((D/'toys').iterdir()):
        need(p.is_file() and not p.is_symlink(),'Unexpected capture entry');report['capture_files'][p.name]=rec(p)
    gate(40,'Late full report/hash capture')


def main():
    report=dict(schema='962-five-toy-retained-owner-result/v1',status='INCOMPLETE',PID=None,ownership_certificate=None,
        process_started=False,events=[],samples=[],sample_error_exit_races=[],valid_live_sample_count=0,
        observed_max_RSS_bytes=None,sampled_RSS_observation_pass=None,observed_threads=None,
        reaped=False,raw_returncode=None,group_absent=None,stop_actions=[],cleanup_errors=[],
        failure=None,adapter_report=None,helper_report=None,capture_files=None,controls_before=None,
        continuation_intent=False,continuation_acknowledged=False,continuation_error=None,
        leader_construction_attempted=False,leader_construction_returned=False,leader_construction_error=None,
        partial_construction_unknown=False,last_resort_partial_construction_exit=False,
        controls_after=None,aliases_before=None,aliases_after=None,handled_stop_requests=None,
        complete_candidate=False,last_resort_unreaped_exit=False,receipt_write_error=None,direct_relationship_unknown=False,
        forced_stop_missing_helper_fields_are_unknown=True,real_head_input_used=False,
        native_execution=False,physical_acceptance=False,automatic_retry=False)
    proc=None;kq=None;certificate=None;continuation_intent=False;reaped=False;raw_returncode=None
    actual=None;records={};before=None;aliases=None;normal=False;old_TERM=None;old_INT=None
    try:
        auth,actual,records,before,aliases,argv=admit()
        report.update(actual=auth['actual'],admission=rec(D/'admission.json'),controls_before=before,aliases_before=aliases)
        old_TERM=signal.signal(signal.SIGTERM,record_controller_stop);old_INT=signal.signal(signal.SIGINT,record_controller_stop)
        need(signal.getsignal(signal.SIGCHLD)==signal.SIG_DFL,'Changed default SIGCHLD before launch')
        limits();kq=select.kqueue()
        with (D/'adapter.stdout').open('xb') as out,(D/'adapter.stderr').open('xb') as err:
            gate(40,'Stopped before wrapper launch')
            report['leader_construction_attempted']=True
            try:
                proc=_RetainedPopen(argv,cwd=D,env=ENV,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
            except BaseException:
                report['leader_construction_error']=traceback.format_exc()
                report['partial_construction_unknown']=True;report['direct_relationship_unknown']=True
                raise
            report['leader_construction_returned']=True
            HELD_LEADERS.append(proc);report.update(process_started=True,PID=proc.pid)
            handshake_until=min(started+40,time.monotonic()+5)
            while True:
                need(not controller_stop_requests and time.monotonic()<handshake_until,'Stopped/late wrapper handshake')
                pid,status=os.waitpid(proc.pid,os.WUNTRACED|os.WNOHANG)
                if pid:
                    need(pid==proc.pid,'Wrong direct-child status')
                    report['wrapper_wait_status']=status
                    if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                        reaped=True;raw_returncode=os.waitstatus_to_exitcode(status);proc.returncode=raw_returncode
                        raise ValueError('Wrapper terminated before certificate')
                    need(os.WIFSTOPPED(status) and os.WSTOPSIG(status)==signal.SIGSTOP,'Exact stopped-before-exec status required')
                    break
                time.sleep(min(.01,max(0,handshake_until-time.monotonic())))
            certificate=dict(PID=proc.pid,PGID=os.getpgid(proc.pid),SID=os.getsid(proc.pid),direct_child_unreaped=True,wait_status=status)
            need(certificate['PID']==certificate['PGID']==certificate['SID'],'Changed stopped ownership identity')
            report['ownership_certificate']=certificate
            watch=select.kevent(proc.pid,filter=select.KQ_FILTER_PROC,flags=select.KQ_EV_ADD|select.KQ_EV_ENABLE|select.KQ_EV_ONESHOT,fflags=select.KQ_NOTE_EXIT)
            events=kq.control([watch],1,0);report['events'].extend(event_record(ev) for ev in events)
            need(not events,'Registration event/error before continuation')
            gate(40,'Stopped before fixed adapter exec')
            continuation_intent=True;report['continuation_intent']=True
            try:
                os.kill(proc.pid,signal.SIGCONT)
                report['continuation_acknowledged']=True
            except BaseException:
                report['continuation_error']=traceback.format_exc()
                raise
            while True:
                gate(40,'Normal40 reservation exhausted')
                if exit_events(kq,proc.pid,report,0):break
                observation=sample(proc.pid);report['samples'].append(observation)
                need(not observation['late'] and left(40)>0,'Late RSS return; reserved cleanup required')
                if observation['error'] is not None:
                    if exit_events(kq,proc.pid,report,0):
                        report['sample_error_exit_races'].append(len(report['samples'])-1);break
                    raise ValueError('Live RSS observation unavailable; full saved sample/error retained')
                need(observation['RSS_bytes'] is not None and observation['RSS_bytes']<=RSS_CAP,'Observed owned-group RSS exceeds2GiB')
                peak=report['observed_max_RSS_bytes']
                report['observed_max_RSS_bytes']=observation['RSS_bytes'] if peak is None else max(peak,observation['RSS_bytes'])
                if observation['live_pids']:report['valid_live_sample_count']+=1
                need(inclusive_bytes(records)<=CAP,'Complete inclusive32MiB cap exceeded')
                if exit_events(kq,proc.pid,report,min(.05,max(0,left(40)))):break
            need(report['valid_live_sample_count']>0,'No valid live RSS observation; unknown is not zero/pass')
            normal_reports(actual,report)
            # All further group-signal intent is ended on this normal path.
            while True:
                gate(56,'Late deliberate exact terminal reap')
                pid,status=os.waitpid(proc.pid,os.WNOHANG)
                if pid:
                    need(pid==proc.pid and (os.WIFEXITED(status) or os.WIFSIGNALED(status)),'Wrong terminal status')
                    reaped=True;raw_returncode=os.waitstatus_to_exitcode(status);proc.returncode=raw_returncode;break
                time.sleep(min(.01,max(0,left(56))))
            need(left(56)>0,'Terminal reap returned beyond56')
            need(raw_returncode==0,'Raw adapter nonzero after prefinal positive report')
        # No raw PGID signal is permitted after the preceding deliberate reap.
        report['group_absent']=not group_exists(proc.pid)
        need(report['group_absent'] is True,'Postreap group survives or is unknown; no recycled-PGID signal')
        need((D/'adapter.stdout').read_bytes()==b'' and (D/'adapter.stderr').read_bytes()==b'','Unexpected adapter streams retained')
        gate(60,'Stopped/late normal closure')
        normal=True
    except BaseException as exc:
        if isinstance(exc,ChildProcessError):report['direct_relationship_unknown']=True
        report['failure']=traceback.format_exc()
    finally:
        if proc is not None and not reaped:
            if proc not in HELD_LEADERS:HELD_LEADERS.append(proc)
            if certificate is not None and continuation_intent:
                try:
                    need(certificate['PID']==certificate['PGID']==certificate['SID']==proc.pid and proc.returncode is None,'Lost unreaped group anchor')
                    need(not report['direct_relationship_unknown'],'Unknown direct-child relation; no numeric group signal')
                    need(left(48)>0,'TERM ceiling already expired')
                    try:os.killpg(proc.pid,signal.SIGTERM);report['stop_actions'].append(dict(scope='certified unreaped group',signal=int(signal.SIGTERM)))
                    except BaseException:report['cleanup_errors'].append(traceback.format_exc())
                    term_until=min(started+48,time.monotonic()+8)
                    while time.monotonic()<term_until:
                        # Exit observation does not reap or release the anchor.
                        try:exit_events(kq,proc.pid,report,min(.05,max(0,term_until-time.monotonic())))
                        except BaseException:report['cleanup_errors'].append(traceback.format_exc());break
                except BaseException:report['cleanup_errors'].append(traceback.format_exc())
                try:
                    need(not report['direct_relationship_unknown'],'Unknown direct-child relation; no numeric group signal')
                    need(left(56)>0,'KILL ceiling already expired')
                    os.killpg(proc.pid,signal.SIGKILL);report['stop_actions'].append(dict(scope='certified unreaped group',signal=int(signal.SIGKILL)))
                except BaseException:report['cleanup_errors'].append(traceback.format_exc())
            else:
                try:
                    need(not report['direct_relationship_unknown'],'Unknown direct-child relation; no numeric PID signal')
                    need(left(56)>0,'Direct-child cleanup ceiling already expired')
                    os.kill(proc.pid,signal.SIGKILL);report['stop_actions'].append(dict(scope='only own unreaped direct PID before certificate/continuation',signal=int(signal.SIGKILL)))
                except BaseException:report['cleanup_errors'].append(traceback.format_exc())
            # Signal errors, including ESRCH, never skip this explicit reap attempt.
            try:
                reap_until=min(started+56,time.monotonic()+8)
                while time.monotonic()<reap_until:
                    pid,status=os.waitpid(proc.pid,os.WNOHANG)
                    if pid:
                        need(pid==proc.pid and (os.WIFEXITED(status) or os.WIFSIGNALED(status)),'Wrong cleanup terminal status')
                        reaped=True;raw_returncode=os.waitstatus_to_exitcode(status);proc.returncode=raw_returncode;break
                    time.sleep(min(.01,max(0,reap_until-time.monotonic())))
                need(reaped and time.monotonic()<reap_until and left(56)>0,'Exact owned-child reap incomplete/late at bounded56 ceiling')
            except BaseException as exc:
                if isinstance(exc,ChildProcessError):report['direct_relationship_unknown']=True
                report['cleanup_errors'].append(traceback.format_exc())
        if proc is not None and reaped:
            try:report['group_absent']=not group_exists(proc.pid)
            except BaseException:report['group_absent']=None;report['cleanup_errors'].append(traceback.format_exc())
        if kq is not None:
            try:kq.close()
            except BaseException:report['cleanup_errors'].append(traceback.format_exc())
        report.update(reaped=reaped,raw_returncode=raw_returncode)
        if before is not None:
            try:
                gate(60,'Late identity closure')
                report['controls_after']=identities(records,actual['selected_python'])
                report['aliases_after']=provider_links(actual['expected_aliases'])
                need(left(60)>0,'Identity/alias closure returned beyond60')
            except BaseException:report['identity_after_error']=traceback.format_exc()
        report['all_controls_unchanged']=before is not None and report['controls_after']==before and report['aliases_after']==aliases
        for name in ['adapter.stdout','adapter.stderr']:
            p=D/name
            if p.is_file():
                try:report.setdefault('owned_streams',{})[name]=rec(p)
                except BaseException:report.setdefault('stream_read_errors',[]).append(traceback.format_exc())
        # No new helper report is invented on TERM/KILL or a missing-output path.
        for key,p in [('available_adapter_report',D/'adapter-report.json'),('available_helper_report',D/'toys/report.json')]:
            try:report[key]=rec(p) if p.is_file() and not p.is_symlink() else None
            except BaseException:report[key]=None;report.setdefault('available_evidence_errors',[]).append(traceback.format_exc())
        try:
            if old_INT is not None:signal.signal(signal.SIGINT,old_INT)
            if old_TERM is not None:signal.signal(signal.SIGTERM,old_TERM)
        except BaseException:report['cleanup_errors'].append(traceback.format_exc())
        report['handler_cutoff_elapsed_seconds']=time.monotonic()-started
        report['handled_stop_requests']=list(controller_stop_requests)
        report['handled_stop_refusal_reason']='Stop handled before recorded handler cutoff' if controller_stop_requests else None
        report['sampled_RSS_observation_pass']=bool(report['valid_live_sample_count']>0 and report['observed_max_RSS_bytes'] is not None and report['observed_max_RSS_bytes']<=RSS_CAP and normal)
        report['last_resort_unreaped_exit']=proc is not None and not reaped
        report['last_resort_partial_construction_exit']=report['partial_construction_unknown']
        report['complete_candidate']=bool(normal and reaped and raw_returncode==0 and report['group_absent'] is True and report['failure'] is None and not report['cleanup_errors'] and report['all_controls_unchanged'] and not controller_stop_requests and report['sampled_RSS_observation_pass'] and left(60)>0 and not report.get('stream_read_errors') and not report.get('available_evidence_errors') and (report.get('owned_streams') or {}).get('adapter.stdout') is not None and (report.get('owned_streams') or {}).get('adapter.stderr') is not None and report.get('available_adapter_report') is not None and report.get('available_helper_report') is not None)
        report['status']='COMPLETE_FIVE_TOY_OWNER_CANDIDATE_ONLY' if report['complete_candidate'] else 'INCOMPLETE'
        report['resource_scope']='Sampled inherited-group RSS only; null threads; no true peak,controller memory cap,hard quota or all-lifetime guarantee. Final root full-return/inclusive postchecks required.'
        report['post_cutoff_scope']='Signals after handler restoration can terminate the owner and leave missing/partial receipts. They are not claimed captured. No scientific child is launched after cutoff.'
        report['whole_root_startup_through_return_and_final_inclusive_census_required']=True
        report['elapsed_before_receipt']=time.monotonic()-started
        try:
            need(left(60)>0,'No receipt serialization time before60')
            encoded=(json.dumps(report,indent=2,allow_nan=False)+'\n').encode()
            need(inclusive_bytes(records)+len(encoded)<=CAP and left(60)>0,'Complete receipt would exceed inclusive cap/deadline; no truncation')
            with (D/'closed-result.json').open('xb') as f:
                f.write(encoded);f.flush()
            need(inclusive_bytes(records)<=CAP and left(60)>0,'Receipt close/final census returned late/oversize')
        except BaseException:
            report['receipt_write_error']=traceback.format_exc()
            # The frozen primary receipt may already have closed; retain a separate
            # exact error if capacity/time permit, otherwise stderr/outer nonzero.
            try:
                raw=report['receipt_write_error'].encode()
                if left(60)>0 and inclusive_bytes(records)+len(raw)<=CAP:
                    with (D/'receipt-error.txt').open('xb') as f:f.write(raw);f.flush()
            except BaseException:pass
            try:print(report['receipt_write_error'],file=sys.stderr,flush=True)
            except BaseException:pass
    rc=0 if report['complete_candidate'] and report['receipt_write_error'] is None and left(60)>0 and not report.get('stream_read_errors') and not report.get('available_evidence_errors') and (report.get('owned_streams') or {}).get('adapter.stdout') is not None and (report.get('owned_streams') or {}).get('adapter.stderr') is not None and report.get('available_adapter_report') is not None and report.get('available_helper_report') is not None else 2
    if (proc is not None and not reaped) or report['partial_construction_unknown']:
        # Last-resort refusal only: this does not reap, clean up or prove absence.
        # Returned leaders stay retained; partial construction stays unknown.
        # _exit bypasses ordinary teardown; base construction is not qualified.
        try:sys.stdout.flush();sys.stderr.flush()
        except BaseException:pass
        os._exit(2)
    return rc


if __name__=='__main__':raise SystemExit(main())
