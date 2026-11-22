"""Contract tests for the assumed identity of the scanned 935 head and the check of its scale.

Records: twins/935-cylinder-head-cad-twin/params/specimen-identity.json (#692)
and params/scale-check.json (#693). They hold published values, each a
declared hypothesis with its source and quote, and fitted values of the twin.
These tests check the records' structure, that every published value carries
a source with a URL and a quote that contains it, that the fitted values are
the twin's own, that the scale arithmetic reproduces, and that nothing in them
claims a measurement or rescales the twin. They read committed JSON only.
"""

import json
import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins" / "935-cylinder-head-cad-twin"
PARAMS = TWIN / "params"
SCAN_SHA256 = "4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486"
ASSUMED = "assumed by owner decision 2026-11-22, not confirmed"
RELATIONS = {"same head", "same family", "other head"}
NUMBER = re.compile(r"\d+(?:\.\d+)?")


def load(name):
    return json.loads((PARAMS / name).read_text())


def numbers(text):
    """Numeric tokens of a value or quote, with decimal commas read as points."""
    flat = re.sub(r"(?<=\d),(?=\d{3}\b)", "", str(text))   # 2,808 -> 2808
    flat = re.sub(r"(?<=\d),(?=\d)", ".", flat)              # 89,6 -> 89.6
    return {float(t) for t in NUMBER.findall(flat)}


def by_id(items, key="id"):
    out = {i[key]: i for i in items}
    assert len(out) == len(items), "duplicate ids"
    return out


class IdentityRecordTests(unittest.TestCase):
    def setUp(self):
        self.rec = load("specimen-identity.json")
        self.sources = by_id(self.rec["sources"])
        self.values = by_id(self.rec["published_values"])

    def test_record_is_bound_to_the_scan_and_the_issues(self):
        self.assertEqual(self.rec["schema"], "935-cad-twin-specimen-identity/1")
        self.assertEqual(self.rec["scan"]["sha256"], SCAN_SHA256)
        self.assertEqual(self.rec["issues"], ["#692", "#693"])
        self.assertIn("owner instruction", self.rec["scan"]["unit"])
        self.assertIn("never a measurement", self.rec["rule"])

    def test_every_source_has_a_url_a_date_and_terms(self):
        for sid, src in self.sources.items():
            self.assertTrue(src["url"].startswith("https://"), sid)
            self.assertRegex(src["accessed"], r"^2026-11-\d\d", sid)
            for key in ("title", "publisher", "kind", "applies_to", "terms"):
                self.assertTrue(src.get(key), f"{sid} lacks {key}")
            if "repo_path" in src:
                self.assertTrue((ROOT / src["repo_path"]).exists(), sid)
            if "private_copy_sha256" in src:
                self.assertRegex(src["private_copy_sha256"], r"^[0-9a-f]{64}$", sid)

    def test_every_published_value_has_a_source_and_a_quote_that_holds_it(self):
        for vid, pv in self.values.items():
            self.assertIn(pv["source"], self.sources, vid)
            for other in pv.get("also_in", []):
                self.assertIn(other, self.sources, vid)
            self.assertTrue(pv["quote"].strip(), vid)
            self.assertIn("re-read", pv["second_reading"], vid)
            self.assertTrue(pv["relation_to_specimen"], vid)
            quoted = numbers(pv["quote"]) | numbers(pv.get("quote_second_source", ""))
            self.assertLessEqual(numbers(pv["value"]), quoted, f"{vid}: a number of the value is not in its quote")

    def test_no_published_value_is_called_a_measurement_of_the_specimen(self):
        for vid, pv in self.values.items():
            self.assertNotIn("measured", json.dumps(pv).lower(), vid)

    def test_identity_fields_are_sourced_or_null_with_a_blocker(self):
        fields = by_id(self.rec["identity"], key="field")
        for name in ("maker_of_the_head", "process", "period_part_or_new_casting",
                     "program_and_bore_family", "part_number_or_casting_mark", "engine_type_number"):
            self.assertIn(name, fields)
        for name, field in fields.items():
            self.assertTrue(field["status"], name)
            if field["value"] is None:
                self.assertTrue(field.get("blocker"), f"{name} is null without a blocker")
            else:
                self.assertTrue(field.get("evidence"), f"{name} has a value without evidence")
            for ref in field.get("evidence", []):
                self.assertIn(ref, self.values, name)

    def test_discriminating_features_point_at_twin_records_and_published_values(self):
        for feat in self.rec["discriminating_features"]:
            for ref in feat["published"]:
                self.assertIn(ref, self.values, feat["id"])
            if feat["twin_value"] is None:
                self.assertTrue(feat.get("blocker"), feat["id"])
                continue
            for path in re.findall(r"params/[\w.-]+\.json", feat["twin_record"]):
                self.assertTrue((TWIN / path).exists(), path)

    def test_candidates_cite_existing_values_and_one_is_assumed(self):
        cands = by_id(self.rec["candidates"])
        self.assertEqual(set(cands), {"A", "B", "C", "D"})
        refs = set(self.values) | {f["id"] for f in self.rec["discriminating_features"]}
        for cid, cand in cands.items():
            self.assertTrue(cand["evidence_for"] and cand["evidence_against"], cid)
            for line in cand["evidence_for"] + cand["evidence_against"]:
                for ref in re.findall(r"\b(?:pv|f)-[\w.-]*\w", line):
                    self.assertIn(ref, refs, f"{cid}: {ref}")
        self.assertIn("assumed", cands["A"]["verdict"])
        self.assertIn("open", cands["B"]["verdict"])

    def test_assumed_identity_is_declared_in_the_hypotheses_register(self):
        reg = json.loads((TWIN / "hypotheses.json").read_text())
        items = by_id(reg["items"])
        assumed = self.rec["assumed_identity"]
        self.assertEqual(assumed["status"], ASSUMED)
        self.assertEqual(assumed["hypotheses"], ["H16-specimen-identity", "H17-bore-family"])
        for hid in assumed["hypotheses"]:
            self.assertIn(hid, items)
            self.assertEqual(items[hid]["status"], ASSUMED)
            self.assertIn("params/", items[hid]["how"])
        # Appended, not renumbered: H01 to H15 still lead the register in order,
        # and the identity hypotheses come after them.
        ids = [i["id"] for i in reg["items"]]
        self.assertEqual([i[:3] for i in ids[:15]], [f"H{n:02d}" for n in range(1, 16)])
        for hid in assumed["hypotheses"]:
            self.assertGreaterEqual(ids.index(hid), 15)

    def test_every_compared_figure_is_marked_same_head_same_family_or_other_head(self):
        rows = self.rec["published_figures_already_compared"]
        self.assertTrue(rows)
        for row in rows:
            self.assertIn(row["relation"], RELATIONS, row)
            path = row["record"]
            self.assertTrue((TWIN / path).exists() or (ROOT / path).exists(), path)
        self.assertNotIn("same head", {r["relation"] for r in rows})
        self.assertTrue(self.rec["same_head_figures"].startswith("none"))

    def test_questions_for_the_reviewer_are_numbered_and_cover_scale_and_identity(self):
        qs = by_id(self.rec["questions_for_reviewer"])
        self.assertEqual(list(qs), [f"Q{n}" for n in range(1, len(qs) + 1)])
        settles = " ".join(q["settles"] for q in qs.values())
        for target in ("H16", "H17", "#693", "H09"):
            self.assertIn(target, settles)

    def test_stud_pattern_quoted_in_the_record_reproduces_from_the_fits(self):
        fits = {r["id"]: r["fit"] for r in load("feature-fits.json")["regions"]}
        pts = {}
        for rid, fit in fits.items():
            if rid.startswith("stud_") and rid.endswith("_passage"):
                p, a = fit["axis_point"], fit["axis_direction"]
                t = (20.0 - p[2]) / a[2]
                pts[rid] = (p[0] + t * a[0], p[1] + t * a[1])
        self.assertEqual(len(pts), 4)
        d = sorted(math.dist(a, b) for i, a in enumerate(pts.values()) for b in list(pts.values())[i + 1:])
        sides, diagonals = d[:4], d[4:]
        self.assertTrue(all(85.6 <= s <= 85.85 for s in sides), sides)
        self.assertTrue(all(121.15 <= g <= 121.4 for g in diagonals), diagonals)
        centre = (sum(p[0] for p in pts.values()) / 4, sum(p[1] for p in pts.values()) / 4)
        recess = fits["deck_register_recess"]["axis_point"]
        self.assertLess(math.dist(centre, recess[:2]), 0.15)


class ScaleCheckTests(unittest.TestCase):
    def setUp(self):
        self.rec = load("scale-check.json")
        self.checks = by_id(self.rec["checks"])
        self.values = by_id(load("specimen-identity.json")["published_values"])

    def test_the_twin_is_not_rescaled_and_the_instruction_stands(self):
        self.assertFalse(self.rec["twin_rescaled"])
        self.assertIn("not a measurement", self.rec["claims"])
        self.assertIn("kept", self.rec["owner_instruction"])
        self.assertIn("1 OBJ unit = 1 mm", load("frame.json")["units"])
        self.assertIn("1 OBJ unit = 1 mm", load("feature-fits.json")["units"])

    def test_fitted_values_are_the_twins_own(self):
        sheet = {f["id"]: f for f in load("reference-sheet.json")["features"]}
        fits = {r["id"]: r["fit"] for r in load("feature-fits.json")["regions"]}
        refits = {r["id"]: r["fit"] for r in load("feature-refits.json")["regions"]}
        rings = {r["name"]: r for r in load("frame.json")["rings"]}
        c = self.checks
        self.assertEqual(c["plug-thread-x-plus"]["twin"]["value_mm"], sheet["plug_x_plus_thread_bore"]["mid_diameter_mm"])
        self.assertEqual(c["plug-thread-x-plus"]["twin"]["radius_sigma_mm"], refits["plug_x_plus_thread_bore"]["radius_sigma_mm"])
        radii = sheet["plug_x_plus_thread_bore"]["radii_mm"]
        self.assertEqual(c["plug-thread-x-plus"]["twin"]["diameter_along_bore_mm"], [round(2 * r, 4) for r in radii])
        self.assertEqual(c["plug-thread-x-minus"]["twin"]["value_mm"], fits["plug_x_minus_thread_bore"]["diameter_mm"])
        self.assertEqual(c["chamber-shoulder-bore"]["twin"]["value_mm"], round(rings["chamber_shoulder"]["diameter_mm"], 4))
        self.assertEqual(c["guide-bore-8mm-stem"]["twin"]["value_mm"], fits["valve_y_minus_guide_bore"]["diameter_mm"])
        self.assertEqual(c["guide-bore-8mm-stem"]["twin"]["refit_value_mm"], refits["valve_y_minus_guide_bore"]["diameter_mm"])
        shoulder = rings["chamber_shoulder"]
        sigma = 2 * shoulder["radial_residual"]["rms_mm"] / math.sqrt(shoulder["radial_residual"]["n"])
        self.assertAlmostEqual(c["chamber-shoulder-bore"]["twin"]["diameter_sigma_mm"], sigma, places=4)

    def test_confirmation_states_match_the_twins_standing(self):
        standing = {r["id"]: r for r in load("feature-confirmation.json")["rows"]}
        self.assertEqual(standing["plug_x_plus_thread_bore"]["status"], "confirmed")
        self.assertNotEqual(standing["plug_x_minus_thread_bore"]["status"], "confirmed")
        self.assertNotEqual(standing["valve_y_minus_guide_bore"]["status"], "confirmed")
        self.assertIn(f"{100 * standing['plug_x_plus_thread_bore']['refit_check_share']:.2f}%",
                      self.checks["plug-thread-x-plus"]["twin"]["confirmed"])

    def test_published_inputs_are_the_identity_records_values(self):
        m12 = self.values["pv-iso-28741-m12"]
        self.assertEqual(numbers(m12["value"]), {12.0, 10.912, 10.647, 1.25})
        pub = self.checks["plug-thread-x-plus"]["published"]
        self.assertEqual(pub["major_diameter_mm"], 12.0)
        self.assertEqual(sorted(pub["minor_diameter_6H_mm"]), [10.647, 10.912])
        self.assertEqual(pub["pitch_mm"], 1.25)
        bores = self.checks["chamber-shoulder-bore"]["published"]["bores_mm"]
        quoted = set()
        for vid in self.checks["chamber-shoulder-bore"]["published"]["values"]:
            quoted |= numbers(self.values[vid]["value"])
        self.assertLessEqual(set(bores), quoted)
        for check in self.rec["checks"]:
            for vid in check["published"].get("values", []):
                self.assertIn(vid, self.values, check["id"])

    def test_scale_intervals_reproduce(self):
        for check in self.rec["checks"]:
            fitted = check["twin"]["value_mm"]
            iv = check["interval"]
            if "published_low_mm" in iv:
                self.assertAlmostEqual(iv["s_low"], iv["published_low_mm"] / fitted, places=4)
                self.assertAlmostEqual(iv["s_high"], iv["published_high_mm"] / fitted, places=4)
            holds = iv["s_low"] <= 1.0 <= iv["s_high"] + 5e-5
            self.assertEqual(check["unit_holds_within_uncertainty"], holds, check["id"])
        bore = self.checks["chamber-shoulder-bore"]
        lo, hi = bore["published"]["bores_mm"][0], bore["published"]["bores_mm"][-1]
        self.assertAlmostEqual(bore["interval"]["s_low"], lo / bore["twin"]["value_mm"], places=4)
        self.assertAlmostEqual(bore["interval"]["s_high"], hi / bore["twin"]["value_mm"], places=4)
        guide = self.checks["guide-bore-8mm-stem"]
        g_lo, g_hi = guide["published"]["guide_bore_mm"]
        self.assertAlmostEqual(guide["interval"]["s_low"], g_lo / guide["twin"]["refit_value_mm"], places=4)
        self.assertAlmostEqual(guide["interval"]["s_high"], g_hi / guide["twin"]["value_mm"], places=4)
        self.assertAlmostEqual(guide["lower_bound_only"]["s_at_least"], g_lo / guide["twin"]["refit_value_mm"], places=4)

    def test_thread_model_follows_the_iso_basic_profile(self):
        check = self.checks["plug-thread-x-plus"]
        d, p = 12.0, 1.25
        self.assertAlmostEqual(d - 1.082532 * p, 10.647, places=3)   # basic minor = 6H lower limit
        # Flanks at 60 degrees over 5/8 H: each flank runs 5P/16 axially, the flats P/4 and P/8.
        h = math.sqrt(3) / 2 * p
        flank_run = 5 / 8 * h * math.tan(math.radians(30))
        self.assertAlmostEqual(flank_run, 5 * p / 16, places=9)
        weight_of_root = (p / 8 + flank_run) / p                     # share of D in the axial mean
        self.assertAlmostEqual(weight_of_root, 7 / 16, places=9)
        means = [d1 + weight_of_root * (d - d1) for d1 in check["published"]["minor_diameter_6H_mm"]]
        self.assertEqual([round(m, 4) for m in means], check["central_estimate"]["published_mean_mm"])
        fitted = check["twin"]["value_mm"]
        self.assertEqual([round(m / fitted, 4) for m in means], check["central_estimate"]["s"])
        alt = check["alternative_thread"]
        self.assertAlmostEqual(alt["s_low"], 12.647 / fitted, places=4)
        self.assertAlmostEqual(alt["s_high"], 14.0 / fitted, places=4)
        self.assertGreater(alt["s_low"], check["interval"]["s_high"])  # M12 and M14 do not overlap

    def test_class_limit_bore_arithmetic(self):
        cl = self.checks["chamber-shoulder-bore"]["published"]["class_limit"]
        volume = 4000 / 1.4
        self.assertAlmostEqual(cl["largest_displacement_cm3"], volume, places=2)
        bore = math.sqrt(volume * 1000 / (6 * math.pi / 4 * 70.4))
        self.assertAlmostEqual(cl["largest_bore_mm"], bore, places=4)
        for cc, b in ((2856, 92.78), (2857, 92.80), (2808, 92.0), (2832, 92.4)):
            self.assertAlmostEqual(math.sqrt(cc * 1000 / (6 * math.pi / 4 * 70.4)), b, delta=0.01)

    def test_only_independent_checks_vote_and_the_primary_one_holds(self):
        primary = [c for c in self.rec["checks"] if c["role"] == "primary"]
        self.assertEqual([c["id"] for c in primary], ["plug-thread-x-plus"])
        self.assertTrue(primary[0]["independent_of_H17"])
        self.assertTrue(primary[0]["unit_holds_within_uncertainty"])
        self.assertFalse(self.checks["chamber-shoulder-bore"]["independent_of_H17"])
        self.assertIn("not counted", self.checks["chamber-shoulder-bore"]["role"])
        self.assertFalse(self.checks["guide-bore-8mm-stem"]["unit_holds_within_uncertainty"])
        self.assertIn("open", self.rec["verdict"]["status"])

    def test_unit_alternatives_are_far_outside_every_interval(self):
        top = max(c["interval"]["s_high"] for c in self.rec["checks"])
        bottom = min(c["interval"]["s_low"] for c in self.rec["checks"])
        for factor in self.rec["unit_alternatives"]["factors"].values():
            self.assertTrue(factor > 5 * top and 1 / factor < bottom / 5)


class ReadmeAndNoteTests(unittest.TestCase):
    def test_readme_section_links_both_records_and_the_note(self):
        text = (TWIN / "README.md").read_text()
        self.assertIn("(params/specimen-identity.json)", text)
        self.assertIn("(params/scale-check.json)", text)
        self.assertIn("docs/research/935-identity-scale-20261122.md", text)

    def test_research_note_lists_the_sources_it_rejected(self):
        note = (ROOT / "docs" / "research" / "935-identity-scale-20261122.md").read_text()
        self.assertIn("## Sources rejected, and why", note)
        self.assertIn("## Queries", note)
        self.assertIn("Nobody was contacted", note)


if __name__ == "__main__":
    unittest.main()
