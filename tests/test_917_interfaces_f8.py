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
EXTERNAL_INTERFACES = TWIN_ROOT / "external-interfaces-f8.json"
VALIDATOR = TWIN_ROOT / "source/validate_interfaces_f8.py"
PREFLIGHT = TWIN_ROOT / "source/run_interfaces_preflight_f8.py"


class Engine917InterfacesF8Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mechanical = json.loads(MECHANICAL.read_text(encoding="utf-8"))
        cls.seals = json.loads(SEALS.read_text(encoding="utf-8"))
        cls.ducts = json.loads(DUCTS.read_text(encoding="utf-8"))
        cls.external = json.loads(EXTERNAL_INTERFACES.read_text(encoding="utf-8"))

    def run_validator_override(self, option, payload):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "override.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
                    str(VALIDATOR),
                    "--project-root",
                    str(ROOT),
                    option,
                    str(path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        return result, json.loads(result.stdout)

    def test_declared_group_and_instance_counts_match(self):
        cases = (
            (self.mechanical, "mechanical_connections", "connection_group_count", "connection_instance_count"),
            (self.seals, "sealing_interfaces", "seal_group_count", "seal_instance_count"),
            (self.ducts, "ducts", "duct_group_count", "duct_instance_count"),
            (
                self.external,
                "external_interfaces",
                "external_interface_group_count",
                "external_interface_instance_count",
            ),
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
        self.assertTrue(
            all(
                not item["geometry_released"]
                and not item["boundary_conditions_released"]
                and not item["measurements"]
                for item in self.external["external_interfaces"]
            )
        )
        self.assertFalse(self.mechanical["acceptance"]["inventory_complete"])
        self.assertFalse(self.seals["acceptance"]["inventory_complete"])
        self.assertFalse(self.ducts["acceptance"]["inventory_complete"])
        self.assertFalse(self.external["acceptance"]["inventory_complete"])

    def test_turbo_fuel_oil_and_bench_gaps_are_explicit(self):
        ducts = {item["id"]: item for item in self.ducts["ducts"]}
        for duct_id in (
            "ambient_to_turbo_compressor_inlet",
            "charge_plenum_to_intake_trumpets",
            "turbo_pressure_oil_feed",
            "turbo_scavenge_oil_drain",
            "bench_fuel_supply_to_injection_pump",
            "blower_to_engine_cooling_field",
            "na_exhaust_collector_to_bench_extraction",
            "turbo_turbine_outlet_to_bench_extraction",
            "crankcase_breather",
        ):
            self.assertIn(duct_id, ducts)
            self.assertIn("missing", ducts[duct_id]["coverage_status"])
        self.assertEqual(ducts["injection_pump_to_injectors"]["domain"], "fuel")
        self.assertEqual(ducts["turbo_pressure_oil_feed"]["variant"], "917_30_only")

    def test_f8_1_topology_closes_turbo_fuel_and_valve_family_gaps(self):
        mechanical = {item["id"]: item for item in self.mechanical["mechanical_connections"]}
        seals = {item["id"]: item for item in self.seals["sealing_interfaces"]}
        ducts = {item["id"]: item for item in self.ducts["ducts"]}

        self.assertNotIn("valve_to_head_guide", mechanical)
        self.assertEqual(mechanical["intake_valve_to_head_guide"]["body_a"]["id"], "intake_valve")
        self.assertEqual(mechanical["exhaust_valve_to_head_guide"]["body_a"]["id"], "exhaust_valve")
        self.assertEqual(ducts["ambient_to_intake_trumpets"]["variant"], "type_912_4_5_na")
        self.assertEqual(ducts["ambient_to_turbo_compressor_inlet"]["target"]["id"], "turbocharger")
        self.assertEqual(
            ducts["turbo_turbine_outlet_to_bench_extraction"]["target"],
            {"scope": "bench_component", "id": "exhaust_extraction"},
        )
        for seal_id in (
            "ambient_intake_to_turbo_compressor_inlet_connection",
            "na_exhaust_collector_to_bench_extraction_connection",
            "turbo_turbine_outlet_to_bench_extraction_connection",
            "bench_fuel_supply_to_injection_pump_fitting",
            "injection_pump_to_injection_line_fittings",
            "injection_line_to_injector_fittings",
        ):
            self.assertIn(seal_id, seals)
            self.assertFalse(seals[seal_id]["seal_released"])

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
        self.assertEqual(report["counts"]["external_interface_instances"], 6)
        self.assertEqual(report["readiness"]["released_external_boundary_instances"], 0)

    def test_all_external_endpoints_are_registered_and_traceable(self):
        registered = {item["id"] for item in self.external["external_interfaces"]}
        used = set()
        cases = (
            (self.mechanical["mechanical_connections"], ("body_a", "body_b")),
            (self.seals["sealing_interfaces"], ("interface_a", "interface_b")),
            (self.ducts["ducts"], ("source", "target")),
        )
        for entries, endpoint_keys in cases:
            for item in entries:
                for endpoint_key in endpoint_keys:
                    endpoint = item[endpoint_key]
                    if endpoint["scope"] == "external_interface":
                        used.add(endpoint["id"])
        self.assertEqual(used, registered)
        self.assertTrue(all(item["traceability"] for item in self.external["external_interfaces"]))

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
        self.assertEqual(report["registered_external_interface_instances"], 6)
        self.assertFalse(report["external_interface_geometry_released"])
        self.assertFalse(report["external_boundary_conditions_released"])
        self.assertIn("ambient_to_turbo_compressor_inlet", report["coverage_gaps"])
        self.assertIn("turbo_turbine_outlet_to_bench_extraction", report["coverage_gaps"])
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

    def test_f8_rejects_ready_or_released_entries_even_with_populated_fields(self):
        mechanical = copy.deepcopy(self.mechanical)
        connection = mechanical["mechanical_connections"][0]
        connection["measurements"] = {
            field: "placeholder" for field in mechanical["input_profiles"][connection["input_profile"]]
        }
        connection["physics_enabled"] = True
        mechanical["acceptance"]["physics_joint_count"] = connection["count"]

        seals = copy.deepcopy(self.seals)
        seal = seals["sealing_interfaces"][0]
        seal["seal_specification"] = {
            field: "placeholder" for field in seals["input_profiles"][seal["input_profile"]]
        }
        seal["seal_released"] = True
        seals["acceptance"]["released_seal_count"] = seal["count"]

        ducts = copy.deepcopy(self.ducts)
        duct = ducts["ducts"][0]
        duct["measurements"] = {
            field: "placeholder" for field in ducts["input_profiles"][duct["input_profile"]]
        }
        duct["geometry_released"] = True
        duct["flow_simulation_ready"] = True
        ducts["acceptance"]["released_geometry_count"] = duct["count"]
        ducts["acceptance"]["flow_ready_count"] = duct["count"]

        external = copy.deepcopy(self.external)
        boundary = external["external_interfaces"][0]
        boundary["measurements"] = {
            field: "placeholder" for field in external["input_profiles"][boundary["input_profile"]]
        }
        boundary["geometry_released"] = True
        boundary["boundary_conditions_released"] = True
        external["acceptance"]["released_geometry_count"] = boundary["count"]
        external["acceptance"]["released_boundary_condition_count"] = boundary["count"]

        cases = (
            ("--mechanical", mechanical, "physics_enabled must remain false"),
            ("--seals", seals, "seal_released must remain false"),
            ("--ducts", ducts, "geometry_released must remain false"),
            ("--ducts", ducts, "flow_simulation_ready must remain false"),
            ("--external-interfaces", external, "geometry_released must remain false"),
            ("--external-interfaces", external, "boundary_conditions_released must remain false"),
        )
        for option, payload, expected_error in cases:
            with self.subTest(option=option, expected_error=expected_error):
                result, report = self.run_validator_override(option, payload)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(report["status"], "failed")
                self.assertTrue(any(expected_error in error for error in report["errors"]), report["errors"])

    def test_f8_requires_sources_pending_status_and_incomplete_inventory(self):
        cases = []
        no_sources = copy.deepcopy(self.mechanical)
        no_sources.pop("source_ids")
        cases.append((no_sources, "missing root fields: source_ids"))

        complete_inventory = copy.deepcopy(self.mechanical)
        complete_inventory["acceptance"]["inventory_complete"] = True
        cases.append((complete_inventory, "inventory_complete must remain false"))

        claiming_status = copy.deepcopy(self.mechanical)
        claiming_status["status"] = "F8_physically_validated"
        cases.append((claiming_status, "status must remain"))

        physical_claim = copy.deepcopy(self.mechanical)
        physical_claim["rated_output_hp"] = 1600
        cases.append((physical_claim, "unknown root fields: rated_output_hp"))

        for payload, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                result, report = self.run_validator_override("--mechanical", payload)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(report["status"], "failed")
                self.assertTrue(any(expected_error in error for error in report["errors"]), report["errors"])

    def test_f8_1_rejects_unregistered_external_or_removed_required_topology(self):
        ducts = copy.deepcopy(self.ducts)
        ducts["ducts"][0]["source"]["id"] = "unregistered_ambient_typo"
        result, report = self.run_validator_override("--ducts", ducts)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("unknown external_interface id" in error for error in report["errors"]))

        mechanical = copy.deepcopy(self.mechanical)
        mechanical["mechanical_connections"] = [
            item
            for item in mechanical["mechanical_connections"]
            if item["id"] != "intake_valve_to_head_guide"
        ]
        mechanical["acceptance"]["connection_group_count"] -= 1
        mechanical["acceptance"]["connection_instance_count"] -= 12
        result, report = self.run_validator_override("--mechanical", mechanical)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("required F8.1 topology entry missing" in error for error in report["errors"]))

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
