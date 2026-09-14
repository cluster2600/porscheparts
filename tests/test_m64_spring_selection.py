#!/usr/bin/env python3
"""Contre-calculs du criblage de ressorts catalogue M64 (fiches publiées, pas qualification)."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "twins/m64-cylinder-head/source/valvetrain"
sys.path.insert(0, str(SRC))
spec = importlib.util.spec_from_file_location("m64_spring_selection", SRC / "spring_selection.py")
ss = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ss
spec.loader.exec_module(ss)
DATA = json.loads((SRC / "spring_candidates.json").read_text(encoding="utf-8"))
BY_ID = {c["id"]: c for c in DATA["candidates"]}


class CandidateFile(unittest.TestCase):
    def test_every_candidate_sourced_and_numeric(self):
        for c in DATA["candidates"]:
            self.assertTrue(c["url"].startswith("https://"), c["id"])
            for k in ("installed_height_mm", "seat_load_lbf", "coil_bind_mm"):
                self.assertIsInstance(c[k], (int, float), (c["id"], k))
            self.assertTrue(c.get("open_load_lbf") is not None or c.get("rate_published"), c["id"])
        self.assertFalse(DATA["ordered_or_contacted"])

    def test_no_wire_diameter_invented(self):
        self.assertTrue(all(c["wire_diameter_mm"] is None for c in DATA["candidates"]))

    def test_inch_conversions_bc1310(self):
        c = BY_ID["BC1310"]
        self.assertAlmostEqual(c["installed_height_mm"], 1.325 * 25.4, places=3)
        self.assertAlmostEqual(c["coil_bind_mm"], 0.730 * 25.4, places=3)
        self.assertAlmostEqual(c["open_lift_mm"], (1.325 - 0.925) * 25.4, places=3)


class Computation(unittest.TestCase):
    def test_rate_derived_by_hand(self):
        k, src = ss.rate_N_per_mm(BY_ID["GSC5092"])
        self.assertEqual(src, "derived_seat_open")
        self.assertAlmostEqual(k, (265 - 113) * 4.4482216152605 / 13.0, places=6)

    def test_supertech_rate_unit_is_lbf_per_mm(self):
        c = BY_ID["SPR-HM1007BE"]
        self.assertAlmostEqual((c["open_load_lbf"] - c["seat_load_lbf"]) / c["open_lift_mm"], c["rate_published"]["value"])

    def test_published_rate_fallback(self):
        k, src = ss.rate_N_per_mm(BY_ID["SPR-TS1015"])
        self.assertEqual(src, "published_unit_inferred")
        self.assertAlmostEqual(k, 12.1 * 4.4482216152605)

    def test_bind_and_shim(self):
        c = BY_ID["GSC5092"]
        sp = ss.spring_from_candidate(c, 11.5)
        self.assertAlmostEqual(sp["coil_bind_clearance_m"] * 1e3, 40.0 - 11.5 - 24.18)
        k, _ = ss.rate_N_per_mm(c)
        shim = ss.spring_from_candidate(c, 11.5, installed_mm=39.0)
        self.assertAlmostEqual(shim["preload_N"] - sp["preload_N"], k)

    def test_margin_scales_inverse_square(self):
        import valvetrain as vt
        p = vt.default_parameters()
        sp = ss.spring_from_candidate(BY_ID["GSC5092"], 11.5)
        law = vt.CamLaw.from_params(p["intake"]); m = vt.effective_mass(p["intake"], sp)
        m1 = vt.spring_margin(law, sp, m, 4000)["min_margin"]
        m2 = vt.spring_margin(law, sp, m, 8000)["min_margin"]
        self.assertAlmostEqual(m1 / m2, 4.0, places=6)

    def test_ranking_and_criteria(self):
        rows = [{"id": i, "supplier": "", "type": "", "intake": ss.evaluate(BY_ID[i], "intake", sdof_steps=3600),
                 "exhaust": ss.evaluate(BY_ID[i], "exhaust", sdof_steps=3600)} for i in ("BC1310", "GSC5092")]
        ranked = ss.rank(rows)
        self.assertEqual(ranked[0]["id"], "GSC5092")
        g = ranked[0]["intake"]
        self.assertGreaterEqual(g["margin_8000"], 1.25)
        self.assertGreaterEqual(g["bind_reserve_mm"], 1.0)
        self.assertEqual(g["checks"]["stress"], "not_computable")
        self.assertLess(ranked[1]["intake"]["margin_8000"], 1.25)

    def test_housing_od_rejects_large_spring(self):
        r = ss.evaluate(BY_ID["PAC-1276X"], "exhaust", sdof_steps=3600)
        self.assertIs(r["checks"]["housing_od"], False)
        self.assertFalse(r["passes_all_known"])

    def test_housing_params_flagged_assumed(self):
        self.assertTrue(all(v["status"] == "assumed" for v in ss.HOUSING.values()))


if __name__ == "__main__":
    unittest.main()
