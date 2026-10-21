import ast
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

try:
    import numpy as np
except ImportError:          # the host may lack numpy; the outline checks do not need it
    np = None

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "twins/964-chassis/monocoque"


def load(name):
    return json.loads((SHELL / "derived" / name).read_text(encoding="utf-8"))


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

    def test_element_check_shows_s3_locking_and_s6_converging(self) -> None:
        r = load("element-check.json")
        self.assertEqual(r["grids"], [8, 16, 32])
        s3, s6 = r["ratio_to_reference"]["S3"], r["ratio_to_reference"]["S6"]
        self.assertTrue(all(x < 0.25 for x in s3))                           # S3 locks in bending
        self.assertTrue(all(a < b for a, b in zip(s6, s6[1:])))
        self.assertGreater(s6[0], 0.8)
        self.assertAlmostEqual(s6[-1], 1.0, delta=0.01)
        plate = r["plate_buckling"]                                            # the *BUCKLE path of shell_s6.run
        self.assertTrue(plate["repeats"])
        self.assertEqual(len(plate["ratio_to_theory"]), 2)
        for x in plate["ratio_to_theory"]:                                     # k = 4 and 6.25, within 5%
            self.assertAlmostEqual(x, 1.0, delta=0.05)

    @unittest.skipIf(np is None, "numpy not installed")
    def test_s6_lives_outside_the_pinned_s3_sources_and_is_restored(self) -> None:
        receipt = load("strength-audit-20261012.json")["source_sha256"]
        for name in ("source/torsion.py", "source/torsion_monocoque.py", "source/bending.py"):
            self.assertEqual(hashlib.sha256((SHELL / name).read_bytes()).hexdigest(), receipt[name], name)
        sys.path.insert(0, str(SHELL / "source"))
        try:
            import bending as bd
            import shell_s6 as s6
            import torsion as tr
            import torsion_monocoque as tm
        finally:
            sys.path.remove(str(SHELL / "source"))
        before = (tr.run, tr.load_shell, tm.solve_repeated.__defaults__, bd.solve_repeated.__defaults__)
        with s6.installed():
            self.assertIs(tr.run, s6.run)
            self.assertIs(tr.load_shell, s6.load_shell)
            self.assertIn(s6.REPEATS, tm.solve_repeated.__defaults__)
        self.assertEqual(before, (tr.run, tr.load_shell, tm.solve_repeated.__defaults__, bd.solve_repeated.__defaults__))
        p = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]])
        tri = np.array([[0, 1, 2], [1, 3, 2]])
        q, tri6 = s6.to_s6(p, tri)
        self.assertEqual(len(q), 4 + 5)                                       # five edges, one mid-side node each
        self.assertEqual(tri6.shape, (2, 6))
        self.assertEqual(sorted(s6.with_midside(np.array([0, 1]), tri6)), [0, 1, 4])   # the clamped edge's mid-side node

    def test_monocoque_torsion_rises_with_the_mesh_and_reproduces_the_open_shell(self) -> None:
        r = load("torsion-monocoque.json")
        self.assertIn("not of a vehicle", r["classification"])
        self.assertIn("prohibited_pending_engineering", r["classification"])
        self.assertIn("S6", r["mesh_note"])
        c = r["cases"]
        if np is not None:                                                  # shell_s6.py torsion on the published shell
            snap = np.load(SHELL / "derived/torsion-snapshot.npz")
            self.assertEqual(c["open shell, 0.8 mm steel"]["K"][-1], round(float(snap["K"])))
        for material in ("0.8 mm steel", "CFRP layup"):
            mono, shell = c[f"monocoque, {material}"]["K"], c[f"open shell, {material}"]["K"]
            self.assertEqual(len(mono), 3)
            self.assertTrue(all(a < b for a, b in zip(mono, mono[1:])), material)   # S6 rises with the mesh
            self.assertLess((mono[-1] - mono[-2]) / mono[-1], 0.12, material)       # ... still 8-10% on the last step:
            self.assertGreater((mono[-1] - mono[-2]) / mono[-1], 0.05, material)    # not converged, a lower bound
            self.assertTrue(all(m > 40 * o for m, o in zip(mono, shell)), material)
            self.assertTrue(all(a > b for a, b in zip(shell, shell[1:])), material)  # the open shell keeps softening
        cf, st = c["monocoque, CFRP layup"], c["monocoque, 0.8 mm steel"]
        self.assertLess(cf["mass_kg"], st["mass_kg"])
        self.assertTrue(all(1.4 < a / b < 1.65 for a, b in zip(cf["K_per_kg"], st["K_per_kg"])))

    def test_every_torsion_value_is_one_two_solves_agree_on(self) -> None:
        for name in ("torsion-monocoque.json", "torsion-rings.json"):
            r = json.loads((SHELL / "derived" / name).read_text(encoding="utf-8"))
            for case, row in r["cases"].items():
                for k, runs in zip(row["K"], row["K_repeats"]):
                    self.assertGreaterEqual(len(runs), 2, case)
                    self.assertGreaterEqual(sum(1 for x in runs if abs(x - k) <= 1), 2, case)

    def test_tube_result_hinges_on_the_bond_and_brackets_the_boxes(self) -> None:
        boxes = load("torsion-monocoque.json")["cases"]
        rings = load("torsion-rings.json")
        self.assertIn("prohibited_pending_engineering", rings["classification"])
        t, bare = rings["cases"]["rings, CFRP layup"], rings["cases"]["rings without tubes, CFRP layup"]
        self.assertTrue(all(b > 1.05 * a for a, b in zip(t["K"][1:], t["K"][2:])))  # strip bond: not converged in S6
        self.assertTrue(all(a < b for a, b in zip(t["K"], t["K"][1:])))
        for kt, k0 in zip(t["K"], bare["K"]):
            self.assertGreater(kt, 10 * k0)                                   # the tubes carry load
        sens = rings["bond_sensitivity"]["rows"]
        finest = sorted([(r["bond_radius_mm"], r["K"][-1]) for r in sens]
                        + [(rings["meshes"][-1]["tubes"]["bond_radius_mm"], t["K"][-1])])
        ks = [k for _, k in finest]
        self.assertEqual(ks, sorted(ks))                                      # wider bond, stiffer model
        box = boxes["monocoque, CFRP layup"]["K"][-1]
        self.assertTrue(ks[0] < box < ks[-1])                                 # the boxes sit inside the bracket

    def test_member_study_ranks_the_cabin_members_and_checks_the_pruning(self) -> None:
        r = load("torsion-members.json")
        self.assertTrue(r["complete"])
        self.assertIn("prohibited_pending_engineering", r["classification"])
        m = r["members"]
        for j in range(len(r["meshes"])):
            cabin = {n: v["K_cabin_lost_fraction"][j] for n, v in m.items()}
            ranked = sorted(cabin, key=lambda n: -cabin[n])
            self.assertEqual(sorted(ranked[:2]), ["door", "windscreen"])   # door rings and windscreen frame, in either order
            self.assertEqual(ranked[2], "quarter_window")
            self.assertLess(cabin["engine_lid"], 0.01)
            for n in ("windscreen", "quarter_window", "door"):
                self.assertGreater(cabin[n], 0.2, n)
        pr = r["pruned"]
        self.assertEqual(sorted(pr["removed"]), ["engine_lid", "front rails", "rear_window", "tunnel"])
        for j, frac in enumerate(pr["K_cabin_lost_fraction"]):             # together about what they cost one by one
            alone = sum(m[n]["K_cabin_lost_fraction"][j] for n in pr["removed"])
            self.assertLess(abs(frac - alone), 0.02)
            self.assertGreater(frac, 0.05)                                   # and the pruning is not free

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

    def test_shell_tubes_record_is_the_superseded_s3_run(self) -> None:
        # The S6 rerun does not fit a 6 GB container (killed at 210 sections,
        # 2026-10-16): the JSON is still the S3 run of 2026-10-11, and it must
        # not be ranked against the S6 skin boxes. Rerun in S6, update this test.
        sh = load("torsion-shell-tubes.json")
        self.assertIn("prohibited_pending_engineering", sh["classification"])
        self.assertTrue(sh["tubes"].startswith("S3 "))
        t = sh["cases"]["rings, CFRP layup"]
        self.assertTrue(all(b < 0.9 * a for a, b in zip(t["K"], t["K"][1:])))       # S3: not converged
        self.assertTrue(all(m["bonded"] > 0.95 * m["stations"] for m in sh["meshes"]))
        readme = (SHELL / "README.md").read_text(encoding="utf-8")
        self.assertIn("**These values are locking S3 values and were not redone in S6.**", readme)

    def test_bending_keeps_the_cabin_members_and_leaves_the_pruning_to_torsion(self) -> None:
        r = json.loads((SHELL / "derived/bending.json").read_text(encoding="utf-8"))
        self.assertIn("prohibited_pending_engineering", r["classification"])
        c = r["cases"]
        for row in c.values():                                                 # every value one two solves agree on
            for k, runs in zip(row["K"], row["K_repeats"]):
                self.assertGreaterEqual(sum(1 for x in runs if abs(x - k) <= 1), 2)
        for material in ("0.8 mm steel", "CFRP layup"):                       # S6: the boxes gain x5.7 to x17 on every mesh
            for key in ("K", "K_cabin"):
                ratio = r["ratios"][f"monocoque / open shell, {material}, {key}"]
                self.assertEqual(len(ratio), 3)
                self.assertTrue(all(5.0 < x < 20.0 for x in ratio), (material, key))
        tors = json.loads((SHELL / "derived/torsion-monocoque.json").read_text(encoding="utf-8"))["ratios"]
        self.assertGreater(tors["monocoque / open shell, CFRP"][-1], r["ratios"]["monocoque / open shell, CFRP layup, K"][-1])
        m = r["members"]
        self.assertTrue(m["complete"])
        lost = {n: row["K_cabin_lost_fraction"] for n, row in m["members"].items()}
        for mesh in range(2):                                                  # sills and door rings, in either order
            ranked = sorted(lost, key=lambda n: -lost[n][mesh])
            self.assertEqual(sorted(ranked[:2]), ["door", "sills"])
            self.assertGreater(lost["door"][mesh], 2 * lost["quarter_window"][mesh])   # the torsion leaders count less here
            self.assertGreater(lost["door"][mesh], 2 * lost["windscreen"][mesh])
        for name in m["pruned"]["removed"]:
            self.assertLess(max(lost[name]), 0.02, name)
        self.assertLess(max(m["pruned"]["K_cabin_lost_fraction"]), 0.03)       # torsion's pruning costs ~1% here
        torsion_pruned = json.loads((SHELL / "derived/torsion-members.json").read_text(encoding="utf-8"))["pruned"]
        self.assertGreater(min(torsion_pruned["K_cabin_lost_fraction"]), 5 * max(m["pruned"]["K_cabin_lost_fraction"]))


    @unittest.skipIf(np is None, "numpy not installed")
    def test_buckling_repeat_check_rejects_nonfinite_or_zero_factors_and_modes(self) -> None:
        sys.path.insert(0, str(SHELL / "source"))
        try:
            import buckling
        finally:
            sys.path.remove(str(SHELL / "source"))
        factors = np.arange(1.0, buckling.N_MODES + 1)
        modes = np.zeros((buckling.N_MODES, 3, 3))
        with mock.patch.object(buckling.s6, "run", return_value=(factors, modes)):
            actual, _ = buckling.buckle_repeated(None, None, None, None, None)
            np.testing.assert_array_equal(actual, factors)
        for bad in (float("nan"), float("inf"), -float("inf"), 0.0):
            invalid = factors.copy()
            invalid[0] = bad
            for first, second in ((invalid, factors), (factors, invalid)):
                with self.subTest(factor=bad), mock.patch.object(buckling.s6, "run",
                                                               side_effect=[(first, modes), (second, modes)]):
                    with self.assertRaises(SystemExit):
                        buckling.buckle_repeated(None, None, None, None, None)
        modes[0, 0, 0] = float("nan")
        with mock.patch.object(buckling.s6, "run", return_value=(factors, modes)):
            with self.assertRaises(SystemExit):
                buckling.buckle_repeated(None, None, None, None, None)

    def test_buckling_is_a_labelled_linear_screen(self) -> None:
        r = load("buckling.json")
        self.assertIn("prohibited_pending_engineering", r["classification"])
        self.assertIn("not of a vehicle", r["classification"])
        for case in ("torsion", "bending"):                                   # loads and core are assumptions
            self.assertTrue(r["service_loads"][case]["basis"].startswith("ASSUMED"), case)
        self.assertTrue(r["core"]["basis"].startswith("ASSUMED"))
        # The hand check uses a foam core; the model carries a honeycomb: the record must say so,
        # and the label must be the one buckling.py writes (no hand-edited drift).
        self.assertIn("NOT the 22.6 mm aramid honeycomb", r["core"]["basis"])
        self.assertIn("dimpling is not checked", r["core"]["basis"])
        self.assertEqual(r["layup_mm"]["core"], 22.6)
        tree = ast.parse((SHELL / "source/buckling.py").read_text(encoding="utf-8"))
        written = {t.id: n.value for n in tree.body if isinstance(n, ast.Assign) for t in n.targets
                   if isinstance(t, ast.Name)}
        self.assertEqual(r["core"]["basis"], ast.literal_eval(written["CORE_BASIS"]))
        self.assertIn("base state excluded", r["repeat_check"])
        sections = [m["sections"] for m in r["meshes"]]
        self.assertTrue(sections)
        for case, row in r["cases"].items():
            self.assertEqual([m["sections"] for m in row["meshes"]], sections, case)
            for mesh in row["meshes"]:
                factors = [m["factor"] for m in mesh["modes"]]
                self.assertEqual(len(factors), 16, case)
                self.assertGreater(factors[0], 0.0, case)                     # not the static base state (0.0)
                self.assertEqual(factors, sorted(factors), case)
                for m in mesh["modes"]:
                    self.assertAlmostEqual(m["critical"], m["factor"] * row["reference_load"], delta=0.01 * m["critical"] + 1)
                thin = next(m for m in mesh["modes"] if m["family"] in ("free skin", "box outer walls", "box inner walls"))
                self.assertAlmostEqual(mesh["first_thin_wall_critical_over_service"],
                                       thin["critical"] / r["service_loads"][case]["value"], delta=0.01)
                for key in ("sandwich_crimping_margin", "sandwich_wrinkling_margin"):
                    self.assertEqual(set(mesh[key]), {"mid_surface", "integration_points"})
        if np is not None:
            modes = np.load(SHELL / "derived/buckling-modes.npz")
            self.assertEqual(int(modes["sections"]), sections[-1])
            self.assertEqual(modes["mode_torsion_first"].shape, modes["points"].shape)

if __name__ == "__main__":
    unittest.main()
