"""Literal source-omission adversaries and complete bounded-study receipt checks."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np


ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/research/935-bounded-fan-pruning-20261106/source'


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


producer=module(SOURCE/'prune_source_fans.py','bounded_omission_producer')
verifier=module(SOURCE/'verify_source_omissions.py','independent_omission_inspector')
boundary=module(SOURCE/'audit_pruned_boundaries.py','omission_edge_audit')
admission=module(SOURCE/'admit_acquisition_gaps.py','acquired_gap_admission')
fans=module(ROOT/'docs/research/935-quarantine-patches-20261106/source/inspect_vertex_fans.py','frozen_used_vertex_graph').vertex_fans
simple=module(ROOT/'docs/research/935-quarantine-patches-20261106/source/check_cgal_patches.py','frozen_exact_polygon').simple_projection
LIMITS=dict(max_facets_per_removed_fan=3,max_area_per_removed_fan_nominal_mm2=.05,max_diagonal_nominal_mm=3.,max_rounds=4,max_total_removed_facets=256)
GAPS=dict(min_edges=3,max_edges=128,max_diagonal_nominal_mm=3.,max_plane_residual_nominal_mm=.25,minimum_adjacent_normal_absolute_p10=.8)


def literal_omission():
    p=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[-.1,0.,0.],[0.,-.1,0.]])
    f=np.array([[0,1,2],[0,3,4]])
    groups=[dict(parent_face_rows=[0],facets=1,area_nominal_mm2=.5,bounds_diagonal_nominal_mm=np.sqrt(2.)),
            dict(parent_face_rows=[1],facets=1,area_nominal_mm2=.005,bounds_diagonal_nominal_mm=np.sqrt(.02))]
    journal=[dict(round=0,current_face_count=2,nonmanifold_contacts=1,
                  private_contacts=[dict(contact_vertex=0,groups=groups,retained_group=0,removal_admitted=True)],
                  requested_parent_face_rows=[1],total_removal_limit_passed=True)]
    return p,f,journal


class BoundedFanPruning(unittest.TestCase):
    def test_literal_largest_fan_retained_and_orphan_vertices_counted_separately(self):
        p,f,journal=literal_omission();keep=verifier.replay(p,f,journal,LIMITS,fans)
        np.testing.assert_array_equal(keep,[0]);counts,_=fans(f[keep],len(p))
        np.testing.assert_array_equal(counts,[1,1,1,0,0])

    def test_nonmaximal_or_forged_fan_partition_is_rejected(self):
        p,f,journal=literal_omission();journal[0]['private_contacts'][0]['groups'][0]['parent_face_rows']=[0,1]
        with self.assertRaisesRegex(AssertionError,'source_fan_partition'):verifier.replay(p,f,journal,LIMITS,fans)

    def test_wrong_retained_fan_and_forged_area_are_rejected(self):
        p,f,journal=literal_omission();journal[0]['private_contacts'][0]['retained_group']=1
        with self.assertRaisesRegex(AssertionError,'largest_source_fan'):verifier.replay(p,f,journal,LIMITS,fans)
        p,f,journal=literal_omission();journal[0]['private_contacts'][0]['groups'][1]['area_nominal_mm2']=.0001
        with self.assertRaises(AssertionError):verifier.replay(p,f,journal,LIMITS,fans)

    def test_out_of_mask_or_unreported_omission_is_refused(self):
        for requested in ([],[0],[0,1]):
            p,f,journal=literal_omission();journal[0]['requested_parent_face_rows']=requested
            with self.subTest(requested=requested):
                with self.assertRaisesRegex(AssertionError,'out_of_mask_omission'):verifier.replay(p,f,journal,LIMITS,fans)

    def test_area_round_and_total_limits_cannot_be_overridden(self):
        for limits in ({**LIMITS,'max_area_per_removed_fan_nominal_mm2':.001},{**LIMITS,'max_rounds':0},{**LIMITS,'max_total_removed_facets':0}):
            p,f,journal=literal_omission()
            with self.assertRaises(AssertionError):verifier.replay(p,f,journal,limits,fans)

    def test_each_producer_bound_is_enforced_including_exact_limit(self):
        row=dict(facets=3,area_nominal_mm2=.05,bounds_diagonal_nominal_mm=3.)
        self.assertTrue(producer.removal_allowed(row,LIMITS))
        for key,value in [('facets',4),('area_nominal_mm2',.050001),('bounds_diagonal_nominal_mm',3.00001)]:
            self.assertFalse(producer.removal_allowed({**row,key:value},LIMITS))

    def test_boundary_cancellation_tracks_newly_exposed_source_edges(self):
        before=np.array([[0,1],[1,2],[2,3],[3,0]]);faces=np.array([[0,1,2],[0,2,3]])
        self.assertEqual(boundary.boundary_after_omission(before,faces[:1]),Counter({(0,2):1,(2,3):1,(3,0):1}))
        self.assertEqual(boundary.boundary_after_omission(before,faces),Counter())

    def test_gap_projection_normal_and_size_screens_are_distinct(self):
        p=np.array([[0.,0.,0.],[1.,0.,0.],[1.,1.,0.],[0.,1.,0.]])
        normals=np.tile([0.,0.,1.],(4,1));reasons,proof=admission.screen(p,normals,simple,GAPS)
        self.assertEqual(reasons,[]);self.assertTrue(proof['exact_simple_projection'])
        reasons,_=admission.screen(p,np.tile([1.,0.,0.],(4,1)),simple,GAPS)
        self.assertIn('adjacent_normal_alignment',reasons)
        reasons,_=admission.screen(p,normals,simple,{**GAPS,'max_diagonal_nominal_mm':.1})
        self.assertIn('diagonal',reasons)

    def test_crossing_or_rank_one_gap_cannot_be_admitted(self):
        points=np.array([[0.,0.,0.],[1.,1.,0.],[0.,1.,0.],[1.,0.,0.]])
        reasons,_=admission.screen(points,np.tile([0.,0.,1.],(4,1)),simple,GAPS)
        self.assertIn('non_simple_or_zero_exact_projection',reasons)
        reasons,_=admission.screen(np.array([[0.,0.,0.],[1.,0.,0.],[2.,0.,0.]]),np.tile([0.,0.,1.],(3,1)),simple,GAPS)
        self.assertIn('rank_below_two',reasons)

    def test_large_rejected_gap_never_runs_quadratic_exact_projection(self):
        t=np.arange(129)*2*np.pi/129;p=np.c_[np.cos(t),np.sin(t),np.zeros(129)]
        def forbidden(points):raise AssertionError('quadratic predicate should not run')
        reasons,proof=admission.screen(p,np.tile([0.,0.,1.],(129,1)),forbidden,GAPS)
        self.assertIn('edge_count',reasons);self.assertFalse(proof['exact_projection_checked'])

    def test_public_receipt_binds_code_and_full_geometry_scope(self):
        r=json.loads((SOURCE.parent/'results.json').read_text())
        for source in r['executed_sources']:
            self.assertEqual(hashlib.sha256((SOURCE/source['name']).read_bytes()).hexdigest(),source['sha256'])
        for source in r['reused_helpers']:
            self.assertEqual(hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest(),source['sha256'])
        checked=r['independent_verification'];self.assertEqual(checked['candidate_nonmanifold_used_vertices'],0)
        self.assertEqual(checked['removed_triangles'],46);self.assertEqual(checked['candidate_unreferenced_vertices'],18)
        self.assertTrue(checked['complete_source_omission_mask_verified']);self.assertTrue(checked['actual_saved_OBJ_readback_exact'])
        for field in ('duplicate_faces','intersection_pairs','excluded_degenerate_faces'):self.assertEqual(checked[field],0)
        self.assertTrue(r['deviations']['geometry_study_deviation_checks_passed'])
        self.assertTrue(r['release']['conservative_open_study_checks_passed'])
        self.assertNotIn('/Users/',json.dumps(r))

    def test_boundary_and_trial_denominators_do_not_claim_a_head_or_filled_gaps(self):
        r=json.loads((SOURCE.parent/'results.json').read_text());b=r['boundary_and_component_audit'];g=r['acquisition_gap_admission']
        self.assertEqual(b['before_boundary_edges']-b['old_boundary_edges_no_longer_open']+b['newly_exposed_omission_boundary_edges'],b['after_boundary_edges'])
        self.assertEqual(sum(b['complete_edge_origin_counts'].values()),b['after_boundary_edges'])
        self.assertEqual(b['complete_edge_origin_counts']['5'],25)
        self.assertEqual(g['complete_walk_denominator'],b['boundary_walks']);self.assertEqual(g['experimental_trials_admitted'],286)
        self.assertFalse(g['geometry_modified']);self.assertTrue(g['trial_inputs_or_native_constructor_not_yet_executed'])
        for field in ('print_ready','closed_volume','full_bare_head_created','physical_acceptance','manufacturing_authorized'):
            self.assertFalse(r['release'][field])
        self.assertTrue(r['release']['full_goal_active'])


if __name__=='__main__':unittest.main()
