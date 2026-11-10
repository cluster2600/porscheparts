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


@unittest.skipUnless(has("numpy", "shapely", "skimage", "build123d"), "build123d stack absent")
class BandSolidTests(unittest.TestCase):
    def test_band_solid_sits_on_its_interval_whatever_the_contour_orientation(self):
        # Until 2026-11-10 extrude() followed the face normal, so a band built
        # from a clockwise contour sat one thickness below its interval.
        sys.path.insert(0, str(SOURCE))
        import build_brep
        from shapely.geometry import Polygon

        square = [(0, 0), (10, 0), (10, 10), (0, 10)]
        for ring in (square, square[::-1]):
            (solid,) = build_brep.band_solid(Polygon(ring), 41.8, 44.12)
            box = solid.bounding_box()
            self.assertAlmostEqual(box.min.Z, 41.8, places=6)
            self.assertAlmostEqual(box.max.Z, 44.12, places=6)
            self.assertAlmostEqual(solid.volume, 100 * 2.32, places=6)


@unittest.skipUnless(has("numpy", "shapely", "skimage"), "numpy/shapely/scikit-image absent")
class BoundaryTests(unittest.TestCase):
    CORNERS = [(-60.0, -120.0), (-60.0, 120.0), (60.0, -120.0), (60.0, 120.0)]

    @staticmethod
    def face(z, side, tilt_slope=0.0, rms_level=0.6, rms_plane=0.3):
        import math

        return {"side": side, "z_level_mm": z, "rms_level_mm": rms_level, "rms_plane_mm": rms_plane,
                "plane_z_at_axis_mm": z, "plane_slope_xy": [tilt_slope, 0.0],
                "plane_tilt_deg": math.degrees(math.atan(tilt_slope)),
                "plane_z_span_mm": [z - 60 * tilt_slope, z + 60 * tilt_slope]}

    def test_tilt_needs_a_better_plane_fit_and_a_real_angle(self):
        sys.path.insert(0, str(SOURCE))
        import fin_stack

        faces = [self.face(20.0, "top", 0.009), self.face(30.0, "top", 0.009, rms_plane=0.55),
                 self.face(40.0, "bottom", 0.001)]
        bounds, notes = fin_stack.make_boundaries([], faces, 0.0, 60.0, True, self.CORNERS)
        self.assertEqual([b["plane"] is not None for b in bounds], [False, True, False, False, False])
        self.assertEqual(notes["tilted"], 1)
        flat, _ = fin_stack.make_boundaries([], faces, 0.0, 60.0, False, self.CORNERS)
        self.assertTrue(all(b["plane"] is None for b in flat))

    def test_fine_levels_inside_a_fin_face_are_dropped_and_crossings_demoted(self):
        sys.path.insert(0, str(SOURCE))
        import fin_stack

        faces = [self.face(20.0, "top", 0.009)]
        bounds, notes = fin_stack.make_boundaries([19.8, 20.5, 25.0], faces, 0.0, 60.0, True, self.CORNERS)
        self.assertEqual(notes["fine_levels_dropped"], 2)
        self.assertEqual([round(b["z"], 1) for b in bounds], [0.0, 20.0, 25.0, 60.0])
        # A level 0.45 mm above a plane that rises 0.54 mm over the footprint crosses it.
        bounds, notes = fin_stack.make_boundaries([20.45], [self.face(20.0, "top", 0.009)], 0.0, 60.0, True,
                                                  self.CORNERS)
        self.assertEqual(notes["demoted"], [])  # dropped as inside the face's own span instead
        faces = [self.face(20.0, "top", 0.009), self.face(20.4, "bottom", 0.0)]
        bounds, notes = fin_stack.make_boundaries([], faces, 0.0, 60.0, True, self.CORNERS)
        self.assertEqual(notes["demoted"], [20.0])
        self.assertEqual(notes["tilted"], 0)


@unittest.skipUnless(has("numpy", "shapely", "skimage"), "numpy/shapely/scikit-image absent")
class ShellTests(unittest.TestCase):
    def test_only_the_uncovered_part_of_a_cap_is_kept(self):
        import numpy as np

        sys.path.insert(0, str(SOURCE))
        import fin_stack
        from shapely.geometry import box

        boundary = {"z": 5.0, "plane": None}
        lower_band_top, upper_band_bottom = box(0, 0, 10, 10), box(4, 0, 10, 10)
        tris, shown = fin_stack.exposed_cap(lower_band_top, upper_band_bottom, boundary)
        self.assertAlmostEqual(shown, 40.0, places=2)   # the 4 x 10 ledge the upper band leaves bare
        self.assertTrue(np.allclose(tris[:, :, 2], 5.0))
        self.assertLessEqual(tris[:, :, 0].max(), 4.001)
        _, hidden_side = fin_stack.exposed_cap(upper_band_bottom, lower_band_top, boundary)
        self.assertAlmostEqual(hidden_side, 0.0, places=6)
        tilted = {"z": 5.0, "plane": (5.0, 0.01, 0.0)}
        tris, _ = fin_stack.exposed_cap(lower_band_top, None, tilted)
        self.assertTrue(np.allclose(tris[:, :, 2], 5.0 + 0.01 * tris[:, :, 0]))

    def test_cap_flags_follow_the_boundary_surface(self):
        import numpy as np

        sys.path.insert(0, str(SOURCE))
        import fin_stack

        v = np.array([[0, 0, 5.0], [10, 0, 5.1], [0, 10, 5.0], [0, 0, 3.0]])
        f = np.array([[0, 1, 2], [0, 1, 3]])
        self.assertEqual(fin_stack.cap_flags(v, f, {"z": 5.0, "plane": (5.0, 0.01, 0.0)}).tolist(), [True, False])
        self.assertEqual(fin_stack.cap_flags(v, f, {"z": 5.0, "plane": None}).tolist(), [False, False])

    def test_thick_band_is_split_at_an_occupancy_step(self):
        import numpy as np

        sys.path.insert(0, str(SOURCE))
        import fin_stack

        grid = {"pitch_mm": 0.25, "x0": 0.0, "y0": 0.0, "z0": 0.0, "shape": [40, 40, 80]}
        wn = np.zeros((40, 40, 80), dtype=np.float32)
        wn[:, :, :] = 1.0                 # a 10 x 10 mm column ...
        wn[20:, :, 40:] = 0.0             # ... that loses half its section above z = 10 mm
        self.assertEqual(fin_stack.split_levels(wn, grid, 0.0, 19.75), [9.875])
        self.assertEqual(fin_stack.split_levels(wn, grid, 0.0, 8.0), [])


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
