import importlib.util
import math
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source'
sys.path.insert(0, str(SOURCE))
import audit_local_junction_cad_budget_v2 as audit


class BudgetTests(unittest.TestCase):
    def test_absolute_new_budget_is_not_permission_to_increase_old_tolerance(self):
        self.assertTrue(audit.numerical_budget_pass('generated_native_history', 1e-4))
        self.assertFalse(audit.numerical_budget_pass('generated_native_history', math.nextafter(1e-4,1)))
        self.assertFalse(audit.numerical_budget_pass('unchanged_exact_native_entity', 1e-4, 1e-7))
        self.assertTrue(audit.numerical_budget_pass('unchanged_exact_native_entity', 1e-7, 1e-7))
        self.assertFalse(audit.numerical_budget_pass('unclassified_rejected', 1e-7))
        self.assertFalse(audit.numerical_budget_pass('generated_native_history', float('nan')))

    def test_volume_relative_error_estimates_are_scaled_before_comparison(self):
        result = audit.volume_reconciliation((1000.,.001),(1002.,.001),(1.5,0.),(0.,0.))
        self.assertAlmostEqual(result['absolute_residual_scan_units_cubed'],.5)
        self.assertAlmostEqual(result['summed_absolute_quadrature_error_estimates_scan_units_cubed'],2.002)
        self.assertTrue(result['agrees_within_reported_quadrature_estimates'])
        rejected = audit.volume_reconciliation((1000.,1e-8),(1002.,1e-8),(1.5,0.),(0.,0.))
        self.assertFalse(rejected['agrees_within_reported_quadrature_estimates'])


@unittest.skipUnless(importlib.util.find_spec('OCP'), 'native OCP runtime required')
class NativeTests(unittest.TestCase):
    def setUp(self):
        self.cad = audit.local.ports.design.CAD()

    def test_curve_surface_and_vertices_on_box(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        shape = BRepPrimAPI_MakeBox(2,2,2).Shape()
        result = audit.curve_surface_consistency(self.cad,shape)
        self.assertEqual(len(result['pcurves']),24)
        self.assertEqual(len(result['vertices']),24)
        self.assertTrue(result['all_within_declared_tolerance_and_absolute_budget'])
        self.assertFalse(result['formal_continuous_error_bound_or_physical_accuracy_claimed'])

    def test_history_classifies_fillet_without_index_transfer(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.TopAbs import TopAbs_EDGE
        from OCP.TopoDS import TopoDS
        shape = BRepPrimAPI_MakeBox(2,2,2).Shape()
        before = audit.entity_groups(self.cad,shape)
        edge = TopoDS.Edge_s(self.cad.indexed(shape,TopAbs_EDGE).FindKey(1))
        maker, build = audit.local.build_fillet(shape,[edge],.25)
        self.assertTrue(build['done'])
        result = audit.classify_history(self.cad,shape,before,maker.Shape(),maker)
        self.assertTrue(result['all_entities_classified_and_within_budget'])
        categories = {r['classification'] for group in result['records'].values() for r in group}
        self.assertIn('unchanged_exact_native_entity', categories)
        self.assertIn('generated_native_history', categories)

    def test_zero_volume_face_is_not_empty(self):
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
        from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
        face = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0,0,0),gp_Dir(0,0,1)),-1,1,-1,1).Shape()
        self.assertFalse(audit.empty_shape(self.cad,face))

    def test_protected_outer_wire_requires_identical_four_native_edges(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        source = BRepPrimAPI_MakeBox(2,2,2).Shape()
        seed = {'center':[0,0,0]}
        same = audit.protected_outer_wire(self.cad,source,source,seed)
        self.assertTrue(same['all_unchanged'])
        self.assertEqual(len(same['edges']),4)
        changed = BRepPrimAPI_MakeBox(3,2,2).Shape()
        self.assertFalse(audit.protected_outer_wire(self.cad,source,changed,seed)['all_unchanged'])

    def test_complete_section_distinguishes_local_change_from_protected_change(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.gp import gp_Pnt
        source = BRepPrimAPI_MakeBox(2,2,2).Shape()
        candidate = BRepPrimAPI_MakeBox(3,2,2).Shape()
        section = {'center':[0,0,1], 'normal':[0,0,1]}
        local_roi = BRepPrimAPI_MakeBox(gp_Pnt(1.9,-1,-1),gp_Pnt(3.1,3,3)).Shape()
        accepted = audit.section_comparison(self.cad,source,candidate,local_roi,section,10)
        self.assertTrue(accepted['outside_ROI_unchanged_native_boolean'])
        self.assertAlmostEqual(accepted['added_area_scan_units_squared'],2.)
        wrong_roi = BRepPrimAPI_MakeBox(gp_Pnt(-1,-1,-1),gp_Pnt(1,3,3)).Shape()
        rejected = audit.section_comparison(self.cad,source,candidate,wrong_roi,section,10)
        self.assertFalse(rejected['outside_ROI_unchanged_native_boolean'])


if __name__ == '__main__':
    unittest.main()
