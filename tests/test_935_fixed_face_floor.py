"""Literal sharpness and orientation controls for the boundary quality bound."""
from fractions import Fraction
import importlib.util
from pathlib import Path
import unittest


class FixedFaceFloorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo = Path(__file__).resolve().parents[1]
        for attribute, path in [('bound', repo/'docs/research/935-global-quality-continuation-20261107/source/certify_face_floor.py'),
                                ('exact', repo/'docs/research/935-condition-directed-20261105/source/verify_surface_peels.py')]:
            spec = importlib.util.spec_from_file_location(attribute, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            setattr(cls, attribute, module)

    def test_literal_sharp_and_nonoptimal_controls(self):
        self.assertTrue(all(self.bound.controls(self.exact).values()))

    def test_quality_bound_is_orientation_invariant(self):
        points = [[0., 0, 0], [1., 0, 0], [0., 1, 0], [0., 0, 1]]
        direct = self.bound.tetra_face_bound(points, self.exact)
        reverse = self.bound.tetra_face_bound([points[i] for i in (0, 2, 1, 3)], self.exact)
        self.assertEqual(direct['q_face_squared'], Fraction(3, 4))
        self.assertEqual(direct['q_tet_cubed'], reverse['q_tet_cubed'])
        self.assertEqual(direct['determinant'], -reverse['determinant'])
