"""Le fond incliné d'un logement de ressort doit rester entièrement sous la face."""
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FV = ROOT / 'twins/m64-cylinder-head/source/fourvalve'
sys.path[:0] = [str(FV), str(FV / 'cad')]

import checks
import layout

try:
    import cadquery as cq
except ImportError:
    cq = None


def parameters():
    path = ROOT / 'twins/m64-cylinder-head/evidence/g2-head-features-20260916/parameters-resolved.json'
    return {k: row['value'] for k, row in json.loads(path.read_text()).items()}


class SpringFloorTests(unittest.TestCase):
    def test_centre_below_face_is_not_enough_and_lowering_floor_restores_check(self):
        p = parameters()
        centres = [layout.head_centre(p, s, 1)[2] + layout.axis_up(p, s)[2] * p[f'{s}_spring_seat_axial']
                   for s in layout.SIDES]
        self.assertLess(max(centres), p['carrier_face_height'])
        row = next(c for c in checks.static_checks(p) if c['check'] == 'spring_seat_below_carrier_face')
        expected = max(z + p['spring_pocket_diameter'] / 2 * abs(math.sin(math.radians(p[f'{s}_axis_angle'])))
                       for z, s in zip(centres, layout.SIDES))
        self.assertAlmostEqual(row['value'], expected, places=3)
        self.assertFalse(row['passed'])
        self.assertTrue(row['blocking'])
        for s in layout.SIDES:
            p[f'{s}_spring_seat_axial'] -= 10
        row = next(c for c in checks.static_checks(p) if c['check'] == 'spring_seat_below_carrier_face')
        self.assertTrue(row['passed'])

    @unittest.skipUnless(cq, 'cadquery absent')
    def test_disk_extent_matches_native_brep_for_both_sides(self):
        p = parameters()
        for s in layout.SIDES:
            u = layout.axis_up(p, s)
            c = layout.head_centre(p, s, 1) + u * p[f'{s}_spring_seat_axial']
            r = p['spring_pocket_diameter'] / 2
            disk = cq.Face.makeFromWires(cq.Wire.makeCircle(r, cq.Vector(*c), cq.Vector(*u)))
            self.assertAlmostEqual(disk.BoundingBox().zmax, c[2] + r * math.hypot(*u[:2]), places=6)

    @unittest.skipUnless(cq, 'cadquery absent')
    def test_pocket_tool_exits_the_face_and_spring_does_not_penetrate_head(self):
        import components as comp
        p = parameters()
        # Configuration issue de la recherche bornée G4, sans bouger le gabarit ni les goujons.
        fixed = {k: p[k] for k in layout.DERIVED if k not in
                 ('roof_ridge_height', 'intake_spring_seat_axial', 'exhaust_spring_seat_axial')}
        fixed.update(intake_axis_angle=29.3758, exhaust_axis_angle=27.5536,
                     intake_valve_x=-18.0421, exhaust_valve_x=22.7754, valve_length_delta=14.4301)
        p = layout.derive(p, fixed)
        head = comp.head(p)
        for s, sy in layout.VALVES:
            u = layout.axis_up(p, s)
            _, end, r = layout.cylinders(p)[f'pocket_{s}_{"p" if sy > 0 else "m"}']
            self.assertGreater(end[2] - r * math.hypot(*u[:2]), p['carrier_face_height'])
            for lift in (0, p[f'{s}_max_lift']):
                self.assertLess(abs(comp.spring(p, s, sy, lift).intersect(head).Volume()), 1e-6)


if __name__ == '__main__':
    unittest.main()
