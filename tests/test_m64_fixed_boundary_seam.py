import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'))


@unittest.skipUnless(importlib.util.find_spec('OCP') and importlib.util.find_spec('numpy'), 'optional native runtime')
class FixedBoundarySeamTest(unittest.TestCase):
    def test_local_Bernstein_surface_boundaries_peak_and_invalid_inputs(self):
        from OCP.Geom import Geom_BSplineSurface
        from OCP.TColgp import TColgp_Array2OfPnt
        from OCP.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger
        from OCP.gp import gp_Pnt, gp_Vec, gp_Trsf, gp_Ax1, gp_Dir
        from OCP.TopLoc import TopLoc_Location
        from OCP.TopoDS import TopoDS
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from trial_fixed_boundary_seam import deform_surface, field, located_surface
        poles = TColgp_Array2OfPnt(1, 2, 1, 2)
        for i in (1, 2):
            for j in (1, 2):
                poles.SetValue(i, j, gp_Pnt(i-1, j-1, 0))
        knots, mults = TColStd_Array1OfReal(1, 2), TColStd_Array1OfInteger(1, 2)
        for i in (1, 2):
            knots.SetValue(i, i-1)
            mults.SetValue(i, 2)
        s = Geom_BSplineSurface(poles, knots, knots, mults, mults, 1, 1)
        transform = gp_Trsf()
        transform.SetRotation(gp_Ax1(gp_Pnt(), gp_Dir(1, 0, 0)), .7)
        transform.SetTranslationPart(gp_Vec(31, -27, 48))
        face = TopoDS.Face_s(BRepBuilderAPI_MakeFace(s.Copy(), 1e-7).Face().Moved(TopLoc_Location(transform)))
        local, placement = located_surface(face)
        deform_surface(local, [0, 0, 1], .02)
        self.assertLess(BRepAdaptor_Surface(face).Value(.98, .97).Distance(
            gp_Pnt(.98, .97, .02).Transformed(placement)), 1e-12)
        for amplitude in (0, -.1, .04, float('nan'), float('inf')):
            with self.assertRaises(ValueError): deform_surface(s.Copy(), [0, 0, 1], amplitude)
        with self.assertRaises(ValueError): deform_surface(s.Copy(), [0, 0, 2], .02)
        coefficient, bound = deform_surface(s, [0, 0, 1], .02)
        self.assertLess(float(bound), .020000000001)
        self.assertEqual((s.UMultiplicity(2), s.VMultiplicity(2)), (2, 2))
        for u in [i/20 for i in range(21)]+[.92, .94, .96, .98, .99]:
            for v in [i/20 for i in range(21)]+[.88, .91, .94, .97, .99]:
                p = s.Value(u, v)
                self.assertLess(p.Distance(gp_Pnt(u, v, field(u, v, coefficient))), 1e-12)
                self.assertLessEqual(abs(p.Z()), float(bound)+1e-12)
                if u in (0, 1) or v in (0, 1): self.assertLess(abs(p.Z()), 1e-12)
        self.assertAlmostEqual(s.Value(.98, .97).Z(), .02, places=12)
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.TopAbs import TopAbs_FACE
        from audit_fixed_boundary_volume import rectangular_flux, indexed
        box = BRepPrimAPI_MakeBox(gp_Pnt(31, -27, 48), 2, 3, 4).Shape()
        self.assertAlmostEqual(sum(rectangular_flux(TopoDS.Face_s(f), 8)
                                   for f in indexed(box, TopAbs_FACE)), 24., places=10)


if __name__ == '__main__': unittest.main()
