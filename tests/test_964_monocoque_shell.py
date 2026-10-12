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
        if np is not None:                                                  # torsion.py on the published shell
            snap = np.load(SHELL / "derived/torsion-snapshot.npz")
            self.assertEqual(c["open shell, 0.8 mm steel"]["K"][-1], round(float(snap["K"])))
        for material in ("0.8 mm steel", "CFRP layup"):
            mono, shell = c[f"monocoque, {material}"]["K"], c[f"open shell, {material}"]["K"]
            self.assertEqual(len(mono), 3)
            self.assertLess((max(mono) - min(mono)) / max(mono), 0.15, material)   # the monocoque converges
            self.assertTrue(all(m > 5 * o for m, o in zip(mono, shell)), material)
            self.assertGreater(shell[0] / shell[-1], 2.0)                           # the open shell does not
        cf, st = c["monocoque, CFRP layup"], c["monocoque, 0.8 mm steel"]
        self.assertLess(cf["mass_kg"], st["mass_kg"])
        self.assertTrue(all(1.1 < a / b < 1.35 for a, b in zip(cf["K_per_kg"], st["K_per_kg"])))

    def test_every_torsion_value_is_one_two_solves_agree_on(self) -> None:
        for name in ("torsion-monocoque.json", "torsion-rings.json"):
            r = json.loads((SHELL / "derived" / name).read_text(encoding="utf-8"))
            for case, row in r["cases"].items():
                for k, runs in zip(row["K"], row["K_repeats"]):
                    self.assertGreaterEqual(len(runs), 3, case)
                    self.assertGreaterEqual(sum(1 for x in runs if abs(x - k) <= 1), 2, case)

    def test_tube_result_hinges_on_the_bond_and_brackets_the_boxes(self) -> None:
        boxes = json.loads((SHELL / "derived/torsion-monocoque.json").read_text(encoding="utf-8"))["cases"]
        rings = json.loads((SHELL / "derived/torsion-rings.json").read_text(encoding="utf-8"))
        self.assertIn("prohibited_pending_engineering", rings["classification"])
        t, bare = rings["cases"]["rings, CFRP layup"], rings["cases"]["rings without tubes, CFRP layup"]
        self.assertLess(abs(t["K"][2] - t["K"][1]) / t["K"][2], 0.01)          # strip bond: converged
        for kt, k0 in zip(t["K"], bare["K"]):
            self.assertGreater(kt, 5 * k0)                                    # the tubes carry load
        sens = rings["bond_sensitivity"]["rows"]
        finest = sorted([(r["bond_radius_mm"], r["K"][-1]) for r in sens]
                        + [(rings["meshes"][-1]["tubes"]["bond_radius_mm"], t["K"][-1])])
        ks = [k for _, k in finest]
        self.assertEqual(ks, sorted(ks))                                      # wider bond, stiffer model
        box = boxes["monocoque, CFRP layup"]["K"][-1]
        self.assertTrue(ks[0] < box < ks[-1])                                 # the boxes sit inside the bracket

    def test_member_study_ranks_the_cabin_members_and_checks_the_pruning(self) -> None:
        r = json.loads((SHELL / "derived/torsion-members.json").read_text(encoding="utf-8"))
        self.assertTrue(r["complete"])
        self.assertIn("prohibited_pending_engineering", r["classification"])
        m = r["members"]
        for j in range(len(r["meshes"])):
            cabin = {n: v["K_cabin_lost_fraction"][j] for n, v in m.items()}
            self.assertEqual(max(cabin, key=cabin.get), "door")              # the door rings carry the cabin
            self.assertLess(cabin["engine_lid"], 0.01)
            for n in ("windscreen", "quarter_window", "door"):
                self.assertGreater(cabin[n], 0.09, n)
        pr = r["pruned"]
        self.assertEqual(sorted(pr["removed"]), ["B-ring", "engine_lid", "front rails", "rear_window", "tunnel"])
        for j, frac in enumerate(pr["K_cabin_lost_fraction"]):             # together they cost more than one by one
            alone = sum(m[n]["K_cabin_lost_fraction"][j] for n in pr["removed"])
            self.assertGreater(frac, alone + 0.02)

    def test_layup_study_puts_plies_on_the_box_skin_and_f1_keeps_the_mass(self) -> None:
        r = json.loads((SHELL / "derived/torsion-layup.json").read_text(encoding="utf-8"))
        sens = r["sensitivity"]
        for j in range(len(r["meshes"])):
            cabin = {f: v["K_cabin_per_kg"][j] for f, v in sens.items()}
            self.assertEqual(max(cabin, key=cabin.get), "box outer walls")
            self.assertGreater(cabin["box outer walls"], 3.5 * max(cabin["floor"], cabin["bulkheads"]))
        f1 = r["F1"]
        for mesh, mass, gain in zip(r["meshes"], f1["mass_kg"], f1["K_cabin_gain_fraction"]):
            self.assertAlmostEqual(mass, mesh["mass_F0_kg"], delta=0.15)       # same mass as F0
            self.assertGreater(gain, 0.03)
        for mm in f1["mm"]:                                                     # every change within one step
            for fam, t in mm.items():
                self.assertLessEqual(abs(t - r["f0_mm"][fam]), r["step_mm"] + 1e-9, fam)

    def test_shell_tubes_leave_the_skin_open_and_trail_the_boxes_on_the_finest_mesh(self) -> None:
        sh = json.loads((SHELL / "derived/torsion-shell-tubes.json").read_text(encoding="utf-8"))
        self.assertIn("prohibited_pending_engineering", sh["classification"])
        boxes = json.loads((SHELL / "derived/torsion-monocoque.json").read_text(encoding="utf-8"))["cases"]["monocoque, CFRP layup"]
        t = sh["cases"]["rings, CFRP layup"]
        self.assertTrue(all(b < 0.9 * a for a, b in zip(t["K"], t["K"][1:])))       # not converged
        self.assertTrue(all(m["bonded"] > 0.95 * m["stations"] for m in sh["meshes"]))
        lead = (boxes["K"][-1] / boxes["mass_kg"]) / (t["K"][-1] / t["mass_kg"])
        self.assertGreater(lead, 1.1)                                             # boxes ahead on the finest mesh

    def test_bending_keeps_the_cabin_members_and_leaves_the_pruning_to_torsion(self) -> None:
        r = json.loads((SHELL / "derived/bending.json").read_text(encoding="utf-8"))
        self.assertIn("prohibited_pending_engineering", r["classification"])
        c = r["cases"]
        for row in c.values():                                                 # every value one two solves agree on
            for k, runs in zip(row["K"], row["K_repeats"]):
                self.assertGreaterEqual(sum(1 for x in runs if abs(x - k) <= 1), 2)
        for material in ("0.8 mm steel", "CFRP layup"):                       # the boxes gain about x4 on every mesh
            for key in ("K", "K_cabin"):
                ratio = r["ratios"][f"monocoque / open shell, {material}, {key}"]
                self.assertEqual(len(ratio), 3)
                self.assertTrue(all(3.0 < x < 5.0 for x in ratio), (material, key))
        tors = json.loads((SHELL / "derived/torsion-monocoque.json").read_text(encoding="utf-8"))["ratios"]
        self.assertGreater(tors["monocoque / open shell, CFRP"][-1], r["ratios"]["monocoque / open shell, CFRP layup, K"][-1])
        m = r["members"]
        self.assertTrue(m["complete"])
        lost = {n: row["K_cabin_lost_fraction"] for n, row in m["members"].items()}
        for mesh in range(2):                                                  # sills, then door rings
            ranked = sorted(lost, key=lambda n: -lost[n][mesh])
            self.assertEqual(ranked[:2], ["sills", "door"])
        for name in m["pruned"]["removed"]:
            self.assertLess(max(lost[name]), 0.02, name)
        self.assertLess(max(m["pruned"]["K_cabin_lost_fraction"]), 0.03)       # torsion's pruning costs ~1% here
        torsion_pruned = json.loads((SHELL / "derived/torsion-members.json").read_text(encoding="utf-8"))["pruned"]
        self.assertGreater(min(torsion_pruned["K_cabin_lost_fraction"]), 5 * max(m["pruned"]["K_cabin_lost_fraction"]))


if __name__ == "__main__":
    unittest.main()
