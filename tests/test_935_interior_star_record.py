"""A corrected mesh and stable bulk response must not become a strength release."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InteriorStarRecordTests(unittest.TestCase):
    def test_exact_mesh_admission_and_mechanical_limits_remain_separate(self):
        r = json.loads((ROOT / 'docs/research/935-horizontal-cooling/interior-star-20261022.json').read_text())
        for path, expected in r['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected)
        for flag, value in r['scope'].items():
            self.assertIs(value, False, flag)
        accepted, refused = r['accepted_interior_correction'], r['rejected_gmsh_relocation']
        self.assertTrue(accepted['exact_boundary_coordinate_triangle_bijection'])
        self.assertTrue(accepted['exact_volume_matches_parent'])
        self.assertEqual(accepted['exact_orientation']['negative'], 0)
        self.assertEqual(accepted['exact_orientation']['zero'], 0)
        self.assertTrue(accepted['all_nodes_used'])
        self.assertEqual(accepted['source_sha256'], r['source_sha256'][
            'twins/935-horizontal-cooling-system-f0/source/audit_interior_relocation.py'])
        self.assertTrue(refused['exact_volume_matches_parent'])
        self.assertGreater(refused['exact_orientation']['negative'], 0)
        self.assertEqual(refused['status'], 'volume_refused')
        self.assertEqual(r['no_q_control']['volume_npz_sha256'], r['no_q_control']['parent_volume_npz_sha256'])
        self.assertTrue(r['q14_refinement']['surface_certificate']['complete_containment_pass'])
        self.assertFalse(r['q14_refinement']['whole_volume_exact_audit_performed'])
        self.assertFalse(r['q14_refinement']['mechanical_mesh_admitted'])
        for name, run in r['solver_runs'].items():
            self.assertTrue(run['equilibrium_pass'])
            self.assertLess(run['relative_force_balance_error'], 1e-5)
            self.assertLess(run['relative_moment_balance_error'], 1e-5)
            self.assertEqual(run['parent_geometry_sha256'], r['unchanged_analysis_boundary_sha256'])
            self.assertEqual(run['integration_points_checked'], run['elements'] * (4 if name == 'P2' else 1))
            self.assertTrue(r['comparison']['actual_support_membership'][name]['actual_solver_support_nodes_identical'])
        metrics = r['comparison']['formulations']['P2']['metrics']
        self.assertLess(abs(metrics['maximum_displacement_mm']['relative_change']), .001)
        self.assertLess(metrics['von_mises_max_MPa']['relative_change'], -.5)
        self.assertFalse(r['comparison']['spatial_mesh_convergence_established'])
        rigid = r['rigid_properties_cross_check']
        self.assertTrue(rigid['cube_and_translation_controls_passed'])
        self.assertLess(rigid['relative_force_difference_to_tetra_integral'], 1e-8)
        self.assertFalse(rigid['physical_unbalance_measured'])
        self.assertTrue(r['all_solver_jobs_finished'])
        self.assertFalse(r['new_paid_instance_created'])
