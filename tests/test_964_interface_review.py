import copy
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import runpy
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins/964-chassis"


@unittest.skipIf(importlib.util.find_spec("numpy") is None, "numpy required for scan diagnostics")
class InterfaceReviewTests(unittest.TestCase):
    def test_review_keeps_every_identity_without_inventing_z_or_reviving_invalid_x(self):
        sys.path.insert(0, str(TWIN / "source"))
        try:
            module = runpy.run_path(str(TWIN / "source/interface_review.py"))
        finally:
            sys.path.pop(0)
        contract = json.loads((TWIN / "derived/monocoque-interface.json").read_text())
        ledger = json.loads((ROOT / contract["source_ledger"]).read_text())
        rows = module["review_rows"](contract, ledger)
        by_id = {r["datum_id"]: r for r in rows}
        self.assertEqual(len(rows), 18)
        self.assertEqual(sum(r["shown_as_xy_hypothesis"] for r in rows), 7)
        self.assertTrue(all(r["z_mm"] is None and not r["xyz_validated"] for r in rows))
        for key in ("P6", "P21", "P4", "P13", "P14", "P15"):
            self.assertFalse(by_id[key]["shown_as_xy_hypothesis"])
            self.assertIsNone(by_id[key]["x_vehicle_hypothesis_mm"])
        self.assertIsNone(by_id["P21"]["x_relative_mm"])
        self.assertEqual(by_id["P12"]["designation"], "Support - traverse de boite")
        self.assertEqual(by_id["P17"]["x_relative_mm"], 0)
        self.assertEqual(by_id["P17"]["transverse_tolerance_mm"], 1)
        sheet = module["measurement_csv"](rows)
        self.assertTrue(all(r["z_mm"] == "" for r in csv.DictReader(io.StringIO(sheet))))
        for mutation in ("nonfinite", "identity", "released", "missing"):
            bad = copy.deepcopy(contract)
            if mutation == "nonfinite":
                bad["points"]["P17"]["x_vehicle_mm_provisoire"] = float("nan")
            elif mutation == "identity":
                bad["points"]["P17"]["designation_source_value_id"] = "wrong"
            elif mutation == "released":
                bad["release_flags"]["geometry_released"] = True
            else:
                bad["points"]["P17"]["x_vehicle_mm_provisoire"] = None
            with self.assertRaises(ValueError):
                module["review_rows"](bad, ledger)
        saved = TWIN / "derived/interface-measurements-20260925.csv"
        self.assertEqual(sheet.encode(), saved.read_bytes())
        report = json.loads((TWIN / "derived/interface-review-20260925.json").read_text())
        self.assertEqual(report["measurement_sheet_sha256"], hashlib.sha256(saved.read_bytes()).hexdigest())
        for path, digest in report["input_sha256"].items():
            self.assertEqual(digest, hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
        self.assertFalse(any(report["release_flags"].values()))
        self.assertEqual(report["validated_xyz_points"], 0)


if __name__ == "__main__":
    unittest.main()
