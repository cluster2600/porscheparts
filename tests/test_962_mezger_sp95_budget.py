"""Independent energy/flow identities for assumed SP95 head sizing."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FAMILY = ROOT / "twins/962-cylinder-head-f0"
spec = importlib.util.spec_from_file_location("mezger_sp95", FAMILY / "source/mezger_sp95_budget.py")
budget = importlib.util.module_from_spec(spec)
with patch.object(sys, "path", [str(FAMILY / "source"), *sys.path]):
    spec.loader.exec_module(budget)


class MezgerSP95Tests(unittest.TestCase):
    def test_full_engine_power_and_energy_close(self):
        r = budget.calculate()["results"]
        self.assertAlmostEqual(r["power_kw"], 735.49875)
        self.assertAlmostEqual(r["displacement_cm3"], 4000.65990807686)
        self.assertAlmostEqual(r["torque_nm"] * 7000 / 60 * 2 * math.pi,
                               r["power_kw"] * 1000)
        self.assertAlmostEqual(r["bmep_bar"] * 1e5 * r["displacement_cm3"] * 1e-6 * 7000 / 120,
                               r["power_kw"] * 1000)
        self.assertAlmostEqual(r["fuel_power_kw"], r["power_kw"] +
                               r["head_coolant_total_kw"] + r["unallocated_non_brake_power_kw"])
        self.assertAlmostEqual(r["fuel_kg_h"] / 3600 * 42.5e6, r["fuel_power_kw"] * 1000)

    def test_air_water_and_port_continuity(self):
        r = budget.calculate()["results"]
        self.assertAlmostEqual(r["air_kg_s"] / r["fuel_kg_h"] * 3600, 14.4 * .82)
        self.assertAlmostEqual(r["water_total_kg_s"] * 4180 * 15,
                               r["head_coolant_total_kw"] * 1000)
        self.assertAlmostEqual(r["water_each_head_l_min"] * 6, r["water_total_l_min"])
        head_area = math.pi / 4 * (r["head_port_id_at_3m_s_mm"] / 1000) ** 2
        bank_area = math.pi / 4 * (r["bank_header_id_at_3m_s_mm"] / 1000) ** 2
        self.assertAlmostEqual(head_area * 3 * 60000, r["water_each_head_l_min"])
        self.assertAlmostEqual(bank_area, head_area * 3)

    def test_sensitivities_preserve_meaning(self):
        nominal = budget.calculate()["results"]
        faster = budget.calculate(rpm=8000)["results"]
        hotter = budget.calculate(head_heat_fraction=.16)["results"]
        delta = budget.calculate(water_delta_k=30)["results"]
        self.assertLess(faster["bmep_bar"], nominal["bmep_bar"])
        self.assertLess(faster["boost_gauge_bar"], nominal["boost_gauge_bar"])
        self.assertEqual(faster["air_kg_s"], nominal["air_kg_s"])
        self.assertGreater(hotter["water_each_head_l_min"], nominal["water_each_head_l_min"])
        self.assertAlmostEqual(delta["water_total_l_min"] * 2, nominal["water_total_l_min"])

    def test_bad_inputs_fail_closed(self):
        for name, value in (("rpm", 0), ("rpm", True), ("rpm", 10**1000),
                            ("brake_efficiency", 1), ("lambda_value", float("nan")),
                            ("charge_c", -273.15), ("water_delta_k", float("inf")),
                            ("fuel_density_kg_m3", "745"), ("head_heat_fraction", .8),
                            ("fuel_lhv_j_kg", 1e-300)):
            with self.subTest(name=name), self.assertRaises(ValueError):
                budget.calculate(**{name: value})

    def test_committed_report_is_current_and_does_not_qualify_hardware(self):
        actual = json.loads((FAMILY / "derived/mezger-sp95-budget.json").read_text())
        self.assertEqual(actual, budget.report())
        self.assertFalse(any(actual["qualification"].values()))
        self.assertIsNone(actual["unknowns"]["knock_limited_boost_bar"])
        self.assertIsNone(actual["target"]["ethanol_volume_fraction"])
        self.assertAlmostEqual(actual["clearance_volume_sweep"][0]["total_clearance_volume_cm3"] * 7,
                               actual["nominal"]["results"]["displacement_cm3"] / 6)

    def test_actual_qwen_receipt_is_bound_and_rejected(self):
        folder = FAMILY / "derived/qwen-assistance/mezger-sp95-r3"
        receipt = json.loads((folder / "qwen-report.json").read_text())
        for key, path in (("prompt_sha256", FAMILY / "source/mezger-sp95-qwen-prompt.txt"),
                          ("runner_sha256", FAMILY / "source/architecture/ask_qwen.py"),
                          ("response_sha256", folder / "response.txt")):
            self.assertEqual(receipt[key], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertFalse(receipt["engineering_approval"])
        self.assertFalse(receipt["generated_code_executed"])
        self.assertEqual(json.loads((folder / "review.json").read_text())["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
