"""Continuous nominal motion witnesses; never hot/physical engine validation."""
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source'
sys.path.insert(0, str(SOURCE))
import build_continuous_valve_envelopes as sweep


class ContinuousProfileTests(unittest.TestCase):
    def test_actual_V2_profiles_meet_analytic_conditions_and_only_base_is_extended(self):
        p = sweep.design.Parameters(**json.loads((SOURCE / 'four-valve-distribution-v2.parameters.json').read_text()))
        p.validate()
        for spec in sweep.design.valve_specs(p):
            profile = sweep.design.profiles(p, spec)[0]['valve']
            envelope, proof = sweep.continuous_sweep_profile(profile, spec['max_lift_mm'])
            self.assertEqual(envelope[2:], profile[2:])
            self.assertEqual(envelope[0][1], profile[0][1] - spec['max_lift_mm'])
            self.assertEqual(envelope[1][1], profile[1][1] - spec['max_lift_mm'])
            self.assertTrue(all(value <= 0 for value in proof['outer_segment_dr_dz']))
            self.assertTrue(proof['initial_base_cylindrical_with_positive_height'])
            self.assertEqual(proof['initial_cylindrical_base_height'], p.valve_head_axial_margin_mm)
            self.assertAlmostEqual(proof['analytic_added_volume'], math.pi * (spec['diameter_mm'] / 2)**2 * spec['max_lift_mm'])
            self.assertTrue(proof['sampling_is_not_the_continuous_coverage_proof'])

    def test_nonmonotone_or_ambiguous_or_unfilled_profile_is_rejected(self):
        invalid = [
            [(0., 0.), (1., 0.), (2., 1.), (0., 1.)],  # Increasing radius.
            [(0., 0.), (1., 0.), (1., 0.), (0., 1.)],  # Not single valued in z.
            [(0., 0.), (1., 0.), (.5, -1.), (0., -1.)],  # Reversed axial range.
            [(.1, 0.), (1., 0.), (1., 1.), (.1, 1.)],  # Annular, not filled.
        ]
        for profile in invalid:
            with self.assertRaises(ValueError):
                sweep.continuous_sweep_profile(profile, 1.)
        for lift in (-1., float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                sweep.continuous_sweep_profile([(0., 0.), (1., 0.), (1., 1.), (0., 1.)], lift)

    def test_monotone_initial_cone_is_rejected_instead_of_undercovered(self):
        # Merely lowering the first two vertices would change r(0) from 2 to
        # 1.5 for L=1: a monotone profile alone is insufficient for this method.
        profile = [(0., 0.), (2., 0.), (1., 1.), (0., 1.)]
        with self.assertRaisesRegex(ValueError, 'initial_cylindrical_base_required'):
            sweep.continuous_sweep_profile(profile, 1.)


@unittest.skipUnless(importlib.util.find_spec('OCP'), 'optional OCCT runtime')
class ContinuousEnvelopeNativeTests(unittest.TestCase):
    def test_continuous_sweep_detects_middle_collision_with_free_endpoints(self):
        cad = sweep.design.CAD()
        profile = [(0., 0.), (1., 0.), (1., 1.), (0., 1.)]
        envelope_profile, proof = sweep.continuous_sweep_profile(profile, 3.)
        original, envelope = cad.revolve(profile), cad.revolve(envelope_profile)
        spec = {'center': [0., 0., 0.], 'axis_angle_deg': 0.}
        obstacle = cad.BRepPrimAPI_MakeCylinder(
            cad.gp_Ax2(cad.gp_Pnt(0., 0., -1.5), cad.gp_Dir(0., 0., 1.)), .25, .25).Shape()
        for lift in (0., 3.):
            overlap = sweep.native_boolean(cad, cad.pose(original, spec, lift), obstacle)
            self.assertEqual(sweep.shape_volume(overlap), 0.)
        middle = sweep.native_boolean(cad, cad.pose(original, spec, 1.5), obstacle)
        whole = sweep.native_boolean(cad, envelope, obstacle)
        self.assertGreater(sweep.shape_volume(middle), 0.)
        self.assertAlmostEqual(sweep.shape_volume(whole), sweep.shape_volume(obstacle))
        self.assertAlmostEqual(sweep.shape_volume(envelope) - sweep.shape_volume(original), proof['analytic_added_volume'])

    def test_actual_V2_sweep_contains_intermediate_poses_and_has_analytic_volume(self):
        cad = sweep.design.CAD()
        p = sweep.design.Parameters(**json.loads((SOURCE / 'four-valve-distribution-v2.parameters.json').read_text()))
        for spec in sweep.design.valve_specs(p):
            profile = sweep.design.profiles(p, spec)[0]['valve']
            envelope_profile, proof = sweep.continuous_sweep_profile(profile, spec['max_lift_mm'])
            original, envelope = cad.revolve(profile), cad.revolve(envelope_profile)
            self.assertLess(abs(sweep.shape_volume(envelope) - sweep.shape_volume(original) - proof['analytic_added_volume']), 1e-7)
            for fraction in (0., .123, .5, .917, 1.):
                translated = cad.pose(original, {'center': [0., 0., 0.], 'axis_angle_deg': 0.}, fraction * spec['max_lift_mm'])
                outside = sweep.native_boolean(cad, translated, envelope, 'cut')
                self.assertLess(abs(sweep.shape_volume(outside)), 1e-7)

    def test_native_matching_is_not_STEP_order_and_rejects_duplicate_identity(self):
        cad = sweep.design.CAD()
        original = cad.revolve([(0., 0.), (1., 0.), (1., 1.), (0., 1.)])
        away = cad.pose(original, {'center': [5., 0., 0.], 'axis_angle_deg': 0.})
        match = sweep.identify_imported_valve(cad, [away, original], original)
        self.assertEqual(match['STEP_solid_index'], 2)
        with self.assertRaisesRegex(ValueError, 'not_unique'):
            sweep.identify_imported_valve(cad, [original, original], original)

    def test_registration_is_applied_once_to_new_shape_and_rejects_wrong_frame(self):
        cad = sweep.design.CAD()
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
        vertex = BRepBuilderAPI_MakeVertex(cad.gp_Pnt(2., 4., 5.)).Vertex()
        registration = {'scale_scan_units_per_mm_hypothesis': 1.0,
                        'rotation_Z_deg_hypothesis': -90., 'translation_Z_hypothesis': 3.}
        moved = sweep.registered(cad, vertex, registration)
        expected = BRepBuilderAPI_MakeVertex(cad.gp_Pnt(4., -2., 8.)).Vertex()
        self.assertLess(cad.distance(moved, expected), 1e-12)
        self.assertGreater(cad.distance(vertex, expected), 1.)
        with self.assertRaises(ValueError):
            sweep.registered(cad, vertex, {**registration, 'rotation_Z_deg_hypothesis': 90.})


if __name__ == '__main__':
    unittest.main()
