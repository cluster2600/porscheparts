from fractions import Fraction
import importlib.util
import math
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source'
sys.path.insert(0, str(SOURCE))
import propose_picogk_convex_intake_roi as roi


class ConvexRoiTests(unittest.TestCase):
    def test_triangle_convex_containment_and_crossing_vertex(self):
        box, center, radius = [-2,-2,-2,2,2,2], [0,0,0], 1.
        triangle = [[.5,-1,.5], [-.5,1,.5], [0,0,-.5]]
        self.assertTrue(roi.triangle_inside_convex_roi(triangle,box,center,radius))
        # These samples illustrate the convexity identity; the proof is the
        # box/cylinder intersection, not the finiteness of this grid.
        for i in range(9):
            for j in range(9-i):
                weights = [i/8,j/8,1-(i+j)/8]
                point = [sum(weights[k]*triangle[k][axis] for k in range(3)) for axis in range(3)]
                self.assertTrue(roi.point_inside_convex_roi(point,box,center,radius))
        triangle[0] = [1.,0.,1.]
        self.assertFalse(roi.triangle_inside_convex_roi(triangle,box,center,radius))

    def test_outer_reference_ring_is_excluded_and_buffers_are_not_rounded_down(self):
        policy = roi.cylinder_policy(21.316152827901732, [-3,-3,-3,3,3,3])
        reference = Fraction(policy['reference_radius_scan_units'])
        authorized = Fraction(policy['authorized_cylinder_radius_scan_units'])
        calculation = Fraction(policy['calculation_cylinder_radius_scan_units'])
        self.assertGreaterEqual(reference-authorized, Fraction(.4))
        self.assertGreaterEqual(authorized-calculation, Fraction(3*.2))
        self.assertFalse(roi.point_inside_convex_roi([float(reference),0,0], [-30,-3,-30,30,3,30],
                                                    [0,0,0], float(authorized)))
        self.assertEqual(policy['authorized_box_private'], [-3,-3,-3,3,3,3])

    def test_one_ulp_outside_cylinder_is_not_accepted(self):
        self.assertTrue(roi.point_inside_convex_roi([1.,0,0],[-2,-2,-2,2,2,2],[0,0,0],1.))
        self.assertFalse(roi.point_inside_convex_roi([math.nextafter(1.,2.),0,0],[-2,-2,-2,2,2,2],[0,0,0],1.))

    def test_radial_box_bound_is_directed_and_not_just_sampled(self):
        result = roi.radial_box_upper([-3,-2,-4,1,2,2],[0,0,0])
        self.assertGreaterEqual(Fraction(result)**2, 25)
        for value in (Fraction(2), Fraction(1,10), Fraction(49,9)):
            self.assertLessEqual(Fraction(roi.sqrt_bound(value, False))**2, value)
            self.assertGreaterEqual(Fraction(roi.sqrt_bound(value, True))**2, value)

    def test_clipping_classification_distinguishes_proof_from_inconclusive(self):
        self.assertEqual(roi.radius_status(.25,.40,.41), 'radius_neighborhood_contained_by_conservative_bound')
        for radius in (1., .5):
            self.assertEqual(roi.radius_status(radius,.40,.41), 'radius_neighborhood_cannot_fit_without_clipping')
        self.assertEqual(roi.radius_status(.405,.40,.41), 'inconclusive_between_bounds')

    def test_empty_contracted_domain_and_bad_input_are_rejected(self):
        for reference, box in ((.9,[-3,-3,-3,3,3,3]), (20.,[-.1,-.1,-.1,.1,.1,.1])):
            with self.assertRaises(ValueError):
                roi.cylinder_policy(reference,box)
        with self.assertRaises(ValueError):
            roi.point_inside_convex_roi([float('nan'),0,0],[-2,-2,-2,2,2,2],[0,0,0],1.)


@unittest.skipUnless(importlib.util.find_spec('OCP'), 'native OCP runtime required')
class NativeBranchBoundsTests(unittest.TestCase):
    def test_control_pole_bound_covers_between_endpoint_bulge(self):
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
        from OCP.Geom import Geom_BSplineCurve
        from OCP.TColgp import TColgp_Array1OfPnt
        from OCP.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger
        from OCP.gp import gp_Pnt
        points = TColgp_Array1OfPnt(1,4)
        for index, coords in enumerate(((0,0,0),(2,0,0),(2,0,0),(0,0,0)),1):
            points.SetValue(index,gp_Pnt(*coords))
        knots, mults = TColStd_Array1OfReal(1,2), TColStd_Array1OfInteger(1,2)
        for index, value in ((1,0.),(2,1.)):
            knots.SetValue(index,value); mults.SetValue(index,4)
        curve = Geom_BSplineCurve(points,knots,mults,3,False)
        edge = BRepBuilderAPI_MakeEdge(curve).Edge()
        bound = roi.edge_radial_bounds(edge,[0,0,0],segments=16)
        # Cubic 6*t*(1-t) peaks at 1.5 despite two zero endpoints.
        self.assertGreaterEqual(bound['radial_max_upper_bound_scan_units'],1.5)
        self.assertLessEqual(bound['radial_max_lower_bound_scan_units'],1.5)
        self.assertGreater(bound['radial_max_lower_bound_scan_units'],1.49)
        self.assertTrue(bound['upper_bound_from_continuous_control_pole_boxes_not_samples'])


if __name__ == '__main__':
    unittest.main()
