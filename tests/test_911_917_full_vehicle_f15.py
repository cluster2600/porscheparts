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
from report_full_vehicle_f15 import F13_STATUS, REQUIRED_COMPONENTS, REQUIRED_CHECKS, VIEWS, checked_file, validate_scope, verify_report

CONFIG = ROOT / "twins/vehicle-911-917/full-vehicle-study-f15.json"
SCAN_SHA = "a" * 64


def f13_receipt(**changes):
    # Quarter turn about Z plus a translation: a rigid row-vector motion like the F13 producer's.
    receipt = {"phase": "F13", "status": F13_STATUS, "input_stl_sha256": SCAN_SHA, "triangle_count": 2,
               "matrix4x4_row_vector": [[0, 1, 0, 0], [-1, 0, 0, 0], [0, 0, 1, 0], [1500, 0, 330, 1]],
               "bounds_min_mm": [1500, -300, 180], "bounds_max_mm": [2600, 300, 900],
               "crankshaft_axis_measured": False, "mounting_face_measured": False,
               "scale_verified": False, "physical_orientation_verified": False}
    receipt.update(changes)
    return receipt


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

    def private_report(self, receipt):
        report = copy.deepcopy(self.report)
        report["components"].append({"id": "private_engine_scan", "properties": {
            "volume_mm3": 10, "bounds_min_mm": [1497.5, -302.5, 177.5], "bounds_max_mm": [2602.5, 302.5, 902.5]}})
        report["checks"].update({"private_scan__firewall": {"collision": False}, "private_scan__transaxle": {"collision": False}})
        report["private_scan"] = {"scan_sha256": SCAN_SHA, "alignment_sha256": "b" * 64, "scale_verified": False,
                                  "physical_datum_verified": False, "alignment": receipt}
        return report

    def test_private_scan_needs_its_rigid_f13_receipt(self):
        validate_scope(self.private_report(f13_receipt()), self.config)
        rigid = f13_receipt()["matrix4x4_row_vector"]
        def matrix(rows): return [row + [0] for row in rows] + [rigid[3]]
        bad = {
            "scale": f13_receipt(matrix4x4_row_vector=matrix([[0, 1.02, 0], [-1.02, 0, 0], [0, 0, 1.02]])),
            "shear": f13_receipt(matrix4x4_row_vector=matrix([[0, 1, 0], [-1, 0.2, 0], [0, 0, 1]])),
            "reflection": f13_receipt(matrix4x4_row_vector=matrix([[0, 1, 0], [1, 0, 0], [0, 0, 1]])),
            "projective": f13_receipt(matrix4x4_row_vector=[[0, 1, 0, 0.1], *rigid[1:]]),
            "non_finite": f13_receipt(matrix4x4_row_vector=[*rigid[:3], [float("nan"), 0, 330, 1]]),
            "short": f13_receipt(matrix4x4_row_vector=rigid[:3]),
            "phase": f13_receipt(phase="F12"),
            "status": f13_receipt(status="edited"),
            "claimed_scale": f13_receipt(scale_verified=True),
            "other_scan": f13_receipt(input_stl_sha256="c" * 64),
            "moved": f13_receipt(matrix4x4_row_vector=[*rigid[:3], [1900, 0, 330, 1]], bounds_min_mm=[1900, -300, 180],
                                 bounds_max_mm=[3000, 300, 900]),
            "nan_bounds": f13_receipt(bounds_min_mm=[float("nan"), -300, 180]),
        }
        for name, receipt in bad.items():
            with self.subTest(name), self.assertRaises(ValueError):
                validate_scope(self.private_report(receipt), self.config)
        report = self.private_report(f13_receipt())
        report["private_scan"]["scale_verified"] = True
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

    def test_native_rejects_foreign_or_non_rigid_f13_receipt(self):
        dotnet = os.environ.get("DOTNET_TEST_EXECUTABLE") or shutil.which("dotnet")
        binary = ROOT / "twins/vehicle-911-917/picogk/bin/Debug/net9.0/Vehicle911917Packaging.dll"
        if not dotnet or not binary.exists():
            self.skipTest("Built .NET executable not available")
        stl = bytes(80) + (2).to_bytes(4, "little") + bytes(100)
        rigid = f13_receipt()["matrix4x4_row_vector"]
        cases = [(f13_receipt(matrix4x4_row_vector=[[0, 2, 0, 0], *rigid[1:]]), "without scale or shear"),
                 (f13_receipt(matrix4x4_row_vector=[[0, 1, 0, 0], [1, 0, 0, 0], *rigid[2:]]), "preserve handedness"),
                 (f13_receipt(matrix4x4_row_vector=[[0, 1, 0, 0.5], *rigid[1:]]), "must be affine"),
                 (f13_receipt(status="edited"), "Not an F13 scan alignment receipt"),
                 (f13_receipt(physical_orientation_verified=True), "cannot claim physical datum"),
                 (f13_receipt(triangle_count=3), "triangle count differs"),
                 (f13_receipt(input_stl_sha256="0" * 64), "differs from its F13 alignment receipt")]
        for receipt, expected in cases:
            with self.subTest(expected), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "917-engine-oriented-f10.stl").write_bytes(stl)
                if receipt["input_stl_sha256"] == SCAN_SHA:
                    receipt["input_stl_sha256"] = hashlib.sha256(stl).hexdigest()
                (root / "scan-alignment-f13.json").write_text(json.dumps(receipt))
                env = {**os.environ, "REPOSITORY_ROOT": str(ROOT), "PICOGK_VEHICLE_F15": "1", "PICOGK_STUDY_F14": "0",
                       "PICOGK_INPUT_DIR": temporary, "PICOGK_F13_ALIGNMENT": str(root / "scan-alignment-f13.json"),
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
