"""HELD/UNRUN: thirteen source004 main/class guards, fake providers only."""
import ast
import builtins
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

SOURCE=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993/work/962-engineering/head-star-current24-qfnra-five-toy-owner-prep-004/run_owner_once.py')
SOURCE_SHA256='4b3025d547b758bb90e822b965517f0ac34a309ad12d5e02e534d6fc83533de5'
SOURCE_BYTES=33525
EXTRACTED=('need','record_controller_stop','event_record','left','gate','exit_events','main')
BUILTINS=('__build_class__','BaseException','ChildProcessError','ValueError','bool','dict','int','isinstance','len','list','max','min','print')
FINAL_TARGETS=('adapter.stdout','adapter.stderr','adapter-report.json','toys/report.json')


class FakePath:
    def __init__(self,fs,key):
        self.fs=fs
        self.key=key
    def __truediv__(self,tail):
        return FakePath(self.fs,self.key+'/'+tail if self.key else tail)
    def is_file(self):
        if self.fs.final_phase and self.fs.mode=='missing' and self.key==self.fs.target:
            self.fs.missing_hits.append(self.key)
            return False
        return self.key in self.fs.files
    def is_symlink(self):
        return False
    def read_bytes(self):
        raw=bytes(self.fs.files[self.key])
        # Source main has now completed both earlier empty-stream reads.
        if self.key=='adapter.stderr':
            self.fs.final_phase=True
        return raw
    def open(self,mode):
        if mode!='xb':
            raise AssertionError('Unexpected fake open mode')
        if self.key in self.fs.files:
            raise FileExistsError('Exclusive fake output already exists')
        self.fs.files[self.key]=bytearray()
        return FakeHandle(self.fs,self.key)


class FakeHandle:
    def __init__(self,fs,key):
        self.fs=fs
        self.key=key
    def __enter__(self):
        return self
    def __exit__(self,*args):
        self.fs.closed.append(self.key)
        return False
    def write(self,raw):
        if type(raw) is not bytes:
            raise AssertionError('Only fake binary writes')
        self.fs.files[self.key].extend(raw)
        return len(raw)
    def flush(self):
        self.fs.flushed.append(self.key)


class FakeFS:
    def __init__(self,mode,target):
        self.mode=mode
        self.target=target
        self.final_phase=False
        self.files={'admission.json':bytearray(b'FAKE admission'),
                    'adapter-report.json':bytearray(b'FAKE adapter'),
                    'toys/report.json':bytearray(b'FAKE helper')}
        self.closed=[]
        self.flushed=[]
        self.rec_calls=[]
        self.error_hits=[]
        self.missing_hits=[]
        self.last_error=None
    def descriptor(self,key):
        return dict(path='FAKE/'+key,sha256='c'*64,bytes=len(self.files[key]))
    def rec(self,path):
        self.rec_calls.append(path.key)
        if self.final_phase and self.mode=='rec_error' and path.key==self.target:
            self.error_hits.append(path.key)
            self.last_error='FAKE_TRACEBACK: final rec failed: '+path.key
            raise OSError('Injected final rec failure: '+path.key)
        return self.descriptor(path.key)
    def output_bytes(self,records):
        return sum(len(v) for v in self.files.values())


class FakeClock:
    def __init__(self):
        self.now=1.0
    def monotonic(self):
        self.now+=0.01
        return self.now
    def sleep(self,seconds):
        self.now+=max(0,seconds)


class MemoryText:
    def __init__(self):
        self.parts=[]
    def write(self,text):
        self.parts.append(text)
        return len(text)
    def flush(self):
        return None


class FakeRawExit(BaseException):
    def __init__(self,code):
        self.code=code


def extracted_namespace(fs):
    # Future admitted invocation only: this exact source read and AST selection
    # never import its module globals, adapter, transport or installed providers.
    raw=SOURCE.read_bytes()
    if len(raw)!=SOURCE_BYTES or hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:
        raise AssertionError('Pinned source004 owner changed')
    tree=ast.parse(raw.decode('utf-8'))
    definitions={node.name:node for node in tree.body if isinstance(node,ast.FunctionDef)}
    classes={node.name:node for node in tree.body if isinstance(node,ast.ClassDef)}
    if any(name not in definitions for name in EXTRACTED) or set(classes)!={'_RetainedPopen'}:
        raise AssertionError('Required exact owner004 definitions/class missing')
    clock=FakeClock()
    pid=991001
    operations=[]
    normal_calls=[]
    wait_calls=[]
    group_queries=[]
    queue_queries=[]
    created=[]
    signals=SimpleNamespace(SIGCHLD=101,SIGTERM=102,SIGINT=103,SIG_DFL=0,
                            SIGSTOP=104,SIGCONT=105,SIGKILL=106)
    def fake_signal(number,handler):
        operations.append(('signal_handler',number))
        return 0
    signals.signal=fake_signal
    signals.getsignal=lambda number:0
    signals.Signals=lambda number:SimpleNamespace(name='FAKE_SIGNAL')
    def forbidden(name):
        def fail(*args,**kwargs):
            operations.append(('forbidden',name))
            fs.last_error='FAKE_TRACEBACK: forbidden fake operation: '+name
            raise AssertionError('Forbidden fake operation: '+name)
        return fail
    def fake_waitpid(requested,flags):
        wait_calls.append((requested,flags))
        if requested!=pid:
            raise AssertionError('Wrong synthetic direct PID')
        if flags&2:
            return pid,700
        if fs.mode=='unreaped':
            fs.last_error='FAKE_TRACEBACK: returned handle stays unreaped at fake ceiling'
            return 0,0
        return pid,0
    def fake_getpgid(requested):
        operations.append(('getpgid',requested))
        if requested!=pid:raise AssertionError('Wrong synthetic identity PID')
        return pid
    def fake_getsid(requested):
        operations.append(('getsid',requested))
        if requested!=pid:raise AssertionError('Wrong synthetic identity PID')
        return pid
    def fake_kill(requested,number):
        operations.append(('kill',requested,number))
        if requested!=pid or number not in (signals.SIGCONT,signals.SIGKILL):
            raise AssertionError('Unexpected synthetic direct signal')
        if number==signals.SIGCONT:
            if fs.mode in ('precont','unreaped'):
                raise AssertionError('Continuation must not be attempted')
            if fs.mode=='cont_raises':
                operations.append(('CONT_delivered_then_raised',requested))
                fs.last_error='FAKE_TRACEBACK: CONT delivered then raised'
                raise OSError('Injected return after synthetic CONT delivery')
        elif fs.mode not in ('precont','unreaped'):
            raise AssertionError('Unexpected direct-PID fallback')
    def fake_killpg(requested,number):
        operations.append(('killpg',requested,number))
        if fs.mode!='cont_raises' or requested!=pid or number not in (signals.SIGTERM,signals.SIGKILL):
            raise AssertionError('Unexpected synthetic group signal')
    def fake_raw_exit(code):
        operations.append(('raw_exit',code))
        if code!=2:raise AssertionError('Only raw refusal is supported')
        raise FakeRawExit(code)
    fake_os=SimpleNamespace(WUNTRACED=2,WNOHANG=1,waitpid=fake_waitpid,
        WIFEXITED=lambda status:status==0,WIFSIGNALED=lambda status:False,
        WIFSTOPPED=lambda status:status==700,WSTOPSIG=lambda status:signals.SIGSTOP,
        waitstatus_to_exitcode=lambda status:0,getpgid=fake_getpgid,
        getsid=fake_getsid,kill=fake_kill,killpg=fake_killpg,_exit=fake_raw_exit)
    class FakePopenBase:
        # The provider retains its own synthetic partial object solely to trace
        # the real source class policy. Owner main receives no partial handle.
        def __init__(self,*args,**kwargs):
            operations.append(('Popen',))
            created.append(self)
            self.pid=pid
            self.returncode=None
            if kwargs.get('start_new_session') is not True:
                raise AssertionError('Fixed fake new-session precondition')
            if fs.mode=='partial_constructor':
                fs.last_error='FAKE_TRACEBACK: constructor partial unknown'
                raise OSError('Injected fake constructor partial failure')
        def __del__(self):
            operations.append(('base_destructor',))
        poll=forbidden('Popen.poll')
        wait=forbidden('Popen.wait')
        communicate=forbidden('Popen.communicate')
        send_signal=forbidden('Popen.send_signal')
        terminate=forbidden('Popen.terminate')
        kill=forbidden('Popen.kill')
        __enter__=forbidden('Popen.__enter__')
        __exit__=forbidden('Popen.__exit__')
    fake_subprocess=SimpleNamespace(DEVNULL=object(),Popen=FakePopenBase)
    def queue_control(changes,maxevents,timeout):
        if changes is not None:
            queue_queries.append('registration')
            if fs.mode in ('precont','unreaped'):
                fs.last_error='FAKE_TRACEBACK: registration refused before CONT'
                raise OSError('Injected preregistration failure')
            return []
        queue_queries.append('exit_query')
        # The normal F1 sequence remains exactly one live sample then NOTE_EXIT.
        if fs.mode in ('normal','rec_error','missing'):
            if queue_queries.count('exit_query')==1:return []
            return [SimpleNamespace(ident=pid,filter=401,flags=0,fflags=16,data=0,udata=0)]
        # No real blocking: cleanup time advances only in the explicit fake clock.
        clock.sleep(timeout)
        return []
    queue=SimpleNamespace(control=queue_control,close=lambda:operations.append(('kqueue_close',)))
    fake_select=SimpleNamespace(kqueue=lambda:queue,kevent=lambda *a,**k:SimpleNamespace(),
        KQ_FILTER_PROC=401,KQ_NOTE_EXIT=16,KQ_EV_ADD=1,KQ_EV_ENABLE=2,
        KQ_EV_ONESHOT=4,KQ_EV_ERROR=8)
    before={'synthetic-control':{'identity':'FAKE stable'}}
    aliases={'synthetic-route':'FAKE stable'}
    actual={'selected_python':{'path':'FAKE Python'},'expected_aliases':dict(aliases)}
    auth={'actual':dict(path='FAKE actual',sha256='a'*64,bytes=1)}
    def admit():
        return auth,actual,{},dict(before),dict(aliases),['FAKE adapter argv']
    def normal_reports(selected_actual,report):
        # This prerequisite is fake, not five real Z3 sessions/report validation.
        normal_calls.append(True)
        report['adapter_report']=fs.descriptor('adapter-report.json')
        report['helper_report']=fs.descriptor('toys/report.json')
        report['capture_files']={'synthetic':'FAKE precondition accepted'}
    def group_exists(requested):
        group_queries.append(requested)
        if fs.mode in ('partial_constructor','unreaped'):
            raise AssertionError('No absence observation without actual fake reap')
        return False
    ns={'__name__':'held_owner004_fragments',
        '__builtins__':{name:getattr(builtins,name) for name in BUILTINS},
        'started':0.0,'controller_stop_requests':[],'HELD_LEADERS':[],
        'D':FakePath(fs,''),'CAP':33554432,'RSS_CAP':2147483648,
        'ENV':{'FAKE_THREAD_ENVIRONMENT':'1'},
        'time':clock,'signal':signals,'os':fake_os,'select':fake_select,
        'subprocess':fake_subprocess,'json':json,
        'traceback':SimpleNamespace(format_exc=lambda:fs.last_error or 'FAKE_TRACEBACK: unexpected path'),
        'sys':SimpleNamespace(stdout=MemoryText(),stderr=MemoryText()),
        'admit':admit,'normal_reports':normal_reports,'rec':fs.rec,
        'limits':lambda:operations.append(('limits',)),
        'sample':lambda requested:dict(error=None,late=False,RSS_bytes=1024,live_pids=[pid]),
        'inclusive_bytes':fs.output_bytes,'group_exists':group_exists,
        'identities':lambda records,python:dict(before),
        'provider_links':lambda paths:dict(aliases)}
    module=ast.Module(body=[classes['_RetainedPopen']]+[definitions[name] for name in EXTRACTED],type_ignores=[])
    # Future separately admitted guard only. No module statements or rewritten
    # target predicate; all external operations above are finite explicit fakes.
    builtins.exec(builtins.compile(module,str(SOURCE),'exec'),ns)
    ns['_fixture']=dict(created=created,base=FakePopenBase,clock=clock)
    return ns,operations,normal_calls,wait_calls,group_queries,queue_queries


class Owner004CoreGuards(unittest.TestCase):
    def scenario(self,mode='normal',target=None):
        self.assertIn(mode,('normal','rec_error','missing'))
        self.assertTrue((mode=='normal' and target is None) or target in FINAL_TARGETS)
        fs=FakeFS(mode,target)
        ns,operations,normal_calls,wait_calls,group_queries,queue_queries=extracted_namespace(fs)
        rc=ns['main']()
        self.assertIn('closed-result.json',fs.files)
        report=json.loads(bytes(fs.files['closed-result.json']))
        # All earlier normal prerequisites remain positive. A setup error,
        # cleanup failure or skipped source path cannot satisfy a refusal test.
        self.assertIsNone(report['failure'])
        self.assertEqual(report['cleanup_errors'],[])
        self.assertEqual(report['raw_returncode'],0)
        self.assertTrue(report['reaped'])
        self.assertTrue(report['group_absent'])
        self.assertTrue(report['all_controls_unchanged'])
        self.assertTrue(report['sampled_RSS_observation_pass'])
        self.assertEqual(report['valid_live_sample_count'],1)
        self.assertIsNone(report['receipt_write_error'])
        self.assertFalse(report['last_resort_unreaped_exit'])
        self.assertEqual(report['handled_stop_requests'],[])
        self.assertEqual(normal_calls,[True])
        self.assertEqual(wait_calls,[(991001,3),(991001,1)])
        self.assertEqual(group_queries,[991001,991001])
        self.assertEqual(queue_queries,['registration','exit_query','exit_query'])
        self.assertEqual(len(ns['HELD_LEADERS']),1)
        self.assertEqual([v for v in operations if v[0]=='Popen'],[('Popen',)])
        self.assertEqual([v for v in operations if v[0]=='kill'],[('kill',991001,105)])
        self.assertFalse(any(v[0]=='forbidden' for v in operations))
        self.assertEqual(ns['sys'].stdout.parts,[])
        self.assertEqual(ns['sys'].stderr.parts,[])
        self.assertIn('closed-result.json',fs.flushed)
        self.assertIn('closed-result.json',fs.closed)
        self.assertTrue(report['leader_construction_attempted'])
        self.assertTrue(report['leader_construction_returned'])
        self.assertIsNone(report['leader_construction_error'])
        self.assertFalse(report['partial_construction_unknown'])
        self.assertFalse(report['last_resort_partial_construction_exit'])
        self.assertTrue(report['continuation_intent'])
        self.assertTrue(report['continuation_acknowledged'])
        self.assertIsNone(report['continuation_error'])
        self.assert_private_policy(ns,operations,returned=True)
        return rc,report,fs

    def assert_refused(self,rc,report):
        self.assertEqual(rc,2)
        self.assertFalse(report['complete_candidate'])
        self.assertEqual(report['status'],'INCOMPLETE')

    def assert_rec_error(self,target,error_field,available_field=None):
        rc,report,fs=self.scenario('rec_error',target)
        self.assert_refused(rc,report)
        self.assertEqual(fs.error_hits,[target])
        self.assertEqual(fs.missing_hits,[])
        self.assertEqual(report[error_field],['FAKE_TRACEBACK: final rec failed: '+target])
        if available_field is None:
            self.assertNotIn(target,report.get('owned_streams',{}))
            self.assertNotIn('available_evidence_errors',report)
        else:
            self.assertIsNone(report[available_field])
            self.assertNotIn('stream_read_errors',report)

    def assert_missing(self,target,available_field=None):
        rc,report,fs=self.scenario('missing',target)
        self.assert_refused(rc,report)
        self.assertEqual(fs.error_hits,[])
        self.assertEqual(fs.missing_hits,[target])
        self.assertNotIn('stream_read_errors',report)
        self.assertNotIn('available_evidence_errors',report)
        if available_field is None:
            self.assertNotIn(target,report.get('owned_streams',{}))
        else:
            self.assertIsNone(report[available_field])

    def test_01_complete_normal_control(self):
        rc,report,fs=self.scenario()
        self.assertEqual(rc,0)
        self.assertTrue(report['complete_candidate'])
        self.assertEqual(report['status'],'COMPLETE_FIVE_TOY_OWNER_CANDIDATE_ONLY')
        self.assertEqual(report['owned_streams']['adapter.stdout'],fs.descriptor('adapter.stdout'))
        self.assertEqual(report['owned_streams']['adapter.stderr'],fs.descriptor('adapter.stderr'))
        self.assertEqual(report['available_adapter_report'],fs.descriptor('adapter-report.json'))
        self.assertEqual(report['available_helper_report'],fs.descriptor('toys/report.json'))
        self.assertNotIn('stream_read_errors',report)
        self.assertNotIn('available_evidence_errors',report)
        self.assertEqual(fs.error_hits,[])
        self.assertEqual(fs.missing_hits,[])

    def test_02_final_stdout_rec_failure(self):
        self.assert_rec_error('adapter.stdout','stream_read_errors')

    def test_03_final_stderr_rec_failure(self):
        self.assert_rec_error('adapter.stderr','stream_read_errors')

    def test_04_final_adapter_report_rec_failure(self):
        self.assert_rec_error('adapter-report.json','available_evidence_errors','available_adapter_report')

    def test_05_final_helper_report_rec_failure(self):
        self.assert_rec_error('toys/report.json','available_evidence_errors','available_helper_report')

    def test_06_missing_final_stdout_descriptor(self):
        self.assert_missing('adapter.stdout')

    def test_07_missing_final_stderr_descriptor(self):
        self.assert_missing('adapter.stderr')

    def test_08_missing_final_adapter_descriptor(self):
        self.assert_missing('adapter-report.json','available_adapter_report')

    def test_09_missing_final_helper_descriptor(self):
        self.assert_missing('toys/report.json','available_helper_report')


    def assert_private_policy(self,ns,operations,returned):
        objects=ns['_fixture']['created']
        self.assertEqual(len(objects),1)
        obj=objects[0]
        self.assertIs(type(obj),ns['_RetainedPopen'])
        self.assertIsNot(type(obj).__del__,ns['_fixture']['base'].__del__)
        before=list(operations)
        obj.__del__()
        self.assertEqual(operations,before)
        self.assertFalse(any(row[0] in ('base_destructor','forbidden') for row in operations))
        if returned:
            self.assertEqual(ns['HELD_LEADERS'],[obj])
        else:
            self.assertEqual(ns['HELD_LEADERS'],[])

    def core_case(self,mode):
        self.assertIn(mode,('cont_raises','precont','partial_constructor','unreaped'))
        fs=FakeFS(mode,None)
        del fs.files['adapter-report.json']
        del fs.files['toys/report.json']
        ns,operations,normal_calls,wait_calls,group_queries,queue_queries=extracted_namespace(fs)
        raw_exit=None
        rc=None
        try:
            rc=ns['main']()
        except FakeRawExit as exc:
            raw_exit=exc.code
        self.assertIn('closed-result.json',fs.files)
        report=json.loads(bytes(fs.files['closed-result.json']))
        self.assertFalse(report['complete_candidate'])
        self.assertEqual(report['status'],'INCOMPLETE')
        self.assertIsNotNone(report['failure'])
        self.assertIsNone(report['receipt_write_error'])
        self.assertFalse(report['sampled_RSS_observation_pass'])
        self.assertEqual(report['valid_live_sample_count'],0)
        self.assertEqual(normal_calls,[])
        self.assertIsNone(report['adapter_report'])
        self.assertIsNone(report['helper_report'])
        self.assertIsNone(report['capture_files'])
        self.assertIsNone(report['available_adapter_report'])
        self.assertIsNone(report['available_helper_report'])
        self.assertIn('closed-result.json',fs.closed)
        self.assertIn('closed-result.json',fs.flushed)
        self.assertEqual([row for row in operations if row[0]=='Popen'],[('Popen',)])
        self.assertTrue(report['leader_construction_attempted'])
        self.assertEqual(report['leader_construction_returned'],mode!='partial_constructor')
        self.assertEqual(report['partial_construction_unknown'],mode=='partial_constructor')
        self.assert_private_policy(ns,operations,returned=mode!='partial_constructor')
        return rc,raw_exit,report,operations,wait_calls,group_queries,queue_queries

    def test_10_delivered_raising_CONT_keeps_group_cleanup(self):
        rc,raw_exit,report,ops,waits,groups,queries=self.core_case('cont_raises')
        self.assertEqual((rc,raw_exit),(2,None))
        self.assertTrue(report['continuation_intent'])
        self.assertFalse(report['continuation_acknowledged'])
        self.assertEqual(report['continuation_error'],'FAKE_TRACEBACK: CONT delivered then raised')
        self.assertEqual(report['failure'],report['continuation_error'])
        self.assertEqual([x for x in ops if x[0]=='CONT_delivered_then_raised'],[('CONT_delivered_then_raised',991001)])
        self.assertEqual([x for x in ops if x[0]=='kill'],[('kill',991001,105)])
        self.assertEqual([x for x in ops if x[0]=='killpg'],[('killpg',991001,102),('killpg',991001,106)])
        self.assertEqual(waits,[(991001,3),(991001,1)])
        self.assertEqual(groups,[991001])
        self.assertTrue(report['reaped'])
        self.assertEqual(report['raw_returncode'],0)
        self.assertTrue(report['group_absent'])
        self.assertFalse(report['last_resort_unreaped_exit'])
        self.assertFalse(report['last_resort_partial_construction_exit'])
        self.assertEqual(report['cleanup_errors'],[])

    def test_11_preCONT_error_uses_only_own_direct_PID(self):
        rc,raw_exit,report,ops,waits,groups,queries=self.core_case('precont')
        self.assertEqual((rc,raw_exit),(2,None))
        self.assertEqual(report['failure'],'FAKE_TRACEBACK: registration refused before CONT')
        self.assertFalse(report['continuation_intent'])
        self.assertFalse(report['continuation_acknowledged'])
        self.assertIsNone(report['continuation_error'])
        self.assertEqual([x for x in ops if x[0]=='kill'],[('kill',991001,106)])
        self.assertEqual([x for x in ops if x[0]=='killpg'],[])
        self.assertEqual(waits,[(991001,3),(991001,1)])
        self.assertEqual(groups,[991001])
        self.assertTrue(report['reaped'])
        self.assertTrue(report['group_absent'])
        self.assertEqual(report['cleanup_errors'],[])

    def test_12_partial_constructor_unknown_raw_exit2_no_guessed_APIs(self):
        rc,raw_exit,report,ops,waits,groups,queries=self.core_case('partial_constructor')
        self.assertEqual((rc,raw_exit),(None,2))
        self.assertTrue(report['leader_construction_attempted'])
        self.assertFalse(report['leader_construction_returned'])
        self.assertEqual(report['leader_construction_error'],'FAKE_TRACEBACK: constructor partial unknown')
        self.assertEqual(report['failure'],report['leader_construction_error'])
        self.assertTrue(report['partial_construction_unknown'])
        self.assertTrue(report['direct_relationship_unknown'])
        self.assertTrue(report['last_resort_partial_construction_exit'])
        self.assertFalse(report['last_resort_unreaped_exit'])
        self.assertFalse(report['process_started'])
        self.assertIsNone(report['PID'])
        self.assertIsNone(report['ownership_certificate'])
        self.assertFalse(report['reaped'])
        self.assertIsNone(report['raw_returncode'])
        self.assertIsNone(report['group_absent'])
        self.assertEqual(waits,[])
        self.assertEqual(groups,[])
        self.assertEqual(queries,[])
        self.assertFalse(any(x[0] in ('kill','killpg','getpgid','getsid') for x in ops))
        self.assertEqual([x for x in ops if x[0]=='raw_exit'],[('raw_exit',2)])

    def test_13_returned_unreaped_private_policy_raw_exit2(self):
        rc,raw_exit,report,ops,waits,groups,queries=self.core_case('unreaped')
        self.assertEqual((rc,raw_exit),(None,2))
        self.assertTrue(report['leader_construction_returned'])
        self.assertFalse(report['partial_construction_unknown'])
        self.assertTrue(report['last_resort_unreaped_exit'])
        self.assertFalse(report['last_resort_partial_construction_exit'])
        self.assertFalse(report['continuation_intent'])
        self.assertFalse(report['reaped'])
        self.assertIsNone(report['raw_returncode'])
        self.assertIsNone(report['group_absent'])
        self.assertEqual(waits[0],(991001,3))
        self.assertGreater(len(waits),1)
        self.assertTrue(all(row==(991001,1) for row in waits[1:]))
        self.assertEqual(groups,[])
        self.assertEqual([x for x in ops if x[0]=='kill'],[('kill',991001,106)])
        self.assertEqual([x for x in ops if x[0]=='killpg'],[])
        self.assertEqual([x for x in ops if x[0]=='raw_exit'],[('raw_exit',2)])
        self.assertEqual(report['cleanup_errors'],['FAKE_TRACEBACK: returned handle stays unreaped at fake ceiling'])


if __name__=='__main__':unittest.main(verbosity=2)
