import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/picogk-local-junction-buffered-v2'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SOURCE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(importlib.util.find_spec('numpy'), 'NumPy required for numerical audit')
class HardenedBufferedDecision(unittest.TestCase):
    def setUp(self):
        self.module = load('audit_buffered_surface')
        self.native = {name: [0, 0] for name in ('outside_ROI_changed_nodes', 'protected_changed_nodes',
                       'lost_original_gas_nodes', 'added_nodes_touching_ROI_boundary')}
        self.native.update({'changed_nodes': [1, 1], 'native_VDB': {'roundtrip_bitwise_comparison': {
            name: {'exact_value_comparison_pass': True, 'bitwise_value_differences': 0,
                   'max_abs_delta_world_units': 0, 'compared_native_bbox_nodes': 1, 'bbox_indices_equal': True}
            for name in self.module.FIELD_NAMES}}, 'SDF_comparison': {'finite_comparable_pairs': 1,
                'unavailable_pairs': 0, 'outside_ROI_value_changes': 0, 'protected_value_changes': 0,
                'max_abs_outside_ROI_delta_world_units': 0, 'max_abs_protected_delta_world_units': 0}})
        self.rows = {name: {'normalized': {'topology': {'closed_oriented_combinatorial_surface_screen_pass': True}}}
                     for name in ('before', 'after', 'added')}
        self.roi = {'all_changed_triangle_supports_inside_convex_ROI': True}

    def decision(self, native=None, rows=None, roi=None):
        return self.module.declared_screen(self.native if native is None else native,
                                          self.rows if rows is None else rows, self.roi if roi is None else roi)

    def test_complete_baseline_passes(self):
        self.assertTrue(self.decision())

    def test_each_SDF_failure_rejects_even_if_flags_pass(self):
        for key in self.native['SDF_comparison']:
            bad = copy.deepcopy(self.native)
            bad['SDF_comparison'][key] = 0 if key == 'finite_comparable_pairs' else 1
            self.assertFalse(self.decision(bad), key)
        for invalid in (float('nan'), float('inf')):
            bad = copy.deepcopy(self.native)
            bad['SDF_comparison']['max_abs_outside_ROI_delta_world_units'] = invalid
            self.assertFalse(self.decision(bad))

    def test_each_VDB_failure_rejects(self):
        name = sorted(self.module.FIELD_NAMES)[0]
        for key, value in [('exact_value_comparison_pass', False), ('bitwise_value_differences', 1),
                           ('max_abs_delta_world_units', 1e-10), ('compared_native_bbox_nodes', 0), ('bbox_indices_equal', False)]:
            bad = copy.deepcopy(self.native)
            bad['native_VDB']['roundtrip_bitwise_comparison'][name][key] = value
            self.assertFalse(self.decision(bad), key)
        bad = copy.deepcopy(self.native)
        bad['native_VDB']['roundtrip_bitwise_comparison']['unexpected'] = bad['native_VDB']['roundtrip_bitwise_comparison'].pop(name)
        self.assertFalse(self.decision(bad))

    def test_each_occupation_failure_and_empty_surface_set_reject(self):
        for key in ('outside_ROI_changed_nodes', 'protected_changed_nodes', 'lost_original_gas_nodes', 'added_nodes_touching_ROI_boundary'):
            bad = copy.deepcopy(self.native)
            bad[key] = [0, 1]
            self.assertFalse(self.decision(bad))
        self.assertFalse(self.decision(rows={}))
        self.assertFalse(self.decision(roi={'all_changed_triangle_supports_inside_convex_ROI': False}))

    def test_actual_added_volume_threshold_and_bad_denominator(self):
        screen = load('compare_resolutions').added_volume_screen
        self.assertTrue(screen(10.5, 10, .05)['pass'])
        self.assertFalse(screen(10.5001, 10, .05)['pass'])
        for coarse, fine in [(1, 0), (0, 1), (1, -1), (float('nan'), 1), (1, float('inf'))]:
            self.assertFalse(screen(coarse, fine, .05)['pass'])

    @unittest.skipUnless(importlib.util.find_spec('vtkmodules'), 'VTK required for triangle-distance witness')
    def test_sampled_triangle_distance_numeric_witness(self):
        import numpy as np
        distance = load('compare_resolutions').sampled_distance
        target = np.array([[[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]])
        source = target + [0., 0., .1]
        row = distance(source, target, 20)
        self.assertAlmostEqual(row['maximum_world_units'], .1, places=12)
        self.assertAlmostEqual(row['mean_world_units'], .1, places=12)
        self.assertFalse(row['continuous_Hausdorff_upper_bound'])


class BufferedV2Policy(unittest.TestCase):
    def test_fixed_world_geometry_and_resource_ceiling(self):
        p = json.loads((SOURCE / 'criteria-0p1-fixed-margin.json').read_text())
        self.assertEqual(p['voxel_world_units'], .1)
        self.assertEqual(p['fixed_interior_margin_world_units'], .6)
        self.assertEqual(p['margin_voxels_at_this_resolution'], 6)
        self.assertEqual(p['audit_resource_only_opt_in_max_faces_fine'], 500000)
        self.assertEqual(p['relative_actual_added_volume_difference_threshold'], .05)
        self.assertEqual(p['sampled_bidirectional_surface_distance_threshold_world_units'], .2)
        self.assertFalse(p['historical_helper_limits_modified_on_disk'])


if __name__ == '__main__':
    unittest.main()
