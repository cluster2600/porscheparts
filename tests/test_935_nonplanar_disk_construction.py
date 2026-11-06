"""Controls for one deterministic proposal and immutable provenance prefixes."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def module(name):
    path = ROOT/'docs/research/935-nonplanar-boundary-admission-20261106/source'/(name+'.py')
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class NonplanarDiskConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.constructor = module('construct_nonplanar_disk')
        cls.inspector = module('inspect_nonplanar_disk')

    def test_first_whole_disk_uses_the_literal_bowed_diagonal(self):
        legal = np.array([[0, 1, 2], [0, 2, 3], [1, 2, 3]])
        result = self.constructor.first_disk(4, legal)
        np.testing.assert_array_equal(result, [[0, 3, 2], [0, 2, 1]])
        self.inspector.check_disk(np.arange(4), result)

    def test_unfillable_disk_has_no_proposal(self):
        with self.assertRaises(AssertionError):
            self.constructor.first_disk(4, np.array([[0, 1, 2]]))

    def test_reversed_incomplete_and_outside_corner_disks_are_refused(self):
        patch = np.array([[0, 2, 1], [0, 3, 2]])
        self.inspector.check_disk(np.arange(4), patch)
        for bad in [patch[:, [0, 2, 1]], patch[:1], np.array([[0, 2, 1], [0, 4, 2]])]:
            with self.assertRaises(AssertionError):
                self.inspector.check_disk(np.arange(4), bad)

    def test_every_old_metadata_prefix_is_preserved_and_new_faces_are_inferred(self):
        parent = dict(points=np.zeros((4, 3)), triangles=np.array([[0, 1, 2]]),
                      global_node_ids=np.arange(4), inferred_surface_kind=np.array([0]),
                      source_patch_curve_ids=np.array([-1]), original_face_ids=np.array([17]),
                      unrelated_parent_channel=np.array([123]))
        snapshots = {k:v.copy() for k, v in parent.items()}
        patch = np.array([[0, 2, 3]])
        result = self.constructor.compose(parent, patch, 7)
        for key, values in snapshots.items():
            np.testing.assert_array_equal(parent[key], values)
            actual = result[key] if key in ('points', 'global_node_ids') else result[key][:len(values)]
            np.testing.assert_array_equal(actual, values)
        self.assertEqual(result['inferred_surface_kind'].tolist(), [0, 10])
        self.assertEqual(result['source_patch_curve_ids'].tolist(), [-1, 70000007])
        self.assertEqual(result['original_face_ids'].tolist(), [17, -1])
        self.assertEqual(result['unrelated_parent_channel'].tolist(), [123, -1])
        self.assertEqual(result['source_nonplanar_cap_curve_ids'].tolist(), [-1, 7])
        self.assertEqual(result['nonplanar_cap_immediate_parent_face_rows'].tolist(), [0, -1])

    def test_existing_nonplanar_birth_namespace_cannot_be_reused(self):
        parent = dict(points=np.zeros((3, 3)), triangles=np.array([[0, 1, 2]]),
                      global_node_ids=np.arange(3), inferred_surface_kind=np.array([10]))
        with self.assertRaises(AssertionError):
            self.constructor.compose(parent, np.array([[0, 2, 1]]), 4)


if __name__ == '__main__':
    unittest.main()
