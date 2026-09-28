import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_pet_993_oil_cooler_circuit.py"
SPEC = importlib.util.spec_from_file_location(
    "generate_pet_993_oil_cooler_circuit", MODULE_PATH
)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class Pet993OilCoolerCircuitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = generator.derive()
        cls.usd_text = generator.render_usd(cls.data["roster"])
        cls.report = generator.build_report(cls.data, cls.usd_text)
        generator.validate(cls.data, cls.usd_text, cls.report)

    def test_all_104_05_occurrences_resolve_to_unique_pet_masters(self) -> None:
        summary = self.report["summary"]
        self.assertEqual(summary["pet_104_05_occurrences"], 80)
        self.assertEqual(summary["pet_104_05_unique_part_masters"], 43)
        self.assertEqual(summary["pet_part_masters_seen_in_both_sources"], 37)
        self.assertEqual(
            summary["source_occurrence_counts"],
            {"pet-993-pdf-rsworkshop": 37, "pet-classic-993": 43},
        )
        self.assertEqual(len(self.report["part_roster"]), 43)

    def test_topology_and_engineering_inputs_fail_closed(self) -> None:
        topology = self.report["topology_hypothesis"]
        self.assertFalse(topology["ports_and_connections_are_proven"])
        self.assertFalse(topology["oil_tank_or_engine_boundary_coupling_is_proven"])
        self.assertFalse(topology["fan_control_logic_is_proven"])
        self.assertFalse(topology["diagram_coordinates_are_vehicle_coordinates"])
        self.assertEqual(len(self.report["parameter_registry"]), 44)
        self.assertTrue(
            all(item["value"] is None for item in self.report["parameter_registry"])
        )
        self.assertEqual(len(self.report["mathematical_model"]["equations"]), 14)
        self.assertEqual(len(self.report["load_cases"]), 8)
        self.assertTrue(all(item["status"] == "blocked" for item in self.report["load_cases"]))

    def test_material_physics_and_release_claims_remain_false(self) -> None:
        self.assertEqual(
            self.report["material_and_manufacturing_route"]["selected_material_count"],
            0,
        )
        self.assertFalse(self.report["physicsnemo_discovery"]["execution_enabled"])
        self.assertFalse(self.report["omniverse_handoff"]["simready_validated"])
        self.assertFalse(any(self.report["claim_boundary"].values()))

    def test_usd_is_a_guide_graph_without_physics_or_material_schemas(self) -> None:
        self.assertEqual(self.usd_text.count('purpose = "guide"'), 25)
        self.assertEqual(self.usd_text.count('def Scope "Part_'), 43)
        for prohibited in (
            "UsdPhysics",
            "RigidBodyAPI",
            "CollisionAPI",
            "MassAPI",
            "MaterialBindingAPI",
        ):
            self.assertNotIn(prohibited, self.usd_text)

    def test_checked_in_contract_is_current(self) -> None:
        self.assertEqual(generator.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
