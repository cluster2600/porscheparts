import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "twins/reference-917-engine/test-bench-f4.json"
SYSTEMS = ROOT / "twins/reference-917-engine/systems-f4.json"
SUPPORT = ROOT / "twins/reference-917-engine/start-support-f5.json"
RUNNER = ROOT / "twins/reference-917-engine/source/run_virtual_test_bench.py"


class Engine917StartSupportF5Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.support = json.loads(SUPPORT.read_text(encoding="utf-8"))

    def test_declared_support_count_matches(self):
        actual = sum(item["count"] for item in self.support["support_components"])
        self.assertEqual(actual, self.support["acceptance"]["support_component_instance_count"])

    def test_topology_does_not_claim_solver_readiness(self):
        self.assertTrue(self.support["acceptance"]["oil_prime_topology_complete"])
        self.assertFalse(self.support["acceptance"]["oil_prime_solver_ready"])
        self.assertFalse(self.support["acceptance"]["starter_torque_simulation_ready"])
        self.assertFalse(self.support["acceptance"]["fired_run_authorized"])

    def test_virtual_run_reports_f5_topology_without_firing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.json"
            subprocess.run(
                [
                    "python3",
                    str(RUNNER),
                    "--bench",
                    str(BENCH),
                    "--systems",
                    str(SYSTEMS),
                    "--support",
                    str(SUPPORT),
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertFalse(report["fired_run_executed"])
        self.assertEqual(report["oil_prime_status"], "topology_complete_parameters_blocked")
        self.assertEqual(report["authored_support_component_count"], 14)
        self.assertEqual(report["remaining_release_inputs"], self.support["remaining_release_inputs"])


if __name__ == "__main__":
    unittest.main()
