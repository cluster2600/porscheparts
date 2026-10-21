"""Tiny literal stdlib arithmetic/eligibility tests; no head or scientific import."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('reference_kernels',Path(__file__).with_name('reference_kernels.py'))
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)


class ReferenceTests(unittest.TestCase):
    def test_all_ties_and_exploratory_lex_first(self):
        rows,all_edges,lex = M.shortest_proposals({0:(0.,0.,0.),1:(1.,0.,0.),2:(0.,1.,0.)},{7:(2,0,1)})
        self.assertEqual(rows[0]['minimum_edges'],[[0,1],[0,2]])
        self.assertEqual(all_edges,[(0,1),(0,2)]); self.assertEqual(lex,[(0,1)])
        self.assertEqual([r['numerator'] for r in rows[0]['exact_squared_lengths_in_ascending_order']],['1','1','2'])

    def test_exact_order_survives_binary64_squared_underflow(self):
        rows,edges,_ = M.shortest_proposals({0:(0.,0.,0.),1:(2.**-600,0.,0.),2:(0.,2.**-599,0.)},{0:(0,1,2)})
        self.assertEqual(edges,[(0,1)])
        self.assertEqual(rows[0]['exact_squared_lengths_in_ascending_order'][0]['numerator'],'1')
        self.assertEqual(rows[0]['exact_squared_lengths_in_ascending_order'][0]['denominator'],str(2**1200))

    def test_component_plane_candidates_and_fixed_conflict(self):
        z={0:1.,1:0.,2:0.,3:1.,4:2.}
        rows=M.component_eligibility([(0,1),(1,2),(3,4)],set(),{1},z)
        self.assertEqual([r['keeper_candidates_satisfying_only_fixed_and_plane'] for r in rows],[[1,2],[3,4]])
        self.assertTrue(all(r['selected_keeper'] is None for r in rows))
        blocked=M.component_eligibility([(0,1),(1,2)],{0},{1},z)
        self.assertEqual(blocked[0]['fixed_conflict_ids'],[0])
        self.assertEqual(blocked[0]['keeper_candidates_satisfying_only_fixed_and_plane'],[])

    def test_cap_exact_winding_and_plane_refusal(self):
        points={0:(0.,0.,0.),1:(1.,0.,0.),2:(0.,1.,0.)}
        self.assertEqual(M.cap_winding(points,{0:(0,2,1),1:(0,1,2)})['negative_z_face_ids'],[0])
        self.assertEqual(M.cap_winding(points,{0:(0,2,1),1:(0,1,2)})['positive_z_face_ids'],[1])
        points[2]=(0.,1.,1.)
        with self.assertRaises(ValueError): M.cap_winding(points,{0:(0,1,2)})

    def test_empty_and_invalid_inputs(self):
        self.assertEqual(M.shortest_proposals({},{}),([],[],[]))
        self.assertEqual(M.component_eligibility([],set(),set(),{}),[])
        for point in [(float('nan'),0.,0.),(0.,float('inf'),0.),(0,0.,0.)]:
            with self.assertRaises(ValueError): M.shortest_proposals({0:point},{})
        with self.assertRaises(ValueError):
            M.shortest_proposals({0:(0.,0.,0.),1:(1.,0.,0.)},{0:(0,1,1)})
        with self.assertRaises(ValueError): M.component_eligibility([(1,0)],set(),set(),{0:0.,1:0.})
        with self.assertRaises(ValueError): M.component_eligibility([(0,1)],set(),set(),{0:0.,1:float('nan')})


if __name__=='__main__':
    unittest.main()
