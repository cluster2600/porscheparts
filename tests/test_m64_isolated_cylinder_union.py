import importlib.util
from pathlib import Path
import sys
import unittest


@unittest.skipUnless(importlib.util.find_spec('OCP') and importlib.util.find_spec('numpy'),'optional native CAD runtime')
class IsolatedUnionTest(unittest.TestCase):
    def test_signature_distinguishes_foreign_representation_from_own_geometry(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'))
        from trial_isolated_cylinder_union import encoded,own_geometry,indexed,periodic_seam,pcurve_gaps
        from OCP.BRep import BRep_Builder,BRep_Tool
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
        from OCP.Geom import Geom_Plane
        from OCP.Geom2d import Geom2d_Line
        from OCP.GeomAbs import GeomAbs_Cylinder
        from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE
        from OCP.TopLoc import TopLoc_Location
        from OCP.TopoDS import TopoDS
        from OCP.gp import gp_Pnt,gp_Dir,gp_Pnt2d,gp_Dir2d
        shape=BRepPrimAPI_MakeCylinder(2.,3.).Shape()
        face=next(TopoDS.Face_s(f) for f in indexed(shape,TopAbs_FACE) if BRepAdaptor_Surface(TopoDS.Face_s(f)).GetType()==GeomAbs_Cylinder)
        edge=next(TopoDS.Edge_s(e) for e in indexed(face,TopAbs_EDGE) if not BRep_Tool.IsClosed_s(TopoDS.Edge_s(e),face))
        seam=next(TopoDS.Edge_s(e) for e in indexed(face,TopAbs_EDGE) if BRep_Tool.IsClosed_s(TopoDS.Edge_s(e),face))
        self.assertTrue(periodic_seam(face,seam))
        self.assertFalse(periodic_seam(face,edge))
        rows=pcurve_gaps([(1,face)])
        self.assertEqual(len(rows),4)
        self.assertLess(max(r['maximum_sampled_gap'] for r in rows),1e-12)
        original,own=encoded(face),own_geometry(face)
        foreign=Geom_Plane(gp_Pnt(0,0,20),gp_Dir(0,0,1));pc=Geom2d_Line(gp_Pnt2d(0,0),gp_Dir2d(1,0))
        builder=BRep_Builder();builder.UpdateEdge(edge,pc,foreign,TopLoc_Location(),BRep_Tool.Tolerance_s(edge))
        self.assertNotEqual(encoded(face),original)
        self.assertEqual(own_geometry(face),own)
        builder.UpdateEdge(edge,pc,face,BRep_Tool.Tolerance_s(edge))
        self.assertNotEqual(own_geometry(face),own)
