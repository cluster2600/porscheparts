"""Pure guard inputs only, never files labelled as native worker results."""
import importlib.util
import math
from pathlib import Path
import unittest

SOURCE = Path(__file__).with_name('assess_mixed_distance.py')
SPEC = importlib.util.spec_from_file_location('held_mixed_assessor', SOURCE)
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)


def guard_payload(scalar=.03286):
    ids = tuple(range(M.COUNTS['cap']))
    low = max(0.,math.nextafter(scalar-M.EPSILON,-math.inf))
    high = math.nextafter(scalar+M.EPSILON,math.inf)
    d = dict(schema='962-CGAL-directed-bounded-distance/v1',status='completed_interval',
        stage='completed',error='',query_completed=True,CGAL='5.6',point_and_oriented_face_snapshots_unchanged=True,
        source_full_vertices=871731,source_full_faces=1743878,source_selected_faces=len(ids),
        source_constructed_disjoint_vertices=3*len(ids),target_full_vertices=902145,target_full_faces=1804706,
        selected_original_face_IDs=list(ids),epsilon_mm=M.EPSILON,required_interval_gap_mm=M.H.GAP,
        polygon_budget_mm=M.H.BUDGET,concurrency='Sequential_tag',match_faces_source=False,match_faces_target=False,
        normalization=False,complete_target_required=True,source_closedness_required=False,roundoff_certificate=False,
        mesh_exported=False,input_files_written=False,scalar_mm=scalar,lower_mm=low,upper_mm=high,
        actual_interval_gap_mm=high-low,polygon_budget_passed=high<=M.H.BUDGET)
    return d, ids


class MixedAssessmentGuards(unittest.TestCase):
    def test_missing_or_same_reverse_part_refused(self):
        for value in ({'cap':'a'},{'cap':'a','noncap':'a'},{}):
            with self.subTest(parts=value), self.assertRaises(ValueError): M.roles(value)
        M.roles({'cap':'a','noncap':'b'})

    def test_actual_cgal_numeric_policy_and_positive_below_epsilon(self):
        d,ids = guard_payload(M.EPSILON)
        self.assertEqual(M.cgal_interval(d,'cap',ids),(0,math.nextafter(2*M.EPSILON,math.inf)))
        d,ids = guard_payload(); self.assertEqual(M.cgal_interval(d,'cap',ids),(d['lower_mm'],d['upper_mm']))

    def test_nonfinite_open_wrong_gap_and_incomplete_refused(self):
        for key,value in [('scalar_mm',math.nan),('upper_mm',math.inf),('lower_mm',-.1),
                          ('upper_mm',.2),('query_completed',False),('status','failed')]:
            d,ids = guard_payload();d[key]=value
            with self.subTest(field=key),self.assertRaises(ValueError): M.cgal_interval(d,'cap',ids)

    def test_wrong_ID_order_counts_or_complete_target_refused(self):
        for key,value in [('selected_original_face_IDs',[1,0]),('source_selected_faces',5426),
                          ('target_full_faces',8976),('source_full_vertices',902145),('match_faces_target',True)]:
            d,ids = guard_payload();d[key]=value
            with self.subTest(field=key),self.assertRaises(ValueError): M.cgal_interval(d,'cap',ids)

    def test_source_identity_and_target_refusal(self):
        _,ids = guard_payload()
        q=dict(source_path=M.H.CANDIDATE,source_sha256=M.H.CANDIDATE_SHA,full_source_vertices=871731,
            full_source_faces=1743878,target_path=M.H.ORIGINAL,target_sha256=M.H.ORIGINAL_SHA,
            complete_target_vertices=902145,complete_target_faces=1804706,selected_faces=len(ids),
            constructed_source_disjoint_vertices=3*len(ids),epsilon_mm=M.EPSILON,
            unchanged_interval_gap_mm=M.H.GAP,unchanged_polygon_budget_mm=M.H.BUDGET,
            query_completion_distinct_from_polygon_budget=True,inner_roundoff_certificate=False)
        M.query_identity(q,'cap',ids)
        for key,value in [('source_sha256','0'*64),('target_path',M.H.CANDIDATE),('selected_faces',5426)]:
            bad=dict(q);bad[key]=value
            with self.subTest(field=key),self.assertRaises(ValueError): M.query_identity(bad,'cap',ids)

    def test_max_three_semantics_and_missing_bound(self):
        bounds=[(.03193,.03197),(.00633,.00639),(.03283,.03289)]
        self.assertEqual(M.H.combine(bounds),(.03283,.03289))
        for bad in (bounds[:2],bounds+[(0,0)],[(0,.1)]+bounds[1:]):
            with self.assertRaises(ValueError): M.H.combine(bad)

    def test_completed_interval_can_reject_budget(self):
        d,ids=guard_payload(1)
        low,high=M.cgal_interval(d,'cap',ids)
        self.assertLess(low,1);self.assertGreater(high,1)
        self.assertFalse(d['polygon_budget_passed'])


if __name__ == '__main__': unittest.main()
