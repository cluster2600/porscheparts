"""Receipts of the scan-fitting and fatigue tool witnesses stay honest.

These tests need neither Open3D nor pyLife: they recheck the recorded receipts
against the scripts and locks, and recompute everything that does not depend
on the tool under test (ground truth, negative control, ASTM reference, closed
form damage).
"""
import hashlib
import json
import runpy
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIT = ROOT / "benchmarks/scan-primitive-fitting"
FATIGUE = ROOT / "benchmarks/fatigue-postprocessor"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ScanPrimitiveFittingWitnessTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((FIT / "results-20261110.json").read_text())
        self.witness = runpy.run_path(str(FIT / "witness_drafted_fins.py"))

    def test_receipt_matches_script_and_lock(self):
        self.assertEqual(self.report["script_sha256"], sha(FIT / "witness_drafted_fins.py"))
        self.assertEqual(self.report["lock_sha256"], sha(FIT / "requirements.lock.txt"))
        lock = (FIT / "requirements.lock.txt").read_text()
        self.assertIn(f"open3d=={self.report['open3d']}", lock)
        self.assertIn(f"numpy=={self.report['numpy']}", lock)

    def test_only_the_assigned_method_passes(self):
        self.assertEqual(self.report["passed"], {
            "open3d_sequential_ransac": True,
            "open3d_patches_library_defaults": False,
            "z_level_histogram_negative_control": False,
        })
        ransac = self.report["detectors"]["open3d_sequential_ransac"]
        self.assertEqual(ransac["found_within_acceptance"], ransac["faces"])
        self.assertEqual(ransac["unmatched_detections"], 0)
        self.assertLessEqual(ransac["max_tilt_error_deg"], self.report["acceptance"]["tilt_error_max_deg"])

    def test_ground_truth_and_negative_control_recompute(self):
        import numpy as np

        rng = np.random.default_rng(self.witness["SEED"])
        faces, cen, nrm, area, _ = self.witness["build"](rng)
        self.assertEqual(len(cen), self.report["geometry"]["samples"])
        drafted = [f for f in faces if f["draft_deg"] > 0]
        self.assertEqual(len(drafted), 20)
        level = self.witness["score"](faces, self.witness["z_level_histogram"](cen, nrm, area))
        recorded = self.report["detectors"]["z_level_histogram_negative_control"]
        self.assertEqual(level["found_within_acceptance"], recorded["found_within_acceptance"])
        self.assertEqual(level["unmatched_detections"], recorded["unmatched_detections"])
        self.assertEqual(level["found_by_draft_deg"], recorded["found_by_draft_deg"])


class FatiguePostprocessorWitnessTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((FATIGUE / "results-20261110.json").read_text())
        self.witness = runpy.run_path(str(FATIGUE / "witness_rainflow_miner.py"))

    def test_receipt_matches_script_and_lock(self):
        self.assertEqual(self.report["script_sha256"], sha(FATIGUE / "witness_rainflow_miner.py"))
        self.assertEqual(self.report["lock_sha256"], sha(FATIGUE / "requirements.lock.txt"))
        self.assertIn(f"pylife=={self.report['pylife']}", (FATIGUE / "requirements.lock.txt").read_text())
        self.assertTrue(self.report["passed"])

    def test_independent_astm_rainflow_reproduces_the_standard_and_the_tool(self):
        counted = self.witness["astm_rainflow"](self.witness["HISTORY"])
        self.assertEqual(counted, self.witness["ASTM_TABLE"])
        recorded = {float(k): v for k, v in self.report["rainflow"]["pylife_three_point"].items()}
        self.assertEqual(recorded, counted)
        self.assertEqual(sum(counted.values()), (len(self.witness["HISTORY"]) - 1) / 2)

    def test_recorded_damage_equals_closed_form(self):
        collective = {float(k): v for k, v in self.report["damage"]["collective_amplitude_mpa"].items()}
        for name, elementary in (("miner_original", False), ("miner_elementary", True)):
            expected = self.witness["closed_form_damage"](collective, elementary)
            self.assertAlmostEqual(self.report["damage"][name]["pylife"] / expected, 1.0, places=12)
        # Original Miner ignores the two amplitudes below SD; elementary does not.
        self.assertLess(self.report["damage"]["miner_original"]["pylife"],
                        self.report["damage"]["miner_elementary"]["pylife"])


if __name__ == "__main__":
    unittest.main()
