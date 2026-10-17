import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT/'twins/m64-cylinder-head/source/bionic-fin-integration'
SPEC = importlib.util.spec_from_file_location('fin_integration_inspector', HERE/'audit.py')
module = importlib.util.module_from_spec(SPEC)
try:
    SPEC.loader.exec_module(module)
except ImportError:
    module = None


@unittest.skipIf(module is None, 'NumPy required')
class IntegrationTests(unittest.TestCase):
    def test_sparse_raw_audit_matches_existing_analytic_witness(self):
        import numpy as np
        try:
            import scipy.sparse.linalg
        except ImportError:
            self.skipTest('Working SciPy required for sparse connectivity')
        vertices = np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
        triangles = vertices[np.array([[1,2,3],[0,3,2],[0,1,3],[0,2,1]])]
        for array in (triangles, np.concatenate([triangles, triangles+3]), triangles[:-1]):
            expected = module.mesh.mesh_summary(array)
            actual = module.raw_surface_summary(array)
            for key in ('connected_vertex_components', 'boundary_edges', 'nonmanifold_edges',
                        'edge_manifold_closed', 'winding_consistent_on_two_face_edges',
                        'zero_area_triangles', 'duplicate_triangles_ignoring_winding'):
                self.assertEqual(actual[key], expected[key])
            self.assertAlmostEqual(actual['signed_volume_scan_units_cubed'], expected['signed_volume_scan_units_cubed'])
        self.assertAlmostEqual(module.raw_surface_summary(triangles)['signed_volume_scan_units_cubed'], 1/6)

    def test_changed_zone_mask_and_independent_reference_separation(self):
        import numpy as np
        c = json.loads((HERE/'contract.json').read_text())
        points = np.array([[49, 0, 20], [-50, 30, 44], [47, 0, 20], [50, 36, 20], [50, 0, 50]])
        self.assertEqual(module.in_zones(points, c['modified_zones'], 0).tolist(), [True, True, False, False, False])
        self.assertAlmostEqual(module.bbox_clearance(np.array([-43,-40,0]), np.array([43,40,90]), c['modified_zones'], .6), 4.4)
        self.assertEqual(module.bbox_clearance(np.array([49,0,20]), np.array([51,1,21]), c['modified_zones'], .6), 0)

    def test_unqualified_or_changed_protected_region_is_rejected(self):
        c = json.loads((HERE/'contract.json').read_text())
        good = dict(schema='m64-bionic-head-integration/v1', fin_count=6, units=c['units'], voxel_scan_units=.3,
                    outside_mask_halo_changes=dict(added_triangles=0, removed_triangles=0),
                    core_preservation_is_at_voxel_resolution_only=True,
                    files=[dict(filename=n+'.stl') for n in ('baseline', 'head-bionic', 'fins', 'added', 'removed')])
        keys = ('source_master_modified', 'full_functional_assembly', 'thermal_gain_transferred_from_coupon',
                'thermal_simulation', 'structural_simulation', 'manufacturing_authorized',
                'physical_root_attachment_verified', 'measured_interfaces_verified')
        good.update({k: False for k in keys})
        self.assertEqual(len(module.validate_report(good, c)), 5)
        for key in keys:
            bad = copy.deepcopy(good); bad[key] = True
            with self.assertRaises(ValueError):
                module.validate_report(bad, c)
        for changes in ({'added_triangles': 1, 'removed_triangles': 0}, None):
            bad = dict(good, outside_mask_halo_changes=changes)
            with self.assertRaises(ValueError):
                module.validate_report(bad, c)
        native = dict(good, representation='native_cad_with_analytic_picogk_profile_counterpart',
                      native_solid_count=1, native_shell_count=1, native_validity_and_readback_passed=True,
                      native_outside_mask_solid_counts=[0, 0], core_preservation_is_at_voxel_resolution_only=False)
        self.assertEqual(len(module.validate_report(native, c)), 5)
        for change in (dict(native_solid_count=2), dict(native_outside_mask_solid_counts=[1, 0]),
                       dict(native_validity_and_readback_passed=False)):
            with self.assertRaises(ValueError):
                module.validate_report(dict(native, **change), c)

    def test_native_counterpart_reuses_the_profile_and_preserves_symmetry(self):
        import numpy as np
        spec = importlib.util.spec_from_file_location('native_fin_builder', HERE/'build_native.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        c = json.loads((HERE/'contract.json').read_text())
        e = json.loads((HERE.parent/'bionic-fins/candidate.json').read_text())['edges'][0]
        right = np.array(builder.vertices(e, 1, 16, c))
        left = np.array(builder.vertices(e, -1, 16, c))
        self.assertTrue(np.all(right[:, 1] == -35))
        self.assertAlmostEqual(np.linalg.norm(right[0]-right[3]), e['t0_mm'])
        self.assertAlmostEqual(np.linalg.norm(right[1]-right[2]), e['t1_mm'])
        self.assertTrue(np.allclose(np.sort(-right[:, 0]), np.sort(left[:, 0])))
        self.assertEqual(builder.material_balance(100, 5, 10, 95), (0, 0))
        self.assertAlmostEqual(builder.material_balance(100, 5, 10, 94)[1], builder.material_balance(1e8, 5e6, 1e7, 9.4e7)[1])
        self.assertGreater(builder.material_balance(100, 5, 10, 94)[1], 1e-10)
        with self.assertRaises(ValueError):
            builder.material_balance(float('nan'), 5, 10, 95)

    def test_existing_profile_and_reference_pins_are_retained(self):
        c = json.loads((HERE/'contract.json').read_text())
        self.assertEqual(module.mesh.sha256(HERE.parent/'bionic-fins/candidate.json'), c['profile_sha256'])
        self.assertEqual(c['root_z'], [16, 30, 44])
        self.assertFalse(c['source_master_modified'])
        self.assertIsNone(c['measured_engine_interfaces'])
        self.assertIsNone(c['thermal_gain_for_integrated_head'])
        self.assertFalse(c['manufacturing_authorized'])


if __name__ == '__main__':
    unittest.main()
