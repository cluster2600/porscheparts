"""Issue #707: the two inherited NVIDIA warnings, the SimReady profiles and the RTX capture.

The warning repairs run on synthetic boxes; the committed record is checked for what it may and may
not claim. The private stage never reaches CI.
"""

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins" / "935-cylinder-head-cad-twin"
RECORD = TWIN / "params" / "simready-conformance-gpu.json"
ADMITTED_IMAGE = ("ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:"
                  "5a69a6805a275ef708e264600cb933663159a2846b069eafe0459c28e5f69699")


def has(*mods):
    return all(importlib.util.find_spec(m) is not None for m in mods)


def load_module():
    spec = importlib.util.spec_from_file_location("stage_warnings", TWIN / "source" / "stage_warnings.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def box():
    import numpy as np

    v = np.array([[x, y, z] for x in (-10.0, 10.0) for y in (-15.0, 15.0) for z in (-5.0, 5.0)])
    f = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                  [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return v, f


@unittest.skipUnless(has("numpy"), "numpy absent")
class StageWarningRepairTests(unittest.TestCase):
    def setUp(self):
        self.sw = load_module()

    def with_cap(self):
        """A box whose edge 0-1 carries a vertex at its midpoint, closed by a face without area."""
        import numpy as np

        v, f = box()
        c = len(v)
        v = np.vstack([v, (v[0] + v[1]) / 2])
        # (0, 1, 3) runs 0 -> 1: split it at c; the cap (0, 1, c) pairs with (0, 5, 1) across 1 -> 0.
        f = np.vstack([f[1:], [[0, c, 3], [c, 1, 3], [0, 1, c]]])
        return v, f

    def test_a_cap_is_flat_in_float32_and_a_flip_removes_it_without_opening_the_box(self):
        v, f = self.with_cap()
        before = self.sw.signed_volume(v, f)
        self.assertTrue(self.sw.topology(f)["closed_and_consistently_wound"])
        self.assertEqual(int(self.sw.flat_in_float32(v, f).sum()), 1)
        for mode in ("float32", "broad"):
            v2, f2, counts = self.sw.repair(v, f, mode)
            self.assertEqual(counts["caps_flipped"], 1, mode)
            self.assertEqual(int(self.sw.flat_in_float32(v2, f2).sum()), 0, mode)
            self.assertTrue(self.sw.topology(f2)["closed_and_consistently_wound"], mode)
            self.assertAlmostEqual(self.sw.signed_volume(v2, f2), before, places=9)
            self.assertEqual(counts["largest_surface_change_mm"], 0.0)

    def test_a_point_closer_than_float32_spacing_is_one_weld_group_and_collapses_back(self):
        import numpy as np

        v, f = box()
        q = len(v)
        # A point 1e-7 mm inside face (0, 1, 3), below the float32 spacing near 10 mm.
        v = np.vstack([v, v[0] + 1.0e-7 * (v[1] + v[3] - 2 * v[0]) / np.linalg.norm(v[1] + v[3] - 2 * v[0])])
        f = np.vstack([f[1:], [[0, 1, q], [1, 3, q], [3, 0, q]]])
        self.assertTrue(self.sw.topology(f)["closed_and_consistently_wound"])
        self.assertEqual(self.sw.colocated_groups(v), [[0, q]])
        self.assertEqual(self.sw.classify_groups(v, f, [[0, q]]), {"joined_by_an_edge": 1})
        v2, f2, counts = self.sw.repair(v, f, "float32")
        self.assertEqual(counts["edges_collapsed"], 1)
        self.assertLess(counts["largest_vertex_move_mm"], 1.0e-6)
        self.assertEqual(self.sw.colocated_groups(v2), [])
        self.assertEqual(len(f2), 12)
        self.assertTrue(self.sw.topology(f2)["closed_and_consistently_wound"])

    def test_a_collapse_that_would_pinch_the_surface_is_refused(self):
        import numpy as np

        # Two tetrahedra sharing nothing, with a vertex of one 1e-7 mm from a vertex of the other,
        # near 10 mm where float32 cannot tell them apart: one float32 point, but no edge joins
        # them, so nothing may weld them.
        t = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
        tf = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
        v = np.vstack([t + 10.0, -t + [10.0, 10.0, 10.0 + 1.0e-7]])
        f = np.vstack([tf, tf[:, ::-1] + 4])
        self.assertTrue(self.sw.topology(f)["closed_and_consistently_wound"])
        self.assertEqual(len(self.sw.colocated_groups(v)), 1)
        self.assertEqual(self.sw.classify_groups(v, f, self.sw.colocated_groups(v)),
                         {"more_than_four_edges_apart": 1})
        v2, f2, counts = self.sw.repair(v, f, "float32")
        self.assertEqual((counts["edges_collapsed"], counts["caps_flipped"]), (0, 0))
        self.assertEqual(len(self.sw.colocated_groups(v2)), 1)


class ConformanceRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = json.loads(RECORD.read_text())

    def test_claims_only_a_well_formed_stage(self):
        claims = self.r["claims"]
        for words in ("well-formed", "not measured, not functional, not released"):
            self.assertIn(words, claims)

    def test_runtime_is_the_admitted_image_on_a_named_gpu(self):
        rt = self.r["runtime"]
        self.assertEqual(rt["image"], ADMITTED_IMAGE)
        guard = (ROOT / "deploy" / "openbao" / "openbao-ghcr").read_text()
        self.assertIn(ADMITTED_IMAGE.split("@")[1], guard)
        self.assertIn("RTX", rt["gpu"]["name"])
        self.assertTrue(rt["gpu"]["driver"])
        self.assertEqual(rt["ovrtx_version"], "0.3.0")

    def test_rental_stayed_in_budget_and_was_destroyed(self):
        rent = self.r["rental"]
        self.assertLessEqual(rent["spent_usd"], rent["budget_usd"])
        self.assertLessEqual(rent["budget_usd"], 4.0)
        self.assertTrue(rent["destroyed_and_absent_from_the_account"])
        self.assertEqual(rent["label"], "porscheparts-935-707-simready")

    def test_the_two_warnings_are_explained_and_no_trial_cleared_them(self):
        w = self.r["inherited_warnings"]
        self.assertEqual(sorted(w["rules"]), ["WeldChecker", "ZeroAreaFaceChecker"])
        self.assertFalse(w["cleared"])
        audit = w["audit"]
        self.assertTrue(audit["stage_points_are_float32_of_body"] and audit["stage_faces_are_body_faces"])
        zero = audit["zero_area_face_checker"]
        self.assertEqual(zero["faces_below_1e-12_mm2_in_double"], 35)   # the count usd-cad-summary.json gives
        self.assertGreater(zero["faces_flat_in_float32"], zero["faces_below_1e-12_mm2_in_double"])
        weld = audit["weld_checker"]
        self.assertEqual(weld["groups_distinct_in_double"] + weld["groups_coincident_in_double"],
                         weld["colocated_float32_groups"])
        self.assertFalse(w["trials"]["a_trial_clears_both_warnings"])
        for mode in ("broad", "float32", "manifold"):
            after = w["trials"][mode]["after"]
            self.assertTrue(after["closed_and_consistently_wound"], mode)
            self.assertGreater(after["faces_flat_in_float32"] + after["colocated_float32_groups"], 0, mode)
        usd = json.loads((TWIN / "params" / "usd-cad-summary.json").read_text())
        self.assertEqual(usd["faces_without_area"], zero["faces_below_1e-12_mm2_in_double"])

    def test_profiles_report_every_run_and_pass_nothing_that_needs_mass(self):
        runs = self.r["profile_conformance"]["runs"]
        self.assertGreater(len(runs), 0)
        for run in runs:
            self.assertIn(run["result"], ("pass", "fail", "unavailable"))
            if run["result"] == "pass":
                self.assertFalse(run["profile"].lower().startswith(("prop-robotics", "robotics-prop")), run)

    def test_every_failing_requirement_has_a_cause_and_the_rigid_body_waits_for_the_alloy(self):
        causes = self.r["profile_conformance"]["requirement_causes"]
        self.assertFalse([r for r, c in causes.items() if c["blocked_by"] == "unclassified"])
        self.assertEqual(causes["com.nvidia.simready.RB.001"]["blocked_by"], "#705")
        failing = {r for run in self.r["profile_conformance"]["runs"] for r in run.get("blocking_requirements", [])}
        self.assertEqual(failing, set(causes))
        stacks = self.r["profile_conformance"]["stacks"]
        self.assertEqual(stacks["image"]["foundation_commit"], "0ed0dfbc539c9de99289771bd6848effe3ef5779")
        self.assertEqual(stacks["latest"]["simready-validate"], "2026.10.0")

    def test_newest_nvidia_validator_writes_the_report_already_recorded(self):
        latest = self.r["nvidia_validator_latest"]
        self.assertEqual(latest["version"], "1.23.0")
        recorded = json.loads((TWIN / "params" / "simready-validate-cad-stage.json").read_text())
        for name, asset in latest["assets"].items():
            self.assertEqual(sorted(asset["rules_with_issues"]), ["WeldChecker", "ZeroAreaFaceChecker"], name)
            self.assertEqual(asset["receipt_sha256"], recorded["stage_input"]["validation"]["raw_report_sha256"], name)

    def test_published_still_is_the_captured_one(self):
        rtx = self.r["rtx"]
        entry = json.loads((TWIN / "media" / "provenance.json").read_text())["images"]["rtx-camside.png"]
        self.assertEqual(rtx["published"], "media/rtx-camside.png")
        self.assertEqual(entry["source_sha256"], rtx["media_sha256"]["camside.png"])
        self.assertEqual(entry["capture_receipt_sha256"], rtx["capture_receipt_sha256"])

    def test_unknowns_stay_null_with_their_blockers(self):
        missing = self.r["not_authored"]
        for key, blocker in (("mass_kg", "#705"), ("inertia", "#705"), ("density", "#705"),
                             ("whole_body_step", "#695"), ("thermal_field", "#702"), ("stress_field", "#703")):
            self.assertIsNone(missing[key]["value"], key)
            self.assertIn(blocker, missing[key]["blocked_by"], key)

    def test_rtx_capture_is_bound_to_the_recorded_stage(self):
        rtx = self.r["rtx"]
        asset = json.loads((TWIN / "params" / "simready-asset.json").read_text())
        self.assertEqual(rtx["cad_stage_sha256"], asset["source_stage_sha256"])
        self.assertEqual(rtx["ovrtx_version"], "0.3.0")
        self.assertTrue(rtx["read_by_the_agent"])
        for name, digest in rtx["media_sha256"].items():
            self.assertRegex(digest, r"^[0-9a-f]{64}$", name)


if __name__ == "__main__":
    unittest.main()
