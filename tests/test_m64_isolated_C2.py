import importlib.util
import json
from pathlib import Path
import unittest

PATH=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/trial_isolated_transition_c2.py'
spec=importlib.util.spec_from_file_location('isolated_C2',PATH)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class IsolatedC2Tests(unittest.TestCase):
    def test_exact_factor_bound_and_target(self):
        self.assertEqual(module.beta3(0.),0.)
        self.assertEqual(module.beta3(1.),0.)
        self.assertEqual(module.beta3(.5),1.)
        self.assertLess(module.coefficient_bound(.55*256/25),1)

    def test_support_keeps_actual_target_centered(self):
        for target in (.04,.3,.96):
            lo,hi=module.centered_support(target)
            self.assertGreaterEqual(lo,0);self.assertLessEqual(hi,1)
            self.assertAlmostEqual((lo+hi)/2,target)
        for target in (0,1,float('nan')):
            with self.assertRaises(ValueError):module.centered_support(target)

    def test_public_rejection_is_not_solid_or_manufacturing_evidence(self):
        path=PATH.parent/'evidence/isolated-c2-surface-rejection-20260907.json'
        report=json.loads(path.read_text())
        self.assertEqual(report['status'],'rejected_surface_quality')
        self.assertLess(report['continuous_scalar_field_bound']['upper_bound'],1.)
        self.assertGreater(report['native_surface']['maximum_tangent_displacement_gradient'],report['rejection']['limit'])
        self.assertTrue(report['native_surface']['constructed'])
        for field in ('boundary_physical_function_established','combined_with_previous_repair',
                      'face_or_solid_constructed','solid_ray_tests_rerun','physical_validation',
                      'absolute_scale_certified','M64_fitment_validated','manufacturing_authorized'):
            self.assertFalse(report['scope'][field],field)
        self.assertFalse(report['rejection']['is_material_or_manufacturing_allowable'])


if __name__=='__main__':unittest.main()
