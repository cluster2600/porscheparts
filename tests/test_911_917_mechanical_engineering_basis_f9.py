import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins" / "vehicle-911-917"
CONFIG = TWIN / "mechanical-engineering-basis-f9.json"
SCRIPT = TWIN / "source" / "build_mechanical_engineering_basis_f9.py"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module():
    spec = importlib.util.spec_from_file_location("engineering_f9", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("module F9 impossible à charger")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Vehicle911917MechanicalEngineeringBasisF9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(CONFIG)
        cls.module = load_module()
        cls.report = cls.module.build_report(cls.config)

    def test_power_to_torque_calculation_is_reproducible(self) -> None:
        by_speed = {row["speed_rpm"]: row for row in self.report["torque_table"]}

        self.assertAlmostEqual(by_speed[8000.0]["equivalent_input_torque_nm"], 1424.2, places=1)
        self.assertAlmostEqual(by_speed[7000.0]["equivalent_input_torque_nm"], 1627.6, places=1)
        self.assertAlmostEqual(by_speed[7000.0]["preliminary_design_input_torque_nm"], 2115.9, places=1)

    def test_no_public_candidate_is_selected_or_passes_service_screen(self) -> None:
        self.assertIsNone(self.report["decision"]["selected_transaxle"])
        self.assertTrue(self.report["decision"]["all_public_candidates_fail_preliminary_service_screen"])
        self.assertEqual(self.report["decision"]["public_candidates_with_complete_GA"], [])
        self.assertTrue(all(not item["selected"] for item in self.report["candidate_comparisons"]))
        self.assertTrue(all(not item["passes_preliminary_service_screen"] for item in self.report["candidate_comparisons"]))

    def test_physical_inputs_and_release_gates_fail_closed(self) -> None:
        self.assertEqual(
            self.config["upstream"]["latest_artistic_brief"]["authority"],
            "visual_brief_only_no_dimensional_or_engineering_authority",
        )
        self.assertFalse(self.config["architecture_decision"]["compactness_is_requirement"])
        self.assertEqual(
            self.report["readiness"]["missing_required_input_count"],
            self.report["readiness"]["required_input_count"],
        )
        self.assertFalse(any(self.report["release_gates"].values()))
        self.module.validate(self.config, self.report)


if __name__ == "__main__":
    unittest.main()
