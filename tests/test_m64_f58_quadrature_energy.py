from decimal import Decimal
import importlib.util
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "twins/m64-cylinder-head/source"
spec = importlib.util.spec_from_file_location("quadrature", HERE / "compare_f58_quadrature_40us.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
PARSER = ROOT / "twins/reference-917-engine/source/additive_energy_diagnostic_f58.py"


def log_rows(count=1600, capped=False, laser_zero=False):
    result = []
    for i in range(1, count + 1):
        values = [Decimal(i)*Decimal("2.5e-8"), "2.5e-8", "3300" if capped else "900",
                  "30", "20", "5", "50", "0", "5", "0"]
        if laser_zero:
            values[3:10] = ["0"] * 7
        result.append("F58_BALANCE " + " ".join(map(str, values)))
    return "\n".join(result) + "\n"


class EnergyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.a, self.b, self.output = (self.root / name for name in ("q10.log", "q20.log", "report.json"))
        self.a.write_text(log_rows())
        self.b.write_text(log_rows())

    def compare(self):
        return m.compare(self.a, m.digest(self.a), self.b, m.digest(self.b), PARSER, self.output)

    def test_complete_is_distinct_from_historical_and_native(self):
        result = self.compare()
        self.assertTrue(result["common_window_complete_40us"])
        self.assertFalse(result["native_executed"])
        self.assertFalse(result["solver_exit_status_verified"])
        case = result["cases"]["q10"]
        self.assertFalse(case["historical_evaluation_120us_criterion_unchanged"]["time_series_complete"])
        self.assertEqual(case["integrated_terms"]["laser_in_j"], .002)
        self.assertEqual(case["absolute_residual_energy_j"], 0)

    def test_cap_does_not_block_diagnostic_completeness(self):
        self.b.write_text(log_rows(capped=True))
        result = self.compare()
        self.assertTrue(result["common_window_complete_40us"])
        self.assertTrue(result["cases"]["q20"]["temperature_censored"])
        self.assertFalse(result["cases"]["q20"]["temperature_validated"])
        self.assertEqual(result["max_paired_temperature_difference_k"], 2400)

    def test_missing_step_refused(self):
        self.b.write_text(log_rows(count=1599))
        with self.assertRaisesRegex(ValueError, "1600"):
            self.compare()

    def test_extra_step_refused(self):
        self.b.write_text(log_rows(count=1601))
        with self.assertRaisesRegex(ValueError, "1600"):
            self.compare()

    def test_component_corruption_refused(self):
        self.b.write_text(log_rows().replace("30 20 5 50 0 5 0", "30 20 5 50 0 5 1", 1))
        with self.assertRaisesRegex(ValueError, "residual inconsistent"):
            self.compare()

    def test_nonfinite_refused(self):
        self.b.write_text(log_rows().replace("900", "NaN", 1))
        with self.assertRaisesRegex(ValueError, "invalid energy"):
            self.compare()

    def test_decimal_recalculation_does_not_trust_public_result(self):
        self.b.write_text(log_rows().replace("30 20 5 50 0 5 0", "30 20 5 50 0 5 1", 1))
        trusted_result_stub = SimpleNamespace(evaluate=lambda path, dt: {"fatal_error_in_log": False})
        with self.assertRaisesRegex(ValueError, "decimal_component_residual_disagreement"):
            m.analyze(self.b, trusted_result_stub)

    def test_nonzero_advection_refused_even_if_balanced(self):
        self.b.write_text(log_rows().replace("30 20 5 50 0 5 0", "29 20 5 50 1 5 0", 1))
        with self.assertRaisesRegex(ValueError, "nonzero_advection"):
            self.compare()

    def test_fatal_refused(self):
        self.b.write_text(log_rows() + "FOAM FATAL ERROR\n")
        with self.assertRaisesRegex(ValueError, "fatal_error"):
            self.compare()

    def test_wrong_dt_refused(self):
        self.b.write_text(log_rows().replace("2.5e-8", "5e-8", 1))
        with self.assertRaisesRegex(ValueError, "time step differs"):
            self.compare()

    def test_hash_refused(self):
        with self.assertRaisesRegex(ValueError, "input_sha_mismatch"):
            m.compare(self.a, "0"*64, self.b, m.digest(self.b), PARSER, self.output)

    def test_zero_denominator_is_null(self):
        self.a.write_text(log_rows(laser_zero=True))
        self.b.write_text(log_rows(laser_zero=True))
        result = self.compare()
        self.assertIsNone(result["cases"]["q10"]["limiter_fraction_of_absorbed"])
        self.assertIsNone(result["integral_differences"]["laser_in_j"]["relative_to_q20"])

    def test_existing_output_preserved(self):
        self.output.write_text("original")
        with self.assertRaisesRegex(ValueError, "output_must_be_new"):
            self.compare()
        self.assertEqual(self.output.read_text(), "original")

    def test_pair_time_grids_must_match_exactly(self):
        lines = []
        for line in log_rows().splitlines():
            values = line.split()
            values[1] = str(Decimal(values[1]) + Decimal("1e-17"))
            lines.append(" ".join(values))
        self.b.write_text("\n".join(lines))
        with self.assertRaisesRegex(ValueError, "paired_sample_times_differ"):
            self.compare()


if __name__ == "__main__":
    unittest.main()
