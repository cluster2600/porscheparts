"""Check heat/power conservation without allowing an assumed COP to qualify hardware."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAMILY = ROOT / "twins/962-cylinder-head-f0"
SOURCE = FAMILY / "source/thermal_budget.py"
spec = importlib.util.spec_from_file_location("thermal_budget", SOURCE)
thermal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thermal)


class ThermalBudgetTests(unittest.TestCase):
    def test_cold_heat_and_all_electrical_inputs_are_rejected_to_ambient(self):
        for cop in (.5, 1, 2):
            r = thermal.calculate(1000, cop, 14, .9, 30)["results"]
            self.assertAlmostEqual(r["tec_hot_side_rejection_w"], 1000 + r["tec_electrical_input_w"])
            self.assertAlmostEqual(r["total_added_ambient_rejection_w"],
                                   r["tec_hot_side_rejection_w"] + r["converter_loss_w"] + 30)
            self.assertAlmostEqual(r["bus_current_a"] * 14, r["bus_input_w"])

    def test_converter_and_auxiliaries_do_not_become_tec_cooling(self):
        r = thermal.calculate(1000, 1, 14, .5, 90)["results"]
        self.assertEqual(r["tec_electrical_input_w"], 1000)
        self.assertEqual(r["tec_hot_side_rejection_w"], 2000)
        self.assertEqual(r["bus_input_w"], 2090)
        self.assertEqual(r["total_added_ambient_rejection_w"], 3090)

    def test_invalid_inputs_and_overflow_never_emit_a_budget(self):
        for position, invalid in [(0, -1), (0, float("nan")), (0, float("inf")),
                                  (1, 0), (2, 0), (3, 0), (3, 1.1), (4, -1),
                                  (1, True), (1, "1")]:
            values = [1000, 1, 14, .9, 0]; values[position] = invalid
            with self.subTest(position=position, invalid=invalid), self.assertRaises(ValueError):
                thermal.calculate(*values)
        with self.assertRaises(ValueError):
            thermal.calculate(1e308, 1e-300, 14, .9, 0)

    def test_cli_rejects_nonfinite_input_without_json_output(self):
        run = subprocess.run([sys.executable, str(SOURCE), "--cold-load-w", "nan",
                              "--assumed-cop", "1", "--assumed-bus-v", "14",
                              "--assumed-dc-efficiency", ".9", "--auxiliaries-w", "0"],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, "")

    def test_committed_examples_use_the_bound_calculator(self):
        report = json.loads((FAMILY / "derived/thermal-budget-examples.json").read_text())
        self.assertEqual(report["calculator_sha256"], hashlib.sha256(SOURCE.read_bytes()).hexdigest())
        for case in report["cases"]:
            result = thermal.calculate(case["cold_load_w"], case["assumed_cop"], **report["common_assumptions"])
            self.assertEqual(result["results"], case["results"])
            self.assertIs(result["hardware_qualified"], False)

    def test_base_cooling_remains_required_and_hardware_unknown(self):
        data = json.loads((FAMILY / "thermal-module.json").read_text())
        self.assertTrue(data["base_cooling_without_tec_required"])
        self.assertTrue(data["hot_side_rejection_includes_tec_power"])
        self.assertFalse(data["automotive_gain_validated"])
        self.assertFalse(data["manufacturing_authorized"])
        self.assertTrue(all(v is None for v in data["unknown_inputs"].values()))


if __name__ == "__main__":
    unittest.main()
