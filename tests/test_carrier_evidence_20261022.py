"""Public numerical claims remain bound to executed receipts and fixed limits."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'docs/reports/carrier-convergence-20261022'


class EvidenceTests(unittest.TestCase):
    def test_every_published_exact_copy_keeps_its_recorded_digest(self):
        manifest=json.loads((REPORT/'evidence-copy-manifest.json').read_text())
        self.assertGreater(len(manifest['exact_copies']),50)
        for row in manifest['exact_copies']:
            with self.subTest(path=row['path']):self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),row['sha256'])

    def test_actual_cuda_and_cpu_pass_the_same_unchanged_oracle_limit(self):
        reports=[json.loads((REPORT/f'evidence/warp/results/carrier-{device}/report.json').read_text())for device in ['cpu','cuda']]
        for row in reports:
            self.assertEqual(row['status'],'passed');self.assertEqual(row['fixed_absolute_error_limit_mm'],.0001);self.assertEqual(row['queries'],65536);self.assertLessEqual(row['maximum_absolute_error_mm'],.0001)
        self.assertTrue(reports[1]['gpu_validated']);self.assertEqual(reports[1]['actual_device'],'cuda:0');self.assertEqual(reports[0]['source_sha256'],reports[1]['source_sha256'])

    def test_refused_and_incomplete_solves_never_become_convergence(self):
        bad=json.loads((REPORT/'evidence/h0-P1-native-001-energy-diagnostic-001/assessment.json').read_text());self.assertGreater(bad['relative_energy_residual'],bad['fixed_relative_limit'])
        timeout=json.loads((REPORT/'evidence/refused-fine-and-tetgen-collected-001/h1-P2-native-001/actual-terminal.json').read_text());self.assertEqual(timeout['actual_returncode'],124);self.assertTrue(timeout['outer_timeout']);self.assertTrue(timeout['process_reaped']);self.assertFalse(timeout['solver_finished_marker'])
        comparison=json.loads((REPORT/'evidence/P1-comparison.json').read_text());self.assertFalse(comparison['convergence_demonstrated'])


if __name__=='__main__':unittest.main()
