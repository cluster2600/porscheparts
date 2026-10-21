"""Prepared tiny array tests only; no head inputs, native query or controller."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec = importlib.util.spec_from_file_location('held_coordinate_masks', Path(__file__).with_name('prepare_masks.py'))
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
module.np = np


class CoordinateMaskTests(unittest.TestCase):
    def points(self):
        return np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.],
                         [0., 0., 1.], [2., 0., 0.]], dtype='<f8')

    def keys(self, points, faces):
        return module.face_keys(points, np.array(faces, dtype='<u8'))

    def test_unequal_counts_complete_intersection_and_duplicate_refusal(self):
        p = self.points()
        a = self.keys(p, [[0, 1, 2], [0, 2, 3]])
        b = self.keys(p, [[0, 2, 3], [0, 3, 4], [0, 1, 2]])
        left, right, common = module.masks_from_keys(a, b)
        np.testing.assert_array_equal(left, [True, True])
        np.testing.assert_array_equal(right, [True, False, True])
        self.assertEqual(len(common), 2)
        np.testing.assert_array_equal(np.flatnonzero(~right), [1])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            module.masks_from_keys(np.concatenate((a, a[:1])), b)

    def test_cyclic_orientation_and_source_row_permutation(self):
        p = self.points()
        a = self.keys(p, [[0, 1, 2], [0, 2, 3]])
        b = self.keys(p, [[2, 3, 0], [1, 2, 0]])
        left, right, common = module.masks_from_keys(a, b)
        self.assertTrue(left.all() and right.all()); self.assertEqual(len(common), 2)

    def test_reversal_remains_in_each_changed_source(self):
        p = self.points()
        a = self.keys(p, [[0, 1, 2]])
        b = self.keys(p, [[0, 2, 1]])
        left, right, common = module.masks_from_keys(a, b)
        self.assertFalse(left.any() or right.any()); self.assertEqual(len(common), 0)
        np.testing.assert_array_equal(np.flatnonzero(~left), [0])
        np.testing.assert_array_equal(np.flatnonzero(~right), [0])

    def test_signed_zero_only_is_normalized_without_tolerance(self):
        p = self.points(); q = p.copy(); q[q == 0] = -0.0
        a = self.keys(p, [[0, 1, 2]])
        b = self.keys(q, [[1, 2, 0]])
        left, right, common = module.masks_from_keys(a, b)
        self.assertTrue(left.all() and right.all()); self.assertEqual(len(common), 1)
        q[0, 2] = np.nextafter(0., 1.)
        b = self.keys(q, [[1, 2, 0]])
        left, right, common = module.masks_from_keys(a, b)
        self.assertFalse(left.any() or right.any()); self.assertEqual(len(common), 0)


if __name__ == '__main__':
    unittest.main()
