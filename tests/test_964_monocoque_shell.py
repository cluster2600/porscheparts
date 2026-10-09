import json
import unittest
from pathlib import Path

try:
    import numpy as np
except ImportError:          # the host may lack numpy; the outline checks do not need it
    np = None

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "twins/964-chassis/monocoque"


class MonocoqueShellTests(unittest.TestCase):
    def test_traced_outline_matches_published_dimensions(self) -> None:
        p = json.loads((SHELL / "data/profiles-50-05a.json").read_text(encoding="utf-8"))
        d = [q[0] for q in p["side_top"]]
        z = [q[1] for q in p["side_top"]]
        self.assertAlmostEqual(max(z), 1310.0, delta=1.0)        # anchored roof height
        self.assertLess(min(d), -700.0)                           # reaches the P1 plane (-722)
        self.assertGreater(max(d), 3030.0)                        # reaches the P16 plane (3034.5)
        mid = [w for x, w in p["plan_half_width"] if 800 < x < 1500]
        self.assertTrue(mid and all(700 < w < 900 for w in mid)) # sills, at body width
        for name in ("door_aperture", "quarter_window", "rear_wheel_house"):
            self.assertGreater(len(p["openings"][name]), 20)

    @unittest.skipIf(np is None, "numpy not installed")
    def test_torsion_snapshot_is_consistent(self) -> None:
        t = np.load(SHELL / "derived/torsion-snapshot.npz")
        self.assertEqual(len(t["points"]), len(t["von_mises"]))
        self.assertLess(int(t["triangles"].max()), len(t["points"]))
        self.assertGreater(float(t["K"]), 0.0)
        self.assertAlmostEqual(float(t["thickness_mm"]), 0.8)

    def test_monocoque_torsion_is_stable_and_reproduces_the_open_shell(self) -> None:
        r = json.loads((SHELL / "derived/torsion-monocoque.json").read_text(encoding="utf-8"))
        self.assertIn("not of a vehicle", r["classification"])
        self.assertIn("prohibited_pending_engineering", r["classification"])
        c = r["cases"]
        self.assertEqual(c["open shell, 0.8 mm steel"]["K"][-1], 2261)   # torsion.py on the published shell
        for material in ("0.8 mm steel", "CFRP layup"):
            mono, shell = c[f"monocoque, {material}"]["K"], c[f"open shell, {material}"]["K"]
            self.assertEqual(len(mono), 3)
            self.assertLess((max(mono) - min(mono)) / max(mono), 0.15, material)   # the monocoque converges
            self.assertTrue(all(m > 5 * o for m, o in zip(mono, shell)), material)
            self.assertGreater(shell[0] / shell[-1], 2.0)                           # the open shell does not
        cf, st = c["monocoque, CFRP layup"], c["monocoque, 0.8 mm steel"]
        self.assertLess(cf["mass_kg"], st["mass_kg"])
        self.assertTrue(all(1.1 < a / b < 1.35 for a, b in zip(cf["K_per_kg"], st["K_per_kg"])))

    def test_every_torsion_value_is_a_median_of_three_solves(self) -> None:
        for name in ("torsion-monocoque.json", "torsion-rings.json"):
            r = json.loads((SHELL / "derived" / name).read_text(encoding="utf-8"))
            for case, row in r["cases"].items():
                for k, runs in zip(row["K"], row["K_repeats"]):
                    self.assertEqual(len(runs), 3, case)
                    self.assertEqual(k, sorted(runs)[1], case)

    def test_skin_boxes_beat_tubes_per_kilogram_at_every_mesh(self) -> None:
        boxes = json.loads((SHELL / "derived/torsion-monocoque.json").read_text(encoding="utf-8"))["cases"]
        rings = json.loads((SHELL / "derived/torsion-rings.json").read_text(encoding="utf-8"))
        self.assertIn("prohibited_pending_engineering", rings["classification"])
        b, t, bare = boxes["monocoque, CFRP layup"], rings["cases"]["rings, CFRP layup"], rings["cases"]["rings without tubes, CFRP layup"]
        for kb, kt, k0 in zip(b["K"], t["K"], bare["K"]):
            self.assertGreater(kb / b["mass_kg"], 1.3 * kt / t["mass_kg"])    # x 1.4 to x 1.9 in the docs
            self.assertGreater(kt, 2.5 * k0)                                  # the tubes carry load
        self.assertTrue(all(m["tubes"]["links"] > 500 for m in rings["meshes"]))


if __name__ == "__main__":
    unittest.main()
