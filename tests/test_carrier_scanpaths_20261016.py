"""Exposure endpoints inside the part must not hide a segment crossing a hole."""
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'parts/993-eng-carrier-0001/source/process-slicing-20261016'
sys.path.insert(0, str(SOURCE))
try:
    import numpy as np
    from audit_scanpaths import layer_check, section_domain, segments_check
except ImportError:
    np = None


@unittest.skipIf(np is None, 'Native NumPy/Shapely runtime required')
class CarrierScanpathTests(unittest.TestCase):
    def rings(self):
        return [np.array([[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]),
                np.array([[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]])]

    def test_full_segment_crossing_hole_is_rejected_despite_valid_endpoints(self):
        domain = section_domain(self.rings())
        result = segments_check(np.array([[[1, 5], [9, 5]]]), domain)
        self.assertFalse(result['passed'])
        self.assertEqual(result['segments_not_covered'], 1)
        self.assertEqual(result['outside_length_mm'], 2)

    def test_interior_and_boundary_segments_pass(self):
        domain = section_domain(self.rings())
        result = segments_check(np.array([[[1, 1], [9, 1]], [[0, 0], [10, 0]]]), domain)
        self.assertTrue(result['passed'])

    def test_duplicate_reverse_and_zero_segments_are_rejected(self):
        domain = section_domain(self.rings())
        result = segments_check(np.array([[[1, 1], [9, 1]], [[9, 1], [1, 1]], [[2, 2], [2, 2]]]), domain)
        self.assertFalse(result['passed'])
        self.assertEqual(result['exact_duplicate_segments'], 1)
        self.assertEqual(result['zero_length_segments'], 1)

    def test_odd_even_nesting_preserves_hole_and_inner_island(self):
        outer, _ = self.rings()
        hole = np.array([[2, 2], [8, 2], [8, 8], [2, 8], [2, 2]])
        island = np.array([[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]])
        self.assertEqual(section_domain([island, outer[::-1], hole]).area, 68)

    def test_crossing_or_open_rings_are_rejected(self):
        rings = self.rings()
        with self.assertRaisesRegex(ValueError, 'Open section ring'):
            section_domain([rings[0][:-1]])
        with self.assertRaisesRegex(ValueError, 'Crossing or duplicate'):
            section_domain([rings[0], rings[0] + [5, 0]])

    def test_area_mismatch_is_separate_from_exposure_coverage(self):
        rings = self.rings()
        data = {'part_boundary_points_mm': np.concatenate(rings), 'part_boundary_offsets': np.array([0, 5, 10]),
                'part_scan_contour_points_mm': np.empty((0, 2)), 'part_scan_contour_offsets': np.array([0]),
                'part_hatch_segments_mm': np.array([[[1, 1], [9, 1]]])}
        self.assertTrue(layer_check(data, 96)['passed'])
        result = layer_check(data, 100)
        self.assertFalse(result['area_pass'])
        self.assertTrue(result['hatches']['passed'])


if __name__ == '__main__':
    unittest.main()
