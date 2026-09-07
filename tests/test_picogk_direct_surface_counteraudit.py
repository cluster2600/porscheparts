import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/picogk-local-junction'


@unittest.skipUnless(importlib.util.find_spec('numpy'), 'numpy QA runtime required')
class DirectSurfaceCounterauditTests(unittest.TestCase):
    def test_oriented_equality_includes_multiplicity_but_not_winding_reversal(self):
        import numpy as np
        sys.path.insert(0, str(SOURCE))
        try:
            from audit_direct_union_surface import oriented_face_multiset
        finally:
            sys.path.pop(0)
        triangle = np.array([[[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]])
        a = oriented_face_multiset(triangle)
        self.assertEqual(a, oriented_face_multiset(np.roll(triangle, 1, axis=1)))
        self.assertNotEqual(a, oriented_face_multiset(triangle[:, ::-1]))
        self.assertNotEqual(a, oriented_face_multiset(np.concatenate([triangle, triangle])))

    def test_roi_is_exact_and_crossing_triangle_is_not_accepted(self):
        import numpy as np
        sys.path.insert(0, str(SOURCE))
        try:
            from audit_direct_union_surface import roi_difference
        finally:
            sys.path.pop(0)
        tri = np.array([[[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]])
        same = roi_difference(tri, tri, (-1, -1, -1), (1, 1, 1))
        self.assertTrue(same['all_changed_triangle_supports_inside_convex_ROI'])
        new = tri.copy()
        new[0, 1, 0] = np.nextafter(1., 2.)
        result = roi_difference(tri, new, (-1, -1, -1), (1, 1, 1))
        self.assertFalse(result['all_changed_triangle_supports_inside_convex_ROI'])
        self.assertEqual(result['added']['unmatched_faces_not_entirely_contained_in_ROI'], 1)


if __name__ == '__main__':
    unittest.main()
