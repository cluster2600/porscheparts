"""Pure controller-guard tests; do not import NumPy/libigl or call Docker."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

PREP = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('held_atomic_topology_controller', PREP/'run_atomic_topology.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class GuardTests(unittest.TestCase):
    def child(self):
        result = json.loads((PREP/'held-child.json').read_text())
        result.update(root_authorized=True, root_and_peer_review_complete=True)
        return result

    def validate(self, child, output=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'child.json'; path.write_text(json.dumps(child))
            return module.validate(path, module.digest(path), output or module.OUTPUT)

    def test_held_and_changed_fixed_controls_refuse_before_output(self):
        held = self.child(); held['root_authorized'] = False
        cases = [held]
        for key, value in [('expected_counts', dict(vertices=902145, triangles=1804706)),
                           ('candidate_sha256', '0'*64), ('gates', {}), ('qualification', {'manufacturing_authorized': True})]:
            child = self.child(); child[key] = value; cases.append(child)
        child = self.child(); child['resources']['memory_bytes'] += 1; cases.append(child)
        for child in cases:
            with self.subTest(child=child), self.assertRaises(ValueError):
                self.validate(child)

    def test_missing_pin_and_observed_drift_refuse_before_output_or_core_import(self):
        child = self.child(); child['input_sha256'].pop(next(iter(child['input_sha256'])))
        with self.assertRaises(ValueError):
            self.validate(child)
        child = self.child()
        with mock.patch.object(module, 'observed', return_value={}), self.assertRaises(ValueError):
            self.validate(child)

    def test_existing_output_refused_after_valid_pins(self):
        child = self.child(); output = mock.Mock()
        output.resolve.return_value = module.OUTPUT.resolve()
        output.exists.return_value = True; output.is_symlink.return_value = False
        with mock.patch.object(module, 'observed', return_value=child['input_sha256']), self.assertRaises(ValueError):
            self.validate(child, output)


if __name__ == '__main__':
    unittest.main()
