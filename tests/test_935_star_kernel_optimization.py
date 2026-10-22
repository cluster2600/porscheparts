"""Exercise the analytic star kernel and the fixed-boundary/exact-orientation guards."""
import importlib.util
import math
from pathlib import Path
import sys
import unittest

try:
    import numpy as np
    import scipy
except ImportError:
    np = None
SOURCE = Path(__file__).resolve().parents[1] / 'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location('star_kernel_optimization', SOURCE / 'optimize_interior_stars.py')
module = importlib.util.module_from_spec(spec)
if np is not None:
    spec.loader.exec_module(module)


@unittest.skipIf(np is None, 'NumPy/SciPy unavailable')
class StarKernelTests(unittest.TestCase):
    def star(self):
        v = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1e-7, .1, .1]])
        f = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
        return v, np.column_stack((np.full(4, 4), f)), f

    def test_right_tetrahedron_kernel_has_the_analytic_incenter(self):
        v, c, _ = self.star()
        target = module.kernel_target(v, c, 4)
        np.testing.assert_allclose(target, np.full(3, 1 / (3 + math.sqrt(3))), rtol=0, atol=1e-8)

    def test_quality_improves_with_exact_volume_and_fixed_boundary(self):
        v, c, f = self.star(); before = v.copy()
        xyz, moves = module.optimize(v, c, f)
        np.testing.assert_array_equal(v, before)
        np.testing.assert_array_equal(xyz[:4], v[:4])
        self.assertTrue(moves)
        self.assertGreater(module.quality(xyz[c]).min(), module.quality(v[c]).min())
        exact = module.exact_orientation(xyz, c)
        self.assertEqual(exact['negative'], 0); self.assertEqual(exact['zero'], 0)
        self.assertEqual(exact['signed_volume_exact'], '1/6')

    def test_boundary_only_mesh_is_unchanged_and_inverted_star_is_refused(self):
        v, c, f = self.star()
        outer, moves = module.optimize(v[:4], np.array([[0, 1, 2, 3]]), f)
        np.testing.assert_array_equal(outer, v[:4]); self.assertEqual(moves, [])
        c[:, [1, 2]] = c[:, [2, 1]]
        self.assertIsNone(module.quality(v[c]))
        with self.assertRaises(ValueError): module.kernel_target(v, c, 4)
