import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "twins/reference-917-engine/performance-target-f9.json"
RUNNER = ROOT / "twins/reference-917-engine/source/model_performance_envelope_0d_f9.py"
SOURCE_1600_HP = ROOT / "catalog/sources/src-porsche-newsroom-91730-1600-qualifying.json"

SPEC = importlib.util.spec_from_file_location("engine_917_performance_f9", RUNNER)
assert SPEC is not None and SPEC.loader is not None
F9 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(F9)


class Engine917PerformanceF9Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.report = F9.build_report(cls.config, CONFIG)

    def test_contract_is_valid_and_uses_the_917_30_geometry(self):
        self.assertEqual(F9.validate_contract(self.config), [])
        geometry = self.config["geometry"]
        self.assertEqual(geometry["cylinder_count"], 12)
        self.assertEqual(geometry["strokes"], 4)
        self.assertEqual(geometry["bore_mm"], 90.0)
        self.assertEqual(geometry["stroke_mm"], 70.4)
        self.assertAlmostEqual(self.report["geometry"]["calculated_displacement_cm3"], 5374.385384, places=6)
        self.assertAlmostEqual(self.report["geometry"]["documented_displacement_cm3"], 5374.0, places=6)

    def test_official_1600_hp_statement_remains_documentary_only(self):
        source = json.loads(SOURCE_1600_HP.read_text(encoding="utf-8"))
        self.assertEqual(source["source_id"], "SRC-PORSCHE-NEWSROOM-91730-1600-QUALIFYING")
        self.assertEqual(source["source_type"], "manufacturer")
        claim = next(item for item in self.config["source_evidence"] if item["power_value"] == 1600.0)
        self.assertEqual(claim["power_unit"], "hp")
        self.assertEqual(claim["qualifier"], "reported_qualifying_trim")
        self.assertEqual(claim["calibration_role"], "documentary_only")
        self.assertFalse(claim["used_for_calibration"])
        self.assertIsNone(claim["rpm"])
        self.assertIsNone(claim["test_conditions"])

    def test_hp_primary_and_ps_sensitivity_are_separate(self):
        primary, alternative = self.report["scenario_envelopes"]
        self.assertEqual(primary["scenario_role"], "primary")
        self.assertEqual(primary["scenario"]["power_unit"], "hp")
        self.assertAlmostEqual(primary["normalized_target_power_kw"], 1193.119795, places=6)
        self.assertEqual(alternative["scenario_role"], "alternative_unit_sensitivity")
        self.assertEqual(alternative["scenario"]["power_unit"], "PS")
        self.assertAlmostEqual(alternative["normalized_target_power_kw"], 1176.798, places=6)
        self.assertNotEqual(primary["envelope"], alternative["envelope"])

    def test_primary_requirement_at_7000_rpm_is_reproducible(self):
        primary = self.report["scenario_envelopes"][0]
        point = next(item for item in primary["envelope"] if item["rpm"] == 7000)
        self.assertAlmostEqual(point["target_power_kw"], 1193.119795, places=6)
        self.assertAlmostEqual(point["required_torque_nm"], 1627.636397, places=6)
        self.assertAlmostEqual(point["required_bmep_bar"], 38.057342, places=6)
        self.assertAlmostEqual(point["mean_piston_speed_m_s"], 16.426667, places=6)

    def test_algebraic_model_does_not_claim_a_solver_or_proof(self):
        model = self.report["model"]
        gate = self.report["proof_gate"]
        self.assertTrue(model["algebraic_envelope_model_executed"])
        self.assertFalse(model["thermodynamic_solver_executed"])
        self.assertFalse(model["calibration_executed"])
        self.assertFalse(model["held_out_validation_executed"])
        self.assertFalse(model["physical_dyno_test_executed"])
        self.assertFalse(model["performance_proven"])
        self.assertEqual(gate["status"], "blocked_missing_solver_and_calibration_evidence")
        self.assertFalse(gate["performance_claim_authorized"])
        self.assertGreater(gate["missing_evidence_count"], 0)
        prohibited = set(self.report["prohibited_use"])
        self.assertIn("claim_that_1600_hp_has_been_simulated_or_proven", prohibited)
        self.assertIn("claim_that_1600_ps_has_been_simulated_or_proven", prohibited)

    def test_airflow_pressure_and_temperature_are_not_inferred(self):
        not_calculated = set(self.report["not_calculated_quantities"])
        self.assertIn("air_mass_flow_kg_s", not_calculated)
        self.assertIn("boost_pressure_pa", not_calculated)
        self.assertIn("compressor_outlet_temperature_k", not_calculated)
        self.assertIn("turbine_inlet_temperature_k", not_calculated)
        self.assertFalse(self.report["model_policy"]["allow_airflow_prediction"])
        self.assertFalse(self.report["model_policy"]["allow_pressure_prediction"])
        self.assertFalse(self.report["model_policy"]["allow_temperature_prediction"])

    def test_contract_rejects_a_premature_performance_claim(self):
        mutated = copy.deepcopy(self.config)
        mutated["proof_gate"]["performance_claim_authorized"] = True
        errors = F9.validate_contract(mutated)
        self.assertIn("proof_gate.performance_claim_authorized: must remain false in F9", errors)

    def test_contract_rejects_documentary_claim_used_as_calibration(self):
        mutated = copy.deepcopy(self.config)
        mutated["source_evidence"][1]["used_for_calibration"] = True
        errors = F9.validate_contract(mutated)
        self.assertIn("source_evidence[1].used_for_calibration: must remain false", errors)

    def test_cli_writes_the_same_fail_closed_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.json"
            subprocess.run(
                ["python3", str(RUNNER), "--config", str(CONFIG), "--output", str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            generated = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(generated, self.report)


if __name__ == "__main__":
    unittest.main()
