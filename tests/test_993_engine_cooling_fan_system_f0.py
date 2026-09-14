import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/993-engine-cooling-fan-system-f0/source/evaluate_integration.py"
USD_SCRIPT = ROOT / "twins/993-engine-cooling-fan-system-f0/source/build_usd_assembly.py"
REPORT = ROOT / "twins/993-engine-cooling-fan-system-f0/evidence/integration-screen.json"
TWIN = ROOT / "catalog/twins/twin-993-engine-cooling-fan-system-f0.json"
SIMREADY = ROOT / "twins/993-engine-cooling-fan-system-f0/evidence/simready-conversion-summary.json"
SPEC = importlib.util.spec_from_file_location("fan_system_integration", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
USD_SPEC = importlib.util.spec_from_file_location("fan_system_usd", USD_SCRIPT)
USD_MODULE = importlib.util.module_from_spec(USD_SPEC)
assert USD_SPEC.loader is not None
USD_SPEC.loader.exec_module(USD_MODULE)
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "validate_twins", ROOT / "scripts/validate_twins.py"
)
VALIDATOR_MODULE = importlib.util.module_from_spec(VALIDATOR_SPEC)
assert VALIDATOR_SPEC.loader is not None
VALIDATOR_SPEC.loader.exec_module(VALIDATOR_MODULE)


class EngineCoolingFanSystemF0Tests(unittest.TestCase):
    def test_analytic_clearance_is_recomputed_from_upstream_reports(self) -> None:
        report = MODULE.build_report(measure_brep=False)
        clearance = report["clearance_screen"]

        self.assertAlmostEqual(clearance["cold_diametral_clearance_mm"], -28.0)
        self.assertAlmostEqual(clearance["cold_radial_clearance_mm"], -14.0)
        self.assertAlmostEqual(clearance["required_throat_diameter_mm"], 284.0)
        self.assertAlmostEqual(clearance["throat_diameter_shortfall_mm"], 32.0)
        expected_hot = (252.0 + 0.68796 - 280.0 - 0.7644) / 2.0
        self.assertAlmostEqual(clearance["hot_radial_clearance_mm"], expected_hot)
        self.assertFalse(clearance["cold_clearance_pass"])
        self.assertFalse(clearance["hot_clearance_pass"])

    def test_flow_and_excitation_contracts_reject_inconsistent_inputs(self) -> None:
        report = MODULE.build_report(measure_brep=False)
        flow = report["flow_contract_screen"]
        excitation = report["excitation_contract_screen"]

        self.assertAlmostEqual(flow["delta_m3_s"], 0.24)
        self.assertAlmostEqual(flow["delta_percent_of_impeller_target"], 100.0 * 0.24 / 1.01)
        self.assertEqual(flow["status"], "failed_inconsistent_synthetic_targets")
        self.assertAlmostEqual(excitation["frequency_delta_hz"], 900.0)
        self.assertEqual(
            excitation["status"],
            "failed_inconsistent_speed_and_blade_count_assumptions",
        )

    def test_published_brep_clash_is_fail_closed(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        clash = report["brep_clash_screen"]

        self.assertEqual(clash["method"], "exact OpenCascade BRep boolean intersection")
        self.assertTrue(clash["housing_valid_brep"])
        self.assertTrue(clash["impeller_valid_brep"])
        self.assertTrue(clash["collision_detected"])
        self.assertGreater(clash["intersection_solid_count"], 0)
        self.assertGreater(clash["intersection_volume_mm3"], 0.0)
        self.assertEqual(clash["status"], "failed_clearance")

    def test_twin_is_registered_without_release_claims(self) -> None:
        twin = json.loads(TWIN.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))

        self.assertEqual(VALIDATOR_MODULE.load_and_validate(TWIN), [])
        self.assertEqual(twin["fidelity"], "F1_envelope")
        self.assertEqual(twin["validation"]["status"], "concept")
        self.assertEqual(twin["interfaces"][0]["status"], "failed")
        self.assertFalse(report["gates"]["integration_pass"])
        self.assertFalse(report["gates"]["simready_property_assignment"])
        self.assertFalse(report["gates"]["physicsnemo_model_executed"])
        self.assertFalse(report["gates"]["manufacturing_authorized"])
        self.assertFalse(report["gates"]["engine_operation_authorized"])
        self.assertFalse(report["gates"]["release_authorized"])

    def test_input_hashes_bind_the_exact_upstream_evidence_and_step(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        for component in report["inputs"].values():
            engineering_report = ROOT / component["engineering_report"]
            step = ROOT / component["step"]
            self.assertEqual(MODULE._sha256(engineering_report), component["engineering_report_sha256"])
            self.assertEqual(MODULE._sha256(step), component["step_sha256"])

    def test_usd_asset_paths_are_relative_and_the_source_authors_no_physics(self) -> None:
        layer = ROOT / "work/fan-system/stages/fan-system.usda"
        asset = ROOT / "work/fan-system/assets/housing.usd"
        source = USD_SCRIPT.read_text(encoding="utf-8")

        self.assertEqual(
            USD_MODULE.relative_asset_path(layer, asset),
            "../assets/housing.usd",
        )
        self.assertIn('"property_assignment_status": "skipped"', source)
        self.assertIn('"simready_claimed": False', source)
        self.assertIn('"simulation_validated": False', source)
        self.assertNotIn("RigidBodyAPI.Apply", source)
        self.assertNotIn("CollisionAPI.Apply", source)

    def test_simready_summary_proves_conversion_only_without_physics_claim(self) -> None:
        evidence = json.loads(SIMREADY.read_text(encoding="utf-8"))

        self.assertEqual(evidence["preflight"]["linux_container"]["status"], "ready")
        self.assertEqual(evidence["runtime"]["platform"], "linux/amd64")
        self.assertFalse(evidence["runtime"]["gpu_used"])
        self.assertEqual(evidence["runtime"]["property_assignment_intent"], "skip")
        self.assertTrue(evidence["assets"]["housing"]["minimum_validation_passed"])
        self.assertTrue(evidence["assets"]["impeller"]["minimum_validation_passed"])
        self.assertTrue(evidence["assembly"]["minimum_validation_passed"])
        self.assertEqual(evidence["assembly"]["mesh_count"], 2)
        self.assertEqual(evidence["assembly"]["top_level_authored_reference_count"], 2)
        self.assertEqual(evidence["assembly"]["meters_per_unit"], 0.001)
        self.assertEqual(evidence["assembly"]["up_axis"], "Z")
        self.assertEqual(evidence["assembly"]["rigid_body_count"], 0)
        self.assertEqual(evidence["assembly"]["collider_count"], 0)
        self.assertEqual(evidence["assembly"]["joint_count"], 0)
        self.assertFalse(evidence["gates"]["simready_property_assignment_complete"])
        self.assertFalse(evidence["gates"]["physics_simulation_complete"])
        self.assertFalse(evidence["gates"]["manufacturing_authorized"])

    def test_simready_summary_is_sanitized_and_binds_source_steps(self) -> None:
        evidence = json.loads(SIMREADY.read_text(encoding="utf-8"))
        serialized = json.dumps(evidence)
        integration = json.loads(REPORT.read_text(encoding="utf-8"))

        for forbidden in ("/Users/", "/tmp/", "/workspace/", "/output/"):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(
            evidence["assets"]["housing"]["source_step_sha256"],
            integration["inputs"]["housing"]["step_sha256"],
        )
        self.assertEqual(
            evidence["assets"]["impeller"]["source_step_sha256"],
            integration["inputs"]["impeller"]["step_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
