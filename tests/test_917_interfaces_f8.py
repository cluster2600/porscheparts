import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TWIN_ROOT = ROOT / "twins/reference-917-engine"
MECHANICAL = TWIN_ROOT / "mechanical-connections-f8.json"
SEALS = TWIN_ROOT / "sealing-interfaces-f8.json"
DUCTS = TWIN_ROOT / "ducts-f8.json"
VALIDATOR = TWIN_ROOT / "source/validate_interfaces_f8.py"
PREFLIGHT = TWIN_ROOT / "source/run_interfaces_preflight_f8.py"


class Engine917InterfacesF8Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mechanical = json.loads(MECHANICAL.read_text(encoding="utf-8"))
        cls.seals = json.loads(SEALS.read_text(encoding="utf-8"))
        cls.ducts = json.loads(DUCTS.read_text(encoding="utf-8"))

    def test_declared_group_and_instance_counts_match(self):
        cases = (
            (self.mechanical, "mechanical_connections", "connection_group_count", "connection_instance_count"),
            (self.seals, "sealing_interfaces", "seal_group_count", "seal_instance_count"),
            (self.ducts, "ducts", "duct_group_count", "duct_instance_count"),
        )
        for config, collection, group_key, instance_key in cases:
            with self.subTest(collection=collection):
                entries = config[collection]
                self.assertEqual(len(entries), config["acceptance"][group_key])
                self.assertEqual(sum(item["count"] for item in entries), config["acceptance"][instance_key])

    def test_every_interface_remains_fail_closed(self):
        self.assertTrue(all(not item["physics_enabled"] and not item["measurements"] for item in self.mechanical["mechanical_connections"]))
        self.assertTrue(all(not item["seal_released"] and not item["seal_specification"] for item in self.seals["sealing_interfaces"]))
        self.assertTrue(
            all(
                not item["geometry_released"]
                and not item["flow_simulation_ready"]
                and not item["measurements"]
                for item in self.ducts["ducts"]
            )
        )
        self.assertFalse(self.mechanical["acceptance"]["inventory_complete"])
        self.assertFalse(self.seals["acceptance"]["inventory_complete"])
        self.assertFalse(self.ducts["acceptance"]["inventory_complete"])

    def test_turbo_fuel_oil_and_bench_gaps_are_explicit(self):
        ducts = {item["id"]: item for item in self.ducts["ducts"]}
        for duct_id in (
            "charge_plenum_to_intake_trumpets",
            "turbo_pressure_oil_feed",
            "turbo_scavenge_oil_drain",
            "bench_fuel_supply_to_injection_pump",
            "blower_to_engine_cooling_field",
            "crankcase_breather",
        ):
            self.assertIn(duct_id, ducts)
            self.assertIn("missing", ducts[duct_id]["coverage_status"])
        self.assertEqual(ducts["injection_pump_to_injectors"]["domain"], "fuel")
        self.assertEqual(ducts["turbo_pressure_oil_feed"]["variant"], "917_30_only")

    def test_native_validator_accepts_the_repository_contracts(self):
        result = subprocess.run(
            ["python3", str(VALIDATOR), "--project-root", str(ROOT)],
            check=True,
            capture_output=True,
            text=True,
        )
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["readiness"]["physics_joint_instances"], 0)
        self.assertEqual(report["readiness"]["released_seal_instances"], 0)
        self.assertEqual(report["readiness"]["flow_ready_instances"], 0)

    def test_native_preflight_stops_before_physics_or_flow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "f8-preflight.json"
            subprocess.run(
                [
                    "python3",
                    str(PREFLIGHT),
                    "--project-root",
                    str(ROOT),
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "blocked_missing_measured_interfaces")
        self.assertGreater(report["missing_input_count"], 0)
        self.assertFalse(report["physics_joints_authored"])
        self.assertFalse(report["pressure_boundaries_released"])
        self.assertFalse(report["flow_simulation_executed"])
        self.assertEqual(report["maximum_authorized_use"], "semantic_connectivity_and_measurement_planning_only")

    def test_validator_rejects_an_enabled_joint_without_measurements(self):
        tampered = copy.deepcopy(self.mechanical)
        tampered["mechanical_connections"][0]["physics_enabled"] = True
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "mechanical.json"
            path.write_text(json.dumps(tampered), encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
                    str(VALIDATOR),
                    "--project-root",
                    str(ROOT),
                    "--mechanical",
                    str(path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("physics_enabled" in error for error in report["errors"]))

    def test_f8_rejects_power_contract_fields(self):
        tampered = copy.deepcopy(self.mechanical)
        tampered["target_power"] = {"value": 1600, "unit": "ch"}
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "mechanical.json"
            path.write_text(json.dumps(tampered), encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
                    str(VALIDATOR),
                    "--project-root",
                    str(ROOT),
                    "--mechanical",
                    str(path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertTrue(any("F9 power keys" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
