"""Contract tests for the 935 head CAD twin (twins/935-cylinder-head-cad-twin).

They run on synthetic geometry and the committed scalar parameters only; the
private scan never reaches CI.
"""

import hashlib
import importlib.util
import json
import re
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


@unittest.skipUnless(has("numpy", "shapely"), "numpy/shapely absent")
class BandTests(unittest.TestCase):
    @unittest.skipUnless(has("skimage"), "scikit-image absent")
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


@unittest.skipUnless(has("numpy", "shapely", "skimage"), "scikit-image absent")
class NestingTests(unittest.TestCase):
    def test_slice_region_keeps_an_island_inside_a_hole(self):
        # Until 2026-11-10 the even rings were united and the odd ones subtracted
        # in one step, which removed every island standing inside a hole.
        import numpy as np

        sys.path.insert(0, str(SOURCE))
        import build_brep

        w = np.zeros((120, 120), dtype=np.float32)
        w[10:110, 10:110] = 1.0     # body, 100 x 100 cells
        w[30:90, 30:90] = 0.0       # pocket, 60 x 60
        w[50:70, 50:70] = 1.0       # boss standing in the pocket, 20 x 20
        w[57:63, 57:63] = 0.0       # bore in the boss, 6 x 6
        region = build_brep.slice_region(w, {"pitch_mm": 1.0, "x0": 0.0, "y0": 0.0})
        self.assertAlmostEqual(region.area, 100 * 100 - 60 * 60 + 20 * 20 - 6 * 6, delta=12.0)
        from shapely.geometry import Point

        self.assertTrue(region.contains(Point(52.0, 52.0)))     # boss wall
        self.assertFalse(region.contains(Point(59.5, 59.5)))    # bore
        self.assertFalse(region.contains(Point(40.0, 40.0)))    # pocket


@unittest.skipUnless(has("numpy", "shapely", "manifold3d", "trimesh"), "numpy/shapely/manifold3d/trimesh absent")
class LoftTests(unittest.TestCase):
    @staticmethod
    def square(lo, hi, hole=None):
        from shapely.geometry import Polygon, box
        from shapely.geometry.polygon import orient

        holes = [] if hole is None else [box(hole[0], hole[0], hole[1], hole[1]).exterior.coords]
        return orient(Polygon(box(lo, lo, hi, hi).exterior.coords, holes), 1.0)

    def test_bands_put_a_prism_on_each_side_of_a_face(self):
        sys.path.insert(0, str(SOURCE))
        import loft_stack

        bands = loft_stack.plan_bands([0.0, 2.0, 2.3], 0.5)
        self.assertEqual(bands[0], (0.0, 0.25, 0.25, 0.25))                 # prism above the face at 0
        self.assertEqual(bands[-2], (1.75, 2.0, 1.75, 1.75))                # prism below the face at 2
        self.assertEqual([round(b[1] - b[0], 6) for b in bands[1:-2]], [0.5, 0.5, 0.5])
        self.assertTrue(all(b[2] == b[0] and b[3] == b[1] for b in bands[1:-2]))   # ruled between
        self.assertEqual(bands[-1], (2.0, 2.3, 2.15, 2.15))                 # gap too thin: one prism
        self.assertAlmostEqual(sum(b[1] - b[0] for b in bands), 2.3)

    def test_ruled_frustum_has_the_exact_volume_and_an_unpaired_hole_stays_a_prism(self):
        import numpy as np
        import trimesh

        sys.path.insert(0, str(SOURCE))
        import loft_stack

        bottom, top = self.square(0, 10, (4, 6)), self.square(1, 9, (4.5, 5.5))
        partner = loft_stack.pair_rings([bottom], [top], 2.0)
        self.assertEqual(sorted(partner), [(0, 0)])     # the hole's overlap is 0.25: not paired
        plans = loft_stack.ruling_plans(bottom, 0, partner)
        self.assertEqual([(len(p[2]), p[3]) for p in plans], [(0, 1), (1, 1), (0, 0)])
        v, f = loft_stack.polygon_solid(plans[0], 0.0, 2.0)
        self.assertTrue(loft_stack.is_manifold(v, f))
        # The second plan cuts the hole out of the ruled solid: same body.
        v2, f2 = loft_stack.polygon_solid(plans[1], 0.0, 2.0)
        self.assertAlmostEqual(trimesh.Trimesh(v2, f2, process=False).volume, 2.0 / 3.0 * (100 + 64 + 80) - 8.0, places=9)
        mesh = trimesh.Trimesh(v, f, process=False)
        self.assertTrue(mesh.is_watertight and mesh.is_winding_consistent)
        # Square frustum 100 -> 64 over 2 mm, minus a 2 x 2 prism.
        self.assertAlmostEqual(mesh.volume, 2.0 / 3.0 * (100 + 64 + 80) - 8.0, places=9)
        self.assertGreater(np.cross(v[f][:, 1] - v[f][:, 0], v[f][:, 2] - v[f][:, 0])[:, 2].max(), 0)

    def test_stitch_uses_only_the_rings_own_vertices(self):
        import numpy as np
        from shapely import segmentize
        from shapely.geometry import Point

        sys.path.insert(0, str(SOURCE))
        import loft_stack

        a = loft_stack.open_ring(segmentize(Point(0, 0).buffer(10.0, 16), 0.7).exterior)[::-1]
        b = loft_stack.open_ring(Point(0.4, -0.2).buffer(8.0, 5).exterior)[::-1]
        rolled, tris = loft_stack.stitch(a, b)
        self.assertEqual(len(tris), len(a) + len(b))
        self.assertEqual(sorted(map(tuple, rolled.tolist())), sorted(map(tuple, b.tolist())))
        # Every edge of either ring is used by exactly one wall triangle.
        for ring, n in ((0, len(a)), (1, len(b))):
            own = tris[(tris[:, :, 0] == ring).sum(axis=1) == 2]
            self.assertEqual(len(own), n)

    def test_union_of_stacked_bands_is_one_closed_body(self):
        import tempfile

        import numpy as np

        sys.path.insert(0, str(SOURCE))
        import loft_stack

        lower, upper = self.square(0, 10), self.square(2, 6)
        with tempfile.TemporaryDirectory() as tmp:
            files = []
            for k, (poly, z0, z1) in enumerate(((lower, 0.0, 1.0), (upper, 1.0, 3.0))):
                rings = [loft_stack.open_ring(poly.exterior)]
                v, f = loft_stack.polygon_mesh(rings, rings, z0, z1)
                files.append(Path(tmp) / f"band-{k}.npz")
                np.savez(files[-1], v=v, f=f, tri_part=np.zeros(len(f), dtype=np.int64))
            whole, parts = loft_stack.unite(files)
        self.assertEqual(parts, 2)
        self.assertEqual(len(whole.decompose()), 1)
        self.assertAlmostEqual(whole.volume(), 100.0 + 32.0, places=9)
        self.assertAlmostEqual(whole.surface_area(), 2 * 100 + 40 + 4 * 4 * 2, places=9)   # shared face gone


@unittest.skipUnless(has("numpy", "trimesh"), "numpy/trimesh absent")
class LoftOccupancyTests(unittest.TestCase):
    def test_plane_cut_fill_reproduces_a_sphere_and_a_tube(self):
        import numpy as np
        import trimesh

        sys.path.insert(0, str(SOURCE))
        import loft_occupancy

        h, n = 0.25, 96
        x0 = y0 = z0 = -12.0
        sphere = trimesh.creation.icosphere(subdivisions=4, radius=10.0)
        outer = trimesh.creation.cylinder(radius=10.0, height=8.0, sections=96)
        inner = trimesh.creation.cylinder(radius=6.0, height=8.0, sections=96)
        inner.invert()                                    # inward wall of a tube; open ends do not matter here
        for mesh, radius_in in ((sphere, None), (trimesh.util.concatenate([outer, inner]), 6.0)):
            tri = np.asarray(mesh.triangles, dtype=np.float64)
            filled = 0
            for k in range(n):
                z = z0 + k * h + loft_occupancy.SLICE_SHIFT_MM
                mask = loft_occupancy.fill(loft_occupancy.plane_segments(tri, z), (n, n), x0, y0, h)
                filled += int(mask.sum())
                if radius_in is not None and abs(z) < 3.9:
                    self.assertFalse(mask[n // 2, n // 2])          # the bore stays empty (even-odd)
                    self.assertTrue(mask[n // 2 + 32, n // 2])      # the wall at r = 8 mm is solid
            exact = 4.0 / 3.0 * np.pi * 1000.0 if radius_in is None else np.pi * (100.0 - 36.0) * 8.0
            self.assertAlmostEqual(filled * h ** 3 / exact, 1.0, delta=0.01)


class PortAuditTests(unittest.TestCase):
    FIT = {"method": {"station_step_mm": 3.0},
           "ports": [{"name": "p", "stations": 11, "closed_stations": 11, "loft_length_mm": 30.0,
                      "wall_points_observed_share": 0.97}]}

    def test_a_port_needs_closed_sections_observed_walls_and_a_valve(self):
        sys.path.insert(0, str(SOURCE))
        import audit_port_domain

        built = {"items": [{"id": "H05-valve-seats-guides", "status": "modelled_from_specification"}]}
        self.assertEqual(audit_port_domain.audit(self.FIT, built)["verdict"], "admissible")
        missing = {"items": [{"id": "H05-valve-seats-guides", "status": "not_modelled_in_v0"}]}
        self.assertEqual(audit_port_domain.audit(self.FIT, missing)["verdict"], "not_admissible")
        import copy

        for key, value in (("closed_stations", 8), ("wall_points_observed_share", 0.90)):
            fit = copy.deepcopy(self.FIT)
            fit["ports"][0][key] = value
            res = audit_port_domain.audit(fit, built)
            self.assertEqual(res["verdict"], "not_admissible")
            self.assertEqual(sum(res["ports"][0]["gates"].values()), 2)

    def test_the_committed_audit_matches_the_register(self):
        sys.path.insert(0, str(SOURCE))
        import audit_port_domain

        fit = json.loads((TWIN / "params" / "port-fit.json").read_text())
        reg = json.loads((TWIN / "hypotheses.json").read_text())
        self.assertEqual(audit_port_domain.audit(fit, reg),
                         json.loads((TWIN / "params" / "port-cfd-audit.json").read_text()))


class DownstreamContractTests(unittest.TestCase):
    """The committed summaries of the v2 body and of what was run on it."""

    def load(self, name):
        return json.loads((TWIN / "params" / name).read_text())

    def test_every_loft_body_is_one_closed_solid(self):
        p95 = []
        for label in ("s100", "s050", "s025"):
            s = self.load(f"v2-loft-{label}-summary.json")
            self.assertEqual(s["union"]["status"], "Error.NoError")
            self.assertEqual(s["bands_failed"], [])
            self.assertTrue(s["body"]["trimesh_watertight"] and s["body"]["trimesh_winding_consistent"])
            self.assertAlmostEqual(s["body"]["volume_mm3"] / s["body"]["trimesh_volume_mm3"], 1.0, places=9)
            p95.append(self.load(f"scorecard-v2-loft-{label}.json")["scan_to_twin"]["p95"])
        self.assertEqual(p95, sorted(p95, reverse=True))      # finer sections never score worse

    def test_the_rasterised_body_keeps_its_volume(self):
        occ = self.load("v2-loft-s025-occupancy.json")
        self.assertLess(abs(occ["relative_difference"]), 2e-3)

    def test_thermal_on_the_cad_body_closes_its_energy_balance(self):
        t = self.load("thermal-screen-cad.json")
        self.assertEqual(t["level"]["solver"]["returncode"], 0)
        self.assertEqual(t["level"]["mesh"]["quality"]["nonpositive"], 0)
        self.assertLess(abs(t["level"]["energy_balance"]["relative_imbalance"]), 0.01)
        self.assertIn("not an engine temperature prediction", t["claims"])
        self.assertIn("mean_nodal_difference_C", t["against_reference"])

    def test_am_screen_passed_its_witnesses_and_claims_nothing(self):
        sup = self.load("am-supports.json")
        self.assertTrue(sup["witness"]["all_within_tolerance"])
        self.assertIn("no orientation choice", sup["scope"])
        cool = self.load("am-cooldown.json")
        self.assertIn("declared-hypothesis", cool["scope"])
        for name in ("hex_4mm", "hex_2mm", "witness_block"):
            self.assertIn(name, cool["levels"])

    def test_simready_summaries_state_what_a_pass_means(self):
        for name in ("simready-deck-plate.json", "simready-ports.json", "simready-validate-t4-stage.json",
                     "simready-validate-cad-stage.json"):
            s = self.load(name)
            self.assertIn("not SimReady-certified", s["claims"])
            self.assertIn(s["status"], ("passed", "validator_findings"))
        # The display surface rebuilt after the stud repair carries one non-manifold vertex.
        t4 = self.load("simready-validate-t4-stage.json")["stage_input"]["validation"]
        self.assertEqual((t4["issues_by_severity"]["FAILURE"], t4["issues_by_severity"]["ERROR"]), (0, 0))
        self.assertEqual([r["rule"] for r in t4["rules_with_issues"]], ["ManifoldChecker"])
        cad = self.load("simready-validate-cad-stage.json")["stage_input"]["validation"]["issues_by_severity"]
        self.assertEqual((cad["FAILURE"], cad["ERROR"]), (0, 0))


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


@unittest.skipUnless(has("numpy"), "numpy absent")
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


@unittest.skipUnless(has("numpy", "shapely"), "numpy/shapely absent")
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


@unittest.skipUnless(has("numpy"), "numpy absent")
class FeatureFitTests(unittest.TestCase):
    """fit_features.py and check_features.py on synthetic geometry and on the committed records."""

    def setUp(self):
        sys.path.insert(0, str(SOURCE))
        import check_features
        import fit_features
        import numpy as np

        self.ff, self.cf, self.np = fit_features, check_features, np

    def cone_points(self, radius, half_angle_deg, offset=(0.0, 0.0), n=4000, seed=3):
        np = self.np
        rng = np.random.default_rng(seed)
        t = rng.uniform(-2.0, 2.0, n)
        theta = rng.uniform(0, 2 * np.pi, n)
        rho = radius + np.tan(np.radians(half_angle_deg)) * t
        return np.column_stack((offset[0] + rho * np.cos(theta), offset[1] + rho * np.sin(theta), t))

    def test_about_axis_recovers_angle_diameter_and_eccentricity(self):
        points = self.cone_points(24.5, 45.0, offset=(0.3, -0.4))
        got = self.ff.about_axis(points, [0, 0, 0], [0, 0, 1])
        self.assertAlmostEqual(got["half_angle_deg"], 45.0, delta=0.05)
        # The diameter is the one at the mean station of the points, on a 45 degree cone.
        self.assertAlmostEqual(got["diameter_mm"], 49.0 + 2.0 * got["station_mm"], delta=0.02)
        self.assertAlmostEqual(got["eccentricity_mm"], 0.5, delta=0.01)
        # Read the other way along the axis, the same surface closes instead of opening.
        self.assertAlmostEqual(self.ff.about_axis(points, [0, 0, 0], [0, 0, -1])["half_angle_deg"], -45.0, delta=0.05)

    def test_window_selects_a_tube_by_position_only(self):
        np = self.np
        points = np.array([[4.0, 0, 1.0], [4.0, 0, 9.0], [7.0, 0, 1.0], [0, 4.0, -1.0], [0.5, 0, 1.0]])
        roi = {"seed_point": [0, 0, 0], "seed_axis": [0, 0, 2.0], "t_mm": [0, 5], "rho_mm": [3, 5]}
        self.assertEqual(self.ff.window(points, roi).tolist(), [0])

    def test_split_is_deterministic_disjoint_and_about_half(self):
        np = self.np
        index = np.arange(100000, 140000)
        fitted, held = self.ff.split_halves(index)
        again, _ = self.ff.split_halves(index[::-1])
        self.assertEqual(set(fitted.tolist()), set(again.tolist()))
        self.assertFalse(set(fitted.tolist()) & set(held.tolist()))
        self.assertEqual(len(fitted) + len(held), len(index))
        self.assertAlmostEqual(len(fitted) / len(index), 0.5, delta=0.02)

    def test_choose_keeps_the_stated_kind_and_prefers_a_determined_fit(self):
        axis = {"axis_direction": [0, 0, 1], "side": "concave"}
        bore = {**axis, "type": "cylinder", "determined": True, "points": 300}
        rival = {**axis, "type": "cylinder", "determined": False, "points": 900}
        seat = {**axis, "type": "cone", "half_angle_deg": 45.0, "determined": True, "points": 500}
        boss = {**axis, "type": "cylinder", "side": "convex", "determined": True, "points": 800}
        tilted = {**axis, "axis_direction": [0, 0.5, 0.866], "type": "cylinder", "determined": True, "points": 999}
        face = {"type": "plane", "normal": [0, 0, -1], "determined": True, "points": 50}
        found = [rival, seat, boss, tilted, face, bore]
        roi = {"seed_axis": [0, 0, 1], "side": "concave"}
        self.assertIs(self.ff.choose(found, {**roi, "kind": "bore"}), bore)
        self.assertIs(self.ff.choose(found, {**roi, "kind": "seat"}), seat)
        self.assertIs(self.ff.choose(found, {**roi, "kind": "boss", "side": "convex"}), boss)
        self.assertIs(self.ff.choose(found, {**roi, "kind": "plane", "side": "plane"}), face)
        self.assertIs(self.ff.choose([rival], {**roi, "kind": "bore"}), rival)
        self.assertIsNone(self.ff.choose([face], {**roi, "kind": "bore"}))

    def test_two_centre_datum_points_from_the_first_centre_to_the_second(self):
        by_id = {"a": {"fit": {"axis_point": [0, 0, 0]}}, "b": {"fit": {"axis_point": [0, 30.0, 40.0]}}, "c": {"fit": None}}
        got = self.ff.group_datums({"g": {"line_through": ["a", "b"]}, "h": {"line_through": ["a", "c"]}}, by_id)
        self.assertEqual(list(got), ["g"])
        self.assertEqual(got["g"]["span_mm"], 50.0)
        self.np.testing.assert_allclose(got["g"]["axis_direction"], [0, 0.6, 0.8], atol=1e-6)

    def test_primitive_mesh_lies_on_the_primitive(self):
        np = self.np
        fit = {"type": "cone", "axis_point": [1.0, 2.0, 3.0], "axis_direction": [0, 0, 1], "diameter_mm": 20.0,
               "half_angle_deg": 45.0, "station_range_mm": [-1.0, 2.0]}
        v, f = self.cf.primitive_mesh(fit)
        t = v[:, 2] - 3.0
        np.testing.assert_allclose(np.hypot(v[:, 0] - 1.0, v[:, 1] - 2.0), 10.0 + t, atol=1e-9)
        self.assertEqual((float(t.min()), float(t.max())), (-1.0, 2.0))
        self.assertEqual(len(f), 2 * self.cf.SEGMENTS)
        flat, _ = self.cf.primitive_mesh({"type": "plane", "point": [0, 0, 5.0], "normal": [0, 0, 1]})
        np.testing.assert_allclose(flat[:, 2], 5.0)

    def test_verdict_applies_the_fixed_acceptance(self):
        np = self.np
        good = np.concatenate([np.full(95, 0.05), np.full(5, 0.3), np.full(40, 2.0)])
        poor = np.concatenate([np.full(80, 0.05), np.full(20, 0.3)])
        self.assertTrue(self.cf.verdict(good)["confirmed"])
        self.assertEqual(self.cf.verdict(good)["check_vertices"], 100)
        self.assertFalse(self.cf.verdict(poor)["confirmed"])
        self.assertFalse(self.cf.verdict(np.full(50, 0.01))["confirmed"])

    def test_feature_scripts_start_in_isolated_mode(self):
        # run_twin.sh runs every step with -I, which leaves the script directory out of
        # sys.path: a script that imports twin_common must add that directory itself.
        import subprocess

        for name in ("fit_features.py", "check_features.py", "export_simready.py", "assemble_records.py"):
            source = (SOURCE / name).read_text()
            if "twin_common" in source:
                self.assertLess(source.index("sys.path.insert(0, str(Path(__file__).resolve().parent))"),
                                source.index("from twin_common import"), name)
        for name in ("fit_features.py", "check_features.py"):
            run = subprocess.run([sys.executable, "-I", str(SOURCE / name), "--help"], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, f"{name}: {run.stderr[-300:]}")

    def test_committed_fits_and_check_are_bound_and_consistent(self):
        import hashlib

        params = TWIN / "params"
        fits = json.loads((params / "feature-fits.json").read_text())
        check = json.loads((params / "feature-check.json").read_text())
        self.assertEqual(fits["scan_sha256"], SCAN_SHA256)
        self.assertEqual(fits["rois_sha256"], hashlib.sha256((params / "feature-rois.json").read_bytes()).hexdigest())
        self.assertEqual(check["fits_sha256"], hashlib.sha256((params / "feature-fits.json").read_bytes()).hexdigest())
        self.assertEqual(fits["tool"]["noise_mm"],
                         json.loads((params / "frame.json").read_text())["planes"][0]["residual"]["rms_mm"])
        self.assertEqual(check["acceptance"], {"fixed_before_first_run": True, "band_mm": self.cf.BAND_MM,
                                               "tolerance_mm": self.cf.TOLERANCE_MM, "min_share": self.cf.MIN_SHARE,
                                               "min_vertices": self.cf.MIN_VERTICES})
        self.assertEqual([r["id"] for r in fits["regions"]], [r["id"] for r in check["regions"]])
        self.assertEqual(check["confirmed"], sum(r["confirmed"] for r in check["regions"]))
        for region, row in zip(fits["regions"], check["regions"]):
            fit = region["fit"]
            if fit is None:
                self.assertFalse(row["confirmed"])
                continue
            self.assertEqual(row["determined_by_the_fit"], fit["determined"])
            if not fit["determined"] and fit["type"] != "plane":
                # Detected, not measured: no uncertainty may be quoted for it.
                self.assertIsNone(fit["radius_sigma_mm"])
                self.assertIsNone(fit["axis_direction_sigma_deg"])
            if row["confirmed"]:
                self.assertGreaterEqual(row["share_within_tolerance"], self.cf.MIN_SHARE)
        for group, datum in fits["group_datums"].items():
            rule = datum["rule"]
            if "axis_of" in rule:
                self.assertTrue(next(r for r in fits["regions"] if r["id"] == rule["axis_of"])["fit"]["determined"], group)

    def test_body_cloudcompare_agrees_with_the_scorecard(self):
        body = json.loads((TWIN / "params" / "cloudcompare-v2-body.json").read_text())
        for key in ("p50_mm", "p95_mm"):
            self.assertAlmostEqual(body["cloudcompare"][key], body["scorecard_scan_to_twin"][key], delta=0.005)
        for key in ("share_within_0p1_mm", "share_within_0p2_mm", "share_within_0p5_mm"):
            self.assertAlmostEqual(body["cloudcompare"][key], body["scorecard_scan_to_twin"][key], delta=0.005)


@unittest.skipUnless(has("numpy"), "numpy absent")
class AlloyThermalTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(SOURCE))
        import alloy_thermal

        self.at = alloy_thermal

    def test_only_the_conductivity_card_changes(self):
        deck = "*MATERIAL,NAME=AL\n*CONDUCTIVITY\n0.15\n*SOLID SECTION,ELSET=EALL,MATERIAL=AL\n*FILM\n1,F1,40,8e-05\n"
        new = self.at.deck_with(deck, 0.173)
        self.assertEqual(new, deck.replace("\n0.15\n", "\n0.173\n"))
        with self.assertRaises(SystemExit):
            self.at.deck_with(deck + "*CONDUCTIVITY\n0.2\n", 0.1)

    def test_fin_efficiency_is_bounded_by_the_isothermal_body(self):
        case = self.at.CASE
        delta = case["chamber_wall_temperature_C"] - case["air_temperature_C"]
        area = 100000.0
        ideal = case["film_coefficient_W_per_mm2K"] * area * delta
        got = self.at.derived(0.8 * ideal, area)
        self.assertAlmostEqual(got["fin_efficiency"], 0.8, places=4)
        self.assertAlmostEqual(got["ideal_heat_W"], ideal, places=1)
        self.assertAlmostEqual(got["thermal_resistance_K_per_W"], delta / (0.8 * ideal), places=5)


@unittest.skipUnless(has("numpy"), "numpy absent")
class AssemblyThermalTests(unittest.TestCase):
    """assembly_thermal.py: hypothesis solids, materials and film groups on the committed fits."""

    def setUp(self):
        sys.path.insert(0, str(SOURCE))
        import assembly_thermal
        import numpy as np

        self.at, self.np = assembly_thermal, np
        self.case = json.loads((TWIN / "params" / "assembly-case.json").read_text())
        self.comps = assembly_thermal.build_components(
            self.case, json.loads((TWIN / "params" / "feature-fits.json").read_text()))

    def point(self, part, station, radius=0.0):
        np = self.np
        a = np.asarray(part["direction"])
        e = np.cross(a, [1.0, 0.0, 0.0])
        return np.asarray(part["origin"]) + station * a + radius * e / np.linalg.norm(e)

    def test_every_number_of_the_case_is_a_declared_hypothesis(self):
        for block in ("valves", "plugs", "materials", "films"):
            for name, item in self.case[block].items():
                self.assertIn("hypothesis", item["status"], f"{block}/{name}")
        self.assertIn("hypothesis", self.case["regions"]["status"])
        for variant in self.case["variants"]:
            self.assertIn("hypothesis", variant["status"], variant["id"])
        self.assertIn(self.case["ranking_variant"], [v["id"] for v in self.case["variants"]])
        self.assertEqual(set(self.case["films"]), set(self.at.GROUPS))

    def test_the_two_valve_faces_sit_at_the_same_height_and_the_inlet_is_larger(self):
        np = self.np
        v = self.comps["valves"]
        z = {n: (np.asarray(x["origin"]) + x["t_face"] * np.asarray(x["direction"]))[2] for n, x in v.items()}
        self.assertAlmostEqual(z["valve_y_minus"], z["valve_y_plus"], delta=0.5)
        self.assertGreater(v["valve_y_minus"]["r_head"], v["valve_y_plus"]["r_head"])
        self.assertEqual({x["role"] for x in v.values()}, {"inlet", "exhaust"})

    def test_materials_follow_the_solids_with_the_valve_first(self):
        np = self.np
        v = self.comps["valves"]["valve_y_minus"]
        p = self.comps["plugs"]["plug_x_plus"]
        middle = 0.5 * (v["guide_stations"][0] + v["guide_stations"][1])
        points = np.array([
            self.point(v, middle),                              # stem inside the guide
            self.point(v, middle, v["r_stem"] + 0.5),           # guide wall
            self.point(v, middle, v["r_guide"] + 2.0),          # head alloy beside the guide
            self.point(v, v["t_face"] - 0.5, v["r_head"] - 0.2),   # rim of the valve head
            self.point(v, v["t_face"] - 0.5, v["r_head"] + 0.2),   # just outside it
            self.point(p, 0.5 * (p["t_tip"] + p["t_seat"])),    # plug thread
        ])
        names = [self.at.MATERIALS[i] for i in self.at.material_of(points, self.comps)]
        self.assertEqual(names, ["valve", "guide", "alloy", "valve", "alloy", "plug"])
        self.assertEqual(self.at.added_solid(points, self.comps).tolist(), [True, False, False, True, False, True])

    def test_faces_are_sorted_into_the_film_groups(self):
        np = self.np
        v_in, v_ex = self.comps["valves"]["valve_y_minus"], self.comps["valves"]["valve_y_plus"]
        ports = {"inlet": [{"centre": [0.0, -90.0, 46.0], "radius_max_mm": 21.0}],
                 "exhaust": [{"centre": [0.0, 70.0, 36.0], "radius_max_mm": 20.0}]}
        centroid = np.array([
            [0.0, 0.0, 20.0],                                   # chamber roof
            self.point(v_in, v_in["t_face"] + 6.0, 10.0),       # back of the inlet valve
            self.point(v_ex, v_ex["t_face"] + 6.0, 10.0),       # back of the exhaust valve
            [20.0, -90.0, 46.0],                                # inlet port wall, looking at its centreline
            [20.0, -90.0, 46.0],                                # same place, looking away: an outside face
            [50.0, 0.0, 2.2],                                   # floor of the register recess
            [60.0, 0.0, 0.0],                                   # deck plane outside the recess
            [50.0, 0.0, 90.0],                                  # cam side, away from the valves
            self.point(v_in, v_in["t_spring_seat"] + 2.0, 10.0),   # floor of the inlet spring pocket
        ])
        normal = np.array([[0, 0, -1.0], [0, 0, 1.0], [0, 0, 1.0], [-1.0, 0, 0], [1.0, 0, 0], [0, 0, -1.0],
                           [0, 0, -1.0], [0, 0, 1.0], [0, 0, 1.0]])
        got = [self.at.GROUPS[i] for i in self.at.classify_faces(centroid, normal, self.comps, self.case, ports)]
        self.assertEqual(got, ["chamber_gas", "cool_port", "hot_port", "cool_port", "air", "cylinder_contact", "air", "air",
                               "oil"])

    def test_heat_by_group_is_film_coefficient_times_area_times_excess(self):
        np = self.np
        tag = np.array([1, 2, 3])
        xyz = np.array([[0, 0, 0], [10.0, 0, 0], [0, 10.0, 0]])
        faces = (np.array([0]), np.array([1]), np.array([[1, 2, 3]]))
        temps = np.array([200.0, 220.0, 240.0])
        films = self.at.variant_films(self.case, {"films": {"oil": None}})
        heat = self.at.heat_by_group(temps, tag, xyz, faces, np.array([self.at.GROUPS.index("air")]), films)
        film = self.case["films"]["air"]
        expected = film["coefficient_W_per_m2K"] * 1e-6 * 50.0 * (220.0 - film["sink_temperature_C"])
        self.assertAlmostEqual(heat["air"]["heat_out_W"], expected, places=2)
        self.assertEqual(heat["chamber_gas"]["area_mm2"], 0.0)
        # A group whose film a variant removes is in air.
        self.assertEqual(self.at.film_of(films, "oil"), self.at.film_of(films, "air"))
        hot = self.at.variant_films(self.case, {"films": {"chamber_gas": {"sink_temperature_C": 621.0}}})
        self.assertEqual(hot["chamber_gas"]["sink_temperature_C"], 621.0)
        self.assertEqual(hot["chamber_gas"]["coefficient_W_per_m2K"], self.case["films"]["chamber_gas"]["coefficient_W_per_m2K"])
        self.assertEqual(self.case["films"]["chamber_gas"]["sink_temperature_C"], 900.0)   # the base case is not altered


class AlloyTradeoffTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(SOURCE))
        import alloy_tradeoff

        self.tr = alloy_tradeoff

    def test_hot_yield_is_interpolated_and_never_extrapolated(self):
        points = {"20": 465, "150": 319, "300": 60}
        self.assertEqual(self.tr.yield_at(points, 150.0), 319.0)
        self.assertAlmostEqual(self.tr.yield_at(points, 225.0), 189.5)
        self.assertIsNone(self.tr.yield_at(points, 301.0))          # beyond the last published point
        self.assertIsNone(self.tr.yield_at({"20": 300}, 20.0))      # one point is not a curve
        self.assertIsNone(self.tr.yield_at({"150": 354, "250": 215}, 100.0))

    def test_rows_take_the_peak_at_solved_conductivities_only(self):
        strength = {"rows": [
            {"id": "a", "alloy": "A", "condition": "c", "conductivity_rows": ["a1", "a2"], "condition_match": "same",
             "yield_MPa_by_temperature_C": {"20": 200, "300": 100}, "verification": "v"},
            {"id": "b", "alloy": "B", "condition": "c", "conductivity_rows": [], "condition_match": "none",
             "yield_MPa_by_temperature_C": {"150": 354, "250": 215}, "verification": "v"},
            {"id": "c", "alloy": "C", "condition": "c", "conductivity_rows": ["c1"], "condition_match": "same",
             "yield_MPa_by_temperature_C": {"20": 300}, "verification": "v"}]}
        candidates = {"candidates": [{"id": "a1", "conductivity_W_per_mK": 100.0}, {"id": "a2", "conductivity_W_per_mK": 150.0},
                                     {"id": "c1", "conductivity_W_per_mK": 150.0}]}
        assembly = {"ranking_variant": "v", "variants": {"v": {"by_conductivity": [
            {"alloy_conductivity_W_per_mK": 100.0, "peak_C": {"alloy": 300.0}},
            {"alloy_conductivity_W_per_mK": 150.0, "peak_C": {"alloy": 160.0}}]}}}
        a, b, c = self.tr.tradeoff(strength, candidates, assembly)
        self.assertEqual(a["peak_head_alloy_C"], [160.0, 300.0])
        self.assertEqual(a["peak_C_above_the_coolest_candidate"], [0.0, 140.0])
        self.assertAlmostEqual(a["yield_MPa_at_reference_temperature"], 117.9, places=1)   # 250 C on the 20-300 C line
        self.assertEqual(a["yield_MPa_at_the_computed_peak"], [100.0, 150.0])
        self.assertIsNone(b["peak_head_alloy_C"])
        self.assertIn("no conductivity", b["hot_yield_status"])
        self.assertIsNone(c["yield_MPa_at_the_computed_peak"])
        self.assertIn("not published", c["hot_yield_status"])


@unittest.skipUnless(has("numpy", "scipy"), "numpy/scipy absent")
class PrintBodyTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(SOURCE))
        import numpy as np
        import print_body

        self.pb, self.np = print_body, np

    def test_enclosed_air_is_found_and_open_air_is_not(self):
        np = self.np
        solid = np.zeros((12, 12, 12), dtype=bool)
        solid[2:10, 2:10, 2:10] = True
        solid[5:7, 5:7, 5:7] = False            # a closed pocket
        solid[3, 3, 0:6] = False                # a blind hole open to the outside
        air = self.pb.enclosed_air(solid)
        self.assertEqual(int(air.sum()), 8)
        self.assertFalse(air[3, 3, 4])
        self.assertEqual(int(self.pb.enclosed_air(solid | air).sum()), 0)

    def test_stock_grows_downward_only_under_low_faces(self):
        np = self.np
        z = 0.25 * np.arange(40)
        solid = np.zeros((3, 1, 40), dtype=bool)
        solid[0, 0, 8:20] = True                # lowest face at 2.0 mm: inside the deck zone
        solid[1, 0, 20:30] = True               # lowest face at 5.0 mm: a dome, left alone
        add = self.pb.stock_below(solid, z, z_max=3.0, stock=1.0, pitch=0.25)
        self.assertEqual(np.flatnonzero(add[0, 0]).tolist(), [4, 5, 6, 7])
        self.assertFalse(add[1].any() or add[2].any())

    def test_each_accepted_stud_gets_its_cluster_radius(self):
        frame = {"rods": {"a": [{"point_on_axis": [0, 0, 100.0], "radial_residual": {"max_mm": 3.0}},
                                {"point_on_axis": [50.0, 0, 100.0], "radial_residual": {"max_mm": 1.0}}]}}
        summary = {"studs": [
            {"accepted": True, "point_on_axis": [50.0, 0, 100.0], "axis": [0, 0, 2.0], "radius_mm": 3.5, "seat_level_along_axis": -12.0},
            {"accepted": False, "point_on_axis": [0, 0, 100.0], "axis": [0, 0, 1.0], "radius_mm": 2.0, "seat_level_along_axis": 0.0}]}
        got = self.pb.stud_envelopes(frame, summary)
        self.assertEqual(len(got), 1)
        self.assertEqual((got[0]["radius"], got[0]["t_seat"], got[0]["direction"]), (4.5, -12.0, [0.0, 0.0, 1.0]))

    def test_committed_print_body_is_closed_clean_and_only_a_study_object(self):
        record = json.loads((TWIN / "params" / "print-body.json").read_text())
        case = json.loads((TWIN / "params" / "print-body-case.json").read_text())
        surface = record["surface"]
        self.assertTrue(surface["watertight_after_welding"] and surface["winding_consistent"])
        self.assertEqual((surface["edges_used_once"], surface["edges_used_by_more_than_two_faces"],
                          surface["triangles_with_area_below_1e-8_mm2"]), (0, 0, 0))
        self.assertEqual(record["enclosed_voids_remaining"], 0)
        self.assertTrue(record["strict_gate"]["passed"])
        self.assertGreater(record["print_body_volume_mm3"], record["twin_body_volume_mm3"])
        self.assertGreater(record["stud_residue_removed_mm3"], 0.0)
        self.assertIn("not a build file", record["claims"])
        self.assertIn("hypothesis", case["stock"]["status"])
        supports = json.loads((TWIN / "params" / "print-body-supports.json").read_text())
        self.assertAlmostEqual(supports["inputs"]["inside_volume_mm3"], record["print_body_volume_mm3"], delta=5.0)
        self.assertEqual(supports["voids"]["strict_flood_fill_fine"]["enclosed_void_volume_mm3"], 0.0)


    def test_layer_screen_record_keeps_its_failed_attempts_and_its_closed_gates(self):
        record = json.loads((TWIN / "params" / "print-body-layer-screen.json").read_text())
        outcomes = [a["outcome"].split(" ")[0] for a in record["attempts"]]
        self.assertEqual(outcomes, ["killed", "killed", "completed", "killed", "killed", "killed", "completed", "completed"])
        self.assertIn("thickness probe", record["why_the_fine_surface_failed"])
        self.assertTrue(record["driver_witness"]["same_hashes_as_the_run_without_the_driver"])
        self.assertEqual(record["driver_witness"]["manifest"], record["coarser_surface"]["manifest"]["artifacts"])
        for report, layers, triangles in ((record["report"], 4482, 1684604), (record["coarser_surface"]["report"], 4481, 398652)):
            self.assertTrue(report["gates"]["full_piece_layer_slicing_completed"])
            self.assertTrue(report["gates"]["bare_part_machine_envelope_fit"])
            for gate in ("metal_print_authorized", "physical_coupon_qualified", "recoater_clearance_validated",
                         "supplier_supports_validated", "supplier_machine_file_signed"):
                self.assertFalse(report["gates"][gate], gate)
            self.assertEqual(report["full_build_slicing"]["layer_count"], layers)
            self.assertEqual(report["analysis_surface"]["triangles"], triangles)
            self.assertEqual(report["selected_candidate_orientation"], "build_y")
            self.assertEqual(report["powder_escape_screen"]["trapped_void_volume_mm3"], 0.0)
            self.assertEqual(report["machine_candidate"]["model"], "EP-M300")

    def test_wall_check_bounds_the_thickness_probe(self):
        walls = json.loads((TWIN / "params" / "print-body-wall-check.json").read_text())["walls"]
        shares = [walls[k]["share_of_surface_voxels"] for k in ("below_1_mm", "below_1.5_mm", "below_2_mm")]
        self.assertEqual(shares, sorted(shares))
        probe = json.loads((TWIN / "params" / "print-body-layer-screen.json").read_text())["comparison"]
        # the grid sits near the smoother surface's probe and far below the rough one's
        self.assertLess(abs(shares[1] - probe["surface_1p0_mm"]["thickness_probe_mm"]["share_below_1p5"]), 0.03)
        self.assertGreater(probe["surface_0p5_mm"]["thickness_probe_mm"]["share_below_1p5"], 2 * shares[1])

    @unittest.skipUnless(has("numpy", "scipy"), "numpy or scipy absent")
    def test_opening_finds_a_thin_plate_and_keeps_a_thick_one(self):
        sys.path.insert(0, str(SOURCE))
        import numpy as np
        import wall_check

        solid = np.zeros((60, 60, 40), dtype=bool)
        solid[5:55, 5:55, 4:16] = True                     # a plate 3 mm thick at 0.25 mm
        solid[5:55, 28:32, 16:36] = True                   # a fin 1 mm thick standing on it
        shares = wall_check.thin_shares(solid, 0.25, walls=(1.5, 2.0, 3.5))["walls"]
        fin = 50 * 4 * 20 / solid.sum()
        # the whole fin, plus the plate's own edges, which no ball reaches into
        for key, edges in (("below_1.5_mm", 0.05), ("below_2_mm", 0.08)):
            self.assertGreaterEqual(shares[key]["share_of_volume"], fin - 0.005)
            self.assertLess(shares[key]["share_of_volume"], fin + edges)
        self.assertGreater(shares["below_3.5_mm"]["share_of_volume"], 0.95)


@unittest.skipUnless(has("numpy"), "numpy absent")
class BuildWitnessTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(SOURCE))
        import am_build
        import numpy as np

        self.ab, self.np = am_build, np

    def test_closed_form_gives_nominal_and_nodal_mixing_temperatures(self):
        rows = self.ab.expected(self.ab.WITNESS)
        self.assertEqual([r["volume_mm3"] for r in rows], [640.0, 1280.0, 1920.0])
        self.assertEqual([r["nominal_mean_K"] for r in rows], [300.0, 400.0, 433.333333])
        # New nodes at 500 K, interface nodes unchanged: half a cell row per layer arrives cold.
        self.assertEqual([r["nodal_mean_K"] for r in rows], [300.0, 375.0, 406.25])

    def test_judge_holds_outputs_to_the_closed_form(self):
        w = self.ab.WITNESS
        good = [{"time_s": 0.5, "volume_mm3": 640.0, "mean_temperature_K": 300.0, "min_temperature_K": 300.0, "max_temperature_K": 300.0},
                {"time_s": 1.0, "volume_mm3": 1280.0, "mean_temperature_K": 380.0, "min_temperature_K": 300.0, "max_temperature_K": 500.0},
                {"time_s": 5.5, "volume_mm3": 1280.0, "mean_temperature_K": 375.0, "min_temperature_K": 375.0, "max_temperature_K": 375.0},
                {"time_s": 11.0, "volume_mm3": 1920.0, "mean_temperature_K": 406.25, "min_temperature_K": 406.2, "max_temperature_K": 406.3}]
        verdict = self.ab.judge(good, w)
        self.assertTrue(verdict["passed"])
        self.assertEqual(verdict["heat_carried_by_a_layer_over_nominal"], 0.75)
        late = [dict(r) for r in good]
        late[2]["volume_mm3"] = 1920.0          # a layer that arrived too early
        self.assertFalse(self.ab.judge(late, w)["passed"])
        cold = [dict(r) for r in good]
        cold[3]["mean_temperature_K"] = 433.33  # the nominal value is not what a nodal solver gives
        self.assertFalse(self.ab.judge(cold, w)["passed"])
        # a solver that stops after the substrate has validated no deposition
        self.assertFalse(self.ab.judge(good[:1], w)["passed"])
        self.assertFalse(self.ab.judge(good[:3], w)["passed"])
        uneven = [dict(r) for r in good]
        uneven[2]["min_temperature_K"], uneven[2]["max_temperature_K"] = 370.0, 380.0   # not settled before the next layer
        self.assertFalse(self.ab.judge(uneven, w)["passed"])

    def test_a_solver_that_exits_with_an_error_fails_the_witness(self):
        held = {"verdict": {"passed": True}, "solver": {"returncode": 0}}
        self.assertTrue(self.ab.passed({"a": held, "b": held}))
        self.assertFalse(self.ab.passed({"a": held, "b": {"verdict": {"passed": True}, "solver": {"returncode": 1}}}))
        self.assertFalse(self.ab.passed({"a": held, "b": {"verdict": {"passed": True}, "solver": {}}}))
        self.assertFalse(self.ab.passed({}))

    def test_hex_mesh_of_a_block_counts_and_tags_the_base(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mesh.msh"
            got = self.ab.write_hex_mesh(path, self.np.ones((3, 2, 2), dtype=bool), (0.0, 0.0, 0.0), 2.0)
            self.assertEqual(got, {"hexahedra": 12, "nodes": 36, "exterior_faces": 32})
            lines = path.read_text().splitlines()
            quads = [l.split() for l in lines if len(l.split()) == 9 and l.split()[1] == "3"]
            self.assertEqual(sum(q[3] == "4" for q in quads), 6)        # the six faces of the lowest plane
            self.assertEqual(len(quads), 32)

    def test_committed_witness_passed_on_both_meshes(self):
        record = json.loads((TWIN / "params" / "am-build-witness.json").read_text())
        self.assertTrue(record["passed"])
        self.assertEqual(set(record["cases"]), {"built_in_mesh", "imported_mesh"})
        for case in record["cases"].values():
            verdict = case["verdict"]
            self.assertTrue(verdict["passed"])
            self.assertLessEqual(verdict["largest_volume_error_mm3"], record["case"]["tolerance_volume_mm3"])
            self.assertLessEqual(verdict["largest_mean_temperature_error_K"], record["case"]["tolerance_mean_temperature_K"])
            self.assertEqual(case["solver"]["returncode"], 0)
        self.assertEqual(len(record["found_on_the_way"]), 3)
        self.assertIn("no laser", record["claims"])


@unittest.skipUnless(has("numpy"), "numpy absent")
class BuildSimTests(unittest.TestCase):
    """The CalculiX build screen: its bookkeeping on synthetic input, then the committed records."""

    def setUp(self):
        sys.path.insert(0, str(SOURCE))
        import build_sim
        import numpy as np

        self.bs, self.np = build_sim, np
        self.case = json.loads((TWIN / "params" / "build-sim-case.json").read_text())

    def test_a_lump_takes_its_exposure_plus_its_recoating_and_absorbs_its_share(self):
        np = self.np
        mesh = {"pitch": np.float64(4.0), "rows_per_lump": np.int64(2), "kind": np.array([1, 2, 2, 3, 2]),
                "lump": np.array([-1, 0, 0, 0, 1]), "plate_rows": np.int64(1),
                "cells": np.array([[0, 0, 0], [0, 0, 1], [0, 0, 2], [1, 0, 1], [0, 0, 4]])}
        process, fraction = self.case["process"], self.case["supports"]["solid_fraction"]
        first, second = self.bs.schedule(mesh, self.case)
        melted = 2 * 64.0 + fraction * 64.0
        self.assertAlmostEqual(first["melted_mm3"], melted)
        self.assertAlmostEqual(first["real_layers"], 8.0 / process["layer_thickness_mm"])
        exposure = melted * process["volumetric_energy_density_J_mm3"] / (process["laser_power_W"] * process["lasers"])
        self.assertAlmostEqual(first["duration_s"], exposure + 160 * process["recoating_s_per_layer"])
        self.assertAlmostEqual(first["absorbed_J"], process["absorptivity"] * process["volumetric_energy_density_J_mm3"] * melted)
        self.assertAlmostEqual(second["melted_mm3"], 64.0)

    def test_rigid_motion_is_removed_and_a_bend_is_kept(self):
        np = self.np
        rng = np.random.default_rng(3)
        xyz = rng.uniform(-50.0, 50.0, (400, 3))
        spin = np.cross(np.array([1e-4, -2e-4, 3e-4]), xyz) + np.array([0.3, -0.1, 0.2])
        self.assertLess(np.abs(self.bs.remove_rigid(xyz, spin)).max(), 1e-9)
        bend = np.zeros_like(xyz)
        bend[:, 2] = 1e-4 * xyz[:, 0] ** 2
        left = self.bs.remove_rigid(xyz, spin + bend)
        self.assertGreater(np.abs(left).max(), 0.05)
        self.assertLess(np.abs(left - self.bs.remove_rigid(xyz, bend)).max(), 1e-9)

    def test_result_blocks_are_read_up_to_the_next_heading(self):
        import tempfile

        text = ("\n temperatures for set ALLN and time  0.1000000E+01\n\n         1  3.000000E+02\n         2  5.000000E+02\n"
                "\n                        S T E P       2\n\n\n temperatures for set ALLN and time  0.6000000E+01\n\n"
                "         1  3.750000E+02\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "w.dat"
            path.write_text(text)
            blocks = self.bs.dat_blocks(path, "temperatures for set ALLN", 2)
        self.assertEqual([t for t, _ in blocks], [1.0, 6.0])
        self.assertEqual(blocks[0][1].tolist(), [[1.0, 300.0], [2.0, 500.0]])
        self.assertEqual(blocks[1][1].tolist(), [[1.0, 375.0]])

    @unittest.skipUnless(has("scipy"), "scipy absent")
    def test_an_overhang_gets_columns_and_a_45_degree_step_does_not(self):
        import tempfile

        np = self.np
        # Twin axes x, y, z at 0.25 mm; the build runs along -y, so the plate is at the high-y end.
        # A post 8 x 8 mm, 24 mm tall, with a cap that steps out by one 4 mm cell (self-supporting)
        # on one side and by three cells on the other (two of them need a column).
        occ = np.zeros((128, 112, 64), dtype=np.float32)
        y = lambda lo, hi: slice(112 - int(hi / 0.25), 112 - int(lo / 0.25))
        occ[32:64, y(0, 24), 16:48] = 1.0                                   # the post: 2 x 2 cells, 6 cells tall
        occ[16:112, y(24, 28), 16:48] = 1.0                                 # the cap: 1 cell out at low x, 3 at high x
        case = json.loads(json.dumps(self.case))
        case["levels"] = {"t": {"cell_mm": 4.0, "cell_rows_per_lump": 1, "plate_margin_cells": 1,
                                "thermal_increments_per_lump": 2, "memory_cap": "1g"}}
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            np.save(tmp / "occupancy-wn.npy", occ)
            (tmp / "occupancy-grid.json").write_text(json.dumps({"pitch_mm": 0.25, "x0": 0.125, "y0": 0.125, "z0": 0.125,
                                                                   "shape": list(occ.shape), "array": "occupancy-wn.npy"}))
            (tmp / "case.json").write_text(json.dumps(case))
            self.bs.prepare(tmp, tmp / "case.json", "t", tmp / "run")
            report = json.loads((tmp / "run" / "prepare.json").read_text())
            mesh = np.load(tmp / "run" / "mesh.npz")
            kind, lump = mesh["kind"], mesh["lump"]
        self.assertEqual(report["lumps"], 7)
        self.assertEqual(report["hexahedra"]["part"], 2 * 2 * 6 + 6 * 2)
        # the two outer cells of the long side, 2 cells deep, on columns of 6 cells
        self.assertEqual(report["cells_needing_support"], 2 * 2)
        self.assertEqual(report["hexahedra"]["support"], 2 * 2 * 6)
        self.assertEqual(int((kind == 3).sum()), 24)
        self.assertEqual(sorted(set(lump[kind == 3].tolist())), [0, 1, 2, 3, 4, 5])
        self.assertTrue((lump[kind == 1] == -1).all())

    def test_witness_record_holds_the_closed_forms_and_keeps_the_pitfall(self):
        record = json.loads((TWIN / "params" / "build-sim-witness.json").read_text())
        self.assertTrue(record["passed"])
        outputs = record["thermal_activation_and_body_flux"]["outputs"]
        self.assertEqual([o["volume_mean_K"] for o in outputs[:3]], [300.0, 375.0, 406.25])
        last = record["bar_elastic"]["steps"][-1]["sxx_MPa_by_cell_row"]
        self.assertEqual([row[0] for row in last], [322.0, 322.0, 483.0, 805.0])
        self.assertEqual(record["bar_perfectly_plastic"]["steps"][-1]["von_mises_MPa"], [200.0, 200.0])
        # the bar whose new nodes were not prescribed is kept, and is wrong
        wrong = record["bar_new_nodes_not_prescribed"]["steps"][-1]["sxx_MPa_by_cell_row"]
        self.assertLess(wrong[-1][0], 200.0)
        self.assertNotIn("passed", record["bar_new_nodes_not_prescribed"])

    def test_record_is_the_committed_case_with_closed_gates_and_finished_solvers(self):
        import hashlib

        record = json.loads((TWIN / "params" / "build-sim.json").read_text())
        self.assertEqual(record["case_sha256"], hashlib.sha256((TWIN / "params" / "build-sim-case.json").read_bytes()).hexdigest())
        self.assertTrue(record["witnesses_passed"])
        self.assertFalse(any(record["gates"].values()))
        self.assertIn("qualifies no process", record["claims"])
        levels = record["levels"]
        self.assertIn("c4-l8", levels)
        self.assertLessEqual(set(levels), set(self.case["levels"]))
        process = self.case["process"]
        for name, level in levels.items():
            thermal, model = level["thermal"], level["model"]
            self.assertTrue(thermal["solver"]["job_finished"], name)
            self.assertEqual(thermal["solver"]["errors_in_log"], 0, name)
            self.assertEqual(thermal["solver"]["threads"], 1, name)
            self.assertLess(thermal["largest_energy_imbalance"], 0.01, name)
            self.assertEqual(len(thermal["lumps"]), model["lumps"], name)
            # the cells hold the volume of the occupancy they were made from, to the half-full rule:
            # +0.04%, -0.24% and +0.66% on 4, 3 and 2 mm cells (the README table prints each)
            self.assertLess(abs(model["part_volume_mm3"] / model["occupancy_volume_mm3"] - 1.0), 0.01, name)
            # absorbed energy is absorptivity x energy density x melted volume, supports included at their fraction
            fraction = model.get("support_solid_fraction", self.case["supports"]["solid_fraction"])
            melted = model["part_volume_mm3"] + fraction * model["support_envelope_mm3"]
            self.assertAlmostEqual(thermal["absorbed_MJ"], process["absorptivity"] * process["volumetric_energy_density_J_mm3"] * melted / 1e6, places=2)
            self.assertAlmostEqual(thermal["build_time_h"], thermal["exposure_h"] + thermal["recoating_h"], places=1)
            if "thermal_only" in self.case["levels"][name]:
                self.assertEqual(level["mechanics"], {}, name)
        # at the declared single laser the rise barely moves with the level; more lasers raise it and shorten the build
        one = [name for name in levels if "process" not in self.case["levels"][name]]
        rises = [levels[name]["thermal"]["largest_rise_over_plate_K"] for name in one]
        self.assertLess(max(rises) - min(rises), 5.0)
        base = levels["c4-l8"]["thermal"]
        previous = base
        for name in sorted((n for n in levels if "process" in self.case["levels"][n]), key=lambda n: self.case["levels"][n]["process"]["lasers"]):
            thermal = levels[name]["thermal"]
            lasers = self.case["levels"][name]["process"]["lasers"]
            self.assertAlmostEqual(thermal["exposure_h"], base["exposure_h"] / lasers, delta=0.02, msg=name)
            self.assertAlmostEqual(thermal["recoating_h"], base["recoating_h"], places=2, msg=name)
            self.assertGreater(thermal["largest_rise_over_plate_K"], previous["largest_rise_over_plate_K"], name)
            previous = thermal

    def test_a_short_last_lump_recoats_its_own_rows_and_a_level_may_declare_its_lasers(self):
        np = self.np
        # three cell rows above one plate row, two rows per lump: the second lump holds one row
        mesh = {"pitch": np.float64(4.0), "rows_per_lump": np.int64(2), "plate_rows": np.int64(1),
                "kind": np.array([1, 2, 2, 2]), "lump": np.array([-1, 0, 0, 1]),
                "cells": np.array([[0, 0, 0], [0, 0, 1], [0, 0, 2], [0, 0, 3]])}
        first, second = self.bs.schedule(mesh, self.case)
        self.assertAlmostEqual(first["real_layers"], 8.0 / self.case["process"]["layer_thickness_mm"])
        self.assertAlmostEqual(second["real_layers"], 4.0 / self.case["process"]["layer_thickness_mm"])
        two = {**self.case, "process": {**self.case["process"], "lasers": 2}}
        self.assertAlmostEqual(self.bs.schedule(mesh, two)[0]["exposure_s"], first["exposure_s"] / 2)
        self.assertAlmostEqual(self.bs.schedule(mesh, two)[0]["recoating_s"], first["recoating_s"])
        self.assertAlmostEqual(self.bs.schedule(mesh, two)[0]["absorbed_J"], first["absorbed_J"])
        for name, level in self.case["levels"].items():
            if "process" in level:
                self.assertEqual(set(level["process"]), {"lasers"}, name)
                self.assertIn(level["process"]["lasers"], (2, 4), name)

    def test_replay_script_runs_every_level_and_run_of_the_record(self):
        record = json.loads((TWIN / "params" / "build-sim.json").read_text())
        script = (TWIN / "source" / "run_twin.sh").read_text()
        loop = re.search(r"^for level in ([^;]+); do$", script, re.M).group(1).split()
        self.assertEqual(loop, list(self.case["levels"]))
        self.assertEqual(list(record["levels"]), list(self.case["levels"]))
        for name, level in record["levels"].items():
            for run in level["mechanics"]:
                variant = run.removeprefix("mechanics").removeprefix("-")
                line = f'mechanics "$BS/{name}"' + (f" --variant {variant}" if variant else "") + "\n"
                self.assertIn(line, script, run)

    def test_stress_stays_under_the_declared_yield_curve_and_variants_are_what_the_case_says(self):
        record = json.loads((TWIN / "params" / "build-sim.json").read_text())
        material, variants = self.case["material"], self.case["variants"]
        runs = record["levels"]["c4-l8"]["mechanics"]
        self.assertEqual(set(runs), {"mechanics"} | {"mechanics-" + name for name in variants})
        self.assertEqual(runs["mechanics"]["yield_MPa_by_temperature_C"], material["yield_MPa_by_temperature_C"])
        self.assertEqual(runs["mechanics-yield-stress-relieved"]["yield_MPa_by_temperature_C"],
                         variants["yield-stress-relieved"]["yield_MPa_by_temperature_C"])
        self.assertEqual(runs["mechanics-stress-free-673K"]["stress_free_temperature_K"], 673.15)
        for level in record["levels"].values():
            for name, run in level["mechanics"].items():
                self.assertTrue(run["solver"]["job_finished"], name)
                self.assertEqual(run["solver"]["errors_in_log"], 0, name)
                top = max(y for _, y in run["yield_MPa_by_temperature_C"])
                for state in run["states"].values():
                    # cell means cannot pass the yield curve by more than the declared hardening allows
                    self.assertLess(state["von_mises_MPa"]["cell_mean_p95"], top + 0.06 * material["hardening_modulus_MPa"], name)
                spread = run["release"]["distortion_after_release_rigid_motion_and_uniform_shrinkage_removed_mm"]
                self.assertLess(spread["median"], spread["p95"])
                self.assertLess(spread["p95"], spread["largest"])
                self.assertLess(run["release"]["best_fit_uniform_shrinkage"], 0.0)


@unittest.skipUnless(has("numpy", "scipy"), "numpy or scipy absent")
class SupportDesignTests(unittest.TestCase):
    """The support layout: its rules on small shapes, then the committed records."""

    RULES = {"critical_angle_from_plate_deg": 45.0, "self_supporting_width_mm": 2.0, "slenderness_limit": 20.0,
             "block_support": {"hatch_mm": 1.5, "wall_thickness_mm": 0.2, "tooth_contact_share_of_the_wall_line": 0.25}}

    def setUp(self):
        sys.path.insert(0, str(SOURCE))
        import numpy as np
        import support_design

        self.sd, self.np = support_design, np

    def grid(self, lo, hi, pitch=0.5):
        np = self.np
        return np.meshgrid(*[np.arange(a + pitch / 2, b, pitch) for a, b in zip(lo, hi)], indexing="ij")

    def test_a_cap_is_supported_from_the_plate_and_a_closed_cavity_is_hidden(self):
        x, y, z = self.grid((-22, -22, 0), (22, 22, 42))
        tee = ((abs(x) < 10) & (abs(y) < 10) & (z < 30)) | ((abs(x) < 20) & (abs(y) < 20) & (z > 30) & (z < 40))
        rep, kind = self.sd.layout(tee, 0.5, self.RULES)
        self.assertAlmostEqual(rep["supported"]["envelope_volume_mm3"], 36000.0, delta=0.03 * 36000.0)
        self.assertEqual(rep["supported"]["envelope_landing_on_part_mm3"], 0.0)
        self.assertEqual(rep["lateral_access"]["hidden_envelope_volume_mm3"], 0.0)
        self.assertEqual(rep["bodies"]["count"], 1)
        self.assertEqual(set(self.np.unique(kind)), {0, 1})
        share = 2 * 0.2 / 1.5 - (0.2 / 1.5) ** 2
        self.assertAlmostEqual(rep["block_support"]["melted_volume_mm3"], share * rep["supported"]["envelope_volume_mm3"])
        # walls every 1.5 mm in both directions: 2 / 1.5 mm of wall line per mm2, a quarter of it in contact
        self.assertAlmostEqual(rep["block_support"]["tooth_contact_line_on_the_part_mm"],
                               0.25 * rep["supported"]["projected_area_mm2"] * 2 / 1.5)

        box = (abs(x) < 20) & (abs(y) < 20) & (z < 40)
        box &= ~((abs(x) < 10) & (abs(y) < 10) & (z > 10) & (z < 20))
        box &= ~((abs(x) < 2) & (abs(y) < 2) & (z > 15))
        rep, kind = self.sd.layout(box, 0.5, self.RULES)
        self.assertAlmostEqual(rep["supported"]["envelope_volume_mm3"], 3840.0, delta=0.03 * 3840.0)
        self.assertEqual(rep["supported"]["envelope_landing_on_plate_mm3"], 0.0)
        self.assertEqual(rep["lateral_access"]["hidden_share_of_the_envelope"], 1.0)
        self.assertEqual(set(self.np.unique(kind)), {0, 6})

    def test_a_narrow_ledge_is_left_bare_and_a_narrow_island_keeps_its_support(self):
        x, y, z = self.grid((-12, 0, 0), (12, 40, 32))
        wall = (abs(x) < 5) & (z < 30)
        wall |= (x > 0) & (x < 6.5) & (z > 20) & (z < 24)        # a ledge of 1.5 mm, under the 2 mm of the rule
        wall |= (x < 0) & (x > -9) & (z > 20) & (z < 24)         # a ledge of 4 mm
        rep, _ = self.sd.layout(wall, 0.5, self.RULES)
        self.assertEqual(rep["exemption"]["patches_left_bare"], 1)
        self.assertAlmostEqual(rep["supported"]["projected_area_mm2"], 160.0, delta=8.0)
        without = {**self.RULES, "self_supporting_width_mm": None}
        self.assertGreater(self.sd.layout(wall, 0.5, without)[0]["supported"]["projected_area_mm2"],
                           rep["supported"]["projected_area_mm2"] + 40.0)

        x, y, z = self.grid((-20, 0, 0), (20, 40, 36))
        hung = (abs(x) < 20) & (z > 30) & (z < 34)
        hung |= (abs(x) > 16) & (z < 34)
        hung |= (abs(x) < 0.75) & (z > 20) & (z < 34)            # a blade 1.5 mm thick hanging under the slab
        rep, _ = self.sd.layout(hung, 0.5, self.RULES)
        self.assertEqual(rep["exemption"]["narrow_patches_kept_as_island_starts"], 1)
        self.assertEqual(rep["exemption"]["patches_left_bare"], 0)

    def test_committed_layout_follows_its_case_and_the_orientation_screen(self):
        case = json.loads((TWIN / "params" / "support-design-case.json").read_text())
        witness = json.loads((TWIN / "params" / "support-design-witness.json").read_text())
        record = json.loads((TWIN / "params" / "support-design.json").read_text())
        rules = case["rules"]
        self.assertTrue(witness["passed"])
        self.assertLessEqual(witness["largest_relative_error"], witness["tolerance_relative"])
        digest = hashlib.sha256(json.dumps(rules, sort_keys=True).encode()).hexdigest()
        self.assertEqual(witness["rules_sha256"], digest)
        self.assertEqual(record["case_sha256"], hashlib.sha256((TWIN / "params" / "support-design-case.json").read_bytes()).hexdigest())
        self.assertFalse(any(record["gates"].values()))
        check = record["check_against_the_orientation_screen"]
        self.assertTrue(check["agrees_within_0p1_percent"])
        sup, block = record["supported"], record["block_support"]
        self.assertAlmostEqual(sup["envelope_landing_on_plate_mm3"] + sup["envelope_landing_on_part_mm3"], sup["envelope_volume_mm3"], places=3)
        self.assertLessEqual(sup["envelope_volume_mm3"], record["before_exemption"]["air_column_volume_mm3"])
        self.assertAlmostEqual(block["melted_share_of_the_envelope"], self.sd.block_fraction(rules), places=4)
        self.assertAlmostEqual(block["melted_volume_mm3"], self.sd.block_fraction(rules) * sup["envelope_volume_mm3"], delta=1.0)
        self.assertLessEqual(record["lateral_access"]["hidden_envelope_volume_mm3"], sup["envelope_volume_mm3"])
        # every rule names where its value comes from
        for key, value in rules.items():
            if key != "block_support":
                self.assertIn(key, case["sources"], key)
        for key in rules["block_support"]:
            self.assertIn(key, case["sources"]["block_support"], key)
        # the occupancy is the one the build screen was prepared on
        build = json.loads((TWIN / "params" / "build-sim.json").read_text())
        self.assertEqual(record["occupancy_sha256"], build["levels"]["c4-l8"]["model"]["occupancy_sha256"])


class PreparedWorkTests(unittest.TestCase):
    """The register of the parts that never ran, and the witness of the drawing tool."""

    def test_register_names_four_parts_and_only_files_that_exist(self):
        register = json.loads((TWIN / "params" / "prepared-work.json").read_text())
        parts = {part["id"]: part for part in register["parts"]}
        self.assertEqual(set(parts), {"port-flow", "fatigue", "valve-train", "drawing"})
        self.assertIn("nothing here is a result", register["scope"])
        for rule in ("contributed_measurements", "what_a_ct_request_must_require", "safety"):
            self.assertTrue((ROOT / register["rules"][rule]).exists(), rule)
        for name, part in parts.items():
            self.assertTrue(part["missing"] and part["held"] and part["first_steps_once_unblocked"], name)
            self.assertTrue(part["a_contribution_must_hold"], name)
            self.assertTrue(any("licence" in item for item in part["a_contribution_must_hold"]), name)
            self.assertTrue((ROOT / part["tool"]["witness"]).exists(), name)
            for held in part["held"]:
                self.assertTrue((ROOT / held["where"]).exists(), held["where"])
        # the count of confirmed features is the feature check's
        check = json.loads((TWIN / "params" / "feature-check.json").read_text())
        confirmed = [row["id"] for row in check["regions"] if row["confirmed"]]
        self.assertIn(f"{len(confirmed)} features confirmed", parts["drawing"]["held"][0]["what"])
        for name in confirmed:
            self.assertIn(name, parts["drawing"]["held"][0]["what"])
        # the load-case contracts it points to still have empty inputs
        contracts = json.loads((ROOT / "twins/engine-simulation-contracts/load-cases-f1.json").read_text())
        cases = {case["load_case_id"]: case for case in contracts["load_cases"]}
        for case_id in ("LC-935-PORT-COLD-FLOW", "LC-993-VALVE-DYNAMIC-CYCLE"):
            self.assertTrue(any(value is None for value in cases[case_id]["required_inputs"].values()), case_id)

    def test_drawing_witness_read_back_every_view(self):
        witness = json.loads((TWIN / "params" / "drawing-witness.json").read_text())
        self.assertTrue(witness["passed"])
        self.assertTrue(all(check["passed"] for check in witness["checks"]))
        self.assertEqual({name: view["size_mm"] for name, view in witness["views"].items()},
                         {"top": [60.0, 40.0], "front": [60.0, 20.0], "side": [40.0, 20.0]})
        self.assertIn("no tool assignment", witness["scope"])
        self.assertIn("dimension and tolerance annotations", witness["not_checked"])
        # hidden edges are kept on their own layer in every view
        for name, view in witness["views"].items():
            self.assertTrue(any(key.startswith("hidden:") for key in view["entities"]), name)

    def test_a_segment_is_found_only_when_collinear_pieces_cover_it(self):
        sys.path.insert(0, str(SOURCE))
        import drawing_witness as dw

        lines = [(4.0, 0.0, 4.0, 8.0), (4.0, 8.0, 4.0, 20.0), (0.0, 12.0, 30.0, 12.0)]
        self.assertTrue(dw.has_line(lines, 4, 0, 4, 20))
        self.assertTrue(dw.has_line(lines, 5, 12, 25, 12))
        self.assertFalse(dw.has_line(lines[:1], 4, 0, 4, 20))
        self.assertFalse(dw.has_line(lines, 16, 0, 16, 20))


class MediaTests(unittest.TestCase):
    def test_public_images_match_their_provenance_and_stay_small(self):
        import hashlib

        media = TWIN / "media"
        record = json.loads((media / "provenance.json").read_text())
        self.assertEqual(record["scan_sha256"], SCAN_SHA256)
        self.assertIn("#462", record["scan_licence"])
        self.assertIn("no geometry file", record["kind"])
        for name, entry in record["images"].items():
            data = (media / name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"], name)
            self.assertLess(len(data), 1 << 20, name)
        readme = (TWIN / "README.md").read_text()
        for name in record["images"]:
            self.assertIn(f"](media/{name})", readme)


class AlloyRecordTests(unittest.TestCase):
    """The committed alloy candidates, both rankings and the surveys."""

    def load(self, name):
        return json.loads((TWIN / "params" / name).read_text())

    def test_every_candidate_names_a_source_and_how_far_it_was_verified(self):
        cand = self.load("alloy-candidates.json")
        for row in cand["candidates"]:
            self.assertTrue(row["verification"] and row["method"], row["id"])
            if row["source"] != "none":
                self.assertTrue(cand["sources"][row["source"]]["url"].startswith("https://"), row["id"])
        self.assertEqual(len({r["id"] for r in cand["candidates"]}), len(cand["candidates"]))

    def test_bare_head_ranking_is_monotonic_bounded_and_reproduces_the_cad_screen(self):
        rank = self.load("alloy-thermal.json")["ranking_by_heat_rejected"]
        by_k = sorted({(r["conductivity_W_per_mK"], r["heat_W"], r["fin_efficiency"]) for r in rank})
        heats = [h for _, h, _ in by_k]
        self.assertEqual(heats, sorted(heats))
        self.assertTrue(all(0.0 < e < 1.0 for _, _, e in by_k))
        self.assertTrue(all(r["relative_imbalance"] < 0.005 for r in rank))
        cad = self.load("thermal-screen-cad.json")["level"]["energy_balance"]["chamber_inflow_W"]
        self.assertAlmostEqual(next(h for k, h, _ in by_k if k == 150.0), cad, places=2)

    def test_assembly_variants_cool_with_conductivity_and_conserve_energy(self):
        asm = self.load("assembly-thermal.json")
        case = self.load("assembly-case.json")
        self.assertFalse(asm["exploratory_single_variant"])
        self.assertEqual(set(asm["variants"]), {v["id"] for v in case["variants"]})
        solved = {c["conductivity_W_per_mK"] for c in self.load("alloy-candidates.json")["candidates"]}
        for name, variant in asm["variants"].items():
            rows = sorted(variant["by_conductivity"], key=lambda r: r["alloy_conductivity_W_per_mK"])
            self.assertGreaterEqual(len(rows), 3, name)
            self.assertLessEqual({r["alloy_conductivity_W_per_mK"] for r in rows}, solved, name)
            for zone in ("alloy", "valve_bridge"):
                peaks = [r["peak_C"][zone] for r in rows]
                self.assertEqual(peaks, sorted(peaks, reverse=True), (name, zone))
            for r in rows:
                self.assertLess(r["energy_imbalance_relative"], 1e-3)
                self.assertLess(r["heat_out_W_by_group"]["chamber_gas"], 0.0)       # gas heats the assembly
                self.assertGreater(r["heat_out_W_by_group"]["air"], 0.0)            # air cools it
                self.assertGreater(r["valve_peak_C"]["exhaust"], r["valve_peak_C"]["inlet"])
        ranking = asm["variants"][asm["ranking_variant"]]
        self.assertEqual({r["alloy_conductivity_W_per_mK"] for r in ranking["by_conductivity"]}, solved)
        self.assertEqual({r["alloy_conductivity_W_per_mK"] for r in asm["ranking_by_peak_alloy_temperature"]}, solved)
        self.assertTrue(all(n > 100 for n in asm["zone_nodes"].values()))
        self.assertIn("hypothesis", asm["claims"])
        ids = {i["id"][:3] for i in json.loads((TWIN / "hypotheses.json").read_text())["items"]}
        self.assertTrue({"H09", "H10", "H11", "H12"} <= ids)

    def test_a_calibrated_variant_carries_its_target_wall_loading_at_the_reference_conductivity(self):
        asm = self.load("assembly-thermal.json")
        reference = self.load("assembly-case.json")["reference_conductivity_W_per_mK"]
        calibrated = {name: v for name, v in asm["variants"].items() if v["calibration"]}
        self.assertTrue(calibrated)
        for name, variant in calibrated.items():
            row = next(r for r in variant["by_conductivity"] if r["alloy_conductivity_W_per_mK"] == reference)
            for group in ("chamber_gas", "hot_port"):
                target = variant["calibration"][-1][group]["target_kW_per_m2"]
                self.assertAlmostEqual(row["wall_loading_kW_per_m2"][group] / target, 1.0, delta=0.02, msg=(name, group))
                # the film the solves used is the last scaled one, not the declared start
                self.assertGreater(variant["films"][group]["coefficient_W_per_m2K"],
                                   variant["calibration"][0][group]["coefficient_W_per_m2K"])
        # an uncalibrated variant keeps its declared films: no oil film means none
        self.assertIsNone(asm["variants"]["declared"]["films"]["oil"])
        self.assertEqual(asm["variants"]["declared"]["calibration"], [])

    def test_strength_rows_name_their_source_and_the_tradeoff_selects_nothing(self):
        strength = self.load("alloy-strength.json")
        ids = {c["id"] for c in self.load("alloy-candidates.json")["candidates"]}
        for row in strength["rows"]:
            self.assertTrue(row["source"] and row["verification"] and row["condition_match"], row["id"])
            self.assertLessEqual(set(row["conductivity_rows"]), ids, row["id"])
            self.assertTrue(row["yield_MPa_by_temperature_C"], row["id"])
        trade = self.load("alloy-tradeoff.json")
        asm = self.load("assembly-thermal.json")
        self.assertEqual(trade["ranking_variant"], asm["ranking_variant"])
        self.assertEqual([r["id"] for r in trade["rows"]], [r["id"] for r in strength["rows"]])
        peaks = [r["peak_C"]["alloy"] for r in asm["variants"][asm["ranking_variant"]]["by_conductivity"]]
        for row in trade["rows"]:
            if row["peak_head_alloy_C"] is None:
                self.assertIn("no conductivity", row["hot_yield_status"])
                continue
            self.assertTrue(set(row["peak_head_alloy_C"]) <= set(peaks), row["id"])
            # every computed peak lies beyond the published strength of its alloy: nothing is extrapolated
            self.assertGreater(row["peak_head_alloy_C"][0], row["yield_MPa_published_up_to_C"], row["id"])
            self.assertIsNone(row["yield_MPa_at_the_computed_peak"], row["id"])
        self.assertIn("no alloy", trade["claims"])
        self.assertIn("never extrapolated", trade["rule"])
        self.assertTrue((TWIN / "media" / "alloy-ranking.png").stat().st_size < (1 << 20))

    def test_surveys_say_what_was_not_found(self):
        self.assertTrue(self.load("thermal-literature-bounds.json")["not_found"])
        machines = self.load("lpbf-machine-survey.json")
        self.assertTrue(machines["not_published_by_any_maker_read"])
        self.assertIn("not a calibration", self.load("published-993-comparison.json")["verdict"])


class SimReadyAssetTests(unittest.TestCase):
    """export_simready.py on a synthetic stage, and the committed asset records."""

    @unittest.skipUnless(has("numpy", "pxr", "trimesh"), "numpy/usd-core/trimesh absent")
    def test_asset_adds_collider_material_and_package_without_touching_geometry(self):
        import tempfile

        import trimesh
        from pxr import Sdf, Usd, UsdGeom, Vt

        sys.path.insert(0, str(SOURCE))
        import export_simready

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            box = trimesh.creation.box(extents=(20.0, 30.0, 10.0))
            stage = Usd.Stage.CreateNew(str(tmp / "cad.usdc"))
            UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
            UsdGeom.SetStageMetersPerUnit(stage, 0.001)
            root = UsdGeom.Xform.Define(stage, "/Head935")
            stage.SetDefaultPrim(root.GetPrim())
            Usd.ModelAPI(root.GetPrim()).SetKind("component")
            root.GetPrim().SetCustomDataByKey("porscheparts:claims", "synthetic")
            mesh = UsdGeom.Mesh.Define(stage, "/Head935/BareHead")
            mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(box.vertices.astype("float32")))
            mesh.CreateFaceVertexCountsAttr([3] * len(box.faces))
            mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(box.faces.astype("int32").ravel()))
            mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
            mesh.CreateExtentAttr([(-10, -15, -5), (10, 15, 5)])
            mesh.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(box.face_normals.astype("float32")))
            mesh.SetNormalsInterpolation(UsdGeom.Tokens.uniform)
            UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("displayColor", Sdf.ValueTypeNames.Color3fArray,
                                                    UsdGeom.Tokens.constant).Set([(0.7, 0.7, 0.7)])
            stage.GetRootLayer().Save()
            box.export(tmp / "collider.stl")

            # usd-core 25 cannot resolve the preview shaders: its registry rule fires on any
            # UsdPreviewSurface and its shader discovery can raise. The validators are
            # exercised from OpenUSD 26 on; everything else is checked on both.
            import contextlib
            from unittest import mock

            legacy = Usd.GetVersion() < (0, 26, 0)
            stub = {"validators_run": 0, "findings_by_type": {}, "error_count": 0}
            with (mock.patch.object(export_simready, "findings", return_value=stub) if legacy
                  else contextlib.nullcontext()):
                export_simready.main(tmp / "cad.usdc", tmp / "collider.stl", tmp / "asset", tmp / "summary.json")
            got = json.loads((tmp / "summary.json").read_text())
            self.assertTrue(got["geometry_layer_is_source_stage"])
            self.assertTrue(got["package_reads_back_identically"])
            self.assertAlmostEqual(got["collider_volume_over_render_volume"], 1.0, places=4)
            st = got["stage"]
            self.assertEqual((st["default_prim"], st["up_axis"], st["meters_per_unit"]), ("/Head935", "Z", 0.001))
            self.assertEqual((st["collider_purpose"], st["collider_approximation"]), ("guide", "convexDecomposition"))
            self.assertTrue(st["collider_has_collision_api"])
            self.assertEqual(st["gprims_with_bound_material"], 1)
            self.assertFalse(st["rigid_body_or_mass_authored"])
            for name in ("part.usda", "part.usdz"):
                self.assertEqual(got["openusd_validation"][name]["error_count"], 0, name)
                self.assertEqual(got["openusd_validation"][name]["validators_run"] > 0, not legacy)
            package = Usd.Stage.Open(str(tmp / "asset" / "part.usdz"))
            self.assertEqual(package.GetDefaultPrim().GetCustomDataByKey("porscheparts:claims"), "synthetic")
            del package
            with self.assertRaises(SystemExit):
                export_simready.main(tmp / "cad.usdc", tmp / "collider.stl", tmp / "asset", tmp / "again.json")

    def test_committed_asset_record_is_consistent_and_claims_no_physics(self):
        params = TWIN / "params"
        asset = json.loads((params / "simready-asset.json").read_text())
        st = asset["stage"]
        self.assertTrue(asset["geometry_layer_is_source_stage"] and asset["package_reads_back_identically"])
        self.assertEqual(st["render_triangles"], json.loads((params / "usd-cad-summary.json").read_text())["surface_triangles"])
        self.assertEqual((st["up_axis"], st["meters_per_unit"], st["kilograms_per_unit"]), ("Z", 0.001, 1.0))
        self.assertTrue(st["collider_has_collision_api"])
        self.assertFalse(st["rigid_body_or_mass_authored"])
        self.assertAlmostEqual(asset["collider_volume_over_render_volume"], 1.0, delta=0.001)
        self.assertIn("no physics was run", asset["claims"])
        for name in ("part.usda", "part.usdz"):
            self.assertEqual(asset["openusd_validation"][name]["error_count"], 0)
            nvidia = json.loads((params / f"simready-validate-asset-{name[-4:]}.json").read_text())
            self.assertEqual(nvidia["stage_input"]["sha256"], asset["files"][name]["sha256"])
            severity = nvidia["stage_input"]["validation"]["issues_by_severity"]
            self.assertEqual((severity["FAILURE"], severity["ERROR"]), (0, 0))
            # The two warnings are the ones the CAD stage already carries; the asset adds none.
            self.assertEqual(sorted(r["rule"] for r in nvidia["stage_input"]["validation"]["rules_with_issues"]),
                             ["WeldChecker", "ZeroAreaFaceChecker"])
        body = json.loads((params / "v2-body-visual-check.json").read_text())
        self.assertFalse(body["strict_gate_passed"])
        self.assertTrue(body["as_built"]["watertight"])
        self.assertEqual(body["as_built"]["triangles"], st["render_triangles"])
        # The stud repair must have removed what the first reading saw.
        self.assertLess(body["readings"][-1]["top_of_the_body_mm"], body["readings"][0]["top_of_the_body_mm"] - 15.0)
        occ = json.loads((params / "occupancy-summary.json").read_text())
        self.assertGreater(sum(x.get("removed_facets_beyond_the_cylinder", 0) for x in occ["studs"]), 8000)


@unittest.skipUnless(has("numpy"), "numpy absent")
class ScorecardTests(unittest.TestCase):
    @unittest.skipUnless(has("warp", "trimesh"), "warp/trimesh absent")
    def test_warp_distances_match_analytic_cube(self):
        import numpy as np
        import trimesh

        sys.path.insert(0, str(SOURCE))
        import score_twin

        box = trimesh.creation.box(extents=(10, 10, 10))
        pts = np.array([[0, 0, 7.0], [0, 0, 5.0], [8.0, 0, 0], [0, 0, 0]])
        d = score_twin.warp_distances(pts, np.asarray(box.vertices), np.asarray(box.faces))
        np.testing.assert_allclose(d, [2.0, 0.0, 3.0, 5.0], atol=1e-5)

    def test_hardware_mask_takes_the_whole_rod_cluster_above_its_fit_height(self):
        import numpy as np

        sys.path.insert(0, str(SOURCE))
        import score_twin

        rod = {"axis": [0, 0, 1.0], "point_on_axis": [0, 0, 30.0], "base_point": [0, 0, 10.0], "radius_mm": 3.5,
               "protrusion_mm": 50.0, "radial_residual": {"rms_mm": 0.7, "max_mm": 3.0}}
        frame = {"rods": {"beyond_cam_face": [rod]}}
        cen = np.array([
            [4.0, 0, 12.0],    # within 0.8 mm of the cylinder, just above the base: hardware
            [5.5, 0, 12.0],    # a boss beside the base, below the fit height: head
            [5.5, 0, 30.0],    # a smeared shell of the stud above the fit height: hardware
            [6.6, 0, 30.0],    # outside the cluster envelope (3.5 + 3.0 + 0.05): head
            [5.5, 0, 15.9],    # still below base + 6 mm: head
        ])
        self.assertEqual(score_twin.hardware_mask(cen, frame).tolist(), [True, False, True, False, False])
        rod["protrusion_mm"] = 8.0          # too short to be accepted as a stud: nothing is removed
        self.assertFalse(score_twin.hardware_mask(cen, frame).any())

    def test_weighted_percentiles_follow_area(self):
        import numpy as np

        sys.path.insert(0, str(SOURCE))
        import score_twin

        d = np.array([0.0, 1.0])
        w = np.array([99.0, 1.0])
        self.assertEqual(score_twin.weighted_percentiles(d, w, (95,))["p95"], 0.0)


if __name__ == "__main__":
    unittest.main()
