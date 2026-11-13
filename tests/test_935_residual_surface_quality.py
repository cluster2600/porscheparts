"""Literal dimensional controls for the read-only residual surface audit."""
import importlib.util
from fractions import Fraction
from pathlib import Path
import unittest


class ResidualQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1]/'docs/research/935-residual-surface-audit-20261107/source/audit_residual_surface.py'
        spec = importlib.util.spec_from_file_location('residual_surface', path)
        cls.audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.audit)

    def test_literal_area_and_refusal_controls(self):
        self.assertTrue(all(self.audit.controls().values()))

    def test_binary_coordinate_perturbation_is_not_rounded_flat(self):
        epsilon = 2.**-44
        # The projected right triangle has area 1/2; its 3-D area is larger.
        result = self.audit.quality_squared([[0., 0, 0], [1., 0, 0], [0., 1, epsilon]])
        e2 = Fraction(1, 1 << 88)
        self.assertEqual(result, 12*(1+e2)/(4+2*e2)**2)
        self.assertNotEqual(result, Fraction(3, 4))
