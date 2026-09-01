import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "twins/reference-917-engine/oil-prime-f6.json"
RUNNER = ROOT / "twins/reference-917-engine/source/run_oil_prime_0d_f6.py"


class Engine917OilPrimeF6Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_topology_counts_match_the_existing_engine_contract(self):
        topology = self.config["known_topology"]
        self.assertEqual(topology["pressure_pump_count"], 1)
        self.assertEqual(topology["scavenge_pump_count"], 6)
        self.assertEqual(topology["main_bearing_count"], 8)

    def test_defaults_cannot_authorize_pressure_prediction(self):
        self.assertFalse(self.config["solver_policy"]["allow_default_engine_values"])
        self.assertFalse(self.config["acceptance"]["solver_ready"])
        self.assertFalse(self.config["acceptance"]["pressure_prediction_authorized"])

    def test_runner_blocks_without_measured_inputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.json"
            subprocess.run(
                ["python3", str(RUNNER), "--config", str(CONFIG), "--output", str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "blocked_missing_measured_inputs")
        self.assertFalse(report["solver_executed"])
        self.assertFalse(report["pressure_prediction_produced"])
        self.assertGreater(report["missing_input_count"], 0)

    def test_physicsnemo_remains_a_correlated_surrogate_only(self):
        role = self.config["solver_policy"]["physicsnemo_role"]
        self.assertIn("surrogate_only", role)
        self.assertIn("correlation", role)


if __name__ == "__main__":
    unittest.main()
