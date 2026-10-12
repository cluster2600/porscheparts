import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/vehicle-911-917/source"
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location("leap_f16", SOURCE / "run_leap_f16.py")
f16 = importlib.util.module_from_spec(spec); spec.loader.exec_module(f16)


class LeapF16Tests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((f16.STUDY / "study.json").read_text())

    def test_declared_scope(self):
        f16.validate_config(self.config)
        self.assertEqual(len(f16.PARTS), 10)

    def test_rejects_promoted_gates(self):
        for key in f16.GATES:
            c = copy.deepcopy(self.config); c[key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                f16.validate_config(c)

    def test_rejects_units_and_resolution(self):
        for key, value in (("units", "inch"), ("voxel_size_mm", 2.5)):
            c = copy.deepcopy(self.config); c[key] = value
            with self.assertRaises(ValueError): f16.validate_config(c)

    def test_rejects_unresolved_or_nonfinite_dimensions(self):
        for value in (0, 5, -1, True, float("nan"), float("inf")):
            c = copy.deepcopy(self.config); c["duct_wall_mm"] = value
            with self.subTest(value=value), self.assertRaises(ValueError): f16.validate_config(c)

    def test_rejects_missing_or_degenerate_routes(self):
        for mode in ("missing", "repeated", "far"):
            c = copy.deepcopy(self.config)
            if mode == "missing": c["ducts"].pop()
            if mode == "repeated": c["ducts"][0]["control_points_mm"][1] = c["ducts"][0]["control_points_mm"][0]
            if mode == "far": c["ducts"][0]["control_points_mm"][0][0] = 10000
            with self.subTest(mode=mode), self.assertRaises(ValueError): f16.validate_config(c)

    def test_native_receipt_when_available(self):
        directory = os.environ.get("PICOGK_F16_RESULT")
        if not directory: self.skipTest("Set PICOGK_F16_RESULT for the installed Mac native result")
        r = f16.verify_output(Path(directory))
        self.assertEqual(len(r["checks"]), 45)
        self.assertGreater(r["solid_fraction_in_zone"], 0)
        self.assertLess(r["solid_fraction_in_zone"], 1)


if __name__ == "__main__": unittest.main()
