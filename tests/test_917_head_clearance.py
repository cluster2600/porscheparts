import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "models/917-engine-reconstruction/clearance"
SCIENCE = all(importlib.util.find_spec(name) for name in ("numpy", "trimesh", "manifold3d", "matplotlib"))
if SCIENCE:
    import numpy as np
    import trimesh
    SPEC = importlib.util.spec_from_file_location("head_clearance", HERE / "check_clearance.py")
    CHECK = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(CHECK)


class HeadClearanceTests(unittest.TestCase):
    @unittest.skipUnless(SCIENCE, "Geometry runtime required")
    def test_four_compact_envelopes_preserve_bore_and_reject_release(self):
        plan = json.loads((HERE / "plan.json").read_text())
        recipe, axes = CHECK.recipe(plan)
        self.assertEqual(len(recipe["parts"]), 4)
        self.assertEqual(len(axes), 4)
        for axis in axes.values():
            self.assertAlmostEqual(sum(x*x for x in axis), 1)
        plan["manufacturing_authorized"] = True
        with self.assertRaises(ValueError):
            CHECK.recipe(plan)

    @unittest.skipUnless(SCIENCE, "Geometry runtime required")
    def test_intersection_distinguishes_contact_from_projection_and_failure(self):
        a = trimesh.creation.box(extents=(2, 2, 2))
        b = a.copy(); b.apply_translation([1, 0, 0])
        self.assertAlmostEqual(CHECK.common_volume(a, b)["volume_mm3_hypothesis"], 4)
        b.apply_translation([2, 0, 0])
        self.assertEqual(CHECK.common_volume(a, b)["volume_mm3_hypothesis"], 0)
        broken = a.copy(); broken.update_faces(np.arange(len(a.faces)-1))
        with self.assertRaises(ValueError):
            CHECK.common_volume(broken, a)

    def test_recorded_screen_keeps_physical_gates_closed_and_binds_sources(self):
        report = json.loads((HERE / "execution-20261012.json").read_text())
        for name, expected in report["source_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)
        self.assertEqual(report["pose_count"], 384)
        self.assertEqual(len(report["native_candidate_audits"]), 8)
        self.assertTrue(all(a["passed"] for a in report["native_candidate_audits"]))
        for key in ("cam_law_validated", "positive_clearance_validated", "manufacturing_authorized", "functional_assembly_accepted"):
            self.assertFalse(report[key])
        self.assertTrue(report["new_head_body_seats_guides_ports_required"])
        self.assertTrue(report["sampled_poses_not_continuous_sweep"])


if __name__ == "__main__":
    unittest.main()
