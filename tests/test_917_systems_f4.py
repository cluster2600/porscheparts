import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "twins/reference-917-engine/systems-f4.json"


class Engine917SystemsF4Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_counts_are_derived_from_declared_topology(self):
        fluid_routes = sum(item["count"] for item in self.data["fluid_routes"])
        electrical_nodes = sum(item["count"] for item in self.data["electrical_system"]["nodes"])
        electrical_routes = sum(item["count"] for item in self.data["electrical_system"]["routes"])
        acceptance = self.data["acceptance"]
        self.assertEqual(fluid_routes, acceptance["fluid_route_instance_count"])
        self.assertEqual(electrical_nodes, acceptance["electrical_node_instance_count"])
        self.assertEqual(electrical_routes, acceptance["electrical_route_instance_count"])

    def test_physicsnemo_is_not_the_reference_solver(self):
        for domain in self.data["fluid_domains"]:
            self.assertNotEqual(domain["solver_baseline"], "PhysicsNeMo")
            self.assertTrue(any(token in domain["physicsnemo_role"] for token in ("after", "not_before")))

    def test_missing_inputs_block_simulation_readiness(self):
        self.assertFalse(self.data["acceptance"]["simulation_ready"])
        self.assertIn("physicsnemo_training_before_validated_baseline_data", self.data["prohibited_use"])
        self.assertTrue(all(domain["required_inputs"] for domain in self.data["fluid_domains"]))
        self.assertTrue(self.data["electrical_system"]["required_inputs"])

    def test_turbo_routes_are_variant_scoped(self):
        turbo = [item for item in self.data["fluid_routes"] if item["id"].startswith("turbo_")]
        self.assertEqual(len(turbo), 2)
        self.assertTrue(all(item["variant"] == "917_30_only" for item in turbo))


if __name__ == "__main__":
    unittest.main()
