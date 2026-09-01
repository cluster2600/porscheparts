import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins" / "engine-simulation-contracts"


def read(name):
    return json.loads((CONTRACT / name).read_text(encoding="utf-8"))


class EngineSimulationContractsTest(unittest.TestCase):
    def test_missing_inputs_keep_load_cases_blocked(self):
        for case in read("load-cases-f1.json")["load_cases"]:
            if any(value is None for value in case["required_inputs"].values()):
                self.assertTrue(case["status"].startswith("blocked_"))

    def test_unknown_scan_materials_have_no_properties(self):
        materials = read("materials-f1.json")["materials"]
        for material in materials.values():
            if material["assignment_status"] == "unassigned":
                self.assertEqual(material["property_sets"], {})

    def test_physicsnemo_is_surrogate_only_and_disabled(self):
        policy = read("load-cases-f1.json")["physicsnemo_policy"]
        self.assertFalse(policy["execution_enabled"])
        self.assertEqual(policy["role"], "surrogate_only_after_validated_baseline")

    def test_obj_interfaces_have_unconfirmed_units(self):
        for interface in read("interfaces-f1.json")["interfaces"]:
            if interface["units"] == "OBJ_unit":
                self.assertEqual(interface["unit_status"], "unconfirmed")

    def test_local_refinement_report_when_present(self):
        path = ROOT / "work" / "engine-segmentation-f1" / "refined-segmentation.json"
        if not path.exists():
            self.skipTest("local scan-derived report intentionally absent")
        report = json.loads(path.read_text(encoding="utf-8"))
        engine = report["engine_917"]
        neighborhoods = [
            part for part in engine["parts"].values()
            if part["classification"] == "visible_opening_neighborhood"
        ]
        self.assertEqual(len(neighborhoods), 12)
        self.assertEqual(
            engine["assigned_opening_triangles"] + engine["remainder_triangles"],
            engine["source_triangles"],
        )

    def test_engine_component_hypotheses_are_explicit(self):
        families = read("engine-components-f1.json")["families"]
        self.assertEqual(
            families["piston_993_turbo"]["evidence"]["diameter"],
            "nominal_engine_bore_not_piston_measurement",
        )
        self.assertEqual(
            families["camshaft_993_layout"]["evidence"]["all_dimensions"],
            "layout_hypothesis",
        )
        self.assertEqual(
            families["turbocharger_k16_pair"]["evidence"]["housings_and_aero_surfaces"],
            "layout_hypothesis",
        )


if __name__ == "__main__":
    unittest.main()
