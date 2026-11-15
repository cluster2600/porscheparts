"""The evaluation record of the learned particle simulator stays what it found: not admitted."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks" / "learned-particle-simulator"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LearnedParticleSimulatorRecordTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((BENCH / "results-20261115.json").read_text())
        self.checks = {c["check"]: c for c in self.record["checks"]}

    def test_record_matches_its_scripts_and_names_what_was_run(self):
        self.assertEqual(self.record["script_sha256"], sha(BENCH / "witness_worldparticle.py"))
        self.assertEqual(self.record["cases_script_sha256"], sha(BENCH / "make_cases.py"))
        tool = self.record["tool"]
        self.assertEqual(tool["licence"], "MIT")
        self.assertEqual(len(tool["code_commit"]), 40)
        self.assertEqual(set(tool["checkpoints_sha256"]), {"cloth_on_ball", "fancy_fluid"})
        requirements = (BENCH / "requirements.txt").read_text()
        for pin in ("torch==2.2.2", "open3d==0.19.0", "numpy==1."):
            self.assertIn(pin, requirements)

    def test_limits_were_fixed_first_and_every_check_is_judged_against_them(self):
        limits = self.record["acceptance_fixed_before_the_first_reading"]
        self.assertEqual(limits["fluid_particles_outside_the_tank"], 0)
        self.assertEqual(limits["reproduction_mean_error_at_the_end_in_spacings"], 1.0)
        for check in self.record["checks"]:
            self.assertEqual(check["passed"], check["value"] <= check["limit"], check["check"])
        self.assertEqual(self.record["passed"], all(c["passed"] for c in self.record["checks"]))
        self.assertFalse(self.record["passed"])

    def test_the_authors_scenes_are_reproduced_and_other_scenes_are_not(self):
        self.assertTrue(self.checks["reproduction, cloth: mean error at the end, in spacings"]["passed"])
        self.assertTrue(self.checks["reproduction, fluid (gpu, 599 steps): particles ever outside the tank"]["passed"])
        for name in ("cloth on a plane: flatness, mm", "cloth over a half-cylinder: deepest vertex inside the cylinder, mm",
                     "fluid at rest: particles ever outside the tank", "dam break in the other tank: particles ever outside the tank"):
            self.assertFalse(self.checks[name]["passed"], name)
        transfer = self.record["transfer"]
        small, control = transfer["fluid_at_rest"], transfer["fluid_at_rest_in_a_tank_of_the_training_size"]
        # the same slab leaks from the smaller tank and not from a tank of the training size
        self.assertGreater(small["particles_ever_outside_the_tank"], 0.25 * small["particles"])
        self.assertEqual(sum(control["outside_at_the_end_by_wall"].values()), 0)
        self.assertEqual(small["tank_m"][1], control["tank_m"][1])
        self.assertLess(small["tank_m"][0], control["tank_m"][0])
        # the plane-only sheet stands about as high as the sphere of the training scene (0.6 m)
        self.assertGreater(transfer["cloth_on_a_plane"]["height_above_the_ground_mm"]["highest"], 500.0)

    def test_readme_states_the_verdict_and_what_is_not_covered(self):
        readme = (BENCH / "README.md").read_text()
        self.assertIn("**Verdict: not admitted as a tool.**", readme)
        for phrase in ("No\ncheckpoint covers gases", "no training code is released", "weights-only"):
            self.assertIn(phrase, readme)
        self.assertTrue(any("gases" in item for item in self.record["not_covered"]))
        for picture in ("media/cloth-transfer.png", "media/fluid-transfer.png"):
            self.assertTrue((BENCH / picture).exists())
            self.assertIn(picture, readme)


if __name__ == "__main__":
    unittest.main()
