import importlib.util
import copy
import json
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/picogk-local-junction-buffered'


class BufferedWitnessContracts(unittest.TestCase):
    def test_policy_preserves_authorized_ROI_and_declares_interior_margin(self):
        policy = json.loads((SOURCE / 'criteria.json').read_text())
        self.assertEqual(policy['authorized_ROI_low'], [-8, -3, -8])
        self.assertEqual(policy['authorized_ROI_high'], [8, 3, 8])
        self.assertEqual(policy['interior_margin_voxels'], 3)
        self.assertEqual(policy['voxel_world_units'], .2)
        self.assertTrue(policy['margin_is_hypothesis_not_surface_protection_proof'])
        for key in ('outside_ROI_occupancy_changes_allowed', 'protected_occupancy_changes_allowed',
                    'source_gas_occupancy_losses_allowed', 'addition_at_ROI_boundary_allowed'):
            self.assertEqual(policy[key], 0)

    def test_native_uses_inner_mask_but_audits_outer_ROI(self):
        s = (SOURCE / 'Program.cs').read_text()
        self.assertIn('closed.voxBoolIntersect(inner)', s)
        self.assertIn('candidate=original.voxBoolAdd(closedInner)', s)
        self.assertIn('bool inROI=authorized.fSignedDistance(point)<=0', s)
        self.assertIn('float margin=3*h', s)
        self.assertIn('h!=0.2f', s)
        self.assertNotIn('times_h', s)
        self.assertIn('max_abs_outside_ROI_delta_world_units', s)

    def test_serialized_values_are_bitwise_compared(self):
        s = (SOURCE / 'Program.cs').read_text()
        self.assertIn('BitConverter.SingleToInt32Bits(first)!=BitConverter.SingleToInt32Bits(second)', s)
        self.assertIn('if(differences!=0)throw', s)
        self.assertIn('outside_active_bbox_values_compared=false', s)

    def test_audit_reuses_exact_helpers_and_retains_raw_status(self):
        s = (SOURCE / 'audit_buffered_surface.py').read_text()
        self.assertIn('direct.normalize_exact_zero(triangles)', s)
        self.assertIn('direct.roi_difference', s)
        self.assertIn("'raw_rejection_overridden': False", s)
        self.assertIn('native_hash != topo.sha(native_path)', s)
        self.assertNotIn('.split(', s)
        self.assertNotIn('fix_normals', s)

    @unittest.skipUnless(importlib.util.find_spec('numpy'), 'NumPy required for numerical audit import')
    def test_declared_screen_rejects_each_geometric_guard_failure(self):
        spec = importlib.util.spec_from_file_location('buffered_audit_test', SOURCE / 'audit_buffered_surface.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        native = {name: [0, 0] for name in ('outside_ROI_changed_nodes', 'protected_changed_nodes',
                  'lost_original_gas_nodes', 'added_nodes_touching_ROI_boundary')}
        native['changed_nodes'] = [1, 1]
        native['native_VDB'] = {'roundtrip_bitwise_comparison': {
            str(index): {'exact_value_comparison_pass': True} for index in range(6)}}
        rows = {name: {'normalized': {'topology': {'closed_oriented_combinatorial_surface_screen_pass': True}}}
                for name in ('before', 'after', 'added')}
        roi = {'all_changed_triangle_supports_inside_convex_ROI': True}
        self.assertTrue(module.declared_screen(native, rows, roi))
        for name in ('outside_ROI_changed_nodes', 'protected_changed_nodes',
                     'lost_original_gas_nodes', 'added_nodes_touching_ROI_boundary'):
            bad = copy.deepcopy(native)
            bad[name] = [0, 1]
            self.assertFalse(module.declared_screen(bad, rows, roi), name)
        self.assertFalse(module.declared_screen(native, rows, {'all_changed_triangle_supports_inside_convex_ROI': False}))
        bad_rows = copy.deepcopy(rows)
        bad_rows['after']['normalized']['topology']['closed_oriented_combinatorial_surface_screen_pass'] = False
        self.assertFalse(module.declared_screen(native, bad_rows, roi))
        bad_vdb = copy.deepcopy(native)
        bad_vdb['native_VDB']['roundtrip_bitwise_comparison']['0']['exact_value_comparison_pass'] = False
        self.assertFalse(module.declared_screen(bad_vdb, rows, roi))


if __name__ == '__main__':
    unittest.main()
