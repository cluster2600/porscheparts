"""Degenerate-facet removal must preserve the complete represented point set."""
import importlib.util
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/exact_triangle_cleanup.py'
SPEC=importlib.util.spec_from_file_location('exact_carrier_triangle_cleanup',SOURCE)
CLEAN=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(CLEAN)


class ExactTriangleCleanupTests(unittest.TestCase):
    def test_ordinary_facets_are_not_reordered_or_changed(self):
        indices,certificate=CLEAN.cleanup_certificate([[0,1,2],[1,3,2]])
        self.assertIsNone(indices)
        self.assertEqual(certificate['removed_count'],0)

    def test_repeated_index_segment_already_in_retained_face_is_redundant(self):
        indices,certificate=CLEAN.cleanup_certificate([[0,1,2],[0,1,1]])
        self.assertEqual(indices,[0])
        self.assertTrue(certificate['all_removed_segments_covered'])
        self.assertFalse(certificate['coordinate_changes'])

    def test_uncovered_degenerate_segment_is_preserved_by_refusal(self):
        with self.assertRaises(ValueError):
            CLEAN.cleanup_certificate([[0,1,2],[1,3,3]])

    def test_isolated_degenerate_point_is_preserved_by_refusal(self):
        with self.assertRaises(ValueError):
            CLEAN.cleanup_certificate([[0,1,2],[3,3,3]])

    def test_point_already_in_a_retained_face_is_redundant(self):
        indices,certificate=CLEAN.cleanup_certificate([[0,1,2],[1,1,1]])
        self.assertEqual(indices,[0])
        self.assertTrue(certificate['all_removed_vertices_covered'])


if __name__=='__main__':unittest.main()
