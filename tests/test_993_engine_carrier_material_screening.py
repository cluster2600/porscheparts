import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "parts"
    / "993-eng-carrier-0001"
    / "source"
    / "material_tradeoff.py"
)
SPEC = importlib.util.spec_from_file_location(
    "engine_carrier_material_tradeoff", MODULE_PATH
)
screening = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(screening)


class EngineCarrierMaterialScreeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = screening.build_report()

    def test_generic_material_model_is_reproducible(self) -> None:
        self.assertEqual(screening.main(["--check"]), 0)
        self.assertEqual(
            json.loads(screening.OUTPUT.read_text(encoding="utf-8")), self.report
        )

    def test_analytic_tradeoff_closes(self) -> None:
        results = self.report["analytic_results"]
        self.assertAlmostEqual(
            results["same_geometry"]["ti64_mass_reduction_fraction"],
            0.43566879,
        )
        self.assertAlmostEqual(
            results["same_geometry"]["ti64_deflection_ratio"],
            1.842105263,
        )
        self.assertAlmostEqual(
            results["same_bending_stiffness"]["ti64_uniform_section_scale"],
            1.165007204,
        )
        self.assertGreater(
            results["same_mass"]["ti64_to_steel_bending_stiffness_ratio"], 1.69
        )

    def test_screening_cannot_be_mistaken_for_component_validation(self) -> None:
        self.assertFalse(self.report["subject"]["component_geometry_used"])
        self.assertFalse(self.report["model_verification"]["component_model_verified"])
        self.assertFalse(self.report["screening_decision"]["component_credit"])
        self.assertIsNone(self.report["screening_decision"]["selected_material"])
        self.assertIsNone(
            self.report["screening_decision"]["selected_functional_process"]
        )
        self.assertFalse(any(self.report["release_gates"].values()))


if __name__ == "__main__":
    unittest.main()
