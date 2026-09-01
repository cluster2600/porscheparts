import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "twins" / "reference-917-engine" / "kinematics-f2.json"


class Engine917KinematicsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_firing_order_contains_each_cylinder_once(self):
        self.assertEqual(sorted(self.config["firing_order"]["sequence"]), list(range(1, 13)))

    def test_slider_model_reaches_declared_stroke(self):
        crank = self.config["crank_slider"]["stroke_mm"] / 2
        rod = self.config["crank_slider"]["connecting_rod_center_distance_mm"]

        def position(angle_deg):
            angle = math.radians(angle_deg)
            return crank * math.cos(angle) + math.sqrt(rod**2 - (crank * math.sin(angle)) ** 2)

        self.assertAlmostEqual(position(0) - position(180), self.config["crank_slider"]["stroke_mm"])

    def test_motion_hypotheses_are_not_manufacturing_claims(self):
        self.assertIn("hypothesis", self.config["cylinder_numbering_hypothesis"]["status"])
        self.assertIn("not_measured", self.config["valve_motion_hypothesis"]["status"])
        self.assertEqual(self.config["physics_policy"]["combustion"], "disabled")
        self.assertIn("engine_part_manufacturing", self.config["prohibited_use"])


if __name__ == "__main__":
    unittest.main()
