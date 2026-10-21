"""Root-only tiny stdlib AST checks; no saved rows/native/scientific imports."""
import ast
from fractions import Fraction
from itertools import permutations
from math import isqrt
import hashlib
from pathlib import Path
import unittest

SOURCE_SHA256='af4762323b2c839a7987b1d0b3bd56e01f61368d21c6957770e68eed14ff9ccd'


class Pair(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw=Path(__file__).with_name('check_pair.py').read_bytes()
        if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:raise ValueError('Exact prepared source required')
        names={'subtract','dot','cross','sqrt_interval','disjoint','enclosing_ball'}
        body=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names]
        if {n.name for n in body}!=names:raise ValueError('Exact selected mathematical helpers required')
        cls.f={'Fraction':Fraction,'isqrt':isqrt,'BITS':106}
        exec(compile(ast.Module(body=body,type_ignores=[]),'selected-rational-pair-functions','exec'),cls.f)
        cls.points=[[Fraction(x) for x in p] for p in [(0,0,0),(1,0,0),(0,1,0),(0,0,1)]]

    def test_sqrt_perfect_nonperfect_negative(self):
        f=self.f['sqrt_interval'];p=f(Fraction(9,4));self.assertEqual((p['lo'],p['hi']),(Fraction(3,2),Fraction(3,2)))
        p=f(Fraction(2));self.assertLess(p['lo']**2,2);self.assertGreater(p['hi']**2,2)
        self.assertEqual(p['hi']-p['lo'],Fraction(1,1<<106))
        with self.assertRaises(ValueError):f(Fraction(-1))
        with self.assertRaises(ValueError):f(2.)

    def test_known_positive_right_tetra_target_inside_enclosure(self):
        # Exact ideal-reference Q²=18/[(9/2)*6]=2/3 >1/100.
        self.assertEqual(Fraction(18)/(Fraction(9,2)*6),Fraction(2,3))
        self.assertGreater(Fraction(2,3),Fraction(1,100))
        b=self.f['enclosing_ball'](self.points,3)
        distance=sum((x-y)**2 for x,y in zip(self.points[3],b['rational_ball_centre_mm']))
        self.assertLessEqual(distance,b['squared_radius_upper_mm2'])

    def test_even_native_corner_permutations_and_side_invariance(self):
        original=self.f['enclosing_ball'](self.points,3)
        checked=0
        for order in permutations(range(4)):
            parity=sum(order[i]>order[j] for i in range(4) for j in range(i+1,4))%2
            if parity:continue
            b=self.f['enclosing_ball']([self.points[i] for i in order],order.index(3));checked+=1
            self.assertEqual(b['rational_ball_centre_mm'],original['rational_ball_centre_mm'])
            self.assertEqual(b['squared_radius_upper_mm2'],original['squared_radius_upper_mm2'])
        self.assertEqual(checked,12)
        with self.assertRaises(ValueError):self.f['enclosing_ball']([self.points[i] for i in [0,2,1,3]],3)

    def test_touching_is_not_strict_disjointness(self):
        d=self.f['disjoint']
        self.assertFalse(d(Fraction(4),Fraction(1),Fraction(1)))
        self.assertTrue(d(Fraction(9),Fraction(1),Fraction(1)))


if __name__=='__main__':unittest.main()
