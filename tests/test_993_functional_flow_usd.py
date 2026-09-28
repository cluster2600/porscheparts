import importlib.util
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_993_functional_flow_usd.py"
SPEC = importlib.util.spec_from_file_location(
    "generate_993_functional_flow_usd", MODULE_PATH
)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)
PREFLIGHT = ROOT / "twins" / "vehicle-993" / "functional-flow-simready-preflight-f0.json"


class FunctionalFlowUsdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = generator.load_json(generator.GRAPH)
        self.stage = generator.render_stage(self.graph)
        self.contract = generator.build_contract(self.graph, self.stage)
        generator.validate(self.graph, self.stage, self.contract)

    def test_stage_contains_all_systems_and_flows(self) -> None:
        self.assertEqual(self.stage.count('def Xform "System_'), 10)
        self.assertEqual(self.stage.count("def BasisCurves"), 29)
        for system in self.graph["systems"]:
            self.assertIn(f'System_{system["system_id"]}', self.stage)
        for edge in self.graph["flow_edges"]:
            self.assertIn(edge["flow_edge_id"].replace("-", "_"), self.stage)

    def test_stage_declares_openusd_units_and_f0_fidelity(self) -> None:
        self.assertIn("metersPerUnit = 1", self.stage)
        self.assertIn('upAxis = "Z"', self.stage)
        self.assertIn('fidelity = "F0_functional_topology"', self.stage)
        self.assertIn('purpose = "engineering_topology_diagram_not_vehicle_geometry"', self.stage)

    def test_stage_has_no_physics_or_material_schema(self) -> None:
        for prohibited in (
            "UsdPhysics",
            "RigidBodyAPI",
            "CollisionAPI",
            "MassAPI",
            "MaterialBindingAPI",
        ):
            self.assertNotIn(prohibited, self.stage)
        self.assertIn("bool simreadyValidated = false", self.stage)
        self.assertIn("bool functioningVehicle = false", self.stage)

    def test_contract_is_fail_closed_before_preflight(self) -> None:
        self.assertEqual(
            self.contract["validation"]["current_status"],
            "authored_pending_cad_to_simready_preflight",
        )
        self.assertEqual(self.contract["stage"]["part_geometry_count"], 0)
        self.assertEqual(self.contract["stage"]["physics_schema_count"], 0)
        self.assertTrue(
            all(value is False for value in self.contract["claim_boundary"].values())
        )

    def test_read_only_simready_preflight_is_captured_and_blocked(self) -> None:
        preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
        self.assertEqual(preflight["status"], "blocked")
        self.assertEqual(preflight["source_asset"]["request_input_status"], "ready")
        self.assertEqual(
            preflight["source_asset"]["sha256"],
            hashlib.sha256(self.stage.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(len(preflight["blockers"]), 7)
        self.assertTrue(
            all(value is False for value in preflight["result_boundary"].values())
        )

    def test_checked_in_stage_and_contract_are_current(self) -> None:
        self.assertEqual(generator.main(["--check"]), 0)
        self.assertEqual(
            json.loads(generator.CONTRACT.read_text(encoding="utf-8")),
            self.contract,
        )
        self.assertEqual(generator.OUTPUT.read_text(encoding="utf-8"), self.stage)


if __name__ == "__main__":
    unittest.main()
