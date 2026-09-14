import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT/'twins/m64-cylinder-head/seat-guide-thermal-screen'
spec = importlib.util.spec_from_file_location('m64_seat_guide_screen', DIRECTORY/'screen.py')
screen = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = screen
spec.loader.exec_module(screen)


class SeatGuideThermalScreenTests(unittest.TestCase):
    def test_exact_free_diameter_definition(self):
        D, I0, ei, eh = 43., .08, .0027, .0045342
        actual = screen.free_interference(D, I0, ei, eh)
        self.assertAlmostEqual(actual, D*(1+ei)-(D-I0)*(1+eh), places=13)
        self.assertAlmostEqual(actual, .001492136, places=13)

    def test_identical_thermal_growth_preserves_scaled_interference(self):
        for strain in (0., .002, .02, -.001):
            self.assertEqual(screen.free_interference(36., .07, strain, strain), .07*(1+strain))

    def test_critical_fit_is_zero_contact_not_margin(self):
        for D in (11., 36., 43.):
            critical = screen.critical_cold_interference(D, .0027, .0045342)
            self.assertAlmostEqual(screen.free_interference(D, critical, .0027, .0045342), 0., places=14)
            self.assertLess(screen.free_interference(D, critical-.001, .0027, .0045342), 0.)

    def test_different_insert_and_head_temperatures(self):
        eh = screen.endpoint_strain(25.19e-6, 20., 200.)
        cold_insert = screen.endpoint_strain(15e-6, 20., 150.)
        hot_insert = screen.endpoint_strain(15e-6, 20., 250.)
        self.assertLess(screen.free_interference(43., .08, cold_insert, eh),
                        screen.free_interference(43., .08, hot_insert, eh))
        self.assertAlmostEqual(screen.critical_cold_interference(43., cold_insert, eh), .11061903118878383)

    def test_corner_bounds_enclose_rectangular_domain(self):
        ranges = ((.05, .09), (.001, .004), (.002, .005))
        lower, upper = screen.free_interference_bounds(36., *ranges)
        # Derivatives: dI/dI0>0, dI/dei=D>0, dI/deh=I0-D<0.
        self.assertAlmostEqual(lower, screen.free_interference(36., .05, .001, .005))
        self.assertAlmostEqual(upper, screen.free_interference(36., .09, .004, .002))
        rng = random.Random(931964)
        for _ in range(500):
            value = screen.free_interference(36., *(rng.uniform(*interval) for interval in ranges))
            self.assertLessEqual(lower, value)
            self.assertGreaterEqual(upper, value)

    def test_lame_independent_stress_and_hooke_displacement_closure(self):
        # Synthetic unit fixture, not proposed material or hardware dimensions.
        a, b, c, Ei, Eh, nui, nuh, I = 3., 5., 8., 150., 50., .2, .3, .01
        result = screen.lame_normalized(a/b, c/b, Ei/Eh, nui, nuh, I/(2*b))
        pressure = result['pressure_over_E_head']*Eh
        # Lame sigma_r=A-B/r², sigma_theta=A+B/r²; boundary tractions.
        Ai, Bi = -pressure*b*b/(b*b-a*a), -pressure*a*a*b*b/(b*b-a*a)
        Ah, Bh = pressure*b*b/(c*c-b*b), pressure*b*b*c*c/(c*c-b*b)
        self.assertAlmostEqual(Ai-Bi/a**2, 0.)
        self.assertAlmostEqual(Ai-Bi/b**2, -pressure)
        self.assertAlmostEqual(Ah-Bh/b**2, -pressure)
        self.assertAlmostEqual(Ah-Bh/c**2, 0.)
        ui = b*((Ai+Bi/b**2)-nui*(Ai-Bi/b**2))/Ei
        uh = b*((Ah+Bh/b**2)-nuh*(Ah-Bh/b**2))/Eh
        self.assertAlmostEqual(2*(uh-ui), I, places=14)  # catches radial/diametral factor 2

    def test_same_material_solid_insert_limits(self):
        result = screen.lame_normalized(0., 2., 1., .3, .3, .001)
        self.assertAlmostEqual(result['pressure_over_E_head'], .000375)
        far_field = screen.lame_normalized(0., 1e8, 1., .3, .3, .001)
        self.assertAlmostEqual(far_field['pressure_over_E_head'], .0005, places=14)

    def test_no_tensile_contact_pressure(self):
        for interference in (0., -.001):
            result = screen.lame_normalized(.5, 2., 3., .3, .3, interference)
            self.assertEqual(result['pressure_over_E_head'], 0.)
            self.assertFalse(result['contact_active_in_ideal_ring'])

    def test_invalid_inputs_fail_closed(self):
        for args in ((1., 1., 0., 0.), (0., 0., 0., 0.), (1., 0., -1., 0.),
                     (1., math.nan, 0., 0.)):
            with self.assertRaises(ValueError):
                screen.free_interference(*args)
        for args in ((1., 2., 3., .3, .3, .001), (.5, 1., 3., .3, .3, .001),
                     (.5, 2., 0., .3, .3, .001), (.5, 2., 3., .5, .3, .001)):
            with self.assertRaises(ValueError):
                screen.lame_normalized(*args)
        with self.assertRaises(ValueError):
            screen.free_interference_bounds(36., (.1, .05), (0., .01), (0., .01))

    def test_source_bindings_and_reproducibility(self):
        recorded = json.loads((DIRECTORY/'report.json').read_text())
        self.assertEqual(recorded, screen.generate_report())
        for source in recorded['source_bindings']:
            self.assertEqual(hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest(), source['sha256'])
        self.assertFalse(recorded['manufacturing_authorized'])
        self.assertFalse(recorded['material_selected'])
        self.assertIsNone(recorded['head_contact_pressure_MPa'])
        self.assertFalse(recorded['synthetic_CTE_range_is_material_property_bound'])
        self.assertFalse(recorded['four_vs_two_valve_scope']['bridge_is_axisymmetric_ring'])
        self.assertFalse(recorded['four_vs_two_valve_scope']['gap_is_existing_body_ligament'])
        self.assertEqual([c['outer_diameter_mm'] for c in recorded['components']], [43., 11., 36., 11.])
        for component in recorded['components']:
            self.assertIsNone(component['cold_diametral_interference_selected_mm'])
            if component['role'] == 'guide':
                self.assertIsNone(component['cold_reference_range_mm'])

    def test_documentary_sources_not_merged_or_interpolated(self):
        report = json.loads((DIRECTORY/'report.json').read_text())
        points = report['CTE_endpoint_cases']
        self.assertEqual([(p['reference_temperature_C'], p['head_temperature_C']) for p in points],
                         [(20, 200), (25, 100), (25, 200), (25, 300)])
        self.assertNotEqual(points[0]['head_CTE_source_id'], points[2]['head_CTE_source_id'])
        for point in points:
            self.assertAlmostEqual(point['head_engineering_strain'],
                                   point['head_mean_CTE_per_K']*(point['head_temperature_C']-point['reference_temperature_C']))


if __name__ == '__main__':
    unittest.main()
