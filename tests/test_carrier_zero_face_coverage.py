"""Exact set coverage, including gaps invisible to endpoint-only checks."""
from pathlib import Path
import importlib.util
import unittest
try:
    import numpy as np
except ImportError:
    np = None

if np is not None:
    source = Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/exact_zero_face_coverage.py'
    spec = importlib.util.spec_from_file_location('carrier_zero_face_coverage', source)
    coverage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(coverage)


@unittest.skipUnless(np is not None, 'Optional NumPy runtime required')
class ZeroFaceCoverage(unittest.TestCase):
    def audit(self, vertices, faces):
        return coverage.certify_zero_face_coverage(np.array(vertices, dtype=np.float64),
                                                   np.array(faces, dtype=np.int64), [0])

    def test_whole_segment_is_covered_by_union_of_two_triangles(self):
        result = self.audit([[0, 0], [2, 0], [1, 0], [0, 1], [2, 1]],
                            [[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['per_face'][0]['union_closed_parameter_intervals'],
                         [[['0', '1'], ['1', '1']]])

    def test_covered_endpoints_do_not_hide_uncovered_middle(self):
        result = self.audit([[0, 0], [2, 0], [1, 0], [.5, 0], [0, 1], [1.5, 0], [2, 1]],
                            [[0, 1, 2], [0, 3, 4], [5, 1, 6]])
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['per_face'][0]['union_closed_parameter_intervals'],
                         [[['0', '1'], ['1', '4']], [['3', '4'], ['1', '1']]])

    def test_other_degenerate_faces_cannot_cover_a_segment(self):
        result = self.audit([[0, 0], [2, 0], [1, 0]], [[0, 1, 2], [2, 1, 0]])
        self.assertEqual(result['status'], 'rejected')

    def test_point_on_triangle_is_covered_but_off_plane_point_is_not(self):
        inside = self.audit([[.25, .25, 0], [0, 0, 0], [1, 0, 0], [0, 1, 0]],
                            [[0, 0, 0], [1, 2, 3]])
        outside = self.audit([[.25, .25, np.nextafter(0., 1.)], [0, 0, 0], [1, 0, 0], [0, 1, 0]],
                             [[0, 0, 0], [1, 2, 3]])
        self.assertEqual(inside['status'], 'passed')
        self.assertEqual(outside['status'], 'rejected')

    def test_transverse_point_intersection_does_not_cover_whole_segment(self):
        result = self.audit([[.25, .25, -1], [.25, .25, 1], [.25, .25, 0],
                             [0, 0, 0], [1, 0, 0], [0, 1, 0]],
                            [[0, 1, 2], [3, 4, 5]])
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['per_face'][0]['union_closed_parameter_intervals'],
                         [[['1', '2'], ['1', '2']]])

    def test_positive_area_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'positive exact area'):
            self.audit([[0, 0], [1, 0], [0, 1]], [[0, 1, 2]])


if __name__ == '__main__':
    unittest.main()
