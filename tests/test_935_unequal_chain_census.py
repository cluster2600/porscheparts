"""Independent five-corner predicates, bipartite coverage and conflict/tie selection."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def module(name):
    path = ROOT/'docs/research/935-unequal-chain-census-20261106/source'/(name+'.py')
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class UnequalChainTests(unittest.TestCase):
    def setUp(self):
        self.producer = module('census_unequal_chains')
        self.checker = module('verify_unequal_chains')
        self.p = np.array([[0.,0.,.1],[1.2,0.,.1],[1.2,0.,-.1],[.6,0.,-.1],[0.,0.,-.1]])
        self.e = np.array([[0,1],[2,3],[3,4]])
        self.n = np.array([[0.,0.,1.],[0.,0.,-1.],[0.,0.,-1.]])

    def compare(self, points=None, edges=None, normals=None):
        p = self.p if points is None else points
        e = self.e if edges is None else edges
        n = self.n if normals is None else normals
        result = self.producer.qualify(p, e, n, np.array([[0,1,2]]))
        reason, scalar = self.checker.inspect(p,e,n,[0,1,2])
        eligible = [(cls, value) for cls, (_,value) in enumerate(scalar or []) if value is not None]
        self.assertEqual(len(result[2]), len(eligible))
        for i, (cls,value) in enumerate(eligible):
            self.assertEqual(result[3][i],cls)
            self.assertTrue(np.array_equal(result[4][i],value[0]))
            self.assertAlmostEqual(result[5][i],value[1])
        return result, reason, scalar

    def test_independent_literal_control_suite(self):
        controls = self.checker.controls()
        self.assertEqual(controls['complete_pentagon_patterns'],5)
        self.assertTrue(all(controls.values()))

    def test_opposed_five_corner_strip(self):
        result,_,_=self.compare()
        self.assertEqual(result[3].tolist(),[1])
        self.assertEqual(result[4].tolist(),[[True,True,True,False,False]])

    def test_same_facing_strip(self):
        points=np.array([[0.,0.,0.],[1.2,0.,0.],[1.2,.2,0.],[.6,.2,0.],[0.,.2,0.]])
        result,_,_=self.compare(points=points,normals=np.tile([0.,0.,-1.],(3,1)))
        self.assertEqual(result[3].tolist(),[0])

    def test_void_side_and_wrong_directed_chain_refused(self):
        self.assertEqual(len(self.compare(normals=-self.n)[0][2]),0)
        bad=self.e.copy();bad[2]=[2,4]
        self.assertEqual(self.compare(edges=bad)[1],'two_edges_not_directed_consecutive')
        bad=self.e.copy();bad[2]=bad[2,::-1]
        self.assertEqual(len(self.compare(edges=bad)[0][2]),0)

    def test_four_corners_and_excess_gap_refused(self):
        points=self.p.copy();points[3]=points[0]
        self.assertEqual(self.compare(points=points)[1],'not_five_distinct_source_corners')
        points=self.p.copy();points[2:,2]=-.6
        self.assertEqual(self.compare(points=points)[1],'cross_endpoint_or_middle_support_distance')

    def test_three_edge_conflict_and_near_tie(self):
        triples=np.array([[0,1,2],[0,3,4],[5,6,7],[8,4,9]])
        for scores in ([.1,.2,.1,.3],[.1,.1,.1,.3],[.1,.1+5e-13,.1,.3]):
            a=self.producer.unique_three_edge_selection(triples,scores,10)
            b=self.checker.three_edge_selection(triples,scores,10)
            for x,y in zip(a,b):self.assertTrue(np.array_equal(x,y))
        chosen=self.producer.unique_three_edge_selection(triples,[.1,.2,.1,.3],10)[0]
        self.assertEqual(chosen.tolist(),[0,2])

    def test_grid_matches_all_ordered_population_pairs(self):
        rng=np.random.default_rng(93512)
        left=rng.uniform(-1,1,(47,3));right=rng.uniform(-1,1,(39,3))
        expected=np.array([(a,b) for a in range(len(left)) for b in range(len(right))
            if np.sum((left[a]-right[b])**2)<=.25],dtype=np.int64)
        self.assertTrue(np.array_equal(self.checker.grid_bipartite(left,right,10000),expected))
        with self.assertRaises(AssertionError):self.checker.grid_bipartite(left,right,1)

    def test_complete_five_corner_halo_includes_inferred_incident_face(self):
        faces=np.array([[0,1,5],[2,3,6],[3,4,7],[0,7,8],[8,9,10]])
        offsets,rows=self.checker.complete_halos(faces,np.array([[0,1,2]]),self.e,11)
        self.assertEqual(offsets.tolist(),[0,4]);self.assertEqual(rows.tolist(),[0,1,2,3])


class LocalAcquiredBorderTests(unittest.TestCase):
    def test_curved_strip_has_local_observed_directions_without_uniform_plane(self):
        first=module('census_unequal_chains')
        producer=module('census_unequal_chains_v2');checker=module('verify_unequal_chains_v2')
        points=np.array([[0.,0.,0.],[1.2,0.,0.],[1.2,.2,0.],[.6,.2,.15],[0.,.2,0.]])
        edges=np.array([[0,1],[2,3],[3,4]])
        normals=np.array([[0.,0.,-1.],[-.25,.05,-1.],[.25,.5,-1.]])
        normals/=np.linalg.norm(normals,axis=1)[:,None]
        tangents=points[edges[:,1]]-points[edges[:,0]]
        self.assertTrue(np.allclose(np.sum(tangents*normals,axis=1),0.,atol=1e-15))
        old=first.qualify(points,edges,normals,np.array([[0,1,2]]))
        new=producer.qualify(points,edges,normals,np.array([[0,1,2]]))
        reason,peer=checker.inspect(points,edges,normals,[0,1,2])
        self.assertEqual(len(old[2]),0)
        self.assertEqual(new[3].tolist(),[0]);self.assertEqual(reason,'passed_common_geometry')
        self.assertEqual(peer[0][0],'eligible')
        self.assertTrue(np.array_equal(new[4][0],peer[0][1][0]))
        self.assertFalse(new[4][0,3]);self.assertFalse(new[4][0,4])
        self.assertTrue(all(checker.controls().values()))

    def test_planar_and_annular_literal_controls_remain_valid(self):
        checker=module('verify_unequal_chains_v2')
        self.assertTrue(all(checker.controls().values()))


if __name__=='__main__':unittest.main()
