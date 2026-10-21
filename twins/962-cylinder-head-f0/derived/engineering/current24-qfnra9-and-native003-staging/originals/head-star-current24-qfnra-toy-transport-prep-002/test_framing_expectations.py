"""Five HELD/UNRUN framing-only expectations; never imports transport or Z3."""

import ast
import builtins
import hashlib
from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name('check_toy_sessions.py')
EXPECTED_SHA256 = '76c13fe57d9598276b349e12dedd8bdfb1eff1ec3ad29d4c95a073abc8e6d49a'


def isolated_frame():
    raw=SOURCE.read_bytes()
    if len(raw)!=21489 or hashlib.sha256(raw).hexdigest()!=EXPECTED_SHA256:
        raise ValueError('Frozen toy transport changed')
    tree=ast.parse(raw.decode('utf-8'))
    selected=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))
              and n.name in ('ToyRefusal','need','Frame')]
    if [n.name for n in selected]!=['ToyRefusal','need','Frame']:
        raise ValueError('Exact framing fragment missing')
    permitted={name:getattr(builtins,name) for name in
        ('__build_class__','ValueError','type','str','bytes','bytearray','all','sum','len')}
    namespace={'__builtins__':permitted,'__name__':'held_frame_only','CAP':32*1024**2}
    exec(compile(ast.Module(body=selected,type_ignores=[]),'held_frame_only','exec'),namespace)
    return namespace,tree


class ToyFramingExpectations(unittest.TestCase):
    def test_01_raw_and_quoted_echo_forms_are_complete_and_retained(self):
        ns,_=isolated_frame()
        for quote in (b'',b'"'):
            with self.subTest(quote=quote):
                frame=ns['Frame']('T')
                self.assertTrue(frame.feed(quote+b'T_BEGIN'+quote+b'\nsat\n'+quote+b'T_END'+quote+b'\n'))
                self.assertEqual(frame.response(),'sat\n')
                self.assertEqual(frame.echo_form,'raw' if not quote else 'quoted')

    def test_02_split_markers_and_multiline_body_do_not_lose_bytes(self):
        ns,_=isolated_frame()
        frame=ns['Frame']('T')
        body=b'((define-fun x () Real\n  (/ 3.0 2.0)))\n'
        complete=b'T_BEGIN\n'+body+b'T_END\n'
        for byte in complete:
            frame.feed(bytes([byte]))
        self.assertEqual(frame.response().encode(),body)

    def test_03_noise_duplicate_wrong_form_and_EOF_refuse(self):
        ns,_=isolated_frame()
        for raw in (b'noise\nT_BEGIN\nsat\nT_END\n',b'T_END\n',
                    b'T_BEGIN\nT_BEGIN\n',b'T_BEGIN\nsat\n"T_END"\n',
                    b'T_BEGIN\nsat\nT_END\nunrequested\n'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                ns['Frame']('T').feed(raw)
        frame=ns['Frame']('T')
        self.assertFalse(frame.feed(b'T_BEGIN\nsat\nT_EN'))
        with self.assertRaises(ValueError):
            frame.response()

    def test_04_ceiling_refuses_without_replacing_partial_bytes(self):
        ns,_=isolated_frame()
        ns['CAP']=20
        frame=ns['Frame']('T')
        frame.feed(b'T_BEGIN\n')
        with self.assertRaises(ValueError):
            frame.feed(b'x'*21)
        self.assertEqual(bytes(frame.buffer),b'x'*21)

    def test_05_child_group_and_fixed_once_only_source_boundary(self):
        _,tree=isolated_frame()
        session=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Session')
        launch=next(n for n in session.body if isinstance(n,ast.FunctionDef) and n.name=='start')
        popen=[n for n in ast.walk(launch) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
               and isinstance(n.func.value,ast.Name) and n.func.value.id=='subprocess' and n.func.attr=='Popen']
        self.assertEqual(len(popen),1)
        kw={n.arg:n.value for n in popen[0].keywords}
        self.assertIs(kw['start_new_session'].value,False)
        self.assertFalse(any(k in kw for k in ('preexec_fn','process_group')))
        self.assertFalse(any(isinstance(n,ast.If) and '__name__' in ast.unparse(n.test) for n in tree.body))
        self.assertFalse(any(isinstance(n,ast.Import) and any(a.name=='z3' for a in n.names) for n in ast.walk(tree)))


if __name__=='__main__':
    unittest.main(defaultTest='ToyFramingExpectations',verbosity=2)
