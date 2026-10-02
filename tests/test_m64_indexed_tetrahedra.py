"""Cross-check the bounded array audit against the independent scalar audit."""
import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source'
sys.path.insert(0, str(SOURCE))
sys.path.insert(0, str(SOURCE/'wholebody'))
import mesh_native_ported_head as native


@unittest.skipUnless(importlib.util.find_spec('numpy') and importlib.util.find_spec('scipy'),
                     'optional indexed NumPy/SciPy runtime')
class IndexedTetrahedraTests(unittest.TestCase):
    def test_matches_scalar_witnesses_without_repairing_or_mutating(self):
        import numpy as np
        from audit_indexed_tetrahedra import connectivity_metrics
        points = np.array([(0.,0.,0.), (1.,0.,0.), (0.,1.,0.), (0.,0.,1.),
                           (0.,0.,-1.), (0.,0.,2.), (3.,0.,0.), (4.,0.,0.),
                           (3.,1.,0.), (3.,0.,1.)])
        skin = [(2,1,0), (0,1,3), (3,2,0), (1,2,3)]
        cases = [([(0,1,2,3)], skin), ([(0,2,1,3)], skin),
            ([(0,1,2,3)], skin[:-1]), ([(0,1,2,3)], skin+[skin[0]]),
            ([(0,1,2,3)], skin+[(0,1,4)]), ([(0,1,2,3)], []),
            ([(0,1,2,2)], skin), ([(0,1,2,3)]*2, skin),
            ([(0,1,2,3), (0,2,1,4)], [(0,1,3),(0,2,3),(1,2,3),(0,1,4),(0,2,4),(1,2,4)]),
            ([(0,1,2,3), (0,2,1,4), (0,1,2,5)], skin),
            ([(0,1,2,3), (6,7,8,9)], skin+[(6,7,8),(6,7,9),(6,8,9),(7,8,9)])]
        for cells, triangles in cases:
            with self.subTest(cells=cells, triangles=triangles):
                c = np.array(cells, dtype=np.int64)
                f = np.array(triangles, dtype=np.int64).reshape(-1,3)
                before = (points.tobytes(), c.tobytes(), f.tobytes())
                expected = native.connectivity_metrics(dict(enumerate(map(tuple, points))), cells, triangles)
                self.assertEqual(connectivity_metrics(points, c, f), expected)
                self.assertEqual(before, (points.tobytes(), c.tobytes(), f.tobytes()))
        with self.subTest(tiny_positive_and_inverted_tetrahedra=True):
            tiny = points*1e-12
            for cell in ((0,1,2,3), (0,2,1,3)):
                self.assertEqual(connectivity_metrics(tiny, np.array([cell]), np.array(skin)),
                    native.connectivity_metrics(dict(enumerate(map(tuple,tiny))), [cell], skin))

    def test_chunk_boundary_preserves_one_inversion_and_nonmanifold_counts(self):
        import numpy as np
        from audit_indexed_tetrahedra import connectivity_metrics
        points = np.array([(0.,0.,0.), (1.,0.,0.), (0.,1.,0.), (0.,0.,1.)])
        cells = np.tile([0,1,2,3], (100_001,1))
        cells[-1] = [0,2,1,3]
        faces = np.array([(2,1,0),(0,1,3),(3,2,0),(1,2,3)])
        expected = native.connectivity_metrics(dict(enumerate(map(tuple,points))), cells.tolist(), faces.tolist())
        self.assertEqual(connectivity_metrics(points,cells,faces), expected)
        self.assertEqual(expected['count_negative'], 1)
        self.assertEqual(expected['nonmanifold_faces'], 4)

    def test_rejects_invalid_references_and_nonfinite_coordinates(self):
        import numpy as np
        from audit_indexed_tetrahedra import connectivity_metrics
        points = np.array([(0.,0.,0.), (1.,0.,0.), (0.,1.,0.), (0.,0.,1.)])
        c, f = np.array([[0,1,2,3]]), np.array([[0,1,2]])
        for p, cells, faces in ((points, c.astype(float), f), (points, c-1, f),
                (points, c+1, f), (points, c, f-1), (points, c, f+4),
                (points, c[:0], f), (points*np.nan, c, f),
                (points, c.astype(np.uint64)+2**32, f)):
            with self.subTest(cells=cells, faces=faces):
                with self.assertRaises(ValueError):
                    connectivity_metrics(p, cells, faces)


if __name__ == '__main__':
    unittest.main()
