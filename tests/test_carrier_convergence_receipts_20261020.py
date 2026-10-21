"""Retain actual analytical controls and completed matched-order result scope."""
import json
from pathlib import Path
import unittest

EVIDENCE=Path(__file__).resolve().parents[1]/'docs/reports/carrier-resume-20261020/evidence'


def read(case):return json.loads((EVIDENCE/case/'assessment.json').read_text())


class ConvergenceReceiptTests(unittest.TestCase):
    def test_quadratic_control_requires_the_analytic_body_force(self):
        positive=read('ccx-quadratic-control-assessment-001');negative=read('ccx-quadratic-missing-body-assessment-001')
        self.assertEqual(positive['status'],'complete_quadratic_patch_control_passed');self.assertEqual(negative['status'],'quadratic_patch_control_refused');self.assertTrue(positive['free_interior_node_indices']);self.assertLessEqual(positive['maximum_displacement_error_mm'],1e-11);self.assertGreater(negative['maximum_displacement_error_mm'],1e-11)

    def test_both_actual_consistent_traction_controls_pass_original_tolerances(self):
        for order,nodes,rows in [('P1',8,6),('P2',27,24)]:
            item=read(f'traction-{order}-assessment-001');self.assertEqual(item['status'],'consistent_traction_patch_passed');self.assertEqual(item['complete_node_rows'],nodes);self.assertEqual(item['complete_stress_rows'],rows);self.assertLessEqual(item['maximum_displacement_error_mm'],1e-11);self.assertLessEqual(item['maximum_stress_error_MPa'],1e-6)

    def test_matched_orders_keep_the_same_parent_cells_and_resultant_load(self):
        first=read('meshlib-R2-matched-P1-assessment-001');second=read('meshlib-R2-matched-P2-assessment-001');self.assertEqual(first['C3D4_elements'],second['C3D10_elements']);self.assertEqual(second['result_rows']['stresses'],4*second['C3D10_elements']);self.assertLessEqual(second['relative_energy_residual'],1e-4);self.assertFalse(second['stress_convergence_demonstrated']);self.assertFalse(second['strength_qualified'])
        for a,b in zip(first['force_N']+first['moment_Nmm'],second['force_N']+second['moment_Nmm']):self.assertAlmostEqual(a,b,places=6)


if __name__=='__main__':unittest.main()
