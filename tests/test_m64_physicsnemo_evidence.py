import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'twins/m64-cylinder-head'


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.pilot = json.loads((BASE / 'evidence/physicsnemo-mesh-pilot-20260912.json').read_text())
        self.stock = json.loads((BASE / 'evidence/physicsnemo-mesh-stock-20260912.json').read_text())
        self.cross = json.loads((BASE / 'evidence/physicsnemo-mesh-cross-20260912.json').read_text())

    def test_reports_and_input_identities(self):
        for kind in ('stock', 'cross'):
            result = self.pilot['results']
            path = BASE / 'evidence' / result[kind + '_report']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), result[kind + '_report_sha256'])
        self.assertEqual(self.stock['pins'], self.cross['input_pins'])
        self.assertEqual(self.stock['array_sha256'], self.cross['array_sha256'])
        self.assertEqual(self.stock['triangles'], 293308)
        for report in (self.stock, self.cross):
            self.assertTrue(report['inputs_unchanged'])
            self.assertTrue(report['ordered_triangle_equivalence_verified'])

    def test_exact_source_bindings(self):
        for filename, expected in (
            ('benchmark_mesh.py', self.stock['benchmark_source_sha256']),
            ('benchmark_cross_adapter.py', self.cross['adapter_sha256']),
        ):
            path = BASE / 'source/physicsnemo-mesh' / filename
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)
        self.assertEqual(self.stock['source_pins'], self.cross['upstream_source_pins'])

    def test_refusal_and_pass_are_not_confused(self):
        self.assertFalse(self.stock['numerical_comparison_passed'])
        self.assertTrue(self.cross['numerical_comparison_passed'])
        self.assertTrue(self.cross['witnesses_passed'])
        for device in ('cpu', 'cuda'):
            native = self.stock['comparisons'][device + '_vs_numpy']['areas']
            adapted = self.cross['comparisons'][device + '_vs_numpy']['areas']
            self.assertEqual(native['failed_cells'], 4438)
            self.assertEqual(adapted['failed_cells'], 0)
            self.assertEqual(native['rtol'], adapted['rtol'])
            self.assertEqual(native['atol'], adapted['atol'])
            self.assertEqual(native['positive_reference_but_zero_area'], 0)
        self.assertTrue(self.stock['cuda']['library_witnesses']['gram_positive_area_lost'])
        self.assertFalse(self.cross['upstream_monkeypatched'])

    def test_scope_and_cleanup(self):
        for report in (self.pilot, self.stock, self.cross):
            self.assertIs(report['CFD_authorized'], False)
            self.assertIs(report['manufacturing_authorized'], False)
        life = self.pilot['lifecycle']
        for key in ('instance_destroyed', 'provider_verified_absent',
                    'external_guard_verified_absent', 'inventory_empty_after_cleanup'):
            self.assertIs(life[key], True)
        self.assertLess(life['observed_credit_decrease_usd'], life['budget_cap_usd'])
        self.assertTrue(self.pilot['results']['ratios_exclude_transfers_warmup_and_bootstrap'])
        self.assertEqual(self.pilot['source_geometry']['moved_vertices'], 0)


if __name__ == '__main__':
    unittest.main()
