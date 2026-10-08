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
        self.assertTrue(all(r["z_mm"] is None and not r["xyz_validated"] for r in rows))
        # Projected: every point with a located X and a published pair span.
        not_projected = {r["datum_id"] for r in rows if not r["shown_as_xy_hypothesis"]}
        self.assertEqual(not_projected, {"P1", "P2", "P4", "P6", "P7", "P11", "P15", "P16"})
        for key in ("P1", "P2", "P4", "P6", "P7", "P11", "P16"):
            self.assertIsNone(by_id[key]["x_vehicle_hypothesis_mm"])
        self.assertIsNone(by_id["P6"]["x_relative_mm"])          # no published longitudinal dimension
        self.assertIsNone(by_id["P15"]["y_half_hypothesis_mm"])   # plate 50-05a gives no P15 span
        self.assertEqual(by_id["P13"]["x_relative_status"], "MESURE_DESSIN")
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
        # The committed measurement sheet is exactly what the contract produces.
        saved = TWIN / "derived/interface-measurements-20261008.csv"
        self.assertEqual(sheet.encode(), saved.read_bytes())


if __name__ == "__main__":
    unittest.main()
