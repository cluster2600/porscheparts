import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "twins/reference-917-engine/source/validate_manufacturing_f13.py"
)
CONTRACT = (
    ROOT / "twins/reference-917-engine/manufacturing-validation-f13.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("manufacturing_917_f13", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Manufacturing917F13Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_is_consistent_but_every_release_stays_blocked(self):
        report = self.module.evaluate(self.contract)

        self.assertEqual(report["report_status"], "passed")
        self.assertEqual(
            self.contract["asset"]["id"],
            "porsche-917-engine-manufacturing-validation-f13",
        )
        self.assertEqual(
            self.contract["asset"]["upstream_contract_reference"],
            "twins/reference-917-engine/whole-engine-reengineering-f12.json",
        )
        self.assertEqual(report["contract_errors"], [])
        self.assertEqual(
            report["decision"],
            "strategy_contract_consistent_releases_still_blocked",
        )
        self.assertTrue(all(value is False for value in report["release"].values()))
        self.assertEqual(
            report["counts"],
            {
                "family_count": 9,
                "material_candidate_count": 20,
                "route_candidate_count": 19,
                "critical_measurement_count": 30,
            },
        )

    def test_three_maturity_levels_are_distinct_and_non_functional(self):
        levels = self.contract["maturity_levels"]

        self.assertEqual(
            [item["id"] for item in levels],
            ["polymer_prototype", "metal_mockup", "functional_engine_part"],
        )
        self.assertEqual(len({item["purpose"] for item in levels}), 3)
        for level in levels:
            self.assertTrue(level["prohibited_uses"])
            self.assertTrue(level["required_before_build"])
            self.assertEqual(
                level["release"],
                {"printable": False, "functional": False, "engine_use": False},
            )

    def test_no_material_route_nominal_or_tolerance_is_selected(self):
        for family in self.contract["family_registry"]:
            self.assertIsNone(family["selected_material_id"])
            self.assertIsNone(family["selected_route_id"])
            self.assertTrue(
                all(
                    item["status"] == "candidate_unqualified"
                    for item in family["candidate_materials"]
                )
            )
            self.assertTrue(
                all(
                    item["status"] == "candidate_unqualified"
                    for item in family["candidate_routes"]
                )
            )
            for measurement in family["critical_measurements"]:
                self.assertIsNone(measurement["nominal"])
                self.assertIsNone(measurement["tolerance"])

    def test_every_family_has_all_route_qualification_controls(self):
        expected = {
            "dfam",
            "machining",
            "heat_treatment",
            "hip",
            "ct",
            "ndt",
            "coupons",
        }
        for family in self.contract["family_registry"]:
            self.assertEqual(set(family["manufacturing_controls"]), expected)
            self.assertTrue(
                all(family["manufacturing_controls"][key] for key in expected)
            )
            self.assertEqual(family["release"]["status"], "blocked")
            self.assertFalse(family["release"]["printable"])
            self.assertFalse(family["release"]["functional"])
            self.assertFalse(family["release"]["engine_use"])

    def test_every_titanium_candidate_has_complete_fail_closed_controls(self):
        expected_ids = set(self.contract["titanium_policy"]["candidate_family_ids"])
        detected_ids = set()

        for family in self.contract["family_registry"]:
            has_titanium = any(
                item["material_family"] == "titanium"
                for item in family["candidate_materials"]
            )
            if not has_titanium:
                self.assertNotIn("titanium_controls", family)
                continue
            detected_ids.add(family["id"])
            controls = family["titanium_controls"]
            for field in self.module.TITANIUM_SELECTION_FIELDS:
                self.assertIsNone(controls[field])
            for field in self.module.TITANIUM_EVIDENCE_FIELDS:
                self.assertTrue(controls[field])
            self.assertFalse(controls["additive_build_authorized"])

        self.assertEqual(detected_ids, expected_ids)

    def test_declaring_a_release_cannot_authorize_a_part(self):
        contract = copy.deepcopy(self.contract)
        contract["family_registry"][0]["release"] = {
            "status": "released",
            "printable": True,
            "functional": True,
            "engine_use": True,
        }

        report = self.module.evaluate(contract)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn(
            "family_release_status_must_be_blocked:crankcase_magnesium_historical",
            report["contract_errors"],
        )
        self.assertTrue(all(value is False for value in report["release"].values()))

    def test_selecting_an_unqualified_route_and_material_fails(self):
        contract = copy.deepcopy(self.contract)
        family = contract["family_registry"][2]
        family["selected_material_id"] = "lpbf_alsi10mg_candidate"
        family["selected_route_id"] = "lpbf_hip_heat_treat_machine"

        errors = self.module.validate_contract(contract)

        self.assertIn(
            "selected_material_forbidden_without_evidence:piston_system", errors
        )
        self.assertIn("selected_route_forbidden_without_evidence:piston_system", errors)

    def test_inventing_a_tolerance_fails(self):
        contract = copy.deepcopy(self.contract)
        measurement = contract["family_registry"][1]["critical_measurements"][0]
        measurement["tolerance"] = 0.01

        errors = self.module.validate_contract(contract)

        self.assertIn(
            "invented_tolerance:cylinder_nikasil_system:finished_bore_diameter_roundness_and_taper",
            errors,
        )

    def test_removing_ct_or_titanium_fatigue_controls_fails(self):
        contract = copy.deepcopy(self.contract)
        contract["family_registry"][8]["manufacturing_controls"]["ct"] = []
        contract["family_registry"][3]["titanium_controls"]["fatigue"] = []

        errors = self.module.validate_contract(contract)

        self.assertIn(
            "missing_manufacturing_control:turbocharger_system:ct", errors
        )
        self.assertIn(
            "missing_titanium_evidence_topic:connecting_rod_titanium:fatigue",
            errors,
        )

    def test_geometry_or_runtime_authority_injection_fails(self):
        contract = copy.deepcopy(self.contract)
        contract["asset"]["upstream_contract_reference"] = "hidden/engine.obj"
        contract["runtime_authorities"]["process_qualification_authority"] = (
            "configured"
        )

        errors = self.module.validate_contract(contract)

        self.assertIn("embedded_geometry_reference_forbidden:.obj", errors)
        self.assertIn(
            "runtime_authority_must_be_absent:process_qualification_authority",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
