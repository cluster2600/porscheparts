import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "twins/reference-917-engine/test-bench-f4.json"
SYSTEMS = ROOT / "twins/reference-917-engine/systems-f4.json"
RUNNER = ROOT / "twins/reference-917-engine/source/run_virtual_test_bench.py"


class Engine917VirtualTestBenchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bench = json.loads(BENCH.read_text(encoding="utf-8"))

    def test_declared_counts_match(self):
        components = sum(item["count"] for item in self.bench["bench_components"])
        channels = sum(item["count"] for item in self.bench["instrumentation"])
        self.assertEqual(components, self.bench["acceptance"]["bench_component_instance_count"])
        self.assertEqual(channels, self.bench["acceptance"]["instrument_channel_count"])

    def test_fired_run_is_fail_closed(self):
        self.assertFalse(self.bench["acceptance"]["fired_run_authorized"])
        self.assertIn("physical_engine_start_authorization", self.bench["prohibited_use"])

    def test_runner_stops_after_visual_dry_crank(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.json"
            subprocess.run(
                ["python3", str(RUNNER), "--bench", str(BENCH), "--systems", str(SYSTEMS), "--output", str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertFalse(report["fired_run_executed"])
        self.assertEqual(report["highest_completed_stage"], "kinematic_dry_crank_visualization_only")
        self.assertTrue(report["missing_parts_and_data"])


if __name__ == "__main__":
    unittest.main()
