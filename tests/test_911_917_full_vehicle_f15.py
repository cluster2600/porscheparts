import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "twins/vehicle-911-917/source"))
from report_full_vehicle_f15 import REQUIRED_COMPONENTS, REQUIRED_CHECKS, VIEWS, checked_file, validate_scope, verify_report

CONFIG = ROOT / "twins/vehicle-911-917/full-vehicle-study-f15.json"


class FullVehicleTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(CONFIG.read_text())
        self.report = {
            "phase": "F15", "status": "produced_packaging_study_not_accepted_vehicle",
            "release_gates": copy.deepcopy(self.config["release_gates"]),
            "unknowns": copy.deepcopy(self.config["unknowns"]),
            "all_functional_components_modelled": False, "mounting_interfaces_measured": False,
            "voxel_size_mm": 5, "private_scan": None,
            "components": [{"id": name, "properties": {"volume_mm3": 10, "bounds_min_mm": [0, 0, 0],
                            "bounds_max_mm": [1, 1, 1]}} for name in sorted(REQUIRED_COMPONENTS)],
            "views": [{"id": name} for name in VIEWS],
            "checks": {key: {"collision": False} for key in REQUIRED_CHECKS},
        }

    def test_complete_packaging_is_not_a_functional_release(self):
        validate_scope(self.report, self.config)
        self.assertGreaterEqual(len(REQUIRED_COMPONENTS), 40)
        self.assertEqual({v for v in REQUIRED_COMPONENTS if v.startswith("seat_")}, {"seat_left", "seat_right"})

    def test_missing_duplicate_or_extra_components_fail(self):
        for change in (lambda r: r["components"].pop(),
                       lambda r: r["components"].append(r["components"][0]),
                       lambda r: r["components"][0].update(id="rear_seat")):
            report = copy.deepcopy(self.report)
            change(report)
            with self.assertRaises(ValueError):
                validate_scope(report, self.config)

    def test_promoted_physical_claims_fail(self):
        for key, value in (("release_gates", {}), ("mounting_interfaces_measured", True),
                           ("all_functional_components_modelled", True), ("voxel_size_mm", 10)):
            report = copy.deepcopy(self.report)
            report[key] = value
            with self.assertRaises(ValueError):
                validate_scope(report, self.config)
        self.report["unknowns"]["suspension_hardpoints_and_linkage"] = [1, 2, 3]
        with self.assertRaises(ValueError):
            validate_scope(self.report, self.config)

    def test_empty_geometry_and_missing_views_fail(self):
        for change in (lambda r: r["views"].pop(),
                       lambda r: r["components"][0]["properties"].update(volume_mm3=float("nan")),
                       lambda r: r["components"][0]["properties"].update(bounds_min_mm=[1, 1, 1]),
                       lambda r: r["checks"].pop(next(iter(r["checks"])))):
            report = copy.deepcopy(self.report)
            change(report)
            with self.assertRaises(ValueError):
                validate_scope(report, self.config)

    def test_hash_and_path_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = directory / "result.bin"
            path.write_bytes(b"witness")
            digest = hashlib.sha256(b"witness").hexdigest()
            self.assertEqual(checked_file(directory, path.name, digest), path.resolve())
            with self.assertRaises(ValueError):
                checked_file(directory, path.name, "0" * 64)
            with self.assertRaises(ValueError):
                checked_file(directory, "../outside", digest)

    def test_clearance_arithmetic_includes_wall_thickness(self):
        c = self.config
        floor_top = c["floor"]["centre_mm"][2] + c["floor"]["size_mm"][2] / 2
        firewall_rear = c["firewall_x_mm"] + c["firewall_thickness_mm"] / 2
        self.assertEqual(c["engine_bounds_mm"][0][2] - floor_top, 40)
        self.assertEqual(c["engine_bounds_mm"][0][0] - firewall_rear, 67)
        self.assertGreater(40, c["clearance_mm"] + 2 * c["voxel_size_mm"])
        self.assertGreater(67, c["firewall_clearance_mm"] + 2 * c["voxel_size_mm"])
        self.assertEqual(c["rear_track_mm"] + c["wheel_width_mm"], 2100)
        self.assertLess(c["engine_bounds_mm"][1][0], c["rear_axle_x_mm"])

    def test_native_validation_rejects_before_opening_viewer(self):
        dotnet = os.environ.get("DOTNET_TEST_EXECUTABLE") or shutil.which("dotnet")
        binary = ROOT / "twins/vehicle-911-917/picogk/bin/Debug/net9.0/Vehicle911917Packaging.dll"
        if not dotnet or not binary.exists():
            self.skipTest("Built .NET executable not available")
        changes = [("units", "inch", "millimetre"), ("rear_track_mm", -1, "Positive finite"),
                   ("front_steering_sweep_deg", 90, "Steering sensitivity"),
                   ("release_gates", {"manufacturing_authorized": True}, "cannot authorize")]
        for key, value, expected in changes:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                config_path = root / CONFIG.relative_to(ROOT)
                config_path.parent.mkdir(parents=True)
                config = copy.deepcopy(self.config)
                config[key] = value
                config_path.write_text(json.dumps(config))
                env = {**os.environ, "REPOSITORY_ROOT": temporary, "PICOGK_VEHICLE_F15": "1", "PICOGK_STUDY_F14": "0",
                       "PICOGK_OUTPUT_DIR": str(root / "result")}
                result = subprocess.run([dotnet, str(binary)], env=env, capture_output=True, text=True, timeout=15)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)
                self.assertFalse((root / "result").exists())

    def test_native_exports_when_available(self):
        directory = ROOT / "work/911-917-picogk-f15"
        if not (directory / "vehicle-report-f15.json").exists():
            self.skipTest("Native F15 output not available")
        report, config = verify_report(directory)
        self.assertEqual(report["nominal_engine_floor_gap_mm"], 40)
        self.assertEqual(report["nominal_engine_firewall_gap_mm"], 67)
        self.assertFalse(report["checks"]["engine_20mm_plus_numerical_guard__floor"]["collision"])
        self.assertFalse(report["checks"]["engine_50mm_plus_numerical_guard__firewall"]["collision"])
        parts = {part["id"]: part["properties"] for part in report["components"]}
        for name in ("seat_left", "seat_right"):
            self.assertLess(parts[name]["bounds_max_mm"][0], config["occupant_rear_limit_x_mm"])
        self.assertLessEqual(parts["firewall"]["bounds_max_mm"][0] - parts["firewall"]["bounds_min_mm"][0],
                             config["firewall_thickness_mm"] + 2 * report["voxel_size_mm"])


if __name__ == "__main__":
    unittest.main()
