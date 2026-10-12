import copy
import hashlib
import json
import math
from pathlib import Path
import runpy
import unittest

ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT/'twins/993-installed-cooling-f1/intercooler-750'
MODEL=runpy.run_path(str(STUDY/'source/size_core.py'))
CARD=json.loads((STUDY/'requirements.json').read_text())


class IntercoolerSizingTests(unittest.TestCase):
    def test_ntu_limits_and_inverse(self):
        effect=MODEL['effectiveness']
        self.assertEqual(effect(0,.5),0)
        self.assertAlmostEqual(effect(1.5,0),1-math.exp(-1.5))
        self.assertAlmostEqual(effect(1.5,.25),.719,delta=.001)
        ua=MODEL['required_ua'](500,2000,450,300,330)
        self.assertAlmostEqual(450-effect(ua/500,.25)*150,330)
        with self.assertRaises(ValueError):effect(math.nan,.5)
        with self.assertRaises(ValueError):MODEL['required_ua'](1,1,300,310,305)

    def test_square_duct_poiseuille_and_nusselt(self):
        a=CARD['assumed'];rho,mu,k=MODEL['properties'](320,101325,1007,a['gas_constant_j_kg_k'])
        mass=1000*mu*.004
        r=MODEL['duct'](.004,.004,1,1,mass,320,101325,1007,a,1,1,0)
        self.assertAlmostEqual(r['re'],1000)
        self.assertAlmostEqual(r['h_w_m2_k']*.004/k,2.9786,delta=.01)
        f=r['pressure_drop_pa']/(1/.004*rho*r['velocity_m_s']**2/2)
        self.assertAlmostEqual(f*1000,56.9184,places=4)

    def test_geometry_and_model_conserve_energy(self):
        g=MODEL['geometry']((620,450,120,3,6,3,3,.3),.8)
        self.assertLess(g['metal_volume_m3'],g['core_volume_l']/1000)
        c=MODEL['evaluate'](g,CARD['assumed']['scenarios'][1],CARD['assumed'])
        self.assertLess(abs(c['energy_residual_w']),1e-8)
        self.assertLess(c['cooling_inlet_c'],c['charge_outlet_c'])
        self.assertLess(c['charge_outlet_c'],c['charge_inlet_c'])
        with self.assertRaises(ValueError):MODEL['evaluate'](g,CARD['assumed']['scenarios'][1],CARD['assumed'],cooling_mass=0)

    def test_boundary_validation_and_acceptance(self):
        MODEL['validate'](CARD)
        for key,value in [('metal_k_w_m_k',math.nan),('coupon_voxel_mm',1),('heat_transfer_multiplier_stress',2)]:
            bad=copy.deepcopy(CARD);bad['assumed'][key]=value
            with self.assertRaises(ValueError):MODEL['validate'](bad)
        bad=copy.deepcopy(CARD);bad['acceptance']['manufacturing_authorized']=True
        with self.assertRaises(ValueError):MODEL['validate'](bad)

    def test_retained_search_and_stress_result(self):
        r=json.loads((STUDY/'results/sizing.json').read_text())
        self.assertEqual(r['candidate_count'],8748)
        self.assertGreater(r['stress_feasible_count'],0)
        self.assertFalse(any(r['acceptance'].values()))
        for path,digest in r['source_hashes'].items():self.assertEqual(hashlib.sha256((STUDY/path).read_bytes()).hexdigest(),digest)
        self.assertEqual(hashlib.sha256((STUDY/'results/sweep.csv').read_bytes()).hexdigest(),r['sweep_sha256'])
        for c in r['selected_stress']:
            self.assertTrue(c['assumed_constraints_pass'])
            self.assertFalse(c['physical_performance_accepted'])
            self.assertLessEqual(c['charge_outlet_c'],60)
            self.assertLessEqual(c['cold']['pressure_drop_pa'],500)
            self.assertLessEqual(c['hot']['pressure_drop_pa'],10000)
        self.assertGreater(r['cooling_flow_sensitivity'][0]['charge_outlet_c'],60)
        self.assertGreater(r['selected_stress'][-1]['engine_inlet_c'],70)
        self.assertGreater(r['mixedness_sensitivity'][-1]['charge_outlet_c'],60)
        g=r['selected_geometry'];c=MODEL['evaluate'](g,CARD['assumed']['scenarios'][-1],CARD['assumed'],hfactor=.75,ffactor=2)
        self.assertAlmostEqual(c['heat_rejection_w'],r['selected_stress'][-1]['heat_rejection_w'],places=5)

    def test_independent_crossflow_grid_conserves_energy_and_refines(self):
        r=json.loads((STUDY/'results/sizing.json').read_text())
        grids=r['crossflow_grid_check']
        for cell in grids:self.assertLess(abs(cell['energy_residual_w']),1e-6)
        self.assertLess(abs(grids[-1]['charge_outlet_c']-grids[-2]['charge_outlet_c']),.003)
        self.assertGreater(abs(grids[-1]['charge_outlet_c']-r['selected_stress'][-1]['charge_outlet_c']),1)

    def test_thin_parallel_route_is_research_only(self):
        r=json.loads((STUDY/'results/thin-sizing.json').read_text());b=r['best_screen_candidate']
        self.assertEqual(r['candidate_count'],6912)
        self.assertEqual(b['geometry']['charge_parallel_banks'],2)
        self.assertLess(b['mass_kg'],20)
        for key in ['manufacturer_recipe_selected','thin_fin_printability_verified','pressure_qualified','manufacturing_authorized','full_core_native_geometry_generated']:self.assertFalse(r[key])
        for path,digest in r['source_hashes'].items():self.assertEqual(hashlib.sha256((STUDY/path).read_bytes()).hexdigest(),digest)
        self.assertEqual(hashlib.sha256((STUDY/'results/thin-sweep.csv').read_bytes()).hexdigest(),r['sweep_sha256'])
        for c in b['stress_cases']:self.assertTrue(c['assumed_constraints_pass'])
        self.assertGreater(r['fully_mixed_bound_charge_outlet_c'],60)
        c=MODEL['evaluate'](b['geometry'],CARD['assumed']['scenarios'][-1],CARD['assumed'],hfactor=.75,ffactor=2)
        self.assertAlmostEqual(c['heat_rejection_w'],b['stress_cases'][-1]['heat_rejection_w'],places=5)
        single=dict(b['geometry'],charge_parallel_banks=1)
        single_case=MODEL['evaluate'](single,CARD['assumed']['scenarios'][-1],CARD['assumed'],hfactor=.75,ffactor=2)
        self.assertGreater(single_case['hot']['pressure_drop_pa'],c['hot']['pressure_drop_pa'])
        coupon=json.loads((STUDY/'coupon-input.json').read_text())
        self.assertEqual(coupon['selected_geometry'],b['geometry'])
        self.assertGreaterEqual(b['geometry']['fin_mm'],4*coupon['basis']['assumed']['coupon_voxel_mm'])

    def test_native_coupon_receipt_and_retained_files(self):
        r=json.loads((STUDY/'derived/review.json').read_text())
        candidate=json.loads((STUDY/'coupon-input.json').read_text())
        self.assertFalse(r['manufacturing_authorized'])
        self.assertFalse(r['generation']['full_core_generated'])
        self.assertEqual(r['generation']['geometry'],candidate['selected_geometry'])
        self.assertAlmostEqual(r['generation']['voxel_mm'],.0375,places=6)
        self.assertEqual({p['name'] for p in r['parts']},{'offset-fin-coupon','plain-fin-control'})
        for part in r['parts']:
            self.assertTrue(part['native_watertight'])
            self.assertEqual(part['native_bodies'],1)
            self.assertGreater(part['native_volume_mm3'],0)
            self.assertEqual(part['sampled_open_route_points'],305)
            self.assertFalse(part['all_voids_inspected'])
            self.assertLessEqual(part['review_volume_relative_error'],.005)
        for name,digest in r['source_hashes'].items():
            self.assertEqual(hashlib.sha256((STUDY/name).read_bytes()).hexdigest(),digest)
        for name,digest in r['output_hashes'].items():
            self.assertEqual(hashlib.sha256((STUDY/'derived'/name).read_bytes()).hexdigest(),digest)

    def test_offset_correlation_excludes_invalid_fin_ratios(self):
        a=CARD['assumed']
        r=MODEL['duct'](.003,.001,1,100,.1,350,250000,1010,a,1,1,0,.0004,.02)
        self.assertEqual(r['regime'],'offset_out_of_range')


if __name__=='__main__':unittest.main()
