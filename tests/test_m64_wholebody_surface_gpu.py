import importlib.util
from pathlib import Path
import unittest


class SurfaceComparisonTests(unittest.TestCase):
    def test_nonfinite_or_zeroed_positive_area_cannot_pass(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest('numpy unavailable outside the numerical runtime')
        path = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/wholebody/audit_surface_gpu.py'
        spec = importlib.util.spec_from_file_location('surface_gpu', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(module.compare(np.array([1e-30]), np.array([1e-30]), 0)['passed'])
        self.assertFalse(module.compare(np.array([0.]), np.array([1e-30]), 0)['passed'])
        self.assertFalse(module.compare(np.array([np.nan]), np.array([np.nan]), 0)['passed'])
        with self.assertRaises(ValueError):
            module.compare(np.array([1.]), np.array([[1.]]), 0)
