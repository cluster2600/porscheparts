"""An internal cavity reverses the material-side normal-turn sign."""
import importlib.util
from pathlib import Path
import unittest

try:
    import numpy as np
except ImportError:
    np = None


@unittest.skipIf(np is None, "numpy unavailable")
class VoidOrientationTests(unittest.TestCase):
    def test_convex_tetrahedron_void_has_six_material_reentrant_edges(self):
        source = Path(__file__).resolve().parents[1]/"parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/audit_void_material_side.py"
        spec = importlib.util.spec_from_file_location("material_side_audit", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        v = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        f = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
        before = f.copy()
        result = module.audit_material_side(v, f)
        self.assertEqual(result["reentrant_edges_above_degrees"]["45"], 6)
        self.assertEqual(result["reentrant_edges_above_degrees"]["90"], 3)
        self.assertEqual(result["convex_edges_above_45_degrees"], 0)
        self.assertTrue(result["input_face_orientation_reversed"])
        self.assertFalse(result["complete_material_assembly"])
        np.testing.assert_array_equal(f, before)


if __name__ == "__main__":
    unittest.main()
