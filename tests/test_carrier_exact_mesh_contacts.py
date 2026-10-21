"""A shared simplex is allowed; further intersection of adjacent faces is not."""
import importlib.util
import math
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/classify_mesh_contacts.py'
spec=importlib.util.spec_from_file_location('carrier_exact_contacts',SOURCE)
contact=importlib.util.module_from_spec(spec);spec.loader.exec_module(contact)


class CarrierExactMeshContactTests(unittest.TestCase):
    def test_shared_point_only_is_allowed(self):
        points=[(0,0,0),(2,0,0),(0,2,0),(-1,0,0),(0,-1,0)]
        result=contact.classify_pair(points,(0,1,2),(0,3,4))
        self.assertEqual(result['kind'],'point')
        self.assertTrue(result['intersection_only_in_shared_topological_simplex'])

    def test_shared_edge_only_is_allowed(self):
        for third in ((0,-2,0),(0,0,2)):
            points=[(0,0,0),(2,0,0),(0,2,0),third]
            result=contact.classify_pair(points,(0,1,2),(1,0,3))
            self.assertEqual(result['kind'],'segment')
            self.assertTrue(result['intersection_only_in_shared_topological_simplex'])

    def test_crossing_beyond_shared_vertex_remains_rejected(self):
        points=[(0,0,0),(2,0,0),(0,2,0),(1,1,1),(1,1,-1)]
        result=contact.classify_pair(points,(0,1,2),(0,3,4))
        self.assertEqual(result['kind'],'segment')
        self.assertFalse(result['intersection_only_in_shared_topological_simplex'])
        self.assertIn([1.,1.,0.],result['intersection_points_float_mm'])

    def test_positive_coplanar_area_remains_rejected(self):
        points=[(0,0,0),(2,0,0),(0,2,0),(.25,.25,0),(1,.25,0),(.25,1,0)]
        result=contact.classify_pair(points,(0,1,2),(3,4,5))
        self.assertEqual(result['kind'],'coplanar_area')
        self.assertFalse(result['intersection_only_in_shared_topological_simplex'])
        self.assertEqual(result['projected_intersection_area_mm2'],.28125)

    def test_shared_edge_does_not_hide_positive_area_overlap(self):
        points=[(0,0,0),(2,0,0),(0,2,0),(0,1,0)]
        result=contact.classify_pair(points,(0,1,2),(1,0,3))
        self.assertEqual(result['kind'],'coplanar_area')
        self.assertFalse(result['intersection_only_in_shared_topological_simplex'])
        self.assertEqual(result['projected_intersection_area_mm2'],1.)

    def test_positive_area_below_float_display_range_is_still_rejected(self):
        tiny=math.nextafter(0.,1.)
        points=[(0,0,0),(1,0,0),(0,1,0),(-1,tiny,0),(1,tiny,0)]
        result=contact.classify_pair(points,(0,1,2),(0,3,4))
        self.assertEqual(result['kind'],'coplanar_area')
        self.assertFalse(result['intersection_only_in_shared_topological_simplex'])
        self.assertNotEqual(result['projected_area_exact_ratio'][0],'0')

    def test_geometrically_shared_but_distinct_indices_are_not_ignored(self):
        points=[(0,0,0),(2,0,0),(0,2,0),(0,0,0),(-1,0,0),(0,-1,0)]
        result=contact.classify_pair(points,(0,1,2),(3,4,5))
        self.assertEqual(result['kind'],'point')
        self.assertFalse(result['intersection_only_in_shared_topological_simplex'])

    def test_degenerate_and_duplicate_faces_are_rejected(self):
        points=[(0,0,0),(1,0,0),(2,0,0),(0,1,0)]
        self.assertFalse(contact.classify_pair(points,(0,1,2),(0,1,3))['intersection_only_in_shared_topological_simplex'])
        self.assertFalse(contact.classify_pair(points,(0,1,3),(3,1,0))['intersection_only_in_shared_topological_simplex'])


if __name__=='__main__':unittest.main()
