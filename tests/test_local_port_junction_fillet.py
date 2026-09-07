import importlib.util
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source'
sys.path.insert(0, str(SOURCE))
import build_local_port_junction_fillet as local


class ParameterTests(unittest.TestCase):
    def test_bounded_radius(self):
        self.assertEqual(local.validate_radius(1.), 1.)
        for x in (0., -1., 1.001, math.nan, math.inf):
            with self.assertRaises(ValueError):
                local.validate_radius(x)

    def test_strict_approximation_only_tightens_construction_settings(self):
        historical = (1e-2, 1e-4, 1e-5, 1e-4, 1e-5, 1e-3)
        self.assertEqual(local.STRICT_PARAMETERS[0], historical[0])
        self.assertTrue(all(a < b for a, b in zip(local.STRICT_PARAMETERS[1:], historical[1:])))


@unittest.skipUnless(importlib.util.find_spec('OCP'), 'OCP native runtime required')
class NativeWitnessTests(unittest.TestCase):
    def test_strict_settings_applied_before_spine_creation(self):
        events = []
        class Maker:
            def __init__(self, shape): events.append('construct')
            def SetParams(self, *values): events.append(('params', values))
            def Contour(self, edge): return 0
            def Add(self, radius, edge): events.append('add')
            def Build(self): events.append('build')
            def IsDone(self): return False
            def NbContours(self): return 0
            def NbFaultyContours(self): return 0
            def NbFaultyVertices(self): return 0
            def HasResult(self): return False
        with patch('OCP.BRepFilletAPI.BRepFilletAPI_MakeFillet', Maker):
            _, report = local.build_fillet(None, [object()], 1., 'strict-approximation-v1')
        self.assertEqual(events, ['construct', ('params', local.STRICT_PARAMETERS), 'add', 'build'])
        self.assertFalse(report['acceptance_guards_relaxed'])

    def test_concave_step_fillet_preserves_outer_circle_and_is_tangent(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
        from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
        from OCP.TopAbs import TopAbs_FACE
        cad = local.ports.design.CAD()
        branch = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0,-10,0),gp_Dir(0,1,0)),5,12).Shape()
        trunk = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0,0,0),gp_Dir(0,1,0)),10,10).Shape()
        source = BRepAlgoAPI_Fuse(branch,trunk).Shape()
        selected = local.branch_cap_edges(cad,source,{'center':[0,0,0],'radius':10})
        self.assertEqual(len(selected),1)
        maker, report = local.build_fillet(source,[x[1] for x in selected],1.)
        self.assertTrue(report['done']); self.assertEqual(report['faulty_contours'],[])
        result = maker.Shape()
        self.assertTrue(cad.valid(result)); self.assertFalse(local.ports.bop_check(result)['has_faulty'])
        generated = [f for x in selected for f in maker.Generated(x[1]) if f.ShapeType()==TopAbs_FACE]
        angles = local.sample_generated_tangency(cad,result,generated)
        self.assertEqual(len(angles),2)
        self.assertLess(max(x['tangent_plane_angle_deg_max'] for x in angles),1e-5)
        self.assertEqual(local.ports.bbox(local.ports.native(),source),local.ports.bbox(local.ports.native(),result))
        va,_=local.bounded.adaptive_volume(source);vb,_=local.bounded.adaptive_volume(result)
        self.assertGreater(vb,va)

    def test_no_edges_is_rejected(self):
        with self.assertRaises(ValueError):
            local.build_fillet(None,[],1.)


if __name__ == '__main__':
    unittest.main()
