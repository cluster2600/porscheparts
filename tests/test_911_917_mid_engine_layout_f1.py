import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins" / "vehicle-911-917"
CONFIG = TWIN / "packaging-concept-f1.json"
WORK = ROOT / "work" / "911-917-packaging-f1"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class Vehicle911917MidEngineLayoutF1Tests(unittest.TestCase):
    def test_contract_moves_engine_ahead_of_rear_axle(self) -> None:
        config = load_json(CONFIG)

        self.assertEqual(config["concept_id"], "911-917-VEHICLE-PACKAGING-F1")
        self.assertEqual(config["body_and_occupant_screening_mm"]["selected_wheelbase_extension"], 450.0)
        self.assertTrue(config["body_and_occupant_screening_mm"]["rear_seats_deleted"])
        self.assertIn("mid_engine", config["rear_transaxle_screening"]["architecture"])
        self.assertIsNone(config["rear_transaxle_screening"]["candidate_selected"])
        self.assertFalse(any(config["release_gates"].values()))

    def test_local_scan_outputs_are_reproducible_when_available(self) -> None:
        scan = ROOT / "raw-scans" / "917-engine" / "original" / "917-engine-case-with-cylinders.obj"
        report = WORK / "packaging-report-f1.json"
        if not scan.exists() or not report.exists():
            self.skipTest("scan brut et sorties locales volontairement absents de Git")

        completed = subprocess.run(
            [
                "python3",
                str(TWIN / "source" / "build_mid_engine_layout_f1.py"),
                "--mode",
                "check",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        generated = load_json(report)
        selected = next(
            item
            for item in generated["layout_screening"]["trials"]
            if item["layout_id"] == generated["decision"]["selected_layout_id"]
        )
        self.assertEqual(selected["wheelbase_extension_mm"], 450.0)
        self.assertTrue(selected["screening_pass"])
        self.assertGreater(selected["rear_axle_x_mm"], selected["engine_scan_geometric_centre_x_mm"])
        self.assertGreaterEqual(selected["front_occupant_to_engine_service_clearance_mm"], 100.0)
        self.assertGreaterEqual(selected["firewall_to_engine_service_clearance_mm"], 50.0)
        self.assertFalse(generated["handling_screening"]["weight_distribution_computed"])
        self.assertIsNone(generated["decision"]["gearbox_selected"])
        self.assertFalse(any(generated["release_gates"].values()))


if __name__ == "__main__":
    unittest.main()
