import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "twins/reference-917-engine/motion-video-f7.json"
ENGINE = ROOT / "twins/reference-917-engine/complete-engine-f1.json"


class Engine917MotionVideoF7Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_shots_cover_the_timeline_without_gaps(self):
        shots = self.config["shots"]
        covered = [frame for shot in shots for frame in range(shot["start"], shot["end"] + 1)]
        expected = list(range(self.config["timeline"]["start_time_code"], self.config["timeline"]["end_time_code"] + 1))
        self.assertEqual(covered, expected)
        self.assertEqual(len(covered), self.config["acceptance"]["expected_frame_count"])

    def test_duration_and_rate_match_existing_kinematics(self):
        timeline = self.config["timeline"]
        self.assertEqual(timeline["frames_per_second"], 24)
        self.assertEqual(timeline["duration_seconds"], 10.0)

    def test_video_discloses_that_motion_is_not_physical_simulation(self):
        self.assertFalse(self.config["acceptance"]["physical_simulation_claim_authorized"])
        self.assertIn("aucune combustion", self.config["disclosure"])
        self.assertEqual(self.config["encode"]["audio"], "none")

    def test_every_component_family_has_a_visual_material_hypothesis(self):
        engine = json.loads(ENGINE.read_text(encoding="utf-8"))
        expected = {item["id"] for item in engine["component_families"]}
        visual = self.config["visual_materials"]
        self.assertEqual(set(visual["family_assignments"]), expected)
        self.assertLessEqual(set(visual["family_assignments"].values()), set(visual["palette"]))
        self.assertIn("not_historical", visual["claim_status"])


if __name__ == "__main__":
    unittest.main()
