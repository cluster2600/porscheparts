import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PART = ROOT / "parts/993-eng-intercooler-bracket-ti-f1-0001"
SCRIPT = PART / "source/intercooler_bracket_f1.py"
RECORD = ROOT / "catalog/parts/993-eng-intercooler-bracket-ti-f1-0001.json"
REPORT = PART / "evidence/engineering-screen.json"
SPEC = importlib.util.spec_from_file_location("intercooler_bracket_f1", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class IntercoolerBracketTiF1Tests(unittest.TestCase):
    def test_sagitta_fills_the_published_width_exactly(self) -> None:
        self.assertAlmostEqual(MODULE._top_y(MODULE.ARM_SAGITTA_MM), 80.0, places=6)

    def test_every_interface_stays_blocked_until_measured(self) -> None:
        self.assertEqual([i["id"] for i in MODULE.INTERFACES], ["IF-1", "IF-2", "IF-3"])
        for interface in MODULE.INTERFACES:
            self.assertEqual(interface["status"], "blocked_unmeasured")
            self.assertIn("candidate", interface["hardware_assignment"])

    def test_screen_claims_no_load_result_and_no_release(self) -> None:
        report = MODULE.screen()
        self.assertIsNone(report["load_case"])
        self.assertFalse(report["release_authorized"])

    def test_committed_report_and_record_agree(self) -> None:
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        self.assertEqual(record["validation"]["status"], "concept")
        self.assertEqual(report["step_check"]["envelope_mm"], [255.0, 80.0, 23.0])
        self.assertAlmostEqual(report["arc"]["sagitta_mm"], MODULE.ARM_SAGITTA_MM, places=9)
        for path in record["geometry"]["derived_files"]:
            self.assertTrue((ROOT / path).is_file(), path)
        # A titanium copy of a cast-aluminium shape must not be sold as lighter.
        mass = report["mass"]
        self.assertGreater(mass["ti64_mass_g"], mass["cast_aluminium_equivalent_mass_g"])


if __name__ == "__main__":
    unittest.main()
