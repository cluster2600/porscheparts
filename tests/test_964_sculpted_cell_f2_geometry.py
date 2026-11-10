"""Geometry-contract controls for the explicitly hypothetical F2 cell."""
import importlib.util
import json
from pathlib import Path
import unittest

from _deps import require_modules

require_modules("numpy")
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "twins/964-chassis/sculpted-cell-f2-20261106"


def module(name):
    spec = importlib.util.spec_from_file_location("f2_geometry_test_"+name, STUDY/(name+".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


geometry, clearance = module("geometry"), module("audit_wheel_clearance")


class SculptedGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parameters = json.loads((STUDY/"parameters.json").read_text())
        cls.model = geometry.build(cls.parameters)
        cls.components = {c["name"]: c for c in cls.model["components"]}

    def test_sill_outer_bottom_keeps_flat_load_line_independent_of_rear_floor(self):
        self.assertGreater(self.parameters["floor_base_z_mm"][-1], 300)
        for side in ("left", "right"):
            sill = self.components["sill_"+side]
            heights = [geometry.evaluate(sill, u, sill['profile_landmarks']['outer_lower_corner'])[2] for u in np.linspace(0, len(sill["sections_mm"])-1, 49)]
            self.assertLess(max(heights)-min(heights), 1e-9)

    def test_end_closures_are_planar_and_share_the_complete_parent_profile(self):
        caps = [c for c in self.components.values() if c["type"] == "planar_profile_cap"]
        self.assertTrue(caps)
        for cap in caps:
            parent = self.components[cap["boundary_loft_name"]]
            index = 0 if cap["boundary_end"] == "start" else -1
            np.testing.assert_array_equal(cap["profile_mm"], parent["sections_mm"][index])
            points, normal = np.asarray(cap["profile_mm"]), np.asarray(cap["normal_direction"])
            self.assertAlmostEqual(np.linalg.norm(normal), 1.)
            self.assertLess(np.max(np.abs((points-points[0])@normal)), 1e-9)

    def test_floor_tunnel_partition_preserves_shared_positions_and_tangents(self):
        tunnel = self.components["integrated_tunnel"]
        for name, boundary in (("floor_bay_right", 3), ("floor_bay_left", 11)):
            floor = self.components[name]
            self.assertIn(boundary, floor["v_range"])
            for u in (0., .7, 4.3, 8.2, 12.):
                np.testing.assert_allclose(geometry.evaluate(floor, u, boundary),
                                           geometry.evaluate(tunnel, u, boundary), atol=1e-10)
                np.testing.assert_allclose(geometry.tangent(floor, u, boundary, 1),
                                           geometry.tangent(tunnel, u, boundary, 1), atol=1e-10)

    def test_declared_load_regions_and_junctions_refer_to_actual_named_surfaces(self):
        fixture = self.model["fixture_contract"]
        self.assertEqual(set(fixture["bending_components"]), {"floor_bay_left", "floor_bay_right"})
        for join in self.model["join_contract"]:
            self.assertIn(join["component_a"], self.components)
            self.assertIn(join["component_b"], self.components)
        for side in ("left", "right"):
            targets = {j["component_b"] for j in self.model["join_contract"]
                       if j["component_a"] == "rear_brace_"+side}
            self.assertEqual(targets, {"upper_side_"+side, "rear_shoulder_return"})
        self.assertFalse(self.model["physical_interfaces_admitted"])
        self.assertFalse(self.model["manufacturing_authorized"])

    def test_triangle_cylinder_screen_detects_a_face_crossing_with_no_inside_vertices(self):
        face = [[-2., 0., -2.], [2., 0., -2.], [0., 0., 2.]]
        self.assertTrue(all(p[0]**2+p[2]**2 > 1 for p in face))
        self.assertEqual(clearance.minimum_radius(face, [0., 0., 0.], .5), 0.)
        self.assertIsNone(clearance.minimum_radius([[x, 2., z] for x, _, z in face], [0., 0., 0.], .5))

    def test_nominal_front_and_rear_tyres_share_the_declared_assumed_ground(self):
        package = self.parameters['assembly_proxy_parameters']
        axles = {a['id']: a for a in package['axles']}
        for name, width, aspect, track in [('front', 205, .55, 1380), ('rear', 225, .50, 1374)]:
            axle = axles[name]
            self.assertAlmostEqual(axle['tyre_outer_radius_mm'], 16*25.4/2+width*aspect)
            self.assertAlmostEqual(axle['centre_z_mm']-axle['tyre_outer_radius_mm'], package['ground_z_mm'])
            self.assertAlmostEqual(2*axle['half_track_mm'], track)


if __name__ == "__main__":
    unittest.main()
