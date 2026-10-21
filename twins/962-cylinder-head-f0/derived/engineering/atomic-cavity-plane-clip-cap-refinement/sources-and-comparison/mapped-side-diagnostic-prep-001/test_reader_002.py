"""Tiny stdlib tests of actual reader functions, without source import or head reads."""
import ast
from fractions import Fraction as F
import math
from pathlib import Path
import struct
import tempfile
import unittest

SOURCE=Path(__file__).with_name('reader_002.py')
tree=ast.parse(SOURCE.read_text());names={'need','sub','cross','dot','measure','selected_rows'}
module=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[])
env={'F':F,'Path':Path,'math':math,'struct':struct};exec(compile(module,str(SOURCE),'exec'),env)

class LiteralChecks(unittest.TestCase):
    def test_exact_quality_drop_and_normal_sign(self):
        t=F(1,1024);p={0:(F(0),F(0),F(0)),1:(F(1),F(0),F(0)),2:(F(0),t,F(0)),3:(F(0),-t,F(0))}
        q,d=env['measure'](p,(0,1,2),(0,1,2))
        self.assertEqual(q,3*t*t/(1+t*t)**2);self.assertLess(q,F(4,841));self.assertEqual(d,t*t)
        self.assertIsNone(env['measure'](p,(0,1,2),(0,1,1)))
        q,d=env['measure'](p,(0,1,2),(0,1,3));self.assertEqual(q,3*t*t/(1+t*t)**2);self.assertEqual(d,-t*t)
        p[2]=(F(0),F(1),F(0));self.assertEqual(env['measure'](p,(0,1,2),(0,1,2))[0],F(3,4))

    def test_degenerate_survivor_is_poor(self):
        p={0:(F(0),F(0),F(0)),1:(F(1),F(0),F(0)),2:(F(0),F(1),F(0)),3:(F(2),F(0),F(0))}
        self.assertEqual(env['measure'](p,(0,1,2),(0,1,3)),(0,0))

    def test_selected_binary_rows_and_nonfinite_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'literal.bin';header=b'962SURF1'+struct.pack('<QQ',4,2);xyz=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(0.,0.,1.)]
            faces=struct.pack('<6Q',0,1,2,0,3,1)
            p.write_bytes(header+b''.join(struct.pack('<ddd',*v) for v in xyz)+faces)
            rows,points,raw=env['selected_rows'](p,[1],4,2)
            self.assertEqual(rows,{1:(0,3,1)});self.assertEqual(set(points),{0,1,3});self.assertEqual(raw[3],struct.pack('<ddd',*xyz[3]))
            xyz[3]=(0.,0.,math.inf);p.write_bytes(header+b''.join(struct.pack('<ddd',*v) for v in xyz)+faces)
            with self.assertRaisesRegex(ValueError,'Finite'):env['selected_rows'](p,[1],4,2)

if __name__=='__main__':unittest.main()
