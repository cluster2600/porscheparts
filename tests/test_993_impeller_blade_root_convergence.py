"""The blade-root refinement ladder and its convergence verdict.

A re-entrant corner has no finite peak stress, so the screen must be able to
say "no converged peak exists" rather than report the last mesh's number. The
geometry-building parts of fe_screen_f1 need gmsh, OpenCASCADE and CalculiX;
only the verdict logic is exercised here, on synthetic runs.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PART = ROOT / "parts/993-eng-cooling-impeller-we43-f1-0001"
SCRIPT = PART / "source/fe_screen_f1.py"
EVIDENCE = PART / "evidence/fe-screen/blade-root-convergence.json"
BLEND = PART / "evidence/fe-screen/blade-root-blend-attempts.json"
SPEC = importlib.util.spec_from_file_location("fe_screen_f1", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class Args:
    def __init__(self, work, out, rpm=12000, geometry="synthetic"):
        self.work = work
        self.out = out
        self.rpm = rpm
        self.geometry = geometry


def _runs(tmp, peaks, rpm=12000, refined=True):
    """One workdir per (root size, peak) pair, in fe_screen_f1's result format."""
    works = []
    for i, (h, peak) in enumerate(peaks):
        w = Path(tmp) / f"rs{i}"
        w.mkdir()
        (w / "result.json").write_text(json.dumps({
            "case": "clamped", "size_mm": 4.0, "size_min_mm": 1.5,
            "root_size_mm": h if refined else None,
            "nodes": 1000 * (i + 1), "elements": 900 * (i + 1),
            "speeds": [{"rpm": rpm, "peak_von_mises_mpa": peak, "peak_region": "blade",
                        "peak_location_mm": [82.5, 0.0, 20.0],
                        "peak_by_region_mpa": {"blade": peak}}],
        }))
        works.append(str(w))
    return works


class BladeRootConvergenceTests(unittest.TestCase):
    def test_a_peak_that_keeps_climbing_is_reported_as_not_converged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "conv.json"
            MODULE.rootconv(Args(_runs(tmp, [(2.0, 88.5), (1.4, 102.0), (1.0, 119.0), (0.7, 141.0)]), str(out)))
            d = json.loads(out.read_text())
            self.assertFalse(d["peak_converged"])
            self.assertIn("no converged peak stress", d["note"])
            # a positive log-log slope is the signature of the singularity
            self.assertGreater(d["fitted_log_log_slope"], 0.1)
            # coarsest first, and every step recorded against the one before
            self.assertEqual([r["root_size_mm"] for r in d["runs"]], [2.0, 1.4, 1.0, 0.7])
            self.assertNotIn("relative_change", d["runs"][0])
            self.assertAlmostEqual(d["runs"][1]["relative_change"], (102.0 - 88.5) / 88.5)

    def test_a_settling_peak_is_reported_as_converged_with_a_flat_slope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "conv.json"
            MODULE.rootconv(Args(_runs(tmp, [(2.0, 60.0), (1.4, 64.0), (1.0, 64.6), (0.7, 64.9)]), str(out)))
            d = json.loads(out.read_text())
            self.assertTrue(d["peak_converged"])
            self.assertLess(abs(d["fitted_log_log_slope"]), 0.1)

    def test_one_late_jump_breaks_convergence_even_after_two_quiet_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "conv.json"
            MODULE.rootconv(Args(_runs(tmp, [(2.0, 60.0), (1.4, 60.2), (1.0, 60.3), (0.7, 75.0)]), str(out)))
            self.assertFalse(json.loads(out.read_text())["peak_converged"])

    def test_two_points_cannot_declare_convergence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "conv.json"
            MODULE.rootconv(Args(_runs(tmp, [(2.0, 60.0), (1.4, 60.1)]), str(out)))
            # one relative change is not two: a single quiet step proves nothing
            self.assertFalse(json.loads(out.read_text())["peak_converged"])

    def test_an_unrefined_baseline_is_not_a_step_in_the_ladder(self) -> None:
        # The baseline runs on the global sizing, not on the root field, so it
        # must not become the neighbour that the first refined step is
        # measured against.
        with tempfile.TemporaryDirectory() as tmp:
            refined = _runs(tmp, [(2.0, 88.5), (1.4, 100.2), (1.0, 110.1)])
            base_dir = Path(tmp) / "base"
            base_dir.mkdir()
            (base_dir / "result.json").write_text(json.dumps({
                "case": "clamped", "size_mm": 4.0, "size_min_mm": 1.5, "root_size_mm": None,
                "nodes": 100, "elements": 89227,
                "speeds": [{"rpm": 12000, "peak_von_mises_mpa": 89.16, "peak_region": "cup_rim",
                            "peak_location_mm": [82.5, 0.0, 20.0],
                            "peak_by_region_mpa": {"cup_rim": 89.16}}],
            }))
            out = Path(tmp) / "conv.json"
            MODULE.rootconv(Args([str(base_dir)] + refined, str(out)))
            d = json.loads(out.read_text())
            self.assertEqual([r["root_size_mm"] for r in d["runs"]], [2.0, 1.4, 1.0])
            self.assertEqual(len(d["unrefined_baseline"]), 1)
            self.assertEqual(d["unrefined_baseline"][0]["elements"], 89227)
            # the first refined point stays the ladder's origin
            self.assertNotIn("relative_change", d["runs"][0])
            self.assertAlmostEqual(d["runs"][1]["relative_change"], (100.2 - 88.5) / 88.5)

    def test_a_missing_speed_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            works = _runs(tmp, [(2.0, 60.0), (1.4, 61.0)], rpm=8500)
            with self.assertRaises(SystemExit):
                MODULE.rootconv(Args(works, str(Path(tmp) / "conv.json"), rpm=12000))

    def test_root_curves_are_clustered_per_blade_not_counted(self) -> None:
        # A blended root has a different curve count from the sharp one, so the
        # mesher checks that the selection reaches all eleven blades instead.
        class FakeGmsh:
            def __init__(self, angles):
                self.angles = angles
                self.model = self

            def getParametrizationBounds(self, dim, tag):
                return ([0.0], [1.0])

            def getValue(self, dim, tag, ts):
                import math as m
                a = m.radians(self.angles[tag])
                return [82.5 * m.cos(a), 82.5 * m.sin(a), 20.0]

        step = 360.0 / MODULE.BLADES
        all_blades = {i: i * step for i in range(MODULE.BLADES)}
        g = FakeGmsh(all_blades)
        self.assertEqual(MODULE.root_curve_clusters(g, list(all_blades)), list(range(MODULE.BLADES)))
        # several curves on one blade still count as that one blade
        many = {0: 0.0, 1: 1.0, 2: -1.0}
        self.assertEqual(MODULE.root_curve_clusters(FakeGmsh(many), list(many)), [0])

    @unittest.skipUnless(EVIDENCE.exists(), "ladder evidence not generated")
    def test_the_recorded_ladder_is_a_real_measurement_of_the_published_rotor(self) -> None:
        d = json.loads(EVIDENCE.read_text())
        self.assertEqual(d["rpm"], 12000)
        self.assertGreaterEqual(len(d["runs"]), 4)
        sizes = [r["root_size_mm"] for r in d["runs"]]
        self.assertEqual(sizes, sorted(sizes, reverse=True))
        for r in d["runs"]:
            self.assertGreater(r["elements"], 0)
            self.assertGreater(r["peak_von_mises_mpa"], 0.0)
        # the ladder must actually refine: elements grow as the size falls
        elements = [r["elements"] for r in d["runs"] if r["root_refined"]]
        self.assertEqual(elements, sorted(elements))
        self.assertFalse(d["peak_converged"])


class BladeRootBlendRecordTests(unittest.TestCase):
    @unittest.skipUnless(BLEND.exists(), "blend evidence not generated")
    def setUp(self) -> None:
        self.d = json.loads(BLEND.read_text())

    def test_the_record_claims_no_stress_and_no_authorisation(self) -> None:
        self.assertEqual(self.d["status"], "blend_builds_but_is_not_solvable")
        self.assertFalse(self.d["manufacturing_authorized"])
        self.assertTrue(any("no root margin" in x or "no root stress" in x
                            for x in self.d["limitations"]))

    def test_every_radius_records_whether_it_meshes_and_its_measured_curvature(self) -> None:
        radii = self.d["geometry"]["radii_mm"]
        self.assertGreaterEqual(len(radii), 4)
        for r in radii:
            # the blend is accepted on curvature, so the measured median must
            # match the requested radius closely
            self.assertAlmostEqual(r["median_curvature_radius_mm"], r["radius_mm"], places=3)
            self.assertIsInstance(r["meshes_as_imported"], bool)
            # the run-out is always far sharper than nominal: that is the defect
            self.assertLess(r["min_curvature_radius_mm"], r["radius_mm"])
        unmeshable = [r for r in radii if not r["meshes_as_imported"]]
        self.assertTrue(unmeshable, "the self-intersecting radius must be recorded")
        for r in unmeshable:
            self.assertIn("mesher_error", r)

    def test_the_optimiser_is_recorded_as_not_fixing_the_inverted_elements(self) -> None:
        tried = self.d["solver_refusal"]["high_order_optimizer_does_not_fix_it"]
        self.assertEqual(len(tried), 4)
        # if any setting had cleared them the claim would be false
        for t in tried:
            self.assertGreater(t["nonpositive"], 0)
            self.assertLess(t["min_det_jac"], 0.0)

    def test_volume_is_explicitly_excluded_as_an_acceptance_metric(self) -> None:
        self.assertIn("never_accepted_on", self.d["geometry"])
        self.assertIn("volume", self.d["geometry"]["never_accepted_on"])

    def test_the_blended_ladder_cost_is_measured_against_a_reference_run(self) -> None:
        cost = self.d["blended_ladder_cost"]
        rungs = cost["rungs"]
        self.assertEqual([r["curvature_sampling"] for r in rungs], sorted(r["curvature_sampling"] for r in rungs))
        elements = [r["elements"] for r in rungs]
        self.assertEqual(elements, sorted(elements))
        # the coarsest rung must exceed the reference the verdict compares it to
        self.assertGreater(elements[0], cost["reference_point"]["elements"])


if __name__ == "__main__":
    unittest.main()
