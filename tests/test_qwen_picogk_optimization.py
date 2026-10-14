"""Run the bounded PicoGK course's existing contract check without loading a model."""
from pathlib import Path
import subprocess
import sys
import unittest


class PicoGKOptimizationTest(unittest.TestCase):
    def test_contract(self):
        script = Path(__file__).resolve().parents[1] / 'training/qwen-picogk-20261012/pilot.py'
        result = subprocess.run([sys.executable, str(script), 'self-check'], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run([sys.executable, str(script.with_name('ask.py')), '--self-check'],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
