"""Contract tests for the 935 head CAD twin (twins/935-cylinder-head-cad-twin).

They run on synthetic geometry and the committed scalar parameters only; the
private scan never reaches CI.
"""

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins" / "935-cylinder-head-cad-twin"
SOURCE = TWIN / "source"
SCAN_SHA256 = "4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486"


def has(*mods):
    return all(importlib.util.find_spec(m) is not None for m in mods)


class RegisterTests(unittest.TestCase):
    def test_hypotheses_register_is_complete(self):
        reg = json.loads((TWIN / "hypotheses.json").read_text())
        ids = [i["id"] for i in reg["items"]]
        self.assertEqual(len(ids), len(set(ids)))
        for item in reg["items"]:
            for key in ("region", "status", "how", "colour", "retire_with"):
                self.assertTrue(item.get(key), f"{item['id']} lacks {key}")
            self.assertIn(item["colour"], reg["display_colours"])
            self.assertNotIn("measured", item["status"])

    def test_frame_is_bound_to_the_scan_and_orthonormal(self):
        frame = json.loads((TWIN / "params" / "frame.json").read_text())
        self.assertEqual(frame["scan_sha256"], SCAN_SHA256)
        r = frame["rotation_scan_to_twin_rows"]
        for i in range(3):
            for j in range(3):
                dot = sum(r[i][k] * r[j][k] for k in range(3))
                self.assertAlmostEqual(dot, 1.0 if i == j else 0.0, places=6)
        det = (r[0][0] * (r[1][1] * r[2][2] - r[1][2] * r[2][1])
               - r[0][1] * (r[1][0] * r[2][2] - r[1][2] * r[2][0])
               + r[0][2] * (r[1][0] * r[2][1] - r[1][1] * r[2][0]))
        self.assertAlmostEqual(det, 1.0, places=6)
        self.assertEqual(frame["levels_twin"]["deck_z"], 0.0)

    def test_scorecards_report_both_directions_and_pass_the_oracle(self):
        cards = sorted((TWIN / "params").glob("scorecard-*.json"))
        self.assertTrue(cards, "no scorecard committed")
        for card in cards:
            s = json.loads(card.read_text())
            self.assertEqual(s["scan_sha256"], SCAN_SHA256)
            self.assertIn("scan_to_twin", s)
            self.assertIn("twin_to_scan", s)
            self.assertTrue(s["oracle_check"]["passed"], card.name)
            self.assertIn("unobserved", s["limits"])

    def test_no_geometry_bearing_files_are_tracked(self):
        banned = {".obj", ".stl", ".ply", ".step", ".stp", ".3mf", ".usdc", ".usda", ".npz", ".npy", ".frd"}
        for p in TWIN.rglob("*"):
            self.assertNotIn(p.suffix.lower(), banned, f"geometry file in Git: {p}")


@unittest.skipUnless(has("numpy"), "numpy absent")
class FitTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(SOURCE))
        import twin_common

        self.tc = twin_common
        import numpy as np

        self.np = np

    def test_circle_fit_recovers_a_noisy_circle(self):
        np = self.np
        rng = np.random.default_rng(1)
        t = rng.uniform(0, 2 * np.pi, 2000)
        xy = np.column_stack((3 + 56.94 * np.cos(t), -2 + 56.94 * np.sin(t))) + rng.normal(0, 0.03, (2000, 2))
        c, r, res = self.tc.fit_circle_2d(xy)
        self.assertAlmostEqual(r, 56.94, delta=0.005)
        self.assertAlmostEqual(c[0], 3, delta=0.005)
        self.assertLess(np.sqrt(np.mean(res ** 2)), 0.04)

    def test_plane_fit_recovers_normal(self):
        np = self.np
        rng = np.random.default_rng(2)
        p = rng.uniform(-50, 50, (5000, 3))
        n = np.array([0.1, -0.8, -0.6])
        n /= np.linalg.norm(n)
        p -= np.outer(p @ n - 7.0, n)
        nrm, pt, res = self.tc.fit_plane(p, np.ones(len(p)))
        self.assertGreater(abs(nrm @ n), 1 - 1e-9)
        self.assertLess(np.abs(res).max(), 1e-9)


@unittest.skipUnless(has("numpy", "shapely", "skimage"), "numpy/shapely/scikit-image absent")
class BandTests(unittest.TestCase):
    def test_slice_region_keeps_holes_and_area(self):
        import numpy as np

        sys.path.insert(0, str(SOURCE))
        import build_brep

        h = 0.25
        x = np.arange(-30, 30, h)
        X, Y = np.meshgrid(x, x, indexing="ij")
        r = np.hypot(X, Y)
        w = ((r < 20) & (r > 8)).astype(np.float32)
        grid = {"pitch_mm": h, "x0": float(x[0]), "y0": float(x[0])}
        region = build_brep.slice_region(w, grid)
        expected = np.pi * (20 ** 2 - 8 ** 2)
        self.assertAlmostEqual(region.area / expected, 1.0, delta=0.01)
        self.assertEqual(len(region.interiors), 1)

    def test_band_merge_tolerance(self):
        sys.path.insert(0, str(SOURCE))
        import build_brep
        from shapely.geometry import Point

        a = Point(0, 0).buffer(20, 256)
        self.assertTrue(build_brep.same_band(a, Point(0, 0).buffer(20.05, 256), 0.2))
        self.assertFalse(build_brep.same_band(a, Point(0, 0).buffer(20.5, 256), 0.2))


@unittest.skipUnless(has("numpy", "warp", "trimesh"), "numpy/warp/trimesh absent")
class ScorecardTests(unittest.TestCase):
    def test_warp_distances_match_analytic_cube(self):
        import numpy as np
        import trimesh

        sys.path.insert(0, str(SOURCE))
        import score_twin

        box = trimesh.creation.box(extents=(10, 10, 10))
        pts = np.array([[0, 0, 7.0], [0, 0, 5.0], [8.0, 0, 0], [0, 0, 0]])
        d = score_twin.warp_distances(pts, np.asarray(box.vertices), np.asarray(box.faces))
        np.testing.assert_allclose(d, [2.0, 0.0, 3.0, 5.0], atol=1e-5)

    def test_weighted_percentiles_follow_area(self):
        import numpy as np

        sys.path.insert(0, str(SOURCE))
        import score_twin

        d = np.array([0.0, 1.0])
        w = np.array([99.0, 1.0])
        self.assertEqual(score_twin.weighted_percentiles(d, w, (95,))["p95"], 0.0)


if __name__ == "__main__":
    unittest.main()
