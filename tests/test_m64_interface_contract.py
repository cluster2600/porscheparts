import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head'
spec = importlib.util.spec_from_file_location('m64_contract', ROOT / 'validate_interface_contract.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class M64InterfaceContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads((ROOT / 'interface-contract.json').read_text())

    def test_research_contract_is_valid_but_not_released(self):
        result = module.validate(self.contract)
        self.assertTrue(result['documentary_contract_valid'])
        self.assertFalse(result['manufacturing_authorized'])
        self.assertTrue(result['manufacturing_blockers'])

    def test_bore_is_not_register_and_legacy_geometry_not_transferred(self):
        self.assertEqual(self.contract['documented_reference_dimensions']['cylinder_bore']['nominal'], 100.0)
        self.assertIsNone(self.contract['critical_interfaces']['cylinder_register_diameter']['nominal'])
        self.assertFalse(self.contract['legacy_917_geometry_transferred'])

    def test_fabrication_claim_with_unknown_interfaces_is_rejected(self):
        self.contract['manufacturing_authorized'] = True
        with self.assertRaisesRegex(ValueError, 'Manufacturing claim rejected'):
            module.validate(self.contract)

    def test_missing_tolerance_remains_blocker_even_with_nominal(self):
        self.contract['critical_interfaces']['cylinder_register_diameter']['nominal'] = 100.0
        self.assertIn('cylinder_register_diameter.tolerance is unknown',
                      module.manufacturing_blockers(self.contract))

    def test_deleted_interface_cannot_evade_gate(self):
        del self.contract['critical_interfaces']['main_stud_axes']
        self.assertIn('main_stud_axes.nominal is unknown', module.manufacturing_blockers(self.contract))

    def test_unregistered_reference_is_rejected(self):
        self.contract['documented_reference_dimensions']['cylinder_bore']['source'] = 'invented'
        with self.assertRaisesRegex(ValueError, 'unregistered source'):
            module.validate(self.contract)

    def test_manual_ocr_is_not_promoted_to_design(self):
        leads = self.contract['local_manual_research_leads']
        self.assertFalse(leads['promoted_to_design_dimensions'])
        self.assertEqual(leads['confidence'], 'ocr_unreviewed_at_record_level')
        self.assertIsNone(self.contract['critical_interfaces']['seat_guide_and_spark_plug_interfaces']['nominal'])

    def test_g0_statuses_and_partial_facts_are_valid(self):
        interfaces = self.contract['critical_interfaces']
        self.assertEqual(interfaces['cylinder_register_diameter']['status'], 'absent')
        self.assertEqual(interfaces['seat_guide_and_spark_plug_interfaces']['status'], 'partial')
        for item in interfaces.values():
            self.assertIsNone(item['nominal'])
            self.assertNotEqual(item['status'], 'found')

    def test_nominal_without_source_is_rejected(self):
        item = self.contract['critical_interfaces']['main_stud_axes']
        item['nominal'] = 50.0
        with self.assertRaisesRegex(ValueError, 'without registered source'):
            module.validate(self.contract)
        item['source'] = 'P1'
        with self.assertRaisesRegex(ValueError, 'source_locator or confidence'):
            module.validate(self.contract)

    def test_partial_fact_promotion_or_unregistered_source_is_rejected(self):
        fact = self.contract['critical_interfaces']['sealing_surface_definition']['documented_partial_facts'][1]
        fact['promoted_to_nominal'] = True
        with self.assertRaisesRegex(ValueError, 'cannot be promoted'):
            module.validate(self.contract)
        fact['promoted_to_nominal'] = False
        fact['source'] = 'invented'
        with self.assertRaisesRegex(ValueError, 'unregistered source'):
            module.validate(self.contract)

    def test_found_requires_nominal_and_tolerance(self):
        self.contract['critical_interfaces']['cam_carrier_axes']['status'] = 'found'
        with self.assertRaisesRegex(ValueError, 'found requires'):
            module.validate(self.contract)


if __name__ == '__main__':
    unittest.main()
