import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PART = ROOT / "parts/993-eng-cooling-impeller-we43-f1-0001"
SCRIPT = PART / "source/fe_screen_f1.py"
REPORT = PART / "evidence/fe-screen/fe-screen.json"
BENCH = PART / "evidence/fe-screen/solver-benchmarks.json"
PLOT = PART / "evidence/fe-screen/campbell.png"
RECORD = ROOT / "catalog/parts/993-eng-cooling-impeller-we43-f1-0001.json"
SPEC = importlib.util.spec_from_file_location("fe_screen_f1", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CoolingImpellerFEScreenF1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT.read_text())

    def test_report_is_fail_closed_and_matches_the_committed_step(self) -> None:
        r = self.report
        self.assertEqual(r["part_id"], "993-ENG-COOLING-IMPELLER-WE43-F1-0001")
        self.assertEqual(r["status"], "screen_unvalidated")
        self.assertFalse(r["manufacturing_authorized"])
        self.assertFalse(r["engine_operation_authorized"])
        self.assertFalse(r["mesh_independence_demonstrated"])
        step = ROOT / r["geometry"]["step"]
        self.assertEqual(hashlib.sha256(step.read_bytes()).hexdigest(), r["geometry"]["sha256"])
        self.assertTrue(PLOT.exists())

    def test_solver_benchmarks_hit_the_closed_form_answers(self) -> None:
        b = json.loads(BENCH.read_text())
        self.assertEqual(self.report["solver_benchmarks"], b)
        self.assertLess(abs(b["spinning_disc_bore_hoop"]["relative_error"]), 0.01)
        # a plate is slightly stiffer than an Euler-Bernoulli beam
        self.assertLess(0.0, b["cantilever_plate_first_mode"]["relative_error"])
        self.assertLess(b["cantilever_plate_first_mode"]["relative_error"], 0.03)
        # one-thread SPOOLES must repeat exactly
        plate = b["cantilever_plate_first_mode"]
        self.assertEqual(plate["fe_hz"], plate["repeat_hz"])

    def test_every_run_covers_the_speed_range_with_all_modes(self) -> None:
        cases = [run["case"] for run in self.report["runs"]]
        self.assertEqual(sorted(cases), ["bore", "clamped"])
        for run in self.report["runs"]:
            self.assertEqual([s["rpm"] for s in run["speeds"]], MODULE.SPEEDS_RPM)
            self.assertAlmostEqual(run["mass_g"], 421.0, delta=2.0)
            for s in run["speeds"]:
                self.assertEqual(len(s["frequencies_hz"]), MODULE.MODES)
                self.assertEqual(s["frequencies_hz"], sorted(s["frequencies_hz"]))
                self.assertEqual(len(s["modes"]), MODULE.MODES)

    def test_stored_crossings_are_recomputed_from_the_stored_modes(self) -> None:
        for run in self.report["runs"]:
            self.assertEqual(MODULE.crossings(run), run["engine_order_crossings"])

    def test_nodal_diameter_aliasing_on_eleven_blades(self) -> None:
        mode = lambda cup, tips: {"nd_cup_lip": cup, "nd_blade_tips": tips}
        self.assertTrue(MODULE.nd_matches(17, mode(5, 5)))    # 17 = 11 + 6 -> ND 6 ~ ND 5
        self.assertTrue(MODULE.nd_matches(12, mode(1, 1)))    # 12 = 11 + 1
        self.assertTrue(MODULE.nd_matches(6, mode(5, 5)))
        self.assertFalse(MODULE.nd_matches(17, mode(1, 1)))
        self.assertFalse(MODULE.nd_matches(3, mode(1, 1)))

    def test_stator_order_crosses_a_blade_mode_inside_the_nominal_range(self) -> None:
        # The finding the dossier reports: in both hub cases the 17-vane
        # stator order meets the ND5 blade family below 10,000 rpm.
        for run in self.report["runs"]:
            hits = [c for c in run["engine_order_crossings"]
                    if c["engine_order"] == 17 and c["nodal_diameter_matched"]]
            self.assertTrue(hits)
            self.assertTrue(all(6_000 < c["rpm"] < 10_000 for c in hits))
            self.assertTrue(all(c["nd_blade_tips"] == 5 for c in hits))

    def test_blade_family_sits_well_above_the_beam_estimate(self) -> None:
        screen = json.loads((PART / "evidence/engineering-screen.json").read_text())
        beam = screen["material_screens"]["WE43_LPBF_T6"]["results"]["blade_first_mode_cantilever_hz"]
        for run in self.report["runs"]:
            zero = run["speeds"][0]
            blade = [m["hz"] for m in zero["modes"] if m["tip_to_lip_amplitude"] > 3.0]
            self.assertGreater(min(blade), 1.3 * beam)

    def test_peak_stress_exceeds_the_beam_screen_and_stays_below_yield(self) -> None:
        screen = json.loads((PART / "evidence/engineering-screen.json").read_text())
        beam = screen["material_screens"]["WE43_LPBF_T6"]["results"]
        for run in self.report["runs"]:
            top = run["at_max_speed"]
            self.assertEqual(top["rpm"], 12_000)
            self.assertGreater(top["peak_von_mises_mpa"], 3 * beam["overspeed_hub_rim_hoop_stress_mpa"])
            self.assertGreater(top["yield_over_peak"], 2.0)
            self.assertLess(top["blade_tip_radial_growth_mm"], 0.1)

    def test_catalogue_record_links_the_fe_screen(self) -> None:
        record = json.loads(RECORD.read_text())
        evidence = record["validation"]["evidence"]
        for path in (REPORT, BENCH, PLOT, SCRIPT):
            self.assertIn(str(path.relative_to(ROOT)), evidence)
        self.assertEqual(record["classification"]["safety_class"], "prohibited_pending_engineering")


if __name__ == "__main__":
    unittest.main()
