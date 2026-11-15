"""The kinematic draping tool: its construction on small nets, then the committed receipts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "kinematic_draping.py"
BENCH = ROOT / "benchmarks" / "kinematic-draping"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(importlib.util.find_spec("numpy") is not None, "numpy absent")
class KinematicDrapingTests(unittest.TestCase):
    def setUp(self):
        import numpy as np

        spec = importlib.util.spec_from_file_location("kinematic_draping_under_test", SCRIPT)
        self.kd = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.kd
        spec.loader.exec_module(self.kd)
        self.np = np

    def test_a_plane_takes_the_square_grid_at_any_warp_angle(self):
        np, kd = self.np, self.kd
        plane = kd.height_field(lambda x, y: 0.0, "plane")
        nodes = kd.drape(plane, np.zeros(3), np.array([math.cos(0.7), math.sin(0.7), 0.0]), 3.0, 4, 3)
        self.assertFalse(np.isnan(nodes).any())
        self.assertAlmostEqual(float(np.linalg.norm(nodes[8, 6] - nodes[4, 3])), 3.0 * 5.0, places=9)   # 4 along warp, 3 along weft
        self.assertLess(float(np.abs(kd.shear_angles(nodes)).max()), 1e-9)

    def test_a_developable_mould_needs_no_shear_and_yarns_keep_their_length(self):
        np, kd = self.np, self.kd
        surface = kd.tunnel(100.0, ground=False)
        for angle in (0.0, math.radians(30.0)):
            nodes = kd.drape(surface, np.array([0.0, 0.0, 100.0]), np.array([math.cos(angle), math.sin(angle), 0.0]), 5.0, 6, 6)
            self.assertFalse(np.isnan(nodes).any())
            self.assertLess(float(np.degrees(np.abs(kd.shear_angles(nodes)).max())), 0.02)
            report = kd.summary(surface, nodes, 5.0)
            self.assertLess(report["largest_error_of_a_yarn_length"], 1e-9)
            self.assertLess(report["largest_distance_of_a_crossing_from_the_mould"], 1e-9)
            self.assertAlmostEqual(report["area_on_the_mould"] / report["flat_pattern_area"], 1.0, places=6)

    def test_a_sphere_follows_the_continuous_net_and_closes_along_the_bias(self):
        np, kd = self.np, self.kd
        n, spacing, radius = 10, 4.0, 100.0
        nodes = kd.drape(kd.sphere(radius), np.array([0.0, 0.0, radius]), np.array([1.0, 0.0, 0.0]), spacing, n, n)
        gamma = kd.shear_angles(nodes)[n:, n:]
        centre = (np.arange(n) + 0.5) * spacing
        reference = kd.sphere_reference(np.outer(centre, centre) / radius ** 2)
        self.assertLess(float(np.degrees(np.abs(gamma - reference)).max()), 0.01)
        # no shear along the two generators, the most on the bias, and more of it further out
        self.assertLess(float(np.degrees(abs(gamma[0, 0]))), 0.1)
        self.assertGreater(gamma[n - 1, n - 1], gamma[n - 2, n - 2])
        self.assertGreater(gamma[n - 1, n - 1], gamma[n - 1, 0])
        # the sheared net covers less mould than its flat pattern: the yarns pack closer
        report = kd.summary(kd.sphere(radius), nodes, spacing)
        self.assertLess(report["area_on_the_mould"], report["flat_pattern_area"])
        self.assertGreater(report["largest_fibre_packing_ratio"], 1.0)

    def test_the_reference_is_its_series_near_zero_and_closes_at_a_finite_distance(self):
        np, kd = self.np, self.kd
        t = np.array([0.01, 0.1, 0.3])
        self.assertLess(float(np.abs(kd.sphere_reference(t) - (t - t ** 3 / 18.0)).max()), 2e-5)
        # the net on a sphere cannot go on for ever: the yarns become parallel at K u v = 1.862
        grid = np.linspace(0.5, 2.5, 2001)
        phi = kd.sphere_reference(grid)
        closed = float(grid[np.argmax(phi >= math.pi / 2)])
        self.assertAlmostEqual(closed, 1.862, delta=0.003)
        self.assertAlmostEqual(float(grid[np.argmax(phi >= math.pi / 4)]), 0.815, delta=0.003)
        self.assertTrue(bool(np.all(np.diff(phi[grid < closed]) > 0)))

    def test_a_net_stops_where_the_mould_ends_instead_of_inventing_crossings(self):
        np, kd = self.np, self.kd
        nodes = kd.drape(kd.tunnel(10.0, ground=False), np.array([0.0, 0.0, 10.0]), np.array([1.0, 0.0, 0.0]), 2.0, 3, 12)
        placed = np.isfinite(nodes).all(axis=2)
        self.assertTrue(placed[:, 12].all())                       # the yarn along the crown
        self.assertFalse(placed[:, 0].any())                       # 24 along the arc: past the foot at 15.7
        self.assertLess(float(np.abs(nodes[placed][:, 1]).max()), 10.0)

    def test_a_fillet_keeps_the_slope_continuous(self):
        kd = self.kd
        h = kd._filleted_arc(0.3, 0.05)
        foot = math.sqrt(0.3 ** 2 + 2 * 0.3 * 0.05)
        touch = foot * 0.3 / 0.35
        for r in (touch, foot):
            left, right = (h(r) - h(r - 1e-6)) / 1e-6, (h(r + 1e-6) - h(r)) / 1e-6
            self.assertLess(abs(left - right), 0.01 * max(1.0, abs(left)))
        self.assertEqual(h(foot + 0.1), 0.0)
        self.assertAlmostEqual(h(0.0), 0.3)

    def test_receipts_match_the_script_and_their_cases(self):
        witness = json.loads((BENCH / "results-20261115.json").read_text())
        self.assertTrue(witness["passed"])
        self.assertEqual(witness["script_sha256"], sha(SCRIPT))
        self.assertTrue(all(case["passed"] for case in witness["cases"]))
        errors = witness["sphere_error_deg_by_spacing"]
        self.assertLess(errors["2"], 0.5 * errors["4"])
        for name in ("dome-on-a-plane", "tunnel-on-a-plane"):
            report = json.loads((BENCH / f"{name}.json").read_text())
            self.assertEqual(report["script_sha256"], sha(SCRIPT), name)
            self.assertEqual(report["case_sha256"], sha(BENCH / "cases" / f"{name}.json"), name)
            self.assertEqual(report["crossings_placed"], report["crossings_asked"], name)
            shares = [report["share_of_cells_above_deg"][key] for key in ("20", "30", "40", "50")]
            self.assertEqual(shares, sorted(shares, reverse=True), name)
            self.assertIn("not a verdict", report["claims"])
        dome = json.loads((BENCH / "dome-on-a-plane.json").read_text())
        tunnel = json.loads((BENCH / "tunnel-on-a-plane.json").read_text())
        self.assertGreater(dome["shear_deg"]["largest"], 40.0)     # a double curvature costs shear
        self.assertLess(tunnel["shear_deg"]["largest"], 0.1)       # a developable mould costs none


if __name__ == "__main__":
    unittest.main()
