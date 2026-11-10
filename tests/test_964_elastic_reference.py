"""Check the documentary reference replay, not a vehicle material approval."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "twins/964-chassis/material-reference-20261106"
INPUT_SHA = "5c79b4e15537cb8a76030d1cde4be08dd870e5a2dab781c649ef716a1fab1d36"


@unittest.skipIf(importlib.util.find_spec("numpy") is None, "numpy required for elastic reference replay")
class ElasticReferenceTests(unittest.TestCase):
    def run_check(self, output, digest=INPUT_SHA):
        return subprocess.run(
            [sys.executable, str(PACKET / "check_elastic_reference.py"),
             "--repo", str(ROOT), "--inputs", str(PACKET / "inputs.json"),
             "--inputs-sha256", digest, "--output", str(output)],
            capture_output=True, text=True, timeout=30,
        )

    def test_replay_matches_independent_decimal_reference_without_release(self):
        self.assertEqual(hashlib.sha256((PACKET / "inputs.json").read_bytes()).hexdigest(), INPUT_SHA)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "replay"
            run = self.run_check(output)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads((output / "result.json").read_text())
        independent = json.loads((PACKET / "verification.json").read_text())["independent_math"]
        for key in ("effective_E_MPa", "effective_G_MPa", "effective_nu"):
            self.assertLess(abs(result[key] / independent[key] - 1), 1e-11)
        self.assertTrue(result["self_checks_passed"])
        for key in ("material_allowables_or_process_qualified", "physical_validation",
                    "coque_or_native_final_twin_validated", "manufacturing_authorized"):
            self.assertIs(result[key], False)

    def test_wrong_input_hash_fails_before_publishing(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "rejected"
            run = self.run_check(output, "0" * 64)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("Input or existing implementation hash changed", run.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
