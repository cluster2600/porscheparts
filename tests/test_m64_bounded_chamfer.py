import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'
sys.path.insert(0, str(HERE))


@unittest.skipUnless(importlib.util.find_spec('numpy'), 'optional numerical runtime')
class BoundedChamferTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('OCP'), 'optional CAD runtime')
    def test_planar_tip_cut_is_one_cap_not_a_bounded_notch(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID
        from OCP.gp import gp_Pnt
        from trial_bounded_tip_cut import cut_tip_plane, encode, indexed
        body=BRepPrimAPI_MakeBox(1.,1.,1.).Shape(); before=encode(body)
        result=cut_tip_plane(body,[0.,0.,0.],.02)
        self.assertEqual(encode(body),before)
        self.assertTrue(BRepCheck_Analyzer(result,True,False,True).IsValid())
        self.assertEqual(len(indexed(result,TopAbs_FACE)),7)
        self.assertEqual(len(indexed(result,TopAbs_SOLID)),1)
        props=GProp_GProps(); BRepGProp.VolumeProperties_s(result,props)
        self.assertAlmostEqual(1-props.Mass(),.01**3/6,places=12)
        notch=BRepAlgoAPI_Cut(body,BRepPrimAPI_MakeBox(gp_Pnt(.5,.5,.5),.5,.5,.5).Shape()).Shape()
        notch_before=encode(notch)
        with self.assertRaisesRegex(ValueError,'exactly_one_planar_cap_required'):
            cut_tip_plane(notch,[.5,.5,.5],.02)
        self.assertEqual(encode(notch),notch_before)
        for point,radius in (([float('nan'),0.,0.],.02),([0.,0.,0.],1.),([.5,0.,0.],.02)):
            with self.assertRaises(ValueError): cut_tip_plane(body,point,radius)

    def test_bound_is_not_constraint_filtering_and_open_intervals_fail(self):
        from run_bounded_chamfer import command, interval_ok
        cmd = command(Path('/mesher'), Path('/input.off'), .020, True, 2000)
        self.assertIn('-a', cmd); self.assertIn('-E', cmd); self.assertNotIn('-e', cmd)
        self.assertIn('-x', cmd); self.assertNotIn('-z', cmd)
        self.assertTrue(interval_ok(.019, .020, .002))
        for values in ((.019, .021, .001), (.02, .01, .001), (0, float('nan'), .001), (-1, 0, .001)):
            self.assertFalse(interval_ok(*values))
        with self.assertRaises(ValueError): command(Path('/m'), Path('/i'), float('inf'), True, 1)

    @unittest.skipUnless(importlib.util.find_spec('cascading_upper_bounds'), 'optional distance library')
    def test_distance_on_analytic_offset_and_translation(self):
        import numpy as np
        from run_bounded_chamfer import distance_bounds, surface_arrays
        p = np.array([[0., 0, 0], [1., 0, 0], [0, .024, 0]])
        f = np.array([[0, 1, 2]])
        for shift in (0., 1000.):
            a = p+shift; b = a+np.array([0., 0, .015])
            for target, expected in ((a, 0.), (b, .015)):
                result = distance_bounds(a, f, target, f, 1e-8)
                self.assertTrue(result['completed'])
                for r in result['directions']:
                    self.assertLessEqual(r['lower'], expected+1e-11)
                    self.assertGreaterEqual(r['upper'], expected-1e-11)
                self.assertAlmostEqual(result['upper'], expected, places=7)
        with self.assertRaises(ValueError): surface_arrays(p, np.array([[0, 0, 1]]))

    @unittest.skipUnless(importlib.util.find_spec('OCP'), 'optional CAD runtime')
    def test_native_curve_representations_agree_on_a_box(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
        from audit_shared_curve_consistency import indexed, inspect, junction
        shape = BRepPrimAPI_MakeBox(1., 2., 3.).Shape()
        rows = inspect(list(enumerate(indexed(shape, TopAbs_FACE), 1)))
        self.assertEqual(len(rows), 24)
        self.assertLess(max(r['maximum_sampled_gap'] for r in rows), 1e-12)
        self.assertTrue(all(r['same_parameter'] and r['same_range'] for r in rows))
        faces = indexed(shape, TopAbs_FACE); fa = faces[0]
        edge = indexed(fa, TopAbs_EDGE)[0]
        fb = next(f for f in faces[1:] if any(edge.IsSame(e) for e in indexed(f, TopAbs_EDGE)))
        for other, angle in ((fa,0.), (fb,90.), (fa.Reversed(),180.)):
            row = junction(edge, (fa,other))
            self.assertAlmostEqual(row['minimum_oriented_normal_angle_degrees'], angle, places=10)
            self.assertAlmostEqual(row['maximum_oriented_normal_angle_degrees'], angle, places=10)
            self.assertEqual(row['sampled_tangent_under_0p1_degree'], angle == 0.)
            self.assertTrue(row['endpoints_included'])
        with self.assertRaises(ValueError): junction(edge, (fa,))

    @unittest.skipUnless(importlib.util.find_spec('OCP'), 'optional CAD runtime')
    def test_bounded_cut_removes_one_eighth_ball_at_box_corner(self):
        import math
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        from OCP.TopAbs import TopAbs_SOLID, TopAbs_SHELL
        from trial_bounded_tip_cut import cut_ball, encode, indexed
        body = BRepPrimAPI_MakeBox(1., 1., 1.).Shape(); before = encode(body)
        result = cut_ball(body, [0., 0., 0.], .02)
        self.assertEqual(encode(body), before)
        self.assertTrue(BRepCheck_Analyzer(result, True, False, True).IsValid())
        self.assertEqual(len(indexed(result, TopAbs_SOLID)), 1)
        self.assertEqual(len(indexed(result, TopAbs_SHELL)), 1)
        props = GProp_GProps(); BRepGProp.VolumeProperties_s(result, props)
        self.assertAlmostEqual(1-props.Mass(), math.pi*.02**3/6, places=12)
        with self.assertRaises(ValueError): cut_ball(body, [float('nan'), 0., 0.], .02)
        with self.assertRaises(ValueError): cut_ball(body, [0., 0., 0.], 1.)


if __name__ == '__main__': unittest.main()
