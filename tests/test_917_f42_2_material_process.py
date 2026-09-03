import hashlib
import json
import pathlib
import unittest
import urllib.parse


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/f42-2-material-process-screen.json"
F42_1 = ROOT / "twins/reference-917-engine/evidence/f42-1-thermal-optimization/f42-1-thermal-optimization-report.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F422MaterialProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CONTRACT.read_text())

    def test_is_bound_to_F42_1_and_does_not_change_envelope(self):
        scope = self.data["scope"]
        self.assertEqual(scope["f42_1_report"]["sha256"], sha256(F42_1))
        self.assertFalse(scope["external_envelope_modified"])
        self.assertFalse(scope["f42_1_report"]["temperature_target_met"])
        self.assertGreater(scope["f42_1_report"]["lowest_executed_calculix_tmax_c"], 260)

    def test_five_real_LPBF_aluminium_candidates_use_primary_sources(self):
        materials = self.data["materials"]
        self.assertEqual(len(materials), 5)
        self.assertTrue(any("AlSi10Mg" in item["id"] for item in materials))
        self.assertTrue(any("CP1" in item["id"] for item in materials))
        self.assertTrue(any("HT1" in item["id"] for item in materials))
        allowed = {"www.eos.info", "assets.foleon.com", "www.apworks.de"}
        for item in materials:
            self.assertIn(urllib.parse.urlparse(item["source_url"]).netloc, allowed)
            self.assertIn("LPBF", item["lpbf_availability_evidence"])

    def test_missing_hot_data_are_null_and_fail_closed(self):
        for item in self.data["materials"]:
            self.assertFalse(item["numeric_tensile_260_to_350_c_available"])
            self.assertFalse(item["numeric_thermal_conductivity_260_to_350_c_available"])
            self.assertFalse(item["fatigue_260_to_350_c_available"])
            self.assertFalse(item["creep_260_to_350_c_available"])
            self.assertFalse(item["hot_band_gate"])
        ht1 = next(item for item in self.data["materials"] if "HT1" in item["id"])
        self.assertEqual(ht1["maximum_published_numeric_hot_tensile_temperature_c"], 250)
        self.assertFalse(ht1["process"]["exact_public_recipe_available"])

    def test_provisional_choice_is_not_a_selection_or_allowable(self):
        decision = self.data["provisional_decision"]
        self.assertIn("HT1", decision["screening_candidate"])
        self.assertFalse(decision["final_material_selected"])
        self.assertFalse(decision["current_F42_1_temperature_field_compatible"])
        self.assertFalse(decision["design_allowables_available"])

    def test_HIP_and_machining_are_not_invented(self):
        route = self.data["process_route"]
        self.assertEqual(route["hip"]["production_requirement"], "not_selected")
        self.assertIsNone(route["hip"]["temperature_pressure_time"])
        self.assertFalse(route["hip"]["qualified"])
        self.assertIsNone(route["machining"]["stock_allowances_mm"])
        self.assertGreaterEqual(len(route["machining"]["mandatory_finished_features"]), 7)

    def test_coupon_plan_covers_hot_tension_thermal_fatigue_CT_and_corrosion(self):
        plan = self.data["coupon_plan"]
        ids = {item["id"] for item in plan["tests"]}
        self.assertTrue({"computed_tomography", "hot_tension", "thermal_properties", "fatigue_and_creep", "seat_guide_galvanic_and_thermal_joint"}.issubset(ids))
        self.assertEqual(plan["orientations"], ["XY", "Z"])
        self.assertTrue({260.0, 300.0, 350.0}.issubset(plan["temperatures_c"]))
        ct = next(item for item in plan["tests"] if item["id"] == "computed_tomography")
        self.assertIsNone(ct["voxel_size_um"])
        self.assertIsNone(ct["acceptance_limit"])
        self.assertIsNone(plan["acceptance_values"])

    def test_seat_guide_compatibility_and_every_release_gate_stay_closed(self):
        joint = self.data["seat_guide_corrosion_control"]
        self.assertFalse(joint["seat_material_selected"])
        self.assertFalse(joint["guide_material_selected"])
        self.assertFalse(joint["compatible"])
        self.assertGreaterEqual(len(joint["controls"]), 4)
        self.assertTrue(all(value is False for value in self.data["release_gates"].values()))


if __name__ == "__main__":
    unittest.main()

