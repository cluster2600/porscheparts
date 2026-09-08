import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake'
sys.path.insert(0,str(SOURCE))
import diagnose_gas_boolean as diagnostic


@unittest.skipUnless(importlib.util.find_spec('OCP'),'native OCP runtime required')
class NativeDiagnosticTests(unittest.TestCase):
    def test_real_nested_void_is_retained_not_repaired(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
        from OCP.gp import gp_Pnt
        cad=diagnostic.boundaries.inspection.design.CAD()
        shape=BRepAlgoAPI_Cut(BRepPrimAPI_MakeBox(3,3,3).Shape(),
                             BRepPrimAPI_MakeBox(gp_Pnt(1,1,1),1,1,1).Shape()).Shape()
        report=diagnostic.inspect_shells(cad,shape)
        self.assertEqual(len(report['shells']),2)
        self.assertAlmostEqual(sum(s['signed_volume_quadrature_not_bound'] for s in report['shells']),26.)
        self.assertTrue(any(s['signed_volume_quadrature_not_bound']<0 for s in report['shells']))
        self.assertEqual(report['pairs'][0]['shared_native_face_ids'],[])
        self.assertEqual(report['shared_topology_localization_face_ids'],[])

    def test_shared_native_face_between_shells_is_explicit(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.BRep import BRep_Builder
        from OCP.TopoDS import TopoDS_Shell,TopoDS_Compound
        cad=diagnostic.boundaries.inspection.design.CAD()
        face=cad.indexed(BRepPrimAPI_MakeBox(1,1,1).Shape(),cad.TopAbs_FACE).FindKey(1)
        builder=BRep_Builder();compound=TopoDS_Compound();builder.MakeCompound(compound)
        for _ in range(2):
            shell=TopoDS_Shell();builder.MakeShell(shell);builder.Add(shell,face);builder.Add(compound,shell)
        report=diagnostic.inspect_shells(cad,compound)
        self.assertEqual(report['pairs'][0]['shared_native_face_ids'],[1])
        self.assertEqual(report['shared_topology_localization_face_ids'],[1])

    def test_valid_box_has_no_faults(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        cad=diagnostic.boundaries.inspection.design.CAD()
        report,_=diagnostic.inspect_native(cad,BRepPrimAPI_MakeBox(1,2,3).Shape())
        self.assertTrue(report['BRep_valid_exact_method'])
        self.assertFalse(report['invalid_records'])

    def test_displaced_vertex_fault_is_not_lost_in_context(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.BRep import BRep_Builder,BRep_Tool
        from OCP.TopoDS import TopoDS
        from OCP.TopAbs import TopAbs_VERTEX
        cad=diagnostic.boundaries.inspection.design.CAD()
        shape=BRepPrimAPI_MakeBox(1,2,3).Shape()
        vertex=TopoDS.Vertex_s(cad.indexed(shape,TopAbs_VERTEX).FindKey(1))
        point=BRep_Tool.Pnt_s(vertex)
        BRep_Builder().UpdateVertex(vertex,cad.gp_Pnt(point.X()+.1,point.Y(),point.Z()),1e-7)
        report,_=diagnostic.inspect_native(cad,shape)
        self.assertFalse(report['BRep_valid_exact_method'])
        self.assertTrue(report['invalid_records'])
        self.assertTrue(any(r['self_statuses'] or r['contextual_statuses'] for r in report['invalid_records']))


if __name__=='__main__':unittest.main()
