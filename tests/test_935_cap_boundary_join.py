"""Literal join and complete feature-incidence controls."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]/'docs/research/935-cap-boundary-integration-20261107/source'


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/(name+'.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class CapBoundaryJoinTests(unittest.TestCase):
    def test_literal_refined_tetrahedron_face_and_tampered_source(self):
        v = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        f = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]])
        ids = np.array([0, 2, 1]); old = dict(vertices=v[ids], source_node_ids=ids,
            source_face_rows=np.array([0]), old_triangles=np.array([[0, 1, 2]]))
        new = dict(vertices=np.vstack((v[ids], [[.25, .25, 0.]])), original_node_rows=np.arange(3),
            triangles=np.array([[0, 1, 3], [1, 2, 3], [2, 0, 3]]))
        module = load('assemble_boundary')
        result, tags, mapping = module.assemble(dict(vertices=v, triangles=f), np.array([1, 0, 0, 0]), old, new)
        self.assertTrue(np.array_equal(result['vertices'][:4].view(np.uint64), v.view(np.uint64)))
        self.assertTrue(np.array_equal(result['triangles'][:3], f[1:]))
        self.assertEqual(result['triangles'].shape, (6, 3))
        self.assertEqual(tags.tolist(), [0, 0, 0, 1, 1, 1])
        self.assertEqual(mapping.tolist(), [0, 2, 1, 4])
        with self.assertRaises(AssertionError):
            module.assemble(dict(vertices=v, triangles=f), np.array([1, 0, 0, 0]),
                            dict(old, source_face_rows=np.array([1])), new)

    def test_complete_feature_incidence_including_absent_high_word(self):
        module = load('check_boundary_join')
        f = np.array([[0, 1, 2], [1, 0, 3]], dtype=np.int64)
        keys = np.array([1, (1 << 32)+2, (7 << 32)+8], dtype=np.uint64)
        self.assertEqual(module.feature_counts(f, keys).tolist(), [2, 1, 0])

    def test_paired_cavity_face_and_same_orientation_refusal(self):
        path = Path(__file__).resolve().parents[1]/'docs/research/935-local-physics-20261105/source/inspect_tetrahedra.py'
        spec = importlib.util.spec_from_file_location('cavity_inspector', path)
        inspector = importlib.util.module_from_spec(spec); spec.loader.exec_module(inspector)
        module = load('audit_cap_cavity')
        patterns = np.array([[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]])
        cells = np.array([[0, 1, 2, 3], [0, 2, 1, 4]])
        boundary, slots = module.outer_faces(cells, patterns, inspector)
        self.assertEqual(len(boundary), 6)
        self.assertEqual(len(slots), 6)
        with self.assertRaises(AssertionError):
            module.outer_faces(np.vstack((cells[0], cells[0])), patterns, inspector)


if __name__ == '__main__':
    unittest.main()
