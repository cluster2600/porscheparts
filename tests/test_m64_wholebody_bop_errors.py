import importlib.util
from pathlib import Path
import unittest


class BopErrorGateTests(unittest.TestCase):
    def test_an_empty_fault_list_cannot_hide_an_error_or_warning(self):
        path = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/wholebody/audit_native_bop.py'
        spec = importlib.util.spec_from_file_location('native_bop_guard', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = dict(exact_valid=True, solids=1, has_faulty=False, has_errors=False, has_warnings=False, inputs_unchanged=True)
        self.assertTrue(module.admitted(result))
        for name in ('has_faulty', 'has_errors', 'has_warnings'):
            self.assertFalse(module.admitted({**result, name: True}))
            self.assertFalse(module.admitted({k: v for k, v in result.items() if k != name}))
