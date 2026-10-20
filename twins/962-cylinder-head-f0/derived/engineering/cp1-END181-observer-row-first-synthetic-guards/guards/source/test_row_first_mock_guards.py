"""UNRUN synthetic guards; never import an executable owner or call real OS APIs."""
import ast
import hashlib
import unittest
from pathlib import Path

R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
OLD=dict(path='work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-prep-002/run_root_once.py',sha256='c4450f31c12d5d3367f7663ece62598b16253aff31b557f7fc051d3854fadf0f',bytes=18913)
NEW=dict(path='work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-row-first-sampler-prep-001/run_root_once_row_first_proposed.py',sha256='5287901ed8459bc003243d89d122307d4d5852b804a6bfb97d0ece893a37cf3d',bytes=18849)
OLD_CALL='sample_owned({proc.pid}|{g for g in owned if group_exists(g)})'
NEW_CALL='sample_owned({proc.pid}|owned)'
OLD_PRED="group_exists(g) and not any(x['pgid']==g for x in rows)"
NEW_PRED="not any(x['pgid']==g for x in rows) and group_exists(g)"
SAFE_BUILTINS=dict(str=str,int=int,dict=dict,repr=repr,any=any,all=all,len=len,sum=sum,
    ValueError=ValueError,ProcessLookupError=ProcessLookupError,Exception=Exception,
    type=type,sorted=sorted)


def checked_text(data,pin):
    if len(data)!=pin['bytes'] or hashlib.sha256(data).hexdigest()!=pin['sha256']:
        raise ValueError('Frozen first-party source identity mismatch')
    return data.decode('utf-8')


def functions(tree):
    return {n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}


def code_text(text,node):
    return '\n'.join(text.splitlines()[node.lineno-1:node.end_lineno])


def handler(tree):
    found=[n for n in ast.walk(functions(tree)['main']) if isinstance(n,ast.ExceptHandler)
        and n.body and isinstance(n.body[0],ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='direct_RC' for t in n.body[0].targets)]
    if len(found)!=1:raise ValueError('Unique real observation-error handler required')
    return found[0]


def sample_assignment(tree):
    found=[n for n in ast.walk(functions(tree)['main']) if isinstance(n,ast.Assign)
        and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name)
        and n.value.func.id=='sample_owned']
    if len(found)!=1:raise ValueError('Unique real main sampler call required')
    return found[0]


def discovery_if(tree):
    found=[n for n in ast.walk(functions(tree)['main']) if isinstance(n,ast.If)
        and len(n.body)==1 and isinstance(n.body[0],ast.Expr)
        and isinstance(n.body[0].value,ast.Call)
        and isinstance(n.body[0].value.func,ast.Attribute)
        and isinstance(n.body[0].value.func.value,ast.Name)
        and n.body[0].value.func.value.id=='owned'
        and n.body[0].value.func.attr=='add']
    if len(found)!=1:raise ValueError('Unique existing owned registration predicate required')
    return found[0]


class FakeCompleted:
    def __init__(self,stdout,returncode=0,stderr=''):
        self.stdout=stdout;self.returncode=returncode;self.stderr=stderr


class FakePS:
    def __init__(self,response):self.response=response;self.calls=[]
    def run(self,argv,**kwargs):
        self.calls.append((argv,kwargs))
        if argv!=['/bin/ps','-axo','pid=,pgid=,rss=,stat='] or kwargs!={
            'capture_output':True,'text':True,'env':{'PATH':'/usr/bin:/bin','LC_ALL':'C'},'timeout':2}:
            raise AssertionError('Unexpected mocked ps API; no real fallback exists')
        if isinstance(self.response,BaseException):raise self.response
        return self.response


class FakeOS:
    def __init__(self,outcomes):self.outcomes=outcomes;self.calls=[]
    def killpg(self,pid,sig):
        self.calls.append((pid,sig))
        if sig!=0 or pid not in self.outcomes:
            raise AssertionError('Forbidden/unconfigured mocked killpg; no real fallback exists')
        result=self.outcomes[pid]
        if isinstance(result,BaseException):raise result
        if result is not None:raise AssertionError('Only a configured normal return or error is allowed')


class FakeProc:
    def __init__(self,returncode=None):self.pid=101;self.returncode=returncode;self.poll_calls=0
    def poll(self):self.poll_calls+=1;return self.returncode


class FakeClock:
    def __init__(self):self.calls=0
    def monotonic(self):self.calls+=1;return 12.5


class FakeTraceback:
    def format_exc(self):return 'SYNTHETIC_TRACEBACK_ONLY'


def isolated_sampler(tree,stdout='',outcomes=None,response=None):
    ps=FakePS(FakeCompleted(stdout) if response is None else response)
    fake_os=FakeOS({} if outcomes is None else outcomes)
    names=functions(tree)
    ns={'__builtins__':SAFE_BUILTINS,'subprocess':ps,'os':fake_os}
    # Compile ONLY these two exact FunctionDef bodies in a sealed fake namespace.
    # No owner imports, globals, main, cleanup, or other executable statements enter.
    selected=ast.Module(body=[names['group_exists'],names['sample_owned']],type_ignores=[])
    exec(compile(ast.fix_missing_locations(selected),'<frozen-functions-FAKE-ONLY>','exec'),ns)
    return ns,ps,fake_os


def handler_result(tree,code,initial_stop=None):
    template=ast.parse('def isolated(proc,injected_error,owned,started,observation_operation,observation_target_PID,initial_stop):\n'
        ' stop=initial_stop\n error=None\n exit_races=[]\n try:\n  raise injected_error\n except Exception as exc:\n  pass\n'
        ' return dict(stop=stop,error=error,exit_races=exit_races)\n')
    template.body[0].body[3].handlers=[handler(tree)]
    clock=FakeClock();proc=FakeProc(code)
    ns={'__builtins__':SAFE_BUILTINS,'time':clock,'traceback':FakeTraceback()}
    exec(compile(ast.fix_missing_locations(template),'<real-handler-FAKE-ONLY>','exec'),ns)
    result=ns['isolated'](proc,PermissionError(1,'synthetic EPERM'),{202},10,
        NEW_CALL,None,initial_stop)
    return result,proc,clock


class RowFirstMockGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Only the two named small first-party source texts are read.
        cls.old=checked_text((R/OLD['path']).read_bytes(),OLD)
        cls.new=checked_text((R/NEW['path']).read_bytes(),NEW)
        cls.ot=ast.parse(cls.old);cls.nt=ast.parse(cls.new)

    def test_01_exact_three_occurrences_and_cleanup_lifecycle_reuse(self):
        self.assertEqual(self.old.count(OLD_CALL),2)
        self.assertEqual(self.old.count(OLD_PRED),1)
        self.assertEqual(self.new.count(NEW_CALL),2)
        self.assertEqual(self.new.count(NEW_PRED),1)
        self.assertEqual(self.old.replace(OLD_CALL,NEW_CALL).replace(OLD_PRED,NEW_PRED),self.new)
        self.assertEqual(self.new.replace(NEW_CALL,OLD_CALL).replace(NEW_PRED,OLD_PRED),self.old)
        a,b=functions(self.ot),functions(self.nt)
        self.assertEqual(set(a),set(b));self.assertEqual(len(a),19)
        for name in sorted(set(a)-{'main','sample_owned'}):
            with self.subTest(exact_helper=name):
                self.assertEqual(code_text(self.old,a[name]),code_text(self.new,b[name]))
                self.assertEqual(ast.dump(a[name],include_attributes=False),ast.dump(b[name],include_attributes=False))
        for name in ('request','stop_wait'):
            aa=next(n for n in ast.walk(a['main']) if isinstance(n,ast.FunctionDef) and n.name==name)
            bb=next(n for n in ast.walk(b['main']) if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(code_text(self.old,aa),code_text(self.new,bb))
            self.assertEqual(ast.dump(aa,include_attributes=False),ast.dump(bb,include_attributes=False))
        self.assertEqual(ast.dump(handler(self.ot),include_attributes=False),ast.dump(handler(self.nt),include_attributes=False))
        self.assertEqual(ast.dump(discovery_if(self.ot),include_attributes=False),ast.dump(discovery_if(self.nt),include_attributes=False))
        # Whole-source inverse above covers cleanup/finalabsence/limits/pins/positive-growth/RC gates.

    def test_02_known_R_Z_question_and_zero_RSS_skip_liveness_old_negative_witness(self):
        text='101 101 2 Rs\n202 202 0 Zs\n404 404 3 ?\n303 303 99 R\n'
        ns,ps,fake_os=isolated_sampler(self.nt,text)
        got=ns['sample_owned']({101,202,404})
        self.assertEqual(got,dict(RSS_bytes=5120,owned_rows=[
            dict(raw='101 101 2 Rs',pid=101,pgid=101,RSS_bytes=2048,state='Rs'),
            dict(raw='202 202 0 Zs',pid=202,pgid=202,RSS_bytes=0,state='Zs'),
            dict(raw='404 404 3 ?',pid=404,pgid=404,RSS_bytes=3072,state='?')]))
        self.assertEqual(fake_os.calls,[]);self.assertEqual(len(ps.calls),1)
        old,_,old_os=isolated_sampler(self.ot,text)
        with self.assertRaisesRegex(AssertionError,'Forbidden/unconfigured'):old['sample_owned']({101,202,404})
        self.assertEqual(len(old_os.calls),1)

    def test_03_real_main_passes_known_set_and_discovery_predicate_stays_narrow(self):
        ns,_,fake_os=isolated_sampler(self.nt,'101 101 2 Rs\n202 202 0 Zs\n')
        ns.update(proc=FakeProc(),owned={202})
        fragment=ast.Module(body=[sample_assignment(self.nt)],type_ignores=[])
        exec(compile(ast.fix_missing_locations(fragment),'<real-main-call-FAKE-ONLY>','exec'),ns)
        self.assertEqual(ns['observed']['RSS_bytes'],2048);self.assertEqual(fake_os.calls,[])
        statement=discovery_if(self.nt)
        for value,expected in [((202,101,202),{202}),((202,999,202),set()),((202,101,999),set()),(None,set())]:
            with self.subTest(discovery=value):
                safe={'__builtins__':SAFE_BUILTINS,'proc':FakeProc(),'pid':202,'v':value,'owned':set()}
                exec(compile(ast.fix_missing_locations(ast.Module(body=[statement],type_ignores=[])),'<real-discovery-FAKE-ONLY>','exec'),safe)
                self.assertEqual(safe['owned'],expected)

    def test_04_missing_group_absent_live_EPERM_and_unknown_remain_distinct(self):
        for outcome,error in [(ProcessLookupError(3,'synthetic absent'),None),(None,ValueError),
                (PermissionError(1,'synthetic EPERM'),PermissionError),(OSError(5,'synthetic unknown'),OSError)]:
            with self.subTest(outcome=repr(outcome)):
                ns,_,fake_os=isolated_sampler(self.nt,'101 101 2 R\n',{202:outcome})
                if error is None:
                    got=ns['sample_owned']({101,202})
                    self.assertEqual(got['RSS_bytes'],2048)
                    self.assertEqual([x['pgid'] for x in got['owned_rows']],[101])
                elif error is ValueError:
                    with self.assertRaisesRegex(ValueError,'Live owned group has unavailable RSS'):ns['sample_owned']({101,202})
                else:
                    with self.assertRaises(error):ns['sample_owned']({101,202})
                self.assertEqual(fake_os.calls,[(202,0)])

    def test_05_empty_rows_never_become_successful_zero_RSS(self):
        ns,_,fake_os=isolated_sampler(self.nt,'',{101:ProcessLookupError(3,'synthetic absent')})
        with self.assertRaisesRegex(ValueError,'No owned RSS rows observed'):ns['sample_owned']({101})
        self.assertEqual(fake_os.calls,[(101,0)])
        ns,_,fake_os=isolated_sampler(self.nt,'',{101:PermissionError(1,'synthetic EPERM')})
        with self.assertRaises(PermissionError):ns['sample_owned']({101})
        self.assertEqual(fake_os.calls,[(101,0)])

    def test_06_malformed_known_rows_and_changed_group_refuse_before_liveness(self):
        for text,message in [('101 101 bad R\n','Missing/nonnumeric'),
                ('101 101 -1 R\n','Missing/nonnumeric'),('101 101 2\n','Missing/nonnumeric'),
                ('101 999 2 R\n','Owned direct group changed')]:
            with self.subTest(row=text):
                ns,_,fake_os=isolated_sampler(self.nt,text)
                with self.assertRaisesRegex(ValueError,message):ns['sample_owned']({101})
                self.assertEqual(fake_os.calls,[])

    def test_07_ps_failure_or_unknown_query_error_refuses_and_unowned_rows_do_not_join(self):
        for response,error in [(FakeCompleted('',7,'synthetic ps failure'),ValueError),
                (OSError(5,'synthetic ps error'),OSError)]:
            with self.subTest(response=repr(response)):
                ns,ps,fake_os=isolated_sampler(self.nt,response=response)
                with self.assertRaises(error):ns['sample_owned']({101})
                self.assertEqual(fake_os.calls,[]);self.assertEqual(len(ps.calls),1)
        ns,_,fake_os=isolated_sampler(self.nt,'303 303 not-an-owned-rss ?\n101 101 0 S\n')
        got=ns['sample_owned']({101})
        self.assertEqual(got['RSS_bytes'],0)
        self.assertEqual(got['owned_rows'],[dict(raw='101 101 0 S',pid=101,pgid=101,RSS_bytes=0,state='S')])
        self.assertEqual(fake_os.calls,[])

    def test_08_real_handler_live_adapter_retains_fatal_error_context_and_prior_stop(self):
        for prior in (None,'earlier_stop'):
            with self.subTest(prior=prior):
                result,proc,clock=handler_result(self.nt,None,prior)
                self.assertEqual(result['stop'],prior or 'resource_or_group_observation_failed')
                self.assertEqual(result['exit_races'],[])
                self.assertEqual(result['error'],dict(type='PermissionError',message='[Errno 1] synthetic EPERM',
                    phase='owned_resource_poll',operation=NEW_CALL,target_PID=None,elapsed_seconds=2.5,
                    owned_adapter_group_ID=101,owned_native_group_IDs=[202],traceback='SYNTHETIC_TRACEBACK_ONLY'))
                self.assertEqual(proc.poll_calls,1);self.assertEqual(clock.calls,1)

    def test_09_real_handler_direct_exit_race_keeps_zero_and_nonzero_raw_RC(self):
        for code in (0,1):
            with self.subTest(direct_RC=code):
                result,proc,clock=handler_result(self.nt,code)
                self.assertIsNone(result['stop']);self.assertIsNone(result['error'])
                self.assertEqual(result['exit_races'],[dict(error="PermissionError(1, 'synthetic EPERM')",
                    direct_returncode=code,elapsed_seconds=2.5,phase='owned_resource_poll',operation=NEW_CALL,
                    target_PID=None,owned_adapter_group_ID=101,owned_native_group_IDs=[202],traceback='SYNTHETIC_TRACEBACK_ONLY')])
                self.assertEqual(proc.poll_calls,1);self.assertEqual(clock.calls,1)
        # This handler only records an exit race. Final success/outerRC0 gates are not evaluated or relaxed.

    def test_10_source_drift_and_unconfigured_providers_refuse_with_no_real_fallback(self):
        for pin,text in [(OLD,self.old),(NEW,self.new)]:
            with self.subTest(pin=pin['sha256']):
                with self.assertRaisesRegex(ValueError,'Frozen first-party source identity mismatch'):
                    checked_text((text+'\n').encode(),pin)
        ns,ps,fake_os=isolated_sampler(self.nt,'')
        with self.assertRaisesRegex(AssertionError,'Forbidden/unconfigured'):ns['sample_owned']({101})
        self.assertEqual(fake_os.calls,[(101,0)])
        self.assertNotIn('__import__',ns['__builtins__']);self.assertNotIn('open',ns['__builtins__'])
        self.assertNotIn('Popen',vars(ps));self.assertEqual(set(ns)-{'__builtins__','subprocess','os'},{'group_exists','sample_owned'})


if __name__=='__main__':
    unittest.main(verbosity=2)
