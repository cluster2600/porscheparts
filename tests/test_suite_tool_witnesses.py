"""Receipts of the scan-fitting and fatigue tool witnesses stay honest.

These tests need neither Open3D nor pyLife: they recheck the recorded receipts
against the scripts and locks, and recompute everything that does not depend
on the tool under test (ground truth, negative control, ASTM reference, closed
form damage). The cylinder and cone fitter needs only NumPy and SciPy, so it
is also run here, on a small scene with analytic normals.
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


class BoresConesFilletsWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((FIT / "results-bores-cones-fillets-20261110.json").read_text())
        cls.witness = runpy.run_path(str(FIT / "witness_bores_cones_fillets.py"))
        cls.fit = runpy.run_path(str(FIT / "primitive_fit.py"))

    def truths(self):
        import numpy as np

        return self.witness["truth_scene"](np.random.default_rng(self.witness["SEED"]))

    def perfect(self, truth, **changes):
        """The detection an exact fit of ``truth`` would report."""
        if truth["type"] == "plane":
            centre = truth["corner"] + truth["size_mm"][0] / 2 * truth["u"] + truth["size_mm"][1] / 2 * truth["v"]
            found = {"type": "plane", "normal": truth["normal"].tolist(), "point": centre.tolist()}
        else:
            found = {"type": truth["type"], "axis_point": truth["centre"].tolist(), "axis_direction": truth["axis"].tolist(),
                     "axis_direction_sigma_deg": 0.01, "axis_point_sigma_mm": 0.01, "radius_sigma_mm": 0.01}
            if truth["type"] == "cylinder":
                found["radius_mm"] = truth["radius_mm"]
            else:
                import math

                k = math.tan(math.radians(truth["half_angle_deg"]))
                found.update(radius_at_axis_point_mm=truth["radius_mm"], half_angle_deg=truth["half_angle_deg"],
                             apex=(truth["centre"] - truth["radius_mm"] / k * truth["axis"]).tolist())
        return {**found, "points": 1000, "fit_points": 900, "rms_mm": 0.03, "determined": True, **changes}

    def test_receipt_matches_scripts_and_lock(self):
        self.assertEqual(self.report["script_sha256"], sha(FIT / "witness_bores_cones_fillets.py"))
        self.assertEqual(self.report["detector_sha256"], sha(FIT / "primitive_fit.py"))
        self.assertEqual(self.report["lock_sha256"], sha(FIT / "requirements.lock.txt"))
        lock = (FIT / "requirements.lock.txt").read_text()
        for package in ("open3d", "numpy", "scipy"):
            self.assertIn(f"{package}=={self.report[package]}", lock)
        self.assertEqual(self.report["geometry"]["seed"], self.witness["SEED"])
        self.assertNotIn(self.witness["SEED"], self.witness["DEVELOPMENT_SEEDS"])
        self.assertEqual(self.report["acceptance"]["limits"], self.witness["ACCEPT"])
        self.assertEqual(self.report["settings"]["distance_mm"], 3 * self.witness["NOISE_MM"])

    def test_recorded_verdicts(self):
        self.assertEqual(self.report["passed"], {"primitive_fit": True, "cylinder_only_negative_control": False})
        detector = self.report["detector"]
        self.assertEqual(detector["required_within_acceptance"], detector["required"])
        self.assertEqual((detector["unmatched_detections"], detector["determined_outside_acceptance"]), (0, []))
        # The 3 mm fillet is not resolvable at this pitch, and the detector must say so.
        self.assertEqual(detector["limit_probes"], {"fillet-3": "found, reported as not determined"})
        for row in detector["rows"]:
            if row["max_sigmas"] is not None:
                self.assertLessEqual(row["max_sigmas"], self.report["acceptance"]["max_sigmas"], row["name"])
        control = self.report["cylinder_only_negative_control"]
        self.assertEqual(control["within_acceptance_by_kind"]["cone"], "0/6")
        self.assertGreater(control["unmatched_detections"], 0)
        self.assertTrue(control["determined_outside_acceptance"])
        further = self.report["further_seeds"]
        self.assertEqual(further["passed"], sum(scene["passed"] for scene in further["scenes"]))
        self.assertEqual(len(further["scenes"]), further["run"])

    def test_ground_truth_recomputes_without_any_detector(self):
        truths = self.truths()
        self.assertEqual([t["name"] for t in truths], [row["name"] for row in self.report["detector"]["rows"]])
        kinds = {k: sum(t["type"] == k for t in truths) for k in ("plane", "cylinder", "cone")}
        self.assertEqual(kinds, self.report["geometry"]["kinds"])
        self.assertEqual({t["half_angle_deg"] for t in truths if t["type"] == "cone"}, {0.5, 1.0, 2.0, 30.0, 45.0})

    def test_scoring_rejects_wrong_type_spurious_and_confident_errors(self):
        truths = self.truths()
        exact = [self.perfect(t, determined=t["name"] not in self.witness["LIMIT_PROBES"]) for t in truths]
        self.assertTrue(self.witness["score"](truths, exact)["passed"])
        self.assertFalse(self.witness["score"](truths, exact + [exact[0]])["passed"])       # an unmatched detection
        drafted = next(i for i, t in enumerate(truths) if t["name"] == "drafted-boss-1deg")
        as_cylinder = list(exact)
        as_cylinder[drafted] = {**self.perfect({**truths[drafted], "type": "cylinder"})}
        result = self.witness["score"](truths, as_cylinder)
        self.assertFalse(result["passed"])
        self.assertEqual(result["determined_outside_acceptance"], ["drafted-boss-1deg"])
        probe = next(i for i, t in enumerate(truths) if t["name"] == "fillet-3")
        confident = list(exact)
        confident[probe] = self.perfect({**truths[probe], "radius_mm": 3.5})                # determined, 0.5 mm off
        self.assertFalse(self.witness["score"](truths, confident)["passed"])

    def test_detector_recovers_a_plane_a_bore_and_a_drafted_boss(self):
        import numpy as np

        rng = np.random.default_rng(7)
        z = np.array([0.0, 0.0, 1.0])
        truths = [
            {"name": "bore", "class": "axial", "type": "cylinder", "centre": np.array([0.0, 0.0, 0.0]), "axis": z,
             "radius_mm": 10.0, "length_mm": 20.0, "arc_deg": 360.0, "half_angle_deg": 0.0, "side": "concave"},
            {"name": "boss", "class": "axial", "type": "cone", "centre": np.array([60.0, 0.0, 0.0]), "axis": z,
             "radius_mm": 12.0, "length_mm": 20.0, "arc_deg": 360.0, "half_angle_deg": 1.0, "side": "convex"},
            {"name": "deck", "class": "plane", "type": "plane", "corner": np.array([-20.0, 40.0, 0.0]),
             "u": np.array([1.0, 0.0, 0.0]), "v": np.array([0.0, 1.0, 0.0]), "normal": z, "size_mm": (40.0, 40.0)},
        ]
        patches = [(self.witness["plane_patch"] if t["type"] == "plane" else self.witness["axial_patch"])(t, rng)
                   for t in truths]
        points = np.vstack([p[0] for p in patches])
        normals = np.vstack([p[2] for p in patches])                     # analytic normals: no Open3D needed
        settings = self.fit["settings"](self.witness["NOISE_MM"], self.witness["PITCH_MM"])
        found, unassigned = self.fit["detect"](points, normals, settings, seed=7)
        self.assertEqual(sorted(f["type"] for f in found), ["cone", "cylinder", "plane"])
        self.assertLess(len(unassigned), 0.02 * len(points))
        result = self.witness["score"](truths, found)
        self.assertTrue(result["passed"], result["rows"])
        boss = next(f for f in found if f["type"] == "cone")
        self.assertAlmostEqual(boss["half_angle_deg"], 1.0, delta=0.05)
        self.assertEqual((boss["side"], next(f for f in found if f["type"] == "cylinder")["side"]), ("convex", "concave"))
        # Assuming the draft away loses the boss: a cylinder cannot hold it within the limits.
        control, _ = self.fit["detect"](points, normals, {**settings, "allow_cones": False}, seed=7)
        self.assertFalse(self.witness["score"](truths, control)["passed"])


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
