import copy
import importlib.util
import json
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/picogk-protected-junction'


@unittest.skipUnless(importlib.util.find_spec('numpy'), 'NumPy required by independent surface audit')
class ProtectedJunctionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('protected_junction_audit', SOURCE/'audit.py')
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def native(self):
        return dict(schema='m64-picogk-protected-junction-witness/v1', policy_sha256='test', method='closing',
                    voxel_world_units=.1, authorized_ROI_low=[-8,-3,-8], authorized_ROI_high=[8,3,8],
                    inner_ROI_low=[-7.4,-2.4,-7.4], inner_ROI_high=[7.4,2.4,7.4],
                    radius_world_units=1, margin_world_units=.6, radial_mask_radius_world_units=8.8,
                    shared_primitive_self_checks_passed=True, source_master_modified=False,
                    analytic_addition_support_restricted=False, difference_shell_used_for_candidate=False,
                    operation='A_union_C_intersect_protected_mask',
                    private_head_processed=False, exact_BRep_created=False,
                    CFD_qualified=False, manufacturing_authorized=False)

    def test_exact_witness_contract(self):
        self.module.validate_native(self.native(), .1, 'test')

    def test_each_changed_or_missing_contract_field_rejects(self):
        original = self.native()
        for key in original:
            bad = copy.deepcopy(original)
            del bad[key]
            with self.assertRaises(ValueError, msg=key):
                self.module.validate_native(bad, .1, 'test')
        for key,value in [('radial_mask_radius_world_units', 10), ('manufacturing_authorized', 0),
                          ('shared_primitive_self_checks_passed', 1), ('voxel_world_units', .2),
                          ('policy_sha256', 'other'), ('private_head_processed', True)]:
            bad = self.native(); bad[key] = value
            with self.assertRaises(ValueError, msg=key):
                self.module.validate_native(bad, .1, 'test')

    def test_same_thresholds_and_shared_code_not_copied(self):
        policy = json.loads((SOURCE/'criteria.json').read_text())
        self.assertEqual(policy['relative_actual_added_volume_difference_threshold'], .05)
        self.assertEqual(policy['sampled_bidirectional_surface_distance_threshold_world_units'], .2)
        project = (SOURCE/'ProtectedJunction.csproj').read_text()
        self.assertIn('parts/picogk-catalog/common/Sdf.cs', project)
        self.assertIn('parts/picogk-catalog/engine/EngineSdf.cs', project)
        self.assertFalse((SOURCE/'Sdf.cs').exists())
        code = (SOURCE/'Program.cs').read_text()
        self.assertIn('outsideSdf==0&&protectedSdf==0&&unavailable==0&&finite>0', code)
        self.assertIn('ProtectedMask.Check()', code)


if __name__ == '__main__':
    unittest.main()
