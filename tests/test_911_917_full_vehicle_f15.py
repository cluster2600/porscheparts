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
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "twins/vehicle-911-917/source"))
sys.path.insert(0, str(ROOT / "tests"))
import test_911_917_picogk_alignment_f13 as f13_tests
import report_full_vehicle_f15
from report_full_vehicle_f15 import REQUIRED_COMPONENTS, REQUIRED_CHECKS, VIEWS, checked_file, validate_scope, verify_report

CONFIG = ROOT / "twins/vehicle-911-917/full-vehicle-study-f15.json"
SCAN_SHA = "a" * 64


def f13_receipt(**changes):
    # Only the fields the F15 record itself reads; F13 provenance and rigidity are checked by its own validator.
    receipt = {"phase": "F13", "input_stl_sha256": SCAN_SHA, "bounds_min_mm": [1500, -300, 180], "bounds_max_mm": [2600, 300, 900]}
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

    def test_private_scan_record_is_bound_to_its_receipt(self):
        validate_scope(self.private_report(f13_receipt()), self.config)
        bad = {"other_scan": f13_receipt(input_stl_sha256="c" * 64),
               "moved": f13_receipt(bounds_min_mm=[1900, -300, 180], bounds_max_mm=[3000, 300, 900]),
               "nan_bounds": f13_receipt(bounds_min_mm=[float("nan"), -300, 180]),
               "no_bounds": {"input_stl_sha256": SCAN_SHA}}
        for name, receipt in bad.items():
            with self.subTest(name), self.assertRaises(ValueError):
                validate_scope(self.private_report(receipt), self.config)
        for key, value in (("scale_verified", True), ("physical_datum_verified", True), ("extra", 1)):
            report = self.private_report(f13_receipt())
            report["private_scan"][key] = value
            with self.subTest(key), self.assertRaises(ValueError):
                validate_scope(report, self.config)

    def test_reporter_applies_the_f13_receipt_rules(self):
        report = self.private_report(f13_receipt())
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(report_full_vehicle_f15, "validate_alignment", side_effect=ValueError("F13 rules")) as rules:
            (Path(temporary) / "vehicle-report-f15.json").write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "F13 rules"):
                verify_report(Path(temporary))
            rules.assert_called_once_with(report["private_scan"]["alignment"])

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

    def test_native_preflight_applies_f13_receipt_rules(self):
        dotnet = os.environ.get("DOTNET_TEST_EXECUTABLE") or shutil.which("dotnet")
        binary = ROOT / "twins/vehicle-911-917/picogk/bin/Debug/net9.0/Vehicle911917Packaging.dll"
        if not dotnet or not binary.exists():
            self.skipTest("Built .NET executable not available")
        with f13_tests.ScanAlignmentTests.alignment_fixture(self) as (root, path):
            for relative in (CONFIG.relative_to(ROOT), Path("twins/vehicle-911-917/picogk-full-vehicle-f12.json")):
                shutil.copyfile(ROOT / relative, root / relative)
            genuine = json.loads(path.read_text())
            def run(receipt):
                (root / "receipt.json").write_text(json.dumps(receipt))
                env = {**os.environ, "REPOSITORY_ROOT": str(root), "PICOGK_VEHICLE_F15": "1", "PICOGK_STUDY_F14": "0",
                       "PICOGK_INPUT_DIR": str(f13_tests.alignment.STL.parent), "PICOGK_F13_ALIGNMENT": str(root / "receipt.json"),
                       "PICOGK_OUTPUT_DIR": str(root / "result")}
                return subprocess.run([dotnet, str(binary)], env=env, capture_output=True, text=True, timeout=15)
            def changed(**fields):
                return {**copy.deepcopy(genuine), **fields}
            cases = [(changed(matrix4x4_row_vector=[[2, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]), "rigid row-vector"),
                     (changed(matrix4x4_row_vector=[[0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]), "rigid row-vector"),
                     (changed(status="edited"), "Unqualified F13 alignment receipt"),
                     (changed(physical_orientation_verified=True), "Unqualified F13 alignment receipt"),
                     (changed(input_stl_sha256="0" * 64), "F13 prepared scan changed"),
                     (changed(triangle_count=genuine["triangle_count"] + 1), "triangle count differs"),
                     (changed(bounds_min_mm=genuine["bounds_max_mm"], bounds_max_mm=genuine["bounds_min_mm"]), "bounds must be ordered")]
            stale = root / "twins/vehicle-911-917/picogk-mechanical-f13.json"
            for receipt, expected in cases + [(genuine, "F13 alignment input changed")]:
                if receipt is genuine:
                    stale.write_text(stale.read_text() + "\n")
                with self.subTest(expected):
                    result = run(receipt)
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
