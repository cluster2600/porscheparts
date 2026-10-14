import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins" / "vehicle-911-917"
CONFIG = TWIN / "picogk-full-vehicle-f12.json"
ANNOTATE = TWIN / "source" / "annotate_picogk_full_vehicle_f12.py"


class Vehicle911917PicoGKFullVehicleF12Tests(unittest.TestCase):
    def test_full_model_remains_fail_closed(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["phase"], "F12")
        self.assertTrue(all(value is False for value in config["release_gates"].values()))
        self.assertIn("not_selected", config["transaxle_reservation"]["status"])

        report_path = ROOT / "work" / "911-917-picogk-f12" / "picogk-full-vehicle-report-f12.json"
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(len(report["layers"]), 9)
            self.assertFalse(report["release_gates"]["physical_fit_verified"])
            self.assertTrue((report_path.parent / report["assembly_vdb"]).is_file())

    def test_annotator_rejects_promoted_report(self) -> None:
        spec = importlib.util.spec_from_file_location("annotate_picogk_f12", ANNOTATE)
        self.assertIsNotNone(spec)
        self.assertIn('report["phase"] != "F12"', ANNOTATE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
