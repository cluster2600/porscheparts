import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/picogk-local-junction'


@unittest.skipUnless(importlib.util.find_spec('trimesh'), 'trimesh QA runtime required')
class ExactZeroCountertrialTests(unittest.TestCase):
    def test_removes_only_exact_zero_and_preserves_inversion_failure(self):
        import numpy as np
        import trimesh
        sys.path.insert(0, str(SOURCE))
        try:
            from exact_zero_countertrial import countertrial
        finally:
            sys.path.pop(0)
        box = trimesh.creation.box()
        broken = trimesh.Trimesh(box.vertices, np.vstack([box.faces, [0, 0, 1]]), process=False)
        result = countertrial(broken)
        self.assertEqual(result['removed_zero_cross_product_faces'], 1)
        self.assertEqual(result['vertex_displacement'], 0)
        self.assertTrue(result['audit']['strict_raw_mesh_screen_pass'])
        inverted = trimesh.Trimesh(box.vertices, box.faces[:, ::-1], process=False)
        self.assertFalse(countertrial(inverted)['audit']['strict_raw_mesh_screen_pass'])

    def test_retains_small_nonzero_face_and_nonmanifold_failure(self):
        import numpy as np
        import trimesh
        sys.path.insert(0, str(SOURCE))
        try:
            from exact_zero_countertrial import countertrial
        finally:
            sys.path.pop(0)
        tiny = trimesh.Trimesh([[0, 0, 0], [1, 0, 0], [0, 1e-20, 0]], [[0, 1, 2]], process=False)
        self.assertEqual(countertrial(tiny)['removed_zero_cross_product_faces'], 0)
        box = trimesh.creation.box()
        duplicate = trimesh.Trimesh(box.vertices, np.vstack([box.faces, box.faces[:1]]), process=False)
        result = countertrial(duplicate)
        self.assertEqual(result['remaining_duplicate_face_groups'], 1)
        self.assertFalse(result['audit']['strict_raw_mesh_screen_pass'])


if __name__ == '__main__':
    unittest.main()
