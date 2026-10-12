import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'twins/bionic-turbo-f1/cfd'))
import steady_restart
import transient_pilot
import test_bionic_turbo_transient as fixtures


class SteadyRestartTests(unittest.TestCase):
    def test_seed_provenance_numerics_and_fail_closed_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = fixtures.TransientPilotTests().parent(root)
            parent = root / 'transient'
            transient_pilot.prepare(original, parent)
            shutil.copytree(parent / '0', parent / '0.000019')
            (parent / 'native-exit.json').write_text('{"exit_code": 1}')
            (parent / 'log.transient-rhoPimpleFoam').write_text('End\n')
            with self.assertRaises(ValueError):
                steady_restart.prepare(parent, root / 'rejected')
            self.assertFalse((root / 'rejected').exists())
            (parent / 'native-exit.json').write_text('{"exit_code": 0}')
            output = root / 'restart'
            before = steady_restart.verify(parent)
            steady_restart.prepare(parent, output)
            self.assertEqual(before, steady_restart.verify(parent))
            self.assertEqual((output / '0/p').read_bytes(), (parent / '0.000019/p').read_bytes())
            self.assertEqual((output / 'constant/MRFProperties').read_bytes(), (parent / 'constant/MRFProperties').read_bytes())
            self.assertIn('default steadyState;', (output / 'system/fvSchemes').read_text())
            self.assertIn('div(phi,K) bounded Gauss upwind;', (output / 'system/fvSchemes').read_text())
            manifest = json.loads((output / 'case-manifest.json').read_text())
            self.assertEqual(manifest['steady_restart']['seed_time_s'], .000019)
            self.assertEqual(len(manifest['steady_restart']['seed_field_sha256']), 7)
            with mock.patch.object(steady_restart.subprocess, 'run', return_value=mock.Mock(returncode=0, stdout='id', stderr='')) as native:
                result = steady_restart.launch(output)
                self.assertFalse(result['performance_ranking_authorized'])
                self.assertIn('rhoSimpleFoam', native.call_args.args[0][-1])
            self.assertIn('stdbuf -oL -eL rhoSimpleFoam', (output / 'transient-supervisor.sh').read_text())
            with self.assertRaises(ValueError):
                steady_restart.launch(output)
            with self.assertRaises(FileExistsError):
                steady_restart.prepare(parent, output)

    def test_local_pseudo_time_is_never_labelled_physical_time(self):
        import lts_restart
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = fixtures.TransientPilotTests().parent(root)
            parent = root / 'transient'
            transient_pilot.prepare(original, parent)
            shutil.copytree(parent / '0', parent / '0.000019')
            (parent / 'native-exit.json').write_text('{"exit_code": 0}')
            (parent / 'log.transient-rhoPimpleFoam').write_text('End\n')
            output = root / 'lts'
            lts_restart.prepare(parent, output)
            manifest = json.loads((output / 'case-manifest.json').read_text())
            self.assertEqual(manifest['active_solve']['time_semantics'], 'local_pseudo_time_iterations_not_seconds')
            self.assertFalse(manifest['active_solve']['performance_ranking_authorized'])
            self.assertIn('default localEuler;', (output / 'system/fvSchemes').read_text())
            self.assertIn('maxCo 0.8; maxDeltaT 1e-6;', (output / 'system/fvSolution').read_text())
            self.assertNotIn('adjustTimeStep yes;', (output / 'system/controlDict').read_text())
            self.assertEqual((output / '0/U').read_bytes(), (parent / '0.000019/U').read_bytes())
            with mock.patch.object(transient_pilot.subprocess, 'run', return_value=mock.Mock(returncode=0, stdout='id', stderr='')):
                self.assertEqual(transient_pilot.launch(output)['status'], 'launched')

    def test_complete_restart_preserves_relative_phi_and_rho_bytes(self):
        import lts_restart_complete
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = fixtures.TransientPilotTests().parent(root)
            parent = root / 'transient'
            transient_pilot.prepare(original, parent)
            shutil.copytree(parent / '0', parent / '0.000019')
            (parent / '0.000019/phi').write_text('native relative flux; do not reconstruct from absolute U')
            (parent / '0.000019/rho').write_text('native transported density')
            (parent / 'native-exit.json').write_text('{"exit_code": 0}')
            (parent / 'log.transient-rhoPimpleFoam').write_text('End\n')
            output = root / 'complete'
            lts_restart_complete.prepare(parent, output)
            for name in ('phi','rho'):
                self.assertEqual((output / '0' / name).read_bytes(), (parent / '0.000019' / name).read_bytes())
            manifest = json.loads((output / 'case-manifest.json').read_text())
            self.assertEqual(len(manifest['steady_restart']['seed_field_sha256']), 9)
            (output / '0/phi').write_text('reconstructed')
            with self.assertRaises(ValueError):
                steady_restart.verify(output)
