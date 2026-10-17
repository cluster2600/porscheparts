import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT/'twins/m64-cylinder-head/source/water-cooled-head'


class WaterHeadTests(unittest.TestCase):
    def test_primary_target_keeps_stock_baseline_and_lubrication(self):
        program = json.loads((ROOT/'twins/m64-engine-system/program.json').read_text())
        self.assertIn('air/huile', program['engine_baseline']['architecture'])
        self.assertEqual(program['design_target']['primary_head_cooling'], 'water_based_liquid')
        self.assertTrue(program['design_target']['oil_lubrication_retained'])
        c = json.loads((HERE/'contract.json').read_text())
        for key in ('source_master_modified', 'material_removal_authorized', 'manufacturing_authorized'):
            self.assertIs(c[key], False)
        for key in ('coolant_heat_load_w', 'coolant_mass_flow_kg_s', 'pump_curve', 'hot_wall_minimum_mm', 'protected_volume_mask'):
            self.assertIsNone(c[key])
        self.assertEqual(c['heads_per_bank'], 3)

    def test_rejects_qualification_missing_reference_and_export_substitution(self):
        spec = importlib.util.spec_from_file_location('water_inspector_test', HERE/'audit.py')
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except ImportError:
            self.skipTest('NumPy required by existing raw-surface inspector')
        c = json.loads((HERE/'contract.json').read_text())
        good = dict(schema='m64-water-head-generation/v1', status='routing_only_integration_blocked',
                    units=c['units'], voxel_scan_units=.3, head_stl_sha256=c['head_stl_sha256'],
                    input_manifest_sha256=c['input_manifest_sha256'], diagnostic_wall_margin=3,
                    files=[dict(filename=n+'.stl') for n in ('coolant-routing','routing-plus-wall-margin','outside-eroded-head')],
                    reference_wall_margin_conflicts=[{}]*12)
        keys = ('source_master_modified','material_removed','manufacturing_authorized',
                'gas_oil_stud_spark_plug_domains_complete','pressure_boundary_qualified','thermal_simulation','structural_simulation')
        good.update({key:False for key in keys})
        self.assertEqual(len(module.validate_report(good,c)),3)
        for key in keys:
            with self.assertRaises(ValueError):
                module.validate_report(dict(good,**{key:True}),c)
        bad = copy.deepcopy(good); bad['files'][0]['filename'] = '../head.stl'
        with self.assertRaises(ValueError): module.validate_report(bad,c)
        with self.assertRaises(ValueError): module.validate_report(dict(good,reference_wall_margin_conflicts=[]),c)
        with self.assertRaises(ValueError): module.validate_report(dict(good,status='approved'),c)


if __name__ == '__main__': unittest.main()
