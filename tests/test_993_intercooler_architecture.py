import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT/'twins/993-intercooler/750-hp'
ARCH=STUDY/'architecture'
spec=importlib.util.spec_from_file_location('cooling_architecture',ARCH/'source/compare.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
A=json.loads((ARCH/'assumptions.json').read_text())

class ArchitectureTests(unittest.TestCase):
    def test_fan_laws_and_operating_point(self):
        f=A['cooler_fan'];rho=A['fan_density_reference_kg_m3']
        self.assertAlmostEqual(M.fan_pressure(0,rho,f,A),f['shutoff_pa'])
        self.assertAlmostEqual(M.fan_pressure(rho*f['free_flow_m3_s'],rho,f,A),0)
        self.assertAlmostEqual(M.fan_pressure(2,rho,f,A,2),4*M.fan_pressure(1,rho,f,A))
        self.assertAlmostEqual(M.root(lambda x:100-2*x*x,0,10),50**.5,places=7)
        with self.assertRaises(ValueError):M.root(lambda x:x+1,0,2)

    def test_assumptions_reject_bad_values_and_acceptance(self):
        M.validate(A)
        for key,value in [('voxel_mm',2),('engine_reference_flow_kg_s',float('nan'))]:
            a=copy.deepcopy(A);a[key]=value
            with self.assertRaises(ValueError):M.validate(a)
        a=copy.deepcopy(A);a['acceptance']['manufacturing_authorized']=True
        with self.assertRaises(ValueError):M.validate(a)

    def test_operating_points_and_hot_weather_failure_are_retained(self):
        r=json.loads((ARCH/'results/comparison.json').read_text())
        self.assertFalse(any(r['acceptance'].values()))
        self.assertGreater(r['passing_count'],0)
        for c in r['selected']['design_cases']:self.assertTrue(c['assumed_constraints_pass'])
        for c in r['architecture_comparison']+r['sensitivity']:
            self.assertLess(abs(c['fan_pressure_residual_pa']),.001)
            self.assertLess(abs(c['energy_residual_w']),1e-6)
            self.assertGreater(c['fan_preheat_k'],0)
            self.assertFalse(c['physical_performance_accepted'])
        hot=[c for c in r['sensitivity'] if c['ambient_c']==45 and c['speed_ratio']==1][0]
        self.assertGreater(hot['charge_outlet_c'],60)
        serial=[c for c in r['architecture_comparison'] if c['architecture']=='serial' and c['scenario']=='high'][0]
        self.assertGreater(serial['engine_inlet_c'],50)
        for name,digest in r['source_hashes'].items():self.assertEqual(hashlib.sha256((STUDY/name).read_bytes()).hexdigest(),digest)
        self.assertEqual(hashlib.sha256((ARCH/'results/sweep.csv').read_bytes()).hexdigest(),r['sweep_sha256'])

    def test_native_header_receipt_keeps_envelopes_distinct(self):
        r=json.loads((ARCH/'derived/review.json').read_text())
        selected=json.loads((ARCH/'results/comparison.json').read_text())['selected']
        self.assertFalse(r['manufacturing_authorized'])
        self.assertFalse(r['full_core_resolved'])
        self.assertFalse(r['generation']['core_fins_resolved'])
        self.assertEqual(r['generation']['geometry'],selected['geometry'])
        self.assertEqual(r['generation']['input_sha256'],hashlib.sha256((ARCH/'results/comparison.json').read_bytes()).hexdigest())
        self.assertEqual(len(r['parts']),5)
        for part in r['parts']:
            self.assertTrue(part['native_closed'])
            self.assertEqual(part['native_bodies'],1)
            self.assertLess(part['review_relative_volume_error'],.005)
            if 'core' in part['name']:self.assertIsNone(part['mass_kg'])
        self.assertGreater(r['header_mass_kg'],0)
        for name,digest in r['source_hashes'].items():self.assertEqual(hashlib.sha256((ARCH/name).read_bytes()).hexdigest(),digest)
        for name,digest in r['output_hashes'].items():self.assertEqual(hashlib.sha256((ARCH/'derived'/name).read_bytes()).hexdigest(),digest)

    def test_recalculation_of_selected_operating_point(self):
        r=json.loads((ARCH/'results/comparison.json').read_text())
        b=json.loads((STUDY/'requirements.json').read_text())['assumed']
        c=M.operating(r['selected']['geometry'],b['scenarios'][-1],b,A,'separate')
        self.assertAlmostEqual(c['charge_outlet_c'],r['selected']['design_cases'][-1]['charge_outlet_c'],places=7)
        for dim,limit in zip(r['selected']['packaging_bounds_mm'],A['available_envelope_mm']):self.assertLessEqual(dim,limit)

if __name__=='__main__':unittest.main()
