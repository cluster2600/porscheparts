"""Source-identity and prior-exclusion controls for the acquired-only pair census."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np


ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/research/935-untried-acquired-pairs-20261106/source'


def module(name):
    spec=importlib.util.spec_from_file_location(name,SOURCE/(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


census=module('census_untried_pairs')
inspection=module('verify_untried_pairs')
filtering=module('filter_untried_strips')
opposed=module('audit_opposed_skins')
opposed_inspection=module('verify_opposed_skins_v2')


class UntriedAcquiredPairs(unittest.TestCase):
    def fixture(self):
        raw=dict(vertices=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,0.],[1.,0.,0.],[0.,-1.,0.]]),
                 triangles=np.array([[0,1,2],[4,3,5]]))
        mesh=dict(points=raw['vertices'].copy(),triangles=raw['triangles'].copy(),
                  original_face_ids=np.array([0,1]),inferred_surface_kind=np.array([0,0]))
        return raw,mesh,np.array([[0,1],[4,3]]),np.array([0,1])

    def test_literal_identity_controls(self):
        self.assertEqual(inspection.identity_controls(),5)

    def test_producer_and_independent_checker_recover_original_directed_corners(self):
        raw,mesh,edges,owners=self.fixture()
        keys,normals=census.source_edge_keys(mesh,edges,owners,raw,np.arange(2))
        self.assertEqual(keys.tolist(),[[0,0,1],[1,4,3]])
        for index in range(2):
            expected,normal=inspection.original_key(mesh,edges[index],owners[index],raw)
            self.assertEqual(tuple(keys[index]),expected);np.testing.assert_array_equal(normals[index],normal)

    def test_local_vertex_permutation_does_not_create_a_new_pair_identity(self):
        raw,mesh,edges,owners=self.fixture();first,_=census.source_edge_keys(mesh,edges,owners,raw,np.arange(2))
        permutation=np.array([3,1,5,0,4,2]);inverse=np.argsort(permutation)
        mesh['points']=mesh['points'][permutation];mesh['triangles']=inverse[mesh['triangles']]
        after,_=census.source_edge_keys(mesh,inverse[edges],owners,raw,np.arange(2))
        np.testing.assert_array_equal(first,after)
        np.testing.assert_array_equal(census.canonical_pair_keys(first,np.array([[0,1]])),census.canonical_pair_keys(after,np.array([[1,0]])))

    def test_coincident_distinct_raw_nodes_and_owners_are_not_coordinate_welded(self):
        raw,mesh,edges,owners=self.fixture();keys,_=census.source_edge_keys(mesh,edges,owners,raw,np.arange(2))
        self.assertTrue(np.array_equal(raw['vertices'][0],raw['vertices'][3]))
        self.assertTrue(np.array_equal(raw['vertices'][1],raw['vertices'][4]))
        self.assertNotEqual(tuple(keys[0]),tuple(keys[1]))

    def test_inferred_owner_is_never_independent_acquired_support(self):
        raw,mesh,edges,owners=self.fixture();mesh['inferred_surface_kind'][0]=4
        with self.assertRaises(AssertionError):census.source_edge_keys(mesh,edges,owners,raw,np.arange(2))
        with self.assertRaises(AssertionError):inspection.original_key(mesh,edges[0],0,raw)

    def test_moved_corner_or_reversed_original_facet_fails_closed(self):
        raw,mesh,edges,owners=self.fixture();mesh['points'][0,2]=.01
        with self.assertRaises(AssertionError):census.source_edge_keys(mesh,edges,owners,raw,np.arange(2))
        raw,mesh,edges,owners=self.fixture();mesh['triangles'][0]=mesh['triangles'][0,::-1]
        with self.assertRaises(AssertionError):census.source_edge_keys(mesh,edges,owners,raw,np.arange(2))
        with self.assertRaises(AssertionError):inspection.original_key(mesh,edges[0],0,raw)

    def test_cyclic_corner_rotation_preserves_acquired_edge_identity(self):
        raw,mesh,edges,owners=self.fixture();before,_=census.source_edge_keys(mesh,edges,owners,raw,np.arange(2))
        mesh['triangles']=np.roll(mesh['triangles'],1,axis=1)
        after,_=census.source_edge_keys(mesh,edges,owners,raw,np.arange(2))
        np.testing.assert_array_equal(before,after)

    def test_prior_attempt_is_recognised_when_pair_order_is_reversed(self):
        keys=np.array([[17,103,204],[29,307,408]])
        attempted={inspection.pair_key(keys,0,1)}
        self.assertIn(inspection.pair_key(keys,1,0),attempted)
        self.assertEqual(tuple(census.canonical_pair_keys(keys,np.array([[1,0]]))[0]),next(iter(attempted)))

    def test_whole_new_strip_removal_preserves_older_identical_numeric_labels(self):
        data=dict(points=np.zeros((4,3)),global_node_ids=np.arange(4),
                  triangles=np.array([[0,1,2],[0,2,3],[1,0,3],[1,3,2]]),
                  source_untried_pair_ids=np.array([-1,-1,7,7]),
                  source_frontier_pair_ids=np.array([7,7,-1,-1]),
                  source_strip_cap_curve_ids=np.array([-1,21,-1,-1]))
        result=filtering.compose(data,{7})
        self.assertEqual(result['triangles'].tolist(),data['triangles'][:2].tolist())
        self.assertEqual(result['source_frontier_pair_ids'].tolist(),[7,7])
        self.assertEqual(result['source_strip_cap_curve_ids'].tolist(),[-1,21])

    def test_opposed_skin_controls_separate_material_side_and_void_side(self):
        limits=dict(maximum_cross_endpoint_distance_nominal_mm=.5,maximum_tangent_dot=-.8,
                    maximum_opposed_skin_normal_dot=-.8,maximum_material_side_gap_dot=-.8,
                    minimum_outward_binormal_dot=.8,minimum_forward_wall_normal_dot=.8)
        self.assertEqual(opposed_inspection.controls(limits),8)
        points=np.array([[0.,0.,.1],[1.,0.,.1],[1.,0.,-.1],[0.,0.,-.1]])
        edges=np.array([[0,1],[2,3]]);normals=np.array([[0.,0.,1.],[0.,0.,-1.]])
        old=census.module(ROOT/'docs/research/935-frontier-pairing-20261106/source/census_frontier_pairs.py','frozen_geometry_for_test')
        for source_normals,expected in ((normals,1),(-normals,0)):
            reasons,ids,flags,scores=opposed.classify(points,edges,source_normals,np.array([[0,1]]),limits,old.triangle_alignment)
            self.assertEqual(len(ids),expected)
            self.assertEqual(reasons['eligible'],expected)

    def test_all_executed_sources_helpers_and_derivative_parents_are_bound(self):
        result=json.loads((SOURCE.parent/'results.json').read_text())
        for row in result['executed_sources']:
            self.assertEqual(hashlib.sha256((SOURCE/row['name']).read_bytes()).hexdigest(),row['sha256'])
        for row in result['reused_helpers']:
            self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),row['sha256'])
        for row in result['derivative_source_ancestry']:
            self.assertEqual(hashlib.sha256((ROOT/row['parent_path']).read_bytes()).hexdigest(),row['parent_sha256'])
        self.assertNotIn('/Users/',json.dumps(result))

    def test_complete_prior_exclusion_and_independent_denominators(self):
        result=json.loads((SOURCE.parent/'results.json').read_text())
        self.assertEqual(result['census']['complete_current_walks'],1226)
        self.assertEqual(result['census']['source_scope_edges'],91573)
        self.assertEqual(result['census']['prior_attempted_pairs'],1315)
        self.assertEqual(result['census']['prior_attempted_broad_pairs_excluded'],210)
        self.assertEqual(result['census']['unchanged_small_walk_broad_pairs_excluded'],456)
        self.assertEqual(result['census']['selected_untried_pairs'],173)
        self.assertTrue(result['independent_census']['census_independently_verified'])
        self.assertEqual(result['construction']['accepted_pairs'],142)
        self.assertEqual(result['opposed_skin_census']['selected_opposed_skin_pairs'],217)
        self.assertTrue(result['opposed_skin_independent_census']['census_independently_verified'])
        self.assertFalse(result['opposed_skin_independent_census']['constructor_admission_granted'])

    def test_surface_numerics_are_not_head_or_manufacturing_completion(self):
        result=json.loads((SOURCE.parent/'results.json').read_text());final=result['final_audit']
        self.assertTrue(final['surface_study_checks_passed'])
        self.assertGreater(final['remaining_boundary_edges'],90000)
        self.assertFalse(final['closed_volume']);self.assertFalse(final['physical_acceptance'])
        self.assertFalse(result['goal_complete']);self.assertFalse(result['manufacturing_authorized'])


if __name__=='__main__':unittest.main()
