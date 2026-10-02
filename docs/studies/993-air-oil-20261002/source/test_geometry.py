"""Independent design-intent checks; no engine or process qualification."""
import copy
import json
import math
import unittest
from pathlib import Path

import build


class DesignIntentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = json.loads(Path(__file__).with_name("parameters.json").read_text())

    def test_connected_coupon_and_analytic_volume(self):
        body, fluid, length, walls = build.coupon_build(self.p["coupon"])
        self.assertTrue(body.is_valid)
        self.assertTrue(fluid.is_valid)
        self.assertEqual(len(body.solids()), 1)
        self.assertEqual(len(fluid.solids()), 1)
        r = self.p["coupon"]["gallery_radius"]
        # Independently derive the profile: circle minus the top circular
        # segment plus the triangle between the two tangent roof planes.
        area = math.pi * r * r - (math.pi * r * r / 4 - r * r / 2) + r * r / 2
        self.assertAlmostEqual(fluid.volume / (area * length), 1, places=7)
        self.assertGreaterEqual(min(walls.values()), 5)
        self.assertAlmostEqual(body.volume + fluid.volume, 100 * 50 * 24, places=4)

    def test_thin_coupon_is_rejected(self):
        p = copy.deepcopy(self.p["coupon"])
        p["height"] = 15
        with self.assertRaisesRegex(ValueError, "ligament"):
            build.coupon_build(p)

    def test_stand_has_two_open_bore_ends(self):
        s = build.stand_build(self.p["valve_stand"])
        self.assertTrue(s.is_valid)
        self.assertEqual(len(s.solids()), 1)
        for z in [0.1, 5.1, 18.9]:
            self.assertFalse(s.solids()[0].is_inside((0, 0, z)))
            self.assertTrue(s.solids()[0].is_inside((10, 0, z)))

    def test_hydraulics_preserves_energy_and_viscosity_sensitivity(self):
        _, length = build.gallery_y(self.p["head"])
        report = build.hydraulic_screen(self.p["hydraulic_screen"], length, 3)
        rows = report["cases"]
        for row in rows:
            self.assertLess(row["Re"], 2300)
        at_one = [r for r in rows if r["flow_L_min"] == 1]
        self.assertAlmostEqual(at_one[2]["friction_pressure_drop_bar"] / at_one[0]["friction_pressure_drop_bar"], 5, places=10)
        self.assertAlmostEqual(at_one[0]["enthalpy_transport_capacity_W_at_assumed_delta_T"], 566.6666666667)
        self.assertIsNone(report["heat_removed_from_head_W"])

    def test_no_geometry_check_grants_engine_release(self):
        for key, value in self.p["release"].items():
            self.assertIs(value, False, key)


if __name__ == "__main__":
    unittest.main(verbosity=2)
