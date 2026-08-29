import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "twins" / "993-cabin-dashboard-switch-0001" / "source" / "check_fit.py"
SPEC = importlib.util.spec_from_file_location("check_fit", MODULE_PATH)
check_fit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(check_fit)


def reading(value, uncertainty=0.1):
    return {"value": value, "uncertainty": uncertainty, "unit": "mm"}


class TwinFitTests(unittest.TestCase):
    def test_positive_worst_case_margins_pass(self) -> None:
        values = {
            "D01": reading(30), "D02": reading(20), "D05": reading(8),
            "D08": reading(27), "D09": reading(17), "H01": reading(28),
            "H02": reading(18), "H03": reading(3), "H05": reading(12),
        }
        report = check_fit.calculate(values)
        self.assertTrue(report["passed"])
        self.assertAlmostEqual(report["metrics"]["horizontal_clearance"]["worst_case_margin_mm"], 0.8)

    def test_uncertainty_can_fail_nominal_clearance(self) -> None:
        values = {
            "D01": reading(30), "D02": reading(20), "D05": reading(8),
            "D08": reading(27.9, 0.1), "D09": reading(17), "H01": reading(28, 0.1),
            "H02": reading(18), "H03": reading(3), "H05": reading(12),
        }
        report = check_fit.calculate(values)
        self.assertFalse(report["passed"])
        self.assertLess(report["metrics"]["horizontal_clearance"]["worst_case_margin_mm"], 0)


if __name__ == "__main__":
    unittest.main()

