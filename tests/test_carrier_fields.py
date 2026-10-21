"""Check real integration-point mapping and the metric orthographic camera."""
import importlib.util
from pathlib import Path
import unittest


@unittest.skipUnless(importlib.util.find_spec('numpy') and importlib.util.find_spec('matplotlib'),
                     'Optional plotting runtime required')
class CarrierFieldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        cls.np = np
        path = Path(__file__).resolve().parents[1] / 'scripts/render_carrier_fields.py'
        spec = importlib.util.spec_from_file_location('carrier_field_renderer', path)
        cls.renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.renderer)

    def test_boundary_colour_uses_own_element_peak(self):
        values = self.renderer.boundary_values(self.np.array([[1, 2, 3], [2, 3, 5]]),
            {10: [1, 2, 3, 4], 20: [2, 3, 4, 5]}, self.np.array([20, 10, 10, 20, 10, 20, 10, 20]),
            self.np.array([5., 1., 2., 6., 3., 7., 4., 8.]))
        self.np.testing.assert_array_equal(values, [4., 8.])

    def test_internal_declared_surface_face_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'internal to two elements'):
            self.renderer.boundary_values(self.np.array([[2, 3, 4]]),
                {10: [1, 2, 3, 4], 20: [2, 3, 4, 5]}, self.np.array([10, 20]), self.np.array([4., 8.]))

    def test_orthographic_basis_is_metric_and_depth_is_independent(self):
        basis = self.renderer.camera_basis()
        self.np.testing.assert_allclose(basis @ basis.T, self.np.eye(3), atol=1e-14)
        uv, depth = self.renderer.project(basis, basis)
        self.np.testing.assert_allclose(uv, [[1, 0], [0, 1], [0, 0]], atol=1e-14)
        self.np.testing.assert_allclose(depth, [0, 0, 1], atol=1e-14)


if __name__ == '__main__':
    unittest.main()
