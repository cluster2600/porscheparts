import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/962-cylinder-head-f0/source/coolant_flow'
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location('cloud_restart', SOURCE / 'prepare_cloud_restart.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(root):
    parent = root / 'parent'
    for name in ('constant', 'system', '2200'):
        (parent / name).mkdir(parents=True)
    (parent / 'system/controlDict').write_text('startTime 1300; endTime 5000; writeInterval 100;')
    (parent / 'system/decomposeParDict').write_text('numberOfSubdomains 4; method scotch;')
    (parent / 'system/fvSolution').write_text('residualControl { p 1e-5; } equations { U 0.3; }')
    (parent / 'accept_mesh.py').write_text('guard')
    for name in ('U', 'p', 'phi', 'k', 'omega', 'nut'):
        (parent / '2200' / name).write_text(name)
    old = dict(cells=1, start_iteration=1300, end_iteration=5000, residual_target=1e-5,
               source_hashes={}, case_hashes={'system/fvSolution': module.sha(parent / 'system/fvSolution')})
    (parent / 'case-report.json').write_text(json.dumps(old))
    (parent / 'mesh-report.json').write_text(json.dumps(dict(cells=1, source_hashes={},
        status='mesh_numerical_gate_passed_not_physical_validation')))
    audit = dict(status='audited_isothermal_restart_not_physical_validation', cells=1,
        case_report_sha256=module.sha(parent / 'case-report.json'),
        mesh_report_sha256=module.sha(parent / 'mesh-report.json'),
        positive_turbulence_fields=True, saved_iteration=2200, history_hashes={}, log_hashes={},
        final_field_hashes={p.name: module.sha(p) for p in (parent / '2200').iterdir()})
    path = root / 'audit.json'
    path.write_text(json.dumps(audit))
    return parent, path


class CloudRestartTests(unittest.TestCase):
    def test_rank_sweep_keeps_checkpoint_physics_and_parent_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent, audit = fixture(root)
            before = {str(p.relative_to(parent)): module.sha(p) for p in parent.rglob('*') if p.is_file()}
            for ranks in (4, 8, 16, 32):
                output = root / str(ranks)
                report = module.prepare(parent, audit, output, ranks, 150, 300)
                module.verify(output, report['case_hashes'])
                self.assertEqual(report['start_iteration'], 2200)
                self.assertEqual(report['end_iteration'], 2350)
                self.assertEqual(report['parallel_ranks'], ranks)
                self.assertEqual((output / '2200/U').read_bytes(), (parent / '2200/U').read_bytes())
                self.assertEqual((output / 'system/fvSolution').read_bytes(), (parent / 'system/fvSolution').read_bytes())
                self.assertFalse(report['paid_instance_created'])
                self.assertIn('numberOfSubdomains ' + str(ranks) + ';', (output / 'system/decomposeParDict').read_text())
            self.assertEqual(before, {str(p.relative_to(parent)): module.sha(p) for p in parent.rglob('*') if p.is_file()})

    def test_changed_checkpoint_and_invalid_limits_leave_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent, audit = fixture(root)
            for ranks, iterations, seconds in ((64, 150, 300), (4, 0, 300), (4, 150, 86400)):
                with self.assertRaises(ValueError):
                    module.prepare(parent, audit, root / 'out', ranks, iterations, seconds)
                self.assertFalse((root / 'out').exists())
            (parent / '2200/U').write_text('tampered')
            with self.assertRaises(ValueError):
                module.prepare(parent, audit, root / 'out', 8, 150, 300)
            self.assertFalse((root / 'out').exists())

    def test_runner_refuses_missing_or_expired_campaign_deadline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent, audit = fixture(root)
            output = root / 'out'
            module.prepare(parent, audit, output, 8, 150, 300)
            for deadline in (None, '1'):
                env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'WM_PROJECT_VERSION': '13'}
                if deadline is not None:
                    env['CAMPAIGN_DEADLINE_EPOCH'] = deadline
                result = subprocess.run(['bash', str(output / 'run_cloud_restart.sh')],
                                        env=env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((output / 'log.checkMesh').exists())


if __name__ == '__main__':
    unittest.main()
