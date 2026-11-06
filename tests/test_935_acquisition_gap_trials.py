"""Synthetic exact-mask/provenance adversaries and complete acquisition-trial receipts."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np


ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/research/935-acquisition-gap-trials-20261106/source'


def module(name):
    spec=importlib.util.spec_from_file_location(name,SOURCE/(name+'.py'));result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


assembly=module('assemble_acquisition_candidate')
checker=module('inspect_acquisition_patches')


def parent_fixture():
    return dict(points=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[-1.,0.,0.],[0.,-1.,0.]]),
                triangles=np.array([[0,1,2],[0,3,4]]),global_node_ids=np.arange(10,15),
                original_face_ids=np.array([100,-1]),source_fragment_indices=np.array([7,-1]),
                source_patch_curve_ids=np.array([-1,3]),source_contact_vertex_ids=np.array([-1,-1]),
                inferred_surface_kind=np.array([0,1]),parent_face_rows=np.array([200,201]))


def prism():
    p=np.array([[0.,0.,0.],[1.,0.,0.],[1.,1.,0.],[0.,1.,0.],[0.,0.,1.],[1.,0.,1.],[1.,1.,1.],[0.,1.,1.]])
    f=np.array([[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])
    hole=np.arange(4);return p,f,hole,np.c_[hole,np.roll(hole,-1)]


class AcquisitionGapTrials(unittest.TestCase):
    def test_composition_preserves_all_parent_coordinates_faces_and_omission_channels(self):
        base=parent_fixture();snapshot={k:v.copy() for k,v in base.items()}
        result=assembly.compose(base,np.array([[0,2,3]]),np.array([7]))
        for key in base:
            np.testing.assert_array_equal(base[key],snapshot[key])
            actual=result[key] if key in ('points','global_node_ids') else result[key][:2]
            np.testing.assert_array_equal(actual,snapshot[key])

    def test_new_cap_ancestry_is_explicit_and_disjoint_from_previous_patches(self):
        result=assembly.compose(parent_fixture(),np.array([[0,2,3]]),np.array([7]))
        for key in ('original_face_ids','source_fragment_indices','parent_face_rows','source_contact_vertex_ids'):
            self.assertEqual(result[key][-1],-1)
        np.testing.assert_array_equal(result['source_acquisition_curve_ids'],[-1,-1,7])
        np.testing.assert_array_equal(result['immediate_parent_face_rows'],[0,1,-1])
        self.assertEqual(result['source_patch_curve_ids'][-1],20000007)
        self.assertEqual(result['inferred_surface_kind'][-1],3)

    def test_empty_composition_retains_the_parent_without_inventing_faces(self):
        base=parent_fixture();r=assembly.compose(base,np.empty((0,3),dtype=np.int64),np.array([],dtype=np.int64))
        np.testing.assert_array_equal(r['triangles'],base['triangles'])
        np.testing.assert_array_equal(r['source_acquisition_curve_ids'],[-1,-1])

    def test_unsupported_provenance_or_label_count_fails_closed(self):
        with self.assertRaises(AssertionError):assembly.compose({**parent_fixture(),'unknown_matrix':np.ones((2,2))},np.array([[0,2,3]]),np.array([7]))
        with self.assertRaises(AssertionError):assembly.compose(parent_fixture(),np.array([[0,2,3]]),np.array([],dtype=np.int64))

    def test_current_checker_accepts_only_the_complete_selected_prism_opening(self):
        p,f,hole,edges=prism();cap=np.array([[0,2,1],[0,3,2]])
        added,proof=checker.check_patch(p,f,hole,edges,p.copy(),np.r_[f,cap])
        np.testing.assert_array_equal(added,cap);self.assertTrue(proof['exact_target_vertex_and_perimeter_mask'])

    def test_wrong_unselected_opening_or_reversed_patch_is_refused(self):
        p,f,hole,edges=prism()
        for cap in ([[4,5,6],[4,6,7]],[[0,1,2],[0,2,3]]):
            with self.assertRaises(AssertionError):checker.check_patch(p,f,hole,edges,p.copy(),np.r_[f,cap])

    def test_moved_coordinates_and_changed_parent_faces_are_refused(self):
        p,f,hole,edges=prism();cap=np.array([[0,2,1],[0,3,2]]);moved=p.copy();moved[0,0]=np.nextafter(0.,1.)
        with self.assertRaises(AssertionError):checker.check_patch(p,f,hole,edges,moved,np.r_[f,cap])
        with self.assertRaises(AssertionError):checker.check_patch(p,f,hole,edges,p.copy(),np.r_[f[:-1],cap])

    def test_incomplete_duplicate_or_zero_area_patch_is_refused(self):
        p,f,hole,edges=prism()
        for cap in ([[0,2,1]],[[0,2,1],[0,2,1]],[[0,0,1],[0,3,2]]):
            with self.assertRaises(AssertionError):checker.check_patch(p,f,hole,edges,p.copy(),np.r_[f,cap])

    def test_all_executed_and_frozen_helper_sources_are_bound(self):
        r=json.loads((SOURCE.parent/'results.json').read_text())
        for source in r['executed_sources']:
            self.assertEqual(hashlib.sha256((SOURCE/source['name']).read_bytes()).hexdigest(),source['sha256'])
        for source in r['reused_helpers']:
            self.assertEqual(hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest(),source['sha256'])
        self.assertTrue(r['native_controls']['native_controls_independently_verified'])
        self.assertNotIn('/Users/',json.dumps(r))

    def test_complete_native_local_and_support_rejection_denominators(self):
        r=json.loads((SOURCE.parent/'results.json').read_text());t=r['trial_counts']
        self.assertEqual(t['native_trials'],286);self.assertEqual(t['native_exit_zero'],286)
        self.assertEqual(t['locally_accepted']+t['locally_rejected'],t['native_trials'])
        self.assertEqual(t['locally_accepted'],277);self.assertEqual(t['support_distance_rejected'],195)
        self.assertEqual(t['retained_patches'],82)
        self.assertEqual(t['locally_rejected']+t['support_distance_rejected']+t['retained_patches'],286)
        self.assertEqual(t['added_inferred_cap_faces'],613)

    def test_whole_topology_and_all_unselected_origins_are_preserved(self):
        r=json.loads((SOURCE.parent/'results.json').read_text());topo=r['final_topology']
        self.assertEqual(topo['candidate_nonmanifold_used_vertices'],0)
        self.assertEqual(topo['candidate_unreferenced_vertices'],18)
        self.assertTrue(topo['all_unselected_boundary_edges_owners_origins_and_omission_ancestry_unchanged'])
        self.assertEqual(topo['remaining_boundary_walks'],932-82)
        self.assertEqual(sum(topo['remaining_edge_origin_counts'].values()),topo['remaining_boundary_edges'])
        self.assertEqual({k:v for k,v in topo['remaining_edge_origin_counts'].items() if k!='1'},{'2':100,'3':726,'4':6,'5':25})
        for field in ('full_candidate_intersection_pairs','predicate_excluded_faces','global_edge_conflicts','duplicate_face_groups'):
            self.assertEqual(r['final_global_inspection'][field],0)

    def test_support_bound_and_numerical_checks_never_grant_physical_release(self):
        r=json.loads((SOURCE.parent/'results.json').read_text())
        self.assertFalse(r['initial_support_screen']['no_added_patch_exceeds_sampled_study_bound'])
        self.assertTrue(r['final_deviations']['no_added_patch_exceeds_sampled_study_bound'])
        self.assertLessEqual(r['final_deviations']['all_new_cap_probes_to_raw_source']['sampled_maximum_nominal_mm'],.25)
        self.assertTrue(r['final_deviations']['source_and_omission_distances_do_not_increase_pointwise'])
        self.assertTrue(r['release']['conservative_open_study_checks_passed'])
        for field in ('print_ready','closed_volume','full_bare_head_created','physical_acceptance','manufacturing_authorized'):
            self.assertFalse(r['release'][field])
        self.assertTrue(r['release']['full_goal_active'])


if __name__=='__main__':unittest.main()
