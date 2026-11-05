"""Synthetic dimension and unit tests; no part qualification is implied."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "twins/935-horizontal-cooling-system-f0/source/check_scan_calibration.py"
spec = importlib.util.spec_from_file_location("check_scan_calibration", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def input_case():
    return {"scan_id": "rotor", "scan_sha256": "a" * 64, "dimensions": [
        {"feature": "fixture length", "provenance": "synthetic", "source_length": 100,
         "source_uncertainty": 0.1, "measured_mm": 200, "measured_uncertainty_mm": 0.2,
         "direction": [1, 0, 0]},
        {"feature": "fixture width", "provenance": "synthetic", "source_length": 50,
         "source_uncertainty": 0.1, "measured_mm": 100, "measured_uncertainty_mm": 0.2,
         "direction": [0, 1, 0]}]}


class CalibrationTest(unittest.TestCase):
    def test_consistent_and_inverse_scale(self):
        result = module.assess(input_case())
        self.assertTrue(result["scale_intervals_overlap"])
        self.assertEqual(result["first_dimension_nominal_mm_per_source_unit"], 2)
        forward = result["first_dimension_origin_scale_source_to_mm"]
        inverse = result["first_dimension_origin_scale_mm_to_source"]
        for i in range(4):
            self.assertAlmostEqual(forward[i][i] * inverse[i][i], 1)
        self.assertFalse(result["scale_verified"])
        self.assertFalse(result["manufacturing_authorized"])

    def test_inconsistent_or_invalid_measurements(self):
        x = input_case(); x["dimensions"][1]["measured_mm"] = 120
        self.assertFalse(module.assess(x)["scale_intervals_overlap"])
        x = input_case(); x["dimensions"][1]["direction"] = [-1, 0, 0]
        with self.assertRaises(ValueError): module.assess(x)
        x = input_case(); x["dimensions"][0]["source_uncertainty"] = 100
        with self.assertRaises(ValueError): module.assess(x)
        x = input_case(); x["dimensions"][0]["direction"] = [True, 0, 0]
        with self.assertRaises(ValueError): module.assess(x)
        x = input_case(); x["dimensions"][0]["source_length"] = 1e-300
        x["dimensions"][0]["source_uncertainty"] = 0
        x["dimensions"][0]["measured_mm"] = 1e300
        with self.assertRaises(ValueError): module.assess(x)
        x = input_case(); x["dimensions"][0]["source_length"] = 1e300
        x["dimensions"][0]["measured_mm"] = 1e-300
        x["dimensions"][0]["measured_uncertainty_mm"] = 0
        with self.assertRaises(ValueError): module.assess(x)

    def test_cli_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "in.json", Path(tmp) / "out.json"
            source.write_text(json.dumps(input_case()))
            command = [sys.executable, str(SCRIPT), str(source), str(output)]
            subprocess.run(command, check=True, capture_output=True)
            original = output.read_bytes()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
