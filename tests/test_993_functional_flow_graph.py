import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_993_functional_flow_graph.py"
SPEC = importlib.util.spec_from_file_location(
    "generate_993_functional_flow_graph", MODULE_PATH
)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class FunctionalFlowGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = generator.build()
        generator.validate(self.graph)

    def test_all_declared_system_interfaces_have_a_flow_edge(self) -> None:
        scope = self.graph["scope"]
        self.assertEqual(scope["system_count"], 10)
        self.assertEqual(scope["flow_type_count"], 10)
        self.assertEqual(scope["flow_edge_count"], 29)
        self.assertEqual(scope["physical_coupling_edge_count"], 20)
        self.assertEqual(scope["declared_integration_interface_pairs"], 20)
        self.assertEqual(scope["covered_integration_interface_pairs"], 20)
        self.assertEqual(
            {item["system_id"] for item in self.graph["systems"]},
            {"0xx", "1xx", "2xx", "3xx", "4xx", "5xx", "6xx", "7xx", "8xx", "9xx"},
        )

    def test_every_catalogue_work_package_is_bound_to_system_flows(self) -> None:
        bindings = self.graph["work_package_bindings"]
        self.assertEqual(len(bindings), 239)
        self.assertEqual(len({item["work_package_id"] for item in bindings}), 239)
        for item in bindings:
            self.assertTrue(item["flow_edge_ids"])
            self.assertEqual(item["quantified_ports"], 0)
            self.assertEqual(item["closed_balance_equations"], 0)

    def test_reference_balance_equations_precede_physicsnemo(self) -> None:
        flow_types = self.graph["flow_types"]
        self.assertEqual(
            flow_types["mechanical_power"]["conservation_law"],
            "power_W=torque_Nm*angular_speed_rad_s",
        )
        self.assertIn(
            "sum_mass_flow_kg_s=0",
            flow_types["thermofluid_mass_energy"]["conservation_law"],
        )
        policy = self.graph["balance_closure_policy"]
        self.assertFalse(policy["LLM_may_supply_physical_values_or_pass_a_balance"])
        self.assertIn("after_reference_balance_closure", policy["physicsnemo_role"])

    def test_missions_exist_but_none_has_passed(self) -> None:
        missions = self.graph["virtual_missions"]
        self.assertEqual(len(missions), 7)
        self.assertEqual(
            {item["mission_id"] for item in missions},
            {
                "MISSION-993-START-IDLE",
                "MISSION-993-ACCELERATION",
                "MISSION-993-BRAKING",
                "MISSION-993-CORNERING",
                "MISSION-993-THERMAL-SOAK",
                "MISSION-993-STEERING-MANOEUVRE",
                "MISSION-993-ELECTRICAL-PEAK",
            },
        )
        for mission in missions:
            self.assertFalse(mission["functional_pass"])
            self.assertEqual(mission["reference_solver_results"], [])
            self.assertTrue(mission["status"].startswith("blocked_"))
        self.assertFalse(self.graph["assembly_readiness"]["functioning_vehicle"])

    def test_checked_in_flow_graph_is_current(self) -> None:
        self.assertEqual(generator.main(["--check"]), 0)
        self.assertEqual(
            json.loads(generator.OUTPUT.read_text(encoding="utf-8")), self.graph
        )


if __name__ == "__main__":
    unittest.main()
