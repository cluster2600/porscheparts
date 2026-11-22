"""Supports of the 935 print body prepared by an open build processor (PySLM), against the rule layout.

The measuring code runs here on synthetic geometry; the committed records are checked against each other
and against the plan written before the run. PySLM itself, the print body and the private envelopes never
reach CI.
"""

import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins" / "935-cylinder-head-cad-twin"
PARAMS = TWIN / "params"
SOURCE = TWIN / "source"


def box(lo, hi):
    """Closed, outward-wound triangle mesh of an axis-aligned box."""

    import numpy as np

    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], dtype=float)
    f = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4],
                  [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
    return v, f


class MeasuringCodeTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(SOURCE))
        import numpy as np
        import support_build_processor as sbp
        import support_design as sd

        self.np, self.sbp, self.sd = np, sbp, sd

    def test_the_voxeliser_counts_closed_boxes_once(self):
        np, sbp = self.np, self.sbp
        one = box((2.13, 3.07, 1.11), (12.13, 8.07, 9.11))                   # 10 x 5 x 8 mm, off the grid
        vox = sbp.voxelise([one], (80, 80, 80))
        self.assertAlmostEqual(vox.sum() * sbp.PITCH ** 3, 400.0, delta=4.0)
        two = box((7.13, 3.07, 1.11), (17.13, 8.07, 9.11))                   # overlaps the first by half
        both = sbp.voxelise([one, two], (80, 80, 80))
        self.assertAlmostEqual(both.sum() * sbp.PITCH ** 3, 600.0, delta=6.0)
        inverted = (one[0], one[1][:, ::-1])                                 # inward-wound: nothing is inside
        self.assertEqual(int(sbp.voxelise([inverted], (80, 80, 80)).sum()), 0)

    def test_the_rule_layout_measured_here_gives_back_its_own_numbers(self):
        np, sbp, sd = self.np, self.sbp, self.sd
        p = sbp.PITCH
        axes = [np.arange(a + p / 2, b, p) for a, b in zip((-22, -22, 0), (22, 22, 42))]
        x, y, z = np.meshgrid(*axes, indexing="ij")
        tee = ((abs(x) < 10) & (abs(y) < 10) & (z < 30)) | ((abs(x) < 20) & (abs(y) < 20) & (z > 30) & (z < 40))
        rules = {"critical_angle_from_plate_deg": 45.0, "self_supporting_width_mm": 1.0, "slenderness_limit": None,
                 "block_support": {"hatch_mm": 1.0, "wall_thickness_mm": 0.2, "tooth_contact_share_of_the_wall_line": 0.5}}
        rep, kind = sd.layout(tee, p, rules)
        t = sd.transitions(tee, p, 45.0)
        ref = {key: t[key][t["over"]] for key in ("i", "j", "k")}
        plate = int(np.flatnonzero(tee.any(axis=(0, 1)))[0])
        m = sbp.measure(kind > 0, tee, ref, plate)
        self.assertEqual(m["supported_projected_area_mm2"], rep["supported"]["projected_area_mm2"])
        self.assertEqual(m["envelope_volume_mm3"], rep["supported"]["envelope_volume_mm3"])
        self.assertEqual(m["contact_with_the_part_projected_mm2"]["at_the_foot"], rep["supported"]["landing_area_on_part_mm2"])
        self.assertAlmostEqual(m["envelope_by_landing"]["on_plate_mm3"], 36000.0, delta=0.01 * 36000.0)
        self.assertEqual(m["envelope_by_landing"]["ending_in_air_mm3"], 0.0)
        self.assertAlmostEqual(m["tallest_column_mm"], 30.0, delta=0.5)
        self.assertEqual(m["unsupported_reference_surface"]["count"], 0)

        # a layout that stops 1.5 mm short of the cap's outer rim leaves a band bare and says how wide it is
        cut = (kind > 0) & (abs(x) < 18.5) & (abs(y) < 18.5)
        m = sbp.measure(cut, tee, ref, plate)
        bare = m["unsupported_reference_surface"]
        self.assertAlmostEqual(bare["projected_area_mm2"], 40.0 ** 2 - 37.0 ** 2, delta=0.03 * (40.0 ** 2 - 37.0 ** 2))
        self.assertEqual(bare["count"], 1)
        self.assertAlmostEqual(bare["largest_inscribed_width_mm"], 1.5, delta=0.5)
        self.assertAlmostEqual(bare["widest_patches"][0]["height_above_plate_mm"], 30.0, delta=0.5)

    def test_a_column_that_stops_short_of_the_plate_ends_in_the_air(self):
        np, sbp = self.np, self.sbp
        solid = np.zeros((20, 20, 60), dtype=bool)
        solid[0:2, 0:2, 0:44] = True                                          # a post that sets the plate level
        solid[0:5, 0:2, 40:44] = True                                         # and carries the slab
        solid[5:15, 5:15, 40:44] = True                                       # a slab hanging at 10 mm
        env = np.zeros_like(solid)
        env[5:15, 5:15, 20:40] = True                                         # 19 voxels short of the plate
        runs = sbp.column_runs(env, solid, 0)
        vol = sbp.runs_volume(env, runs)
        self.assertEqual(vol["ending_in_air_mm3"], float(env.sum()) * sbp.PITCH ** 3)
        self.assertTrue(runs["top_touches_part"].all())
        env[5:15, 5:15, 1:40] = True
        vol = sbp.runs_volume(env, sbp.column_runs(env, solid, 0))
        self.assertEqual(vol["on_plate_mm3"], float(env.sum()) * sbp.PITCH ** 3)
        # a column over a part voxel stands on the part, even at the plate level, as in support_design.py
        solid[5:7, 5:7, 0] = True
        env[5:7, 5:7, 0] = False
        runs = sbp.column_runs(env, solid, 0)
        self.assertEqual(int(runs["foot_on_part"].sum()), 4)


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((PARAMS / "support-build-processor-plan.json").read_text())
        self.witness = json.loads((PARAMS / "support-build-processor-witness.json").read_text())

    def test_the_plan_pins_the_processor_the_carrier_pins_and_the_rule_layouts_build(self):
        carrier = json.loads((ROOT / "parts" / "993-eng-carrier-0001" / "source" / "process-coverage-20261016" / "upstream.json").read_text())
        proc = self.plan["processor"]
        self.assertEqual(proc["revision"], carrier["revision"])
        self.assertEqual(proc["licence"], carrier["license"])
        self.assertEqual(proc["licence_sha256"], carrier["license_sha256"])
        self.assertIn("none", proc["patches"])
        case = json.loads((PARAMS / "support-design-case.json").read_text())
        self.assertEqual(self.plan["orientation"]["build_direction"], case["build"]["direction"])
        self.assertEqual(self.plan["orientation"]["name"], case["build"]["orientation_in_the_screen"])
        self.assertEqual(self.plan["parameters"]["overhang_angle_deg"], case["rules"]["critical_angle_from_plate_deg"])
        rule = json.loads((PARAMS / "support-design.json").read_text())
        self.assertIn(rule["occupancy_sha256"], self.plan["input"]["occupancy"])
        self.assertEqual(set(self.plan["compared"]["quantities"]),
                         {"supported_area", "support_volume", "contact_area_with_the_part", "regions", "max_overhang_left_unsupported"})

    def test_the_witness_passed_and_its_settings_are_the_planned_defaults(self):
        self.assertTrue(self.witness["passed"])
        planned = self.plan["parameters"]["defaults_at_this_revision"]
        settings = self.witness["settings"]
        for key, value in planned.items():
            name = key.rsplit("_", 1)[0] if key.endswith(("_mm", "_mm2", "_deg")) else key
            self.assertEqual(settings[name], value, key)
        by_name = {(c["witness"], c["quantity"]): c for c in self.witness["cases"]}
        for (name, _), case in by_name.items():
            if "within_tolerance" in case:
                self.assertTrue(case["within_tolerance"], name)
        self.assertEqual(by_name[("G1 height-map canvases in one process", "canvases drawn in a row, of 120")]["measured"], 120)

    def test_the_comparison_record_follows_its_plan_and_adds_up(self):
        record = json.loads((PARAMS / "support-build-processor.json").read_text())
        sha = lambda name: hashlib.sha256((PARAMS / name).read_bytes()).hexdigest()  # noqa: E731
        self.assertEqual(record["plan_sha256"], sha("support-build-processor-plan.json"))
        self.assertEqual(record["witness_sha256"], sha("support-build-processor-witness.json"))
        rule = json.loads((PARAMS / "support-design.json").read_text())
        self.assertEqual(record["occupancy_sha256"], rule["occupancy_sha256"])
        self.assertTrue(all(c["equal"] for key, c in record["consistency_with_the_committed_rule_layout"].items() if key != "note"))
        self.assertFalse(any(record["gates"].values()))
        self.assertFalse(record["for_issue_706"]["counts_as_prepared_by_a_build_processor"])

        # the processor that ran is the planned one, in a declared state
        run = record["processor_run"]
        self.assertEqual(run["library"]["packages"]["PythonSLM"], "0.6.1")
        self.assertEqual(run["library"]["source_sha256"]["gridBlockSupport.py"],
                         self.plan["processor"]["upstream_support_sources_sha256"]["gridBlockSupport.py"])
        self.assertTrue(run["library"]["state"].startswith(("upstream", "declared fallback 1")))
        self.assertEqual(run["mesh_file"], "print-body-mc050.stl")
        self.assertEqual(run["settings"]["rayProjectionResolution"], self.plan["parameters"]["defaults_at_this_revision"]["rayProjectionResolution_mm"])
        if run["library"]["state"].startswith("declared fallback 1"):
            self.assertTrue(any("fallback 1" in d for d in record["deviations_from_the_plan"]))
        if "fallback" in run:
            self.assertIsNone(run["settings"]["splineSimplificationFactor"])
            self.assertTrue(any("fallback 2" in d for d in record["deviations_from_the_plan"]))

        # the regions partition the reference surface and the two envelopes
        r, mine, theirs = record["regions"], record["rule_layout"], record["processor_layout"]
        parts = r["supported_by_both_mm2"] + r["supported_by_the_processor_only_mm2"] + r["supported_by_the_rule_only_mm2"] + r["supported_by_neither_mm2"]
        self.assertAlmostEqual(parts, r["reference_surface_projected_mm2"], places=6)
        self.assertAlmostEqual(r["supported_by_both_mm2"] + r["supported_by_the_rule_only_mm2"], mine["supported_projected_area_mm2"], places=6)
        self.assertAlmostEqual(r["supported_by_both_mm2"] + r["supported_by_the_processor_only_mm2"], theirs["supported_projected_area_mm2"], places=6)
        self.assertAlmostEqual(r["envelope_in_both_mm3"] + r["envelope_of_the_rule_only_mm3"], mine["envelope_volume_mm3"], places=6)
        self.assertAlmostEqual(r["envelope_in_both_mm3"] + r["envelope_of_the_processor_only_mm3"], theirs["envelope_volume_mm3"], places=6)
        for layout in (mine, theirs, record["sensitivity_not_in_the_plan"]["processor_layout"]):
            self.assertAlmostEqual(sum(layout["envelope_by_landing"].values()), layout["envelope_volume_mm3"], places=6)
            bare = layout["unsupported_reference_surface"]
            self.assertAlmostEqual(bare["projected_area_mm2"] + layout["supported_projected_area_mm2"], r["reference_surface_projected_mm2"], places=6)
            self.assertGreaterEqual(bare["largest_patch_mm2"], max(p["projected_area_mm2"] for p in bare["widest_patches"]))
        self.assertEqual(r["reference_surface_projected_mm2"], rule["before_exemption"]["overhang_projected_area_mm2"])

        # the voxeliser holds each block to the library's own volume; overlaps between blocks are counted once
        vox = record["voxelised"]
        self.assertLess(abs(vox["one_by_one_against_the_block_meshes"]), 0.02)
        self.assertGreaterEqual(vox["overlap_between_blocks_mm3"], 0.0)

        # the diagnosis accounts for every region the library processed
        diag = record["diagnosis_of_the_dropped_overhang"]
        self.assertEqual(sum(s["regions"] for s in diag["steps"].values()), diag["regions"])
        self.assertEqual(diag["regions"], run["log"]["subregions"])

    def test_the_readme_quotes_the_record(self):
        record = json.loads((PARAMS / "support-build-processor.json").read_text())
        readme = (TWIN / "README.md").read_text()
        section = readme.split("### Supports from an open build-preparation library", 1)[1].split("\n### ", 1)[0]
        mine, theirs = record["rule_layout"], record["processor_layout"]
        other = record["sensitivity_not_in_the_plan"]["processor_layout"]
        for value in (f"{theirs['supported_share_of_the_reference_surface'] * 100:.1f}%",
                      f"{other['supported_share_of_the_reference_surface'] * 100:.1f}%",
                      f"{mine['supported_projected_area_mm2']:,.0f} mm²", f"{theirs['supported_projected_area_mm2']:,.0f} mm²",
                      f"{mine['envelope_volume_mm3']:,.0f} mm³", f"{theirs['envelope_volume_mm3']:,.0f} mm³",
                      f"{theirs['unsupported_reference_surface']['projected_area_mm2']:,.0f} mm²",
                      f"{theirs['unsupported_reference_surface']['largest_inscribed_width_mm']:.1f} mm",
                      f"{record['regions']['reference_surface_projected_mm2']:,.0f} mm²"):
            self.assertIn(value, section, value)
        self.assertIn("No.", section)
        self.assertIn("](media/support-build-processor.png)", section)
        provenance = json.loads((TWIN / "media" / "provenance.json").read_text())
        self.assertIn("support-build-processor.png", provenance["images"])


if __name__ == "__main__":
    unittest.main()
