import copy
import hashlib
import json
import math
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT/'twins/993-intercooler/750-hp'
HERE = STUDY/'core-comparison'
MODEL = runpy.run_path(str(HERE/'source/screen.py'))
CARD = json.loads((STUDY/'requirements.json').read_text())
SPEC = json.loads((HERE/'assumptions.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


class CoreComparisonModelTests(unittest.TestCase):
    def test_validation_refuses_acceptance_and_unresolved_walls(self):
        MODEL['validate'](CARD, SPEC)
        for change in (lambda s: s['acceptance'].update(pressure_qualified=True), lambda s: s['helical']['web_mm'].append(.1),
                       lambda s: s['gyroid']['wall_mm'].append(1.5)):
            bad = copy.deepcopy(SPEC); change(bad)
            with self.assertRaises(ValueError): MODEL['validate'](CARD, bad)

    def test_twisted_tape_untwisted_limit_is_a_divided_tube(self):
        # y -> infinity and zero thickness: the tape still splits the tube, so only
        # the wetted-perimeter factor (pi+2)/pi remains on Dittus-Boelter and Blasius.
        a = CARD['assumed']; rho, mu, k = MODEL['properties'](400, 2e5, 1010, a['gas_constant_j_kg_k'])
        d = .008; mass = 2e4*mu*math.pi*d/4; wet = (math.pi+2)/math.pi
        r = MODEL['twisted_tape'](mass, d, 1e-12, 1e9, 1., 400, 2e5, {**a, 'header_loss_k': 0}, 1, 1)
        self.assertAlmostEqual(r['re'], 2e4, delta=1)
        self.assertAlmostEqual(r['h_w_m2_k']*d/k, .023*2e4**.8*.71**.4*wet**.2, delta=.01)
        self.assertAlmostEqual(r['pressure_drop_pa']/(rho*r['velocity_m_s']**2/2)*d/4, .0791*2e4**-.25*wet**1.25, places=6)
        swirl = MODEL['twisted_tape'](mass, d, .0002, 3, 1., 400, 2e5, a, 1, 1)
        self.assertGreater(swirl['h_w_m2_k'], r['h_w_m2_k']); self.assertFalse(MODEL['twisted_tape'](mass/4, d, .0002, 3, 1., 400, 2e5, a, 1, 1)['admissible'])

    def test_row_correction_table(self):
        self.assertEqual(MODEL['row_correction'](1), .64); self.assertEqual(MODEL['row_correction'](25), 1.)
        values = [MODEL['row_correction'](n) for n in range(1, 21)]
        self.assertEqual(values, sorted(values))

    def test_both_new_families_conserve_energy(self):
        a = CARD['assumed']
        for g in (MODEL['helical_geometry']((800, 550), 120, 1, 6, .4, .2, 3, 1.5), MODEL['gyroid_geometry']((800, 550), 90, 2, 4, .3, 3.0917)):
            for s in a['scenarios']:
                c = MODEL['evaluate'](g, s, a, SPEC, .75, 2)
                self.assertLess(abs(c['energy_residual_w']), 1e-6)
                self.assertLess(a['ambient_c'], c['charge_outlet_c']); self.assertLess(c['charge_outlet_c'], c['charge_inlet_c'])
                self.assertFalse(c['physical_performance_accepted'])
                if g['family'] == 'gyroid': self.assertFalse(c['assumed_constraints_pass'])


class RetainedComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = json.loads((HERE/'results/screen.json').read_text())

    def test_sources_and_sweep_are_pinned(self):
        for path, digest in self.r['source_hashes'].items(): self.assertEqual(sha(STUDY/path), digest, path)
        self.assertEqual(sha(HERE/'results/screen-sweep.csv'), self.r['sweep_sha256'])
        self.assertFalse(any(self.r['acceptance'].values()))

    def test_witness_replays_and_new_families_do_not_beat_it(self):
        self.assertTrue(self.r['witness_offset_strip']['replay_matches_retained'])
        self.assertEqual(self.r['family_counts'], {'helical': 3840, 'gyroid': 384})
        self.assertEqual(self.r['best_by_family'], {})
        self.assertEqual(self.r['helical_rejection_counts']['admissible_and_passing'], 0)
        self.assertGreater(self.r['helical_closest_in_domain'][0]['max_charge_outlet_c'], 100)

    def test_gyroid_break_even_is_a_measurement_requirement(self):
        a = CARD['assumed']; light = self.r['gyroid_break_even_lighter_than_witness']
        self.assertLess(light['mass_kg'], self.r['witness_offset_strip']['mass_kg'])
        for nu, ok in ((light['required_equal_nusselt'], True), (.95*light['required_equal_nusselt'], False)):
            cases = [MODEL['evaluate'](light['geometry'], s, a, SPEC, .75, 2, nu) for s in a['scenarios']]
            self.assertEqual(all(c['targets_met'] for c in cases), ok)
            self.assertFalse(any(c['assumed_constraints_pass'] for c in cases))

    def test_counterflow_bound_needs_less_ua(self):
        for c in self.r['witness_counterflow_bound']:
            self.assertLess(c['ideal_counterflow_outlet_c'], c['crossflow_unmixed_outlet_c'])
            self.assertLess(c['required_ua_counterflow_w_k'], c['required_ua_crossflow_w_k'])


class CouponMeasurementTests(unittest.TestCase):
    def test_measured_coupons_confirm_screen_geometry(self):
        m = json.loads((HERE/'results/coupon-measurement.json').read_text()); g = m['gyroid']
        for name, digest in m['source_sha256'].items():
            path = HERE/('source/'+name if name.endswith('.py') else 'source/picogk/'+name)
            self.assertEqual(sha(path), digest, name)
        self.assertAlmostEqual(g['metal_fraction_measured'], g['metal_fraction_screen'], delta=.03*g['metal_fraction_screen'])
        self.assertAlmostEqual(g['volume_closure'], 1, delta=.005)
        for n in g['networks']:
            self.assertAlmostEqual(n['porosity'], g['network_porosity_screen'], delta=.01)
            self.assertAlmostEqual(n['hydraulic_diameter_mm'], g['hydraulic_diameter_screen_mm'], delta=.06*g['hydraulic_diameter_screen_mm'])
            self.assertTrue(n['all_fragments_open_on_cut_window'])
        h = m['helical']
        self.assertAlmostEqual(h['metal_volume_measured_mm3']/h['metal_volume_screen_mm3'], 1, delta=.001)
        self.assertAlmostEqual(h['passage_volume_measured_mm3']/h['passage_volume_screen_mm3'], 1, delta=.001)
        parts = m['parts']
        self.assertEqual(parts['helical-charge-passage']['components'], h['passage_components_expected'])
        for name in ('gyroid-metal', 'helical-metal'):
            self.assertTrue(parts[name]['watertight']); self.assertEqual(parts[name]['components'], 1)
        review = json.loads((HERE/'derived/review.json').read_text())
        self.assertEqual({r['name']: r['native_sha256'] for r in review['records']}, {k: parts[k]['file_sha256'] for k in ('gyroid-metal', 'helical-metal')})


if __name__ == '__main__':
    unittest.main()
