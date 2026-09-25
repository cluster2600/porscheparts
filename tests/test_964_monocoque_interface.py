import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins/964-chassis"


class MonocoqueInterfaceTests(unittest.TestCase):
    def test_report_preserves_manual_identity_missing_data_and_release_limits(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            (work / "source").mkdir()
            (work / "derived").mkdir()
            subprocess.run(
                [sys.executable, str(TWIN / "source/monocoque_interface.py")],
                cwd=work / "source", check=True, capture_output=True, text=True,
            )
            generated = (work / "derived/monocoque-interface.json").read_text()

        report = json.loads(generated)
        ledger = json.loads((ROOT / "catalog/measurements/MEAS-MANUAL-964-BODY-CONTROL.json").read_text())
        names = {row["details"]["point"]: row for row in ledger["declared_values"]
                 if row["details"]["kind"] == "datum_point"}
        spans = [row for row in ledger["declared_values"]
                 if row["details"].get("measurement_kind") == "transverse"]
        self.assertEqual(report["points"]["P12"]["designation"], names[12]["value_text"])
        self.assertEqual(report["points"]["P12"]["fonction_monocoque"], "groupe motopropulseur")
        self.assertEqual(set(report["points"]), {f'P{row["details"]["between"][0]}' for row in spans})
        for row in spans:
            number = row["details"]["between"][0]
            point = report["points"][f"P{number}"]
            self.assertEqual(point["designation"], names[number]["value_text"])
            self.assertEqual(point["designation_source_value_id"], names[number]["value_id"])
            self.assertEqual(point["transverse_span_mm"], row["numeric_values"][0])
            self.assertEqual(point["transverse_tolerance_mm"], row["numeric_values"][1])
            self.assertEqual(point["y_half_mm"], row["numeric_values"][0] / 2)
            self.assertIsNone(point["y_tolerance_mm"])
        self.assertEqual(report["points"]["P6"]["x_statut"], "MANQUANT")
        self.assertEqual(report["points"]["P6"]["fonction_monocoque"], "suspension")
        self.assertIsNone(report["points"]["P6"]["x_local_mm"])
        self.assertIsNone(report["points"]["P6"]["x_vehicle_mm_provisoire"])
        self.assertEqual(report["points"]["P21"]["x_statut"], "INVALIDE")
        self.assertFalse(report["cote_gouvernante"]["defines_wheelbase"])
        self.assertAlmostEqual(report["cote_gouvernante"]["valeur_mm"], 1724.3)
        self.assertEqual(report["classe_securite"], "prohibited_pending_engineering")
        self.assertFalse(any(report["release_flags"].values()))
        self.assertEqual(generated, (TWIN / "derived/monocoque-interface.json").read_text())


if __name__ == "__main__":
    unittest.main()
