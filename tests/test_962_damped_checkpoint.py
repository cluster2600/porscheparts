import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/962-cylinder-head-f0/source/coolant_flow'
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location('damped_checkpoint', SOURCE / 'prepare_damped_checkpoint.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class CheckpointTests(unittest.TestCase):
    def test_advanced_checkpoint_keeps_time_label_and_changes_only_equation_damping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); parent = root / 'parent'; parent.mkdir()
            (parent / 'constant').mkdir(); (parent / 'system').mkdir(); (parent / '1300').mkdir()
            (parent / 'system/controlDict').write_text('startTime 900; endTime 5000; writeInterval 100;')
            (parent / 'system/fvSolution').write_text(
                'p { solver GAMG; tolerance 1e-8; relTol 0.01; smoother GaussSeidel; }\n'
                'SIMPLE { consistent yes; }\n'
                'residualControl { p 1e-5; } equations { U 0.5; k 0.5; omega 0.5; }')
            (parent / 'accept_mesh.py').write_text('guard')
            for name in ('U', 'p', 'phi', 'k', 'omega', 'nut'): (parent / '1300' / name).write_text(name)
            old = dict(cells=1, start_iteration=900, end_iteration=5000, source_hashes={},
                case_hashes={'system/fvSolution': module.sha(parent / 'system/fvSolution')})
            (parent / 'case-report.json').write_text(json.dumps(old))
            (parent / 'mesh-report.json').write_text(json.dumps(dict(cells=1, source_hashes={})))
            audit = dict(status='audited_isothermal_restart_not_physical_validation',
                case_report_sha256=module.sha(parent / 'case-report.json'),
                mesh_report_sha256=module.sha(parent / 'mesh-report.json'), cells=1,
                positive_turbulence_fields=True, saved_iteration=1300, history_hashes={}, log_hashes={},
                final_field_hashes={p.name: module.sha(p) for p in (parent / '1300').iterdir()})
            path = root / 'audit.json'; path.write_text(json.dumps(audit))
            report = module.prepare_checkpoint(parent, path, root / 'out')
            module.verify(root / 'out', report['case_hashes'])
            self.assertIn('startTime 1300;', (root / 'out/system/controlDict').read_text())
            self.assertIn('-time 1300', (root / 'out/run_restart.sh').read_text())
            self.assertIn('p 1e-5;', (root / 'out/system/fvSolution').read_text())
            self.assertIn('U 0.3;', (root / 'out/system/fvSolution').read_text())
            self.assertEqual((root / 'out/1300/U').read_bytes(), (parent / '1300/U').read_bytes())
            import prepare_precise_pressure_pilot
            pilot = prepare_precise_pressure_pilot.prepare_pilot(parent, path, root / 'pilot')
            module.verify(root / 'pilot', pilot['case_hashes'])
            self.assertIn('tolerance 1e-10; relTol 0;', (root / 'pilot/system/fvSolution').read_text())
            self.assertIn('p 1e-5;', (root / 'pilot/system/fvSolution').read_text())
            self.assertIn('--kill-after=30s 300 mpirun', (root / 'pilot/run_restart.sh').read_text())
            self.assertEqual(pilot['maximum_solver_seconds'], 300)
            import prepare_simple_pressure_pilot
            simple = prepare_simple_pressure_pilot.prepare_simple(parent, path, root / 'simple')
            module.verify(root / 'simple', simple['case_hashes'])
            self.assertIn('consistent no;', (root / 'simple/system/fvSolution').read_text())
            self.assertIn('p 1e-5;', (root / 'simple/system/fvSolution').read_text())
            self.assertIn('writeInterval 10;', (root / 'simple/system/controlDict').read_text())
            (parent / '1300/U').write_text('changed')
            with self.assertRaises(ValueError): module.prepare_checkpoint(parent, path, root / 'bad')
            self.assertFalse((root / 'bad').exists())


if __name__ == '__main__': unittest.main()
