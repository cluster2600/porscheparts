"""Four pure checks; no CAD, rendering, network or private input is loaded."""
import builtins
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


def load_source():
    path = Path(__file__).with_name('render_v5_v2.py')
    spec = importlib.util.spec_from_file_location('wholebody_render_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RenderCheckpointTests(unittest.TestCase):
    def test_no_native_import_on_load(self):
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.split('.')[0] in {'OCP', 'pyvista', 'vtk', 'matplotlib', 'numpy'}:
                raise AssertionError('native_or_render_import_during_source_load')
            return original(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=guarded):
            load_source()

    def test_exact_body_and_module(self):
        module = load_source()
        self.assertEqual(module.PINS['candidate.binbrep'], '450ba0816bf355f350b45e1878e3327f2070cd10b405f885afb3ef2c026bff0e')
        self.assertEqual(module.PINS['closed.step'], 'fac380b277add2e3d265d7fa8265baeb0ce460b9f69075730d14ece555e76a76')

    def test_exact_registration(self):
        self.assertEqual(load_source().REGISTRATION, {'scale_scan_units_per_mm_hypothesis': 1.0,
            'rotation_Z_deg_hypothesis': -90.0, 'translation_Z_hypothesis': 3.0})

    def test_hash_tamper_fails(self):
        module = load_source()
        with patch.object(module, 'sha', return_value='0' * 64), patch.object(Path, 'is_file', return_value=True), patch.object(Path, 'is_symlink', return_value=False):
            with self.assertRaisesRegex(ValueError, 'exact_input_required'):
                module.preflight(Path('/unused'))


if __name__ == '__main__':
    unittest.main()
