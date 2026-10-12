import copy
import contextlib
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "twins/vehicle-911-917/source"))
from study_rear_driveline_f14 import travel_case, validate_config
import study_rear_driveline_f14 as study


class DrivelineStudyTests(unittest.TestCase):
    def test_preparation_needs_no_private_scan_or_report(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(study, "OUTPUT", Path(directory)), contextlib.redirect_stdout(io.StringIO()):
            study.build()
            data = json.loads((Path(directory) / "study-inputs-f14.json").read_text())
        self.assertEqual(data["rear_axle_x_mm"], 2722)
        self.assertEqual(data["gearbox_bounds_x_mm"], [2622, 3272])
        self.assertEqual(data["engine_service_bounds_x_mm"], [1472, 2622])
        self.assertFalse(any(entry["path"].startswith(("work/", "raw-scans/")) for entry in data["inputs"]))

    def test_public_vehicle_reference_resolves(self):
        for name in ("packaging-concept-f0.json", "packaging-concept-f1.json"):
            c = json.loads((ROOT / "twins/vehicle-911-917" / name).read_text())
            self.assertTrue((ROOT / c["inputs"]["vehicle_reference"]).is_file())
            self.assertNotIn("vehicle_packaging_hypotheses", c["inputs"])

    def test_zero_travel(self):
        case = travel_case(1444, 250, 0)
        self.assertEqual(case["nominal_joint_distance_mm"], 472)
        self.assertEqual(case["required_length_change_mm"], 0)
        self.assertEqual(case["required_joint_angle_deg"], 0)

    def test_known_right_triangle(self):
        case = travel_case(1100, 250, 400)
        self.assertEqual(case["maximum_joint_distance_mm"], 500)
        self.assertEqual(case["required_length_change_mm"], 200)
        self.assertAlmostEqual(case["required_joint_angle_deg"], 53.13010235415598)

    def test_invalid_geometry(self):
        for args in ((500, 250, 80), (1444, -1, 80), (1444, 250, -1), (math.nan, 250, 80)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                travel_case(*args)

    def test_configuration_keeps_unknown_interfaces_unknown(self):
        c = json.loads((ROOT / "twins/vehicle-911-917/rear-driveline-study-f14.json").read_text())
        validate_config(c)
        for key, value in (("sample_step_mm", 0), ("required_clearance_mm", math.inf)):
            changed = copy.deepcopy(c)
            changed[key] = value
            with self.assertRaises(ValueError):
                validate_config(changed)
        c["unknowns"]["engine_output_shaft_datum"] = [0, 0, 0]
        with self.assertRaises(ValueError):
            validate_config(c)

    def test_native_results_when_available(self):
        path = ROOT / "work/911-917-picogk-f14/picogk-driveline-report-f14.json"
        if not path.exists():
            self.skipTest("native private output absent")
        report = json.loads(path.read_text())
        self.assertLessEqual(report["voxel_size_mm"], 2)
        self.assertFalse(any(report["release_gates"].values()))
        self.assertTrue(report["cases"]["baseline"]["nominal_shafts_vs_frame"]["collision"])
        for check in report["cases"]["candidate"].values():
            if isinstance(check, dict) and "collision" in check:
                self.assertFalse(check["collision"])
        data = json.loads((path.parent / "study-inputs-f14.json").read_text())
        self.assertEqual(report["input_sha256"].lower(), hashlib.sha256((path.parent / "study-inputs-f14.json").read_bytes()).hexdigest())
        for entry in data["inputs"]:
            self.assertEqual(entry["sha256"], hashlib.sha256((ROOT / entry["path"]).read_bytes()).hexdigest())
        for gap in data["candidate_analytic_clearance_lower_bounds_mm"].values():
            self.assertGreater(gap, report["continuous_keepout_allowance_mm"])


if __name__ == "__main__":
    unittest.main()
