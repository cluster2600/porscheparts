"""Issue #418: skips are grouped per reason and the budget file is well formed."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from run_tests_with_skip_report import BUDGET, report_lines, summarise  # noqa: E402


class _Fake:
    def __init__(self, ident):
        self.ident = ident

    def id(self):
        return self.ident


class SkipReportTests(unittest.TestCase):
    def test_skips_group_by_normalised_reason(self):
        skipped = [(_Fake('test_a.A.test_1'), 'trimesh  unavailable'),
                   (_Fake('test_b.B.test_1'), 'trimesh unavailable'),
                   (_Fake('test_a.A.test_2'), 'OCP unavailable')]
        rows = summarise(skipped)
        self.assertEqual(rows[0], ('trimesh unavailable', 2, ['test_a', 'test_b']))
        lines = report_lines(rows, 3, 5)
        self.assertIn('## Test skips: 3 (budget 5)', lines[0])

    def test_budget_is_a_non_negative_integer(self):
        budget = json.loads(BUDGET.read_text())['max_skips']
        self.assertIsInstance(budget, int)
        self.assertGreaterEqual(budget, 0)


if __name__ == '__main__':
    unittest.main()
