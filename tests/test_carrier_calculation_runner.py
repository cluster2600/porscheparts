"""A failed solve retains its receipt and removes only its owned container."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/run_carrier_calculations.py'
spec = importlib.util.spec_from_file_location('carrier_calculation_runner', SOURCE)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class CalculationRunnerTests(unittest.TestCase):
    def test_failed_case_preserves_prior_case_and_cleans_owned_container(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for size in (9, 7):
                (folder / f'mesh-{size}').mkdir()
                (folder / f'mesh-{size}/mesh.inp').write_text('fixture mesh')
            simulation = folder / 'simulation.py'
            simulation.write_text('def solve(folder, case, support=None):\n    if support: raise RuntimeError("fixture solve failure")\n')
            def docker(*args):
                return runner.CCX_SHA256 + ' /usr/bin/ccx' if 'sha256sum' in args else 'fixture'
            with patch.object(runner, 'SOURCE', simulation), patch.object(runner, 'docker', side_effect=docker), \
                 patch.object(runner.subprocess, 'run', return_value=Mock(returncode=0)) as remove:
                with self.assertRaisesRegex(RuntimeError, 'fixture solve failure'):
                    runner.run(folder)
            receipt = json.loads((folder / 'simulation-runtime.json').read_text())
            self.assertEqual(receipt['status'], 'failed')
            self.assertEqual(len(receipt['completed_cases']), 1)
            self.assertTrue(receipt['owned_container_removed'])
            self.assertEqual(remove.call_args.args[0], [runner.DOCKER, 'rm', '-f', receipt['container']])
            with self.assertRaises(FileExistsError):
                runner.run(folder)

    def test_missing_mesh_refuses_before_docker(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(runner, 'docker') as docker:
            with self.assertRaisesRegex(ValueError, 'Both C3D10 meshes'):
                runner.run(Path(temporary))
            docker.assert_not_called()


if __name__ == '__main__':
    unittest.main()
