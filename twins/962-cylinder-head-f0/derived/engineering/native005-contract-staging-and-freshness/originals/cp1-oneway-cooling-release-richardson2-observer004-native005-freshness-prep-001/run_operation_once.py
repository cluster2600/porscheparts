"""HELD/UNRUN retained-anchor owner for one fixed native005 freshness operation."""
import time
started=time.monotonic();controller_stop_requests=[]
import hashlib,json,os,re,select,signal,subprocess,sys,traceback
from pathlib import Path

R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E=R/'work/962-engineering'
X=E/'cp1-oneway-cooling-release-richardson2-observer004-native005-freshness-prep-001'
D=E/'cp1-oneway-cooling-release-richardson2-observer004-native005-freshness-owner-root-execution-001'
H=E/'cp1-oneway-cooling-release-richardson2-observer004-native005-freshness-helper-root-execution-001'
O=E/'cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004'
N=E/'cp1-oneway-cooling-release-richardson2-observer004-native-measurement-root-execution-004'
W=E/'cp1-oneway-cooling-release-richardson2-observer004-native005-freshness-root-terminal-review-001'
WRAPPER=X/'stopped_exec_wrapper.py'
CAP=33554432

PYTHON={"path":"/Users/maxime/.codex/worktrees/962-watercooled-head/3dprinting993/work/962-head/check-venv/bin/python","resolved_path":"/Users/maxime/.local/share/uv/python/cpython-3.12.11-macos-aarch64-none/bin/python3.12","sha256":"1699bf8aa705a8bb71613bef5cdd7d7c8c9d9a188a841f41679aa9b5830b8f60","bytes":49968,"is_symlink":True,"raw_target":"python3.12"}
ENV={"PATH":"/usr/bin:/bin","LANG":"C","LC_ALL":"C","OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1","VECLIB_MAXIMUM_THREADS":"1","FI_PROVIDER":"tcp"}
REQUIRED_PROTECTED={
  "native_actual": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-execution-prep-004/actual-contract.json",
    "sha256": "a5e35548cacd4f2abfd4f0d29e5aeb738ce16bdc814f642e016851c3450f1986",
    "bytes": 273368
  },
  "native_caller": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-prep-005/run_native_capture.py",
    "sha256": "a04276da60fe09d9af26d32c7661fb421105b7c93724d43c728025dd1fd51aa5",
    "bytes": 45810
  },
  "native_root_controller": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-prep-005/run_root_once.py",
    "sha256": "34826ad993e4d874455adb40777df545f76cf611a6f23ae021a49302dc0dd649",
    "bytes": 61563
  },
  "native_wrapper": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-prep-005/stopped_exec_wrapper.py",
    "sha256": "a81328f9e07bded2120d8f908f8831bdafead07132ae09a1af4ccfcc4bf50e17",
    "bytes": 5295
  },
  "native_source_index": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-prep-005/index.json",
    "sha256": "acb06644ef2df3ed06273b4d936ecab8a76cd7760b1ddcc6e911bca0d1c554c3",
    "bytes": 6734
  },
  "native_exact_child_peer": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-source-peer-001/review.json",
    "sha256": "777233540d91a59b70df3ae0947eddb32a07a3a7b1cc715de4906873d4fc946f",
    "bytes": 5291
  },
  "native_exact_child_bindings": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-source-peer-001/bindings.json",
    "sha256": "29a29c02987c67782cd5a1ab8654bc43f3309995e49a6bad25fd4e04b9546691",
    "bytes": 14116
  },
  "native_root_source_review": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-root-source-review-001/review.json",
    "sha256": "a8f8dd842abdc4a309b8bd4dc7c420af65ef1e9bb5b80826eb71ea93f9cd76f8",
    "bytes": 3969
  },
  "native_binding_candidate": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-execution-binding-prep-001/actual-contract.candidate.json",
    "sha256": "a5e35548cacd4f2abfd4f0d29e5aeb738ce16bdc814f642e016851c3450f1986",
    "bytes": 273368
  },
  "native_binding_method": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-execution-binding-prep-001/METHOD.md",
    "sha256": "3e06b15581208a893da4f145079a117e202ac6c54316bf886c18dcfae88ef188",
    "bytes": 6452
  },
  "native_binding_inputs": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-execution-binding-prep-001/bindings.json",
    "sha256": "451d80933d3ce589032fe82189af060b90e27a913b719ca924b6ff9f96515b43",
    "bytes": 58253
  },
  "native_binding_change_map": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-execution-binding-prep-001/change-map.json",
    "sha256": "b857a0c7486833aa8de671f7aaf1307d83353003e8ff01886746ccab25af763e",
    "bytes": 115691
  },
  "helper": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-freshness-prep-001/capture_freshness.py",
    "sha256": "e3f1c980ead8f7952eb82a1996db7fc167ca829c294afdccf4b9c83d65fe2dac",
    "bytes": 17737
  },
  "wrapper": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-freshness-prep-001/stopped_exec_wrapper.py",
    "sha256": "9839a4b3837115e13e331a07296daa0a95f77915be78f6e6c63afb732ad9a3a2",
    "bytes": 1588
  },
  "source_adaptation_authority": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-freshness-adaptation-root-authority-001/review.json",
    "sha256": "c777a995b439c8329f0aee20c432a5361416a12cee1a5c4d2f882fcf38a5d276",
    "bytes": 7936
  },
  "current_contract_root": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-execution-binding-root-review-001/review.json",
    "sha256": "3f030491c886a450d6be43f3f5d2f198ec1fc4bd4ae0b2ce9588c876b094a5d2",
    "bytes": 10112
  },
  "accepted_staging_receipt": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-four-input-staging-root-001/staging-receipt.json",
    "sha256": "3ec1f62e359414c02eda78ed6e285beed3e9774c61366816560e22cfe6bddfa9",
    "bytes": 5897
  },
  "stage_root_acceptance": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-four-input-staging-root-001/postreturn-acceptance.json",
    "sha256": "44b4efd5a9fada59392979b628f9a12c87ce5f86293b8397d5713936e251d087",
    "bytes": 3920
  },
  "parent003_actual": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-execution-prep-003/actual-contract.json",
    "sha256": "85a9195ed1a217eef6bad44518390f1b2dfdb879c9cdfc072b6e1465461a5198",
    "bytes": 116306
  },
  "historical_freshness_acceptance": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native003-freshness-root-result-acceptance-001/acceptance.json",
    "sha256": "ac5477484c620b2fd3d0b67a9d4c73945bc14e8e5564d1bf9559bc9b12fc2984",
    "bytes": 3866
  },
  "donor_freshness_helper": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native003-staging-freshness-prep-001/capture_freshness.py",
    "sha256": "a577e2b3499aa3571d2f08e0b7e5f54d687464654e8de7af523f7d112a1edd7d",
    "bytes": 15798
  },
  "donor_legacy_owner_semantic_receipt_only": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native003-freshness-operation-controls-prep-002/run_operation_once.py",
    "sha256": "0555062736bd2b63dbd8da4cddfc5ef56d158eca0878be188a2cf32fcbe4fded",
    "bytes": 18764
  },
  "donor_modern_retained_owner": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-f1-guards-controls-prep-002/run_guards_once.py",
    "sha256": "42aec198fb911c43f7658544911e0af23cdc76222ce25e917ceb932c2473088a",
    "bytes": 27767
  },
  "donor_modern_stopped_wrapper": {
    "path": "work/962-engineering/head-star-current24-qfnra-five-toy-owner-f1-guards-controls-prep-002/stopped_exec_wrapper.py",
    "sha256": "ab0ebf6bc3110680ce0f03022da2d66452175877a07612b6657ecb66c02afdf4",
    "bytes": 1536
  }
}

CONTROLS=dict(normal_seconds=40,TERM_absolute_seconds=48,KILL_reap_absolute_seconds=56,whole_seconds=60,
    TERM_grace_seconds=8,KILL_reap_grace_seconds=8,total_inclusive_bytes=33554432,thread_environment=1,retries=0,RSS_sampler=False)
HELPER_LIMITS=dict(whole_seconds=60,TERM_grace_seconds=8,stream_buffer_bytes=1048576,query_seconds=5,total_inclusive_bytes=33554432,thread_environment=1,retries=0)
DIRECT_ROLES=('controller','wrapper','helper','held_plan','held_actual','control_preparation_index','helper_authorization','helper_source_peer','helper_source_findings','helper_source_bindings','helper_root_review','root_control_review','staging_receipt','stage_root_acceptance',)
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
    # Installed runtime/provider bodies are excluded unless copied into an owned root.
    files={}
    for owned in (D,H,O):
        need(owned.is_dir() and not owned.is_symlink(),'Changed fixed owned directory')
        for p in owned.rglob('*'):
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


def diagnostics(auth):
    need(all((D/name).stat().st_size<=CAP for name in ('helper.stdout','helper.stderr')),'Full helper stream exceeds cap; retained without parsing')
    with (D/'helper.stdout').open('rb') as f:out=f.read(CAP+1)
    with (D/'helper.stderr').open('rb') as f:err=f.read(CAP+1)
    need(out==err==b'','Positive helper closure requires complete empty helper streams')
    path=H/'fresh-preflight.json'
    need(path.is_file() and not path.is_symlink() and path.stat().st_size<=CAP,'Complete fixed helper receipt required before leader reap')
    value=json.loads(path.read_bytes());q=value['query']
    need(value['schema']=='962-observer004-native005-fresh-preflight/v1' and value['status']=='COMPLETE_METADATA_ONLY' and value['all_declared_identities_unchanged'] is True and value['error'] is None,'Finite freshness refused')
    need(value['metadata_query_only'] is True and value['native_execution'] is False and value['fixture_execution'] is False and value['field_parsing'] is False,'Only fixed metadata operation permitted')
    need(value['helper']==REQUIRED_PROTECTED['helper'] and value['held_plan']==auth['held_plan'] and value['authorization']==auth['helper_authorization']==rec(H/'authorization.json'),'Helper receipt source/authority associations changed')
    need(value['controls_before']==value['controls_after'] and value['observations_before']==value['observations_after'],'Complete before/after helper identity maps required')
    observations=value['observations_before']
    need(all(len(observations[key])==count for key,count in [('inputs',348),('runtime_files',19),('runtime_links',13),('providers',22),('host_records',89),('staged_inputs',4)]),'Complete finite observation counts required')
    need(type(q['attempts']) is int and q['attempts']==1 and q['started'] is True and type(q['returncode']) is int and q['returncode']==0 and q['reaped'] is True and q['new_session'] is False,'One normally reaped inherited-group query required')
    need(q['error'] is None and q.get('validation_error') is None and q['stop_actions']==[] and type(q['elapsed_through_cleanup']) in (int,float) and 0<=q['elapsed_through_cleanup']<=5,'Query cleanup failed/unknown/late; retain group anchor')
    need(q.get('cleanup_TERM_error') is None and q.get('cleanup_KILL_error') is None,'No query cleanup error may release the helper leader')
    need(q['stdout']==rec(H/'query.stdout') and 0<q['stdout']['bytes']<=65536 and q['stderr']==rec(H/'query.stderr') and q['stderr']['bytes']==0,'Complete exact query streams required')
    meta=q['metadata']
    need(meta['version_info']==[3,12,11] and meta['executable']==PYTHON['path'] and meta['resolved_executable']==PYTHON['resolved_path'],'Exact selected query identity required')
    need(meta['flags']==dict(isolated=1,no_site=1,dont_write_bytecode=1,no_user_site=1,optimize=0) and meta['site_loaded'] is False and meta['distutils_hack_loaded'] is False,'Exact query startup flags required')
    return dict(helper_receipt=rec(path),query_reaped=True,query_returncode=0,query_elapsed_through_cleanup=q['elapsed_through_cleanup'],complete_metadata_only=True)


def admit():
    need(len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1]),'HELD: sole external root-admission digest required')
    A=D/'admission.json';ap=rec(A)
    need(ap['sha256']==sys.argv[1] and ap['bytes']<=CAP,'Changed/oversize root admission')
    auth=json.loads(A.read_bytes())
    need(auth['schema']=='962-native005-freshness-owner-root-admission/v1' and auth['root_issued'] is True and auth['metadata_freshness_authorized'] is True,'No metadata freshness authority')
    need(type(auth['invocations']) is int and auth['invocations']==1 and auth['automatic_retry'] is False and auth['controls']==CONTROLS,'One fixed bounded invocation required')
    need(all(auth[k] is True for k in ('independent_source_review_complete','independent_control_source_review_complete','root_control_review_complete','selected_operation_identity_accepted_by_root','opaque_declared_identity_reads_authorized')),'Pending source/control/fixed-operation admission')
    need(all(auth[k] is False for k in ('staging_authorized','fixture_execution_authorized','Z3_authorized','native_execution_authorized','field_parsing_authorized','physical_acceptance','manufacturing_authorized')),'No staging/scientific/native authority')
    need(auth['selected_python']==PYTHON and auth['environment']==ENV and all(os.environ.get(k)==v for k,v in ENV.items()),'Exact3.12/thread-one route required; no environment dump')
    need(str(Path(sys.executable).resolve(strict=True))==PYTHON['resolved_path'] and sys.version_info[:3]==(3,12,11),'Selected3.12.11 owner required')
    need(Path(PYTHON['path']).is_symlink() is PYTHON['is_symlink'] and os.readlink(PYTHON['path'])==PYTHON['raw_target'],'Changed selected alias metadata')
    need(sys.flags.isolated==sys.flags.dont_write_bytecode==sys.flags.no_site==1 and sys.flags.optimize==0 and 'site' not in sys.modules and '_distutils_hack' not in sys.modules,'Exact -B-I-S startup required')
    need(signal.getsignal(signal.SIGCHLD)==signal.SIG_DFL,'Already-default SIGCHLD and no competing waiter required')
    need(all(hasattr(select,k) for k in ('kqueue','kevent','KQ_FILTER_PROC','KQ_NOTE_EXIT','KQ_EV_ADD','KQ_EV_ENABLE','KQ_EV_ONESHOT','KQ_EV_ERROR')) and all(hasattr(os,k) for k in ('waitpid','WUNTRACED','WNOHANG','WIFSTOPPED','WSTOPSIG','WIFEXITED','WIFSIGNALED','waitstatus_to_exitcode','getpgid','getsid','killpg','kill')),'Named APIs unavailable; no launch')
    need(not D.is_symlink() and D.resolve(strict=True)==D and set(p.name for p in D.iterdir())=={'admission.json'},'Fresh fixed owner root required')
    need(H.is_dir() and not H.is_symlink() and H.resolve(strict=True)==H and set(p.name for p in H.iterdir())=={'authorization.json'} and not N.exists(),'Fresh helper authorization only and no native root required')
    need(selected(auth['controller'])==X/'run_operation_once.py' and auth['controller']==rec(Path(__file__)) and selected(auth['wrapper'])==WRAPPER and selected(auth['control_preparation_index'])==X/'index.json','Fixed executed controller and source preparation paths required')
    need(auth['helper']==REQUIRED_PROTECTED['helper'] and selected(auth['held_plan'])==X/'held-plan.json' and selected(auth['held_actual'])==X/'held-actual.json','Fixed helper/held context required')
    need(auth['helper_authorization']==rec(H/'authorization.json') and auth['staging_receipt']==REQUIRED_PROTECTED['accepted_staging_receipt'] and auth['stage_root_acceptance']==REQUIRED_PROTECTED['stage_root_acceptance'],'Exact helper authorization/current staging required')
    need(auth['outer_stream_paths']==[str(W/'outer.stdout'),str(W/'outer.stderr')],'Fixed external streams required')
    held=json.loads((X/'held-actual.json').read_bytes());plan=json.loads((X/'held-plan.json').read_bytes())
    need(held['status']=='HELD_UNRUN_SOURCE_ONLY' and held['operation_authorized'] is False and held['controller']==auth['controller'] and held['wrapper']==auth['wrapper'] and held['helper']==auth['helper'] and held['helper_plan']==auth['held_plan'] and held['controls']==CONTROLS and held['helper_limits']==HELPER_LIMITS,'Exact immutable held operation context required')
    need(plan['known_native_roles']==held['known_native_roles'] and plan['native_final_role_names']==held['native_final_role_names'] and len(plan['known_native_roles'])==12 and set(plan['known_native_roles'])==set(plan['native_final_role_names'])-{'staging_receipt','fresh_preflight'} and len(plan['native_final_role_names'])==14,'Exact12 known/14 final native roles required')
    helper_auth=json.loads((H/'authorization.json').read_bytes())
    need(helper_auth['schema']=='962-native005-finite-helper-root-admission/v1' and helper_auth['helper']==auth['helper'] and helper_auth['plan']==auth['held_plan'] and helper_auth['limits']==HELPER_LIMITS,'Fixed helper source/plan/limits required')
    for key in ('helper_source_peer','helper_source_findings','helper_source_bindings','helper_root_review','staging_receipt','stage_root_acceptance'):
        need(helper_auth[key]==auth[key],'Exact shared late helper/control roles required')
    need(helper_auth['helper_preparation_index']==auth['control_preparation_index'],'Shared packet index required')
    first=dict(auth['protected_records'])
    need(all(first.get(k)==v for k,v in REQUIRED_PROTECTED.items()),'All known finite provenance must be protected')
    for k in DIRECT_ROLES:first['direct_'+k]=auth[k]
    for k,pin in helper_auth['protected_records'].items():
        need(pin in first.values(),'Every helper-protected record must also be owner-protected')
    packet=json.loads(selected(auth['control_preparation_index']).read_bytes())
    expected={'capture_freshness.py','run_operation_once.py','stopped_exec_wrapper.py','held-plan.json','held-actual.json','METHOD.md','bindings.json','source-reuse.json','source.diff','source.inverse.diff'}
    need(set(packet['files'])==expected and packet['file_count_including_this_index']==11,'Fixed eleven-file freshness source packet required')
    need(all(pin in first.values() for pin in packet['files'].values()),'All finite source/proof files must be admitted and protected')
    actual=json.loads(selected(REQUIRED_PROTECTED['native_actual']).read_bytes())
    need(len(actual['input_sha256'])==348 and len(actual['inclusive_external_records'])==348,'Exact current348 input scope required')
    expected_inputs={pin['path']:pin for pin in actual['inclusive_external_records'].values()}
    need(len(expected_inputs)==348 and set(expected_inputs)==set(actual['input_sha256']) and all(pin['sha256']==actual['input_sha256'][name] for name,pin in expected_inputs.items()),'Complete348 input descriptor association required')
    for i,(name,pin) in enumerate(sorted(expected_inputs.items())):first['native_input_'+str(i)]=pin
    need(O.is_dir() and not O.is_symlink() and set(p.name for p in O.iterdir())==set(actual['staged_inputs']) and len(actual['staged_inputs'])==4,'Exactly four existing staged inputs required')
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
    report=dict(schema='962-native005-freshness-owner-result/v1',status='INCOMPLETE',admission=ap,before=before,after=None,
        PID=None,ownership_certificate=None,process_started=False,continuation_intent=False,normal_NOTE_EXIT=False,
        group_signal_intent_ended=False,reaped=False,raw_returncode=None,direct_relationship_unknown=False,events=[],
        stop_actions=[],cleanup_errors=[],failure=None,group_absent=None,postreap_absence_observations=0,
        diagnostics=None,pre_reap_helper_diagnostics=None,helper_query_cleanup_confirmed=False,owned_streams={},stream_read_errors=[],finalization_errors=[],receipt_write_error=None,
        complete_candidate=False,last_resort_unreaped_exit=False,sampled_RSS_bytes=None,sampled_RSS_observation_pass=None,
        RSS_scope='No RSS sampler, query, hard quota or pass claim.',source_descriptor_reads=True,
        scientific_body_decode=False,opaque_declared_identity_reads=True,Z3_executed=False,native_execution=False,physical_acceptance=False,automatic_retry=False)
    proc=None;kq=None;certificate=None
    old_TERM=signal.signal(signal.SIGTERM,record_controller_stop);old_INT=signal.signal(signal.SIGINT,record_controller_stop)
    try:
        kq=select.kqueue()
        argv=[PYTHON['path'],'-B','-I','-S',str(WRAPPER),auth['helper_authorization']['sha256']]
        need(auth['argv_prefix']==argv[:-1] and auth['cwd']==str(H),'Fixed stopped-wrapper invocation required')
        with (D/'helper.stdout').open('xb') as out,(D/'helper.stderr').open('xb') as err:
            gate(40,'Stopped before fixed wrapper launch')
            proc=_RetainedPopen(argv,cwd=H,env=ENV,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
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
                    report['normal_NOTE_EXIT']=True
                gate(40,'Exit query returned late/stopped')
                if seen:
                    report['pre_reap_helper_diagnostics']=diagnostics(auth)
                    gate(40,'Positive helper query-cleanup validation returned late/stopped')
                    report['helper_query_cleanup_confirmed']=True
                    report['group_signal_intent_ended']=True
                    break
            reap(proc,report,started+56)
            need(report['raw_returncode']==0,'Helper raw nonzero; full diagnostics retained')
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
        for name in ('helper.stdout','helper.stderr'):
            try:
                p=D/name;need(p.is_file() and not p.is_symlink(),'Missing final fixed stream')
                report['owned_streams'][name]=rec(p)
            except BaseException:report['stream_read_errors'].append(traceback.format_exc())
        if report['reaped'] and report['group_absent'] is True and report['raw_returncode']==0:
            try:
                report['diagnostics']=diagnostics(auth)
                need(report['diagnostics']==report['pre_reap_helper_diagnostics'],'Helper receipt changed after deliberate reap')
                gate(60,'Diagnostics returned late/stopped')
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
        report['complete_candidate']=bool(report['normal_NOTE_EXIT'] and report['reaped'] and report['raw_returncode']==0 and report['group_absent'] is True and report['postreap_absence_observations']==1 and report['failure'] is None and not report['cleanup_errors'] and not report['finalization_errors'] and not report['stream_read_errors'] and set(report['owned_streams'])=={'helper.stdout','helper.stderr'} and report['helper_query_cleanup_confirmed'] is True and report['diagnostics'] is not None and report['diagnostics']==report['pre_reap_helper_diagnostics'] and report['all_controls_unchanged'] and not controller_stop_requests and time.monotonic()<started+60)
        report['status']='COMPLETE_NATIVE005_METADATA_FRESHNESS_CANDIDATE_ONLY' if report['complete_candidate'] else 'INCOMPLETE'
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

