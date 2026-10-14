import copy
import hashlib
import json
import math
from pathlib import Path
import runpy
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT/'twins/993-intercooler/750-hp'
HERE = STUDY/'counterflow-passes'
MODEL = runpy.run_path(str(HERE/'source/passes.py'))
BASE = MODEL['BASE']
CARD = json.loads((STUDY/'requirements.json').read_text())
SPEC = json.loads((HERE/'assumptions.json').read_text())
WITNESS = json.loads((STUDY/'results/thin-sizing.json').read_text())['best_screen_candidate']
A = CARD['assumed']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


class MultipassModelTests(unittest.TestCase):
    def test_validation_refuses_acceptance_and_missing_reference(self):
        MODEL['validate'](CARD, SPEC)
        for change in (lambda s: s['acceptance'].update(pressure_qualified=True), lambda s: s['arrangement'].update(passes=[2, 3]),
                       lambda s: s['arrangement'].update(return_tank_loss_k=0)):
            bad = copy.deepcopy(SPEC); change(bad)
            with self.assertRaises(ValueError): MODEL['validate'](CARD, bad)

    def test_single_pass_is_the_retained_model(self):
        g = MODEL['pass_geometry'](WITNESS['geometry'], 1)
        self.assertEqual(g['metal_volume_m3'], WITNESS['geometry']['metal_volume_m3'])
        for s in A['scenarios']:
            mine, base = MODEL['evaluate'](g, s, A, 4., .75, 2), BASE['evaluate'](WITNESS['geometry'], s, A, hfactor=.75, ffactor=2)
            self.assertAlmostEqual(mine['charge_outlet_c'], base['charge_outlet_c'], places=9)
            self.assertAlmostEqual(mine['hot']['pressure_drop_pa'], base['hot']['pressure_drop_pa'], places=6)
            self.assertAlmostEqual(mine['cold']['pressure_drop_pa'], base['cold']['pressure_drop_pa'], places=6)

    def test_series_effectiveness_tends_to_counterflow(self):
        ntu, cr = 3., .25; eps = lambda p: MODEL['series_effectiveness'](MODEL['effectiveness'](ntu/p, cr), cr, p)
        counter = -math.expm1(-ntu*(1-cr))/(1-cr*math.exp(-ntu*(1-cr)))
        values = [eps(p) for p in (1, 2, 3, 4, 8, 64)]
        self.assertEqual(values, sorted(values)); self.assertAlmostEqual(values[-1], counter, delta=2e-3); self.assertLess(values[-1], counter+1e-12)
        self.assertAlmostEqual(MODEL['series_effectiveness'](.6, 1., 3), 3*.6/(1+2*.6))

    def test_grid_reproduces_single_pass_and_orders_the_passes(self):
        c = WITNESS['stress_cases'][-1]; ch, cc = .62*A['hot_cp_j_kg_k'], A['cooling_mass_flow_kg_s']*A['cold_cp_j_kg_k']; th, tc = c['charge_inlet_c']+273.15, A['ambient_c']+273.15
        one = MODEL['grid'](c['ua_w_k'], ch, cc, th, tc, 1, 40)
        # size_core.crossflow_grid returns whatever unit it is given; it is fed kelvin here.
        self.assertAlmostEqual(one['charge_outlet_c'], BASE['crossflow_grid'](c['ua_w_k'], ch, cc, th, tc, 40)['charge_outlet_c']-273.15, places=9)
        previous = one['charge_outlet_c']
        for p in (2, 3, 4):
            counter, parallel = MODEL['grid'](c['ua_w_k'], ch, cc, th, tc, p, 40), MODEL['grid'](c['ua_w_k'], ch, cc, th, tc, p, 40, 'parallel')
            self.assertLess(counter['charge_outlet_c'], previous); self.assertGreater(parallel['charge_outlet_c'], one['charge_outlet_c'])
            self.assertLess(abs(counter['energy_residual_w']), 1e-5); previous = counter['charge_outlet_c']

    def test_passes_cost_channels_dividers_and_pressure(self):
        g = WITNESS['geometry']; previous = None
        for p in (1, 2, 3, 4):
            q = MODEL['pass_geometry'](g, p)
            self.assertLessEqual(p*q['hot_channels_per_pass']+p-1, g['hot_channels_per_tube'])
            self.assertAlmostEqual(q['divider_metal_volume_m3'], (p-1)*g['tubes']*g['width_mm']*g['hot_gap_mm']*g['wall_mm']*1e-9)
            high = MODEL['evaluate'](q, A['scenarios'][-1], A, 2., .75, 2)
            self.assertFalse(high['physical_performance_accepted']); self.assertLess(abs(high['energy_residual_w']), 1e-6)
            if previous:
                self.assertGreater(high['hot']['pressure_drop_pa'], previous['hot']['pressure_drop_pa']); self.assertLess(high['charge_outlet_c'], previous['charge_outlet_c'])
            previous = high
        low_k, high_k = (MODEL['evaluate'](MODEL['pass_geometry'](g, 2), A['scenarios'][-1], A, k, .75, 2)['hot']['pressure_drop_pa'] for k in (1., 4.))
        self.assertLess(low_k, high_k)


class RetainedMultipassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = json.loads((HERE/'results/passes.json').read_text())

    def test_sources_and_sweep_are_pinned(self):
        for path, digest in self.r['source_hashes'].items(): self.assertEqual(sha(STUDY/path), digest, path)
        self.assertEqual(sha(HERE/'results/passes-sweep.csv'), self.r['sweep_sha256'])
        self.assertFalse(any(self.r['acceptance'].values())); self.assertTrue(self.r['witness_single_pass_replay_matches_retained'])

    def test_thin_search_single_pass_is_the_witness(self):
        one = self.r['thin_search']['lightest_by_passes']['1']
        self.assertAlmostEqual(one['mass_kg'], WITNESS['mass_kg'], places=9)
        self.assertEqual(self.r['passing_by_passes']['thin_search']['1'], 48)

    def test_counterflow_passes_do_not_beat_the_single_pass_core(self):
        self.assertEqual(self.r['counts_by_passes'], {'thin_search': {str(p): 6912 for p in (1, 2, 3, 4)}, 'extended_search': {str(p): 18432 for p in (1, 2, 3, 4)}})
        for name in ('thin_search', 'extended_search'):
            best = self.r[name]['lightest_by_passes']; self.assertEqual(set(best), {'1', '2'})
            self.assertGreater(best['2']['mass_kg'], best['1']['mass_kg']+1.5)
            self.assertEqual(set(self.r[name]['lightest_by_passes_grid_conservative']), {'1', '2'})
        self.assertTrue(all(s['all_scenarios_pass'] for s in self.r['extended_search']['return_tank_sensitivity']['2']))
        self.assertFalse(self.r['thin_search']['return_tank_sensitivity']['2'][-1]['all_scenarios_pass'])

    def test_coupon_passes_join_only_through_the_tank(self):
        m = json.loads((HERE/'results/coupon-measurement.json').read_text())
        for name, digest in m['source_sha256'].items():
            path = HERE/('results/'+name if name.endswith('.json') else 'source/'+name if name.endswith('.py') else 'source/picogk/'+name)
            self.assertEqual(sha(path), digest, name)
        self.assertTrue(m['metal_single_closed_body']); self.assertTrue(m['passes_joined_only_by_return_tank'])
        self.assertAlmostEqual(m['volume_closure'], 1, delta=.005)
        halves = m['parts']['two-pass-charge-without-tank']['component_volumes_mm3']
        self.assertAlmostEqual(halves[0], halves[1], delta=.01*halves[0])
        g = m['generation']; best = self.r['extended_search']['lightest_by_passes']['2']['geometry']
        for k in ('hot_gap_mm', 'hot_pitch_mm', 'fin_mm', 'strip_length_mm', 'wall_mm'): self.assertAlmostEqual(g[k], best[k], places=5)
        self.assertFalse(g['manufacturing_authorized'])

    def test_coupon_refuses_an_existing_derived_directory(self):
        stubs = {n: types.ModuleType(n) for n in ('numpy', 'pyvista', 'trimesh')}
        with mock.patch.dict(sys.modules, stubs), tempfile.TemporaryDirectory() as tmp:
            run = runpy.run_path(str(HERE/'source/coupon.py'))['run']; tmp = Path(tmp)
            (tmp/'derived').mkdir(); (tmp/'derived/two-pass-coupon.png').write_bytes(b'earlier')
            with self.assertRaises(FileExistsError): run(tmp/'generated', tmp/'measurement.json', tmp/'derived')
            self.assertEqual((tmp/'derived/two-pass-coupon.png').read_bytes(), b'earlier'); self.assertFalse((tmp/'measurement.json').exists())

    def test_witness_split_trades_outlet_for_charge_loss(self):
        split = self.r['witness_fins_split_into_passes']
        self.assertTrue(split[0]['all_scenarios_pass']); self.assertFalse(any(s['all_scenarios_pass'] for s in split[1:]))
        for a, b in zip(split, split[1:]):
            self.assertLess(b['high_case']['charge_outlet_c'], a['high_case']['charge_outlet_c']); self.assertGreater(b['max_hot_dp_pa'], A['charge_pressure_loss_budget_pa'])


if __name__ == '__main__':
    unittest.main()
