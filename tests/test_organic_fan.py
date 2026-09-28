"""Small executable checks for the organic fan study's reusable numerical tools."""
from pathlib import Path
import subprocess
import sys
import unittest
import tempfile
from _deps import require_modules

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'twins/993-engine-cooling-fan-system-f0/source'


class OrganicFanTests(unittest.TestCase):
    def test_cfd_scope_hashes_and_rotation(self):
        subprocess.run([sys.executable, str(SOURCE/'test_build_fan_cfd.py')], check=True)

    def test_flow_rejects_unstable_history(self):
        subprocess.run([sys.executable, str(SOURCE/'summarize_fan_cfd.py')], check=True)

    def test_monitor_rejects_an_unprepared_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(SOURCE/'monitor_reference_cfd.py'), directory], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Not a prepared case', result.stderr)

    def test_invalid_trial_budget_is_rejected_before_output(self):
        require_modules('trimesh')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'case'
            result = subprocess.run([sys.executable, str(SOURCE/'prepare_reference_cfd.py'),
                'missing-geometry', str(output), '--iterations', '0'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('invalid choice', result.stderr)
            self.assertFalse(output.exists())

    def test_thermal_energy_balance_and_invalid_machine_recipe(self):
        require_modules('numpy', 'scipy', 'trimesh', 'matplotlib')
        subprocess.run([sys.executable, str(SOURCE/'simulate_zrapid_print.py'), 'self-test'], check=True)
