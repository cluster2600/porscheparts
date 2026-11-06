"""Independent synthetic masks and adversarial topology for inferred local patches."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np


SOURCE = Path(__file__).resolve().parents[1]/'docs/research/935-quarantine-patches-20261106/source'


def module(name):
    spec = importlib.util.spec_from_file_location(name,SOURCE/(name+'.py'))
    result = importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


checker = module('check_cgal_patches')
fans = module('inspect_vertex_fans')


def open_prism(polygon=((0.,0.),(1.,0.),(1.,1.),(0.,1.))):
    n = len(polygon)
    points = np.array([[x,y,z] for z in (0.,1.) for x,y in polygon])
    sides = np.array([face for i in range(n) for face in
                      ((i,(i+1)%n,(i+1)%n+n),(i,(i+1)%n+n,i+n))])
    hole = np.arange(n);boundary = np.c_[hole,np.roll(hole,-1)]
    return points,sides,hole,boundary


class QuarantinePatches(unittest.TestCase):
    def test_selected_missing_face_only_and_unselected_opening_preserved(self):
        p,f,h,b = open_prism();cap = np.array([[0,2,1],[0,3,2]])
        added,proof = checker.check_patch(p,f,h,b,p.copy(),np.r_[f,cap])
        np.testing.assert_array_equal(added,cap)
        self.assertTrue(proof['exact_target_vertex_and_perimeter_mask'])
        self.assertEqual(proof['added_faces'],2)
        counts,edges = fans.vertex_fans(np.r_[f,cap],len(p))
        np.testing.assert_array_equal(counts,np.ones(8,dtype=int))
        self.assertEqual({tuple(e) for e in edges},{(5,4),(6,5),(7,6),(4,7)})

    def test_moved_vertex_is_refused_even_below_a_geometric_tolerance(self):
        p,f,h,b = open_prism();moved = p.copy();moved[0,0] = np.nextafter(0.,1.)
        with self.assertRaisesRegex(AssertionError,'moved, added or reordered'):
            checker.check_patch(p,f,h,b,moved,np.r_[f,[[0,2,1],[0,3,2]]])

    def test_missing_or_duplicated_source_face_is_refused(self):
        p,f,h,b = open_prism();cap = np.array([[0,2,1],[0,3,2]])
        for wrong in (np.r_[f[:-1],cap],np.r_[f,f[:1],cap]):
            with self.subTest(faces=len(wrong)):
                with self.assertRaisesRegex(AssertionError,'original face coverage'):
                    checker.check_patch(p,f,h,b,p.copy(),wrong)

    def test_reversed_incomplete_duplicate_or_wrong_opening_caps_are_refused(self):
        p,f,h,b = open_prism()
        for cap in ([[0,1,2],[0,2,3]],[[0,2,1]],[[0,2,1],[0,2,1]],[[4,5,6],[4,6,7]]):
            with self.subTest(cap=cap):
                with self.assertRaises(AssertionError):checker.check_patch(p,f,h,b,p.copy(),np.r_[f,cap])

    def test_folded_projected_disk_cannot_pass_perimeter_and_euler_alone(self):
        p,f,h,b = open_prism(((0.,0.),(2.,0.),(.5,1.),(2.,2.),(0.,2.)))
        cap = [[0,2,1],[0,3,2],[0,4,3]]
        with self.assertRaisesRegex(AssertionError,'Folded, reversed or zero'):
            checker.check_patch(p,f,h,b,p.copy(),np.r_[f,cap])

    def test_self_crossing_and_backtracking_projections_are_refused(self):
        self.assertFalse(checker.simple_projection([(0,0),(1,1),(0,1),(1,0)]))
        self.assertFalse(checker.simple_projection([(0,0),(2,0),(1,0),(1,1),(0,1)]))
        self.assertTrue(checker.simple_projection([(0,0),(1,0),(2,0),(2,1),(0,1)]))

    def test_point_contact_is_not_a_manifold_used_vertex(self):
        counts,edges = fans.vertex_fans(np.array([[0,1,2],[0,3,4]]),5)
        np.testing.assert_array_equal(counts,[2,1,1,1,1])
        self.assertEqual(len(edges),6)

    def test_overused_or_inconsistently_wound_edges_are_refused(self):
        for faces in ([[0,1,2],[0,1,3]],[[0,1,2],[1,0,3],[0,1,4]]):
            with self.assertRaises(AssertionError):fans.vertex_fans(np.array(faces),5)

    def test_public_receipt_binds_sources_and_preserves_failed_workflow_gates(self):
        report = json.loads((SOURCE.parent/'results.json').read_text())
        for source in report['executed_sources']:
            self.assertEqual(hashlib.sha256((SOURCE/source['name']).read_bytes()).hexdigest(),source['sha256'])
        counts = report['trial_counts']
        self.assertEqual(counts['quarantine_only_contours'],counts['screen_rejected']+counts['native_trials'])
        self.assertEqual(counts['native_trials'],counts['local_rejected']+counts['local_accepted'])
        self.assertEqual(counts['local_accepted'],counts['global_rejected_patches']+counts['retained_patches'])
        self.assertEqual(counts['quarantine_only_contours']-counts['retained_patches'],32)
        topology = report['final_topology']
        self.assertEqual(topology['global_edge_conflicts'],0)
        self.assertEqual(topology['full_candidate_intersection_pairs'],0)
        self.assertEqual(topology['open_boundary_edges'],98768)
        self.assertEqual(report['used_vertices']['candidate_nonmanifold_used_vertices'],48)
        self.assertFalse(report['used_vertices']['conservative_surface_workflow_fully_admitted'])
        for name in ('print_ready','closed_volume','physical_acceptance','manufacturing_authorized','full_bare_head_created'):
            self.assertFalse(report['release'][name])
        self.assertTrue(report['release']['full_goal_active'])
        self.assertNotIn('/Users/',json.dumps(report))
        self.assertNotIn('private_per_patch_deviations',json.dumps(report))


if __name__=='__main__':unittest.main()
