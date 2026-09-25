"""Cinématique articulée et profils de came : checks indépendants, sans qualification moteur."""
import json
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FV = ROOT / 'twins/m64-cylinder-head/source/fourvalve'
sys.path[:0] = [str(FV), str(FV / 'cad')]

import kinematics as kin
import provenance
import rocker_geometry as rg

try:
    import cadquery as cq
    import assembly
    import components as comp
    import rocker_train as rt
except ImportError:
    cq = None


def parameters():
    p = json.loads((ROOT / 'twins/m64-cylinder-head/evidence/g4-spring-layout-20260925/candidate.json').read_text())['values']
    for k, row in json.loads((FV / 'params-rockers/rocker_train.json').read_text())['parameters'].items():
        provenance.verify_provenance(k, row, {})
        p[k] = row['value']
    return p


class RockerTrainTests(unittest.TestCase):
    def test_invalid_geometry_is_rejected(self):
        p = parameters()
        for key, value in [('rocker_valve_arm', 11), ('rocker_cam_arm', 46), ('rocker_pad_radius', math.nan),
                           ('rocker_width', 20), ('rocker_roller_width', 14), ('rocker_pivot_radius', 8), ('rocker_pin_radius', 4),
                           ('rocker_pressure_angle_limit', 90)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                rg.validate(dict(p, **{key: value}))
        with self.assertRaises(ValueError):
            rg.profile(p, 'intake', 0)

    def test_articulated_output_reproduces_law_and_stays_on_stem(self):
        p = parameters()
        phi = np.arange(0, 720.01, 0.25)
        for side in ('intake', 'exhaust'):
            r = rg.state(p, side, phi)
            geometric = np.maximum(p['rocker_valve_arm'] * np.sin(r['beta']) - r['lash_mm'], 0)
            np.testing.assert_allclose(geometric, kin.cam_laws(p)[0][side].valve_lift(np.radians(phi)) * 1000, atol=1e-12)
            self.assertLess(r['tip_walk_mm'].max() + p['rocker_tip_edge_margin'], p['guide_bore_diameter'] / 2 - .02)
            np.testing.assert_allclose(r['roller'][0], r['roller'][-1], atol=1e-12)

    def test_contact_is_global_and_converges_with_profile_resolution(self):
        p = parameters()
        for side in ('intake', 'exhaust'):
            errors = []
            # Vérification hors des sommets utilisés pour construire le profil.
            phi = np.arange(.37, 720, 3.0)
            s = rg.state(p, side, phi)
            centres = s['roller'] - [p['rocker_cam_arm'], p['cam_base_circle_radius'] + p['rocker_roller_radius']]
            probes = rg.rotate(centres, -np.radians(phi / 2))
            for step in (2, 1, .5):
                profile = rg.profile(p, side, step)
                errors.append(np.max(abs(rg.point_to_polygon_distance(probes, profile['points']) - p['rocker_roller_radius'])))
                self.assertLess(profile['pressure_deg'].max(), p['rocker_pressure_angle_limit'])
            self.assertLess(errors[2], errors[1])
            self.assertLess(errors[1], errors[0])
            self.assertLess(errors[2], .001)  # tolérance numérique, pas d'usinage
            self.assertGreater(min(rg.cam_body_clearances(p, profile).values()), p['min_valve_clearance'])
            angles = np.arange(.37, 720, 11.0)
            recovered = rg.recover_valve_lift(p, side, angles, profile['points'])
            self.assertLess(np.max(abs(recovered - rg.state(p, side, angles)['valve_lift_mm'])), .001)
        rejected = dict(p, rocker_valve_arm=35, rocker_cam_arm=21)
        self.assertLess(rg.cam_body_clearances(rejected, rg.profile(rejected, 'intake'))['pivot_boss_mm'], 0)

    @unittest.skipUnless(cq, 'cadquery absent')
    def test_native_contacts_at_peak_lift_and_no_rocker_collisions(self):
        p = parameters()
        for side, law in kin.cam_laws(p)[0].items():
            phi = math.degrees(law.centreline_rad)
            pieces = rt.moving_parts(p, side, 1, phi)
            cam = rt.camshaft(p, side, phi)
            lift = rg.state(p, side, phi)['valve_lift_mm'][0]
            valve = comp.valve(p, side, 1, lift)
            self.assertTrue(all(assembly.brep_valid(s) for s in [*pieces.values(), cam]))
            self.assertEqual(len(pieces['rocker'].Solids()), 1)
            self.assertLess(assembly.brep_distance(cam, pieces['roller']), .001)
            self.assertLess(assembly.brep_distance(pieces['rocker'], valve), 1e-6)
            for other in (cam, pieces['roller'], valve, comp.retainer(p, side, 1, lift), comp.spring(p, side, 1, lift)):
                self.assertLess(abs(pieces['rocker'].intersect(other).Volume()), 1e-6)
            # La came heurtait les joues étroites à forte pente, malgré un sommet sans collision.
            steep = rg.profile(p, side)
            phi = float(steep['phi_deg'][np.argmax(steep['pressure_deg'])])
            rocker = rt.moving_parts(p, side, 1, phi)['rocker']
            self.assertLess(abs(rocker.intersect(rt.camshaft(p, side, phi)).Volume()), 1e-6)

    @unittest.skipUnless(cq, 'cadquery absent')
    def test_assembly_does_not_round_valve_lift_to_integer_crank_degrees(self):
        p = parameters()
        phi = 65.37
        original = comp.valve
        calls = []
        def record(p, side, sy, lift=0):
            calls.append((side, lift))
            return original(p, side, sy, lift)
        with patch.object(comp, 'head', return_value=cq.Solid.makeBox(1, 1, 1)), \
                patch.object(comp, 'valve', side_effect=record), patch.object(rt, 'parts', return_value={}):
            shapes = assembly.parts(p, phi)
        self.assertFalse(any(k.startswith('follower_') for k in shapes))
        for side, lift in calls:
            expected = float(kin.cam_laws(p)[0][side].valve_lift(np.radians(phi))[0]) * 1000
            self.assertAlmostEqual(lift, expected, places=12)


if __name__ == '__main__':
    unittest.main()
