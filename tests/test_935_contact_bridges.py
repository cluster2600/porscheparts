"""Synthetic masks, contact fans and source-preserving bridge adversaries."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np


ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/research/935-contact-bridges-20261106/source'


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


producer=module(SOURCE/'prepare_contact_bridges.py','contact_producer')
checker=module(SOURCE/'check_contact_bridges.py','contact_checker')
audit=module(SOURCE/'audit_contact_topology.py','contact_audit')
fan_count=module(ROOT/'docs/research/935-quarantine-patches-20261106/source/inspect_vertex_fans.py','frozen_fan_counter').vertex_fans
LIMITS=dict(maximum_diagonal_nominal_mm=3.,minimum_signed_adjacent_normal_dot=.8)


def no_predicates_for_topology_fixture(points,faces):
    """These unit cases exercise topology only; actual native controls are receipted separately."""
    return np.empty((0,2),dtype=np.int64),np.empty(0,dtype=bool),np.empty(0,dtype=np.int64)


def two_fans():
    return np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[-1.,0.,0.],[0.,-1.,0.]]),np.array([[0,1,2],[0,3,4]])


class ContactBridges(unittest.TestCase):
    def test_two_open_source_fans_join_without_moved_coordinates(self):
        p,f=two_fans();fans=producer.contact_fans(f,0);proposals=producer.proposals(fans,0)
        self.assertEqual(len(fans),2);self.assertEqual(len(proposals),2)
        original=p.copy();area=checker.inspect(p,f,0,proposals[0],fan_count,no_predicates_for_topology_fixture,LIMITS)
        self.assertAlmostEqual(area,.5);np.testing.assert_array_equal(original,p)
        counts,_=fan_count(np.r_[f,proposals[0]],len(p));np.testing.assert_array_equal(counts,np.ones(5,dtype=int))

    def test_closed_fan_is_not_offered_a_boundary_bridge(self):
        f=np.array([[0,1,2],[0,2,3],[0,3,1],[0,4,5]])
        fans=producer.contact_fans(f,0)
        self.assertEqual(len(fans),2);self.assertEqual(sum(not x['outgoing'] for x in fans),1)
        self.assertEqual(producer.proposals(fans,0),[])

    def test_three_open_fans_require_two_bridges_and_all_orders_are_retained(self):
        angle=np.deg2rad([0,40,120,160,240,280])
        p=np.r_[[[0.,0.,0.]],np.c_[np.cos(angle),np.sin(angle),np.zeros(6)]]
        f=np.array([[0,1,2],[0,3,4],[0,5,6]])
        proposals=producer.proposals(producer.contact_fans(f,0),0)
        self.assertEqual(len(proposals),6);self.assertTrue(all(len(x)==2 for x in proposals))
        checker.inspect(p,f,0,proposals[0],fan_count,no_predicates_for_topology_fixture,LIMITS)
        with self.assertRaises(AssertionError):checker.inspect(p,f,0,proposals[0][:1],fan_count,no_predicates_for_topology_fixture,LIMITS)

    def test_wrong_anchor_wrong_boundary_or_reversed_bridge_is_refused(self):
        p,f=two_fans()
        for patch in ([[2,0,3]],[[0,2,4]],[[0,3,2]],[[0,0,3]]):
            with self.subTest(patch=patch):
                with self.assertRaises(AssertionError):checker.inspect(p,f,0,np.array(patch),fan_count,no_predicates_for_topology_fixture,LIMITS)

    def test_signed_normal_and_fixed_size_limits_are_enforced(self):
        p,f=two_fans();patch=np.array([[0,2,3]])
        with self.assertRaisesRegex(AssertionError,'experimental_size_screen'):
            checker.inspect(p,f,0,patch,fan_count,no_predicates_for_topology_fixture,{**LIMITS,'maximum_diagonal_nominal_mm':.1})
        p[3:,2]=1.
        with self.assertRaisesRegex(AssertionError,'experimental_normal_screen'):
            checker.inspect(p,f,0,patch,fan_count,no_predicates_for_topology_fixture,LIMITS)

    def test_independent_intersection_rejection_cannot_be_overridden_by_topology(self):
        p,f=two_fans()
        def detected(points,faces):return np.array([[0,2]]),np.array([False]),np.array([],dtype=np.int64)
        with self.assertRaisesRegex(AssertionError,'local_bridge_intersection'):
            checker.inspect(p,f,0,np.array([[0,2,3]]),fan_count,detected,LIMITS)

    def test_complete_changed_boundary_mask_preserves_all_other_edges(self):
        _,f=two_fans();_,boundary=fan_count(f,5)
        expected=audit.changed_boundary(boundary,np.array([[0,2,3]]))
        self.assertEqual(expected,Counter({(0,1):1,(1,2):1,(2,3):1,(3,4):1,(4,0):1}))
        self.assertNotEqual(expected,Counter(map(tuple,boundary.tolist())))

    def test_executed_sources_controls_and_complete_denominators_are_bound(self):
        r=json.loads((SOURCE.parent/'results.json').read_text())
        for source in r['executed_sources']:
            self.assertEqual(hashlib.sha256((SOURCE/source['name']).read_bytes()).hexdigest(),source['sha256'])
        for source in r['reused_helpers']:
            self.assertEqual(hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest(),source['sha256'])
        counts=r['trial_counts']
        self.assertEqual(counts['source_contacts'],48)
        self.assertEqual(counts['closed_fan_contacts'],23)
        self.assertEqual(counts['proposals'],54)
        self.assertEqual(counts['selected_local_contacts'],8)
        self.assertEqual(counts['selected_local_contacts']-counts['global_rejected_contacts'],counts['retained_contacts'])
        self.assertEqual(counts['retained_contacts'],6)
        self.assertTrue(all(r['native_controls'].values()))
        self.assertFalse(r['release']['print_ready']);self.assertTrue(r['release']['full_goal_active'])
        self.assertNotIn('/Users/',json.dumps(r))

    def test_full_topology_origins_and_remaining_failure_gates_are_honest(self):
        r=json.loads((SOURCE.parent/'results.json').read_text());t=r['used_vertices_and_boundaries']
        self.assertEqual((t['base_nonmanifold_used_vertices'],t['candidate_nonmanifold_used_vertices']),(48,42))
        self.assertEqual(t['base_boundary_edges']-t['removed_previous_boundary_edges']+t['new_inferred_bridge_boundary_edges'],t['candidate_boundary_edges'])
        self.assertEqual(sum(t['complete_boundary_origin_counts'].values()),t['candidate_boundary_edges'])
        self.assertEqual(t['complete_boundary_origin_counts']['4'],6)
        self.assertTrue(t['exact_whole_boundary_change_mask_verified'])
        for field in ('index_duplicates_created','full_used_vertex_manifold','conservative_surface_workflow_fully_admitted','closed_volume'):
            self.assertFalse(t[field])
        for field in ('full_candidate_intersection_pairs','predicate_excluded_faces','global_edge_conflicts','duplicate_face_groups'):
            self.assertEqual(r['final_topology'][field],0)
        for field in ('closed_volume','full_bare_head_created','physical_acceptance','manufacturing_authorized'):
            self.assertFalse(r['release'][field])


if __name__=='__main__':unittest.main()
