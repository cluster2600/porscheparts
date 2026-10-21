"""Prepared tiny plane-classification check only; no head array or native call."""
import ast
from pathlib import Path
import unittest

import numpy as np


class PlaneClassification(unittest.TestCase):
    def test_exact_plane_partition_including_signed_zero(self):
        source = Path(__file__).with_name('reader.py')
        definitions = [node for node in ast.parse(source.read_text()).body
                       if isinstance(node, ast.FunctionDef) and node.name == 'plane_classes']
        self.assertEqual(len(definitions), 1)
        namespace = {'np': np}
        exec(compile(ast.Module(body=definitions, type_ignores=[]), str(source), 'exec'), namespace)
        points = np.array([[0., 0., -0.], [1., 0., 0.], [0., 1., 0.],
                           [0., 0., 1.], [1., 0., 1.], [0., 1., 1.]])
        faces = np.array([[0, 1, 2], [0, 1, 3], [0, 3, 4], [3, 4, 5]], dtype=np.uint64)
        masks = namespace['plane_classes'](points, faces)
        self.assertEqual(masks['cap_all_z0'].tolist(), [True, False, False, False])
        self.assertEqual(masks['noncap_mixed_plane_vertices'].tolist(), [False, True, True, False])
        self.assertEqual(masks['noncap_no_plane_vertices'].tolist(), [False, False, False, True])
        self.assertTrue(np.all(sum(masks.values()) == 1))


if __name__ == '__main__':
    unittest.main()
