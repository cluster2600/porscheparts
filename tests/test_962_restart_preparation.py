import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/962-cylinder-head-f0/source/coolant_flow'
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location('water_restart', SOURCE / 'prepare_restart.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class RestartTests(unittest.TestCase):
    def fixture(self, root):
        parent = root / 'parent'; parent.mkdir()
        for name in ('constant/polyMesh', 'system', '900'):
            (parent / name).mkdir(parents=True)
        for name in ('U', 'p', 'phi', 'k', 'omega', 'nut'):
            (parent / '900' / name).write_text(name)
        (parent / 'constant/polyMesh/points').write_text('mesh')
        (parent / 'accept_mesh.py').write_text('guard')
        (parent / 'system/controlDict').write_text(
            'startFrom startTime; startTime 0; stopAt endTime; endTime 2000;')
        (parent / 'system/fvSolution').write_text(
            'nNonOrthogonalCorrectors 0; consistent yes; fields { p 0.3; }')
        (parent / 'system/fvSchemes').write_text(
            'gradSchemes { default Gauss linear; }\n'
            'laplacianSchemes { default Gauss linear corrected; }\n'
            'snGradSchemes { default corrected; }')
        old = {'case_hashes': {'system/fvSolution': module.sha(parent / 'system/fvSolution')}}
        (parent / 'case-report.json').write_text(json.dumps(old))
        mesh = dict(status='mesh_numerical_gate_passed_not_physical_validation', cells=4,
            source_hashes={'constant/polyMesh/points': module.sha(parent / 'constant/polyMesh/points')})
        (parent / 'mesh-report.json').write_text(json.dumps(mesh))
        stop = dict(latest_saved_iteration=900, simple_residual_control_satisfied=False,
            case_report_sha256=module.sha(parent / 'case-report.json'),
            native_mesh_receipt_sha256=module.sha(parent / 'mesh-report.json'),
            latest_saved_field_hashes={p.name: module.sha(p) for p in (parent / '900').iterdir()})
        stop_path = root / 'stop.json'; stop_path.write_text(json.dumps(stop))
        return parent, stop_path

    def test_changed_checkpoint_fails_before_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); parent, stop = self.fixture(root)
            (parent / '900/U').write_text('changed')
            with self.assertRaises(ValueError): module.prepare(parent, stop, root / 'out')
            self.assertFalse((root / 'out').exists())

    def test_limiter_comparison_changes_only_normal_gradient_recipe(self):
        import prepare_limited_restart
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); parent, stop = self.fixture(root)
            limited = root / 'limited'; unlimited = root / 'unlimited'
            module.prepare(parent, stop, unlimited)
            report = prepare_limited_restart.prepare_limited(parent, stop, limited)
            module.verify(limited, report['case_hashes'])
            self.assertIn('limited corrected 0.5;', (limited / 'system/fvSchemes').read_text())
            for name in ('system/fvSolution', 'system/controlDict', '900/U'):
                self.assertEqual(module.sha(limited / name), module.sha(unlimited / name))
            self.assertEqual(report['residual_target'], 1e-5)

    def test_restart_keeps_parent_and_binds_new_pressure_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); parent, stop = self.fixture(root)
            report = module.prepare(parent, stop, root / 'out')
            module.verify(root / 'out', report['case_hashes'])
            self.assertIn('nNonOrthogonalCorrectors 0;', (parent / 'system/fvSolution').read_text())
            self.assertIn('nNonOrthogonalCorrectors 2;', (root / 'out/system/fvSolution').read_text())
            self.assertIn('startTime 900;', (root / 'out/system/controlDict').read_text())
            with self.assertRaises(ValueError): module.prepare(parent, stop, root / 'out')

    def test_bounded_gradient_preserves_pressure_and_residual_controls(self):
        import prepare_bounded_gradient_restart
        import prepare_limited_restart
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); parent, stop = self.fixture(root)
            limited = root / 'limited'; bounded = root / 'bounded'
            prepare_limited_restart.prepare_limited(parent, stop, limited)
            report = prepare_bounded_gradient_restart.prepare_bounded(parent, stop, bounded)
            module.verify(bounded, report['case_hashes'])
            self.assertEqual(module.sha(bounded / 'system/fvSolution'), module.sha(limited / 'system/fvSolution'))
            self.assertIn('grad(U) cellLimited Gauss linear 1;', (bounded / 'system/fvSchemes').read_text())
            self.assertEqual(report['residual_target'], 1e-5)

    def test_consistent_pressure_variant_keeps_velocity_discretization_and_tolerance(self):
        import prepare_consistent_pressure_restart
        import prepare_limited_restart
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); parent, stop = self.fixture(root)
            limited = root / 'limited'; consistent = root / 'consistent'
            prepare_limited_restart.prepare_limited(parent, stop, limited)
            report = prepare_consistent_pressure_restart.prepare_consistent(parent, stop, consistent)
            module.verify(consistent, report['case_hashes'])
            self.assertEqual(module.sha(consistent / 'system/fvSchemes'), module.sha(limited / 'system/fvSchemes'))
            self.assertIn('fields { p 1; }', (consistent / 'system/fvSolution').read_text())
            self.assertEqual(report['residual_target'], 1e-5)


if __name__ == '__main__': unittest.main()
