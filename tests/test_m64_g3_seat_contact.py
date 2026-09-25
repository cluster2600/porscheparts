"""Portées concordantes candidates : contact, dégagement et témoins de chambre ouverte."""
import json
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FV = ROOT / 'twins/m64-cylinder-head/source/fourvalve'
sys.path[:0] = [str(FV), str(FV / 'cad')]

import layout
import provenance

try:
    import cadquery as cq
    import assembly
    import components as comp
except ImportError:
    cq = None


def parameters():
    path = ROOT / 'twins/m64-cylinder-head/evidence/g2-head-features-20260916/parameters-resolved.json'
    p = {k: row['value'] for k, row in json.loads(path.read_text()).items()}
    for name in ('params-plugs/spark_plug_envelope.json', 'params-seats/seat_contact.json'):
        for k, row in json.loads((FV / name).read_text())['parameters'].items():
            provenance.verify_provenance(k, row, {})
            p[k] = row['value']
    return p


class SeatContactTests(unittest.TestCase):
    def test_invalid_profile_is_rejected_without_clamping(self):
        p = parameters()
        for name, value in [('seat_face_angle', 0), ('seat_face_angle', 90), ('seat_face_angle', math.nan),
                            ('valve_margin_height', -1), ('valve_margin_height', 7),
                            ('intake_seat_contact_radial_width', 5), ('seat_entry_radial_relief', 2)]:
            with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                layout.seat_contact(dict(p, **{name: value}), 'intake')

    @unittest.skipUnless(cq, 'cadquery absent')
    def test_all_four_contacts_have_analytic_area_and_zero_penetration(self):
        p = parameters()
        for side, sy in layout.VALVES:
            with self.subTest(side=side, sy=sy):
                v, s = comp.valve(p, side, sy), comp.seat_insert(p, side, sy)
                self.assertTrue(assembly.brep_valid(v) and assembly.brep_valid(s))
                self.assertEqual((len(v.Solids()), len(s.Solids())), (1, 1))
                self.assertLess(abs(v.intersect(s).Volume()), 1e-6)
                r0, r1, z0, z1 = layout.seat_contact(p, side)
                area = math.pi * (r0 + r1) * math.hypot(r0 - r1, z1 - z0)
                vf = [f for f in v.Faces() if f.geomType() == 'CONE' and abs(f.Area() - area) < 1e-6]
                sf = [f for f in s.Faces() if f.geomType() == 'CONE' and abs(f.Area() - area) < 1e-6]
                self.assertEqual((len(vf), len(sf)), (1, 1))
                self.assertAlmostEqual(vf[0].intersect(sf[0]).Area(), area, places=6)
                for lift in (0.1, 1.0, p[f'{side}_max_lift']):
                    opened = comp.valve(p, side, sy, lift)
                    self.assertLess(abs(opened.intersect(s).Volume()), 1e-6)
                    self.assertGreater(assembly.brep_distance(opened, s), 0.01)

    @unittest.skipUnless(cq, 'cadquery absent')
    def test_lateral_port_leak_is_rejected_and_closed_volume_is_window_invariant(self):
        p = parameters()
        head = comp.head(p)
        with patch.object(comp, 'head', return_value=head):
            rows = [assembly.compression_ratio(p, margin) for margin in (2, 10)]
            for row in rows:
                self.assertEqual(row['status'], 'synthetic_twin_estimate_not_m64_value')
            self.assertAlmostEqual(rows[0]['clearance_volume_cc'], rows[1]['clearance_volume_cc'], places=6)
            real_valve = comp.valve
            for side in layout.SIDES:
                def opened(p, s, sy, lift=0):
                    return real_valve(p, s, sy, 1 if (s, sy) == (side, 1) else lift)
                with self.subTest(opened=side), patch.object(comp, 'valve', side_effect=opened):
                    row = assembly.compression_ratio(p)
                    self.assertIsNone(row['compression_ratio'])
                    self.assertEqual(row['status'], 'blocked_unsealed_chamber')


if __name__ == '__main__':
    unittest.main()
