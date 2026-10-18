"""Root-only tiny stdlib AST self-checks; no saved geometry or native imports."""
import ast
from fractions import Fraction
import hashlib
from pathlib import Path
import unittest

SOURCE_SHA256 = '4e6d677e11ccaa6b8a9a66b3e59b764e7e4575bb6b467bdc3dd8e5a689d22007'


class Bounds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = Path(__file__).with_name('check_balls.py').read_bytes()
        if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
            raise ValueError('Exact prepared source required')
        body = [n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)
                and n.name in {'outer_radius_squared','disjoint'}]
        if {n.name for n in body} != {'outer_radius_squared','disjoint'}:
            raise ValueError('Exact two mathematical helpers required')
        cls.f = {'Fraction':Fraction}
        exec(compile(ast.Module(body=body,type_ignores=[]),'selected-pure-bounds','exec'),cls.f)

    def test_regular_face_and_exact_isolated_threshold(self):
        r = self.f['outer_radius_squared']
        self.assertEqual(r(Fraction(2),Fraction(1)),Fraction(895,3))
        self.assertEqual(r(Fraction(29),Fraction(1)),Fraction(4,3))
        for S,T in [(0,1),(1,0),(30,1)]:
            with self.assertRaises(ValueError):r(Fraction(S),Fraction(T))
        with self.assertRaises(ValueError):r(2.,1.)

    def test_disjoint_touching_overlap_and_zero_radii(self):
        d = self.f['disjoint']
        self.assertTrue(d(Fraction(9),Fraction(1),Fraction(1)))
        self.assertFalse(d(Fraction(4),Fraction(1),Fraction(1)))
        self.assertFalse(d(Fraction(3),Fraction(1),Fraction(1)))
        self.assertFalse(d(Fraction(0),Fraction(1),Fraction(1)))
        self.assertTrue(d(Fraction(1),Fraction(0),Fraction(0)))
        with self.assertRaises(ValueError):d(Fraction(-1),Fraction(1),Fraction(1))

    def test_exact_similarity_scaling_preserves_certificate(self):
        r = self.f['outer_radius_squared']; d = self.f['disjoint']
        scale = Fraction(3,7); S,T = Fraction(2),Fraction(1)
        U = r(S,T); factor = scale*scale
        self.assertEqual(r(S*factor,T*factor*factor),U*factor)
        for D in [U,4*U,5*U]:
            self.assertEqual(d(D,U,U),d(D*factor,U*factor,U*factor))


if __name__ == '__main__':
    unittest.main()
