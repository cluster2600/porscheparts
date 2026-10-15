import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT/'twins/993-intercooler/750-hp'
HOT=STUDY/'hot-weather'
spec=importlib.util.spec_from_file_location('hot_weather_study',HOT/'source/study.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
CONFIG=json.loads((HOT/'assumptions.json').read_text())

class HotWeatherTests(unittest.TestCase):
    def test_pressure_strip_scaling_and_small_deflection_gate(self):
        p=CONFIG['pressure'];r=M.wall_screen(p,150,700,65);self.assertFalse(r['pressure_qualified'])
        old,small=r['cases'][:2]
        self.assertAlmostEqual(old['stress_pa']/small['stress_pa'],36)
        self.assertAlmostEqual(old['deflection_mm']/small['deflection_mm'],1296)
        self.assertFalse(old['small_deflection_admissible']);self.assertTrue(small['small_deflection_admissible'])
        self.assertAlmostEqual(r['cases'][3]['stress_pa'],28.125e6)
        self.assertAlmostEqual(r['per_bank_interface_force_at_proof_n'],39375)

    def test_invalid_inputs_and_acceptance_reject(self):
        M.validate(CONFIG)
        for key,value in [('ambient_c',float('nan')),('charge_target_c',40)]:
            c=copy.deepcopy(CONFIG);c[key]=value
            with self.assertRaises(ValueError):M.validate(c)
        c=copy.deepcopy(CONFIG);c['acceptance']['pressure_qualified']=True
        with self.assertRaises(ValueError):M.validate(c)

    def test_retained_target_and_failed_recirculation(self):
        r=json.loads((HOT/'results/study.json').read_text());c=r['selected']['design_point']
        self.assertFalse(any(r['acceptance'].values()));self.assertEqual(r['case_count'],288)
        self.assertGreater(r['passing_count'],0);self.assertEqual(c['fan_position'],'downstream')
        self.assertEqual(c['compressor_inlet_c'],50);self.assertGreater(c['compressor_outlet_c'],230)
        self.assertLessEqual(c['charge_outlet_c'],59);self.assertLessEqual(c['total_shaft_power_w'],15000)
        self.assertGreater(c['charge_port_loss_pa'],0)
        for c in r['sensitivity']:self.assertLess(abs(c['energy_residual_w']),1e-6)
        case=next(c for c in r['sensitivity'] if c['ambient_c']==45 and c['recirculation_fraction']==.05)
        self.assertGreater(case['charge_outlet_c'],60)
        self.assertTrue(r['rib_loss_sensitivity'][1]['within_10kpa_budget']);self.assertFalse(r['rib_loss_sensitivity'][2]['within_10kpa_budget'])
        for path,digest in r['source_hashes'].items():self.assertEqual(hashlib.sha256((STUDY/path).read_bytes()).hexdigest(),digest)
        self.assertEqual(hashlib.sha256((HOT/'results/sweep.csv').read_bytes()).hexdigest(),r['sweep_sha256'])

    def test_native_rib_spacing_and_file_provenance(self):
        r=json.loads((HOT/'derived/review.json').read_text());layout=json.loads((HOT/'layout-input.json').read_text())
        self.assertFalse(r['manufacturing_authorized']);self.assertFalse(r['full_core_resolved'])
        self.assertEqual(r['generation']['geometry'],layout['selected']['geometry'])
        self.assertEqual(r['generation']['input_sha256'],hashlib.sha256((HOT/'layout-input.json').read_bytes()).hexdigest())
        wall=layout['pressure']['wall_mm'];span=layout['selected']['geometry']['span_mm']
        supports=[wall/2]+r['generation']['rib_positions_y_mm']+[span-wall/2]
        self.assertLessEqual(max(b-a for a,b in zip(supports,supports[1:])),30.0001)
        self.assertEqual(len(r['parts']),5)
        for part in r['parts']:
            self.assertTrue(part['native_closed']);self.assertEqual(part['native_bodies'],1)
            self.assertLess(part['review_relative_volume_error'],.005)
        for path,digest in r['source_hashes'].items():self.assertEqual(hashlib.sha256((HOT/path).read_bytes()).hexdigest(),digest)
        for path,digest in r['output_hashes'].items():self.assertEqual(hashlib.sha256((HOT/'derived'/path).read_bytes()).hexdigest(),digest)
        coupon=json.loads((HOT/'coupon-input.json').read_text())
        self.assertEqual(coupon['selected_geometry'],layout['selected']['geometry'])

    def test_inverse_fan_solution_matches_curve(self):
        r=json.loads((HOT/'results/study.json').read_text());c=r['selected']['design_point'];a=r['layout_input']['assumptions']
        pressure=M.fan_pressure(c['cooling_flow_kg_s'],c['fan_density_kg_m3'],a['cooler_fan'],a,c['cooler_speed_ratio'])
        self.assertAlmostEqual(pressure,c['fan_total_pressure_pa'],places=6)
        b=json.loads((STUDY/'requirements.json').read_text())['assumed']
        first=M.required(r['selected']['geometry'],c['duct_area_m2'],c['fan_position'],45,b,a,b['scenarios'][-1],1000)
        self.assertEqual(first['cooling_flow_kg_s'],1)
        x=M.fixed_speed(r['selected']['geometry'],c,45,b,a,b['scenarios'][-1])
        self.assertAlmostEqual(x['charge_outlet_c'],c['charge_outlet_c'],places=5)

    def test_lattice_comparison_vdb_and_research_boundaries(self):
        r=json.loads((HOT/'lattice/review.json').read_text())
        self.assertFalse(r['raw_mesh_accepted']);self.assertFalse(r['resolved_cfd'])
        self.assertFalse(r['thermal_improvement_demonstrated']);self.assertFalse(r['manufacturing_authorized'])
        self.assertEqual({(x['variant'],x['voxel_mm']) for x in r['runs']},{(v,h) for v in ['plain','bcc'] for h in [.1,.2]})
        for x in r['runs']:
            receipt=x['native_receipt'];self.assertEqual(receipt['field_count'],7)
            self.assertTrue(receipt['geometry_roundtrip_exact']);self.assertTrue(receipt['hot_cold_overlap_empty'])
            self.assertFalse(receipt['thermal_solver_executed']);self.assertFalse(receipt['hydraulic_solver_executed'])
            self.assertLess(x['volume_partition_relative_error'],.01)
            self.assertEqual(hashlib.sha256((HOT/'results/study.json').read_bytes()).hexdigest(),receipt['study_sha256'])
            self.assertEqual(hashlib.sha256(gzip.decompress((HOT/'lattice'/x['vdb_gzip']).read_bytes())).hexdigest(),receipt['vdb_sha256'])
            self.assertTrue(all(n>0 for n in receipt['active_values_checked'].values()))
            for p in x['parts'].values():
                self.assertTrue(p['closed_after_cleanup']);self.assertEqual(p['surface_components'],1)
                self.assertLess(p['cleanup_volume_error'],1e-7)
        for values in r['relative_volume_change_0p2_to_0p1'].values():self.assertTrue(all(v<.02 for v in values.values()))
        for path,digest in r['source_hashes'].items():self.assertEqual(hashlib.sha256((HOT/path).read_bytes()).hexdigest(),digest)
        for path,digest in r['output_hashes'].items():self.assertEqual(hashlib.sha256((HOT/'lattice'/path).read_bytes()).hexdigest(),digest)
        runtime=json.loads((HOT/'results/lattice-runtime.json').read_text())
        self.assertEqual(runtime['build_errors'],0)
        for path,digest in runtime['source_hashes'].items():self.assertEqual(hashlib.sha256((HOT/path).read_bytes()).hexdigest(),digest)
        for check in runtime['invalid_input_checks']:
            self.assertNotEqual(check['exit_code'],0);self.assertFalse(check['output_created'])

if __name__=='__main__':unittest.main()
