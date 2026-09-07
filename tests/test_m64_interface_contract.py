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


if __name__ == '__main__':
    unittest.main()
