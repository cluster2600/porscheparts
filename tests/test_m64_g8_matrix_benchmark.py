"""Check triangle reconstruction, DOF mapping and bounded CPU benchmark plumbing."""
import hashlib
import json
import statistics
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'twins/m64-cylinder-head/source/fourvalve'))
try:
    import numpy as np
    import scipy.sparse.linalg
    import g8_matrix_benchmark as bench
except ImportError:
    bench = None


@unittest.skipIf(bench is None, 'optional NumPy/SciPy sparse runtime unavailable; use benchmark venv')
class MatrixBenchmarkChecks(unittest.TestCase):
    def test_mapping_triangle_solver_and_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stiffness, dofs = root / 'matrix.sti', root / 'matrix.dof'
            # Non-node-sorted DOF order catches accidental contiguous-node assumptions.
            dofs.write_text('2.3\n2.1\n2.2\n')
            stiffness.write_text('1 1 4\n1 2 -1\n2 2 3\n2 3 -1\n3 3 2\n')
            matrix, mapping = bench.read_matrix(stiffness, dofs, {1: (), 2: ()}, {1: ()})
            self.assertEqual(mapping, [(2, 3), (2, 1), (2, 2)])
            np.testing.assert_array_equal(matrix.toarray(), [[4, -1, 0], [-1, 3, -1], [0, -1, 2]])
            expected = np.array([1., 2., 3.])
            rhs = matrix @ expected
            u, result = bench.solve(matrix, rhs, 'cpu')
            np.testing.assert_allclose(u, expected, rtol=1e-10)
            self.assertEqual(result['info'], 0)
            check = bench.comparison(matrix, rhs, mapping, u, {1: (0, 0, 0), 2: (2, 3, 1)})
            self.assertLess(check['max_nodal_difference_over_max_reference_U'], 1e-10)
            self.assertLess(check['printed_dat_relative_residual'], 1e-10)
            wrong = bench.comparison(matrix, rhs, mapping, u, {1: (0, 0, 0), 2: (3, 2, 1)})
            self.assertGreater(wrong['printed_dat_relative_residual'], wrong['printed_dat_rounding_residual_bound'])
            with self.assertRaises(TimeoutError):
                bench.solve(matrix, rhs, 'cpu', max_seconds=-1)
            original = stiffness.read_text()
            for bad in (original + '1 1 1\n', original.replace('1 1 4', '1 1 nan'),
                        original.replace('3 3 2', '3 3 -2'), original + '2 1 -1\n'):
                stiffness.write_text(bad)
                with self.assertRaises(ValueError):
                    bench.read_matrix(stiffness, dofs, {1: (), 2: ()}, {1: ()})
            stiffness.write_text(original)
            dofs.write_text('2.1\n2.1\n2.3\n')
            with self.assertRaises(ValueError):
                bench.read_matrix(stiffness, dofs, {1: (), 2: ()}, {1: ()})


class PublishedAuditChecks(unittest.TestCase):
    def test_gpu_trials_keep_scope_and_verified_cleanup(self):
        directory = ROOT / 'twins/m64-cylinder-head/evidence/g8-matrix-benchmark-20260925'
        report = json.loads((directory / 'vast-trials.json').read_text())
        execution = json.loads((directory / 'execution.json').read_text())
        rows = report['trials']
        self.assertEqual(len(rows), 6)
        self.assertTrue(report['fresh_direct_comparisons_and_equation_residuals_passed'])
        self.assertFalse(report['original_G8_reference_gate_passed'])
        for row in rows:
            self.assertEqual(row['hashes'], rows[0]['hashes'])
            self.assertEqual(row['dtype'], 'float64')
            self.assertFalse(row['accepted'])
            self.assertLess(row['relative_residual'], 1e-8)
            for reference in row['additional_comparisons']:
                self.assertLess(reference['max_nodal_difference_over_max_reference_U'], 1e-4)
        for backend in ('cpu', 'cuda'):
            group = [r for r in rows if r['backend'] == backend]
            self.assertEqual([r['trial'] for r in group], [1, 2, 3])
            self.assertEqual(statistics.median(r['solve_seconds'] for r in group), report[f'median_{backend}_solve_seconds'])
        life = execution['lifecycle']
        for key in ('external_guard_armed_before_rental', 'provider_destroyed',
                    'provider_verified_absent', 'external_guard_verified_absent', 'inventory_empty_after_cleanup'):
            self.assertTrue(life[key])
        self.assertLessEqual(life['planned_with_cleanup_reserve_usd'], life['run_budget_usd'])
        self.assertLessEqual(life['run_budget_usd'], 5)
        self.assertFalse(execution['manufacturing_authorized'])
        self.assertFalse(execution['engine_start_authorized'])

    def test_historical_failure_is_not_silently_cleared(self):
        path = ROOT / 'twins/m64-cylinder-head/evidence/g8-matrix-benchmark-20260925/cpu-reference-audit.json'
        report = json.loads(path.read_text())
        source = ROOT / 'twins/m64-cylinder-head/source/fourvalve/g8_matrix_benchmark.py'
        self.assertEqual(report['hashes']['source'], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertFalse(report['accepted'])
        self.assertFalse(report['manufacturing_authorized'])
        self.assertFalse(report['engine_start_authorized'])
        self.assertLess(report['relative_residual'], 1e-8)
        old = report['original_reference']
        self.assertGreater(old['max_nodal_difference_over_max_reference_U'], 1e-4)
        self.assertGreater(old['printed_dat_relative_residual'], old['printed_dat_rounding_residual_bound'])
        self.assertEqual(len(report['additional_comparisons']), 4)
        for fresh in report['additional_comparisons']:
            self.assertLess(fresh['max_nodal_difference_over_max_reference_U'], 1e-4)
            self.assertLess(fresh['printed_dat_relative_residual'], fresh['printed_dat_rounding_residual_bound'])


if __name__ == '__main__':
    unittest.main()
