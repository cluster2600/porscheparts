import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'twins/m64-cylinder-head/source/parametric/m64_head_skeleton.py'
spec = importlib.util.spec_from_file_location('m64_head_skeleton', MODULE_PATH)
skeleton = importlib.util.module_from_spec(spec)
spec.loader.exec_module(skeleton)

try:
    import cadquery  # noqa: F401
    HAVE_CQ = True
except ImportError:
    HAVE_CQ = False


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads(skeleton.DEFAULT_PARAMETERS.read_text())
        self.contract = json.loads(skeleton.DEFAULT_CONTRACT.read_text())

    def test_current_parameters_resolve(self):
        _, unsourced, sourced = skeleton.resolve_parameters(self.spec, self.contract)
        self.assertEqual(set(sourced), {'chamber_reference_diameter', 'intake_valve_head_diameter',
                                        'exhaust_valve_head_diameter'})
        self.assertIn('cylinder_register_diameter', unsourced)

    def test_modified_sourced_value_is_refused(self):
        self.spec['parameters']['chamber_reference_diameter']['value'] = 102.0
        with self.assertRaisesRegex(ValueError, 'differs from contract'):
            skeleton.resolve_parameters(self.spec, self.contract)

    def test_contract_value_changed_without_source_is_refused(self):
        ref = self.contract['documented_reference_dimensions']['cylinder_bore']
        ref['nominal'] = 102.0
        ref['source'] = None
        with self.assertRaisesRegex(ValueError, 'registered source'):
            skeleton.resolve_parameters(self.spec, self.contract)

    def test_unsourced_cannot_pose_as_sourced(self):
        item = self.spec['parameters']['cylinder_register_diameter']
        item['provenance'] = 'sourced'
        item['contract_path'] = 'critical_interfaces.cylinder_register_diameter.nominal'
        with self.assertRaisesRegex(ValueError, 'not found in contract'):
            skeleton.resolve_parameters(self.spec, self.contract)
        item['contract_path'] = None
        with self.assertRaisesRegex(ValueError, 'without contract_path'):
            skeleton.resolve_parameters(self.spec, self.contract)

    def test_unsourced_citing_path_or_unknown_provenance_is_refused(self):
        spec = copy.deepcopy(self.spec)
        spec['parameters']['chamber_depth']['contract_path'] = 'documented_reference_dimensions.cylinder_bore.nominal'
        with self.assertRaisesRegex(ValueError, 'cannot cite'):
            skeleton.resolve_parameters(spec, self.contract)
        self.spec['parameters']['chamber_depth']['provenance'] = 'estimated'
        with self.assertRaisesRegex(ValueError, 'provenance'):
            skeleton.resolve_parameters(self.spec, self.contract)

    def test_placeholder_refused_once_contract_sources_interface(self):
        iface = self.contract['critical_interfaces']['cam_carrier_axes']
        iface['status'] = 'found'
        with self.assertRaisesRegex(ValueError, 'placeholder refused'):
            skeleton.resolve_parameters(self.spec, self.contract)


@unittest.skipUnless(HAVE_CQ, 'cadquery indisponible')
class GenerationTests(unittest.TestCase):
    def test_generation_is_valid_and_not_master(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = skeleton.generate(tmp)
            self.assertTrue(manifest['brep_check_valid'])
            self.assertFalse(manifest['master_geometry'])
            self.assertFalse(manifest['manufacturing_authorized'])
            self.assertGreater(manifest['volume_mm3'], 0)
            self.assertTrue((Path(tmp) / 'm64-head-skeleton.step').stat().st_size > 0)
            params = json.loads(skeleton.DEFAULT_PARAMETERS.read_text())['parameters']
            expected = sorted(k for k, v in params.items() if v['provenance'] == 'unsourced')
            self.assertEqual(manifest['unsourced_parameters'], expected)
            self.assertFalse(set(manifest['unsourced_parameters']) & set(manifest['sourced_parameters']))
            self.assertEqual(len(manifest['sha256']['step']), 64)


if __name__ == '__main__':
    unittest.main()
