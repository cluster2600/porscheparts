import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins" / "vehicle-911-917"
CONFIG = TWIN / "packaging-concept-f0.json"
WORK = ROOT / "work" / "911-917-packaging-f0"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class Vehicle911917PackagingF0Tests(unittest.TestCase):
    def test_contract_keeps_every_release_gate_closed(self) -> None:
        config = load_json(CONFIG)

        self.assertEqual(config["concept_id"], "911-917-VEHICLE-PACKAGING-F0")
        self.assertEqual(
            config["gearbox_research"]["preferred_architecture"],
            "front_of_engine_rear_transaxle_like_911",
        )
        self.assertTrue(all(
            candidate["public_overall_dimensions_mm"] is None
            for candidate in config["gearbox_research"]["candidates"]
        ))
        self.assertFalse(any(config["release_gates"].values()))

    def test_gearbox_is_not_selected_from_torque_claims_alone(self) -> None:
        config = load_json(CONFIG)
        candidates = {
            candidate["candidate_id"]: candidate
            for candidate in config["gearbox_research"]["candidates"]
        }

        self.assertEqual(candidates["dma_1071_w_2wd"]["maximum_input_torque_nm"]["five_speed"], 1200.0)
        self.assertEqual(candidates["dma_s1098"]["maximum_input_torque_nm"]["sprint_hillclimb"], 1300.0)
        self.assertIn("requires_GA", candidates["dma_1071_w_2wd"]["screening_decision"])
        self.assertIn("unresolved", candidates["dma_s1098"]["screening_decision"])

    def test_local_scan_outputs_are_reproducible_when_available(self) -> None:
        scan = ROOT / "raw-scans" / "917-engine" / "original" / "917-engine-case-with-cylinders.obj"
        report = WORK / "packaging-report-f0.json"
        if not scan.exists() or not report.exists():
            self.skipTest("scan brut et sorties locales volontairement absents de Git")

        completed = subprocess.run(
            [
                "python3",
                str(TWIN / "source" / "build_packaging_concept_f0.py"),
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
        self.assertTrue(generated["source_integrity"]["source_scan_sha256_matches_f21"])
        self.assertIsNone(generated["decision"]["gearbox_selected"])
        self.assertEqual(generated["decision"]["preferred_layout_id"], "911_FRONT_GEARBOX_LONG_TAIL_450")
        self.assertFalse(any(generated["release_gates"].values()))


if __name__ == "__main__":
    unittest.main()
