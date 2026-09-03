"""Tests fail-closed du plan de qualification matière F38."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/f38-material-coupon-qualification.json"
SOURCE = ROOT / "twins/reference-917-engine/source/plan_f38_hot_coupon_qualification.py"


def load_module():
    spec = importlib.util.spec_from_file_location("f38_coupon_plan", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot_import_f38_coupon_plan")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class F38MaterialCouponPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.plan = load_module().build_plan(cls.contract, CONTRACT)

    def test_candidate_is_process_specific_and_still_conditional(self):
        candidate = self.contract["candidate"]
        self.assertEqual(candidate["machine"], "EOS M 290")
        self.assertEqual(candidate["layer_thickness_um"], 60)
        self.assertEqual(candidate["supplier_process_trl"], 3)
        self.assertIn("conditional", candidate["selection_status"])

    def test_matrix_covers_hot_strength_fatigue_creep_and_thermal_card(self):
        ids = {row["id"] for row in self.plan["matrix"]}
        self.assertEqual(
            ids,
            {
                "tensile_hot",
                "low_cycle_fatigue_hot",
                "high_cycle_fatigue_hot",
                "creep_hot",
                "thermal_diffusivity_conductivity",
                "thermal_expansion",
                "density_metallography_ct",
            },
        )
        self.assertGreaterEqual(self.plan["coupon_count_total"], 150)
        all_temperatures = {
            temperature
            for row in self.plan["matrix"]
            for temperature in row["temperatures_degC"]
        }
        self.assertTrue({20, 150, 200, 250, 300}.issubset(all_temperatures))

    def test_supplier_values_are_not_promoted_to_design_allowables(self):
        acceptance = self.plan["acceptance_logic"]
        self.assertIn("no supplier typical value", acceptance["design_allowable"])
        self.assertIn("extrapolation", acceptance["out_of_range_action"])
        self.assertEqual(acceptance["statistical_basis"], "one-sided 95/90 lower tolerance bound where applicable")

    def test_release_is_fail_closed_until_physical_campaign(self):
        self.assertFalse(self.plan["result"]["campaign_executed"])
        self.assertFalse(self.plan["result"]["material_card_qualified"])
        self.assertFalse(self.plan["result"]["manufacturing_authorized"])
        self.assertTrue(all(value is False for value in self.plan["release_gates"].values()))

    def test_only_official_supplier_sources_are_used(self):
        urls = [item["url"] for item in self.plan["official_sources"]]
        self.assertTrue(any(url.startswith("https://www.eos.info/") for url in urls))
        self.assertTrue(any(url.startswith("https://www.constellium.com/") for url in urls))


if __name__ == "__main__":
    unittest.main()
