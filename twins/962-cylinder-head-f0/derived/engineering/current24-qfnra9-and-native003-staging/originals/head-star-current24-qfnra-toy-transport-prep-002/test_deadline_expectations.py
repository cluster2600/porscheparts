"""Four HELD/UNRUN real-method expectations, fake clocks/streams/process only.

No transport import, selector, pipe, process, sleep, solver or runtime query.
Only exact pinned exchange/close definitions are compiled in a FUTURE guard call.
"""

import ast
import builtins
import hashlib
from pathlib import Path
from types import SimpleNamespace
import unittest


SOURCE = Path(__file__).with_name('check_toy_sessions.py')
EXPECTED_SHA256 = '76c13fe57d9598276b349e12dedd8bdfb1eff1ec3ad29d4c95a073abc8e6d49a'


def source_tree():
    raw=SOURCE.read_bytes()
    if len(raw)!=21489 or hashlib.sha256(raw).hexdigest()!=EXPECTED_SHA256:
        raise ValueError('Frozen toy transport changed')
    return ast.parse(raw.decode('utf-8'))


class FakeProcess:
    def __init__(self,clock,wait_finish=None):
        self.pid=123
        self.running=True
        self.returncode=None
        self.clock=clock
        self.wait_finish=wait_finish
        self.signals=[]
        self.stdin=SimpleNamespace(closed=False)
        self.stdin.close=lambda:setattr(self.stdin,'closed',True)
    def poll(self):
        return None if self.running else 0
    def wait(self,timeout):
        if self.running:
            raise ValueError('Fake wait attempted on a running child')
        if self.wait_finish is not None:
            self.clock.now=max(self.clock.now,self.wait_finish)
        self.returncode=0
        return 0
    def terminate(self):
        self.signals.append('terminate')
    def kill(self):
        self.signals.append('kill')


def isolated_session(clock,serialization_finish=None,wait_finish=None):
    tree=source_tree()
    original=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Session')
    methods=[n for n in original.body if isinstance(n,ast.FunctionDef) and n.name in ('exchange','close')]
    if [n.name for n in methods]!=['exchange','close']:
        raise ValueError('Exactly two pinned Session methods required')
    selected=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in ('ToyRefusal','need')]
    shell=ast.copy_location(ast.ClassDef(name='Session',bases=[],keywords=[],body=methods,decorator_list=[]),original)
    selected.append(shell)
    permitted={name:getattr(builtins,name) for name in
        ('__build_class__','ValueError','BaseException','KeyError','type','str','list','bytes','bytearray',
         'all','bool','len','min','max','getattr','repr')}
    ns={'__builtins__':permitted,'__name__':'held_deadline_only','QUERY_SECONDS':5,'TERM_SECONDS':8,'KILL_SECONDS':8,
        'time':SimpleNamespace(monotonic=lambda:clock.now),
        'traceback':SimpleNamespace(format_exc=lambda:'synthetic traceback'),
        'Frame':lambda tag:SimpleNamespace(state='before',echo_form='raw',response=lambda:'sat\n')}
    exec(compile(ast.fix_missing_locations(ast.Module(body=selected,type_ignores=[])),
                 'held_deadline_only','exec'),ns)
    session=ns['Session']()
    session.proc=FakeProcess(clock,wait_finish)
    session.phase='sat'
    session.check_count=1
    session.ordinal=0
    session.toy={'ID':'rational'}
    session.session_id='toy_rational'
    session.deadline=60
    session.pending=bytearray()
    session.eof=set()
    session.cleanup=[]
    session.transcript=object()
    session.selector=SimpleNamespace(register=lambda *args:None,unregister=lambda *args:None)
    session.protocol=SimpleNamespace(parse_sexpr=lambda text:['get-model'])
    records=[]
    def record(handle,value):
        records.append(value)
        if value['event']=='response' and serialization_finish is not None:
            clock.now=max(clock.now,serialization_finish)
    session.capture=SimpleNamespace(record=record)
    return session,records,ns


class ToyDeadlineExpectations(unittest.TestCase):
    def test_01_query_full_response_and_serialization_are_inside_original_until(self):
        for deadline,pump_finish,serialization_finish,refuse in ((60,4.99,4.999,False),(60,5,5,True),
                (60,5.1,5.1,True),(60,4,5,True),(60,4,5.1,True),(4,4,4,True)):
            with self.subTest(deadline=deadline,pump_finish=pump_finish,serialization_finish=serialization_finish):
                clock=SimpleNamespace(now=0)
                session,records,_=isolated_session(clock,serialization_finish)
                session.deadline=deadline
                def pump(until,cleanup=False):
                    self.assertEqual(until,min(deadline,5))
                    clock.now=pump_finish
                    session.pending.clear()
                    session.frame.state='done'
                session.pump=pump
                if refuse:
                    with self.assertRaisesRegex(ValueError,'Query full-return deadline'):
                        session.exchange('model','(get-model)')
                else:
                    self.assertEqual(session.exchange('model','(get-model)'),'sat\n')
                self.assertEqual([r['event'] for r in records],['request','response'])
                self.assertEqual(records[-1]['complete_response'],'sat\n')

    def test_02_normal_drain_retains_late_final_pump_or_wait_as_refusal(self):
        for pump_finish,wait_finish,refuse in ((4.9,4.99,False),(5,5,True),(4,5,True),(4,5.1,True)):
            with self.subTest(pump_finish=pump_finish,wait_finish=wait_finish):
                clock=SimpleNamespace(now=0)
                session,_,_=isolated_session(clock,wait_finish=wait_finish)
                def pump(until,cleanup=False):
                    self.assertFalse(cleanup)
                    self.assertEqual(until,5)
                    clock.now=pump_finish
                    session.proc.running=False
                    session.eof={'stdout','stderr'}
                session.pump=pump
                session.close(normal=True)
                self.assertEqual(session.proc.returncode,0)
                self.assertEqual(session.proc.signals,[])
                if refuse:
                    self.assertEqual(session.cleanup[0]['stage'],'normal_drain')
                    self.assertIn('Normal drain full-return deadline',session.cleanup[0]['error'])
                else:
                    self.assertEqual(session.cleanup,[])

    def test_03_cleanup_TERM_and_KILL_late_return_errors_are_retained(self):
        for late_stage in ('terminate','kill'):
            with self.subTest(late_stage=late_stage):
                clock=SimpleNamespace(now=0)
                session,_,ns=isolated_session(clock)
                calls=[]
                def pump(until,cleanup=False):
                    self.assertTrue(cleanup)
                    calls.append(until)
                    clock.now=until
                    if late_stage=='kill' and len(calls)==1:
                        raise ns['ToyRefusal']('synthetic TERM drain failure')
                    session.proc.running=False
                    session.eof={'stdout','stderr'}
                session.pump=pump
                session.close(normal=False)
                self.assertEqual(calls,[8] if late_stage=='terminate' else [8,16])
                self.assertEqual(session.cleanup[-1]['stage'],late_stage)
                self.assertIn('Cleanup '+late_stage+' full-return deadline',session.cleanup[-1]['error'])
                self.assertEqual(session.proc.signals,['terminate'] if late_stage=='terminate' else ['terminate','kill'])
                self.assertEqual(session.proc.returncode,0)

    def test_04_final_checks_follow_complete_capture_or_wait_and_keep_original_until(self):
        tree=source_tree()
        session=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Session')
        exchange=next(n for n in session.body if isinstance(n,ast.FunctionDef) and n.name=='exchange')
        close=next(n for n in session.body if isinstance(n,ast.FunctionDef) and n.name=='close')
        self.assertIsInstance(exchange.body[-1],ast.Return)
        self.assertEqual(ast.unparse(exchange.body[-2]),
            "need(time.monotonic() < until, 'Query full-return deadline expired after response/transcript capture')")
        self.assertIn('self.capture.record(self.transcript',ast.unparse(exchange.body[-3]))
        normal=next(n for n in close.body if isinstance(n,ast.Try)).body[0]
        self.assertIsInstance(normal,ast.If)
        self.assertEqual(ast.unparse(normal.body[-2]),
            "need(time.monotonic() < until, 'Normal drain full-return deadline expired')")
        loop=next(n for n in close.body if isinstance(n,ast.For))
        self.assertIsInstance(loop.body[0].body[-1],ast.Break)
        self.assertEqual(ast.unparse(loop.body[0].body[-2]),
            "need(time.monotonic() < until, 'Cleanup %s full-return deadline expired' % name)")
        self.assertEqual(sum(isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='until'
                             for t in n.targets) for n in ast.walk(exchange)),1)
        self.assertEqual(sum(isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='until'
                             for t in n.targets) for n in ast.walk(close)),2)


if __name__=='__main__':
    unittest.main(defaultTest='ToyDeadlineExpectations',verbosity=2)
