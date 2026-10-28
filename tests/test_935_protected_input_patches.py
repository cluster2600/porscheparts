"""The published patch must reproduce the independently certified native source."""
import hashlib
import json
from fractions import Fraction
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'twins/935-horizontal-cooling-system-f0/source/analysis-simplification'


class ProtectedInputPatchTests(unittest.TestCase):
    def test_documented_patch_application_in_a_checkout(self):
        with tempfile.TemporaryDirectory() as folder:
            checkout = Path(folder)
            subprocess.run(['git', 'init', '-q', folder], check=True, capture_output=True)
            target = checkout / 'work/NEW-protected-source'
            target.mkdir(parents=True)
            shutil.copyfile(SOURCE / 'quality_preserving_simplify.cpp', target / 'quality_preserving_simplify.cpp')
            subprocess.run(['git', 'apply', '--directory=work/NEW-protected-source',
                            str(SOURCE / 'protected-input-patches-20261022.patch')],
                           cwd=checkout, check=True, capture_output=True)
            self.assertEqual(hashlib.sha256((target / 'quality_preserving_simplify.cpp').read_bytes()).hexdigest(),
                             '3e19ea9a93c5f11fe71a0742d383c974dae8201b50d6827f2726b4e5b15198d4')

    def test_complete_fields_do_not_override_quality_or_convergence(self):
        r = json.loads((ROOT / 'docs/research/935-horizontal-cooling/quadratic-rotor-20261022.json').read_text())
        for path, expected in r['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected)
        for flag, value in r['scope'].items():
            self.assertIs(value, False, flag)
        self.assertTrue(r['surface']['certificate']['complete_containment_pass'])
        self.assertTrue(r['volume']['exact_boundary_coordinate_triangle_bijection'])
        self.assertEqual(r['volume']['exact_orientation']['zero'], 0)
        self.assertEqual(r['volume']['exact_orientation']['negative'], 0)
        self.assertFalse(r['quality']['mechanical_mesh_admitted'])
        self.assertEqual(r['FEA_preparation']['whole_simplex_refused_cells'], 0)
        self.assertLess(r['FEA_preparation']['numeric_transport_budget_native_units'], 1e-8)
        self.assertLessEqual(float(Fraction(r['FEA_preparation']['exact_complete_numeric_transport_L1_bound'])),
                             r['FEA_preparation']['numeric_transport_budget_native_units'])
        runs = r['structural_executions']
        self.assertEqual(runs['P1-mac']['binary_sha256'], runs['P2-mac']['binary_sha256'])
        self.assertEqual(runs['P1-kali']['deck_sha256'], runs['P1-mac']['deck_sha256'])
        for name, run in runs.items():
            self.assertTrue(run['equilibrium_pass'], name)
            self.assertLess(run['relative_force_balance_error'], 1e-5)
            self.assertLess(run['relative_moment_balance_error'], 1e-5)
            gauss = 4 if run['formulation'] == 'C3D10' else 1
            self.assertEqual(run['integration_points_checked'], gauss * run['elements'])
        self.assertTrue(r['comparison']['cross_platform_P1']['passed'])
        gap = r['comparison']['same_runtime_P1_P2']['metrics']['maximum_displacement_mm']['absolute_relative_difference_to_P2']
        self.assertGreater(gap, .05)
        self.assertTrue(r['peak_location']['coincides_with_worst_mean_ratio_and_condition'])
        self.assertEqual(r['refinement']['exit'], 0)
        self.assertGreater(r['refinement']['boundary_change']['removed_boundary_triangles'], 0)
        self.assertFalse(r['refinement']['boundary_change']['boundary_certificate_reused'])
        self.assertFalse(r['refinement']['mechanical_mesh_admitted'])
        self.assertTrue(r['runtime_state']['all_solver_jobs_finished'])
        self.assertFalse(r['runtime_state']['new_paid_instance_created'])
